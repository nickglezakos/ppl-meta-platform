"""
Backfill `individual_video_appearances.representative_faces`.

For every iva row whose `representative_faces` column is NULL or empty (or
contains only a synthetic bbox stub written by the live recording path), this
script fetches the orchestrator's stored person_groups for the same video
(`GET /person-objects/{video_uuid}`), matches each row to its person_group,
and updates the row with the recovered `representative_faces` JSON.

Matching strategy (in order):
  1. Direct UUID match: iva.person_object_uuid == group.person_uuid/person_id
  2. Face-id intersection: face_ids inside iva.representative_faces overlap
     with group.all_face_ids
  3. Geometric match: entry_bbox center is closest to a group's
     movement_tracking.route_points center

Required because multiple iva insertion paths exist (live instant detection,
cross-video tracking, single-media MVR materialization) and only the last
writes a full `representative_faces` payload. Without it the cross-video
analysis screen renders empty Routes and missing thumbnails.

Usage:
    cd ppl-meta-vmeta && source venv/bin/activate
    set -a && source .env && set +a && cd src
    python scripts/backfill_iva_representative_faces.py [--dry-run] \
        [--video-uuid <uuid>] [--limit N] [--report-orphans]

Env vars:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    ORCHESTRATOR_BASE_URL          (default: http://localhost:8002)
    INTERNAL_SERVICE_TOKEN         (default: dev secret)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

import asyncpg
import httpx


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backfill_iva_representative_faces")


DEFAULT_INTERNAL_TOKEN = "ppl-meta-internal-service-secret-key-change-in-production"


def _db_config() -> Dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost")),
        "port": int(os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))),
        "database": os.getenv(
            "DB_NAME", os.getenv("POSTGRES_DATABASE", "ppl_meta_vmeta")
        ),
        "user": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "ppl_user")),
        "password": os.getenv(
            "DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "ppl_password")
        ),
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _fetch_missing_iva_rows(
    pool: asyncpg.Pool,
    video_uuid: Optional[str],
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    """Return iva rows whose representative_faces is missing/empty/stub.

    A "stub" row is one written by the live recording path that only stores
    `[{bbox, confidence}]` without face_id/face_data. We treat those as
    missing too, so backfill can replace them with a real face payload.
    """
    conditions = [
        "(iva.representative_faces IS NULL "
        " OR jsonb_typeof(iva.representative_faces) = 'null' "
        " OR iva.representative_faces = '[]'::jsonb "
        " OR iva.representative_faces = '{}'::jsonb "
        # bbox-only stubs from instant_detection_storage have no face_id/face_data
        " OR ("
        "     jsonb_typeof(iva.representative_faces) = 'array' "
        "     AND NOT EXISTS ("
        "         SELECT 1 FROM jsonb_array_elements(iva.representative_faces) e "
        "         WHERE e ? 'face_id' OR e ? 'face_data'"
        "     )"
        " )"
        ")"
    ]
    params: List[Any] = []
    idx = 1

    if video_uuid:
        conditions.append(f"iva.video_uuid = ${idx}::uuid")
        params.append(video_uuid)
        idx += 1

    where = " AND ".join(conditions)
    sql = f"""
        SELECT
            iva.individual_uuid::text   AS individual_uuid,
            iva.video_uuid::text        AS video_uuid,
            iva.person_object_uuid::text AS person_object_uuid,
            iva.entry_bbox              AS entry_bbox,
            iva.representative_faces    AS representative_faces
        FROM individual_video_appearances iva
        WHERE {where}
        ORDER BY iva.video_uuid, iva.start_timestamp
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def _update_iva_row(
    pool: asyncpg.Pool,
    individual_uuid: str,
    video_uuid: str,
    person_object_uuid: str,
    representative_faces: List[Dict[str, Any]],
) -> bool:
    sql = """
        UPDATE individual_video_appearances
           SET representative_faces = $4::jsonb
         WHERE individual_uuid    = $1::uuid
           AND video_uuid         = $2::uuid
           AND person_object_uuid = $3::uuid
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            sql,
            individual_uuid,
            video_uuid,
            person_object_uuid,
            json.dumps(representative_faces),
        )
    try:
        return int(result.split()[-1]) > 0
    except (IndexError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Orchestrator helpers
# ---------------------------------------------------------------------------

async def _fetch_orchestrator_person_groups(
    client: httpx.AsyncClient,
    orchestrator_url: str,
    video_uuid: str,
    auth_header: str,
) -> List[Dict[str, Any]]:
    url = f"{orchestrator_url.rstrip('/')}/person-objects/{video_uuid}"
    try:
        resp = await client.get(url, headers={"Authorization": auth_header})
    except httpx.HTTPError as exc:
        logger.warning("Orchestrator call failed for %s: %s", video_uuid, exc)
        return []

    if resp.status_code == 404:
        logger.info("Orchestrator returned 404 for video %s", video_uuid)
        return []
    if resp.status_code != 200:
        logger.warning(
            "Orchestrator returned %s for video %s: %s",
            resp.status_code,
            video_uuid,
            resp.text[:200],
        )
        return []

    try:
        data = resp.json()
    except ValueError:
        logger.warning("Non-JSON orchestrator response for %s", video_uuid)
        return []

    if not data.get("success"):
        logger.warning(
            "Orchestrator success=false for video %s; keys=%s",
            video_uuid,
            list(data.keys()),
        )
        return []

    groups = data.get("person_groups") or data.get("group_tracking") or []
    return [g for g in groups if isinstance(g, dict)]


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _normalize_representative_faces(group: Dict[str, Any]) -> List[Dict[str, Any]]:
    rep = group.get("representative_faces")
    if isinstance(rep, str):
        try:
            rep = json.loads(rep)
        except (TypeError, ValueError):
            rep = None
    if isinstance(rep, dict):
        faces = rep.get("faces")
        if isinstance(faces, list):
            return [f for f in faces if isinstance(f, dict)]
        return []
    if isinstance(rep, list):
        return [f for f in rep if isinstance(f, dict)]
    return []


def _extract_face_ids(rep: Any) -> Set[str]:
    if rep is None:
        return set()
    if isinstance(rep, str):
        try:
            rep = json.loads(rep)
        except (TypeError, ValueError):
            return set()
    if isinstance(rep, dict):
        rep = rep.get("faces") or []
    if not isinstance(rep, list):
        return set()
    out: Set[str] = set()
    for face in rep:
        if not isinstance(face, dict):
            continue
        for key in ("face_id", "id"):
            value = face.get(key)
            if value:
                out.add(str(value))
                break
        face_data = face.get("face_data") if isinstance(face.get("face_data"), dict) else None
        if face_data:
            for key in ("face_id", "id"):
                value = face_data.get(key)
                if value:
                    out.add(str(value))
                    break
    return out


def _bbox_center(bbox: Any) -> Optional[Tuple[float, float]]:
    if not bbox:
        return None
    try:
        if isinstance(bbox, str):
            bbox = json.loads(bbox)
        if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
            return None
        x1, y1, x2, y2 = (float(v) for v in bbox[:4])
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _match_group(
    person_groups: List[Dict[str, Any]],
    person_object_uuid: Optional[str],
    representative_faces: Any,
    entry_bbox: Any,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Match an iva row to the best person_group; return (group, reason)."""
    if not person_groups:
        return None, "no_groups"

    # 1. Direct UUID match.
    if person_object_uuid:
        target = str(person_object_uuid)
        for group in person_groups:
            for key in ("person_uuid", "person_object_uuid", "person_id"):
                value = group.get(key)
                if value is not None and str(value) == target:
                    return group, "uuid"

    # 2. Face-id intersection.
    iva_face_ids = _extract_face_ids(representative_faces)
    if iva_face_ids:
        for group in person_groups:
            group_face_ids = {
                str(fid)
                for fid in (group.get("all_face_ids") or [])
                if fid
            }
            if group_face_ids & iva_face_ids:
                return group, "face_id"

    # 3. Geometric fallback against route_points.
    center = _bbox_center(entry_bbox)
    if center is not None:
        ref_cx, ref_cy = center
        best_group: Optional[Dict[str, Any]] = None
        best_distance = float("inf")
        for group in person_groups:
            route_points = (group.get("movement_tracking") or {}).get("route_points") or []
            for rp in route_points:
                try:
                    dx = float(rp.get("center_x", 0)) - ref_cx
                    dy = float(rp.get("center_y", 0)) - ref_cy
                except (TypeError, ValueError):
                    continue
                distance = math.hypot(dx, dy)
                if distance < best_distance:
                    best_distance = distance
                    best_group = group
        if best_group is not None and best_distance < 50.0:
            return best_group, f"geometry({best_distance:.1f}px)"

    return None, "no_match"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

async def run(
    *,
    dry_run: bool,
    video_uuid_filter: Optional[str],
    limit: Optional[int],
    report_orphans: bool,
) -> int:
    orchestrator_url = os.getenv(
        "ORCHESTRATOR_BASE_URL", "http://localhost:8002"
    )
    auth_token = os.getenv("INTERNAL_SERVICE_TOKEN", DEFAULT_INTERNAL_TOKEN)
    auth_header = f"Bearer {auth_token}"

    pool = await asyncpg.create_pool(**_db_config(), min_size=1, max_size=4)
    if pool is None:
        logger.error("Failed to create DB pool")
        return 1

    try:
        rows = await _fetch_missing_iva_rows(pool, video_uuid_filter, limit)
        if not rows:
            logger.info("No iva rows with missing representative_faces. Done.")
            return 0

        logger.info(
            "Found %d iva rows missing representative_faces across %d videos.",
            len(rows),
            len({r["video_uuid"] for r in rows}),
        )

        rows_by_video: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            rows_by_video.setdefault(r["video_uuid"], []).append(r)

        updated = 0
        unmatched: List[Dict[str, Any]] = []
        skipped_empty_groups = 0
        videos_no_data = 0
        match_reasons: Dict[str, int] = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for video_uuid, video_rows in rows_by_video.items():
                groups = await _fetch_orchestrator_person_groups(
                    client, orchestrator_url, video_uuid, auth_header
                )
                if not groups:
                    videos_no_data += 1
                    logger.info(
                        "Video %s: orchestrator returned no person_groups; "
                        "skipping %d row(s).",
                        video_uuid,
                        len(video_rows),
                    )
                    for row in video_rows:
                        unmatched.append({**row, "reason": "no_groups"})
                    continue

                for row in video_rows:
                    matched, reason = _match_group(
                        groups,
                        row["person_object_uuid"],
                        row.get("representative_faces"),
                        row.get("entry_bbox"),
                    )
                    if matched is None:
                        unmatched.append({**row, "reason": reason})
                        continue

                    rep_faces = _normalize_representative_faces(matched)
                    if not rep_faces:
                        skipped_empty_groups += 1
                        continue

                    bucket = reason.split("(")[0]
                    match_reasons[bucket] = match_reasons.get(bucket, 0) + 1

                    if dry_run:
                        logger.info(
                            "[DRY RUN] Would update video=%s person=%s "
                            "via %s with %d face(s).",
                            video_uuid,
                            row["person_object_uuid"],
                            reason,
                            len(rep_faces),
                        )
                        updated += 1
                        continue

                    did_update = await _update_iva_row(
                        pool,
                        individual_uuid=row["individual_uuid"],
                        video_uuid=video_uuid,
                        person_object_uuid=row["person_object_uuid"],
                        representative_faces=rep_faces,
                    )
                    if did_update:
                        updated += 1
                        logger.info(
                            "Updated video=%s person=%s via %s (%d face(s))",
                            video_uuid,
                            row["person_object_uuid"],
                            reason,
                            len(rep_faces),
                        )

        logger.info("=" * 60)
        logger.info("Backfill summary:")
        logger.info("  rows scanned        : %d", len(rows))
        logger.info(
            "  rows updated        : %d%s",
            updated,
            " (dry run)" if dry_run else "",
        )
        if match_reasons:
            for reason, count in sorted(match_reasons.items()):
                logger.info("    via %-18s : %d", reason, count)
        logger.info("  rows unmatched      : %d", len(unmatched))
        logger.info("  rows empty groups   : %d", skipped_empty_groups)
        logger.info("  videos w/ no data   : %d", videos_no_data)
        logger.info("=" * 60)

        if report_orphans and unmatched:
            logger.info("Orphan iva rows (no orchestrator match):")
            orphan_by_video: Dict[str, List[Dict[str, Any]]] = {}
            for row in unmatched:
                orphan_by_video.setdefault(row["video_uuid"], []).append(row)
            for vid, orph_rows in orphan_by_video.items():
                logger.info(
                    "  video %s: %d orphan row(s)", vid, len(orph_rows)
                )
                for row in orph_rows:
                    logger.info(
                        "    individual=%s person_object=%s reason=%s",
                        row["individual_uuid"],
                        row["person_object_uuid"],
                        row.get("reason"),
                    )

        return 0
    finally:
        await pool.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview updates without writing to the database.",
    )
    parser.add_argument(
        "--video-uuid",
        default=None,
        help="Only process iva rows for this video UUID.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum iva rows to scan.",
    )
    parser.add_argument(
        "--report-orphans",
        action="store_true",
        help="Print iva rows that have no orchestrator backing for diagnosis.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    code = asyncio.run(
        run(
            dry_run=args.dry_run,
            video_uuid_filter=args.video_uuid,
            limit=args.limit,
            report_orphans=args.report_orphans,
        )
    )
    sys.exit(code)


if __name__ == "__main__":
    main()

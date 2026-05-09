"""
Audit and optionally delete orphan `individual_video_appearances` rows.

A row is considered an orphan when, for its `(video_uuid, person_object_uuid)`,
the orchestrator's persisted `person_groups` (from
`GET /person-objects/{video_uuid}`) provides no backing — meaning the row was
written by a different path (typically cross-video tracking before the
standalone-MVR contract was enforced) and points to a person identity that no
longer exists in the per-video orchestrator state.

Two orphan classes are reported and optionally deleted:

  classA — orchestrator returned >=1 person_group for the video, but the iva
           row could not be matched by UUID, face_id intersection, or
           bbox-center geometry. These are phantom rows.

  classB — orchestrator returned NO person_groups for the video at all AND
           the iva row's representative_faces is missing or stub-only. These
           are the rows from videos that were never materialized through
           `process_single_media_for_mvr`.

Usage:
    cd ppl-meta-vmeta && source venv/bin/activate
    set -a && source .env && set +a && cd src
    python scripts/audit_delete_orphan_iva.py --dry-run            # report only
    python scripts/audit_delete_orphan_iva.py --dry-run --classes A
    python scripts/audit_delete_orphan_iva.py --apply --classes A,B

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
logger = logging.getLogger("audit_delete_orphan_iva")


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

async def _fetch_candidate_rows(
    pool: asyncpg.Pool,
    video_uuid: Optional[str],
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    """Fetch iva rows that might be orphans (missing or stub rep_faces)."""
    conditions = [
        "(iva.representative_faces IS NULL "
        " OR jsonb_typeof(iva.representative_faces) = 'null' "
        " OR iva.representative_faces = '[]'::jsonb "
        " OR iva.representative_faces = '{}'::jsonb "
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


async def _delete_iva_rows(
    pool: asyncpg.Pool,
    rows: List[Dict[str, Any]],
) -> int:
    if not rows:
        return 0
    deleted = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for row in rows:
                result = await conn.execute(
                    """
                    DELETE FROM individual_video_appearances
                     WHERE individual_uuid    = $1::uuid
                       AND video_uuid         = $2::uuid
                       AND person_object_uuid = $3::uuid
                    """,
                    row["individual_uuid"],
                    row["video_uuid"],
                    row["person_object_uuid"],
                )
                try:
                    deleted += int(result.split()[-1])
                except (IndexError, ValueError):
                    pass
    return deleted


# ---------------------------------------------------------------------------
# Orchestrator helpers
# ---------------------------------------------------------------------------

async def _fetch_orchestrator_person_groups(
    client: httpx.AsyncClient,
    orchestrator_url: str,
    video_uuid: str,
    auth_header: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Return (person_groups, status). status is 'ok'|'http'|'404'|'error'."""
    url = f"{orchestrator_url.rstrip('/')}/person-objects/{video_uuid}"
    try:
        resp = await client.get(url, headers={"Authorization": auth_header})
    except httpx.HTTPError as exc:
        logger.warning("Orchestrator call failed for %s: %s", video_uuid, exc)
        return [], "error"

    if resp.status_code == 404:
        return [], "404"
    if resp.status_code != 200:
        logger.warning(
            "Orchestrator %s for %s: %s",
            resp.status_code, video_uuid, resp.text[:200],
        )
        return [], "http"
    try:
        data = resp.json()
    except ValueError:
        return [], "error"
    if not data.get("success"):
        return [], "error"
    groups = data.get("person_groups") or data.get("group_tracking") or []
    return [g for g in groups if isinstance(g, dict)], "ok"


# ---------------------------------------------------------------------------
# Matching helpers (same algorithm as backfill)
# ---------------------------------------------------------------------------

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


def _is_matched(
    person_groups: List[Dict[str, Any]],
    person_object_uuid: Optional[str],
    representative_faces: Any,
    entry_bbox: Any,
) -> bool:
    if not person_groups:
        return False
    if person_object_uuid:
        target = str(person_object_uuid)
        for group in person_groups:
            for key in ("person_uuid", "person_object_uuid", "person_id"):
                value = group.get(key)
                if value is not None and str(value) == target:
                    return True
    iva_face_ids = _extract_face_ids(representative_faces)
    if iva_face_ids:
        for group in person_groups:
            group_face_ids = {
                str(fid) for fid in (group.get("all_face_ids") or []) if fid
            }
            if group_face_ids & iva_face_ids:
                return True
    center = _bbox_center(entry_bbox)
    if center is not None:
        ref_cx, ref_cy = center
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
        if best_distance < 50.0:
            return True
    return False


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

async def run(
    *,
    apply: bool,
    classes: Set[str],
    video_uuid_filter: Optional[str],
    limit: Optional[int],
    sample: int,
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
        candidates = await _fetch_candidate_rows(pool, video_uuid_filter, limit)
        if not candidates:
            logger.info("No candidate rows.")
            return 0

        rows_by_video: Dict[str, List[Dict[str, Any]]] = {}
        for r in candidates:
            rows_by_video.setdefault(r["video_uuid"], []).append(r)

        logger.info(
            "Scanning %d candidate iva rows across %d videos.",
            len(candidates), len(rows_by_video),
        )

        classA_rows: List[Dict[str, Any]] = []
        classB_rows: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for video_uuid, video_rows in rows_by_video.items():
                groups, status = await _fetch_orchestrator_person_groups(
                    client, orchestrator_url, video_uuid, auth_header
                )
                if not groups:
                    # classB: orchestrator has no data, iva rep_faces missing
                    classB_rows.extend(video_rows)
                    continue
                for row in video_rows:
                    if not _is_matched(
                        groups,
                        row["person_object_uuid"],
                        row.get("representative_faces"),
                        row.get("entry_bbox"),
                    ):
                        classA_rows.append(row)

        logger.info("=" * 60)
        logger.info("Audit summary:")
        logger.info("  candidates scanned       : %d", len(candidates))
        logger.info(
            "  classA (phantom UUIDs)   : %d rows  (will %s)",
            len(classA_rows),
            "DELETE" if apply and "A" in classes else (
                "delete" if "A" in classes else "skip"
            ),
        )
        logger.info(
            "  classB (no orch data)    : %d rows  (will %s)",
            len(classB_rows),
            "DELETE" if apply and "B" in classes else (
                "delete" if "B" in classes else "skip"
            ),
        )
        logger.info("=" * 60)

        # Per-video grouping for human inspection
        if sample > 0:
            for label, rows in (("classA", classA_rows), ("classB", classB_rows)):
                if not rows:
                    continue
                by_video: Dict[str, int] = {}
                for r in rows:
                    by_video[r["video_uuid"]] = by_video.get(r["video_uuid"], 0) + 1
                logger.info(
                    "%s touches %d videos. Top %d by row count:",
                    label, len(by_video), min(sample, len(by_video)),
                )
                for vid, cnt in sorted(
                    by_video.items(), key=lambda x: -x[1]
                )[:sample]:
                    logger.info("  %s : %d row(s)", vid, cnt)

        target_rows: List[Dict[str, Any]] = []
        if "A" in classes:
            target_rows.extend(classA_rows)
        if "B" in classes:
            target_rows.extend(classB_rows)

        if not apply:
            logger.info(
                "[DRY RUN] Would delete %d row(s). Re-run with --apply to commit.",
                len(target_rows),
            )
            return 0

        if not target_rows:
            logger.info("Nothing to delete.")
            return 0

        deleted = await _delete_iva_rows(pool, target_rows)
        logger.info("DELETED %d iva row(s).", deleted)
        return 0
    finally:
        await pool.close()


def _parse_classes(value: str) -> Set[str]:
    valid = {"A", "B"}
    requested = {c.strip().upper() for c in value.split(",") if c.strip()}
    invalid = requested - valid
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Unknown class(es): {sorted(invalid)}. Use A and/or B."
        )
    if not requested:
        raise argparse.ArgumentTypeError("Specify at least one class (A or B).")
    return requested


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="Audit only; do not delete.")
    mode.add_argument("--apply", action="store_true",
                      help="Apply deletions for the requested --classes.")
    parser.add_argument(
        "--classes", type=_parse_classes, default={"A", "B"},
        help="Comma list of classes to act on (A,B). Default: A,B.",
    )
    parser.add_argument("--video-uuid", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--sample", type=int, default=10,
        help="Number of top videos per class to print in the report.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    code = asyncio.run(
        run(
            apply=args.apply,
            classes=args.classes,
            video_uuid_filter=args.video_uuid,
            limit=args.limit,
            sample=args.sample,
        )
    )
    sys.exit(code)


if __name__ == "__main__":
    main()

"""
One-shot recovery: delete broken iva/individuals/mvr_people rows for given
video_uuid(s) and re-materialize them from the orchestrator's authoritative
/person-objects/{video_uuid} payload (proper person_uuid + representative_faces +
movement_tracking).

Why:
    A previous materialization path coerced synthetic person identifiers
    ("person_1") into freshly minted random UUIDs and persisted iva rows with
    NULL representative_faces. Those rows can't be matched against the
    orchestrator's person_groups by UUID, so the frontend overlay/route
    renderers find no data. The forward-looking fix lives in
    `_materialize_single_media_from_persisted_person_objects` which now enriches
    the payload from orchestrator before persisting.

This script applies the same enrichment retroactively for already-broken videos.

Usage:
    python -m scripts.rematerialize_video_iva --video-uuid UUID [--video-uuid UUID ...]
    python -m scripts.rematerialize_video_iva --apply           # required to actually mutate
    python -m scripts.rematerialize_video_iva --dry-run         # default
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import asyncpg
import httpx

LOGGER = logging.getLogger("rematerialize_iva")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val


async def _connect_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=_env("DB_HOST", "localhost"),
        port=int(_env("DB_PORT", "5432")),
        database=_env("DB_NAME", "ppl_meta_vmeta"),
        user=_env("DB_USER", "ppl_user"),
        password=_env("DB_PASSWORD", "ppl_password"),
        min_size=1,
        max_size=4,
    )


async def _fetch_person_groups(
    client: httpx.AsyncClient, orchestrator_url: str, token: str, video_uuid: str
) -> List[Dict[str, Any]]:
    resp = await client.get(
        f"{orchestrator_url}/person-objects/{video_uuid}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Service-Name": "ppl-meta-vmeta-rematerialize",
        },
    )
    if resp.status_code != 200:
        LOGGER.warning(
            "orchestrator returned %s for /person-objects/%s: %s",
            resp.status_code,
            video_uuid,
            resp.text[:200],
        )
        return []
    data = resp.json() or {}
    return list(data.get("person_groups") or [])


def _normalize_quality(raw: Any) -> float:
    try:
        q = float(raw)
    except (TypeError, ValueError):
        return 0.85
    if q <= 0.0:
        return 0.85
    return q / 100.0 if q > 1.0 else q


def _coerce_uuid(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except (ValueError, AttributeError):
        return None


async def _delete_existing(conn: asyncpg.Connection, video_uuid: UUID) -> Dict[str, int]:
    """Remove iva rows + dependent individuals/mvr_people scoped to this video."""
    counts: Dict[str, int] = {}
    # Capture individual_uuids tied to this video before deleting iva rows.
    rows = await conn.fetch(
        "SELECT DISTINCT individual_uuid FROM individual_video_appearances WHERE video_uuid=$1",
        video_uuid,
    )
    individual_uuids = [r["individual_uuid"] for r in rows]

    iva_del = await conn.execute(
        "DELETE FROM individual_video_appearances WHERE video_uuid=$1",
        video_uuid,
    )
    counts["iva_deleted"] = int(iva_del.split()[-1] or 0)

    mvr_del = await conn.execute(
        "DELETE FROM mvr_people WHERE source_media_uuid=$1",
        video_uuid,
    )
    counts["mvr_people_deleted"] = int(mvr_del.split()[-1] or 0)

    if individual_uuids:
        # Drop mapping rows then individuals that have no remaining appearances.
        try:
            await conn.execute(
                "DELETE FROM individual_mvr_mapping WHERE individual_uuid = ANY($1::uuid[])",
                individual_uuids,
            )
        except asyncpg.UndefinedTableError:
            pass
        # Only delete individuals that no longer appear in any video.
        ind_del = await conn.execute(
            """
            DELETE FROM individuals i
             WHERE i.individual_uuid = ANY($1::uuid[])
               AND NOT EXISTS (
                   SELECT 1 FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = i.individual_uuid
               )
            """,
            individual_uuids,
        )
        counts["individuals_deleted"] = int(ind_del.split()[-1] or 0)
    else:
        counts["individuals_deleted"] = 0

    return counts


async def _insert_for_group(
    conn: asyncpg.Connection,
    video_uuid: UUID,
    appearance_ts: datetime,
    group: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist a single orchestrator person_group as iva + individuals row pair."""
    person_uuid_str = _coerce_uuid(
        group.get("person_uuid")
        or group.get("person_object_uuid")
        or group.get("person_id")
    )
    if not person_uuid_str:
        return {"status": "skipped_no_uuid"}

    person_object_uuid = UUID(person_uuid_str)
    representative_faces = group.get("representative_faces") or []
    movement = group.get("movement_tracking") or {}
    route_points = movement.get("route_points") or []
    avg_conf = float(group.get("average_confidence") or 0.9)
    quality_metrics = group.get("quality_metrics") or {}
    avg_quality = _normalize_quality(
        quality_metrics.get("average_quality")
        or quality_metrics.get("best_quality")
        or 80.0
    )
    demographics = group.get("demographics") or {}

    individual_uuid = uuid4()
    individual_id = f"isolated_{individual_uuid.hex[:8]}"

    age_min = demographics.get("age_min")
    age_max = demographics.get("age_max", age_min)
    persisted_age = None
    if age_min is not None:
        try:
            persisted_age = int(round((float(age_min) + float(age_max if age_max is not None else age_min)) / 2))
        except (TypeError, ValueError):
            persisted_age = None
    persisted_gender = demographics.get("gender")

    await conn.execute(
        """
        INSERT INTO individuals
            (individual_uuid, individual_id, confidence_score,
             spatial_signature, temporal_signature,
             gender_estimate, age_estimate, source_type)
        VALUES ($1,$2,$3,$4,$5,$6,$7,'recording_pipeline')
        """,
        individual_uuid,
        individual_id,
        avg_conf,
        json.dumps({}),
        json.dumps({}),
        persisted_gender,
        persisted_age,
    )

    # Pull entry/exit bbox from route_points for richer per-video context.
    entry_bbox = None
    exit_bbox = None
    if route_points:
        first_bbox = route_points[0].get("bbox")
        last_bbox = route_points[-1].get("bbox")
        if isinstance(first_bbox, list) and len(first_bbox) == 4:
            entry_bbox = [float(x) for x in first_bbox]
        if isinstance(last_bbox, list) and len(last_bbox) == 4:
            exit_bbox = [float(x) for x in last_bbox]

    movement_pattern = {
        "route_points": route_points,
        "movement_statistics": movement.get("movement_statistics") or {},
    } if route_points else None

    await conn.execute(
        """
        INSERT INTO individual_video_appearances
            (individual_uuid, video_uuid, person_object_uuid,
             start_timestamp, end_timestamp,
             entry_bbox, exit_bbox,
             confidence, representative_faces, movement_pattern,
             quality_score, processing_method)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb,$11,'rematerialize_orch')
        """,
        individual_uuid,
        video_uuid,
        person_object_uuid,
        appearance_ts,
        appearance_ts,
        entry_bbox,
        exit_bbox,
        avg_conf,
        json.dumps(representative_faces),
        json.dumps(movement_pattern) if movement_pattern else None,
        float(avg_quality),
    )

    return {
        "status": "inserted",
        "individual_uuid": str(individual_uuid),
        "person_object_uuid": str(person_object_uuid),
        "rep_faces": len(representative_faces),
        "route_points": len(route_points),
    }


async def _process_video(
    pool: asyncpg.Pool,
    client: httpx.AsyncClient,
    orchestrator_url: str,
    token: str,
    video_uuid_str: str,
    apply: bool,
) -> Dict[str, Any]:
    video_uuid = UUID(video_uuid_str)

    person_groups = await _fetch_person_groups(client, orchestrator_url, token, str(video_uuid))
    if not person_groups:
        return {
            "video_uuid": str(video_uuid),
            "status": "no_orchestrator_data",
            "person_groups": 0,
        }

    appearance_ts = datetime.utcnow()
    summary: Dict[str, Any] = {
        "video_uuid": str(video_uuid),
        "person_groups_returned": len(person_groups),
        "applied": apply,
    }

    if not apply:
        summary["status"] = "dry_run"
        summary["would_replace_with"] = [
            {
                "person_uuid": _coerce_uuid(
                    g.get("person_uuid") or g.get("person_object_uuid") or g.get("person_id")
                ),
                "rep_faces": len(g.get("representative_faces") or []),
                "route_points": len((g.get("movement_tracking") or {}).get("route_points") or []),
            }
            for g in person_groups
        ]
        return summary

    async with pool.acquire() as conn:
        async with conn.transaction():
            deletions = await _delete_existing(conn, video_uuid)
            inserts = []
            for group in person_groups:
                inserts.append(await _insert_for_group(conn, video_uuid, appearance_ts, group))

    summary["deletions"] = deletions
    summary["inserts"] = inserts
    summary["status"] = "applied"
    return summary


async def main_async(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    orchestrator_url = _env("PPL_ORCHESTRATOR_URL", "http://localhost:8002")
    token = _env(
        "INTERNAL_SERVICE_TOKEN",
        "ppl-meta-internal-service-secret-key-change-in-production",
    )

    pool = await _connect_pool()
    try:
        target_uuids: List[str] = list(args.video_uuid or [])
        if not target_uuids and args.from_broken:
            rows = await pool.fetch(
                """
                SELECT DISTINCT video_uuid::text AS v
                  FROM individual_video_appearances
                 WHERE representative_faces IS NULL
                    OR representative_faces = 'null'::jsonb
                    OR (jsonb_typeof(representative_faces) = 'array'
                        AND jsonb_array_length(representative_faces) = 0)
                """
            )
            target_uuids = [r["v"] for r in rows]
            LOGGER.info("Discovered %d broken video_uuid(s) via --from-broken", len(target_uuids))

        if not target_uuids:
            LOGGER.error("No video UUIDs supplied. Use --video-uuid or --from-broken.")
            return 2

        async with httpx.AsyncClient(timeout=30.0) as client:
            results = []
            for vu in target_uuids:
                try:
                    res = await _process_video(pool, client, orchestrator_url, token, vu, args.apply)
                except Exception as exc:  # noqa: BLE001
                    LOGGER.exception("Failed to process %s", vu)
                    res = {"video_uuid": vu, "status": "error", "error": str(exc)}
                results.append(res)
                LOGGER.info("Result for %s: %s", vu, json.dumps(res, default=str)[:400])

        print(json.dumps({"results": results, "applied": args.apply}, indent=2, default=str))
        return 0
    finally:
        await pool.close()


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--video-uuid",
        action="append",
        help="Specific video UUID(s) to re-materialize. Repeatable.",
    )
    parser.add_argument(
        "--from-broken",
        action="store_true",
        help=(
            "Discover all video_uuids whose iva rows have missing/empty "
            "representative_faces and process them."
        ),
    )
    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument("--dry-run", action="store_true", default=True, help="Default. Do not mutate.")
    mutex.add_argument("--apply", action="store_true", help="Perform deletes + inserts.")
    args = parser.parse_args(argv)
    if args.apply:
        args.dry_run = False
    return args


def main() -> int:
    args = parse_args(sys.argv[1:])
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())

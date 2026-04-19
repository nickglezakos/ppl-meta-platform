"""
Tracking Sessions Summary API

Aggregated summary endpoint for tracking sessions, used by the analytics dashboard
when querying instant detection data (source_type = 'instant_detection').
"""

import logging
from datetime import datetime, timezone as tz
from typing import Dict, List, Optional

import pytz
from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_user, get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_local_time(dt: datetime) -> datetime:
    """Convert datetime to local server timezone (naive) for DB queries."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    local_tz = pytz.timezone('Europe/Athens')
    return dt.astimezone(local_tz).replace(tzinfo=None)


@router.get(
    "/tracking-sessions/summary",
    summary="Get aggregated tracking session summary",
    description="Returns aggregated counts from tracking sessions filtered by source_type and optional camera_device_id list. Used by the analytics dashboard for instant detection data.",
)
async def get_tracking_session_summary(
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)"),
    source_type: str = Query("recording_pipeline", description="Source type: recording_pipeline or instant_detection"),
    camera_device_ids: Optional[str] = Query(None, description="Comma-separated camera device IDs to filter"),
    db_connection=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Aggregated tracking session summary with demographics.

    Returns session counts, individual counts, MVR people counts,
    and demographics broken down from the individuals table.
    """
    try:
        start_local = _to_local_time(start_time)
        end_local = _to_local_time(end_time)

        device_ids: Optional[List[str]] = None
        if camera_device_ids:
            device_ids = [d.strip() for d in camera_device_ids.split(",") if d.strip()]

        logger.info(
            f"📊 Tracking sessions summary: source={source_type}, "
            f"cameras={len(device_ids) if device_ids else 'ALL'}, "
            f"range={start_local} to {end_local}"
        )

        # Session aggregates
        sessions_query = """
        SELECT
            COUNT(DISTINCT ts.session_uuid) AS session_count,
            COALESCE(SUM(ts.individuals_found), 0) AS total_individuals,
            COALESCE(SUM(ts.unique_mvr_people_count), 0) AS total_mvr_people,
            MAX(ts.completed_at) AS last_detection
        FROM tracking_sessions ts
        WHERE ts.source_type = $1
          AND ts.created_at >= $2
          AND ts.created_at <= $3
          AND ts.status = 'completed'
        """
        params = [source_type, start_local, end_local]

        if device_ids:
            sessions_query += f"  AND ts.camera_device_id = ANY(${len(params) + 1}::text[])\n"
            params.append(device_ids)

        row = await db_connection.fetchrow(sessions_query, *params)

        session_count = row["session_count"] if row else 0
        total_individuals = row["total_individuals"] if row else 0
        total_mvr_people = row["total_mvr_people"] if row else 0
        last_detection = row["last_detection"] if row else None

        # Demographics from individuals linked to matching sessions
        demo_query = """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE i.gender_estimate = 'male') AS total_male,
            COUNT(*) FILTER (WHERE i.gender_estimate = 'female') AS total_female,
            COUNT(*) FILTER (WHERE i.age_estimate IS NOT NULL AND i.age_estimate < 25) AS total_young,
            COUNT(*) FILTER (WHERE i.age_estimate IS NOT NULL AND i.age_estimate >= 25
                              AND i.age_estimate < 65) AS total_adult,
            COUNT(*) FILTER (WHERE i.age_estimate IS NOT NULL AND i.age_estimate >= 65) AS total_elderly
        FROM individuals i
        JOIN tracking_sessions ts ON i.created_by_session = ts.session_uuid
        WHERE ts.source_type = $1
          AND ts.created_at >= $2
          AND ts.created_at <= $3
          AND ts.status = 'completed'
        """
        demo_params = [source_type, start_local, end_local]

        if device_ids:
            demo_query += f"  AND ts.camera_device_id = ANY(${len(demo_params) + 1}::text[])\n"
            demo_params.append(device_ids)

        demo = await db_connection.fetchrow(demo_query, *demo_params)

        total_demo = demo["total"] if demo else 0
        total_male = demo["total_male"] if demo else 0
        total_female = demo["total_female"] if demo else 0
        total_young = demo["total_young"] if demo else 0
        total_adult = demo["total_adult"] if demo else 0
        total_elderly = demo["total_elderly"] if demo else 0

        # Per-camera breakdown
        camera_query = """
        SELECT
            ts.camera_device_id,
            COUNT(DISTINCT ts.session_uuid) AS sessions,
            COALESCE(SUM(ts.individuals_found), 0) AS individuals,
            COALESCE(SUM(ts.unique_mvr_people_count), 0) AS mvr_people
        FROM tracking_sessions ts
        WHERE ts.source_type = $1
          AND ts.created_at >= $2
          AND ts.created_at <= $3
          AND ts.status = 'completed'
          AND ts.camera_device_id IS NOT NULL
        """
        cam_params = [source_type, start_local, end_local]
        if device_ids:
            camera_query += f"  AND ts.camera_device_id = ANY(${len(cam_params) + 1}::text[])\n"
            cam_params.append(device_ids)
        camera_query += " GROUP BY ts.camera_device_id ORDER BY mvr_people DESC"

        cam_rows = await db_connection.fetch(camera_query, *cam_params)
        camera_breakdown = [
            {
                "camera_device_id": r["camera_device_id"],
                "sessions": r["sessions"],
                "individuals": r["individuals"],
                "mvr_people": r["mvr_people"],
            }
            for r in cam_rows
        ]

        logger.info(
            f"✅ Summary: {session_count} sessions, {total_individuals} individuals, "
            f"{total_mvr_people} MVR people, {len(camera_breakdown)} cameras"
        )

        return {
            "source_type": source_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "session_count": session_count,
            "total_individuals": total_individuals,
            "total_mvr_people": total_mvr_people,
            "last_detection": last_detection.isoformat() if last_detection else None,
            "active_cameras": len(camera_breakdown),
            "demographics": {
                "total": total_demo,
                "total_male": total_male,
                "total_female": total_female,
                "total_young": total_young,
                "total_adult": total_adult,
                "total_elderly": total_elderly,
            },
            "camera_breakdown": camera_breakdown,
        }

    except Exception as e:
        logger.error(f"❌ Error in tracking sessions summary: {e}", exc_info=True)
        return {
            "source_type": source_type,
            "session_count": 0,
            "total_individuals": 0,
            "total_mvr_people": 0,
            "last_detection": None,
            "active_cameras": 0,
            "demographics": {
                "total": 0,
                "total_male": 0,
                "total_female": 0,
                "total_young": 0,
                "total_adult": 0,
                "total_elderly": 0,
            },
            "camera_breakdown": [],
            "error": str(e),
        }

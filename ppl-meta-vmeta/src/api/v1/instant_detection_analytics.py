"""Instant-detection analytics endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_user, get_db_connection
from services.instant_detection_approximation import (
    ApproximationParams,
    cluster_sightings,
    normalize_sightings,
    summarize_clusters,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/instant-detection/approx-people",
    summary="Approximate unique people seen by instant detection",
    description="Returns heuristic person-group approximations for one camera and time range using persisted instant-detection appearances.",
)
async def get_instant_detection_approx_people(
    camera_id: str = Query(..., description="Camera device identifier"),
    start_time: datetime = Query(..., description="Inclusive range start"),
    end_time: datetime = Query(..., description="Inclusive range end"),
    time_window_seconds: int = Query(12, ge=1, le=300),
    center_distance_px: int = Query(120, ge=1, le=2000),
    size_ratio_tolerance: float = Query(0.35, ge=0.0, le=1.0),
    min_confidence: float = Query(0.50, ge=0.0, le=1.0),
    use_mvr_hint: bool = Query(True),
    include_members: bool = Query(False),
    db_connection=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    params = ApproximationParams(
        time_window_seconds=time_window_seconds,
        center_distance_px=center_distance_px,
        size_ratio_tolerance=size_ratio_tolerance,
        min_confidence=min_confidence,
        use_mvr_hint=use_mvr_hint,
    )
    requester = current_user.get("email") or current_user.get("user_uuid") or "unknown"

    query = """
    SELECT
        ts.camera_device_id,
        iva.source_session_uuid,
        iva.individual_uuid,
        iva.person_object_uuid,
        iva.start_timestamp,
        iva.end_timestamp,
        iva.confidence,
        iva.quality_score,
        iva.representative_faces,
        i.age_estimate,
        i.gender_estimate,
        imm.mvr_people_uuid
    FROM individual_video_appearances iva
    JOIN tracking_sessions ts
      ON ts.session_uuid = iva.source_session_uuid
    JOIN individuals i
      ON i.individual_uuid = iva.individual_uuid
    LEFT JOIN individual_mvr_mapping imm
      ON imm.individual_uuid = iva.individual_uuid
    WHERE ts.source_type = 'instant_detection'
      AND ts.camera_device_id = $1
      AND iva.start_timestamp >= $2
      AND iva.start_timestamp <= $3
    ORDER BY iva.start_timestamp ASC
    """

    rows = await db_connection.fetch(query, camera_id, start_time, end_time)
    raw_rows: List[Dict[str, Any]] = [dict(row) for row in rows]
    sightings = normalize_sightings(raw_rows, params)
    clusters = cluster_sightings(sightings, params)
    people = summarize_clusters(clusters, include_members)

    logger.info(
        "📊 Instant detection approximation requester=%s camera=%s range=%s..%s raw=%s filtered=%s approx=%s",
        requester,
        camera_id,
        start_time.isoformat(),
        end_time.isoformat(),
        len(raw_rows),
        len(sightings),
        len(people),
    )

    return {
        "success": True,
        "camera_id": camera_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "approx_unique_people": len(people),
        "total_sightings": len(sightings),
        "raw_rows_considered": len(raw_rows),
        "parameters": {
            "time_window_seconds": params.time_window_seconds,
            "center_distance_px": params.center_distance_px,
            "size_ratio_tolerance": params.size_ratio_tolerance,
            "min_confidence": params.min_confidence,
            "use_mvr_hint": params.use_mvr_hint,
            "include_members": include_members,
        },
        "people": people,
    }
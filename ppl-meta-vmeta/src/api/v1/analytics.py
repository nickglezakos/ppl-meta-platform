"""
vmeta Service Analytics API
Person movement analytics and spatial analysis.
"""

import logging
import os
import uuid as uuid_mod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()

MEDIA_SERVICE_URL = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Camera Demographics Search models
# ---------------------------------------------------------------------------

class CameraDemographicsSearchRequest(BaseModel):
    """Request model for searching demographics across cameras."""
    camera_ids: List[str] = Field(..., min_length=1, description="Camera / collection IDs to query")
    start_time: datetime = Field(..., description="Search window start (ISO 8601)")
    end_time: datetime = Field(..., description="Search window end (ISO 8601)")


class CameraDemographicsSearchResponse(BaseModel):
    """Aggregated demographics for the requested cameras and time window."""
    camera_ids: List[str]
    search_window: Dict[str, str]
    people_count: int
    demographics: Dict[str, float]
    search_session_uuid: str


@router.get("/demographics")
async def get_demographics_breakdown(
    start_time: datetime = Query(..., description="Start time for filtering (ISO format)"),
    end_time: datetime = Query(..., description="End time for filtering (ISO format)"),
    collection_name: Optional[str] = Query(None, description="Optional collection name filter"),
    db_connection=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get demographics breakdown (gender and age distribution) for MVR people.
    
    Returns demographics aggregated from MVR people created in the specified time range.
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        collection_name: Optional collection filter
        db_connection: Database connection
        current_user: Authenticated user
        
    Returns:
        Dict with gender_distribution, age_distribution, and completeness stats
    """
    # Convert times to local timezone (same as quality_metrics endpoint)
    from datetime import timezone as tz
    import pytz
    
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=tz.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=tz.utc)
    
    local_tz = pytz.timezone('Europe/Athens')
    start_time_local = start_time.astimezone(local_tz).replace(tzinfo=None)
    end_time_local = end_time.astimezone(local_tz).replace(tzinfo=None)
    
    # Get MVR people demographics from database
    demographics_query = """
    SELECT 
        gender,
        age_min,
        age_max
    FROM mvr_people
    WHERE created_at >= $1
        AND created_at <= $2
        AND is_orphaned = false
        AND merged_into_mvr_uuid IS NULL
    """
    
    mvr_demographics = await db_connection.fetch(
        demographics_query, start_time_local, end_time_local
    )
    
    total_mvr_people = len(mvr_demographics)
    
    # Count MVR people with demographics
    mvr_with_gender = sum(1 for m in mvr_demographics if m['gender'] is not None)
    mvr_with_age = sum(
        1 for m in mvr_demographics 
        if m['age_min'] is not None and m['age_max'] is not None
    )
    
    # Count gender distribution
    gender_counts = {"Male": 0, "Female": 0, "Unknown": 0}
    for m in mvr_demographics:
        gender = m['gender']
        if gender == "Male":
            gender_counts["Male"] += 1
        elif gender == "Female":
            gender_counts["Female"] += 1
        else:
            gender_counts["Unknown"] += 1
    
    # Count age distribution
    age_ranges = {
        "0-17": 0,
        "18-24": 0,
        "25-34": 0,
        "35-44": 0,
        "45-54": 0,
        "55-64": 0,
        "65+": 0,
        "Unknown": 0
    }
    
    for m in mvr_demographics:
        age_min = m['age_min']
        age_max = m['age_max']
        
        if age_min is None or age_max is None:
            age_ranges["Unknown"] += 1
        else:
            # Use average age for classification
            avg_age = (age_min + age_max) / 2
            if avg_age < 18:
                age_ranges["0-17"] += 1
            elif avg_age < 25:
                age_ranges["18-24"] += 1
            elif avg_age < 35:
                age_ranges["25-34"] += 1
            elif avg_age < 45:
                age_ranges["35-44"] += 1
            elif avg_age < 55:
                age_ranges["45-54"] += 1
            elif avg_age < 65:
                age_ranges["55-64"] += 1
            else:
                age_ranges["65+"] += 1
    
    return {
        "total_mvr_people": total_mvr_people,
        "mvr_with_gender": mvr_with_gender,
        "mvr_with_age": mvr_with_age,
        "gender_distribution": gender_counts,
        "age_distribution": age_ranges,
        "completeness": {
            "gender_percentage": round(
                (mvr_with_gender / total_mvr_people * 100) if total_mvr_people > 0 else 0, 2
            ),
            "age_percentage": round(
                (mvr_with_age / total_mvr_people * 100) if total_mvr_people > 0 else 0, 2
            )
        }
    }


@router.post(
    "/cameras/demographics-search",
    response_model=CameraDemographicsSearchResponse,
    summary="Aggregate demographics for cameras over a time window",
)
async def camera_demographics_search(
    body: CameraDemographicsSearchRequest,
    request: Request,
    db_connection=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
) -> CameraDemographicsSearchResponse:
    """
    Return aggregated demographics (gender %, age %) for all unique individuals
    detected by the specified cameras within a time window.

    Does NOT require an individual group or face matching — works on raw MVR
    people data linked through video appearances.
    """
    auth_token = request.headers.get("Authorization")
    start_time = body.start_time.replace(tzinfo=None) if body.start_time.tzinfo else body.start_time
    end_time = body.end_time.replace(tzinfo=None) if body.end_time.tzinfo else body.end_time

    # Step 1: Collect video UUIDs from the media service for each camera/collection
    all_video_uuids: List[str] = []
    headers: Dict[str, str] = {}
    if auth_token:
        token_value = auth_token.replace("Bearer ", "").strip() if auth_token.startswith("Bearer ") else auth_token
        headers["Authorization"] = f"Bearer {token_value}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        for camera_id in body.camera_ids:
            params = {
                "collection": camera_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "page_size": 500,
            }
            try:
                resp = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/search",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                videos = resp.json()
                if isinstance(videos, list):
                    all_video_uuids.extend(str(v["uuid"]) for v in videos)
            except Exception as exc:
                logger.warning("Failed to fetch videos for camera %s: %s", camera_id, exc)

    if not all_video_uuids:
        return CameraDemographicsSearchResponse(
            camera_ids=body.camera_ids,
            search_window={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
            people_count=0,
            demographics={
                "percent_male": 0.0,
                "percent_female": 0.0,
                "percent_age_0_12": 0.0,
                "percent_age_13_17": 0.0,
                "percent_age_18_24": 0.0,
                "percent_age_25_34": 0.0,
                "percent_age_35_44": 0.0,
                "percent_age_45_54": 0.0,
                "percent_age_55_64": 0.0,
                "percent_age_65_plus": 0.0,
            },
            search_session_uuid=str(uuid_mod.uuid4()),
        )

    # Step 2: Find distinct super-individuals from those videos and get demographics
    query = """
    WITH video_individuals AS (
        SELECT DISTINCT iva.individual_uuid
        FROM individual_video_appearances iva
        WHERE iva.video_uuid = ANY($1::uuid[])
    ),
    mapped_mvr AS (
        SELECT DISTINCT imm.mvr_people_uuid
        FROM video_individuals vi
        JOIN individual_mvr_mapping imm ON imm.individual_uuid = vi.individual_uuid
    ),
    resolved AS (
        -- Non-orphaned / non-merged
        SELECT mm.mvr_people_uuid
        FROM mapped_mvr mm
        JOIN mvr_people mp ON mp.mvr_people_uuid = mm.mvr_people_uuid
        WHERE mp.is_orphaned = false AND mp.merged_into_mvr_uuid IS NULL
        UNION
        -- Orphaned → follow merge
        SELECT mp.merged_into_mvr_uuid AS mvr_people_uuid
        FROM mapped_mvr mm
        JOIN mvr_people mp ON mp.mvr_people_uuid = mm.mvr_people_uuid
        WHERE mp.merged_into_mvr_uuid IS NOT NULL
    )
    SELECT DISTINCT sp.gender, sp.age_min, sp.age_max
    FROM resolved r
    JOIN mvr_people sp ON sp.mvr_people_uuid = r.mvr_people_uuid
    """

    rows = await db_connection.fetch(query, all_video_uuids)
    total = len(rows)

    if total == 0:
        return CameraDemographicsSearchResponse(
            camera_ids=body.camera_ids,
            search_window={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
            people_count=0,
            demographics={
                "percent_male": 0.0,
                "percent_female": 0.0,
                "percent_age_0_12": 0.0,
                "percent_age_13_17": 0.0,
                "percent_age_18_24": 0.0,
                "percent_age_25_34": 0.0,
                "percent_age_35_44": 0.0,
                "percent_age_45_54": 0.0,
                "percent_age_55_64": 0.0,
                "percent_age_65_plus": 0.0,
            },
            search_session_uuid=str(uuid_mod.uuid4()),
        )

    # Step 3: Aggregate demographics
    male = female = 0
    age_buckets = {
        "percent_age_0_12": 0,
        "percent_age_13_17": 0,
        "percent_age_18_24": 0,
        "percent_age_25_34": 0,
        "percent_age_35_44": 0,
        "percent_age_45_54": 0,
        "percent_age_55_64": 0,
        "percent_age_65_plus": 0,
    }

    for row in rows:
        gender = (row["gender"] or "").strip()
        if gender == "Male":
            male += 1
        elif gender == "Female":
            female += 1

        age_min = row["age_min"]
        age_max = row["age_max"]
        if age_min is not None and age_max is not None:
            avg = (age_min + age_max) / 2
            if avg < 13:
                age_buckets["percent_age_0_12"] += 1
            elif avg < 18:
                age_buckets["percent_age_13_17"] += 1
            elif avg < 25:
                age_buckets["percent_age_18_24"] += 1
            elif avg < 35:
                age_buckets["percent_age_25_34"] += 1
            elif avg < 45:
                age_buckets["percent_age_35_44"] += 1
            elif avg < 55:
                age_buckets["percent_age_45_54"] += 1
            elif avg < 65:
                age_buckets["percent_age_55_64"] += 1
            else:
                age_buckets["percent_age_65_plus"] += 1

    demographics: Dict[str, float] = {
        "percent_male": round(male / total * 100, 1),
        "percent_female": round(female / total * 100, 1),
    }
    for bucket, count in age_buckets.items():
        demographics[bucket] = round(count / total * 100, 1)

    session_uuid = str(uuid_mod.uuid4())
    logger.info(
        "Camera demographics search: cameras=%s people=%d session=%s",
        body.camera_ids, total, session_uuid,
    )

    return CameraDemographicsSearchResponse(
        camera_ids=body.camera_ids,
        search_window={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
        people_count=total,
        demographics=demographics,
        search_session_uuid=session_uuid,
    )


@router.post("/person-routes")
async def analyze_person_routes(analytics_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze person movement routes and patterns.

    Args:
        analytics_request: Analytics computation parameters

    Returns:
        Dict containing movement analytics results
    """
    return {
        "person_routes": [],
        "movement_statistics": {
            "total_distance": 0,
            "average_velocity": 0,
            "time_in_frame": 0,
        },
        "status": "completed",
    }


@router.get("/heatmap")
async def generate_heatmap(session_uuid: str = None) -> Dict[str, Any]:
    """
    Generate spatial heatmap for person detection.

    Args:
        session_uuid: Optional session filter

    Returns:
        Dict containing heatmap data
    """
    return {
        "heatmap_data": [],
        "grid_size": {"width": 0, "height": 0},
        "session_uuid": session_uuid,
        "generated_at": "2025-10-03T12:00:00Z",
    }

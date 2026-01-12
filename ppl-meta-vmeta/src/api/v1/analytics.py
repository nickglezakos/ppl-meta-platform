"""
vmeta Service Analytics API
Person movement analytics and spatial analysis.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_user, get_db_connection

router = APIRouter()


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

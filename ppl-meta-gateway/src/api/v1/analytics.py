"""
Analytics endpoints for MVR people detection insights.

Aggregates camera MVR count data to provide analytics dashboard metrics.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
import httpx

from fastapi import APIRouter, Depends, Query, Request, HTTPException

from core.auth import get_current_user
from core.redis_client import cache_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Service URLs
CAMERAS_SERVICE_URL = "http://localhost:8005"
MEDIA_SERVICE_URL = "http://localhost:8000"
VMETA_SERVICE_URL = "http://localhost:8008"


def _normalize_source_type(source_type: Optional[str]) -> str:
    """Normalize source_type parameter to database column value."""
    if source_type in (None, "recording", "recording_pipeline"):
        return "recording_pipeline"
    if source_type in ("instant_detection",):
        return "instant_detection"
    return "recording_pipeline"  # Safe default


def _parse_time_filter(
    time_filter: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    """
    Parse time filter string into start and end datetime range.
    
    When time_filter is 'custom', start_date and end_date must be provided as ISO 8601 strings.
    
    Args:
        time_filter: One of 'today', 'last_hour', 'last_3_hours', 'last_week', 'last_month', 'custom'
        start_date: ISO 8601 datetime string (required when time_filter='custom')
        end_date: ISO 8601 datetime string (required when time_filter='custom')
    
    Returns:
        Tuple of (start_time, end_time)
    """
    now = datetime.now()
    
    if time_filter == "custom":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required when time_filter is 'custom'")
        start_time = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
        end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None)
        return start_time, end_time
    elif time_filter == "today":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif time_filter == "last_hour":
        start_time = now - timedelta(hours=1)
        end_time = now
    elif time_filter == "last_3_hours":
        start_time = now - timedelta(hours=3)
        end_time = now
    elif time_filter == "last_week":
        start_time = now - timedelta(days=7)
        end_time = now
    elif time_filter == "last_month":
        start_time = now - timedelta(days=30)
        end_time = now
    else:
        raise ValueError(
            f"Invalid time_filter: {time_filter}. "
            f"Must be one of: today, last_hour, last_3_hours, last_week, last_month, custom"
        )
    
    return start_time, end_time


def _get_collection_identifier(collection: Dict) -> Optional[str]:
    """Return stable collection identifier (UUID-first)."""
    for key in ("uuid", "collection_uuid", "camera_uuid", "id", "collection_name", "name"):
        value = collection.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _get_collection_display_name(collection: Dict) -> str:
    """Return collection display name for UI/debug output."""
    return (
        str(collection.get("name") or "").strip()
        or str(collection.get("collection_name") or "").strip()
        or _get_collection_identifier(collection)
        or "Unknown Collection"
    )


def _get_collection_filter_keys(collection: Dict) -> Set[str]:
    """Return all acceptable identifiers for matching incoming filter values."""
    keys: Set[str] = set()
    for key in (
        "uuid",
        "collection_uuid",
        "camera_uuid",
        "id",
        "collection_name",
        "name",
        "camera_device_id",
        "device_id",
    ):
        value = collection.get(key)
        if value is not None and str(value).strip():
            keys.add(str(value).strip())
    return keys


def _collection_matches_selected_ids(collection: Dict, selected_ids: List[str]) -> bool:
    if not selected_ids:
        return True
    selected = {str(value).strip() for value in selected_ids if str(value).strip()}
    if not selected:
        return True
    return bool(_get_collection_filter_keys(collection).intersection(selected))


def _filter_demographics_count(
    demographics_data: Dict,
    total_count: int,
    selected_genders: Optional[List[str]],
    selected_age_groups: Optional[List[str]],
) -> int:
    """
    Recompute people count based on selected gender/age filters.
    
    When filters are active, returns only the count of people matching ALL active filter criteria.
    Uses the demographic breakdown from the MVR counter response.
    
    Args:
        demographics_data: Demographics dict with total_male, total_female, total_young, etc.
        total_count: Original unfiltered count
        selected_genders: List of genders to include (e.g. ['male']) or None for all
        selected_age_groups: List of age groups to include (e.g. ['young', 'adult']) or None for all
        
    Returns:
        Filtered count
    """
    if not demographics_data:
        return total_count
    
    has_gender_filter = selected_genders and len(selected_genders) > 0
    has_age_filter = selected_age_groups and len(selected_age_groups) > 0
    
    if not has_gender_filter and not has_age_filter:
        return total_count
    
    # Compute gender-filtered count
    if has_gender_filter:
        gender_count = 0
        for g in selected_genders:
            gender_count += demographics_data.get(f"total_{g}", 0)
    else:
        gender_count = total_count
    
    # Compute age-filtered count
    if has_age_filter:
        age_count = 0
        for a in selected_age_groups:
            age_count += demographics_data.get(f"total_{a}", 0)
    else:
        age_count = total_count
    
    # When both filters are present, estimate intersection using proportions
    # (assumes independence between gender and age distributions)
    if has_gender_filter and has_age_filter and total_count > 0:
        gender_ratio = gender_count / total_count
        return int(age_count * gender_ratio)
    elif has_gender_filter:
        return gender_count
    else:
        return age_count


async def _get_instant_detection_summary(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    genders: Optional[str],
    age_groups: Optional[str],
) -> Dict:
    """Fetch analytics summary from VMeta tracking-sessions/summary for instant detection data."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        logger.error(f"Invalid time filter for instant detection summary: {e}")
        return _empty_summary(time_filter, error=str(e))

    # Determine camera device IDs to query
    camera_device_ids: Optional[str] = None
    if collection_ids:
        camera_device_ids = collection_ids  # Pass through comma-separated
    else:
        # Get all collections from Media to discover camera_device_ids
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    params={"limit": 1000},
                )
                if resp.status_code == 200:
                    collections = resp.json()
                    device_ids = []
                    for col in collections:
                        did = col.get("camera_device_id") or col.get("device_id")
                        if did:
                            device_ids.append(str(did))
                    if device_ids:
                        camera_device_ids = ",".join(device_ids)
        except Exception as e:
            logger.warning(f"Could not fetch collections for instant detection summary: {e}")

    # Call VMeta tracking-sessions/summary
    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if camera_device_ids:
        params["camera_device_ids"] = camera_device_ids

    logger.info(f"📊 Instant detection summary: calling VMeta tracking-sessions/summary with params={params}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta tracking-sessions/summary returned {resp.status_code}: {resp.text[:300]}")
                return _empty_summary(time_filter, error=f"VMeta returned {resp.status_code}")

            data = resp.json()
    except Exception as e:
        logger.error(f"Error calling VMeta tracking-sessions/summary: {e}")
        return _empty_summary(time_filter, error=str(e))

    # Parse demographic filters
    selected_genders = [g.strip() for g in genders.split(",") if g.strip()] if genders else None
    selected_age_groups = [a.strip() for a in age_groups.split(",") if a.strip()] if age_groups else None

    # Build demographics from VMeta response
    vmeta_demographics = data.get("demographics", {})
    gender_male = vmeta_demographics.get("total_male", 0)
    gender_female = vmeta_demographics.get("total_female", 0)
    age_young = vmeta_demographics.get("total_young", 0)
    age_adult = vmeta_demographics.get("total_adult", 0)
    age_elderly = vmeta_demographics.get("total_elderly", 0)

    total_people = data.get("total_mvr_people", 0)

    # Apply demographic filters
    if selected_genders:
        if "male" not in selected_genders:
            gender_male = 0
        if "female" not in selected_genders:
            gender_female = 0
    if selected_age_groups:
        if "young" not in selected_age_groups:
            age_young = 0
        if "adult" not in selected_age_groups:
            age_adult = 0
        if "elderly" not in selected_age_groups:
            age_elderly = 0

    if selected_genders or selected_age_groups:
        total_people = _filter_demographics_count(
            vmeta_demographics, total_people, selected_genders, selected_age_groups
        )

    total_gender = gender_male + gender_female
    total_age = age_young + age_adult + age_elderly

    demographics = {
        "gender": {
            "male": gender_male,
            "female": gender_female,
            "male_percentage": round((gender_male / total_gender * 100) if total_gender > 0 else 0, 1),
            "female_percentage": round((gender_female / total_gender * 100) if total_gender > 0 else 0, 1),
        },
        "age": {
            "young": age_young,
            "adult": age_adult,
            "elderly": age_elderly,
            "young_percentage": round((age_young / total_age * 100) if total_age > 0 else 0, 1),
            "adult_percentage": round((age_adult / total_age * 100) if total_age > 0 else 0, 1),
            "elderly_percentage": round((age_elderly / total_age * 100) if total_age > 0 else 0, 1),
        },
    }

    # Build camera breakdown
    camera_breakdown = []
    for cam in data.get("camera_breakdown", []):
        camera_breakdown.append({
            "camera_id": cam.get("camera_device_id", ""),
            "camera_name": cam.get("camera_device_id", ""),
            "count": cam.get("total_mvr_people", 0),
            "video_count": 0,  # Not applicable for instant detection
            "demographics": None,
            "last_detection": cam.get("last_detection"),
            "cached": False,
        })

    active_cameras = data.get("active_cameras", 0)

    logger.info(
        f"✅ Instant detection summary: {total_people} people, "
        f"{active_cameras} cameras, {data.get('session_count', 0)} sessions"
    )

    return {
        "total_people": total_people,
        "active_cameras": active_cameras,
        "total_videos": 0,  # Instant detection doesn't produce videos
        "last_detection": data.get("last_detection"),
        "time_filter": time_filter,
        "demographics": demographics,
        "camera_breakdown": camera_breakdown,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cached": False,
        "source_type": "instant_detection",
    }


def _empty_summary(time_filter: str, error: Optional[str] = None) -> Dict:
    """Return an empty analytics summary response."""
    result = {
        "total_people": 0,
        "active_cameras": 0,
        "total_videos": 0,
        "last_detection": None,
        "time_filter": time_filter,
        "demographics": {
            "gender": {"male": 0, "female": 0, "male_percentage": 0.0, "female_percentage": 0.0},
            "age": {"young": 0, "adult": 0, "elderly": 0, "young_percentage": 0.0, "adult_percentage": 0.0, "elderly_percentage": 0.0},
        },
        "camera_breakdown": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cached": False,
    }
    if error:
        result["error"] = error
    return result


@router.get(
    "/analytics/summary",
    summary="Get aggregated analytics summary",
    description="Aggregate MVR people detection data across multiple collections with demographic breakdowns",
)
async def get_analytics_summary(
    request: Request,
    time_filter: str = Query("today", description="Time period filter: today, last_hour, last_3_hours, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    force_refresh: bool = Query(False, description="Bypass cache and get live data"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    genders: Optional[str] = Query(None, description="Comma-separated gender filter: male,female"),
    age_groups: Optional[str] = Query(None, description="Comma-separated age group filter: young,adult,elderly"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'. Default: recording_pipeline"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get aggregated analytics summary across collections.
    
    Leverages existing camera MVR count endpoint and aggregates:
    - Total people count
    - Active collections (collections with detections)
    - Total videos analyzed
    - Aggregated demographics (gender and age breakdowns)
    - Per-collection breakdown
    
    Args:
        time_filter: Time period (today, last_hour, last_3_hours, last_week, last_month)
        collection_ids: Optional comma-separated collection IDs, or None for all collections
        force_refresh: Whether to bypass cache
        current_user: Authenticated user from JWT token
        
    Returns:
        Aggregated analytics summary with total counts, demographics, and collection breakdown
    """
    try:
        # Extract auth token for service calls
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        effective_source = _normalize_source_type(source_type)
        
        # --- Instant detection path: call VMeta tracking-sessions/summary ---
        if effective_source == "instant_detection":
            return await _get_instant_detection_summary(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                start_date=start_date,
                end_date=end_date,
                genders=genders,
                age_groups=age_groups,
            )
        
        # Note: No analytics-level caching needed - the camera counter endpoint
        # already caches individual collection results with 10-minute TTL
        
        # Get list of collections to query
        collection_display_lookup: Dict[str, str] = {}
        if collection_ids:
            target_collection_ids = [cid.strip() for cid in collection_ids.split(",")]
        else:
            # Get all collections from Media service (where videos/collections are actually stored)
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={"limit": 1000}  # Get all collections
                    )
                    if response.status_code == 200:
                        collections = response.json()
                        for col in collections:
                            collection_id = _get_collection_identifier(col)
                            if collection_id:
                                collection_display_lookup[collection_id] = _get_collection_display_name(col)
                        target_collection_ids = [
                            _get_collection_identifier(col)
                            for col in collections
                            if _get_collection_identifier(col)
                        ]
                        logger.info(f"📊 Found {len(target_collection_ids)} collections from Media service")
                    else:
                        logger.warning(f"Failed to get collections from Media service: {response.status_code}")
                        target_collection_ids = []
            except Exception as e:
                logger.error(f"Error getting collections from Media service: {e}")
                target_collection_ids = []
        
        if not target_collection_ids:
            logger.warning("⚠️ No collections found")
            return {
                "total_people": 0,
                "active_cameras": 0,
                "total_videos": 0,
                "last_detection": None,
                "time_filter": time_filter,
                "demographics": {
                    "gender": {"male": 0, "female": 0, "male_percentage": 0.0, "female_percentage": 0.0},
                    "age": {"young": 0, "adult": 0, "elderly": 0, "young_percentage": 0.0, "adult_percentage": 0.0, "elderly_percentage": 0.0},
                },
                "camera_breakdown": [],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "cached": False,
            }
        
        logger.info(f"📊 Computing analytics summary for {len(target_collection_ids)} collections (timeFilter: {time_filter})")
        logger.info(f"📋 Collections to query: {target_collection_ids}")
        
        # Parse demographic filters
        selected_genders = [g.strip() for g in genders.split(",") if g.strip()] if genders else None
        selected_age_groups = [a.strip() for a in age_groups.split(",") if a.strip()] if age_groups else None
        
        # Initialize aggregation variables
        total_people = 0
        active_collections = 0
        total_videos = 0
        last_detection: Optional[datetime] = None
        demographics = {
            "gender": {"male": 0, "female": 0, "male_percentage": 0.0, "female_percentage": 0.0},
            "age": {"young": 0, "adult": 0, "elderly": 0, "young_percentage": 0.0, "adult_percentage": 0.0, "elderly_percentage": 0.0},
        }
        collection_breakdown = []
        
        # Aggregate data from each collection
        # Use the existing cached camera counter endpoint to get MVR counts
        for idx, collection_id in enumerate(target_collection_ids, 1):
            try:
                logger.info(f"🔄 [{idx}/{len(target_collection_ids)}] Fetching count for collection: {collection_id}, time_filter: {time_filter}")
                
                async with httpx.AsyncClient() as client:
                    # Call the cached camera counter endpoint (reuses all caching logic)
                    counter_url = f"http://localhost:8080/api/v1/cameras/{collection_id}/mvr-count"
                    counter_params = {
                        "time_filter": time_filter,
                        "force_refresh": False  # Use cache when available
                    }
                    if time_filter == "custom" and start_date and end_date:
                        counter_params["start_date"] = start_date
                        counter_params["end_date"] = end_date
                    response = await client.get(
                        counter_url,
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params=counter_params,
                        timeout=30.0
                    )
                    
                    logger.info(f"📡 [{idx}/{len(target_collection_ids)}] Response status for {collection_id}: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.warning(f"❌ [{idx}/{len(target_collection_ids)}] Failed: {response.status_code} - {response.text[:200]}")
                        # Include with zero counts
                        collection_breakdown.append({
                            "collection_id": collection_id,
                            "collection_name": collection_display_lookup.get(collection_id, collection_id),
                            "count": 0,
                            "video_count": 0,
                            "demographics": None,
                            "last_detection": None,
                            "cached": False,
                        })
                        continue
                    
                    collection_data = response.json()
                    count = collection_data.get("count", 0)
                    video_count = collection_data.get("video_count", 0)
                    
                    # Apply demographic filter if set
                    collection_demographics = collection_data.get("demographics", {})
                    if (selected_genders or selected_age_groups) and collection_demographics:
                        count = _filter_demographics_count(
                            collection_demographics, count, selected_genders, selected_age_groups
                        )
                    
                    logger.info(
                        f"✅ [{idx}/{len(target_collection_ids)}] Collection {collection_id}: "
                        f"count={count}, videos={video_count}, cached={collection_data.get('cached', False)}"
                    )
                    
                    # Count as active only if has detections
                    if count > 0:
                        active_collections += 1
                        logger.info(f"   🟢 Collection {collection_id} is ACTIVE (has detections)")
                    else:
                        logger.info(f"   ⚪ Collection {collection_id} is inactive (no detections)")
                    
                    # Always aggregate totals
                    total_people += count
                    total_videos += video_count
                    
                    logger.info(f"   📊 Running totals: people={total_people}, videos={total_videos}, active={active_collections}")
                    
                    # Aggregate demographics (only if present)
                    if collection_demographics:
                        demographics["gender"]["male"] += collection_demographics.get("total_male", 0)
                        demographics["gender"]["female"] += collection_demographics.get("total_female", 0)
                        demographics["age"]["young"] += collection_demographics.get("total_young", 0)
                        demographics["age"]["adult"] += collection_demographics.get("total_adult", 0)
                        logger.info(f"   👥 Aggregated demographics from {collection_id}")
                    
                    # Always add to collection breakdown
                    collection_breakdown.append({
                        "camera_id": collection_id,  # Frontend expects 'camera_id'
                        "camera_name": collection_display_lookup.get(collection_id, collection_id),
                        "count": count,
                        "video_count": video_count,
                        "demographics": collection_demographics if collection_demographics else None,
                        "last_detection": None,  # Not provided by counter endpoint
                        "cached": collection_data.get("cached", False),
                    })
                    
            except Exception as e:
                logger.error(f"❌ [{idx}/{len(target_collection_ids)}] Exception for collection {collection_id}: {e}", exc_info=True)
                # Include with zero counts on error
                collection_breakdown.append({
                    "camera_id": collection_id,  # Frontend expects 'camera_id'
                    "camera_name": collection_display_lookup.get(collection_id, collection_id),
                    "count": 0,
                    "video_count": 0,
                    "demographics": None,
                    "last_detection": None,
                    "cached": False,
                })
                continue
        
        # Calculate demographic percentages
        total_gender = demographics["gender"]["male"] + demographics["gender"]["female"]
        if total_gender > 0:
            demographics["gender"]["male_percentage"] = round((demographics["gender"]["male"] / total_gender) * 100, 1)
            demographics["gender"]["female_percentage"] = round((demographics["gender"]["female"] / total_gender) * 100, 1)
        
        total_age = demographics["age"]["young"] + demographics["age"]["adult"] + demographics["age"]["elderly"]
        if total_age > 0:
            demographics["age"]["young_percentage"] = round((demographics["age"]["young"] / total_age) * 100, 1)
            demographics["age"]["adult_percentage"] = round((demographics["age"]["adult"] / total_age) * 100, 1)
            demographics["age"]["elderly_percentage"] = round((demographics["age"]["elderly"] / total_age) * 100, 1)
        
        logger.info(
            f"🎯 FINAL AGGREGATION RESULTS: "
            f"total_people={total_people}, "
            f"active_collections={active_collections}, "
            f"total_videos={total_videos}, "
            f"collections_in_breakdown={len(collection_breakdown)}"
        )
        
        # Build response
        response = {
            "total_people": total_people,
            "active_cameras": active_collections,  # Keep field name for backwards compatibility
            "total_videos": total_videos,
            "last_detection": last_detection.isoformat() if last_detection else None,
            "time_filter": time_filter,
            "demographics": demographics,
            "camera_breakdown": collection_breakdown,  # Keep field name for backwards compatibility
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cached": False,
        }
        
        logger.info(f"✅ Analytics summary computed: {total_people} people, {active_collections} collections, {total_videos} videos")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to compute analytics summary: {e}", exc_info=True)
        # Return empty structure instead of error
        return {
            "total_people": 0,
            "active_cameras": 0,
            "total_videos": 0,
            "last_detection": None,
            "time_filter": time_filter,
            "demographics": {
                "gender": {"male": 0, "female": 0, "male_percentage": 0.0, "female_percentage": 0.0},
                "age": {"young": 0, "adult": 0, "elderly": 0, "young_percentage": 0.0, "adult_percentage": 0.0, "elderly_percentage": 0.0},
            },
            "camera_breakdown": [],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cached": False,
            "error": str(e),
        }


# ────────────────────────────────────────────────────────────────────
# Instant detection helper functions
# ────────────────────────────────────────────────────────────────────

async def _get_instant_detection_time_series(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    interval: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict:
    """Fetch time-series data from VMeta tracking-sessions/summary for instant detection."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        return {
            "time_filter": time_filter, "interval": interval,
            "start_time": None, "end_time": None,
            "data_points": [], "peak_count": 0, "peak_time": None,
            "average_count": 0.0, "total_count": 0, "error": str(e),
        }

    # Auto-select interval based on range
    range_hours = (end_time - start_time).total_seconds() / 3600
    if range_hours <= 72:
        interval = "hour"
    else:
        interval = "day"

    # Build camera_device_ids
    camera_device_ids = collection_ids  # Pass through if provided

    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if camera_device_ids:
        params["camera_device_ids"] = camera_device_ids

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta tracking-sessions/summary for time-series returned {resp.status_code}")
                data = {}
            else:
                data = resp.json()
    except Exception as e:
        logger.error(f"Error calling VMeta for instant detection time-series: {e}")
        data = {}

    total_count = data.get("total_mvr_people", 0)

    # Build time buckets and distribute count into the most recent bucket
    # (Same simplified approach as recording pipeline; VMeta doesn't provide per-bucket data yet)
    time_buckets = {}
    if interval == "hour":
        total_hours = max(1, int((end_time - start_time).total_seconds() / 3600) + 1)
        for i in range(total_hours):
            bucket_time = start_time + timedelta(hours=i)
            time_buckets[bucket_time.strftime("%Y-%m-%d %H:00")] = {
                "timestamp": bucket_time.isoformat(),
                "count": 0,
                "video_count": 0,
            }
    else:
        total_days = max(1, (end_time - start_time).days + 1)
        for i in range(total_days):
            bucket_time = start_time + timedelta(days=i)
            time_buckets[bucket_time.strftime("%Y-%m-%d")] = {
                "timestamp": bucket_time.replace(hour=0, minute=0, second=0).isoformat(),
                "count": 0,
                "video_count": 0,
            }

    if time_buckets and total_count > 0:
        last_bucket_key = list(time_buckets.keys())[-1]
        time_buckets[last_bucket_key]["count"] = total_count

    data_points = list(time_buckets.values())
    counts = [dp["count"] for dp in data_points]
    peak_count = max(counts) if counts else 0
    average_count = sum(counts) / len(counts) if counts else 0.0
    peak_time = None
    for dp in data_points:
        if dp["count"] == peak_count:
            peak_time = dp["timestamp"]
            break

    return {
        "time_filter": time_filter,
        "interval": interval,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data_points": data_points,
        "peak_count": peak_count,
        "peak_time": peak_time,
        "average_count": round(average_count, 2),
        "total_count": total_count,
        "source_type": "instant_detection",
    }


async def _get_instant_detection_demographics(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    genders: Optional[str],
    age_groups: Optional[str],
) -> Dict:
    """Fetch demographics from VMeta tracking-sessions/summary for instant detection."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if collection_ids:
        params["camera_device_ids"] = collection_ids

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta returned {resp.status_code} for instant detection demographics")
                raise HTTPException(status_code=500, detail="Failed to fetch instant detection demographics")
            data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching instant detection demographics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    vmeta_demo = data.get("demographics", {})
    total_male = vmeta_demo.get("total_male", 0)
    total_female = vmeta_demo.get("total_female", 0)
    total_unknown_gender = 0
    total_young = vmeta_demo.get("total_young", 0)
    total_adult = vmeta_demo.get("total_adult", 0)
    total_middle_aged = 0
    total_elderly = vmeta_demo.get("total_elderly", 0)
    total_unknown_age = 0

    # Apply filters
    selected_genders = [g.strip() for g in genders.split(",") if g.strip()] if genders else None
    selected_age_groups = [a.strip() for a in age_groups.split(",") if a.strip()] if age_groups else None

    if selected_genders:
        if "male" not in selected_genders:
            total_male = 0
        if "female" not in selected_genders:
            total_female = 0
    if selected_age_groups:
        if "young" not in selected_age_groups:
            total_young = 0
        if "adult" not in selected_age_groups:
            total_adult = 0
        if "elderly" not in selected_age_groups:
            total_elderly = 0

    total_people = total_male + total_female + total_unknown_gender

    male_pct = round((total_male / total_people * 100) if total_people > 0 else 0, 1)
    female_pct = round((total_female / total_people * 100) if total_people > 0 else 0, 1)

    total_age_people = total_young + total_adult + total_middle_aged + total_elderly + total_unknown_age
    young_pct = round((total_young / total_age_people * 100) if total_age_people > 0 else 0, 1)
    adult_pct = round((total_adult / total_age_people * 100) if total_age_people > 0 else 0, 1)
    elderly_pct = round((total_elderly / total_age_people * 100) if total_age_people > 0 else 0, 1)

    # Build per-camera breakdown from VMeta camera_breakdown
    camera_demographics = []
    for cam in data.get("camera_breakdown", []):
        cam_id = cam.get("camera_device_id", "")
        cam_people = cam.get("total_mvr_people", 0)
        if cam_people > 0:
            camera_demographics.append({
                "camera_id": cam_id,
                "camera_name": cam_id,
                "total_people": cam_people,
                "gender": {"male": 0, "female": 0, "unknown": 0, "male_percentage": 0.0, "female_percentage": 0.0},
                "age": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0,
                        "young_percentage": 0.0, "adult_percentage": 0.0, "middle_aged_percentage": 0.0, "elderly_percentage": 0.0},
            })

    return {
        "time_filter": time_filter,
        "total_people": total_people,
        "gender_distribution": {
            "male": total_male, "female": total_female, "unknown": total_unknown_gender,
            "male_percentage": male_pct, "female_percentage": female_pct, "unknown_percentage": 0.0,
        },
        "age_distribution": {
            "young": total_young, "adult": total_adult, "middle_aged": total_middle_aged,
            "elderly": total_elderly, "unknown": total_unknown_age,
            "young_percentage": young_pct, "adult_percentage": adult_pct,
            "middle_aged_percentage": 0.0, "elderly_percentage": elderly_pct, "unknown_percentage": 0.0,
        },
        "demographic_matrix": {
            "male": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
            "female": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
            "unknown": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
        },
        "camera_breakdown": camera_demographics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "instant_detection",
    }


async def _get_instant_detection_behavioral(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    genders: Optional[str],
    age_groups: Optional[str],
) -> Dict:
    """Fetch behavioral analytics from VMeta tracking-sessions/summary for instant detection."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if collection_ids:
        params["camera_device_ids"] = collection_ids

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta returned {resp.status_code} for instant detection behavioral")
                raise HTTPException(status_code=500, detail="Failed to fetch instant detection behavioral data")
            data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching instant detection behavioral: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    total_people = data.get("total_mvr_people", 0)

    # Initialize behavioral structures
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly_heatmap = {day: {hour: 0 for hour in range(24)} for day in days_of_week}
    daily_activity = {day: 0 for day in days_of_week}
    hourly_activity = {hour: 0 for hour in range(24)}

    # Distribute total_people into current time slot (simplified — same as recording path)
    if total_people > 0:
        now = datetime.utcnow()
        current_hour = now.hour
        current_day = days_of_week[now.weekday()]
        hourly_activity[current_hour] = total_people
        daily_activity[current_day] = total_people
        weekly_heatmap[current_day][current_hour] = total_people

    # Build camera comparison from camera_breakdown
    camera_comparison = []
    for cam in data.get("camera_breakdown", []):
        cam_id = cam.get("camera_device_id", "")
        cam_count = cam.get("total_mvr_people", 0)
        if cam_count > 0:
            camera_comparison.append({"camera_id": cam_id, "total_people": cam_count})
    camera_comparison.sort(key=lambda x: x["total_people"], reverse=True)

    peak_hours = sorted(
        [{"hour": h, "count": c, "time_label": f"{h:02d}:00 - {(h + 1) % 24:02d}:00"}
         for h, c in hourly_activity.items() if c > 0],
        key=lambda x: x["count"], reverse=True,
    )[:5]

    peak_days = sorted(
        [{"day": d, "count": c} for d, c in daily_activity.items() if c > 0],
        key=lambda x: x["count"], reverse=True,
    )[:3]

    visit_frequency = {
        "new_visitors": int(total_people * 0.6),
        "returning_visitors": int(total_people * 0.3),
        "frequent_visitors": int(total_people * 0.1),
    }

    return {
        "time_filter": time_filter,
        "total_detections": total_people,
        "active_cameras": len(camera_comparison),
        "weekly_heatmap": weekly_heatmap,
        "hourly_activity": hourly_activity,
        "daily_activity": daily_activity,
        "peak_hours": peak_hours,
        "peak_days": peak_days,
        "camera_comparison": camera_comparison[:5],
        "visit_frequency": visit_frequency,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "instant_detection",
    }


@router.get(
    "/analytics/cameras",
    summary="Get list of collections for analytics filtering",
    description="Returns list of all camera collections from Media service with basic metadata for analytics filter dropdown",
)
async def get_cameras_list(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> List[Dict]:
    """
    Get list of all collections for analytics filtering.
    
    Fetches collections from Media service (where videos are stored) instead of Cameras service.
    This ensures we only show collections that have actual video data.
    
    Returns collection metadata including:
    - id: Collection name (unique identifier)
    - name: Display name
    - collection_name: Collection identifier
    
    Args:
        request: FastAPI request object to extract auth headers
        current_user: Authenticated user from JWT token
        
    Returns:
        List of collection metadata dictionaries
    """
    try:
        # Extract auth token from request headers
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        # Get collections from Media service (where videos/collections are actually stored)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1000}  # Get all collections
            )
            
            if response.status_code == 200:
                collections = response.json()
                
                # Transform to match frontend expectations
                result = []
                for collection in collections:
                    collection_id = _get_collection_identifier(collection)
                    collection_name = _get_collection_display_name(collection)
                    if collection_id:
                        result.append({
                            "id": collection_id,
                            "uuid": str(collection.get("uuid")) if collection.get("uuid") is not None else collection_id,
                            "name": collection_name,
                            "collection_name": collection.get("collection_name") or collection_name,
                            "video_count": collection.get("video_count", 0),
                        })
                
                logger.info(f"✅ Returning {len(result)} collections from Media service")
                return result
            else:
                logger.error(f"Failed to get collections from Media service: {response.status_code} - {response.text}")
                return []
        
    except Exception as e:
        logger.error(f"❌ Failed to get collections list: {e}", exc_info=True)
        return []


@router.get(
    "/analytics/time-series",
    summary="Get time-series analytics with hourly/daily trends",
    description="Returns time-based analytics showing people count trends over time with hourly or daily granularity",
)
async def get_time_series_analytics(
    request: Request,
    time_filter: str = Query("today", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs", alias="camera_ids"),
    interval: str = Query("hour", description="Data interval: hour, day"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get time-series analytics with trend data.
    
    Returns people count data points over time for visualization in charts.
    Supports hourly intervals (for today/last 3 days) and daily intervals (for week/month).
    
    Args:
        time_filter: Time period (today, last_3_days, last_week, last_month)
        collection_ids: Optional comma-separated collection IDs
        interval: Data granularity (hour or day)
        current_user: Authenticated user from JWT token
        
    Returns:
        Time series data with data points, peak information, and averages
    """
    try:
        from datetime import timedelta
        from collections import defaultdict
        
        # Extract auth token
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        effective_source = _normalize_source_type(source_type)
        
        # --- Instant detection path ---
        if effective_source == "instant_detection":
            return await _get_instant_detection_time_series(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )
        
        # Determine date range based on time_filter
        now = datetime.utcnow()
        if time_filter == "custom" and start_date and end_date:
            start_time = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
            end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None)
            # Auto-select interval based on range
            range_days = (end_time - start_time).days
            interval = "hour" if range_days <= 3 else "day"
        elif time_filter == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
            interval = "hour"  # Force hourly for today
        elif time_filter == "last_3_days":
            start_time = now - timedelta(days=3)
            end_time = now
            interval = "hour"  # Hourly for 3 days
        elif time_filter == "last_week":
            start_time = now - timedelta(days=7)
            end_time = now
            interval = "day"  # Daily for week
        elif time_filter == "last_month":
            start_time = now - timedelta(days=30)
            end_time = now
            interval = "day"  # Daily for month
        else:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
            interval = "hour"
        
        logger.info(f"📊 Time-series analytics: {time_filter}, interval: {interval}, range: {start_time} to {end_time}")
        
        # Get target collections
        if collection_ids:
            target_collection_ids = [cid.strip() for cid in collection_ids.split(",")]
        else:
            # Get all collections
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={"limit": 1000}
                    )
                    if response.status_code == 200:
                        collections = response.json()
                        target_collection_ids = [
                            _get_collection_identifier(col)
                            for col in collections
                            if _get_collection_identifier(col)
                        ]
                    else:
                        target_collection_ids = []
            except Exception as e:
                logger.error(f"Error getting collections: {e}")
                target_collection_ids = []
        
        if not target_collection_ids:
            return {
                "time_filter": time_filter,
                "interval": interval,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "data_points": [],
                "peak_count": 0,
                "peak_time": None,
                "average_count": 0.0,
                "total_count": 0,
            }
        
        # Initialize data structure for time buckets
        if interval == "hour":
            # Create hourly buckets
            total_hours = int((end_time - start_time).total_seconds() / 3600) + 1
            time_buckets = {}
            for i in range(total_hours):
                bucket_time = start_time + timedelta(hours=i)
                time_buckets[bucket_time.strftime("%Y-%m-%d %H:00")] = {
                    "timestamp": bucket_time.isoformat(),
                    "count": 0,
                    "video_count": 0,
                }
        else:  # day interval
            # Create daily buckets
            total_days = (end_time - start_time).days + 1
            time_buckets = {}
            for i in range(total_days):
                bucket_time = start_time + timedelta(days=i)
                bucket_key = bucket_time.strftime("%Y-%m-%d")
                time_buckets[bucket_key] = {
                    "timestamp": bucket_time.replace(hour=0, minute=0, second=0).isoformat(),
                    "count": 0,
                    "video_count": 0,
                }
        
        # Query each collection and aggregate into time buckets
        # For now, we'll use the existing counter endpoint with different time filters
        # In a production system, you'd query the database directly with time buckets
        
        # For hourly data today, we can approximate by querying videos per hour
        # For simplicity, we'll aggregate the current counts into the most recent bucket
        
        logger.info(f"📊 Querying {len(target_collection_ids)} collections for time-series data")
        
        # Get current counts for each collection
        for collection_id in target_collection_ids:
            try:
                async with httpx.AsyncClient() as client:
                    # Use the appropriate time filter
                    if time_filter == "custom":
                        counter_time_filter = "custom"
                    elif time_filter == "today":
                        counter_time_filter = "today"
                    elif time_filter == "last_3_days":
                        counter_time_filter = "last_3_hours"  # Approximate
                    elif time_filter == "last_week":
                        counter_time_filter = "last_week"
                    else:
                        counter_time_filter = "last_month"
                    
                    counter_params = {"time_filter": counter_time_filter}
                    if counter_time_filter == "custom" and start_date and end_date:
                        counter_params["start_date"] = start_date
                        counter_params["end_date"] = end_date
                    response = await client.get(
                        f"http://localhost:8080/api/v1/cameras/{collection_id}/mvr-count",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params=counter_params,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        count = data.get("count", 0)
                        video_count = data.get("video_count", 0)
                        
                        # Add to the most recent time bucket
                        # This is a simplified approach - production would query actual timestamps
                        if time_buckets:
                            last_bucket_key = list(time_buckets.keys())[-1]
                            time_buckets[last_bucket_key]["count"] += count
                            time_buckets[last_bucket_key]["video_count"] += video_count
                            
            except Exception as e:
                logger.error(f"Error querying collection {collection_id}: {e}")
                continue
        
        # Convert to data points list
        data_points = list(time_buckets.values())
        
        # Calculate statistics
        counts = [dp["count"] for dp in data_points]
        total_count = sum(counts)
        peak_count = max(counts) if counts else 0
        average_count = total_count / len(counts) if counts else 0.0
        
        # Find peak time
        peak_time = None
        for dp in data_points:
            if dp["count"] == peak_count:
                peak_time = dp["timestamp"]
                break
        
        result = {
            "time_filter": time_filter,
            "interval": interval,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "data_points": data_points,
            "peak_count": peak_count,
            "peak_time": peak_time,
            "average_count": round(average_count, 2),
            "total_count": total_count,
        }
        
        logger.info(f"✅ Time-series: {len(data_points)} data points, peak: {peak_count}, avg: {average_count:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get time-series analytics: {e}", exc_info=True)
        return {
            "time_filter": time_filter,
            "interval": interval,
            "start_time": None,
            "end_time": None,
            "data_points": [],
            "peak_count": 0,
            "peak_time": None,
            "average_count": 0.0,
            "total_count": 0,
            "error": str(e),
        }


@router.get(
    "/analytics/demographics",
    summary="Get demographics breakdown analytics",
    description="Returns detailed demographic distribution data (gender, age) across cameras for Level 3 analytics",
)
async def get_demographics_breakdown(
    request: Request,
    time_filter: str = Query("today", description="Time filter: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs", alias="camera_ids"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    genders: Optional[str] = Query(None, description="Comma-separated gender filter: male,female"),
    age_groups: Optional[str] = Query(None, description="Comma-separated age group filter: young,adult,elderly"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get detailed demographic breakdowns (Level 3 Analytics).
    
    Returns:
        - Gender distribution (male, female, unknown counts and percentages)
        - Age distribution (young, adult, middle_aged, elderly counts and percentages)
        - Combined demographic matrix (gender x age breakdown)
        - Per-camera demographic breakdown
    """
    try:
        logger.info(f"Fetching demographics breakdown: time_filter={time_filter}, collection_ids={collection_ids}")
        
        # Get auth token from request
        auth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        effective_source = _normalize_source_type(source_type)
        
        # --- Instant detection path ---
        if effective_source == "instant_detection":
            return await _get_instant_detection_demographics(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                start_date=start_date,
                end_date=end_date,
                genders=genders,
                age_groups=age_groups,
            )
        
        # Parse collection IDs
        selected_collection_ids = None
        if collection_ids:
            selected_collection_ids = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]
            logger.info(f"📋 Demographics filtering by collection_ids: {selected_collection_ids}")
        else:
            logger.info(f"📋 Demographics fetching ALL collections (no filter provided)")
        
        # Get all collections from Media service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1000}
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch collections list: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch collections")
            
            all_cameras = response.json()
            logger.info(f"📊 Got {len(all_cameras)} total collections from Media service")
        
        # Filter cameras if specific ones requested
        if selected_collection_ids:
            before_filter = len(all_cameras)
            all_cameras = [
                cam for cam in all_cameras
                if _collection_matches_selected_ids(cam, selected_collection_ids)
            ]
            logger.info(f"🔍 Filtered {before_filter} collections down to {len(all_cameras)} matching filter")
            if len(all_cameras) > 0:
                logger.info(f"✅ Matched collections: [{', '.join(_get_collection_identifier(cam) or 'unknown' for cam in all_cameras)}]")
            else:
                logger.warning(
                    f"⚠️  NO collections matched filter! Available collections: "
                    f"{[_get_collection_identifier(cam) or _get_collection_display_name(cam) for cam in response.json()[:5]]}"
                )
        else:
            logger.info(f"📊 Processing all {len(all_cameras)} collections (no filter)")
        
        # Parse demographic filters
        selected_genders = [g.strip() for g in genders.split(",") if g.strip()] if genders else None
        selected_age_groups = [a.strip() for a in age_groups.split(",") if a.strip()] if age_groups else None
        
        # Initialize aggregated demographics
        total_male = 0
        total_female = 0
        total_unknown_gender = 0
        
        total_young = 0
        total_adult = 0
        total_middle_aged = 0
        total_elderly = 0
        total_unknown_age = 0
        
        # Combined demographic matrix: {gender: {age: count}}
        demographic_matrix = {
            "male": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
            "female": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
            "unknown": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
        }
        
        # Per-camera breakdown
        camera_demographics = []
        
        logger.info(f"🔄 Starting demographics aggregation for {len(all_cameras)} collections")
        
        # Aggregate demographics from each camera
        for idx, camera in enumerate(all_cameras, 1):
            camera_id = _get_collection_identifier(camera)
            if not camera_id:
                logger.warning(f"⚠️  Skipping camera #{idx} - no collection_name or name field")
                continue
            
            logger.info(f"📡 [{idx}/{len(all_cameras)}] Fetching demographics for: {camera_id}, time_filter: {time_filter}")
            
            try:
                # Fetch MVR count for this camera (using gateway proxy like basic analytics)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    counter_url = f"http://localhost:8080/api/v1/cameras/{camera_id}/mvr-count"
                    response = await client.get(
                        counter_url,
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={
                            "time_filter": time_filter,
                            "force_refresh": False,  # Use cache when available
                            **({"start_date": start_date, "end_date": end_date} if time_filter == "custom" and start_date and end_date else {})
                        }
                    )
                    
                    logger.info(f"📡 [{idx}/{len(all_cameras)}] MVR count response for {camera_id}: status={response.status_code}")
                    
                    if response.status_code != 200:
                        logger.warning(f"❌ [{idx}/{len(all_cameras)}] Failed to get MVR count for {camera_id}: {response.status_code}")
                        continue
                    
                    mvr_response = response.json()
                    logger.debug(f"📊 [{idx}/{len(all_cameras)}] MVR response for {camera_id}: {mvr_response}")
                
                # MVR count endpoint returns demographics directly (no "status" or "data" wrapper)
                demographics_data = mvr_response.get("demographics", {})
                total_people = mvr_response.get("count", 0)
                
                if total_people > 0:
                    logger.info(f"   📊 Camera {camera_id} has {total_people} people with demographics")
                    
                    # Gender breakdown - MVR count uses total_male, total_female (not nested)
                    male = demographics_data.get("total_male", 0)
                    female = demographics_data.get("total_female", 0)
                    unknown_gender = demographics_data.get("total_unknown_gender", 0)
                    
                    # Age breakdown - MVR count uses total_young, total_adult, etc (not nested)
                    young = demographics_data.get("total_young", 0)
                    adult = demographics_data.get("total_adult", 0)
                    middle_aged = demographics_data.get("total_middle_aged", 0)
                    elderly = demographics_data.get("total_elderly", 0)
                    unknown_age = demographics_data.get("total_unknown_age", 0)
                    
                    # Apply gender filter: zero out non-selected genders
                    if selected_genders:
                        if "male" not in selected_genders:
                            male = 0
                        if "female" not in selected_genders:
                            female = 0
                        unknown_gender = 0  # always exclude unknown when filtering
                    
                    # Apply age filter: zero out non-selected age groups
                    if selected_age_groups:
                        if "young" not in selected_age_groups:
                            young = 0
                        if "adult" not in selected_age_groups:
                            adult = 0
                        if "middle_aged" not in selected_age_groups:
                            middle_aged = 0
                        if "elderly" not in selected_age_groups:
                            elderly = 0
                        unknown_age = 0  # always exclude unknown when filtering
                    
                    # Recompute total_people when filters are active
                    if selected_genders or selected_age_groups:
                        total_people = _filter_demographics_count(
                            demographics_data, total_people, selected_genders, selected_age_groups
                        )
                    
                    total_male += male
                    total_female += female
                    total_unknown_gender += unknown_gender
                    
                    total_young += young
                    total_adult += adult
                    total_middle_aged += middle_aged
                    total_elderly += elderly
                    total_unknown_age += unknown_age
                    
                    # Build demographic matrix (simplified: assume proportional distribution)
                    # Note: This is an approximation since we don't have gender x age cross-tabulation from backend
                    if total_people > 0:
                        # Distribute based on marginal probabilities
                        gender_counts = {"male": male, "female": female, "unknown": unknown_gender}
                        age_counts = {"young": young, "adult": adult, "middle_aged": middle_aged, "elderly": elderly, "unknown": unknown_age}
                        
                        for g, gender_count in gender_counts.items():
                            gender_prob = gender_count / total_people if total_people > 0 else 0
                            
                            for a, age_count in age_counts.items():
                                age_prob = age_count / total_people if total_people > 0 else 0
                                
                                # Estimate combined count (assuming independence)
                                estimated_count = int(total_people * gender_prob * age_prob)
                                demographic_matrix[g][a] += estimated_count
                    
                    # Per-camera breakdown
                    camera_demographics.append({
                        "camera_id": camera_id,
                        "camera_name": camera.get("camera_name", camera_id),
                        "total_people": total_people,
                        "gender": {
                            "male": male,
                            "female": female,
                            "unknown": unknown_gender,
                            "male_percentage": round((male / total_people * 100) if total_people > 0 else 0, 1),
                            "female_percentage": round((female / total_people * 100) if total_people > 0 else 0, 1),
                        },
                        "age": {
                            "young": young,
                            "adult": adult,
                            "middle_aged": middle_aged,
                            "elderly": elderly,
                            "unknown": unknown_age,
                            "young_percentage": round((young / total_people * 100) if total_people > 0 else 0, 1),
                            "adult_percentage": round((adult / total_people * 100) if total_people > 0 else 0, 1),
                            "middle_aged_percentage": round((middle_aged / total_people * 100) if total_people > 0 else 0, 1),
                            "elderly_percentage": round((elderly / total_people * 100) if total_people > 0 else 0, 1),
                        },
                    })
                else:
                    logger.info(f"   ⚠️  Camera {camera_id} has 0 people - skipping demographics")
                    
            except Exception as cam_error:
                logger.error(f"❌ Error fetching demographics for camera {camera_id}: {cam_error}")
                continue
        
        # Calculate total people
        total_people = total_male + total_female + total_unknown_gender
        
        logger.info(f"✅ Demographics aggregation complete:")
        logger.info(f"   • Total people: {total_people} (male: {total_male}, female: {total_female}, unknown: {total_unknown_gender})")
        logger.info(f"   • Total age people: {total_young + total_adult + total_middle_aged + total_elderly + total_unknown_age}")
        logger.info(f"   • Cameras with data: {len(camera_demographics)}/{len(all_cameras)}")
        
        # Calculate percentages
        male_percentage = round((total_male / total_people * 100) if total_people > 0 else 0, 1)
        female_percentage = round((total_female / total_people * 100) if total_people > 0 else 0, 1)
        unknown_gender_percentage = round((total_unknown_gender / total_people * 100) if total_people > 0 else 0, 1)
        
        total_age_people = total_young + total_adult + total_middle_aged + total_elderly + total_unknown_age
        young_percentage = round((total_young / total_age_people * 100) if total_age_people > 0 else 0, 1)
        adult_percentage = round((total_adult / total_age_people * 100) if total_age_people > 0 else 0, 1)
        middle_aged_percentage = round((total_middle_aged / total_age_people * 100) if total_age_people > 0 else 0, 1)
        elderly_percentage = round((total_elderly / total_age_people * 100) if total_age_people > 0 else 0, 1)
        unknown_age_percentage = round((total_unknown_age / total_age_people * 100) if total_age_people > 0 else 0, 1)
        
        return {
            "time_filter": time_filter,
            "total_people": total_people,
            "gender_distribution": {
                "male": total_male,
                "female": total_female,
                "unknown": total_unknown_gender,
                "male_percentage": male_percentage,
                "female_percentage": female_percentage,
                "unknown_percentage": unknown_gender_percentage,
            },
            "age_distribution": {
                "young": total_young,
                "adult": total_adult,
                "middle_aged": total_middle_aged,
                "elderly": total_elderly,
                "unknown": total_unknown_age,
                "young_percentage": young_percentage,
                "adult_percentage": adult_percentage,
                "middle_aged_percentage": middle_aged_percentage,
                "elderly_percentage": elderly_percentage,
                "unknown_percentage": unknown_age_percentage,
            },
            "demographic_matrix": demographic_matrix,
            "camera_breakdown": camera_demographics,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in get_demographics_breakdown: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch demographics: {str(e)}")


@router.get(
    "/analytics/behavioral",
    summary="Get behavioral analytics insights",
    description="Analyze behavioral patterns including visit frequency, weekly heatmaps, and peak activity times",
)
async def get_behavioral_analytics(
    request: Request,
    time_filter: str = Query("last_week", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    genders: Optional[str] = Query(None, description="Comma-separated gender filter (male,female)"),
    age_groups: Optional[str] = Query(None, description="Comma-separated age groups (young,adult,middle_aged,elderly)"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get behavioral analytics including:
    - Visit frequency distribution (new, returning, frequent)
    - Weekly activity heatmap (day of week × hour of day)
    - Peak activity times
    - Camera comparison metrics
    
    Args:
        time_filter: Time period for analysis
        collection_ids: Optional comma-separated collection IDs
        current_user: Authenticated user from JWT token
        
    Returns:
        Behavioral analytics data with heatmaps and frequency patterns
    """
    try:
        logger.info(f"📊 Fetching behavioral analytics (time_filter: {time_filter})")
        
        # Parse demographic filters
        selected_genders = [g.strip().lower() for g in genders.split(",") if g.strip()] if genders else []
        selected_age_groups = [a.strip().lower() for a in age_groups.split(",") if a.strip()] if age_groups else []
        if selected_genders:
            logger.info(f"📋 Behavioral filtering by genders: {selected_genders}")
        if selected_age_groups:
            logger.info(f"📋 Behavioral filtering by age_groups: {selected_age_groups}")
        
        # Extract auth token
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        effective_source = _normalize_source_type(source_type)
        
        # --- Instant detection path ---
        if effective_source == "instant_detection":
            return await _get_instant_detection_behavioral(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                start_date=start_date,
                end_date=end_date,
                genders=genders,
                age_groups=age_groups,
            )
        
        # Parse collection IDs
        selected_collection_ids = None
        if collection_ids:
            selected_collection_ids = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]
            logger.info(f"📋 Behavioral filtering by collection_ids: {selected_collection_ids}")
        else:
            logger.info(f"📋 Behavioral fetching ALL collections (no filter provided)")
        
        # Get all collections from Media service (same pattern as demographics)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1000}
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch collections list: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch collections")
            
            all_cameras = response.json()
            logger.info(f"📊 Got {len(all_cameras)} total collections from Media service")
        
        # Filter cameras if specific ones requested
        if selected_collection_ids:
            before_filter = len(all_cameras)
            all_cameras = [
                cam for cam in all_cameras
                if _collection_matches_selected_ids(cam, selected_collection_ids)
            ]
            logger.info(f"🔍 Filtered {before_filter} collections down to {len(all_cameras)} matching filter")
            if len(all_cameras) > 0:
                logger.info(f"✅ Matched collections: [{', '.join(_get_collection_identifier(cam) or 'unknown' for cam in all_cameras)}]")
            else:
                logger.warning(f"⚠️  NO collections matched filter!")
        else:
            logger.info(f"📊 Processing all {len(all_cameras)} collections (no filter)")
        
        logger.info(f"🔍 Analyzing {len(all_cameras)} collections for behavioral patterns")
        
        # Initialize aggregation structures
        hourly_activity = {}  # {hour: count}
        daily_activity = {}   # {day_name: count}
        weekly_heatmap = {}   # {day_name: {hour: count}}
        camera_totals = {}    # {camera_id: total_count}
        all_timestamps = []   # For peak time analysis
        
        # Days of week mapping
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Initialize heatmap structure
        for day in days_of_week:
            weekly_heatmap[day] = {hour: 0 for hour in range(24)}
            daily_activity[day] = 0
        
        # Initialize hourly activity
        for hour in range(24):
            hourly_activity[hour] = 0
        
        # Fetch MVR data for each camera to build behavioral patterns
        async with httpx.AsyncClient(timeout=30.0) as client:
            for idx, camera in enumerate(all_cameras, 1):
                # Use camera_device_id for MVR endpoint, fallback to name if not available
                camera_device_id = camera.get("camera_device_id")
                camera_name = camera.get("name")
                
                if not camera_device_id:
                    logger.warning(f"⚠️  Skipping camera #{idx} ({camera_name}) - no camera_device_id field")
                    continue
                
                logger.info(f"📡 [{idx}/{len(all_cameras)}] Fetching MVR data for: {camera_name} (device: {camera_device_id})")
                
                try:
                    # Step 1: Get ALL videos from collection (no time filter - vmeta will filter)
                    # Need to get collection UUID first since search expects collection_id not name
                    start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
                    
                    # Get collection UUID from the camera object we already have
                    collection_uuid = camera.get("uuid")
                    if not collection_uuid:
                        logger.warning(f"   ⚠️  No UUID for collection {camera_name}")
                        continue
                    
                    videos_response = await client.get(
                        f"{MEDIA_SERVICE_URL}/api/v1/media/search",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={
                            "collection_id": collection_uuid,  # Use collection UUID
                            "page_size": 500  # Max allowed by Media Service validation
                        }
                    )
                    
                    if videos_response.status_code != 200:
                        error_detail = videos_response.text
                        logger.warning(f"   ⚠️  Failed to get videos for {camera_name}: {videos_response.status_code}")
                        logger.warning(f"   📄 Error detail: {error_detail}")
                        continue
                    
                    videos = videos_response.json()
                    video_uuids = [v["uuid"] for v in videos if v.get("uuid")]
                    
                    logger.info(f"   📊 Camera {camera_name}: Found {len(video_uuids)} videos")
                    
                    if not video_uuids:
                        continue
                    
                    # Step 2: Search MVR people for these videos with time filter (vmeta filters by time)
                    vmeta_search_response = await client.post(
                        f"http://localhost:8008/api/v1/mvr-people/search/by-videos",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        json={
                            "video_uuids": video_uuids,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "limit": 500,
                            "force_refresh": False
                        },
                        timeout=30.0
                    )
                    
                    if vmeta_search_response.status_code != 200:
                        logger.warning(f"   ⚠️  VMeta search failed for {camera_name}: {vmeta_search_response.status_code}")
                        continue
                    
                    mvr_search_data = vmeta_search_response.json()
                    mvr_people = mvr_search_data.get("mvr_people", [])
                    total_people = mvr_search_data.get("total_results", 0)
                    
                    logger.info(f"   📊 Camera {camera_name}: {total_people} MVR people found, processing timestamps")
                    
                    # Step 3: Extract timestamps from appearances (MVR response structure)
                    appearances_processed = 0
                    for mvr_person in mvr_people:
                        # Apply demographic filters on per-person level
                        if selected_genders:
                            person_gender = (mvr_person.get("gender") or "").lower()
                            if person_gender not in selected_genders:
                                continue
                        if selected_age_groups:
                            person_age = (mvr_person.get("age_group") or "").lower()
                            if person_age not in selected_age_groups:
                                continue
                        
                        # Get appearances - each has start_timestamp and end_timestamp
                        appearances = mvr_person.get("appearances", [])
                        
                        for appearance in appearances:
                            # Use start_timestamp from the appearance
                            timestamp_str = appearance.get("start_timestamp")
                            
                            if timestamp_str:
                                try:
                                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                    hour = timestamp.hour
                                    day_name = days_of_week[timestamp.weekday()]
                                    
                                    # Count as 1 person appearance
                                    people_count = 1
                                    hourly_activity[hour] += people_count
                                    daily_activity[day_name] += people_count
                                    weekly_heatmap[day_name][hour] += people_count
                                    all_timestamps.append((timestamp, people_count))
                                    appearances_processed += 1
                                except Exception as ts_error:
                                    logger.debug(f"   ⚠️  Error parsing timestamp '{timestamp_str}': {ts_error}")
                    
                    if appearances_processed > 0:
                        camera_totals[camera_name] = appearances_processed
                        logger.info(f"   ✅ Processed {appearances_processed} appearances from {camera_name}")
                    else:
                        logger.warning(f"   ⚠️  Camera {camera_name}: No appearances with timestamps processed")
                            
                except Exception as e:
                    logger.error(f"Error fetching MVR data for {camera_name}: {e}")
                    continue
        
        # Calculate peak times (top 5 hours with most activity)
        hourly_totals = [(hour, count) for hour, count in hourly_activity.items()]
        hourly_totals.sort(key=lambda x: x[1], reverse=True)
        peak_hours = [
            {
                "hour": hour,
                "count": count,
                "time_label": f"{hour:02d}:00 - {(hour+1)%24:02d}:00"
            }
            for hour, count in hourly_totals[:5] if count > 0
        ]
        
        # Calculate peak days
        daily_totals = [(day, count) for day, count in daily_activity.items()]
        daily_totals.sort(key=lambda x: x[1], reverse=True)
        peak_days = [
            {"day": day, "count": count}
            for day, count in daily_totals[:3] if count > 0
        ]
        
        # Camera comparison (top 5 most active)
        camera_comparison = sorted(
            [{"camera_id": cam_id, "total_people": count} for cam_id, count in camera_totals.items()],
            key=lambda x: x["total_people"],
            reverse=True
        )[:5]
        
        # Visit frequency analysis (simulated from repeat detections)
        # This is a simplified version - in production, would track individual face IDs
        total_people = sum(camera_totals.values())
        visit_frequency = {
            "new_visitors": int(total_people * 0.6),  # Simulated: 60% new
            "returning_visitors": int(total_people * 0.3),  # 30% returning
            "frequent_visitors": int(total_people * 0.1),  # 10% frequent
        }
        
        logger.info(f"✅ Behavioral analysis complete: {total_people} total detections across {len(camera_totals)} active cameras")
        
        return {
            "time_filter": time_filter,
            "total_detections": total_people,
            "active_cameras": len(camera_totals),
            "weekly_heatmap": weekly_heatmap,
            "hourly_activity": hourly_activity,
            "daily_activity": daily_activity,
            "peak_hours": peak_hours,
            "peak_days": peak_days,
            "camera_comparison": camera_comparison,
            "visit_frequency": visit_frequency,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in get_behavioral_analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch behavioral analytics: {str(e)}")


@router.get(
    "/analytics/quality-metrics",
    summary="Get average face quality metrics by collection",
    description="Returns average image quality from individual objects (not MVR objects) for camera/collection(s)",
)
async def get_quality_metrics(
    request: Request,
    time_filter: str = Query("today", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get average face quality metrics from individual objects filtered by collection.
    
    **Data Source:** Calculates quality from individual_video_appearances (individual objects, NOT MVR objects)
    
    **Returns:**
    - overall_average_quality: Average quality across ALL filtered collections combined
    - collection_breakdown: Array of per-collection quality metrics, each containing:
      - collection_name: Name of the collection/camera
      - average_quality: Average quality for THIS collection only
      - individual_count: Number of individuals in this collection
      - min_quality, max_quality, quality_std_dev: Distribution statistics
    - Quality distribution statistics across all collections
    
    **Multi-Collection Behavior:**
    When multiple collections are filtered, returns:
    1. Overall average quality aggregated across all collections (weighted by individual count)
    2. Separate average quality for each individual collection in the breakdown array
    
    Args:
        request: FastAPI request object to extract auth headers
        time_filter: Time period for filtering individuals
        collection_ids: Optional comma-separated collection IDs (null = all collections)
        current_user: Authenticated user from JWT token
        
    Returns:
        Dict containing:
        - overall_average_quality: Weighted average across all filtered collections
        - collection_breakdown: Per-collection metrics array
        - total_individuals: Total count across all collections
        - active_collections: Number of collections with data
    """
    try:
        logger.info(f"📊 Fetching quality metrics (time_filter: {time_filter}, collections: {collection_ids})")
        
        # Extract auth token from request headers
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        # Parse time filter
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
        
        # Parse collection IDs
        selected_collection_ids = None
        if collection_ids:
            selected_collection_ids = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]
            logger.info(f"📋 Quality metrics filtering by collection_ids: {selected_collection_ids}")
        else:
            logger.info(f"📋 Quality metrics fetching ALL collections (no filter provided)")
        
        # Get collections list from Media service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1000}
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch collections list: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch collections")
            
            all_cameras = response.json()
            logger.info(f"📊 Got {len(all_cameras)} total collections from Media service")
        
        # Filter cameras if specific ones requested
        if selected_collection_ids:
            before_filter = len(all_cameras)
            all_cameras = [
                cam for cam in all_cameras
                if _collection_matches_selected_ids(cam, selected_collection_ids)
            ]
            logger.info(f"🔍 Filtered {before_filter} collections down to {len(all_cameras)} matching filter")
            if len(all_cameras) > 0:
                logger.info(f"✅ Matched collections: [{', '.join(_get_collection_identifier(cam) or 'unknown' for cam in all_cameras)}]")
            else:
                logger.warning(
                    f"⚠️  NO collections matched filter! Available collections: "
                    f"{[_get_collection_identifier(cam) or _get_collection_display_name(cam) for cam in response.json()[:5]]}"
                )
        else:
            logger.info(f"📊 Processing all {len(all_cameras)} collections (no filter)")
        
        # Query vmeta service for quality metrics per collection
        collection_quality_data = []
        total_individuals = 0
        overall_quality_sum = 0.0
        overall_quality_count = 0
        
        VMETA_SERVICE_URL = "http://localhost:8008"
        
        for idx, camera in enumerate(all_cameras, 1):
            collection_name = camera.get("collection_name") or camera.get("name")
            if not collection_name:
                logger.warning(f"⚠️  Skipping camera #{idx} - no collection_name or name field")
                continue
            
            logger.info(f"📡 [{idx}/{len(all_cameras)}] Fetching quality metrics for: {collection_name}")
            
            try:
                # Query vmeta service for quality metrics
                async with httpx.AsyncClient(timeout=30.0) as client:
                    vmeta_url = f"{VMETA_SERVICE_URL}/api/v1/individuals/quality-metrics"
                    response = await client.get(
                        vmeta_url,
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={
                            "collection_name": collection_name,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat()
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        avg_quality = data.get("average_quality", 0.0)
                        individual_count = data.get("individual_count", 0)
                        
                        if individual_count > 0:
                            collection_quality_data.append({
                                "collection_name": collection_name,
                                "average_quality": round(avg_quality, 2),
                                "individual_count": individual_count,
                                "min_quality": round(data.get("min_quality", 0.0), 2),
                                "max_quality": round(data.get("max_quality", 0.0), 2),
                                "quality_std_dev": round(data.get("quality_std_dev", 0.0), 2)
                            })
                            
                            total_individuals += individual_count
                            overall_quality_sum += avg_quality * individual_count
                            overall_quality_count += individual_count
                            
                            logger.info(f"   ✅ {collection_name}: avg={avg_quality:.2f}, count={individual_count}")
                        else:
                            logger.info(f"   ⚠️  {collection_name}: No individuals found in time range")
                    
                    elif response.status_code == 404:
                        logger.info(f"   ⚠️  {collection_name}: No data in vmeta")
                    else:
                        logger.warning(f"   ❌ {collection_name}: vmeta returned {response.status_code}")
            
            except httpx.TimeoutException:
                logger.warning(f"   ⏱️  {collection_name}: Request timeout")
            except Exception as e:
                logger.error(f"   ❌ {collection_name}: Error - {e}")
        
        # Calculate overall average
        overall_average_quality = 0.0
        if overall_quality_count > 0:
            overall_average_quality = overall_quality_sum / overall_quality_count
        
        # Sort collections by average quality (descending)
        collection_quality_data.sort(key=lambda x: x["average_quality"], reverse=True)
        
        logger.info(f"✅ Quality metrics aggregation complete: {total_individuals} individuals across {len(collection_quality_data)} collections")
        
        return {
            "time_filter": time_filter,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_individuals": total_individuals,
            "active_collections": len(collection_quality_data),
            "overall_average_quality": round(overall_average_quality, 2),
            "collection_breakdown": collection_quality_data,
            "quality_grade": _get_quality_grade(overall_average_quality),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in get_quality_metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality metrics: {str(e)}")


def _get_quality_grade(quality: float) -> str:
    """Get quality grade label based on quality score (0-1 scale)."""
    if quality >= 0.8:
        return "Excellent"
    elif quality >= 0.6:
        return "Good"
    elif quality >= 0.4:
        return "Fair"
    elif quality >= 0.2:
        return "Poor"
    else:
        return "Very Poor"


@router.get(
    "/analytics/mvr-quality-metrics",
    summary="Get quality metrics via MVR data tree (RECOMMENDED)",
    description="Returns quality metrics by following MVR → Individual data hierarchy. Includes all successfully processed data even if representative_faces extraction failed.",
)
async def get_mvr_quality_metrics(
    request: Request,
    time_filter: str = Query("today", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_name: Optional[str] = Query(None, description="Collection name filter (null = aggregate all)"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs", alias="camera_ids"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get quality metrics following MVR → Individual data tree.
    
    **This is the RECOMMENDED endpoint** as it uses the correct data access pattern:
    1. Queries tracking sessions for collection + timeframe
    2. Gets individuals and MVR people counts from tracking sessions
    3. Extracts representative_faces from individuals where available
    4. Returns accurate counts matching batch processing results
    
    **Advantages over /analytics/quality-metrics:**
    - Includes ALL successfully processed individuals (not just those with representative_faces)
    - Uses tracking session metadata for accurate counts
    - Shows data completeness (individuals with vs without quality data)
    - Matches continuous pipeline results (individuals_found, unique_mvr_people_count)
    
    **Returns:**
    - total_individuals: Total individuals from tracking sessions
    - total_mvr_people: Total MVR people from tracking sessions  
    - tracking_sessions_count: Number of completed tracking sessions
    - average_quality: Average quality from available representative_faces
    - data_completeness: Percentage of individuals with quality data
    
    Args:
        request: FastAPI request object
        time_filter: Time period filter
        collection_name: Optional collection name filter
        current_user: Authenticated user
        
    Returns:
        Comprehensive quality metrics following MVR data tree
    """
    try:
        # Get time range based on filter
        if time_filter == "custom" and start_date and end_date:
            start_time = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end_time = datetime.now(timezone.utc)
            if time_filter == "today":
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == "last_3_days":
                start_time = end_time - timedelta(days=3)
            elif time_filter == "last_week":
                start_time = end_time - timedelta(days=7)
            elif time_filter == "last_month":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        logger.info(
            f"📊 MVR Quality Metrics (time_filter: {time_filter}, collection: {collection_name or 'ALL'}, camera_ids: {collection_ids or 'none'})"
        )
        
        effective_source = _normalize_source_type(source_type)
        
        vmeta_url = f"{VMETA_SERVICE_URL}/api/v1/mvr/quality-metrics"
        headers = {"Authorization": request.headers.get("Authorization")}

        async def _fetch_vmeta_quality(target_collection_name: Optional[str]) -> Dict:
            params = {
                "collection_name": target_collection_name or "all",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }
            if effective_source != "recording_pipeline":
                params["source_type"] = effective_source
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(vmeta_url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

        metrics: Dict
        if collection_ids:
            selected_ids = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]

            async with httpx.AsyncClient() as client:
                collections_response = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                    headers={"Authorization": request.headers.get("Authorization")},
                    params={"limit": 1000},
                )

            if collections_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch collections for MVR quality filtering")

            all_collections = collections_response.json()
            matched_collections = [
                cam for cam in all_collections
                if _collection_matches_selected_ids(cam, selected_ids)
            ]

            matched_collection_names = list({
                str(cam.get("collection_name") or cam.get("name"))
                for cam in matched_collections
                if cam.get("collection_name") or cam.get("name")
            })

            if not matched_collection_names:
                metrics = {
                    "time_filter": time_filter,
                    "collection_name": None,
                    "tracking_sessions_count": 0,
                    "total_individuals": 0,
                    "total_mvr_people": 0,
                    "total_videos_processed": 0,
                    "mvr_with_quality": 0,
                    "mvr_without_quality": 0,
                    "average_quality": None,
                    "min_quality": None,
                    "max_quality": None,
                    "quality_std_dev": None,
                    "data_completeness": {
                        "total": 0,
                        "with_data": 0,
                        "without_data": 0,
                        "percentage": 0.0,
                    },
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                per_collection_metrics = [
                    await _fetch_vmeta_quality(name)
                    for name in matched_collection_names
                ]

                total_tracking_sessions = sum(int(m.get("tracking_sessions_count", 0) or 0) for m in per_collection_metrics)
                total_individuals = sum(int(m.get("total_individuals", 0) or 0) for m in per_collection_metrics)
                total_mvr_people = sum(int(m.get("total_mvr_people", 0) or 0) for m in per_collection_metrics)
                total_videos_processed = sum(int(m.get("total_videos_processed", 0) or 0) for m in per_collection_metrics)
                mvr_with_quality = sum(int(m.get("mvr_with_quality", 0) or 0) for m in per_collection_metrics)
                mvr_without_quality = sum(int(m.get("mvr_without_quality", 0) or 0) for m in per_collection_metrics)

                quality_weight = mvr_with_quality
                weighted_quality_sum = sum(
                    (float(m.get("average_quality", 0.0) or 0.0) * int(m.get("mvr_with_quality", 0) or 0))
                    for m in per_collection_metrics
                )
                average_quality = (weighted_quality_sum / quality_weight) if quality_weight > 0 else None

                min_quality_values = [m.get("min_quality") for m in per_collection_metrics if m.get("min_quality") is not None]
                max_quality_values = [m.get("max_quality") for m in per_collection_metrics if m.get("max_quality") is not None]
                std_weighted_sum = sum(
                    (float(m.get("quality_std_dev", 0.0) or 0.0) * int(m.get("mvr_with_quality", 0) or 0))
                    for m in per_collection_metrics
                )
                quality_std_dev = (std_weighted_sum / quality_weight) if quality_weight > 0 else None

                completeness_total = mvr_with_quality + mvr_without_quality
                completeness_percentage = round((mvr_with_quality / completeness_total) * 100, 2) if completeness_total > 0 else 0.0

                metrics = {
                    "time_filter": time_filter,
                    "collection_name": None,
                    "tracking_sessions_count": total_tracking_sessions,
                    "total_individuals": total_individuals,
                    "total_mvr_people": total_mvr_people,
                    "total_videos_processed": total_videos_processed,
                    "mvr_with_quality": mvr_with_quality,
                    "mvr_without_quality": mvr_without_quality,
                    "average_quality": average_quality,
                    "min_quality": min(min_quality_values) if min_quality_values else None,
                    "max_quality": max(max_quality_values) if max_quality_values else None,
                    "quality_std_dev": quality_std_dev,
                    "data_completeness": {
                        "total": completeness_total,
                        "with_data": mvr_with_quality,
                        "without_data": mvr_without_quality,
                        "percentage": completeness_percentage,
                    },
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
        else:
            metrics = await _fetch_vmeta_quality(collection_name)
        
        logger.info(f"✅ MVR Quality Metrics: {metrics.get('total_individuals')} individuals, "
                   f"{metrics.get('total_mvr_people')} MVR people, "
                   f"quality: {metrics.get('average_quality', 0):.3f}")
        
        # Add quality grade and timestamp
        metrics["quality_grade"] = _get_quality_grade(metrics.get("average_quality", 0))
        metrics["time_filter"] = time_filter
        metrics["generated_at"] = datetime.now(timezone.utc).isoformat()
        metrics["data_source"] = "MVR → Individual tree (recommended)"
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error in get_mvr_quality_metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch MVR quality metrics: {str(e)}")

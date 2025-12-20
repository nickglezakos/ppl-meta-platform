"""
Analytics endpoints for MVR people detection insights.

Aggregates camera MVR count data to provide analytics dashboard metrics.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import httpx

from fastapi import APIRouter, Depends, Query, Request

from core.auth import get_current_user
from core.redis_client import cache_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Service URLs
CAMERAS_SERVICE_URL = "http://localhost:8005"
MEDIA_SERVICE_URL = "http://localhost:8000"


@router.get(
    "/analytics/summary",
    summary="Get aggregated analytics summary",
    description="Aggregate MVR people detection data across multiple collections with demographic breakdowns",
)
async def get_analytics_summary(
    request: Request,
    time_filter: str = Query("today", description="Time period filter: today, last_hour, last_3_hours, last_week, last_month"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    force_refresh: bool = Query(False, description="Bypass cache and get live data"),
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
        
        # Note: No analytics-level caching needed - the camera counter endpoint
        # already caches individual collection results with 10-minute TTL
        
        # Get list of collections to query
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
                        target_collection_ids = [
                            col.get("collection_name") or col.get("name")
                            for col in collections
                            if col.get("collection_name") or col.get("name")
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
                    response = await client.get(
                        counter_url,
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={
                            "time_filter": time_filter,
                            "force_refresh": False  # Use cache when available
                        },
                        timeout=30.0
                    )
                    
                    logger.info(f"📡 [{idx}/{len(target_collection_ids)}] Response status for {collection_id}: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.warning(f"❌ [{idx}/{len(target_collection_ids)}] Failed: {response.status_code} - {response.text[:200]}")
                        # Include with zero counts
                        collection_breakdown.append({
                            "collection_id": collection_id,
                            "collection_name": collection_id,
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
                    collection_demographics = collection_data.get("demographics", {})
                    if collection_demographics:
                        demographics["gender"]["male"] += collection_demographics.get("total_male", 0)
                        demographics["gender"]["female"] += collection_demographics.get("total_female", 0)
                        demographics["age"]["young"] += collection_demographics.get("total_young", 0)
                        demographics["age"]["adult"] += collection_demographics.get("total_adult", 0)
                        logger.info(f"   👥 Aggregated demographics from {collection_id}")
                    
                    # Always add to collection breakdown
                    collection_breakdown.append({
                        "camera_id": collection_id,  # Frontend expects 'camera_id'
                        "camera_name": collection_id,
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
                    "camera_name": collection_id,
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
                    collection_name = collection.get("collection_name") or collection.get("name")
                    if collection_name:
                        result.append({
                            "id": collection_name,
                            "name": collection_name,
                            "collection_name": collection_name,
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

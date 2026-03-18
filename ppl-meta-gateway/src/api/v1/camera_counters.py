"""Camera MVR counter endpoints with caching support."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, Tuple
import logging
import httpx

from core.redis_client import cache_client
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# Service URLs from environment
MEDIA_SERVICE_URL = "http://localhost:8000"
VMETA_SERVICE_URL = "http://localhost:8008"


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


async def _get_videos_for_camera(
    camera_id: str,
    start_time: datetime,
    end_time: datetime,
    auth_token: str
) -> list:
    """
    Get videos from Media service for a camera.
    
    Args:
        camera_id: Camera device ID (used as collection_id)
        start_time: Start datetime
        end_time: End datetime
        auth_token: JWT token for authorization
    
    Returns:
        List of video UUIDs
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/search",
                params={
                    "collection": camera_id,  # Use 'collection' alias for name-based lookup
                    # Note: media_types filter has a bug in Media service, omitting for now
                    # All items in camera collections should be videos anyway
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "page_size": 100
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Failed to get videos from Media service: "
                    f"{response.status_code} - {response.text}"
                )
                return []
            
            media_items = response.json()
            
            # Media service returns a list of media items directly
            if not isinstance(media_items, list):
                logger.warning(f"Unexpected response format from Media service: {type(media_items)}")
                return []
            
            video_uuids = [item["uuid"] for item in media_items if item.get("uuid")]
            
            logger.debug(f"Found {len(video_uuids)} videos for camera {camera_id}")
            return video_uuids
            
    except Exception as e:
        logger.error(f"Error fetching videos from Media service: {e}")
        return []


async def _count_mvr_people_by_videos(
    video_uuids: list,
    auth_token: str,
    include_demographics: bool = True
) -> Dict[str, Any]:
    """
    Count MVR people from VMeta service for given videos with demographics.
    
    Args:
        video_uuids: List of video UUIDs
        auth_token: JWT token for authorization
        include_demographics: Include gender/age breakdowns
    
    Returns:
        Dict with 'count', 'video_count', and demographics if requested
    """
    if not video_uuids:
        base_response = {"count": 0, "video_count": 0}
        if include_demographics:
            base_response["demographics"] = {
                "total_male": 0,
                "total_female": 0,
                "percent_male": 0.0,
                "percent_female": 0.0,
                "total_young": 0,
                "total_adult": 0,
                "percent_young": 0.0,
                "percent_adult": 0.0
            }
        return base_response
    
    try:
        # Use demographics endpoint if requested
        endpoint = (
            f"{VMETA_SERVICE_URL}/api/v1/mvr-people/count-by-videos-demographics"
            if include_demographics
            else f"{VMETA_SERVICE_URL}/api/v1/mvr-people/count-by-videos"
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                json={"video_uuids": video_uuids},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Failed to count MVR people from VMeta service: "
                    f"{response.status_code} - {response.text}"
                )
                return {"count": 0, "video_count": 0}
            
            data = response.json()
            
            logger.debug(
                f"MVR count: {data.get('count', 0)} people, "
                f"{data.get('video_count', 0)} videos"
            )
            
            result = {
                "count": data.get("count", 0),
                "video_count": data.get("video_count", 0)
            }
            
            # Add demographics if included in response
            if include_demographics and "demographics" in data:
                result["demographics"] = data["demographics"]
            
            return result
            
    except Exception as e:
        logger.error(f"Error counting MVR people from VMeta service: {e}")
        return {"count": 0, "video_count": 0}


async def _compute_mvr_count_live(
    camera_id: str,
    start_time: datetime,
    end_time: datetime,
    auth_token: str,
    include_demographics: bool = True
) -> Dict[str, Any]:
    """
    Compute MVR count by querying Media and VMeta services.
    
    This is the fallback when cache misses or force_refresh is true.
    
    Args:
        camera_id: Camera device ID
        start_time: Start datetime for video search
        end_time: End datetime for video search
        auth_token: JWT token for authorization
        include_demographics: Include gender/age breakdowns
    
    Returns:
        Dict with count data and demographics if requested
    """
    logger.info(
        f"Computing live MVR count for camera {camera_id} "
        f"from {start_time.isoformat()} to {end_time.isoformat()}"
    )
    
    # Step 1: Get videos from Media service
    video_uuids = await _get_videos_for_camera(
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
        auth_token=auth_token
    )
    
    # Step 2: Count MVR people from VMeta service with demographics
    count_data = await _count_mvr_people_by_videos(
        video_uuids=video_uuids,
        auth_token=auth_token,
        include_demographics=include_demographics
    )
    
    return count_data


@router.get(
    "/cameras/{camera_id}/mvr-count",
    summary="Get Camera MVR People Count with Demographics (Cached)",
    description=(
        "Returns the count of unique MVR people detected by a camera with demographic breakdowns. "
        "Results are cached for 10 minutes for optimal performance. "
        "Use force_refresh=true to bypass cache and get live data."
    ),
    tags=["cameras", "counters"]
)
async def get_camera_mvr_count_cached(
    camera_id: str,
    request: Request,
    time_filter: Optional[str] = Query(
        "today",
        description="Time filter: 'today', 'last_hour', 'last_3_hours', 'last_week', 'last_month', 'custom'"
    ),
    force_refresh: bool = Query(
        False,
        description="Force refresh from database (bypass cache)"
    ),
    start_date: Optional[str] = Query(
        None,
        description="ISO 8601 start datetime (required when time_filter=custom)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="ISO 8601 end datetime (required when time_filter=custom)"
    ),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cached or live MVR people count for a camera with demographic breakdowns.
    
    **Cache Strategy:**
    - First checks Redis cache (10 min TTL)
    - If cache miss or force_refresh=true, queries Media + VMeta services
    - Stores result in cache for subsequent requests
    
    **Response Example:**
    ```json
    {
        "camera_id": "camera-123",
        "time_filter": "today",
        "start_time": "2025-12-06T00:00:00",
        "end_time": "2025-12-06T14:30:00",
        "count": 12,
        "video_count": 9,
        "demographics": {
            "total_male": 7,
            "total_female": 5,
            "percent_male": 58.3,
            "percent_female": 41.7,
            "total_young": 3,
            "total_adult": 9,
            "percent_young": 25.0,
            "percent_adult": 75.0
        },
        "cached": true,
        "cached_at": "2025-12-06T10:15:30.123456"
    }
    ```
    
    **Parameters:**
    - camera_id: Camera device identifier
    - time_filter: Time range filter (default: today)
    - force_refresh: Bypass cache (default: false)
    
    **Authentication:**
    - Requires valid JWT token
    """
    try:
        # Validate and parse time filter
        try:
            start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # Extract auth token from Authorization header
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        # Generate cache key with time filter
        cache_key = f"mvr_count:{camera_id}:{time_filter}"
        
        # Step 1: Try cache (unless force refresh)
        if not force_refresh and cache_client.is_connected():
            try:
                cached_value = await cache_client.redis.get(cache_key)
                if cached_value:
                    import json
                    cached_data = json.loads(cached_value)
                    cached_data["cached"] = True
                    logger.info(
                        f"✅ Cache HIT for camera {camera_id} with {time_filter}: "
                        f"{cached_data['count']} people"
                    )
                    return cached_data
            except Exception as e:
                logger.warning(f"Cache retrieval error: {e}")
        
        # Step 2: Cache miss or forced refresh - compute live
        logger.info(
            f"🔄 Computing live MVR count for camera {camera_id} with {time_filter} "
            f"(force_refresh={force_refresh})"
        )
        
        live_data = await _compute_mvr_count_live(
            camera_id=camera_id,
            start_time=start_time,
            end_time=end_time,
            auth_token=auth_token,
            include_demographics=True
        )
        
        # Build response
        response_data = {
            "camera_id": camera_id,
            "time_filter": time_filter,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "count": live_data["count"],
            "video_count": live_data["video_count"],
            "demographics": live_data.get("demographics", {}),
            "cached": False
        }
        
        # Step 3: Store in cache (if Redis available)
        if cache_client.is_connected():
            try:
                import json
                await cache_client.redis.setex(
                    cache_key,
                    600,  # 10 minutes TTL
                    json.dumps(response_data)
                )
            except Exception as e:
                logger.warning(f"Cache storage error: {e}")
        
        logger.info(
            f"✅ Live count for camera {camera_id} with {time_filter}: "
            f"{response_data['count']} people, "
            f"{response_data.get('demographics', {}).get('total_male', 0)} men, "
            f"{response_data.get('demographics', {}).get('total_female', 0)} women"
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching camera MVR count for {camera_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch camera MVR count: {str(e)}"
        )


@router.delete(
    "/cameras/{camera_id}/mvr-count/cache",
    summary="Invalidate Camera MVR Count Cache",
    description="Force invalidate cached MVR count for a camera.",
    tags=["cameras", "counters", "cache"]
)
async def invalidate_camera_mvr_count_cache(
    camera_id: str,
    date: Optional[str] = Query(
        None,
        description="Date in YYYY-MM-DD format (default: today)"
    ),
    current_user: dict = Depends(get_current_user)
):
    """
    Invalidate cached MVR count for a camera.
    
    Use this when you know new detections have been processed
    and want to force cache refresh on next request.
    
    **Response Example:**
    ```json
    {
        "camera_id": "camera-123",
        "date": "2025-12-06",
        "invalidated": true
    }
    ```
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if not cache_client.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Redis cache not available"
            )
        
        deleted = await cache_client.delete_camera_mvr_count(
            camera_id=camera_id,
            date=date
        )
        
        return {
            "camera_id": camera_id,
            "date": date,
            "invalidated": deleted
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating cache for {camera_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.get(
    "/cameras/mvr-counts/all",
    summary="Get All Camera MVR Counts (Cached)",
    description="Get cached MVR counts for all cameras on a specific date.",
    tags=["cameras", "counters"]
)
async def get_all_camera_mvr_counts(
    date: Optional[str] = Query(
        None,
        description="Date in YYYY-MM-DD format (default: today)"
    ),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all cached camera MVR counts for a date.
    
    Useful for displaying dashboard summaries without
    querying each camera individually.
    
    **Response Example:**
    ```json
    {
        "date": "2025-12-06",
        "counts": {
            "camera-123": {
                "count": 12,
                "video_count": 9,
                "cached_at": "2025-12-06T10:15:30"
            },
            "camera-456": {
                "count": 5,
                "video_count": 3,
                "cached_at": "2025-12-06T10:15:45"
            }
        },
        "total_cameras": 2
    }
    ```
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if not cache_client.is_connected():
            return {
                "date": date,
                "counts": {},
                "total_cameras": 0,
                "error": "Redis cache not available"
            }
        
        counts = await cache_client.get_all_camera_counts(date=date)
        
        return {
            "date": date,
            "counts": counts,
            "total_cameras": len(counts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching all camera counts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch all camera counts: {str(e)}"
        )

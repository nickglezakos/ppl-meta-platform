"""Background worker to pre-compute camera MVR counts."""
import asyncio
from datetime import datetime, time
import logging
from typing import List
import httpx

from core.redis_client import cache_client

logger = logging.getLogger(__name__)


# Service URLs
CAMERAS_SERVICE_URL = "http://localhost:8005"
MEDIA_SERVICE_URL = "http://localhost:8000"
VMETA_SERVICE_URL = "http://localhost:8008"


class MVRCounterWorker:
    """Background worker to pre-compute and cache camera MVR counts."""
    
    def __init__(
        self, 
        interval_seconds: int = 300,  # 5 minutes
        internal_token: str = None
    ):
        """
        Initialize worker.
        
        Args:
            interval_seconds: How often to refresh counts (default: 300s = 5min)
            internal_token: Service-to-service auth token
        """
        self.interval_seconds = interval_seconds
        self.running = False
        self.internal_token = internal_token or "internal-service-token"  # TODO: Get from env
    
    async def start(self):
        """Start the background worker."""
        self.running = True
        logger.info(
            f"🚀 MVR Counter Worker starting "
            f"(interval: {self.interval_seconds}s)"
        )
        
        while self.running:
            try:
                await self._refresh_all_camera_counts()
            except Exception as e:
                logger.error(
                    f"❌ Error in MVR counter worker cycle: {e}",
                    exc_info=True
                )
            
            # Wait for next interval
            await asyncio.sleep(self.interval_seconds)
    
    async def stop(self):
        """Stop the background worker."""
        self.running = False
        logger.info("🛑 MVR Counter Worker stopped")
    
    async def _get_all_cameras(self) -> List[dict]:
        """
        Fetch all cameras from Cameras service.
        
        Returns:
            List of camera dicts with device_id
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{CAMERAS_SERVICE_URL}/api/v1/cameras",
                    headers={"Authorization": f"Bearer {self.internal_token}"}
                )
                
                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch cameras: {response.status_code}"
                    )
                    return []
                
                data = response.json()
                
                if not data.get("success"):
                    return []
                
                cameras = data.get("data", {}).get("cameras", [])
                return cameras
                
        except Exception as e:
            logger.error(f"Error fetching cameras list: {e}")
            return []
    
    async def _get_videos_for_camera(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[str]:
        """
        Get video UUIDs for a camera from Media service.
        
        Args:
            camera_id: Camera device ID
            start_time: Start datetime
            end_time: End datetime
        
        Returns:
            List of video UUIDs
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/search",
                    json={
                        "collection_id": camera_id,
                        "media_type": "video",
                        "start_date": start_time.isoformat(),
                        "end_date": end_time.isoformat(),
                        "limit": 100
                    },
                    headers={"Authorization": f"Bearer {self.internal_token}"}
                )
                
                if response.status_code != 200:
                    logger.warning(
                        f"Failed to get videos for camera {camera_id}: "
                        f"{response.status_code}"
                    )
                    return []
                
                data = response.json()
                
                if not data.get("success") or not data.get("data"):
                    return []
                
                items = data["data"].get("items", [])
                video_uuids = [item["uuid"] for item in items]
                
                return video_uuids
                
        except Exception as e:
            logger.error(
                f"Error fetching videos for camera {camera_id}: {e}"
            )
            return []
    
    async def _count_mvr_people(self, video_uuids: List[str]) -> dict:
        """
        Count MVR people from VMeta service.
        
        Args:
            video_uuids: List of video UUIDs
        
        Returns:
            Dict with 'count' and 'video_count'
        """
        if not video_uuids:
            return {"count": 0, "video_count": 0}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{VMETA_SERVICE_URL}/api/v1/mvr-people/count-by-videos",
                    json={"video_uuids": video_uuids},
                    headers={"Authorization": f"Bearer {self.internal_token}"}
                )
                
                if response.status_code != 200:
                    logger.warning(
                        f"Failed to count MVR people: {response.status_code}"
                    )
                    return {"count": 0, "video_count": 0}
                
                data = response.json()
                
                return {
                    "count": data.get("count", 0),
                    "video_count": data.get("video_count", 0)
                }
                
        except Exception as e:
            logger.error(f"Error counting MVR people: {e}")
            return {"count": 0, "video_count": 0}
    
    async def _refresh_camera_count(self, camera_id: str) -> bool:
        """
        Refresh MVR count for a single camera.
        
        Args:
            camera_id: Camera device ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get today's date range
            today = datetime.now()
            date_str = today.strftime("%Y-%m-%d")
            start_time = datetime.combine(today, time.min)
            end_time = datetime.combine(today, time.max)
            
            # Step 1: Get videos
            video_uuids = await self._get_videos_for_camera(
                camera_id=camera_id,
                start_time=start_time,
                end_time=end_time
            )
            
            # Step 2: Count MVR people
            count_data = await self._count_mvr_people(video_uuids)
            
            # Step 3: Cache result
            if cache_client.is_connected():
                await cache_client.set_camera_mvr_count(
                    camera_id=camera_id,
                    count=count_data["count"],
                    video_count=count_data["video_count"],
                    date=date_str,
                    ttl=600  # 10 minutes
                )
                
                logger.debug(
                    f"✅ Refreshed {camera_id}: "
                    f"{count_data['count']} people, "
                    f"{count_data['video_count']} videos"
                )
                return True
            else:
                logger.warning("Redis not connected, cannot cache")
                return False
            
        except Exception as e:
            logger.error(
                f"Error refreshing count for {camera_id}: {e}",
                exc_info=True
            )
            return False
    
    async def _refresh_all_camera_counts(self):
        """Refresh MVR counts for all cameras."""
        if not cache_client.is_connected():
            logger.warning("⚠️  Redis not connected, skipping refresh cycle")
            return
        
        start_time = datetime.now()
        logger.info("🔄 Starting MVR count refresh cycle")
        
        # Step 1: Get all cameras
        cameras = await self._get_all_cameras()
        
        if not cameras:
            logger.warning("No cameras found, skipping refresh")
            return
        
        logger.info(f"📊 Refreshing counts for {len(cameras)} cameras")
        
        # Step 2: Refresh each camera's count (parallel with concurrency limit)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent refreshes
        
        async def refresh_with_limit(camera):
            async with semaphore:
                return await self._refresh_camera_count(camera["device_id"])
        
        tasks = [refresh_with_limit(camera) for camera in cameras]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 3: Log results
        success_count = sum(
            1 for r in results 
            if not isinstance(r, Exception) and r
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"✅ MVR count refresh complete: "
            f"{success_count}/{len(cameras)} cameras updated "
            f"in {duration:.2f}s"
        )


# Global worker instance
mvr_counter_worker = MVRCounterWorker(
    interval_seconds=300,  # 5 minutes
    internal_token=None  # Will be set from env
)

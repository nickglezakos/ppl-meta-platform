"""
Mobile camera cleanup service to handle stale connections.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera, CameraStatus, CameraType

logger = logging.getLogger(__name__)


class MobileCameraCleanupService:
    """Service to clean up stale mobile camera connections."""

    def __init__(self, timeout_minutes: int = 10):
        """
        Initialize the cleanup service.

        Args:
            timeout_minutes: Minutes after which a mobile camera is considered stale
        """
        self.timeout_minutes = timeout_minutes
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the cleanup service."""
        if self._running:
            logger.warning("Mobile camera cleanup service already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Mobile camera cleanup service started with {self.timeout_minutes} minute timeout"
        )

    async def stop(self):
        """Stop the cleanup service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Mobile camera cleanup service stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop that runs every minute."""
        while self._running:
            try:
                await self.cleanup_stale_mobile_cameras()
                await asyncio.sleep(60)  # Run every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in mobile camera cleanup loop: {e}")
                await asyncio.sleep(60)

    async def cleanup_stale_mobile_cameras(self) -> int:
        """
        Mark stale mobile cameras as available and cleanup streaming service.

        Returns:
            Number of cameras updated
        """
        try:
            # First cleanup stale cameras in mobile streaming service
            try:
                from src.services.mobile_streaming import mobile_streaming_service
                await mobile_streaming_service.cleanup_stale_cameras()
            except Exception as e:
                logger.error(f"Error cleaning up mobile streaming service: {e}")
            
            db_gen = get_db()
            db = next(db_gen)

            try:
                # Calculate cutoff time
                cutoff_time = datetime.utcnow() - timedelta(
                    minutes=self.timeout_minutes
                )

                # Find stale mobile cameras that are marked as connected
                stale_cameras = (
                    db.query(Camera)
                    .filter(
                        Camera.camera_type == CameraType.MOBILE,
                        Camera.status == CameraStatus.CONNECTED,
                        Camera.last_seen < cutoff_time,
                    )
                    .all()
                )

                updated_count = 0
                for camera in stale_cameras:
                    old_status = camera.status
                    camera.status = CameraStatus.AVAILABLE

                    time_since_seen = datetime.utcnow() - camera.last_seen
                    minutes_ago = int(time_since_seen.total_seconds() / 60)

                    logger.info(
                        f"Marked stale mobile camera {camera.device_id} as available "
                        f"(last seen {minutes_ago} minutes ago, IP: {camera.connection_string})"
                    )
                    updated_count += 1

                if updated_count > 0:
                    db.commit()
                    logger.info(
                        f"Updated {updated_count} stale mobile cameras to available status"
                    )

                return updated_count

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error cleaning up stale mobile cameras: {e}")
            return 0

    async def force_cleanup_camera(self, device_id: str) -> bool:
        """
        Force cleanup a specific mobile camera.

        Args:
            device_id: Device ID of the mobile camera

        Returns:
            True if camera was updated, False otherwise
        """
        try:
            db_gen = get_db()
            db = next(db_gen)

            try:
                camera = (
                    db.query(Camera)
                    .filter(
                        Camera.device_id == device_id,
                        Camera.camera_type == CameraType.MOBILE,
                    )
                    .first()
                )

                if not camera:
                    logger.warning(f"Mobile camera {device_id} not found")
                    return False

                if camera.status == CameraStatus.CONNECTED:
                    old_status = camera.status
                    camera.status = CameraStatus.AVAILABLE
                    db.commit()

                    logger.info(
                        f"Force cleaned mobile camera {device_id} "
                        f"(status: {old_status.value} -> {camera.status.value})"
                    )
                    return True
                else:
                    logger.info(
                        f"Mobile camera {device_id} is already {camera.status.value}"
                    )
                    return False

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error force cleaning mobile camera {device_id}: {e}")
            return False


# Global cleanup service instance
mobile_cleanup_service = MobileCameraCleanupService(
    timeout_minutes=5
)  # 5 minute timeout

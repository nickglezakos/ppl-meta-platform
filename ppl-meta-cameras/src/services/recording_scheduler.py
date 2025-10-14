# ppl-meta-cameras/src/services/recording_scheduler.py

"""
Recording Scheduler Service
Handles automatic recording scheduling based on camera recording profiles
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera
from src.services.recording_profile_service import RecordingProfileService

logger = logging.getLogger(__name__)


class RecordingScheduler:
    """
    Service for managing automatic recording schedules based on camera profiles.

    This service monitors cameras with recording profiles and triggers
    automatic recordings according to their configured intervals.
    """

    def __init__(self, db: Session):
        self.db = db
        self.profile_service = RecordingProfileService(db)
        self.active_schedules: Dict[int, asyncio.Task] = {}  # camera_id -> task
        self.is_running = False

    async def start_scheduler(self):
        """Start the recording scheduler service."""
        if self.is_running:
            logger.warning("Recording scheduler is already running")
            return

        self.is_running = True
        logger.info("Starting recording scheduler service")

        # Start scheduler loop
        asyncio.create_task(self._scheduler_loop())

    async def stop_scheduler(self):
        """Stop the recording scheduler service."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping recording scheduler service")

        # Cancel all active schedules
        for camera_id, task in self.active_schedules.items():
            task.cancel()
            logger.info(f"Cancelled recording schedule for camera {camera_id}")

        self.active_schedules.clear()

    async def _scheduler_loop(self):
        """Main scheduler loop that monitors cameras and manages schedules."""
        while self.is_running:
            try:
                await self._update_camera_schedules()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _update_camera_schedules(self):
        """Update recording schedules for all cameras with profiles."""
        # Get all active cameras with recording profiles
        cameras_with_profiles = (
            self.db.query(Camera)
            .filter(
                Camera.is_active == True,
                Camera.recording_profile_id.isnot(None),
                Camera.supports_recording == True,
            )
            .all()
        )

        current_camera_ids = {camera.id for camera in cameras_with_profiles}
        scheduled_camera_ids = set(self.active_schedules.keys())

        # Remove schedules for cameras that no longer need them
        cameras_to_unschedule = scheduled_camera_ids - current_camera_ids
        for camera_id in cameras_to_unschedule:
            await self._unschedule_camera_recording(camera_id)

        # Add or update schedules for cameras that need them
        for camera in cameras_with_profiles:
            config = camera.effective_recording_config
            if config and config.get("auto_segment_recording", False):
                if camera.id not in self.active_schedules:
                    await self._schedule_camera_recording(camera)
                else:
                    # Check if schedule needs updating
                    await self._update_camera_schedule_if_needed(camera)

    async def _schedule_camera_recording(self, camera: Camera):
        """Schedule automatic recording for a camera."""
        config = camera.effective_recording_config
        if not config or not config.get("auto_segment_recording", False):
            return

        interval_seconds = config.get("segment_interval_seconds")
        if not interval_seconds or interval_seconds < 5:
            logger.warning(f"Invalid recording interval for camera {camera.id}")
            return

        # Create and start recording task
        task = asyncio.create_task(
            self._camera_recording_loop(camera, interval_seconds)
        )
        self.active_schedules[camera.id] = task

        logger.info(
            f"Scheduled automatic recording for camera {camera.name} "
            f"(ID: {camera.id}) every {interval_seconds} seconds"
        )

    async def _unschedule_camera_recording(self, camera_id: int):
        """Remove automatic recording schedule for a camera."""
        if camera_id in self.active_schedules:
            task = self.active_schedules[camera_id]
            task.cancel()
            del self.active_schedules[camera_id]
            logger.info(f"Unscheduled automatic recording for camera {camera_id}")

    async def _update_camera_schedule_if_needed(self, camera: Camera):
        """Update camera schedule if configuration changed."""
        config = camera.effective_recording_config
        if not config:
            await self._unschedule_camera_recording(camera.id)
            return

        # For now, we'll just reschedule if the camera is already scheduled
        # In production, you might want to check if the interval actually changed
        if camera.id in self.active_schedules:
            await self._unschedule_camera_recording(camera.id)
            await self._schedule_camera_recording(camera)

    async def _camera_recording_loop(self, camera: Camera, interval_seconds: int):
        """Recording loop for a specific camera."""
        try:
            while self.is_running:
                # Trigger recording for this camera
                await self._trigger_camera_recording(camera)

                # Wait for the next recording interval
                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info(f"Recording loop cancelled for camera {camera.id}")
        except Exception as e:
            logger.error(f"Error in recording loop for camera {camera.id}: {e}")

    async def _trigger_camera_recording(self, camera: Camera):
        """
        Trigger a recording for the specified camera.

        This method would integrate with the actual recording service
        to start a recording session based on the camera's profile configuration.
        """
        config = camera.effective_recording_config
        if not config:
            return

        duration_seconds = config.get("segment_duration_seconds", 30)
        recording_quality = config.get("recording_quality", "high")

        # Log the recording trigger (in production, this would call the recording service)
        logger.info(
            f"Triggering automatic recording for camera {camera.name} "
            f"(ID: {camera.id}) - Duration: {duration_seconds}s, "
            f"Quality: {recording_quality}"
        )

        # TODO: Integrate with actual recording service
        # This would call something like:
        # await recording_service.start_recording(
        #     camera_id=camera.id,
        #     duration=duration_seconds,
        #     quality=recording_quality,
        #     auto_face_detection=config.get("auto_face_detection_enabled", True)
        # )

        # Update profile usage statistics
        if camera.recording_profile:
            camera.recording_profile.update_usage_stats()
            self.db.commit()

    async def schedule_camera_recording_now(self, camera_id: int) -> bool:
        """
        Manually trigger recording for a camera (outside of automatic schedule).

        Args:
            camera_id: ID of the camera to record

        Returns:
            True if recording was triggered successfully, False otherwise
        """
        camera = (
            self.db.query(Camera)
            .filter(
                Camera.id == camera_id,
                Camera.is_active == True,
                Camera.supports_recording == True,
            )
            .first()
        )

        if not camera:
            logger.warning(
                f"Camera {camera_id} not found or does not support recording"
            )
            return False

        config = camera.effective_recording_config
        if not config:
            logger.warning(f"Camera {camera_id} has no recording profile assigned")
            return False

        await self._trigger_camera_recording(camera)
        return True

    def get_active_schedules(self) -> List[Dict]:
        """
        Get information about currently active recording schedules.

        Returns:
            List of dictionaries with schedule information
        """
        active_schedules = []

        for camera_id in self.active_schedules.keys():
            camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
            if camera and camera.effective_recording_config:
                config = camera.effective_recording_config
                active_schedules.append(
                    {
                        "camera_id": camera_id,
                        "camera_name": camera.name,
                        "profile_name": config.get("profile_name", "Unknown"),
                        "interval_seconds": config.get("segment_interval_seconds"),
                        "duration_seconds": config.get("segment_duration_seconds", 30),
                        "recording_quality": config.get("recording_quality", "high"),
                        "next_recording_in": "unknown",  # Could calculate based on last trigger
                    }
                )

        return active_schedules

    async def force_schedule_update(self):
        """Force an immediate update of all camera schedules."""
        logger.info("Forcing recording schedule update")
        await self._update_camera_schedules()


# Global scheduler instance
_recording_scheduler: Optional[RecordingScheduler] = None


async def get_recording_scheduler() -> RecordingScheduler:
    """Get or create the global recording scheduler instance."""
    global _recording_scheduler

    if _recording_scheduler is None:
        db = next(get_db())
        _recording_scheduler = RecordingScheduler(db)
        await _recording_scheduler.start_scheduler()

    return _recording_scheduler


async def schedule_automatic_recording_for_camera(camera: Camera):
    """Schedule automatic recording based on camera's profile settings."""
    scheduler = await get_recording_scheduler()
    if camera.supports_automatic_recording:
        await scheduler._schedule_camera_recording(camera)


async def unschedule_automatic_recording_for_camera(camera_id: int):
    """Remove scheduled automatic recording for a camera."""
    scheduler = await get_recording_scheduler()
    await scheduler._unschedule_camera_recording(camera_id)


async def trigger_profile_based_recording(camera_id: int) -> bool:
    """Trigger recording based on the camera's assigned profile."""
    scheduler = await get_recording_scheduler()
    return await scheduler.schedule_camera_recording_now(camera_id)

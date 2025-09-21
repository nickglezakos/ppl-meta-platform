"""
PPL Meta Orchestrator - Camera Automation & Settings Management
Phase 2.1 Implementation: User camera settings, interval scheduling, and automation triggers
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from models import (
    CameraSettings,
    CameraWorkflow,
    IntervalSchedule,
    SessionLocal,
    WorkflowExecution,
)
from service_clients import ServiceClientManager
from sqlalchemy import and_, func
from sqlalchemy.orm import sessionmaker
from workflow_orchestrator import CameraFaceDetectionWorkflowOrchestrator

logger = logging.getLogger(__name__)


class AutomationTrigger(Enum):
    """Types of automation triggers for camera workflows."""

    MANUAL = "manual"
    RECORDING_COMPLETION = "recording_completion"
    TIME_INTERVAL = "time_interval"
    SCHEDULED = "scheduled"
    CONTINUOUS = "continuous"


class ProcessingInterval(Enum):
    """Interval types for automated processing."""

    IMMEDIATE = "immediate"  # Process right after recording
    HOURLY = "hourly"  # Every hour
    EVERY_2_HOURS = "every_2_hours"
    EVERY_6_HOURS = "every_6_hours"
    DAILY = "daily"  # Once per day
    WEEKLY = "weekly"  # Once per week
    CUSTOM = "custom"  # User-defined interval


@dataclass
class CameraAutomationConfig:
    """Configuration for camera automation settings."""

    camera_device_id: str
    user_id: str

    # Automation settings
    auto_face_detection_enabled: bool = True
    automation_trigger: AutomationTrigger = AutomationTrigger.RECORDING_COMPLETION
    processing_interval: ProcessingInterval = ProcessingInterval.IMMEDIATE
    custom_interval_minutes: Optional[int] = None

    # Face detection settings
    detection_methods: List[str] = field(default_factory=lambda: ["two_stage"])
    confidence_threshold: float = 0.8
    max_faces_per_frame: int = 10

    # Processing preferences
    priority: str = "normal"  # low, normal, high
    batch_processing: bool = True
    max_batch_size: int = 50

    # Time-based settings
    active_hours_start: Optional[str] = None  # "09:00"
    active_hours_end: Optional[str] = None  # "17:00"
    timezone: str = "UTC"

    # Storage and retention
    store_results: bool = True
    retention_days: Optional[int] = 30

    # Notification settings
    notify_on_completion: bool = False
    notify_on_failures: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class CameraAutomationManager:
    """Manages camera automation settings and triggers for individual cameras."""

    def __init__(
        self,
        service_manager: ServiceClientManager,
        workflow_orchestrator: CameraFaceDetectionWorkflowOrchestrator,
    ):
        self.service_manager = service_manager
        self.workflow_orchestrator = workflow_orchestrator
        self.automation_configs: Dict[str, CameraAutomationConfig] = {}
        self._active_schedules: Dict[str, asyncio.Task] = {}

    async def get_camera_automation_config(
        self, camera_device_id: str, user_id: str
    ) -> Optional[CameraAutomationConfig]:
        """Get automation configuration for a specific camera."""
        db = SessionLocal()
        try:
            # Get camera settings from database
            camera_settings = (
                db.query(CameraSettings)
                .filter(
                    and_(
                        CameraSettings.camera_device_id == camera_device_id,
                        CameraSettings.user_id == user_id,
                    )
                )
                .first()
            )

            if not camera_settings:
                return None

            # Convert database settings to automation config
            config = CameraAutomationConfig(
                camera_device_id=camera_device_id,
                user_id=user_id,
                auto_face_detection_enabled=camera_settings.auto_face_detection_enabled,
                automation_trigger=AutomationTrigger(
                    camera_settings.automation_trigger
                ),
                processing_interval=ProcessingInterval(
                    camera_settings.processing_interval
                ),
                custom_interval_minutes=camera_settings.custom_interval_minutes,
                detection_methods=camera_settings.detection_methods,
                confidence_threshold=camera_settings.confidence_threshold,
                max_faces_per_frame=camera_settings.max_faces_per_frame,
                priority=camera_settings.priority,
                batch_processing=camera_settings.batch_processing,
                max_batch_size=camera_settings.max_batch_size,
                active_hours_start=camera_settings.active_hours_start,
                active_hours_end=camera_settings.active_hours_end,
                timezone=camera_settings.timezone,
                store_results=camera_settings.store_results,
                retention_days=camera_settings.retention_days,
                notify_on_completion=camera_settings.notify_on_completion,
                notify_on_failures=camera_settings.notify_on_failures,
                created_at=camera_settings.created_at,
                updated_at=camera_settings.updated_at,
            )

            return config

        except Exception as e:
            logger.error(f"Error getting camera automation config: {e}")
            return None
        finally:
            db.close()

    async def update_camera_automation_config(
        self, config: CameraAutomationConfig
    ) -> bool:
        """Update automation configuration for a camera."""
        db = SessionLocal()
        try:
            # Update or create camera settings
            camera_settings = (
                db.query(CameraSettings)
                .filter(
                    and_(
                        CameraSettings.camera_device_id == config.camera_device_id,
                        CameraSettings.user_id == config.user_id,
                    )
                )
                .first()
            )

            if not camera_settings:
                # Create new settings
                camera_settings = CameraSettings(
                    camera_device_id=config.camera_device_id, user_id=config.user_id
                )
                db.add(camera_settings)

            # Update all settings
            camera_settings.auto_face_detection_enabled = (
                config.auto_face_detection_enabled
            )
            camera_settings.automation_trigger = config.automation_trigger.value
            camera_settings.processing_interval = config.processing_interval.value
            camera_settings.custom_interval_minutes = config.custom_interval_minutes
            camera_settings.detection_methods = config.detection_methods
            camera_settings.confidence_threshold = config.confidence_threshold
            camera_settings.max_faces_per_frame = config.max_faces_per_frame
            camera_settings.priority = config.priority
            camera_settings.batch_processing = config.batch_processing
            camera_settings.max_batch_size = config.max_batch_size
            camera_settings.active_hours_start = config.active_hours_start
            camera_settings.active_hours_end = config.active_hours_end
            camera_settings.timezone = config.timezone
            camera_settings.store_results = config.store_results
            camera_settings.retention_days = config.retention_days
            camera_settings.notify_on_completion = config.notify_on_completion
            camera_settings.notify_on_failures = config.notify_on_failures
            camera_settings.updated_at = datetime.now()

            db.commit()

            # Update in-memory cache
            cache_key = f"{config.camera_device_id}:{config.user_id}"
            self.automation_configs[cache_key] = config

            # Handle automation scheduling changes
            await self._update_automation_schedule(config)

            logger.info(
                f"Updated automation config for camera {config.camera_device_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating camera automation config: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    async def _update_automation_schedule(self, config: CameraAutomationConfig):
        """Update automation scheduling for a camera based on configuration."""
        schedule_key = f"{config.camera_device_id}:{config.user_id}"

        # Cancel existing schedule
        if schedule_key in self._active_schedules:
            self._active_schedules[schedule_key].cancel()
            del self._active_schedules[schedule_key]

        # Create new schedule if automation is enabled and interval-based
        if (
            config.auto_face_detection_enabled
            and config.automation_trigger == AutomationTrigger.TIME_INTERVAL
        ):

            interval_seconds = self._get_interval_seconds(
                config.processing_interval, config.custom_interval_minutes
            )

            if interval_seconds > 0:
                task = asyncio.create_task(
                    self._run_interval_automation(config, interval_seconds)
                )
                self._active_schedules[schedule_key] = task
                logger.info(
                    f"Started interval automation for camera {config.camera_device_id} "
                    f"(interval: {interval_seconds}s)"
                )

    def _get_interval_seconds(
        self, interval: ProcessingInterval, custom_minutes: Optional[int]
    ) -> int:
        """Convert processing interval to seconds."""
        interval_map = {
            ProcessingInterval.HOURLY: 3600,
            ProcessingInterval.EVERY_2_HOURS: 7200,
            ProcessingInterval.EVERY_6_HOURS: 21600,
            ProcessingInterval.DAILY: 86400,
            ProcessingInterval.WEEKLY: 604800,
        }

        if interval == ProcessingInterval.CUSTOM and custom_minutes:
            return custom_minutes * 60

        return interval_map.get(interval, 0)

    async def _run_interval_automation(
        self, config: CameraAutomationConfig, interval_seconds: int
    ):
        """Run interval-based automation for a camera."""
        logger.info(
            f"Starting interval automation for camera {config.camera_device_id}"
        )

        while True:
            try:
                await asyncio.sleep(interval_seconds)

                # Check if we're in active hours
                if not self._is_in_active_hours(config):
                    logger.debug(
                        f"Outside active hours for camera {config.camera_device_id}"
                    )
                    continue

                # Get unprocessed recordings for this camera
                unprocessed_media = await self._get_unprocessed_recordings(
                    config.camera_device_id, config.user_id
                )

                if not unprocessed_media:
                    logger.debug(
                        f"No unprocessed media for camera {config.camera_device_id}"
                    )
                    continue

                # Trigger batch processing
                await self._trigger_automated_processing(config, unprocessed_media)

            except asyncio.CancelledError:
                logger.info(
                    f"Interval automation cancelled for camera {config.camera_device_id}"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error in interval automation for camera {config.camera_device_id}: {e}"
                )
                # Continue running despite errors

    def _is_in_active_hours(self, config: CameraAutomationConfig) -> bool:
        """Check if current time is within active hours for automation."""
        if not config.active_hours_start or not config.active_hours_end:
            return True  # No time restrictions

        try:
            from datetime import datetime, time

            import pytz

            # Get current time in specified timezone
            tz = pytz.timezone(config.timezone)
            current_time = datetime.now(tz).time()

            # Parse active hours
            start_time = time.fromisoformat(config.active_hours_start)
            end_time = time.fromisoformat(config.active_hours_end)

            # Check if current time is within range
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:
                # Handle overnight range (e.g., 22:00 to 06:00)
                return current_time >= start_time or current_time <= end_time

        except Exception as e:
            logger.error(f"Error checking active hours: {e}")
            return True  # Default to allowing processing

    async def _get_unprocessed_recordings(
        self, camera_device_id: str, user_id: str
    ) -> List[str]:
        """Get list of unprocessed media IDs for a camera."""
        try:
            # Query Camera Service for recent recordings
            camera_client = self.service_manager.camera_client
            recordings_response = await camera_client.get_camera_recordings(
                camera_device_id, limit=100
            )

            if not recordings_response:
                return []

            # Filter for recordings that haven't been processed
            media_ids = []
            db = SessionLocal()

            try:
                for recording in recordings_response.get("recordings", []):
                    media_id = recording.get("id")
                    if not media_id:
                        continue

                    # Check if this media has been processed
                    existing_workflow = (
                        db.query(CameraWorkflow)
                        .filter(
                            and_(
                                CameraWorkflow.camera_device_id == camera_device_id,
                                CameraWorkflow.media_id == media_id,
                                CameraWorkflow.user_id == user_id,
                            )
                        )
                        .first()
                    )

                    if not existing_workflow:
                        media_ids.append(media_id)

                return media_ids

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting unprocessed recordings: {e}")
            return []

    async def _trigger_automated_processing(
        self, config: CameraAutomationConfig, media_ids: List[str]
    ):
        """Trigger automated face detection processing for media."""
        try:
            if not media_ids:
                return

            # Limit batch size
            if config.batch_processing and len(media_ids) > config.max_batch_size:
                media_ids = media_ids[: config.max_batch_size]

            logger.info(
                f"Triggering automated processing for {len(media_ids)} media files "
                f"from camera {config.camera_device_id}"
            )

            # Start bulk processing workflow
            workflow = await self.workflow_orchestrator.start_bulk_processing(
                media_ids=media_ids,
                methods=config.detection_methods,
                user_id=config.user_id,
                processing_options={
                    "confidence_threshold": config.confidence_threshold,
                    "max_faces_per_frame": config.max_faces_per_frame,
                    "camera_device_id": config.camera_device_id,
                    "automated_trigger": True,
                    "automation_config": {
                        "trigger": config.automation_trigger.value,
                        "interval": config.processing_interval.value,
                    },
                },
                priority=config.priority,
            )

            if workflow:
                logger.info(
                    f"Started automated workflow {workflow.workflow_id} "
                    f"for camera {config.camera_device_id}"
                )

        except Exception as e:
            logger.error(f"Error triggering automated processing: {e}")

    async def handle_recording_completion_trigger(
        self, camera_device_id: str, user_id: str, media_id: str
    ) -> bool:
        """Handle automation trigger when a recording is completed."""
        try:
            # Get automation config for this camera
            config = await self.get_camera_automation_config(camera_device_id, user_id)

            if not config or not config.auto_face_detection_enabled:
                return False

            # Check if this trigger type is enabled
            if config.automation_trigger != AutomationTrigger.RECORDING_COMPLETION:
                return False

            # Check active hours
            if not self._is_in_active_hours(config):
                logger.debug(f"Outside active hours for camera {camera_device_id}")
                return False

            # Trigger processing for this specific media
            await self._trigger_automated_processing(config, [media_id])

            return True

        except Exception as e:
            logger.error(f"Error handling recording completion trigger: {e}")
            return False

    async def get_camera_automation_stats(
        self, camera_device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Get automation statistics for a camera."""
        db = SessionLocal()
        try:
            # Get automation config
            config = await self.get_camera_automation_config(camera_device_id, user_id)

            # Get workflow statistics
            workflow_stats = (
                db.query(
                    func.count(CameraWorkflow.id).label("total_workflows"),
                    func.count(CameraWorkflow.id)
                    .filter(CameraWorkflow.status == "completed")
                    .label("completed"),
                    func.count(CameraWorkflow.id)
                    .filter(CameraWorkflow.status == "failed")
                    .label("failed"),
                    func.avg(CameraWorkflow.processing_duration_seconds).label(
                        "avg_duration"
                    ),
                )
                .filter(
                    and_(
                        CameraWorkflow.camera_device_id == camera_device_id,
                        CameraWorkflow.user_id == user_id,
                    )
                )
                .first()
            )

            # Check if automation is currently active
            schedule_key = f"{camera_device_id}:{user_id}"
            is_scheduled = schedule_key in self._active_schedules

            return {
                "camera_device_id": camera_device_id,
                "automation_enabled": (
                    config.auto_face_detection_enabled if config else False
                ),
                "automation_trigger": (
                    config.automation_trigger.value if config else None
                ),
                "processing_interval": (
                    config.processing_interval.value if config else None
                ),
                "is_scheduled": is_scheduled,
                "total_workflows": workflow_stats.total_workflows or 0,
                "completed_workflows": workflow_stats.completed or 0,
                "failed_workflows": workflow_stats.failed or 0,
                "average_processing_duration": float(workflow_stats.avg_duration or 0),
                "last_updated": config.updated_at.isoformat() if config else None,
            }

        except Exception as e:
            logger.error(f"Error getting camera automation stats: {e}")
            return {"camera_device_id": camera_device_id, "error": str(e)}
        finally:
            db.close()

    async def cleanup_expired_schedules(self):
        """Clean up expired or invalid automation schedules."""
        expired_keys = []

        for schedule_key, task in self._active_schedules.items():
            if task.done() or task.cancelled():
                expired_keys.append(schedule_key)

        for key in expired_keys:
            del self._active_schedules[key]
            logger.info(f"Cleaned up expired schedule: {key}")

    async def shutdown(self):
        """Shutdown automation manager and cancel all schedules."""
        logger.info("Shutting down camera automation manager...")

        for task in self._active_schedules.values():
            task.cancel()

        # Wait for tasks to complete cancellation
        if self._active_schedules:
            await asyncio.gather(
                *self._active_schedules.values(), return_exceptions=True
            )

        self._active_schedules.clear()
        logger.info("Camera automation manager shutdown complete")

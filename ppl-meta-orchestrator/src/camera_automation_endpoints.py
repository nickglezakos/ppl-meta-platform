"""
PPL Meta Orchestrator - Camera Automation API Endpoints
Phase 2.1 Implementation: Camera settings management and automation controls
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from camera_automation import (
    AutomationTrigger,
    CameraAutomationConfig,
    CameraAutomationManager,
    ProcessingInterval,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create router for camera automation endpoints
automation_router = APIRouter(prefix="/camera-automation", tags=["automation"])


class CameraSettingsRequest(BaseModel):
    """Request model for camera automation settings."""

    camera_device_id: str
    auto_face_detection_enabled: bool = True
    automation_trigger: str = "recording_completion"
    processing_interval: str = "immediate"
    custom_interval_minutes: Optional[int] = None

    # Face detection settings
    detection_methods: List[str] = Field(default_factory=lambda: ["mtcnn"])
    confidence_threshold: float = Field(default=0.8, ge=0.1, le=1.0)
    max_faces_per_frame: int = Field(default=10, ge=1, le=100)

    # Processing preferences
    priority: str = Field(default="normal", regex="^(low|normal|high)$")
    batch_processing: bool = True
    max_batch_size: int = Field(default=50, ge=1, le=1000)

    # Time-based settings
    active_hours_start: Optional[str] = Field(
        None, regex="^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    active_hours_end: Optional[str] = Field(
        None, regex="^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    timezone: str = "UTC"

    # Storage and retention
    store_results: bool = True
    retention_days: Optional[int] = Field(None, ge=1, le=365)

    # Notification settings
    notify_on_completion: bool = False
    notify_on_failures: bool = True


class CameraSettingsResponse(BaseModel):
    """Response model for camera automation settings."""

    camera_device_id: str
    user_id: str
    auto_face_detection_enabled: bool
    automation_trigger: str
    processing_interval: str
    custom_interval_minutes: Optional[int]
    detection_methods: List[str]
    confidence_threshold: float
    max_faces_per_frame: int
    priority: str
    batch_processing: bool
    max_batch_size: int
    active_hours_start: Optional[str]
    active_hours_end: Optional[str]
    timezone: str
    store_results: bool
    retention_days: Optional[int]
    notify_on_completion: bool
    notify_on_failures: bool
    created_at: datetime
    updated_at: datetime


class CameraAutomationStatsResponse(BaseModel):
    """Response model for camera automation statistics."""

    camera_device_id: str
    automation_enabled: bool
    automation_trigger: Optional[str]
    processing_interval: Optional[str]
    is_scheduled: bool
    total_workflows: int
    completed_workflows: int
    failed_workflows: int
    average_processing_duration: float
    last_updated: Optional[str]


class CameraAutomationEndpoints:
    """Camera automation API endpoints for user settings and controls."""

    def __init__(self, automation_manager: CameraAutomationManager):
        self.automation_manager = automation_manager

    async def get_camera_settings(
        self, camera_device_id: str, user_id: str
    ) -> CameraSettingsResponse:
        """Get automation settings for a specific camera."""
        try:
            config = await self.automation_manager.get_camera_automation_config(
                camera_device_id, user_id
            )

            if not config:
                # Return default settings if none exist
                config = CameraAutomationConfig(
                    camera_device_id=camera_device_id, user_id=user_id
                )

            return CameraSettingsResponse(
                camera_device_id=config.camera_device_id,
                user_id=config.user_id,
                auto_face_detection_enabled=config.auto_face_detection_enabled,
                automation_trigger=config.automation_trigger.value,
                processing_interval=config.processing_interval.value,
                custom_interval_minutes=config.custom_interval_minutes,
                detection_methods=config.detection_methods,
                confidence_threshold=config.confidence_threshold,
                max_faces_per_frame=config.max_faces_per_frame,
                priority=config.priority,
                batch_processing=config.batch_processing,
                max_batch_size=config.max_batch_size,
                active_hours_start=config.active_hours_start,
                active_hours_end=config.active_hours_end,
                timezone=config.timezone,
                store_results=config.store_results,
                retention_days=config.retention_days,
                notify_on_completion=config.notify_on_completion,
                notify_on_failures=config.notify_on_failures,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )

        except Exception as e:
            logger.error(f"Error getting camera settings: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get camera settings: {str(e)}"
            )

    async def update_camera_settings(
        self, camera_device_id: str, user_id: str, settings: CameraSettingsRequest
    ) -> CameraSettingsResponse:
        """Update automation settings for a camera."""
        try:
            # Validate automation trigger and processing interval
            try:
                automation_trigger = AutomationTrigger(settings.automation_trigger)
                processing_interval = ProcessingInterval(settings.processing_interval)
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid automation settings: {str(e)}"
                )

            # Validate custom interval if specified
            if (
                processing_interval == ProcessingInterval.CUSTOM
                and not settings.custom_interval_minutes
            ):
                raise HTTPException(
                    status_code=400,
                    detail="custom_interval_minutes required when using custom interval",
                )

            # Create automation config
            config = CameraAutomationConfig(
                camera_device_id=camera_device_id,
                user_id=user_id,
                auto_face_detection_enabled=settings.auto_face_detection_enabled,
                automation_trigger=automation_trigger,
                processing_interval=processing_interval,
                custom_interval_minutes=settings.custom_interval_minutes,
                detection_methods=settings.detection_methods,
                confidence_threshold=settings.confidence_threshold,
                max_faces_per_frame=settings.max_faces_per_frame,
                priority=settings.priority,
                batch_processing=settings.batch_processing,
                max_batch_size=settings.max_batch_size,
                active_hours_start=settings.active_hours_start,
                active_hours_end=settings.active_hours_end,
                timezone=settings.timezone,
                store_results=settings.store_results,
                retention_days=settings.retention_days,
                notify_on_completion=settings.notify_on_completion,
                notify_on_failures=settings.notify_on_failures,
            )

            # Update configuration
            success = await self.automation_manager.update_camera_automation_config(
                config
            )

            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update camera automation settings",
                )

            # Return updated settings
            return await self.get_camera_settings(camera_device_id, user_id)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating camera settings: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to update camera settings: {str(e)}"
            )

    async def get_camera_automation_stats(
        self, camera_device_id: str, user_id: str
    ) -> CameraAutomationStatsResponse:
        """Get automation statistics for a camera."""
        try:
            stats = await self.automation_manager.get_camera_automation_stats(
                camera_device_id, user_id
            )

            return CameraAutomationStatsResponse(**stats)

        except Exception as e:
            logger.error(f"Error getting camera automation stats: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get automation stats: {str(e)}"
            )

    async def trigger_manual_processing(
        self, camera_device_id: str, user_id: str, media_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Manually trigger face detection processing for a camera."""
        try:
            # Get automation config
            config = await self.automation_manager.get_camera_automation_config(
                camera_device_id, user_id
            )

            if not config:
                raise HTTPException(
                    status_code=404, detail="Camera automation settings not found"
                )

            # If no media IDs specified, get unprocessed recordings
            if not media_ids:
                media_ids = await self.automation_manager._get_unprocessed_recordings(
                    camera_device_id, user_id
                )

            if not media_ids:
                return {
                    "status": "success",
                    "message": "No media files available for processing",
                    "processed_count": 0,
                }

            # Trigger processing
            await self.automation_manager._trigger_automated_processing(
                config, media_ids
            )

            return {
                "status": "success",
                "message": f"Manual processing triggered for {len(media_ids)} media files",
                "processed_count": len(media_ids),
                "camera_device_id": camera_device_id,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error triggering manual processing: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to trigger manual processing: {str(e)}"
            )

    async def get_available_automation_options(self) -> Dict[str, Any]:
        """Get available automation trigger types and processing intervals."""
        return {
            "automation_triggers": [
                {
                    "value": trigger.value,
                    "label": trigger.value.replace("_", " ").title(),
                    "description": self._get_trigger_description(trigger),
                }
                for trigger in AutomationTrigger
            ],
            "processing_intervals": [
                {
                    "value": interval.value,
                    "label": interval.value.replace("_", " ").title(),
                    "description": self._get_interval_description(interval),
                }
                for interval in ProcessingInterval
            ],
            "detection_methods": [
                {
                    "value": "haar",
                    "label": "Haar Cascade",
                    "description": "Fast, basic face detection",
                },
                {
                    "value": "dlib",
                    "label": "DLib HOG",
                    "description": "Balanced speed and accuracy",
                },
                {
                    "value": "mtcnn",
                    "label": "MTCNN",
                    "description": "High accuracy, slower processing",
                },
                {
                    "value": "two_stage",
                    "label": "Two-Stage",
                    "description": "Best accuracy, slowest processing",
                },
            ],
            "priority_levels": [
                {"value": "low", "description": "Background processing"},
                {"value": "normal", "description": "Standard processing"},
                {"value": "high", "description": "Priority processing"},
            ],
        }

    def _get_trigger_description(self, trigger: AutomationTrigger) -> str:
        """Get description for automation trigger."""
        descriptions = {
            AutomationTrigger.MANUAL: "Process only when manually triggered",
            AutomationTrigger.RECORDING_COMPLETION: "Process immediately after recording",
            AutomationTrigger.TIME_INTERVAL: "Process at regular time intervals",
            AutomationTrigger.SCHEDULED: "Process at specific scheduled times",
            AutomationTrigger.CONTINUOUS: "Continuous real-time processing",
        }
        return descriptions.get(trigger, "Unknown trigger type")

    def _get_interval_description(self, interval: ProcessingInterval) -> str:
        """Get description for processing interval."""
        descriptions = {
            ProcessingInterval.IMMEDIATE: "Process immediately",
            ProcessingInterval.HOURLY: "Process every hour",
            ProcessingInterval.EVERY_2_HOURS: "Process every 2 hours",
            ProcessingInterval.EVERY_6_HOURS: "Process every 6 hours",
            ProcessingInterval.DAILY: "Process once per day",
            ProcessingInterval.WEEKLY: "Process once per week",
            ProcessingInterval.CUSTOM: "Process at custom interval",
        }
        return descriptions.get(interval, "Unknown interval")


# FastAPI endpoint definitions
@automation_router.get("/cameras/{camera_device_id}/settings")
async def get_camera_automation_settings_endpoint(
    camera_device_id: str, user_id: str
) -> CameraSettingsResponse:
    """Get automation settings for a specific camera."""
    from main import automation_endpoints

    if automation_endpoints is None:
        raise HTTPException(status_code=503, detail="Camera automation not initialized")

    return await automation_endpoints.get_camera_settings(camera_device_id, user_id)


@automation_router.put("/cameras/{camera_device_id}/settings")
async def update_camera_automation_settings_endpoint(
    camera_device_id: str, user_id: str, settings: CameraSettingsRequest
) -> CameraSettingsResponse:
    """Update automation settings for a camera."""
    from main import automation_endpoints

    if automation_endpoints is None:
        raise HTTPException(status_code=503, detail="Camera automation not initialized")

    return await automation_endpoints.update_camera_settings(
        camera_device_id, user_id, settings
    )


@automation_router.get("/cameras/{camera_device_id}/stats")
async def get_camera_automation_stats_endpoint(
    camera_device_id: str, user_id: str
) -> CameraAutomationStatsResponse:
    """Get automation statistics for a camera."""
    from main import automation_endpoints

    if automation_endpoints is None:
        raise HTTPException(status_code=503, detail="Camera automation not initialized")

    return await automation_endpoints.get_camera_automation_stats(
        camera_device_id, user_id
    )


@automation_router.post("/cameras/{camera_device_id}/process")
async def trigger_manual_processing_endpoint(
    camera_device_id: str, user_id: str, media_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Manually trigger face detection processing for a camera."""
    from main import automation_endpoints

    if automation_endpoints is None:
        raise HTTPException(status_code=503, detail="Camera automation not initialized")

    return await automation_endpoints.trigger_manual_processing(
        camera_device_id, user_id, media_ids
    )


@automation_router.get("/options")
async def get_automation_options_endpoint() -> Dict[str, Any]:
    """Get available automation trigger types and processing intervals."""
    from main import automation_endpoints

    if automation_endpoints is None:
        raise HTTPException(status_code=503, detail="Camera automation not initialized")

    return await automation_endpoints.get_available_automation_options()


@automation_router.get("/health")
async def automation_health_check() -> Dict[str, Any]:
    """Health check for camera automation functionality."""
    return {
        "status": "healthy",
        "component": "camera_automation",
        "capabilities": [
            "camera_settings_management",
            "interval_scheduling",
            "automated_triggers",
            "manual_processing",
            "automation_stats",
        ],
        "timestamp": datetime.now().isoformat(),
    }

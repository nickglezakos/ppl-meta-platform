"""
PPL Meta Orchestrator - Camera Event Publishing API Endpoints
Phase 2.2 Implementation: Camera Service webhook integration and event management
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from camera_event_publisher import CameraEventPublisher, CameraEventWebhookHandler
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create router for camera event endpoints
events_router = APIRouter(prefix="/camera-events", tags=["camera-events"])


class WebhookRegistrationRequest(BaseModel):
    """Request model for webhook registration."""

    camera_device_id: str
    user_id: str


class WebhookEventRequest(BaseModel):
    """Request model for incoming webhook events."""

    event_type: str
    camera_device_id: str
    user_id: str
    recording_data: Dict[str, Any]
    timestamp: Optional[datetime] = None


class CameraEventStatsResponse(BaseModel):
    """Response model for camera event statistics."""

    camera_device_id: str
    webhook_registered: bool
    polling_active: bool
    integration_method: str
    last_event_time: Optional[str]
    events_processed_today: int
    automation_success_rate: float


class CameraEventEndpoints:
    """Camera event publishing API endpoints."""

    def __init__(self, event_publisher: CameraEventPublisher):
        self.event_publisher = event_publisher
        self.webhook_handler = CameraEventWebhookHandler(event_publisher)

    async def register_camera_webhook(
        self, camera_device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Register webhook for camera recording events."""
        try:
            success = await self.event_publisher.register_camera_webhook(
                camera_device_id, user_id
            )

            if success:
                return {
                    "status": "success",
                    "message": f"Webhook registered for camera {camera_device_id}",
                    "camera_device_id": camera_device_id,
                    "webhook_url": "http://localhost:8002/camera-events/webhook",
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to register webhook with Camera Service",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering webhook: {e}")
            raise HTTPException(
                status_code=500, detail=f"Webhook registration failed: {str(e)}"
            )

    async def unregister_camera_webhook(
        self, camera_device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Unregister webhook for camera recording events."""
        try:
            success = await self.event_publisher.unregister_camera_webhook(
                camera_device_id, user_id
            )

            if success:
                return {
                    "status": "success",
                    "message": f"Webhook unregistered for camera {camera_device_id}",
                    "camera_device_id": camera_device_id,
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to unregister webhook with Camera Service",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error unregistering webhook: {e}")
            raise HTTPException(
                status_code=500, detail=f"Webhook unregistration failed: {str(e)}"
            )

    async def handle_incoming_webhook(
        self, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle incoming webhook from Camera Service."""
        try:
            result = await self.webhook_handler.handle_webhook(request_data)
            return result

        except Exception as e:
            logger.error(f"Error handling incoming webhook: {e}")
            raise HTTPException(
                status_code=500, detail=f"Webhook processing failed: {str(e)}"
            )

    async def get_camera_event_stats(
        self, camera_device_id: str, user_id: str
    ) -> CameraEventStatsResponse:
        """Get event processing statistics for a camera."""
        try:
            stats = await self.event_publisher.get_camera_event_stats(
                camera_device_id, user_id
            )

            return CameraEventStatsResponse(**stats)

        except Exception as e:
            logger.error(f"Error getting camera event stats: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get event stats: {str(e)}"
            )

    async def register_all_user_cameras(self, user_id: str) -> Dict[str, Any]:
        """Register webhooks for all cameras belonging to a user."""
        try:
            result = await self.event_publisher.register_all_user_cameras(user_id)
            return result

        except Exception as e:
            logger.error(f"Error registering all user cameras: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to register user cameras: {str(e)}"
            )

    async def start_camera_polling(
        self, camera_device_id: str, user_id: str, interval: int = 30
    ) -> Dict[str, Any]:
        """Start polling for camera events (fallback method)."""
        try:
            await self.event_publisher.start_camera_polling(
                camera_device_id, user_id, interval
            )

            return {
                "status": "success",
                "message": f"Started polling for camera {camera_device_id}",
                "camera_device_id": camera_device_id,
                "polling_interval": interval,
            }

        except Exception as e:
            logger.error(f"Error starting camera polling: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to start polling: {str(e)}"
            )

    async def stop_camera_polling(
        self, camera_device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Stop polling for camera events."""
        try:
            await self.event_publisher.stop_camera_polling(camera_device_id, user_id)

            return {
                "status": "success",
                "message": f"Stopped polling for camera {camera_device_id}",
                "camera_device_id": camera_device_id,
            }

        except Exception as e:
            logger.error(f"Error stopping camera polling: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to stop polling: {str(e)}"
            )


# FastAPI endpoint definitions
@events_router.post("/cameras/{camera_device_id}/webhook/register")
async def register_camera_webhook_endpoint(
    camera_device_id: str, user_id: str
) -> Dict[str, Any]:
    """Register webhook for camera recording events."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    return await event_endpoints.register_camera_webhook(camera_device_id, user_id)


@events_router.delete("/cameras/{camera_device_id}/webhook/unregister")
async def unregister_camera_webhook_endpoint(
    camera_device_id: str, user_id: str
) -> Dict[str, Any]:
    """Unregister webhook for camera recording events."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    return await event_endpoints.unregister_camera_webhook(camera_device_id, user_id)


@events_router.post("/webhook")
async def handle_camera_webhook_endpoint(request: Request) -> Dict[str, Any]:
    """Handle incoming webhook from Camera Service."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    try:
        request_data = await request.json()
        return await event_endpoints.handle_incoming_webhook(request_data)
    except Exception as e:
        logger.error(f"Error processing webhook request: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook request format")


@events_router.get("/cameras/{camera_device_id}/stats")
async def get_camera_event_stats_endpoint(
    camera_device_id: str, user_id: str
) -> CameraEventStatsResponse:
    """Get event processing statistics for a camera."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    return await event_endpoints.get_camera_event_stats(camera_device_id, user_id)


@events_router.post("/users/{user_id}/cameras/register-all")
async def register_all_user_cameras_endpoint(user_id: str) -> Dict[str, Any]:
    """Register webhooks for all cameras belonging to a user."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    return await event_endpoints.register_all_user_cameras(user_id)


@events_router.post("/cameras/{camera_device_id}/polling/start")
async def start_camera_polling_endpoint(
    camera_device_id: str, user_id: str, interval: int = 30
) -> Dict[str, Any]:
    """Start polling for camera events (fallback method)."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    return await event_endpoints.start_camera_polling(
        camera_device_id, user_id, interval
    )


@events_router.post("/cameras/{camera_device_id}/polling/stop")
async def stop_camera_polling_endpoint(
    camera_device_id: str, user_id: str
) -> Dict[str, Any]:
    """Stop polling for camera events."""
    from main import event_endpoints

    if event_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Camera event publisher not initialized"
        )

    return await event_endpoints.stop_camera_polling(camera_device_id, user_id)


@events_router.get("/health")
async def camera_events_health_check() -> Dict[str, Any]:
    """Health check for camera event publishing functionality."""
    return {
        "status": "healthy",
        "component": "camera_event_publisher",
        "capabilities": [
            "webhook_registration",
            "event_processing",
            "camera_polling",
            "automation_triggers",
            "event_statistics",
        ],
        "timestamp": datetime.now().isoformat(),
    }

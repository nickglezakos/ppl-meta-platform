"""
PPL Meta Orchestrator - Camera Event Publishing Integration
Phase 2.2 Implementation: Camera Service integration for recording completion events
Phase 4 Integration: Recording session database persistence
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

# Phase 4 imports for session tracking
from models.recording_session import SessionStatus
from service_clients import ServiceClientManager
from services.recording_session_service import RecordingSessionService

logger = logging.getLogger(__name__)


class CameraEventPublisher:
    """
    Handles publishing and subscribing to camera events for automated workflows.
    """

    def __init__(
        self,
        service_manager: ServiceClientManager,
        automation_manager=None,  # Will be passed in to avoid circular imports
    ):
        self.service_manager = service_manager
        self.automation_manager = automation_manager
        self.session_service = RecordingSessionService()  # Phase 4 session tracking
        self._event_subscribers: Dict[str, List[callable]] = {}
        self._polling_tasks: Dict[str, asyncio.Task] = {}
        self._webhook_server_task: Optional[asyncio.Task] = None

    async def register_camera_webhook(
        self, camera_device_id: str, user_id: str
    ) -> bool:
        """Register webhook with Camera Service for recording completion events."""
        try:
            camera_client = self.service_manager.camera_client

            # Webhook URL pointing to our orchestrator service
            webhook_url = "http://localhost:8002/camera-events/webhook"

            # Register webhook with Camera Service
            webhook_data = {
                "camera_device_id": camera_device_id,
                "user_id": user_id,
                "webhook_url": webhook_url,
                "event_types": ["recording_completed", "recording_failed"],
                "active": True,
                "metadata": {
                    "registered_by": "orchestrator",
                    "purpose": "automated_face_detection",
                    "timestamp": datetime.now().isoformat(),
                },
            }

            response = await camera_client.register_webhook(webhook_data)

            if response:
                logger.info(
                    f"Successfully registered webhook for camera {camera_device_id}"
                )
                return True
            else:
                logger.error(
                    f"Failed to register webhook for camera {camera_device_id}"
                )
                return False

        except Exception as e:
            logger.error(f"Error registering camera webhook: {e}")
            return False

    async def unregister_camera_webhook(
        self, camera_device_id: str, user_id: str
    ) -> bool:
        """Unregister webhook from Camera Service."""
        try:
            camera_client = self.service_manager.camera_client

            response = await camera_client.unregister_webhook(camera_device_id, user_id)

            if response:
                logger.info(
                    f"Successfully unregistered webhook for camera {camera_device_id}"
                )
                return True
            else:
                logger.error(
                    f"Failed to unregister webhook for camera {camera_device_id}"
                )
                return False

        except Exception as e:
            logger.error(f"Error unregistering camera webhook: {e}")
            return False

    async def process_camera_webhook_event(
        self, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process incoming webhook event from Camera Service."""
        try:
            event_type = event_data.get("event_type")
            camera_device_id = event_data.get("camera_device_id")
            user_id = event_data.get("user_id")
            recording_data = event_data.get("recording_data", {})

            logger.info(
                f"Processing webhook event: {event_type} for camera {camera_device_id}"
            )

            # Handle recording completion events
            if event_type == "recording_completed":
                return await self._handle_recording_completed(
                    camera_device_id, user_id, recording_data
                )
            elif event_type == "recording_failed":
                return await self._handle_recording_failed(
                    camera_device_id, user_id, recording_data
                )
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return {
                    "status": "ignored",
                    "message": f"Unknown event type: {event_type}",
                }

        except Exception as e:
            logger.error(f"Error processing camera webhook event: {e}")
            return {"status": "error", "message": f"Failed to process event: {str(e)}"}

    async def _handle_recording_completed(
        self, camera_device_id: str, user_id: str, recording_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle recording completion event with session tracking and automation."""
        try:
            # Extract recording information
            media_id = recording_data.get("id") or recording_data.get("recording_id")
            video_file_path = recording_data.get("file_path") or recording_data.get(
                "video_file_path"
            )
            duration = recording_data.get("duration_seconds") or recording_data.get(
                "recording_duration_seconds", 0
            )
            file_size = recording_data.get("file_size_bytes", 0)
            recording_session_id = recording_data.get("recording_session_id")

            if not media_id:
                logger.error("Recording completion event missing media_id")
                return {
                    "status": "error",
                    "message": "Missing media_id in recording data",
                }

            logger.info(
                f"Recording completed for camera {camera_device_id}: {media_id}"
            )

            # Phase 4: Update session status to completed
            session_updated = False
            if recording_session_id:
                session_updated = self.session_service.update_session_status(
                    session_uuid=recording_session_id, status=SessionStatus.COMPLETED
                )

                # Update final session progress
                if duration and file_size:
                    self.session_service.update_session_progress(
                        session_uuid=recording_session_id,
                        duration_seconds=float(duration),
                        estimated_file_size_bytes=int(file_size),
                        frames_recorded=int(float(duration) * 30),  # Estimate 30 FPS
                    )

                # Update media information
                self.session_service.update_media_upload_status(
                    session_uuid=recording_session_id,
                    completed=True,
                    media_uuid=media_id,
                )

                logger.info(
                    f"Session {recording_session_id} marked as completed: {session_updated}"
                )

            # Check if automation is enabled for this camera
            automation_triggered = False
            if self.automation_manager:
                automation_triggered = (
                    await self.automation_manager.handle_recording_completion_trigger(
                        camera_device_id, user_id, media_id
                    )
                )

            # Publish event to other subscribers
            await self._publish_event(
                "recording_completed",
                {
                    "camera_device_id": camera_device_id,
                    "user_id": user_id,
                    "media_id": media_id,
                    "video_file_path": video_file_path,
                    "duration_seconds": duration,
                    "file_size_bytes": file_size,
                    "recording_session_id": recording_session_id,
                    "automation_triggered": automation_triggered,
                    "session_updated": session_updated,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return {
                "status": "success",
                "message": "Recording completion processed",
                "automation_triggered": automation_triggered,
                "session_updated": session_updated,
                "media_id": media_id,
                "recording_session_id": recording_session_id,
            }

        except Exception as e:
            logger.error(f"Error handling recording completion: {e}")

            # Try to mark session as failed if session exists
            if recording_session_id:
                try:
                    self.session_service.update_session_status(
                        session_uuid=recording_session_id,
                        status=SessionStatus.FAILED,
                        error_message=f"Failed to process completion: {str(e)}",
                    )
                except Exception:
                    pass  # Don't fail if session update fails

            return {
                "status": "error",
                "message": f"Failed to handle recording completion: {str(e)}",
            }

    async def _handle_recording_failed(
        self, camera_device_id: str, user_id: str, recording_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle recording failure event with session tracking."""
        try:
            error_message = recording_data.get("error_message", "Unknown error")
            recording_session_id = recording_data.get("recording_session_id")

            logger.warning(
                f"Recording failed for camera {camera_device_id}: {error_message}"
            )

            # Phase 4: Update session status to failed
            session_updated = False
            if recording_session_id:
                session_updated = self.session_service.update_session_status(
                    session_uuid=recording_session_id,
                    status=SessionStatus.FAILED,
                    error_message=error_message,
                )
                logger.info(
                    f"Session {recording_session_id} marked as failed: {session_updated}"
                )

            # Publish failure event
            await self._publish_event(
                "recording_failed",
                {
                    "camera_device_id": camera_device_id,
                    "user_id": user_id,
                    "recording_session_id": recording_session_id,
                    "error_message": error_message,
                    "session_updated": session_updated,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return {
                "status": "acknowledged",
                "message": "Recording failure processed",
                "session_updated": session_updated,
                "recording_session_id": recording_session_id,
            }

        except Exception as e:
            logger.error(f"Error handling recording failure: {e}")
            return {
                "status": "error",
                "message": f"Failed to handle recording failure: {str(e)}",
            }

    async def handle_face_detection_completion(
        self, session_uuid: str, face_detection_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle face detection workflow completion for a recording session."""
        try:
            # Update session with face detection completion
            success = self.session_service.complete_face_detection(
                session_uuid=session_uuid, face_detection_results=face_detection_results
            )

            if success:
                logger.info(f"Face detection completed for session {session_uuid}")

                # Get session details for event publishing
                session = self.session_service.get_session(session_uuid)
                if session:
                    # Publish face detection completion event
                    await self._publish_event(
                        "face_detection_completed",
                        {
                            "session_uuid": session_uuid,
                            "camera_device_id": session.camera_device_id,
                            "user_id": session.user_id,
                            "workflow_execution_id": session.workflow_execution_id,
                            "face_detection_results": face_detection_results,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                return {
                    "status": "success",
                    "message": "Face detection completion recorded",
                    "session_uuid": session_uuid,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update face detection completion for session {session_uuid}",
                }

        except Exception as e:
            logger.error(f"Error handling face detection completion: {e}")
            return {
                "status": "error",
                "message": f"Failed to handle face detection completion: {str(e)}",
            }

    async def subscribe_to_events(self, event_type: str, callback: callable):
        """Subscribe to camera events."""
        if event_type not in self._event_subscribers:
            self._event_subscribers[event_type] = []

        self._event_subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type} events")

    async def _publish_event(self, event_type: str, event_data: Dict[str, Any]):
        """Publish event to all subscribers."""
        subscribers = self._event_subscribers.get(event_type, [])

        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Error in event subscriber callback: {e}")

    async def start_camera_polling(
        self, camera_device_id: str, user_id: str, interval: int = 30
    ):
        """Start polling Camera Service for new recordings (fallback method)."""
        if f"{camera_device_id}:{user_id}" in self._polling_tasks:
            logger.warning(f"Polling already active for camera {camera_device_id}")
            return

        async def poll_camera():
            last_check = datetime.now()

            while True:
                try:
                    await asyncio.sleep(interval)

                    # Get recent recordings from Camera Service
                    camera_client = self.service_manager.camera_client
                    recordings = await camera_client.get_camera_recordings(
                        camera_device_id, since=last_check, limit=50
                    )

                    if recordings:
                        for recording in recordings.get("recordings", []):
                            # Check if this is a new recording
                            recording_time = datetime.fromisoformat(
                                recording.get("created_at", "").replace("Z", "+00:00")
                            )

                            if recording_time > last_check:
                                # Process as recording completion event
                                await self._handle_recording_completed(
                                    camera_device_id, user_id, recording
                                )

                    last_check = datetime.now()

                except asyncio.CancelledError:
                    logger.info(f"Polling cancelled for camera {camera_device_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in camera polling: {e}")
                    # Continue polling despite errors

        task = asyncio.create_task(poll_camera())
        self._polling_tasks[f"{camera_device_id}:{user_id}"] = task
        logger.info(
            f"Started polling for camera {camera_device_id} (interval: {interval}s)"
        )

    async def stop_camera_polling(self, camera_device_id: str, user_id: str):
        """Stop polling for a specific camera."""
        key = f"{camera_device_id}:{user_id}"

        if key in self._polling_tasks:
            self._polling_tasks[key].cancel()
            del self._polling_tasks[key]
            logger.info(f"Stopped polling for camera {camera_device_id}")

    async def get_camera_event_stats(
        self, camera_device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Get event processing statistics for a camera."""
        try:
            # This would typically query a database for event statistics
            # For now, return basic information

            is_polling = f"{camera_device_id}:{user_id}" in self._polling_tasks
            has_webhook = await self._check_webhook_registration(
                camera_device_id, user_id
            )

            return {
                "camera_device_id": camera_device_id,
                "webhook_registered": has_webhook,
                "polling_active": is_polling,
                "integration_method": (
                    "webhook" if has_webhook else ("polling" if is_polling else "none")
                ),
                "last_event_time": None,  # Could be tracked in database
                "events_processed_today": 0,  # Could be tracked in database
                "automation_success_rate": 100.0,  # Could be calculated from database
            }

        except Exception as e:
            logger.error(f"Error getting camera event stats: {e}")
            return {"camera_device_id": camera_device_id, "error": str(e)}

    async def _check_webhook_registration(
        self, camera_device_id: str, user_id: str
    ) -> bool:
        """Check if webhook is registered with Camera Service."""
        try:
            camera_client = self.service_manager.camera_client
            webhooks = await camera_client.get_camera_webhooks(camera_device_id)

            if webhooks:
                for webhook in webhooks.get("webhooks", []):
                    if webhook.get("user_id") == user_id and webhook.get(
                        "active", False
                    ):
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking webhook registration: {e}")
            return False

    async def register_all_user_cameras(self, user_id: str) -> Dict[str, Any]:
        """Register webhooks for all cameras belonging to a user."""
        try:
            # Get all cameras for user from Camera Service
            camera_client = self.service_manager.camera_client
            cameras = await camera_client.get_user_cameras(user_id)

            if not cameras:
                return {
                    "status": "success",
                    "message": "No cameras found for user",
                    "registered_count": 0,
                }

            registered_count = 0
            failed_cameras = []

            for camera in cameras.get("cameras", []):
                camera_device_id = camera.get("device_id")
                if camera_device_id:
                    success = await self.register_camera_webhook(
                        camera_device_id, user_id
                    )
                    if success:
                        registered_count += 1
                    else:
                        failed_cameras.append(camera_device_id)

            return {
                "status": "success",
                "message": f"Registered webhooks for {registered_count} cameras",
                "registered_count": registered_count,
                "failed_cameras": failed_cameras,
                "total_cameras": len(cameras.get("cameras", [])),
            }

        except Exception as e:
            logger.error(f"Error registering all user cameras: {e}")
            return {
                "status": "error",
                "message": f"Failed to register user cameras: {str(e)}",
            }

    async def cleanup(self):
        """Cleanup all active polling tasks and subscriptions."""
        logger.info("Cleaning up camera event publisher...")

        # Cancel all polling tasks
        for task in self._polling_tasks.values():
            task.cancel()

        # Wait for tasks to complete cancellation
        if self._polling_tasks:
            await asyncio.gather(*self._polling_tasks.values(), return_exceptions=True)

        self._polling_tasks.clear()
        self._event_subscribers.clear()

        logger.info("Camera event publisher cleanup complete")


class CameraEventWebhookHandler:
    """Handles incoming webhook requests from Camera Service."""

    def __init__(self, event_publisher: CameraEventPublisher):
        self.event_publisher = event_publisher

    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook request."""
        try:
            # Validate webhook request
            if not self._validate_webhook_request(request_data):
                return {"status": "error", "message": "Invalid webhook request format"}

            # Process the event
            result = await self.event_publisher.process_camera_webhook_event(
                request_data
            )

            return result

        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {
                "status": "error",
                "message": f"Webhook processing failed: {str(e)}",
            }

    def _validate_webhook_request(self, request_data: Dict[str, Any]) -> bool:
        """Validate incoming webhook request format."""
        required_fields = ["event_type", "camera_device_id", "user_id"]

        for field in required_fields:
            if field not in request_data:
                logger.error(f"Missing required field in webhook: {field}")
                return False

        return True

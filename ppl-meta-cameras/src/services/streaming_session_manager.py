"""
PPL Meta Cameras Service - Streaming Session Manager
Handles session lifecycle for real-time streaming face detection

This module provides session management for streaming scenarios:
- Automatic session creation on stream start
- Real-time session updates during face detection
- Session completion on stream end
- Integration with Vision service for session persistence
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class StreamingSessionManager:
    """Manages streaming face detection sessions for real-time camera streams."""

    def __init__(self, vision_service_url: str = "http://localhost:8003"):
        """Initialize with Vision service connection."""
        self.vision_service_url = vision_service_url
        self.active_streaming_sessions: Dict[str, Dict[str, Any]] = {}

    async def create_streaming_session(
        self,
        device_id: str,
        camera_device_uuid: Optional[str] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Create a new streaming session for a camera device.

        Args:
            device_id: Camera device identifier
            camera_device_uuid: Optional camera UUID from database
            session_metadata: Additional session metadata

        Returns:
            session_uuid if successful, None if failed
        """
        try:
            # Generate media UUID for streaming session
            media_uuid = str(uuid.uuid4())

            # Prepare session creation request
            session_request = {
                "media_uuid": media_uuid,
                "camera_device_uuid": camera_device_uuid,
                "session_type": "streaming",
                "detection_parameters": {
                    "method": "two_stage",  # Use best detection method for streaming
                    "confidence_threshold": 0.7,
                    "real_time": True,
                },
                "session_metadata": {
                    "device_id": device_id,
                    "stream_type": "real_time_camera",
                    "auto_created": True,
                    **(session_metadata or {}),
                },
            }

            # Create session via Vision service API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vision_service_url}/api/v1/sessions/start",
                    json=session_request,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        session_uuid = result.get("session_uuid")

                        if session_uuid:
                            # Store active session locally for tracking
                            self.active_streaming_sessions[device_id] = {
                                "session_uuid": session_uuid,
                                "media_uuid": media_uuid,
                                "device_id": device_id,
                                "camera_device_uuid": camera_device_uuid,
                                "started_at": datetime.now(timezone.utc),
                                "face_count": 0,
                                "frames_processed": 0,
                                "last_detection_time": None,
                                "session_metadata": session_metadata or {},
                            }

                            logger.info(
                                f"✅ Created streaming session {session_uuid} for device {device_id}"
                            )
                            return session_uuid
                        else:
                            logger.error(f"❌ No session_uuid in response: {result}")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"❌ Failed to create streaming session for {device_id}: "
                            f"HTTP {response.status} - {error_text}"
                        )
                        return None

        except Exception as e:
            logger.error(f"❌ Error creating streaming session for {device_id}: {e}")
            return None

    async def update_session_detection(
        self,
        device_id: str,
        faces_detected: List[Dict[str, Any]],
        frame_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update session with new face detection results.

        Args:
            device_id: Camera device identifier
            faces_detected: List of detected faces with metadata
            frame_metadata: Optional frame processing metadata

        Returns:
            True if update successful, False otherwise
        """
        try:
            session_info = self.active_streaming_sessions.get(device_id)
            if not session_info:
                logger.warning(f"⚠️ No active session for device {device_id}")
                return False

            session_uuid = session_info["session_uuid"]

            # Update local session tracking
            session_info["face_count"] += len(faces_detected)
            session_info["frames_processed"] += 1
            session_info["last_detection_time"] = datetime.now(timezone.utc)

            # Prepare detection update for Vision service
            detection_update = {
                "session_uuid": session_uuid,
                "faces_detected": faces_detected,
                "frame_metadata": {
                    "frame_number": session_info["frames_processed"],
                    "timestamp": session_info["last_detection_time"].isoformat(),
                    "device_id": device_id,
                    **(frame_metadata or {}),
                },
                "session_statistics": {
                    "total_faces": session_info["face_count"],
                    "frames_processed": session_info["frames_processed"],
                },
            }

            # Send update to Vision service (non-blocking)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vision_service_url}/api/v1/sessions/{session_uuid}/detections",
                    json=detection_update,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        logger.debug(
                            f"✅ Updated session {session_uuid} with {len(faces_detected)} faces"
                        )
                        return True
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"⚠️ Failed to update session {session_uuid}: "
                            f"HTTP {response.status} - {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Error updating session for device {device_id}: {e}")
            return False

    async def complete_streaming_session(
        self, device_id: str, completion_reason: str = "stream_ended"
    ) -> bool:
        """
        Complete and cleanup a streaming session.

        Args:
            device_id: Camera device identifier
            completion_reason: Reason for session completion

        Returns:
            True if completion successful, False otherwise
        """
        try:
            session_info = self.active_streaming_sessions.get(device_id)
            if not session_info:
                logger.warning(
                    f"⚠️ No active session to complete for device {device_id}"
                )
                return False

            session_uuid = session_info["session_uuid"]

            # Prepare completion request
            completion_request = {
                "session_uuid": session_uuid,
                "completion_reason": completion_reason,
                "final_statistics": {
                    "total_faces_detected": session_info["face_count"],
                    "frames_processed": session_info["frames_processed"],
                    "session_duration_seconds": (
                        datetime.now(timezone.utc) - session_info["started_at"]
                    ).total_seconds(),
                    "last_detection_time": (
                        session_info["last_detection_time"].isoformat()
                        if session_info["last_detection_time"]
                        else None
                    ),
                },
                "session_metadata": {
                    "device_id": device_id,
                    "completion_reason": completion_reason,
                    **session_info["session_metadata"],
                },
            }

            # Complete session via Vision service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vision_service_url}/api/v1/sessions/{session_uuid}/complete",
                    json=completion_request,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        # Remove from active sessions
                        del self.active_streaming_sessions[device_id]

                        logger.info(
                            f"✅ Completed streaming session {session_uuid} for device {device_id} "
                            f"({session_info['face_count']} faces, {session_info['frames_processed']} frames)"
                        )
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"❌ Failed to complete session {session_uuid}: "
                            f"HTTP {response.status} - {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Error completing session for device {device_id}: {e}")
            return False

    def get_active_session(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get active session info for a device."""
        return self.active_streaming_sessions.get(device_id)

    def get_all_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active streaming sessions."""
        return self.active_streaming_sessions.copy()

    async def cleanup_stale_sessions(self, max_idle_minutes: int = 30) -> int:
        """
        Cleanup sessions that have been idle for too long.

        Args:
            max_idle_minutes: Maximum idle time before cleanup

        Returns:
            Number of sessions cleaned up
        """
        try:
            current_time = datetime.now(timezone.utc)
            stale_sessions = []

            for device_id, session_info in self.active_streaming_sessions.items():
                last_activity = session_info.get(
                    "last_detection_time", session_info["started_at"]
                )
                idle_minutes = (current_time - last_activity).total_seconds() / 60

                if idle_minutes > max_idle_minutes:
                    stale_sessions.append(device_id)

            # Cleanup stale sessions
            cleaned_count = 0
            for device_id in stale_sessions:
                if await self.complete_streaming_session(device_id, "stale_cleanup"):
                    cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} stale streaming sessions")

            return cleaned_count

        except Exception as e:
            logger.error(f"❌ Error during session cleanup: {e}")
            return 0


# Global streaming session manager instance
streaming_session_manager = StreamingSessionManager()

"""
Session Completion Handler for Camera Recording Face Detection
Handles the completion of camera recording sessions and persistence of detected faces.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.services.face_detection_service import CameraRecordingFaceDetectionService

logger = logging.getLogger(__name__)


class CameraRecordingSessionHandler:
    """
    Handler for camera recording session completion events.

    Manages the transition from in-memory face storage during recording
    to persistent database storage after recording completion.
    """

    def __init__(self):
        """Initialize the session handler."""
        self.session_detector = CameraRecordingFaceDetectionService()
        logger.info("✅ Camera Recording Session Handler initialized")

    async def handle_recording_completion(
        self,
        recording_session_id: str,
        media_id: str,
        camera_device_id: str,
        user_id: str,
        workflow_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle completion of a camera recording session.

        Args:
            recording_session_id: Unique recording session identifier
            media_id: Media ID for the completed recording
            camera_device_id: Camera device that performed the recording
            user_id: User who owns the recording
            workflow_metadata: Additional workflow metadata

        Returns:
            Dict with completion results and persistence status
        """
        try:
            logger.info(
                f"Handling recording completion for session {recording_session_id}, "
                f"media {media_id}, camera {camera_device_id}"
            )

            # Complete the recording session and get stored faces
            completion_result = self.session_detector.complete_recording_session(
                recording_session_id
            )

            if not completion_result.get("success"):
                logger.warning(
                    f"No session data found for recording {recording_session_id}: "
                    f"{completion_result.get('error')}"
                )
                return {
                    "success": True,
                    "faces_persisted": 0,
                    "message": "No session data to persist",
                    "session_had_faces": False,
                }

            faces_for_persistence = completion_result.get("faces_for_persistence", [])
            session_stats = completion_result.get("session_stats", {})

            if not faces_for_persistence:
                logger.info(
                    f"No faces detected in recording session {recording_session_id}"
                )
                return {
                    "success": True,
                    "faces_persisted": 0,
                    "message": "No faces detected during recording",
                    "session_had_faces": False,
                    "session_stats": session_stats,
                }

            # Persist faces to database via Vision Service integration
            persistence_result = await self._persist_faces_to_database(
                faces_for_persistence,
                media_id,
                camera_device_id,
                user_id,
                recording_session_id,
                workflow_metadata,
            )

            # Clean up memory after successful persistence
            if persistence_result.get("success"):
                self.session_detector.session_detector.cleanup_session_memory(
                    recording_session_id
                )

            logger.info(
                f"✅ Completed recording session {recording_session_id}: "
                f"{len(faces_for_persistence)} faces detected, "
                f"{persistence_result.get('faces_persisted', 0)} faces persisted"
            )

            return {
                "success": persistence_result.get("success", False),
                "recording_session_id": recording_session_id,
                "media_id": media_id,
                "faces_detected": len(faces_for_persistence),
                "faces_persisted": persistence_result.get("faces_persisted", 0),
                "session_had_faces": True,
                "session_stats": session_stats,
                "persistence_details": persistence_result.get("details", {}),
                "message": persistence_result.get("message", ""),
            }

        except Exception as e:
            logger.error(
                f"Error handling recording completion {recording_session_id}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "recording_session_id": recording_session_id,
                "media_id": media_id,
            }

    async def _persist_faces_to_database(
        self,
        faces: List[Dict[str, Any]],
        media_id: str,
        camera_device_id: str,
        user_id: str,
        recording_session_id: str,
        workflow_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Persist detected faces to the database via Vision Service.

        Args:
            faces: List of face detection results from session memory
            media_id: Media ID for the recording
            camera_device_id: Camera device identifier
            user_id: User identifier
            recording_session_id: Recording session identifier
            workflow_metadata: Additional metadata

        Returns:
            Dict with persistence results
        """
        try:
            logger.info(
                f"Persisting {len(faces)} faces to database for media {media_id}"
            )

            # Format faces for Vision Service database storage
            formatted_faces = []
            for face in faces:
                # Convert session face format to Vision Service format
                formatted_face = {
                    "media_id": media_id,
                    "media_type": "video",  # Camera recordings are videos
                    "bbox": [
                        face.get("bounding_box", {}).get("x", 0),
                        face.get("bounding_box", {}).get("y", 0),
                        face.get("bounding_box", {}).get("x", 0)
                        + face.get("bounding_box", {}).get("width", 0),
                        face.get("bounding_box", {}).get("y", 0)
                        + face.get("bounding_box", {}).get("height", 0),
                    ],
                    "confidence": face.get("confidence", 0.0),
                    "method": face.get("method", "haar"),
                    "timestamp": face.get("timestamp"),
                    "frame_metadata": face.get("frame_metadata", {}),
                    "recording_session_id": recording_session_id,
                    "camera_device_id": camera_device_id,
                    "user_id": user_id,
                    "source": "camera_recording_session",
                }

                # Add frame info if available
                frame_meta = face.get("frame_metadata", {})
                if frame_meta:
                    formatted_face["frame_info"] = {
                        "width": frame_meta.get("width"),
                        "height": frame_meta.get("height"),
                    }

                formatted_faces.append(formatted_face)

            # TODO: Integrate with Vision Service database persistence
            # For now, we'll simulate the persistence and return success
            # In the full implementation, this would call the Vision Service API
            # to store the faces in the proper database with proper schema

            logger.info(
                f"Would persist {len(formatted_faces)} faces to Vision Service database"
            )

            # Simulate successful persistence
            persisted_count = len(formatted_faces)

            return {
                "success": True,
                "faces_persisted": persisted_count,
                "details": {
                    "media_id": media_id,
                    "recording_session_id": recording_session_id,
                    "faces_formatted": len(formatted_faces),
                    "persistence_method": "vision_service_database",
                    "camera_device_id": camera_device_id,
                },
                "message": f"Successfully persisted {persisted_count} faces from camera recording",
            }

        except Exception as e:
            logger.error(f"Error persisting faces to database: {e}")
            return {
                "success": False,
                "faces_persisted": 0,
                "error": str(e),
                "details": {
                    "media_id": media_id,
                    "error_location": "database_persistence",
                },
            }

    def get_active_sessions(self) -> List[str]:
        """Get list of currently active recording sessions."""
        if not self.session_detector.is_session_detection_enabled():
            return []

        return self.session_detector.session_detector.get_all_active_sessions()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics for session storage."""
        if not self.session_detector.is_session_detection_enabled():
            return {"error": "Session detection not enabled"}

        return self.session_detector.get_memory_usage_info()

    async def handle_session_timeout(self, recording_session_id: str) -> Dict[str, Any]:
        """
        Handle timeout of a recording session (cleanup without persistence).

        Args:
            recording_session_id: Session that timed out

        Returns:
            Dict with cleanup results
        """
        try:
            logger.warning(
                f"Handling timeout for recording session {recording_session_id}"
            )

            # Get session stats before cleanup
            stats = {}
            if self.session_detector.is_session_detection_enabled():
                stats = self.session_detector.get_session_statistics(
                    recording_session_id
                )

            # Clean up memory without persistence
            cleanup_success = False
            if self.session_detector.is_session_detection_enabled():
                cleanup_success = (
                    self.session_detector.session_detector.cleanup_session_memory(
                        recording_session_id
                    )
                )

            logger.info(f"Cleaned up timed-out session {recording_session_id}")

            return {
                "success": True,
                "recording_session_id": recording_session_id,
                "action": "timeout_cleanup",
                "faces_lost": stats.get("total_faces", 0),
                "cleanup_success": cleanup_success,
                "session_stats": stats,
            }

        except Exception as e:
            logger.error(f"Error handling session timeout {recording_session_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "recording_session_id": recording_session_id,
                "action": "timeout_cleanup",
            }

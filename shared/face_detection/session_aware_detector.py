"""
Session-Aware Face Detection Module
Extends SharedFaceDetector with memory storage for real-time camera sessions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .shared_face_detector import SharedFaceDetector


class SessionAwareFaceDetector(SharedFaceDetector):
    """
    Session-aware face detector that stores detected faces in memory during recording sessions.

    Features:
    - In-memory storage of faces keyed by recording_session_id
    - Automatic face detection during live camera recording
    - Persistence of faces to database when recording session completes
    - Memory cleanup after successful persistence
    """

    def __init__(self, logger=None, models_path: str = None):
        """Initialize session-aware face detector."""
        super().__init__(logger, models_path)

        # In-memory storage for face detection results during active sessions
        self.session_faces: Dict[str, List[Dict[str, Any]]] = {}

        # Track active recording sessions
        self.active_sessions: Set[str] = set()

        # Configuration for session management
        self.session_config = {
            "max_faces_per_session": 1000,  # Prevent memory overflow
            "face_deduplication": True,  # Remove duplicate faces based on similarity
            "min_confidence_for_storage": 0.6,  # Only store high-confidence faces
            "max_session_duration_hours": 24,  # Auto-cleanup old sessions
        }

        self.logger.info("✅ SessionAwareFaceDetector initialized")

    def start_recording_session(
        self, recording_session_id: str, metadata: Optional[Dict] = None
    ) -> bool:
        """
        Start a new recording session for face detection.

        Args:
            recording_session_id: Unique identifier for the recording session
            metadata: Optional metadata about the session

        Returns:
            bool: True if session started successfully
        """
        try:
            if recording_session_id in self.active_sessions:
                self.logger.warning(
                    f"Recording session {recording_session_id} already active"
                )
                return False

            self.active_sessions.add(recording_session_id)
            self.session_faces[recording_session_id] = []

            self.logger.info(f"✅ Started recording session: {recording_session_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to start recording session {recording_session_id}: {e}"
            )
            return False

    def detect_and_store_faces(
        self,
        recording_session_id: str,
        frame: any,
        timestamp: Optional[datetime] = None,
        method: str = "haar",
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in frame and store them in session memory.

        Args:
            recording_session_id: Session ID for storing faces
            frame: Video frame (numpy array)
            timestamp: Frame timestamp
            method: Detection method to use

        Returns:
            List of detected faces with session storage
        """
        try:
            if recording_session_id not in self.active_sessions:
                self.logger.warning(f"Session {recording_session_id} not active")
                return []

            # Perform face detection using parent class
            faces = self.detect_faces_frame(frame, method=method)

            if not faces:
                return []

            # Filter faces by confidence threshold
            high_confidence_faces = [
                face
                for face in faces
                if face.get("confidence", 0)
                >= self.session_config["min_confidence_for_storage"]
            ]

            # Prepare faces for session storage
            timestamp = timestamp or datetime.now()
            session_faces = []

            for face in high_confidence_faces:
                session_face = {
                    "recording_session_id": recording_session_id,
                    "timestamp": timestamp.isoformat(),
                    "confidence": face.get("confidence", 0),
                    "bounding_box": face.get("bbox", {}),
                    "method": method,
                    "frame_metadata": {
                        "width": frame.shape[1] if hasattr(frame, "shape") else None,
                        "height": frame.shape[0] if hasattr(frame, "shape") else None,
                    },
                }

                # Add face embedding if available
                if "embedding" in face:
                    session_face["embedding"] = face["embedding"]

                session_faces.append(session_face)

            # Store faces in session memory with deduplication
            if session_faces:
                self._store_faces_in_session(recording_session_id, session_faces)

            return session_faces

        except Exception as e:
            self.logger.error(
                f"Error detecting faces for session {recording_session_id}: {e}"
            )
            return []

    def _store_faces_in_session(
        self, recording_session_id: str, faces: List[Dict[str, Any]]
    ) -> None:
        """Store faces in session memory with deduplication."""
        try:
            session_storage = self.session_faces[recording_session_id]

            for face in faces:
                # Simple deduplication based on bounding box similarity
                if self.session_config["face_deduplication"]:
                    if not self._is_duplicate_face(session_storage, face):
                        session_storage.append(face)
                else:
                    session_storage.append(face)

            # Check memory limits
            max_faces = self.session_config["max_faces_per_session"]
            if len(session_storage) > max_faces:
                # Keep only the most recent faces
                self.session_faces[recording_session_id] = session_storage[-max_faces:]
                self.logger.warning(
                    f"Session {recording_session_id} reached max faces limit, keeping {max_faces} most recent"
                )

        except Exception as e:
            self.logger.error(
                f"Error storing faces in session {recording_session_id}: {e}"
            )

    def _is_duplicate_face(self, existing_faces: List[Dict], new_face: Dict) -> bool:
        """Simple duplicate detection based on bounding box overlap."""
        try:
            new_bbox = new_face.get("bounding_box", {})
            if not new_bbox:
                return False

            new_x = new_bbox.get("x", 0)
            new_y = new_bbox.get("y", 0)
            new_w = new_bbox.get("width", 0)
            new_h = new_bbox.get("height", 0)

            for face in existing_faces[-50:]:  # Check only recent faces for performance
                bbox = face.get("bounding_box", {})
                if not bbox:
                    continue

                x = bbox.get("x", 0)
                y = bbox.get("y", 0)
                w = bbox.get("width", 0)
                h = bbox.get("height", 0)

                # Calculate overlap
                overlap_x = max(0, min(new_x + new_w, x + w) - max(new_x, x))
                overlap_y = max(0, min(new_y + new_h, y + h) - max(new_y, y))
                overlap_area = overlap_x * overlap_y

                face1_area = new_w * new_h
                face2_area = w * h

                if face1_area > 0 and face2_area > 0:
                    overlap_ratio = overlap_area / min(face1_area, face2_area)
                    if overlap_ratio > 0.7:  # 70% overlap threshold
                        return True

            return False

        except Exception:
            return False

    def get_session_faces(self, recording_session_id: str) -> List[Dict[str, Any]]:
        """Get all faces detected in a recording session."""
        return self.session_faces.get(recording_session_id, [])

    def get_session_stats(self, recording_session_id: str) -> Dict[str, Any]:
        """Get statistics for a recording session."""
        faces = self.session_faces.get(recording_session_id, [])

        if not faces:
            return {
                "total_faces": 0,
                "session_active": recording_session_id in self.active_sessions,
            }

        confidences = [face.get("confidence", 0) for face in faces]

        return {
            "total_faces": len(faces),
            "session_active": recording_session_id in self.active_sessions,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "max_confidence": max(confidences) if confidences else 0,
            "detection_methods": list(
                set(face.get("method", "unknown") for face in faces)
            ),
            "face_count_by_method": {
                method: len([f for f in faces if f.get("method") == method])
                for method in set(face.get("method", "unknown") for face in faces)
            },
        }

    def complete_recording_session(self, recording_session_id: str) -> Dict[str, Any]:
        """
        Complete a recording session and return faces for persistence.

        Args:
            recording_session_id: Session to complete

        Returns:
            Dict with session completion info and faces to persist
        """
        try:
            if recording_session_id not in self.active_sessions:
                self.logger.warning(f"Session {recording_session_id} not active")
                return {"success": False, "error": "Session not active"}

            # Get all faces from session
            faces = self.session_faces.get(recording_session_id, [])

            # Remove from active sessions
            self.active_sessions.discard(recording_session_id)

            # Prepare response
            result = {
                "success": True,
                "recording_session_id": recording_session_id,
                "faces_detected": len(faces),
                "faces_for_persistence": faces,
                "session_stats": self.get_session_stats(recording_session_id),
            }

            self.logger.info(
                f"✅ Completed recording session {recording_session_id}: {len(faces)} faces detected"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error completing recording session {recording_session_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    def cleanup_session_memory(self, recording_session_id: str) -> bool:
        """Clean up memory for a completed session."""
        try:
            if recording_session_id in self.session_faces:
                del self.session_faces[recording_session_id]

            self.active_sessions.discard(recording_session_id)

            self.logger.info(f"✅ Cleaned up memory for session {recording_session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error cleaning up session {recording_session_id}: {e}")
            return False

    def get_all_active_sessions(self) -> List[str]:
        """Get list of all active recording sessions."""
        return list(self.active_sessions)

    def get_memory_usage_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        total_faces = sum(len(faces) for faces in self.session_faces.values())

        return {
            "active_sessions": len(self.active_sessions),
            "total_sessions_in_memory": len(self.session_faces),
            "total_faces_in_memory": total_faces,
            "memory_usage_mb": self._estimate_memory_usage(),
            "sessions": {
                session_id: len(faces)
                for session_id, faces in self.session_faces.items()
            },
        }

    def _estimate_memory_usage(self) -> float:
        """Rough estimate of memory usage in MB."""
        try:
            total_faces = sum(len(faces) for faces in self.session_faces.values())
            # Rough estimate: ~1KB per face entry
            estimated_bytes = total_faces * 1024
            return estimated_bytes / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0

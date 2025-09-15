"""
PPL Meta Cameras Service - Session-Aware Face Detection Service
Enhanced face detection with integrated session tracking and real-time statistics

This module provides session-aware face detection capabilities:
- Face detection with session context tracking
- Real-time session statistics updates
- Performance monitoring and optimization
- Integration with streaming session manager
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from src.shared.shared.face_detection import SharedFaceDetector

logger = logging.getLogger(__name__)


class SessionAwareFaceDetector:
    """Face detector with integrated session tracking and real-time statistics."""

    def __init__(
        self, detection_method: str = "two_stage", confidence_threshold: float = 0.7
    ):
        """Initialize session-aware face detector."""
        self.base_detector = SharedFaceDetector()
        self.default_method = detection_method
        self.default_confidence = confidence_threshold

        # Session tracking
        self.session_stats: Dict[str, Dict[str, Any]] = {}
        self.performance_metrics: Dict[str, List[float]] = {}

        logger.info(
            "SessionAwareFaceDetector initialized with method: %s", detection_method
        )

    async def detect_faces_with_session(
        self,
        frame: np.ndarray,
        session_uuid: str,
        device_id: str,
        method: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        frame_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform face detection with session context tracking.

        Args:
            frame: Input video frame
            session_uuid: Session identifier for tracking
            device_id: Camera device identifier
            method: Detection method override
            confidence_threshold: Confidence threshold override
            frame_metadata: Additional frame metadata

        Returns:
            Detection results with session statistics
        """
        start_time = time.time()

        try:
            # Initialize session stats if needed
            if session_uuid not in self.session_stats:
                self.session_stats[session_uuid] = {
                    "device_id": device_id,
                    "total_frames": 0,
                    "total_faces": 0,
                    "detection_times": [],
                    "avg_detection_time": 0.0,
                    "faces_per_frame": 0.0,
                    "last_detection_time": None,
                    "session_start": datetime.now(timezone.utc),
                    "last_frame_metadata": None,
                }

            session_stats = self.session_stats[session_uuid]

            # Perform face detection
            detected_faces = self.base_detector.detect_faces_frame(
                frame=frame,
                method=method or self.default_method,
                confidence_threshold=confidence_threshold or self.default_confidence,
            )

            # Calculate detection time
            detection_time = time.time() - start_time

            # Update session statistics
            session_stats["total_frames"] += 1
            session_stats["total_faces"] += len(detected_faces)
            session_stats["detection_times"].append(detection_time)
            session_stats["last_detection_time"] = datetime.now(timezone.utc)
            session_stats["last_frame_metadata"] = frame_metadata

            # Keep only last 100 detection times for rolling average
            if len(session_stats["detection_times"]) > 100:
                session_stats["detection_times"] = session_stats["detection_times"][
                    -100:
                ]

            # Calculate rolling averages
            session_stats["avg_detection_time"] = sum(
                session_stats["detection_times"]
            ) / len(session_stats["detection_times"])
            session_stats["faces_per_frame"] = (
                session_stats["total_faces"] / session_stats["total_frames"]
            )

            # Calculate session duration
            session_duration = (
                datetime.now(timezone.utc) - session_stats["session_start"]
            ).total_seconds()

            # Prepare enhanced detection results
            result = {
                "session_uuid": session_uuid,
                "device_id": device_id,
                "detection_timestamp": datetime.now(timezone.utc).isoformat(),
                "faces_detected": detected_faces,
                "face_count": len(detected_faces),
                "detection_time_ms": round(detection_time * 1000, 2),
                "frame_metadata": frame_metadata or {},
                "session_statistics": {
                    "total_frames_processed": session_stats["total_frames"],
                    "total_faces_detected": session_stats["total_faces"],
                    "average_detection_time_ms": round(
                        session_stats["avg_detection_time"] * 1000, 2
                    ),
                    "average_faces_per_frame": round(
                        session_stats["faces_per_frame"], 2
                    ),
                    "processing_rate_fps": (
                        round(session_stats["total_frames"] / session_duration, 2)
                        if session_duration > 0
                        else 0.0
                    ),
                    "session_duration_seconds": round(session_duration, 2),
                },
            }

            # Log performance for monitoring
            if session_stats["total_frames"] % 50 == 0:  # Log every 50 frames
                logger.info(
                    f"📊 Session {session_uuid[:8]}... performance: "
                    f"{result['session_statistics']['processing_rate_fps']:.1f} FPS, "
                    f"{result['session_statistics']['average_detection_time_ms']:.1f}ms avg detection, "
                    f"{result['session_statistics']['total_faces_detected']} total faces"
                )

            return result

        except Exception as e:
            logger.error(
                f"❌ Session-aware face detection error for {session_uuid}: {e}"
            )
            return {
                "session_uuid": session_uuid,
                "device_id": device_id,
                "detection_timestamp": datetime.now(timezone.utc).isoformat(),
                "faces_detected": [],
                "face_count": 0,
                "detection_time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e),
                "frame_metadata": frame_metadata or {},
                "session_statistics": self.get_session_statistics(session_uuid),
            }

    def get_session_statistics(self, session_uuid: str) -> Dict[str, Any]:
        """Get current session statistics."""
        if session_uuid not in self.session_stats:
            return {"error": f"Session {session_uuid} not found"}

        session_stats = self.session_stats[session_uuid]
        session_duration = (
            datetime.now(timezone.utc) - session_stats["session_start"]
        ).total_seconds()

        return {
            "total_frames_processed": session_stats["total_frames"],
            "total_faces_detected": session_stats["total_faces"],
            "average_detection_time_ms": (
                round(session_stats["avg_detection_time"] * 1000, 2)
                if session_stats["detection_times"]
                else 0.0
            ),
            "average_faces_per_frame": round(session_stats["faces_per_frame"], 2),
            "processing_rate_fps": (
                round(session_stats["total_frames"] / session_duration, 2)
                if session_duration > 0
                else 0.0
            ),
            "session_duration_seconds": round(session_duration, 2),
            "last_detection_time": (
                session_stats["last_detection_time"].isoformat()
                if session_stats["last_detection_time"]
                else None
            ),
        }

    def get_all_session_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all active sessions."""
        return {
            session_uuid: self.get_session_statistics(session_uuid)
            for session_uuid in self.session_stats.keys()
        }

    def cleanup_session(self, session_uuid: str) -> bool:
        """Clean up session statistics."""
        if session_uuid in self.session_stats:
            session_stats = self.session_stats[session_uuid]
            logger.info(
                f"🧹 Cleaning up session {session_uuid[:8]}... "
                f"({session_stats['total_frames']} frames, {session_stats['total_faces']} faces)"
            )
            del self.session_stats[session_uuid]
            return True
        return False

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary across all sessions."""
        if not self.session_stats:
            return {"active_sessions": 0, "message": "No active sessions"}

        total_frames = sum(
            stats["total_frames"] for stats in self.session_stats.values()
        )
        total_faces = sum(stats["total_faces"] for stats in self.session_stats.values())

        all_detection_times = []
        for stats in self.session_stats.values():
            all_detection_times.extend(stats["detection_times"])

        avg_detection_time = (
            sum(all_detection_times) / len(all_detection_times)
            if all_detection_times
            else 0.0
        )

        return {
            "active_sessions": len(self.session_stats),
            "total_frames_processed": total_frames,
            "total_faces_detected": total_faces,
            "average_detection_time_ms": round(avg_detection_time * 1000, 2),
            "overall_face_detection_rate": (
                round(total_faces / total_frames, 2) if total_frames > 0 else 0.0
            ),
            "sessions": list(self.session_stats.keys()),
        }

    async def cleanup_idle_sessions(self, max_idle_minutes: int = 30) -> int:
        """Clean up sessions that have been idle for too long."""
        current_time = datetime.now(timezone.utc)
        idle_sessions = []

        for session_uuid, stats in self.session_stats.items():
            last_activity = stats.get("last_detection_time", stats["session_start"])
            idle_minutes = (current_time - last_activity).total_seconds() / 60

            if idle_minutes > max_idle_minutes:
                idle_sessions.append(session_uuid)

        cleaned_count = 0
        for session_uuid in idle_sessions:
            if self.cleanup_session(session_uuid):
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} idle face detection sessions")

        return cleaned_count


# Global session-aware face detector instance
session_aware_face_detector = SessionAwareFaceDetector(
    detection_method="two_stage", confidence_threshold=0.7
)

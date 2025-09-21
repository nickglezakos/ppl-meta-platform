"""
Face Detection Service for PPL Meta Media Service

This service provides embedded face detection capabilities to eliminate
cross-service API calls. It uses a shared face detection module that can
be embedded in any service.
"""

import base64
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Import shared face detector
try:
    from shared.face_detection import SessionAwareFaceDetector, SharedFaceDetector
except ImportError:
    SharedFaceDetector = None
    SessionAwareFaceDetector = None

logger = logging.getLogger(__name__)


class MediaFaceDetectionService:
    """
    Embedded face detection service for Media microservice.

    This service eliminates the need for cross-service API calls to the Vision
    service by providing local face detection capabilities for real-time
    video streaming with yellow face detection rectangles.
    """

    def __init__(self):
        """Initialize the face detection service."""
        self.detector = None
        try:
            if SharedFaceDetector:
                self.detector = SharedFaceDetector()
                logger.info("✅ Media Face Detection Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize face detection: {e}")
            self.detector = None

    def is_face_detection_enabled(self) -> bool:
        """Check if face detection is available and ready."""
        return self.detector is not None and self.detector.is_ready()

    def get_face_detection_info(self) -> Dict[str, Any]:
        """Get information about face detection capabilities."""
        if not self.detector:
            return {
                "enabled": False,
                "available_methods": [],
                "ready": False,
                "error": "Face detection not initialized",
            }

        return {
            "enabled": True,
            "available_methods": self.detector.available_methods,
            "ready": self.detector.is_ready(),
        }

    def process_video_frame_with_faces(
        self,
        frame_data: Union[np.ndarray, bytes, str],
        draw_overlay: bool = True,
        confidence_threshold: float = 0.5,
        method: str = "auto",
    ) -> Tuple[Union[np.ndarray, bytes], List[Dict[str, Any]]]:
        """
        Process a video frame with real-time face detection.

        Args:
            frame_data: Frame data (numpy array, bytes, or base64 string)
            draw_overlay: Whether to draw yellow rectangles on frame
            confidence_threshold: Minimum confidence for face detection
            method: Detection method ("auto", "two_stage", "haar", "dlib", "dnn")

        Returns:
            Tuple of (processed_frame, face_detections)
        """
        if not self.is_face_detection_enabled():
            return frame_data, []

        try:
            # Convert input to numpy array
            frame = self._convert_to_frame(frame_data)
            if frame is None:
                return frame_data, []

            # Auto-select best available method
            detection_method = self._select_best_method(method)

            # Process frame with face detection
            processed_frame, faces = self.detector.process_video_frame_with_overlay(
                frame=frame,
                draw_overlay=draw_overlay,
                method=detection_method,
                confidence_threshold=confidence_threshold,
            )

            return processed_frame, faces

        except Exception as e:
            logger.warning(f"Face detection processing error: {e}")
            return frame_data, []

    def _select_best_method(self, method: str) -> str:
        """Select the best available face detection method."""
        if method != "auto":
            return method

        # Prefer two-stage for best accuracy, fallback to others
        available = self.detector.available_methods
        if "two_stage" in available:
            return "two_stage"
        elif "dlib" in available:
            return "dlib"
        elif "haar" in available:
            return "haar"
        elif "dnn" in available:
            return "dnn"
        else:
            return "haar"  # Final fallback

    def detect_faces_only(
        self,
        frame_data: Union[np.ndarray, bytes, str],
        confidence_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in a frame without modifying the frame.

        Args:
            frame_data: Frame data (numpy array, bytes, or base64 string)
            confidence_threshold: Minimum confidence for face detection

        Returns:
            List of face detections with bbox and confidence
        """
        if not self.is_face_detection_enabled():
            return []

        try:
            # Convert input to numpy array
            frame = self._convert_to_frame(frame_data)
            if frame is None:
                return []

            # Detect faces using available method
            faces = self.detector.detect_faces_frame(
                frame=frame, method="haar", confidence_threshold=confidence_threshold
            )

            return faces

        except Exception as e:
            logger.warning(f"Face detection error: {e}")
            return []

    def detect_faces_fast(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Fast face detection optimized for real-time processing.

        Used in Phase 1 of Hybrid Face Detection Architecture (Issue 052).
        Optimized for speed over accuracy to provide immediate feedback
        during video playbook.

        Args:
            frame: OpenCV frame as numpy array
            confidence_threshold: Minimum confidence for face detection

        Returns:
            List of face detections with bbox, confidence, and method
        """
        if not self.is_face_detection_enabled():
            return []

        try:
            # Check if detector is available
            if not self.detector:
                return []

            # Use the same two_stage method as Vision service bulk processing
            detection_result = self.detector.detect_faces_two_stage(
                frame, confidence_threshold=confidence_threshold
            )

            # Extract faces from the structured result
            if detection_result.get("success", False):
                return detection_result.get("detections", [])
            else:
                return []

        except Exception as e:
            logger.warning(f"Fast face detection error: {e}")
            return []

    def _convert_to_frame(
        self, frame_data: Union[np.ndarray, bytes, str]
    ) -> Optional[np.ndarray]:
        """
        Convert various input formats to OpenCV frame (numpy array).

        Args:
            frame_data: Frame data in various formats

        Returns:
            OpenCV frame as numpy array or None if conversion fails
        """
        try:
            if isinstance(frame_data, np.ndarray):
                # Already a numpy array
                return frame_data

            elif isinstance(frame_data, (bytes, bytearray)):
                # Try to decode as compressed image (JPEG/PNG)
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return frame  # Could be None if decoding fails

            elif isinstance(frame_data, str):
                # Assume base64 encoded image
                try:
                    # Decode base64
                    image_bytes = base64.b64decode(frame_data)
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return frame
                except Exception:
                    return None

            else:
                logger.warning(f"Unsupported frame type: {type(frame_data)}")
                return None

        except Exception as e:
            logger.warning(f"Frame conversion error: {e}")
            return None

    def convert_frame_to_bytes(
        self, frame: np.ndarray, image_format: str = ".jpg"
    ) -> Optional[bytes]:
        """
        Convert OpenCV frame to bytes.

        Args:
            frame: OpenCV frame as numpy array
            image_format: Image format (.jpg, .png, etc.)

        Returns:
            Frame as bytes or None if encoding fails
        """
        try:
            success, encoded = cv2.imencode(image_format, frame)
            if success:
                return encoded.tobytes()
            else:
                return None
        except Exception as e:
            logger.warning(f"Frame encoding error: {e}")
            return None

    def get_service_status(self) -> Dict[str, Any]:
        """Get detailed service status and capabilities."""
        status = {
            "service": "MediaFaceDetectionService",
            "face_detection": self.get_face_detection_info(),
            "performance": {
                "real_time": True,
                "methods": ["haar_cascade"],
                "optimized_for": "video_streaming",
            },
            "benefits": [
                "No cross-service API calls required",
                "Real-time face detection during streaming",
                "Immediate yellow rectangle overlay",
                "High performance with minimal latency",
            ],
        }

        return status

    def detect_faces_vision_compatible(
        self, frame: np.ndarray, confidence_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Vision service compatible two-stage face detection.
        This is an exact copy of the Vision service's
        detect_faces_two_stage implementation to ensure identical results
        for progressive pre-loading.

        Stage 1: Haar cascade detection
        Stage 2: Dlib validation to filter false positives
        """
        try:
            # Check if detector is available
            if not self.detector:
                return []

            # Get available methods from shared detector
            available_methods = getattr(self.detector, "available_methods", [])

            # Ensure we have the required methods
            if "haar" not in available_methods or "dlib" not in available_methods:
                logger.warning(
                    "Required methods (haar, dlib) not available for "
                    "vision-compatible detection"
                )
                return []

            import time

            start_time = time.time()

            # Convert to grayscale if needed
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Stage 1: Haar cascade for initial detection
            # Using same parameters as Vision service
            haar_cascade = getattr(self.detector, "haar_cascade", None)
            if not haar_cascade:
                logger.warning("Haar cascade not available in shared detector")
                return []

            faces = haar_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            # Initial face rectangles from Haar cascade
            face_rects = []
            for face in faces:
                x = int(face[0])
                y = int(face[1])
                w = int(face[2])
                h = int(face[3])
                face_rects.append([x, y, w, h])

            # Stage 2: Dlib validation (filter false positives)
            filtered_face_rects = []

            dlib_detector = getattr(self.detector, "dlib_detector", None)
            if not dlib_detector:
                logger.warning("Dlib detector not available in shared detector")
                return []

            for face_rect in face_rects:
                x, y, w, h = face_rect

                # Crop the face region for Dlib validation
                face_region = gray[y : y + h, x : x + w]

                # Skip if face region is too small
                if face_region.size == 0:
                    continue

                # Perform Dlib face detection on the cropped face region
                try:
                    dlib_faces = dlib_detector(face_region, 1)
                    # If Dlib detects faces in this region, it's a valid face
                    if len(dlib_faces) > 0:
                        filtered_face_rects.append(face_rect)
                except Exception:
                    # Skip this face if dlib detection fails
                    continue

            # Convert to the expected output format
            # (matching Vision service exactly)
            detections = []
            for face_rect in filtered_face_rects:
                x, y, w, h = face_rect
                detections.append(
                    {
                        "bbox": [x, y, x + w, y + h],
                        "confidence": 0.5,  # Fixed confidence
                        "method": "two_stage_haar_dlib",
                    }
                )

            processing_time = time.time() - start_time

            logger.info(
                "Vision-compatible detection: %d initial Haar detections → "
                "%d Dlib-validated faces in %.3fs",
                len(faces),
                len(filtered_face_rects),
                processing_time,
            )

            return detections

        except Exception as e:
            logger.warning("Vision-compatible face detection error: %s", str(e))
            return []


class CameraRecordingFaceDetectionService:
    """
    Session-aware face detection service for camera recordings.

    Provides memory storage during recording sessions and persistence
    after recording completion for automatic face detection workflows.
    """

    def __init__(self):
        """Initialize session-aware face detection service."""
        self.session_detector = None
        try:
            if SessionAwareFaceDetector:
                self.session_detector = SessionAwareFaceDetector()
                logger.info("✅ Camera Recording Face Detection Service initialized")
        except Exception as e:
            logger.error("❌ Failed to initialize session detector: %s", str(e))
            self.session_detector = None

    def is_session_detection_enabled(self) -> bool:
        """Check if session-aware face detection is available."""
        return (
            self.session_detector is not None
            and hasattr(self.session_detector, "models_loaded")
            and self.session_detector.models_loaded
        )

    def start_recording_session(
        self, recording_session_id: str, metadata: Optional[Dict] = None
    ) -> bool:
        """Start a new recording session for face detection."""
        if not self.is_session_detection_enabled():
            logger.warning("Session detection not enabled")
            return False

        return self.session_detector.start_recording_session(
            recording_session_id, metadata
        )

    def process_recording_frame(
        self,
        recording_session_id: str,
        frame: np.ndarray,
        timestamp: Optional[str] = None,
        detection_method: str = "haar",
    ) -> List[Dict[str, Any]]:
        """Process a frame during recording and store faces in session memory."""
        if not self.is_session_detection_enabled():
            return []

        # Convert timestamp string to datetime if provided
        timestamp_dt = None
        if timestamp:
            try:
                from datetime import datetime

                timestamp_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                timestamp_dt = None

        return self.session_detector.detect_and_store_faces(
            recording_session_id, frame, timestamp_dt, detection_method
        )

    def get_session_statistics(self, recording_session_id: str) -> Dict[str, Any]:
        """Get face detection statistics for a recording session."""
        if not self.is_session_detection_enabled():
            return {"error": "Session detection not enabled"}

        return self.session_detector.get_session_stats(recording_session_id)

    def complete_recording_session(self, recording_session_id: str) -> Dict[str, Any]:
        """Complete recording session and return faces for database persistence."""
        if not self.is_session_detection_enabled():
            return {"success": False, "error": "Session detection not enabled"}

        result = self.session_detector.complete_recording_session(recording_session_id)

        # Clean up memory after completion
        if result.get("success"):
            self.session_detector.cleanup_session_memory(recording_session_id)

        return result

    def get_memory_usage_info(self) -> Dict[str, Any]:
        """Get memory usage information for all active sessions."""
        if not self.is_session_detection_enabled():
            return {"error": "Session detection not enabled"}

        return self.session_detector.get_memory_usage_stats()


# Alias for backward compatibility
FaceDetectionService = MediaFaceDetectionService

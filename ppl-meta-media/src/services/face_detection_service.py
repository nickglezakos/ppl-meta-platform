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
    from shared.face_detection import SharedFaceDetector
except ImportError:
    SharedFaceDetector = None

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

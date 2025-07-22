"""
Face Detection Service for PPL Meta Media Service

This service provides embedded face detection capabilities to eliminate
cross-service API calls. It uses a shared face detection module that can
be embedded in any service.
"""

import base64
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

# Import shared face detector
from shared.face_detection import SharedFaceDetector

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
        try:
            self.detector = SharedFaceDetector()
            logger.info("✅ Media Face Detection Service initialized successfully")
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
        confidence_threshold: float = 0.3,
    ) -> Tuple[Union[np.ndarray, bytes], List[Dict[str, Any]]]:
        """
        Process a video frame with real-time face detection.

        Args:
            frame_data: Frame data (numpy array, bytes, or base64 string)
            draw_overlay: Whether to draw yellow rectangles on frame
            confidence_threshold: Minimum confidence for face detection

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

            # Process frame with face detection
            processed_frame, faces = self.detector.process_video_frame_with_overlay(
                frame=frame,
                draw_overlay=draw_overlay,
                confidence_threshold=confidence_threshold,
            )

            return processed_frame, faces

        except Exception as e:
            logger.warning(f"Face detection processing error: {e}")
            return frame_data, []

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

            # Detect faces using haar method (fastest for real-time)
            faces = self.detector.detect_faces_haar_realtime(
                frame=frame, confidence_threshold=confidence_threshold
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


import logging
import os
import sys
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from fastapi import HTTPException

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from shared.face_detection import SharedFaceDetector
except ImportError:
    # Fallback if shared module not available
    SharedFaceDetector = None

logger = logging.getLogger(__name__)


class MediaFaceDetectionService:
    """
    Real-time face detection service embedded in Media service.
    Eliminates need for cross-service API calls during video streaming.
    """

    def __init__(self):
        """Initialize the face detection service."""
        self.detector = None
        self.is_enabled = False
        self.models_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "face_detection"
        )

        # Ensure models directory exists
        os.makedirs(self.models_path, exist_ok=True)

        # Initialize face detector
        self._initialize_detector()

    def _initialize_detector(self):
        """Initialize the shared face detector."""
        if SharedFaceDetector is None:
            logger.warning("SharedFaceDetector not available - face detection disabled")
            return

        try:
            self.detector = SharedFaceDetector(
                logger=logger, models_path=self.models_path
            )

            if self.detector.is_ready():
                self.is_enabled = True
                available_methods = self.detector.get_available_methods()
                logger.info(
                    f"✅ Media face detection enabled with methods: {available_methods}"
                )
            else:
                logger.warning("⚠️ Face detection models not available - disabled")

        except Exception as e:
            logger.error(f"❌ Failed to initialize face detection: {e}")
            self.detector = None

    def is_face_detection_enabled(self) -> bool:
        """Check if face detection is available and enabled."""
        return self.is_enabled and self.detector is not None

    def process_video_frame(
        self,
        frame_data: bytes,
        draw_overlay: bool = True,
        confidence_threshold: float = 0.3,
    ) -> Tuple[bytes, List[Dict[str, Any]]]:
        """
        Process a video frame with real-time face detection.

        Args:
            frame_data: Raw frame data (bytes)
            draw_overlay: Whether to draw yellow rectangles on frame
            confidence_threshold: Minimum confidence for face detection

        Returns:
            Tuple of (processed_frame_bytes, face_detections)

        Raises:
            HTTPException: If face detection is not available
        """
        if not self.is_face_detection_enabled():
            # Return original frame without face detection
            return frame_data, []

        try:
            # Convert bytes to OpenCV frame
            frame = self._bytes_to_frame(frame_data)

            # Process frame with face detection
            processed_frame, faces = self.detector.process_video_frame_with_overlay(
                frame=frame,
                draw_overlay=draw_overlay,
                method="haar",  # Use haar for real-time performance
                confidence_threshold=confidence_threshold,
            )

            # Convert back to bytes
            processed_bytes = self._frame_to_bytes(processed_frame)

            return processed_bytes, faces

        except Exception as e:
            logger.error(f"Face detection processing error: {e}")
            # Return original frame on error
            return frame_data, []

    def detect_faces_only(
        self, frame_data: bytes, confidence_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in a frame without modifying the frame.
        Useful for generating face detection metadata without overlay.

        Args:
            frame_data: Raw frame data (bytes)
            confidence_threshold: Minimum confidence for face detection

        Returns:
            List of face detections
        """
        if not self.is_face_detection_enabled():
            return []

        try:
            # Convert bytes to OpenCV frame
            frame = self._bytes_to_frame(frame_data)

            # Detect faces only
            faces = self.detector.detect_faces_frame(
                frame=frame, method="haar", confidence_threshold=confidence_threshold
            )

            return faces

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    def _bytes_to_frame(self, frame_data: bytes) -> np.ndarray:
        """Convert bytes data to OpenCV frame."""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)

            # Try to decode as compressed image first (JPEG/PNG)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                return frame

            # If decoding fails, assume it's raw image data
            # This is a fallback for uncompressed frame data
            self.logger.debug("Frame decoding failed, treating as raw data")
            return None

        except Exception as e:
            self.logger.warning(f"Frame conversion error: {e}")
            return None

    def _frame_to_bytes(self, frame: np.ndarray, format: str = ".jpg") -> bytes:
        """Convert OpenCV frame to bytes."""
        # Encode frame to bytes
        success, encoded = cv2.imencode(format, frame)

        if not success:
            raise ValueError("Failed to encode frame to bytes")

        return encoded.tobytes()

    def get_detection_info(self) -> Dict[str, Any]:
        """Get information about face detection capabilities."""
        if not self.is_face_detection_enabled():
            return {
                "enabled": False,
                "reason": "Face detection not available",
                "available_methods": [],
            }

        return {
            "enabled": True,
            "available_methods": self.detector.get_available_methods(),
            "models_path": self.models_path,
            "ready": self.detector.is_ready(),
        }

    def update_detection_config(self, **kwargs):
        """Update face detection configuration."""
        if self.detector:
            self.detector.update_config(**kwargs)


# Global instance
media_face_detection = MediaFaceDetectionService()

"""
Face Detection Service for PPL Meta Mini Service
Exact copy of MediaFaceDetectionService implementation for consistent results.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List

import cv2
import numpy as np

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Import shared face detector
try:
    from shared.face_detection.shared_face_detector import SharedFaceDetector
except ImportError:
    SharedFaceDetector = None

logger = logging.getLogger(__name__)


class MiniFaceDetectionService:
    """
    Face detection service for Mini service.
    Uses the exact same implementation as MediaFaceDetectionService
    for consistent face detection results.
    """

    def __init__(self):
        """Initialize the face detection service."""
        self.detector = None
        try:
            if SharedFaceDetector:
                self.detector = SharedFaceDetector()
                logger.info("✅ Mini Face Detection Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize face detection: {e}")
            self.detector = None

    def is_ready(self) -> bool:
        """Check if the face detection service is ready."""
        return self.detector is not None and self.detector.is_ready()

    def is_face_detection_enabled(self) -> bool:
        """Check if face detection is available and ready."""
        return self.is_ready()

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

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video information."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": "Cannot open video file"}

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            cap.release()

            return {
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": frame_count / fps if fps > 0 else 0,
            }
        except Exception as e:
            return {"error": str(e)}

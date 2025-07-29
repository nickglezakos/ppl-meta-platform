"""
Face Detection Service for PPL Meta Mini Service
Completely autonomous implementation with hardcoded parameters matching media service.
"""

import logging
import os
import time
from typing import Any, Dict, List

import cv2
import numpy as np

# Try to import dlib for second stage validation
try:
    import dlib

    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class MiniFaceDetectionService:
    """
    Completely autonomous face detection service for Mini service.
    Uses hardcoded parameters matching the media service for consistent results.
    No dependency on shared modules.
    """

    def __init__(self):
        """Initialize the autonomous face detection service."""
        self.haar_cascade = None
        self.dlib_detector = None
        self._initialize_detectors()

    def _initialize_detectors(self):
        """Initialize Haar cascade and Dlib detectors autonomously."""
        try:
            # Load Haar cascade for face detection
            haar_cascade_path = (
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            if os.path.exists(haar_cascade_path):
                self.haar_cascade = cv2.CascadeClassifier(haar_cascade_path)
                logger.info("✅ Autonomous Haar cascade loaded successfully")
            else:
                logger.error(f"❌ Haar cascade not found at {haar_cascade_path}")
                return

            # Initialize Dlib face detector if available
            if DLIB_AVAILABLE:
                try:
                    self.dlib_detector = dlib.get_frontal_face_detector()
                    logger.info("✅ Autonomous Dlib face detector loaded successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Dlib detector initialization failed: {e}")
                    self.dlib_detector = None
            else:
                logger.warning("⚠️ Dlib not available, using Haar only")
                self.dlib_detector = None

            logger.info("✅ Autonomous Mini Face Detection Service initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize autonomous face detection: {e}")
            self.haar_cascade = None
            self.dlib_detector = None

    def is_ready(self) -> bool:
        """Check if the face detection service is ready."""
        return self.haar_cascade is not None

    def is_face_detection_enabled(self) -> bool:
        """Check if face detection is available and ready."""
        return self.is_ready()

    def get_face_detection_info(self) -> Dict[str, Any]:
        """Get information about the face detection service."""
        if not self.is_ready():
            return {
                "enabled": False,
                "error": "Face detection not initialized",
            }

        available_methods = ["haar"]
        if self.dlib_detector is not None:
            available_methods.extend(["dlib", "two_stage"])

        return {
            "enabled": True,
            "available_methods": available_methods,
            "ready": True,
            "autonomous": True,
        }

    def detect_faces_vision_compatible(
        self, frame: np.ndarray, confidence_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Autonomous two-stage face detection matching media service exactly.

        Stage 1: Haar cascade detection with hardcoded parameters
        Stage 2: Dlib validation to filter false positives (if available)

        Parameters match shared detector: scaleFactor=1.1, minNeighbors=4
        """
        try:
            if not self.is_ready():
                logger.warning("Face detection not ready")
                return []

            start_time = time.time()

            # Convert to grayscale if needed
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Stage 1: Haar cascade detection - EXACT MEDIA SERVICE parameters
            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,  # Exact Media Service match
                minNeighbors=5,  # Exact Media Service match (was 4)
                minSize=(30, 30),  # Exact Media Service match
            )

            logger.debug(f"Haar cascade found {len(faces)} initial faces")

            # Convert Haar results to list format
            face_rects = []
            for x, y, w, h in faces:
                face_rects.append([int(x), int(y), int(w), int(h)])

            # Stage 2: Dlib validation (if available) - Media Service approach
            if self.dlib_detector is not None:
                validated_faces = []
                for x, y, w, h in face_rects:
                    # Extract face region for Dlib validation
                    face_region = gray[y : y + h, x : x + w]
                    dlib_faces = self.dlib_detector(face_region, 1)

                    if len(dlib_faces) > 0:
                        # Face validated by Dlib
                        validated_faces.append([x, y, w, h])

                face_rects = validated_faces
                method = "autonomous_two_stage"
                logger.debug(f"Two-stage detection: {len(face_rects)} validated faces")
            else:
                method = "autonomous_haar_only"
                logger.debug(f"Haar-only detection: {len(face_rects)} faces")

            # Format results to match media service response format
            detection_results = []
            for i, (x, y, w, h) in enumerate(face_rects):
                detection_results.append(
                    {
                        "face_id": i + 1,
                        "confidence": confidence_threshold,  # Use threshold
                        "bbox": [x, y, x + w, y + h],  # [x1, y1, x2, y2]
                        "method": method,
                    }
                )

            detection_time = time.time() - start_time

            logger.info(
                f"Autonomous detection: {len(detection_results)} faces "
                f"in {detection_time:.3f}s"
            )

            return detection_results

        except Exception as e:
            logger.error(f"Autonomous face detection error: {e}")
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

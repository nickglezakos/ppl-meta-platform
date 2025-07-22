"""
PPL Meta Shared Face Detection Module
Provides face detection capabilities that can be used across multiple services
without requiring cross-service API calls for real-time video processing.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Try to import dlib for two-stage detection
try:
    import dlib

    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False


class SharedFaceDetector:
    """
    Shared face detection module that can be embedded in any service.
    Optimized for real-time video streaming with minimal overhead.
    """

    def __init__(self, logger=None, models_path: str = None):
        """Initialize the face detector with optional custom models path."""
        self.logger = logger or self._setup_default_logger()
        self.models_loaded = False
        self.available_methods = []

        # Default models path - can be overridden
        self.models_path = models_path or os.path.join(
            os.path.dirname(__file__), "..", "models"
        )

        # Configuration for real-time processing
        self.config = {
            "confidence_thresholds": {
                "haar": 0.3,  # Lower threshold for real-time detection
                "dlib": 0.3,
                "two_stage": 0.5,  # Higher threshold for validated faces
            },
            "scale_factor": 1.1,  # For Haar cascade
            "min_neighbors": 4,  # For Haar cascade (lowered for real-time)
            "min_size": (30, 30),  # Minimum face size
            "max_size": (300, 300),  # Maximum face size for performance
        }

        # Initialize detection methods
        self._initialize_detection_methods()

    def _setup_default_logger(self):
        """Setup a default logger."""
        logger = logging.getLogger("SharedFaceDetector")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _initialize_detection_methods(self):
        """Initialize available face detection methods."""
        self.logger.info("🔧 Initializing shared face detection methods...")

        # 1. Haar Cascade Detection (most reliable for real-time)
        haar_path = os.path.join(
            self.models_path, "haarcascade_frontalface_default.xml"
        )
        if os.path.exists(haar_path):
            try:
                self.haar_cascade = cv2.CascadeClassifier(haar_path)
                if not self.haar_cascade.empty():
                    self.available_methods.append("haar")
                    self.logger.info("✅ Haar cascade loaded successfully")
                else:
                    self.logger.warning("❌ Haar cascade file is empty")
            except Exception as e:
                self.logger.error(f"❌ Failed to load Haar cascade: {e}")
        else:
            # Use OpenCV's built-in Haar cascade as fallback
            try:
                self.haar_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
                if not self.haar_cascade.empty():
                    self.available_methods.append("haar")
                    self.logger.info("✅ Built-in Haar cascade loaded successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to load built-in Haar cascade: {e}")

        # 2. Dlib Detection (for two-stage validation)
        if DLIB_AVAILABLE:
            try:
                self.dlib_detector = dlib.get_frontal_face_detector()
                self.available_methods.append("dlib")
                self.logger.info("✅ Dlib face detector loaded successfully")
            except Exception as e:
                self.logger.warning(f"⚠️ Dlib face detector failed to load: {e}")
        else:
            self.logger.warning("⚠️ Dlib not available - install with: pip install dlib")

        # 3. Two-Stage Detection (Haar + Dlib validation - highest accuracy)
        if "haar" in self.available_methods and "dlib" in self.available_methods:
            self.available_methods.append("two_stage")
            self.logger.info("✅ Two-stage detection enabled (Haar + Dlib validation)")

        # 4. DNN-based detection (optional, better accuracy)
        try:
            dnn_config = os.path.join(self.models_path, "opencv_face_detector.pbtxt")
            dnn_weights = os.path.join(
                self.models_path, "opencv_face_detector_uint8.pb"
            )

            if os.path.exists(dnn_config) and os.path.exists(dnn_weights):
                self.dnn_net = cv2.dnn.readNetFromTensorflow(dnn_weights, dnn_config)
                self.available_methods.append("dnn")
                self.logger.info("✅ DNN face detector loaded successfully")
        except Exception as e:
            self.logger.warning(f"⚠️ DNN face detector not available: {e}")

        if not self.available_methods:
            self.logger.error("❌ No face detection methods available!")
        else:
            self.models_loaded = True
            self.logger.info(
                f"✅ Face detection initialized with methods: {self.available_methods}"
            )

    def detect_faces_frame(
        self,
        frame: np.ndarray,
        method: str = "haar",
        confidence_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in a single video frame.
        Optimized for real-time video streaming.

        Args:
            frame: Input video frame (numpy array)
            method: Detection method ("haar" or "dnn")
            confidence_threshold: Minimum confidence for detection

        Returns:
            List of face detections with bounding boxes and confidence scores
        """
        if not self.models_loaded:
            return []

        if confidence_threshold is None:
            confidence_threshold = self.config["confidence_thresholds"].get(method, 0.3)

        faces = []

        try:
            if method == "haar" and "haar" in self.available_methods:
                faces = self._detect_faces_haar(frame, confidence_threshold)
            elif method == "dlib" and "dlib" in self.available_methods:
                faces = self._detect_faces_dlib(frame, confidence_threshold)
            elif method == "two_stage" and "two_stage" in self.available_methods:
                faces = self._detect_faces_two_stage(frame, confidence_threshold)
            elif method == "dnn" and "dnn" in self.available_methods:
                faces = self._detect_faces_dnn(frame, confidence_threshold)
            else:
                # Fallback to haar if method not available
                if "haar" in self.available_methods:
                    faces = self._detect_faces_haar(frame, confidence_threshold)

        except Exception as e:
            self.logger.error(f"Face detection error: {e}")
            return []

        return faces

    def _detect_faces_haar(
        self, frame: np.ndarray, confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect faces using Haar cascade."""
        # Convert to grayscale for better performance
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        face_rects = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=self.config["scale_factor"],
            minNeighbors=self.config["min_neighbors"],
            minSize=self.config["min_size"],
            maxSize=self.config["max_size"],
        )

        faces = []
        for x, y, w, h in face_rects:
            # Haar cascade doesn't provide confidence, so we use a fixed high value
            # for faces that pass the minNeighbors threshold
            confidence = 0.8  # High confidence for detected faces

            if confidence >= confidence_threshold:
                faces.append(
                    {
                        "bbox": [int(x), int(y), int(x + w), int(y + h)],
                        "confidence": float(confidence),
                        "method": "haar_realtime",
                    }
                )

        return faces

    def _detect_faces_dnn(
        self, frame: np.ndarray, confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect faces using DNN."""
        h, w = frame.shape[:2]

        # Create blob from image
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123])
        self.dnn_net.setInput(blob)
        detections = self.dnn_net.forward()

        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            if confidence >= confidence_threshold:
                # Get bounding box coordinates
                x1 = int(detections[0, 0, i, 3] * w)
                y1 = int(detections[0, 0, i, 4] * h)
                x2 = int(detections[0, 0, i, 5] * w)
                y2 = int(detections[0, 0, i, 6] * h)

                faces.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(confidence),
                        "method": "dnn_realtime",
                    }
                )

        return faces

    def _detect_faces_dlib(
        self, frame: np.ndarray, confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect faces using Dlib."""
        # Convert to grayscale for dlib
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces with dlib
        dlib_faces = self.dlib_detector(gray, 1)

        faces = []
        for face in dlib_faces:
            # Extract coordinates
            x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()

            # Dlib doesn't provide confidence scores, use fixed high value
            confidence = 0.8  # High confidence for dlib detections

            if confidence >= confidence_threshold:
                faces.append(
                    {
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": float(confidence),
                        "method": "dlib_realtime",
                    }
                )

        return faces

    def _detect_faces_two_stage(
        self, frame: np.ndarray, confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Two-stage face detection method - Haar + Dlib validation.
        Stage 1: Haar cascade for initial detection
        Stage 2: Dlib validation to filter false positives
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Stage 1: Haar cascade for initial detection
        face_rects = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=self.config["scale_factor"],
            minNeighbors=self.config["min_neighbors"],
            minSize=self.config["min_size"],
            maxSize=self.config["max_size"],
        )

        # Stage 2: Dlib validation
        validated_faces = []
        for x, y, w, h in face_rects:
            # Crop face region for dlib validation
            face_region = gray[y : y + h, x : x + w]

            # Skip if face region is too small
            if face_region.size == 0:
                continue

            # Dlib validation on cropped region
            dlib_faces = self.dlib_detector(face_region, 1)

            # If dlib confirms face, it's validated
            if len(dlib_faces) > 0:
                confidence = self.config["confidence_thresholds"]["two_stage"]

                if confidence >= confidence_threshold:
                    validated_faces.append(
                        {
                            "bbox": [int(x), int(y), int(x + w), int(y + h)],
                            "confidence": float(confidence),
                            "method": "two_stage_haar_dlib",
                        }
                    )

        return validated_faces

    def process_video_frame_with_overlay(
        self,
        frame: np.ndarray,
        draw_overlay: bool = True,
        method: str = "haar",
        confidence_threshold: float = None,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Process a video frame and optionally draw face detection overlay.
        Perfect for real-time video streaming.

        Args:
            frame: Input video frame
            draw_overlay: Whether to draw yellow rectangles on the frame
            method: Detection method to use
            confidence_threshold: Minimum confidence for detection

        Returns:
            Tuple of (processed_frame, face_detections)
        """
        # Detect faces
        faces = self.detect_faces_frame(frame, method, confidence_threshold)

        # Draw overlay if requested
        if draw_overlay and faces:
            processed_frame = frame.copy()
            for face in faces:
                x1, y1, x2, y2 = face["bbox"]
                confidence = face["confidence"]

                # Draw yellow rectangle
                cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

                # Draw confidence text
                label = f"{confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                cv2.rectangle(
                    processed_frame,
                    (x1, y1 - label_size[1] - 10),
                    (x1 + label_size[0], y1),
                    (0, 255, 255),
                    -1,
                )
                cv2.putText(
                    processed_frame,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    2,
                )
        else:
            processed_frame = frame

        return processed_frame, faces

    def get_available_methods(self) -> List[str]:
        """Get list of available detection methods."""
        return self.available_methods.copy()

    def is_ready(self) -> bool:
        """Check if face detection is ready to use."""
        return self.models_loaded and len(self.available_methods) > 0

    def update_config(self, **kwargs):
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                self.logger.info(f"Updated config {key} = {value}")

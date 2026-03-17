# Extracted Face Detector Module for PPL Meta Vision Service
# Generated from VIS-001.2 - Code Extraction Phase
# Source: /Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/face_detector.py

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


class ExtractedFaceDetector:
    """
    Extracted face detection functionality from the monolithic app.
    This class represents the core face detection logic that will be
    migrated to the PPL Meta Vision Service microservice.
    """

    def __init__(self, logger=None):
        self.logger = logger or self._setup_default_logger()
        self.models_loaded = False
        self.available_methods = []

        # Configuration settings for face detection
        self.config = {
            "confidence_thresholds": {
                "haar": 0.5,  # Default confidence for Haar cascade detections
                "dlib": 0.5,  # Default confidence for Dlib detections
                "two_stage": 0.5,  # Default confidence for two-stage faces
            }
        }

        # Model paths based on Vision Service structure
        base_path = os.path.join(os.path.dirname(__file__), "..", "models")
        self.model_paths = {
            "haar_cascade": os.path.join(
                base_path, "haarcascade_frontalface_default.xml"
            ),
            "ssd_config": os.path.join(base_path, "ssd-face.cfg"),
            "ssd_weights": os.path.join(base_path, "ssd-face.weights"),
            "dlib_predictor": os.path.join(
                base_path, "shape_predictor_68_face_landmarks.dat"
            ),
        }

        # Initialize detection methods
        self._initialize_detection_methods()

    def _setup_default_logger(self):
        """Setup a default logger for the extracted face detector."""
        logger = logging.getLogger("ExtractedFaceDetector")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def update_confidence_threshold(self, method, confidence):
        """Update confidence threshold for a specific detection method."""
        if method in self.config["confidence_thresholds"]:
            self.config["confidence_thresholds"][method] = confidence
            self.logger.info(f"Updated {method} confidence threshold to {confidence}")
        else:
            self.logger.warning(f"Unknown method: {method}")

    def get_confidence_threshold(self, method):
        """Get confidence threshold for a specific detection method."""
        return self.config["confidence_thresholds"].get(method, 0.5)

    def _initialize_detection_methods(self):
        """Initialize available face detection methods based on real monolithic app."""
        self.logger.info("🔧 Initializing face detection methods...")

        # Check for ML libraries availability
        ml_libraries = {"dlib": False}

        for lib in ml_libraries:
            try:
                if lib == "dlib":
                    import dlib

                    ml_libraries[lib] = True
            except ImportError:
                ml_libraries[lib] = False

        # 1. Haar Cascade Detection (from real face_detector.py)
        try:
            if os.path.exists(self.model_paths["haar_cascade"]):
                self.haar_cascade = cv2.CascadeClassifier(
                    self.model_paths["haar_cascade"]
                )
                if not self.haar_cascade.empty():
                    self.available_methods.append("haar")
                    self.logger.info("✅ Haar cascade loaded successfully")
                else:
                    self.logger.warning(
                        "❌ Haar cascade file exists but failed to load"
                    )
            else:
                self.logger.warning(
                    f"❌ Haar cascade file not found: {self.model_paths['haar_cascade']}"
                )
        except Exception as e:
            self.logger.error(f"❌ Error loading Haar cascade: {e}")

        # 2. Dlib Detection (from real face_detector.py)
        try:
            if ml_libraries["dlib"]:
                import dlib

                self.dlib_detector = dlib.get_frontal_face_detector()
                self.available_methods.append("dlib")
                self.logger.info("✅ Dlib face detector initialized")

                # Try to load shape predictor if available
                if os.path.exists(self.model_paths["dlib_predictor"]):
                    self.dlib_predictor = dlib.shape_predictor(
                        self.model_paths["dlib_predictor"]
                    )
                    self.logger.info("✅ Dlib shape predictor loaded")
                else:
                    self.logger.warning(
                        f"⚠️  Dlib predictor not found: {self.model_paths['dlib_predictor']}"
                    )
            else:
                self.logger.warning("❌ Dlib not available")
        except Exception as e:
            self.logger.error(f"❌ Error initializing dlib: {e}")

        # 3. Two-Stage Detection (Haar + Dlib validation - proven method)
        if "haar" in self.available_methods and "dlib" in self.available_methods:
            self.available_methods.append("two_stage")
            self.logger.info("✅ Two-stage detection enabled (Haar + Dlib validation)")

        self.models_loaded = len(self.available_methods) > 0
        self.logger.info(
            f"🎯 Initialized {len(self.available_methods)} detection methods: {self.available_methods}"
        )

    def detect_faces_haar(
        self, image, scale_factor=1.1, min_neighbors=5, min_size=(30, 30)
    ):
        """Haar cascade face detection - extracted from real face_detector.py"""
        if "haar" not in self.available_methods:
            return {
                "success": False,
                "error": "Haar cascade not available",
                "detections": [],
            }

        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=scale_factor,
                minNeighbors=min_neighbors,
                minSize=min_size,
            )

            detections = []
            for x, y, w, h in faces:
                detections.append(
                    {
                        "bbox": [x, y, x + w, y + h],
                        "confidence": self.config["confidence_thresholds"]["haar"],
                        "method": "haar",
                    }
                )

            return {
                "success": True,
                "detections": detections,
                "method": "haar",
                "processing_time": 0,
            }

        except Exception as e:
            self.logger.error(f"Haar detection error: {e}")
            return {"success": False, "error": str(e), "detections": []}

    def detect_faces_dlib(self, image, upsample_times=1):
        """Dlib face detection - extracted from real face_detector.py"""
        if "dlib" not in self.available_methods:
            return {"success": False, "error": "Dlib not available", "detections": []}

        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            faces = self.dlib_detector(gray, upsample_times)

            detections = []
            for face in faces:
                x, y, w, h = (face.left(), face.top(), face.width(), face.height())
                detections.append(
                    {
                        "bbox": [x, y, x + w, y + h],
                        "confidence": self.config["confidence_thresholds"]["dlib"],
                        "method": "dlib",
                    }
                )

            return {
                "success": True,
                "detections": detections,
                "method": "dlib",
                "processing_time": 0,
            }

        except Exception as e:
            self.logger.error(f"Dlib detection error: {e}")
            return {"success": False, "error": str(e), "detections": []}

    def detect_faces_two_stage(self, image, confidence_threshold=0.5):
        """
        Two-stage face detection method proven in monolithic app.
        Stage 1: Haar cascade detection
        Stage 2: Dlib validation to filter false positives
        """
        try:
            # Ensure we have the required methods
            if (
                "haar" not in self.available_methods
                or "dlib" not in self.available_methods
            ):
                return {
                    "success": False,
                    "error": "Required methods (haar, dlib) not available",
                    "detections": [],
                }

            start_time = time.time()

            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Stage 1: Haar cascade for initial detection
            # Using same parameters as proven monolithic app
            faces = self.haar_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            # Initial face rectangles from Haar cascade
            face_rects = []
            for x, y, w, h in faces:
                face_rects.append([x, y, w, h])

            # Stage 2: Dlib validation with padded crop (filter false positives)
            # Tight crops strip the surrounding context that Dlib's HOG model
            # needs (forehead, chin, cheeks), causing it to reject valid faces.
            # Expand each Haar bbox by 100% margin before running Dlib.
            img_h, img_w = gray.shape[:2]
            filtered_face_rects = []

            for face_rect in face_rects:
                x, y, w, h = face_rect

                # Pad the crop by 100% of the face size on each side
                pad = int(max(w, h) * 1.0)
                px1 = max(0, x - pad)
                py1 = max(0, y - pad)
                px2 = min(img_w, x + w + pad)
                py2 = min(img_h, y + h + pad)

                face_region = gray[py1:py2, px1:px2]

                if face_region.size == 0:
                    continue

                dlib_faces = self.dlib_detector(face_region, 1)

                if len(dlib_faces) > 0:
                    filtered_face_rects.append(face_rect)

            # Convert to the expected output format
            detections = []
            for face_rect in filtered_face_rects:
                x, y, w, h = face_rect
                detections.append(
                    {
                        "bbox": [x, y, x + w, y + h],
                        "confidence": self.config["confidence_thresholds"]["two_stage"],
                        "method": "two_stage_haar_dlib",
                    }
                )

            processing_time = time.time() - start_time

            self.logger.info(
                f"Two-stage detection: {len(faces)} initial Haar detections → "
                f"{len(filtered_face_rects)} Dlib-validated faces in {processing_time:.3f}s"
            )

            return {
                "success": True,
                "detections": detections,
                "method": "two_stage_haar_dlib",
                "processing_time": processing_time,
                "initial_detections": len(faces),
                "validated_detections": len(filtered_face_rects),
            }

        except Exception as e:
            self.logger.error(f"Two-stage detection error: {e}")
            return {"success": False, "error": str(e), "detections": []}

    def detect_faces_multi_method(self, image, methods=None):
        """Run face detection using multiple methods for comparison."""
        if methods is None:
            methods = self.available_methods

        results = {}

        for method in methods:
            if method not in self.available_methods:
                results[method] = {"success": False, "error": f"{method} not available"}
                continue

            start_time = time.time()

            if method == "haar":
                result = self.detect_faces_haar(image)
            elif method == "dlib":
                result = self.detect_faces_dlib(image)
            elif method == "two_stage":
                result = self.detect_faces_two_stage(image)
            else:
                result = {"success": False, "error": f"Unknown method: {method}"}

            result["processing_time"] = time.time() - start_time
            results[method] = result

        return results

    def get_detection_summary(self):
        """Get summary of available detection methods and their status."""
        return {
            "available_methods": self.available_methods,
            "models_loaded": self.models_loaded,
            "model_paths": self.model_paths,
            "total_methods": len(self.available_methods),
        }

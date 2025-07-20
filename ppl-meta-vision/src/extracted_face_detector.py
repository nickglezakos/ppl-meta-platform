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

        # Model paths based on monolithic app structure
        self.model_paths = {
            "haar_cascade": "/Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/models/haarcascade_frontalface_default.xml",
            "ssd_config": "/Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/models/ssd-face.cfg",
            "ssd_weights": "/Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/models/ssd-face.weights",
            "dlib_predictor": "/Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/models/shape_predictor_68_face_landmarks.dat",
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

    def _initialize_detection_methods(self):
        """Initialize available face detection methods based on real monolithic app."""
        self.logger.info("🔧 Initializing face detection methods...")

        # Check for ML libraries availability
        ml_libraries = {"dlib": False, "mtcnn": False}

        for lib in ml_libraries:
            try:
                if lib == "dlib":
                    import dlib

                    ml_libraries[lib] = True
                elif lib == "mtcnn":
                    from mtcnn import MTCNN

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

        # 3. MTCNN (if available)
        try:
            if ml_libraries["mtcnn"]:
                from mtcnn import MTCNN

                self.mtcnn_detector = MTCNN()
                self.available_methods.append("mtcnn")
                self.logger.info("✅ MTCNN detector initialized")
            else:
                self.logger.warning("❌ MTCNN not available")
        except Exception as e:
            self.logger.error(f"❌ Error initializing MTCNN: {e}")

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
                    {"bbox": [x, y, x + w, y + h], "confidence": 1.0, "method": "haar"}
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
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                detections.append(
                    {"bbox": [x, y, x + w, y + h], "confidence": 1.0, "method": "dlib"}
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

    def detect_faces_mtcnn(self, image):
        """MTCNN face detection"""
        if "mtcnn" not in self.available_methods:
            return {"success": False, "error": "MTCNN not available", "detections": []}

        try:
            if len(image.shape) == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

            result = self.mtcnn_detector.detect_faces(rgb_image)

            detections = []
            for face in result:
                bbox = face["box"]
                x, y, w, h = bbox
                detections.append(
                    {
                        "bbox": [x, y, x + w, y + h],
                        "confidence": face["confidence"],
                        "method": "mtcnn",
                    }
                )

            return {
                "success": True,
                "detections": detections,
                "method": "mtcnn",
                "processing_time": 0,
            }

        except Exception as e:
            self.logger.error(f"MTCNN detection error: {e}")
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
            elif method == "mtcnn":
                result = self.detect_faces_mtcnn(image)
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

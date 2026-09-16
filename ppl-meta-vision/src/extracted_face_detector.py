# Extracted Face Detector Module for PPL Meta Vision Service
# Generated from VIS-001.2 - Code Extraction Phase
# Source: /Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/face_detector.py

import logging
import os
import sys
import time
from pathlib import Path
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
        self.loaded_model_ids = []

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
                    self.loaded_model_ids.append("face-haar-builtin")
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
                self.loaded_model_ids.append("face-dlib-builtin")
                self.logger.info("✅ Dlib face detector initialized")

                # Shape predictor is assignment-only (face_landmarks). File on disk
                # must not auto-activate.
                enable_landmarks = os.getenv(
                    "VISION_ENABLE_FACE_LANDMARKS", "false"
                ).lower() in ("1", "true", "yes")
                if enable_landmarks and os.path.exists(self.model_paths["dlib_predictor"]):
                    self.dlib_predictor = dlib.shape_predictor(
                        self.model_paths["dlib_predictor"]
                    )
                    self.logger.info("✅ Dlib shape predictor loaded (assigned)")
                    self.loaded_model_ids.append("face-landmarks-68-builtin")
                elif os.path.exists(self.model_paths["dlib_predictor"]):
                    self.logger.info(
                        "ℹ️  Dlib predictor present but not loaded (assignment-only)"
                    )
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
            self.loaded_model_ids.append("face-two-stage-builtin")
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

        If dlib is unavailable but haar is loaded, fall back to haar-only
        so instant detection still works on slim images.
        """
        try:
            if "haar" not in self.available_methods:
                return {
                    "success": False,
                    "error": "Required method (haar) not available",
                    "detections": [],
                }
            if "dlib" not in self.available_methods:
                self.logger.warning(
                    "⚠️ two_stage requested but dlib unavailable — falling back to haar"
                )
                return self.detect_faces_haar(image)

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

    def _normalize_runtime(self, runtime: Optional[str]) -> str:
        value = (runtime or "").lower()
        if value in ("haar", "face-haar-builtin"):
            return "haar"
        if value in ("dlib", "dlib_hog", "face-dlib-builtin"):
            return "dlib"
        if value in ("two_stage", "two_stage_haar_dlib", "face-two-stage-builtin"):
            return "two_stage"
        if value in ("onnx", "onnx_yolo", "yolo", "yolov8"):
            return "onnx"
        return value or "two_stage"

    def resolve_onnx_artifact_path(
        self,
        model_id: str,
        version: str = "1.0.0",
        artifact_uri: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve local ONNX path from uri, env cache, or Models service download."""
        if artifact_uri and Path(artifact_uri).is_file():
            return artifact_uri
        cache_root = Path(
            os.getenv(
                "VISION_ONNX_CACHE",
                os.path.join(os.path.dirname(__file__), "..", "onnx_cache"),
            )
        )
        cache_root.mkdir(parents=True, exist_ok=True)
        local = cache_root / f"{model_id}_{version}.onnx"
        if local.is_file():
            return str(local)

        models_url = os.getenv("MODELS_SERVICE_URL", "http://localhost:8013").rstrip("/")
        url = f"{models_url}/api/v1/mv-models/{model_id}/versions/{version}/artifact"
        try:
            import httpx

            with httpx.Client(timeout=60.0) as client:
                resp = client.get(url)
                if resp.status_code == 200 and resp.content:
                    local.write_bytes(resp.content)
                    return str(local)
                self.logger.warning(
                    "artifact fetch %s -> HTTP %s", url, resp.status_code
                )
        except Exception as exc:
            self.logger.warning("artifact fetch failed: %s", exc)

        # Shared monorepo artifact_store fallback
        repo_store = Path(
            os.getenv(
                "MODELS_ARTIFACT_ROOT",
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "ppl-meta-models",
                    "artifact_store",
                ),
            )
        )
        candidate_dir = repo_store / model_id / version
        if candidate_dir.is_dir():
            for path in candidate_dir.glob("*.onnx"):
                return str(path)
        return None

    def detect_faces_onnx(
        self,
        image,
        *,
        model_id: str = "face-yolo-onnx-os",
        version: str = "1.0.0",
        artifact_uri: Optional[str] = None,
        conf: float = 0.25,
        class_ids: Optional[list] = None,
    ):
        from onnx_yolo import detect_yolo_onnx

        path = self.resolve_onnx_artifact_path(model_id, version, artifact_uri)
        if not path:
            return {"success": False, "error": "onnx_artifact_missing", "detections": []}
        # Face models often have a single class; allow all if unspecified.
        result = detect_yolo_onnx(
            image,
            model_path=path,
            conf=conf,
            class_ids=class_ids,
            class_labels={0: "face"} if class_ids == [0] or class_ids is None else None,
        )
        if result.get("success"):
            for det in result.get("detections") or []:
                det["method"] = "onnx_yolo"
            result["method"] = "onnx_yolo"
            result["faces_detected"] = len(result.get("detections") or [])
        return result

    def detect_bodies_onnx(
        self,
        image,
        *,
        model_id: str = "body-yolo-person-os",
        version: str = "1.0.0",
        artifact_uri: Optional[str] = None,
        conf: float = 0.25,
        use_pose: Optional[bool] = None,
    ):
        """Detect person bodies. Prefer pose when model_id contains 'pose' or use_pose=True."""
        from onnx_yolo import (
            detect_yolo_onnx,
            detect_yolo_pose_onnx,
            estimate_dominant_colors,
            estimate_height_px,
            estimate_posture_from_keypoints,
        )

        path = self.resolve_onnx_artifact_path(model_id, version, artifact_uri)
        if not path:
            return {"success": False, "error": "onnx_artifact_missing", "detections": []}

        want_pose = use_pose if use_pose is not None else (
            "pose" in (model_id or "").lower() or model_id.endswith("-pose-os")
        )
        if want_pose:
            result = detect_yolo_pose_onnx(image, model_path=path, conf=conf)
            if result.get("success"):
                for det in result.get("detections") or []:
                    det["method"] = "onnx_yolo_pose"
                    det.setdefault("class_label", "person")
                    det.setdefault("class_id", 0)
                    posture = estimate_posture_from_keypoints(
                        det.get("keypoints"), det.get("bbox")
                    )
                    height = estimate_height_px(det.get("keypoints"), det.get("bbox"))
                    det["posture"] = posture.get("posture")
                    det["posture_confidence"] = posture.get("posture_confidence")
                    det["height_px"] = height.get("height_px")
                    det["height_relative"] = height.get("height_relative")
                    det["height_m"] = height.get("height_m")
                    colors = estimate_dominant_colors(
                        image,
                        bbox=det.get("bbox"),
                        keypoints=det.get("keypoints"),
                    )
                    det["dominant_colors"] = colors.get("dominant_colors")
                result["method"] = "onnx_yolo_pose"
                return result
            # Fall through to detect-only if pose decode failed hard
            if result.get("error") and result.get("error") != "onnx_session_unavailable":
                self.logger.warning(
                    "pose detect failed, falling back to person detect: %s",
                    result.get("error"),
                )
            # Pose weights unavailable: switch to person-os artifact for bbox detect
            if result.get("error") == "onnx_session_unavailable" or not result.get("success"):
                person_path = self.resolve_onnx_artifact_path(
                    "body-yolo-person-os", version, None
                )
                if person_path:
                    self.logger.warning(
                        "pose unavailable; using body-yolo-person-os for bbox detect"
                    )
                    path = person_path
                    model_id = "body-yolo-person-os"
        result = detect_yolo_onnx(
            image,
            model_path=path,
            conf=conf,
            class_ids=[0],  # COCO person
            class_labels={0: "person"},
        )
        if result.get("success"):
            for det in result.get("detections") or []:
                det["method"] = "onnx_yolo_person"
                det.setdefault("class_label", "person")
                det.setdefault("class_id", 0)
                posture = estimate_posture_from_keypoints(None, det.get("bbox"))
                height = estimate_height_px(None, det.get("bbox"))
                det["posture"] = posture.get("posture")
                det["posture_confidence"] = posture.get("posture_confidence")
                det["height_px"] = height.get("height_px")
                det["height_relative"] = height.get("height_relative")
                det["height_m"] = None
                colors = estimate_dominant_colors(
                    image, bbox=det.get("bbox"), keypoints=None
                )
                det["dominant_colors"] = colors.get("dominant_colors")
            result["method"] = "onnx_yolo_person"
        return result

    def detect_objects_onnx(
        self,
        image,
        *,
        model_id: str = "body-yolo-person-os",
        version: str = "1.0.0",
        artifact_uri: Optional[str] = None,
        conf: float = 0.25,
        class_ids: Optional[list] = None,
        class_labels: Optional[dict] = None,
    ):
        """
        Generic COCO object detection (not person-only).

        Uses the same YOLOv8n detect weights as body-yolo-person-os but allows
        arbitrary class_ids. Defaults to common left-luggage classes.
        """
        from onnx_yolo import (
            COCO80_LABELS,
            DEFAULT_LEFT_OBJECT_CLASS_IDS,
            detect_yolo_onnx,
        )

        path = self.resolve_onnx_artifact_path(model_id, version, artifact_uri)
        if not path:
            # Fall back to person detect weights (full COCO head)
            path = self.resolve_onnx_artifact_path("body-yolo-person-os", version, None)
            model_id = "body-yolo-person-os"
        if not path:
            return {"success": False, "error": "onnx_artifact_missing", "detections": []}

        ids = class_ids if class_ids is not None else list(DEFAULT_LEFT_OBJECT_CLASS_IDS)
        labels = class_labels if class_labels is not None else dict(COCO80_LABELS)
        result = detect_yolo_onnx(
            image,
            model_path=path,
            conf=conf,
            class_ids=ids,
            class_labels=labels,
        )
        if result.get("success"):
            for det in result.get("detections") or []:
                det["method"] = "onnx_yolo_object"
                cid = det.get("class_id")
                if cid is not None and not det.get("class_label"):
                    det["class_label"] = labels.get(int(cid), str(cid))
            result["method"] = "onnx_yolo_object"
            result["capability"] = "object_detection"
        return result

    def acquire_model(self, model_id: str, version: str = "1.0.0") -> None:
        """Refcount a loaded catalog version (builtins stay resident)."""
        if not hasattr(self, "_loader_refcount"):
            self._loader_refcount = {}
        key = f"{model_id}@{version}"
        self._loader_refcount[key] = self._loader_refcount.get(key, 0) + 1
        if model_id and model_id not in self.loaded_model_ids:
            self.loaded_model_ids.append(model_id)

    def release_model(self, model_id: str, version: str = "1.0.0") -> None:
        if not hasattr(self, "_loader_refcount"):
            self._loader_refcount = {}
        key = f"{model_id}@{version}"
        current = self._loader_refcount.get(key, 0)
        if current <= 1:
            self._loader_refcount.pop(key, None)
            # Builtins stay loaded; drop ONNX/user refs when refcount hits 0.
            if model_id and (
                model_id.startswith("user-")
                or model_id.endswith("-os")
                or "yolo" in model_id
            ):
                path = self.resolve_onnx_artifact_path(model_id, version)
                if path:
                    try:
                        from onnx_yolo import unload_session

                        unload_session(path)
                    except Exception:
                        pass
                if model_id in self.loaded_model_ids:
                    self.loaded_model_ids.remove(model_id)
        else:
            self._loader_refcount[key] = current - 1

    def detect_faces_pipeline(self, image, stages: Optional[list] = None, method: Optional[str] = None):
        """
        Execute a single-stage or two-stage pipeline from catalog resolve `stages`.

        stages: [{role, runtime|model_id, ...}, ...]
        Falls back to legacy method string when stages are absent.
        """
        if stages:
            roles = [str(s.get("role") or "").lower() for s in stages]
            runtimes = [
                self._normalize_runtime(s.get("runtime") or s.get("model_id"))
                for s in stages
            ]
            for stage in stages:
                self.acquire_model(
                    str(stage.get("model_id") or stage.get("runtime") or "unknown"),
                    str(stage.get("version") or "1.0.0"),
                )
            try:
                if len(stages) == 1 or (len(roles) == 1 and roles[0] == "single"):
                    runtime = runtimes[0]
                    stage0 = stages[0]
                    if runtime == "haar":
                        result = self.detect_faces_haar(image)
                    elif runtime == "dlib":
                        result = self.detect_faces_dlib(image)
                    elif runtime == "onnx":
                        hyper = stage0.get("hyperparameters") or {}
                        result = self.detect_faces_onnx(
                            image,
                            model_id=str(stage0.get("model_id") or "face-yolo-onnx-os"),
                            version=str(stage0.get("version") or "1.0.0"),
                            artifact_uri=stage0.get("artifact_uri"),
                            conf=float(hyper.get("confidence") or hyper.get("conf") or 0.25),
                            class_ids=hyper.get("class_ids"),
                        )
                    else:
                        result = self.detect_faces_two_stage(image)
                    if isinstance(result, dict):
                        result["pipeline_kind"] = "single"
                        result["stages"] = stages
                    return result
                # two_stage: proposal then refine (Haar→Dlib semantics when those runtimes)
                if runtimes[0] == "haar" and runtimes[1] == "dlib":
                    result = self.detect_faces_two_stage(image)
                elif runtimes[0] == "onnx":
                    stage0 = stages[0]
                    hyper = stage0.get("hyperparameters") or {}
                    result = self.detect_faces_onnx(
                        image,
                        model_id=str(stage0.get("model_id") or "face-yolo-onnx-os"),
                        version=str(stage0.get("version") or "1.0.0"),
                        artifact_uri=stage0.get("artifact_uri"),
                        conf=float(hyper.get("confidence") or hyper.get("conf") or 0.25),
                    )
                elif runtimes[0] == "haar":
                    result = self.detect_faces_haar(image)
                elif runtimes[0] == "dlib":
                    result = self.detect_faces_dlib(image)
                else:
                    result = self.detect_faces_two_stage(image)
                if isinstance(result, dict):
                    result["pipeline_kind"] = "two_stage"
                    result["stages"] = stages
                return result
            finally:
                for stage in stages:
                    self.release_model(
                        str(stage.get("model_id") or stage.get("runtime") or "unknown"),
                        str(stage.get("version") or "1.0.0"),
                    )

        runtime = self._normalize_runtime(method)
        if runtime == "haar":
            return self.detect_faces_haar(image)
        if runtime == "dlib":
            return self.detect_faces_dlib(image)
        if runtime == "onnx":
            return self.detect_faces_onnx(image)
        return self.detect_faces_two_stage(image)

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

    def get_runtime_health(self):
        summary = self.get_detection_summary()
        summary["loaded_model_ids"] = list(self.loaded_model_ids)
        summary["landmarks_loaded"] = bool(getattr(self, "dlib_predictor", None))
        summary["loader_refcount"] = dict(getattr(self, "_loader_refcount", {}) or {})
        return summary

    def get_detection_summary(self):
        """Get summary of available detection methods and their status."""
        return {
            "available_methods": self.available_methods,
            "models_loaded": self.models_loaded,
            "model_paths": self.model_paths,
            "total_methods": len(self.available_methods),
        }

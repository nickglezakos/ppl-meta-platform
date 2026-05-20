# ================================================================
# Phase 1: Vision Service Session Enhancement
# PPL Meta Platform - Enhanced Face Detection with Distance & Embeddings
# ================================================================

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# External dependencies for Phase 1
try:
    from deepface import DeepFace

    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    logging.warning("DeepFace not installed. Facial embeddings will be disabled.")

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Enhanced Vision Service with session-based face detection,
    distance calculation, and facial embeddings generation.

    Phase 1 Features:
    - Session-based processing (eliminates duplicate prevention)
    - Distance calculation using autonomous system methodology
    - DeepFace facial embeddings generation
    - Person routes tracking
    """

    def __init__(self, database_client, config: dict = None):
        self.db = database_client
        self.config = config or {}

        # Distance calculation settings (Autonomous PPL Meta System)
        self.distance_multiplier = self.config.get("distance_multiplier", 1000000.0)

        # DeepFace configuration
        self.embedding_model = self.config.get("embedding_model", "Facenet512")
        self.detector_backend = self.config.get("detector_backend", "opencv")

        # Session tracking
        self.current_session_uuid = None
        self.face_detection_sequence = 0

        logger.info("Enhanced Vision Service initialized for Phase 1")
        if DEEPFACE_AVAILABLE:
            logger.info(f"DeepFace enabled with model: {self.embedding_model}")
        else:
            logger.warning("DeepFace disabled - facial embeddings unavailable")

    async def start_session_based_face_detection(
        self,
        session_uuid: str,
        media_id: str,
        source_identifier: str,
        source_type: str,
        execution_trigger: str = "automatic",
        config: dict = None,
    ) -> Dict:
        """
        Start enhanced face detection with session management.

        Phase 1 Key Changes:
        - NO duplicate prevention checks (supports unlimited re-executions)
        - Session-based tracking for all detections
        - Distance calculation for every face
        - Facial embeddings generation
        - Person routes creation
        """

        self.current_session_uuid = session_uuid
        self.face_detection_sequence = 0

        # Enhanced configuration with Phase 1 features
        detection_config = {
            "confidence_threshold": config.get("confidence_threshold", 0.5),
            "frames_per_second": config.get("frames_per_second", 3),
            "method": config.get("method", "two_stage"),
            "enable_distance_calculation": config.get(
                "enable_distance_calculation", True
            ),
            "enable_embedding_generation": config.get(
                "enable_embedding_generation", True
            ),
            "enable_route_tracking": config.get("enable_route_tracking", True),
            **config,
        }

        logger.info(f"Starting session-based face detection for session {session_uuid}")
        logger.info(
            f"Enhanced features: distance={detection_config['enable_distance_calculation']}, "
            f"embeddings={detection_config['enable_embedding_generation']}, "
            f"routes={detection_config['enable_route_tracking']}"
        )

        try:
            # Create master workflow record
            await self._create_master_workflow_record(
                session_uuid,
                source_identifier,
                source_type,
                media_id,
                execution_trigger,
                detection_config,
            )

            # Process video with enhanced detection
            results = await self._process_video_enhanced(
                media_id, session_uuid, detection_config
            )

            # Generate person routes after face detection
            if detection_config["enable_route_tracking"]:
                await self._generate_person_routes(session_uuid)

            # Update master workflow with results
            await self._update_master_workflow_completion(session_uuid, results)

            return {
                "session_uuid": session_uuid,
                "status": "completed",
                "faces_detected": results.get("total_faces", 0),
                "faces_with_embeddings": results.get("faces_with_embeddings", 0),
                "faces_with_distance": results.get("faces_with_distance", 0),
                "person_routes_created": results.get("person_routes_created", 0),
                "processing_time_seconds": results.get("processing_time", 0),
                "enhanced_features": {
                    "distance_calculation": detection_config[
                        "enable_distance_calculation"
                    ],
                    "embedding_generation": detection_config[
                        "enable_embedding_generation"
                    ],
                    "route_tracking": detection_config["enable_route_tracking"],
                },
            }

        except Exception as e:
            logger.error(
                f"Enhanced face detection failed for session {session_uuid}: {e}"
            )
            await self._update_master_workflow_error(session_uuid, str(e))
            raise

    async def _process_video_enhanced(
        self, media_id: str, session_uuid: str, config: dict
    ) -> Dict:
        """
        Enhanced video processing with distance calculation and embeddings.
        """

        start_time = datetime.now()
        total_faces = 0
        faces_with_embeddings = 0
        faces_with_distance = 0

        # Get video information
        video_info = await self._get_video_info(media_id)
        video_path = video_info["file_path"]
        fps = video_info.get("fps", 30)

        # Initialize video capture
        cap = cv2.VideoCapture(video_path)
        frame_interval = int(fps / config["frames_per_second"])
        frame_count = 0
        processed_frames = 0

        logger.info(f"Processing video: {video_path}")
        logger.info(
            f"Target FPS: {config['frames_per_second']}, Frame interval: {frame_interval}"
        )

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Process frames at specified interval
                if frame_count % frame_interval == 0:
                    timestamp_ms = int((frame_count / fps) * 1000)

                    # Detect faces in frame
                    faces = await self._detect_faces_in_frame(
                        frame, timestamp_ms, config["confidence_threshold"]
                    )

                    # Process each detected face
                    for face in faces:
                        face_data = await self._process_face_enhanced(
                            face, frame, session_uuid, timestamp_ms, frame_count, config
                        )

                        if face_data:
                            total_faces += 1
                            if face_data.get("has_embedding"):
                                faces_with_embeddings += 1
                            if face_data.get("has_distance"):
                                faces_with_distance += 1

                    processed_frames += 1

                    # Progress logging
                    if processed_frames % 10 == 0:
                        logger.info(
                            f"Processed {processed_frames} frames, detected {total_faces} faces"
                        )

                frame_count += 1

        finally:
            cap.release()

        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Enhanced face detection completed: {total_faces} faces, "
            f"{faces_with_embeddings} with embeddings, {faces_with_distance} with distance"
        )

        return {
            "total_faces": total_faces,
            "faces_with_embeddings": faces_with_embeddings,
            "faces_with_distance": faces_with_distance,
            "processed_frames": processed_frames,
            "processing_time": processing_time,
        }

    async def _process_face_enhanced(
        self,
        face: Dict,
        frame: np.ndarray,
        session_uuid: str,
        timestamp_ms: int,
        frame_number: int,
        config: dict,
    ) -> Optional[Dict]:
        """
        Enhanced face processing with distance calculation and embeddings.
        """

        try:
            # Extract face bounding box
            x, y, width, height = face["x"], face["y"], face["width"], face["height"]
            confidence = face["confidence"]

            # Calculate distance using autonomous system methodology
            distance_from_camera = None
            face_area_pixels = None

            if config["enable_distance_calculation"]:
                face_area_pixels = width * height
                if face_area_pixels > 0:
                    distance_from_camera = self.distance_multiplier / face_area_pixels

            # Generate facial embedding
            facial_embedding = None
            embedding_confidence = None

            if config["enable_embedding_generation"] and DEEPFACE_AVAILABLE:
                facial_embedding, embedding_confidence = (
                    await self._generate_facial_embedding(
                        frame, x, y, width, height, frame_number=frame_number
                    )
                )

            # Calculate center coordinates for routes
            center_x = x + (width / 2)
            center_y = y + (height / 2)

            # Create face detection record
            face_id = await self._create_face_detection_record(
                session_uuid=session_uuid,
                timestamp_ms=timestamp_ms,
                frame_number=frame_number,
                x=x,
                y=y,
                width=width,
                height=height,
                confidence=confidence,
                distance_from_camera=distance_from_camera,
                face_area_pixels=face_area_pixels,
                facial_embedding=facial_embedding,
                embedding_confidence=embedding_confidence,
            )

            self.face_detection_sequence += 1

            return {
                "face_id": face_id,
                "center_x": center_x,
                "center_y": center_y,
                "distance_from_camera": distance_from_camera,
                "has_embedding": facial_embedding is not None,
                "has_distance": distance_from_camera is not None,
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"Error processing face: {e}")
            return None

    async def _generate_facial_embedding(
        self, frame: np.ndarray, x: int, y: int, width: int, height: int,
        frame_number: Optional[int] = None
    ) -> Tuple[Optional[List[float]], Optional[float]]:
        """
        Generate 512-dimensional facial embedding using DeepFace.

        Applies Fix 1 (multi-face crop rejection) and Fix 2 (facial_area
        alignment) from docs/modules/MVR merge/EMBEDDING_CONTAMINATION.md.

        Returns:
            Tuple of (embedding_vector, confidence_score), or (None, None)
            if the crop is rejected due to contamination risk.
        """

        if not DEEPFACE_AVAILABLE:
            return None, None

        try:
            # Extract face region from full frame using detection bbox
            face_img = frame[y : y + height, x : x + width]

            # Convert BGR to RGB for DeepFace
            face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)

            # Generate embedding using DeepFace
            embedding_result = DeepFace.represent(
                img_path=face_rgb,
                model_name=self.embedding_model,
                enforce_detection=False,
                detector_backend=self.detector_backend,
            )

            # DeepFace.represent may return different shapes depending on version:
            # - a list of dicts: [{"embedding": [...]}, ...]  <- modern, primary path
            # - a flat list of floats (the embedding vector)
            # - a numpy array
            embedding = None

            # If it's a numpy array (legacy fallback)
            if isinstance(embedding_result, np.ndarray):
                embedding = embedding_result.tolist()

            # If it's a list (modern DeepFace format)
            elif isinstance(embedding_result, list):
                if len(embedding_result) == 0:
                    embedding = None
                else:
                    first = embedding_result[0]
                    # Primary case: list of dicts with 'embedding' key
                    if isinstance(first, dict) and "embedding" in first:
                        # FIX 1: Reject multi-face crops.
                        # When > 1 face is detected in the crop, result[0] is the
                        # most prominent/frontal face — which may be a *different*
                        # person than the one whose bbox we are processing, causing
                        # identity contamination in the stored MVR embedding.
                        # See: docs/modules/MVR merge/EMBEDDING_CONTAMINATION.md
                        if len(embedding_result) > 1:
                            logger.warning(
                                f"Multi-face crop at frame={frame_number} "
                                f"bbox=[{x},{y},{x + width},{y + height}]: "
                                f"{len(embedding_result)} faces detected. "
                                f"Rejecting embedding to prevent contamination."
                            )
                            return None, None

                        # FIX 2: Refine the confidence calculation using the
                        # face-aligned sub-region reported by the detector
                        # (facial_area) rather than the raw bbox crop.
                        facial_area = first.get("facial_area", {})
                        if facial_area:
                            fx = facial_area.get("x", 0)
                            fy = facial_area.get("y", 0)
                            fw = facial_area.get("w", face_img.shape[1])
                            fh = facial_area.get("h", face_img.shape[0])
                            aligned = face_img[fy : fy + fh, fx : fx + fw]
                            if aligned.size > 0:
                                face_img = aligned

                        embedding = first["embedding"]
                    else:
                        # Legacy: flat list of floats — cannot check face count
                        if all(isinstance(v, (int, float)) for v in embedding_result):
                            embedding = embedding_result
                        elif isinstance(first, (int, float)):
                            embedding = embedding_result
                        elif isinstance(first, (list, tuple, np.ndarray)):
                            try:
                                embedding = list(first)
                            except Exception:
                                embedding = None

            # If we found a clean embedding, compute confidence and return
            if embedding is not None and len(embedding) > 0:
                confidence = self._calculate_embedding_confidence(face_img)
                return embedding, confidence

        except Exception as e:
            logger.warning(f"Failed to generate facial embedding: {e}")

        return None, None

    def _calculate_embedding_confidence(self, face_img: np.ndarray) -> float:
        """
        Calculate embedding confidence based on face image quality.
        """

        try:
            # Basic quality metrics
            height, width = face_img.shape[:2]

            # Size-based confidence (larger faces generally better)
            size_confidence = min(
                1.0, (width * height) / 10000
            )  # Normalize to 100x100 baseline

            # Sharpness-based confidence (Laplacian variance)
            gray = (
                cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
                if len(face_img.shape) == 3
                else face_img
            )
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_confidence = min(1.0, sharpness / 1000)  # Normalize

            # Brightness-based confidence (avoid too dark/bright)
            brightness = np.mean(gray)
            brightness_confidence = (
                1.0 - abs(brightness - 128) / 128
            )  # Optimal around 128

            # Combined confidence
            overall_confidence = (
                size_confidence + sharpness_confidence + brightness_confidence
            ) / 3

            return max(0.1, min(1.0, overall_confidence))  # Clamp between 0.1 and 1.0

        except Exception as e:
            logger.warning(f"Error calculating embedding confidence: {e}")
            return 0.5  # Default confidence

    async def _generate_person_routes(self, session_uuid: str) -> int:
        """
        Generate person routes from face detections for movement tracking.

        Phase 1 Implementation:
        - Creates route points from face detection centers
        - Calculates movement velocity between consecutive detections
        - Stores spatial analysis data
        """

        logger.info(f"Generating person routes for session {session_uuid}")

        try:
            # Get all person objects for this session
            persons = await self.db.get_person_objects_by_session(session_uuid)
            routes_created = 0

            for person in persons:
                person_id = person["id"]

                # Get face detections for this person, ordered by timestamp
                face_detections = await self.db.get_face_detections_by_person(
                    person_id, order_by="timestamp_ms"
                )

                if len(face_detections) < 1:
                    continue

                # Create route points from face detections
                for i, detection in enumerate(face_detections):
                    # Calculate center coordinates
                    center_x = detection["x"] + (detection["width"] / 2)
                    center_y = detection["y"] + (detection["height"] / 2)

                    # Calculate velocity from previous detection
                    velocity_x = velocity_y = velocity_magnitude = direction_radians = (
                        0.0
                    )

                    if i > 0:
                        prev_detection = face_detections[i - 1]
                        prev_center_x = prev_detection["x"] + (
                            prev_detection["width"] / 2
                        )
                        prev_center_y = prev_detection["y"] + (
                            prev_detection["height"] / 2
                        )

                        time_diff = (
                            detection["timestamp_ms"] - prev_detection["timestamp_ms"]
                        ) / 1000.0

                        if time_diff > 0:
                            velocity_x = (center_x - prev_center_x) / time_diff
                            velocity_y = (center_y - prev_center_y) / time_diff
                            velocity_magnitude = np.sqrt(velocity_x**2 + velocity_y**2)
                            direction_radians = np.arctan2(velocity_y, velocity_x)

                    # Create route point
                    route_point = {
                        "person_object_id": person_id,
                        "session_uuid": session_uuid,
                        "sequence_number": i + 1,
                        "timestamp_ms": detection["timestamp_ms"],
                        "frame_number": detection.get("frame_number"),
                        "center_x": center_x,
                        "center_y": center_y,
                        "bounding_box_width": detection["width"],
                        "bounding_box_height": detection["height"],
                        "distance_from_camera": detection.get("distance_from_camera"),
                        "face_area_pixels": detection.get("face_area_pixels"),
                        "velocity_x": velocity_x,
                        "velocity_y": velocity_y,
                        "velocity_magnitude": velocity_magnitude,
                        "direction_radians": direction_radians,
                        "confidence_score": detection["confidence"],
                        "detection_quality": self._classify_detection_quality(
                            detection["confidence"]
                        ),
                    }

                    await self.db.create_person_route_point(route_point)
                    routes_created += 1

                # Update person object with movement summary
                await self._update_person_movement_summary(person_id, face_detections)

            logger.info(
                f"Created {routes_created} route points for {len(persons)} persons"
            )
            return routes_created

        except Exception as e:
            logger.error(f"Error generating person routes: {e}")
            return 0

    def _classify_detection_quality(self, confidence: float) -> str:
        """Classify detection quality based on confidence score."""
        if confidence >= 0.9:
            return "excellent"
        elif confidence >= 0.75:
            return "good"
        elif confidence >= 0.5:
            return "fair"
        else:
            return "poor"

    async def _update_person_movement_summary(
        self, person_id: str, face_detections: List[Dict]
    ):
        """Update person object with movement summary statistics."""

        if len(face_detections) < 2:
            return

        # Calculate total movement distance
        total_distance = 0.0
        velocities = []

        for i in range(1, len(face_detections)):
            curr = face_detections[i]
            prev = face_detections[i - 1]

            curr_x = curr["x"] + (curr["width"] / 2)
            curr_y = curr["y"] + (curr["height"] / 2)
            prev_x = prev["x"] + (prev["width"] / 2)
            prev_y = prev["y"] + (prev["height"] / 2)

            # Distance between consecutive detections
            distance = np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)
            total_distance += distance

            # Velocity calculation
            time_diff = (curr["timestamp_ms"] - prev["timestamp_ms"]) / 1000.0
            if time_diff > 0:
                velocity = distance / time_diff
                velocities.append(velocity)

        # Time in frame
        first_detection = face_detections[0]
        last_detection = face_detections[-1]
        time_in_frame = (
            last_detection["timestamp_ms"] - first_detection["timestamp_ms"]
        ) / 1000.0

        # Average velocity
        avg_velocity = np.mean(velocities) if velocities else 0.0

        # Calculate distance statistics
        distances = [
            d.get("distance_from_camera")
            for d in face_detections
            if d.get("distance_from_camera")
        ]
        avg_distance = np.mean(distances) if distances else None
        min_distance = min(distances) if distances else None
        max_distance = max(distances) if distances else None

        # Update person object
        await self.db.update_person_movement_summary(
            person_id=person_id,
            total_route_points=len(face_detections),
            movement_distance_pixels=total_distance,
            average_velocity=avg_velocity,
            time_in_frame_seconds=time_in_frame,
            average_distance=avg_distance,
            min_distance=min_distance,
            max_distance=max_distance,
        )

    # ================================================================
    # Master Workflow Management
    # ================================================================

    async def _create_master_workflow_record(
        self,
        session_uuid: str,
        source_identifier: str,
        source_type: str,
        source_id: str,
        execution_trigger: str,
        configuration: dict,
    ):
        """Create master workflow record for session tracking."""

        workflow_data = {
            "session_uuid": session_uuid,
            "source_identifier": source_identifier,
            "source_type": source_type,
            "source_id": source_id,
            "execution_trigger": execution_trigger,
            "status": "processing",
            "current_stage": "face_detection",
            "configuration": json.dumps(configuration),
            "started_at": datetime.now().isoformat(),
        }

        await self.db.create_master_workflow(workflow_data)
        logger.info(f"Created master workflow for session {session_uuid}")

    async def _update_master_workflow_completion(
        self, session_uuid: str, results: Dict
    ):
        """Update master workflow with completion results."""

        update_data = {
            "status": "completed",
            "current_stage": "completed",
            "progress_percentage": 100.0,
            "completed_at": datetime.now().isoformat(),
            "total_faces_detected": results.get("total_faces", 0),
            "processing_duration_seconds": int(results.get("processing_time", 0)),
        }

        await self.db.update_master_workflow(session_uuid, update_data)
        logger.info(f"Updated master workflow completion for session {session_uuid}")

    async def _update_master_workflow_error(
        self, session_uuid: str, error_message: str
    ):
        """Update master workflow with error status."""

        update_data = {
            "status": "failed",
            "error_message": error_message,
            "completed_at": datetime.now().isoformat(),
        }

        await self.db.update_master_workflow(session_uuid, update_data)
        logger.error(
            f"Updated master workflow error for session {session_uuid}: {error_message}"
        )

    # ================================================================
    # Database Integration Methods (to be implemented by database client)
    # ================================================================

    async def _get_video_info(self, media_id: str) -> Dict:
        """Get video file information from database."""
        # Implementation depends on existing media service integration
        pass

    async def _detect_faces_in_frame(
        self, frame: np.ndarray, timestamp_ms: int, confidence_threshold: float
    ) -> List[Dict]:
        """Detect faces in a single frame using existing face detection model."""
        # Implementation depends on existing face detection model
        pass

    async def _create_face_detection_record(self, **kwargs) -> str:
        """Create face detection record in database."""
        # Implementation depends on existing database schema
        pass


# ================================================================
# Phase 1 Configuration Example
# ================================================================

PHASE1_VISION_CONFIG = {
    # Distance calculation (Autonomous PPL Meta System)
    "distance_multiplier": 1000000.0,
    # DeepFace configuration
    "embedding_model": "Facenet512",  # 512-dimensional embeddings
    "detector_backend": "opencv",
    # Enhanced features
    "enable_distance_calculation": True,
    "enable_embedding_generation": True,
    "enable_route_tracking": True,
    # Face detection settings
    "confidence_threshold": 0.5,
    "frames_per_second": 3,
    "method": "two_stage",
}


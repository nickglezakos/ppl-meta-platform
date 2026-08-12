"""
PPL Meta Vision Service - Face Grouping Engine
Independent implementation of the face grouping algorithm for PPL Thread workflow.

This module implements the same percentage-based tolerance matching algorithm
as PPL Meta Mini's FaceGroupingEngine, but as a completely separate
implementation to maintain mini's autonomy.

Grouping is performed through a configurable three-tier discrimination cascade:

1. Tier 1 - Position tolerance: faces are matched to a track when they fall
   within a tolerance of the track's position. The tolerance is proportional to
   the face's bounding-box size (size_tolerance_factor) when bbox data is
   available, falling back to the legacy percentage-of-position tolerance when
   it is not. This removes the positional dependency of the original formula
   (x_tolerance = x1 * tolerance_percent) which grew unreasonable with
   distance from the image origin.

2. Tier 2 - Velocity vector discrimination (optional): when enabled, a
   positionally-close face is rejected if it is inconsistent with where the
   track's smoothed velocity predicts it should be. This disambiguates two
   people crossing paths even when they momentarily occupy the same pixels.
   Disabled by default because noisy/jittery detections can overshoot the
   prediction and require calibration against the deployment's frame rate.

3. Tier 3 - Embedding similarity gate (optional): when enabled and both the
   face and the track carry a face embedding, a positionally-close and
   velocity-consistent candidate is rejected if its embedding is dissimilar.
   This separates two people who are moving together (same velocity) but are
   visually distinct. Skipped when either side lacks an embedding.

Key Features:
- Size-proportional tolerance matching (bbox-based, percentage fallback)
- Chronological frame processing
- Quality-weighted face grouping
- Optional velocity and embedding discrimination
- Identical base algorithm logic to PPL Meta Mini
- Independent implementation with zero hard dependencies
"""

import logging
import math
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VisionFaceGroupingEngine:
    """
    Independent face grouping engine for PPL Meta Vision Service.

    Implements the same percentage-based tolerance matching algorithm
    as PPL Meta Mini's FaceGroupingEngine, but as a completely separate
    implementation to maintain mini's autonomy.
    """

    def __init__(self, embedding_extractor: Optional[Callable] = None):
        """
        Initialize the face grouping engine with PPL Mini default settings.

        Args:
            embedding_extractor: Optional callable that produces a face
                embedding for a face record lazily (in-memory). Signature:
                ``callable(face_record: Dict) -> Optional[List[float]]``.
                Used by Tier 3 to obtain embeddings on demand. When not
                provided (or when it returns None), Tier 3 remains a no-op.
        """
        self.tolerance_percent = 20.0
        self.quality_weights = {
            "sharpness": 0.4,
            "exposure": 0.3,
            "contrast": 0.2,
            "noise": 0.1,
        }

        # Lazy, in-memory embedding extraction for Tier 3. Kept alongside the
        # track state and garbage-collected when the engine is destroyed.
        self._embedding_extractor = embedding_extractor
        self._extracted_embeddings = {}  # face_id -> embedding (in-memory cache)

        # --- Tier 1: position tolerance (size-proportional, percentage fallback) ---
        # When bbox size is available, tolerance = bbox_size * size_tolerance_factor.
        # When no bbox is present, falls back to legacy x1 * tolerance_percent.
        self.use_size_based_tolerance = True
        self.size_tolerance_factor = 0.5

        # --- Tier 2: velocity vector discrimination (self-activating) ---
        # Auto-activates per-track only when the track's smoothed velocity
        # magnitude exceeds velocity_activation_threshold. Stationary tracks
        # (velocity ~ 0) are always considered consistent and never rejected.
        # Set threshold to 0 to always activate, or a positive value to gate on
        # meaningful motion. Velocity is time-normalized (px/ms) so one global
        # threshold works across cameras with different frame rates.
        self.velocity_activation_threshold = 0.0  # 0 = always, >0 = auto on motion
        self.velocity_smoothing_alpha = 0.3  # EMA smoothing factor
        self.min_frames_for_velocity = 2  # frames of history before velocity is meaningful
        self.velocity_inconsistency_factor = 1.5  # reject when |pred - actual| > bbox_size * factor
        self._min_velocity_size_px = 20.0  # floor for bbox size when no bbox is available

        # --- Tier 3: embedding similarity gate (always on, self-gating) ---
        # Rejects a positionally-close + velocity-consistent candidate when its
        # embedding is dissimilar. Self-regulating: skipped when either side
        # lacks an embedding, so it is a no-op until embeddings are available.
        self.embedding_gate_enabled = True  # safe because it self-gates on missing embeddings
        self.embedding_similarity_threshold = 0.6  # minimum cosine similarity

        # Tracking state (reset per session)
        self.active_tracks = {}
        self.next_person_id = 1
        self.processing_stats = {
            "tracked_faces": 0,
            "new_faces": 0,
            "merge_operations": 0,
            "frames_processed": 0,
            "tier1_position_matched": 0,
            "tier2_velocity_rejected": 0,
            "tier3_embedding_rejected": 0,
        }

    def calculate_position_distance(self, pos1: Dict, pos2: Dict) -> Dict[str, float]:
        """
        Calculate position-based distance with tolerance matching.

        Tolerance is computed from the maximum bounding-box size of the two
        candidates when available (size_proportional), otherwise it falls back
        to the legacy percentage-of-position tolerance for backward
        compatibility. This removes the positional dependency of the original
        formula: a face's positional uncertainty is tied to its spatial extent,
        not to how far it sits from the image origin.

        Args:
            pos1: First position dict with 'x' and 'y' keys and optional 'size'
            pos2: Second position dict with 'x' and 'y' keys and optional 'size'

        Returns:
            Dictionary containing:
            - x_distance: Absolute X coordinate difference
            - y_distance: Absolute Y coordinate difference
            - euclidean_distance: Geometric distance
            - combined_distance: Weighted combination for matching
            - within_tolerance: Boolean indicating if within tolerance
            - x_tolerance_used: X tolerance value applied
            - y_tolerance_used: Y tolerance value applied
        """
        x1, y1 = float(pos1["x"]), float(pos1["y"])
        x2, y2 = float(pos2["x"]), float(pos2["y"])

        # Calculate absolute differences
        x_distance = abs(x1 - x2)
        y_distance = abs(y1 - y2)

        # Determine tolerance: prefer bounding-box size when available.
        size1 = float(pos1.get("size", 0.0) or 0.0)
        size2 = float(pos2.get("size", 0.0) or 0.0)
        bbox_size = max(size1, size2)

        if self.use_size_based_tolerance and bbox_size > 0.0:
            # Tolerance proportional to the face's spatial extent.
            x_tolerance = bbox_size * self.size_tolerance_factor
            y_tolerance = bbox_size * self.size_tolerance_factor
            tolerance_mode = "size_proportional"
        else:
            # Legacy percentage-based tolerance (same as PPL Meta Mini).
            x_tolerance = x1 * (self.tolerance_percent / 100.0)
            y_tolerance = y1 * (self.tolerance_percent / 100.0)
            tolerance_mode = "percentage"

        # Check if within tolerance thresholds
        x_within_tolerance = x_distance <= x_tolerance
        y_within_tolerance = y_distance <= y_tolerance

        # Calculate Euclidean distance
        euclidean_distance = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

        # Calculate combined distance metric (weighted, same as PPL Mini)
        combined_distance = (
            x_distance * 0.3 + y_distance * 0.3 + euclidean_distance * 0.4
        )

        return {
            "x_distance": x_distance,
            "y_distance": y_distance,
            "euclidean_distance": euclidean_distance,
            "combined_distance": combined_distance,
            "within_tolerance": x_within_tolerance and y_within_tolerance,
            "x_tolerance_used": x_tolerance,
            "y_tolerance_used": y_tolerance,
            "tolerance_mode": tolerance_mode,
        }

    def _reset_processing_state(self):
        """Reset processing state for new session."""
        self.active_tracks = {}
        self.next_person_id = 1
        # Clear the in-memory embedding cache so a reused engine does not leak
        # embeddings from a previous session.
        self._extracted_embeddings = {}
        self.processing_stats = {
            "tracked_faces": 0,
            "new_faces": 0,
            "merge_operations": 0,
            "frames_processed": 0,
            "tier1_position_matched": 0,
            "tier2_velocity_rejected": 0,
            "tier3_embedding_rejected": 0,
        }

    def _extract_face_position(self, face_record: Dict) -> Dict[str, float]:
        """
        Extract face position from detection record.

        Supports multiple position formats for compatibility.
        """
        # Try explicit position fields first
        if "position_x" in face_record and "position_y" in face_record:
            return {
                "x": float(face_record["position_x"]),
                "y": float(face_record["position_y"]),
            }

        # Fall back to bbox coordinates (use top-left as position)
        if all(key in face_record for key in ["bbox_x1", "bbox_y1"]):
            return {
                "x": float(face_record["bbox_x1"]),
                "y": float(face_record["bbox_y1"]),
            }

        # Default fallback
        logger.warning(
            f"No position data found for face {face_record.get('id', 'unknown')}"
        )
        return {"x": 0.0, "y": 0.0}

    def _extract_bbox_size(self, face_record: Dict) -> float:
        """
        Extract the spatial extent (bounding-box size) of a face detection.

        Used by the size-proportional tolerance (Tier 1). Returns the larger of
        width and height so the tolerance scales with the face's dominant axis.

        Args:
            face_record: Face detection record with bbox fields

        Returns:
            Float size in pixels, or 0.0 when no bbox is available
        """
        if all(
            key in face_record
            for key in ["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]
        ):
            try:
                width = abs(float(face_record["bbox_x2"]) - float(face_record["bbox_x1"]))
                height = abs(
                    float(face_record["bbox_y2"]) - float(face_record["bbox_y1"])
                )
                return max(width, height)
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _find_best_track_match(
        self,
        face_position: Dict[str, float],
        face_size: float = 0.0,
        face_record: Optional[Dict] = None,
        frame_number: int = 0,
    ) -> Tuple[Optional[str], float]:
        """
        Find the best matching active track for a face using the three-tier
        discrimination cascade.

        Tier 1 (position): the face must fall within the track's position
            tolerance (size-proportional with percentage fallback).
        Tier 2 (velocity, optional): the face must be consistent with the
            track's predicted next position given its smoothed velocity.
        Tier 3 (embedding, optional): if both carry embeddings, the face must be
            visually similar to the track.

        Only candidates that pass all enabled tiers are considered; the closest
        surviving candidate (by combined distance) wins.

        Returns:
            Tuple of (track_id, distance) or (None, inf) if no match
        """
        best_match = None
        best_distance = float("inf")

        for track_id, track_info in self.active_tracks.items():
            track_position = track_info["position"]
            track_size = track_info.get("size", 0.0)

            # Enrich position dicts with size for the size-proportional tolerance.
            pos1 = dict(face_position)
            pos2 = dict(track_position)
            if face_size > 0.0:
                pos1["size"] = face_size
            if track_size > 0.0:
                pos2["size"] = track_size

            distance_data = self.calculate_position_distance(pos1, pos2)

            # Tier 1: position must be within tolerance.
            if not distance_data["within_tolerance"]:
                continue

            # Tier 2: velocity discrimination (self-activating).
            if not self._velocities_consistent(
                face_position, frame_number, face_record, track_info
            ):
                continue

            # Tier 3: embedding gate (opt-in).
            if self.embedding_gate_enabled and face_record is not None:
                if not self._embeddings_similar(face_record, track_info):
                    continue

            # Track how many faces reached a positive position match.
            self.processing_stats["tier1_position_matched"] += 1

            # Choose the closest surviving candidate.
            if distance_data["combined_distance"] < best_distance:
                best_match = track_id
                best_distance = distance_data["combined_distance"]

        return best_match, best_distance

    def _velocities_consistent(
        self,
        face_position: Dict[str, float],
        face_frame: int,
        face_record: Optional[Dict],
        track_info: Dict,
    ) -> bool:
        """
        Check whether a face position is consistent with the track's predicted
        next position derived from its smoothed velocity.

        The track's velocity projects its current position forward to the face's
        observation time; if the face is farther than bbox_size * velocity_inconsistency_factor
        from that projection, it is treated as a different person (e.g. crossing
        paths).

        Self-activating: if the track's velocity magnitude is below
        velocity_activation_threshold there is no meaningful motion to
        discriminate by, so the face is always considered consistent. Tracks
        without enough history are also always considered consistent.

        Args:
            face_position: New face position
            face_frame: Frame number of the new face
            face_record: Incoming face record (for time-based prediction)
            track_info: Active track state

        Returns:
            True if consistent or no meaningful motion, False if rejected
        """
        if track_info.get("frame_history", 1) < self.min_frames_for_velocity:
            return True

        velocity = track_info.get("velocity", {"x": 0.0, "y": 0.0})
        vel_mag = math.sqrt(velocity["x"] ** 2 + velocity["y"] ** 2)

        # Self-activating: skip when there is no meaningful motion.
        if vel_mag < self.velocity_activation_threshold:
            return True

        current_pos = track_info["position"]

        # Time-normalized prediction: velocity is px/ms, dt is in milliseconds.
        dt_ms = self._elapsed_ms_between(
            track_info.get("last_seen_at"),
            face_record,
            track_info.get("last_seen_frame"),
            face_frame,
        )
        dt_ms = max(dt_ms, 1.0)
        pred_x = current_pos["x"] + velocity["x"] * dt_ms
        pred_y = current_pos["y"] + velocity["y"] * dt_ms

        dist = math.sqrt(
            (pred_x - face_position["x"]) ** 2 + (pred_y - face_position["y"]) ** 2
        )

        # Use the track's bbox size for the threshold, with a minimum floor so
        # the filter does not reject everything when no bbox is available.
        size = track_info.get("size", 0.0) or 0.0
        effective_size = max(size, self._min_velocity_size_px)

        threshold = effective_size * self.velocity_inconsistency_factor
        consistent = dist <= threshold

        if not consistent:
            self.processing_stats["tier2_velocity_rejected"] += 1

        return consistent

    @staticmethod
    def _elapsed_ms_between(
        prev_ts,
        face_record: Optional[Dict],
        prev_frame: Optional[int] = None,
        cur_frame: Optional[int] = None,
    ) -> float:
        """
        Compute the elapsed time in milliseconds between a previous timestamp and
        the current face's created_at timestamp.

        Falls back to a frame-delta heuristic when timestamps are unavailable or
        unrealistically close (coarse/identical timestamps, e.g. synthetic test
        data), assuming ~33ms per frame.
        """
        cur_ts = None
        if face_record is not None:
            cur_ts = face_record.get("created_at")

        dt_ms = None
        try:
            if prev_ts is not None and cur_ts is not None:
                candidate = (cur_ts - prev_ts).total_seconds() * 1000.0
                # Reject unrealistically small deltas (timestamp too coarse).
                if candidate >= 5.0:
                    dt_ms = candidate
        except (TypeError, AttributeError):
            pass

        if dt_ms is None:
            # Fallback: frame-delta heuristic (~33ms per frame).
            if prev_frame is not None and cur_frame is not None:
                dt_ms = max(cur_frame - prev_frame, 1) * 33.0
            else:
                dt_ms = 33.0

        return dt_ms

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Compute cosine similarity between two embedding vectors.

        Args:
            a: First embedding vector
            b: Second embedding vector

        Returns:
            Cosine similarity in [-1.0, 1.0]
        """
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _get_face_embedding(self, face_record: Dict) -> Optional[List[float]]:
        """
        Lazily obtain a face embedding, preferring the record's own field and
        otherwise calling the injected extractor. Results are cached in-memory
        per face id so each face is only ever computed once.

        Returns None when no extractor is available, extraction fails, or the
        face has no id to cache by.
        """
        face_id = face_record.get("id")
        if face_id and face_id in self._extracted_embeddings:
            return self._extracted_embeddings[face_id]

        embedding = face_record.get("embedding")
        if not embedding and self._embedding_extractor is not None:
            try:
                embedding = self._embedding_extractor(face_record)
            except Exception as e:  # noqa: BLE001 - extractor failure must not break grouping
                logger.warning(
                    f"Embedding extraction failed for face {face_id}: {e}"
                )
                embedding = None

        if face_id and embedding:
            self._extracted_embeddings[face_id] = embedding

        return embedding

    def _embeddings_similar(self, face_record: Dict, track_info: Dict) -> bool:
        """
        Check whether a face's embedding is similar to the track's stored
        embedding (Tier 3). Embeddings are obtained lazily (in-memory) and the
        comparison is skipped when either side lacks an embedding.

        Args:
            face_record: Incoming face detection record
            track_info: Active track state

        Returns:
            True if similar, embeddings absent, or gate disabled
        """
        if not self.embedding_gate_enabled:
            return True

        face_emb = self._get_face_embedding(face_record)
        track_emb = track_info.get("embedding")

        # No embedding on either side -> cannot discriminate, accept.
        if not face_emb or not track_emb:
            return True

        similarity = self._cosine_similarity(face_emb, track_emb)
        similar = similarity >= self.embedding_similarity_threshold

        if not similar:
            self.processing_stats["tier3_embedding_rejected"] += 1
            logger.debug(
                f"Tier 3 rejected face {face_record.get('id')}: "
                f"embedding similarity {similarity:.3f} < {self.embedding_similarity_threshold}"
            )

        return similar

    def _create_new_track(
        self,
        face_record: Dict,
        face_position: Dict[str, float],
        frame_number: int,
        face_size: float = 0.0,
    ) -> str:
        """
        Create a new person track for unmatched face.

        Initializes velocity tracking state (zero velocity) and stores the
        face's embedding for later Tier 3 discrimination.

        Returns:
            New person track ID
        """
        person_id = f"person_{self.next_person_id}"
        self.next_person_id += 1

        created_at = face_record.get("created_at") or datetime.now()

        self.active_tracks[person_id] = {
            "person_id": person_id,
            "position": face_position,
            "size": face_size,
            "prev_position": face_position,
            "prev_frame": frame_number,
            "velocity": {"x": 0.0, "y": 0.0},
            "frame_history": 1,
            "embedding": self._get_face_embedding(face_record),
            "last_seen_frame": frame_number,
            "last_seen_at": created_at,
            "prev_at": created_at,
            "face_count": 1,
            "first_face_id": face_record["id"],
            "created_at": created_at,
        }

        self.processing_stats["new_faces"] += 1

        logger.debug(f"Created new track {person_id} at position {face_position}")
        return person_id

    def _update_existing_track(
        self,
        track_id: str,
        face_position: Dict[str, float],
        frame_number: int,
        face_size: float = 0.0,
        face_record: Optional[Dict] = None,
    ) -> None:
        """
        Update existing track with new face detection.

        Computes the instantaneous velocity from the previous position and frame,
        smooths it with an exponential moving average, and stores the embedding
        (keeping the first-seen one as the most stable reference).
        """
        track = self.active_tracks[track_id]

        prev_pos = track["position"]
        prev_frame = track["last_seen_frame"]
        cur_at = face_record.get("created_at") if face_record else None
        prev_at = track.get("last_seen_at")

        # Compute time-normalized velocity (px/ms) using timestamps when possible.
        dt_ms = self._elapsed_ms_between(
            prev_at, face_record, prev_frame, frame_number
        )
        if dt_ms > 0:
            inst_vx = (face_position["x"] - prev_pos["x"]) / dt_ms
            inst_vy = (face_position["y"] - prev_pos["y"]) / dt_ms
            alpha = self.velocity_smoothing_alpha
            cur_vx = alpha * inst_vx + (1 - alpha) * track["velocity"]["x"]
            cur_vy = alpha * inst_vy + (1 - alpha) * track["velocity"]["y"]
            track["velocity"] = {"x": cur_vx, "y": cur_vy}

        # Preserve the first-seen embedding as the track's stable identity.
        if not track.get("embedding") and face_record is not None:
            track["embedding"] = self._get_face_embedding(face_record)

        track["prev_position"] = prev_pos
        track["prev_frame"] = prev_frame
        track["position"] = face_position
        if face_size > 0.0:
            track["size"] = face_size
        track["last_seen_frame"] = frame_number
        if cur_at is not None:
            track["last_seen_at"] = cur_at
        track["frame_history"] += 1
        track["face_count"] += 1

        self.processing_stats["tracked_faces"] += 1

        logger.debug(f"Updated track {track_id} to position {face_position}")

    def _create_face_mapping(
        self,
        person_id: str,
        face_record: Dict,
        match_type: str,
        match_distance: float,
        frame_number: int,
        face_position: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Create face mapping record for database storage.
        """
        return {
            "person_id": person_id,
            "face_detection_id": face_record["id"],
            "match_type": match_type,  # 'tracked' or 'new_track'
            "match_distance": match_distance,
            "frame_number": frame_number,
            "position_x": face_position["x"],
            "position_y": face_position["y"],
        }

    def _calculate_person_average_position(
        self, face_mappings: List[Dict], person_id: str
    ) -> Dict[str, float]:
        """
        Calculate average position for a person from all their face mappings.
        """
        person_faces = [fm for fm in face_mappings if fm["person_id"] == person_id]

        if not person_faces:
            return {"x": 0.0, "y": 0.0}

        avg_x = sum(fm["position_x"] for fm in person_faces) / len(person_faces)
        avg_y = sum(fm["position_y"] for fm in person_faces) / len(person_faces)

        return {"x": avg_x, "y": avg_y}

    def _calculate_aggregate_quality(
        self, face_records: List[Dict]
    ) -> float:
        """
        Calculate aggregate quality score for person object from constituent faces.
        
        Uses weighted average of individual face qualities, weighted by detection confidence.
        This provides meaningful quality metrics instead of hardcoded defaults.
        
        Args:
            face_records: List of face detection records with quality metrics
            
        Returns:
            Aggregate quality score (0.0 to 1.0)
        """
        if not face_records:
            return 0.0
        
        total_weighted_quality = 0.0
        total_weight = 0.0
        
        for face in face_records:
            # Extract quality components from face record
            confidence = float(face.get('detection_confidence', face.get('confidence', 0.8)))
            sharpness = float(face.get('sharpness', 0.7))
            brightness = float(face.get('brightness', 0.7))
            
            # Calculate individual face quality (weighted combination)
            face_quality = (
                sharpness * 0.4 +      # 40% weight on sharpness
                brightness * 0.3 +     # 30% weight on brightness
                confidence * 0.3       # 30% weight on confidence
            )
            
            # Weight by confidence (more confident detections count more)
            weight = confidence
            total_weighted_quality += face_quality * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
            
        aggregate_quality = total_weighted_quality / total_weight
        return round(min(1.0, max(0.0, aggregate_quality)), 3)
    
    def _create_person_object(
        self, track_id: str, track_info: Dict, face_mappings: List[Dict], face_detections: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create person object from track data and face mappings with aggregate quality score.
        
        Args:
            track_id: Person track identifier
            track_info: Track information dictionary
            face_mappings: List of face-to-person mappings
            face_detections: Optional list of original face detection records for quality calculation
        """
        # Calculate average position
        avg_position = self._calculate_person_average_position(face_mappings, track_id)

        # Get all face IDs for this person
        person_faces = [fm for fm in face_mappings if fm["person_id"] == track_id]
        face_ids = [fm["face_detection_id"] for fm in person_faces]
        
        # Calculate aggregate quality score from face records
        quality_score = 0.0
        if face_detections:
            # Get face records for this person
            person_face_records = [
                face for face in face_detections 
                if face["id"] in face_ids
            ]
            quality_score = self._calculate_aggregate_quality(person_face_records)

        return {
            "person_id": track_id,
            "face_count": track_info["face_count"],
            "average_position": avg_position,
            "quality_score": quality_score,  # Real calculated quality instead of 0.0
            "tracking_algorithm": "percentage_based_tracking",
            "tolerance_percent": self.tolerance_percent,
            "original_face_ids": face_ids,
            "first_seen_frame": min(fm["frame_number"] for fm in person_faces),
            "last_seen_frame": track_info["last_seen_frame"],
        }

    async def group_by_orchestrator_person_id(
        self, face_detections: List[Dict]
    ) -> Dict[str, Any]:
        """
        Group faces using Orchestrator's existing person_id assignments.
        
        This preserves Orchestrator's IoU-based grouping instead of re-clustering.
        Used when face detections already have person_id from Orchestrator.
        
        Args:
            face_detections: List of face detection records with person_id field
            
        Returns:
            Dictionary containing:
            - person_objects: List of grouped person objects
            - face_mappings: List of face-to-person mappings  
            - statistics: Processing statistics
        """
        logger.info(
            f"Grouping {len(face_detections)} faces by Orchestrator person_id"
        )
        
        if not face_detections:
            return self._create_empty_result()
        
        # Group faces by person_id
        person_groups = {}
        face_mappings = []
        
        for face in face_detections:
            person_id = face.get("person_id", "unknown")
            
            if person_id not in person_groups:
                person_groups[person_id] = []
            
            person_groups[person_id].append(face)
            
            # Create face mapping
            face_mapping = {
                "person_id": person_id,
                "face_id": face.get("id"),
                "frame_number": face.get("frame_number", 0),
                "assignment_type": "orchestrator_grouped",
                "distance": 0.0,  # No distance calculation needed
                "position": self._extract_face_position(face),
            }
            face_mappings.append(face_mapping)
        
        # Create person objects from groups
        person_objects = []
        for person_id, group_faces in person_groups.items():
            person_obj = self._create_person_object(person_id, {
                "person_id": person_id,
                "positions": [self._extract_face_position(f) for f in group_faces],
                "frames": [f.get("frame_number", 0) for f in group_faces],
                "faces": group_faces,
            }, face_mappings, face_detections)
            person_objects.append(person_obj)
        
        statistics = {
            "total_faces": len(face_detections),
            "total_persons": len(person_objects),
            "tracked_faces": len(face_detections),
            "new_faces": 0,
            "frames_processed": len(set(f.get("frame_number", 0) for f in face_detections)),
            "tolerance_percent": 0.0,  # Not used
            "algorithm": "orchestrator_person_id_grouping",
            "grouping_efficiency": self._calculate_grouping_efficiency(
                face_detections, person_objects
            ),
        }
        
        logger.info(
            f"Orchestrator grouping complete: {statistics['total_faces']} faces → {statistics['total_persons']} persons"
        )
        
        return {
            "person_objects": person_objects,
            "face_mappings": face_mappings,
            "statistics": statistics,
        }

    async def apply_percentage_based_tracking(
        self, face_detections: List[Dict], tolerance_percent: float = 20.0
    ) -> Dict[str, Any]:
        """
        Apply the same percentage-based tracking algorithm as PPL Meta Mini.

        This is the core algorithm that processes face detections chronologically
        and groups them into person objects using position-based tolerance matching.

        Args:
            face_detections: List of face detection records from database
            tolerance_percent: Position matching tolerance percentage (default 20%)

        Returns:
            Dictionary containing:
            - person_objects: List of grouped person objects
            - face_mappings: List of face-to-person mappings
            - statistics: Processing statistics and metrics
        """
        logger.info(
            f"Starting face grouping for {len(face_detections)} faces with {tolerance_percent}% tolerance"
        )

        # Set tolerance and reset state
        self.tolerance_percent = tolerance_percent
        self._reset_processing_state()

        if not face_detections:
            logger.warning("No face detections provided for grouping")
            return self._create_empty_result()

        # Group face detections by frame number for chronological processing
        frames_with_faces = {}
        for face in face_detections:
            frame_num = face.get("frame_number", 0)
            if frame_num not in frames_with_faces:
                frames_with_faces[frame_num] = []
            frames_with_faces[frame_num].append(face)

        # Sort frames chronologically (critical for tracking)
        sorted_frames = sorted(frames_with_faces.keys())
        logger.info(f"Processing {len(sorted_frames)} frames chronologically")

        # Storage for results
        face_mappings = []

        # Process each frame chronologically
        for frame_number in sorted_frames:
            frame_faces = frames_with_faces[frame_number]
            logger.debug(
                f"Processing frame {frame_number} with {len(frame_faces)} faces"
            )

            for face in frame_faces:
                # Extract face position and size (for size-proportional tolerance)
                face_position = self._extract_face_position(face)
                face_size = self._extract_bbox_size(face)

                # Find best matching active track (three-tier cascade)
                best_match, best_distance = self._find_best_track_match(
                    face_position, face_size, face, frame_number
                )

                if best_match is not None:
                    # Update existing track
                    self._update_existing_track(
                        best_match, face_position, frame_number, face_size, face
                    )

                    # Record face mapping as tracked
                    face_mapping = self._create_face_mapping(
                        best_match,
                        face,
                        "tracked",
                        best_distance,
                        frame_number,
                        face_position,
                    )
                    face_mappings.append(face_mapping)

                else:
                    # Create new track for unmatched face
                    person_id = self._create_new_track(
                        face, face_position, frame_number, face_size
                    )

                    # Record face mapping as new track
                    face_mapping = self._create_face_mapping(
                        person_id, face, "new_track", 0.0, frame_number, face_position
                    )
                    face_mappings.append(face_mapping)

            # Update frames processed
            self.processing_stats["frames_processed"] += 1

        # Create person objects from final tracks with quality calculation
        person_objects = []
        for track_id, track_info in self.active_tracks.items():
            person_obj = self._create_person_object(track_id, track_info, face_mappings, face_detections)
            person_objects.append(person_obj)

        # Create final statistics
        statistics = {
            "total_faces": len(face_detections),
            "total_persons": len(person_objects),
            "tracked_faces": self.processing_stats["tracked_faces"],
            "new_faces": self.processing_stats["new_faces"],
            "frames_processed": self.processing_stats["frames_processed"],
            "tolerance_percent": tolerance_percent,
            "algorithm": "percentage_based_tracking",
            "grouping_efficiency": self._calculate_grouping_efficiency(
                face_detections, person_objects
            ),
            "tier1_position_matched": self.processing_stats["tier1_position_matched"],
            "tier2_velocity_rejected": self.processing_stats["tier2_velocity_rejected"],
            "tier3_embedding_rejected": self.processing_stats[
                "tier3_embedding_rejected"
            ],
            "discrimination": {
                "use_size_based_tolerance": self.use_size_based_tolerance,
                "size_tolerance_factor": self.size_tolerance_factor,
                "velocity_activation_threshold": self.velocity_activation_threshold,
                "embedding_gate_enabled": self.embedding_gate_enabled,
            },
        }

        logger.info(
            f"Face grouping complete: {statistics['total_faces']} faces → {statistics['total_persons']} persons"
        )
        logger.info(
            f"Efficiency: {statistics['grouping_efficiency']:.1f}% (tracked: {statistics['tracked_faces']}, new: {statistics['new_faces']})"
        )

        return {
            "person_objects": person_objects,
            "face_mappings": face_mappings,
            "statistics": statistics,
        }

    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result for edge cases."""
        return {
            "person_objects": [],
            "face_mappings": [],
            "statistics": {
                "total_faces": 0,
                "total_persons": 0,
                "tracked_faces": 0,
                "new_faces": 0,
                "frames_processed": 0,
                "tolerance_percent": self.tolerance_percent,
                "algorithm": "percentage_based_tracking",
                "grouping_efficiency": 0.0,
                "tier1_position_matched": 0,
                "tier2_velocity_rejected": 0,
                "tier3_embedding_rejected": 0,
                "discrimination": {
                    "use_size_based_tolerance": self.use_size_based_tolerance,
                    "size_tolerance_factor": self.size_tolerance_factor,
                    "velocity_activation_threshold": self.velocity_activation_threshold,
                    "embedding_gate_enabled": self.embedding_gate_enabled,
                },
            },
        }

    def _calculate_grouping_efficiency(
        self, face_detections: List[Dict], person_objects: List[Dict]
    ) -> float:
        """
        Calculate grouping efficiency as percentage of faces that were successfully grouped.
        """
        if not face_detections:
            return 0.0

        total_faces = len(face_detections)
        total_persons = len(person_objects)

        if total_persons == 0:
            return 0.0

        # Efficiency = (faces_grouped / total_faces) * 100
        # Higher efficiency means more faces per person (better grouping)
        efficiency = ((total_faces - total_persons) / total_faces) * 100
        return max(0.0, min(100.0, efficiency))

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get detailed processing statistics from the last grouping operation.
        """
        return {
            "processing_stats": self.processing_stats.copy(),
            "active_tracks_count": len(self.active_tracks),
            "tolerance_percent": self.tolerance_percent,
            "quality_weights": self.quality_weights.copy(),
            "discrimination": {
                "use_size_based_tolerance": self.use_size_based_tolerance,
                "size_tolerance_factor": self.size_tolerance_factor,
                "velocity_activation_threshold": self.velocity_activation_threshold,
                "velocity_smoothing_alpha": self.velocity_smoothing_alpha,
                "min_frames_for_velocity": self.min_frames_for_velocity,
                "velocity_inconsistency_factor": self.velocity_inconsistency_factor,
                "embedding_gate_enabled": self.embedding_gate_enabled,
                "embedding_similarity_threshold": self.embedding_similarity_threshold,
            },
        }

    def validate_face_detections(self, face_detections: List[Dict]) -> List[str]:
        """
        Validate face detection data for required fields.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not face_detections:
            errors.append("No face detections provided")
            return errors

        required_fields = ["id", "frame_number"]
        position_fields = [["position_x", "position_y"], ["bbox_x1", "bbox_y1"]]

        for i, face in enumerate(face_detections):
            # Check required fields
            for field in required_fields:
                if field not in face:
                    errors.append(f"Face {i}: Missing required field '{field}'")

            # Check position fields (at least one set must be present)
            has_position = any(
                all(field in face for field in field_set)
                for field_set in position_fields
            )

            if not has_position:
                errors.append(
                    f"Face {i}: Missing position data (need position_x/y or bbox_x1/y1)"
                )

        return errors

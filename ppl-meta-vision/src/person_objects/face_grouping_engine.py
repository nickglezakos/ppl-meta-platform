"""
PPL Meta Vision Service - Face Grouping Engine
Independent implementation of the face grouping algorithm for PPL Thread workflow.

This module implements the same percentage-based tolerance matching algorithm
as PPL Meta Mini's FaceGroupingEngine, but as a completely separate
implementation to maintain mini's autonomy.

Key Features:
- Percentage-based tolerance matching (20% default)
- Chronological frame processing
- Quality-weighted face grouping
- Identical algorithm logic to PPL Meta Mini
- Independent implementation with zero dependencies
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VisionFaceGroupingEngine:
    """
    Independent face grouping engine for PPL Meta Vision Service.

    Implements the same percentage-based tolerance matching algorithm
    as PPL Meta Mini's FaceGroupingEngine, but as a completely separate
    implementation to maintain mini's autonomy.
    """

    def __init__(self):
        """Initialize the face grouping engine with PPL Mini default settings."""
        self.tolerance_percent = 20.0
        self.quality_weights = {
            "sharpness": 0.4,
            "exposure": 0.3,
            "contrast": 0.2,
            "noise": 0.1,
        }

        # Tracking state (reset per session)
        self.active_tracks = {}
        self.next_person_id = 1
        self.processing_stats = {
            "tracked_faces": 0,
            "new_faces": 0,
            "merge_operations": 0,
            "frames_processed": 0,
        }

    def calculate_position_distance(self, pos1: Dict, pos2: Dict) -> Dict[str, float]:
        """
        Calculate position-based distance with percentage tolerance matching.

        This replicates the exact same algorithm used in PPL Meta Mini's
        FaceGroupingEngine for consistency across implementations.

        Args:
            pos1: First position dict with 'x' and 'y' keys
            pos2: Second position dict with 'x' and 'y' keys

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

        # Calculate percentage-based tolerances (same as PPL Meta Mini)
        x_tolerance = x1 * (self.tolerance_percent / 100.0)
        y_tolerance = y1 * (self.tolerance_percent / 100.0)

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
        }

    def _reset_processing_state(self):
        """Reset processing state for new session."""
        self.active_tracks = {}
        self.next_person_id = 1
        self.processing_stats = {
            "tracked_faces": 0,
            "new_faces": 0,
            "merge_operations": 0,
            "frames_processed": 0,
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

    def _find_best_track_match(
        self, face_position: Dict[str, float]
    ) -> Tuple[Optional[str], float]:
        """
        Find the best matching active track for a face position.

        Returns:
            Tuple of (track_id, distance) or (None, inf) if no match
        """
        best_match = None
        best_distance = float("inf")

        for track_id, track_info in self.active_tracks.items():
            track_position = track_info["position"]

            distance_data = self.calculate_position_distance(
                face_position, track_position
            )

            # Check if within tolerance and better than current best
            if (
                distance_data["within_tolerance"]
                and distance_data["combined_distance"] < best_distance
            ):
                best_match = track_id
                best_distance = distance_data["combined_distance"]

        return best_match, best_distance

    def _create_new_track(
        self, face_record: Dict, face_position: Dict[str, float], frame_number: int
    ) -> str:
        """
        Create a new person track for unmatched face.

        Returns:
            New person track ID
        """
        person_id = f"person_{self.next_person_id}"
        self.next_person_id += 1

        self.active_tracks[person_id] = {
            "person_id": person_id,
            "position": face_position,
            "last_seen_frame": frame_number,
            "face_count": 1,
            "first_face_id": face_record["id"],
            "created_at": datetime.now(),
        }

        self.processing_stats["new_faces"] += 1

        logger.debug(f"Created new track {person_id} at position {face_position}")
        return person_id

    def _update_existing_track(
        self, track_id: str, face_position: Dict[str, float], frame_number: int
    ):
        """
        Update existing track with new face detection.
        """
        self.active_tracks[track_id]["position"] = face_position
        self.active_tracks[track_id]["last_seen_frame"] = frame_number
        self.active_tracks[track_id]["face_count"] += 1

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
                # Extract face position
                face_position = self._extract_face_position(face)

                # Find best matching active track
                best_match, best_distance = self._find_best_track_match(face_position)

                if best_match is not None:
                    # Update existing track
                    self._update_existing_track(best_match, face_position, frame_number)

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
                        face, face_position, frame_number
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

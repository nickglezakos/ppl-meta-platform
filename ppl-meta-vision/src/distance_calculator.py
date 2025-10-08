"""
PPL Meta Vision Service - Distance Calculator
Implements autonomous system methodology for calculating distance from camera based on face size.

This module provides distance calculation functionality for person objects
based on the bounding box size of detected faces, following the autonomous
system methodology documented in the PPL Meta platform.
"""

import logging
import math
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class DistanceCalculator:
    """
    Calculate distance from camera using face bounding box dimensions.

    Uses the autonomous system methodology:
    - Larger faces = closer to camera
    - Smaller faces = farther from camera
    - Distance inversely proportional to face area
    """

    def __init__(
        self, baseline_distance: float = 100.0, baseline_face_size: float = 10000.0
    ):
        """
        Initialize distance calculator with baseline parameters.

        Args:
            baseline_distance: Reference distance in arbitrary units (default: 100.0)
            baseline_face_size: Reference face area in pixels (default: 10000.0)
        """
        self.baseline_distance = baseline_distance
        self.baseline_face_size = baseline_face_size
        logger.info(
            f"Initialized DistanceCalculator with baseline distance={baseline_distance}, face_size={baseline_face_size}"
        )

    def calculate_distance_from_bbox(self, bbox: List[float]) -> float:
        """
        Calculate distance from camera based on face bounding box.

        Args:
            bbox: Face bounding box [x1, y1, x2, y2]

        Returns:
            Estimated distance from camera (arbitrary units)
        """
        try:
            # Calculate face dimensions
            face_width = abs(bbox[2] - bbox[0])
            face_height = abs(bbox[3] - bbox[1])
            face_area = face_width * face_height

            # Prevent division by zero
            if face_area <= 0:
                logger.warning(
                    f"Invalid face area: {face_area}, using default distance"
                )
                return self.baseline_distance * 2.0

            # Distance inversely proportional to face area
            # Larger face = closer to camera = smaller distance value
            distance = (self.baseline_face_size / face_area) * self.baseline_distance

            # Round to 2 decimal places for consistency
            distance = round(distance, 2)

            logger.debug(f"Face area: {face_area}, calculated distance: {distance}")
            return distance

        except Exception as e:
            logger.error(f"Error calculating distance from bbox {bbox}: {e}")
            return self.baseline_distance

    def calculate_distance_for_face_detection(self, face_detection: Dict) -> float:
        """
        Calculate distance for a face detection dictionary.

        Args:
            face_detection: Face detection with bbox coordinates

        Returns:
            Calculated distance from camera
        """
        try:
            # Extract bbox from face detection
            if "bbox" in face_detection:
                bbox = face_detection["bbox"]
            elif all(
                key in face_detection
                for key in ["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]
            ):
                bbox = [
                    face_detection["bbox_x1"],
                    face_detection["bbox_y1"],
                    face_detection["bbox_x2"],
                    face_detection["bbox_y2"],
                ]
            else:
                logger.warning(
                    f"No valid bbox found in face detection: {list(face_detection.keys())}"
                )
                return self.baseline_distance

            return self.calculate_distance_from_bbox(bbox)

        except Exception as e:
            logger.error(f"Error calculating distance for face detection: {e}")
            return self.baseline_distance

    def calculate_center_coordinates(self, bbox: List[float]) -> Tuple[float, float]:
        """
        Calculate center coordinates from bounding box.

        Args:
            bbox: Face bounding box [x1, y1, x2, y2]

        Returns:
            Tuple of (center_x, center_y) coordinates
        """
        try:
            center_x = (bbox[0] + bbox[2]) / 2.0
            center_y = (bbox[1] + bbox[3]) / 2.0
            return round(center_x, 2), round(center_y, 2)
        except Exception as e:
            logger.error(f"Error calculating center coordinates from bbox {bbox}: {e}")
            return 0.0, 0.0

    def calculate_movement_velocity(
        self,
        prev_center: Tuple[float, float],
        curr_center: Tuple[float, float],
        time_diff_ms: float,
    ) -> float:
        """
        Calculate movement velocity between two positions.

        Args:
            prev_center: Previous (x, y) position
            curr_center: Current (x, y) position
            time_diff_ms: Time difference in milliseconds

        Returns:
            Movement velocity in pixels per second
        """
        try:
            if time_diff_ms <= 0:
                return 0.0

            # Calculate Euclidean distance
            dx = curr_center[0] - prev_center[0]
            dy = curr_center[1] - prev_center[1]
            pixel_distance = math.sqrt(dx * dx + dy * dy)

            # Convert to velocity (pixels per second)
            time_diff_sec = time_diff_ms / 1000.0
            velocity = pixel_distance / time_diff_sec

            return round(velocity, 2)

        except Exception as e:
            logger.error(f"Error calculating movement velocity: {e}")
            return 0.0

    def enhance_face_detection_with_distance(self, face_detection: Dict) -> Dict:
        """
        Enhance face detection with distance and spatial data.

        Args:
            face_detection: Original face detection data

        Returns:
            Enhanced face detection with distance and center coordinates
        """
        try:
            enhanced = face_detection.copy()

            # Calculate distance
            distance = self.calculate_distance_for_face_detection(face_detection)
            enhanced["distance_from_camera"] = distance

            # Calculate center coordinates
            bbox = enhanced.get("bbox") or [
                enhanced.get("bbox_x1", 0),
                enhanced.get("bbox_y1", 0),
                enhanced.get("bbox_x2", 0),
                enhanced.get("bbox_y2", 0),
            ]

            center_x, center_y = self.calculate_center_coordinates(bbox)
            enhanced["center_x"] = center_x
            enhanced["center_y"] = center_y

            # Add face dimensions
            enhanced["face_width"] = abs(bbox[2] - bbox[0])
            enhanced["face_height"] = abs(bbox[3] - bbox[1])
            enhanced["face_area"] = enhanced["face_width"] * enhanced["face_height"]

            return enhanced

        except Exception as e:
            logger.error(f"Error enhancing face detection with distance: {e}")
            return face_detection


# Global distance calculator instance
distance_calculator = DistanceCalculator()


def calculate_distance_from_bbox(bbox: List[float]) -> float:
    """
    Convenience function for calculating distance from bounding box.

    Args:
        bbox: Face bounding box [x1, y1, x2, y2]

    Returns:
        Estimated distance from camera
    """
    return distance_calculator.calculate_distance_from_bbox(bbox)


def enhance_face_detections_with_distance(face_detections: List[Dict]) -> List[Dict]:
    """
    Enhance multiple face detections with distance calculations.

    Args:
        face_detections: List of face detection dictionaries

    Returns:
        List of enhanced face detections with distance data
    """
    enhanced_detections = []

    for detection in face_detections:
        enhanced = distance_calculator.enhance_face_detection_with_distance(detection)
        enhanced_detections.append(enhanced)

    logger.info(
        f"Enhanced {len(face_detections)} face detections with distance calculations"
    )
    return enhanced_detections

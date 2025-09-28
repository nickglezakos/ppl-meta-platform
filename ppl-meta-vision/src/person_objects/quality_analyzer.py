"""
PPL Meta Vision Service - Person Quality Analyzer
Independent implementation of the quality analysis system for PPL Thread workflow.

This module implements face quality assessment and best face selection
for person objects, supporting the face grouping engine with quality-based
ranking and filtering capabilities.

Key Features:
- Multi-factor quality scoring
- Best face selection per person
- Age detection integration
- Independent implementation with zero dependencies on PPL Mini
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PersonQualityAnalyzer:
    """
    Independent quality analyzer for PPL Meta Vision Service.

    Provides quality assessment and best face selection for person objects
    to support the face grouping engine with quality-based operations.
    """

    def __init__(self):
        """Initialize the quality analyzer with default scoring weights."""
        self.quality_weights = {
            "sharpness": 0.35,
            "exposure": 0.25,
            "contrast": 0.20,
            "noise": 0.10,
            "size": 0.10,
        }

        # Quality thresholds for filtering
        self.quality_thresholds = {
            "minimum_score": 0.3,
            "good_quality": 0.6,
            "excellent_quality": 0.8,
        }

        # Face size preferences
        self.size_preferences = {
            "minimum_width": 50,
            "minimum_height": 50,
            "optimal_width": 200,
            "optimal_height": 200,
        }

    def calculate_quality_score(
        self, face_record: Dict, image_dimensions: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive quality score for a face detection.

        Args:
            face_record: Face detection record with quality metrics
            image_dimensions: Optional image dimensions for size scoring

        Returns:
            Dictionary containing:
            - overall_score: Combined quality score (0-1)
            - component_scores: Individual metric scores
            - quality_category: Text description of quality level
            - recommendations: List of quality improvement suggestions
        """
        component_scores = {}

        # Sharpness assessment
        component_scores["sharpness"] = self._calculate_sharpness_score(face_record)

        # Exposure assessment
        component_scores["exposure"] = self._calculate_exposure_score(face_record)

        # Contrast assessment
        component_scores["contrast"] = self._calculate_contrast_score(face_record)

        # Noise assessment
        component_scores["noise"] = self._calculate_noise_score(face_record)

        # Size assessment
        component_scores["size"] = self._calculate_size_score(
            face_record, image_dimensions
        )

        # Calculate weighted overall score
        overall_score = sum(
            component_scores[metric] * weight
            for metric, weight in self.quality_weights.items()
        )

        # Determine quality category
        quality_category = self._determine_quality_category(overall_score)

        # Generate recommendations
        recommendations = self._generate_quality_recommendations(
            component_scores, overall_score
        )

        return {
            "overall_score": overall_score,
            "component_scores": component_scores,
            "quality_category": quality_category,
            "recommendations": recommendations,
            "weights_used": self.quality_weights.copy(),
        }

    def _calculate_sharpness_score(self, face_record: Dict) -> float:
        """
        Calculate sharpness score from face detection data.

        Uses confidence and blur metrics if available.
        """
        # Try detection confidence first
        if "detection_confidence" in face_record:
            confidence = float(face_record["detection_confidence"])
            # Convert confidence to sharpness proxy
            return min(1.0, max(0.0, confidence))

        # Try explicit sharpness metric
        if "sharpness" in face_record:
            sharpness = float(face_record["sharpness"])
            return min(1.0, max(0.0, sharpness))

        # Try blur metric (inverted)
        if "blur_score" in face_record:
            blur = float(face_record["blur_score"])
            return min(1.0, max(0.0, 1.0 - blur))

        # Default moderate sharpness
        return 0.5

    def _calculate_exposure_score(self, face_record: Dict) -> float:
        """
        Calculate exposure score from face detection data.

        Uses brightness and exposure metrics if available.
        """
        # Try explicit exposure metric
        if "exposure_score" in face_record:
            exposure = float(face_record["exposure_score"])
            return min(1.0, max(0.0, exposure))

        # Try brightness as exposure proxy
        if "brightness" in face_record:
            brightness = float(face_record["brightness"])
            # Normalize brightness (assuming 0-255 range)
            normalized = brightness / 255.0
            # Optimal exposure around 0.4-0.7 range
            if 0.4 <= normalized <= 0.7:
                return 1.0
            elif normalized < 0.4:
                # Under-exposed
                return normalized / 0.4
            else:
                # Over-exposed
                return (1.0 - normalized) / 0.3

        # Default moderate exposure
        return 0.6

    def _calculate_contrast_score(self, face_record: Dict) -> float:
        """
        Calculate contrast score from face detection data.

        Uses contrast metrics if available.
        """
        # Try explicit contrast metric
        if "contrast_score" in face_record:
            contrast = float(face_record["contrast_score"])
            return min(1.0, max(0.0, contrast))

        # Try standard deviation as contrast proxy
        if "pixel_std" in face_record:
            std_dev = float(face_record["pixel_std"])
            # Normalize standard deviation (good contrast ~30-80)
            normalized = min(80.0, max(0.0, std_dev)) / 80.0
            return normalized

        # Default moderate contrast
        return 0.5

    def _calculate_noise_score(self, face_record: Dict) -> float:
        """
        Calculate noise score from face detection data.

        Uses noise metrics if available (higher score = less noise).
        """
        # Try explicit noise metric (assuming lower is better)
        if "noise_level" in face_record:
            noise = float(face_record["noise_level"])
            # Invert noise level (higher noise = lower score)
            return min(1.0, max(0.0, 1.0 - noise))

        # Try image quality as noise proxy
        if "image_quality" in face_record:
            quality = float(face_record["image_quality"])
            return min(1.0, max(0.0, quality))

        # Default low noise assumption
        return 0.7

    def _calculate_size_score(
        self, face_record: Dict, image_dimensions: Optional[Dict] = None
    ) -> float:
        """
        Calculate size score based on face dimensions.

        Prefers larger faces within reasonable limits.
        """
        # Extract face dimensions
        width = self._extract_face_width(face_record)
        height = self._extract_face_height(face_record)

        if width <= 0 or height <= 0:
            return 0.0

        # Calculate size score based on optimal dimensions
        width_score = min(1.0, width / self.size_preferences["optimal_width"])
        height_score = min(1.0, height / self.size_preferences["optimal_height"])

        # Penalty for too small faces
        if width < self.size_preferences["minimum_width"]:
            width_score *= 0.3
        if height < self.size_preferences["minimum_height"]:
            height_score *= 0.3

        # Combined size score
        size_score = (width_score + height_score) / 2.0

        # Relative size bonus if image dimensions available
        if image_dimensions:
            img_width = image_dimensions.get("width", 1)
            img_height = image_dimensions.get("height", 1)

            if img_width > 0 and img_height > 0:
                # Face area relative to image
                face_area = width * height
                image_area = img_width * img_height
                relative_size = face_area / image_area

                # Bonus for faces that are 5-25% of image area
                if 0.05 <= relative_size <= 0.25:
                    size_score *= 1.2
                elif relative_size > 0.25:
                    size_score *= 0.8

        return min(1.0, size_score)

    def _extract_face_width(self, face_record: Dict) -> float:
        """Extract face width from detection record."""
        if "width" in face_record:
            return float(face_record["width"])

        if "bbox_x2" in face_record and "bbox_x1" in face_record:
            return float(face_record["bbox_x2"] - face_record["bbox_x1"])

        return 0.0

    def _extract_face_height(self, face_record: Dict) -> float:
        """Extract face height from detection record."""
        if "height" in face_record:
            return float(face_record["height"])

        if "bbox_y2" in face_record and "bbox_y1" in face_record:
            return float(face_record["bbox_y2"] - face_record["bbox_y1"])

        return 0.0

    def _determine_quality_category(self, overall_score: float) -> str:
        """
        Determine quality category from overall score.
        """
        if overall_score >= self.quality_thresholds["excellent_quality"]:
            return "excellent"
        elif overall_score >= self.quality_thresholds["good_quality"]:
            return "good"
        elif overall_score >= self.quality_thresholds["minimum_score"]:
            return "acceptable"
        else:
            return "poor"

    def _generate_quality_recommendations(
        self, component_scores: Dict[str, float], overall_score: float
    ) -> List[str]:
        """
        Generate quality improvement recommendations.
        """
        recommendations = []

        # Check individual components for issues
        for metric, score in component_scores.items():
            if score < 0.4:
                if metric == "sharpness":
                    recommendations.append("Improve camera focus or reduce motion blur")
                elif metric == "exposure":
                    recommendations.append("Adjust lighting conditions")
                elif metric == "contrast":
                    recommendations.append("Improve lighting contrast")
                elif metric == "noise":
                    recommendations.append("Reduce image noise or improve lighting")
                elif metric == "size":
                    recommendations.append(
                        "Move closer to subject or use higher resolution"
                    )

        # Overall recommendations
        if overall_score < self.quality_thresholds["minimum_score"]:
            recommendations.append("Consider retaking photo under better conditions")
        elif overall_score < self.quality_thresholds["good_quality"]:
            recommendations.append("Photo quality is acceptable but could be improved")

        return recommendations

    def select_best_face_per_person(
        self,
        person_objects: List[Dict],
        face_detections: List[Dict],
        face_mappings: List[Dict],
    ) -> Dict[str, Any]:
        """
        Select the best face for each person based on quality scores.

        Args:
            person_objects: List of person objects from grouping
            face_detections: List of all face detections
            face_mappings: List of face-to-person mappings

        Returns:
            Dictionary containing:
            - best_faces: Dict mapping person_id to best face record
            - quality_rankings: Dict mapping person_id to ranked face list
            - selection_statistics: Statistics about the selection process
        """
        logger.info("Selecting best faces for %d persons", len(person_objects))

        # Create face lookup for efficient access
        face_lookup = {face["id"]: face for face in face_detections}

        # Group faces by person
        person_faces = {}
        for mapping in face_mappings:
            person_id = mapping["person_id"]
            face_id = mapping["face_detection_id"]

            if person_id not in person_faces:
                person_faces[person_id] = []

            if face_id in face_lookup:
                person_faces[person_id].append(face_lookup[face_id])

        best_faces = {}
        quality_rankings = {}
        stats = {
            "persons_processed": 0,
            "total_faces_analyzed": 0,
            "average_quality_score": 0.0,
            "quality_distribution": {
                "excellent": 0,
                "good": 0,
                "acceptable": 0,
                "poor": 0,
            },
        }

        total_quality_sum = 0.0

        # Process each person
        for person_obj in person_objects:
            person_id = person_obj["person_id"]

            if person_id not in person_faces:
                logger.warning("No faces found for person %s", person_id)
                continue

            faces = person_faces[person_id]

            # Calculate quality scores for all faces
            face_quality_data = []
            for face in faces:
                quality_result = self.calculate_quality_score(face)
                face_quality_data.append(
                    {
                        "face": face,
                        "quality_score": quality_result["overall_score"],
                        "quality_category": quality_result["quality_category"],
                        "component_scores": quality_result["component_scores"],
                    }
                )

                # Update statistics
                total_quality_sum += quality_result["overall_score"]
                stats["quality_distribution"][quality_result["quality_category"]] += 1
                stats["total_faces_analyzed"] += 1

            # Sort by quality score (best first)
            face_quality_data.sort(key=lambda x: x["quality_score"], reverse=True)

            # Select best face
            best_face_data = face_quality_data[0]
            best_faces[person_id] = {
                "face_record": best_face_data["face"],
                "quality_score": best_face_data["quality_score"],
                "quality_category": best_face_data["quality_category"],
                "component_scores": best_face_data["component_scores"],
                "rank": 1,
                "total_faces_for_person": len(faces),
            }

            # Store full quality rankings
            quality_rankings[person_id] = [
                {
                    "face_id": fqd["face"]["id"],
                    "quality_score": fqd["quality_score"],
                    "quality_category": fqd["quality_category"],
                    "rank": i + 1,
                }
                for i, fqd in enumerate(face_quality_data)
            ]

            stats["persons_processed"] += 1

        # Calculate average quality
        if stats["total_faces_analyzed"] > 0:
            stats["average_quality_score"] = (
                total_quality_sum / stats["total_faces_analyzed"]
            )

        logger.info(
            "Best face selection complete: %d persons processed",
            stats["persons_processed"],
        )

        return {
            "best_faces": best_faces,
            "quality_rankings": quality_rankings,
            "selection_statistics": stats,
        }

    def filter_faces_by_quality(
        self, face_detections: List[Dict], minimum_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Filter faces based on quality thresholds.

        Args:
            face_detections: List of face detection records
            minimum_score: Custom minimum quality score (uses default if None)

        Returns:
            Dictionary containing:
            - passed_faces: List of faces that passed quality filter
            - failed_faces: List of faces that failed quality filter
            - filter_statistics: Statistics about filtering results
        """
        if minimum_score is None:
            minimum_score = self.quality_thresholds["minimum_score"]

        logger.info(
            "Filtering %d faces with minimum score %.2f",
            len(face_detections),
            minimum_score,
        )

        passed_faces = []
        failed_faces = []

        stats = {
            "total_faces": len(face_detections),
            "passed_count": 0,
            "failed_count": 0,
            "pass_rate": 0.0,
            "average_passed_score": 0.0,
            "average_failed_score": 0.0,
            "minimum_score_used": minimum_score,
        }

        passed_scores_sum = 0.0
        failed_scores_sum = 0.0

        for face in face_detections:
            quality_result = self.calculate_quality_score(face)
            quality_score = quality_result["overall_score"]

            face_with_quality = {**face, "quality_analysis": quality_result}

            if quality_score >= minimum_score:
                passed_faces.append(face_with_quality)
                passed_scores_sum += quality_score
                stats["passed_count"] += 1
            else:
                failed_faces.append(face_with_quality)
                failed_scores_sum += quality_score
                stats["failed_count"] += 1

        # Calculate averages
        if stats["passed_count"] > 0:
            stats["average_passed_score"] = passed_scores_sum / stats["passed_count"]

        if stats["failed_count"] > 0:
            stats["average_failed_score"] = failed_scores_sum / stats["failed_count"]

        if stats["total_faces"] > 0:
            stats["pass_rate"] = (stats["passed_count"] / stats["total_faces"]) * 100

        logger.info(
            "Quality filtering complete: %d passed, %d failed (%.1f%% pass rate)",
            stats["passed_count"],
            stats["failed_count"],
            stats["pass_rate"],
        )

        return {
            "passed_faces": passed_faces,
            "failed_faces": failed_faces,
            "filter_statistics": stats,
        }

    def get_quality_distribution_analysis(
        self, face_detections: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze quality distribution across all face detections.

        Returns comprehensive statistics about quality patterns.
        """
        logger.info("Analyzing quality distribution for %d faces", len(face_detections))

        quality_scores = []
        quality_categories = {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0}
        component_sums = {metric: 0.0 for metric in self.quality_weights.keys()}

        for face in face_detections:
            quality_result = self.calculate_quality_score(face)

            quality_scores.append(quality_result["overall_score"])
            quality_categories[quality_result["quality_category"]] += 1

            for metric, score in quality_result["component_scores"].items():
                component_sums[metric] += score

        # Calculate statistics
        total_faces = len(face_detections)

        if total_faces == 0:
            return self._create_empty_distribution_analysis()

        # Basic statistics
        avg_score = sum(quality_scores) / total_faces
        min_score = min(quality_scores)
        max_score = max(quality_scores)

        # Component averages
        component_averages = {
            metric: component_sums[metric] / total_faces
            for metric in component_sums.keys()
        }

        # Quality category percentages
        category_percentages = {
            category: (count / total_faces) * 100
            for category, count in quality_categories.items()
        }

        return {
            "total_faces": total_faces,
            "quality_statistics": {
                "average_score": avg_score,
                "minimum_score": min_score,
                "maximum_score": max_score,
                "score_range": max_score - min_score,
            },
            "component_averages": component_averages,
            "quality_categories": quality_categories,
            "category_percentages": category_percentages,
            "thresholds_used": self.quality_thresholds.copy(),
            "weights_used": self.quality_weights.copy(),
        }

    def _create_empty_distribution_analysis(self) -> Dict[str, Any]:
        """Create empty distribution analysis for edge cases."""
        return {
            "total_faces": 0,
            "quality_statistics": {
                "average_score": 0.0,
                "minimum_score": 0.0,
                "maximum_score": 0.0,
                "score_range": 0.0,
            },
            "component_averages": {
                metric: 0.0 for metric in self.quality_weights.keys()
            },
            "quality_categories": {
                "excellent": 0,
                "good": 0,
                "acceptable": 0,
                "poor": 0,
            },
            "category_percentages": {
                "excellent": 0.0,
                "good": 0.0,
                "acceptable": 0.0,
                "poor": 0.0,
            },
            "thresholds_used": self.quality_thresholds.copy(),
            "weights_used": self.quality_weights.copy(),
        }

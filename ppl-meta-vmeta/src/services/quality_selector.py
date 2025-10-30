"""
Quality Selection Algorithms
PPL Meta Platform - vmeta Service

Provides quality-based selection algorithms for person objects and faces
in cross-video individual tracking. Uses weighted quality metrics to
determine best quality frames for display and analysis.

Quality Algorithm:
- Sharpness: 40% weight
- Brightness: 30% weight  
- Confidence: 30% weight

Created: October 28, 2025
Author: PPL Meta Platform Team
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def select_best_quality_object(
    person_objects: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Select person object with highest quality score.
    
    Analyzes all person objects and returns the one with the best overall
    quality based on a weighted combination of sharpness, brightness, and
    confidence metrics.
    
    Quality Score Calculation:
        score = (sharpness × 0.4) + (brightness × 0.3) + (confidence × 0.3)
        
    Args:
        person_objects: List of person object dictionaries from Orchestrator
        
    Returns:
        Person object dictionary with highest quality score
        Returns None if input list is empty
        
    Example:
        >>> person_objects = [
        ...     {"quality_metrics": {"average_sharpness": 0.8, ...}},
        ...     {"quality_metrics": {"average_sharpness": 0.9, ...}}
        ... ]
        >>> best = select_best_quality_object(person_objects)
        >>> print(f"Best quality score: {calculate_quality_score(best)}")
    """
    if not person_objects:
        logger.warning("No person objects provided for quality selection")
        return None
    
    scored_objects = []
    for obj in person_objects:
        score = calculate_quality_score(obj)
        scored_objects.append((score, obj))
        logger.debug(
            f"Person object {obj.get('person_uuid', 'unknown')}: "
            f"quality_score={score:.3f}"
        )
    
    # Sort by score descending
    scored_objects.sort(key=lambda x: x[0], reverse=True)
    
    best_score, best_object = scored_objects[0]
    logger.info(
        f"Selected best quality person object: "
        f"uuid={best_object.get('person_uuid', 'unknown')}, "
        f"score={best_score:.3f}"
    )
    
    return best_object


def calculate_quality_score(person_object: Dict[str, Any]) -> float:
    """
    Calculate overall quality score for a person object.
    
    Uses weighted average of sharpness (40%), brightness (30%),
    and confidence (30%) from quality_metrics.
    
    Args:
        person_object: Person object dictionary with quality_metrics
        
    Returns:
        Quality score between 0.0 and 1.0
        Defaults to 0.5 for missing metrics
        
    Example:
        >>> person_obj = {
        ...     "quality_metrics": {
        ...         "average_sharpness": 0.85,
        ...         "average_brightness": 0.75,
        ...         "average_confidence": 0.90
        ...     }
        ... }
        >>> score = calculate_quality_score(person_obj)
        >>> print(f"Quality: {score:.2f}")
        Quality: 0.84
    """
    metrics = person_object.get("quality_metrics", {})
    
    sharpness = metrics.get("average_sharpness", 0.5)
    brightness = metrics.get("average_brightness", 0.5)
    confidence = metrics.get("average_confidence", 0.5)
    
    # Weighted score: sharpness 40%, brightness 30%, confidence 30%
    score = (sharpness * 0.4) + (brightness * 0.3) + (confidence * 0.3)
    
    return score


def select_best_quality_face(
    faces: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Select face with highest quality from list.
    
    Analyzes individual face quality using sharpness, brightness,
    face size, and confidence to determine the best quality face
    for display or analysis.
    
    Quality Score Components:
        - Sharpness: 40% weight
        - Brightness: 20% weight
        - Face size (normalized to 1920x1080): 30% weight
        - Confidence: 10% weight
        
    Args:
        faces: List of face dictionaries with bbox and quality_metrics
        
    Returns:
        Face dictionary with highest quality score
        Returns None if input list is empty
        
    Example:
        >>> faces = [
        ...     {
        ...         "face_id": "face_1",
        ...         "bbox": [100, 200, 300, 400],
        ...         "confidence": 0.95,
        ...         "quality_metrics": {"sharpness": 0.85, "brightness": 0.75}
        ...     }
        ... ]
        >>> best_face = select_best_quality_face(faces)
    """
    if not faces:
        logger.warning("No faces provided for quality selection")
        return None
    
    scored_faces = []
    for face in faces:
        score = calculate_face_quality_score(face)
        scored_faces.append((score, face))
    
    scored_faces.sort(key=lambda x: x[0], reverse=True)
    
    best_score, best_face = scored_faces[0]
    logger.debug(
        f"Selected best quality face: "
        f"id={best_face.get('face_id', 'unknown')}, "
        f"score={best_score:.3f}"
    )
    
    return best_face


def calculate_face_quality_score(face: Dict[str, Any]) -> float:
    """
    Calculate quality score for an individual face.
    
    Uses weighted combination of:
    - Sharpness (40%)
    - Brightness (20%)
    - Face size normalized to 1920x1080 (30%)
    - Confidence (10%)
    
    Args:
        face: Face dictionary with bbox, confidence, quality_metrics
        
    Returns:
        Quality score between 0.0 and 1.0
        
    Face Dictionary Structure:
        {
            "face_id": str,
            "bbox": [x1, y1, x2, y2],
            "confidence": float,
            "quality_metrics": {
                "sharpness": float,
                "brightness": float
            }
        }
        
    Example:
        >>> face = {
        ...     "bbox": [100, 200, 300, 400],
        ...     "confidence": 0.95,
        ...     "quality_metrics": {"sharpness": 0.85, "brightness": 0.75}
        ... }
        >>> score = calculate_face_quality_score(face)
    """
    quality_metrics = face.get("quality_metrics", {})
    bbox = face.get("bbox", [])
    confidence = face.get("confidence", 0.5)
    
    score = 0.0
    
    # Sharpness (40%)
    if "sharpness" in quality_metrics:
        score += quality_metrics["sharpness"] * 0.4
    
    # Brightness (20%)
    if "brightness" in quality_metrics:
        score += quality_metrics["brightness"] * 0.2
    
    # Face size (30%) - normalized to 1920x1080
    if len(bbox) >= 4:
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area = width * height
        # Normalize to reference frame size and clamp to [0, 1]
        normalized_size = min(area / (1920.0 * 1080.0), 1.0)
        score += normalized_size * 0.3
    
    # Confidence (10%)
    score += confidence * 0.1
    
    return score


def rank_person_objects_by_quality(
    person_objects: List[Dict[str, Any]]
) -> List[tuple[float, Dict[str, Any]]]:
    """
    Rank all person objects by quality score.
    
    Returns sorted list of (score, person_object) tuples in descending order
    by quality score. Useful for analysis and debugging.
    
    Args:
        person_objects: List of person object dictionaries
        
    Returns:
        List of (quality_score, person_object) tuples sorted by score
        
    Example:
        >>> person_objects = [obj1, obj2, obj3]
        >>> ranked = rank_person_objects_by_quality(person_objects)
        >>> for score, obj in ranked:
        ...     print(f"Score: {score:.3f}, UUID: {obj['person_uuid']}")
    """
    scored_objects = [
        (calculate_quality_score(obj), obj)
        for obj in person_objects
    ]
    scored_objects.sort(key=lambda x: x[0], reverse=True)
    
    return scored_objects


def get_quality_statistics(
    person_objects: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate quality statistics for a set of person objects.
    
    Args:
        person_objects: List of person object dictionaries
        
    Returns:
        Dictionary with quality statistics:
        {
            "min_quality": float,
            "max_quality": float,
            "avg_quality": float,
            "median_quality": float
        }
        
    Example:
        >>> stats = get_quality_statistics(person_objects)
        >>> print(f"Average quality: {stats['avg_quality']:.2f}")
    """
    if not person_objects:
        return {
            "min_quality": 0.0,
            "max_quality": 0.0,
            "avg_quality": 0.0,
            "median_quality": 0.0
        }
    
    scores = [calculate_quality_score(obj) for obj in person_objects]
    scores.sort()
    
    return {
        "min_quality": min(scores),
        "max_quality": max(scores),
        "avg_quality": sum(scores) / len(scores),
        "median_quality": scores[len(scores) // 2]
    }

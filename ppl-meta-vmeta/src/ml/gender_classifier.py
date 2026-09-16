"""
Gender Classification Processor
PPL Meta Platform - vmeta service

Classifies gender from face images using DeepFace gender model.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import numpy as np
from typing import Any, Dict, Optional
import logging
from deepface import DeepFace

from .deepface_compat import deepface_analyze
import cv2

logger = logging.getLogger(__name__)


class GenderClassifier:
    """
    Gender classification processor.
    
    Uses DeepFace library to classify gender from face images.
    Returns gender ('male', 'female', 'unknown') with confidence.
    """
    
    def __init__(self, confidence_threshold: float = 0.6):
        """
        Initialize gender classifier.
        
        Args:
            confidence_threshold: Minimum confidence for classification
                                 (default: 0.6)
        """
        self.confidence_threshold = confidence_threshold
        self._model_loaded = False
        logger.info(
            f"GenderClassifier initialized "
            f"(threshold: {confidence_threshold})"
        )
    
    def _ensure_model_loaded(self) -> bool:
        """Mark gender model ready. Weights load lazily on first real inference."""
        if not self._model_loaded:
            # Avoid dummy zero-image warmup: older DeepFace OOMs / fails on blanks.
            logger.info("Gender classification model will load on first inference")
            self._model_loaded = True
        return True
    
    def classify_gender(
        self,
        face_image: np.ndarray,
        enforce_detection: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Classify gender from face image.
        
        Args:
            face_image: Face image as numpy array (RGB or BGR)
            enforce_detection: If True, raise error if no face detected
            
        Returns:
            Dict with 'gender' and 'confidence', or None if failed
        """
        if not self._ensure_model_loaded():
            return None
        
        try:
            result = deepface_analyze(
                img_path=face_image,
                actions=['gender'],
                enforce_detection=enforce_detection,
                detector_backend='opencv',
            )
            
            if result and len(result) > 0:
                row = result[0]
                gender_data = row.get('gender', {})
                if not gender_data and row.get('dominant_gender'):
                    gender_data = row.get('dominant_gender')
                
                if not gender_data:
                    logger.warning("No gender prediction in result")
                    return None
                
                # DeepFace returns dict like {'Man': 98.5, 'Woman': 1.5}
                # or a string / dominant_gender label on older builds.
                gender_result = self._parse_gender_result(gender_data)
                
                logger.debug(
                    f"Classified gender: {gender_result['gender']} "
                    f"({gender_result['confidence']:.2f})"
                )
                
                return gender_result
            else:
                logger.warning("No face detected for gender classification")
                return None
                
        except Exception as e:
            logger.error(f"Failed to classify gender: {e}")
            return None
    
    def _parse_gender_result(
        self,
        gender_scores: Any,
    ) -> Dict[str, Any]:
        """
        Parse DeepFace gender result.
        
        Args:
            gender_scores: Dict with 'Man'/'Woman' scores, or a label string
            
        Returns:
            Dict with normalized gender and confidence
        """
        if isinstance(gender_scores, str):
            label = gender_scores.strip().lower()
            if label in ("man", "male"):
                gender, confidence = "male", 0.9
            elif label in ("woman", "female"):
                gender, confidence = "female", 0.9
            else:
                gender, confidence = "unknown", 0.5
            if confidence < self.confidence_threshold:
                gender = "unknown"
            return {
                "gender": gender,
                "confidence": confidence,
                "raw_scores": {"male": 0.0, "female": 0.0},
            }

        # Get scores (support Man/Woman and Male/Female keys)
        man_score = float(
            gender_scores.get("Man", gender_scores.get("male", 0.0)) or 0.0
        )
        woman_score = float(
            gender_scores.get("Woman", gender_scores.get("female", 0.0)) or 0.0
        )
        
        # Determine gender
        if man_score > woman_score:
            gender = 'male'
            confidence = man_score / 100.0 if man_score > 1.0 else man_score
        elif woman_score > man_score:
            gender = 'female'
            confidence = woman_score / 100.0 if woman_score > 1.0 else woman_score
        else:
            gender = 'unknown'
            confidence = 0.5
        
        # If confidence below threshold, mark as unknown
        if confidence < self.confidence_threshold:
            gender = 'unknown'
        
        return {
            'gender': gender,
            'confidence': confidence,
            'raw_scores': {
                'male': man_score / 100.0 if man_score > 1.0 else man_score,
                'female': woman_score / 100.0 if woman_score > 1.0 else woman_score,
            }
        }
    
    def classify_from_person_object(
        self,
        person_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Classify gender from person object data.
        
        Args:
            person_data: Person object dict with face data
            
        Returns:
            Gender classification dict or None
        """
        try:
            # Check if gender already exists
            if 'gender_estimate' in person_data:
                gender_est = person_data['gender_estimate']
                if 'gender' in gender_est and 'confidence' in gender_est:
                    return gender_est
            
            # Extract from face crop
            if 'best_face_crop' in person_data:
                face_crop = person_data['best_face_crop']
                
                if isinstance(face_crop, str):
                    try:
                        face_image = cv2.imread(face_crop)
                        if face_image is not None:
                            return self.classify_gender(face_image)
                    except Exception as e:
                        logger.warning(f"Failed to load face crop: {e}")
                        return None
                
                elif isinstance(face_crop, np.ndarray):
                    return self.classify_gender(face_crop)
            
            logger.warning("No suitable face data for gender classification")
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to classify gender from person object: {e}"
            )
            return None
    
    def validate_gender(self, gender: str) -> bool:
        """
        Validate gender value.
        
        Args:
            gender: Gender string
            
        Returns:
            True if valid
        """
        return gender.lower() in ['male', 'female', 'unknown']
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_name': 'DeepFace Gender',
            'confidence_threshold': self.confidence_threshold,
            'valid_classes': ['male', 'female', 'unknown'],
            'loaded': self._model_loaded
        }

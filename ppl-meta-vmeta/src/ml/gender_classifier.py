"""
Gender Classification Processor
PPL Meta Platform - vmeta service

Classifies gender from face images using DeepFace gender model.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import numpy as np
from typing import Optional, Dict, Any
import logging
from deepface import DeepFace
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
        """Ensure DeepFace gender model is loaded."""
        if not self._model_loaded:
            try:
                logger.info("Loading gender classification model...")
                # Trigger model load
                DeepFace.analyze(
                    img_path=np.zeros((160, 160, 3), dtype=np.uint8),
                    actions=['gender'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True
                )
                self._model_loaded = True
                logger.info("✅ Gender model loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load gender model: {e}")
                return False
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
            result = DeepFace.analyze(
                img_path=face_image,
                actions=['gender'],
                enforce_detection=enforce_detection,
                detector_backend='opencv',
                silent=True
            )
            
            if result and len(result) > 0:
                gender_data = result[0].get('gender', {})
                
                if not gender_data:
                    logger.warning("No gender prediction in result")
                    return None
                
                # DeepFace returns dict like:
                # {'Man': 98.5, 'Woman': 1.5}
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
        gender_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Parse DeepFace gender result.
        
        Args:
            gender_scores: Dict with 'Man' and 'Woman' scores
            
        Returns:
            Dict with normalized gender and confidence
        """
        # Get scores
        man_score = gender_scores.get('Man', 0.0)
        woman_score = gender_scores.get('Woman', 0.0)
        
        # Determine gender
        if man_score > woman_score:
            gender = 'male'
            confidence = man_score / 100.0
        elif woman_score > man_score:
            gender = 'female'
            confidence = woman_score / 100.0
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
                'male': man_score / 100.0,
                'female': woman_score / 100.0
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

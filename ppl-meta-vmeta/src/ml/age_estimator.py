"""
Age Estimation Processor
PPL Meta Platform - vmeta service

Estimates age range from face images using DeepFace age model.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple
import logging
from deepface import DeepFace
import cv2

logger = logging.getLogger(__name__)


class AgeEstimator:
    """
    Age estimation processor.
    
    Uses DeepFace library to estimate age from face images.
    Returns age range (min, max) with confidence score.
    """
    
    def __init__(self, age_tolerance: int = 5):
        """
        Initialize age estimator.
        
        Args:
            age_tolerance: +/- years around predicted age (default: 5)
        """
        self.age_tolerance = age_tolerance
        self._model_loaded = False
        logger.info(f"AgeEstimator initialized (tolerance: ±{age_tolerance})")
    
    def _ensure_model_loaded(self) -> bool:
        """Ensure DeepFace age model is loaded."""
        if not self._model_loaded:
            try:
                logger.info("Loading age estimation model...")
                # Trigger model load
                DeepFace.analyze(
                    img_path=np.zeros((160, 160, 3), dtype=np.uint8),
                    actions=['age'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True
                )
                self._model_loaded = True
                logger.info("✅ Age model loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load age model: {e}")
                return False
        return True
    
    def estimate_age(
        self,
        face_image: np.ndarray,
        enforce_detection: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Estimate age from face image.
        
        Args:
            face_image: Face image as numpy array (RGB or BGR)
            enforce_detection: If True, raise error if no face detected
            
        Returns:
            Dict with 'age', 'min_age', 'max_age', 'confidence'
            or None if failed
        """
        if not self._ensure_model_loaded():
            return None
        
        try:
            result = DeepFace.analyze(
                img_path=face_image,
                actions=['age'],
                enforce_detection=enforce_detection,
                detector_backend='opencv',
                silent=True
            )
            
            if result and len(result) > 0:
                predicted_age = result[0].get('age')
                
                if predicted_age is None:
                    logger.warning("No age prediction in result")
                    return None
                
                # Convert to age range
                age_data = self._age_to_range(predicted_age)
                
                logger.debug(
                    f"Estimated age: {predicted_age} "
                    f"({age_data['min_age']}-{age_data['max_age']})"
                )
                
                return age_data
            else:
                logger.warning("No face detected for age estimation")
                return None
                
        except Exception as e:
            logger.error(f"Failed to estimate age: {e}")
            return None
    
    def _age_to_range(self, predicted_age: float) -> Dict[str, Any]:
        """
        Convert predicted age to age range.
        
        Args:
            predicted_age: Predicted age (float)
            
        Returns:
            Dict with age, min_age, max_age, confidence
        """
        # Round to nearest integer
        age = int(round(predicted_age))
        
        # Calculate range
        min_age = max(0, age - self.age_tolerance)
        max_age = min(120, age + self.age_tolerance)
        
        # Estimate confidence (higher confidence for adult ages)
        # Age models are typically more accurate for 20-60 range
        if 20 <= age <= 60:
            confidence = 0.85
        elif 10 <= age <= 70:
            confidence = 0.75
        else:
            confidence = 0.65
        
        return {
            'age': age,
            'min_age': min_age,
            'max_age': max_age,
            'confidence': confidence,
            'tolerance': self.age_tolerance
        }
    
    def estimate_from_person_object(
        self,
        person_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Estimate age from person object data.
        
        Args:
            person_data: Person object dict with face data
            
        Returns:
            Age estimation dict or None
        """
        try:
            # Check if age already exists
            if 'age_estimate' in person_data:
                age_est = person_data['age_estimate']
                if all(k in age_est for k in ['min_age', 'max_age']):
                    return age_est
            
            # Extract from face crop
            if 'best_face_crop' in person_data:
                face_crop = person_data['best_face_crop']
                
                if isinstance(face_crop, str):
                    try:
                        face_image = cv2.imread(face_crop)
                        if face_image is not None:
                            return self.estimate_age(face_image)
                    except Exception as e:
                        logger.warning(f"Failed to load face crop: {e}")
                        return None
                
                elif isinstance(face_crop, np.ndarray):
                    return self.estimate_age(face_crop)
            
            logger.warning("No suitable face data for age estimation")
            return None
            
        except Exception as e:
            logger.error(f"Failed to estimate age from person object: {e}")
            return None
    
    def validate_age_range(
        self,
        min_age: int,
        max_age: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate age range values.
        
        Args:
            min_age: Minimum age
            max_age: Maximum age
            
        Returns:
            (is_valid, error_message)
        """
        if min_age < 0:
            return False, "Minimum age cannot be negative"
        
        if max_age > 120:
            return False, "Maximum age cannot exceed 120"
        
        if min_age > max_age:
            return False, "Minimum age cannot exceed maximum age"
        
        return True, None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_name': 'DeepFace Age',
            'age_tolerance': self.age_tolerance,
            'loaded': self._model_loaded
        }

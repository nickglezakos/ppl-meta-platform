"""
MVR Processor - Orchestrates ML Models
PPL Meta Platform - vmeta service

Coordinates FaceNet, Age, and Gender models for MVR-People processing.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import numpy as np
from typing import Optional, Dict, Any
import logging
from .facenet_processor import FaceNetProcessor
from .age_estimator import AgeEstimator
from .gender_classifier import GenderClassifier

logger = logging.getLogger(__name__)


class MVRProcessor:
    """
    MVR-People ML processor.
    
    Orchestrates FaceNet, Age, and Gender models to extract
    complete biometric features for MVR-People creation.
    """
    
    def __init__(
        self,
        age_tolerance: int = 5,
        gender_confidence_threshold: float = 0.6
    ):
        """
        Initialize MVR processor.
        
        Args:
            age_tolerance: +/- years for age estimation
            gender_confidence_threshold: Min confidence for gender
        """
        self.facenet = FaceNetProcessor()
        self.age_estimator = AgeEstimator(age_tolerance=age_tolerance)
        self.gender_classifier = GenderClassifier(
            confidence_threshold=gender_confidence_threshold
        )
        logger.info("MVRProcessor initialized with all ML models")
    
    def process_face(
        self,
        face_image: np.ndarray,
        enforce_detection: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Process face image through all ML models.
        
        Args:
            face_image: Face image as numpy array
            enforce_detection: If True, fail if no face detected
            
        Returns:
            Dict with embedding, age, gender data or None
        """
        try:
            result = {
                'success': False,
                'face_embedding': None,
                'age_estimate': None,
                'gender_estimate': None,
                'errors': []
            }
            
            # Extract face embedding (required)
            embedding = self.facenet.extract_embedding(
                face_image,
                enforce_detection=enforce_detection
            )
            
            if embedding is None:
                result['errors'].append('Face embedding extraction failed')
                logger.warning("Failed to extract face embedding")
                return result
            
            result['face_embedding'] = embedding.tolist()
            
            # Estimate age (optional but recommended)
            age_data = self.age_estimator.estimate_age(
                face_image,
                enforce_detection=False
            )
            
            if age_data:
                result['age_estimate'] = age_data
            else:
                result['errors'].append('Age estimation failed')
                logger.warning("Failed to estimate age")
            
            # Classify gender (optional but recommended)
            gender_data = self.gender_classifier.classify_gender(
                face_image,
                enforce_detection=False
            )
            
            if gender_data:
                result['gender_estimate'] = gender_data
            else:
                result['errors'].append('Gender classification failed')
                logger.warning("Failed to classify gender")
            
            # Mark as success if we got at least the embedding
            result['success'] = True
            
            logger.info(
                f"Face processing complete: "
                f"embedding={embedding is not None}, "
                f"age={age_data is not None}, "
                f"gender={gender_data is not None}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Face processing failed: {e}")
            return {
                'success': False,
                'face_embedding': None,
                'age_estimate': None,
                'gender_estimate': None,
                'errors': [str(e)]
            }
    
    def process_person_object(
        self,
        person_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process person object through all ML models.
        
        Args:
            person_data: Person object dict from Orchestrator
            
        Returns:
            Dict with all biometric features or None
        """
        try:
            result = {
                'success': False,
                'face_embedding': None,
                'age_estimate': None,
                'gender_estimate': None,
                'quality_score': None,
                'confidence_score': None,
                'errors': []
            }
            
            # Extract quality and confidence if available
            result['quality_score'] = person_data.get('quality_score', 0.5)
            result['confidence_score'] = person_data.get(
                'confidence_score',
                0.5
            )
            
            # Extract face embedding
            embedding = self.facenet.extract_from_person_object(person_data)
            
            if embedding is None:
                result['errors'].append(
                    'Failed to extract face embedding from person object'
                )
                logger.warning(
                    "Failed to extract embedding from person object"
                )
                return result
            
            result['face_embedding'] = embedding.tolist()
            
            # Estimate age
            age_data = self.age_estimator.estimate_from_person_object(
                person_data
            )
            if age_data:
                result['age_estimate'] = age_data
            else:
                result['errors'].append('Age estimation failed')
            
            # Classify gender
            gender_data = (
                self.gender_classifier.classify_from_person_object(
                    person_data
                )
            )
            if gender_data:
                result['gender_estimate'] = gender_data
            else:
                result['errors'].append('Gender classification failed')
            
            # Success if we got the embedding
            result['success'] = True
            
            logger.info(
                f"Person object processing complete for "
                f"person {person_data.get('person_object_uuid', 'unknown')}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Person object processing failed: {e}")
            return {
                'success': False,
                'face_embedding': None,
                'age_estimate': None,
                'gender_estimate': None,
                'errors': [str(e)]
            }
    
    def calculate_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate similarity between two face embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        return self.facenet.cosine_similarity(embedding1, embedding2)
    
    def get_models_info(self) -> Dict[str, Any]:
        """Get information about all loaded models."""
        return {
            'facenet': self.facenet.get_model_info(),
            'age_estimator': self.age_estimator.get_model_info(),
            'gender_classifier': self.gender_classifier.get_model_info()
        }
    
    def validate_embedding(self, embedding: Any) -> bool:
        """
        Validate face embedding format and size.
        
        Args:
            embedding: Face embedding to validate
            
        Returns:
            True if valid
        """
        try:
            if embedding is None:
                return False
            
            # Convert to numpy array if needed
            if isinstance(embedding, list):
                embedding = np.array(embedding)
            
            if not isinstance(embedding, np.ndarray):
                return False
            
            # Check size
            if len(embedding) != 512:
                return False
            
            # Check for NaN or Inf
            if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Embedding validation failed: {e}")
            return False

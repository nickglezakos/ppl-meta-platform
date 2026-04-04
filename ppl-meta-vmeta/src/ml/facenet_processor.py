"""
FaceNet Face Embedding Processor
PPL Meta Platform - vmeta service

Generates 512-dimensional face embeddings using FaceNet model via DeepFace.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import numpy as np
from typing import Optional, Dict, Any, List
import logging
from deepface import DeepFace
import cv2

logger = logging.getLogger(__name__)


class FaceNetProcessor:
    """
    FaceNet face embedding processor.
    
    Uses DeepFace library with Facenet512 model to generate
    512-dimensional face embeddings for person identification.
    """
    
    def __init__(self):
        """Initialize FaceNet processor."""
        self.model_name = "Facenet512"
        self.embedding_size = 512
        self._model_loaded = False
        logger.info("FaceNetProcessor initialized")
    
    def _ensure_model_loaded(self) -> bool:
        """Ensure DeepFace model is loaded (lazy loading)."""
        if not self._model_loaded:
            try:
                # DeepFace automatically downloads and caches models
                logger.info(f"Loading {self.model_name} model...")
                # Trigger model load with a dummy operation
                DeepFace.represent(
                    img_path=np.zeros((160, 160, 3), dtype=np.uint8),
                    model_name=self.model_name,
                    enforce_detection=False
                )
                self._model_loaded = True
                logger.info(f"✅ {self.model_name} model loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load {self.model_name} model: {e}")
                return False
        return True
    
    def extract_embedding(
        self,
        face_image: np.ndarray,
        enforce_detection: bool = False
    ) -> Optional[np.ndarray]:
        """
        Extract face embedding from image.
        
        Args:
            face_image: Face image as numpy array (RGB or BGR)
            enforce_detection: If True, raise error if no face detected
            
        Returns:
            512-dimensional embedding as numpy array, or None if failed
        """
        if not self._ensure_model_loaded():
            return None
        
        try:
            # DeepFace.represent returns list of dicts with embeddings
            result = DeepFace.represent(
                img_path=face_image,
                model_name=self.model_name,
                enforce_detection=enforce_detection,
                detector_backend='opencv',
                align=True
            )

            if not result:
                logger.warning("No face detected in image")
                return None

            # FIX 1: Reject crops that contain more than one detected face.
            # result[0] is the most prominent/frontal face — not necessarily
            # the intended subject — causing silent identity contamination in
            # the stored MVR embedding when two people share a crop.
            # See: docs/modules/MVR merge/EMBEDDING_CONTAMINATION.md
            if isinstance(result, list) and len(result) > 1:
                logger.warning(
                    f"Multi-face crop: {len(result)} faces detected. "
                    f"Rejecting embedding to prevent identity contamination."
                )
                return None

            embedding = np.array(result[0]['embedding'])

            # Verify embedding size
            if len(embedding) != self.embedding_size:
                logger.warning(
                    f"Unexpected embedding size: {len(embedding)}"
                )
                return None

            # Normalize embedding
            embedding = self._normalize_embedding(embedding)

            return embedding

        except Exception as e:
            logger.error(f"Failed to extract embedding: {e}")
            return None
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        Normalize embedding to unit vector.
        
        Args:
            embedding: Raw embedding vector
            
        Returns:
            Normalized embedding (L2 norm = 1)
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            # Cosine similarity = dot product of normalized vectors
            similarity = np.dot(embedding1, embedding2)
            
            # Ensure result is in [0, 1] range
            # (normalized vectors should give [-1, 1], map to [0, 1])
            similarity = (similarity + 1) / 2
            
            return float(np.clip(similarity, 0.0, 1.0))
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def extract_from_person_object(
        self,
        person_data: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """
        Extract embedding from person object data.
        
        Args:
            person_data: Person object dict with 'best_face_crop' or similar
            
        Returns:
            Face embedding or None
        """
        try:
            # Check if embedding already exists
            if 'face_embedding' in person_data:
                embedding = np.array(person_data['face_embedding'])
                if len(embedding) == self.embedding_size:
                    return embedding
            
            # Extract from face crop if available
            if 'best_face_crop' in person_data:
                face_crop = person_data['best_face_crop']
                
                # Handle different formats (base64, file path, numpy array)
                if isinstance(face_crop, str):
                    # Assume it's a file path or base64
                    try:
                        face_image = cv2.imread(face_crop)
                        if face_image is not None:
                            return self.extract_embedding(face_image)
                    except Exception as e:
                        logger.warning(f"Failed to load face crop: {e}")
                        return None
                
                elif isinstance(face_crop, np.ndarray):
                    return self.extract_embedding(face_crop)
            
            logger.warning(
                "No suitable face data found in person object"
            )
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to extract from person object: {e}"
            )
            return None
    
    def batch_extract_embeddings(
        self,
        face_images: List[np.ndarray]
    ) -> List[Optional[np.ndarray]]:
        """
        Extract embeddings from multiple face images.
        
        Args:
            face_images: List of face images
            
        Returns:
            List of embeddings (may contain None for failed extractions)
        """
        embeddings = []
        for face_image in face_images:
            embedding = self.extract_embedding(face_image)
            embeddings.append(embedding)
        
        logger.info(
            f"Extracted {sum(1 for e in embeddings if e is not None)}"
            f"/{len(face_images)} embeddings"
        )
        
        return embeddings
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_name': self.model_name,
            'embedding_size': self.embedding_size,
            'backend': 'DeepFace',
            'loaded': self._model_loaded
        }

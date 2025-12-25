"""
ML Inference API
PPL Meta Platform - vmeta service

Provides endpoints for age/gender detection using DeepFace models.
Used by instant detection feature in Camera Service.

Created: December 11, 2025
"""

import logging
from typing import Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from ml.age_estimator import AgeEstimator
from ml.gender_classifier import GenderClassifier

logger = logging.getLogger(__name__)

router = APIRouter()

# Global model instances (shared across all requests)
_age_estimator = None
_gender_classifier = None

def get_age_estimator() -> AgeEstimator:
    """Get or create age estimator singleton."""
    global _age_estimator
    if _age_estimator is None:
        logger.info("🔧 Creating AgeEstimator singleton...")
        _age_estimator = AgeEstimator(age_tolerance=5)
        # Pre-warm the model
        _age_estimator._ensure_model_loaded()
    return _age_estimator

def get_gender_classifier() -> GenderClassifier:
    """Get or create gender classifier singleton."""
    global _gender_classifier
    if _gender_classifier is None:
        logger.info("🔧 Creating GenderClassifier singleton...")
        _gender_classifier = GenderClassifier(confidence_threshold=0.6)
        # Pre-warm the model
        _gender_classifier._ensure_model_loaded()
    return _gender_classifier


class AgeGenderResponse(BaseModel):
    """Response model for age/gender detection"""
    age_min: int
    age_max: int
    age_confidence: float
    gender: str
    gender_confidence: float
    success: bool


@router.post("/detect-age-gender", response_model=AgeGenderResponse)
async def detect_age_gender(
    file: UploadFile = File(..., description="Face region image (JPEG/PNG)")
):
    """
    Detect age and gender from a cropped face image.
    
    Uses DeepFace models:
    - Age estimation with ±5 year tolerance
    - Gender classification (male/female)
    
    Expected input: Cropped face region (bbox extracted from frame)
    
    Used by Camera Service instant detection feature.
    """
    try:
        # Read and decode image
        file_content = await file.read()
        nparr = np.frombuffer(file_content, np.uint8)
        face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if face_image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Get singleton instances
        age_est = get_age_estimator()
        gender_clf = get_gender_classifier()
        
        # Estimate age
        age_result = age_est.estimate_age(
            face_image,
            enforce_detection=False
        )
        
        # Classify gender
        gender_result = gender_clf.classify_gender(
            face_image,
            enforce_detection=False
        )
        
        # Handle failures gracefully
        if age_result is None or gender_result is None:
            logger.warning("Age or gender detection failed, returning defaults")
            return AgeGenderResponse(
                age_min=0,
                age_max=100,
                age_confidence=0.0,
                gender="unknown",
                gender_confidence=0.0,
                success=False
            )
        
        return AgeGenderResponse(
            age_min=age_result.get("min_age", 0),
            age_max=age_result.get("max_age", 100),
            age_confidence=age_result.get("confidence", 0.0),
            gender=gender_result.get("gender", "unknown"),
            gender_confidence=gender_result.get("confidence", 0.0),
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in age/gender detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Detection error: {str(e)}"
        )


@router.get("/ml-status")
async def ml_status():
    """
    Get status of ML models (age/gender).
    
    Returns model loading status and readiness.
    """
    age_est = get_age_estimator()
    gender_clf = get_gender_classifier()
    return {
        "age_model_loaded": age_est._model_loaded,
        "gender_model_loaded": gender_clf._model_loaded,
        "ready": age_est._model_loaded and gender_clf._model_loaded
    }

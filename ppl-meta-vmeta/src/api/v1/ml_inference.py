"""
ML Inference API
PPL Meta Platform - vmeta service

Provides endpoints for age/gender detection using DeepFace models.
Used by instant detection feature in Camera Service.

Created: December 11, 2025
"""

import logging
import asyncio
from typing import Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from pydantic import BaseModel

from ml.age_estimator import AgeEstimator
from ml.gender_classifier import GenderClassifier
from api.dependencies import get_mvr_service
from services.mvr_service import MVRService

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


class FaceIdentityResponse(BaseModel):
    """Response model for face identity lookup"""
    success: bool
    matched: bool
    mvr_people_uuid: Optional[str] = None
    similarity_score: float = 0.0
    total_candidates: int = 0


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


@router.post("/identify-face", response_model=FaceIdentityResponse)
async def identify_face(
    file: UploadFile = File(..., description="Face region image (JPEG/PNG)"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0),
    max_results: int = Query(1, ge=1, le=10),
    mvr_service: MVRService = Depends(get_mvr_service),
):
    """
    Identify a face crop against existing MVR identities.

    This endpoint is intended for instant detection enrichment:
    face image -> embedding -> nearest MVR candidate.
    """
    try:
        file_content = await file.read()
        nparr = np.frombuffer(file_content, np.uint8)
        face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if face_image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        ml_result = await asyncio.to_thread(
            mvr_service.ml_processor.process_face,
            face_image,
            False,
        )

        if not ml_result or not ml_result.get("success"):
            return FaceIdentityResponse(
                success=False,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
            )

        embedding_data = ml_result.get("face_embedding")
        if not embedding_data:
            return FaceIdentityResponse(
                success=False,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
            )

        face_embedding = np.array(embedding_data, dtype=np.float32)
        if face_embedding.size != 512:
            return FaceIdentityResponse(
                success=False,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
            )

        candidates = await mvr_service.find_similar_people(
            face_embedding=face_embedding,
            similarity_threshold=similarity_threshold,
            max_results=max_results,
        )

        if not candidates:
            return FaceIdentityResponse(
                success=True,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
            )

        best = candidates[0]
        best_uuid = best.get("mvr_people_uuid")
        best_similarity = float(best.get("similarity_score", 0.0) or 0.0)

        return FaceIdentityResponse(
            success=True,
            matched=bool(best_uuid),
            mvr_people_uuid=str(best_uuid) if best_uuid else None,
            similarity_score=best_similarity,
            total_candidates=len(candidates),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face identity lookup: {e}")
        raise HTTPException(status_code=500, detail=f"Identity lookup error: {str(e)}")

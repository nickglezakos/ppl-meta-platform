"""
ML Inference API
PPL Meta Platform - vmeta service

Provides endpoints for age/gender detection using DeepFace models.
Used by instant detection feature in Camera Service.

Created: December 11, 2025
"""

import logging
import asyncio
import threading
from typing import Any, Dict, Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from pydantic import BaseModel

from ml.age_estimator import AgeEstimator
from ml.gender_classifier import GenderClassifier
from ml.deepface_compat import (
    deepface_analyze,
    ensure_deepface_weight_paths,
    warmup_age_gender_models,
)
from api.dependencies import get_mvr_service
from services.mvr_service import MVRService
from uuid import UUID

logger = logging.getLogger(__name__)

router = APIRouter()

# Global model instances (shared across all requests)
_age_estimator = None
_gender_classifier = None
_deepface_models: Optional[Dict[str, Any]] = None
_warmup_lock = threading.Lock()
_warmup_started = False


def get_age_estimator() -> AgeEstimator:
    """Get or create age estimator singleton."""
    global _age_estimator
    if _age_estimator is None:
        logger.info("🔧 Creating AgeEstimator singleton...")
        _age_estimator = AgeEstimator(age_tolerance=5)
        _age_estimator._ensure_model_loaded()
    return _age_estimator


def get_gender_classifier() -> GenderClassifier:
    """Get or create gender classifier singleton."""
    global _gender_classifier
    if _gender_classifier is None:
        logger.info("🔧 Creating GenderClassifier singleton...")
        _gender_classifier = GenderClassifier(confidence_threshold=0.6)
        _gender_classifier._ensure_model_loaded()
    return _gender_classifier


def ensure_deepface_models_warm() -> Dict[str, Any]:
    """Load Age/Gender weights once; safe to call from request path or startup."""
    global _deepface_models
    if _deepface_models is not None:
        return _deepface_models
    with _warmup_lock:
        if _deepface_models is not None:
            return _deepface_models
        ensure_deepface_weight_paths()
        logger.info("🔥 Warming DeepFace Age + Gender models (CPU; may take 30–90s)...")
        _deepface_models = warmup_age_gender_models()
        get_age_estimator()._model_loaded = True
        get_gender_classifier()._model_loaded = True
        logger.info("✅ DeepFace Age + Gender models ready")
        return _deepface_models


async def _mvr_people_exists(mvr_service: MVRService, mvr_people_uuid: Any) -> bool:
    """True when the UUID is present in mvr_people (ghost ids must not leave this API)."""
    if not mvr_people_uuid:
        return False
    try:
        uid = UUID(str(mvr_people_uuid))
    except (TypeError, ValueError):
        return False
    row = await mvr_service.repository.get_mvr_people_by_uuid(uid)
    return row is not None


async def _verified_mvr_uuid(
    mvr_service: MVRService, mvr_people_uuid: Any
) -> Optional[str]:
    """Return uuid string only if the row exists; otherwise None (never return ghosts)."""
    if not mvr_people_uuid:
        return None
    if await _mvr_people_exists(mvr_service, mvr_people_uuid):
        return str(mvr_people_uuid)
    logger.warning(
        "identify-face: MVR uuid %s is not in mvr_people; treating as unmatched",
        mvr_people_uuid,
    )
    return None


def start_deepface_warmup_background() -> None:
    """Kick off model preload without blocking FastAPI startup."""
    global _warmup_started
    if _warmup_started:
        return
    _warmup_started = True

    def _run():
        try:
            ensure_deepface_models_warm()
        except Exception as exc:
            logger.error("❌ DeepFace warmup failed: %s", exc, exc_info=True)

    threading.Thread(target=_run, name="deepface-warmup", daemon=True).start()
    logger.info("🔥 DeepFace warmup thread started")


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
    created_new: bool = False
    dedupe_reused_existing: bool = False


class FaceEmbedResponse(BaseModel):
    """FaceNet embedding only — no gallery match or mvr_people write."""
    success: bool
    face_embedding: Optional[list] = None
    face_quality: float = 0.0
    detection_confidence: float = 0.0


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
        file_content = await file.read()
        nparr = np.frombuffer(file_content, np.uint8)
        face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if face_image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        age_est = get_age_estimator()
        gender_clf = get_gender_classifier()

        # One analyze() for both attributes (avoids loading/running twice).
        models = None
        try:
            models = await asyncio.to_thread(ensure_deepface_models_warm)
        except Exception as warm_err:
            logger.warning("DeepFace warmup unavailable, analyzing cold: %s", warm_err)

        rows = await asyncio.to_thread(
            deepface_analyze,
            face_image,
            ["age", "gender"],
            False,
            "opencv",
            models,
        )
        if not rows:
            logger.warning("Age/gender detection returned empty result")
            return AgeGenderResponse(
                age_min=0,
                age_max=100,
                age_confidence=0.0,
                gender="unknown",
                gender_confidence=0.0,
                success=False,
            )

        row = rows[0]
        predicted_age = row.get("age")
        age_result = (
            age_est._age_to_range(float(predicted_age))
            if predicted_age is not None
            else None
        )

        gender_data = row.get("gender", {})
        if not gender_data and row.get("dominant_gender"):
            gender_data = row.get("dominant_gender")
        gender_result = (
            gender_clf._parse_gender_result(gender_data) if gender_data else None
        )

        if age_result is None or gender_result is None:
            logger.warning("Age or gender detection failed, returning defaults")
            return AgeGenderResponse(
                age_min=0,
                age_max=100,
                age_confidence=0.0,
                gender="unknown",
                gender_confidence=0.0,
                success=False,
            )

        return AgeGenderResponse(
            age_min=age_result.get("min_age", 0),
            age_max=age_result.get("max_age", 100),
            age_confidence=age_result.get("confidence", 0.0),
            gender=gender_result.get("gender", "unknown"),
            gender_confidence=gender_result.get("confidence", 0.0),
            success=True,
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
        "deepface_models_warm": _deepface_models is not None,
        "ready": bool(_deepface_models),
    }


@router.post("/embed-face", response_model=FaceEmbedResponse)
async def embed_face(
    file: UploadFile = File(..., description="Face region image (JPEG/PNG)"),
    mvr_service: MVRService = Depends(get_mvr_service),
):
    """
    Extract a FaceNet embedding from a face crop without gallery lookup or DB writes.

    Used by Instant Detection live cycles to attach ephemeral InstantMvr embeddings
    for Redis / Vprofile matching.
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
            None,
        )
        if not ml_result or not ml_result.get("success"):
            return FaceEmbedResponse(success=False)

        embedding_data = ml_result.get("face_embedding")
        if not embedding_data:
            return FaceEmbedResponse(success=False)

        return FaceEmbedResponse(
            success=True,
            face_embedding=list(embedding_data),
            face_quality=float(ml_result.get("face_quality", 0.5) or 0.5),
            detection_confidence=float(
                ml_result.get("detection_confidence", 0.5) or 0.5
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in embed-face: {e}")
        raise HTTPException(status_code=500, detail=f"embed-face failed: {e}") from e


@router.post("/identify-face", response_model=FaceIdentityResponse)
async def identify_face(
    file: UploadFile = File(..., description="Face region image (JPEG/PNG)"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0),
    max_results: int = Query(1, ge=1, le=10),
    create_if_missing: bool = Query(
        True,
        description="Create isolated MVR identity if no match is found",
    ),
    dedupe_similarity_threshold: float = Query(
        0.55,
        ge=0.0,
        le=1.0,
        description="Lower threshold used for dedupe reuse before creating new MVR",
    ),
    enable_dedupe_reuse: bool = Query(
        True,
        description="Reuse near-existing MVR below strict threshold before creating new",
    ),
    force_create: bool = Query(
        False,
        description="Always create a new isolated MVR (skip gallery match / dedupe). "
        "Used by authenticator enroll so phone faces are not bound to unrelated gallery people.",
    ),
    target_mvr_people_uuid: str | None = Query(
        None,
        description="If set, compare 1:1 against this MVR only (skip gallery nearest-neighbor). "
        "Used by authenticator verify against the enrolled person.",
    ),
    target_mvr_people_uuids: str | None = Query(
        None,
        description="Comma-separated MVR UUIDs for 1:N compare (single face extract, best score). "
        "Used by authenticator against PPP-linked identities for the signed-in user.",
    ),
    detect_face: bool = Query(
        False,
        description="Run a face detector before FaceNet. Required for full-frame phone "
        "photos (authenticator). Leave false for pre-cropped face patches.",
    ),
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
            bool(detect_face),  # enforce_detection when detecting full frames
            "opencv" if detect_face else None,
        )

        if not ml_result or not ml_result.get("success"):
            return FaceIdentityResponse(
                success=False,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
                created_new=False,
                dedupe_reused_existing=False,
            )

        embedding_data = ml_result.get("face_embedding")
        if not embedding_data:
            return FaceIdentityResponse(
                success=False,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
                created_new=False,
                dedupe_reused_existing=False,
            )

        face_embedding = np.array(embedding_data, dtype=np.float32)
        if face_embedding.size != 512:
            return FaceIdentityResponse(
                success=False,
                matched=False,
                mvr_people_uuid=None,
                similarity_score=0.0,
                total_candidates=0,
                created_new=False,
                dedupe_reused_existing=False,
            )

        # Authenticator: score against one or more known MVR people (not gallery NN).
        target_ids: list[str] = []
        if target_mvr_people_uuids:
            target_ids.extend(
                part.strip()
                for part in str(target_mvr_people_uuids).split(",")
                if part.strip()
            )
        if target_mvr_people_uuid:
            target_ids.append(str(target_mvr_people_uuid).strip())
        # Dedupe preserve order
        seen_targets: set[str] = set()
        ordered_targets: list[str] = []
        for tid in target_ids:
            if tid and tid not in seen_targets:
                seen_targets.add(tid)
                ordered_targets.append(tid)

        if ordered_targets:
            from uuid import UUID as _UUID

            def _parse_embedding(raw) -> np.ndarray | None:
                if raw is None:
                    return None
                if isinstance(raw, str):
                    arr = np.array(
                        [float(x) for x in raw.strip("[]").split(",") if x.strip()],
                        dtype=np.float32,
                    )
                else:
                    arr = np.array(raw, dtype=np.float32)
                if arr.size != 512:
                    return None
                return arr

            best_uuid: str | None = None
            best_score = -1.0
            scored = 0
            for tid in ordered_targets:
                try:
                    target_uuid = _UUID(tid)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid target MVR uuid: {tid}"
                    ) from exc
                person = await mvr_service.repository.get_mvr_people_by_uuid(target_uuid)
                if not person:
                    continue
                stored = _parse_embedding(person.get("face_embedding"))
                if stored is None:
                    continue
                denom = float(
                    np.linalg.norm(face_embedding) * np.linalg.norm(stored)
                )
                score = (
                    float(np.dot(face_embedding, stored) / denom) if denom > 0 else 0.0
                )
                scored += 1
                if score > best_score:
                    best_score = score
                    best_uuid = str(target_uuid)

            if scored == 0 or best_uuid is None:
                return FaceIdentityResponse(
                    success=True,
                    matched=False,
                    mvr_people_uuid=None,
                    similarity_score=0.0,
                    total_candidates=0,
                    created_new=False,
                    dedupe_reused_existing=False,
                )

            matched = best_score >= similarity_threshold
            return FaceIdentityResponse(
                success=True,
                matched=matched,
                mvr_people_uuid=best_uuid if matched else None,
                similarity_score=float(best_score),
                total_candidates=scored,
                created_new=False,
                dedupe_reused_existing=False,
            )

        # Authenticator enroll: always mint a fresh isolated MVR for this capture.
        if force_create:
            created = await mvr_service.repository.create_mvr_people(
                face_embedding=face_embedding,
                featured_individual_uuid=None,
                age_min=ml_result.get("age_min"),
                age_max=ml_result.get("age_max"),
                age_confidence=ml_result.get("age_confidence"),
                gender=ml_result.get("gender"),
                gender_confidence=ml_result.get("gender_confidence"),
                quality_score=float(ml_result.get("face_quality", 0.5) or 0.5),
                confidence_score=float(
                    ml_result.get("detection_confidence", 0.5) or 0.5
                ),
                face_quality=float(ml_result.get("face_quality", 0.5) or 0.5),
                auto_created=True,
                is_isolated=True,
            )
            created_uuid = await _verified_mvr_uuid(
                mvr_service, created.get("mvr_people_uuid")
            )
            return FaceIdentityResponse(
                success=True,
                matched=bool(created_uuid),
                mvr_people_uuid=created_uuid,
                similarity_score=1.0 if created_uuid else 0.0,
                total_candidates=0,
                created_new=bool(created_uuid),
                dedupe_reused_existing=False,
            )

        candidates = await mvr_service.find_similar_people(
            face_embedding=face_embedding,
            similarity_threshold=similarity_threshold,
            max_results=max_results,
        )

        verified_match: Optional[tuple[str, float]] = None
        for cand in candidates or []:
            cand_uuid = await _verified_mvr_uuid(
                mvr_service, cand.get("mvr_people_uuid")
            )
            if cand_uuid:
                verified_match = (
                    cand_uuid,
                    float(cand.get("similarity_score", 0.0) or 0.0),
                )
                break

        if verified_match:
            match_uuid, match_score = verified_match
            return FaceIdentityResponse(
                success=True,
                matched=True,
                mvr_people_uuid=match_uuid,
                similarity_score=match_score,
                total_candidates=len(candidates),
                created_new=False,
                dedupe_reused_existing=False,
            )

        if (
            create_if_missing
            and enable_dedupe_reuse
            and dedupe_similarity_threshold < similarity_threshold
        ):
            reuse_candidates = await mvr_service.find_similar_people(
                face_embedding=face_embedding,
                similarity_threshold=dedupe_similarity_threshold,
                max_results=1,
            )

            for reused in reuse_candidates or []:
                reused_uuid = await _verified_mvr_uuid(
                    mvr_service, reused.get("mvr_people_uuid")
                )
                if not reused_uuid:
                    continue
                reused_similarity = float(
                    reused.get("similarity_score", 0.0) or 0.0
                )
                return FaceIdentityResponse(
                    success=True,
                    matched=True,
                    mvr_people_uuid=reused_uuid,
                    similarity_score=reused_similarity,
                    total_candidates=1,
                    created_new=False,
                    dedupe_reused_existing=True,
                )

        if create_if_missing:
            created = await mvr_service.repository.create_mvr_people(
                face_embedding=face_embedding,
                featured_individual_uuid=None,
                age_min=ml_result.get("age_min"),
                age_max=ml_result.get("age_max"),
                age_confidence=ml_result.get("age_confidence"),
                gender=ml_result.get("gender"),
                gender_confidence=ml_result.get("gender_confidence"),
                quality_score=float(
                    ml_result.get("face_quality", 0.5) or 0.5
                ),
                confidence_score=float(
                    ml_result.get("detection_confidence", 0.5) or 0.5
                ),
                face_quality=float(
                    ml_result.get("face_quality", 0.5) or 0.5
                ),
                auto_created=True,
                is_isolated=True,
            )

            created_uuid = await _verified_mvr_uuid(
                mvr_service, created.get("mvr_people_uuid")
            )
            return FaceIdentityResponse(
                success=True,
                matched=bool(created_uuid),
                mvr_people_uuid=created_uuid,
                similarity_score=1.0 if created_uuid else 0.0,
                total_candidates=0,
                created_new=bool(created_uuid),
                dedupe_reused_existing=False,
            )

        return FaceIdentityResponse(
            success=True,
            matched=False,
            mvr_people_uuid=None,
            similarity_score=0.0,
            total_candidates=0,
            created_new=False,
            dedupe_reused_existing=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face identity lookup: {e}")
        raise HTTPException(status_code=500, detail=f"Identity lookup error: {str(e)}")

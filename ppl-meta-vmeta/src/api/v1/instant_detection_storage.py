"""
Instant Detection Storage API

Persists instant detection results into the VMeta database schema
(tracking_sessions, individuals, individual_video_appearances, individual_mvr_mapping).
Called by the Cameras service Celery task after each persisted detection cycle.
"""

import json
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, get_mvr_service
from services.mvr_service import MVRService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Request / Response models ----------


class BestFace(BaseModel):
    bbox: Optional[List[float]] = None
    confidence: Optional[float] = None


class AgeGender(BaseModel):
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    age_confidence: Optional[float] = None
    gender: Optional[str] = None
    gender_confidence: Optional[float] = None


class PersonObject(BaseModel):
    person_object_uuid: str
    mvr_person_uuid: Optional[str] = None
    mvr_created_new: bool = False
    face_count: int = 0
    avg_confidence: float = 0.5
    best_face: Optional[BestFace] = None
    age_gender: Optional[AgeGender] = None


class InstantDetectionPersistRequest(BaseModel):
    session_uuid: str
    camera_id: str
    cycle_timestamp: str
    person_objects: List[PersonObject] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)


class InstantDetectionPersistResponse(BaseModel):
    success: bool = True
    stored_individuals: int = 0
    new_individuals_created: int = 0
    existing_individuals_updated: int = 0
    mvr_records_promoted: int = 0
    appearances_created: int = 0


class TrackingSessionCreateRequest(BaseModel):
    session_uuid: str
    camera_id: str
    source_type: str = "instant_detection"
    user_id: str = "system"


class TrackingSessionCreateResponse(BaseModel):
    success: bool = True
    session_uuid: str


# ---------- Endpoints ----------


@router.post(
    "/instant-detection/create-session",
    response_model=TrackingSessionCreateResponse,
)
async def create_instant_detection_session(
    request: TrackingSessionCreateRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """Create a tracking session for an instant detection run."""
    try:
        pool = mvr_service.repository.pool
        async with pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO tracking_sessions (
                    session_uuid, user_id, collections,
                    start_time, end_time, status,
                    config_hash, algorithm_config,
                    source_type, camera_device_id,
                    created_at, started_at
                ) VALUES (
                    $1, $2, $3,
                    $4, $5, $6,
                    $7, $8,
                    $9, $10,
                    $11, $12
                )
                """,
                _uuid.UUID(request.session_uuid),
                request.user_id,
                [request.camera_id],
                now,
                now,
                "running",
                "instant_detection",
                json.dumps({"source": "instant_detection", "camera_id": request.camera_id}),
                request.source_type,
                request.camera_id,
                now,
                now,
            )

        return TrackingSessionCreateResponse(
            success=True,
            session_uuid=request.session_uuid,
        )
    except Exception as e:
        logger.error(f"Failed to create instant detection session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}",
        )


@router.post(
    "/instant-detection/complete-session/{session_uuid}",
)
async def complete_instant_detection_session(
    session_uuid: str,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """Mark a tracking session as completed."""
    try:
        pool = mvr_service.repository.pool
        async with pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            await conn.execute(
                """
                UPDATE tracking_sessions
                SET status = 'completed',
                    completed_at = $1,
                    end_time = $1
                WHERE session_uuid = $2
                  AND status = 'running'
                """,
                now,
                _uuid.UUID(session_uuid),
            )

        return {"success": True, "session_uuid": session_uuid}
    except Exception as e:
        logger.error(f"Failed to complete session {session_uuid}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete session: {e}",
        )


@router.post(
    "/instant-detection/persist",
    response_model=InstantDetectionPersistResponse,
)
async def persist_instant_detection(
    request: InstantDetectionPersistRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Persist instant detection results to the database.

    For each person object the endpoint:
      1. Finds or creates an Individual linked to the MVR identity.
      2. Creates an individual_video_appearance with a synthetic video UUID.
      3. Creates/updates the individual_mvr_mapping.
      4. Promotes isolated MVR records to first-class citizens.
      5. Increments session metrics.
    """
    pool = mvr_service.repository.pool

    new_created = 0
    existing_updated = 0
    promoted = 0
    appearances = 0

    session_id = _uuid.UUID(request.session_uuid)

    try:
        cycle_ts = datetime.fromisoformat(
            request.cycle_timestamp.replace("Z", "+00:00")
        )
    except Exception:
        cycle_ts = datetime.now(timezone.utc)

    # Deterministic synthetic video UUID per cycle
    synthetic_video_uuid = _uuid.uuid5(
        _uuid.NAMESPACE_URL,
        f"instant-detection:{request.camera_id}:{request.cycle_timestamp}",
    )

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for po in request.person_objects:
                    individual_uuid: Optional[_uuid.UUID] = None
                    is_new = False

                    mvr_uuid = (
                        _uuid.UUID(po.mvr_person_uuid)
                        if po.mvr_person_uuid
                        else None
                    )

                    # --- Resolve or create Individual ---
                    if mvr_uuid:
                        if po.mvr_created_new:
                            # New MVR was just created — create a new Individual
                            individual_uuid = await _create_individual(
                                conn, session_id, po, cycle_ts
                            )
                            is_new = True

                            # Link Individual ↔ MVR
                            await _create_mvr_mapping(
                                conn, individual_uuid, mvr_uuid, po.avg_confidence
                            )

                            # Promote MVR: set featured_individual, clear isolated flag
                            await _promote_mvr(conn, mvr_uuid, individual_uuid)
                            promoted += 1
                        else:
                            # Matched an existing MVR — try to reuse its Individual
                            row = await conn.fetchrow(
                                """
                                SELECT featured_individual_uuid
                                FROM mvr_people
                                WHERE mvr_people_uuid = $1
                                """,
                                mvr_uuid,
                            )
                            featured = row["featured_individual_uuid"] if row else None

                            if featured:
                                individual_uuid = featured
                                # Update stats on existing individual
                                await conn.execute(
                                    """
                                    UPDATE individuals
                                    SET total_appearances = COALESCE(total_appearances, 0) + 1,
                                        last_seen = $1,
                                        updated_at = $1
                                    WHERE individual_uuid = $2
                                    """,
                                    cycle_ts,
                                    individual_uuid,
                                )
                                existing_updated += 1
                            else:
                                # Legacy isolated MVR with no individual — backfill
                                individual_uuid = await _create_individual(
                                    conn, session_id, po, cycle_ts
                                )
                                is_new = True
                                await _create_mvr_mapping(
                                    conn, individual_uuid, mvr_uuid, po.avg_confidence
                                )
                                await _promote_mvr(conn, mvr_uuid, individual_uuid)
                                promoted += 1
                    else:
                        # No MVR identity — create unlinked Individual
                        individual_uuid = await _create_individual(
                            conn, session_id, po, cycle_ts
                        )
                        is_new = True

                    if is_new:
                        new_created += 1

                    # --- Create appearance record ---
                    representative_faces = None
                    if po.best_face:
                        representative_faces = json.dumps(
                            [{"bbox": po.best_face.bbox, "confidence": po.best_face.confidence}]
                        )

                    await conn.execute(
                        """
                        INSERT INTO individual_video_appearances (
                            individual_uuid, video_uuid, person_object_uuid,
                            start_timestamp, end_timestamp,
                            confidence, quality_score,
                            processing_method, source_session_uuid,
                            representative_faces, created_at
                        ) VALUES (
                            $1, $2, $3,
                            $4, $5,
                            $6, $7,
                            $8, $9,
                            $10, $11
                        )
                        ON CONFLICT (individual_uuid, video_uuid, person_object_uuid)
                        DO NOTHING
                        """,
                        individual_uuid,
                        synthetic_video_uuid,
                        _uuid.UUID(po.person_object_uuid),
                        cycle_ts,
                        cycle_ts,
                        po.avg_confidence,
                        po.avg_confidence,
                        "instant_detection",
                        session_id,
                        representative_faces,
                        cycle_ts,
                    )
                    appearances += 1

                # Update session metrics
                total_stored = new_created + existing_updated
                await conn.execute(
                    """
                    UPDATE tracking_sessions
                    SET individuals_found = COALESCE(individuals_found, 0) + $1,
                        person_objects_processed = COALESCE(person_objects_processed, 0) + $2,
                        completed_at = $3
                    WHERE session_uuid = $4
                    """,
                    total_stored,
                    len(request.person_objects),
                    cycle_ts,
                    session_id,
                )

        return InstantDetectionPersistResponse(
            success=True,
            stored_individuals=new_created + existing_updated,
            new_individuals_created=new_created,
            existing_individuals_updated=existing_updated,
            mvr_records_promoted=promoted,
            appearances_created=appearances,
        )

    except Exception as e:
        logger.error(f"Failed to persist instant detection results: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Persistence failed: {e}",
        )


# ---------- Internal helpers ----------


async def _create_individual(
    conn,
    session_id: _uuid.UUID,
    po: PersonObject,
    cycle_ts: datetime,
) -> _uuid.UUID:
    """Create a new Individual record for instant detection."""
    individual_uuid = _uuid.uuid4()
    individual_id = f"ind_{individual_uuid.hex[:8]}"

    person_objects_json = json.dumps([po.person_object_uuid])

    await conn.execute(
        """
        INSERT INTO individuals (
            individual_uuid, individual_id, confidence_score,
            spatial_signature, temporal_signature,
            source_type, created_by_session,
            total_appearances, first_seen, last_seen,
            created_at, updated_at,
            person_objects
        ) VALUES (
            $1, $2, $3,
            $4, $5,
            $6, $7,
            $8, $9, $10,
            $11, $12,
            $13
        )
        """,
        individual_uuid,
        individual_id,
        po.avg_confidence,
        json.dumps({}),
        json.dumps({}),
        "instant_detection",
        session_id,
        1,
        cycle_ts,
        cycle_ts,
        cycle_ts,
        cycle_ts,
        person_objects_json,
    )

    # Session-individual relationship
    await conn.execute(
        """
        INSERT INTO session_individuals (
            session_uuid, individual_uuid, processing_type, confidence_contribution
        ) VALUES ($1, $2, $3, $4)
        ON CONFLICT DO NOTHING
        """,
        session_id,
        individual_uuid,
        "new",
        po.avg_confidence,
    )

    return individual_uuid


async def _create_mvr_mapping(
    conn,
    individual_uuid: _uuid.UUID,
    mvr_uuid: _uuid.UUID,
    quality_score: float,
) -> None:
    """Create an individual_mvr_mapping entry with link_method='instant_detection'."""
    await conn.execute(
        """
        INSERT INTO individual_mvr_mapping (
            individual_uuid, mvr_people_uuid,
            quality_score, confidence_score, similarity_score,
            is_representative, link_method,
            linked_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (individual_uuid, mvr_people_uuid) DO NOTHING
        """,
        individual_uuid,
        mvr_uuid,
        quality_score,
        quality_score,
        None,
        False,
        "instant_detection",
        datetime.now(timezone.utc),
    )


async def _promote_mvr(
    conn,
    mvr_uuid: _uuid.UUID,
    individual_uuid: _uuid.UUID,
) -> None:
    """Promote an isolated MVR to first-class by linking an individual."""
    await conn.execute(
        """
        UPDATE mvr_people
        SET featured_individual_uuid = $1,
            is_isolated = FALSE,
            total_linked_individuals = COALESCE(total_linked_individuals, 0) + 1,
            updated_at = NOW()
        WHERE mvr_people_uuid = $2
          AND (featured_individual_uuid IS NULL OR is_isolated = TRUE)
        """,
        individual_uuid,
        mvr_uuid,
    )

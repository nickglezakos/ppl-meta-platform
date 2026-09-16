"""
Instant Detection Storage API

Persists instant detection results into the VMeta database schema
(tracking_sessions, individuals, individual_video_appearances, individual_mvr_mapping).
Called by the Cameras service Celery task after each persisted detection cycle.
"""

import json
import logging
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, get_current_user_or_internal_service, get_mvr_service
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


class VelocityPxMs(BaseModel):
    x: float = 0.0
    y: float = 0.0


class PersonObject(BaseModel):
    person_object_uuid: str
    mvr_person_uuid: Optional[str] = None
    mvr_created_new: bool = False
    face_count: int = 0
    avg_confidence: float = 0.5
    best_face: Optional[BestFace] = None
    age_gender: Optional[AgeGender] = None
    # Instant-detection velocity (optional; stripped previously by strict schema)
    speed_mps: Optional[float] = None
    velocity_px_ms: Optional[VelocityPxMs] = None
    gait_band: Optional[str] = None
    samples: Optional[int] = None
    scale_face_height_m: Optional[float] = None


class InstantDetectionPersistRequest(BaseModel):
    session_uuid: str
    camera_id: str
    cycle_timestamp: str
    person_objects: List[PersonObject] = Field(default_factory=list)
    body_persons: List[Dict[str, Any]] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    crowd_velocity_mps: Optional[float] = None
    max_person_speed_mps: Optional[float] = None
    crowd_person_count: Optional[int] = None


class InstantDetectionPersistResponse(BaseModel):
    success: bool = True
    stored_individuals: int = 0
    new_individuals_created: int = 0
    existing_individuals_updated: int = 0
    mvr_records_promoted: int = 0
    appearances_created: int = 0
    body_mvr_created: int = 0


class InstantDetectionPersistBatchRequest(BaseModel):
    items: List[InstantDetectionPersistRequest] = Field(default_factory=list)


class InstantDetectionPersistBatchResponse(BaseModel):
    success: bool = True
    cycles_flushed: int = 0
    stored_individuals: int = 0
    new_individuals_created: int = 0
    existing_individuals_updated: int = 0
    mvr_records_promoted: int = 0
    appearances_created: int = 0
    body_mvr_created: int = 0


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
    current_user: dict = Depends(get_current_user_or_internal_service),
):
    """Create a tracking session for an instant detection run."""
    requester = current_user.get("email") or current_user.get("service_name") or "unknown"
    try:
        pool = mvr_service.repository.pool
        async with pool.acquire() as conn:
            now = datetime.utcnow()
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
                now + timedelta(seconds=1),
                "running",
                "instant_detection",
                json.dumps({
                    "source": "instant_detection",
                    "camera_id": request.camera_id,
                    "max_gap_seconds": 5,
                    "iou_threshold": 0.5,
                    "min_overlap_confidence": 0.3,
                }),
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
        logger.error(
            "Failed to create instant detection session for %s: %s",
            requester,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}",
        ) from e


@router.post(
    "/instant-detection/complete-session/{session_uuid}",
)
async def complete_instant_detection_session(
    session_uuid: str,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user_or_internal_service),
):
    """Mark a tracking session as completed."""
    requester = current_user.get("email") or current_user.get("service_name") or "unknown"
    try:
        pool = mvr_service.repository.pool
        async with pool.acquire() as conn:
            now = datetime.utcnow()
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
        logger.error(
            "Failed to complete session %s for %s: %s",
            session_uuid,
            requester,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete session: {e}",
        ) from e


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
    requester = current_user.get("email") or current_user.get("service_name") or "unknown"
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                counts = await _persist_requests(conn, [request])

        return InstantDetectionPersistResponse(
            success=True,
            stored_individuals=counts["stored_individuals"],
            new_individuals_created=counts["new_individuals_created"],
            existing_individuals_updated=counts["existing_individuals_updated"],
            mvr_records_promoted=counts["mvr_records_promoted"],
            appearances_created=counts["appearances_created"],
            body_mvr_created=counts.get("body_mvr_created", 0),
        )

    except Exception as e:
        logger.error(
            "Failed to persist instant detection results for %s: %s",
            requester,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Persistence failed: {e}",
        ) from e


@router.post(
    "/instant-detection/persist-batch",
    response_model=InstantDetectionPersistBatchResponse,
)
async def persist_instant_detection_batch(
    request: InstantDetectionPersistBatchRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user_or_internal_service),
):
    requester = current_user.get("email") or current_user.get("service_name") or "unknown"
    if not request.items:
        return InstantDetectionPersistBatchResponse(success=True, cycles_flushed=0)

    pool = mvr_service.repository.pool
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                counts = await _persist_requests(conn, request.items)

        return InstantDetectionPersistBatchResponse(
            success=True,
            cycles_flushed=len(request.items),
            stored_individuals=counts["stored_individuals"],
            new_individuals_created=counts["new_individuals_created"],
            existing_individuals_updated=counts["existing_individuals_updated"],
            mvr_records_promoted=counts["mvr_records_promoted"],
            appearances_created=counts["appearances_created"],
            body_mvr_created=counts.get("body_mvr_created", 0),
        )
    except Exception as e:
        logger.error(
            "Failed to persist instant detection batch for %s: %s",
            requester,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch persistence failed: {e}",
        ) from e


# ---------- Internal helpers ----------


def _movement_pattern_for_person(po: PersonObject) -> Optional[str]:
    """Build recording-compatible movement_pattern JSON for one appearance."""
    if po.speed_mps is None and po.velocity_px_ms is None and not po.gait_band:
        return None

    px_per_s = None
    if po.velocity_px_ms is not None:
        mag = (float(po.velocity_px_ms.x) ** 2 + float(po.velocity_px_ms.y) ** 2) ** 0.5
        px_per_s = round(mag * 1000.0, 4)

    return json.dumps(
        {
            "movement_statistics": {
                "average_speed_mps": po.speed_mps,
                "average_speed_pixels_per_second": px_per_s,
                "gait_band": po.gait_band,
                "samples": po.samples,
                "scale": {
                    "method": "face_height",
                    "face_height_m": po.scale_face_height_m or 0.20,
                },
            }
        }
    )


async def _persist_requests(conn, requests: List[InstantDetectionPersistRequest]) -> Dict[str, int]:
    from services import mvr_people_body_service as body_svc

    total_new_created = 0
    total_existing_updated = 0
    total_promoted = 0
    total_appearances = 0
    total_body_mvr = 0

    for request in requests:
        session_id = _uuid.UUID(request.session_uuid)

        try:
            cycle_ts = datetime.fromisoformat(
                request.cycle_timestamp.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            cycle_ts = datetime.utcnow()

        synthetic_video_uuid = _uuid.uuid5(
            _uuid.NAMESPACE_URL,
            f"instant-detection:{request.camera_id}:{request.cycle_timestamp}",
        )

        new_created = 0
        existing_updated = 0
        promoted = 0
        appearances = 0

        for po in request.person_objects:
            individual_uuid: Optional[_uuid.UUID] = None
            is_new = False

            mvr_uuid = _uuid.UUID(po.mvr_person_uuid) if po.mvr_person_uuid else None

            if mvr_uuid:
                if po.mvr_created_new:
                    individual_uuid = await _create_individual(conn, session_id, po, cycle_ts)
                    is_new = True
                    await _create_mvr_mapping(conn, individual_uuid, mvr_uuid, po.avg_confidence)
                    await _promote_mvr(conn, mvr_uuid, individual_uuid)
                    promoted += 1
                else:
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
                        temporal_patch = {}
                        if po.speed_mps is not None:
                            temporal_patch = {
                                "last_speed_mps": po.speed_mps,
                                "gait_band": po.gait_band,
                            }
                        await conn.execute(
                            """
                            UPDATE individuals
                            SET total_appearances = COALESCE(total_appearances, 0) + 1,
                                last_seen = $1,
                                updated_at = $1,
                                temporal_signature = CASE
                                    WHEN $3::text IS NULL THEN temporal_signature
                                    ELSE COALESCE(temporal_signature, '{}'::jsonb) || $3::jsonb
                                END
                            WHERE individual_uuid = $2
                            """,
                            cycle_ts,
                            individual_uuid,
                            json.dumps(temporal_patch) if temporal_patch else None,
                        )
                        existing_updated += 1
                    else:
                        individual_uuid = await _create_individual(conn, session_id, po, cycle_ts)
                        is_new = True
                        await _create_mvr_mapping(conn, individual_uuid, mvr_uuid, po.avg_confidence)
                        await _promote_mvr(conn, mvr_uuid, individual_uuid)
                        promoted += 1
            else:
                individual_uuid = await _create_individual(conn, session_id, po, cycle_ts)
                is_new = True

            if is_new:
                new_created += 1

            representative_faces = None
            if po.best_face:
                representative_faces = json.dumps(
                    [{"bbox": po.best_face.bbox, "confidence": po.best_face.confidence}]
                )

            movement_pattern = _movement_pattern_for_person(po)

            await conn.execute(
                """
                INSERT INTO individual_video_appearances (
                    individual_uuid, video_uuid, person_object_uuid,
                    start_timestamp, end_timestamp,
                    confidence, quality_score,
                    processing_method, source_session_uuid,
                    representative_faces, movement_pattern, created_at
                ) VALUES (
                    $1, $2, $3,
                    $4, $5,
                    $6, $7,
                    $8, $9,
                    $10, $11::jsonb, $12
                )
                ON CONFLICT (individual_uuid, video_uuid, person_object_uuid)
                DO UPDATE SET
                    movement_pattern = COALESCE(EXCLUDED.movement_pattern, individual_video_appearances.movement_pattern),
                    confidence = EXCLUDED.confidence,
                    quality_score = EXCLUDED.quality_score
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
                movement_pattern,
                cycle_ts,
            )
            appearances += 1

        total_stored = new_created + existing_updated
        if request.person_objects or request.crowd_velocity_mps is not None:
            crowd_patch = {
                "last_crowd_velocity_mps": request.crowd_velocity_mps,
                "last_max_person_speed_mps": request.max_person_speed_mps,
                "last_crowd_person_count": request.crowd_person_count,
            }
            await conn.execute(
                """
                UPDATE tracking_sessions
                SET individuals_found = COALESCE(individuals_found, 0) + $1,
                    person_objects_processed = COALESCE(person_objects_processed, 0) + $2,
                    completed_at = $3,
                    algorithm_config = COALESCE(algorithm_config, '{}'::jsonb) || $5::jsonb
                WHERE session_uuid = $4
                """,
                total_stored,
                len(request.person_objects),
                cycle_ts,
                session_id,
                json.dumps({k: v for k, v in crowd_patch.items() if v is not None}),
            )

        # Body persons: same flush batch as faces → mvr_people_body
        if request.body_persons:
            body_result = await body_svc.materialize_from_body_persons(
                conn,
                request.body_persons,
                media_id=str(synthetic_video_uuid),
                camera_id=request.camera_id,
                session_uuid=request.session_uuid,
            )
            total_body_mvr += int(body_result.get("count") or 0)

        total_new_created += new_created
        total_existing_updated += existing_updated
        total_promoted += promoted
        total_appearances += appearances

    return {
        "stored_individuals": total_new_created + total_existing_updated,
        "new_individuals_created": total_new_created,
        "existing_individuals_updated": total_existing_updated,
        "mvr_records_promoted": total_promoted,
        "appearances_created": total_appearances,
        "body_mvr_created": total_body_mvr,
    }


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

    # Extract demographics from age_gender if available
    gender_est = po.age_gender.gender if po.age_gender and po.age_gender.gender else None
    age_est = po.age_gender.age_min if po.age_gender and po.age_gender.age_min is not None else None

    temporal_signature: Dict[str, Any] = {}
    if po.speed_mps is not None:
        temporal_signature = {
            "last_speed_mps": po.speed_mps,
            "gait_band": po.gait_band,
        }

    # Prefer full schema; fall back for minimal Lima/installer DBs.
    insert_attempts = [
        (
            """
            INSERT INTO individuals (
                individual_uuid, individual_id, confidence_score,
                spatial_signature, temporal_signature,
                source_type, created_by_session,
                total_appearances, first_seen, last_seen,
                created_at, updated_at,
                person_objects,
                gender_estimate, age_estimate
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            )
            """,
            (
                individual_uuid,
                individual_id,
                po.avg_confidence,
                json.dumps({}),
                json.dumps(temporal_signature),
                "instant_detection",
                session_id,
                1,
                cycle_ts,
                cycle_ts,
                cycle_ts,
                cycle_ts,
                person_objects_json,
                gender_est,
                age_est,
            ),
        ),
        (
            """
            INSERT INTO individuals (
                individual_uuid, individual_id, confidence_score,
                spatial_signature, temporal_signature,
                source_type, created_by_session,
                created_at, updated_at,
                gender_estimate, age_estimate
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            """,
            (
                individual_uuid,
                individual_id,
                po.avg_confidence,
                json.dumps({}),
                json.dumps(temporal_signature),
                "instant_detection",
                session_id,
                cycle_ts,
                cycle_ts,
                gender_est,
                age_est,
            ),
        ),
        (
            """
            INSERT INTO individuals (
                individual_uuid, individual_id, confidence_score,
                spatial_signature, temporal_signature,
                source_type, created_by_session,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9
            )
            """,
            (
                individual_uuid,
                individual_id,
                po.avg_confidence,
                json.dumps({}),
                json.dumps(temporal_signature),
                "instant_detection",
                session_id,
                cycle_ts,
                cycle_ts,
            ),
        ),
        (
            """
            INSERT INTO individuals (
                individual_uuid, individual_id, confidence_score,
                spatial_signature, temporal_signature,
                source_type, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8
            )
            """,
            (
                individual_uuid,
                individual_id,
                po.avg_confidence,
                json.dumps({}),
                json.dumps(temporal_signature),
                "instant_detection",
                cycle_ts,
                cycle_ts,
            ),
        ),
    ]

    last_exc: Optional[Exception] = None
    for sql, params in insert_attempts:
        try:
            await conn.execute(sql, *params)
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "does not exist" in msg or "undefinedcolumn" in msg:
                continue
            raise
    if last_exc is not None:
        raise last_exc

    # Session-individual relationship (optional on minimal schemas)
    try:
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
    except Exception as exc:
        if "session_individuals" not in str(exc).lower() and "does not exist" not in str(exc).lower():
            raise

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

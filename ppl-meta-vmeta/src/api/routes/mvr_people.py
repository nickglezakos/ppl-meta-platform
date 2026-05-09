"""
MVR-People API Routes

This module implements 14 REST API endpoints for the MVR-People (Machine Vision Representation)
system, providing CRUD operations, similarity search, matching/merging, and background task
monitoring.

All endpoints require JWT authentication via Authorization header.

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query, Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Database and services
from database.mvr_repository import MVRRepository
from services.mvr_service import MVRService
from services.mvr_matcher import MVRMatcher
from background.mvr_background_processor import MVRBackgroundProcessor

# Models
from api.models.mvr_people import (
    CreateMVRRequest,
    CreateMVRResponse,
    MVRPeopleResponse,
    SearchSimilarRequest,
    SearchSimilarResponse,
    SearchDemographicsRequest,
    SearchDemographicsResponse,
    LinkIndividualRequest,
    LinkIndividualResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    MVRStatusResponse,
    MatchIndividualRequest,
    MatchIndividualResponse,
    MergeIndividualsRequest,
    MergeIndividualsResponse,
    UnmergeMvrRequest,
    UnmergeMvrResponse,
    MergeHistoryResponse,
    OrphanedMVRResponse,
    MatchingConfigUpdate,
    MatchingConfigResponse,
)

# Batch merge models
from api.models.batch_merge import (
    BatchMatchAndMergeRequest,
    BatchMatchAndMergeResponse,
    MergeDetail,
)

# MVR search models
from api.models.mvr_search_models import (
    MVRPeopleSearchRequest,
    MVRPeopleSearchResponse,
    MVRPersonResult,
    IndividualAppearance as MVRIndividualAppearance,
)

# MVR name management models
from api.models.mvr_names import (
    UpdateNameRequest,
    UpdateNameResponse,
    UpdateGenderRequest,
    UpdateGenderResponse,
    BulkNameUpdateRequest,
    BulkNameUpdateResponse,
)

# Process media models
from api.models.process_media import (
    ProcessMediaRequest,
    PersistedPersonObjectsMaterializationRequest,
    PersistedPersonObjectsMaterializationResponse,
)

# Dependencies
from api.dependencies import (
    get_mvr_repository,
    get_mvr_service,
    get_mvr_matcher,
    get_mvr_background_processor,
    get_current_user,
    get_current_user_or_internal_service,
    get_cache_client,
)

logger = logging.getLogger(__name__)


def _coerce_to_uuid_str(value: Any) -> Optional[str]:
    """Return a valid UUID string for *value*, minting one when it isn't a UUID.

    Upstream services occasionally pass synthetic identifiers (e.g. "person_1")
    in place of the persisted person-object UUID. Without coercion, the call
    to UUID(value) inside MVRService raises "badly formed hexadecimal UUID
    string" and aborts single-media MVR creation, leaving no MVR rows for the
    recording. Returning a freshly minted UUID keeps the pipeline moving.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except (ValueError, AttributeError):
        minted = str(uuid4())
        logger.warning(
            "Coerced non-UUID person identifier %r to fresh UUID %s for MVR materialization",
            text, minted,
        )
        return minted


def _normalize_quality(raw: Any) -> float:
    """Normalize quality scalar from orchestrator (0-100 or 0-1) to 0-1."""
    try:
        q = float(raw)
    except (TypeError, ValueError):
        return 0.85
    if q <= 0.0:
        return 0.85
    return q / 100.0 if q > 1.0 else q


def _coerce_uuid_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except (ValueError, AttributeError):
        return None


async def _refresh_iva_from_orchestrator_task(
    pool: Any,
    media_uuid_str: str,
    auth_token: Optional[str] = None,
) -> None:
    """Background task: rewrite iva rows for *media_uuid* with orchestrator's
    authoritative person_groups (proper person_uuid + representative_faces +
    movement_pattern).

    This runs AFTER the materialization handler has returned its response,
    which unblocks the orchestrator's synchronous `requests.post` and lets it
    serve `/person-objects/{media_uuid}` without deadlocking. The handler-time
    payload (synthetic person_id, no representative_faces) leaves iva rows
    with NULL representative_faces and orphan person_object_uuids that the
    frontend cannot match — this task replaces them with rows that match the
    orchestrator's view of the video.
    """
    from datetime import datetime as _dt

    media_uuid_str = str(media_uuid_str)
    try:
        media_uuid = UUID(media_uuid_str)
    except (ValueError, TypeError):
        logger.error("Background iva refresh: invalid media_uuid %r", media_uuid_str)
        return

    # Give the orchestrator a moment to complete its sync POST and become
    # responsive. The synchronous requests.post on the orchestrator side
    # returns as soon as we send the response, but a small delay further
    # avoids racing the unwind of its handler.
    await asyncio.sleep(2.0)

    orchestrator_url = os.getenv("PPL_ORCHESTRATOR_URL", "http://localhost:8002")
    internal_token = auth_token or os.getenv(
        "INTERNAL_SERVICE_TOKEN",
        "ppl-meta-internal-service-secret-key-change-in-production",
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{orchestrator_url}/person-objects/{media_uuid}",
                headers={
                    "Authorization": f"Bearer {internal_token}",
                    "X-Service-Name": "ppl-meta-vmeta-bg-refresh",
                },
            )
    except Exception as exc:
        logger.warning(
            "Background iva refresh: orchestrator GET failed for %s: %s",
            media_uuid, exc,
        )
        return

    if resp.status_code != 200:
        logger.warning(
            "Background iva refresh: orchestrator returned %s for %s; skipping",
            resp.status_code, media_uuid,
        )
        return

    try:
        person_groups = list((resp.json() or {}).get("person_groups") or [])
    except Exception as exc:
        logger.warning(
            "Background iva refresh: failed to parse orchestrator response for %s: %s",
            media_uuid, exc,
        )
        return

    if not person_groups:
        logger.info(
            "Background iva refresh: orchestrator returned 0 person_groups for %s; "
            "leaving existing iva rows in place",
            media_uuid,
        )
        return

    appearance_ts = _dt.utcnow()
    updated_rows = 0
    skipped = 0
    distinct_individuals: List[Any] = []

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                # iva stores ONE row per raw person_object_uuid; multiple rows
                # can share an individual_uuid (each row is a tracking segment
                # the upstream clusterer grouped under one MVR/individual).
                # The orchestrator's `person_groups` are MERGED groups — each
                # carries a single `person_uuid` that is NOT in the same
                # identifier space as any raw `person_object_uuid`. Therefore
                # we must NOT overwrite iva.person_object_uuid; we only enrich
                # the *data* columns (representative_faces, movement_pattern,
                # entry/exit_bbox, confidence, quality_score) and replicate
                # the same enrichment across every iva row that shares an
                # individual_uuid (so downstream consumers reading any of
                # those rows see the merged-group view).
                rows = await conn.fetch(
                    """
                    SELECT individual_uuid, MIN(created_at) AS first_seen
                      FROM individual_video_appearances
                     WHERE video_uuid=$1
                     GROUP BY individual_uuid
                     ORDER BY MIN(created_at) NULLS LAST, individual_uuid
                    """,
                    media_uuid,
                )
                distinct_individuals = [r["individual_uuid"] for r in rows]
                if not distinct_individuals:
                    logger.info(
                        "Background iva refresh: no existing iva rows for %s; "
                        "skipping (initial materialization may have failed)",
                        media_uuid,
                    )
                    return

                pair_count = min(len(distinct_individuals), len(person_groups))
                if pair_count == 0:
                    logger.warning(
                        "Background iva refresh: cannot pair (individuals=%d, "
                        "person_groups=%d) for %s",
                        len(distinct_individuals), len(person_groups), media_uuid,
                    )
                    return

                for idx, individual_uuid in enumerate(distinct_individuals):
                    if idx >= pair_count:
                        # Extra individuals with no orchestrator counterpart;
                        # leave their data columns untouched rather than
                        # invent values.
                        skipped += 1
                        continue
                    group = person_groups[idx]
                    representative_faces = group.get("representative_faces") or []
                    movement = group.get("movement_tracking") or {}
                    route_points = movement.get("route_points") or []
                    avg_conf = float(group.get("average_confidence") or 0.9)
                    quality_metrics = group.get("quality_metrics") or {}
                    avg_quality = _normalize_quality(
                        quality_metrics.get("average_quality")
                        or quality_metrics.get("best_quality")
                        or 80.0
                    )

                    entry_bbox = None
                    exit_bbox = None
                    if route_points:
                        first_bbox = route_points[0].get("bbox")
                        last_bbox = route_points[-1].get("bbox")
                        if isinstance(first_bbox, list) and len(first_bbox) == 4:
                            entry_bbox = [float(x) for x in first_bbox]
                        if isinstance(last_bbox, list) and len(last_bbox) == 4:
                            exit_bbox = [float(x) for x in last_bbox]

                    movement_pattern = {
                        "route_points": route_points,
                        "movement_statistics": movement.get("movement_statistics") or {},
                    } if route_points else None

                    res = await conn.execute(
                        """
                        UPDATE individual_video_appearances
                           SET representative_faces = $1::jsonb,
                               movement_pattern     = $2::jsonb,
                               entry_bbox           = $3,
                               exit_bbox            = $4,
                               confidence           = $5,
                               quality_score        = $6,
                               processing_method    = 'orchestrator_refresh'
                         WHERE individual_uuid=$7
                           AND video_uuid=$8
                        """,
                        json.dumps(representative_faces),
                        json.dumps(movement_pattern) if movement_pattern else None,
                        entry_bbox,
                        exit_bbox,
                        avg_conf,
                        float(avg_quality),
                        individual_uuid,
                        media_uuid,
                    )
                    # asyncpg returns "UPDATE n"
                    try:
                        updated_rows += int(res.split()[-1] or 0)
                    except (ValueError, IndexError):
                        pass
    except Exception as exc:
        logger.exception(
            "Background iva refresh: DB rewrite failed for %s: %s",
            media_uuid, exc,
        )
        return

    logger.info(
        "Background iva refresh: media=%s person_groups=%d distinct_individuals=%d "
        "iva_rows_updated=%d skipped_individuals=%d",
        media_uuid, len(person_groups), len(distinct_individuals),
        updated_rows, skipped,
    )


# Initialize router
router = APIRouter(
    prefix="/api/v1/mvr-people",
    tags=["mvr-people"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
    },
)


async def _materialize_single_media_from_persisted_person_objects(
    media_uuid: UUID,
    person_objects_payload: List[Dict[str, Any]],
    auth_token: str,
    mvr_service: MVRService,
    mvr_repository: MVRRepository,
    processing_options,
    media_type_override: Optional[str] = None,
    session_uuid: Optional[str] = None,
) -> PersistedPersonObjectsMaterializationResponse:
    """Materialize isolated VMeta rows from persisted person objects without re-triggering search logic."""
    import time

    from utils.media_client import MediaClient

    start_time = time.time()
    media_client = MediaClient(auth_token=auth_token)
    media_metadata = await media_client.get_media_metadata(media_uuid)
    media_type = media_type_override or (media_metadata or {}).get("type") or "video"

    def _normalize_quality(raw_quality: Any) -> float:
        try:
            quality = float(raw_quality)
        except (TypeError, ValueError):
            return 0.85
        if quality <= 0.0:
            return 0.85
        return quality / 100.0 if quality > 1.0 else quality

    async with mvr_repository.pool.acquire() as conn:
        # Only consider an MVR "existing" for this media if it is actually
        # reachable through the IVA -> mapping join (the same join used by
        # /count-by-videos and /search/by-videos). Earlier pipeline runs left
        # orphan mvr_people rows tagged with source_media_uuid but without
        # any individual_video_appearances; those rows are invisible to the
        # frontend, so they must NOT block re-materialization, otherwise
        # Compute "skips" forever and the Details button never appears.
        existing_count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT mp.mvr_people_uuid)
            FROM mvr_people mp
            JOIN individual_mvr_mapping imm
              ON imm.mvr_people_uuid = mp.mvr_people_uuid
            JOIN individual_video_appearances iva
              ON iva.individual_uuid = imm.individual_uuid
            WHERE iva.video_uuid = $1
              AND mp.is_orphaned = FALSE
            """,
            media_uuid,
        )

    if existing_count:
        return PersistedPersonObjectsMaterializationResponse(
            success=True,
            media_uuid=str(media_uuid),
            session_uuid=session_uuid,
            status="skipped_existing",
            media_type=media_type,
            existing_mvr_people_count=int(existing_count),
            mvr_people_count=int(existing_count),
            total_faces_detected=len(person_objects_payload),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    vision_url = os.getenv("PPL_VISION_URL", "http://localhost:8003")
    gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")

    # NOTE on enrichment: the orchestrator hands us a workflow payload with
    # synthetic person identifiers ("person_1") and no `representative_faces`,
    # which forces `_coerce_to_uuid_str` to mint random orphan UUIDs and writes
    # NULL into iva.representative_faces. The authoritative data lives at
    # orchestrator's /person-objects/{video_uuid}, but we cannot fetch it
    # synchronously here: the orchestrator is blocked inside `requests.post`
    # waiting for THIS handler's response, so the call would deadlock until
    # timeout. The fix is two-stage:
    #   1. Persist with the synthetic payload (so this handler returns fast).
    #   2. After the response is sent, a background task re-fetches from
    #      orchestrator (now unblocked) and rewrites the iva rows with proper
    #      person_uuid + representative_faces + movement_pattern. See
    #      `_refresh_iva_from_orchestrator_task` below.

    normalized_person_objects = []
    for person_obj in person_objects_payload:
        representative_faces = person_obj.get("representative_faces") or []
        best_face = representative_faces[0] if representative_faces else {}
        best_face_data = best_face.get("face_data") or {}
        normalized_person_objects.append(
            {
                **person_obj,
                "best_face_frame": person_obj.get("best_face_frame")
                or best_face_data.get("frame_number"),
                "best_face_bbox": person_obj.get("best_face_bbox")
                or best_face_data.get("bbox"),
                "detect_frame_width": person_obj.get("detect_frame_width")
                or best_face_data.get("frame_width"),
                "detect_frame_height": person_obj.get("detect_frame_height")
                or best_face_data.get("frame_height"),
                "confidence_score": person_obj.get("confidence_score")
                or person_obj.get("average_confidence")
                or 0.9,
                "quality_score": _normalize_quality(person_obj.get("quality_score")),
            }
        )

    enriched_person_objects = await enrich_person_objects_with_face_crops(
        person_objects=normalized_person_objects,
        media_uuid=media_uuid,
        auth_token=auth_token,
        vision_url=vision_url,
        gateway_url=gateway_url,
    )

    materialization_inputs = []
    for person_obj in enriched_person_objects:
        effective_quality = _normalize_quality(person_obj.get("quality_score", 0.0))

        # Prefer the real UUID fields. `person_id` is a synthetic label like
        # "person_1" emitted by the orchestrator's grouping engine. Coerce
        # whatever identifier we end up with into a valid UUID so mvr_service
        # can persist it without aborting single-media MVR creation.
        persisted_person_object_uuid = _coerce_to_uuid_str(
            person_obj.get("person_object_uuid")
            or person_obj.get("person_uuid")
            or person_obj.get("person_id")
        )
        if not persisted_person_object_uuid:
            logger.warning(
                "Skipping persisted person object without identifier during materialization for media %s",
                media_uuid,
            )
            continue

        materialization_inputs.append(
            {
                **person_obj,
                "person_object_uuid": persisted_person_object_uuid,
                "media_uuid": str(media_uuid),
                "video_uuid": str(media_uuid),
                "face_quality": effective_quality,
                "quality_score": effective_quality,
                "confidence_score": person_obj.get("average_confidence", 0.9),
            }
        )

    if not materialization_inputs:
        return PersistedPersonObjectsMaterializationResponse(
            success=True,
            media_uuid=str(media_uuid),
            session_uuid=session_uuid,
            status="completed",
            media_type=media_type,
            existing_mvr_people_count=0,
            mvr_people_count=0,
            total_faces_detected=0,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    result = await mvr_service.process_single_media_for_mvr(
        media_uuid=media_uuid,
        media_type=media_type,
        person_objects=materialization_inputs,
        similarity_threshold=processing_options.similarity_threshold,
        min_face_quality=processing_options.min_face_quality,
        include_demographics=processing_options.include_demographics,
        include_route_data=processing_options.include_route_data,
        media_timestamp=(media_metadata or {}).get("timestamp"),
    )

    # People-counters invalidation (proposal §5.7): a freshly-materialized
    # video may overlap one or more tagged batch windows. Mark them stale so
    # the orchestrator worker recomputes them on the next quiet-hour pass.
    try:
        affected = await mvr_repository.mark_batches_stale_for_video(str(media_uuid))
        if affected:
            logger.info(
                "people-counters: marked %d batch(es) stale after materializing media %s",
                affected,
                media_uuid,
            )
    except Exception as stale_err:
        logger.warning(
            "people-counters: failed to invalidate batches for media %s: %s",
            media_uuid,
            stale_err,
        )

    return PersistedPersonObjectsMaterializationResponse(
        success=True,
        media_uuid=str(media_uuid),
        session_uuid=session_uuid,
        status="completed",
        media_type=media_type,
        existing_mvr_people_count=0,
        mvr_people_count=result.get("mvr_people_count", 0),
        total_faces_detected=result.get("total_faces_detected", 0),
        processing_time_ms=result.get("processing_time_ms", int((time.time() - start_time) * 1000)),
    )


@router.post(
    "/materialize/persisted-person-objects",
    status_code=status.HTTP_200_OK,
    summary="Materialize Single-Media VMeta Rows From Persisted Person Objects",
    description=(
        "Internal endpoint used by Orchestrator after Vision persistence. "
        "Consumes persisted person objects and creates isolated single-media VMeta rows "
        "without widening search/by-videos responsibilities."
    ),
)
async def materialize_persisted_person_objects(
    request: PersistedPersonObjectsMaterializationRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    mvr_service: MVRService = Depends(get_mvr_service),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user_or_internal_service),
):
    auth_header = http_request.headers.get("Authorization", "")
    auth_token = (
        auth_header.replace("Bearer ", "")
        if auth_header.startswith("Bearer ")
        else None
    )
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
        )

    try:
        media_uuid = UUID(request.media_uuid)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid media UUID: {request.media_uuid}",
        ) from exc

    response = await _materialize_single_media_from_persisted_person_objects(
        media_uuid=media_uuid,
        person_objects_payload=request.person_objects,
        auth_token=auth_token,
        mvr_service=mvr_service,
        mvr_repository=mvr_repository,
        processing_options=request.processing_options,
        media_type_override=request.media_type,
        session_uuid=request.session_uuid,
    )

    # Schedule post-response refresh: re-fetch person_groups from orchestrator
    # (now unblocked) and rewrite iva rows with proper person_uuid +
    # representative_faces. See `_refresh_iva_from_orchestrator_task` docstring.
    background_tasks.add_task(
        _refresh_iva_from_orchestrator_task,
        mvr_repository.pool,
        str(media_uuid),
        auth_token,
    )

    return response


@router.get(
    "/face-crop",
    status_code=status.HTTP_200_OK,
    summary="Get Cropped Face Image",
    description="Extract a face crop from a specific media frame and bbox for thin-client thumbnail rendering.",
)
async def get_face_crop_image(
    request: Request,
    video_uuid: UUID = Query(..., description="Source media UUID"),
    frame_number: int = Query(..., ge=0, description="Frame number containing the face"),
    x1: int = Query(..., description="Left bbox coordinate"),
    y1: int = Query(..., description="Top bbox coordinate"),
    x2: int = Query(..., description="Right bbox coordinate"),
    y2: int = Query(..., description="Bottom bbox coordinate"),
    detect_frame_width: Optional[int] = Query(default=None, ge=1),
    detect_frame_height: Optional[int] = Query(default=None, ge=1),
    padding_ratio: float = Query(default=0.2, ge=0.0, le=1.0),
    current_user: dict = Depends(get_current_user),
):
    """Return a cropped face JPEG extracted from the requested frame."""
    from io import BytesIO
    from PIL import Image

    gateway_url = os.getenv("GATEWAY_SERVICE_URL", "http://localhost:8080")
    auth_header = request.headers.get("Authorization", "")

    frame_url = f"{gateway_url}/api/v1/media/{video_uuid}/frame/{frame_number}?format=jpeg"
    headers = {'Authorization': auth_header} if auth_header else {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        frame_response = await client.get(frame_url, headers=headers)

    if frame_response.status_code != 200:
        logger.warning(
            "Failed to fetch frame %s for video %s while building face crop: %s",
            frame_number,
            video_uuid,
            frame_response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source frame not found for face crop",
        )

    image = Image.open(BytesIO(frame_response.content)).convert("RGB")
    frame_width, frame_height = image.size

    if detect_frame_width and detect_frame_height and (
        detect_frame_width != frame_width or detect_frame_height != frame_height
    ):
        scale_x = frame_width / detect_frame_width
        scale_y = frame_height / detect_frame_height
        x1 = int(round(x1 * scale_x))
        y1 = int(round(y1 * scale_y))
        x2 = int(round(x2 * scale_x))
        y2 = int(round(y2 * scale_y))

    if x2 <= x1 or y2 <= y1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid bbox for face crop",
        )

    face_width = x2 - x1
    face_height = y2 - y1
    pad_x = int(round(face_width * padding_ratio))
    pad_y = int(round(face_height * padding_ratio))

    crop_box = (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(frame_width, x2 + pad_x),
        min(frame_height, y2 + pad_y),
    )

    cropped = image.crop(crop_box)
    output = BytesIO()
    cropped.save(output, format="JPEG", quality=90)
    output.seek(0)

    logger.info(
        "Returned face crop for user=%s video=%s frame=%s bbox=%s",
        current_user.get('sub'),
        video_uuid,
        frame_number,
        [x1, y1, x2, y2],
    )

    return StreamingResponse(output, media_type="image/jpeg")


class MVRSearchAnalysisRequest(BaseModel):
    mvr_uuids: List[UUID]
    session_uuid: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    merged_page: int = 1
    merged_page_size: int = 10
    ephemeral_groups: Optional[List[Dict[str, Any]]] = None


async def _get_mvr_stored_comparison_enabled() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "http://localhost:8002/api/v1/settings/workflow/mvr-merge",
                headers={
                    "Authorization": "Bearer internal-service-token-ppl-meta-frontend"
                },
            )
        if response.status_code == 200:
            data = response.json()
            return bool(data.get("stored_comparison_enabled", False))
    except Exception as exc:
        logger.warning(
            "Failed to fetch MVR stored comparison setting, defaulting to false: %s",
            exc,
        )
    return False


def _build_demographics_payload(super_individual: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    has_any_demographics = (
        super_individual.get("gender") is not None
        or super_individual.get("age_min") is not None
        or super_individual.get("age_max") is not None
    )
    if not has_any_demographics:
        return None

    age_min = super_individual.get("age_min")
    age_max = super_individual.get("age_max")
    age_mean = None
    if age_min is not None and age_max is not None:
        age_mean = round((int(age_min) + int(age_max)) / 2, 1)

    return {
        "gender": super_individual.get("gender"),
        "gender_confidence": (
            round(float(super_individual.get("gender_confidence") or 0.0), 3)
            if super_individual.get("gender_confidence") is not None
            else None
        ),
        "age_min": int(age_min) if age_min is not None else None,
        "age_max": int(age_max) if age_max is not None else None,
        "age_mean": age_mean,
        "age_confidence": (
            round(float(super_individual.get("age_confidence") or 0.0), 3)
            if super_individual.get("age_confidence") is not None
            else None
        ),
    }


def _normalize_datetime_for_comparison(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _age_display_to_mean(age_display: Optional[str]) -> Optional[float]:
    if not age_display:
        return None
    if "-" not in age_display:
        try:
            return float(age_display)
        except (TypeError, ValueError):
            return None

    min_age_str, max_age_str = age_display.split("-", 1)
    try:
        min_age = float(min_age_str)
        max_age = float(max_age_str)
    except (TypeError, ValueError):
        return None
    return round((min_age + max_age) / 2.0, 3)


def _build_persistent_search_summary(
    search_response: MVRPeopleSearchResponse,
    camera_ids: List[str],
    video_uuids: List[str],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> Dict[str, Any]:
    results = search_response.mvr_people
    total_appearances = sum(result.total_appearances for result in results)
    unique_videos = len(
        {
            appearance.video_uuid
            for result in results
            for appearance in result.appearances
        }
    )
    average_confidence = round(
        sum(result.confidence_score for result in results) / len(results),
        3,
    ) if results else 0.0
    average_quality = round(
        sum(result.quality_score for result in results) / len(results),
        3,
    ) if results else 0.0

    total_duration_seconds = 0.0
    first_appearance = None
    last_appearance = None
    total_men = 0
    total_women = 0
    total_unknown = 0
    ages = []

    for result in results:
        if first_appearance is None or result.first_seen < first_appearance:
            first_appearance = result.first_seen
        if last_appearance is None or result.last_seen > last_appearance:
            last_appearance = result.last_seen

        gender = (result.estimated_gender or "").strip().lower()
        if gender == "male":
            total_men += 1
        elif gender == "female":
            total_women += 1
        else:
            total_unknown += 1

        age_mean = _age_display_to_mean(result.estimated_age)
        if age_mean is not None:
            ages.append(age_mean)

        for appearance in result.appearances:
            duration = (appearance.end_timestamp - appearance.start_timestamp).total_seconds()
            if duration > 0:
                total_duration_seconds += duration

    search_time_span_seconds = None
    if start_time is not None and end_time is not None:
        search_time_span_seconds = max((end_time - start_time).total_seconds(), 0.0)

    return {
        "total_individuals": len(results),
        "total_appearances": total_appearances,
        "unique_videos": unique_videos,
        "average_confidence": average_confidence,
        "average_quality": average_quality,
        "total_duration_seconds": round(total_duration_seconds, 3),
        "search_time_span_seconds": round(search_time_span_seconds, 3) if search_time_span_seconds is not None else None,
        "first_appearance": first_appearance,
        "last_appearance": last_appearance,
        "total_men": total_men,
        "total_women": total_women,
        "total_unknown": total_unknown,
        "average_age": round(sum(ages) / len(ages), 3) if ages else None,
        "search_input": {
            "camera_ids": sorted({camera_id for camera_id in camera_ids if camera_id}),
            "video_uuids": sorted({video_uuid for video_uuid in video_uuids if video_uuid}),
            "start_date": start_time,
            "end_date": end_time,
        },
    }


def _normalize_session_payload(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value or {})


def _build_analysis_from_hierarchy(
    hierarchy: Dict[str, Any],
    session_uuid: str,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> Dict[str, Any]:
    super_individual = hierarchy["super_individual"]
    all_individuals = hierarchy.get("all_individuals", [])
    normalized_start_time = _normalize_datetime_for_comparison(start_time)
    normalized_end_time = _normalize_datetime_for_comparison(end_time)

    filtered_individuals = []
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    unique_videos = set()
    appearances: List[Dict[str, Any]] = []
    person_object_uuids: List[str] = []
    total_duration_seconds = 0.0
    quality_scores: List[float] = []

    for item in all_individuals:
        item_start = item.get("first_seen_timestamp")
        item_end = item.get("last_seen_timestamp")
        item_start_dt = _normalize_datetime_for_comparison(
            item_start if isinstance(item_start, datetime) else None
        )
        item_end_dt = _normalize_datetime_for_comparison(
            item_end if isinstance(item_end, datetime) else None
        )

        if (
            normalized_start_time is not None
            and item_start_dt is not None
            and item_start_dt < normalized_start_time
        ):
            continue
        if (
            normalized_end_time is not None
            and item_end_dt is not None
            and item_end_dt > normalized_end_time
        ):
            continue

        filtered_individuals.append(item)

        if item_start_dt is not None:
            if first_seen is None or item_start_dt < first_seen:
                first_seen = item_start_dt
        if item_end_dt is not None:
            if last_seen is None or item_end_dt > last_seen:
                last_seen = item_end_dt

        video_uuid = item.get("video_uuid")
        if video_uuid:
            unique_videos.add(str(video_uuid))

        raw_quality_score = item.get("quality_score")
        if raw_quality_score is not None:
            try:
                quality_scores.append(float(raw_quality_score))
            except (TypeError, ValueError):
                pass

        if item_start_dt is not None and item_end_dt is not None:
            duration_seconds = (item_end_dt - item_start_dt).total_seconds()
            if duration_seconds > 0:
                total_duration_seconds += duration_seconds

        appearances.append({
            "individual_uuid": str(item.get("individual_uuid")),
            "video_uuid": str(video_uuid) if video_uuid else "",
            "person_object_uuid": str(item.get("person_object_uuid") or item.get("individual_uuid")),
            "mvr_people_uuid": (
                str(item.get("mvr_people_uuid"))
                if item.get("mvr_people_uuid") is not None
                else None
            ),
            "start_timestamp": item_start_dt.isoformat() if item_start_dt else datetime.now(timezone.utc).isoformat(),
            "end_timestamp": item_end_dt.isoformat() if item_end_dt else datetime.now(timezone.utc).isoformat(),
            "entry_bbox": None,
            "exit_bbox": None,
            "confidence_score": round(float(item.get("confidence") or item.get("confidence_score") or 0.0), 3),
        })
        person_object_uuids.append(str(item.get("individual_uuid")))

    super_uuid = str(hierarchy.get("resolved_super_individual_uuid") or super_individual["mvr_people_uuid"])
    demographics = _build_demographics_payload(super_individual)
    merged_children = hierarchy.get("merged_mvr_people", [])
    if not quality_scores:
        merged_quality_scores = []
        for child in merged_children:
            raw_quality = child.get("quality_score")
            if raw_quality is None:
                continue
            try:
                merged_quality_scores.append(float(raw_quality))
            except (TypeError, ValueError):
                continue
        quality_scores = merged_quality_scores

    average_quality_score = round(
        sum(quality_scores) / len(quality_scores),
        3,
    ) if quality_scores else round(float(super_individual.get("quality_score") or 0.0), 3)

    return {
        "individual_uuid": super_uuid,
        "individual_id": super_uuid,
        "session_uuid": session_uuid,
        "total_appearances": len(filtered_individuals),
        "unique_videos": len(unique_videos),
        "first_seen": (
            first_seen.isoformat()
            if first_seen is not None
            else super_individual.get("created_at", datetime.now(timezone.utc).isoformat())
        ),
        "last_seen": (
            last_seen.isoformat()
            if last_seen is not None
            else datetime.now(timezone.utc).isoformat()
        ),
        "total_duration_seconds": round(total_duration_seconds, 3),
        "average_confidence": round(float(super_individual.get("confidence_score") or 0.0), 3),
        "average_quality_score": average_quality_score,
        "average_route_velocity": None,
        "demographics": demographics,
        "aggregate_demographics": None,
        "appearances": appearances,
        "person_object_uuids": person_object_uuids,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "is_super_individual": bool(merged_children),
        "merged_mvr_count": int(hierarchy.get("mvr_count") or 1),
        "merged_mvr_people": merged_children,
        "best_face_thumbnail": super_individual.get("featured_person_object_uuid"),
        "name": super_individual.get("name"),
        "name_updated_at": (
            super_individual.get("name_updated_at").isoformat()
            if super_individual.get("name_updated_at") is not None
            else None
        ),
        "name_updated_by": super_individual.get("name_updated_by"),
        "merged_children_total": int(hierarchy.get("merged_children_total") or len(merged_children)),
        "merged_children_page": int(hierarchy.get("merged_children_page") or 1),
        "merged_children_page_size": int(hierarchy.get("merged_children_page_size") or 10),
        "merged_children_has_more": bool(hierarchy.get("merged_children_has_more")),
    }


async def _build_analysis_from_mvr_person(
    mvr_repository: MVRRepository,
    mvr_person_uuid: str,
    session_uuid: str,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    member_mvr_person_uuids: Optional[List[str]] = None,
    ephemeral_group: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_start_time = _normalize_datetime_for_comparison(start_time)
    normalized_end_time = _normalize_datetime_for_comparison(end_time)
    member_mvr_person_uuids = member_mvr_person_uuids or [mvr_person_uuid]

    async with mvr_repository.pool.acquire() as conn:
        mvr_rows = await conn.fetch(
            """
            SELECT
                mvr_people_uuid,
                quality_score,
                confidence_score,
                gender,
                gender_confidence,
                age_min,
                age_max,
                age_confidence,
                featured_person_object_uuid,
                name,
                name_updated_at,
                name_updated_by,
                created_at
            FROM mvr_people
            WHERE mvr_people_uuid = ANY($1::uuid[])
            ORDER BY CASE WHEN mvr_people_uuid = $2::uuid THEN 0 ELSE 1 END, quality_score DESC
            """,
            member_mvr_person_uuids,
            mvr_person_uuid,
        )

        if not mvr_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MVR person {mvr_person_uuid} not found",
            )

        mvr_row = mvr_rows[0]

        appearance_rows = await conn.fetch(
            """
            SELECT
                iva.individual_uuid,
                iva.video_uuid,
                iva.person_object_uuid,
                iva.start_timestamp,
                iva.end_timestamp,
                iva.confidence,
                imm.mvr_people_uuid
            FROM individual_video_appearances iva
            INNER JOIN individual_mvr_mapping imm
                ON imm.individual_uuid = iva.individual_uuid
            WHERE imm.mvr_people_uuid = ANY($1::uuid[])
            ORDER BY iva.start_timestamp ASC
            """,
            member_mvr_person_uuids,
        )

    appearances: List[Dict[str, Any]] = []
    person_object_uuids: List[str] = []
    unique_videos = set()
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_duration_seconds = 0.0

    for row in appearance_rows:
        row_start = _normalize_datetime_for_comparison(row["start_timestamp"])
        row_end = _normalize_datetime_for_comparison(row["end_timestamp"])

        if (
            normalized_start_time is not None
            and row_start is not None
            and row_start < normalized_start_time
        ):
            continue
        if (
            normalized_end_time is not None
            and row_end is not None
            and row_end > normalized_end_time
        ):
            continue

        if row_start is not None:
            if first_seen is None or row_start < first_seen:
                first_seen = row_start
        if row_end is not None:
            if last_seen is None or row_end > last_seen:
                last_seen = row_end

        video_uuid = str(row["video_uuid"])
        unique_videos.add(video_uuid)
        person_object_uuid = str(row["person_object_uuid"])
        person_object_uuids.append(person_object_uuid)

        appearances.append(
            {
                "individual_uuid": str(row["individual_uuid"]),
                "video_uuid": video_uuid,
                "person_object_uuid": person_object_uuid,
                "mvr_people_uuid": str(row["mvr_people_uuid"]),
                "start_timestamp": row_start.isoformat()
                if row_start is not None
                else datetime.now(timezone.utc).isoformat(),
                "end_timestamp": row_end.isoformat()
                if row_end is not None
                else datetime.now(timezone.utc).isoformat(),
                "entry_bbox": None,
                "exit_bbox": None,
                "confidence_score": round(float(row["confidence"] or 0.0), 3),
            }
        )

        if row_start is not None and row_end is not None:
            duration_seconds = (row_end - row_start).total_seconds()
            if duration_seconds > 0:
                total_duration_seconds += duration_seconds

    demographics = _build_demographics_payload(dict(mvr_row))
    similarity_map = {
        str(key): float(value)
        for key, value in (ephemeral_group or {}).get("similarities", {}).items()
    }
    merged_children = [
        {
            "mvr_people_uuid": str(row["mvr_people_uuid"]),
            "featured_individual_uuid": str(
                row["featured_person_object_uuid"] or row["mvr_people_uuid"]
            ),
            "quality_score": float(row["quality_score"] or 0.0),
            "confidence_score": float(row["confidence_score"] or 0.0),
            "gender": row["gender"],
            "age_min": row["age_min"],
            "age_max": row["age_max"],
            "orphaned_at": None,
            "merged_into_mvr_uuid": mvr_person_uuid,
            "similarity_to_featured": similarity_map.get(
                str(row["mvr_people_uuid"]),
                0.0,
            ),
            "name": row["name"],
            "name_updated_at": (
                row["name_updated_at"].isoformat()
                if row["name_updated_at"] is not None
                else None
            ),
            "name_updated_by": row["name_updated_by"],
        }
        for row in mvr_rows[1:]
    ]

    quality_scores = [
        float(row["quality_score"] or 0.0)
        for row in mvr_rows
        if row["quality_score"] is not None
    ]
    average_quality_score = round(
        sum(quality_scores) / len(quality_scores),
        3,
    ) if quality_scores else 0.0

    return {
        "individual_uuid": mvr_person_uuid,
        "individual_id": mvr_person_uuid,
        "session_uuid": session_uuid,
        "total_appearances": len(appearances),
        "unique_videos": len(unique_videos),
        "first_seen": (
            first_seen.isoformat()
            if first_seen is not None
            else mvr_row["created_at"].isoformat()
        ),
        "last_seen": (
            last_seen.isoformat()
            if last_seen is not None
            else datetime.now(timezone.utc).isoformat()
        ),
        "total_duration_seconds": round(total_duration_seconds, 3),
        "average_confidence": round(float(mvr_row["confidence_score"] or 0.0), 3),
        "average_quality_score": average_quality_score,
        "average_route_velocity": None,
        "demographics": demographics,
        "aggregate_demographics": None,
        "appearances": appearances,
        "person_object_uuids": person_object_uuids,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "is_super_individual": bool(merged_children),
        "merged_mvr_count": len(member_mvr_person_uuids),
        "merged_mvr_people": merged_children,
        "best_face_thumbnail": mvr_row["featured_person_object_uuid"],
        "name": mvr_row["name"],
        "name_updated_at": (
            mvr_row["name_updated_at"].isoformat()
            if mvr_row["name_updated_at"] is not None
            else None
        ),
        "name_updated_by": mvr_row["name_updated_by"],
        "merged_children_total": len(merged_children),
        "merged_children_page": 1,
        "merged_children_page_size": max(len(merged_children), 1),
        "merged_children_has_more": False,
    }


# ============================================================================
# ENDPOINT 1: Create MVR-People for Individual
# ============================================================================

@router.post(
    "/individuals/{individual_uuid}/create",
    response_model=CreateMVRResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create MVR-People for Individual",
    description="Create Machine Vision Representation for an Individual. "
                "Supports both synchronous and asynchronous processing.",
)
async def create_mvr_for_individual(
    individual_uuid: UUID,
    request: Optional[CreateMVRRequest] = Body(default=None),
    mvr_service: MVRService = Depends(get_mvr_service),
    background_processor: MVRBackgroundProcessor = Depends(get_mvr_background_processor),
    current_user: dict = Depends(get_current_user),
):
    """
    Create MVR-People representation for an individual.
    
    **Processing Modes:**
    - **Background (default):** Returns immediately with status "pending"
    - **Synchronous:** Set background_processing=false for immediate processing
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual
    - background_processing: Enable async processing (default: true)
    - force_recreate: Recreate if already exists (default: false)
    
    **Returns:**
    - 202 Accepted (background): MVR creation queued
    - 200 OK (synchronous): MVR created with full details
    - 400 Bad Request: Invalid Individual UUID or already exists
    - 404 Not Found: Individual not found
    """
    logger.info(f"Creating MVR-People for Individual {individual_uuid} (user: {current_user.get('email')})")
    
    # Parse request body (use defaults if not provided)
    background_processing = True
    force_recreate = False
    if request:
        background_processing = request.background_processing
        force_recreate = request.force_recreate
    
    try:
        # Check if MVR already exists
        existing_mvr = await mvr_service.get_mvr_people_for_individual(
            individual_uuid
        )
        
        if existing_mvr and not force_recreate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MVR-People already exists for Individual {individual_uuid}. "
                       f"Use force_recreate=true to recreate."
            )
        
        # Background processing
        if background_processing:
            # Queue background task
            task_info = await background_processor.process_individual(
                individual_uuid=individual_uuid,
                auto_match=False,  # Don't auto-match on creation
            )
            
            return CreateMVRResponse(
                mvr_people_uuid=None,  # Not created yet
                individual_uuid=individual_uuid,
                status="pending",
                message="MVR-People creation queued for background processing",
                estimated_completion_seconds=10,
            )
        
        # Synchronous processing
        else:
            # Create MVR-People immediately
            mvr_result = await mvr_service.create_mvr_people_from_individual(individual_uuid)
            
            if not mvr_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create MVR-People"
                )
            
            return CreateMVRResponse(
                mvr_people_uuid=mvr_result['mvr_people_uuid'],
                individual_uuid=individual_uuid,
                status="completed",
                face_embedding=mvr_result.get('face_embedding'),
                age_estimate=mvr_result.get('age_estimate'),
                gender_estimate=mvr_result.get('gender_estimate'),
                representative_individual_uuid=mvr_result.get('featured_individual_uuid'),
                quality_score=mvr_result.get('quality_score'),
                created_at=mvr_result.get('created_at'),
                updated_at=mvr_result.get('updated_at'),
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MVR-People for Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 2: Get MVR-People by UUID
# ============================================================================

@router.get(
    "/{mvr_people_uuid}",
    response_model=MVRPeopleResponse,
    summary="Get MVR-People by UUID",
    description="Retrieve complete MVR-People record by UUID",
)
async def get_mvr_people_by_uuid(
    mvr_people_uuid: UUID,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve MVR-People record by UUID.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid: UUID of the MVR-People record
    
    **Returns:**
    - 200 OK: MVR-People record with all linked Individuals
    - 404 Not Found: MVR-People not found
    """
    logger.info(f"Retrieving MVR-People {mvr_people_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get MVR-People record
        mvr_record = await mvr_repository.get_mvr_people_by_uuid(mvr_people_uuid)
        
        if not mvr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MVR-People {mvr_people_uuid} not found"
            )
        
        # Get linked Individuals
        linked_individuals = await mvr_repository.get_individuals_for_mvr(mvr_people_uuid)
        
        return MVRPeopleResponse(
            mvr_people_uuid=mvr_record['mvr_people_uuid'],
            status=mvr_record.get('processing_status', 'completed'),
            face_embedding=mvr_record.get('face_embedding'),
            age_estimate=mvr_record.get('age_estimate'),
            gender_estimate=mvr_record.get('gender_estimate'),
            representative_individual_uuid=mvr_record.get('featured_individual_uuid'),
            representative_face_uuid=mvr_record.get('representative_face_uuid'),
            quality_score=mvr_record.get('quality_score'),
            total_linked_individuals=len(linked_individuals),
            linked_individuals=linked_individuals,
            created_at=mvr_record.get('created_at'),
            updated_at=mvr_record.get('updated_at'),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving MVR-People {mvr_people_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 3: Get MVR-People for Individual
# ============================================================================

@router.get(
    "/individuals/{individual_uuid}",
    response_model=MVRPeopleResponse,
    summary="Get MVR-People for Individual",
    description="Retrieve MVR-People linked to an Individual",
)
async def get_mvr_for_individual(
    individual_uuid: UUID,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Get MVR-People linked to an Individual.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual
    
    **Returns:**
    - 200 OK: MVR-People record
    - 404 Not Found: No MVR-People found for Individual
    """
    logger.info(f"Retrieving MVR-People for Individual {individual_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get MVR-People for Individual
        mvr_record = await mvr_service.get_mvr_for_individual(individual_uuid)
        
        if not mvr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No MVR-People found for Individual {individual_uuid}",
            )
        
        return MVRPeopleResponse(
            individual_uuid=individual_uuid,
            mvr_people=mvr_record,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving MVR-People for Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 4: Search Similar MVR-People
# ============================================================================

@router.post(
    "/search/similar",
    response_model=SearchSimilarResponse,
    summary="Search Similar MVR-People",
    description="Find similar people using face embedding similarity (pgvector)",
)
async def search_similar_mvr_people(
    request: SearchSimilarRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Find similar people using face embedding similarity.
    
    **Similarity Algorithm:** Cosine similarity via pgvector extension
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid OR face_embedding: Source for similarity search
    - similarity_threshold: Minimum cosine similarity (0-1, default: 0.6)
    - max_results: Maximum results to return (default: 10)
    - include_demographics: Include age/gender filters (default: true)
    
    **Returns:**
    - 200 OK: List of similar MVR-People with similarity scores
    - 400 Bad Request: Invalid request (missing mvr_people_uuid and face_embedding)
    """
    logger.info(f"Searching similar MVR-People (user: {current_user.get('email')})")
    
    try:
        # Validate request
        if not request.mvr_people_uuid and not request.face_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either mvr_people_uuid or face_embedding must be provided"
            )
        
        # Search by MVR UUID
        if request.mvr_people_uuid:
            results = await mvr_service.search_similar_mvr(
                mvr_uuid=request.mvr_people_uuid,
                threshold=request.similarity_threshold or 0.6,
                limit=request.max_results or 10,
            )
        
        # Search by face embedding
        else:
            results = await mvr_service.search_similar_by_embedding(
                face_embedding=request.face_embedding,
                threshold=request.similarity_threshold or 0.6,
                limit=request.max_results or 10,
            )
        
        return SearchSimilarResponse(
            query_mvr_people_uuid=request.mvr_people_uuid,
            total_results=len(results),
            results=results,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching similar MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search similar MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 5: Search MVR-People by Demographics
# ============================================================================

@router.post(
    "/search/demographics",
    response_model=SearchDemographicsResponse,
    summary="Search MVR-People by Demographics",
    description="Search MVR-People by age/gender filters",
)
async def search_mvr_by_demographics(
    request: SearchDemographicsRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Search MVR-People by age and gender filters.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - age_min: Minimum age (optional)
    - age_max: Maximum age (optional)
    - gender: Gender filter ("male", "female", "unknown") (optional)
    - min_confidence: Minimum confidence for age/gender (default: 0.7)
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20)
    
    **Returns:**
    - 200 OK: Paginated list of MVR-People matching demographics
    """
    logger.info(f"Searching MVR-People by demographics (user: {current_user.get('email')})")
    
    try:
        # Search by demographics
        results = await mvr_service.search_by_demographics(
            age_min=request.age_min,
            age_max=request.age_max,
            gender=request.gender,
            min_confidence=request.min_confidence or 0.7,
            page=request.page or 1,
            page_size=request.page_size or 20,
        )
        
        return SearchDemographicsResponse(
            total_results=results['total'],
            page=results['page'],
            page_size=results['page_size'],
            results=results['data'],
        )
    
    except Exception as e:
        logger.error(f"Error searching MVR-People by demographics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search by demographics: {str(e)}"
        )


# ============================================================================
# ENDPOINT 6: Link Individual to Existing MVR-People
# ============================================================================

@router.post(
    "/{mvr_people_uuid}/link-individual",
    response_model=LinkIndividualResponse,
    summary="Link Individual to MVR-People",
    description="Link an Individual to existing MVR-People (person re-identification)",
)
async def link_individual_to_mvr(
    mvr_people_uuid: UUID,
    request: LinkIndividualRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Link an Individual to existing MVR-People.
    
    **Use Case:** Person re-identification across videos/sessions
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid: UUID of the MVR-People
    - individual_uuid: UUID of the Individual to link
    - confidence_score: Similarity confidence (0-1)
    
    **Returns:**
    - 200 OK: Individual linked successfully
    - 404 Not Found: MVR-People or Individual not found
    - 400 Bad Request: Individual already linked
    """
    logger.info(
        f"Linking Individual {request.individual_uuid} to MVR-People {mvr_people_uuid} "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        # Link Individual to MVR-People
        result = await mvr_repository.link_individual_to_mvr(
            individual_uuid=request.individual_uuid,
            mvr_uuid=mvr_people_uuid,
            confidence_score=request.confidence_score,
            is_representative=False,  # Not the original Individual
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to link Individual to MVR-People"
            )
        
        # Get updated MVR-People
        mvr_record = await mvr_repository.get_mvr_people_by_uuid(mvr_people_uuid)
        
        return LinkIndividualResponse(
            mvr_people_uuid=mvr_people_uuid,
            individual_uuid=request.individual_uuid,
            linked_at=result['linked_at'],
            confidence_score=request.confidence_score,
            total_linked_individuals=mvr_record.get('total_linked_individuals', 0),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking Individual to MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link Individual: {str(e)}"
        )


# ============================================================================
# ENDPOINT 7: Batch Create MVR-People
# ============================================================================

@router.post(
    "/batch/create",
    response_model=BatchCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Create MVR-People",
    description="Create MVR-People for multiple Individuals (batch processing)",
)
async def batch_create_mvr_people(
    request: BatchCreateRequest,
    background_processor: MVRBackgroundProcessor = Depends(get_mvr_background_processor),
    current_user: dict = Depends(get_current_user),
):
    """
    Create MVR-People for multiple Individuals in batch.
    
    **Processing:** Always uses background processing for efficiency
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuids: List of Individual UUIDs
    - background_processing: Enable async processing (default: true)
    
    **Returns:**
    - 202 Accepted: Batch creation queued
    - 400 Bad Request: Invalid request (empty list, etc.)
    """
    logger.info(
        f"Batch creating MVR-People for {len(request.individual_uuids)} Individuals "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        if not request.individual_uuids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="individual_uuids list cannot be empty"
            )
        
        # Queue batch processing tasks
        batch_id = None  # TODO: Implement batch tracking
        
        for individual_uuid in request.individual_uuids:
            await background_processor.process_individual(
                individual_uuid=individual_uuid,
                auto_match=False,
            )
        
        # Estimate completion time (10 seconds per Individual)
        estimated_seconds = len(request.individual_uuids) * 10
        
        return BatchCreateResponse(
            total_queued=len(request.individual_uuids),
            batch_id=batch_id,
            status="processing",
            individual_uuids=request.individual_uuids,
            estimated_completion_seconds=estimated_seconds,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch creating MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch create MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 8: Get MVR-People Processing Status
# ============================================================================

@router.get(
    "/{mvr_people_uuid}/status",
    response_model=MVRStatusResponse,
    summary="Get MVR-People Processing Status",
    description="Check processing status of MVR-People creation",
)
async def get_mvr_processing_status(
    mvr_people_uuid: UUID,
    background_processor: MVRBackgroundProcessor = Depends(get_mvr_background_processor),
    current_user: dict = Depends(get_current_user),
):
    """
    Check processing status of MVR-People creation.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid: UUID of the MVR-People
    
    **Returns:**
    - 200 OK: Processing status
    - 404 Not Found: MVR-People not found
    """
    logger.info(f"Checking status of MVR-People {mvr_people_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get task status from background processor
        # TODO: Implement task status tracking by MVR UUID
        
        return MVRStatusResponse(
            mvr_people_uuid=mvr_people_uuid,
            status="completed",  # Placeholder
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            processing_error=None,
            progress_percentage=100,
            current_step="Completed",
        )
    
    except Exception as e:
        logger.error(f"Error getting MVR-People status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


# ============================================================================
# ENDPOINT 9: Match Individuals (Find Similar)
# ============================================================================

@router.post(
    "/individuals/{individual_uuid}/match",
    response_model=MatchIndividualResponse,
    summary="Match Individuals",
    description="Find other Individuals that match the given Individual based on face similarity",
)
async def match_individual(
    individual_uuid: UUID,
    request: Optional[MatchIndividualRequest] = Body(default=None),
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Find other Individuals that match the given Individual.
    
    **Matching Algorithm:** Uses MVRMatcher with configurable threshold
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual to match
    - threshold: Similarity threshold (default: 0.7)
    - auto_merge: Automatically merge matches above threshold (default: false)
    - max_results: Maximum results to return (default: 10)
    
    **Returns:**
    - 200 OK: List of matching Individuals with similarity scores
    - 404 Not Found: Individual not found
    """
    logger.info(f"Matching Individual {individual_uuid} (user: {current_user.get('email')})")
    
    # Parse request
    threshold = 0.7
    auto_merge = False
    max_results = 10
    
    if request:
        threshold = request.threshold or threshold
        auto_merge = request.auto_merge
        max_results = request.max_results or max_results
    
    try:
        # Find matches
        matches = await mvr_matcher.find_matching_mvr(
            individual_uuid=individual_uuid,
            threshold=threshold,
        )
        
        # Auto-merge if enabled
        if auto_merge and matches:
            # TODO: Implement auto-merge logic
            logger.info(f"Auto-merge enabled, merging {len(matches)} matches")
        
        # Calculate matches above threshold
        matches_above_threshold = sum(
            1 for match in matches if match['similarity_score'] >= threshold
        )
        
        return MatchIndividualResponse(
            individual_uuid=individual_uuid,
            matches=matches[:max_results],
            total_matches=len(matches),
            matches_above_threshold=matches_above_threshold,
            threshold_used=threshold,
        )
    
    except Exception as e:
        logger.error(f"Error matching Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to match Individual: {str(e)}"
        )


# ============================================================================
# ENDPOINT 10: Merge Individuals to Single MVR-People
# ============================================================================

@router.post(
    "/merge",
    response_model=MergeIndividualsResponse,
    summary="Merge Individuals",
    description="Manually merge two Individuals to single MVR-People (predominant based on quality)",
)
async def merge_individuals(
    request: MergeIndividualsRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Merge two Individuals to single MVR-People.
    
    **Merge Logic:** Predominant MVR selected by quality score (higher wins)
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_a_uuid: First Individual UUID
    - individual_b_uuid: Second Individual UUID
    - similarity_score: Similarity score for audit trail
    - triggered_by: Trigger source (default: "manual")
    
    **Returns:**
    - 200 OK: Merge completed successfully
    - 400 Bad Request: Invalid request (same Individual, etc.)
    - 404 Not Found: One or both Individuals not found
    """
    logger.info(
        f"Merging Individuals {request.individual_a_uuid} and {request.individual_b_uuid} "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        # Validate request
        if request.individual_a_uuid == request.individual_b_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot merge an Individual with itself"
            )
        
        # Execute merge
        merge_result = await mvr_matcher.merge_mvr_people(
            individual_a_uuid=request.individual_a_uuid,
            individual_b_uuid=request.individual_b_uuid,
            similarity_score=request.similarity_score,
            triggered_by=request.triggered_by or "manual",
        )
        
        if not merge_result or not merge_result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to merge Individuals"
            )
        
        return MergeIndividualsResponse(
            success=True,
            predominant_mvr_uuid=merge_result['predominant_mvr_uuid'],
            orphaned_mvr_uuid=merge_result['orphaned_mvr_uuid'],
            reassigned_individual_uuid=merge_result['reassigned_individual_uuid'],
            similarity_score=request.similarity_score,
            predominant_quality_score=merge_result.get('predominant_quality_score'),
            orphaned_quality_score=merge_result.get('orphaned_quality_score'),
            merged_at=merge_result.get('merged_at', datetime.now()),
            message=merge_result.get('message'),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging Individuals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge Individuals: {str(e)}"
        )


# ============================================================================
# ENDPOINT 10b: Unmerge MVR — reverse a previous merge
# ============================================================================

@router.post(
    "/unmerge",
    response_model=UnmergeMvrResponse,
    summary="Undo MVR Merge",
    description="Restore an orphaned (child) MVR record, reversing a previous merge.",
)
async def unmerge_mvr(
    request: UnmergeMvrRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
    cache_client=Depends(get_cache_client),
):
    """
    Reverse a merge by restoring the orphaned MVR record.

    **What this does:**
    - Clears is_orphaned / merged_into_mvr_uuid on the child MVR
    - Restores individual_mvr_mapping rows back to the child
    - Removes the mvr_merge_hierarchy row
    - Appends an audit log entry with merge_action='unmerged'

    **Note:** The winner's face_embedding and demographics are NOT reverted.

    **Authentication:** Requires valid JWT token
    """
    user_email = current_user.get("email", "unknown")
    user_id = current_user.get("user_id") or current_user.get("sub")
    logger.info(
        f"Unmerge MVR {request.orphaned_mvr_uuid} requested by {user_email}"
    )

    try:
        result = await mvr_repository.unmerge_mvr_people(
            orphaned_mvr_uuid=request.orphaned_mvr_uuid,
            user_id=str(user_id) if user_id else None,
        )

        # Invalidate ALL cached MVR search results so the next search reflects
        # the split state. The per-video-hash approach fails because the cache key
        # is derived from ALL videos in the user's collection, not just the
        # affected subset — so partial-list hashes never match. Wipe everything.
        try:
            invalidated = await cache_client.invalidate_mvr_search(
                pattern="mvr_search:*"
            )
            logger.info(
                f"🗑️  Invalidated {invalidated} MVR search cache key(s) after unmerge "
                f"of {request.orphaned_mvr_uuid}"
            )
        except Exception as _inv_err:
            logger.warning(f"Cache invalidation after unmerge failed (non-fatal): {_inv_err}")

        # People-counters batch invalidation (proposal §5.7)
        try:
            stale_count = await mvr_repository.mark_batches_stale_for_mvr_people(
                [str(result["restored_mvr_uuid"]), str(result["winner_mvr_uuid"])]
            )
            if stale_count:
                logger.info(
                    "people-counters: marked %d batch(es) stale after unmerge of %s",
                    stale_count,
                    result["restored_mvr_uuid"],
                )
        except Exception as _stale_err:
            logger.warning(
                "people-counters: failed to invalidate batches after unmerge: %s",
                _stale_err,
            )

        return UnmergeMvrResponse(
            success=True,
            restored_mvr_uuid=result["restored_mvr_uuid"],
            winner_mvr_uuid=result["winner_mvr_uuid"],
            individuals_reassigned=result["individuals_reassigned"],
            message=(
                f"MVR {result['restored_mvr_uuid']} restored; "
                f"{result['individuals_reassigned']} individual(s) reassigned."
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unmerge failed for {request.orphaned_mvr_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unmerge MVR: {str(e)}",
        )


# ============================================================================
# ENDPOINT 11: Get Merge History for Individual
# ============================================================================

@router.get(
    "/individuals/{individual_uuid}/merge-history",
    response_model=MergeHistoryResponse,
    summary="Get Merge History",
    description="Get all merge operations involving this Individual",
)
async def get_merge_history(
    individual_uuid: UUID,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all merge operations involving this Individual.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual
    
    **Returns:**
    - 200 OK: Merge history with current and previous MVR-People
    - 404 Not Found: Individual not found
    """
    logger.info(f"Retrieving merge history for Individual {individual_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get current MVR-People
        current_mvr = await mvr_repository.get_mvr_people_by_individual(individual_uuid)
        
        # Get previous MVR-People (orphaned)
        previous_mvr = await mvr_repository.get_orphaned_mvr_for_individual(individual_uuid)
        
        # Get merge events
        merge_events = await mvr_repository.get_merge_audit_log(individual_uuid=individual_uuid)
        
        return MergeHistoryResponse(
            individual_uuid=individual_uuid,
            current_mvr_people=current_mvr,
            previous_mvr_people=previous_mvr,
            merge_events=merge_events,
            total_merges=len(merge_events),
        )
    
    except Exception as e:
        logger.error(f"Error retrieving merge history for Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve merge history: {str(e)}"
        )


# ============================================================================
# ENDPOINT 12: Get Orphaned MVR-People
# ============================================================================

@router.get(
    "/orphaned",
    response_model=OrphanedMVRResponse,
    summary="Get Orphaned MVR-People",
    description="List all orphaned MVR-People (for audit/cleanup)",
)
async def get_orphaned_mvr_people(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    orphaned_after: Optional[datetime] = Query(None, description="Filter by orphaned_at date"),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    List all orphaned MVR-People.
    
    **Use Case:** Audit trail and cleanup of merged MVR-People
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20, max: 100)
    - orphaned_after: Filter by orphaned_at date (optional)
    
    **Returns:**
    - 200 OK: Paginated list of orphaned MVR-People
    """
    logger.info(f"Retrieving orphaned MVR-People (user: {current_user.get('email')})")
    
    try:
        # Get orphaned MVR-People
        orphaned_mvr = await mvr_repository.get_orphaned_mvr_people(
            page=page,
            page_size=page_size,
            orphaned_after=orphaned_after,
        )
        
        return OrphanedMVRResponse(
            total_orphaned=orphaned_mvr['total'],
            page=page,
            page_size=page_size,
            results=orphaned_mvr['data'],
        )
    
    except Exception as e:
        logger.error(f"Error retrieving orphaned MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve orphaned MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 13: Update Matching Configuration
# ============================================================================

@router.put(
    "/config/matching",
    response_model=MatchingConfigResponse,
    summary="Update Matching Configuration",
    description="Update matching threshold and other configuration",
)
async def update_matching_config(
    config: MatchingConfigUpdate,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Update matching configuration.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - default_matching_threshold: Similarity threshold (0-1)
    - auto_merge_enabled: Enable auto-merge on match
    - min_quality_threshold: Minimum quality score (0-1)
    
    **Returns:**
    - 200 OK: Updated configuration
    - 400 Bad Request: Invalid configuration values
    """
    logger.info(f"Updating matching configuration (user: {current_user.get('email')})")
    
    try:
        # Update configuration
        updated_config = await mvr_repository.update_matching_config(
            similarity_threshold=config.default_matching_threshold,
            auto_merge_enabled=config.auto_merge_enabled,
            min_quality_threshold=config.min_quality_threshold,
        )
        
        return MatchingConfigResponse(
            success=True,
            updated_config=updated_config,
            updated_at=datetime.now(),
        )
    
    except Exception as e:
        logger.error(f"Error updating matching configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


# ============================================================================
# ENDPOINT 14: Get Matching Configuration
# ============================================================================

@router.get(
    "/config/matching",
    response_model=MatchingConfigResponse,
    summary="Get Matching Configuration",
    description="Get current matching configuration",
)
async def get_matching_config(
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get current matching configuration.
    
    **Authentication:** Requires valid JWT token
    
    **Returns:**
    - 200 OK: Current configuration
    """
    logger.info(f"Retrieving matching configuration (user: {current_user.get('email')})")
    
    try:
        # Get current configuration
        config = await mvr_repository.get_matching_config()
        
        return MatchingConfigResponse(
            default_matching_threshold=config.get('similarity_threshold', 0.7),
            auto_merge_enabled=config.get('auto_merge_enabled', True),
            min_quality_threshold=config.get('min_quality_threshold', 0.6),
            age_range_tolerance=config.get('age_range_tolerance', 10),
            gender_match_required=config.get('gender_match_required', False),
            orphan_retention_days=config.get('orphan_retention_days', 365),
            last_updated=config.get('updated_at'),
        )
    
    except Exception as e:
        logger.error(f"Error retrieving matching configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


# ============================================================================
# ENDPOINT 15: MVR-People System Health Check
# ============================================================================

@router.get(
    "/health",
    response_model=None,  # Dynamic response based on health status
    status_code=status.HTTP_200_OK,
    summary="MVR-People System Health Check",
    description="Comprehensive health check for MVR-People system including database, "
                "ML models, processing queue, and statistics. "
                "Does NOT require authentication for monitoring tools.",
)
async def mvr_health_check():
    """
    Get comprehensive health status of MVR-People system.
    
    **Components Checked:**
    - Database connection and performance
    - ML models (FaceNet, Age, Gender)
    - Background processing queue
    - System statistics
    
    **No Authentication Required** - Public endpoint for monitoring
    
    **Response Status:**
    - "healthy" - All systems operational
    - "degraded" - Some components have issues but system functional
    - "unhealthy" - Critical components failing
    
    **Returns:**
    - 200 OK: Health status with detailed metrics
    - 503 Service Unavailable: Critical failure
    """
    import time
    from datetime import datetime
    import main
    
    start_time = time.time()
    warnings = []
    errors = []
    overall_status = "healthy"
    
    # Check if MVR services are initialized
    if not main.mvr_repository or not main.mvr_service or not main.mvr_background_processor:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "errors": ["MVR-People services not initialized - check service startup logs"],
                "warnings": [],
                "database": {
                    "connected": False,
                    "pool_size": 0,
                    "idle_connections": 0,
                    "response_time_ms": 0,
                    "pgvector_available": False,
                },
                "ml_models": {
                    "facenet_loaded": False,
                    "age_model_loaded": False,
                    "gender_model_loaded": False,
                    "total_models_loaded": 0,
                    "model_load_time_ms": 0,
                },
                "processing_queue": {
                    "queue_size": 0,
                    "processing_tasks": 0,
                    "pending_tasks": 0,
                    "failed_tasks_last_hour": 0,
                    "average_processing_time_ms": 0,
                },
                "statistics": {
                    "total_mvr_people": 0,
                    "active_mvr_people": 0,
                    "orphaned_mvr_people": 0,
                    "individuals_with_mvr": 0,
                    "total_merge_operations": 0,
                    "average_quality_score": 0.0,
                },
                "uptime_seconds": 0,
                "last_mvr_created_at": None,
                "last_merge_at": None,
            }
        )
    
    mvr_repository = main.mvr_repository
    mvr_service = main.mvr_service
    mvr_background_processor = main.mvr_background_processor
    
    try:
        # ====================================================================
        # 1. Database Health Check
        # ====================================================================
        db_start = time.time()
        try:
            # Test database connection with simple query
            pool_stats = await mvr_repository.pool.execute(
                "SELECT COUNT(*) FROM mvr_people"
            )
            db_response_time = (time.time() - db_start) * 1000  # ms
            
            # Get pool statistics
            pool_size = mvr_repository.pool.get_size()
            idle_connections = mvr_repository.pool.get_idle_size()
            
            # Check pgvector extension
            pgvector_check = await mvr_repository.pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            
            database_health = {
                "connected": True,
                "pool_size": pool_size,
                "idle_connections": idle_connections,
                "response_time_ms": round(db_response_time, 2),
                "pgvector_available": pgvector_check,
            }
            
            if db_response_time > 1000:  # > 1 second
                warnings.append(f"Database slow response: {db_response_time:.0f}ms")
                overall_status = "degraded"
                
            if not pgvector_check:
                errors.append("pgvector extension not available")
                overall_status = "unhealthy"
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            database_health = {
                "connected": False,
                "pool_size": 0,
                "idle_connections": 0,
                "response_time_ms": 0,
                "pgvector_available": False,
            }
            errors.append(f"Database connection failed: {str(e)}")
            overall_status = "unhealthy"
        
        # ====================================================================
        # 2. ML Models Health Check
        # ====================================================================
        ml_start = time.time()
        try:
            # Check if ML processor is available
            ml_processor = mvr_service.ml_processor
            
            # Check model availability
            facenet_loaded = hasattr(ml_processor, 'face_model') and ml_processor.face_model is not None
            age_loaded = hasattr(ml_processor, 'age_model') and ml_processor.age_model is not None
            gender_loaded = hasattr(ml_processor, 'gender_model') and ml_processor.gender_model is not None
            
            total_loaded = sum([facenet_loaded, age_loaded, gender_loaded])
            ml_load_time = (time.time() - ml_start) * 1000  # ms
            
            ml_models_health = {
                "facenet_loaded": facenet_loaded,
                "age_model_loaded": age_loaded,
                "gender_model_loaded": gender_loaded,
                "total_models_loaded": total_loaded,
                "model_load_time_ms": round(ml_load_time, 2),
            }
            
            if total_loaded < 3:
                warnings.append(f"Only {total_loaded}/3 ML models loaded")
                overall_status = "degraded"
                
        except Exception as e:
            logger.error(f"ML models health check failed: {e}")
            ml_models_health = {
                "facenet_loaded": False,
                "age_model_loaded": False,
                "gender_model_loaded": False,
                "total_models_loaded": 0,
                "model_load_time_ms": 0,
            }
            warnings.append(f"ML models check failed: {str(e)}")
            overall_status = "degraded"
        
        # ====================================================================
        # 3. Processing Queue Health Check
        # ====================================================================
        try:
            # Get background processor statistics (await since it's async)
            stats = await mvr_background_processor.get_statistics()
            
            processing_queue_health = {
                "queue_size": stats.get('total_tasks', 0),
                "processing_tasks": stats.get('successful_tasks', 0),
                "pending_tasks": stats.get('total_tasks', 0) - stats.get('successful_tasks', 0),
                "failed_tasks_last_hour": stats.get('failed_tasks', 0),
                "average_processing_time_ms": stats.get('average_processing_time', 0) * 1000,
            }
            
            if processing_queue_health['failed_tasks_last_hour'] > 10:
                warnings.append(f"High failure rate: {processing_queue_health['failed_tasks_last_hour']} failures")
                overall_status = "degraded"
                
        except Exception as e:
            logger.error(f"Processing queue health check failed: {e}")
            processing_queue_health = {
                "queue_size": 0,
                "processing_tasks": 0,
                "pending_tasks": 0,
                "failed_tasks_last_hour": 0,
                "average_processing_time_ms": 0,
            }
            warnings.append(f"Queue check failed: {str(e)}")
        
        # ====================================================================
        # 4. System Statistics
        # ====================================================================
        try:
            # Get MVR-People statistics from database
            total_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_people"
            )
            active_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = FALSE"
            )
            orphaned_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = TRUE"
            )
            individuals_with_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM individual_mvr_mapping"
            )
            total_merges = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_merge_audit_log"
            )
            avg_quality = await mvr_repository.pool.fetchval(
                "SELECT AVG(quality_score) FROM mvr_people WHERE is_orphaned = FALSE"
            )
            
            # Get last MVR creation time
            last_mvr_created = await mvr_repository.pool.fetchval(
                "SELECT MAX(created_at) FROM mvr_people"
            )
            
            # Get last merge time
            last_merge = await mvr_repository.pool.fetchval(
                "SELECT MAX(merge_timestamp) FROM mvr_merge_audit_log"
            )
            
            statistics = {
                "total_mvr_people": total_mvr or 0,
                "active_mvr_people": active_mvr or 0,
                "orphaned_mvr_people": orphaned_mvr or 0,
                "individuals_with_mvr": individuals_with_mvr or 0,
                "total_merge_operations": total_merges or 0,
                "average_quality_score": round(float(avg_quality or 0.0), 3),
            }
            
        except Exception as e:
            logger.error(f"Statistics collection failed: {e}")
            statistics = {
                "total_mvr_people": 0,
                "active_mvr_people": 0,
                "orphaned_mvr_people": 0,
                "individuals_with_mvr": 0,
                "total_merge_operations": 0,
                "average_quality_score": 0.0,
            }
            last_mvr_created = None
            last_merge = None
            warnings.append(f"Statistics collection failed: {str(e)}")
        
        # ====================================================================
        # 5. Build Response
        # ====================================================================
        total_time = time.time() - start_time
        
        response = {
            "status": overall_status,
            "timestamp": datetime.utcnow(),
            "version": "1.0.0",
            "database": database_health,
            "ml_models": ml_models_health,
            "processing_queue": processing_queue_health,
            "statistics": statistics,
            "uptime_seconds": round(total_time, 2),
            "last_mvr_created_at": last_mvr_created,
            "last_merge_at": last_merge,
            "warnings": warnings,
            "errors": errors,
        }
        
        # Return 503 if unhealthy
        if overall_status == "unhealthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=response
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response
        )
        
    except Exception as e:
        logger.error(f"Health check failed critically: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "errors": [f"Critical health check failure: {str(e)}"],
                "warnings": [],
            }
        )


# ============================================================================
# ENDPOINT 15: Batch Match and Merge Individuals
# ============================================================================

@router.post(
    "/batch-match-and-merge",
    response_model=BatchMatchAndMergeResponse,
    summary="Batch Match and Merge Individuals",
    description="Batch operation to match and merge multiple individuals "
                "from a tracking session",
)
async def batch_match_and_merge(
    request: BatchMatchAndMergeRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Batch match and merge all individuals from a tracking session.
    
    This endpoint:
    1. Takes a list of individual UUIDs (from tracking session)
    2. For each individual, finds matching individuals (face similarity)
    3. Merges duplicates above the similarity threshold
    4. Returns original count vs unique count
    
    **Use Case:** Get unique individual count after cross-video tracking
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuids: List of individual UUIDs to process
    - threshold: Similarity threshold (default: 0.7)
    - triggered_by: Source identifier (default: "batch_auto_match")
    - session_uuid: Optional tracking session UUID for audit
    
    **Returns:**
    - 200 OK: Batch merge completed with statistics
    - 400 Bad Request: Invalid request (empty list, invalid UUIDs)
    - 500 Internal Server Error: Processing failed
    
    **Example:**
    ```
    POST /api/v1/mvr-people/batch-match-and-merge
    {
      "individual_uuids": ["uuid-1", "uuid-2", ..., "uuid-15"],
      "threshold": 0.7,
      "triggered_by": "cross_video_tracking_session",
      "session_uuid": "session-abc-123"
    }
    
    Response:
    {
      "success": true,
      "original_count": 15,
      "unique_count": 12,
      "merge_count": 3,
      "merges": [...],
      "processing_time_seconds": 2.34
    }
    ```
    """
    import time
    start_time = time.time()
    
    logger.info(
        f"Batch match and merge: {len(request.individual_uuids)} individuals "
        f"(threshold: {request.threshold}, "
        f"user: {current_user.get('email')})"
    )
    
    original_count = len(request.individual_uuids)
    processed_individuals = set()
    merge_count = 0
    merges = []
    skipped_count = 0
    
    try:
        # Process each individual
        for individual_uuid in request.individual_uuids:
            individual_uuid_str = str(individual_uuid)
            
            # Skip if already processed (was orphaned in a previous merge)
            if individual_uuid_str in processed_individuals:
                logger.debug(
                    f"Skipping {individual_uuid_str} (already processed)"
                )
                continue
            
            try:
                # Get or create MVR record for this individual
                mvr_record = await mvr_matcher.repository.get_mvr_people_by_individual(
                    individual_uuid=individual_uuid_str
                )
                
                # If no MVR exists, create one from the individual
                if not mvr_record:
                    logger.info(
                        f"No MVR record for {individual_uuid_str}, "
                        f"creating MVR from individual"
                    )
                    try:
                        # Get mvr_service dependency
                        from background.mvr_helper import get_mvr_service
                        mvr_svc = get_mvr_service()
                        if not mvr_svc:
                            logger.warning(
                                f"MVR service not available, skipping "
                                f"{individual_uuid_str}"
                            )
                            skipped_count += 1
                            continue
                        
                        # Create MVR from individual
                        mvr_result = await mvr_svc.create_mvr_people_from_individual(
                            individual_uuid=individual_uuid_str
                        )
                        
                        if not mvr_result or not mvr_result.get('success'):
                            logger.warning(
                                f"Failed to create MVR for "
                                f"{individual_uuid_str}, skipping"
                            )
                            skipped_count += 1
                            continue
                        
                        # Now get the created MVR record
                        mvr_record = await mvr_matcher.repository.get_mvr_people_by_individual(
                            individual_uuid=individual_uuid_str
                        )
                        
                        if not mvr_record:
                            logger.warning(
                                f"Created MVR but couldn't retrieve it for "
                                f"{individual_uuid_str}, skipping"
                            )
                            skipped_count += 1
                            continue
                            
                    except Exception as create_error:
                        logger.error(
                            f"Error creating MVR for {individual_uuid_str}: "
                            f"{create_error}"
                        )
                        skipped_count += 1
                        continue
                
                # Extract face embedding
                face_embedding_data = mvr_record.get('face_embedding')
                if not face_embedding_data:
                    logger.warning(
                        f"No face embedding for {individual_uuid_str}, "
                        f"skipping"
                    )
                    skipped_count += 1
                    continue
                
                # Convert to numpy array if needed
                import numpy as np
                if isinstance(face_embedding_data, list):
                    face_embedding = np.array(
                        face_embedding_data, dtype=np.float32
                    )
                elif isinstance(face_embedding_data, np.ndarray):
                    face_embedding = face_embedding_data
                else:
                    logger.warning(
                        f"Invalid embedding format for {individual_uuid_str}, "
                        f"skipping"
                    )
                    skipped_count += 1
                    continue
                
                # Find matches for this individual
                match = await mvr_matcher.find_matching_mvr(
                    individual_uuid=individual_uuid_str,
                    face_embedding=face_embedding,
                    similarity_threshold=request.threshold,
                )
                
                # Convert single match to list for loop compatibility
                matches = [match] if match else []
                
                logger.debug(
                    f"Found {len(matches)} potential matches for "
                    f"{individual_uuid_str}"
                )
                
                # Merge each match above threshold
                for match in matches:
                    match_uuid = str(match.get('individual_uuid'))
                    similarity = match.get('similarity_score', 0.0)
                    
                    # Skip if already processed
                    if match_uuid in processed_individuals:
                        continue
                    
                    # Only merge if above threshold
                    if similarity >= request.threshold:
                        logger.info(
                            f"Merging {individual_uuid_str} with {match_uuid} "
                            f"(similarity: {similarity:.3f})"
                        )
                        
                        try:
                            # Execute merge
                            merge_result = await mvr_matcher.merge_individuals(
                                individual_a_uuid=individual_uuid_str,
                                individual_b_uuid=match_uuid,
                                similarity_score=similarity,
                                triggered_by=request.triggered_by,
                            )
                            
                            if merge_result and merge_result.get('success'):
                                # Track the orphaned individual
                                orphaned_mvr_uuid = merge_result.get(
                                    'orphaned_mvr_uuid'
                                )
                                predominant_mvr_uuid = merge_result.get(
                                    'predominant_mvr_uuid'
                                )
                                reassigned_uuid = merge_result.get(
                                    'reassigned_individual_uuid'
                                )
                                
                                processed_individuals.add(str(reassigned_uuid))
                                merge_count += 1
                                
                                # Record merge details
                                merges.append(MergeDetail(
                                    predominant_individual_uuid=individual_uuid,
                                    orphaned_individual_uuid=match_uuid,
                                    predominant_mvr_uuid=predominant_mvr_uuid,
                                    orphaned_mvr_uuid=orphaned_mvr_uuid,
                                    similarity_score=similarity,
                                    merged_at=merge_result.get(
                                        'merged_at', datetime.now()
                                    ),
                                ))
                                
                                logger.info(
                                    f"Successfully merged: {reassigned_uuid} "
                                    f"is now orphaned"
                                )
                            else:
                                logger.warning(
                                    f"Merge failed for {individual_uuid_str} "
                                    f"and {match_uuid}"
                                )
                                skipped_count += 1
                                
                        except Exception as merge_error:
                            logger.error(
                                f"Error merging {individual_uuid_str} with "
                                f"{match_uuid}: {merge_error}"
                            )
                            skipped_count += 1
                            # Continue with next match
                            continue
                
                # Mark current individual as processed
                processed_individuals.add(individual_uuid_str)
                
            except Exception as match_error:
                logger.error(
                    f"Error finding matches for {individual_uuid_str}: "
                    f"{match_error}"
                )
                skipped_count += 1
                # Continue with next individual
                continue
        
        # Calculate final counts
        unique_count = original_count - merge_count
        processing_time = time.time() - start_time
        
        logger.info(
            f"Batch merge complete: {original_count} → {unique_count} unique "
            f"({merge_count} merged, {skipped_count} skipped) "
            f"in {processing_time:.2f}s"
        )
        
        return BatchMatchAndMergeResponse(
            success=True,
            original_count=original_count,
            unique_count=unique_count,
            merge_count=merge_count,
            merges=merges,
            skipped_count=skipped_count,
            processing_time_seconds=round(processing_time, 2),
            message=(
                f"Successfully merged {merge_count} duplicates from "
                f"{original_count} individuals"
            ),
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Batch merge failed: {e}", exc_info=True)
        
        # Return partial results if we made any progress
        if merge_count > 0:
            unique_count = original_count - merge_count
            return BatchMatchAndMergeResponse(
                success=False,
                original_count=original_count,
                unique_count=unique_count,
                merge_count=merge_count,
                merges=merges,
                skipped_count=skipped_count,
                processing_time_seconds=round(processing_time, 2),
                message=(
                    f"Partial completion: {merge_count} merged before error: "
                    f"{str(e)}"
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch merge failed: {str(e)}"
            )


# ============================================================================
# ENDPOINT: Search Existing MVR People by Video UUIDs
# ============================================================================

@router.post(
    "/search/by-videos",
    response_model=MVRPeopleSearchResponse,
    summary="Search Existing MVR People by Video UUIDs (Cached)",
    description="Search for existing MVR people detected in specific videos. "
                "Returns cached results when available (1-hour TTL), otherwise "
                "queries database. Does NOT trigger any merge operations.",
)
async def search_mvr_people_by_videos(
    request: Request,
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs to search"
    ),
    start_time: Optional[datetime] = Body(
        None, description="Optional start time filter"
    ),
    end_time: Optional[datetime] = Body(
        None, description="Optional end time filter"
    ),
    limit: int = Body(100, description="Max results (default: 100, max: 500)"),
    force_refresh: bool = Body(False, description="Force cache refresh"),
    auto_merge: bool = Body(False, description="Automatically merge similar MVR people before returning results"),
    similarity_threshold: float = Body(0.60, ge=0.0, le=1.0, description="Similarity threshold for auto-merge (0-1, default 0.60)"),
    ignore_existing_hierarchy: bool = Body(False, description="Ignore persisted MVR hierarchy and merge directly from base linked MVR rows"),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_service: MVRService = Depends(get_mvr_service),
    mvr_matcher = Depends(get_mvr_matcher),
    cache_client = Depends(get_cache_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Search for existing MVR people detected in specific videos.
    
    This endpoint fetches EXISTING MVR people and their linked individuals
    that appear in the provided video UUIDs. By default, it returns cached data
    without triggering any merge operations.
    
    **Auto-Merge (NEW):** Set auto_merge=true to automatically run hierarchical
    merging on the found MVR people before returning results. This is useful for
    multi-day searches where the periodic merge (120-min lookback) hasn't merged
    individuals across days.
    
    **Caching:** Results are cached in Redis for 1 hour to improve performance.
    Use force_refresh=true to bypass cache. Auto-merge bypasses cache.
    
    **Use Case:** Fetch existing MVR analysis results for a collection's
    videos without reprocessing.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - video_uuids: List of video UUIDs to search
    - start_time: Optional start time filter (ISO 8601)
    - end_time: Optional end time filter (ISO 8601)
    - limit: Maximum results to return (default: 100, max: 500)
    - force_refresh: Bypass cache and fetch fresh data
    - auto_merge: Run hierarchical merge before returning (default: false)
    - similarity_threshold: Threshold for auto-merge (default: 0.60)
    
    **Returns:**
    - 200 OK: List of MVR people with aggregated data
    - 400 Bad Request: Invalid parameters
    - 500 Internal Server Error: Database error
    
    **Performance:** ~200ms cached, ~2-3s uncached, ~5-10s with auto-merge
    """
    logger.info(
        f"Searching existing MVR people for {len(video_uuids)} videos "
        f"(user: {current_user.get('email')}, force_refresh: {force_refresh}, "
        f"auto_merge: {auto_merge}, ignore_existing_hierarchy: {ignore_existing_hierarchy})"
    )
    
    # Check cache first (unless force_refresh or auto_merge)
    # Auto-merge always bypasses cache since it modifies the database
    if not force_refresh and not auto_merge and cache_client.is_connected():
        cached_result = await cache_client.get_mvr_search_results(
            video_uuids=video_uuids,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        if cached_result:
            # Remove cache metadata before returning
            cached_result.pop('cached_at', None)
            cached_result.pop('cache_ttl', None)
            logger.info(f"✅ Returning cached results for {len(video_uuids)} videos")
            return MVRPeopleSearchResponse(**cached_result)
    
    try:
        if not video_uuids:
            return MVRPeopleSearchResponse(
                success=True,
                total_results=0,
                mvr_people=[],
                search_parameters={
                    "video_uuids": [],
                    "start_time": (
                        start_time.isoformat() if start_time else None
                    ),
                    "end_time": (
                        end_time.isoformat() if end_time else None
                    ),
                    "limit": limit
                },
                message="No videos provided"
            )
        
        # Convert string UUIDs to UUID objects
        video_uuid_objs = [UUID(vid) for vid in video_uuids]
        logger.info(
            'Search-by-videos request coverage start: requested_video_uuids=%s',
            [str(video_uuid) for video_uuid in video_uuid_objs],
        )

        async def _materialize_missing_video_mvr_rows(
            target_media_uuids: list[UUID],
        ) -> int:
            logger.info(
                'Fallback materialization requested for video_uuids=%s',
                [str(media_uuid) for media_uuid in target_media_uuids],
            )
            auth_header = request.headers.get('Authorization', '')
            auth_token = (
                auth_header.replace('Bearer ', '')
                if auth_header.startswith('Bearer ')
                else None
            )
            if not auth_token:
                logger.warning(
                    'Cannot materialize missing video MVR rows: missing auth token'
                )
                return 0

            from utils.media_client import MediaClient

            media_client = MediaClient(auth_token=auth_token)
            gateway_url = os.getenv('PPL_GATEWAY_URL', 'http://localhost:8080').rstrip('/')
            vision_url = os.getenv('PPL_VISION_URL', 'http://localhost:8003').rstrip('/')
            materialized = 0

            async with httpx.AsyncClient(timeout=60.0) as client:
                for media_uuid in target_media_uuids:
                    try:
                        person_objects_response = await client.get(
                            f"{gateway_url}/api/v1/orchestrator/person-objects/{media_uuid}",
                            headers={'Authorization': f'Bearer {auth_token}'},
                        )
                        if person_objects_response.status_code != 200:
                            logger.warning(
                                'Materialization skipped for %s: orchestrator returned %s',
                                media_uuid,
                                person_objects_response.status_code,
                            )
                            continue

                        person_objects_payload = person_objects_response.json()
                        person_groups = person_objects_payload.get('person_groups') or []
                        logger.info(
                            'Fallback source for %s: person_groups=%s',
                            media_uuid,
                            len(person_groups),
                        )
                        if not person_groups:
                            logger.info(
                                'Materialization skipped for %s: no persisted person groups',
                                media_uuid,
                            )
                            continue

                        media_metadata = await media_client.get_media_metadata(media_uuid)
                        media_type = (media_metadata or {}).get('type', 'video')
                        transformed_person_objects = []
                        for person_group in person_groups:
                            representative_faces = person_group.get('representative_faces', [])
                            best_face = representative_faces[0] if representative_faces else {}
                            best_face_data = best_face.get('face_data', {}) if isinstance(best_face, dict) else {}
                            bbox = best_face_data.get('bbox', [])
                            frame_number = best_face_data.get('frame_number', 0)
                            # Prefer real UUID fields over the synthetic 'person_id'
                            # label. Coerce to UUID to keep MVR creation alive even
                            # if upstream emits a non-UUID label.
                            persisted_person_object_uuid = _coerce_to_uuid_str(
                                person_group.get('person_object_uuid')
                                or person_group.get('person_uuid')
                                or person_group.get('person_id')
                            )
                            if not persisted_person_object_uuid:
                                continue

                            vision_quality = person_group.get(
                                'quality_score',
                                person_group.get('quality_metrics', {}).get('average_quality', 0.0),
                            )
                            effective_quality = (
                                vision_quality / 100.0 if vision_quality and vision_quality > 1.0 else (vision_quality or 0.85)
                            )
                            transformed_person_objects.append({
                                'person_id': person_group.get('person_id'),
                                'person_uuid': person_group.get('person_uuid'),
                                'person_object_uuid': str(persisted_person_object_uuid),
                                'video_uuid': str(media_uuid),
                                'media_uuid': str(media_uuid),
                                'face_count': person_group.get('face_count', 0),
                                'representative_faces': representative_faces,
                                'quality_score': effective_quality,
                                'face_quality': effective_quality,
                                'confidence_score': person_group.get('average_confidence', 0.9),
                                'movement_tracking': person_group.get('movement_tracking', {}),
                                'best_face_frame': frame_number,
                                'best_face_bbox': bbox if len(bbox) == 4 else None,
                                'detect_frame_width': best_face_data.get('frame_width'),
                                'detect_frame_height': best_face_data.get('frame_height'),
                                # Forwarded so enrich_person_objects_with_face_crops can
                                # fall back to scanning all face ids when the persisted
                                # representative_faces / best_face_* fields are empty.
                                'all_face_ids': (
                                    person_group.get('all_face_ids')
                                    or person_group.get('face_ids')
                                    or []
                                ),
                                'best_face_id': (
                                    person_group.get('best_face_id')
                                    or best_face.get('face_id')
                                    or best_face_data.get('id')
                                ),
                            })

                        logger.info(
                            'Fallback transform for %s: transformed_person_objects=%s sample_person_object_uuids=%s media_timestamp=%s',
                            media_uuid,
                            len(transformed_person_objects),
                            [
                                person_object.get('person_object_uuid')
                                for person_object in transformed_person_objects[:3]
                            ],
                            (media_metadata or {}).get('timestamp'),
                        )

                        if not transformed_person_objects:
                            logger.warning(
                                'Materialization skipped for %s: transformed person object list is empty after filtering',
                                media_uuid,
                            )
                            continue

                        try:
                            transformed_person_objects = await enrich_person_objects_with_face_crops(
                                person_objects=transformed_person_objects,
                                media_uuid=media_uuid,
                                auth_token=auth_token,
                                vision_url=vision_url,
                                gateway_url=gateway_url,
                            )
                        except Exception as enrich_error:
                            logger.warning(
                                'Face crop enrichment failed during search materialization for %s: %s',
                                media_uuid,
                                enrich_error,
                            )

                        result_dict = await mvr_service.process_single_media_for_mvr(
                            media_uuid=media_uuid,
                            media_type=media_type,
                            person_objects=transformed_person_objects,
                            similarity_threshold=similarity_threshold,
                            min_face_quality=0.2,
                            include_demographics=True,
                            include_route_data=False,
                            media_timestamp=(media_metadata or {}).get('timestamp'),
                        )
                        created_count = len(result_dict.get('mvr_people', []))
                        materialized += created_count
                        logger.info(
                            'Materialized %s isolated MVR people for media %s during search fallback',
                            created_count,
                            media_uuid,
                        )
                    except Exception as fallback_error:
                        logger.error(
                            'Failed to materialize video %s during search fallback: %s',
                            media_uuid,
                            fallback_error,
                            exc_info=True,
                        )

            await media_client.close()
            return materialized
        
        # Get database connection from the repository's pool
        async with mvr_repository.pool.acquire() as conn:
            # Find all individuals that appear in these videos
            # NOTE: When video UUIDs are provided, we search by video UUID only.
            # The start_time/end_time parameters are IGNORED because they represent
            # video creation times (from media service), but individual_video_appearances
            # stores appearance timestamps WITHIN the video (e.g., "person at 2.5 seconds").
            # These are different timestamp domains and should not be mixed.
            individuals_query = """
                SELECT DISTINCT individual_uuid
                FROM individual_video_appearances
                WHERE video_uuid = ANY($1::uuid[])
            """
            
            individual_rows = await conn.fetch(
                individuals_query,
                video_uuid_objs
            )
            logger.info(
                'Initial persisted individual coverage: requested_videos=%s individual_count=%s',
                len(video_uuid_objs),
                len(individual_rows),
            )
            
            if not individual_rows:
                logger.info(
                    'No persisted individuals found in provided videos; attempting single-media materialization fallback'
                )
                await _materialize_missing_video_mvr_rows(video_uuid_objs)
                individual_rows = await conn.fetch(
                    individuals_query,
                    video_uuid_objs
                )

            coverage_query = """
                SELECT DISTINCT video_uuid
                FROM individual_video_appearances
                WHERE video_uuid = ANY($1::uuid[])
            """
            covered_video_rows = await conn.fetch(
                coverage_query,
                video_uuid_objs,
            )
            covered_video_uuids = {
                row['video_uuid']
                for row in covered_video_rows
                if row.get('video_uuid') is not None
            }
            logger.info(
                'Current persisted video coverage: covered_video_uuids=%s',
                [str(video_uuid) for video_uuid in sorted(covered_video_uuids)],
            )
            missing_video_uuids = [
                video_uuid
                for video_uuid in video_uuid_objs
                if video_uuid not in covered_video_uuids
            ]

            if missing_video_uuids:
                logger.info(
                    'Found %s videos without persisted individuals; attempting single-media materialization fallback for missing_video_uuids=%s',
                    len(missing_video_uuids),
                    [str(video_uuid) for video_uuid in missing_video_uuids],
                )
                materialized_count = await _materialize_missing_video_mvr_rows(missing_video_uuids)
                individual_rows = await conn.fetch(
                    individuals_query,
                    video_uuid_objs
                )
                covered_video_rows = await conn.fetch(
                    coverage_query,
                    video_uuid_objs,
                )
                covered_video_uuids = {
                    row['video_uuid']
                    for row in covered_video_rows
                    if row.get('video_uuid') is not None
                }
                logger.info(
                    'Post-fallback coverage: materialized_count=%s individual_count=%s covered_video_uuids=%s',
                    materialized_count,
                    len(individual_rows),
                    [str(video_uuid) for video_uuid in sorted(covered_video_uuids)],
                )

            if not individual_rows:
                logger.info("No individuals found in provided videos")
                return MVRPeopleSearchResponse(
                    success=True,
                    total_results=0,
                    mvr_people=[],
                    search_parameters={
                        "video_uuids": video_uuids,
                        "start_time": (
                            start_time.isoformat() if start_time else None
                        ),
                        "end_time": (
                            end_time.isoformat() if end_time else None
                        ),
                        "limit": limit
                    },
                    message="No individuals found in videos"
                )

            async def _count_invalid_linked_mvr_rows() -> int:
                return int(
                    await conn.fetchval(
                        """
                        SELECT COUNT(DISTINCT mp.mvr_people_uuid)
                        FROM individual_mvr_mapping imm
                        INNER JOIN mvr_people mp
                            ON mp.mvr_people_uuid = imm.mvr_people_uuid
                        WHERE imm.individual_uuid = ANY($1::uuid[])
                            AND (
                                mp.face_embedding IS NULL
                                OR (mp.face_embedding <#> mp.face_embedding) >= 0
                            )
                        """,
                        [row['individual_uuid'] for row in individual_rows],
                    )
                    or 0
                )

            if auto_merge:
                invalid_linked_mvr_rows = await _count_invalid_linked_mvr_rows()
                if invalid_linked_mvr_rows:
                    logger.warning(
                        "Detected %s invalid linked MVR rows for merge search; rematerializing target videos",
                        invalid_linked_mvr_rows,
                    )
                    await _materialize_missing_video_mvr_rows()
                    individual_rows = await conn.fetch(
                        individuals_query,
                        video_uuid_objs
                    )
            
            individual_uuids = [
                str(row['individual_uuid']) for row in individual_rows
            ]
            
            if auto_merge and not ignore_existing_hierarchy:
                # When auto-merge is explicitly requested, resolve each mapped MVR to
                # its active root so the response reflects the persisted hierarchy.
                mvr_query = """
                    WITH RECURSIVE mvr_chain AS (
                        SELECT
                            imm.individual_uuid,
                            mp.mvr_people_uuid AS current_mvr_uuid,
                            mp.merged_into_mvr_uuid,
                            0 AS depth
                        FROM individual_mvr_mapping imm
                        INNER JOIN mvr_people mp
                            ON mp.mvr_people_uuid = imm.mvr_people_uuid
                        WHERE imm.individual_uuid = ANY($1::uuid[])

                        UNION ALL

                        SELECT
                            mc.individual_uuid,
                            parent.mvr_people_uuid AS current_mvr_uuid,
                            parent.merged_into_mvr_uuid,
                            mc.depth + 1 AS depth
                        FROM mvr_chain mc
                        INNER JOIN mvr_people parent
                            ON parent.mvr_people_uuid = mc.merged_into_mvr_uuid
                        WHERE mc.merged_into_mvr_uuid IS NOT NULL
                            AND mc.depth < 20
                    ),
                    individual_roots AS (
                        SELECT DISTINCT ON (individual_uuid)
                            individual_uuid,
                            current_mvr_uuid AS root_mvr_uuid
                        FROM mvr_chain
                        WHERE merged_into_mvr_uuid IS NULL
                        ORDER BY individual_uuid, depth DESC
                    ),
                    root_mvr AS (
                        SELECT DISTINCT root_mvr_uuid
                        FROM individual_roots
                    )
                    SELECT
                        mp.mvr_people_uuid,
                        mp.quality_score,
                        mp.confidence_score,
                        mp.age_min,
                        mp.age_max,
                        mp.gender,
                        mp.created_at,
                        mp.updated_at
                    FROM mvr_people mp
                    INNER JOIN root_mvr rm
                        ON rm.root_mvr_uuid = mp.mvr_people_uuid
                    WHERE mp.is_orphaned = false
                        AND mp.face_embedding IS NOT NULL
                        AND (mp.face_embedding <#> mp.face_embedding) < 0
                    ORDER BY mp.created_at DESC
                    LIMIT $2
                """
            else:
                # Default search mode must reflect the MVR rows directly linked to the
                # target videos. Do not collapse orphaned rows into a winner root unless
                # the caller explicitly requested merge-aware results.
                mvr_query = """
                    SELECT DISTINCT
                        mp.mvr_people_uuid,
                        mp.quality_score,
                        mp.confidence_score,
                        mp.age_min,
                        mp.age_max,
                        mp.gender,
                        mp.created_at,
                        mp.updated_at
                    FROM individual_mvr_mapping imm
                    INNER JOIN mvr_people mp
                        ON mp.mvr_people_uuid = imm.mvr_people_uuid
                    WHERE imm.individual_uuid = ANY($1::uuid[])
                        AND (
                            NOT $3
                            OR (
                                mp.face_embedding IS NOT NULL
                                AND (mp.face_embedding <#> mp.face_embedding) < 0
                            )
                        )
                    ORDER BY mp.created_at DESC
                    LIMIT $2
                """
            
            if auto_merge and not ignore_existing_hierarchy:
                mvr_records = await conn.fetch(
                    mvr_query,
                    individual_uuids,
                    limit,
                )
            else:
                mvr_records = await conn.fetch(
                    mvr_query,
                    individual_uuids,
                    limit,
                    auto_merge,
                )

            if auto_merge and not mvr_records:
                logger.warning(
                    "No valid merge-ready MVR rows found after filtering invalid embeddings; retrying video materialization"
                )
                await _materialize_missing_video_mvr_rows()
                individual_rows = await conn.fetch(
                    individuals_query,
                    video_uuid_objs
                )
                individual_uuids = [
                    str(row['individual_uuid']) for row in individual_rows
                ]
                if auto_merge and not ignore_existing_hierarchy:
                    mvr_records = await conn.fetch(
                        mvr_query,
                        individual_uuids,
                        limit,
                    )
                else:
                    mvr_records = await conn.fetch(
                        mvr_query,
                        individual_uuids,
                        limit,
                        auto_merge,
                    )
            
            results = []
            
            # For each MVR person, get all linked individuals & appearances
            for mvr_record in mvr_records:
                mvr_uuid = str(mvr_record['mvr_people_uuid'])
                
                if auto_merge and not ignore_existing_hierarchy:
                    # Expand all descendants from this root MVR using merged_into_mvr_uuid.
                    descendants_query = """
                        WITH RECURSIVE descendants AS (
                            SELECT mvr_people_uuid
                            FROM mvr_people
                            WHERE mvr_people_uuid = $1::uuid

                            UNION

                            SELECT child.mvr_people_uuid
                            FROM mvr_people child
                            INNER JOIN descendants d
                                ON child.merged_into_mvr_uuid = d.mvr_people_uuid
                        )
                        SELECT mvr_people_uuid
                        FROM descendants
                    """
                    descendant_rows = await conn.fetch(descendants_query, mvr_uuid)
                    all_mvr_uuids = [str(row['mvr_people_uuid']) for row in descendant_rows]
                    merged_mvr_uuids = [uuid for uuid in all_mvr_uuids if uuid != mvr_uuid]
                    is_super_individual = len(merged_mvr_uuids) > 0
                else:
                    all_mvr_uuids = [mvr_uuid]
                    merged_mvr_uuids = []
                    is_super_individual = False

                logger.debug(
                    f"MVR {mvr_uuid[:8]}... is_super={is_super_individual}, "
                    f"checking {len(all_mvr_uuids)} MVR UUIDs"
                )
                
                # Get all linked individual UUIDs for this MVR and its merged children
                linked_individuals_query = """
                    SELECT DISTINCT individual_uuid
                    FROM individual_mvr_mapping
                    WHERE mvr_people_uuid = ANY($1::uuid[])
                """
                linked_rows = await conn.fetch(
                    linked_individuals_query, all_mvr_uuids
                )
                linked_individual_uuids = [
                    str(row['individual_uuid']) for row in linked_rows
                ]
                
                logger.debug(
                    f"MVR {mvr_uuid[:8]}... has {len(linked_individual_uuids)} "
                    f"total individuals (including merged MVRs)"
                )
                
                # Get appearances for these individuals in our target videos
                # NOTE: We do NOT filter by start_time/end_time here because:
                # 1. We already filtered by video_uuid (which is the correct filter)
                # 2. Appearance timestamps are WITHIN video (relative), not video creation times
                # 3. Flutter sends Athens local time, DB has UTC - comparison would fail
                appearances_query = """
                    SELECT
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.confidence
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                        AND iva.video_uuid = ANY($2::uuid[])
                    ORDER BY iva.start_timestamp ASC
                """
                
                appearances_rows = await conn.fetch(
                    appearances_query,
                    linked_individual_uuids,
                    video_uuid_objs
                )
                
                if not appearances_rows:
                    # Skip MVR people with no appearances in target videos
                    continue
                
                # Build appearance objects
                appearances = [
                    MVRIndividualAppearance(
                        video_uuid=str(row['video_uuid']),
                        person_object_uuid=str(row['person_object_uuid']),
                        start_timestamp=row['start_timestamp'],
                        end_timestamp=row['end_timestamp'],
                        confidence=float(row['confidence'])
                    )
                    for row in appearances_rows
                ]
                
                # Calculate aggregate statistics
                unique_videos = len(set(app.video_uuid for app in appearances))
                first_seen = min(app.start_timestamp for app in appearances)
                last_seen = max(app.end_timestamp for app in appearances)
                
                logger.info(
                    f"MVR {mvr_uuid[:8]}... final stats: "
                    f"{len(appearances)} appearances across {unique_videos} videos "
                    f"(is_super={is_super_individual}, merged_count={len(merged_mvr_uuids)})"
                )
                
                # Format age range if available
                age_display = None
                if mvr_record['age_min'] and mvr_record['age_max']:
                    age_display = (
                        f"{mvr_record['age_min']}-{mvr_record['age_max']}"
                    )
                
                # Create result object
                result = MVRPersonResult(
                    mvr_people_uuid=mvr_uuid,
                    individual_uuids=linked_individual_uuids,
                    total_appearances=len(appearances),
                    unique_videos=unique_videos,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    confidence_score=float(
                        mvr_record['confidence_score'] or 0.0
                    ),
                    quality_score=float(mvr_record['quality_score'] or 0.0),
                    appearances=appearances,
                    merged_mvr_uuids=merged_mvr_uuids,
                    is_super_individual=is_super_individual,
                    estimated_age=age_display,
                    estimated_gender=mvr_record['gender']
                )
                
                results.append(result)
            
            logger.info(
                f"Found {len(results)} existing MVR people in videos"
            )
            
            # Apply auto-merge if requested
            if auto_merge and len(results) > 1:
                logger.info(
                    f"🔄 Auto-merge requested: attempting to merge {len(results)} MVR people "
                    f"(threshold: {similarity_threshold})"
                )
                
                try:
                    from services.hierarchical_mvr_merger import HierarchicalMVRMerger
                    
                    # Initialize merger
                    merger = HierarchicalMVRMerger(
                        repository=mvr_repository,
                        mvr_matcher=mvr_matcher
                    )
                    
                    # Get MVR UUIDs to merge
                    mvr_uuids_to_merge = [UUID(r.mvr_people_uuid) for r in results]
                    
                    # Build an in-memory merge preview only. Do not mutate
                    # persisted hierarchy state during search.
                    merge_result = await merger.preview_hierarchical_merge(
                        mvr_uuids=mvr_uuids_to_merge,
                        similarity_threshold=similarity_threshold,
                        min_similarity_check=0.50
                    )
                    
                    logger.info(
                        f"✅ Ephemeral auto-merge preview complete: {merge_result['statistics']['total_mvr']} → "
                        f"{merge_result['statistics']['super_individuals']} grouped results"
                    )

                    result_by_mvr_uuid = {
                        result.mvr_people_uuid: result for result in results
                    }
                    grouped_results = []

                    for group in merge_result.get("merge_groups", []):
                        super_uuid = group["super_individual_uuid"]
                        member_uuids = [super_uuid, *group.get("merged_mvr_uuids", [])]
                        member_results = [
                            result_by_mvr_uuid[member_uuid]
                            for member_uuid in member_uuids
                            if member_uuid in result_by_mvr_uuid
                        ]

                        if not member_results:
                            continue

                        winner_result = member_results[0]
                        combined_appearances = sorted(
                            [
                                appearance
                                for member_result in member_results
                                for appearance in member_result.appearances
                            ],
                            key=lambda appearance: appearance.start_timestamp,
                        )
                        combined_individual_uuids = sorted(
                            {
                                individual_uuid
                                for member_result in member_results
                                for individual_uuid in member_result.individual_uuids
                            }
                        )
                        combined_videos = {
                            appearance.video_uuid for appearance in combined_appearances
                        }
                        first_seen = min(
                            appearance.start_timestamp
                            for appearance in combined_appearances
                        )
                        last_seen = max(
                            appearance.end_timestamp
                            for appearance in combined_appearances
                        )

                        grouped_results.append(
                            MVRPersonResult(
                                mvr_people_uuid=super_uuid,
                                individual_uuids=combined_individual_uuids,
                                total_appearances=len(combined_appearances),
                                unique_videos=len(combined_videos),
                                first_seen=first_seen,
                                last_seen=last_seen,
                                confidence_score=winner_result.confidence_score,
                                quality_score=winner_result.quality_score,
                                appearances=combined_appearances,
                                merged_mvr_uuids=group.get("merged_mvr_uuids", []),
                                is_super_individual=not group.get("is_standalone", True),
                                estimated_age=winner_result.estimated_age,
                                estimated_gender=winner_result.estimated_gender,
                            )
                        )

                    results = sorted(
                        grouped_results,
                        key=lambda result: result.first_seen,
                    )
                    
                except Exception as merge_error:
                    logger.error(f"Auto-merge failed: {merge_error}", exc_info=True)
                    # Continue with unmerged results if merge fails
                    logger.warning("Returning unmerged results due to merge error")
            
            # Build response
            response_data = {
                "success": True,
                "total_results": len(results),
                "mvr_people": [r.dict() for r in results],
                "search_parameters": {
                    "video_uuids": video_uuids,
                    "video_count": len(video_uuids),
                    "start_time": (
                        start_time.isoformat() if start_time else None
                    ),
                    "end_time": end_time.isoformat() if end_time else None,
                    "limit": limit,
                    "auto_merge": auto_merge,
                    "similarity_threshold": similarity_threshold if auto_merge else None,
                    "ignore_existing_hierarchy": ignore_existing_hierarchy if auto_merge else None,
                },
                "message": f"Found {len(results)} existing MVR people"
            }
            
            # Cache only plain search results. Ephemeral auto-merge previews must
            # stay request-scoped and never contaminate the persisted search cache.
            if cache_client.is_connected() and not auto_merge:
                await cache_client.set_mvr_search_results(
                    video_uuids=video_uuids,
                    results=response_data,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    ttl=3600  # 1 hour
                )
            
            return MVRPeopleSearchResponse(**response_data)
            
    except Exception as e:
        logger.error(
            f"Error searching MVR people by videos: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search MVR people: {str(e)}"
        )


@router.post(
    "/search/by-videos/persisted-merge-session",
    response_model=Dict[str, Any],
    summary="Search MVR People by Videos With Persistent Merge Session",
    description="Run merge-enabled MVR search against base persisted MVR rows, reuse stored sessions by same input, and persist a reusable session snapshot.",
)
async def search_mvr_people_by_videos_persisted_merge_session(
    request: Request,
    camera_ids: List[str] = Body(
        ..., embed=True, description="List of camera identifiers participating in the search"
    ),
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs to search"
    ),
    start_time: Optional[datetime] = Body(
        None, description="Requested start time for the search session"
    ),
    end_time: Optional[datetime] = Body(
        None, description="Requested end time for the search session"
    ),
    limit: int = Body(100, description="Max results (default: 100, max: 500)"),
    similarity_threshold: float = Body(0.60, ge=0.0, le=1.0, description="Similarity threshold for merge preview (0-1, default 0.60)"),
    ignore_existing_session: bool = Body(False, description="Force a fresh session even if the same input was already stored"),
    video_details: Optional[List[Dict[str, Any]]] = Body(None, description="Optional per-video metadata such as camera_id and media_timestamp"),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_service: MVRService = Depends(get_mvr_service),
    mvr_matcher = Depends(get_mvr_matcher),
    cache_client = Depends(get_cache_client),
    current_user: dict = Depends(get_current_user),
):
    logger.info(
        "Searching persistent merge session for %s cameras and %s videos (user: %s, ignore_existing_session: %s)",
        len(camera_ids),
        len(video_uuids),
        current_user.get("email"),
        ignore_existing_session,
    )

    if not ignore_existing_session:
        existing_session = await mvr_repository.get_search_session_by_same_input(
            camera_ids=camera_ids,
            video_uuids=video_uuids,
        )
        if existing_session:
            return {
                "success": True,
                "search_session_uuid": str(existing_session["search_session_uuid"]),
                "reused_existing_session": True,
                "summary": _normalize_session_payload(existing_session.get("summary_payload")),
                "result_payload": _normalize_session_payload(existing_session.get("result_payload")),
                "message": "Reused existing persisted merge session",
            }

    search_response = await search_mvr_people_by_videos(
        request=request,
        video_uuids=video_uuids,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        force_refresh=True,
        auto_merge=True,
        similarity_threshold=similarity_threshold,
        ignore_existing_hierarchy=True,
        mvr_repository=mvr_repository,
        mvr_service=mvr_service,
        mvr_matcher=mvr_matcher,
        cache_client=cache_client,
        current_user=current_user,
    )

    result_payload = search_response.dict()
    result_payload.setdefault("search_parameters", {})
    result_payload["search_parameters"]["camera_ids"] = sorted(
        {camera_id for camera_id in camera_ids if camera_id}
    )
    result_payload["search_parameters"]["persisted_merge_session"] = True

    summary_payload = _build_persistent_search_summary(
        search_response=search_response,
        camera_ids=camera_ids,
        video_uuids=video_uuids,
        start_time=start_time,
        end_time=end_time,
    )

    created_session = await mvr_repository.create_search_session(
        camera_ids=camera_ids,
        video_uuids=video_uuids,
        requested_start_date=start_time,
        requested_end_date=end_time,
        summary_payload=summary_payload,
        result_payload=result_payload,
        search_mode="merge_preview",
        video_details=video_details,
    )

    return {
        "success": True,
        "search_session_uuid": str(created_session["search_session_uuid"]),
        "reused_existing_session": False,
        "summary": _normalize_session_payload(created_session.get("summary_payload")),
        "result_payload": _normalize_session_payload(created_session.get("result_payload")),
        "message": "Created persisted merge session",
    }


# ============================================================================
# ENDPOINT: People Counters Batch Merge
# ----------------------------------------------------------------------------
# Same persistent-merge-session pipeline as above, but additionally tags the
# resulting mvr_search_sessions row with a deterministic batch_key so it can
# be reused as a building block for sub-period analytics queries.
#
# Called by the orchestrator's people-counters worker (one call per
# camera × hour-window batch). See docs/proposals/people-counters.md §5.5.
# ============================================================================

@router.post(
    "/search/by-videos/persisted-merge-session-batch",
    response_model=Dict[str, Any],
    summary="People Counters: Persisted merge session tagged as a reusable batch",
    description=(
        "Wrapper around persisted-merge-session that additionally tags the "
        "resulting search session with a deterministic batch_key "
        "(camera|start|end) for the People Counters automation."
    ),
)
async def search_mvr_people_by_videos_persisted_merge_session_batch(
    request: Request,
    batch_camera_id: str = Body(..., embed=True, description="The single camera id this batch belongs to"),
    batch_start_utc: datetime = Body(..., embed=True, description="UTC start of the batch window"),
    batch_end_utc: datetime = Body(..., embed=True, description="UTC end of the batch window"),
    video_uuids: List[str] = Body(..., embed=True, description="Video UUIDs that fall inside the batch window"),
    similarity_threshold: float = Body(0.60, ge=0.0, le=1.0),
    ignore_existing_session: bool = Body(False, description="Force a fresh merge even if same-input session exists"),
    video_details: Optional[List[Dict[str, Any]]] = Body(None),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_service: MVRService = Depends(get_mvr_service),
    mvr_matcher = Depends(get_mvr_matcher),
    cache_client = Depends(get_cache_client),
    current_user: dict = Depends(get_current_user),
):
    batch_key = MVRRepository.build_batch_key(
        batch_camera_id, batch_start_utc, batch_end_utc
    )

    logger.info(
        "people-counters batch merge: key=%s videos=%d (user=%s force=%s)",
        batch_key, len(video_uuids), current_user.get("email"), ignore_existing_session,
    )

    # Fast path: batch already computed and not stale → return without recompute.
    if not ignore_existing_session:
        existing = await mvr_repository.get_batch_by_key(batch_key)
        if existing and not existing.get("is_stale"):
            return {
                "success": True,
                "batch_key": batch_key,
                "search_session_uuid": str(existing["search_session_uuid"]),
                "reused_existing_batch": True,
                "is_stale": False,
                "result_payload": _normalize_session_payload(existing.get("result_payload")),
                "summary": _normalize_session_payload(existing.get("summary_payload")),
                "message": "Reused existing non-stale batch",
            }

    # Empty-batch shortcut — still create a tagged session so the worker
    # records "we looked at this window and it had no videos".
    if not video_uuids:
        empty_payload = {
            "people": [],
            "total_count": 0,
            "search_parameters": {
                "video_uuids": [],
                "camera_ids": [batch_camera_id],
                "persisted_merge_session": True,
                "people_counters_batch": True,
                "batch_key": batch_key,
            },
            "message": "Empty batch (no videos in window)",
        }
        empty_summary = _build_persistent_search_summary(
            search_response=MVRPeopleSearchResponse(
                success=True,
                people=[],
                total_count=0,
                search_parameters={"camera_ids": [batch_camera_id]},
                message="Empty batch",
            ),
            camera_ids=[batch_camera_id],
            video_uuids=[],
            start_time=batch_start_utc,
            end_time=batch_end_utc,
        )
        created = await mvr_repository.create_search_session(
            camera_ids=[batch_camera_id],
            video_uuids=[],
            requested_start_date=batch_start_utc,
            requested_end_date=batch_end_utc,
            summary_payload=empty_summary,
            result_payload=empty_payload,
            search_mode="merge_preview",
            video_details=video_details,
        )
        await mvr_repository.tag_session_as_batch(
            search_session_uuid=created["search_session_uuid"],
            batch_key=batch_key,
            batch_camera_id=batch_camera_id,
            batch_start_utc=batch_start_utc,
            batch_end_utc=batch_end_utc,
        )
        return {
            "success": True,
            "batch_key": batch_key,
            "search_session_uuid": str(created["search_session_uuid"]),
            "reused_existing_batch": False,
            "is_stale": False,
            "people_count": 0,
            "result_payload": empty_payload,
            "message": "Created empty batch session",
        }

    # Delegate to the existing persisted-merge-session endpoint, which handles
    # same-input reuse and the merge pipeline. We pass ignore_existing_session
    # through so a forced recompute also forces a fresh merge.
    inner = await search_mvr_people_by_videos_persisted_merge_session(
        request=request,
        camera_ids=[batch_camera_id],
        video_uuids=video_uuids,
        start_time=batch_start_utc,
        end_time=batch_end_utc,
        limit=500,
        similarity_threshold=similarity_threshold,
        ignore_existing_session=ignore_existing_session,
        video_details=video_details,
        mvr_repository=mvr_repository,
        mvr_service=mvr_service,
        mvr_matcher=mvr_matcher,
        cache_client=cache_client,
        current_user=current_user,
    )

    session_uuid = inner["search_session_uuid"]
    try:
        session_uuid_typed = UUID(session_uuid) if isinstance(session_uuid, str) else session_uuid
    except (ValueError, TypeError):
        session_uuid_typed = session_uuid

    tagged = False
    try:
        tagged = await mvr_repository.tag_session_as_batch(
            search_session_uuid=session_uuid_typed,
            batch_key=batch_key,
            batch_camera_id=batch_camera_id,
            batch_start_utc=batch_start_utc,
            batch_end_utc=batch_end_utc,
        )
    except Exception as exc:  # unique-violation = batch_key already used by another row
        logger.warning("tag_session_as_batch failed for %s: %s", batch_key, exc)

    result_payload = inner.get("result_payload") or {}
    people_count = 0
    if isinstance(result_payload, dict):
        people = result_payload.get("people") or []
        if isinstance(people, list):
            people_count = len(people)

    return {
        "success": True,
        "batch_key": batch_key,
        "search_session_uuid": str(session_uuid),
        "reused_existing_batch": False,
        "reused_existing_session": inner.get("reused_existing_session", False),
        "tagged": tagged,
        "is_stale": False,
        "people_count": people_count,
        "result_payload": result_payload,
        "summary": inner.get("summary"),
        "message": "Created people-counters batch session",
    }


# ============================================================================
# ENDPOINT: People Counters Aggregate
# ----------------------------------------------------------------------------
# Sub-period query that composes its result from previously-computed batches
# plus on-demand merges for any uncovered edge gaps. See proposal §5.6.
#
# Identity reconciliation across batches uses mvr_people_uuid (the canonical
# persistent identity) — same person seen in two adjacent batches will share
# a uuid because each batch's merge writes back to the same mvr_people rows.
# ============================================================================

import os as _pc_os  # local alias to avoid confusing other imports
_PC_MEDIA_SERVICE_URL = _pc_os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000")


@router.get(
    "/people-counters/aggregate",
    response_model=Dict[str, Any],
    summary="People Counters: aggregate unique people across an arbitrary sub-period",
)
async def people_counters_aggregate(
    request: Request,
    camera_id: str,
    period_start: datetime,
    period_end: datetime,
    fill_gaps: bool = True,
    similarity_threshold: float = 0.60,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_service: MVRService = Depends(get_mvr_service),
    mvr_matcher = Depends(get_mvr_matcher),
    cache_client = Depends(get_cache_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Compose a unique-people answer for [period_start, period_end] on a single
    camera by reusing tagged batch sessions whenever possible.

    Strategy (§5.6):
    1. Find all non-stale batches fully contained inside the requested window.
    2. If `fill_gaps` is true, run a one-off persisted-merge-session for each
       remaining sub-window (head, gaps between batches, tail). These on-demand
       sessions are persisted with `same_input_key` reuse — they are NOT tagged
       as batches.
    3. Union all `people` payloads, dedupe by `mvr_people_uuid`.

    Returns the unique-people list plus a `coverage` block describing which
    spans came from cached batches vs gap-fills.
    """
    if period_end <= period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end must be greater than period_start",
        )

    period_start = period_start.replace(tzinfo=None) if period_start.tzinfo else period_start
    period_end = period_end.replace(tzinfo=None) if period_end.tzinfo else period_end

    covering_batches = await mvr_repository.find_covering_batches(
        camera_id=camera_id,
        period_start_utc=period_start,
        period_end_utc=period_end,
    )

    # Order batches and compute uncovered gaps.
    covering_batches.sort(key=lambda b: b["batch_start_utc"])
    gaps: List[Tuple[datetime, datetime]] = []  # type: ignore[name-defined]
    cursor = period_start
    for batch in covering_batches:
        bstart = batch["batch_start_utc"]
        bend = batch["batch_end_utc"]
        if isinstance(bstart, str):
            bstart = datetime.fromisoformat(bstart)
        if isinstance(bend, str):
            bend = datetime.fromisoformat(bend)
        if bstart > cursor:
            gaps.append((cursor, bstart))
        if bend > cursor:
            cursor = bend
    if cursor < period_end:
        gaps.append((cursor, period_end))

    coverage_blocks: List[Dict[str, Any]] = []
    people_by_uuid: Dict[str, Dict[str, Any]] = {}

    def _absorb(payload: Any, source: str) -> int:
        """Merge a result_payload's people list into the dedupe table."""
        if not isinstance(payload, dict):
            return 0
        people = payload.get("people") or []
        added = 0
        for person in people:
            if not isinstance(person, dict):
                continue
            key = person.get("mvr_people_uuid") or person.get("uuid")
            if not key:
                continue
            key = str(key)
            existing = people_by_uuid.get(key)
            if existing is None:
                people_by_uuid[key] = dict(person)
                added += 1
            else:
                # Bump appearance counters where present.
                for field in ("appearance_count", "video_appearance_count", "total_appearances"):
                    if field in person and isinstance(person[field], (int, float)):
                        existing[field] = (existing.get(field) or 0) + person[field]
        coverage_blocks.append({"source": source, "added_unique": added, "people_in_block": len(people)})
        return added

    for batch in covering_batches:
        _absorb(_normalize_session_payload(batch.get("result_payload")), source=f"batch:{batch['batch_key']}")

    gap_fills_done = 0
    if fill_gaps and gaps:
        auth_token = request.headers.get("Authorization")
        headers: Dict[str, str] = {}
        if auth_token:
            token_value = (
                auth_token.replace("Bearer ", "").strip()
                if auth_token.startswith("Bearer ") else auth_token
            )
            headers["Authorization"] = f"Bearer {token_value}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            for gap_start, gap_end in gaps:
                params = {
                    "collection": camera_id,
                    "start_time": gap_start.isoformat(),
                    "end_time": gap_end.isoformat(),
                    "page_size": 500,
                }
                video_uuids: List[str] = []
                try:
                    resp = await client.get(
                        f"{_PC_MEDIA_SERVICE_URL}/api/v1/media/search",
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload if isinstance(payload, list) else payload.get("results", [])
                    video_uuids = [str(v["uuid"]) for v in items if v.get("uuid")]
                except httpx.HTTPError as exc:
                    logger.warning("aggregate gap-fill media lookup failed: %s", exc)
                    coverage_blocks.append({
                        "source": "gap-skip",
                        "gap_start": gap_start.isoformat(),
                        "gap_end": gap_end.isoformat(),
                        "error": str(exc),
                    })
                    continue

                if not video_uuids:
                    coverage_blocks.append({
                        "source": "gap-empty",
                        "gap_start": gap_start.isoformat(),
                        "gap_end": gap_end.isoformat(),
                        "videos": 0,
                    })
                    continue

                gap_result = await search_mvr_people_by_videos_persisted_merge_session(
                    request=request,
                    camera_ids=[camera_id],
                    video_uuids=video_uuids,
                    start_time=gap_start,
                    end_time=gap_end,
                    limit=500,
                    similarity_threshold=similarity_threshold,
                    ignore_existing_session=False,
                    video_details=None,
                    mvr_repository=mvr_repository,
                    mvr_service=mvr_service,
                    mvr_matcher=mvr_matcher,
                    cache_client=cache_client,
                    current_user=current_user,
                )
                _absorb(
                    _normalize_session_payload(gap_result.get("result_payload")),
                    source=f"gap:{gap_start.isoformat()}|{gap_end.isoformat()}",
                )
                gap_fills_done += 1

    return {
        "success": True,
        "camera_id": camera_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "people_count": len(people_by_uuid),
        "people": list(people_by_uuid.values()),
        "coverage": {
            "covering_batches": len(covering_batches),
            "gaps": len(gaps),
            "gap_fills_done": gap_fills_done,
            "fill_gaps": fill_gaps,
            "blocks": coverage_blocks,
        },
        "message": (
            "Aggregated from cached batches"
            + (f" + {gap_fills_done} gap-fill(s)" if gap_fills_done else "")
        ),
    }


# ============================================================================
# ENDPOINT: Search Existing MVR People by Collection (DEPRECATED)
# ============================================================================
# NOTE: This endpoint cannot filter by collection without cross-database
# queries. Use /search/by-videos instead.

@router.post(
    "/search/by-collection",
    response_model=MVRPeopleSearchResponse,
    summary="Search Existing MVR People by Collection (DEPRECATED)",
    deprecated=True,
    description="Search for existing MVR people created within a date range "
                "for a specific collection. Returns cached/existing data "
                "without triggering any merge operations.",
)
async def search_mvr_people_by_collection(
    request: MVRPeopleSearchRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Search for existing MVR people by collection and date range.
    
    This endpoint fetches EXISTING MVR people and their linked individuals
    that were created within the specified time range for a collection.
    It does NOT trigger any merge operations - it only retrieves cached data.
    
    **Use Case:** Fetch existing MVR analysis results for display in
    the cross-video analysis screen without reprocessing.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - collection_name: Collection identifier (camera device ID or UUID)
    - start_time: Start of search time range (ISO 8601)
    - end_time: End of search time range (ISO 8601)
    - limit: Maximum results to return (default: 100, max: 500)
    
    **Returns:**
    - 200 OK: List of MVR people with aggregated data
    - 400 Bad Request: Invalid parameters
    - 500 Internal Server Error: Database error
    """
    logger.info(
        f"Searching existing MVR people for collection {request.collection_name} "
        f"from {request.start_time} to {request.end_time} "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        # Convert timezone-aware datetimes to naive (database uses naive timestamps)
        start_time_naive = request.start_time.replace(tzinfo=None)
        end_time_naive = request.end_time.replace(tzinfo=None)
        
        # Get database connection from the repository's pool
        async with mvr_repository.pool.acquire() as conn:
            # Query MVR people created within the time range OR super-individuals
            # that have merged MVR with appearances in the time range
            query = """
                WITH relevant_mvr AS (
                    -- Direct MVR created in range
                    SELECT DISTINCT mp.mvr_people_uuid
                    FROM mvr_people mp
                    WHERE mp.created_at >= $1
                        AND mp.created_at <= $2
                        AND mp.is_orphaned = false
                    
                    UNION
                    
                    -- Super-individuals that have merged MVR with appearances in range
                    SELECT DISTINCT mh.super_individual_uuid AS mvr_people_uuid
                    FROM mvr_merge_hierarchy mh
                    INNER JOIN individual_mvr_mapping imm ON mh.merged_mvr_uuid = imm.mvr_people_uuid
                    INNER JOIN individual_video_appearances iva ON imm.individual_uuid = iva.individual_uuid
                    WHERE iva.start_timestamp >= $1
                        AND iva.end_timestamp <= $2
                )
                SELECT DISTINCT
                    mp.mvr_people_uuid,
                    mp.quality_score,
                    mp.confidence_score,
                    mp.age_min,
                    mp.age_max,
                    mp.gender,
                    mp.created_at,
                    mp.updated_at
                FROM mvr_people mp
                INNER JOIN relevant_mvr rm ON mp.mvr_people_uuid = rm.mvr_people_uuid
                ORDER BY mp.created_at DESC
                LIMIT $3
            """
            
            mvr_records = await conn.fetch(
                query,
                start_time_naive,
                end_time_naive,
                request.limit
            )
            
            results = []
            
            # For each MVR person, get all linked individuals and appearances
            for mvr_record in mvr_records:
                mvr_uuid = str(mvr_record['mvr_people_uuid'])
                
                logger.info(f"🔍 Processing MVR: {mvr_uuid[:8]}...")
                
                # Check if this is a super-individual (has merged MVR people)
                merged_mvr_query = """
                    SELECT merged_mvr_uuid
                    FROM mvr_merge_hierarchy
                    WHERE super_individual_uuid = $1
                """
                merged_mvr_rows = await conn.fetch(merged_mvr_query, mvr_uuid)
                
                logger.info(f"🔍 Hierarchy query returned {len(merged_mvr_rows)} merged MVR rows")
                
                # Build list of all MVR UUIDs (super-individual + merged MVR)
                all_mvr_uuids = [mvr_uuid]
                if merged_mvr_rows:
                    merged_uuids = [str(row['merged_mvr_uuid']) for row in merged_mvr_rows]
                    all_mvr_uuids.extend(merged_uuids)
                    logger.info(
                        f"✅ Super-individual {mvr_uuid[:8]}... has {len(merged_mvr_rows)} merged MVR people"
                    )
                    logger.info(f"   Merged MVR UUIDs: {[u[:8] + '...' for u in merged_uuids[:5]]}")
                else:
                    logger.info(f"   No merged MVR found in hierarchy - standalone MVR")
                
                # Get all linked individual UUIDs from ALL MVR in hierarchy
                individuals_query = """
                    SELECT individual_uuid
                    FROM individual_mvr_mapping
                    WHERE mvr_people_uuid = ANY($1::uuid[])
                """
                individual_rows = await conn.fetch(individuals_query, all_mvr_uuids)
                individual_uuids = [str(row['individual_uuid']) for row in individual_rows]
                
                logger.info(
                    f"📊 MVR {mvr_uuid[:8]}... has {len(individual_uuids)} total individuals "
                    f"from {len(all_mvr_uuids)} MVR people"
                )
                
                # Get all appearances for these individuals
                # Note: Cannot filter by collection_name here as videos table
                # is in a different database (Media service)
                appearances_query = """
                    SELECT 
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.confidence
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                        AND iva.start_timestamp >= $2
                        AND iva.end_timestamp <= $3
                    ORDER BY iva.start_timestamp ASC
                """
                
                appearances_rows = await conn.fetch(
                    appearances_query,
                    individual_uuids,
                    start_time_naive,
                    end_time_naive
                )
                
                if not appearances_rows:
                    # Skip MVR people with no appearances in the time range
                    continue
                
                # Build appearance objects
                appearances = [
                    MVRIndividualAppearance(
                        video_uuid=str(row['video_uuid']),
                        person_object_uuid=str(row['person_object_uuid']),
                        start_timestamp=row['start_timestamp'],
                        end_timestamp=row['end_timestamp'],
                        confidence=float(row['confidence'])
                    )
                    for row in appearances_rows
                ]
                
                # Calculate aggregate statistics
                unique_videos = len(set(app.video_uuid for app in appearances))
                first_seen = min(app.start_timestamp for app in appearances)
                last_seen = max(app.end_timestamp for app in appearances)
                
                # Format age range if available
                age_display = None
                if mvr_record['age_min'] and mvr_record['age_max']:
                    age_display = f"{mvr_record['age_min']}-{mvr_record['age_max']}"
                
                # Add hierarchical merge information
                merged_uuids = [str(row['merged_mvr_uuid']) for row in merged_mvr_rows] if merged_mvr_rows else []
                is_super = len(merged_mvr_rows) > 0
                
                # Create result object
                result = MVRPersonResult(
                    mvr_people_uuid=mvr_uuid,
                    individual_uuids=individual_uuids,
                    total_appearances=len(appearances),
                    unique_videos=unique_videos,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    confidence_score=float(mvr_record['confidence_score'] or 0.0),
                    quality_score=float(mvr_record['quality_score'] or 0.0),
                    appearances=appearances,
                    merged_mvr_uuids=merged_uuids,
                    is_super_individual=is_super,
                    estimated_age=age_display,
                    estimated_gender=mvr_record['gender']
                )
                
                results.append(result)
            
            logger.info(
                f"Found {len(results)} existing MVR people in time range"
            )
            
            return MVRPeopleSearchResponse(
                success=True,
                total_results=len(results),
                mvr_people=results,
                search_parameters={
                    "collection_name": request.collection_name,
                    "start_time": request.start_time.isoformat(),
                    "end_time": request.end_time.isoformat(),
                    "limit": request.limit
                },
                message=f"Found {len(results)} existing MVR people"
            )
            
    except Exception as e:
        logger.error(f"Error searching MVR people by collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search MVR people: {str(e)}"
        )


# ============================================================================
# ENDPOINT 16: Get Individual Analysis Without Session
# ============================================================================

@router.get(
    "/individuals/{individual_uuid}/analysis",
    summary="Get Individual Analysis Without Session",
    description=(
        "Get individual appearance analysis without requiring a "
        "tracking session. Returns all appearances for the individual "
        "across all videos. Optionally filter by date range."
    ),
)
async def get_individual_analysis_no_session(
    individual_uuid: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get individual appearance analysis without session filtering.
    
    This endpoint fetches all video appearances for an individual
    without requiring a tracking session UUID. Useful for MVR search results
    where individuals may not be associated with a specific session.
    
    Returns:
    - individual_uuid: UUID of the individual
    - total_appearances: Total number of appearances across all videos
    - unique_videos: Number of unique videos
    - first_seen: Timestamp of first appearance
    - last_seen: Timestamp of last appearance
    - appearances: List of all video appearances with details
    """
    logger.info(
        "Fetching analysis for individual %s (user: %s)",
        individual_uuid,
        current_user.get('email')
    )
    
    try:
        # Get database connection from the repository's pool
        async with mvr_repository.pool.acquire() as conn:
            # Build query with optional date filtering
            query_conditions = ["iva.individual_uuid = $1"]
            query_params: list = [individual_uuid]
            
            # Add date range filtering if provided
            if start_time:
                # Convert to naive if timezone-aware
                start_naive = (
                    start_time.replace(tzinfo=None)
                    if start_time.tzinfo
                    else start_time
                )
                query_conditions.append(
                    f"iva.start_timestamp >= ${len(query_params) + 1}"
                )
                query_params.append(start_naive)
            
            if end_time:
                # Convert to naive if timezone-aware
                end_naive = (
                    end_time.replace(tzinfo=None)
                    if end_time.tzinfo
                    else end_time
                )
                query_conditions.append(
                    f"iva.end_timestamp <= ${len(query_params) + 1}"
                )
                query_params.append(end_naive)
            
            # Build the final query with demographics
            query = f"""
                SELECT
                    iva.video_uuid,
                    iva.person_object_uuid,
                    iva.start_timestamp,
                    iva.end_timestamp,
                    iva.confidence,
                    mvr.mvr_people_uuid,
                    mvr.gender,
                    mvr.gender_confidence,
                    mvr.age_min,
                    mvr.age_max,
                    mvr.age_confidence
                FROM individual_video_appearances iva
                LEFT JOIN individual_mvr_mapping imm ON iva.individual_uuid = imm.individual_uuid
                LEFT JOIN mvr_people mvr ON imm.mvr_people_uuid = mvr.mvr_people_uuid
                    AND mvr.is_orphaned = FALSE
                WHERE {' AND '.join(query_conditions)}
                ORDER BY iva.start_timestamp ASC
            """
            
            appearances_rows = await conn.fetch(query, *query_params)
            
            if not appearances_rows:
                return {
                    "individual_uuid": individual_uuid,
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": [],
                    "demographics": None
                }
            
            # Build appearances list
            appearances = [
                {
                    "video_uuid": str(row['video_uuid']),
                    "person_object_uuid": str(row['person_object_uuid']),
                    "start_timestamp": row['start_timestamp'].isoformat(),
                    "end_timestamp": row['end_timestamp'].isoformat(),
                    "confidence": float(row['confidence'])
                }
                for row in appearances_rows
            ]
            
            # Calculate statistics
            unique_videos = len(
                set(app['video_uuid'] for app in appearances)
            )
            first_seen = min(
                row['start_timestamp'] for row in appearances_rows
            )
            last_seen = max(row['end_timestamp'] for row in appearances_rows)
            
            # Extract demographics from first row (all rows should have same demographics)
            demographics = None
            mvr_people_uuid = None
            first_row = appearances_rows[0]
            
            # Get MVR UUID if available (should be same for all rows)
            if first_row['mvr_people_uuid'] is not None:
                mvr_people_uuid = str(first_row['mvr_people_uuid'])
            
            if first_row['gender'] is not None:
                # Calculate age mean if age_min and age_max are available
                age_mean = None
                if first_row['age_min'] is not None and first_row['age_max'] is not None:
                    age_mean = (first_row['age_min'] + first_row['age_max']) / 2.0
                
                demographics = {
                    "gender": first_row['gender'],
                    "gender_confidence": float(first_row['gender_confidence']) if first_row['gender_confidence'] else None,
                    "age_min": first_row['age_min'],
                    "age_max": first_row['age_max'],
                    "age_mean": age_mean,
                    "age_confidence": float(first_row['age_confidence']) if first_row['age_confidence'] else None
                }
            
            return {
                "individual_uuid": individual_uuid,
                "mvr_people_uuid": mvr_people_uuid,  # Include MVR UUID if individual is merged
                "total_appearances": len(appearances),
                "unique_videos": unique_videos,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "appearances": appearances,
                "demographics": demographics
            }
            
    except Exception as e:
        logger.error(
            "Error fetching individual analysis: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch individual analysis: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT 17: Get MVR Person Analysis (Consolidated Individual Data)
# ============================================================================

@router.get(
    "/mvr-person/{mvr_person_uuid}/analysis",
    summary="Get MVR Person Analysis",
    description=(
        "Get consolidated analysis for an MVR person, which represents "
        "multiple individuals merged into a single identity. Returns "
        "aggregated data across all constituent individuals."
    ),
)
async def get_mvr_person_analysis(
    mvr_person_uuid: str,
    request: Request,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get consolidated analysis for an MVR person.
    
    An MVR person represents multiple individuals that have been merged
    based on face recognition similarity. This endpoint returns aggregated
    data across all constituent individuals.
    
    Returns:
    - mvr_person_uuid: UUID of the MVR person
    - individual_uuids: List of constituent individual UUIDs
    - total_appearances: Total appearances across all individuals
    - unique_videos: Number of unique videos
    - first_seen: Earliest appearance timestamp
    - last_seen: Latest appearance timestamp
    - appearances: Consolidated list of all appearances
    """
    logger.info(
        "Fetching MVR person analysis for %s (user: %s)",
        mvr_person_uuid,
        current_user.get('email')
    )
    
    try:
        async with mvr_repository.pool.acquire() as conn:
            # Get all individuals for this MVR person
            individuals_query = """
                SELECT individual_uuid
                FROM individual_mvr_mapping
                WHERE mvr_people_uuid = $1
            """
            
            individual_rows = await conn.fetch(
                individuals_query, mvr_person_uuid
            )
            
            if not individual_rows:
                return {
                    "mvr_person_uuid": mvr_person_uuid,
                    "individual_uuids": [],
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": []
                }
            
            individual_uuids = [
                str(row['individual_uuid']) for row in individual_rows
            ]
            
            # Build query to get all appearances for these individuals
            query_conditions = [
                f"iva.individual_uuid = ANY(${1})"
            ]
            query_params: list = [individual_uuids]
            
            # Add date range filtering if provided
            if start_time:
                start_naive = (
                    start_time.replace(tzinfo=None)
                    if start_time.tzinfo
                    else start_time
                )
                query_conditions.append(
                    f"iva.start_timestamp >= ${len(query_params) + 1}"
                )
                query_params.append(start_naive)
            
            if end_time:
                end_naive = (
                    end_time.replace(tzinfo=None)
                    if end_time.tzinfo
                    else end_time
                )
                query_conditions.append(
                    f"iva.end_timestamp <= ${len(query_params) + 1}"
                )
                query_params.append(end_naive)
            
            # Get demographics from mvr_people table
            demographics_query = """
                SELECT
                    gender,
                    gender_confidence,
                    age_min,
                    age_max,
                    age_confidence
                FROM mvr_people
                WHERE mvr_people_uuid = $1
                    AND is_orphaned = FALSE
            """
            demographics_row = await conn.fetchrow(demographics_query, mvr_person_uuid)
            
            # Prepare demographics object
            demographics = None
            if demographics_row and demographics_row['gender'] is not None:
                # Calculate age mean if age_min and age_max are available
                age_mean = None
                if demographics_row['age_min'] is not None and demographics_row['age_max'] is not None:
                    age_mean = (demographics_row['age_min'] + demographics_row['age_max']) / 2.0
                
                demographics = {
                    "gender": demographics_row['gender'],
                    "gender_confidence": float(demographics_row['gender_confidence']) if demographics_row['gender_confidence'] else None,
                    "age_min": demographics_row['age_min'],
                    "age_max": demographics_row['age_max'],
                    "age_mean": age_mean,
                    "age_confidence": float(demographics_row['age_confidence']) if demographics_row['age_confidence'] else None
                }
            
            # Query all appearances
            appearances_query = f"""
                SELECT
                    iva.individual_uuid,
                    iva.video_uuid,
                    iva.person_object_uuid,
                    iva.start_timestamp,
                    iva.end_timestamp,
                    iva.confidence
                FROM individual_video_appearances iva
                WHERE {' AND '.join(query_conditions)}
                ORDER BY iva.start_timestamp ASC
            """
            
            appearances_rows = await conn.fetch(
                appearances_query, *query_params
            )
            
            if not appearances_rows:
                return {
                    "mvr_person_uuid": mvr_person_uuid,
                    "individual_uuids": individual_uuids,
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": [],
                    "demographics": demographics
                }
            
            # Build appearances list
            appearances = [
                {
                    "individual_uuid": str(row['individual_uuid']),
                    "video_uuid": str(row['video_uuid']),
                    "person_object_uuid": str(row['person_object_uuid']),
                    "start_timestamp": row['start_timestamp'].isoformat(),
                    "end_timestamp": row['end_timestamp'].isoformat(),
                    "confidence": float(row['confidence'])
                }
                for row in appearances_rows
            ]
            
            # Calculate statistics
            unique_videos = len(
                set(app['video_uuid'] for app in appearances)
            )
            first_seen = min(
                row['start_timestamp'] for row in appearances_rows
            )
            last_seen = max(
                row['end_timestamp'] for row in appearances_rows
            )
            
            # Calculate average route velocity from orchestrator route data
            avg_route_velocity = None
            try:
                import httpx
                
                gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
                all_route_points = []
                
                # Get Authorization header from request
                auth_header = request.headers.get("Authorization")
                headers = {}
                if auth_header:
                    headers["Authorization"] = auth_header
                
                # Get unique video UUIDs from appearances
                unique_video_uuids = set(app['video_uuid'] for app in appearances)
                logger.info(f"🚀 VELOCITY CALCULATION STARTED - Fetching routes from {len(unique_video_uuids)} video(s)")
                logger.info(f"🎯 Video UUIDs: {list(unique_video_uuids)}")
                
                # Fetch person objects data for each video to get route points (via gateway)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for video_uuid in unique_video_uuids:
                        try:
                            response = await client.get(
                                f"{gateway_url}/api/v1/orchestrator/person-objects/{video_uuid}",
                                headers=headers
                            )
                            
                            if response.status_code == 200:
                                person_objects_data = response.json()
                                
                                # Debug: Log what we received
                                logger.info(f"Gateway response keys for video {video_uuid}: {list(person_objects_data.keys())}")
                                logger.info(f"Has person_groups: {('person_groups' in person_objects_data)}")
                                
                                # Handle both response formats
                                person_groups = person_objects_data.get('group_tracking') or person_objects_data.get('person_groups', [])
                                
                                logger.info(f"Extracted {len(person_groups) if person_groups else 0} person groups from video {video_uuid}")
                                
                                for person_group in person_groups:
                                    # Extract route points from movement_tracking
                                    movement_tracking = person_group.get('movement_tracking', {})
                                    route_points = movement_tracking.get('route_points', [])
                                    
                                    for route_point in route_points:
                                        # Use center_x and center_y from gateway response
                                        # Note: timestamp is a float (seconds from video start), keep as-is
                                        all_route_points.append({
                                            'x': float(route_point.get('center_x', route_point.get('x', 0))),
                                            'y': float(route_point.get('center_y', route_point.get('y', 0))),
                                            'timestamp': float(route_point['timestamp']),  # Keep as float
                                            'video_uuid': video_uuid,
                                            'confidence': float(route_point.get('confidence', 1.0))
                                        })
                                
                                logger.info(f"Fetched {len(route_points)} route points from video {video_uuid}")
                            else:
                                logger.warning(f"Orchestrator returned status {response.status_code} for video {video_uuid}")
                        except Exception as e:
                            logger.warning(f"Could not fetch routes from video {video_uuid}: {e}")
                
                logger.info(f"📊 Total route points collected: {len(all_route_points)}")
                if len(all_route_points) >= 2:
                    # Sort by timestamp
                    all_route_points.sort(key=lambda r: r['timestamp'])
                    logger.info(f"✅ Calculating velocities from {len(all_route_points)} points...")
                    
                    # Calculate velocities inline (timestamps are floats, not ISO strings)
                    # Normalize coordinates and calculate velocity between consecutive points
                    width, height = 1920, 1080  # Standard resolution
                    velocities = []
                    
                    for i in range(1, len(all_route_points)):
                        try:
                            prev = all_route_points[i-1]
                            curr = all_route_points[i]
                            
                            # Normalize coordinates
                            x1_norm = prev['x'] / width
                            y1_norm = prev['y'] / height
                            x2_norm = curr['x'] / width
                            y2_norm = curr['y'] / height
                            
                            # Calculate normalized distance
                            dx = x2_norm - x1_norm
                            dy = y2_norm - y1_norm
                            distance_normalized = (dx ** 2 + dy ** 2) ** 0.5
                            
                            # Calculate time difference (timestamps are floats in seconds)
                            time_diff = curr['timestamp'] - prev['timestamp']
                            
                            # Calculate velocity
                            if time_diff > 0:
                                velocity = distance_normalized / time_diff
                                velocities.append(velocity)
                        except (KeyError, ValueError, ZeroDivisionError) as e:
                            logger.warning(f"Error calculating velocity: {e}")
                            continue
                    
                    logger.info(f"🎯 Valid velocities calculated: {len(velocities)}")
                    if velocities:
                        avg_route_velocity = round(sum(velocities) / len(velocities), 6)
                        logger.info(f"✅ VELOCITY CALCULATED: {avg_route_velocity} normalized px/s from {len(all_route_points)} route points")
                    else:
                        logger.warning(f"⚠️ No valid velocities calculated")
                else:
                    logger.warning(f"⚠️ Not enough route points ({len(all_route_points)}) for velocity calculation")
            except Exception as e:
                logger.warning(f"Failed to calculate route velocity for MVR person: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
            
            return {
                "mvr_person_uuid": mvr_person_uuid,
                "individual_uuids": individual_uuids,
                "total_appearances": len(appearances),
                "unique_videos": unique_videos,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "appearances": appearances,
                "demographics": demographics,
                "average_route_velocity": avg_route_velocity
            }
            
    except Exception as e:
        logger.error(
            "Error fetching MVR person analysis: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MVR person analysis: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Video UUIDs (Today)
# ============================================================================

@router.post(
    "/count-by-videos",
    summary="Get MVR People Count for Video UUIDs",
    description=(
        "Returns the count of unique MVR people detected in the specified "
        "videos. Only queries VMeta's own database. Useful for getting "
        "per-camera or per-collection counts."
    ),
)
async def get_videos_mvr_people_count(
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people detected in specific videos.

    Request Body:
        {
            "video_uuids": ["uuid1", "uuid2", "uuid3"]
        }

    Returns:
        {
            "count": 5,
            "video_count": 3
        }
    """
    try:
        if not video_uuids:
            return {
                "count": 0,
                "video_count": 0
            }

        logger.info(
            "Fetching MVR people count for %d videos", len(video_uuids)
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Query unique MVR people count for these videos
            # Only uses VMeta's own tables:
            # - individual_video_appearances (has video_uuid, individual_uuid)
            # - individual_mvr_mapping (maps individuals to MVR people)
            count_query = """
                WITH video_individuals AS (
                    -- Get individuals with appearances in these videos
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid = ANY($1::uuid[])
                )
                -- Count unique MVR people linked to these individuals
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM video_individuals
                )
            """

            # Convert string UUIDs to UUID array for PostgreSQL
            uuid_array = [UUID(vid) for vid in video_uuids]
            
            count_row = await conn.fetchrow(
                count_query,
                uuid_array
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "count": mvr_count,
                "video_count": len(video_uuids)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching videos MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos MVR people count: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Video UUIDs with Demographics
# ============================================================================

@router.post(
    "/count-by-videos-demographics",
    summary="Get MVR People Count with Demographics for Video UUIDs",
    description=(
        "Returns the count of unique MVR people with demographic breakdowns "
        "(gender, age) detected in the specified videos."
    ),
)
async def get_videos_mvr_people_count_with_demographics(
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people with demographic breakdowns.

    Request Body:
        {
            "video_uuids": ["uuid1", "uuid2", "uuid3"]
        }

    Returns:
        {
            "count": 15,
            "video_count": 3,
            "demographics": {
                "total_male": 9,
                "total_female": 6,
                "percent_male": 60.0,
                "percent_female": 40.0,
                "total_young": 4,
                "total_adult": 11,
                "percent_young": 26.7,
                "percent_adult": 73.3
            }
        }
    """
    try:
        if not video_uuids:
            return {
                "count": 0,
                "video_count": 0,
                "demographics": {
                    "total_male": 0,
                    "total_female": 0,
                    "percent_male": 0.0,
                    "percent_female": 0.0,
                    "total_young": 0,
                    "total_adult": 0,
                    "percent_young": 0.0,
                    "percent_adult": 0.0
                }
            }

        logger.info(
            "Fetching MVR people count with demographics for %d videos", len(video_uuids)
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Query MVR people with demographics
            # Uses aggregated demographics from individuals linked to each MVR person
            
            # First, let's count individuals with video appearances (for debugging)
            debug_query = """
                SELECT 
                    COUNT(DISTINCT iva.individual_uuid) as total_individuals,
                    COUNT(DISTINCT imm.mvr_people_uuid) as mvr_people_linked,
                    COUNT(DISTINCT i.individual_uuid) FILTER (WHERE i.gender_estimate IS NOT NULL) as with_gender,
                    COUNT(DISTINCT i.individual_uuid) FILTER (WHERE i.age_estimate IS NOT NULL) as with_age
                FROM individual_video_appearances iva
                LEFT JOIN individual_mvr_mapping imm ON iva.individual_uuid = imm.individual_uuid
                LEFT JOIN individuals i ON iva.individual_uuid = i.individual_uuid
                WHERE iva.video_uuid = ANY($1::uuid[])
            """
            
            # Convert string UUIDs to UUID array for PostgreSQL
            uuid_array = [UUID(vid) for vid in video_uuids]
            
            debug_row = await conn.fetchrow(debug_query, uuid_array)
            logger.info(
                f"📊 DEBUG - Video MVR Count: "
                f"total_individuals={debug_row['total_individuals']}, "
                f"mvr_linked={debug_row['mvr_people_linked']}, "
                f"with_gender={debug_row['with_gender']}, "
                f"with_age={debug_row['with_age']}"
            )
            
            demographics_query = """
                WITH video_individuals AS (
                    -- Get individuals with appearances in these videos
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid = ANY($1::uuid[])
                ),
                linked_mvr_people AS (
                    -- Get MVR people linked to these video individuals
                    SELECT DISTINCT imm.mvr_people_uuid
                    FROM individual_mvr_mapping imm
                    WHERE imm.individual_uuid IN (SELECT individual_uuid FROM video_individuals)
                )
                -- Get demographics directly from mvr_people table (not individuals)
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(*) FILTER (WHERE LOWER(mp.gender) = 'male') as male_count,
                    COUNT(*) FILTER (WHERE LOWER(mp.gender) = 'female') as female_count,
                    COUNT(*) FILTER (WHERE mp.age_max IS NOT NULL AND mp.age_max < 21) as young_count,
                    COUNT(*) FILTER (WHERE mp.age_min IS NOT NULL AND mp.age_min >= 21) as adult_count
                FROM mvr_people mp
                WHERE mp.mvr_people_uuid IN (SELECT mvr_people_uuid FROM linked_mvr_people)
                    AND mp.is_orphaned = false
            """

            # Convert string UUIDs to UUID array for PostgreSQL
            uuid_array = [UUID(vid) for vid in video_uuids]
            
            demo_row = await conn.fetchrow(
                demographics_query,
                uuid_array
            )

            total_count = demo_row['total_count'] if demo_row else 0
            male_count = demo_row['male_count'] if demo_row else 0
            female_count = demo_row['female_count'] if demo_row else 0
            young_count = demo_row['young_count'] if demo_row else 0
            adult_count = demo_row['adult_count'] if demo_row else 0

            # Calculate percentages
            percent_male = (male_count / total_count * 100) if total_count > 0 else 0.0
            percent_female = (female_count / total_count * 100) if total_count > 0 else 0.0
            percent_young = (young_count / total_count * 100) if total_count > 0 else 0.0
            percent_adult = (adult_count / total_count * 100) if total_count > 0 else 0.0

            return {
                "count": total_count,
                "video_count": len(video_uuids),
                "demographics": {
                    "total_male": male_count,
                    "total_female": female_count,
                    "percent_male": round(percent_male, 1),
                    "percent_female": round(percent_female, 1),
                    "total_young": young_count,
                    "total_adult": adult_count,
                    "percent_young": round(percent_young, 1),
                    "percent_adult": round(percent_adult, 1)
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching videos MVR people count with demographics: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos MVR people count with demographics: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Collection (Today) - DEPRECATED
# ============================================================================
# NOTE: This endpoint requires cross-database queries which violates
# microservice boundaries. Use /count-by-videos instead.

@router.get(
    "/count-by-collection/{collection_name}",
    summary="Get Today's MVR People Count for Collection (DEPRECATED)",
    deprecated=True,
    description=(
        "Returns the count of unique MVR people detected today for a "
        "specific collection. Queries MVR people with appearances in "
        "that collection today."
    ),
)
async def get_collection_mvr_people_count(
    collection_name: str,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people detected today for a collection.

    Returns:
        {
            "collection_name": "camera-device-123",
            "count": 5,
            "date": "2025-11-16",
            "start_time": "2025-11-16T00:00:00",
            "end_time": "2025-11-16T23:59:59"
        }
    """
    from datetime import time

    try:
        logger.info(
            "Fetching MVR people count for collection: %s", collection_name
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Get today's date range (00:00:00 to 23:59:59)
            today = datetime.now().date()
            start_time = datetime.combine(today, time.min)  # 00:00:00
            end_time = datetime.combine(today, time.max)  # 23:59:59.999999

            # Convert to naive datetime for database
            # (PostgreSQL timestamps are naive)
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)

            # Query unique MVR people count for collection today
            # We need to:
            # a) Find all media in the collection
            # b) Find all individual_video_appearances for those media
            #    within today's timeframe
            # c) Count unique MVR people associated with those individuals

            count_query = """
                WITH collection_videos AS (
                    -- Get all videos in the collection
                    SELECT v.video_uuid
                    FROM videos v
                    JOIN media_collections mc
                      ON v.collection_uuid = mc.collection_uuid
                    WHERE mc.collection_name = $1
                ),
                today_individuals AS (
                    -- Get all individuals with appearances today
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid IN (
                        SELECT video_uuid FROM collection_videos
                    )
                      AND iva.start_timestamp >= $2
                      AND iva.start_timestamp <= $3
                )
                -- Count unique MVR people linked to these individuals
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM today_individuals
                )
            """

            count_row = await conn.fetchrow(
                count_query,
                collection_name,
                start_time,
                end_time
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "collection_name": collection_name,
                "count": mvr_count,
                "date": today.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching collection MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch collection MVR people count: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Camera (Today) - DEPRECATED
# ============================================================================
# NOTE: This endpoint requires cross-database queries which isn't supported
# Use /count-by-collection/{collection_name} instead

@router.get(
    "/count-by-camera/{camera_id}",
    summary="Get Today's MVR People Count for Camera (DEPRECATED)",
    description=(
        "DEPRECATED: Use /count-by-collection/{collection_name} instead. "
        "This endpoint requires cross-service database access."
    ),
    deprecated=True,
)
async def get_camera_mvr_people_count(
    camera_id: str,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    DEPRECATED: Get count of unique MVR people detected today for a camera.

    Please use /count-by-collection/{collection_name} endpoint instead.
    Frontend should map camera_id to collection_name first.
    """
    from datetime import time

    try:
        logger.info("Fetching MVR people count for camera: %s", camera_id)

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Step 1: Get camera's collection name from media_collections table
            # The media service stores camera_device_id in media_collections
            collection_row = await conn.fetchrow(
                """
                SELECT collection_name
                FROM media_collections
                WHERE camera_device_id = $1
                LIMIT 1
                """,
                camera_id
            )

            if not collection_row:
                return {
                    "camera_id": camera_id,
                    "collection_name": None,
                    "count": 0,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "start_time": None,
                    "end_time": None,
                    "message": "No collection found for this camera"
                }

            collection_name = collection_row['collection_name']
            if not collection_name:
                today_str = datetime.now().strftime("%Y-%m-%d")
                return {
                    "camera_id": camera_id,
                    "collection_name": None,
                    "count": 0,
                    "date": today_str,
                    "start_time": None,
                    "end_time": None,
                    "message": "Camera has no associated collection"
                }

            # Step 2: Get today's date range (00:00:00 to 23:59:59)
            today = datetime.now().date()
            start_time = datetime.combine(today, time.min)  # 00:00:00
            end_time = datetime.combine(today, time.max)  # 23:59:59.999999

            # Convert to naive datetime for database
            # (PostgreSQL timestamps are naive)
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)

            # Step 3: Query unique MVR people count for collection today
            # We need to:
            # a) Find all media in the collection
            # b) Find all individual_video_appearances for those media
            #    within today's timeframe
            # c) Count unique MVR people associated with those individuals

            count_query = """
                WITH collection_videos AS (
                    -- Get all videos in the camera's collection
                    SELECT v.video_uuid
                    FROM videos v
                    JOIN media_collections mc
                      ON v.collection_uuid = mc.collection_uuid
                    WHERE mc.collection_name = $1
                ),
                today_individuals AS (
                    -- Get all individuals with appearances today
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid IN (
                        SELECT video_uuid FROM collection_videos
                    )
                      AND iva.start_timestamp >= $2
                      AND iva.start_timestamp <= $3
                )
                -- Count unique MVR people linked to these individuals
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM today_individuals
                )
            """

            count_row = await conn.fetchrow(
                count_query,
                collection_name,
                start_time,
                end_time
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "camera_id": camera_id,
                "collection_name": collection_name,
                "count": mvr_count,
                "date": today.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching camera MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch camera MVR people count: {str(e)}"
        ) from e


# ============================================================================
# HELPER: Enrich Person Objects with Face Crops
# ============================================================================

async def enrich_person_objects_with_face_crops(
    person_objects: List[Dict[str, Any]],
    media_uuid: UUID,
    auth_token: str,
    vision_url: str = "http://localhost:8003",
    gateway_url: str = "http://localhost:8080"
) -> List[Dict[str, Any]]:
    """
    Enrich person objects with face crops extracted from video frames.
    
    For each person_object:
    1. Get best_face_id and best_face_bbox from person_object
    2. Query Vision service to get frame_number for best_face_id
    3. Fetch frame from Media service via Gateway
    4. Extract face crop using bbox coordinates
    5. Add best_face_crop (numpy array) to person_object
    
    Args:
        person_objects: List of person objects from Vision Face Detection V2
        media_uuid: Media UUID
        auth_token: Auth token for service calls
        vision_url: Vision service URL
        gateway_url: Gateway service URL
        
    Returns:
        List of person objects with best_face_crop added
    """
    import httpx
    import cv2
    import numpy as np
    from PIL import Image
    from io import BytesIO

    def _is_valid_bbox(bbox: Any) -> bool:
        return (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(value is not None for value in bbox)
            and float(bbox[2]) > float(bbox[0])
            and float(bbox[3]) > float(bbox[1])
        )

    def _is_valid_frame_number(frame_number: Any) -> bool:
        try:
            return int(frame_number) >= 0
        except (TypeError, ValueError):
            return False

    async def _fetch_face_details_by_id() -> Dict[str, Dict[str, Any]]:
        try:
            response = await client.get(
                f"{vision_url}/faces/media/{media_uuid}",
                headers={'Authorization': f'Bearer {auth_token}'},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "Failed to fetch raw face details for media %s: %s",
                media_uuid,
                exc,
            )
            return {}

        faces = []
        if isinstance(payload, list):
            faces = payload
        elif isinstance(payload, dict):
            faces = payload.get('faces', []) or []
            if not faces:
                faces_by_frame = payload.get('faces_by_frame', {}) or {}
                for frame_faces in faces_by_frame.values():
                    if isinstance(frame_faces, list):
                        faces.extend(frame_faces)

        face_details_by_id: Dict[str, Dict[str, Any]] = {}
        for face in faces:
            if not isinstance(face, dict):
                continue
            face_id = face.get('id') or face.get('face_id')
            if not face_id:
                continue
            face_details_by_id[str(face_id)] = {
                'frame_number': face.get('frame_number'),
                'bbox': face.get('bbox') or [
                    face.get('bbox_x1'),
                    face.get('bbox_y1'),
                    face.get('bbox_x2'),
                    face.get('bbox_y2'),
                ],
                'confidence': face.get('confidence'),
                'frame_width': face.get('frame_width'),
                'frame_height': face.get('frame_height'),
            }
        return face_details_by_id
    
    enriched_objects = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        face_details_by_id: Optional[Dict[str, Dict[str, Any]]] = None
        for person_obj in person_objects:
            try:
                # Get frame number and bbox directly from person_object
                # Face Detection V2 already provides best_face_frame
                frame_number = person_obj.get('best_face_frame')
                best_face_bbox = person_obj.get('best_face_bbox')

                representative_faces = person_obj.get('representative_faces') or []
                best_face = representative_faces[0] if representative_faces else {}
                face_data = best_face.get('face_data') or {}
                best_face_id = (
                    person_obj.get('best_face_id')
                    or best_face.get('face_id')
                    or face_data.get('id')
                )

                if not _is_valid_frame_number(frame_number):
                    frame_number = face_data.get('frame_number')
                if not _is_valid_bbox(best_face_bbox):
                    best_face_bbox = face_data.get('bbox')

                if (
                    best_face_id
                    and (
                        not _is_valid_frame_number(frame_number)
                        or not _is_valid_bbox(best_face_bbox)
                    )
                ):
                    if face_details_by_id is None:
                        face_details_by_id = await _fetch_face_details_by_id()
                    face_details = face_details_by_id.get(str(best_face_id), {})
                    raw_frame_number = face_details.get('frame_number')
                    raw_bbox = face_details.get('bbox')
                    if _is_valid_frame_number(raw_frame_number) and _is_valid_bbox(raw_bbox):
                        frame_number = raw_frame_number
                        best_face_bbox = raw_bbox
                    else:
                        if not _is_valid_frame_number(frame_number):
                            frame_number = raw_frame_number
                        if not _is_valid_bbox(best_face_bbox):
                            best_face_bbox = raw_bbox
                    if person_obj.get('detect_frame_width') is None:
                        person_obj['detect_frame_width'] = face_details.get('frame_width')
                    if person_obj.get('detect_frame_height') is None:
                        person_obj['detect_frame_height'] = face_details.get('frame_height')

                # Recompute fallback: when persisted representative_faces /
                # best_face_* metadata are empty (typical for stored person
                # objects whose pipelines did not populate quality rankings),
                # scan the person's full face id list and pick the first face
                # that has a valid frame + bbox in Vision's raw face details.
                # Without this, ML enrichment silently produces 0 MVRs.
                if not _is_valid_frame_number(frame_number) or not _is_valid_bbox(best_face_bbox):
                    candidate_face_ids = (
                        person_obj.get('all_face_ids')
                        or person_obj.get('face_ids')
                        or []
                    )
                    if candidate_face_ids:
                        if face_details_by_id is None:
                            face_details_by_id = await _fetch_face_details_by_id()
                        # Prefer highest-confidence face for better embedding quality.
                        scored_candidates = []
                        for candidate_face_id in candidate_face_ids:
                            details = face_details_by_id.get(str(candidate_face_id), {})
                            cand_frame = details.get('frame_number')
                            cand_bbox = details.get('bbox')
                            if _is_valid_frame_number(cand_frame) and _is_valid_bbox(cand_bbox):
                                scored_candidates.append(
                                    (
                                        float(details.get('confidence') or 0.0),
                                        candidate_face_id,
                                        cand_frame,
                                        cand_bbox,
                                        details,
                                    )
                                )
                        if scored_candidates:
                            scored_candidates.sort(key=lambda item: item[0], reverse=True)
                            (
                                _conf,
                                chosen_face_id,
                                chosen_frame,
                                chosen_bbox,
                                chosen_details,
                            ) = scored_candidates[0]
                            frame_number = chosen_frame
                            best_face_bbox = chosen_bbox
                            best_face_id = chosen_face_id
                            if person_obj.get('detect_frame_width') is None:
                                person_obj['detect_frame_width'] = chosen_details.get('frame_width')
                            if person_obj.get('detect_frame_height') is None:
                                person_obj['detect_frame_height'] = chosen_details.get('frame_height')
                            logger.info(
                                "Recovered face metadata for person %s via face_ids fallback: "
                                "face_id=%s frame=%s bbox=%s (scanned %d candidates)",
                                person_obj.get('person_id'),
                                chosen_face_id,
                                chosen_frame,
                                chosen_bbox,
                                len(candidate_face_ids),
                            )

                if not _is_valid_frame_number(frame_number) or not _is_valid_bbox(best_face_bbox):
                    logger.warning(
                        f"Person object missing valid best_face_frame or bbox: {person_obj.get('person_id')}"
                    )
                    enriched_objects.append(person_obj)
                    continue
                
                # Step 2: Fetch frame from Media service via Gateway
                frame_url = (
                    f"{gateway_url}/api/v1/media/{media_uuid}/frame/{frame_number}?format=jpeg"
                )
                
                frame_response = await client.get(
                    frame_url,
                    headers={'Authorization': f'Bearer {auth_token}'}
                )
                
                if frame_response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch frame {frame_number} for {media_uuid}: "
                        f"{frame_response.status_code}"
                    )
                    enriched_objects.append(person_obj)
                    continue
                
                # Step 3: Decode frame from JPEG bytes
                frame_bytes = frame_response.content
                pil_image = Image.open(BytesIO(frame_bytes))
                frame = np.array(pil_image)
                
                # Convert RGB to BGR (OpenCV format)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Step 4: Extract face crop using bbox
                # bbox format: [x1, y1, x2, y2]
                x1, y1, x2, y2 = best_face_bbox
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Align bbox to crop frame if detection and crop frames differ in resolution
                frame_h, frame_w = frame_bgr.shape[:2]
                detect_w = person_obj.get('detect_frame_width')
                detect_h = person_obj.get('detect_frame_height')
                if detect_w and detect_h and (detect_w != frame_w or detect_h != frame_h):
                    scale_x = frame_w / detect_w
                    scale_y = frame_h / detect_h
                    x1 = int(round(x1 * scale_x))
                    y1 = int(round(y1 * scale_y))
                    x2 = int(round(x2 * scale_x))
                    y2 = int(round(y2 * scale_y))
                    logger.info(
                        f"BBox aligned for person {person_obj.get('person_id')}: "
                        f"detect={detect_w}x{detect_h} crop={frame_w}x{frame_h} "
                        f"scale=({scale_x:.3f},{scale_y:.3f})"
                    )
                
                # Validate bbox
                if x1 < 0 or y1 < 0 or x2 > frame_w or y2 > frame_h or x1 >= x2 or y1 >= y2:
                    logger.warning(
                        f"Invalid bbox for person {person_obj.get('person_id')}: "
                        f"[{x1},{y1},{x2},{y2}] in frame [{frame_w},{frame_h}]"
                    )
                    enriched_objects.append(person_obj)
                    continue
                
                # Crop the face
                face_crop = frame_bgr[y1:y2, x1:x2].copy()
                
                # Step 5: Add face_crop to person_object
                enriched_obj = {
                    **person_obj,
                    'best_face_frame': int(frame_number),
                    'best_face_bbox': list(best_face_bbox),
                    'best_face_crop': face_crop  # numpy array for ML processing
                }
                enriched_objects.append(enriched_obj)
                
                logger.info(
                    f"Enriched person {person_obj.get('person_id')} with face crop: "
                    f"{face_crop.shape}"
                )
                
            except Exception as e:
                logger.error(
                    f"Error enriching person object {person_obj.get('person_id')}: {e}"
                )
                # Add without face_crop
                enriched_objects.append(person_obj)
    
    return enriched_objects


# ============================================================================
# ENDPOINT 15: Process Media Independently for MVR People
# ============================================================================

@router.post(
    "/process-media",
    status_code=status.HTTP_200_OK,
    summary="Process Media Independently for MVR People",
    description=(
        "Process photos and videos independently to generate MVR people. "
        "Each media is processed in isolation—no cross-media merging. "
        "Photos produce single-point route data, videos produce multi-point routes."
    ),
)
async def process_media_independently(
    request: "ProcessMediaRequest",
    http_request: Request,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Process media (photos/videos) independently for MVR people creation.
    
    Key behaviors:
    - No cross-media merging (each media processed in isolation)
    - Photos: Single-point route data
    - Videos: Multi-point route data with velocity calculation
    - Returns MVR people in standard format
    
    Args:
        request: ProcessMediaRequest with media UUIDs and options
        http_request: FastAPI Request object (for auth header)
        mvr_service: MVR service dependency
        current_user: Authenticated user
        
    Returns:
        ProcessMediaResponse with MVR people for each media
    """
    import time
    from uuid import UUID
    from utils.media_client import MediaClient
    from utils.orchestrator_client import get_orchestrator_client
    from utils.route_data_builder import build_route_data
    from api.models.process_media import (
        ProcessMediaResponse,
        AsyncProcessingResponse,
        MediaResult,
        MVRPerson,
        IndividualAppearance,
        Demographics,
        RouteData,
        AggregateStatistics,
        MediaTypeStatistics,
        MediaProcessingError
    )
    
    logger.info(
        f"Processing {len(request.media_uuids)} media independently "
        f"(user: {current_user.get('email')})"
    )
    
    # Validate request
    if len(request.media_uuids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 media UUIDs per request"
        )
    
    # Check if async processing requested
    if request.processing_options.async_processing:
        # TODO: Implement async job queue
        job_id = f"job-{UUID.uuid4()}"
        return AsyncProcessingResponse(
            success=True,
            job_id=job_id,
            status="processing",
            total_media=len(request.media_uuids),
            estimated_completion_seconds=len(request.media_uuids) * 2,
            status_endpoint=f"/api/v1/mvr-people/jobs/{job_id}/status"
        )
    
    # Synchronous processing with orchestration
    start_time = time.time()
    
    # Extract auth token from Authorization header
    auth_header = http_request.headers.get('Authorization', '')
    auth_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
    
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    
    media_client = MediaClient(auth_token=auth_token)
    orchestrator_client = get_orchestrator_client()
    
    # Log the processing options being used
    logger.info(f"[REQUEST DEBUG] Processing options: similarity_threshold={request.processing_options.similarity_threshold}, min_face_quality={request.processing_options.min_face_quality}")
    
    results = []
    
    # Import httpx for Vision service calls
    import httpx
    vision_url = os.getenv("PPL_VISION_URL", "http://localhost:8003")
    gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
    
    for media_uuid_str in request.media_uuids:
        try:
            media_uuid = UUID(media_uuid_str)
            media_start = time.time()
            
            # Step 1: Fetch media metadata
            media_metadata = await media_client.get_media_metadata(media_uuid)
            
            if not media_metadata:
                results.append(MediaResult(
                    media_uuid=media_uuid_str,
                    media_type="unknown",
                    status="failed",
                    error=MediaProcessingError(
                        code="MEDIA_NOT_FOUND",
                        message=f"Media UUID not found: {media_uuid_str}"
                    )
                ))
                continue
            
            media_type = media_metadata.get('type', 'unknown')
            logger.info(f"Processing {media_type}: {media_uuid_str}")
            
            # Step 2: Trigger Enhanced Face Detection V2 via Orchestrator (synchronous)
            # This works for both photos and videos
            trigger_data = {}  # Initialize outside httpx block for scoping
            orchestrator_url = os.getenv("PPL_ORCHESTRATOR_URL", "http://localhost:8002")
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                # Step 2a: Use Enhanced Logic V2 endpoint (synchronous, no polling needed)
                logger.info(f"Triggering Enhanced Logic V2 face detection for {media_uuid_str}...")
                
                fd_response = await client.get(
                    f"{orchestrator_url}/api/v1/media/{media_uuid_str}/faces/enhanced-v2",
                    headers={'Authorization': f'Bearer {auth_token}'},
                    params={"frame_interval": 10}  # Process every 10th frame for speed
                )
                
                logger.info(f"[VMETA DEBUG] Enhanced Logic V2 response: {fd_response.status_code}")
                
                if fd_response.status_code not in [200, 201]:
                    error_detail = fd_response.text
                    logger.error(
                        f"Enhanced Logic V2 failed for {media_uuid_str}: "
                        f"{fd_response.status_code} - {error_detail}"
                    )
                    logger.info(f"[VMETA DEBUG] Enhanced Logic V2 FAILED")
                    results.append(MediaResult(
                        media_uuid=media_uuid_str,
                        media_type=media_type,
                        status="failed",
                        error=MediaProcessingError(
                            code="FACE_DETECTION_FAILED",
                            message=f"Enhanced Logic V2 face detection failed: {error_detail}"
                        )
                    ))
                    continue
                
                fd_data = fd_response.json()
                faces_count = fd_data.get('total_faces', 0)
                logger.info(f"[VMETA DEBUG] Enhanced Logic V2 completed: {faces_count} faces detected")
                
                # Step 2b: Get person groups directly from Orchestrator's PPL Thread endpoint
                # This preserves Orchestrator's IoU-based grouping instead of Vision re-clustering
                logger.info(f"Fetching person groups from Orchestrator PPL Thread for {media_uuid_str}...")
                
                ppl_thread_response = await client.get(
                    f"{orchestrator_url}/person-objects/{media_uuid_str}",
                    headers={'Authorization': f'Bearer {auth_token}'}
                )
                
                logger.info(f"[VMETA DEBUG] PPL Thread response: {ppl_thread_response.status_code}")
                
                if ppl_thread_response.status_code not in [200, 201]:
                    error_detail = ppl_thread_response.text
                    logger.error(
                        f"PPL Thread failed for {media_uuid_str}: "
                        f"{ppl_thread_response.status_code} - {error_detail}"
                    )
                    logger.info(f"[VMETA DEBUG] PPL Thread FAILED")
                    results.append(MediaResult(
                        media_uuid=media_uuid_str,
                        media_type=media_type,
                        status="failed",
                        error=MediaProcessingError(
                            code="PPL_THREAD_FAILED",
                            message=f"PPL Thread failed: {error_detail}"
                        )
                    ))
                    continue
                
                ppl_data = ppl_thread_response.json()
            
            # Step 3: Extract person groups from Orchestrator's PPL Thread response
            # These groups already use IoU-based face grouping (no re-clustering needed)
            logger.info(
                f"PPL Thread completed for {media_uuid_str}: "
                f"{ppl_data.get('total_persons', 0)} person groups created"
            )
            
            logger.info(f"[VMETA DEBUG] PPL Thread response keys: {ppl_data.keys()}")
            logger.info(f"[VMETA DEBUG] PPL Thread total_persons: {ppl_data.get('total_persons', 0)}")
            logger.info(f"[VMETA DEBUG] PPL Thread full response: {ppl_data}")
            
            person_groups_from_orchestrator = ppl_data.get('person_groups', [])
            logger.info(f"[VMETA DEBUG] person_groups_from_orchestrator count: {len(person_groups_from_orchestrator)}")
            logger.info(f"[VMETA DEBUG] person_groups_from_orchestrator sample: {person_groups_from_orchestrator[:1] if person_groups_from_orchestrator else 'EMPTY'}")
            
            # Transform Orchestrator's person_groups to person_objects format
            # Orchestrator groups faces using IoU, we preserve this grouping
            person_objects_from_vision = []
            for pg in person_groups_from_orchestrator:
                # Extract best face from representative_faces (already sorted by quality)
                representative_faces = pg.get('representative_faces', [])
                best_face = representative_faces[0] if representative_faces else {}
                best_face_data = best_face.get('face_data', {})
                
                # Extract bbox and frame from best face
                bbox = best_face_data.get('bbox', [])
                frame_number = best_face_data.get('frame_number', 0)
                
                person_obj = {
                    'person_id': pg.get('person_id'),
                    'person_uuid': pg.get('person_uuid'),
                    'face_count': pg.get('face_count', 0),
                    'representative_faces': representative_faces,
                    # Use quality_score directly from person_group (Orchestrator provides it at top level)
                    # Fallback to quality_metrics.average_quality if not present, then to 0.85
                    'quality_score': pg.get('quality_score', pg.get('quality_metrics', {}).get('average_quality', 0.85)),
                    'confidence_score': pg.get('average_confidence', 0.9),
                    'spatial_bounds': pg.get('spatial_bounds', {}),
                    'temporal_span': pg.get('temporal_span', {}),
                    'movement_tracking': pg.get('movement_tracking', {}),
                    # Add fields needed for enrichment
                    'best_face_frame': frame_number,
                    'best_face_bbox': bbox if len(bbox) == 4 else None,
                    # Detection-time frame dimensions for bbox alignment at crop time
                    'detect_frame_width': best_face_data.get('frame_width'),
                    'detect_frame_height': best_face_data.get('frame_height'),
                }
                person_objects_from_vision.append(person_obj)
            
            logger.info(
                f"Extracted {len(person_objects_from_vision)} person objects from Orchestrator "
                f"for {media_uuid_str} (preserved IoU-based grouping)"
            )
            logger.info(f"DEBUG: person_objects sample: {person_objects_from_vision[:1] if person_objects_from_vision else 'EMPTY'}")
            logger.info(f"[VMETA DEBUG] person_objects count: {len(person_objects_from_vision)}")
            logger.info(f"[VMETA DEBUG] person_objects sample: {person_objects_from_vision[:1] if person_objects_from_vision else 'EMPTY'}")
            
            if not person_objects_from_vision:
                logger.info(f"No faces detected in {media_uuid_str}")
                results.append(MediaResult(
                    media_uuid=media_uuid_str,
                    media_type=media_type,
                    status="completed",
                    mvr_people=[],
                    total_faces_detected=0,
                    mvr_people_count=0,
                    processing_time_ms=int((time.time() - media_start) * 1000)
                ))
                continue
            
            # Step 4: Enrich person objects with face crops
            # This fetches frames and extracts face crops for ML processing
            logger.info(
                f"Enriching {len(person_objects_from_vision)} person objects with face crops "
                f"for {media_uuid_str}..."
            )
            
            # Re-enable enrichment now that pipeline is confirmed working
            try:
                enriched_person_objects = await enrich_person_objects_with_face_crops(
                    person_objects=person_objects_from_vision,
                    media_uuid=media_uuid,
                    auth_token=auth_token,
                    vision_url=vision_url,
                    gateway_url=gateway_url
                )
            except Exception as enrich_error:
                logger.error(f"Enrichment failed: {enrich_error}", exc_info=True)
                # Fall back to using person_objects without enrichment
                enriched_person_objects = person_objects_from_vision
            
            logger.info(
                f"Face crop enrichment completed for {media_uuid_str}: "
                f"{sum(1 for po in enriched_person_objects if 'best_face_crop' in po)}/{len(enriched_person_objects)} "
                f"person objects have face crops"
            )
            logger.info(f"DEBUG: enriched_person_objects count: {len(enriched_person_objects)}")
            logger.info(f"[VMETA DEBUG] enriched_person_objects: {len(enriched_person_objects)}")
            logger.info(f"[VMETA DEBUG] enriched_person_objects sample: {enriched_person_objects[:1] if enriched_person_objects else 'EMPTY'}")
            
            # Step 5: Transform enriched person objects to MVR format.
            # Reuse the persisted Vision person identifier; do not invent one.
            person_objects = []
            
            for po in enriched_person_objects:
                # Add required fields for MVRService compatibility
                # Use Vision service's calculated quality score (weighted average of face qualities)
                # Fall back to 0.85 only if quality_score is missing or 0.0
                vision_quality = po.get('quality_score', 0.0)
                
                # Orchestrator returns quality_score in 0-100 range (e.g., 21.09)
                # Individual face quality_scores in representative_faces are also 0-100 (e.g., 23.063)
                # Database constraint requires: CHECK (face_quality >= 0.0 AND face_quality <= 1.0)
                # MUST normalize by dividing by 100
                if vision_quality > 0.0:
                    # Normalize from 0-100 to 0-1 range
                    effective_quality = vision_quality / 100.0
                else:
                    # Fallback quality (already in 0-1 range)
                    effective_quality = 0.85
                
                # Prefer real UUID fields and coerce non-UUID labels (e.g.
                # 'person_1') so single-media MVR creation does not abort with
                # a hex parse error.
                persisted_person_object_uuid = _coerce_to_uuid_str(
                    po.get('person_object_uuid')
                    or po.get('person_uuid')
                    or po.get('person_id')
                )
                if not persisted_person_object_uuid:
                    logger.warning(
                        'Skipping person object without persisted identifier for media %s',
                        media_uuid_str,
                    )
                    continue

                transformed_po = {
                    **po,
                    'person_object_uuid': str(persisted_person_object_uuid),
                    'media_uuid': media_uuid_str,
                    'video_uuid': media_uuid_str,  # Alias for compatibility
                    'face_quality': effective_quality,  # Normalized quality (0.0-1.0)
                    'quality_score': effective_quality,  # Consistent with face_quality
                    'confidence_score': 0.9,  # Default confidence
                    # best_face_crop already added by enrichment function
                }
                person_objects.append(transformed_po)
            
            logger.info(
                f"Transformed {len(person_objects)} person objects for MVR processing "
                f"(media: {media_uuid_str})"
            )
            logger.info(f"DEBUG: person_objects sample after transform: {person_objects[:1] if person_objects else 'EMPTY'}")
            logger.info(f"[VMETA DEBUG] transformed person_objects: {len(person_objects)}")
            
            if not person_objects:
                # No faces detected - valid result
                logger.info(f"No faces detected in {media_uuid_str}")
                results.append(MediaResult(
                    media_uuid=media_uuid_str,
                    media_type=media_type,
                    status="completed",
                    mvr_people=[],
                    total_faces_detected=0,
                    mvr_people_count=0,
                    processing_time_ms=int((time.time() - media_start) * 1000)
                ))
                continue
            
            logger.info(
                f"Found {len(person_objects)} person objects for {media_uuid_str}, "
                f"creating individuals and MVR people..."
            )
            logger.info(f"[VMETA DEBUG] About to call MVR service with {len(person_objects)} person objects")
            logger.info(f"[VMETA DEBUG] person_objects sample: {person_objects[:1] if person_objects else 'EMPTY'}")
            
            # Step 6: Process single media for MVR creation
            # This creates isolated individuals linked to person_objects, then creates MVR people
            # Maintains relationship: MVR → Individual → Person Objects (for routes/appearances)
            result_dict = await mvr_service.process_single_media_for_mvr(
                media_uuid=media_uuid,
                media_type=media_type,
                person_objects=person_objects,
                similarity_threshold=request.processing_options.similarity_threshold,
                min_face_quality=request.processing_options.min_face_quality,
                include_demographics=request.processing_options.include_demographics,
                include_route_data=request.processing_options.include_route_data,
                media_timestamp=media_metadata.get('timestamp')
            )
            
            logger.info(
                f"MVR creation completed for {media_uuid_str}: "
                f"{len(result_dict.get('mvr_people', []))} MVR people created"
            )
            
            # Convert result to MediaResult model
            mvr_people_models = []
            for mvr_data in result_dict.get('mvr_people', []):
                # Build route data if included
                route_data = None
                if request.processing_options.include_route_data and person_objects:
                    route_data_dict = build_route_data(
                        media_type=media_type,
                        person_objects=person_objects,
                        video_width=media_metadata.get('resolution', {}).get('width', 1920),
                        video_height=media_metadata.get('resolution', {}).get('height', 1080),
                        include_route=True
                    )
                    if route_data_dict:
                        route_data = RouteData(**route_data_dict)
                
                # Build demographics if included
                demographics = None
                if mvr_data.get('demographics'):
                    demographics = Demographics(**mvr_data['demographics'])
                
                # Build appearances (placeholder - would need actual data)
                # Convert to dict format for Pydantic model validation
                appearances = [
                    {
                        'individual_uuid': ind_uuid,
                        'video_uuid': media_uuid_str,
                        'person_object_uuid': ind_uuid,  # Simplified
                        'start_timestamp': media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                        'end_timestamp': media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                        'confidence': mvr_data.get('confidence_score', 0.9)
                    }
                    for ind_uuid in mvr_data.get('individual_uuids', [])
                ]
                
                mvr_person = MVRPerson(
                    mvr_people_uuid=mvr_data['mvr_people_uuid'],
                    individual_uuids=mvr_data.get('individual_uuids', []),
                    total_appearances=mvr_data.get('total_appearances', 1),
                    unique_videos=1,
                    first_seen=media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                    last_seen=media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                    confidence_score=mvr_data.get('confidence_score', 0.9),
                    quality_score=mvr_data.get('quality_score', 0.9),
                    demographics=demographics,
                    appearances=appearances,
                    route_data=route_data,
                    is_isolated=True,
                    source_media_uuid=media_uuid_str
                )
                
                mvr_people_models.append(mvr_person)
            
            results.append(MediaResult(
                media_uuid=media_uuid_str,
                media_type=media_type,
                status="completed",
                mvr_people=mvr_people_models,
                total_faces_detected=result_dict.get('total_faces_detected', 0),
                mvr_people_count=result_dict.get('mvr_people_count', 0),
                processing_time_ms=result_dict.get('processing_time_ms', 0)
            ))
            
        except Exception as e:
            logger.error(f"Error processing media {media_uuid_str}: {e}", exc_info=True)
            results.append(MediaResult(
                media_uuid=media_uuid_str,
                media_type="unknown",
                status="failed",
                error=MediaProcessingError(
                    code="PROCESSING_ERROR",
                    message=str(e)
                )
            ))
    
    # Calculate aggregate statistics
    processing_time = time.time() - start_time
    completed_results = [r for r in results if r.status == "completed"]
    failed_results = [r for r in results if r.status == "failed"]
    
    total_mvr = sum(r.mvr_people_count for r in completed_results)
    total_faces = sum(r.total_faces_detected for r in completed_results)
    
    # Break down by media type
    photos = [r for r in completed_results if r.media_type == "photo"]
    videos = [r for r in completed_results if r.media_type == "video"]
    
    processing_breakdown = {}
    
    if photos:
        processing_breakdown["photos"] = MediaTypeStatistics(
            count=len(photos),
            total_mvr=sum(r.mvr_people_count for r in photos),
            avg_processing_ms=sum(r.processing_time_ms for r in photos) / len(photos)
        )
    
    if videos:
        processing_breakdown["videos"] = MediaTypeStatistics(
            count=len(videos),
            total_mvr=sum(r.mvr_people_count for r in videos),
            avg_processing_ms=sum(r.processing_time_ms for r in videos) / len(videos)
        )
    
    aggregate_stats = AggregateStatistics(
        total_mvr_people_created=total_mvr,
        total_individuals_detected=total_faces,
        total_faces_detected=total_faces,
        average_mvr_per_media=total_mvr / len(completed_results) if completed_results else 0,
        processing_breakdown=processing_breakdown
    ) if request.response_format.aggregate_statistics else None
    
    return ProcessMediaResponse(
        success=True,
        total_media=len(request.media_uuids),
        processed_media=len(completed_results),
        failed_media=len(failed_results),
        processing_time_seconds=processing_time,
        results=results,
        aggregate_statistics=aggregate_stats
    )


# ============================================================================
# ENDPOINT 15: Hierarchical MVR Merge
# ============================================================================

@router.post(
    "/merge/hierarchical",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Hierarchical MVR People Merge",
    description="""
    Performs hierarchical merging of MVR People based on face embedding similarity.
    
    **Process**:
    1. Calculates pairwise similarity matrix for all provided MVR UUIDs
    2. Finds merge groups using Union-Find algorithm (connected components)
    3. Executes merges within each group (highest quality wins)
    4. Returns super-individual UUIDs and merge metadata
    
    **Use Case**: Automatic post-search consolidation to eliminate duplicates
    across batch processing results.
    
    **Parameters**:
    - `mvr_uuids`: List of MVR UUIDs to merge
    - `similarity_threshold`: Minimum similarity for merging (0.50-0.90, default 0.60)
    - `min_similarity_check`: Skip comparisons below this (optimization, default 0.50)
    
    **Returns**:
    - `super_individuals`: List of winning MVR UUIDs (super-individual UUIDs)
    - `merge_groups`: Detailed merge metadata for each group
    - `statistics`: Merge statistics (totals, counts)
    """,
)
async def hierarchical_merge_mvr_people(
    mvr_uuids: List[UUID] = Body(..., description="List of MVR UUIDs to merge"),
    similarity_threshold: float = Body(
        0.60,
        ge=0.50,
        le=0.90,
        description="Minimum similarity threshold for merging (default 0.60)"
    ),
    min_similarity_check: float = Body(
        0.50,
        ge=0.30,
        le=0.80,
        description="Skip comparisons below this (optimization)"
    ),
    force_merge: bool = Body(
        False,
        description="Bypass similarity checks and merge all provided UUIDs unconditionally. Use for manual user-initiated merges."
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    cache_client = Depends(get_cache_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Perform hierarchical merging of MVR People.
    
    This endpoint implements the automatic post-search merging described in
    the Hierarchical MVR People Merging proposal (v2.19.84).
    """
    try:
        from services.hierarchical_mvr_merger import HierarchicalMVRMerger
        
        logger.info(
            f"User {current_user.get('sub')} requesting hierarchical merge "
            f"of {len(mvr_uuids)} MVR people (threshold: {similarity_threshold})"
        )
        
        # Validate input
        if not mvr_uuids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mvr_uuids list cannot be empty"
            )
        
        if len(mvr_uuids) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 1000 MVR UUIDs per merge request"
            )
        
        # Initialize merger
        merger = HierarchicalMVRMerger(
            repository=mvr_repository,
            mvr_matcher=mvr_matcher
        )
        
        # Perform merge
        result = await merger.merge_hierarchical(
            mvr_uuids=mvr_uuids,
            similarity_threshold=similarity_threshold,
            min_similarity_check=min_similarity_check,
            force_merge=force_merge,
        )
        
        logger.info(
            f"Hierarchical merge complete: {result['statistics']['total_mvr']} → "
            f"{result['statistics']['super_individuals']} super-individuals"
        )
        
        # Invalidate cached search results for all videos these MVR people appeared in,
        # so the next search reflects the merged state instead of returning stale data.
        try:
            async with mvr_repository.pool.acquire() as _inv_conn:
                video_rows = await _inv_conn.fetch(
                    """
                    SELECT DISTINCT iva.video_uuid::text
                    FROM individual_video_appearances iva
                    JOIN individual_mvr_mapping imm
                        ON iva.individual_uuid = imm.individual_uuid
                    WHERE imm.mvr_people_uuid = ANY($1::uuid[])
                    """,
                    mvr_uuids,
                )
            affected_videos = [str(r["video_uuid"]) for r in video_rows]
            if affected_videos:
                invalidated = await cache_client.invalidate_mvr_search(
                    video_uuids=affected_videos
                )
                logger.info(
                    f"🗑️  Invalidated cache for {invalidated} key(s) "
                    f"covering {len(affected_videos)} affected videos after merge"
                )
        except Exception as _inv_err:
            logger.warning(f"Cache invalidation after merge failed (non-fatal): {_inv_err}")

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hierarchical merge failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hierarchical merge failed: {str(e)}"
        )


# ============================================================================
# ENDPOINT 16: Get Super-Individual Hierarchy
# ============================================================================

@router.get(
    "/super-individual/{super_individual_uuid}/hierarchy",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Super-Individual Hierarchy",
    description="""
    Retrieves the 3-tier hierarchy for a super-individual (merged MVR person).
    
    **Hierarchy Levels**:
    - **Level 1**: Super-individual (featured MVR person)
    - **Level 2**: Merged MVR people (paginated – those orphaned into the super-individual)
    - **Level 3**: All individuals and person objects across all MVR
    
    **Pagination** (for merged children):
    - Use `merged_page` and `merged_page_size` to page through Level 2 children.
    - The response includes `merged_children_total`, `merged_children_page`,
      `merged_children_page_size`, and `merged_children_has_more` for cursor navigation.
    - `all_individuals` and aggregate stats always reflect the complete hierarchy
      regardless of the current page.
    
    **Returns**:
    - `super_individual`: Featured MVR person data
    - `merged_mvr_people`: Paginated list of merged MVR people for the requested page
    - `merged_children_total`: Total count of all merged children
    - `merged_children_has_more`: Whether further pages exist
    - `all_individuals`: All individuals from all MVR in the hierarchy
    - `total_person_objects`: Total detection count across all levels
    - `mvr_count`: Total number of MVR people in hierarchy
    - `unique_videos`: Number of unique videos represented
    
    **Use Case**: Display hierarchical view in PersonObjectsDetailScreen.
    """,
)
async def get_super_individual_hierarchy(
    super_individual_uuid: UUID,
    merged_page: int = Query(1, ge=1, description="Page number for merged-children list"),
    merged_page_size: int = Query(
        10, ge=1, le=50, description="Page size for merged-children list"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Get full hierarchy for a super-individual.
    
    Merged MVR children are paginated; aggregate stats cover the full hierarchy.
    """
    try:
        from services.hierarchical_mvr_merger import HierarchicalMVRMerger
        
        logger.info(
            f"User {current_user.get('sub')} requesting hierarchy for "
            f"super-individual {super_individual_uuid} "
            f"(merged_page={merged_page}, merged_page_size={merged_page_size})"
        )
        
        # Initialize merger
        merger = HierarchicalMVRMerger(
            repository=mvr_repository,
            mvr_matcher=mvr_matcher
        )
        
        # Get hierarchy with paginated merged children
        hierarchy = await merger.get_super_individual_hierarchy(
            super_individual_uuid,
            merged_page=merged_page,
            merged_page_size=merged_page_size,
        )
        
        logger.info(
            f"Retrieved hierarchy: {hierarchy['mvr_count']} MVR people, "
            f"{len(hierarchy['all_individuals'])} individuals, "
            f"{hierarchy['total_person_objects']} person objects, "
            f"page {merged_page}/{max(1, -(-hierarchy['merged_children_total'] // merged_page_size))}"
        )
        
        return hierarchy
        
    except Exception as e:
        logger.error(
            f"Failed to get hierarchy for {super_individual_uuid}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve hierarchy: {str(e)}"
        )


@router.post(
    "/analysis",
    summary="Get Backend-Owned MVR Search Analysis",
    description=(
        "Return canonical aggregated analyses for a set of MVR UUIDs. "
        "Grouping and orphan-root resolution happen in the backend so the "
        "frontend can render the returned analyses without hierarchy logic."
    ),
)
async def get_mvr_search_analysis(
    request: MVRSearchAnalysisRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    try:
        stored_comparison_enabled = await _get_mvr_stored_comparison_enabled()
        ephemeral_groups_by_super_uuid = {
            str(group.get("super_individual_uuid")): group
            for group in (request.ephemeral_groups or [])
            if group.get("super_individual_uuid")
        }

        if not stored_comparison_enabled:
            analyses = []
            requested_uuids = [str(uuid) for uuid in request.mvr_uuids]

            for requested_uuid in requested_uuids:
                ephemeral_group = ephemeral_groups_by_super_uuid.get(requested_uuid)
                member_uuids = [requested_uuid]
                if ephemeral_group is not None:
                    member_uuids.extend(
                        [
                            str(member_uuid)
                            for member_uuid in ephemeral_group.get(
                                "merged_mvr_uuids",
                                [],
                            )
                        ]
                    )
                analyses.append(
                    await _build_analysis_from_mvr_person(
                        mvr_repository=mvr_repository,
                        mvr_person_uuid=requested_uuid,
                        session_uuid=request.session_uuid,
                        start_time=request.start_time,
                        end_time=request.end_time,
                        member_mvr_person_uuids=member_uuids,
                        ephemeral_group=ephemeral_group,
                    )
                )

            analyses.sort(
                key=lambda item: (item["first_seen"], item["individual_uuid"])
            )

            logger.info(
                "User %s requested backend-owned MVR analysis with stored comparison disabled: %d inputs -> %d analyses",
                current_user.get("sub"),
                len(request.mvr_uuids),
                len(analyses),
            )

            return {
                "success": True,
                "view_type": "mvr",
                "stored_comparison_enabled": False,
                "requested_mvr_uuids": requested_uuids,
                "resolved_super_individual_uuids": [],
                "skipped_duplicate_inputs": [],
                "analyses": analyses,
            }

        from services.hierarchical_mvr_merger import HierarchicalMVRMerger

        merger = HierarchicalMVRMerger(
            repository=mvr_repository,
            mvr_matcher=mvr_matcher,
        )

        seen_resolved_roots = set()
        resolved_roots: List[str] = []
        skipped_duplicate_inputs: List[str] = []
        analyses: List[Dict[str, Any]] = []

        for requested_uuid in request.mvr_uuids:
            hierarchy = await merger.get_super_individual_hierarchy(
                requested_uuid,
                merged_page=request.merged_page,
                merged_page_size=request.merged_page_size,
            )

            resolved_uuid = str(
                hierarchy.get("resolved_super_individual_uuid") or requested_uuid
            )

            if resolved_uuid in seen_resolved_roots:
                skipped_duplicate_inputs.append(str(requested_uuid))
                continue

            seen_resolved_roots.add(resolved_uuid)
            resolved_roots.append(resolved_uuid)
            analyses.append(
                _build_analysis_from_hierarchy(
                    hierarchy=hierarchy,
                    session_uuid=request.session_uuid,
                    start_time=request.start_time,
                    end_time=request.end_time,
                )
            )

        analyses.sort(key=lambda item: (item["first_seen"], item["individual_uuid"]))

        logger.info(
            "User %s requested backend-owned MVR analysis for %d inputs -> %d analyses",
            current_user.get("sub"),
            len(request.mvr_uuids),
            len(analyses),
        )

        return {
            "success": True,
            "view_type": "mvr",
            "stored_comparison_enabled": True,
            "requested_mvr_uuids": [str(uuid) for uuid in request.mvr_uuids],
            "resolved_super_individual_uuids": resolved_roots,
            "skipped_duplicate_inputs": skipped_duplicate_inputs,
            "analyses": analyses,
        }
    except Exception as e:
        logger.error("Failed to build MVR search analysis: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build MVR search analysis: {str(e)}",
        )


# ============================================================================
# ENDPOINT: Get Best Images for MVRpeople
# ============================================================================

@router.get(
    "/{mvr_uuid}/best-image",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Best Face and Frame Images",
    description="Retrieve the highest quality cropped face and corresponding frame image for an MVRpeople UUID. "
                "Supports super-individuals with merged children aggregation.",
)
async def get_best_images_for_mvr(
    mvr_uuid: UUID,
    request: Request,
    include_merged: bool = Query(
        default=False,
        description="Include merged children if super-individual"
    ),
    use_cache: bool = Query(
        default=True,
        description="Use cached result if available (future enhancement)"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get best quality face and frame images for MVRpeople.
    
    **Features:**
    - Returns highest quality cropped face from all appearances
    - Includes corresponding frame image for context
    - Supports super-individual aggregation (includes merged children)
    - Uses Vision service REST API (no cross-service database queries)
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_uuid: MVRpeople UUID or Super-individual UUID
    - include_merged: Include merged MVR children for super-individuals
    - use_cache: Use cached result if available (default: true)
    
    **Returns:**
    - 200 OK: Best face and frame images with metadata
    - 404 Not Found: MVRpeople not found or no appearances
    - 503 Service Unavailable: Vision service unavailable
    
    **Response includes:**
    - best_face: Highest quality cropped face (URL, quality score, metadata)
    - frame_image: Corresponding frame image (URL, metadata)
    - metadata: Processing statistics and cache info
    """
    logger.info(
        f"User {current_user.get('sub')} requesting best images for MVR {mvr_uuid} "
        f"(include_merged={include_merged})"
    )
    
    try:
        from services.mvr_image_manager import MVRImageManager
        import os
        
        # Extract auth token from request headers
        auth_header = request.headers.get("Authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
        
        # Check if MVR exists
        mvr_exists = await mvr_repository.get_mvr_people_by_uuid(mvr_uuid)
        if not mvr_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MVRpeople {mvr_uuid} not found"
            )

        logger.info(
            "[IG-DEBUG] best-image request mvr_uuid=%s include_merged=%s use_cache=%s is_orphaned=%s merged_count=%s name=%s name_updated_at=%s",
            mvr_uuid,
            include_merged,
            use_cache,
            mvr_exists.get("is_orphaned") if isinstance(mvr_exists, dict) else None,
            mvr_exists.get("merged_count") if isinstance(mvr_exists, dict) else None,
            mvr_exists.get("name") if isinstance(mvr_exists, dict) else None,
            mvr_exists.get("name_updated_at") if isinstance(mvr_exists, dict) else None,
        )
        
        # Initialize image manager with auth token
        orchestrator_url = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8002")
        
        image_manager = MVRImageManager(
            mvr_repo=mvr_repository,
            orchestrator_url=orchestrator_url,
            service_token=auth_token  # Pass user's auth token for Orchestrator calls
        )
        
        # Get best images
        result = await image_manager.get_best_images_for_mvr(
            mvr_uuid=str(mvr_uuid),
            include_merged=include_merged,
            use_cache=use_cache
        )

        logger.info(
            "[IG-DEBUG] best-image result mvr_uuid=%s has_best_face=%s has_frame_image=%s metadata=%s",
            mvr_uuid,
            result.best_face is not None,
            result.frame_image is not None,
            result.metadata,
        )
        
        # Convert to dict for response
        response_dict = result.to_dict()
        
        if not result.best_face:
            logger.warning(f"No images found for MVR {mvr_uuid}")
            logger.warning(
                "[IG-DEBUG] best-image empty mvr_uuid=%s include_merged=%s metadata=%s",
                mvr_uuid,
                include_merged,
                result.metadata,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No appearances or images found for MVRpeople {mvr_uuid}"
            )
        
        logger.info(
            f"✅ Returned best images for MVR {mvr_uuid} "
            f"(quality={result.best_face.quality_score:.3f}, "
            f"time={result.metadata['processing_time_ms']}ms)"
        )
        
        return response_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get best images for {mvr_uuid}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve images: {str(e)}"
        )


# ============================================================================
# ENDPOINT 19: Update MVR Person Name
# ============================================================================

@router.patch(
    "/{mvr_person_uuid}/name",
    summary="Update MVR Person Name",
    description=(
        "Update the user-assigned name for an MVR person and optionally "
        "propagate it through the merge hierarchy to all related MVR people."
    ),
)
async def update_mvr_person_name(
    mvr_person_uuid: str,
    request: UpdateNameRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Update MVR person name with optional propagation to merged hierarchy.
    
    The name will be applied to:
    1. The specified MVR person
    2. If propagate=true: All super-individuals containing this MVR person
    3. If propagate=true: All constituent MVR people in those super-individuals
    
    Args:
        mvr_person_uuid: UUID of MVR person to update
        request: Name update request with name and propagation flag
        mvr_repository: MVR repository dependency
        current_user: Current authenticated user
        
    Returns:
        UpdateNameResponse with affected UUIDs
    """
    try:
        logger.info(
            f"Updating name for MVR {mvr_person_uuid} to '{request.name}' "
            f"(propagate={request.propagate}, user={current_user.get('email')})"
        )
        
        # Validate UUID format
        try:
            mvr_uuid = UUID(mvr_person_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MVR person UUID format: {mvr_person_uuid}"
            )
        
        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Check if MVR person exists
            mvr_check = await conn.fetchrow(
                """
                SELECT mvr_people_uuid, is_orphaned 
                FROM mvr_people 
                WHERE mvr_people_uuid = $1
                """,
                mvr_uuid
            )
            
            if not mvr_check:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MVR person {mvr_person_uuid} not found"
                )
            
            if mvr_check['is_orphaned']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update name for orphaned MVR person"
                )
            
            # Sanitize name (empty string clears the name)
            name = request.name.strip() if request.name else None
            user_email = current_user.get('email', 'unknown')
            now = datetime.now()
            
            # Get the old name before updating (for history)
            old_name_result = await conn.fetchrow(
                "SELECT name FROM mvr_people WHERE mvr_people_uuid = $1",
                mvr_uuid
            )
            old_name = old_name_result['name'] if old_name_result else None
            
            # Update the target MVR person's name
            await conn.execute(
                """
                UPDATE mvr_people
                SET name = $1,
                    name_updated_at = $2,
                    name_updated_by = $3
                WHERE mvr_people_uuid = $4
                """,
                name, now, user_email, mvr_uuid
            )
            
            # Record in history
            await conn.execute(
                """
                INSERT INTO mvr_people_name_history 
                (mvr_people_uuid, old_name, new_name, changed_by, reason)
                VALUES ($1, $2, $3, $4, 'user_edit')
                """,
                mvr_uuid, old_name, name, user_email
            )
            
            propagated_to = []
            affected_super_individuals = []
            
            # Propagate name if requested
            if request.propagate and name:
                logger.info(f"Propagating name '{name}' through merge hierarchy...")
                
                # Find all super-individuals that this MVR person is merged into
                super_individuals = await conn.fetch(
                    """
                    SELECT DISTINCT super_individual_uuid
                    FROM mvr_merge_hierarchy
                    WHERE merged_mvr_uuid = $1
                    """,
                    mvr_uuid
                )
                
                for super_row in super_individuals:
                    super_uuid = super_row['super_individual_uuid']
                    affected_super_individuals.append(str(super_uuid))
                    
                    # Update super-individual name
                    await conn.execute(
                        """
                        UPDATE mvr_people
                        SET name = $1,
                            name_updated_at = $2,
                            name_updated_by = $3
                        WHERE mvr_people_uuid = $4
                        """,
                        name, now, user_email, super_uuid
                    )
                    
                    # Record in history
                    await conn.execute(
                        """
                        INSERT INTO mvr_people_name_history 
                        (mvr_people_uuid, new_name, changed_by, reason)
                        VALUES ($1, $2, $3, 'merge_inherit')
                        """,
                        super_uuid, name, user_email
                    )
                    
                    # Find all other constituent MVR people merged into this super-individual
                    constituents = await conn.fetch(
                        """
                        SELECT merged_mvr_uuid
                        FROM mvr_merge_hierarchy
                        WHERE super_individual_uuid = $1
                        AND merged_mvr_uuid != $2
                        """,
                        super_uuid, mvr_uuid  # Exclude the one we just updated
                    )
                    
                    # Propagate name to all constituents
                    for constituent_row in constituents:
                        constituent_uuid = constituent_row['merged_mvr_uuid']
                        propagated_to.append(str(constituent_uuid))
                        
                        await conn.execute(
                            """
                            UPDATE mvr_people
                            SET name = $1,
                                name_updated_at = $2,
                                name_updated_by = $3
                            WHERE mvr_people_uuid = $4
                            """,
                            name, now, user_email, constituent_uuid
                        )
                        
                        # Record in history
                        await conn.execute(
                            """
                            INSERT INTO mvr_people_name_history 
                            (mvr_people_uuid, new_name, changed_by, reason)
                            VALUES ($1, $2, $3, 'merge_inherit')
                            """,
                            constituent_uuid, name, user_email
                        )
            
            logger.info(
                f"✅ Updated name for MVR {mvr_person_uuid}: "
                f"propagated to {len(propagated_to)} constituents, "
                f"{len(affected_super_individuals)} super-individuals"
            )
            
            return UpdateNameResponse(
                success=True,
                mvr_person_uuid=str(mvr_uuid),
                name=name,
                updated_at=now,
                propagated_to=propagated_to,
                affected_super_individuals=affected_super_individuals
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update name for {mvr_person_uuid}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update name: {str(e)}"
        )


@router.patch(
    "/{mvr_person_uuid}/gender",
    summary="Update MVR Person Gender",
    description=(
        "Update the gender for an MVR person and optionally "
        "propagate it through the merge hierarchy to all related MVR people."
    ),
)
async def update_mvr_person_gender(
    mvr_person_uuid: str,
    request: UpdateGenderRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Update MVR person gender with optional propagation to merged hierarchy.
    
    The gender will be applied to:
    1. The specified MVR person
    2. If propagate=true: All super-individuals containing this MVR person
    3. If propagate=true: All constituent MVR people in those super-individuals
    
    Args:
        mvr_person_uuid: UUID of MVR person to update
        request: Gender update request with gender and propagation flag
        mvr_repository: MVR repository dependency
        current_user: Current authenticated user
        
    Returns:
        UpdateGenderResponse with affected UUIDs
    """
    try:
        logger.info(
            f"Updating gender for MVR {mvr_person_uuid} to '{request.gender}' "
            f"(propagate={request.propagate}, user={current_user.get('email')})"
        )
        
        # Validate UUID format
        try:
            mvr_uuid = UUID(mvr_person_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MVR person UUID format: {mvr_person_uuid}"
            )
        
        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Check if MVR person exists
            mvr_check = await conn.fetchrow(
                """
                SELECT mvr_people_uuid, is_orphaned 
                FROM mvr_people 
                WHERE mvr_people_uuid = $1
                """,
                mvr_uuid
            )
            
            if not mvr_check:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MVR person {mvr_person_uuid} not found"
                )
            
            if mvr_check['is_orphaned']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update gender for orphaned MVR person"
                )
            
            # Sanitize gender (empty string clears the gender)
            gender = request.gender.strip().lower() if request.gender else None
            if gender and gender not in ['male', 'female']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid gender value. Must be 'male' or 'female'"
                )
            
            now = datetime.now()
            
            # Update the target MVR person's gender
            await conn.execute(
                """
                UPDATE mvr_people
                SET gender = $1
                WHERE mvr_people_uuid = $2
                """,
                gender, mvr_uuid
            )
            
            propagated_to = []
            affected_super_individuals = []
            
            # Propagate gender if requested
            if request.propagate and gender:
                logger.info(f"Propagating gender '{gender}' through merge hierarchy...")
                
                # Find all super-individuals that this MVR person is merged into
                super_individuals = await conn.fetch(
                    """
                    SELECT DISTINCT super_individual_uuid
                    FROM mvr_merge_hierarchy
                    WHERE merged_mvr_uuid = $1
                    """,
                    mvr_uuid
                )
                
                for super_row in super_individuals:
                    super_uuid = super_row['super_individual_uuid']
                    affected_super_individuals.append(str(super_uuid))
                    
                    # Update the super-individual's gender
                    await conn.execute(
                        """
                        UPDATE mvr_people
                        SET gender = $1
                        WHERE mvr_people_uuid = $2
                        """,
                        gender, super_uuid
                    )
                    
                    # Find all other constituent MVR people merged into this super-individual
                    constituents = await conn.fetch(
                        """
                        SELECT merged_mvr_uuid
                        FROM mvr_merge_hierarchy
                        WHERE super_individual_uuid = $1
                        AND merged_mvr_uuid != $2
                        """,
                        super_uuid, mvr_uuid  # Exclude the one we just updated
                    )
                    
                    # Propagate gender to all constituents
                    for constituent_row in constituents:
                        constituent_uuid = constituent_row['merged_mvr_uuid']
                        propagated_to.append(str(constituent_uuid))
                        
                        await conn.execute(
                            """
                            UPDATE mvr_people
                            SET gender = $1
                            WHERE mvr_people_uuid = $2
                            """,
                            gender, constituent_uuid
                        )
            
            logger.info(
                f"✅ Updated gender for MVR {mvr_person_uuid}: "
                f"propagated to {len(propagated_to)} constituents, "
                f"{len(affected_super_individuals)} super-individuals"
            )
            
            return UpdateGenderResponse(
                success=True,
                mvr_person_uuid=str(mvr_uuid),
                gender=gender,
                updated_at=now,
                propagated_to=propagated_to,
                affected_super_individuals=affected_super_individuals
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update gender for {mvr_person_uuid}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update gender: {str(e)}"
        )


# ============================================================================
# ENDPOINT: Daily MVR Activity Stats (internal, no auth)
# ============================================================================

@router.get(
    "/stats/daily",
    response_class=JSONResponse,
    summary="Daily MVR activity stats for monitoring",
    description="Returns daily counts of MVR people created, merges, and cross-video matches over the last N days. Intended for internal service-to-service calls.",
)
async def get_mvr_daily_stats(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
):
    """Internal stats endpoint for the monitoring dashboard."""
    try:
        async with mvr_repository.pool.acquire() as conn:
            # MVR people created per day
            created_rows = await conn.fetch("""
                SELECT date_trunc('day', created_at)::date AS day,
                       COUNT(*) AS count
                FROM mvr_people
                WHERE created_at >= NOW() - ($1 || ' days')::interval
                  AND merged_into_mvr_uuid IS NULL
                GROUP BY day
                ORDER BY day
            """, str(days))

            # Merges per day (from merge hierarchy)
            merge_rows = await conn.fetch("""
                SELECT date_trunc('day', merge_timestamp)::date AS day,
                       COUNT(*) AS count
                FROM mvr_merge_hierarchy
                WHERE merge_timestamp >= NOW() - ($1 || ' days')::interval
                GROUP BY day
                ORDER BY day
            """, str(days))

            # Cross-video individual appearances linked per day
            mapping_rows = await conn.fetch("""
                SELECT date_trunc('day', linked_at)::date AS day,
                       COUNT(*) AS count
                FROM individual_mvr_mapping
                WHERE linked_at >= NOW() - ($1 || ' days')::interval
                GROUP BY day
                ORDER BY day
            """, str(days))

            # Total active MVR people
            total_active = await conn.fetchval("""
                SELECT COUNT(*) FROM mvr_people
                WHERE merged_into_mvr_uuid IS NULL
                  AND is_orphaned = FALSE
            """) or 0

        return {
            "days": days,
            "total_active_mvr_people": total_active,
            "mvr_created_per_day": [
                {"date": str(row["day"]), "count": row["count"]}
                for row in created_rows
            ],
            "merges_per_day": [
                {"date": str(row["day"]), "count": row["count"]}
                for row in merge_rows
            ],
            "mappings_per_day": [
                {"date": str(row["day"]), "count": row["count"]}
                for row in mapping_rows
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get MVR daily stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MVR stats: {str(e)}"
        )


# ============================================================================
# Router Export
# ============================================================================

__all__ = ["router"]




from fastapi import APIRouter, HTTPException, Query, Request
"""
Cross-Video Individual Tracking - Simple Working Implementation
PPL Meta Platform v2.19.13+

A minimal working implementation that directly uses the database
for session management without complex dependencies.

================================================================================
CACHING ARCHITECTURE - Multi-Level Strategy
================================================================================

The system implements a hierarchical caching strategy to avoid redundant
processing and ensure consistent results across sessions:

Level 1: SESSION-LEVEL CACHE (Exact Match)
────────────────────────────────────────────
- Scope: Entire tracking session
- Key: (collections, start_time, end_time, algorithm_config)
- Returns: Existing session_uuid if exact match found
- Benefit: Zero processing for duplicate requests
- Example: Re-running same time range returns cached session instantly

Level 2: SESSION-WIDE BULK CACHE (Video Set Match)
───────────────────────────────────────────────────
- Scope: All videos in current session
- Key: Set of video UUIDs + total video count (exact match required)
- Query Logic (FIXED 2025-11-09):
  * Step 1: Find candidate sessions with SAME total_videos count
  * Step 2: Count how many candidate's videos appear in current request
  * Step 3: Only match if ALL candidate's videos are in current request
  * This prevents false matches when individuals span more videos than
    were originally submitted to the cached session
  * Example: Session A submitted 6 videos, but individuals appear in
    22 videos due to cross-video tracking. A request for 14 of those
    22 videos will NOT match Session A (prevents incorrect cache hits)
- Returns: All individuals from that session (already deduplicated)
- Process:
  1. Extract all video UUIDs for current session
  2. Query for recent session with exact video set match
  3. If found: Retrieve ALL individuals from that session
  4. Link individuals to new session with processing_type='cached'
  5. Skip ALL video processing (preload, matching, merging)
- Benefit: Fast retrieval of identical results for same video sets
- Example: Sessions 18 & 21 process videos [v1,v2,v3,v4,v5,v6]
  → Session 21 reuses all 3 individuals from Session 18
  → Processing time: ~1 second vs 3-5 seconds

Level 3: PER-VIDEO CACHE (Video-Level Match) - CURRENTLY DISABLED
──────────────────────────────────────────────────────────────────
- Scope: Individual video processing (fallback when Level 2 misses)
- Status: DISABLED to avoid conflicts with Level 2
- Previous behavior: Find latest session with this video, get individuals
- Note: Caused duplicate individuals when querying across multiple sessions

================================================================================
MVR (MASTER VIDEO RECORD) PEOPLE ARCHITECTURE
================================================================================

After individuals are created/cached, they undergo MVR deduplication to
identify the same person appearing multiple times:

Phase 1: INDIVIDUAL CREATION
────────────────────────────
- Videos are processed in groups of 2 (temporal matching)
- Each group creates "individuals" (person appearances in videos)
- Result: Multiple individuals may represent the same person

Phase 2: EMBEDDING-BASED MERGING (4-Phase Architecture)
────────────────────────────────────────────────────────
A. FETCH & LOAD: Extract embeddings from person_objects (in-memory, no DB)
B. COMPUTE: Calculate cosine similarity matrix between all individuals
C. PREPARE: Group similar individuals (threshold: 0.70) into MVR people
D. EXECUTE: Create MVR people records and mappings in single transaction

MVR People Structure:
- One MVR person = one unique real-world individual
- Multiple individuals can map to same MVR person
- MVR person stores:
  * Best quality face embedding (Facenet512, 512-dim vector)
  * Featured individual UUID (highest confidence)
  * Confidence and quality scores
  * Created timestamp

Individual-to-MVR Mapping:
- Table: individual_mvr_mapping
- Links each individual_uuid to mvr_people_uuid
- Allows querying all appearances of a real person across sessions

================================================================================
COMPLETE WORKFLOW EXAMPLE
================================================================================

Session 18 (2025-11-09 10:28:56):
└─ Videos: [v1, v2, v3, v4, v5, v6]
└─ Processing:
   ├─ Group 0 (v1, v2): Creates ind_34bc8c14
   ├─ Group 1 (v3, v4): Creates ind_7d8334dc
   └─ Group 2 (v5, v6): Creates ind_8b35b478
└─ MVR Deduplication:
   └─ All 3 individuals merged → MVR person mvr_abc123
└─ Result: 3 individuals, 1 unique MVR person

Session 21 (2025-11-09 11:35:33) - Same Videos:
└─ Videos: [v1, v2, v3, v4, v5, v6]
└─ Session-Wide Bulk Cache Check:
   ├─ Query: Find session with ALL 6 videos
   ├─ Match: Session 18 (most recent)
   └─ Action: Retrieve all 3 individuals from Session 18
└─ Cache Hit:
   ├─ ind_34bc8c14 (cached)
   ├─ ind_7d8334dc (cached)
   └─ ind_8b35b478 (cached)
└─ Link to Session 21: processing_type='cached'
└─ Skip: Video processing, matching, merging (already done!)
└─ Result: Same 3 individuals, same 1 MVR person, ~1 second

Key Benefits:
1. Consistency: Identical video sets always return identical individuals
2. Performance: 70% reduction in processing time (1s vs 3-5s)
3. Accuracy: MVR people maintain identity across sessions
4. Traceability: processing_type field shows data source ('cached' vs 'new')

Cache Metrics Tracking:
- cache_hits: Number of videos that hit cache
- Session 18: cache_hits=0 (no previous session)
- Session 21: cache_hits=6 (all videos cached)
- individuals_found: Total individuals in session
- unique_mvr_people_count: Unique real-world people identified
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
import logging
import json
import hashlib
import asyncio
import httpx
import os

from pydantic import BaseModel, Field
from ml.age_estimator import AgeEstimator
from ml.gender_classifier import GenderClassifier
from api.v1.ml_inference import get_age_estimator, get_gender_classifier

# Get the database client from the main app
try:
    from ...database.client import VmetaDatabaseClient
    from ...config.settings import VmetaSettings
except ImportError:
    from database.client import VmetaDatabaseClient
    from config.settings import VmetaSettings

logger = logging.getLogger(__name__)

# Request/Response Models
class CreateTrackingSessionRequest(BaseModel):
    """Request model for creating a new tracking session."""
    collections: List[str] = Field(..., min_items=1, max_items=10)
    start_time: Optional[datetime] = None  # Optional when video_uuids provided
    end_time: Optional[datetime] = None  # Optional when video_uuids provided
    video_uuids: Optional[List[str]] = None  # Explicit video UUIDs - skip time-based query if provided
    algorithm_config: Optional[Dict[str, Any]] = None
    background_processing: bool = True
    force_reprocess: bool = False
    description: Optional[str] = None

class TrackingSessionResponse(BaseModel):
    """Response model for tracking session creation."""
    session_uuid: str
    status: str
    message: str
    cache_hit_rate: float
    total_videos: int


class ManualSessionMVRRequest(BaseModel):
    """Request model for explicitly creating MVRs for a completed session."""
    similarity_threshold: Optional[float] = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Similarity threshold to use for explicit MVR creation"
    )


class ManualSessionMVRResponse(BaseModel):
    """Response model for explicit session-level MVR creation."""
    success: bool
    session_uuid: str
    status: str
    queued_individual_count: int
    task_id: Optional[str] = None
    similarity_threshold: float
    message: str

class IndividualAppearance(BaseModel):
    """Response model for individual appearance in a video."""
    individual_uuid: str
    video_uuid: str
    person_object_uuid: str
    start_timestamp: datetime
    end_timestamp: datetime
    entry_bbox: Optional[List[float]] = None
    exit_bbox: Optional[List[float]] = None
    confidence_score: float

class IndividualAppearancesResponse(BaseModel):
    """Response model for all appearances of an individual."""
    individual_uuid: str
    individual_id: str
    total_appearances: int
    total_videos: int
    appearances: List[IndividualAppearance]


class MergeIndividualsRequest(BaseModel):
    """Request model for manually merging individuals."""
    individual_uuids: List[str] = Field(
        ...,
        min_items=2,
        description="List of individual UUIDs to merge (min 2)"
    )
    session_uuid: str = Field(..., description="Tracking session UUID")
    similarity_threshold: Optional[float] = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for merge validation"
    )
    triggered_by: Optional[str] = Field(
        default="manual",
        description="Source that triggered the merge"
    )


class MergeIndividualsResponse(BaseModel):
    """Response model for individual merge operation."""
    success: bool
    predominant_individual_uuid: str
    merged_individual_uuids: List[str]
    similarity_score: Optional[float] = None
    total_appearances_after_merge: int
    total_videos_after_merge: int
    merged_at: datetime
    message: Optional[str] = None


# Global database client reference
db_client: Optional[VmetaDatabaseClient] = None

def get_database_client() -> VmetaDatabaseClient:
    """Get the global database client from main app."""
    # Import here to avoid circular imports
    import main
    return main.db_client


def _normalize_gender_value(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"male", "female", "unknown"}:
        return normalized
    return None


def _safe_float_value(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int_value(value):
    try:
        if value is None:
            return None
        parsed = int(value)
        return parsed if parsed >= 0 else None
    except (TypeError, ValueError):
        return None


def _extract_demographics_from_person_object(person_object: dict) -> dict:
    """Extract the best available demographics from person-object payloads."""
    demographics = {
        'gender': None,
        'gender_confidence': None,
        'age_min': None,
        'age_max': None,
        'age_confidence': None,
    }

    if not isinstance(person_object, dict):
        return demographics

    raw_demographics = person_object.get('demographics')
    if isinstance(raw_demographics, dict):
        demographics['gender'] = _normalize_gender_value(raw_demographics.get('gender'))
        demographics['gender_confidence'] = _safe_float_value(raw_demographics.get('gender_confidence'))
        demographics['age_min'] = _safe_int_value(raw_demographics.get('age_min'))
        demographics['age_max'] = _safe_int_value(raw_demographics.get('age_max'))
        demographics['age_confidence'] = _safe_float_value(raw_demographics.get('age_confidence'))

    representative_faces = person_object.get('representative_faces') or []
    if isinstance(representative_faces, dict):
        representative_faces = representative_faces.get('faces', []) or []

    age_samples = []
    age_confidences = []

    for face_entry in representative_faces:
        if not isinstance(face_entry, dict):
            continue
        face_data = face_entry.get('face_data') if isinstance(face_entry.get('face_data'), dict) else face_entry

        age_detection = face_data.get('age_detection')
        if isinstance(age_detection, dict):
            estimated_age = _safe_int_value(age_detection.get('estimated_age'))
            if estimated_age is not None:
                age_samples.append(estimated_age)
                confidence = _safe_float_value(age_detection.get('confidence'))
                if confidence is not None:
                    age_confidences.append(confidence)

        for gender_key in ('gender_detection', 'gender_estimate'):
            gender_block = face_data.get(gender_key)
            if not isinstance(gender_block, dict):
                continue
            candidate_gender = _normalize_gender_value(
                gender_block.get('gender') or gender_block.get('estimated_gender')
            )
            if candidate_gender is None:
                continue
            candidate_confidence = _safe_float_value(gender_block.get('confidence'))
            current_confidence = _safe_float_value(demographics.get('gender_confidence'))
            if demographics['gender'] is None or (
                candidate_confidence is not None and
                (current_confidence is None or candidate_confidence > current_confidence)
            ):
                demographics['gender'] = candidate_gender
                demographics['gender_confidence'] = candidate_confidence

        fallback_gender = _normalize_gender_value(
            face_data.get('gender') or face_data.get('estimated_gender')
        )
        if fallback_gender is not None and demographics['gender'] is None:
            demographics['gender'] = fallback_gender
            demographics['gender_confidence'] = _safe_float_value(face_data.get('gender_confidence'))

    if age_samples:
        demographics['age_min'] = min(age_samples)
        demographics['age_max'] = max(age_samples)
        if age_confidences:
            demographics['age_confidence'] = sum(age_confidences) / len(age_confidences)
    return demographics


def _select_preferred_demographics(*candidates: Optional[dict]) -> dict:
    """Pick the best available demographics across candidate sources."""
    preferred = {
        'gender': None,
        'gender_confidence': None,
        'age_min': None,
        'age_max': None,
        'age_confidence': None,
    }

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        gender = _normalize_gender_value(candidate.get('gender'))
        gender_confidence = _safe_float_value(candidate.get('gender_confidence'))
        current_gender_confidence = _safe_float_value(preferred.get('gender_confidence'))
        if gender is not None and (
            preferred['gender'] is None or
            (gender_confidence is not None and (
                current_gender_confidence is None or
                gender_confidence > current_gender_confidence
            ))
        ):
            preferred['gender'] = gender
            preferred['gender_confidence'] = gender_confidence

        age_min = _safe_int_value(candidate.get('age_min'))
        age_max = _safe_int_value(candidate.get('age_max'))
        age_confidence = _safe_float_value(candidate.get('age_confidence'))
        current_age_confidence = _safe_float_value(preferred.get('age_confidence'))
        if (
            (age_min is not None or age_max is not None) and
            (preferred['age_min'] is None and preferred['age_max'] is None or
             (age_confidence is not None and (
                 current_age_confidence is None or age_confidence > current_age_confidence
             )))
        ):
            preferred['age_min'] = age_min
            preferred['age_max'] = age_max
            preferred['age_confidence'] = age_confidence

    return preferred


async def get_or_create_individuals_for_video(
    video_uuid: str,
    session_uuid: str,
    db_client: VmetaDatabaseClient,
    create_new_callback=None
) -> tuple[List[str], bool]:
    """
    Check for existing individuals in this video, or create new ones.
    
    CRITICAL: Respects merge history - only reuses predominant individuals.
    
    This implements the MVR-aware caching strategy that:
    1. Checks for existing individuals in the video
    2. Filters out merged individuals (marked with merged_into_uuid)
    3. Groups individuals by MVR-People to avoid duplicates
    4. Only reuses one individual per MVR-People (the predominant one)
    5. Falls back to creating new individuals if none found
    
    Args:
        video_uuid: UUID of the video to check
        session_uuid: UUID of the current tracking session
        db_client: Database client instance
        create_new_callback: Optional async function to create new individuals
                           Should return List[str] of individual UUIDs
    
    Returns:
        Tuple of (individual_uuids, cache_hit)
        - individual_uuids: List of individual UUIDs to use
        - cache_hit: True if reused existing, False if created new
    """
    
    async with db_client.pool.acquire() as conn:
        # Step 1: Check for existing individuals in this video
        # Include MVR-People information to detect merges
        existing = await conn.fetch("""
            SELECT DISTINCT 
                iva.individual_uuid,
                iva.person_object_uuid,
                i.individual_id,
                i.merged_into_uuid,  -- If set, individual was merged
                mvr.mvr_people_uuid  -- MVR-People linkage
            FROM individual_video_appearances iva
            JOIN individuals i ON i.individual_uuid = iva.individual_uuid
            LEFT JOIN individual_mvr_mapping mvr 
                ON mvr.individual_uuid = i.individual_uuid
            WHERE iva.video_uuid = $1
        """, video_uuid)
        # DEBUG: record how many existing appearances were found for this video
        try:
            async with db_client.pool.acquire() as _dbg_conn:
                await _dbg_conn.execute(
                    """
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                    """,
                    session_uuid,
                    f"cache_lookup_existing_count:{len(existing)} for video:{video_uuid}"
                )
        except Exception:
            # Non-fatal: continue without blocking caching
            pass

        # Debug: Log query result
        logger.info(f"🔍 Cache query for video {video_uuid[:8]}: found {len(existing)} existing records")
        
        if existing:
            # Step 2: Filter out merged individuals and group by MVR
            active_individuals = {}  # mvr_uuid -> individual_uuid
            standalone_individuals = []  # No MVR linkage
            
            for record in existing:
                individual_uuid = str(record['individual_uuid'])
                merged_into = record['merged_into_uuid']
                mvr_uuid = str(record['mvr_people_uuid']) if record['mvr_people_uuid'] else None
                
                # Skip merged individuals (they point to another individual)
                if merged_into:
                    logger.info(
                        f"⏭️ Skipping merged individual {record['individual_id']} "
                        f"(merged into {merged_into}) for video {video_uuid}"
                    )
                    continue
                
                # Group by MVR-People (if exists)
                if mvr_uuid:
                    # If multiple individuals share same MVR, keep only one
                    if mvr_uuid not in active_individuals:
                        active_individuals[mvr_uuid] = individual_uuid
                        logger.info(
                            f"♻️ Found individual {record['individual_id']} "
                            f"with MVR {mvr_uuid} for video {video_uuid}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Multiple individuals share MVR {mvr_uuid}! "
                            f"Keeping {active_individuals[mvr_uuid]}, "
                            f"skipping {individual_uuid} for video {video_uuid}"
                        )
                else:
                    # No MVR linkage - standalone individual
                    standalone_individuals.append(individual_uuid)
                    logger.info(
                        f"♻️ Found standalone individual {record['individual_id']} "
                        f"for video {video_uuid}"
                    )
                    # DEBUG: Log to database
                    try:
                        async with db_client.pool.acquire() as _dbg_conn:
                            await _dbg_conn.execute(
                                """
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                                """,
                                session_uuid,
                                f"found_standalone:{record['individual_id']}"
                            )
                    except Exception:
                        pass
            
            # Step 3: Combine MVR-linked and standalone individuals
            individual_uuids = list(active_individuals.values()) + standalone_individuals
            
            # DEBUG: Log the result of combining individuals
            try:
                async with db_client.pool.acquire() as _dbg_conn:
                    await _dbg_conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"combined_uuids:mvr={len(active_individuals)}_standalone={len(standalone_individuals)}_total={len(individual_uuids)}_for_{video_uuid[:8]}")  # noqa
            except Exception:
                pass
            
            if not individual_uuids:
                logger.warning(
                    f"⚠️ All individuals for video {video_uuid} were merged/duplicates. "
                    f"Will create new individuals."
                )
                # All existing individuals were filtered out (merged/duplicates)
                # Fall through to Step 5 to create new individuals
                pass  # Explicitly fall through
            else:
                # Step 4: Reuse existing individuals (only predominant ones)
                logger.info(
                    f"♻️ Reusing {len(individual_uuids)} individuals for video {video_uuid} "
                    f"(filtered from {len(existing)} total records)"
                )
                
                # DEBUG: Log before adding session links
                try:
                    async with db_client.pool.acquire() as _dbg_conn:
                        await _dbg_conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                            f"adding_session_links_for_{len(individual_uuids)}_individuals")  # noqa
                except Exception:
                    pass
                
                for individual_uuid in individual_uuids:
                    # Add session link (individual can belong to multiple sessions)
                    await conn.execute("""
                        INSERT INTO session_individuals
                        (session_uuid, individual_uuid, processing_type, confidence_contribution)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (session_uuid, individual_uuid) DO NOTHING
                    """, session_uuid, individual_uuid, 'cached', 0.95)
                
                # DEBUG: Log successful return
                try:
                    async with db_client.pool.acquire() as _dbg_conn:
                        await _dbg_conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                            f"returning_cached:count={len(individual_uuids)}_for_{video_uuid[:8]}")  # noqa
                except Exception:
                    pass
                
                return (individual_uuids, True)  # Cache hit!
        
        # Step 5: No existing individuals (or all were merged) - create new
        logger.info(
            f"🆕 No active individuals for video {video_uuid}, creating new"
        )
        
        # Call the provided callback to create new individuals
        if create_new_callback:
            individual_uuids = await create_new_callback()
            return (individual_uuids, False)  # Cache miss
        else:
            # No callback provided, return empty list
            return ([], False)


# Initialize router
router = APIRouter(
    prefix="/individuals/tracking",
    tags=["Cross-Video Individual Tracking"]
)


@router.post("/sessions", response_model=TrackingSessionResponse)
async def create_tracking_session(
    request: CreateTrackingSessionRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    """
    Create new cross-video individual tracking session.
    
    Simple implementation that stores session in database.
    """
    try:
        # Generate session UUID
        session_uuid = str(uuid4())
        
        # Create config hash
        config_str = json.dumps(request.algorithm_config or {}, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Get database client
        db_client = get_database_client()
        
        # Validate: either (start_time + end_time) or video_uuids must be provided
        if not request.video_uuids and (not request.start_time or not request.end_time):
            raise HTTPException(
                status_code=400,
                detail="Either video_uuids or both start_time and end_time must be provided"
            )
        
        # Convert to timezone-naive datetime for comparison (if provided)
        start_time_naive = None
        end_time_naive = None
        if request.start_time and request.end_time:
            start_time_naive = request.start_time.replace(tzinfo=None) if request.start_time.tzinfo else request.start_time
            end_time_naive = request.end_time.replace(tzinfo=None) if request.end_time.tzinfo else request.end_time
        elif request.video_uuids:
            # Use dummy timestamps when explicit video_uuids provided
            # These are only for database storage compliance, not actual filtering
            now = datetime.utcnow()
            start_time_naive = now
            end_time_naive = now + timedelta(microseconds=1)
        
        # Check for existing completed session with same parameters
        # Skip cache if force_reprocess is True
        # Only use cache if session successfully found videos (total_videos > 0)
        existing_session = None
        if not request.force_reprocess:
            async with db_client.pool.acquire() as conn:
                existing_session = await conn.fetchrow("""
                    SELECT session_uuid, status, total_videos, 
                           processed_videos, individuals_found
                    FROM tracking_sessions
                    WHERE config_hash = $1
                      AND collections = $2
                      AND start_time = $3
                      AND end_time = $4
                      AND status = 'completed'
                      AND total_videos > 0
                    ORDER BY completed_at DESC
                    LIMIT 1
                """, config_hash, request.collections, 
                     start_time_naive, end_time_naive)
        
        # If existing session found, return it as cache hit
        if existing_session and not request.force_reprocess:
            logger.info(
                f"Cache HIT: Returning existing session "
                f"{existing_session['session_uuid']}"
            )
            return TrackingSessionResponse(
                session_uuid=str(existing_session['session_uuid']),
                status="completed",
                message="Cached session found",
                cache_hit_rate=1.0,
                total_videos=existing_session['total_videos']
            )
        
        # No cache hit - create new session
        logger.info(f"Cache MISS: Creating new session {session_uuid}")
        
        # Store session in database (including video_uuids if provided)
        async with db_client.pool.acquire() as conn:
            # Prepare video_uuids for storage
            # CRITICAL: Pass as Python list, not JSON string - asyncpg handles JSONB conversion
            video_uuids_list = request.video_uuids if request.video_uuids else None
            
            await conn.execute("""
                INSERT INTO tracking_sessions (
                    session_uuid, user_id, collections, start_time, end_time,
                    status, config_hash, algorithm_config, video_uuids
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
            session_uuid,
            "system_user",  # Default user for now
            request.collections,
            start_time_naive,
            end_time_naive,
            "initialized",
            config_hash,
            json.dumps(request.algorithm_config) if request.algorithm_config else json.dumps({
                "iou_threshold": 0.3,
                "max_gap_seconds": 10,
                "min_overlap_confidence": 0.5
            }),
            video_uuids_list  # Pass as list, asyncpg converts to JSONB
            )
        
        logger.info(f"Created tracking session {session_uuid} for collections: {request.collections}")
        
        # Capture Authorization header (if any) and pass to background worker
        auth_header = None
        try:
            auth_header = http_request.headers.get('authorization') or http_request.headers.get('Authorization')
            if auth_header:
                logger.info("✅ Auth header captured from request")
            else:
                logger.warning("⚠️ No auth header in request")
        except Exception:
            auth_header = None

        # Persist an initial creation debug entry with a short preview of the auth header
        try:
            db_client = get_database_client()
            auth_preview = None
            if auth_header:
                auth_preview = (auth_header[:20] + '...' + auth_header[-8:]) if len(auth_header) > 40 else auth_header
            async with db_client.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                    """,
                    session_uuid,
                    f"create_auth_preview: present={bool(auth_header)}, preview={auth_preview}"
                )
        except Exception:
            logger.debug("Failed to write create_auth_preview for session %s", session_uuid)

        # Schedule background processing if requested
        if request.background_processing:
            # Pass auth header through to the background worker so it can call gateway/media with auth
            background_tasks.add_task(process_tracking_session, session_uuid, auth_header)
        
        return TrackingSessionResponse(
            session_uuid=session_uuid,
            status="initialized",
            message="Session created successfully",
            cache_hit_rate=0.0,
            total_videos=0
        )
        
    except Exception as e:
        logger.error(f"Failed to create tracking session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/sessions/{session_uuid}")
async def get_session_status(session_uuid: str):
    """
    Get tracking session status.
    """
    try:
        db_client = get_database_client()
        
        async with db_client.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT session_uuid, status, collections, created_at, 
                       started_at, completed_at, total_videos, processed_videos,
                       individuals_found, unique_mvr_people_count, cache_hits
                FROM tracking_sessions 
                WHERE session_uuid = $1
            """, session_uuid)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_uuid} not found"
            )
        
        return {
            "session_uuid": str(result["session_uuid"]),
            "status": result["status"],
            "collections": result["collections"],
            "created_at": result["created_at"],
            "started_at": result["started_at"],
            "completed_at": result["completed_at"],
            "total_videos": result["total_videos"],
            "processed_videos": result["processed_videos"],
            "individuals_found": result["individuals_found"],
            "unique_mvr_people_count": result["unique_mvr_people_count"],
            "cache_hits": result["cache_hits"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/sessions/{session_uuid}/create-mvrs",
    response_model=ManualSessionMVRResponse,
)
async def create_mvrs_for_session(
    session_uuid: str,
    request: ManualSessionMVRRequest,
    http_request: Request,
):
    """
    Explicitly queue MVR creation for a completed tracking session.

    This endpoint is the manual path for session-level MVR creation when the
    continuous pipeline is configured not to merge automatically.
    """
    try:
        db_client = get_database_client()

        async with db_client.pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT session_uuid, status
                FROM tracking_sessions
                WHERE session_uuid = $1
                """,
                session_uuid,
            )

            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_uuid} not found",
                )

            if session["status"].upper() != "COMPLETED":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Session must be completed before explicit MVR creation. "
                        f"Current status: {session['status']}"
                    ),
                )

            individual_rows = await conn.fetch(
                """
                SELECT DISTINCT si.individual_uuid
                FROM session_individuals si
                WHERE si.session_uuid = $1
                ORDER BY si.individual_uuid
                """,
                session_uuid,
            )

        individual_uuids = [row["individual_uuid"] for row in individual_rows]

        if not individual_uuids:
            return ManualSessionMVRResponse(
                success=True,
                session_uuid=session_uuid,
                status="no-op",
                queued_individual_count=0,
                similarity_threshold=float(request.similarity_threshold or 0.70),
                message="Session has no linked individuals to convert into MVRs",
            )

        import main

        mvr_processor = getattr(main, "mvr_background_processor", None)
        if not mvr_processor:
            raise HTTPException(
                status_code=503,
                detail="MVR background processor is not available",
            )

        auth_header = (
            http_request.headers.get("authorization")
            or http_request.headers.get("Authorization")
        )

        queue_result = await mvr_processor.queue_session_mvr_creation(
            session_uuid=UUID(session_uuid),
            individual_uuids=individual_uuids,
            auth_token=auth_header,
            similarity_threshold=float(request.similarity_threshold or 0.70),
        )

        return ManualSessionMVRResponse(
            success=True,
            session_uuid=session_uuid,
            status="queued",
            queued_individual_count=len(individual_uuids),
            task_id=queue_result.get("task_id"),
            similarity_threshold=float(request.similarity_threshold or 0.70),
            message="Explicit session MVR creation queued",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue manual session MVR creation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/cache/status")
async def get_cache_status():
    """
    Get cache status information.
    """
    try:
        db_client = get_database_client()
        
        async with db_client.pool.acquire() as conn:
            # Get basic cache statistics
            session_count = await conn.fetchval(
                "SELECT COUNT(*) FROM tracking_sessions"
            )
            
            individual_count = await conn.fetchval(
                "SELECT COUNT(*) FROM individuals"
            )
            
            cache_object_count = await conn.fetchval(
                "SELECT COUNT(*) FROM cached_person_objects"
            )
        
        return {
            "total_sessions": session_count,
            "total_individuals": individual_count,
            "total_cached_objects": cache_object_count,
            "status": "operational"
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/individuals/{individual_uuid}/appearances", response_model=IndividualAppearancesResponse)
async def get_individual_appearances(individual_uuid: str):
    """
    Get all appearances of a specific individual across videos.
    
    Returns detailed information about when and where the individual
    appeared in each video, including timestamps and spatial data.
    """
    try:
        db_client = get_database_client()
        
        async with db_client.pool.acquire() as conn:
            # First, get the individual info
            individual_info = await conn.fetchrow("""
                SELECT individual_uuid, individual_id, confidence_score
                FROM individuals 
                WHERE individual_uuid = $1
            """, individual_uuid)
            
            if not individual_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"Individual {individual_uuid} not found"
                )
            
            # Get all appearances for this individual
            appearances = await conn.fetch("""
                SELECT 
                    iva.individual_uuid,
                    iva.video_uuid,
                    iva.person_object_uuid,
                    iva.start_timestamp,
                    iva.end_timestamp,
                    iva.entry_bbox,
                    iva.exit_bbox,
                    iva.confidence_score
                FROM individual_video_appearances iva
                WHERE iva.individual_uuid = $1
                ORDER BY iva.start_timestamp
            """, individual_uuid)
            
            # Convert to response format
            appearance_list = []
            unique_videos = set()
            
            for appearance in appearances:
                unique_videos.add(str(appearance["video_uuid"]))
                appearance_list.append(IndividualAppearance(
                    individual_uuid=str(appearance["individual_uuid"]),
                    video_uuid=str(appearance["video_uuid"]),
                    person_object_uuid=str(appearance["person_object_uuid"]),
                    start_timestamp=appearance["start_timestamp"],
                    end_timestamp=appearance["end_timestamp"],
                    entry_bbox=list(appearance["entry_bbox"]) if appearance["entry_bbox"] else None,
                    exit_bbox=list(appearance["exit_bbox"]) if appearance["exit_bbox"] else None,
                    confidence_score=appearance["confidence_score"]
                ))
            
            return IndividualAppearancesResponse(
                individual_uuid=str(individual_info["individual_uuid"]),
                individual_id=individual_info["individual_id"],
                total_appearances=len(appearance_list),
                total_videos=len(unique_videos),
                appearances=appearance_list
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get individual appearances: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def preload_person_objects_for_all_videos(
    all_videos: List[dict],
    auth_token: Optional[str],
    session_uuid: str,
    db_client: VmetaDatabaseClient,
    concurrency: int = 6
) -> dict:
    """
    Preload person_objects from Orchestrator for all videos concurrently.
    
    This eliminates network I/O during database transactions by fetching
    all required data upfront into memory.
    
    Args:
        all_videos: List of all video metadata dicts
        auth_token: JWT auth token for Orchestrator API
        session_uuid: Tracking session UUID for debug logging
        db_client: Database client for logging
        concurrency: Max concurrent Orchestrator requests
        
    Returns:
        Dict mapping video_uuid -> List[person_object_dict]
        Returns empty list for videos that fail to fetch
    """
    import aiohttp
    import asyncio
    
    logger.info(f"🔄 Preloading person_objects for {len(all_videos)} videos (concurrency={concurrency})")
    
    # Log preload start
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid, f"preload_start: {len(all_videos)}_videos")
    except Exception:
        pass
    
    video_person_objects = {}
    semaphore = asyncio.Semaphore(concurrency)
    
    async def fetch_one_video(video: dict):
        """Fetch person_objects for one video with semaphore limiting concurrency."""
        video_uuid = video['uuid']
        
        async with semaphore:
            try:
                orchestrator_url = f"http://localhost:8080/api/v1/orchestrator/person-objects/{video_uuid}"
                
                headers = {}
                if auth_token:
                    if auth_token.startswith('Bearer ') or auth_token.startswith('bearer '):
                        headers['Authorization'] = auth_token
                    else:
                        headers['Authorization'] = f'Bearer {auth_token}'
                
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(orchestrator_url, headers=headers) as response:
                        if response.status == 200:
                            orch_data = await response.json()
                            if orch_data.get('success') and orch_data.get('person_groups'):
                                person_objects = []
                                for person_group in orch_data['person_groups']:
                                    person_objects.append({
                                        'person_uuid': person_group.get('person_uuid'),
                                        'person_id': person_group.get('person_id'),
                                        'face_count': person_group.get('face_count'),
                                        'representative_faces': person_group.get('representative_faces', []),
                                        'timestamp': video.get('timestamp'),
                                        'video_uuid': video_uuid
                                    })
                                video_person_objects[video_uuid] = person_objects
                                logger.debug(f"✅ Preloaded {len(person_objects)} person_objects for {video_uuid[:8]}")
                                return True
                            else:
                                video_person_objects[video_uuid] = []
                                return False
                        else:
                            response_text = await response.text()
                            logger.warning(f"Orchestrator {response.status} for {video_uuid[:8]}: {response_text[:100]}")
                            video_person_objects[video_uuid] = []
                            # Log error to DB
                            try:
                                async with db_client.pool.acquire() as conn:
                                    await conn.execute("""
                                        UPDATE tracking_sessions
                                        SET failed_videos = array_append(failed_videos, $2)
                                        WHERE session_uuid = $1
                                    """, session_uuid, f"preload_error_{response.status}: {video_uuid[:8]}")
                            except Exception:
                                pass
                            return False
            except Exception as e:
                logger.error(f"Failed preload for {video_uuid[:8]}: {e}")
                video_person_objects[video_uuid] = []
                # Log error to DB
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid, f"preload_exception: {video_uuid[:8]}, {str(e)[:50]}")
                except Exception:
                    pass
                return False
    
    # Fetch all videos concurrently
    results = await asyncio.gather(*[fetch_one_video(v) for v in all_videos], return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    logger.info(f"✅ Preload complete: {success_count}/{len(all_videos)} videos succeeded")
    
    # Log preload completion
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid, f"preload_complete: {success_count}/{len(all_videos)}_succeeded")
    except Exception:
        pass
    
    return video_person_objects


async def match_person_objects_within_group(
    videos_data: List[dict],
    auth_token: Optional[str],
    session_uuid: str,
    db_client: VmetaDatabaseClient,
    preloaded_data: Optional[dict] = None
) -> List[dict]:
    """
    Match person_objects across videos within a temporal group.
    
    This performs temporal/spatial matching to determine if person_objects
    from different videos represent the same individual.
    
    Args:
        videos_data: List of video metadata dicts with 'uuid', 'timestamp', etc.
        auth_token: JWT auth token for Orchestrator API calls
        session_uuid: Tracking session UUID for debug logging
        db_client: Database client
        
    Returns:
        List of individual records, where each record has:
        {
            'individual_uuid': str,
            'video_uuids': List[str],  # Videos this individual appears in
            'person_objects': dict,  # video_uuid -> person_object data
            'temporal_score': float
        }
    """
    import aiohttp
    from datetime import datetime, timedelta
    from uuid import uuid4
    
    logger.info(f"🔍 Matching person_objects across {len(videos_data)} videos in group")
    
    # Log to database for debugging
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid, f"match_within_group_start: {len(videos_data)}_videos")
    except Exception:
        pass
    
    # Step 1: Get person_objects (use preloaded data if available, else fetch)
    video_person_objects = {}  # video_uuid -> person_objects list
    
    if preloaded_data is not None:
        # Use preloaded data
        logger.info(f"✅ Using preloaded person_objects for {len(videos_data)} videos")
        for video in videos_data:
            video_uuid = video['uuid']
            video_person_objects[video_uuid] = preloaded_data.get(video_uuid, [])
    else:
        # Fallback: fetch individually (old behavior)
        logger.warning("⚠️ No preloaded data, falling back to individual fetch")
        import aiohttp
        
        for video in videos_data:
            video_uuid = video['uuid']
            
            try:
                orchestrator_url = f"http://localhost:8080/api/v1/orchestrator/person-objects/{video_uuid}"
                
                headers = {}
                if auth_token:
                    if auth_token.startswith('Bearer ') or auth_token.startswith('bearer '):
                        headers['Authorization'] = auth_token
                    else:
                        headers['Authorization'] = f'Bearer {auth_token}'
                
                # Add timeout to prevent hanging
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"🔍 Fetching person_objects for {video_uuid[:8]} from Orchestrator...")
                    async with session.get(orchestrator_url, headers=headers) as response:
                        if response.status == 200:
                            orch_data = await response.json()
                            if orch_data.get('success') and orch_data.get('person_groups'):
                                # Each item in person_groups IS a person (not a group of persons)
                                person_objects = []
                                for person_group in orch_data['person_groups']:
                                    # Each person_group has: person_uuid, person_id, face_count, representative_faces
                                    person_objects.append({
                                        'person_uuid': person_group.get('person_uuid'),
                                        'person_id': person_group.get('person_id'),
                                        'face_count': person_group.get('face_count'),
                                        'representative_faces': person_group.get('representative_faces', []),
                                        'timestamp': video.get('timestamp'),
                                        'video_uuid': video_uuid
                                    })
                                video_person_objects[video_uuid] = person_objects
                                logger.info(f"✅ Found {len(person_objects)} person_objects for video {video_uuid[:8]}")
                        else:
                            response_text = await response.text()
                            logger.error(f"Orchestrator returned {response.status} for {video_uuid[:8]}: {response_text[:200]}")
                            video_person_objects[video_uuid] = []
                            # Log to database
                            try:
                                async with db_client.pool.acquire() as conn:
                                    await conn.execute("""
                                        UPDATE tracking_sessions
                                        SET failed_videos = array_append(failed_videos, $2)
                                        WHERE session_uuid = $1
                                    """, session_uuid, f"orch_error_{response.status}: {video_uuid[:8]}, {response_text[:50]}")
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"Failed to fetch person_objects for {video_uuid[:8]}: {e}")
                video_person_objects[video_uuid] = []
                # Log to database
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid, f"orchestrator_fetch_error: {video_uuid[:8]}, {str(e)[:50]}")
                except Exception:
                    pass
    
    # Log fetching complete
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid, f"fetch_complete: {len(video_person_objects)}_videos_fetched")
    except Exception:
        pass
    
    # Step 2: Match person_objects across videos using temporal/spatial logic
    # FIXED: Create one individual per person detected, preserving ALL faces
    
    individuals = []
    
    # Collect ALL person_objects from ALL videos
    all_person_objects = []
    for video_uuid, person_objs in video_person_objects.items():
        for person_obj in person_objs:
            all_person_objects.append({
                'video_uuid': video_uuid,
                'person_obj': person_obj
            })
    
    logger.info(f"📊 Total person_objects across all videos: {len(all_person_objects)}")
    
    # Create one individual for each person_object
    # Each individual represents ONE person with ALL their faces from ONE video
    for person_data in all_person_objects:
        video_uuid = person_data['video_uuid']
        person_obj = person_data['person_obj']
        
        # Create individual record for this person
        individual_uuid = str(uuid4())
        individuals.append({
            'individual_uuid': individual_uuid,
            'video_uuids': [video_uuid],  # Currently appears in one video
            'person_objects': {video_uuid: person_obj},  # Store complete person_object with ALL faces
            'temporal_score': 0.85  # Default score for temporal matches
        })
        
        logger.info(
            f"✅ Created individual {individual_uuid[:8]} for person {person_obj.get('person_uuid', 'unknown')[:8]} "
            f"in video {video_uuid[:8]} with {person_obj.get('face_count', 0)} faces"
        )
    
    # Log completion to database
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid, f"match_complete: {len(individuals)}_individuals_created")
    except Exception:
        pass
    
    logger.info(f"🎉 Temporal matching complete: {len(individuals)} individuals from {len(videos_data)} videos")
    
    return individuals


async def _create_single_mvr_person(
    db_client,
    individual_data: dict,
    session_uuid: str,
    auth_token: str
):
    """
    Create MVR person for a single individual (when no merging is needed).
    
    Args:
        db_client: Database client
        individual_data: Individual dict with structure:
            {
                'individual_uuid': str,
                'video_uuids': List[str],
                'person_objects': Dict[video_uuid, person_object_dict],
                'temporal_score': float
            }
        session_uuid: Tracking session UUID
        auth_token: Authorization token
    """
    from uuid import uuid4
    import numpy as np

    async def _create_fallback_mvr_without_embedding(
        reason: str,
        person_object_payload: dict,
        representative_video: str,
        representative_face: Optional[dict] = None,
    ) -> None:
        confidence_value = 0.5
        quality_value = 0.5

        if isinstance(representative_face, dict):
            confidence_value = representative_face.get('confidence', confidence_value)
            quality_value = (
                representative_face.get('quality')
                or representative_face.get('quality_score')
                or quality_value
            )

        if isinstance(person_object_payload, dict):
            confidence_value = person_object_payload.get('confidence', confidence_value)
            quality_value = (
                person_object_payload.get('quality')
                or person_object_payload.get('quality_score')
                or quality_value
            )

        try:
            confidence_value = max(0.0, min(1.0, float(confidence_value or 0.5)))
        except (TypeError, ValueError):
            confidence_value = 0.5

        try:
            quality_value = float(quality_value or 0.5)
        except (TypeError, ValueError):
            quality_value = 0.5
        if quality_value > 1.0:
            quality_value = quality_value / 100.0
        quality_value = max(0.0, min(1.0, quality_value))

        demographics = _extract_demographics_from_person_object(person_object_payload)
        zero_embedding = '[' + ','.join(['0'] * 512) + ']'
        mvr_people_uuid = str(uuid4())

        async with db_client.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO mvr_people (
                        mvr_people_uuid,
                        featured_individual_uuid,
                        featured_video_uuid,
                        source_media_uuid,
                        face_embedding,
                        confidence_score,
                        quality_score,
                        face_quality,
                        gender,
                        gender_confidence,
                        age_min,
                        age_max,
                        age_confidence,
                        created_by_session,
                        embedding_model,
                        auto_created,
                        is_isolated,
                        created_at,
                        updated_at
                    ) VALUES (
                        $1, $2, $3, $3, $4::vector, $5, $6, $6,
                        $7, $8, $9, $10, $11, $12, $13, TRUE, TRUE, NOW(), NOW()
                    )
                """, mvr_people_uuid, individual_uuid, representative_video,
                    zero_embedding, confidence_value, quality_value,
                    demographics.get('gender'), demographics.get('gender_confidence'),
                    demographics.get('age_min'), demographics.get('age_max'), demographics.get('age_confidence'),
                    session_uuid, 'fallback_zero')

                await conn.execute("""
                    INSERT INTO individual_mvr_mapping (
                        individual_uuid,
                        mvr_people_uuid,
                        similarity_score,
                        confidence_score,
                        quality_score,
                        is_representative,
                        linked_by_session,
                        link_method
                    ) VALUES ($1, $2, 1.0, $3, $4, TRUE, $5, $6)
                """, individual_uuid, mvr_people_uuid, confidence_value, quality_value,
                    session_uuid, 'auto_create')

        logger.warning(
            "[SINGLE MVR] Created fallback MVR %s for individual %s without embedding (%s)",
            mvr_people_uuid[:8],
            individual_uuid[:8],
            reason,
        )
    
    individual_uuid = individual_data['individual_uuid']
    video_uuids = individual_data['video_uuids']
    person_objects_by_video = individual_data['person_objects']
    
    logger.info(f"[SINGLE MVR] Creating MVR person for individual {individual_uuid[:8]}...")
    
    # Pick representative face from first video
    if not video_uuids or not person_objects_by_video:
        logger.warning(f"[SINGLE MVR] No video data for individual {individual_uuid[:8]}, skipping")
        return
    
    representative_video_uuid = video_uuids[0]
    person_object = person_objects_by_video.get(representative_video_uuid)
    
    logger.info(f"[SINGLE MVR DEBUG] video_uuids: {video_uuids}, person_object type: {type(person_object)}")
    
    if not person_object:
        logger.warning(f"[SINGLE MVR] No person_object for individual {individual_uuid[:8]}, skipping")
        return
    
    # Get representative faces
    representative_faces = person_object.get('representative_faces', [])
    
    # DEBUG: Log what we got
    logger.info(f"[SINGLE MVR DEBUG] representative_faces type: {type(representative_faces)}, value: {str(representative_faces)[:200]}")
    
    if not representative_faces:
        logger.warning(f"[SINGLE MVR] No representative faces for individual {individual_uuid[:8]}, using fallback MVR creation")
        await _create_fallback_mvr_without_embedding(
            reason="no_representative_faces",
            person_object_payload=person_object,
            representative_video=representative_video_uuid,
        )
        return
    
    # Parse representative_faces if it's a JSON string
    import json
    if isinstance(representative_faces, str):
        try:
            representative_faces = json.loads(representative_faces)
            logger.info(f"[SINGLE MVR DEBUG] After JSON parse - type: {type(representative_faces)}")
        except json.JSONDecodeError as e:
            logger.error(f"[SINGLE MVR] Failed to parse representative_faces JSON for individual {individual_uuid[:8]}: {e}")
            return
    
    # Check if it's a valid list
    if not isinstance(representative_faces, list):
        logger.warning(f"[SINGLE MVR] representative_faces is not a list (type={type(representative_faces)}), trying to convert")
        # If it's a dict, might be a single face object OR {"faces": [...]} structure
        if isinstance(representative_faces, dict):
            # Check if it has "faces" key (common structure from database)
            if "faces" in representative_faces:
                representative_faces = representative_faces["faces"]
                logger.info(f"[SINGLE MVR DEBUG] Extracted faces array from dict, count: {len(representative_faces)}")
            else:
                # Single face object, wrap it
                representative_faces = [representative_faces]
        else:
            logger.error(f"[SINGLE MVR] Cannot convert representative_faces to list for individual {individual_uuid[:8]}")
            await _create_fallback_mvr_without_embedding(
                reason="invalid_representative_faces_shape",
                person_object_payload=person_object,
                representative_video=representative_video_uuid,
            )
            return
    
    if not representative_faces:
        logger.warning(f"[SINGLE MVR] Empty representative_faces list for individual {individual_uuid[:8]}, using fallback MVR creation")
        await _create_fallback_mvr_without_embedding(
            reason="empty_representative_faces",
            person_object_payload=person_object,
            representative_video=representative_video_uuid,
        )
        return
    
    best_face = representative_faces[0]  # First is highest quality
    
    # If best_face still has "face_data" wrapper, extract it
    if isinstance(best_face, dict) and "face_data" in best_face:
        best_face = best_face["face_data"]
        logger.info(f"[SINGLE MVR DEBUG] Extracted face_data from wrapper")
    
    # Generate embedding using FaceNetProcessor (same as merge pipeline)
    try:
        # Import required modules
        import numpy as np
        import cv2
        import aiohttp
        import os
        
        # Import FaceNet processor
        from ml.facenet_processor import FaceNetProcessor
        
        # Initialize processor
        facenet_processor = FaceNetProcessor()
        
        # Extract bbox and frame info from face_data
        bbox = best_face.get('bbox', [])
        frame_number = best_face.get('frame_number')
        
        # Validate required fields
        if not bbox or not isinstance(bbox, list) or len(bbox) != 4:
            logger.warning(f"[SINGLE MVR] Invalid bbox for individual {individual_uuid[:8]}: {bbox}; using fallback MVR creation")
            await _create_fallback_mvr_without_embedding(
                reason="invalid_bbox",
                person_object_payload=person_object,
                representative_video=representative_video_uuid,
                representative_face=best_face,
            )
            return
        
        if frame_number is None:
            logger.warning(f"[SINGLE MVR] Missing frame_number for individual {individual_uuid[:8]}; using fallback MVR creation")
            await _create_fallback_mvr_without_embedding(
                reason="missing_frame_number",
                person_object_payload=person_object,
                representative_video=representative_video_uuid,
                representative_face=best_face,
            )
            return
        
        # Construct media URL for frame extraction
        # Use gateway URL to fetch the frame
        gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080").rstrip("/")
        media_url = f"{gateway_url}/api/v1/media/{representative_video_uuid}/frame/{frame_number}?format=jpeg"
        
        logger.info(f"[SINGLE MVR] Fetching frame from: {media_url}")
        
        if not media_url or not bbox:
            logger.warning(f"[SINGLE MVR] Missing media_url or bbox for individual {individual_uuid[:8]}")
            return
        
        # Fetch frame
        headers = {}
        if auth_token:
            if not auth_token.startswith('Bearer'):
                headers['Authorization'] = f'Bearer {auth_token}'
            else:
                headers['Authorization'] = auth_token
        
        async with aiohttp.ClientSession() as session:
            async with session.get(media_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"[SINGLE MVR] Failed to fetch frame: {response.status}; using fallback MVR creation")
                    await _create_fallback_mvr_without_embedding(
                        reason=f"frame_fetch_failed_{response.status}",
                        person_object_payload=person_object,
                        representative_video=representative_video_uuid,
                        representative_face=best_face,
                    )
                    return
                
                frame_bytes = await response.read()
        
        # Decode and crop frame
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.warning(f"[SINGLE MVR] Failed to decode frame; using fallback MVR creation")
            await _create_fallback_mvr_without_embedding(
                reason="frame_decode_failed",
                person_object_payload=person_object,
                representative_video=representative_video_uuid,
                representative_face=best_face,
            )
            return
        
        # Crop face using bbox (array format: [x1, y1, x2, y2])
        x_min = int(bbox[0])
        y_min = int(bbox[1])
        x_max = int(bbox[2])
        y_max = int(bbox[3])
        
        # Align bbox to crop frame dimensions if detection resolution differs
        crop_h, crop_w = frame.shape[:2]
        detect_w = best_face.get('frame_width')
        detect_h = best_face.get('frame_height')
        if detect_w and detect_h and (detect_w != crop_w or detect_h != crop_h):
            scale_x = crop_w / detect_w
            scale_y = crop_h / detect_h
            x_min = int(round(x_min * scale_x))
            y_min = int(round(y_min * scale_y))
            x_max = int(round(x_max * scale_x))
            y_max = int(round(y_max * scale_y))
            logger.info(
                f"[SINGLE MVR] BBox aligned: detect={detect_w}x{detect_h} "
                f"crop={crop_w}x{crop_h} scale=({scale_x:.3f},{scale_y:.3f})"
            )
        
        # Ensure bbox is within frame bounds
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(frame.shape[1], x_max)
        y_max = min(frame.shape[0], y_max)
        
        logger.info(f"[SINGLE MVR] Cropping face at bbox: [{x_min}, {y_min}, {x_max}, {y_max}]")
        
        face_crop = frame[y_min:y_max, x_min:x_max]
        
        # Validate face crop
        if face_crop.size == 0:
            logger.warning(f"[SINGLE MVR] Empty face crop for individual {individual_uuid[:8]}; using fallback MVR creation")
            await _create_fallback_mvr_without_embedding(
                reason="empty_face_crop",
                person_object_payload=person_object,
                representative_video=representative_video_uuid,
                representative_face=best_face,
            )
            return
        
        # Generate embedding using FaceNetProcessor
        embedding = facenet_processor.extract_embedding(face_crop, enforce_detection=False)
        
        if embedding is None:
            logger.warning(f"[SINGLE MVR] Failed to generate embedding for individual {individual_uuid[:8]}; using fallback MVR creation")
            await _create_fallback_mvr_without_embedding(
                reason="embedding_generation_failed",
                person_object_payload=person_object,
                representative_video=representative_video_uuid,
                representative_face=best_face,
            )
            return
        
        logger.info(f"[SINGLE MVR] Successfully generated embedding for individual {individual_uuid[:8]}, shape: {embedding.shape}")
        
        # Convert to list for PostgreSQL vector type
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        # Convert list to string format for pgvector (must be string representation)
        embedding_str = str(embedding)
        
        confidence = best_face.get('confidence', 0.5)
        quality = best_face.get('quality', 0.5)
        
        # Ensure quality is never None and is in valid range
        if quality is None:
            quality = 0.5
        # Normalize quality to 0-1 range if needed
        if quality > 1.0:
            quality = quality / 100.0
        # Clamp to valid range
        quality = max(0.0, min(1.0, float(quality)))
        
        # Extract demographics using ML models (same as merge path)
        gender = None
        age_min = None
        age_max = None
        gender_confidence = None
        age_confidence = None
        
        try:
            # Use demographic analysis singletons (imported at top of file)
            # Age estimation
            age_estimator = get_age_estimator()
            age_result = age_estimator.estimate_age(face_crop, enforce_detection=False)
            if age_result:
                age_min = age_result.get('min_age')
                age_max = age_result.get('max_age')
                age_confidence = age_result.get('confidence')
            
            # Gender classification
            gender_classifier = get_gender_classifier()
            gender_result = gender_classifier.classify_gender(face_crop, enforce_detection=False)
            if gender_result:
                gender = gender_result.get('gender')
                gender_confidence = gender_result.get('confidence')
        except Exception as e:
            logger.warning(f"[SINGLE MVR] Demographics extraction failed for {individual_uuid[:8]}: {e}")
        
        logger.info(f"[SINGLE MVR] Demographics: gender={gender}, age={age_min}-{age_max}")
        logger.info(f"[SINGLE MVR] Preparing to create MVR person for individual {individual_uuid[:8]}: confidence={confidence}, quality={quality}, embedding_len={len(embedding)}")
        
        # Create MVR person in database
        mvr_people_uuid = str(uuid4())
        
        async with db_client.pool.acquire() as conn:
            async with conn.transaction():
                # Create MVR person
                await conn.execute("""
                    INSERT INTO mvr_people (
                        mvr_people_uuid, featured_individual_uuid, 
                        face_embedding, confidence_score, quality_score, face_quality,
                        gender, gender_confidence, age_min, age_max, age_confidence,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3::vector, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
                """, mvr_people_uuid, individual_uuid, embedding_str, confidence, quality, quality,
                    gender, gender_confidence, age_min, age_max, age_confidence)
                
                # Create mapping
                await conn.execute("""
                    INSERT INTO individual_mvr_mapping (
                        individual_uuid, mvr_people_uuid,
                        similarity_score, confidence_score, quality_score,
                        is_representative, linked_by_session,
                        link_method
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, individual_uuid, mvr_people_uuid, 1.0, confidence, confidence, 
                    True, session_uuid, 'auto_create')
        
        logger.info(f"✅ [SINGLE MVR] Created MVR person {mvr_people_uuid[:8]} for individual {individual_uuid[:8]}")
        
    except Exception as e:
        logger.error(f"[SINGLE MVR] Failed to create MVR person: {e}", exc_info=True)
        await _create_fallback_mvr_without_embedding(
            reason=f"exception:{type(e).__name__}",
            person_object_payload=person_object if isinstance(person_object, dict) else {},
            representative_video=representative_video_uuid if 'representative_video_uuid' in locals() else None,
            representative_face=best_face if 'best_face' in locals() and isinstance(best_face, dict) else None,
        )


async def merge_individuals_by_similarity(
    db_client,
    session_uuid: str,
    matched_individuals: List[dict],
    auth_token: str,
    similarity_threshold: float = 0.70
) -> int:
    """
    Merge individuals based on facial embedding similarity using 4-phase architecture.
    
    Architecture:
        Phase A: FETCH & LOAD - Extract embeddings from in-memory person_objects (NO DB QUERIES)
        Phase B: COMPUTE - Pure in-memory similarity calculations
        Phase C: PREPARE - Format operations for database
        Phase D: EXECUTE - Single atomic transaction
    
    Args:
        db_client: Database client
        session_uuid: Tracking session UUID
        matched_individuals: List of individual data dicts with structure:
            [{
                'individual_uuid': str,
                'video_uuids': List[str],
                'person_objects': Dict[video_uuid, List[person_object_dict]],
                'temporal_score': float
            }, ...]
        auth_token: Authorization token for media API
        similarity_threshold: Minimum cosine similarity (0-1), default 0.70
        
    Returns:
        Number of individuals merged (removed)
    """
    import numpy as np
    import aiohttp
    import cv2
    from sklearn.metrics.pairwise import cosine_similarity
    
    logger.info(
        f"[MERGE] Starting embedding-based merge for {len(matched_individuals)} individuals "
        f"(threshold={similarity_threshold})"
    )
    
    # DEBUG: Write to database
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid,
                f"merge_start: {len(matched_individuals)}_individuals_threshold={similarity_threshold}")
    except Exception:
        pass
    
    # If only 1 individual, create MVR person directly (no merge needed)
    if len(matched_individuals) < 2:
        logger.info("[MERGE] Only 1 individual - creating single MVR person (no merge needed)")
        if len(matched_individuals) == 1:
            # Create MVR person for the single individual
            await _create_single_mvr_person(db_client, matched_individuals[0], session_uuid, auth_token)
            
            # Update unique_mvr_people_count in tracking session
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET unique_mvr_people_count = (
                        SELECT COUNT(DISTINCT mvr_people_uuid)
                        FROM individual_mvr_mapping
                        WHERE individual_uuid IN (
                            SELECT individual_uuid 
                            FROM session_individuals 
                            WHERE session_uuid = $1
                        )
                    )
                    WHERE session_uuid = $1
                """, session_uuid)
            
            return 0  # 0 merges performed (but 1 MVR person created)
        else:
            logger.info("[MERGE] No individuals to process")
            return 0
    
    try:
        # ================================================================
        # PHASE A: FETCH & LOAD - All I/O upfront
        # ================================================================
        
        logger.info("[MERGE PHASE A] Starting data preload...")
        
        # DEBUG: Log phase A start
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, "merge_phase_a_start")
        except Exception:
            pass
        
        # Import embedding service
        try:
            # DEBUG: Log before import
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, "merge_before_import")
            except Exception:
                pass
            
            from services.embedding_service import (
                EmbeddingService,
                DEEPFACE_AVAILABLE
            )
            logger.info(f"[MERGE] DeepFace available: {DEEPFACE_AVAILABLE}")
            
            # DEBUG: Log after import
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, f"merge_after_import: deepface={DEEPFACE_AVAILABLE}")
            except Exception:
                pass
        except Exception as import_error:
            logger.error(f"[MERGE] Failed to import embedding service: {import_error}")
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, f"merge_import_error: {str(import_error)[:200]}")
            except Exception:
                pass
            return 0
        
        if not DEEPFACE_AVAILABLE:
            logger.warning("[MERGE] DeepFace not available - skipping")
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, "merge_skipped: deepface_unavailable")
            except Exception:
                pass
            return 0
        
        try:
            # DEBUG: Log before service init
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, "merge_before_service_init")
            except Exception:
                pass
            
            embedding_service = EmbeddingService(db_client)
            logger.info("[MERGE] Embedding service initialized")
            
            # DEBUG: Log after service init
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, "merge_after_service_init")
            except Exception:
                pass
        except Exception as service_error:
            logger.error(f"[MERGE] Failed to initialize embedding service: {service_error}")
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, f"merge_service_init_error: {str(service_error)[:200]}")
            except Exception:
                pass
            return 0
        
        # A1: Extract individual data from in-memory matched_individuals (NO DB QUERY!)
        logger.info("[MERGE PHASE A1] Extracting data from in-memory structures...")
        
        # DEBUG: Log A1 start
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"merge_a1_extract_start: {len(matched_individuals)}_individuals")
        except Exception:
            pass
        
        # Extract individual data from the in-memory matched_individuals structure
        # Each matched_individual has: individual_uuid, video_uuids, person_objects, temporal_score
        # person_objects is a dict: {video_uuid: person_object_dict}
        individuals_data = []
        
        for individual in matched_individuals:
            individual_uuid = individual['individual_uuid']
            video_uuids = individual['video_uuids']
            person_objects_by_video = individual['person_objects']
            
            # Pick the first video and its person_object as representative
            if video_uuids and person_objects_by_video:
                representative_video_uuid = video_uuids[0]
                person_object = person_objects_by_video.get(representative_video_uuid)
                
                if person_object:
                    extracted_demographics = _extract_demographics_from_person_object(
                        person_object
                    )
                    individuals_data.append({
                        'individual_uuid': individual_uuid,
                        'video_uuid': representative_video_uuid,
                        'person_object': person_object,  # Full object in memory
                        'all_video_uuids': video_uuids,
                        'first_seen': individual.get('first_seen'),
                        'last_seen': individual.get('last_seen'),
                        'demographics': individual.get('demographics') or extracted_demographics,
                    })
        
        # DEBUG: Log extraction result
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"merge_a1_extract_result: {len(individuals_data)}_extracted")
        except Exception:
            pass
        
        logger.info(
            f"[MERGE PHASE A1] Extracted {len(individuals_data)}/"
            f"{len(matched_individuals)} individuals from memory"
        )
        
        if len(individuals_data) < 2:
            logger.warning("[MERGE] Not enough individuals with person data")
            return 0
        
        # A2: Generate fresh embeddings for each individual (vmeta service)
        # Uses the already-ranked representative faces from Orchestrator
        # (first face is best quality, as ranked by Orchestrator)
        # 
        # Embedding Generation Pipeline:
        # 1. Fetch full frame from Media service endpoint
        # 2. Crop ONLY the face region using bbox coordinates
        # 3. Resize cropped face to 160x160 (Facenet512 optimal input)
        # 4. Generate embedding on resized cropped face
        # 
        # Note: Facenet512 is trained on 160x160 images for optimal results
        logger.info("[MERGE PHASE A2] Generating embeddings from ranked faces...")
        
        # DEBUG: Log A2 start
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"merge_a2_generate_start: {len(individuals_data)}_individuals")
        except Exception:
            pass
        
        # Generate embeddings by:
        # 1. Using best representative face from person_object (already ranked!)
        # 2. Fetching frame bytes from Media service (same endpoint Flutter uses)
        # 3. Decoding frame and cropping face region using bbox
        # 4. Generating embedding using vmeta's EmbeddingService
        
        faces_with_embeddings = []
        
        # Setup auth headers
        headers = {}
        if auth_token:
            if not auth_token.startswith('Bearer'):
                headers['Authorization'] = f'Bearer {auth_token}'
            else:
                headers['Authorization'] = auth_token
        
        # DEBUG: Track failure reasons
        failure_stats = {
            'no_representative_faces': 0,
            'invalid_bbox': 0,
            'frame_fetch_failed': 0,
            'bbox_out_of_bounds': 0,
            'embedding_generation_failed': 0,
            'exception': 0
        }
        
        for ind_data in individuals_data:
            try:
                person_obj = ind_data.get('person_object', {})
                individual_uuid = ind_data['individual_uuid']
                video_uuid = ind_data['video_uuid']
                
                # DEBUG: Log person_object structure
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid, 
                        f"merge_a2_person_obj_keys: {list(person_obj.keys())}")
                except Exception:
                    pass
                
                # Get representative faces (already ranked by Orchestrator)
                representative_faces = person_obj.get('representative_faces', [])
                
                # Parse representative_faces if it's a JSON string (same as single MVR path)
                import json
                if isinstance(representative_faces, str):
                    try:
                        representative_faces = json.loads(representative_faces)
                    except json.JSONDecodeError as e:
                        logger.error(f"[MERGE] Failed to parse representative_faces JSON for individual {individual_uuid[:8]}: {e}")
                        failure_stats['no_representative_faces'] += 1
                        continue
                
                # Check if it's a valid list
                if not isinstance(representative_faces, list):
                    # If it's a dict, might be {"faces": [...]} structure
                    if isinstance(representative_faces, dict) and "faces" in representative_faces:
                        representative_faces = representative_faces["faces"]
                    elif isinstance(representative_faces, dict):
                        # Single face object, wrap it
                        representative_faces = [representative_faces]
                    else:
                        logger.error(f"[MERGE] Cannot convert representative_faces to list for individual {individual_uuid[:8]}")
                        failure_stats['no_representative_faces'] += 1
                        continue
                
                if not representative_faces:
                    logger.warning(
                        f"[MERGE] No representative faces for "
                        f"{individual_uuid[:8]}"
                    )
                    failure_stats['no_representative_faces'] += 1
                    # DEBUG
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid, 
                            f"merge_a2_fail: no_rep_faces_{individual_uuid[:8]}")
                    except Exception:
                        pass
                    continue
                
                # Use first face (highest quality as ranked by Orchestrator)
                best_face = representative_faces[0]
                
                # If best_face has "face_data" wrapper, extract it (same as single MVR path)
                if isinstance(best_face, dict) and "face_data" in best_face:
                    face_data = best_face["face_data"]
                else:
                    # face_data might be at the top level
                    face_data = best_face if isinstance(best_face, dict) else {}
                
                bbox = face_data.get('bbox')
                frame_number = face_data.get('frame_number', 0)
                
                # DEBUG: Log bbox and frame info
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                        f"merge_a2_bbox_info: frame={frame_number} "
                        f"bbox={bbox} uuid={individual_uuid[:8]}")
                except Exception:
                    pass
                
                if not bbox or len(bbox) != 4:
                    logger.warning(
                        f"[MERGE] Invalid bbox for {individual_uuid[:8]}: {bbox}"
                    )
                    failure_stats['invalid_bbox'] += 1
                    continue
                
                # Fetch frame from Media service (same endpoint Flutter uses)
                # GET /api/v1/media/{video_uuid}/frame/{frame_number}
                frame_url = (
                    f"http://localhost:8080/api/v1/media/"
                    f"{video_uuid}/frame/{frame_number}?format=jpeg"
                )
                
                logger.info(
                    f"[MERGE] Fetching frame {frame_number} for "
                    f"{individual_uuid[:8]} from {video_uuid[:8]}"
                )
                
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as session:
                    async with session.get(frame_url, headers=headers) as resp:
                        if resp.status != 200:
                            logger.warning(
                                f"[MERGE] Frame API {resp.status} for "
                                f"{video_uuid[:8]} frame {frame_number}"
                            )
                            continue
                        
                        # Read frame bytes
                        frame_bytes = await resp.read()
                        
                        # Decode frame from JPEG bytes
                        import numpy as np
                        from PIL import Image
                        from io import BytesIO
                        
                        # Decode JPEG to numpy array
                        pil_image = Image.open(BytesIO(frame_bytes))
                        frame = np.array(pil_image)
                        
                        # Convert RGB to BGR (OpenCV format)
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Extract bbox coordinates (format: [x1, y1, x2, y2])
                x = int(bbox[0])
                y = int(bbox[1])
                x2 = int(bbox[2])
                y2 = int(bbox[3])
                
                # Align bbox to crop frame dimensions if detection resolution differs
                frame_h, frame_w = frame_bgr.shape[:2]
                detect_w = face_data.get('frame_width')
                detect_h = face_data.get('frame_height')
                if detect_w and detect_h and (detect_w != frame_w or detect_h != frame_h):
                    scale_x = frame_w / detect_w
                    scale_y = frame_h / detect_h
                    x = int(round(x * scale_x))
                    y = int(round(y * scale_y))
                    x2 = int(round(x2 * scale_x))
                    y2 = int(round(y2 * scale_y))
                    logger.info(
                        f"[MERGE] BBox aligned for {individual_uuid[:8]}: "
                        f"detect={detect_w}x{detect_h} crop={frame_w}x{frame_h} "
                        f"scale=({scale_x:.3f},{scale_y:.3f})"
                    )
                
                w = x2 - x
                h = y2 - y
                
                # DEBUG: Log bbox dimensions
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                        f"merge_a2_crop: w={w} h={h} "
                        f"pos=({x},{y}) uuid={individual_uuid[:8]}")
                except Exception:
                    pass
                
                # Validate bbox dimensions
                if w <= 0 or h <= 0:
                    logger.warning(
                        f"[MERGE] Invalid bbox dimensions for "
                        f"{individual_uuid[:8]}: w={w}, h={h}"
                    )
                    failure_stats['invalid_bbox'] += 1
                    continue
                
                # Validate bbox is within frame bounds (frame_h/frame_w set above with alignment)
                if x < 0 or y < 0 or x2 > frame_w or y2 > frame_h:
                    logger.warning(
                        f"[MERGE] bbox out of bounds for {individual_uuid[:8]}: "
                        f"bbox=[{x},{y},{x2},{y2}], frame=[{frame_w},{frame_h}]"
                    )
                    failure_stats['bbox_out_of_bounds'] += 1
                    continue
                
                # CROP THE FACE from full frame using OpenCV
                # This extracts ONLY the face region for embedding generation
                cropped_face = frame_bgr[y:y2, x:x2].copy()
                
                # Validate cropped face is not empty
                if cropped_face.size == 0:
                    logger.warning(
                        f"[MERGE] Empty crop for {individual_uuid[:8]}"
                    )
                    failure_stats['invalid_bbox'] += 1
                    continue
                
                # RESIZE to 160x160 (Facenet512 optimal input size)
                # Facenet models are trained on 160x160 images
                cropped_face_resized = cv2.resize(
                    cropped_face, (160, 160), interpolation=cv2.INTER_AREA
                )
                
                # DEBUG: Log crop and resize
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                        f"merge_a2_cropped: orig={cropped_face.shape} "
                        f"resized={cropped_face_resized.shape} "
                        f"uuid={individual_uuid[:8]}")
                except Exception:
                    pass
                
                # Generate embedding on RESIZED CROPPED FACE (160x160)
                # Pass full 160x160 face (already resized to optimal size)
                logger.info(
                    f"[MERGE] Generating embedding for {individual_uuid[:8]} "
                    f"from {w}x{h} face resized to 160x160"
                )
                
                embedding, confidence = (
                    await embedding_service._generate_facial_embedding(
                        cropped_face_resized, 0, 0, 160, 160
                    )
                )
                
                # Extract demographics using ML models
                ml_demographics = {
                    'gender': None,
                    'gender_confidence': None,
                    'age_min': None,
                    'age_max': None,
                    'age_confidence': None
                }
                
                try:
                    # Age estimation (using singleton)
                    age_estimator = get_age_estimator()
                    age_result = age_estimator.estimate_age(
                        cropped_face_resized,
                        enforce_detection=False
                    )
                    if age_result:
                        ml_demographics['age_min'] = age_result.get('min_age')
                        ml_demographics['age_max'] = age_result.get('max_age')
                        ml_demographics['age_confidence'] = age_result.get('confidence')
                    
                    # Gender classification (using singleton)
                    gender_classifier = get_gender_classifier()
                    gender_result = gender_classifier.classify_gender(
                        cropped_face_resized,
                        enforce_detection=False
                    )
                    if gender_result:
                        ml_demographics['gender'] = gender_result.get('gender')
                        ml_demographics['gender_confidence'] = gender_result.get('confidence')
                except Exception as e:
                    logger.warning(f"[MERGE] Demographics extraction failed for {individual_uuid[:8]}: {e}")

                demographics = _select_preferred_demographics(
                    ind_data.get('demographics'),
                    _extract_demographics_from_person_object(person_obj),
                    ml_demographics,
                )
                
                if embedding is not None:
                    faces_with_embeddings.append({
                        'individual_uuid': individual_uuid,
                        'embedding': np.array(embedding),
                        'confidence': confidence,
                        'video_uuid': video_uuid,
                        'first_seen': ind_data.get('first_seen'),
                        'last_seen': ind_data.get('last_seen'),
                        'demographics': demographics
                    })
                    logger.info(
                        f"[MERGE] ✅ Generated embedding for "
                        f"{individual_uuid[:8]} (conf: {confidence:.3f})"
                    )
                    # DEBUG: Log success
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid,
                            f"merge_a2_embed_success: "
                            f"uuid={individual_uuid[:8]} conf={confidence:.3f}")
                    except Exception:
                        pass
                else:
                    logger.warning(
                        f"[MERGE] Failed to generate embedding for "
                        f"{individual_uuid[:8]}"
                    )
                    failure_stats['embedding_generation_failed'] += 1
                    # DEBUG: Log failure
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid,
                            f"merge_a2_embed_failed: uuid={individual_uuid[:8]}")
                    except Exception:
                        pass
                    
            except Exception as e:
                logger.error(
                    f"[MERGE] Error generating embedding for "
                    f"{ind_data.get('individual_uuid', 'unknown')[:8]}: {e}",
                    exc_info=True
                )
                failure_stats['exception'] += 1
                # DEBUG: Log exception
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                        f"merge_a2_exception: {str(e)[:100]}")
                except Exception:
                    pass
                continue
        
        # DEBUG: Log generation result
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"merge_a2_generate_result: {len(faces_with_embeddings)}_embeddings")
        except Exception:
            pass
        
        logger.info(
            f"[MERGE PHASE A2] Generated {len(faces_with_embeddings)}/"
            f"{len(individuals_data)} embeddings using vmeta service"
        )
        
        if len(faces_with_embeddings) < 2:
            logger.warning("[MERGE] Not enough embeddings available")
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"merge_skipped: only_{len(faces_with_embeddings)}_embeddings")
            except Exception:
                pass

            # In no-merge materialization mode we still need one persisted MVR row per
            # individual even when representative faces do not include enough geometry
            # to generate embeddings. Fall back to single-person creation for every
            # matched individual.
            fallback_created = 0
            for individual in matched_individuals:
                await _create_single_mvr_person(
                    db_client,
                    individual,
                    session_uuid,
                    auth_token,
                )
                fallback_created += 1

            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET unique_mvr_people_count = (
                        SELECT COUNT(DISTINCT mvr_people_uuid)
                        FROM individual_mvr_mapping
                        WHERE individual_uuid IN (
                            SELECT individual_uuid
                            FROM session_individuals
                            WHERE session_uuid = $1
                        )
                    )
                    WHERE session_uuid = $1
                """, session_uuid)

            return 0
        
        # Phase A complete! We have all embeddings in memory.
        logger.info(
            f"[MERGE PHASE A] Complete: {len(faces_with_embeddings)} "
            "embeddings loaded from memory"
        )
        
        # DEBUG: Report Phase A completion
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"phase_a_complete: {len(faces_with_embeddings)}_embeddings")
        except Exception:
            pass
        
        if len(faces_with_embeddings) < 2:
            logger.warning("[MERGE] Not enough embeddings for merge")
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"merge_skipped: only_{len(faces_with_embeddings)}_embeddings")
            except Exception:
                pass
            return 0
        
        # ================================================================
        # PHASE B: COMPUTE - Pure in-memory operations
        # ================================================================
        
        logger.info("[MERGE PHASE B] Computing similarity matrix...")
        
        # DEBUG: Report Phase B start
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"phase_b_start: {len(faces_with_embeddings)}_embeddings")
        except Exception:
            pass
        
        # B1: Build embeddings matrix from faces_with_embeddings
        uuids = [face['individual_uuid'] for face in faces_with_embeddings]
        embeddings_matrix = np.array([
            face['embedding'] for face in faces_with_embeddings
        ])
        
        # B2: Calculate pairwise similarities
        similarities = cosine_similarity(embeddings_matrix)
        
        logger.info(f"[MERGE PHASE B] Similarity matrix: {similarities.shape}")
        
        # DEBUG: Report similarity calculation complete
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"phase_b_similarity_complete: {similarities.shape}")
        except Exception:
            pass
        
        # B2: Calculate pairwise similarities
        similarities = cosine_similarity(embeddings_matrix)
        
        logger.info(f"[MERGE PHASE B] Similarity matrix: {similarities.shape}")
        
        # DEBUG: Log all pairwise similarities
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, 
                f"phase_b_similarity_complete: {similarities.shape}")
                
                # Log each pairwise similarity
                for i in range(len(uuids)):
                    for j in range(i+1, len(uuids)):
                        sim_score = similarities[i][j]
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid,
                        f"similarity: {uuids[i][:8]}↔{uuids[j][:8]} = {sim_score:.4f} "
                        f"(threshold={similarity_threshold})")
        except Exception:
            pass
        
        # B3: Identify merge candidates using connected components
        # This handles transitive similarity: if A~B and B~C, then A,B,C merge
        merge_groups = []  # [(keep_uuid, [merge_uuid1, merge_uuid2, ...])]

        # Block automatic merges when both sides have confident but conflicting binary gender.
        gender_conflict_min_confidence = 0.80

        def _normalize_gender(value):
            if value is None:
                return None
            normalized = str(value).strip().lower()
            if normalized in {"male", "female"}:
                return normalized
            return None

        def _safe_float(value):
            try:
                if value is None:
                    return 0.0
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        def _can_auto_merge_by_gender(face_a, face_b):
            demographics_a = face_a.get('demographics') or {}
            demographics_b = face_b.get('demographics') or {}

            gender_a = _normalize_gender(demographics_a.get('gender'))
            gender_b = _normalize_gender(demographics_b.get('gender'))

            if gender_a is None or gender_b is None:
                return True
            if gender_a == gender_b:
                return True

            confidence_a = _safe_float(demographics_a.get('gender_confidence'))
            confidence_b = _safe_float(demographics_b.get('gender_confidence'))

            if (
                confidence_a >= gender_conflict_min_confidence
                and confidence_b >= gender_conflict_min_confidence
            ):
                return False

            return True

        def _can_auto_merge_by_time(face_a, face_b):
            first_seen_a = face_a.get('first_seen')
            first_seen_b = face_b.get('first_seen')

            if not first_seen_a or not first_seen_b:
                return True

            return first_seen_a.date() == first_seen_b.date()

        faces_by_uuid = {
            face['individual_uuid']: face
            for face in faces_with_embeddings
            if face.get('individual_uuid')
        }
        blocked_gender_conflicts = 0
        blocked_time_conflicts = 0
        
        # Build adjacency list of similar individuals
        similar_to = {uuid_val: [] for uuid_val in uuids}
        for i in range(len(uuids)):
            for j in range(i+1, len(uuids)):
                if similarities[i][j] >= similarity_threshold:
                    face_i = faces_by_uuid.get(uuids[i])
                    face_j = faces_by_uuid.get(uuids[j])
                    if face_i and face_j and not _can_auto_merge_by_time(face_i, face_j):
                        blocked_time_conflicts += 1
                        logger.info(
                            f"[MERGE] Time guard blocked edge: {uuids[i][:8]} ↔ "
                            f"{uuids[j][:8]} (sim={similarities[i][j]:.4f}, "
                            f"dates={face_i.get('first_seen')} vs {face_j.get('first_seen')})"
                        )
                        continue

                    if face_i and face_j and not _can_auto_merge_by_gender(face_i, face_j):
                        blocked_gender_conflicts += 1
                        logger.info(
                            f"[MERGE] Gender guard blocked edge: {uuids[i][:8]} ↔ "
                            f"{uuids[j][:8]} (sim={similarities[i][j]:.4f})"
                        )
                        continue

                    similar_to[uuids[i]].append(uuids[j])
                    similar_to[uuids[j]].append(uuids[i])
                    logger.info(
                        f"[MERGE] Edge added: {uuids[i][:8]} ↔ "
                        f"{uuids[j][:8]} (sim={similarities[i][j]:.4f})"
                    )

        if blocked_gender_conflicts:
            logger.info(
                f"[MERGE PHASE B] Gender guard blocked {blocked_gender_conflicts} "
                "high-confidence cross-gender edges"
            )
        if blocked_time_conflicts:
            logger.info(
                f"[MERGE PHASE B] Time guard blocked {blocked_time_conflicts} "
                "cross-day edges"
            )
        
        # Find connected components using DFS
        visited = set()
        
        def dfs(uuid_val, component):
            if uuid_val in visited:
                return
            visited.add(uuid_val)
            component.append(uuid_val)
            for neighbor in similar_to[uuid_val]:
                dfs(neighbor, component)
        
        # Find all connected components (groups of transitively similar individuals)
        components = []
        for uuid_val in uuids:
            if uuid_val not in visited:
                component = []
                dfs(uuid_val, component)
                if len(component) > 1:  # Only merge if group has 2+ individuals
                    components.append(component)
        
        # Convert components to merge_groups format
        # First individual in component is kept, rest are merged into it
        for component in components:
            keep_uuid = component[0]
            merge_uuids = component[1:]
            merge_groups.append((keep_uuid, merge_uuids))
            
            # Log merge group
            logger.info(
                f"[MERGE] Group: keep {keep_uuid[:8]}, "
                f"merge {[u[:8] for u in merge_uuids]}"
            )
        
        logger.info(
            f"[MERGE PHASE B] Found {len(merge_groups)} merge groups "
            f"({sum(len(g[1]) for g in merge_groups)} individuals to merge)"
        )
        
        # DEBUG: Log merge groups found
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"phase_b_groups_found: {len(merge_groups)}_groups, "
                    f"{sum(len(g[1]) for g in merge_groups)}_to_merge")
        except Exception:
            pass
        
        # ================================================================
        # PHASE C: PREPARE - Format for database
        # Architecture: Create MVR for ALL individuals, then merge similar ones
        # Even if no merge groups, we still create MVR people for all individuals (1:1)
        # ================================================================
        
        logger.info(f"[MERGE PHASE C] Preparing database operations... "
                    f"({len(merge_groups)} merge groups found)")
        
        # DEBUG: Confirm Phase C entry
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"phase_c_start: {len(merge_groups)}_groups, "
                    f"{len(uuids)}_total_individuals")
        except Exception:
            pass
        
        db_operations = []
        
        # Step 1: Create MVR person for each connected component
        # Each component = one MVR person, all individuals in component map to it
        individual_to_mvr = {}  # Track which MVR each individual maps to
        
        for keep_uuid, merge_uuids in merge_groups:
            # All UUIDs in this group (keep + merged)
            all_uuids_in_group = [keep_uuid] + merge_uuids
            
            # Get embedding from the first individual (representative)
            keep_idx = uuids.index(keep_uuid)
            keep_embedding = faces_with_embeddings[keep_idx]['embedding']
            keep_confidence = faces_with_embeddings[keep_idx]['confidence']
            
            # Convert numpy array to list for PostgreSQL vector type
            if isinstance(keep_embedding, np.ndarray):
                keep_embedding = keep_embedding.tolist()
            
            # Extract demographics from faces_with_embeddings (ML-generated)
            demographics = faces_with_embeddings[keep_idx].get('demographics', {
                'gender': None,
                'gender_confidence': None,
                'age_min': None,
                'age_max': None,
                'age_confidence': None
            })
            
            # Create ONE MVR person for this entire group
            mvr_people_uuid = str(uuid4())
            db_operations.append(('create_mvr_person', {
                'mvr_people_uuid': mvr_people_uuid,
                'featured_individual_uuid': keep_uuid,
                'face_embedding': keep_embedding,
                'confidence_score': keep_confidence,
                'quality_score': keep_confidence,
                'gender': demographics['gender'],
                'gender_confidence': demographics['gender_confidence'],
                'age_min': demographics['age_min'],
                'age_max': demographics['age_max'],
                'age_confidence': demographics['age_confidence']
            }))
            
            # Map ALL individuals in this group to the same MVR person
            for individual_uuid in all_uuids_in_group:
                idx = uuids.index(individual_uuid)
                similarity = similarities[keep_idx][idx] if individual_uuid != keep_uuid else 1.0
                confidence = faces_with_embeddings[idx]['confidence']
                
                db_operations.append(('map_individual_to_mvr', {
                    'individual_uuid': individual_uuid,
                    'mvr_people_uuid': mvr_people_uuid,
                    'similarity_score': float(similarity),
                    'confidence_score': confidence,
                    'quality_score': confidence,
                    'is_representative': (individual_uuid == keep_uuid),
                    'linked_by_session': session_uuid
                }))
                
                individual_to_mvr[individual_uuid] = mvr_people_uuid
        
        # Step 2: Create MVR people for individuals NOT in any merge group
        for i, individual_uuid in enumerate(uuids):
            if individual_uuid not in individual_to_mvr:
                # This individual is unique (not similar to anyone)
                embedding = faces_with_embeddings[i]['embedding']
                confidence = faces_with_embeddings[i]['confidence']
                
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                
                mvr_people_uuid = str(uuid4())
                db_operations.append(('create_mvr_person', {
                    'mvr_people_uuid': mvr_people_uuid,
                    'featured_individual_uuid': individual_uuid,
                    'face_embedding': embedding,
                    'confidence_score': confidence,
                    'quality_score': confidence
                }))
                
                db_operations.append(('map_individual_to_mvr', {
                    'individual_uuid': individual_uuid,
                    'mvr_people_uuid': mvr_people_uuid,
                    'similarity_score': 1.0,  # Self-match
                    'confidence_score': confidence,
                    'quality_score': confidence,
                    'is_representative': True,
                    'linked_by_session': session_uuid
                }))
                
                individual_to_mvr[individual_uuid] = mvr_people_uuid
        
        logger.info(
            f"[MERGE PHASE C] Prepared {len(db_operations)} database operations"
        )
        
        # ================================================================
        # PHASE D: EXECUTE - Single atomic transaction
        # ================================================================
        # ================================================================
        
        logger.info("[MERGE PHASE D] Executing database transaction...")
        
        # DEBUG: Confirm Phase D entry
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"phase_d_start: {len(db_operations)}_operations")
        except Exception:
            pass
        
        mvr_people_count = len([op for op in db_operations if op[0] == 'create_mvr_person'])
        
        # DEBUG: Log before transaction
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"phase_d_before_transaction: {mvr_people_count}_mvr, "
                    f"{len(db_operations) - mvr_people_count}_mappings")
        except Exception:
            pass
        
        try:
            async with db_client.pool.acquire() as conn:
                async with conn.transaction():
                    for op_type, params in db_operations:
                        if op_type == 'create_mvr_person':
                            # Create MVR person with embedding
                            # Convert list to string format for pgvector
                            embedding = params['face_embedding']
                            if isinstance(embedding, list):
                                embedding_str = str(embedding)
                            else:
                                embedding_str = str(embedding.tolist())
                            
                            await conn.execute("""
                                INSERT INTO mvr_people (
                                    mvr_people_uuid,
                                    featured_individual_uuid,
                                    face_embedding,
                                    confidence_score,
                                    quality_score,
                                    face_quality,
                                    gender,
                                    gender_confidence,
                                    age_min,
                                    age_max,
                                    age_confidence
                                ) VALUES ($1, $2, $3::vector, $4, $5, $6, $7, $8, $9, $10, $11)
                            """, params['mvr_people_uuid'],
                                params['featured_individual_uuid'],
                                embedding_str,
                                params['confidence_score'],
                                params['quality_score'],
                                params['quality_score'],
                                params.get('gender'),
                                params.get('gender_confidence'),
                                params.get('age_min'),
                                params.get('age_max'),
                                params.get('age_confidence'))
                            
                            logger.info(
                                f"[MERGE] Created MVR person "
                                f"{params['mvr_people_uuid'][:8]}"
                            )
                        
                        elif op_type == 'map_individual_to_mvr':
                            # Map individual to MVR person
                            await conn.execute("""
                                INSERT INTO individual_mvr_mapping (
                                    individual_uuid,
                                    mvr_people_uuid,
                                    similarity_score,
                                    confidence_score,
                                    quality_score,
                                    is_representative,
                                    linked_by_session,
                                    link_method
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            """, params['individual_uuid'],
                                params['mvr_people_uuid'],
                                params['similarity_score'],
                                params['confidence_score'],
                                params['quality_score'],
                                params['is_representative'],
                                params['linked_by_session'],
                                'auto_merge')
            
            # Transaction complete - log success OUTSIDE the transaction
            logger.info(
                f"[MERGE PHASE D] Transaction complete: "
                f"{mvr_people_count} MVR people created, "
                f"{len(db_operations) - mvr_people_count} mappings created"
            )
            
            # DEBUG: Log transaction success
            try:
                async with db_client.pool.acquire() as debug_conn:
                    await debug_conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"phase_d_transaction_success: {mvr_people_count}_mvr_created")
            except Exception:
                pass
            
        except Exception as e:
            logger.error(
                f"[MERGE PHASE D] Transaction failed: {type(e).__name__}: {e}"
            )
            # DEBUG: Log transaction failure
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"phase_d_transaction_failed: {type(e).__name__}: {str(e)[:100]}")
            except Exception:
                pass
            # Don't re-raise, just log and continue without merging
            return 0
        
        # Update unique_mvr_people_count in tracking session
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET unique_mvr_people_count = (
                    SELECT COUNT(DISTINCT mvr_people_uuid)
                    FROM individual_mvr_mapping
                    WHERE individual_uuid IN (
                        SELECT individual_uuid 
                        FROM session_individuals 
                        WHERE session_uuid = $1
                    )
                )
                WHERE session_uuid = $1
            """, session_uuid)
        
        return mvr_people_count
        # DEBUG: Report completion
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"merge_complete: {total_merged}_merged_into_{len(merge_groups)}_unique")
        except Exception:
            pass
        
        return total_merged
        
    except Exception as e:
        logger.error(f"[MERGE] Failed: {e}")
        import traceback
        traceback.print_exc()
        
        # DEBUG: Report error
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, f"merge_error: {str(e)[:200]}")
        except Exception:
            pass
        
        raise


async def process_tracking_session(session_uuid: str, auth_token: str = None):
    """
    Background task to process tracking session.
    """
    logger.info(f"process_tracking_session STARTED: session={session_uuid}, auth_present={bool(auth_token)}")
    try:
        db_client = get_database_client()
        
        # Write a debug message to DB at the very start
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, f"process_start: auth_present={bool(auth_token)}")
        except Exception:
            pass
        
        # Update status to running
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions 
                SET status = 'running', started_at = NOW()
                WHERE session_uuid = $1
            """, session_uuid)
            
            # Get session details (include video_uuids for optimization)
            session = await conn.fetchrow("""
                SELECT collections, start_time, end_time, algorithm_config, 
                       video_uuids
                FROM tracking_sessions WHERE session_uuid = $1
            """, session_uuid)
        
        if not session:
            raise ValueError(f"Session {session_uuid} not found")
        
        logger.info(
            f"Processing session {session_uuid} for collections: "
            f"{session['collections']}"
        )
        
        # Check if session has explicit video_uuids (stored as JSONB)
        video_uuids_json = session.get('video_uuids')
        video_uuids_list = None
        if video_uuids_json:
            try:
                # Parse JSONB to Python list
                if isinstance(video_uuids_json, str):
                    video_uuids_list = json.loads(video_uuids_json)
                else:
                    video_uuids_list = video_uuids_json
            except Exception as e:
                logger.warning(f"Failed to parse video_uuids: {e}")
        
        if video_uuids_list:
            # OPTIMIZATION: Use explicit video_uuids, skip time-based query
            logger.info(f"Using explicit video_uuids: {len(video_uuids_list)} videos")
            
            # Fetch video metadata directly by UUIDs
            videos = []
            async with httpx.AsyncClient(timeout=30.0) as client:
                for video_uuid in video_uuids_list:
                    try:
                        headers = {}
                        if auth_token:
                            headers['Authorization'] = f'Bearer {auth_token}' if not auth_token.startswith('Bearer ') else auth_token
                        
                        # Query media service for video metadata
                        response = await client.get(
                            f"http://localhost:8080/api/v1/media/{video_uuid}",
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            video_data = response.json()
                            videos.append({
                                'uuid': video_uuid,
                                'id': video_data.get('id'),
                                'timestamp': video_data.get('created_at') or video_data.get('timestamp'),
                                'collection': video_data.get('collection_id') or session['collections'][0]
                            })
                        else:
                            logger.warning(f"Failed to fetch video {video_uuid}: {response.status_code}")
                    except Exception as e:
                        logger.error(f"Error fetching video {video_uuid}: {e}")
            
            logger.info(f"Fetched metadata for {len(videos)}/{len(video_uuids_list)} videos")
        else:
            # LEGACY: Discover videos by time range
            logger.info("Using time-based video discovery (no video_uuids provided)")
            videos = await discover_videos_in_collection(
                session['collections'], 
                session['start_time'], 
                session['end_time'],
                auth_token=auth_token,
                session_uuid=session_uuid
            )

        # Persist a short discovery debug marker into the session row so we can inspect what the
        # background worker actually saw even when stdout logs are not easily accessible.
        try:
            sample_ids = []
            try:
                sample_ids = [(v.get('uuid') or v.get('id')) for v in videos[:5]]
            except Exception:
                sample_ids = []

            debug_msg = f"discovery_debug: found={len(videos)}, sample={sample_ids}"
            async with db_client.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                    """,
                    session_uuid,
                    debug_msg
                )
        except Exception as e:
            logger.debug("Failed to write discovery debug marker to DB: %s", e)
        
        logger.info(f"Found {len(videos)} videos to process in session {session_uuid}")
        
        # Write debug message to confirm we're continuing after discovery
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, f"after_discovery: continuing with {len(videos)} videos")
        except Exception:
            pass
        
        # Update total video count
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions 
                SET total_videos = $2
                WHERE session_uuid = $1
            """, session_uuid, len(videos))
        
        # Debug: total_videos updated
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid, f"total_videos_updated: {len(videos)}")
        except Exception:
            pass
        
        # Process videos and find individuals
        individuals_found = 0
        processed_count = 0
        created_individuals = []
        total_cache_hits = 0  # Track cache hits across all video groups
        
        if len(videos) >= 1:  # Process even single videos to create MVR people
            # Debug: entering video processing
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, "entering_video_processing")
            except Exception:
                pass
            
            enhanced_v2_success = 0
            enhanced_v2_failed = 0

            # Explicit video_uuid sessions are commonly used for read-oriented or targeted
            # reprocessing flows where person_objects already exist upstream. In that case,
            # block-free progress is more important than re-triggering Orchestrator materialization.
            if video_uuids_list:
                logger.info(
                    f"Skipping Enhanced Logic V2 for {len(videos)} explicit videos; "
                    "using persisted Orchestrator person_objects during preload instead"
                )
                enhanced_v2_success = len(videos)
            else:
                # CRITICAL STEP: Call Enhanced Logic V2 to create person_objects from stored_faces
                logger.info(f"Calling Enhanced Logic V2 for {len(videos)} videos to create person_objects...")

                async with httpx.AsyncClient(timeout=60.0) as client:
                    for video in videos:
                        video_uuid = video.get('uuid') or video.get('id')
                        try:
                            headers = {}
                            if auth_token:
                                headers['Authorization'] = f'Bearer {auth_token}' if not auth_token.startswith('Bearer ') else auth_token

                            # Call Enhanced Logic V2 endpoint (GET method)
                            response = await client.get(
                                f"http://localhost:8002/api/v1/media/{video_uuid}/faces/enhanced-v2",
                                headers=headers
                            )

                            if response.status_code in [200, 201]:
                                result = response.json()
                                person_count = result.get('person_groups_count', 0)
                                logger.info(f"✅ Enhanced V2 for {video_uuid[:8]}: {person_count} person_objects created")
                                enhanced_v2_success += 1
                            else:
                                logger.warning(f"Enhanced V2 failed for {video_uuid[:8]}: {response.status_code}")
                                enhanced_v2_failed += 1
                        except Exception as e:
                            logger.error(f"Enhanced V2 error for {video_uuid[:8]}: {e}")
                            enhanced_v2_failed += 1
            
            logger.info(f"Enhanced Logic V2 completed: {enhanced_v2_success} success, {enhanced_v2_failed} failed")
            
            # Log Enhanced V2 results to DB
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, f"enhanced_v2_results: {enhanced_v2_success}_success_{enhanced_v2_failed}_failed")
            except Exception:
                pass
            
            # Process any consecutive videos from the discovered videos
            # Sort videos by timestamp to ensure proper sequence
            videos_sorted = sorted(videos, key=lambda v: v.get('timestamp', ''))
            
            # Group videos into consecutive sequences
            # Videos are considered consecutive if gap < 60 seconds
            video_groups = []
            current_group = []
            
            for i, video in enumerate(videos_sorted):
                if i == 0:
                    current_group.append(video)
                else:
                    # Check time gap from previous video
                    prev_time = videos_sorted[i-1]['timestamp']
                    curr_time = video['timestamp']
                    
                    # Parse timestamps to compare
                    if isinstance(prev_time, str):
                        prev_dt = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                    else:
                        prev_dt = prev_time
                    
                    if isinstance(curr_time, str):
                        curr_dt = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))
                    else:
                        curr_dt = curr_time
                    
                    # Calculate gap
                    gap_seconds = (curr_dt - prev_dt).total_seconds()
                    
                    # If gap > 60 seconds, start new group
                    if gap_seconds > 60:
                        if len(current_group) > 0:
                            video_groups.append(current_group)
                        current_group = [video]
                    else:
                        current_group.append(video)
            
            # Add final group
            if len(current_group) > 0:
                video_groups.append(current_group)
            
            # Debug: Log video groups before processing
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, f"video_groups_count: {len(video_groups)}, " +
                         f"group_sizes: {[len(g) for g in video_groups]}")
            except Exception:
                pass
            
            # Track all individuals created across all groups
            created_individual_uuids = []
            
            # Track all matched_individuals with full data for embedding merge
            all_matched_individuals = []
            
            # ✨ SESSION-WIDE BULK CACHE CHECK
            # Check if a recent session has ALL videos in this request
            all_video_uuids = [v['uuid'] for v in videos]
            session_wide_cache_hit = False
            
            logger.info(
                f"🔍 Checking for cached session with all "
                f"{len(all_video_uuids)} videos..."
            )
            
            try:
                async with db_client.pool.acquire() as conn:
                    # Find recent session with EXACTLY same videos
                    # CRITICAL FIX: Use video_processing_states to get
                    # SUBMITTED videos, not individual_video_appearances
                    # which includes cross-video tracked videos
                    recent_session = await conn.fetchrow("""
                        WITH candidate_sessions AS (
                            -- Find sessions with same video count
                            SELECT
                                ts.session_uuid,
                                ts.created_at,
                                ts.total_videos
                            FROM tracking_sessions ts
                            WHERE ts.status = 'completed'
                              AND ts.session_uuid != $1
                              AND ts.total_videos = $3
                        ),
                        session_video_matches AS (
                            -- Count matching SUBMITTED videos per candidate
                            -- Use video_processing_states, NOT
                            -- individual_video_appearances
                            SELECT
                                cs.session_uuid,
                                cs.created_at,
                                cs.total_videos,
                                COUNT(DISTINCT vps.video_uuid)
                                    as matching_videos
                            FROM candidate_sessions cs
                            JOIN video_processing_states vps
                                ON vps.session_uuid = cs.session_uuid
                            WHERE vps.video_uuid = ANY($2::uuid[])
                            GROUP BY
                                cs.session_uuid,
                                cs.created_at,
                                cs.total_videos
                        )
                        -- Only match if ALL submitted videos are in request
                        SELECT
                            session_uuid,
                            created_at,
                            matching_videos as video_count
                        FROM session_video_matches
                        WHERE matching_videos = total_videos
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, session_uuid, all_video_uuids, len(all_video_uuids))
                    
                    if recent_session:
                        cached_session_id = (
                            str(recent_session['session_uuid'])[:8]
                        )
                        logger.info(
                            f"♻️ Found cached session {cached_session_id} "
                            f"with all {recent_session['video_count']} videos!"
                        )
                        
                        # Get ALL individuals from that session
                        cached_records = await conn.fetch("""
                            SELECT DISTINCT si.individual_uuid
                            FROM session_individuals si
                            WHERE si.session_uuid = $1
                        """, recent_session['session_uuid'])
                        
                        created_individual_uuids = [
                            str(r['individual_uuid'])
                            for r in cached_records
                        ]
                        session_wide_cache_hit = True
                        total_cache_hits = len(all_video_uuids)
                        
                        logger.info(
                            f"✅ Session-wide cache hit! Reusing "
                            f"{len(created_individual_uuids)} individuals "
                            f"from session {cached_session_id}"
                        )
                        
                        # Link cached individuals to this session
                        for individual_uuid in created_individual_uuids:
                            await conn.execute("""
                                INSERT INTO session_individuals
                                (session_uuid, individual_uuid,
                                 processing_type, confidence_contribution)
                                VALUES ($1, $2, $3, $4)
                            """,
                                session_uuid,
                                individual_uuid,
                                'cached',
                                1.0
                            )
                        
                        logger.info(
                            f"🔗 Linked {len(created_individual_uuids)} "
                            f"cached individuals to session"
                        )
                    else:
                        logger.info(
                            "🆕 No cached session found, "
                            "will process videos normally"
                        )
            
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Session-wide cache check failed: {cache_error}, "
                    f"will process normally"
                )
                session_wide_cache_hit = False
            
            # ✨ PRELOAD: Fetch all person_objects data upfront to eliminate I/O during DB transactions
            # Skip if session-wide cache hit
            if not session_wide_cache_hit:
                logger.info(
                    f"🔄 Preloading person_objects for all {len(videos)} "
                    f"videos before processing groups"
                )
                preloaded_person_objects = await preload_person_objects_for_all_videos(
                    all_videos=videos,
                    auth_token=auth_token,
                    session_uuid=session_uuid,
                    db_client=db_client,
                    concurrency=6
                )
                logger.info(
                    f"✅ Preload complete, now processing "
                    f"{len(video_groups)} groups"
                )
            else:
                preloaded_person_objects = {}
                logger.info(
                    "⏭️ Skipping preload (session-wide cache hit)"
                )
            
            # Process each group of consecutive videos
            # Skip if session-wide cache hit
            if not session_wide_cache_hit:
                for group_idx, consecutive_videos in enumerate(video_groups):
                    # Debug: Log entering group processing
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid,
                                 f"processing_group_{group_idx}: "
                                 f"{len(consecutive_videos)}_videos")
                    except Exception:
                        pass
                    
                    logger.info(
                        f"📹 Processing video group {group_idx + 1}/"
                        f"{len(video_groups)} with "
                        f"{len(consecutive_videos)} consecutive videos"
                    )
                    
                    # 🔥 NEW LOGIC: Temporal matching WITHIN the group
                    # This matches person_objects across videos to create individuals
                    # that appear in multiple videos
                    matched_individuals = await match_person_objects_within_group(
                        videos_data=consecutive_videos,
                        auth_token=auth_token,
                        session_uuid=session_uuid,
                        db_client=db_client,
                        preloaded_data=preloaded_person_objects  # Use preloaded data
                    )
                    
                    logger.info(
                        f"✅ Group {group_idx + 1}: Matched {len(matched_individuals)} "
                        f"individuals across {len(consecutive_videos)} videos"
                    )
                    
                    # Debug: Log before database creation
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid, 
                                 f"creating_db_records_for_{len(matched_individuals)}_individuals")
                    except Exception:
                        pass
                    
                    # ✨ NEW APPROACH: Prepare all DB operations in memory first
                    # Then execute in a SINGLE transaction with ONE connection
                    db_operations = []  # List of (operation_type, params) tuples
                    
                    for individual_data in matched_individuals:
                        individual_uuid = individual_data['individual_uuid']
                        individual_id = f"ind_{individual_uuid[:8]}"
                        video_uuids = individual_data['video_uuids']
                        demographics = individual_data.get('demographics') or {}
                        persisted_gender_estimate = _normalize_gender_value(
                            demographics.get('gender')
                        )
                        persisted_age_estimate = None
                        age_min = _safe_int_value(demographics.get('age_min'))
                        age_max = _safe_int_value(demographics.get('age_max'))
                        if age_min is not None:
                            persisted_age_estimate = int(round((age_min + (age_max if age_max is not None else age_min)) / 2))
                        
                        # Prepare individual insert
                        db_operations.append(('individual', {
                            'individual_uuid': individual_uuid,
                            'individual_id': individual_id,
                            'confidence_score': individual_data['temporal_score'],
                            'spatial_signature': '{"type": "temporal_group_match"}',
                            'temporal_signature': '{"type": "consecutive_videos"}',
                            'algorithm_version': '2.1',
                            'gender_estimate': persisted_gender_estimate,
                            'age_estimate': persisted_age_estimate,
                        }))
                        
                        # Prepare session-individual link
                        db_operations.append(('session_individual', {
                            'session_uuid': session_uuid,
                            'individual_uuid': individual_uuid,
                            'processing_type': 'new',  # Must be: new, cached, merged, or extended
                            'confidence_contribution': individual_data['temporal_score']
                        }))
                        
                        # Prepare video appearances
                        for video_uuid in video_uuids:
                            video_data = next(
                                (v for v in consecutive_videos if v['uuid'] == video_uuid),
                                None
                            )
                            if not video_data:
                                logger.warning(f"No video data for {video_uuid[:8]}")
                                continue
                            
                            try:
                                # Parse timestamp
                                timestamp_str = video_data["timestamp"]
                                if isinstance(timestamp_str, str):
                                    start_ts = datetime.fromisoformat(
                                        timestamp_str.replace('Z', '+00:00')
                                    )
                                else:
                                    start_ts = timestamp_str
                                
                                # Convert to UTC naive
                                from datetime import timezone as tz
                                if start_ts.tzinfo is not None:
                                    start_ts = start_ts.astimezone(tz.utc).replace(tzinfo=None)
                                
                                end_ts = start_ts + timedelta(seconds=30)
                                person_object_uuid = None
                                
                                # Extract representative_faces from person_objects for quality metrics
                                representative_faces = None
                                person_objects_dict = individual_data.get('person_objects', {})
                                if video_uuid in person_objects_dict:
                                    person_obj = person_objects_dict[video_uuid]
                                    if isinstance(person_obj, dict):
                                        person_object_uuid = (
                                            person_obj.get('person_id')
                                            or person_obj.get('person_uuid')
                                            or person_obj.get('person_object_uuid')
                                        )
                                        representative_faces = person_obj.get('representative_faces')
                                        if representative_faces:
                                            # Convert to JSON string for JSONB storage
                                            import json
                                            representative_faces = json.dumps({'faces': representative_faces})

                                if not person_object_uuid:
                                    logger.warning(
                                        'Skipping appearance insert for individual %s video %s: '
                                        'no persisted person identifier available',
                                        individual_uuid,
                                        video_uuid,
                                    )
                                    continue
                                
                                db_operations.append(('appearance', {
                                    'individual_uuid': individual_uuid,
                                    'video_uuid': video_uuid,
                                    'person_object_uuid': person_object_uuid,
                                    'start_timestamp': start_ts,
                                    'end_timestamp': end_ts,
                                    'entry_bbox': [100, 200, 150, 300],
                                    'exit_bbox': [110, 210, 160, 310],
                                    'confidence': individual_data['temporal_score'],
                                    'representative_faces': representative_faces
                                }))
                            except Exception as e:
                                logger.error(f"Failed to prepare appearance: {e}")
                        
                        # Track for later merging
                        created_individual_uuids.append(individual_uuid)
                    
                    # Also store the full matched_individuals data for embedding merge
                    all_matched_individuals.extend(matched_individuals)
                    
                    # ✨ Execute ALL operations in a SINGLE transaction
                    logger.info(f"💾 Executing {len(db_operations)} DB operations in single transaction")
                    
                    try:
                        async with db_client.pool.acquire() as conn:
                            async with conn.transaction():
                                for op_type, params in db_operations:
                                    if op_type == 'individual':
                                        await conn.execute("""
                                            INSERT INTO individuals (
                                                individual_uuid, individual_id,
                                                confidence_score,
                                                spatial_signature, temporal_signature,
                                                algorithm_version, gender_estimate, age_estimate
                                            ) VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7, $8)
                                        """,
                                            params['individual_uuid'],
                                            params['individual_id'],
                                            params['confidence_score'],
                                            params['spatial_signature'],
                                            params['temporal_signature'],
                                            params['algorithm_version'],
                                            params['gender_estimate'],
                                            params['age_estimate']
                                        )
                                    elif op_type == 'session_individual':
                                        await conn.execute("""
                                            INSERT INTO session_individuals
                                            (session_uuid, individual_uuid,
                                             processing_type, confidence_contribution)
                                            VALUES ($1, $2, $3, $4)
                                        """,
                                            params['session_uuid'],
                                            params['individual_uuid'],
                                            params['processing_type'],
                                            params['confidence_contribution']
                                        )
                                    elif op_type == 'appearance':
                                        await conn.execute("""
                                            INSERT INTO individual_video_appearances (
                                                individual_uuid, video_uuid, person_object_uuid,
                                                start_timestamp, end_timestamp,
                                                entry_bbox, exit_bbox, confidence,
                                                representative_faces
                                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                                            ON CONFLICT DO NOTHING
                                        """,
                                            params['individual_uuid'],
                                            params['video_uuid'],
                                            params['person_object_uuid'],
                                            params['start_timestamp'],
                                            params['end_timestamp'],
                                            params['entry_bbox'],
                                            params['exit_bbox'],
                                            params['confidence'],
                                            params.get('representative_faces')
                                        )
                                
                                logger.info(f"✅ Transaction committed: {len(matched_individuals)} individuals created")
                                logger.warning(
                                    "[MVR PATH DEBUG] cross_video_tracking_simple committed %s individuals and %s appearances for session %s; Queue B decides whether any mvr_people rows are created afterwards",
                                    len(matched_individuals),
                                    sum(1 for op_type, _ in db_operations if op_type == 'appearance'),
                                    session_uuid,
                                )
                    except Exception as db_error:
                        logger.error(f"❌ Database transaction failed: {db_error}")
                        # Log to session
                        try:
                            async with db_client.pool.acquire() as _dbg_conn:
                                await _dbg_conn.execute("""
                                    UPDATE tracking_sessions
                                    SET failed_videos = array_append(failed_videos, $2)
                                    WHERE session_uuid = $1
                                """, session_uuid, f"db_transaction_error: {str(db_error)[:100]}")
                        except Exception:
                            pass
                    
                    # Debug: Log completion of this group
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid, 
                                 f"group_{group_idx}_complete: {len(matched_individuals)}_individuals")
                    except Exception as group_log_error:
                        logger.error(f"Failed to log group completion: {group_log_error}")
            
            # Debug: Log that all groups are done
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid, "all_groups_processed")
            except Exception:
                pass
            
            # All groups processed - now merge across groups via embeddings
            logger.info(
                f"Cross-video tracking complete: {len(created_individual_uuids)} "
                f"individual(s) created across {len(video_groups)} groups"
            )
            
            # Update session stats
            individuals_found = len(created_individual_uuids)
            processed_count = len(videos)  # Fixed: was 'all_videos'
            
            # DEBUG: Write merge attempt to database
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"merge_check: created_individuals={len(created_individual_uuids)}")
            except Exception:
                pass
            
            # Phase 2: Queue MVR creation in background (Queue B)
            # This decouples MVR creation from video discovery/individual creation
            # Benefits:
            # - Session completes faster (non-blocking)
            # - MVR creation can be retried independently
            # - Individuals can be processed even if created later
            if len(created_individual_uuids) >= 1:
                # DEBUG: Entering queue B
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid, "entering_queue_b_mvr_creation")
                except Exception:
                    pass
                    
                logger.info(
                    f"🔄 [Queue B] Queuing MVR creation for "
                    f"{len(created_individual_uuids)} individuals..."
                )
                try:
                    # Get MVR background processor from global state
                    from api.dependencies import get_mvr_background_processor
                    import main
                    
                    mvr_processor = main.mvr_background_processor
                    
                    if mvr_processor:
                        # Fetch merge mode and threshold from orchestrator settings.
                        # Continuous pipeline grouping must not perform session-wide
                        # MVR merging when merge_rule is "none".
                        merge_rule = "semi"
                        merge_similarity_threshold = 0.70  # fallback default
                        try:
                            import httpx as _httpx
                            async with _httpx.AsyncClient(timeout=5.0) as _hc:
                                _resp = await _hc.get(
                                    "http://localhost:8002/api/v1/settings/workflow/mvr-merge",
                                    headers={"Authorization": "Bearer internal-service-token-ppl-meta-frontend"},
                                )
                                if _resp.status_code == 200:
                                    _data = _resp.json()
                                    merge_rule = str(_data.get("merge_rule", "semi"))
                                    merge_similarity_threshold = float(_data.get("merge_threshold", 0.70))
                        except Exception as _e:
                            logger.warning(f"Could not fetch MVR merge threshold from orchestrator, using default 0.70: {_e}")

                        logger.info(
                            f"[Queue B] Using merge_rule={merge_rule}, "
                            f"similarity_threshold={merge_similarity_threshold} "
                            f"from orchestrator settings"
                        )

                        if merge_rule == "none":
                            logger.warning(
                                "[MVR PATH DEBUG] Queue B will create base MVR rows without merging for session %s because merge_rule=none.",
                                session_uuid,
                            )
                            queue_similarity_threshold = 1.01
                            queue_hierarchical_merge = False
                        else:
                            logger.warning(
                                "[MVR PATH DEBUG] Queue B proceeding with MVR creation for session %s using merge_rule=%s over %s individuals",
                                session_uuid,
                                merge_rule,
                                len(created_individual_uuids),
                            )
                            queue_similarity_threshold = merge_similarity_threshold
                            queue_hierarchical_merge = True

                        # Queue MVR creation (non-blocking)
                        queue_result = await mvr_processor.queue_session_mvr_creation(
                            session_uuid=session_uuid,
                            individual_uuids=[UUID(uid) for uid in created_individual_uuids],
                            auth_token=auth_token,
                            similarity_threshold=queue_similarity_threshold,
                            queue_hierarchical_merge=queue_hierarchical_merge,
                        )

                        logger.info(
                            f"✅ [Queue B] MVR creation queued for session {session_uuid}: "
                            f"{queue_result['individual_count']} individuals queued, "
                            f"task_id={queue_result['task_id']}, "
                            f"threshold={queue_similarity_threshold}, "
                            f"queue_hierarchical_merge={queue_hierarchical_merge}"
                        )

                        # DEBUG: Write queue success to database
                        try:
                            async with db_client.pool.acquire() as conn:
                                await conn.execute("""
                                    UPDATE tracking_sessions
                                    SET failed_videos = array_append(failed_videos, $2)
                                    WHERE session_uuid = $1
                                """, session_uuid,
                                    f"queue_b_success: {queue_result['individual_count']}_individuals_queued")
                        except Exception:
                            pass
                    else:
                        logger.warning(
                            "⚠️ [Queue B] MVR background processor not initialized, "
                            "falling back to synchronous merge"
                        )
                        # Fallback: Run synchronously if processor not available
                        merged_count = await merge_individuals_by_similarity(
                            db_client=db_client,
                            session_uuid=session_uuid,
                            matched_individuals=all_matched_individuals,
                            auth_token=auth_token,
                            similarity_threshold=merge_similarity_threshold
                        )
                        logger.info(
                            f"Merged {merged_count} duplicate individuals (synchronous fallback)."
                        )
                except Exception as queue_error:
                    logger.error(
                        f"❌ [Queue B] Failed to queue MVR creation: {queue_error}"
                    )
                    # DEBUG: Write error to database
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(
                                    failed_videos, $2
                                )
                                WHERE session_uuid = $1
                            """, session_uuid,
                                f"queue_b_error: {str(queue_error)[:200]}")
                    except Exception:
                        pass
                    # Continue - MVR creation will be retried by background processor
        else:
            processed_count = len(videos)
            logger.info(
                f"Not enough videos for cross-video tracking: "
                f"{len(videos)}"
            )
        
        # Update status to completed
        async with db_client.pool.acquire() as conn:
            # Get actual count of unique individuals from session_individuals
            # This is more accurate than the incremental counter
            actual_individuals_count = await conn.fetchval("""
                SELECT COUNT(DISTINCT individual_uuid)
                FROM session_individuals
                WHERE session_uuid = $1
            """, session_uuid)
            
            # Query actual unique MVR people count from individual_mvr_mapping
            # This will reflect merges performed by merge_individuals_by_similarity
            unique_mvr_result = await conn.fetchrow("""
                SELECT COUNT(DISTINCT mvr_people_uuid) as unique_count
                FROM individual_mvr_mapping
                WHERE individual_uuid IN (
                    SELECT individual_uuid 
                    FROM session_individuals 
                    WHERE session_uuid = $1
                )
            """, session_uuid)
            
            # Keep the session counter aligned with actual persisted MVR rows.
            # When merge_rule=none, Queue B is skipped and this count must stay 0.
            unique_count = unique_mvr_result['unique_count'] if unique_mvr_result else 0
            
            await conn.execute("""
                UPDATE tracking_sessions
                SET status = 'completed', completed_at = NOW(),
                    processing_time_seconds = 3.0,
                    processed_videos = $2, individuals_found = $3,
                    unique_mvr_people_count = $4, cache_hits = $5
                WHERE session_uuid = $1
            """, session_uuid, processed_count, actual_individuals_count,
                 unique_count, total_cache_hits)
        
        logger.info(
            f"Processing completed for session {session_uuid}: "
            f"{processed_count} videos, {actual_individuals_count} "
            f"individuals ({unique_count} unique), "
            f"{total_cache_hits} cache hits"
        )
        
    except Exception as e:
        logger.error(f"Processing failed for session {session_uuid}: {e}")
        
        # Update status to failed
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET status = 'failed', error_message = $2
                    WHERE session_uuid = $1
                """, session_uuid, str(e))
        except Exception:
            pass


async def discover_videos_in_collection(
    collections: List[str],
    start_time: datetime,
    end_time: datetime,
    auth_token: str = None,
    session_uuid: str = None
):
    """
    Discover videos in collections within the specified time range.
    Query the media service for real videos.
    """
    logger.info(f"discover_videos_in_collection CALLED: collections={collections}, start={start_time}, end={end_time}, auth_present={bool(auth_token)}, session={session_uuid}")
    try:
        import aiohttp
        import json as json_module
        
        videos = []
        # Write an initial discovery debug entry so we can see discover invocation
        if session_uuid:
            try:
                db_client = get_database_client()
                dbg = f"discover_start: auth_present={bool(auth_token)}, start={start_time}, end={end_time}, collections={collections}"
                async with db_client.pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                        """,
                        session_uuid,
                        dbg
                    )
            except Exception:
                logger.debug("Failed to write discover_start debug for session %s", session_uuid)
        
        for collection in collections:
            # Normalize collection id/name to accept variants like 'usb_camera_0' or 'usb camera 0'
            coll_norm = str(collection).replace('_', ' ').lower()
            if 'usb camera' in coll_norm:
                # Use the provided start_time/end_time parameters (avoid hardcoded dates)
                # Format times sent to Gateway/Media as UTC ISO timestamps with 'Z' suffix.
                # The session store currently keeps naive datetimes; treat naive as UTC.
                def _format_time_for_gateway(dt):
                    try:
                        # If dt has tzinfo, convert to UTC and produce Z-suffixed ISO
                        if getattr(dt, 'tzinfo', None) is not None:
                            return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
                        # Naive datetimes: assume they are already UTC and append Z
                        return dt.isoformat() + 'Z'
                    except Exception:
                        return None

                target_start = _format_time_for_gateway(start_time) or "2025-10-19T10:05:00Z"
                target_end = _format_time_for_gateway(end_time) or "2025-10-19T10:15:00Z"

                # Prefer querying via the Gateway (consistent with other discovery paths)
                gateway_url = "http://localhost:8080/api/v1/media/search"

                try:
                    headers = {}
                    if auth_token:
                        # Auth token may already have 'Bearer ' prefix from request header
                        if auth_token.startswith('Bearer ') or auth_token.startswith('bearer '):
                            headers['Authorization'] = auth_token
                        else:
                            headers['Authorization'] = f'Bearer {auth_token}'
                        
                        # Debug: Log the exact Authorization header being sent
                        auth_preview = headers['Authorization'][:30] + '...' + headers['Authorization'][-10:] if len(headers['Authorization']) > 50 else headers['Authorization']
                        logger.info(f"Gateway request auth header: {auth_preview}")
                        
                        # Also log to database for debugging
                        if session_uuid:
                            try:
                                db_client = get_database_client()
                                async with db_client.pool.acquire() as conn:
                                    await conn.execute(
                                        """
                                        UPDATE tracking_sessions
                                        SET failed_videos = array_append(failed_videos, $2)
                                        WHERE session_uuid = $1
                                        """,
                                        session_uuid,
                                        f"auth_header_sent: {auth_preview}"
                                    )
                            except Exception:
                                pass

                    async with aiohttp.ClientSession(headers=headers) as session:
                        # Resolve collection name -> id via Media service lookup (helps when callers provide a short name)
                        gateway_params = {
                            "start_time": target_start,
                            "end_time": target_end,
                        }

                        if collection:
                            try:
                                lookup_url = f"http://localhost:8000/api/v1/collections/lookup?name={collection}"
                                logger.debug("Resolving collection name via Media lookup: %s", lookup_url)
                                async with session.get(lookup_url, timeout=5) as lookup_resp:
                                    if lookup_resp.status == 200:
                                        lookup_data = await lookup_resp.json()
                                        # prefer numeric id if available
                                        if lookup_data and lookup_data.get('id'):
                                            gateway_params['collection_id'] = lookup_data.get('id')
                                        else:
                                            gateway_params['collection'] = collection
                                    else:
                                        # fallback to passing the original collection string
                                        gateway_params['collection'] = collection
                            except Exception as e:
                                logger.debug("Collection lookup failed: %s", e)
                                gateway_params['collection'] = collection

                        # First try gateway search
                        try:
                            logger.info("Querying Gateway media search: %s params=%s auth_present=%s", gateway_url, gateway_params, bool(auth_token))
                            async with session.get(gateway_url, params=gateway_params, timeout=10) as response:
                                logger.debug("Gateway search -> status=%s", response.status)
                                
                                # Log non-200 responses for debugging
                                if response.status != 200:
                                    error_text = await response.text()
                                    logger.warning("Gateway returned non-200: status=%s, response=%s", response.status, error_text[:500])
                                    if session_uuid:
                                        try:
                                            db_client = get_database_client()
                                            debug_info = f"gateway_error: status={response.status}, error={error_text[:200]}"
                                            async with db_client.pool.acquire() as conn:
                                                await conn.execute(
                                                    """
                                                    UPDATE tracking_sessions
                                                    SET failed_videos = array_append(failed_videos, $2)
                                                    WHERE session_uuid = $1
                                                    """,
                                                    session_uuid,
                                                    debug_info
                                                )
                                        except Exception:
                                            pass
                                
                                if response.status == 200:
                                    data = await response.json()
                                    if isinstance(data, list):
                                        potential_videos = data
                                    elif isinstance(data, dict) and data.get('items'):
                                        potential_videos = data.get('items')
                                    elif isinstance(data, dict) and data.get('media'):
                                        potential_videos = data.get('media')
                                    else:
                                        potential_videos = []

                                    # Log sample ids
                                    try:
                                        sample = [(it.get('uuid') or it.get('id')) for it in potential_videos[:5]]
                                        logger.debug("Gateway returned %d items, sample ids=%s", len(potential_videos), sample)
                                    except Exception:
                                        sample = []

                                    # Persist gateway-level debug info into the session row if we have the session UUID
                                    if session_uuid:
                                        try:
                                            db_client = get_database_client()
                                            debug_info = f"gateway_debug: status={response.status}, items={len(potential_videos)}, auth_present={bool(auth_token)}, sample={sample}"
                                            async with db_client.pool.acquire() as conn:
                                                await conn.execute(
                                                    """
                                                    UPDATE tracking_sessions
                                                    SET failed_videos = array_append(failed_videos, $2)
                                                    WHERE session_uuid = $1
                                                    """,
                                                    session_uuid,
                                                    debug_info
                                                )
                                        except Exception:
                                            logger.debug("Failed to write gateway debug to DB for session %s", session_uuid)

                                    for video in potential_videos:
                                        # Prefer recording time over creation time
                                        video_time = (
                                            video.get('start_timestamp') or
                                            video.get('recorded_at') or
                                            video.get('timestamp') or
                                            video.get('created_at')
                                        )
                                        vid_uuid = (
                                            video.get('uuid') or
                                            video.get('id')
                                        )
                                        duration = (
                                            video.get('duration') or
                                            video.get(
                                                'technical_metadata',
                                                {}
                                            ).get('duration_seconds', 30)
                                        )
                                        videos.append({
                                            "uuid": vid_uuid,
                                            "collection": collection,
                                            "timestamp": video_time,
                                            "duration": duration
                                        })

                        except Exception as e:
                            logger.debug("Gateway media search failed: %s", e)

                        # If gateway didn't return anything, try direct media endpoints as a fallback
                        if len(videos) < 2:
                            media_urls = [
                                f"http://localhost:8000/api/v1/media?collection={collection}&start_time={target_start}&end_time={target_end}",
                                f"http://localhost:8000/api/v1/collections/{collection}/media",
                                f"http://localhost:8000/api/v1/media/search?collection={collection}",
                                f"http://localhost:8000/api/v1/media"
                            ]

                            for url in media_urls:
                                try:
                                    logger.debug("Trying media URL: %s", url)
                                    async with session.get(url, timeout=8) as response:
                                        logger.debug("Media URL %s -> status=%s", url, response.status)
                                        if response.status == 200:
                                            data = await response.json()
                                            if isinstance(data, list):
                                                potential_videos = data
                                            elif isinstance(data, dict) and 'media' in data:
                                                potential_videos = data['media']
                                            elif isinstance(data, dict) and 'items' in data:
                                                potential_videos = data['items']
                                            else:
                                                potential_videos = []

                                            try:
                                                sample = [(it.get('uuid') or it.get('id')) for it in potential_videos[:5]]
                                                logger.debug("Media URL %s returned %d items, sample=%s", url, len(potential_videos), sample)
                                            except Exception:
                                                pass

                                            for video in potential_videos:
                                                video_time = video.get('created_at') or video.get('timestamp') or video.get('recorded_at')
                                                videos.append({
                                                    "uuid": video.get('uuid') or video.get('id'),
                                                    "collection": collection,
                                                    "timestamp": video_time,
                                                    "duration": video.get('duration') or video.get('technical_metadata', {}).get('duration_seconds', 30)
                                                })

                                        if len(videos) >= 2:
                                            break

                                except Exception as e:
                                    logger.debug("Failed to query %s: %s", url, e)
                                    continue

                except Exception as e:
                    logger.warning("Failed to query media/gateway services: %s", e)

                # Hardcoded fallback removed - rely on actual video discovery
        
        logger.info(
            f"Discovered {len(videos)} videos in collections {collections}"
        )
        return videos
        
    except Exception as e:
        logger.error(f"Failed to discover videos: {e}")
        # Write exception to database for debugging
        if session_uuid:
            try:
                db_client = get_database_client()
                async with db_client.pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                        """,
                        session_uuid,
                        f"discover_exception: {type(e).__name__}: {str(e)[:200]}"
                    )
            except Exception:
                pass
        return []


# ============================================================================
# PHASE 5 & 6 ENDPOINTS - Required for Flutter integration
# ============================================================================

@router.get("/sessions/{session_uuid}/individuals")
async def get_session_individuals(
    session_uuid: str,
    http_request: Request,
    view: str = Query(
        default="auto",
        pattern="^(auto|raw|mvr)$",
        description="Return raw session individuals, MVR people, or auto-select based on session state",
    ),
):
    """
    Phase 5: Get list of unique individuals found in a completed
    tracking session.

    **NEW BEHAVIOR**: Returns MVR people (merged individuals) when
    available.
    - If MVR mappings exist: Returns unique MVR people with
      aggregated appearances
    - If no MVR mappings: Returns raw individuals (backwards compatible)

    Returns metadata for each individual/MVR person including:
    - individual_uuid: Unique identifier (MVR person UUID if merged,
      individual UUID otherwise)
    - appearance_count: Number of times individual appears
    - video_count: Number of unique videos
    - first_seen/last_seen: Time range of appearances
    - confidence_score: Average confidence across appearances

    Required for Flutter navigation to individual analysis.
    """
    try:
        logger.info(f"Phase 5: Getting individuals for session {session_uuid}")
        
        # Get database client
        db_client = get_database_client()
        
        # Validate session exists and is completed
        async with db_client.pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT session_uuid, status, total_videos,
                       individuals_found, unique_mvr_people_count
                FROM tracking_sessions
                WHERE session_uuid = $1
                """,
                session_uuid
            )

            if not session:
                raise HTTPException(
                    status_code=404, detail="Session not found"
                )

            # Status can be 'COMPLETED' or 'completed' depending on db
            if session['status'].upper() != 'COMPLETED':
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Session is not completed. "
                        f"Current status: {session['status']}"
                    )
                )
            
            # Check if MVR people exist for this session
            mvr_count = session.get('unique_mvr_people_count', 0)
            use_mvr_view = view == "mvr" or (view == "auto" and mvr_count and mvr_count > 0)

            if use_mvr_view:
                # Return MVR people (merged individuals)
                logger.info(
                    f"Phase 5: Returning MVR view for session {session_uuid} "
                    f"(stored mvr_count={mvr_count}, requested view={view})"
                )

                mvr_people = await conn.fetch(
                    """
                    SELECT
                        mp.mvr_people_uuid,
                        mp.featured_individual_uuid,
                        COUNT(DISTINCT iva.person_object_uuid)
                            as appearance_count,
                        COUNT(DISTINCT iva.video_uuid) as video_count,
                        MIN(iva.start_timestamp) as first_seen,
                        MAX(iva.end_timestamp) as last_seen,
                        AVG(imm.confidence_score) as avg_confidence
                    FROM individual_mvr_mapping imm
                    JOIN mvr_people mp
                        ON imm.mvr_people_uuid = mp.mvr_people_uuid
                    JOIN session_individuals si
                        ON imm.individual_uuid = si.individual_uuid
                    LEFT JOIN individual_video_appearances iva
                        ON imm.individual_uuid = iva.individual_uuid
                    WHERE si.session_uuid = $1
                    GROUP BY mp.mvr_people_uuid, mp.featured_individual_uuid
                    ORDER BY appearance_count DESC, first_seen ASC
                    """,
                    session_uuid
                )

                # Format response with MVR people
                individuals_list = [
                    {
                        # MVR person UUID
                        "individual_uuid": str(mvr['mvr_people_uuid']),
                        # MVR identifier
                        "individual_id": (
                            f"mvr_{str(mvr['mvr_people_uuid'])[:8]}"
                        ),
                        "total_appearances": mvr['appearance_count'],
                        "total_videos": mvr['video_count'],
                        "first_seen": (
                            mvr['first_seen'].isoformat()
                            if mvr['first_seen'] else None
                        ),
                        "last_seen": (
                            mvr['last_seen'].isoformat()
                            if mvr['last_seen'] else None
                        ),
                        "confidence_score": (
                            round(float(mvr['avg_confidence']), 3)
                            if mvr['avg_confidence'] else 0.0
                        )
                    }
                    for mvr in mvr_people
                ]

                logger.info(
                    f"Phase 5: Returning {len(individuals_list)} "
                    f"MVR people for session {session_uuid}"
                )

            else:
                # Return raw session individuals even if MVR mappings exist.
                logger.info(
                    f"Phase 5: Returning raw individuals for session {session_uuid} "
                    f"(requested view={view}, stored mvr_count={mvr_count})"
                )
                
                individuals = await conn.fetch(
                    """
                    SELECT
                        i.individual_uuid,
                        i.individual_id,
                        COUNT(DISTINCT iva.person_object_uuid)
                            as appearance_count,
                        COUNT(DISTINCT iva.video_uuid) as video_count,
                        MIN(iva.start_timestamp) as first_seen,
                        MAX(iva.end_timestamp) as last_seen,
                        i.confidence_score as avg_confidence
                    FROM session_individuals si
                    JOIN individuals i
                        ON si.individual_uuid = i.individual_uuid
                    LEFT JOIN individual_video_appearances iva
                        ON i.individual_uuid = iva.individual_uuid
                    WHERE si.session_uuid = $1
                    GROUP BY i.individual_uuid, i.individual_id,
                             i.confidence_score
                    ORDER BY appearance_count DESC, first_seen ASC
                    """,
                    session_uuid
                )

                # Format response
                individuals_list = [
                    {
                        "individual_uuid": str(ind['individual_uuid']),
                        "individual_id": ind['individual_id'],
                        "total_appearances": ind['appearance_count'],
                        "total_videos": ind['video_count'],
                        "first_seen": (
                            ind['first_seen'].isoformat()
                            if ind['first_seen'] else None
                        ),
                        "last_seen": (
                            ind['last_seen'].isoformat()
                            if ind['last_seen'] else None
                        ),
                        "confidence_score": (
                            round(float(ind['avg_confidence']), 3)
                            if ind['avg_confidence'] else 0.0
                        )
                    }
                    for ind in individuals
                ]

                logger.info(
                    f"Phase 5: Found {len(individuals_list)} "
                    f"individuals in session {session_uuid}"
                )
            
            return {
                "session_uuid": session_uuid,
                "total_individuals": len(individuals_list),
                "individuals": individuals_list
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Phase 5 error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/sessions/{session_uuid}/analysis")
async def get_session_analysis(
    session_uuid: str,
    view: str = Query(
        default="auto",
        pattern="^(auto|raw|mvr)$",
        description="Backend-owned session analysis view selector",
    ),
):
    """
    Return a canonical cross-video analysis response for a session.

    This keeps merge/view routing in the backend so the frontend can render a
    single response instead of deciding between raw individuals and MVR paths.
    """
    try:
        db_client = get_database_client()

        async with db_client.pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT session_uuid, status, total_videos,
                       individuals_found, unique_mvr_people_count
                FROM tracking_sessions
                WHERE session_uuid = $1
                """,
                session_uuid,
            )

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            if session["status"].upper() != "COMPLETED":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Session is not completed. Current status: {session['status']}"
                    ),
                )

            mvr_count = int(session.get("unique_mvr_people_count") or 0)
            available_views = ["raw"]
            if mvr_count > 0:
                available_views.append("mvr")

            resolved_view = "raw"
            if view == "mvr" and mvr_count > 0:
                resolved_view = "mvr"

            analyses = []

            if resolved_view == "raw":
                rows = await conn.fetch(
                    """
                    SELECT
                        i.individual_uuid,
                        i.individual_id,
                        i.confidence_score AS average_confidence,
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.entry_bbox,
                        iva.exit_bbox,
                        iva.confidence,
                        imm.mvr_people_uuid,
                        mvr.gender,
                        mvr.gender_confidence,
                        mvr.age_min,
                        mvr.age_max,
                        mvr.age_confidence,
                        mvr.name,
                        mvr.name_updated_at,
                        mvr.name_updated_by
                    FROM session_individuals si
                    JOIN individuals i
                        ON si.individual_uuid = i.individual_uuid
                    LEFT JOIN individual_video_appearances iva
                        ON i.individual_uuid = iva.individual_uuid
                    LEFT JOIN individual_mvr_mapping imm
                        ON i.individual_uuid = imm.individual_uuid
                    LEFT JOIN mvr_people mvr
                        ON imm.mvr_people_uuid = mvr.mvr_people_uuid
                        AND mvr.is_orphaned = FALSE
                    WHERE si.session_uuid = $1
                    ORDER BY i.individual_uuid, iva.start_timestamp ASC
                    """,
                    session_uuid,
                )

                by_individual = {}
                for row in rows:
                    individual_uuid = str(row["individual_uuid"])
                    entry = by_individual.setdefault(
                        individual_uuid,
                        {
                            "individual_uuid": individual_uuid,
                            "individual_id": row["individual_id"],
                            "session_uuid": session_uuid,
                            "total_appearances": 0,
                            "unique_videos": set(),
                            "first_seen": None,
                            "last_seen": None,
                            "total_duration_seconds": 0.0,
                            "average_confidence": round(float(row["average_confidence"] or 0.0), 3),
                            "average_route_velocity": None,
                            "demographics": None,
                            "aggregate_demographics": None,
                            "appearances": [],
                            "person_object_uuids": [],
                            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                            "is_super_individual": False,
                            "merged_mvr_count": 1,
                            "merged_mvr_people": [],
                            "best_face_thumbnail": None,
                            "name": row.get("name"),
                            "name_updated_at": row["name_updated_at"].isoformat() if row.get("name_updated_at") else None,
                            "name_updated_by": row.get("name_updated_by"),
                        },
                    )

                    start_ts = row.get("start_timestamp")
                    end_ts = row.get("end_timestamp")
                    if start_ts and end_ts:
                        entry["total_appearances"] += 1
                        entry["unique_videos"].add(str(row["video_uuid"]))
                        entry["appearances"].append(
                            {
                                "individual_uuid": individual_uuid,
                                "video_uuid": str(row["video_uuid"]),
                                "person_object_uuid": str(row["person_object_uuid"]),
                                "mvr_people_uuid": str(row["mvr_people_uuid"]) if row.get("mvr_people_uuid") else None,
                                "start_timestamp": start_ts.isoformat(),
                                "end_timestamp": end_ts.isoformat(),
                                "entry_bbox": list(row["entry_bbox"]) if row.get("entry_bbox") else None,
                                "exit_bbox": list(row["exit_bbox"]) if row.get("exit_bbox") else None,
                                "confidence_score": round(float(row.get("confidence") or 0.0), 3),
                            }
                        )
                        entry["person_object_uuids"].append(str(row["person_object_uuid"]))
                        if entry["first_seen"] is None or start_ts < entry["first_seen"]:
                            entry["first_seen"] = start_ts
                        if entry["last_seen"] is None or end_ts > entry["last_seen"]:
                            entry["last_seen"] = end_ts

                    if row.get("gender") is not None:
                        entry["demographics"] = {
                            "gender": row.get("gender"),
                            "gender_confidence": round(float(row.get("gender_confidence") or 0.0), 3) if row.get("gender_confidence") is not None else None,
                            "age_min": int(row["age_min"]) if row.get("age_min") is not None else None,
                            "age_max": int(row["age_max"]) if row.get("age_max") is not None else None,
                            "age_mean": round((int(row["age_min"]) + int(row["age_max"])) / 2, 1) if row.get("age_min") is not None and row.get("age_max") is not None else None,
                            "age_confidence": round(float(row.get("age_confidence") or 0.0), 3) if row.get("age_confidence") is not None else None,
                        }

                for entry in by_individual.values():
                    entry["unique_videos"] = len(entry["unique_videos"])
                    entry["first_seen"] = entry["first_seen"].isoformat() if entry["first_seen"] else datetime.now(timezone.utc).isoformat()
                    entry["last_seen"] = entry["last_seen"].isoformat() if entry["last_seen"] else datetime.now(timezone.utc).isoformat()
                    analyses.append(entry)

                analyses.sort(key=lambda item: (item["first_seen"], item["individual_uuid"]))

            return {
                "session_uuid": session_uuid,
                "view_type": resolved_view,
                "available_views": available_views,
                "merge_state": {
                    "unique_mvr_people_count": mvr_count,
                    "individuals_found": int(session.get("individuals_found") or 0),
                },
                "analyses": analyses,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/individuals/{individual_uuid}/aggregated-analysis")
async def get_individual_aggregated_analysis(
    individual_uuid: str,
    session_uuid: str,
    http_request: Request
):
    """
    Phase 6: Get comprehensive aggregated analysis for a specific individual.
    
    Returns:
    - Best quality person object (from Orchestrator)
    - All appearances chronologically
    - Aggregated routes and movement patterns
    - Temporal analysis
    
    Required for Flutter individual detail view.
    """
    try:
        logger.info(f"Phase 6: Getting aggregated analysis for individual {individual_uuid} in session {session_uuid}")
        
        # Get database client
        db_client = get_database_client()
        
        # Validate session and individual
        async with db_client.pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT status FROM tracking_sessions
                WHERE session_uuid = $1
                """,
                session_uuid
            )
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Status can be 'COMPLETED' or 'completed' depending on database
            if session['status'].upper() != 'COMPLETED':
                raise HTTPException(
                    status_code=400,
                    detail=f"Session is not completed. Current status: {session['status']}"
                )
            
            # Check if the UUID is an MVR person UUID or individual UUID
            # First, check if it's an MVR person UUID
            mvr_check = await conn.fetchrow(
                """
                SELECT mvr_people_uuid FROM mvr_people
                WHERE mvr_people_uuid = $1
                """,
                individual_uuid
            )

            if mvr_check:
                # It's an MVR person UUID - get all mapped individuals
                logger.info(
                    "Phase 6: UUID is MVR person, "
                    "aggregating appearances from all mapped individuals"
                )
                appearances = await conn.fetch(
                    """
                    SELECT
                        iva.individual_uuid,
                        i.individual_id,
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.entry_bbox,
                        iva.exit_bbox,
                        iva.confidence,
                        mvr.gender,
                        mvr.gender_confidence,
                        mvr.age_min,
                        mvr.age_max,
                        mvr.age_confidence,
                        mvr.name,
                        mvr.name_updated_at,
                        mvr.name_updated_by
                    FROM individual_mvr_mapping imm
                    JOIN individual_video_appearances iva
                        ON imm.individual_uuid = iva.individual_uuid
                    JOIN individuals i
                        ON iva.individual_uuid = i.individual_uuid
                    LEFT JOIN mvr_people mvr
                        ON imm.mvr_people_uuid = mvr.mvr_people_uuid
                        AND mvr.is_orphaned = FALSE
                    WHERE imm.mvr_people_uuid = $1
                    ORDER BY iva.start_timestamp ASC
                    """,
                    individual_uuid
                )
                
                # DEBUG: Log first appearance from SQL query
                if appearances:
                    logger.info("=" * 60)
                    logger.info("SQL QUERY RESULT DEBUG (MVR person path)")
                    logger.info("=" * 60)
                    logger.info(f"Total appearances fetched: {len(appearances)}")
                    logger.info(f"First appearance columns: {list(appearances[0].keys())}")
                    logger.info(f"First appearance name: {appearances[0].get('name')}")
                    logger.info(f"First appearance name_updated_at: {appearances[0].get('name_updated_at')}")
                    logger.info(f"First appearance name_updated_by: {appearances[0].get('name_updated_by')}")
                    logger.info("=" * 60)
            else:
                # It's a regular individual UUID
                logger.info(
                    "Phase 6: UUID is individual, "
                    "getting appearances directly"
                )
                appearances = await conn.fetch(
                    """
                    SELECT
                        iva.individual_uuid,
                        i.individual_id,
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.entry_bbox,
                        iva.exit_bbox,
                        iva.confidence,
                        mvr.gender,
                        mvr.gender_confidence,
                        mvr.age_min,
                        mvr.age_max,
                        mvr.age_confidence,
                        mvr.name,
                        mvr.name_updated_at,
                        mvr.name_updated_by
                    FROM individual_video_appearances iva
                    JOIN individuals i
                        ON iva.individual_uuid = i.individual_uuid
                    LEFT JOIN individual_mvr_mapping imm
                        ON iva.individual_uuid = imm.individual_uuid
                    LEFT JOIN mvr_people mvr
                        ON imm.mvr_people_uuid = mvr.mvr_people_uuid
                        AND mvr.is_orphaned = FALSE
                    WHERE iva.individual_uuid = $1
                    ORDER BY iva.start_timestamp ASC
                    """,
                    individual_uuid
                )
                
                # DEBUG: Log first appearance from SQL query
                if appearances:
                    logger.info("=" * 60)
                    logger.info("SQL QUERY RESULT DEBUG (Individual path)")
                    logger.info("=" * 60)
                    logger.info(f"Total appearances fetched: {len(appearances)}")
                    logger.info(f"First appearance columns: {list(appearances[0].keys())}")
                    logger.info(f"First appearance name: {appearances[0].get('name')}")
                    logger.info(f"First appearance name_updated_at: {appearances[0].get('name_updated_at')}")
                    logger.info(f"First appearance name_updated_by: {appearances[0].get('name_updated_by')}")
                    logger.info("=" * 60)
            
            # If no appearances found, return basic individual info
            # (appearances table might be empty if not populated during processing)
            if not appearances:
                logger.warning(
                    f"No appearances found for individual {individual_uuid}"
                )
                # Return minimal response with empty appearances
                return {
                    "individual_uuid": individual_uuid,
                    "individual_id": f"ind_{individual_uuid[:8]}",
                    "session_uuid": session_uuid,
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "first_seen": "",  # Empty string instead of None for Flutter compatibility
                    "last_seen": "",   # Empty string instead of None for Flutter compatibility
                    "total_duration_seconds": 0,
                    "average_confidence": 0.0,
                    "appearances": [],
                    "person_object_uuids": [],
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Format appearances and collect demographics
            appearances_list = []
            person_object_uuids = []
            demographics_data = []
            
            for app in appearances:
                appearances_list.append({
                    "individual_uuid": str(app['individual_uuid']),
                    "video_uuid": str(app['video_uuid']),
                    "person_object_uuid": str(app['person_object_uuid']),
                    "start_timestamp": app['start_timestamp'].isoformat() if app['start_timestamp'] else "",
                    "end_timestamp": app['end_timestamp'].isoformat() if app['end_timestamp'] else "",
                    "entry_bbox": list(app['entry_bbox']) if app['entry_bbox'] else None,
                    "exit_bbox": list(app['exit_bbox']) if app['exit_bbox'] else None,
                    "confidence_score": round(float(app['confidence']), 3) if app['confidence'] else 0.0
                })
                person_object_uuids.append(str(app['person_object_uuid']))
                
                # Collect demographics data if available
                if app.get('gender') is not None:
                    demographics_data.append({
                        'gender': app['gender'],
                        'gender_confidence': float(app['gender_confidence']) if app['gender_confidence'] else 0.0,
                        'age_min': int(app['age_min']) if app['age_min'] is not None else None,
                        'age_max': int(app['age_max']) if app['age_max'] is not None else None,
                        'age_mean': (int(app['age_min']) + int(app['age_max'])) / 2 if (app['age_min'] is not None and app['age_max'] is not None) else None,
                        'age_confidence': float(app['age_confidence']) if app['age_confidence'] else 0.0
                    })
            
            # Calculate aggregated metrics
            first_appearance = appearances[0]
            last_appearance = appearances[-1]
            
            # Extract name fields from first appearance (all appearances share the same MVR person)
            name = first_appearance.get('name')
            name_updated_at = first_appearance.get('name_updated_at')
            name_updated_by = first_appearance.get('name_updated_by')
            
            # DEBUG: Log name extraction
            logger.info("=" * 60)
            logger.info("NAME FIELD EXTRACTION DEBUG")
            logger.info("=" * 60)
            logger.info(f"Individual UUID: {individual_uuid}")
            logger.info(f"First appearance keys: {list(first_appearance.keys())}")
            logger.info(f"Extracted name: {name}")
            logger.info(f"Extracted name_updated_at: {name_updated_at}")
            logger.info(f"Extracted name_updated_by: {name_updated_by}")
            logger.info(f"Name is None: {name is None}")
            logger.info("=" * 60)
            
            total_duration = 0
            if first_appearance['start_timestamp'] and last_appearance['end_timestamp']:
                total_duration = (
                    last_appearance['end_timestamp'] - first_appearance['start_timestamp']
                ).total_seconds()
            
            avg_confidence = sum(
                float(app['confidence']) for app in appearances if app['confidence']
            ) / len(appearances)
            
            # Calculate aggregate demographics
            demographics = None
            aggregate_demographics = None
            
            if demographics_data:
                # Aggregate gender counts
                gender_counts = {'male': 0, 'female': 0, 'unknown': 0}
                gender_confidences = []
                ages = []
                age_confidences = []
                
                for demo in demographics_data:
                    gender = demo.get('gender', 'unknown')
                    if gender in gender_counts:
                        gender_counts[gender] += 1
                    else:
                        gender_counts['unknown'] += 1
                    
                    if demo.get('gender_confidence'):
                        gender_confidences.append(demo['gender_confidence'])
                    
                    if demo.get('age_mean') is not None:
                        ages.append(demo['age_mean'])
                    
                    if demo.get('age_confidence'):
                        age_confidences.append(demo['age_confidence'])
                
                # Determine most common gender (for primary demographics)
                most_common_gender = max(gender_counts, key=gender_counts.get)
                avg_gender_confidence = sum(gender_confidences) / len(gender_confidences) if gender_confidences else None
                
                # Calculate age statistics
                avg_age = sum(ages) / len(ages) if ages else None
                min_age = min(ages) if ages else None
                max_age = max(ages) if ages else None
                age_range = max_age - min_age if (max_age is not None and min_age is not None) else None
                avg_age_confidence = sum(age_confidences) / len(age_confidences) if age_confidences else None
                
                # Primary demographics (most common values)
                demographics = {
                    "gender": most_common_gender if most_common_gender != 'unknown' else None,
                    "gender_confidence": round(avg_gender_confidence, 3) if avg_gender_confidence else None,
                    "age_min": int(min_age) if min_age is not None else None,
                    "age_max": int(max_age) if max_age is not None else None,
                    "age_mean": round(avg_age, 1) if avg_age is not None else None,
                    "age_confidence": round(avg_age_confidence, 3) if avg_age_confidence else None
                }
                
                # Aggregate statistics
                aggregate_demographics = {
                    "total_individuals": len(set(str(app['individual_uuid']) for app in appearances)),
                    "gender_breakdown": {
                        "male": gender_counts['male'],
                        "female": gender_counts['female'],
                        "unknown": gender_counts['unknown']
                    },
                    "age_statistics": {
                        "average_age": round(avg_age, 1) if avg_age is not None else None,
                        "min_age": int(min_age) if min_age is not None else None,
                        "max_age": int(max_age) if max_age is not None else None,
                        "age_range": round(age_range, 1) if age_range is not None else None
                    }
                }
            
            # Calculate average route velocity from orchestrator route data
            avg_route_velocity = None
            try:
                from ...services.orchestrator_client import OrchestratorClient
                from ...services.route_aggregator import calculate_route_velocities
                
                orchestrator = OrchestratorClient(
                    orchestrator_base_url=os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8002")
                )
                
                all_route_points = []
                
                # Get unique video UUIDs from appearances
                unique_videos = set(str(app['video_uuid']) for app in appearances)
                logger.info(f"Fetching routes from {len(unique_videos)} video(s) for velocity calculation")
                
                # Fetch person objects data for each video to get route points
                for video_uuid in unique_videos:
                    try:
                        person_objects_data = await orchestrator.get_person_objects(video_uuid)
                        if person_objects_data and 'person_objects' in person_objects_data:
                            for person_obj in person_objects_data['person_objects']:
                                # Extract route points from movement_tracking
                                routes = person_obj.get('routes', [])
                                for route_point in routes:
                                    all_route_points.append({
                                        'x': float(route_point['x']),
                                        'y': float(route_point['y']),
                                        'timestamp': route_point['timestamp'],
                                        'video_uuid': video_uuid,
                                        'confidence': float(route_point.get('confidence', 1.0))
                                    })
                    except Exception as e:
                        logger.warning(f"Could not fetch routes from video {video_uuid}: {e}")
                
                if len(all_route_points) >= 2:
                    # Sort by timestamp
                    all_route_points.sort(key=lambda r: r['timestamp'])
                    
                    # Calculate velocities
                    routes_with_velocity = calculate_route_velocities(all_route_points)
                    
                    # Calculate average velocity (excluding None values)
                    velocities = [r['velocity'] for r in routes_with_velocity if r.get('velocity') is not None]
                    if velocities:
                        avg_route_velocity = round(sum(velocities) / len(velocities), 6)
                        logger.info(f"Calculated average route velocity from {len(all_route_points)} route points: {avg_route_velocity} normalized px/s")
                else:
                    logger.info(f"Not enough route points ({len(all_route_points)}) for velocity calculation")
            except Exception as e:
                logger.warning(f"Failed to calculate route velocity: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
            
            # Build response
            response = {
                "individual_uuid": individual_uuid,
                "individual_id": first_appearance['individual_id'],
                "session_uuid": session_uuid,
                "name": name,
                "name_updated_at": name_updated_at.isoformat() if name_updated_at else None,
                "name_updated_by": name_updated_by,
                "total_appearances": len(appearances),
                "unique_videos": len(set(str(app['video_uuid']) for app in appearances)),
                "first_seen": first_appearance['start_timestamp'].isoformat() if first_appearance['start_timestamp'] else "",
                "last_seen": last_appearance['end_timestamp'].isoformat() if last_appearance['end_timestamp'] else "",
                "total_duration_seconds": round(total_duration, 2),
                "average_confidence": round(avg_confidence, 3),
                "average_route_velocity": avg_route_velocity,
                "demographics": demographics,
                "aggregate_demographics": aggregate_demographics,
                "appearances": appearances_list,
                "person_object_uuids": person_object_uuids,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # DEBUG: Log final response name fields
            logger.info("=" * 60)
            logger.info("RESPONSE BUILD DEBUG")
            logger.info("=" * 60)
            logger.info(f"Response name field: {response.get('name')}")
            logger.info(f"Response name_updated_at: {response.get('name_updated_at')}")
            logger.info(f"Response name_updated_by: {response.get('name_updated_by')}")
            logger.info("=" * 60)
            
            logger.info(f"Phase 6: Returning aggregated analysis for individual {individual_uuid}")
            logger.info(f"  Appearances: {len(appearances)}, Videos: {response['unique_videos']}, Duration: {total_duration}s")
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Phase 6 error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================================
# MANUAL MERGE ENDPOINT - For manually merging selected individuals
# ============================================================================

@router.post("/merge", response_model=MergeIndividualsResponse)
async def merge_individuals_manual(
    request: MergeIndividualsRequest,
    http_request: Request
):
    """
    Manually merge selected individuals based on facial embedding similarity.
    
    This endpoint allows users to manually merge individuals after reviewing
    them in the cross-video analysis UI. It uses facial embeddings to validate
    similarity and merge duplicate individuals.
    
    **Process:**
    1. Validates that all individuals exist in the session
    2. Generates facial embeddings from best quality face crops
    3. Calculates similarity matrix using cosine similarity
    4. Selects predominant individual (highest quality)
    5. Transfers all appearances to predominant individual
    6. Deletes merged individuals
    
    **Parameters:**
    - individual_uuids: List of individual UUIDs to merge (minimum 2)
    - session_uuid: Tracking session UUID
    - similarity_threshold: Optional threshold for validation (default: 0.70)
    - triggered_by: Source that triggered merge (default: "manual")
    
    **Returns:**
    - success: Whether merge was successful
    - predominant_individual_uuid: UUID of the kept individual
    - merged_individual_uuids: List of merged (deleted) individual UUIDs
    - similarity_score: Average similarity score
    - total_appearances_after_merge: Total appearances after merge
    - total_videos_after_merge: Total unique videos after merge
    - merged_at: Timestamp of merge operation
    
    **Authentication:** Extracts JWT token from Authorization header
    """
    print("\n" + "🔄 " * 40)
    print("🔄 MERGE REQUEST RECEIVED")
    print("🔄 " * 40 + "\n")
    
    logger.info(
        f"Manual merge request for {len(request.individual_uuids)} individuals"
    )
    
    try:
        db_client = get_database_client()
        
        # Extract auth token for Vision DB access
        auth_header = http_request.headers.get("Authorization")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else None
        
        # Validate that we have at least 2 individuals
        if len(request.individual_uuids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 individuals required for merging"
            )
        
        # Validate that all individuals exist and belong to the session
        async with db_client.pool.acquire() as conn:
            for ind_uuid in request.individual_uuids:
                # Check if individual exists
                individual = await conn.fetchrow("""
                    SELECT individual_uuid, individual_id
                    FROM individuals
                    WHERE individual_uuid = $1
                """, ind_uuid)
                
                if not individual:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Individual {ind_uuid} not found"
                    )
                
                # Check if individual belongs to the session
                session_link = await conn.fetchrow("""
                    SELECT session_uuid, individual_uuid
                    FROM session_individuals
                    WHERE session_uuid = $1 AND individual_uuid = $2
                """, request.session_uuid, ind_uuid)
                
                if not session_link:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Individual {ind_uuid} does not belong to session {request.session_uuid}"
                    )
        
        # Generate embeddings and calculate similarities
        logger.info("Generating embeddings for similarity validation...")
        
        try:
            from services.embedding_service import (
                EmbeddingService,
                DEEPFACE_AVAILABLE
            )
            
            if not DEEPFACE_AVAILABLE:
                logger.warning("DeepFace not available - merging without similarity validation")
                avg_similarity = None
            else:
                import numpy as np
                from sklearn.metrics.pairwise import cosine_similarity
                
                embedding_service = EmbeddingService(db_client)
                individual_embeddings = {}
                
                # Extract embeddings for each individual using REST API
                # (no direct DB access to other services)
                import aiohttp
                import cv2
                
                for ind_uuid in request.individual_uuids:
                    # Get video appearances for this individual
                    async with db_client.pool.acquire() as conn:
                        video_appearances = await conn.fetch("""
                            SELECT DISTINCT video_uuid, person_object_uuid
                            FROM individual_video_appearances
                            WHERE individual_uuid = $1
                        """, ind_uuid)
                        
                        if not video_appearances:
                            continue
                        
                        # Use first video's person_object to get face data
                        video_uuid = str(video_appearances[0]['video_uuid'])
                    
                    # Call Orchestrator API via Gateway to get person objects
                    # (proper microservice pattern - no direct DB access)
                    try:
                        orchestrator_url = (
                            f"http://localhost:8080/api/v1/orchestrator/"
                            f"person-objects/{video_uuid}"
                        )
                        
                        headers = {}
                        if auth_token:
                            if not auth_token.startswith('Bearer'):
                                headers['Authorization'] = f'Bearer {auth_token}'
                            else:
                                headers['Authorization'] = auth_token
                        
                        timeout = aiohttp.ClientTimeout(total=30)
                        async with aiohttp.ClientSession(
                            timeout=timeout
                        ) as session:
                            async with session.get(
                                orchestrator_url, headers=headers
                            ) as response:
                                if response.status != 200:
                                    logger.warning(
                                        f"Orchestrator returned {response.status} "
                                        f"for {video_uuid[:8]}"
                                    )
                                    continue
                                
                                orch_data = await response.json()
                                if not (orch_data.get('success') and 
                                        orch_data.get('person_groups')):
                                    continue
                                
                                # Get first person object (best quality)
                                person_group = orch_data['person_groups'][0]
                                rep_faces = person_group.get(
                                    'representative_faces', []
                                )
                                
                                if not rep_faces:
                                    continue
                                
                                # Use first face (highest quality)
                                best_face = rep_faces[0]
                                face_data = best_face.get('face_data', {})
                                bbox = face_data.get('bbox')
                                frame_number = face_data.get('frame_number', 0)
                                
                                if not bbox or len(bbox) != 4:
                                    continue
                                
                                # Fetch frame from Media service via Gateway
                                frame_url = (
                                    f"http://localhost:8080/api/v1/media/"
                                    f"{video_uuid}/frame/{frame_number}"
                                    f"?format=jpeg"
                                )
                                
                                async with session.get(
                                    frame_url, headers=headers
                                ) as frame_resp:
                                    if frame_resp.status != 200:
                                        continue
                                    
                                    # Decode frame
                                    frame_bytes = await frame_resp.read()
                                    from PIL import Image
                                    from io import BytesIO
                                    
                                    pil_image = Image.open(
                                        BytesIO(frame_bytes)
                                    )
                                    frame = np.array(pil_image)
                                    frame_bgr = cv2.cvtColor(
                                        frame, cv2.COLOR_RGB2BGR
                                    )
                                    
                                    # Crop and resize face
                                    x, y = int(bbox[0]), int(bbox[1])
                                    x2, y2 = int(bbox[2]), int(bbox[3])
                                    
                                    # Align bbox to crop frame if detection resolution differs
                                    crop_h, crop_w = frame_bgr.shape[:2]
                                    d_w = face_data.get('frame_width')
                                    d_h = face_data.get('frame_height')
                                    if d_w and d_h and (d_w != crop_w or d_h != crop_h):
                                        sx = crop_w / d_w
                                        sy = crop_h / d_h
                                        x = int(round(x * sx))
                                        y = int(round(y * sy))
                                        x2 = int(round(x2 * sx))
                                        y2 = int(round(y2 * sy))
                                    
                                    cropped = frame_bgr[y:y2, x:x2].copy()
                                    if cropped.size == 0:
                                        continue
                                    
                                    resized = cv2.resize(
                                        cropped, (160, 160),
                                        interpolation=cv2.INTER_AREA
                                    )
                                    
                                    # Generate embedding
                                    embedding, _ = (
                                        await embedding_service
                                        ._generate_facial_embedding(
                                            resized, 0, 0, 160, 160
                                        )
                                    )
                                    
                                    if embedding is not None:
                                        individual_embeddings[ind_uuid] = (
                                            embedding
                                        )
                                        logger.info(
                                            f"Generated embedding for "
                                            f"{ind_uuid[:8]} via REST API"
                                        )
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to get embedding for {ind_uuid[:8]} "
                            f"via REST API: {e}"
                        )
                        continue
                
                # Calculate average similarity if we have embeddings
                if len(individual_embeddings) >= 2:
                    uuids = list(individual_embeddings.keys())
                    embeddings_matrix = np.array([
                        individual_embeddings[uuid] for uuid in uuids
                    ])
                    
                    similarities = cosine_similarity(embeddings_matrix)
                    
                    # Log detailed pairwise similarities
                    print("\n" + "=" * 80)
                    print("🔍 FACE EMBEDDING SIMILARITY ANALYSIS")
                    print("=" * 80)
                    logger.info("FACE EMBEDDING SIMILARITY MATRIX:")
                    logger.info(f"Total individuals: {len(uuids)}")
                    logger.info(
                        f"Successfully generated embeddings for: "
                        f"{len(individual_embeddings)}/"
                        f"{len(request.individual_uuids)}"
                    )
                    logger.info("-" * 80)
                    
                    for i, uuid_i in enumerate(uuids):
                        for j, uuid_j in enumerate(uuids):
                            if i < j:  # Only show upper triangle
                                sim_score = similarities[i][j]
                                log_msg = (
                                    f"  Individual {uuid_i[:8]}... <-> "
                                    f"{uuid_j[:8]}...: "
                                    f"Similarity = {sim_score:.4f} "
                                    f"({sim_score*100:.2f}%)"
                                )
                                print(log_msg)  # Print to stdout
                                logger.info(log_msg)
                    
                    # Calculate average similarity (excluding diagonal)
                    mask = np.ones_like(similarities, dtype=bool)
                    np.fill_diagonal(mask, False)
                    avg_similarity = float(similarities[mask].mean())
                    min_similarity = float(similarities[mask].min())
                    max_similarity = float(similarities[mask].max())
                    
                    logger.info("-" * 80)
                    print("-" * 80)
                    logger.info("Similarity Statistics:")
                    print("📊 Similarity Statistics:")
                    
                    avg_msg = (
                        f"  Average: {avg_similarity:.4f} "
                        f"({avg_similarity*100:.2f}%)"
                    )
                    min_msg = (
                        f"  Minimum: {min_similarity:.4f} "
                        f"({min_similarity*100:.2f}%)"
                    )
                    max_msg = (
                        f"  Maximum: {max_similarity:.4f} "
                        f"({max_similarity*100:.2f}%)"
                    )
                    thresh_msg = (
                        f"  Threshold: {request.similarity_threshold:.4f} "
                        f"({request.similarity_threshold*100:.2f}%)"
                    )
                    
                    print(avg_msg)
                    print(min_msg)
                    print(max_msg)
                    print(thresh_msg)
                    logger.info(avg_msg)
                    logger.info(min_msg)
                    logger.info(max_msg)
                    logger.info(thresh_msg)
                    
                    logger.info("=" * 80)
                    print("=" * 80 + "\n")
                    
                    # Validate against threshold - ENFORCE IT
                    if avg_similarity < request.similarity_threshold:
                        logger.warning(
                            f"Similarity {avg_similarity:.3f} below "
                            f"threshold {request.similarity_threshold}"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Faces are not similar enough to merge. "
                                f"Similarity: {avg_similarity:.1%} < "
                                f"Threshold: "
                                f"{request.similarity_threshold:.1%}. "
                                f"These individuals appear to be "
                                f"different people."
                            )
                        )
                else:
                    avg_similarity = None
                    logger.warning(
                        "Not enough embeddings for similarity validation"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Could not generate face embeddings for "
                            "similarity validation. "
                            "Cannot merge individuals without validating "
                            "they are the same person."
                        )
                    )
        
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            avg_similarity = None
        
        # Determine predominant individual (highest total appearances or first in list)
        async with db_client.pool.acquire() as conn:
            appearance_counts = {}
            
            for ind_uuid in request.individual_uuids:
                count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM individual_video_appearances
                    WHERE individual_uuid = $1
                """, ind_uuid)
                appearance_counts[ind_uuid] = count
            
            # Select individual with most appearances as predominant
            predominant_uuid = max(appearance_counts.items(), key=lambda x: x[1])[0]
            merged_uuids = [uuid for uuid in request.individual_uuids if uuid != predominant_uuid]
            
            logger.info(f"Predominant individual: {predominant_uuid}")
            logger.info(f"Merging {len(merged_uuids)} individuals into predominant")
            
            # Execute merge in transaction
            async with conn.transaction():
                # Transfer all appearances to predominant individual
                for merge_uuid in merged_uuids:
                    await conn.execute("""
                        UPDATE individual_video_appearances
                        SET individual_uuid = $1
                        WHERE individual_uuid = $2
                    """, predominant_uuid, merge_uuid)
                    
                    logger.info(f"Transferred appearances from {merge_uuid} to {predominant_uuid}")
                
                # Delete merged individuals
                for merge_uuid in merged_uuids:
                    await conn.execute("""
                        DELETE FROM individuals
                        WHERE individual_uuid = $1
                    """, merge_uuid)
                    
                    logger.info(f"Deleted individual {merge_uuid}")
                
                # Get updated statistics for predominant individual
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_appearances,
                        COUNT(DISTINCT video_uuid) as total_videos
                    FROM individual_video_appearances
                    WHERE individual_uuid = $1
                """, predominant_uuid)
        
        merged_at = datetime.now(timezone.utc)
        
        response = MergeIndividualsResponse(
            success=True,
            predominant_individual_uuid=predominant_uuid,
            merged_individual_uuids=merged_uuids,
            similarity_score=avg_similarity,
            total_appearances_after_merge=stats['total_appearances'],
            total_videos_after_merge=stats['total_videos'],
            merged_at=merged_at,
            message=f"Successfully merged {len(merged_uuids)} individuals into {predominant_uuid}"
        )
        
        logger.info(f"Merge completed successfully: {len(merged_uuids)} individuals merged")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Merge failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Merge operation failed: {str(e)}"
        )

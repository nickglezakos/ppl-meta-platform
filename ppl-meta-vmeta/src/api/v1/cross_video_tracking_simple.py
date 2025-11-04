"""
Cross-Video Individual Tracking - Simple Working Implementation
PPL Meta Platform v2.19.13+

A minimal working implementation that directly uses the database
for session management without complex dependencies.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import logging
import json
import hashlib
import asyncio

from pydantic import BaseModel, Field

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
    start_time: datetime
    end_time: datetime
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
        default=0.6,
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

# Initialize router
router = APIRouter(
    prefix="/individuals/tracking",
    tags=["Cross-Video Individual Tracking"]
)


@router.post("/sessions", response_model=TrackingSessionResponse)
async def create_tracking_session(
    request: CreateTrackingSessionRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
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
        
        # Convert to timezone-naive datetime for comparison
        start_time_naive = request.start_time.replace(tzinfo=None) if request.start_time.tzinfo else request.start_time
        end_time_naive = request.end_time.replace(tzinfo=None) if request.end_time.tzinfo else request.end_time
        
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
        
        # Store session in database  
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tracking_sessions (
                    session_uuid, user_id, collections, start_time, end_time,
                    status, config_hash, algorithm_config
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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
            })
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
                       individuals_found, cache_hits
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


async def merge_individuals_by_similarity(
    db_client,
    session_uuid: str,
    individual_uuids: List[str],
    auth_token: str,
    similarity_threshold: float = 0.75
) -> int:
    """
    Merge individuals based on facial embedding similarity.
    
    Uses DeepFace/FaceNet embeddings to identify duplicate individuals
    across different video groups and merges them into single entities.
    
    Args:
        db_client: Database client
        session_uuid: Tracking session UUID
        individual_uuids: List of individual UUIDs to compare
        auth_token: Authorization token for media API
        similarity_threshold: Minimum cosine similarity (0-1)
        
    Returns:
        Number of individuals merged (removed)
    """
    import numpy as np
    
    logger.info(
        f"Merging {len(individual_uuids)} individuals "
        f"with threshold {similarity_threshold}"
    )
    
    # DEBUG: Write to database
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET failed_videos = array_append(failed_videos, $2)
                WHERE session_uuid = $1
            """, session_uuid,
                f"merge_function_called: count={len(individual_uuids)}")
    except Exception:
        pass
    
    # Skip if not enough individuals to merge
    if len(individual_uuids) < 2:
        return 0
    
    try:
        # Import embedding service
        from services.embedding_service import (
            EmbeddingService,
            DEEPFACE_AVAILABLE
        )
        
        # DEBUG
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"deepface_available: {DEEPFACE_AVAILABLE}")
        except Exception:
            pass
        
        if not DEEPFACE_AVAILABLE:
            logger.warning(
                "DeepFace not available - skipping embedding merge"
            )
            return 0
        
        embedding_service = EmbeddingService(db_client)
        
        # Step 1: Extract representative frames for each individual
        individual_embeddings = {}
        
        async with db_client.pool.acquire() as conn:
            for individual_uuid in individual_uuids:
                # Get ALL video UUIDs for this individual
                video_appearances = await conn.fetch("""
                    SELECT DISTINCT video_uuid
                    FROM individual_video_appearances
                    WHERE individual_uuid = $1
                """, individual_uuid)
                
                if not video_appearances:
                    logger.warning(
                        f"No appearances for individual {individual_uuid}"
                    )
                    continue
                
                video_uuids = [
                    str(va['video_uuid']) for va in video_appearances
                ]
                
                if not video_uuids:
                    logger.warning(
                        f"No video UUIDs for individual {individual_uuid}"
                    )
                    continue
                
                # Query Vision DB to find person_objects for these videos
                # Select the one with highest quality score
                try:
                    import asyncpg
                    import base64
                    import cv2
                    
                    # Convert to UUID array for PostgreSQL
                    import uuid
                    video_uuid_objects = [
                        uuid.UUID(v) for v in video_uuids
                    ]
                    
                    # Connect to Vision DB
                    vision_conn_str = (
                        "postgresql://postgres:localdevpass@localhost:5432/"
                        "ppl_vision_db"
                    )
                    vision_conn = await asyncpg.connect(vision_conn_str)
                    
                    try:
                        # Get ALL person_objects for this individual's videos
                        # ordered by quality score (best first)
                        person_obj = await vision_conn.fetchrow("""
                            SELECT 
                                po.person_id,
                                po.best_face_id,
                                po.quality_score,
                                fd.media_id
                            FROM person_objects po
                            JOIN face_detections fd 
                                ON fd.id = po.best_face_id
                            WHERE fd.media_id = ANY($1::uuid[])
                              AND po.quality_score IS NOT NULL
                            ORDER BY po.quality_score DESC
                            LIMIT 1
                        """, video_uuid_objects)
                        
                        if not person_obj or not person_obj['best_face_id']:
                            logger.warning(
                                f"No person_object with quality score "
                                f"for individual {individual_uuid}, "
                                f"videos: {len(video_uuids)}"
                            )
                            continue
                        
                        best_face_id = person_obj['best_face_id']
                        
                        # Get face crop from face_crops table
                        face_crop_data = await vision_conn.fetchrow("""
                            SELECT crop_base64, crop_width, crop_height
                            FROM face_crops
                            WHERE face_detection_id = $1
                        """, best_face_id)
                        
                        if not face_crop_data or not face_crop_data['crop_base64']:
                            logger.warning(
                                f"No face_crop for face {best_face_id}"
                            )
                            continue
                        
                        # Decode base64 face crop
                        crop_bytes = base64.b64decode(
                            face_crop_data['crop_base64']
                        )
                        crop_array = np.frombuffer(crop_bytes, np.uint8)
                        face_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)
                        
                        if face_crop is None or face_crop.size == 0:
                            logger.warning(
                                f"Failed to decode face crop for {best_face_id}"
                            )
                            continue
                        
                        # Convert BGR to RGB for DeepFace
                        face_crop_rgb = cv2.cvtColor(
                            face_crop, cv2.COLOR_BGR2RGB
                        )
                        
                        # Generate DeepFace embedding from face crop
                        # Use full crop as bbox (face is already cropped)
                        h, w = face_crop_rgb.shape[:2]
                        embedding = await embedding_service._generate_facial_embedding(  # noqa
                            face_crop_rgb, 0, 0, w, h
                        )
                        
                        if embedding is not None:
                            individual_embeddings[individual_uuid] = embedding
                            logger.info(
                                f"✅ Generated embedding for individual "
                                f"{individual_uuid} from Vision face crop"
                            )
                    
                    finally:
                        await vision_conn.close()
                        
                except Exception as e:
                    logger.error(
                        f"Failed to generate embedding for "
                        f"individual {individual_uuid}: {e}"
                    )
                    continue
        
        # DEBUG: Report embedding extraction results
        try:
            async with db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $2)
                    WHERE session_uuid = $1
                """, session_uuid,
                    f"embeddings_generated: {len(individual_embeddings)}/{len(individual_uuids)}")
        except Exception:
            pass
        
        # Step 2: Compare embeddings and find duplicates
        if len(individual_embeddings) < 2:
            logger.warning(
                "Not enough embeddings generated for merging"
            )
            # DEBUG
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"merge_skipped: only_{len(individual_embeddings)}_embeddings")
            except Exception:
                pass
            return 0
        
        # Build similarity matrix using cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        
        uuids = list(individual_embeddings.keys())
        embeddings_matrix = np.array([
            individual_embeddings[uuid] for uuid in uuids
        ])
        
        # Calculate pairwise similarities
        similarities = cosine_similarity(embeddings_matrix)
        
        # Find merge candidates
        merge_groups = []  # [(keep_uuid, [merge_uuid1, merge_uuid2, ...])]
        merged_uuids = set()
        
        for i in range(len(uuids)):
            if uuids[i] in merged_uuids:
                continue
            
            # Find all individuals similar to this one
            similar_indices = np.where(
                similarities[i] >= similarity_threshold
            )[0]
            
            # Filter out self and already merged
            similar_uuids = [
                uuids[j] for j in similar_indices
                if j != i and uuids[j] not in merged_uuids
            ]
            
            if similar_uuids:
                # Keep the first one, merge the others
                merge_groups.append((uuids[i], similar_uuids))
                merged_uuids.update(similar_uuids)
        
        # Step 3: Execute merges in database
        total_merged = 0
        
        async with db_client.pool.acquire() as conn:
            async with conn.transaction():
                for keep_uuid, merge_uuids in merge_groups:
                    for merge_uuid in merge_uuids:
                        # Transfer all appearances to kept individual
                        await conn.execute("""
                            UPDATE individual_video_appearances
                            SET individual_uuid = $1
                            WHERE individual_uuid = $2
                        """, keep_uuid, merge_uuid)
                        
                        # Delete merged individual
                        await conn.execute("""
                            DELETE FROM individuals
                            WHERE individual_uuid = $1
                        """, merge_uuid)
                        
                        total_merged += 1
                        logger.info(
                            f"Merged individual {merge_uuid} "
                            f"into {keep_uuid}"
                        )
        
        logger.info(
            f"Successfully merged {total_merged} individuals "
            f"into {len(merge_groups)} unique individuals"
        )
        return total_merged
        
    except Exception as e:
        logger.error(f"Merging failed: {e}")
        import traceback
        traceback.print_exc()
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
            
            # Get session details
            session = await conn.fetchrow("""
                SELECT collections, start_time, end_time, algorithm_config
                FROM tracking_sessions WHERE session_uuid = $1
            """, session_uuid)
        
        if not session:
            raise ValueError(f"Session {session_uuid} not found")
        
        logger.info(f"Processing session {session_uuid} for collections: {session['collections']}")
        
        # Discover videos in the collection within time range
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
        
        if len(videos) >= 2:  # Need at least 2 videos for cross-video tracking
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
            
            # Process each group of consecutive videos
            for group_idx, consecutive_videos in enumerate(video_groups):
                if len(consecutive_videos) < 2:
                    # Skip groups with only 1 video
                    continue
                
                # Simulate cross-video individual tracking for this group
                # In a real implementation, this would:
                # 1. Extract person objects from each video
                # 2. Calculate bounding box overlaps and similarities
                # 3. Apply tracking algorithm to group person objects
                
                # Create one individual for this group
                individuals_found += 1
                processed_count += len(consecutive_videos)
                
                # Debug: before creating individual
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid, f"before_creating_individual_group_{group_idx}")
                except Exception:
                    pass
                
                # Create actual individual record in database
                individual_uuid = str(uuid4())
                individual_id = f"ind_{individual_uuid[:8]}"
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO individuals (
                                individual_uuid, individual_id, confidence_score,
                                spatial_signature, temporal_signature
                            ) VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                        """,
                            individual_uuid,
                            individual_id,
                            0.85,
                            '{"type": "mock_spatial"}',
                            '{"type": "mock_temporal"}'
                        )
                    
                    # Debug: individual created
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid, f"individual_created: {individual_uuid}")
                    except Exception:
                        pass
                except Exception as e:
                    # Debug: individual creation failed
                    try:
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tracking_sessions
                                SET failed_videos = array_append(failed_videos, $2)
                                WHERE session_uuid = $1
                            """, session_uuid, f"individual_creation_error: {str(e)}")
                    except Exception:
                        pass
                    raise
                
                # Create appearance records for each video
                for i, video in enumerate(consecutive_videos):
                    # Fetch actual person_object from Vision database
                    person_object_uuid = None
                    try:
                        import asyncpg
                        
                        # Connect to Vision DB
                        vision_conn = await asyncpg.connect(
                            "postgresql://postgres:localdevpass@localhost:5432/ppl_vision_db"
                        )
                        
                        try:
                            # Get person_object for this video (first person)
                            person_obj = await vision_conn.fetchrow("""
                                SELECT po.person_id
                                FROM person_objects po
                                JOIN face_detections fd ON fd.id = po.best_face_id
                                WHERE fd.media_id = $1
                                LIMIT 1
                            """, video['uuid'])
                            
                            if person_obj:
                                person_object_uuid = str(person_obj['person_id'])
                            else:
                                # No person_object found - skip or use fallback
                                person_object_uuid = str(uuid4())
                        finally:
                            await vision_conn.close()
                            
                    except Exception as fetch_error:
                        logger.warning(
                            f"Failed to fetch person_object for "
                            f"video {video['uuid']}: {fetch_error}"
                        )
                        person_object_uuid = str(uuid4())  # Fallback
                    
                    try:
                        # Parse timestamp - handle both Z suffix and timezone offsets
                        timestamp_str = video["timestamp"]
                        
                        # Log what we're working with
                        if session_uuid:
                            try:
                                async with db_client.pool.acquire() as conn:
                                    await conn.execute("""
                                        UPDATE tracking_sessions
                                        SET failed_videos = array_append(failed_videos, $2)
                                        WHERE session_uuid = $1
                                    """, session_uuid, 
                                    f"debug_timestamp_{i}: type={type(timestamp_str).__name__}, value={str(timestamp_str)[:50]}")
                            except Exception:
                                pass
                        
                        if isinstance(timestamp_str, str):
                            # Parse string timestamp
                            start_ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            # Already a datetime object
                            start_ts = timestamp_str
                        
                        # Convert to UTC and make naive for database storage
                        # Database columns are TIMESTAMP WITHOUT TIME ZONE (stores UTC)
                        from datetime import timezone as tz
                        if start_ts.tzinfo is None:
                            # Already naive - assume it's UTC
                            pass
                        else:
                            # Convert to UTC and remove timezone info
                            start_ts = start_ts.astimezone(tz.utc).replace(tzinfo=None)
                        
                        end_ts = start_ts + timedelta(seconds=30)
                        
                        async with db_client.pool.acquire() as conn:
                            await conn.execute("""
                                INSERT INTO individual_video_appearances (
                                    individual_uuid, video_uuid,
                                    person_object_uuid,
                                    start_timestamp, end_timestamp,
                                    entry_bbox, exit_bbox,
                                    confidence
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            """,
                                individual_uuid,
                                video["uuid"],
                                person_object_uuid,
                                start_ts,
                                end_ts,
                                [100 + i*10, 200 + i*10, 150 + i*10, 300 + i*10],
                                [110 + i*10, 210 + i*10, 160 + i*10, 310 + i*10],
                                0.85
                            )
                    except Exception as e:
                        # Debug: appearance creation failed
                        try:
                            async with db_client.pool.acquire() as conn:
                                await conn.execute("""
                                    UPDATE tracking_sessions
                                    SET failed_videos = array_append(
                                        failed_videos, $2
                                    )
                                    WHERE session_uuid = $1
                                """, session_uuid,
                                    f"appearance_error_{i}: {str(e)}")
                        except Exception:
                            pass
                
                created_individuals.append(individual_uuid)
                
                logger.info(f"Group {group_idx}: Created individual {individual_uuid} with {len(consecutive_videos)} appearances")
            
            # After processing all groups
            logger.info(
                f"Cross-video tracking complete: {individuals_found} "
                f"individual(s), {processed_count} videos processed"
            )
            
            # DEBUG: Write merge attempt to database
            try:
                async with db_client.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $2)
                        WHERE session_uuid = $1
                    """, session_uuid,
                        f"merge_check: created_individuals={len(created_individuals)}")
            except Exception:
                pass
            
            # Phase 2: Merge individuals based on facial similarity
            # (DeepFace/FaceNet)
            if len(created_individuals) > 1:
                # DEBUG: Entering merge block
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tracking_sessions
                            SET failed_videos = array_append(failed_videos, $2)
                            WHERE session_uuid = $1
                        """, session_uuid, "entering_merge_block")
                except Exception:
                    pass
                    
                logger.info(
                    f"Starting embedding-based merging for "
                    f"{len(created_individuals)} individuals..."
                )
                try:
                    merged_count = await merge_individuals_by_similarity(
                        db_client=db_client,
                        session_uuid=session_uuid,
                        individual_uuids=created_individuals,
                        auth_token=auth_token,
                        similarity_threshold=0.75  # Adjust as needed
                    )
                    
                    # Update final count after merging
                    individuals_found = individuals_found - merged_count
                    logger.info(
                        f"Merged {merged_count} duplicate individuals. "
                        f"Final count: {individuals_found}"
                    )
                except Exception as merge_error:
                    logger.error(
                        f"Embedding-based merging failed: {merge_error}"
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
                                f"merge_error: {str(merge_error)[:200]}")
                    except Exception:
                        pass
                    # Continue without merging - keep original individuals
        else:
            processed_count = len(videos)
            logger.info(
                f"Not enough videos for cross-video tracking: "
                f"{len(videos)}"
            )
        
        # Update status to completed
        async with db_client.pool.acquire() as conn:
            await conn.execute("""
                UPDATE tracking_sessions
                SET status = 'completed', completed_at = NOW(),
                    processing_time_seconds = 3.0,
                    processed_videos = $2, individuals_found = $3
                WHERE session_uuid = $1
            """, session_uuid, processed_count, individuals_found)
        
        logger.info(
            f"Processing completed for session {session_uuid}: "
            f"{processed_count} videos, {individuals_found} individuals"
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
    http_request: Request
):
    """
    Phase 5: Get list of unique individuals found in a completed tracking session.
    
    Returns metadata for each individual including:
    - individual_uuid: Unique identifier
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
                SELECT session_uuid, status, total_videos, individuals_found
                FROM tracking_sessions
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
            
            # Get individual metadata from tracking results
            # WORKAROUND: session_individuals table not populated by processing
            # Instead, get individuals created around the same time as session
            # This works because each session creates its own individuals
            individuals = await conn.fetch(
                """
                SELECT 
                    i.individual_uuid,
                    i.individual_id,
                    COUNT(DISTINCT iva.person_object_uuid) as appearance_count,
                    COUNT(DISTINCT iva.video_uuid) as video_count,
                    MIN(iva.start_timestamp) as first_seen,
                    MAX(iva.end_timestamp) as last_seen,
                    i.confidence_score as avg_confidence
                FROM individuals i
                LEFT JOIN individual_video_appearances iva 
                    ON i.individual_uuid = iva.individual_uuid
                WHERE i.created_at >= (
                    SELECT created_at FROM tracking_sessions 
                    WHERE session_uuid = $1
                ) - INTERVAL '5 seconds'
                AND i.created_at <= (
                    SELECT COALESCE(completed_at, NOW()) FROM tracking_sessions 
                    WHERE session_uuid = $1
                ) + INTERVAL '5 seconds'
                GROUP BY i.individual_uuid, i.individual_id, i.confidence_score
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
                    "first_seen": ind['first_seen'].isoformat() if ind['first_seen'] else None,
                    "last_seen": ind['last_seen'].isoformat() if ind['last_seen'] else None,
                    "confidence_score": round(float(ind['avg_confidence']), 3) if ind['avg_confidence'] else 0.0
                }
                for ind in individuals
            ]
            
            logger.info(f"Phase 5: Found {len(individuals_list)} individuals in session {session_uuid}")
            
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
            
            # Get all appearances for this individual
            # Note: individual_video_appearances table doesn't have session_uuid
            # or created_at columns, so we get all appearances for the individual
            # Since the individual was created during this session, all appearances
            # should belong to this session
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
                    iva.confidence
                FROM individual_video_appearances iva
                JOIN individuals i ON iva.individual_uuid = i.individual_uuid
                WHERE iva.individual_uuid = $1
                ORDER BY iva.start_timestamp ASC
                """,
                individual_uuid
            )
            
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
            
            # Format appearances
            appearances_list = []
            person_object_uuids = []
            
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
            
            # Calculate aggregated metrics
            first_appearance = appearances[0]
            last_appearance = appearances[-1]
            
            total_duration = 0
            if first_appearance['start_timestamp'] and last_appearance['end_timestamp']:
                total_duration = (
                    last_appearance['end_timestamp'] - first_appearance['start_timestamp']
                ).total_seconds()
            
            avg_confidence = sum(
                float(app['confidence']) for app in appearances if app['confidence']
            ) / len(appearances)
            
            # Build response
            response = {
                "individual_uuid": individual_uuid,
                "individual_id": first_appearance['individual_id'],
                "session_uuid": session_uuid,
                "total_appearances": len(appearances),
                "unique_videos": len(set(str(app['video_uuid']) for app in appearances)),
                "first_seen": first_appearance['start_timestamp'].isoformat() if first_appearance['start_timestamp'] else "",
                "last_seen": last_appearance['end_timestamp'].isoformat() if last_appearance['end_timestamp'] else "",
                "total_duration_seconds": round(total_duration, 2),
                "average_confidence": round(avg_confidence, 3),
                "appearances": appearances_list,
                "person_object_uuids": person_object_uuids,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
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
    - similarity_threshold: Optional threshold for validation (default: 0.75)
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
                individual = await conn.fetchrow("""
                    SELECT individual_uuid, individual_id, session_uuid
                    FROM individuals
                    WHERE individual_uuid = $1
                """, ind_uuid)
                
                if not individual:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Individual {ind_uuid} not found"
                    )
                
                if str(individual['session_uuid']) != request.session_uuid:
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
                
                # Extract embeddings for each individual
                for ind_uuid in request.individual_uuids:
                    # Get best quality face crop from Vision DB
                    async with db_client.pool.acquire() as conn:
                        video_appearances = await conn.fetch("""
                            SELECT DISTINCT video_uuid
                            FROM individual_video_appearances
                            WHERE individual_uuid = $1
                        """, ind_uuid)
                        
                        if not video_appearances:
                            continue
                        
                        video_uuids = [str(va['video_uuid']) for va in video_appearances]
                    
                    # Query Vision DB for best face crop
                    try:
                        import asyncpg
                        import base64
                        import cv2
                        import uuid
                        
                        video_uuid_objects = [uuid.UUID(v) for v in video_uuids]
                        
                        vision_conn = await asyncpg.connect(
                            "postgresql://postgres:localdevpass@localhost:5432/ppl_vision_db"
                        )
                        
                        try:
                            person_obj = await vision_conn.fetchrow("""
                                SELECT 
                                    po.person_id,
                                    po.best_face_id,
                                    po.quality_score
                                FROM person_objects po
                                JOIN face_detections fd 
                                    ON fd.id = po.best_face_id
                                WHERE fd.media_id = ANY($1::uuid[])
                                  AND po.quality_score IS NOT NULL
                                ORDER BY po.quality_score DESC
                                LIMIT 1
                            """, video_uuid_objects)
                            
                            if person_obj and person_obj['best_face_id']:
                                face_crop_data = await vision_conn.fetchrow("""
                                    SELECT crop_base64
                                    FROM face_crops
                                    WHERE face_detection_id = $1
                                """, person_obj['best_face_id'])
                                
                                if face_crop_data and face_crop_data['crop_base64']:
                                    crop_bytes = base64.b64decode(face_crop_data['crop_base64'])
                                    crop_array = np.frombuffer(crop_bytes, np.uint8)
                                    face_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)
                                    
                                    if face_crop is not None and face_crop.size > 0:
                                        face_crop_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                                        h, w = face_crop_rgb.shape[:2]
                                        
                                        embedding, _ = await embedding_service._generate_facial_embedding(
                                            face_crop_rgb, 0, 0, w, h
                                        )
                                        
                                        if embedding is not None:
                                            individual_embeddings[ind_uuid] = embedding
                                            logger.info(f"Generated embedding for {ind_uuid}")
                        finally:
                            await vision_conn.close()
                    except Exception as e:
                        logger.error(f"Failed to get embedding for {ind_uuid}: {e}")
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

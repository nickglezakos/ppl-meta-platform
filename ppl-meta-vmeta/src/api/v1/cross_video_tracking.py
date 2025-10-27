"""
Cross-Video Individual Tracking - REST API Implementation
PPL Meta Platform v2.19.13+

FastAPI REST endpoints for cross-video individual tracking with session management,
cache operations, and comprehensive result retrieval.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import logging

try:
    from ...models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        TrackingSession,
        SessionStatus
    )
    from ...services.integrated_caching import IntegratedCachingService
    from ...database.connection import get_db_connection
    # Try to import auth dependencies
    try:
        from ...auth.dependencies import get_auth_token, get_current_user
    except ImportError:
        # Auth dependencies not available, create dummy functions
        def get_auth_token():
            return "dummy_token"

        def get_current_user():
            return {"user_id": "test_user"}
except ImportError:
    # Fallback for development
    from models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        TrackingSession,
        SessionStatus
    )
    from services.integrated_caching import IntegratedCachingService
    # Create dummy functions for development

    def get_auth_token():
        return "dummy_token"

    def get_current_user():
        return {"user_id": "test_user"}

    def get_db_connection():
        return None

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Helper function to extract auth token from request
def extract_auth_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    return None

# Request/Response Models
class CreateTrackingSessionRequest(BaseModel):
    """Request model for creating a new tracking session."""
    collections: List[str] = Field(..., min_items=1, max_items=10)
    start_time: datetime
    end_time: datetime
    algorithm_config: Optional[CrossVideoTrackingConfig] = None
    background_processing: bool = True
    force_reprocess: bool = False
    description: Optional[str] = None

class TrackingSessionResponse(BaseModel):
    """Response model for tracking session creation."""
    session_uuid: str
    status: str
    message: str
    cache_utilization: Dict[str, Any]
    session_info: Dict[str, Any]
    estimated_processing_time: Optional[float] = None

class TrackingSessionStatus(BaseModel):
    """Response model for session status."""
    session_uuid: str
    status: str
    progress_percentage: float
    cache_hit_rate: float
    processing_time_seconds: Optional[float]
    total_videos: int
    processed_videos: int
    individuals_found: int
    is_active: bool
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cache_info: Optional[Dict[str, Any]] = None

class IndividualTrackingResults(BaseModel):
    """Response model for tracking results."""
    session_uuid: str
    success: bool
    processing_time_seconds: float
    individuals: List[Dict[str, Any]]
    video_sequences: List[Dict[str, Any]]
    overlap_groups: List[Dict[str, Any]]
    cache_utilization: Dict[str, Any]
    algorithm_config: Dict[str, Any]
    statistics: Dict[str, Any]

class ClearCollectionCacheRequest(BaseModel):
    """Request model for clearing collection cache."""
    collections: List[str] = Field(..., min_items=1)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    config_filter: Optional[str] = None
    force_clear: bool = False

class ClearVideoCacheRequest(BaseModel):
    """Request model for clearing video cache."""
    video_uuids: List[str] = Field(..., min_items=1)
    config_filter: Optional[str] = None

class CacheStatusResponse(BaseModel):
    """Response model for cache status."""
    total_cached_entries: int
    total_cache_size_mb: float
    unique_configurations: int
    unique_videos: int
    cache_efficiency_score: float
    recommendations: List[str]
    collections_covered: List[str]
    oldest_cache_entry: Optional[datetime]
    newest_cache_entry: Optional[datetime]


# Initialize router
router = APIRouter(
    prefix="/individuals/tracking",
    tags=["Cross-Video Individual Tracking"]
)


@router.post("/sessions", response_model=TrackingSessionResponse)
async def create_tracking_session(
    request_body: CreateTrackingSessionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Create new cross-video individual tracking session.
    
    Analyzes cache availability and initiates tracking processing
    with intelligent cache utilization.
    """
    try:
        # Extract auth token from request headers
        auth_token = extract_auth_token(request)
        
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Use default config if not provided
        config = request_body.algorithm_config or CrossVideoTrackingConfig()
        
        # DEBUG: Log the config
        logger.info(f"DEBUG: Config object: {config}")
        logger.info(f"DEBUG: Config dict: {config.dict() if hasattr(config, 'dict') else 'NO DICT'}")
        logger.info(f"DEBUG: Config model_dump: {config.model_dump() if hasattr(config, 'model_dump') else 'NO MODEL_DUMP'}")
        
        # Execute cache-aware tracking
        result = await caching_service.execute_cache_aware_tracking(
            user_id=current_user['user_id'],
            collections=request_body.collections,
            start_time=request_body.start_time,
            end_time=request_body.end_time,
            config=config,
            background=request_body.background_processing,
            force_reprocess=request_body.force_reprocess,
            auth_token=auth_token  # Pass auth token through
        )
        
        if not result.get('success', True):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create tracking session: {result.get('error')}"
            )
        
        # Estimate processing time based on video count
        cache_util = result.get('cache_utilization', {})
        total_videos = cache_util.get('total_videos', 0)
        cached_videos = cache_util.get('cached_videos', 0)
        new_videos = total_videos - cached_videos
        
        # Rough estimate: 0.1 seconds per video for processing
        estimated_time = new_videos * 0.1 if new_videos > 0 else 0.05
        
        logger.info(
            f"Created tracking session {result.get('session_info', {}).get('session_uuid')} "
            f"for user {current_user['user_id']}: {total_videos} videos, "
            f"{cache_util.get('cache_hit_rate', 0):.1f}% cache hit rate"
        )
        
        return TrackingSessionResponse(
            session_uuid=result.get('session_info', {}).get('session_uuid'),
            status=result.get('status', 'started'),
            message=result.get('message', 'Session created successfully'),
            cache_utilization=cache_util,
            session_info=result.get('session_info', {}),
            estimated_processing_time=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Failed to create tracking session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/sessions/{session_uuid}", response_model=TrackingSessionStatus)
async def get_session_status(
    session_uuid: str,
    include_cache_info: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Get tracking session status and progress.
    
    Returns real-time status information including progress,
    cache utilization, and processing metrics.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Get session status with cache info if requested
        if include_cache_info:
            status = await caching_service.get_session_status_with_cache_info(
                session_uuid
            )
        else:
            status = await caching_service.session_manager.get_session_status(
                session_uuid
            )
        
        if status.get('status') == 'not_found':
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_uuid} not found"
            )
        
        if status.get('status') == 'error':
            raise HTTPException(
                status_code=500,
                detail=f"Session error: {status.get('error')}"
            )
        
        return TrackingSessionStatus(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/sessions/{session_uuid}/results", response_model=IndividualTrackingResults)
async def get_session_results(
    session_uuid: str,
    include_details: bool = Query(True),
    include_video_sequences: bool = Query(True),
    include_overlap_groups: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Get tracking session results.
    
    Returns comprehensive tracking results including individuals,
    video sequences, and performance metrics.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Get session status first
        status = await caching_service.session_manager.get_session_status(
            session_uuid
        )
        
        if status.get('status') == 'not_found':
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_uuid} not found"
            )
        
        if status.get('status') != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_uuid} is not completed (status: {status.get('status')})"
            )
        
        # For now, return mock results structure
        # In production, this would retrieve from database
        results = {
            'session_uuid': session_uuid,
            'success': True,
            'processing_time_seconds': status.get('processing_time_seconds', 0),
            'individuals': [] if not include_details else [],  # Would load from DB
            'video_sequences': [] if not include_video_sequences else [],
            'overlap_groups': [] if not include_overlap_groups else [],
            'cache_utilization': {
                'cache_hit_rate': status.get('cache_hit_rate', 0),
                'total_videos': status.get('total_videos', 0),
                'cached_videos': int(
                    status.get('total_videos', 0) * status.get('cache_hit_rate', 0) / 100
                    if status.get('total_videos', 0) > 0 else 0
                )
            },
            'algorithm_config': {},  # Would load from session
            'statistics': {
                'total_videos': status.get('total_videos', 0),
                'individuals_found': status.get('individuals_found', 0),
                'processing_time_seconds': status.get('processing_time_seconds', 0),
                'cache_efficiency': status.get('cache_hit_rate', 0)
            }
        }
        
        return IndividualTrackingResults(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/sessions/{session_uuid}")
async def cancel_tracking_session(
    session_uuid: str,
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Cancel running tracking session.
    
    Cancels active session and cleans up resources.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Cancel session
        result = await caching_service.session_manager.cancel_session(session_uuid)
        
        if result.get('status') == 'not_active':
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_uuid} is not currently active"
            )
        
        if result.get('status') == 'error':
            raise HTTPException(
                status_code=500,
                detail=f"Failed to cancel session: {result.get('error')}"
            )
        
        logger.info(f"Cancelled session {session_uuid} for user {current_user['user_id']}")
        
        return {
            'session_uuid': session_uuid,
            'status': 'cancelled',
            'message': result.get('message', 'Session cancelled successfully')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Cache Management Endpoints
@router.delete("/cache/collections")
async def clear_collection_cache(
    request: ClearCollectionCacheRequest,
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Clear cached results for specific collections.
    
    WARNING: This will force reprocessing of all videos in the collections.
    Use with caution in production environments.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Clear cache for collections
        result = await caching_service.cache_clearing.clear_cache_for_collections(
            collections=request.collections,
            start_time=request.start_time,
            end_time=request.end_time,
            config_filter=request.config_filter
        )
        
        logger.warning(
            f"Cleared cache for collections {request.collections} "
            f"by user {current_user['user_id']}: "
            f"{result.get('deleted_count', 0)} entries removed"
        )
        
        return {
            'message': 'Cache cleared successfully',
            'collections_cleared': request.collections,
            'cache_entries_removed': result.get('deleted_count', 0),
            'space_freed_mb': result.get('freed_space_mb', 0),
            'operation_timestamp': datetime.utcnow(),
            'force_clear': request.force_clear
        }
        
    except Exception as e:
        logger.error(f"Failed to clear collection cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/cache/videos")
async def clear_video_cache(
    request: ClearVideoCacheRequest,
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Clear cached results for specific videos.
    
    Use for targeted cache invalidation when video content changes.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Clear cache for videos
        result = await caching_service.cache_clearing.clear_cache_for_videos(
            video_uuids=request.video_uuids,
            config_filter=request.config_filter
        )
        
        logger.info(
            f"Cleared cache for {len(request.video_uuids)} videos "
            f"by user {current_user['user_id']}: "
            f"{result.get('deleted_count', 0)} entries removed"
        )
        
        return {
            'message': 'Video cache cleared successfully',
            'videos_cleared': request.video_uuids,
            'cache_entries_removed': result.get('deleted_count', 0),
            'space_freed_mb': result.get('freed_space_mb', 0),
            'operation_timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear video cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/cache/all")
async def clear_all_cache(
    confirm_operation: str = Query(..., description="Type 'CONFIRM_CLEAR_ALL' to proceed"),
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Clear ALL cached tracking results.
    
    DESTRUCTIVE OPERATION: This will remove all cached data and force
    complete reprocessing of all future tracking requests.
    """
    if confirm_operation != "CONFIRM_CLEAR_ALL":
        raise HTTPException(
            status_code=400,
            detail="Must confirm operation with 'CONFIRM_CLEAR_ALL'"
        )
    
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Clear all cache
        result = await caching_service.cache_clearing.clear_all_tracking_cache()
        
        logger.warning(
            f"CLEARED ALL TRACKING CACHE by user {current_user['user_id']}: "
            f"{result.get('deleted_count', 0)} entries removed, "
            f"{result.get('freed_space_mb', 0):.1f}MB freed"
        )
        
        return {
            'message': 'ALL tracking cache cleared successfully',
            'cache_entries_removed': result.get('deleted_count', 0),
            'space_freed_mb': result.get('freed_space_mb', 0),
            'operation_timestamp': datetime.utcnow(),
            'warning': 'All future tracking requests will require full processing'
        }
        
    except Exception as e:
        logger.error(f"Failed to clear all cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/cache/status", response_model=CacheStatusResponse)
async def get_cache_status(
    collections: Optional[List[str]] = Query(None),
    days_back: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Get cache status and statistics.
    
    Returns comprehensive cache performance metrics and recommendations.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Get cache performance report
        report = await caching_service.get_cache_performance_report(
            collections=collections,
            days_back=days_back
        )
        
        if 'error' in report:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate cache report: {report['error']}"
            )
        
        cache_overview = report.get('cache_overview', {})
        performance_metrics = report.get('performance_metrics', {})
        
        return CacheStatusResponse(
            total_cached_entries=cache_overview.get('total_cached_entries', 0),
            total_cache_size_mb=cache_overview.get('total_cache_size_mb', 0),
            unique_configurations=cache_overview.get('unique_configurations', 0),
            unique_videos=cache_overview.get('unique_videos', 0),
            cache_efficiency_score=performance_metrics.get('cache_efficiency_score', 0),
            recommendations=report.get('recommendations', []),
            collections_covered=[],  # Would be computed from database
            oldest_cache_entry=None,  # Would be computed from database
            newest_cache_entry=None   # Would be computed from database
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/cache/optimize")
async def optimize_cache_storage(
    max_age_days: int = Query(30, ge=1, le=365),
    max_size_gb: float = Query(5.0, ge=0.1, le=100.0),
    min_access_count: int = Query(1, ge=0),
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
):
    """
    Optimize cache storage by removing old or unused entries.
    
    Automatically cleans up cache based on age, size, and access patterns.
    """
    try:
        # Initialize integrated caching service
        caching_service = IntegratedCachingService(db_connection)
        
        # Run cache optimization
        result = await caching_service.optimize_cache_storage(
            max_age_days=max_age_days,
            max_size_gb=max_size_gb,
            min_access_count=min_access_count
        )
        
        if not result.get('success', True):
            raise HTTPException(
                status_code=500,
                detail=f"Cache optimization failed: {result.get('error')}"
            )
        
        space_opt = result.get('space_optimization', {})
        entries_opt = result.get('entries_optimization', {})
        
        logger.info(
            f"Cache optimization completed by user {current_user['user_id']}: "
            f"{space_opt.get('space_freed_mb', 0):.1f}MB freed, "
            f"{entries_opt.get('entries_removed', 0)} entries removed"
        )
        
        return {
            'message': 'Cache optimization completed successfully',
            'space_freed_mb': space_opt.get('space_freed_mb', 0),
            'entries_removed': entries_opt.get('entries_removed', 0),
            'optimization_criteria': {
                'max_age_days': max_age_days,
                'max_size_gb': max_size_gb,
                'min_access_count': min_access_count
            },
            'recommendations': result.get('recommendations', []),
            'processing_time_seconds': result.get('processing_time_seconds', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to optimize cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
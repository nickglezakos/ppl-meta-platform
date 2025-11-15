"""
Batch Processing API Endpoints

REST API for continuous individuals and MVR pipeline batch processing.
Provides endpoints for monitoring, configuration, and manual control.

Author: PPL Meta Platform
Date: November 13, 2025
Version: 1.0.0
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator

from api.dependencies import get_current_user
from database.batch_repository import BatchProcessingRepository
from services.batch_monitor import BatchMonitor
from services.hybrid_batch_trigger import HybridBatchTrigger
from services.pipeline_executor import PipelineExecutor

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class BatchStatusResponse(BaseModel):
    """Response model for batch status."""
    
    batch_uuid: str
    collection_id: str
    batch_number: int
    status: str
    video_count: int
    batch_size_threshold: int
    is_partial_batch: bool
    trigger_reason: Optional[str] = None
    created_at: datetime
    triggered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    
    # Processing metrics
    individuals_created: Optional[int] = None
    individuals_cached: Optional[int] = None
    mvr_people_created: Optional[int] = None
    mvr_people_cached: Optional[int] = None
    cache_hit_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class BatchHistoryItem(BaseModel):
    """Response model for batch history item."""
    
    batch_uuid: str
    collection_id: str
    video_count: int
    status: str
    is_partial_batch: bool
    trigger_reason: Optional[str] = None
    
    # Processing results
    individuals_created: int
    individuals_cached: int
    mvr_people_created: int
    mvr_people_cached: int
    cache_hit_rate: Optional[float] = None
    throughput_videos_per_sec: Optional[float] = None
    
    # Timing
    batch_start_time: datetime
    batch_end_time: datetime
    processing_time_seconds: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class BatchHistoryResponse(BaseModel):
    """Response model for batch history list."""
    
    total: int
    limit: int
    offset: int
    batches: List[BatchHistoryItem]


class TriggerBatchRequest(BaseModel):
    """Request model for manual batch trigger."""
    
    collection_id: str = Field(..., description="Collection ID to trigger batch for")
    force_trigger: bool = Field(
        default=False,
        description="Force trigger even if below minimum size"
    )
    min_videos: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Minimum videos required (overrides config)"
    )


class TriggerBatchResponse(BaseModel):
    """Response model for batch trigger."""
    
    batch_uuid: str
    collection_id: str
    status: str
    video_count: int
    triggered_at: datetime
    message: str


class BatchConfigResponse(BaseModel):
    """Response model for batch configuration."""
    
    batch_size_threshold: int = Field(ge=2, le=50)
    partial_batch_min_videos: int = Field(ge=1, le=50)
    partial_batch_timeout_minutes: int = Field(ge=1, le=1440)
    max_concurrent_batches: int = Field(ge=1, le=20)
    
    # Event configuration
    event_triggering_enabled: bool
    polling_interval_seconds: int
    
    # Resource limits
    worker_pool_size: int
    max_batch_memory_gb: int
    max_batch_processing_time_seconds: int


class UpdateConfigRequest(BaseModel):
    """Request model for updating batch configuration."""
    
    batch_size_threshold: Optional[int] = Field(None, ge=2, le=50)
    partial_batch_min_videos: Optional[int] = Field(None, ge=1, le=50)
    partial_batch_timeout_minutes: Optional[int] = Field(None, ge=1, le=1440)
    max_concurrent_batches: Optional[int] = Field(None, ge=1, le=20)
    
    @validator('partial_batch_min_videos')
    def validate_min_videos(cls, v, values):
        """Ensure min_videos < batch_size_threshold."""
        if v is not None and 'batch_size_threshold' in values:
            batch_size = values.get('batch_size_threshold')
            if batch_size is not None and v >= batch_size:
                raise ValueError(
                    f"partial_batch_min_videos ({v}) must be less than "
                    f"batch_size_threshold ({batch_size})"
                )
        return v


class UpdateConfigResponse(BaseModel):
    """Response model for configuration update."""
    
    message: str
    config: BatchConfigResponse
    effective_at: datetime


class UpdateBatchSizeRequest(BaseModel):
    """Request model for updating batch size."""
    
    batch_size: int = Field(..., ge=2, le=50, description="Number of videos per batch")
    collection_id: Optional[str] = Field(
        None,
        description="Apply to specific collection only (omit for global)"
    )


class UpdateBatchSizeResponse(BaseModel):
    """Response model for batch size update."""
    
    message: str
    batch_size: int
    collection_id: Optional[str]
    scope: str  # "collection" or "global"
    previous_batch_size: int
    effective_at: datetime
    current_batch_status: Optional[Dict[str, Any]] = None


class IncompleteBatch(BaseModel):
    """Model for incomplete batch information."""
    
    batch_uuid: str
    collection_id: str
    video_count: int
    batch_size_threshold: int
    videos_needed: int
    last_video_time: Optional[datetime]
    timeout_at: Optional[datetime]
    created_at: datetime


class IncompleteBatchesResponse(BaseModel):
    """Response model for incomplete batches."""
    
    total_incomplete: int
    incomplete_batches: List[IncompleteBatch]


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    
    status: str
    worker_pool: Dict[str, Any]
    active_batches: List[Dict[str, Any]]
    recent_failures: int
    uptime_seconds: float
    database_connected: bool
    event_subscription_status: Dict[str, Any]


# ============================================================================
# Dependency Injection
# ============================================================================

# These will be set at startup
_batch_repository: Optional[BatchProcessingRepository] = None
_batch_monitor: Optional[BatchMonitor] = None
_hybrid_trigger: Optional[HybridBatchTrigger] = None
_pipeline_executor: Optional[PipelineExecutor] = None


def set_batch_services(
    repository: BatchProcessingRepository,
    monitor: BatchMonitor,
    trigger: Optional[HybridBatchTrigger],  # Made optional
    executor: PipelineExecutor
):
    """Initialize batch processing services (called at startup)."""
    global _batch_repository, _batch_monitor, _hybrid_trigger, _pipeline_executor
    _batch_repository = repository
    _batch_monitor = monitor
    _hybrid_trigger = trigger
    _pipeline_executor = executor


def get_batch_repository() -> BatchProcessingRepository:
    """Dependency for batch repository."""
    if _batch_repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch processing service not initialized"
        )
    return _batch_repository


def get_batch_monitor() -> BatchMonitor:
    """Dependency for batch monitor."""
    if _batch_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch monitor not initialized"
        )
    return _batch_monitor


def get_hybrid_trigger() -> HybridBatchTrigger:
    """Dependency for hybrid trigger."""
    if _hybrid_trigger is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hybrid trigger not initialized"
        )
    return _hybrid_trigger


def get_pipeline_executor() -> PipelineExecutor:
    """Dependency for pipeline executor."""
    if _pipeline_executor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline executor not initialized"
        )
    return _pipeline_executor


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/status",
    response_model=List[BatchStatusResponse],
    summary="Get Batch Processing Status",
    description="Get current status of all batch processing operations",
    tags=["Batch Processing"]
)
async def get_batch_status(
    collection_id: Optional[str] = Query(None, description="Filter by collection ID"),
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository)
) -> List[BatchStatusResponse]:
    """
    Get current status of batch processing.
    
    Returns details of all active and recently completed batches.
    Optionally filter by collection_id.
    """
    try:
        # Get active batches
        query = """
            SELECT 
                batch_uuid,
                collection_id,
                batch_number,
                status,
                video_count,
                batch_size_threshold,
                is_partial_batch,
                trigger_reason,
                created_at,
                triggered_at,
                completed_at,
                processing_time_seconds,
                individuals_created,
                individuals_cached,
                mvr_people_created,
                mvr_people_cached
            FROM batch_processing_state
            WHERE status IN ('accumulating', 'processing', 'completed')
        """
        
        params = []
        if collection_id:
            query += " AND collection_id = $1"
            params.append(collection_id)
        
        query += " ORDER BY created_at DESC LIMIT 20"
        
        async with repository.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        batches = []
        for row in rows:
            # Calculate cache hit rate
            cache_hit_rate = None
            if row['individuals_created'] is not None and row['individuals_cached'] is not None:
                total = row['individuals_created'] + row['individuals_cached']
                if total > 0:
                    cache_hit_rate = (row['individuals_cached'] / total) * 100
            
            batches.append(BatchStatusResponse(
                batch_uuid=str(row['batch_uuid']),
                collection_id=row['collection_id'],
                batch_number=row['batch_number'],
                status=row['status'],
                video_count=row['video_count'],
                batch_size_threshold=row['batch_size_threshold'],
                is_partial_batch=row['is_partial_batch'] or False,
                trigger_reason=row['trigger_reason'],
                created_at=row['created_at'],
                triggered_at=row['triggered_at'],
                completed_at=row['completed_at'],
                processing_time_seconds=row['processing_time_seconds'],
                individuals_created=row['individuals_created'],
                individuals_cached=row['individuals_cached'],
                mvr_people_created=row['mvr_people_created'],
                mvr_people_cached=row['mvr_people_cached'],
                cache_hit_rate=cache_hit_rate
            ))
        
        logger.info(f"Retrieved {len(batches)} batch statuses for user {user.get('email')}")
        return batches
        
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch status: {str(e)}"
        )


@router.get(
    "/history",
    response_model=BatchHistoryResponse,
    summary="Get Batch Processing History",
    description="Get historical data of completed batch processing operations",
    tags=["Batch Processing"]
)
async def get_batch_history(
    collection_id: Optional[str] = Query(None, description="Filter by collection ID"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository)
) -> BatchHistoryResponse:
    """
    Get batch processing history with pagination.
    
    Returns historical data of completed batches including processing metrics.
    """
    try:
        # Build query
        count_query = "SELECT COUNT(*) FROM batch_processing_history"
        data_query = """
            SELECT 
                batch_uuid,
                collection_id,
                video_count,
                status,
                is_partial_batch,
                trigger_reason,
                individuals_created,
                individuals_cached,
                mvr_people_created,
                mvr_people_cached,
                cache_hit_rate,
                throughput_videos_per_sec,
                batch_start_time,
                batch_end_time,
                processing_time_seconds,
                created_at
            FROM batch_processing_history
        """
        
        params = []
        param_count = 0
        
        where_clause = ""
        if collection_id:
            param_count += 1
            where_clause = f" WHERE collection_id = ${param_count}"
            params.append(collection_id)
        
        count_query += where_clause
        data_query += where_clause
        data_query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])
        
        async with repository.pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params[:-2] if collection_id else [])
            rows = await conn.fetch(data_query, *params)
        
        batches = [
            BatchHistoryItem(
                batch_uuid=str(row['batch_uuid']),
                collection_id=row['collection_id'],
                video_count=row['video_count'],
                status=row['status'],
                is_partial_batch=row['is_partial_batch'] or False,
                trigger_reason=row['trigger_reason'],
                individuals_created=row['individuals_created'],
                individuals_cached=row['individuals_cached'],
                mvr_people_created=row['mvr_people_created'],
                mvr_people_cached=row['mvr_people_cached'],
                cache_hit_rate=row['cache_hit_rate'],
                throughput_videos_per_sec=row['throughput_videos_per_sec'],
                batch_start_time=row['batch_start_time'],
                batch_end_time=row['batch_end_time'],
                processing_time_seconds=row['processing_time_seconds'],
                created_at=row['created_at']
            )
            for row in rows
        ]
        
        logger.info(
            f"Retrieved {len(batches)} batch history items (total: {total}) "
            f"for user {user.get('email')}"
        )
        
        return BatchHistoryResponse(
            total=total,
            limit=limit,
            offset=offset,
            batches=batches
        )
        
    except Exception as e:
        logger.error(f"Failed to get batch history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch history: {str(e)}"
        )


@router.post(
    "/trigger",
    response_model=TriggerBatchResponse,
    summary="Trigger Batch Processing",
    description="Manually trigger batch processing for a collection",
    tags=["Batch Processing"]
)
async def trigger_batch(
    request: TriggerBatchRequest,
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository),
    monitor: BatchMonitor = Depends(get_batch_monitor)
) -> TriggerBatchResponse:
    """
    Manually trigger batch processing.
    
    Useful for development, testing, or manual recovery scenarios.
    """
    try:
        # Get current batch
        batch = await repository.get_active_batch(request.collection_id)
        
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active batch found for collection '{request.collection_id}'"
            )
        
        video_count = batch['video_count']
        min_videos = request.min_videos or batch['partial_batch_min_videos'] or 2
        
        # Check if batch meets minimum requirements
        if not request.force_trigger and video_count < min_videos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Batch has only {video_count} videos, "
                    f"minimum is {min_videos}. "
                    f"Use force_trigger=true to override."
                )
            )
        
        # Trigger batch
        batch_uuid = batch['batch_uuid']
        await monitor.trigger_batch(
            batch_uuid=batch_uuid,
            trigger_reason='manual',
            is_partial=(video_count < batch['batch_size_threshold'])
        )
        
        logger.info(
            f"Manually triggered batch {batch_uuid} for collection "
            f"{request.collection_id} with {video_count} videos "
            f"(user: {user.get('email')})"
        )
        
        return TriggerBatchResponse(
            batch_uuid=str(batch_uuid),
            collection_id=request.collection_id,
            status="processing",
            video_count=video_count,
            triggered_at=datetime.utcnow(),
            message="Batch processing triggered successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger batch: {str(e)}"
        )


@router.get(
    "/config",
    response_model=BatchConfigResponse,
    summary="Get Batch Configuration",
    description="Get current batch processing configuration",
    tags=["Batch Processing"]
)
async def get_batch_config(
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository)
) -> BatchConfigResponse:
    """
    Get current batch processing configuration.
    
    Returns global configuration settings.
    """
    try:
        config = await repository.get_batch_config(collection_id=None)
        
        if not config:
            # Return default config
            return BatchConfigResponse(
                batch_size_threshold=5,
                partial_batch_min_videos=2,
                partial_batch_timeout_minutes=10,
                max_concurrent_batches=3,
                event_triggering_enabled=True,
                polling_interval_seconds=30,
                worker_pool_size=3,
                max_batch_memory_gb=2,
                max_batch_processing_time_seconds=300
            )
        
        logger.info(f"Retrieved batch config for user {user.get('email')}")
        
        return BatchConfigResponse(
            batch_size_threshold=config['batch_size_threshold'],
            partial_batch_min_videos=config.get('partial_batch_min_videos', 2),
            partial_batch_timeout_minutes=config.get('partial_batch_timeout_minutes', 10),
            max_concurrent_batches=config.get('max_concurrent_batches', 3),
            event_triggering_enabled=True,
            polling_interval_seconds=30,
            worker_pool_size=3,
            max_batch_memory_gb=2,
            max_batch_processing_time_seconds=300
        )
        
    except Exception as e:
        logger.error(f"Failed to get batch config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.put(
    "/config",
    response_model=UpdateConfigResponse,
    summary="Update Batch Configuration",
    description="Update batch processing configuration settings",
    tags=["Batch Processing"]
)
async def update_batch_config(
    request: UpdateConfigRequest,
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository)
) -> UpdateConfigResponse:
    """
    Update batch processing configuration.
    
    Updates global configuration settings. Changes take effect immediately.
    """
    try:
        # Get current config
        current_config = await repository.get_batch_config(collection_id=None)
        
        # Build update dict
        updates = {}
        if request.batch_size_threshold is not None:
            updates['batch_size_threshold'] = request.batch_size_threshold
        if request.partial_batch_min_videos is not None:
            updates['partial_batch_min_videos'] = request.partial_batch_min_videos
        if request.partial_batch_timeout_minutes is not None:
            updates['partial_batch_timeout_minutes'] = request.partial_batch_timeout_minutes
        if request.max_concurrent_batches is not None:
            updates['max_concurrent_batches'] = request.max_concurrent_batches
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No configuration updates provided"
            )
        
        # Update config in database
        async with repository.pool.acquire() as conn:
            # Update or insert
            set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(updates.keys())])
            values = list(updates.values())
            
            await conn.execute(
                f"""
                INSERT INTO batch_processing_config 
                    (collection_id, {', '.join(updates.keys())}, updated_at)
                VALUES (NULL, {', '.join([f'${i+1}' for i in range(len(updates))])}, NOW())
                ON CONFLICT (collection_id) 
                DO UPDATE SET {set_clause}, updated_at = NOW()
                """,
                *values, *values
            )
        
        # Get updated config
        new_config = await repository.get_batch_config(collection_id=None)
        
        logger.info(
            f"Updated batch config: {updates} (user: {user.get('email')})"
        )
        
        return UpdateConfigResponse(
            message="Configuration updated successfully",
            config=BatchConfigResponse(
                batch_size_threshold=new_config['batch_size_threshold'],
                partial_batch_min_videos=new_config.get('partial_batch_min_videos', 2),
                partial_batch_timeout_minutes=new_config.get('partial_batch_timeout_minutes', 10),
                max_concurrent_batches=new_config.get('max_concurrent_batches', 3),
                event_triggering_enabled=True,
                polling_interval_seconds=30,
                worker_pool_size=3,
                max_batch_memory_gb=2,
                max_batch_processing_time_seconds=300
            ),
            effective_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.put(
    "/batch-size",
    response_model=UpdateBatchSizeResponse,
    summary="Update Batch Size",
    description="Quick endpoint to update the number of videos per batch",
    tags=["Batch Processing"]
)
async def update_batch_size(
    request: UpdateBatchSizeRequest,
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository)
) -> UpdateBatchSizeResponse:
    """
    Update batch size threshold.
    
    Quick endpoint to update just the batch size without changing other settings.
    Changes take effect immediately for new videos added to batches.
    """
    try:
        # Get current config
        current_config = await repository.get_batch_config(
            collection_id=request.collection_id
        )
        
        previous_size = current_config['batch_size_threshold'] if current_config else 5
        
        # Update batch size
        async with repository.pool.acquire() as conn:
            if request.collection_id:
                # Collection-specific update
                await conn.execute(
                    """
                    INSERT INTO batch_processing_config 
                        (collection_id, batch_size_threshold, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (collection_id) 
                    DO UPDATE SET batch_size_threshold = $2, updated_at = NOW()
                    """,
                    request.collection_id,
                    request.batch_size
                )
                
                # Update active batches for this collection
                await conn.execute(
                    """
                    UPDATE batch_processing_state
                    SET batch_size_threshold = $1
                    WHERE collection_id = $2 AND status = 'accumulating'
                    """,
                    request.batch_size,
                    request.collection_id
                )
                
                scope = "collection"
            else:
                # Global update
                await conn.execute(
                    """
                    INSERT INTO batch_processing_config 
                        (collection_id, batch_size_threshold, updated_at)
                    VALUES (NULL, $1, NOW())
                    ON CONFLICT (collection_id) 
                    DO UPDATE SET batch_size_threshold = $1, updated_at = NOW()
                    """,
                    request.batch_size
                )
                
                # Update all active batches
                await conn.execute(
                    """
                    UPDATE batch_processing_state
                    SET batch_size_threshold = $1
                    WHERE status = 'accumulating'
                    """,
                    request.batch_size
                )
                
                scope = "global"
        
        # Get current batch status if collection specified
        current_batch_status = None
        if request.collection_id:
            batch = await repository.get_active_batch(request.collection_id)
            if batch:
                videos_needed = max(0, request.batch_size - batch['video_count'])
                current_batch_status = {
                    "video_count": batch['video_count'],
                    "videos_needed": videos_needed,
                    "estimated_trigger_time": None  # TODO: Calculate based on recording rate
                }
        
        logger.info(
            f"Updated batch size to {request.batch_size} "
            f"(scope: {scope}, collection: {request.collection_id}, "
            f"user: {user.get('email')})"
        )
        
        return UpdateBatchSizeResponse(
            message="Batch size updated successfully",
            batch_size=request.batch_size,
            collection_id=request.collection_id,
            scope=scope,
            previous_batch_size=previous_size,
            effective_at=datetime.utcnow(),
            current_batch_status=current_batch_status
        )
        
    except Exception as e:
        logger.error(f"Failed to update batch size: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update batch size: {str(e)}"
        )


@router.get(
    "/incomplete",
    response_model=IncompleteBatchesResponse,
    summary="Get Incomplete Batches",
    description="Get list of batches waiting for more videos",
    tags=["Batch Processing"]
)
async def get_incomplete_batches(
    user: dict = Depends(get_current_user),
    repository: BatchProcessingRepository = Depends(get_batch_repository)
) -> IncompleteBatchesResponse:
    """
    Get incomplete batches.
    
    Returns batches that are accumulating but haven't reached the threshold yet.
    """
    try:
        async with repository.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    batch_uuid,
                    collection_id,
                    video_count,
                    batch_size_threshold,
                    last_video_time,
                    timeout_at,
                    created_at
                FROM batch_processing_state
                WHERE status = 'accumulating'
                ORDER BY created_at DESC
                """
            )
        
        batches = [
            IncompleteBatch(
                batch_uuid=str(row['batch_uuid']),
                collection_id=row['collection_id'],
                video_count=row['video_count'],
                batch_size_threshold=row['batch_size_threshold'],
                videos_needed=row['batch_size_threshold'] - row['video_count'],
                last_video_time=row['last_video_time'],
                timeout_at=row['timeout_at'],
                created_at=row['created_at']
            )
            for row in rows
        ]
        
        logger.info(
            f"Retrieved {len(batches)} incomplete batches "
            f"for user {user.get('email')}"
        )
        
        return IncompleteBatchesResponse(
            total_incomplete=len(batches),
            incomplete_batches=batches
        )
        
    except Exception as e:
        logger.error(f"Failed to get incomplete batches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve incomplete batches: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Batch Processing Health Check",
    description="Get detailed health status of batch processing system",
    tags=["Batch Processing"]
)
async def health_check(
    repository: BatchProcessingRepository = Depends(get_batch_repository),
    monitor: BatchMonitor = Depends(get_batch_monitor),
    trigger: HybridBatchTrigger = Depends(get_hybrid_trigger),
    executor: PipelineExecutor = Depends(get_pipeline_executor)
) -> HealthCheckResponse:
    """
    Comprehensive health check for batch processing system.
    
    Returns status of worker pool, active batches, database, and event subscriptions.
    """
    try:
        # Worker pool status
        worker_pool = {
            "active_workers": 0,
            "idle_workers": 0,
            "queue_size": 0
        }
        
        if hasattr(executor, 'get_statistics'):
            stats = executor.get_statistics()
            worker_pool["active_workers"] = stats.get('batches_processing', 0)
            worker_pool["queue_size"] = stats.get('batches_queued', 0)
        
        # Active batches
        active_batches = []
        async with repository.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    batch_uuid,
                    collection_id,
                    status,
                    video_count,
                    triggered_at,
                    EXTRACT(EPOCH FROM (NOW() - triggered_at)) as processing_time_seconds
                FROM batch_processing_state
                WHERE status = 'processing'
                ORDER BY triggered_at DESC
                LIMIT 10
                """
            )
            
            for row in rows:
                active_batches.append({
                    "batch_uuid": str(row['batch_uuid']),
                    "collection_id": row['collection_id'],
                    "video_count": row['video_count'],
                    "triggered_at": row['triggered_at'].isoformat(),
                    "processing_time_seconds": float(row['processing_time_seconds'] or 0)
                })
        
        # Recent failures
        async with repository.pool.acquire() as conn:
            recent_failures = await conn.fetchval(
                """
                SELECT COUNT(*) 
                FROM batch_processing_history
                WHERE status = 'failed' 
                  AND created_at > NOW() - INTERVAL '1 hour'
                """
            )
        
        # Database connectivity
        database_connected = True
        try:
            async with repository.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except:
            database_connected = False
        
        # Event subscription status
        event_subscription_status = {
            "camera_events_enabled": True,
            "vision_events_enabled": True,
            "websocket_connected": False,
            "polling_enabled": True
        }
        
        if hasattr(monitor, 'camera_integration'):
            integration = monitor.camera_integration
            if hasattr(integration, 'get_statistics'):
                integration_stats = integration.get_statistics()
                event_subscription_status["websocket_connected"] = integration_stats.get(
                    'websocket_connected', False
                )
        
        # Calculate uptime (placeholder - would need service start time tracking)
        uptime_seconds = 3600.0  # TODO: Implement actual uptime tracking
        
        return HealthCheckResponse(
            status="healthy" if database_connected else "degraded",
            worker_pool=worker_pool,
            active_batches=active_batches,
            recent_failures=recent_failures or 0,
            uptime_seconds=uptime_seconds,
            database_connected=database_connected,
            event_subscription_status=event_subscription_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthCheckResponse(
            status="unhealthy",
            worker_pool={"active_workers": 0, "idle_workers": 0, "queue_size": 0},
            active_batches=[],
            recent_failures=0,
            uptime_seconds=0.0,
            database_connected=False,
            event_subscription_status={
                "camera_events_enabled": False,
                "vision_events_enabled": False,
                "websocket_connected": False,
                "polling_enabled": False
            }
        )

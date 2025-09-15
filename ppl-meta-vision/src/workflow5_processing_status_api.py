#!/usr/bin/env python3
"""
Workflow 5 Processing Status API
===============================

Comprehensive API for managing video processing status including:
- Processing status checking and management
- Completion marking and metadata storage
- Health monitoring integration
- Performance tracking and optimization

API Endpoints:
- GET /api/v1/processing-status/{media_uuid}
- POST /api/v1/processing-status/{media_uuid}/complete
- GET /api/v1/processing-status/{media_uuid}/metadata
- DELETE /api/v1/processing-status/{media_uuid}/reset
- GET /api/v1/processing-status/health
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from workflow5_cache_manager import Workflow5CacheManager
from workflow5_data_access import Workflow5DataAccess

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessingStatus(str, Enum):
    """Video processing status enumeration."""

    NOT_PROCESSED = "not_processed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"
    INVALID = "invalid"


class PlaybackMode(str, Enum):
    """Playback mode selection enumeration."""

    STORED_DATA = "stored_data"  # Zero-CPU using cached face data
    REALTIME_WITH_SESSION = "realtime_with_session"  # Real-time with session
    REALTIME_ONLY = "realtime_only"  # Pure real-time detection
    HYBRID = "hybrid"  # Mixed mode for partial data


class ProcessingStatusResponse(BaseModel):
    """Response model for processing status queries."""

    media_uuid: str
    status: ProcessingStatus
    face_detection_processed: bool
    session_uuid: Optional[str] = None
    processing_completed_at: Optional[datetime] = None
    total_frames_processed: Optional[int] = None
    total_faces_detected: Optional[int] = None
    processing_method: Optional[str] = None
    processing_quality_score: Optional[float] = None
    last_updated: datetime
    cache_status: Optional[str] = None
    optimal_playback_mode: PlaybackMode
    performance_metrics: Optional[Dict[str, Any]] = None


class ProcessingCompletionRequest(BaseModel):
    """Request model for marking processing completion."""

    session_uuid: str = Field(..., description="Face detection session UUID")
    total_frames_processed: int = Field(..., ge=1, description="Total frames processed")
    total_faces_detected: int = Field(..., ge=0, description="Total faces detected")
    processing_method: str = Field(..., description="Processing method used")
    processing_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    frame_analysis_metadata: Optional[Dict[str, Any]] = None
    enable_caching: bool = Field(True, description="Enable face data caching")

    @validator("processing_quality_score")
    def validate_quality_score(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Quality score must be between 0.0 and 1.0")
        return v


class ProcessingMetadataResponse(BaseModel):
    """Response model for processing metadata."""

    media_uuid: str
    processing_metadata: Dict[str, Any]
    frame_analysis_metadata: Optional[Dict[str, Any]] = None
    performance_metrics: Dict[str, Any]
    optimization_recommendations: List[str]
    last_accessed: Optional[datetime] = None
    access_count: Optional[int] = None


class ProcessingStatusHealthResponse(BaseModel):
    """Response model for processing status health check."""

    status: str
    total_processed_videos: int
    total_cached_videos: int
    average_processing_time_ms: float
    cache_hit_ratio: float
    processing_queue_size: int
    system_health_score: float
    last_updated: datetime


class Workflow5ProcessingStatusAPI:
    """
    Comprehensive Processing Status API for Workflow 5.

    Provides all necessary endpoints for processing status management,
    completion tracking, metadata storage, and health monitoring.
    """

    def __init__(self):
        """Initialize the Processing Status API."""
        self.data_access = Workflow5DataAccess()
        self.cache_manager = Workflow5CacheManager()
        self.router = APIRouter(
            prefix="/api/v1/processing-status", tags=["processing-status"]
        )
        self._setup_routes()

        # Performance tracking
        self.performance_stats = {
            "total_status_checks": 0,
            "total_completions": 0,
            "average_check_time_ms": 0.0,
            "cache_hit_ratio": 0.0,
            "last_reset": datetime.utcnow(),
        }

    def _setup_routes(self):
        """Setup all API routes."""
        self.router.add_api_route(
            "/{media_uuid}",
            self.get_processing_status,
            methods=["GET"],
            response_model=ProcessingStatusResponse,
            summary="Get video processing status",
        )

        self.router.add_api_route(
            "/{media_uuid}/complete",
            self.mark_processing_complete,
            methods=["POST"],
            response_model=ProcessingStatusResponse,
            summary="Mark video processing as complete",
        )

        self.router.add_api_route(
            "/{media_uuid}/metadata",
            self.get_processing_metadata,
            methods=["GET"],
            response_model=ProcessingMetadataResponse,
            summary="Get video processing metadata",
        )

        self.router.add_api_route(
            "/{media_uuid}/reset",
            self.reset_processing_status,
            methods=["DELETE"],
            summary="Reset video processing status",
        )

        self.router.add_api_route(
            "/health",
            self.get_health_status,
            methods=["GET"],
            response_model=ProcessingStatusHealthResponse,
            summary="Get processing status system health",
        )

        self.router.add_api_route(
            "/batch/status",
            self.get_batch_processing_status,
            methods=["POST"],
            summary="Get processing status for multiple videos",
        )

    async def get_processing_status(
        self,
        media_uuid: str,
        include_performance: bool = Query(
            False, description="Include performance metrics"
        ),
    ) -> ProcessingStatusResponse:
        """
        Get comprehensive processing status for a video.

        Returns processing state, optimal playback mode, and performance metrics.
        """
        start_time = time.perf_counter()

        try:
            async with self.data_access.async_session_maker() as session:
                # Get base processing status
                status_query = text(
                    """
                    SELECT 
                        media_uuid,
                        face_detection_processed,
                        face_detection_session_uuid,
                        processing_completed_at,
                        total_frames_processed,
                        total_faces_detected,
                        processing_method,
                        last_updated,
                        processing_quality_score,
                        frame_analysis_metadata,
                        optimization_enabled,
                        cache_status,
                        last_accessed,
                        access_count,
                        avg_detection_latency,
                        face_density_score,
                        processing_efficiency
                    FROM media_processing_status 
                    WHERE media_uuid = :media_uuid
                """
                )

                result = await session.execute(status_query, {"media_uuid": media_uuid})
                row = result.fetchone()

                if not row:
                    # Video not yet processed
                    optimal_mode = await self._determine_optimal_playback_mode(
                        media_uuid, None, session
                    )

                    return ProcessingStatusResponse(
                        media_uuid=media_uuid,
                        status=ProcessingStatus.NOT_PROCESSED,
                        face_detection_processed=False,
                        last_updated=datetime.utcnow(),
                        optimal_playback_mode=optimal_mode,
                    )

                # Parse processing status
                processing_status = self._parse_processing_status(row)

                # Determine optimal playback mode
                optimal_mode = await self._determine_optimal_playback_mode(
                    media_uuid, row, session
                )

                # Get performance metrics if requested
                performance_metrics = None
                if include_performance:
                    performance_metrics = await self._get_performance_metrics(
                        media_uuid, session
                    )

                # Update access tracking
                await self._update_access_tracking(media_uuid, session)
                await session.commit()

                # Update performance stats
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self._update_performance_stats("status_check", elapsed_ms)

                return ProcessingStatusResponse(
                    media_uuid=media_uuid,
                    status=processing_status,
                    face_detection_processed=row[1],
                    session_uuid=row[2],
                    processing_completed_at=row[3],
                    total_frames_processed=row[4],
                    total_faces_detected=row[5],
                    processing_method=row[6],
                    last_updated=row[7],
                    processing_quality_score=row[8],
                    cache_status=row[11],
                    optimal_playback_mode=optimal_mode,
                    performance_metrics=performance_metrics,
                )

        except Exception as e:
            logger.error(f"Failed to get processing status for {media_uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve processing status: {str(e)}",
            )

    async def mark_processing_complete(
        self,
        media_uuid: str,
        completion_data: ProcessingCompletionRequest,
        background_tasks: BackgroundTasks,
    ) -> ProcessingStatusResponse:
        """
        Mark video processing as complete with comprehensive metadata.

        Triggers cache warming and optimization in the background.
        """
        start_time = time.perf_counter()

        try:
            async with self.data_access.async_session_maker() as session:
                # Update processing status
                update_query = text(
                    """
                    UPDATE media_processing_status 
                    SET 
                        face_detection_processed = TRUE,
                        face_detection_session_uuid = :session_uuid,
                        processing_completed_at = NOW(),
                        total_frames_processed = :total_frames,
                        total_faces_detected = :total_faces,
                        processing_method = :method,
                        processing_quality_score = :quality_score,
                        frame_analysis_metadata = :frame_metadata,
                        last_updated = NOW(),
                        cache_status = 'warming',
                        optimization_enabled = TRUE
                    WHERE media_uuid = :media_uuid
                """
                )

                # Convert metadata to JSON for database storage
                frame_metadata = (
                    json.dumps(completion_data.frame_analysis_metadata)
                    if completion_data.frame_analysis_metadata
                    else None
                )

                await session.execute(
                    update_query,
                    {
                        "media_uuid": media_uuid,
                        "session_uuid": completion_data.session_uuid,
                        "total_frames": completion_data.total_frames_processed,
                        "total_faces": completion_data.total_faces_detected,
                        "method": completion_data.processing_method,
                        "quality_score": completion_data.processing_quality_score,
                        "frame_metadata": frame_metadata,
                    },
                )

                # Create enhanced processing status record
                enhanced_query = text(
                    """
                    INSERT INTO media_processing_status_enhanced (
                        media_uuid, original_processing_status_id, cache_status,
                        optimization_enabled, last_accessed
                    ) VALUES (
                        :media_uuid, :media_uuid, 'warming', TRUE, NOW()
                    )
                    ON CONFLICT (media_uuid) DO UPDATE SET
                        cache_status = 'warming',
                        optimization_enabled = TRUE,
                        last_accessed = NOW()
                """
                )

                await session.execute(enhanced_query, {"media_uuid": media_uuid})
                await session.commit()

                # Schedule background cache warming if enabled
                if completion_data.enable_caching:
                    background_tasks.add_task(
                        self._background_cache_warming,
                        media_uuid,
                        completion_data.session_uuid,
                    )

                # Update performance stats
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self._update_performance_stats("completion", elapsed_ms)

                logger.info(
                    f"Processing completed for {media_uuid} with {completion_data.total_faces_detected} faces"
                )

                # Return updated status
                return await self.get_processing_status(
                    media_uuid, include_performance=True
                )

        except Exception as e:
            logger.error(f"Failed to mark processing complete for {media_uuid}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to mark processing complete: {str(e)}"
            )

    async def get_processing_metadata(
        self, media_uuid: str
    ) -> ProcessingMetadataResponse:
        """
        Get comprehensive processing metadata for a video.
        """
        try:
            async with self.data_access.async_session_maker() as session:
                metadata_query = text(
                    """
                    SELECT 
                        mps.frame_analysis_metadata,
                        mps.processing_quality_score,
                        mps.processing_method,
                        mps.total_frames_processed,
                        mps.total_faces_detected,
                        mps.last_accessed,
                        mps.access_count,
                        mps.avg_detection_latency,
                        mps.face_density_score,
                        mps.processing_efficiency,
                        mpse.cache_status,
                        mpse.last_accessed
                    FROM media_processing_status mps
                    LEFT JOIN media_processing_status_enhanced mpse 
                        ON mps.media_uuid = mpse.media_uuid
                    WHERE mps.media_uuid = :media_uuid
                """
                )

                result = await session.execute(
                    metadata_query, {"media_uuid": media_uuid}
                )
                row = result.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Processing metadata not found for {media_uuid}",
                    )

                # Build processing metadata
                processing_metadata = {
                    "processing_quality_score": row[1],
                    "processing_method": row[2],
                    "total_frames_processed": row[3],
                    "total_faces_detected": row[4],
                    "avg_detection_latency": row[7],
                    "face_density_score": row[8],
                    "processing_efficiency": row[9],
                    "cache_status": row[10],
                    "last_accessed": row[11],
                }

                # Build performance metrics
                performance_metrics = await self._get_performance_metrics(
                    media_uuid, session
                )

                # Generate optimization recommendations
                recommendations = self._generate_optimization_recommendations(row)

                return ProcessingMetadataResponse(
                    media_uuid=media_uuid,
                    processing_metadata=processing_metadata,
                    frame_analysis_metadata=row[0],
                    performance_metrics=performance_metrics,
                    optimization_recommendations=recommendations,
                    last_accessed=row[5],
                    access_count=row[6],
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get processing metadata for {media_uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve processing metadata: {str(e)}",
            )

    async def reset_processing_status(self, media_uuid: str) -> Dict[str, str]:
        """
        Reset processing status for a video (development/debugging).
        """
        try:
            async with self.data_access.async_session_maker() as session:
                # Reset processing status
                reset_query = text(
                    """
                    UPDATE media_processing_status 
                    SET 
                        face_detection_processed = FALSE,
                        face_detection_session_uuid = NULL,
                        processing_completed_at = NULL,
                        total_frames_processed = NULL,
                        total_faces_detected = NULL,
                        processing_method = NULL,
                        processing_quality_score = NULL,
                        frame_analysis_metadata = NULL,
                        cache_status = 'not_cached',
                        optimization_enabled = FALSE,
                        last_updated = NOW()
                    WHERE media_uuid = :media_uuid
                """
                )

                await session.execute(reset_query, {"media_uuid": media_uuid})

                # Clear cache data
                await self.cache_manager.invalidate_cache(media_uuid)

                await session.commit()

                logger.info(f"Processing status reset for {media_uuid}")

                return {"message": f"Processing status reset for {media_uuid}"}

        except Exception as e:
            logger.error(f"Failed to reset processing status for {media_uuid}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to reset processing status: {str(e)}"
            )

    async def get_health_status(self) -> ProcessingStatusHealthResponse:
        """
        Get comprehensive health status of the processing system.
        """
        try:
            async with self.data_access.async_session_maker() as session:
                # Get processing statistics
                stats_query = text(
                    """
                    SELECT 
                        COUNT(*) as total_videos,
                        COUNT(*) FILTER (WHERE face_detection_processed = TRUE) as processed_videos,
                        COUNT(*) FILTER (WHERE cache_status = 'cached') as cached_videos,
                        AVG(avg_detection_latency) as avg_latency,
                        AVG(processing_efficiency) as avg_efficiency
                    FROM media_processing_status
                """
                )

                result = await session.execute(stats_query)
                stats = result.fetchone()

                # Get cache performance metrics
                cache_metrics = await self.cache_manager.get_cache_performance_metrics()

                # Calculate system health score
                health_score = self._calculate_system_health_score(stats, cache_metrics)

                return ProcessingStatusHealthResponse(
                    status="healthy" if health_score > 0.8 else "degraded",
                    total_processed_videos=stats[1] or 0,
                    total_cached_videos=stats[2] or 0,
                    average_processing_time_ms=stats[3] or 0.0,
                    cache_hit_ratio=cache_metrics.cache_hit_ratio,
                    processing_queue_size=cache_metrics.processing_queue_size,
                    system_health_score=health_score,
                    last_updated=datetime.utcnow(),
                )

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve health status: {str(e)}"
            )

    async def get_batch_processing_status(
        self, media_uuids: List[str]
    ) -> Dict[str, ProcessingStatusResponse]:
        """
        Get processing status for multiple videos in batch.
        """
        try:
            results = {}

            # Process in batches to avoid overwhelming the database
            batch_size = 50
            for i in range(0, len(media_uuids), batch_size):
                batch = media_uuids[i : i + batch_size]

                # Get status for this batch
                batch_results = await asyncio.gather(
                    *[self.get_processing_status(media_uuid) for media_uuid in batch],
                    return_exceptions=True,
                )

                # Process results
                for media_uuid, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.warning(
                            f"Failed to get status for {media_uuid}: {result}"
                        )
                        continue
                    results[media_uuid] = result

            return results

        except Exception as e:
            logger.error(f"Failed to get batch processing status: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve batch processing status: {str(e)}",
            )

    # Helper methods
    async def _determine_optimal_playback_mode(
        self, media_uuid: str, processing_row: Optional[tuple], session: AsyncSession
    ) -> PlaybackMode:
        """
        Determine the optimal playback mode based on processing status and data availability.
        """
        if not processing_row or not processing_row[1]:  # Not processed
            return PlaybackMode.REALTIME_ONLY

        # Check if face data is cached and valid
        cache_query = text(
            """
            SELECT total_faces, cache_created_at, cache_expires_at
            FROM face_data_cache 
            WHERE media_uuid = :media_uuid
        """
        )

        result = await session.execute(cache_query, {"media_uuid": media_uuid})
        cache_row = result.fetchone()

        if cache_row and cache_row[0] > 0:  # Has cached faces
            # Check if cache is still valid
            if not cache_row[2] or datetime.utcnow() < cache_row[2]:
                return PlaybackMode.STORED_DATA

        # Has session but no valid cache
        if processing_row[2]:  # Has session UUID
            return PlaybackMode.REALTIME_WITH_SESSION

        return PlaybackMode.REALTIME_ONLY

    def _parse_processing_status(self, row: tuple) -> ProcessingStatus:
        """Parse processing status from database row."""
        if not row[1]:  # face_detection_processed
            return ProcessingStatus.NOT_PROCESSED

        cache_status = row[11]  # cache_status column
        if cache_status == "cached":
            return ProcessingStatus.CACHED
        elif cache_status == "warming":
            return ProcessingStatus.PROCESSING
        elif cache_status == "failed":
            return ProcessingStatus.FAILED
        elif row[1]:  # face_detection_processed is True
            return ProcessingStatus.COMPLETED

        return ProcessingStatus.NOT_PROCESSED

    async def _get_performance_metrics(
        self, media_uuid: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Get performance metrics for a video."""
        metrics_query = text(
            """
            SELECT 
                avg_detection_latency,
                face_density_score,
                processing_efficiency,
                access_count,
                last_accessed
            FROM media_processing_status
            WHERE media_uuid = :media_uuid
        """
        )

        result = await session.execute(metrics_query, {"media_uuid": media_uuid})
        row = result.fetchone()

        if not row:
            return {}

        return {
            "avg_detection_latency_ms": row[0],
            "face_density_score": row[1],
            "processing_efficiency": row[2],
            "access_count": row[3],
            "last_accessed": row[4],
            "performance_grade": self._calculate_performance_grade(row),
        }

    def _generate_optimization_recommendations(self, row: tuple) -> List[str]:
        """Generate optimization recommendations based on processing data."""
        recommendations = []

        # Low processing efficiency
        if row[9] and row[9] < 0.7:  # processing_efficiency
            recommendations.append(
                "Consider optimizing face detection parameters for better efficiency"
            )

        # High face density
        if row[8] and row[8] > 0.8:  # face_density_score
            recommendations.append(
                "High face density detected - consider specialized processing"
            )

        # Slow detection latency
        if row[7] and row[7] > 100:  # avg_detection_latency
            recommendations.append(
                "Detection latency is high - consider performance optimization"
            )

        # Low quality score
        if row[1] and row[1] < 0.8:  # processing_quality_score
            recommendations.append(
                "Processing quality could be improved with better parameters"
            )

        if not recommendations:
            recommendations.append("Processing parameters are optimal")

        return recommendations

    def _calculate_performance_grade(self, row: tuple) -> str:
        """Calculate performance grade based on metrics."""
        scores = []

        # Latency score (lower is better)
        if row[0]:  # avg_detection_latency
            latency_score = max(0, 1 - (row[0] / 200))  # 200ms baseline
            scores.append(latency_score)

        # Efficiency score
        if row[2]:  # processing_efficiency
            scores.append(row[2])

        if not scores:
            return "N/A"

        avg_score = sum(scores) / len(scores)

        if avg_score >= 0.9:
            return "A+"
        elif avg_score >= 0.8:
            return "A"
        elif avg_score >= 0.7:
            return "B"
        elif avg_score >= 0.6:
            return "C"
        else:
            return "D"

    def _calculate_system_health_score(self, stats: tuple, cache_metrics) -> float:
        """Calculate overall system health score."""
        scores = []

        # Processing completion rate
        if stats[0] > 0:  # total_videos
            completion_rate = stats[1] / stats[0]  # processed_videos / total_videos
            scores.append(completion_rate)

        # Cache effectiveness
        if stats[1] > 0:  # processed_videos
            cache_rate = stats[2] / stats[1]  # cached_videos / processed_videos
            scores.append(cache_rate)

        # Performance score
        if stats[3]:  # avg_latency
            latency_score = max(0, 1 - (stats[3] / 200))  # 200ms baseline
            scores.append(latency_score)

        # Cache hit ratio
        scores.append(cache_metrics.cache_hit_ratio / 100)

        return sum(scores) / len(scores) if scores else 0.0

    async def _update_access_tracking(self, media_uuid: str, session: AsyncSession):
        """Update access tracking for analytics."""
        update_query = text(
            """
            UPDATE media_processing_status 
            SET 
                access_count = COALESCE(access_count, 0) + 1,
                last_accessed = NOW()
            WHERE media_uuid = :media_uuid
        """
        )

        await session.execute(update_query, {"media_uuid": media_uuid})

    def _update_performance_stats(self, operation: str, elapsed_ms: float):
        """Update internal performance statistics."""
        if operation == "status_check":
            self.performance_stats["total_status_checks"] += 1
            # Update rolling average
            current_avg = self.performance_stats["average_check_time_ms"]
            total_checks = self.performance_stats["total_status_checks"]
            new_avg = ((current_avg * (total_checks - 1)) + elapsed_ms) / total_checks
            self.performance_stats["average_check_time_ms"] = new_avg

        elif operation == "completion":
            self.performance_stats["total_completions"] += 1

    async def _background_cache_warming(self, media_uuid: str, session_uuid: str):
        """Background task for cache warming after processing completion."""
        try:
            logger.info(f"Starting background cache warming for {media_uuid}")

            # Warm the cache
            success = await self.cache_manager.warm_cache_for_media(media_uuid)

            if success:
                # Update cache status to 'cached'
                async with self.data_access.async_session_maker() as session:
                    update_query = text(
                        """
                        UPDATE media_processing_status 
                        SET cache_status = 'cached', last_updated = NOW()
                        WHERE media_uuid = :media_uuid
                    """
                    )
                    await session.execute(update_query, {"media_uuid": media_uuid})
                    await session.commit()

                logger.info(f"Cache warming completed for {media_uuid}")
            else:
                # Mark cache as failed
                async with self.data_access.async_session_maker() as session:
                    update_query = text(
                        """
                        UPDATE media_processing_status 
                        SET cache_status = 'failed', last_updated = NOW()
                        WHERE media_uuid = :media_uuid
                    """
                    )
                    await session.execute(update_query, {"media_uuid": media_uuid})
                    await session.commit()

                logger.warning(f"Cache warming failed for {media_uuid}")

        except Exception as e:
            logger.error(f"Background cache warming failed for {media_uuid}: {e}")

    async def close(self):
        """Close database connections."""
        await self.data_access.close()


# FastAPI router instance for integration
def get_processing_status_router() -> APIRouter:
    """Get the configured processing status API router."""
    api = Workflow5ProcessingStatusAPI()
    return api.router


if __name__ == "__main__":
    # For testing the API standalone
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="Workflow 5 Processing Status API")

    # Add the processing status routes
    api = Workflow5ProcessingStatusAPI()
    app.include_router(api.router)

    @app.on_event("shutdown")
    async def shutdown_event():
        await api.close()

    uvicorn.run(app, host="0.0.0.0", port=8010)

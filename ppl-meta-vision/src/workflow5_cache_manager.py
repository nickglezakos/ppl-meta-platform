"""
PPL Meta Vision Service - Workflow 5 Face Data Caching System
Comprehensive caching pipeline for instant face detection retrieval.

This module implements the complete face data caching system including:
- Pre-computation pipeline for media processing
- Frame-indexed face storage with JSONB optimization
- Automatic cache warming and invalidation
- Intelligent cache management and optimization
- Background processing and queue management

Performance Goals:
- Process 1000+ frames/minute for cache building
- <5ms face data retrieval from cache
- 95%+ cache hit ratio for processed media
- Automatic background cache warming
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from workflow5_data_access import workflow5_data_access
from workflow5_schema import FaceDataCache, MediaProcessingStatusEnhanced

logger = logging.getLogger(__name__)


class CacheStatus(Enum):
    """Face data cache status states."""

    NOT_CACHED = "not_cached"
    PROCESSING = "processing"
    CACHED = "cached"
    PARTIAL = "partial"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class CacheProcessingJob:
    """Cache processing job definition."""

    media_uuid: str
    media_path: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    requested_at: datetime = None
    processing_options: Dict[str, Any] = None


@dataclass
class CachePerformanceMetrics:
    """Cache system performance metrics."""

    total_media_cached: int
    total_faces_cached: int
    cache_hit_ratio: float
    average_retrieval_time_ms: float
    cache_size_mb: float
    processing_queue_size: int
    cache_effectiveness_score: float


class Workflow5CacheManager:
    """
    Comprehensive face data caching system for Workflow 5.

    Manages the complete lifecycle of face data caching including:
    - Media file processing and face detection
    - Frame-indexed storage with JSONB optimization
    - Cache warming, invalidation, and cleanup
    - Background processing queue management
    - Performance monitoring and optimization
    """

    def __init__(self):
        """Initialize cache management system."""
        self.processing_queue = []
        self.active_jobs = {}
        self.cache_stats = {
            "total_cached": 0,
            "total_hits": 0,
            "total_misses": 0,
            "total_faces_stored": 0,
            "cache_size_bytes": 0,
            "avg_processing_time_ms": 0.0,
        }

        # Cache management settings
        self.settings = {
            "max_cache_age_days": 30,
            "cache_cleanup_interval_hours": 6,
            "max_processing_concurrent": 3,
            "cache_compression_enabled": True,
            "auto_warming_enabled": True,
            "background_processing_enabled": True,
        }

        # Performance thresholds
        self.thresholds = {
            "max_cache_size_gb": 10.0,
            "min_cache_hit_ratio": 0.9,
            "max_retrieval_time_ms": 5.0,
            "cache_expiry_check_interval": 3600,  # 1 hour
        }

        self._background_tasks = []
        self._shutdown_event = asyncio.Event()

    async def process_media_for_cache(
        self,
        media_uuid: str,
        media_path: str,
        force_reprocess: bool = False,
        priority: int = 1,
    ) -> bool:
        """
        Process media file and build optimized face data cache.

        Args:
            media_uuid: Unique media identifier
            media_path: Path to media file for processing
            force_reprocess: Force reprocessing even if cache exists
            priority: Processing priority (1=high, 2=medium, 3=low)

        Returns:
            True if processing was successful
        """
        start_time = time.perf_counter()

        try:
            logger.info(f"Starting cache processing for media {media_uuid}")

            # Step 1: Check if already cached (unless forced)
            if not force_reprocess:
                existing_cache = await self._get_cache_status(media_uuid)
                if existing_cache["status"] == CacheStatus.CACHED:
                    logger.info(f"Media {media_uuid} already cached, skipping")
                    return True

            # Step 2: Update processing status
            await self._update_cache_status(media_uuid, CacheStatus.PROCESSING)

            # Step 3: Process media file for face detection
            face_detection_results = await self._process_media_file(media_path)

            if not face_detection_results:
                logger.warning(f"No face detection results for {media_uuid}")
                await self._update_cache_status(media_uuid, CacheStatus.ERROR)
                return False

            # Step 4: Optimize and store face data
            optimized_cache = await self._optimize_face_data_for_cache(
                face_detection_results
            )

            # Step 5: Store in database with frame indexing
            cache_success = await self._store_face_cache(
                media_uuid, optimized_cache, len(face_detection_results)
            )

            if cache_success:
                await self._update_cache_status(media_uuid, CacheStatus.CACHED)

                # Step 6: Update performance metrics
                processing_time = (time.perf_counter() - start_time) * 1000
                await self._update_processing_metrics(media_uuid, processing_time)

                logger.info(
                    f"Cache processing completed for {media_uuid} in "
                    f"{processing_time:.2f}ms ({len(face_detection_results)} faces)"
                )
                return True
            else:
                await self._update_cache_status(media_uuid, CacheStatus.ERROR)
                return False

        except Exception as e:
            logger.error(f"Cache processing failed for {media_uuid}: {e}")
            await self._update_cache_status(media_uuid, CacheStatus.ERROR)
            return False

    async def warm_cache_for_media(self, media_uuid: str) -> bool:
        """
        Warm cache for specific media (load into memory cache).

        Args:
            media_uuid: Media to warm cache for

        Returns:
            True if cache warming successful
        """
        try:
            # Use the data access layer's cache warming
            success = await workflow5_data_access.warm_cache_for_media(media_uuid)

            if success:
                # Update access statistics
                await self._update_cache_access_stats(media_uuid, hit=True)
                logger.info(f"Cache warmed successfully for {media_uuid}")

            return success

        except Exception as e:
            logger.error(f"Cache warming failed for {media_uuid}: {e}")
            return False

    async def get_cached_faces(
        self,
        media_uuid: str,
        frame_range: Tuple[int, int],
        confidence_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve face data from cache with performance tracking.

        Args:
            media_uuid: Media identifier
            frame_range: (start_frame, end_frame)
            confidence_threshold: Minimum confidence filter

        Returns:
            List of face detection data
        """
        start_time = time.perf_counter()

        try:
            # Use the data access layer for retrieval
            faces = await workflow5_data_access.get_face_data_by_frame_range(
                media_uuid, frame_range[0], frame_range[1], confidence_threshold
            )

            retrieval_time = (time.perf_counter() - start_time) * 1000

            # Update cache statistics
            if faces:
                await self._update_cache_access_stats(media_uuid, hit=True)
                self.cache_stats["total_hits"] += 1
            else:
                await self._update_cache_access_stats(media_uuid, hit=False)
                self.cache_stats["total_misses"] += 1

            # Update performance metrics
            await workflow5_data_access.update_access_metrics(
                media_uuid, retrieval_time
            )

            logger.debug(
                f"Cache retrieval for {media_uuid}: {len(faces)} faces in "
                f"{retrieval_time:.2f}ms"
            )

            return faces

        except Exception as e:
            logger.error(f"Cache retrieval failed for {media_uuid}: {e}")
            self.cache_stats["total_misses"] += 1
            return []

    async def invalidate_cache(self, media_uuid: str) -> bool:
        """
        Invalidate cache for specific media.

        Args:
            media_uuid: Media to invalidate cache for

        Returns:
            True if invalidation successful
        """
        try:
            async with workflow5_data_access.async_session_maker() as session:
                # Mark cache as expired
                await session.execute(
                    text(
                        """
                        UPDATE face_data_cache 
                        SET cache_expires_at = NOW() - INTERVAL '1 day'
                        WHERE media_uuid = :media_uuid
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                # Update processing status
                await session.execute(
                    text(
                        """
                        UPDATE media_processing_status_enhanced
                        SET cache_status = 'expired',
                            last_accessed = NOW()
                        WHERE original_processing_status_id = :media_uuid
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                await session.commit()

            logger.info(f"Cache invalidated for {media_uuid}")
            return True

        except Exception as e:
            logger.error(f"Cache invalidation failed for {media_uuid}: {e}")
            return False

    async def cleanup_expired_cache(self) -> int:
        """
        Clean up expired cache entries.

        Returns:
            Number of entries cleaned up
        """
        try:
            async with workflow5_data_access.async_session_maker() as session:
                # Find expired cache entries
                result = await session.execute(
                    text(
                        """
                        SELECT media_uuid FROM face_data_cache 
                        WHERE cache_expires_at IS NOT NULL 
                        AND cache_expires_at < NOW()
                        LIMIT 100
                    """
                    )
                )

                expired_media = [row[0] for row in result]

                if expired_media:
                    # Delete expired cache entries
                    await session.execute(
                        text(
                            """
                            DELETE FROM face_data_cache 
                            WHERE media_uuid = ANY(:media_uuids)
                        """
                        ),
                        {"media_uuids": expired_media},
                    )

                    await session.commit()

                    logger.info(
                        f"Cleaned up {len(expired_media)} expired cache entries"
                    )

                return len(expired_media)

        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return 0

    async def get_cache_performance_metrics(self) -> CachePerformanceMetrics:
        """Get comprehensive cache performance metrics."""
        try:
            async with workflow5_data_access.async_session_maker() as session:
                # Get cache statistics
                cache_stats = await session.execute(
                    text(
                        """
                        SELECT 
                            COUNT(*) as total_cached,
                            SUM(total_faces) as total_faces,
                            AVG(cache_efficiency) as avg_efficiency,
                            SUM(cache_size_bytes) as total_size_bytes,
                            AVG(avg_retrieval_time) as avg_retrieval_time
                        FROM face_data_cache
                        WHERE cache_expires_at IS NULL OR cache_expires_at > NOW()
                    """
                    )
                )

                row = cache_stats.fetchone()

                if row:
                    total_requests = (
                        self.cache_stats["total_hits"]
                        + self.cache_stats["total_misses"]
                    )
                    hit_ratio = (
                        self.cache_stats["total_hits"] / total_requests
                        if total_requests > 0
                        else 0.0
                    )

                    return CachePerformanceMetrics(
                        total_media_cached=row[0] or 0,
                        total_faces_cached=row[1] or 0,
                        cache_hit_ratio=hit_ratio,
                        average_retrieval_time_ms=row[4] or 0.0,
                        cache_size_mb=(row[3] or 0) / 1024 / 1024,
                        processing_queue_size=len(self.processing_queue),
                        cache_effectiveness_score=(hit_ratio * 100 + (row[2] or 0)) / 2,
                    )

                # Return default metrics if no data
                return CachePerformanceMetrics(
                    total_media_cached=0,
                    total_faces_cached=0,
                    cache_hit_ratio=0.0,
                    average_retrieval_time_ms=0.0,
                    cache_size_mb=0.0,
                    processing_queue_size=0,
                    cache_effectiveness_score=0.0,
                )

        except Exception as e:
            logger.error(f"Failed to get cache metrics: {e}")
            return CachePerformanceMetrics(
                total_media_cached=0,
                total_faces_cached=0,
                cache_hit_ratio=0.0,
                average_retrieval_time_ms=0.0,
                cache_size_mb=0.0,
                processing_queue_size=0,
                cache_effectiveness_score=0.0,
            )

    async def start_background_processing(self) -> None:
        """Start background cache processing tasks."""
        if self.settings["background_processing_enabled"]:
            # Cache cleanup task
            cleanup_task = asyncio.create_task(self._background_cache_cleanup())
            self._background_tasks.append(cleanup_task)

            # Queue processing task
            queue_task = asyncio.create_task(self._background_queue_processor())
            self._background_tasks.append(queue_task)

            logger.info("Background cache processing started")

    async def stop_background_processing(self) -> None:
        """Stop background processing tasks."""
        self._shutdown_event.set()

        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()
        logger.info("Background cache processing stopped")

    async def check_cache_status(self, media_uuid: str) -> Dict[str, Any]:
        """
        Public method to check cache status for media.

        Returns cache status information including whether media is cached,
        cache effectiveness metrics, and availability details.
        """
        return await self._get_cache_status(media_uuid)

    async def close(self) -> None:
        """
        Close cache manager and cleanup resources.

        Stops background processing and cleans up any pending tasks.
        """
        await self.stop_background_processing()
        logger.info("Cache manager closed successfully")

    # Private helper methods

    async def _get_cache_status(self, media_uuid: str) -> Dict[str, Any]:
        """Get current cache status for media."""
        try:
            async with workflow5_data_access.async_session_maker() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT 
                            total_faces,
                            cache_created_at,
                            cache_expires_at,
                            cache_size_bytes
                        FROM face_data_cache 
                        WHERE media_uuid = :media_uuid
                        LIMIT 1
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                row = result.fetchone()
                if row:
                    is_expired = row[2] and datetime.utcnow() > row[2]
                    status = CacheStatus.EXPIRED if is_expired else CacheStatus.CACHED

                    return {
                        "status": status,
                        "total_faces": row[0],
                        "created_at": row[1],
                        "expires_at": row[2],
                        "size_bytes": row[3],
                    }

                return {"status": CacheStatus.NOT_CACHED}

        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            return {"status": CacheStatus.ERROR}

    async def _update_cache_status(self, media_uuid: str, status: CacheStatus) -> None:
        """Update cache processing status."""
        try:
            async with workflow5_data_access.async_session_maker() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO media_processing_status_enhanced (
                            media_uuid, original_processing_status_id, cache_status
                        ) VALUES (
                            :media_uuid, :media_uuid, :status
                        )
                        ON CONFLICT (media_uuid) DO UPDATE SET
                            cache_status = EXCLUDED.cache_status,
                            last_accessed = NOW()
                    """
                    ),
                    {"media_uuid": media_uuid, "status": status.value},
                )

                await session.commit()

        except Exception as e:
            logger.error(f"Failed to update cache status: {e}")

    async def _process_media_file(self, media_path: str) -> List[Dict[str, Any]]:
        """
        Process media file for face detection.

        NOTE: This is a placeholder implementation. In production, this would
        integrate with the actual face detection ML pipeline.
        """
        # Placeholder: Mock face detection results
        # In production, this would call the actual face detection service
        mock_faces = []

        # Simulate processing time and generate mock data
        await asyncio.sleep(0.1)  # Simulate processing

        # Generate sample face data for testing
        for frame in range(0, 100, 10):  # Every 10th frame
            for face_id in range(2):  # 2 faces per frame
                mock_faces.append(
                    {
                        "frame_number": frame,
                        "bbox": {
                            "x1": 100 + face_id * 200,
                            "y1": 100,
                            "x2": 200 + face_id * 200,
                            "y2": 200,
                        },
                        "confidence": 0.85 + (face_id * 0.1),
                        "method": "mock_detector",
                        "detected_at": datetime.utcnow().isoformat(),
                    }
                )

        return mock_faces

    async def _optimize_face_data_for_cache(
        self, face_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Optimize face detection results for efficient caching."""

        # Group faces by frame for efficient lookup
        frame_indexed_faces = {}

        for face in face_results:
            frame_num = face["frame_number"]
            if frame_num not in frame_indexed_faces:
                frame_indexed_faces[frame_num] = []

            # Optimize face data structure
            optimized_face = {
                "bbox": face["bbox"],
                "confidence": round(face["confidence"], 3),
                "method": face["method"],
            }

            frame_indexed_faces[frame_num].append(optimized_face)

        # Sort faces by confidence within each frame
        for frame_num in frame_indexed_faces:
            frame_indexed_faces[frame_num].sort(
                key=lambda f: f["confidence"], reverse=True
            )

        return {
            "faces_by_frame": frame_indexed_faces,
            "total_faces": len(face_results),
            "frame_count": len(frame_indexed_faces),
            "optimization_version": "1.0",
        }

    async def _store_face_cache(
        self, media_uuid: str, optimized_cache: Dict[str, Any], total_faces: int
    ) -> bool:
        """Store optimized face cache in database."""
        try:
            # Convert to JSONB for PostgreSQL
            faces_jsonb = json.dumps(optimized_cache["faces_by_frame"])

            async with workflow5_data_access.async_session_maker() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO face_data_cache (
                            media_uuid,
                            cached_faces,
                            total_frames,
                            total_faces,
                            cache_version,
                            cache_size_bytes
                        ) VALUES (
                            :media_uuid,
                            :faces_data,
                            :total_frames,
                            :total_faces,
                            :version,
                            :size_bytes
                        )
                        ON CONFLICT (media_uuid) DO UPDATE SET
                            cached_faces = EXCLUDED.cached_faces,
                            total_frames = EXCLUDED.total_frames,
                            total_faces = EXCLUDED.total_faces,
                            cache_version = EXCLUDED.cache_version,
                            cache_size_bytes = EXCLUDED.cache_size_bytes,
                            last_accessed = NOW()
                    """
                    ),
                    {
                        "media_uuid": media_uuid,
                        "faces_data": faces_jsonb,
                        "total_frames": optimized_cache["frame_count"],
                        "total_faces": total_faces,
                        "version": optimized_cache["optimization_version"],
                        "size_bytes": len(faces_jsonb.encode("utf-8")),
                    },
                )

                await session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to store face cache: {e}")
            return False

    async def _update_processing_metrics(
        self, media_uuid: str, processing_time_ms: float
    ) -> None:
        """Update processing performance metrics."""
        try:
            # Update running averages
            total = self.cache_stats["total_cached"] + 1
            current_avg = self.cache_stats["avg_processing_time_ms"]

            self.cache_stats["avg_processing_time_ms"] = (
                current_avg * (total - 1) + processing_time_ms
            ) / total

            self.cache_stats["total_cached"] = total

        except Exception as e:
            logger.error(f"Failed to update processing metrics: {e}")

    async def _update_cache_access_stats(self, media_uuid: str, hit: bool) -> None:
        """Update cache access statistics."""
        try:
            async with workflow5_data_access.async_session_maker() as session:
                if hit:
                    await session.execute(
                        text(
                            """
                            UPDATE face_data_cache 
                            SET 
                                hit_count = COALESCE(hit_count, 0) + 1,
                                access_count = COALESCE(access_count, 0) + 1,
                                last_accessed = NOW()
                            WHERE media_uuid = :media_uuid
                        """
                        ),
                        {"media_uuid": media_uuid},
                    )
                else:
                    await session.execute(
                        text(
                            """
                            UPDATE face_data_cache 
                            SET 
                                miss_count = COALESCE(miss_count, 0) + 1,
                                access_count = COALESCE(access_count, 0) + 1,
                                last_accessed = NOW()
                            WHERE media_uuid = :media_uuid
                        """
                        ),
                        {"media_uuid": media_uuid},
                    )

                await session.commit()

        except Exception as e:
            logger.debug(f"Failed to update cache access stats: {e}")

    async def _background_cache_cleanup(self) -> None:
        """Background task for periodic cache cleanup."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(
                    self.settings["cache_cleanup_interval_hours"] * 3600
                )

                if self._shutdown_event.is_set():
                    break

                cleaned_count = await self.cleanup_expired_cache()
                if cleaned_count > 0:
                    logger.info(
                        f"Background cleanup removed {cleaned_count} expired entries"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cache cleanup error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _background_queue_processor(self) -> None:
        """Background task for processing cache queue."""
        while not self._shutdown_event.is_set():
            try:
                if not self.processing_queue:
                    await asyncio.sleep(5)  # Check queue every 5 seconds
                    continue

                # Process jobs from queue
                concurrent_jobs = min(
                    len(self.processing_queue),
                    self.settings["max_processing_concurrent"],
                )

                if concurrent_jobs > 0:
                    jobs_to_process = self.processing_queue[:concurrent_jobs]
                    self.processing_queue = self.processing_queue[concurrent_jobs:]

                    # Process jobs concurrently
                    tasks = [
                        self.process_media_for_cache(job.media_uuid, job.media_path)
                        for job in jobs_to_process
                    ]

                    await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background queue processor error: {e}")
                await asyncio.sleep(30)  # Wait before retrying


# Singleton instance for easy import
workflow5_cache_manager = Workflow5CacheManager()

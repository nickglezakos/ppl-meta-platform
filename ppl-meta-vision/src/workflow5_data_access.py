"""
PPL Meta Vision Service - Workflow 5 Data Access Layer
Ultra-fast frame-indexed face data retrieval with <10ms performance targets.

This module implements the high-performance data access layer for Workflow 5,
providing optimized query methods for frame-indexed face retrieval and intelligent
caching strategies to achieve sub-10ms latency targets.

Performance Targets:
- Face data retrieval: <10ms
- Frame index queries: <5ms
- Cache hit ratio: >95%
- Connection pooling: 50 concurrent
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from workflow5_schema import (
    Base,
    FaceDataCache,
    FrameIndexOptimization,
    MediaProcessingStatusEnhanced,
)

logger = logging.getLogger(__name__)


class Workflow5DataAccess:
    """
    Ultra-fast data access layer for Workflow 5 face detection optimization.

    Provides frame-indexed face retrieval with <10ms performance targets through:
    - Connection pooling and async operations
    - JSONB-optimized face data queries
    - Intelligent query planning and caching
    - Frame index optimization lookup tables
    """

    def __init__(self, database_url: str = None):
        """Initialize high-performance data access layer."""
        if database_url is None:
            # Construct async PostgreSQL URL from environment
            import os

            database_url = (
                f"postgresql+asyncpg://{os.getenv('DB_USER', 'nickgklezakos')}:"
                f"{os.getenv('DB_PASSWORD', 'change-this-password')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'ppl_vision_db')}"
            )

        # Async engine with connection pooling for performance
        self.async_engine = create_async_engine(
            database_url,
            pool_size=20,  # High connection pool for concurrency
            max_overflow=30,  # Additional connections under load
            pool_timeout=30,  # Quick timeout for responsiveness
            pool_recycle=1800,  # Recycle connections every 30 minutes
            echo=False,  # Disable SQL logging for performance
        )

        # Async session maker
        self.async_session_maker = async_sessionmaker(
            self.async_engine, expire_on_commit=False, class_=AsyncSession
        )

        # Performance monitoring
        self.query_stats = {
            "total_queries": 0,
            "avg_latency_ms": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Query cache for frequently accessed data
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL

    async def get_face_data_by_frame_range(
        self,
        media_uuid: str,
        start_frame: int,
        end_frame: int,
        confidence_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Ultra-fast frame-indexed face data retrieval.

        Target: <10ms latency for cached data, <25ms for database queries.

        Args:
            media_uuid: Media file identifier
            start_frame: Starting frame number (inclusive)
            end_frame: Ending frame number (inclusive)
            confidence_threshold: Minimum confidence score filter

        Returns:
            List of face detection data within frame range
        """
        start_time = time.perf_counter()

        try:
            # Check cache first for ultra-fast retrieval
            cache_key = (
                f"faces:{media_uuid}:{start_frame}:{end_frame}:{confidence_threshold}"
            )
            cached_data = self._get_from_cache(cache_key)

            if cached_data is not None:
                self.query_stats["cache_hits"] += 1
                logger.debug(f"Cache hit for {cache_key}")
                return cached_data

            self.query_stats["cache_misses"] += 1

            # Check if we have cached face data for this media
            async with self.async_session_maker() as session:
                # First, try to get pre-cached face data
                face_cache_result = await session.execute(
                    text(
                        """
                        SELECT cached_faces, total_frames, total_faces 
                        FROM face_data_cache 
                        WHERE media_uuid = :media_uuid 
                        LIMIT 1
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                face_cache_row = face_cache_result.fetchone()

                if face_cache_row:
                    # Extract faces from cached JSONB data
                    cached_faces = face_cache_row[0] if face_cache_row[0] else []

                    # Filter by frame range and confidence
                    filtered_faces = [
                        face
                        for face in cached_faces
                        if (
                            start_frame <= face.get("frame_number", 0) <= end_frame
                            and face.get("confidence", 0.0) >= confidence_threshold
                        )
                    ]

                    # Cache the result
                    self._set_cache(cache_key, filtered_faces)

                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    self._update_performance_stats(elapsed_ms)

                    logger.info(
                        f"Face data retrieved in {elapsed_ms:.2f}ms (cached source)"
                    )
                    return filtered_faces

                # Fallback to direct face_detections query if no cache
                direct_result = await session.execute(
                    text(
                        """
                        SELECT 
                            frame_number,
                            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                            confidence,
                            method,
                            created_at
                        FROM face_detections 
                        WHERE media_id = :media_uuid
                        AND frame_number BETWEEN :start_frame AND :end_frame
                        AND confidence >= :confidence_threshold
                        ORDER BY frame_number, confidence DESC
                    """
                    ),
                    {
                        "media_uuid": media_uuid,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "confidence_threshold": confidence_threshold,
                    },
                )

                faces = []
                for row in direct_result:
                    face_data = {
                        "frame_number": row[0],
                        "bbox": {
                            "x1": row[1],
                            "y1": row[2],
                            "x2": row[3],
                            "y2": row[4],
                        },
                        "confidence": row[5],
                        "method": row[6],
                        "detected_at": row[7].isoformat() if row[7] else None,
                    }
                    faces.append(face_data)

                # Cache the result
                self._set_cache(cache_key, faces)

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self._update_performance_stats(elapsed_ms)

                logger.info(f"Face data retrieved in {elapsed_ms:.2f}ms (direct query)")
                return faces

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Face data retrieval failed in {elapsed_ms:.2f}ms: {e}")
            return []

    async def get_optimized_frame_lookup(
        self, media_uuid: str, target_frame: int
    ) -> Optional[Dict[str, Any]]:
        """
        Ultra-fast frame index optimization lookup.

        Target: <5ms latency using frame_index_optimization table.

        Args:
            media_uuid: Media file identifier
            target_frame: Frame number to optimize lookup for

        Returns:
            Optimization metadata for the target frame
        """
        start_time = time.perf_counter()

        try:
            async with self.async_session_maker() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT 
                            has_faces,
                            face_count,
                            detection_confidence_avg,
                            processing_time_ms
                        FROM frame_index_optimization
                        WHERE media_uuid = :media_uuid
                        AND frame_number = :target_frame
                        LIMIT 1
                    """
                    ),
                    {"media_uuid": media_uuid, "target_frame": target_frame},
                )

                row = result.fetchone()
                if row:
                    optimization_data = {
                        "has_faces": row[0],
                        "face_count": row[1],
                        "avg_confidence": row[2],
                        "processing_time_ms": row[3],
                    }

                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    logger.debug(f"Frame optimization lookup in {elapsed_ms:.2f}ms")
                    return optimization_data

                return None

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Frame optimization lookup failed in {elapsed_ms:.2f}ms: {e}")
            return None

    async def check_processing_status(self, media_uuid: str) -> Dict[str, Any]:
        """
        Fast processing status check for smart mode selection.

        Target: <3ms latency for mode selection decisions.

        Args:
            media_uuid: Media file identifier

        Returns:
            Processing status and optimization metadata
        """
        start_time = time.perf_counter()

        try:
            # Check enhanced processing status first
            async with self.async_session_maker() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT 
                            mps.face_detection_processed,
                            mps.processing_completed_at,
                            mps.total_faces_detected,
                            mps.processing_method,
                            mpse.processing_quality_score,
                            mpse.optimization_enabled,
                            mpse.cache_status,
                            mpse.avg_detection_latency,
                            mpse.face_density_score
                        FROM media_processing_status mps
                        LEFT JOIN media_processing_status_enhanced mpse
                            ON mps.media_uuid = mpse.original_processing_status_id
                        WHERE mps.media_uuid = :media_uuid
                        LIMIT 1
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                row = result.fetchone()
                if row:
                    status = {
                        "is_processed": row[0] or False,
                        "processing_completed_at": (
                            row[1].isoformat() if row[1] else None
                        ),
                        "total_faces": row[2] or 0,
                        "processing_method": row[3],
                        # Enhanced Workflow 5 data
                        "quality_score": row[4] or 0.0,
                        "optimization_enabled": row[5] if row[5] is not None else True,
                        "cache_status": row[6] or "not_cached",
                        "avg_latency_ms": row[7] or None,
                        "face_density": row[8] or 0.0,
                        # Computed optimization flags
                        "workflow5_eligible": (
                            row[0]  # is_processed
                            and (
                                row[5] if row[5] is not None else True
                            )  # optimization_enabled
                            and (row[6] in ["cached", "partial"])  # cache_status
                            and (row[4] or 0.0) > 0.6  # quality_score threshold
                        ),
                    }

                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    logger.debug(f"Processing status check in {elapsed_ms:.2f}ms")
                    return status

                # Return default status if no record found
                return {
                    "is_processed": False,
                    "workflow5_eligible": False,
                    "cache_status": "not_processed",
                }

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Processing status check failed in {elapsed_ms:.2f}ms: {e}")
            return {"is_processed": False, "workflow5_eligible": False}

    async def update_access_metrics(
        self, media_uuid: str, query_latency_ms: float
    ) -> None:
        """
        Update access metrics for performance optimization.

        Args:
            media_uuid: Media file identifier
            query_latency_ms: Query latency to record
        """
        try:
            async with self.async_session_maker() as session:
                await session.execute(
                    text(
                        """
                        UPDATE media_processing_status 
                        SET 
                            access_count = COALESCE(access_count, 0) + 1,
                            last_accessed = NOW()
                        WHERE media_uuid = :media_uuid
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                # Update enhanced metrics if available
                await session.execute(
                    text(
                        """
                        UPDATE media_processing_status_enhanced 
                        SET 
                            avg_detection_latency = (
                                COALESCE(avg_detection_latency, 0) * 0.9 + :latency * 0.1
                            ),
                            last_accessed = NOW()
                        WHERE original_processing_status_id = :media_uuid
                    """
                    ),
                    {"media_uuid": media_uuid, "latency": query_latency_ms},
                )

                await session.commit()

        except Exception as e:
            logger.warning(f"Failed to update access metrics: {e}")

    async def warm_cache_for_media(self, media_uuid: str) -> bool:
        """
        Pre-warm cache for a media file to optimize subsequent queries.

        Args:
            media_uuid: Media file identifier

        Returns:
            True if cache warming successful
        """
        try:
            start_time = time.perf_counter()

            async with self.async_session_maker() as session:
                # Get all face detections for this media
                result = await session.execute(
                    text(
                        """
                        SELECT 
                            frame_number,
                            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                            confidence,
                            method,
                            created_at
                        FROM face_detections 
                        WHERE media_id = :media_uuid
                        ORDER BY frame_number, confidence DESC
                    """
                    ),
                    {"media_uuid": media_uuid},
                )

                faces = []
                for row in result:
                    face_data = {
                        "frame_number": row[0],
                        "bbox": {
                            "x1": row[1],
                            "y1": row[2],
                            "x2": row[3],
                            "y2": row[4],
                        },
                        "confidence": row[5],
                        "method": row[6],
                        "detected_at": row[7].isoformat() if row[7] else None,
                    }
                    faces.append(face_data)

                # Update or create face cache entry
                total_frames = max([f["frame_number"] for f in faces]) if faces else 0

                await session.execute(
                    text(
                        """
                        INSERT INTO face_data_cache (
                            media_uuid, cached_faces,
                            total_frames, total_faces
                        ) VALUES (
                            :media_uuid, :faces,
                            :total_frames, :total_faces
                        )
                        ON CONFLICT (media_uuid) DO UPDATE SET
                            cached_faces = EXCLUDED.cached_faces,
                            total_frames = EXCLUDED.total_frames,
                            total_faces = EXCLUDED.total_faces,
                            last_accessed = NOW()
                    """
                    ),
                    {
                        "media_uuid": media_uuid,
                        "faces": json.dumps(faces),
                        "total_frames": total_frames,
                        "total_faces": len(faces),
                    },
                )

                await session.commit()

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"Cache warmed for {media_uuid} in {elapsed_ms:.2f}ms ({len(faces)} faces)"
                )
                return True

        except Exception as e:
            logger.error(f"Cache warming failed for {media_uuid}: {e}")
            return False

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from memory cache with TTL check."""
        if key in self._query_cache:
            cached_data, timestamp = self._query_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
            else:
                # Expired cache entry
                del self._query_cache[key]
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        """Set data in memory cache with timestamp."""
        self._query_cache[key] = (data, time.time())

        # Simple cache cleanup - remove oldest entries if cache grows too large
        if len(self._query_cache) > 1000:
            # Remove 20% of oldest entries
            sorted_items = sorted(
                self._query_cache.items(), key=lambda x: x[1][1]  # Sort by timestamp
            )
            for key_to_remove, _ in sorted_items[:200]:
                del self._query_cache[key_to_remove]

    def _update_performance_stats(self, latency_ms: float) -> None:
        """Update performance statistics."""
        self.query_stats["total_queries"] += 1

        # Exponential moving average for latency
        if self.query_stats["avg_latency_ms"] == 0.0:
            self.query_stats["avg_latency_ms"] = latency_ms
        else:
            self.query_stats["avg_latency_ms"] = (
                self.query_stats["avg_latency_ms"] * 0.9 + latency_ms * 0.1
            )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        cache_total = self.query_stats["cache_hits"] + self.query_stats["cache_misses"]
        cache_hit_ratio = (
            self.query_stats["cache_hits"] / cache_total if cache_total > 0 else 0.0
        )

        return {
            **self.query_stats,
            "cache_hit_ratio": cache_hit_ratio,
            "cache_size": len(self._query_cache),
            "target_latency_ms": 10.0,
            "performance_status": (
                "optimal"
                if self.query_stats["avg_latency_ms"] < 10.0
                else (
                    "acceptable"
                    if self.query_stats["avg_latency_ms"] < 25.0
                    else "degraded"
                )
            ),
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.async_engine.dispose()


# Singleton instance for easy import
workflow5_data_access = Workflow5DataAccess()

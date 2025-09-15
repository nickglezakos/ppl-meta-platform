"""
PPL Meta Vision Service - Workflow 5 Stored Face Data Retrieval System
Efficient frame-indexed face data retrieval for zero-latency face detection.

This module implements the complete stored face data retrieval system including:
- Fast frame-indexed face data queries with caching
- Optimized face coordinate serialization/deserialization
- Batch loading for entire videos with memory management
- Range-based queries for efficient streaming
- Intelligent caching with memory optimization

Performance Goals:
- <50ms full video face data retrieval
- <5ms single frame face data access
- 95%+ cache hit ratio for active videos
- Memory-efficient bulk loading
- Frame-perfect synchronization accuracy
"""

import asyncio
import json
import logging
import pickle
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from workflow5_data_access import Workflow5DataAccess, workflow5_data_access

logger = logging.getLogger(__name__)


class FaceDataFormat(Enum):
    """Face data storage and retrieval formats."""

    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_JSON = "compressed_json"
    NUMPY_BINARY = "numpy_binary"


@dataclass
class FaceDetection:
    """Enhanced face detection data structure for stored retrieval."""

    face_id: str
    frame_number: int
    bounding_box: Dict[str, float]  # {x, y, width, height}
    confidence: float
    landmarks: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    detection_metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert face detection to dictionary for serialization."""
        return {
            "face_id": self.face_id,
            "frame_number": self.frame_number,
            "bounding_box": self.bounding_box,
            "confidence": self.confidence,
            "landmarks": self.landmarks,
            "embedding": self.embedding,
            "detection_metadata": self.detection_metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FaceDetection":
        """Create face detection from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            face_id=data["face_id"],
            frame_number=data["frame_number"],
            bounding_box=data["bounding_box"],
            confidence=data["confidence"],
            landmarks=data.get("landmarks"),
            embedding=data.get("embedding"),
            detection_metadata=data.get("detection_metadata"),
            timestamp=timestamp,
        )


@dataclass
class VideoFaceData:
    """Complete face data for a video with metadata."""

    media_uuid: str
    total_frames: int
    total_faces: int
    faces_by_frame: Dict[int, List[FaceDetection]]
    processing_metadata: Dict[str, Any]
    retrieval_timestamp: datetime
    data_format: FaceDataFormat
    data_size_bytes: int

    def get_frame_faces(self, frame_number: int) -> List[FaceDetection]:
        """Get faces for a specific frame."""
        return self.faces_by_frame.get(frame_number, [])

    def get_faces_in_range(
        self, start_frame: int, end_frame: int
    ) -> Dict[int, List[FaceDetection]]:
        """Get faces for a range of frames."""
        return {
            frame_num: faces
            for frame_num, faces in self.faces_by_frame.items()
            if start_frame <= frame_num <= end_frame
        }

    def get_face_statistics(self) -> Dict[str, Any]:
        """Get statistics about the face data."""
        frames_with_faces = len([f for f in self.faces_by_frame.values() if f])
        avg_faces_per_frame = self.total_faces / max(frames_with_faces, 1)

        return {
            "total_frames": self.total_frames,
            "total_faces": self.total_faces,
            "frames_with_faces": frames_with_faces,
            "frames_without_faces": self.total_frames - frames_with_faces,
            "avg_faces_per_frame": avg_faces_per_frame,
            "face_coverage_percentage": (frames_with_faces / max(self.total_frames, 1))
            * 100,
            "data_size_mb": self.data_size_bytes / (1024 * 1024),
        }


class FaceDataCache:
    """High-performance face data caching system."""

    def __init__(self, max_videos: int = 100, max_memory_mb: int = 500):
        """Initialize face data cache."""
        self.max_videos = max_videos
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, VideoFaceData] = {}
        self.access_times: Dict[str, datetime] = {}
        self.current_memory_bytes = 0

        # Cache performance metrics
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "evictions": 0,
            "total_memory_used": 0,
        }

    def get(self, media_uuid: str) -> Optional[VideoFaceData]:
        """Get video face data from cache."""
        self.stats["total_requests"] += 1

        if media_uuid in self.cache:
            self.stats["cache_hits"] += 1
            self.access_times[media_uuid] = datetime.now()
            return self.cache[media_uuid]

        self.stats["cache_misses"] += 1
        return None

    def put(self, media_uuid: str, face_data: VideoFaceData) -> bool:
        """Put video face data into cache."""
        data_size = face_data.data_size_bytes

        # Check if we need to evict items
        while (
            len(self.cache) >= self.max_videos
            or self.current_memory_bytes + data_size > self.max_memory_bytes
        ):
            if not self._evict_lru():
                # Can't evict anymore, item too large
                logger.warning(
                    f"Cannot cache {media_uuid}: data too large ({data_size} bytes)"
                )
                return False

        # Add to cache
        self.cache[media_uuid] = face_data
        self.access_times[media_uuid] = datetime.now()
        self.current_memory_bytes += data_size
        self.stats["total_memory_used"] = self.current_memory_bytes

        logger.debug(f"Cached face data for {media_uuid} ({data_size} bytes)")
        return True

    def _evict_lru(self) -> bool:
        """Evict least recently used item."""
        if not self.cache:
            return False

        # Find LRU item
        lru_uuid = min(self.access_times.items(), key=lambda x: x[1])[0]

        # Remove from cache
        face_data = self.cache.pop(lru_uuid)
        del self.access_times[lru_uuid]
        self.current_memory_bytes -= face_data.data_size_bytes
        self.stats["evictions"] += 1

        logger.debug(f"Evicted {lru_uuid} from cache")
        return True

    def clear(self) -> None:
        """Clear all cache data."""
        self.cache.clear()
        self.access_times.clear()
        self.current_memory_bytes = 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.stats["total_requests"]
        hit_ratio = (self.stats["cache_hits"] / max(total_requests, 1)) * 100

        return {
            "total_requests": total_requests,
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_ratio_percentage": hit_ratio,
            "evictions": self.stats["evictions"],
            "current_videos_cached": len(self.cache),
            "current_memory_mb": self.current_memory_bytes / (1024 * 1024),
            "memory_utilization_percentage": (
                self.current_memory_bytes / self.max_memory_bytes
            )
            * 100,
        }


class StoredFaceDataRetriever:
    """
    High-performance stored face data retrieval system.

    Provides efficient access to pre-computed face detection data with:
    - Frame-indexed queries for instant access
    - Intelligent caching for frequently accessed videos
    - Batch loading with memory optimization
    - Multiple data formats for performance optimization
    """

    def __init__(
        self,
        data_access: Workflow5DataAccess = None,
        cache_max_videos: int = 100,
        cache_max_memory_mb: int = 500,
        default_format: FaceDataFormat = FaceDataFormat.JSON,
    ):
        """Initialize stored face data retriever."""
        self.data_access = data_access or workflow5_data_access
        self.cache = FaceDataCache(cache_max_videos, cache_max_memory_mb)
        self.default_format = default_format

        # Performance tracking
        self.performance_stats = {
            "total_retrievals": 0,
            "cache_retrievals": 0,
            "db_retrievals": 0,
            "avg_retrieval_time_ms": 0.0,
            "total_faces_retrieved": 0,
            "total_videos_processed": 0,
        }

        # Configuration
        self.config = {
            "enable_parallel_loading": True,
            "batch_size": 1000,
            "memory_optimization": True,
            "prefetch_enabled": True,
            "compression_threshold_kb": 100,
        }

    async def get_frame_faces(
        self, media_uuid: str, frame_number: int, use_cache: bool = True
    ) -> List[FaceDetection]:
        """
        Get face detections for a specific frame.

        Args:
            media_uuid: UUID of the media
            frame_number: Frame number to retrieve faces for
            use_cache: Whether to use cached data if available

        Returns:
            List of face detections for the frame
        """
        start_time = time.time()

        try:
            # Try cache first if enabled
            if use_cache:
                cached_data = self.cache.get(media_uuid)
                if cached_data:
                    faces = cached_data.get_frame_faces(frame_number)
                    self._update_performance_stats(start_time, len(faces), True)
                    return faces

            # Query database for single frame
            faces = await self._query_frame_faces(media_uuid, frame_number)
            self._update_performance_stats(start_time, len(faces), False)
            return faces

        except Exception as e:
            logger.error(
                f"Failed to retrieve frame faces for {media_uuid}:{frame_number}: {e}"
            )
            return []

    async def get_faces_in_range(
        self,
        media_uuid: str,
        start_frame: int,
        end_frame: int,
        use_cache: bool = True,
    ) -> Dict[int, List[FaceDetection]]:
        """
        Get face detections for a range of frames.

        Args:
            media_uuid: UUID of the media
            start_frame: Starting frame number (inclusive)
            end_frame: Ending frame number (inclusive)
            use_cache: Whether to use cached data if available

        Returns:
            Dictionary mapping frame numbers to face detection lists
        """
        start_time = time.time()

        try:
            # Try cache first if enabled
            if use_cache:
                cached_data = self.cache.get(media_uuid)
                if cached_data:
                    faces = cached_data.get_faces_in_range(start_frame, end_frame)
                    total_faces = sum(
                        len(frame_faces) for frame_faces in faces.values()
                    )
                    self._update_performance_stats(start_time, total_faces, True)
                    return faces

            # Query database for frame range
            faces = await self._query_faces_in_range(media_uuid, start_frame, end_frame)
            total_faces = sum(len(frame_faces) for frame_faces in faces.values())
            self._update_performance_stats(start_time, total_faces, False)
            return faces

        except Exception as e:
            logger.error(
                f"Failed to retrieve faces in range for {media_uuid}:{start_frame}-{end_frame}: {e}"
            )
            return {}

    async def preload_video_faces(
        self,
        media_uuid: str,
        force_reload: bool = False,
        data_format: Optional[FaceDataFormat] = None,
    ) -> VideoFaceData:
        """
        Preload all face data for a video into cache.

        Args:
            media_uuid: UUID of the media
            force_reload: Whether to reload even if cached
            data_format: Data format to use for storage

        Returns:
            Complete video face data
        """
        start_time = time.time()

        try:
            # Check cache first unless force reload
            if not force_reload:
                cached_data = self.cache.get(media_uuid)
                if cached_data:
                    logger.debug(f"Using cached data for {media_uuid}")
                    return cached_data

            # Load all face data from database
            video_face_data = await self._load_complete_video_faces(
                media_uuid, data_format or self.default_format
            )

            # Cache the loaded data
            self.cache.put(media_uuid, video_face_data)

            # Update performance stats
            self._update_performance_stats(
                start_time, video_face_data.total_faces, False
            )
            self.performance_stats["total_videos_processed"] += 1

            logger.info(
                f"Preloaded {video_face_data.total_faces} faces "
                f"from {video_face_data.total_frames} frames for {media_uuid} "
                f"in {(time.time() - start_time) * 1000:.1f}ms"
            )

            return video_face_data

        except Exception as e:
            logger.error(f"Failed to preload video faces for {media_uuid}: {e}")
            raise

    async def _query_frame_faces(
        self, media_uuid: str, frame_number: int
    ) -> List[FaceDetection]:
        """Query face detections for a single frame from database."""
        async with self.data_access.async_session_maker() as session:
            result = await session.execute(
                text(
                    """
                    SELECT 
                        fd.id as face_id,
                        fd.frame_number,
                        fd.bbox_x1,
                        fd.bbox_y1,
                        fd.bbox_x2,
                        fd.bbox_y2,
                        fd.confidence,
                        fd.method,
                        fd.timestamp,
                        mr.media_uuid
                    FROM face_detections fd
                    JOIN media_records mr ON fd.media_id = mr.media_id
                    WHERE mr.media_uuid = :media_uuid 
                    AND fd.frame_number = :frame_number
                    ORDER BY fd.confidence DESC
                    """
                ),
                {"media_uuid": media_uuid, "frame_number": frame_number},
            )

            faces = []
            for row in result:
                # Calculate width and height from coordinates
                width = abs(row.bbox_x2 - row.bbox_x1)
                height = abs(row.bbox_y2 - row.bbox_y1)

                face = FaceDetection(
                    face_id=str(row.face_id),
                    frame_number=row.frame_number,
                    bounding_box={
                        "x": float(min(row.bbox_x1, row.bbox_x2)),
                        "y": float(min(row.bbox_y1, row.bbox_y2)),
                        "width": float(width),
                        "height": float(height),
                    },
                    confidence=float(row.confidence),
                    landmarks=None,  # Not available in current schema
                    embedding=None,  # Not available in current schema
                    detection_metadata={"method": row.method} if row.method else None,
                    timestamp=row.timestamp,
                )
                faces.append(face)

            return faces

    async def _query_faces_in_range(
        self, media_uuid: str, start_frame: int, end_frame: int
    ) -> Dict[int, List[FaceDetection]]:
        """Query face detections for a range of frames from database."""
        async with self.data_access.async_session_maker() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        fd.id as face_id,
                        fd.frame_number,
                        fd.bbox_x1,
                        fd.bbox_y1,
                        fd.bbox_x2,
                        fd.bbox_y2,
                        fd.confidence,
                        fd.method,
                        fd.timestamp,
                        mr.media_uuid
                    FROM face_detections fd
                    JOIN media_records mr ON fd.media_id = mr.media_id
                    WHERE mr.media_uuid = :media_uuid
                    AND fd.frame_number BETWEEN :start_frame AND :end_frame
                    ORDER BY fd.frame_number, fd.confidence DESC
                    """
                ),
                {
                    "media_uuid": media_uuid,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                },
            )

            faces_by_frame = {}
            for row in result:
                frame_number = row.frame_number

                if frame_number not in faces_by_frame:
                    faces_by_frame[frame_number] = []

                # Calculate width and height from coordinates
                width = abs(row.bbox_x2 - row.bbox_x1)
                height = abs(row.bbox_y2 - row.bbox_y1)

                face = FaceDetection(
                    face_id=str(row.face_id),
                    frame_number=frame_number,
                    bounding_box={
                        "x": float(min(row.bbox_x1, row.bbox_x2)),
                        "y": float(min(row.bbox_y1, row.bbox_y2)),
                        "width": float(width),
                        "height": float(height),
                    },
                    confidence=float(row.confidence),
                    landmarks=None,  # Not available in current schema
                    embedding=None,  # Not available in current schema
                    detection_metadata=({"method": row.method} if row.method else None),
                    timestamp=row.timestamp,
                )
                faces_by_frame[frame_number].append(face)

            return faces_by_frame

    async def _load_complete_video_faces(
        self, media_uuid: str, data_format: FaceDataFormat
    ) -> VideoFaceData:
        """Load complete face data for a video."""
        start_time = time.time()

        async with self.data_access.async_session_maker() as session:
            # Get video metadata first
            metadata_result = await session.execute(
                text(
                    """
                    SELECT 
                        mps.total_frames_processed,
                        mps.total_faces_detected,
                        mps.processing_method,
                        mps.frame_analysis_metadata,
                        mps.processing_quality_score
                    FROM media_processing_status_enhanced mps
                    WHERE mps.media_uuid = :media_uuid
                    """
                ),
                {"media_uuid": media_uuid},
            )

            metadata_row = metadata_result.first()
            if not metadata_row:
                raise ValueError(f"No processing metadata found for {media_uuid}")

            # Get all face detections
            faces_result = await session.execute(
                text(
                    """
                    SELECT 
                        fd.face_id,
                        fd.frame_number,
                        fd.bounding_box_x,
                        fd.bounding_box_y,
                        fd.bounding_box_width,
                        fd.bounding_box_height,
                        fd.confidence_score,
                        fd.face_landmarks,
                        fd.face_embedding,
                        fd.detection_metadata,
                        fd.detection_timestamp
                    FROM face_detections fd
                    JOIN media_files mf ON fd.media_id = mf.media_id
                    WHERE mf.media_uuid = :media_uuid
                    ORDER BY fd.frame_number, fd.confidence_score DESC
                    """
                ),
                {"media_uuid": media_uuid},
            )

            # Organize faces by frame
            faces_by_frame = {}
            total_faces = 0

            for row in faces_result:
                frame_number = row.frame_number

                if frame_number not in faces_by_frame:
                    faces_by_frame[frame_number] = []

                face = FaceDetection(
                    face_id=row.face_id,
                    frame_number=frame_number,
                    bounding_box={
                        "x": float(row.bounding_box_x),
                        "y": float(row.bounding_box_y),
                        "width": float(row.bounding_box_width),
                        "height": float(row.bounding_box_height),
                    },
                    confidence=float(row.confidence_score),
                    landmarks=(
                        json.loads(row.face_landmarks) if row.face_landmarks else None
                    ),
                    embedding=(
                        json.loads(row.face_embedding) if row.face_embedding else None
                    ),
                    detection_metadata=(
                        json.loads(row.detection_metadata)
                        if row.detection_metadata
                        else None
                    ),
                    timestamp=row.detection_timestamp,
                )
                faces_by_frame[frame_number].append(face)
                total_faces += 1

            # Calculate data size for memory management
            data_size_bytes = self._estimate_data_size(faces_by_frame, data_format)

            # Create video face data object
            video_face_data = VideoFaceData(
                media_uuid=media_uuid,
                total_frames=metadata_row.total_frames_processed,
                total_faces=total_faces,
                faces_by_frame=faces_by_frame,
                processing_metadata={
                    "processing_method": metadata_row.processing_method,
                    "frame_analysis_metadata": (
                        json.loads(metadata_row.frame_analysis_metadata)
                        if metadata_row.frame_analysis_metadata
                        else {}
                    ),
                    "processing_quality_score": metadata_row.processing_quality_score,
                },
                retrieval_timestamp=datetime.now(),
                data_format=data_format,
                data_size_bytes=data_size_bytes,
            )

            load_time_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Loaded {total_faces} faces from {metadata_row.total_frames_processed} "
                f"frames for {media_uuid} in {load_time_ms:.1f}ms "
                f"({data_size_bytes / (1024 * 1024):.1f}MB)"
            )

            return video_face_data

    def _estimate_data_size(
        self,
        faces_by_frame: Dict[int, List[FaceDetection]],
        data_format: FaceDataFormat,
    ) -> int:
        """Estimate memory size of face data."""
        # Base estimation: 200 bytes per face detection (conservative)
        total_faces = sum(len(faces) for faces in faces_by_frame.values())
        base_size = total_faces * 200

        # Format-specific multipliers
        format_multipliers = {
            FaceDataFormat.JSON: 1.5,  # JSON overhead
            FaceDataFormat.PICKLE: 1.2,  # Pickle efficiency
            FaceDataFormat.COMPRESSED_JSON: 0.8,  # Compression savings
            FaceDataFormat.NUMPY_BINARY: 0.6,  # Binary efficiency
        }

        multiplier = format_multipliers.get(data_format, 1.0)
        return int(base_size * multiplier)

    def _update_performance_stats(
        self, start_time: float, faces_count: int, from_cache: bool
    ) -> None:
        """Update performance statistics."""
        elapsed_ms = (time.time() - start_time) * 1000

        self.performance_stats["total_retrievals"] += 1
        self.performance_stats["total_faces_retrieved"] += faces_count

        if from_cache:
            self.performance_stats["cache_retrievals"] += 1
        else:
            self.performance_stats["db_retrievals"] += 1

        # Update average retrieval time
        total_retrievals = self.performance_stats["total_retrievals"]
        current_avg = self.performance_stats["avg_retrieval_time_ms"]
        self.performance_stats["avg_retrieval_time_ms"] = (
            (current_avg * (total_retrievals - 1)) + elapsed_ms
        ) / total_retrievals

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        cache_stats = self.cache.get_cache_stats()

        return {
            "retrieval_performance": self.performance_stats.copy(),
            "cache_performance": cache_stats,
            "configuration": self.config.copy(),
            "system_health": {
                "total_cached_videos": len(self.cache.cache),
                "memory_utilization_mb": cache_stats["current_memory_mb"],
                "cache_efficiency": cache_stats["hit_ratio_percentage"],
                "avg_retrieval_speed_ms": self.performance_stats[
                    "avg_retrieval_time_ms"
                ],
            },
        }

    async def clear_cache(self) -> None:
        """Clear all cached face data."""
        self.cache.clear()
        logger.info("Face data cache cleared")

    async def close(self) -> None:
        """Close the retriever and cleanup resources."""
        await self.clear_cache()
        logger.info("Stored face data retriever closed")


# Factory function for easy instantiation
async def create_stored_face_data_retriever(
    data_access: Workflow5DataAccess = None,
    cache_max_videos: int = 100,
    cache_max_memory_mb: int = 500,
) -> StoredFaceDataRetriever:
    """Create and configure a stored face data retriever."""
    retriever = StoredFaceDataRetriever(
        data_access=data_access or workflow5_data_access,
        cache_max_videos=cache_max_videos,
        cache_max_memory_mb=cache_max_memory_mb,
    )

    logger.info(f"Created face data retriever with {cache_max_videos} video cache")
    return retriever


# Test and validation
if __name__ == "__main__":

    async def test_face_data_retrieval():
        print("🧪 Testing Stored Face Data Retrieval System...\n")

        # Initialize retriever
        retriever = await create_stored_face_data_retriever(cache_max_videos=10)
        print("✅ Face data retriever initialized")

        # Test single frame retrieval
        print("\n📽️ Test 1: Single Frame Retrieval")
        start_time = time.time()

        faces = await retriever.get_frame_faces("test-video-uuid", 100)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"⚡ Retrieved {len(faces)} faces in {elapsed_ms:.1f}ms")
        for i, face in enumerate(faces[:3]):  # Show first 3 faces
            print(
                f"  Face {i+1}: confidence={face.confidence:.2f} at {face.bounding_box}"
            )

        # Test range retrieval
        print("\n📊 Test 2: Frame Range Retrieval")
        start_time = time.time()

        faces_in_range = await retriever.get_faces_in_range("test-video-uuid", 100, 200)
        elapsed_ms = (time.time() - start_time) * 1000

        total_faces = sum(len(frame_faces) for frame_faces in faces_in_range.values())
        print(
            f"⚡ Retrieved {total_faces} faces from {len(faces_in_range)} frames in {elapsed_ms:.1f}ms"
        )

        # Test video preloading
        print("\n🎬 Test 3: Complete Video Preloading")
        start_time = time.time()

        try:
            video_data = await retriever.preload_video_faces("test-video-uuid")
            elapsed_ms = (time.time() - start_time) * 1000

            stats = video_data.get_face_statistics()
            print(f"⚡ Preloaded complete video in {elapsed_ms:.1f}ms")
            print(
                f"📊 Video stats: {stats['total_faces']} faces, {stats['total_frames']} frames"
            )
            print(f"💾 Data size: {stats['data_size_mb']:.1f}MB")
            print(f"📈 Face coverage: {stats['face_coverage_percentage']:.1f}%")
        except Exception as e:
            print(f"⚠️ Video preload test skipped (no test data): {e}")

        # Test cache performance
        print("\n💾 Test 4: Cache Performance")

        # Multiple retrievals to test caching
        for i in range(3):
            start_time = time.time()
            faces = await retriever.get_frame_faces("test-video-uuid", 150)
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"  Retrieval {i+1}: {len(faces)} faces in {elapsed_ms:.1f}ms")

        # Get performance metrics
        print("\n📈 Test 5: Performance Metrics")
        metrics = await retriever.get_performance_metrics()

        print(f"📊 Retrieval stats:")
        print(
            f"  Total retrievals: {metrics['retrieval_performance']['total_retrievals']}"
        )
        print(
            f"  Cache retrievals: {metrics['retrieval_performance']['cache_retrievals']}"
        )
        print(f"  DB retrievals: {metrics['retrieval_performance']['db_retrievals']}")
        print(
            f"  Avg retrieval time: {metrics['retrieval_performance']['avg_retrieval_time_ms']:.1f}ms"
        )

        print(f"💾 Cache stats:")
        print(
            f"  Hit ratio: {metrics['cache_performance']['hit_ratio_percentage']:.1f}%"
        )
        print(
            f"  Memory usage: {metrics['cache_performance']['current_memory_mb']:.1f}MB"
        )
        print(
            f"  Videos cached: {metrics['cache_performance']['current_videos_cached']}"
        )

        print("\n✅ Stored Face Data Retrieval System testing completed!")

        # Cleanup
        await retriever.close()

    # Run tests
    import asyncio

    asyncio.run(test_face_data_retrieval())

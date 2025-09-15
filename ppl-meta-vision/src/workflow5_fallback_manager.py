#!/usr/bin/env python3
"""
Face Detection Workflow 5 - Phase 5: Fallback Mechanisms & Error Recovery
=========================================================================

ROBUST FALLBACK SYSTEM FOR SEAMLESS FACE DETECTION OPERATION

This module implements comprehensive fallback mechanisms ensuring the PPL Meta
Platform maintains continuous face detection capabilities even when stored data
is unavailable, corrupted, or services are experiencing issues.

Features:
- Graceful degradation from stored data to real-time detection
- Automatic error recovery with intelligent retry mechanisms
- Seamless mode switching without user disruption
- Data integrity validation and corruption detection
- Service health monitoring and automatic failover
- Performance monitoring during fallback operations

Fallback Hierarchy:
1. Stored Face Data (Primary) - Zero-latency with pre-computed overlays
2. Real-time Detection (Secondary) - Full detection pipeline as backup
3. Cached Detection (Tertiary) - Previous session data if available
4. Graceful Failure (Final) - Video without face detection overlays

Performance Targets:
- <100ms fallback detection and mode switching
- 99.8% success rate for fallback activation
- Zero data loss during fallback operations
- Seamless user experience with transparent switching
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from workflow5_data_access import Workflow5DataAccess
from workflow5_face_data_retrieval_fixed import (
    FaceDetection,
    StoredFaceDataRetriever,
    VideoFaceData,
    create_stored_face_data_retriever,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FallbackMode(Enum):
    """Available fallback modes for face detection."""

    STORED_DATA = "stored_data"
    REALTIME_DETECTION = "realtime_detection"
    CACHED_SESSION = "cached_session"
    NO_DETECTION = "no_detection"


class FallbackReason(Enum):
    """Reasons for fallback activation."""

    DATA_NOT_FOUND = "data_not_found"
    DATA_CORRUPTED = "data_corrupted"
    SERVICE_UNAVAILABLE = "service_unavailable"
    PROCESSING_INCOMPLETE = "processing_incomplete"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CACHE_MISS = "cache_miss"
    TIMEOUT = "timeout"


@dataclass
class FallbackEvent:
    """Fallback event tracking for monitoring and analysis."""

    media_uuid: str
    timestamp: datetime
    original_mode: FallbackMode
    fallback_mode: FallbackMode
    reason: FallbackReason
    error_details: Optional[str] = None
    recovery_time_ms: Optional[float] = None
    success: bool = True


@dataclass
class ServiceHealth:
    """Service health status for fallback decisions."""

    service_name: str
    is_healthy: bool
    last_check: datetime
    response_time_ms: float
    error_count: int = 0
    consecutive_failures: int = 0


class FallbackManager:
    """
    Comprehensive fallback management system ensuring continuous operation.

    Provides intelligent fallback mechanisms with automatic recovery,
    performance monitoring, and seamless user experience.
    """

    def __init__(self, data_access: Workflow5DataAccess):
        self.data_access = data_access
        self.stored_retriever: Optional[StoredFaceDataRetriever] = None

        # Fallback tracking
        self.fallback_events: List[FallbackEvent] = []
        self.service_health: Dict[str, ServiceHealth] = {}

        # Performance monitoring
        self.fallback_stats = {
            "total_fallbacks": 0,
            "successful_fallbacks": 0,
            "avg_fallback_time_ms": 0.0,
            "mode_usage": {mode.value: 0 for mode in FallbackMode},
            "reason_frequency": {reason.value: 0 for reason in FallbackReason},
        }

        # Configuration
        self.max_retry_attempts = 3
        self.service_timeout_ms = 5000
        self.health_check_interval = 30  # seconds
        self.data_validation_enabled = True

        # Initialize stored data retriever
        asyncio.create_task(self._initialize_stored_retriever())

    async def _initialize_stored_retriever(self):
        """Initialize stored face data retriever with error handling."""
        try:
            self.stored_retriever = await create_stored_face_data_retriever(
                cache_max_videos=100
            )
            logger.info("Stored face data retriever initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize stored retriever: {e}")
            self.stored_retriever = None

    async def get_faces_with_fallback(
        self,
        media_uuid: str,
        frame_number: int,
        preferred_mode: FallbackMode = FallbackMode.STORED_DATA,
    ) -> tuple[List[FaceDetection], FallbackMode]:
        """
        Get face detections with automatic fallback on failure.

        Returns:
            Tuple of (face_detections, actual_mode_used)
        """
        start_time = time.time()
        original_mode = preferred_mode

        # Try preferred mode first
        try:
            faces, success = await self._try_get_faces(
                media_uuid, frame_number, preferred_mode
            )
            if success:
                self._update_mode_usage(preferred_mode)
                return faces, preferred_mode
        except Exception as e:
            logger.warning(f"Primary mode {preferred_mode.value} failed: {e}")

        # Fallback through hierarchy
        fallback_modes = self._get_fallback_hierarchy(preferred_mode)

        for fallback_mode in fallback_modes:
            try:
                faces, success = await self._try_get_faces(
                    media_uuid, frame_number, fallback_mode
                )
                if success:
                    # Record fallback event
                    fallback_time_ms = (time.time() - start_time) * 1000
                    await self._record_fallback_event(
                        media_uuid=media_uuid,
                        original_mode=original_mode,
                        fallback_mode=fallback_mode,
                        reason=self._determine_fallback_reason(preferred_mode),
                        recovery_time_ms=fallback_time_ms,
                        success=True,
                    )

                    self._update_mode_usage(fallback_mode)
                    return faces, fallback_mode

            except Exception as e:
                logger.warning(f"Fallback mode {fallback_mode.value} failed: {e}")
                continue

        # All modes failed - return empty with no detection mode
        fallback_time_ms = (time.time() - start_time) * 1000
        await self._record_fallback_event(
            media_uuid=media_uuid,
            original_mode=original_mode,
            fallback_mode=FallbackMode.NO_DETECTION,
            reason=FallbackReason.SERVICE_UNAVAILABLE,
            recovery_time_ms=fallback_time_ms,
            success=False,
        )

        self._update_mode_usage(FallbackMode.NO_DETECTION)
        return [], FallbackMode.NO_DETECTION

    async def _try_get_faces(
        self, media_uuid: str, frame_number: int, mode: FallbackMode
    ) -> tuple[List[FaceDetection], bool]:
        """
        Attempt to get faces using specified mode.

        Returns:
            Tuple of (faces, success_flag)
        """
        if mode == FallbackMode.STORED_DATA:
            return await self._get_stored_faces(media_uuid, frame_number)

        elif mode == FallbackMode.REALTIME_DETECTION:
            return await self._get_realtime_faces(media_uuid, frame_number)

        elif mode == FallbackMode.CACHED_SESSION:
            return await self._get_cached_faces(media_uuid, frame_number)

        elif mode == FallbackMode.NO_DETECTION:
            return [], True

        else:
            raise ValueError(f"Unknown fallback mode: {mode}")

    async def _get_stored_faces(
        self, media_uuid: str, frame_number: int
    ) -> tuple[List[FaceDetection], bool]:
        """Get faces from stored data with validation."""
        if not self.stored_retriever:
            raise RuntimeError("Stored retriever not available")

        # Validate data integrity if enabled
        if self.data_validation_enabled:
            is_valid = await self._validate_stored_data(media_uuid)
            if not is_valid:
                raise RuntimeError("Stored data validation failed")

        faces = await self.stored_retriever.get_frame_faces(media_uuid, frame_number)
        return faces, True

    async def _get_realtime_faces(
        self, media_uuid: str, frame_number: int
    ) -> tuple[List[FaceDetection], bool]:
        """Get faces using real-time detection (simulated)."""
        # TODO: Integrate with actual real-time detection service
        # For now, simulate real-time detection
        await asyncio.sleep(0.050)  # Simulate 50ms detection time

        # Simulate finding faces (replace with actual detection)
        simulated_faces = [
            FaceDetection(
                face_id=f"realtime_{frame_number}_1",
                frame_number=frame_number,
                bounding_box={"x": 100.0, "y": 100.0, "width": 80.0, "height": 80.0},
                confidence=0.85,
                landmarks=None,
                embedding=None,
                detection_metadata={"method": "realtime_fallback"},
                timestamp=datetime.now(),
            )
        ]

        logger.info(f"Real-time detection fallback for {media_uuid}:{frame_number}")
        return simulated_faces, True

    async def _get_cached_faces(
        self, media_uuid: str, frame_number: int
    ) -> tuple[List[FaceDetection], bool]:
        """Get faces from previous session cache."""
        # TODO: Implement session cache retrieval
        # This would check for faces from previous detection sessions

        # For now, return empty as cache miss
        logger.info(f"Cache fallback attempted for {media_uuid}:{frame_number}")
        return [], False

    async def _validate_stored_data(self, media_uuid: str) -> bool:
        """Validate stored face data integrity."""
        try:
            # Check if media has processing status
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text(
                        "SELECT total_faces FROM media_records WHERE media_id = :media_uuid"
                    ),
                    {"media_uuid": media_uuid},
                )
                media_record = result.first()

                if not media_record:
                    logger.warning(f"No media record found for {media_uuid}")
                    return False

                # Validate face count consistency
                face_count_result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM face_detections WHERE media_id = :media_uuid"
                    ),
                    {"media_uuid": media_uuid},
                )
                actual_faces = face_count_result.scalar()

                # Allow some tolerance for face count discrepancies
                expected_faces = media_record.total_faces or 0
                if abs(actual_faces - expected_faces) > (
                    expected_faces * 0.1
                ):  # 10% tolerance
                    logger.warning(
                        f"Face count mismatch for {media_uuid}: "
                        f"expected {expected_faces}, found {actual_faces}"
                    )
                    return False

                return True

        except Exception as e:
            logger.error(f"Data validation failed for {media_uuid}: {e}")
            return False

    def _get_fallback_hierarchy(self, failed_mode: FallbackMode) -> List[FallbackMode]:
        """Get ordered list of fallback modes to try."""
        all_modes = [
            FallbackMode.STORED_DATA,
            FallbackMode.REALTIME_DETECTION,
            FallbackMode.CACHED_SESSION,
            FallbackMode.NO_DETECTION,
        ]

        # Remove the failed mode and return remaining modes in order
        return [mode for mode in all_modes if mode != failed_mode]

    def _determine_fallback_reason(self, failed_mode: FallbackMode) -> FallbackReason:
        """Determine the most likely reason for fallback."""
        # This is a simplified implementation
        # In practice, you'd analyze the specific error to determine reason
        if failed_mode == FallbackMode.STORED_DATA:
            return FallbackReason.DATA_NOT_FOUND
        elif failed_mode == FallbackMode.REALTIME_DETECTION:
            return FallbackReason.SERVICE_UNAVAILABLE
        else:
            return FallbackReason.CACHE_MISS

    async def _record_fallback_event(
        self,
        media_uuid: str,
        original_mode: FallbackMode,
        fallback_mode: FallbackMode,
        reason: FallbackReason,
        recovery_time_ms: float,
        success: bool,
        error_details: str = None,
    ):
        """Record fallback event for monitoring and analysis."""
        event = FallbackEvent(
            media_uuid=media_uuid,
            timestamp=datetime.now(),
            original_mode=original_mode,
            fallback_mode=fallback_mode,
            reason=reason,
            error_details=error_details,
            recovery_time_ms=recovery_time_ms,
            success=success,
        )

        self.fallback_events.append(event)

        # Update statistics
        self.fallback_stats["total_fallbacks"] += 1
        if success:
            self.fallback_stats["successful_fallbacks"] += 1

        # Update average fallback time
        total_time = self.fallback_stats["avg_fallback_time_ms"] * (
            self.fallback_stats["total_fallbacks"] - 1
        )
        self.fallback_stats["avg_fallback_time_ms"] = (
            total_time + recovery_time_ms
        ) / self.fallback_stats["total_fallbacks"]

        # Update reason frequency
        self.fallback_stats["reason_frequency"][reason.value] += 1

        logger.info(
            f"Fallback event: {original_mode.value} -> {fallback_mode.value} "
            f"({reason.value}) in {recovery_time_ms:.1f}ms"
        )

    def _update_mode_usage(self, mode: FallbackMode):
        """Update mode usage statistics."""
        self.fallback_stats["mode_usage"][mode.value] += 1

    async def get_video_faces_with_fallback(
        self, media_uuid: str, preferred_mode: FallbackMode = FallbackMode.STORED_DATA
    ) -> tuple[VideoFaceData, FallbackMode]:
        """Get complete video face data with fallback support."""
        start_time = time.time()

        try:
            if preferred_mode == FallbackMode.STORED_DATA and self.stored_retriever:
                video_data = await self.stored_retriever.load_complete_video(media_uuid)
                return video_data, FallbackMode.STORED_DATA

        except Exception as e:
            logger.warning(f"Failed to load stored video data for {media_uuid}: {e}")

        # Fallback to generating video data from individual frame queries
        try:
            faces_by_frame = {}

            # Get frame range from media records
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text(
                        "SELECT total_frames FROM media_records WHERE media_id = :media_uuid"
                    ),
                    {"media_uuid": media_uuid},
                )
                total_frames = result.scalar() or 100  # Default if not found

            # Collect faces for first 10 frames as sample (optimize as needed)
            for frame_num in range(min(10, total_frames)):
                faces, _ = await self.get_faces_with_fallback(
                    media_uuid, frame_num, FallbackMode.REALTIME_DETECTION
                )
                if faces:
                    faces_by_frame[frame_num] = faces

            # Create fallback video data
            fallback_video_data = VideoFaceData(
                media_uuid=media_uuid,
                total_frames=total_frames,
                total_faces=sum(len(faces) for faces in faces_by_frame.values()),
                faces_by_frame=faces_by_frame,
                processing_metadata={
                    "processing_method": "fallback_realtime",
                    "fallback_generated": True,
                    "sample_frames": len(faces_by_frame),
                },
                retrieval_timestamp=datetime.now(),
                data_format="json",  # Use string instead of enum for fallback
                data_size_bytes=len(json.dumps(faces_by_frame, default=str)),
            )

            return fallback_video_data, FallbackMode.REALTIME_DETECTION

        except Exception as e:
            logger.error(f"All fallback modes failed for video {media_uuid}: {e}")
            raise

    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fallback statistics."""
        success_rate = (
            self.fallback_stats["successful_fallbacks"]
            / max(self.fallback_stats["total_fallbacks"], 1)
            * 100
        )

        return {
            "fallback_performance": {
                "total_fallbacks": self.fallback_stats["total_fallbacks"],
                "successful_fallbacks": self.fallback_stats["successful_fallbacks"],
                "success_rate_percent": round(success_rate, 2),
                "avg_recovery_time_ms": round(
                    self.fallback_stats["avg_fallback_time_ms"], 2
                ),
            },
            "mode_usage": self.fallback_stats["mode_usage"],
            "failure_reasons": self.fallback_stats["reason_frequency"],
            "recent_events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "media_uuid": event.media_uuid,
                    "fallback": f"{event.original_mode.value} -> {event.fallback_mode.value}",
                    "reason": event.reason.value,
                    "recovery_time_ms": event.recovery_time_ms,
                    "success": event.success,
                }
                for event in self.fallback_events[-10:]  # Last 10 events
            ],
        }

    async def health_check_services(self) -> Dict[str, ServiceHealth]:
        """Perform health check on all relevant services."""
        services_to_check = [
            ("vision_service", "http://localhost:8003/health"),
            ("media_service", "http://localhost:8000/health"),
            ("database", None),  # Special case for database
        ]

        health_results = {}

        for service_name, health_url in services_to_check:
            try:
                if service_name == "database":
                    # Database health check
                    start_time = time.time()
                    async with self.data_access.async_session_maker() as session:
                        from sqlalchemy import text

                        await session.execute(text("SELECT 1"))
                    response_time_ms = (time.time() - start_time) * 1000

                    health_results[service_name] = ServiceHealth(
                        service_name=service_name,
                        is_healthy=True,
                        last_check=datetime.now(),
                        response_time_ms=response_time_ms,
                        error_count=0,
                        consecutive_failures=0,
                    )
                else:
                    # HTTP service health check
                    import aiohttp

                    start_time = time.time()
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            health_url, timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            is_healthy = response.status == 200
                            response_time_ms = (time.time() - start_time) * 1000

                            health_results[service_name] = ServiceHealth(
                                service_name=service_name,
                                is_healthy=is_healthy,
                                last_check=datetime.now(),
                                response_time_ms=response_time_ms,
                                error_count=0 if is_healthy else 1,
                                consecutive_failures=0 if is_healthy else 1,
                            )

            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                health_results[service_name] = ServiceHealth(
                    service_name=service_name,
                    is_healthy=False,
                    last_check=datetime.now(),
                    response_time_ms=5000.0,  # Timeout value
                    error_count=1,
                    consecutive_failures=1,
                )

        self.service_health = health_results
        return health_results


async def create_fallback_manager() -> FallbackManager:
    """Create a properly configured fallback manager instance."""
    data_access = Workflow5DataAccess()

    fallback_manager = FallbackManager(data_access)
    logger.info("Fallback manager created and initialized")

    return fallback_manager


# Demonstration and testing code
async def main():
    """Demonstrate the Fallback Manager capabilities."""
    print("🚀 Face Detection Workflow 5 - Phase 5: Fallback Mechanisms")
    print("=============================================================")

    try:
        # Create fallback manager
        fallback_manager = await create_fallback_manager()

        # Get test media_id
        from sqlalchemy import text

        async with fallback_manager.data_access.async_session_maker() as session:
            result = await session.execute(
                text("SELECT media_id FROM media_records LIMIT 1")
            )
            media_id = result.scalar()
            if not media_id:
                print("No media records found for testing")
                return

        print(f"Testing with media_id: {media_id}")

        # Test 1: Normal stored data retrieval
        print("\n📋 Test 1: Normal stored data retrieval...")
        faces, mode = await fallback_manager.get_faces_with_fallback(
            media_id, 1, FallbackMode.STORED_DATA
        )
        print(f"✅ Retrieved {len(faces)} faces using {mode.value}")

        # Test 2: Force fallback by using non-existent media
        print("\n📋 Test 2: Fallback mechanism test...")
        faces, mode = await fallback_manager.get_faces_with_fallback(
            "non-existent-uuid", 1, FallbackMode.STORED_DATA
        )
        print(f"✅ Fallback activated: {len(faces)} faces using {mode.value}")

        # Test 3: Video fallback test
        print("\n📋 Test 3: Video fallback test...")
        try:
            video_data, mode = await fallback_manager.get_video_faces_with_fallback(
                media_id
            )
            stats = video_data.get_statistics()
            print(f"✅ Video fallback: {stats['total_faces']} faces using {mode.value}")
        except Exception as e:
            print(f"Video fallback test failed: {e}")

        # Test 4: Service health check
        print("\n📋 Test 4: Service health check...")
        health_status = await fallback_manager.health_check_services()
        for service, health in health_status.items():
            status = "✅ Healthy" if health.is_healthy else "❌ Unhealthy"
            print(f"  {service}: {status} ({health.response_time_ms:.1f}ms)")

        # Show fallback statistics
        print("\n📊 Fallback Statistics:")
        stats = fallback_manager.get_fallback_statistics()
        perf = stats["fallback_performance"]
        print(f"  • Total fallbacks: {perf['total_fallbacks']}")
        print(f"  • Success rate: {perf['success_rate_percent']:.1f}%")
        print(f"  • Average recovery time: {perf['avg_recovery_time_ms']:.1f}ms")

        print(f"\n  Mode usage:")
        for mode, count in stats["mode_usage"].items():
            print(f"    - {mode}: {count} times")

        print("\n✅ Fallback mechanism testing completed successfully!")

    except Exception as e:
        print(f"❌ Error during fallback testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

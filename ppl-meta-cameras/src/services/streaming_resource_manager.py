"""
PPL Meta Cameras Service - Streaming Resource Manager
Manages concurrent streaming resources to prevent performance degradation

This module provides resource management for multi-camera concurrent streaming:
- Limits concurrent stream count to prevent system overload
- Automatically adjusts quality based on active stream count
- Implements face detection throttling for performance
- Provides stream priority management
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from src.models.camera import CameraType

logger = logging.getLogger(__name__)


class StreamingResourceManager:
    """Manages resources for concurrent camera streaming to prevent performance issues."""

    def __init__(self, max_concurrent_streams: int = 3, performance_threshold: int = 2):
        """
        Initialize resource manager.

        Args:
            max_concurrent_streams: Maximum number of concurrent streams allowed
            performance_threshold: Stream count at which quality degradation begins
        """
        self.max_concurrent_streams = max_concurrent_streams
        self.performance_threshold = performance_threshold
        self.active_streams: Dict[str, Dict] = {}
        self.stream_lock = asyncio.Lock()

    async def can_start_stream(self, device_id: str) -> bool:
        """
        Check if a new stream can be started without overloading the system.

        Args:
            device_id: Camera device identifier

        Returns:
            True if stream can be started, False if system is at capacity
        """
        async with self.stream_lock:
            current_count = len(self.active_streams)
            if current_count >= self.max_concurrent_streams:
                logger.warning(
                    f"🚫 Cannot start stream for {device_id}: "
                    f"maximum concurrent streams ({self.max_concurrent_streams}) reached"
                )
                return False

            logger.info(
                f"✅ Stream start approved for {device_id} "
                f"({current_count + 1}/{self.max_concurrent_streams} streams)"
            )
            return True

    async def register_stream(
        self, device_id: str, camera_type: CameraType, quality: str
    ):
        """
        Register a new active stream.

        Args:
            device_id: Camera device identifier
            camera_type: Type of camera (USB, RTSP, etc.)
            quality: Requested quality level
        """
        async with self.stream_lock:
            stream_count = len(self.active_streams)
            performance_mode = stream_count >= self.performance_threshold

            # Auto-adjust quality for concurrent streams
            optimized_quality = self._get_optimized_quality(quality, stream_count + 1)

            self.active_streams[device_id] = {
                "camera_type": camera_type,
                "requested_quality": quality,
                "optimized_quality": optimized_quality,
                "started_at": datetime.now(),
                "performance_mode": performance_mode,
                "priority": self._get_stream_priority(camera_type),
            }

            logger.info(
                f"📹 Stream registered: {device_id} ({camera_type.value}) "
                f"quality: {quality} → {optimized_quality} "
                f"({len(self.active_streams)} active streams)"
            )

    async def unregister_stream(self, device_id: str):
        """
        Unregister an active stream.

        Args:
            device_id: Camera device identifier
        """
        async with self.stream_lock:
            if device_id in self.active_streams:
                stream_info = self.active_streams.pop(device_id)
                duration = datetime.now() - stream_info["started_at"]

                logger.info(
                    f"🛑 Stream unregistered: {device_id} "
                    f"(duration: {duration.total_seconds():.1f}s, "
                    f"{len(self.active_streams)} streams remaining)"
                )

    def get_stream_count(self) -> int:
        """Get current number of active streams."""
        return len(self.active_streams)

    def is_in_performance_mode(self) -> bool:
        """Check if system is in performance mode (reduced quality)."""
        return len(self.active_streams) >= self.performance_threshold

    def get_optimized_quality_for_device(self, device_id: str) -> Optional[str]:
        """
        Get the optimized quality for a specific device.

        Args:
            device_id: Camera device identifier

        Returns:
            Optimized quality level or None if device not found
        """
        stream_info = self.active_streams.get(device_id)
        return stream_info["optimized_quality"] if stream_info else None

    def _get_optimized_quality(self, requested_quality: str, stream_count: int) -> str:
        """
        Automatically adjust quality based on concurrent stream count.

        Args:
            requested_quality: Originally requested quality
            stream_count: Number of concurrent streams

        Returns:
            Optimized quality level
        """
        # Quality degradation matrix
        quality_map = {
            1: requested_quality,  # Single stream: full quality
            2: "medium" if requested_quality == "high" else requested_quality,
            3: "low",  # Triple+ streams: force low quality
        }

        optimized = quality_map.get(stream_count, "low")

        if optimized != requested_quality:
            logger.info(
                f"🎯 Quality auto-adjustment: {requested_quality} → {optimized} "
                f"(concurrent streams: {stream_count})"
            )

        return optimized

    def _get_stream_priority(self, camera_type: CameraType) -> int:
        """
        Get priority level for camera type.

        Args:
            camera_type: Type of camera

        Returns:
            Priority level (1 = highest, 3 = lowest)
        """
        priority_levels = {
            CameraType.USB: 1,  # Highest priority
            CameraType.RTSP: 2,  # Medium priority
            CameraType.MOBILE: 3,  # Lowest priority
            CameraType.MJPEG: 2,  # Medium priority
            CameraType.WEBRTC: 2,  # Medium priority
            CameraType.VIRTUAL: 3,  # Lowest priority
        }

        return priority_levels.get(camera_type, 3)

    def should_throttle_detection(self, device_id: str) -> bool:
        """
        Determine if face detection should be throttled for a device.

        Args:
            device_id: Camera device identifier

        Returns:
            True if detection should be throttled
        """
        if device_id not in self.active_streams:
            return False

        stream_info = self.active_streams[device_id]
        stream_count = len(self.active_streams)
        priority = stream_info["priority"]

        # Throttle lower priority streams when system is under load
        return stream_count > 2 and priority > 2

    def get_fps_adjustment(self, device_id: str) -> float:
        """
        Get FPS adjustment factor for a device based on system load.

        Args:
            device_id: Camera device identifier

        Returns:
            FPS adjustment factor (1.0 = no adjustment, <1.0 = reduced FPS)
        """
        stream_count = len(self.active_streams)

        # FPS adjustment based on concurrent stream count
        fps_adjustments = {
            1: 1.0,  # Single stream: full FPS
            2: 0.8,  # Dual stream: 80% FPS
            3: 0.6,  # Triple stream: 60% FPS
        }

        return fps_adjustments.get(stream_count, 0.5)

    def get_detection_frame_skip(self, device_id: str) -> int:
        """
        Get frame skip interval for face detection based on system load.

        Args:
            device_id: Camera device identifier

        Returns:
            Frame skip interval (1 = every frame, 2 = every other frame, etc.)
        """
        stream_count = len(self.active_streams)

        # More aggressive frame skipping with more concurrent streams
        skip_intervals = {
            1: 1,  # Single stream: detect every frame
            2: 2,  # Dual stream: detect every 2nd frame
            3: 3,  # Triple stream: detect every 3rd frame
        }

        return skip_intervals.get(stream_count, 4)


# Global instance
streaming_resource_manager = StreamingResourceManager()

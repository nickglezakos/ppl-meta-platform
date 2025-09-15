"""
PPL Meta Vision Service - Workflow 5 Media Service Integration
Enhanced streaming service with embedded processing status and smart mode selection.

This module integrates the Processing Status API and Smart Mode Selection Logic
directly into the Media Service, providing:
- Embedded processing status checks during streaming
- Intelligent streaming protocol selection
- Real-time mode switching based on processing state
- Optimized data delivery based on cache availability

Performance Goals:
- <10ms processing status integration overhead
- Seamless mode switching during streaming
- Intelligent bandwidth optimization
- Cache-aware streaming decisions
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from workflow5_cache_manager import Workflow5CacheManager
from workflow5_data_access import Workflow5DataAccess, workflow5_data_access
from workflow5_processing_status_api import (
    PlaybackMode,
    ProcessingStatus,
    Workflow5ProcessingStatusAPI,
)
from workflow5_smart_mode_selector import (
    PlaybackModeSelector,
    ProcessingStatusAnalyzer,
    create_smart_mode_selector,
)

logger = logging.getLogger(__name__)


class StreamingProtocol(Enum):
    """Streaming protocol options for media delivery."""

    REALTIME_WEBRTC = "realtime_webrtc"
    CACHED_HLS = "cached_hls"
    HYBRID_ADAPTIVE = "hybrid_adaptive"
    PROGRESSIVE_DOWNLOAD = "progressive_download"


class StreamQuality(Enum):
    """Streaming quality levels."""

    LOW = "low"  # 480p, optimized for speed
    MEDIUM = "medium"  # 720p, balanced
    HIGH = "high"  # 1080p, optimized for quality
    ADAPTIVE = "adaptive"  # Dynamic based on conditions


@dataclass
class StreamingDecision:
    """Streaming decision with rationale."""

    protocol: StreamingProtocol
    quality: StreamQuality
    use_cached_data: bool
    estimated_latency_ms: int
    bandwidth_requirement_mbps: float
    confidence_score: float
    decision_factors: List[str]
    fallback_options: List[StreamingProtocol]


@dataclass
class MediaServiceConfig:
    """Configuration for enhanced media service."""

    enable_smart_mode_selection: bool = True
    enable_processing_status_integration: bool = True
    cache_preference_threshold: float = 0.8
    realtime_latency_threshold_ms: int = 100
    adaptive_quality_enabled: bool = True
    fallback_protocols_enabled: bool = True


class Workflow5MediaService:
    """
    Enhanced Media Service with integrated processing status and smart mode selection.

    Provides intelligent streaming decisions based on:
    - Current video processing state
    - Cache availability and effectiveness
    - User preferences and system performance
    - Network conditions and bandwidth
    """

    def __init__(
        self,
        data_access: Workflow5DataAccess,
        cache_manager: Workflow5CacheManager,
        config: MediaServiceConfig = None,
    ):
        """Initialize enhanced media service."""
        self.data_access = data_access
        self.cache_manager = cache_manager
        self.config = config or MediaServiceConfig()

        # Initialize integrated components
        self.status_api = None
        self.mode_selector = None

        # Streaming state management
        self.active_streams = {}
        self.streaming_stats = {
            "total_streams": 0,
            "cached_streams": 0,
            "realtime_streams": 0,
            "hybrid_streams": 0,
            "avg_decision_time_ms": 0.0,
            "total_bandwidth_saved_mb": 0.0,
        }

        # Performance thresholds
        self.thresholds = {
            "max_decision_time_ms": 10.0,
            "cache_effectiveness_threshold": 0.7,
            "realtime_confidence_threshold": 0.8,
            "quality_degradation_threshold": 0.6,
        }

    async def initialize(self) -> bool:
        """Initialize the enhanced media service with all components."""
        try:
            # Initialize Processing Status API
            self.status_api = Workflow5ProcessingStatusAPI()

            # Initialize Smart Mode Selector
            self.mode_selector = await create_smart_mode_selector(
                self.data_access, self.cache_manager
            )

            logger.info("Enhanced Media Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Media Service: {e}")
            return False

    async def get_streaming_decision(
        self,
        media_uuid: str,
        user_preferences: Dict[str, Any] = None,
        network_conditions: Dict[str, Any] = None,
    ) -> StreamingDecision:
        """
        Get intelligent streaming decision based on processing status and preferences.

        Args:
            media_uuid: UUID of the media to stream
            user_preferences: User preferences for streaming
            network_conditions: Current network conditions

        Returns:
            StreamingDecision with optimal protocol and quality settings
        """
        start_time = time.time()

        try:
            # Get processing status and smart mode recommendation
            processing_status = await self.status_api.get_processing_status(media_uuid)
            optimal_mode, mode_confidence = (
                await self.mode_selector.select_optimal_mode(
                    media_uuid, user_preferences or {}
                )
            )

            # Analyze network conditions
            network_analysis = self._analyze_network_conditions(
                network_conditions or {}
            )

            # Convert processing status to dict for decision making
            status_dict = {
                "status": processing_status.status,
                "face_detection_processed": processing_status.face_detection_processed,
                "cache_available": processing_status.cache_status == "cached",
                "cache_effectiveness": (
                    0.8 if processing_status.cache_status == "cached" else 0.0
                ),
                "session_available": processing_status.session_uuid is not None,
                "total_faces": processing_status.total_faces_detected or 0,
                "processing_quality": processing_status.processing_quality_score or 0.0,
            }

            # Make streaming decision
            decision = await self._make_streaming_decision(
                media_uuid,
                status_dict,
                optimal_mode,
                network_analysis,
                user_preferences,
            )

            # Update statistics
            decision_time_ms = (time.time() - start_time) * 1000
            await self._update_streaming_stats(decision, decision_time_ms)

            logger.info(
                f"Streaming decision for {media_uuid}: {decision.protocol.value} "
                f"(confidence: {decision.confidence_score:.2f}, "
                f"decision_time: {decision_time_ms:.1f}ms)"
            )

            return decision

        except Exception as e:
            logger.error(f"Failed to make streaming decision for {media_uuid}: {e}")
            # Return fallback decision
            return self._get_fallback_decision()

    async def _make_streaming_decision(
        self,
        media_uuid: str,
        processing_status: Dict[str, Any],
        optimal_mode: PlaybackMode,
        network_analysis: Dict[str, Any],
        user_preferences: Dict[str, Any],
    ) -> StreamingDecision:
        """Make the optimal streaming decision based on all factors."""
        decision_factors = []
        confidence_score = 0.8

        # Determine protocol based on optimal mode
        if optimal_mode == PlaybackMode.STORED_DATA:
            if processing_status.get("cache_available", False):
                protocol = StreamingProtocol.CACHED_HLS
                decision_factors.append("cached_data_available")
                confidence_score = 0.9
            else:
                protocol = StreamingProtocol.PROGRESSIVE_DOWNLOAD
                decision_factors.append("stored_data_preferred")
                confidence_score = 0.7

        elif optimal_mode == PlaybackMode.REALTIME_ONLY:
            protocol = StreamingProtocol.REALTIME_WEBRTC
            decision_factors.append("realtime_required")
            confidence_score = 0.85

        elif optimal_mode == PlaybackMode.HYBRID:
            protocol = StreamingProtocol.HYBRID_ADAPTIVE
            decision_factors.append("hybrid_optimal")
            confidence_score = 0.8

        else:
            protocol = StreamingProtocol.REALTIME_WEBRTC
            decision_factors.append("fallback_realtime")
            confidence_score = 0.6

        # Determine quality based on network and preferences
        quality = self._determine_quality(network_analysis, user_preferences)
        decision_factors.append(f"quality_{quality.value}")

        # Check if cached data should be used
        use_cached_data = (
            processing_status.get("cache_available", False)
            and processing_status.get("cache_effectiveness", 0.0)
            >= self.thresholds["cache_effectiveness_threshold"]
        )

        if use_cached_data:
            decision_factors.append("cache_effective")

        # Estimate performance characteristics
        estimated_latency_ms = self._estimate_latency(protocol, use_cached_data)
        bandwidth_requirement = self._estimate_bandwidth(protocol, quality)

        # Determine fallback options
        fallback_options = self._get_fallback_protocols(protocol)

        return StreamingDecision(
            protocol=protocol,
            quality=quality,
            use_cached_data=use_cached_data,
            estimated_latency_ms=estimated_latency_ms,
            bandwidth_requirement_mbps=bandwidth_requirement,
            confidence_score=confidence_score,
            decision_factors=decision_factors,
            fallback_options=fallback_options,
        )

    def _analyze_network_conditions(
        self, network_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze network conditions for streaming optimization."""
        # Default network conditions if not provided
        bandwidth_mbps = network_conditions.get("bandwidth_mbps", 10.0)
        latency_ms = network_conditions.get("latency_ms", 50)
        packet_loss = network_conditions.get("packet_loss_percent", 0.0)
        connection_type = network_conditions.get("connection_type", "wifi")

        # Calculate network quality score
        quality_score = 1.0

        if bandwidth_mbps < 2.0:
            quality_score *= 0.5  # Very low bandwidth
        elif bandwidth_mbps < 5.0:
            quality_score *= 0.7  # Low bandwidth

        if latency_ms > 200:
            quality_score *= 0.6  # High latency
        elif latency_ms > 100:
            quality_score *= 0.8  # Moderate latency

        if packet_loss > 5.0:
            quality_score *= 0.4  # High packet loss
        elif packet_loss > 1.0:
            quality_score *= 0.7  # Moderate packet loss

        return {
            "bandwidth_mbps": bandwidth_mbps,
            "latency_ms": latency_ms,
            "packet_loss_percent": packet_loss,
            "connection_type": connection_type,
            "quality_score": quality_score,
            "is_mobile": connection_type in ["cellular", "mobile"],
            "is_stable": quality_score >= 0.8,
        }

    def _determine_quality(
        self, network_analysis: Dict[str, Any], user_preferences: Dict[str, Any]
    ) -> StreamQuality:
        """Determine optimal streaming quality."""
        bandwidth = network_analysis.get("bandwidth_mbps", 10.0)
        quality_score = network_analysis.get("quality_score", 0.8)
        is_mobile = network_analysis.get("is_mobile", False)

        # User preference override
        if user_preferences.get("force_quality"):
            requested_quality = user_preferences["force_quality"]
            if requested_quality in [q.value for q in StreamQuality]:
                return StreamQuality(requested_quality)

        # Adaptive quality logic
        if self.config.adaptive_quality_enabled:
            if bandwidth >= 8.0 and quality_score >= 0.8 and not is_mobile:
                return StreamQuality.HIGH
            elif bandwidth >= 4.0 and quality_score >= 0.6:
                return StreamQuality.MEDIUM
            elif bandwidth >= 1.0:
                return StreamQuality.LOW
            else:
                return StreamQuality.ADAPTIVE

        # Default quality based on bandwidth
        if bandwidth >= 5.0:
            return StreamQuality.MEDIUM
        else:
            return StreamQuality.LOW

    def _estimate_latency(
        self, protocol: StreamingProtocol, use_cached_data: bool
    ) -> int:
        """Estimate streaming latency based on protocol and data source."""
        base_latency = {
            StreamingProtocol.REALTIME_WEBRTC: 50,
            StreamingProtocol.CACHED_HLS: 200,
            StreamingProtocol.HYBRID_ADAPTIVE: 100,
            StreamingProtocol.PROGRESSIVE_DOWNLOAD: 500,
        }

        latency = base_latency.get(protocol, 100)

        # Cache reduces latency significantly
        if use_cached_data:
            latency = int(latency * 0.6)

        return latency

    def _estimate_bandwidth(
        self, protocol: StreamingProtocol, quality: StreamQuality
    ) -> float:
        """Estimate bandwidth requirements for streaming configuration."""
        quality_multipliers = {
            StreamQuality.LOW: 1.0,
            StreamQuality.MEDIUM: 2.5,
            StreamQuality.HIGH: 6.0,
            StreamQuality.ADAPTIVE: 3.0,  # Average
        }

        protocol_base_bandwidth = {
            StreamingProtocol.REALTIME_WEBRTC: 2.0,
            StreamingProtocol.CACHED_HLS: 1.5,
            StreamingProtocol.HYBRID_ADAPTIVE: 2.2,
            StreamingProtocol.PROGRESSIVE_DOWNLOAD: 1.8,
        }

        base_bandwidth = protocol_base_bandwidth.get(protocol, 2.0)
        quality_multiplier = quality_multipliers.get(quality, 1.0)

        return base_bandwidth * quality_multiplier

    def _get_fallback_protocols(
        self, primary_protocol: StreamingProtocol
    ) -> List[StreamingProtocol]:
        """Get fallback protocols for graceful degradation."""
        if not self.config.fallback_protocols_enabled:
            return []

        fallback_map = {
            StreamingProtocol.CACHED_HLS: [
                StreamingProtocol.PROGRESSIVE_DOWNLOAD,
                StreamingProtocol.REALTIME_WEBRTC,
            ],
            StreamingProtocol.HYBRID_ADAPTIVE: [
                StreamingProtocol.REALTIME_WEBRTC,
                StreamingProtocol.CACHED_HLS,
            ],
            StreamingProtocol.REALTIME_WEBRTC: [
                StreamingProtocol.HYBRID_ADAPTIVE,
                StreamingProtocol.PROGRESSIVE_DOWNLOAD,
            ],
            StreamingProtocol.PROGRESSIVE_DOWNLOAD: [
                StreamingProtocol.CACHED_HLS,
                StreamingProtocol.REALTIME_WEBRTC,
            ],
        }

        return fallback_map.get(primary_protocol, [StreamingProtocol.REALTIME_WEBRTC])

    def _get_fallback_decision(self) -> StreamingDecision:
        """Get safe fallback streaming decision."""
        return StreamingDecision(
            protocol=StreamingProtocol.REALTIME_WEBRTC,
            quality=StreamQuality.LOW,
            use_cached_data=False,
            estimated_latency_ms=100,
            bandwidth_requirement_mbps=2.0,
            confidence_score=0.5,
            decision_factors=["fallback_safe_mode"],
            fallback_options=[],
        )

    async def _update_streaming_stats(
        self, decision: StreamingDecision, decision_time_ms: float
    ) -> None:
        """Update streaming statistics for monitoring."""
        self.streaming_stats["total_streams"] += 1

        # Update protocol-specific counters
        if decision.protocol == StreamingProtocol.CACHED_HLS:
            self.streaming_stats["cached_streams"] += 1
        elif decision.protocol == StreamingProtocol.REALTIME_WEBRTC:
            self.streaming_stats["realtime_streams"] += 1
        elif decision.protocol == StreamingProtocol.HYBRID_ADAPTIVE:
            self.streaming_stats["hybrid_streams"] += 1

        # Update average decision time
        total_streams = self.streaming_stats["total_streams"]
        current_avg = self.streaming_stats["avg_decision_time_ms"]
        self.streaming_stats["avg_decision_time_ms"] = (
            (current_avg * (total_streams - 1)) + decision_time_ms
        ) / total_streams

        # Estimate bandwidth savings from cached data usage
        if decision.use_cached_data:
            # Estimate savings compared to full realtime processing
            estimated_savings_mb = (
                decision.bandwidth_requirement_mbps * 0.3
            )  # 30% savings
            self.streaming_stats["total_bandwidth_saved_mb"] += estimated_savings_mb

    async def get_streaming_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive streaming performance metrics."""
        try:
            # Get Processing Status API metrics
            status_health = await self.status_api.get_health_status()

            # Get cache performance metrics
            cache_metrics = await self.cache_manager.get_cache_performance_metrics()

            # Convert health response to dict
            status_metrics = {
                "status": status_health.status,
                "total_processed_videos": status_health.total_processed_videos,
                "avg_response_time_ms": status_health.average_processing_time_ms,
                "cache_hit_ratio": status_health.cache_hit_ratio,
                "system_health_score": status_health.system_health_score,
            }

            # Combine with streaming-specific metrics
            return {
                "streaming_stats": self.streaming_stats.copy(),
                "processing_integration": {
                    "status_api_health": status_metrics,
                    "avg_status_check_time_ms": status_metrics.get(
                        "avg_response_time_ms", 0
                    ),
                },
                "cache_integration": {
                    "cache_hit_ratio": cache_metrics.cache_hit_ratio,
                    "avg_retrieval_time_ms": cache_metrics.average_retrieval_time_ms,
                    "cache_effectiveness": cache_metrics.cache_effectiveness_score,
                },
                "decision_performance": {
                    "avg_decision_time_ms": self.streaming_stats[
                        "avg_decision_time_ms"
                    ],
                    "total_decisions": self.streaming_stats["total_streams"],
                    "cached_decision_ratio": (
                        self.streaming_stats["cached_streams"]
                        / max(self.streaming_stats["total_streams"], 1)
                    ),
                },
                "bandwidth_optimization": {
                    "total_saved_mb": self.streaming_stats["total_bandwidth_saved_mb"],
                    "avg_savings_per_stream_mb": (
                        self.streaming_stats["total_bandwidth_saved_mb"]
                        / max(self.streaming_stats["total_streams"], 1)
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get streaming performance metrics: {e}")
            return {"error": str(e)}

    async def start_adaptive_stream(
        self,
        media_uuid: str,
        stream_id: str,
        user_preferences: Dict[str, Any] = None,
        network_conditions: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Start an adaptive stream with integrated processing status monitoring.

        This method continuously monitors processing status and adapts
        the stream configuration in real-time.
        """
        try:
            # Get initial streaming decision
            decision = await self.get_streaming_decision(
                media_uuid, user_preferences, network_conditions
            )

            # Initialize stream state
            stream_state = {
                "stream_id": stream_id,
                "media_uuid": media_uuid,
                "current_decision": decision,
                "start_time": datetime.now(),
                "adaptations_count": 0,
                "quality_switches": [],
                "protocol_switches": [],
                "user_preferences": user_preferences or {},
                "performance_metrics": {
                    "avg_latency_ms": decision.estimated_latency_ms,
                    "current_bandwidth_mbps": decision.bandwidth_requirement_mbps,
                    "quality_score": 1.0,
                },
            }

            self.active_streams[stream_id] = stream_state

            logger.info(
                f"Started adaptive stream {stream_id} for {media_uuid} "
                f"with {decision.protocol.value} protocol"
            )

            return {
                "stream_id": stream_id,
                "initial_decision": {
                    "protocol": decision.protocol.value,
                    "quality": decision.quality.value,
                    "use_cached_data": decision.use_cached_data,
                    "estimated_latency_ms": decision.estimated_latency_ms,
                    "confidence_score": decision.confidence_score,
                },
                "adaptive_monitoring_enabled": True,
                "status": "started",
            }

        except Exception as e:
            logger.error(f"Failed to start adaptive stream {stream_id}: {e}")
            return {"error": str(e), "status": "failed"}

    async def stop_stream(self, stream_id: str) -> Dict[str, Any]:
        """Stop an active stream and return performance summary."""
        if stream_id not in self.active_streams:
            return {"error": "Stream not found", "status": "not_found"}

        try:
            stream_state = self.active_streams[stream_id]
            duration_seconds = (
                datetime.now() - stream_state["start_time"]
            ).total_seconds()

            # Compile performance summary
            summary = {
                "stream_id": stream_id,
                "media_uuid": stream_state["media_uuid"],
                "duration_seconds": duration_seconds,
                "adaptations_count": stream_state["adaptations_count"],
                "quality_switches": stream_state["quality_switches"],
                "protocol_switches": stream_state["protocol_switches"],
                "final_performance": stream_state["performance_metrics"],
                "status": "stopped",
            }

            # Remove from active streams
            del self.active_streams[stream_id]

            logger.info(f"Stopped stream {stream_id} after {duration_seconds:.1f}s")
            return summary

        except Exception as e:
            logger.error(f"Failed to stop stream {stream_id}: {e}")
            return {"error": str(e), "status": "failed"}

    async def close(self) -> None:
        """Close the enhanced media service and cleanup resources."""
        try:
            # Stop all active streams
            for stream_id in list(self.active_streams.keys()):
                await self.stop_stream(stream_id)

            # Close integrated components
            if self.cache_manager:
                await self.cache_manager.close()

            logger.info("Enhanced Media Service closed successfully")

        except Exception as e:
            logger.error(f"Failed to close Enhanced Media Service: {e}")


# Factory function for easy instantiation
async def create_workflow5_media_service(
    data_access: Workflow5DataAccess = None,
    cache_manager: Workflow5CacheManager = None,
    config: MediaServiceConfig = None,
) -> Workflow5MediaService:
    """Create and initialize an enhanced media service."""
    data_access = data_access or workflow5_data_access
    cache_manager = cache_manager or Workflow5CacheManager()

    service = Workflow5MediaService(data_access, cache_manager, config)
    await service.initialize()
    return service


# Test and validation
if __name__ == "__main__":

    async def test_media_service_integration():
        print("🧪 Testing Enhanced Media Service Integration...\n")

        # Initialize service
        service = await create_workflow5_media_service()
        print("✅ Enhanced Media Service initialized")

        # Test streaming decision making
        print("\n📺 Test 1: Streaming Decision Making")

        decision = await service.get_streaming_decision(
            "test-media-uuid",
            user_preferences={"prefer_quality": True},
            network_conditions={"bandwidth_mbps": 8.0, "latency_ms": 30},
        )

        print(f"🚀 Protocol: {decision.protocol.value}")
        print(f"🎨 Quality: {decision.quality.value}")
        print(f"💾 Use cached data: {decision.use_cached_data}")
        print(f"⚡ Estimated latency: {decision.estimated_latency_ms}ms")
        print(f"📊 Confidence: {decision.confidence_score:.2f}")

        # Test adaptive streaming
        print("\n📡 Test 2: Adaptive Streaming")

        stream_result = await service.start_adaptive_stream(
            "test-adaptive-uuid",
            "stream-001",
            {"prefer_speed": True},
            {"bandwidth_mbps": 5.0, "connection_type": "wifi"},
        )

        print(f"📡 Stream started: {stream_result['status']}")
        print(f"🔧 Initial protocol: {stream_result['initial_decision']['protocol']}")

        # Stop the stream
        stop_result = await service.stop_stream("stream-001")
        print(f"🛑 Stream stopped: {stop_result['status']}")

        # Test performance metrics
        print("\n📈 Test 3: Performance Metrics")

        metrics = await service.get_streaming_performance_metrics()
        print(f"📊 Total streams: {metrics['streaming_stats']['total_streams']}")
        print(
            f"⚡ Avg decision time: {metrics['streaming_stats']['avg_decision_time_ms']:.1f}ms"
        )

        print("\n✅ Enhanced Media Service integration tests completed!")

        # Cleanup
        await service.close()

    # Run tests
    import asyncio

    asyncio.run(test_media_service_integration())

"""
PPL Meta Vision Service - Workflow 5 Smart Mode Selection
Intelligent decision engine for optimal face detection performance.

This module implements the smart mode selection logic that automatically chooses
between stored face data (Workflow 5) and real-time ML processing (Workflow 4)
based on processing status, quality scores, performance metrics, and system load.

Performance Goals:
- 90% CPU reduction through intelligent caching
- <10ms decision latency
- 95%+ optimal mode selection accuracy
- Automatic fallback and recovery
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from workflow5_data_access import workflow5_data_access

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Face detection processing modes."""

    WORKFLOW_4_REALTIME = "workflow4_realtime"  # Real-time ML processing
    WORKFLOW_5_CACHED = "workflow5_cached"  # Pre-computed face data
    HYBRID_SMART = "hybrid_smart"  # Dynamic mode switching
    FALLBACK_SAFE = "fallback_safe"  # Safe fallback mode


@dataclass
class ModeSelectionMetrics:
    """Metrics for mode selection decision analysis."""

    decision_latency_ms: float
    selected_mode: ProcessingMode
    confidence_score: float
    cpu_savings_estimate: float
    cache_hit_probability: float
    quality_score: float
    fallback_reason: Optional[str] = None
    performance_projection: Optional[Dict[str, float]] = None


@dataclass
class SystemPerformanceProfile:
    """Current system performance profile for decision making."""

    cpu_usage_percent: float
    memory_usage_percent: float
    active_sessions: int
    average_query_latency_ms: float
    cache_hit_ratio: float
    error_rate: float


class Workflow5SmartModeSelector:
    """
    Intelligent mode selection engine for Workflow 5 optimization.

    Makes real-time decisions about whether to use pre-computed face data
    or fall back to real-time ML processing based on multiple factors:
    - Processing status and data availability
    - Quality scores and confidence metrics
    - System performance and load
    - Historical performance patterns
    """

    def __init__(self):
        """Initialize smart mode selection engine."""
        self.selection_stats = {
            "total_decisions": 0,
            "workflow5_selected": 0,
            "workflow4_fallback": 0,
            "hybrid_selected": 0,
            "avg_decision_time_ms": 0.0,
            "cpu_savings_total": 0.0,
            "cache_effectiveness": 0.0,
        }

        # Performance thresholds for decision making
        self.thresholds = {
            "quality_score_min": 0.7,  # Minimum quality for Workflow 5
            "confidence_threshold": 0.8,  # Decision confidence required
            "cache_hit_ratio_min": 0.85,  # Minimum cache performance
            "cpu_usage_max": 80.0,  # Max CPU before optimization
            "latency_target_ms": 10.0,  # Target response latency
            "error_rate_max": 0.02,  # Maximum acceptable error rate
        }

        # Decision history for learning and optimization
        self.decision_history = []
        self.max_history_size = 1000

    async def select_optimal_mode(
        self,
        media_uuid: str,
        frame_range: Tuple[int, int],
        confidence_threshold: float = 0.7,
        system_profile: Optional[SystemPerformanceProfile] = None,
    ) -> ModeSelectionMetrics:
        """
        Select the optimal processing mode for face detection.

        Args:
            media_uuid: Media file identifier
            frame_range: (start_frame, end_frame) for processing
            confidence_threshold: Minimum face detection confidence
            system_profile: Current system performance metrics

        Returns:
            ModeSelectionMetrics with decision details and projections
        """
        decision_start = time.perf_counter()

        try:
            # Step 1: Check processing status and data availability
            processing_status = await workflow5_data_access.check_processing_status(
                media_uuid
            )

            # Step 2: Evaluate system performance if not provided
            if system_profile is None:
                system_profile = await self._get_system_performance_profile()

            # Step 3: Make intelligent mode selection
            mode_decision = await self._analyze_and_select_mode(
                media_uuid,
                frame_range,
                confidence_threshold,
                processing_status,
                system_profile,
            )

            # Step 4: Calculate performance projections
            performance_projection = self._calculate_performance_projection(
                mode_decision, processing_status, system_profile
            )

            decision_latency = (time.perf_counter() - decision_start) * 1000

            # Step 5: Create metrics result
            metrics = ModeSelectionMetrics(
                decision_latency_ms=decision_latency,
                selected_mode=mode_decision["mode"],
                confidence_score=mode_decision["confidence"],
                cpu_savings_estimate=performance_projection["cpu_savings_percent"],
                cache_hit_probability=mode_decision["cache_probability"],
                quality_score=processing_status.get("quality_score", 0.0),
                fallback_reason=mode_decision.get("fallback_reason"),
                performance_projection=performance_projection,
            )

            # Step 6: Update statistics and learning
            await self._update_selection_stats(metrics)
            self._add_to_decision_history(metrics, processing_status, system_profile)

            logger.info(
                f"Mode selection for {media_uuid}: {mode_decision['mode'].value} "
                f"(confidence: {mode_decision['confidence']:.2f}, "
                f"decision_time: {decision_latency:.2f}ms)"
            )

            return metrics

        except Exception as e:
            decision_latency = (time.perf_counter() - decision_start) * 1000
            logger.error(f"Mode selection failed in {decision_latency:.2f}ms: {e}")

            # Return safe fallback mode
            return ModeSelectionMetrics(
                decision_latency_ms=decision_latency,
                selected_mode=ProcessingMode.FALLBACK_SAFE,
                confidence_score=0.0,
                cpu_savings_estimate=0.0,
                cache_hit_probability=0.0,
                quality_score=0.0,
                fallback_reason=f"Selection error: {str(e)}",
            )

    async def _analyze_and_select_mode(
        self,
        media_uuid: str,
        frame_range: Tuple[int, int],
        confidence_threshold: float,
        processing_status: Dict[str, Any],
        system_profile: SystemPerformanceProfile,
    ) -> Dict[str, Any]:
        """
        Core intelligence for mode selection analysis.

        Returns:
            Dictionary with mode, confidence, cache_probability, and reasoning
        """
        start_frame, end_frame = frame_range

        # Analysis factors
        factors = {
            "has_processed_data": processing_status.get("is_processed", False),
            "workflow5_eligible": processing_status.get("workflow5_eligible", False),
            "quality_score": processing_status.get("quality_score", 0.0),
            "cache_status": processing_status.get("cache_status", "not_cached"),
            "system_cpu_usage": system_profile.cpu_usage_percent,
            "system_cache_ratio": system_profile.cache_hit_ratio,
            "frame_count": end_frame - start_frame + 1,
            "confidence_requirement": confidence_threshold,
        }

        # Decision matrix analysis
        workflow5_score = 0.0
        workflow4_score = 0.0

        # Factor 1: Data Availability and Quality (40% weight)
        if factors["has_processed_data"] and factors["workflow5_eligible"]:
            workflow5_score += 0.4 * min(factors["quality_score"], 1.0)
        else:
            workflow4_score += 0.4  # Must use real-time if no data

        # Factor 2: System Performance Load (30% weight)
        cpu_stress = factors["system_cpu_usage"] / 100.0
        if cpu_stress > 0.7:  # High CPU usage favors caching
            workflow5_score += 0.3 * (cpu_stress - 0.3)
        else:  # Low CPU usage allows real-time processing
            workflow4_score += 0.3 * (1.0 - cpu_stress)

        # Factor 3: Cache Performance (20% weight)
        cache_effectiveness = factors["system_cache_ratio"]
        workflow5_score += 0.2 * cache_effectiveness

        # Factor 4: Request Characteristics (10% weight)
        frame_complexity = min(factors["frame_count"] / 100.0, 1.0)  # Normalize
        if frame_complexity > 0.5:  # Large frame ranges benefit from caching
            workflow5_score += 0.1 * frame_complexity
        else:  # Small ranges can use real-time
            workflow4_score += 0.1 * (1.0 - frame_complexity)

        # Determine mode selection
        if workflow5_score > workflow4_score and workflow5_score > 0.6:
            selected_mode = ProcessingMode.WORKFLOW_5_CACHED
            confidence = workflow5_score
            cache_probability = 0.9 if factors["cache_status"] == "cached" else 0.6
        elif abs(workflow5_score - workflow4_score) < 0.1:
            # Scores are close - use hybrid mode
            selected_mode = ProcessingMode.HYBRID_SMART
            confidence = 0.7
            cache_probability = 0.5
        else:
            selected_mode = ProcessingMode.WORKFLOW_4_REALTIME
            confidence = workflow4_score
            cache_probability = 0.1

        # Apply safety checks
        if factors["quality_score"] < self.thresholds["quality_score_min"]:
            selected_mode = ProcessingMode.WORKFLOW_4_REALTIME
            confidence *= 0.8
            fallback_reason = "Quality score below threshold"
        elif not factors["workflow5_eligible"]:
            selected_mode = ProcessingMode.WORKFLOW_4_REALTIME
            confidence *= 0.9
            fallback_reason = "Not eligible for Workflow 5"
        else:
            fallback_reason = None

        return {
            "mode": selected_mode,
            "confidence": confidence,
            "cache_probability": cache_probability,
            "factors": factors,
            "scores": {"workflow5": workflow5_score, "workflow4": workflow4_score},
            "fallback_reason": fallback_reason,
        }

    def _calculate_performance_projection(
        self,
        mode_decision: Dict[str, Any],
        processing_status: Dict[str, Any],
        system_profile: SystemPerformanceProfile,
    ) -> Dict[str, float]:
        """Calculate projected performance improvements."""

        base_cpu_usage = 100.0  # Assume 100% CPU for real-time processing
        base_latency_ms = 150.0  # Typical real-time processing latency

        if mode_decision["mode"] == ProcessingMode.WORKFLOW_5_CACHED:
            # Cached data performance projections
            cpu_savings = 90.0  # 90% CPU reduction
            latency_improvement = 93.0  # ~10ms vs ~150ms
            throughput_multiplier = 15.0  # 15x more requests possible

        elif mode_decision["mode"] == ProcessingMode.HYBRID_SMART:
            # Hybrid mode averages
            cpu_savings = 45.0  # 45% average savings
            latency_improvement = 50.0  # 50% average improvement
            throughput_multiplier = 3.0  # 3x throughput

        else:  # WORKFLOW_4_REALTIME or FALLBACK_SAFE
            cpu_savings = 0.0
            latency_improvement = 0.0
            throughput_multiplier = 1.0

        return {
            "cpu_savings_percent": cpu_savings,
            "latency_improvement_percent": latency_improvement,
            "throughput_multiplier": throughput_multiplier,
            "projected_latency_ms": base_latency_ms * (1 - latency_improvement / 100),
            "projected_cpu_usage": base_cpu_usage * (1 - cpu_savings / 100),
            "efficiency_score": (cpu_savings + latency_improvement) / 2.0,
        }

    async def _get_system_performance_profile(self) -> SystemPerformanceProfile:
        """Get current system performance metrics."""
        try:
            # Get performance stats from data access layer
            stats = workflow5_data_access.get_performance_stats()

            # Mock additional system metrics (in production, get from system monitors)
            import psutil

            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()

            return SystemPerformanceProfile(
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_info.percent,
                active_sessions=1,  # TODO: Get from session manager
                average_query_latency_ms=stats["avg_latency_ms"],
                cache_hit_ratio=stats["cache_hit_ratio"],
                error_rate=0.01,  # TODO: Get from error tracking
            )

        except Exception as e:
            logger.warning(f"Failed to get system profile, using defaults: {e}")
            # Return safe default profile
            return SystemPerformanceProfile(
                cpu_usage_percent=50.0,
                memory_usage_percent=60.0,
                active_sessions=1,
                average_query_latency_ms=25.0,
                cache_hit_ratio=0.7,
                error_rate=0.02,
            )

    async def _update_selection_stats(self, metrics: ModeSelectionMetrics) -> None:
        """Update selection statistics for monitoring and optimization."""
        self.selection_stats["total_decisions"] += 1

        if metrics.selected_mode == ProcessingMode.WORKFLOW_5_CACHED:
            self.selection_stats["workflow5_selected"] += 1
        elif metrics.selected_mode == ProcessingMode.WORKFLOW_4_REALTIME:
            self.selection_stats["workflow4_fallback"] += 1
        elif metrics.selected_mode == ProcessingMode.HYBRID_SMART:
            self.selection_stats["hybrid_selected"] += 1

        # Update rolling averages
        total = self.selection_stats["total_decisions"]

        # Decision time average
        current_avg = self.selection_stats["avg_decision_time_ms"]
        self.selection_stats["avg_decision_time_ms"] = (
            current_avg * (total - 1) + metrics.decision_latency_ms
        ) / total

        # CPU savings accumulation
        self.selection_stats["cpu_savings_total"] += metrics.cpu_savings_estimate

    def _add_to_decision_history(
        self,
        metrics: ModeSelectionMetrics,
        processing_status: Dict[str, Any],
        system_profile: SystemPerformanceProfile,
    ) -> None:
        """Add decision to history for learning and analysis."""
        decision_record = {
            "timestamp": time.time(),
            "metrics": metrics,
            "processing_status": processing_status,
            "system_profile": system_profile,
        }

        self.decision_history.append(decision_record)

        # Trim history if it gets too large
        if len(self.decision_history) > self.max_history_size:
            self.decision_history = self.decision_history[-self.max_history_size :]

    def get_selection_statistics(self) -> Dict[str, Any]:
        """Get comprehensive selection statistics and performance metrics."""
        total = self.selection_stats["total_decisions"]
        if total == 0:
            return {"message": "No decisions made yet"}

        workflow5_ratio = self.selection_stats["workflow5_selected"] / total
        cpu_savings_avg = self.selection_stats["cpu_savings_total"] / total

        return {
            "total_decisions": total,
            "mode_distribution": {
                "workflow5_cached": self.selection_stats["workflow5_selected"],
                "workflow4_realtime": self.selection_stats["workflow4_fallback"],
                "hybrid_smart": self.selection_stats["hybrid_selected"],
            },
            "performance_metrics": {
                "workflow5_selection_ratio": workflow5_ratio,
                "average_decision_time_ms": self.selection_stats[
                    "avg_decision_time_ms"
                ],
                "average_cpu_savings_percent": cpu_savings_avg,
                "optimization_effectiveness": workflow5_ratio * cpu_savings_avg / 100,
            },
            "decision_quality": {
                "target_decision_time": "< 1ms",
                "target_workflow5_ratio": "> 0.7",
                "target_cpu_savings": "> 80%",
                "current_performance": (
                    "excellent"
                    if workflow5_ratio > 0.8 and cpu_savings_avg > 80
                    else (
                        "good"
                        if workflow5_ratio > 0.6 and cpu_savings_avg > 60
                        else "needs_optimization"
                    )
                ),
            },
        }

    async def optimize_thresholds(self) -> None:
        """Optimize decision thresholds based on historical performance."""
        if len(self.decision_history) < 100:
            logger.info("Insufficient history for threshold optimization")
            return

        # Analyze decision outcomes and adjust thresholds
        # This is a simplified optimization - in production, use ML techniques

        successful_decisions = [
            record
            for record in self.decision_history
            if record["metrics"].confidence_score > 0.8
        ]

        if len(successful_decisions) > 50:
            # Calculate optimal thresholds based on successful decisions
            quality_scores = [
                record["processing_status"].get("quality_score", 0)
                for record in successful_decisions
            ]

            if quality_scores:
                # Adjust quality threshold to 10th percentile of successful decisions
                self.thresholds["quality_score_min"] = max(
                    0.5, sorted(quality_scores)[len(quality_scores) // 10]
                )

            logger.info(
                f"Optimized thresholds based on {len(successful_decisions)} successful decisions"
            )


# Singleton instance for easy import
workflow5_mode_selector = Workflow5SmartModeSelector()

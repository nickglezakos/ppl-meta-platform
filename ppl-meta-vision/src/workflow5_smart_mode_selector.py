#!/usr/bin/env python3
"""
Workflow 5 Smart Mode Selection Logic
====================================

Intelligent algorithms for automatically detecting processed vs unprocessed videos
and choosing optimal playback modes based on:

- Video processing state analysis
- Face data availability assessment
- Session validity verification
- Performance metrics evaluation
- System load and resource optimization

Core Components:
- ProcessingStatusAnalyzer: Main analysis engine
- PlaybackModeSelector: Decision algorithm implementation
- PerformanceOptimizer: System load and resource analysis
- CacheEfficiencyAnalyzer: Cache hit ratio and effectiveness
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from workflow5_cache_manager import Workflow5CacheManager
from workflow5_data_access import Workflow5DataAccess
from workflow5_processing_status_api import PlaybackMode, ProcessingStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisResult(Enum):
    """Analysis result classifications."""

    HIGHLY_PROCESSED = "highly_processed"
    PARTIALLY_PROCESSED = "partially_processed"
    NOT_PROCESSED = "not_processed"
    CACHE_AVAILABLE = "cache_available"
    SESSION_VALID = "session_valid"
    PERFORMANCE_OPTIMAL = "performance_optimal"


class SystemLoadLevel(Enum):
    """System load level classifications."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingStatusAnalyzer:
    """
    Advanced analyzer for video processing state and data availability.

    Provides comprehensive analysis of video processing status, face data
    completeness, session validity, and performance characteristics to
    enable intelligent playback mode selection.
    """

    def __init__(
        self, data_access: Workflow5DataAccess, cache_manager: Workflow5CacheManager
    ):
        self.data_access = data_access
        self.cache_manager = cache_manager

        # Analysis thresholds and parameters
        self.quality_thresholds = {
            "min_face_detection_ratio": 0.7,  # 70% frames with faces
            "min_confidence_score": 0.8,  # 80% confidence
            "min_processing_quality": 0.85,  # 85% processing quality
            "max_frame_gaps": 10,  # Max consecutive missing frames
        }

        self.performance_thresholds = {
            "max_cache_miss_ratio": 0.2,  # 20% cache miss tolerance
            "max_retrieval_latency_ms": 50,  # 50ms max retrieval time
            "min_system_health_score": 0.7,  # 70% system health
            "max_concurrent_sessions": 25,  # Max active sessions
        }

        # Internal analysis cache
        self._analysis_cache = {}
        self._cache_ttl_seconds = 300  # 5 minutes

        # Performance statistics
        self.analysis_stats = {
            "total_analyses": 0,
            "cache_hits": 0,
            "avg_analysis_time_ms": 0.0,
            "decision_accuracy": 0.95,
        }

    async def analyze_video_processing_state(
        self, media_uuid: str, include_detailed_metrics: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of video processing state.

        Returns:
            Dict containing processing analysis with:
            - processing_completeness: 0.0-1.0 scale
            - face_data_quality: Quality metrics
            - session_validity: Session state analysis
            - cache_effectiveness: Cache performance
            - recommended_mode: Suggested playback mode
            - confidence_score: Decision confidence (0.0-1.0)
        """
        start_time = time.perf_counter()

        try:
            # Check analysis cache first
            cache_key = f"analysis_{media_uuid}_{include_detailed_metrics}"
            if cache_key in self._analysis_cache:
                cache_entry = self._analysis_cache[cache_key]
                if datetime.now() - cache_entry["timestamp"] < timedelta(
                    seconds=self._cache_ttl_seconds
                ):
                    self.analysis_stats["cache_hits"] += 1
                    return cache_entry["result"]

            # Perform comprehensive analysis
            analysis_result = {
                "media_uuid": media_uuid,
                "analysis_timestamp": datetime.now().isoformat(),
                "processing_completeness": 0.0,
                "face_data_quality": {},
                "session_validity": {},
                "cache_effectiveness": {},
                "system_performance": {},
                "recommended_mode": PlaybackMode.REALTIME_ONLY,
                "confidence_score": 0.0,
                "analysis_details": {} if include_detailed_metrics else None,
            }

            # Step 1: Analyze processing completeness
            processing_analysis = await self._analyze_processing_completeness(
                media_uuid
            )
            analysis_result["processing_completeness"] = processing_analysis[
                "completeness_score"
            ]

            # Step 2: Analyze face data quality
            face_data_analysis = await self._analyze_face_data_quality(media_uuid)
            analysis_result["face_data_quality"] = face_data_analysis

            # Step 3: Analyze session validity
            session_analysis = await self._analyze_session_validity(media_uuid)
            analysis_result["session_validity"] = session_analysis

            # Step 4: Analyze cache effectiveness
            cache_analysis = await self._analyze_cache_effectiveness(media_uuid)
            analysis_result["cache_effectiveness"] = cache_analysis

            # Step 5: Analyze system performance
            system_analysis = await self._analyze_system_performance()
            analysis_result["system_performance"] = system_analysis

            # Step 6: Calculate recommendation and confidence
            recommendation = await self._calculate_optimal_mode_recommendation(
                processing_analysis,
                face_data_analysis,
                session_analysis,
                cache_analysis,
                system_analysis,
            )

            analysis_result["recommended_mode"] = recommendation["mode"]
            analysis_result["confidence_score"] = recommendation["confidence"]

            if include_detailed_metrics:
                analysis_result["analysis_details"] = {
                    "processing_analysis": processing_analysis,
                    "decision_factors": recommendation["factors"],
                    "performance_metrics": await self._get_detailed_performance_metrics(
                        media_uuid
                    ),
                }

            # Cache the result
            self._analysis_cache[cache_key] = {
                "result": analysis_result,
                "timestamp": datetime.now(),
            }

            # Update statistics
            analysis_time = (time.perf_counter() - start_time) * 1000
            self.analysis_stats["total_analyses"] += 1
            self.analysis_stats["avg_analysis_time_ms"] = (
                self.analysis_stats["avg_analysis_time_ms"]
                * (self.analysis_stats["total_analyses"] - 1)
                + analysis_time
            ) / self.analysis_stats["total_analyses"]

            logger.info(f"Completed analysis for {media_uuid} in {analysis_time:.2f}ms")
            return analysis_result

        except Exception as e:
            logger.error(
                f"Failed to analyze video processing state for {media_uuid}: {e}"
            )
            # Return safe default
            return {
                "media_uuid": media_uuid,
                "analysis_timestamp": datetime.now().isoformat(),
                "processing_completeness": 0.0,
                "recommended_mode": PlaybackMode.REALTIME_ONLY,
                "confidence_score": 0.0,
                "error": str(e),
            }

    async def _analyze_processing_completeness(self, media_uuid: str) -> Dict[str, Any]:
        """Analyze how complete the processing is for a video."""
        try:
            # Get processing status from data access layer
            processing_status = await self.data_access.check_processing_status(
                media_uuid
            )

            completeness_score = 0.0
            factors = []

            # Check if face detection was completed
            if processing_status.get("face_detection_processed", False):
                completeness_score += 0.4
                factors.append("face_detection_completed")

            # Check processing quality score
            quality_score = processing_status.get("processing_quality_score", 0.0)
            if quality_score >= self.quality_thresholds["min_processing_quality"]:
                completeness_score += 0.3
                factors.append("high_quality_processing")
            elif quality_score >= 0.7:
                completeness_score += 0.2
                factors.append("medium_quality_processing")

            # Check face data availability
            total_faces = processing_status.get("total_faces_detected", 0)
            total_frames = processing_status.get("total_frames_processed", 1)
            face_frame_ratio = (
                total_faces / max(total_frames, 1) if total_frames > 0 else 0
            )

            if face_frame_ratio >= self.quality_thresholds["min_face_detection_ratio"]:
                completeness_score += 0.2
                factors.append("sufficient_face_data")
            elif face_frame_ratio >= 0.4:
                completeness_score += 0.1
                factors.append("partial_face_data")

            # Check processing method reliability
            processing_method = processing_status.get("processing_method", "")
            if "workflow5" in processing_method.lower():
                completeness_score += 0.1
                factors.append("workflow5_processing")

            return {
                "completeness_score": min(completeness_score, 1.0),
                "quality_score": quality_score,
                "face_frame_ratio": face_frame_ratio,
                "total_faces_detected": total_faces,
                "total_frames_processed": total_frames,
                "contributing_factors": factors,
                "processing_method": processing_method,
            }

        except Exception as e:
            logger.error(f"Failed to analyze processing completeness: {e}")
            return {"completeness_score": 0.0, "error": str(e)}

    async def _analyze_face_data_quality(self, media_uuid: str) -> Dict[str, Any]:
        """Analyze quality and completeness of face data."""
        try:
            # Get sample of face data for analysis
            face_data = await self.data_access.get_face_data_by_frame_range(
                media_uuid, 0, 100, confidence_threshold=0.5
            )

            if not face_data:
                return {
                    "quality_score": 0.0,
                    "data_available": False,
                    "analysis": "no_face_data",
                }

            # Analyze confidence scores
            confidence_scores = [
                detection.get("confidence_score", 0.0) for detection in face_data
            ]
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )
            high_confidence_ratio = len(
                [
                    c
                    for c in confidence_scores
                    if c >= self.quality_thresholds["min_confidence_score"]
                ]
            ) / len(confidence_scores)

            # Analyze temporal distribution
            frame_numbers = [
                detection.get("frame_number", 0) for detection in face_data
            ]
            frame_gaps = self._analyze_frame_gaps(frame_numbers)

            # Calculate quality score
            quality_score = 0.0

            # Confidence quality (40% weight)
            if avg_confidence >= self.quality_thresholds["min_confidence_score"]:
                quality_score += 0.4
            elif avg_confidence >= 0.7:
                quality_score += 0.3
            elif avg_confidence >= 0.6:
                quality_score += 0.2

            # High confidence ratio (30% weight)
            if high_confidence_ratio >= 0.8:
                quality_score += 0.3
            elif high_confidence_ratio >= 0.6:
                quality_score += 0.2
            elif high_confidence_ratio >= 0.4:
                quality_score += 0.1

            # Temporal consistency (30% weight)
            if frame_gaps["max_gap"] <= self.quality_thresholds["max_frame_gaps"]:
                quality_score += 0.3
            elif frame_gaps["max_gap"] <= 20:
                quality_score += 0.2
            elif frame_gaps["max_gap"] <= 50:
                quality_score += 0.1

            return {
                "quality_score": min(quality_score, 1.0),
                "data_available": True,
                "total_detections": len(face_data),
                "avg_confidence": avg_confidence,
                "high_confidence_ratio": high_confidence_ratio,
                "frame_distribution": frame_gaps,
                "analysis": "quality_assessment_complete",
            }

        except Exception as e:
            logger.error(f"Failed to analyze face data quality: {e}")
            return {"quality_score": 0.0, "data_available": False, "error": str(e)}

    async def _analyze_session_validity(self, media_uuid: str) -> Dict[str, Any]:
        """Analyze validity and availability of processing sessions."""
        try:
            # Check for active/recent sessions
            processing_status = await self.data_access.check_processing_status(
                media_uuid
            )
            session_uuid = processing_status.get("face_detection_session_uuid")

            if not session_uuid:
                return {"session_valid": False, "analysis": "no_session_found"}

            # Analyze session characteristics
            session_analysis = {
                "session_valid": True,
                "session_uuid": session_uuid,
                "analysis": "session_available",
            }

            # Check session recency (if timestamps available)
            last_accessed = processing_status.get("last_accessed")
            if last_accessed:
                time_since_access = datetime.now() - last_accessed
                if time_since_access.days < 7:
                    session_analysis["recency_score"] = 1.0
                elif time_since_access.days < 30:
                    session_analysis["recency_score"] = 0.7
                else:
                    session_analysis["recency_score"] = 0.3
            else:
                session_analysis["recency_score"] = 0.5

            return session_analysis

        except Exception as e:
            logger.error(f"Failed to analyze session validity: {e}")
            return {"session_valid": False, "error": str(e)}

    async def _analyze_cache_effectiveness(self, media_uuid: str) -> Dict[str, Any]:
        """Analyze cache performance and effectiveness."""
        try:
            # Check if data is cached
            cache_status = await self.cache_manager.check_cache_status(media_uuid)

            effectiveness_score = 0.0
            analysis_factors = []

            if cache_status.get("cached", False):
                effectiveness_score += 0.5
                analysis_factors.append("data_cached")

                # Check cache performance metrics
                hit_ratio = cache_status.get("hit_ratio", 0.0)
                if hit_ratio >= 0.9:
                    effectiveness_score += 0.3
                    analysis_factors.append("high_hit_ratio")
                elif hit_ratio >= 0.7:
                    effectiveness_score += 0.2
                    analysis_factors.append("medium_hit_ratio")

                # Check retrieval performance
                avg_retrieval_time = cache_status.get("avg_retrieval_time_ms", 1000)
                if (
                    avg_retrieval_time
                    <= self.performance_thresholds["max_retrieval_latency_ms"]
                ):
                    effectiveness_score += 0.2
                    analysis_factors.append("fast_retrieval")
            else:
                analysis_factors.append("not_cached")

            return {
                "effectiveness_score": min(effectiveness_score, 1.0),
                "cached": cache_status.get("cached", False),
                "hit_ratio": cache_status.get("hit_ratio", 0.0),
                "avg_retrieval_time_ms": cache_status.get("avg_retrieval_time_ms", 0),
                "contributing_factors": analysis_factors,
            }

        except Exception as e:
            logger.error(f"Failed to analyze cache effectiveness: {e}")
            return {"effectiveness_score": 0.0, "cached": False, "error": str(e)}

    async def _analyze_system_performance(self) -> Dict[str, Any]:
        """Analyze current system performance and load."""
        try:
            # Get system metrics (simplified for this implementation)
            current_time = datetime.now()

            # Simulate system load analysis
            # In production, this would check actual system metrics
            system_load_level = SystemLoadLevel.MEDIUM
            load_score = 0.7

            performance_analysis = {
                "load_level": system_load_level,
                "load_score": load_score,
                "timestamp": current_time.isoformat(),
                "can_handle_realtime": load_score >= 0.6,
                "prefer_cached_data": load_score < 0.8,
            }

            return performance_analysis

        except Exception as e:
            logger.error(f"Failed to analyze system performance: {e}")
            return {
                "load_level": SystemLoadLevel.HIGH,
                "load_score": 0.3,
                "can_handle_realtime": False,
                "prefer_cached_data": True,
                "error": str(e),
            }

    async def _calculate_optimal_mode_recommendation(
        self,
        processing_analysis: Dict[str, Any],
        face_data_analysis: Dict[str, Any],
        session_analysis: Dict[str, Any],
        cache_analysis: Dict[str, Any],
        system_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculate optimal playback mode recommendation with confidence score."""

        # Initialize scoring for each mode
        mode_scores = {
            PlaybackMode.STORED_DATA: 0.0,
            PlaybackMode.REALTIME_WITH_SESSION: 0.0,
            PlaybackMode.REALTIME_ONLY: 0.0,
            PlaybackMode.HYBRID: 0.0,
        }

        decision_factors = []

        # Factor 1: Processing completeness (weight: 0.3)
        completeness = processing_analysis.get("completeness_score", 0.0)
        if completeness >= 0.8:
            mode_scores[PlaybackMode.STORED_DATA] += 0.3
            mode_scores[PlaybackMode.HYBRID] += 0.2
            decision_factors.append("high_processing_completeness")
        elif completeness >= 0.5:
            mode_scores[PlaybackMode.REALTIME_WITH_SESSION] += 0.2
            mode_scores[PlaybackMode.HYBRID] += 0.3
            decision_factors.append("medium_processing_completeness")
        else:
            mode_scores[PlaybackMode.REALTIME_ONLY] += 0.3
            decision_factors.append("low_processing_completeness")

        # Factor 2: Face data quality (weight: 0.25)
        face_quality = face_data_analysis.get("quality_score", 0.0)
        if face_quality >= 0.8:
            mode_scores[PlaybackMode.STORED_DATA] += 0.25
            mode_scores[PlaybackMode.HYBRID] += 0.15
            decision_factors.append("high_face_data_quality")
        elif face_quality >= 0.5:
            mode_scores[PlaybackMode.REALTIME_WITH_SESSION] += 0.15
            mode_scores[PlaybackMode.HYBRID] += 0.25
            decision_factors.append("medium_face_data_quality")

        # Factor 3: Session validity (weight: 0.2)
        if session_analysis.get("session_valid", False):
            mode_scores[PlaybackMode.REALTIME_WITH_SESSION] += 0.2
            mode_scores[PlaybackMode.HYBRID] += 0.1
            decision_factors.append("valid_session_available")
        else:
            mode_scores[PlaybackMode.REALTIME_ONLY] += 0.15
            mode_scores[PlaybackMode.STORED_DATA] += 0.05
            decision_factors.append("no_valid_session")

        # Factor 4: Cache effectiveness (weight: 0.15)
        cache_effectiveness = cache_analysis.get("effectiveness_score", 0.0)
        if cache_effectiveness >= 0.7:
            mode_scores[PlaybackMode.STORED_DATA] += 0.15
            mode_scores[PlaybackMode.HYBRID] += 0.1
            decision_factors.append("effective_cache_available")

        # Factor 5: System performance (weight: 0.1)
        if system_analysis.get("can_handle_realtime", False):
            mode_scores[PlaybackMode.REALTIME_ONLY] += 0.05
            mode_scores[PlaybackMode.REALTIME_WITH_SESSION] += 0.1
        else:
            mode_scores[PlaybackMode.STORED_DATA] += 0.1
            decision_factors.append("system_prefers_cached_data")

        # Select mode with highest score
        recommended_mode = max(mode_scores, key=mode_scores.get)
        confidence_score = mode_scores[recommended_mode]

        # Adjust confidence based on score distribution
        scores = list(mode_scores.values())
        score_variance = max(scores) - min(scores)
        if score_variance < 0.1:
            confidence_score *= 0.7  # Low confidence if scores are close

        return {
            "mode": recommended_mode,
            "confidence": min(confidence_score, 1.0),
            "mode_scores": mode_scores,
            "factors": decision_factors,
        }

    def _analyze_frame_gaps(self, frame_numbers: List[int]) -> Dict[str, Any]:
        """Analyze gaps in frame coverage."""
        if not frame_numbers:
            return {"max_gap": 0, "avg_gap": 0, "total_gaps": 0}

        sorted_frames = sorted(frame_numbers)
        gaps = []

        for i in range(1, len(sorted_frames)):
            gap = sorted_frames[i] - sorted_frames[i - 1] - 1
            if gap > 0:
                gaps.append(gap)

        return {
            "max_gap": max(gaps) if gaps else 0,
            "avg_gap": sum(gaps) / len(gaps) if gaps else 0,
            "total_gaps": len(gaps),
            "frame_coverage": (
                len(sorted_frames) / (max(sorted_frames) - min(sorted_frames) + 1)
                if sorted_frames
                else 0
            ),
        }

    async def _get_detailed_performance_metrics(
        self, media_uuid: str
    ) -> Dict[str, Any]:
        """Get detailed performance metrics for analysis."""
        try:
            return {
                "analysis_cache_hits": self.analysis_stats["cache_hits"],
                "total_analyses": self.analysis_stats["total_analyses"],
                "avg_analysis_time_ms": self.analysis_stats["avg_analysis_time_ms"],
                "decision_accuracy": self.analysis_stats["decision_accuracy"],
                "cache_efficiency": len(self._analysis_cache),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

    async def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get analyzer performance statistics."""
        return {
            "analysis_stats": self.analysis_stats.copy(),
            "cache_size": len(self._analysis_cache),
            "quality_thresholds": self.quality_thresholds.copy(),
            "performance_thresholds": self.performance_thresholds.copy(),
        }

    async def clear_analysis_cache(self) -> None:
        """Clear the analysis cache."""
        self._analysis_cache.clear()
        logger.info("Analysis cache cleared")


class PlaybackModeSelector:
    """
    High-level interface for intelligent playback mode selection.

    Provides a simplified API for getting optimal playback modes
    based on comprehensive video analysis.
    """

    def __init__(self, analyzer: ProcessingStatusAnalyzer):
        self.analyzer = analyzer

    async def select_optimal_mode(
        self, media_uuid: str, user_preferences: Optional[Dict[str, Any]] = None
    ) -> Tuple[PlaybackMode, float]:
        """
        Select optimal playback mode for a video.

        Args:
            media_uuid: Video identifier
            user_preferences: Optional user preferences for mode selection

        Returns:
            Tuple of (PlaybackMode, confidence_score)
        """
        try:
            # Perform comprehensive analysis
            analysis = await self.analyzer.analyze_video_processing_state(
                media_uuid, include_detailed_metrics=False
            )

            recommended_mode = analysis.get(
                "recommended_mode", PlaybackMode.REALTIME_ONLY
            )
            confidence = analysis.get("confidence_score", 0.0)

            # Apply user preferences if provided
            if user_preferences:
                recommended_mode, confidence = self._apply_user_preferences(
                    recommended_mode, confidence, user_preferences
                )

            logger.info(
                f"Selected mode {recommended_mode} for {media_uuid} (confidence: {confidence:.2f})"
            )
            return recommended_mode, confidence

        except Exception as e:
            logger.error(f"Failed to select optimal mode for {media_uuid}: {e}")
            return PlaybackMode.REALTIME_ONLY, 0.0

    def _apply_user_preferences(
        self,
        recommended_mode: PlaybackMode,
        confidence: float,
        preferences: Dict[str, Any],
    ) -> Tuple[PlaybackMode, float]:
        """Apply user preferences to mode selection."""

        # Check for explicit mode preference
        preferred_mode = preferences.get("preferred_mode")
        if preferred_mode and preferred_mode in [mode.value for mode in PlaybackMode]:
            preference_mode = PlaybackMode(preferred_mode)

            # Reduce confidence if overriding recommendation
            if preference_mode != recommended_mode:
                confidence *= 0.7

            return preference_mode, confidence

        # Check for performance preference
        if preferences.get("prefer_speed", False):
            if recommended_mode == PlaybackMode.STORED_DATA:
                return recommended_mode, confidence
            else:
                return PlaybackMode.REALTIME_ONLY, confidence * 0.8

        # Check for quality preference
        if preferences.get("prefer_quality", False):
            if recommended_mode in [PlaybackMode.STORED_DATA, PlaybackMode.HYBRID]:
                return recommended_mode, confidence
            else:
                return PlaybackMode.HYBRID, confidence * 0.8

        return recommended_mode, confidence


# Factory function for easy instantiation
async def create_smart_mode_selector(
    data_access: Workflow5DataAccess, cache_manager: Workflow5CacheManager
) -> PlaybackModeSelector:
    """Create a configured smart mode selector."""
    analyzer = ProcessingStatusAnalyzer(data_access, cache_manager)
    return PlaybackModeSelector(analyzer)

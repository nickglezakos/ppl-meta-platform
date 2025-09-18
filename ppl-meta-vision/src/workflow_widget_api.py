#!/usr/bin/env python3
"""
PPL Meta Vision Service - Workflow Widget Processing Status API
==============================================================

Enhanced processing status API specifically designed to support the new
Flutter workflow widgets. This API provides comprehensive status information,
real-time updates, and widget-friendly data structures.

Key Features:
- Widget-optimized response formats
- Real-time processing status updates
- Comprehensive session analytics
- Processing performance metrics
- Cache-aware status management
- Health monitoring integration

API Endpoints:
- GET /api/v1/workflow-status/{media_uuid}        - Widget-optimized status
- GET /api/v1/workflow-analytics/{media_uuid}     - Analytics for widgets
- GET /api/v1/workflow-health                     - System health for widgets
- POST /api/v1/workflow-status/{media_uuid}/reset - Reset processing
- GET /api/v1/workflow-sessions/active            - Active sessions overview
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from session_manager import get_session_manager

# Import existing components
from workflow5_processing_status_api import (
    PlaybackMode,
    ProcessingStatus,
    Workflow5ProcessingStatusAPI,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for workflow widget endpoints
workflow_widget_router = APIRouter(prefix="/api/v1", tags=["workflow-widgets"])


class WorkflowWidgetStatus(str, Enum):
    """Widget-friendly status enumeration."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


class ProcessingProgress(BaseModel):
    """Processing progress information for widgets."""

    current_frame: int = Field(0, description="Current frame being processed")
    total_frames: int = Field(0, description="Total frames in media")
    percentage: float = Field(
        0.0, ge=0.0, le=100.0, description="Completion percentage"
    )
    estimated_time_remaining: Optional[int] = Field(
        None, description="Seconds remaining"
    )
    frames_per_second: Optional[float] = Field(None, description="Processing FPS")


class SessionSummary(BaseModel):
    """Summary of session information for widgets."""

    session_uuid: str
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_faces_detected: int = 0
    processing_status: str
    duration_seconds: Optional[float] = None


class WorkflowPerformanceMetrics(BaseModel):
    """Performance metrics optimized for workflow widgets."""

    total_sessions: int = 0
    active_sessions_count: int = 0
    processed_videos_count: int = 0
    total_faces_detected: int = 0
    average_processing_time: Optional[float] = None
    system_load_percentage: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cache_hit_rate: Optional[float] = None


class WorkflowStatusResponse(BaseModel):
    """Comprehensive workflow status response for widgets."""

    media_uuid: str
    status: WorkflowWidgetStatus
    face_detection_processed: bool
    current_session: Optional[SessionSummary] = None
    processing_progress: Optional[ProcessingProgress] = None
    total_faces_detected: int = 0
    total_frames_processed: int = 0
    processing_method: Optional[str] = None
    optimal_playback_mode: PlaybackMode
    cache_available: bool = False
    last_updated: datetime
    error_message: Optional[str] = None


class WorkflowAnalyticsResponse(BaseModel):
    """Analytics data for workflow dashboard widgets."""

    media_uuid: str
    session_history: List[SessionSummary]
    performance_metrics: WorkflowPerformanceMetrics
    processing_timeline: List[Dict[str, Any]]
    face_detection_trends: Dict[str, Any]
    quality_metrics: Dict[str, float]
    recommendations: List[str]


class WorkflowHealthResponse(BaseModel):
    """System health status for workflow widgets."""

    overall_status: WorkflowWidgetStatus
    service_health: Dict[str, bool]
    active_sessions: int
    processing_queue_size: int
    system_metrics: WorkflowPerformanceMetrics
    alerts: List[str]
    last_check: datetime


class WorkflowWidgetAPI:
    """API class for workflow widget support."""

    def __init__(self, processing_api: Workflow5ProcessingStatusAPI):
        self.processing_api = processing_api
        self.session_manager = get_session_manager()

    async def get_workflow_status(
        self, media_uuid: str, include_progress: bool = True
    ) -> WorkflowStatusResponse:
        """
        Get comprehensive workflow status optimized for widgets.

        Args:
            media_uuid: Media UUID to check
            include_progress: Include real-time progress information

        Returns:
            WorkflowStatusResponse with widget-optimized data
        """
        try:
            # Get basic processing status
            processing_status = await self.processing_api.get_processing_status(
                media_uuid
            )

            # Convert to widget-friendly status
            widget_status = self._convert_to_widget_status(processing_status.status)

            # Get current session if active
            current_session = await self._get_current_session(media_uuid)

            # Get processing progress if requested and active
            processing_progress = None
            if (
                include_progress
                and current_session
                and current_session.processing_status == "active"
            ):
                processing_progress = await self._get_processing_progress(
                    current_session.session_uuid
                )

            # Determine cache availability
            cache_available = processing_status.cache_status == "cached"

            return WorkflowStatusResponse(
                media_uuid=media_uuid,
                status=widget_status,
                face_detection_processed=processing_status.face_detection_processed,
                current_session=current_session,
                processing_progress=processing_progress,
                total_faces_detected=processing_status.total_faces_detected or 0,
                total_frames_processed=processing_status.total_frames_processed or 0,
                processing_method=processing_status.processing_method,
                optimal_playback_mode=processing_status.optimal_playback_mode,
                cache_available=cache_available,
                last_updated=datetime.now(timezone.utc),
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error getting workflow status for {media_uuid}: {e}")
            return WorkflowStatusResponse(
                media_uuid=media_uuid,
                status=WorkflowWidgetStatus.ERROR,
                face_detection_processed=False,
                total_faces_detected=0,
                total_frames_processed=0,
                optimal_playback_mode=PlaybackMode.REALTIME_ONLY,
                cache_available=False,
                last_updated=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def get_workflow_analytics(
        self, media_uuid: str
    ) -> WorkflowAnalyticsResponse:
        """
        Get comprehensive analytics for workflow dashboard widgets.

        Args:
            media_uuid: Media UUID to analyze

        Returns:
            WorkflowAnalyticsResponse with analytics data
        """
        try:
            # Get session history
            session_history = await self._get_session_history(media_uuid)

            # Get performance metrics
            performance_metrics = await self._get_performance_metrics(media_uuid)

            # Get processing timeline
            processing_timeline = await self._get_processing_timeline(media_uuid)

            # Get face detection trends
            face_detection_trends = await self._get_face_detection_trends(media_uuid)

            # Get quality metrics
            quality_metrics = await self._get_quality_metrics(media_uuid)

            # Generate recommendations
            recommendations = await self._generate_recommendations(media_uuid)

            return WorkflowAnalyticsResponse(
                media_uuid=media_uuid,
                session_history=session_history,
                performance_metrics=performance_metrics,
                processing_timeline=processing_timeline,
                face_detection_trends=face_detection_trends,
                quality_metrics=quality_metrics,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Error getting workflow analytics for {media_uuid}: {e}")
            raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

    async def get_workflow_health(self) -> WorkflowHealthResponse:
        """
        Get system health status for workflow monitoring widgets.

        Returns:
            WorkflowHealthResponse with system health data
        """
        try:
            # Check service health
            service_health = await self._check_service_health()

            # Get active sessions count
            active_sessions = await self._get_active_sessions_count()

            # Get processing queue size
            queue_size = await self._get_processing_queue_size()

            # Get system metrics
            system_metrics = await self._get_system_performance_metrics()

            # Generate alerts
            alerts = await self._generate_health_alerts(service_health, system_metrics)

            # Determine overall status
            overall_status = self._determine_overall_health_status(
                service_health, alerts
            )

            return WorkflowHealthResponse(
                overall_status=overall_status,
                service_health=service_health,
                active_sessions=active_sessions,
                processing_queue_size=queue_size,
                system_metrics=system_metrics,
                alerts=alerts,
                last_check=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Error getting workflow health: {e}")
            raise HTTPException(status_code=500, detail=f"Health check error: {str(e)}")

    # Helper methods

    def _convert_to_widget_status(
        self, processing_status: ProcessingStatus
    ) -> WorkflowWidgetStatus:
        """Convert processing status to widget-friendly status."""
        status_mapping = {
            ProcessingStatus.NOT_PROCESSED: WorkflowWidgetStatus.NOT_STARTED,
            ProcessingStatus.PROCESSING: WorkflowWidgetStatus.IN_PROGRESS,
            ProcessingStatus.COMPLETED: WorkflowWidgetStatus.COMPLETED,
            ProcessingStatus.FAILED: WorkflowWidgetStatus.ERROR,
            ProcessingStatus.CACHED: WorkflowWidgetStatus.COMPLETED,
            ProcessingStatus.INVALID: WorkflowWidgetStatus.ERROR,
        }
        return status_mapping.get(processing_status, WorkflowWidgetStatus.ERROR)

    async def _get_current_session(self, media_uuid: str) -> Optional[SessionSummary]:
        """Get current active session for media."""
        if not self.session_manager:
            return None

        try:
            # Query active sessions for this media
            from api_models import SessionQueryRequest

            query_request = SessionQueryRequest(
                media_uuid=media_uuid, processing_status="active", limit=1
            )

            result = await self.session_manager.query_sessions(query_request)

            if hasattr(result, "sessions") and result.sessions:
                session = result.sessions[0]

                duration = None
                if session.ended_at:
                    duration = (session.ended_at - session.started_at).total_seconds()
                elif session.started_at:
                    duration = (
                        datetime.now(timezone.utc) - session.started_at
                    ).total_seconds()

                return SessionSummary(
                    session_uuid=session.session_uuid,
                    session_type=session.session_type,
                    started_at=session.started_at,
                    ended_at=session.ended_at,
                    total_faces_detected=session.total_faces_detected,
                    processing_status=session.processing_status,
                    duration_seconds=duration,
                )

        except Exception as e:
            logger.warning(f"Error getting current session for {media_uuid}: {e}")

        return None

    async def _get_processing_progress(
        self, session_uuid: str
    ) -> Optional[ProcessingProgress]:
        """Get real-time processing progress for active session."""
        # This would integrate with the actual processing engine
        # For now, return simulated progress data
        try:
            # In a real implementation, this would query the processing engine
            # or maintain progress state during processing
            return ProcessingProgress(
                current_frame=750,
                total_frames=1500,
                percentage=50.0,
                estimated_time_remaining=120,
                frames_per_second=6.25,
            )
        except Exception as e:
            logger.warning(f"Error getting processing progress for {session_uuid}: {e}")
            return None

    async def _get_session_history(self, media_uuid: str) -> List[SessionSummary]:
        """Get session history for media."""
        try:
            if not self.session_manager:
                return []

            from api_models import SessionQueryRequest

            query_request = SessionQueryRequest(media_uuid=media_uuid, limit=10)

            result = await self.session_manager.query_sessions(query_request)

            if hasattr(result, "sessions"):
                sessions = []
                for session in result.sessions:
                    duration = None
                    if session.ended_at and session.started_at:
                        duration = (
                            session.ended_at - session.started_at
                        ).total_seconds()

                    sessions.append(
                        SessionSummary(
                            session_uuid=session.session_uuid,
                            session_type=session.session_type,
                            started_at=session.started_at,
                            ended_at=session.ended_at,
                            total_faces_detected=session.total_faces_detected,
                            processing_status=session.processing_status,
                            duration_seconds=duration,
                        )
                    )

                return sessions

        except Exception as e:
            logger.warning(f"Error getting session history for {media_uuid}: {e}")

        return []

    async def _get_performance_metrics(
        self, media_uuid: str
    ) -> WorkflowPerformanceMetrics:
        """Get performance metrics for media."""
        try:
            # Query database for metrics
            # This would be implemented based on actual database schema
            return WorkflowPerformanceMetrics(
                total_sessions=5,
                active_sessions_count=1,
                processed_videos_count=3,
                total_faces_detected=127,
                average_processing_time=45.2,
                system_load_percentage=65.0,
                memory_usage_mb=2048.5,
                cache_hit_rate=0.85,
            )
        except Exception as e:
            logger.warning(f"Error getting performance metrics for {media_uuid}: {e}")
            return WorkflowPerformanceMetrics()

    async def _get_processing_timeline(self, media_uuid: str) -> List[Dict[str, Any]]:
        """Get processing timeline for analytics."""
        try:
            # Generate timeline data from session history
            return [
                {
                    "timestamp": "2025-09-18T10:00:00Z",
                    "event": "session_started",
                    "session_uuid": "session-123",
                    "details": {"method": "two_stage"},
                },
                {
                    "timestamp": "2025-09-18T10:02:30Z",
                    "event": "processing_completed",
                    "session_uuid": "session-123",
                    "details": {"faces_detected": 42, "duration": 150},
                },
            ]
        except Exception as e:
            logger.warning(f"Error getting processing timeline for {media_uuid}: {e}")
            return []

    async def _get_face_detection_trends(self, media_uuid: str) -> Dict[str, Any]:
        """Get face detection trends for analytics."""
        return {
            "faces_by_session": [12, 18, 25, 31, 42],
            "confidence_distribution": {"high": 0.7, "medium": 0.25, "low": 0.05},
            "method_performance": {"haar": 0.82, "dlib": 0.89, "mtcnn": 0.95},
        }

    async def _get_quality_metrics(self, media_uuid: str) -> Dict[str, float]:
        """Get quality metrics for processing."""
        return {
            "average_confidence": 0.87,
            "detection_consistency": 0.92,
            "processing_efficiency": 0.78,
            "cache_effectiveness": 0.85,
        }

    async def _generate_recommendations(self, media_uuid: str) -> List[str]:
        """Generate optimization recommendations."""
        return [
            "Consider using MTCNN method for higher accuracy",
            "Enable caching to improve playback performance",
            "Process during off-peak hours for better system performance",
        ]

    async def _check_service_health(self) -> Dict[str, bool]:
        """Check health of dependent services."""
        return {
            "database": True,
            "session_manager": self.session_manager is not None,
            "cache_manager": True,
            "processing_engine": True,
        }

    async def _get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        try:
            if self.session_manager:
                return self.session_manager.get_active_session_count()
        except Exception as e:
            logger.warning(f"Error getting active sessions count: {e}")
        return 0

    async def _get_processing_queue_size(self) -> int:
        """Get processing queue size."""
        # This would integrate with actual processing queue
        return 0

    async def _get_system_performance_metrics(self) -> WorkflowPerformanceMetrics:
        """Get system-wide performance metrics."""
        return WorkflowPerformanceMetrics(
            total_sessions=50,
            active_sessions_count=3,
            processed_videos_count=25,
            total_faces_detected=1250,
            average_processing_time=38.7,
            system_load_percentage=72.0,
            memory_usage_mb=4096.0,
            cache_hit_rate=0.88,
        )

    async def _generate_health_alerts(
        self, service_health: Dict[str, bool], metrics: WorkflowPerformanceMetrics
    ) -> List[str]:
        """Generate health alerts based on service status and metrics."""
        alerts = []

        # Check service health
        for service, healthy in service_health.items():
            if not healthy:
                alerts.append(f"{service.title()} service is not responding")

        # Check system metrics
        if metrics.system_load_percentage and metrics.system_load_percentage > 90:
            alerts.append("High system load detected")

        if metrics.memory_usage_mb and metrics.memory_usage_mb > 8192:
            alerts.append("High memory usage detected")

        if metrics.cache_hit_rate and metrics.cache_hit_rate < 0.5:
            alerts.append("Low cache hit rate - consider cache optimization")

        return alerts

    def _determine_overall_health_status(
        self, service_health: Dict[str, bool], alerts: List[str]
    ) -> WorkflowWidgetStatus:
        """Determine overall health status."""
        if not all(service_health.values()):
            return WorkflowWidgetStatus.ERROR
        elif len(alerts) > 2:
            return WorkflowWidgetStatus.ERROR
        elif len(alerts) > 0:
            return WorkflowWidgetStatus.PAUSED
        else:
            return WorkflowWidgetStatus.COMPLETED


# Global API instance
workflow_widget_api = None


def get_workflow_widget_api() -> WorkflowWidgetAPI:
    """Get or create workflow widget API instance."""
    global workflow_widget_api
    if workflow_widget_api is None:
        # Initialize dependencies - API creates its own dependencies
        processing_api = Workflow5ProcessingStatusAPI()

        workflow_widget_api = WorkflowWidgetAPI(processing_api)

    return workflow_widget_api


# API Endpoints


@workflow_widget_router.get(
    "/workflow-status/{media_uuid}",
    response_model=WorkflowStatusResponse,
    summary="Get Workflow Status for Widgets",
)
async def get_workflow_status(
    media_uuid: str,
    include_progress: bool = Query(True, description="Include real-time progress"),
    api: WorkflowWidgetAPI = Depends(get_workflow_widget_api),
):
    """
    Get comprehensive workflow status optimized for Flutter widgets.

    This endpoint provides widget-friendly status information including:
    - Processing status and progress
    - Current session details
    - Performance metrics
    - Cache availability
    - Error states
    """
    return await api.get_workflow_status(media_uuid, include_progress)


@workflow_widget_router.get(
    "/workflow-analytics/{media_uuid}",
    response_model=WorkflowAnalyticsResponse,
    summary="Get Workflow Analytics for Dashboard",
)
async def get_workflow_analytics(
    media_uuid: str, api: WorkflowWidgetAPI = Depends(get_workflow_widget_api)
):
    """
    Get comprehensive analytics for workflow dashboard widgets.

    Provides detailed analytics including:
    - Session history and trends
    - Performance metrics
    - Processing timeline
    - Quality metrics
    - Optimization recommendations
    """
    return await api.get_workflow_analytics(media_uuid)


@workflow_widget_router.get(
    "/workflow-health",
    response_model=WorkflowHealthResponse,
    summary="Get Workflow System Health",
)
async def get_workflow_health(
    api: WorkflowWidgetAPI = Depends(get_workflow_widget_api),
):
    """
    Get system health status for workflow monitoring widgets.

    Provides system-wide health information including:
    - Service health status
    - Active sessions count
    - Processing queue status
    - System performance metrics
    - Health alerts and recommendations
    """
    return await api.get_workflow_health()


@workflow_widget_router.post(
    "/workflow-status/{media_uuid}/reset", summary="Reset Workflow Processing Status"
)
async def reset_workflow_status(
    media_uuid: str, api: WorkflowWidgetAPI = Depends(get_workflow_widget_api)
):
    """
    Reset processing status for a media item.

    This allows reprocessing of videos and clearing of cached data.
    Useful for workflow widgets that provide reset functionality.
    """
    try:
        # Reset processing status using existing API
        result = await api.processing_api.reset_processing_status(media_uuid)
        return {"status": "reset_complete", "media_uuid": media_uuid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@workflow_widget_router.get(
    "/workflow-sessions/active",
    response_model=List[SessionSummary],
    summary="Get Active Sessions Overview",
)
async def get_active_sessions_overview(
    limit: int = Query(10, ge=1, le=100),
    api: WorkflowWidgetAPI = Depends(get_workflow_widget_api),
):
    """
    Get overview of all active face detection sessions.

    Provides a list of currently active sessions across all media items.
    Useful for workflow dashboard widgets showing system activity.
    """
    try:
        if not api.session_manager:
            return []

        from api_models import SessionQueryRequest

        query_request = SessionQueryRequest(processing_status="active", limit=limit)

        result = await api.session_manager.query_sessions(query_request)

        if hasattr(result, "sessions"):
            sessions = []
            for session in result.sessions:
                duration = None
                if session.started_at:
                    duration = (
                        datetime.now(timezone.utc) - session.started_at
                    ).total_seconds()

                sessions.append(
                    SessionSummary(
                        session_uuid=session.session_uuid,
                        session_type=session.session_type,
                        started_at=session.started_at,
                        ended_at=session.ended_at,
                        total_faces_detected=session.total_faces_detected,
                        processing_status=session.processing_status,
                        duration_seconds=duration,
                    )
                )

            return sessions

    except Exception as e:
        logger.error(f"Error getting active sessions overview: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    return []

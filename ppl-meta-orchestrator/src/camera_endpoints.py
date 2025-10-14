"""
PPL Meta Orchestrator - Camera Event Handling and API Endpoints
Phase 1 Implementation: Camera video storage event processing and workflow triggers
Phase 4 Integration: Recording session database persistence
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Phase 4 imports for session tracking
from models.recording_session import SessionStatus
from pydantic import BaseModel
from services.recording_session_service import RecordingSessionService
from workflow_orchestrator import (
    CameraEventData,
    CameraFaceDetectionWorkflowOrchestrator,
    WorkflowExecution,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer()


def get_auth_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract and validate authentication token."""
    return credentials.credentials


# Create router for workflow endpoints
workflow_router = APIRouter(prefix="/workflows", tags=["workflows"])


class BulkProcessingRequest(BaseModel):
    """Request model for bulk processing."""

    media_ids: List[str]
    methods: List[str] = ["two_stage"]
    processing_options: Optional[Dict[str, Any]] = None
    priority: str = "normal"


class CameraEventRequest(BaseModel):
    """Request model for camera events."""

    event_type: str
    camera_device_id: str
    recording_session_id: str
    video_file_path: str
    user_id: str
    recording_duration_seconds: float
    file_size_bytes: int
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    workflow_id: str
    workflow_type: str
    status: str
    user_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_media_count: int
    processed_media_count: int
    failed_media_count: int
    camera_device_ids: List[str]
    error_message: Optional[str]
    metadata: Dict[str, Any]


class MethodLifecycleResponse(BaseModel):
    """Response model for method lifecycle."""

    lifecycle_id: str
    method: str
    media_id: str
    camera_device_id: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    results_count: Optional[int]
    confidence_scores: List[float]


class WorkflowAnalyticsResponse(BaseModel):
    """Response model for workflow analytics."""

    total_workflows: int
    active_workflows: int
    completed_workflows: int
    failed_workflows: int
    total_media_processed: int
    average_processing_time_seconds: Optional[float]
    camera_workflows: int
    bulk_workflows: int


class CameraWorkflowEndpoints:
    """Camera workflow API endpoints with Phase 4 recording session tracking."""

    def __init__(self, orchestrator: CameraFaceDetectionWorkflowOrchestrator):
        self.orchestrator = orchestrator
        self.session_service = RecordingSessionService()

    def _workflow_to_response(
        self, workflow: WorkflowExecution
    ) -> WorkflowStatusResponse:
        """Convert workflow execution to response model."""
        return WorkflowStatusResponse(
            workflow_id=workflow.workflow_id,
            workflow_type=workflow.workflow_type.value,
            status=workflow.status.value,
            user_id=workflow.user_id,
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            total_media_count=workflow.total_media_count,
            processed_media_count=workflow.processed_media_count,
            failed_media_count=workflow.failed_media_count,
            camera_device_ids=workflow.camera_device_ids,
            error_message=workflow.error_message,
            metadata=workflow.metadata,
        )

    async def handle_camera_event(
        self, event_request: CameraEventRequest
    ) -> Dict[str, Any]:
        """Handle camera recording events with automated workflow triggers and session tracking."""
        try:
            logger.info(
                f"Received camera event: {event_request.event_type} "
                f"from camera {event_request.camera_device_id}"
            )

            # Phase 4: Handle session tracking based on event type
            session_uuid = event_request.recording_session_id
            session_result = await self._handle_session_lifecycle(
                event_request, session_uuid
            )

            # Convert request to event data
            event_data = CameraEventData(
                event_type=event_request.event_type,
                camera_device_id=event_request.camera_device_id,
                recording_session_id=event_request.recording_session_id,
                video_file_path=event_request.video_file_path,
                user_id=event_request.user_id,
                recording_duration_seconds=event_request.recording_duration_seconds,
                file_size_bytes=event_request.file_size_bytes,
                timestamp=event_request.timestamp or datetime.now(),
                metadata=event_request.metadata or {},
            )

            # Handle the camera event
            workflow = await self.orchestrator.handle_camera_recording_event(event_data)

            # Phase 4: Update session with workflow information
            if workflow and session_result.get("session_created"):
                await self._update_session_workflow(session_uuid, workflow)

            response = {
                "status": "success",
                "session_uuid": session_uuid,
                "session_status": session_result.get("session_status"),
                "session_action": session_result.get("action"),
            }

            if workflow:
                response.update(
                    {
                        "message": "Camera event processed successfully",
                        "workflow_created": True,
                        "workflow_id": workflow.workflow_id,
                        "workflow_status": workflow.status.value,
                    }
                )
            else:
                response.update(
                    {
                        "message": "Camera event processed, no workflow created",
                        "workflow_created": False,
                        "reason": "Auto face detection disabled or event not applicable",
                    }
                )

            return response

        except Exception as e:
            logger.error(f"Failed to handle camera event: {e}")
            # Try to mark session as failed if it exists
            try:
                if hasattr(event_request, "recording_session_id"):
                    self.session_service.update_session_status(
                        event_request.recording_session_id,
                        SessionStatus.FAILED,
                        error_message=str(e),
                    )
            except Exception:
                pass  # Don't fail if session update fails

            raise HTTPException(
                status_code=500, detail=f"Camera event processing failed: {str(e)}"
            )

    async def _handle_session_lifecycle(
        self, event_request: CameraEventRequest, session_uuid: str
    ) -> Dict[str, Any]:
        """Handle recording session lifecycle based on event type."""
        event_type = event_request.event_type.lower()

        if event_type in ["recording_started", "start_recording"]:
            # Create new recording session
            session = self.session_service.create_session(
                camera_device_id=event_request.camera_device_id,
                user_id=event_request.user_id,
                recording_config={
                    "event_type": event_request.event_type,
                    "video_file_path": event_request.video_file_path,
                },
                workflow_metadata=event_request.metadata or {},
            )
            return {
                "action": "session_created",
                "session_created": True,
                "session_status": session.status,
                "session_uuid": session.session_uuid,
            }

        elif event_type in ["recording_progress", "progress_update"]:
            # Update session progress
            success = self.session_service.update_session_progress(
                session_uuid=session_uuid,
                duration_seconds=event_request.recording_duration_seconds,
                estimated_file_size_bytes=event_request.file_size_bytes,
                frames_recorded=int(
                    event_request.recording_duration_seconds * 30
                ),  # Estimate 30 FPS
            )
            return {
                "action": "progress_updated",
                "session_created": False,
                "session_status": "active" if success else "unknown",
                "progress_updated": success,
            }

        elif event_type in [
            "recording_completed",
            "recording_finished",
            "end_recording",
        ]:
            # Complete recording session
            success = self.session_service.update_session_status(
                session_uuid=session_uuid, status=SessionStatus.COMPLETED
            )
            # Final progress update
            self.session_service.update_session_progress(
                session_uuid=session_uuid,
                duration_seconds=event_request.recording_duration_seconds,
                estimated_file_size_bytes=event_request.file_size_bytes,
                frames_recorded=int(event_request.recording_duration_seconds * 30),
            )
            return {
                "action": "session_completed",
                "session_created": False,
                "session_status": "completed" if success else "unknown",
                "session_completed": success,
            }

        elif event_type in ["recording_failed", "recording_error"]:
            # Mark session as failed
            success = self.session_service.update_session_status(
                session_uuid=session_uuid,
                status=SessionStatus.FAILED,
                error_message=event_request.metadata.get(
                    "error_message", "Recording failed"
                ),
            )
            return {
                "action": "session_failed",
                "session_created": False,
                "session_status": "failed" if success else "unknown",
                "error_message": event_request.metadata.get(
                    "error_message", "Recording failed"
                ),
            }

        else:
            # Heartbeat for unknown event types
            self.session_service.heartbeat_session(session_uuid)
            return {
                "action": "heartbeat",
                "session_created": False,
                "session_status": "active",
                "event_type": event_type,
            }

    async def _update_session_workflow(
        self, session_uuid: str, workflow: WorkflowExecution
    ) -> bool:
        """Update session with workflow information and trigger face detection tracking."""
        try:
            # Update workflow metadata
            workflow_metadata = {
                "workflow_id": workflow.workflow_id,
                "workflow_type": workflow.workflow_type.value,
                "workflow_status": workflow.status.value,
                "media_count": workflow.total_media_count,
                "created_at": (
                    workflow.created_at.isoformat() if workflow.created_at else None
                ),
            }

            # Get current session to update metadata
            session = self.session_service.get_session(session_uuid)
            if session and session.workflow_metadata:
                session.workflow_metadata.update(workflow_metadata)
            else:
                session.workflow_metadata = workflow_metadata

            # Trigger face detection tracking if workflow involves face detection
            if "face_detection" in workflow.workflow_type.value.lower():
                success = self.session_service.trigger_face_detection(
                    session_uuid=session_uuid,
                    face_detection_session_uuid=workflow.workflow_id,
                    workflow_execution_id=workflow.workflow_id,
                )
                logger.info(
                    f"Face detection triggered for session {session_uuid}: {success}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to update session workflow: {e}")
            return False

    async def start_bulk_processing(
        self,
        request: BulkProcessingRequest,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """Start bulk face detection processing workflow."""
        try:
            logger.info(
                f"Starting bulk processing for {len(request.media_ids)} "
                f"media files with methods: {request.methods}"
            )

            workflow = await self.orchestrator.start_bulk_processing(
                media_ids=request.media_ids,
                methods=request.methods,
                user_id=user_id,
                processing_options=request.processing_options,
                priority=request.priority,
                auth_token=auth_token,
            )

            return self._workflow_to_response(workflow)

        except Exception as e:
            logger.error(f"Failed to start bulk processing: {e}")
            raise HTTPException(
                status_code=500, detail=f"Bulk processing initiation failed: {str(e)}"
            )

    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatusResponse:
        """Get detailed workflow status with method lifecycles."""
        workflow = await self.orchestrator.get_workflow_status(workflow_id)

        if not workflow:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found"
            )

        return self._workflow_to_response(workflow)

    async def get_workflow_lifecycles(
        self, workflow_id: str
    ) -> List[MethodLifecycleResponse]:
        """Get method lifecycles for a workflow."""
        workflow = await self.orchestrator.get_workflow_status(workflow_id)

        if not workflow:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found"
            )

        return [
            MethodLifecycleResponse(
                lifecycle_id=lifecycle.lifecycle_id,
                method=lifecycle.method,
                media_id=lifecycle.media_id,
                camera_device_id=lifecycle.camera_device_id,
                status=lifecycle.status.value,
                started_at=lifecycle.started_at,
                completed_at=lifecycle.completed_at,
                error_message=lifecycle.error_message,
                results_count=lifecycle.results_count,
                confidence_scores=lifecycle.confidence_scores,
            )
            for lifecycle in workflow.method_lifecycles
        ]

    async def get_user_workflows(
        self, user_id: str, limit: int = 50
    ) -> List[WorkflowStatusResponse]:
        """Get workflows for specific user."""
        workflows = await self.orchestrator.get_user_workflows(
            user_id=user_id, limit=limit
        )

        return [self._workflow_to_response(w) for w in workflows]

    async def get_camera_workflows(
        self, camera_device_id: str, limit: int = 50
    ) -> List[WorkflowStatusResponse]:
        """Get workflows for specific camera device."""
        workflows = await self.orchestrator.get_camera_workflows(
            camera_device_id=camera_device_id, limit=limit
        )

        return [self._workflow_to_response(w) for w in workflows]

    async def get_camera_analytics(
        self,
        camera_device_id: str,
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get camera analytics with workflow correlation."""
        start_dt = None
        end_dt = None

        if time_range_start:
            try:
                start_dt = datetime.fromisoformat(time_range_start)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid time_range_start format. Use ISO format.",
                )

        if time_range_end:
            try:
                end_dt = datetime.fromisoformat(time_range_end)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid time_range_end format. Use ISO format.",
                )

        analytics = await self.orchestrator.get_camera_analytics(
            camera_device_id=camera_device_id,
            time_range_start=start_dt,
            time_range_end=end_dt,
        )

        return analytics

    async def get_workflow_analytics(self) -> WorkflowAnalyticsResponse:
        """Get overall workflow analytics."""
        active_workflows = list(self.orchestrator.active_workflows.values())
        historical_workflows = self.orchestrator.workflow_history
        all_workflows = active_workflows + historical_workflows

        completed_workflows = [
            w for w in all_workflows if w.status == WorkflowStatus.COMPLETED
        ]
        failed_workflows = [
            w for w in all_workflows if w.status == WorkflowStatus.FAILED
        ]
        camera_workflows = [w for w in all_workflows if w.camera_device_ids]
        bulk_workflows = [
            w for w in all_workflows if w.workflow_type.value == "bulk_processing"
        ]

        # Calculate average processing time
        avg_processing_time = None
        if completed_workflows:
            processing_times = []
            for w in completed_workflows:
                if w.started_at and w.completed_at:
                    duration = (w.completed_at - w.started_at).total_seconds()
                    processing_times.append(duration)

            if processing_times:
                avg_processing_time = sum(processing_times) / len(processing_times)

        return WorkflowAnalyticsResponse(
            total_workflows=len(all_workflows),
            active_workflows=len(active_workflows),
            completed_workflows=len(completed_workflows),
            failed_workflows=len(failed_workflows),
            total_media_processed=sum(w.processed_media_count for w in all_workflows),
            average_processing_time_seconds=avg_processing_time,
            camera_workflows=len(camera_workflows),
            bulk_workflows=len(bulk_workflows),
        )


# FastAPI route definitions
@workflow_router.post("/camera/events")
async def handle_camera_event_endpoint(
    event_request: CameraEventRequest,
) -> Dict[str, Any]:
    """
    Handle camera recording events with automated workflow triggers.

    This endpoint receives events from the Camera Service when recordings
    are completed and automatically triggers face detection workflows
    based on user settings.
    """
    # Get endpoints from global workflow_endpoints (will be set in main.py)
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.handle_camera_event(event_request)


@workflow_router.post("/face-detection/bulk-process")
async def start_bulk_processing_endpoint(
    request: BulkProcessingRequest,
    auth_token: str = Depends(get_auth_token),
    user_id: Optional[str] = None,
) -> WorkflowStatusResponse:
    """
    Start bulk face detection processing workflow.

    Processes multiple media files with specified detection methods
    and tracks progress through method-specific lifecycles.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.start_bulk_processing(request, user_id, auth_token)


@workflow_router.get("/face-detection/status/{workflow_id}")
async def get_workflow_status_endpoint(workflow_id: str) -> WorkflowStatusResponse:
    """
    Get detailed workflow status with complete traceability.

    Returns comprehensive workflow information including method
    lifecycles, camera attribution, and processing statistics.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.get_workflow_status(workflow_id)


@workflow_router.get("/face-detection/lifecycles/{workflow_id}")
async def get_workflow_lifecycles_endpoint(
    workflow_id: str,
) -> List[MethodLifecycleResponse]:
    """
    Get method-specific lifecycles for a workflow.

    Returns detailed information about each detection method's
    processing lifecycle within the workflow.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.get_workflow_lifecycles(workflow_id)


@workflow_router.get("/user/{user_id}/workflows")
async def get_user_workflows_endpoint(
    user_id: str, limit: int = 50
) -> List[WorkflowStatusResponse]:
    """
    Get workflows for specific user with traceability.

    Returns user's workflow history including camera-triggered
    and manually initiated workflows.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.get_user_workflows(user_id, limit)


@workflow_router.get("/camera/{camera_device_id}/workflows")
async def get_camera_workflows_endpoint(
    camera_device_id: str, limit: int = 50
) -> List[WorkflowStatusResponse]:
    """
    Get workflows for specific camera device.

    Returns camera-specific workflow history with complete
    device attribution and processing statistics.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.get_camera_workflows(camera_device_id, limit)


@workflow_router.get("/camera/{camera_device_id}/analytics")
async def get_camera_analytics_endpoint(
    camera_device_id: str,
    time_range_start: Optional[str] = None,
    time_range_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get camera analytics with workflow correlation.

    Returns comprehensive analytics including face detection
    performance, workflow statistics, and device-specific insights.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.get_camera_analytics(
        camera_device_id, time_range_start, time_range_end
    )


@workflow_router.get("/analytics")
async def get_workflow_analytics_endpoint() -> WorkflowAnalyticsResponse:
    """
    Get overall workflow analytics.

    Returns platform-wide workflow statistics including
    performance metrics and processing insights.
    """
    from main import workflow_endpoints

    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return await workflow_endpoints.get_workflow_analytics()


# Health check endpoint specifically for workflow functionality
@workflow_router.get("/health")
async def workflow_health_check() -> Dict[str, Any]:
    """
    Health check for workflow orchestration functionality.

    Returns status of workflow processing capabilities
    and service integrations.
    """
    return {
        "status": "healthy",
        "component": "workflow_orchestrator",
        "capabilities": [
            "camera_event_processing",
            "bulk_processing",
            "method_lifecycle_tracking",
            "traceability_audit",
            "camera_analytics",
        ],
        "timestamp": datetime.now().isoformat(),
    }

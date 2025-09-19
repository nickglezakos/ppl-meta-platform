"""
PPL Meta Orchestrator - Session Endpoints
Provides session management for workflow tracking and status monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from workflow_orchestrator import CameraFaceDetectionWorkflowOrchestrator

logger = logging.getLogger(__name__)

# Create router for session endpoints
sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionResponse(BaseModel):
    """Response model for session data."""

    session_id: str
    workflow_id: str
    media_uuid: str
    status: str  # 'active', 'completed', 'failed', 'cancelled'
    detection_methods: List[str]
    camera_device_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: Optional[float] = None
    results_count: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session."""

    media_uuid: str
    detection_methods: List[str] = ["two_stage"]
    camera_device_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SessionUpdateRequest(BaseModel):
    """Request model for updating session status."""

    status: str
    progress_percentage: Optional[float] = None
    results_count: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionsOverviewResponse(BaseModel):
    """Response model for sessions overview."""

    total_sessions: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
    recent_sessions: List[SessionResponse]


class SessionEndpoints:
    """Session management API endpoints for Orchestrator service."""

    def __init__(self, orchestrator: CameraFaceDetectionWorkflowOrchestrator):
        self.orchestrator = orchestrator

    def _workflow_to_session_response(
        self, workflow, method_lifecycle=None
    ) -> SessionResponse:
        """Convert workflow execution and method lifecycle to session response."""

        # Extract media UUID from workflow metadata or method lifecycle
        media_uuid = None
        if method_lifecycle and method_lifecycle.media_id:
            media_uuid = method_lifecycle.media_id
        elif workflow.workflow_metadata and "media_ids" in workflow.workflow_metadata:
            media_ids = workflow.workflow_metadata["media_ids"]
            media_uuid = media_ids[0] if media_ids else None

        # Extract detection methods
        detection_methods = []
        if method_lifecycle:
            detection_methods = [method_lifecycle.method]
        elif workflow.workflow_metadata and "methods" in workflow.workflow_metadata:
            detection_methods = workflow.workflow_metadata["methods"]

        # Calculate progress percentage
        progress_percentage = None
        if workflow.total_media_count > 0:
            progress_percentage = (
                workflow.processed_media_count / workflow.total_media_count
            ) * 100

        # Get camera device ID
        camera_device_id = None
        if method_lifecycle:
            camera_device_id = method_lifecycle.camera_device_id
        elif (
            workflow.workflow_metadata
            and "camera_device_id" in workflow.workflow_metadata
        ):
            camera_device_id = workflow.workflow_metadata["camera_device_id"]

        # Use method lifecycle ID as session ID, or workflow ID as fallback
        session_id = (
            method_lifecycle.lifecycle_id if method_lifecycle else workflow.workflow_id
        )

        return SessionResponse(
            session_id=session_id,
            workflow_id=workflow.workflow_id,
            media_uuid=media_uuid or "unknown",
            status=(
                method_lifecycle.status if method_lifecycle else workflow.status.value
            ),
            detection_methods=detection_methods,
            camera_device_id=camera_device_id,
            user_id=workflow.user_id,
            created_at=workflow.created_at,
            started_at=(
                method_lifecycle.started_at if method_lifecycle else workflow.started_at
            ),
            completed_at=(
                method_lifecycle.completed_at
                if method_lifecycle
                else workflow.completed_at
            ),
            progress_percentage=progress_percentage,
            results_count=method_lifecycle.results_count if method_lifecycle else None,
            error_message=(
                method_lifecycle.error_message
                if method_lifecycle
                else workflow.error_message
            ),
            metadata=workflow.workflow_metadata or {},
        )

    async def get_session(self, session_id: str) -> SessionResponse:
        """Get a specific session by ID."""
        try:
            # Try to find by method lifecycle ID first
            method_lifecycle = await self.orchestrator.get_method_lifecycle_by_id(
                session_id
            )
            if method_lifecycle:
                workflow = await self.orchestrator.get_workflow_by_id(
                    method_lifecycle.workflow_id
                )
                if workflow:
                    return self._workflow_to_session_response(
                        workflow, method_lifecycle
                    )

            # Fallback: try to find by workflow ID
            workflow = await self.orchestrator.get_workflow_by_id(session_id)
            if workflow:
                return self._workflow_to_session_response(workflow)

            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_sessions(
        self,
        status: Optional[str] = None,
        media_uuid: Optional[str] = None,
        camera_device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SessionResponse]:
        """List sessions with optional filtering."""
        try:
            # Get workflows with optional filtering
            workflows = await self.orchestrator.get_workflows(
                status=status, user_id=user_id, limit=limit, offset=offset
            )

            sessions = []
            for workflow in workflows:
                # Get method lifecycles for this workflow
                method_lifecycles = (
                    await self.orchestrator.get_method_lifecycles_by_workflow(
                        workflow.workflow_id
                    )
                )

                if method_lifecycles:
                    # Create sessions for each method lifecycle
                    for method_lifecycle in method_lifecycles:
                        # Apply additional filters
                        if media_uuid and method_lifecycle.media_id != media_uuid:
                            continue
                        if (
                            camera_device_id
                            and method_lifecycle.camera_device_id != camera_device_id
                        ):
                            continue

                        session = self._workflow_to_session_response(
                            workflow, method_lifecycle
                        )
                        sessions.append(session)
                else:
                    # Create session from workflow only
                    session = self._workflow_to_session_response(workflow)
                    sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new processing session."""
        try:
            # Create workflow for face detection
            workflow = await self.orchestrator.start_bulk_processing(
                media_ids=[request.media_uuid],
                methods=request.detection_methods,
                user_id=request.user_id,
                processing_options=request.metadata,
            )

            # Get the method lifecycle for this workflow
            method_lifecycles = (
                await self.orchestrator.get_method_lifecycles_by_workflow(
                    workflow.workflow_id
                )
            )
            method_lifecycle = method_lifecycles[0] if method_lifecycles else None

            return self._workflow_to_session_response(workflow, method_lifecycle)

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_session(
        self, session_id: str, request: SessionUpdateRequest
    ) -> SessionResponse:
        """Update session status and metadata."""
        try:
            # Try to find and update method lifecycle
            method_lifecycle = await self.orchestrator.get_method_lifecycle_by_id(
                session_id
            )
            if method_lifecycle:
                updated_lifecycle = await self.orchestrator.update_method_lifecycle(
                    lifecycle_id=session_id,
                    status=request.status,
                    results_count=request.results_count,
                    error_message=request.error_message,
                )
                workflow = await self.orchestrator.get_workflow_by_id(
                    updated_lifecycle.workflow_id
                )
                return self._workflow_to_session_response(workflow, updated_lifecycle)

            # Fallback: update workflow
            workflow = await self.orchestrator.get_workflow_by_id(session_id)
            if workflow:
                updated_workflow = await self.orchestrator.update_workflow_status(
                    workflow_id=session_id,
                    status=request.status,
                    error_message=request.error_message,
                )
                return self._workflow_to_session_response(updated_workflow)

            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_session(self, session_id: str) -> Dict[str, str]:
        """Cancel/delete a session."""
        try:
            # Try to cancel method lifecycle
            method_lifecycle = await self.orchestrator.get_method_lifecycle_by_id(
                session_id
            )
            if method_lifecycle:
                await self.orchestrator.update_method_lifecycle(
                    lifecycle_id=session_id, status="cancelled"
                )
                return {
                    "status": "success",
                    "message": f"Session {session_id} cancelled",
                }

            # Fallback: cancel workflow
            workflow = await self.orchestrator.get_workflow_by_id(session_id)
            if workflow:
                await self.orchestrator.update_workflow_status(
                    workflow_id=session_id, status="cancelled"
                )
                return {
                    "status": "success",
                    "message": f"Session {session_id} cancelled",
                }

            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_sessions_overview(self) -> SessionsOverviewResponse:
        """Get overview of all sessions."""
        try:
            # Get workflow statistics
            workflows = await self.orchestrator.get_workflows(limit=1000)

            total_sessions = len(workflows)
            active_sessions = len(
                [w for w in workflows if w.status.value in ["processing", "queued"]]
            )
            completed_sessions = len(
                [w for w in workflows if w.status.value == "completed"]
            )
            failed_sessions = len([w for w in workflows if w.status.value == "failed"])

            # Get recent sessions (last 10)
            recent_workflows = workflows[:10] if workflows else []
            recent_sessions = []

            for workflow in recent_workflows:
                method_lifecycles = (
                    await self.orchestrator.get_method_lifecycles_by_workflow(
                        workflow.workflow_id
                    )
                )
                method_lifecycle = method_lifecycles[0] if method_lifecycles else None
                session = self._workflow_to_session_response(workflow, method_lifecycle)
                recent_sessions.append(session)

            return SessionsOverviewResponse(
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                completed_sessions=completed_sessions,
                failed_sessions=failed_sessions,
                recent_sessions=recent_sessions,
            )

        except Exception as e:
            logger.error(f"Error getting sessions overview: {e}")
            raise HTTPException(status_code=500, detail=str(e))


def create_session_endpoints(orchestrator: CameraFaceDetectionWorkflowOrchestrator):
    """Create session endpoints with the orchestrator instance."""
    session_endpoints = SessionEndpoints(orchestrator)

    @sessions_router.get("/", response_model=List[SessionResponse])
    async def list_sessions(
        status: Optional[str] = Query(None, description="Filter by session status"),
        media_uuid: Optional[str] = Query(None, description="Filter by media UUID"),
        camera_device_id: Optional[str] = Query(
            None, description="Filter by camera device ID"
        ),
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        limit: int = Query(50, description="Maximum number of sessions to return"),
        offset: int = Query(0, description="Number of sessions to skip"),
    ):
        """List all sessions with optional filtering."""
        return await session_endpoints.list_sessions(
            status=status,
            media_uuid=media_uuid,
            camera_device_id=camera_device_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    @sessions_router.get("/overview", response_model=SessionsOverviewResponse)
    async def get_sessions_overview():
        """Get overview of all sessions."""
        return await session_endpoints.get_sessions_overview()

    @sessions_router.post("/", response_model=SessionResponse)
    async def create_session(request: SessionCreateRequest):
        """Create a new processing session."""
        return await session_endpoints.create_session(request)

    @sessions_router.get("/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str):
        """Get a specific session by ID."""
        return await session_endpoints.get_session(session_id)

    @sessions_router.put("/{session_id}", response_model=SessionResponse)
    async def update_session(session_id: str, request: SessionUpdateRequest):
        """Update session status and metadata."""
        return await session_endpoints.update_session(session_id, request)

    @sessions_router.delete("/{session_id}")
    async def delete_session(session_id: str):
        """Cancel/delete a session."""
        return await session_endpoints.delete_session(session_id)

    return sessions_router

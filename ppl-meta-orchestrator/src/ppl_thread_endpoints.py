"""
PPL Meta Orchestrator - PPL Thread (Person Objects) Endpoints
Provides centralized PPL Thread workflow management and data retrieval.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from workflow_orchestrator import (
    CameraFaceDetectionWorkflowOrchestrator,
    ServiceClientManager,
    TraceabilityContext,
)

logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer()


def get_auth_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract and validate authentication token."""
    return credentials.credentials


# Create router for PPL Thread endpoints
ppl_thread_router = APIRouter(prefix="/person-objects", tags=["person-objects"])


class PPLThreadWorkflowRequest(BaseModel):
    """Request model for PPL Thread workflow."""

    media_id: str


class PPLThreadWorkflowResponse(BaseModel):
    """Response model for PPL Thread workflow."""

    success: bool
    media_id: str
    total_persons: int
    total_faces: int
    status: str
    message: str


class PPLThreadEndpoints:
    """PPL Thread workflow management endpoints."""

    def __init__(
        self,
        orchestrator: CameraFaceDetectionWorkflowOrchestrator,
        service_manager: ServiceClientManager,
    ):
        self.orchestrator = orchestrator
        self.service_manager = service_manager
        self._setup_routes()

    def _setup_routes(self):
        """Setup PPL Thread API routes."""

        @ppl_thread_router.post("/trigger", response_model=PPLThreadWorkflowResponse)
        async def trigger_ppl_thread_workflow(
            request: PPLThreadWorkflowRequest,
            auth_token: str = Depends(get_auth_token),
        ):
            """
            🎯 Trigger PPL Thread workflow for media with face data.

            This is called automatically by the Orchestrator after face detection
            completes, but can also be called manually via API.
            """
            media_id = request.media_id

            logger.info(
                f"🎯 ORCHESTRATOR API: Triggering PPL Thread workflow for media {media_id}"
            )

            try:
                # Create traceability context
                trace_ctx = self.service_manager.create_trace_context(
                    workflow_id=f"ppl-thread-{media_id}",
                    operation="manual_ppl_thread_trigger",
                    metadata={"media_id": media_id, "source": "api"},
                )

                # Trigger PPL Thread workflow via Vision Service
                ppl_response = (
                    await self.service_manager.vision.trigger_person_objects_workflow(
                        trace_ctx=trace_ctx,
                        media_id=media_id,
                        auth_token=auth_token,
                    )
                )

                if ppl_response.success:
                    response_data = ppl_response.data
                    total_persons = response_data.get("total_persons", 0)
                    total_faces = response_data.get("total_faces", 0)
                    status = response_data.get("status", "completed")

                    logger.info(
                        f"🎯 ORCHESTRATOR API: ✅ PPL Thread workflow completed for media {media_id}: {total_persons} persons"
                    )

                    return PPLThreadWorkflowResponse(
                        success=True,
                        media_id=media_id,
                        total_persons=total_persons,
                        total_faces=total_faces,
                        status=status,
                        message=f"PPL Thread workflow completed successfully",
                    )
                else:
                    error_msg = ppl_response.error_message or "Unknown error"
                    logger.error(
                        f"🎯 ORCHESTRATOR API: ❌ PPL Thread workflow failed for media {media_id}: {error_msg}"
                    )

                    return PPLThreadWorkflowResponse(
                        success=False,
                        media_id=media_id,
                        total_persons=0,
                        total_faces=0,
                        status="failed",
                        message=f"PPL Thread workflow failed: {error_msg}",
                    )

            except Exception as e:
                logger.error(
                    f"🎯 ORCHESTRATOR API: Exception triggering PPL Thread for media {media_id}: {e}"
                )

                return PPLThreadWorkflowResponse(
                    success=False,
                    media_id=media_id,
                    total_persons=0,
                    total_faces=0,
                    status="error",
                    message=f"Exception: {str(e)}",
                )

        @ppl_thread_router.get("/{media_id}", response_model=PPLThreadWorkflowResponse)
        async def get_person_objects_for_media(
            media_id: str,
            auth_token: str = Depends(get_auth_token),
        ):
            """
            🎯 Get person objects data for media UUID.

            This is the simple endpoint that Flutter uses to retrieve person objects
            data. It proxies the request to the Vision Service.
            """
            logger.info(
                f"🎯 ORCHESTRATOR API: Getting person objects for media {media_id}"
            )

            try:
                # Create traceability context
                trace_ctx = self.service_manager.create_trace_context(
                    workflow_id=f"ppl-get-{media_id}",
                    operation="get_person_objects",
                    metadata={"media_id": media_id, "source": "api"},
                )

                # Get person objects data from Vision Service
                response = (
                    await self.service_manager.vision.get_person_objects_for_media(
                        trace_ctx=trace_ctx,
                        media_id=media_id,
                        auth_token=auth_token,
                    )
                )

                if response.success:
                    response_data = response.data
                    total_persons = response_data.get("total_persons", 0)
                    total_faces = response_data.get("total_faces", 0)
                    status = response_data.get("status", "completed")

                    logger.info(
                        f"🎯 ORCHESTRATOR API: ✅ Retrieved {total_persons} persons for media {media_id}"
                    )

                    return PPLThreadWorkflowResponse(
                        success=True,
                        media_id=media_id,
                        total_persons=total_persons,
                        total_faces=total_faces,
                        status=status,
                        message="Person objects data retrieved successfully",
                    )
                else:
                    error_msg = response.error_message or "Data not found"
                    logger.info(
                        f"🎯 ORCHESTRATOR API: ⚠️ No person data for media {media_id}: {error_msg}"
                    )

                    return PPLThreadWorkflowResponse(
                        success=True,  # Success but no data
                        media_id=media_id,
                        total_persons=0,
                        total_faces=0,
                        status="no_data",
                        message="No person objects data available yet",
                    )

            except Exception as e:
                logger.error(
                    f"🎯 ORCHESTRATOR API: Exception getting data for media {media_id}: {e}"
                )

                return PPLThreadWorkflowResponse(
                    success=False,
                    media_id=media_id,
                    total_persons=0,
                    total_faces=0,
                    status="error",
                    message=f"Exception: {str(e)}",
                )


def create_ppl_thread_endpoints(
    orchestrator: CameraFaceDetectionWorkflowOrchestrator,
    service_manager: ServiceClientManager,
) -> APIRouter:
    """Create and return PPL Thread API router."""
    endpoints = PPLThreadEndpoints(orchestrator, service_manager)
    return ppl_thread_router

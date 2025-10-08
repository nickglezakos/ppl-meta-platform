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
            🎯 Get person objects data for media UUID using Enhanced Logic V2.

            This simplified endpoint:
            1. Uses Enhanced Logic V2 to get face detection data
            2. Applies grouping logic to calculate person objects
            3. Returns person count and face count
            """
            logger.info(
                f"🎯 PPL THREAD: Getting person objects for media {media_id} via Enhanced Logic V2"
            )

            try:
                # Import the session manager to use Enhanced Logic V2 directly
                from face_detection_endpoints import FaceDetectionSessionManager

                session_manager = FaceDetectionSessionManager()

                # Step 1: Use Enhanced Logic V2 to get face detection data
                logger.info("🔄 Step 1: Calling Enhanced Logic V2 for face detection")
                face_result = await session_manager.enhanced_logic_v2_session_based(
                    media_id=media_id,
                    auth_token=auth_token,
                    frame_interval=10,  # Use default frame sampling
                )

                if not face_result.get("success", False):
                    error_msg = face_result.get("error", "Enhanced Logic V2 failed")
                    logger.error(f"❌ Enhanced Logic V2 failed: {error_msg}")

                    return PPLThreadWorkflowResponse(
                        success=False,
                        media_id=media_id,
                        total_persons=0,
                        total_faces=0,
                        status="error",
                        message=f"Enhanced Logic V2 failed: {error_msg}",
                    )

                # Step 2: Extract face data and apply grouping logic
                total_faces = face_result.get("total_faces", 0)
                faces_data = face_result.get("faces", [])

                logger.info(f"✅ Enhanced Logic V2 returned {total_faces} faces")

                # Step 3: Apply simple grouping logic for person objects
                # For now, use a simple heuristic: assume faces are grouped by proximity
                # This is a placeholder - real PPL Thread logic would be more sophisticated
                if total_faces == 0:
                    total_persons = 0
                elif total_faces <= 5:
                    total_persons = 1  # Small group = likely 1 person
                elif total_faces <= 20:
                    total_persons = max(1, total_faces // 3)  # Medium group
                else:
                    total_persons = max(1, total_faces // 5)  # Large group

                logger.info(
                    f"🎯 PPL THREAD: ✅ Processed {total_faces} faces → {total_persons} persons"
                )

                return PPLThreadWorkflowResponse(
                    success=True,
                    media_id=media_id,
                    total_persons=total_persons,
                    total_faces=total_faces,
                    status="completed",
                    message=f"Enhanced Logic V2 + grouping: {total_faces} faces → {total_persons} persons",
                )

            except Exception as e:
                logger.error(f"❌ PPL Thread error for media {media_id}: {e}")
                return PPLThreadWorkflowResponse(
                    success=False,
                    media_id=media_id,
                    total_persons=0,
                    total_faces=0,
                    status="error",
                    message=f"PPL Thread error: {str(e)}",
                )


def create_ppl_thread_endpoints(
    orchestrator: CameraFaceDetectionWorkflowOrchestrator,
    service_manager: ServiceClientManager,
) -> APIRouter:
    """Create and return PPL Thread API router."""
    endpoints = PPLThreadEndpoints(orchestrator, service_manager)
    return ppl_thread_router

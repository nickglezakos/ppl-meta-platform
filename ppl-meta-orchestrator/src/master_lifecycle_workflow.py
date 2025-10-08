"""
PPL Meta Orchestrator - Master Lifecycle Workflow Controller
Implements the Persons Lifecycle Master Workflow for Phase 1 completion.

This controller manages the complete lifecycle of person detection workflows,
coordinating between face detection, person objects creation, person routes
analytics, and future advanced features through the vmeta service.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorkflowExecutionRequest(BaseModel):
    """Request model for starting a master workflow execution."""

    source_id: str  # Media ID or camera ID
    source_identifier: str  # Source name/identifier
    source_type: str = "media"  # media, camera, stream
    workflow_types: List[str] = ["face_detection", "person_objects"]
    execution_trigger: str = "manual"
    config: Optional[Dict] = None


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    session_uuid: str
    status: str  # queued, processing, completed, failed
    progress: float  # 0.0 to 100.0
    current_stage: str
    created_at: str
    completed_at: Optional[str] = None
    results: Optional[Dict] = None
    error_message: Optional[str] = None


class MasterLifecycleWorkflowController:
    """
    Master controller for all PPL Meta person detection workflows.

    Phase 1 Features:
    - Session-based workflow execution (no duplicate prevention)
    - Master workflow lifecycle management
    - Enhanced face detection with distance calculation
    - Person objects creation coordination
    - Future: Person routes analytics and vmeta integration
    """

    def __init__(
        self, vision_service_client, vmeta_service_client=None, config: dict = None
    ):
        """
        Initialize master workflow controller.

        Args:
            vision_service_client: Client for Vision Service API
            vmeta_service_client: Client for vmeta Service API (optional)
            config: Configuration dictionary
        """
        self.vision_service = vision_service_client
        self.vmeta_service = vmeta_service_client
        self.config = config or {}

        # Track active workflow sessions
        self.active_sessions: Dict[str, Dict] = {}

        logger.info("Initialized MasterLifecycleWorkflowController")

    async def start_workflow_execution(
        self,
        request: WorkflowExecutionRequest,
        background_tasks: BackgroundTasks,
        auth_token: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """
        Start a new master workflow execution.

        Creates a session UUID and coordinates all sub-workflows based on the
        request configuration. Returns immediately with session tracking info.

        Args:
            request: Workflow execution parameters
            background_tasks: FastAPI background tasks
            auth_token: Authentication token for downstream services

        Returns:
            Workflow status response with session UUID for tracking
        """
        session_uuid = str(uuid.uuid4())

        logger.info(
            f"Starting master workflow execution - Session: {session_uuid}, "
            f"Source: {request.source_id}, Types: {request.workflow_types}"
        )

        # Initialize session tracking
        self.active_sessions[session_uuid] = {
            "status": "queued",
            "progress": 0.0,
            "current_stage": "initialization",
            "created_at": datetime.now().isoformat(),
            "results": {},
        }

        # Start background workflow execution
        background_tasks.add_task(
            self._execute_workflows_background, session_uuid, request, auth_token
        )

        return WorkflowStatusResponse(
            session_uuid=session_uuid,
            status="queued",
            progress=0.0,
            current_stage="initialization",
            created_at=self.active_sessions[session_uuid]["created_at"],
        )

    async def get_workflow_status(self, session_uuid: str) -> WorkflowStatusResponse:
        """
        Get current status of a workflow execution.

        Args:
            session_uuid: Session UUID to check

        Returns:
            Current workflow status
        """
        if session_uuid not in self.active_sessions:
            raise HTTPException(status_code=404, detail="Workflow session not found")

        session = self.active_sessions[session_uuid]

        return WorkflowStatusResponse(
            session_uuid=session_uuid,
            status=session["status"],
            progress=session["progress"],
            current_stage=session["current_stage"],
            created_at=session["created_at"],
            completed_at=session.get("completed_at"),
            results=session.get("results"),
            error_message=session.get("error_message"),
        )

    async def _execute_workflows_background(
        self,
        session_uuid: str,
        request: WorkflowExecutionRequest,
        auth_token: Optional[str] = None,
    ):
        """
        Execute workflows in background with session tracking.

        Args:
            session_uuid: Session UUID for tracking
            request: Workflow execution request
            auth_token: Authentication token for downstream services
        """
        try:
            # Update session status
            await self._update_workflow_status(
                session_uuid, "processing", "workflow_execution", 10.0
            )

            # Execute each workflow type
            results = {}
            total_workflows = len(request.workflow_types)

            for i, workflow_type in enumerate(request.workflow_types):
                progress = 10.0 + (i / total_workflows) * 80.0  # 10% to 90% range

                if workflow_type == "face_detection":
                    result = await self._execute_face_detection_workflow(
                        session_uuid, request, progress, auth_token
                    )
                    results["face_detection"] = result

                elif workflow_type == "person_objects":
                    result = await self._execute_person_objects_workflow(
                        session_uuid, request, progress
                    )
                    results["person_objects"] = result

                elif workflow_type == "person_routes":
                    result = await self._execute_person_routes_workflow(
                        session_uuid, request, progress
                    )
                    results["person_routes"] = result

                elif workflow_type == "vector_analytics":
                    result = await self._execute_vector_analytics_workflow(
                        session_uuid, request, progress
                    )
                    results["vector_analytics"] = result

                else:
                    logger.warning(f"Unknown workflow type: {workflow_type}")

            # Complete workflow
            await self._update_workflow_status(
                session_uuid, "completed", "finished", 100.0, results
            )

            logger.info(f"Master workflow {session_uuid} completed successfully")

        except Exception as e:
            error_msg = f"Master workflow failed: {str(e)}"
            logger.error(f"Master workflow {session_uuid} failed: {error_msg}")

            await self._update_workflow_status(
                session_uuid, "failed", "error", 0.0, None, error_msg
            )

    async def _execute_face_detection_workflow(
        self,
        session_uuid: str,
        request: WorkflowExecutionRequest,
        progress: float,
        auth_token: Optional[str] = None,
    ) -> Dict:
        """Execute enhanced face detection workflow with distance calculation."""

        logger.info(f"Executing face detection workflow - Session: {session_uuid}")

        await self._update_workflow_status(
            session_uuid, "processing", "face_detection", progress
        )

        # Configure face detection with distance calculation
        detection_config = {
            "method": "two_stage",  # Use proven working detection method
            "confidence_threshold": 0.5,
            "enable_distance_calculation": True,
            "store_session": True,
        }

        # Override with user-provided config if available
        if request.config:
            detection_config.update(request.config)

        # ENHANCED: Use bulk processing for immediate results instead of just session creation
        if detection_config.get("force_process", False):
            logger.info(
                f"Using bulk processing with force_process for session: {session_uuid}"
            )

            # Call Vision Service bulk processing API directly
            result = await self.vision_service.bulk_process_media(
                media_id=request.source_id,
                detection_method=detection_config.get("method", "two_stage"),
                force_process=True,
                frame_interval=detection_config.get("frame_interval", 1),
                max_frames=detection_config.get("max_frames", None),
                config=detection_config,
                auth_token=auth_token,
            )

            # FALLBACK: If bulk processing fails (e.g., media not registered),
            # try session-based approach which can retrieve existing data
            if not result.success:
                logger.warning(
                    f"Bulk processing failed for session {session_uuid}, "
                    f"falling back to session-based approach: "
                    f"{result.error_message}"
                )
                result = await self.vision_service.start_session_based_face_detection(  # noqa: E501
                    session_uuid=session_uuid,
                    media_id=request.source_id,
                    source_identifier=request.source_identifier,
                    source_type=request.source_type,
                    execution_trigger=request.execution_trigger,
                    config=detection_config,
                )
        else:
            # CRITICAL FIX: Use bulk processing with force_process=false for duplication scenario
            # This ensures we get the same structure as Vision Service direct calls
            logger.info(
                f"Using bulk processing with force_process=false for duplication scenario: {session_uuid}"
            )

            # Call Vision Service bulk processing API for duplication method
            result = await self.vision_service.bulk_process_media(
                media_id=request.source_id,
                detection_method=detection_config.get("method", "two_stage"),
                force_process=False,  # This triggers duplication method
                frame_interval=detection_config.get("frame_interval", 1),
                max_frames=detection_config.get("max_frames", None),
                config=detection_config,
                auth_token=auth_token,
            )

            # FALLBACK ONLY: If bulk processing fails, try session-based approach
            if not result.success:
                logger.warning(
                    f"Bulk processing (duplication) failed for session {session_uuid}, "
                    f"falling back to session-based approach: {result.error_message}"
                )
                result = await self.vision_service.start_session_based_face_detection(
                    session_uuid=session_uuid,
                    media_id=request.source_id,
                    source_identifier=request.source_identifier,
                    source_type=request.source_type,
                    execution_trigger=request.execution_trigger,
                    config=detection_config,
                )

        # Parse faces count from Vision Service response structure
        # Vision Service returns "total_faces" (bulk) or "faces_detected"
        faces_count = 0
        if result.data:
            # Try Vision Service bulk processing response format first
            faces_count = result.data.get("total_faces", 0)
            if faces_count == 0:
                # Fall back to session-based response format
                faces_count = result.data.get("faces_detected", 0)

        # FINAL FALLBACK: If both methods failed OR returned 0 faces,
        # try to retrieve existing face data
        if faces_count == 0:
            logger.warning(
                f"No faces detected for session {session_uuid}, "
                f"attempting to retrieve existing face data directly"
            )
            try:
                # Try to get existing faces via direct database query
                existing_faces_result = (
                    await self.vision_service.get_existing_faces(  # noqa: E501
                        media_id=request.source_id,
                        auth_token=auth_token,
                    )
                )
                if existing_faces_result.success and existing_faces_result.data:
                    existing_faces_count = existing_faces_result.data.get(
                        "total_faces", 0
                    )
                    if existing_faces_count > 0:
                        logger.info(
                            f"Retrieved {existing_faces_count} existing faces "
                            f"for session {session_uuid}"
                        )
                        faces_count = existing_faces_count
                        # Update result with existing data
                        result = existing_faces_result
            except Exception as e:
                logger.warning(f"Failed to retrieve existing faces: {e}")

        method_type = "bulk" if detection_config.get("force_process") else "session"
        logger.info(
            f"Face detection completed - Session: {session_uuid}, "
            f"Faces: {faces_count}, Method: {method_type}"
        )

        # CRITICAL FIX: Return the complete Vision Service response structure
        # When duplication method succeeds, we must return the identical
        # structure that Vision Service provides, not just face counts
        return_data = {}

        if result.success and result.data:
            # Use the complete Vision Service response as-is
            return_data = result.data.copy()
            logger.info(
                f"Returning complete Vision Service response structure "
                f"with {faces_count} faces"
            )
        elif faces_count > 0:
            # Fallback: construct minimal structure if we have face count
            # but no complete response data
            return_data = {
                "faces_detected": faces_count,
                "total_faces": faces_count,
                "message": f"Face detection completed for media {request.source_id}",
                "processing_method": "fallback_retrieval",
            }
            logger.warning(
                f"Had to construct minimal response structure with {faces_count} faces"
            )
        else:
            # No faces found - return minimal empty structure
            return_data = {
                "faces_detected": 0,
                "total_faces": 0,
                "message": f"No faces found for media {request.source_id}",
                "processing_method": "no_faces_detected",
            }

        return return_data

    async def _execute_person_objects_workflow(
        self, session_uuid: str, request: WorkflowExecutionRequest, progress: float
    ) -> Dict:
        """Execute person objects creation workflow."""

        logger.info(f"Executing person objects workflow - Session: {session_uuid}")

        await self._update_workflow_status(
            session_uuid, "processing", "person_objects", progress
        )

        # Configure person objects workflow
        objects_config = {
            "tolerance_percent": 20.0,
            "enable_quality_analysis": True,
            "enable_age_detection": False,
        }

        # Call Vision Service person objects API
        result = await self.vision_service.start_person_objects_workflow(
            session_uuid=session_uuid, config=objects_config
        )

        person_count = result.data.get("person_count", 0) if result.data else 0
        logger.info(
            f"Person objects completed - Session: {session_uuid}, "
            f"Persons: {person_count}"
        )

        return result.data if result.success else {}

    async def _execute_person_routes_workflow(
        self, session_uuid: str, request: WorkflowExecutionRequest, progress: float
    ) -> Dict:
        """Execute person routes analytics workflow (Phase 2)."""

        logger.info(f"Executing person routes workflow - Session: {session_uuid}")

        await self._update_workflow_status(
            session_uuid, "processing", "person_routes", progress
        )

        # Future implementation: Generate person routes from face detections
        # For now, return placeholder
        result = {
            "routes_created": 0,
            "spatial_analysis": {"coverage_area": 0.0, "movement_patterns": []},
        }

        logger.info(
            f"Person routes completed - Session: {session_uuid}, "
            f"Routes: {result.get('routes_created', 0)}"
        )

        return result

    async def _execute_vector_analytics_workflow(
        self, session_uuid: str, request: WorkflowExecutionRequest, progress: float
    ) -> Dict:
        """Execute vector analytics workflow via vmeta service (Phase 3)."""

        logger.info(f"Executing vector analytics workflow - Session: {session_uuid}")

        await self._update_workflow_status(
            session_uuid, "processing", "vector_analytics", progress
        )

        if not self.vmeta_service:
            logger.warning("vmeta service not available, skipping vector analytics")
            return {
                "vector_analytics": "skipped",
                "reason": "vmeta_service_unavailable",
            }

        # Call vmeta service for advanced analytics
        result = await self.vmeta_service.analyze_person_objects_for_session(
            session_uuid=session_uuid
        )

        logger.info(f"Vector analytics completed - Session: {session_uuid}")

        return result

    async def _update_workflow_status(
        self,
        session_uuid: str,
        status: str,
        current_stage: str,
        progress: float,
        results: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ):
        """Update workflow session status."""

        if session_uuid in self.active_sessions:
            self.active_sessions[session_uuid].update(
                {"status": status, "current_stage": current_stage, "progress": progress}
            )

            if results:
                self.active_sessions[session_uuid]["results"] = results

            if error_message:
                self.active_sessions[session_uuid]["error_message"] = error_message

            if status in ["completed", "failed"]:
                completion_time = datetime.now().isoformat()
                self.active_sessions[session_uuid]["completed_at"] = completion_time

            logger.debug(
                f"Updated workflow {session_uuid}: {status} - {current_stage} ({progress}%)"
            )

    def cleanup_completed_sessions(self, max_age_hours: int = 24):
        """Clean up old completed workflow sessions."""

        current_time = datetime.now()
        sessions_to_remove = []

        for session_uuid, session_data in self.active_sessions.items():
            if session_data["status"] in ["completed", "failed"] and session_data.get(
                "completed_at"
            ):
                age_hours = (
                    current_time - session_data["completed_at"]
                ).total_seconds() / 3600
                if age_hours > max_age_hours:
                    sessions_to_remove.append(session_uuid)

        for session_uuid in sessions_to_remove:
            del self.active_sessions[session_uuid]
            logger.info(f"Cleaned up old workflow session: {session_uuid}")

        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old workflow sessions")


# Global master workflow controller instance
master_workflow_controller: Optional[MasterLifecycleWorkflowController] = None


def initialize_master_workflow_controller(
    vision_service_client, vmeta_service_client=None, config: dict = None
) -> MasterLifecycleWorkflowController:
    """Initialize the global master workflow controller instance."""
    global master_workflow_controller

    master_workflow_controller = MasterLifecycleWorkflowController(
        vision_service_client, vmeta_service_client, config
    )

    logger.info("Global master workflow controller initialized")
    return master_workflow_controller


def get_master_workflow_controller() -> MasterLifecycleWorkflowController:
    """Get the global master workflow controller instance."""
    if master_workflow_controller is None:
        raise RuntimeError("Master workflow controller not initialized")

    return master_workflow_controller

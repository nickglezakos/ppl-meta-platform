"""
PPL Meta Orchestrator - Master Lifecycle Workflow API Endpoints
API endpoints for the Persons Lifecycle Master Workflow.

These endpoints provide the main interface for coordinating person detection
workflows across the vision service and future vmeta service integration.
"""

import logging
from typing import Dict

import master_lifecycle_workflow
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from master_lifecycle_workflow import (
    MasterLifecycleWorkflowController,
    WorkflowExecutionRequest,
    WorkflowStatusResponse,
    get_master_workflow_controller,
)

logger = logging.getLogger(__name__)

# Create API router for master workflow endpoints
router = APIRouter(
    prefix="/api/v1/master-lifecycle", tags=["Master Lifecycle Workflow"]
)


@router.post("/workflows/start", response_model=WorkflowStatusResponse)
async def start_master_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    controller: MasterLifecycleWorkflowController = Depends(
        get_master_workflow_controller
    ),
    authorization: str = Header(None),
):
    """
    Start a new Persons Lifecycle Master Workflow execution.

    This endpoint coordinates all person detection sub-workflows including:
    - Face detection with distance calculation (Vision Service)
    - Person objects creation (Vision Service)
    - Person routes analytics (Future - Phase 2)
    - Vector analytics (Future - Phase 3 via vmeta Service)

    Args:
        request: Workflow execution parameters
        background_tasks: FastAPI background tasks for async execution
        controller: Master workflow controller dependency

    Returns:
        Workflow status response with session UUID for tracking progress
    """
    try:
        logger.info(
            f"API: Starting master workflow - Source: {request.source_id}, "
            f"Types: {request.workflow_types}"
        )

        # Extract auth token from authorization header
        auth_token = None
        if authorization and authorization.startswith("Bearer "):
            auth_token = authorization[7:]  # Remove "Bearer " prefix

        response = await controller.start_workflow_execution(
            request, background_tasks, auth_token
        )

        logger.info(f"API: Master workflow started - Session: {response.session_uuid}")
        return response

    except Exception as e:
        logger.error(f"API: Failed to start master workflow: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start master workflow: {str(e)}"
        )


@router.get("/workflows/{session_uuid}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    session_uuid: str,
    controller: MasterLifecycleWorkflowController = Depends(
        get_master_workflow_controller
    ),
):
    """
    Get current status of a master workflow execution.

    Returns real-time progress information including current stage,
    completion percentage, and any results or error messages.

    Args:
        session_uuid: Workflow session UUID to check
        controller: Master workflow controller dependency

    Returns:
        Current workflow status and progress information
    """
    try:
        logger.info(f"API: Getting workflow status for session: {session_uuid}")

        response = await controller.get_workflow_status(session_uuid)

        logger.debug(
            f"API: Workflow status - Session: {session_uuid}, "
            f"Status: {response.status}, Progress: {response.progress}%"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for not found)
        raise
    except Exception as e:
        logger.error(f"API: Failed to get workflow status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get("/workflows/{session_uuid}/results")
async def get_workflow_results(
    session_uuid: str,
    controller: MasterLifecycleWorkflowController = Depends(
        get_master_workflow_controller
    ),
):
    """
    Get detailed results of a completed workflow execution.

    Returns comprehensive results from all completed sub-workflows including
    face detection statistics, person objects data, routes analytics, etc.

    Args:
        session_uuid: Workflow session UUID to retrieve results for
        controller: Master workflow controller dependency

    Returns:
        Detailed workflow execution results
    """
    try:
        logger.info(f"API: Getting workflow results for session: {session_uuid}")

        status_response = await controller.get_workflow_status(session_uuid)

        if status_response.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Workflow not completed yet. Current status: {status_response.status}",
            )

        return {
            "session_uuid": session_uuid,
            "status": status_response.status,
            "results": status_response.results,
            "completed_at": status_response.completed_at,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"API: Failed to get workflow results: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow results: {str(e)}"
        )


@router.delete("/workflows/{session_uuid}")
async def cancel_workflow(
    session_uuid: str,
    controller: MasterLifecycleWorkflowController = Depends(
        get_master_workflow_controller
    ),
):
    """
    Cancel a running workflow execution.

    Attempts to stop a workflow that is currently in progress.
    Note: May not be able to cancel workflows that are already
    executing within sub-services.

    Args:
        session_uuid: Workflow session UUID to cancel
        controller: Master workflow controller dependency

    Returns:
        Cancellation status
    """
    try:
        logger.info(f"API: Cancelling workflow for session: {session_uuid}")

        # For now, just mark as cancelled in our tracking
        # Future: Implement proper cancellation logic
        if session_uuid in controller.active_sessions:
            await controller._update_workflow_status(
                session_uuid, "cancelled", "cancelled", 0.0, None, "Cancelled by user"
            )

            logger.info(f"API: Workflow cancelled - Session: {session_uuid}")
            return {"session_uuid": session_uuid, "status": "cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Workflow session not found")

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"API: Failed to cancel workflow: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel workflow: {str(e)}"
        )


@router.get("/workflows/active")
async def list_active_workflows(
    controller: MasterLifecycleWorkflowController = Depends(
        get_master_workflow_controller
    ),
):
    """
    List all currently active workflow sessions.

    Returns summary information for all workflows that are currently
    queued, processing, or recently completed.

    Args:
        controller: Master workflow controller dependency

    Returns:
        List of active workflow sessions with basic status info
    """
    try:
        logger.info("API: Listing active workflows")

        active_workflows = []

        for session_uuid, session_data in controller.active_sessions.items():
            active_workflows.append(
                {
                    "session_uuid": session_uuid,
                    "status": session_data["status"],
                    "progress": session_data["progress"],
                    "current_stage": session_data["current_stage"],
                    "created_at": session_data["created_at"].isoformat(),
                    "source_id": session_data["request"].source_id,
                    "workflow_types": session_data["request"].workflow_types,
                }
            )

        logger.info(f"API: Found {len(active_workflows)} active workflows")

        return {
            "active_workflows": active_workflows,
            "total_count": len(active_workflows),
        }

    except Exception as e:
        logger.error(f"API: Failed to list active workflows: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list active workflows: {str(e)}"
        )


@router.post("/workflows/cleanup")
async def cleanup_old_workflows(
    max_age_hours: int = 24,
    controller: MasterLifecycleWorkflowController = Depends(
        get_master_workflow_controller
    ),
):
    """
    Clean up old completed workflow sessions.

    Removes workflow session data for executions that completed
    more than the specified number of hours ago.

    Args:
        max_age_hours: Maximum age in hours for keeping completed workflows
        controller: Master workflow controller dependency

    Returns:
        Cleanup summary
    """
    try:
        logger.info(f"API: Cleaning up workflows older than {max_age_hours} hours")

        sessions_before = len(controller.active_sessions)
        controller.cleanup_completed_sessions(max_age_hours)
        sessions_after = len(controller.active_sessions)

        cleaned_count = sessions_before - sessions_after

        logger.info(f"API: Cleaned up {cleaned_count} old workflow sessions")

        return {
            "cleaned_sessions": cleaned_count,
            "remaining_sessions": sessions_after,
            "max_age_hours": max_age_hours,
        }

    except Exception as e:
        logger.error(f"API: Failed to cleanup workflows: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup workflows: {str(e)}"
        )


# Health check endpoint for master workflow service
@router.get("/health")
async def health_check():
    """
    Health check endpoint for master lifecycle workflow service.

    Returns:
        Service health status
    """
    return {
        "service": "master-lifecycle-workflow",
        "status": "healthy",
        "version": "1.0.0",
        "capabilities": [
            "master_workflow_orchestration",
            "session_based_execution",
            "face_detection_coordination",
            "person_objects_coordination",
            "future_vmeta_integration",
        ],
    }

"""
PPL Meta Vision Service - Person Objects API
FastAPI integration for PPL Thread (Person Objects) workflow functionality.

This module provides REST API endpoints that integrate with the PPL Thread
workflow controller to offer person objects functionality through HTTP API.

Key Features:
- Start person objects workflows from existing face detection sessions
- Retrieve person objects data in PPL Meta Mini compatible format
- Monitor workflow status and get comprehensive statistics
- Full integration with Phase 1 database schema and Phase 2 algorithms
- Error handling and validation for production use

API Endpoints:
- POST /api/v1/person-objects/workflows/start - Start new workflow
- GET /api/v1/person-objects/sessions/{session_uuid} - Get person objects
- GET /api/v1/person-objects/workflows/{workflow_id}/status - Workflow status
- GET /api/v1/person-objects/sessions/{session_uuid}/statistics - Statistics
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, validator

# Add the src directory to path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    # Import the database module with explicit path
    database_path = os.path.join(src_dir, "database.py")
    import importlib.util

    spec = importlib.util.spec_from_file_location("database", database_path)
    database_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database_module)

    def get_vision_database():
        return database_module.vision_db

except Exception as e:
    print(f"CRITICAL: Failed to import database module: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")

    # Fallback to mock for testing
    def get_vision_database():
        class MockDB:
            pass

        return MockDB()


# Workflow controller integration
from .ppl_thread_workflow import PPLThreadWorkflowController

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/person-objects", tags=["person-objects"])


# Pydantic models for request/response validation


class PersonObjectsWorkflowRequest(BaseModel):
    """Request model for starting person objects workflow."""

    session_uuid: str = Field(
        ...,
        description="Face detection session UUID to process",
        min_length=36,
        max_length=36,
    )
    tolerance_percent: Optional[float] = Field(
        default=None,
        description="Position matching tolerance percentage (5.0-50.0). If not provided, fetches from orchestrator settings.",
        ge=5.0,
        le=50.0,
    )
    enable_quality_analysis: bool = Field(
        default=True, description="Enable best face quality analysis"
    )
    enable_age_detection: bool = Field(
        default=True, description="Enable age estimation (future enhancement)"
    )
    workflow_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional workflow metadata"
    )

    @validator("session_uuid")
    def validate_session_uuid(cls, v):
        """Validate session UUID format."""
        if not v or len(v) != 36:
            raise ValueError("session_uuid must be a valid UUID string")
        return v

    class Config:
        schema_extra = {
            "example": {
                "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
                "tolerance_percent": None,
                "enable_quality_analysis": True,
                "enable_age_detection": True,
                "workflow_metadata": {
                    "description": "Security footage person analysis (uses orchestrator setting)",
                    "camera_location": "Main entrance",
                },
            }
        }


class PersonObjectsFromFacesRequest(BaseModel):
    """Request model for starting person objects workflow from in-memory faces."""

    session_uuid: str = Field(
        ...,
        description="Face detection session UUID to associate with",
        min_length=36,
        max_length=36,
    )
    face_detections: List[Dict[str, Any]] = Field(
        ...,
        description="Face detection data from Enhanced Logic V2",
        min_items=1,
    )
    tolerance_percent: Optional[float] = Field(
        default=None,
        description="Position matching tolerance percentage (5.0-50.0). If not provided, fetches from orchestrator settings.",
        ge=5.0,
        le=50.0,
    )
    enable_quality_analysis: bool = Field(
        default=True, description="Enable best face quality analysis"
    )
    enable_age_detection: bool = Field(
        default=True, description="Enable age estimation (future enhancement)"
    )
    workflow_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional workflow metadata"
    )

    @validator("session_uuid")
    def validate_session_uuid(cls, v):
        """Validate session UUID format."""
        if not v or len(v) != 36:
            raise ValueError("session_uuid must be a valid UUID string")
        return v

    @validator("face_detections")
    def validate_face_detections(cls, v):
        """Validate face detection data has required fields."""
        required_fields = ["id", "frame_number", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence"]
        for face in v:
            for field in required_fields:
                if field not in face:
                    raise ValueError(f"Face detection missing required field: {field}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
                "face_detections": [
                    {
                        "id": 12345,
                        "frame_number": 1,
                        "bbox_x1": 100,
                        "bbox_y1": 200,
                        "bbox_x2": 300,
                        "bbox_y2": 400,
                        "confidence": 0.95,
                        "method": "enhanced_logic_v2",
                    }
                ],
                "tolerance_percent": 20.0,
                "enable_quality_analysis": True,
                "enable_age_detection": True,
                "workflow_metadata": {
                    "source": "enhanced_logic_v2",
                    "orchestrator_triggered": True,
                },
            }
        }


class GroupTrackingItem(BaseModel):
    """Individual group tracking item in PPL Mini format."""

    Merged_Group_ID: str
    Original_Group_IDs: List[str]
    Face_Count: int
    Average_Position: Dict[str, float]
    Y_Coordinate_Based: bool
    Tracking_Based: bool
    Tolerance_Percent: float
    Merge_History: List[Any]


class SummaryStatistics(BaseModel):
    """Summary statistics in PPL Mini format."""

    total_groups: int
    original_unique_faces: int
    merged_groups_count: int
    total_detections: int
    frames_processed: Optional[int] = None
    grouping_algorithm: str
    tolerance_percent: float
    tracked_faces: Optional[int] = None
    new_faces: Optional[int] = None
    merge_iterations: int = 0


class BestQualityFace(BaseModel):
    """Best quality face data in PPL Mini format."""

    face_id: str
    frame_number: Optional[int] = 0
    quality_score: float = 0.0
    bbox: Optional[List[int]] = [0, 0, 0, 0]
    age_detection: Optional[Dict[str, Any]] = {"estimated_age": "Unknown"}
    distance: float = 0.0


class ClassifiedFace(BaseModel):
    """Classified face mapping in PPL Mini format."""

    face_id: str
    person_id: str
    match_type: str
    match_distance: float
    frame_number: int
    position: Dict[str, float]


class PersonObjectsSummary(BaseModel):
    """Simplified response for person objects summary - Flutter compatible."""

    success: bool
    media_id: str
    total_persons: int
    total_faces: int
    status: str
    message: str = ""


class PersonObjectsWorkflowResponse(BaseModel):
    """Response model for person objects workflow - PPL Mini compatible."""

    workflow_id: str
    session_uuid: str
    success: bool
    original_groups: int
    merged_groups: int
    group_tracking: List[GroupTrackingItem]
    summary: SummaryStatistics
    statistics: SummaryStatistics  # Duplicate for compatibility
    best_quality_faces: Dict[str, BestQualityFace]
    classified_faces: List[ClassifiedFace]
    person_objects: List[Dict[str, Any]]  # ← NEW: Full person objects for in-memory processing
    processing_timestamp: str
    workflow_type: str

    class Config:
        schema_extra = {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
                "success": True,
                "original_groups": 15,
                "merged_groups": 8,
                "group_tracking": [
                    {
                        "Merged_Group_ID": "person_1",
                        "Original_Group_IDs": ["face_1", "face_3", "face_7"],
                        "Face_Count": 3,
                        "Average_Position": {"x": 245.5, "y": 156.2},
                        "Y_Coordinate_Based": False,
                        "Tracking_Based": True,
                        "Tolerance_Percent": 20.0,
                        "Merge_History": [],
                    }
                ],
                "summary": {
                    "total_groups": 8,
                    "original_unique_faces": 15,
                    "merged_groups_count": 8,
                    "total_detections": 15,
                    "frames_processed": 120,
                    "grouping_algorithm": "percentage_based_tracking",
                    "tolerance_percent": 20.0,
                    "tracked_faces": 12,
                    "new_faces": 3,
                },
            }
        }


class WorkflowStatusResponse(BaseModel):
    """Workflow status response model."""

    workflow_id: str
    session_uuid: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    person_count: int
    face_count: int
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class SessionStatisticsResponse(BaseModel):
    """Session statistics response model."""

    session_uuid: str
    total_face_detections: int
    total_person_objects: int
    grouping_efficiency: float
    average_faces_per_person: float
    max_quality_score: float
    avg_quality_score: float
    has_quality_analysis: bool
    has_person_objects: bool


# API endpoint implementations


@router.post("/workflows/start", response_model=PersonObjectsWorkflowResponse)
async def start_person_objects_workflow(
    request: PersonObjectsWorkflowRequest, database=Depends(get_vision_database)
):
    """
    Start PPL Thread workflow to create person objects from existing face detections.

    This endpoint applies the same face grouping algorithm as PPL Meta Mini's
    FaceGroupingEngine to create person objects with identical data structure.

    The workflow process:
    1. Validates the face detection session exists
    2. Fetches all face detections for the session
    3. Applies percentage-based tracking algorithm (Phase 2)
    4. Performs quality analysis and best face selection
    5. Stores results in database (Phase 1 schema)
    6. Returns PPL Meta Mini compatible response format

    Args:
        request: Workflow configuration and parameters
        database: Vision Service database dependency

    Returns:
        Complete person objects data in PPL Meta Mini format

    Raises:
        HTTPException 400: Invalid request parameters
        HTTPException 404: Session not found
        HTTPException 500: Workflow processing error
    """
    logger.info(
        "API: Starting person objects workflow for session %s", request.session_uuid
    )

    try:
        # Initialize workflow controller
        controller = PPLThreadWorkflowController(database)

        # Execute workflow (now async method)
        result = await controller.start_person_objects_workflow(
            session_uuid=request.session_uuid,
            tolerance_percent=request.tolerance_percent,
            enable_quality_analysis=request.enable_quality_analysis,
            enable_age_detection=request.enable_age_detection,
            workflow_metadata=request.workflow_metadata,
        )

        logger.info(
            "API: Workflow completed successfully for session %s: %s",
            request.session_uuid,
            result["workflow_id"],
        )

        return PersonObjectsWorkflowResponse(**result)

    except ValueError as e:
        # Input validation or session not found
        logger.warning(
            "API: Bad request for session %s: %s", request.session_uuid, str(e)
        )
        raise HTTPException(
            status_code=400 if "not found" not in str(e).lower() else 404, detail=str(e)
        )
    except RuntimeError as e:
        # Workflow processing error
        logger.error(
            "API: Workflow failed for session %s: %s", request.session_uuid, str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Unexpected error
        logger.error(
            "API: Unexpected error for session %s: %s", request.session_uuid, str(e)
        )
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.post("/workflows/start-from-faces", response_model=PersonObjectsWorkflowResponse)
async def start_person_objects_workflow_from_faces(
    request: PersonObjectsFromFacesRequest, database=Depends(get_vision_database)
):
    """
    Start PPL Thread workflow from in-memory face detections (NO DATABASE LOOKUP).

    This endpoint is optimized for Enhanced Logic V2 integration - it accepts
    face detection data directly in memory, bypassing the database query step.
    This is faster and avoids timing issues with session commits.

    The workflow process:
    1. Validates the face detection session exists
    2. Uses provided face_detections array (NO database query)
    3. Applies percentage-based tracking algorithm (Phase 2)
    4. Performs quality analysis and best face selection
    5. Stores results in database (Phase 1 schema)
    6. Returns PPL Meta Mini compatible response format

    Args:
        request: Workflow configuration with face_detections array
        database: Vision Service database dependency

    Returns:
        Complete person objects data in PPL Meta Mini format

    Raises:
        HTTPException 400: Invalid request parameters or missing required fields
        HTTPException 404: Session not found
        HTTPException 500: Workflow processing error
    """
    logger.info(
        "API: Starting person objects workflow from %d in-memory faces for session %s",
        len(request.face_detections),
        request.session_uuid,
    )

    try:
        # Initialize workflow controller
        controller = PPLThreadWorkflowController(database)

        # Execute workflow with in-memory face data (now async method)
        result = await controller.start_person_objects_workflow_from_faces(
            face_detections=request.face_detections,
            session_uuid=request.session_uuid,
            tolerance_percent=request.tolerance_percent,
            enable_quality_analysis=request.enable_quality_analysis,
            enable_age_detection=request.enable_age_detection,
            workflow_metadata=request.workflow_metadata,
        )

        logger.info(
            "API: Workflow completed successfully for session %s: %s (%d persons from %d faces)",
            request.session_uuid,
            result["workflow_id"],
            result.get("merged_groups", 0),
            len(request.face_detections),
        )

        return PersonObjectsWorkflowResponse(**result)

    except ValueError as e:
        # Input validation or session not found
        logger.warning(
            "API: Bad request for session %s: %s", request.session_uuid, str(e)
        )
        raise HTTPException(
            status_code=400 if "not found" not in str(e).lower() else 404, detail=str(e)
        )
    except RuntimeError as e:
        # Workflow processing error
        logger.error(
            "API: Workflow failed for session %s: %s", request.session_uuid, str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Unexpected error
        logger.error(
            "API: Unexpected error for session %s: %s", request.session_uuid, str(e)
        )
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.post("/workflow/trigger", response_model=PersonObjectsWorkflowResponse)
async def trigger_person_objects_workflow_for_media(
    request: Dict[str, str], database=Depends(get_vision_database)
):
    """
    🎯 AUTOMATIC TRIGGER: Start PPL Thread workflow for media with face data.

    This endpoint is called automatically by the Orchestrator when face detection
    completes. It finds existing face data for the media and processes it into
    person objects, eliminating the need for Flutter to manage complex workflows.

    Flow:
    1. Face Detection completes -> Orchestrator calls this endpoint
    2. Vision Service finds face data for the media
    3. PPL Thread workflow processes faces into person objects
    4. Results stored in Vision database
    5. Flutter simply retrieves results via GET endpoint

    Args:
        request: {"media_id": "uuid"} - Media UUID with face data
        database: Vision Service database dependency

    Returns:
        Complete person objects data in PPL Meta Mini format
    """
    media_id = request.get("media_id")
    if not media_id:
        raise HTTPException(status_code=400, detail="media_id is required")

    logger.info(f"🎯 AUTO-TRIGGER: Starting PPL Thread workflow for media {media_id}")
    print(f"[VISION DEBUG] AUTO-TRIGGER called with media_id: {media_id}", flush=True)
    print(f"[VISION DEBUG] Full request: {request}", flush=True)

    try:
        # Initialize workflow controller
        controller = PPLThreadWorkflowController(database)

        # Find session for this media (existing faces)
        session_uuid = controller.find_session_uuid_by_media_uuid(media_id)

        if not session_uuid:
            # Legacy media without session - create session on-demand
            logger.info(
                f"🎯 AUTO-TRIGGER: No session found for legacy media {media_id}, creating session on-demand"
            )

            # Check if media has face detection data
            face_detections = database.get_face_detections(media_id)
            if not face_detections:
                raise HTTPException(
                    status_code=404,
                    detail=f"No face detection data found for media {media_id}",
                )

            # Create session for legacy media
            session_uuid = controller.create_session_for_legacy_media(
                media_id, len(face_detections)
            )

            if not session_uuid:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create session for legacy media {media_id}",
                )

        logger.info(
            f"🎯 AUTO-TRIGGER: Found session {session_uuid} for media {media_id}"
        )

        # Execute PPL Thread workflow with default settings
        result = await controller.start_person_objects_workflow(
            session_uuid=session_uuid,
            tolerance_percent=10.0,  # Default tolerance
            enable_quality_analysis=True,
            enable_age_detection=False,
            workflow_metadata={
                "auto_triggered": True,
                "media_id": media_id,
                "trigger_source": "orchestrator",
            },
        )

        logger.info(
            f"🎯 AUTO-TRIGGER: ✅ PPL Thread workflow completed for media {media_id}: {result.get('merged_groups', 0)} persons found"
        )
        
        print(f"[VISION DEBUG] Workflow result keys: {result.keys()}", flush=True)
        print(f"[VISION DEBUG] person_objects count: {len(result.get('person_objects', []))}", flush=True)
        print(f"[VISION DEBUG] person_objects sample: {result.get('person_objects', [])[:1]}", flush=True)

        return PersonObjectsWorkflowResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🎯 AUTO-TRIGGER: ❌ Failed to process media {media_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process person objects for media {media_id}: {str(e)}",
        )


@router.get("/{media_id}", response_model=PersonObjectsSummary)
async def get_person_objects_for_media(
    media_id: str = Path(..., description="Media UUID"),
    database=Depends(get_vision_database),
):
    """
    🎯 SIMPLE RETRIEVAL: Get person objects data for media UUID.

    This is the clean, simple endpoint that Flutter uses to retrieve
    person objects data. No complex workflow management needed.

    Args:
        media_id: Media UUID
        database: Vision Service database dependency

    Returns:
        Person objects summary or None if not processed yet
    """
    logger.info(f"🎯 RETRIEVAL: Getting person objects for media {media_id}")

    try:
        controller = PPLThreadWorkflowController(database)

        # Find session for this media
        session_uuid = controller.find_session_uuid_by_media_uuid(media_id)

        if not session_uuid:
            # No face detection data exists
            return PersonObjectsSummary(
                success=False,
                media_id=media_id,
                total_persons=0,
                total_faces=0,
                status="no_faces",
                message="No face detection data found",
            )

        # Try to get existing person objects
        existing_result = controller.get_person_objects_for_session(session_uuid)

        if existing_result and existing_result.get("total_persons", 0) > 0:
            logger.info(
                f"🎯 RETRIEVAL: ✅ Found {existing_result['total_persons']} persons for media {media_id}"
            )
            return PersonObjectsSummary(
                success=True,
                media_id=media_id,
                total_persons=existing_result["total_persons"],
                total_faces=existing_result["total_faces"],
                status="completed",
                message=f"Found {existing_result['total_persons']} persons",
            )
        else:
            # Face data exists but no person objects yet
            return PersonObjectsSummary(
                success=False,
                media_id=media_id,
                total_persons=0,
                total_faces=0,
                status="pending",
                message="Face detection complete, person processing pending",
            )

    except Exception as e:
        logger.error(f"🎯 RETRIEVAL: ❌ Error getting data for media {media_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve person objects: {str(e)}"
        )


@router.get("/sessions/{session_uuid}", response_model=PersonObjectsWorkflowResponse)
async def get_person_objects_for_session(
    session_uuid: str = Path(..., description="Face detection session UUID"),
    include_quality_analysis: bool = Query(
        default=True, description="Include quality analysis data"
    ),
    database=Depends(get_vision_database),
):
    """
    Retrieve existing person objects for a face detection session.

    Returns data in PPL Meta Mini compatible format. If no person objects
    exist for the session, returns appropriate error response.

    Args:
        session_uuid: Face detection session UUID
        include_quality_analysis: Include best face quality data
        database: Vision Service database dependency

    Returns:
        Person objects data in PPL Meta Mini format

    Raises:
        HTTPException 404: No person objects found for session
        HTTPException 500: Database retrieval error
    """
    logger.info("API: Retrieving person objects for session %s", session_uuid)

    try:
        # Initialize workflow controller
        controller = PPLThreadWorkflowController(database)

        # Retrieve person objects
        # Get person objects for session (synchronous method)
        result = controller.get_person_objects_for_session(
            session_uuid=session_uuid, include_quality_analysis=include_quality_analysis
        )

        if not result["success"]:
            logger.info("API: No person objects found for session %s", session_uuid)
            raise HTTPException(status_code=404, detail=result["message"])

        logger.info(
            "API: Retrieved person objects for session %s: %d persons",
            session_uuid,
            len(result.get("group_tracking", [])),
        )

        return PersonObjectsWorkflowResponse(**result)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "API: Failed to retrieve person objects for session %s: %s",
            session_uuid,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve person objects: {str(e)}"
        )


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str = Path(..., description="Workflow ID to check"),
    database=Depends(get_vision_database),
):
    """
    Get detailed status information for a person objects workflow.

    Provides real-time workflow status including progress, completion time,
    and error details if the workflow failed.

    Args:
        workflow_id: Workflow ID to check
        database: Vision Service database dependency

    Returns:
        Workflow status and execution details

    Raises:
        HTTPException 404: Workflow not found
        HTTPException 500: Database query error
    """
    logger.info("API: Getting workflow status for %s", workflow_id)

    try:
        # Initialize workflow controller
        controller = PPLThreadWorkflowController(database)

        # Get workflow status (synchronous method)
        status_data = controller.get_workflow_status(workflow_id)

        # Format response
        response = WorkflowStatusResponse(
            workflow_id=workflow_id,
            session_uuid=status_data["session_uuid"],
            status=status_data["status"],
            created_at=(
                status_data["started_at"].isoformat()
                if status_data["started_at"]
                else ""
            ),
            completed_at=(
                status_data["completed_at"].isoformat()
                if status_data.get("completed_at")
                else None
            ),
            person_count=status_data.get("output_person_count", 0),
            face_count=status_data.get("input_face_count", 0),
            error_message=status_data.get("error_message"),
            processing_time_seconds=None,  # Calculated from metadata if available
        )

        # Extract processing time from metadata if available
        if (
            status_data.get("metadata")
            and "processing_time_seconds" in status_data["metadata"]
        ):
            response.processing_time_seconds = status_data["metadata"][
                "processing_time_seconds"
            ]

        logger.info("API: Workflow %s status: %s", workflow_id, status_data["status"])

        return response

    except ValueError as e:
        logger.warning("API: Workflow not found: %s", workflow_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "API: Failed to get workflow status for %s: %s", workflow_id, str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get(
    "/sessions/{session_uuid}/statistics", response_model=SessionStatisticsResponse
)
async def get_session_person_statistics(
    session_uuid: str = Path(..., description="Face detection session UUID"),
    database=Depends(get_vision_database),
):
    """
    Get comprehensive person objects statistics for a session.

    Provides detailed analytics about person objects including grouping
    efficiency, quality analysis results, and face distribution metrics.

    Args:
        session_uuid: Face detection session UUID
        database: Vision Service database dependency

    Returns:
        Comprehensive statistical analysis of person objects

    Raises:
        HTTPException 404: Session has no person objects
        HTTPException 500: Database query error
    """
    logger.info("API: Getting statistics for session %s", session_uuid)

    try:
        # Initialize workflow controller
        controller = PPLThreadWorkflowController(database)

        # Get session statistics (synchronous method)
        stats = controller.get_session_statistics(session_uuid)

        if not stats.get("has_person_objects", False):
            logger.info(
                "API: No person objects statistics for session %s", session_uuid
            )
            raise HTTPException(
                status_code=404, detail="No person objects found for session"
            )

        response = SessionStatisticsResponse(
            session_uuid=session_uuid,
            total_face_detections=stats["total_faces"],
            total_person_objects=stats["total_persons"],
            grouping_efficiency=stats["grouping_efficiency"],
            average_faces_per_person=stats["avg_faces_per_person"],
            max_quality_score=stats["max_quality_score"],
            avg_quality_score=stats["avg_quality_score"],
            has_quality_analysis=stats["has_quality_analysis"],
            has_person_objects=True,
        )

        logger.info(
            "API: Statistics for session %s: %d persons from %d faces (%.1f%% efficiency)",
            session_uuid,
            stats["total_persons"],
            stats["total_faces"],
            stats["grouping_efficiency"],
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "API: Failed to get statistics for session %s: %s", session_uuid, str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def person_objects_health_check():
    """
    Health check endpoint for person objects functionality.

    Returns basic health status and version information.
    """
    return {
        "status": "healthy",
        "service": "ppl-thread-person-objects",
        "version": "1.0.0",
        "features": {
            "face_grouping": True,
            "quality_analysis": True,
            "ppl_mini_compatibility": True,
            "database_integration": True,
        },
        "timestamp": datetime.now().isoformat(),
    }


# Additional utility endpoints


@router.get("/sessions/{session_uuid}/summary")
async def get_session_summary(
    session_uuid: str = Path(..., description="Face detection session UUID"),
    database=Depends(get_vision_database),
):
    """
    Get a quick summary of person objects status for a session.

    Lightweight endpoint for checking if person objects exist and basic counts.
    """
    logger.info("API: Getting session summary for %s", session_uuid)

    try:
        controller = PPLThreadWorkflowController(database)
        stats = controller.get_session_statistics(session_uuid)

        return {
            "session_uuid": session_uuid,
            "has_person_objects": stats.get("has_person_objects", False),
            "person_count": stats.get("total_persons", 0),
            "face_count": stats.get("total_faces", 0),
            "grouping_efficiency": stats.get("grouping_efficiency", 0.0),
            "has_quality_analysis": stats.get("has_quality_analysis", False),
        }

    except Exception as e:
        logger.error(
            "API: Failed to get session summary for %s: %s", session_uuid, str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get session summary: {str(e)}"
        )


@router.delete("/sessions/{session_uuid}")
async def delete_person_objects_for_session(
    session_uuid: str = Path(..., description="Face detection session UUID"),
    database=Depends(get_vision_database),
):
    """
    Delete all person objects data for a session.

    This removes person objects, face mappings, and workflow records
    for the specified session. Use with caution - this cannot be undone.
    """
    logger.warning("API: Delete request for person objects in session %s", session_uuid)

    try:
        cursor = await database.connection.cursor()

        # Delete in proper order to maintain referential integrity
        delete_queries = [
            "DELETE FROM person_face_mappings WHERE person_id IN (SELECT person_id FROM person_objects WHERE session_uuid = %s)",
            "DELETE FROM person_objects WHERE session_uuid = %s",
            "DELETE FROM person_workflows WHERE session_uuid = %s",
        ]

        deleted_counts = []
        for query in delete_queries:
            await cursor.execute(query, (session_uuid,))
            deleted_counts.append(cursor.rowcount)

        await database.connection.commit()

        logger.info(
            "API: Deleted person objects for session %s: mappings=%d, objects=%d, workflows=%d",
            session_uuid,
            deleted_counts[0],
            deleted_counts[1],
            deleted_counts[2],
        )

        return {
            "success": True,
            "message": f"Deleted person objects for session {session_uuid}",
            "deleted_counts": {
                "face_mappings": deleted_counts[0],
                "person_objects": deleted_counts[1],
                "workflows": deleted_counts[2],
            },
        }

    except Exception as e:
        logger.error(
            "API: Failed to delete person objects for session %s: %s",
            session_uuid,
            str(e),
        )
        await database.connection.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete person objects: {str(e)}"
        )


@router.get("/media/{media_uuid}/session")
async def find_session_by_media_uuid(
    media_uuid: str = Path(..., description="Media UUID"),
    database=Depends(get_vision_database),
):
    """
    Find session UUID by media UUID for person objects processing.

    This endpoint provides dynamic session discovery functionality that allows
    the frontend to find the appropriate session UUID for a given media UUID
    to enable person objects processing and statistics.

    Args:
        media_uuid: The media UUID to find session for

    Returns:
        Session UUID and media UUID mapping information
    """
    try:
        logger.info("API: Finding session for media UUID %s", media_uuid)

        # Initialize the workflow controller
        controller = PPLThreadWorkflowController(database)

        # Use the dynamic discovery method
        session_uuid = controller.find_session_uuid_by_media_uuid(media_uuid)

        if session_uuid:
            return {
                "success": True,
                "media_uuid": media_uuid,
                "session_uuid": session_uuid,
                "message": (f"Found session {session_uuid} for media {media_uuid}"),
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"No session found for media UUID {media_uuid}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "API: Failed to find session for media UUID %s: %s",
            media_uuid,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to find session for media UUID: {str(e)}"
        )

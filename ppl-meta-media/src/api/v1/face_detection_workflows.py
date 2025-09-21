"""
PPL Meta Media Service - Face Detection Workflows API
Phase 2: Workflow-enabled bulk processing with Vision Service integration

Enhanced endpoints for bulk face detection processing with comprehensive
workflow tracking, progress monitoring, and result aggregation.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.auth import AuthUser, get_current_user
from src.database import get_db
from src.models.media import Media
from src.services.face_detection_service import MediaFaceDetectionService

logger = logging.getLogger(__name__)

# Initialize face detection service
media_face_detection = MediaFaceDetectionService()

# Create router for workflow-enabled face detection
workflow_router = APIRouter(prefix="/workflow", tags=["face-detection-workflows"])


class WorkflowFaceDetectionRequest(BaseModel):
    """Request model for workflow-enabled face detection."""

    media_ids: List[str]
    method: str = "mtcnn"
    confidence_threshold: float = 0.5
    store_results: bool = True
    workflow_metadata: Optional[Dict[str, Any]] = {}
    processing_priority: str = "normal"  # "low", "normal", "high"


class WorkflowFaceDetectionResponse(BaseModel):
    """Response model for workflow face detection."""

    workflow_id: str
    status: str
    media_count: int
    created_at: datetime
    estimated_completion_time: Optional[datetime] = None
    processing_options: Dict[str, Any]


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    workflow_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    processed_count: int
    total_count: int
    current_media_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results_summary: Dict[str, Any] = {}


@workflow_router.post(
    "/face-detection/bulk-process", response_model=WorkflowFaceDetectionResponse
)
async def start_bulk_face_detection_workflow(
    request: WorkflowFaceDetectionRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a bulk face detection workflow for multiple media items.

    This endpoint enhances the existing face detection capabilities by:
    - Processing multiple videos in a managed workflow
    - Storing results directly in Vision Service database
    - Providing progress tracking and status updates
    - Supporting both camera recordings and user uploads
    """
    try:
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())

        # Validate media access for all requested items
        validated_media = []
        for media_id in request.media_ids:
            # TODO: Add media access validation logic
            validated_media.append(media_id)

        # Create workflow execution context
        workflow_context = {
            "workflow_id": workflow_id,
            "user_id": current_user.user_id,
            "media_ids": validated_media,
            "method": request.method,
            "confidence_threshold": request.confidence_threshold,
            "store_results": request.store_results,
            "metadata": request.workflow_metadata,
            "priority": request.processing_priority,
            "created_at": datetime.now(),
            "status": "queued",
        }

        # Start background processing
        background_tasks.add_task(
            process_bulk_face_detection_workflow, workflow_context, db
        )

        return WorkflowFaceDetectionResponse(
            workflow_id=workflow_id,
            status="queued",
            media_count=len(validated_media),
            created_at=workflow_context["created_at"],
            processing_options={
                "method": request.method,
                "confidence_threshold": request.confidence_threshold,
                "store_results": request.store_results,
                "priority": request.processing_priority,
            },
        )

    except Exception as e:
        logger.error(f"Failed to start bulk face detection workflow: {e}")
        raise HTTPException(status_code=500, detail="Failed to start workflow")


@workflow_router.get(
    "/face-detection/status/{workflow_id}", response_model=WorkflowStatusResponse
)
async def get_workflow_status(
    workflow_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the status of a face detection workflow.

    Provides real-time progress tracking for bulk processing workflows.
    """
    try:
        # TODO: Implement workflow status retrieval from database/cache
        # For now, return a placeholder response
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status="processing",
            progress=0.5,
            processed_count=5,
            total_count=10,
            current_media_id="sample-media-id",
            started_at=datetime.now(),
            results_summary={
                "total_faces_detected": 25,
                "processing_time_seconds": 120.5,
                "successful_media": 5,
                "failed_media": 0,
            },
        )

    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workflow status")


@workflow_router.get(
    "/face-detection/workflows", response_model=List[WorkflowStatusResponse]
)
async def list_user_workflows(
    current_user: AuthUser = Depends(get_current_user),
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    List all face detection workflows for the current user.

    Supports filtering by status and pagination.
    """
    try:
        # TODO: Implement user workflows retrieval
        # For now, return placeholder data
        return [
            WorkflowStatusResponse(
                workflow_id="workflow-1",
                status="completed",
                progress=1.0,
                processed_count=10,
                total_count=10,
                completed_at=datetime.now(),
                results_summary={
                    "total_faces_detected": 45,
                    "processing_time_seconds": 300.2,
                    "successful_media": 10,
                    "failed_media": 0,
                },
            )
        ]

    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail="Failed to list workflows")


async def process_bulk_face_detection_workflow(
    workflow_context: Dict[str, Any], db: Session
):
    """
    Background task to process bulk face detection workflow.

    This function:
    1. Processes each media item in the workflow
    2. Performs face detection using embedded service
    3. Sends results to Vision Service for storage and analytics
    4. Updates workflow status and progress
    """
    from services.vision_service_client import VisionServiceClient
    from src.services.face_detection_service import (
        CameraRecordingFaceDetectionService,
        FaceDetectionService,
    )

    workflow_id = workflow_context["workflow_id"]
    media_ids = workflow_context["media_ids"]
    workflow_metadata = workflow_context.get("workflow_metadata", {})

    try:
        logger.info(
            f"Starting bulk face detection workflow {workflow_id} for {len(media_ids)} media items"
        )

        # Initialize services
        face_detector = FaceDetectionService()
        camera_face_detector = CameraRecordingFaceDetectionService()
        vision_client = VisionServiceClient()

        # Update workflow status to processing
        workflow_context["status"] = "processing"
        workflow_context["started_at"] = datetime.now()

        processed_count = 0
        total_faces_detected = 0
        vision_results = []

        for media_id in media_ids:
            try:
                # Update current processing status
                workflow_context["current_media_id"] = media_id

                logger.info(f"Processing face detection for media {media_id}")

                # Get media record from database
                media_record = db.query(Media).filter(Media.uuid == media_id).first()

                if not media_record:
                    logger.warning(f"Media record not found for {media_id}")
                    continue

                # Perform face detection using embedded service
                if media_record.media_type == "video":
                    detection_results = (
                        await face_detector.process_video_face_detection(
                            media_record.file_path,
                            method="mtcnn",
                            confidence_threshold=0.5,
                        )
                    )
                elif media_record.media_type == "image":
                    detection_results = (
                        await face_detector.process_image_face_detection(
                            media_record.file_path,
                            method="mtcnn",
                            confidence_threshold=0.5,
                        )
                    )
                else:
                    logger.warning(f"Unsupported media type: {media_record.media_type}")
                    continue

                # Count faces detected
                faces_detected = len(detection_results.get("detections", []))
                total_faces_detected += faces_detected
                processed_count += 1

                # Prepare results for Vision Service
                vision_result = {
                    "media_id": media_id,
                    "frame_number": detection_results.get("frame_number"),
                    "timestamp": detection_results.get("timestamp"),
                    "detections": detection_results.get("detections", []),
                    "metadata": {
                        "workflow_id": workflow_id,
                        "media_type": media_record.media_type,
                        "processing_method": "mtcnn",
                        "confidence_threshold": 0.5,
                    },
                }
                vision_results.append(vision_result)

                # Update progress
                progress = processed_count / len(media_ids)
                workflow_context["progress"] = progress

                logger.info(
                    f"Completed face detection for media {media_id}, found {faces_detected} faces"
                )

            except Exception as e:
                logger.error(
                    f"Failed to process media {media_id} in workflow {workflow_id}: {e}"
                )
                # Continue with next media item
                continue

        # Send all results to Vision Service for storage
        if vision_results:
            try:
                vision_response = await vision_client.send_bulk_face_detection_results(
                    workflow_id=workflow_id,
                    results=vision_results,
                    source_service="ppl-meta-media",
                )

                if vision_response.get("success"):
                    logger.info(
                        f"Successfully sent {len(vision_results)} results to Vision Service"
                    )
                else:
                    logger.error(
                        f"Failed to send results to Vision Service: {vision_response.get('error')}"
                    )

            except Exception as e:
                logger.error(f"Failed to communicate with Vision Service: {e}")

        # Update final workflow status
        workflow_context["status"] = "completed"
        workflow_context["completed_at"] = datetime.now()
        workflow_context["results_summary"] = {
            "total_faces_detected": total_faces_detected,
            "successful_media": processed_count,
            "failed_media": len(media_ids) - processed_count,
            "vision_service_integration": len(vision_results) > 0,
            "processing_time_seconds": (
                workflow_context["completed_at"] - workflow_context["started_at"]
            ).total_seconds(),
        }

        logger.info(f"Completed bulk face detection workflow {workflow_id}")

    except Exception as e:
        logger.error(f"Bulk face detection workflow {workflow_id} failed: {e}")
        workflow_context["status"] = "failed"
        workflow_context["error_message"] = str(e)


# Add enhanced single media processing endpoint
@workflow_router.post("/face-detection/process/{media_id}")
async def process_single_media_workflow(
    media_id: str,
    method: str = "mtcnn",
    confidence_threshold: float = 0.5,
    store_results: bool = True,
    workflow_metadata: Optional[Dict[str, Any]] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Process face detection for a single media item with workflow tracking.

    Enhanced version of existing face detection that includes:
    - Workflow metadata and tracking
    - Direct Vision Service integration
    - Source-agnostic processing (camera recordings + user uploads)
    """
    try:
        # Create single-item workflow
        workflow_request = WorkflowFaceDetectionRequest(
            media_ids=[media_id],
            method=method,
            confidence_threshold=confidence_threshold,
            store_results=store_results,
            workflow_metadata=workflow_metadata or {},
        )

        # Use existing bulk processing workflow
        background_tasks = BackgroundTasks()
        response = await start_bulk_face_detection_workflow(
            workflow_request, background_tasks, current_user, db
        )

        return {
            "workflow_id": response.workflow_id,
            "media_id": media_id,
            "status": response.status,
            "processing_options": response.processing_options,
            "message": "Face detection workflow started for single media item",
        }

    except Exception as e:
        logger.error(f"Failed to start single media workflow for {media_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start face detection workflow"
        )


# Export the router to be included in main API
__all__ = ["workflow_router"]

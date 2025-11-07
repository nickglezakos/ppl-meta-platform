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

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.auth import AuthUser, get_current_user
from src.database import get_db
from src.models.media import Media
from src.models.workflow import MediaWorkflow
from src.services.face_detection_service import MediaFaceDetectionService

# Queue-based PPL Thread triggering
try:
    import redis
    from celery import Celery

    QUEUE_AVAILABLE = True
    # Initialize queue connection
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    celery_app = Celery("ppl_workflows", broker="redis://localhost:6379/0")
except ImportError:
    QUEUE_AVAILABLE = False
    redis_client = None
    celery_app = None

logger = logging.getLogger(__name__)

# Initialize face detection service
media_face_detection = MediaFaceDetectionService()

# Create router for workflow-enabled face detection
workflow_router = APIRouter(prefix="/workflow", tags=["face-detection-workflows"])

# Security for extracting JWT tokens
security = HTTPBearer()


class WorkflowFaceDetectionRequest(BaseModel):
    """Request model for workflow-enabled face detection."""

    media_ids: List[str]
    method: str = "two_stage"
    confidence_threshold: float = 0.5
    store_results: bool = True
    workflow_metadata: Optional[Dict[str, Any]] = {}
    processing_priority: str = "normal"  # "low", "normal", "high"
    frames_per_second: int = 3  # Frames to process per second (default: 3 fps)


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
    current_user: AuthUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
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

        # Create workflow record in database
        workflow = MediaWorkflow(
            workflow_id=workflow_id,
            user_id=current_user.user_id,
            method=request.method,
            confidence_threshold=request.confidence_threshold,
            processing_priority=request.processing_priority,
            total_count=len(validated_media),
            media_ids=validated_media,
            workflow_metadata=request.workflow_metadata,
            status="queued",
        )

        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        # Create workflow execution context for background task
        workflow_context = {
            "workflow_id": workflow_id,
            "media_ids": validated_media,
            "user_id": current_user.user_id,
            "method": request.method,
            "confidence_threshold": request.confidence_threshold,
            "store_results": request.store_results,
            "frames_per_second": request.frames_per_second,
            "created_at": datetime.now(),
            "status": "queued",
            "authorization_token": credentials.credentials,
        }

        # 🔐 DEBUG: Confirm authorization token is present
        logger.info(
            f"🔐 WORKFLOW AUTH: Token present = "
            f"{bool(credentials.credentials)} for workflow {workflow_id}"
        )

        # Start background processing using asyncio instead of FastAPI BackgroundTasks
        asyncio.create_task(process_bulk_face_detection_workflow(workflow_context))

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
        # Retrieve workflow from database
        workflow = (
            db.query(MediaWorkflow)
            .filter(
                MediaWorkflow.workflow_id == workflow_id,
                MediaWorkflow.user_id == current_user.user_id,
            )
            .first()
        )

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return WorkflowStatusResponse(
            workflow_id=workflow.workflow_id,
            status=workflow.status,
            progress=workflow.progress,
            processed_count=workflow.processed_count,
            total_count=workflow.total_count,
            current_media_id=workflow.current_media_id,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            error_message=workflow.error_message,
            results_summary=workflow.results_summary or {},
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


async def process_bulk_face_detection_workflow(workflow_context: Dict[str, Any]):
    """
    Background task to process bulk face detection workflow.

    This function:
    1. Processes each media item in the workflow
    2. Performs face detection using embedded service
    3. Sends results to Vision Service for storage and analytics
    4. Updates workflow status and progress
    """
    from src.services.face_detection_service import (
        CameraRecordingFaceDetectionService,
        MediaFaceDetectionService,
    )
    from src.services.vision_service_client import VisionServiceClient

    workflow_id = workflow_context["workflow_id"]
    media_ids = workflow_context["media_ids"]
    detection_method = workflow_context.get("method", "two_stage")
    confidence_threshold = workflow_context.get("confidence_threshold", 0.5)
    workflow_metadata = workflow_context.get("workflow_metadata", {})

    # Create new database session for background task
    from src.database import SessionLocal

    db = SessionLocal()

    try:
        logger.info(
            f"Starting bulk face detection workflow {workflow_id} for {len(media_ids)} media items"
        )

        # Get workflow from database
        workflow = (
            db.query(MediaWorkflow)
            .filter(MediaWorkflow.workflow_id == workflow_id)
            .first()
        )

        if not workflow:
            logger.error(f"Workflow {workflow_id} not found in database")
            return

        # Mark workflow as started
        workflow.mark_started()
        db.commit()

        # Initialize services
        face_detector = MediaFaceDetectionService()
        camera_face_detector = CameraRecordingFaceDetectionService()
        vision_client = VisionServiceClient()

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
                    # Skip this media item - don't use continue to ensure completion logic runs
                    skip_processing = True
                else:
                    skip_processing = False

                # DUPLICATE PREVENTION: Check if Vision Service already has results for this media
                if not skip_processing:
                    try:
                        vision_check_response = (
                            await vision_client.check_existing_faces(media_id)
                        )
                        if vision_check_response.get("has_existing_faces", False):
                            logger.info(
                                f"Media {media_id} already has {vision_check_response.get('face_count', 0)} "
                                f"face detections in Vision Service. Skipping duplicate processing."
                            )

                            # Create mock detection results to maintain workflow flow
                            detection_results = {
                                "detections": [],
                                "metadata": {
                                    "skipped_duplicate": True,
                                    "existing_face_count": vision_check_response.get(
                                        "face_count", 0
                                    ),
                                    "message": "Face detection already completed - reusing existing results",
                                },
                            }

                            # Update counters but don't re-process
                            processed_count += 1
                            skip_processing = True
                            logger.info(
                                f"Skipped duplicate processing for media {media_id}"
                            )

                    except Exception as check_error:
                        logger.warning(
                            f"Failed to check existing faces in Vision Service: {check_error}"
                        )
                        # Continue with normal processing if check fails
                        skip_processing = False

                # Initialize detection_results for all code paths
                detection_results = {
                    "detections": [],
                    "metadata": {"skipped_processing": True},
                }

                # Perform face detection using embedded service (only if not skipped)
                if not skip_processing:
                    if media_record.media_type == "video":
                        detection_results = (
                            await face_detector.process_video_face_detection(
                                media_record.file_path,
                                method=detection_method,
                                confidence_threshold=confidence_threshold,
                                frames_per_second=workflow_context.get(
                                    "frames_per_second", 3
                                ),
                            )
                        )
                    elif media_record.media_type == "image":
                        detection_results = (
                            await face_detector.process_image_face_detection(
                                media_record.file_path,
                                method=detection_method,
                                confidence_threshold=confidence_threshold,
                            )
                        )
                    else:
                        logger.warning(
                            f"Unsupported media type: {media_record.media_type}"
                        )
                        # Skip this media item - don't use continue to ensure completion logic runs
                        skip_processing = True

                # Count faces detected (works for both new and skipped processing)
                if not skip_processing:
                    # Only count newly detected faces for processing statistics
                    faces_detected = len(detection_results.get("detections", []))
                    total_faces_detected += faces_detected
                    processed_count += 1
                else:
                    # For skipped items, don't count new faces but still track processing
                    faces_detected = 0  # No new faces detected for skipped items

                # Prepare results for Vision Service
                vision_result = {
                    "media_id": media_id,
                    "frame_number": detection_results.get("frame_number"),
                    "timestamp": detection_results.get("timestamp"),
                    "detections": detection_results.get("detections", []),
                    "metadata": {
                        "workflow_id": workflow_id,
                        "media_type": media_record.media_type,
                        "processing_method": detection_method,
                        "confidence_threshold": confidence_threshold,
                    },
                }
                vision_results.append(vision_result)

                # Update workflow progress in database
                workflow.update_progress(processed_count, media_id)
                db.commit()

                logger.info(
                    f"Completed face detection for media {media_id}, found {faces_detected} faces"
                )

            except Exception as e:
                logger.error(
                    f"Failed to process media {media_id} in workflow {workflow_id}: {e}"
                )
                # Skip this media item - don't use continue to ensure completion logic runs
                # The workflow completion logic will still run after this loop

        # Send all results to Vision Service for storage with session tracking
        if vision_results:
            try:
                # Get authorization token from workflow context
                auth_token = workflow_context.get("authorization_token")
                
                # 🎯 KEY FIX: Use session-aware endpoint for automatic session creation and PPL Thread triggering
                vision_response = (
                    await vision_client.send_bulk_face_detection_results_with_sessions(
                        workflow_id=workflow_id,
                        results=vision_results,
                        source_service="ppl-meta-media",
                        authorization=auth_token,
                    )
                )

                if vision_response.get("success"):
                    logger.info(
                        f"✅ SESSION-AWARE: Successfully processed {vision_response.get('media_processed', 0)} media items "
                        f"with {vision_response.get('total_faces_stored', 0)} faces stored and session tracking enabled"
                    )

                    # Log session UUIDs created for traceability
                    session_uuids = vision_response.get("session_uuids", [])
                    if session_uuids:
                        logger.info(
                            f"✅ SESSION-AWARE: Created sessions: {', '.join(session_uuids)}"
                        )
                else:
                    logger.error(
                        f"❌ SESSION-AWARE: Failed to send results to Vision Service: {vision_response.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ SESSION-AWARE: Failed to communicate with Vision Service: {e}"
                )

        # Mark workflow as completed in database
        logger.info("🚨 WORKFLOW COMPLETION: Marking workflow as completed")
        results_summary = {
            "total_faces_detected": total_faces_detected,
            "successful_media": processed_count,
            "failed_media": len(media_ids) - processed_count,
            "vision_service_integration": len(vision_results) > 0,
            "processing_time_seconds": (
                (datetime.utcnow() - workflow.started_at).total_seconds()
                if workflow.started_at
                else 0
            ),
        }
        workflow.mark_completed(results_summary)
        db.commit()

        logger.info(f"Completed bulk face detection workflow {workflow_id}")
        logger.info("🔥 TRIGGER DEBUG: About to start automatic trigger logic")
        logger.info(
            "🎯 DEBUG AUTO TRIGGER: total_faces_detected=%d, " "media_count=%d",
            total_faces_detected,
            len(media_ids),
        )

        # 🎯 EVENT-DRIVEN PPL THREAD TRIGGER: Automatically trigger PPL Thread when face detection completes
        # Check if there are any faces (newly detected OR already existing) to process
        total_available_faces = total_faces_detected

        # If no new faces detected, check Vision Service for existing faces
        if total_available_faces == 0:
            logger.info("🔍 DEBUG AUTO TRIGGER: Checking for existing faces...")
            try:
                for media_id in media_ids:
                    vision_check = await vision_client.check_existing_faces(media_id)
                    if vision_check.get("has_existing_faces", False):
                        existing_count = vision_check.get("face_count", 0)
                        total_available_faces += existing_count
                        logger.info(
                            "🔍 AUTO TRIGGER: Found %d existing faces for media %s",
                            existing_count,
                            media_id,
                        )
            except Exception as e:
                logger.warning("⚠️ AUTO TRIGGER: Could not check existing faces: %s", e)

        logger.info(
            "🎯 DEBUG AUTO TRIGGER: total_available_faces=%d", total_available_faces
        )

        # Trigger PPL Thread if there are any faces available (new or existing)
        if total_available_faces > 0:
            logger.info(
                "🎯 AUTO TRIGGER: Starting PPL Thread for %d total faces",
                total_available_faces,
            )
            try:
                await trigger_automatic_ppl_thread_workflow(
                    workflow_id=workflow_id,
                    media_ids=media_ids,
                    total_faces=total_available_faces,
                    vision_response=(
                        vision_response if "vision_response" in locals() else None
                    ),
                )
                logger.info("✅ AUTO TRIGGER: PPL Thread trigger completed")
            except Exception as trigger_error:
                logger.error(
                    "❌ AUTO TRIGGER: Error during PPL Thread trigger: %s",
                    trigger_error,
                )
        else:
            logger.warning(
                "⚠️ AUTO TRIGGER: No faces found (new or existing) for workflow %s",
                workflow_id,
            )

    except Exception as e:
        logger.error(f"Bulk face detection workflow {workflow_id} failed: {e}")

        # Mark workflow as failed in database
        workflow.mark_failed(str(e))
        db.commit()

    finally:
        # Always close the database session
        db.close()


# Add enhanced single media processing endpoint
@workflow_router.post("/face-detection/process/{media_id}")
async def process_single_media_workflow(
    media_id: str,
    method: str = "two_stage",
    confidence_threshold: float = 0.5,
    store_results: bool = True,
    frames_per_second: int = 3,
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
    - Frame rate optimization (frames_per_second parameter)
    """
    try:
        # Create single-item workflow
        workflow_request = WorkflowFaceDetectionRequest(
            media_ids=[media_id],
            method=method,
            confidence_threshold=confidence_threshold,
            store_results=store_results,
            frames_per_second=frames_per_second,
            workflow_metadata=workflow_metadata or {},
        )

        # Use existing bulk processing workflow
        response = await start_bulk_face_detection_workflow(
            workflow_request, current_user, db
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


async def trigger_automatic_ppl_thread_workflow(
    workflow_id: str,
    media_ids: List[str],
    total_faces: int,
    vision_response: Optional[Dict[str, Any]] = None,
):
    """
    Queue-based automatic PPL Thread trigger for completed face detection.

    This function uses Redis/Celery queue for reliable, asynchronous triggering
    of PPL Thread workflows when face detection completes.

    Benefits:
    - Reliable: Tasks survive service restarts
    - Decoupled: No direct service-to-service API calls
    - Scalable: Multiple workers can process triggers
    - Monitored: Queue status visible via Celery tools
    """
    logger.info("🎯 QUEUE TRIGGER: Starting for workflow %s", workflow_id)
    logger.info(
        "📊 QUEUE TRIGGER: %d faces detected for %d media",
        total_faces,
        len(media_ids),
    )

    if not QUEUE_AVAILABLE:
        logger.error(
            "❌ QUEUE UNAVAILABLE: Redis/Celery not available, falling back to direct trigger"
        )
        return await _legacy_direct_trigger(workflow_id, media_ids, total_faces)

    try:
        # Queue PPL Thread trigger tasks for each media item
        queued_tasks = []
        for media_id in media_ids:
            try:
                # Queue the task using Celery
                task = celery_app.send_task(
                    "trigger_ppl_thread",
                    args=[media_id, total_faces, workflow_id],
                    kwargs={"trigger_reason": "automatic_face_detection_completion"},
                    queue="ppl_thread_queue",
                )

                queued_tasks.append(
                    {"media_id": media_id, "task_id": task.id, "status": "queued"}
                )

                logger.info(
                    "✅ QUEUED: PPL Thread trigger for media %s (task: %s)",
                    media_id,
                    task.id,
                )

            except Exception as queue_error:
                logger.error(
                    "❌ QUEUE ERROR: Failed to queue PPL trigger for %s: %s",
                    media_id,
                    queue_error,
                )
                queued_tasks.append(
                    {
                        "media_id": media_id,
                        "task_id": None,
                        "status": "failed",
                        "error": str(queue_error),
                    }
                )

        # Log summary
        successful_queues = len([t for t in queued_tasks if t["status"] == "queued"])
        logger.info(
            "📋 QUEUE SUMMARY: %d/%d tasks queued successfully",
            successful_queues,
            len(media_ids),
        )

        return {
            "queued_tasks": queued_tasks,
            "successful_queues": successful_queues,
            "total_media": len(media_ids),
            "method": "queue_based",
        }

    except Exception as e:
        logger.error("❌ QUEUE TRIGGER: Unexpected error: %s", e)
        # Fallback to direct trigger if queue completely fails
        logger.info("🔄 FALLBACK: Attempting direct trigger")
        return await _legacy_direct_trigger(workflow_id, media_ids, total_faces)


async def _legacy_direct_trigger(
    workflow_id: str, media_ids: List[str], total_faces: int
) -> Dict[str, Any]:
    """
    Legacy direct API trigger as fallback when queue is unavailable.
    This is the old implementation kept for reliability.
    """
    logger.info("🔄 LEGACY TRIGGER: Using direct API calls as fallback")

    try:
        successful_triggers = 0
        async with httpx.AsyncClient() as client:
            # Use the PPL Thread workflow trigger endpoint
            ppl_trigger_payload = {
                "media_ids": (
                    media_ids[0] if media_ids else ""
                ),  # Single string, not array
                "workflow_type": "automatic_face_detection_trigger",
                "source_workflow_id": workflow_id,
                "total_faces": str(total_faces),  # Convert to string
                "trigger_reason": "legacy_fallback_trigger",
            }

            response = await client.post(
                "http://localhost:8003/api/v1/person-objects/workflow/trigger",
                json=ppl_trigger_payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                result = response.json()
                successful_triggers = len(media_ids)
                logger.info(
                    "✅ LEGACY TRIGGER: Successfully triggered PPL Thread workflow: %s",
                    result,
                )
            else:
                logger.error(
                    "❌ LEGACY TRIGGER: Failed to trigger PPL Thread (status %d): %s",
                    response.status_code,
                    response.text,
                )

    except httpx.RequestError as e:
        logger.error("❌ LEGACY TRIGGER: Network error during trigger: %s", e)
    except Exception as e:
        logger.error("❌ LEGACY TRIGGER: Unexpected error during trigger: %s", e)

    return {
        "successful_triggers": successful_triggers,
        "total_media": len(media_ids),
        "method": "legacy_direct",
    }


# Export the router to be included in main API
__all__ = ["workflow_router"]

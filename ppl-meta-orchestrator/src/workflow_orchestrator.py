"""
PPL Meta Orchestrator - Workflow Orchestrator Classes
Phase 1 Implementation: FaceDetectionWorkflowOrchestrator and
CameraFaceDetectionWorkflowOrchestrator with method-specific lifecycle management
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from service_clients import ServiceClientManager, ServiceResponse, TraceabilityContext

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow processing status enumeration."""

    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(Enum):
    """Workflow type enumeration."""

    BULK_PROCESSING = "bulk_processing"
    CAMERA_TRIGGERED = "camera_triggered"
    SCHEDULED = "scheduled"
    REAL_TIME = "real_time"
    PROGRESSIVE_ANALYTICS = "progressive_analytics"


class MethodLifecycle(BaseModel):
    """Track individual detection method lifecycle within a workflow."""

    lifecycle_id: str
    method: str
    media_id: str
    workflow_id: str
    camera_device_id: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.CREATED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_options: Dict[str, Any] = {}
    results_count: Optional[int] = None
    confidence_scores: List[float] = []
    trace_id: str
    user_id: Optional[str] = None


class WorkflowExecution(BaseModel):
    """Complete workflow execution tracking."""

    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowStatus = WorkflowStatus.CREATED
    user_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_media_count: int = 0
    processed_media_count: int = 0
    failed_media_count: int = 0
    method_lifecycles: List[MethodLifecycle] = []
    camera_device_ids: List[str] = []
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    trace_contexts: List[TraceabilityContext] = []


class CameraEventData(BaseModel):
    """Camera service event data structure."""

    event_type: str  # "recording_completed", "recording_started", etc.
    camera_device_id: str
    recording_session_id: str
    video_file_path: str
    user_id: str
    recording_duration_seconds: float
    file_size_bytes: int
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class FaceDetectionWorkflowOrchestrator:
    """Core workflow orchestrator for face detection processing."""

    def __init__(self, service_manager: ServiceClientManager):
        self.service_manager = service_manager
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_history: List[WorkflowExecution] = []

    async def create_workflow(
        self,
        workflow_type: WorkflowType,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> WorkflowExecution:
        """Create new workflow execution with traceability."""
        workflow_id = str(uuid.uuid4())

        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            user_id=user_id,
            created_at=datetime.now(),
            metadata=metadata or {},
        )

        self.active_workflows[workflow_id] = workflow
        logger.info(f"Created workflow {workflow_id} of type {workflow_type}")

        return workflow

    async def start_bulk_processing(
        self,
        media_ids: List[str],
        methods: List[str],
        user_id: Optional[str] = None,
        processing_options: Optional[Dict] = None,
        priority: str = "normal",
    ) -> WorkflowExecution:
        """Start bulk face detection processing workflow."""
        workflow = await self.create_workflow(
            WorkflowType.BULK_PROCESSING,
            user_id=user_id,
            metadata={
                "media_ids": media_ids,
                "methods": methods,
                "processing_options": processing_options or {},
                "priority": priority,
            },
        )

        workflow.total_media_count = len(media_ids)
        workflow.status = WorkflowStatus.PROCESSING
        workflow.started_at = datetime.now()

        # Create method lifecycles for each media/method combination
        for media_id in media_ids:
            for method in methods:
                lifecycle = MethodLifecycle(
                    lifecycle_id=str(uuid.uuid4()),
                    method=method,
                    media_id=media_id,
                    workflow_id=workflow.workflow_id,
                    processing_options=processing_options or {},
                    trace_id=str(uuid.uuid4()),
                    user_id=user_id,
                )
                workflow.method_lifecycles.append(lifecycle)

        # Start processing asynchronously
        asyncio.create_task(self._execute_bulk_processing(workflow))

        return workflow

    async def _execute_bulk_processing(self, workflow: WorkflowExecution) -> None:
        """Execute bulk processing workflow with full traceability."""
        try:
            logger.info(f"Starting bulk processing workflow {workflow.workflow_id}")

            # Process each method lifecycle
            for lifecycle in workflow.method_lifecycles:
                try:
                    await self._process_method_lifecycle(workflow, lifecycle)
                    workflow.processed_media_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to process lifecycle {lifecycle.lifecycle_id}: {e}"
                    )
                    lifecycle.status = WorkflowStatus.FAILED
                    lifecycle.error_message = str(e)
                    workflow.failed_media_count += 1

            # Update workflow completion status
            if workflow.failed_media_count == 0:
                workflow.status = WorkflowStatus.COMPLETED
            elif workflow.processed_media_count > 0:
                workflow.status = WorkflowStatus.COMPLETED  # Partial success
            else:
                workflow.status = WorkflowStatus.FAILED

            workflow.completed_at = datetime.now()

            # Move to history
            self.workflow_history.append(workflow)
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]

            logger.info(f"Completed bulk processing workflow {workflow.workflow_id}")

        except Exception as e:
            logger.error(
                f"Critical error in bulk processing workflow {workflow.workflow_id}: {e}"
            )
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = str(e)
            workflow.completed_at = datetime.now()

    async def _process_method_lifecycle(
        self, workflow: WorkflowExecution, lifecycle: MethodLifecycle
    ) -> None:
        """Process individual method lifecycle with traceability."""
        lifecycle.status = WorkflowStatus.PROCESSING
        lifecycle.started_at = datetime.now()

        # Create traceability context
        trace_ctx = self.service_manager.create_trace_context(
            workflow_id=workflow.workflow_id,
            operation="face_detection_processing",
            user_id=workflow.user_id,
            metadata={
                "lifecycle_id": lifecycle.lifecycle_id,
                "method": lifecycle.method,
                "media_id": lifecycle.media_id,
            },
        )

        # Start face detection processing
        response = await self.service_manager.vision.start_face_detection(
            trace_ctx=trace_ctx,
            media_id=lifecycle.media_id,
            method=lifecycle.method,
            camera_device_id=lifecycle.camera_device_id,
            processing_options=lifecycle.processing_options,
        )

        if not response.success:
            raise Exception(f"Failed to start face detection: {response.error_message}")

        # Wait for processing completion (simplified polling)
        vision_lifecycle_id = response.data.get("lifecycle_id")
        await self._wait_for_processing_completion(
            trace_ctx, vision_lifecycle_id, lifecycle
        )

        lifecycle.status = WorkflowStatus.COMPLETED
        lifecycle.completed_at = datetime.now()

    async def _wait_for_processing_completion(
        self,
        trace_ctx: TraceabilityContext,
        vision_lifecycle_id: str,
        lifecycle: MethodLifecycle,
        max_wait_minutes: int = 30,
    ) -> None:
        """Wait for vision service processing completion with timeout."""
        start_time = datetime.now()
        max_wait_time = start_time + timedelta(minutes=max_wait_minutes)

        while datetime.now() < max_wait_time:
            # Check processing status
            status_response = await self.service_manager.vision.get_processing_status(
                trace_ctx=trace_ctx, lifecycle_id=vision_lifecycle_id
            )

            if status_response.success:
                status_data = status_response.data
                vision_status = status_data.get("status", "unknown")

                if vision_status in ["completed", "failed"]:
                    if vision_status == "failed":
                        raise Exception(
                            f"Vision processing failed: {status_data.get('error')}"
                        )

                    # Get final results
                    results_response = (
                        await self.service_manager.vision.get_detection_results(
                            trace_ctx=trace_ctx,
                            media_id=lifecycle.media_id,
                            method=lifecycle.method,
                            lifecycle_id=vision_lifecycle_id,
                        )
                    )

                    if results_response.success:
                        results = results_response.data.get("faces", [])
                        lifecycle.results_count = len(results)
                        lifecycle.confidence_scores = [
                            face.get("confidence", 0.0) for face in results
                        ]

                    return

            # Wait before next check
            await asyncio.sleep(5)

        raise Exception(f"Processing timeout after {max_wait_minutes} minutes")

    async def get_workflow_status(
        self, workflow_id: str
    ) -> Optional[WorkflowExecution]:
        """Get workflow execution status with complete traceability."""
        # Check active workflows first
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]

        # Check historical workflows
        for workflow in self.workflow_history:
            if workflow.workflow_id == workflow_id:
                return workflow

        return None

    async def get_user_workflows(
        self, user_id: str, limit: int = 50
    ) -> List[WorkflowExecution]:
        """Get workflows for specific user with traceability."""
        user_workflows = []

        # Get active workflows
        for workflow in self.active_workflows.values():
            if workflow.user_id == user_id:
                user_workflows.append(workflow)

        # Get historical workflows
        for workflow in self.workflow_history:
            if workflow.user_id == user_id:
                user_workflows.append(workflow)

        # Sort by creation time (newest first) and limit
        user_workflows.sort(key=lambda w: w.created_at, reverse=True)
        return user_workflows[:limit]


class CameraFaceDetectionWorkflowOrchestrator(FaceDetectionWorkflowOrchestrator):
    """Extended orchestrator with camera-specific workflow capabilities."""

    def __init__(self, service_manager: ServiceClientManager):
        super().__init__(service_manager)
        self.camera_settings_cache: Dict[str, Dict] = {}
        self.interval_schedules: Dict[str, Dict] = {}

    async def handle_camera_recording_event(
        self, event_data: CameraEventData
    ) -> Optional[WorkflowExecution]:
        """Handle camera recording completion event with automated processing."""
        logger.info(
            f"Handling camera event: {event_data.event_type} from {event_data.camera_device_id}"
        )

        if event_data.event_type != "recording_completed":
            logger.debug(f"Ignoring non-completion event: {event_data.event_type}")
            return None

        try:
            # Get user camera settings
            camera_settings = await self._get_camera_settings(
                event_data.camera_device_id, event_data.user_id
            )

            if not camera_settings.get("auto_face_detection", False):
                logger.info(
                    f"Auto face detection disabled for camera {event_data.camera_device_id}"
                )
                return None

            # Register video with Media Service
            media_response = await self._register_camera_video(event_data)
            if not media_response.success:
                logger.error(
                    f"Failed to register camera video: {media_response.error_message}"
                )
                return None

            media_id = media_response.data.get("media_id")

            # Create camera-triggered workflow
            workflow = await self.create_workflow(
                WorkflowType.CAMERA_TRIGGERED,
                user_id=event_data.user_id,
                metadata={
                    "camera_device_id": event_data.camera_device_id,
                    "recording_session_id": event_data.recording_session_id,
                    "media_id": media_id,
                    "event_data": event_data.dict(),
                },
            )

            workflow.camera_device_ids = [event_data.camera_device_id]

            # Get detection methods from camera settings
            detection_methods = camera_settings.get("detection_methods", ["mtcnn"])
            processing_options = camera_settings.get("processing_options", {})

            # Start automated processing
            await self.start_camera_processing(
                workflow=workflow,
                media_id=media_id,
                camera_device_id=event_data.camera_device_id,
                methods=detection_methods,
                processing_options=processing_options,
            )

            return workflow

        except Exception as e:
            logger.error(f"Failed to handle camera recording event: {e}")
            return None

    async def start_camera_processing(
        self,
        workflow: WorkflowExecution,
        media_id: str,
        camera_device_id: str,
        methods: List[str],
        processing_options: Optional[Dict] = None,
    ) -> None:
        """Start camera-specific face detection processing."""
        workflow.total_media_count = 1
        workflow.status = WorkflowStatus.PROCESSING
        workflow.started_at = datetime.now()

        # Create method lifecycles for camera processing
        for method in methods:
            lifecycle = MethodLifecycle(
                lifecycle_id=str(uuid.uuid4()),
                method=method,
                media_id=media_id,
                workflow_id=workflow.workflow_id,
                camera_device_id=camera_device_id,
                processing_options=processing_options or {},
                trace_id=str(uuid.uuid4()),
                user_id=workflow.user_id,
            )
            workflow.method_lifecycles.append(lifecycle)

        # Start processing asynchronously
        asyncio.create_task(self._execute_camera_processing(workflow))

    async def _execute_camera_processing(self, workflow: WorkflowExecution) -> None:
        """Execute camera-specific processing workflow."""
        try:
            logger.info(f"Starting camera processing workflow {workflow.workflow_id}")

            # Process each method lifecycle
            for lifecycle in workflow.method_lifecycles:
                try:
                    await self._process_method_lifecycle(workflow, lifecycle)
                    workflow.processed_media_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to process camera lifecycle {lifecycle.lifecycle_id}: {e}"
                    )
                    lifecycle.status = WorkflowStatus.FAILED
                    lifecycle.error_message = str(e)
                    workflow.failed_media_count += 1

            # Update completion status
            workflow.status = (
                WorkflowStatus.COMPLETED
                if workflow.failed_media_count == 0
                else WorkflowStatus.FAILED
            )
            workflow.completed_at = datetime.now()

            # Move to history
            self.workflow_history.append(workflow)
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]

            logger.info(f"Completed camera processing workflow {workflow.workflow_id}")

        except Exception as e:
            logger.error(
                f"Critical error in camera processing workflow {workflow.workflow_id}: {e}"
            )
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = str(e)
            workflow.completed_at = datetime.now()

    async def _register_camera_video(
        self, event_data: CameraEventData
    ) -> ServiceResponse:
        """Register camera video with Media Service including attribution."""
        trace_ctx = self.service_manager.create_trace_context(
            workflow_id=str(uuid.uuid4()),
            operation="register_camera_video",
            user_id=event_data.user_id,
            metadata={
                "camera_device_id": event_data.camera_device_id,
                "recording_session_id": event_data.recording_session_id,
            },
        )

        return await self.service_manager.media.register_video(
            trace_ctx=trace_ctx,
            file_path=event_data.video_file_path,
            camera_device_id=event_data.camera_device_id,
            recording_session_id=event_data.recording_session_id,
            metadata={
                "duration_seconds": event_data.recording_duration_seconds,
                "file_size_bytes": event_data.file_size_bytes,
                "recording_timestamp": event_data.timestamp.isoformat(),
                **event_data.metadata,
            },
        )

    async def _get_camera_settings(
        self, camera_device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Get camera settings with caching."""
        cache_key = f"{camera_device_id}:{user_id}"

        if cache_key in self.camera_settings_cache:
            cached_settings = self.camera_settings_cache[cache_key]
            # Check if cache is still fresh (5 minutes)
            if (datetime.now() - cached_settings["cached_at"]).seconds < 300:
                return cached_settings["settings"]

        # Fetch fresh settings
        trace_ctx = self.service_manager.create_trace_context(
            workflow_id=str(uuid.uuid4()),
            operation="get_camera_settings",
            user_id=user_id,
            metadata={"camera_device_id": camera_device_id},
        )

        response = await self.service_manager.camera.get_camera_settings(
            trace_ctx=trace_ctx, camera_device_id=camera_device_id, user_id=user_id
        )

        if response.success:
            settings = response.data.get("settings", {})

            # Cache settings
            self.camera_settings_cache[cache_key] = {
                "settings": settings,
                "cached_at": datetime.now(),
            }

            return settings
        else:
            logger.warning(f"Failed to get camera settings: {response.error_message}")
            # Return default settings
            return {
                "auto_face_detection": True,
                "detection_methods": ["mtcnn"],
                "processing_options": {},
            }

    async def get_camera_workflows(
        self, camera_device_id: str, limit: int = 50
    ) -> List[WorkflowExecution]:
        """Get workflows for specific camera device."""
        camera_workflows = []

        # Get active workflows
        for workflow in self.active_workflows.values():
            if camera_device_id in workflow.camera_device_ids:
                camera_workflows.append(workflow)

        # Get historical workflows
        for workflow in self.workflow_history:
            if camera_device_id in workflow.camera_device_ids:
                camera_workflows.append(workflow)

        # Sort by creation time (newest first) and limit
        camera_workflows.sort(key=lambda w: w.created_at, reverse=True)
        return camera_workflows[:limit]

    async def get_camera_analytics(
        self,
        camera_device_id: str,
        time_range_start: Optional[datetime] = None,
        time_range_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive camera analytics with workflow correlation."""
        # Get vision service analytics
        trace_ctx = self.service_manager.create_trace_context(
            workflow_id=str(uuid.uuid4()),
            operation="get_camera_analytics",
            metadata={"camera_device_id": camera_device_id},
        )

        vision_response = await self.service_manager.vision.get_camera_analytics(
            trace_ctx=trace_ctx,
            camera_device_id=camera_device_id,
            time_range_start=time_range_start.isoformat() if time_range_start else None,
            time_range_end=time_range_end.isoformat() if time_range_end else None,
        )

        # Get workflow statistics
        camera_workflows = await self.get_camera_workflows(camera_device_id)

        workflow_stats = {
            "total_workflows": len(camera_workflows),
            "completed_workflows": len(
                [w for w in camera_workflows if w.status == WorkflowStatus.COMPLETED]
            ),
            "failed_workflows": len(
                [w for w in camera_workflows if w.status == WorkflowStatus.FAILED]
            ),
            "total_media_processed": sum(
                w.processed_media_count for w in camera_workflows
            ),
            "average_processing_time": self._calculate_average_processing_time(
                camera_workflows
            ),
        }

        return {
            "camera_device_id": camera_device_id,
            "vision_analytics": vision_response.data if vision_response.success else {},
            "workflow_statistics": workflow_stats,
            "generated_at": datetime.now().isoformat(),
        }

    def _calculate_average_processing_time(
        self, workflows: List[WorkflowExecution]
    ) -> Optional[float]:
        """Calculate average processing time for completed workflows."""
        completed_workflows = [
            w
            for w in workflows
            if w.status == WorkflowStatus.COMPLETED and w.started_at and w.completed_at
        ]

        if not completed_workflows:
            return None

        total_time = sum(
            (w.completed_at - w.started_at).total_seconds() for w in completed_workflows
        )

        return total_time / len(completed_workflows)

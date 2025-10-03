# ================================================================
# Phase 1: Orchestrator Master Lifecycle Workflow
# PPL Meta Platform - Session-Based Workflow Management
# ================================================================

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ================================================================
# Pydantic Models for Phase 1 API
# ================================================================


class WorkflowExecutionRequest(BaseModel):
    """Request model for starting workflow execution."""

    source_identifier: str = Field(
        ..., description="Source identifier (camera stream, video file, etc.)"
    )
    source_type: str = Field(
        ..., description="Type of source (camera_recording, live_stream, etc.)"
    )
    source_id: str = Field(..., description="ID of the source media/stream")
    execution_trigger: str = Field(
        default="manual", description="Trigger type: manual, automatic, scheduled"
    )
    workflow_types: List[str] = Field(
        default=["face_detection"], description="Workflows to execute"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow configuration"
    )


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    session_uuid: str
    status: str
    current_stage: str
    progress_percentage: float
    started_at: str
    completed_at: Optional[str] = None
    total_faces_detected: Optional[int] = None
    processing_duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    configuration: Dict[str, Any]


class PersonRoutesRequest(BaseModel):
    """Request model for person routes analytics."""

    session_uuid: Optional[str] = None
    time_range_hours: int = Field(
        default=24, description="Time range for analytics in hours"
    )
    confidence_threshold: float = Field(
        default=0.5, description="Minimum confidence for routes"
    )
    include_spatial_analysis: bool = Field(
        default=True, description="Include spatial analysis"
    )


class PersonRoutesResponse(BaseModel):
    """Response model for person routes analytics."""

    total_routes: int
    total_route_points: int
    unique_persons: int
    time_range_start: str
    time_range_end: str
    routes: List[Dict[str, Any]]
    spatial_analysis: Optional[Dict[str, Any]] = None


# ================================================================
# Master Lifecycle Workflow Controller
# ================================================================


class MasterLifecycleWorkflowController:
    """
    Master controller for all PPL Meta workflows with session-based management.

    Phase 1 Features:
    - Session-based workflow execution (no duplicate prevention)
    - Master workflow lifecycle management
    - Enhanced face detection with distance & embeddings
    - Person routes analytics
    - Vector search capabilities
    """

    def __init__(self, database_client, vision_service, config: dict = None):
        self.db = database_client
        self.vision_service = vision_service
        self.config = config or {}

        # Active sessions tracking
        self.active_sessions = {}

        logger.info("Master Lifecycle Workflow Controller initialized for Phase 1")

    async def start_workflow_execution(
        self, request: WorkflowExecutionRequest, background_tasks: BackgroundTasks
    ) -> WorkflowStatusResponse:
        """
        Start session-based workflow execution.

        Phase 1 Key Changes:
        - NO duplicate prevention (supports unlimited re-executions)
        - Session UUID generation for every execution
        - Background task execution
        - Master workflow tracking
        """

        # Generate unique session UUID for this execution
        session_uuid = str(uuid.uuid4())

        logger.info(f"Starting workflow execution - Session: {session_uuid}")
        logger.info(f"Source: {request.source_identifier} ({request.source_type})")
        logger.info(f"Workflows: {request.workflow_types}")

        try:
            # Create master workflow record
            workflow_data = {
                "session_uuid": session_uuid,
                "source_identifier": request.source_identifier,
                "source_type": request.source_type,
                "source_id": request.source_id,
                "execution_trigger": request.execution_trigger,
                "workflow_types": json.dumps(request.workflow_types),
                "status": "queued",
                "current_stage": "initialization",
                "progress_percentage": 0.0,
                "configuration": json.dumps(request.configuration),
                "started_at": datetime.now().isoformat(),
            }

            await self.db.create_master_workflow(workflow_data)

            # Track active session
            self.active_sessions[session_uuid] = {
                "status": "queued",
                "started_at": datetime.now(),
                "workflow_types": request.workflow_types,
            }

            # Execute workflows in background
            background_tasks.add_task(
                self._execute_workflows_background, session_uuid, request
            )

            return WorkflowStatusResponse(
                session_uuid=session_uuid,
                status="queued",
                current_stage="initialization",
                progress_percentage=0.0,
                started_at=datetime.now().isoformat(),
                configuration=request.configuration,
            )

        except Exception as e:
            logger.error(f"Failed to start workflow execution: {e}")
            raise HTTPException(
                status_code=500, detail=f"Workflow start failed: {str(e)}"
            )

    async def _execute_workflows_background(
        self, session_uuid: str, request: WorkflowExecutionRequest
    ):
        """
        Execute workflows in background with session tracking.
        """

        try:
            # Update session status
            await self._update_workflow_status(
                session_uuid, "processing", "workflow_execution", 10.0
            )
            self.active_sessions[session_uuid]["status"] = "processing"

            # Execute each workflow type
            results = {}
            total_workflows = len(request.workflow_types)

            for i, workflow_type in enumerate(request.workflow_types):

                progress = 10.0 + (i / total_workflows) * 80.0  # 10% to 90% range

                if workflow_type == "face_detection":
                    result = await self._execute_face_detection_workflow(
                        session_uuid, request, progress
                    )
                    results["face_detection"] = result

                elif workflow_type == "person_routes":
                    result = await self._execute_person_routes_workflow(
                        session_uuid, request, progress
                    )
                    results["person_routes"] = result

                else:
                    logger.warning(f"Unknown workflow type: {workflow_type}")

            # Complete workflow execution
            await self._complete_workflow_execution(session_uuid, results)

        except Exception as e:
            logger.error(
                f"Background workflow execution failed for session {session_uuid}: {e}"
            )
            await self._fail_workflow_execution(session_uuid, str(e))

    async def _execute_face_detection_workflow(
        self, session_uuid: str, request: WorkflowExecutionRequest, progress: float
    ) -> Dict:
        """Execute enhanced face detection workflow."""

        logger.info(f"Executing face detection workflow - Session: {session_uuid}")

        await self._update_workflow_status(
            session_uuid, "processing", "face_detection", progress
        )

        # Configure enhanced face detection
        detection_config = {
            "confidence_threshold": request.configuration.get(
                "confidence_threshold", 0.5
            ),
            "frames_per_second": request.configuration.get("frames_per_second", 3),
            "enable_distance_calculation": request.configuration.get(
                "enable_distance_calculation", True
            ),
            "enable_embedding_generation": request.configuration.get(
                "enable_embedding_generation", True
            ),
            "enable_route_tracking": request.configuration.get(
                "enable_route_tracking", True
            ),
            **request.configuration,
        }

        # Execute enhanced face detection
        result = await self.vision_service.start_session_based_face_detection(
            session_uuid=session_uuid,
            media_id=request.source_id,
            source_identifier=request.source_identifier,
            source_type=request.source_type,
            execution_trigger=request.execution_trigger,
            config=detection_config,
        )

        logger.info(
            f"Face detection completed - Session: {session_uuid}, "
            f"Faces: {result.get('faces_detected', 0)}"
        )

        return result

    async def _execute_person_routes_workflow(
        self, session_uuid: str, request: WorkflowExecutionRequest, progress: float
    ) -> Dict:
        """Execute person routes analytics workflow."""

        logger.info(f"Executing person routes workflow - Session: {session_uuid}")

        await self._update_workflow_status(
            session_uuid, "processing", "person_routes", progress
        )

        # Generate person routes from face detections
        routes_created = await self.vision_service._generate_person_routes(session_uuid)

        # Calculate spatial analytics
        spatial_analysis = await self._calculate_spatial_analytics(session_uuid)

        result = {
            "routes_created": routes_created,
            "spatial_analysis": spatial_analysis,
        }

        logger.info(
            f"Person routes completed - Session: {session_uuid}, "
            f"Routes: {routes_created}"
        )

        return result

    async def get_workflow_status(self, session_uuid: str) -> WorkflowStatusResponse:
        """Get current workflow status."""

        try:
            workflow = await self.db.get_master_workflow_by_session(session_uuid)

            if not workflow:
                raise HTTPException(
                    status_code=404, detail="Workflow session not found"
                )

            return WorkflowStatusResponse(
                session_uuid=workflow["session_uuid"],
                status=workflow["status"],
                current_stage=workflow["current_stage"],
                progress_percentage=workflow["progress_percentage"],
                started_at=workflow["started_at"],
                completed_at=workflow.get("completed_at"),
                total_faces_detected=workflow.get("total_faces_detected"),
                processing_duration_seconds=workflow.get("processing_duration_seconds"),
                error_message=workflow.get("error_message"),
                configuration=json.loads(workflow["configuration"]),
            )

        except Exception as e:
            logger.error(
                f"Failed to get workflow status for session {session_uuid}: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Status retrieval failed: {str(e)}"
            )

    async def get_person_routes_analytics(
        self, request: PersonRoutesRequest
    ) -> PersonRoutesResponse:
        """
        Get person routes analytics with spatial analysis.

        Phase 1 Features:
        - Route movement tracking
        - Spatial analysis (heatmaps, movement patterns)
        - Distance-based analytics
        - Velocity calculations
        """

        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=request.time_range_hours)

            # Get routes data
            if request.session_uuid:
                routes = await self.db.get_person_routes_by_session(
                    request.session_uuid,
                    confidence_threshold=request.confidence_threshold,
                )
            else:
                routes = await self.db.get_person_routes_by_time_range(
                    start_time=start_time,
                    end_time=end_time,
                    confidence_threshold=request.confidence_threshold,
                )

            # Calculate analytics
            total_routes = len(set([r["person_object_id"] for r in routes]))
            total_route_points = len(routes)
            unique_persons = len(set([r["person_object_id"] for r in routes]))

            # Spatial analysis
            spatial_analysis = None
            if request.include_spatial_analysis and routes:
                spatial_analysis = await self._calculate_spatial_analytics_from_routes(
                    routes
                )

            return PersonRoutesResponse(
                total_routes=total_routes,
                total_route_points=total_route_points,
                unique_persons=unique_persons,
                time_range_start=start_time.isoformat(),
                time_range_end=end_time.isoformat(),
                routes=routes,
                spatial_analysis=spatial_analysis,
            )

        except Exception as e:
            logger.error(f"Failed to get person routes analytics: {e}")
            raise HTTPException(
                status_code=500, detail=f"Analytics retrieval failed: {str(e)}"
            )

    async def search_similar_faces(
        self,
        embedding_vector: List[float],
        similarity_threshold: float = 0.8,
        limit: int = 10,
        session_uuid: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for similar faces using vector embeddings.

        Phase 1 Vector Search Implementation.
        """

        try:
            similar_faces = await self.db.search_similar_faces_by_embedding(
                embedding_vector=embedding_vector,
                similarity_threshold=similarity_threshold,
                limit=limit,
                session_uuid=session_uuid,
            )

            logger.info(
                f"Found {len(similar_faces)} similar faces with threshold {similarity_threshold}"
            )

            return similar_faces

        except Exception as e:
            logger.error(f"Failed to search similar faces: {e}")
            raise HTTPException(
                status_code=500, detail=f"Vector search failed: {str(e)}"
            )

    # ================================================================
    # Workflow Management Helpers
    # ================================================================

    async def _update_workflow_status(
        self,
        session_uuid: str,
        status: str,
        current_stage: str,
        progress_percentage: float,
    ):
        """Update workflow status in database."""

        update_data = {
            "status": status,
            "current_stage": current_stage,
            "progress_percentage": progress_percentage,
            "updated_at": datetime.now().isoformat(),
        }

        await self.db.update_master_workflow(session_uuid, update_data)

    async def _complete_workflow_execution(self, session_uuid: str, results: Dict):
        """Complete workflow execution with results."""

        # Calculate totals from all workflow results
        total_faces = sum([r.get("faces_detected", 0) for r in results.values()])
        total_routes = sum([r.get("routes_created", 0) for r in results.values()])

        # Calculate processing duration
        session_info = self.active_sessions.get(session_uuid, {})
        started_at = session_info.get("started_at", datetime.now())
        processing_duration = int((datetime.now() - started_at).total_seconds())

        update_data = {
            "status": "completed",
            "current_stage": "completed",
            "progress_percentage": 100.0,
            "completed_at": datetime.now().isoformat(),
            "total_faces_detected": total_faces,
            "processing_duration_seconds": processing_duration,
            "execution_results": json.dumps(results),
        }

        await self.db.update_master_workflow(session_uuid, update_data)

        # Clean up active session
        if session_uuid in self.active_sessions:
            del self.active_sessions[session_uuid]

        logger.info(
            f"Workflow execution completed - Session: {session_uuid}, "
            f"Faces: {total_faces}, Routes: {total_routes}"
        )

    async def _fail_workflow_execution(self, session_uuid: str, error_message: str):
        """Mark workflow execution as failed."""

        update_data = {
            "status": "failed",
            "current_stage": "error",
            "error_message": error_message,
            "completed_at": datetime.now().isoformat(),
        }

        await self.db.update_master_workflow(session_uuid, update_data)

        # Clean up active session
        if session_uuid in self.active_sessions:
            del self.active_sessions[session_uuid]

        logger.error(
            f"Workflow execution failed - Session: {session_uuid}: {error_message}"
        )

    # ================================================================
    # Spatial Analytics
    # ================================================================

    async def _calculate_spatial_analytics(self, session_uuid: str) -> Dict:
        """Calculate spatial analytics for a session."""

        routes = await self.db.get_person_routes_by_session(session_uuid)
        return await self._calculate_spatial_analytics_from_routes(routes)

    async def _calculate_spatial_analytics_from_routes(
        self, routes: List[Dict]
    ) -> Dict:
        """Calculate spatial analytics from route data."""

        if not routes:
            return {}

        import numpy as np

        # Extract coordinates and metrics
        x_coords = [r["center_x"] for r in routes]
        y_coords = [r["center_y"] for r in routes]
        velocities = [
            r["velocity_magnitude"] for r in routes if r["velocity_magnitude"] > 0
        ]
        distances = [
            r["distance_from_camera"] for r in routes if r.get("distance_from_camera")
        ]

        # Basic statistics
        analytics = {
            "coordinate_bounds": {
                "x_min": min(x_coords),
                "x_max": max(x_coords),
                "y_min": min(y_coords),
                "y_max": max(y_coords),
            },
            "movement_statistics": {
                "average_velocity": np.mean(velocities) if velocities else 0,
                "max_velocity": max(velocities) if velocities else 0,
                "total_movement_points": len(routes),
            },
            "distance_statistics": {
                "average_distance": np.mean(distances) if distances else None,
                "min_distance": min(distances) if distances else None,
                "max_distance": max(distances) if distances else None,
            },
        }

        # Heatmap generation (simplified)
        if len(x_coords) > 5:  # Minimum points for heatmap
            analytics["heatmap"] = await self._generate_simple_heatmap(
                x_coords, y_coords
            )

        return analytics

    async def _generate_simple_heatmap(
        self, x_coords: List[float], y_coords: List[float]
    ) -> Dict:
        """Generate simple heatmap data from coordinates."""

        import numpy as np

        # Create 10x10 grid for heatmap
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        if x_max == x_min or y_max == y_min:
            return {}

        # Create histogram
        heatmap, x_edges, y_edges = np.histogram2d(
            x_coords, y_coords, bins=10, range=[[x_min, x_max], [y_min, y_max]]
        )

        return {
            "grid_size": [10, 10],
            "x_range": [x_min, x_max],
            "y_range": [y_min, y_max],
            "density_values": heatmap.tolist(),
            "x_edges": x_edges.tolist(),
            "y_edges": y_edges.tolist(),
        }


# ================================================================
# FastAPI Router for Phase 1 Endpoints
# ================================================================


def create_phase1_router(
    workflow_controller: MasterLifecycleWorkflowController,
) -> APIRouter:
    """Create FastAPI router with Phase 1 endpoints."""

    router = APIRouter(prefix="/api/v1/workflows", tags=["Phase 1 Workflows"])

    @router.post("/execute", response_model=WorkflowStatusResponse)
    async def execute_workflow(
        request: WorkflowExecutionRequest, background_tasks: BackgroundTasks
    ):
        """
        Execute workflow with session-based processing.

        Phase 1 Features:
        - No duplicate prevention (unlimited re-executions)
        - Session UUID generation
        - Enhanced face detection with distance & embeddings
        - Person routes generation
        """
        return await workflow_controller.start_workflow_execution(
            request, background_tasks
        )

    @router.get("/status/{session_uuid}", response_model=WorkflowStatusResponse)
    async def get_workflow_status(session_uuid: str):
        """Get workflow execution status by session UUID."""
        return await workflow_controller.get_workflow_status(session_uuid)

    @router.post("/analytics/person-routes", response_model=PersonRoutesResponse)
    async def get_person_routes_analytics(request: PersonRoutesRequest):
        """
        Get person routes analytics with spatial analysis.

        Phase 1 Features:
        - Movement tracking
        - Spatial analysis and heatmaps
        - Distance-based analytics
        - Velocity calculations
        """
        return await workflow_controller.get_person_routes_analytics(request)

    @router.post("/search/similar-faces")
    async def search_similar_faces(
        embedding_vector: List[float],
        similarity_threshold: float = 0.8,
        limit: int = 10,
        session_uuid: Optional[str] = None,
    ):
        """
        Search for similar faces using vector embeddings.

        Phase 1 Vector Search with pgvector.
        """
        return await workflow_controller.search_similar_faces(
            embedding_vector, similarity_threshold, limit, session_uuid
        )

    @router.get("/sessions/active")
    async def get_active_sessions():
        """Get currently active workflow sessions."""
        return {
            "active_sessions": list(workflow_controller.active_sessions.keys()),
            "session_details": workflow_controller.active_sessions,
        }

    return router


# ================================================================
# Phase 1 Usage Example
# ================================================================


async def example_phase1_workflow():
    """Example of Phase 1 workflow execution."""

    # Initialize workflow controller
    workflow_controller = MasterLifecycleWorkflowController(
        database_client=db_client, vision_service=vision_service
    )

    # Create execution request
    request = WorkflowExecutionRequest(
        source_identifier="camera-lobby-main",
        source_type="camera_recording",
        source_id="media-12345",
        execution_trigger="automatic",
        workflow_types=["face_detection", "person_routes"],
        configuration={
            "confidence_threshold": 0.5,
            "frames_per_second": 3,
            "enable_distance_calculation": True,
            "enable_embedding_generation": True,
            "enable_route_tracking": True,
        },
    )

    # Execute workflow
    from fastapi import BackgroundTasks

    background_tasks = BackgroundTasks()

    result = await workflow_controller.start_workflow_execution(
        request, background_tasks
    )

    print(f"Workflow started: {result.session_uuid}")
    print(f"Status: {result.status}")

    # Check status later
    status = await workflow_controller.get_workflow_status(result.session_uuid)
    print(f"Current status: {status.status} - {status.current_stage}")

    # Get person routes analytics
    routes_request = PersonRoutesRequest(
        session_uuid=result.session_uuid, include_spatial_analysis=True
    )

    routes_analytics = await workflow_controller.get_person_routes_analytics(
        routes_request
    )
    print(
        f"Routes analytics: {routes_analytics.total_routes} routes, "
        f"{routes_analytics.total_route_points} points"
    )

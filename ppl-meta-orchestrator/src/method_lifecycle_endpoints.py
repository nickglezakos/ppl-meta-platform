"""
PPL Meta Orchestrator - Method Lifecycle API Endpoints
Phase 2.3 Implementation: API endpoints for method lifecycle management
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from method_lifecycle_manager import (
    MethodConfiguration,
    MethodLifecycleManager,
    MethodPerformanceMetrics,
    MethodPriority,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses


class MethodInitializationRequest(BaseModel):
    """Request model for initializing camera methods."""

    enabled_methods: Optional[List[str]] = Field(
        default=None, description="List of methods to enable (default: all available)"
    )


class MethodExecutionRequest(BaseModel):
    """Request model for executing method processing."""

    method_name: str = Field(description="Detection method to execute")
    media_id: str = Field(description="Media file identifier")
    processing_params: Dict[str, Any] = Field(
        default_factory=dict, description="Additional processing parameters"
    )


class MethodConfigurationUpdate(BaseModel):
    """Request model for updating method configuration."""

    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=4)
    max_retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[float] = Field(None, gt=0, le=300)
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class MethodStatusResponse(BaseModel):
    """Response model for method status."""

    method_name: str
    status: str
    metrics: Dict[str, Any]
    configuration: Dict[str, Any]
    is_active: bool


class CameraMethodsStatusResponse(BaseModel):
    """Response model for all methods on a camera."""

    camera_device_id: str
    methods: Dict[str, Dict[str, Any]]
    active_methods_count: int
    total_methods_count: int


class MethodLifecycleEndpoints:
    """API endpoints for method lifecycle management."""

    def __init__(self, lifecycle_manager: MethodLifecycleManager):
        """Initialize endpoints with lifecycle manager."""
        self.lifecycle_manager = lifecycle_manager
        self.router = APIRouter(prefix="/methods", tags=["Method Lifecycle"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes."""

        @self.router.post("/cameras/{camera_device_id}/initialize")
        async def initialize_camera_methods(
            camera_device_id: str,
            user_id: str = Query(..., description="User identifier"),
            request: MethodInitializationRequest = MethodInitializationRequest(),
        ):
            """Initialize detection methods for a camera."""
            try:
                configs = await self.lifecycle_manager.initialize_camera_methods(
                    camera_device_id=camera_device_id,
                    user_id=user_id,
                    enabled_methods=request.enabled_methods,
                )

                return {
                    "status": "success",
                    "message": f"Initialized {len(configs)} methods for camera",
                    "camera_device_id": camera_device_id,
                    "initialized_methods": list(configs.keys()),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error(
                    "Failed to initialize methods for camera %s: %s",
                    camera_device_id,
                    str(e),
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize camera methods: {str(e)}",
                )

        @self.router.post("/cameras/{camera_device_id}/execute")
        async def execute_method_processing(
            camera_device_id: str, request: MethodExecutionRequest
        ):
            """Execute processing for a specific method."""
            try:
                result = await self.lifecycle_manager.execute_method_processing(
                    camera_device_id=camera_device_id,
                    method_name=request.method_name,
                    media_id=request.media_id,
                    processing_params=request.processing_params,
                )

                return {
                    "status": "success",
                    "camera_device_id": camera_device_id,
                    "execution_result": result,
                }

            except Exception as e:
                logger.error(
                    "Method execution failed for camera %s, method %s: %s",
                    camera_device_id,
                    request.method_name,
                    str(e),
                )
                raise HTTPException(
                    status_code=500, detail=f"Method execution failed: {str(e)}"
                )

        @self.router.get("/cameras/{camera_device_id}/status")
        async def get_camera_methods_status(
            camera_device_id: str,
        ) -> CameraMethodsStatusResponse:
            """Get status of all methods for a camera."""
            try:
                status = await self.lifecycle_manager.get_method_status(
                    camera_device_id
                )

                if "error" in status:
                    raise HTTPException(status_code=404, detail=status["error"])

                return CameraMethodsStatusResponse(**status)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get camera methods status for %s: %s",
                    camera_device_id,
                    str(e),
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get camera methods status: {str(e)}",
                )

        @self.router.get("/cameras/{camera_device_id}/methods/{method_name}/status")
        async def get_method_status(
            camera_device_id: str, method_name: str
        ) -> MethodStatusResponse:
            """Get status of a specific method."""
            try:
                status = await self.lifecycle_manager.get_method_status(
                    camera_device_id, method_name
                )

                if "error" in status:
                    raise HTTPException(status_code=404, detail=status["error"])

                return MethodStatusResponse(**status)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get method status for %s/%s: %s",
                    camera_device_id,
                    method_name,
                    str(e),
                )
                raise HTTPException(
                    status_code=500, detail=f"Failed to get method status: {str(e)}"
                )

        @self.router.get("/cameras/{camera_device_id}/analytics")
        async def get_camera_analytics(camera_device_id: str):
            """Get comprehensive analytics for all methods on a camera."""
            try:
                analytics = await self.lifecycle_manager.get_camera_analytics(
                    camera_device_id
                )

                if "error" in analytics:
                    raise HTTPException(status_code=404, detail=analytics["error"])

                return analytics

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get camera analytics for %s: %s",
                    camera_device_id,
                    str(e),
                )
                raise HTTPException(
                    status_code=500, detail=f"Failed to get camera analytics: {str(e)}"
                )

        @self.router.put("/cameras/{camera_device_id}/methods/{method_name}/config")
        async def update_method_configuration(
            camera_device_id: str, method_name: str, request: MethodConfigurationUpdate
        ):
            """Update configuration for a specific method."""
            try:
                # Get current status to verify method exists
                status = await self.lifecycle_manager.get_method_status(
                    camera_device_id, method_name
                )

                if "error" in status:
                    raise HTTPException(status_code=404, detail=status["error"])

                # Update configuration
                config = self.lifecycle_manager.method_configs.get(
                    camera_device_id, {}
                ).get(method_name)

                if not config:
                    raise HTTPException(
                        status_code=404, detail="Method configuration not found"
                    )

                # Apply updates
                if request.enabled is not None:
                    config.enabled = request.enabled

                if request.priority is not None:
                    config.priority = MethodPriority(request.priority)

                if request.max_retry_attempts is not None:
                    config.max_retry_attempts = request.max_retry_attempts

                if request.timeout_seconds is not None:
                    config.timeout_seconds = request.timeout_seconds

                if request.confidence_threshold is not None:
                    config.confidence_threshold = request.confidence_threshold

                if request.quality_threshold is not None:
                    config.quality_threshold = request.quality_threshold

                return {
                    "status": "success",
                    "message": "Method configuration updated",
                    "camera_device_id": camera_device_id,
                    "method_name": method_name,
                    "updated_configuration": config.__dict__,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Failed to update method configuration for %s/%s: %s",
                    camera_device_id,
                    method_name,
                    str(e),
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update method configuration: {str(e)}",
                )

        @self.router.post("/cameras/{camera_device_id}/methods/{method_name}/reset")
        async def reset_method_metrics(camera_device_id: str, method_name: str):
            """Reset performance metrics for a specific method."""
            try:
                # Verify method exists
                status = await self.lifecycle_manager.get_method_status(
                    camera_device_id, method_name
                )

                if "error" in status:
                    raise HTTPException(status_code=404, detail=status["error"])

                # Reset metrics
                if (
                    camera_device_id in self.lifecycle_manager.method_metrics
                    and method_name
                    in self.lifecycle_manager.method_metrics[camera_device_id]
                ):

                    self.lifecycle_manager.method_metrics[camera_device_id][
                        method_name
                    ] = MethodPerformanceMetrics(method_name)

                return {
                    "status": "success",
                    "message": "Method metrics reset",
                    "camera_device_id": camera_device_id,
                    "method_name": method_name,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Failed to reset method metrics for %s/%s: %s",
                    camera_device_id,
                    method_name,
                    str(e),
                )
                raise HTTPException(
                    status_code=500, detail=f"Failed to reset method metrics: {str(e)}"
                )

        @self.router.get("/health")
        async def method_lifecycle_health():
            """Health check for method lifecycle management."""
            active_cameras = len(self.lifecycle_manager.method_states)
            total_methods = sum(
                len(methods)
                for methods in self.lifecycle_manager.method_states.values()
            )
            active_methods = sum(
                len(tasks) for tasks in self.lifecycle_manager.active_tasks.values()
            )

            return {
                "status": "healthy",
                "component": "method_lifecycle_manager",
                "capabilities": [
                    "method_initialization",
                    "method_execution",
                    "performance_tracking",
                    "error_handling",
                    "analytics",
                    "configuration_management",
                ],
                "statistics": {
                    "active_cameras": active_cameras,
                    "total_methods": total_methods,
                    "active_methods": active_methods,
                    "available_detection_methods": self.lifecycle_manager.available_methods,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        @self.router.get("/cameras/{camera_device_id}/methods/{method_name}/logs")
        async def get_method_execution_logs(
            camera_device_id: str,
            method_name: str,
            limit: int = Query(
                10, ge=1, le=100, description="Number of logs to return"
            ),
        ):
            """Get recent execution logs for a specific method."""
            try:
                # This would typically query a logging database
                # For now, return basic information from metrics
                status = await self.lifecycle_manager.get_method_status(
                    camera_device_id, method_name
                )

                if "error" in status:
                    raise HTTPException(status_code=404, detail=status["error"])

                metrics = status.get("metrics", {})

                return {
                    "camera_device_id": camera_device_id,
                    "method_name": method_name,
                    "recent_activity": {
                        "last_execution": metrics.get("last_execution_time"),
                        "last_success": metrics.get("last_success_time"),
                        "last_failure": metrics.get("last_failure_time"),
                        "current_status": status.get("status"),
                        "total_executions": metrics.get("total_executions", 0),
                        "success_rate": (
                            metrics.get("successful_executions", 0)
                            / max(metrics.get("total_executions", 1), 1)
                        ),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get method logs for %s/%s: %s",
                    camera_device_id,
                    method_name,
                    str(e),
                )
                raise HTTPException(
                    status_code=500, detail=f"Failed to get method logs: {str(e)}"
                )


# Create the router instance
def create_method_lifecycle_router(
    lifecycle_manager: MethodLifecycleManager,
) -> APIRouter:
    """Create and return the method lifecycle API router."""
    endpoints = MethodLifecycleEndpoints(lifecycle_manager)
    return endpoints.router

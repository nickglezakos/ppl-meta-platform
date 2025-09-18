"""
PPL Meta Orchestrator - Service Clients for Camera, Media, and Vision Services
Phase 1 Implementation: HTTP clients with full traceability support and lifecycle tracking
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ServiceResponse(BaseModel):
    """Standard response wrapper for service client calls."""

    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    trace_id: Optional[str] = None
    service_name: str
    endpoint: str
    timestamp: datetime


class TraceabilityContext(BaseModel):
    """Traceability context for cross-service tracking."""

    workflow_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: str
    parent_trace_id: Optional[str] = None
    source_service: str = "orchestrator"
    operation: str
    metadata: Dict[str, Any] = {}


class CameraServiceClient:
    """HTTP client for Camera Service integration with traceability."""

    def __init__(self, base_url: str = "http://localhost:8005", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.service_name = "camera"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        trace_ctx: TraceabilityContext,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> ServiceResponse:
        """Make HTTP request with traceability tracking."""
        start_time = datetime.now()
        url = urljoin(self.base_url, endpoint)

        headers = {
            "Content-Type": "application/json",
            "X-Trace-ID": trace_ctx.request_id,
            "X-Workflow-ID": trace_ctx.workflow_id,
            "X-Source-Service": trace_ctx.source_service,
            "X-Operation": trace_ctx.operation,
        }

        if trace_ctx.user_id:
            headers["X-User-ID"] = trace_ctx.user_id
        if trace_ctx.session_id:
            headers["X-Session-ID"] = trace_ctx.session_id
        if trace_ctx.parent_trace_id:
            headers["X-Parent-Trace-ID"] = trace_ctx.parent_trace_id

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                    method=method, url=url, json=data, params=params, headers=headers
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    response_data = (
                        await response.json()
                        if response.content_type == "application/json"
                        else None
                    )

                    return ServiceResponse(
                        success=response.status < 400,
                        status_code=response.status,
                        data=response_data,
                        error_message=(
                            None if response.status < 400 else str(response_data)
                        ),
                        response_time_ms=response_time,
                        trace_id=trace_ctx.request_id,
                        service_name=self.service_name,
                        endpoint=endpoint,
                        timestamp=start_time,
                    )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Camera Service request failed: {e}")
            return ServiceResponse(
                success=False,
                status_code=500,
                error_message=str(e),
                response_time_ms=response_time,
                trace_id=trace_ctx.request_id,
                service_name=self.service_name,
                endpoint=endpoint,
                timestamp=start_time,
            )

    async def start_recording(
        self,
        trace_ctx: TraceabilityContext,
        camera_device_id: str,
        recording_settings: Dict[str, Any],
    ) -> ServiceResponse:
        """Start camera recording with workflow traceability."""
        trace_ctx.operation = "start_recording"
        trace_ctx.metadata.update(
            {
                "camera_device_id": camera_device_id,
                "recording_settings": recording_settings,
            }
        )

        return await self._make_request(
            "POST",
            f"/api/v1/cameras/{camera_device_id}/start-recording",
            trace_ctx,
            data=recording_settings,
        )

    async def stop_recording(
        self, trace_ctx: TraceabilityContext, camera_device_id: str, session_id: str
    ) -> ServiceResponse:
        """Stop camera recording with workflow traceability."""
        trace_ctx.operation = "stop_recording"
        trace_ctx.metadata.update(
            {"camera_device_id": camera_device_id, "recording_session_id": session_id}
        )

        return await self._make_request(
            "POST",
            f"/api/v1/cameras/{camera_device_id}/stop-recording",
            trace_ctx,
            data={"session_id": session_id},
        )

    async def get_camera_settings(
        self, trace_ctx: TraceabilityContext, camera_device_id: str, user_id: str
    ) -> ServiceResponse:
        """Get user camera settings with traceability."""
        trace_ctx.operation = "get_camera_settings"
        trace_ctx.metadata.update(
            {"camera_device_id": camera_device_id, "settings_user_id": user_id}
        )

        return await self._make_request(
            "GET",
            f"/api/v1/cameras/{camera_device_id}/settings",
            trace_ctx,
            params={"user_id": user_id},
        )

    async def update_camera_settings(
        self,
        trace_ctx: TraceabilityContext,
        camera_device_id: str,
        user_id: str,
        settings: Dict[str, Any],
    ) -> ServiceResponse:
        """Update user camera settings with traceability."""
        trace_ctx.operation = "update_camera_settings"
        trace_ctx.metadata.update(
            {
                "camera_device_id": camera_device_id,
                "settings_user_id": user_id,
                "updated_settings": settings,
            }
        )

        return await self._make_request(
            "PUT",
            f"/api/v1/cameras/{camera_device_id}/settings",
            trace_ctx,
            data={"user_id": user_id, **settings},
        )

    async def get_recording_sessions(
        self, trace_ctx: TraceabilityContext, camera_device_id: str, limit: int = 50
    ) -> ServiceResponse:
        """Get camera recording sessions with traceability."""
        trace_ctx.operation = "get_recording_sessions"
        trace_ctx.metadata.update(
            {"camera_device_id": camera_device_id, "session_limit": limit}
        )

        return await self._make_request(
            "GET",
            f"/api/v1/cameras/{camera_device_id}/sessions",
            trace_ctx,
            params={"limit": limit},
        )


class MediaServiceClient:
    """HTTP client for Media Service integration with traceability."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.service_name = "media"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        trace_ctx: TraceabilityContext,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> ServiceResponse:
        """Make HTTP request with traceability tracking."""
        start_time = datetime.now()
        url = urljoin(self.base_url, endpoint)

        headers = {
            "Content-Type": "application/json",
            "X-Trace-ID": trace_ctx.request_id,
            "X-Workflow-ID": trace_ctx.workflow_id,
            "X-Source-Service": trace_ctx.source_service,
            "X-Operation": trace_ctx.operation,
        }

        if trace_ctx.user_id:
            headers["X-User-ID"] = trace_ctx.user_id
        if trace_ctx.session_id:
            headers["X-Session-ID"] = trace_ctx.session_id
        if trace_ctx.parent_trace_id:
            headers["X-Parent-Trace-ID"] = trace_ctx.parent_trace_id

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                    method=method, url=url, json=data, params=params, headers=headers
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    response_data = (
                        await response.json()
                        if response.content_type == "application/json"
                        else None
                    )

                    return ServiceResponse(
                        success=response.status < 400,
                        status_code=response.status,
                        data=response_data,
                        error_message=(
                            None if response.status < 400 else str(response_data)
                        ),
                        response_time_ms=response_time,
                        trace_id=trace_ctx.request_id,
                        service_name=self.service_name,
                        endpoint=endpoint,
                        timestamp=start_time,
                    )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Media Service request failed: {e}")
            return ServiceResponse(
                success=False,
                status_code=500,
                error_message=str(e),
                response_time_ms=response_time,
                trace_id=trace_ctx.request_id,
                service_name=self.service_name,
                endpoint=endpoint,
                timestamp=start_time,
            )

    async def register_video(
        self,
        trace_ctx: TraceabilityContext,
        file_path: str,
        camera_device_id: Optional[str] = None,
        recording_session_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> ServiceResponse:
        """Register video with Media Service including camera attribution."""
        trace_ctx.operation = "register_video"
        trace_ctx.metadata.update(
            {
                "file_path": file_path,
                "camera_device_id": camera_device_id,
                "recording_session_id": recording_session_id,
                "video_metadata": metadata or {},
            }
        )

        registration_data = {
            "file_path": file_path,
            "source": "camera" if camera_device_id else "upload",
            "metadata": metadata or {},
        }

        if camera_device_id:
            registration_data["camera_device_id"] = camera_device_id
        if recording_session_id:
            registration_data["recording_session_id"] = recording_session_id

        return await self._make_request(
            "POST", "/api/v1/media/register", trace_ctx, data=registration_data
        )

    async def get_media_info(
        self, trace_ctx: TraceabilityContext, media_id: str
    ) -> ServiceResponse:
        """Get media information with traceability."""
        trace_ctx.operation = "get_media_info"
        trace_ctx.metadata.update({"media_id": media_id})

        return await self._make_request("GET", f"/api/v1/media/{media_id}", trace_ctx)

    async def get_media_by_camera(
        self, trace_ctx: TraceabilityContext, camera_device_id: str, limit: int = 50
    ) -> ServiceResponse:
        """Get media files by camera device with traceability."""
        trace_ctx.operation = "get_media_by_camera"
        trace_ctx.metadata.update(
            {"camera_device_id": camera_device_id, "media_limit": limit}
        )

        return await self._make_request(
            "GET",
            f"/api/v1/media/camera/{camera_device_id}",
            trace_ctx,
            params={"limit": limit},
        )

    async def update_media_metadata(
        self,
        trace_ctx: TraceabilityContext,
        media_id: str,
        metadata_updates: Dict[str, Any],
    ) -> ServiceResponse:
        """Update media metadata with traceability."""
        trace_ctx.operation = "update_media_metadata"
        trace_ctx.metadata.update(
            {"media_id": media_id, "metadata_updates": metadata_updates}
        )

        return await self._make_request(
            "PATCH",
            f"/api/v1/media/{media_id}/metadata",
            trace_ctx,
            data=metadata_updates,
        )


class VisionServiceClient:
    """HTTP client for Vision Service integration with method-specific lifecycle tracking."""

    def __init__(self, base_url: str = "http://localhost:8003", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.service_name = "vision"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        trace_ctx: TraceabilityContext,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> ServiceResponse:
        """Make HTTP request with traceability tracking."""
        start_time = datetime.now()
        url = urljoin(self.base_url, endpoint)

        headers = {
            "Content-Type": "application/json",
            "X-Trace-ID": trace_ctx.request_id,
            "X-Workflow-ID": trace_ctx.workflow_id,
            "X-Source-Service": trace_ctx.source_service,
            "X-Operation": trace_ctx.operation,
        }

        if trace_ctx.user_id:
            headers["X-User-ID"] = trace_ctx.user_id
        if trace_ctx.session_id:
            headers["X-Session-ID"] = trace_ctx.session_id
        if trace_ctx.parent_trace_id:
            headers["X-Parent-Trace-ID"] = trace_ctx.parent_trace_id

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                    method=method, url=url, json=data, params=params, headers=headers
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    response_data = (
                        await response.json()
                        if response.content_type == "application/json"
                        else None
                    )

                    return ServiceResponse(
                        success=response.status < 400,
                        status_code=response.status,
                        data=response_data,
                        error_message=(
                            None if response.status < 400 else str(response_data)
                        ),
                        response_time_ms=response_time,
                        trace_id=trace_ctx.request_id,
                        service_name=self.service_name,
                        endpoint=endpoint,
                        timestamp=start_time,
                    )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Vision Service request failed: {e}")
            return ServiceResponse(
                success=False,
                status_code=500,
                error_message=str(e),
                response_time_ms=response_time,
                trace_id=trace_ctx.request_id,
                service_name=self.service_name,
                endpoint=endpoint,
                timestamp=start_time,
            )

    async def start_face_detection(
        self,
        trace_ctx: TraceabilityContext,
        media_id: str,
        method: str = "mtcnn",
        camera_device_id: Optional[str] = None,
        processing_options: Optional[Dict] = None,
    ) -> ServiceResponse:
        """Start face detection processing with method-specific lifecycle tracking."""
        trace_ctx.operation = "start_face_detection"
        trace_ctx.metadata.update(
            {
                "media_id": media_id,
                "detection_method": method,
                "camera_device_id": camera_device_id,
                "processing_options": processing_options or {},
            }
        )

        detection_data = {
            "media_id": media_id,
            "method": method,
            "options": processing_options or {},
        }

        if camera_device_id:
            detection_data["camera_device_id"] = camera_device_id

        return await self._make_request(
            "POST", "/api/v1/face-detection/process", trace_ctx, data=detection_data
        )

    async def get_processing_status(
        self, trace_ctx: TraceabilityContext, lifecycle_id: str
    ) -> ServiceResponse:
        """Get processing status with lifecycle tracking."""
        trace_ctx.operation = "get_processing_status"
        trace_ctx.metadata.update({"lifecycle_id": lifecycle_id})

        return await self._make_request(
            "GET", f"/api/v1/face-detection/status/{lifecycle_id}", trace_ctx
        )

    async def get_detection_results(
        self,
        trace_ctx: TraceabilityContext,
        media_id: str,
        method: Optional[str] = None,
        lifecycle_id: Optional[str] = None,
    ) -> ServiceResponse:
        """Get face detection results with method-specific filtering."""
        trace_ctx.operation = "get_detection_results"
        trace_ctx.metadata.update(
            {
                "media_id": media_id,
                "method_filter": method,
                "lifecycle_id": lifecycle_id,
            }
        )

        params = {}
        if method:
            params["method"] = method
        if lifecycle_id:
            params["lifecycle_id"] = lifecycle_id

        return await self._make_request(
            "GET",
            f"/api/v1/face-detection/results/{media_id}",
            trace_ctx,
            params=params,
        )

    async def get_method_lifecycles(
        self, trace_ctx: TraceabilityContext, media_id: str
    ) -> ServiceResponse:
        """Get all method-specific lifecycles for a media file."""
        trace_ctx.operation = "get_method_lifecycles"
        trace_ctx.metadata.update({"media_id": media_id})

        return await self._make_request(
            "GET", f"/api/v1/face-detection/lifecycles/{media_id}", trace_ctx
        )

    async def get_camera_analytics(
        self,
        trace_ctx: TraceabilityContext,
        camera_device_id: str,
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
    ) -> ServiceResponse:
        """Get camera-specific face detection analytics."""
        trace_ctx.operation = "get_camera_analytics"
        trace_ctx.metadata.update(
            {
                "camera_device_id": camera_device_id,
                "time_range_start": time_range_start,
                "time_range_end": time_range_end,
            }
        )

        params = {"camera_device_id": camera_device_id}
        if time_range_start:
            params["start"] = time_range_start
        if time_range_end:
            params["end"] = time_range_end

        return await self._make_request(
            "GET", "/api/v1/face-detection/analytics/camera", trace_ctx, params=params
        )


class ServiceClientManager:
    """Manager for all service clients with centralized configuration."""

    def __init__(
        self,
        camera_base_url: str = "http://localhost:8005",
        media_base_url: str = "http://localhost:8000",
        vision_base_url: str = "http://localhost:8003",
        default_timeout: int = 30,
    ):
        self.camera = CameraServiceClient(camera_base_url, default_timeout)
        self.media = MediaServiceClient(media_base_url, default_timeout)
        self.vision = VisionServiceClient(vision_base_url, max(default_timeout, 120))

    def create_trace_context(
        self,
        workflow_id: str,
        operation: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_trace_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> TraceabilityContext:
        """Create standardized traceability context."""
        return TraceabilityContext(
            workflow_id=workflow_id,
            user_id=user_id,
            session_id=session_id,
            request_id=str(uuid.uuid4()),
            parent_trace_id=parent_trace_id,
            source_service="orchestrator",
            operation=operation,
            metadata=metadata or {},
        )

    async def health_check_all(self) -> Dict[str, ServiceResponse]:
        """Health check all services with traceability."""
        health_workflow_id = str(uuid.uuid4())

        async def check_service(
            name: str,
            client: Union[CameraServiceClient, MediaServiceClient, VisionServiceClient],
        ):
            trace_ctx = self.create_trace_context(
                workflow_id=health_workflow_id, operation="health_check"
            )
            return await client._make_request("GET", "/health", trace_ctx)

        # Run health checks in parallel
        results = await asyncio.gather(
            check_service("camera", self.camera),
            check_service("media", self.media),
            check_service("vision", self.vision),
            return_exceptions=True,
        )

        return {
            "camera": results[0] if not isinstance(results[0], Exception) else None,
            "media": results[1] if not isinstance(results[1], Exception) else None,
            "vision": results[2] if not isinstance(results[2], Exception) else None,
        }

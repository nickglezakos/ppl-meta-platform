"""
PPL Meta Vision Service - Data Models
Enhanced models for media processing pipeline with database integration
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Base Models
class BaseResponse(BaseModel):
    """Base response model with common fields."""

    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(default=None, description="Status message")
    timestamp: datetime = Field(default_factory=datetime.now)


# Face Detection Models
class FaceDetectionRequest(BaseModel):
    """Request model for face detection."""

    image_base64: str = Field(..., description="Base64 encoded image")
    methods: Optional[List[str]] = Field(default=None, description="Detection methods")
    confidence_threshold: Optional[float] = Field(
        default=0.5, description="Confidence threshold"
    )


class FaceDetection(BaseModel):
    """Model for a single face detection."""

    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., description="Detection confidence score")
    method: str = Field(..., description="Detection method used")


class FaceDetectionResponse(BaseResponse):
    """Response model for face detection."""

    detections: List[FaceDetection] = Field(..., description="List of detected faces")
    processing_time: float = Field(..., description="Processing time in seconds")
    method_results: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed results per method"
    )


# Media Processing Models
class MediaProcessingRequest(BaseModel):
    """Request to process media from Media Service."""

    media_id: str = Field(..., description="Media ID from Media Service")
    media_type: str = Field(..., description="Type: 'image' or 'video'")
    media_url: str = Field(..., description="URL to fetch media from Media Service")
    processing_options: Optional[Dict[str, Any]] = Field(
        default=None, description="Processing options"
    )
    store_results: bool = Field(
        default=True, description="Whether to store results in database"
    )


class VideoFrame(BaseModel):
    """Model for video frame information."""

    frame_number: int = Field(..., description="Frame number in video")
    timestamp: float = Field(..., description="Timestamp in seconds")
    width: int = Field(..., description="Frame width")
    height: int = Field(..., description="Frame height")


class FaceDetectionResult(BaseModel):
    """Individual face detection result with metadata."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique detection ID"
    )
    media_id: str = Field(..., description="Source media ID")
    media_type: str = Field(..., description="Media type (image/video)")
    frame_number: Optional[int] = Field(
        default=None, description="Frame number for video"
    )
    timestamp: Optional[float] = Field(
        default=None, description="Timestamp in video (seconds)"
    )
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., description="Detection confidence")
    method: str = Field(..., description="Detection method used")
    frame_width: Optional[int] = Field(default=None, description="Detection frame width in pixels")
    frame_height: Optional[int] = Field(default=None, description="Detection frame height in pixels")
    frame_info: Optional[VideoFrame] = Field(default=None, description="Frame metadata")
    created_at: datetime = Field(default_factory=datetime.now)


class MediaProcessingResponse(BaseResponse):
    """Response from media processing."""

    media_id: str = Field(..., description="Processed media ID")
    media_type: str = Field(..., description="Media type processed")
    total_faces: int = Field(..., description="Total faces detected")
    total_frames: Optional[int] = Field(
        default=None, description="Total frames processed (video)"
    )
    processing_time: float = Field(..., description="Total processing time")
    detections: List[FaceDetectionResult] = Field(
        ..., description="All face detections"
    )
    video_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Video metadata"
    )


# Database Models
class FaceDetectionSession(BaseModel):
    """Database model for face detection sessions."""

    session_uuid: str = Field(..., description="Unique session identifier")
    media_uuid: str = Field(..., description="Associated media UUID")
    camera_device_uuid: str = Field(..., description="Camera device UUID")
    session_type: str = Field(
        ..., description="Session type (streaming, batch, realtime)"
    )
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = Field(default=None)
    processing_status: str = Field(default="active", description="Session status")
    total_faces_detected: int = Field(default=0, description="Total faces detected")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Session metadata"
    )


class MediaRecord(BaseModel):
    """Database model for media records."""

    media_id: str = Field(..., description="Unique media identifier")
    media_type: str = Field(..., description="Media type (image/video)")
    media_url: str = Field(..., description="Original media URL")
    processing_status: str = Field(default="pending", description="Processing status")
    total_faces: int = Field(default=0, description="Total faces detected")
    total_frames: Optional[int] = Field(
        default=None, description="Total frames (video)"
    )
    video_duration: Optional[float] = Field(
        default=None, description="Video duration (seconds)"
    )
    video_fps: Optional[float] = Field(default=None, description="Video FPS")
    processed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)


class FaceRecord(BaseModel):
    """Database model for face detection records."""

    id: str = Field(..., description="Unique detection ID")
    media_id: str = Field(..., description="Source media ID")
    frame_number: Optional[int] = Field(default=None)
    timestamp: Optional[float] = Field(default=None)
    bbox_x1: int = Field(..., description="Bounding box left")
    bbox_y1: int = Field(..., description="Bounding box top")
    bbox_x2: int = Field(..., description="Bounding box right")
    bbox_y2: int = Field(..., description="Bounding box bottom")
    confidence: float = Field(..., description="Detection confidence")
    method: str = Field(..., description="Detection method")
    created_at: datetime = Field(default_factory=datetime.now)


# Overlay Models
class OverlayRequest(BaseModel):
    """Request for overlay data."""

    media_id: str = Field(..., description="Media ID")
    frame_number: Optional[int] = Field(
        default=None, description="Specific frame for video"
    )
    timestamp: Optional[float] = Field(default=None, description="Timestamp for video")
    confidence_threshold: Optional[float] = Field(
        default=0.5, description="Minimum confidence"
    )
    overlay_style: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom overlay styling"
    )


class OverlayRectangle(BaseModel):
    """Individual overlay rectangle."""

    id: str = Field(..., description="Detection ID")
    bbox: List[int] = Field(..., description="Bounding box coordinates")
    confidence: float = Field(..., description="Detection confidence")
    method: str = Field(..., description="Detection method")
    style: Dict[str, Any] = Field(..., description="CSS-like styling")
    frame_number: Optional[int] = Field(default=None)
    timestamp: Optional[float] = Field(default=None)


class OverlayResponse(BaseResponse):
    """Response with overlay data for media player."""

    media_id: str = Field(..., description="Media ID")
    overlays: List[OverlayRectangle] = Field(..., description="Overlay rectangles")
    frame_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Frame information"
    )
    video_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Video metadata"
    )


class TimelineRequest(BaseModel):
    """Request for face detection timeline."""

    media_id: str = Field(..., description="Media ID")
    confidence_threshold: Optional[float] = Field(default=0.5)
    time_resolution: Optional[float] = Field(
        default=1.0, description="Time resolution in seconds"
    )


class TimelineSegment(BaseModel):
    """Timeline segment with face detections."""

    start_time: float = Field(..., description="Segment start time")
    end_time: float = Field(..., description="Segment end time")
    face_count: int = Field(..., description="Number of faces in segment")
    max_confidence: float = Field(..., description="Highest confidence in segment")
    detections: List[str] = Field(..., description="Detection IDs in segment")


class TimelineResponse(BaseResponse):
    """Timeline response for video scrubbing."""

    media_id: str = Field(..., description="Media ID")
    total_duration: Optional[float] = Field(
        default=None, description="Total video duration"
    )
    timeline: List[TimelineSegment] = Field(..., description="Timeline segments")
    summary: Dict[str, Any] = Field(..., description="Timeline summary statistics")


# Service Health Models
class ServiceHealth(BaseModel):
    """Service health status."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    models_loaded: bool = Field(..., description="Whether models are loaded")
    available_methods: List[str] = Field(..., description="Available detection methods")
    database_status: str = Field(
        default="unknown", description="Database connection status"
    )
    media_service_status: str = Field(
        default="unknown", description="Media service connectivity"
    )


# Batch Processing Models
class BatchProcessingRequest(BaseModel):
    """Request for batch media processing."""

    media_ids: List[str] = Field(..., description="List of media IDs to process")
    processing_options: Optional[Dict[str, Any]] = Field(default=None)
    priority: Optional[str] = Field(default="normal", description="Processing priority")


class BatchProcessingResponse(BaseResponse):
    """Response for batch processing."""

    job_id: str = Field(..., description="Batch job ID")
    total_media: int = Field(..., description="Total media items to process")
    estimated_time: Optional[float] = Field(
        default=None, description="Estimated processing time"
    )
    status: str = Field(default="queued", description="Job status")


# Analytics Models
class MediaAnalytics(BaseModel):
    """Analytics for processed media."""

    media_id: str = Field(..., description="Media ID")
    total_faces: int = Field(..., description="Total faces detected")
    unique_faces: Optional[int] = Field(
        default=None, description="Estimated unique faces"
    )
    face_density: float = Field(..., description="Faces per frame/second")
    confidence_stats: Dict[str, float] = Field(..., description="Confidence statistics")
    method_performance: Dict[str, Dict[str, Any]] = Field(
        ..., description="Method performance"
    )
    processing_stats: Dict[str, Any] = Field(..., description="Processing statistics")

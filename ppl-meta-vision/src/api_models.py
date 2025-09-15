"""
PPL Meta Vision Service - Pydantic API Models for Session-Based Face Detection
Enhanced API models for Workflow 4 session management

These models define the API request/response structures for session-based
face detection functionality. They work with the SQLAlchemy models to provide
type-safe API endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


# Base Response Models
class BaseAPIResponse(BaseModel):
    """Base response model with common fields."""

    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(default=None, description="Status message")
    timestamp: datetime = Field(default_factory=datetime.now)


# Session Management Models
class FaceDetectionSessionModel(BaseModel):
    """Data model for face detection session."""

    session_uuid: str = Field(..., description="Unique session identifier")
    media_uuid: str = Field(..., description="Associated media UUID")
    camera_device_uuid: Optional[str] = Field(
        default=None, description="Camera device UUID"
    )
    session_type: str = Field(..., description="Session type")
    started_at: datetime = Field(..., description="Session start time")
    ended_at: Optional[datetime] = Field(default=None, description="Session end time")
    processing_status: str = Field(..., description="Current processing status")
    total_faces_detected: int = Field(default=0, description="Total faces detected")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Session metadata"
    )


class MediaProcessingStatusModel(BaseModel):
    """Data model for media processing status."""

    media_uuid: str = Field(..., description="Media UUID")
    processing_status: str = Field(..., description="Processing status")
    total_faces_detected: int = Field(default=0, description="Total faces detected")
    processing_started_at: Optional[datetime] = Field(default=None)
    processing_completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class FaceDetectionSessionRequest(BaseModel):
    """Request model to create a new face detection session."""

    session_uuid: Optional[str] = Field(
        default=None,
        description="Optional session UUID (auto-generated if not provided)",
    )
    media_uuid: str = Field(..., description="Media file UUID being processed")
    camera_device_uuid: Optional[str] = Field(
        default=None, description="Optional camera device UUID that captured the media"
    )
    session_type: str = Field(
        default="streaming",
        description="Session type: 'streaming' or 'bulk_processing'",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional session metadata"
    )

    @validator("session_uuid", pre=True, always=True)
    def validate_session_uuid(cls, v):
        """Generate UUID if not provided, validate format if provided."""
        if v is None:
            return str(uuid.uuid4())

        # Validate UUID format
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid UUID format")

    @validator("session_type")
    def validate_session_type(cls, v):
        """Validate session type."""
        if v not in ["streaming", "bulk_processing"]:
            raise ValueError("session_type must be 'streaming' or 'bulk_processing'")
        return v

    @validator("media_uuid", "camera_device_uuid")
    def validate_uuids(cls, v):
        """Validate UUID format for media and camera device UUIDs."""
        if v is not None:
            try:
                uuid.UUID(v)
                return v
            except ValueError:
                raise ValueError("Invalid UUID format")
        return v


class FaceDetectionSessionResponse(BaseAPIResponse):
    """Response model for face detection session creation."""

    session_uuid: str = Field(..., description="Created session UUID")
    media_uuid: str = Field(..., description="Media file UUID")
    camera_device_uuid: Optional[str] = Field(
        default=None, description="Camera device UUID"
    )
    session_type: str = Field(..., description="Session type")
    started_at: datetime = Field(..., description="Session start timestamp")
    processing_status: str = Field(..., description="Current session status")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Session metadata"
    )


class FaceDetectionSessionDetailResponse(FaceDetectionSessionResponse):
    """Detailed response model for session information."""

    ended_at: Optional[datetime] = Field(
        default=None, description="Session end timestamp"
    )
    total_faces_detected: int = Field(
        default=0, description="Total faces detected in session"
    )
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    duration_seconds: Optional[float] = Field(
        default=None, description="Session duration in seconds (if completed)"
    )


class CloseSessionRequest(BaseModel):
    """Request model to close a face detection session."""

    total_faces: int = Field(
        ..., ge=0, description="Total number of faces detected in the session"
    )
    final_status: str = Field(
        default="completed", description="Final session status: 'completed' or 'failed'"
    )

    @validator("final_status")
    def validate_final_status(cls, v):
        """Validate final session status."""
        if v not in ["completed", "failed"]:
            raise ValueError("final_status must be 'completed' or 'failed'")
        return v


class SessionCompleteRequest(BaseModel):
    """Request model to complete a face detection session."""

    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Final session metadata"
    )


class SessionCompleteResponse(BaseAPIResponse):
    """Response model for session completion."""

    session_uuid: str = Field(..., description="Completed session UUID")
    total_faces_detected: int = Field(..., description="Total faces detected")
    session_duration: float = Field(..., description="Session duration in seconds")
    ended_at: datetime = Field(..., description="Session end timestamp")


class SessionErrorResponse(BaseAPIResponse):
    """Response model for session errors."""

    session_uuid: Optional[str] = Field(
        default=None, description="Session UUID if available"
    )
    error_code: str = Field(..., description="Error code")
    error_details: Optional[Dict[str, Any]] = Field(default=None)


# Face Detection Models
class FaceDetectionWithSessionRequest(BaseModel):
    """Request model to store face detection with session context."""

    session_uuid: str = Field(..., description="Associated session UUID")
    frame_number: Optional[int] = Field(
        default=None, ge=0, description="Frame number in video"
    )
    timestamp: Optional[float] = Field(
        default=None, ge=0.0, description="Timestamp in video (seconds)"
    )
    bbox: List[int] = Field(
        ...,
        min_items=4,
        max_items=4,
        description="Bounding box coordinates [x1, y1, x2, y2]",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Detection confidence score"
    )
    method: str = Field(..., description="Detection method used")

    @validator("bbox")
    def validate_bbox(cls, v):
        """Validate bounding box coordinates."""
        if len(v) != 4:
            raise ValueError("bbox must have exactly 4 coordinates")

        x1, y1, x2, y2 = v
        if x2 <= x1 or y2 <= y1:
            raise ValueError("Invalid bounding box: x2 > x1 and y2 > y1 required")

        if any(coord < 0 for coord in v):
            raise ValueError("Bounding box coordinates must be non-negative")

        return v

    @validator("session_uuid")
    def validate_session_uuid(cls, v):
        """Validate session UUID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid session UUID format")


class FaceDetectionResponse(BaseModel):
    """Response model for face detection storage."""

    face_id: str = Field(..., description="Unique face detection ID")
    session_uuid: str = Field(..., description="Associated session UUID")
    media_id: str = Field(..., description="Media file ID")
    frame_number: Optional[int] = Field(default=None, description="Frame number")
    timestamp: Optional[float] = Field(default=None, description="Timestamp")
    bbox: List[int] = Field(..., description="Bounding box coordinates")
    confidence: float = Field(..., description="Detection confidence")
    method: str = Field(..., description="Detection method")
    created_at: datetime = Field(..., description="Creation timestamp")


# Media Processing Status Models
class MediaProcessingStatusResponse(BaseAPIResponse):
    """Response model for media processing status."""

    media_uuid: str = Field(..., description="Media file UUID")
    face_detection_processed: bool = Field(
        ..., description="Whether face detection has been completed"
    )
    face_detection_session_uuid: Optional[str] = Field(
        default=None, description="Associated processing session UUID"
    )
    processing_completed_at: Optional[datetime] = Field(
        default=None, description="Processing completion timestamp"
    )
    total_frames_processed: Optional[int] = Field(
        default=None, description="Total number of frames processed"
    )
    total_faces_detected: Optional[int] = Field(
        default=None, description="Total faces detected during processing"
    )
    processing_method: Optional[str] = Field(
        default=None, description="Detection method used for processing"
    )
    last_updated: datetime = Field(..., description="Last update timestamp")
    status: str = Field(..., description="Processing status: processed/unprocessed")


class CompleteProcessingRequest(BaseModel):
    """Request model to mark media as fully processed."""

    session_uuid: str = Field(..., description="Processing session UUID")
    total_frames: int = Field(..., ge=0, description="Total number of frames processed")
    total_faces: int = Field(..., ge=0, description="Total faces detected")
    method: str = Field(..., description="Detection method used")

    @validator("session_uuid")
    def validate_session_uuid(cls, v):
        """Validate session UUID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid session UUID format")


# Frame-Indexed Face Data Models
class FrameFaceDataResponse(BaseAPIResponse):
    """Response model for frame-indexed face detection data."""

    media_uuid: str = Field(..., description="Media file UUID")
    total_frames: int = Field(..., description="Total number of frames with faces")
    face_data: Dict[str, List[Dict[str, Union[List[int], float]]]] = Field(
        ..., description="Face data organized by frame number"
    )
    session_uuid: Optional[str] = Field(
        default=None, description="Associated session UUID"
    )


# Analytics Models
class SessionAnalyticsResponse(BaseAPIResponse):
    """Response model for session analytics."""

    session_uuid: str = Field(..., description="Session UUID")
    media_uuid: str = Field(..., description="Media file UUID")
    camera_device_uuid: Optional[str] = Field(
        default=None, description="Camera device UUID"
    )
    total_faces: int = Field(..., description="Total faces detected")
    session_duration: Optional[float] = Field(
        default=None, description="Session duration in seconds"
    )
    avg_confidence: float = Field(..., description="Average detection confidence")
    faces_per_frame: Dict[int, int] = Field(
        ..., description="Number of faces detected per frame"
    )
    detection_method: Optional[str] = Field(
        default=None, description="Detection method used"
    )
    session_type: str = Field(..., description="Session type")
    processing_status: str = Field(..., description="Session status")


class MediaFaceTimelineResponse(BaseAPIResponse):
    """Response model for media face detection timeline."""

    media_uuid: str = Field(..., description="Media file UUID")
    total_sessions: int = Field(..., description="Total number of sessions")
    session_timeline: List[SessionAnalyticsResponse] = Field(
        ..., description="Timeline of all sessions for this media"
    )


class DeviceTraceabilityResponse(BaseAPIResponse):
    """Response model for camera device traceability."""

    camera_device_uuid: str = Field(..., description="Camera device UUID")
    total_sessions: int = Field(..., description="Total sessions from this device")
    total_faces_detected: int = Field(
        ..., description="Total faces detected from this device"
    )
    unique_media_files: int = Field(
        ..., description="Number of unique media files from this device"
    )
    media_files: List[str] = Field(
        ..., description="List of media file UUIDs from this device"
    )
    sessions: List[Dict[str, Any]] = Field(
        ..., description="Session summary information"
    )


# Error Response Models
class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationErrorResponse(ErrorResponse):
    """Validation error response model."""

    error: str = Field(default="validation_error", description="Error type")
    validation_errors: List[Dict[str, Any]] = Field(
        ..., description="List of validation errors"
    )


# Health Check Models
class SessionHealthResponse(BaseAPIResponse):
    """Response model for session management health check."""

    active_sessions: int = Field(..., description="Number of active sessions")
    completed_sessions_24h: int = Field(
        ..., description="Sessions completed in last 24 hours"
    )
    failed_sessions_24h: int = Field(
        ..., description="Sessions failed in last 24 hours"
    )
    total_faces_stored_24h: int = Field(
        ..., description="Total faces stored in last 24 hours"
    )
    database_connection: bool = Field(..., description="Database connection status")
    average_session_duration: Optional[float] = Field(
        default=None, description="Average session duration in seconds"
    )


# Batch Operations Models
class BatchFaceDetectionRequest(BaseModel):
    """Request model for batch face detection storage."""

    session_uuid: str = Field(..., description="Associated session UUID")
    faces: List[FaceDetectionWithSessionRequest] = Field(
        ..., min_items=1, description="List of face detections to store"
    )

    @validator("session_uuid")
    def validate_session_uuid(cls, v):
        """Validate session UUID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid session UUID format")


class BatchFaceDetectionResponse(BaseAPIResponse):
    """Response model for batch face detection storage."""

    session_uuid: str = Field(..., description="Associated session UUID")
    faces_stored: int = Field(..., description="Number of faces successfully stored")
    faces_failed: int = Field(
        default=0, description="Number of faces that failed to store"
    )
    face_ids: List[str] = Field(..., description="List of created face detection IDs")
    errors: Optional[List[str]] = Field(
        default=None, description="List of errors for failed faces"
    )


# Configuration for Pydantic models
class Config:
    """Pydantic configuration."""

    # Allow population by field name or alias
    allow_population_by_field_name = True

    # Validate assignment
    validate_assignment = True

    # Use enum values
    use_enum_values = True

    # JSON encoders for special types
    json_encoders = {datetime: lambda v: v.isoformat()}


# Apply configuration to all models
for model_name in dir():
    model = globals()[model_name]
    if isinstance(model, type) and issubclass(model, BaseModel) and model != BaseModel:
        if not hasattr(model, "Config"):
            model.Config = Config

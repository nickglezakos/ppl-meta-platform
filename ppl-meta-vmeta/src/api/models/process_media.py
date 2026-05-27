"""
Process Media API Models

Pydantic models for the single-media MVR processing endpoint.
This endpoint processes photos and videos independently to generate MVR people
without cross-media merging.

Author: PPL Meta Platform
Date: November 29, 2025
Version: 1.0.0
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ============================================================================
# Request Models
# ============================================================================

class ProcessingOptions(BaseModel):
    """Processing configuration options."""
    
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.50,
        le=0.95,
        description="Minimum cosine similarity for matching faces within the same media"
    )
    
    min_face_quality: float = Field(
        default=0.20,
        ge=0.10,
        le=0.95,
        description="Minimum quality score for face detection to be included"
    )
    
    include_demographics: bool = Field(
        default=True,
        description="Whether to estimate age and gender for detected faces"
    )
    
    include_route_data: bool = Field(
        default=True,
        description="Whether to include movement tracking data"
    )
    
    async_processing: bool = Field(
        default=False,
        description="Process asynchronously in background (return immediately with job ID)"
    )


class ResponseFormat(BaseModel):
    """Response format configuration."""
    
    include_embeddings: bool = Field(
        default=False,
        description="Include 512-dimensional face embeddings in response"
    )
    
    include_face_crops: bool = Field(
        default=False,
        description="Include base64-encoded face crop images"
    )
    
    aggregate_statistics: bool = Field(
        default=True,
        description="Include summary statistics across all processed media"
    )


class ProcessMediaRequest(BaseModel):
    """Request to process media independently for MVR people."""
    
    media_uuids: List[str] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="List of media UUIDs to process independently (photos or videos)"
    )
    
    processing_options: Optional[ProcessingOptions] = Field(
        default_factory=ProcessingOptions,
        description="Processing configuration"
    )
    
    response_format: Optional[ResponseFormat] = Field(
        default_factory=ResponseFormat,
        description="Response format configuration"
    )
    
    @validator('media_uuids')
    def validate_media_uuids(cls, v):
        """Validate media UUIDs."""
        if len(v) > 50:
            raise ValueError("Maximum 50 media UUIDs per request")
        if len(v) < 1:
            raise ValueError("At least 1 media UUID required")
        return v


class PersistedPersonObjectsMaterializationRequest(BaseModel):
    """Internal request to materialize single-media VMeta rows from persisted person objects."""

    media_uuid: str = Field(
        ...,
        description="Media UUID whose persisted person objects should be materialized into VMeta",
    )

    session_uuid: Optional[str] = Field(
        default=None,
        description="Vision/Orchestrator session UUID that produced the persisted person objects",
    )

    media_type: Optional[str] = Field(
        default=None,
        description="Optional media type override; if omitted VMeta will resolve it from media metadata",
    )

    person_objects: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Persisted person objects produced by Vision/Orchestrator",
    )

    processing_options: Optional[ProcessingOptions] = Field(
        default_factory=ProcessingOptions,
        description="Materialization options reused by single-media MVR processing",
    )

    await_authoritative_refresh: bool = Field(
        default=False,
        description=(
            "When true, wait for the authoritative orchestrator-backed IVA refresh "
            "before returning. Intended for UI/manual repair flows, not the "
            "orchestrator callback path."
        ),
    )


class PersistedPersonObjectsMaterializationResponse(BaseModel):
    """Response for internal persisted person-object materialization."""

    success: bool = Field(..., description="Whether materialization completed successfully")
    media_uuid: str = Field(..., description="Media UUID that was processed")
    session_uuid: Optional[str] = Field(default=None, description="Source session UUID")
    status: str = Field(..., description="completed, skipped_existing, or failed")
    media_type: str = Field(..., description="Resolved media type")
    existing_mvr_people_count: int = Field(
        default=0,
        description="Existing isolated MVR rows already present for this media before materialization",
    )
    mvr_people_count: int = Field(
        default=0,
        description="Number of isolated MVR people created or already present for this media",
    )
    total_faces_detected: int = Field(
        default=0,
        description="Number of face/person inputs included in materialization",
    )
    processing_time_ms: int = Field(
        default=0,
        description="Materialization processing time in milliseconds",
    )


# ============================================================================
# Response Models - Route Data
# ============================================================================

class RoutePoint(BaseModel):
    """Single route point for movement tracking."""
    
    center_x: float = Field(..., description="X-coordinate of center (pixels)")
    center_y: float = Field(..., description="Y-coordinate of center (pixels)")
    timestamp: float = Field(..., description="Seconds from video start (0.0 for photos)")
    frame_number: int = Field(..., description="Frame index (0 for photos)")
    velocity_x: float = Field(default=0.0, description="Horizontal velocity (px/s)")
    velocity_y: float = Field(default=0.0, description="Vertical velocity (px/s)")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Detection confidence (optional)")


class RouteData(BaseModel):
    """Route/movement data for an MVR person."""
    
    route_points: List[RoutePoint] = Field(
        ...,
        description="Route points (single point for photos, multiple for videos)"
    )
    
    total_detections: int = Field(
        ...,
        description="Total route points before sampling"
    )
    
    sampled_points: int = Field(
        default=None,
        description="Route points after sampling (if applied)"
    )
    
    movement_duration: float = Field(
        default=0.0,
        description="Duration from first to last detection (seconds)"
    )
    
    average_velocity: float = Field(
        default=0.0,
        description="Average movement speed (normalized px/s)"
    )


# ============================================================================
# Response Models - Demographics
# ============================================================================

class Demographics(BaseModel):
    """Demographic information for MVR person."""
    
    gender: Optional[str] = Field(
        None,
        description="Estimated gender (Male, Female, or null)"
    )
    
    gender_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Gender estimation confidence"
    )
    
    age_min: Optional[int] = Field(
        None,
        ge=0,
        le=120,
        description="Minimum estimated age"
    )
    
    age_max: Optional[int] = Field(
        None,
        ge=0,
        le=120,
        description="Maximum estimated age"
    )
    
    age_mean: Optional[float] = Field(
        None,
        ge=0,
        le=120,
        description="Mean estimated age"
    )
    
    age_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Age estimation confidence"
    )


# ============================================================================
# Response Models - Appearances
# ============================================================================

class IndividualAppearance(BaseModel):
    """Appearance of an individual in a video/photo."""
    
    individual_uuid: str = Field(..., description="Individual UUID")
    video_uuid: str = Field(..., description="Video/photo UUID")
    person_object_uuid: str = Field(..., description="Person object UUID")
    start_timestamp: datetime = Field(..., description="First detection timestamp")
    end_timestamp: datetime = Field(..., description="Last detection timestamp")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")


# ============================================================================
# Response Models - MVR Person
# ============================================================================

class MVRPerson(BaseModel):
    """MVR person data object (standard format)."""
    
    mvr_people_uuid: str = Field(..., description="MVR person UUID")
    
    individual_uuids: List[str] = Field(
        ...,
        description="UUIDs of individuals merged into this MVR person"
    )
    
    total_appearances: int = Field(
        ...,
        description="Total number of appearances"
    )
    
    unique_videos: int = Field(
        ...,
        description="Number of unique videos (always 1 for single-media processing)"
    )
    
    first_seen: datetime = Field(
        ...,
        description="Timestamp of first detection"
    )
    
    last_seen: datetime = Field(
        ...,
        description="Timestamp of last detection"
    )
    
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Overall confidence score"
    )
    
    quality_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Overall quality score"
    )
    
    average_route_velocity: float = Field(
        default=0.0,
        description="Average movement velocity (normalized px/s)"
    )
    
    demographics: Optional[Demographics] = Field(
        None,
        description="Demographic estimates (age, gender)"
    )
    
    appearances: List[IndividualAppearance] = Field(
        ...,
        description="All appearances of this MVR person"
    )
    
    route_data: Optional[RouteData] = Field(
        None,
        description="Movement tracking data"
    )
    
    face_embedding_available: bool = Field(
        default=True,
        description="Whether face embedding is available"
    )
    
    embedding_model: str = Field(
        default="Facenet512",
        description="Face embedding model used"
    )
    
    is_isolated: bool = Field(
        default=True,
        description="Whether this MVR is isolated (no cross-media merging)"
    )
    
    source_media_uuid: str = Field(
        ...,
        description="UUID of the single media this MVR was created from"
    )


# ============================================================================
# Response Models - Media Result
# ============================================================================

class MediaProcessingError(BaseModel):
    """Error information for failed media processing."""
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )


class MediaResult(BaseModel):
    """Result of processing a single media."""
    
    media_uuid: str = Field(..., description="Media UUID")
    
    media_type: str = Field(
        ...,
        description="Media type (photo or video)"
    )
    
    status: str = Field(
        ...,
        description="Processing status (completed, failed)"
    )
    
    mvr_people: List[MVRPerson] = Field(
        default_factory=list,
        description="MVR people detected in this media"
    )
    
    total_faces_detected: int = Field(
        default=0,
        description="Total faces detected"
    )
    
    mvr_people_count: int = Field(
        default=0,
        description="Number of unique MVR people created"
    )
    
    processing_time_ms: int = Field(
        default=0,
        description="Processing time in milliseconds"
    )
    
    error: Optional[MediaProcessingError] = Field(
        None,
        description="Error information if processing failed"
    )


# ============================================================================
# Response Models - Aggregate Statistics
# ============================================================================

class MediaTypeStatistics(BaseModel):
    """Statistics for a specific media type."""
    
    count: int = Field(..., description="Number of media processed")
    total_mvr: int = Field(..., description="Total MVR people created")
    avg_processing_ms: float = Field(..., description="Average processing time (ms)")


class AggregateStatistics(BaseModel):
    """Aggregate statistics across all processed media."""
    
    total_mvr_people_created: int = Field(
        ...,
        description="Total MVR people created across all media"
    )
    
    total_individuals_detected: int = Field(
        ...,
        description="Total individuals detected"
    )
    
    total_faces_detected: int = Field(
        ...,
        description="Total faces detected"
    )
    
    average_mvr_per_media: float = Field(
        ...,
        description="Average MVR people per media"
    )
    
    processing_breakdown: Dict[str, MediaTypeStatistics] = Field(
        default_factory=dict,
        description="Statistics broken down by media type (photos, videos)"
    )


# ============================================================================
# Response Models - Main Response
# ============================================================================

class ProcessMediaResponse(BaseModel):
    """Response from processing media independently."""
    
    success: bool = Field(..., description="Whether processing was successful")
    
    total_media: int = Field(
        ...,
        description="Total media requested"
    )
    
    processed_media: int = Field(
        ...,
        description="Media successfully processed"
    )
    
    failed_media: int = Field(
        ...,
        description="Media that failed processing"
    )
    
    processing_time_seconds: float = Field(
        default=0.0,
        description="Total processing time in seconds"
    )
    
    results: List[MediaResult] = Field(
        ...,
        description="Results for each media"
    )
    
    aggregate_statistics: Optional[AggregateStatistics] = Field(
        None,
        description="Aggregate statistics across all media"
    )


# ============================================================================
# Response Models - Async Processing
# ============================================================================

class AsyncProcessingResponse(BaseModel):
    """Response for asynchronous processing request."""
    
    success: bool = Field(..., description="Whether job was created successfully")
    
    job_id: str = Field(..., description="Background job ID")
    
    status: str = Field(
        default="processing",
        description="Job status (processing)"
    )
    
    message: str = Field(
        default="Media processing job created successfully",
        description="Status message"
    )
    
    total_media: int = Field(
        ...,
        description="Total media to process"
    )
    
    estimated_completion_seconds: int = Field(
        default=10,
        description="Estimated time to completion"
    )
    
    status_endpoint: str = Field(
        ...,
        description="Endpoint to poll for job status"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Job creation timestamp"
    )


class JobStatusResponse(BaseModel):
    """Response for job status polling."""
    
    job_id: str = Field(..., description="Job ID")
    
    status: str = Field(
        ...,
        description="Job status (processing, completed, failed)"
    )
    
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Processing progress (0.0 to 1.0)"
    )
    
    processed_media: int = Field(
        default=0,
        description="Media processed so far"
    )
    
    total_media: int = Field(
        ...,
        description="Total media to process"
    )
    
    started_at: datetime = Field(
        ...,
        description="Job start timestamp"
    )
    
    completed_at: Optional[datetime] = Field(
        None,
        description="Job completion timestamp"
    )
    
    results_endpoint: Optional[str] = Field(
        None,
        description="Endpoint to retrieve results (available when completed)"
    )
    
    error: Optional[MediaProcessingError] = Field(
        None,
        description="Error information if job failed"
    )

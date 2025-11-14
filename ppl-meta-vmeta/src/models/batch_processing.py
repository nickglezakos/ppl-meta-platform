"""
Batch Processing Models
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Pydantic models for batch processing state, configuration, and history.
These models mirror the database schema created in Phase 1 migrations.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# =============================================
# ENUMS
# =============================================

class BatchStatus(str, Enum):
    """Batch processing status states."""
    ACCUMULATING = "accumulating"  # Collecting videos
    PROCESSING = "processing"      # Pipeline executing
    COMPLETED = "completed"        # Successfully finished
    FAILED = "failed"              # Processing failed
    INCOMPLETE = "incomplete"      # Partial batch not processed


class TriggerReason(str, Enum):
    """Reasons why batch processing was triggered."""
    BATCH_SIZE_REACHED = "batch_size_reached"      # Normal: X videos completed
    RECORDING_STOPPED = "recording_stopped"         # Partial: Recording ended
    TIMEOUT_REACHED = "timeout_reached"            # Partial: Timeout expired
    MANUAL_TRIGGER = "manual_trigger"              # Manual intervention
    FORCE_PROCESSING = "force_processing"          # Admin override


# =============================================
# CONFIGURATION MODELS
# =============================================

class BatchProcessingConfig(BaseModel):
    """
    Batch processing configuration model.
    Maps to batch_processing_config table.
    """
    
    id: Optional[int] = None
    collection_id: Optional[str] = Field(
        None,
        description="Camera collection ID, None for global config"
    )
    
    # Batch size configuration
    batch_size_threshold: int = Field(
        5,
        ge=2,
        le=50,
        description="Number of videos that trigger batch processing"
    )
    
    # Partial batch handling
    partial_batch_min_videos: int = Field(
        2,
        ge=1,
        description="Minimum videos required to process partial batch"
    )
    partial_batch_timeout_minutes: int = Field(
        10,
        ge=1,
        le=1440,
        description="Minutes to wait before triggering partial batch"
    )
    partial_batch_max_wait_hours: int = Field(
        24,
        ge=1,
        le=168,
        description="Maximum hours to wait for batch completion"
    )
    
    # Recording stop event configuration
    enable_recording_stop_event: bool = Field(
        True,
        description="Use recording stop event as primary trigger"
    )
    recording_stop_trigger_delay_seconds: int = Field(
        2,
        ge=0,
        description="Delay in seconds after recording stop before triggering"
    )
    
    # Timeout fallback configuration
    enable_timeout_fallback: bool = Field(
        True,
        description="Use timeout as fallback trigger if event fails"
    )
    
    # Concurrency limits
    max_concurrent_batches: int = Field(
        3,
        ge=1,
        le=10,
        description="Maximum number of batches processing concurrently"
    )
    worker_pool_size: int = Field(
        3,
        ge=1,
        le=10,
        description="Number of dedicated worker processes"
    )
    
    # Resource limits
    max_batch_memory_gb: int = Field(
        2,
        ge=1,
        description="Maximum memory per batch in GB"
    )
    max_videos_per_session: int = Field(
        10,
        ge=1,
        description="Maximum videos per processing session"
    )
    max_processing_time_seconds: int = Field(
        300,
        ge=1,
        description="Maximum processing time per batch in seconds"
    )
    
    # Event configuration
    enable_event_triggering: bool = Field(
        True,
        description="Use event-driven triggering"
    )
    enable_polling_fallback: bool = Field(
        True,
        description="Use polling as fallback if events fail"
    )
    polling_interval_seconds: int = Field(
        30,
        ge=1,
        description="Polling interval in seconds when using fallback"
    )
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @validator('partial_batch_min_videos')
    def min_videos_less_than_threshold(cls, v, values):
        """Ensure min videos is less than batch size threshold."""
        if 'batch_size_threshold' in values and v >= values['batch_size_threshold']:
            raise ValueError(
                'partial_batch_min_videos must be less than batch_size_threshold'
            )
        return v
    
    class Config:
        from_attributes = True
        use_enum_values = True


# =============================================
# BATCH STATE MODELS
# =============================================

class BatchProcessingState(BaseModel):
    """
    Batch processing state model.
    Maps to batch_processing_state table.
    Tracks current batch accumulation and processing.
    """
    
    batch_uuid: UUID = Field(default_factory=uuid4, description="Unique batch identifier")
    collection_id: str = Field(description="Camera collection identifier")
    batch_number: int = Field(ge=1, description="Sequential batch number for collection")
    
    # Status and timing
    status: BatchStatus = Field(
        BatchStatus.ACCUMULATING,
        description="Current batch status"
    )
    video_count: int = Field(0, ge=0, description="Number of videos in batch")
    batch_size_threshold: int = Field(
        5,
        ge=2,
        le=50,
        description="Target batch size"
    )
    
    # Partial batch tracking
    is_partial_batch: bool = Field(
        False,
        description="Whether this is a partial batch"
    )
    trigger_reason: Optional[TriggerReason] = Field(
        None,
        description="Reason batch processing was triggered"
    )
    last_video_time: Optional[datetime] = Field(
        None,
        description="Timestamp of last video added"
    )
    timeout_at: Optional[datetime] = Field(
        None,
        description="When batch will timeout if no new videos"
    )
    
    # Results tracking
    individuals_created: int = Field(0, ge=0, description="New individuals created")
    individuals_cached: int = Field(0, ge=0, description="Individuals from cache")
    mvr_people_created: int = Field(0, ge=0, description="New MVR people created")
    mvr_people_cached: int = Field(0, ge=0, description="MVR people from cache")
    
    # Processing metrics
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def is_full_batch(self) -> bool:
        """Check if batch has reached full size."""
        return self.video_count >= self.batch_size_threshold
    
    @property
    def is_timeout_due(self) -> bool:
        """Check if batch timeout has been reached."""
        if not self.timeout_at:
            return False
        return datetime.utcnow() >= self.timeout_at
    
    @property
    def processing_time_seconds(self) -> Optional[float]:
        """Calculate processing time in seconds."""
        if not self.processing_started_at or not self.processing_completed_at:
            return None
        delta = self.processing_completed_at - self.processing_started_at
        return delta.total_seconds()
    
    @property
    def cache_hit_rate(self) -> Optional[float]:
        """Calculate cache hit rate as percentage."""
        total_individuals = self.individuals_created + self.individuals_cached
        if total_individuals == 0:
            return None
        return (self.individuals_cached / total_individuals) * 100
    
    class Config:
        from_attributes = True
        use_enum_values = True


class BatchVideoAssignment(BaseModel):
    """
    Video assignment to batch model.
    Maps to batch_video_assignments table.
    """
    
    id: Optional[int] = None
    batch_uuid: UUID = Field(description="Batch identifier")
    video_uuid: UUID = Field(description="Video identifier")
    collection_id: str = Field(description="Collection identifier")
    
    # Video timing
    video_start_time: datetime = Field(description="Video recording start time")
    video_end_time: datetime = Field(description="Video recording end time")
    
    # Ordering
    sequence_number: int = Field(
        ge=1,
        description="Sequential order of video in batch"
    )
    
    # Traceability
    face_detection_session_uuid: Optional[UUID] = Field(
        None,
        description="Face detection session that triggered video completion"
    )
    
    # Timestamps
    assigned_at: Optional[datetime] = None
    
    @validator('video_end_time')
    def end_after_start(cls, v, values):
        """Ensure video end is after start."""
        if 'video_start_time' in values and v <= values['video_start_time']:
            raise ValueError('video_end_time must be after video_start_time')
        return v
    
    class Config:
        from_attributes = True


# =============================================
# HISTORY MODELS
# =============================================

class BatchProcessingHistory(BaseModel):
    """
    Batch processing history model.
    Maps to batch_processing_history table.
    Permanent audit log of completed/failed batches.
    """
    
    batch_uuid: UUID = Field(description="Unique batch identifier")
    collection_id: str = Field(description="Collection identifier")
    batch_number: int = Field(ge=1, description="Batch number")
    
    # Status
    status: BatchStatus = Field(description="Final batch status (completed/failed)")
    
    # Batch composition
    video_count: int = Field(ge=0, description="Number of videos processed")
    is_partial_batch: bool = Field(description="Whether this was a partial batch")
    trigger_reason: TriggerReason = Field(description="Trigger reason")
    
    # Results
    individuals_created: int = Field(ge=0, description="Individuals created")
    individuals_cached: int = Field(ge=0, description="Individuals from cache")
    mvr_people_created: int = Field(ge=0, description="MVR people created")
    mvr_people_cached: int = Field(ge=0, description="MVR people from cache")
    
    # Performance metrics
    processing_time_seconds: float = Field(ge=0, description="Processing duration")
    cache_hit_rate: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Cache hit rate percentage"
    )
    throughput_videos_per_sec: Optional[float] = Field(
        None,
        ge=0,
        description="Videos processed per second"
    )
    
    # Error tracking
    error_message: Optional[str] = Field(None, description="Error if failed")
    
    # Timestamps
    batch_created_at: datetime = Field(description="When batch was created")
    processing_started_at: datetime = Field(description="When processing started")
    processing_completed_at: datetime = Field(description="When processing finished")
    archived_at: Optional[datetime] = None
    
    @validator('status')
    def status_must_be_terminal(cls, v):
        """Ensure only completed or failed batches in history."""
        if v not in [BatchStatus.COMPLETED, BatchStatus.FAILED]:
            raise ValueError('History only accepts completed or failed batches')
        return v
    
    class Config:
        from_attributes = True
        use_enum_values = True


# =============================================
# BATCH SUMMARY MODELS
# =============================================

class BatchVideoSummary(BaseModel):
    """
    Summary of videos in a batch.
    Maps to batch_video_summary view.
    """
    
    batch_uuid: UUID
    video_count: int
    earliest_video_start: Optional[datetime] = None
    latest_video_end: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BatchStatistics(BaseModel):
    """
    Aggregated statistics for batches.
    Returned by get_collection_batch_stats function.
    """
    
    collection_id: str
    total_batches: int = Field(ge=0)
    completed_batches: int = Field(ge=0)
    failed_batches: int = Field(ge=0)
    
    total_videos: int = Field(ge=0)
    total_individuals_created: int = Field(ge=0)
    total_individuals_cached: int = Field(ge=0)
    total_mvr_people_created: int = Field(ge=0)
    total_mvr_people_cached: int = Field(ge=0)
    
    avg_processing_time_seconds: Optional[float] = Field(None, ge=0)
    avg_cache_hit_rate: Optional[float] = Field(None, ge=0, le=100)
    avg_throughput: Optional[float] = Field(None, ge=0)
    
    class Config:
        from_attributes = True


# =============================================
# REQUEST/RESPONSE MODELS
# =============================================

class BatchCreateRequest(BaseModel):
    """Request to create a new batch."""
    
    collection_id: str = Field(description="Collection identifier")
    batch_size_threshold: Optional[int] = Field(
        None,
        ge=2,
        le=50,
        description="Override default batch size"
    )


class BatchUpdateRequest(BaseModel):
    """Request to update batch state."""
    
    status: Optional[BatchStatus] = None
    video_count: Optional[int] = Field(None, ge=0)
    is_partial_batch: Optional[bool] = None
    trigger_reason: Optional[TriggerReason] = None
    
    individuals_created: Optional[int] = Field(None, ge=0)
    individuals_cached: Optional[int] = Field(None, ge=0)
    mvr_people_created: Optional[int] = Field(None, ge=0)
    mvr_people_cached: Optional[int] = Field(None, ge=0)
    
    processing_error: Optional[str] = None


class VideoCompletionEvent(BaseModel):
    """Event payload for video completion."""
    
    video_uuid: UUID = Field(description="Completed video identifier")
    collection_id: str = Field(description="Collection identifier")
    video_start_time: datetime = Field(description="Video start time")
    video_end_time: datetime = Field(description="Video end time")
    face_detection_session_uuid: Optional[UUID] = Field(
        None,
        description="Face detection session UUID"
    )
    
    @validator('video_end_time')
    def end_after_start(cls, v, values):
        """Ensure video end is after start."""
        if 'video_start_time' in values and v <= values['video_start_time']:
            raise ValueError('video_end_time must be after video_start_time')
        return v


class RecordingStopEvent(BaseModel):
    """Event payload for recording stop."""
    
    collection_id: str = Field(description="Collection identifier")
    stopped_at: datetime = Field(description="When recording stopped")
    reason: Optional[str] = Field(None, description="Stop reason")


class BatchTriggerResponse(BaseModel):
    """Response after triggering batch processing."""
    
    batch_uuid: UUID
    collection_id: str
    trigger_reason: TriggerReason
    video_count: int
    is_partial_batch: bool
    triggered_at: datetime
    
    class Config:
        from_attributes = True

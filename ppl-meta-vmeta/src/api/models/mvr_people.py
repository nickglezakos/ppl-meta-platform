"""
MVR-People API Models

Pydantic models for request/response validation for all 14 MVR-People endpoints.

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ============================================================================
# Common Models
# ============================================================================

class FaceEmbedding(BaseModel):
    """Face embedding model."""
    vector: List[float] = Field(
        ...,
        description="512-dimensional face embedding vector"
    )
    model_name: str = Field(..., description="Embedding model name")
    model_version: str = Field(..., description="Embedding model version")


class AgeEstimate(BaseModel):
    """Age estimation model."""
    min_age: int = Field(..., ge=0, le=120, description="Minimum age")
    max_age: int = Field(..., ge=0, le=120, description="Maximum age")
    mean_age: float = Field(..., ge=0, le=120, description="Mean age")
    confidence: float = Field(..., ge=0, le=1, description="Confidence")
    model_name: Optional[str] = Field(None, description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")


class GenderEstimate(BaseModel):
    """Gender estimation model."""
    gender: str = Field(
        ...,
        description="Estimated gender",
        pattern="^(male|female|unknown)$"
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence")
    model_name: Optional[str] = Field(None, description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")


class LinkedIndividual(BaseModel):
    """Linked Individual model."""
    individual_uuid: UUID
    is_representative: bool = Field(
        ...,
        description="Is this the Individual that provided the face"
    )
    linked_at: datetime
    confidence_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Confidence score"
    )


# ============================================================================
# ENDPOINT 1: Create MVR-People for Individual
# ============================================================================

class CreateMVRRequest(BaseModel):
    """Request model for creating MVR-People."""
    background_processing: bool = Field(
        True,
        description="Enable background processing"
    )
    force_recreate: bool = Field(
        False,
        description="Recreate if already exists"
    )


class CreateMVRResponse(BaseModel):
    """Response model for creating MVR-People."""
    mvr_people_uuid: Optional[UUID] = Field(
        None,
        description="UUID of created MVR-People (null if pending)"
    )
    individual_uuid: UUID
    status: str = Field(
        ...,
        description="Processing status",
        pattern="^(pending|processing|completed|failed)$"
    )
    message: Optional[str] = None
    estimated_completion_seconds: Optional[int] = None
    
    # Synchronous processing fields (only if status=completed)
    face_embedding: Optional[FaceEmbedding] = None
    age_estimate: Optional[AgeEstimate] = None
    gender_estimate: Optional[GenderEstimate] = None
    representative_individual_uuid: Optional[UUID] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# ENDPOINT 2 & 3: Get MVR-People by UUID / for Individual
# ============================================================================

class MVRPeopleResponse(BaseModel):
    """Response model for MVR-People record."""
    mvr_people_uuid: UUID
    status: str = Field(
        ...,
        description="Processing status",
        pattern="^(pending|processing|completed|failed)$"
    )
    
    # Core data
    face_embedding: Optional[FaceEmbedding] = None
    age_estimate: Optional[AgeEstimate] = None
    gender_estimate: Optional[GenderEstimate] = None
    
    # Source information
    representative_individual_uuid: Optional[UUID] = None
    representative_face_uuid: Optional[UUID] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Linked Individuals
    total_linked_individuals: int = Field(0, ge=0)
    linked_individuals: Optional[List[LinkedIndividual]] = None
    
    # Orphaning information
    is_orphaned: Optional[bool] = Field(False)
    orphaned_at: Optional[datetime] = None
    merged_into_mvr_uuid: Optional[UUID] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Alternative response format (for endpoint 3)
    individual_uuid: Optional[UUID] = None
    mvr_people: Optional[Dict[str, Any]] = None


# ============================================================================
# ENDPOINT 4: Search Similar MVR-People
# ============================================================================

class SearchSimilarRequest(BaseModel):
    """Request model for similarity search."""
    mvr_people_uuid: Optional[UUID] = Field(
        None,
        description="MVR-People UUID to search from"
    )
    face_embedding: Optional[List[float]] = Field(
        None,
        description="512D face embedding vector"
    )
    similarity_threshold: Optional[float] = Field(
        0.7,
        ge=0,
        le=1,
        description="Minimum cosine similarity"
    )
    max_results: Optional[int] = Field(
        10,
        ge=1,
        le=100,
        description="Maximum results"
    )
    include_demographics: Optional[bool] = Field(
        True,
        description="Include age/gender in results"
    )
    
    @validator('face_embedding')
    def validate_embedding_size(cls, v):
        """Validate embedding is 512D."""
        if v is not None and len(v) != 512:
            raise ValueError('face_embedding must be 512-dimensional')
        return v


class SimilarMVRResult(BaseModel):
    """Single result from similarity search."""
    mvr_people_uuid: UUID
    similarity_score: float = Field(..., ge=0, le=1)
    age_estimate: Optional[AgeEstimate] = None
    gender_estimate: Optional[GenderEstimate] = None
    total_linked_individuals: int = Field(0, ge=0)
    quality_score: Optional[float] = Field(None, ge=0, le=1)


class SearchSimilarResponse(BaseModel):
    """Response model for similarity search."""
    query_mvr_people_uuid: Optional[UUID] = None
    total_results: int = Field(0, ge=0)
    results: List[SimilarMVRResult] = Field(default_factory=list)


# ============================================================================
# ENDPOINT 5: Search MVR-People by Demographics
# ============================================================================

class SearchDemographicsRequest(BaseModel):
    """Request model for demographic search."""
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = Field(
        None,
        pattern="^(male|female|unknown)$"
    )
    min_confidence: Optional[float] = Field(0.7, ge=0, le=1)
    page: Optional[int] = Field(1, ge=1)
    page_size: Optional[int] = Field(20, ge=1, le=100)


class DemographicMVRResult(BaseModel):
    """Single result from demographic search."""
    mvr_people_uuid: UUID
    age_estimate: AgeEstimate
    gender_estimate: GenderEstimate
    total_linked_individuals: int = Field(0, ge=0)
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    created_at: datetime


class SearchDemographicsResponse(BaseModel):
    """Response model for demographic search."""
    total_results: int = Field(0, ge=0)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    results: List[DemographicMVRResult] = Field(default_factory=list)


# ============================================================================
# ENDPOINT 6: Link Individual to MVR-People
# ============================================================================

class LinkIndividualRequest(BaseModel):
    """Request model for linking Individual to MVR-People."""
    individual_uuid: UUID
    confidence_score: float = Field(..., ge=0, le=1)


class LinkIndividualResponse(BaseModel):
    """Response model for linking Individual."""
    mvr_people_uuid: UUID
    individual_uuid: UUID
    linked_at: datetime
    confidence_score: float = Field(..., ge=0, le=1)
    total_linked_individuals: int = Field(0, ge=0)


# ============================================================================
# ENDPOINT 7: Batch Create MVR-People
# ============================================================================

class BatchCreateRequest(BaseModel):
    """Request model for batch MVR creation."""
    individual_uuids: List[UUID] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of Individual UUIDs"
    )
    background_processing: bool = Field(True)


class BatchCreateResponse(BaseModel):
    """Response model for batch creation."""
    total_queued: int = Field(..., ge=0)
    batch_id: Optional[UUID] = None
    status: str = Field(
        ...,
        pattern="^(processing|completed|failed)$"
    )
    individual_uuids: List[UUID]
    estimated_completion_seconds: int = Field(..., ge=0)


# ============================================================================
# ENDPOINT 8: Get MVR-People Processing Status
# ============================================================================

class MVRStatusResponse(BaseModel):
    """Response model for processing status."""
    mvr_people_uuid: UUID
    status: str = Field(
        ...,
        pattern="^(pending|processing|completed|failed)$"
    )
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[str] = None


# ============================================================================
# ENDPOINT 9: Match Individuals
# ============================================================================

class MatchIndividualRequest(BaseModel):
    """Request model for matching Individuals."""
    threshold: Optional[float] = Field(0.85, ge=0, le=1)
    auto_merge: bool = Field(False)
    max_results: Optional[int] = Field(10, ge=1, le=100)


class MatchResult(BaseModel):
    """Single match result."""
    individual_uuid: UUID
    mvr_people_uuid: UUID
    similarity_score: float = Field(..., ge=0, le=1)
    quality_score: float = Field(..., ge=0, le=1)
    age_estimate: Optional[AgeEstimate] = None
    gender_estimate: Optional[GenderEstimate] = None
    above_threshold: bool


class MatchIndividualResponse(BaseModel):
    """Response model for matching Individuals."""
    individual_uuid: UUID
    matches: List[MatchResult] = Field(default_factory=list)
    total_matches: int = Field(0, ge=0)
    matches_above_threshold: int = Field(0, ge=0)
    threshold_used: float = Field(..., ge=0, le=1)


# ============================================================================
# ENDPOINT 10: Merge Individuals
# ============================================================================

class MergeIndividualsRequest(BaseModel):
    """Request model for merging Individuals."""
    individual_a_uuid: UUID
    individual_b_uuid: UUID
    similarity_score: float = Field(..., ge=0, le=1)
    triggered_by: Optional[str] = Field("manual")


class MergeIndividualsResponse(BaseModel):
    """Response model for merging Individuals."""
    success: bool
    predominant_mvr_uuid: UUID
    orphaned_mvr_uuid: UUID
    reassigned_individual_uuid: UUID
    similarity_score: float = Field(..., ge=0, le=1)
    predominant_quality_score: Optional[float] = Field(None, ge=0, le=1)
    orphaned_quality_score: Optional[float] = Field(None, ge=0, le=1)
    merged_at: datetime
    message: Optional[str] = None


# ============================================================================
# ENDPOINT 10b: Unmerge MVR
# ============================================================================

class UnmergeMvrRequest(BaseModel):
    """Request model for undoing a merge (unmerge)."""
    orphaned_mvr_uuid: UUID = Field(
        ..., description="UUID of the orphaned (child) MVR to restore"
    )


class UnmergeMvrResponse(BaseModel):
    """Response model for unmerge operation."""
    success: bool
    restored_mvr_uuid: UUID
    winner_mvr_uuid: UUID
    individuals_reassigned: int
    message: str


# ============================================================================
# ENDPOINT 11: Get Merge History
# ============================================================================

class CurrentMVRPeople(BaseModel):
    """Current MVR-People model."""
    mvr_people_uuid: UUID
    is_orphaned: bool
    total_linked_individuals: int = Field(0, ge=0)


class PreviousMVRPeople(BaseModel):
    """Previous (orphaned) MVR-People model."""
    mvr_people_uuid: UUID
    is_orphaned: bool
    orphaned_at: datetime
    merged_into_mvr_uuid: UUID


class MergeEvent(BaseModel):
    """Merge event from audit log."""
    merge_id: int
    predominant_mvr_uuid: UUID
    orphaned_mvr_uuid: UUID
    similarity_score: float = Field(..., ge=0, le=1)
    merged_at: datetime
    triggered_by: str


class MergeHistoryResponse(BaseModel):
    """Response model for merge history."""
    individual_uuid: UUID
    current_mvr_people: Optional[CurrentMVRPeople] = None
    previous_mvr_people: List[PreviousMVRPeople] = Field(
        default_factory=list
    )
    merge_events: List[MergeEvent] = Field(default_factory=list)
    total_merges: int = Field(0, ge=0)


# ============================================================================
# ENDPOINT 12: Get Orphaned MVR-People
# ============================================================================

class OrphanedMVRResult(BaseModel):
    """Single orphaned MVR result."""
    mvr_people_uuid: UUID
    is_orphaned: bool
    orphaned_at: datetime
    merged_into_mvr_uuid: UUID
    previous_individual_uuids: List[UUID]
    quality_score: float = Field(..., ge=0, le=1)
    created_at: datetime


class OrphanedMVRResponse(BaseModel):
    """Response model for orphaned MVR-People."""
    total_orphaned: int = Field(0, ge=0)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    results: List[OrphanedMVRResult] = Field(default_factory=list)


# ============================================================================
# ENDPOINT 13 & 14: Matching Configuration
# ============================================================================

class MatchingConfigUpdate(BaseModel):
    """Request model for updating matching config."""
    default_matching_threshold: Optional[float] = Field(
        None,
        ge=0,
        le=1
    )
    auto_merge_enabled: Optional[bool] = None
    min_quality_threshold: Optional[float] = Field(None, ge=0, le=1)


class MatchingConfigResponse(BaseModel):
    """Response model for matching configuration."""
    default_matching_threshold: float = Field(..., ge=0, le=1)
    auto_merge_enabled: bool
    min_quality_threshold: float = Field(..., ge=0, le=1)
    age_range_tolerance: int = Field(..., ge=0)
    gender_match_required: bool
    orphan_retention_days: int = Field(..., ge=0)
    last_updated: Optional[datetime] = None
    
    # For update response
    success: Optional[bool] = None
    updated_config: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# HEALTH CHECK: MVR-People System Health
# ============================================================================

class DatabaseHealthStatus(BaseModel):
    """Database health status for MVR-People system."""
    connected: bool = Field(..., description="Database connection status")
    pool_size: int = Field(..., description="Current connection pool size")
    idle_connections: int = Field(..., description="Idle connections in pool")
    response_time_ms: float = Field(..., description="Database response time in milliseconds")
    pgvector_available: bool = Field(..., description="pgvector extension availability")


class MLModelsHealthStatus(BaseModel):
    """ML models health status."""
    facenet_loaded: bool = Field(..., description="FaceNet model loaded")
    age_model_loaded: bool = Field(..., description="Age estimation model loaded")
    gender_model_loaded: bool = Field(..., description="Gender classification model loaded")
    total_models_loaded: int = Field(..., description="Total models loaded")
    model_load_time_ms: float = Field(..., description="Model load time in milliseconds")


class ProcessingQueueStatus(BaseModel):
    """Background processing queue status."""
    queue_size: int = Field(..., description="Current queue size")
    processing_tasks: int = Field(..., description="Tasks currently processing")
    pending_tasks: int = Field(..., description="Tasks pending")
    failed_tasks_last_hour: int = Field(..., description="Failed tasks in last hour")
    average_processing_time_ms: float = Field(..., description="Average task processing time")


class MVRStatistics(BaseModel):
    """MVR-People system statistics."""
    total_mvr_people: int = Field(..., description="Total MVR-People records")
    active_mvr_people: int = Field(..., description="Active (non-orphaned) MVR-People")
    orphaned_mvr_people: int = Field(..., description="Orphaned MVR-People")
    individuals_with_mvr: int = Field(..., description="Individuals with MVR mapping")
    total_merge_operations: int = Field(..., description="Total merge operations")
    average_quality_score: float = Field(..., description="Average MVR quality score")


class MVRHealthResponse(BaseModel):
    """Comprehensive health check response for MVR-People system."""
    status: str = Field(
        ...,
        description="Overall system status",
        pattern="^(healthy|degraded|unhealthy)$"
    )
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="MVR-People version")
    
    # Component health
    database: DatabaseHealthStatus
    ml_models: MLModelsHealthStatus
    processing_queue: ProcessingQueueStatus
    
    # Statistics
    statistics: MVRStatistics
    
    # Additional metadata
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    last_mvr_created_at: Optional[datetime] = Field(None, description="Last MVR creation time")
    last_merge_at: Optional[datetime] = Field(None, description="Last merge operation time")
    
    # Warnings/Errors
    warnings: List[str] = Field(default_factory=list, description="System warnings")
    errors: List[str] = Field(default_factory=list, description="System errors")


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Common models
    "FaceEmbedding",
    "AgeEstimate",
    "GenderEstimate",
    "LinkedIndividual",
    
    # Endpoint 1: Create MVR
    "CreateMVRRequest",
    "CreateMVRResponse",
    
    # Endpoint 2 & 3: Get MVR
    "MVRPeopleResponse",
    
    # Endpoint 4: Search Similar
    "SearchSimilarRequest",
    "SimilarMVRResult",
    "SearchSimilarResponse",
    
    # Endpoint 5: Search Demographics
    "SearchDemographicsRequest",
    "DemographicMVRResult",
    "SearchDemographicsResponse",
    
    # Endpoint 6: Link Individual
    "LinkIndividualRequest",
    "LinkIndividualResponse",
    
    # Endpoint 7: Batch Create
    "BatchCreateRequest",
    "BatchCreateResponse",
    
    # Endpoint 8: Status
    "MVRStatusResponse",
    
    # Endpoint 9: Match
    "MatchIndividualRequest",
    "MatchResult",
    "MatchIndividualResponse",
    
    # Endpoint 10: Merge
    "MergeIndividualsRequest",
    "MergeIndividualsResponse",

    # Endpoint 10b: Unmerge
    "UnmergeMvrRequest",
    "UnmergeMvrResponse",

    # Endpoint 11: Merge History
    "CurrentMVRPeople",
    "PreviousMVRPeople",
    "MergeEvent",
    "MergeHistoryResponse",
    
    # Endpoint 12: Orphaned
    "OrphanedMVRResult",
    "OrphanedMVRResponse",
    
    # Endpoint 13 & 14: Config
    "MatchingConfigUpdate",
    "MatchingConfigResponse",
    
    # Health Check
    "MVRHealthResponse",
    "DatabaseHealthStatus",
    "MLModelsHealthStatus",
    "ProcessingQueueStatus",
    "MVRStatistics",
]

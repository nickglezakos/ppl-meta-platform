"""
Batch Match & Merge Models
Pydantic models for batch matching and merging of individuals.

Author: PPL Meta Platform
Date: November 1, 2025
Version: 1.0.0
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class BatchMatchAndMergeRequest(BaseModel):
    """Request to batch match and merge individuals."""
    
    individual_uuids: List[UUID] = Field(
        ...,
        min_items=1,
        description="List of individual UUIDs to match and merge"
    )
    threshold: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for matching (0.0-1.0)"
    )
    triggered_by: Optional[str] = Field(
        default="batch_auto_match",
        description="Source that triggered the merge"
    )
    session_uuid: Optional[UUID] = Field(
        default=None,
        description="Optional tracking session UUID for audit trail"
    )


class MergeDetail(BaseModel):
    """Details of a single merge operation."""
    
    predominant_individual_uuid: UUID
    orphaned_individual_uuid: UUID
    predominant_mvr_uuid: UUID
    orphaned_mvr_uuid: UUID
    similarity_score: float
    merged_at: datetime


class BatchMatchAndMergeResponse(BaseModel):
    """Response from batch match and merge operation."""
    
    success: bool
    original_count: int = Field(
        ...,
        description="Number of individuals before merging"
    )
    unique_count: int = Field(
        ...,
        description="Number of unique individuals after merging"
    )
    merge_count: int = Field(
        ...,
        description="Number of individuals that were merged (orphaned)"
    )
    merges: List[MergeDetail] = Field(
        default_factory=list,
        description="Details of each merge operation"
    )
    skipped_count: int = Field(
        default=0,
        description="Number of individuals skipped due to errors"
    )
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time in seconds"
    )
    message: Optional[str] = None


class BatchMatchAndMergeError(BaseModel):
    """Error response for batch operations."""
    
    success: bool = False
    error: str
    original_count: int
    unique_count: int
    partial_results: Optional[BatchMatchAndMergeResponse] = None

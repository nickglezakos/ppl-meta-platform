"""
MVR People Search Models

Models for searching existing MVR people and their linked individuals
without triggering any merge operations.

Author: PPL Meta Platform
Date: November 16, 2025
Version: 2.19.33
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class MVRPeopleSearchRequest(BaseModel):
    """Request model for searching existing MVR people by collection and date range."""
    collection_name: str = Field(..., description="Collection identifier (camera device ID or collection UUID)")
    start_time: datetime = Field(..., description="Start of search time range")
    end_time: datetime = Field(..., description="End of search time range")
    limit: int = Field(100, ge=1, le=500, description="Maximum results to return")


class IndividualAppearance(BaseModel):
    """Individual appearance within a video."""
    video_uuid: str
    person_object_uuid: str
    start_timestamp: datetime
    end_timestamp: datetime
    confidence: float


class MVRPersonResult(BaseModel):
    """Single MVR person result with aggregated data."""
    mvr_people_uuid: str
    individual_uuids: List[str] = Field(description="All linked individual UUIDs")
    total_appearances: int = Field(description="Total appearances across all videos")
    unique_videos: int = Field(description="Number of unique videos")
    first_seen: datetime
    last_seen: datetime
    confidence_score: float
    quality_score: float
    appearances: List[IndividualAppearance] = Field(description="All video appearances")
    
    # Demographics
    estimated_age: Optional[str] = None  # Changed from int to str to support age ranges like "33-43"
    estimated_gender: Optional[str] = None


class MVRPeopleSearchResponse(BaseModel):
    """Response model for MVR people search."""
    success: bool = True
    total_results: int = Field(ge=0)
    mvr_people: List[MVRPersonResult]
    search_parameters: dict
    message: Optional[str] = None


__all__ = [
    "MVRPeopleSearchRequest",
    "IndividualAppearance",
    "MVRPersonResult",
    "MVRPeopleSearchResponse",
]

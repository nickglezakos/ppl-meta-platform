"""
MVR People Name Management Models

Request and response models for MVR people naming feature.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime


class UpdateNameRequest(BaseModel):
    """Request model for updating MVR person name."""
    name: str = Field(
        ...,
        description="New name for the MVR person (empty string to clear name)",
        max_length=255
    )
    propagate: bool = Field(
        default=True,
        description="Whether to propagate name to all merged MVR people in hierarchy"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name field."""
        if v is None:
            return ""
        
        # Strip whitespace
        v = v.strip()
        
        # Check length after stripping
        if len(v) > 255:
            raise ValueError("Name must be 255 characters or less")
        
        # Check for control characters
        if any(ord(c) < 32 for c in v):
            raise ValueError("Name contains invalid control characters")
        
        return v


class UpdateNameResponse(BaseModel):
    """Response model for name update operation."""
    success: bool
    mvr_person_uuid: str
    name: Optional[str]
    updated_at: datetime
    propagated_to: List[str] = Field(
        default_factory=list,
        description="List of MVR UUIDs that inherited this name"
    )
    affected_super_individuals: List[str] = Field(
        default_factory=list,
        description="List of super-individual UUIDs that were updated"
    )


class BulkNameUpdate(BaseModel):
    """Single name update in bulk operation."""
    mvr_person_uuid: str
    name: str = Field(max_length=255)


class BulkNameUpdateRequest(BaseModel):
    """Request model for bulk name updates."""
    updates: List[BulkNameUpdate]
    propagate: bool = Field(
        default=True,
        description="Whether to propagate names to merged hierarchies"
    )


class BulkNameUpdateResponse(BaseModel):
    """Response model for bulk name updates."""
    success: bool
    updated_count: int
    total_propagated: int = Field(
        description="Total number of MVR records updated including propagation"
    )
    errors: List[dict] = Field(default_factory=list)


class UpdateGenderRequest(BaseModel):
    """Request model for updating MVR person gender."""
    gender: str = Field(
        ...,
        description="Gender value: 'male', 'female', or empty string to clear",
        max_length=50
    )
    propagate: bool = Field(
        default=True,
        description="Whether to propagate gender to all merged MVR people in hierarchy"
    )
    
    @validator('gender')
    def validate_gender(cls, v):
        """Validate gender field."""
        if v is None:
            return ""
        
        # Strip whitespace and lowercase
        v = v.strip().lower()
        
        # Only allow specific values
        if v and v not in ['male', 'female', 'man', 'woman', 'm', 'f']:
            raise ValueError("Gender must be 'male', 'female', or empty string")
        
        # Normalize to standard values
        if v in ['man', 'm']:
            return 'male'
        elif v in ['woman', 'f']:
            return 'female'
        
        return v


class UpdateGenderResponse(BaseModel):
    """Response model for gender update operation."""
    success: bool
    mvr_person_uuid: str
    gender: Optional[str]
    updated_at: datetime
    propagated_to: List[str] = Field(
        default_factory=list,
        description="List of MVR UUIDs that inherited this gender"
    )
    affected_super_individuals: List[str] = Field(
        default_factory=list,
        description="List of super-individual UUIDs that were updated"
    )


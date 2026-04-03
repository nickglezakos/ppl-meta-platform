"""
Individual Groups Data Models
Data models for organizing individuals into user-created groups.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class GroupVisibility(str, Enum):
    """Visibility level for individual groups"""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class IndividualGroup(BaseModel):
    """
    Represents a collection of individuals organized by the user.
    
    Individual groups allow users to organize detected persons into meaningful
    categories like "VIP Customers", "Staff", "Regulars", etc.
    """
    
    id: str = Field(
        default_factory=lambda: f"grp_{uuid4().hex[:12]}",
        description="Unique group identifier"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Group name"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional group description"
    )
    
    # Ownership & Permissions
    created_by: str = Field(
        ...,
        description="User ID who created the group"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Group creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    # Members
    member_count: int = Field(
        default=0,
        ge=0,
        description="Number of individuals in this group"
    )
    member_ids: List[str] = Field(
        default_factory=list,
        description="Individual IDs in this group"
    )
    
    # Settings
    visibility: GroupVisibility = Field(
        default=GroupVisibility.PRIVATE,
        description="Group visibility level"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization"
    )
    
    # Display
    cover_individual_id: Optional[str] = Field(
        None,
        description="Individual ID to use for group thumbnail"
    )
    
    # Metadata
    metadata: Dict = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "grp_abc123xyz",
                "name": "VIP Customers",
                "description": "High-value customers identified across stores",
                "created_by": "user_456",
                "member_count": 15,
                "visibility": "private",
                "tags": ["vip", "loyalty", "store-a"]
            }
        }


class GroupMembership(BaseModel):
    """
    Junction model for many-to-many relationship between groups and individuals.
    """
    
    id: str = Field(
        default_factory=lambda: f"mem_{uuid4().hex[:12]}",
        description="Membership record ID"
    )
    group_id: str = Field(..., description="Group identifier")
    individual_id: str = Field(..., description="Individual identifier")
    
    added_by: str = Field(
        ...,
        description="User ID who added this member"
    )
    added_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Membership creation timestamp"
    )
    
    # Optional notes
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes about this membership"
    )


class CreateIndividualGroupRequest(BaseModel):
    """Request model for creating a new individual group"""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    visibility: GroupVisibility = Field(default=GroupVisibility.PRIVATE)
    tags: List[str] = Field(default_factory=list)
    initial_member_ids: List[str] = Field(
        default_factory=list,
        description="Initial members to add to the group"
    )


class UpdateIndividualGroupRequest(BaseModel):
    """Request model for updating an individual group"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    visibility: Optional[GroupVisibility] = None
    tags: Optional[List[str]] = None
    cover_individual_id: Optional[str] = None


class AddGroupMembersRequest(BaseModel):
    """Request model for adding members to a group"""
    
    individual_ids: List[str] = Field(..., min_items=1)
    notes: Optional[str] = Field(None, max_length=500)


class RemoveGroupMembersRequest(BaseModel):
    """Request model for removing members from a group"""
    
    individual_ids: List[str] = Field(..., min_items=1)


class IndividualSummary(BaseModel):
    """Lightweight individual data for list views"""
    
    id: str
    mvr_person_uuid: Optional[str] = None
    thumbnail_url: Optional[str] = None
    total_appearances: int = 0
    last_seen: Optional[datetime] = None
    group_count: int = 0
    confidence_score: float = 0.0
    group_member_number: Optional[int] = None
    
    # Individual naming (v2.21.0)
    name: Optional[str] = None
    name_updated_at: Optional[datetime] = None
    name_updated_by: Optional[str] = None


class IndividualGroupResponse(BaseModel):
    """Response model for individual group with member preview"""
    
    group: IndividualGroup
    members_preview: List[IndividualSummary] = Field(
        default_factory=list,
        description="First 5 members for preview"
    )


class ListGroupsResponse(BaseModel):
    """Response model for listing groups"""
    
    groups: List[IndividualGroup]
    total: int
    skip: int
    limit: int


class ListMembersResponse(BaseModel):
    """Response model for listing group members"""
    
    members: List[IndividualSummary]
    total: int
    skip: int
    limit: int


class AddMembersResponse(BaseModel):
    """Response model for adding members"""
    
    group: IndividualGroup
    added_count: int
    skipped_count: int = Field(
        default=0,
        description="Number of individuals already in group"
    )


class RemoveMembersResponse(BaseModel):
    """Response model for removing members"""
    
    group: IndividualGroup
    removed_count: int


class BulkAddMembersRequest(BaseModel):
    """Request model for bulk adding members to a group"""
    
    group_id: str
    individual_ids: List[str] = Field(..., min_items=1)


class BulkAddMembersResponse(BaseModel):
    """Response model for bulk operations"""
    
    success_count: int
    error_count: int
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of errors with individual_id and reason"
    )


class BulkAssignGroupsRequest(BaseModel):
    """Request model for assigning individuals to multiple groups"""
    
    individual_ids: List[str] = Field(..., min_items=1)
    group_ids: List[str] = Field(..., min_items=1)


class BulkAssignGroupsResponse(BaseModel):
    """Response model for bulk group assignment"""
    
    assignments_created: int
    individuals_updated: int


# ============================================================================
# Camera Search Models
# ============================================================================

class GroupCameraSearchRequest(BaseModel):
    """Request model for searching group members in camera footage"""
    
    camera_id: Optional[str] = Field(None, description="Single camera/collection ID (deprecated, use camera_ids)")
    camera_ids: Optional[List[str]] = Field(None, description="List of camera/collection IDs to search")
    start_time: datetime = Field(..., description="Search start time")
    end_time: datetime = Field(..., description="Search end time")
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for matches (default: 0.5)"
    )
    
    @model_validator(mode='after')
    def validate_cameras(self):
        """Ensure at least one camera is specified"""
        if not self.camera_id and not self.camera_ids:
            raise ValueError("Either camera_id or camera_ids must be provided")
        
        if self.camera_ids is not None and len(self.camera_ids) == 0:
            raise ValueError("camera_ids cannot be an empty list")
        
        return self
    
    def get_camera_ids(self) -> List[str]:
        """Get normalized list of camera IDs"""
        if self.camera_ids:
            return self.camera_ids
        elif self.camera_id:
            return [self.camera_id]
        return []


class MatchedIndividual(BaseModel):
    """Matched individual from camera search"""
    
    individual_uuid: str
    mvr_person_uuid: Optional[str] = None
    total_appearances: int
    first_seen: datetime
    last_seen: datetime
    confidence_score: float
    demographics: Optional[Dict] = None
    appearances: Optional[List[Dict]] = None  # Individual appearance records with video_uuid


class GroupCameraSearchResponse(BaseModel):
    """Response model for group camera search"""
    
    group_id: str
    group_name: str
    camera_id: Optional[str] = Field(None, description="Single camera ID (deprecated)")
    camera_name: Optional[str] = Field(None, description="Single camera name (deprecated)")
    camera_ids: Optional[List[str]] = Field(None, description="List of camera IDs searched")
    camera_names: Optional[List[str]] = Field(None, description="List of camera names searched")
    search_window: Dict = Field(
        description="Search time range with start_time and end_time"
    )
    total_group_members: int
    members_found: int
    matched_individuals: List[MatchedIndividual]
    search_session_uuid: str = Field(
        description="Session UUID for further analysis"
    )


# ============================================================================
# Duplicate Detection & Merge Models
# ============================================================================

class DuplicateMatch(BaseModel):
    """A potential duplicate match within a group"""
    
    existing_member_id: str = Field(description="UUID of existing group member")
    existing_member_name: Optional[str] = Field(description="Name of existing member if set")
    group_member_number: Optional[int] = Field(
        default=None,
        description="Display member number inside the group (Group Member NN)",
    )
    similarity_score: float = Field(description="Face similarity score (0-1)")
    confidence: str = Field(description="Match confidence level: high, medium, low")


class CheckDuplicatesRequest(BaseModel):
    """Request to check if candidate matches existing group members"""
    
    candidate_mvr_uuid: str = Field(description="MVR person UUID to check")
    similarity_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum similarity to consider a match"
    )


class CheckDuplicatesResponse(BaseModel):
    """Response with potential duplicate matches"""
    
    has_duplicates: bool
    matches: List[DuplicateMatch] = Field(default_factory=list)
    candidate_mvr_uuid: str
    group_id: str
    group_name: str


class MergeMembersRequest(BaseModel):
    """Request to merge two group members"""
    
    source_mvr_uuid: str = Field(description="UUID of member to merge (will be merged into target)")
    target_mvr_uuid: str = Field(description="UUID of member to keep")
    user_confirmed: bool = Field(default=True, description="User confirmed the merge")


class MergeMembersResponse(BaseModel):
    """Response after merging members"""
    
    success: bool
    super_individual_uuid: str = Field(description="UUID of resulting super-individual")
    merged_count: int = Field(description="Total MVR people in the merge")
    group_membership_updated: bool = Field(
        description="Whether group membership was updated to use super-individual"
    )

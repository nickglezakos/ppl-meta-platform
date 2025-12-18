"""
Individual Groups API Routes
RESTful endpoints for managing individual groups.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.dependencies import get_groups_manager
from models.individual_group import (
    AddGroupMembersRequest,
    AddMembersResponse,
    BulkAddMembersRequest,
    BulkAddMembersResponse,
    BulkAssignGroupsRequest,
    BulkAssignGroupsResponse,
    CreateIndividualGroupRequest,
    GroupCameraSearchRequest,
    GroupCameraSearchResponse,
    IndividualGroup,
    IndividualGroupResponse,
    ListGroupsResponse,
    ListMembersResponse,
    RemoveGroupMembersRequest,
    RemoveMembersResponse,
    UpdateIndividualGroupRequest,
)
from services.individual_groups_manager import IndividualGroupsManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/individual-groups", tags=["individual-groups"])


# ================================================================
# Group Management Endpoints
# ================================================================

@router.post("", status_code=status.HTTP_201_CREATED, response_model=IndividualGroupResponse)
async def create_group(
    request: CreateIndividualGroupRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> IndividualGroupResponse:
    """
    Create a new individual group.
    
    Args:
        request: Group creation parameters
        manager: IndividualGroupsManager dependency
        
    Returns:
        Created group with member preview
    """
    try:
        group = await manager.create_group(
            name=request.name,
            description=request.description,
            created_by="default_user",  # TODO: Get from auth context
            visibility=request.visibility,
            tags=request.tags,
            initial_member_ids=request.initial_member_ids,
        )
        
        # Get member preview
        members_preview, _ = await manager.get_group_members(
            group.id, skip=0, limit=5
        )
        
        return IndividualGroupResponse(
            group=group,
            members_preview=members_preview,
        )
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create group: {str(e)}"
        )


@router.get("", response_model=ListGroupsResponse)
async def list_groups(
    user_id: Optional[str] = Query(None, description="Filter by creator user ID"),
    visibility: Optional[str] = Query(None, description="Filter by visibility"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> ListGroupsResponse:
    """
    List all individual groups with optional filtering.
    
    Args:
        user_id: Filter by creator
        visibility: Filter by visibility level
        tags: Filter by tags (any match)
        search: Search query
        skip: Pagination offset
        limit: Page size
        manager: IndividualGroupsManager dependency
        
    Returns:
        List of groups with pagination info
    """
    try:
        groups, total = await manager.list_groups(
            user_id=user_id,
            visibility=visibility,
            tags=tags,
            search=search,
            skip=skip,
            limit=limit,
        )
        
        return ListGroupsResponse(
            groups=groups,
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list groups: {str(e)}"
        )


@router.get("/{group_id}", response_model=IndividualGroupResponse)
async def get_group(
    group_id: str,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> IndividualGroupResponse:
    """
    Get a single group by ID.
    
    Args:
        group_id: Group identifier
        manager: IndividualGroupsManager dependency
        
    Returns:
        Group with member summary
    """
    try:
        group = await manager.get_group(group_id)
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {group_id}"
            )
        
        # Get member preview
        members_preview, _ = await manager.get_group_members(
            group_id, skip=0, limit=5
        )
        
        return IndividualGroupResponse(
            group=group,
            members_preview=members_preview,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get group: {str(e)}"
        )


@router.patch("/{group_id}", response_model=IndividualGroup)
async def update_group(
    group_id: str,
    request: UpdateIndividualGroupRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> IndividualGroup:
    """
    Update a group's metadata.
    
    Args:
        group_id: Group identifier
        request: Update parameters
        manager: IndividualGroupsManager dependency
        
    Returns:
        Updated group
    """
    try:
        group = await manager.update_group(group_id, request)
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {group_id}"
            )
        
        return group
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update group: {str(e)}"
        )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    remove_members: bool = Query(False, description="Also delete membership records"),
    manager: IndividualGroupsManager = Depends(get_groups_manager),
):
    """
    Delete a group.
    
    Args:
        group_id: Group identifier
        remove_members: If True, also removes membership records
        manager: IndividualGroupsManager dependency
    """
    try:
        deleted = await manager.delete_group(group_id, remove_members=remove_members)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {group_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete group: {str(e)}"
        )


# ================================================================
# Member Management Endpoints
# ================================================================

@router.get("/{group_id}/members", response_model=ListMembersResponse)
async def get_group_members(
    group_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort: str = Query("added_date", regex="^(added_date|appearances|last_seen)$"),
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> ListMembersResponse:
    """
    Get members of a group.
    
    Args:
        group_id: Group identifier
        skip: Pagination offset
        limit: Page size
        sort: Sort field
        manager: IndividualGroupsManager dependency
        
    Returns:
        List of members with pagination info
    """
    try:
        members, total = await manager.get_group_members(
            group_id, skip=skip, limit=limit, sort=sort
        )
        
        return ListMembersResponse(
            members=members,
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting members for group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get group members: {str(e)}"
        )


@router.post("/{group_id}/members", response_model=AddMembersResponse)
async def add_members(
    group_id: str,
    request: AddGroupMembersRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> AddMembersResponse:
    """
    Add members to a group.
    
    Args:
        group_id: Group identifier
        request: Members to add
        manager: IndividualGroupsManager dependency
        
    Returns:
        Response with counts of added/skipped members
    """
    try:
        response = await manager.add_members(
            group_id=group_id,
            individual_ids=request.individual_ids,
            added_by="default_user",  # TODO: Get from auth context
            notes=request.notes,
        )
        
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding members to group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add members: {str(e)}"
        )


@router.delete("/{group_id}/members", response_model=RemoveMembersResponse)
async def remove_members(
    group_id: str,
    request: RemoveGroupMembersRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> RemoveMembersResponse:
    """
    Remove members from a group.
    
    Args:
        group_id: Group identifier
        request: Members to remove
        manager: IndividualGroupsManager dependency
        
    Returns:
        Response with count of removed members
    """
    try:
        response = await manager.remove_members(
            group_id=group_id,
            individual_ids=request.individual_ids,
        )
        
        return response
    except Exception as e:
        logger.error(f"Error removing members from group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove members: {str(e)}"
        )


# ================================================================
# Individual-Centric Endpoints
# ================================================================

@router.get("/individuals/{individual_id}/groups", response_model=List[IndividualGroup])
async def get_individual_groups(
    individual_id: str,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> List[IndividualGroup]:
    """
    Get all groups an individual belongs to.
    
    Args:
        individual_id: Individual identifier
        manager: IndividualGroupsManager dependency
        
    Returns:
        List of groups
    """
    try:
        groups = await manager.get_individual_groups(individual_id)
        return groups
    except Exception as e:
        logger.error(f"Error getting groups for individual {individual_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get individual groups: {str(e)}"
        )


# ================================================================
# Bulk Operations
# ================================================================

@router.post("/bulk/add-members", response_model=BulkAddMembersResponse)
async def bulk_add_members(
    request: BulkAddMembersRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> BulkAddMembersResponse:
    """
    Bulk add individuals to a group.
    
    Args:
        request: Bulk operation parameters
        manager: IndividualGroupsManager dependency
        
    Returns:
        Response with success/error counts
    """
    try:
        response = await manager.add_members(
            group_id=request.group_id,
            individual_ids=request.individual_ids,
            added_by="default_user",  # TODO: Get from auth context
        )
        
        return BulkAddMembersResponse(
            success_count=response.added_count,
            error_count=response.skipped_count,
            errors=[],
        )
    except Exception as e:
        logger.error(f"Error in bulk add members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk add members: {str(e)}"
        )


@router.post("/bulk/assign-groups", response_model=BulkAssignGroupsResponse)
async def bulk_assign_groups(
    request: BulkAssignGroupsRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> BulkAssignGroupsResponse:
    """
    Bulk assign individuals to multiple groups.
    
    Args:
        request: Bulk assignment parameters
        manager: IndividualGroupsManager dependency
        
    Returns:
        Response with assignment counts
    """
    try:
        total_assignments = 0
        
        for group_id in request.group_ids:
            response = await manager.add_members(
                group_id=group_id,
                individual_ids=request.individual_ids,
                added_by="default_user",  # TODO: Get from auth context
            )
            total_assignments += response.added_count
        
        return BulkAssignGroupsResponse(
            assignments_created=total_assignments,
            individuals_updated=len(request.individual_ids),
        )
    except Exception as e:
        logger.error(f"Error in bulk assign groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk assign groups: {str(e)}"
        )


# ================================================================
# Camera Search Endpoint
# ================================================================

@router.post("/{group_id}/camera-search", response_model=GroupCameraSearchResponse)
async def search_group_in_camera(
    group_id: str,
    request_body: GroupCameraSearchRequest,
    request: Request,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> GroupCameraSearchResponse:
    """
    Search for group members within specific camera footage during a time range.
    
    This endpoint:
    1. Fetches all member individual_uuids for the group
    2. Executes MVR search on specified camera/time range
    3. Compares MVR results with group members
    4. Returns matched individuals with appearance data
    
    Args:
        group_id: Group identifier
        request_body: Camera search parameters
        request: FastAPI Request object to extract auth token
        manager: IndividualGroupsManager dependency
        
    Returns:
        Matched group members found in camera footage
    """
    try:
        # Extract auth token from request headers
        auth_token = request.headers.get("Authorization")
        logger.info(f"Camera search request - auth_token present: {bool(auth_token)}, length: {len(auth_token) if auth_token else 0}")
        
        response = await manager.search_members_in_camera(
            group_id=group_id,
            camera_id=request_body.camera_id,
            start_time=request_body.start_time,
            end_time=request_body.end_time,
            confidence_threshold=request_body.confidence_threshold,
            auth_token=auth_token,
        )
        
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in camera search for group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute camera search: {str(e)}"
        )

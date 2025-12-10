"""
User Trigger Actions API Routes

CRUD endpoints for user-defined trigger actions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import math

from ..database import get_db
from ..models.user_trigger_action import UserTriggerAction
from ..schemas.user_trigger_action import (
    UserTriggerActionCreate,
    UserTriggerActionUpdate,
    UserTriggerActionResponse,
    UserTriggerActionListResponse,
    UserTriggerActionStatsResponse,
)

router = APIRouter(prefix="/api/v1/user-actions", tags=["user-actions"])


@router.post("/", response_model=UserTriggerActionResponse, status_code=201)
async def create_user_action(
    action: UserTriggerActionCreate,
    db: Session = Depends(get_db)
):
    """Create a new user-defined trigger action"""
    try:
        db_action = UserTriggerAction(**action.dict())
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        return db_action
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create action: {str(e)}")


@router.get("/", response_model=UserTriggerActionListResponse)
async def list_user_actions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    db: Session = Depends(get_db)
):
    """List user-defined trigger actions with pagination and filtering"""
    try:
        # Build query
        query = db.query(UserTriggerAction)
        
        # Apply filters
        if is_active is not None:
            query = query.filter(UserTriggerAction.is_active == is_active)
        if action_type:
            query = query.filter(UserTriggerAction.action_type == action_type)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        actions = query.order_by(UserTriggerAction.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return UserTriggerActionListResponse(
            actions=actions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list actions: {str(e)}")


@router.get("/{uuid}", response_model=UserTriggerActionResponse)
async def get_user_action(
    uuid: str,
    db: Session = Depends(get_db)
):
    """Get a single user-defined trigger action by UUID"""
    action = db.query(UserTriggerAction).filter(UserTriggerAction.uuid == uuid).first()
    if not action:
        raise HTTPException(status_code=404, detail=f"Action with UUID {uuid} not found")
    return action


@router.put("/{uuid}", response_model=UserTriggerActionResponse)
async def update_user_action(
    uuid: str,
    action_update: UserTriggerActionUpdate,
    db: Session = Depends(get_db)
):
    """Update a user-defined trigger action"""
    action = db.query(UserTriggerAction).filter(UserTriggerAction.uuid == uuid).first()
    if not action:
        raise HTTPException(status_code=404, detail=f"Action with UUID {uuid} not found")
    
    try:
        # Update fields if provided
        update_data = action_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(action, field, value)
        
        db.commit()
        db.refresh(action)
        return action
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update action: {str(e)}")


@router.patch("/{uuid}/toggle", response_model=UserTriggerActionResponse)
async def toggle_user_action(
    uuid: str,
    db: Session = Depends(get_db)
):
    """Toggle the active status of a user-defined trigger action"""
    action = db.query(UserTriggerAction).filter(UserTriggerAction.uuid == uuid).first()
    if not action:
        raise HTTPException(status_code=404, detail=f"Action with UUID {uuid} not found")
    
    try:
        action.is_active = not action.is_active
        db.commit()
        db.refresh(action)
        return action
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to toggle action: {str(e)}")


@router.delete("/{uuid}", status_code=204)
async def delete_user_action(
    uuid: str,
    db: Session = Depends(get_db)
):
    """Delete a user-defined trigger action"""
    action = db.query(UserTriggerAction).filter(UserTriggerAction.uuid == uuid).first()
    if not action:
        raise HTTPException(status_code=404, detail=f"Action with UUID {uuid} not found")
    
    try:
        db.delete(action)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete action: {str(e)}")


@router.get("/stats/summary", response_model=UserTriggerActionStatsResponse)
async def get_user_action_stats(
    db: Session = Depends(get_db)
):
    """Get statistics summary for user-defined trigger actions"""
    try:
        total = db.query(UserTriggerAction).count()
        active = db.query(UserTriggerAction).filter(UserTriggerAction.is_active == True).count()
        inactive = total - active
        
        # Count by action type
        by_type_query = db.query(
            UserTriggerAction.action_type,
            func.count(UserTriggerAction.id)
        ).group_by(UserTriggerAction.action_type).all()
        
        by_type = {action_type: count for action_type, count in by_type_query}
        
        return UserTriggerActionStatsResponse(
            total=total,
            active=active,
            inactive=inactive,
            by_type=by_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

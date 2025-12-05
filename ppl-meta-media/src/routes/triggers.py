"""
API routes for Trigger management.
"""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.trigger import Trigger
from ..schemas.trigger import (
    TriggerCreate,
    TriggerListResponse,
    TriggerResponse,
    TriggerUpdate,
)

router = APIRouter(prefix="/api/v1/triggers", tags=["triggers"])


@router.post("", response_model=TriggerResponse, status_code=201)
async def create_trigger(
    trigger: TriggerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new trigger.
    
    - **person_count_operator**: Comparison operator (less_than, more_than, equals, between)
    - **person_count_value**: Threshold value (e.g., '5', '10-20' for between)
    - **age_range**: Age range filter (underage, adults, seniors, all)
    - **time_span**: Time when active (e.g., 'Mon-Fri 09:00-17:00')
    - **media_source_uuid**: UUID of camera/media collection
    - **action**: Action to execute (alert, email, webhook, log)
    - **is_active**: Whether trigger is active
    """
    db_trigger = Trigger(**trigger.model_dump())
    db.add(db_trigger)
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.get("", response_model=TriggerListResponse)
async def list_triggers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    db: Session = Depends(get_db)
):
    """
    List all triggers with pagination and optional filtering.
    
    Returns paginated list of triggers with metadata.
    """
    query = db.query(Trigger)
    
    # Apply filters
    if is_active is not None:
        query = query.filter(Trigger.is_active == is_active)
    if action:
        query = query.filter(Trigger.action == action)
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    
    # Get page results
    triggers = query.order_by(Trigger.created_at.desc()).offset(offset).limit(page_size).all()
    
    return TriggerListResponse(
        triggers=triggers,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{trigger_uuid}", response_model=TriggerResponse)
async def get_trigger(
    trigger_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific trigger by UUID.
    """
    trigger = db.query(Trigger).filter(Trigger.uuid == trigger_uuid).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return trigger


@router.put("/{trigger_uuid}", response_model=TriggerResponse)
async def update_trigger(
    trigger_uuid: UUID,
    trigger_update: TriggerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a trigger.
    
    Only provided fields will be updated.
    """
    db_trigger = db.query(Trigger).filter(Trigger.uuid == trigger_uuid).first()
    if not db_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    # Update only provided fields
    update_data = trigger_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trigger, field, value)
    
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.patch("/{trigger_uuid}/toggle", response_model=TriggerResponse)
async def toggle_trigger(
    trigger_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Toggle trigger active status.
    
    Convenience endpoint to activate/deactivate a trigger.
    """
    db_trigger = db.query(Trigger).filter(Trigger.uuid == trigger_uuid).first()
    if not db_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    db_trigger.is_active = not db_trigger.is_active
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.delete("/{trigger_uuid}", status_code=204)
async def delete_trigger(
    trigger_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a trigger.
    """
    db_trigger = db.query(Trigger).filter(Trigger.uuid == trigger_uuid).first()
    if not db_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    db.delete(db_trigger)
    db.commit()
    return None


@router.get("/stats/summary")
async def get_trigger_stats(
    db: Session = Depends(get_db)
):
    """
    Get trigger statistics summary.
    
    Returns counts by status, action type, etc.
    """
    total = db.query(func.count(Trigger.id)).scalar()
    active = db.query(func.count(Trigger.id)).filter(Trigger.is_active == True).scalar()
    inactive = total - active
    
    # Count by action type
    action_counts = db.query(
        Trigger.action,
        func.count(Trigger.id)
    ).group_by(Trigger.action).all()
    
    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "by_action": {action: count for action, count in action_counts}
    }

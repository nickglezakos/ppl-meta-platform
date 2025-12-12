"""
API routes for Trigger management.
"""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.trigger import Trigger
from ..models.user_trigger_action import UserTriggerAction
from ..schemas.trigger import (
    CounterDataRequest,
    TriggerCreate,
    TriggerEvaluationResponse,
    TriggerEvaluationResult,
    TriggerListResponse,
    TriggerResponse,
    TriggerUpdate,
)
from ..services.trigger_evaluation import CounterData, TriggerEvaluationService

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
    - **camera_device_id**: Device ID of camera (e.g., 'usb_camera_0')
    - **action**: Action to execute (alert, email, webhook, log)
    - **is_active**: Whether trigger is active
    """
    try:
        db_trigger = Trigger(**trigger.model_dump())
        db.add(db_trigger)
        db.commit()
        db.refresh(db_trigger)
        return db_trigger
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Error creating trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    
    Returns paginated list of triggers with metadata and linked action names.
    """
    query = db.query(Trigger).options(joinedload(Trigger.user_action))
    
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
    
    # Populate action_name from user_action relationship
    trigger_responses = []
    for trigger in triggers:
        trigger_dict = {
            **{c.name: getattr(trigger, c.name) for c in trigger.__table__.columns},
            'action_name': trigger.user_action.name if trigger.user_action else None
        }
        trigger_responses.append(TriggerResponse(**trigger_dict))
    
    return TriggerListResponse(
        triggers=trigger_responses,
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
    Get a specific trigger by UUID with linked action name.
    """
    trigger = db.query(Trigger).options(joinedload(Trigger.user_action)).filter(Trigger.uuid == trigger_uuid).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    # Populate action_name from user_action relationship
    trigger_dict = {
        **{c.name: getattr(trigger, c.name) for c in trigger.__table__.columns},
        'action_name': trigger.user_action.name if trigger.user_action else None
    }
    return TriggerResponse(**trigger_dict)


@router.put("/{trigger_uuid}", response_model=TriggerResponse)
async def update_trigger(
    trigger_uuid: UUID,
    trigger_update: TriggerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a trigger with linked action name.
    
    Only provided fields will be updated.
    """
    db_trigger = db.query(Trigger).options(joinedload(Trigger.user_action)).filter(Trigger.uuid == trigger_uuid).first()
    if not db_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    # Update only provided fields
    update_data = trigger_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trigger, field, value)
    
    db.commit()
    db.refresh(db_trigger)
    
    # Reload to ensure relationship is fresh
    db_trigger = db.query(Trigger).options(joinedload(Trigger.user_action)).filter(Trigger.uuid == trigger_uuid).first()
    
    # Populate action_name from user_action relationship
    trigger_dict = {
        **{c.name: getattr(db_trigger, c.name) for c in db_trigger.__table__.columns},
        'action_name': db_trigger.user_action.name if db_trigger.user_action else None
    }
    return TriggerResponse(**trigger_dict)


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


@router.post("/evaluate", response_model=TriggerEvaluationResponse)
async def evaluate_triggers(
    counter_data: CounterDataRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate all active triggers for a camera based on counter data.
    
    This endpoint receives camera counter data (total count, age/gender distribution)
    and evaluates all active triggers associated with that camera. Returns detailed
    results showing which triggers passed/failed and why.
    
    **Input**: Counter data from camera (total_count, age_distribution, gender_distribution)
    **Output**: Evaluation results with pass/fail status for each trigger
    
    Example request:
    ```json
    {
        "camera_device_id": "usb_camera_0",
        "total_count": 25,
        "age_distribution": {
            "0-18": 5,
            "19-30": 10,
            "31-50": 8,
            "51+": 2
        },
        "gender_distribution": {
            "male": 12,
            "female": 13
        }
    }
    ```
    """
    try:
        # Convert Pydantic model to service CounterData
        counter = CounterData(
            camera_device_id=counter_data.camera_device_id,
            total_count=counter_data.total_count,
            age_distribution=counter_data.age_distribution,
            gender_distribution=counter_data.gender_distribution,
            timestamp=counter_data.timestamp
        )
        
        # Evaluate triggers
        evaluation_service = TriggerEvaluationService(db)
        results = evaluation_service.evaluate_all_active_triggers(counter)
    except Exception as e:
        import logging
        logging.error(f"Error evaluating triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Convert results to response format
    evaluation_results = []
    for trigger, passed, reason in results:
        evaluation_results.append(
            TriggerEvaluationResult(
                trigger_uuid=trigger.uuid,
                trigger_name=trigger.name,
                passed=passed,
                reason=reason,
                person_count=counter_data.total_count,
                timestamp=counter.timestamp
            )
        )
    
    # Count passed triggers
    triggers_passed = sum(1 for _, passed, _ in results if passed)
    
    return TriggerEvaluationResponse(
        camera_device_id=counter_data.camera_device_id,
        total_count=counter_data.total_count,
        evaluated_at=counter.timestamp,
        triggers_evaluated=len(results),
        triggers_passed=triggers_passed,
        results=evaluation_results
    )

"""
API routes for Trigger management.
"""

import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.trigger import Trigger
from ..models.user_trigger_action import UserTriggerAction
from ..schemas.trigger import (
    CounterDataRequest,
    InstantDetectionPayload,
    TriggerCreate,
    TriggerEvaluationResponse,
    TriggerEvaluationResult,
    TriggerListResponse,
    TriggerResponse,
    TriggerUpdate,
)
from ..services.trigger_evaluation import CounterData, TriggerEvaluationService

logger = logging.getLogger(__name__)
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


@router.post("/instant-detection")
async def process_instant_detection_webhook(
    payload: InstantDetectionPayload,
    db: Session = Depends(get_db)
):
    """
    Webhook receiver for camera instant detection demographics.
    
    Receives real-time demographic data from camera service and evaluates
    demographic-enabled triggers to control signage playback.
    
    **Flow**:
    1. Camera POSTs demographics every ~5 seconds
    2. Find active triggers with enable_demographic_conditions=true
    3. Evaluate demographic_conditions JSON (AND logic)
    4. Check cooldown period (last_fired_at + cooldown_seconds)
    5. If passed: Execute signage action, update last_fired_at
    
    **Demographic Conditions Format**:
    ```json
    [
        {"field": "percent_male", "operator": "gte", "value": 60},
        {"field": "percent_female", "operator": "lte", "value": 40}
    ]
    ```
    
    **Supported Fields**:
    - people_count: Total person count
    - percent_male: Male percentage (0-100)
    - percent_female: Female percentage (0-100)
    - age_18_25, age_26_40, age_41_60, age_60_plus: Age group counts
    
    **Operators**: gt, gte, lt, lte, eq
    """
    logger.info("="*80)
    logger.info(f"📥 INSTANT DETECTION WEBHOOK RECEIVED")
    logger.info("="*80)
    logger.info(f"Camera ID: {payload.camera_id}")
    logger.info(f"Timestamp: {payload.timestamp}")
    logger.info(f"People Count: {payload.people_count} (type: {type(payload.people_count).__name__})")
    logger.info(f"Demographics: {json.dumps(payload.demographics, indent=2)}")
    logger.info("="*80)
    
    try:
        # Find active demographic-enabled triggers for this camera
        logger.info(f"🔍 Querying database for active triggers...")
        triggers = db.query(Trigger).filter(
            Trigger.camera_device_id == payload.camera_id,
            Trigger.is_active == True,
            Trigger.enable_demographic_conditions == True
        ).all()
        
        if not triggers:
            logger.debug(f"No demographic triggers found for camera {payload.camera_id}")
            return {
                "status": "ok",
                "camera_id": payload.camera_id,
                "triggers_evaluated": 0,
                "triggers_fired": 0
            }
        
        logger.info(f"Found {len(triggers)} demographic triggers to evaluate")
        
        triggered_count = 0
        evaluation_results = []
        
        for trigger in triggers:
            try:
                # Check cooldown
                if trigger.last_fired_at and trigger.cooldown_seconds:
                    time_since_last_fire = (datetime.now(timezone.utc) - trigger.last_fired_at).total_seconds()
                    if time_since_last_fire < trigger.cooldown_seconds:
                        remaining = trigger.cooldown_seconds - time_since_last_fire
                        logger.debug(
                            f"Trigger '{trigger.name}' in cooldown: "
                            f"{remaining:.1f}s remaining"
                        )
                        evaluation_results.append({
                            "trigger_uuid": str(trigger.uuid),
                            "trigger_name": trigger.name,
                            "passed": False,
                            "reason": f"Cooldown active ({remaining:.1f}s remaining)"
                        })
                        continue
                
                # Parse and evaluate demographic conditions
                if not trigger.demographic_conditions:
                    logger.warning(f"Trigger '{trigger.name}' has no demographic conditions")
                    continue
                
                conditions = json.loads(trigger.demographic_conditions)
                passed = await _evaluate_demographic_conditions(
                    conditions=conditions,
                    people_count=payload.people_count,
                    demographics=payload.demographics
                )
                
                if passed:
                    logger.info("="*80)
                    logger.info(f"🔥 TRIGGER FIRED! 🔥")
                    logger.info("="*80)
                    logger.info(f"Trigger ID: {trigger.id}")
                    logger.info(f"Trigger UUID: {trigger.uuid}")
                    logger.info(f"Trigger Name: {trigger.name}")
                    logger.info(f"Camera: {payload.camera_id}")
                    logger.info(f"People Count: {payload.people_count}")
                    logger.info(f"Demographics: {payload.demographics}")
                    logger.info("="*80)
                    
                    # Execute signage action
                    logger.info(f"▶️ Calling signage action execution...")
                    await _execute_signage_action(
                        trigger=trigger,
                        camera_id=payload.camera_id
                    )
                    logger.info(f"✅ Signage action execution completed")
                    
                    # Update last_fired_at
                    old_last_fired = trigger.last_fired_at
                    trigger.last_fired_at = datetime.now(timezone.utc)
                    db.commit()
                    logger.info(
                        f"📝 Updated trigger last_fired_at: "
                        f"{old_last_fired} → {trigger.last_fired_at}"
                    )
                    
                    triggered_count += 1
                    evaluation_results.append({
                        "trigger_uuid": str(trigger.uuid),
                        "trigger_name": trigger.name,
                        "passed": True,
                        "reason": "All demographic conditions met"
                    })
                else:
                    logger.debug(f"Trigger '{trigger.name}' FAILED - Conditions not met")
                    evaluation_results.append({
                        "trigger_uuid": str(trigger.uuid),
                        "trigger_name": trigger.name,
                        "passed": False,
                        "reason": "Demographic conditions not met"
                    })
                    
            except Exception as e:
                logger.error(f"Error evaluating trigger '{trigger.name}': {e}")
                evaluation_results.append({
                    "trigger_uuid": str(trigger.uuid),
                    "trigger_name": trigger.name,
                    "passed": False,
                    "reason": f"Evaluation error: {str(e)}"
                })
        
        logger.info(
            f"Webhook processing complete: {len(triggers)} evaluated, "
            f"{triggered_count} fired"
        )
        
        return {
            "status": "ok",
            "camera_id": payload.camera_id,
            "timestamp": payload.timestamp,
            "people_count": payload.people_count,
            "triggers_evaluated": len(triggers),
            "triggers_fired": triggered_count,
            "results": evaluation_results
        }
        
    except Exception as e:
        logger.error(f"Error processing instant detection webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _evaluate_demographic_conditions(
    conditions: List[Dict[str, Any]],
    people_count: int,
    demographics: Dict[str, Any]
) -> bool:
    """
    Evaluate demographic conditions with AND logic.
    
    Args:
        conditions: List of condition dicts with field, operator, value
        people_count: Total person count
        demographics: Demographics dict from camera payload
        
    Returns:
        True if ALL conditions pass (AND logic), False otherwise
    """
    if not conditions:
        logger.warning("No conditions provided - defaulting to False")
        return False
    
    for condition in conditions:
        field = condition.get("field")
        operator = condition.get("operator")
        threshold = condition.get("value")
        
        # Get actual value from demographics or people_count
        if field == "people_count":
            actual_value = people_count
        else:
            actual_value = demographics.get(field)
            
        if actual_value is None:
            logger.warning(f"Field '{field}' not found in demographics")
            return False
        
        # Log data types for debugging
        logger.info(
            f"🔍 Evaluating: field='{field}', operator='{operator}', "
            f"threshold={threshold} (type={type(threshold).__name__}), "
            f"actual_value={actual_value} (type={type(actual_value).__name__})"
        )
        
        # Evaluate operator
        passed = False
        if operator == "gt":
            passed = actual_value > threshold
        elif operator == "gte":
            passed = actual_value >= threshold
        elif operator == "lt":
            passed = actual_value < threshold
        elif operator == "lte":
            passed = actual_value <= threshold
        elif operator == "eq":
            passed = actual_value == threshold
        else:
            logger.warning(f"Unknown operator '{operator}'")
            return False
        
        logger.info(
            f"{'✅' if passed else '❌'} Condition result: "
            f"{field} {operator} {threshold} (actual={actual_value}) -> {passed}"
        )
        
        if not passed:
            logger.info("Condition FAILED - returning False")
            return False  # AND logic - one failure means all fail
    
    return True  # All conditions passed


async def _execute_signage_action(
    trigger: Trigger,
    camera_id: str
):
    """
    Execute signage action using EXISTING playback control API.
    
    Calls the existing /api/v1/signage/playback/control endpoint
    to switch playlists on registered signage devices.
    
    Args:
        trigger: Trigger with signage configuration
        camera_id: Camera that triggered the action
    """
    logger.info("="*80)
    logger.info(f"🎬 EXECUTING SIGNAGE ACTION")
    logger.info("="*80)
    logger.info(f"Trigger ID: {trigger.id}")
    logger.info(f"Trigger UUID: {trigger.uuid}")
    logger.info(f"Trigger Name: {trigger.name}")
    logger.info(f"Camera ID: {camera_id}")
    logger.info(f"Target Playlist UUID: {trigger.signage_playlist_id}")
    logger.info(f"Target Device IDs: {trigger.signage_device_ids}")
    logger.info(f"Transition Mode: {trigger.signage_transition_mode}")
    logger.info(f"Fade Duration: {trigger.signage_fade_duration_ms}ms")
    logger.info("="*80)
    
    if not trigger.signage_device_ids or not trigger.signage_playlist_id:
        logger.error(
            f"❌ Trigger '{trigger.name}' missing signage configuration: "
            f"device_ids={trigger.signage_device_ids}, playlist_id={trigger.signage_playlist_id}"
        )
        return
    
    # Parse device IDs from JSON string
    try:
        logger.info(f"📋 Parsing device IDs from: {trigger.signage_device_ids} (type: {type(trigger.signage_device_ids)})")
        device_ids = json.loads(trigger.signage_device_ids)
        if not isinstance(device_ids, list):
            device_ids = [device_ids]
        logger.info(f"✅ Parsed device IDs: {device_ids}")
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"⚠️ JSON parse failed ({e}), treating as raw value")
        # If it's already a list or single string
        device_ids = trigger.signage_device_ids if isinstance(trigger.signage_device_ids, list) else [trigger.signage_device_ids]
        logger.info(f"📋 Using device IDs: {device_ids}")
    
    logger.info(
        f"📺 Preparing signage API call: playlist={trigger.signage_playlist_id}, "
        f"devices={device_ids}, mode={trigger.signage_transition_mode}"
    )
    
    # Call EXISTING signage playback control API
    signage_api_url = "http://localhost:8000/api/v1/signage/playback/control"
    
    payload = {
        "device_ids": device_ids,  # List of device UUIDs
        "command": "start",  # Start playing the video list
        "video_list_id": trigger.signage_playlist_id,  # Video list UUID
        "parameters": {
            "transition_mode": trigger.signage_transition_mode or "immediate",
            "fade_duration_ms": trigger.signage_fade_duration_ms or 2000,
            "volume": 80,  # Default volume
            "start_index": 0,  # Start from first video
            # Include trigger metadata for auditing
            "triggered_by": {
                "trigger_uuid": str(trigger.uuid),
                "trigger_name": trigger.name,
                "camera_id": camera_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    }
    
    logger.info(f"🌐 Calling signage API: {signage_api_url}")
    logger.info(f"📦 Request payload:")
    logger.info(json.dumps(payload, indent=2))
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            logger.info(f"⏳ Sending POST request to {signage_api_url}...")
            response = await client.post(signage_api_url, json=payload)
            logger.info(f"📨 Response received: HTTP {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Signage API call successful!")
                logger.info(f"   Affected devices: {result.get('affected_devices', 0)}/{len(device_ids)}")
                logger.info(f"   Status: {result.get('status')}")
                logger.info(f"   Message: {result.get('message')}")
                logger.info(f"   Full response: {json.dumps(result, indent=2)}")
            else:
                logger.error(
                    f"❌ Signage API returned error {response.status_code}"
                )
                logger.error(f"   Response body: {response.text}")
                
        except httpx.TimeoutException:
            logger.error(
                f"❌ Signage API timeout after 5s - service may be down"
            )
            logger.error(f"   URL: {signage_api_url}")
            logger.error(f"   This means the media service's signage playback endpoint didn't respond")
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error calling signage API: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   URL: {signage_api_url}")
        except Exception as e:
            logger.error(f"❌ Unexpected error calling signage API: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   URL: {signage_api_url}")
            import traceback
            logger.error(f"   Traceback:\n{traceback.format_exc()}")
    
    logger.info("="*80)
    logger.info(f"🎬 SIGNAGE ACTION EXECUTION COMPLETE")
    logger.info("="*80)

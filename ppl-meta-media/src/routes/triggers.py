"""
API routes for Trigger management.
"""

import json
import logging
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.trigger import Trigger
from ..models.trigger_execution_log import TriggerExecutionLog
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
from ..services.trigger_evaluation import DemographicData, TriggerEvaluationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/triggers", tags=["triggers"])


def _build_ppl_match_reason(best_match: Dict[str, Any]) -> str:
    similarity_score = best_match.get("similarity_score")
    matched_member_uuid = best_match.get("matched_member_uuid")
    existing_member_name = (best_match.get("existing_member_name") or "").strip()
    group_member_number_raw = best_match.get("group_member_number")

    group_member_number: Optional[int] = None
    if isinstance(group_member_number_raw, int):
        group_member_number = group_member_number_raw
    elif isinstance(group_member_number_raw, str) and group_member_number_raw.isdigit():
        group_member_number = int(group_member_number_raw)

    descriptor: Optional[str] = None
    if group_member_number is not None:
        descriptor = f"Group Member {group_member_number:02d}"

    if existing_member_name:
        descriptor = f"{descriptor} ({existing_member_name})" if descriptor else existing_member_name

    if not descriptor and matched_member_uuid:
        descriptor = f"member {matched_member_uuid}"

    if not descriptor:
        descriptor = "member"

    return f"Matched {descriptor} score={similarity_score}"


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
        trigger_data = trigger.model_dump()
        
        # Convert demographic_conditions list to JSON string for storage
        if 'demographic_conditions' in trigger_data and trigger_data['demographic_conditions'] is not None:
            trigger_data['demographic_conditions'] = json.dumps([
                cond.model_dump() if hasattr(cond, 'model_dump') else cond
                for cond in trigger_data['demographic_conditions']
            ])
        
        db_trigger = Trigger(**trigger_data)
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
    
    # Convert demographic_conditions list to JSON string for storage
    if 'demographic_conditions' in update_data and update_data['demographic_conditions'] is not None:
        import json
        update_data['demographic_conditions'] = json.dumps([
            cond.model_dump() if hasattr(cond, 'model_dump') else cond
            for cond in update_data['demographic_conditions']
        ])
    
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
        # Convert old CounterDataRequest format to new DemographicData format
        demographics = {}
        
        # Convert gender distribution to percentages
        if counter_data.gender_distribution:
            total = counter_data.total_count or sum(counter_data.gender_distribution.values())
            if total > 0:
                demographics['percent_male'] = (counter_data.gender_distribution.get('male', 0) / total) * 100
                demographics['percent_female'] = (counter_data.gender_distribution.get('female', 0) / total) * 100
        
        # Convert age distribution to percentages (map old ranges to new ranges)
        if counter_data.age_distribution:
            total = counter_data.total_count or sum(counter_data.age_distribution.values())
            if total > 0:
                # Map old age ranges to new format
                demographics['percent_age_0_12'] = (counter_data.age_distribution.get('0-18', 0) / total) * 100 * 0.7  # approximate
                demographics['percent_age_13_17'] = (counter_data.age_distribution.get('0-18', 0) / total) * 100 * 0.3  # approximate
                demographics['percent_age_18_24'] = (counter_data.age_distribution.get('19-30', 0) / total) * 100 * 0.5
                demographics['percent_age_25_34'] = (counter_data.age_distribution.get('19-30', 0) / total) * 100 * 0.5 + (counter_data.age_distribution.get('31-50', 0) / total) * 100 * 0.2
                demographics['percent_age_35_44'] = (counter_data.age_distribution.get('31-50', 0) / total) * 100 * 0.5
                demographics['percent_age_45_54'] = (counter_data.age_distribution.get('31-50', 0) / total) * 100 * 0.3 + (counter_data.age_distribution.get('51+', 0) / total) * 100 * 0.3
                demographics['percent_age_55_64'] = (counter_data.age_distribution.get('51+', 0) / total) * 100 * 0.4
                demographics['percent_age_65_plus'] = (counter_data.age_distribution.get('51+', 0) / total) * 100 * 0.3
        
        demographic_data = DemographicData(
            camera_device_id=counter_data.camera_device_id,
            people_count=counter_data.total_count,
            demographics=demographics,
            timestamp=counter_data.timestamp
        )
        
        # Evaluate triggers
        evaluation_service = TriggerEvaluationService(db)
        results = evaluation_service.evaluate_all_active_triggers(demographic_data)
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
                timestamp=counter_data.timestamp
            )
        )
    
    # Count passed triggers
    triggers_passed = sum(1 for _, passed, _ in results if passed)
    
    return TriggerEvaluationResponse(
        camera_device_id=counter_data.camera_device_id,
        total_count=counter_data.total_count,
        evaluated_at=counter_data.timestamp,
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
        # Find active triggers for this camera
        logger.info(f"🔍 Querying database for active triggers...")
        triggers = db.query(Trigger).filter(
            Trigger.camera_device_id == payload.camera_id,
            Trigger.is_active == True
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
                        _persist_trigger_execution_log(
                            db=db,
                            trigger=trigger,
                            passed=False,
                            reason=f"Cooldown active ({remaining:.1f}s remaining)",
                            payload=payload,
                            match_info=None,
                            action_executed=False,
                        )
                        evaluation_results.append({
                            "trigger_uuid": str(trigger.uuid),
                            "trigger_name": trigger.name,
                            "passed": False,
                            "reason": f"Cooldown active ({remaining:.1f}s remaining)"
                        })
                        continue
                
                trigger_mode = (getattr(trigger, "trigger_mode", None) or "demographic").lower()
                match_info = None

                if trigger_mode == "ppl_match":
                    passed, reason, match_info = await _evaluate_ppl_match(
                        trigger=trigger,
                        payload=payload,
                    )
                    if not passed:
                        logger.debug(f"Trigger '{trigger.name}' FAILED - {reason}")
                        _persist_trigger_execution_log(
                            db=db,
                            trigger=trigger,
                            passed=False,
                            reason=reason,
                            payload=payload,
                            match_info=match_info,
                            action_executed=False,
                        )
                        evaluation_results.append({
                            "trigger_uuid": str(trigger.uuid),
                            "trigger_name": trigger.name,
                            "passed": False,
                            "reason": reason
                        })
                        continue
                else:
                    if not trigger.demographic_conditions:
                        logger.warning(f"Trigger '{trigger.name}' has no demographic conditions")
                        _persist_trigger_execution_log(
                            db=db,
                            trigger=trigger,
                            passed=False,
                            reason="No demographic conditions configured",
                            payload=payload,
                            match_info=None,
                            action_executed=False,
                        )
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
                    action_executed = False
                    logger.info(f"▶️ Calling signage action execution...")
                    await _execute_signage_action(
                        trigger=trigger,
                        camera_id=payload.camera_id
                    )
                    action_executed = True
                    logger.info(f"✅ Signage action execution completed")
                    
                    # Update last_fired_at
                    old_last_fired = trigger.last_fired_at
                    trigger.last_fired_at = datetime.now(timezone.utc)
                    if match_info is not None:
                        trigger.last_match_info = json.dumps(match_info)
                        trigger.last_matched_at = datetime.now(timezone.utc)

                    success_reason = reason if trigger_mode == "ppl_match" else "All demographic conditions met"

                    _persist_trigger_execution_log(
                        db=db,
                        trigger=trigger,
                        passed=True,
                        reason=success_reason,
                        payload=payload,
                        match_info=match_info,
                        action_executed=action_executed,
                    )
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
                        "reason": success_reason,
                        "match": match_info
                    })
                else:
                    logger.debug(f"Trigger '{trigger.name}' FAILED - Conditions not met")
                    _persist_trigger_execution_log(
                        db=db,
                        trigger=trigger,
                        passed=False,
                        reason="Demographic conditions not met",
                        payload=payload,
                        match_info=None,
                        action_executed=False,
                    )
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

        db.commit()
        
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


def _persist_trigger_execution_log(
    db: Session,
    trigger: Trigger,
    passed: bool,
    reason: str,
    payload: InstantDetectionPayload,
    match_info: Optional[Dict[str, Any]],
    action_executed: bool,
):
    source_mvr_uuids = payload.metadata.get("source_mvr_uuids", []) if payload.metadata else []
    source_mvr_uuid = None
    matched_group_id = None
    matched_member_uuid = None
    similarity_score = None
    threshold = None
    match_details_json = None

    if match_info:
        best_match = match_info.get("best_match") or {}
        source_mvr_uuid = best_match.get("source_mvr_uuid") or (source_mvr_uuids[0] if source_mvr_uuids else None)
        matched_group_id = match_info.get("group_id")
        matched_member_uuid = best_match.get("matched_member_uuid")
        similarity_score = best_match.get("similarity_score")
        threshold = match_info.get("threshold")
        match_details_json = json.dumps(match_info)
    elif source_mvr_uuids:
        source_mvr_uuid = source_mvr_uuids[0]

    db.add(TriggerExecutionLog(
        trigger_uuid=trigger.uuid,
        trigger_id=trigger.id,
        trigger_name=trigger.name,
        trigger_mode=(getattr(trigger, "trigger_mode", None) or "demographic"),
        camera_device_id=payload.camera_id,
        source_mvr_uuid=source_mvr_uuid,
        matched_group_id=matched_group_id,
        matched_member_uuid=matched_member_uuid,
        similarity_score=similarity_score,
        threshold=threshold,
        match_details_json=match_details_json,
        passed=passed,
        reason=reason,
        action_executed=action_executed,
        evaluated_at=datetime.now(timezone.utc),
    ))


async def _evaluate_ppl_match(
    trigger: Trigger,
    payload: InstantDetectionPayload,
) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Evaluate ppl-match mode by checking source MVR UUIDs against target group via vmeta duplicate-check endpoint.
    """
    group_id = getattr(trigger, "ppl_match_group_id", None)
    threshold = float(getattr(trigger, "ppl_match_similarity_threshold", 0.75) or 0.75)
    top_k = int(getattr(trigger, "ppl_match_top_k", 1) or 1)

    if not group_id:
        return False, "Missing ppl_match_group_id", None

    source_mvr_uuids = (
        payload.metadata.get("source_mvr_uuids", [])
        if payload.metadata else []
    )
    if not source_mvr_uuids:
        return False, "No source MVR UUIDs in evaluation context", None

    vmeta_service_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
    endpoint = f"{vmeta_service_url}/api/v1/individual-groups/{group_id}/check-duplicates"
    all_candidates: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            for source_mvr_uuid in source_mvr_uuids:
                response = await client.post(
                    endpoint,
                    json={
                        "candidate_mvr_uuid": source_mvr_uuid,
                        "similarity_threshold": threshold,
                    },
                )
                if response.status_code != 200:
                    logger.warning(
                        f"ppl_match duplicate-check failed for source {source_mvr_uuid}: "
                        f"{response.status_code} {response.text[:200]}"
                    )
                    continue

                data = response.json()
                if data.get("has_duplicates"):
                    for item in data.get("matches", []):
                        all_candidates.append({
                            "source_mvr_uuid": source_mvr_uuid,
                            "matched_member_uuid": item.get("existing_member_id"),
                            "similarity_score": item.get("similarity_score", 0.0),
                            "confidence": item.get("confidence"),
                            "existing_member_name": item.get("existing_member_name"),
                            "group_member_number": item.get("group_member_number"),
                        })
    except Exception as e:
        logger.error(f"Error evaluating ppl_match trigger '{trigger.name}': {e}", exc_info=True)
        return False, f"ppl_match evaluation error: {str(e)}", None

    if not all_candidates:
        return False, "No group matches above threshold", None

    all_candidates = sorted(
        all_candidates,
        key=lambda x: x.get("similarity_score", 0.0),
        reverse=True,
    )
    top_candidates = all_candidates[:top_k]
    best = top_candidates[0]

    match_info = {
        "mode": "ppl_match",
        "group_id": group_id,
        "threshold": threshold,
        "top_k": top_k,
        "matched": True,
        "best_match": best,
        "top_candidates": top_candidates,
        "evaluated_source_count": len(source_mvr_uuids),
        "matched_at": datetime.now(timezone.utc).isoformat(),
    }
    return True, _build_ppl_match_reason(best), match_info


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

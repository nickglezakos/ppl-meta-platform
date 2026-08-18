"""
API routes for Trigger management.
"""

import json
import asyncio
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

from ..config import get_config
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
from ..services.vprofile_match_worker import get_vprofile_worker
from ..services.communications_client import CommunicationsClient
from ..services.signage_service import SignagePlaybackService
from ..schemas.signage import PlaybackControlRequest, PlaybackCommand, PlaybackParameters

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/triggers", tags=["triggers"])

_communications_client: Optional[CommunicationsClient] = None

AGE_COUNT_TO_PERCENT_FIELD = {
    'age_count_0_12': 'percent_age_0_12',
    'age_count_13_17': 'percent_age_13_17',
    'age_count_18_24': 'percent_age_18_24',
    'age_count_25_34': 'percent_age_25_34',
    'age_count_35_44': 'percent_age_35_44',
    'age_count_45_54': 'percent_age_45_54',
    'age_count_55_64': 'percent_age_55_64',
    'age_count_65_plus': 'percent_age_65_plus',
}

LEGACY_PERCENT_AGE_FIELDS = set(AGE_COUNT_TO_PERCENT_FIELD.values())

# Midpoint ages used for computing weighted-average age from bracket percentages
AGE_BRACKET_MIDPOINTS = {
    'percent_age_0_12': 6.0,
    'percent_age_13_17': 15.0,
    'percent_age_18_24': 21.0,
    'percent_age_25_34': 29.5,
    'percent_age_35_44': 39.5,
    'percent_age_45_54': 49.5,
    'percent_age_55_64': 59.5,
    'percent_age_65_plus': 70.0,
}


def _get_communications_client() -> CommunicationsClient:
    global _communications_client
    if _communications_client is None:
        settings = get_config()
        _communications_client = CommunicationsClient(
            base_url=settings.COMMUNICATIONS_SERVICE_URL
        )
    return _communications_client


def _resolve_action_names(db: Session, trigger) -> Optional[List[str]]:
    """Resolve action_uuids JSON column to a list of action names."""
    raw = getattr(trigger, 'action_uuids', None)
    if not raw:
        # Fallback to legacy single action
        if trigger.user_action:
            return [trigger.user_action.name]
        return None
    try:
        uuids = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None
    if not uuids:
        return None
    actions = db.query(UserTriggerAction).filter(
        UserTriggerAction.uuid.in_(uuids)
    ).all()
    # Preserve ordering
    name_map = {str(a.uuid): a.name for a in actions}
    return [name_map[u] for u in uuids if u in name_map]


def _build_trigger_response_dict(db: Session, trigger) -> dict:
    """Build a response dict for a trigger, resolving action names."""
    trigger_dict = {
        **{c.name: getattr(trigger, c.name) for c in trigger.__table__.columns},
        'action_name': trigger.user_action.name if trigger.user_action else None,
        'action_names': _resolve_action_names(db, trigger),
    }
    return trigger_dict


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


def _extract_ppl_match_context(match_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not match_info:
        return {}

    best_match = match_info.get("best_match") or {}
    match_reason = _build_ppl_match_reason(best_match)

    return {
        "match_reason": match_reason,
        "matched_member_uuid": best_match.get("matched_member_uuid") or "",
        "matched_member_name": (best_match.get("existing_member_name") or "").strip(),
        "group_member_number": best_match.get("group_member_number") or "",
        "similarity_score": best_match.get("similarity_score") if best_match.get("similarity_score") is not None else "",
    }


def _interpolate_action_message(
    base_message: str,
    trigger: Trigger,
    evaluation_reason: Optional[str],
    match_info: Optional[Dict[str, Any]],
) -> str:
    message = base_message or ""

    match_context = _extract_ppl_match_context(match_info)
    replacements = {
        "trigger_name": trigger.name,
        "trigger_id": str(trigger.uuid),
        "reason": evaluation_reason or "",
        "match_reason": match_context.get("match_reason", ""),
        "matched_member_uuid": match_context.get("matched_member_uuid", ""),
        "matched_member_name": match_context.get("matched_member_name", ""),
        "group_member_number": match_context.get("group_member_number", ""),
        "similarity_score": match_context.get("similarity_score", ""),
    }

    used_template_variable = False
    for key, value in replacements.items():
        token = "{" + key + "}"
        if token in message:
            used_template_variable = True
            message = message.replace(token, str(value))

    if (
        not used_template_variable
        and match_context.get("match_reason")
        and match_info
        and (match_info.get("mode") == "ppl_match" or match_info.get("matched"))
    ):
        if message:
            message = f"{message} - {match_context['match_reason']}"
        else:
            message = match_context["match_reason"]

    return message


def _build_action_context(
    trigger: Trigger,
    camera_id: str,
    detection_payload: Optional[InstantDetectionPayload],
    evaluation_reason: Optional[str],
    match_info: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "trigger_id": str(trigger.uuid),
        "trigger_name": trigger.name,
        "camera_id": camera_id,
        "detection_timestamp": detection_payload.timestamp if detection_payload else None,
        "people_count": detection_payload.people_count if detection_payload else None,
        "demographics": detection_payload.demographics if detection_payload else {},
        "reason": evaluation_reason,
        "match": match_info,
    }


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
        
        # Convert search_camera_device_ids list to JSON string for storage
        if 'search_camera_device_ids' in trigger_data and trigger_data['search_camera_device_ids'] is not None:
            trigger_data['search_camera_device_ids'] = json.dumps(trigger_data['search_camera_device_ids'])
        
        # Convert ppl_match_group_ids list to JSON string for storage
        if 'ppl_match_group_ids' in trigger_data and trigger_data['ppl_match_group_ids'] is not None:
            trigger_data['ppl_match_group_ids'] = json.dumps(trigger_data['ppl_match_group_ids'])

        # Convert camera_device_ids list to JSON string for storage
        if 'camera_device_ids' in trigger_data and trigger_data['camera_device_ids'] is not None:
            trigger_data['camera_device_ids'] = json.dumps(trigger_data['camera_device_ids'])
        
        # Convert action_uuids list to JSON string for storage
        action_uuids_list = trigger_data.get('action_uuids')
        if action_uuids_list is not None:
            trigger_data['action_uuids'] = json.dumps([str(u) for u in action_uuids_list])
            # Set legacy action_uuid to first action for backward compat
            if action_uuids_list and not trigger_data.get('action_uuid'):
                trigger_data['action_uuid'] = action_uuids_list[0]
        elif trigger_data.get('action_uuid'):
            # Single action_uuid provided → sync to action_uuids
            trigger_data['action_uuids'] = json.dumps([str(trigger_data['action_uuid'])])
        
        # For search triggers, generate UUID upfront and set camera_device_id
        if trigger_data.get('trigger_mode') in ('search', 'search_demographic') and not trigger_data.get('camera_device_id'):
            from uuid import uuid4
            trigger_uuid = uuid4()
            trigger_data['uuid'] = trigger_uuid
            trigger_data['camera_device_id'] = f"search:{trigger_uuid}"
        
        # For vprofile_match triggers, set a synthetic camera_device_id since the column is NOT NULL
        if trigger_data.get('trigger_mode') == 'vprofile_match' and not trigger_data.get('camera_device_id'):
            trigger_data['camera_device_id'] = 'vprofile_match'
        
        db_trigger = Trigger(**trigger_data)
        db.add(db_trigger)
        db.commit()
        db.refresh(db_trigger)
        
        # VProfile lifecycle: activate on creation if active
        if db_trigger.trigger_mode == 'vprofile_match' and db_trigger.is_active:
            try:
                worker = get_vprofile_worker()
                await worker.activate_trigger(db_trigger)
            except Exception as activate_err:
                logger.error("Failed to activate vprofile trigger %s on create: %s", db_trigger.uuid, activate_err)
        
        trigger_dict = {
            **{c.name: getattr(db_trigger, c.name) for c in db_trigger.__table__.columns},
            'action_name': None,
            'action_names': _resolve_action_names(db, db_trigger),
        }
        return TriggerResponse(**trigger_dict)
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
    
    # Populate action_name and action_names from relationships / JSON
    trigger_responses = []
    for trigger in triggers:
        trigger_responses.append(TriggerResponse(**_build_trigger_response_dict(db, trigger)))
    
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
    
    return TriggerResponse(**_build_trigger_response_dict(db, trigger))


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

    # Keep DB NOT NULL ppl_match numeric fields stable when client sends null.
    # Frontend can switch to demographic mode and send nulls for ppl-match fields,
    # but these columns are NOT NULL at the DB level.
    if update_data.get('ppl_match_similarity_threshold') is None:
        update_data.pop('ppl_match_similarity_threshold', None)
    if update_data.get('ppl_match_top_k') is None:
        update_data.pop('ppl_match_top_k', None)
    
    # Convert demographic_conditions list to JSON string for storage
    if 'demographic_conditions' in update_data and update_data['demographic_conditions'] is not None:
        update_data['demographic_conditions'] = json.dumps([
            cond.model_dump() if hasattr(cond, 'model_dump') else cond
            for cond in update_data['demographic_conditions']
        ])
    
    # Convert search_camera_device_ids list to JSON string for storage
    if 'search_camera_device_ids' in update_data and update_data['search_camera_device_ids'] is not None:
        update_data['search_camera_device_ids'] = json.dumps(update_data['search_camera_device_ids'])
    
    # Convert action_uuids list to JSON string for storage and sync legacy field
    if 'action_uuids' in update_data:
        action_uuids_list = update_data['action_uuids']
        if action_uuids_list is not None:
            update_data['action_uuids'] = json.dumps([str(u) for u in action_uuids_list])
            # Sync legacy action_uuid to first action
            update_data['action_uuid'] = action_uuids_list[0] if action_uuids_list else None
        else:
            update_data['action_uuids'] = None
            update_data['action_uuid'] = None
    elif 'action_uuid' in update_data:
        # Single action_uuid update → sync to action_uuids
        au = update_data['action_uuid']
        update_data['action_uuids'] = json.dumps([str(au)]) if au else None
    
    for field, value in update_data.items():
        setattr(db_trigger, field, value)
    
    db.commit()
    db.refresh(db_trigger)
    
    # Reload to ensure relationship is fresh
    db_trigger = db.query(Trigger).options(joinedload(Trigger.user_action)).filter(Trigger.uuid == trigger_uuid).first()
    
    return TriggerResponse(**_build_trigger_response_dict(db, db_trigger))


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
    
    was_active = db_trigger.is_active
    db_trigger.is_active = not db_trigger.is_active
    db.commit()
    db.refresh(db_trigger)
    
    # VProfile lifecycle: activate on toggle-on, deactivate on toggle-off
    if db_trigger.trigger_mode == 'vprofile_match':
        try:
            worker = get_vprofile_worker()
            if db_trigger.is_active and not was_active:
                await worker.activate_trigger(db_trigger)
            elif not db_trigger.is_active and was_active:
                group_ids_raw = db_trigger.ppl_match_group_ids
                group_ids = json.loads(group_ids_raw) if group_ids_raw else []
                await worker.deactivate_trigger(str(db_trigger.uuid), group_ids=group_ids)
        except Exception as lifecycle_err:
            logger.error("Failed to handle vprofile lifecycle on toggle %s: %s", db_trigger.uuid, lifecycle_err)
    
    return db_trigger


@router.post("/{trigger_uuid}/execute-now")
async def execute_trigger_now(
    trigger_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Manually execute a search trigger immediately, bypassing the interval schedule.
    
    Only works for triggers with trigger_mode='search' or 'search_demographic'. The search is executed
    and results are published to Redis for evaluation by the existing subscriber.
    """
    db_trigger = db.query(Trigger).filter(Trigger.uuid == trigger_uuid).first()
    if not db_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    if db_trigger.trigger_mode not in ("search", "search_demographic"):
        raise HTTPException(
            status_code=400,
            detail=f"execute-now is only available for search triggers (this trigger is '{db_trigger.trigger_mode}')"
        )
    
    from ..services.search_trigger_scheduler import get_search_scheduler
    scheduler = get_search_scheduler()
    if scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Search trigger scheduler is not running"
        )
    
    result = await scheduler.execute_now(str(trigger_uuid))
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


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
    
    # Count by trigger mode
    mode_counts = db.query(
        Trigger.trigger_mode,
        func.count(Trigger.id)
    ).group_by(Trigger.trigger_mode).all()
    
    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "by_action": {action: count for action, count in action_counts},
        "by_mode": {mode: count for mode, count in mode_counts}
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
                    
                    # Dispatch all linked actions via action_uuids
                    action_executed = False
                    logger.info(f"▶️ Dispatching trigger actions...")
                    action_executed = await _dispatch_trigger_actions(
                        trigger=trigger,
                        db=db,
                        camera_id=payload.camera_id,
                        detection_payload=payload,
                        evaluation_reason=reason if trigger_mode == "ppl_match" else "All demographic conditions met",
                        match_info=match_info,
                    )
                    logger.info(f"✅ Trigger action dispatch completed (executed={action_executed})")
                    
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
            async def _check_single_source(source_mvr_uuid: str) -> List[Dict[str, Any]]:
                try:
                    response = await client.post(
                        endpoint,
                        json={
                            "candidate_mvr_uuid": source_mvr_uuid,
                            "similarity_threshold": threshold,
                        },
                    )
                except Exception as source_error:
                    logger.warning(
                        f"ppl_match duplicate-check error for source {source_mvr_uuid}: {source_error}"
                    )
                    return []

                if response.status_code != 200:
                    logger.warning(
                        f"ppl_match duplicate-check failed for source {source_mvr_uuid}: "
                        f"{response.status_code} {response.text[:200]}"
                    )
                    return []

                data = response.json()
                if not data.get("has_duplicates"):
                    return []

                candidates: List[Dict[str, Any]] = []
                for item in data.get("matches", []):
                    candidates.append({
                        "source_mvr_uuid": source_mvr_uuid,
                        "group_id": data.get("group_id"),
                        "group_name": data.get("group_name"),
                        "matched_member_uuid": item.get("existing_member_id"),
                        "similarity_score": item.get("similarity_score", 0.0),
                        "confidence": item.get("confidence"),
                        "existing_member_name": item.get("existing_member_name"),
                        "group_member_number": item.get("group_member_number"),
                        "gender": item.get("gender"),
                        "age_min": item.get("age_min"),
                        "age_max": item.get("age_max"),
                    })
                return candidates

            candidate_lists = await asyncio.gather(
                *[_check_single_source(source_mvr_uuid) for source_mvr_uuid in source_mvr_uuids]
            )
            for candidates in candidate_lists:
                all_candidates.extend(candidates)
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
        elif field == "age_threshold":
            # Compute weighted-average age from bracket percentages
            actual_value = sum(
                float(demographics.get(k, 0)) * mid / 100.0
                for k, mid in AGE_BRACKET_MIDPOINTS.items()
            )
        elif isinstance(field, str) and (
            field in AGE_COUNT_TO_PERCENT_FIELD or field in LEGACY_PERCENT_AGE_FIELDS
        ):
            percent_field = AGE_COUNT_TO_PERCENT_FIELD.get(field, field)
            age_count_value = demographics.get(field) if field in AGE_COUNT_TO_PERCENT_FIELD else None
            age_percent_value = demographics.get(percent_field)
            if age_count_value is not None:
                actual_value = float(age_count_value)
            elif age_percent_value is not None:
                actual_value = (float(people_count) * float(age_percent_value)) / 100.0
            else:
                logger.warning(f"Field '{field}' not found in demographics")
                return False
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


async def _dispatch_trigger_actions(
    trigger: Trigger,
    db: Session,
    camera_id: str,
    detection_payload: Optional[InstantDetectionPayload] = None,
    evaluation_reason: Optional[str] = None,
    match_info: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Dispatch all actions linked to a trigger via action_uuids / action_uuid.

    Reads UserTriggerAction records and routes each to the appropriate handler.
    Returns True if at least one action was attempted.
    """
    # Resolve action UUIDs list
    action_uuid_list: List[str] = []
    if trigger.action_uuids:
        try:
            parsed = json.loads(trigger.action_uuids)
            if isinstance(parsed, list):
                action_uuid_list = [str(u) for u in parsed if u]
        except (json.JSONDecodeError, TypeError):
            pass
    if not action_uuid_list and trigger.action_uuid:
        action_uuid_list = [str(trigger.action_uuid)]

    if not action_uuid_list:
        logger.warning(f"Trigger '{trigger.name}' fired but has no linked actions")
        return False

    attempted = False
    for action_uuid_str in action_uuid_list:
        action = db.query(UserTriggerAction).filter(
            UserTriggerAction.uuid == action_uuid_str
        ).first()
        if not action:
            logger.warning(f"Action {action_uuid_str} not found, skipping")
            continue

        logger.info(f"  ▶️ Executing action '{action.name}' (type={action.action_type})")
        attempted = True

        try:
            config = json.loads(action.action_config) if action.action_config else {}
        except (json.JSONDecodeError, TypeError):
            config = {}

        try:
            if action.action_type == "digital_signage":
                device_ids = config.get("device_ids", [])
                playlist_id = config.get("playlist_id")
                transition_mode = config.get("transition_mode", "immediate")
                fade_duration_ms = config.get("fade_duration_ms", 1000)

                if not device_ids or not playlist_id:
                    logger.error(
                        f"  ❌ digital_signage action '{action.name}' missing device_ids or playlist_id"
                    )
                    continue

                from uuid import UUID as _UUID
                playback_service = SignagePlaybackService(db)
                control_request = PlaybackControlRequest(
                    device_ids=[_UUID(d) for d in device_ids],
                    command=PlaybackCommand.START,
                    video_list_id=_UUID(playlist_id),
                    parameters=PlaybackParameters(),
                )
                result = await playback_service.control_playback(control_request)
                logger.info(f"  ✅ digital_signage action sent: {result}")

            elif action.action_type in ("alert", "log", "email", "webhook", "messaging_app"):
                comms_client = _get_communications_client()
                action_context = _build_action_context(
                    trigger=trigger,
                    camera_id=camera_id,
                    detection_payload=detection_payload,
                    evaluation_reason=evaluation_reason,
                    match_info=match_info,
                )

                if action.action_type == "log":
                    message = _interpolate_action_message(
                        base_message=config.get("message", f"Trigger '{trigger.name}' fired"),
                        trigger=trigger,
                        evaluation_reason=evaluation_reason,
                        match_info=match_info,
                    )
                    await comms_client.log_audit_event(
                        event_type="trigger_fired",
                        event_source="media_service_http",
                        event_data={
                            "action_name": action.name,
                            "message": message,
                            **action_context,
                        },
                        severity=config.get("level", "info"),
                    )
                    logger.info(f"  ✅ log action dispatched")
                elif action.action_type == "email":
                    recipients = config.get("recipients")
                    if not recipients:
                        to_field = config.get("to", "")
                        if isinstance(to_field, str):
                            recipients = [email.strip() for email in to_field.split(',') if email.strip()]
                        elif isinstance(to_field, list):
                            recipients = [str(email).strip() for email in to_field if str(email).strip()]
                        else:
                            recipients = []

                    cc = config.get("cc", [])
                    if not isinstance(cc, list):
                        cc = [str(cc)] if cc else []

                    if not recipients:
                        logger.error(f"  ❌ email action '{action.name}' has no recipients configured")
                        continue

                    subject = config.get("subject", "Trigger Alert")
                    body = config.get("body", f"Trigger '{trigger.name}' was fired.")
                    interpolated_subject = _interpolate_action_message(
                        base_message=subject,
                        trigger=trigger,
                        evaluation_reason=evaluation_reason,
                        match_info=match_info,
                    )
                    interpolated_body = _interpolate_action_message(
                        base_message=body,
                        trigger=trigger,
                        evaluation_reason=evaluation_reason,
                        match_info=match_info,
                    )
                    result = await comms_client.send_email(
                        to=recipients,
                        cc=cc if cc else None,
                        subject=interpolated_subject,
                        text_body=interpolated_body,
                        triggered_by="media_service_http",
                        trigger_type="trigger_action",
                        trigger_id=str(trigger.uuid),
                        payload={
                            "action_name": action.name,
                            **action_context,
                        },
                    )
                    if result.get("success"):
                        logger.info(f"  ✅ email action dispatched")
                    else:
                        logger.error(f"  ❌ email action failed: {result.get('message')}")
                elif action.action_type == "webhook":
                    webhook_url = config.get("url")
                    if not webhook_url:
                        logger.error(f"  ❌ webhook action '{action.name}' missing url")
                        continue

                    result = await comms_client.send_webhook(
                        url=webhook_url,
                        payload={
                            "event": "trigger_fired",
                            "action_name": action.name,
                            **action_context,
                        },
                        method=config.get("method", "POST"),
                        headers=config.get("headers"),
                        triggered_by="media_service_http",
                        trigger_type="trigger_action",
                        trigger_id=str(trigger.uuid),
                    )
                    if result.get("success"):
                        logger.info(f"  ✅ webhook action dispatched")
                    else:
                        logger.error(f"  ❌ webhook action failed: {result.get('message')}")
                elif action.action_type == "messaging_app":
                    platform = (config.get("platform") or "slack").lower()
                    webhook_url = config.get("webhook_url") or config.get("url")
                    if not webhook_url:
                        logger.error(f"  ❌ messaging_app action '{action.name}' missing webhook_url")
                        continue

                    message = config.get("message_template") or config.get("message") or f"Trigger '{trigger.name}' fired"
                    message = _interpolate_action_message(
                        base_message=message,
                        trigger=trigger,
                        evaluation_reason=evaluation_reason,
                        match_info=match_info,
                    )
                    mention = config.get("mention", "")
                    if platform == "slack":
                        payload = {"text": f"{mention} {message}".strip() if mention else message}
                    else:
                        payload = {"text": message}

                    result = await comms_client.send_webhook(
                        url=webhook_url,
                        payload=payload,
                        method="POST",
                        triggered_by="media_service_http",
                        trigger_type="trigger_action",
                        trigger_id=str(trigger.uuid),
                    )
                    if result.get("success"):
                        logger.info(f"  ✅ messaging_app action dispatched")
                    else:
                        logger.error(f"  ❌ messaging_app action failed: {result.get('message')}")
                elif action.action_type == "alert":
                    result = await comms_client.log_audit_event(
                        event_type="alert",
                        event_source="media_service_http",
                        event_data={
                            "action_name": action.name,
                            "message": _interpolate_action_message(
                                base_message=config.get("message", "Alert triggered"),
                                trigger=trigger,
                                evaluation_reason=evaluation_reason,
                                match_info=match_info,
                            ),
                            "severity": config.get("severity", "warning"),
                            "duration_seconds": config.get("duration_seconds", 30),
                            **action_context,
                        },
                        severity=config.get("severity", "warning"),
                    )
                    if result.get("success"):
                        logger.info(f"  ✅ alert action dispatched")
                    else:
                        logger.error(f"  ❌ alert action failed: {result.get('message')}")
                else:
                    logger.warning(f"  ⚠️ Unsupported notification action type: {action.action_type}")
            else:
                logger.warning(f"  ⚠️ Unsupported action type: {action.action_type}")

        except Exception as exc:
            logger.error(f"  ❌ Error executing action '{action.name}': {exc}", exc_info=True)

    return attempted


async def _execute_signage_action(
    trigger: Trigger,
    camera_id: str,
    detection_payload: Optional[InstantDetectionPayload] = None,
    evaluation_reason: Optional[str] = None,
    match_info: Optional[Dict[str, Any]] = None,
):
    """
    DEPRECATED — kept for reference only. Do not call.
    This function read trigger.signage_playlist_id / signage_device_ids which were
    removed from the Trigger model. Use _dispatch_trigger_actions() instead.
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

                try:
                    comms_client = _get_communications_client()
                    audit_event_data = {
                        "trigger_id": str(trigger.uuid),
                        "trigger_name": trigger.name,
                        "action_type": "digital_signage",
                        "camera_id": camera_id,
                        "detection_timestamp": detection_payload.timestamp if detection_payload else None,
                        "people_count": detection_payload.people_count if detection_payload else None,
                        "demographics": detection_payload.demographics if detection_payload else None,
                        "reason": evaluation_reason,
                        "match": match_info,
                        "signage": {
                            "playlist_id": trigger.signage_playlist_id,
                            "device_ids": device_ids,
                            "transition_mode": trigger.signage_transition_mode,
                            "response": result,
                        },
                    }
                    audit_result = await comms_client.log_audit_event(
                        event_type="trigger_fired",
                        event_source="media_service",
                        event_data=audit_event_data,
                        severity="info",
                    )
                    if audit_result.get("success"):
                        logger.info(f"📋 Trigger audit log created: {audit_result.get('log_uuid')}")
                    else:
                        logger.warning(f"⚠️ Trigger audit log failed: {audit_result.get('message')}")
                except Exception as audit_err:
                    logger.warning(f"⚠️ Failed to create trigger audit log: {audit_err}")
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

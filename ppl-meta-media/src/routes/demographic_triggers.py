"""
Demographic Triggers - Webhook-based Real-time Signage Control

Receives instant detection demographics from camera service and triggers
signage playlist changes based on configurable demographic conditions.

Integrates with existing PPL Meta Signage infrastructure.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/triggers", tags=["demographic-triggers"])


# ============================================================================
# Data Models
# ============================================================================

class InstantDetectionPayload(BaseModel):
    """Payload received from camera service webhook"""
    camera_id: str
    timestamp: str
    people_count: int
    demographics: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = {}


class TriggerCondition(BaseModel):
    """Single condition for trigger evaluation"""
    field: str = Field(..., description="Demographic field to check (e.g., 'percent_male', 'people_count')")
    operator: str = Field(..., description="Comparison operator: gt, gte, lt, lte, eq")
    value: float = Field(..., description="Threshold value to compare against")
    
    class Config:
        json_schema_extra = {
            "example": {
                "field": "percent_male",
                "operator": "gte",
                "value": 60
            }
        }


class TriggerAction(BaseModel):
    """Action to execute when trigger fires"""
    type: str = Field(default="signage_playback", description="Action type")
    device_ids: List[str] = Field(..., description="Target device UUIDs from discovery service")
    video_list_id: str = Field(..., description="Playlist UUID to play")
    start_index: int = Field(default=0, description="Starting video index in playlist")
    volume: int = Field(default=80, ge=0, le=100, description="Playback volume (0-100)")
    transition_mode: str = Field(
        default="immediate",
        description="Transition mode: immediate | after_current | fade"
    )
    fade_duration_ms: int = Field(
        default=2000,
        ge=0,
        description="Fade duration in milliseconds (for fade mode)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "signage_playback",
                "device_ids": ["device-uuid-1234"],
                "video_list_id": "playlist-uuid-5678",
                "start_index": 0,
                "volume": 80,
                "transition_mode": "after_current",
                "fade_duration_ms": 2000
            }
        }


class DemographicTrigger(BaseModel):
    """Complete demographic trigger configuration"""
    name: str = Field(..., description="Unique trigger name")
    description: Optional[str] = Field(None, description="Human-readable description")
    camera_ids: List[str] = Field(..., description="Camera IDs to monitor")
    conditions: List[TriggerCondition] = Field(..., description="All conditions must be met (AND logic)")
    actions: List[TriggerAction] = Field(..., description="Actions to execute when triggered")
    enabled: bool = Field(default=True, description="Whether trigger is active")
    cooldown_seconds: int = Field(default=60, ge=0, description="Minimum seconds between trigger fires")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "male_dominant_audience",
                "description": "Switch to men's products when >60% male audience",
                "camera_ids": ["usb_camera_0"],
                "conditions": [
                    {"field": "percent_male", "operator": "gte", "value": 60},
                    {"field": "people_count", "operator": "gte", "value": 2}
                ],
                "actions": [{
                    "type": "signage_playback",
                    "device_ids": ["device-uuid-1234"],
                    "video_list_id": "playlist-uuid-mens-products",
                    "transition_mode": "after_current",
                    "fade_duration_ms": 2000
                }],
                "enabled": True,
                "cooldown_seconds": 60
            }
        }


# ============================================================================
# In-Memory Storage (Replace with database in production)
# ============================================================================

TRIGGERS: Dict[str, DemographicTrigger] = {}
LAST_TRIGGERED: Dict[str, datetime] = {}


# ============================================================================
# Webhook Endpoint - Receives Demographics from Camera Service
# ============================================================================

@router.post("/instant-detection")
async def process_instant_detection_webhook(
    payload: InstantDetectionPayload,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint that receives instant detection demographics from camera service.
    
    Camera service POSTs here every 5 seconds with demographic data.
    This endpoint evaluates all active triggers and executes actions if conditions met.
    
    **Flow**:
    1. Receive demographics from camera
    2. Find matching triggers for this camera
    3. Evaluate conditions (AND logic)
    4. Check cooldown (prevent spam)
    5. Execute actions if triggered
    
    **Webhook Format** (received from camera service):
    ```json
    {
        "camera_id": "usb_camera_0",
        "timestamp": "2025-12-13T10:30:00",
        "people_count": 3,
        "demographics": {
            "percent_male": 67,
            "percent_female": 33,
            "percent_young": 0,
            "percent_adult": 100,
            ...
        },
        "metadata": {
            "processing_time": 2.5,
            "total_faces": 3
        }
    }
    ```
    
    **Response**:
    ```json
    {
        "success": true,
        "triggers_evaluated": 2,
        "triggers_fired": 1,
        "fired_triggers": ["male_dominant_audience"]
    }
    ```
    """
    logger.info(f"📥 Received instant detection webhook: camera={payload.camera_id}, people={payload.people_count}")
    
    # Find triggers for this camera
    matching_triggers = [
        trigger for trigger in TRIGGERS.values()
        if trigger.enabled and payload.camera_id in trigger.camera_ids
    ]
    
    if not matching_triggers:
        logger.debug(f"No active triggers for camera: {payload.camera_id}")
        return {
            "success": True,
            "triggers_evaluated": 0,
            "triggers_fired": 0,
            "fired_triggers": []
        }
    
    fired_triggers = []
    
    # Evaluate each trigger
    for trigger in matching_triggers:
        try:
            # Check if all conditions pass (AND logic)
            conditions_met = _evaluate_conditions(trigger.conditions, payload)
            
            if not conditions_met:
                logger.debug(f"Trigger '{trigger.name}' conditions not met")
                continue
            
            # Check cooldown
            cooldown_key = f"{trigger.name}_{payload.camera_id}"
            last_fired = LAST_TRIGGERED.get(cooldown_key)
            
            if last_fired:
                elapsed = (datetime.utcnow() - last_fired).total_seconds()
                if elapsed < trigger.cooldown_seconds:
                    logger.debug(
                        f"Trigger '{trigger.name}' in cooldown "
                        f"({elapsed:.1f}s / {trigger.cooldown_seconds}s)"
                    )
                    continue
            
            # Execute actions
            logger.info(f"🎯 Trigger fired: '{trigger.name}'")
            
            for action in trigger.actions:
                await _execute_action(action, payload)
            
            # Update last fired timestamp
            LAST_TRIGGERED[cooldown_key] = datetime.utcnow()
            fired_triggers.append(trigger.name)
            
        except Exception as e:
            logger.error(f"Error evaluating trigger '{trigger.name}': {e}", exc_info=True)
    
    return {
        "success": True,
        "triggers_evaluated": len(matching_triggers),
        "triggers_fired": len(fired_triggers),
        "fired_triggers": fired_triggers
    }


def _evaluate_conditions(
    conditions: List[TriggerCondition],
    payload: InstantDetectionPayload
) -> bool:
    """
    Evaluate all conditions against demographic data (AND logic).
    
    Args:
        conditions: List of conditions to check
        payload: Demographic data from camera
        
    Returns:
        True if ALL conditions pass, False otherwise
    """
    demographics = payload.demographics
    demographics["people_count"] = payload.people_count  # Add people_count to demographics
    
    for condition in conditions:
        field_value = demographics.get(condition.field)
        
        if field_value is None:
            logger.warning(f"Field '{condition.field}' not found in demographics")
            return False
        
        # Evaluate based on operator
        if condition.operator == "gt":
            if not (field_value > condition.value):
                return False
        elif condition.operator == "gte":
            if not (field_value >= condition.value):
                return False
        elif condition.operator == "lt":
            if not (field_value < condition.value):
                return False
        elif condition.operator == "lte":
            if not (field_value <= condition.value):
                return False
        elif condition.operator == "eq":
            if not (field_value == condition.value):
                return False
        else:
            logger.warning(f"Unknown operator: {condition.operator}")
            return False
    
    return True


async def _execute_action(
    action: TriggerAction,
    context: InstantDetectionPayload
):
    """
    Execute a trigger action using EXISTING signage infrastructure.
    
    Calls the existing /api/v1/signage/playback/start endpoint
    to switch playlists on registered devices.
    
    Args:
        action: Action configuration
        context: Demographic context that triggered the action
    """
    if action.type != "signage_playback":
        logger.warning(f"Unsupported action type: {action.type}")
        return
    
    try:
        # Call existing signage API
        payload = {
            "device_ids": action.device_ids,
            "video_list_id": action.video_list_id,
            "start_index": action.start_index,
            "volume": action.volume,
            "transition_mode": action.transition_mode,
            "fade_duration_ms": action.fade_duration_ms,
            "_trigger_context": {
                "camera_id": context.camera_id,
                "people_count": context.people_count,
                "demographics": context.demographics
            }
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/signage/playback/start",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(
                    f"✅ Signage action executed: devices={action.device_ids}, "
                    f"playlist={action.video_list_id}, transition={action.transition_mode}"
                )
            else:
                logger.error(
                    f"❌ Signage action failed: status={response.status_code}, "
                    f"response={response.text}"
                )
    
    except Exception as e:
        logger.error(f"Error executing action: {e}", exc_info=True)


# ============================================================================
# Trigger Management CRUD Endpoints
# ============================================================================

@router.post("/demographic", status_code=201)
async def create_demographic_trigger(
    trigger: DemographicTrigger,
    db: Session = Depends(get_db)
):
    """
    Create a new demographic trigger.
    
    **Example**:
    ```bash
    curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "name": "male_dominant_audience",
        "description": "Switch to men products playlist",
        "camera_ids": ["usb_camera_0"],
        "conditions": [
          {"field": "percent_male", "operator": "gte", "value": 60},
          {"field": "people_count", "operator": "gte", "value": 2}
        ],
        "actions": [{
          "type": "signage_playback",
          "device_ids": ["device-uuid-1234"],
          "video_list_id": "playlist-uuid-mens",
          "transition_mode": "after_current"
        }],
        "cooldown_seconds": 60
      }'
    ```
    """
    if trigger.name in TRIGGERS:
        raise HTTPException(
            status_code=409,
            detail=f"Trigger with name '{trigger.name}' already exists"
        )
    
    TRIGGERS[trigger.name] = trigger
    logger.info(f"✅ Created demographic trigger: {trigger.name}")
    
    return {
        "success": True,
        "message": f"Trigger '{trigger.name}' created successfully",
        "trigger": trigger
    }


@router.get("/demographic")
async def list_demographic_triggers(db: Session = Depends(get_db)):
    """
    List all configured demographic triggers.
    
    Returns trigger configurations and their current status.
    """
    triggers_with_status = []
    
    for trigger in TRIGGERS.values():
        # Calculate cooldown status for each camera
        cooldown_status = {}
        for camera_id in trigger.camera_ids:
            cooldown_key = f"{trigger.name}_{camera_id}"
            last_fired = LAST_TRIGGERED.get(cooldown_key)
            
            if last_fired:
                elapsed = (datetime.utcnow() - last_fired).total_seconds()
                cooldown_remaining = max(0, trigger.cooldown_seconds - elapsed)
                cooldown_status[camera_id] = {
                    "last_fired": last_fired.isoformat(),
                    "elapsed_seconds": round(elapsed, 1),
                    "cooldown_remaining": round(cooldown_remaining, 1),
                    "can_fire": cooldown_remaining == 0
                }
            else:
                cooldown_status[camera_id] = {
                    "last_fired": None,
                    "elapsed_seconds": None,
                    "cooldown_remaining": 0,
                    "can_fire": True
                }
        
        triggers_with_status.append({
            "trigger": trigger,
            "cooldown_status": cooldown_status
        })
    
    return {
        "success": True,
        "total": len(TRIGGERS),
        "triggers": triggers_with_status
    }


@router.get("/demographic/{trigger_name}")
async def get_demographic_trigger(
    trigger_name: str,
    db: Session = Depends(get_db)
):
    """Get specific trigger configuration"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' not found"
        )
    
    return {
        "success": True,
        "trigger": TRIGGERS[trigger_name]
    }


@router.put("/demographic/{trigger_name}")
async def update_demographic_trigger(
    trigger_name: str,
    trigger: DemographicTrigger,
    db: Session = Depends(get_db)
):
    """Update existing trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' not found"
        )
    
    # Update with new configuration
    TRIGGERS[trigger_name] = trigger
    logger.info(f"✅ Updated demographic trigger: {trigger_name}")
    
    return {
        "success": True,
        "message": f"Trigger '{trigger_name}' updated successfully",
        "trigger": trigger
    }


@router.delete("/demographic/{trigger_name}")
async def delete_demographic_trigger(
    trigger_name: str,
    db: Session = Depends(get_db)
):
    """Delete trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' not found"
        )
    
    del TRIGGERS[trigger_name]
    
    # Clean up cooldown tracking
    keys_to_remove = [key for key in LAST_TRIGGERED.keys() if key.startswith(f"{trigger_name}_")]
    for key in keys_to_remove:
        del LAST_TRIGGERED[key]
    
    logger.info(f"✅ Deleted demographic trigger: {trigger_name}")
    
    return {
        "success": True,
        "message": f"Trigger '{trigger_name}' deleted successfully"
    }


@router.post("/demographic/{trigger_name}/enable")
async def enable_trigger(
    trigger_name: str,
    db: Session = Depends(get_db)
):
    """Enable trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' not found"
        )
    
    TRIGGERS[trigger_name].enabled = True
    logger.info(f"✅ Enabled demographic trigger: {trigger_name}")
    
    return {
        "success": True,
        "enabled": True,
        "message": f"Trigger '{trigger_name}' enabled"
    }


@router.post("/demographic/{trigger_name}/disable")
async def disable_trigger(
    trigger_name: str,
    db: Session = Depends(get_db)
):
    """Disable trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' not found"
        )
    
    TRIGGERS[trigger_name].enabled = False
    logger.info(f"✅ Disabled demographic trigger: {trigger_name}")
    
    return {
        "success": True,
        "enabled": False,
        "message": f"Trigger '{trigger_name}' disabled"
    }


@router.post("/demographic/{trigger_name}/reset-cooldown")
async def reset_trigger_cooldown(
    trigger_name: str,
    camera_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Reset trigger cooldown.
    
    If camera_id provided, resets only for that camera.
    Otherwise resets for all cameras.
    """
    if trigger_name not in TRIGGERS:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' not found"
        )
    
    if camera_id:
        cooldown_key = f"{trigger_name}_{camera_id}"
        if cooldown_key in LAST_TRIGGERED:
            del LAST_TRIGGERED[cooldown_key]
            message = f"Cooldown reset for trigger '{trigger_name}' on camera '{camera_id}'"
        else:
            message = f"No cooldown active for trigger '{trigger_name}' on camera '{camera_id}'"
    else:
        keys_to_remove = [key for key in LAST_TRIGGERED.keys() if key.startswith(f"{trigger_name}_")]
        for key in keys_to_remove:
            del LAST_TRIGGERED[key]
        message = f"Cooldown reset for trigger '{trigger_name}' on all cameras"
    
    logger.info(f"✅ {message}")
    
    return {
        "success": True,
        "message": message
    }

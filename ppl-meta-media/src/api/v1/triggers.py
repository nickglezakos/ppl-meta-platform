"""
Trigger evaluation endpoints for PPL Meta Media Service.

Receives instant detection webhooks from cameras service and evaluates triggers.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.trigger import Trigger
from ...models.signage import SignageDevice
from ...services.signage_service import SignageService, SignagePlaybackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


async def _execute_signage_action(trigger_id: int, device_ids: List[str], playlist_id: str):
    """
    Execute signage action in background (non-blocking).
    
    This runs independently from the webhook response to prevent blocking
    the instant detection flow and camera stream.
    
    Args:
        trigger_id: Trigger ID for logging
        device_ids: List of device UUID strings
        playlist_id: Playlist UUID string
    """
    try:
        # Get database session for background task
        from ...database import SessionLocal
        db = SessionLocal()
        
        try:
            playback_service = SignagePlaybackService(db)
            
            for device_uuid_str in device_ids:
                try:
                    device_uuid = UUID(device_uuid_str)
                    device = db.query(SignageDevice).filter(SignageDevice.device_id == device_uuid).first()
                    
                    if device:
                        logger.info(f"\n     📱 [BACKGROUND] Sending switch command to device:")
                        logger.info(f"        Device Name: {device.device_name}")
                        logger.info(f"        Device UUID: {device_uuid}")
                        logger.info(f"        Current IP: {device.ip_address}")
                        
                        # Import required classes
                        from src.schemas.signage import PlaybackControlRequest, PlaybackCommand
                        
                        # Create control request to start new playlist
                        control_request = PlaybackControlRequest(
                            device_ids=[device_uuid],
                            command=PlaybackCommand.START,
                            video_list_id=UUID(playlist_id),
                            parameters=None  # Use default playback parameters
                        )
                        
                        logger.info(f"        📤 Sending START command with playlist {playlist_id}")
                        
                        # Send playback control command to switch playlist
                        result = await playback_service.control_playback(control_request)
                        
                        logger.info(f"        ✅ Command sent! Result: {json.dumps(result, indent=10)}")
                    else:
                        logger.warning(f"        ❌ Device {device_uuid_str} not found in database")
                
                except ValueError as e:
                    logger.error(f"[BACKGROUND] Invalid device UUID {device_uuid_str}: {e}")
                except Exception as e:
                    logger.error(f"[BACKGROUND] Error switching playlist for device {device_uuid_str}: {e}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"[BACKGROUND] Signage action failed for trigger {trigger_id}: {e}", exc_info=True)


class InstantDetectionWebhook(BaseModel):
    """Webhook payload from cameras service instant detection."""
    
    camera_id: str = Field(..., description="Camera device ID (e.g., 'usb_camera_0')")
    timestamp: str = Field(..., description="ISO format timestamp")
    people_count: int = Field(..., ge=0, description="Number of people detected")
    demographics: Dict = Field(..., description="Demographic statistics")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


@router.post("/instant-detection")
async def handle_instant_detection(
    payload: InstantDetectionWebhook,
    db: Session = Depends(get_db),
) -> Dict:
    """
    Receive instant detection webhooks from cameras service and evaluate triggers.
    
    This endpoint is called by the cameras service every time instant detection runs.
    It evaluates all active triggers with demographic conditions enabled and fires
    those that match.
    
    Args:
        payload: Instant detection data including demographics
        db: Database session
        
    Returns:
        Status and any triggered actions
    """
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔔 INSTANT DETECTION WEBHOOK RECEIVED")
        logger.info(f"{'='*80}")
        logger.info(f"📷 Camera ID: {payload.camera_id}")
        logger.info(f"👥 People Count: {payload.people_count}")
        logger.info(f"📊 Demographics: {json.dumps(payload.demographics, indent=2)}")
        logger.info(f"⏰ Timestamp: {payload.timestamp}")
        logger.info(f"{'='*80}\n")
        
        # Get all active triggers with demographic conditions enabled
        triggers = (
            db.query(Trigger)
            .filter(
                Trigger.is_active == True,
                Trigger.enable_demographic_conditions == True,
                Trigger.camera_device_id == payload.camera_id
            )
            .all()
        )
        
        logger.info(f"🔍 Database query found {len(triggers)} active demographic triggers for camera {payload.camera_id}")
        
        if not triggers:
            logger.debug(f"No active demographic triggers found for camera {payload.camera_id}")
            return {
                "success": True,
                "message": "No active demographic triggers to evaluate",
                "triggers_evaluated": 0,
                "triggers_fired": 0
            }
        
        logger.info(f"Evaluating {len(triggers)} demographic triggers for camera {payload.camera_id}")
        
        triggers_fired = 0
        fired_trigger_ids = []
        
        for trigger in triggers:
            logger.info(f"\n--- Evaluating Trigger #{trigger.id}: '{trigger.name}' ---")
            logger.info(f"  Trigger UUID: {trigger.uuid}")
            logger.info(f"  Is Active: {trigger.is_active}")
            logger.info(f"  Cooldown: {trigger.cooldown_seconds}s")
            logger.info(f"  Last Fired: {trigger.last_fired_at}")
            
            # Check cooldown
            if trigger.last_fired_at:
                cooldown_end = trigger.last_fired_at + timedelta(seconds=trigger.cooldown_seconds)
                now = datetime.now(trigger.last_fired_at.tzinfo)
                if now < cooldown_end:
                    remaining = (cooldown_end - now).total_seconds()
                    logger.info(f"  ⏸️  SKIP: In cooldown ({remaining:.1f}s remaining)")
                    continue
                else:
                    logger.info(f"  ✅ Cooldown passed")
            else:
                logger.info(f"  ✅ Never fired before (no cooldown)")
            
            # Evaluate demographic conditions
            if trigger.demographic_conditions:
                try:
                    conditions = json.loads(trigger.demographic_conditions)
                    logger.info(f"  📋 Conditions to evaluate: {json.dumps(conditions, indent=4)}")
                    
                    if not evaluate_demographic_conditions(conditions, payload.demographics, payload.people_count):
                        logger.info(f"  ❌ SKIP: Conditions NOT met")
                        continue
                    else:
                        logger.info(f"  ✅ Conditions MET!")
                except json.JSONDecodeError as e:
                    logger.error(f"  ❌ ERROR: Failed to parse demographic_conditions: {e}")
                    continue
            
            # Trigger matches! Execute action
            logger.info(f"\n🔥🔥🔥 TRIGGER FIRED! 🔥🔥🔥")
            logger.info(f"  Trigger #{trigger.id}: '{trigger.name}'")
            triggers_fired += 1
            fired_trigger_ids.append(trigger.id)
            
            # Update last_fired_at
            trigger.last_fired_at = datetime.now(trigger.last_fired_at.tzinfo) if trigger.last_fired_at else datetime.now()
            logger.info(f"  Updated last_fired_at to {trigger.last_fired_at}")
            
            # Execute signage action if configured (NON-BLOCKING)
            if trigger.signage_device_ids and trigger.signage_playlist_id:
                logger.info(f"  🎬 Scheduling signage action in background...")
                logger.info(f"     Target Playlist UUID: {trigger.signage_playlist_id}")
                logger.info(f"     Transition Mode: {trigger.signage_transition_mode}")
                logger.info(f"     Fade Duration: {trigger.signage_fade_duration_ms}ms")
                
                try:
                    device_ids = json.loads(trigger.signage_device_ids)
                    logger.info(f"     Target Device IDs: {device_ids}")
                    
                    # 🚀 CRITICAL FIX: Execute in background task to prevent blocking
                    import asyncio
                    asyncio.create_task(
                        _execute_signage_action(
                            trigger_id=trigger.id,
                            device_ids=device_ids,
                            playlist_id=trigger.signage_playlist_id
                        )
                    )
                    logger.info(f"     ✅ Signage action scheduled in background (non-blocking)")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse signage_device_ids for trigger {trigger.id}: {e}")
        
        # Commit all updates
        db.commit()
        
        result = {
            "success": True,
            "message": f"Evaluated {len(triggers)} triggers, {triggers_fired} fired",
            "triggers_evaluated": len(triggers),
            "triggers_fired": triggers_fired,
            "fired_trigger_ids": fired_trigger_ids
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ EVALUATION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"   Triggers Evaluated: {len(triggers)}")
        logger.info(f"   Triggers Fired: {triggers_fired}")
        logger.info(f"   Fired IDs: {fired_trigger_ids}")
        logger.info(f"{'='*80}\n")
        return result
    
    except Exception as e:
        logger.error(f"Error handling instant detection webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process instant detection: {str(e)}"
        )


def evaluate_demographic_conditions(
    conditions: list,
    demographics: dict,
    people_count: int
) -> bool:
    """
    Evaluate demographic conditions against current detection data.
    
    Args:
        conditions: List of condition dicts with field, operator, value
        demographics: Demographics data from detection
        people_count: Current people count
        
    Returns:
        True if all conditions match (AND logic)
    """
    logger.info(f"  🔍 Evaluating {len(conditions)} condition(s)")
    logger.info(f"     Input people_count: {people_count}")
    logger.info(f"     Input demographics: {demographics}")
    
    if not conditions:
        logger.info(f"  ✅ No conditions to evaluate (always true)")
        return True
    
    for idx, condition in enumerate(conditions, 1):
        field = condition.get('field')
        operator = condition.get('operator')
        threshold = condition.get('value')
        
        logger.info(f"     Condition {idx}: {field} {operator} {threshold}")
        
        if not all([field, operator, threshold is not None]):
            logger.warning(f"     ⚠️ Invalid condition: {condition}")
            continue
        
        # Get the actual value from demographics or people_count
        if field == 'people_count':
            actual_value = people_count
            logger.info(f"       Actual people_count: {actual_value}")
        else:
            actual_value = demographics.get(field)
            logger.info(f"       Actual {field}: {actual_value}")
            if actual_value is None:
                logger.warning(f"       ❌ Field {field} not found in demographics")
                return False
        
        # Evaluate condition
        try:
            threshold = float(threshold)
            actual_value = float(actual_value)
            
            logger.info(f"       Comparing: {actual_value} {operator} {threshold}")
            
            if operator == 'gt' and not (actual_value > threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT > {threshold}")
                return False
            elif operator == 'gte' and not (actual_value >= threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT >= {threshold}")
                return False
            elif operator == 'lt' and not (actual_value < threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT < {threshold}")
                return False
            elif operator == 'lte' and not (actual_value <= threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT <= {threshold}")
                return False
            elif operator == 'eq' and not (actual_value == threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT == {threshold}")
                return False
            else:
                logger.info(f"       ✅ PASS")
        
        except (ValueError, TypeError) as e:
            logger.error(f"       ❌ Error evaluating condition {condition}: {e}")
            return False
    
    # All conditions passed
    logger.info(f"  ✅ ALL CONDITIONS PASSED")
    return True

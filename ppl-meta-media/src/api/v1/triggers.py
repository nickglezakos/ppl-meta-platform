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
        from ...schemas.trigger import InstantDetectionPayload
        from ...routes.triggers import process_instant_detection_webhook

        adapted_payload = InstantDetectionPayload(
            camera_id=payload.camera_id,
            timestamp=payload.timestamp,
            people_count=payload.people_count,
            demographics=payload.demographics,
            metadata=payload.metadata or {},
        )

        return await process_instant_detection_webhook(payload=adapted_payload, db=db)

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
        elif field == 'age_threshold':
            # Compute weighted-average age from bracket percentages
            actual_value = sum(
                float(demographics.get(k, 0)) * mid / 100.0
                for k, mid in AGE_BRACKET_MIDPOINTS.items()
            )
            logger.info(f"       Computed weighted avg age: {actual_value}")
        elif field in AGE_COUNT_TO_PERCENT_FIELD or field in LEGACY_PERCENT_AGE_FIELDS:
            percent_field = AGE_COUNT_TO_PERCENT_FIELD.get(field, field)
            age_count_value = demographics.get(field) if field in AGE_COUNT_TO_PERCENT_FIELD else None
            age_percent_value = demographics.get(percent_field)

            if age_count_value is not None:
                actual_value = float(age_count_value)
                logger.info(f"       Actual {field}: {actual_value}")
            elif age_percent_value is not None:
                actual_value = (float(people_count) * float(age_percent_value)) / 100.0
                logger.info(
                    f"       Actual {percent_field}: {age_percent_value}% -> derived age_count: {actual_value}"
                )
            else:
                logger.warning(f"       ❌ Field {field} not found in demographics")
                return False
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

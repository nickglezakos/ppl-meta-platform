"""
Notification API routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.notification import (
    PushNotificationRequest,
    PushNotificationResponse,
)
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/push", response_model=PushNotificationResponse)
async def send_push_notification(
    request: PushNotificationRequest,
    db: Session = Depends(get_db)
):
    """
    Send push notifications to device tokens.
    
    Sends notifications via FCM (Android) or APNS (iOS).
    """
    notification_service = NotificationService(db)
    
    success, message, log_uuid, successful_count, failed_count = await notification_service.send_push_notification(
        device_tokens=request.device_tokens,
        title=request.title,
        body=request.body,
        data=request.data,
        badge=request.badge,
        sound=request.sound,
        priority=request.priority,
        triggered_by=request.triggered_by,
        trigger_type=request.trigger_type,
        trigger_id=request.trigger_id,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return PushNotificationResponse(
        success=success,
        message=message,
        log_uuid=log_uuid,
        devices_count=len(request.device_tokens),
        successful_count=successful_count,
        failed_count=failed_count
    )

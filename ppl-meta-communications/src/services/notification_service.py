"""
Notification and audit logging services.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..config import get_config
from ..models.communication_log import (
    CommunicationLog,
    CommunicationStatus,
    CommunicationType,
)

logger = logging.getLogger(__name__)
config = get_config()


class NotificationService:
    """Service for sending push notifications."""

    def __init__(self, db: Session):
        self.db = db
        self.config = config

    async def send_push_notification(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        badge: Optional[int] = None,
        sound: Optional[str] = None,
        priority: str = "high",
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> tuple[bool, str, UUID, int, int]:
        """
        Send push notifications to device tokens.
        
        Returns:
            tuple: (success, message, log_uuid, successful_count, failed_count)
        """
        if not self.config.PUSH_ENABLED:
            logger.warning("Push notifications are disabled in configuration")
            return False, "Push notifications are disabled", None, 0, 0

        # Create communication log
        log = CommunicationLog(
            type=CommunicationType.PUSH_NOTIFICATION,
            status=CommunicationStatus.PENDING,
            recipient=", ".join(device_tokens[:5]) + (f"... ({len(device_tokens)} total)" if len(device_tokens) > 5 else ""),
            subject=title,
            content=body,
            payload={"data": data, "badge": badge, "sound": sound, "priority": priority},
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            installation_id=installation_id,
            tenant_name=tenant_name,
            attempts=0,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        try:
            # TODO: Implement actual push notification logic here
            # This would integrate with FCM (Firebase Cloud Messaging) for Android
            # and APNS (Apple Push Notification Service) for iOS
            
            # For now, just log the notification
            logger.info(f"📱 Push notification queued: {title} to {len(device_tokens)} devices")
            logger.info(f"   Body: {body}")
            logger.info(f"   Data: {data}")
            
            # Placeholder: Mark as sent
            log.status = CommunicationStatus.SENT
            log.delivered_at = datetime.now(timezone.utc)
            log.attempts = 1
            self.db.commit()

            # In a real implementation, you would:
            # 1. Use firebase-admin SDK for FCM
            # 2. Use aioapns for APNS
            # 3. Batch requests appropriately
            # 4. Track individual device success/failure

            return True, f"Push notification sent to {len(device_tokens)} devices", log.uuid, len(device_tokens), 0

        except Exception as e:
            log.status = CommunicationStatus.FAILED
            log.failed_at = datetime.now(timezone.utc)
            log.error_message = str(e)
            log.attempts = 1
            self.db.commit()

            logger.error(f"❌ Failed to send push notification: {e}")
            return False, f"Failed to send push notification: {str(e)}", log.uuid, 0, len(device_tokens)


class AuditLogService:
    """Service for audit logging."""

    def __init__(self, db: Session):
        self.db = db
        self.config = config

    async def log_audit_event(
        self,
        event_type: str,
        event_source: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "info",
    ) -> tuple[bool, str, UUID]:
        """
        Create an audit log entry.
        
        Returns:
            tuple: (success, message, log_uuid)
        """
        if not self.config.AUDIT_LOG_ENABLED:
            logger.warning("Audit logging is disabled in configuration")
            return False, "Audit logging is disabled", None

        try:
            # Create communication log (audit logs use the same table)
            log = CommunicationLog(
                type=CommunicationType.AUDIT_LOG,
                status=CommunicationStatus.DELIVERED,  # Audit logs are immediately "delivered"
                recipient=event_source,  # Source service/component
                subject=event_type,  # Event type
                content=f"User: {user_id}, IP: {ip_address}, Severity: {severity}",
                payload=event_data,
                triggered_by=user_id,
                trigger_type="audit_event",
                trigger_id=event_type,
                attempts=1,
                delivered_at=datetime.now(timezone.utc),
                installation_id=self.config.INSTALLATION_ID,
                tenant_name=self.config.TENANT_NAME,
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)

            logger.info(f"📋 Audit event logged: {event_type} from {event_source}. Log UUID: {log.uuid}")
            return True, "Audit event logged successfully", log.uuid

        except Exception as e:
            logger.error(f"❌ Failed to log audit event: {e}")
            return False, f"Failed to log audit event: {str(e)}", None


class CommunicationLogService:
    """Service for querying communication logs."""

    def __init__(self, db: Session):
        self.db = db

    def get_logs(
        self,
        type: Optional[str] = None,
        status: Optional[str] = None,
        recipient: Optional[str] = None,
        triggered_by: Optional[str] = None,
        trigger_id: Optional[str] = None,
        installation_id: Optional[str] = None,
        tenant_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[CommunicationLog], int]:
        """
        Query communication logs with filters.
        
        Returns:
            tuple: (logs, total_count)
        """
        query = self.db.query(CommunicationLog)

        # Apply filters
        if type:
            query = query.filter(CommunicationLog.type == type)
        if status:
            query = query.filter(CommunicationLog.status == status)
        if recipient:
            query = query.filter(CommunicationLog.recipient.ilike(f"%{recipient}%"))
        if triggered_by:
            query = query.filter(CommunicationLog.triggered_by == triggered_by)
        if trigger_id:
            query = query.filter(CommunicationLog.trigger_id == trigger_id)
        if installation_id:
            query = query.filter(CommunicationLog.installation_id == installation_id)
        if tenant_name:
            query = query.filter(CommunicationLog.tenant_name.ilike(f"%{tenant_name}%"))
        if start_date:
            query = query.filter(CommunicationLog.created_at > start_date)
        if end_date:
            query = query.filter(CommunicationLog.created_at <= end_date)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        logs = query.order_by(CommunicationLog.created_at.desc()).offset(offset).limit(page_size).all()

        return logs, total
    def get_log_by_uuid(self, log_uuid: UUID) -> Optional[CommunicationLog]:
        """Get a single communication log by UUID."""
        return self.db.query(CommunicationLog).filter(CommunicationLog.uuid == log_uuid).first()

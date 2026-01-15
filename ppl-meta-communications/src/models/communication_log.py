"""
Database model for communication logs.
"""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ..database import Base


class CommunicationType(str, enum.Enum):
    """Communication type enumeration."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    PUSH_NOTIFICATION = "push_notification"
    SMS = "sms"
    AUDIT_LOG = "audit_log"


class CommunicationStatus(str, enum.Enum):
    """Communication status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class CommunicationLog(Base):
    """Model for tracking all communications sent by the platform."""
    
    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PGUUID(as_uuid=True), unique=True, nullable=False, default=uuid4, index=True)
    
    # Communication metadata
    type = Column(Enum(CommunicationType), nullable=False, index=True)
    status = Column(Enum(CommunicationStatus), nullable=False, default=CommunicationStatus.PENDING, index=True)
    
    # Recipient information
    recipient = Column(String(500), nullable=False, index=True)  # email, phone, device_token, webhook URL
    
    # Content
    subject = Column(String(500), nullable=True)  # For email/notifications
    content = Column(Text, nullable=True)  # Main content
    payload = Column(JSON, nullable=True)  # Additional structured data
    
    # Trigger information
    triggered_by = Column(String(200), nullable=True, index=True)  # Service/user that triggered
    trigger_type = Column(String(100), nullable=True)  # e.g., "trigger_action", "manual", "scheduled"
    trigger_id = Column(String(200), nullable=True, index=True)  # ID of trigger/action that caused this
    
    # Multi-tenant / Installation tracking
    installation_id = Column(String(200), nullable=True, index=True)  # UUID of admin/owner user for this installation
    tenant_name = Column(String(200), nullable=True)  # Optional human-readable tenant/installation name
    
    # Delivery tracking
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Response tracking
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CommunicationLog(uuid={self.uuid}, type={self.type}, status={self.status}, recipient={self.recipient})>"

"""
User-defined Trigger Actions Model

User-created actions that can be assigned to triggers.
Separate from system workflows (which are read-only).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class UserTriggerAction(Base):
    """
    User-defined action that can be triggered.
    
    Unlike system workflows (read-only), these are CRUD-able by users.
    Initial implementation supports 'alert' type (on-screen notification).
    """
    __tablename__ = "user_trigger_actions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    
    # Core fields
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Action type: 'alert', 'email', 'webhook', 'log', etc.
    action_type = Column(String(50), nullable=False, default='alert')
    
    # Action-specific configuration (JSON string)
    # For 'alert': {"message": "Alert text", "severity": "warning|error|info"}
    # For 'email': {"recipients": ["email1", "email2"], "subject": "...", "body": "..."}
    # For 'webhook': {"url": "https://...", "method": "POST", "headers": {...}, "body": {...}}
    action_config = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)  # Username/email of creator
    
    def __repr__(self):
        return f"<UserTriggerAction(id={self.id}, uuid={self.uuid}, name={self.name}, type={self.action_type}, active={self.is_active})>"

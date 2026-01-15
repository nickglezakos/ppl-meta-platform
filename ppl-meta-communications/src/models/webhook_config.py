"""
Database model for webhook configurations.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ..database import Base


class WebhookConfig(Base):
    """Model for webhook endpoint configurations."""
    
    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PGUUID(as_uuid=True), unique=True, nullable=False, default=uuid4, index=True)
    
    # Webhook identification
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Endpoint configuration
    url = Column(String(2000), nullable=False)
    method = Column(String(10), nullable=False, default="POST")  # GET, POST, PUT, DELETE
    
    # Authentication
    auth_type = Column(String(50), nullable=True)  # bearer, basic, api_key, none
    auth_token = Column(String(500), nullable=True)  # Encrypted in production
    auth_username = Column(String(200), nullable=True)
    auth_password = Column(String(200), nullable=True)
    
    # Headers
    headers = Column(JSON, nullable=True, default=dict)  # Additional custom headers
    
    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=5, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    
    # Event filtering (optional - which events trigger this webhook)
    event_types = Column(JSON, nullable=True, default=list)  # ["trigger_fired", "user_created", etc.]
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Statistics
    total_calls = Column(Integer, default=0, nullable=False)
    successful_calls = Column(Integer, default=0, nullable=False)
    failed_calls = Column(Integer, default=0, nullable=False)
    last_called_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_by = Column(String(200), nullable=True)
    updated_by = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<WebhookConfig(name={self.name}, url={self.url}, uuid={self.uuid})>"

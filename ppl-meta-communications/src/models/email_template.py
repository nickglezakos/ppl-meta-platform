"""
Database model for email templates.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ..database import Base


class EmailTemplate(Base):
    """Model for reusable email templates."""
    
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PGUUID(as_uuid=True), unique=True, nullable=False, default=uuid4, index=True)
    
    # Template identification
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Template content
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=True)
    text_body = Column(Text, nullable=False)
    
    # Template variables (JSON array of variable names that can be substituted)
    variables = Column(JSON, nullable=True, default=list)
    
    # Metadata
    category = Column(String(100), nullable=True, index=True)  # e.g., "trigger_notification", "user_notification"
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by = Column(String(200), nullable=True)
    updated_by = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailTemplate(name={self.name}, uuid={self.uuid})>"

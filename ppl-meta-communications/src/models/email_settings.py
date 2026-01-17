"""
Email Settings Model for storing SMTP configuration in database.
"""
from sqlalchemy import Boolean, Column, Integer, String, DateTime, func
from ..database import Base


class EmailSettings(Base):
    """Email settings model for SMTP configuration."""

    __tablename__ = "email_settings"

    id = Column(Integer, primary_key=True, index=True)
    mail_enabled = Column(Boolean, default=False, nullable=False)
    mail_server = Column(String(255), default="smtp.gmail.com", nullable=False)
    mail_port = Column(Integer, default=587, nullable=False)
    mail_username = Column(String(255), default="", nullable=False)
    mail_password = Column(String(500), default="", nullable=False)  # Encrypted in production
    mail_from = Column(String(255), default="noreply@pplmeta.com", nullable=False)
    mail_from_name = Column(String(255), default="PPL Meta Platform", nullable=False)
    mail_starttls = Column(Boolean, default=True, nullable=False)
    mail_ssl_tls = Column(Boolean, default=False, nullable=False)
    use_credentials = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<EmailSettings(id={self.id}, server={self.mail_server}, enabled={self.mail_enabled})>"

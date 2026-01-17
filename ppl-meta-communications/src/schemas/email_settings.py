"""
Pydantic schemas for Email Settings API.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class EmailSettingsBase(BaseModel):
    """Base schema for email settings."""
    
    mail_enabled: bool = Field(default=False, description="Enable/disable email functionality")
    mail_server: str = Field(default="smtp.gmail.com", description="SMTP server address")
    mail_port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    mail_username: str = Field(default="", description="SMTP username/email")
    mail_password: str = Field(default="", description="SMTP password")
    mail_from: str = Field(default="noreply@pplmeta.com", description="From email address")
    mail_from_name: str = Field(default="PPL Meta Platform", description="From name")
    mail_starttls: bool = Field(default=True, description="Use STARTTLS")
    mail_ssl_tls: bool = Field(default=False, description="Use SSL/TLS")
    use_credentials: bool = Field(default=True, description="Use authentication")

    @field_validator('mail_server')
    @classmethod
    def validate_server(cls, v: str) -> str:
        if v and not v.strip():
            raise ValueError('mail_server cannot be empty string')
        return v.strip() if v else ""

    @field_validator('mail_from')
    @classmethod
    def validate_from_email(cls, v: str) -> str:
        if v and not v.strip():
            raise ValueError('mail_from cannot be empty string')
        # Basic email validation
        if v and '@' not in v:
            raise ValueError('mail_from must be a valid email address')
        return v.strip() if v else ""


class EmailSettingsCreate(EmailSettingsBase):
    """Schema for creating email settings."""
    pass


class EmailSettingsUpdate(BaseModel):
    """Schema for updating email settings (all fields optional)."""
    
    mail_enabled: Optional[bool] = None
    mail_server: Optional[str] = None
    mail_port: Optional[int] = Field(None, ge=1, le=65535)
    mail_username: Optional[str] = None
    mail_password: Optional[str] = None
    mail_from: Optional[str] = None
    mail_from_name: Optional[str] = None
    mail_starttls: Optional[bool] = None
    mail_ssl_tls: Optional[bool] = None
    use_credentials: Optional[bool] = None


class EmailSettingsResponse(EmailSettingsBase):
    """Schema for email settings response."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Don't return password in response for security
    mail_password: str = Field(default="********", description="Password (masked)")

    class Config:
        from_attributes = True

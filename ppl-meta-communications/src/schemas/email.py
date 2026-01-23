"""
Pydantic schemas for email operations.
"""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class EmailSendRequest(BaseModel):
    """Request schema for sending an email."""
    
    to: List[EmailStr] = Field(..., description="List of recipient email addresses")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject")
    html_body: Optional[str] = Field(None, description="HTML email body")
    text_body: str = Field(..., min_length=1, description="Plain text email body")
    cc: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    from_email: Optional[EmailStr] = Field(None, description="Sender email (uses config default if not provided)")
    from_name: Optional[str] = Field(None, description="Sender name (uses config default if not provided)")
    attachments: Optional[List[Dict]] = Field(None, description="Attachments (future feature)")
    payload: Optional[Dict] = Field(None, description="Additional structured data (e.g., demographics, trigger data)")
    
    # Trigger tracking
    triggered_by: Optional[str] = Field(None, description="Service/user that triggered this email")
    trigger_type: Optional[str] = Field(None, description="Type of trigger (e.g., 'trigger_action')")
    trigger_id: Optional[str] = Field(None, description="ID of trigger that caused this email")


class EmailTemplateRequest(BaseModel):
    """Request schema for sending an email using a template."""
    
    to: List[EmailStr] = Field(..., description="List of recipient email addresses")
    template_name: str = Field(..., description="Name of the email template to use")
    variables: Dict[str, str] = Field(default_factory=dict, description="Variables to substitute in template")
    cc: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    
    # Trigger tracking
    triggered_by: Optional[str] = Field(None, description="Service/user that triggered this email")
    trigger_type: Optional[str] = Field(None, description="Type of trigger")
    trigger_id: Optional[str] = Field(None, description="ID of trigger")


class EmailSendResponse(BaseModel):
    """Response schema for email send operations."""
    
    success: bool
    message: str
    log_uuid: UUID
    recipients_count: int
    
    class Config:
        from_attributes = True


class EmailTemplateCreate(BaseModel):
    """Schema for creating an email template."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Unique template name")
    description: Optional[str] = Field(None, description="Template description")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject (supports variables)")
    html_body: Optional[str] = Field(None, description="HTML body (supports variables)")
    text_body: str = Field(..., min_length=1, description="Plain text body (supports variables)")
    variables: Optional[List[str]] = Field(default_factory=list, description="List of variable names used in template")
    category: Optional[str] = Field(None, description="Template category")
    is_active: bool = Field(True, description="Whether template is active")


class EmailTemplateResponse(BaseModel):
    """Response schema for email template."""
    
    id: int
    uuid: UUID
    name: str
    description: Optional[str]
    subject: str
    html_body: Optional[str]
    text_body: str
    variables: Optional[List[str]]
    category: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

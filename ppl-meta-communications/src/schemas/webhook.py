"""
Pydantic schemas for webhook operations.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class WebhookSendRequest(BaseModel):
    """Request schema for sending a webhook."""
    
    url: HttpUrl = Field(..., description="Webhook URL to call")
    method: str = Field("POST", description="HTTP method (GET, POST, PUT, DELETE)")
    payload: Dict[str, Any] = Field(..., description="Payload to send")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    timeout: Optional[int] = Field(30, description="Request timeout in seconds")
    
    # Trigger tracking
    triggered_by: Optional[str] = Field(None, description="Service/user that triggered this webhook")
    trigger_type: Optional[str] = Field(None, description="Type of trigger")
    trigger_id: Optional[str] = Field(None, description="ID of trigger")


class WebhookSendResponse(BaseModel):
    """Response schema for webhook send operations."""
    
    success: bool
    message: str
    log_uuid: UUID
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    
    class Config:
        from_attributes = True


class WebhookConfigCreate(BaseModel):
    """Schema for creating a webhook configuration."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Unique webhook name")
    description: Optional[str] = Field(None, description="Webhook description")
    url: HttpUrl = Field(..., description="Webhook endpoint URL")
    method: str = Field("POST", description="HTTP method")
    auth_type: Optional[str] = Field(None, description="Auth type: bearer, basic, api_key, none")
    auth_token: Optional[str] = Field(None, description="Auth token/API key")
    auth_username: Optional[str] = Field(None, description="Basic auth username")
    auth_password: Optional[str] = Field(None, description="Basic auth password")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Custom headers")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(5, description="Delay between retries")
    timeout_seconds: int = Field(30, description="Request timeout")
    event_types: Optional[List[str]] = Field(default_factory=list, description="Event types that trigger this webhook")
    is_active: bool = Field(True, description="Whether webhook is active")


class WebhookConfigResponse(BaseModel):
    """Response schema for webhook configuration."""
    
    id: int
    uuid: UUID
    name: str
    description: Optional[str]
    url: str
    method: str
    auth_type: Optional[str]
    headers: Optional[Dict[str, str]]
    max_retries: int
    retry_delay_seconds: int
    timeout_seconds: int
    event_types: Optional[List[str]]
    is_active: bool
    total_calls: int
    successful_calls: int
    failed_calls: int
    last_called_at: Optional[str]
    last_success_at: Optional[str]
    last_failure_at: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

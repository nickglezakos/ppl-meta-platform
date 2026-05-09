"""
User Trigger Action API Schemas

Pydantic models for user-defined trigger actions.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class UserTriggerActionBase(BaseModel):
    """Base schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Action name")
    description: Optional[str] = Field(None, description="Action description")
    action_type: str = Field(..., description="Action type: alert, email, webhook, log, digital_signage")
    action_config: Optional[str] = Field(
        None, 
        description=(
            "JSON configuration for action.\n"
            "- digital_signage: {\"device_ids\": [...], \"playlist_id\": \"...\", \"transition_mode\": \"immediate|after_current|fade\", \"fade_duration_ms\": 2000}\n"
            "- email: {\"recipients\": [\"email1@example.com\", \"email2@example.com\"], \"subject\": \"Alert: {trigger_name} - {match_reason}\", \"body\": \"Trigger fired: {reason}\"}\n"
            "- webhook: {\"url\": \"https://webhook.site/...\", \"method\": \"POST\", \"payload_data\": {\"custom_field\": \"value\"}}\n"
            "- log: {\"severity\": \"info|warning|error\", \"data\": {\"category\": \"trigger_events\", \"tags\": [\"marketing\"]}}\n"
            "- messaging_app: {\"platform\": \"slack|teams\", \"webhook_url\": \"https://hooks.slack.com/...\", \"message_template\": \"Alert: {trigger_name}\", \"mention\": \"@channel\"}"
        )
    )
    is_active: bool = Field(True, description="Whether action is active")
    created_by: Optional[str] = Field(None, description="Username/email of creator")
    
    @validator('action_type')
    def validate_action_type(cls, v):
        """Validate action type is one of the supported types"""
        allowed_types = ['alert', 'email', 'webhook', 'log', 'digital_signage', 'messaging_app']
        if v not in allowed_types:
            raise ValueError(f"action_type must be one of {allowed_types}, got '{v}'")
        return v
    
    class Config:
        from_attributes = True


class UserTriggerActionCreate(UserTriggerActionBase):
    """Schema for creating a new user action"""
    pass


class UserTriggerActionUpdate(BaseModel):
    """Schema for updating a user action (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    action_type: Optional[str] = None
    action_config: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('action_type')
    def validate_action_type(cls, v):
        """Validate action type if provided"""
        if v is not None:
            allowed_types = ['alert', 'email', 'webhook', 'log', 'digital_signage', 'messaging_app']
            if v not in allowed_types:
                raise ValueError(f"action_type must be one of {allowed_types}, got '{v}'")
        return v
    
    class Config:
        from_attributes = True


class UserTriggerActionResponse(UserTriggerActionBase):
    """Schema for action responses (includes id, uuid, timestamps)"""
    id: int
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserTriggerActionListResponse(BaseModel):
    """Paginated list response"""
    actions: list[UserTriggerActionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True


class UserTriggerActionStatsResponse(BaseModel):
    """Statistics response"""
    total: int
    active: int
    inactive: int
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by action type")
    
    class Config:
        from_attributes = True

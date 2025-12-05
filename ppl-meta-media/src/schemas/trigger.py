"""
Pydantic schemas for Trigger API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PersonCountOperatorEnum(str):
    """Person count operators."""
    LESS_THAN = "less_than"
    MORE_THAN = "more_than"
    EQUALS = "equals"
    BETWEEN = "between"


class AgeRangeEnum(str):
    """Age range categories."""
    UNDERAGE = "underage"
    ADULTS = "adults"
    SENIORS = "seniors"
    ALL = "all"


class TriggerActionEnum(str):
    """Trigger actions."""
    ALERT = "alert"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


class TriggerBase(BaseModel):
    """Base trigger schema with common fields."""
    
    person_count_operator: str = Field(
        ...,
        description="Comparison operator: less_than, more_than, equals, between"
    )
    person_count_value: str = Field(
        ...,
        description="Person count threshold (e.g., '5', '10-20' for between)",
        min_length=1,
        max_length=50
    )
    age_range: str = Field(
        default="all",
        description="Age range filter: underage, adults, seniors, all"
    )
    gender_filter: Optional[str] = Field(
        None,
        description="Gender filter (e.g., 'Any', '3M/2W', 'Male', 'Female')",
        max_length=50
    )
    time_span: str = Field(
        ...,
        description="Time span when active (e.g., 'Mon-Fri 09:00-17:00')",
        min_length=1,
        max_length=100
    )
    media_source_uuid: UUID = Field(
        ...,
        description="UUID of the camera or media collection"
    )
    media_source_name: Optional[str] = Field(
        None,
        description="Friendly name of media source",
        max_length=255
    )
    action: str = Field(
        default="alert",
        description="Action to execute: alert, email, webhook, log"
    )
    action_config: Optional[str] = Field(
        None,
        description="Additional action configuration (JSON string)",
        max_length=500
    )
    is_active: bool = Field(
        default=True,
        description="Whether trigger is active"
    )
    name: Optional[str] = Field(
        None,
        description="Optional friendly name",
        max_length=255
    )
    description: Optional[str] = Field(
        None,
        description="Optional description",
        max_length=500
    )

    @field_validator('person_count_operator')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        valid = ['less_than', 'more_than', 'equals', 'between']
        if v not in valid:
            raise ValueError(f'person_count_operator must be one of {valid}')
        return v

    @field_validator('age_range')
    @classmethod
    def validate_age_range(cls, v: str) -> str:
        valid = ['underage', 'adults', 'seniors', 'all']
        if v not in valid:
            raise ValueError(f'age_range must be one of {valid}')
        return v

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid = ['alert', 'email', 'webhook', 'log']
        if v not in valid:
            raise ValueError(f'action must be one of {valid}')
        return v


class TriggerCreate(TriggerBase):
    """Schema for creating a new trigger."""
    pass


class TriggerUpdate(BaseModel):
    """Schema for updating a trigger (all fields optional)."""
    
    person_count_operator: Optional[str] = None
    person_count_value: Optional[str] = None
    age_range: Optional[str] = None
    gender_filter: Optional[str] = None
    time_span: Optional[str] = None
    media_source_uuid: Optional[UUID] = None
    media_source_name: Optional[str] = None
    action: Optional[str] = None
    action_config: Optional[str] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None

    @field_validator('person_count_operator')
    @classmethod
    def validate_operator(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['less_than', 'more_than', 'equals', 'between']
            if v not in valid:
                raise ValueError(f'person_count_operator must be one of {valid}')
        return v

    @field_validator('age_range')
    @classmethod
    def validate_age_range(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['underage', 'adults', 'seniors', 'all']
            if v not in valid:
                raise ValueError(f'age_range must be one of {valid}')
        return v

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['alert', 'email', 'webhook', 'log']
            if v not in valid:
                raise ValueError(f'action must be one of {valid}')
        return v


class TriggerResponse(TriggerBase):
    """Schema for trigger response."""
    
    id: int
    uuid: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TriggerListResponse(BaseModel):
    """Schema for paginated trigger list response."""
    
    triggers: list[TriggerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

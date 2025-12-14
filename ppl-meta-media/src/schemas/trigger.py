"""
Pydantic schemas for Trigger API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PersonCountOperatorEnum(str):
    """Person count operators."""
    LESS_THAN = "less_than"
    MORE_THAN = "more_than"
    EQUALS = "equals"
    BETWEEN = "between"


class AgeRangeOperatorEnum(str):
    """Age range operators."""
    LESS_THAN = "less_than"
    MORE_THAN = "more_than"
    BETWEEN = "between"
    ANY = "any"


class GenderFilterEnum(str):
    """Gender filter options."""
    MALE = "male"
    FEMALE = "female"
    ANY = "any"


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
    age_range_operator: Optional[str] = Field(
        None,
        description="Age comparison operator: less_than, more_than, between, any"
    )
    age_range_value: Optional[str] = Field(
        None,
        description="Age threshold (e.g., '18', '65', '18-30' for between)",
        max_length=50
    )
    gender_filter: Optional[str] = Field(
        "any",
        description="Gender filter: male, female, any",
        max_length=50
    )
    time_span: str = Field(
        ...,
        description="Time span when active (e.g., 'Mon-Fri 09:00-17:00')",
        min_length=1,
        max_length=100
    )
    camera_device_id: str = Field(
        ...,
        description="Device ID of the camera from Camera service (e.g., 'usb_camera_0')",
        min_length=1,
        max_length=255
    )
    camera_name: Optional[str] = Field(
        None,
        description="Friendly name of the camera",
        max_length=255
    )
    action: str = Field(
        default="alert",
        description="Action to execute: alert, email, webhook, log (deprecated - use action_uuid)"
    )
    action_config: Optional[str] = Field(
        None,
        description="Additional action configuration (JSON string)",
        max_length=500
    )
    action_uuid: Optional[UUID] = Field(
        None,
        description="UUID of the linked user action"
    )
    tracking_duration: str = Field(
        default="10 minutes",
        description='Time window for MVR search (e.g., "5 seconds", "10 minutes", "2 hours", "1 day")',
        max_length=50
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
    enable_demographic_conditions: bool = Field(
        default=False,
        description="Enable demographic-based trigger evaluation"
    )
    demographic_conditions: Optional[str] = Field(
        None,
        description='JSON array of demographic conditions: [{"field": "percent_male", "operator": "gte", "value": 60}]'
    )
    signage_device_ids: Optional[str] = Field(
        None,
        description='JSON array of signage device UUIDs: ["device-uuid-1", "device-uuid-2"]'
    )
    signage_playlist_id: Optional[str] = Field(
        None,
        description="Playlist UUID to play when trigger fires",
        max_length=255
    )
    signage_transition_mode: str = Field(
        default="immediate",
        description="Playlist transition mode: immediate | after_current | fade"
    )
    signage_fade_duration_ms: int = Field(
        default=2000,
        ge=0,
        description="Fade duration in milliseconds"
    )
    cooldown_seconds: int = Field(
        default=60,
        ge=0,
        description="Minimum seconds between trigger firings"
    )

    @field_validator('person_count_operator')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        valid = ['less_than', 'more_than', 'equals', 'between']
        if v not in valid:
            raise ValueError(f'person_count_operator must be one of {valid}')
        return v

    @field_validator('age_range_operator')
    @classmethod
    def validate_age_range_operator(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = ['less_than', 'more_than', 'between', 'any']
        if v not in valid:
            raise ValueError(f'age_range_operator must be one of {valid}')
        return v

    @field_validator('gender_filter')
    @classmethod
    def validate_gender_filter(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return 'any'
        valid = ['male', 'female', 'any']
        if v not in valid:
            raise ValueError(f'gender_filter must be one of {valid}')
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
    age_range_operator: Optional[str] = None
    age_range_value: Optional[str] = None
    gender_filter: Optional[str] = None
    time_span: Optional[str] = None
    camera_device_id: Optional[str] = None
    camera_name: Optional[str] = None
    action: Optional[str] = None
    action_config: Optional[str] = None
    action_uuid: Optional[UUID] = None
    tracking_duration: Optional[str] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None
    enable_demographic_conditions: Optional[bool] = None
    demographic_conditions: Optional[str] = None
    signage_device_ids: Optional[str] = None
    signage_playlist_id: Optional[str] = None
    signage_transition_mode: Optional[str] = None
    signage_fade_duration_ms: Optional[int] = None
    cooldown_seconds: Optional[int] = None

    @field_validator('person_count_operator')
    @classmethod
    def validate_operator(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['less_than', 'more_than', 'equals', 'between']
            if v not in valid:
                raise ValueError(f'person_count_operator must be one of {valid}')
        return v

    @field_validator('age_range_operator')
    @classmethod
    def validate_age_range_operator(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['less_than', 'more_than', 'between', 'any']
            if v not in valid:
                raise ValueError(f'age_range_operator must be one of {valid}')
        return v

    @field_validator('gender_filter')
    @classmethod
    def validate_gender_filter(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['male', 'female', 'any']
            if v not in valid:
                raise ValueError(f'gender_filter must be one of {valid}')
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
    action_name: Optional[str] = Field(None, description="Name of the linked user action")

    class Config:
        from_attributes = True


class TriggerListResponse(BaseModel):
    """Schema for paginated trigger list response."""
    
    triggers: list[TriggerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CounterDataRequest(BaseModel):
    """Schema for camera counter data input."""
    
    camera_device_id: str = Field(..., description="Device ID of the camera (e.g., 'usb_camera_0')")
    total_count: int = Field(..., ge=0, description="Total person count")
    age_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Age distribution (e.g., {'0-18': 5, '19-30': 10, ...})"
    )
    gender_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Gender distribution (e.g., {'male': 8, 'female': 7})"
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp of the count (defaults to now)"
    )


class TriggerEvaluationResult(BaseModel):
    """Schema for single trigger evaluation result."""
    
    trigger_uuid: UUID
    trigger_name: Optional[str]
    passed: bool = Field(..., description="Whether trigger conditions were met")
    reason: str = Field(..., description="Explanation of the result")
    person_count: int = Field(..., description="Actual person count evaluated")
    timestamp: datetime = Field(..., description="When the evaluation occurred")


class TriggerEvaluationResponse(BaseModel):
    """Schema for trigger evaluation response."""
    
    camera_device_id: str
    total_count: int
    evaluated_at: datetime
    triggers_evaluated: int = Field(..., description="Number of triggers checked")
    triggers_passed: int = Field(..., description="Number of triggers that passed")
    results: List[TriggerEvaluationResult] = Field(
        ...,
        description="Detailed results for each trigger"
    )


class InstantDetectionPayload(BaseModel):
    """Payload received from camera service instant detection webhook."""
    
    camera_id: str = Field(..., description="Camera device ID")
    timestamp: str = Field(..., description="ISO format timestamp of detection")
    people_count: int = Field(..., ge=0, description="Total number of people detected")
    demographics: Dict[str, Any] = Field(
        ...,
        description="Demographic data including age/gender distributions and percentages"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata from camera"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "camera_id": "usb_camera_0",
                "timestamp": "2025-12-13T10:30:00Z",
                "people_count": 8,
                "demographics": {
                    "age_distribution": {"18-25": 3, "26-40": 4, "41-60": 1},
                    "gender_distribution": {"male": 5, "female": 3},
                    "percent_male": 62.5,
                    "percent_female": 37.5
                },
                "metadata": {}
            }
        }

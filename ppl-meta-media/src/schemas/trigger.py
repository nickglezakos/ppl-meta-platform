"""
Pydantic schemas for Trigger API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DemographicCondition(BaseModel):
    """Single demographic condition."""
    field: str = Field(
        ...,
        description="Demographic field: people_count, percent_male, percent_female, percent_age_0_12, percent_age_13_17, percent_age_18_24, percent_age_25_34, percent_age_35_44, percent_age_45_54, percent_age_55_64, percent_age_65_plus"
    )
    operator: str = Field(
        ...,
        description="Comparison operator: gt, gte, lt, lte, eq"
    )
    value: float = Field(
        ...,
        description="Threshold value"
    )

    @field_validator('field')
    @classmethod
    def validate_field(cls, v: str) -> str:
        valid = [
            'people_count', 'percent_male', 'percent_female',
            'percent_age_0_12', 'percent_age_13_17', 'percent_age_18_24',
            'percent_age_25_34', 'percent_age_35_44', 'percent_age_45_54',
            'percent_age_55_64', 'percent_age_65_plus'
        ]
        if v not in valid:
            raise ValueError(f'field must be one of {valid}')
        return v

    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        valid = ['gt', 'gte', 'lt', 'lte', 'eq']
        if v not in valid:
            raise ValueError(f'operator must be one of {valid}')
        return v


class TriggerBase(BaseModel):
    """Base trigger schema with common fields."""
    
    demographic_conditions: List[DemographicCondition] = Field(
        ...,
        description="List of demographic conditions (all must match)",
        min_length=1
    )
    time_span: str = Field(
        ...,
        description="Time span when active (e.g., 'Mon-Fri 09:00-17:00', 'any')",
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
    action_uuid: Optional[UUID] = Field(
        None,
        description="UUID of the linked user action (alert, webhook, email, digital_signage, etc.)"
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
    cooldown_seconds: int = Field(
        default=60,
        ge=0,
        description="Minimum seconds between trigger firings to prevent spam"
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


class TriggerCreate(TriggerBase):
    """Schema for creating a new trigger."""
    pass


class TriggerUpdate(BaseModel):
    """Schema for updating a trigger (all fields optional)."""
    
    demographic_conditions: Optional[List[DemographicCondition]] = None
    time_span: Optional[str] = None
    camera_device_id: Optional[str] = None
    camera_name: Optional[str] = None
    action_uuid: Optional[UUID] = None
    tracking_duration: Optional[str] = None
    is_active: Optional[bool] = None
    cooldown_seconds: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None


class TriggerResponse(BaseModel):
    """Schema for trigger response."""
    
    id: int
    uuid: UUID
    demographic_conditions: List[DemographicCondition]
    time_span: str
    camera_device_id: str
    camera_name: Optional[str]
    action_uuid: Optional[UUID]
    action_name: Optional[str] = Field(None, description="Name of the linked user action")
    tracking_duration: str
    is_active: bool
    cooldown_seconds: int
    last_fired_at: Optional[datetime]
    name: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    @field_validator('demographic_conditions', mode='before')
    @classmethod
    def parse_demographic_conditions(cls, v):
        """Parse demographic_conditions if it's a JSON string."""
        if isinstance(v, str):
            import json
            parsed = json.loads(v)
            return [DemographicCondition(**item) for item in parsed]
        return v

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

"""
Pydantic schemas for Trigger API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


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
        default_factory=list,
        description="List of demographic conditions (all must match in demographic mode)"
    )
    time_span: str = Field(
        ...,
        description="Time span when active (e.g., 'Mon-Fri 09:00-17:00', 'any')",
        min_length=1,
        max_length=100
    )
    camera_device_id: Optional[str] = Field(
        None,
        description="Device ID of the camera from Camera service (e.g., 'usb_camera_0'). Not required for search mode.",
        max_length=255
    )
    camera_name: Optional[str] = Field(
        None,
        description="Friendly name of the camera",
        max_length=255
    )
    action_uuid: Optional[UUID] = Field(
        None,
        description="UUID of the linked user action (legacy single-action field)"
    )
    action_uuids: Optional[List[UUID]] = Field(
        None,
        description="List of action UUIDs assigned to this trigger (multi-action support)"
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
    trigger_mode: str = Field(
        default="demographic",
        description="Trigger mode: demographic | ppl_match | search | search_demographic"
    )
    ppl_match_group_id: Optional[str] = Field(
        None,
        description="Individual group ID used for ppl_match mode",
        max_length=255
    )
    ppl_match_similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for ppl_match mode"
    )
    ppl_match_top_k: int = Field(
        default=1,
        ge=1,
        description="Maximum number of top candidates to keep in ppl_match mode"
    )
    search_camera_device_ids: Optional[List[str]] = Field(
        None,
        description="JSON array of camera device IDs to search (required for search mode)"
    )
    search_interval_seconds: Optional[int] = Field(
        default=300,
        ge=30,
        description="How often the search executes in seconds (minimum 30, required for search mode)"
    )

    @field_validator('trigger_mode')
    @classmethod
    def validate_trigger_mode(cls, v: str) -> str:
        valid = ['demographic', 'ppl_match', 'search', 'search_demographic']
        if v not in valid:
            raise ValueError(f'trigger_mode must be one of {valid}')
        return v

    @model_validator(mode='after')
    def validate_mode_config(self):
        if self.trigger_mode not in ('search', 'search_demographic') and not self.camera_device_id:
            raise ValueError('camera_device_id is required for demographic and ppl_match trigger modes')
        if self.trigger_mode == 'demographic' and len(self.demographic_conditions) == 0:
            raise ValueError('demographic_conditions must contain at least one condition in demographic mode')
        if self.trigger_mode == 'ppl_match' and not self.ppl_match_group_id:
            raise ValueError('ppl_match_group_id is required when trigger_mode is ppl_match')
        if self.trigger_mode == 'search':
            if not self.search_camera_device_ids:
                raise ValueError('search_camera_device_ids is required when trigger_mode is search')
            if not self.ppl_match_group_id:
                raise ValueError('ppl_match_group_id is required when trigger_mode is search (the group to search against camera collections)')
        if self.trigger_mode == 'search_demographic':
            if not self.search_camera_device_ids:
                raise ValueError('search_camera_device_ids is required when trigger_mode is search_demographic')
            if len(self.demographic_conditions) == 0:
                raise ValueError('demographic_conditions must contain at least one condition in search_demographic mode')
        return self


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
    action_uuids: Optional[List[UUID]] = None
    tracking_duration: Optional[str] = None
    is_active: Optional[bool] = None
    cooldown_seconds: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_mode: Optional[str] = None
    ppl_match_group_id: Optional[str] = None
    ppl_match_similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ppl_match_top_k: Optional[int] = Field(default=None, ge=1)
    search_camera_device_ids: Optional[List[str]] = None
    search_interval_seconds: Optional[int] = Field(default=None, ge=30)

    @field_validator('trigger_mode')
    @classmethod
    def validate_trigger_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = ['demographic', 'ppl_match', 'search', 'search_demographic']
        if v not in valid:
            raise ValueError(f'trigger_mode must be one of {valid}')
        return v

    @model_validator(mode='after')
    def validate_mode_config(self):
        if self.trigger_mode == 'ppl_match' and not self.ppl_match_group_id:
            raise ValueError('ppl_match_group_id is required when trigger_mode is ppl_match')
        if self.trigger_mode == 'search':
            if not self.search_camera_device_ids:
                raise ValueError('search_camera_device_ids is required when trigger_mode is search')
            if not self.ppl_match_group_id:
                raise ValueError('ppl_match_group_id is required when trigger_mode is search')
        if self.trigger_mode == 'search_demographic':
            if not self.search_camera_device_ids:
                raise ValueError('search_camera_device_ids is required when trigger_mode is search_demographic')
        return self


class TriggerResponse(BaseModel):
    """Schema for trigger response."""
    
    id: int
    uuid: UUID
    demographic_conditions: List[DemographicCondition]
    time_span: str
    camera_device_id: str
    camera_name: Optional[str]
    action_uuid: Optional[UUID]
    action_name: Optional[str] = Field(None, description="Name of the linked user action (legacy)")
    action_uuids: Optional[List[UUID]] = Field(None, description="List of action UUIDs assigned to this trigger")
    action_names: Optional[List[str]] = Field(None, description="Names of the linked user actions")
    tracking_duration: str
    is_active: bool
    cooldown_seconds: int
    last_fired_at: Optional[datetime]
    trigger_mode: str
    ppl_match_group_id: Optional[str]
    ppl_match_similarity_threshold: float
    ppl_match_top_k: int
    last_match_info: Optional[Dict[str, Any]] = None
    last_matched_at: Optional[datetime] = None
    search_camera_device_ids: Optional[List[str]] = None
    search_interval_seconds: Optional[int] = None
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

    @field_validator('last_match_info', mode='before')
    @classmethod
    def parse_last_match_info(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator('search_camera_device_ids', mode='before')
    @classmethod
    def parse_search_camera_device_ids(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator('action_uuids', mode='before')
    @classmethod
    def parse_action_uuids(cls, v):
        """Parse action_uuids if it's a JSON string."""
        if isinstance(v, str):
            import json
            return json.loads(v)
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
    match: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional ppl_match metadata when trigger_mode is ppl_match"
    )
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

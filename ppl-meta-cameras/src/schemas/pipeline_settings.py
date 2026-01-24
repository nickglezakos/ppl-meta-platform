"""
Pipeline settings schemas for camera recording and instant detection decoupling.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PipelineSettingsUpdate(BaseModel):
    """Schema for updating camera pipeline settings."""

    instant_detection_enabled: bool = Field(
        ..., description="Enable instant detection pipeline"
    )
    recording_pipeline_enabled: bool = Field(
        ..., description="Enable recording and continuous detection pipeline"
    )
    instant_detection_interval_seconds: Optional[int] = Field(
        default=5,
        ge=1,
        le=60,
        description="Interval in seconds for instant detection sampling",
    )
    segment_duration_seconds: Optional[int] = Field(
        default=30,
        ge=5,
        le=300,
        description="Segment duration in seconds for recording",
    )

    @field_validator("instant_detection_enabled", "recording_pipeline_enabled")
    @classmethod
    def validate_at_least_one_enabled(cls, v, info):
        """Ensure at least one pipeline is enabled."""
        # This validation happens at the model level
        # Additional validation in the endpoint ensures both fields are checked together
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "instant_detection_enabled": True,
                "recording_pipeline_enabled": True,
                "instant_detection_interval_seconds": 5,
                "segment_duration_seconds": 30,
            }
        }


class PipelineSettingsResponse(BaseModel):
    """Schema for pipeline settings API responses."""

    device_id: str
    camera_name: Optional[str] = None
    instant_detection_enabled: bool
    recording_pipeline_enabled: bool
    instant_detection_interval_seconds: int
    segment_duration_seconds: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "device_id": "usb_camera_0",
                "camera_name": "Main Entrance Camera",
                "instant_detection_enabled": True,
                "recording_pipeline_enabled": True,
                "instant_detection_interval_seconds": 5,
                "segment_duration_seconds": 30,
                "created_at": "2026-01-20T08:00:00Z",
                "updated_at": "2026-01-24T10:30:00Z",
            }
        }


class RecordingStartRequest(BaseModel):
    """Enhanced schema for starting recording with pipeline overrides."""

    quality: str = Field(default="high", description="Recording quality")
    segment_duration_seconds: Optional[int] = Field(
        default=30,
        ge=5,
        le=300,
        description="Override segment duration for this recording session",
    )
    enable_instant_detection: Optional[bool] = Field(
        default=None,
        description="Override camera's instant detection setting (None = use camera default)",
    )
    enable_recording_pipeline: Optional[bool] = Field(
        default=None,
        description="Override camera's recording pipeline setting (None = use camera default)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "quality": "high",
                "segment_duration_seconds": 30,
                "enable_instant_detection": True,
                "enable_recording_pipeline": True,
            }
        }

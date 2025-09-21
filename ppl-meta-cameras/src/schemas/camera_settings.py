"""
Camera settings schemas for API requests and responses.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CameraSettingsBase(BaseModel):
    """Base camera settings schema."""

    auto_face_detection: bool = Field(
        default=False, description="Enable automatic face detection"
    )
    detection_methods: List[str] = Field(
        default=["mtcnn"], description="Face detection methods to use"
    )
    processing_options: Dict[str, Any] = Field(
        default_factory=dict, description="Processing options"
    )
    auto_recording: bool = Field(
        default=False, description="Enable automatic recording"
    )
    recording_duration: int = Field(
        default=30, description="Recording duration in seconds"
    )
    notifications_enabled: bool = Field(
        default=True, description="Enable notifications"
    )
    notification_methods: List[str] = Field(
        default=["email"], description="Notification methods"
    )
    store_faces_in_memory: bool = Field(
        default=True, description="Store faces in memory during recording"
    )
    persist_after_recording: bool = Field(
        default=True, description="Persist faces to database after recording"
    )


class CameraSettingsCreate(CameraSettingsBase):
    """Schema for creating camera settings."""

    pass


class CameraSettingsUpdate(BaseModel):
    """Schema for updating camera settings."""

    auto_face_detection: bool = None
    detection_methods: List[str] = None
    processing_options: Dict[str, Any] = None
    auto_recording: bool = None
    recording_duration: int = None
    notifications_enabled: bool = None
    notification_methods: List[str] = None
    store_faces_in_memory: bool = None
    persist_after_recording: bool = None


class CameraSettingsResponse(CameraSettingsBase):
    """Schema for camera settings API responses."""

    id: int
    camera_device_id: str
    user_id: str
    created_at: str = None
    updated_at: str = None

    class Config:
        from_attributes = True

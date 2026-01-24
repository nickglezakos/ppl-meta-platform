"""
Camera workflow settings schemas for API requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CameraWorkflowSettingsBase(BaseModel):
    """Base camera workflow settings schema."""

    auto_face_detection: bool = Field(
        default=False, description="Enable automatic face detection"
    )
    detection_methods: List[str] = Field(
        default=["opencv", "dlib"], 
        description="Face detection methods to use: opencv, dlib, mtcnn, yolo"
    )
    processing_options: Dict[str, Any] = Field(
        default_factory=dict, description="Additional processing options"
    )
    confidence_threshold: float = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence threshold for face detection"
    )
    enable_performance_optimization: bool = Field(
        default=True, 
        description="Enable performance optimization (Workflow 5) for CPU reduction"
    )
    show_performance_indicators: bool = Field(
        default=True, 
        description="Display performance metrics and CPU usage indicators"
    )
    default_playback_mode: str = Field(
        default="auto", 
        description="Default playback mode: auto, optimized, standard"
    )
    mvr_quality_threshold: float = Field(
        default=0.20, 
        ge=0.0, 
        le=1.0, 
        description="Minimum quality threshold for creating MVR people"
    )


class CameraWorkflowSettingsUpdate(BaseModel):
    """Schema for updating camera workflow settings."""

    auto_face_detection: Optional[bool] = None
    detection_methods: Optional[List[str]] = None
    processing_options: Optional[Dict[str, Any]] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    enable_performance_optimization: Optional[bool] = None
    show_performance_indicators: Optional[bool] = None
    default_playback_mode: Optional[str] = None
    mvr_quality_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class CameraWorkflowSettingsResponse(CameraWorkflowSettingsBase):
    """Schema for camera workflow settings API responses."""

    device_id: str

    class Config:
        from_attributes = True

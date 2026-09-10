"""
Camera workflow settings schemas for API requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DetectionPathComposition(BaseModel):
    """Single Instant or Bulk pipeline composition for one capability."""

    kind: str = Field(default="single", description="single | two_stage")
    recipe_id: Optional[str] = Field(
        default=None,
        description="Seeded or existing recipe_id shortcut; composition models ignored when set",
    )
    model_id: Optional[str] = None
    version: Optional[str] = "1.0.0"
    proposal_model_id: Optional[str] = None
    proposal_version: Optional[str] = "1.0.0"
    refine_model_id: Optional[str] = None
    refine_version: Optional[str] = "1.0.0"


class CameraWorkflowSettingsBase(BaseModel):
    """Base camera workflow settings schema."""

    auto_face_detection: bool = Field(
        default=False, description="Enable automatic face detection"
    )
    auto_body_detection: bool = Field(
        default=False, description="Enable body detection assignment (catalog; Vision Phase C)"
    )
    assigned_model_id: Optional[str] = Field(
        default=None,
        description="Catalog model_id override for this camera (all paths unless path overrides set)",
    )
    assigned_model_id_instant: Optional[str] = Field(
        default=None,
        description="Catalog model_id override for instant detection",
    )
    assigned_model_id_bulk: Optional[str] = Field(
        default=None,
        description="Catalog model_id override for bulk/recording detection",
    )
    assigned_recipe_id_face_instant: Optional[str] = None
    assigned_recipe_id_face_bulk: Optional[str] = None
    assigned_recipe_id_body_instant: Optional[str] = None
    assigned_recipe_id_body_bulk: Optional[str] = None
    detection_pipelines: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Per-capability Instant/Bulk compositions sent on save",
    )
    processing_options: Dict[str, Any] = Field(
        default_factory=dict, description="Additional processing options"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for face detection",
    )
    enable_performance_optimization: bool = Field(
        default=True,
        description="Enable performance optimization (Workflow 5) for CPU reduction",
    )
    show_performance_indicators: bool = Field(
        default=True,
        description="Display performance metrics and CPU usage indicators",
    )
    default_playback_mode: str = Field(
        default="auto",
        description="Default playback mode: auto, optimized, standard",
    )
    mvr_quality_threshold: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Minimum quality threshold for creating MVR people",
    )
    mvr_periodic_scheduler_enabled: bool = Field(
        default=False,
        description="Enable periodic MVR merge scheduler for this camera",
    )
    mvr_periodic_scheduler_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Similarity threshold used by periodic MVR merge scheduler",
    )
    mvr_periodic_scheduler_frequency_seconds: int = Field(
        default=300,
        ge=30,
        le=86400,
        description="How often to run periodic MVR merge scheduler (seconds)",
    )


class CameraWorkflowSettingsUpdate(BaseModel):
    """Schema for updating camera workflow settings."""

    auto_face_detection: Optional[bool] = None
    auto_body_detection: Optional[bool] = None
    detection_methods: Optional[List[str]] = None
    processing_options: Optional[Dict[str, Any]] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    enable_performance_optimization: Optional[bool] = None
    show_performance_indicators: Optional[bool] = None
    default_playback_mode: Optional[str] = None
    mvr_quality_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    mvr_periodic_scheduler_enabled: Optional[bool] = None
    mvr_periodic_scheduler_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    mvr_periodic_scheduler_frequency_seconds: Optional[int] = Field(None, ge=30, le=86400)
    assigned_model_id: Optional[str] = None
    assigned_model_id_instant: Optional[str] = None
    assigned_model_id_bulk: Optional[str] = None
    assigned_recipe_id_face_instant: Optional[str] = None
    assigned_recipe_id_face_bulk: Optional[str] = None
    assigned_recipe_id_body_instant: Optional[str] = None
    assigned_recipe_id_body_bulk: Optional[str] = None
    detection_pipelines: Optional[Dict[str, Any]] = None


class CameraWorkflowSettingsResponse(CameraWorkflowSettingsBase):
    """Schema for camera workflow settings API responses."""

    device_id: str

    class Config:
        from_attributes = True

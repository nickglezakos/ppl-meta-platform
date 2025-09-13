"""
Storage Management Schemas

Pydantic schemas for storage preferences, configuration, and usage tracking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class UserStoragePreferencesBase(BaseModel):
    """Base schema for user storage preferences."""

    default_collection_size_gb: float = Field(
        default=50.0, ge=1.0, le=1000.0, description="Default collection size in GB"
    )
    default_live_portion_percentage: float = Field(
        default=70.0,
        ge=10.0,
        le=95.0,
        description="Default percentage for live storage portion",
    )
    default_auto_archive_enabled: bool = Field(
        default=True, description="Enable automatic archival by default"
    )
    default_min_age_for_archive_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Minimum age in days before media can be archived",
    )
    enable_storage_notifications: bool = Field(
        default=True, description="Enable storage capacity notifications"
    )
    notification_threshold_percentage: float = Field(
        default=80.0,
        ge=50.0,
        le=98.0,
        description="Storage usage percentage to trigger notifications",
    )
    email_notifications_enabled: bool = Field(
        default=True, description="Enable email notifications for storage events"
    )
    push_notifications_enabled: bool = Field(
        default=True, description="Enable push notifications for storage events"
    )
    auto_delete_old_archives_enabled: bool = Field(
        default=False, description="Automatically delete old archived media"
    )
    auto_delete_after_days: int = Field(
        default=365,
        ge=30,
        le=3650,
        description="Days after which archived media is auto-deleted",
    )
    auto_increase_quota_enabled: bool = Field(
        default=False, description="Automatically increase storage quota when needed"
    )
    max_auto_quota_increase_gb: float = Field(
        default=100.0,
        ge=10.0,
        le=500.0,
        description="Maximum automatic quota increase in GB",
    )
    preferred_compression_enabled: bool = Field(
        default=True, description="Enable compression for archived media"
    )
    preferred_video_quality: str = Field(
        default="medium", description="Preferred video quality for recordings"
    )
    enable_redundant_storage: bool = Field(
        default=False, description="Enable redundant storage for critical media"
    )

    @validator("preferred_video_quality")
    def validate_video_quality(cls, v):
        """Validate video quality setting."""
        allowed_qualities = ["low", "medium", "high", "ultra"]
        if v not in allowed_qualities:
            raise ValueError(f"Video quality must be one of: {allowed_qualities}")
        return v

    @validator("default_live_portion_percentage")
    def validate_live_portion(cls, v):
        """Ensure live portion percentage is reasonable."""
        if v < 10.0:
            raise ValueError("Live portion must be at least 10%")
        if v > 95.0:
            raise ValueError("Live portion cannot exceed 95%")
        return v


class UserStoragePreferencesCreate(UserStoragePreferencesBase):
    """Schema for creating user storage preferences."""

    user_id: UUID = Field(description="User ID for these preferences")


class UserStoragePreferencesUpdate(BaseModel):
    """Schema for updating user storage preferences."""

    default_collection_size_gb: Optional[float] = Field(None, ge=1.0, le=1000.0)
    default_live_portion_percentage: Optional[float] = Field(None, ge=10.0, le=95.0)
    default_auto_archive_enabled: Optional[bool] = None
    default_min_age_for_archive_days: Optional[int] = Field(None, ge=1, le=365)
    enable_storage_notifications: Optional[bool] = None
    notification_threshold_percentage: Optional[float] = Field(None, ge=50.0, le=98.0)
    email_notifications_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    auto_delete_old_archives_enabled: Optional[bool] = None
    auto_delete_after_days: Optional[int] = Field(None, ge=30, le=3650)
    auto_increase_quota_enabled: Optional[bool] = None
    max_auto_quota_increase_gb: Optional[float] = Field(None, ge=10.0, le=500.0)
    preferred_compression_enabled: Optional[bool] = None
    preferred_video_quality: Optional[str] = None
    enable_redundant_storage: Optional[bool] = None

    @validator("preferred_video_quality")
    def validate_video_quality(cls, v):
        """Validate video quality setting."""
        if v is not None:
            allowed_qualities = ["low", "medium", "high", "ultra"]
            if v not in allowed_qualities:
                raise ValueError(f"Video quality must be one of: {allowed_qualities}")
        return v


class UserStoragePreferencesResponse(UserStoragePreferencesBase):
    """Schema for returning user storage preferences."""

    uuid: UUID
    user_id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollectionStorageConfigBase(BaseModel):
    """Base schema for collection storage configuration."""

    total_size_gb: float = Field(ge=1.0, le=1000.0)
    live_portion_percentage: float = Field(ge=10.0, le=95.0)
    archive_portion_percentage: float = Field(ge=5.0, le=90.0)
    warning_threshold_percentage: float = Field(ge=50.0, le=98.0)
    critical_threshold_percentage: float = Field(ge=80.0, le=99.0)
    auto_archive_enabled: bool = True
    min_age_for_archive_days: int = Field(ge=1, le=365)
    auto_delete_enabled: bool = False
    auto_delete_after_days: int = Field(ge=30, le=3650)
    notes: Optional[str] = None

    @validator("archive_portion_percentage", always=True)
    def validate_portion_sum(cls, v, values):
        """Ensure live and archive portions sum to 100%."""
        if "live_portion_percentage" in values:
            live_portion = values["live_portion_percentage"]
            if (
                abs(live_portion + v - 100.0) > 0.1
            ):  # Allow small floating point differences
                raise ValueError("Live and archive portions must sum to 100%")
        return v

    @validator("critical_threshold_percentage")
    def validate_critical_threshold(cls, v, values):
        """Ensure critical threshold is higher than warning threshold."""
        if "warning_threshold_percentage" in values:
            warning_threshold = values["warning_threshold_percentage"]
            if v <= warning_threshold:
                raise ValueError(
                    "Critical threshold must be higher than warning threshold"
                )
        return v


class CollectionStorageConfigCreate(CollectionStorageConfigBase):
    """Schema for creating collection storage configuration."""

    collection_id: int = Field(description="Collection ID for this configuration")


class CollectionStorageConfigUpdate(BaseModel):
    """Schema for updating collection storage configuration."""

    total_size_gb: Optional[float] = Field(None, ge=1.0, le=1000.0)
    live_portion_percentage: Optional[float] = Field(None, ge=10.0, le=95.0)
    archive_portion_percentage: Optional[float] = Field(None, ge=5.0, le=90.0)
    warning_threshold_percentage: Optional[float] = Field(None, ge=50.0, le=98.0)
    critical_threshold_percentage: Optional[float] = Field(None, ge=80.0, le=99.0)
    auto_archive_enabled: Optional[bool] = None
    min_age_for_archive_days: Optional[int] = Field(None, ge=1, le=365)
    auto_delete_enabled: Optional[bool] = None
    auto_delete_after_days: Optional[int] = Field(None, ge=30, le=3650)
    notes: Optional[str] = None


class CollectionStorageConfigResponse(CollectionStorageConfigBase):
    """Schema for returning collection storage configuration."""

    uuid: UUID
    collection_id: int
    live_capacity_gb: float
    archive_capacity_gb: float
    total_capacity_bytes: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollectionStorageUsageResponse(BaseModel):
    """Schema for returning collection storage usage."""

    uuid: UUID
    collection_id: int
    total_used_bytes: int
    live_portion_used_bytes: int
    archive_portion_used_bytes: int
    total_media_count: int
    live_media_count: int
    archived_media_count: int
    is_near_capacity: bool
    is_at_capacity: bool
    requires_cleanup: bool
    last_archival_run: Optional[datetime]
    last_cleanup_run: Optional[datetime]
    last_notification_sent: Optional[datetime]
    avg_file_size_bytes: int
    largest_file_size_bytes: int
    oldest_media_date: Optional[datetime]
    newest_media_date: Optional[datetime]
    total_used_gb: float
    live_used_gb: float
    archive_used_gb: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StorageStatusResponse(BaseModel):
    """Combined storage status for a collection."""

    collection_id: int
    collection_name: str
    config: CollectionStorageConfigResponse
    usage: CollectionStorageUsageResponse
    usage_percentage: float
    live_usage_percentage: float
    archive_usage_percentage: float
    available_space_gb: float
    notifications: List[Dict[str, Any]] = []


class StorageNotification(BaseModel):
    """Storage notification schema."""

    type: str  # "warning", "critical", "info"
    message: str
    collection_id: int
    collection_name: str
    usage_percentage: float
    timestamp: datetime
    actions: List[Dict[str, str]] = []


class StorageCleanupRequest(BaseModel):
    """Request schema for storage cleanup operations."""

    action: str = Field(
        description="Cleanup action: delete_old, archive_all, move_external"
    )
    days_threshold: Optional[int] = Field(30, ge=1, le=3650)
    dry_run: bool = Field(False, description="Preview changes without applying them")
    force: bool = Field(False, description="Force cleanup even if risky")

    @validator("action")
    def validate_action(cls, v):
        """Validate cleanup action."""
        allowed_actions = [
            "delete_old",
            "archive_all",
            "move_external",
            "compress_archives",
        ]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v


class StorageCleanupResponse(BaseModel):
    """Response schema for storage cleanup operations."""

    success: bool
    action: str
    collection_id: int
    items_processed: int
    space_freed_gb: float
    estimated_time_seconds: Optional[int] = None
    warnings: List[str] = []
    errors: List[str] = []
    dry_run: bool = False


class StorageRecommendation(BaseModel):
    """Storage size recommendation schema."""

    recommended_total_gb: float
    recommended_live_gb: float
    recommended_archive_gb: float
    camera_type: str
    base_user_preference: float
    adjustment_multiplier: float
    reasoning: str = ""


class StorageUsageSummary(BaseModel):
    """Summary of storage usage across all user collections."""

    total_collections: int
    total_allocated_gb: float
    total_used_gb: float
    usage_percentage: float
    collections_near_capacity: int
    collections_at_capacity: int
    efficiency_score: float
    recommendations: List[str] = []


class StorageValidationResult(BaseModel):
    """Result of storage settings validation."""

    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []


# Response classes for API endpoints
class StorageRecommendationResponse(BaseModel):
    """Response containing storage recommendations."""

    recommendations: List[StorageRecommendation]


class StorageUsageSummaryResponse(BaseModel):
    """Response containing storage usage summary."""

    summary: StorageUsageSummary

"""
Collection Storage Management Models

This module defines the database models for managing storage quotas, usage tracking,
and archival status for camera collections in the PPL Meta Platform.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel


class CollectionStorageConfig(BaseModel):
    """
    Storage configuration for camera collections.

    Defines size limits, live/archive split, and archival policies for each collection.
    """

    __tablename__ = "collection_storage_configs"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Collection reference
    collection_id = Column(
        Integer, ForeignKey("media_collections.id"), unique=True, nullable=False
    )
    collection = relationship("MediaCollection", back_populates="storage_config")

    # Storage configuration
    total_size_gb = Column(
        Float, default=50.0, nullable=False
    )  # Default 50GB per collection
    live_portion_percentage = Column(
        Float, default=70.0, nullable=False
    )  # 70% for live streaming
    archive_portion_percentage = Column(
        Float, default=30.0, nullable=False
    )  # 30% for archive

    # Monitoring thresholds
    warning_threshold_percentage = Column(
        Float, default=80.0, nullable=False
    )  # Warn at 80%
    critical_threshold_percentage = Column(
        Float, default=95.0, nullable=False
    )  # Critical at 95%

    # Auto-archival settings
    auto_archive_enabled = Column(Boolean, default=True, nullable=False)
    min_age_for_archive_days = Column(
        Integer, default=7, nullable=False
    )  # Archive after 7 days minimum

    # Storage policies
    auto_delete_enabled = Column(Boolean, default=False, nullable=False)
    auto_delete_after_days = Column(
        Integer, default=365, nullable=False
    )  # Delete archives after 1 year

    # Metadata
    notes = Column(Text)  # Admin notes about storage configuration

    def __repr__(self):
        return f"<CollectionStorageConfig(collection_id={self.collection_id}, total_size={self.total_size_gb}GB)>"

    @property
    def live_capacity_gb(self) -> float:
        """Calculate live portion capacity in GB."""
        return self.total_size_gb * (self.live_portion_percentage / 100)

    @property
    def archive_capacity_gb(self) -> float:
        """Calculate archive portion capacity in GB."""
        return self.total_size_gb * (self.archive_portion_percentage / 100)

    @property
    def live_capacity_bytes(self) -> int:
        """Calculate live portion capacity in bytes."""
        return int(self.live_capacity_gb * 1024 * 1024 * 1024)

    @property
    def archive_capacity_bytes(self) -> int:
        """Calculate archive portion capacity in bytes."""
        return int(self.archive_capacity_gb * 1024 * 1024 * 1024)

    @property
    def total_capacity_bytes(self) -> int:
        """Calculate total capacity in bytes."""
        return int(self.total_size_gb * 1024 * 1024 * 1024)


class CollectionStorageUsage(BaseModel):
    """
    Real-time storage usage tracking for collections.

    Tracks current usage, media counts, and capacity status for monitoring and alerts.
    """

    __tablename__ = "collection_storage_usage"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Collection reference
    collection_id = Column(
        Integer, ForeignKey("media_collections.id"), unique=True, nullable=False
    )
    collection = relationship("MediaCollection", back_populates="storage_usage")

    # Current usage tracking (in bytes)
    total_used_bytes = Column(Integer, default=0, nullable=False)
    live_portion_used_bytes = Column(Integer, default=0, nullable=False)
    archive_portion_used_bytes = Column(Integer, default=0, nullable=False)

    # Media counts
    total_media_count = Column(Integer, default=0, nullable=False)
    live_media_count = Column(Integer, default=0, nullable=False)
    archived_media_count = Column(Integer, default=0, nullable=False)

    # Storage status flags
    is_near_capacity = Column(Boolean, default=False, nullable=False)
    is_at_capacity = Column(Boolean, default=False, nullable=False)
    requires_cleanup = Column(Boolean, default=False, nullable=False)

    # Activity tracking
    last_archival_run = Column(DateTime)
    last_cleanup_run = Column(DateTime)
    last_notification_sent = Column(DateTime)

    # Performance metrics
    avg_file_size_bytes = Column(Integer, default=0)
    largest_file_size_bytes = Column(Integer, default=0)
    oldest_media_date = Column(DateTime)
    newest_media_date = Column(DateTime)

    def __repr__(self):
        return f"<CollectionStorageUsage(collection_id={self.collection_id}, used={self.total_used_bytes} bytes)>"

    @property
    def total_used_gb(self) -> float:
        """Get total used storage in GB."""
        return self.total_used_bytes / (1024 * 1024 * 1024)

    @property
    def live_used_gb(self) -> float:
        """Get live portion used storage in GB."""
        return self.live_portion_used_bytes / (1024 * 1024 * 1024)

    @property
    def archive_used_gb(self) -> float:
        """Get archive portion used storage in GB."""
        return self.archive_portion_used_bytes / (1024 * 1024 * 1024)

    def calculate_usage_percentage(self, total_capacity_bytes: int) -> float:
        """Calculate overall usage percentage."""
        if total_capacity_bytes == 0:
            return 0.0
        return (self.total_used_bytes / total_capacity_bytes) * 100

    def calculate_live_usage_percentage(self, live_capacity_bytes: int) -> float:
        """Calculate live portion usage percentage."""
        if live_capacity_bytes == 0:
            return 0.0
        return (self.live_portion_used_bytes / live_capacity_bytes) * 100


class MediaArchiveStatus(BaseModel):
    """
    Archive status tracking for individual media files.

    Tracks whether media is in live or archive storage, with metadata about archival process.
    """

    __tablename__ = "media_archive_status"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Media reference
    media_id = Column(Integer, ForeignKey("media.id"), unique=True, nullable=False)
    media = relationship("Media", back_populates="archive_status")

    # Archive status
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime)
    archive_reason = Column(
        String(100)
    )  # "auto_archive", "manual_archive", "capacity_limit", "policy"

    # Storage locations
    live_storage_path = Column(String(500))
    archive_storage_path = Column(String(500))

    # Access characteristics
    can_stream_immediately = Column(Boolean, default=True, nullable=False)
    requires_retrieval = Column(Boolean, default=False, nullable=False)
    estimated_retrieval_time_seconds = Column(Integer, default=0)

    # Archive metadata
    original_file_size_bytes = Column(Integer)
    compressed_file_size_bytes = Column(Integer)
    compression_ratio = Column(Float)
    checksum = Column(String(64))  # File integrity verification

    # Access tracking
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)
    retrieval_count = Column(Integer, default=0)

    def __repr__(self):
        status = "archived" if self.is_archived else "live"
        return f"<MediaArchiveStatus(media_id={self.media_id}, status={status})>"

    @property
    def is_live(self) -> bool:
        """Check if media is in live storage."""
        return not self.is_archived

    @property
    def storage_savings_bytes(self) -> int:
        """Calculate storage savings from compression (if any)."""
        if self.original_file_size_bytes and self.compressed_file_size_bytes:
            return self.original_file_size_bytes - self.compressed_file_size_bytes
        return 0

    def mark_as_archived(self, reason: str, archive_path: str = None):
        """Mark media as archived with metadata."""
        self.is_archived = True
        self.archived_at = datetime.utcnow()
        self.archive_reason = reason
        self.can_stream_immediately = False
        self.requires_retrieval = True
        if archive_path:
            self.archive_storage_path = archive_path

    def mark_as_live(self, live_path: str = None):
        """Mark media as live/unarchived."""
        self.is_archived = False
        self.archived_at = None
        self.archive_reason = None
        self.can_stream_immediately = True
        self.requires_retrieval = False
        if live_path:
            self.live_storage_path = live_path


class UserStoragePreferences(BaseModel):
    """
    User-specific storage preferences and defaults.

    Stores user preferences for default collection sizes, notification settings,
    and automatic management policies.
    """

    __tablename__ = "user_storage_preferences"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # User reference
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)

    # Default collection settings
    default_collection_size_gb = Column(Float, default=50.0, nullable=False)
    default_live_portion_percentage = Column(Float, default=70.0, nullable=False)
    default_auto_archive_enabled = Column(Boolean, default=True, nullable=False)
    default_min_age_for_archive_days = Column(Integer, default=7, nullable=False)

    # Notification preferences
    enable_storage_notifications = Column(Boolean, default=True, nullable=False)
    notification_threshold_percentage = Column(Float, default=80.0, nullable=False)
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)
    push_notifications_enabled = Column(Boolean, default=True, nullable=False)

    # Auto-management preferences
    auto_delete_old_archives_enabled = Column(Boolean, default=False, nullable=False)
    auto_delete_after_days = Column(
        Integer, default=365, nullable=False
    )  # Delete archives after 1 year
    auto_increase_quota_enabled = Column(Boolean, default=False, nullable=False)
    max_auto_quota_increase_gb = Column(Float, default=100.0)  # Max auto-increase limit

    # Advanced settings
    preferred_compression_enabled = Column(Boolean, default=True, nullable=False)
    preferred_video_quality = Column(
        String(20), default="medium"
    )  # low, medium, high, ultra
    enable_redundant_storage = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<UserStoragePreferences(user_id={self.user_id}, default_size={self.default_collection_size_gb}GB)>"

    @classmethod
    def get_default_preferences(cls) -> dict:
        """Get default storage preferences for new users."""
        return {
            "default_collection_size_gb": 50.0,
            "default_live_portion_percentage": 70.0,
            "default_auto_archive_enabled": True,
            "default_min_age_for_archive_days": 7,
            "enable_storage_notifications": True,
            "notification_threshold_percentage": 80.0,
            "email_notifications_enabled": True,
            "push_notifications_enabled": True,
            "auto_delete_old_archives_enabled": False,
            "auto_delete_after_days": 365,
            "auto_increase_quota_enabled": False,
            "max_auto_quota_increase_gb": 100.0,
            "preferred_compression_enabled": True,
            "preferred_video_quality": "medium",
            "enable_redundant_storage": False,
        }

    def to_dict(self) -> dict:
        """Convert preferences to dictionary."""
        return {
            "user_id": str(self.user_id),
            "default_collection_size_gb": self.default_collection_size_gb,
            "default_live_portion_percentage": self.default_live_portion_percentage,
            "default_auto_archive_enabled": self.default_auto_archive_enabled,
            "default_min_age_for_archive_days": self.default_min_age_for_archive_days,
            "enable_storage_notifications": self.enable_storage_notifications,
            "notification_threshold_percentage": self.notification_threshold_percentage,
            "email_notifications_enabled": self.email_notifications_enabled,
            "push_notifications_enabled": self.push_notifications_enabled,
            "auto_delete_old_archives_enabled": self.auto_delete_old_archives_enabled,
            "auto_delete_after_days": self.auto_delete_after_days,
            "auto_increase_quota_enabled": self.auto_increase_quota_enabled,
            "max_auto_quota_increase_gb": self.max_auto_quota_increase_gb,
            "preferred_compression_enabled": self.preferred_compression_enabled,
            "preferred_video_quality": self.preferred_video_quality,
            "enable_redundant_storage": self.enable_redundant_storage,
        }

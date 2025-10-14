# ppl-meta-cameras/src/models/profile_template.py

"""
User Profile Template Model
Enables users to save, share, and manage custom recording configuration templates
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserProfileTemplate(Base):
    """
    User-created recording profile templates for saving and sharing configurations.

    Templates allow users to save custom recording configurations and apply them
    to multiple cameras or share them with other users.
    """

    __tablename__ = "user_profile_templates"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    template_uuid = Column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    # Template metadata
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        String(50), nullable=True, index=True
    )  # e.g., "security", "monitoring", "event"
    tags = Column(JSON, nullable=True)  # List of tags for search

    # Template configuration (mirrors CameraRecordingProfile structure)
    # Recording Quality Settings
    quality = Column(String(20), default="high")
    format = Column(String(10), default="mp4")
    resolution = Column(String(20), default="1920x1080")
    frame_rate = Column(Integer, default=30)
    bitrate_kbps = Column(Integer, default=5000)

    # Duration and Timing
    default_duration_seconds = Column(Integer, default=30)
    max_duration_seconds = Column(Integer, default=3600)
    segment_interval_seconds = Column(Integer, nullable=True)

    # Automatic Recording Settings
    enable_auto_recording = Column(Boolean, default=False)
    auto_recording_schedule = Column(JSON, nullable=True)
    motion_detection_enabled = Column(Boolean, default=False)
    motion_sensitivity = Column(String(20), default="medium")

    # Audio Settings
    enable_audio = Column(Boolean, default=True)
    audio_quality = Column(String(20), default="medium")
    audio_bitrate_kbps = Column(Integer, default=128)

    # Storage and Retention
    storage_location = Column(String(200), default="default")
    retention_days = Column(Integer, default=30)
    auto_delete_enabled = Column(Boolean, default=True)
    compression_enabled = Column(Boolean, default=True)

    # Processing Settings
    enable_face_detection = Column(Boolean, default=False)
    enable_object_detection = Column(Boolean, default=False)
    processing_priority = Column(String(20), default="normal")

    # Advanced Configuration
    custom_ffmpeg_params = Column(JSON, nullable=True)
    metadata_config = Column(JSON, nullable=True)
    notification_config = Column(JSON, nullable=True)

    # User and ownership
    created_by_user_id = Column(String(100), nullable=False, index=True)
    organization_id = Column(String(100), nullable=True, index=True)
    is_public = Column(Boolean, default=False, index=True)  # Can be shared publicly
    is_featured = Column(Boolean, default=False, index=True)  # Featured templates

    # Usage tracking
    usage_count = Column(Integer, default=0, index=True)
    last_used_at = Column(DateTime, nullable=True)
    favorite_count = Column(Integer, default=0, index=True)

    # Version and sharing
    version = Column(String(20), default="1.0")
    parent_template_id = Column(
        Integer, ForeignKey("user_profile_templates.id"), nullable=True
    )
    is_template_copy = Column(Boolean, default=False)
    shared_by_user_id = Column(String(100), nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent_template = relationship("UserProfileTemplate", remote_side=[id])
    child_templates = relationship(
        "UserProfileTemplate", back_populates="parent_template"
    )
    favorites = relationship(
        "UserTemplateFavorite", back_populates="template", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "name", "created_by_user_id", name="unique_template_name_per_user"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary representation."""
        return {
            "id": self.id,
            "template_uuid": self.template_uuid,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags or [],
            "configuration": self.get_configuration(),
            "metadata": self.get_metadata(),
            "usage_stats": self.get_usage_stats(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_configuration(self) -> Dict[str, Any]:
        """Get template configuration in recording profile format."""
        return {
            # Recording Quality Settings
            "quality": self.quality,
            "format": self.format,
            "resolution": self.resolution,
            "frame_rate": self.frame_rate,
            "bitrate_kbps": self.bitrate_kbps,
            # Duration and Timing
            "default_duration_seconds": self.default_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "segment_interval_seconds": self.segment_interval_seconds,
            # Automatic Recording Settings
            "enable_auto_recording": self.enable_auto_recording,
            "auto_recording_schedule": self.auto_recording_schedule,
            "motion_detection_enabled": self.motion_detection_enabled,
            "motion_sensitivity": self.motion_sensitivity,
            # Audio Settings
            "enable_audio": self.enable_audio,
            "audio_quality": self.audio_quality,
            "audio_bitrate_kbps": self.audio_bitrate_kbps,
            # Storage and Retention
            "storage_location": self.storage_location,
            "retention_days": self.retention_days,
            "auto_delete_enabled": self.auto_delete_enabled,
            "compression_enabled": self.compression_enabled,
            # Processing Settings
            "enable_face_detection": self.enable_face_detection,
            "enable_object_detection": self.enable_object_detection,
            "processing_priority": self.processing_priority,
            # Advanced Configuration
            "custom_ffmpeg_params": self.custom_ffmpeg_params,
            "metadata_config": self.metadata_config,
            "notification_config": self.notification_config,
        }

    def get_metadata(self) -> Dict[str, Any]:
        """Get template metadata."""
        return {
            "created_by_user_id": self.created_by_user_id,
            "organization_id": self.organization_id,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "version": self.version,
            "parent_template_id": self.parent_template_id,
            "is_template_copy": self.is_template_copy,
            "shared_by_user_id": self.shared_by_user_id,
        }

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get template usage statistics."""
        return {
            "usage_count": self.usage_count,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "favorite_count": self.favorite_count,
        }

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate template configuration for compatibility."""
        validation_result = {"is_valid": True, "errors": [], "warnings": []}

        # Validate required fields
        if not self.name:
            validation_result["errors"].append("Template name is required")
            validation_result["is_valid"] = False

        # Validate recording settings
        if self.quality not in ["low", "medium", "high", "ultra"]:
            validation_result["errors"].append("Invalid quality setting")
            validation_result["is_valid"] = False

        if self.format not in ["mp4", "avi", "mkv", "webm"]:
            validation_result["errors"].append("Invalid format setting")
            validation_result["is_valid"] = False

        # Validate duration limits
        if self.default_duration_seconds <= 0:
            validation_result["errors"].append("Default duration must be positive")
            validation_result["is_valid"] = False

        if self.max_duration_seconds < self.default_duration_seconds:
            validation_result["errors"].append(
                "Max duration cannot be less than default duration"
            )
            validation_result["is_valid"] = False

        # Validate bitrate settings
        if self.bitrate_kbps <= 0:
            validation_result["warnings"].append("Video bitrate should be positive")

        if self.audio_bitrate_kbps <= 0:
            validation_result["warnings"].append("Audio bitrate should be positive")

        return validation_result

    def clone_template(self, new_name: str, user_id: str) -> "UserProfileTemplate":
        """Create a copy of this template for another user."""
        cloned_template = UserProfileTemplate(
            name=new_name,
            description=f"Copy of {self.name}",
            category=self.category,
            tags=self.tags.copy() if self.tags else None,
            # Copy all configuration
            quality=self.quality,
            format=self.format,
            resolution=self.resolution,
            frame_rate=self.frame_rate,
            bitrate_kbps=self.bitrate_kbps,
            default_duration_seconds=self.default_duration_seconds,
            max_duration_seconds=self.max_duration_seconds,
            segment_interval_seconds=self.segment_interval_seconds,
            enable_auto_recording=self.enable_auto_recording,
            auto_recording_schedule=(
                self.auto_recording_schedule.copy()
                if self.auto_recording_schedule
                else None
            ),
            motion_detection_enabled=self.motion_detection_enabled,
            motion_sensitivity=self.motion_sensitivity,
            enable_audio=self.enable_audio,
            audio_quality=self.audio_quality,
            audio_bitrate_kbps=self.audio_bitrate_kbps,
            storage_location=self.storage_location,
            retention_days=self.retention_days,
            auto_delete_enabled=self.auto_delete_enabled,
            compression_enabled=self.compression_enabled,
            enable_face_detection=self.enable_face_detection,
            enable_object_detection=self.enable_object_detection,
            processing_priority=self.processing_priority,
            custom_ffmpeg_params=(
                self.custom_ffmpeg_params.copy() if self.custom_ffmpeg_params else None
            ),
            metadata_config=(
                self.metadata_config.copy() if self.metadata_config else None
            ),
            notification_config=(
                self.notification_config.copy() if self.notification_config else None
            ),
            # Set ownership and tracking
            created_by_user_id=user_id,
            parent_template_id=self.id,
            is_template_copy=True,
            shared_by_user_id=self.created_by_user_id,
        )

        return cloned_template

    @classmethod
    def from_recording_profile(
        cls,
        profile: "CameraRecordingProfile",
        template_name: str,
        user_id: str,
        description: str = None,
    ) -> "UserProfileTemplate":
        """Create a template from an existing recording profile."""
        return cls(
            name=template_name,
            description=description or f"Template created from profile: {profile.name}",
            category="custom",
            # Copy configuration from profile
            quality=profile.quality,
            format=profile.format,
            resolution=profile.resolution,
            frame_rate=profile.frame_rate,
            bitrate_kbps=profile.bitrate_kbps,
            default_duration_seconds=profile.default_duration_seconds,
            max_duration_seconds=profile.max_duration_seconds,
            segment_interval_seconds=profile.segment_interval_seconds,
            enable_auto_recording=profile.enable_auto_recording,
            auto_recording_schedule=profile.auto_recording_schedule,
            motion_detection_enabled=profile.motion_detection_enabled,
            motion_sensitivity=profile.motion_sensitivity,
            enable_audio=profile.enable_audio,
            audio_quality=profile.audio_quality,
            audio_bitrate_kbps=profile.audio_bitrate_kbps,
            storage_location=profile.storage_location,
            retention_days=profile.retention_days,
            auto_delete_enabled=profile.auto_delete_enabled,
            compression_enabled=profile.compression_enabled,
            enable_face_detection=profile.enable_face_detection,
            enable_object_detection=profile.enable_object_detection,
            processing_priority=profile.processing_priority,
            custom_ffmpeg_params=profile.custom_ffmpeg_params,
            metadata_config=profile.metadata_config,
            notification_config=profile.notification_config,
            created_by_user_id=user_id,
        )


class UserTemplateFavorite(Base):
    """
    User favorites for profile templates.
    Tracks which templates users have marked as favorites.
    """

    __tablename__ = "user_template_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    template_id = Column(
        Integer, ForeignKey("user_profile_templates.id"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("UserProfileTemplate", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "template_id", name="unique_user_template_favorite"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert favorite to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "template_uuid": self.template.template_uuid if self.template else None,
            "template_name": self.template.name if self.template else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TemplateUsageAnalytics(Base):
    """
    Analytics tracking for template usage patterns.
    Stores detailed usage analytics for templates.
    """

    __tablename__ = "template_usage_analytics"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer, ForeignKey("user_profile_templates.id"), nullable=False
    )
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(
        String(50), nullable=False, index=True
    )  # "applied", "copied", "favorited", "shared"
    camera_id = Column(String(100), nullable=True, index=True)
    context_data = Column(JSON, nullable=True)  # Additional context information
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    template = relationship("UserProfileTemplate")

    def to_dict(self) -> Dict[str, Any]:
        """Convert analytics record to dictionary representation."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "user_id": self.user_id,
            "action": self.action,
            "camera_id": self.camera_id,
            "context_data": self.context_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

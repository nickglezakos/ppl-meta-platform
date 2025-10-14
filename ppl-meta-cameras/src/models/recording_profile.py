# ppl-meta-cameras/src/models/recording_profile.py

"""
Camera Recording Profile Model
Defines reusable recording configurations for cameras
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from src.database import Base


class CameraRecordingProfile(Base):
    """
    Recording profile entity for reusable camera recording configurations.

    This model defines all recording parameters that can be applied to cameras,
    including system defaults and user-created custom profiles.
    """

    __tablename__ = "camera_recording_profiles"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    profile_uuid = Column(String(36), unique=True, index=True, nullable=False)

    # Profile metadata
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_default = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # User and ownership
    created_by_user_id = Column(String(100), nullable=False, index=True)
    organization_id = Column(String(100), nullable=True, index=True)

    # Recording configuration parameters
    segment_interval_seconds = Column(Integer, nullable=True)  # null = manual only
    segment_duration_seconds = Column(Integer, default=30, nullable=False)
    auto_segment_recording = Column(Boolean, default=False, nullable=False)

    # Video quality settings
    recording_quality = Column(
        String(20), default="high", nullable=False
    )  # low, medium, high
    video_codec = Column(String(20), default="h264", nullable=False)
    audio_enabled = Column(Boolean, default=False, nullable=False)

    # Processing settings
    auto_face_detection_enabled = Column(Boolean, default=True, nullable=False)
    face_detection_method = Column(String(20), default="two_stage", nullable=False)
    enable_motion_detection = Column(Boolean, default=False, nullable=False)

    # Storage and retention
    storage_location = Column(
        String(50), default="local", nullable=False
    )  # local, s3, gcs, azure
    retention_days = Column(Integer, default=30, nullable=False)
    auto_cleanup_enabled = Column(Boolean, default=True, nullable=False)

    # Schedule and triggers
    schedule_config = Column(JSON, nullable=True)  # Flexible scheduling configuration
    trigger_conditions = Column(
        JSON, nullable=True
    )  # Motion, schedule, manual triggers

    # Metadata and tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cameras = relationship("Camera", back_populates="recording_profile", lazy="dynamic")

    def __repr__(self):
        return f"<CameraRecordingProfile(id={self.id}, name='{self.name}', uuid='{self.profile_uuid}')>"

    @property
    def is_manual_only(self) -> bool:
        """Check if this profile is for manual recording only."""
        return self.segment_interval_seconds is None and not self.auto_segment_recording

    @property
    def effective_recording_config(self) -> Dict[str, Any]:
        """Get the complete recording configuration as a dictionary."""
        return {
            "profile_id": self.id,
            "profile_uuid": self.profile_uuid,
            "profile_name": self.name,
            "segment_interval_seconds": self.segment_interval_seconds,
            "segment_duration_seconds": self.segment_duration_seconds,
            "auto_segment_recording": self.auto_segment_recording,
            "recording_quality": self.recording_quality,
            "video_codec": self.video_codec,
            "audio_enabled": self.audio_enabled,
            "auto_face_detection_enabled": self.auto_face_detection_enabled,
            "face_detection_method": self.face_detection_method,
            "enable_motion_detection": self.enable_motion_detection,
            "storage_location": self.storage_location,
            "retention_days": self.retention_days,
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
            "schedule_config": self.schedule_config,
            "trigger_conditions": self.trigger_conditions,
        }

    def validate_configuration(self) -> Dict[str, str]:
        """
        Validate the recording profile configuration.
        Returns a dictionary of validation errors (empty if valid).
        """
        errors = {}

        # Validate segment interval
        if self.segment_interval_seconds is not None:
            if self.segment_interval_seconds < 5:
                errors["segment_interval"] = (
                    "Minimum interval is 5 seconds to prevent system overload"
                )
            elif self.segment_interval_seconds > 3600:
                errors["segment_interval"] = (
                    "Maximum interval is 1 hour for practical recording schedules"
                )

        # Validate segment duration
        if self.segment_duration_seconds < 5:
            errors["segment_duration"] = (
                "Minimum duration is 5 seconds for meaningful content"
            )
        elif self.segment_duration_seconds > 300:
            errors["segment_duration"] = (
                "Maximum duration is 5 minutes for optimal file management"
            )

        # Validate quality settings
        if self.recording_quality not in ["low", "medium", "high"]:
            errors["recording_quality"] = "Quality must be 'low', 'medium', or 'high'"

        # Validate codec
        if self.video_codec not in ["h264", "h265", "vp8", "vp9"]:
            errors["video_codec"] = "Unsupported video codec"

        # Validate storage location
        if self.storage_location not in ["local", "s3", "gcs", "azure"]:
            errors["storage_location"] = "Unsupported storage location"

        # Validate retention
        if self.retention_days < 1:
            errors["retention_days"] = "Retention must be at least 1 day"
        elif self.retention_days > 365:
            errors["retention_days"] = "Maximum retention is 365 days"

        return errors

    def clone(self, new_name: str, created_by_user_id: str) -> "CameraRecordingProfile":
        """
        Create a clone of this profile with a new name and owner.
        """
        import uuid

        cloned_profile = CameraRecordingProfile(
            profile_uuid=str(uuid.uuid4()),
            name=new_name,
            description=f"Cloned from: {self.name}",
            is_system_default=False,  # Cloned profiles are never system defaults
            is_active=True,
            created_by_user_id=created_by_user_id,
            organization_id=self.organization_id,
            # Copy all configuration parameters
            segment_interval_seconds=self.segment_interval_seconds,
            segment_duration_seconds=self.segment_duration_seconds,
            auto_segment_recording=self.auto_segment_recording,
            recording_quality=self.recording_quality,
            video_codec=self.video_codec,
            audio_enabled=self.audio_enabled,
            auto_face_detection_enabled=self.auto_face_detection_enabled,
            face_detection_method=self.face_detection_method,
            enable_motion_detection=self.enable_motion_detection,
            storage_location=self.storage_location,
            retention_days=self.retention_days,
            auto_cleanup_enabled=self.auto_cleanup_enabled,
            schedule_config=(
                self.schedule_config.copy() if self.schedule_config else None
            ),
            trigger_conditions=(
                self.trigger_conditions.copy() if self.trigger_conditions else None
            ),
        )

        return cloned_profile

    def update_usage_stats(self):
        """Update usage statistics when profile is used."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary representation."""
        return {
            "id": self.id,
            "profile_uuid": self.profile_uuid,
            "name": self.name,
            "description": self.description,
            "is_system_default": self.is_system_default,
            "is_active": self.is_active,
            "created_by_user_id": self.created_by_user_id,
            "organization_id": self.organization_id,
            "configuration": self.effective_recording_config,
            "usage_count": self.usage_count,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def create_system_defaults(cls) -> list["CameraRecordingProfile"]:
        """
        Create the system default recording profiles.
        These profiles are pre-configured for common use cases.
        """
        import uuid

        system_profiles = []

        # 1. Manual Recording Only
        manual_profile = cls(
            profile_uuid=str(uuid.uuid4()),
            name="Manual Recording Only",
            description="Basic on-demand recording without automatic segments",
            is_system_default=True,
            created_by_user_id="system",
            segment_interval_seconds=None,  # Manual only
            segment_duration_seconds=30,
            auto_segment_recording=False,
            recording_quality="high",
            auto_face_detection_enabled=True,
            retention_days=30,
        )
        system_profiles.append(manual_profile)

        # 2. Security Monitor
        security_profile = cls(
            profile_uuid=str(uuid.uuid4()),
            name="Security Monitor",
            description="60-second segments every 5 minutes for security monitoring",
            is_system_default=True,
            created_by_user_id="system",
            segment_interval_seconds=300,  # Every 5 minutes
            segment_duration_seconds=60,  # 60-second segments
            auto_segment_recording=True,
            recording_quality="high",
            auto_face_detection_enabled=True,
            enable_motion_detection=True,
            retention_days=60,
        )
        system_profiles.append(security_profile)

        # 3. Activity Logger
        activity_profile = cls(
            profile_uuid=str(uuid.uuid4()),
            name="Activity Logger",
            description="15-second segments every 30 seconds for detailed activity logging",
            is_system_default=True,
            created_by_user_id="system",
            segment_interval_seconds=30,  # Every 30 seconds
            segment_duration_seconds=15,  # 15-second segments
            auto_segment_recording=True,
            recording_quality="medium",
            auto_face_detection_enabled=True,
            retention_days=14,
        )
        system_profiles.append(activity_profile)

        # 4. Event Detection
        event_profile = cls(
            profile_uuid=str(uuid.uuid4()),
            name="Event Detection",
            description="30-second segments every minute for balanced event detection",
            is_system_default=True,
            created_by_user_id="system",
            segment_interval_seconds=60,  # Every minute
            segment_duration_seconds=30,  # 30-second segments
            auto_segment_recording=True,
            recording_quality="high",
            auto_face_detection_enabled=True,
            enable_motion_detection=True,
            retention_days=30,
        )
        system_profiles.append(event_profile)

        # 5. High Traffic
        high_traffic_profile = cls(
            profile_uuid=str(uuid.uuid4()),
            name="High Traffic",
            description="10-second segments every 15 seconds for high-traffic areas",
            is_system_default=True,
            created_by_user_id="system",
            segment_interval_seconds=15,  # Every 15 seconds
            segment_duration_seconds=10,  # 10-second segments
            auto_segment_recording=True,
            recording_quality="medium",  # Balance quality vs storage
            auto_face_detection_enabled=True,
            retention_days=7,  # Shorter retention due to high volume
        )
        system_profiles.append(high_traffic_profile)

        return system_profiles

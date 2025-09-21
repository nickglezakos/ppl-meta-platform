"""
Camera settings model for storing user preferences per camera.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class CameraSettings(Base):
    """Camera settings model for user preferences."""

    __tablename__ = "camera_settings"

    id = Column(Integer, primary_key=True, index=True)
    camera_device_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Face detection settings
    auto_face_detection = Column(Boolean, default=False, nullable=False)
    detection_methods = Column(JSON, default=lambda: ["two_stage"], nullable=False)

    # Processing options
    processing_options = Column(JSON, default=dict, nullable=False)

    # Recording settings
    auto_recording = Column(Boolean, default=False, nullable=False)
    recording_duration = Column(Integer, default=30, nullable=False)  # seconds

    # Notification settings
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    notification_methods = Column(JSON, default=lambda: ["email"], nullable=False)

    # Storage settings
    store_faces_in_memory = Column(Boolean, default=True, nullable=False)
    persist_after_recording = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "camera_device_id": self.camera_device_id,
            "user_id": self.user_id,
            "auto_face_detection": self.auto_face_detection,
            "detection_methods": self.detection_methods,
            "processing_options": self.processing_options,
            "auto_recording": self.auto_recording,
            "recording_duration": self.recording_duration,
            "notifications_enabled": self.notifications_enabled,
            "notification_methods": self.notification_methods,
            "store_faces_in_memory": self.store_faces_in_memory,
            "persist_after_recording": self.persist_after_recording,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

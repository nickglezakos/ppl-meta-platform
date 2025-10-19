# ppl-meta-orchestrator/src/models/recording_session.py

"""
Recording Session Model for Orchestrator Service
Tracks recording sessions with comprehensive metadata and workflow integration
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Enumeration of recording session status values"""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    TIMEOUT = "timeout"


class RecordingSession(Base):
    """
    Recording session entity for tracking camera recording workflows.

    This model tracks all recording sessions initiated through the orchestrator,
    providing comprehensive workflow management and session tracking capabilities.
    """

    __tablename__ = "recording_sessions"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(36), unique=True, index=True, nullable=False)

    # Camera and user context
    camera_device_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    recording_profile_id = Column(Integer, nullable=True)  # Link to recording profiles

    # Session status and lifecycle
    status = Column(String(20), nullable=False, index=True, default="active")
    # Status values: "active", "completed", "failed", "stopped", "timeout"

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    stopped_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Recording configuration and metadata
    recording_config = Column(JSON, nullable=True)  # Recording parameters
    workflow_metadata = Column(JSON, nullable=True)  # Workflow execution context

    # Performance and tracking
    current_duration_seconds = Column(Float, default=0.0)
    estimated_file_size_bytes = Column(Integer, default=0)
    frames_recorded = Column(Integer, default=0)
    average_fps = Column(Float, nullable=True)

    # Error handling and diagnostics
    error_message = Column(Text, nullable=True)
    warning_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)

    # Workflow integration
    face_detection_triggered = Column(Boolean, default=False)
    face_detection_completed = Column(Boolean, default=False)
    face_detection_session_uuid = Column(String(36), nullable=True)
    workflow_execution_id = Column(String(36), nullable=True)

    # Media service integration
    media_upload_started = Column(Boolean, default=False)
    media_upload_completed = Column(Boolean, default=False)
    media_collection_id = Column(String(36), nullable=True)
    media_uuid = Column(String(36), nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # TODO: Create WorkflowExecution SQLAlchemy model if needed
    # workflow_executions = relationship(
    #     "WorkflowExecution", back_populates="recording_session"
    # )

    def __init__(self, **kwargs):
        if "session_uuid" not in kwargs:
            kwargs["session_uuid"] = str(uuid4())
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "id": self.id,
            "session_uuid": self.session_uuid,
            "camera_device_id": self.camera_device_id,
            "user_id": self.user_id,
            "recording_profile_id": self.recording_profile_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "current_duration_seconds": self.current_duration_seconds,
            "estimated_file_size_bytes": self.estimated_file_size_bytes,
            "frames_recorded": self.frames_recorded,
            "average_fps": self.average_fps,
            "error_message": self.error_message,
            "warning_count": self.warning_count,
            "retry_count": self.retry_count,
            "face_detection_triggered": self.face_detection_triggered,
            "face_detection_completed": self.face_detection_completed,
            "face_detection_session_uuid": self.face_detection_session_uuid,
            "workflow_execution_id": self.workflow_execution_id,
            "media_upload_started": self.media_upload_started,
            "media_upload_completed": self.media_upload_completed,
            "media_collection_id": self.media_collection_id,
            "media_uuid": self.media_uuid,
            "recording_config": self.recording_config,
            "workflow_metadata": self.workflow_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_heartbeat(self):
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()

    def update_progress(
        self,
        duration_seconds: Optional[float] = None,
        file_size_bytes: Optional[int] = None,
        frames_recorded: Optional[int] = None,
        fps: Optional[float] = None,
    ):
        """Update recording progress metrics."""
        if duration_seconds is not None:
            self.current_duration_seconds = duration_seconds
        if file_size_bytes is not None:
            self.estimated_file_size_bytes = file_size_bytes
        if frames_recorded is not None:
            self.frames_recorded = frames_recorded
        if fps is not None:
            self.average_fps = fps

        self.update_heartbeat()

    def mark_completed(self, media_uuid: Optional[str] = None):
        """Mark session as completed successfully."""
        self.status = "completed"
        self.stopped_at = datetime.utcnow()
        if media_uuid:
            self.media_uuid = media_uuid
            self.media_upload_completed = True

    def mark_failed(self, error_message: str):
        """Mark session as failed with error message."""
        self.status = "failed"
        self.stopped_at = datetime.utcnow()
        self.error_message = error_message

    def mark_stopped(self):
        """Mark session as manually stopped."""
        self.status = "stopped"
        self.stopped_at = datetime.utcnow()

    def trigger_face_detection(self, face_detection_session_uuid: str):
        """Mark face detection as triggered."""
        self.face_detection_triggered = True
        self.face_detection_session_uuid = face_detection_session_uuid

    def complete_face_detection(self):
        """Mark face detection as completed."""
        self.face_detection_completed = True

    def start_media_upload(self, media_collection_id: str):
        """Mark media upload as started."""
        self.media_upload_started = True
        self.media_collection_id = media_collection_id

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == "active"

    def is_completed(self) -> bool:
        """Check if session completed successfully."""
        return self.status == "completed"

    def has_error(self) -> bool:
        """Check if session has errors."""
        return self.status == "failed" or self.error_message is not None

    def get_duration_minutes(self) -> float:
        """Get current duration in minutes."""
        return (
            self.current_duration_seconds / 60.0
            if self.current_duration_seconds
            else 0.0
        )

    def get_estimated_file_size_mb(self) -> float:
        """Get estimated file size in MB."""
        return (
            self.estimated_file_size_bytes / (1024 * 1024)
            if self.estimated_file_size_bytes
            else 0.0
        )


class RecordingSessionStatus(Base):
    """
    Real-time status tracking for recording sessions.

    Stores time-series data for monitoring recording progress and performance.
    """

    __tablename__ = "recording_session_status"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(
        String(36), ForeignKey("recording_sessions.session_uuid"), nullable=False
    )
    status_timestamp = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Recording progress
    duration_seconds = Column(Float, nullable=False, default=0.0)
    file_size_bytes = Column(Integer, default=0)
    frames_recorded = Column(Integer, default=0)
    current_fps = Column(Float, nullable=True)

    # System performance metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    disk_write_speed_mbps = Column(Float, nullable=True)
    disk_space_available_gb = Column(Float, nullable=True)

    # Quality metrics
    video_bitrate_kbps = Column(Integer, nullable=True)
    audio_bitrate_kbps = Column(Integer, nullable=True)
    frame_drop_count = Column(Integer, default=0)
    encoding_lag_seconds = Column(Float, default=0.0)

    # Error tracking
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    last_warning = Column(Text, nullable=True)

    # Additional context
    context_data = Column(JSON, nullable=True)

    # Relationships
    recording_session = relationship("RecordingSession")

    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary representation."""
        return {
            "id": self.id,
            "session_uuid": self.session_uuid,
            "status_timestamp": (
                self.status_timestamp.isoformat() if self.status_timestamp else None
            ),
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "frames_recorded": self.frames_recorded,
            "current_fps": self.current_fps,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "disk_write_speed_mbps": self.disk_write_speed_mbps,
            "disk_space_available_gb": self.disk_space_available_gb,
            "video_bitrate_kbps": self.video_bitrate_kbps,
            "audio_bitrate_kbps": self.audio_bitrate_kbps,
            "frame_drop_count": self.frame_drop_count,
            "encoding_lag_seconds": self.encoding_lag_seconds,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "last_error": self.last_error,
            "last_warning": self.last_warning,
            "context_data": self.context_data,
        }

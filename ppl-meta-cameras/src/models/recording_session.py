"""
Recording Session Models for Camera Service
Created: 2025-10-15
Purpose: SQLAlchemy models for recording session tracking system
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base


class RecordingSession(Base):
    """
    Core recording session tracking.
    Each recording session represents a complete recording workflow with unique UUID.
    """

    __tablename__ = "recording_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    user_id = Column(String(100), nullable=False)
    status = Column(
        String(20), nullable=False, default="active"
    )  # active, completed, failed, stopped
    started_at = Column(DateTime, default=datetime.utcnow)
    stopped_at = Column(DateTime, nullable=True)
    recording_quality = Column(String(20), default="high")  # low, medium, high
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Real-time tracking fields
    current_duration_seconds = Column(Float, default=0.0)
    estimated_file_size_bytes = Column(BigInteger, default=0)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    frames_recorded = Column(Integer, default=0)
    average_fps = Column(Float, nullable=True)

    # Relationships
    camera = relationship("Camera", back_populates="recording_sessions")
    recording_metadata = relationship(
        "RecordingMetadata",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    files = relationship(
        "RecordingFile", back_populates="session", cascade="all, delete-orphan"
    )
    status_reports = relationship(
        "RecordingStatus", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RecordingSession(uuid={self.session_uuid}, camera_id={self.camera_id}, status={self.status})>"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def duration_seconds(self):
        if self.stopped_at and self.started_at:
            return (self.stopped_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return 0

    def to_dict(self):
        return {
            "id": self.id,
            "session_uuid": self.session_uuid,
            "camera_id": self.camera_id,
            "user_id": self.user_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "recording_quality": self.recording_quality,
            "current_duration_seconds": self.current_duration_seconds,
            "estimated_file_size_bytes": self.estimated_file_size_bytes,
            "frames_recorded": self.frames_recorded,
            "average_fps": self.average_fps,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecordingMetadata(Base):
    """
    Recording configuration and technical metadata for each session.
    One-to-one relationship with RecordingSession.
    """

    __tablename__ = "recording_metadata"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(
        String(36),
        ForeignKey("recording_sessions.session_uuid", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    recording_profile_id = Column(
        Integer, nullable=True
    )  # Future: link to recording profiles

    # Configuration parameters
    segment_interval_seconds = Column(Integer, nullable=True)
    segment_duration_seconds = Column(Integer, default=30)
    auto_face_detection_enabled = Column(Boolean, default=True)
    video_codec = Column(String(20), default="h264")
    audio_enabled = Column(Boolean, default=False)

    # Technical specifications
    resolution_width = Column(Integer, nullable=True)
    resolution_height = Column(Integer, nullable=True)
    fps = Column(Integer, nullable=True)
    bitrate = Column(Integer, nullable=True)

    # Processing settings
    face_detection_method = Column(String(20), default="two_stage")
    quality_preset = Column(String(20), default="balanced")

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("RecordingSession", back_populates="recording_metadata")

    def __repr__(self):
        return f"<RecordingMetadata(session_uuid={self.session_uuid}, quality={self.quality_preset})>"

    def to_dict(self):
        return {
            "id": self.id,
            "session_uuid": self.session_uuid,
            "recording_profile_id": self.recording_profile_id,
            "segment_interval_seconds": self.segment_interval_seconds,
            "segment_duration_seconds": self.segment_duration_seconds,
            "auto_face_detection_enabled": self.auto_face_detection_enabled,
            "video_codec": self.video_codec,
            "audio_enabled": self.audio_enabled,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "fps": self.fps,
            "bitrate": self.bitrate,
            "face_detection_method": self.face_detection_method,
            "quality_preset": self.quality_preset,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RecordingFile(Base):
    """
    File tracking for recorded videos with media service integration.
    Multiple files can belong to one recording session (segments).
    """

    __tablename__ = "recording_files"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(
        String(36),
        ForeignKey("recording_sessions.session_uuid", ondelete="CASCADE"),
        nullable=False,
    )
    file_uuid = Column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    # File location and organization
    file_path = Column(String(500), nullable=False)
    relative_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(BigInteger, default=0)

    # File type and format
    mime_type = Column(String(100), default="video/mp4")
    video_codec = Column(String(20), nullable=True)
    audio_codec = Column(String(20), nullable=True)
    duration_seconds = Column(Float, default=0.0)

    # Storage backend information
    storage_type = Column(String(20), default="local")  # local, s3, gcs, azure
    storage_bucket = Column(String(100), nullable=True)
    storage_region = Column(String(50), nullable=True)

    # File integrity and verification
    checksum_md5 = Column(String(32), nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    file_verified_at = Column(DateTime, nullable=True)

    # Media service integration
    is_uploaded_to_media = Column(Boolean, default=False)
    media_collection_id = Column(String(36), nullable=True)
    media_uuid = Column(String(36), nullable=True)  # UUID from media service
    media_upload_attempted_at = Column(DateTime, nullable=True)
    media_upload_completed_at = Column(DateTime, nullable=True)

    # Lifecycle management
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    retention_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("RecordingSession", back_populates="files")

    def __repr__(self):
        return f"<RecordingFile(uuid={self.file_uuid}, session={self.session_uuid}, media_uuid={self.media_uuid})>"

    def to_dict(self):
        return {
            "id": self.id,
            "session_uuid": self.session_uuid,
            "file_uuid": self.file_uuid,
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "duration_seconds": self.duration_seconds,
            "storage_type": self.storage_type,
            "storage_bucket": self.storage_bucket,
            "storage_region": self.storage_region,
            "checksum_md5": self.checksum_md5,
            "checksum_sha256": self.checksum_sha256,
            "file_verified_at": (
                self.file_verified_at.isoformat() if self.file_verified_at else None
            ),
            "is_uploaded_to_media": self.is_uploaded_to_media,
            "media_collection_id": self.media_collection_id,
            "media_uuid": self.media_uuid,
            "media_upload_attempted_at": (
                self.media_upload_attempted_at.isoformat()
                if self.media_upload_attempted_at
                else None
            ),
            "media_upload_completed_at": (
                self.media_upload_completed_at.isoformat()
                if self.media_upload_completed_at
                else None
            ),
            "is_archived": self.is_archived,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "retention_until": (
                self.retention_until.isoformat() if self.retention_until else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecordingStatus(Base):
    """
    Real-time recording status and performance metrics.
    Multiple status reports per recording session for monitoring.
    """

    __tablename__ = "recording_status"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(
        String(36),
        ForeignKey("recording_sessions.session_uuid", ondelete="CASCADE"),
        nullable=False,
    )

    # Real-time recording metrics
    current_duration_seconds = Column(Float, default=0.0)
    current_file_size_bytes = Column(BigInteger, default=0)
    frames_recorded = Column(Integer, default=0)
    frames_dropped = Column(Integer, default=0)
    average_fps = Column(Float, nullable=True)
    current_bitrate = Column(Integer, nullable=True)

    # System performance metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    disk_space_available_mb = Column(BigInteger, nullable=True)
    network_upload_speed_mbps = Column(Float, nullable=True)

    # Error tracking
    error_count = Column(Integer, default=0)
    last_error_message = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Timestamps
    reported_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("RecordingSession", back_populates="status_reports")

    def __repr__(self):
        return f"<RecordingStatus(session={self.session_uuid}, duration={self.current_duration_seconds}s)>"

    def to_dict(self):
        return {
            "id": self.id,
            "session_uuid": self.session_uuid,
            "current_duration_seconds": self.current_duration_seconds,
            "current_file_size_bytes": self.current_file_size_bytes,
            "frames_recorded": self.frames_recorded,
            "frames_dropped": self.frames_dropped,
            "average_fps": self.average_fps,
            "current_bitrate": self.current_bitrate,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "disk_space_available_mb": self.disk_space_available_mb,
            "network_upload_speed_mbps": self.network_upload_speed_mbps,
            "error_count": self.error_count,
            "last_error_message": self.last_error_message,
            "last_error_at": (
                self.last_error_at.isoformat() if self.last_error_at else None
            ),
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Update the Camera model to include recording sessions relationship
# This should be added to the existing Camera model in models/camera.py
"""
Add this to the existing Camera model:

# Recording sessions relationship
recording_sessions = relationship("RecordingSession", back_populates="camera", cascade="all, delete-orphan")

def get_active_recording_session(self):
    '''Get currently active recording session for this camera'''
    for session in self.recording_sessions:
        if session.is_active:
            return session
    return None

def has_active_recording(self):
    '''Check if camera currently has an active recording session'''
    return self.get_active_recording_session() is not None
"""

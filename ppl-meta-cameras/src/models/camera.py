"""
Camera-related database models for PPL Meta Cameras microservice.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class CameraStatus(str, Enum):
    """Camera status enumeration."""

    AVAILABLE = "available"
    CONNECTED = "connected"
    IN_USE = "in_use"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class CameraType(str, Enum):
    """Camera type enumeration."""

    USB = "USB"
    IP = "IP"
    RTSP = "RTSP"
    WEBCAM = "WEBCAM"
    VIRTUAL = "VIRTUAL"
    MOBILE = "MOBILE"
    EDGE = "EDGE"


class StreamQuality(str, Enum):
    """Stream quality enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class Camera(Base):
    """Camera model representing detected cameras."""

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    device_id = Column(String(255), unique=True, nullable=False, index=True)
    camera_type = Column(SQLEnum(CameraType), nullable=False)
    status = Column(SQLEnum(CameraStatus), default=CameraStatus.AVAILABLE)

    # Technical specifications
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    max_fps = Column(Integer)
    supported_formats = Column(JSON)  # List of supported video formats

    # Connection details
    connection_string = Column(String(500))  # USB path, IP address, RTSP URL
    port = Column(Integer)
    username = Column(String(100))
    password = Column(String(100))  # Should be encrypted in production

    # Metadata
    manufacturer = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(100))
    firmware_version = Column(String(50))

    # Capabilities
    supports_streaming = Column(Boolean, default=True)
    supports_recording = Column(Boolean, default=True)
    supports_audio = Column(Boolean, default=False)
    supports_ptz = Column(Boolean, default=False)  # Pan/Tilt/Zoom

    # Status tracking
    last_seen = Column(DateTime, default=func.now())
    last_error = Column(Text)
    is_active = Column(Boolean, default=True)
    archived = Column(Boolean, default=False, index=True)  # Archive status for hiding cameras

    # Pipeline Configuration (Instant Detection + Recording Decoupling)
    instant_detection_enabled = Column(Boolean, default=True)
    recording_pipeline_enabled = Column(Boolean, default=True)
    instant_detection_interval_seconds = Column(Integer, default=5)
    segment_duration_seconds = Column(Integer, default=30)

    # Workflow Configuration (Face Detection & Performance)
    auto_face_detection = Column(Boolean, default=False)
    detection_methods = Column(JSON, default=lambda: ['opencv', 'dlib'])  # ['opencv', 'dlib', 'mtcnn', 'yolo']
    processing_options = Column(JSON, default=dict)  # Additional processing options
    confidence_threshold = Column(Float, default=0.7)
    enable_performance_optimization = Column(Boolean, default=True)
    show_performance_indicators = Column(Boolean, default=True)
    default_playback_mode = Column(String(50), default='auto')
    mvr_quality_threshold = Column(Float, default=0.20)

    # Recording profile assignment - TODO: Add when Phase 2 is implemented
    # recording_profile_id = Column(
    #     Integer, ForeignKey("camera_recording_profiles.id"), nullable=True
    # )

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    sessions = relationship("CameraSession", back_populates="camera")
    capabilities = relationship("CameraCapability", back_populates="camera")
    recording_sessions = relationship(
        "RecordingSession", back_populates="camera", cascade="all, delete-orphan"
    )
    # recording_profile = relationship("CameraRecordingProfile", back_populates="cameras")

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}', type='{self.camera_type}', status='{self.status}')>"

    # Recording session management methods
    def get_active_recording_session(self):
        """Get currently active recording session for this camera."""
        for session in self.recording_sessions:
            if session.is_active:
                return session
        return None

    def has_active_recording(self):
        """Check if camera currently has an active recording session."""
        return self.get_active_recording_session() is not None

    # TODO: Uncomment when Phase 2 recording profiles are implemented
    # @property
    # def effective_recording_config(self) -> Optional[dict]:
    #     """
    #     Get the effective recording configuration for this camera.

    #     Returns the assigned recording profile configuration, or None if no profile assigned.
    #     This property provides a convenient way to access recording parameters.
    #     """
    #     if self.recording_profile:
    #         return self.recording_profile.effective_recording_config
    #     return None

    # @property
    # def supports_automatic_recording(self) -> bool:
    #     """
    #     Check if this camera supports automatic recording based on its profile.

    #     Returns:
    #         True if camera has a profile with automatic recording enabled, False otherwise
    #     """
    #     config = self.effective_recording_config
    #     if config:
    #         return config.get("auto_segment_recording", False)
    #     return False

    # def get_recording_schedule_info(self) -> dict:
    #     """
    #     Get recording schedule information for this camera.

    #     Returns:
    #         Dictionary with schedule details or empty dict if no profile assigned
    #     """
    #     config = self.effective_recording_config
    #     if not config:
    #         return {}

    #     return {
    #         "has_profile": True,
    #         "profile_name": config.get("profile_name", "Unknown"),
    #         "auto_recording": config.get("auto_segment_recording", False),
    #         "interval_seconds": config.get("segment_interval_seconds"),
    #         "duration_seconds": config.get("segment_duration_seconds", 30),
    #         "recording_quality": config.get("recording_quality", "high"),
    #         "face_detection_enabled": config.get("auto_face_detection_enabled", True),
    #     }


class CameraSession(Base):
    """Camera session model for tracking active connections."""

    __tablename__ = "camera_sessions"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False, index=True)

    # Session details
    user_id = Column(String(100))  # Who initiated the session
    purpose = Column(String(100))  # streaming, recording, monitoring
    stream_quality = Column(SQLEnum(StreamQuality), default=StreamQuality.MEDIUM)

    # Technical parameters
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    fps = Column(Integer)
    bitrate = Column(Integer)

    # Session tracking
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=func.now())

    # Statistics
    frames_captured = Column(Integer, default=0)
    bytes_transmitted = Column(Integer, default=0)
    duration_seconds = Column(Float)

    # Error tracking
    error_count = Column(Integer, default=0)
    last_error = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    camera = relationship("Camera", back_populates="sessions")

    def __repr__(self):
        return f"<CameraSession(id={self.id}, camera_id={self.camera_id}, session_id='{self.session_id}', active={self.is_active})>"


class CameraCapability(Base):
    """Camera capability model for storing detailed camera features."""

    __tablename__ = "camera_capabilities"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)

    # Video capabilities
    min_resolution_width = Column(Integer)
    min_resolution_height = Column(Integer)
    max_resolution_width = Column(Integer)
    max_resolution_height = Column(Integer)
    supported_resolutions = Column(JSON)  # List of [width, height] pairs

    # Frame rate capabilities
    min_fps = Column(Integer)
    max_fps = Column(Integer)
    supported_fps_rates = Column(JSON)  # List of supported FPS values

    # Format capabilities
    supported_video_codecs = Column(JSON)  # H.264, H.265, MJPEG, etc.
    supported_audio_codecs = Column(JSON)  # AAC, MP3, etc.
    supported_containers = Column(JSON)  # MP4, AVI, MKV, etc.

    # Advanced features
    auto_focus = Column(Boolean, default=False)
    auto_exposure = Column(Boolean, default=False)
    auto_white_balance = Column(Boolean, default=False)
    digital_zoom = Column(Boolean, default=False)
    image_stabilization = Column(Boolean, default=False)

    # PTZ capabilities (if supported)
    pan_range_degrees = Column(Float)
    tilt_range_degrees = Column(Float)
    zoom_range = Column(Float)
    preset_positions = Column(Integer, default=0)

    # Network capabilities (for IP cameras)
    supports_https = Column(Boolean, default=False)
    supports_onvif = Column(Boolean, default=False)
    supports_rtsp = Column(Boolean, default=False)
    supports_rtmp = Column(Boolean, default=False)

    # Power and environmental
    power_consumption_watts = Column(Float)
    operating_temperature_min = Column(Float)
    operating_temperature_max = Column(Float)
    night_vision = Column(Boolean, default=False)
    infrared_range_meters = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    camera = relationship("Camera", back_populates="capabilities")

    def __repr__(self):
        return f"<CameraCapability(id={self.id}, camera_id={self.camera_id})>"

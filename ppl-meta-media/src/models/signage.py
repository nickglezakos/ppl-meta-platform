"""
Signage Simple Player Models

This module defines the database models for managing video lists, synchronization,
and playback control for the Signage Simple Player microservice in the PPL Meta Platform.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel


class LoopMode(str, Enum):
    """Video list loop modes."""

    CONTINUOUS = "continuous"  # Loop continuously
    ONCE = "once"  # Play once then stop
    SHUFFLE = "shuffle"  # Random order with loop
    REPEAT_ONE = "repeat_one"  # Repeat current video


class SyncStatus(str, Enum):
    """Video list synchronization status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class PlaybackCommand(str, Enum):
    """Remote playback control commands."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    SEEK = "seek"


class VideoList(BaseModel):
    """
    Video list for digital signage playback.

    A video list aggregates videos from multiple user collections into a single playlist
    that can be synced to signage devices for playback.
    """

    __tablename__ = "video_lists"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Basic information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Ownership
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Playback configuration
    loop_mode = Column(String(50), default=LoopMode.CONTINUOUS.value, nullable=False)
    transition_duration = Column(
        Integer, default=0, nullable=False
    )  # milliseconds between videos

    # Status flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_published = Column(
        Boolean, default=False, nullable=False
    )  # Ready for distribution

    # Metadata
    total_duration_ms = Column(Integer, default=0)  # Cached total duration
    video_count = Column(Integer, default=0)  # Cached video count
    last_modified_by = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    video_items = relationship(
        "VideoListItem",
        back_populates="video_list",
        cascade="all, delete-orphan",
        order_by="VideoListItem.sequence_order",
    )
    sync_history = relationship(
        "VideoListSyncHistory",
        back_populates="video_list",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<VideoList(uuid={self.uuid}, name='{self.name}', videos={self.video_count})>"

    @property
    def total_duration_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.total_duration_ms / 1000 if self.total_duration_ms else 0

    def update_cached_stats(self):
        """Update cached statistics (video_count, total_duration_ms)."""
        self.video_count = len(self.video_items)
        self.total_duration_ms = sum(
            item.duration_ms or 0 for item in self.video_items
        )


class VideoListItem(BaseModel):
    """
    Individual video item within a video list.

    References videos from media collections with sequence ordering and optional overrides.
    """

    __tablename__ = "video_list_items"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # References
    video_list_id = Column(
        Integer, ForeignKey("video_lists.id", ondelete="CASCADE"), nullable=False
    )
    collection_id = Column(
        Integer, ForeignKey("media_collections.id"), nullable=False
    )
    video_id = Column(Integer, ForeignKey("media.id"), nullable=False)

    # Ordering
    sequence_order = Column(Integer, nullable=False)

    # Optional overrides
    duration_override = Column(
        Integer, nullable=True
    )  # Override duration in milliseconds
    title_override = Column(String(255), nullable=True)  # Custom title for this list
    transition_override = Column(
        Integer, nullable=True
    )  # Override transition duration

    # Cached metadata (for performance)
    video_filename = Column(String(255), nullable=True)
    video_file_path = Column(String(500), nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Original duration from media
    thumbnail_url = Column(String(500), nullable=True)

    # Status
    is_available = Column(
        Boolean, default=True, nullable=False
    )  # False if video deleted

    # Relationships
    video_list = relationship("VideoList", back_populates="video_items")
    collection = relationship("MediaCollection")
    media = relationship("Media")

    def __repr__(self):
        return f"<VideoListItem(uuid={self.uuid}, list={self.video_list_id}, seq={self.sequence_order})>"

    @property
    def effective_duration_ms(self) -> int:
        """Get the effective duration (override or original)."""
        return self.duration_override if self.duration_override else (self.duration_ms or 0)

    @property
    def effective_title(self) -> str:
        """Get the effective title (override or original)."""
        if self.title_override:
            return self.title_override
        if self.media:
            return self.media.title or self.media.original_filename
        return self.video_filename or "Unknown"


class VideoListSyncHistory(BaseModel):
    """
    History of video list synchronizations to signage devices.

    Tracks each sync operation for auditing and troubleshooting.
    """

    __tablename__ = "video_list_sync_history"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # References
    video_list_id = Column(
        Integer, ForeignKey("video_lists.id", ondelete="CASCADE"), nullable=False
    )
    signage_device_id = Column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # Reference to signage device

    # Sync details
    sync_status = Column(String(50), nullable=False, default=SyncStatus.PENDING.value)
    sync_mode = Column(String(20), nullable=False)  # "full" or "incremental"

    # Statistics
    videos_synced = Column(Integer, default=0)
    videos_failed = Column(Integer, default=0)
    total_videos = Column(Integer, nullable=True)
    data_transferred_bytes = Column(Integer, default=0)

    # Timing
    sync_started_at = Column(DateTime(timezone=True), nullable=True)
    sync_completed_at = Column(DateTime(timezone=True), nullable=True)
    sync_duration_ms = Column(Integer, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)

    # Metadata
    initiated_by = Column(UUID(as_uuid=True), nullable=True)  # User who triggered sync
    device_ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    device_hostname = Column(String(255), nullable=True)

    # Relationships
    video_list = relationship("VideoList", back_populates="sync_history")

    def __repr__(self):
        return f"<VideoListSyncHistory(uuid={self.uuid}, status={self.sync_status}, device={self.signage_device_id})>"

    @property
    def sync_duration_seconds(self) -> float:
        """Get sync duration in seconds."""
        return self.sync_duration_ms / 1000 if self.sync_duration_ms else 0

    @property
    def success_rate(self) -> float:
        """Calculate sync success rate percentage."""
        if not self.total_videos or self.total_videos == 0:
            return 0.0
        return (self.videos_synced / self.total_videos) * 100

    def mark_started(self):
        """Mark sync as started."""
        self.sync_status = SyncStatus.IN_PROGRESS.value
        self.sync_started_at = datetime.now(timezone.utc)

    def mark_completed(self, videos_synced: int, videos_failed: int = 0):
        """Mark sync as completed with statistics."""
        self.sync_status = (
            SyncStatus.COMPLETED.value
            if videos_failed == 0
            else SyncStatus.PARTIAL.value
        )
        self.videos_synced = videos_synced
        self.videos_failed = videos_failed
        self.sync_completed_at = datetime.now(timezone.utc)

        if self.sync_started_at:
            duration = (self.sync_completed_at - self.sync_started_at).total_seconds()
            self.sync_duration_ms = int(duration * 1000)

    def mark_failed(self, error_message: str, error_details: str = None):
        """Mark sync as failed with error information."""
        self.sync_status = SyncStatus.FAILED.value
        self.error_message = error_message
        self.error_details = error_details
        self.sync_completed_at = datetime.now(timezone.utc)

        if self.sync_started_at:
            duration = (self.sync_completed_at - self.sync_started_at).total_seconds()
            self.sync_duration_ms = int(duration * 1000)


class SignageDevice(BaseModel):
    """
    Registered signage device information.

    Tracks devices that can receive video lists and playback commands.
    Note: This is a reference table; actual device registration happens via discovery service.
    """

    __tablename__ = "signage_devices"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Device identification
    device_id = Column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )  # From discovery service
    device_name = Column(String(255), nullable=False)
    device_hostname = Column(String(255), nullable=True)

    # Network information
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    mac_address = Column(String(17), nullable=True)

    # Device characteristics
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    android_version = Column(String(50), nullable=True)
    screen_resolution = Column(String(20), nullable=True)  # "1920x1080"
    screen_size_inches = Column(Integer, nullable=True)

    # Software information
    app_version = Column(String(50), nullable=True)
    last_app_update = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_online = Column(Boolean, default=False, nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    # Current playback
    current_video_list_id = Column(
        Integer, ForeignKey("video_lists.id", ondelete="SET NULL"), nullable=True
    )
    playback_state = Column(
        String(20), nullable=True
    )  # "playing", "paused", "stopped"

    # Ownership
    registered_by = Column(UUID(as_uuid=True), nullable=True)  # User who registered
    organization_id = Column(UUID(as_uuid=True), nullable=True)  # For multi-tenant

    # Capabilities
    supports_hd = Column(Boolean, default=True)
    supports_4k = Column(Boolean, default=False)
    max_storage_gb = Column(Integer, default=10)

    # Metadata
    notes = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)  # Physical location
    tags = Column(Text, nullable=True)  # JSON array of tags

    # Relationships
    current_video_list = relationship("VideoList", foreign_keys=[current_video_list_id])

    def __repr__(self):
        return f"<SignageDevice(uuid={self.uuid}, name='{self.device_name}', online={self.is_online})>"

    def update_heartbeat(self):
        """Update the device heartbeat timestamp."""
        now = datetime.now(timezone.utc)
        self.last_heartbeat = now
        self.last_seen = now
        self.is_online = True

    def mark_offline(self):
        """Mark device as offline."""
        self.is_online = False

    @property
    def is_healthy(self) -> bool:
        """Check if device is considered healthy (online and recent heartbeat)."""
        if not self.is_online or not self.last_heartbeat:
            return False

        # Consider unhealthy if no heartbeat in last 2 minutes
        time_since_heartbeat = datetime.now(timezone.utc) - self.last_heartbeat
        return time_since_heartbeat.total_seconds() < 120

"""
Signage Simple Player Pydantic Schemas

Request/Response schemas for video list management, synchronization, and playback control.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums
# ============================================================================


class LoopMode(str, Enum):
    """Video list loop modes."""

    CONTINUOUS = "continuous"
    ONCE = "once"
    SHUFFLE = "shuffle"
    REPEAT_ONE = "repeat_one"


class SyncMode(str, Enum):
    """Synchronization modes."""

    FULL = "full"
    INCREMENTAL = "incremental"


class SyncStatus(str, Enum):
    """Sync operation status."""

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
    SHOW_RICH_MESSAGE = "show_rich_message"
    DISMISS_RICH_MESSAGE = "dismiss_rich_message"


class RichMessageLayout(str, Enum):
    """Rich message overlay layout."""

    FULLSCREEN = "fullscreen"
    BANNER = "banner"
    CARD = "card"


class PlaybackState(str, Enum):
    """Playback state."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    LOADING = "loading"
    BUFFERING = "buffering"
    ERROR = "error"


# ============================================================================
# Video List Item Schemas
# ============================================================================


class VideoListItemBase(BaseModel):
    """Base schema for video list items."""

    collection_id: int = Field(..., description="Collection ID containing the video")
    video_id: int = Field(..., description="Video (media) ID")
    sequence_order: int = Field(..., description="Order in the playlist", ge=0)
    duration_override: Optional[int] = Field(
        None, description="Override duration in milliseconds", ge=0
    )
    title_override: Optional[str] = Field(
        None, max_length=255, description="Custom title for this video in the list"
    )
    transition_override: Optional[int] = Field(
        None, description="Override transition duration in milliseconds", ge=0
    )


class VideoListItemCreate(VideoListItemBase):
    """Schema for creating a video list item."""

    pass


class VideoListItemUpdate(BaseModel):
    """Schema for updating a video list item."""

    sequence_order: Optional[int] = Field(None, ge=0)
    duration_override: Optional[int] = Field(None, ge=0)
    title_override: Optional[str] = Field(None, max_length=255)
    transition_override: Optional[int] = Field(None, ge=0)


class VideoListItemResponse(VideoListItemBase):
    """Schema for video list item response."""

    id: int
    uuid: UUID
    video_list_id: int
    video_filename: Optional[str]
    video_title: Optional[str]
    video_file_path: Optional[str]
    duration_ms: Optional[int]
    thumbnail_url: Optional[str]
    is_available: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Video List Schemas
# ============================================================================


class VideoListBase(BaseModel):
    """Base schema for video lists."""

    name: str = Field(..., min_length=1, max_length=255, description="Video list name")
    description: Optional[str] = Field(None, description="Video list description")
    loop_mode: LoopMode = Field(
        default=LoopMode.CONTINUOUS, description="Playback loop mode"
    )
    transition_duration: int = Field(
        default=0, description="Transition duration in milliseconds", ge=0
    )


class VideoListCreate(VideoListBase):
    """Schema for creating a video list."""

    collection_ids: List[str] = Field(
        ..., description="List of collection UUIDs to include videos from", min_items=1
    )
    video_order: Optional[List[dict]] = Field(
        None,
        description='Manual video order: [{"collection_id": "uuid", "video_id": "uuid", "sequence": 1}]',
    )


class VideoListUpdate(BaseModel):
    """Schema for updating a video list."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    loop_mode: Optional[LoopMode] = None
    transition_duration: Optional[int] = Field(None, ge=0)
    video_order: Optional[List[dict]] = Field(
        None,
        description='Manual video order: [{"collection_id": "uuid", "video_id": "uuid", "sequence": 1}]',
    )
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None


class VideoListResponse(VideoListBase):
    """Schema for video list response."""

    id: int
    uuid: UUID
    user_id: UUID
    is_active: bool
    is_published: bool
    total_duration_ms: int
    video_count: int
    last_modified_by: Optional[UUID]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class VideoListDetailResponse(VideoListResponse):
    """Detailed video list response with items."""

    video_items: List[VideoListItemResponse] = []
    # Collection UUIDs whose videos are aggregated into this playlist.
    # Populated by the detail endpoint from the video items' collections
    # (the VideoList entity itself does not store collection_ids).
    collection_ids: List[str] = []

    class Config:
        from_attributes = True


class VideoListSummary(BaseModel):
    """Summary info for video list."""

    id: int
    uuid: UUID
    name: str
    video_count: int
    total_duration_ms: int
    is_active: bool
    is_published: bool
    last_synced_at: Optional[datetime]
    created_at: datetime


class VideoListListResponse(BaseModel):
    """Paginated list of video lists."""

    total_count: int
    page: int
    page_size: int
    results: List[VideoListSummary]


# ============================================================================
# Sync Schemas
# ============================================================================


class SyncRequest(BaseModel):
    """Request to sync a video list to device(s)."""

    video_list_id: UUID = Field(..., description="Video list UUID to sync")
    target_devices: List[UUID] = Field(
        ..., description="List of signage device UUIDs", min_items=1
    )
    sync_mode: SyncMode = Field(
        default=SyncMode.INCREMENTAL, description="Sync mode: full or incremental"
    )
    force_update: bool = Field(
        default=False, description="Force re-sync even if up-to-date"
    )
    notify_on_complete: bool = Field(
        default=True, description="Send notification when sync completes"
    )


class SyncResponse(BaseModel):
    """Response for sync operation."""

    sync_job_id: UUID
    status: SyncStatus
    target_device_count: int
    estimated_completion_at: Optional[datetime]
    message: str


class SyncResult(BaseModel):
    """Result of a sync operation."""

    sync_id: UUID
    video_list_id: UUID
    device_id: UUID
    status: SyncStatus
    videos_synced: int
    videos_failed: int
    sync_duration_ms: int
    error_message: Optional[str]
    next_sync_recommended_at: Optional[datetime]


class VideoListSyncHistoryResponse(BaseModel):
    """Schema for sync history response."""

    id: int
    uuid: UUID
    video_list_id: int
    signage_device_id: UUID
    sync_status: SyncStatus
    sync_mode: str
    videos_synced: int
    videos_failed: int
    videos_skipped: int
    total_videos: Optional[int]
    data_transferred_bytes: int
    sync_started_at: Optional[datetime]
    sync_completed_at: Optional[datetime]
    sync_duration_ms: Optional[int]
    error_message: Optional[str]
    initiated_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class SyncHistoryListResponse(BaseModel):
    """Paginated sync history."""

    total_count: int
    page: int
    page_size: int
    results: List[VideoListSyncHistoryResponse]


# ============================================================================
# Playback Control Schemas
# ============================================================================


class PlaybackParameters(BaseModel):
    """Playback control parameters."""

    start_index: int = Field(default=0, description="Start from video index", ge=0)
    volume: int = Field(default=80, description="Volume level (0-100)", ge=0, le=100)
    speed: float = Field(default=1.0, description="Playback speed", ge=0.1, le=3.0)


class RichMessageOverlayPayload(BaseModel):
    """Resolved overlay payload sent to the player."""

    template_id: UUID
    title: str = ""
    message: Optional[str] = None
    html_body: str
    media_url: Optional[str] = None
    sound_url: Optional[str] = None
    title_font_size: int = 48
    message_font_size: int = 28
    title_color: str = "#FFFFFF"
    message_color: str = "#F0F0F0"
    background_color: str = "#000000"
    opacity: int = 80
    layout: str = "card"
    duration_ms: int = 15000


class PlaybackControlRequest(BaseModel):
    """Request to control playback on device(s)."""

    device_ids: List[UUID] = Field(
        ..., description="List of signage device UUIDs", min_items=1
    )
    command: PlaybackCommand = Field(..., description="Playback command")
    video_list_id: Optional[UUID] = Field(
        None, description="Video list UUID (required for START command)"
    )
    parameters: Optional[PlaybackParameters] = Field(
        None, description="Additional playback parameters"
    )
    rich_message: Optional[RichMessageOverlayPayload] = Field(
        None,
        description="Resolved rich message overlay payload (for show_rich_message)",
    )

    @validator("video_list_id")
    def validate_video_list_for_start(cls, v, values):
        """Ensure video_list_id is provided for START command."""
        if values.get("command") == PlaybackCommand.START and not v:
            raise ValueError("video_list_id is required for START command")
        return v

    @validator("rich_message")
    def validate_rich_message_for_show(cls, v, values):
        """Ensure rich_message is provided for SHOW_RICH_MESSAGE command."""
        if values.get("command") == PlaybackCommand.SHOW_RICH_MESSAGE and not v:
            raise ValueError("rich_message is required for show_rich_message command")
        return v


class PlaybackControlResponse(BaseModel):
    """Response for playback control operation."""

    command_id: UUID
    status: str
    affected_devices: int
    executed_at: datetime
    message: str


# ============================================================================
# Rich Message Template Schemas
# ============================================================================


class RichMessageTemplateBase(BaseModel):
    """Base schema for rich message templates."""

    name: str = Field(..., min_length=1, max_length=255)
    title: str = Field(default="", max_length=255)
    message: Optional[str] = None
    title_font_size: int = Field(default=48, ge=8, le=200)
    message_font_size: int = Field(default=28, ge=8, le=200)
    title_color: str = Field(default="#FFFFFF", max_length=32)
    message_color: str = Field(default="#F0F0F0", max_length=32)
    background_color: str = Field(default="#000000", max_length=32)
    opacity: int = Field(default=80, ge=0, le=100)
    layout: RichMessageLayout = Field(default=RichMessageLayout.CARD)
    media_uuid: Optional[UUID] = Field(
        None, description="Optional media UUID for video/image container"
    )
    sound_media_uuid: Optional[UUID] = Field(
        None, description="Optional sound media UUID"
    )
    default_duration_ms: int = Field(default=15000, ge=500, le=600000)


class RichMessageTemplateCreate(RichMessageTemplateBase):
    """Schema for creating a rich message template."""

    pass


class RichMessageTemplateUpdate(BaseModel):
    """Schema for updating a rich message template."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = None
    title_font_size: Optional[int] = Field(None, ge=8, le=200)
    message_font_size: Optional[int] = Field(None, ge=8, le=200)
    title_color: Optional[str] = Field(None, max_length=32)
    message_color: Optional[str] = Field(None, max_length=32)
    background_color: Optional[str] = Field(None, max_length=32)
    opacity: Optional[int] = Field(None, ge=0, le=100)
    layout: Optional[RichMessageLayout] = None
    media_uuid: Optional[UUID] = None
    sound_media_uuid: Optional[UUID] = None
    clear_media: bool = Field(default=False, description="Clear media_id when true")
    clear_sound: bool = Field(
        default=False, description="Clear sound_media_id when true"
    )
    default_duration_ms: Optional[int] = Field(None, ge=500, le=600000)
    is_active: Optional[bool] = None


class RichMessageTemplateResponse(BaseModel):
    """Schema for rich message template response."""

    id: int
    uuid: UUID
    name: str
    title: str
    message: Optional[str]
    html_body: Optional[str]
    title_font_size: int
    message_font_size: int
    title_color: str
    message_color: str
    background_color: str
    opacity: int
    layout: str
    media_id: Optional[int]
    media_uuid: Optional[UUID] = None
    sound_media_id: Optional[int]
    sound_media_uuid: Optional[UUID] = None
    default_duration_ms: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RichMessageTemplateListResponse(BaseModel):
    """Paginated list of rich message templates."""

    total_count: int
    page: int
    page_size: int
    results: List[RichMessageTemplateResponse]


# ============================================================================
# Signage Device Schemas
# ============================================================================


class SignageDeviceBase(BaseModel):
    """Base schema for signage devices."""

    device_name: str = Field(..., max_length=255)
    device_hostname: Optional[str] = Field(None, max_length=255)
    ip_address: Optional[str] = Field(None, max_length=45)
    port: Optional[int] = Field(None, ge=1, le=65535)
    location: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class SignageDeviceRegister(SignageDeviceBase):
    """Schema for registering a new signage device."""

    device_id: UUID = Field(..., description="Unique device identifier from discovery")
    mac_address: Optional[str] = Field(None, max_length=17)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    android_version: Optional[str] = Field(None, max_length=50)
    screen_resolution: Optional[str] = Field(None, max_length=20)
    app_version: Optional[str] = Field(None, max_length=50)
    max_storage_gb: int = Field(default=10, ge=1)


class SignageDeviceUpdate(BaseModel):
    """Schema for updating signage device info."""

    device_name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SignageDeviceResponse(SignageDeviceBase):
    """Schema for signage device response."""

    id: int
    uuid: UUID
    device_id: UUID
    is_active: bool
    is_online: bool
    last_seen: Optional[datetime]
    last_heartbeat: Optional[datetime]
    current_video_list_id: Optional[int]
    playback_state: Optional[PlaybackState]
    app_version: Optional[str]
    screen_resolution: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SignageDeviceListResponse(BaseModel):
    """Paginated list of signage devices."""

    total_count: int
    page: int
    page_size: int
    results: List[SignageDeviceResponse]


# ============================================================================
# Utility Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str
    data: Optional[dict] = None

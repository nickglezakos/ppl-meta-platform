"""
Pydantic schemas for Media API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import UUID4, BaseModel, ConfigDict, Field


class MediaType(str, Enum):
    """Supported media types."""

    VIDEO = "video"
    PICTURE = "picture"
    SOUND = "sound"
    STREAMING = "streaming"
    DOCUMENT = "document"


class ProcessingStatus(str, Enum):
    """Media processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class StorageProvider(str, Enum):
    """Storage backend providers."""

    LOCAL = "local"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"


# Base schemas
class MediaBase(BaseModel):
    """Base media schema with common fields."""

    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    categories: Optional[List[str]] = Field(default_factory=list)
    is_public: bool = Field(default=False)

    # Device information (optional)
    device_name: Optional[str] = Field(None, max_length=255)
    device_model: Optional[str] = Field(None, max_length=100)
    device_manufacturer: Optional[str] = Field(None, max_length=100)
    device_os: Optional[str] = Field(None, max_length=50)
    app_name: Optional[str] = Field(None, max_length=100)
    app_version: Optional[str] = Field(None, max_length=50)

    # Location and context
    location_data: Optional[Dict[str, Any]] = None
    capture_timestamp: Optional[datetime] = None


class MediaDetailsBase(BaseModel):
    """Base media details schema."""

    # Video-specific fields
    duration: Optional[float] = Field(None, description="Duration in seconds")
    width: Optional[int] = Field(None, ge=1, le=7680)
    height: Optional[int] = Field(None, ge=1, le=4320)
    frame_rate: Optional[float] = Field(None, ge=0.1, le=120.0)
    bitrate: Optional[int] = Field(None, ge=1)
    codec: Optional[str] = Field(None, max_length=50)

    # Audio-specific fields
    audio_channels: Optional[int] = Field(None, ge=1, le=32)
    audio_sample_rate: Optional[int] = Field(None, ge=8000, le=192000)
    audio_bitrate: Optional[int] = Field(None, ge=1)
    audio_codec: Optional[str] = Field(None, max_length=50)

    # Image-specific fields
    color_space: Optional[str] = Field(None, max_length=20)
    dpi: Optional[int] = Field(None, ge=1, le=2400)
    has_transparency: Optional[bool] = None

    # Streaming-specific fields
    stream_type: Optional[str] = Field(None, max_length=20)
    stream_protocol: Optional[str] = Field(None, max_length=20)
    manifest_url: Optional[str] = Field(None, max_length=500)

    # Document-specific fields
    page_count: Optional[int] = Field(None, ge=1)
    word_count: Optional[int] = Field(None, ge=0)
    language: Optional[str] = Field(None, max_length=10)


class MediaVariantBase(BaseModel):
    """Base media variant schema."""

    variant_type: str = Field(..., max_length=50)
    filename: str = Field(..., max_length=255)
    file_size: int = Field(..., ge=1)
    mime_type: str = Field(..., max_length=100)
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    quality: Optional[str] = Field(None, max_length=20)


# Request schemas
class MediaUploadRequest(MediaBase):
    """Schema for media upload requests."""

    model_config = ConfigDict(extra="forbid")

    # File info will be handled by FastAPI's UploadFile
    # These fields are for additional metadata
    media_type: MediaType
    user_id: Optional[UUID4] = None  # User who is uploading
    technical_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MediaUpdateRequest(BaseModel):
    """Schema for updating media metadata."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_archived: Optional[bool] = None


class MediaDetailsUpdateRequest(MediaDetailsBase):
    """Schema for updating media technical details."""

    model_config = ConfigDict(extra="forbid")


class MediaSearchRequest(BaseModel):
    """Schema for media search requests."""

    model_config = ConfigDict(extra="forbid")

    query: Optional[str] = Field(None, max_length=500)
    media_types: Optional[List[MediaType]] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    uploaded_by: Optional[UUID4] = None
    is_public: Optional[bool] = None
    is_archived: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    # Sorting
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# Response schemas
class MediaVariantResponse(MediaVariantBase):
    """Schema for media variant responses."""

    id: int
    media_id: int
    file_path: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MediaDetailsResponse(MediaDetailsBase):
    """Schema for media details responses."""

    id: int
    media_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MediaResponse(MediaBase):
    """Schema for basic media responses."""

    id: int
    uuid: UUID4
    filename: str
    original_filename: str
    media_type: MediaType
    mime_type: str
    file_extension: str
    file_size: int
    file_path: str
    storage_provider: StorageProvider
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    uploaded_by: UUID4
    technical_metadata: Optional[Dict[str, Any]] = None
    access_permissions: Optional[Dict[str, Any]] = None
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MediaDetailedResponse(MediaResponse):
    """Schema for detailed media responses with relationships."""

    media_details: Optional[MediaDetailsResponse] = None
    media_variants: List[MediaVariantResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MediaListResponse(BaseModel):
    """Schema for paginated media list responses."""

    items: List[MediaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    model_config = ConfigDict(from_attributes=True)


# Collection schemas
class MediaCollectionBase(BaseModel):
    """Base media collection schema."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_public: bool = Field(default=False)
    tags: Optional[List[str]] = Field(default_factory=list)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MediaCollectionCreateRequest(MediaCollectionBase):
    """Schema for creating media collections."""

    model_config = ConfigDict(extra="forbid")


class MediaCollectionUpdateRequest(BaseModel):
    """Schema for updating media collections."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    cover_media_id: Optional[int] = None


class MediaCollectionResponse(MediaCollectionBase):
    """Schema for media collection responses."""

    id: int
    uuid: UUID4
    created_by: UUID4
    cover_media_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MediaCollectionItemRequest(BaseModel):
    """Schema for adding media to collections."""

    model_config = ConfigDict(extra="forbid")

    media_id: int = Field(..., ge=1)
    sort_order: int = Field(default=0)
    notes: Optional[str] = None


class MediaCollectionItemResponse(BaseModel):
    """Schema for collection item responses."""

    id: int
    collection_id: int
    media_id: int
    sort_order: int
    added_by: UUID4
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Share schemas
class MediaShareCreateRequest(BaseModel):
    """Schema for creating media shares."""

    model_config = ConfigDict(extra="forbid")

    media_id: int = Field(..., ge=1)
    shared_with: Optional[UUID4] = None  # None for public links
    can_view: bool = Field(default=True)
    can_download: bool = Field(default=False)
    can_share: bool = Field(default=False)
    expires_at: Optional[datetime] = None
    max_views: Optional[int] = Field(None, ge=1)


class MediaShareResponse(BaseModel):
    """Schema for media share responses."""

    id: int
    uuid: UUID4
    media_id: int
    shared_by: UUID4
    shared_with: Optional[UUID4] = None
    share_token: str
    can_view: bool
    can_download: bool
    can_share: bool
    expires_at: Optional[datetime] = None
    max_views: Optional[int] = None
    view_count: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Error schemas
class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidationErrorResponse(BaseModel):
    """Schema for validation error responses."""

    error: str = "validation_error"
    message: str
    errors: List[Dict[str, Any]]


# Upload response schemas
class MediaUploadResponse(BaseModel):
    """Schema for successful upload responses."""

    message: str
    media: MediaResponse
    upload_info: Dict[str, Any] = Field(default_factory=dict)


class ProcessingStatusResponse(BaseModel):
    """Schema for processing status responses."""

    media_uuid: UUID4
    processing_status: ProcessingStatus
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

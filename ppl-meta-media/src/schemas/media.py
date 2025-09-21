"""
Pydantic schemas for Media API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

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
    media_type: Optional[MediaType] = None  # Will be determined by service
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
    # Filter by specific collection (deprecated - use collection_ids)
    collection_id: Optional[str] = None
    # Filter by multiple collections
    collection_ids: Optional[List[str]] = None

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
    uploaded_by: UUID
    technical_metadata: Optional[Dict[str, Any]] = None
    access_permissions: Optional[Dict[str, Any]] = None
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    url: Optional[str] = None
    collections: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

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


class VideoFrameResponse(BaseModel):
    """Schema for video frame extraction responses."""

    media_id: UUID4
    frame_number: int
    frame_timestamp: float = Field(..., description="Timestamp in seconds")
    format: str = Field(default="jpeg", description="Output image format")
    width: int = Field(..., description="Frame width in pixels")
    height: int = Field(..., description="Frame height in pixels")
    file_size: int = Field(..., description="Size of extracted frame in bytes")
    total_frames: Optional[int] = Field(None, description="Total frames in video")
    video_duration: Optional[float] = Field(
        None, description="Video duration in seconds"
    )

    model_config = ConfigDict(from_attributes=True)


# Collection schemas
class MediaCollectionBase(BaseModel):
    """Base media collection schema."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_public: bool = Field(default=False)
    tags: Optional[List[str]] = Field(default_factory=list)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    camera_device_id: Optional[str] = Field(None, max_length=255)


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
    camera_device_id: Optional[str] = Field(None, max_length=255)


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


# Issue #013: Complete Media CRUD Operations - New Schemas
class MediaMetadataUpdateRequest(BaseModel):
    """Schema for metadata-only updates."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class MediaPrivacyUpdateRequest(BaseModel):
    """Schema for privacy settings updates."""

    model_config = ConfigDict(extra="forbid")

    is_public: bool


class MediaLocationUpdateRequest(BaseModel):
    """Schema for GPS/location data updates."""

    model_config = ConfigDict(extra="forbid")

    location_data: Optional[Dict[str, Any]] = None
    capture_timestamp: Optional[datetime] = None


class BulkMediaRequest(BaseModel):
    """Schema for bulk media operations."""

    model_config = ConfigDict(extra="forbid")

    media_ids: List[str] = Field(..., description="List of media IDs (max 100)")

    @classmethod
    def validate_media_ids(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 media IDs allowed per bulk operation")
        if len(v) < 1:
            raise ValueError("At least 1 media ID required")
        return v

    user_id: UUID4


class BulkMediaUpdateRequest(BulkMediaRequest):
    """Schema for bulk metadata updates."""

    updates: MediaMetadataUpdateRequest


class BulkPrivacyUpdateRequest(BulkMediaRequest):
    """Schema for bulk privacy updates."""

    is_public: bool


class MediaReplaceRequest(BaseModel):
    """Schema for media file replacement."""

    model_config = ConfigDict(extra="forbid")

    preserve_metadata: bool = True
    update_timestamp: bool = False


class MediaDuplicateRequest(BaseModel):
    """Schema for media duplication."""

    model_config = ConfigDict(extra="forbid")

    new_title: Optional[str] = None
    new_description: Optional[str] = None
    new_tags: Optional[List[str]] = None
    copy_privacy_settings: bool = True


class MediaMoveRequest(BaseModel):
    """Schema for moving media between storage locations."""

    model_config = ConfigDict(extra="forbid")

    target_storage_provider: StorageProvider
    target_path: Optional[str] = None


class MediaArchiveRequest(BaseModel):
    """Schema for archiving media."""

    model_config = ConfigDict(extra="forbid")

    archive_reason: Optional[str] = None
    soft_delete: bool = True


# Bulk operation response schemas
class BulkOperationResponse(BaseModel):
    """Schema for bulk operation responses."""

    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    processed_media_ids: List[str] = Field(default_factory=list)


class MediaVersionResponse(BaseModel):
    """Schema for media version responses."""

    version_id: str
    media_id: str
    filename: str
    file_size: int
    created_at: datetime
    is_active: bool
    version_number: int


class MediaAuditLogResponse(BaseModel):
    """Schema for media audit log responses."""

    id: int
    media_id: str
    user_id: UUID4
    action: str
    details: Dict[str, Any]
    timestamp: datetime


# Collection bulk operations and additional schemas
class CollectionSearchRequest(BaseModel):
    """Schema for searching collections."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=255)
    user_id: UUID4
    include_public: bool = Field(default=True)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class CollectionStatsResponse(BaseModel):
    """Schema for collection statistics."""

    item_count: int
    total_size: int
    size_formatted: str
    by_type: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BulkCollectionItemRequest(BaseModel):
    """Schema for bulk collection item operations."""

    model_config = ConfigDict(extra="forbid")

    media_ids: List[str] = Field(..., description="List of media IDs (max 100)")
    collection_id: str = Field(..., description="Target collection UUID")
    user_id: UUID4

    @classmethod
    def validate_media_ids(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 media IDs allowed per bulk operation")
        if len(v) < 1:
            raise ValueError("At least 1 media ID required")
        return v


class CollectionReorderRequest(BaseModel):
    """Schema for reordering collection items."""

    model_config = ConfigDict(extra="forbid")

    item_orders: List[Dict[str, int]] = Field(
        ..., description="List of {media_id: int, sort_order: int} mappings"
    )
    user_id: UUID4


class CollectionDuplicateRequest(BaseModel):
    """Schema for duplicating collections."""

    model_config = ConfigDict(extra="forbid")

    new_name: str = Field(..., max_length=255)
    new_description: Optional[str] = None
    copy_privacy_settings: bool = Field(default=True)
    copy_items: bool = Field(default=True)
    user_id: UUID4


class CollectionMergeRequest(BaseModel):
    """Schema for merging collections."""

    model_config = ConfigDict(extra="forbid")

    source_collection_ids: List[str] = Field(..., min_length=1, max_length=10)
    target_name: str = Field(..., max_length=255)
    target_description: Optional[str] = None
    delete_source_collections: bool = Field(default=False)
    user_id: UUID4


class CollectionExportRequest(BaseModel):
    """Schema for exporting collection metadata."""

    model_config = ConfigDict(extra="forbid")

    format: str = Field(default="json", pattern="^(json|csv|xml)$")
    include_media_metadata: bool = Field(default=True)
    include_file_paths: bool = Field(default=False)
    user_id: UUID4


class CollectionImportRequest(BaseModel):
    """Schema for importing items to collection."""

    model_config = ConfigDict(extra="forbid")

    import_data: Dict[str, Any] = Field(..., description="Import data structure")
    import_format: str = Field(default="json", pattern="^(json|csv|xml)$")
    merge_strategy: str = Field(default="append", pattern="^(append|replace|merge)$")
    user_id: UUID4


class CollectionShareRequest(BaseModel):
    """Schema for creating collection share links."""

    model_config = ConfigDict(extra="forbid")

    collection_id: str
    shared_with: Optional[UUID4] = None  # None for public links
    can_view: bool = Field(default=True)
    can_download: bool = Field(default=False)
    can_edit: bool = Field(default=False)
    expires_at: Optional[datetime] = None
    password: Optional[str] = None
    user_id: UUID4


class CollectionCollaboratorRequest(BaseModel):
    """Schema for adding collaborators to collections."""

    model_config = ConfigDict(extra="forbid")

    collection_id: str
    collaborator_id: UUID4
    permission_level: str = Field(default="viewer", pattern="^(viewer|editor|admin)$")
    user_id: UUID4  # The user making the request


class BulkCollectionOperationResponse(BaseModel):
    """Schema for bulk collection operation responses."""

    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    processed_collection_ids: List[str] = Field(default_factory=list)


# ============================================================================
# MEDIA VARIANTS SCHEMAS - Issue #015 Implementation
# ============================================================================


class VariantTypeEnum(str, Enum):
    """Supported variant types."""

    # Thumbnail variants
    THUMBNAIL_SMALL = "thumbnail_small"
    THUMBNAIL_MEDIUM = "thumbnail_medium"
    THUMBNAIL_LARGE = "thumbnail_large"

    # Quality variants
    COMPRESSED_LOW = "compressed_low"
    COMPRESSED_MEDIUM = "compressed_medium"
    COMPRESSED_HIGH = "compressed_high"

    # Format variants
    FORMAT_WEBP = "format_webp"
    FORMAT_AVIF = "format_avif"
    FORMAT_JPEG = "format_jpeg"
    FORMAT_PNG = "format_png"

    # Video variants
    VIDEO_PREVIEW = "video_preview"
    VIDEO_LOW_RES = "video_low_res"
    VIDEO_HIGH_RES = "video_high_res"

    # Audio variants
    AUDIO_PREVIEW = "audio_preview"
    AUDIO_COMPRESSED = "audio_compressed"


class QualityLevel(str, Enum):
    """Quality levels for variants."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ORIGINAL = "original"


class VariantCreateRequest(BaseModel):
    """Schema for creating media variants."""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., description="Path to the variant file")
    filename: str = Field(..., max_length=255)
    file_size: int = Field(..., ge=1)
    mime_type: str = Field(..., max_length=100)
    variant_type: VariantTypeEnum
    quality_level: Optional[QualityLevel] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class VariantGenerateRequest(BaseModel):
    """Schema for auto-generating standard variants."""

    model_config = ConfigDict(extra="forbid")

    variant_types: List[VariantTypeEnum] = Field(..., min_length=1, max_length=10)
    quality_levels: List[QualityLevel] = Field(
        default=[QualityLevel.MEDIUM], min_length=1
    )
    include_thumbnails: bool = Field(default=True)
    background_processing: bool = Field(default=True)


class VariantUpdateRequest(BaseModel):
    """Schema for updating variant metadata."""

    model_config = ConfigDict(extra="forbid")

    quality: Optional[QualityLevel] = None
    width: Optional[int] = Field(None, ge=1, le=8192)
    height: Optional[int] = Field(None, ge=1, le=8192)
    custom_metadata: Optional[Dict[str, Any]] = None


class VariantResponseDetailed(MediaVariantResponse):
    """Detailed variant response with additional metadata."""

    quality: Optional[str] = None
    generation_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    processing_status: Optional[str] = None
    error_message: Optional[str] = None


class VariantListResponse(BaseModel):
    """Response for variant listing."""

    media_id: int
    total_variants: int
    variants_by_type: Dict[str, int] = Field(default_factory=dict)
    variants: List[VariantResponseDetailed] = Field(default_factory=list)


class VariantTypesResponse(BaseModel):
    """Response for available variant types."""

    available_types: List[Dict[str, str]] = Field(default_factory=list)
    supported_formats: List[str] = Field(default_factory=list)
    quality_levels: List[str] = Field(default_factory=list)


class VariantBulkOperationRequest(BaseModel):
    """Schema for bulk variant operations."""

    model_config = ConfigDict(extra="forbid")

    media_ids: List[int] = Field(..., min_length=1, max_length=100)
    variant_types: List[VariantTypeEnum] = Field(..., min_length=1)
    quality_levels: List[QualityLevel] = Field(
        default=[QualityLevel.MEDIUM], min_length=1
    )
    background_processing: bool = Field(default=True)


class VariantBulkOperationResponse(BaseModel):
    """Response for bulk variant operations."""

    total_requested: int
    successful: int
    failed: int
    processing_in_background: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    task_ids: List[str] = Field(default_factory=list)


# Version Management Schemas
class MediaVersionCreateRequest(BaseModel):
    """Schema for creating new media versions."""

    model_config = ConfigDict(extra="forbid")

    version_name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    copy_variants: bool = Field(default=True)
    set_as_active: bool = Field(default=False)


class MediaVersionDetailedResponse(BaseModel):
    """Schema for detailed media version responses."""

    id: int
    media_id: int
    version_number: int
    version_name: str
    description: Optional[str] = None
    is_active: bool
    variant_count: int
    created_at: datetime
    created_by: UUID4

    model_config = ConfigDict(from_attributes=True)


class MediaVersionListResponse(BaseModel):
    """Response for version listing."""

    media_id: int
    total_versions: int
    active_version_id: int
    versions: List[MediaVersionDetailedResponse] = Field(default_factory=list)


class VariantResponse(MediaVariantResponse):
    """Basic variant response schema."""


class VariantStatisticsResponse(BaseModel):
    """Response for variant statistics."""

    media_id: int
    original_size: int
    total_variants: int
    variants_total_size: int
    size_formatted: str
    storage_efficiency: float
    variants_by_type: Dict[str, Dict[str, int]] = Field(default_factory=dict)


# ============================================================================
# ISSUE #016: Advanced Media Details and Metadata Management
# ============================================================================


class MetadataFieldType(str, Enum):
    """Types of metadata fields."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"
    URL = "url"


class MetadataCategory(str, Enum):
    """Categories of metadata."""

    TECHNICAL = "technical"
    DESCRIPTIVE = "descriptive"
    ADMINISTRATIVE = "administrative"
    CUSTOM = "custom"


class MetadataValidationRule(BaseModel):
    """Schema for metadata field validation rules."""

    model_config = ConfigDict(extra="forbid")

    required: bool = Field(default=False)
    min_length: Optional[int] = Field(None, ge=0)
    max_length: Optional[int] = Field(None, ge=1)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None


class MetadataFieldSchema(BaseModel):
    """Schema for defining metadata fields."""

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(..., max_length=100, pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    field_type: MetadataFieldType
    category: MetadataCategory
    display_name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    validation_rules: Optional[MetadataValidationRule] = None
    default_value: Optional[Any] = None


class MetadataTemplateBase(BaseModel):
    """Base schema for metadata templates."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    media_types: List[MediaType] = Field(..., min_length=1)
    is_system_template: bool = Field(default=False)
    fields: List[MetadataFieldSchema] = Field(..., min_length=1)


class MetadataTemplateCreateRequest(MetadataTemplateBase):
    """Schema for creating metadata templates."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID4


class MetadataTemplateUpdateRequest(BaseModel):
    """Schema for updating metadata templates."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    media_types: Optional[List[MediaType]] = None
    fields: Optional[List[MetadataFieldSchema]] = None
    user_id: UUID4


class MetadataTemplateResponse(MetadataTemplateBase):
    """Schema for metadata template responses."""

    id: int
    uuid: UUID4
    created_by: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None
    usage_count: int = Field(default=0)

    model_config = ConfigDict(from_attributes=True)


# Advanced MediaDetails Operations
class MediaDetailsCreateRequest(BaseModel):
    """Schema for creating comprehensive media details."""

    model_config = ConfigDict(extra="forbid")

    media_id: int
    technical_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Technical fields (from MediaDetailsBase)
    duration: Optional[float] = Field(None, description="Duration in seconds")
    width: Optional[int] = Field(None, ge=1, le=7680)
    height: Optional[int] = Field(None, ge=1, le=4320)
    frame_rate: Optional[float] = Field(None, ge=0.1, le=120.0)
    bitrate: Optional[int] = Field(None, ge=1)
    codec: Optional[str] = Field(None, max_length=50)
    audio_channels: Optional[int] = Field(None, ge=1, le=32)
    audio_sample_rate: Optional[int] = Field(None, ge=8000, le=192000)
    audio_bitrate: Optional[int] = Field(None, ge=1)
    audio_codec: Optional[str] = Field(None, max_length=50)
    color_space: Optional[str] = Field(None, max_length=20)
    dpi: Optional[int] = Field(None, ge=1, le=2400)
    has_transparency: Optional[bool] = None


class MediaDetailsCompleteUpdateRequest(BaseModel):
    """Schema for updating complete media details."""

    model_config = ConfigDict(extra="forbid")

    technical_metadata: Optional[Dict[str, Any]] = None
    user_metadata: Optional[Dict[str, Any]] = None

    # Technical fields (optional updates)
    duration: Optional[float] = Field(None, description="Duration in seconds")
    width: Optional[int] = Field(None, ge=1, le=7680)
    height: Optional[int] = Field(None, ge=1, le=4320)
    frame_rate: Optional[float] = Field(None, ge=0.1, le=120.0)
    bitrate: Optional[int] = Field(None, ge=1)
    codec: Optional[str] = Field(None, max_length=50)
    audio_channels: Optional[int] = Field(None, ge=1, le=32)
    audio_sample_rate: Optional[int] = Field(None, ge=8000, le=192000)
    audio_bitrate: Optional[int] = Field(None, ge=1)
    audio_codec: Optional[str] = Field(None, max_length=50)
    color_space: Optional[str] = Field(None, max_length=20)
    dpi: Optional[int] = Field(None, ge=1, le=2400)
    has_transparency: Optional[bool] = None


class TechnicalMetadataUpdateRequest(BaseModel):
    """Schema for updating technical metadata only."""

    model_config = ConfigDict(extra="forbid")

    technical_metadata: Dict[str, Any] = Field(
        ..., description="Technical metadata fields"
    )
    merge_strategy: str = Field(default="merge", pattern="^(merge|replace)$")


class UserMetadataUpdateRequest(BaseModel):
    """Schema for updating user metadata only."""

    model_config = ConfigDict(extra="forbid")

    user_metadata: Dict[str, Any] = Field(
        ..., description="User-defined metadata fields"
    )
    merge_strategy: str = Field(default="merge", pattern="^(merge|replace)$")


class CustomMetadataFieldRequest(BaseModel):
    """Schema for adding/updating custom metadata fields."""

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(..., max_length=100, pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    field_value: Any = Field(..., description="Field value (type depends on schema)")
    field_type: Optional[MetadataFieldType] = None
    validation_rules: Optional[MetadataValidationRule] = None


class CustomMetadataResponse(BaseModel):
    """Schema for custom metadata field responses."""

    field_name: str
    field_value: Any
    field_type: MetadataFieldType
    category: MetadataCategory
    last_updated: datetime
    updated_by: UUID4


class MetadataApplyTemplateRequest(BaseModel):
    """Schema for applying metadata templates to media."""

    model_config = ConfigDict(extra="forbid")

    template_id: int
    field_values: Dict[str, Any] = Field(default_factory=dict)
    merge_strategy: str = Field(default="merge", pattern="^(merge|replace|preserve)$")
    user_id: UUID4


class BulkMetadataUpdateRequest(BaseModel):
    """Schema for bulk metadata operations."""

    model_config = ConfigDict(extra="forbid")

    media_ids: List[str] = Field(..., min_length=1, max_length=100)
    metadata_updates: Dict[str, Any] = Field(
        ..., description="Metadata updates to apply"
    )
    update_type: str = Field(default="user", pattern="^(technical|user|both)$")
    merge_strategy: str = Field(default="merge", pattern="^(merge|replace)$")
    user_id: UUID4


class MetadataExportRequest(BaseModel):
    """Schema for exporting metadata."""

    model_config = ConfigDict(extra="forbid")

    media_ids: List[str] = Field(..., min_length=1, max_length=1000)
    export_format: str = Field(default="json", pattern="^(json|csv|xml)$")
    include_technical: bool = Field(default=True)
    include_user: bool = Field(default=True)
    include_system: bool = Field(default=False)
    user_id: UUID4


class MetadataImportRequest(BaseModel):
    """Schema for importing metadata."""

    model_config = ConfigDict(extra="forbid")

    import_data: Dict[str, Any] = Field(..., description="Metadata import data")
    import_format: str = Field(default="json", pattern="^(json|csv|xml)$")
    merge_strategy: str = Field(
        default="merge", pattern="^(merge|replace|skip_existing)$"
    )
    validate_fields: bool = Field(default=True)
    user_id: UUID4


class MetadataSearchRequest(BaseModel):
    """Schema for searching media by metadata."""

    model_config = ConfigDict(extra="forbid")

    search_criteria: Dict[str, Any] = Field(..., description="Metadata search criteria")
    search_type: str = Field(default="exact", pattern="^(exact|contains|range|exists)$")
    media_types: Optional[List[MediaType]] = None
    include_technical: bool = Field(default=True)
    include_user: bool = Field(default=True)
    user_id: UUID4

    # Pagination
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class MetadataAnalyticsRequest(BaseModel):
    """Schema for metadata analytics requests."""

    model_config = ConfigDict(extra="forbid")

    analysis_type: str = Field(
        default="summary", pattern="^(summary|field_usage|value_distribution|trends)$"
    )
    media_types: Optional[List[MediaType]] = None
    date_range: Optional[Dict[str, datetime]] = None
    field_filters: Optional[List[str]] = None
    user_id: UUID4


class MetadataValidationRequest(BaseModel):
    """Schema for metadata validation requests."""

    model_config = ConfigDict(extra="forbid")

    metadata: Dict[str, Any] = Field(..., description="Metadata to validate")
    schema_template_id: Optional[int] = None
    media_type: Optional[MediaType] = None
    validation_level: str = Field(default="strict", pattern="^(strict|lenient|custom)$")


# Response Schemas
class MediaDetailsDetailedResponse(MediaDetailsResponse):
    """Schema for detailed media details responses."""

    technical_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata_schema_id: Optional[int] = None
    last_metadata_update: Optional[datetime] = None
    metadata_version: int = Field(default=1)


class BulkMetadataOperationResponse(BaseModel):
    """Schema for bulk metadata operation responses."""

    total_requested: int
    successful: int
    failed: int
    skipped: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    processed_media_ids: List[str] = Field(default_factory=list)
    operation_summary: Dict[str, Any] = Field(default_factory=dict)


class MetadataSearchResponse(BaseModel):
    """Schema for metadata search responses."""

    items: List[MediaResponse] = Field(default_factory=list)
    total: int
    matching_criteria: Dict[str, Any]
    search_metadata: Dict[str, Any] = Field(default_factory=dict)
    skip: int
    limit: int
    has_next: bool


class MetadataAnalyticsResponse(BaseModel):
    """Schema for metadata analytics responses."""

    analysis_type: str
    summary_stats: Dict[str, Any] = Field(default_factory=dict)
    field_statistics: Dict[str, Any] = Field(default_factory=dict)
    value_distributions: Dict[str, Any] = Field(default_factory=dict)
    trends_data: Optional[Dict[str, Any]] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MetadataValidationResponse(BaseModel):
    """Schema for metadata validation responses."""

    is_valid: bool
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
    validation_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    field_validations: Dict[str, bool] = Field(default_factory=dict)
    schema_compliance: Dict[str, Any] = Field(default_factory=dict)


class MetadataExportResponse(BaseModel):
    """Schema for metadata export responses."""

    export_format: str
    total_records: int
    export_data: Any  # Can be dict, list, or string depending on format
    export_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MetadataImportResponse(BaseModel):
    """Schema for metadata import responses."""

    total_records: int
    imported: int
    updated: int
    skipped: int
    failed: int
    import_errors: List[Dict[str, Any]] = Field(default_factory=list)
    import_summary: Dict[str, Any] = Field(default_factory=dict)


class MetadataSchemaResponse(BaseModel):
    """Schema for metadata schema responses by media type."""

    media_type: MediaType
    technical_fields: List[MetadataFieldSchema] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)
    custom_field_support: bool = Field(default=True)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# END ISSUE #016: Advanced Media Details and Metadata Management
# ============================================================================

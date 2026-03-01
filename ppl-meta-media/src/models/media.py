"""
Media models for PPL Meta Platform Media Service.
"""

import uuid
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class MediaType(Enum):
    """Supported media types."""

    VIDEO = "video"
    PICTURE = "picture"
    SOUND = "sound"
    STREAMING = "streaming"
    DOCUMENT = "document"


class ProcessingStatus(Enum):
    """Media processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class StorageProvider(Enum):
    """Storage backend providers."""

    LOCAL = "local"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"


class Media(BaseModel):
    """Main media entity with metadata."""

    __tablename__ = "media"

    # Unique identifiers
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)

    # Media classification
    media_type = Column(SQLEnum(MediaType), nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)
    file_extension = Column(String(10), nullable=False)

    # File properties
    file_size = Column(Integer, nullable=False)  # bytes
    file_path = Column(String(500), nullable=False)  # relative path
    checksum = Column(String(64), nullable=False, index=True)  # SHA256 hash
    storage_provider = Column(SQLEnum(StorageProvider), default=StorageProvider.LOCAL)

    # Processing status
    processing_status = Column(
        SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    processing_error = Column(Text, nullable=True)  # User and ownership
    uploaded_by = Column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # User UUID from node service

    # Device information
    device_name = Column(String(255), nullable=True)  # "iPhone 15 Pro"
    device_model = Column(String(100), nullable=True)  # "iPhone15,2"
    device_manufacturer = Column(String(100), nullable=True)  # "Apple"
    device_os = Column(String(50), nullable=True)  # "iOS 17.5"
    app_name = Column(String(100), nullable=True)  # "Camera", "Instagram"
    app_version = Column(String(50), nullable=True)  # "1.0.0"

    # Location and context (optional)
    location_data = Column(JSON, nullable=True)  # GPS coordinates, city, etc.
    capture_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Recording timestamps (for camera recordings)
    start_timestamp = Column(DateTime(timezone=True), nullable=True)
    end_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Grouping and organization
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # ["vacation", "family", "2025"]
    categories = Column(JSON, nullable=True)  # Array of categories

    # Technical metadata (varies by media type)
    technical_metadata = Column(JSON, nullable=True)

    # Access control
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    archive_source = Column(String(100), nullable=True)
    archive_reason = Column(Text, nullable=True)
    access_permissions = Column(JSON, nullable=True)  # Complex permissions

    # Relationships
    media_details = relationship("MediaDetails", back_populates="media", uselist=False)
    media_variants = relationship("MediaVariant", back_populates="media")
    archive_status = relationship(
        "MediaArchiveStatus", back_populates="media", uselist=False
    )

    def __repr__(self):
        return (
            f"<Media(uuid={self.uuid}, type={self.media_type.value}, "
            f"filename={self.filename})>"
        )


class MediaDetails(BaseModel):
    """Type-specific media details."""

    __tablename__ = "media_details"

    media_id = Column(Integer, ForeignKey("media.id"), unique=True, index=True)

    # Video-specific fields
    duration = Column(Float, nullable=True)  # seconds
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    frame_rate = Column(Float, nullable=True)
    bitrate = Column(Integer, nullable=True)
    codec = Column(String(50), nullable=True)

    # Audio-specific fields
    audio_channels = Column(Integer, nullable=True)
    audio_sample_rate = Column(Integer, nullable=True)
    audio_bitrate = Column(Integer, nullable=True)
    audio_codec = Column(String(50), nullable=True)

    # Image-specific fields
    color_space = Column(String(20), nullable=True)
    dpi = Column(Integer, nullable=True)
    has_transparency = Column(Boolean, nullable=True)

    # Streaming-specific fields
    stream_type = Column(String(20), nullable=True)  # "live", "vod", "recorded"
    stream_protocol = Column(String(20), nullable=True)  # "hls", "dash", "rtmp"
    manifest_url = Column(String(500), nullable=True)

    # Document-specific fields
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True)

    # Relationships
    media = relationship("Media", back_populates="media_details")


class MediaVariant(BaseModel):
    """Different versions/variants of the same media (thumbnails, different qualities, etc.)."""

    __tablename__ = "media_variants"

    media_id = Column(Integer, ForeignKey("media.id"), index=True)

    variant_type = Column(
        String(50), nullable=False
    )  # "thumbnail", "low_quality", "high_quality", "poster"
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)

    # Variant-specific metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    quality = Column(String(20), nullable=True)  # "low", "medium", "high", "original"

    # Relationships
    media = relationship("Media", back_populates="media_variants")


class MediaCollection(BaseModel):
    """Collections/albums/playlists of media."""

    __tablename__ = "media_collections"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    name = Column(String(255), unique=True, nullable=False)  # Unique collection name (synced with camera name)
    description = Column(Text, nullable=True)

    # Ownership
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Camera association
    camera_device_id = Column(
        String(255), nullable=True, index=True
    )  # Links collection to specific camera

    # Collection settings
    is_public = Column(Boolean, default=False)
    cover_media_id = Column(Integer, ForeignKey("media.id"), nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)  # Display settings, etc.

    # Relationships
    storage_config = relationship(
        "CollectionStorageConfig", back_populates="collection", uselist=False
    )
    storage_usage = relationship(
        "CollectionStorageUsage", back_populates="collection", uselist=False
    )


class MediaCollectionItem(BaseModel):
    """Association between media and collections."""

    __tablename__ = "media_collection_items"

    collection_id = Column(Integer, ForeignKey("media_collections.id"), index=True)
    media_id = Column(Integer, ForeignKey("media.id"), index=True)

    # Ordering and metadata
    sort_order = Column(Integer, default=0)
    added_by = Column(UUID(as_uuid=True), nullable=False)
    notes = Column(Text, nullable=True)


class MediaShare(BaseModel):
    """Sharing permissions and links for media."""

    __tablename__ = "media_shares"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    media_id = Column(Integer, ForeignKey("media.id"), index=True)

    # Share settings
    shared_by = Column(UUID(as_uuid=True), nullable=False)
    shared_with = Column(UUID(as_uuid=True), nullable=True)  # Null = public link
    share_token = Column(String(255), unique=True, index=True)

    # Permissions
    can_view = Column(Boolean, default=True)
    can_download = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_views = Column(Integer, nullable=True)
    view_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

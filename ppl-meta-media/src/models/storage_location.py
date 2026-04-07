"""
Storage Location Model

Defines user-configurable storage locations where media files can reside.
Supports local disk, external drives, and cloud storage providers.
"""

import uuid
from enum import Enum

from sqlalchemy import Boolean, BigInteger, Column, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import BaseModel


class LocationType(Enum):
    """Storage location types."""

    LOCAL_DISK = "local_disk"
    EXTERNAL_DRIVE = "external_drive"
    CLOUD_S3 = "cloud_s3"
    CLOUD_AZURE = "cloud_azure"
    CLOUD_GCP = "cloud_gcp"


class StorageTier(Enum):
    """Storage tier classification."""

    ACTIVE = "active"
    ARCHIVE = "archive"


class StorageLocation(BaseModel):
    """
    User-defined storage location where media files can reside.

    Supports local disk paths, external/mounted drives, and cloud storage buckets.
    Each location tracks its capacity, usage, and availability status.
    """

    __tablename__ = "storage_locations"

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Owner
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Display
    name = Column(String(255), nullable=False)  # e.g. "Main SSD", "NAS Backup"

    # Type and path
    location_type = Column(SQLEnum(LocationType), nullable=False)
    base_path = Column(
        String(1000), nullable=False
    )  # /Volumes/MediaDrive or s3://bucket

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Tier
    tier = Column(SQLEnum(StorageTier), default=StorageTier.ACTIVE, nullable=False)

    # Capacity tracking
    total_capacity_bytes = Column(BigInteger, nullable=True)  # null = unlimited (cloud)
    used_bytes = Column(BigInteger, default=0, nullable=False)
    file_count = Column(Integer, default=0, nullable=False)

    # Cloud credentials (encrypted JSON, null for local/external)
    cloud_config = Column(JSON, nullable=True)

    # Verification
    mount_verified = Column(Boolean, default=False, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def free_bytes(self):
        """Available bytes. None if unlimited."""
        if self.total_capacity_bytes is None:
            return None
        return max(0, self.total_capacity_bytes - self.used_bytes)

    @property
    def usage_percentage(self):
        """Usage as a percentage. 0 if unlimited."""
        if not self.total_capacity_bytes or self.total_capacity_bytes == 0:
            return 0.0
        return round((self.used_bytes / self.total_capacity_bytes) * 100, 2)

    @property
    def total_capacity_gb(self):
        """Total capacity in GB. None if unlimited."""
        if self.total_capacity_bytes is None:
            return None
        return round(self.total_capacity_bytes / (1024**3), 2)

    @property
    def used_gb(self):
        """Used space in GB."""
        return round(self.used_bytes / (1024**3), 2)

    @property
    def free_gb(self):
        """Free space in GB. None if unlimited."""
        if self.free_bytes is None:
            return None
        return round(self.free_bytes / (1024**3), 2)

    @property
    def uri_scheme(self):
        """URI scheme for this location type."""
        schemes = {
            LocationType.LOCAL_DISK: "file://",
            LocationType.EXTERNAL_DRIVE: "file://",
            LocationType.CLOUD_S3: "s3://",
            LocationType.CLOUD_AZURE: "azure://",
            LocationType.CLOUD_GCP: "gs://",
        }
        return schemes.get(self.location_type, "file://")

    @property
    def is_cloud(self):
        """Whether this is a cloud storage location."""
        return self.location_type in (
            LocationType.CLOUD_S3,
            LocationType.CLOUD_AZURE,
            LocationType.CLOUD_GCP,
        )

    def __repr__(self):
        return (
            f"<StorageLocation(uuid={self.uuid}, name='{self.name}', "
            f"type={self.location_type.value}, tier={self.tier.value})>"
        )

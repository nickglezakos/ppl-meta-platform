"""
Base storage provider interface and configuration for cloud storage.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO, Dict, List, Optional


@dataclass
class StorageConfig:
    """Configuration for cloud storage providers."""

    provider: str  # 's3', 'azure', 'gcp'
    bucket_name: str
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    connection_string: Optional[str] = None  # For Azure
    project_id: Optional[str] = None  # For GCP
    credentials_path: Optional[str] = None  # For GCP service account

    # Additional configuration
    public_read: bool = False
    encryption: bool = True
    versioning: bool = False
    lifecycle_days: int = 365

    @classmethod
    def from_env(cls, provider: str) -> "StorageConfig":
        """Create configuration from environment variables."""
        if provider.lower() == "s3":
            return cls(
                provider="s3",
                bucket_name=os.getenv("S3_BUCKET_NAME", ""),
                region=os.getenv("S3_REGION", "us-east-1"),
                access_key=os.getenv("S3_ACCESS_KEY", ""),
                secret_key=os.getenv("S3_SECRET_KEY", ""),
                endpoint_url=os.getenv("S3_ENDPOINT_URL"),
                public_read=(os.getenv("S3_PUBLIC_READ", "false").lower() == "true"),
                encryption=(os.getenv("S3_ENCRYPTION", "true").lower() == "true"),
                versioning=(os.getenv("S3_VERSIONING", "false").lower() == "true"),
            )
        elif provider.lower() == "azure":
            return cls(
                provider="azure",
                bucket_name=os.getenv("AZURE_CONTAINER_NAME", ""),
                connection_string=(os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")),
                public_read=(os.getenv("AZURE_PUBLIC_READ", "false").lower() == "true"),
                encryption=(os.getenv("AZURE_ENCRYPTION", "true").lower() == "true"),
            )
        elif provider.lower() == "gcp":
            return cls(
                provider="gcp",
                bucket_name=os.getenv("GCP_BUCKET_NAME", ""),
                project_id=os.getenv("GCP_PROJECT_ID", ""),
                credentials_path=os.getenv("GCP_CREDENTIALS_PATH"),
                region=os.getenv("GCP_REGION", "us-central1"),
                public_read=(os.getenv("GCP_PUBLIC_READ", "false").lower() == "true"),
                encryption=(os.getenv("GCP_ENCRYPTION", "true").lower() == "true"),
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")


@dataclass
class FileMetadata:
    """Metadata for stored files."""

    key: str
    size: int
    content_type: str
    last_modified: datetime
    etag: str
    public_url: Optional[str] = None
    version_id: Optional[str] = None
    storage_class: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


@dataclass
class UploadResult:
    """Result of file upload operation."""

    key: str
    url: str
    size: int
    etag: str
    version_id: Optional[str] = None
    public_url: Optional[str] = None


class BaseStorageProvider(ABC):
    """Abstract base class for cloud storage providers."""

    def __init__(self, config: StorageConfig):
        """Initialize storage provider with configuration."""
        self.config = config
        self._client = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage provider client."""

    @abstractmethod
    async def upload_file(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None,
        public_read: Optional[bool] = None,
    ) -> UploadResult:
        """
        Upload a file to cloud storage.

        Args:
            file_data: File-like object containing data to upload
            key: Storage key/path for the file
            content_type: MIME type of the file
            metadata: Optional metadata to store with file
            public_read: Whether file should be publicly readable

        Returns:
            UploadResult with details of uploaded file
        """

    @abstractmethod
    async def download_file(self, key: str, local_path: Optional[str] = None) -> bytes:
        """
        Download a file from cloud storage.

        Args:
            key: Storage key/path of the file
            local_path: Optional local path to save file

        Returns:
            File content as bytes
        """

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from cloud storage.

        Args:
            key: Storage key/path of the file

        Returns:
            True if file was deleted successfully
        """

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in cloud storage.

        Args:
            key: Storage key/path of the file

        Returns:
            True if file exists
        """

    @abstractmethod
    async def get_file_metadata(self, key: str) -> FileMetadata:
        """
        Get metadata for a file in cloud storage.

        Args:
            key: Storage key/path of the file

        Returns:
            FileMetadata object with file information
        """

    @abstractmethod
    async def list_files(
        self, prefix: str = "", limit: int = 1000
    ) -> List[FileMetadata]:
        """
        List files in cloud storage.

        Args:
            prefix: Optional prefix to filter files
            limit: Maximum number of files to return

        Returns:
            List of FileMetadata objects
        """

    @abstractmethod
    async def generate_presigned_url(
        self, key: str, expiration: int = 3600, operation: str = "get"
    ) -> str:
        """
        Generate a presigned URL for file access.

        Args:
            key: Storage key/path of the file
            expiration: URL expiration time in seconds
            operation: Operation type ('get', 'put', 'delete')

        Returns:
            Presigned URL string
        """

    @abstractmethod
    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        destination_bucket: Optional[str] = None,
    ) -> bool:
        """
        Copy a file within or between buckets.

        Args:
            source_key: Source file key
            destination_key: Destination file key
            destination_bucket: Optional destination bucket

        Returns:
            True if copy was successful
        """

    async def get_storage_info(self) -> Dict[str, Any]:
        """Get storage provider information and statistics."""
        return {
            "provider": self.config.provider,
            "bucket": self.config.bucket_name,
            "region": self.config.region,
            "encryption": self.config.encryption,
            "versioning": self.config.versioning,
            "public_read_default": self.config.public_read,
        }

    async def test_connection(self) -> bool:
        """Test connection to storage provider."""
        try:
            await self.initialize()
            # Try to list files with limit 1 to test connectivity
            await self.list_files(limit=1)
            return True
        except Exception:
            return False

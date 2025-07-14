"""
Cloud Storage Service integration for PPL Meta Media Service.
"""

import logging
import os

# Import from the cloud_storage module in the same package
import sys
import time
from typing import BinaryIO, Dict, List, Optional, Union

from fastapi import UploadFile

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cloud_storage import (
    CloudStorageError,
    CloudStorageManager,
    FileMetadata,
    StorageConfig,
    UploadResult,
)

logger = logging.getLogger(__name__)


class MediaCloudStorageService:
    """Cloud storage service for media files."""

    def __init__(self, storage_manager: CloudStorageManager = None):
        """Initialize media cloud storage service."""
        self.storage_manager = storage_manager or storage_manager
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize cloud storage providers from environment."""
        if self._initialized:
            return

        try:
            # Initialize S3 if configured
            if self._is_s3_configured():
                await self._setup_s3_provider()

            # Initialize Azure if configured
            if self._is_azure_configured():
                await self._setup_azure_provider()

            # Initialize GCP if configured
            if self._is_gcp_configured():
                await self._setup_gcp_provider()

            self._initialized = True
            logger.info("Media cloud storage service initialized")

        except Exception as e:
            logger.error(f"Failed to initialize cloud storage: {e}")
            raise CloudStorageError(f"Storage initialization failed: {e}") from e

    def _is_s3_configured(self) -> bool:
        """Check if S3 is configured."""
        return all(
            [
                os.getenv("S3_BUCKET_NAME"),
                os.getenv("S3_ACCESS_KEY"),
                os.getenv("S3_SECRET_KEY"),
            ]
        )

    def _is_azure_configured(self) -> bool:
        """Check if Azure is configured."""
        return all(
            [
                os.getenv("AZURE_CONTAINER_NAME"),
                os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
            ]
        )

    def _is_gcp_configured(self) -> bool:
        """Check if GCP is configured."""
        return all(
            [
                os.getenv("GCP_BUCKET_NAME"),
                os.getenv("GCP_PROJECT_ID"),
                (
                    os.getenv("GCP_CREDENTIALS_PATH")
                    or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                ),
            ]
        )

    async def _setup_s3_provider(self) -> None:
        """Setup S3 storage provider."""
        config = StorageConfig.from_env("s3")
        await self.storage_manager.add_provider("s3", config, set_as_default=True)
        logger.info("S3 storage provider configured")

    async def _setup_azure_provider(self) -> None:
        """Setup Azure storage provider."""
        config = StorageConfig.from_env("azure")
        await self.storage_manager.add_provider("azure", config)
        logger.info("Azure storage provider configured")

    async def _setup_gcp_provider(self) -> None:
        """Setup GCP storage provider."""
        config = StorageConfig.from_env("gcp")
        await self.storage_manager.add_provider("gcp", config)
        logger.info("GCP storage provider configured")

    async def upload_media(
        self,
        file: Union[UploadFile, BinaryIO],
        file_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public_read: bool = False,
        provider: Optional[str] = None,
    ) -> UploadResult:
        """
        Upload a media file to cloud storage.

        Args:
            file: File to upload (FastAPI UploadFile or BinaryIO)
            file_key: Storage key for the file
            content_type: MIME type of the file
            metadata: Optional metadata to store with file
            public_read: Whether file should be publicly readable
            provider: Optional specific provider to use

        Returns:
            UploadResult with details of uploaded file
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Handle FastAPI UploadFile
            if hasattr(file, "file"):
                file_data = file.file
                if content_type is None:
                    content_type = file.content_type or "application/octet-stream"
            else:
                file_data = file
                if content_type is None:
                    content_type = "application/octet-stream"

            # Add media-specific metadata
            if metadata is None:
                metadata = {}
            metadata.update(
                {"service": "ppl-meta-media", "upload_timestamp": str(int(time.time()))}
            )

            # Upload to cloud storage
            result = await self.storage_manager.upload_file(
                file_data=file_data,
                key=file_key,
                content_type=content_type,
                metadata=metadata,
                public_read=public_read,
                provider=provider,
            )

            logger.info(f"Uploaded media file: {file_key}")
            return result

        except Exception as e:
            logger.error(f"Media upload failed: {e}")
            raise CloudStorageError(f"Media upload failed: {e}") from e

    async def download_media(
        self,
        file_key: str,
        local_path: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> bytes:
        """
        Download a media file from cloud storage.

        Args:
            file_key: Storage key of the file
            local_path: Optional local path to save file
            provider: Optional specific provider to use

        Returns:
            File content as bytes
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self.storage_manager.download_file(
                key=file_key, local_path=local_path, provider=provider
            )
        except Exception as e:
            logger.error(f"Media download failed: {e}")
            raise CloudStorageError(f"Media download failed: {e}") from e

    async def delete_media(self, file_key: str, provider: Optional[str] = None) -> bool:
        """
        Delete a media file from cloud storage.

        Args:
            file_key: Storage key of the file
            provider: Optional specific provider to use

        Returns:
            True if file was deleted successfully
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.storage_manager.delete_file(
                key=file_key, provider=provider
            )
            if result:
                logger.info(f"Deleted media file: {file_key}")
            return result
        except Exception as e:
            logger.error(f"Media deletion failed: {e}")
            raise CloudStorageError(f"Media deletion failed: {e}") from e

    async def get_media_metadata(
        self, file_key: str, provider: Optional[str] = None
    ) -> FileMetadata:
        """
        Get metadata for a media file.

        Args:
            file_key: Storage key of the file
            provider: Optional specific provider to use

        Returns:
            FileMetadata object with file information
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self.storage_manager.get_file_metadata(
                key=file_key, provider=provider
            )
        except Exception as e:
            logger.error(f"Media metadata retrieval failed: {e}")
            raise CloudStorageError(f"Media metadata retrieval failed: {e}") from e

    async def list_media_files(
        self, prefix: str = "media/", limit: int = 1000, provider: Optional[str] = None
    ) -> List[FileMetadata]:
        """
        List media files in cloud storage.

        Args:
            prefix: Prefix to filter files (default: "media/")
            limit: Maximum number of files to return
            provider: Optional specific provider to use

        Returns:
            List of FileMetadata objects
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self.storage_manager.list_files(
                prefix=prefix, limit=limit, provider=provider
            )
        except Exception as e:
            logger.error(f"Media file listing failed: {e}")
            raise CloudStorageError(f"Media file listing failed: {e}") from e

    async def generate_media_url(
        self,
        file_key: str,
        expiration: int = 3600,
        operation: str = "get",
        provider: Optional[str] = None,
    ) -> str:
        """
        Generate a presigned URL for media file access.

        Args:
            file_key: Storage key of the file
            expiration: URL expiration time in seconds
            operation: Operation type ('get', 'put', 'delete')
            provider: Optional specific provider to use

        Returns:
            Presigned URL string
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self.storage_manager.generate_presigned_url(
                key=file_key,
                expiration=expiration,
                operation=operation,
                provider=provider,
            )
        except Exception as e:
            logger.error(f"Media URL generation failed: {e}")
            raise CloudStorageError(f"Media URL generation failed: {e}") from e

    async def get_storage_health(self) -> Dict[str, bool]:
        """Get health status of all configured storage providers."""
        if not self._initialized:
            await self.initialize()

        return await self.storage_manager.health_check()

    async def get_storage_stats(self) -> Dict[str, Dict]:
        """Get storage statistics for all providers."""
        if not self._initialized:
            await self.initialize()

        return await self.storage_manager.get_storage_stats()


# Global service instance
media_cloud_storage = MediaCloudStorageService()

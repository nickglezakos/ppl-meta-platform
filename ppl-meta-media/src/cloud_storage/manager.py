"""
Cloud storage manager for handling multiple storage providers.
"""

import logging
from dataclasses import asdict
from typing import BinaryIO, Dict, List, Optional, Type

from .base import BaseStorageProvider, FileMetadata, StorageConfig, UploadResult
from .exceptions import CloudProviderNotFoundError, CloudStorageError

logger = logging.getLogger(__name__)


class CloudStorageManager:
    """Manager for multiple cloud storage providers."""

    def __init__(self):
        """Initialize the cloud storage manager."""
        self._providers: Dict[str, BaseStorageProvider] = {}
        self._default_provider: Optional[str] = None
        self._provider_classes: Dict[str, Type[BaseStorageProvider]] = {}

        # Register available providers
        self._register_providers()

    def _register_providers(self) -> None:
        """Register available storage providers."""
        try:
            from .s3 import S3StorageProvider

            self._provider_classes["s3"] = S3StorageProvider
        except ImportError:
            logger.warning("S3 provider not available (boto3 not installed)")

        try:
            from .azure import AzureBlobProvider

            self._provider_classes["azure"] = AzureBlobProvider
        except ImportError:
            logger.warning("Azure provider not available")

        try:
            from .gcp import GCPStorageProvider

            self._provider_classes["gcp"] = GCPStorageProvider
        except ImportError:
            logger.warning("GCP provider not available")

    async def add_provider(
        self, name: str, config: StorageConfig, set_as_default: bool = False
    ) -> None:
        """
        Add a storage provider with configuration.

        Args:
            name: Provider instance name
            config: Storage configuration
            set_as_default: Whether to set as default provider
        """
        provider_type = config.provider.lower()

        if provider_type not in self._provider_classes:
            available = list(self._provider_classes.keys())
            raise CloudProviderNotFoundError(
                f"Provider '{provider_type}' not available. "
                f"Available providers: {available}"
            )

        # Create provider instance
        provider_class = self._provider_classes[provider_type]
        provider = provider_class(config)

        # Initialize provider
        await provider.initialize()

        # Store provider
        self._providers[name] = provider

        # Set as default if requested or if it's the first provider
        if set_as_default or self._default_provider is None:
            self._default_provider = name

        logger.info(f"Added {provider_type} provider '{name}'")

    async def remove_provider(self, name: str) -> bool:
        """
        Remove a storage provider.

        Args:
            name: Provider instance name

        Returns:
            True if provider was removed
        """
        if name not in self._providers:
            return False

        del self._providers[name]

        # Reset default if this was the default provider
        if self._default_provider == name:
            self._default_provider = (
                next(iter(self._providers.keys())) if self._providers else None
            )

        logger.info(f"Removed provider '{name}'")
        return True

    def get_provider(self, name: Optional[str] = None) -> BaseStorageProvider:
        """
        Get a storage provider by name.

        Args:
            name: Provider name (uses default if None)

        Returns:
            Storage provider instance
        """
        if name is None:
            name = self._default_provider

        if name is None:
            raise CloudStorageError("No storage providers configured")

        if name not in self._providers:
            available = list(self._providers.keys())
            raise CloudProviderNotFoundError(
                f"Provider '{name}' not found. Available: {available}"
            )

        return self._providers[name]

    def list_providers(self) -> List[str]:
        """List all configured provider names."""
        return list(self._providers.keys())

    def get_default_provider(self) -> Optional[str]:
        """Get the default provider name."""
        return self._default_provider

    def set_default_provider(self, name: str) -> None:
        """Set the default provider."""
        if name not in self._providers:
            available = list(self._providers.keys())
            raise CloudProviderNotFoundError(
                f"Provider '{name}' not found. Available: {available}"
            )
        self._default_provider = name

    # Convenience methods that delegate to the default provider

    async def upload_file(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None,
        public_read: Optional[bool] = None,
        provider: Optional[str] = None,
    ) -> UploadResult:
        """Upload a file using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.upload_file(
            file_data, key, content_type, metadata, public_read
        )

    async def download_file(
        self, key: str, local_path: Optional[str] = None, provider: Optional[str] = None
    ) -> bytes:
        """Download a file using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.download_file(key, local_path)

    async def delete_file(self, key: str, provider: Optional[str] = None) -> bool:
        """Delete a file using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.delete_file(key)

    async def file_exists(self, key: str, provider: Optional[str] = None) -> bool:
        """Check if file exists using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.file_exists(key)

    async def get_file_metadata(
        self, key: str, provider: Optional[str] = None
    ) -> FileMetadata:
        """Get file metadata using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.get_file_metadata(key)

    async def list_files(
        self, prefix: str = "", limit: int = 1000, provider: Optional[str] = None
    ) -> List[FileMetadata]:
        """List files using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.list_files(prefix, limit)

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        operation: str = "get",
        provider: Optional[str] = None,
    ) -> str:
        """Generate presigned URL using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.generate_presigned_url(key, expiration, operation)

    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        destination_bucket: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> bool:
        """Copy file using specified or default provider."""
        storage_provider = self.get_provider(provider)
        return await storage_provider.copy_file(
            source_key, destination_key, destination_bucket
        )

    async def migrate_file(
        self,
        key: str,
        source_provider: str,
        destination_provider: str,
        delete_source: bool = False,
    ) -> bool:
        """
        Migrate a file between storage providers.

        Args:
            key: File key to migrate
            source_provider: Source provider name
            destination_provider: Destination provider name
            delete_source: Whether to delete from source after migration

        Returns:
            True if migration was successful
        """
        try:
            # Get providers
            source = self.get_provider(source_provider)
            destination = self.get_provider(destination_provider)

            # Download from source
            file_data = await source.download_file(key)
            metadata = await source.get_file_metadata(key)

            # Upload to destination
            from io import BytesIO

            await destination.upload_file(
                BytesIO(file_data), key, metadata.content_type, metadata.metadata
            )

            # Delete from source if requested
            if delete_source:
                await source.delete_file(key)

            logger.info(
                f"Migrated file '{key}' from {source_provider} "
                f"to {destination_provider}"
            )
            return True

        except Exception as e:
            logger.error(f"File migration failed: {e}")
            raise CloudStorageError(f"File migration failed: {e}") from e

    async def get_storage_stats(self) -> Dict[str, Dict]:
        """Get storage statistics for all providers."""
        stats = {}
        for name, provider in self._providers.items():
            try:
                provider_info = await provider.get_storage_info()
                # Get file count and total size
                files = await provider.list_files(limit=10000)  # Sample
                total_size = sum(f.size for f in files)

                stats[name] = {
                    **provider_info,
                    "file_count": len(files),
                    "total_size_bytes": total_size,
                    "status": "healthy",
                }
            except Exception as e:
                stats[name] = {"status": "error", "error": str(e)}

        return stats

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all configured providers."""
        health = {}
        for name, provider in self._providers.items():
            try:
                health[name] = await provider.test_connection()
            except Exception:
                health[name] = False

        return health


# Global instance
storage_manager = CloudStorageManager()

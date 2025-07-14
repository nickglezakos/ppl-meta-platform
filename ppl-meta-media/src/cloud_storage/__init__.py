"""
Cloud Storage Module for PPL Meta Media Service.

This module provides a unified interface for multiple cloud storage providers
including AWS S3, Azure Blob Storage, and Google Cloud Storage.
"""

from .base import BaseStorageProvider, FileMetadata, StorageConfig, UploadResult
from .exceptions import (
    AuthenticationError,
    CloudFileNotFoundError,
    CloudProviderNotFoundError,
    CloudStorageError,
    ConfigurationError,
    DownloadError,
    ProviderNotFoundError,
    QuotaExceededError,
    UploadError,
)
from .manager import CloudStorageManager, storage_manager

# Try to import providers (they may not be available if dependencies aren't installed)
try:
    from .s3 import S3StorageProvider

    __all__ = [
        "CloudStorageManager",
        "storage_manager",
        "StorageConfig",
        "FileMetadata",
        "UploadResult",
        "BaseStorageProvider",
        "S3StorageProvider",
        "CloudStorageError",
        "CloudFileNotFoundError",
        "CloudProviderNotFoundError",
    ]
except ImportError:
    __all__ = [
        "CloudStorageManager",
        "storage_manager",
        "StorageConfig",
        "FileMetadata",
        "UploadResult",
        "BaseStorageProvider",
        "CloudStorageError",
        "CloudFileNotFoundError",
        "CloudProviderNotFoundError",
    ]

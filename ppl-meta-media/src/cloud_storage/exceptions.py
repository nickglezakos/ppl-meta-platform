"""
Cloud Storage exceptions for PPL Meta Media Service.
"""


class CloudStorageError(Exception):
    """Base exception for cloud storage operations."""

    pass


class ProviderNotFoundError(CloudStorageError):
    """Raised when specified storage provider is not available."""

    pass


class CloudFileNotFoundError(CloudStorageError):
    """Raised when a file is not found in cloud storage."""

    pass


class UploadError(CloudStorageError):
    """Raised when file upload fails."""

    pass


class DownloadError(CloudStorageError):
    """Raised when file download fails."""

    pass


class ConfigurationError(CloudStorageError):
    """Raised when storage provider configuration is invalid."""

    pass


class AuthenticationError(CloudStorageError):
    """Raised when authentication with storage provider fails."""

    pass


class QuotaExceededError(CloudStorageError):
    """Raised when storage quota is exceeded."""

    pass


class CloudProviderNotFoundError(CloudStorageError):
    """Raised when a requested storage provider is not found."""

    pass

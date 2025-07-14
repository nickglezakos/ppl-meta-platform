"""
AWS S3 storage provider implementation.
"""

import asyncio
import logging
from typing import BinaryIO, Dict, List, Optional

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .base import BaseStorageProvider, FileMetadata, StorageConfig, UploadResult
from .exceptions import (
    CloudAuthenticationError,
    CloudFileNotFoundError,
    CloudPermissionError,
    CloudStorageError,
)

logger = logging.getLogger(__name__)


class S3StorageProvider(BaseStorageProvider):
    """AWS S3 storage provider implementation."""

    def __init__(self, config: StorageConfig):
        """Initialize S3 storage provider."""
        if not BOTO3_AVAILABLE:
            raise CloudStorageError(
                "boto3 library is required for S3 storage provider. "
                "Install it with: pip install boto3"
            )

        super().__init__(config)
        self._s3_client = None
        self._s3_resource = None

    async def initialize(self) -> None:
        """Initialize S3 client and resource."""
        try:
            # Create boto3 config
            boto_config = Config(
                region_name=self.config.region,
                retries={"max_attempts": 3, "mode": "adaptive"},
                signature_version="s3v4",
            )

            # Create S3 client
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                endpoint_url=self.config.endpoint_url,
                config=boto_config,
            )

            # Create S3 resource
            self._s3_resource = boto3.resource(
                "s3",
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                endpoint_url=self.config.endpoint_url,
                config=boto_config,
            )

            # Verify bucket exists
            await self._ensure_bucket_exists()

            logger.info(
                f"S3 storage provider initialized for bucket: {self.config.bucket_name}"
            )

        except NoCredentialsError as e:
            raise CloudAuthenticationError(f"S3 authentication failed: {e}") from e
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                raise CloudPermissionError(f"S3 access denied: {e}") from e
            elif error_code == "NoSuchBucket":
                raise CloudStorageError(
                    f"S3 bucket not found: {self.config.bucket_name}"
                ) from e
            else:
                raise CloudStorageError(f"S3 initialization failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 initialization failed: {e}") from e

    async def _ensure_bucket_exists(self) -> None:
        """Ensure the S3 bucket exists."""
        try:
            await asyncio.to_thread(
                self._s3_client.head_bucket, Bucket=self.config.bucket_name
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Bucket doesn't exist, create it
                if self.config.region == "us-east-1":
                    await asyncio.to_thread(
                        self._s3_client.create_bucket, Bucket=self.config.bucket_name
                    )
                else:
                    await asyncio.to_thread(
                        self._s3_client.create_bucket,
                        Bucket=self.config.bucket_name,
                        CreateBucketConfiguration={
                            "LocationConstraint": self.config.region
                        },
                    )
                logger.info(f"Created S3 bucket: {self.config.bucket_name}")
            else:
                raise

    async def upload_file(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None,
        public_read: Optional[bool] = None,
    ) -> UploadResult:
        """Upload a file to S3."""
        try:
            # Prepare upload parameters
            upload_args = {
                "Bucket": self.config.bucket_name,
                "Key": key,
                "Body": file_data,
                "ContentType": content_type,
            }

            # Add metadata if provided
            if metadata:
                upload_args["Metadata"] = metadata

            # Add server-side encryption if enabled
            if self.config.encryption:
                upload_args["ServerSideEncryption"] = "AES256"

            # Set ACL for public read if specified
            if public_read or (public_read is None and self.config.public_read):
                upload_args["ACL"] = "public-read"

            # Upload file
            response = await asyncio.to_thread(
                self._s3_client.put_object, **upload_args
            )

            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset position

            # Generate URLs
            url = f"https://{self.config.bucket_name}.s3.{self.config.region}.amazonaws.com/{key}"
            public_url = url if (public_read or self.config.public_read) else None

            return UploadResult(
                key=key,
                url=url,
                size=file_size,
                etag=response["ETag"].strip('"'),
                version_id=response.get("VersionId"),
                public_url=public_url,
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                raise CloudPermissionError(f"S3 upload access denied: {e}") from e
            elif error_code == "NoSuchBucket":
                raise CloudStorageError(
                    f"S3 bucket not found: {self.config.bucket_name}"
                ) from e
            else:
                raise CloudStorageError(f"S3 upload failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 upload failed: {e}") from e

    async def download_file(self, key: str, local_path: Optional[str] = None) -> bytes:
        """Download a file from S3."""
        try:
            if local_path:
                # Download to local file
                await asyncio.to_thread(
                    self._s3_client.download_file,
                    self.config.bucket_name,
                    key,
                    local_path,
                )
                # Return file content
                with open(local_path, "rb") as f:
                    return f.read()
            else:
                # Download to memory
                response = await asyncio.to_thread(
                    self._s3_client.get_object, Bucket=self.config.bucket_name, Key=key
                )
                return response["Body"].read()

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise CloudFileNotFoundError(f"S3 file not found: {key}") from e
            elif error_code == "AccessDenied":
                raise CloudPermissionError(f"S3 download access denied: {e}") from e
            else:
                raise CloudStorageError(f"S3 download failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 download failed: {e}") from e

    async def delete_file(self, key: str) -> bool:
        """Delete a file from S3."""
        try:
            await asyncio.to_thread(
                self._s3_client.delete_object, Bucket=self.config.bucket_name, Key=key
            )
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                return False  # File already doesn't exist
            elif error_code == "AccessDenied":
                raise CloudPermissionError(f"S3 delete access denied: {e}") from e
            else:
                raise CloudStorageError(f"S3 delete failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 delete failed: {e}") from e

    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            await asyncio.to_thread(
                self._s3_client.head_object, Bucket=self.config.bucket_name, Key=key
            )
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey" or error_code == "404":
                return False
            else:
                raise CloudStorageError(f"S3 file check failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 file check failed: {e}") from e

    async def get_file_metadata(self, key: str) -> FileMetadata:
        """Get metadata for a file in S3."""
        try:
            response = await asyncio.to_thread(
                self._s3_client.head_object, Bucket=self.config.bucket_name, Key=key
            )

            # Generate public URL if applicable
            public_url = None
            if self.config.public_read:
                public_url = f"https://{self.config.bucket_name}.s3.{self.config.region}.amazonaws.com/{key}"

            return FileMetadata(
                key=key,
                size=response["ContentLength"],
                content_type=response.get("ContentType", "application/octet-stream"),
                last_modified=response["LastModified"],
                etag=response["ETag"].strip('"'),
                public_url=public_url,
                version_id=response.get("VersionId"),
                storage_class=response.get("StorageClass"),
                metadata=response.get("Metadata", {}),
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise CloudFileNotFoundError(f"S3 file not found: {key}") from e
            else:
                raise CloudStorageError(f"S3 metadata retrieval failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 metadata retrieval failed: {e}") from e

    async def list_files(
        self, prefix: str = "", limit: int = 1000
    ) -> List[FileMetadata]:
        """List files in S3."""
        try:
            paginator = self._s3_client.get_paginator("list_objects_v2")

            page_iterator = paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                PaginationConfig={"MaxItems": limit},
            )

            files = []
            for page in page_iterator:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        # Generate public URL if applicable
                        public_url = None
                        if self.config.public_read:
                            public_url = (
                                f"https://{self.config.bucket_name}.s3."
                                f"{self.config.region}.amazonaws.com/{obj['Key']}"
                            )

                        files.append(
                            FileMetadata(
                                key=obj["Key"],
                                size=obj["Size"],
                                content_type="application/octet-stream",  # Not available in list
                                last_modified=obj["LastModified"],
                                etag=obj["ETag"].strip('"'),
                                public_url=public_url,
                                storage_class=obj.get("StorageClass"),
                            )
                        )

            return files

        except ClientError as e:
            raise CloudStorageError(f"S3 file listing failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 file listing failed: {e}") from e

    async def generate_presigned_url(
        self, key: str, expiration: int = 3600, operation: str = "get"
    ) -> str:
        """Generate a presigned URL for S3 file access."""
        try:
            # Map operation to S3 method
            operation_mapping = {
                "get": "get_object",
                "put": "put_object",
                "delete": "delete_object",
            }

            if operation not in operation_mapping:
                raise ValueError(f"Unsupported operation: {operation}")

            url = await asyncio.to_thread(
                self._s3_client.generate_presigned_url,
                operation_mapping[operation],
                Params={"Bucket": self.config.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )

            return url

        except ClientError as e:
            raise CloudStorageError(f"S3 presigned URL generation failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 presigned URL generation failed: {e}") from e

    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        destination_bucket: Optional[str] = None,
    ) -> bool:
        """Copy a file within or between S3 buckets."""
        try:
            dest_bucket = destination_bucket or self.config.bucket_name

            copy_source = {"Bucket": self.config.bucket_name, "Key": source_key}

            await asyncio.to_thread(
                self._s3_client.copy_object,
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=destination_key,
            )

            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise CloudFileNotFoundError(
                    f"S3 source file not found: {source_key}"
                ) from e
            elif error_code == "AccessDenied":
                raise CloudPermissionError(f"S3 copy access denied: {e}") from e
            else:
                raise CloudStorageError(f"S3 copy failed: {e}") from e
        except Exception as e:
            raise CloudStorageError(f"S3 copy failed: {e}") from e

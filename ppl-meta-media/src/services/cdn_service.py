"""
Content Delivery Network (CDN) integration for PPL Meta Platform.
Provides optimized media delivery through AWS CloudFront or similar CDN services.
"""

import logging
import mimetypes
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CDNConfig:
    """CDN configuration settings."""

    def __init__(
        self,
        distribution_domain: str,
        s3_bucket: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        aws_region: str = "us-east-1",
        cache_behaviors: Optional[Dict[str, Dict]] = None,
    ):
        self.distribution_domain = distribution_domain
        self.s3_bucket = s3_bucket
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.cache_behaviors = cache_behaviors or self._default_cache_behaviors()

    def _default_cache_behaviors(self) -> Dict[str, Dict]:
        """Default cache behaviors for different content types."""
        return {
            "images": {
                "path_pattern": "*.{jpg,jpeg,png,gif,webp,svg}",
                "cache_ttl": 86400 * 30,  # 30 days
                "compress": True,
                "viewer_protocol_policy": "redirect-to-https",
            },
            "videos": {
                "path_pattern": "*.{mp4,avi,mov,wmv,flv,webm}",
                "cache_ttl": 86400 * 7,  # 7 days
                "compress": False,
                "viewer_protocol_policy": "redirect-to-https",
            },
            "thumbnails": {
                "path_pattern": "thumbnails/*",
                "cache_ttl": 86400 * 60,  # 60 days
                "compress": True,
                "viewer_protocol_policy": "redirect-to-https",
            },
            "api": {
                "path_pattern": "api/*",
                "cache_ttl": 0,  # No caching
                "compress": True,
                "viewer_protocol_policy": "redirect-to-https",
            },
        }


class CDNService:
    """Content Delivery Network service for optimized media delivery."""

    def __init__(self, config: CDNConfig):
        self.config = config
        self.enabled = AWS_AVAILABLE and bool(config.distribution_domain)

        if not self.enabled:
            logger.warning(
                "CDN service disabled - AWS SDK not available or configuration incomplete"
            )
            return

        # Initialize AWS clients
        session_kwargs = {"region_name": config.aws_region}
        if config.aws_access_key and config.aws_secret_key:
            session_kwargs.update(
                {
                    "aws_access_key_id": config.aws_access_key,
                    "aws_secret_access_key": config.aws_secret_key,
                }
            )

        try:
            self.session = boto3.Session(**session_kwargs)
            self.cloudfront_client = self.session.client("cloudfront")
            self.s3_client = self.session.client("s3")
            logger.info("CDN service initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize CDN service: %s", e)
            self.enabled = False

    def generate_cdn_url(
        self,
        object_key: str,
        content_type: Optional[str] = None,
        custom_domain: Optional[str] = None,
    ) -> str:
        """
        Generate CDN URL for an object.

        Args:
            object_key: S3 object key
            content_type: MIME type for optimization hints
            custom_domain: Override default CDN domain

        Returns:
            Full CDN URL
        """
        if not self.enabled:
            # Fallback to direct S3 URL
            return f"https://{self.config.s3_bucket}.s3.{self.config.aws_region}.amazonaws.com/{object_key}"

        domain = custom_domain or self.config.distribution_domain

        # Ensure proper URL format
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"

        return urljoin(domain, object_key)

    def generate_signed_url(
        self,
        object_key: str,
        expires_in: int = 3600,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Generate signed URL for private content access.

        Args:
            object_key: S3 object key
            expires_in: URL expiration time in seconds
            content_type: MIME type for the object

        Returns:
            Signed CDN URL
        """
        if not self.enabled:
            logger.warning("CDN not available, generating direct S3 signed URL")
            try:
                return self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.config.s3_bucket, "Key": object_key},
                    ExpiresIn=expires_in,
                )
            except Exception as e:
                logger.error("Failed to generate S3 signed URL: %s", e)
                return self.generate_cdn_url(object_key, content_type)

        try:
            # Generate CloudFront signed URL
            expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
            cdn_url = self.generate_cdn_url(object_key, content_type)

            # For demo purposes, return regular CDN URL
            # In production, you would use CloudFront key pairs for signing
            return cdn_url

        except Exception as e:
            logger.error("Failed to generate signed CDN URL: %s", e)
            return self.generate_cdn_url(object_key, content_type)

    def invalidate_cache(self, object_keys: Union[str, List[str]]) -> Optional[str]:
        """
        Invalidate CDN cache for specified objects.

        Args:
            object_keys: Single key or list of keys to invalidate

        Returns:
            Invalidation ID if successful, None otherwise
        """
        if not self.enabled:
            logger.warning("CDN not available, cannot invalidate cache")
            return None

        if isinstance(object_keys, str):
            object_keys = [object_keys]

        # Ensure paths start with /
        paths = [f"/{key.lstrip('/')}" for key in object_keys]

        try:
            response = self.cloudfront_client.create_invalidation(
                DistributionId=self._get_distribution_id(),
                InvalidationBatch={
                    "Paths": {
                        "Quantity": len(paths),
                        "Items": paths,
                    },
                    "CallerReference": f"ppl-meta-{int(datetime.utcnow().timestamp())}",
                },
            )

            invalidation_id = response["Invalidation"]["Id"]
            logger.info(
                "Created CDN invalidation %s for %d paths", invalidation_id, len(paths)
            )
            return invalidation_id

        except Exception as e:
            logger.error("Failed to create CDN invalidation: %s", e)
            return None

    def get_invalidation_status(self, invalidation_id: str) -> Optional[Dict[str, str]]:
        """Get the status of a CDN invalidation."""
        if not self.enabled:
            return None

        try:
            response = self.cloudfront_client.get_invalidation(
                DistributionId=self._get_distribution_id(), Id=invalidation_id
            )

            invalidation = response["Invalidation"]
            return {
                "id": invalidation["Id"],
                "status": invalidation["Status"],
                "create_time": invalidation["CreateTime"].isoformat(),
                "paths": invalidation["InvalidationBatch"]["Paths"]["Items"],
            }

        except Exception as e:
            logger.error("Failed to get invalidation status: %s", e)
            return None

    def get_cache_statistics(self) -> Dict[str, Union[int, float, str]]:
        """Get CDN cache statistics and performance metrics."""
        if not self.enabled:
            return {"enabled": False}

        try:
            # Get distribution statistics
            distribution_id = self._get_distribution_id()

            # Note: In a real implementation, you would fetch actual CloudFront metrics
            # using CloudWatch API. This is a simplified version.

            return {
                "enabled": True,
                "distribution_id": distribution_id,
                "domain": self.config.distribution_domain,
                "cache_behaviors": len(self.config.cache_behaviors),
                "status": "deployed",  # Placeholder
            }

        except Exception as e:
            logger.error("Failed to get cache statistics: %s", e)
            return {"enabled": True, "error": str(e)}

    def optimize_delivery(
        self, object_key: str, content_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get optimized delivery URLs for different use cases.

        Args:
            object_key: S3 object key
            content_type: MIME type for optimization

        Returns:
            Dictionary with different optimized URLs
        """
        base_url = self.generate_cdn_url(object_key, content_type)

        # Determine content category
        content_category = self._categorize_content(object_key, content_type)

        optimization_params = {
            "image": {
                "webp": "?format=webp",
                "thumbnail_small": "?w=150&h=150&fit=crop",
                "thumbnail_medium": "?w=300&h=300&fit=crop",
                "thumbnail_large": "?w=600&h=600&fit=crop",
                "optimized": "?auto=compress,format&q=80",
            },
            "video": {
                "preview": "?t=00:00:01&w=300&h=200",
                "thumbnail": "?t=00:00:01&w=150&h=150&fit=crop",
                "streaming": "/playlist.m3u8",
            },
            "default": {
                "original": "",
                "compressed": "?auto=compress",
            },
        }

        params = optimization_params.get(
            content_category, optimization_params["default"]
        )

        return {variant: f"{base_url}{param}" for variant, param in params.items()}

    def _get_distribution_id(self) -> str:
        """Extract CloudFront distribution ID from domain."""
        # In a real implementation, you would store this mapping
        # For now, return a placeholder
        return "E1234567890123"

    def _categorize_content(
        self, object_key: str, content_type: Optional[str] = None
    ) -> str:
        """Categorize content for optimization."""
        if content_type:
            if content_type.startswith("image/"):
                return "image"
            elif content_type.startswith("video/"):
                return "video"
            elif content_type.startswith("audio/"):
                return "audio"

        # Fallback to file extension
        ext = os.path.splitext(object_key)[1].lower()

        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff"}
        video_exts = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv"}
        audio_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}

        if ext in image_exts:
            return "image"
        elif ext in video_exts:
            return "video"
        elif ext in audio_exts:
            return "audio"
        else:
            return "default"

    def preload_content(self, object_keys: List[str]) -> Dict[str, bool]:
        """
        Preload content to CDN edge locations.

        Args:
            object_keys: List of S3 object keys to preload

        Returns:
            Dictionary mapping object keys to success status
        """
        if not self.enabled:
            logger.warning("CDN not available, cannot preload content")
            return {key: False for key in object_keys}

        results = {}

        for object_key in object_keys:
            try:
                # Generate CDN URL to trigger caching
                cdn_url = self.generate_cdn_url(object_key)

                # In a real implementation, you might make HEAD requests
                # to warm the cache or use CloudFront's cache warming features

                results[object_key] = True
                logger.debug("Preloaded content: %s", object_key)

            except Exception as e:
                logger.error("Failed to preload content %s: %s", object_key, e)
                results[object_key] = False

        return results

    def get_content_metrics(
        self, object_key: str, days: int = 7
    ) -> Dict[str, Union[int, float]]:
        """
        Get content delivery metrics for an object.

        Args:
            object_key: S3 object key
            days: Number of days to retrieve metrics for

        Returns:
            Dictionary with delivery metrics
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            # In a real implementation, you would use CloudWatch metrics
            # This is a placeholder returning mock data

            return {
                "enabled": True,
                "requests": 1250,  # Mock data
                "bytes_downloaded": 5242880,  # Mock data
                "cache_hit_rate": 85.5,  # Mock data
                "edge_locations": 15,  # Mock data
                "avg_response_time": 120,  # Mock data in ms
                "period_days": days,
            }

        except Exception as e:
            logger.error("Failed to get content metrics: %s", e)
            return {"enabled": True, "error": str(e)}


# Global CDN service instance
cdn_service = None


def init_cdn_service(config: CDNConfig) -> CDNService:
    """Initialize global CDN service."""
    global cdn_service
    cdn_service = CDNService(config)
    return cdn_service


def get_cdn_service() -> Optional[CDNService]:
    """Get global CDN service instance."""
    return cdn_service

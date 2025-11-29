"""
Media Client

HTTP client for communicating with Media service to fetch media metadata
(photos, videos).

Author: PPL Meta Platform
Date: November 29, 2025
Version: 1.0.0
"""

import logging
import httpx
import os
from typing import Optional, Dict, Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Media service configuration
MEDIA_BASE_URL = os.getenv("PPL_MEDIA_URL", "http://localhost:8000")
MEDIA_TIMEOUT = 30.0  # seconds


class MediaClient:
    """
    HTTP client for Media service.
    
    **Service Architecture:**
    vmeta service → Media service → Media metadata (photos, videos)
    """
    
    def __init__(
        self,
        base_url: str = MEDIA_BASE_URL,
        timeout: float = MEDIA_TIMEOUT,
        auth_token: Optional[str] = None
    ):
        """
        Initialize Media client.
        
        Args:
            base_url: Media service base URL
            timeout: Request timeout in seconds
            auth_token: Optional Bearer token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auth_token = auth_token
        
        # Prepare headers
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers
        )
        logger.info(f"MediaClient initialized: {self.base_url}")
    
    async def get_media_metadata(
        self,
        media_uuid: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a media (photo or video).
        
        **Endpoint:** GET /api/v1/media/{uuid}
        
        Args:
            media_uuid: Media UUID
            
        Returns:
            Dict with media metadata or None if not found
            
        Response format (from Media service):
        {
            "uuid": "...",
            "media_type": "video" | "picture",  # Normalize to "video" | "photo"
            "filename": "...",
            "file_size": 1234567,
            "created_at": "2025-11-29T10:15:00Z",
            "duration": 45.5  # seconds, may be null for photos
        }
        
        Normalized response:
        {
            "uuid": "...",
            "type": "photo" | "video",  # Normalized from media_type
            "filename": "...",
            "timestamp": "...",  # From created_at or capture_timestamp
            "duration": 0 | float,  # 0 for photos
            "file_size": int
        }
        """
        try:
            response = await self.client.get(
                f"/api/v1/media/{media_uuid}"
            )
            response.raise_for_status()
            
            raw_data = response.json()
            
            # Normalize Media service response to expected format
            media_type = raw_data.get('media_type', '').lower()
            normalized_type = 'photo' if media_type in ['picture', 'image'] else 'video'
            
            data = {
                'uuid': raw_data.get('uuid'),
                'type': normalized_type,
                'filename': raw_data.get('filename'),
                'timestamp': raw_data.get('capture_timestamp') or raw_data.get('created_at'),
                'duration': raw_data.get('duration', 0) or 0,
                'file_size': raw_data.get('file_size', 0)
            }
            
            logger.info(
                f"Retrieved metadata for media {media_uuid}: "
                f"type={data['type']}, "
                f"duration={data.get('duration', 0)}s"
            )
            return data
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Media not found: {media_uuid}")
                return None
            logger.error(
                f"HTTP error getting media metadata for {media_uuid}: "
                f"{e.response.status_code}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error getting media metadata for {media_uuid}: {e}"
            )
            return None
    
    async def get_media_type(
        self,
        media_uuid: UUID
    ) -> Optional[str]:
        """
        Get media type (photo or video).
        
        Args:
            media_uuid: Media UUID
            
        Returns:
            "photo", "video", or None if not found
        """
        metadata = await self.get_media_metadata(media_uuid)
        if metadata:
            return metadata.get('type')
        return None
    
    async def batch_get_media_metadata(
        self,
        media_uuids: list[UUID]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for multiple media in batch.
        
        Args:
            media_uuids: List of media UUIDs
            
        Returns:
            Dict mapping media_uuid (str) to metadata
        """
        results = {}
        
        # TODO: If Media service supports batch endpoint, use it
        # For now, fetch individually
        for media_uuid in media_uuids:
            metadata = await self.get_media_metadata(media_uuid)
            if metadata:
                results[str(media_uuid)] = metadata
        
        logger.info(
            f"Batch fetched metadata for {len(results)}/{len(media_uuids)} media"
        )
        return results
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("MediaClient closed")


# Note: Singleton pattern removed - create instances with auth tokens as needed

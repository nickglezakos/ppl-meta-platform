"""Redis client for caching MVR search results."""
import redis.asyncio as redis
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
import logging
import os
import hashlib

logger = logging.getLogger(__name__)


class VMetaCacheClient:
    """Async Redis cache client for VMeta MVR search results."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache client.
        
        Args:
            redis_url: Redis connection URL (default: from env or localhost)
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379"
        )
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection."""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            logger.info(f"✅ VMeta Redis cache connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            # Don't raise - allow graceful degradation
            self.client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            try:
                await self.client.close()
                logger.info("VMeta Redis cache disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Redis: {e}")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self.client is not None
    
    @property
    def redis(self):
        """Property to access the Redis client directly."""
        return self.client
    
    def _generate_cache_key(
        self,
        video_uuids: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> str:
        """
        Generate a deterministic cache key from search parameters.
        
        Args:
            video_uuids: List of video UUIDs
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Result limit
        
        Returns:
            Cache key string
        """
        # Sort video UUIDs for consistency
        sorted_videos = sorted(video_uuids)
        
        # Create hash of video UUIDs (to keep key length manageable)
        videos_str = ",".join(sorted_videos)
        videos_hash = hashlib.md5(videos_str.encode()).hexdigest()[:12]
        
        # Format timestamps
        start_str = start_time.isoformat() if start_time else "none"
        end_str = end_time.isoformat() if end_time else "none"
        
        # Build key
        key = f"mvr_search:v2:{videos_hash}:{start_str}:{end_str}:{limit}"
        return key
    
    async def get_mvr_search_results(
        self,
        video_uuids: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached MVR search results.
        
        Args:
            video_uuids: List of video UUIDs
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Result limit
        
        Returns:
            Cached search results or None if not found
        """
        if not self.is_connected():
            logger.debug("Redis not connected, cache disabled")
            return None
        
        key = self._generate_cache_key(video_uuids, start_time, end_time, limit)
        
        try:
            cached_data = await self.client.get(key)
            if cached_data:
                logger.info(
                    f"📦 Cache HIT for MVR search: {len(video_uuids)} videos, "
                    f"key: {key[:50]}..."
                )
                return json.loads(cached_data)
            
            logger.debug(f"❌ Cache MISS for key: {key[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Redis GET error for {key}: {e}")
            return None
    
    async def set_mvr_search_results(
        self,
        video_uuids: List[str],
        results: Dict[str, Any],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        ttl: int = 3600  # 1 hour default
    ) -> bool:
        """
        Cache MVR search results.
        
        Args:
            video_uuids: List of video UUIDs
            results: Search results to cache
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Result limit
            ttl: Time-to-live in seconds (default: 3600 = 1 hour)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.debug("Redis not connected, skipping cache")
            return False
        
        key = self._generate_cache_key(video_uuids, start_time, end_time, limit)
        
        # Add cache metadata
        cache_data = {
            **results,
            "cached_at": datetime.now().isoformat(),
            "cache_ttl": ttl
        }
        
        try:
            await self.client.setex(
                key,
                ttl,
                json.dumps(cache_data, default=str)  # default=str handles datetime serialization
            )
            logger.info(
                f"💾 Cache SET for MVR search: {len(video_uuids)} videos, "
                f"TTL: {ttl}s, key: {key[:50]}..."
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET error for {key}: {e}")
            return False
    
    async def invalidate_mvr_search(
        self,
        video_uuids: Optional[List[str]] = None,
        pattern: Optional[str] = None
    ) -> int:
        """
        Invalidate cached MVR search results.
        
        Args:
            video_uuids: Specific video UUIDs to invalidate (invalidates all variations)
            pattern: Redis key pattern to match (e.g., "mvr_search:*")
        
        Returns:
            Number of keys deleted
        """
        if not self.is_connected():
            return 0
        
        try:
            deleted_count = 0
            
            if pattern:
                # Delete by pattern
                keys = []
                async for key in self.client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    deleted_count = await self.client.delete(*keys)
                    logger.info(f"🗑️  Invalidated {deleted_count} cache keys matching: {pattern}")
            
            elif video_uuids:
                # Delete all variations for these videos
                # (different time ranges, limits, etc.)
                sorted_videos = sorted(video_uuids)
                videos_str = ",".join(sorted_videos)
                videos_hash = hashlib.md5(videos_str.encode()).hexdigest()[:12]
                pattern = f"mvr_search:{videos_hash}:*"
                
                keys = []
                async for key in self.client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    deleted_count = await self.client.delete(*keys)
                    logger.info(
                        f"🗑️  Invalidated {deleted_count} cache keys for "
                        f"{len(video_uuids)} videos"
                    )
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0


# Global cache client instance
vmeta_cache_client = VMetaCacheClient()

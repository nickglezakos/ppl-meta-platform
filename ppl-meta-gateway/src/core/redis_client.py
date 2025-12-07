"""Redis client for caching camera MVR counts."""
import redis.asyncio as redis
from typing import Optional, Dict, Any
import json
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class CacheClient:
    """Async Redis cache client for MVR counts."""
    
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
            logger.info(f"✅ Redis cache client connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            # Don't raise - allow graceful degradation
            self.client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            try:
                await self.client.close()
                logger.info("Redis cache client disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Redis: {e}")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self.client is not None
    
    @property
    def redis(self):
        """Property to access the Redis client directly."""
        return self.client
    
    async def get_camera_mvr_count(
        self, 
        camera_id: str, 
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached MVR count for a camera.
        
        Args:
            camera_id: Camera device ID
            date: Date in YYYY-MM-DD format (default: today)
        
        Returns:
            Cached count data or None if not found
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot get cache")
            return None
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        key = f"mvr_count:{camera_id}:{date}"
        
        try:
            cached_data = await self.client.get(key)
            if cached_data:
                logger.debug(f"📦 Cache HIT for {key}")
                return json.loads(cached_data)
            
            logger.debug(f"❌ Cache MISS for {key}")
            return None
        except Exception as e:
            logger.error(f"Redis GET error for {key}: {e}")
            return None
    
    async def set_camera_mvr_count(
        self,
        camera_id: str,
        count: int,
        video_count: int,
        date: Optional[str] = None,
        ttl: int = 600  # 10 minutes
    ) -> bool:
        """
        Cache MVR count for a camera.
        
        Args:
            camera_id: Camera device ID
            count: Number of unique MVR people
            video_count: Number of videos processed
            date: Date in YYYY-MM-DD format (default: today)
            ttl: Time-to-live in seconds (default: 600 = 10 minutes)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot set cache")
            return False
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        key = f"mvr_count:{camera_id}:{date}"
        
        data = {
            "count": count,
            "video_count": video_count,
            "cached_at": datetime.now().isoformat(),
            "date": date,
            "camera_id": camera_id
        }
        
        try:
            await self.client.setex(
                key,
                ttl,
                json.dumps(data)
            )
            logger.info(
                f"💾 Cache SET for {key}: {count} people, "
                f"{video_count} videos (TTL: {ttl}s)"
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET error for {key}: {e}")
            return False
    
    async def delete_camera_mvr_count(
        self,
        camera_id: str,
        date: Optional[str] = None
    ) -> bool:
        """
        Invalidate cached count for a camera.
        
        Args:
            camera_id: Camera device ID
            date: Date in YYYY-MM-DD format (default: today)
        
        Returns:
            True if deleted, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot delete cache")
            return False
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        key = f"mvr_count:{camera_id}:{date}"
        
        try:
            result = await self.client.delete(key)
            logger.info(f"🗑️  Cache DELETE for {key}: {result}")
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for {key}: {e}")
            return False
    
    async def get_all_camera_counts(self, date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached camera counts for a date.
        
        Args:
            date: Date in YYYY-MM-DD format (default: today)
        
        Returns:
            Dict of camera_id -> count data
        """
        if not self.is_connected():
            return {}
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        pattern = f"mvr_count:*:{date}"
        
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            
            if not keys:
                return {}
            
            # Get all values
            values = await self.client.mget(keys)
            
            # Build result dict
            result = {}
            for key, value in zip(keys, values):
                if value:
                    # Extract camera_id from key: mvr_count:{camera_id}:{date}
                    camera_id = key.split(":")[1]
                    result[camera_id] = json.loads(value)
            
            logger.info(f"Retrieved {len(result)} cached camera counts for {date}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting all camera counts: {e}")
            return {}


# Global cache client instance
cache_client = CacheClient()

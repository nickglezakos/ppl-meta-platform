"""
Redis caching service for workflow dashboard performance optimization.
Implements 60-second TTL caching for summary metrics.
"""

import json
import logging
import os
from datetime import timedelta
from typing import Any, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service with fallback to in-memory dict."""
    
    def __init__(self, host: str = None, port: int = None, db: int = 0, password: str = None):
        """Initialize cache service with Redis connection."""
        # Get Redis config from environment or use defaults
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', '6379'))
        self.db = db
        self.password = password or os.getenv('REDIS_PASSWORD')
        
        self.redis_client = None
        self.fallback_cache = {}  # In-memory fallback
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"✅ Redis cache connected: {self.host}:{self.port}")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"⚠️ Redis unavailable, using in-memory fallback: {e}")
                self.redis_client = None
        else:
            logger.warning("⚠️ Redis module not installed, using in-memory fallback")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data by key."""
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    logger.debug(f"Cache HIT: {key}")
                    return json.loads(data)
                logger.debug(f"Cache MISS: {key}")
                return None
            except Exception as e:
                logger.error(f"Redis GET error for key '{key}': {e}")
                return self.fallback_cache.get(key)
        else:
            # Fallback to in-memory dict
            return self.fallback_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 60):
        """Set cached data with TTL in seconds."""
        if self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    timedelta(seconds=ttl),
                    json.dumps(value, default=str)
                )
                logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.error(f"Redis SET error for key '{key}': {e}")
                self.fallback_cache[key] = value
                return False
        else:
            # Fallback to in-memory dict (no TTL support)
            self.fallback_cache[key] = value
            return True
    
    def delete(self, key: str):
        """Delete cached data by key."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                logger.debug(f"Cache DELETE: {key}")
                return True
            except Exception as e:
                logger.error(f"Redis DELETE error for key '{key}': {e}")
                self.fallback_cache.pop(key, None)
                return False
        else:
            self.fallback_cache.pop(key, None)
            return True
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern (e.g., 'workflow_*')."""
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Cache CLEAR: {len(keys)} keys matching '{pattern}'")
                return True
            except Exception as e:
                logger.error(f"Redis CLEAR_PATTERN error for '{pattern}': {e}")
                return False
        else:
            # Fallback: clear matching keys from dict
            keys_to_delete = [k for k in self.fallback_cache.keys() if pattern.replace('*', '') in k]
            for k in keys_to_delete:
                self.fallback_cache.pop(k, None)
            logger.info(f"In-memory cache cleared: {len(keys_to_delete)} keys")
            return True
    
    def health_check(self) -> dict:
        """Check cache service health."""
        if self.redis_client:
            try:
                self.redis_client.ping()
                info = self.redis_client.info('memory')
                return {
                    "status": "healthy",
                    "backend": "redis",
                    "memory_used": info.get('used_memory_human', 'unknown'),
                    "connected": True
                }
            except Exception as e:
                return {
                    "status": "degraded",
                    "backend": "in-memory",
                    "error": str(e),
                    "connected": False
                }
        else:
            return {
                "status": "degraded",
                "backend": "in-memory",
                "cache_size": len(self.fallback_cache),
                "connected": False
            }


# Global cache service instance
cache_service = CacheService()

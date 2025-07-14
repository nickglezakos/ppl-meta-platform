"""
Redis-based caching service for PPL Meta Platform.
Implements comprehensive caching strategies for frequently accessed data.
"""

import json
import logging
import pickle
import time
from functools import wraps
from hashlib import md5
from typing import Any, Dict, List, Optional, Union

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for performance optimization."""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        default_ttl: int = 3600,  # 1 hour
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.default_ttl = default_ttl
        self.redis_client = None
        self.is_connected = False

        self._connect()

    def _connect(self) -> bool:
        """Establish Redis connection with error handling."""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            return True

        except (ConnectionError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            return False

    def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active, reconnect if necessary."""
        if not self.is_connected:
            return self._connect()

        try:
            self.redis_client.ping()
            return True
        except (ConnectionError, RedisError):
            logger.warning("Redis connection lost, attempting to reconnect...")
            return self._connect()

    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage."""
        try:
            # Use JSON for simple types, pickle for complex objects
            if isinstance(data, (str, int, float, bool, list, dict)):
                return json.dumps(data).encode("utf-8")
            else:
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Error serializing data: {e}")
            return b""

    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis storage."""
        try:
            # Try JSON first
            try:
                return json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error deserializing data: {e}")
            return None

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key from arguments."""
        key_parts = [str(prefix)]

        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(
                    md5(json.dumps(arg, sort_keys=True).encode()).hexdigest()[:8]
                )
            else:
                key_parts.append(str(arg))

        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = md5(
                json.dumps(sorted_kwargs, sort_keys=True).encode()
            ).hexdigest()[:8]
            key_parts.append(kwargs_str)

        return ":".join(key_parts)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._ensure_connection():
            return None

        try:
            data = self.redis_client.get(key)
            if data is None:
                return None

            return self._deserialize_data(data)
        except RedisError as e:
            logger.error(f"Error getting cache key '{key}': {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        """
        if not self._ensure_connection():
            return False

        try:
            serialized_data = self._serialize_data(value)
            if not serialized_data:
                return False

            ttl = ttl or self.default_ttl

            return self.redis_client.set(key, serialized_data, ex=ttl, nx=nx, xx=xx)
        except RedisError as e:
            logger.error(f"Error setting cache key '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete keys from cache."""
        if not self._ensure_connection():
            return 0

        try:
            return self.redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error deleting cache keys: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._ensure_connection():
            return False

        try:
            return bool(self.redis_client.exists(key))
        except RedisError as e:
            logger.error(f"Error checking cache key existence '{key}': {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for existing key."""
        if not self._ensure_connection():
            return False

        try:
            return bool(self.redis_client.expire(key, ttl))
        except RedisError as e:
            logger.error(f"Error setting expiration for key '{key}': {e}")
            return False

    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._ensure_connection():
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Error flushing pattern '{pattern}': {e}")
            return 0

    def cache_search_results(
        self,
        search_params: Dict[str, Any],
        results: List[Dict],
        ttl: int = 300,  # 5 minutes for search results
    ) -> bool:
        """Cache search results with automatic key generation."""
        cache_key = self._generate_cache_key("search", **search_params)
        return self.set(cache_key, results, ttl=ttl)

    def get_cached_search_results(
        self, search_params: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """Get cached search results."""
        cache_key = self._generate_cache_key("search", **search_params)
        return self.get(cache_key)

    def cache_media_metadata(
        self, media_id: str, metadata: Dict[str, Any], ttl: int = 1800
    ) -> bool:
        """Cache media metadata (30 minutes TTL)."""
        cache_key = f"media:metadata:{media_id}"
        return self.set(cache_key, metadata, ttl=ttl)

    def get_cached_media_metadata(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get cached media metadata."""
        cache_key = f"media:metadata:{media_id}"
        return self.get(cache_key)

    def cache_analytics_data(
        self,
        analytics_type: str,
        params: Dict[str, Any],
        data: Dict[str, Any],
        ttl: int = 900,  # 15 minutes for analytics
    ) -> bool:
        """Cache analytics data."""
        cache_key = self._generate_cache_key(f"analytics:{analytics_type}", **params)
        return self.set(cache_key, data, ttl=ttl)

    def get_cached_analytics_data(
        self, analytics_type: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached analytics data."""
        cache_key = self._generate_cache_key(f"analytics:{analytics_type}", **params)
        return self.get(cache_key)

    def cache_collection_data(
        self, collection_id: str, data: Dict[str, Any], ttl: int = 600
    ) -> bool:
        """Cache collection data (10 minutes TTL)."""
        cache_key = f"collection:{collection_id}"
        return self.set(cache_key, data, ttl=ttl)

    def get_cached_collection_data(
        self, collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached collection data."""
        cache_key = f"collection:{collection_id}"
        return self.get(cache_key)

    def invalidate_media_cache(self, media_id: str) -> int:
        """Invalidate all cache entries related to a media item."""
        patterns = [
            f"media:metadata:{media_id}",
            f"search:*",  # Invalidate all search results as they might include this media
            f"analytics:*",  # Invalidate analytics as they might be affected
        ]

        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.flush_pattern(pattern)

        return total_deleted

    def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries related to a user."""
        patterns = [
            f"search:*uploaded_by*{user_id}*",
            f"analytics:*user*{user_id}*",
            f"collection:*",  # Collections might be affected
        ]

        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.flush_pattern(pattern)

        return total_deleted

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if not self._ensure_connection():
            return {}

        try:
            info = self.redis_client.info()

            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "expired_keys": info.get("expired_keys", 0),
                "evicted_keys": info.get("evicted_keys", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(
                        info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
                    )
                )
                * 100,
                "is_connected": self.is_connected,
            }
        except RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"is_connected": False, "error": str(e)}


def cached(
    ttl: int = 3600,
    key_prefix: str = "cached",
    cache_service: Optional[CacheService] = None,
):
    """
    Decorator for caching function results.

    Args:
        ttl: Cache time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_service: CacheService instance (will use global instance if None)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if no cache service available
            service = cache_service or getattr(wrapper, "_cache_service", None)
            if not service or not service.is_connected:
                return func(*args, **kwargs)

            # Generate cache key
            cache_key = service._generate_cache_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )

            # Try to get from cache
            cached_result = service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            service.set(cache_key, result, ttl=ttl)
            logger.debug(f"Cache miss for {func.__name__}, result cached")

            return result

        # Allow setting cache service on the wrapper
        wrapper._cache_service = cache_service
        return wrapper

    return decorator


# Global cache service instance
cache_service = None


def init_cache_service(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    default_ttl: int = 3600,
) -> CacheService:
    """Initialize global cache service."""
    global cache_service
    cache_service = CacheService(
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        redis_password=redis_password,
        default_ttl=default_ttl,
    )
    return cache_service


def get_cache_service() -> Optional[CacheService]:
    """Get global cache service instance."""
    return cache_service

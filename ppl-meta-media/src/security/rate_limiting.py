"""
Rate Limiting Service for PPL Meta Media Service.
Provides Redis-based rate limiting for API endpoints and file uploads.
"""

import json
import logging
import time
from typing import Dict, Optional, Tuple

import redis
from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimitingService:
    """Redis-based rate limiting service."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_limits: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize rate limiting service.

        Args:
            redis_url: Redis connection URL
            default_limits: Default rate limits per endpoint type
        """
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for rate limiting")
        except Exception as e:
            logger.warning("Redis unavailable for rate limiting: %s", e)
            self.redis_client = None

        # Default rate limits (requests per minute)
        self.default_limits = default_limits or {
            "upload": 10,  # 10 uploads per minute
            "api": 100,  # 100 API calls per minute
            "download": 50,  # 50 downloads per minute
            "search": 30,  # 30 searches per minute
            "auth": 5,  # 5 auth attempts per minute
        }

    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier string
        """
        # Try to get user ID from headers first
        user_id = request.headers.get("User-ID")
        if user_id:
            return f"user:{user_id}"

        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    def _get_redis_key(self, client_id: str, endpoint_type: str) -> str:
        """
        Generate Redis key for rate limiting.

        Args:
            client_id: Client identifier
            endpoint_type: Type of endpoint (upload, api, etc.)

        Returns:
            Redis key string
        """
        # Include current minute in key for automatic expiration
        current_minute = int(time.time() // 60)
        return f"rate_limit:{endpoint_type}:{client_id}:{current_minute}"

    def check_rate_limit(
        self, request: Request, endpoint_type: str, custom_limit: Optional[int] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limits.

        Args:
            request: FastAPI request object
            endpoint_type: Type of endpoint being accessed
            custom_limit: Custom rate limit for this check

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if not self.redis_client:
            # If Redis unavailable, allow all requests
            return True, {
                "allowed": True,
                "limit": None,
                "remaining": None,
                "reset_time": None,
                "message": "Rate limiting unavailable",
            }

        client_id = self._get_client_id(request)
        redis_key = self._get_redis_key(client_id, endpoint_type)

        # Get rate limit for this endpoint type
        rate_limit = custom_limit or self.default_limits.get(endpoint_type, 100)

        try:
            # Get current request count
            current_count = self.redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0

            # Calculate reset time (next minute)
            current_time = time.time()
            next_minute = int((current_time // 60) + 1) * 60
            reset_time = next_minute

            # Check if limit exceeded
            if current_count >= rate_limit:
                return False, {
                    "allowed": False,
                    "limit": rate_limit,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "current_count": current_count,
                    "message": f"Rate limit exceeded for {endpoint_type}",
                }

            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 120)  # Keep for 2 minutes for safety
            pipe.execute()

            remaining = rate_limit - (current_count + 1)

            return True, {
                "allowed": True,
                "limit": rate_limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count + 1,
                "message": "Within rate limits",
            }

        except Exception as e:
            logger.error("Rate limiting check failed: %s", e)
            # On error, allow the request
            return True, {
                "allowed": True,
                "limit": rate_limit,
                "remaining": None,
                "reset_time": None,
                "message": "Rate limiting check failed",
            }

    def enforce_rate_limit(
        self, request: Request, endpoint_type: str, custom_limit: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Enforce rate limit, raising HTTPException if exceeded.

        Args:
            request: FastAPI request object
            endpoint_type: Type of endpoint being accessed
            custom_limit: Custom rate limit for this check

        Returns:
            Rate limit information

        Raises:
            HTTPException: If rate limit is exceeded
        """
        allowed, rate_info = self.check_rate_limit(request, endpoint_type, custom_limit)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": rate_info["message"],
                    "limit": rate_info["limit"],
                    "reset_time": rate_info["reset_time"],
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset_time"]),
                    "Retry-After": "60",
                },
            )

        return rate_info

    def get_rate_limit_headers(self, rate_info: Dict[str, any]) -> Dict[str, str]:
        """
        Generate rate limit headers for response.

        Args:
            rate_info: Rate limit information from check

        Returns:
            Dictionary of headers to add to response
        """
        headers = {}

        if rate_info.get("limit") is not None:
            headers["X-RateLimit-Limit"] = str(rate_info["limit"])

        if rate_info.get("remaining") is not None:
            headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])

        if rate_info.get("reset_time") is not None:
            headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])

        return headers

    def clear_rate_limit(self, client_id: str, endpoint_type: str) -> bool:
        """
        Clear rate limit for specific client and endpoint.

        Args:
            client_id: Client identifier
            endpoint_type: Type of endpoint

        Returns:
            True if cleared successfully
        """
        if not self.redis_client:
            return False

        try:
            current_minute = int(time.time() // 60)
            redis_key = f"rate_limit:{endpoint_type}:{client_id}:{current_minute}"
            self.redis_client.delete(redis_key)
            return True
        except Exception as e:
            logger.error("Failed to clear rate limit: %s", e)
            return False

    def get_client_stats(self, client_id: str) -> Dict[str, any]:
        """
        Get rate limiting statistics for a client.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary with client rate limiting stats
        """
        if not self.redis_client:
            return {"error": "Redis unavailable"}

        stats = {}
        current_minute = int(time.time() // 60)

        for endpoint_type in self.default_limits.keys():
            redis_key = f"rate_limit:{endpoint_type}:{client_id}:{current_minute}"
            try:
                current_count = self.redis_client.get(redis_key)
                current_count = int(current_count) if current_count else 0
                limit = self.default_limits[endpoint_type]

                stats[endpoint_type] = {
                    "current_count": current_count,
                    "limit": limit,
                    "remaining": limit - current_count,
                    "percentage_used": (current_count / limit) * 100,
                }
            except Exception as e:
                logger.error("Failed to get stats for %s: %s", endpoint_type, e)
                stats[endpoint_type] = {"error": str(e)}

        return stats


def rate_limit_middleware(
    rate_limiter: RateLimitingService,
    endpoint_type: str,
    custom_limit: Optional[int] = None,
):
    """
    Decorator for applying rate limiting to FastAPI endpoints.

    Args:
        rate_limiter: RateLimitingService instance
        endpoint_type: Type of endpoint for rate limiting
        custom_limit: Custom rate limit override

    Returns:
        Decorator function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if request:
                # Check and enforce rate limit
                rate_info = rate_limiter.enforce_rate_limit(
                    request, endpoint_type, custom_limit
                )

                # Add rate limit info to kwargs for endpoint use
                kwargs["rate_limit_info"] = rate_info

            return await func(*args, **kwargs)

        return wrapper

    return decorator

"""
Advanced middleware for the API Gateway with enterprise features
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Callable, Dict, Optional

import redis.asyncio as aioredis
import structlog
from circuitbreaker import CircuitBreaker
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class AdvancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting with Redis backend and multiple strategies."""

    def __init__(
        self,
        app,
        redis_url: str = "redis://localhost:6379",
        default_rate: str = "100/minute",
        strategies: Optional[Dict[str, str]] = None,
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.default_rate = default_rate
        self.strategies = strategies or {
            "/api/v1/auth": "10/minute",
            "/api/v1/register": "5/minute",
            "/api/v1/password": "3/minute",
        }
        self.redis_pool = None
        self.limiter = Limiter(key_func=get_remote_address)

    async def init_redis(self):
        """Initialize Redis connection pool."""
        if not self.redis_pool:
            try:
                self.redis_pool = aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                await self.redis_pool.ping()
                logger.info("Rate limiting Redis connection established")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed, using in-memory rate limiting: {e}"
                )
                self.redis_pool = None

    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if request is within rate limit."""
        if self.redis_pool:
            return await self._check_redis_rate_limit(key, limit, window)
        else:
            return await self._check_memory_rate_limit(key, limit, window)

    async def _check_redis_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Redis-based rate limiting with sliding window."""
        try:
            current_time = time.time()
            pipe = self.redis_pool.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, current_time - window)
            # Add current request
            pipe.zadd(key, {str(uuid.uuid4()): current_time})
            # Count requests in window
            pipe.zcard(key)
            # Set expiry
            pipe.expire(key, window)

            results = await pipe.execute()
            request_count = results[2]

            return request_count <= limit
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True  # Fail open

    # In-memory fallback with simple sliding window
    _memory_store = defaultdict(lambda: deque())

    async def _check_memory_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Memory-based rate limiting fallback."""
        current_time = time.time()
        requests = self._memory_store[key]

        # Remove old requests
        while requests and requests[0] < current_time - window:
            requests.popleft()

        # Check if under limit
        if len(requests) < limit:
            requests.append(current_time)
            return True

        return False

    def parse_rate(self, rate_string: str) -> tuple[int, int]:
        """Parse rate string like '100/minute' to (limit, window_seconds)."""
        try:
            limit_str, period = rate_string.split("/")
            limit = int(limit_str)

            period_map = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

            window = period_map.get(period, 60)
            return limit, window
        except:
            return 100, 60  # Default fallback

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        if not self.redis_pool:
            await self.init_redis()

        # Determine rate limit for this endpoint
        path = request.url.path
        rate_string = self.default_rate

        # Check for exact match first, then prefix match
        for strategy_path, strategy_rate in self.strategies.items():
            if path == strategy_path or path.startswith(strategy_path):
                rate_string = strategy_rate
                break

        limit, window = self.parse_rate(rate_string)

        # Create rate limit key
        client_ip = get_remote_address(request)
        rate_key = f"rate_limit:{client_ip}:{path}"

        # Check rate limit
        allowed = await self.check_rate_limit(rate_key, limit, window)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=path,
                limit=limit,
                window=window,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": f"{window} seconds",
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Circuit breaker pattern for external service calls."""

    def __init__(
        self,
        app,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: type = Exception,
    ):
        super().__init__(app)
        self.circuit_breakers = {}
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                expected_exception=self.expected_exception,
                name=service_name,
            )
        return self.circuit_breakers[service_name]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply circuit breaker pattern."""
        # Extract target service from headers or path
        target_service = request.headers.get("X-Target-Service")
        if not target_service:
            # Infer from path
            path_parts = request.url.path.strip("/").split("/")
            if len(path_parts) >= 3 and path_parts[0] == "api":
                target_service = path_parts[2]  # e.g., /api/v1/users -> users

        if not target_service:
            return await call_next(request)

        circuit_breaker = self.get_circuit_breaker(target_service)

        try:
            # Wrap the call in circuit breaker
            response = await circuit_breaker.call_async(call_next, request)
            return response
        except Exception as e:
            logger.error(
                "Circuit breaker opened",
                service=target_service,
                error=str(e),
                state=circuit_breaker.current_state,
            )

            if circuit_breaker.current_state == "open":
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Service temporarily unavailable",
                        "service": target_service,
                        "circuit_breaker_state": "open",
                        "retry_after": self.recovery_timeout,
                    },
                    headers={"Retry-After": str(self.recovery_timeout)},
                )

            # Re-raise for other states
            raise


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Distributed request tracing with correlation IDs."""

    def __init__(
        self,
        app,
        trace_header: str = "X-Trace-ID",
        span_header: str = "X-Span-ID",
        parent_span_header: str = "X-Parent-Span-ID",
    ):
        super().__init__(app)
        self.trace_header = trace_header
        self.span_header = span_header
        self.parent_span_header = parent_span_header

    def generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return str(uuid.uuid4())

    def generate_span_id(self) -> str:
        """Generate a unique span ID."""
        return str(uuid.uuid4())[:8]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add distributed tracing to requests."""
        # Get or create trace ID
        trace_id = request.headers.get(self.trace_header) or self.generate_trace_id()

        # Create new span
        span_id = self.generate_span_id()
        parent_span_id = request.headers.get(self.span_header)

        # Add tracing context to request state
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.parent_span_id = parent_span_id

        # Start span timing
        start_time = time.time()

        # Log span start
        logger.info(
            "Span started",
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("User-Agent"),
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log span completion
            logger.info(
                "Span completed",
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add tracing headers to response
            response.headers[self.trace_header] = trace_id
            response.headers[self.span_header] = span_id
            if parent_span_id:
                response.headers[self.parent_span_header] = parent_span_id

            return response

        except Exception as e:
            # Log span error
            duration = time.time() - start_time
            logger.error(
                "Span failed",
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise


class RequestTransformationMiddleware(BaseHTTPMiddleware):
    """Request/Response transformation middleware."""

    def __init__(
        self,
        app,
        request_transformations: Optional[Dict[str, Callable]] = None,
        response_transformations: Optional[Dict[str, Callable]] = None,
    ):
        super().__init__(app)
        self.request_transformations = request_transformations or {}
        self.response_transformations = response_transformations or {}

    async def transform_request(self, request: Request) -> Request:
        """Apply request transformations."""
        path = request.url.path

        # Check if transformation is needed for this path
        for pattern, transformer in self.request_transformations.items():
            if pattern in path:
                try:
                    # Read request body if needed
                    if request.method in ["POST", "PUT", "PATCH"]:
                        body = await request.body()
                        if body:
                            content_type = request.headers.get("content-type", "")

                            # Handle JSON data
                            if "application/json" in content_type:
                                request_data = json.loads(body)
                                transformed_data = transformer(request_data)

                                # Create new body with transformed data
                                new_body = json.dumps(transformed_data).encode()

                                # Replace the request body
                                request._body = new_body

                                logger.info(
                                    "Request transformed (JSON)",
                                    path=path,
                                    transformer=transformer.__name__,
                                )
                            # Handle form data
                            elif "application/x-www-form-urlencoded" in content_type:
                                # Parse form data
                                import urllib.parse

                                form_data = urllib.parse.parse_qs(body.decode())
                                # Convert to dict with single values
                                request_data = {
                                    k: v[0] if v else "" for k, v in form_data.items()
                                }
                                transformed_data = transformer(request_data)

                                # Convert back to form data
                                new_form_data = urllib.parse.urlencode(transformed_data)
                                new_body = new_form_data.encode()

                                # Replace the request body
                                request._body = new_body

                                logger.info(
                                    "Request transformed (Form)",
                                    path=path,
                                    transformer=transformer.__name__,
                                )
                            else:
                                # Skip transformation for other content types
                                logger.debug(
                                    f"Skipping transformation for content-type: {content_type}"
                                )

                except Exception as e:
                    logger.error(f"Request transformation failed: {e}")

        return request

    async def transform_response(self, response: Response, path: str) -> Response:
        """Apply response transformations."""
        # Check if transformation is needed for this path
        for pattern, transformer in self.response_transformations.items():
            if pattern in path:
                try:
                    # This is a simplified implementation
                    # Full implementation would need to handle streaming responses
                    logger.info(
                        "Response transformed",
                        path=path,
                        transformer=transformer.__name__,
                    )
                except Exception as e:
                    logger.error(f"Response transformation failed: {e}")

        return response

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply request/response transformations."""
        # Transform request
        request = await self.transform_request(request)

        # Process request
        response = await call_next(request)

        # Transform response
        response = await self.transform_response(response, request.url.path)

        return response


# Example transformation functions
def normalize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Normalize user data format."""
    if "email" in data:
        data["email"] = data["email"].lower().strip()
    if "username" in data:
        data["username"] = data["username"].lower().strip()
    return data


def add_api_version_header(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Add API version to response."""
    response_data["api_version"] = "v1.4.0"
    return response_data

"""
Logging middleware for PPL Meta Media Service.

This middleware provides automatic request/response logging with:
- Request correlation IDs
- Performance timing
- Error tracking
- Request/response size monitoring
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logger import logger, log_api_request, log_api_response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    
    Features:
    - Automatic request ID generation
    - Request/response timing
    - Status code tracking
    - Error logging
    - Request size monitoring
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: list[str] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        """
        Initialize logging middleware.

        Args:
            app: ASGI application
            exclude_paths: List of paths to exclude from logging
            log_request_body: Whether to log request body (default: False)
            log_response_body: Whether to log response body (default: False)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and response with logging.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from the application
        """
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate and attach request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log request
        request_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else None,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_length": request.headers.get("content-length"),
            "content_type": request.headers.get("content-type"),
        }

        # Extract user ID if available
        if hasattr(request.state, "user_id"):
            request_data["user_id"] = request.state.user_id

        logger.info("HTTP request received", **request_data)

        # Process request
        response = None
        error = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            error = e
            logger.error(
                "Request processing failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=e,
            )
            # Re-raise to let FastAPI handle it
            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            response_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            }

            if error:
                response_data["error"] = str(error)
                response_data["error_type"] = type(error).__name__

            if response:
                response_data["response_size"] = response.headers.get("content-length")
                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id

            # Log based on status code
            if status_code >= 500:
                logger.error("HTTP request failed (5xx)", **response_data)
            elif status_code >= 400:
                logger.warning("HTTP request error (4xx)", **response_data)
            elif duration_ms > 5000:  # Slow request threshold
                logger.warning("HTTP request slow", **response_data)
            else:
                logger.info("HTTP request completed", **response_data)

        return response


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging performance metrics.
    
    Tracks slow requests and provides performance insights.
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_threshold_ms: float = 1000.0,
        very_slow_threshold_ms: float = 5000.0,
    ):
        """
        Initialize performance logging middleware.

        Args:
            app: ASGI application
            slow_threshold_ms: Threshold for slow requests in milliseconds
            very_slow_threshold_ms: Threshold for very slow requests in milliseconds
        """
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
        self.very_slow_threshold_ms = very_slow_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with performance tracking.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from the application
        """
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log if request is slow
        if duration_ms > self.very_slow_threshold_ms:
            logger.warning(
                "Very slow request detected",
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.very_slow_threshold_ms,
                severity="high",
            )
        elif duration_ms > self.slow_threshold_ms:
            logger.warning(
                "Slow request detected",
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.slow_threshold_ms,
                severity="medium",
            )

        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive error logging.
    
    Captures and logs all unhandled exceptions with full context.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error logging.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from the application
        """
        try:
            return await call_next(request)
        except Exception as e:
            # Log comprehensive error details
            logger.error(
                "Unhandled exception in request processing",
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params) if request.query_params else None,
                client_ip=request.client.host if request.client else None,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=e,
            )
            raise


__all__ = [
    "LoggingMiddleware",
    "PerformanceLoggingMiddleware",
    "ErrorLoggingMiddleware",
]

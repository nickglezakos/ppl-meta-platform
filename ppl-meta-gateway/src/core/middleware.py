"""
Custom middleware for the API Gateway
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/Response logging middleware."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=str(request.url.path),
            query_params=str(request.url.query) if request.url.query else None,
        )
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            process_time=f"{process_time:.4f}s"
        )
        
        return response


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus metrics middleware."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Basic implementation - can be enhanced with actual Prometheus metrics
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Here you would typically update Prometheus metrics
        # For now, just logging
        logger.debug(
            "Metrics",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration=process_time
        )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Basic implementation - can be enhanced with actual rate limiting
        # For now, just pass through
        response = await call_next(request)
        return response

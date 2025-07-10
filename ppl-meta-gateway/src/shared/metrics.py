"""
Local metrics stub for the gateway service.
"""

import time
from typing import Any, Dict, Optional


class PrometheusMiddleware:
    """Stub metrics middleware for the gateway service."""

    def __init__(self, app, *_args, app_name: str = "gateway", **_kwargs):
        self.app = app
        self.app_name = app_name
        self.request_count = 0
        self.start_time = time.time()

    async def __call__(self, scope, receive, send):
        """Process request and track basic metrics using ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        self.request_count += 1

        try:
            await self.app(scope, receive, send)
        finally:
            # Track duration for future metrics implementation
            _ = time.time() - start_time


def create_metrics_endpoint(*_args, **_kwargs):
    """Create a basic metrics endpoint response (stub implementation)."""
    from fastapi import APIRouter

    print("DEBUG: create_metrics_endpoint called, creating APIRouter")
    router = APIRouter()

    @router.get("/metrics")
    async def get_metrics():
        return {
            "status": "metrics endpoint",
            "service": "ppl-meta-gateway",
            "uptime": time.time()
            - getattr(create_metrics_endpoint, "start_time", time.time()),
        }

    print(f"DEBUG: returning router of type {type(router)}")
    return router


def init_metrics(service_name: str = "unknown", service_version: str = "1.0.0"):
    """Initialize metrics collection (stub implementation)."""
    if not hasattr(create_metrics_endpoint, "start_time"):
        create_metrics_endpoint.start_time = time.time()

    # Return a stub metrics collector
    class StubMetricsCollector:
        def __init__(self):
            self.service_name = service_name
            self.service_version = service_version

        def track_request(self, *args, **kwargs):
            pass

        def track_error(self, *args, **kwargs):
            pass

    return StubMetricsCollector()

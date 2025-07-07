"""
Shared Prometheus metrics module for PPL Meta Platform services.

This module provides a standardized way to collect and expose metrics
across all microservices in the PPL Meta Platform ecosystem.
"""

import os
import threading
import time
from typing import Optional

import psutil
from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)
from prometheus_client.core import CollectorRegistry
from starlette.middleware.base import BaseHTTPMiddleware

# Create a custom registry for each service instance
metrics_registry = CollectorRegistry()

# Common metrics that all services should track
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "service_name"],
    registry=metrics_registry,
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "service_name"],
    registry=metrics_registry,
)

REQUEST_SIZE = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint", "service_name"],
    registry=metrics_registry,
)

RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint", "service_name"],
    registry=metrics_registry,
)

ACTIVE_CONNECTIONS = Gauge(
    "http_active_connections",
    "Number of active HTTP connections",
    ["service_name"],
    registry=metrics_registry,
)

# System metrics
CPU_USAGE = Gauge(
    "system_cpu_usage_percent",
    "Current CPU usage percentage",
    ["service_name"],
    registry=metrics_registry,
)

MEMORY_USAGE = Gauge(
    "system_memory_usage_bytes",
    "Current memory usage in bytes",
    ["service_name"],
    registry=metrics_registry,
)

MEMORY_USAGE_PERCENT = Gauge(
    "system_memory_usage_percent",
    "Current memory usage percentage",
    ["service_name"],
    registry=metrics_registry,
)

DISK_USAGE = Gauge(
    "system_disk_usage_bytes",
    "Current disk usage in bytes",
    ["service_name"],
    registry=metrics_registry,
)

DISK_USAGE_PERCENT = Gauge(
    "system_disk_usage_percent",
    "Current disk usage percentage",
    ["service_name"],
    registry=metrics_registry,
)

# Database metrics
DB_CONNECTIONS = Gauge(
    "database_connections_active",
    "Number of active database connections",
    ["service_name"],
    registry=metrics_registry,
)

DB_QUERY_DURATION = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["service_name", "query_type"],
    registry=metrics_registry,
)

DB_QUERY_COUNT = Counter(
    "database_queries_total",
    "Total database queries",
    ["service_name", "query_type", "status"],
    registry=metrics_registry,
)

# Error metrics
ERROR_COUNT = Counter(
    "errors_total",
    "Total errors",
    ["service_name", "error_type", "endpoint"],
    registry=metrics_registry,
)

# Service info
SERVICE_INFO = Info("service_info", "Service information", registry=metrics_registry)

# Business metrics (service-specific)
BUSINESS_OPERATIONS = Counter(
    "business_operations_total",
    "Total business operations",
    ["service_name", "operation_type", "status"],
    registry=metrics_registry,
)

BUSINESS_OPERATION_DURATION = Histogram(
    "business_operation_duration_seconds",
    "Business operation duration in seconds",
    ["service_name", "operation_type"],
    registry=metrics_registry,
)


class MetricsCollector:
    """Centralized metrics collection and management."""

    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.active_requests = 0
        self.lock = threading.Lock()

        # Set service info
        SERVICE_INFO.info(
            {
                "service_name": service_name,
                "version": service_version,
                "python_version": (
                    f"{os.sys.version_info.major}."
                    f"{os.sys.version_info.minor}."
                    f"{os.sys.version_info.micro}"
                ),
            }
        )

        # Start system metrics collection
        self._start_system_metrics_collection()

    def _start_system_metrics_collection(self):
        """Start periodic system metrics collection."""

        def collect_system_metrics():
            while True:
                try:
                    # CPU metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    CPU_USAGE.labels(service_name=self.service_name).set(cpu_percent)

                    # Memory metrics
                    memory = psutil.virtual_memory()
                    MEMORY_USAGE.labels(service_name=self.service_name).set(memory.used)
                    MEMORY_USAGE_PERCENT.labels(service_name=self.service_name).set(
                        memory.percent
                    )

                    # Disk metrics
                    disk = psutil.disk_usage("/")
                    DISK_USAGE.labels(service_name=self.service_name).set(disk.used)
                    DISK_USAGE_PERCENT.labels(service_name=self.service_name).set(
                        disk.percent
                    )

                    # Active connections
                    with self.lock:
                        ACTIVE_CONNECTIONS.labels(service_name=self.service_name).set(
                            self.active_requests
                        )

                except Exception as e:
                    # Log error but don't crash the thread
                    print(f"Error collecting system metrics: {e}")

                time.sleep(30)  # Collect every 30 seconds

        # Start metrics collection in background thread
        metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
        metrics_thread.start()

    def record_request_start(self, method: str, endpoint: str) -> float:
        """Record the start of a request."""
        with self.lock:
            self.active_requests += 1
        return time.time()

    def record_request_end(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        start_time: float,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Record the end of a request."""
        duration = time.time() - start_time

        with self.lock:
            self.active_requests -= 1

        # Record metrics
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            service_name=self.service_name,
        ).inc()

        REQUEST_DURATION.labels(
            method=method, endpoint=endpoint, service_name=self.service_name
        ).observe(duration)

        if request_size > 0:
            REQUEST_SIZE.labels(
                method=method, endpoint=endpoint, service_name=self.service_name
            ).observe(request_size)

        if response_size > 0:
            RESPONSE_SIZE.labels(
                method=method, endpoint=endpoint, service_name=self.service_name
            ).observe(response_size)

    def record_error(self, error_type: str, endpoint: str = ""):
        """Record an error occurrence."""
        ERROR_COUNT.labels(
            service_name=self.service_name, error_type=error_type, endpoint=endpoint
        ).inc()

    def record_db_query(
        self, query_type: str, duration: float, status: str = "success"
    ):
        """Record a database query."""
        DB_QUERY_COUNT.labels(
            service_name=self.service_name, query_type=query_type, status=status
        ).inc()

        DB_QUERY_DURATION.labels(
            service_name=self.service_name, query_type=query_type
        ).observe(duration)

    def record_business_operation(
        self, operation_type: str, duration: float, status: str = "success"
    ):
        """Record a business operation."""
        BUSINESS_OPERATIONS.labels(
            service_name=self.service_name, operation_type=operation_type, status=status
        ).inc()

        BUSINESS_OPERATION_DURATION.labels(
            service_name=self.service_name, operation_type=operation_type
        ).observe(duration)

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(metrics_registry).decode("utf-8")


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic metrics collection."""

    def __init__(self, app, metrics_collector: MetricsCollector):
        super().__init__(app)
        self.metrics_collector = metrics_collector

    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Get request details
        method = request.method
        endpoint = self._get_endpoint_path(request)

        # Get request size
        request_size = 0
        if hasattr(request, "headers") and "content-length" in request.headers:
            try:
                request_size = int(request.headers["content-length"])
            except (ValueError, KeyError):
                pass

        # Record request start
        start_time = self.metrics_collector.record_request_start(method, endpoint)

        try:
            # Process request
            response = await call_next(request)

            # Get response size
            response_size = 0
            if hasattr(response, "headers") and "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except (ValueError, KeyError):
                    pass

            # Record successful request
            self.metrics_collector.record_request_end(
                method,
                endpoint,
                response.status_code,
                start_time,
                request_size,
                response_size,
            )

            return response

        except Exception as e:
            # Record error
            self.metrics_collector.record_error(
                error_type=type(e).__name__, endpoint=endpoint
            )

            # Record failed request (assuming 500 status)
            self.metrics_collector.record_request_end(
                method, endpoint, 500, start_time, request_size, 0
            )

            raise

    def _get_endpoint_path(self, request: Request) -> str:
        """Get normalized endpoint path for metrics."""
        path = request.url.path

        # Normalize paths with IDs to avoid high cardinality
        import re

        # Replace numeric IDs with placeholder
        path = re.sub(r"/\d+", "/{id}", path)

        # Replace UUIDs with placeholder
        uuid_pattern = (
            r"/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-" r"[a-f0-9]{4}-[a-f0-9]{12}"
        )
        path = re.sub(uuid_pattern, "/{uuid}", path)

        return path


# Global metrics collector instance - to be initialized by each service
metrics_collector: Optional[MetricsCollector] = None


def init_metrics(service_name: str, service_version: str = "1.0.0") -> MetricsCollector:
    """Initialize metrics collection for a service."""
    global metrics_collector
    metrics_collector = MetricsCollector(service_name, service_version)
    return metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the current metrics collector instance."""
    return metrics_collector


def create_metrics_endpoint():
    """Create a FastAPI endpoint for metrics exposure."""
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/metrics")
    async def get_metrics():
        """Prometheus metrics endpoint."""
        if metrics_collector is None:
            return Response(content="Metrics not initialized", status_code=500)

        metrics_data = metrics_collector.get_metrics()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    return router

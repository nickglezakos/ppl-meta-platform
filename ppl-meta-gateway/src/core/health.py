"""
Health check endpoints and monitoring.
"""

import time
from typing import Any, Dict

import httpx
import psutil
from config import settings
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Try to import service discovery client
try:
    from shared.service_discovery import ServiceDiscoveryClient

    service_discovery_available = True
except ImportError:
    service_discovery_available = False

health_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: float
    service: str
    version: str
    environment: str


class DetailedHealthResponse(HealthResponse):
    """Detailed health check response model."""

    uptime: float
    memory: Dict[str, Any]
    cpu_percent: float
    services: Dict[str, str]


# Service start time for uptime calculation
start_time = time.time()


@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
    )


@health_router.get("/health/ready", response_model=DetailedHealthResponse)
async def readiness_check():
    """Readiness probe for Kubernetes."""
    # Check if dependent services are reachable
    services_status = {}

    # Check user management service
    health_url = f"{settings.user_service_url}/health"
    if service_discovery_available:
        # Use service discovery to get service URL, but never let a failure
        # here prevent us from falling back to the direct URL below.
        try:
            service_discovery_client = ServiceDiscoveryClient(
                consul_host=settings.consul_host, consul_port=settings.consul_port
            )
            service_url = await service_discovery_client.get_service_url(
                "ppl-meta-node"
            )
            if service_url:
                health_url = f"{service_url}/health"
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(health_url)
            services_status["user_service"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
    except Exception:
        services_status["user_service"] = "unreachable"

    # Check media service
    health_url = f"{settings.media_service_url}/health"
    if service_discovery_available:
        try:
            service_discovery_client = ServiceDiscoveryClient(
                consul_host=settings.consul_host, consul_port=settings.consul_port
            )
            service_url = await service_discovery_client.get_service_url(
                "ppl-meta-media"
            )
            if service_url:
                health_url = f"{service_url}/health"
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(health_url)
            services_status["media_service"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
    except Exception:
        services_status["media_service"] = "unreachable"


    # Get system metrics
    memory_info = psutil.virtual_memory()

    return DetailedHealthResponse(
        status="ready",
        timestamp=time.time(),
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
        uptime=time.time() - start_time,
        memory={
            "total": memory_info.total,
            "available": memory_info.available,
            "percent": memory_info.percent,
        },
        cpu_percent=psutil.cpu_percent(interval=1),
        services=services_status,
    )


@health_router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return HealthResponse(
        status="alive",
        timestamp=time.time(),
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
    )

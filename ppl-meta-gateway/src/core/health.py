"""
Health check endpoints and monitoring.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import time
import psutil
import httpx

from src.config import settings

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
        environment=settings.environment
    )

@health_router.get("/health/ready", response_model=DetailedHealthResponse)
async def readiness_check():
    """Readiness probe for Kubernetes."""
    # Check if dependent services are reachable
    services_status = {}
    
    # Check user management service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.user_service_url}/health")
            services_status["user_service"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        services_status["user_service"] = "unreachable"
    
    # Check media service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.media_service_url}/health")
            services_status["media_service"] = "healthy" if response.status_code == 200 else "unhealthy"
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
            "percent": memory_info.percent
        },
        cpu_percent=psutil.cpu_percent(interval=1),
        services=services_status
    )

@health_router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return HealthResponse(
        status="alive",
        timestamp=time.time(),
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment
    )

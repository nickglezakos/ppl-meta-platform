"""
Health check endpoints for PPL Meta Cameras microservice.
"""

import time
from datetime import datetime
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Depends
from src.database import check_db_health
from src.security.auth import get_current_user

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""

    # Check database health
    db_health = check_db_health()

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Service uptime (simplified)
    uptime_seconds = time.time() - psutil.boot_time()

    health_status = {
        "service": "ppl-meta-cameras",
        "version": "1.0.0",
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "checks": {
            "database": db_health,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free // (1024 * 1024 * 1024),
            },
        },
    }

    return health_status


@router.get("/detailed", tags=["Health"])
async def detailed_health_check(
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Detailed health check with authentication required."""

    # Basic health info
    basic_health = await health_check()

    # Additional detailed metrics
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    network_info = psutil.net_if_addrs()

    # Camera-specific health checks
    camera_health = {
        "active_sessions": 0,  # TODO: Count from database
        "available_cameras": 0,  # TODO: Count from database
        "connected_cameras": 0,  # TODO: Count from database
        "streaming_sessions": 0,  # TODO: Count active streams
        "recording_sessions": 0,  # TODO: Count active recordings
    }

    detailed_health = {
        **basic_health,
        "detailed_checks": {
            "system": {
                "boot_time": boot_time.isoformat(),
                "network_interfaces": len(network_info),
                "process_count": len(psutil.pids()),
            },
            "cameras": camera_health,
            "user": {
                "user_id": current_user.get("sub", "unknown"),
                "permissions": current_user.get("permissions", []),
                "token_expires": current_user.get("exp", 0),
            },
        },
    }

    return detailed_health


@router.get("/ready", tags=["Health"])
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes-style readiness probe."""

    # Check if service is ready to accept requests
    db_health = check_db_health()

    if db_health["status"] == "healthy":
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": ["database"],
        }
    else:
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "failed_checks": ["database"],
            "error": db_health.get("database", "unknown error"),
        }


@router.get("/live", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes-style liveness probe."""

    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ppl-meta-cameras",
    }

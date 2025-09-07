"""
Health check and monitoring endpoints - API v1.
"""

import time

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.health import HealthResponse

router = APIRouter(tags=["health-v1"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint - v1."""
    return HealthResponse(
        status="healthy", timestamp=time.time(), service="ppl-meta-media"
    )


@router.get("/health/detailed", response_model=dict)
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check including database and system metrics - v1."""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "timestamp": time.time(),
        "service": "ppl-meta-media",
        "version": "v1",
        "database": db_status,
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        },
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe endpoint - v1."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "version": "v1"}
    except Exception:
        return {"status": "not ready", "version": "v1"}, 503


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint - v1."""
    return {"status": "alive", "version": "v1"}

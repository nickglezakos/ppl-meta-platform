"""
Health check endpoint for Communications Service.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db, get_db_info

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Basic health check endpoint.
    Returns service status and database connectivity.
    """
    try:
        # Test database connection
        db_info = get_db_info()
        
        return {
            "status": "healthy",
            "service": "ppl-meta-communications",
            "version": "1.0.0",
            "database": {
                "status": db_info.get("status", "unknown"),
                "database": db_info.get("database", "unknown"),
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "ppl-meta-communications",
            "version": "1.0.0",
            "error": str(e)
        }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check endpoint for Kubernetes.
    Returns whether the service is ready to accept requests.
    """
    try:
        db_info = get_db_info()
        if db_info.get("status") == "connected":
            return {"status": "ready", "service": "ppl-meta-communications"}
        else:
            return {"status": "not ready", "service": "ppl-meta-communications", "reason": "database not connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "service": "ppl-meta-communications", "error": str(e)}


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes.
    Returns whether the service is alive (can be restarted if this fails).
    """
    return {"status": "alive", "service": "ppl-meta-communications"}

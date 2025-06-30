"""
Core API endpoints - API v1.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.services.core import CoreService
from typing import Dict, Any

router = APIRouter(prefix="/core", tags=["core-v1"])

@router.get("/info", response_model=Dict[str, Any])
async def get_service_info(db: Session = Depends(get_db)):
    """Get service information - v1."""
    service = CoreService(db)
    info = await service.get_service_info()
    info["api_version"] = "v1"
    return info

@router.get("/status")
async def get_service_status():
    """Get service operational status - v1."""
    return {
        "service": "ppl-meta-media",
        "api_version": "v1",
        "status": "operational",
        "features": [
            "health_monitoring",
            "database_integration", 
            "microservice_ready",
            "nuitka_compatible"
        ]
    }

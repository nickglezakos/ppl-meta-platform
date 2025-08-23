"""
Health check endpoints for PPL Meta Mini.
"""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "ppl-meta-mini",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "core_algorithms": "operational",
                "visualization_engine": "operational",
            },
        },
    )


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with system information."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "ppl-meta-mini",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "algorithms": {
                    "face_grouping": "ready",
                    "trajectory_analysis": "ready",
                    "3d_visualization": "ready",
                },
                "endpoints": {
                    "analytics": "/api/v1/analytics",
                    "health": "/health",
                    "docs": "/docs",
                },
            },
            "capabilities": [
                "advanced_face_grouping",
                "trajectory_visualization",
                "3d_plotting",
                "coordinate_analysis",
            ],
        },
    )

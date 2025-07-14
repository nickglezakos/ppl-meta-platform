"""
API v1 routes aggregation.
"""

from fastapi import APIRouter

from .core import router as core_router
from .health import router as health_router
from .media import router as media_router
from .security import router as security_router
from .user import router as user_router

# Create v1 API router
v1_router = APIRouter(prefix="/api/v1")

# Include all v1 routers
v1_router.include_router(health_router)
v1_router.include_router(core_router)
v1_router.include_router(user_router)
v1_router.include_router(media_router)
v1_router.include_router(security_router)

__all__ = ["v1_router"]

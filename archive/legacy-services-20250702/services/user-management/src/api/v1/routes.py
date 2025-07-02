"""API v1 routes aggregation."""

from fastapi import APIRouter
from src.api.v1 import users, health

router = APIRouter()

# Include v1 routers
router.include_router(users.router)
router.include_router(health.router)

"""API v1 routes aggregation."""

from fastapi import APIRouter
from src.api import licences
from src.api.v1 import health, users

router = APIRouter()

# Include v1 routers
router.include_router(users.router)
router.include_router(health.router)

# Include licensing router on both legacy and versioned paths.
router.include_router(licences.router)
router.include_router(licences.router, prefix="/api/v1")

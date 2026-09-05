"""API v1 routes aggregation."""

from fastapi import APIRouter
from src.api import capabilities, licences, roles
from src.api.v1 import health, users, vpn

router = APIRouter()

# Include v1 routers
router.include_router(users.router)
router.include_router(health.router)
router.include_router(vpn.router)
# Variant A: leaf-facing GET /api/v1/vpn/local-ip (no /node prefix).
router.include_router(vpn.leaf_router)

# Include roles router on versioned path only (legacy /roles is in main.py).
router.include_router(roles.router, prefix="/api/v1")

# Include capabilities router on versioned path only (legacy /capabilities is in main.py).
router.include_router(capabilities.router, prefix="/api/v1")

# Include licensing router on both legacy and versioned paths.
router.include_router(licences.router)
router.include_router(licences.router, prefix="/api/v1")

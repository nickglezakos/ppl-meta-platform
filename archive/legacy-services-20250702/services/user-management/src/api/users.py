"""
LEGACY USERS API - Backward Compatibility

This module provides backward compatibility for existing API consumers.
New implementations should use the v1 API at /api/v1/users/

This file imports and re-exports the v1 users router with legacy prefixes.
"""

from src.api.v1.users import router as v1_users_router
from fastapi import APIRouter

# Create legacy router with old prefix
router = APIRouter(prefix="/users", tags=["users-legacy"])

# Re-export all v1 routes with legacy prefix
for route in v1_users_router.routes:
    if hasattr(route, 'path') and route.path.startswith('/api/v1/users'):
        legacy_path = route.path.replace('/api/v1/users', '')
        if legacy_path == '':
            legacy_path = '/'
        
        # Add the route with legacy path
        router.add_api_route(
            legacy_path,
            route.endpoint,
            methods=route.methods,
            response_model=getattr(route, 'response_model', None),
            tags=["users-legacy"],
            dependencies=getattr(route, 'dependencies', [])
        )



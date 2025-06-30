"""Legacy API routes for backward compatibility."""

from fastapi import APIRouter
from src.api.v1.users import router as users_v1_router
from src.api.v1.health import router as health_v1_router

# Legacy routes (without versioning) for backward compatibility
legacy_users_router = APIRouter(prefix="/users", tags=["users-legacy"])
legacy_health_router = APIRouter(prefix="/health", tags=["health-legacy"])

# Copy all routes from v1 but with legacy prefixes
for route in users_v1_router.routes:
    if hasattr(route, 'path') and route.path.startswith('/api/v1/users'):
        legacy_path = route.path.replace('/api/v1/users', '')
        if legacy_path == '':
            legacy_path = '/'
        # Create a new route with the legacy path
        legacy_users_router.add_api_route(
            legacy_path,
            route.endpoint,
            methods=route.methods,
            response_model=getattr(route, 'response_model', None),
            tags=["users-legacy"]
        )

for route in health_v1_router.routes:
    if hasattr(route, 'path') and route.path.startswith('/api/v1/health'):
        legacy_path = route.path.replace('/api/v1/health', '')
        if legacy_path == '':
            legacy_path = '/'
        # Create a new route with the legacy path
        legacy_health_router.add_api_route(
            legacy_path,
            route.endpoint,
            methods=route.methods,
            response_model=getattr(route, 'response_model', None),
            tags=["health-legacy"]
        )

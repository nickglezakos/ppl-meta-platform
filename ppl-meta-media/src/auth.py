"""
Authentication and authorization dependencies for FastAPI.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.config import settings
from src.services.user_service import user_service_client

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()

# Base URL of the API gateway used to validate user tokens.
# The configured GATEWAY_SERVICE_URL is used (resolves to the gateway's Docker
# service name, e.g. http://ppl-meta-gateway:8080). Hardcoding "localhost:8080"
# is wrong inside a container, where it points at the media service itself and
# causes every authenticated request to fail with 401.
def _gateway_base_url() -> str:
    return str(settings.GATEWAY_SERVICE_URL).rstrip("/")


def _user_profile_url() -> str:
    return f"{_gateway_base_url()}/api/v1/user/profile"

# In-memory cache: token -> (AuthUser, expiry_timestamp)
# Avoids re-validating the same token via gateway on every request
_token_cache: Dict[str, Tuple["AuthUser", float]] = {}
_TOKEN_CACHE_TTL = 60  # seconds
_TOKEN_CACHE_MAX_SIZE = 200


class AuthUser:
    """Authenticated user information."""

    def __init__(
        self, user_id: str, username: str, email: str, roles: list, permissions: list
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions


def _get_cached_user(token: str) -> Optional["AuthUser"]:
    """Return cached AuthUser if token was recently validated, else None."""
    entry = _token_cache.get(token)
    if entry is None:
        return None
    user, expiry = entry
    if time.monotonic() > expiry:
        _token_cache.pop(token, None)
        return None
    return user


def _set_cached_user(token: str, user: "AuthUser") -> None:
    """Cache a validated AuthUser for a short TTL."""
    # Evict oldest entries if cache is too large
    if len(_token_cache) >= _TOKEN_CACHE_MAX_SIZE:
        now = time.monotonic()
        expired = [k for k, (_, exp) in _token_cache.items() if now > exp]
        for k in expired:
            _token_cache.pop(k, None)
        # If still too large, clear half
        if len(_token_cache) >= _TOKEN_CACHE_MAX_SIZE:
            keys = list(_token_cache.keys())
            for k in keys[: len(keys) // 2]:
                _token_cache.pop(k, None)
    _token_cache[token] = (user, time.monotonic() + _TOKEN_CACHE_TTL)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """
    Dependency to get the current authenticated user.
    Validates JWT token by calling the user profile endpoint.
    Uses a short-lived in-memory cache to avoid hitting the gateway
    on every request (prevents circular-call bottleneck under load).
    
    Also supports internal service-to-service authentication using
    INTERNAL_SERVICE_TOKEN for microservice communication.
    """
    token = credentials.credentials
    
    # Check if this is an internal service request
    import os
    INTERNAL_SERVICE_TOKEN = os.getenv(
        "INTERNAL_SERVICE_TOKEN",
        "ppl-meta-internal-service-secret-key-change-in-production"
    )
    
    if token == INTERNAL_SERVICE_TOKEN:
        # Internal service request - use system user
        logger.info("Internal service request detected - using system user UUID")
        return AuthUser(
            user_id="00000000-0000-0000-0000-000000000000",  # System user UUID
            username="internal-service",
            email="service@ppl-meta.internal",
            roles=["system"],
            permissions=["all"],
        )

    # Check cache first
    cached = _get_cached_user(token)
    if cached is not None:
        return cached

    try:
        # Call user profile endpoint through gateway to get user data
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(_user_profile_url(), headers=headers)

            if response.status_code == 200:
                user_data = response.json()
                # Use UUID (guid) as user_id for media access control
                user = AuthUser(
                    user_id=user_data.get("guid"),  # Use UUID instead of integer ID
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    roles=user_data.get("roles", []),
                    permissions=user_data.get("capabilities", []),
                )
                _set_cached_user(token, user)
                return user
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token validation failed (gateway unreachable?): {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to validate token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[AuthUser]:
    """
    Optional authentication dependency.
    Returns None if no token provided, AuthUser if valid token.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_media_view(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """
    Dependency that requires the media:view capability.
    Returns 403 if the user lacks the media:view permission.
    """
    user = await get_current_user(credentials)
    if "media:view" not in user.permissions and "all" not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Media viewing is disabled for your account",
        )
    return user


def require_permission(resource: str, action: str):
    """
    Dependency factory for permission-based authorization.

    Usage:
    @app.get("/protected")
    async def protected_endpoint(
        user: AuthUser = Depends(require_permission("media", "read"))
    ):
        return {"message": "Access granted"}
    """

    async def permission_dependency(
        user: AuthUser = Depends(get_current_user),
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> AuthUser:
        # Check if user has the required permission
        has_permission = await user_service_client.check_user_permissions(
            user.user_id, resource, action, credentials.credentials
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {action} on {resource}",
            )

        return user

    return permission_dependency


async def get_user_from_token(token: str) -> AuthUser:
    """
    Get user from JWT token string (used for query parameter authentication).
    """
    try:
        # Call user profile endpoint through gateway to get user data
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(_user_profile_url(), headers=headers)

            if response.status_code == 200:
                user_data = response.json()
                # Use UUID (guid) as user_id for media access control
                return AuthUser(
                    user_id=user_data.get("guid"),  # Use UUID
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    roles=[],  # Default empty roles
                    permissions=[],  # Default empty permissions
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to validate token",
        ) from exc


def require_role(required_role: str):
    """
    Dependency factory for role-based authorization.

    Usage:
    @app.get("/admin")
    async def admin_endpoint(
        user: AuthUser = Depends(require_role("admin"))
    ):
        return {"message": "Admin access granted"}
    """

    async def role_dependency(
        user: AuthUser = Depends(get_current_user),
    ) -> AuthUser:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )

        return user

    return role_dependency

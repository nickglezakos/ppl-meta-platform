"""
Authentication and authorization dependencies for FastAPI.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.services.user_service import user_service_client

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """
    Dependency to get the current authenticated user.
    Validates JWT token by calling the user profile endpoint.
    
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

    try:
        # Call user profile endpoint through gateway to get user data
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                "http://localhost:8080/api/v1/user/profile", headers=headers
            )

            if response.status_code == 200:
                user_data = response.json()
                # Use UUID (guid) as user_id for media access control
                return AuthUser(
                    user_id=user_data.get("guid"),  # Use UUID instead of integer ID
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    roles=user_data.get("roles", []),
                    permissions=user_data.get("capabilities", []),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    except Exception as e:
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
            response = await client.get(
                "http://localhost:8080/api/v1/user/profile", headers=headers
            )

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

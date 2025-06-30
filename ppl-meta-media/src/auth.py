"""
Authentication and authorization dependencies for FastAPI.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from src.services.user_service import user_service_client
import logging

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()

class AuthUser:
    """Authenticated user information."""
    def __init__(self, user_id: str, username: str, email: str, roles: list, permissions: list):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """
    Dependency to get the current authenticated user.
    Validates JWT token with User Management service.
    """
    token = credentials.credentials
    
    # Validate token with User Management service
    user_data = await user_service_client.validate_token(token)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return AuthUser(
        user_id=user_data.get("user_id"),
        username=user_data.get("username"),
        email=user_data.get("email"),
        roles=user_data.get("roles", []),
        permissions=user_data.get("permissions", [])
    )

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
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
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> AuthUser:
        # Check if user has the required permission
        has_permission = await user_service_client.check_user_permissions(
            user.user_id, resource, action, credentials.credentials
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {action} on {resource}"
            )
        
        return user
    
    return permission_dependency

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
    async def role_dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return user
    
    return role_dependency

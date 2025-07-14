"""
Authentication and Authorization service for PPL Meta Media Service.
Provides JWT-based authentication and role-based access control (RBAC).
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class AuthenticationService:
    """JWT-based authentication service."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize authentication service.

        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm to use
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(
        self, data: Dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Payload data to encode
            expires_delta: Token expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)


class RoleBasedAccessControl:
    """Role-based access control system."""

    # Define available roles and their permissions
    ROLES = {
        "admin": {
            "permissions": {
                "media:create",
                "media:read",
                "media:update",
                "media:delete",
                "collection:create",
                "collection:read",
                "collection:update",
                "collection:delete",
                "share:create",
                "share:read",
                "share:update",
                "share:delete",
                "user:create",
                "user:read",
                "user:update",
                "user:delete",
                "system:admin",
            }
        },
        "user": {
            "permissions": {
                "media:create",
                "media:read",
                "media:update",
                "media:delete_own",
                "collection:create",
                "collection:read",
                "collection:update_own",
                "collection:delete_own",
                "share:create",
                "share:read_own",
                "share:update_own",
                "share:delete_own",
            }
        },
        "viewer": {
            "permissions": {"media:read", "collection:read", "share:read_shared"}
        },
        "guest": {"permissions": {"media:read_public", "collection:read_public"}},
    }

    @classmethod
    def get_user_permissions(cls, role: str) -> Set[str]:
        """Get permissions for a user role."""
        role_config = cls.ROLES.get(role, cls.ROLES["guest"])
        return role_config["permissions"]

    @classmethod
    def check_permission(cls, user_role: str, required_permission: str) -> bool:
        """
        Check if user role has required permission.

        Args:
            user_role: User's role
            required_permission: Required permission string

        Returns:
            True if user has permission
        """
        user_permissions = cls.get_user_permissions(user_role)
        return required_permission in user_permissions

    @classmethod
    def check_resource_access(
        cls, user_role: str, user_id: str, resource_owner_id: str, permission: str
    ) -> bool:
        """
        Check if user can access a specific resource.

        Args:
            user_role: User's role
            user_id: User's ID
            resource_owner_id: ID of resource owner
            permission: Required permission

        Returns:
            True if access is allowed
        """
        # Admin can access everything
        if user_role == "admin":
            return True

        # Check if user owns the resource
        if user_id == resource_owner_id:
            # Replace generic permission with owner-specific
            owner_permission = permission.replace(":delete", ":delete_own")
            owner_permission = owner_permission.replace(":update", ":update_own")
            owner_permission = owner_permission.replace(":read", ":read_own")
            return cls.check_permission(user_role, owner_permission)

        # Check standard permission
        return cls.check_permission(user_role, permission)


class AuthorizationMiddleware:
    """FastAPI middleware for authentication and authorization."""

    def __init__(self, auth_service: AuthenticationService):
        """Initialize authorization middleware."""
        self.auth_service = auth_service
        self.security = HTTPBearer()

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> Dict:
        """
        Get current user from JWT token.

        Args:
            credentials: HTTP Bearer token credentials

        Returns:
            User information from token
        """
        token = credentials.credentials
        payload = self.auth_service.verify_token(token)

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    def require_permission(self, permission: str):
        """
        Decorator to require specific permission for endpoint access.

        Args:
            permission: Required permission string

        Returns:
            Decorator function
        """

        def permission_decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract request and credentials from function arguments
                request = kwargs.get("request")
                credentials = kwargs.get("credentials")

                if not request or not credentials:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Get user from token
                user = await self.get_current_user(credentials)
                user_role = user.get("role", "guest")
                user_id = user.get("sub")

                # Check permission
                if not RoleBasedAccessControl.check_permission(user_role, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions: {permission} required",
                    )

                # Add user info to kwargs for endpoint use
                kwargs["current_user"] = user
                return await func(*args, **kwargs)

            return wrapper

        return permission_decorator

    def require_resource_access(self, permission: str, resource_id_param: str):
        """
        Decorator to require access to specific resource.

        Args:
            permission: Required permission string
            resource_id_param: Parameter name containing resource owner ID

        Returns:
            Decorator function
        """

        def access_decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract request and credentials
                request = kwargs.get("request")
                credentials = kwargs.get("credentials")

                if not request or not credentials:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Get user from token
                user = await self.get_current_user(credentials)
                user_role = user.get("role", "guest")
                user_id = user.get("sub")

                # Get resource owner ID from parameters
                resource_owner_id = kwargs.get(resource_id_param)
                if not resource_owner_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Resource owner ID required: {resource_id_param}",
                    )

                # Check resource access
                if not RoleBasedAccessControl.check_resource_access(
                    user_role, user_id, resource_owner_id, permission
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this resource",
                    )

                # Add user info to kwargs
                kwargs["current_user"] = user
                return await func(*args, **kwargs)

            return wrapper

        return access_decorator


class SecurityConfig:
    """Security configuration and utilities."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    @staticmethod
    def is_secure_request(request: Request) -> bool:
        """Check if request uses HTTPS."""
        return request.url.scheme == "https"

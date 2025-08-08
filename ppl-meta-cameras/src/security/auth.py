"""
Authentication and authorization module for PPL Meta Cameras.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from src.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer security scheme
security = HTTPBearer()


class CameraPermission:
    """Camera-specific permissions."""

    # Basic permissions
    VIEW_CAMERAS = "cameras:view"
    DETECT_CAMERAS = "cameras:detect"
    CONNECT_CAMERA = "cameras:connect"
    DISCONNECT_CAMERA = "cameras:disconnect"

    # Streaming permissions
    START_STREAM = "cameras:stream:start"
    STOP_STREAM = "cameras:stream:stop"
    VIEW_STREAM = "cameras:stream:view"

    # Recording permissions
    START_RECORDING = "cameras:record:start"
    STOP_RECORDING = "cameras:record:stop"
    VIEW_RECORDINGS = "cameras:record:view"
    DELETE_RECORDINGS = "cameras:record:delete"

    # Configuration permissions
    CONFIGURE_CAMERA = "cameras:configure"
    UPDATE_SETTINGS = "cameras:settings:update"

    # Administrative permissions
    ADMIN_CAMERAS = "cameras:admin"
    MANAGE_SESSIONS = "cameras:sessions:manage"


class CameraRole:
    """Predefined camera roles with permission sets."""

    VIEWER = {
        CameraPermission.VIEW_CAMERAS,
        CameraPermission.VIEW_STREAM,
        CameraPermission.VIEW_RECORDINGS,
    }

    OPERATOR = {
        CameraPermission.VIEW_CAMERAS,
        CameraPermission.CONNECT_CAMERA,
        CameraPermission.DISCONNECT_CAMERA,
        CameraPermission.START_STREAM,
        CameraPermission.STOP_STREAM,
        CameraPermission.VIEW_STREAM,
        CameraPermission.START_RECORDING,
        CameraPermission.STOP_RECORDING,
        CameraPermission.VIEW_RECORDINGS,
    }

    ADMINISTRATOR = {
        CameraPermission.VIEW_CAMERAS,
        CameraPermission.DETECT_CAMERAS,
        CameraPermission.CONNECT_CAMERA,
        CameraPermission.DISCONNECT_CAMERA,
        CameraPermission.START_STREAM,
        CameraPermission.STOP_STREAM,
        CameraPermission.VIEW_STREAM,
        CameraPermission.START_RECORDING,
        CameraPermission.STOP_RECORDING,
        CameraPermission.VIEW_RECORDINGS,
        CameraPermission.DELETE_RECORDINGS,
        CameraPermission.CONFIGURE_CAMERA,
        CameraPermission.UPDATE_SETTINGS,
        CameraPermission.ADMIN_CAMERAS,
        CameraPermission.MANAGE_SESSIONS,
    }


class AuthenticationService:
    """JWT-based authentication service for camera operations."""

    def __init__(self):
        self.secret_key = config.JWT_SECRET_KEY
        self.algorithm = config.JWT_ALGORITHM
        self.expire_minutes = config.JWT_EXPIRE_MINUTES

    def create_access_token(
        self,
        user_id: str,
        permissions: Set[str],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT access token with camera permissions."""

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "permissions": list(permissions),
            "service": "ppl-meta-cameras",
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(
            f"Created access token for user {user_id} with {len(permissions)} permissions"
        )

        return token

    def verify_token(self, token: str) -> Dict:
        """Verify JWT token from Node service or Cameras service."""

        try:
            # First try with camera service secret
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            payload_dict = dict(payload)

            # Check if token is for cameras service
            if payload_dict.get("service") == "cameras":
                return payload_dict

            # If no service specified, assume it's from cameras service
            if "service" not in payload_dict:
                payload_dict["service"] = "cameras"
                return payload_dict

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass  # Try with Node service secret

        try:
            # Try with Node service secret (get from environment or use default)
            import os

            node_secret = os.getenv(
                "NODE_SERVICE_SECRET", "default-secret-key-change-in-production"
            )
            payload = jwt.decode(token, node_secret, algorithms=[self.algorithm])
            payload_dict = dict(payload)

            # Accept Node service tokens and add cameras permissions
            if payload_dict.get("sub"):  # Node service uses 'sub' for user_id
                # Convert Node user to cameras permissions
                payload_dict["service"] = "node"
                # Grant admin access to Node users
                payload_dict["permissions"] = list(CameraRole.ADMINISTRATOR)
                user_sub = payload_dict.get("sub")
                logger.info(f"Accepted Node service token for user {user_sub}")
                return payload_dict

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # If we get here, both attempts failed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def get_user_permissions(self, token: str) -> Set[str]:
        """Extract user permissions from token."""
        payload = self.verify_token(token)
        return set(payload.get("permissions", []))

    def has_permission(self, token: str, required_permission: str) -> bool:
        """Check if user has specific permission."""
        try:
            payload = self.verify_token(token)

            # For Node service tokens, grant administrator permissions
            if payload.get("service") == "node" and payload.get("sub"):
                user_sub = payload.get("sub")
                logger.info(f"Granting admin permissions to Node user {user_sub}")
                # Node service users get full administrator permissions
                admin_permissions = set(CameraRole.ADMINISTRATOR)
                return required_permission in admin_permissions

            # For camera service tokens, check permissions normally
            user_permissions = set(payload.get("permissions", []))
            return required_permission in user_permissions

        except HTTPException:
            return False


# Global authentication service instance
auth_service = AuthenticationService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    """Dependency to get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.verify_token(credentials.credentials)


def require_permission(permission: str):
    """Dependency factory to require specific permission."""

    async def permission_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> Dict:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not auth_service.has_permission(credentials.credentials, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )

        return auth_service.verify_token(credentials.credentials)

    return permission_checker


# Permission dependency shortcuts
require_view_cameras = require_permission(CameraPermission.VIEW_CAMERAS)
require_detect_cameras = require_permission(CameraPermission.DETECT_CAMERAS)
require_connect_camera = require_permission(CameraPermission.CONNECT_CAMERA)
require_start_stream = require_permission(CameraPermission.START_STREAM)
require_view_stream = require_permission(CameraPermission.VIEW_STREAM)
require_start_recording = require_permission(CameraPermission.START_RECORDING)
require_admin_cameras = require_permission(CameraPermission.ADMIN_CAMERAS)


def create_demo_token(role: str = "administrator") -> str:
    """Create a demo token for testing purposes."""

    role_permissions = {
        "viewer": CameraRole.VIEWER,
        "operator": CameraRole.OPERATOR,
        "administrator": CameraRole.ADMINISTRATOR,
    }

    permissions = role_permissions.get(role.lower(), CameraRole.VIEWER)

    return auth_service.create_access_token(
        user_id=f"demo_{role}",
        permissions=permissions,
        expires_delta=timedelta(hours=24),
    )

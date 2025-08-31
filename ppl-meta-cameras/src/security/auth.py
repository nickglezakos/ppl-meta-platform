"""
Authentication and authorization module for PPL Meta Cameras.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import jwt
from fastapi import Depends, HTTPException, Request, status
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

        # First try with Node service secret
        try:
            import os

            node_secret = os.getenv(
                "NODE_SERVICE_SECRET", "default-secret-key-change-in-production"
            )
            logger.info(f"Trying Node service secret: {node_secret[:10]}...")
            payload = jwt.decode(token, node_secret, algorithms=[self.algorithm])
            payload_dict = dict(payload)
            logger.info(
                f"Successfully decoded with Node secret. Payload: {payload_dict}"
            )

            # Check if this is a Node service token (minimal payload with just sub + exp)
            if payload_dict.get("sub") and len(payload_dict) <= 3:  # sub, exp, iat
                # This is a Node service token - grant admin permissions
                payload_dict["service"] = "node"
                payload_dict["permissions"] = list(CameraRole.ADMINISTRATOR)
                user_sub = payload_dict.get("sub")
                logger.info(
                    f"Identified as Node service token for user {user_sub}, granted admin permissions"
                )
                return payload_dict

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            logger.info(f"Node service verification failed: {e}")

        # Try with camera service secret
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            payload_dict = dict(payload)
            logger.info(
                f"Successfully decoded with cameras secret. Payload: {payload_dict}"
            )

            # Check if token is for cameras service
            if payload_dict.get("service") == "cameras":
                return payload_dict

            # If no service specified, assume it's from cameras service
            if "service" not in payload_dict:
                payload_dict["service"] = "cameras"
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
            logger.info(f"Checking permission '{required_permission}' for token...")
            payload = self.verify_token(token)
            logger.info(f"Token verified, payload service: {payload.get('service')}")

            # For Node service tokens, grant administrator permissions
            if payload.get("service") == "node" and payload.get("sub"):
                user_sub = payload.get("sub")
                logger.info(f"Node service token for user {user_sub}")
                # Node service users get full administrator permissions
                admin_permissions = set(CameraRole.ADMINISTRATOR)
                logger.info(f"Admin permissions: {admin_permissions}")
                has_perm = required_permission in admin_permissions
                logger.info(
                    f"User {user_sub} has permission '{required_permission}': {has_perm}"
                )
                return has_perm

            # For camera service tokens, check permissions normally
            user_permissions = set(payload.get("permissions", []))
            logger.info(f"Camera service permissions: {user_permissions}")
            has_perm = required_permission in user_permissions
            logger.info(f"Has permission '{required_permission}': {has_perm}")
            return has_perm

        except HTTPException as e:
            logger.error(f"Permission check failed with HTTPException: {e.detail}")
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


async def get_current_user_flexible(
    request: Request,
) -> Dict:
    """Get current authenticated user - supports header and query param auth."""

    auth_token = None

    # Try to get token from Authorization header first
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header[7:]  # Remove "Bearer " prefix

    # Fall back to query parameter
    if not auth_token:
        auth_token = request.query_params.get("token")

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.verify_token(auth_token)


def require_permission_flexible(permission: str):
    """Permission factory supporting both header and query param auth."""

    async def permission_checker(request: Request) -> Dict:

        auth_token = None

        # Try to get token from Authorization header first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]  # Remove "Bearer " prefix

        # Fall back to query parameter
        if not auth_token:
            auth_token = request.query_params.get("token")

        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not auth_service.has_permission(auth_token, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )

        return auth_service.verify_token(auth_token)

    return permission_checker


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

# Flexible permission dependencies (support query params for browser compatibility)
require_view_stream_flexible = require_permission_flexible(CameraPermission.VIEW_STREAM)


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

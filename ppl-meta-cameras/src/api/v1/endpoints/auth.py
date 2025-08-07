"""
Authentication endpoints for PPL Meta Cameras API.
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException, status
from src.security.auth import CameraRole, auth_service, create_demo_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/demo-token")
async def create_demo_authentication_token(role: str = "administrator") -> Dict:
    """Create a demo authentication token for testing purposes."""

    valid_roles = ["viewer", "operator", "administrator"]

    if role.lower() not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    try:
        token = create_demo_token(role.lower())

        # Get role permissions for display
        role_permissions = {
            "viewer": list(CameraRole.VIEWER),
            "operator": list(CameraRole.OPERATOR),
            "administrator": list(CameraRole.ADMINISTRATOR),
        }

        logger.info(f"Created demo token for role: {role}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": role.lower(),
            "permissions": role_permissions[role.lower()],
            "expires_in_hours": 24,
            "usage": {
                "curl_example": f"curl -H 'Authorization: Bearer {token}' http://localhost:8005/api/v1/cameras/",
                "header_format": "Authorization: Bearer <token>",
            },
            "warning": "This is a demo token for testing purposes only. Do not use in production.",
        }

    except Exception as e:
        logger.error(f"Error creating demo token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create demo token",
        )


@router.get("/permissions")
async def list_camera_permissions() -> Dict:
    """List all available camera permissions and roles."""

    from src.security.auth import CameraPermission

    # Get all permission attributes
    permissions = [
        attr
        for attr in dir(CameraPermission)
        if not attr.startswith("_") and isinstance(getattr(CameraPermission, attr), str)
    ]

    permission_details = {}
    for perm in permissions:
        permission_details[perm] = getattr(CameraPermission, perm)

    roles_with_permissions = {
        "viewer": list(CameraRole.VIEWER),
        "operator": list(CameraRole.OPERATOR),
        "administrator": list(CameraRole.ADMINISTRATOR),
    }

    return {
        "available_permissions": permission_details,
        "predefined_roles": roles_with_permissions,
        "permission_hierarchy": {
            "viewer": "Basic read-only access to cameras and streams",
            "operator": "Can connect/disconnect cameras and control streaming/recording",
            "administrator": "Full access including camera detection and system administration",
        },
    }


@router.post("/validate-token")
async def validate_token(token: str) -> Dict:
    """Validate a JWT token and return user information."""

    try:
        payload = auth_service.verify_token(token)

        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "service": payload.get("service"),
            "permissions": payload.get("permissions", []),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat"),
        }

    except HTTPException as e:
        return {"valid": False, "error": e.detail, "status_code": e.status_code}
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return {"valid": False, "error": "Token validation failed", "status_code": 500}

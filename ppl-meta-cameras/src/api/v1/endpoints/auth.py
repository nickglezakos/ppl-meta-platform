"""
Authentication endpoints for PPL Meta Cameras API.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from src.security.auth import (
    CameraRole,
    auth_service,
    create_demo_token,
    get_current_user,
)
from src.services.session_auth import session_manager

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


@router.post("/streaming-session/{device_id}")
async def create_streaming_session(
    device_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Create an authenticated streaming session for browser-compatible MJPEG streaming."""

    try:
        user_id = current_user.get("sub", "unknown")
        permissions = current_user.get("permissions", [])

        # Create streaming session
        session_id = session_manager.create_session(user_id, device_id, permissions)

        # Generate authenticated streaming URL
        streaming_url = f"/api/v1/streaming/{device_id}/video-session/{session_id}"

        logger.info(
            "Created streaming session %s for user %s on device %s",
            session_id[:16] + "...",
            user_id,
            device_id,
        )

        return {
            "session_id": session_id,
            "device_id": device_id,
            "user_id": user_id,
            "streaming_url": streaming_url,
            "expires_in_seconds": 3600,  # 1 hour
            "usage": {
                "html_example": f'<img src="http://localhost:8005{streaming_url}" />',
                "javascript_example": f'document.getElementById("stream").src = "http://localhost:8005{streaming_url}";',
                "description": "Use the streaming_url directly in HTML img src or video src attributes",
            },
            "status": "active",
        }

    except Exception as e:
        logger.error("Error creating streaming session: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create streaming session",
        ) from e


@router.get("/streaming-sessions")
async def get_active_streaming_sessions(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Get information about active streaming sessions."""

    try:
        sessions_info = session_manager.get_active_sessions()

        return {
            "status": "success",
            "sessions": sessions_info,
            "user": current_user.get("sub", "unknown"),
        }

    except Exception as e:
        logger.error("Error retrieving streaming sessions: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve streaming sessions",
        ) from e


@router.delete("/streaming-session/{session_id}")
async def revoke_streaming_session(
    session_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Revoke a streaming session."""

    try:
        success = session_manager.revoke_session(session_id)

        if success:
            logger.info(
                "Revoked streaming session %s by user %s",
                session_id[:16] + "...",
                current_user.get("sub", "unknown"),
            )
            return {
                "status": "success",
                "message": f"Session {session_id[:16]}... revoked successfully",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or already expired",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error revoking streaming session: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke streaming session",
        ) from e

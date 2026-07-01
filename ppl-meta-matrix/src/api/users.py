"""Matrix User Directory + SSO API endpoints.

Phase 3: JWT-based authentication (trusts node-issued JWTs),
Matrix user directory CRUD, capability management, and the
GET /api/v1/matrix/me endpoint for frontend integration.
"""

import logging
import os
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from services.matrix_service import matrix_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["matrix-users"])

# Matches the node's SECRET_KEY for JWT validation
MATRIX_JWT_SECRET = os.environ.get("SECRET_KEY", "default-secret-key-change-in-production")
MATRIX_JWT_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AddUserRequest(BaseModel):
    user_email: str = Field(..., description="User's email address")
    home_installation_uuid: str = Field(..., description="UUID of the user's home installation")
    home_node_url: str = Field("http://localhost:8000", description="URL of the user's home node")
    display_name: str = ""
    capabilities: list[str] = Field(default_factory=list, description="Initial Matrix capabilities to grant")


class UpdateCapabilitiesRequest(BaseModel):
    capabilities: list[str] = Field(..., description="Full list of capabilities (replaces existing)")


# ---------------------------------------------------------------------------
# JWT Helpers
# ---------------------------------------------------------------------------

def _decode_jwt(authorization: Optional[str] = Header(None)) -> dict:
    """Validate a JWT from any member node and return payload.

    The Matrix service trusts node-issued JWTs — it does not issue its own.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, MATRIX_JWT_SECRET, algorithms=[MATRIX_JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def _get_user_email(payload: dict = Depends(_decode_jwt)) -> str:
    """Extract user email from a validated JWT payload."""
    email = payload.get("sub_email") or payload.get("email") or ""
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email claim")
    return email


# ---------------------------------------------------------------------------
# /me — Current User's Matrix Profile
# ---------------------------------------------------------------------------

@router.get("/me")
async def matrix_me(payload: dict = Depends(_decode_jwt)):
    """Get the current user's Matrix groups and capabilities.

    This is the primary endpoint for frontend integration.
    The frontend calls this after node login to determine:
    - Which Matrix groups the user belongs to
    - Which Matrix capabilities the user has
    - Whether to show the "Matrix" tab in the UI

    Returns:
        Dict with user's Matrix memberships, capabilities, and group IDs.
    """
    email = payload.get("sub_email") or payload.get("email") or ""
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email claim")

    user_id = payload.get("sub") or payload.get("user_id")
    home_installation = payload.get("installation_uuid", "")

    result = matrix_service.get_user_matrix_profile(email)

    return {
        "authenticated": True,
        "user_email": email,
        "user_id": user_id,
        "home_installation_uuid": home_installation,
        "groups": result.get("groups", []),
        "capabilities": result.get("capabilities", []),
        "has_matrix_access": len(result.get("groups", [])) > 0,
    }


# ---------------------------------------------------------------------------
# User Directory CRUD
# ---------------------------------------------------------------------------

@router.get("/groups/{group_id}/users")
async def list_users(group_id: str, _payload: dict = Depends(_decode_jwt)):
    """List all users in a Matrix group's directory."""
    users = matrix_service.list_users(group_id)
    return {
        "users": [
            {
                "id": u.id,
                "user_email": u.user_email,
                "home_installation_uuid": u.home_installation_uuid,
                "display_name": u.display_name,
                "capabilities": matrix_service.get_user_capabilities(u.id),
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "count": len(users),
    }


@router.post("/groups/{group_id}/users")
async def add_user(group_id: str, request: AddUserRequest, _payload: dict = Depends(_decode_jwt)):
    """Add a user to a Matrix group's directory with optional capabilities."""
    try:
        user, capabilities = matrix_service.add_user(
            group_id=group_id,
            user_email=request.user_email,
            home_installation_uuid=request.home_installation_uuid,
            home_node_url=request.home_node_url,
            display_name=request.display_name,
            capabilities=request.capabilities,
            granted_by_user_id=_payload.get("sub", 0),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "id": user.id,
        "user_email": user.user_email,
        "home_installation_uuid": user.home_installation_uuid,
        "display_name": user.display_name,
        "capabilities": capabilities,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.delete("/groups/{group_id}/users/{user_email}")
async def remove_user(group_id: str, user_email: str, _payload: dict = Depends(_decode_jwt)):
    """Remove a user from a Matrix group's directory."""
    try:
        removed = matrix_service.remove_user(group_id, user_email)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not removed:
        raise HTTPException(status_code=404, detail="User not found in group")
    return {"status": "removed", "user_email": user_email}


@router.put("/groups/{group_id}/users/{user_email}/capabilities")
async def update_user_capabilities(
    group_id: str,
    user_email: str,
    request: UpdateCapabilitiesRequest,
    _payload: dict = Depends(_decode_jwt),
):
    """Update a user's Matrix capabilities (full replacement)."""
    try:
        capabilities = matrix_service.set_user_capabilities(
            group_id=group_id,
            user_email=user_email,
            capabilities=request.capabilities,
            granted_by_user_id=_payload.get("sub", 0),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "user_email": user_email,
        "capabilities": capabilities,
        "count": len(capabilities),
    }
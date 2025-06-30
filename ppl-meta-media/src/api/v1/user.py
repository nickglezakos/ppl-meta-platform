"""
User-related endpoints - API v1.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth import AuthUser, get_current_user, get_optional_user, require_permission, require_role
from typing import Dict, Any

router = APIRouter(prefix="/user", tags=["user-v1"])

@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile information."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "service": "ppl-meta-media"
    }

@router.get("/permissions", response_model=Dict[str, Any])
async def get_user_permissions(
    user: AuthUser = Depends(get_current_user)
):
    """Get current user's permissions."""
    return {
        "user_id": user.user_id,
        "permissions": user.permissions,
        "roles": user.roles
    }

@router.get("/media/access", response_model=Dict[str, Any])
async def check_media_access(
    user: AuthUser = Depends(require_permission("media", "read"))
):
    """Check if user has media access permissions."""
    return {
        "user_id": user.user_id,
        "has_media_access": True,
        "message": "User has permission to access media"
    }

@router.get("/admin/status", response_model=Dict[str, Any])
async def admin_status(
    user: AuthUser = Depends(require_role("admin"))
):
    """Admin-only endpoint example."""
    return {
        "user_id": user.user_id,
        "admin_access": True,
        "message": "Admin access granted",
        "service_status": "operational"
    }

@router.get("/public/info", response_model=Dict[str, Any])
async def public_info(
    user: AuthUser = Depends(get_optional_user)
):
    """Public endpoint that works with or without authentication."""
    if user:
        return {
            "message": "Welcome back!",
            "authenticated": True,
            "username": user.username
        }
    else:
        return {
            "message": "Welcome, guest!",
            "authenticated": False
        }

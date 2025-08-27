"""
User API Routes for PPL Meta BootCore Service

Endpoints:
- POST /api/v1/users/create - Create new user
- GET /api/v1/users/list - List all users
- GET /api/v1/users/owner - Get owner information

GitHub Issue: #44
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from models.platform_models import (
    UserListResponse,
    UserManagementRequest,
    UserManagementResponse,
)
from services.user_service import UserService

logger = logging.getLogger(__name__)

# Create router
user_router = APIRouter()


def get_user_service() -> UserService:
    """Dependency to get user service"""
    # This will be replaced by proper dependency injection
    from main import user_service

    if not user_service:
        raise HTTPException(status_code=503, detail="User service not available")
    return user_service


@user_router.post("/create", response_model=UserManagementResponse)
async def create_user(
    request: UserManagementRequest,
    user_service: UserService = Depends(get_user_service),
):
    """
    Create a new user account

    Creates a new user with specified role and permissions.
    Requires owner privileges.
    """
    try:
        logger.info("👤 User creation requested: %s", request.username)

        response = await user_service.create_user(request)

        if response.success:
            logger.info("✅ User created successfully: %s", response.username)
        else:
            logger.warning("❌ User creation failed: %s", response.message)

        return response

    except Exception as e:
        logger.error("❌ User creation error: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@user_router.get("/list", response_model=UserListResponse)
async def list_users(user_service: UserService = Depends(get_user_service)):
    """
    Get list of all users

    Returns all users with their roles and status.
    Requires admin or owner privileges.
    """
    try:
        logger.debug("📋 User list requested")

        response = await user_service.get_users()

        return response

    except Exception as e:
        logger.error("❌ User list error: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get user list: {str(e)}"
        )


@user_router.get("/owner")
async def get_owner_info(user_service: UserService = Depends(get_user_service)):
    """
    Get platform owner information

    Returns information about the platform owner.
    """
    try:
        logger.debug("👑 Owner info requested")

        users = await user_service.get_users()
        owner = users.owner_info

        if not owner:
            return {"has_owner": False, "message": "No owner configured"}

        return {
            "has_owner": True,
            "owner": {
                "user_id": str(owner.user_id),
                "username": owner.username,
                "email": owner.email,
                "created_date": owner.created_date.isoformat(),
                "last_login": (
                    owner.last_login.isoformat() if owner.last_login else None
                ),
                "is_active": owner.is_active,
            },
        }

    except Exception as e:
        logger.error("❌ Owner info error: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get owner info: {str(e)}"
        )


@user_router.get("/count")
async def get_user_count(user_service: UserService = Depends(get_user_service)):
    """
    Get user count and limits

    Returns current user count and license limits.
    """
    try:
        logger.debug("🔢 User count requested")

        users = await user_service.get_users()

        return {
            "current_users": users.total_count,
            "max_users": users.max_users,
            "available_slots": max(0, users.max_users - users.total_count),
            "has_owner": users.owner_info is not None,
        }

    except Exception as e:
        logger.error("❌ User count error: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get user count: {str(e)}"
        )


@user_router.get("/health")
async def user_health(user_service: UserService = Depends(get_user_service)):
    """
    User service health check

    Returns user service health status.
    """
    try:
        health_status = await user_service.health_check()
        user_count = await user_service.get_user_count()

        return {
            "service": "user",
            "status": health_status,
            "user_count": user_count,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ User health check error: %s", e)
        return {
            "service": "user",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

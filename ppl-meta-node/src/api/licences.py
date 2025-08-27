"""
PPL Meta Node - Licensing API Endpoints

Provides licensing integration endpoints for the node service to communicate
with the bootcore licensing system and manage local platform identity.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.services.licensing_service import LicensingService, get_licensing_service
from src.services.user_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/licensing", tags=["licensing"])


@router.get("/platform/identity", response_model=Dict[str, Any])
async def get_platform_identity(
    licensing_service: LicensingService = Depends(get_licensing_service),
):
    """Get the platform identity for this node installation."""
    try:
        identity = await licensing_service.get_platform_identity()
        return {"success": True, "platform_identity": identity}
    except Exception as e:
        logger.error("Failed to get platform identity: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform identity",
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_license_status(
    current_user: User = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service),
):
    """Get current license status and information. [AUTH REQUIRED]"""
    try:
        license_info = await licensing_service.get_license_status()
        return {"success": True, "license": license_info}
    except Exception as e:
        logger.error("Failed to get license status: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve license status",
        )


@router.get("/validation/user-limit", response_model=Dict[str, Any])
async def validate_user_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    licensing_service: LicensingService = Depends(get_licensing_service),
):
    """Validate if current user count is within license limits. [AUTH REQUIRED]"""
    try:
        # Get current user count
        current_user_count = db.query(User).filter(User.is_active == True).count()

        # Check license limits
        is_valid = await licensing_service.validate_user_limit(current_user_count)
        license_info = await licensing_service.get_license_info_for_user_creation()

        return {
            "success": True,
            "validation": {
                "current_users": current_user_count,
                "max_users": license_info.get("max_users", 1),
                "license_type": license_info.get("license_type", "trial"),
                "within_limit": is_valid,
                "can_add_users": is_valid,
            },
        }
    except Exception as e:
        logger.error("Failed to validate user limit: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate user limit",
        )


@router.post("/owner/register", response_model=Dict[str, Any])
async def register_platform_owner(
    user_data: Dict[str, Any],
    licensing_service: LicensingService = Depends(get_licensing_service),
):
    """Register the platform owner with the bootcore service."""
    try:
        success = await licensing_service.register_owner(user_data)
        return {
            "success": success,
            "message": (
                "Owner registered successfully"
                if success
                else "Failed to register owner"
            ),
        }
    except Exception as e:
        logger.error("Failed to register platform owner: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register platform owner",
        )


@router.get("/features", response_model=Dict[str, Any])
async def get_license_features(
    current_user: User = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service),
):
    """Get available features based on current license. [AUTH REQUIRED]"""
    try:
        license_info = await licensing_service.get_license_status()

        features = license_info.get("features", [])
        license_type = license_info.get("license_type", "trial")

        # Define feature mappings
        feature_mappings = {
            "trial": ["basic_user_management"],
            "professional": [
                "basic_user_management",
                "advanced_analytics",
                "multi_camera_support",
            ],
            "enterprise": [
                "basic_user_management",
                "advanced_analytics",
                "multi_camera_support",
                "bulk_operations",
                "api_access",
                "priority_support",
            ],
            "developer": [
                "basic_user_management",
                "advanced_analytics",
                "api_access",
                "development_tools",
            ],
        }

        available_features = feature_mappings.get(
            license_type, ["basic_user_management"]
        )

        return {
            "success": True,
            "license_type": license_type,
            "available_features": available_features,
            "custom_features": features,
        }
    except Exception as e:
        logger.error("Failed to get license features: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve license features",
        )


@router.get("/health", response_model=Dict[str, Any])
async def licensing_health_check(
    licensing_service: LicensingService = Depends(get_licensing_service),
):
    """Health check for licensing service connectivity."""
    try:
        # Test connection to bootcore
        license_status = await licensing_service.get_license_status()

        is_connected = license_status.get("status") != "offline"

        return {
            "success": True,
            "licensing_service": {
                "connected": is_connected,
                "bootcore_url": licensing_service.bootcore_url,
                "platform_instance_id": licensing_service.platform_instance_id,
                "last_check": license_status.get("checked_at", "unknown"),
            },
        }
    except Exception as e:
        logger.error("Licensing health check failed: %s", str(e))
        return {
            "success": False,
            "licensing_service": {"connected": False, "error": str(e)},
        }

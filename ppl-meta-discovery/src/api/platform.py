"""Platform metadata API endpoints for PPL Meta Discovery Service."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from models.service_models import PlatformLicenseInfo, PlatformMetadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["platform"])

# In-memory storage for platform metadata (in production, use a database)
_platform_metadata: Optional[PlatformMetadata] = None


@router.post("/metadata", response_model=Dict[str, Any])
async def register_platform_metadata(metadata: PlatformMetadata):
    """Register or update platform metadata including licensing information."""
    global _platform_metadata

    try:
        # Update timestamp
        metadata.last_updated = datetime.utcnow()

        # Store metadata
        _platform_metadata = metadata

        logger.info(f"Platform metadata registered: {metadata.platform_instance_id}")

        return {
            "success": True,
            "message": "Platform metadata registered successfully",
            "platform_instance_id": metadata.platform_instance_id,
            "last_updated": metadata.last_updated.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to register platform metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register platform metadata",
        )


@router.get("/metadata", response_model=Dict[str, Any])
async def get_platform_metadata():
    """Get current platform metadata including licensing information."""
    try:
        if not _platform_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform metadata not found",
            )

        return {
            "success": True,
            "platform_metadata": _platform_metadata.dict(),
            "summary": {
                "platform_instance_id": _platform_metadata.platform_instance_id,
                "platform_version": _platform_metadata.platform_version,
                "is_licensed": _platform_metadata.is_licensed,
                "license_status": (
                    _platform_metadata.license_info.license_status
                    if _platform_metadata.license_info
                    else "unknown"
                ),
                "license_type": (
                    _platform_metadata.license_info.license_type
                    if _platform_metadata.license_info
                    else "unknown"
                ),
                "current_users": (
                    _platform_metadata.license_info.current_users
                    if _platform_metadata.license_info
                    else 0
                ),
                "max_users": (
                    _platform_metadata.license_info.max_users
                    if _platform_metadata.license_info
                    else 0
                ),
                "days_until_expiry": (
                    _platform_metadata.license_info.days_until_expiry
                    if _platform_metadata.license_info
                    else None
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform metadata",
        )


@router.get("/licensing", response_model=Dict[str, Any])
async def get_platform_licensing():
    """Get platform licensing information."""
    try:
        if not _platform_metadata or not _platform_metadata.license_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform licensing information not found",
            )

        license_info = _platform_metadata.license_info

        return {
            "success": True,
            "licensing": {
                "license_status": license_info.license_status,
                "license_type": license_info.license_type,
                "max_users": license_info.max_users,
                "current_users": license_info.current_users,
                "expires_at": (
                    license_info.expires_at.isoformat()
                    if license_info.expires_at
                    else None
                ),
                "activated_at": (
                    license_info.activated_at.isoformat()
                    if license_info.activated_at
                    else None
                ),
                "owner_email": license_info.owner_email,
                "instance_id": license_info.instance_id,
                "features": license_info.features,
                "is_valid": license_info.is_valid,
                "days_until_expiry": license_info.days_until_expiry,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform licensing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform licensing information",
        )


@router.get("/topology", response_model=Dict[str, Any])
async def get_platform_topology():
    """Get enhanced platform topology with licensing information."""
    try:
        if not _platform_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform metadata not found",
            )

        # Build enhanced topology
        topology = {
            "platform_instance_id": _platform_metadata.platform_instance_id,
            "platform_version": _platform_metadata.platform_version,
            "installation_date": _platform_metadata.installation_date.isoformat(),
            "last_updated": _platform_metadata.last_updated.isoformat(),
            "system_info": _platform_metadata.system_info,
            "service_topology": _platform_metadata.service_topology,
        }

        # Add licensing information if available
        if _platform_metadata.license_info:
            license_info = _platform_metadata.license_info
            topology["licensing"] = {
                "status": license_info.license_status,
                "type": license_info.license_type,
                "is_valid": license_info.is_valid,
                "max_users": license_info.max_users,
                "current_users": license_info.current_users,
                "features": license_info.features,
                "days_until_expiry": license_info.days_until_expiry,
            }

        return {
            "success": True,
            "topology": topology,
            "is_licensed": _platform_metadata.is_licensed,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform topology: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform topology",
        )


@router.delete("/metadata", response_model=Dict[str, Any])
async def clear_platform_metadata():
    """Clear platform metadata (for testing/reset purposes)."""
    global _platform_metadata

    try:
        _platform_metadata = None

        logger.info("Platform metadata cleared")

        return {"success": True, "message": "Platform metadata cleared successfully"}

    except Exception as e:
        logger.error(f"Failed to clear platform metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear platform metadata",
        )

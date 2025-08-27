"""
Platform API Routes for PPL Meta BootCore Service

Endpoints:
- GET /api/v1/platform/identity - Get platform instance identity
- GET /api/v1/platform/info - Get platform information

GitHub Issue: #44
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from models.platform_models import PlatformIdentityResponse
from services.platform_service import PlatformService

logger = logging.getLogger(__name__)

# Create router
platform_router = APIRouter()


def get_platform_service() -> PlatformService:
    """Dependency to get platform service"""
    # This will be replaced by proper dependency injection
    from main import platform_service

    if not platform_service:
        raise HTTPException(status_code=503, detail="Platform service not available")
    return platform_service


@platform_router.get("/identity", response_model=PlatformIdentityResponse)
async def get_platform_identity(
    platform_service: PlatformService = Depends(get_platform_service),
):
    """
    Get platform instance identity and information

    Returns unique platform instance details including licensing status.
    """
    try:
        logger.debug("🆔 Platform identity requested")

        instance = await platform_service.ensure_platform_instance()

        response = PlatformIdentityResponse(
            instance_id=instance.instance_id,
            installation_date=instance.installation_date,
            platform_version=instance.platform_version,
            owner_email=instance.owner_email,
            activation_status=instance.activation_status,
            license_type=instance.license_type,
            hardware_fingerprint=instance.hardware_fingerprint,
            metadata=instance.metadata,
        )

        return response

    except Exception as e:
        logger.error("❌ Platform identity error: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get platform identity: {str(e)}"
        )


@platform_router.get("/info")
async def get_platform_info(
    platform_service: PlatformService = Depends(get_platform_service),
):
    """
    Get comprehensive platform information

    Returns detailed platform status and configuration.
    """
    try:
        logger.debug("ℹ️  Platform info requested")

        instance = await platform_service.ensure_platform_instance()
        health_status = await platform_service.health_check()

        return {
            "platform_instance": {
                "instance_id": str(instance.instance_id),
                "installation_date": instance.installation_date.isoformat(),
                "platform_version": instance.platform_version,
                "activation_status": instance.activation_status,
                "hardware_fingerprint": (
                    instance.hardware_fingerprint[:16] + "..."
                    if instance.hardware_fingerprint
                    else None
                ),
            },
            "licensing": {
                "has_license": bool(instance.license_key),
                "license_type": instance.license_type,
                "owner_email": instance.owner_email,
                "activation_date": (
                    instance.activation_date.isoformat()
                    if instance.activation_date
                    else None
                ),
                "expires_date": (
                    instance.expires_date.isoformat() if instance.expires_date else None
                ),
                "last_validation": (
                    instance.last_validation.isoformat()
                    if instance.last_validation
                    else None
                ),
                "validation_count": instance.validation_count,
            },
            "system_info": instance.metadata.get("system_info", {}),
            "service_status": {
                "platform_service": health_status,
                "timestamp": datetime.now().isoformat(),
            },
        }

    except Exception as e:
        logger.error("❌ Platform info error: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get platform info: {str(e)}"
        )


@platform_router.get("/health")
async def platform_health(
    platform_service: PlatformService = Depends(get_platform_service),
):
    """
    Platform service health check

    Returns platform service health status.
    """
    try:
        health_status = await platform_service.health_check()

        return {
            "service": "platform",
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "instance_id": platform_service.get_instance_id(),
        }

    except Exception as e:
        logger.error("❌ Platform health check error: %s", e)
        return {
            "service": "platform",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

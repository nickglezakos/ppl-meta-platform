"""
License API Routes for PPL Meta BootCore Service

Endpoints:
- POST /api/v1/license/activate - Activate license key
- GET /api/v1/license/status - Get license status
- POST /api/v1/license/validate - Force license validation

GitHub Issue: #44
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from models.platform_models import (
    ActivationStatus,
    LicenseActivationRequest,
    LicenseActivationResponse,
    LicenseStatusResponse,
)
from services.license_service import LicenseService

logger = logging.getLogger(__name__)

# Create router
license_router = APIRouter()


def get_license_service() -> LicenseService:
    """Dependency to get license service"""
    # This will be replaced by proper dependency injection
    from main import license_service

    if not license_service:
        raise HTTPException(status_code=503, detail="License service not available")
    return license_service


@license_router.post("/activate", response_model=LicenseActivationResponse)
async def activate_license(
    request: LicenseActivationRequest,
    license_service: LicenseService = Depends(get_license_service),
):
    """
    Activate a license key for the platform

    Validates the license key and binds it to this platform instance.
    Creates hardware fingerprint for anti-piracy protection.
    """
    try:
        logger.info(f"🔑 License activation requested: {request.license_key[:8]}...")

        response = await license_service.activate_license(request)

        if response.success:
            logger.info(f"✅ License activated successfully: {response.license_type}")
        else:
            logger.warning(f"❌ License activation failed: {response.message}")

        return response

    except Exception as e:
        logger.error(f"❌ License activation error: {e}")
        return LicenseActivationResponse(
            success=False,
            instance_id="00000000-0000-0000-0000-000000000000",
            activation_status=ActivationStatus.INVALID,
            message=f"Internal error: {str(e)}",
        )


@license_router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(
    license_service: LicenseService = Depends(get_license_service),
):
    """
    Get current license status and information

    Returns license type, expiration, features, and validation status.
    """
    try:
        logger.debug("📊 License status requested")

        status = await license_service.get_license_status()

        return status

    except Exception as e:
        logger.error(f"❌ License status error: {e}")
        return LicenseStatusResponse(
            license_active=False,
            activation_status=ActivationStatus.INVALID,
            current_users=0,
            max_users=1,
        )


@license_router.post("/validate")
async def validate_license(
    force_online: bool = False,
    license_service: LicenseService = Depends(get_license_service),
):
    """
    Force license validation

    Optionally forces online validation even if cache is valid.
    """
    try:
        logger.info(f"🔄 License validation requested (force_online={force_online})")

        # Get current status
        status = await license_service.get_license_status()

        # TODO: Implement actual validation logic
        validation_result = {
            "valid": status.license_active,
            "status": status.activation_status,
            "validated_at": datetime.now().isoformat(),
            "next_validation": (
                status.next_validation.isoformat() if status.next_validation else None
            ),
            "force_online": force_online,
        }

        return validation_result

    except Exception as e:
        logger.error(f"❌ License validation error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "valid": False,
                "status": "error",
                "message": str(e),
                "validated_at": datetime.now().isoformat(),
            },
        )


@license_router.get("/info")
async def get_license_info(
    license_service: LicenseService = Depends(get_license_service),
):
    """
    Get detailed license information

    Returns comprehensive license details for administrative purposes.
    """
    try:
        logger.debug("ℹ️  License info requested")

        status = await license_service.get_license_status()

        return {
            "license_active": status.license_active,
            "license_type": status.license_type,
            "activation_status": status.activation_status,
            "expires_date": status.expires_date,
            "days_remaining": status.days_remaining,
            "features_enabled": status.features_enabled,
            "user_limits": {
                "max_users": status.max_users,
                "current_users": status.current_users,
            },
            "validation_info": {
                "last_validation": status.last_validation,
                "next_validation": status.next_validation,
            },
            "service_status": "operational",
        }

    except Exception as e:
        logger.error(f"❌ License info error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to get license info",
                "message": str(e),
                "service_status": "error",
            },
        )

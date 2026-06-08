"""
PPL Meta Node - Licensing API Endpoints

Provides licensing integration endpoints for the node service to communicate
with the bootcore licensing system and manage local platform identity.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from src.auth_utils import create_access_token, get_user_role_names
from src.config import settings
from src.database import get_db
from src.models.installation_info import InstallationInfo
from src.models.user import User
from src.services.authority_service import authority_service, ensure_utc_datetime
from src.services.licensing_service import LicensingService, get_licensing_service
from src.services.role_service import ensure_exact_system_roles
from src.services.user_service import create_user, get_user_by_email, log_user_action
from src.services.user_service import get_current_user
from src.schemas.user import UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/licensing", tags=["licensing"])

APPLICATION_KEY_PATTERN = r"^lic_[0-9a-f]{32}$"


class BootstrapActivationRequest(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=8)
    application_key: str = Field(pattern=APPLICATION_KEY_PATTERN)


class BootstrapActivationResponse(BaseModel):
    success: bool
    bootstrap_state: str
    message: str
    reason: str
    access_token: str | None = None
    token_type: str | None = None
    user: Dict[str, Any] | None = None
    installation: Dict[str, Any] | None = None


def _build_bootstrap_state_payload(db: Session) -> Dict[str, Any]:
    installation_info = db.query(InstallationInfo).first()
    installation_uuid = authority_service.get_effective_installation_uuid(db)
    application_key = authority_service.get_effective_application_key(db)
    approved_owner_email = (
        installation_info.authority_approved_owner_email if installation_info else None
    )
    local_owner_user = None
    local_owner_roles: list[str] = []

    if approved_owner_email:
        local_owner_user = get_user_by_email(db, approved_owner_email)
        if local_owner_user is not None:
            local_owner_roles = get_user_role_names(db, local_owner_user.id)

    bootstrap_state = "not_started"
    if authority_service.is_configured() and application_key:
        bootstrap_state = "awaiting_owner_activation"
    if approved_owner_email:
        bootstrap_state = "owner_approved"
    if local_owner_user is not None and "owner" in local_owner_roles:
        bootstrap_state = "bootstrap_complete"

    return {
        "success": True,
        "bootstrap": {
            "state": bootstrap_state,
            "complete": bootstrap_state == "bootstrap_complete",
            "authority": {
                "enabled": settings.AUTHORITY_SERVICE_ENABLED,
                "configured": bool(authority_service.is_configured() and application_key),
                "service_url": settings.AUTHORITY_SERVICE_URL,
                "last_result_reason": (
                    installation_info.authority_last_result_reason if installation_info else None
                ),
            },
            "installation": {
                "installation_uuid": installation_uuid,
                "application_key_configured": bool(application_key),
            },
            "owner": {
                "approved_owner_email": approved_owner_email,
                "local_user_exists": local_owner_user is not None,
                "local_owner_role_present": "owner" in local_owner_roles,
                "local_roles": local_owner_roles,
            },
            "users": {
                "total_users": db.query(User).count(),
            },
        },
    }


@router.get("/bootstrap/status", response_model=Dict[str, Any])
async def get_bootstrap_status(db: Session = Depends(get_db)):
    """Get the first-install bootstrap state without requiring authentication."""
    try:
        return _build_bootstrap_state_payload(db)
    except RuntimeError as e:
        logger.error("Failed to get bootstrap status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bootstrap status",
        ) from e


@router.post("/bootstrap/activate", response_model=BootstrapActivationResponse)
async def activate_bootstrap_owner(
    payload: BootstrapActivationRequest,
    db: Session = Depends(get_db),
):
    """Activate the first installation owner using Authority approval and create a local session."""
    try:
        bootstrap = _build_bootstrap_state_payload(db)["bootstrap"]
        if bootstrap["complete"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bootstrap is already complete",
            )

        existing_user = get_user_by_email(db, payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        authority_result = await authority_service.activate_owner_candidate(
            db,
            payload.email,
            application_key_override=payload.application_key,
        )
        if not authority_result.get("configured"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authority bootstrap is not configured",
            )

        if not authority_result.get("approved"):
            return BootstrapActivationResponse(
                success=False,
                bootstrap_state="awaiting_owner_activation",
                message="Owner activation was rejected",
                reason=authority_result.get("reason", "activation_rejected"),
                installation=authority_result.get("installation"),
            )

        created_user = create_user(
            db,
            UserCreate(
                username=payload.username,
                email=payload.email,
                password=payload.password,
            ),
        )
        created_user.email_verified = True
        db.commit()
        db.refresh(created_user)

        ensure_exact_system_roles(db, payload.email, {"owner", "admin", "user"})
        log_user_action(db, created_user.username, created_user.email, "bootstrap_activate")

        access_token = create_access_token(data={"sub": str(created_user.id)})
        return BootstrapActivationResponse(
            success=True,
            bootstrap_state="bootstrap_complete",
            message="Bootstrap owner activated successfully",
            reason=authority_result.get("reason", "approved_owner"),
            access_token=access_token,
            token_type="bearer",
            user=created_user.to_dict(),
            installation=authority_result.get("installation"),
        )
    except RuntimeError as e:
        logger.error("Failed to activate bootstrap owner: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate bootstrap owner",
        ) from e


@router.get("/authority/status", response_model=Dict[str, Any])
async def get_authority_status(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current authority integration and cached offline-grace state. [AUTH REQUIRED]"""
    try:
        installation_info = db.query(InstallationInfo).first()
        cache_expires_at = None
        cache_within_grace = False
        last_checked_at = ensure_utc_datetime(
            installation_info.authority_last_checked_at if installation_info else None
        )
        last_successful_check_at = ensure_utc_datetime(
            installation_info.authority_last_successful_check_at if installation_info else None
        )

        if (
            installation_info
            and last_successful_check_at
            and installation_info.authority_offline_grace_days is not None
        ):
            cache_expiry_dt = last_successful_check_at + timedelta(
                days=installation_info.authority_offline_grace_days
            )
            cache_expires_at = cache_expiry_dt.isoformat()
            cache_within_grace = datetime.now(timezone.utc) <= cache_expiry_dt

        runtime_state = authority_service.derive_runtime_state(db)

        return {
            "success": True,
            "authority": {
                "enabled": settings.AUTHORITY_SERVICE_ENABLED,
                "configured": bool(
                    authority_service.is_configured()
                    and authority_service.get_effective_application_key(db)
                ),
                "service_url": settings.AUTHORITY_SERVICE_URL,
                "installation_uuid": authority_service.get_effective_installation_uuid(db),
                "resolved_installation_uuid": (
                    installation_info.authority_installation_uuid if installation_info else None
                ),
                "cached_licence_name": (
                    installation_info.authority_licence_name if installation_info else None
                ),
                "cached_tenant_name": (
                    installation_info.authority_tenant_name if installation_info else None
                ),
                "application_key_configured": bool(
                    authority_service.get_effective_application_key(db)
                ),
                "cached_owner_email": (
                    installation_info.authority_approved_owner_email if installation_info else None
                ),
                "current_user_is_approved_owner": bool(
                    installation_info
                    and installation_info.authority_approved_owner_email
                    and installation_info.authority_approved_owner_email.lower()
                    == _current_user.email.lower()
                ),
                "cached_licence_status": (
                    installation_info.authority_licence_status if installation_info else None
                ),
                "cached_owner_enabled": (
                    installation_info.authority_owner_enabled if installation_info else None
                ),
                "warning_period_days": (
                    installation_info.authority_warning_period_days if installation_info else None
                ),
                "warning_started_at": (
                    ensure_utc_datetime(installation_info.authority_warning_started_at).isoformat()
                    if installation_info and installation_info.authority_warning_started_at
                    else None
                ),
                "offline_grace_days": (
                    installation_info.authority_offline_grace_days if installation_info else None
                ),
                "last_checked_at": (
                    last_checked_at.isoformat() if last_checked_at else None
                ),
                "last_successful_check_at": (
                    last_successful_check_at.isoformat() if last_successful_check_at else None
                ),
                "last_result_reason": (
                    installation_info.authority_last_result_reason if installation_info else None
                ),
                "cache_expires_at": cache_expires_at,
                "cache_within_grace": cache_within_grace,
                "runtime_state": runtime_state["state"],
                "runtime_reason": runtime_state["reason"],
                "can_operate": runtime_state["can_operate"],
                "warning_deadline": runtime_state["warning_deadline"],
                "warning_days_remaining": runtime_state["warning_days_remaining"],
            },
        }
    except RuntimeError as e:
        logger.error("Failed to get authority status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authority status",
        ) from e


@router.post("/authority/refresh", response_model=Dict[str, Any])
async def refresh_authority_status(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force a fresh Authority lookup and update the cached metadata. [AUTH REQUIRED]"""
    try:
        result = await authority_service.refresh_cached_authority_state(db)
        return {
            "success": True,
            "refresh": result,
            "authority": (await get_authority_status(_current_user=_current_user, db=db))["authority"],
        }
    except RuntimeError as e:
        logger.error("Failed to refresh authority status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh authority status",
        ) from e


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
        ) from e


@router.get("/status", response_model=Dict[str, Any])
async def get_license_status(
    _current_user: User = Depends(get_current_user),
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
        ) from e


@router.get("/validation/user-limit", response_model=Dict[str, Any])
async def validate_user_limit(
    _current_user: User = Depends(get_current_user),
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
        ) from e


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
        ) from e


@router.get("/features", response_model=Dict[str, Any])
async def get_license_features(
    _current_user: User = Depends(get_current_user),
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
        ) from e


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
    except RuntimeError as e:
        logger.error("Licensing health check failed: %s", str(e))
        return {
            "success": False,
            "licensing_service": {"connected": False, "error": str(e)},
        }

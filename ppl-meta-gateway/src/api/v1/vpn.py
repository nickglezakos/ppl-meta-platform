from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.v1.router import extract_user_from_token
from config import settings
from services.vpn_service import vpn_service


router = APIRouter(prefix="/vpn", tags=["VPN"])


class EnrollDeviceRequest(BaseModel):
    device_type: str = Field(..., examples=["camera", "edge", "desktop", "mobile"])
    device_name: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


class VPNHealthResponse(BaseModel):
    enabled: bool
    provider: str
    ok: bool
    details: Dict[str, Any]


def _parse_admin_emails(value: str) -> List[str]:
    emails = [e.strip().lower() for e in (value or "").split(",")]
    return [e for e in emails if e]


def _require_vpn_admin(request: Request) -> Dict[str, Any]:
    user = extract_user_from_token(request)
    admin_emails = _parse_admin_emails(getattr(settings, "vpn_admin_emails", ""))

    # If unset, allow any authenticated user (development-friendly).
    if not admin_emails:
        return user

    if (user.get("email") or "").lower() not in admin_emails:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/health", response_model=VPNHealthResponse)
async def vpn_health():
    health = await vpn_service.health()
    return VPNHealthResponse(
        enabled=health.enabled,
        provider=health.provider,
        ok=health.ok,
        details=health.details,
    )


@router.post("/devices/enroll")
async def enroll_device(payload: EnrollDeviceRequest, request: Request):
    _require_vpn_admin(request)
    try:
        enrollment = await vpn_service.enroll_device(
            device_type=payload.device_type,
            device_name=payload.device_name,
            tags=payload.tags,
        )
        return {
            "auth_key": enrollment.auth_key,
            "device_id": enrollment.device_id,
            "instructions": enrollment.instructions or {},
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))


@router.get("/devices")
async def list_devices(request: Request):
    _require_vpn_admin(request)
    try:
        devices = await vpn_service.list_devices()
        return {
            "count": len(devices),
            "devices": [
                {
                    "id": d.id,
                    "name": d.name,
                    "user": d.user,
                    "online": d.online,
                    "addresses": d.addresses or [],
                }
                for d in devices
            ],
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))


@router.delete("/devices/{device_id}")
async def revoke_device(device_id: str, request: Request):
    _require_vpn_admin(request)
    try:
        await vpn_service.revoke_device(device_id)
        return {"status": "revoked", "device_id": device_id}
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))


@router.get("/devices/{device_id}/status")
async def device_status(device_id: str, request: Request):
    _require_vpn_admin(request)
    try:
        d = await vpn_service.device_status(device_id)
        return {
            "id": d.id,
            "name": d.name,
            "user": d.user,
            "online": d.online,
            "addresses": d.addresses or [],
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

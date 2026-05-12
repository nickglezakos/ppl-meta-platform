from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.storage import (
    activate_entitlement,
    find_installation_by_owner_email,
    get_installation_by_uuid,
)

router = APIRouter(prefix="/api/v1", tags=["authority"])


class InstallationRecord(BaseModel):
    installation_uuid: str
    application_key: str
    approved_owner_email: str
    owner_enabled: bool
    licence_status: str
    offline_grace_days: int
    tenant_name: str | None = None
    notes: str | None = None


class EntitlementRecord(BaseModel):
    entitlement_uuid: str
    installation_uuid: str | None = None
    application_key: str
    approved_owner_email: str
    owner_enabled: bool
    licence_status: str
    offline_grace_days: int
    tenant_name: str | None = None
    activation_status: str
    notes: str | None = None


class InstallationUpsertRequest(BaseModel):
    entitlement_uuid: str | None = None
    installation_uuid: str | None = None
    application_key: str | None = Field(default=None, min_length=3)
    approved_owner_email: str
    owner_enabled: bool = True
    licence_status: str = "active"
    offline_grace_days: int = Field(default=14, ge=0)
    tenant_name: str | None = None
    notes: str | None = None


class ActivationRequest(BaseModel):
    application_key: str = Field(min_length=3)
    installation_uuid: str = Field(min_length=3)
    owner_email: str


class ActivationResponse(BaseModel):
    approved: bool
    reason: str
    entitlement_uuid: str | None = None
    installation_uuid: str | None = None
    application_key: str | None = None
    approved_owner_email: str | None = None
    owner_enabled: bool | None = None
    licence_status: str | None = None
    offline_grace_days: int | None = None
    tenant_name: str | None = None
    activation_status: str | None = None
    notes: str | None = None


class OwnerStatusResponse(BaseModel):
    email: str
    approved: bool
    licence_status: str | None = None
    owner_enabled: bool = False
    installation_uuid: str | None = None
    activation_status: str | None = None


@router.get("/installations/{installation_uuid}", response_model=InstallationRecord)
async def get_installation(installation_uuid: str) -> InstallationRecord:
    record = get_installation_by_uuid(installation_uuid)
    if record is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    return InstallationRecord(**record)


@router.get("/owners/{email}", response_model=OwnerStatusResponse)
async def get_owner_status(email: str) -> OwnerStatusResponse:
    record = find_installation_by_owner_email(email)
    if record is None:
        return OwnerStatusResponse(email=email, approved=False)

    return OwnerStatusResponse(
        email=email,
        approved=record["owner_enabled"] and record["licence_status"] in {"active", "grace"},
        licence_status=record["licence_status"],
        owner_enabled=record["owner_enabled"],
        installation_uuid=record["installation_uuid"],
        activation_status=record["activation_status"],
    )


@router.post("/installations/activate", response_model=ActivationResponse)
async def activate_installation(payload: ActivationRequest) -> ActivationResponse:
    result = activate_entitlement(
        application_key=payload.application_key,
        installation_uuid=payload.installation_uuid,
        owner_email=payload.owner_email,
    )
    return ActivationResponse(**result)
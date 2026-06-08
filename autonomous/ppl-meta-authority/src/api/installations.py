from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.storage import (
    activate_entitlement,
    evaluate_update_eligibility,
    find_installation_by_owner_email,
    get_installation_by_application_key,
    get_entitlement_by_installation_uuid,
    get_installation_by_uuid,
    record_installation_state,
    record_update_event,
)

router = APIRouter(prefix="/api/v1", tags=["authority"])

APPLICATION_KEY_PATTERN = r"^lic_[0-9a-f]{32}$"


class InstallationRecord(BaseModel):
    installation_uuid: str
    application_key: str
    licence_name: str | None = None
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
    licence_name: str | None = None
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
    application_key: str | None = Field(default=None, pattern=APPLICATION_KEY_PATTERN)
    licence_name: str | None = None
    approved_owner_email: str
    owner_enabled: bool = True
    licence_status: str = "active"
    offline_grace_days: int = Field(default=14, ge=0)
    tenant_name: str | None = None
    notes: str | None = None


class ActivationRequest(BaseModel):
    application_key: str = Field(pattern=APPLICATION_KEY_PATTERN)
    installation_uuid: str = Field(min_length=3)
    owner_email: str


class ActivationResponse(BaseModel):
    approved: bool
    reason: str
    entitlement_uuid: str | None = None
    installation_uuid: str | None = None
    application_key: str | None = None
    licence_name: str | None = None
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


class InstallationStateReportRequest(BaseModel):
    installation_uuid: str = Field(min_length=3)
    current_release_version: str = Field(min_length=1)
    deployment_mode: str | None = None
    health_state: str | None = None
    components: dict[str, str] = Field(default_factory=dict)


class InstallationStateReportResponse(BaseModel):
    report_uuid: str
    installation_uuid: str
    current_release_version: str
    deployment_mode: str | None = None
    health_state: str | None = None
    components: dict[str, str]
    reported_at: str


class UpdateEligibilityRequest(BaseModel):
    installation_uuid: str = Field(min_length=3)
    target_release_version: str = Field(min_length=1)


class UpdateEligibilityResponse(BaseModel):
    allowed: bool
    reason: str
    installation_uuid: str | None = None
    current_release_version: str | None = None
    target_release_version: str | None = None


class UpdateResultRequest(BaseModel):
    installation_uuid: str = Field(min_length=3)
    from_release_version: str | None = None
    to_release_version: str = Field(min_length=1)
    status: str = Field(pattern="^(pending|running|succeeded|failed|rolled_back)$")
    failure_reason: str | None = None
    components: dict[str, str] = Field(default_factory=dict)


class UpdateEventResponse(BaseModel):
    update_event_uuid: str
    installation_uuid: str
    from_release_version: str | None = None
    to_release_version: str
    status: str
    failure_reason: str | None = None
    components: dict[str, str]
    created_at: str


@router.get("/installations/{installation_uuid}", response_model=InstallationRecord)
async def get_installation(installation_uuid: str) -> InstallationRecord:
    record = get_installation_by_uuid(installation_uuid)
    if record is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    return InstallationRecord(**record)


@router.get("/application-keys/{application_key}", response_model=InstallationRecord)
async def get_installation_for_application_key(application_key: str) -> InstallationRecord:
    record = get_installation_by_application_key(application_key)
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


@router.post("/installations/report-state", response_model=InstallationStateReportResponse)
async def report_installation_state(
    payload: InstallationStateReportRequest,
) -> InstallationStateReportResponse:
    entitlement = get_entitlement_by_installation_uuid(payload.installation_uuid)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    report = record_installation_state(payload.model_dump())
    return InstallationStateReportResponse(**report)


@router.post("/installations/check-update", response_model=UpdateEligibilityResponse)
async def check_installation_update(
    payload: UpdateEligibilityRequest,
) -> UpdateEligibilityResponse:
    result = evaluate_update_eligibility(
        installation_uuid=payload.installation_uuid,
        target_release_version=payload.target_release_version,
    )
    return UpdateEligibilityResponse(**result)


@router.post("/installations/report-update-result", response_model=UpdateEventResponse)
async def report_update_result(payload: UpdateResultRequest) -> UpdateEventResponse:
    entitlement = get_entitlement_by_installation_uuid(payload.installation_uuid)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    event = record_update_event(payload.model_dump())
    return UpdateEventResponse(**event)
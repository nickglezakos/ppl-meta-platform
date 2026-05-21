from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from api.installations import EntitlementRecord, InstallationUpsertRequest
from core.auth import require_platform_admin
from core.email import send_invitation_email
from core.storage import (
    assign_entitlement_to_user,
    create_invitation,
    delete_entitlement,
    get_authority_user_by_email,
    get_entitlement_by_uuid,
    list_authority_users,
    list_entitlements,
    list_invitations,
    update_invitation_email_delivery,
    upsert_entitlement,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])


class InvitationRequest(BaseModel):
    email: str
    role_name: str = Field(pattern="^(owner|reseller|distributor|support)$")
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    invitation_uuid: str
    invitation_token: str
    email: str
    role_name: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    status: str
    effective_status: str
    expires_at: str
    created_at: str
    issued_by_user_uuid: str | None = None
    accepted_at: str | None = None
    accepted_by_user_uuid: str | None = None
    is_expired: bool
    email_delivery_attempted: bool = False
    email_delivered: bool = False
    email_delivery_message: str | None = None


class InstallationAssignmentRequest(BaseModel):
    entitlement_uuid: str
    user_email: str


class InstallationAssignmentResponse(BaseModel):
    assignment_uuid: str
    user_uuid: str
    entitlement_uuid: str
    assigned_by_user_uuid: str | None = None
    created_at: str


class AuthorityUserRecord(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    role_name: str
    status: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@router.get("/installations", response_model=list[EntitlementRecord])
async def admin_list_installations() -> list[EntitlementRecord]:
    return [EntitlementRecord(**record) for record in list_entitlements()]


@router.get("/users", response_model=list[AuthorityUserRecord])
async def admin_list_users() -> list[AuthorityUserRecord]:
    return [AuthorityUserRecord(**record) for record in list_authority_users()]


@router.post("/installations", response_model=EntitlementRecord)
async def admin_upsert_installation(payload: InstallationUpsertRequest) -> EntitlementRecord:
    record = upsert_entitlement(payload.model_dump(exclude_none=True))
    return EntitlementRecord(**record)


@router.get("/installations/{entitlement_uuid}", response_model=EntitlementRecord)
async def admin_get_installation(entitlement_uuid: str) -> EntitlementRecord:
    record = get_entitlement_by_uuid(entitlement_uuid)
    if record is None:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    return EntitlementRecord(**record)


@router.delete("/installations/{entitlement_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_installation(entitlement_uuid: str) -> Response:
    deleted = delete_entitlement(entitlement_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/invitations", response_model=list[InvitationResponse])
async def admin_list_invitations() -> list[InvitationResponse]:
    return [InvitationResponse(**record) for record in list_invitations()]


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_invitation(
    payload: InvitationRequest,
    current_admin: dict[str, str] = Depends(require_platform_admin),
) -> InvitationResponse:
    if payload.role_name == "distributor" and not (payload.distributor_uuid or "").strip():
        raise HTTPException(status_code=400, detail="Distributor invitations require a distributor_uuid")

    invitation = create_invitation(
        email=payload.email,
        role_name=payload.role_name,
        distributor_uuid=payload.distributor_uuid,
        reseller_uuid=payload.reseller_uuid,
        issued_by_user_uuid=current_admin.get("user_uuid"),
        expires_in_days=payload.expires_in_days,
    )
    delivery_result = send_invitation_email(invitation, issuer_email=current_admin.get("email"))
    invitation = update_invitation_email_delivery(
        invitation_uuid=invitation["invitation_uuid"],
        attempted=delivery_result.attempted,
        delivered=delivery_result.delivered,
        message=delivery_result.message,
    )
    return InvitationResponse(**invitation)


@router.post("/installation-assignments", response_model=InstallationAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def admin_assign_installation(
    payload: InstallationAssignmentRequest,
    current_admin: dict[str, str] = Depends(require_platform_admin),
) -> InstallationAssignmentResponse:
    entitlement = get_entitlement_by_uuid(payload.entitlement_uuid)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    user = get_authority_user_by_email(payload.user_email)
    if user is None:
        raise HTTPException(status_code=404, detail="Authority user not found")

    assignment = assign_entitlement_to_user(
        entitlement_uuid=payload.entitlement_uuid,
        user_uuid=user["user_uuid"],
        assigned_by_user_uuid=current_admin.get("user_uuid"),
    )
    return InstallationAssignmentResponse(**assignment)
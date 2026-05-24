from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import require_distributor_or_platform_admin
from core.email import send_invitation_email
from core.storage import (
    assign_entitlement_to_user,
    create_invitation,
    get_authority_user_by_email,
    get_authority_user_by_uuid,
    get_entitlement_by_uuid,
    list_owner_users_by_distributor_uuid,
    list_reseller_users_by_distributor_uuid,
    set_authority_user_status,
    update_invitation_email_delivery,
)

router = APIRouter(prefix="/api/v1/distributor", tags=["distributor"])


class DistributorInvitationRequest(BaseModel):
    email: str
    role_name: str = Field(default="reseller", pattern="^(reseller|owner)$")
    reseller_uuid: str | None = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class DistributorInvitationResponse(BaseModel):
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


class DistributorScopedUserResponse(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    role_name: str
    status: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DistributorInstallationAssignmentRequest(BaseModel):
    entitlement_uuid: str
    user_email: str


class DistributorInstallationAssignmentResponse(BaseModel):
    assignment_uuid: str
    user_uuid: str
    entitlement_uuid: str
    assigned_by_user_uuid: str | None = None
    created_at: str


class DistributorUserStatusChangeRequest(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")
    reason_code: str = Field(min_length=1)
    operator_note: str | None = None


def _resolve_distributor_scope(current_user: dict[str, str], requested_distributor_uuid: str | None = None) -> str | None:
    if current_user["role_name"] == "platform_admin":
        return requested_distributor_uuid

    distributor_uuid = current_user.get("distributor_uuid")
    if not distributor_uuid:
        raise HTTPException(status_code=400, detail="Distributor account is not scoped to a distributor_uuid")
    if requested_distributor_uuid and requested_distributor_uuid != distributor_uuid:
        raise HTTPException(status_code=403, detail="Requested distributor scope does not match current distributor account")
    return distributor_uuid


def _validate_distributor_user_status_target(
    current_user: dict[str, str],
    target_user: dict[str, str],
) -> None:
    if target_user["role_name"] != "reseller":
        raise HTTPException(status_code=403, detail="Distributor may only suspend or reinstate reseller users")

    distributor_uuid = _resolve_distributor_scope(current_user, target_user.get("distributor_uuid"))
    if current_user["role_name"] != "platform_admin" and distributor_uuid != current_user.get("distributor_uuid"):
        raise HTTPException(status_code=403, detail="Target reseller is outside distributor scope")


@router.get("/resellers", response_model=list[DistributorScopedUserResponse])
async def distributor_list_resellers(
    current_user: dict[str, str] = Depends(require_distributor_or_platform_admin),
) -> list[DistributorScopedUserResponse]:
    distributor_uuid = _resolve_distributor_scope(current_user, current_user.get("distributor_uuid"))
    if current_user["role_name"] == "platform_admin" and not distributor_uuid:
        raise HTTPException(status_code=400, detail="Distributor scope is required to list reseller users")
    return [DistributorScopedUserResponse(**record) for record in list_reseller_users_by_distributor_uuid(distributor_uuid)]


@router.get("/owners", response_model=list[DistributorScopedUserResponse])
async def distributor_list_owners(
    current_user: dict[str, str] = Depends(require_distributor_or_platform_admin),
) -> list[DistributorScopedUserResponse]:
    distributor_uuid = _resolve_distributor_scope(current_user, current_user.get("distributor_uuid"))
    if current_user["role_name"] == "platform_admin" and not distributor_uuid:
        raise HTTPException(status_code=400, detail="Distributor scope is required to list owner users")
    return [DistributorScopedUserResponse(**record) for record in list_owner_users_by_distributor_uuid(distributor_uuid)]


@router.post("/invitations", response_model=DistributorInvitationResponse, status_code=status.HTTP_201_CREATED)
async def distributor_create_reseller_invitation(
    payload: DistributorInvitationRequest,
    current_user: dict[str, str] = Depends(require_distributor_or_platform_admin),
) -> DistributorInvitationResponse:
    distributor_uuid = _resolve_distributor_scope(current_user, current_user.get("distributor_uuid"))
    reseller_uuid = (payload.reseller_uuid or "").strip() or None
    invitation = create_invitation(
        email=payload.email,
        role_name=payload.role_name,
        distributor_uuid=distributor_uuid,
        reseller_uuid=reseller_uuid,
        issued_by_user_uuid=current_user.get("user_uuid"),
        expires_in_days=payload.expires_in_days,
    )
    delivery_result = send_invitation_email(invitation, issuer_email=current_user.get("email"))
    invitation = update_invitation_email_delivery(
        invitation_uuid=invitation["invitation_uuid"],
        attempted=delivery_result.attempted,
        delivered=delivery_result.delivered,
        message=delivery_result.message,
    )
    return DistributorInvitationResponse(**invitation)


@router.post(
    "/installation-assignments",
    response_model=DistributorInstallationAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def distributor_assign_installation(
    payload: DistributorInstallationAssignmentRequest,
    current_user: dict[str, str] = Depends(require_distributor_or_platform_admin),
) -> DistributorInstallationAssignmentResponse:
    entitlement = get_entitlement_by_uuid(payload.entitlement_uuid)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    user = get_authority_user_by_email(payload.user_email)
    if user is None:
        raise HTTPException(status_code=404, detail="Authority user not found")
    if user["role_name"] != "owner":
        raise HTTPException(status_code=400, detail="Only owner users can receive installation assignments")

    distributor_uuid = _resolve_distributor_scope(current_user, user.get("distributor_uuid"))
    if current_user["role_name"] != "platform_admin" and not distributor_uuid:
        raise HTTPException(status_code=403, detail="Distributor assignment requires a scoped distributor_uuid")
    if current_user["role_name"] != "platform_admin" and entitlement["approved_owner_email"].lower() != user["email"].lower():
        raise HTTPException(status_code=403, detail="Distributor may only assign entitlements to the approved owner email")

    assignment = assign_entitlement_to_user(
        entitlement_uuid=payload.entitlement_uuid,
        user_uuid=user["user_uuid"],
        assigned_by_user_uuid=current_user.get("user_uuid"),
    )
    return DistributorInstallationAssignmentResponse(**assignment)


@router.patch("/users/{user_uuid}/status", response_model=DistributorScopedUserResponse)
async def distributor_update_user_status(
    user_uuid: str,
    payload: DistributorUserStatusChangeRequest,
    current_user: dict[str, str] = Depends(require_distributor_or_platform_admin),
) -> DistributorScopedUserResponse:
    target_user = get_authority_user_by_uuid(user_uuid)
    if target_user is None:
        raise HTTPException(status_code=404, detail="Authority user not found")

    _validate_distributor_user_status_target(current_user, target_user)

    try:
        user = set_authority_user_status(
            user_uuid=user_uuid,
            status=payload.status,
            actor_user_uuid=current_user.get("user_uuid"),
            actor_role_name=current_user.get("role_name"),
            reason_code=payload.reason_code,
            operator_note=payload.operator_note,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("not found") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return DistributorScopedUserResponse(**user)
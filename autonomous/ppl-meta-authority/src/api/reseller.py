from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import require_reseller_or_platform_admin
from core.email import send_invitation_email
from core.storage import (
    assign_entitlement_to_user,
    create_invitation,
    find_installation_by_owner_email,
    get_authority_user_by_email,
    get_authority_user_by_uuid,
    get_entitlement_by_uuid,
    set_authority_user_status,
    update_invitation_email_delivery,
)

router = APIRouter(prefix="/api/v1/reseller", tags=["reseller"])


class ResellerInvitationRequest(BaseModel):
    email: str
    role_name: str = Field(default="owner", pattern="^(owner)$")
    expires_in_days: int = Field(default=7, ge=1, le=30)


class ResellerInvitationResponse(BaseModel):
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


class ResellerInstallationAssignmentRequest(BaseModel):
    entitlement_uuid: str
    user_email: str


class ResellerInstallationAssignmentResponse(BaseModel):
    assignment_uuid: str
    user_uuid: str
    entitlement_uuid: str
    assigned_by_user_uuid: str | None = None
    created_at: str


class ResellerScopedUserResponse(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    role_name: str
    status: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ResellerUserStatusChangeRequest(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")
    reason_code: str = Field(min_length=1)
    operator_note: str | None = None


def _resolve_reseller_scope(current_user: dict[str, str], requested_reseller_uuid: str | None = None) -> str | None:
    if current_user["role_name"] == "platform_admin":
        return requested_reseller_uuid
    # reseller scope must be present and fixed to the current session
    reseller_uuid = current_user.get("reseller_uuid")
    if not reseller_uuid:
        raise HTTPException(status_code=400, detail="Reseller account is not scoped to a reseller_uuid")
    if requested_reseller_uuid and requested_reseller_uuid != reseller_uuid:
        raise HTTPException(status_code=403, detail="Requested reseller scope does not match current reseller account")
    return reseller_uuid


def _validate_reseller_user_status_target(
    current_user: dict[str, str],
    target_user: dict[str, str],
) -> None:
    if target_user["role_name"] != "owner":
        raise HTTPException(status_code=403, detail="Reseller may only suspend or reinstate owner users")

    reseller_uuid = _resolve_reseller_scope(current_user, target_user.get("reseller_uuid"))
    if current_user["role_name"] != "platform_admin" and reseller_uuid != current_user.get("reseller_uuid"):
        raise HTTPException(status_code=403, detail="Target owner is outside reseller scope")


@router.post("/invitations", response_model=ResellerInvitationResponse, status_code=status.HTTP_201_CREATED)
async def reseller_create_owner_invitation(
    payload: ResellerInvitationRequest,
    current_user: dict[str, str] = Depends(require_reseller_or_platform_admin),
) -> ResellerInvitationResponse:
    reseller_uuid = _resolve_reseller_scope(current_user)
    if find_installation_by_owner_email(payload.email) is None:
        raise HTTPException(
            status_code=400,
            detail="Create an entitlement for this owner email before sending an owner invitation",
        )
    invitation = create_invitation(
        email=payload.email,
        role_name="owner",
        distributor_uuid=current_user.get("distributor_uuid"),
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
    return ResellerInvitationResponse(**invitation)


@router.post(
    "/installation-assignments",
    response_model=ResellerInstallationAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reseller_assign_installation(
    payload: ResellerInstallationAssignmentRequest,
    current_user: dict[str, str] = Depends(require_reseller_or_platform_admin),
) -> ResellerInstallationAssignmentResponse:
    entitlement = get_entitlement_by_uuid(payload.entitlement_uuid)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    user = get_authority_user_by_email(payload.user_email)
    if user is None:
        raise HTTPException(status_code=404, detail="Authority user not found")
    if user["role_name"] != "owner":
        raise HTTPException(status_code=400, detail="Only owner users can receive installation assignments")

    reseller_uuid = _resolve_reseller_scope(current_user, user.get("reseller_uuid"))
    if current_user["role_name"] != "platform_admin" and entitlement["approved_owner_email"].lower() != user["email"].lower():
        raise HTTPException(status_code=403, detail="Reseller may only assign entitlements to the approved owner email")
    if current_user["role_name"] != "platform_admin" and not reseller_uuid:
        raise HTTPException(status_code=403, detail="Reseller assignment requires a scoped reseller_uuid")

    assignment = assign_entitlement_to_user(
        entitlement_uuid=payload.entitlement_uuid,
        user_uuid=user["user_uuid"],
        assigned_by_user_uuid=current_user.get("user_uuid"),
    )
    return ResellerInstallationAssignmentResponse(**assignment)


@router.patch("/users/{user_uuid}/status", response_model=ResellerScopedUserResponse)
async def reseller_update_user_status(
    user_uuid: str,
    payload: ResellerUserStatusChangeRequest,
    current_user: dict[str, str] = Depends(require_reseller_or_platform_admin),
) -> ResellerScopedUserResponse:
    target_user = get_authority_user_by_uuid(user_uuid)
    if target_user is None:
        raise HTTPException(status_code=404, detail="Authority user not found")

    _validate_reseller_user_status_target(current_user, target_user)

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

    return ResellerScopedUserResponse(**user)

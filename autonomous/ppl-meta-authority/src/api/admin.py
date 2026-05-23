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
    list_authority_audit_events,
    list_authority_users,
    list_entitlements,
    list_invitations,
    reassign_authority_user_scope,
    set_authority_user_status,
    set_entitlement_activation_status,
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


class UserStatusChangeRequest(BaseModel):
    status: str = Field(pattern="^(active|suspended|removed|orphaned)$")
    reason_code: str = Field(min_length=1)
    operator_note: str | None = None


class EntitlementStatusChangeRequest(BaseModel):
    activation_status: str = Field(pattern="^(pending_activation|active|suspended|revoked|expired|orphaned)$")
    reason_code: str = Field(min_length=1)
    operator_note: str | None = None


class AuditEventRecord(BaseModel):
    audit_event_uuid: str
    actor_user_uuid: str | None = None
    actor_email: str | None = None
    actor_role_name: str | None = None
    target_entity_type: str
    target_entity_uuid: str
    target_email: str | None = None
    action: str
    previous_state: dict | None = None
    new_state: dict | None = None
    scope_before: dict | None = None
    scope_after: dict | None = None
    reason_code: str | None = None
    operator_note: str | None = None
    created_at: str | None = None


class AuditEventListResponse(BaseModel):
    items: list[AuditEventRecord]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None = None


class UserScopeReassignmentRequest(BaseModel):
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    reason_code: str = Field(min_length=1)
    operator_note: str | None = None


@router.get("/installations", response_model=list[EntitlementRecord])
async def admin_list_installations() -> list[EntitlementRecord]:
    return [EntitlementRecord(**record) for record in list_entitlements()]


@router.get("/users", response_model=list[AuthorityUserRecord])
async def admin_list_users() -> list[AuthorityUserRecord]:
    return [AuthorityUserRecord(**record) for record in list_authority_users()]


@router.get("/audit-events", response_model=AuditEventListResponse)
async def admin_list_audit_events(
    limit: int = 100,
    offset: int = 0,
    target_entity_type: str | None = None,
    target_entity_uuid: str | None = None,
    action: str | None = None,
    actor_role_name: str | None = None,
) -> AuditEventListResponse:
    records = list_authority_audit_events(
            limit=limit + 1,
            offset=offset,
            target_entity_type=target_entity_type,
            target_entity_uuid=target_entity_uuid,
            action=action,
            actor_role_name=actor_role_name,
        )
    has_more = len(records) > limit
    items = records[:limit]
    next_offset = offset + len(items) if has_more else None
    return AuditEventListResponse(
        items=[AuditEventRecord(**record) for record in items],
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_offset=next_offset,
    )


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


@router.patch("/users/{user_uuid}/status", response_model=AuthorityUserRecord)
async def admin_update_user_status(
    user_uuid: str,
    payload: UserStatusChangeRequest,
    current_admin: dict[str, str] = Depends(require_platform_admin),
) -> AuthorityUserRecord:
    try:
        user = set_authority_user_status(
            user_uuid=user_uuid,
            status=payload.status,
            actor_user_uuid=current_admin.get("user_uuid"),
            actor_role_name=current_admin.get("role_name"),
            reason_code=payload.reason_code,
            operator_note=payload.operator_note,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("not found") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return AuthorityUserRecord(**user)


@router.patch("/users/{user_uuid}/scope", response_model=AuthorityUserRecord)
async def admin_reassign_user_scope(
    user_uuid: str,
    payload: UserScopeReassignmentRequest,
    current_admin: dict[str, str] = Depends(require_platform_admin),
) -> AuthorityUserRecord:
    try:
        user = reassign_authority_user_scope(
            user_uuid=user_uuid,
            distributor_uuid=payload.distributor_uuid,
            reseller_uuid=payload.reseller_uuid,
            actor_user_uuid=current_admin.get("user_uuid"),
            actor_role_name=current_admin.get("role_name"),
            reason_code=payload.reason_code,
            operator_note=payload.operator_note,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("not found") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return AuthorityUserRecord(**user)


@router.patch("/installations/{entitlement_uuid}/activation-status", response_model=EntitlementRecord)
async def admin_update_entitlement_status(
    entitlement_uuid: str,
    payload: EntitlementStatusChangeRequest,
    current_admin: dict[str, str] = Depends(require_platform_admin),
) -> EntitlementRecord:
    try:
        entitlement = set_entitlement_activation_status(
            entitlement_uuid=entitlement_uuid,
            activation_status=payload.activation_status,
            actor_user_uuid=current_admin.get("user_uuid"),
            actor_role_name=current_admin.get("role_name"),
            reason_code=payload.reason_code,
            operator_note=payload.operator_note,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("not found") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return EntitlementRecord(**entitlement)


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
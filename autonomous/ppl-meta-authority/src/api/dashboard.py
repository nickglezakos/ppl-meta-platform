from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import require_authority_user
from core.storage import (
    list_entitlements,
    list_authority_users,
    list_entitlements_for_distributor_uuid,
    list_entitlements_for_reseller_uuid,
    list_entitlements_for_user_uuid,
    list_invitations,
    list_entitlements_for_owner_email,
    list_entitlements_for_owner_emails,
    list_owner_users_by_distributor_uuid,
    list_owner_users_by_reseller_uuid,
    list_recent_assignment_activity,
    list_recent_state_reports,
    list_recent_state_reports_for_distributor,
    list_recent_state_reports_for_owner,
    list_recent_state_reports_for_reseller,
    list_reseller_users_by_distributor_uuid,
    list_recent_update_events_for_owner,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class DashboardInstallation(BaseModel):
    entitlement_uuid: str
    installation_uuid: str | None = None
    application_key: str
    approved_owner_email: str
    owner_enabled: bool
    licence_status: str
    warning_period_days: int = 0
    warning_started_at: str | None = None
    offline_grace_days: int
    tenant_name: str | None = None
    activation_status: str
    notes: str | None = None


class ResellerOwnerSummary(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    role_name: str
    status: str
    installation_count: int


class ResellerDashboardSummary(BaseModel):
    reseller_uuid: str
    owner_count: int
    orphaned_owner_count: int
    suspended_owner_count: int
    installation_count: int
    active_installation_count: int
    pending_activation_count: int
    pending_invitation_count: int
    owners: list[ResellerOwnerSummary]
    installations: list[DashboardInstallation]
    recent_assignments: list["AssignmentActivity"]
    recent_health_reports: list["StateReportActivity"]


class DistributorResellerSummary(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    reseller_uuid: str | None = None
    status: str
    owner_count: int


class DistributorOwnerSummary(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    reseller_uuid: str | None = None
    status: str
    installation_count: int


class DistributorDashboardSummary(BaseModel):
    distributor_uuid: str
    reseller_count: int
    orphaned_reseller_count: int
    suspended_reseller_count: int
    owner_count: int
    orphaned_owner_count: int
    suspended_owner_count: int
    installation_count: int
    active_installation_count: int
    pending_invitation_count: int
    resellers: list[DistributorResellerSummary]
    owners: list[DistributorOwnerSummary]
    installations: list[DashboardInstallation]
    recent_assignments: list["AssignmentActivity"]
    recent_health_reports: list["StateReportActivity"]


class AssignmentActivity(BaseModel):
    assignment_uuid: str
    user_uuid: str
    entitlement_uuid: str
    assigned_by_user_uuid: str | None = None
    created_at: str
    owner_email: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    application_key: str
    tenant_name: str | None = None
    activation_status: str


class InvitationActivity(BaseModel):
    invitation_uuid: str
    email: str
    role_name: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    status: str
    effective_status: str
    created_at: str
    expires_at: str
    accepted_at: str | None = None


class AdminDashboardSummary(BaseModel):
    entitlement_count: int
    active_entitlement_count: int
    pending_activation_count: int
    pending_invitation_count: int
    suspended_user_count: int
    orphaned_user_count: int
    recent_invitations: list[InvitationActivity]
    recent_assignments: list[AssignmentActivity]
    recent_health_reports: list[StateReportActivity]


class OwnerUpdateActivity(BaseModel):
    update_event_uuid: str
    installation_uuid: str
    from_release_version: str | None = None
    to_release_version: str
    status: str
    failure_reason: str | None = None
    components: dict[str, str]
    created_at: str
    entitlement_uuid: str
    application_key: str
    tenant_name: str | None = None
    approved_owner_email: str
    activation_status: str
    licence_status: str


class OwnerDashboardSummary(BaseModel):
    installation_count: int
    active_installation_count: int
    grace_installation_count: int
    pending_activation_count: int
    orphaned_installation_count: int
    suspended_installation_count: int
    recent_updates: list[OwnerUpdateActivity]
    recent_health_reports: list["StateReportActivity"]


class StateReportActivity(BaseModel):
    report_uuid: str
    installation_uuid: str
    current_release_version: str
    deployment_mode: str | None = None
    health_state: str | None = None
    components: dict[str, str]
    reported_at: str
    entitlement_uuid: str
    application_key: str
    tenant_name: str | None = None
    approved_owner_email: str
    activation_status: str
    licence_status: str


ResellerDashboardSummary.model_rebuild()
DistributorDashboardSummary.model_rebuild()
OwnerDashboardSummary.model_rebuild()
AdminDashboardSummary.model_rebuild()


@router.get("/admin/summary", response_model=AdminDashboardSummary)
async def admin_summary(
    current_user: dict[str, str] = Depends(require_authority_user),
) -> AdminDashboardSummary:
    if current_user["role_name"] != "platform_admin":
        raise HTTPException(status_code=403, detail="Platform admin role required")

    entitlements = list_entitlements()
    users = list_authority_users()
    invitations = list_invitations()
    recent_invitations = invitations[:5]
    recent_assignments = list_recent_assignment_activity(limit=5)
    recent_health_reports = list_recent_state_reports(limit=5)

    return AdminDashboardSummary(
        entitlement_count=len(entitlements),
        active_entitlement_count=sum(1 for record in entitlements if record["activation_status"] == "active"),
        pending_activation_count=sum(
            1 for record in entitlements if record["activation_status"] == "pending_activation"
        ),
        pending_invitation_count=sum(1 for record in invitations if record["effective_status"] == "pending"),
        suspended_user_count=sum(1 for user in users if user["status"] == "suspended"),
        orphaned_user_count=sum(1 for user in users if user["status"] == "orphaned"),
        recent_invitations=[InvitationActivity(**record) for record in recent_invitations],
        recent_assignments=[AssignmentActivity(**record) for record in recent_assignments],
        recent_health_reports=[StateReportActivity(**record) for record in recent_health_reports],
    )


@router.get("/owner/installations", response_model=list[DashboardInstallation])
async def owner_installations(
    current_user: dict[str, str] = Depends(require_authority_user),
) -> list[DashboardInstallation]:
    if current_user["role_name"] not in {"owner", "platform_admin", "support"}:
        raise HTTPException(status_code=403, detail="Owner, support, or platform admin role required")

    records = list_entitlements_for_user_uuid(current_user["user_uuid"])
    if not records:
        records = list_entitlements_for_owner_email(current_user["email"])
    return [DashboardInstallation(**record) for record in records]


@router.get("/owner/summary", response_model=OwnerDashboardSummary)
async def owner_summary(
    current_user: dict[str, str] = Depends(require_authority_user),
) -> OwnerDashboardSummary:
    if current_user["role_name"] not in {"owner", "platform_admin", "support"}:
        raise HTTPException(status_code=403, detail="Owner, support, or platform admin role required")

    records = list_entitlements_for_user_uuid(current_user["user_uuid"])
    if not records:
        records = list_entitlements_for_owner_email(current_user["email"])

    recent_updates = list_recent_update_events_for_owner(current_user["email"], limit=5)
    recent_health_reports = list_recent_state_reports_for_owner(current_user["email"], limit=5)

    return OwnerDashboardSummary(
        installation_count=len(records),
        active_installation_count=sum(1 for record in records if record["licence_status"] == "active"),
        grace_installation_count=sum(1 for record in records if record["licence_status"] == "grace"),
        pending_activation_count=sum(1 for record in records if record["activation_status"] == "pending_activation"),
        orphaned_installation_count=sum(1 for record in records if record["activation_status"] == "orphaned"),
        suspended_installation_count=sum(1 for record in records if record["activation_status"] == "suspended"),
        recent_updates=[OwnerUpdateActivity(**record) for record in recent_updates],
        recent_health_reports=[StateReportActivity(**record) for record in recent_health_reports],
    )


@router.get("/reseller/summary", response_model=ResellerDashboardSummary)
async def reseller_summary(
    current_user: dict[str, str] = Depends(require_authority_user),
) -> ResellerDashboardSummary:
    if current_user["role_name"] != "reseller":
        raise HTTPException(status_code=403, detail="Reseller role required")
    if not current_user.get("reseller_uuid"):
        raise HTTPException(status_code=400, detail="Reseller account is not scoped to a reseller_uuid")

    owners = list_owner_users_by_reseller_uuid(current_user["reseller_uuid"])
    installations = list_entitlements_for_reseller_uuid(current_user["reseller_uuid"])
    invitations = [
        record for record in list_invitations()
        if record.get("reseller_uuid") == current_user["reseller_uuid"]
    ]
    recent_assignments = list_recent_assignment_activity(limit=5, reseller_uuid=current_user["reseller_uuid"])
    recent_health_reports = list_recent_state_reports_for_reseller(current_user["reseller_uuid"], limit=5)

    if not installations:
        owner_emails = [owner["email"] for owner in owners if owner["role_name"] == "owner"]
        installations = list_entitlements_for_owner_emails(owner_emails)

    installations_by_email: dict[str, int] = {}
    for installation in installations:
        email = installation["approved_owner_email"].lower()
        installations_by_email[email] = installations_by_email.get(email, 0) + 1

    owner_summaries = [
        ResellerOwnerSummary(
            user_uuid=owner["user_uuid"],
            email=owner["email"],
            display_name=owner["display_name"],
            role_name=owner["role_name"],
            status=owner["status"],
            installation_count=installations_by_email.get(owner["email"].lower(), 0),
        )
        for owner in owners
        if owner["role_name"] == "owner"
    ]

    return ResellerDashboardSummary(
        reseller_uuid=current_user["reseller_uuid"],
        owner_count=len(owner_summaries),
        orphaned_owner_count=sum(1 for owner in owner_summaries if owner.status == "orphaned"),
        suspended_owner_count=sum(1 for owner in owner_summaries if owner.status == "suspended"),
        installation_count=len(installations),
        active_installation_count=sum(1 for installation in installations if installation["activation_status"] == "active"),
        pending_activation_count=sum(
            1 for installation in installations if installation["activation_status"] == "pending_activation"
        ),
        pending_invitation_count=sum(1 for invitation in invitations if invitation["effective_status"] == "pending"),
        owners=owner_summaries,
        installations=[DashboardInstallation(**record) for record in installations],
        recent_assignments=[AssignmentActivity(**record) for record in recent_assignments],
        recent_health_reports=[StateReportActivity(**record) for record in recent_health_reports],
    )


@router.get("/distributor/summary", response_model=DistributorDashboardSummary)
async def distributor_summary(
    current_user: dict[str, str] = Depends(require_authority_user),
) -> DistributorDashboardSummary:
    if current_user["role_name"] != "distributor":
        raise HTTPException(status_code=403, detail="Distributor role required")
    if not current_user.get("distributor_uuid"):
        raise HTTPException(status_code=400, detail="Distributor account is not scoped to a distributor_uuid")

    distributor_uuid = current_user["distributor_uuid"]
    resellers = list_reseller_users_by_distributor_uuid(distributor_uuid)
    owners = list_owner_users_by_distributor_uuid(distributor_uuid)
    installations = list_entitlements_for_distributor_uuid(distributor_uuid)
    invitations = [
        record for record in list_invitations()
        if record.get("distributor_uuid") == distributor_uuid
    ]
    recent_assignments = list_recent_assignment_activity(limit=5, distributor_uuid=distributor_uuid)
    recent_health_reports = list_recent_state_reports_for_distributor(distributor_uuid, limit=5)

    owner_count_by_reseller: dict[str, int] = {}
    for owner in owners:
        reseller_uuid = owner.get("reseller_uuid") or ""
        owner_count_by_reseller[reseller_uuid] = owner_count_by_reseller.get(reseller_uuid, 0) + 1

    reseller_summaries = [
        DistributorResellerSummary(
            user_uuid=reseller["user_uuid"],
            email=reseller["email"],
            display_name=reseller["display_name"],
            reseller_uuid=reseller.get("reseller_uuid"),
            status=reseller["status"],
            owner_count=owner_count_by_reseller.get(reseller.get("reseller_uuid") or "", 0),
        )
        for reseller in resellers
    ]

    installations_by_email: dict[str, int] = {}
    for installation in installations:
        email = installation["approved_owner_email"].lower()
        installations_by_email[email] = installations_by_email.get(email, 0) + 1

    owner_summaries = [
        DistributorOwnerSummary(
            user_uuid=owner["user_uuid"],
            email=owner["email"],
            display_name=owner["display_name"],
            reseller_uuid=owner.get("reseller_uuid"),
            status=owner["status"],
            installation_count=installations_by_email.get(owner["email"].lower(), 0),
        )
        for owner in owners
    ]

    return DistributorDashboardSummary(
        distributor_uuid=distributor_uuid,
        reseller_count=len(reseller_summaries),
        orphaned_reseller_count=sum(1 for reseller in reseller_summaries if reseller.status == "orphaned"),
        suspended_reseller_count=sum(1 for reseller in reseller_summaries if reseller.status == "suspended"),
        owner_count=len(owners),
        orphaned_owner_count=sum(1 for owner in owner_summaries if owner.status == "orphaned"),
        suspended_owner_count=sum(1 for owner in owner_summaries if owner.status == "suspended"),
        installation_count=len(installations),
        active_installation_count=sum(1 for installation in installations if installation["activation_status"] == "active"),
        pending_invitation_count=sum(1 for invitation in invitations if invitation["effective_status"] == "pending"),
        resellers=reseller_summaries,
        owners=owner_summaries,
        installations=[DashboardInstallation(**record) for record in installations],
        recent_assignments=[AssignmentActivity(**record) for record in recent_assignments],
        recent_health_reports=[StateReportActivity(**record) for record in recent_health_reports],
    )

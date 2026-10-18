"""Reconcile Presence People Profiles with installation user accounts."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Any, Optional

from models.presence_models import (
    PresencePeopleProfile,
    PeopleUserSyncReport,
)

logger = logging.getLogger(__name__)

# Immediate attempt, then short backoff so a parallel node boot can finish
# without waiting for the regular interval (default 300s).
PEOPLE_USER_STARTUP_RETRY_DELAYS_SECONDS: tuple[int, ...] = (0, 2, 5, 10, 20, 30)


async def retry_people_user_sync_until_ok(
    sync: Callable[[], Awaitable[PeopleUserSyncReport]],
    *,
    delays: Sequence[int] = PEOPLE_USER_STARTUP_RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> PeopleUserSyncReport | None:
    """Retry a people-user sync until it has no errors, or delays are exhausted."""
    last_report: PeopleUserSyncReport | None = None
    total = len(delays)
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            await sleep(delay)
        try:
            last_report = await sync()
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "people-user startup sync attempt %s/%s raised: %s",
                attempt,
                total,
                exc,
            )
            continue
        if not last_report.errors:
            return last_report
        logger.warning(
            "people-user startup sync attempt %s/%s failed: %s",
            attempt,
            total,
            "; ".join(last_report.errors),
        )
    return last_report


def normalize_email(email: Optional[str]) -> Optional[str]:
    if email is None:
        return None
    value = str(email).strip().lower()
    return value or None


def user_display_name(user: dict[str, Any]) -> str:
    """People-profile display name from account fields.

    Prefer real-name fields; if none are set, use the full email (not username
    and not the local-part). Username is only a last resort when email is missing.
    """
    given = (user.get("given_name") or "").strip()
    if given:
        return given
    full = (user.get("name") or "").strip()
    if full:
        return full
    email = normalize_email(user.get("email"))
    if email:
        return email
    username = (user.get("username") or "").strip()
    if username:
        return username
    return "user"


def user_is_eligible(user: dict[str, Any]) -> bool:
    if not user:
        return False
    if user.get("is_active") is False:
        return False
    if user.get("blocked") is True:
        return False
    return normalize_email(user.get("email")) is not None


class PeopleUserAssociationService:
    """Email-based association between PPPs and node user accounts."""

    def __init__(
        self,
        *,
        get_profiles: Callable[[], dict[str, PresencePeopleProfile]],
        save_profile: Callable[[PresencePeopleProfile], None],
        list_users: Callable[[], Any],
        emit_association_log: Callable[..., Any],
    ) -> None:
        self._get_profiles = get_profiles
        self._save_profile = save_profile
        self._list_users = list_users
        self._emit_association_log = emit_association_log
        self.last_report: Optional[PeopleUserSyncReport] = None

    def find_active_by_email(self, email: Optional[str]) -> Optional[PresencePeopleProfile]:
        normalized = normalize_email(email)
        if not normalized:
            return None
        matches = [
            p
            for p in self._get_profiles().values()
            if p.status == "active" and normalize_email(p.email) == normalized
        ]
        if not matches:
            return None
        matches.sort(
            key=lambda p: (-(p.linked_member_count or 0), p.created_at or datetime.utcnow())
        )
        return matches[0]

    def apply_user_to_profile(
        self,
        profile: PresencePeopleProfile,
        user: dict[str, Any],
        *,
        reason: str,
        report: PeopleUserSyncReport,
    ) -> None:
        user_guid = str(user.get("guid") or user.get("user_uuid") or "").strip()
        email = normalize_email(user.get("email"))
        desired_name = user_display_name(user)
        name_before = profile.name
        linked_before = profile.linked_user_uuid
        changed = False

        if email and normalize_email(profile.email) != email:
            profile.email = email
            changed = True

        if user_guid and profile.linked_user_uuid != user_guid:
            profile.linked_user_uuid = user_guid
            changed = True

        if profile.name != desired_name:
            profile.name = desired_name
            changed = True

        if not changed:
            report.unchanged += 1
            return

        profile.association_updated_at = datetime.utcnow()
        profile.updated_at = datetime.utcnow()
        self._save_profile(profile)

        if linked_before != profile.linked_user_uuid:
            report.linked += 1
        if name_before != profile.name:
            report.updated_name += 1
        if linked_before == profile.linked_user_uuid and name_before == profile.name:
            # email-only change
            report.linked += 1

        outcome = "updated_name" if name_before != profile.name else "linked"
        if linked_before != profile.linked_user_uuid and name_before == profile.name:
            outcome = "linked"
        elif linked_before != profile.linked_user_uuid:
            outcome = "linked"

        self._emit_association_log(
            outcome=outcome,
            reason=reason,
            email=email,
            user_guid=user_guid or None,
            ppp_uuid=profile.ppp_uuid,
            name_before=name_before,
            name_after=profile.name,
        )

    def ensure_profile_for_user(
        self,
        user: dict[str, Any],
        *,
        reason: str = "user_create",
        installation_uuid: str = "local-installation",
    ) -> PresencePeopleProfile:
        """Create or update the active PPP for one user account (register path)."""
        report = PeopleUserSyncReport(reason=reason, started_at=datetime.utcnow())
        if not user_is_eligible(user):
            report.errors.append("user_not_eligible")
            report.finished_at = datetime.utcnow()
            self.last_report = report
            raise ValueError("User is not eligible for a people profile (need active email)")

        email = normalize_email(user.get("email"))
        existing = self.find_active_by_email(email)
        if existing is None:
            profile = self.create_profile_for_user(
                user,
                reason=reason,
                report=report,
                installation_uuid=installation_uuid,
            )
        else:
            self.apply_user_to_profile(existing, user, reason=reason, report=report)
            profile = existing

        report.finished_at = datetime.utcnow()
        self.last_report = report
        return profile

    def create_profile_for_user(
        self,
        user: dict[str, Any],
        *,
        reason: str,
        report: PeopleUserSyncReport,
        installation_uuid: str = "local-installation",
    ) -> PresencePeopleProfile:
        email = normalize_email(user.get("email"))
        user_guid = str(user.get("guid") or "").strip() or None
        profile = PresencePeopleProfile(
            name=user_display_name(user),
            email=email,
            linked_user_uuid=user_guid,
            association_updated_at=datetime.utcnow(),
            installation_uuid=installation_uuid,
        )
        self._save_profile(profile)
        report.created += 1
        self._emit_association_log(
            outcome="created",
            reason=reason,
            email=email,
            user_guid=user_guid,
            ppp_uuid=profile.ppp_uuid,
            name_before=None,
            name_after=profile.name,
        )
        return profile

    def unlink_profile(
        self,
        profile: PresencePeopleProfile,
        *,
        reason: str,
        report: PeopleUserSyncReport,
    ) -> None:
        if not profile.linked_user_uuid:
            return
        name_before = profile.name
        user_guid = profile.linked_user_uuid
        email = normalize_email(profile.email)
        profile.linked_user_uuid = None
        profile.association_updated_at = datetime.utcnow()
        profile.updated_at = datetime.utcnow()
        self._save_profile(profile)
        report.unlinked += 1
        self._emit_association_log(
            outcome="unlinked",
            reason=reason,
            email=email,
            user_guid=user_guid,
            ppp_uuid=profile.ppp_uuid,
            name_before=name_before,
            name_after=profile.name,
        )

    async def sync(self, *, reason: str) -> PeopleUserSyncReport:
        report = PeopleUserSyncReport(reason=reason, started_at=datetime.utcnow())
        try:
            users = await self._list_users()
        except Exception as exc:  # noqa: BLE001
            logger.exception("people-user sync failed listing users: %s", exc)
            report.errors.append(f"list_users: {exc}")
            report.finished_at = datetime.utcnow()
            self.last_report = report
            return report

        if not isinstance(users, list):
            report.errors.append("list_users returned non-list")
            report.finished_at = datetime.utcnow()
            self.last_report = report
            return report

        eligible = [u for u in users if isinstance(u, dict) and user_is_eligible(u)]
        report.users_seen = len(eligible)
        eligible_by_guid = {
            str(u.get("guid")): u for u in eligible if u.get("guid")
        }
        for user in eligible:
            email = normalize_email(user.get("email"))
            existing = self.find_active_by_email(email)
            if existing is None:
                self.create_profile_for_user(user, reason=reason, report=report)
            else:
                self.apply_user_to_profile(existing, user, reason=reason, report=report)

        # Unlink PPPs whose linked user is gone / ineligible.
        for profile in list(self._get_profiles().values()):
            if profile.status != "active" or not profile.linked_user_uuid:
                continue
            if profile.linked_user_uuid not in eligible_by_guid:
                self.unlink_profile(profile, reason=reason, report=report)

        report.finished_at = datetime.utcnow()
        self.last_report = report
        logger.info(
            "people-user sync reason=%s created=%s updated=%s linked=%s unlinked=%s unchanged=%s users=%s",
            reason,
            report.created,
            report.updated_name,
            report.linked,
            report.unlinked,
            report.unchanged,
            report.users_seen,
        )
        return report

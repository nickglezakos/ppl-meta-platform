import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from src.config import settings
from src.models.app_setting import AppSetting
from src.models.installation_info import InstallationInfo

logger = logging.getLogger(__name__)

ACTIVE_LICENCE_STATES = {"active", "grace"}
IMMEDIATE_SAFEGUARD_STATUSES = {"revoked"}
APPLICATION_KEY_PATTERN = re.compile(r"^lic_[0-9a-f]{32}$")
AUTHORITY_APPLICATION_KEY_SETTING = "authority_application_key"
AUTHORITY_INSTALLATION_UUID_SETTING = "authority_installation_uuid"


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return ensure_utc_datetime(value)
    if not value:
        return None
    try:
        return ensure_utc_datetime(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


class AuthorityService:
    """Client for the Hetzner authority service."""

    def __init__(self):
        self.base_url = settings.AUTHORITY_SERVICE_URL.rstrip("/")
        self.installation_uuid = settings.AUTHORITY_INSTALLATION_UUID.strip()
        self.application_key = settings.AUTHORITY_APPLICATION_KEY.strip()
        self.timeout = settings.AUTHORITY_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(
            settings.AUTHORITY_SERVICE_ENABLED
            and self.base_url
        )

    def is_machine_application_key(self, value: str | None) -> bool:
        return bool(value and APPLICATION_KEY_PATTERN.fullmatch(value.strip().lower()))

    def get_effective_application_key(self, db) -> str:
        configured_key = self.application_key.strip().lower()
        if configured_key:
            if self.is_machine_application_key(configured_key):
                return configured_key
            logger.warning("Ignoring legacy authority application key that does not match lic_<32 hex> format")
            return ""

        db_setting = self._get_app_setting(db, AUTHORITY_APPLICATION_KEY_SETTING)
        if db_setting and db_setting.value:
            stored_key = db_setting.value.strip().lower()
            if self.is_machine_application_key(stored_key):
                return stored_key
            logger.warning("Ignoring stored authority application key that does not match lic_<32 hex> format")
        return ""

    def get_effective_installation_uuid(self, db) -> str:
        configured_uuid = self.installation_uuid.strip()
        if configured_uuid:
            return configured_uuid

        db_setting = self._get_app_setting(db, AUTHORITY_INSTALLATION_UUID_SETTING)
        if db_setting and db_setting.value:
            return db_setting.value.strip()

        info = self._get_or_create_installation_info(db)
        return info.guid

    def derive_runtime_state(self, db) -> dict[str, Any]:
        info = self._get_or_create_installation_info(db)
        now = datetime.now(timezone.utc)
        warning_started_at = ensure_utc_datetime(info.authority_warning_started_at)
        last_successful_check_at = ensure_utc_datetime(info.authority_last_successful_check_at)
        cache_expires_at = None
        warning_deadline = None
        warning_days_remaining = None

        configured = bool(self.is_configured() and self.get_effective_application_key(db))
        if not configured:
            return {
                "state": "not_configured",
                "reason": "authority_not_configured",
                "can_operate": False,
                "warning_deadline": None,
                "warning_days_remaining": None,
                "cache_expires_at": None,
            }

        if info.authority_last_result_reason == "authority_request_failed":
            if last_successful_check_at and info.authority_offline_grace_days is not None:
                grace_deadline = last_successful_check_at + timedelta(days=info.authority_offline_grace_days)
                cache_expires_at = grace_deadline.isoformat()
                if (
                    info.authority_owner_enabled is True
                    and info.authority_licence_status in ACTIVE_LICENCE_STATES
                    and now <= grace_deadline
                ):
                    return {
                        "state": "offline_grace",
                        "reason": "offline_grace_cache",
                        "can_operate": True,
                        "warning_deadline": None,
                        "warning_days_remaining": None,
                        "cache_expires_at": cache_expires_at,
                    }
            return {
                "state": "safeguard",
                "reason": "authority_offline_grace_expired",
                "can_operate": False,
                "warning_deadline": None,
                "warning_days_remaining": None,
                "cache_expires_at": cache_expires_at,
            }

        if info.authority_owner_enabled is True and info.authority_licence_status in ACTIVE_LICENCE_STATES:
            return {
                "state": "valid",
                "reason": info.authority_last_result_reason or "approved_owner",
                "can_operate": True,
                "warning_deadline": None,
                "warning_days_remaining": None,
                "cache_expires_at": None,
            }

        if info.authority_licence_status in IMMEDIATE_SAFEGUARD_STATUSES:
            return {
                "state": "safeguard",
                "reason": "licence_revoked",
                "can_operate": False,
                "warning_deadline": None,
                "warning_days_remaining": None,
                "cache_expires_at": None,
            }

        warning_period_days = info.authority_warning_period_days or 0
        if warning_started_at and warning_period_days > 0:
            warning_deadline_dt = warning_started_at + timedelta(days=warning_period_days)
            warning_deadline = warning_deadline_dt.isoformat()
            if now < warning_deadline_dt:
                warning_days_remaining = max(0, (warning_deadline_dt - now).days)
                return {
                    "state": "warning",
                    "reason": info.authority_licence_status or "licence_warning_active",
                    "can_operate": True,
                    "warning_deadline": warning_deadline,
                    "warning_days_remaining": warning_days_remaining,
                    "cache_expires_at": None,
                }

        return {
            "state": "safeguard",
            "reason": info.authority_licence_status or "licence_inactive",
            "can_operate": False,
            "warning_deadline": warning_deadline,
            "warning_days_remaining": warning_days_remaining,
            "cache_expires_at": None,
        }

    async def refresh_cached_authority_state(self, db) -> dict[str, Any]:
        if not self.is_configured():
            return {"configured": False, "reason": "authority_not_configured"}

        application_key = self.get_effective_application_key(db)
        if not application_key:
            return {"configured": False, "reason": "authority_not_configured"}

        try:
            installation_payload = await self._fetch_installation_payload_by_application_key(application_key)
            installation_uuid = installation_payload.get("installation_uuid") or self.get_effective_installation_uuid(db)
            approved_owner_email = installation_payload.get("approved_owner_email", "")
            owner_payload = None

            if approved_owner_email:
                owner_payload = await self._fetch_owner_payload(approved_owner_email)

            approved = bool(
                approved_owner_email
                and owner_payload is not None
                and owner_payload.get("approved") is True
                and installation_payload.get("application_key") == application_key
                and installation_payload.get("owner_enabled") is True
                and installation_payload.get("licence_status") in ACTIVE_LICENCE_STATES
            )

            self._persist_effective_authority_settings(
                db,
                installation_uuid=installation_uuid,
                application_key=application_key,
            )
            reason = "approved_owner" if approved else "not_approved_owner"
            self._cache_authority_state(db, installation_payload, reason)
            return {
                "configured": True,
                "approved": approved,
                "reason": reason,
                "owner": owner_payload,
                "installation": installation_payload,
            }
        except httpx.HTTPError as exc:
            logger.error("Authority refresh failed: %s", exc)
            failure = {
                "configured": True,
                "approved": False,
                "reason": "authority_request_failed",
                "error": str(exc),
            }
            self._record_failed_check(db, failure["reason"])
            return failure

    async def verify_owner_candidate(self, db, email: str) -> dict[str, Any]:
        if not self.is_configured():
            return {"configured": False, "approved": False, "reason": "authority_not_configured"}

        application_key = self.get_effective_application_key(db)
        if not application_key:
            return {"configured": False, "approved": False, "reason": "authority_not_configured"}

        try:
            owner_payload = await self._fetch_owner_payload(email)
            installation_payload = await self._fetch_installation_payload_by_application_key(application_key)
            installation_uuid = installation_payload.get("installation_uuid") or self.get_effective_installation_uuid(db)

            approved = (
                owner_payload.get("approved") is True
                and installation_payload.get("application_key") == application_key
                and installation_payload.get("approved_owner_email", "").lower() == email.lower()
                and installation_payload.get("owner_enabled") is True
                and installation_payload.get("licence_status") in ACTIVE_LICENCE_STATES
            )

            self._persist_effective_authority_settings(
                db,
                installation_uuid=installation_uuid,
                application_key=application_key,
            )
            self._cache_authority_state(
                db,
                installation_payload,
                "approved_owner" if approved else "not_approved_owner",
            )

            return {
                "configured": True,
                "approved": approved,
                "reason": "approved_owner" if approved else "not_approved_owner",
                "owner": owner_payload,
                "installation": installation_payload,
            }
        except httpx.HTTPError as exc:
            logger.error("Authority verification failed for %s: %s", email, exc)
            failure = {
                "configured": True,
                "approved": False,
                "reason": "authority_request_failed",
                "error": str(exc),
            }
            self._record_failed_check(db, failure["reason"])
            return self._resolve_cached_owner_candidate(db, email, failure)

    async def activate_owner_candidate(
        self,
        db,
        email: str,
        *,
        application_key_override: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            return {"configured": False, "approved": False, "reason": "authority_not_configured"}

        application_key = (application_key_override or "").strip().lower() or self.get_effective_application_key(db)
        if not application_key:
            return {"configured": False, "approved": False, "reason": "authority_not_configured"}
        if not self.is_machine_application_key(application_key):
            return {"configured": True, "approved": False, "reason": "invalid_application_key_format"}

        installation_uuid = self.get_effective_installation_uuid(db)
        payload = {
            "application_key": application_key,
            "installation_uuid": installation_uuid,
            "owner_email": email,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                activation_response = await client.post(
                    f"{self.base_url}/api/v1/installations/activate",
                    json=payload,
                )

            if activation_response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"installation_activation_failed:{activation_response.status_code}",
                    request=activation_response.request,
                    response=activation_response,
                )

            activation_payload = activation_response.json()
            approved = activation_payload.get("approved") is True
            self._persist_effective_authority_settings(
                db,
                installation_uuid=installation_uuid,
                application_key=application_key,
            )
            if approved:
                self._cache_authority_state(db, activation_payload, activation_payload.get("reason", "approved_owner"))
            else:
                self._record_failed_check(db, activation_payload.get("reason", "activation_rejected"))

            return {
                "configured": True,
                "approved": approved,
                "reason": activation_payload.get("reason", "unknown_reason"),
                "installation": activation_payload,
            }
        except httpx.HTTPError as exc:
            logger.error("Authority activation failed for %s: %s", email, exc)
            failure = {
                "configured": True,
                "approved": False,
                "reason": "authority_request_failed",
                "error": str(exc),
            }
            self._record_failed_check(db, failure["reason"])
            return failure

    async def _fetch_installation_payload(self, installation_uuid: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            installation_response = await client.get(
                f"{self.base_url}/api/v1/installations/{installation_uuid}"
            )

        if installation_response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"installation_lookup_failed:{installation_response.status_code}",
                request=installation_response.request,
                response=installation_response,
            )

        return installation_response.json()

    async def _fetch_installation_payload_by_application_key(self, application_key: str) -> dict[str, Any]:
        encoded_key = quote(application_key, safe="")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            installation_response = await client.get(
                f"{self.base_url}/api/v1/application-keys/{encoded_key}"
            )

        if installation_response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"application_key_lookup_failed:{installation_response.status_code}",
                request=installation_response.request,
                response=installation_response,
            )

        return installation_response.json()

    async def _fetch_owner_payload(self, email: str) -> dict[str, Any]:
        encoded_email = quote(email, safe="@")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            owner_response = await client.get(f"{self.base_url}/api/v1/owners/{encoded_email}")

        if owner_response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"owner_lookup_failed:{owner_response.status_code}",
                request=owner_response.request,
                response=owner_response,
            )

        return owner_response.json()

    def _get_or_create_installation_info(self, db) -> InstallationInfo:
        info = db.query(InstallationInfo).first()
        if info is None:
            info = InstallationInfo(guid=str(uuid.uuid4()))
            db.add(info)
            db.commit()
            db.refresh(info)
        return info

    def _get_app_setting(self, db, key: str) -> AppSetting | None:
        return db.query(AppSetting).filter(AppSetting.key == key).first()

    def _upsert_app_setting(self, db, key: str, value: str) -> None:
        db_setting = self._get_app_setting(db, key)
        if db_setting is None:
            db_setting = AppSetting(key=key, value=value)
            db.add(db_setting)
            return

        if db_setting.value != value:
            db_setting.value = value

    def _persist_effective_authority_settings(
        self,
        db,
        *,
        installation_uuid: str,
        application_key: str,
    ) -> None:
        if installation_uuid:
            self._upsert_app_setting(db, AUTHORITY_INSTALLATION_UUID_SETTING, installation_uuid)
        if application_key:
            self._upsert_app_setting(db, AUTHORITY_APPLICATION_KEY_SETTING, application_key)

    def _cache_authority_state(self, db, installation_payload: dict[str, Any], reason: str) -> None:
        info = self._get_or_create_installation_info(db)
        now = datetime.now(timezone.utc)
        info.authority_application_key = installation_payload.get("application_key")
        info.authority_installation_uuid = installation_payload.get("installation_uuid")
        info.authority_licence_name = installation_payload.get("licence_name")
        info.authority_tenant_name = installation_payload.get("tenant_name")
        info.authority_approved_owner_email = installation_payload.get("approved_owner_email")
        info.authority_licence_status = installation_payload.get("licence_status")
        info.authority_owner_enabled = bool(installation_payload.get("owner_enabled"))
        info.authority_warning_period_days = installation_payload.get("warning_period_days")
        info.authority_warning_started_at = _parse_datetime(installation_payload.get("warning_started_at"))
        info.authority_offline_grace_days = installation_payload.get("offline_grace_days")
        info.authority_last_checked_at = now
        info.authority_last_successful_check_at = now
        info.authority_last_result_reason = reason
        db.commit()

    def _record_failed_check(self, db, reason: str) -> None:
        info = self._get_or_create_installation_info(db)
        info.authority_last_checked_at = datetime.now(timezone.utc)
        info.authority_last_result_reason = reason
        db.commit()

    def _resolve_cached_owner_candidate(self, db, email: str, failure_result: dict[str, Any]) -> dict[str, Any]:
        info = self._get_or_create_installation_info(db)
        last_successful_check_at = ensure_utc_datetime(info.authority_last_successful_check_at)
        if not last_successful_check_at:
            return failure_result

        grace_days = info.authority_offline_grace_days or 0
        grace_deadline = last_successful_check_at + timedelta(days=grace_days)
        now = datetime.now(timezone.utc)

        if (
            info.authority_approved_owner_email
            and info.authority_approved_owner_email.lower() == email.lower()
            and info.authority_owner_enabled is True
            and info.authority_licence_status in ACTIVE_LICENCE_STATES
            and now <= grace_deadline
        ):
            return {
                "configured": True,
                "approved": True,
                "reason": "offline_grace_cache",
                "cached": True,
                "cache_expires_at": grace_deadline.isoformat(),
            }

        return failure_result


authority_service = AuthorityService()
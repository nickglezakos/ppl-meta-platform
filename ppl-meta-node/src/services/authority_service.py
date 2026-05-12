import logging
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
AUTHORITY_APPLICATION_KEY_SETTING = "authority_application_key"
AUTHORITY_INSTALLATION_UUID_SETTING = "authority_installation_uuid"


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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

    def get_effective_application_key(self, db) -> str:
        configured_key = self.application_key.strip()
        if configured_key:
            return configured_key

        db_setting = self._get_app_setting(db, AUTHORITY_APPLICATION_KEY_SETTING)
        if db_setting and db_setting.value:
            return db_setting.value.strip()
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

    async def refresh_cached_authority_state(self, db) -> dict[str, Any]:
        if not self.is_configured():
            return {"configured": False, "reason": "authority_not_configured"}

        application_key = self.get_effective_application_key(db)
        if not application_key:
            return {"configured": False, "reason": "authority_not_configured"}

        try:
            installation_uuid = self.get_effective_installation_uuid(db)
            installation_payload = await self._fetch_installation_payload(installation_uuid)
            approved_owner_email = installation_payload.get("approved_owner_email", "")
            owner_payload = None

            if approved_owner_email:
                owner_payload = await self._fetch_owner_payload(approved_owner_email)

            approved = bool(
                approved_owner_email
                and owner_payload is not None
                and owner_payload.get("approved") is True
                and owner_payload.get("installation_uuid") == installation_uuid
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
            installation_uuid = self.get_effective_installation_uuid(db)
            owner_payload = await self._fetch_owner_payload(email)
            installation_payload = await self._fetch_installation_payload(installation_uuid)

            approved = (
                owner_payload.get("approved") is True
                and owner_payload.get("installation_uuid") == installation_uuid
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

    async def activate_owner_candidate(self, db, email: str) -> dict[str, Any]:
        if not self.is_configured():
            return {"configured": False, "approved": False, "reason": "authority_not_configured"}

        application_key = self.get_effective_application_key(db)
        if not application_key:
            return {"configured": False, "approved": False, "reason": "authority_not_configured"}

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
        info.authority_approved_owner_email = installation_payload.get("approved_owner_email")
        info.authority_licence_status = installation_payload.get("licence_status")
        info.authority_owner_enabled = bool(installation_payload.get("owner_enabled"))
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
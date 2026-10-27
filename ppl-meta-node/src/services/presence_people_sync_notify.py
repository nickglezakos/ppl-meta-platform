"""Best-effort notify Presence to reconcile people↔user associations."""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


def _presence_base_url() -> str:
    return (
        os.getenv("PRESENCE_SERVICE_URL")
        or getattr(settings, "PRESENCE_SERVICE_URL", None)
        or "http://ppl-meta-presence:8011"
    ).rstrip("/")


def _service_headers() -> Optional[dict[str, str]]:
    secret = settings.SERVICE_SECRET
    if not secret:
        logger.debug("Skipping presence people notify: SERVICE_SECRET unset")
        return None
    return {"Authorization": f"Bearer {secret}"}


async def notify_presence_people_user_sync(reason: str = "user_update") -> None:
    """Fire-and-forget Presence full people↔user sync. Never raises to callers."""
    headers = _service_headers()
    if not headers:
        return
    url = f"{_presence_base_url()}/api/v1/presence/internal/people-user-sync"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            response = await client.post(
                url,
                headers=headers,
                params={"reason": reason},
            )
            if response.status_code >= 400:
                logger.warning(
                    "Presence people sync notify failed status=%s body=%s",
                    response.status_code,
                    response.text[:200],
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Presence people sync notify skipped: %s", exc)


async def notify_presence_people_from_user(
    user: Mapping[str, Any],
    *,
    reason: str = "user_create",
) -> None:
    """Create/link one Presence people profile for a registered user.

    Falls back to a full sync if the targeted endpoint is unavailable.
    Never raises to callers.
    """
    headers = _service_headers()
    if not headers:
        return

    email = str(user.get("email") or "").strip()
    if not email:
        logger.warning("Presence people-from-user skipped: missing email")
        return

    payload = {
        "email": email,
        "guid": str(user.get("guid") or "") or None,
        "given_name": user.get("given_name"),
        "family_name": user.get("family_name"),
        "name": user.get("name"),
        "username": user.get("username"),
        "is_active": bool(user.get("is_active", True)),
        "blocked": bool(user.get("blocked", False)),
        "reason": reason,
    }

    url = f"{_presence_base_url()}/api/v1/presence/internal/people-from-user"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code < 400:
                logger.info(
                    "Presence people-from-user ok reason=%s email=%s",
                    reason,
                    email,
                )
                return
            logger.warning(
                "Presence people-from-user failed status=%s body=%s — falling back to sync",
                response.status_code,
                response.text[:200],
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Presence people-from-user skipped: %s — falling back to sync",
            exc,
        )

    await notify_presence_people_user_sync(reason=reason)

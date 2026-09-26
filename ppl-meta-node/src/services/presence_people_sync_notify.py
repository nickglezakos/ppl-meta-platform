"""Best-effort notify Presence to reconcile people↔user associations."""

from __future__ import annotations

import logging
import os

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


def _presence_base_url() -> str:
    return (
        os.getenv("PRESENCE_SERVICE_URL")
        or getattr(settings, "PRESENCE_SERVICE_URL", None)
        or "http://ppl-meta-presence:8011"
    ).rstrip("/")


async def notify_presence_people_user_sync(reason: str = "user_update") -> None:
    """Fire-and-forget Presence internal sync. Never raises to callers."""
    secret = settings.SERVICE_SECRET
    if not secret:
        logger.debug("Skipping presence people sync notify: SERVICE_SECRET unset")
        return
    url = f"{_presence_base_url()}/api/v1/presence/internal/people-user-sync"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {secret}"},
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

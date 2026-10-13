"""
Delayed second-playlist switch for digital_signage automation actions.

After the first playlist START succeeds, optionally schedule a second START
for ``second_playlist_id`` after a duration (default 10 seconds).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

logger = logging.getLogger(__name__)

DEFAULT_SECOND_PLAYLIST_DURATION_SECONDS = 10

# Process-local pending delayed switches, keyed by device id string.
_pending_switches: Dict[str, asyncio.Task] = {}


def resolve_second_playlist_duration_seconds(raw: Any) -> int:
    """Return positive duration seconds; default 10 when missing/invalid."""
    if raw is None or raw == "":
        return DEFAULT_SECOND_PLAYLIST_DURATION_SECONDS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_SECOND_PLAYLIST_DURATION_SECONDS
    if value <= 0:
        return DEFAULT_SECOND_PLAYLIST_DURATION_SECONDS
    return value


def cancel_pending_second_playlist_switches(device_ids: List[str]) -> None:
    """Cancel any pending delayed second-playlist switches for the given devices."""
    for device_id in device_ids:
        key = str(device_id)
        task = _pending_switches.pop(key, None)
        if task is not None and not task.done():
            task.cancel()
            logger.info(
                "Cancelled pending second-playlist switch for device %s", key
            )


async def _run_delayed_playlist_start(
    device_ids: List[str],
    playlist_id: str,
    delay_seconds: int,
    task_keys: Set[str],
) -> None:
    """Sleep then START playlist on devices using a fresh DB session."""
    try:
        await asyncio.sleep(delay_seconds)

        from src.database import SessionLocal
        from src.schemas.signage import (
            PlaybackCommand,
            PlaybackControlRequest,
            PlaybackParameters,
        )
        from src.services.signage_service import SignagePlaybackService

        db = SessionLocal()
        try:
            playback_service = SignagePlaybackService(db)
            control_request = PlaybackControlRequest(
                device_ids=[UUID(str(d)) for d in device_ids],
                command=PlaybackCommand.START,
                video_list_id=UUID(str(playlist_id)),
                parameters=PlaybackParameters(),
            )
            result = await playback_service.control_playback(control_request)
            logger.info(
                "Delayed second-playlist START sent (playlist=%s, devices=%s): %s",
                playlist_id,
                device_ids,
                result,
            )
        finally:
            db.close()
    except asyncio.CancelledError:
        logger.info(
            "Delayed second-playlist switch cancelled (playlist=%s, devices=%s)",
            playlist_id,
            device_ids,
        )
        raise
    except Exception:
        logger.exception(
            "Delayed second-playlist START failed (playlist=%s, devices=%s)",
            playlist_id,
            device_ids,
        )
    finally:
        for key in task_keys:
            existing = _pending_switches.get(key)
            if existing is not None and existing.done():
                _pending_switches.pop(key, None)


def schedule_second_playlist_switch(
    device_ids: List[str],
    second_playlist_id: Optional[str],
    duration_seconds: Any = None,
) -> Optional[asyncio.Task]:
    """
    Schedule a delayed START for ``second_playlist_id`` on ``device_ids``.

    Cancels any existing pending delayed switch for the same devices.
    Returns the created task, or None if no second playlist was requested.
    """
    if not second_playlist_id or not str(second_playlist_id).strip():
        return None
    if not device_ids:
        return None

    normalized_ids = [str(d) for d in device_ids if d]
    if not normalized_ids:
        return None

    delay = resolve_second_playlist_duration_seconds(duration_seconds)
    playlist_id = str(second_playlist_id).strip()

    cancel_pending_second_playlist_switches(normalized_ids)

    task_keys = set(normalized_ids)
    task = asyncio.create_task(
        _run_delayed_playlist_start(
            device_ids=normalized_ids,
            playlist_id=playlist_id,
            delay_seconds=delay,
            task_keys=task_keys,
        ),
        name=f"signage-second-playlist-{playlist_id}",
    )
    for key in task_keys:
        _pending_switches[key] = task

    logger.info(
        "Scheduled second-playlist switch in %ss (playlist=%s, devices=%s)",
        delay,
        playlist_id,
        normalized_ids,
    )
    return task

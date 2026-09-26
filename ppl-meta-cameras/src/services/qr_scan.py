"""Short-lived QR decode from a connected camera frame buffer."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import cv2

from src.services.camera_service_queue import get_camera_service

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 0.15


def clamp_timeout_seconds(timeout_seconds: Optional[float]) -> float:
    if timeout_seconds is None:
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        value = float(timeout_seconds)
    except (TypeError, ValueError):
        return float(DEFAULT_TIMEOUT_SECONDS)
    if value <= 0:
        return float(DEFAULT_TIMEOUT_SECONDS)
    return min(value, float(MAX_TIMEOUT_SECONDS))


async def scan_qr_from_camera(
    device_id: str,
    *,
    timeout_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Ensure the camera worker is connected, then poll latest frames for a QR code.

    Does not disconnect the camera when finished — the shared worker stays up for
    streaming / instant detection / triggers.
    """
    timeout = clamp_timeout_seconds(timeout_seconds)
    queue_service = get_camera_service()

    connected = await queue_service.connect_camera(device_id)
    if not connected:
        logger.warning("QR scan failed to connect camera %s", device_id)
        return {
            "found": False,
            "device_id": device_id,
            "reason": "connect_failed",
            "timeout_seconds": timeout,
        }

    detector = cv2.QRCodeDetector()
    deadline = time.monotonic() + timeout
    last_error: Optional[str] = None

    while time.monotonic() < deadline:
        try:
            frame = await queue_service.get_latest_frame(device_id)
        except Exception as exc:  # noqa: BLE001 — keep scanning until timeout
            last_error = str(exc)
            logger.debug("QR scan frame read error for %s: %s", device_id, exc)
            frame = None

        if frame is not None:
            try:
                text, _points, _straight = detector.detectAndDecode(frame)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.debug("QR decode error for %s: %s", device_id, exc)
                text = ""
            if text:
                logger.info("QR scan found payload on camera %s (%d chars)", device_id, len(text))
                return {
                    "found": True,
                    "text": text,
                    "device_id": device_id,
                    "timeout_seconds": timeout,
                }

        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    result: Dict[str, Any] = {
        "found": False,
        "device_id": device_id,
        "reason": "timeout",
        "timeout_seconds": timeout,
    }
    if last_error:
        result["last_error"] = last_error
    return result

"""
Velocity Trigger Worker

Evaluates instant-detection velocity events from Redis pub/sub against
configured gait-band floors (walking / light_running / running / fast_running)
for either crowd mean or single-person max speed.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger

logger = logging.getLogger(__name__)

# Keep in sync with ppl-meta-cameras/src/services/instant_velocity.py
GAIT_THRESHOLD_MPS = {
    "walking": 1.25,
    "light_running": 2.2,
    "running": 3.3,
    "fast_running": 5.0,
}

VALID_SCOPES = ("crowd", "single")
VALID_BANDS = tuple(GAIT_THRESHOLD_MPS.keys())


def _parse_json_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x]
        except (json.JSONDecodeError, TypeError, ValueError):
            if raw.startswith("{") and raw.endswith("}"):
                items = raw[1:-1].split(",")
                return [item.strip().strip('"') for item in items if item.strip()]
    return []


class VelocityTriggerWorker:
    """Thin multicamera evaluator for velocity triggers (no rolling window)."""

    def __init__(self) -> None:
        # trigger_uuid -> set of camera device ids
        self._cameras: Dict[str, List[str]] = {}

    def get_camera_device_ids(self, trigger: Trigger) -> List[str]:
        cached = self._cameras.get(str(trigger.uuid))
        if cached is not None:
            return cached
        cameras = _parse_json_list(getattr(trigger, "camera_device_ids", None))
        legacy = getattr(trigger, "camera_device_id", None)
        if legacy and legacy not in ("velocity", "body_posture", "vprofile_match"):
            if legacy not in cameras:
                cameras.append(str(legacy))
        return cameras

    async def activate_trigger(self, trigger: Trigger) -> None:
        cameras = _parse_json_list(getattr(trigger, "camera_device_ids", None))
        self._cameras[str(trigger.uuid)] = cameras
        logger.info(
            "Activated velocity trigger %s — cameras=%s scope=%s band=%s",
            trigger.uuid,
            cameras,
            getattr(trigger, "velocity_scope", None),
            getattr(trigger, "velocity_band", None),
        )

    async def deactivate_trigger(self, trigger_uuid: str) -> None:
        self._cameras.pop(str(trigger_uuid), None)
        logger.info("Deactivated velocity trigger %s", trigger_uuid)

    async def ensure_trigger_loaded(self, trigger: Trigger) -> bool:
        cameras = self.get_camera_device_ids(trigger)
        if not cameras:
            return False
        self._cameras[str(trigger.uuid)] = cameras
        return True

    async def load_all_active_triggers(self) -> int:
        return self.restore_active_triggers()

    def restore_active_triggers(self, db: Optional[Session] = None) -> int:
        owns_session = db is None
        session = db or SessionLocal()
        try:
            triggers = (
                session.query(Trigger)
                .filter(
                    Trigger.is_active == True,  # noqa: E712
                    Trigger.trigger_mode == "velocity",
                )
                .all()
            )
            for trigger in triggers:
                try:
                    self.activate_trigger(trigger)
                except Exception as exc:
                    logger.warning(
                        "Failed to restore velocity trigger %s: %s",
                        trigger.uuid,
                        exc,
                    )
            logger.info("Restored %d active velocity trigger(s)", len(triggers))
            return len(triggers)
        finally:
            if owns_session:
                session.close()

    async def evaluate(
        self, trigger: Trigger, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        scope = str(getattr(trigger, "velocity_scope", None) or "crowd").lower()
        band = str(getattr(trigger, "velocity_band", None) or "walking").lower()
        if scope not in VALID_SCOPES:
            return False, f"Invalid velocity_scope={scope}", None
        if band not in VALID_BANDS:
            return False, f"Invalid velocity_band={band}", None

        floor = float(GAIT_THRESHOLD_MPS[band])
        velocity = data.get("velocity") or {}
        if not isinstance(velocity, dict):
            velocity = {}

        crowd_mps = velocity.get("crowd_mps")
        max_mps = velocity.get("max_mps")
        valid_count = int(velocity.get("valid_count") or 0)
        people = velocity.get("people") or []
        camera_id = data.get("camera_id")

        match_info: Dict[str, Any] = {
            "scope": scope,
            "band": band,
            "band_floor_mps": floor,
            "camera_id": camera_id,
            "crowd_mps": crowd_mps,
            "max_mps": max_mps,
            "valid_count": valid_count,
        }

        if scope == "crowd":
            if crowd_mps is None or valid_count < 1:
                return (
                    False,
                    "velocity crowd: no valid speed samples in cycle",
                    match_info,
                )
            if float(crowd_mps) >= floor:
                reason = (
                    f"velocity crowd MET: mean {float(crowd_mps):.2f} m/s "
                    f">= {band} ({floor} m/s) on {camera_id}"
                )
                match_info["measured_mps"] = float(crowd_mps)
                return True, reason, match_info
            return (
                False,
                f"velocity crowd not met: mean {float(crowd_mps):.2f} < {floor}",
                match_info,
            )

        # single-person scope
        if max_mps is None or valid_count < 1:
            return (
                False,
                "velocity single: no valid speed samples in cycle",
                match_info,
            )

        offenders = [
            p
            for p in people
            if isinstance(p, dict)
            and p.get("speed_mps") is not None
            and float(p["speed_mps"]) >= floor
        ]
        if float(max_mps) >= floor:
            reason = (
                f"velocity single MET: max {float(max_mps):.2f} m/s "
                f">= {band} ({floor} m/s) on {camera_id}"
            )
            match_info["measured_mps"] = float(max_mps)
            match_info["offending_people"] = offenders
            return True, reason, match_info

        return (
            False,
            f"velocity single not met: max {float(max_mps):.2f} < {floor}",
            match_info,
        )


_velocity_worker: Optional[VelocityTriggerWorker] = None


def get_velocity_trigger_worker() -> VelocityTriggerWorker:
    global _velocity_worker
    if _velocity_worker is None:
        _velocity_worker = VelocityTriggerWorker()
    return _velocity_worker

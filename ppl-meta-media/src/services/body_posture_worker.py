"""
Body Posture Trigger Worker

VProfile-style multicamera worker for instant body posture triggers.

Maintains an in-memory rolling window of consecutive body scans per camera,
associates bodies across cycles with bbox IoU, and majority-votes posture
(horizontal / upright / either) per track.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger

logger = logging.getLogger(__name__)

BODY_POSTURE_HISTORY_KEY_PREFIX = "instant_body_posture:"
DEFAULT_WINDOW_SIZE = 4
DEFAULT_MIN_MATCHES = 3
DEFAULT_MIN_CONFIDENCE = 0.5
DEFAULT_IOU_THRESHOLD = 0.3


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


def _bbox_iou(a: Any, b: Any) -> float:
    if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)):
        return 0.0
    if len(a) < 4 or len(b) < 4:
        return 0.0
    try:
        ax1, ay1, ax2, ay2 = [float(v) for v in a[:4]]
        bx1, by1, bx2, by2 = [float(v) for v in b[:4]]
    except (TypeError, ValueError):
        return 0.0
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def _normalize_posture(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if value in ("horizontal", "upright", "uncertain"):
        return value
    return None


def _matches_target(posture: Optional[str], target: str) -> bool:
    if not posture or posture == "uncertain":
        return False
    if target == "either":
        return posture in ("horizontal", "upright")
    return posture == target


@dataclass
class ScanObservation:
    timestamp: str
    body_person_id: Optional[str]
    bbox: Optional[List[float]]
    posture: Optional[str]
    posture_confidence: float


@dataclass
class BodyTrack:
    track_id: str
    observations: List[ScanObservation] = field(default_factory=list)
    last_bbox: Optional[List[float]] = None

    def append(self, obs: ScanObservation, window_size: int) -> None:
        self.observations.append(obs)
        if obs.bbox:
            self.last_bbox = obs.bbox
        if len(self.observations) > window_size:
            self.observations = self.observations[-window_size:]


@dataclass
class CameraPostureState:
    camera_id: str
    cycles: List[Dict[str, Any]] = field(default_factory=list)
    tracks: Dict[str, BodyTrack] = field(default_factory=dict)


class BodyPostureWorker:
    """In-memory multicamera evaluator for body_posture triggers."""

    def __init__(self) -> None:
        self._active_trigger_ids: set[str] = set()
        self._camera_state: Dict[str, CameraPostureState] = {}
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        import redis

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return self._redis

    @staticmethod
    def get_camera_device_ids(trigger: Trigger) -> List[str]:
        cameras = _parse_json_list(getattr(trigger, "camera_device_ids", None))
        if cameras:
            return cameras
        legacy = getattr(trigger, "camera_device_id", None)
        if legacy and legacy not in ("body_posture", "vprofile_match"):
            return [str(legacy)]
        return []

    @staticmethod
    def _trigger_params(trigger: Trigger) -> Dict[str, Any]:
        window = int(getattr(trigger, "body_posture_window_size", None) or DEFAULT_WINDOW_SIZE)
        window = max(3, min(4, window))
        min_matches = int(
            getattr(trigger, "body_posture_min_matches", None) or DEFAULT_MIN_MATCHES
        )
        min_matches = max(1, min(window, min_matches))
        min_conf = float(
            getattr(trigger, "body_posture_min_confidence", None) or DEFAULT_MIN_CONFIDENCE
        )
        iou = float(
            getattr(trigger, "body_posture_iou_threshold", None) or DEFAULT_IOU_THRESHOLD
        )
        target = (
            str(getattr(trigger, "body_posture_target", None) or "horizontal")
            .strip()
            .lower()
        )
        if target not in ("horizontal", "upright", "either"):
            target = "horizontal"
        return {
            "target": target,
            "window_size": window,
            "min_matches": min_matches,
            "min_confidence": min_conf,
            "iou_threshold": iou,
        }

    def _load_history_from_redis(self, camera_id: str) -> List[Dict[str, Any]]:
        try:
            client = self._get_redis()
            key = f"{BODY_POSTURE_HISTORY_KEY_PREFIX}{camera_id}"
            raw_items = client.lrange(key, 0, -1) or []
            cycles: List[Dict[str, Any]] = []
            for raw in raw_items:
                try:
                    item = json.loads(raw)
                    if isinstance(item, dict):
                        cycles.append(item)
                except (json.JSONDecodeError, TypeError):
                    continue
            return cycles
        except Exception as exc:
            logger.warning(
                "Failed to load body posture history for %s: %s", camera_id, exc
            )
            return []

    def _ensure_camera_state(self, camera_id: str) -> CameraPostureState:
        state = self._camera_state.get(camera_id)
        if state is None:
            state = CameraPostureState(camera_id=camera_id)
            history = self._load_history_from_redis(camera_id)
            for cycle in history:
                self._ingest_cycle(state, cycle, window_size=DEFAULT_WINDOW_SIZE)
            self._camera_state[camera_id] = state
        return state

    def _ingest_cycle(
        self,
        state: CameraPostureState,
        cycle: Dict[str, Any],
        *,
        window_size: int,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    ) -> None:
        timestamp = str(cycle.get("timestamp") or datetime.now(timezone.utc).isoformat())
        # Deduplicate identical timestamps already present
        if state.cycles and state.cycles[-1].get("timestamp") == timestamp:
            return

        bodies = cycle.get("body_persons") or []
        if not isinstance(bodies, list):
            bodies = []

        observations: List[ScanObservation] = []
        for person in bodies:
            if not isinstance(person, dict):
                continue
            posture = _normalize_posture(person.get("posture"))
            try:
                conf = float(person.get("posture_confidence") or 0.0)
            except (TypeError, ValueError):
                conf = 0.0
            bbox = person.get("average_bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                try:
                    bbox = [float(v) for v in bbox[:4]]
                except (TypeError, ValueError):
                    bbox = None
            else:
                bbox = None
            observations.append(
                ScanObservation(
                    timestamp=timestamp,
                    body_person_id=(
                        str(person.get("body_person_id"))
                        if person.get("body_person_id")
                        else None
                    ),
                    bbox=bbox,
                    posture=posture,
                    posture_confidence=conf,
                )
            )

        # Greedy IoU assignment against current tracks' last bbox
        active_tracks = list(state.tracks.values())
        used_track_ids: set[str] = set()
        for obs in observations:
            best_track: Optional[BodyTrack] = None
            best_iou = 0.0
            if obs.bbox:
                for track in active_tracks:
                    if track.track_id in used_track_ids or not track.last_bbox:
                        continue
                    iou = _bbox_iou(obs.bbox, track.last_bbox)
                    if iou >= iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_track = track
            if best_track is None:
                best_track = BodyTrack(track_id=str(uuid4()))
                state.tracks[best_track.track_id] = best_track
            used_track_ids.add(best_track.track_id)
            best_track.append(obs, window_size)

        # Drop stale tracks that did not appear this cycle and have empty windows
        stale = [
            tid
            for tid, track in state.tracks.items()
            if tid not in used_track_ids and not track.observations
        ]
        for tid in stale:
            state.tracks.pop(tid, None)

        state.cycles.append({"timestamp": timestamp, "body_persons": bodies})
        if len(state.cycles) > window_size:
            state.cycles = state.cycles[-window_size:]

    async def activate_trigger(self, trigger: Trigger) -> None:
        trigger_id = str(trigger.uuid)
        self._active_trigger_ids.add(trigger_id)
        cameras = self.get_camera_device_ids(trigger)
        params = self._trigger_params(trigger)
        for camera_id in cameras:
            state = self._ensure_camera_state(camera_id)
            # Re-hydrate from Redis so memory matches latest history
            history = self._load_history_from_redis(camera_id)
            state.cycles = []
            state.tracks = {}
            for cycle in history:
                self._ingest_cycle(
                    state,
                    cycle,
                    window_size=params["window_size"],
                    iou_threshold=params["iou_threshold"],
                )
        logger.info(
            "Activated body_posture trigger %s — cameras=%s window=%s min_matches=%s target=%s",
            trigger_id,
            cameras,
            params["window_size"],
            params["min_matches"],
            params["target"],
        )

    async def deactivate_trigger(self, trigger_uuid: str) -> None:
        self._active_trigger_ids.discard(str(trigger_uuid))
        logger.info("Deactivated body_posture trigger %s", trigger_uuid)

    async def ensure_trigger_loaded(self, trigger: Trigger) -> bool:
        trigger_id = str(trigger.uuid)
        cameras = self.get_camera_device_ids(trigger)
        if not cameras:
            return False
        if trigger_id not in self._active_trigger_ids:
            await self.activate_trigger(trigger)
        else:
            for camera_id in cameras:
                self._ensure_camera_state(camera_id)
        return True

    async def load_all_active_triggers(self) -> int:
        db: Session = SessionLocal()
        try:
            triggers = (
                db.query(Trigger)
                .filter(
                    Trigger.is_active == True,  # noqa: E712
                    Trigger.trigger_mode == "body_posture",
                )
                .all()
            )
            for trigger in triggers:
                try:
                    await self.activate_trigger(trigger)
                except Exception as exc:
                    logger.error(
                        "Failed to restore body_posture trigger %s: %s",
                        trigger.uuid,
                        exc,
                    )
            logger.info("Restored %d active body_posture trigger(s)", len(triggers))
            return len(triggers)
        finally:
            db.close()

    async def evaluate(
        self,
        trigger: Trigger,
        event_data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        camera_id = event_data.get("camera_id")
        if not camera_id:
            return False, "Missing camera_id on event", None

        allowed = self.get_camera_device_ids(trigger)
        if allowed and camera_id not in allowed:
            return False, f"Camera {camera_id} not in allowlist", None

        params = self._trigger_params(trigger)
        state = self._ensure_camera_state(camera_id)

        body_persons = event_data.get("body_persons")
        if not body_persons:
            # Fallback: reload Redis history and use latest cycle
            history = self._load_history_from_redis(camera_id)
            if history:
                latest = history[-1]
                body_persons = latest.get("body_persons") or []
                cycle = {
                    "timestamp": latest.get("timestamp")
                    or event_data.get("timestamp")
                    or datetime.now(timezone.utc).isoformat(),
                    "body_persons": body_persons,
                }
            else:
                return False, "No body_persons on event or Redis history", None
        else:
            cycle = {
                "timestamp": event_data.get("timestamp")
                or datetime.now(timezone.utc).isoformat(),
                "body_persons": body_persons,
            }

        self._ingest_cycle(
            state,
            cycle,
            window_size=params["window_size"],
            iou_threshold=params["iou_threshold"],
        )

        target = params["target"]
        window_size = params["window_size"]
        min_matches = params["min_matches"]
        min_conf = params["min_confidence"]

        best_info: Optional[Dict[str, Any]] = None
        for track in state.tracks.values():
            recent = track.observations[-window_size:]
            if len(recent) < window_size:
                continue
            qualifying: List[ScanObservation] = []
            matching: List[ScanObservation] = []
            for obs in recent:
                if not obs.posture or obs.posture == "uncertain":
                    continue
                if obs.posture_confidence < min_conf:
                    continue
                qualifying.append(obs)
                if _matches_target(obs.posture, target):
                    matching.append(obs)
            # Require a full window of recent scans present; vote among confident labels.
            match_count = len(matching)
            if match_count >= min_matches and len(qualifying) >= min_matches:
                postures = [obs.posture for obs in recent]
                avg_conf = sum(obs.posture_confidence for obs in matching) / max(
                    match_count, 1
                )
                best_info = {
                    "source_camera_id": camera_id,
                    "track_id": track.track_id,
                    "target": target,
                    "match_count": match_count,
                    "window_size": window_size,
                    "min_matches": min_matches,
                    "postures": postures,
                    "average_match_confidence": round(avg_conf, 4),
                    "last_bbox": track.last_bbox,
                    "body_person_ids": [
                        obs.body_person_id
                        for obs in qualifying
                        if obs.body_person_id
                    ],
                }
                reason = (
                    f"body_posture MET: track {track.track_id[:8]} "
                    f"{match_count}/{window_size} scans match '{target}' "
                    f"(avg_conf={avg_conf:.2f})"
                )
                return True, reason, best_info

        return (
            False,
            f"body_posture not met for {camera_id} "
            f"(need {min_matches}/{window_size} '{target}' with conf>={min_conf})",
            best_info,
        )


_worker: Optional[BodyPostureWorker] = None


def get_body_posture_worker() -> BodyPostureWorker:
    global _worker
    if _worker is None:
        _worker = BodyPostureWorker()
    return _worker

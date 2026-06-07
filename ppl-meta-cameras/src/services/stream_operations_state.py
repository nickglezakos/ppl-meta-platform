"""
Stream operations state service.

Tracks camera stream liveness, active viewers, and lifecycle events with Redis as
source-of-truth when available and an in-memory fallback when Redis is not
available. This allows phased rollout without blocking live streaming.
"""

from __future__ import annotations

import logging
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - optional dependency fallback
    redis = None

from src.config import get_config

logger = logging.getLogger(__name__)


class StreamOperationsStateService:
    """Manages stream lifecycle state and lightweight operations metadata."""

    def __init__(self) -> None:
        self._config = get_config()
        self._enabled = self._config.STREAM_STATE_REDIS_ENABLED
        self._namespace = self._config.STREAM_STATE_KEY_NAMESPACE
        self._events_stream = self._config.STREAM_STATE_EVENTS_STREAM
        self._frame_event_interval_seconds = (
            self._config.STREAM_STATE_FRAME_EVENT_MIN_INTERVAL_SECONDS
        )

        self._redis_client: Optional[redis.Redis] = None
        self._connected = False

        # Fallback in-memory state for local/dev and Redis outages.
        self._memory_state: Dict[str, Dict[str, Any]] = {}
        self._memory_viewers: Dict[str, int] = {}
        self._last_frame_event_ts: Dict[str, float] = {}
        self._readings_history: Dict[str, List[Dict[str, Any]]] = {}
        self._memory_events: List[Dict[str, Any]] = []
        self._max_readings_per_camera = 5000
        self._max_events = 50000

        self._editable_policy_ranges: Dict[str, Dict[str, int]] = {
            "liveness_ttl_seconds": {"min": 5, "max": 120, "step": 1},
            "stale_grace_seconds": {"min": 5, "max": 180, "step": 5},
            "reconnect_cooldown_seconds": {"min": 1, "max": 60, "step": 1},
            "retry_cap": {"min": 1, "max": 10, "step": 1},
        }
        self._policy_values_by_profile: Dict[str, Dict[str, int]] = {
            "usb": {
                "liveness_ttl_seconds": self._config.STREAM_PROFILE_USB_LIVENESS_TTL_SECONDS,
                "stale_grace_seconds": int(
                    getattr(self._config, "STREAM_PROFILE_USB_STALE_GRACE_SECONDS", 20)
                ),
                "reconnect_cooldown_seconds": 5,
                "retry_cap": 3,
            },
            "mobile": {
                "liveness_ttl_seconds": self._config.STREAM_PROFILE_MOBILE_LIVENESS_TTL_SECONDS,
                "stale_grace_seconds": int(
                    getattr(self._config, "STREAM_PROFILE_MOBILE_STALE_GRACE_SECONDS", 45)
                ),
                "reconnect_cooldown_seconds": 10,
                "retry_cap": 5,
            },
            "rtsp": {
                "liveness_ttl_seconds": self._config.STREAM_PROFILE_RTSP_LIVENESS_TTL_SECONDS,
                "stale_grace_seconds": int(
                    getattr(self._config, "STREAM_PROFILE_RTSP_STALE_GRACE_SECONDS", 35)
                ),
                "reconnect_cooldown_seconds": 8,
                "retry_cap": 5,
            },
            "edge": {
                "liveness_ttl_seconds": self._config.STREAM_PROFILE_EDGE_LIVENESS_TTL_SECONDS,
                "stale_grace_seconds": int(
                    getattr(self._config, "STREAM_PROFILE_EDGE_STALE_GRACE_SECONDS", 40)
                ),
                "reconnect_cooldown_seconds": 10,
                "retry_cap": 5,
            },
        }
        self._policy_versions: Dict[str, int] = {
            profile: 1 for profile in self._policy_values_by_profile.keys()
        }

    async def _connect_if_needed(self) -> bool:
        if not self._enabled:
            return False
        if self._connected and self._redis_client is not None:
            return True
        if redis is None:
            logger.warning("Redis dependency unavailable; stream state service running in memory mode")
            return False

        redis_url = self._config.STREAM_STATE_REDIS_URL
        if not redis_url:
            redis_url = (
                f"redis://{self._config.STREAM_STATE_REDIS_HOST}:"
                f"{self._config.STREAM_STATE_REDIS_PORT}/"
                f"{self._config.STREAM_STATE_REDIS_DB}"
            )

        try:
            self._redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            await self._redis_client.ping()
            self._connected = True
            logger.info("Stream operations state service connected to Redis")
            return True
        except Exception as exc:
            logger.warning("Stream operations state Redis unavailable; using memory fallback: %s", exc)
            self._connected = False
            self._redis_client = None
            return False

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _camera_profile(camera_type: str) -> str:
        normalized = (camera_type or "").upper()
        if normalized == "MOBILE":
            return "mobile"
        if normalized == "RTSP" or normalized == "IP":
            return "rtsp"
        if normalized == "EDGE":
            return "edge"
        return "usb"

    def _ttl_for_profile(self, profile: str) -> int:
        if profile == "mobile":
            return self._config.STREAM_PROFILE_MOBILE_LIVENESS_TTL_SECONDS
        if profile == "rtsp":
            return self._config.STREAM_PROFILE_RTSP_LIVENESS_TTL_SECONDS
        if profile == "edge":
            return self._config.STREAM_PROFILE_EDGE_LIVENESS_TTL_SECONDS
        return self._config.STREAM_PROFILE_USB_LIVENESS_TTL_SECONDS

    def _key_viewers(self, camera_id: str) -> str:
        return f"{self._namespace}:stream:{camera_id}:viewers"

    def _key_liveness(self, camera_id: str) -> str:
        return f"{self._namespace}:stream:{camera_id}:liveness"

    def _key_state(self, camera_id: str) -> str:
        return f"{self._namespace}:stream:{camera_id}:state"

    def _key_readings(self, camera_id: str) -> str:
        return f"{self._namespace}:stream:{camera_id}:readings"

    def _key_events(self, camera_id: str) -> str:
        return f"{self._namespace}:stream:{camera_id}:events"

    def _policy_key(self, scope_type: str, scope_id: str) -> str:
        return f"{self._namespace}:stream:policy:{scope_type}:{scope_id}"

    async def _xadd_event(self, camera_id: str, event: str, details: Optional[Dict[str, Any]] = None) -> None:
        details = details or {}
        timestamp = self._utc_now_iso()
        self._memory_events.append(
            {
                "camera_id": camera_id,
                "event": event,
                "timestamp": timestamp,
                "details": dict(details),
            }
        )
        if len(self._memory_events) > self._max_events:
            self._memory_events = self._memory_events[-self._max_events :]

        payload = {
            "camera_id": camera_id,
            "event": event,
            "timestamp": timestamp,
            "details": str(details),
        }

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                await self._redis_client.xadd(self._events_stream, payload, maxlen=50000, approximate=True)
                serialized = json.dumps(
                    {
                        "camera_id": camera_id,
                        "event": event,
                        "timestamp": timestamp,
                        "details": details,
                    }
                )
                await self._redis_client.rpush(self._key_events(camera_id), serialized)
                await self._redis_client.ltrim(self._key_events(camera_id), -self._max_events, -1)
            except Exception as exc:
                logger.debug("Failed to append stream lifecycle event for %s: %s", camera_id, exc)

    async def _append_reading(self, camera_id: str, reading: Dict[str, Any]) -> None:
        history = self._readings_history.setdefault(camera_id, [])
        history.append(reading)
        if len(history) > self._max_readings_per_camera:
            self._readings_history[camera_id] = history[-self._max_readings_per_camera :]

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                await self._redis_client.rpush(self._key_readings(camera_id), json.dumps(reading))
                await self._redis_client.ltrim(
                    self._key_readings(camera_id),
                    -self._max_readings_per_camera,
                    -1,
                )
            except Exception as exc:
                logger.debug("Failed to persist readings for %s: %s", camera_id, exc)

    @staticmethod
    def _parse_iso_timestamp(timestamp: str) -> Optional[datetime]:
        if not timestamp:
            return None
        try:
            normalized = timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    def _policy_for_profile(self, profile: str) -> Dict[str, int]:
        base_ttl = self._ttl_for_profile(profile)
        defaults = {
            "liveness_ttl_seconds": base_ttl,
            "stale_grace_seconds": 20,
        }
        policy = self._policy_values_by_profile.get(profile)
        if not policy:
            return defaults

        merged = dict(defaults)
        merged.update(policy)
        return merged

    async def _enforce_liveness_disconnect(
        self,
        camera_id: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Ensure connected states downgrade to DISCONNECTED when liveness expires."""
        stream_state = str(state.get("stream_state", "DISCONNECTED"))
        if stream_state not in {"CONNECTED_WITH_VIEWERS", "CONNECTED_NO_VIEWERS", "STALE_CANDIDATE"}:
            return state

        camera_type = str(state.get("camera_type", "UNKNOWN"))
        profile = str(state.get("camera_profile") or self._camera_profile(camera_type))
        policy = self._policy_for_profile(profile)
        liveness_ttl_seconds = int(policy.get("liveness_ttl_seconds", self._ttl_for_profile(profile)))
        stale_grace_seconds = int(policy.get("stale_grace_seconds", 20))
        stale_after_seconds = max(1, liveness_ttl_seconds + stale_grace_seconds)

        connected = await self._connect_if_needed()
        liveness_missing = False
        if connected and self._redis_client is not None:
            try:
                liveness_missing = int(await self._redis_client.exists(self._key_liveness(camera_id))) == 0
            except Exception as exc:
                logger.debug("Failed to verify liveness key for %s: %s", camera_id, exc)

        now_dt = datetime.now(timezone.utc)
        last_frame_dt = self._parse_iso_timestamp(str(state.get("last_frame_at", "")))
        updated_dt = self._parse_iso_timestamp(str(state.get("updated_at", "")))
        reference_dt = last_frame_dt or updated_dt
        stale_by_time = (
            reference_dt is None
            or (now_dt - reference_dt).total_seconds() > stale_after_seconds
        )

        if not (liveness_missing or stale_by_time):
            return state

        now = self._utc_now_iso()
        previous_state = stream_state
        reason = "liveness_expired"
        if liveness_missing and stale_by_time:
            reason = "liveness_and_timestamp_expired"
        elif liveness_missing:
            reason = "liveness_key_missing"
        elif stale_by_time:
            reason = "timestamp_expired"

        disconnected_state = {
            "camera_id": camera_id,
            "camera_type": camera_type,
            "camera_profile": profile,
            "stream_state": "DISCONNECTED",
            "active_viewers": 0,
            "last_frame_at": state.get("last_frame_at"),
            "frame_gap_ms": state.get("frame_gap_ms"),
            "last_transition_reason": reason,
            "updated_at": now,
        }

        if "quality" in state:
            disconnected_state["quality"] = state.get("quality")
        if "last_user_id" in state:
            disconnected_state["last_user_id"] = state.get("last_user_id")

        self._memory_viewers[camera_id] = 0
        if connected and self._redis_client is not None:
            try:
                await self._redis_client.set(self._key_viewers(camera_id), "0")
            except Exception as exc:
                logger.debug("Failed to reset viewer counter for %s: %s", camera_id, exc)

        await self._store_state(camera_id, disconnected_state)
        await self._append_reading(
            camera_id,
            {
                "ts": now,
                "camera_id": camera_id,
                "camera_type": camera_type,
                "active_viewers": 0,
                "frame_gap_ms": None,
                "event": "liveness_expired",
            },
        )
        await self._xadd_event(
            camera_id,
            "liveness_expired",
            {
                "from_state": previous_state,
                "reason": reason,
                "stale_after_seconds": stale_after_seconds,
                "last_frame_at": state.get("last_frame_at"),
            },
        )
        return disconnected_state

    async def _store_state(self, camera_id: str, state: Dict[str, Any]) -> None:
        self._memory_state[camera_id] = dict(state)
        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                serializable = {k: str(v) for k, v in state.items() if v is not None}
                await self._redis_client.hset(self._key_state(camera_id), mapping=serializable)
            except Exception as exc:
                logger.debug("Failed to write Redis stream state for %s: %s", camera_id, exc)

    async def register_viewer(
        self,
        camera_id: str,
        camera_type: str,
        user_id: Optional[str],
        quality: str,
    ) -> None:
        profile = self._camera_profile(camera_type)
        ttl = self._ttl_for_profile(profile)
        now = self._utc_now_iso()

        connected = await self._connect_if_needed()
        viewers = 0
        if connected and self._redis_client is not None:
            try:
                viewers = int(await self._redis_client.incr(self._key_viewers(camera_id)))
                await self._redis_client.setex(self._key_liveness(camera_id), ttl, now)
            except Exception as exc:
                logger.debug("Redis viewer registration fallback for %s: %s", camera_id, exc)
                connected = False

        if not connected:
            viewers = max(0, int(self._memory_viewers.get(camera_id, 0)) + 1)
            self._memory_viewers[camera_id] = viewers

        state = {
            "camera_id": camera_id,
            "camera_type": camera_type,
            "camera_profile": profile,
            "stream_state": "CONNECTED_WITH_VIEWERS",
            "active_viewers": viewers,
            "quality": quality,
            "last_frame_at": now,
            "last_transition_reason": "viewer_attached",
            "last_user_id": user_id or "unknown",
            "updated_at": now,
        }
        await self._store_state(camera_id, state)
        await self._append_reading(
            camera_id,
            {
                "ts": now,
                "camera_id": camera_id,
                "camera_type": camera_type,
                "active_viewers": viewers,
                "frame_gap_ms": None,
                "event": "viewer_attached",
            },
        )
        await self._xadd_event(
            camera_id,
            "viewer_attached",
            {"active_viewers": viewers, "quality": quality, "camera_type": camera_type},
        )

    async def unregister_viewer(self, camera_id: str, reason: str = "viewer_detached") -> None:
        now = self._utc_now_iso()
        connected = await self._connect_if_needed()
        viewers = 0
        existing_state = await self.get_camera_state(camera_id)
        camera_type = existing_state.get("camera_type", "UNKNOWN")
        profile = existing_state.get("camera_profile", self._camera_profile(camera_type))

        if connected and self._redis_client is not None:
            try:
                viewers = int(await self._redis_client.decr(self._key_viewers(camera_id)))
                if viewers < 0:
                    viewers = 0
                    await self._redis_client.set(self._key_viewers(camera_id), "0")
            except Exception as exc:
                logger.debug("Redis viewer unregister fallback for %s: %s", camera_id, exc)
                connected = False

        if not connected:
            viewers = max(0, int(self._memory_viewers.get(camera_id, 0)) - 1)
            self._memory_viewers[camera_id] = viewers

        state = {
            "camera_id": camera_id,
            "camera_type": camera_type,
            "camera_profile": profile,
            "stream_state": "CONNECTED_NO_VIEWERS" if viewers == 0 else "CONNECTED_WITH_VIEWERS",
            "active_viewers": viewers,
            "last_transition_reason": reason,
            "updated_at": now,
        }
        await self._store_state(camera_id, state)
        await self._append_reading(
            camera_id,
            {
                "ts": now,
                "camera_id": camera_id,
                "camera_type": camera_type,
                "active_viewers": viewers,
                "frame_gap_ms": None,
                "event": "viewer_detached",
            },
        )
        await self._xadd_event(camera_id, "viewer_detached", {"active_viewers": viewers, "reason": reason})

    async def heartbeat_frame(
        self,
        camera_id: str,
        camera_type: str,
        frame_gap_ms: Optional[int] = None,
    ) -> None:
        profile = self._camera_profile(camera_type)
        ttl = self._ttl_for_profile(profile)
        now = self._utc_now_iso()

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                await self._redis_client.setex(self._key_liveness(camera_id), ttl, now)
            except Exception as exc:
                logger.debug("Redis liveness refresh fallback for %s: %s", camera_id, exc)

        existing_state = await self.get_camera_state(camera_id)
        viewers = int(existing_state.get("active_viewers", 0))
        state = {
            "camera_id": camera_id,
            "camera_type": camera_type,
            "camera_profile": profile,
            "stream_state": "CONNECTED_WITH_VIEWERS" if viewers > 0 else "CONNECTED_NO_VIEWERS",
            "active_viewers": viewers,
            "last_frame_at": now,
            "frame_gap_ms": frame_gap_ms if frame_gap_ms is not None else existing_state.get("frame_gap_ms"),
            "last_transition_reason": "frame_received",
            "updated_at": now,
        }
        await self._store_state(camera_id, state)
        effective_fps = None
        if frame_gap_ms and frame_gap_ms > 0:
            effective_fps = round(1000.0 / float(frame_gap_ms), 2)
        await self._append_reading(
            camera_id,
            {
                "ts": now,
                "camera_id": camera_id,
                "camera_type": camera_type,
                "active_viewers": viewers,
                "frame_gap_ms": frame_gap_ms,
                "effective_fps": effective_fps,
                "event": "frame_received",
            },
        )

        last_event = self._last_frame_event_ts.get(camera_id, 0.0)
        now_ts = time.time()
        if now_ts - last_event >= self._frame_event_interval_seconds:
            self._last_frame_event_ts[camera_id] = now_ts
            await self._xadd_event(camera_id, "frame_received", {"frame_gap_ms": frame_gap_ms})

    async def mark_stale_candidate(self, camera_id: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        now = self._utc_now_iso()
        existing = await self.get_camera_state(camera_id)
        state = {
            "camera_id": camera_id,
            "camera_type": existing.get("camera_type", "UNKNOWN"),
            "camera_profile": existing.get("camera_profile", "usb"),
            "stream_state": "STALE_CANDIDATE",
            "active_viewers": int(existing.get("active_viewers", 0)),
            "last_transition_reason": reason,
            "updated_at": now,
        }
        await self._store_state(camera_id, state)
        await self._append_reading(
            camera_id,
            {
                "ts": now,
                "camera_id": camera_id,
                "camera_type": state["camera_type"],
                "active_viewers": state["active_viewers"],
                "frame_gap_ms": None,
                "event": "stale_candidate",
            },
        )
        payload = {"reason": reason}
        if details:
            payload.update(details)
        await self._xadd_event(camera_id, "stale_candidate", payload)

    async def mark_stream_stopped(self, camera_id: str, reason: str = "stream_stopped") -> None:
        now = self._utc_now_iso()
        existing_state = await self.get_camera_state(camera_id)
        camera_type = existing_state.get("camera_type", "UNKNOWN")
        profile = existing_state.get("camera_profile", self._camera_profile(camera_type))

        connected = await self._connect_if_needed()
        self._memory_viewers[camera_id] = 0
        if connected and self._redis_client is not None:
            try:
                await self._redis_client.set(self._key_viewers(camera_id), "0")
            except Exception as exc:
                logger.debug("Failed to reset viewer counter on stream stop for %s: %s", camera_id, exc)

        state = {
            "camera_id": camera_id,
            "camera_type": camera_type,
            "camera_profile": profile,
            "stream_state": "DISCONNECTED",
            "active_viewers": 0,
            "last_frame_at": existing_state.get("last_frame_at"),
            "frame_gap_ms": existing_state.get("frame_gap_ms"),
            "last_transition_reason": reason,
            "updated_at": now,
        }
        await self._store_state(camera_id, state)
        await self._append_reading(
            camera_id,
            {
                "ts": now,
                "camera_id": camera_id,
                "camera_type": camera_type,
                "active_viewers": 0,
                "frame_gap_ms": None,
                "event": "stream_stopped",
            },
        )
        await self._xadd_event(camera_id, "stream_stopped", {"reason": reason})

    def _validate_policy_changes(self, changes: Dict[str, int]) -> None:
        for key, value in changes.items():
            if key not in self._editable_policy_ranges:
                raise ValueError(f"Unsupported policy key: {key}")

            bounds = self._editable_policy_ranges[key]
            minimum = bounds["min"]
            maximum = bounds["max"]
            step = bounds["step"]
            if not isinstance(value, int):
                raise ValueError(f"Policy value for {key} must be integer")
            if value < minimum or value > maximum:
                raise ValueError(
                    f"Policy value for {key} must be between {minimum} and {maximum}"
                )
            if (value - minimum) % step != 0:
                raise ValueError(
                    f"Policy value for {key} must follow step {step} from min {minimum}"
                )

    async def list_policies(
        self,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if scope_type not in (None, "camera_type"):
            raise ValueError("Only scope_type 'camera_type' is currently supported")

        profiles = [scope_id] if scope_id else list(self._policy_values_by_profile.keys())
        policies = []
        for profile in profiles:
            if profile not in self._policy_values_by_profile:
                continue
            values = dict(self._policy_values_by_profile[profile])
            policies.append(
                {
                    "scope_type": "camera_type",
                    "scope_id": profile,
                    "version": self._policy_versions.get(profile, 1),
                    "effective_values": values,
                    "editable_ranges": self._editable_policy_ranges,
                    "updated_at": self._utc_now_iso(),
                }
            )

        return {"policies": policies}

    async def update_policy(
        self,
        scope_type: str,
        scope_id: str,
        changes: Dict[str, int],
        if_version: int,
        reason: str,
        actor: str,
    ) -> Dict[str, Any]:
        if scope_type != "camera_type":
            raise ValueError("Only scope_type 'camera_type' is currently supported")
        if scope_id not in self._policy_values_by_profile:
            raise ValueError(f"Unknown policy scope_id: {scope_id}")
        if not reason or len(reason.strip()) < 8:
            raise ValueError("Policy update reason is required and must be at least 8 characters")

        current_version = self._policy_versions.get(scope_id, 1)
        if if_version != current_version:
            raise RuntimeError(
                f"Policy version conflict for {scope_id}: expected {current_version}, received {if_version}"
            )

        self._validate_policy_changes(changes)

        old_values = dict(self._policy_values_by_profile[scope_id])
        new_values = dict(old_values)
        new_values.update(changes)
        self._policy_values_by_profile[scope_id] = new_values
        self._policy_versions[scope_id] = current_version + 1

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                redis_mapping = {k: str(v) for k, v in new_values.items()}
                redis_mapping["version"] = str(self._policy_versions[scope_id])
                redis_mapping["updated_by"] = actor
                redis_mapping["updated_at"] = self._utc_now_iso()
                redis_mapping["reason"] = reason
                await self._redis_client.hset(
                    self._policy_key(scope_type, scope_id), mapping=redis_mapping
                )
            except Exception as exc:
                logger.debug("Failed to persist policy update to Redis for %s: %s", scope_id, exc)

        await self._xadd_event(
            camera_id=scope_id,
            event="policy_updated",
            details={"scope_type": scope_type, "changes": changes, "updated_by": actor},
        )

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "previous_version": current_version,
            "new_version": self._policy_versions[scope_id],
            "old_values": old_values,
            "new_values": new_values,
        }

    async def get_camera_state(self, camera_id: str) -> Dict[str, Any]:
        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                state = await self._redis_client.hgetall(self._key_state(camera_id))
                if state:
                    viewers = await self._redis_client.get(self._key_viewers(camera_id))
                    if viewers is not None:
                        state["active_viewers"] = int(viewers)
                    elif "active_viewers" in state:
                        state["active_viewers"] = int(state["active_viewers"])
                    return await self._enforce_liveness_disconnect(camera_id, state)
            except Exception as exc:
                logger.debug("Failed to read Redis state for %s: %s", camera_id, exc)

        state = dict(self._memory_state.get(camera_id, {}))
        if not state:
            return state
        return await self._enforce_liveness_disconnect(camera_id, state)

    async def get_many_states(self, camera_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for camera_id in camera_ids:
            result[camera_id] = await self.get_camera_state(camera_id)
        return result

    async def query_readings(
        self,
        camera_ids: Optional[Iterable[str]],
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        selected_ids = set(camera_ids) if camera_ids is not None else set(self._readings_history.keys())
        rows: List[Dict[str, Any]] = []

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            for camera_id in selected_ids:
                try:
                    raw_rows = await self._redis_client.lrange(self._key_readings(camera_id), 0, -1)
                    for raw in raw_rows:
                        parsed_row = json.loads(raw)
                        parsed = self._parse_iso_timestamp(str(parsed_row.get("ts", "")))
                        if parsed is None:
                            continue
                        if from_dt <= parsed <= to_dt:
                            rows.append(parsed_row)
                except Exception as exc:
                    logger.debug("Failed to query Redis readings for %s: %s", camera_id, exc)

        if not rows:
            for camera_id in selected_ids:
                for reading in self._readings_history.get(camera_id, []):
                    parsed = self._parse_iso_timestamp(str(reading.get("ts", "")))
                    if parsed is None:
                        continue
                    if from_dt <= parsed <= to_dt:
                        rows.append(dict(reading))

        rows.sort(key=lambda item: item.get("ts", ""))
        if len(rows) > limit:
            rows = rows[-limit:]
        return rows

    async def query_incident_events(
        self,
        camera_id: str,
        from_dt: datetime,
        to_dt: datetime,
        include_policy_changes: bool = True,
        policy_scope_hint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            keys = [self._key_events(camera_id)]
            if include_policy_changes and policy_scope_hint:
                keys.append(self._key_events(policy_scope_hint))

            for key in keys:
                try:
                    raw_events = await self._redis_client.lrange(key, 0, -1)
                    for raw in raw_events:
                        event = json.loads(raw)
                        parsed = self._parse_iso_timestamp(str(event.get("timestamp", "")))
                        if parsed is None or parsed < from_dt or parsed > to_dt:
                            continue

                        event_name = event.get("event")
                        event_camera_id = event.get("camera_id")
                        is_camera_event = event_camera_id == camera_id
                        is_policy_event = (
                            include_policy_changes
                            and event_name == "policy_updated"
                            and (policy_scope_hint is None or event_camera_id == policy_scope_hint)
                        )
                        if not is_camera_event and not is_policy_event:
                            continue

                        event_type = "policy_change" if event_name == "policy_updated" else "lifecycle"
                        events.append(
                            {
                                "ts": event.get("timestamp"),
                                "type": event_type,
                                "name": event_name,
                                "details": event.get("details", {}),
                            }
                        )
                except Exception as exc:
                    logger.debug("Failed to query Redis incident events for key %s: %s", key, exc)

        if events:
            events.sort(key=lambda item: item.get("ts", ""))
            return events

        for event in self._memory_events:
            parsed = self._parse_iso_timestamp(str(event.get("timestamp", "")))
            if parsed is None or parsed < from_dt or parsed > to_dt:
                continue

            is_camera_event = event.get("camera_id") == camera_id
            is_policy_event = (
                include_policy_changes
                and event.get("event") == "policy_updated"
                and (
                    policy_scope_hint is None
                    or event.get("camera_id") == policy_scope_hint
                )
            )
            if not is_camera_event and not is_policy_event:
                continue

            event_type = "policy_change" if event.get("event") == "policy_updated" else "lifecycle"
            events.append(
                {
                    "ts": event.get("timestamp"),
                    "type": event_type,
                    "name": event.get("event"),
                    "details": event.get("details", {}),
                }
            )

        events.sort(key=lambda item: item.get("ts", ""))
        return events

    async def list_tracked_camera_ids(self) -> List[str]:
        camera_ids = set(self._memory_state.keys())
        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                keys = await self._redis_client.keys(f"{self._namespace}:stream:*:state")
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 4:
                        camera_ids.add(parts[2])
            except Exception as exc:
                logger.debug("Failed to list tracked camera IDs from Redis: %s", exc)

        return sorted(camera_ids)

    async def reconcile_camera_state(self, camera_id: str) -> Dict[str, Any]:
        state = await self.get_camera_state(camera_id)
        if not state:
            return {
                "camera_id": camera_id,
                "status": "not_found",
                "changes": [],
            }

        changes: List[Dict[str, Any]] = []
        now = self._utc_now_iso()

        state = await self._enforce_liveness_disconnect(camera_id, state)

        viewers = int(state.get("active_viewers", 0) or 0)
        if viewers < 0:
            viewers = 0
            changes.append({"field": "active_viewers", "reason": "negative_viewers_clamped"})

        stream_state = state.get("stream_state", "DISCONNECTED")
        expected_state = "CONNECTED_WITH_VIEWERS" if viewers > 0 else "CONNECTED_NO_VIEWERS"
        if stream_state in {"CONNECTED_WITH_VIEWERS", "CONNECTED_NO_VIEWERS"} and stream_state != expected_state:
            state["stream_state"] = expected_state
            changes.append(
                {
                    "field": "stream_state",
                    "from": stream_state,
                    "to": expected_state,
                    "reason": "viewer_count_reconciliation",
                }
            )

        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                redis_viewers = await self._redis_client.get(self._key_viewers(camera_id))
                if redis_viewers is not None:
                    redis_viewers_int = max(0, int(redis_viewers))
                    if redis_viewers_int != viewers:
                        viewers = redis_viewers_int
                        state["active_viewers"] = redis_viewers_int
                        changes.append(
                            {
                                "field": "active_viewers",
                                "from": int(state.get("active_viewers", 0) or 0),
                                "to": redis_viewers_int,
                                "reason": "redis_counter_authoritative",
                            }
                        )
            except Exception as exc:
                logger.debug("Redis viewer reconciliation failed for %s: %s", camera_id, exc)

        state["active_viewers"] = viewers
        state["updated_at"] = now

        if changes:
            await self._store_state(camera_id, state)
            await self._xadd_event(
                camera_id,
                "reconciled",
                {"changes": changes},
            )

        return {
            "camera_id": camera_id,
            "status": "updated" if changes else "ok",
            "changes": changes,
            "state": {
                "stream_state": state.get("stream_state"),
                "active_viewers": viewers,
                "updated_at": state.get("updated_at"),
            },
        }

    async def get_last_event_timestamp(self, event_name: str) -> Optional[str]:
        """Return most recent timestamp for a lifecycle event name."""
        connected = await self._connect_if_needed()
        if connected and self._redis_client is not None:
            try:
                entries = await self._redis_client.xrevrange(self._events_stream, count=200)
                for _, payload in entries:
                    if payload.get("event") == event_name:
                        return payload.get("timestamp")
            except Exception as exc:
                logger.debug("Failed to fetch last event timestamp for %s: %s", event_name, exc)

        for event in reversed(self._memory_events):
            if event.get("event") == event_name:
                return str(event.get("timestamp"))
        return None


_stream_operations_state_service: Optional[StreamOperationsStateService] = None


def get_stream_operations_state_service() -> StreamOperationsStateService:
    global _stream_operations_state_service
    if _stream_operations_state_service is None:
        _stream_operations_state_service = StreamOperationsStateService()
    return _stream_operations_state_service

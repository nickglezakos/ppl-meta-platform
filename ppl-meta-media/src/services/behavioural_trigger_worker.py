"""
Behavioural Trigger Worker

Evaluates intent metrics over a Redis ring of Instant Detection flush snapshots.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.models.trigger import Trigger
from src.schemas.trigger import INTENT_METRIC_FIELDS
from src.services.behavioural_flush_ring import load_flush_ring

logger = logging.getLogger(__name__)

_worker: Optional["BehaviouralTriggerWorker"] = None


def get_behavioural_trigger_worker() -> "BehaviouralTriggerWorker":
    global _worker
    if _worker is None:
        _worker = BehaviouralTriggerWorker()
    return _worker


def _parse_conditions(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [c for c in raw if isinstance(c, dict)]
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [c for c in parsed if isinstance(c, dict)]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    return []


def _parse_ts(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw.astimezone(timezone.utc)
    if isinstance(raw, (int, float)):
        # epoch seconds vs ms
        val = float(raw)
        if val > 1e12:
            val = val / 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(raw, str):
        try:
            normalized = raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _compare(actual: Optional[float], operator: str, threshold: float) -> bool:
    if actual is None:
        return False
    op = (operator or "gte").lower()
    if op == "gt":
        return actual > threshold
    if op == "gte":
        return actual >= threshold
    if op == "lt":
        return actual < threshold
    if op == "lte":
        return actual <= threshold
    if op == "eq":
        return abs(actual - threshold) < 1e-6
    return False


def compute_behavioural_metrics(ring: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Phase-1 intent metrics over newest-first flush ring."""
    if not ring:
        return {
            "occupancy_span_count": 0.0,
            "peak_occupancy_window": 0.0,
            "dwell_seconds": 0.0,
            "path_velocity_avg": 0.0,
            "co_presence_count": 0.0,
            "buffer_len": 0,
            "window_span_seconds": 0.0,
        }

    counts = [int(f.get("people_count") or 0) for f in ring]
    occupancy_latest = float(counts[0])
    peak = float(max(counts) if counts else 0)
    co_presence = float(max((c for c in counts if c >= 2), default=0))

    # Per-flush mean velocity → mean across flushes with data
    flush_vels: List[float] = []
    max_tif = 0.0
    # Cross-flush dwell: first/last sighting by person id
    first_seen: Dict[str, datetime] = {}
    last_seen: Dict[str, datetime] = {}

    # Iterate oldest→newest for sighting span
    for flush in reversed(ring):
        flush_start = _parse_ts(flush.get("flush_started_at")) or _parse_ts(
            flush.get("timestamp")
        )
        flush_end = _parse_ts(flush.get("flush_ended_at")) or flush_start
        people = flush.get("people") or []
        vels: List[float] = []
        if isinstance(people, list):
            for person in people:
                if not isinstance(person, dict):
                    continue
                tif = person.get("time_in_frame_seconds")
                if isinstance(tif, (int, float)) and tif > max_tif:
                    max_tif = float(tif)
                vel = person.get("average_route_velocity")
                if isinstance(vel, (int, float)) and vel > 0:
                    vels.append(float(vel))
                pou = person.get("person_object_uuid")
                if pou and flush_start:
                    key = str(pou)
                    if key not in first_seen:
                        first_seen[key] = flush_start
                    if flush_end:
                        last_seen[key] = flush_end
                    elif flush_start:
                        last_seen[key] = flush_start
        if vels:
            flush_vels.append(sum(vels) / len(vels))

    cross_dwell = 0.0
    for key, start in first_seen.items():
        end = last_seen.get(key)
        if end and end >= start:
            cross_dwell = max(cross_dwell, (end - start).total_seconds())

    dwell = max(max_tif, cross_dwell)
    path_vel = sum(flush_vels) / len(flush_vels) if flush_vels else 0.0

    newest_end = _parse_ts(ring[0].get("flush_ended_at")) or _parse_ts(
        ring[0].get("timestamp")
    )
    oldest_start = _parse_ts(ring[-1].get("flush_started_at")) or _parse_ts(
        ring[-1].get("timestamp")
    )
    window_span = 0.0
    if newest_end and oldest_start and newest_end >= oldest_start:
        window_span = (newest_end - oldest_start).total_seconds()

    return {
        "occupancy_span_count": occupancy_latest,
        "peak_occupancy_window": peak,
        "dwell_seconds": float(dwell),
        "path_velocity_avg": float(path_vel),
        "co_presence_count": co_presence,
        "buffer_len": len(ring),
        "window_span_seconds": float(window_span),
    }


class BehaviouralTriggerWorker:
    async def evaluate(
        self,
        trigger: Trigger,
        redis,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        camera_id = getattr(trigger, "camera_device_id", None)
        if not camera_id:
            return False, "behavioural: missing camera_device_id", None

        lookback = int(getattr(trigger, "behavioural_lookback_flushes", None) or 6)
        lookback = max(2, min(lookback, 60))
        conditions = _parse_conditions(getattr(trigger, "behavioural_conditions", None))
        if not conditions:
            return False, "behavioural: no conditions", None

        ring = await load_flush_ring(redis, str(camera_id), lookback)
        if not ring:
            return False, "behavioural: empty flush ring (warming up)", {
                "buffer_len": 0,
                "lookback_flushes": lookback,
                "warming_up": True,
            }

        metrics = compute_behavioural_metrics(ring)
        logic = (getattr(trigger, "behavioural_condition_logic", None) or "and").lower()
        results: List[bool] = []
        details: List[Dict[str, Any]] = []
        for cond in conditions:
            field = str(cond.get("field") or "")
            if field not in INTENT_METRIC_FIELDS:
                results.append(False)
                details.append({"field": field, "ok": False, "reason": "unknown_field"})
                continue
            op = str(cond.get("operator") or "gte")
            try:
                threshold = float(cond.get("value"))
            except (TypeError, ValueError):
                results.append(False)
                details.append({"field": field, "ok": False, "reason": "bad_value"})
                continue
            actual = metrics.get(field)
            try:
                actual_f = float(actual) if actual is not None else None
            except (TypeError, ValueError):
                actual_f = None
            ok = _compare(actual_f, op, threshold)
            results.append(ok)
            details.append(
                {
                    "field": field,
                    "operator": op,
                    "threshold": threshold,
                    "actual": actual_f,
                    "ok": ok,
                }
            )

        matched = all(results) if logic != "or" else any(results)
        info = {
            "metrics": metrics,
            "conditions": details,
            "logic": logic,
            "lookback_flushes": lookback,
            "buffer_len": metrics.get("buffer_len"),
            "window_span_seconds": metrics.get("window_span_seconds"),
            "warming_up": int(metrics.get("buffer_len") or 0) < lookback,
            "camera_device_id": camera_id,
        }
        if matched:
            return True, "Behavioural conditions met", info
        return False, "Behavioural conditions not met", info

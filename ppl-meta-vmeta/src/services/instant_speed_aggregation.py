"""Aggregate Instant Detection ground-speed (m/s) and gait band for analysis."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# Keep in sync with ppl-meta-cameras/src/services/instant_velocity.py
GAIT_THRESHOLD_MPS = {
    "walking": 1.25,
    "light_running": 2.2,
    "running": 3.3,
    "fast_running": 5.0,
}
GAIT_BAND_ORDER = (
    "walking",
    "light_running",
    "running",
    "fast_running",
)


def gait_band_for_speed_mps(speed_mps: Optional[float]) -> Optional[str]:
    """Highest gait band whose floor the speed meets, or None below walking."""
    if speed_mps is None:
        return None
    matched: Optional[str] = None
    for band in GAIT_BAND_ORDER:
        if float(speed_mps) >= GAIT_THRESHOLD_MPS[band]:
            matched = band
    return matched


def instant_record_speed_mps(record: Dict[str, Any]) -> Optional[float]:
    """Read ground speed (m/s) from an Instant flush / appearance record."""
    candidates = [
        record.get("speed_mps"),
        record.get("average_speed_mps"),
    ]
    tracking = record.get("movement_tracking")
    if isinstance(tracking, dict):
        stats = tracking.get("movement_statistics") or {}
        if isinstance(stats, dict):
            candidates.append(stats.get("average_speed_mps"))
    pattern = record.get("movement_pattern")
    if isinstance(pattern, str):
        try:
            pattern = json.loads(pattern)
        except (json.JSONDecodeError, TypeError, ValueError):
            pattern = None
    if isinstance(pattern, dict):
        stats = pattern.get("movement_statistics") or pattern
        if isinstance(stats, dict):
            candidates.append(stats.get("average_speed_mps"))
            candidates.append(stats.get("speed_mps"))
    for raw in candidates:
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def aggregate_speed_and_gait(
    records: List[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[str]]:
    """Mean speed_mps across member records; gait_band derived from that mean.

    Prefer the mean of positive speeds so stationary 0 m/s members do not
    zero-out Instant Statistics / analysis averages.
    """
    speeds: List[float] = []
    for record in records:
        speed = instant_record_speed_mps(record)
        if speed is not None:
            speeds.append(speed)
    if not speeds:
        return None, None
    positive = [s for s in speeds if s > 0]
    chosen = positive if positive else speeds
    average = round(sum(chosen) / len(chosen), 4)
    return average, gait_band_for_speed_mps(average)

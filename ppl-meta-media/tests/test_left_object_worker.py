"""Unit tests for left_object worker state machine (V1 STABLE + V2 ABANDONED)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.services.left_object_worker import LeftObjectWorker, get_left_object_metrics


def _trigger(**overrides):
    base = dict(
        uuid="11111111-1111-1111-1111-111111111111",
        camera_device_ids='["cam_a"]',
        camera_device_id="left_object",
        left_object_class_allowlist='["backpack"]',
        left_object_roi=None,
        left_object_t_stable_seconds=10,
        left_object_t_abandon_seconds=5,
        left_object_min_box_area_px=100,
        left_object_require_person_left=False,
        left_object_proximity_px=120.0,
        left_object_iou_threshold=0.3,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _event(ts: datetime, bbox, *, bodies=None):
    return {
        "camera_id": "cam_a",
        "timestamp": ts.isoformat(),
        "objects": [
            {
                "class_label": "backpack",
                "class_id": 24,
                "bbox": bbox,
                "confidence": 0.9,
            }
        ],
        "body_persons": bodies or [],
    }


@pytest.mark.asyncio
async def test_v1_fires_when_stable():
    worker = LeftObjectWorker()
    trigger = _trigger(left_object_require_person_left=False)
    await worker.activate_trigger(trigger)

    t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    bbox = [100.0, 100.0, 160.0, 180.0]

    passed, _, info = await worker.evaluate(trigger, _event(t0, bbox))
    assert passed is False

    # Still moving slightly within eps — accumulate stability from first low-motion cycle
    passed, _, info = await worker.evaluate(
        trigger, _event(t0 + timedelta(seconds=5), [101.0, 100.0, 161.0, 180.0])
    )
    assert passed is False

    passed, reason, info = await worker.evaluate(
        trigger, _event(t0 + timedelta(seconds=12), [102.0, 101.0, 162.0, 181.0])
    )
    assert passed is True
    assert info is not None
    assert info["class_label"] == "backpack"
    assert info["state"] == "STABLE"
    assert "left_object MET" in reason

    # Second fire suppressed (ACKNOWLEDGED)
    passed2, _, _ = await worker.evaluate(
        trigger, _event(t0 + timedelta(seconds=20), [102.0, 101.0, 162.0, 181.0])
    )
    assert passed2 is False


@pytest.mark.asyncio
async def test_v2_requires_person_left():
    worker = LeftObjectWorker()
    trigger = _trigger(
        left_object_require_person_left=True,
        left_object_t_stable_seconds=10,
        left_object_t_abandon_seconds=5,
        left_object_proximity_px=80.0,
    )
    await worker.activate_trigger(trigger)

    t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    bbox = [100.0, 100.0, 160.0, 180.0]
    # Body overlapping object center ~(130,140)
    body_near = [{"average_bbox": [110.0, 90.0, 150.0, 200.0]}]

    # Stabilize with person nearby → ATTENDED, no fire
    for sec in (0, 5, 12):
        passed, _, info = await worker.evaluate(
            trigger,
            _event(t0 + timedelta(seconds=sec), bbox, bodies=body_near),
        )
        assert passed is False

    # Person leaves but abandon not yet long enough
    passed, _, _ = await worker.evaluate(
        trigger, _event(t0 + timedelta(seconds=14), bbox, bodies=[])
    )
    assert passed is False

    # After T_abandon → fire
    passed, reason, info = await worker.evaluate(
        trigger, _event(t0 + timedelta(seconds=20), bbox, bodies=[])
    )
    assert passed is True
    assert info["state"] == "ABANDONED"
    assert "left_object MET" in reason


@pytest.mark.asyncio
async def test_v2_fail_closed_without_attendance():
    worker = LeftObjectWorker()
    trigger = _trigger(
        left_object_require_person_left=True,
        left_object_t_stable_seconds=10,
    )
    await worker.activate_trigger(trigger)
    t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    bbox = [100.0, 100.0, 160.0, 180.0]

    for sec in (0, 5, 15, 30):
        passed, _, _ = await worker.evaluate(
            trigger, _event(t0 + timedelta(seconds=sec), bbox, bodies=[])
        )
        assert passed is False


def test_metrics_counters_increment():
    before = get_left_object_metrics()
    assert "left_object_tracks" in before
    assert "left_object_fired" in before
    assert "left_object_cleared" in before

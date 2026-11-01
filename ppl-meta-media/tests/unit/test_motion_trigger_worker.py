"""Unit tests for motion trigger AND/OR conditions and ROI transit."""

from __future__ import annotations

import types

import pytest

from src.services.motion_trigger_worker import (
    MotionTriggerWorker,
    classify_roi_transit,
    distance_to_roi,
    parse_motion_conditions,
)


def _trigger(**kwargs):
    defaults = {
        "uuid": "00000000-0000-0000-0000-000000000001",
        "motion_scope": "crowd",
        "motion_condition_logic": "and",
        "motion_conditions": None,
        "motion_roi": None,
        "velocity_scope": None,
        "velocity_band": None,
        "camera_device_ids": '["cam_a"]',
        "camera_device_id": "motion",
        "is_active": True,
        "trigger_mode": "motion",
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_legacy_velocity_band_backfill_fires_on_crowd_speed():
    worker = MotionTriggerWorker()
    trigger = _trigger(velocity_band="walking", motion_conditions=None)
    data = {
        "camera_id": "cam_a",
        "velocity": {
            "crowd_mps": 1.5,
            "max_mps": 1.5,
            "valid_count": 1,
            "people": [{"person_object_uuid": "p1", "speed_mps": 1.5}],
        },
    }
    passed, reason, info = await worker.evaluate(trigger, data)
    assert passed is True
    assert "MET" in reason
    assert info["logic"] == "and"


@pytest.mark.asyncio
async def test_and_requires_all_dimensions():
    worker = MotionTriggerWorker()
    trigger = _trigger(
        motion_condition_logic="and",
        motion_scope="single",
        motion_conditions='[{"field":"speed_band","operator":"gte","value":"walking"},'
        '{"field":"motion_class","operator":"eq","value":"directed_transit"}]',
    )
    # Fast but short route → likely unknown/not directed_transit with 1 point
    data = {
        "camera_id": "cam_a",
        "timestamp": 1000.0,
        "velocity": {
            "crowd_mps": 2.0,
            "max_mps": 2.0,
            "valid_count": 1,
            "people": [
                {
                    "person_object_uuid": "p1",
                    "speed_mps": 2.0,
                    "center_norm": [0.1, 0.1],
                    "route_tail": [{"center_norm": [0.1, 0.1], "timestamp": 1000.0}],
                }
            ],
        },
    }
    passed, _, info = await worker.evaluate(trigger, data)
    # speed passes, class likely fails with tiny route → AND fails
    assert passed is False
    assert any(c["field"] == "speed_band" and c["passed"] for c in info["conditions"])


@pytest.mark.asyncio
async def test_or_passes_when_one_dimension_matches():
    worker = MotionTriggerWorker()
    trigger = _trigger(
        motion_condition_logic="or",
        motion_scope="crowd",
        motion_conditions='[{"field":"speed_band","operator":"gte","value":"running"},'
        '{"field":"roi_transit","operator":"eq","value":"inside"}]',
        motion_roi="[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]",
    )
    data = {
        "camera_id": "cam_a",
        "timestamp": 1.0,
        "velocity": {
            "crowd_mps": 0.5,
            "max_mps": 0.5,
            "valid_count": 1,
            "people": [
                {
                    "person_object_uuid": "p1",
                    "speed_mps": 0.5,
                    "center_norm": [0.5, 0.5],
                }
            ],
        },
    }
    passed, reason, info = await worker.evaluate(trigger, data)
    assert passed is True
    assert info["logic"] == "or"
    assert any(c["field"] == "roi_transit" and c["passed"] for c in info["conditions"])


def test_roi_approach_by_distance_trend():
    poly = [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]]
    assert classify_roi_transit(
        center=(0.2, 0.5),
        prev_center=(0.05, 0.5),
        velocity_xy=(0.1, 0.0),
        polygon=poly,
    ) == "approach"


def test_roi_retreat_by_distance_trend():
    poly = [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]]
    assert classify_roi_transit(
        center=(0.05, 0.5),
        prev_center=(0.2, 0.5),
        velocity_xy=(-0.1, 0.0),
        polygon=poly,
    ) == "retreat"


def test_roi_inside():
    poly = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert classify_roi_transit(
        center=(0.5, 0.5),
        prev_center=None,
        velocity_xy=None,
        polygon=poly,
    ) == "inside"
    assert distance_to_roi(0.5, 0.5, poly) == 0.0


def test_parse_conditions_from_json_list():
    trigger = _trigger(
        motion_conditions=[
            {"field": "motion_class", "operator": "in", "value": ["loitering", "pacing"]}
        ]
    )
    conds = parse_motion_conditions(trigger)
    assert len(conds) == 1
    assert conds[0]["field"] == "motion_class"
    assert conds[0]["value"] == ["loitering", "pacing"]

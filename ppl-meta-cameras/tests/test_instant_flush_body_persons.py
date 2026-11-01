"""Y-window flush buffer carries body_persons with derived route_points."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.instant_detection_flush import (  # noqa: E402
    collect_body_persons_for_flush,
    enrich_body_person_for_flush,
    push_cycle_to_flush_buffer,
    route_points_from_body_trajectory,
)


def test_route_points_from_body_trajectory():
    person = {
        "bbox_trajectory": [
            {"frame": 0, "bbox": [10, 20, 50, 120], "confidence": 0.9},
            {"frame": 2, "bbox": [12, 22, 52, 122], "confidence": 0.8},
        ]
    }
    points = route_points_from_body_trajectory(person, cycle_epoch=1_700_000_000.0)
    assert len(points) == 2
    assert points[0]["center_x"] == 30.0
    assert points[1]["timestamp"] == points[0]["timestamp"] + 1.0  # 2 frames * 0.5s


def test_enrich_body_person_for_flush_sets_modality():
    enriched = enrich_body_person_for_flush(
        {
            "body_person_id": "bp-1",
            "bbox_trajectory": [
                {"frame": 1, "bbox": [0, 0, 10, 20], "confidence": 0.5},
            ],
        },
        cycle_id="c1",
        cycle_timestamp="2026-03-19T12:00:00+00:00",
    )
    assert enriched["identity_modality"] == "body"
    assert enriched["route_points"]
    assert enriched["first_seen"]
    assert enriched["last_seen"]


def test_collect_body_persons_for_flush_dedupes_by_id():
    cycles = [
        {
            "cycle_id": "c1",
            "timestamp": "2026-03-19T12:00:00+00:00",
            "body_persons": [
                {
                    "body_person_id": "bp-1",
                    "bbox_trajectory": [
                        {"frame": 0, "bbox": [0, 0, 10, 20]},
                    ],
                }
            ],
        },
        {
            "cycle_id": "c2",
            "timestamp": "2026-03-19T12:00:01+00:00",
            "body_persons": [
                {
                    "body_person_id": "bp-1",
                    "bbox_trajectory": [
                        {"frame": 0, "bbox": [0, 0, 10, 20]},
                        {"frame": 1, "bbox": [1, 1, 11, 21]},
                        {"frame": 2, "bbox": [2, 2, 12, 22]},
                    ],
                }
            ],
        },
    ]
    collected = collect_body_persons_for_flush(cycles)
    assert len(collected) == 1
    assert len(collected[0]["route_points"]) == 3


def test_push_cycle_to_flush_buffer_includes_body_persons():
    fake_redis = MagicMock()
    fake_redis.llen.return_value = 1
    with patch(
        "src.services.instant_detection_flush._redis", return_value=fake_redis
    ):
        length = push_cycle_to_flush_buffer(
            "cam-1",
            cycle_id="cycle-1",
            timestamp="2026-03-19T12:00:00+00:00",
            face_detections=[],
            person_objects=[],
            instant_mvrs=[],
            body_persons=[
                {
                    "body_person_id": "bp-1",
                    "bbox_trajectory": [{"frame": 0, "bbox": [1, 2, 3, 4]}],
                }
            ],
        )
    assert length == 1
    fake_redis.lpush.assert_called_once()
    raw = fake_redis.lpush.call_args[0][1]
    text = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
    assert "body_persons" in text
    assert "bp-1" in text

"""Unit tests for Instant Detection speed / gait aggregation helpers."""

from src.services.instant_speed_aggregation import (
    aggregate_speed_and_gait,
    gait_band_for_speed_mps,
    instant_record_speed_mps,
)


def test_gait_band_for_speed_mps_floors():
    assert gait_band_for_speed_mps(None) is None
    assert gait_band_for_speed_mps(1.0) is None
    assert gait_band_for_speed_mps(1.25) == "walking"
    assert gait_band_for_speed_mps(2.2) == "light_running"
    assert gait_band_for_speed_mps(3.3) == "running"
    assert gait_band_for_speed_mps(5.0) == "fast_running"
    assert gait_band_for_speed_mps(6.0) == "fast_running"


def test_instant_record_speed_mps_reads_nested_stats():
    record = {
        "movement_tracking": {
            "movement_statistics": {"average_speed_mps": 1.8},
        }
    }
    assert instant_record_speed_mps(record) == 1.8
    assert instant_record_speed_mps({"speed_mps": 3.1}) == 3.1


def test_instant_aggregate_speed_and_gait_mean_and_band():
    records = [
        {"speed_mps": 1.5},
        {"speed_mps": 2.5},
        {
            "movement_tracking": {
                "movement_statistics": {"average_speed_mps": 2.0},
            }
        },
        {"speed_mps": None},
    ]
    avg, band = aggregate_speed_and_gait(records)
    assert avg == 2.0
    assert band == "walking"


def test_instant_aggregate_empty_records():
    assert aggregate_speed_and_gait([]) == (None, None)
    assert aggregate_speed_and_gait([{"bbox": [0, 0, 1, 1]}]) == (None, None)


def test_instant_aggregate_light_running_from_mean():
    avg, band = aggregate_speed_and_gait(
        [{"speed_mps": 2.4}, {"speed_mps": 2.6}]
    )
    assert avg == 2.5
    assert band == "light_running"

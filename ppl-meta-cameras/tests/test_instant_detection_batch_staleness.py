"""Pure-function tests for instant-detection Redis batch age guards."""

from datetime import datetime, timedelta, timezone

from src.tasks.instant_detection_tasks import (
    cycle_age_seconds,
    is_cycle_over_max_age,
    parse_cycle_timestamp,
)


def test_parse_cycle_timestamp_zulu():
    parsed = parse_cycle_timestamp("2026-10-19T12:00:00Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_cycle_timestamp_naive_assumes_utc():
    parsed = parse_cycle_timestamp("2026-10-19T12:00:00")
    assert parsed == datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_cycle_timestamp_invalid():
    assert parse_cycle_timestamp("not-a-time") is None
    assert parse_cycle_timestamp(None) is None
    assert parse_cycle_timestamp("") is None


def test_cycle_age_seconds():
    now = datetime(2026, 10, 19, 12, 2, 0, tzinfo=timezone.utc)
    age = cycle_age_seconds("2026-10-19T12:00:00Z", now=now)
    assert age == 120.0


def test_is_cycle_over_max_age_boundary():
    now = datetime(2026, 10, 19, 12, 2, 0, tzinfo=timezone.utc)
    # Exactly 120s is still allowed; older than 120s is dropped.
    assert is_cycle_over_max_age(
        "2026-10-19T12:00:00Z", max_age_seconds=120, now=now
    ) is False
    assert is_cycle_over_max_age(
        "2026-10-19T11:59:59Z", max_age_seconds=120, now=now
    ) is True


def test_is_cycle_over_max_age_for_weeks_old():
    now = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    old = (now - timedelta(days=14)).isoformat().replace("+00:00", "Z")
    assert is_cycle_over_max_age(old, max_age_seconds=120, now=now) is True


def test_unparseable_treated_as_over_age():
    assert is_cycle_over_max_age("bogus", max_age_seconds=120) is True

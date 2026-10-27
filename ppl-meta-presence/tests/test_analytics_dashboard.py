"""Unit tests for session-backed Presence analytics dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from models.presence_models import (
    PresenceDecisionState,
    PresenceGrantType,
    PresenceSession,
    PresenceSessionMode,
    PresenceSessionStatus,
)
from services.presence_service import PresenceService


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    svc = PresenceService.__new__(PresenceService)
    svc.repository = MagicMock()
    svc.repository.save_session = MagicMock()
    svc.repository.save_analytics_event = MagicMock()
    svc.sessions = {}
    svc.attempts = {}
    svc.analytics_events = []
    svc.decision_history = []
    svc._session_timeout_tasks = {}
    svc._resolve_trigger_and_action = MagicMock(return_value=(None, None, "default_policy"))
    svc._record_decision = MagicMock()
    svc._cancel_session_timeout = MagicMock()
    svc._schedule_detection_cleanup = MagicMock()
    svc._session_has_terminal_resolution = PresenceService._session_has_terminal_resolution.__get__(
        svc, PresenceService
    )
    svc._normalize_client_origin = PresenceService._normalize_client_origin
    svc._session_client_origin = PresenceService._session_client_origin.__get__(svc, PresenceService)
    svc._ensure_analytics_event = PresenceService._ensure_analytics_event.__get__(svc, PresenceService)
    svc._fail_session = PresenceService._fail_session.__get__(svc, PresenceService)
    svc._sessions_in_range = PresenceService._sessions_in_range.__get__(svc, PresenceService)
    svc.analytics_summary = PresenceService.analytics_summary.__get__(svc, PresenceService)
    svc.analytics_dashboard = PresenceService.analytics_dashboard.__get__(svc, PresenceService)
    svc._analytics_grant_type_from_sessions = PresenceService._analytics_grant_type_from_sessions.__get__(
        svc, PresenceService
    )
    return svc


def _session(**overrides) -> PresenceSession:
    now = datetime.utcnow()
    base = dict(
        device_uuid="device-1",
        user_uuid="user-1",
        session_mode=PresenceSessionMode.QR_ONLY,
        grant_type=PresenceGrantType.CHECK_IN,
        status=PresenceSessionStatus.COMPLETED,
        decision=PresenceDecisionState.GRANTED,
        expires_at=now + timedelta(minutes=5),
        created_at=now,
        updated_at=now,
        client_origin="authenticator",
        policy_source="default_policy",
    )
    base.update(overrides)
    return PresenceSession(**base)


def test_fail_session_records_analytics_event(service):
    session = _session(
        status=PresenceSessionStatus.CREATED,
        decision=PresenceDecisionState.PENDING,
        client_origin="authenticator",
    )
    service.sessions[session.session_uuid] = session

    service._fail_session(session, "presence_session_expired")

    assert session.decision == PresenceDecisionState.FAILED
    assert len(service.analytics_events) == 1
    event = service.analytics_events[0]
    assert event.outcome == "failed"
    assert event.reason_code == "presence_session_expired"
    assert event.client_origin == "authenticator"


def test_analytics_dashboard_outcomes_failures_origin_and_mode_success(service):
    now = datetime.utcnow()
    granted = _session(
        session_mode=PresenceSessionMode.CAMERA_ONLY,
        grant_type=PresenceGrantType.VERIFIED_PRESENCE,
        client_origin="authenticator",
        policy_source="authenticator_mvr_verify",
        created_at=now,
    )
    expired = _session(
        session_mode=PresenceSessionMode.QR_ONLY,
        status=PresenceSessionStatus.FAILED,
        decision=PresenceDecisionState.FAILED,
        failure_reason_code="presence_session_expired",
        client_origin="authenticator",
        policy_source="default_policy",
        created_at=now,
    )
    camera_grant = _session(
        session_mode=PresenceSessionMode.QR_PLUS_CAMERA,
        grant_type=PresenceGrantType.VERIFIED_PRESENCE,
        client_origin="mobile_camera",
        policy_source="platform_trigger",
        created_at=now,
    )
    for session in (granted, expired, camera_grant):
        service.sessions[session.session_uuid] = session

    dashboard = service.analytics_dashboard()

    assert dashboard["summary"]["total_sessions"] == 3
    assert dashboard["summary"]["granted_sessions"] == 2
    assert dashboard["summary"]["failed_sessions"] == 1
    assert dashboard["summary"]["expired_sessions"] == 1

    outcomes = {item["outcome"]: item["count"] for item in dashboard["outcomes"]}
    assert outcomes["granted"] == 2
    assert outcomes["failed"] == 1

    failures = {item["failure_reason_code"]: item["count"] for item in dashboard["failure_reasons"]}
    assert failures["presence_session_expired"] == 1

    origins = {item["client_origin"]: item["count"] for item in dashboard["client_origins"]}
    assert origins["authenticator"] == 2
    assert origins["mobile_camera"] == 1

    policies = {item["policy_source"]: item["count"] for item in dashboard["policy_sources"]}
    assert policies["authenticator_mvr_verify"] == 1
    assert policies["platform_trigger"] == 1

    by_mode = {item["session_mode"]: item for item in dashboard["mode_success"]}
    assert by_mode["qr_only"]["expired"] == 1
    assert by_mode["qr_only"]["expire_rate"] == 1.0
    assert by_mode["camera_only"]["granted"] == 1
    assert by_mode["camera_only"]["grant_rate"] == 1.0


def test_analytics_dashboard_respects_date_range(service):
    old = _session(created_at=datetime.utcnow() - timedelta(days=10))
    recent = _session(created_at=datetime.utcnow())
    service.sessions[old.session_uuid] = old
    service.sessions[recent.session_uuid] = recent

    dashboard = service.analytics_dashboard(start_date=datetime.utcnow() - timedelta(days=1))
    assert dashboard["summary"]["total_sessions"] == 1

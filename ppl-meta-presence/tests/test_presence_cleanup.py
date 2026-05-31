import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.presence_models import (  # noqa: E402
    BindResourcesRequest,
    PresenceAnalyticsEvent,
    PresenceDecisionState,
    PresenceDetectionAttempt,
    PresenceResource,
    PresenceSession,
    PresenceSessionStatus,
)
from services import presence_service as presence_service_module  # noqa: E402


class _FakeRepository:
    def __init__(self) -> None:
        self.saved_sessions = []
        self.saved_attempts = []
        self.saved_profiles = []
        self.saved_decisions = []
        self.saved_analytics = []

    def load_sessions(self):
        return {}

    def load_attempts(self):
        return {}

    def load_profiles(self):
        return {}

    def load_analytics_events(self):
        return []

    def load_decision_history(self):
        return []

    def load_resources(self, _resource_type: str):
        return {}

    def save_profile(self, profile):
        self.saved_profiles.append(profile)

    def save_session(self, session):
        self.saved_sessions.append(session)

    def save_attempt(self, attempt):
        self.saved_attempts.append(attempt)

    def save_decision_record(self, decision_record):
        self.saved_decisions.append(decision_record)

    def save_analytics_event(self, event):
        self.saved_analytics.append(event)


class _FakePlatformClients:
    def __init__(self, results_payload, status_payload=None) -> None:
        self.results_payload = results_payload
        self.status_payload = status_payload or {"status": {"active_cameras": {}}}
        self.calls = []
        self.triggers = []
        self.actions = []
        self.groups = []
        self.group_members = {}
        self.trigger_lookup = {}

    async def list_cameras(self, token: str):
        self.calls.append(("list_cameras", token))
        return [
            {
                "device_id": "camera-platform-001",
                "name": "Presence Camera",
                "camera_type": "USB",
                "status": "available",
            }
        ]

    async def list_collections(self, token: str):
        self.calls.append(("list_collections", token))
        return [
            {
                "uuid": "collection-platform-001",
                "name": "Presence Collection",
                "camera_device_id": "camera-platform-001",
            }
        ]

    async def get_collection_by_camera_device_id(self, camera_device_id: str, token: str):
        self.calls.append(("get_collection_by_camera", token, camera_device_id))
        if camera_device_id == "camera-platform-001":
            return {
                "uuid": "collection-platform-001",
                "name": "Presence Collection",
                "camera_device_id": camera_device_id,
            }
        return None

    async def get_instant_detection_results(self, camera_id: str):
        self.calls.append(("get_results", camera_id))
        return self.results_payload

    async def get_instant_detection_status(self):
        self.calls.append(("get_status", None))
        return self.status_payload

    async def start_instant_detection(self, camera_id: str):
        self.calls.append(("start", camera_id))
        return {"session_uuid": "restart-session"}

    async def connect_camera(self, camera_id: str):
        self.calls.append(("connect", camera_id))
        return {"status": "connected"}

    async def stop_instant_detection(self, camera_id: str):
        self.calls.append(("stop", camera_id))
        return {"success": True}

    async def disconnect_camera(self, camera_id: str):
        self.calls.append(("disconnect", camera_id))
        return {"status": "disconnected"}

    async def list_triggers(self, token: str):
        self.calls.append(("list_triggers", token))
        return list(self.triggers)

    async def create_trigger(self, token: str, payload):
        self.calls.append(("create_trigger", token, payload))
        trigger = {"uuid": "trigger-uuid", **payload}
        self.triggers.append(trigger)
        self.trigger_lookup["trigger-uuid"] = trigger
        return trigger

    async def get_trigger(self, token: str, trigger_uuid: str):
        self.calls.append(("get_trigger", token, trigger_uuid))
        return dict(self.trigger_lookup.get(trigger_uuid, {}))

    async def list_user_actions(self, token: str):
        self.calls.append(("list_actions", token))
        return list(self.actions)

    async def create_user_action(self, token: str, payload):
        self.calls.append(("create_action", token, payload))
        action = {"uuid": "action-uuid", **payload}
        self.actions.append(action)
        return action

    async def list_individual_groups(self, token: str):
        self.calls.append(("list_groups", token))
        return list(self.groups)

    async def create_individual_group(self, token: str, payload):
        self.calls.append(("create_group", token, payload))
        group = {"id": "group-001", **payload}
        self.groups.append(group)
        self.group_members[group["id"]] = []
        return {"group": group, "members_preview": []}

    async def get_individual_group_members(self, token: str, group_id: str):
        self.calls.append(("list_members", token, group_id))
        return list(self.group_members.get(group_id, []))

    async def add_individual_group_members(self, token: str, group_id: str, payload):
        self.calls.append(("add_members", token, group_id, payload))
        members = self.group_members.setdefault(group_id, [])
        for individual_id in payload.get("individual_ids", []):
            members.append({"id": individual_id})
        return {"group": {"id": group_id}, "added_count": len(payload.get("individual_ids", [])), "skipped_count": 0}

    async def create_audit_log(self, token: str, payload):
        self.calls.append(("create_audit_log", token, payload))
        return {"log_uuid": "audit-log-001"}


def _build_service(monkeypatch: pytest.MonkeyPatch, platform_clients: _FakePlatformClients):
    monkeypatch.setattr(presence_service_module, "PresenceRepository", _FakeRepository)
    monkeypatch.setattr(presence_service_module.config, "DETECTION_BACKEND_MODE", "auto", raising=False)
    return presence_service_module.PresenceService(platform_clients=platform_clients)


def _build_session(camera_id: str) -> PresenceSession:
    return PresenceSession(
        device_uuid="presence-validation-device",
        user_uuid="7",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        resolved_camera_uuid=camera_id,
        decision=PresenceDecisionState.PENDING,
        status="qr_resolved",
    )


def _build_attempt(session_uuid: str) -> PresenceDetectionAttempt:
    return PresenceDetectionAttempt(
        session_uuid=session_uuid,
        attempt_index=1,
        capture_phase="initial",
    )


def test_qr_current_returns_existing_session_qr_without_creating_new_token(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    session = PresenceSession(
        device_uuid="presence-validation-device",
        user_uuid="7",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    service.sessions[session.session_uuid] = session
    service.qr_tokens[session.qr_token] = session.session_uuid

    current_qr = service.qr_current("local-installation", "presence-validation-device")

    assert current_qr["found"] is True
    assert current_qr["qr_token"] == session.qr_token
    assert current_qr["session_uuid"] == session.session_uuid
    assert current_qr["payload"]["session_uuid"] == session.session_uuid
    assert current_qr["qr_status"] == session.qr_status


def test_qr_current_returns_not_found_without_minting_token(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)

    current_qr = service.qr_current("local-installation", "missing-device")

    assert current_qr["found"] is False
    assert current_qr["qr_token"] is None
    assert current_qr["session_uuid"] is None
    assert service.qr_tokens == {}


def test_bind_resources_uses_reserved_platform_resource_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    session = PresenceSession(
        device_uuid="presence-validation-device",
        user_uuid="7",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    camera_resource = PresenceResource(
        resource_type="camera",
        installation_uuid="local-installation",
        platform_resource_uuid="camera-platform-001",
    )
    collection_resource = PresenceResource(
        resource_type="collection",
        installation_uuid="local-installation",
        platform_resource_uuid="collection-platform-001",
    )
    service.sessions[session.session_uuid] = session
    service.cameras[camera_resource.resource_uuid] = camera_resource
    service.collections[collection_resource.resource_uuid] = collection_resource

    bound_session = service.bind_resources(
        session.session_uuid,
        BindResourcesRequest(
            camera_uuid=camera_resource.resource_uuid,
            collection_uuid=collection_resource.resource_uuid,
        ),
    )

    assert bound_session.resolved_camera_uuid == "camera-platform-001"
    assert bound_session.resolved_collection_uuid == "collection-platform-001"


def test_bind_resources_rejects_unknown_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    session = PresenceSession(
        device_uuid="presence-validation-device",
        user_uuid="7",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    service.sessions[session.session_uuid] = session

    with pytest.raises(ValueError, match="not reserved for presence"):
        service.bind_resources(
            session.session_uuid,
            BindResourcesRequest(
                camera_uuid="unknown-camera",
                collection_uuid="unknown-collection",
            ),
        )


@pytest.mark.asyncio
async def test_reserve_camera_rejects_unsupported_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)

    with pytest.raises(ValueError, match="not supported"):
        await service.reserve_camera(
            presence_service_module.ReserveResourceRequest(
                installation_uuid="local-installation",
                resource_uuid="camera-platform-001",
                mode="create",
            ),
            {"token": "user-token"},
        )


@pytest.mark.asyncio
async def test_list_cameras_exposes_reservation_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    camera_resource = PresenceResource(
        resource_type="camera",
        installation_uuid="local-installation",
        platform_resource_uuid="camera-platform-001",
    )
    collection_resource = PresenceResource(
        resource_type="collection",
        installation_uuid="local-installation",
        platform_resource_uuid="collection-platform-001",
        metadata={"camera_device_id": "camera-platform-001"},
    )
    service.cameras[camera_resource.resource_uuid] = camera_resource
    service.collections[collection_resource.resource_uuid] = collection_resource

    items = await service.list_cameras({"token": "user-token"})

    assert items[0]["reserved_for_presence"] is True
    assert items[0]["reserved_resource_uuid"] == camera_resource.resource_uuid
    assert items[0]["reserved_installation_uuid"] == "local-installation"
    assert items[0]["linked_collection_uuid"] == "collection-platform-001"


@pytest.mark.asyncio
async def test_action_plan_exposes_trigger_action_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    current_user = {"sub": "7", "token": "user-token", "username": "presence-user"}
    group = service.ensure_group(
        presence_service_module.CreatePresenceGroupRequest(
            installation_uuid="local-installation",
            user_uuid="7",
            display_name="Presence Group 7",
        ),
        current_user,
    )
    profile = service.profiles[group.group_uuid]
    profile.metadata = {
        "presence_individual_group_id": "group-001",
        "presence_action_uuid": "action-uuid",
        "presence_trigger_uuid": "trigger-uuid",
    }
    platform_clients.trigger_lookup["trigger-uuid"] = {
        "uuid": "trigger-uuid",
        "action_uuid": "action-uuid",
        "action_uuids": ["action-uuid", "email-action-uuid"],
        "action_names": ["Presence Action 7", "email notification"],
        "last_fired_at": "2026-05-31T10:41:41Z",
        "last_matched_at": "2026-05-31T10:41:37Z",
        "ppl_match_group_id": "group-001",
    }
    session = PresenceSession(
        device_uuid="presence-validation-device",
        user_uuid="7",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    service.sessions[session.session_uuid] = session

    action_plan = service.get_action_plan(session.session_uuid)

    assert action_plan.trigger_observation is not None
    assert action_plan.trigger_observation.trigger_uuid == "trigger-uuid"
    assert action_plan.trigger_observation.configured_action_uuids == ["action-uuid", "email-action-uuid"]
    assert action_plan.trigger_observation.configured_action_names == ["Presence Action 7", "email notification"]


def test_phase4_analytics_breakdowns_cover_installation_collection_and_action_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    service.analytics_events = [
        PresenceAnalyticsEvent(
            session_uuid="session-1",
            installation_uuid="inst-a",
            user_uuid="7",
            device_uuid="device-a",
            outcome="granted",
            reason_code="presence_ppl_match",
            resolved_collection_uuid="collection-1",
            action_type="group_open_door",
            action_execution_status="executed",
        ),
        PresenceAnalyticsEvent(
            session_uuid="session-2",
            installation_uuid="inst-a",
            user_uuid="8",
            device_uuid="device-b",
            outcome="failed",
            reason_code="presence_timeout",
            resolved_collection_uuid=None,
            action_type="group_open_door",
            action_execution_status="failed",
        ),
        PresenceAnalyticsEvent(
            session_uuid="session-3",
            installation_uuid="inst-b",
            user_uuid="9",
            device_uuid="device-c",
            outcome="granted",
            reason_code="presence_ppl_match",
            resolved_collection_uuid="collection-1",
            action_type=None,
            action_execution_status=None,
        ),
    ]

    by_installation = service.analytics_by_installation()
    by_collection = service.analytics_by_reserved_collection()
    action_outcomes = service.analytics_action_outcomes()
    repair_payload = service.repair_analytics_metadata()

    assert {item["installation_uuid"]: item["event_count"] for item in by_installation} == {
        "inst-a": 2,
        "inst-b": 1,
    }
    assert {item["resolved_collection_uuid"]: item["event_count"] for item in by_collection} == {
        "collection-1": 2,
        "unbound": 1,
    }
    assert {
        (item["action_type"], item["action_execution_status"]): item["event_count"]
        for item in action_outcomes
    } == {
        ("group_open_door", "executed"): 1,
        ("group_open_door", "failed"): 1,
        ("unknown", "unknown"): 1,
    }
    assert repair_payload["installation_breakdown"] == by_installation
    assert repair_payload["reserved_collection_breakdown"] == by_collection
    assert repair_payload["action_outcome_breakdown"] == action_outcomes


@pytest.mark.asyncio
async def test_advance_live_detection_cleans_up_camera_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    camera_id = "camera-success"
    platform_clients = _FakePlatformClients(
        {
            "success": True,
            "camera_id": camera_id,
            "match": {"detected": True, "confidence": 0.99},
        }
    )
    service = _build_service(monkeypatch, platform_clients)
    session = _build_session(camera_id)
    attempt = _build_attempt(session.session_uuid)
    service.sessions[session.session_uuid] = session
    service.attempts[session.session_uuid] = [attempt]
    advance_live_detection = getattr(service, "_advance_live_detection")

    await advance_live_detection(session)

    assert session.detection_status == "completed"
    assert attempt.instant_detection_status == "completed"
    assert ("stop", camera_id) not in platform_clients.calls
    assert ("disconnect", camera_id) not in platform_clients.calls


@pytest.mark.asyncio
async def test_advance_live_detection_does_not_complete_on_empty_success_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    camera_id = "camera-empty-success"
    platform_clients = _FakePlatformClients(
        {
            "success": True,
            "camera_id": camera_id,
            "people_count": 0,
            "people_detected": 0,
            "person_objects": [],
            "match": {"detected": False, "confidence": 0.0},
        },
        {"status": {"active_cameras": {camera_id: {"running": False}}}},
    )
    service = _build_service(monkeypatch, platform_clients)
    session = _build_session(camera_id)
    attempt = _build_attempt(session.session_uuid)
    service.sessions[session.session_uuid] = session
    service.attempts[session.session_uuid] = [attempt]
    advance_live_detection = getattr(service, "_advance_live_detection")

    await advance_live_detection(session)

    assert session.detection_status == "started"
    assert attempt.instant_detection_status == "restarted"
    assert ("connect", camera_id) in platform_clients.calls
    assert ("start", camera_id) in platform_clients.calls


@pytest.mark.asyncio
async def test_advance_live_detection_cleans_up_camera_after_retry_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    camera_id = "camera-timeout"
    platform_clients = _FakePlatformClients(
        {"success": False, "detail": "No instant detection results yet"},
        {"status": {"active_cameras": {camera_id: {"running": False}}}},
    )
    service = _build_service(monkeypatch, platform_clients)
    session = _build_session(camera_id)
    attempt = _build_attempt(session.session_uuid)
    attempt.instant_detection_result_payload = {"retry_count": 3}
    service.sessions[session.session_uuid] = session
    service.attempts[session.session_uuid] = [attempt]
    advance_live_detection = getattr(service, "_advance_live_detection")

    await advance_live_detection(session)

    assert session.detection_status == "results_timeout"
    assert session.decision == PresenceDecisionState.FAILED
    assert attempt.instant_detection_status == "results_timeout"
    assert ("stop", camera_id) in platform_clients.calls
    assert ("disconnect", camera_id) in platform_clients.calls


@pytest.mark.asyncio
async def test_presence_assets_are_auto_provisioned(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    current_user = {"sub": "7", "token": "user-token", "username": "presence-user"}
    group = service.ensure_group(
        presence_service_module.CreatePresenceGroupRequest(
            installation_uuid="local-installation",
            user_uuid="7",
            display_name="Presence Group 7",
        ),
        current_user,
    )
    session = _build_session("camera-provision")

    ensure_assets = getattr(service, "_ensure_presence_automation_assets")
    await ensure_assets(session, current_user)

    profile = service.profiles[group.group_uuid]
    assert profile.metadata["presence_individual_group_id"] == "group-001"
    assert profile.metadata["presence_action_uuid"] == "action-uuid"
    assert profile.metadata["presence_trigger_uuid"] == "trigger-uuid"
    assert profile.metadata["presence_trigger_threshold"] == 0.6
    assert session.external_assets is not None
    assert session.external_assets.individual_group_id == "group-001"
    assert session.external_assets.action_uuid == "action-uuid"
    assert session.external_assets.trigger_uuid == "trigger-uuid"
    assert any(call[0] == "create_group" for call in platform_clients.calls)
    assert any(call[0] == "create_action" for call in platform_clients.calls)
    assert any(call[0] == "create_trigger" for call in platform_clients.calls)


@pytest.mark.asyncio
async def test_first_detection_seeds_external_presence_group(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    current_user = {"sub": "7", "token": "user-token", "username": "presence-user"}
    group = service.ensure_group(
        presence_service_module.CreatePresenceGroupRequest(
            installation_uuid="local-installation",
            user_uuid="7",
            display_name="Presence Group 7",
        ),
        current_user,
    )
    profile = service.profiles[group.group_uuid]
    profile.metadata = {"presence_individual_group_id": "group-001"}
    session = _build_session("camera-seed")
    attempt = _build_attempt(session.session_uuid)
    attempt.instant_detection_result_payload = {
        "identity_ids": ["mvr-123"],
        "raw_payload": {"person_objects": [{"mvr_person_uuid": "mvr-123"}]},
    }

    ensure_seed_member = getattr(service, "_ensure_presence_group_seed_member")
    await ensure_seed_member(session, attempt, current_user)

    assert platform_clients.group_members["group-001"] == [{"id": "mvr-123"}]
    assert profile.metadata["presence_seed_member_id"] == "mvr-123"
    assert "presence_seeded_at" in profile.metadata


@pytest.mark.asyncio
async def test_get_result_waits_for_trigger_backed_match(monkeypatch: pytest.MonkeyPatch) -> None:
    camera_id = "camera-trigger-pending"
    platform_clients = _FakePlatformClients(
        {
            "success": True,
            "camera_id": camera_id,
            "person_objects": [{"mvr_person_uuid": "mvr-123"}],
            "match": {"detected": True, "confidence": 0.99},
        }
    )
    service = _build_service(monkeypatch, platform_clients)
    current_user = {"sub": "7", "token": "user-token", "username": "presence-user"}
    group = service.ensure_group(
        presence_service_module.CreatePresenceGroupRequest(
            installation_uuid="local-installation",
            user_uuid="7",
            display_name="Presence Group 7",
        ),
        current_user,
    )
    profile = service.profiles[group.group_uuid]
    profile.metadata = {
        "presence_individual_group_id": "group-001",
        "presence_trigger_uuid": "trigger-uuid",
    }
    platform_clients.trigger_lookup["trigger-uuid"] = {
        "uuid": "trigger-uuid",
        "last_match_info": None,
        "last_matched_at": None,
    }
    session = _build_session(camera_id)
    service.sessions[session.session_uuid] = session
    service.attempts[session.session_uuid] = [_build_attempt(session.session_uuid)]

    result = await service.get_result(session.session_uuid, current_user)

    assert result.decision == PresenceDecisionState.PENDING
    assert result.status == PresenceSessionStatus.QR_RESOLVED
    assert service.sessions[session.session_uuid].detection_status == "confirmation_started"
    confirmation_attempts = [
        attempt for attempt in service.attempts[session.session_uuid] if attempt.capture_phase == "confirmation"
    ]
    assert len(confirmation_attempts) == 1
    assert confirmation_attempts[0].instant_detection_status == "started"
    assert ("connect", camera_id) in platform_clients.calls
    assert ("start", camera_id) in platform_clients.calls
    assert ("stop", camera_id) not in platform_clients.calls
    assert ("disconnect", camera_id) not in platform_clients.calls


@pytest.mark.asyncio
async def test_confirmation_detection_is_started_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    platform_clients = _FakePlatformClients({"success": False})
    service = _build_service(monkeypatch, platform_clients)
    session = _build_session("camera-confirmation")
    service.sessions[session.session_uuid] = session
    service.attempts[session.session_uuid] = [_build_attempt(session.session_uuid)]

    start_confirmation = getattr(service, "_start_confirmation_detection")

    first_started = await start_confirmation(session)
    second_started = await start_confirmation(session)

    assert first_started is True
    assert second_started is False
    confirmation_attempts = [
        attempt for attempt in service.attempts[session.session_uuid] if attempt.capture_phase == "confirmation"
    ]
    assert len(confirmation_attempts) == 1


@pytest.mark.asyncio
async def test_get_result_grants_after_fresh_trigger_backed_match(monkeypatch: pytest.MonkeyPatch) -> None:
    camera_id = "camera-trigger-match"
    platform_clients = _FakePlatformClients(
        {
            "success": True,
            "camera_id": camera_id,
            "person_objects": [{"mvr_person_uuid": "mvr-123"}],
            "match": {"detected": True, "confidence": 0.99},
        }
    )
    service = _build_service(monkeypatch, platform_clients)
    current_user = {"sub": "7", "token": "user-token", "username": "presence-user"}
    group = service.ensure_group(
        presence_service_module.CreatePresenceGroupRequest(
            installation_uuid="local-installation",
            user_uuid="7",
            display_name="Presence Group 7",
        ),
        current_user,
    )
    session = _build_session(camera_id)
    session.created_at = datetime.utcnow() - timedelta(seconds=2)
    profile = service.profiles[group.group_uuid]
    profile.metadata = {
        "presence_individual_group_id": "group-001",
        "presence_trigger_uuid": "trigger-uuid",
    }
    platform_clients.group_members["group-001"] = [{"id": "mvr-seeded"}]
    platform_clients.trigger_lookup["trigger-uuid"] = {
        "uuid": "trigger-uuid",
        "last_matched_at": datetime.utcnow().isoformat(),
        "last_match_info": {
            "mode": "ppl_match",
            "best_match": {
                "source_mvr_uuid": "mvr-123",
                "matched_member_uuid": "mvr-seeded",
                "similarity_score": 0.91,
            },
        },
    }
    service.sessions[session.session_uuid] = session
    service.attempts[session.session_uuid] = [_build_attempt(session.session_uuid)]

    result = await service.get_result(session.session_uuid, current_user)

    assert result.decision == PresenceDecisionState.GRANTED
    assert result.reason_code == "presence_ppl_match"
    assert result.external_assets is not None
    assert result.external_assets.individual_group_id == "group-001"
    assert result.external_assets.trigger_uuid == "trigger-uuid"
    assert service.sessions[session.session_uuid].policy_source == "platform_trigger"
    assert ("stop", camera_id) in platform_clients.calls
    assert ("disconnect", camera_id) in platform_clients.calls
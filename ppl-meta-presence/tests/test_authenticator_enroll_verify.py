"""Unit tests for authenticator enroll/verify (no cameras registration)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.presence_models import (
    CreatePresenceSessionRequest,
    PresenceDecisionState,
    PresencePeopleProfile,
    PresencePeopleProfileLink,
    PresenceSessionMode,
    PresenceSessionStatus,
)
from services.presence_service import PresenceService


def _user(**overrides):
    base = {
        "guid": "user-guid-1",
        "email": "member@example.com",
        "token": "test-jwt",
        "given_name": "Test",
        "family_name": "Member",
    }
    base.update(overrides)
    return base


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'presence_auth.db'}")
    # Avoid real DB if repository needs postgres — use in-memory stubs.
    svc = PresenceService.__new__(PresenceService)
    svc.repository = MagicMock()
    svc.repository.save_session = MagicMock()
    svc.repository.save_people_profile = MagicMock()
    svc.repository.save_people_profile_link = MagicMock()
    svc.repository.save_analytics_event = MagicMock()
    svc.repository.save_profile = MagicMock()
    svc.sessions = {}
    svc.attempts = {}
    svc.profiles = {}
    svc.analytics_events = []
    svc.decision_history = []
    svc._session_timeout_tasks = {}
    svc.qr_tokens = {}
    svc.cameras = {}
    svc.collections = {}
    svc.people_profiles = {}
    svc.people_profile_links = []
    svc._users_by_email_cache = {}
    svc.platform_clients = MagicMock()
    svc.platform_clients.identify_face = AsyncMock()
    svc.platform_clients.add_individual_group_members = AsyncMock(return_value={})
    svc.platform_clients.list_triggers = AsyncMock(return_value=[])
    svc.platform_clients.list_user_actions = AsyncMock(return_value=[])
    svc.installation_profile = MagicMock()
    svc.installation_profile.installation_uuid = "local-installation"
    svc.installation_profile.metadata = {}
    svc.installation_profile.user_uuid = None
    svc.people_user_association = MagicMock()

    def _ensure(user, reason="user_create", installation_uuid="local-installation"):
        ppp = PresencePeopleProfile(
            name=user.get("email") or "User",
            email=user.get("email"),
            linked_user_uuid=user.get("guid"),
            installation_uuid=installation_uuid,
        )
        svc.people_profiles[ppp.ppp_uuid] = ppp
        return ppp

    svc.people_user_association.ensure_profile_for_user = _ensure
    svc.ensure_people_profile_for_user = lambda user, reason="user_create", installation_uuid="local-installation": _ensure(
        user, reason=reason, installation_uuid=installation_uuid
    )
    svc._persist_people_profile = lambda profile: svc.people_profiles.__setitem__(profile.ppp_uuid, profile)
    svc._active_presence_individual_group_id = lambda: "group-1"
    svc._active_presence_individual_group_name = lambda: "Presence Group"
    svc._get_or_create_user_profile = MagicMock(
        return_value=MagicMock(user_uuid="user-guid-1", metadata={})
    )
    svc._ensure_default_resources = AsyncMock()
    svc._ensure_presence_automation_assets = AsyncMock()
    svc._sync_session_external_assets = MagicMock()
    svc._schedule_session_timeout = MagicMock()
    svc._current_session_settings = MagicMock(
        return_value=MagicMock(session_timeout_seconds=300, max_unsuccessful_attempts=3)
    )
    svc._get_default_camera_id = MagicMock(return_value=None)
    svc._get_default_collection_id = MagicMock(return_value=None)
    svc._assurance_level_for_mode = PresenceService._assurance_level_for_mode.__get__(svc, PresenceService)
    svc._grant_type_for_mode = PresenceService._grant_type_for_mode.__get__(svc, PresenceService)
    svc._cancel_session_timeout = MagicMock()
    svc._session_has_terminal_resolution = lambda session: session.decision in {
        PresenceDecisionState.GRANTED,
        PresenceDecisionState.DENIED,
        PresenceDecisionState.FAILED,
    }
    svc._resolve_matched_group_uuid = lambda session: session.matched_group_uuid
    svc._resolve_trigger_and_action = lambda session: ("presence_match", "presence_grant", "authenticator_mvr_verify")
    svc._execute_action = AsyncMock(return_value=("not_applicable", None))
    svc._record_decision = MagicMock()
    svc._apply_matched_person_fields = PresenceService._apply_matched_person_fields.__get__(svc, PresenceService)
    svc._apply_ppp_to_session = PresenceService._apply_ppp_to_session.__get__(svc, PresenceService)
    svc._ppp_for_member = PresenceService._ppp_for_member.__get__(svc, PresenceService)
    svc.link_member = PresenceService.link_member.__get__(svc, PresenceService)
    svc._refresh_linked_member_counts = MagicMock()
    svc._grant_presence_match = PresenceService._grant_presence_match.__get__(svc, PresenceService)
    svc.get_authenticator_enrollment = PresenceService.get_authenticator_enrollment.__get__(svc, PresenceService)
    svc._ppp_for_current_user = PresenceService._ppp_for_current_user.__get__(svc, PresenceService)
    svc._linked_mvr_ids_for_ppp = PresenceService._linked_mvr_ids_for_ppp.__get__(svc, PresenceService)
    svc._authenticator_candidate_mvr_ids = PresenceService._authenticator_candidate_mvr_ids.__get__(
        svc, PresenceService
    )
    svc.enroll_authenticator_face = PresenceService.enroll_authenticator_face.__get__(svc, PresenceService)
    svc.verify_authenticator_face = PresenceService.verify_authenticator_face.__get__(svc, PresenceService)
    svc.create_session = PresenceService.create_session.__get__(svc, PresenceService)
    return svc


def test_enroll_stores_mvr_on_ppp(service):
    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": False,
        "mvr_people_uuid": "mvr-abc",
        "similarity_score": 0.0,
        "created_new": True,
    }

    result = asyncio.get_event_loop().run_until_complete(
        service.enroll_authenticator_face(_user(), b"fake-jpeg")
    )
    assert result.mvr_people_uuid == "mvr-abc"
    assert result.created_new is True
    enrollment = service.get_authenticator_enrollment(_user())
    assert enrollment.enrolled is True
    assert enrollment.mvr_people_uuid == "mvr-abc"
    # force_create path used when no PPP-linked candidates exist
    kwargs = service.platform_clients.identify_face.await_args.kwargs
    assert kwargs.get("force_create") is True


def test_enroll_reuses_ppp_linked_mvr(service):
    ppp = PresencePeopleProfile(
        name="member@example.com",
        email="member@example.com",
        linked_user_uuid="user-guid-1",
        installation_uuid="local-installation",
    )
    service.people_profiles[ppp.ppp_uuid] = ppp
    service.people_profile_links.append(
        PresencePeopleProfileLink(
            ppp_uuid=ppp.ppp_uuid,
            group_id="group-1",
            individual_id="mvr-linked",
            linked_by="console",
        )
    )
    service.ensure_people_profile_for_user = lambda user, reason="user_create", installation_uuid="local-installation": ppp

    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": True,
        "mvr_people_uuid": "mvr-linked",
        "similarity_score": 0.88,
        "created_new": False,
    }
    result = asyncio.get_event_loop().run_until_complete(
        service.enroll_authenticator_face(_user(), b"fake-jpeg")
    )
    assert result.mvr_people_uuid == "mvr-linked"
    assert result.created_new is False
    kwargs = service.platform_clients.identify_face.await_args.kwargs
    assert kwargs.get("force_create") is False
    assert "mvr-linked" in (kwargs.get("target_mvr_people_uuids") or [])


def test_verify_grants_camera_only_session(service):
    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": False,
        "mvr_people_uuid": "mvr-abc",
        "similarity_score": 0.0,
        "created_new": True,
    }
    asyncio.get_event_loop().run_until_complete(
        service.enroll_authenticator_face(_user(), b"enroll")
    )

    session = asyncio.get_event_loop().run_until_complete(
        service.create_session(
            CreatePresenceSessionRequest(
                session_mode=PresenceSessionMode.CAMERA_ONLY,
                device_uuid="soft-device-1",
                device_name="Authenticator",
                device_platform="android",
                app_version="ppl-meta-authenticator/1.0.0",
                client_origin="authenticator",
            ),
            _user(),
        )
    )
    assert session.detection_status == "awaiting_authenticator_verify"
    assert session.resolved_camera_uuid is None

    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": True,
        "mvr_people_uuid": "mvr-abc",
        "similarity_score": 0.91,
        "created_new": False,
    }
    verify = asyncio.get_event_loop().run_until_complete(
        service.verify_authenticator_face(
            _user(),
            b"live",
            session_uuid=session.session_uuid,
        )
    )
    assert verify.verified is True
    assert session.decision == PresenceDecisionState.GRANTED
    assert session.status == PresenceSessionStatus.COMPLETED


def test_verify_rejects_wrong_mvr(service):
    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": False,
        "mvr_people_uuid": "mvr-abc",
        "similarity_score": 0.0,
        "created_new": True,
    }
    asyncio.get_event_loop().run_until_complete(
        service.enroll_authenticator_face(_user(), b"enroll")
    )
    session = asyncio.get_event_loop().run_until_complete(
        service.create_session(
            CreatePresenceSessionRequest(
                session_mode=PresenceSessionMode.CAMERA_ONLY,
                device_uuid="soft-device-1",
                device_name="Authenticator",
                device_platform="android",
                app_version="ppl-meta-authenticator/1.0.0",
                client_origin="authenticator",
            ),
            _user(),
        )
    )
    # Gallery-best "other" person must not grant — only candidate set counts.
    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": True,
        "mvr_people_uuid": "mvr-other",
        "similarity_score": 0.95,
        "created_new": False,
    }
    verify = asyncio.get_event_loop().run_until_complete(
        service.verify_authenticator_face(
            _user(),
            b"live",
            session_uuid=session.session_uuid,
        )
    )
    assert verify.verified is False
    assert session.decision == PresenceDecisionState.DENIED


def test_verify_matches_secondary_linked_mvr(service):
    """Live face may match a console-linked MVR even if binding is another candidate."""
    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": False,
        "mvr_people_uuid": "mvr-bound",
        "similarity_score": 1.0,
        "created_new": True,
    }
    asyncio.get_event_loop().run_until_complete(
        service.enroll_authenticator_face(_user(), b"enroll")
    )
    ppp = next(iter(service.people_profiles.values()))
    service.people_profile_links.append(
        PresencePeopleProfileLink(
            ppp_uuid=ppp.ppp_uuid,
            group_id="group-1",
            individual_id="mvr-alt",
            linked_by="console",
        )
    )
    session = asyncio.get_event_loop().run_until_complete(
        service.create_session(
            CreatePresenceSessionRequest(
                session_mode=PresenceSessionMode.CAMERA_ONLY,
                device_uuid="soft-device-1",
                device_name="Authenticator",
                device_platform="android",
                app_version="ppl-meta-authenticator/1.0.0",
                client_origin="authenticator",
            ),
            _user(),
        )
    )
    service.platform_clients.identify_face.return_value = {
        "success": True,
        "matched": True,
        "mvr_people_uuid": "mvr-alt",
        "similarity_score": 0.93,
        "created_new": False,
    }
    verify = asyncio.get_event_loop().run_until_complete(
        service.verify_authenticator_face(
            _user(),
            b"live",
            session_uuid=session.session_uuid,
        )
    )
    assert verify.verified is True
    assert verify.mvr_people_uuid == "mvr-alt"
    assert session.matched_member_uuid == "mvr-alt"
    assert session.decision == PresenceDecisionState.GRANTED


def test_enrollment_true_when_only_ppp_links(service):
    ppp = PresencePeopleProfile(
        name="member@example.com",
        email="member@example.com",
        linked_user_uuid="user-guid-1",
        installation_uuid="local-installation",
    )
    service.people_profiles[ppp.ppp_uuid] = ppp
    service.people_profile_links.append(
        PresencePeopleProfileLink(
            ppp_uuid=ppp.ppp_uuid,
            group_id="group-1",
            individual_id="mvr-console",
            linked_by="console",
        )
    )
    enrollment = service.get_authenticator_enrollment(_user())
    assert enrollment.enrolled is True
    assert enrollment.mvr_people_uuid == "mvr-console"

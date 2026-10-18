"""Unit tests for HubSpot CRM mapping, config masking, and grant notify gates."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models.presence_models import (  # noqa: E402
    HubSpotCrmConfig,
    PresenceAssuranceLevel,
    PresenceDecisionState,
    PresenceExternalAssets,
    PresenceGrantType,
    PresencePeopleProfile,
    PresenceSession,
    PresenceSessionMode,
    PresenceSessionStatus,
    UpdateHubSpotCrmConfigRequest,
)
from services.hubspot_crm import grant_note_body, map_hubspot_contact  # noqa: E402
from services.presence_service import PresenceService  # noqa: E402


def test_map_hubspot_contact_basic():
    contact = map_hubspot_contact(
        {
            "id": "123",
            "properties": {
                "firstname": "Ada",
                "lastname": "Lovelace",
                "email": "ada@example.com",
                "phone": "+15551212",
            },
        }
    )
    assert contact is not None
    assert contact.contact_id == "123"
    assert contact.display_name == "Ada Lovelace"
    assert contact.email == "ada@example.com"
    assert contact.phone == "+15551212"


def test_map_hubspot_contact_falls_back_to_email_name():
    contact = map_hubspot_contact(
        {"id": "9", "properties": {"email": "solo@example.com", "firstname": "", "lastname": ""}}
    )
    assert contact is not None
    assert contact.display_name == "solo@example.com"


def test_map_hubspot_contact_requires_id():
    assert map_hubspot_contact({"properties": {"email": "a@b.c"}}) is None


def test_grant_note_body_includes_session_uuid():
    body = grant_note_body(
        session_uuid="sess-1",
        grant_type="verified_presence",
        assurance_level="high",
        person_name="Nick",
        occurred_at=datetime(2026, 1, 2, 3, 4, 5),
    )
    assert "session_uuid=sess-1" in body
    assert "verified_presence" in body
    assert "Nick" in body


def test_hubspot_config_get_masks_token():
    service = PresenceService.__new__(PresenceService)
    service.installation_profile = SimpleNamespace(
        installation_uuid="local-installation",
        presence_profile_uuid="prof-1",
        metadata={
            "crm_hubspot": {
                "enabled": True,
                "access_token": "secret-token",
                "hub_id": "99",
                "list_id": None,
                "post_grants": True,
                "grant_types": ["check_in"],
                "last_sync_at": None,
                "last_sync_status": None,
                "last_error": None,
            }
        },
        updated_at=datetime.utcnow(),
    )
    service.profiles = {}
    service.repository = SimpleNamespace(save_profile=lambda *_a, **_k: None)

    public = PresenceService.get_hubspot_crm_config(service)
    assert public.enabled is True
    assert public.token_configured is True
    assert public.hub_id == "99"
    dumped = public.model_dump()
    assert "access_token" not in dumped
    assert "secret-token" not in str(dumped)


def test_hubspot_config_update_preserves_token_when_blank():
    service = PresenceService.__new__(PresenceService)
    saved = {}

    def save_profile(profile):
        saved["cfg"] = dict(profile.metadata.get("crm_hubspot") or {})

    service.installation_profile = SimpleNamespace(
        installation_uuid="local-installation",
        presence_profile_uuid="prof-1",
        metadata={
            "crm_hubspot": HubSpotCrmConfig(
                enabled=True,
                access_token="keep-me",
                hub_id="1",
            ).model_dump(mode="json")
        },
        updated_at=datetime.utcnow(),
    )
    service.profiles = {}
    service.repository = SimpleNamespace(save_profile=save_profile)

    PresenceService.update_hubspot_crm_config(
        service,
        UpdateHubSpotCrmConfigRequest(
            enabled=True,
            access_token="   ",
            hub_id="42",
            post_grants=False,
            grant_types=["presence_match"],
        ),
    )
    assert saved["cfg"]["access_token"] == "keep-me"
    assert saved["cfg"]["hub_id"] == "42"
    assert saved["cfg"]["post_grants"] is False


def test_upsert_ppp_from_hubspot_creates_and_updates():
    service = PresenceService.__new__(PresenceService)
    service.installation_profile = SimpleNamespace(installation_uuid="local-installation")
    service.people_profiles = {}
    service._users_by_email_cache = {}
    persisted = []

    def persist(profile):
        service.people_profiles[profile.ppp_uuid] = profile
        persisted.append(profile.ppp_uuid)

    service._persist_people_profile = persist
    service._schedule_people_user_sync = lambda *_a, **_k: None
    service._emit_people_association_log = lambda **_k: None
    service.people_user_association = SimpleNamespace(find_active_by_email=lambda _email: None)

    contact = SimpleNamespace(
        contact_id="hs-1",
        display_name="Ada Lovelace",
        email="ada@example.com",
        phone="1",
    )
    assert PresenceService._upsert_ppp_from_hubspot_contact(service, contact) == "created"
    assert len(service.people_profiles) == 1
    profile = next(iter(service.people_profiles.values()))
    assert profile.external_ref == "hs-1"

    contact.phone = "2"
    contact.display_name = "Ada L"
    assert PresenceService._upsert_ppp_from_hubspot_contact(service, contact) == "updated"
    assert profile.phone == "2"
    assert PresenceService._upsert_ppp_from_hubspot_contact(service, contact) == "skipped"


def test_notify_hubspot_grant_skips_when_disabled():
    service = PresenceService.__new__(PresenceService)
    service.installation_profile = SimpleNamespace(
        metadata={"crm_hubspot": HubSpotCrmConfig(enabled=False, access_token="t").model_dump(mode="json")}
    )
    service.people_profiles = {}
    service.people_profile_links = []
    service.repository = SimpleNamespace(save_session=lambda *_a, **_k: None)
    client_called = {"n": 0}

    def hubspot_client():
        client_called["n"] += 1
        return object()

    service._hubspot_client = hubspot_client

    session = PresenceSession(
        session_mode=PresenceSessionMode.CAMERA_ONLY,
        assurance_level=PresenceAssuranceLevel.MEDIUM,
        grant_type=PresenceGrantType.PRESENCE_MATCH,
        status=PresenceSessionStatus.COMPLETED,
        decision=PresenceDecisionState.GRANTED,
        device_uuid="d1",
        user_uuid="u1",
        installation_uuid="local-installation",
        expires_at=datetime.utcnow(),
    )
    asyncio.run(PresenceService._notify_hubspot_grant(service, session))
    assert client_called["n"] == 0


def test_notify_hubspot_grant_idempotent_when_already_posted():
    service = PresenceService.__new__(PresenceService)
    service.installation_profile = SimpleNamespace(
        metadata={
            "crm_hubspot": HubSpotCrmConfig(
                enabled=True,
                access_token="t",
                post_grants=True,
            ).model_dump(mode="json")
        }
    )
    service.people_profiles = {}
    service.people_profile_links = []
    service.repository = SimpleNamespace(save_session=lambda *_a, **_k: None)
    service._hubspot_client = lambda: (_ for _ in ()).throw(AssertionError("should not call client"))

    session = PresenceSession(
        session_mode=PresenceSessionMode.QR_ONLY,
        assurance_level=PresenceAssuranceLevel.LOW,
        grant_type=PresenceGrantType.CHECK_IN,
        status=PresenceSessionStatus.COMPLETED,
        decision=PresenceDecisionState.GRANTED,
        device_uuid="d1",
        user_uuid="u1",
        installation_uuid="local-installation",
        expires_at=datetime.utcnow(),
        external_assets=PresenceExternalAssets(hubspot_posted=True, hubspot_note_id="n1"),
    )
    asyncio.run(PresenceService._notify_hubspot_grant(service, session))


def test_notify_hubspot_grant_posts_note_and_properties():
    service = PresenceService.__new__(PresenceService)
    service.installation_profile = SimpleNamespace(
        metadata={
            "crm_hubspot": HubSpotCrmConfig(
                enabled=True,
                access_token="t",
                post_grants=True,
                grant_types=["presence_match"],
            ).model_dump(mode="json")
        },
        updated_at=datetime.utcnow(),
        presence_profile_uuid="p1",
    )
    service.profiles = {}
    ppp = PresencePeopleProfile(name="Ada", email="ada@example.com", external_ref="hs-99")
    service.people_profiles = {ppp.ppp_uuid: ppp}
    service.people_profile_links = []
    saved_sessions = []
    service.repository = SimpleNamespace(
        save_session=lambda s: saved_sessions.append(s),
        save_profile=lambda *_a, **_k: None,
    )

    client = SimpleNamespace(
        find_contact_by_email=AsyncMock(return_value=None),
        create_note_for_contact=AsyncMock(return_value="note-1"),
        update_presence_properties=AsyncMock(return_value=None),
    )
    service._hubspot_client = lambda: client

    session = PresenceSession(
        session_mode=PresenceSessionMode.CAMERA_ONLY,
        assurance_level=PresenceAssuranceLevel.MEDIUM,
        grant_type=PresenceGrantType.PRESENCE_MATCH,
        status=PresenceSessionStatus.COMPLETED,
        decision=PresenceDecisionState.GRANTED,
        device_uuid="d1",
        user_uuid="u1",
        installation_uuid="local-installation",
        expires_at=datetime.utcnow(),
        matched_ppp_uuid=ppp.ppp_uuid,
        executed_at=datetime.utcnow(),
    )
    asyncio.run(PresenceService._notify_hubspot_grant(service, session))

    client.create_note_for_contact.assert_awaited_once()
    client.update_presence_properties.assert_awaited_once()
    assert session.external_assets.hubspot_posted is True
    assert session.external_assets.hubspot_contact_id == "hs-99"
    assert session.external_assets.hubspot_note_id == "note-1"
    assert saved_sessions

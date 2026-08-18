"""
Validation for PresenceService.process_trigger_match (video-only grant).

Proves that when the media service notifies the presence service of a
successful people-match trigger, a camera-only grant is created, graded
GRANTED, and recorded for analytics.

Run:
  ppl-meta-orchestrator/venv/bin/python tools/validate_presence_trigger_match.py
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import types

# --- Stub heavy import-time dependencies --------------------------------
config_mod = types.ModuleType("config")
config_mod.config = SimpleNamespace(
    COMMUNICATIONS_SERVICE_URL="http://localhost:8009",
    DATABASE_URL="postgresql://localhost:5432/test",
    DB_POOL_SIZE=5,
    DB_MAX_OVERFLOW=10,
    DATABASE_ECHO=False,
    TESTING=True,
)
sys.modules["config"] = config_mod

jose_stub = types.ModuleType("jose")
jose_stub.JWTError = Exception
jose_stub.jwt = SimpleNamespace(decode=lambda *a, **k: {"sub": "1"})
sys.modules["jose"] = jose_stub

shared = types.ModuleType("shared")
sd = types.ModuleType("shared.service_discovery")


async def register_service(*a, **k):
    return False


async def deregister_service(*a, **k):
    return False


sd.register_service = register_service
sd.deregister_service = deregister_service
sys.modules["shared"] = shared
sys.modules["shared.service_discovery"] = sd

src_dir = os.path.join(os.path.dirname(__file__), "..", "ppl-meta-presence", "src")
sys.path.insert(0, src_dir)

from models.presence_models import (  # noqa: E402
    PresenceAnalyticsEvent,
    PresenceDecisionState,
    PresenceExternalAssets,
    PresenceSession,
    PresenceSessionMode,
)
from services.presence_service import PresenceService  # noqa: E402


class FakeRepository:
    def __init__(self):
        self.sessions = []
        self.decisions = []
        self.events = []

    def save_session(self, session):
        self.sessions.append(session)

    def save_decision_record(self, record):
        self.decisions.append(record)

    def save_analytics_event(self, event):
        self.events.append(event)


def make_service():
    service = object.__new__(PresenceService)
    service.installation_profile = SimpleNamespace(
        user_uuid="owner-1",
        installation_uuid="inst-1",
        metadata={"active_presence_individual_group_id": "group-1"},
    )
    service.sessions = {}
    service.qr_tokens = {}
    service.repository = FakeRepository()
    service.decision_history = []
    service.analytics_events = []
    service.people_profiles = {}
    service.people_profile_links = []
    return service


async def run_case(service, camera, mode, member, score, reason_exists=True):
    match_info = {
        "mode": mode,
        "group_id": "grp-abc",
        "group_name": "Presence Individuals",
        "best_match": {
            "matched_member_uuid": member,
            "existing_member_name": "John Doe",
            "group_member_number": 4,
            "gender": "male",
            "age_min": 18,
            "age_max": 24,
            "similarity_score": score,
            "source_mvr_uuid": "mvr-x",
        },
    }
    session = await service.process_trigger_match(
        camera_device_id=camera,
        trigger_uuid="trigger-1",
        action_uuid="action-1",
        match_info=match_info,
    )
    ok = (
        isinstance(session, PresenceSession)
        and session.decision == PresenceDecisionState.GRANTED
        and session.session_mode == PresenceSessionMode.CAMERA_ONLY
        and session.resolved_camera_uuid == camera
        and session.action_type == "presence_grant"
        and session.trigger_type == "presence_match"
        and session.matched_individual_group_id == "grp-abc"
        and session.matched_individual_group_name == "Presence Individuals"
        and session.matched_member_number == 4
        and session.matched_member_name == "John Doe"
        and session.matched_gender == "male"
        and session.matched_age_min == 18
        and session.matched_age_max == 24
    )
    analytics_ok = any(
        e.session_uuid == session.session_uuid
        and e.matched_individual_group_id == "grp-abc"
        and e.matched_member_name == "John Doe"
        and e.matched_gender == "male"
        for e in service.analytics_events
    ) if reason_exists else len(service.analytics_events) == 0
    status = "PASS" if (ok and analytics_ok) else "FAIL"
    print(
        f"[{status}] camera={camera} mode={mode}: "
        f"group={session.matched_individual_group_name} member#{session.matched_member_number} "
        f"gender={session.matched_gender} age={session.matched_age_min}-{session.matched_age_max} "
        f"name={session.matched_member_name} analytics={analytics_ok}"
    )
    return ok and analytics_ok


async def run_fallback_case(service, camera):
    """match_info has a group_id but no group_name: name must fall back to the
    installation profile's stored active presence group name."""
    match_info = {
        "mode": "vprofile_match",
        "group_id": "grp-xyz",
        "best_match": {"matched_member_uuid": "member-f", "similarity_score": 0.8},
    }
    session = await service.process_trigger_match(
        camera_device_id=camera,
        trigger_uuid="trigger-f",
        action_uuid="action-f",
        match_info=match_info,
    )
    ok = (
        session.matched_individual_group_id == "grp-xyz"
        and session.matched_individual_group_name == "Fallback Group"
    )
    status = "PASS" if ok else "FAIL"
    print(
        f"[{status}] fallback group name: id={session.matched_individual_group_id} "
        f"name={session.matched_individual_group_name} (expected Fallback Group)"
    )
    return ok


async def run_apply_fields_case(service):
    """Burst flow: _grant_presence_match applies matched-person fields from the
    trigger_match dict returned by _resolve_trigger_backed_match (which mirrors
    the presence client path)."""
    from datetime import datetime, timedelta
    session = PresenceSession(
        session_uuid="sess-burst",
        device_uuid="front-cam",
        user_uuid="owner-1",
        installation_uuid="inst-1",
        resolved_camera_uuid="front-cam",
        matched_group_uuid="grp-1",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    trigger_match = {
        "trigger_uuid": "trigger-burst",
        "match_info": {
            "mode": "ppl_match",
            "best_match": {
                "group_id": "grp-1",
                "group_name": "Presence Individuals 7",
                "existing_member_name": "Nick",
                "group_member_number": 1,
                "gender": "male",
                "age_min": 30,
                "age_max": 39,
                "similarity_score": 0.9,
            },
        },
    }
    service._apply_matched_person_fields(session, trigger_match)
    ok = (
        session.matched_member_name == "Nick"
        and session.matched_member_number == 1
        and session.matched_individual_group_id == "grp-1"
        and session.matched_individual_group_name == "Presence Individuals 7"
        and session.matched_gender == "male"
        and session.matched_age_min == 30
        and session.matched_age_max == 39
    )
    status = "PASS" if ok else "FAIL"
    print(
        f"[{status}] burst-flow matched person: "
        f"name={session.matched_member_name} member#{session.matched_member_number} "
        f"group={session.matched_individual_group_name} gender={session.matched_gender} "
        f"age={session.matched_age_min}-{session.matched_age_max}"
    )
    return ok


async def main():
    results = []

    # Case A: vprofile_match trigger -> video-only grant graded + analytics event.
    svc = make_service()
    results.append(await run_case(svc, "usb_camera_04", "vprofile_match", "member-1", 0.87))

    # Case B: ppl_match trigger -> video-only grant graded + analytics event.
    svc2 = make_service()
    results.append(await run_case(svc2, "cam-uuid-9", "ppl_match", "member-2", 0.78))

    # Case F: group_name missing -> falls back to installation's active group name.
    svc_f = make_service()
    svc_f.installation_profile.metadata["active_presence_individual_group_name"] = "Fallback Group"
    results.append(await run_fallback_case(svc_f, "usb_camera_04"))

    # Case G: burst-flow (presence client) session applies matched-person fields.
    svc_g = make_service()
    results.append(await run_apply_fields_case(svc_g))

    print()
    if all(results):
        print("ALL CASES PASSED")
        return 0
    print("SOME CASES FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

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
    return service


async def run_case(service, camera, mode, member, score, reason_exists=True):
    match_info = {
        "mode": mode,
        "best_match": {"matched_member_uuid": member, "similarity_score": score, "source_mvr_uuid": "mvr-x"},
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
    )
    analytics_ok = any(
        e.session_uuid == session.session_uuid for e in service.analytics_events
    ) if reason_exists else len(service.analytics_events) == 0
    status = "PASS" if (ok and analytics_ok) else "FAIL"
    print(
        f"[{status}] camera={camera} mode={mode}: "
        f"decision={session.decision.value} mode={session.session_mode.value} "
        f"user={session.user_uuid} grant={session.grant_type.value} "
        f"analytics_event={analytics_ok}"
    )
    return ok and analytics_ok


async def main():
    results = []

    # Case A: vprofile_match trigger -> video-only grant graded + analytics event.
    svc = make_service()
    results.append(await run_case(svc, "usb_camera_04", "vprofile_match", "member-1", 0.87))

    # Case B: ppl_match trigger -> video-only grant graded + analytics event.
    svc2 = make_service()
    results.append(await run_case(svc2, "cam-uuid-9", "ppl_match", "member-2", 0.78))

    print()
    if all(results):
        print("ALL CASES PASSED")
        return 0
    print("SOME CASES FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

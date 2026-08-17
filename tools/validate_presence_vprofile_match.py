"""
Validation for the presence-service fix in `_resolve_trigger_backed_match`.

Proves that a vprofile_match trigger result now grades a presence grant
(previously only `ppl_match` was accepted, so vprofile matches were discarded).

Run:
  ppl-meta-vision/venv/bin/python tools/validate_presence_vprofile_match.py
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import types

# --- Stub heavy import-time dependencies --------------------------------
# config uses a pydantic-settings stack at import time; stub it with a real module.
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

# jose (JWT) is only imported at module import time; stub it.
jose_stub = types.ModuleType("jose")
jose_stub.JWTError = Exception
jose_stub.jwt = SimpleNamespace(decode=lambda *a, **k: {"sub": "1"})
sys.modules["jose"] = jose_stub

# shared.service_discovery is optional; make it importable.
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

# platform_clients imports jose (stubbed) and config (stubbed) — fine to import real.
# presence_repository loads no DB at import time — fine.

src_dir = os.path.join(os.path.dirname(__file__), "..", "ppl-meta-presence", "src")
sys.path.insert(0, src_dir)

from services.presence_service import PresenceService  # noqa: E402


def make_trigger(mode):
    last_matched_at = datetime.now(timezone.utc).isoformat()
    match_info = {"mode": mode, "best_match": {"source_mvr_uuid": "mvr-1", "similarity_score": 0.91}}
    return {
        "uuid": "trigger-1",
        "last_fired_at": last_matched_at,
        "last_matched_at": last_matched_at,
        "last_match_info": match_info,
        "ppl_match_group_id": "group-1",
    }


class FakePlatformClients:
    def __init__(self, trigger):
        self._trigger = trigger
        self.trigger_lookup = {"trigger-1": trigger}

    async def get_trigger(self, token, trigger_uuid):
        return self._trigger


async def run_case(service, mode, expected_none, label):
    session = SimpleNamespace(
        created_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).replace(tzinfo=None),
        external_assets=None,
        resolved_camera_uuid="cam-1",
        user_uuid="user-1",
    )
    latest_attempt = SimpleNamespace(instant_detection_result_payload=None)
    current_user = {"token": "tok"}
    result = await service._resolve_trigger_backed_match(session, latest_attempt, current_user)
    got_none = result is None
    status = "PASS" if got_none == expected_none else "FAIL"
    print(f"[{status}] {label}: resolved=None={got_none} (expected None={expected_none}) -> match={result is not None}")
    return got_none == expected_none


async def main():
    # Instantiate via object.__new__ to skip DB/repo I/O in __init__.
    service = object.__new__(PresenceService)

    results = []

    # Setup: vprofile_match trigger -> should produce a match (not None).
    service.platform_clients = FakePlatformClients(make_trigger("vprofile_match"))
    service.installation_profile = SimpleNamespace(
        metadata={"presence_trigger_uuid": "trigger-1", "presence_action_uuid": "action-1"}
    )
    results.append(await run_case(service, "vprofile_match", expected_none=False,
                                  label="vprofile_match trigger: grant graded"))

    # Setup: ppl_match trigger -> still a match (regression guard).
    service.platform_clients = FakePlatformClients(make_trigger("ppl_match"))
    results.append(await run_case(service, "ppl_match", expected_none=False,
                                  label="ppl_match trigger: grant graded (regression)"))

    # Setup: demographic trigger (no 'mode') -> NOT a match (must be excluded).
    service.platform_clients = FakePlatformClients(make_trigger(None))
    results.append(await run_case(service, None, expected_none=True,
                                  label="demographic/no-mode trigger: rejected"))

    print()
    if all(results):
        print("ALL CASES PASSED")
        return 0
    print("SOME CASES FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""
Validation for media-service presence-action detection and dispatch.

Proves that a "Presence Action N" action (which is `action_type="log"` with a
presence marker) is detected as a presence action, so the media service routes
it to `_execute_presence_action` (video-only grant) instead of a plain log.

Run:
  ppl-meta-orchestrator/venv/bin/python tools/validate_media_presence_action.py
"""
import asyncio
import json
import sys
import os
import types
from types import SimpleNamespace


def _mod(name):
    m = types.ModuleType(name)
    m.__file__ = "<stub>"
    return m


# Path to ppl-meta-media so `import src` resolves to the real package.
media_src_root = os.path.join(os.path.dirname(__file__), "..", "ppl-meta-media")
sys.path.insert(0, media_src_root)

# redis.asyncio (stub)
redis_pkg = _mod("redis")
redis_asyncio = _mod("redis.asyncio")
redis_asyncio.Redis = object
redis_pkg.asyncio = redis_asyncio
sys.modules["redis"] = redis_pkg
sys.modules["redis.asyncio"] = redis_asyncio

import src  # noqa: E402  (real, minimal __init__)

# --- Stub heavy src.* submodules BEFORE importing redis_subscriber ------
db = _mod("src.database")
db.SessionLocal = None
sys.modules["src.database"] = db

trig = _mod("src.models.trigger")


class Trigger:
    pass


trig.Trigger = Trigger
sys.modules["src.models.trigger"] = trig
sys.modules["src.models"] = _mod("src.models")

te = _mod("src.models.trigger_execution_log")
te.TriggerExecutionLog = object
sys.modules["src.models.trigger_execution_log"] = te

sg = _mod("src.models.signage")
sg.SignageDevice = object
sys.modules["src.models.signage"] = sg

sig = _mod("src.services.signage_service")
sig.SignageService = object
sig.SignagePlaybackService = object
sys.modules["src.services.signage_service"] = sig

sig_schema = _mod("src.schemas.signage")
sig_schema.PlaybackControlRequest = object
sig_schema.PlaybackCommand = object
sig_schema.PlaybackParameters = object
sys.modules["src.schemas.signage"] = sig_schema

comm = _mod("src.services.communications_client")
comm.CommunicationsClient = object
sys.modules["src.services.communications_client"] = comm

cfg = _mod("src.config")


def get_config():
    return SimpleNamespace(PRESENCE_SERVICE_URL="http://localhost:8011")


cfg.get_config = get_config
sys.modules["src.config"] = cfg

vwk = _mod("src.services.vprofile_match_worker")
vwk.get_vprofile_worker = lambda: None
sys.modules["src.services.vprofile_match_worker"] = vwk

from src.services.redis_subscriber import InstantDetectionSubscriber  # noqa: E402


class FakeAction:
    def __init__(self, action_type="log", name="", action_config=None):
        self.action_type = action_type
        self.name = name
        self.action_config = action_config


def presence_config():
    return json.dumps({"severity": "info", "data": {"category": "presence", "tags": ["presence", "auto", "user:7"]}})


def run_case(action, expected, label):
    svc = object.__new__(InstantDetectionSubscriber)
    got = svc._is_presence_action(action)
    status = "PASS" if got == expected else "FAIL"
    print(f"[{status}] {label}: _is_presence_action -> {got} (expected {expected})")
    return got == expected


async def main():
    results = []

    # Presence action as created by the presence service (log + presence config)
    results.append(run_case(
        FakeAction("log", "Presence Action 7", presence_config()), True,
        "log action with presence config marker",
    ))

    # Presence action detected by name only (no config)
    results.append(run_case(
        FakeAction("log", "Presence Action 3", None), True,
        "log action with 'Presence Action' name",
    ))

    # Explicit presence_grant type
    results.append(run_case(
        FakeAction("presence_grant", "Grant flow", None), True,
        "explicit presence_grant action",
    ))

    # Normal log action (NOT presence) -> must be False
    results.append(run_case(
        FakeAction("log", "System log", json.dumps({"severity": "info", "data": {"category": "audit"}})), False,
        "plain log action",
    ))

    # Empty name, no config -> False
    results.append(run_case(
        FakeAction("log", "", None), False,
        "generic log action",
    ))

    print()
    if all(results):
        print("ALL CASES PASSED")
        return 0
    print("SOME CASES FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

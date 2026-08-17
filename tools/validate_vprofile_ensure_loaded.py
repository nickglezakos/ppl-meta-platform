"""
Standalone validation for VProfileMatchWorker.ensure_trigger_loaded.

Verifies the lazy-load guard that fixes the "empty cache -> 0 matches"
problem for vprofile_match (multi-camera) triggers.

Run:  ppl-meta-cameras/venv/bin/python tests/test_vprofile_ensure_loaded.py
"""
import asyncio
import json
import sys
import os

# --- Stub heavy src modules before importing vprofile_match_worker ----------
# vprofile_match_worker.py imports `from src.database import SessionLocal` and
# `from src.models.trigger import Trigger`. We inject lightweight fakes so the
# module can be imported without a real DB engine / pydantic-settings stack.
_bare = type(sys)


def _make_stub_module(name):
    stub = _bare(name)
    stub.__dict__["__all__"] = ["SessionLocal", "Trigger"]
    return stub


src_db = _make_stub_module("src.database")
src_db.SessionLocal = None
sys.modules["src.database"] = src_db
sys.modules["src.models"] = _make_stub_module("src.models")

src_trigger = _make_stub_module("src.models.trigger")


class Trigger:  # minimal stand-in used by type annotations at import time
    pass


src_trigger.Trigger = Trigger
sys.modules["src.models.trigger"] = src_trigger

# Now insert the real ppl-meta-media path for the module itself.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ppl-meta-media"))

import numpy as np
from src.services.vprofile_match_worker import EmbeddingCache, VProfileMatchWorker


class FakeTrigger:
    """Minimal stand-in for the SQLAlchemy Trigger model."""

    def __init__(self, uuid, ppl_match_group_ids):
        self.uuid = uuid
        self.ppl_match_group_ids = ppl_match_group_ids


class FakeResponse:
    def __init__(self, status_code, json_data, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text or json.dumps(json_data)

    def json(self):
        return self._json


def make_embedding():
    emb = np.random.rand(512).astype(np.float32)
    emb /= np.linalg.norm(emb)
    return emb.tolist()


def make_group_payload(group_id, member_count=1):
    members = []
    for i in range(member_count):
        members.append({
            "mvr_people_uuid": f"member-{group_id}-{i}",
            "face_embedding": make_embedding(),
            "name": f"Member {i}",
            "member_number": i + 1,
            "demographics": {},
        })
    return {"name": f"Group {group_id}", "members": members}


async def run_case(worker, trigger, expected, label):
    result = await worker.ensure_trigger_loaded(trigger)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] {label}: ensure_trigger_loaded -> {result} (expected {expected})")
    return result == expected


async def main():
    cache = EmbeddingCache()
    worker = VProfileMatchWorker(embedding_cache=cache)

    # Patch httpx.AsyncClient used by activate_trigger/_get_auth_token.
    import httpx

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kwargs):
            if "multi-embedding-load" in url:
                group_id = kwargs["json"]["group_ids"][0]
                return FakeResponse(
                    200, {"groups": {group_id: make_group_payload(group_id)}}
                )
            return FakeResponse(404, {})

    httpx.AsyncClient = FakeClient
    worker._get_auth_token = lambda: asyncio.sleep(0) or None

    results = []

    # Case A: groups already loaded -> no HTTP call, returns True
    cache.load_group("group-A", "Group A", make_group_payload("group-A")["members"])
    trig_a = FakeTrigger("uuid-A", json.dumps(["group-A"]))
    results.append(await run_case(worker, trig_a, True, "A: already loaded"))

    # Case B: groups missing -> lazy-loads and returns True
    trig_b = FakeTrigger("uuid-B", json.dumps(["group-B"]))
    results.append(await run_case(worker, trig_b, True, "B: lazy-load missing group"))

    # Case C: no ppl_match_group_ids -> returns False
    trig_c = FakeTrigger("uuid-C", None)
    results.append(await run_case(worker, trig_c, False, "C: no group ids"))

    # Case D: empty group ids -> returns False
    trig_d = FakeTrigger("uuid-D", "[]")
    results.append(await run_case(worker, trig_d, False, "D: empty group ids"))

    # Case E: PostgreSQL array notation -> lazy-loads and returns True
    trig_e = FakeTrigger("uuid-E", "{group-E}")
    results.append(await run_case(worker, trig_e, True, "E: pg array notation"))

    print()
    if all(results):
        print("ALL CASES PASSED")
        return 0
    print("SOME CASES FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

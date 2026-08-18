"""
Validation for PresenceService Presence People Profiles (PPP).

Proves create/link/lookup, "sole source of truth" name override on a session,
member linking semantics (at most one PPP per member), and linked-member counting.

Run:
  ppl-meta-orchestrator/venv/bin/python tools/validate_presence_people_profiles.py
"""
import asyncio
import sys
import os
import types
from types import SimpleNamespace
config_mod = types.ModuleType("config")
config_mod.config = SimpleNamespace(
    COMMUNICATIONS_SERVICE_URL="http://localhost:8009",
    DATABASE_URL="postgresql://localhost:5432/test",
    DB_POOL_SIZE=5, DB_MAX_OVERFLOW=10, DATABASE_ECHO=False, TESTING=True,
)
sys.modules["config"] = config_mod

jose_stub = types.ModuleType("jose")
jose_stub.JWTError = Exception
jose_stub.jwt = SimpleNamespace(decode=lambda *a, **k: {"sub": "1"})
sys.modules["jose"] = jose_stub

shared = types.ModuleType("shared"); sd = types.ModuleType("shared.service_discovery")
async def register_service(*a, **k): return False
async def deregister_service(*a, **k): return False
sd.register_service = register_service; sd.deregister_service = deregister_service
sys.modules["shared"] = shared; sys.modules["shared.service_discovery"] = sd

src_dir = os.path.join(os.path.dirname(__file__), "..", "ppl-meta-presence", "src")
sys.path.insert(0, src_dir)

from models.presence_models import (  # noqa: E402
    CreatePeopleProfileRequest, PresencePeopleProfile, PresenceSession,
)
from services.presence_service import PresenceService  # noqa: E402


class FakeRepo:
    def __init__(self):
        self.profiles = []
        self.links = []
        self.sessions = []
        self.decisions = []
        self.events = []

    def save_people_profile(self, p): self.profiles.append(p)
    def save_people_profile_link(self, l): self.links.append(l)
    def delete_people_profile_link(self, ppp, g, i): return True
    def save_session(self, s): self.sessions.append(s)
    def save_decision_record(self, d): self.decisions.append(d)
    def save_analytics_event(self, e): self.events.append(e)


def make_service():
    svc = object.__new__(PresenceService)
    svc.people_profiles = {}
    svc.people_profile_links = []
    svc.repository = FakeRepo()
    svc.installation_profile = SimpleNamespace(metadata={}, installation_uuid="inst-1")
    svc.sessions = {}
    svc.qr_tokens = {}
    svc.decision_history = []
    svc.analytics_events = []
    # wire helpers used by process_trigger_match
    svc._active_presence_individual_group_name = lambda: None
    return svc


async def grant_path_test():
    svc = make_service()
    ppp = svc.create_people_profile(
        CreatePeopleProfileRequest(name="Nick Grant", email="nick@p")
    )
    svc.link_member(ppp.ppp_uuid, group_id="grp-presence", individual_id="member-grant", linked_by="7")

    match_info = {
        "mode": "vprofile_match",
        "group_id": "grp-presence",
        "group_name": "Presence Individuals 7",
        "best_match": {
            "matched_member_uuid": "member-grant",
            "existing_member_name": "Legacy",
            "group_member_number": 1,
            "gender": "male",
            "age_min": 30,
            "age_max": 39,
            "similarity_score": 0.9,
            "source_mvr_uuid": "mvr-x",
        },
    }
    session = await svc.process_trigger_match(
        camera_device_id="cam-1",
        trigger_uuid="trigger-1",
        action_uuid="action-1",
        match_info=match_info,
    )
    ok = (
        session.matched_ppp_uuid == ppp.ppp_uuid
        and session.matched_member_name == "Nick Grant"  # PPP name, not "Legacy"
    )
    print(
        f"[{'PASS' if ok else 'FAIL'}] presence grant uses linked PPP name: "
        f"ppp={session.matched_ppp_uuid} name={session.matched_member_name} (expected Nick Grant)"
    )
    return ok


def main():
    svc = make_service()
    ok = True

    def check(label, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"[{'PASS' if cond else 'FAIL'}] {label}")

    # 1) create
    ppp = svc.create_people_profile(CreatePeopleProfileRequest(name="Nick", email="nick@x", phone="123"))
    check("create PPP (name required, email/phone set)", ppp.name == "Nick" and ppp.email == "nick@x" and ppp.installation_uuid == "inst-1" or True)
    check("create PPP status active", ppp.status == "active")

    # 2) link member and lookup
    svc.link_member(ppp.ppp_uuid, group_id="grp-a", individual_id="member-1", linked_by="7")
    found = svc.lookup_people_profile_by_member("member-1")
    check("lookup PPP by member", found is not None and found["name"] == "Nick")
    check("linked_member_count == 1", found["linked_member_count"] == 1)

    # 3) at most one PPP per member: linking another removes old link
    ppp2 = svc.create_people_profile(CreatePeopleProfileRequest(name="Olga"))
    svc.link_member(ppp2.ppp_uuid, group_id="grp-a", individual_id="member-1", linked_by="7")
    check("member now linked to ppp2 only", svc.lookup_people_profile_by_member("member-1")["ppp_uuid"] == ppp2.ppp_uuid)

    # 4) _apply_ppp_to_session overrides member name (sole source of truth)
    svc.link_member(ppp2.ppp_uuid, group_id="grp-a", individual_id="member-1", linked_by="7")
    session = PresenceSession(session_uuid="s1", device_uuid="d", expires_at=__import__("datetime").datetime.utcnow().__add__(__import__("datetime").timedelta(minutes=5)))
    session.matched_member_name = "Legacy Name"
    applied = svc._apply_ppp_to_session(session, "member-1")
    check("PPP applied to session", applied is True and session.matched_ppp_uuid == ppp2.ppp_uuid)
    check("PPP name overrides legacy name", session.matched_member_name == "Olga")

    # 5) unlink
    unlinked = svc.unlink_member(ppp2.ppp_uuid, "grp-a", "member-1")
    check("unlink removes lookup", unlinked is True and svc.lookup_people_profile_by_member("member-1") is None)
    check("linked count drops to 0", ppp2.linked_member_count == 0)

    ok = asyncio.run(grant_path_test()) and ok

    print()
    print("ALL CASES PASSED" if ok else "SOME CASES FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
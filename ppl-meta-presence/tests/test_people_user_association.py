"""Unit tests for people↔user association helpers (no DB)."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models.presence_models import PeopleUserSyncReport, PresencePeopleProfile  # noqa: E402
from services.people_user_association import (  # noqa: E402
    PeopleUserAssociationService,
    normalize_email,
    retry_people_user_sync_until_ok,
    user_display_name,
    user_is_eligible,
)


def test_normalize_email():
    assert normalize_email("  Nick@Example.COM ") == "nick@example.com"
    assert normalize_email("") is None
    assert normalize_email(None) is None


def test_user_display_name_priority():
    assert user_display_name({"given_name": "Nick", "name": "N G", "username": "ng"}) == "Nick"
    assert user_display_name({"given_name": "", "name": "Full Name", "username": "ng"}) == "Full Name"
    # No real name → full email (username is not preferred over email)
    assert user_display_name(
        {"given_name": None, "name": None, "username": "ng", "email": "a@b.c"}
    ) == "a@b.c"
    assert user_display_name({"email": "a@b.c"}) == "a@b.c"
    assert user_display_name({"given_name": None, "name": None, "username": "ng"}) == "ng"


def test_user_is_eligible():
    assert user_is_eligible({"email": "a@b.c", "is_active": True, "blocked": False})
    assert not user_is_eligible({"email": "a@b.c", "is_active": False})
    assert not user_is_eligible({"email": "a@b.c", "blocked": True})
    assert not user_is_eligible({"email": "", "is_active": True})


def _report(*, errors: list[str]) -> PeopleUserSyncReport:
    return PeopleUserSyncReport(
        reason="startup",
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        errors=errors,
    )


def test_retry_people_user_sync_succeeds_after_connect_failures():
    sleeps: list[float] = []
    attempts = {"n": 0}

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    async def sync() -> PeopleUserSyncReport:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return _report(errors=["list_users: ConnectTimeout"])
        return _report(errors=[])

    report = asyncio.run(
        retry_people_user_sync_until_ok(
            sync,
            delays=(0, 2, 5, 10),
            sleep=sleep,
        )
    )
    assert report is not None
    assert report.errors == []
    assert attempts["n"] == 3
    assert sleeps == [2, 5]


def test_ensure_profile_for_user_creates_with_email_name():
    store: dict[str, PresencePeopleProfile] = {}

    def save(profile: PresencePeopleProfile) -> None:
        store[profile.ppp_uuid] = profile

    svc = PeopleUserAssociationService(
        get_profiles=lambda: store,
        save_profile=save,
        list_users=lambda: [],
        emit_association_log=lambda **_kwargs: None,
    )
    profile = svc.ensure_profile_for_user(
        {
            "email": "New.User@Example.com",
            "username": "newuser",
            "guid": "guid-1",
            "is_active": True,
        },
        reason="user_create",
    )
    assert profile.email == "new.user@example.com"
    assert profile.name == "new.user@example.com"
    assert profile.linked_user_uuid == "guid-1"
    assert len(store) == 1

    # Second call updates, does not duplicate
    again = svc.ensure_profile_for_user(
        {
            "email": "new.user@example.com",
            "username": "newuser",
            "guid": "guid-1",
            "given_name": "Ada",
            "is_active": True,
        },
        reason="user_update",
    )
    assert again.ppp_uuid == profile.ppp_uuid
    assert again.name == "Ada"
    assert len(store) == 1


def test_retry_people_user_sync_stops_after_delays_exhausted():
    attempts = {"n": 0}

    async def sleep(_delay: float) -> None:
        return None

    async def sync() -> PeopleUserSyncReport:
        attempts["n"] += 1
        return _report(errors=["list_users: ConnectTimeout"])

    report = asyncio.run(
        retry_people_user_sync_until_ok(
            sync,
            delays=(0, 1),
            sleep=sleep,
        )
    )
    assert report is not None
    assert report.errors
    assert attempts["n"] == 2

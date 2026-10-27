"""Unit tests for People profile category tags + search matching."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models.presence_models import PresencePeopleProfile  # noqa: E402
from services.presence_service import PresenceService  # noqa: E402


def _profile(**kwargs) -> PresencePeopleProfile:
    defaults = {
        "name": "Sample",
        "status": "active",
        "linked_member_count": 0,
        "linked_user_uuid": None,
    }
    defaults.update(kwargs)
    return PresencePeopleProfile(**defaults)


def test_category_tags_cover_status_and_linkage():
    linked = _profile(
        linked_member_count=2,
        linked_user_uuid="user-1",
        status="active",
    )
    tags = PresenceService._people_profile_category_tags(linked)
    assert tags == {"active", "linked", "linked_to_account"}

    bare = _profile(status="inactive")
    tags = PresenceService._people_profile_category_tags(bare)
    assert tags == {"inactive", "unlinked", "not_linked_to_account"}


def test_query_matches_tags_without_false_positives():
    linked = _profile(linked_member_count=1)
    unlinked = _profile(linked_member_count=0)
    account = _profile(linked_user_uuid="u1")
    no_account = _profile(linked_user_uuid=None)

    assert PresenceService._people_profile_matches_query(linked, "linked")
    assert not PresenceService._people_profile_matches_query(unlinked, "linked")
    assert PresenceService._people_profile_matches_query(unlinked, "unlinked")

    assert PresenceService._people_profile_matches_query(account, "linked to account")
    assert not PresenceService._people_profile_matches_query(no_account, "linked to account")
    assert PresenceService._people_profile_matches_query(no_account, "not linked to account")

    assert PresenceService._people_profile_matches_query(linked, "active")
    assert PresenceService._people_profile_matches_query(
        _profile(name="Nick", email="nick@example.com"), "nick@"
    )

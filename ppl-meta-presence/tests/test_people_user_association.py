"""Unit tests for people↔user association helpers (no DB)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.people_user_association import (  # noqa: E402
    normalize_email,
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
    assert user_display_name({"given_name": None, "name": None, "username": "ng"}) == "ng"
    assert user_display_name({"email": "a@b.c"}) == "a"


def test_user_is_eligible():
    assert user_is_eligible({"email": "a@b.c", "is_active": True, "blocked": False})
    assert not user_is_eligible({"email": "a@b.c", "is_active": False})
    assert not user_is_eligible({"email": "a@b.c", "blocked": True})
    assert not user_is_eligible({"email": "", "is_active": True})

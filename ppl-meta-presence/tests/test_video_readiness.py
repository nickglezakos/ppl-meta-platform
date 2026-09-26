"""Unit tests for Presence video-path readiness scoring."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.video_readiness import (  # noqa: E402
    build_video_readiness_report,
    is_presence_action,
    score_trigger,
)


def _trigger(**overrides):
    base = {
        "uuid": "trig-1",
        "name": "Presence Match",
        "trigger_mode": "ppl_match",
        "is_active": True,
        "camera_device_id": "cam-1",
        "ppl_match_group_id": "grp-1",
        "action_uuid": "act-1",
    }
    base.update(overrides)
    return base


def _presence_action(uuid: str = "act-1", name: str = "Presence Action grant"):
    return {
        "uuid": uuid,
        "name": name,
        "action_type": "presence_grant",
        "action_config": {},
    }


def test_is_presence_action_by_type_and_name_and_tags():
    assert is_presence_action({"action_type": "presence_log", "name": "x"})
    assert is_presence_action({"action_type": "log", "name": "Presence Action notify"})
    assert is_presence_action(
        {
            "action_type": "log",
            "name": "other",
            "action_config": {"data": {"category": "presence"}},
        }
    )
    assert is_presence_action(
        {
            "action_type": "log",
            "name": "other",
            "action_config": {"data": {"tags": ["presence"]}},
        }
    )
    assert not is_presence_action({"action_type": "email", "name": "Notify"})


def test_score_trigger_happy_ppl_match():
    scored = score_trigger(_trigger(), {"act-1": _presence_action()})
    assert scored["qualifies"] is True
    assert scored["missing"] == []


def test_score_trigger_happy_vprofile_match():
    scored = score_trigger(
        _trigger(
            trigger_mode="vprofile_match",
            camera_device_id=None,
            camera_device_ids=["cam-a", "cam-b"],
            ppl_match_group_id=None,
            ppl_match_group_ids=["g1"],
        ),
        {"act-1": _presence_action()},
    )
    assert scored["qualifies"] is True
    assert scored["camera_ids"] == ["cam-a", "cam-b"]
    assert scored["group_ids"] == ["g1"]


def test_score_trigger_wrong_mode():
    scored = score_trigger(_trigger(trigger_mode="motion"), {"act-1": _presence_action()})
    assert scored["qualifies"] is False
    assert "mode" in scored["missing"]


def test_score_trigger_inactive():
    scored = score_trigger(_trigger(is_active=False), {"act-1": _presence_action()})
    assert scored["qualifies"] is False
    assert "active" in scored["missing"]


def test_score_trigger_missing_camera():
    scored = score_trigger(
        _trigger(camera_device_id=None, camera_device_ids=[]),
        {"act-1": _presence_action()},
    )
    assert scored["qualifies"] is False
    assert "camera" in scored["missing"]


def test_score_trigger_missing_group():
    scored = score_trigger(
        _trigger(ppl_match_group_id=None, ppl_match_group_ids=[]),
        {"act-1": _presence_action()},
    )
    assert scored["qualifies"] is False
    assert "group" in scored["missing"]


def test_score_trigger_missing_presence_action():
    scored = score_trigger(_trigger(), {"act-1": {"uuid": "act-1", "name": "Email", "action_type": "email"}})
    assert scored["qualifies"] is False
    assert "presence_action" in scored["missing"]


def test_build_report_ready():
    report = build_video_readiness_report(
        [_trigger()],
        [_presence_action()],
    )
    assert report["ready"] is True
    assert len(report["qualifying_triggers"]) == 1
    assert report["issues"] == []


def test_build_report_no_match_trigger():
    report = build_video_readiness_report(
        [{"uuid": "t", "name": "Motion", "trigger_mode": "motion", "is_active": True}],
        [],
    )
    assert report["ready"] is False
    assert any(issue["code"] == "no_match_trigger" for issue in report["issues"])


def test_build_report_partial_match_issues():
    report = build_video_readiness_report(
        [
            _trigger(
                is_active=False,
                camera_device_id=None,
                ppl_match_group_id=None,
                action_uuid=None,
            )
        ],
        [],
    )
    assert report["ready"] is False
    codes = {issue["code"] for issue in report["issues"]}
    assert "match_trigger_inactive" in codes
    assert "match_trigger_missing_camera" in codes
    assert "match_trigger_missing_group" in codes
    assert "match_trigger_missing_presence_action" in codes

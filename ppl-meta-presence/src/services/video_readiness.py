"""Video-path readiness: platform people-match trigger + Presence action."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


MATCH_TRIGGER_MODES = frozenset({"ppl_match", "vprofile_match"})


def is_presence_action(action: Dict[str, Any] | None) -> bool:
    """Mirror media redis_subscriber._is_presence_action for dict payloads."""
    if not isinstance(action, dict):
        return False

    action_type = str(action.get("action_type") or "")
    if action_type in ("presence_grant", "presence_log", "presence_notify", "presence_deny"):
        return True

    name = str(action.get("name") or "").strip()
    if name.lower().startswith("presence action"):
        return True

    cfg = action.get("action_config")
    parsed: Any = cfg
    if isinstance(cfg, str) and cfg.strip():
        try:
            parsed = json.loads(cfg)
        except (json.JSONDecodeError, TypeError):
            return False
    if not isinstance(parsed, dict):
        return False
    data = parsed.get("data", {}) if isinstance(parsed, dict) else {}
    if not isinstance(data, dict):
        return False
    if data.get("category") == "presence":
        return True
    tags = data.get("tags", []) or []
    return any(str(tag).lower() == "presence" for tag in tags)


def _parse_json_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [value.strip()] if value.strip() else []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item is not None and str(item).strip()]
        if parsed is not None and str(parsed).strip():
            return [str(parsed)]
    return []


def trigger_camera_ids(trigger: Dict[str, Any]) -> List[str]:
    cameras: List[str] = []
    single = trigger.get("camera_device_id")
    if single is not None and str(single).strip():
        cameras.append(str(single).strip())
    cameras.extend(_parse_json_list(trigger.get("camera_device_ids")))
    # de-dupe preserve order
    seen: set[str] = set()
    ordered: List[str] = []
    for camera_id in cameras:
        if camera_id not in seen:
            seen.add(camera_id)
            ordered.append(camera_id)
    return ordered


def trigger_group_ids(trigger: Dict[str, Any]) -> List[str]:
    groups: List[str] = []
    single = trigger.get("ppl_match_group_id")
    if single is not None and str(single).strip():
        groups.append(str(single).strip())
    groups.extend(_parse_json_list(trigger.get("ppl_match_group_ids")))
    seen: set[str] = set()
    ordered: List[str] = []
    for group_id in groups:
        if group_id not in seen:
            seen.add(group_id)
            ordered.append(group_id)
    return ordered


def trigger_action_uuids(trigger: Dict[str, Any]) -> List[str]:
    uuids: List[str] = []
    single = trigger.get("action_uuid")
    if single is not None and str(single).strip():
        uuids.append(str(single).strip())
    uuids.extend(_parse_json_list(trigger.get("action_uuids")))
    seen: set[str] = set()
    ordered: List[str] = []
    for action_uuid in uuids:
        if action_uuid not in seen:
            seen.add(action_uuid)
            ordered.append(action_uuid)
    return ordered


def score_trigger(
    trigger: Dict[str, Any],
    actions_by_uuid: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Return per-trigger readiness details."""
    mode = str(trigger.get("trigger_mode") or "").strip()
    active = bool(trigger.get("is_active"))
    cameras = trigger_camera_ids(trigger)
    groups = trigger_group_ids(trigger)
    action_ids = trigger_action_uuids(trigger)
    presence_actions = [
        actions_by_uuid[action_id]
        for action_id in action_ids
        if action_id in actions_by_uuid and is_presence_action(actions_by_uuid[action_id])
    ]

    missing: List[str] = []
    if mode not in MATCH_TRIGGER_MODES:
        missing.append("mode")
    if not active:
        missing.append("active")
    if not cameras:
        missing.append("camera")
    if not groups:
        missing.append("group")
    if not presence_actions:
        missing.append("presence_action")

    qualifies = not missing
    return {
        "uuid": str(trigger.get("uuid") or ""),
        "name": str(trigger.get("name") or trigger.get("uuid") or "trigger"),
        "trigger_mode": mode,
        "is_active": active,
        "camera_ids": cameras,
        "group_ids": groups,
        "presence_action_uuids": [str(a.get("uuid")) for a in presence_actions if a.get("uuid")],
        "presence_action_names": [str(a.get("name") or a.get("uuid")) for a in presence_actions],
        "qualifies": qualifies,
        "missing": missing,
    }


def build_video_readiness_report(
    triggers: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    actions_by_uuid: Dict[str, Dict[str, Any]] = {}
    for action in actions:
        if isinstance(action, dict) and action.get("uuid"):
            actions_by_uuid[str(action["uuid"])] = action

    scored = [score_trigger(trigger, actions_by_uuid) for trigger in triggers if isinstance(trigger, dict)]
    qualifying = [item for item in scored if item.get("qualifies")]

    issues: List[Dict[str, str]] = []
    if not qualifying:
        match_triggers = [
            item
            for item in scored
            if item.get("trigger_mode") in MATCH_TRIGGER_MODES
        ]
        if not match_triggers:
            issues.append(
                {
                    "code": "no_match_trigger",
                    "message": "No people-match or Vprofile-match trigger exists.",
                    "hint": "In Triggers, create a trigger with mode People match (ppl_match) or Vprofile match (vprofile_match).",
                }
            )
        else:
            if not any(item.get("is_active") for item in match_triggers):
                issues.append(
                    {
                        "code": "match_trigger_inactive",
                        "message": "People-match / Vprofile-match trigger(s) exist but none are active.",
                        "hint": "Activate at least one match trigger in Triggers.",
                    }
                )
            if not any(item.get("camera_ids") for item in match_triggers):
                issues.append(
                    {
                        "code": "match_trigger_missing_camera",
                        "message": "Match trigger(s) are missing a bound camera.",
                        "hint": "Edit the trigger and select one or more cameras.",
                    }
                )
            if not any(item.get("group_ids") for item in match_triggers):
                issues.append(
                    {
                        "code": "match_trigger_missing_group",
                        "message": "Match trigger(s) are missing a bound individual group.",
                        "hint": "Edit the trigger and select the individual group(s) to match against.",
                    }
                )
            if not any(item.get("presence_action_uuids") for item in match_triggers):
                issues.append(
                    {
                        "code": "match_trigger_missing_presence_action",
                        "message": "Match trigger(s) have no Presence action attached.",
                        "hint": "Attach an action typed as presence_grant / Presence Action, or a log action with category/tags presence.",
                    }
                )
            if not issues:
                issues.append(
                    {
                        "code": "no_qualifying_trigger",
                        "message": "No single trigger satisfies mode, active, camera, group, and Presence action together.",
                        "hint": "Ensure one active ppl_match or vprofile_match trigger has camera(s), group(s), and a Presence action.",
                    }
                )

    return {
        "ready": bool(qualifying),
        "qualifying_triggers": qualifying,
        "issues": issues,
        "evaluated_trigger_count": len(scored),
    }


def first_qualifying_camera_id(report: Dict[str, Any]) -> Optional[str]:
    for trigger in report.get("qualifying_triggers") or []:
        cameras = trigger.get("camera_ids") or []
        if cameras:
            return str(cameras[0])
    return None


def first_qualifying_group_id(report: Dict[str, Any]) -> Optional[str]:
    for trigger in report.get("qualifying_triggers") or []:
        groups = trigger.get("group_ids") or []
        if groups:
            return str(groups[0])
    return None

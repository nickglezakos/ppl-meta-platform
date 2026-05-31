from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from urllib import error, parse, request


BASE_URL = os.getenv("PRESENCE_VALIDATION_BASE_URL", "http://localhost:8011/api/v1/presence")
LOGIN_URL = os.getenv("PRESENCE_VALIDATION_LOGIN_URL", "http://localhost:8001/api/v1/users/login")
GATEWAY_URL = os.getenv("PRESENCE_VALIDATION_GATEWAY_URL", "http://localhost:8080/api/v1")
USERNAME = os.getenv("PRESENCE_VALIDATION_USERNAME")
PASSWORD = os.getenv("PRESENCE_VALIDATION_PASSWORD")
DEVICE_UUID = os.getenv("PRESENCE_VALIDATION_DEVICE_UUID", "presence-validation-device")
INSTALLATION_UUID = os.getenv("PRESENCE_VALIDATION_INSTALLATION_UUID", "local-installation")
POLL_SECONDS = float(os.getenv("PRESENCE_VALIDATION_POLL_SECONDS", "1.0"))
MAX_POLLS = int(os.getenv("PRESENCE_VALIDATION_MAX_POLLS", "20"))
SKIP_COMPLETION = os.getenv("PRESENCE_VALIDATION_SKIP_COMPLETION", "0") == "1"
EXPECT_CONFIRMATION = os.getenv("PRESENCE_VALIDATION_EXPECT_CONFIRMATION", "0") == "1"
FORCE_EMPTY_GROUP = os.getenv("PRESENCE_VALIDATION_FORCE_EMPTY_GROUP", "0") == "1"


@dataclass
class ValidationContext:
    token: str
    session_id: str
    qr_token: str


def presence_group_name(user_uuid: str) -> str:
    return f"Presence Individuals {user_uuid}"


def presence_action_name(user_uuid: str) -> str:
    return f"Presence Action {user_uuid}"


def presence_trigger_name(user_uuid: str) -> str:
    return f"Presence Trigger {user_uuid}"


def list_gateway_items(token: str, path: str) -> list[dict]:
    status, payload = http_json(f"{GATEWAY_URL}{path}", token=token)
    if status != 200:
        fail(f"Gateway list failed for {path}: HTTP {status} {json.dumps(payload)}")

    if isinstance(payload, dict):
        for key in ("groups", "actions", "triggers", "members"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def gateway_json(token: str, path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    status, response = http_json(f"{GATEWAY_URL}{path}", method=method, token=token, payload=payload)
    if status not in (200, 201):
        fail(f"Gateway request failed for {path}: HTTP {status} {json.dumps(response)}")
    return response


def find_presence_assets(token: str, user_uuid: str) -> dict[str, dict | None]:
    expected_group_name = presence_group_name(user_uuid)
    expected_action_name = presence_action_name(user_uuid)
    expected_trigger_name = presence_trigger_name(user_uuid)

    groups = list_gateway_items(token, "/individual-groups")
    actions = list_gateway_items(token, "/user-actions")
    triggers = list_gateway_items(token, "/triggers")

    return {
        "group": next((group for group in groups if group.get("name") == expected_group_name), None),
        "action": next((action for action in actions if action.get("name") == expected_action_name), None),
        "trigger": next((trigger for trigger in triggers if trigger.get("name") == expected_trigger_name), None),
    }


def clear_presence_group_members(token: str, group_id: str) -> list[dict]:
    members = list_gateway_items(token, f"/individual-groups/{group_id}/members")
    if not members:
        return []

    member_ids = [member.get("id") for member in members if member.get("id")]
    if not member_ids:
        return members

    gateway_json(
        token,
        f"/individual-groups/{group_id}/members",
        method="DELETE",
        payload={"individual_ids": member_ids},
    )
    return members


def fail(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def http_json(url: str, *, method: str = "GET", token: str | None = None, payload: dict | None = None, form: dict | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    data = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = parse.urlencode(form).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed


def login() -> str:
    if not USERNAME or not PASSWORD:
        fail(
            "Set PRESENCE_VALIDATION_USERNAME and PRESENCE_VALIDATION_PASSWORD before running validation.",
        )

    status, payload = http_json(
        LOGIN_URL,
        method="POST",
        form={"username": USERNAME, "password": PASSWORD},
    )
    if status != 200:
        fail(f"Login failed: HTTP {status} {json.dumps(payload)}")

    token = payload.get("access_token")
    if not token:
        fail(f"Login response did not include access_token: {json.dumps(payload)}")
    return token


def create_session(token: str) -> tuple[str, dict]:
    status, payload = http_json(
        f"{BASE_URL}/mobile/sessions",
        method="POST",
        token=token,
        payload={
            "device_uuid": DEVICE_UUID,
            "device_name": "Presence Validation Device",
            "device_platform": "android",
            "app_version": "0.1.0",
        },
    )
    if status != 200:
        fail(f"Session creation failed: HTTP {status} {json.dumps(payload)}")
    return payload["data"]["session_uuid"], payload


def render_qr(token: str) -> tuple[str, dict]:
    status, payload = http_json(
        f"{BASE_URL}/qr/render",
        method="POST",
        token=token,
        payload={
            "installation_uuid": INSTALLATION_UUID,
            "device_reference": DEVICE_UUID,
        },
    )
    if status != 200:
        fail(f"QR render failed: HTTP {status} {json.dumps(payload)}")
    return payload["data"]["qr_token"], payload


def validate_qr(token: str, qr_token: str, expected_session_id: str) -> None:
    status, payload = http_json(
        f"{BASE_URL}/qr/validate",
        method="POST",
        token=token,
        payload={"qr_token": qr_token},
    )
    if status != 200 or not payload["data"].get("valid"):
        fail(f"QR validate failed: HTTP {status} {json.dumps(payload)}")
    if payload["data"].get("session_uuid") != expected_session_id:
        fail(f"QR validate returned wrong session: {json.dumps(payload)}")


def upload_burst(token: str, session_id: str) -> None:
    status, payload = http_json(
        f"{BASE_URL}/mobile/sessions/{session_id}/feeds/front-burst",
        method="POST",
        token=token,
        payload={
            "device_id": DEVICE_UUID,
            "session_uuid": session_id,
            "capture_phase": "initial",
            "frames": [
                {
                    "frame_data": "ZmFrZV9mcmFtZQ==",
                    "timestamp": 1717070000.0,
                    "width": 720,
                    "height": 1280,
                    "format": "jpeg",
                    "orientation": "portrait",
                    "rotation_angle": 0,
                    "fps": 15,
                    "camera_facing": "front",
                }
            ],
            "captured_at": "2026-05-30T14:55:00Z",
            "transport_source": "mobile_app",
        },
    )
    if status != 200:
        fail(f"Front burst failed: HTTP {status} {json.dumps(payload)}")


def qr_hit(token: str, session_id: str, qr_token: str) -> None:
    status, payload = http_json(
        f"{BASE_URL}/mobile/sessions/{session_id}/qr-hit",
        method="POST",
        token=token,
        payload={
            "qr_token": qr_token,
            "installation_uuid": INSTALLATION_UUID,
            "scanned_at": "2026-05-30T14:55:05Z",
        },
    )
    if status != 200:
        fail(f"QR hit failed: HTTP {status} {json.dumps(payload)}")


def wait_for_completed_result(token: str, session_id: str) -> tuple[dict, list[dict], list[dict]]:
    last_detection_payload: dict | None = None
    last_result_payload: dict | None = None
    detection_history: list[dict] = []
    result_history: list[dict] = []

    for _ in range(MAX_POLLS):
        detection_status, detection_payload = http_json(
            f"{BASE_URL}/mobile/sessions/{session_id}/instant-detection-status",
            token=token,
        )
        if detection_status != 200:
            fail(f"Detection status failed: HTTP {detection_status} {json.dumps(detection_payload)}")
        last_detection_payload = detection_payload
        detection_history.append(detection_payload.get("data") or {})

        result_status, result_payload = http_json(
            f"{BASE_URL}/mobile/sessions/{session_id}/result",
            token=token,
        )
        if result_status != 200:
            fail(f"Result fetch failed: HTTP {result_status} {json.dumps(result_payload)}")
        last_result_payload = result_payload
        result_history.append(result_payload.get("data") or {})

        data = result_payload["data"]
        if data.get("status") == "completed" and data.get("decision") == "granted":
            if data.get("reason_code") != "presence_ppl_match":
                fail(f"Presence flow completed with unexpected reason_code: {json.dumps(result_payload)}")
            if data.get("policy_source") != "platform_trigger":
                fail(f"Presence flow completed without platform trigger provenance: {json.dumps(result_payload)}")
            if EXPECT_CONFIRMATION:
                confirmation_seen = any(
                    (entry.get("latest_attempt_index") or 0) >= 2
                    or entry.get("instant_detection_status") in {"started", "completed"} and (entry.get("latest_attempt_index") or 0) >= 2
                    for entry in detection_history
                )
                if not confirmation_seen:
                    fail(
                        "Presence flow completed without observing a confirmation attempt: "
                        f"detection_history={json.dumps(detection_history)} result_history={json.dumps(result_history)}"
                    )
            return data, detection_history, result_history

        time.sleep(POLL_SECONDS)

    fail(
        "Presence flow did not complete after polling: "
        f"detection={json.dumps(last_detection_payload)} result={json.dumps(last_result_payload)}"
    )


def assert_trace(token: str, session_id: str) -> dict:
    status, payload = http_json(
        f"{BASE_URL}/mobile/sessions/{session_id}/trace",
        token=token,
    )
    if status != 200:
        fail(f"Trace fetch failed: HTTP {status} {json.dumps(payload)}")

    data = payload["data"]
    session = data.get("session") or {}
    action_plan = data.get("action_plan") or {}
    decision_history = data.get("decision_history") or []

    if SKIP_COMPLETION:
        if session.get("session_uuid") != session_id:
            fail(f"Trace did not return the requested session: {json.dumps(payload)}")
    else:
        if session.get("status") != "completed" or session.get("decision") != "granted":
            fail(f"Trace session did not reflect completion: {json.dumps(payload)}")
        if session.get("policy_source") != "platform_trigger":
            fail(f"Trace session did not preserve platform_trigger provenance: {json.dumps(payload)}")
        if not decision_history:
            fail(f"Trace did not include decision history: {json.dumps(payload)}")
        if action_plan.get("decision") != "granted":
            fail(f"Trace action plan did not reflect granted decision: {json.dumps(payload)}")
        if not any(item.get("reason_code") == "presence_ppl_match" for item in decision_history):
            fail(f"Trace decision history did not include trigger-backed presence grant: {json.dumps(payload)}")
    return data


def assert_decision_history_query(token: str, session_id: str) -> list[dict]:
    status, payload = http_json(
        f"{BASE_URL}/decision-history?session_uuid={parse.quote(session_id)}&limit=5",
        token=token,
    )
    if status != 200:
        fail(f"Decision history query failed: HTTP {status} {json.dumps(payload)}")

    data = payload["data"]
    items = data.get("items", [])
    if not isinstance(items, list):
        fail(f"Decision history query returned invalid payload: {json.dumps(payload)}")
    if data.get("returned") != len(items):
        fail(f"Decision history query returned inconsistent metadata: {json.dumps(payload)}")
    if data.get("total", 0) < len(items):
        fail(f"Decision history query total was smaller than returned items: {json.dumps(payload)}")
    if not SKIP_COMPLETION and not items:
        fail(f"Decision history query returned no items for completed session: {json.dumps(payload)}")
    if any(item.get("session_uuid") != session_id for item in items):
        fail(f"Decision history query returned wrong session rows: {json.dumps(payload)}")
    return items


def assert_session_trace_query(token: str, session_id: str, policy_source: str | None = None) -> list[dict]:
    query = [f"session_uuid={parse.quote(session_id)}", "limit=5"]
    if policy_source:
        query.append(f"policy_source={parse.quote(policy_source)}")
    status, payload = http_json(
        f"{BASE_URL}/mobile/session-traces?{'&'.join(query)}",
        token=token,
    )
    if status != 200:
        fail(f"Session trace query failed: HTTP {status} {json.dumps(payload)}")

    data = payload["data"]
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        fail(f"Session trace query returned no items: {json.dumps(payload)}")
    if data.get("returned") != len(items):
        fail(f"Session trace query returned inconsistent metadata: {json.dumps(payload)}")
    if data.get("total", 0) < len(items):
        fail(f"Session trace query total was smaller than returned items: {json.dumps(payload)}")
    if any((item.get("session") or {}).get("session_uuid") != session_id for item in items):
        fail(f"Session trace query returned wrong sessions: {json.dumps(payload)}")
    return items


def assert_analytics_summary(token: str) -> dict:
    status, payload = http_json(f"{BASE_URL}/analytics/summary", token=token)
    if status != 200:
        fail(f"Analytics summary failed: HTTP {status} {json.dumps(payload)}")
    if payload["data"].get("granted", 0) < 1:
        fail(f"Analytics summary did not record granted flow: {json.dumps(payload)}")
    return payload["data"]


def assert_policy_source_analytics(token: str) -> list[dict]:
    status, payload = http_json(f"{BASE_URL}/analytics/by-policy-source", token=token)
    if status != 200:
        fail(f"Policy source analytics failed: HTTP {status} {json.dumps(payload)}")

    items = payload["data"].get("items", [])
    if not isinstance(items, list) or not items:
        fail(f"Policy source analytics returned no items: {json.dumps(payload)}")
    if SKIP_COMPLETION:
        return items
    if not any(item.get("policy_source") == "platform_trigger" for item in items):
        fail(f"Policy source analytics did not include platform_trigger rows: {json.dumps(payload)}")
    return items


def main() -> None:
    token = login()
    session_id, session_payload = create_session(token)
    qr_payload: dict = {}
    result: dict | None = None
    detection_history: list[dict] = []
    result_history: list[dict] = []
    assets_before = find_presence_assets(token, session_payload["data"]["user_uuid"])
    cleared_members: list[dict] = []

    if FORCE_EMPTY_GROUP and assets_before.get("group") and assets_before["group"].get("id"):
        cleared_members = clear_presence_group_members(token, assets_before["group"]["id"])

    if not SKIP_COMPLETION:
        qr_token, qr_payload = render_qr(token)
        validate_qr(token, qr_token, session_id)
        upload_burst(token, session_id)
        qr_hit(token, session_id, qr_token)
        result, detection_history, result_history = wait_for_completed_result(token, session_id)

    trace = assert_trace(token, session_id)
    decision_history_query = assert_decision_history_query(token, session_id)
    trace_query = assert_session_trace_query(token, session_id, trace.get("session", {}).get("policy_source"))
    analytics = assert_analytics_summary(token)
    policy_source_analytics = assert_policy_source_analytics(token)
    assets_after = find_presence_assets(token, session_payload["data"]["user_uuid"])

    print(json.dumps(
        {
            "session": session_payload["data"],
            "qr": qr_payload.get("data"),
            "result": result,
            "detection_history": detection_history,
            "result_history": result_history,
            "assets_before": assets_before,
            "cleared_group_members": cleared_members,
            "assets_after": assets_after,
            "trace": trace,
            "decision_history_query": decision_history_query,
            "session_trace_query": trace_query,
            "analytics_summary": analytics,
            "analytics_by_policy_source": policy_source_analytics,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()

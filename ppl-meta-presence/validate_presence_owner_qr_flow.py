from __future__ import annotations

import json
import os
import sys
from urllib import error, parse, request


BASE_URL = os.getenv("PRESENCE_VALIDATION_BASE_URL", "http://localhost:8011/api/v1/presence")
LOGIN_URL = os.getenv("PRESENCE_VALIDATION_LOGIN_URL", "http://localhost:8001/api/v1/users/login")
USERNAME = os.getenv("PRESENCE_VALIDATION_USERNAME")
PASSWORD = os.getenv("PRESENCE_VALIDATION_PASSWORD")
TOKEN = os.getenv("PRESENCE_VALIDATION_TOKEN")
DEVICE_UUID = os.getenv("PRESENCE_VALIDATION_DEVICE_UUID", "presence-owner-qr-validator")
INSTALLATION_UUID = os.getenv("PRESENCE_VALIDATION_INSTALLATION_UUID", "local-installation")


def fail(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def http_json(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
    form: dict | None = None,
) -> tuple[int, dict]:
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
    if TOKEN:
        return TOKEN
    if not USERNAME or not PASSWORD:
        fail(
            "Set PRESENCE_VALIDATION_TOKEN or PRESENCE_VALIDATION_USERNAME and PRESENCE_VALIDATION_PASSWORD before running validation.",
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


def api_json(token: str, path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    status, response = http_json(
        f"{BASE_URL}{path}",
        method=method,
        token=token,
        payload=payload,
    )
    if status not in (200, 201):
        fail(f"Presence request failed for {path}: HTTP {status} {json.dumps(response)}")
    if not response.get("success"):
        fail(f"Presence request returned unsuccessful payload for {path}: {json.dumps(response)}")
    data = response.get("data")
    if not isinstance(data, dict):
        fail(f"Presence request returned unexpected data for {path}: {json.dumps(response)}")
    return data


def main() -> None:
    token = login()
    session = api_json(
        token,
        "/mobile/sessions",
        method="POST",
        payload={
            "session_mode": "qr_only",
            "device_uuid": DEVICE_UUID,
            "device_name": "Presence Owner QR Validator",
            "device_platform": "script",
            "app_version": "owner-qr-validation",
        },
    )
    session_uuid = session.get("session_uuid")
    if not session_uuid:
        fail(f"Session creation did not return session_uuid: {json.dumps(session)}")

    owner_qr = api_json(
        token,
        "/qr/render-owner",
        method="POST",
        payload={
            "installation_uuid": INSTALLATION_UUID,
            "owner_display_name": "Presence Owner QR Validator",
        },
    )
    owner_payload = owner_qr.get("payload")
    if not isinstance(owner_payload, dict):
        fail(f"Owner QR render did not return payload: {json.dumps(owner_qr)}")
    if owner_payload.get("qr_type") != "owner_identity":
        fail(f"Owner QR render returned wrong qr_type: {json.dumps(owner_payload)}")

    updated_session = api_json(
        token,
        f"/mobile/sessions/{session_uuid}/owner-qr-hit",
        method="POST",
        payload={
            "qr_payload": owner_payload,
            "installation_uuid": INSTALLATION_UUID,
            "scanned_at": owner_payload.get("issued_at"),
        },
    )
    if updated_session.get("decision") != "granted":
        fail(f"Owner QR hit did not grant immediately: {json.dumps(updated_session)}")
    if updated_session.get("status") != "completed":
        fail(f"Owner QR hit did not complete session: {json.dumps(updated_session)}")

    result = api_json(token, f"/mobile/sessions/{session_uuid}/result")
    if result.get("decision") != "granted":
        fail(f"Owner QR result was not granted: {json.dumps(result)}")
    if result.get("status") != "completed":
        fail(f"Owner QR result was not completed: {json.dumps(result)}")

    print(
        json.dumps(
            {
                "session_uuid": session_uuid,
                "result": result,
                "owner": owner_payload.get("owner"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
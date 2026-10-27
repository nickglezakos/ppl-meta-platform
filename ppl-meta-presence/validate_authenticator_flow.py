#!/usr/bin/env python3
"""Validate authenticator enroll → verify → grant without cameras/mobile registration.

Env:
  PRESENCE_VALIDATION_BASE_URL   default http://localhost:8080/api/v1/presence
  PRESENCE_VALIDATION_LOGIN_URL  default http://localhost:8080/api/v1/users/login
  PRESENCE_VALIDATION_USERNAME / PASSWORD or PRESENCE_VALIDATION_TOKEN
  PRESENCE_VALIDATION_FACE_IMAGE path to a JPEG/PNG face crop (required for live ML)
  PRESENCE_VALIDATION_SKIP_ML=1  smoke-test session create only (no enroll/verify)
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib import error, parse, request


BASE_URL = os.getenv(
    "PRESENCE_VALIDATION_BASE_URL",
    "http://localhost:8080/api/v1/presence",
).rstrip("/")
LOGIN_URL = os.getenv(
    "PRESENCE_VALIDATION_LOGIN_URL",
    "http://localhost:8080/api/v1/users/login",
)
USERNAME = os.getenv("PRESENCE_VALIDATION_USERNAME")
PASSWORD = os.getenv("PRESENCE_VALIDATION_PASSWORD")
TOKEN = os.getenv("PRESENCE_VALIDATION_TOKEN")
FACE_IMAGE = os.getenv("PRESENCE_VALIDATION_FACE_IMAGE")
SKIP_ML = os.getenv("PRESENCE_VALIDATION_SKIP_ML", "").lower() in {"1", "true", "yes"}
DEVICE_UUID = os.getenv(
    "PRESENCE_VALIDATION_DEVICE_UUID",
    f"authenticator-soft-{uuid.uuid4()}",
)


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
        with request.urlopen(req, timeout=90) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed


def http_multipart(
    url: str,
    *,
    token: str,
    file_path: Path,
    field_name: str = "file",
    query: dict | None = None,
) -> tuple[int, dict]:
    boundary = f"----AuthBoundary{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(str(file_path))[0] or "image/jpeg"
    raw = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{file_path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode(),
        raw,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=90) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {"detail": payload}
        return exc.code, parsed


def login() -> str:
    if TOKEN:
        return TOKEN
    if not USERNAME or not PASSWORD:
        fail("Set PRESENCE_VALIDATION_TOKEN or USERNAME/PASSWORD")
    status, payload = http_json(
        LOGIN_URL,
        method="POST",
        form={"username": USERNAME, "password": PASSWORD},
    )
    if status != 200:
        fail(f"Login failed: HTTP {status} {json.dumps(payload)}")
    token = payload.get("access_token")
    if not token:
        fail("No access_token in login response")
    return token


def main() -> None:
    token = login()
    print(f"OK login soft_device={DEVICE_UUID}")

    # Soft device session create must not require cameras/mobile registration.
    status, payload = http_json(
        f"{BASE_URL}/mobile/sessions",
        method="POST",
        token=token,
        payload={
            "session_mode": "camera_only",
            "device_uuid": DEVICE_UUID,
            "device_name": "Authenticator Validator",
            "device_platform": "validation",
            "app_version": "ppl-meta-authenticator/validate",
            "client_origin": "authenticator",
        },
    )
    if status != 200 or not payload.get("success"):
        fail(f"create_session failed: HTTP {status} {json.dumps(payload)}")
    session = payload["data"]
    if session.get("resolved_camera_uuid"):
        fail("Authenticator session unexpectedly bound a platform camera")
    if session.get("detection_status") != "awaiting_authenticator_verify":
        fail(f"Unexpected detection_status: {session.get('detection_status')}")
    session_uuid = session["session_uuid"]
    print(f"OK create_session session={session_uuid} (no camera registration)")

    status, payload = http_json(
        f"{BASE_URL}/authenticator/enrollment",
        token=token,
    )
    if status != 200:
        fail(f"enrollment GET failed: HTTP {status} {json.dumps(payload)}")
    print(f"OK enrollment GET enrolled={payload.get('data', {}).get('enrolled')}")

    if SKIP_ML:
        print("SKIP_ML set — skipping enroll/verify against vmeta")
        print("PASS authenticator smoke (session create + enrollment GET)")
        return

    if not FACE_IMAGE:
        fail("Set PRESENCE_VALIDATION_FACE_IMAGE to a face JPEG/PNG, or SKIP_ML=1")
    face_path = Path(FACE_IMAGE)
    if not face_path.is_file():
        fail(f"Face image not found: {face_path}")

    status, payload = http_multipart(
        f"{BASE_URL}/authenticator/enroll-face",
        token=token,
        file_path=face_path,
    )
    if status != 200 or not payload.get("success"):
        fail(f"enroll-face failed: HTTP {status} {json.dumps(payload)}")
    mvr = payload["data"]["mvr_people_uuid"]
    print(f"OK enroll-face mvr={mvr}")

    status, payload = http_multipart(
        f"{BASE_URL}/authenticator/verify-face",
        token=token,
        file_path=face_path,
        query={"session_uuid": session_uuid},
    )
    if status != 200 or not payload.get("success"):
        fail(f"verify-face failed: HTTP {status} {json.dumps(payload)}")
    data = payload["data"]
    if not data.get("verified"):
        fail(f"verify-face not verified: {json.dumps(data)}")
    if data.get("decision") != "granted":
        fail(f"expected granted decision, got {data.get('decision')}")
    print(f"OK verify-face granted score={data.get('similarity_score')}")

    status, payload = http_json(
        f"{BASE_URL}/mobile/sessions/{session_uuid}/result",
        token=token,
    )
    if status != 200 or not payload.get("success"):
        fail(f"result failed: HTTP {status} {json.dumps(payload)}")
    result = payload["data"]
    if result.get("decision") != "granted":
        fail(f"result not granted: {json.dumps(result)}")
    print("PASS authenticator enroll → verify → grant (no cameras/mobile)")


if __name__ == "__main__":
    main()

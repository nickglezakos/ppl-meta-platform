"""Tests for the HMAC installation-token auth path (Issue #8).

Run from the repository root:

    cd ppl-meta-discovery
    python -m pip install -r requirements.txt -r requirements-dev.txt
    python -m pytest tests -v

The middleware round-trip tests use Starlette's TestClient and are skipped
automatically if ``httpx`` is not installed.
"""

import hashlib
import hmac

import pytest
from auth import (
    INTERNAL_SERVICE_TOKEN,
    KNOWN_SERVICES,
    _extract_bearer,
    _is_exempt_readonly,
    _is_protected_path,
    _is_valid_service_request,
    compute_installation_token,
)


# --------------------------------------------------------------------------- #
# Pure functions
# --------------------------------------------------------------------------- #
def test_compute_installation_token_is_hmac_sha256_hex():
    secret = "test-secret"
    installation_uuid = "installation-abc"
    token = compute_installation_token(installation_uuid, secret=secret)
    expected = hmac.new(
        secret.encode("utf-8"),
        installation_uuid.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert token == expected
    assert len(token) == 64  # SHA-256 hex digest


def test_compute_installation_token_deterministic_and_per_uuid():
    secret = "test-secret"
    assert compute_installation_token("u1", secret) == compute_installation_token(
        "u1", secret
    )
    assert compute_installation_token("u1", secret) != compute_installation_token(
        "u2", secret
    )


def test_extract_bearer():
    assert _extract_bearer("Bearer abc123") == "abc123"
    assert _extract_bearer("bearer abc") == "abc"  # case-insensitive
    assert _extract_bearer("Bearer   spaced") == "spaced"
    assert _extract_bearer("") == ""
    assert _extract_bearer("abc") == "abc"  # no scheme -> returned as-is


def test_is_protected_path():
    protected = [
        "/api/v1/services",
        "/api/v1/services/register",
        "/api/v1/services/heartbeat",
        "/api/v1/devices",
        "/api/v1/devices/register",
        "/api/v1/devices/heartbeat",
        "/api/v1/discovery/topology",
    ]
    for path in protected:
        assert _is_protected_path(path), path

    open_paths = [
        "/health",
        "/api/v1/discovery/capabilities",
        "/api/v1/platform/metadata",
        "/api/v1/discovery/status",
    ]
    for path in open_paths:
        assert not _is_protected_path(path), path


# --------------------------------------------------------------------------- #
# Middleware enforcement
# --------------------------------------------------------------------------- #
class _FakeSettings:
    def __init__(self, enforce: bool, secret: str):
        self.AUTH_ENFORCE = enforce
        self.INSTALLATION_AUTH_SECRET = secret


def _make_echo_app():
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def ok(_request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/v1/services/register", ok, methods=["POST"])])
    from auth import InstallationAuthMiddleware

    app.add_middleware(InstallationAuthMiddleware)
    return app


def _client():
    pytest.importorskip("starlette")
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient

    return TestClient(_make_echo_app())


def test_middleware_rejects_missing_or_bad_token(monkeypatch):
    monkeypatch.setattr(
        "auth.get_settings", lambda: _FakeSettings(True, "test-secret")
    )
    client = _client()

    resp = client.post("/api/v1/services/register", json={})
    assert resp.status_code == 401

    resp = client.post(
        "/api/v1/services/register",
        json={},
        headers={"X-Installation-Uuid": "installation-abc"},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/api/v1/services/register",
        json={},
        headers={
            "Authorization": "Bearer wrong-token",
            "X-Installation-Uuid": "installation-abc",
        },
    )
    assert resp.status_code == 401


def test_middleware_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(
        "auth.get_settings", lambda: _FakeSettings(True, "test-secret")
    )
    client = _client()

    installation_uuid = "installation-abc"
    token = compute_installation_token(installation_uuid, secret="test-secret")
    resp = client.post(
        "/api/v1/services/register",
        json={},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Installation-Uuid": installation_uuid,
        },
    )
    assert resp.status_code == 200


def test_middleware_allows_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "auth.get_settings", lambda: _FakeSettings(False, "test-secret")
    )
    client = _client()

    resp = client.post("/api/v1/services/register", json={})
def test_is_valid_service_request():
    token = INTERNAL_SERVICE_TOKEN
    assert _is_valid_service_request(f"Bearer {token}", "ppl-meta-gateway")
    assert _is_valid_service_request(token, "ppl-meta-cameras")
    assert not _is_valid_service_request("Bearer wrong-token", "ppl-meta-gateway")
    assert not _is_valid_service_request(f"Bearer {token}", "unknown-service")
    assert not _is_valid_service_request(f"Bearer {token}", "")


def test_middleware_accepts_service_token(monkeypatch):
    monkeypatch.setattr(
        "auth.get_settings", lambda: _FakeSettings(True, "test-secret")
    )
    client = _client()

    resp = client.post(
        "/api/v1/services/register",
        json={},
        headers={
            "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
            "X-Service-Name": "ppl-meta-gateway",
        },
    )
    assert resp.status_code == 200


def test_middleware_rejects_unknown_service_name(monkeypatch):
    monkeypatch.setattr(
        "auth.get_settings", lambda: _FakeSettings(True, "test-secret")
    )
    client = _client()

    resp = client.post(
        "/api/v1/services/register",
        json={},
        headers={
            "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
            "X-Service-Name": "not-a-known-service",
        },
    )
    assert resp.status_code == 401


def test_is_exempt_readonly():
    import auth

    class _Req:
        def __init__(self, method, path):
            self._m = method
            self._p = path

        @property
        def method(self):
            return self._m

        @property
        def url(self):
            return type("U", (), {"path": self._p})()

    assert auth._is_exempt_readonly(_Req("GET", "/api/v1/services"))
    assert not auth._is_exempt_readonly(_Req("POST", "/api/v1/services/register"))
    assert not auth._is_exempt_readonly(_Req("GET", "/api/v1/services/some-id"))
    assert not auth._is_exempt_readonly(_Req("GET", "/api/v1/devices"))


def test_middleware_allows_readonly_service_list_without_token(monkeypatch):
    monkeypatch.setattr(
        "auth.get_settings", lambda: _FakeSettings(True, "test-secret")
    )
    pytest.importorskip("starlette")
    pytest.importorskip("httpx")
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def ok(_request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/v1/services", ok, methods=["GET"])])
    from auth import InstallationAuthMiddleware

    app.add_middleware(InstallationAuthMiddleware)
    client = TestClient(app)

    # No token but a read-only GET to the service list is exempt.
    resp = client.get("/api/v1/services")
    assert resp.status_code == 200
    assert resp.status_code == 200  # no auth required when AUTH_ENFORCE is off
"""Token authentication for registration/heartbeat/topology (Issue #8).

Two credential types are accepted on the protected endpoints:

1. HMAC-SHA256 installation token (edge installations):
       api_token = HMAC_SHA256(INSTALLATION_AUTH_SECRET, installation_uuid)
   Issued by the Authority during VPN enrollment. Sent as
   ``Authorization: Bearer <api_token>`` + ``X-Installation-Uuid``.

2. Internal service token (platform backend services):
   A shared bearer token (``INTERNAL_SERVICE_TOKEN``) plus an ``X-Service-Name``
   in ``KNOWN_SERVICES`` — mirrors ``shared/auth/service_auth.py`` so existing
   service-to-service registration/heartbeat keeps working when enforcement is on.

The read-only ``GET /api/v1/services`` directory listing is **exempt** from auth so
the browser frontend dashboard can query it without exposing a secret.

Enforcement is gated behind ``AUTH_ENFORCE`` (defaults to false) so the rollout
does not break existing clients before they ship tokens.
"""

import hashlib
import hmac
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import get_settings

# Internal service token — mirrors shared/auth/service_auth.py and must match
# INTERNAL_SERVICE_TOKEN used by the platform backend services.
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "ppl-meta-internal-service-secret-key-change-in-production",
)

KNOWN_SERVICES = {
    "ppl-meta-media",
    "ppl-meta-cameras",
    "ppl-meta-orchestrator",
    "ppl-meta-gateway",
    "ppl-meta-node",
    "ppl-meta-vision",
    "ppl-meta-vmeta",
    "ppl-meta-discovery",
    "ppl-meta-bootcore",
    "ppl-meta-presence",
}


def compute_installation_token(installation_uuid: str, secret: str | None = None) -> str:
    """Return the expected HMAC token for an installation UUID."""
    key = (secret or get_settings().INSTALLATION_AUTH_SECRET).encode("utf-8")
    return hmac.new(key, str(installation_uuid).encode("utf-8"), hashlib.sha256).hexdigest()


def _extract_bearer(authorization: str) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return (authorization or "").strip()


def _is_valid_service_request(authorization: str, service_name: str) -> bool:
    """True if the request carries a valid internal service token (Issue #8 / Group 2)."""
    if service_name not in KNOWN_SERVICES:
        return False
    return hmac.compare_digest(_extract_bearer(authorization), INTERNAL_SERVICE_TOKEN)


def _is_protected_path(path: str) -> bool:
    return (
        path == "/api/v1/services"
        or path.startswith("/api/v1/services/")
        or path == "/api/v1/devices"
        or path.startswith("/api/v1/devices/")
        or path == "/api/v1/discovery/topology"
    )


def _is_exempt_readonly(request: Request) -> bool:
    """Read-only directory listing that browser clients (frontend) may access
    without a token. A discovery service list is meant to be queried; the
    mutating/identity endpoints and topology remain protected.
    """
    return request.method.upper() == "GET" and request.url.path == "/api/v1/services"


class InstallationAuthMiddleware(BaseHTTPMiddleware):
    """Enforce service/installation-token auth on protected paths when AUTH_ENFORCE is set."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if (
            settings.AUTH_ENFORCE
            and _is_protected_path(request.url.path)
            and not _is_exempt_readonly(request)
        ):
            authorization = request.headers.get("Authorization", "")
            service_name = request.headers.get("X-Service-Name", "")
            installation_uuid = request.headers.get("X-Installation-Uuid", "")

            # Platform backend services authenticate with the internal service token.
            service_ok = _is_valid_service_request(authorization, service_name)

            # Edge installations authenticate with the HMAC installation token.
            expected = compute_installation_token(
                installation_uuid, settings.INSTALLATION_AUTH_SECRET
            )
            install_ok = bool(installation_uuid) and hmac.compare_digest(
                _extract_bearer(authorization), expected
            )

            if not (service_ok or install_ok):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized - no valid service or installation token"},
                )
        return await call_next(request)
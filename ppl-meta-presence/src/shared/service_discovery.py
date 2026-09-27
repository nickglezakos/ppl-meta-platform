"""
PPL Meta Discovery Service integration for ppl-meta-presence.
Aligned with the working gateway client (HTTP register to ppl-meta-discovery).
"""

import logging
import os
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

DISCOVERY_SERVICE_URL = os.getenv(
    "DISCOVERY_SERVICE_URL", "http://ppl-meta-discovery:8006"
).rstrip("/")

INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "ppl-meta-internal-service-secret-key-change-in-production",
)
_SERVICE_NAME = "ppl-meta-presence"


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "X-Service-Name": _SERVICE_NAME,
    }


async def _make_discovery_request(method: str, endpoint: str, **kwargs) -> dict:
    if not httpx:
        logger.error("httpx not available, using stub implementation")
        return {"success": False}

    try:
        url = f"{DISCOVERY_SERVICE_URL}{endpoint}"
        merged = {
            **kwargs,
            "headers": {**_auth_headers(), **(kwargs.get("headers") or {})},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.request(method, url, **merged)
            if response.status_code < 400:
                try:
                    return response.json()
                except Exception:
                    return {"success": True}
            logger.error(
                "Discovery service request failed: %s - %s",
                response.status_code,
                getattr(response, "text", ""),
            )
            return {"success": False}
    except Exception as e:
        logger.error("Exception contacting discovery service: %s", e)
        return {"success": False}


async def register_service(
    service_name: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    health_endpoint: Optional[str] = None,
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    name: Optional[str] = None,
    service_type: Optional[str] = None,
    version: Optional[str] = None,
    capabilities: Optional[list] = None,
) -> bool:
    """Register with discovery. Accepts gateway-style or package-style kwargs."""
    resolved_name = service_name or name
    if not resolved_name or host is None or port is None:
        raise TypeError(
            "register_service requires service_name/name, host, and port"
        )

    resolved_tags = tags if tags is not None else (capabilities or [])
    resolved_metadata: Dict[str, Any] = dict(metadata or {})
    if version:
        resolved_metadata.setdefault("version", version)
    if service_type:
        resolved_metadata.setdefault("service_type", service_type)

    logger.info("Registering %s with PPL Meta Discovery Service", resolved_name)

    registration_data = {
        "name": resolved_name,
        "service_type": resolved_metadata.get("service_type", "backend"),
        "version": resolved_metadata.get("version", "1.0.0"),
        "host": host,
        "port": port,
        "health_endpoint": health_endpoint or "/health",
        "capabilities": resolved_tags,
        "metadata": resolved_metadata,
    }

    result = await _make_discovery_request(
        "POST", "/api/v1/services/register", json=registration_data
    )

    success = result.get("success", False)
    if success:
        logger.info("Successfully registered %s with discovery service", resolved_name)
    else:
        logger.error("Failed to register %s with discovery service", resolved_name)
    return success


async def deregister_service(
    service_name: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    *,
    name: Optional[str] = None,
) -> bool:
    """Deregister from discovery. Accepts gateway-style or name-only calls."""
    resolved_name = service_name or name
    if not resolved_name:
        raise TypeError("deregister_service requires service_name/name")

    logger.info("Deregistering %s from PPL Meta Discovery Service", resolved_name)

    if host and port:
        service_id = f"{resolved_name}-{host}-{port}"
    else:
        service_id = resolved_name

    result = await _make_discovery_request("DELETE", f"/api/v1/services/{service_id}")

    success = result.get("success", False)
    if success:
        logger.info("Successfully deregistered %s", resolved_name)
    else:
        logger.error("Failed to deregister %s", resolved_name)
    return success


async def start_health_monitoring() -> None:
    logger.info("Health monitoring managed automatically by PPL Discovery Service")


async def cleanup_service_discovery() -> None:
    logger.info("PPL Meta Discovery Service cleanup completed")

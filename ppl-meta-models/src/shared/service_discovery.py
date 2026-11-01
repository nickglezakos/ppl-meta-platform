"""
PPL Meta Discovery Service integration for ppl-meta-models.
Registers with discovery, sends periodic heartbeats, deregisters by UUID.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


def _default_discovery_url() -> str:
    if os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        return "http://ppl-meta-discovery:8006"
    return "http://127.0.0.1:8006"


DISCOVERY_SERVICE_URL = (
    os.getenv("DISCOVERY_SERVICE_URL") or _default_discovery_url()
).rstrip("/")

INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "ppl-meta-internal-service-secret-key-change-in-production",
)
_SERVICE_NAME = "ppl-meta-models"
_HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("DISCOVERY_HEARTBEAT_INTERVAL_SECONDS", "30"))

_discovery_service_id: Optional[str] = None
_last_registration: Optional[Dict[str, Any]] = None
_heartbeat_task: Optional[asyncio.Task] = None
_heartbeat_running = False


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "X-Service-Name": _SERVICE_NAME,
    }


def _deterministic_service_id(name: str) -> str:
    """Match discovery registry: uuid5(NAMESPACE_DNS, name)."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))


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
                    data = response.json()
                    if isinstance(data, dict):
                        data.setdefault("success", True)
                        return data
                    return {"success": True, "data": data}
                except Exception:
                    return {"success": True}
            logger.error(
                "Discovery service request failed: %s - %s",
                response.status_code,
                getattr(response, "text", "")[:300],
            )
            return {"success": False, "status_code": response.status_code}
    except Exception as e:
        logger.error("Exception contacting discovery service: %s", e)
        return {"success": False, "error": str(e)}


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
    global _discovery_service_id, _last_registration

    resolved_name = service_name or name or _SERVICE_NAME
    if host is None or port is None:
        raise TypeError("register_service requires host and port")

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
        "port": int(port),
        "health_endpoint": health_endpoint or "/health",
        "capabilities": resolved_tags,
        "metadata": resolved_metadata,
    }

    _last_registration = {
        "service_name": resolved_name,
        "host": host,
        "port": int(port),
        "health_endpoint": health_endpoint or "/health",
        "tags": list(resolved_tags),
        "metadata": dict(resolved_metadata),
    }

    result = await _make_discovery_request(
        "POST", "/api/v1/services/register", json=registration_data
    )

    success = bool(result.get("success"))
    _discovery_service_id = (
        result.get("service_id") if success else None
    ) or _deterministic_service_id(resolved_name)
    if success:
        logger.info(
            "Successfully registered %s with discovery service (id=%s)",
            resolved_name,
            _discovery_service_id,
        )
    else:
        logger.error("Failed to register %s with discovery service", resolved_name)
    await start_health_monitoring()
    return success


async def deregister_service(
    service_name: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    *,
    name: Optional[str] = None,
) -> bool:
    """Deregister using discovery UUID (uuid5 of name)."""
    global _discovery_service_id

    resolved_name = service_name or name or _SERVICE_NAME
    logger.info("Deregistering %s from PPL Meta Discovery Service", resolved_name)

    await stop_health_monitoring()

    service_id = _discovery_service_id or _deterministic_service_id(resolved_name)
    result = await _make_discovery_request("DELETE", f"/api/v1/services/{service_id}")
    success = bool(result.get("success"))
    if success:
        logger.info("Successfully deregistered %s (%s)", resolved_name, service_id)
        _discovery_service_id = None
    else:
        logger.error("Failed to deregister %s (%s)", resolved_name, service_id)
    return success


async def _send_heartbeat() -> bool:
    global _discovery_service_id
    if not _discovery_service_id and _last_registration:
        _discovery_service_id = _deterministic_service_id(
            _last_registration["service_name"]
        )
    if not _discovery_service_id:
        return False

    payload = {
        "service_id": _discovery_service_id,
        "status": "healthy",
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_name": _SERVICE_NAME,
        },
    }
    result = await _make_discovery_request(
        "POST", "/api/v1/services/heartbeat", json=payload
    )
    if result.get("success"):
        return True

    if not _last_registration:
        return False

    logger.warning(
        "Discovery heartbeat failed for %s — re-registering", _SERVICE_NAME
    )
    reg = dict(_last_registration)
    registration_data = {
        "name": reg["service_name"],
        "service_type": (reg.get("metadata") or {}).get("service_type", "backend"),
        "version": (reg.get("metadata") or {}).get("version", "1.0.0"),
        "host": reg["host"],
        "port": reg["port"],
        "health_endpoint": reg.get("health_endpoint") or "/health",
        "capabilities": reg.get("tags") or [],
        "metadata": reg.get("metadata") or {},
    }
    rereg = await _make_discovery_request(
        "POST", "/api/v1/services/register", json=registration_data
    )
    if not rereg.get("success"):
        return False
    _discovery_service_id = (
        rereg.get("service_id") or _deterministic_service_id(reg["service_name"])
    )
    payload["service_id"] = _discovery_service_id
    retry = await _make_discovery_request(
        "POST", "/api/v1/services/heartbeat", json=payload
    )
    return bool(retry.get("success"))


async def _heartbeat_loop() -> None:
    logger.info(
        "Discovery heartbeat loop started for %s (every %ss)",
        _SERVICE_NAME,
        _HEARTBEAT_INTERVAL_SECONDS,
    )
    while _heartbeat_running:
        try:
            await _send_heartbeat()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Discovery heartbeat error for %s: %s", _SERVICE_NAME, exc)
        try:
            await asyncio.sleep(_HEARTBEAT_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break
    logger.info("Discovery heartbeat loop stopped for %s", _SERVICE_NAME)


async def start_health_monitoring() -> None:
    """Start periodic discovery heartbeats (idempotent)."""
    global _heartbeat_task, _heartbeat_running
    if _heartbeat_running and _heartbeat_task and not _heartbeat_task.done():
        return
    _heartbeat_running = True
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "No running event loop — cannot start discovery heartbeat for %s",
            _SERVICE_NAME,
        )
        _heartbeat_running = False
        return
    _heartbeat_task = loop.create_task(
        _heartbeat_loop(), name=f"discovery-hb-{_SERVICE_NAME}"
    )


async def stop_health_monitoring() -> None:
    global _heartbeat_task, _heartbeat_running
    _heartbeat_running = False
    task = _heartbeat_task
    _heartbeat_task = None
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


async def cleanup_service_discovery() -> None:
    await stop_health_monitoring()
    logger.info("PPL Meta Discovery Service cleanup completed for %s", _SERVICE_NAME)

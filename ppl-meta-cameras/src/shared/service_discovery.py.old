"""
PPL Meta Discovery Service integration for the cameras service.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

# Import httpx for making requests to discovery service
try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# PPL Meta Discovery Service URL
DISCOVERY_SERVICE_URL = "http://localhost:8006"


async def _make_discovery_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make a request to the PPL Meta Discovery Service."""
    if not httpx:
        logger.error("httpx not available, using stub implementation")
        return {"success": False}

    try:
        url = f"{DISCOVERY_SERVICE_URL}{endpoint}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.request(method, url, **kwargs)
            if response.status_code < 400:
                try:
                    return response.json()
                except Exception:
                    return {"success": True}
            else:
                logger.error(
                    f"Discovery service request failed: {response.status_code} - {response.text}"
                )
                return {"success": False}
    except Exception as e:
        logger.error(f"Exception contacting discovery service: {e}")
        return {"success": False}


async def register_service(
    service_name: str,
    host: str,
    port: int,
    health_endpoint: Optional[str] = None,
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Register service with PPL Meta Discovery Service."""
    logger.info(f"Registering {service_name} with PPL Meta Discovery Service")

    # Generate service ID
    service_id = f"{service_name}-{host}-{port}"

    # Prepare registration data
    registration_data = {
        "name": service_name,
        "service_type": "backend",  # All backend services are type "backend"
        "version": metadata.get("version", "1.0.0") if metadata else "1.0.0",
        "host": host,
        "port": port,
        "health_endpoint": health_endpoint or "/health",
        "capabilities": tags or [],
        "metadata": metadata or {},
    }

    result = await _make_discovery_request(
        "POST", "/api/v1/services/register", json=registration_data
    )

    success = result.get("success", False)
    if success:
        logger.info(f"Successfully registered {service_name} with discovery service")
    else:
        logger.error(f"Failed to register {service_name} with discovery service")

    return success


async def deregister_service(
    service_name: str, host: str = None, port: int = None
) -> bool:
    """Deregister service from PPL Meta Discovery Service."""
    logger.info(f"Deregistering {service_name} from PPL Meta Discovery Service")

    # If host and port are provided, generate service ID
    if host and port:
        service_id = f"{service_name}-{host}-{port}"
    else:
        service_id = service_name

    result = await _make_discovery_request("DELETE", f"/api/v1/services/{service_id}")

    success = result.get("success", False)
    if success:
        logger.info(f"Successfully deregistered {service_name}")
    else:
        logger.error(f"Failed to deregister {service_name}")

    return success


async def start_health_monitoring() -> None:
    """Start health monitoring for PPL Meta Discovery Service."""
    logger.info("Health monitoring managed automatically by PPL Discovery Service")
    # Health monitoring is handled by the discovery service itself


async def cleanup_service_discovery() -> None:
    """Cleanup PPL Meta Discovery Service."""
    logger.info("PPL Meta Discovery Service cleanup completed")
    # Cleanup is handled when services are deregistered

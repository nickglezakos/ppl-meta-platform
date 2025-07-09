"""
Local service discovery stub for the gateway service.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def register_service(
    service_name: str,
    service_id: str,
    address: str,
    port: int,
    health_check_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Register service with service discovery (stub implementation)."""
    logger.info(f"Service registration stub: {service_name} at {address}:{port}")
    return True


async def deregister_service(service_id: str) -> bool:
    """Deregister service from service discovery (stub implementation)."""
    logger.info(f"Service deregistration stub: {service_id}")
    return True


async def start_health_monitoring() -> None:
    """Start health monitoring (stub implementation)."""
    logger.info("Health monitoring stub started")


async def cleanup_service_discovery() -> None:
    """Cleanup service discovery (stub implementation)."""
    logger.info("Service discovery cleanup stub")

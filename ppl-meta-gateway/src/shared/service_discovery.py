"""
Local service discovery stub for the gateway service.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def register_service(
    service_name: str,
    host: str,
    port: int,
    health_endpoint: Optional[str] = None,
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Register service with service discovery (stub implementation)."""
    logger.info("Service registration stub: %s at %s:%s", service_name, host, port)
    if health_endpoint:
        logger.info("Health endpoint: %s", health_endpoint)
    if tags:
        logger.info("Tags: %s", tags)
    if metadata:
        logger.info("Metadata: %s", metadata)
    return True


async def deregister_service(service_name: str, host: str, port: int) -> bool:
    """Deregister service from service discovery (stub implementation)."""
    logger.info("Service deregistration stub: %s at %s:%s", service_name, host, port)
    return True


async def start_health_monitoring() -> None:
    """Start health monitoring (stub implementation)."""
    logger.info("Health monitoring stub started")


async def cleanup_service_discovery() -> None:
    """Cleanup service discovery (stub implementation)."""
    logger.info("Service discovery cleanup stub")

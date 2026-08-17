"""
PPL Meta Discovery Service Client

Integration client for connecting backend services to the PPL Meta Discovery Service.
This replaces Consul-based discovery with our own centralized discovery service.
"""

import asyncio
import json
import logging
import os
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Internal service token for service-to-service auth (Issue #8).
# Must match shared/auth/service_auth.py INTERNAL_SERVICE_TOKEN.
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "ppl-meta-internal-service-secret-key-change-in-production",
)


class ServiceConfig(BaseModel):
    """Service configuration for discovery registration."""

    service_name: str
    service_id: str
    host: str = "localhost"
    port: int
    health_endpoint: str = "/health"
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    check_interval: int = 30  # seconds


class DiscoveryClient:
    """Client for PPL Meta Discovery Service integration."""

    def __init__(
        self,
        discovery_url: str = "http://localhost:8006",
        timeout: int = 10,
        retry_attempts: int = 3,
        retry_delay: int = 5,
        service_name: Optional[str] = None,
    ):
        """Initialize discovery client.

        Args:
            discovery_url: URL of the PPL Meta Discovery Service
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
            service_name: Name of the calling service (for X-Service-Name auth header)
        """
        self.discovery_url = discovery_url.rstrip("/")
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.service_name = service_name
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

        # Track registered services for this client instance
        self.registered_services: Dict[str, ServiceConfig] = {}

        # Track actual service IDs returned by discovery service
        self.service_id_mapping: Dict[str, str] = {}  # local_id -> discovery_id

        # Health monitoring task
        self._health_task: Optional[asyncio.Task] = None
        self._health_running = False

        logger.info(f"PPL Discovery Client initialized for {discovery_url}")

    async def register_service(self, config: ServiceConfig) -> bool:
        """Register a service with the discovery service.

        Args:
            config: Service configuration

        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Detect local IP if host is localhost
            host = config.host
            if host in ["localhost", "127.0.0.1"]:
                host = self._get_local_ip()

            # Extract service info from metadata if available
            service_type = config.metadata.get("service_type", "backend")
            version = config.metadata.get("version", "1.0.0")
            capabilities = config.metadata.get("capabilities", config.tags)

            registration_data = {
                "name": config.service_name,
                "service_type": service_type,
                "version": version,
                "host": host,
                "port": config.port,
                "health_endpoint": config.health_endpoint,
                "capabilities": capabilities,
                "metadata": {
                    **config.metadata,
                    "service_id": config.service_id,
                    "registered_at": datetime.utcnow().isoformat(),
                    "check_interval": config.check_interval,
                },
            }

            # Register with discovery service
            url = f"{self.discovery_url}/api/v1/services/register"
            response = await self._make_request("POST", url, json=registration_data)

            if response and response.get("success"):
                # Store mapping between local service ID and discovery service ID
                discovery_service_id = response.get("service_id")
                if discovery_service_id:
                    self.service_id_mapping[config.service_id] = discovery_service_id
                    logger.info(
                        f"Service {config.service_name} registered with ID {discovery_service_id}"
                    )
                else:
                    logger.warning(
                        f"Registration successful but no service_id returned"
                    )

                self.registered_services[config.service_id] = config
                logger.info(f"Service {config.service_name} registered successfully")

                # Start health monitoring if not already running
                if not self._health_running:
                    await self._start_health_monitoring()

                return True
            else:
                logger.error(
                    f"Failed to register service {config.service_name}: {response}"
                )
                return False

        except Exception as e:
            logger.error(f"Exception during service registration: {e}")
            return False

    async def deregister_service(self, local_service_id: str) -> bool:
        """Deregister a service from the discovery service.

        Args:
            local_service_id: Local service identifier

        Returns:
            True if deregistration successful, False otherwise
        """
        try:
            # Get the actual discovery service ID
            discovery_service_id = self.service_id_mapping.get(local_service_id)
            if not discovery_service_id:
                logger.warning(f"No discovery service ID found for {local_service_id}")
                return False

            url = f"{self.discovery_url}/api/v1/services/{discovery_service_id}"
            response = await self._make_request("DELETE", url)

            if response:
                # Remove from local tracking
                self.registered_services.pop(local_service_id, None)
                self.service_id_mapping.pop(local_service_id, None)
                logger.info(f"Service {local_service_id} deregistered successfully")
                return True
            else:
                logger.error(f"Failed to deregister service {local_service_id}")
                return False

        except Exception as e:
            logger.error(f"Exception during service deregistration: {e}")
            return False

    async def discover_services(
        self,
        service_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        healthy_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Discover services from the discovery service.

        Args:
            service_name: Filter by service name (optional)
            tags: Filter by tags (optional)
            healthy_only: Only return healthy services

        Returns:
            List of service information dictionaries
        """
        try:
            url = f"{self.discovery_url}/api/v1/services"
            params = {}

            if service_name:
                params["service_name"] = service_name
            if tags:
                params["tags"] = ",".join(tags)
            if healthy_only:
                params["healthy_only"] = "true"

            response = await self._make_request("GET", url, params=params)

            if response and "services" in response:
                return response["services"]
            else:
                logger.warning("No services found or invalid response")
                return []

        except Exception as e:
            logger.error(f"Exception during service discovery: {e}")
            return []

    async def get_service_url(self, service_name: str) -> Optional[str]:
        """Get a service URL for connecting to a specific service.

        Args:
            service_name: Name of the service to find

        Returns:
            Service URL if found, None otherwise
        """
        services = await self.discover_services(service_name=service_name)

        if services:
            # Simple round-robin selection
            service = services[0]  # Could implement load balancing here
            return f"http://{service['host']}:{service['port']}"

        return None

    async def health_check(self, service_id: str) -> bool:
        """Perform health check for a registered service.

        Args:
            service_id: Service identifier

        Returns:
            True if service is healthy, False otherwise
        """
        config = self.registered_services.get(service_id)
        if not config:
            return False

        try:
            # Check service health endpoint
            health_url = f"http://{config.host}:{config.port}{config.health_endpoint}"
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(health_url)
                healthy = response.status_code == 200

                # Update discovery service with heartbeat
                if healthy:
                    await self._send_heartbeat(service_id)

                return healthy

        except Exception as e:
            logger.warning(f"Health check failed for {service_id}: {e}")
            return False

    async def _send_heartbeat(self, local_service_id: str) -> bool:
        """Send heartbeat to discovery service.

        Args:
            local_service_id: Local service identifier

        Returns:
            True if heartbeat sent successfully
        """
        try:
            # Get the actual discovery service ID
            discovery_service_id = self.service_id_mapping.get(local_service_id)
            if not discovery_service_id:
                logger.warning(f"No discovery service ID found for {local_service_id}")
                return False

            heartbeat_data = {
                "service_id": discovery_service_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "healthy",
            }

            url = f"{self.discovery_url}/api/v1/services/heartbeat"
            response = await self._make_request("POST", url, json=heartbeat_data)

            return response is not None

        except Exception as e:
            logger.warning(f"Failed to send heartbeat for {local_service_id}: {e}")
            return False

    async def _start_health_monitoring(self):
        """Start background health monitoring for registered services."""
        if self._health_running:
            return

        self._health_running = True
        self._health_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Started health monitoring for registered services")

    async def _health_monitor_loop(self):
        """Background task for monitoring service health."""
        while self._health_running:
            try:
                # Check health of all registered services
                for service_id in list(self.registered_services.keys()):
                    await self.health_check(service_id)

                # Wait before next health check cycle
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay before retry

    async def stop_health_monitoring(self):
        """Stop health monitoring task."""
        if self._health_task and not self._health_task.done():
            self._health_running = False
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped health monitoring")

    async def cleanup(self):
        """Cleanup client resources and deregister all services."""
        # Stop health monitoring
        await self.stop_health_monitoring()

        # Deregister all services
        for service_id in list(self.registered_services.keys()):
            await self.deregister_service(service_id)

        # Close HTTP client
        await self.client.aclose()
        logger.info("Discovery client cleanup completed")

    async def _make_request(
        self, method: str, url: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data or None if failed
        """
        # Attach internal service-token auth headers (Issue #8) so the request is
        # accepted by Discovery once AUTH_ENFORCE is enabled.
        headers = dict(kwargs.get("headers") or {})
        if self.service_name:
            headers["Authorization"] = f"Bearer {INTERNAL_SERVICE_TOKEN}"
            headers["X-Service-Name"] = self.service_name
        if headers:
            kwargs["headers"] = headers

        for attempt in range(self.retry_attempts):
            try:
                response = await self.client.request(method, url, **kwargs)

                if response.status_code < 400:
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    ):
                        return response.json()
                    else:
                        return {"success": True}
                else:
                    logger.warning(
                        f"Request failed with status {response.status_code}: {url}"
                    )

            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)

        return None

    def _get_local_ip(self) -> str:
        """Get local IP address for service registration."""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


# Global discovery client instance
_discovery_client: Optional[DiscoveryClient] = None


async def get_discovery_client(service_name: Optional[str] = None) -> DiscoveryClient:
    """Get or create the global discovery client instance."""
    global _discovery_client

    if _discovery_client is None:
        discovery_url = os.getenv("DISCOVERY_SERVICE_URL", "http://localhost:8006")
        _discovery_client = DiscoveryClient(discovery_url=discovery_url)

    if service_name:
        _discovery_client.service_name = service_name

    return _discovery_client


# Convenience functions for easy integration
async def register_service(
    service_name: str,
    service_id: str,
    port: int,
    host: str = "localhost",
    health_endpoint: str = "/health",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Register a service with the discovery service.

    Convenience function for service registration.
    """
    client = await get_discovery_client(service_name=service_name)
    config = ServiceConfig(
        service_name=service_name,
        service_id=service_id,
        host=host,
        port=port,
        health_endpoint=health_endpoint,
        tags=tags or [],
        metadata=metadata or {},
    )
    return await client.register_service(config)


async def deregister_service(service_id: str) -> bool:
    """Deregister a service from the discovery service."""
    client = await get_discovery_client()
    return await client.deregister_service(service_id)


async def discover_services(
    service_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    healthy_only: bool = True,
) -> List[Dict[str, Any]]:
    """Discover services from the discovery service."""
    client = await get_discovery_client()
    return await client.discover_services(service_name, tags, healthy_only)


async def get_service_url(service_name: str) -> Optional[str]:
    """Get a service URL for connecting to a specific service."""
    client = await get_discovery_client()
    return await client.get_service_url(service_name)


async def cleanup_service_discovery():
    """Cleanup discovery client and deregister all services."""
    global _discovery_client

    if _discovery_client:
        await _discovery_client.cleanup()
        _discovery_client = None


# Backward compatibility functions for existing code
async def start_health_monitoring():
    """Start health monitoring (for backward compatibility)."""
    # Health monitoring is automatically started when services are registered
    pass

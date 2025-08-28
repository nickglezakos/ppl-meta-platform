"""
PPL Meta Discovery Service Client
=================================

This module provides a client for integrating backend services with the
PPL Meta Discovery Service. It handles service registration, discovery,
and health monitoring.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for a service to be registered."""

    name: str
    service_type: str
    version: str
    host: str
    port: int
    health_endpoint: str = "/health"
    capabilities: List[str] = None
    metadata: Dict[str, str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}


class DiscoveryClient:
    """Client for interacting with PPL Meta Discovery Service."""

    def __init__(self, discovery_service_url: str = "http://localhost:8006"):
        """
        Initialize the discovery client.

        Args:
            discovery_service_url: Base URL of the discovery service
        """
        self.discovery_service_url = discovery_service_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def register_service(self, config: ServiceConfig) -> bool:
        """
        Register a service with the discovery service.

        Args:
            config: Service configuration

        Returns:
            True if registration successful, False otherwise
        """
        try:
            session = await self._get_session()

            # Prepare registration data
            registration_data = {
                "name": config.name,
                "service_type": config.service_type,
                "version": config.version,
                "host": config.host,
                "port": config.port,
                "health_endpoint": config.health_endpoint,
                "capabilities": config.capabilities,
                "metadata": config.metadata,
            }

            # Send registration request
            url = f"{self.discovery_service_url}/api/v1/services/register"
            async with session.post(url, json=registration_data) as response:
                if response.status == 200:
                    logger.info(
                        f"Successfully registered {config.name} with discovery service"
                    )
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to register {config.name}: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Exception during service registration: {e}")
            return False

    async def deregister_service(self, service_name: str) -> bool:
        """
        Deregister a service from the discovery service.

        Args:
            service_name: Name of the service to deregister

        Returns:
            True if deregistration successful, False otherwise
        """
        try:
            session = await self._get_session()

            # First, get the service ID
            services = await self.discover_services()
            service_id = None

            for service in services:
                if service.get("name") == service_name:
                    service_id = service.get("service_id")
                    break

            if not service_id:
                logger.warning(f"Service {service_name} not found for deregistration")
                return False

            # Send deregistration request
            url = f"{self.discovery_service_url}/api/v1/services/{service_id}"
            async with session.delete(url) as response:
                if response.status == 200:
                    logger.info(f"Successfully deregistered {service_name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to deregister {service_name}: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Exception during service deregistration: {e}")
            return False

    async def get_service_url(self, service_name: str) -> Optional[str]:
        """
        Get the URL for a registered service.

        Args:
            service_name: Name of the service

        Returns:
            Service URL if found, None otherwise
        """
        try:
            services = await self.discover_services()

            for service in services:
                if service.get("name") == service_name:
                    host = service.get("host")
                    port = service.get("port")
                    if host and port:
                        return f"http://{host}:{port}"

            return None

        except Exception as e:
            logger.error(f"Exception getting service URL for {service_name}: {e}")
            return None

    async def discover_services(
        self, service_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover registered services.

        Args:
            service_type: Filter by service type (optional)

        Returns:
            List of service information dictionaries
        """
        try:
            session = await self._get_session()

            # Prepare query parameters
            params = {}
            if service_type:
                params["service_type"] = service_type

            # Send discovery request
            url = f"{self.discovery_service_url}/api/v1/services"
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("services", [])
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to discover services: {response.status} - {error_text}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Exception during service discovery: {e}")
            return []

    async def health_check(self, service_name: str) -> bool:
        """
        Perform health check on a service.

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            service_url = await self.get_service_url(service_name)
            if not service_url:
                return False

            session = await self._get_session()
            health_url = f"{service_url}/health"

            async with session.get(health_url, timeout=5) as response:
                return response.status == 200

        except Exception as e:
            logger.debug(f"Health check failed for {service_name}: {e}")
            return False


# Convenience functions for backward compatibility
async def register_service(
    name: str,
    service_type: str,
    version: str,
    host: str,
    port: int,
    health_endpoint: str = "/health",
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> bool:
    """Convenience function to register a service."""
    config = ServiceConfig(
        name=name,
        service_type=service_type,
        version=version,
        host=host,
        port=port,
        health_endpoint=health_endpoint,
        capabilities=capabilities or [],
        metadata=metadata or {},
    )

    client = DiscoveryClient()
    try:
        result = await client.register_service(config)
        return result
    finally:
        await client.close()


async def deregister_service(service_name: str) -> bool:
    """Convenience function to deregister a service."""
    client = DiscoveryClient()
    try:
        result = await client.deregister_service(service_name)
        return result
    finally:
        await client.close()


async def get_service_url(service_name: str) -> Optional[str]:
    """Convenience function to get a service URL."""
    client = DiscoveryClient()
    try:
        result = await client.get_service_url(service_name)
        return result
    finally:
        await client.close()


async def discover_services(service_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function to discover services."""
    client = DiscoveryClient()
    try:
        result = await client.discover_services(service_type)
        return result
    finally:
        await client.close()

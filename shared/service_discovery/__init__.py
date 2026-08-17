"""
PPL Meta Discovery Service Integration
=====================================

This module provides convenience functions for integrating backend services
with the PPL Meta Discovery Service.
"""

from typing import Dict, List, Optional

import os

# Use the local ppl_discovery_client (httpx-based, not aiohttp-based)
try:
    from .ppl_discovery_client import DiscoveryClient, ServiceConfig

    _discovery_client = None

    def _get_client() -> DiscoveryClient:
        """Get or create the discovery client instance."""
        global _discovery_client
        if _discovery_client is None:
            _discovery_client = DiscoveryClient(
                service_name=os.getenv("DISCOVERY_SERVICE_NAME")
            )
        return _discovery_client

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
        """
        Register a service with the PPL Meta Discovery Service.

        Args:
            name: Service name (e.g., "ppl-meta-gateway")
            service_type: Type of service (e.g., "backend", "frontend")
            version: Service version
            host: Service host/IP
            port: Service port
            health_endpoint: Health check endpoint path
            capabilities: List of service capabilities
            metadata: Additional service metadata

        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Create service metadata with all the additional info
            service_metadata = {
                "service_type": service_type,
                "version": version,
                "capabilities": capabilities or [],
                **(metadata or {}),
            }

            config = ServiceConfig(
                service_name=name,
                service_id=f"{name}-{host}-{port}",
                host=host,
                port=port,
                health_endpoint=health_endpoint,
                tags=[service_type] + (capabilities or []),
                metadata=service_metadata,
            )

            client = _get_client()
            # Ensure the client sends the service-token auth header (Issue #8)
            client.service_name = client.service_name or name
            return await client.register_service(config)
        except Exception as e:
            print(f"Failed to register service {name}: {e}")
            return False

    async def deregister_service(service_name: str) -> bool:
        """
        Deregister a service from the PPL Meta Discovery Service.

        Args:
            service_name: Name of the service to deregister

        Returns:
            True if deregistration successful, False otherwise
        """
        try:
            client = _get_client()
            # Ensure the client sends the service-token auth header (Issue #8)
            client.service_name = client.service_name or service_name
            return await client.deregister_service(service_name)
        except Exception as e:
            print(f"Failed to deregister service {service_name}: {e}")
            return False

    async def get_service_url(service_name: str) -> Optional[str]:
        """
        Get the URL for a registered service.

        Args:
            service_name: Name of the service

        Returns:
            Service URL if found, None otherwise
        """
        try:
            client = _get_client()
            return await client.get_service_url(service_name)
        except Exception as e:
            print(f"Failed to get service URL for {service_name}: {e}")
            return None

    async def discover_services(service_type: Optional[str] = None) -> List[Dict]:
        """
        Discover registered services.

        Args:
            service_type: Filter by service type (optional)

        Returns:
            List of service information dictionaries
        """
        try:
            client = _get_client()
            return await client.discover_services(service_type)
        except Exception as e:
            print(f"Failed to discover services: {e}")
            return []

except ImportError as e:
    print(f"PPL Discovery Client not available: {e}")

    # Provide stub implementations for backward compatibility
    async def register_service(*args, **kwargs) -> bool:
        print("Service discovery not available - register_service stub")
        return False

    async def deregister_service(*args, **kwargs) -> bool:
        print("Service discovery not available - deregister_service stub")
        return False

    async def get_service_url(*args, **kwargs) -> Optional[str]:
        print("Service discovery not available - get_service_url stub")
        return None

    async def discover_services(*args, **kwargs) -> List[Dict]:
        print("Service discovery not available - discover_services stub")
        return []


# Export the functions
__all__ = [
    "register_service",
    "deregister_service",
    "get_service_url",
    "discover_services",
]

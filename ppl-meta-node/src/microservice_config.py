"""Microservice-specific configuration for PPL Meta Node."""

import os
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from src.config import settings

# Service registry configuration
SERVICE_REGISTRY = {
    "name": "ppl-meta-node",
    "version": settings.APP_VERSION,
    "host": settings.HOST,
    "port": settings.PORT,
    "health_check": f"http://{settings.HOST}:{settings.PORT}/api/v1/health",
    "tags": ["user-management", "authentication", "microservice"],
}

# Consul configuration
CONSUL_CONFIG = {
    "host": os.getenv("CONSUL_HOST", "consul"),
    "port": int(os.getenv("CONSUL_PORT", "8500")),
    "enabled": os.getenv("CONSUL_ENABLED", "true").lower() == "true",
}

# Inter-service communication endpoints
EXTERNAL_SERVICES = {
    "ppl_media": {
        "url": settings.PPL_MEDIA_SERVICE_URL,
        "health_endpoint": "/api/v1/health",
        "timeout": 30,
    },
    "ppl_gateway": {
        "url": os.getenv("PPL_GATEWAY_URL", "http://ppl-meta-gateway:8080"),
        "health_endpoint": "/health",
        "timeout": 10,
    },
    "ppl_orchestrator": {
        "url": os.getenv("PPL_ORCHESTRATOR_URL", "http://ppl-meta-orchestrator:8002"),
        "health_endpoint": "/api/v1/health",
        "timeout": 30,
    },
}

# API configuration
API_CONFIG = {
    "title": settings.APP_NAME,
    "version": settings.APP_VERSION,
    "description": "User Management Microservice for PPL Meta Platform",
    "prefix": "/api",
    "current_version": "v1",
    "supported_versions": ["v1"],
}

# Security configuration
SECURITY_CONFIG = {
    "cors_origins": [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        settings.PPL_MEDIA_SERVICE_URL,
        os.getenv("PPL_GATEWAY_URL", "http://ppl-meta-gateway:8080"),
        os.getenv("PPL_ORCHESTRATOR_URL", "http://ppl-meta-orchestrator:8002"),
    ],
    "trusted_hosts": [
        "localhost",
        "127.0.0.1",
        "*.localhost",
        "ppl-meta-media",
        "ppl-meta-node",
        "ppl-meta-gateway",
        "ppl-meta-orchestrator",
        "nginx-gateway",
    ],
}


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""

    name: str
    url: str
    health_endpoint: str = "/health"
    version: str = "1.0.0"
    capabilities: List[str] = None


class ServiceDiscovery:
    """Service discovery and communication helper"""

    def __init__(self):
        self.consul_url = os.getenv("CONSUL_URL", "http://consul:8500")
        self.service_secret = settings.SERVICE_SECRET

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the URL for a specific service"""
        service_map = {
            "gateway": os.getenv("PPL_GATEWAY_URL", "http://ppl-meta-gateway:8080"),
            "media": settings.PPL_MEDIA_SERVICE_URL,
            "orchestrator": os.getenv(
                "PPL_ORCHESTRATOR_URL", "http://ppl-meta-orchestrator:8002"
            ),
        }
        return service_map.get(service_name)

    def make_internal_request(
        self, service_name: str, endpoint: str, method: str = "GET", **kwargs
    ):
        """Make an authenticated request to another service"""
        service_url = self.get_service_url(service_name)
        if not service_url:
            raise ValueError(f"Service {service_name} not found")

        url = urljoin(service_url, endpoint)
        headers = kwargs.pop("headers", {})

        # Add internal service authentication
        headers["X-Service-Auth"] = "internal"
        headers["X-Service-Secret"] = self.service_secret
        headers["X-Requesting-Service"] = "ppl-meta-node"

        with httpx.Client() as client:
            response = client.request(method, url, headers=headers, **kwargs)
        return response


class MeshVPNConfig:
    """Configuration for Mesh VPN connectivity to edge devices"""

    def __init__(self):
        self.vpn_subnet = os.getenv("VPN_INTERNAL_SUBNET", "10.13.13.0/24")
        self.gateway_vpn_ip = os.getenv("GATEWAY_VPN_IP", "10.13.13.1")
        self.edge_devices = {
            "iot-controller": "10.13.13.10",
            "camera-system": "10.13.13.11",
            "local-processor": "10.13.13.12",
            "edge-storage": "10.13.13.13",
        }

    def get_edge_device_url(self, device_name: str, port: int = 8000) -> Optional[str]:
        """Get the VPN URL for an edge device"""
        ip = self.edge_devices.get(device_name)
        return f"http://{ip}:{port}" if ip else None


# Global instances
service_discovery = ServiceDiscovery()
mesh_vpn = MeshVPNConfig()

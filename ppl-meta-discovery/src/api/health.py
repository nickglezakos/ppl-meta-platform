"""Health API routes for PPL Meta Discovery Service."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from models import PlatformTopology
from services.edge_registry import EdgeRegistry
from services.service_registry import ServiceRegistry

router = APIRouter(prefix="/health", tags=["health"])


def get_service_registry() -> ServiceRegistry:
    """Dependency to get service registry instance."""
    # This will be properly injected in main.py
    return None


def get_edge_registry() -> EdgeRegistry:
    """Dependency to get edge registry instance."""
    # This will be properly injected in main.py
    return None


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "ppl-meta-discovery",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/detailed")
async def detailed_health_check(
    service_registry: ServiceRegistry = Depends(get_service_registry),
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> Dict[str, Any]:
    """Detailed health check with registry information."""

    # Get service and device counts
    if service_registry:
        services = service_registry.list_services()
        service_count = services.total_count
        healthy_services = services.healthy_count
    else:
        service_count = 0
        healthy_services = 0

    if edge_registry:
        devices = edge_registry.list_devices()
        device_count = devices.total_count
        healthy_devices = devices.healthy_count
    else:
        device_count = 0
        healthy_devices = 0

    return {
        "status": "healthy",
        "service": "ppl-meta-discovery",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "registries": {
            "services": {
                "total": service_count,
                "healthy": healthy_services,
            },
            "devices": {
                "total": device_count,
                "healthy": healthy_devices,
            },
        },
    }


@router.get("/topology")
async def get_platform_topology(
    service_registry: ServiceRegistry = Depends(get_service_registry),
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> PlatformTopology:
    """Get complete platform topology."""

    # Get all services and devices
    if service_registry:
        services_list = service_registry.list_services()
        backend_services = {
            service.service_id: service for service in services_list.services
        }
    else:
        backend_services = {}

    if edge_registry:
        devices_list = edge_registry.list_devices()
        edge_devices = {device.device_id: device for device in devices_list.devices}
    else:
        edge_devices = {}

    return PlatformTopology(
        version="1.0.0",
        discovery_service="http://localhost:8006",
        backend_services=backend_services,
        edge_devices=edge_devices,
        network_config={
            "discovery_port": 8006,
            "multicast_enabled": True,
            "vpn_discovery_enabled": True,
        },
    )

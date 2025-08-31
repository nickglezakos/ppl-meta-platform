"""PPL Meta Discovery Service - Main application."""

import logging
import socket
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

# Import platform API
from api.platform import router as platform_router
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from models import (
    DiscoveryQuery,
    EdgeDeviceList,
    EdgeRegistrationRequest,
    HeartbeatRequest,
    PlatformTopology,
    RegistrationRequest,
    RegistrationResponse,
    ServiceInfo,
    ServiceList,
)
from services.edge_registry import EdgeRegistry
from services.multicast_announcer import MulticastAnnouncer
from services.service_registry import ServiceRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global registries and announcer
service_registry = ServiceRegistry()
edge_registry = EdgeRegistry()
multicast_announcer = MulticastAnnouncer()


def get_machine_ip() -> str:
    """Get the machine's IP address for external connections."""
    try:
        # Connect to a remote address to determine the local IP
        # that would be used for external connections
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        # Fallback to localhost if detection fails
        return "127.0.0.1"


def resolve_service_hosts(services_list: ServiceList) -> ServiceList:
    """Resolve 0.0.0.0 hosts to actual machine IP for external clients."""
    machine_ip = get_machine_ip()

    resolved_services = []
    for service in services_list.services:
        if service.host == "0.0.0.0":
            # Create a new service object with resolved host
            resolved_service = ServiceInfo(
                service_id=service.service_id,
                name=service.name,
                service_type=service.service_type,
                version=service.version,
                host=machine_ip,  # Replace 0.0.0.0 with actual IP
                port=service.port,
                health_endpoint=service.health_endpoint,
                status=service.status,
                capabilities=service.capabilities,
                metadata=service.metadata,
                registered_at=service.registered_at,
                last_seen=service.last_seen,
                heartbeat_count=service.heartbeat_count,
            )
            resolved_services.append(resolved_service)
        else:
            resolved_services.append(service)

    return ServiceList(
        services=resolved_services,
        total_count=services_list.total_count,
        healthy_count=services_list.healthy_count,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info("PPL Meta Discovery Service v2.14.0 - Phase 2 Implementation starting")

    # Start registries
    await service_registry.start()
    await edge_registry.start()

    # Start multicast announcer for network discovery
    await multicast_announcer.start()

    yield

    # Stop all services
    await multicast_announcer.stop()
    await service_registry.stop()
    await edge_registry.stop()

    logger.info("PPL Meta Discovery Service stopped")

    logger.info("PPL Meta Discovery Service stopped")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta Discovery Service",
    description="Centralized service discovery for PPL Meta platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(platform_router, prefix="/api/v1")


# Basic health endpoint
@app.get("/health")
async def basic_health():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "ppl-meta-discovery",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Service registry endpoints
@app.post("/api/v1/services/register", response_model=RegistrationResponse)
async def register_service(request: RegistrationRequest):
    """Register a backend service."""
    return await service_registry.register_service(request)


@app.get("/api/v1/services", response_model=ServiceList)
async def list_services(query: Optional[DiscoveryQuery] = None):
    """List all registered services with resolved hosts for external clients."""
    services_list = service_registry.list_services(query)
    # Resolve 0.0.0.0 hosts to actual machine IP for mobile/external clients
    return resolve_service_hosts(services_list)


@app.post("/api/v1/services/heartbeat")
async def service_heartbeat(request: HeartbeatRequest):
    """Update service heartbeat."""
    return await service_registry.update_heartbeat(request)


@app.delete("/api/v1/services/{service_id}")
async def deregister_service(service_id: str):
    """Deregister a service."""
    return await service_registry.deregister_service(service_id)


@app.get("/api/v1/services/{service_id}")
async def get_service(service_id: str):
    """Get service details by ID."""
    service = service_registry.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


# Edge device endpoints
@app.post("/api/v1/devices/register", response_model=RegistrationResponse)
async def register_device(request: EdgeRegistrationRequest):
    """Register an edge device."""
    return await edge_registry.register_device(request)


@app.get("/api/v1/devices", response_model=EdgeDeviceList)
async def list_devices():
    """List all registered edge devices."""
    return edge_registry.list_devices()


@app.post("/api/v1/devices/heartbeat")
async def device_heartbeat(request: HeartbeatRequest):
    """Update device heartbeat."""
    return await edge_registry.update_heartbeat(request)


@app.delete("/api/v1/devices/{device_id}")
async def deregister_device(device_id: str):
    """Deregister a device."""
    return await edge_registry.deregister_device(device_id)


@app.get("/api/v1/devices/{device_id}")
async def get_device(device_id: str):
    """Get device details by ID."""
    device = edge_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# Discovery endpoints
# Enhanced discovery endpoints with complete platform topology
@app.get("/api/v1/discovery/topology", response_model=PlatformTopology)
async def get_platform_topology():
    """Get complete platform topology including all services and devices."""
    services = service_registry.list_services()
    devices = edge_registry.list_devices()

    # Get mobile cameras specifically
    mobile_cameras = edge_registry.get_mobile_cameras()
    raspberry_pi_devices = edge_registry.get_raspberry_pi_devices()

    topology = PlatformTopology(
        discovery_service={
            "service_id": "discovery-service",
            "name": "ppl-meta-discovery",
            "version": "2.14.0",
            "status": "healthy",
            "port": 8006,
            "endpoints": [
                "/health",
                "/api/v1/services",
                "/api/v1/devices",
                "/api/v1/discovery/topology",
                "/api/v1/discovery/capabilities",
                "/api/v1/platform/metadata",
            ],
            "multicast": {
                "address": multicast_announcer.multicast_group,
                "port": multicast_announcer.multicast_port,
                "active": True,
            },
        },
        backend_services={service.service_id: service for service in services.services},
        edge_devices={device.device_id: device for device in devices.devices},
        network_summary={
            "total_services": len(services.services),
            "healthy_services": len(
                [s for s in services.services if s.status == "healthy"]
            ),
            "total_devices": len(devices.devices),
            "mobile_cameras": len(mobile_cameras),
            "raspberry_pi_devices": len(raspberry_pi_devices),
            "capabilities": list(edge_registry._device_capabilities_index.keys()),
            "locations": list(edge_registry._location_index.keys()),
        },
        timestamp=datetime.utcnow(),
    )

    return topology


@app.get("/api/v1/discovery/capabilities")
async def get_platform_capabilities():
    """Get all available capabilities across the platform."""
    service_capabilities = set()
    device_capabilities = set()

    # Collect service capabilities
    services = service_registry.list_services()
    for service in services.services:
        service_capabilities.update(service.capabilities)

    # Collect device capabilities
    devices = edge_registry.list_devices()
    for device in devices.devices:
        device_capabilities.update(device.capabilities)

    return {
        "service_capabilities": list(service_capabilities),
        "device_capabilities": list(device_capabilities),
        "all_capabilities": list(service_capabilities.union(device_capabilities)),
        "capability_index": edge_registry._device_capabilities_index,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/discovery/mobile-cameras")
async def get_mobile_cameras():
    """Get all registered mobile camera devices."""
    cameras = edge_registry.get_mobile_cameras()
    return {
        "mobile_cameras": cameras,
        "count": len(cameras),
        "online": len([c for c in cameras if c.status == "healthy"]),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/discovery/raspberry-pi")
async def get_raspberry_pi_devices():
    """Get all registered Raspberry Pi devices."""
    pi_devices = edge_registry.get_raspberry_pi_devices()
    return {
        "raspberry_pi_devices": pi_devices,
        "count": len(pi_devices),
        "online": len([d for d in pi_devices if d.status == "healthy"]),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/discovery/by-capability/{capability}")
async def find_devices_by_capability(capability: str):
    """Find all devices that have a specific capability."""
    devices = edge_registry.find_devices_by_capability(capability)
    return {
        "capability": capability,
        "devices": devices,
        "count": len(devices),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/discovery/by-location/{location}")
async def find_devices_by_location(location: str):
    """Find all devices in a specific location."""
    devices = edge_registry.find_devices_by_location(location)
    return {
        "location": location,
        "devices": devices,
        "count": len(devices),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/v1/discovery/announce")
async def trigger_multicast_announcement():
    """Manually trigger a multicast announcement."""
    try:
        multicast_announcer.send_discovery_request()
        return {
            "status": "success",
            "message": "Multicast announcement sent",
            "multicast_group": multicast_announcer.multicast_group,
            "multicast_port": multicast_announcer.multicast_port,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to send multicast announcement: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to send announcement: {str(e)}"
        )


@app.get("/api/v1/discovery/status")
async def get_discovery_status():
    """Get comprehensive discovery service status."""
    services = service_registry.list_services()
    devices = edge_registry.list_devices()

    return {
        "discovery_service": {
            "name": "ppl-meta-discovery",
            "version": "2.14.0",
            "phase": "Phase 2 - Core Implementation",
            "status": "healthy",
            "uptime": "active",
            "port": 8006,
        },
        "multicast": {
            "group": multicast_announcer.multicast_group,
            "port": multicast_announcer.multicast_port,
            "active": True,
            "announcement_interval": multicast_announcer.announcement_interval,
        },
        "registries": {
            "services": {
                "total": len(services.services),
                "healthy": len([s for s in services.services if s.status == "healthy"]),
                "types": list(set(s.service_type for s in services.services)),
            },
            "devices": {
                "total": len(devices.devices),
                "healthy": len([d for d in devices.devices if d.status == "healthy"]),
                "types": list(set(d.device_type for d in devices.devices)),
            },
        },
        "capabilities": {
            "device_capabilities": list(
                edge_registry._device_capabilities_index.keys()
            ),
            "locations": list(edge_registry._location_index.keys()),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# Additional discovery endpoints
@app.get("/api/v1/services/by-type/{service_type}")
async def get_services_by_type(service_type: str):
    """Get services by type."""
    services = service_registry.get_services_by_type(service_type)
    return {"services": services, "count": len(services)}


@app.get("/api/v1/services/healthy")
async def get_healthy_services():
    """Get all healthy services."""
    services = service_registry.get_healthy_services()
    return {"services": services, "count": len(services)}


@app.post("/api/v1/health-check/all")
async def health_check_all():
    """Perform health check on all registered services."""
    results = await service_registry.health_check_all()
    return {"health_results": results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True, log_level="info")

"""PPL Meta Discovery Service - Main application."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

# Import platform API
from api.platform import router as platform_router
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import (
    DiscoveryQuery,
    EdgeDeviceList,
    EdgeRegistrationRequest,
    HeartbeatRequest,
    PlatformTopology,
    RegistrationRequest,
    RegistrationResponse,
    ServiceList,
)
from services.edge_registry import EdgeRegistry
from services.service_registry import ServiceRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global registries
service_registry = ServiceRegistry()
edge_registry = EdgeRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info("PPL Meta Discovery Service started")

    # Start registries
    await service_registry.start()
    await edge_registry.start()

    yield

    # Stop registries
    await service_registry.stop()
    await edge_registry.stop()

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
    """List all registered services."""
    return service_registry.list_services(query)


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
@app.get("/api/v1/topology")
async def get_topology():
    """Get platform topology."""
    services = service_registry.list_services()
    devices = edge_registry.list_devices()

    return PlatformTopology(
        platform="ppl-meta",
        version="1.0.0",
        discovery_service="http://localhost:8006",
        timestamp=datetime.utcnow(),
        backend_services={service.service_id: service for service in services.services},
        edge_devices={device.device_id: device for device in devices.devices},
        network_config={
            "discovery_port": 8006,
            "multicast_enabled": True,
            "vpn_discovery_enabled": True,
        },
    )


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

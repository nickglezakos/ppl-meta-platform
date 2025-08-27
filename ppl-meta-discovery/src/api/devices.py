"""Edge devices API routes for PPL Meta Discovery Service."""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from models import (
    EdgeDeviceInfo,
    EdgeDeviceList,
    EdgeRegistrationRequest,
    HeartbeatRequest,
    RegistrationResponse,
    ServiceStatus,
)
from services.edge_registry import EdgeRegistry

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def get_edge_registry() -> EdgeRegistry:
    """Dependency to get edge registry instance."""
    # This will be properly injected in main.py
    from src.main import app

    return app.state.edge_registry


@router.post("/register", response_model=RegistrationResponse)
async def register_device(
    request: EdgeRegistrationRequest,
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> RegistrationResponse:
    """Register a new edge device."""
    return await edge_registry.register_device(request)


@router.post("/heartbeat")
async def device_heartbeat(
    request: HeartbeatRequest,
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> Dict[str, str]:
    """Update device heartbeat."""
    return await edge_registry.update_heartbeat(request)


@router.delete("/deregister/{device_id}")
async def deregister_device(
    device_id: str,
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> Dict[str, str]:
    """Deregister an edge device."""
    return await edge_registry.deregister_device(device_id)


@router.get("/", response_model=EdgeDeviceList)
async def list_devices(
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> EdgeDeviceList:
    """List all registered edge devices with optional filtering."""

    # Convert string status to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = ServiceStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    return edge_registry.list_devices(device_type=device_type, status=status_enum)


@router.get("/{device_id}", response_model=EdgeDeviceInfo)
async def get_device(
    device_id: str,
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> EdgeDeviceInfo:
    """Get specific device by ID."""
    device = edge_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return device


@router.get("/capability/{capability}")
async def get_devices_by_capability(
    capability: str,
    edge_registry: EdgeRegistry = Depends(get_edge_registry),
) -> EdgeDeviceList:
    """Get devices that have a specific capability."""
    devices = edge_registry.get_devices_by_capability(capability)

    healthy_count = sum(1 for d in devices if d.status == ServiceStatus.HEALTHY)

    return EdgeDeviceList(
        devices=devices,
        total_count=len(devices),
        healthy_count=healthy_count,
    )

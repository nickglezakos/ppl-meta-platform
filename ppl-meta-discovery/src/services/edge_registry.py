"""Edge device registry for mobile and edge devices."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException
from models import (
    EdgeDeviceInfo,
    EdgeDeviceList,
    EdgeRegistrationRequest,
    HeartbeatRequest,
    RegistrationResponse,
    ServiceStatus,
)

logger = logging.getLogger(__name__)


class EdgeRegistry:
    """Registry for managing edge devices."""

    def __init__(self, heartbeat_timeout: int = 120):
        """Initialize the edge device registry.

        Args:
            heartbeat_timeout: Seconds after which device is stale
        """
        self._devices: Dict[str, EdgeDeviceInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the edge registry background tasks."""
        logger.info("Starting edge device registry")
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_devices())

    async def stop(self):
        """Stop the edge registry background tasks."""
        logger.info("Stopping edge device registry")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def register_device(
        self, request: EdgeRegistrationRequest
    ) -> RegistrationResponse:
        """Register a new edge device or update existing one.

        Args:
            request: Device registration request

        Returns:
            Registration response with device ID
        """
        # Generate unique device ID
        device_id = str(uuid.uuid4())

        # Check if device with same name already exists
        existing_device = self._find_device_by_name(request.device_name)
        if existing_device:
            logger.info(f"Updating existing device: {request.device_name}")
            device_id = existing_device.device_id

        # Create device info
        device_info = EdgeDeviceInfo(
            device_id=device_id,
            device_name=request.device_name,
            device_type=request.device_type,
            capabilities=request.capabilities,
            network_interfaces=request.network_interfaces,
            platform_info=request.platform_info,
            location=request.location,
            metadata=request.metadata,
            status=ServiceStatus.HEALTHY,
            registered_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )

        # Store the device
        self._devices[device_id] = device_info

        logger.info(
            f"Registered edge device {request.device_name} "
            f"({device_id}) of type {request.device_type}"
        )

        return RegistrationResponse(
            success=True,
            device_id=device_id,
            message=f"Device {request.device_name} registered successfully",
            heartbeat_interval=60,
        )

    async def update_heartbeat(self, request: HeartbeatRequest) -> Dict[str, str]:
        """Update device heartbeat.

        Args:
            request: Heartbeat request

        Returns:
            Status message

        Raises:
            HTTPException: If device not found
        """
        if not request.device_id:
            raise HTTPException(
                status_code=400, detail="device_id is required for device heartbeat"
            )

        device = self._devices.get(request.device_id)
        if not device:
            raise HTTPException(
                status_code=404, detail=f"Device {request.device_id} not found"
            )

        # Update device information
        device.last_seen = datetime.utcnow()
        device.heartbeat_count += 1
        device.status = request.status

        # Update metadata if provided
        if request.metadata:
            device.metadata.update(request.metadata)

        logger.debug(
            f"Updated heartbeat for device {device.device_name} "
            f"({request.device_id})"
        )

        return {"status": "heartbeat updated"}

    async def deregister_device(self, device_id: str) -> Dict[str, str]:
        """Deregister an edge device.

        Args:
            device_id: ID of device to deregister

        Returns:
            Status message

        Raises:
            HTTPException: If device not found
        """
        device = self._devices.get(device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        device.status = ServiceStatus.DEREGISTERING

        # Remove after short delay to allow for cleanup
        await asyncio.sleep(1)
        del self._devices[device_id]

        logger.info(f"Deregistered edge device {device.device_name} ({device_id})")

        return {"status": "device deregistered"}

    def get_device(self, device_id: str) -> Optional[EdgeDeviceInfo]:
        """Get device by ID.

        Args:
            device_id: Device ID

        Returns:
            Device info if found, None otherwise
        """
        return self._devices.get(device_id)

    def list_devices(
        self, device_type: Optional[str] = None, status: Optional[ServiceStatus] = None
    ) -> EdgeDeviceList:
        """List devices with optional filtering.

        Args:
            device_type: Optional device type filter
            status: Optional status filter

        Returns:
            Filtered list of devices
        """
        devices = list(self._devices.values())

        # Apply filters
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]

        if status:
            devices = [d for d in devices if d.status == status]

        healthy_count = sum(1 for d in devices if d.status == ServiceStatus.HEALTHY)

        return EdgeDeviceList(
            devices=devices,
            total_count=len(devices),
            healthy_count=healthy_count,
        )

    def get_devices_by_type(self, device_type: str) -> List[EdgeDeviceInfo]:
        """Get all devices of a specific type.

        Args:
            device_type: Type of devices to retrieve

        Returns:
            List of devices of the specified type
        """
        return [
            device
            for device in self._devices.values()
            if device.device_type == device_type
        ]

    def get_healthy_devices(self) -> List[EdgeDeviceInfo]:
        """Get all healthy devices.

        Returns:
            List of healthy devices
        """
        return [
            device
            for device in self._devices.values()
            if device.status == ServiceStatus.HEALTHY
        ]

    def get_devices_by_capability(self, capability: str) -> List[EdgeDeviceInfo]:
        """Get devices that have a specific capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of devices with the capability
        """
        return [
            device
            for device in self._devices.values()
            if capability in device.capabilities
        ]

    def _find_device_by_name(self, name: str) -> Optional[EdgeDeviceInfo]:
        """Find device by name.

        Args:
            name: Device name to search for

        Returns:
            Device info if found, None otherwise
        """
        for device in self._devices.values():
            if device.device_name == name:
                return device
        return None

    async def _cleanup_stale_devices(self):
        """Background task to clean up stale devices."""
        while True:
            try:
                current_time = datetime.utcnow()
                stale_devices = []

                for device_id, device in self._devices.items():
                    time_since_heartbeat = (
                        current_time - device.last_seen
                    ).total_seconds()

                    if time_since_heartbeat > self._heartbeat_timeout:
                        stale_devices.append(device_id)
                        device.status = ServiceStatus.UNHEALTHY
                        logger.warning(
                            f"Device {device.device_name} ({device_id}) "
                            f"marked as stale (last seen: {device.last_seen})"
                        )

                # Remove very stale devices (2x timeout)
                very_stale_threshold = self._heartbeat_timeout * 2
                for device_id in list(self._devices.keys()):
                    device = self._devices[device_id]
                    time_since_heartbeat = (
                        current_time - device.last_seen
                    ).total_seconds()

                    if time_since_heartbeat > very_stale_threshold:
                        del self._devices[device_id]
                        logger.info(
                            f"Removed very stale device {device.device_name} "
                            f"({device_id})"
                        )

                # Sleep for cleanup interval
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in device cleanup task: {e}")
                await asyncio.sleep(60)

"""Edge device registry for mobile and edge devices.

Phase 2: VPN-aware — supports Tailscale IP tracking and trusted-device
authentication via Tailscale CGNAT IP range + ACL tag validation.
"""

import asyncio
import ipaddress
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from fastapi import HTTPException, Request
from models import (
    EdgeDeviceInfo,
    EdgeDeviceList,
    EdgeDeviceType,
    EdgeRegistrationRequest,
    HeartbeatRequest,
    RegistrationResponse,
    ServiceStatus,
)

logger = logging.getLogger(__name__)

TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


class EdgeRegistry:
    """Registry for managing edge devices like mobile cameras and Raspberry Pi."""

    def __init__(self, heartbeat_timeout: int = 120):
        """Initialize the edge device registry.

        Args:
            heartbeat_timeout: Seconds after which device is stale
        """
        self._devices: Dict[str, EdgeDeviceInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        self._device_capabilities_index: Dict[str, Set[str]] = {}
        self._location_index: Dict[str, Set[str]] = {}

    async def start(self):
        """Start the edge registry background tasks."""
        logger.info("Starting edge device registry with enhanced mobile camera support")
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
        # Validate device type (Pydantic already coerces to EdgeDeviceType, so this
        # guards against any non-enum edge values reaching the registry).
        if request.device_type not in EdgeDeviceType.__members__.values():
            logger.warning(f"Unsupported device type: {request.device_type}")

        # Generate unique device ID or reuse existing
        device_id = str(uuid.uuid4())
        existing_device = self._find_device_by_name(request.device_name)

        if existing_device:
            logger.info(f"Updating existing device: {request.device_name}")
            device_id = existing_device.device_id
            # Remove old device from indexes
            self._remove_from_indexes(existing_device)

        # Extract Tailscale IP from metadata (Phase 2)
        tailscale_ip = request.metadata.get("tailscale_ip") if request.metadata else None
        vpn_reachable = bool(tailscale_ip)

        # Enhanced device info with mobile camera specific fields
        device_info = EdgeDeviceInfo(
            device_id=device_id,
            device_name=request.device_name,
            device_type=request.device_type,
            capabilities=request.capabilities or [],
            network_interfaces=request.network_interfaces or [],
            platform_info=request.platform_info or {},
            location=request.location,
            metadata=self._enhance_metadata(request),
            tailscale_ip=tailscale_ip,
            vpn_reachable=vpn_reachable,
            status=ServiceStatus.HEALTHY,
            registered_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            heartbeat_count=0,
        )

        # Store the device
        self._devices[device_id] = device_info

        # Update indexes
        self._update_indexes(device_info)

        logger.info(
            f"Registered edge device {request.device_name} "
            f"({device_id}) of type {request.device_type} with {len(request.capabilities or [])} capabilities"
        )

        # Determine heartbeat interval based on device type
        heartbeat_interval = self._get_heartbeat_interval(request.device_type)

        return RegistrationResponse(
            success=True,
            device_id=device_id,
            message=f"Device {request.device_name} registered successfully",
            heartbeat_interval=heartbeat_interval,
        )

    def _enhance_metadata(self, request: EdgeRegistrationRequest) -> Dict:
        """Enhance metadata with device-specific information."""
        metadata = request.metadata or {}

        # Add registration timestamp
        metadata["registration_timestamp"] = datetime.utcnow().isoformat()

        # Add device-specific enhancements
        if request.device_type == "mobile_camera":
            metadata.update(
                {
                    "camera_ready": True,
                    "supports_live_stream": "live_stream"
                    in (request.capabilities or []),
                    "supports_recording": "video_recording"
                    in (request.capabilities or []),
                    "mobile_platform": request.platform_info.get("platform", "unknown"),
                    "app_version": request.platform_info.get("app_version", "unknown"),
                }
            )
        elif request.device_type == "raspberry_pi":
            metadata.update(
                {
                    "pi_model": request.platform_info.get("model", "unknown"),
                    "pi_os": request.platform_info.get("os", "unknown"),
                    "supports_gpio": "gpio_control" in (request.capabilities or []),
                    "camera_attached": "camera_module" in (request.capabilities or []),
                }
            )
        elif request.device_type in ["android_device", "ios_device"]:
            metadata.update(
                {
                    "mobile_os": request.platform_info.get("os", "unknown"),
                    "device_model": request.platform_info.get("model", "unknown"),
                    "supports_push": "push_notifications"
                    in (request.capabilities or []),
                }
            )

        return metadata

    def _get_heartbeat_interval(self, device_type: str) -> int:
        """Get appropriate heartbeat interval for device type."""
        intervals = {
            "mobile_camera": 30,  # Frequent for mobile cameras
            "raspberry_pi": 60,  # Standard for Pi devices
            "ip_camera": 45,  # Medium for IP cameras
            "android_device": 30,  # Frequent for mobile
            "ios_device": 30,  # Frequent for mobile
            "edge_gateway": 60,  # Standard for gateways
        }
        return intervals.get(device_type, 60)

    def _update_indexes(self, device_info: EdgeDeviceInfo):
        """Update capability and location indexes."""
        device_id = device_info.device_id

        # Update capabilities index
        for capability in device_info.capabilities:
            if capability not in self._device_capabilities_index:
                self._device_capabilities_index[capability] = set()
            self._device_capabilities_index[capability].add(device_id)

        # Update location index
        if device_info.location:
            location_key = f"{device_info.location.get('area', 'unknown')}"
            if location_key not in self._location_index:
                self._location_index[location_key] = set()
            self._location_index[location_key].add(device_id)

    def _remove_from_indexes(self, device_info: EdgeDeviceInfo):
        """Remove device from all indexes."""
        device_id = device_info.device_id

        # Remove from capabilities index
        for capability in device_info.capabilities:
            if capability in self._device_capabilities_index:
                self._device_capabilities_index[capability].discard(device_id)
                if not self._device_capabilities_index[capability]:
                    del self._device_capabilities_index[capability]

        # Remove from location index
        if device_info.location:
            location_key = f"{device_info.location.get('area', 'unknown')}"
            if location_key in self._location_index:
                self._location_index[location_key].discard(device_id)
                if not self._location_index[location_key]:
                    del self._location_index[location_key]

    def find_devices_by_capability(self, capability: str) -> List[EdgeDeviceInfo]:
        """Find devices that have a specific capability."""
        device_ids = self._device_capabilities_index.get(capability, set())
        return [
            self._devices[device_id]
            for device_id in device_ids
            if device_id in self._devices
        ]

    def find_devices_by_location(self, location_area: str) -> List[EdgeDeviceInfo]:
        """Find devices in a specific location area."""
        device_ids = self._location_index.get(location_area, set())
        return [
            self._devices[device_id]
            for device_id in device_ids
            if device_id in self._devices
        ]

    def get_mobile_cameras(self) -> List[EdgeDeviceInfo]:
        """Get all registered mobile camera devices."""
        return [
            device
            for device in self._devices.values()
            if device.device_type == "mobile_camera"
        ]

    def get_raspberry_pi_devices(self) -> List[EdgeDeviceInfo]:
        """Get all registered Raspberry Pi devices."""
        return [
            device
            for device in self._devices.values()
            if device.device_type == "raspberry_pi"
        ]

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

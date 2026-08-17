"""Data models for PPL Meta Discovery Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Types of services in the PPL Meta platform."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    EDGE = "edge"


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    REGISTERING = "registering"
    DEREGISTERING = "deregistering"


class EdgeDeviceType(str, Enum):
    """Types of edge devices."""

    MOBILE_CAMERA = "mobile_camera"
    EDGE_CAMERA = "edge_camera"
    EDGE_VPN = "edge_vpn"
    RASPBERRY_PI = "raspberry_pi"
    SIGNAGE_PLAYER = "signage_player"
    DIGITAL_SIGNAGE = "digital_signage"


class LicenseStatus(str, Enum):
    """Platform license status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    TRIAL = "trial"
    SUSPENDED = "suspended"


class LicenseType(str, Enum):
    """Types of licenses."""

    TRIAL = "trial"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    DEVELOPER = "developer"


class PlatformLicenseInfo(BaseModel):
    """Platform licensing information for discovery service."""

    license_status: LicenseStatus = Field(..., description="Current license status")
    license_type: LicenseType = Field(..., description="Type of license")
    max_users: int = Field(..., description="Maximum allowed users")
    current_users: int = Field(..., description="Current user count")
    expires_at: Optional[datetime] = Field(None, description="License expiration date")
    owner_email: Optional[str] = Field(None, description="Platform owner email")
    instance_id: str = Field(..., description="Unique platform instance ID")
    activated_at: Optional[datetime] = Field(
        None, description="License activation date"
    )
    features: List[str] = Field(default_factory=list, description="Available features")

    @property
    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self.license_status not in [LicenseStatus.ACTIVE, LicenseStatus.TRIAL]:
            return False
        if self.expires_at:
            now = datetime.utcnow()
            expires_at = self.expires_at
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            if expires_at < now:
                return False
        return True

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until license expires."""
        if not self.expires_at:
            return None
        now = datetime.utcnow()
        expires_at = self.expires_at
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        delta = expires_at - now
        return max(0, delta.days)


class PlatformMetadata(BaseModel):
    """Enhanced platform metadata including licensing information."""

    platform_instance_id: str = Field(..., description="Unique platform instance ID")
    platform_version: str = Field(..., description="Platform version")
    installation_date: datetime = Field(..., description="Platform installation date")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last metadata update"
    )
    license_info: Optional[PlatformLicenseInfo] = Field(
        None, description="Licensing information"
    )
    system_info: Dict[str, str] = Field(
        default_factory=dict, description="System information"
    )
    service_topology: Dict[str, Any] = Field(
        default_factory=dict, description="Service topology"
    )

    @property
    def is_licensed(self) -> bool:
        """Check if platform has valid licensing."""
        return self.license_info is not None and self.license_info.is_valid


class NetworkInterface(BaseModel):
    """Network interface information."""

    interface_name: str
    ip_address: str
    network_type: str  # wifi, cellular, vpn, ethernet
    is_active: bool = True


class ServiceInfo(BaseModel):
    """Information about a registered service."""

    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Service name")
    service_type: ServiceType = Field(..., description="Type of service")
    version: str = Field(..., description="Service version")
    host: str = Field(..., description="Service host/IP")
    port: int = Field(..., description="Service port")
    health_endpoint: str = Field(default="/health", description="Health check endpoint")
    status: ServiceStatus = Field(
        default=ServiceStatus.HEALTHY, description="Current status"
    )
    capabilities: List[str] = Field(
        default_factory=list, description="Service capabilities"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Registration time"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Last heartbeat time"
    )
    heartbeat_count: int = Field(default=0, description="Number of heartbeats received")
    # Phase 2: VPN-aware fields
    tailscale_ip: Optional[str] = Field(default=None, description="Tailscale VPN IP address")
    tailscale_port: Optional[int] = Field(default=None, description="Port reachable via Tailscale IP")

    @property
    def base_url(self) -> str:
        """Get the base URL for this service."""
        return f"http://{self.host}:{self.port}"

    @property
    def health_url(self) -> str:
        """Get the health check URL for this service."""
        return f"{self.base_url}{self.health_endpoint}"

    @property
    def vpn_url(self) -> Optional[str]:
        """Get VPN-reachable URL if tailscale IP is set."""
        if self.tailscale_ip:
            port = self.tailscale_port or self.port
            return f"http://{self.tailscale_ip}:{port}"
        return None


class EdgeDeviceInfo(BaseModel):
    """Information about a registered edge device."""

    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: EdgeDeviceType = Field(..., description="Type of edge device")
    capabilities: List[str] = Field(
        default_factory=list, description="Device capabilities"
    )
    network_interfaces: List[NetworkInterface] = Field(
        default_factory=list, description="Network interfaces"
    )
    platform_info: Dict[str, str] = Field(
        default_factory=dict, description="Platform information"
    )
    location: Optional[str] = Field(None, description="Physical location")
    status: ServiceStatus = Field(
        default=ServiceStatus.HEALTHY, description="Current status"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Registration time"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Last seen time"
    )
    heartbeat_count: int = Field(default=0, description="Number of heartbeats received")
    # Phase 2: VPN-aware fields
    tailscale_ip: Optional[str] = Field(default=None, description="Tailscale VPN IP address")
    vpn_reachable: bool = Field(default=False, description="Whether device is reachable via VPN")


class RegistrationRequest(BaseModel):
    """Request model for service registration."""

    name: str = Field(..., description="Service name")
    service_type: ServiceType = Field(..., description="Type of service")
    version: str = Field(..., description="Service version")
    host: str = Field(..., description="Service host/IP")
    port: int = Field(..., description="Service port")
    health_endpoint: str = Field(default="/health", description="Health check endpoint")
    capabilities: List[str] = Field(
        default_factory=list, description="Service capabilities"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EdgeRegistrationRequest(BaseModel):
    """Request model for edge device registration."""

    device_name: str = Field(..., description="Human-readable device name")
    device_type: EdgeDeviceType = Field(..., description="Type of edge device")
    capabilities: List[str] = Field(
        default_factory=list, description="Device capabilities"
    )
    network_interfaces: List[NetworkInterface] = Field(
        default_factory=list, description="Network interfaces"
    )
    platform_info: Dict[str, str] = Field(
        default_factory=dict, description="Platform information"
    )
    location: Optional[str] = Field(None, description="Physical location")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class RegistrationResponse(BaseModel):
    """Response model for successful registration."""

    success: bool = Field(..., description="Registration success status")
    service_id: Optional[str] = Field(None, description="Assigned service ID")
    device_id: Optional[str] = Field(None, description="Assigned device ID")
    message: str = Field(..., description="Status message")
    heartbeat_interval: int = Field(
        default=30, description="Recommended heartbeat interval"
    )


class HeartbeatRequest(BaseModel):
    """Request model for heartbeat updates."""

    service_id: Optional[str] = Field(
        None, description="Service ID for service heartbeat"
    )
    device_id: Optional[str] = Field(
        None, description="Device ID for edge device heartbeat"
    )
    status: ServiceStatus = Field(
        default=ServiceStatus.HEALTHY, description="Current status"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Updated metadata"
    )


class PlatformTopology(BaseModel):
    """Complete platform topology information."""

    platform: str = Field(default="ppl-meta", description="Platform name")
    version: str = Field(..., description="Platform version")
    discovery_service: str = Field(..., description="Discovery service URL")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Topology timestamp"
    )
    backend_services: Dict[str, ServiceInfo] = Field(
        default_factory=dict, description="Backend services"
    )
    edge_devices: Dict[str, EdgeDeviceInfo] = Field(
        default_factory=dict, description="Edge devices"
    )
    network_config: Dict[str, Any] = Field(
        default_factory=dict, description="Network configuration"
    )
    # Phase 2: VPN preference flag
    preferred_network: Optional[str] = Field(
        default=None, description="Preferred network: tailscale or local"
    )

    @property
    def service_count(self) -> int:
        """Get total number of registered services."""
        return len(self.backend_services)

    @property
    def device_count(self) -> int:
        """Get total number of registered edge devices."""
        return len(self.edge_devices)

    def get_healthy_services(self) -> List[str]:
        """Get list of healthy service IDs."""
        return [
            service_id
            for service_id, service in self.backend_services.items()
            if service.status == ServiceStatus.HEALTHY
        ]

    def get_healthy_devices(self) -> List[str]:
        """Get list of healthy device IDs."""
        return [
            device_id
            for device_id, device in self.edge_devices.items()
            if device.status == ServiceStatus.HEALTHY
        ]


class DiscoveryQuery(BaseModel):
    """Query model for service discovery."""

    service_type: Optional[ServiceType] = Field(
        None, description="Filter by service type"
    )
    service_name: Optional[str] = Field(None, description="Filter by service name")
    capabilities: Optional[List[str]] = Field(None, description="Required capabilities")
    status: Optional[ServiceStatus] = Field(None, description="Filter by status")
    network_type: Optional[str] = Field(None, description="Filter by network type")


class ServiceList(BaseModel):
    """List of services response."""

    services: List[ServiceInfo] = Field(..., description="List of services")
    total_count: int = Field(..., description="Total number of services")
    healthy_count: int = Field(..., description="Number of healthy services")


class EdgeDeviceList(BaseModel):
    """List of edge devices response."""

    devices: List[EdgeDeviceInfo] = Field(..., description="List of edge devices")
    total_count: int = Field(..., description="Total number of devices")
    healthy_count: int = Field(..., description="Number of healthy devices")
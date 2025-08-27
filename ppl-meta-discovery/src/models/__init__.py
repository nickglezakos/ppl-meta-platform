"""Models package for PPL Meta Discovery Service."""

from .service_models import (
    DiscoveryQuery,
    EdgeDeviceInfo,
    EdgeDeviceList,
    EdgeDeviceType,
    EdgeRegistrationRequest,
    HeartbeatRequest,
    LicenseStatus,
    LicenseType,
    NetworkInterface,
    PlatformLicenseInfo,
    PlatformMetadata,
    PlatformTopology,
    RegistrationRequest,
    RegistrationResponse,
    ServiceInfo,
    ServiceList,
    ServiceStatus,
    ServiceType,
)

__all__ = [
    # Enums
    "ServiceType",
    "ServiceStatus",
    "EdgeDeviceType",
    "LicenseStatus",
    "LicenseType",
    # Core Models
    "NetworkInterface",
    "ServiceInfo",
    "EdgeDeviceInfo",
    "PlatformLicenseInfo",
    "PlatformMetadata",
    # Request/Response Models
    "RegistrationRequest",
    "EdgeRegistrationRequest",
    "RegistrationResponse",
    "HeartbeatRequest",
    # Discovery Models
    "PlatformTopology",
    "DiscoveryQuery",
    "ServiceList",
    "EdgeDeviceList",
]

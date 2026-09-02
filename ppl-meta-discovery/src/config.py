"""Configuration settings for PPL Meta Discovery Service."""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Service Configuration
    SERVICE_NAME: str = "ppl-meta-discovery"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8006
    
    # Security Configuration
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Installation Authentication (Issue #8)
    # Shared secret used to derive HMAC installation tokens. Must match the
    # Authority (INSTALLATION_AUTH_SECRET) that issues them.
    INSTALLATION_AUTH_SECRET: str = "ppl-meta-installation-auth-secret-dev"
    # When true, register/heartbeat/topology endpoints require a valid
    # Authorization: Bearer <HMAC token> + X-Installation-Uuid header.
    AUTH_ENFORCE: bool = False

    # Local onboarding / one-time enrollment token (scenario b, LAN auto-discovery)
    # The discovery service can mint a short-lived single-use enrollment token on
    # the Authority's behalf so a LAN device can self-register without manual paste.
    # AUTHORITY_ADMIN_TOKEN is optional; when unset the LAN auto-discovery endpoint
    # returns 404 and the device falls back to pasting a token from the network screen.
    AUTHORITY_BASE_URL: str = "https://authority.eyenet-vision.com"
    AUTHORITY_ADMIN_TOKEN: str = ""
    # Installation the platform mints onboarding tokens for (e.g. "tenant-a").
    ONBOARDING_INSTALLATION_UUID: str = "tenant-a"
    # Default node_type assigned to LAN-onboarded signage devices.
    ONBOARDING_NODE_TYPE: str = "signage"
    # Token TTL for LAN auto-discovery minted tokens (seconds).
    ONBOARDING_TOKEN_TTL_SECONDS: int = 300
    
    # Discovery Configuration
    ENABLE_MULTICAST: bool = True
    MULTICAST_GROUP: str = "224.1.1.1"
    MULTICAST_PORT: int = 12345
    
    # Health Monitoring
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    SERVICE_TIMEOUT: int = 10  # seconds
    MAX_MISSED_HEARTBEATS: int = 3
    
    # Registry Configuration
    REGISTRY_CLEANUP_INTERVAL: int = 60  # seconds
    EDGE_DEVICE_TIMEOUT: int = 300  # 5 minutes
    SERVICE_REGISTRY_SIZE: int = 100
    EDGE_REGISTRY_SIZE: int = 1000
    
    # Network Configuration
    VPN_DISCOVERY_ENABLED: bool = True
    TAILSCALE_DOMAINS: List[str] = ["*.tailnet.ts.net"]
    OPENVPN_RANGES: List[str] = ["10.8.0.0/24", "192.168.255.0/24"]
    
    # Logging Configuration  
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

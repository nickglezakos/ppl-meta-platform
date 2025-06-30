"""
PPL Meta Gateway Configuration
"""
import os
from pathlib import Path
from typing import List, Dict, Any

from pydantic_settings import BaseSettings
from pydantic import field_validator

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Basic Configuration
    environment: str = "development"
    debug: bool = False
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    service_name: str = "ppl-meta-gateway"
    service_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8080
    
    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Service URLs
    user_service_url: str = "http://ppl-meta-node:8001"
    media_service_url: str = "http://ppl-meta-media:8000"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Service Discovery
    service_discovery_enabled: bool = True
    consul_host: str = "localhost"
    consul_port: int = 8500
    
    # Nginx Configuration
    nginx_config_path: str = "/etc/nginx/conf.d"
    nginx_reload_command: str = "nginx -s reload"
    
    # Load Balancing
    enable_load_balancing: bool = True
    health_check_interval: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Monitoring
    metrics_enabled: bool = True
    prometheus_port: int = 9090
    
    # Mesh VPN
    mesh_vpn_enabled: bool = False
    mesh_vpn_interface: str = "wg0"
    
    # Service Registry Configuration
    service_registry: Dict[str, Dict[str, Any]] = {
        "ppl-meta-node": {
            "name": "User Management Service",
            "base_url": "http://ppl-meta-node:8001",
            "health_endpoint": "/health",
            "routes": ["/auth", "/users", "/api/v1/auth", "/api/v1/users"],
            "load_balancer": "round_robin"
        },
        "ppl-meta-media": {
            "name": "Media Processing Service", 
            "base_url": "http://ppl-meta-media:8000",
            "health_endpoint": "/health",
            "routes": ["/api/v1/media", "/media"],
            "load_balancer": "round_robin"
        }
    }
    
    # Health check endpoints
    health_check_paths: List[str] = [
        "/health",
        "/health/ready",
        "/health/live"
    ]
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if v == "your-secret-key-change-in-production":
            raise ValueError("Please change the default secret key")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# CORS settings
CORS_SETTINGS = {
    "allow_origins": ["*"] if settings.debug else ["https://yourdomain.com"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

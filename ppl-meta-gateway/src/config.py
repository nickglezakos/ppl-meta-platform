"""
PPL Meta Gateway Configuration
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Debug: Print environment variables
print(f"DEBUG: SECRET_KEY from env: {os.getenv('SECRET_KEY', 'NOT SET')}")
secret_env_vars = [(k, v) for k, v in os.environ.items() if "SECRET" in k]
print(f"DEBUG: All env vars starting with SECRET: {secret_env_vars}")

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    def validate_database_url(self) -> bool:
        """Validate the database connection string format and components."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.get_database_url())

            if not parsed.scheme.startswith("postgresql"):
                logger.error("Database URL must use postgresql:// scheme")
                return False

            if not parsed.username:
                logger.error("Database URL missing username")
                return False

            if not parsed.password:
                logger.error("Database URL missing password")
                return False

            if not parsed.hostname:
                logger.error("Database URL missing hostname")
                return False

            if not parsed.path or parsed.path == "/":
                logger.error("Database URL missing database name")
                return False

            logger.info("Database URL validation passed")
            return True

        except Exception as e:
            logger.error(f"Database URL validation failed: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get database connection information for debugging."""
        url = self.get_database_url()
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "username": parsed.username,
                "database": parsed.path.lstrip("/"),
                "url_masked": (
                    url.replace(parsed.password or "", "*****")
                    if parsed.password
                    else url
                ),
            }
        except Exception:
            return {"error": "Failed to parse database URL"}

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",
    )

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
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring
    metrics_enabled: bool = True
    prometheus_port: int = 9090

    # Advanced Gateway Features
    # Rate Limiting Configuration
    rate_limiting_enabled: bool = True
    default_rate_limit: str = "100/minute"
    redis_rate_limiting: bool = True

    # Circuit Breaker Configuration
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 30

    # Request Tracing Configuration
    request_tracing_enabled: bool = True
    trace_header: str = "X-Trace-ID"
    span_header: str = "X-Span-ID"
    parent_span_header: str = "X-Parent-Span-ID"

    # Request/Response Transformation
    request_transformation_enabled: bool = True
    response_transformation_enabled: bool = True

    # OpenTelemetry Distributed Tracing Configuration
    tracing_enabled: bool = False  # Disabled - Jaeger not running
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    tracing_sampling_rate: float = 1.0
    tracing_service_name: str = "ppl-meta-gateway"
    tracing_excluded_urls: str = "health,metrics,docs,redoc"

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
            "load_balancer": "round_robin",
        },
        "ppl-meta-media": {
            "name": "Media Processing Service",
            "base_url": "http://ppl-meta-media:8000",
            "health_endpoint": "/health",
            "routes": ["/api/v1/media", "/media"],
            "load_balancer": "round_robin",
        },
    }

    # Health check endpoints
    health_check_paths: List[str] = ["/health", "/health/ready", "/health/live"]

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        # Temporarily disabled for debugging environment variable loading
        # if v == "your-secret-key-change-in-production":
        #     raise ValueError("Please change the default secret key")
        print(f"DEBUG: Secret key loaded: {v}")
        return v


# Global settings instance
settings = Settings()

# CORS settings
CORS_SETTINGS = {
    "allow_origins": ["*"] if settings.debug else ["https://yourdomain.com"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

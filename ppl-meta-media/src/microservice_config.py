"""
Microservice configuration and settings.
"""
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# API Configuration
API_V1_PREFIX = "/api/v1"
SERVICE_NAME = "ppl-meta-media"
SERVICE_VERSION = "1.0.0"

# Microservices settings
MICROSERVICE_CONFIG = {
    "service_discovery": {
        "enabled": os.getenv("SERVICE_DISCOVERY_ENABLED", "false").lower() == "true",
        "registry_url": os.getenv("SERVICE_REGISTRY_URL", "http://consul:8500"),
    },
    "monitoring": {
        "metrics_enabled": os.getenv("METRICS_ENABLED", "true").lower() == "true",
        "tracing_enabled": os.getenv("TRACING_ENABLED", "true").lower() == "true",
    },
    "circuit_breaker": {
        "failure_threshold": int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")),
        "timeout": int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60")),
    }
}

# Health check endpoints
HEALTH_CHECK_PATHS = [
    "/health",
    "/health/ready", 
    "/health/live"
]

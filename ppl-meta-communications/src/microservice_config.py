"""
Microservice configuration and settings for Communications Service.
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# API Configuration
API_V1_PREFIX = "/api/v1"
SERVICE_NAME = "ppl-meta-communications"
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
    },
}

# Service registry configuration for Consul-based service discovery
SERVICE_REGISTRY = {
    "name": "ppl-meta-communications",
    "version": "1.0.0",
    "host": "0.0.0.0",
    "port": 8009,
    "health_check": "http://0.0.0.0:8009/health",
    "tags": ["communications", "email", "webhook", "notifications", "microservice"],
}

# Consul configuration
CONSUL_CONFIG = {
    "host": os.getenv("CONSUL_HOST", "consul"),
    "port": int(os.getenv("CONSUL_PORT", "8500")),
    "enabled": os.getenv("CONSUL_ENABLED", "true").lower() == "true",
}

# Health check endpoints
HEALTH_CHECK_PATHS = ["/health", "/health/ready", "/health/live"]

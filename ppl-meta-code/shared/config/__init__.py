"""Shared configuration utilities for PPL Meta Platform services."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class BaseServiceConfig(BaseSettings):
    """Base configuration for all PPL Meta Platform services."""
    
    # Service identity
    service_name: str
    service_version: str = "1.0.0"
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int
    debug: bool = False
    
    # Database
    database_url: str
    
    # Service discovery
    consul_host: str = "consul"
    consul_port: int = 8500
    service_discovery_enabled: bool = True
    
    # Security
    secret_key: str
    jwt_secret: str = ""
    
    # External services
    redis_url: str = "redis://redis:6379"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_service_config(service_name: str, default_port: int) -> BaseServiceConfig:
    """Get configuration for a specific service."""
    config = BaseServiceConfig(
        service_name=service_name,
        port=default_port
    )
    return config

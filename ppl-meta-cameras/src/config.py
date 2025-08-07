"""
Configuration module for PPL Meta Cameras microservice.
"""

import os
from typing import Optional


class Config:
    """Configuration class for the cameras microservice."""

    # Basic service configuration
    SERVICE_NAME: str = "ppl-meta-cameras"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8005"))

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://nickgklezakos@localhost:5432/ppl_meta_cameras"
    )
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"

    # Authentication configuration
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # Service discovery configuration (Consul)
    CONSUL_ENABLED: bool = os.getenv("CONSUL_ENABLED", "false").lower() == "true"
    CONSUL_HOST: str = os.getenv("CONSUL_HOST", "localhost")
    CONSUL_PORT: int = int(os.getenv("CONSUL_PORT", "8500"))

    # Camera detection configuration
    CAMERA_SCAN_TIMEOUT: int = int(os.getenv("CAMERA_SCAN_TIMEOUT", "30"))
    CAMERA_CONNECTION_TIMEOUT: int = int(os.getenv("CAMERA_CONNECTION_TIMEOUT", "10"))
    MAX_SIMULTANEOUS_CAMERAS: int = int(os.getenv("MAX_SIMULTANEOUS_CAMERAS", "10"))
    DEFAULT_CAMERA_RESOLUTION: str = os.getenv("DEFAULT_CAMERA_RESOLUTION", "1280x720")
    DEFAULT_CAMERA_FPS: int = int(os.getenv("DEFAULT_CAMERA_FPS", "30"))

    # Video streaming configuration
    STREAM_BUFFER_SIZE: int = int(os.getenv("STREAM_BUFFER_SIZE", "1024"))
    STREAM_QUALITY: str = os.getenv("STREAM_QUALITY", "medium")  # low, medium, high

    # Storage configuration
    VIDEO_STORAGE_PATH: str = os.getenv("VIDEO_STORAGE_PATH", "/tmp/cameras/videos")
    SNAPSHOT_STORAGE_PATH: str = os.getenv(
        "SNAPSHOT_STORAGE_PATH", "/tmp/cameras/snapshots"
    )

    # Security configuration
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "*").split(",")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

    # Health check configuration
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))


# Global configuration instance
_config = None


def get_config() -> Config:
    """Get configuration instance (singleton pattern)."""
    global _config
    if _config is None:
        _config = Config()
    return _config


# Configuration for different environments
class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"
    DATABASE_ECHO = True


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    LOG_LEVEL = "INFO"
    DATABASE_ECHO = False


class TestConfig(Config):
    """Test environment configuration."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"
    DATABASE_URL = "sqlite:///test_cameras.db"


def get_config_by_env(env: Optional[str] = None) -> Config:
    """Get configuration based on environment."""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")

    config_map = {
        "development": DevelopmentConfig(),
        "production": ProductionConfig(),
        "test": TestConfig(),
    }

    return config_map.get(env.lower(), DevelopmentConfig())

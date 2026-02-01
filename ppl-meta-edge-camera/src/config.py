"""Configuration management for edge camera."""
import os
import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DeviceConfig(BaseModel):
    """Device configuration."""
    id: str
    name: str
    location: str
    type: str = "usb"


class CameraResolution(BaseModel):
    """Camera resolution settings."""
    width: int = 1280
    height: int = 720


class CameraConfig(BaseModel):
    """Camera configuration."""
    device_id: int = 0
    resolution: CameraResolution = Field(default_factory=CameraResolution)
    fps: int = 15
    format: str = "mjpeg"
    buffer_size: int = 10


class PlatformConfig(BaseModel):
    """Platform connection configuration."""
    cameras_url: str
    discovery_url: str
    health_check_interval: int = 30
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    api_key: Optional[str] = None


class StreamConfig(BaseModel):
    """Stream configuration."""
    encoding: str = "mjpeg"
    quality: int = 80
    chunk_size: int = 4096


class ServerConfig(BaseModel):
    """Local server configuration."""
    host: str = "0.0.0.0"
    port: int = 9001


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class AppConfig(BaseSettings):
    """Application configuration."""
    device: DeviceConfig
    camera: CameraConfig
    platform: PlatformConfig
    stream: StreamConfig
    server: ServerConfig
    logging: LoggingConfig

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        # Default to config/default.yaml
        base_dir = Path(__file__).parent.parent
        config_path = base_dir / "config" / "default.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    # Override with environment variables if set
    if os.getenv("DEVICE_ID"):
        config_dict['device']['id'] = os.getenv("DEVICE_ID")
    if os.getenv("PLATFORM_CAMERAS_URL"):
        config_dict['platform']['cameras_url'] = os.getenv("PLATFORM_CAMERAS_URL")
    if os.getenv("PLATFORM_DISCOVERY_URL"):
        config_dict['platform']['discovery_url'] = os.getenv("PLATFORM_DISCOVERY_URL")
    
    return AppConfig(**config_dict)


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: AppConfig):
    """Set global config instance."""
    global _config
    _config = config

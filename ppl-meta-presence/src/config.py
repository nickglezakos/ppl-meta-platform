"""Configuration for PPL Meta Presence."""

from __future__ import annotations

import os


def _default_detection_backend_mode() -> str:
    return "auto" if os.getenv("ENVIRONMENT", "development") == "development" else "gateway"


def _default_allowed_camera_statuses() -> str:
    if os.getenv("ENVIRONMENT", "development") == "development":
        return "available,disconnected,connected"
    return "available,connected"


class Config:
    SERVICE_NAME: str = "ppl-meta-presence"
    VERSION: str = os.getenv("PRESENCE_SERVICE_VERSION", "0.1.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PRESENCE_SERVICE_PORT", "8011"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://nickgklezakos@localhost:5432/ppl_meta_presence",
    )
    COMMUNICATIONS_SERVICE_URL: str = os.getenv(
        "COMMUNICATIONS_SERVICE_URL",
        "http://localhost:8009/api/v1",
    ).rstrip("/")
    NODE_SERVICE_URL: str = os.getenv(
        "NODE_SERVICE_URL",
        "http://localhost:8001/api/v1",
    ).rstrip("/")
    SERVICE_SECRET: str | None = os.getenv("SERVICE_SECRET") or os.getenv(
        "NODE_SERVICE_SECRET"
    )
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    DETECTION_BACKEND_MODE: str = os.getenv(
        "PRESENCE_DETECTION_BACKEND_MODE",
        _default_detection_backend_mode(),
    ).lower()
    PREFERRED_CAMERA_TYPES: list[str] = [
        camera_type.strip().upper()
        for camera_type in os.getenv(
            "PRESENCE_PREFERRED_CAMERA_TYPES",
            "USB,EDGE,RTSP,MOBILE",
        ).split(",")
        if camera_type.strip()
    ]
    PREFERRED_CAMERA_NAMES: list[str] = [
        camera_name.strip().lower()
        for camera_name in os.getenv(
            "PRESENCE_PREFERRED_CAMERA_NAMES",
            "",
        ).split(",")
        if camera_name.strip()
    ]
    ALLOWED_CAMERA_STATUSES: list[str] = [
        status.strip().lower()
        for status in os.getenv(
            "PRESENCE_ALLOWED_CAMERA_STATUSES",
            _default_allowed_camera_statuses(),
        ).split(",")
        if status.strip()
    ]


config = Config()
"""Configuration for PPL Meta Models catalog service."""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    SERVICE_NAME: str = "ppl-meta-models"
    VERSION: str = os.getenv("MODELS_SERVICE_VERSION", "0.1.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("MODELS_SERVICE_PORT", "8013"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATABASE_URL: str = os.getenv(
        "MODELS_DATABASE_URL",
        f"sqlite:///{Path(__file__).resolve().parents[1] / 'ppl_meta_models.db'}",
    )
    NODE_SERVICE_URL: str = os.getenv(
        "NODE_SERVICE_URL",
        "http://localhost:8001/api/v1",
    ).rstrip("/")
    SERVICE_SECRET: str | None = os.getenv("SERVICE_SECRET") or os.getenv(
        "NODE_SERVICE_SECRET"
    )
    # When true, catalog mutations require eyenet_mv_models from Node cache.
    REQUIRE_LICENCE: bool = os.getenv("MODELS_REQUIRE_LICENCE", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    ARTIFACT_ROOT: Path = Path(
        os.getenv(
            "MODELS_ARTIFACT_ROOT",
            str(Path(__file__).resolve().parents[1] / "artifact_store"),
        )
    )
    MAX_UPLOAD_BYTES: int = int(os.getenv("MODELS_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
    VISION_SERVICE_URL: str = os.getenv(
        "VISION_SERVICE_URL", "http://localhost:8003"
    ).rstrip("/")
    ALLOWED_UPLOAD_EXTENSIONS: set[str] = {".xml", ".onnx", ".dat"}


config = Config()

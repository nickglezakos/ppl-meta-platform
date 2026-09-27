"""PPL Meta Models catalog service."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import socket
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router as catalog_router
from catalog import seed_builtins
from config import config
from database import SessionLocal, create_tables, test_connection

src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

logger = logging.getLogger(__name__)

try:
    from shared.service_discovery import deregister_service, register_service

    _service_discovery_available = True
except ImportError:
    _service_discovery_available = False
    register_service = None  # type: ignore
    deregister_service = None  # type: ignore


def _detect_host() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
        s.close()
        return host
    except OSError:
        return socket.gethostbyname(socket.gethostname())


@asynccontextmanager
async def lifespan(_application: FastAPI):
    create_tables()
    db = SessionLocal()
    try:
        seed_builtins(db)
    finally:
        db.close()

    if _service_discovery_available and register_service is not None:
        try:
            await register_service(
                name=config.SERVICE_NAME,
                service_type="backend",
                version=config.VERSION,
                host=_detect_host(),
                port=config.PORT,
                health_endpoint="/health",
                capabilities=["models", "catalog", "onnx"],
                metadata={
                    "version": config.VERSION,
                    "environment": config.ENVIRONMENT,
                },
            )
            logger.info(
                "Successfully registered %s with discovery service",
                config.SERVICE_NAME,
            )
        except Exception as exc:
            logger.warning("Failed to register with discovery service: %s", exc)

    yield

    if _service_discovery_available and deregister_service is not None:
        try:
            await deregister_service(config.SERVICE_NAME)
            logger.info("Service deregistered from discovery service")
        except Exception as exc:
            logger.warning("Failed to deregister from discovery: %s", exc)


app = FastAPI(
    title="PPL Meta Models Service",
    description="Detection model catalog, assignments, and later training jobs",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog_router, prefix="/api/v1/mv-models", tags=["mv-models"])


@app.get("/")
async def root():
    return {
        "service": "ppl-meta-models",
        "version": config.VERSION,
        "endpoints": {
            "health": "/health",
            "catalog": "/api/v1/mv-models",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "service": "ppl-meta-models",
        "status": "healthy" if test_connection() else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": config.VERSION,
        "database": "connected" if test_connection() else "unavailable",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )

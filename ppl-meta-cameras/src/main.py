"""
PPL Meta Cameras - Camera Detection and Management Microservice
Main application entry point.
"""

import os
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Add the parent directory to Python path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Local logging implementation
import logging

from src.api.health import router as health_router
from src.api.v1.routes import v1_router
from src.config import get_config
from src.database import Base, engine, test_connection

# Import all models for table creation
from src.models.camera import Camera, CameraCapability, CameraSession

# Try to import the shared service discovery module
try:
    from shared.service_discovery import register_service

    service_discovery_available = True
except ImportError:
    service_discovery_available = False

# Initialize configuration
config = get_config()

# Setup basic logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ppl-meta-cameras")

# Global service discovery client
service_discovery_client = None

if service_discovery_available:
    logger.info("Service discovery module available")
else:
    logger.warning("Service discovery module not available, using fallback mode")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager for startup and shutdown tasks."""
    global service_discovery_client
    logger.info("Starting PPL Meta Cameras Service...")

    # Test database connection
    try:
        await test_connection()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        # Don't exit completely in development
        if config.ENVIRONMENT == "production":
            raise

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

    # Skip metrics initialization for now
    logger.info("Metrics initialization skipped")

    # Initialize service discovery if available
    # Initialize service discovery if available
    if service_discovery_available:
        try:
            from shared.service_discovery import register_service

            await register_service(
                name="ppl-meta-cameras",
                service_type="backend",
                version="1.0.0",
                host="0.0.0.0",
                port=config.PORT,
                health_endpoint="/health",
                capabilities=["cameras", "video-streaming", "detection"],
                metadata={
                    "version": "1.0.0",
                    "environment": "development",
                    "features": "camera_management,video_streaming,motion_detection",
                },
            )
            logger.info(
                "Successfully registered ppl-meta-cameras with discovery service"
            )
        except Exception as e:
            logger.error(f"Failed to register with discovery service: {e}")

    logger.info("PPL Meta Cameras Service startup completed")

    yield

    # Shutdown tasks
    logger.info("Shutting down PPL Meta Cameras Service...")

    # Deregister service
    if service_discovery_available:
        try:
            from shared.service_discovery import deregister_service

            await deregister_service("ppl-meta-cameras")
            logger.info("Service deregistered from discovery service")
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")

    logger.info("PPL Meta Cameras Service shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta Cameras",
    description="Camera Detection and Management Microservice for PPL Meta Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]  # Configure appropriately
)

# Skip metrics middleware for now
logger.info("Metrics middleware skipped")


# Add exception handling middleware
@app.middleware("http")
async def exception_handling_middleware(request: Request, call_next):
    """Global exception handling middleware."""
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception in {request.url}: {e}")
        process_time = time.time() - start_time
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "timestamp": time.time(),
                "process_time": process_time,
            },
            headers={"X-Process-Time": str(process_time)},
        )


# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(v1_router, prefix="/api/v1", tags=["API v1"])

# Skip metrics endpoint for now
logger.info("Metrics endpoint skipped")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint returning service information."""
    return {
        "service": "PPL Meta Cameras",
        "version": "1.0.0",
        "description": "Camera Detection and Management Microservice",
        "status": "running",
        "timestamp": time.time(),
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.PORT,
        reload=config.ENVIRONMENT == "development",
        log_level=config.LOG_LEVEL.lower(),
        access_log=True,
    )

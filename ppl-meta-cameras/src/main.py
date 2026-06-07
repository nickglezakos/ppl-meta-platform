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
from src.models.recording_session import (
    RecordingFile,
    RecordingMetadata,
    RecordingSession,
    RecordingStatus,
)

# Try to import the shared service discovery module
try:
    sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/shared")
    service_discovery_available = True
except ImportError:
    service_discovery_available = False

# Initialize configuration
config = get_config()

# Setup logging with file handler
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ppl-meta-cameras.log")

# Configure logging with both file and console handlers
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        ),
        logging.StreamHandler()
    ]
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

    # Start mobile camera cleanup service
    try:
        from src.services.mobile_cleanup import mobile_cleanup_service

        await mobile_cleanup_service.start()
        logger.info("Mobile camera cleanup service started successfully")
    except Exception as e:
        logger.error(f"Failed to start mobile camera cleanup service: {e}")

    # Clean up stale recording sessions on startup
    try:
        from src.services.recording_session_service import RecordingSessionService
        from src.database import SessionLocal
        
        db = SessionLocal()
        try:
            session_service = RecordingSessionService(db)
            cleaned_count = session_service.cleanup_stale_sessions()
            logger.info(f"✅ Cleaned up {cleaned_count} stale recording sessions on startup")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to cleanup stale recording sessions: {e}")
    
    # Initialize Redis status notification service
    try:
        from src.services.status_notification_service import initialize_status_service
        await initialize_status_service()
        logger.info("✅ Redis status notification service initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis status service not available: {e}")
        logger.info("Status updates will work locally but not across instances")

    # Start Celery worker for instant detection (background process)
    celery_process = None
    try:
        import subprocess
        
        # Get venv python path
        venv_path = os.path.join(os.path.dirname(__file__), "..", "venv", "bin", "python")
        if not os.path.exists(venv_path):
            # Fallback to system python
            venv_path = sys.executable
        
        # Start Celery worker as background process
        celery_log_file = os.path.join(log_dir, "celery-instant-detection.log")
        celery_enable_beat = os.getenv("CAMERAS_CELERY_ENABLE_BEAT", "true").lower() == "true"
        celery_cmd = [
            venv_path, "-m", "celery",
            "-A", "src.tasks.instant_detection_tasks",
            "worker",
            "--loglevel=INFO",
            "--concurrency=2",
            "--queues=instant_detection_queue",
            f"--logfile={celery_log_file}",
            "--detach"
        ]

        # Run beat in-process for local orchestration of periodic reconciliation tasks.
        if celery_enable_beat:
            celery_cmd.append("--beat")
        
        celery_process = subprocess.Popen(
            celery_cmd,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment to check if it started
        import asyncio
        await asyncio.sleep(2)
        
        if celery_process.poll() is None or celery_process.returncode == 0:
            logger.info("✅ Celery worker for instant detection started successfully")
        else:
            logger.warning("⚠️ Celery worker may have failed to start, check logs")
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        logger.info("Instant detection will fall back to synchronous processing")

    # Skip metrics initialization for now
    logger.info("Metrics initialization skipped")

    # Initialize service discovery if available
    if service_discovery_available:
        try:
            import socket

            from service_discovery.ppl_discovery_client import (
                DiscoveryClient,
                ServiceConfig,
            )

            # Detect actual network IP for registration
            try:
                # Connect to a remote address to determine local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                detected_ip = s.getsockname()[0]
                s.close()
            except Exception:
                # Fallback to hostname resolution
                detected_ip = socket.gethostbyname(socket.gethostname())

            # Create discovery client
            discovery_client = DiscoveryClient("http://localhost:8006")

            # Create service configuration
            service_config = ServiceConfig(
                service_name="ppl-meta-cameras",
                service_id="ppl-meta-cameras-001",
                host=detected_ip,
                port=config.PORT,
                health_endpoint="/health",
                tags=["cameras", "video-streaming", "detection"],
                metadata={
                    "service_type": "backend",
                    "version": "1.0.0",
                    "environment": "development",
                    "features": "camera_management,video_streaming,detection",
                },
            )

            # Register service
            await discovery_client.register_service(service_config)
            logger.info(
                "Successfully registered ppl-meta-cameras with discovery service"
            )

            # Store client for cleanup
            global service_discovery_client
            service_discovery_client = discovery_client

        except Exception as e:
            logger.error(f"Failed to register with discovery service: {e}")

    logger.info("PPL Meta Cameras Service startup completed")

    yield

    # Shutdown tasks
    logger.info("Shutting down PPL Meta Cameras Service...")

    # Stop mobile camera cleanup service
    try:
        from src.services.mobile_cleanup import mobile_cleanup_service

        await mobile_cleanup_service.stop()
        logger.info("Mobile camera cleanup service stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping mobile camera cleanup service: {e}")
    
    # Shutdown Redis status notification service
    try:
        from src.services.status_notification_service import shutdown_status_service
        await shutdown_status_service()
        logger.info("Redis status notification service stopped")
    except Exception as e:
        logger.error(f"Error stopping status notification service: {e}")

    # Deregister service
    if service_discovery_available and service_discovery_client:
        try:
            await service_discovery_client.deregister_service("ppl-meta-cameras-001")
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
app.include_router(health_router, tags=["Health"])
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

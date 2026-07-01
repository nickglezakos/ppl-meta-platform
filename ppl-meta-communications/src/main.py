"""
PPL Meta Communications Service - Main application entry point.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging FIRST
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
log_dir = os.path.join(workspace_root, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ppl-meta-communications.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"📝 Communications service logging to: {log_file}")
print(f"📝 Communications service logging to: {log_file}", flush=True)

# Add the parent directory to Python path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from .config import get_config
from .database import Base, engine, test_connection
from .microservice_config import CONSUL_CONFIG

# Import models for table creation
from .models.communication_log import CommunicationLog, CommunicationType, CommunicationStatus
from .models.email_template import EmailTemplate
from .models.webhook_config import WebhookConfig
from .models.email_settings import EmailSettings

# Import routes
from .routes.email import router as email_router
from .routes.webhook import router as webhook_router
from .routes.notification import router as notification_router
from .routes.audit import router as audit_router
from .routes.email_settings import router as email_settings_router
from .api.health import router as health_router
from .api.vpn import router as vpn_router

# Try to import shared modules
try:
    from shared.service_discovery import register_service
    service_discovery_available = True
except ImportError:
    service_discovery_available = False
    logger.warning("Service discovery module not available, using fallback mode")

# Initialize configuration
config = get_config()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager for startup and shutdown tasks."""
    logger.info("Starting PPL Meta Communications Service...")

    # Initialize service discovery if available
    if service_discovery_available:
        try:
            import socket

            # Detect actual network IP for registration
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                detected_ip = s.getsockname()[0]
                s.close()
            except Exception:
                detected_ip = socket.gethostbyname(socket.gethostname())

            # Phase 3: Detect Tailscale IP for VPN registration
            tailscale_ip = None
            try:
                import json, subprocess
                result = subprocess.run(
                    ["tailscale", "status", "--json"],
                    capture_output=True, text=True, timeout=3,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    ips = data.get("Self", {}).get("TailscaleIPs", [])
                    tailscale_ip = ips[0] if ips else None
                if tailscale_ip:
                    logger.info(f"Detected Tailscale IP: {tailscale_ip}")
            except Exception:
                pass

            await register_service(
                name="ppl-meta-communications",
                service_type="backend",
                version="1.0.0",
                host=detected_ip,
                port=8009,
                health_endpoint="/health",
                capabilities=["email", "webhooks", "notifications", "audit-logging"],
                metadata={
                    "version": "1.0.0",
                    "environment": config.ENVIRONMENT,
                    "features": "email,webhooks,push_notifications,audit_logging",
                    "tailscale_ip": tailscale_ip,
                },
            )
            logger.info("Successfully registered ppl-meta-communications with discovery service")
        except Exception as e:
            logger.error(f"Failed to register with discovery service: {e}")
            logger.info("Continuing without service discovery")

    # Log configuration
    config.log_configuration()

    # Test database connection
    max_retries = 5
    for attempt in range(max_retries):
        try:
            logger.info(f"Testing database connection (attempt {attempt + 1}/{max_retries})...")
            if test_connection():
                logger.info("✅ Database connection successful")
                break
            else:
                raise Exception("Connection test returned False")
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
            else:
                logger.error("Failed to connect to database after all retries")
                logger.error("Service will start but database operations will fail")

    # Create database tables
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        logger.error("Service will start but database operations may fail")

    logger.info("✅ Communications Service startup complete")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    logger.info("Shutting down Communications Service...")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta Communications Service",
    description="Communications microservice for email, webhooks, notifications, and audit logging",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(email_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(email_settings_router)
app.include_router(vpn_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ppl-meta-communications",
        "version": "1.0.0",
        "status": "operational",
        "capabilities": ["email", "webhooks", "notifications", "audit-logging"]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )

"""Main entry point for the PPL Meta Node - User Management Service."""

import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Add the parent directory to Python path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.logging import setup_logging
from shared.metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics
from shared.validation import handle_validation_error

try:
    from src.config import settings
    from src.database import SessionLocal, engine
    from src.microservice_config import CONSUL_CONFIG
    from src.models.user import Base
    from src.services.user_service import create_user, get_user_by_email

    logger.info("Successfully imported core modules")
except Exception as e:
    logger.error(f"Failed to import core modules: {e}")
    sys.exit(1)

from src.api import app_settings, backup, capabilities, logs, otp, roles

# Import API routers
from src.api.v1.routes import router as v1_router
from src.models.app_setting import AppSetting

# Import models to ensure they're created
from src.models.installation_info import InstallationInfo
from src.models.log import Log
from src.models.otp import OTP
from src.models.role import Capability, Role, RoleCapability, UserRole
from src.models.user import User, UserAction
from src.schemas.user import UserCreate
from src.services.role_service import ensure_admin_role

# Setup standardized logging
logger = setup_logging(
    service_name="ppl-meta-node",
    log_level=settings.LOG_LEVEL.upper(),
    log_format=settings.LOG_FORMAT.lower(),
    log_file="/app/logs/node-service.log" if os.path.exists("/app") else None,
)

# Try to import the shared service discovery module
try:
    from shared.service_discovery import ServiceDiscoveryClient

    service_discovery_available = True
    service_discovery_client = None
    logger.info("Service discovery module available")
except ImportError:
    service_discovery_available = False
    service_discovery_client = None
    logger.warning("Service discovery module not available, using fallback mode")

# Create database tables
Base.metadata.create_all(bind=engine)


def clear_log_file():
    """Clears the application log file."""
    log_path = os.path.join(os.path.dirname(__file__), "logs", "log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8"):
        pass


def get_or_create_installation_guid(db: Session):
    """Gets or creates the installation GUID."""
    info = db.query(InstallationInfo).first()
    if not info:
        guid = str(uuid.uuid4())
        info = InstallationInfo(guid=guid)
        db.add(info)
        db.commit()
        db.refresh(info)
    return info.guid


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing headers."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager for startup and shutdown tasks."""
    global service_discovery_client
    logger.info("Starting PPL Meta Node service...")

    # Initialize service discovery if available
    if service_discovery_available and CONSUL_CONFIG["enabled"]:
        try:
            service_discovery_client = ServiceDiscoveryClient(
                consul_host=CONSUL_CONFIG["host"], consul_port=CONSUL_CONFIG["port"]
            )
            await service_discovery_client.register_service(
                service_name="ppl-meta-node",
                service_host=settings.HOST,
                service_port=settings.PORT,
                health_check_path="/api/v1/health",
                tags=["user-management", "authentication", "microservice"],
            )
            logger.info("Service registered with Consul")

            # Start health monitoring
            await service_discovery_client.start_health_monitoring(
                "ppl-meta-node", settings.HOST, settings.PORT
            )
            logger.info("Health monitoring started")
        except Exception as e:
            logger.error(f"Failed to initialize service discovery: {e}")
            logger.info("Continuing without service discovery")
            service_discovery_client = None

    try:
        clear_log_file()
        logger.info("Log file cleared")

        def init_guid_and_admin():
            logger.info("Initializing database connection...")
            try:
                # Test database connection
                db = SessionLocal()

                # Test connection with a simple query
                db.execute(text("SELECT 1"))
                logger.info("Database connection successful")

                # Create tables
                Base.metadata.create_all(bind=engine)
                logger.info("Database tables created/verified")

                # Ensure installation GUID
                guid = get_or_create_installation_guid(db)
                logger.info(f"Installation GUID: {guid}")

                # Ensure first admin user exists
                admin_email = "nick.glezakos@gmail.com"
                admin_username = "nick.glezakos@gmail.com"
                admin_user = get_user_by_email(db, admin_email)
                if not admin_user:
                    admin = UserCreate(
                        username=admin_username,
                        email=admin_email,
                        password="Kodikos@23",
                    )
                    create_user(db, admin)
                    logger.info("Admin user created with default credentials.")
                else:
                    logger.info("Admin user already exists")

                # Ensure admin role exists and is assigned to the admin user
                ensure_admin_role(db, admin_username)
                logger.info("Admin role ensured")

                db.close()
                logger.info("Database initialization completed successfully")

            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                if "db" in locals():
                    db.close()
                raise

        await run_in_threadpool(init_guid_and_admin)
        logger.info("Service startup completed successfully")

    except Exception as e:
        logger.error(f"Service startup failed: {e}")
        raise

    yield

    logger.info("Service shutting down...")

    # Deregister from service discovery
    if service_discovery_client:
        try:
            await service_discovery_client.deregister_service("ppl-meta-node")
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")


# FastAPI application with metadata
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="User Management Microservice for PPL Meta Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add global exception handlers for validation errors
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors."""
    return handle_validation_error(exc)


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle value errors from custom validation."""
    return handle_validation_error(exc)


# Initialize metrics
metrics_collector = init_metrics(
    service_name=settings.APP_NAME, service_version=settings.APP_VERSION
)

# Middleware
app.add_middleware(TimingMiddleware)

# Add metrics middleware
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Include API routers
app.include_router(v1_router)  # API v1 routes

# Add metrics endpoint
metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])

# Legacy routes for backward compatibility
app.include_router(roles.router)
app.include_router(otp.router)
app.include_router(logs.router)
app.include_router(backup.router)
app.include_router(app_settings.router)
app.include_router(capabilities.router)

# Initialize metrics
init_metrics()

# Add Prometheus middleware for metrics endpoint
app.add_middleware(PrometheusMiddleware)
create_metrics_endpoint(app)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )

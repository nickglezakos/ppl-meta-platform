"""
FastAPI microservice main application.
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

from src.api.health import router as legacy_health_router
from src.api.v1.routes import v1_router
from src.config import get_config
from src.database import Base, engine, test_connection
from src.microservice_config import CONSUL_CONFIG

from shared.logging import setup_logging
from shared.metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics

# Try to import the shared service discovery module
try:
    from shared.service_discovery import ServiceDiscoveryClient

    service_discovery_available = True
except ImportError:
    service_discovery_available = False

# Initialize configuration
config = get_config()

# Setup standardized logging
logger = setup_logging(
    service_name="ppl-meta-media",
    log_level=config.LOG_LEVEL.upper(),
    log_format=config.LOG_FORMAT.lower(),
    log_file="/app/logs/media-service.log" if os.path.exists("/app") else None,
)

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
    logger.info("Starting PPL Meta Media Service...")

    # Initialize service discovery if available
    if service_discovery_available and CONSUL_CONFIG["enabled"]:
        try:
            service_discovery_client = ServiceDiscoveryClient(
                consul_host=CONSUL_CONFIG["host"], consul_port=CONSUL_CONFIG["port"]
            )
            await service_discovery_client.register_service(
                service_name="ppl-meta-media",
                service_host="0.0.0.0",
                service_port=8000,
                health_check_path="/api/v1/health",
                tags=["media", "processing", "microservice"],
            )
            logger.info("Service registered with Consul")

            # Start health monitoring
            await service_discovery_client.start_health_monitoring(
                "ppl-meta-media", "0.0.0.0", 8000
            )
            logger.info("Health monitoring started")
        except Exception as e:
            logger.error(f"Failed to initialize service discovery: {e}")
            logger.info("Continuing without service discovery")
            service_discovery_client = None

    # Get and log configuration
    config.log_configuration()

    # Test database connection with retries
    max_retries = 5
    for attempt in range(max_retries):
        try:
            logger.info(
                "Testing database connection (attempt %d/%d)...",
                attempt + 1,
                max_retries,
            )
            if test_connection():
                logger.info("Database connection successful")
                break
            else:
                logger.error("Database connection test failed")
        except Exception as e:
            logger.error("Database connection error: %s", e)
            if attempt == max_retries - 1:
                logger.error(
                    "Failed to connect to database after %d attempts", max_retries
                )
                logger.info("Service will start but database operations will fail")
                logger.info("Ensure database is running and accessible")
                break
            else:
                logger.info("Retrying database connection in 2 seconds...")
                time.sleep(2)

    # Create database tables (only if connection is available)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)
        logger.info("Service will start but database operations will fail")

    logger.info("Service startup completed successfully")

    yield

    logger.info("Shutting down PPL Meta Media Service...")

    # Deregister from service discovery
    if service_discovery_client:
        try:
            await service_discovery_client.deregister_service("ppl-meta-media")
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")


# Initialize FastAPI app
app = FastAPI(
    title="PPL Meta Media Service",
    description="Headless FastAPI microservice for media processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Initialize metrics
metrics_collector = init_metrics(service_name="ppl-meta-media", service_version="1.0.0")

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]  # Configure for production
)

# Add metrics middleware
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

# CORS middleware for microservices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global exception handler caught: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Add validation error handlers
try:
    from shared.validation import ValidationError

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        logger.warning("Validation error: %s", exc)
        return JSONResponse(
            status_code=400,
            content=exc.dict() if hasattr(exc, "dict") else {"detail": str(exc)},
        )

except ImportError:
    logger.info("Shared validation module not available, using basic error handling")


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation-related ValueError exceptions."""
    error_msg = str(exc)
    if any(
        keyword in error_msg.lower() for keyword in ["injection", "xss", "validation"]
    ):
        logger.warning("Security validation error: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"detail": error_msg, "error_type": "validation_error"},
        )
    else:
        logger.error("Value error: %s", exc)
        return JSONResponse(status_code=400, content={"detail": error_msg})


# Include routers
app.include_router(v1_router)  # Versioned API
app.include_router(legacy_health_router)  # Legacy health endpoints

# Add metrics endpoint
metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information and API versions."""
    return {
        "service": "ppl-meta-media",
        "status": "operational",
        "version": "1.0.0",
        "api_versions": {"v1": "/api/v1", "legacy": "/health"},
        "documentation": {"swagger": "/docs", "redoc": "/redoc"},
    }


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.ENVIRONMENT == "development",
        log_level="info",
    )

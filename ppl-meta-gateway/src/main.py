"""
PPL Meta Gateway Main Application
"""

import os
import sys

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from contextlib import asynccontextmanager

import structlog
import uvicorn
from api.v1.router import api_router
from config import CORS_SETTINGS, settings
from core.health import health_router
from core.middleware import LoggingMiddleware, RateLimitMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import shared metrics
from metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics
from utils.logger import setup_logging

# Import shared service discovery
try:
    from service_discovery import (
        cleanup_service_discovery,
        deregister_service,
        register_service,
        start_health_monitoring,
    )

    SERVICE_DISCOVERY_AVAILABLE = True
except ImportError:
    logger.info("Shared service discovery module not available, using legacy")
    SERVICE_DISCOVERY_AVAILABLE = False

    async def register_service(*args, **kwargs):
        return True

    async def deregister_service(*args, **kwargs):
        return True

    async def start_health_monitoring():
        pass

    async def cleanup_service_discovery():
        pass


# Setup structured logging
setup_logging()
logger = structlog.get_logger()

# Add validation error handlers
try:
    from shared.validation import SecurityValidator

    def validate_gateway_request(request_data: dict, endpoint: str) -> dict:
        """Validate gateway request data for security."""
        validated_data = {}

        for key, value in request_data.items():
            if isinstance(value, str):
                try:
                    SecurityValidator.validate_sql_injection(value, key)
                    SecurityValidator.validate_xss(value, key)
                    validated_data[key] = SecurityValidator.escape_html(value)
                except ValueError as e:
                    logger.warning(
                        "Security validation failed",
                        field=key,
                        endpoint=endpoint,
                        error=str(e),
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Security validation failed for {key}: {str(e)}",
                    )
            else:
                validated_data[key] = value

        return validated_data

except ImportError:
    logger.info("Shared validation module not available")

    def validate_gateway_request(request_data: dict, endpoint: str) -> dict:
        """Fallback validation when shared module unavailable."""
        return request_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Initialize metrics first
    init_metrics(
        service_name=settings.service_name, service_version=settings.service_version
    )

    logger.info("Starting PPL Meta Gateway", version=settings.service_version)

    # Register this service with discovery system
    if SERVICE_DISCOVERY_AVAILABLE:
        success = await register_service(
            service_name="ppl-meta-gateway",
            host=settings.host,
            port=settings.port,
            health_endpoint="/health",
            tags=["api-gateway", "routing", "load-balancer"],
            metadata={
                "version": settings.service_version,
                "environment": settings.environment,
                "features": "routing,load_balancing,rate_limiting",
            },
        )

        if success:
            logger.info("Gateway service registered with discovery system")
        else:
            logger.warning("Failed to register gateway service")

        # Start health monitoring
        await start_health_monitoring()
        logger.info("Health monitoring started")

    yield

    # Cleanup
    logger.info("Shutting down PPL Meta Gateway")

    if SERVICE_DISCOVERY_AVAILABLE:
        await deregister_service(
            service_name="ppl-meta-gateway", host=settings.host, port=settings.port
        )
        await cleanup_service_discovery()
        logger.info("Service deregistered and discovery cleaned up")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="PPL Meta Gateway",
        description="Central API Gateway for PPL Meta Microservices Ecosystem",
        version=settings.service_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(CORSMiddleware, **CORS_SETTINGS)

    # Initialize metrics and add metrics middleware
    metrics_collector = init_metrics(
        service_name=settings.service_name, service_version=settings.service_version
    )
    app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

    # Add other middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(api_router, prefix=settings.api_v1_prefix, tags=["API Gateway"])

    # Add metrics endpoint
    metrics_router = create_metrics_endpoint()
    app.include_router(metrics_router, tags=["Metrics"])

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": (
                    str(exc) if settings.debug else "An unexpected error occurred"
                ),
                "path": str(request.url.path),
            },
        )

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": settings.service_name,
            "version": settings.service_version,
            "status": "running",
            "environment": settings.environment,
            "docs": "/docs" if settings.debug else "disabled",
        }

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.LOG_LEVEL.lower(),
    )

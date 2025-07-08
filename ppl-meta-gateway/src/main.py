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
from core.service_discovery import ServiceRegistry
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import shared metrics
from metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics
from utils.logger import setup_logging

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

    # Initialize service registry
    if settings.service_discovery_enabled:
        service_registry = ServiceRegistry()
        await service_registry.initialize()
        app.state.service_registry = service_registry
        logger.info("Service discovery initialized")

    # Register this service
    try:
        await app.state.service_registry.register_service(
            name=settings.service_name,
            address=settings.host,
            port=settings.port,
            health_check=f"http://{settings.host}:{settings.port}/health",
        )
        logger.info("Gateway service registered")
    except Exception as e:
        logger.error("Failed to register gateway service", error=str(e))

    yield

    # Cleanup
    logger.info("Shutting down PPL Meta Gateway")
    if hasattr(app.state, "service_registry"):
        await app.state.service_registry.deregister_service(settings.service_name)
        await app.state.service_registry.close()


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

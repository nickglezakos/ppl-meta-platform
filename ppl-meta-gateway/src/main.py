"""
PPL Meta Gateway Main Application
"""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from src.config import settings, CORS_SETTINGS
from src.api.v1.router import api_router
from src.core.middleware import (
    LoggingMiddleware,
    PrometheusMiddleware,
    RateLimitMiddleware
)
from src.core.service_discovery import ServiceRegistry
from src.core.health import health_router
from src.utils.logger import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
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
            health_check=f"http://{settings.host}:{settings.port}/health"
        )
        logger.info("Gateway service registered")
    except Exception as e:
        logger.error("Failed to register gateway service", error=str(e))
    
    yield
    
    # Cleanup
    logger.info("Shutting down PPL Meta Gateway")
    if hasattr(app.state, 'service_registry'):
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
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        **CORS_SETTINGS
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    
    if settings.metrics_enabled:
        app.add_middleware(PrometheusMiddleware)
        # Mount Prometheus metrics endpoint
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    
    app.add_middleware(RateLimitMiddleware)
    
    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
        tags=["API Gateway"]
    )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else "An unexpected error occurred",
                "path": str(request.url.path)
            }
        )
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": settings.service_name,
            "version": settings.service_version,
            "status": "running",
            "environment": settings.environment,
            "docs": f"/docs" if settings.debug else "disabled"
        }
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

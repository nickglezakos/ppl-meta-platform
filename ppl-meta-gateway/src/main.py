"""
PPL Meta Gateway Main Application
"""

from contextlib import asynccontextmanager

import uvicorn
from api.v1.router import api_router
from api.v1.camera_counters import router as camera_counters_router
from api.v1.websockets import router as websockets_router
from core.advanced_middleware import (
    AdvancedRateLimitMiddleware,
    CircuitBreakerMiddleware,
    RequestTracingMiddleware,
    RequestTransformationMiddleware,
    add_api_version_header,
    normalize_user_data,
)
from core.health import health_router
from core.middleware import LoggingMiddleware, RateLimitMiddleware

# Import distributed tracing
from core.tracing import setup_tracing, shutdown_tracing
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import CORS_SETTINGS, settings

# Import shared modules (local stubs)
from shared.logging import get_logger, setup_logging
from shared.metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics
from shared.service_discovery import (
    cleanup_service_discovery,
    deregister_service,
    register_service,
    start_health_monitoring,
)

# Import Redis cache client and worker
from core.redis_client import cache_client
from workers.mvr_counter_worker import mvr_counter_worker

# Setup logging
setup_logging(
    service_name="ppl-meta-gateway",
    log_level=settings.LOG_LEVEL.upper(),
    log_format=settings.LOG_FORMAT.lower(),
)
logger = get_logger(__name__)

# Initialize metrics
init_metrics("ppl-meta-gateway", "1.0.0")

# Set availability flags
SERVICE_DISCOVERY_AVAILABLE = True  # Since we have local stubs

logger.info("Starting PPL Meta Gateway with distributed tracing enabled")


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
    """Startup and shutdown lifespan for the FastAPI application."""

    # Detect actual network IP for registration
    import socket

    detected_ip = None
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        detected_ip = s.getsockname()[0]
        s.close()
    except Exception:
        # Fallback to hostname resolution
        detected_ip = socket.gethostbyname(socket.gethostname())

    # Startup
    logger.info("Starting PPL Meta Gateway", version=settings.service_version)

    # Connect to Redis cache
    try:
        await cache_client.connect()
        logger.info("✅ Redis cache connected for camera counters")
        
        # Start MVR counter background worker
        import asyncio
        asyncio.create_task(mvr_counter_worker.start())
        logger.info("✅ MVR counter worker started")
    except Exception as e:
        logger.warning(f"⚠️  Redis cache connection failed: {e}")
        logger.info("Continuing without cache (will use live queries)")

    # Initialize tracing
    if hasattr(settings, "jaeger_enabled") and settings.jaeger_enabled:
        try:
            init_tracing()
            logger.info("Distributed tracing initialized")
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            logger.info("Continuing without tracing")
    else:
        logger.info("Distributed tracing disabled or failed to initialize")

    logger.info("Starting PPL Meta Gateway", version=settings.service_version)

    # Register this service with discovery system
    if SERVICE_DISCOVERY_AVAILABLE:
        success = await register_service(
            service_name="ppl-meta-gateway",
            host=detected_ip,
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

    yield

    # Cleanup
    logger.info("Shutting down PPL Meta Gateway")

    # Stop MVR counter worker
    try:
        await mvr_counter_worker.stop()
        logger.info("MVR counter worker stopped")
    except Exception as e:
        logger.error(f"Error stopping MVR counter worker: {e}")
    
    # Disconnect Redis cache
    try:
        await cache_client.disconnect()
        logger.info("Redis cache disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting Redis cache: {e}")

    # Shutdown tracing
    shutdown_tracing()

    if SERVICE_DISCOVERY_AVAILABLE and detected_ip:
        await deregister_service(
            service_name="ppl-meta-gateway", host=detected_ip, port=settings.port
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

    # Initialize metrics
    _ = init_metrics(settings.service_name, settings.service_version)

    # Add metrics middleware
    app.add_middleware(PrometheusMiddleware, app_name=settings.service_name)

    # Add advanced middleware (order matters - inner middleware runs first)
    app.add_middleware(RequestTracingMiddleware)  # Tracing for all requests
    # Re-enable RequestTransformationMiddleware to test
    app.add_middleware(
        RequestTransformationMiddleware,
        request_transformations={
            "/api/v1/users/register": normalize_user_data,
            "/api/v1/users/me": normalize_user_data,
            # Exclude login endpoint from transformation to avoid timeout
        },
        response_transformations={
            "/api/v1": add_api_version_header,
        },
    )
    app.add_middleware(CircuitBreakerMiddleware)  # Circuit breaker for service calls
    app.add_middleware(
        AdvancedRateLimitMiddleware,
        redis_url=(
            settings.redis_url
            if hasattr(settings, "redis_url")
            else "redis://redis:6379"
        ),
        default_rate="100/minute",
        strategies={
            "/api/v1/auth": "10/minute",
            "/api/v1/register": "5/minute",
            "/api/v1/password": "3/minute",
            "/api/v1/users": "50/minute",
            "/api/v1/streaming": "1000/minute",  # High limit for cameras
        },
    )

    # Add basic middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)  # Fallback rate limiting

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(api_router, prefix=settings.api_v1_prefix, tags=["API Gateway"])
    app.include_router(camera_counters_router, prefix=settings.api_v1_prefix, tags=["Camera Counters"])
    app.include_router(websockets_router, prefix=settings.api_v1_prefix, tags=["WebSockets"])

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

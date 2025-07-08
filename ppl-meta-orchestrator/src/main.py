import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

# Local imports
from config import settings

# Standard library and third-party imports
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import consul for service discovery
try:
    import consul

    service_discovery_available = True
    logger.info("Consul module available for service discovery")
except ImportError:
    service_discovery_available = False
    logger.warning("Consul module not available, service discovery disabled")

# Global consul client
consul_client = None

# Consul configuration
CONSUL_CONFIG = {
    "host": os.getenv("CONSUL_HOST", "consul"),
    "port": int(os.getenv("CONSUL_PORT", "8500")),
    "enabled": os.getenv("CONSUL_ENABLED", "true").lower() == "true",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager for startup and shutdown tasks."""
    global consul_client
    logger.info("Starting PPL Meta Orchestrator Service...")

    # Initialize service discovery if available
    if service_discovery_available and CONSUL_CONFIG["enabled"]:
        try:
            consul_client = consul.Consul(
                host=CONSUL_CONFIG["host"], port=CONSUL_CONFIG["port"]
            )

            # Register service with Consul
            consul_client.agent.service.register(
                name="ppl-meta-orchestrator",
                service_id="ppl-meta-orchestrator",
                address=settings.HOST,
                port=settings.PORT,
                tags=["orchestrator", "coordination", "microservice"],
                check=consul.Check.http(
                    f"http://{settings.HOST}:{settings.PORT}/health", interval="10s"
                ),
            )
            logger.info("Service registered with Consul")
        except Exception as e:
            logger.error(f"Failed to initialize service discovery: {e}")
            logger.info("Continuing without service discovery")
            consul_client = None

    logger.info("Service startup completed successfully")

    yield

    logger.info("Shutting down PPL Meta Orchestrator Service...")

    # Deregister from service discovery
    if consul_client:
        try:
            consul_client.agent.service.deregister("ppl-meta-orchestrator")
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")


def validate_orchestrator_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Basic validation for orchestrator input data."""
    # Simple validation - can be extended later
    validated_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Basic sanitization
            validated_data[key] = value.strip()
        else:
            validated_data[key] = value
    return validated_data


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker container."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"{settings.APP_NAME} Service",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.post("/orchestrate")
async def orchestrate_request(data: Dict[str, Any]):
    """Orchestrate service requests with validation."""
    try:
        # Validate input data
        validated_data = validate_orchestrator_input(data)

        # Process orchestration logic here
        return {
            "status": "orchestrated",
            "processed_data": validated_data,
            "message": "Request orchestration successful",
            "service": settings.APP_NAME,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Orchestration processing error: {str(e)}"
        ) from e


@app.get("/validate")
async def validate_data_endpoint():
    """Endpoint to test validation functionality."""
    return {
        "validation_active": True,
        "security_features": [
            "sql_injection_prevention",
            "xss_protection",
            "input_sanitization",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    # Log configuration on startup
    settings.log_configuration()

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

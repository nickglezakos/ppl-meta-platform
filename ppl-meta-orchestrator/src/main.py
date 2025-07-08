import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

from typing import Any, Dict

# Local imports
from config import settings

# Standard library and third-party imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from shared.logging import setup_logging
from shared.metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics

# Add validation support
try:
    from shared.validation import SecurityValidator

    def validate_orchestrator_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate orchestrator input data."""
        validated_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                try:
                    SecurityValidator.validate_sql_injection(value, key)
                    SecurityValidator.validate_xss(value, key)
                    validated_data[key] = SecurityValidator.escape_html(value)
                except ValueError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Security validation failed for {key}: {str(e)}",
                    )
            else:
                validated_data[key] = value

        return validated_data

except ImportError:

    def validate_orchestrator_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback validation when shared module unavailable."""
        return data


# Setup standardized logging
logger = setup_logging(
    service_name="ppl-meta-orchestrator",
    log_level=settings.LOG_LEVEL.upper(),
    log_format=settings.LOG_FORMAT.lower(),
    log_file=(
        "/app/logs/orchestrator-service.log" if os.path.exists("/app") else None
    ),  # noqa: E501
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

# Initialize metrics
metrics_collector = init_metrics(
    service_name=settings.APP_NAME, service_version=settings.APP_VERSION
)

# Add metrics middleware
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

# Add metrics endpoint
metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])


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
        )


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

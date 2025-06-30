"""
FastAPI microservice main application.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time

from src.config import get_config
from src.database import engine, Base
from src.api.health import router as legacy_health_router
from src.api.v1.routes import v1_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PPL Meta Media Service",
    description="Headless FastAPI microservice for media processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure for production
)

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
    logger.error(f"Global exception handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include routers
app.include_router(v1_router)  # Versioned API
app.include_router(legacy_health_router)  # Legacy health endpoints (backward compatibility)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    logger.info("Starting PPL Meta Media Service...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Log configuration
    config = get_config()
    logger.info(f"Service starting with environment: {config.ENVIRONMENT}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down PPL Meta Media Service...")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information and API versions."""
    return {
        "service": "ppl-meta-media",
        "status": "operational",
        "version": "1.0.0",
        "api_versions": {
            "v1": "/api/v1",
            "legacy": "/health"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.ENVIRONMENT == "development",
        log_level="info"
    )
"""
PPL Meta BootCore Service - Licensing and Platform Identity Management

This service provides:
- Platform instance identity management
- License key activation and validation
- User management with owner privileges
- Hardware binding for anti-piracy protection
- Integration with PPL Meta Discovery Service

GitHub Issue: #44
Port: 8007
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

import uvicorn
from api.license_routes import license_router
from api.platform_routes import platform_router
from api.user_routes import user_router
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models.platform_models import (
    LicenseActivationRequest,
    LicenseActivationResponse,
    LicenseInfo,
    PlatformIdentityResponse,
    PlatformInstance,
    UserAccount,
    UserManagementRequest,
)
from services.license_service import LicenseService
from services.platform_service import PlatformService
from services.user_service import UserService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
license_service: LicenseService = None
platform_service: PlatformService = None
user_service: UserService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global license_service, platform_service, user_service

    logger.info("🚀 Starting PPL Meta BootCore Service...")

    # Initialize services
    try:
        platform_service = PlatformService()
        license_service = LicenseService(platform_service)
        user_service = UserService(platform_service)

        # Start background tasks
        asyncio.create_task(license_service.start_background_tasks())
        asyncio.create_task(platform_service.start_background_tasks())
        asyncio.create_task(user_service.start_background_tasks())

        # Ensure platform instance is initialized
        await platform_service.ensure_platform_instance()

        logger.info("✅ PPL Meta BootCore Service started successfully")
        logger.info(f"🔧 Platform Instance ID: {platform_service.get_instance_id()}")
        logger.info(f"🔒 License Status: {license_service.get_license_status()}")
        user_count = await user_service.get_user_count()
        logger.info(f"👤 User Count: {user_count}")

    except Exception as e:
        logger.error(f"❌ Failed to start BootCore Service: {e}")
        raise

    yield

    # Cleanup
    logger.info("🛑 Shutting down PPL Meta BootCore Service...")
    if license_service:
        await license_service.cleanup()
    if platform_service:
        await platform_service.cleanup()
    if user_service:
        await user_service.cleanup()
    logger.info("✅ PPL Meta BootCore Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta BootCore Service",
    description="Platform Identity, Licensing, and User Management Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Service dependencies
def get_license_service() -> LicenseService:
    if not license_service:
        raise HTTPException(status_code=503, detail="License service not available")
    return license_service


def get_platform_service() -> PlatformService:
    if not platform_service:
        raise HTTPException(status_code=503, detail="Platform service not available")
    return platform_service


def get_user_service() -> UserService:
    if not user_service:
        raise HTTPException(status_code=503, detail="User service not available")
    return user_service


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        platform_status = (
            await platform_service.health_check() if platform_service else "unavailable"
        )
        license_status = (
            await license_service.health_check() if license_service else "unavailable"
        )
        user_status = (
            await user_service.health_check() if user_service else "unavailable"
        )

        return {
            "service": "ppl-meta-bootcore",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "port": 8007,
            "components": {
                "platform_service": platform_status,
                "license_service": license_status,
                "user_service": user_status,
            },
            "platform_instance": (
                platform_service.get_instance_id() if platform_service else None
            ),
            "license_active": (
                license_service.is_license_active() if license_service else False
            ),
            "user_count": await user_service.get_user_count() if user_service else 0,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "ppl-meta-bootcore",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "PPL Meta BootCore",
        "description": "Platform Identity, Licensing, and User Management Service",
        "version": "1.0.0",
        "github_issue": "#44",
        "endpoints": {
            "health": "/health",
            "license": "/api/v1/license/*",
            "platform": "/api/v1/platform/*",
            "users": "/api/v1/users/*",
        },
        "documentation": "/docs",
    }


# Include API routers
app.include_router(license_router, prefix="/api/v1/license", tags=["License"])
app.include_router(platform_router, prefix="/api/v1/platform", tags=["Platform"])
app.include_router(user_router, prefix="/api/v1/users", tags=["Users"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8007, reload=True, log_level="info")

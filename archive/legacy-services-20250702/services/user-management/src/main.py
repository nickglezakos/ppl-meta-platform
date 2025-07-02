"""Main entry point for the PPL Meta Node - User Management Service."""

import os
import uuid
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

from src.config import settings
from src.services.user_service import create_user, get_user_by_email
from src.models.user import Base
from src.database import engine, SessionLocal

# Import API routers
from src.api.v1.routes import router as v1_router
from src.api import roles, otp, logs, backup, app_settings, capabilities

# Import models to ensure they're created
from src.models.installation_info import InstallationInfo
from src.models.app_setting import AppSetting
from src.models.log import Log
from src.models.otp import OTP
from src.models.role import Role, UserRole, Capability, RoleCapability
from src.models.user import User, UserAction
from src.services.role_service import ensure_admin_role
from src.schemas.user import UserCreate

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
    clear_log_file()
    
    def init_guid_and_admin():
        db = SessionLocal()
        # Ensure installation GUID
        guid = get_or_create_installation_guid(db)
        print(f"Installation GUID: {guid}")

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
            print("Admin user created with default credentials.")
        # Ensure admin role exists and is assigned to the admin user
        ensure_admin_role(db, admin_username)
        db.close()
    
    await run_in_threadpool(init_guid_and_admin)
    yield

# FastAPI application with metadata
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="User Management Microservice for PPL Meta Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware
app.add_middleware(TimingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Include API routers
app.include_router(v1_router)  # API v1 routes

# Legacy routes for backward compatibility
app.include_router(roles.router)
app.include_router(otp.router)
app.include_router(logs.router)
app.include_router(backup.router)
app.include_router(app_settings.router)
app.include_router(capabilities.router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

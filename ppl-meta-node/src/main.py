"""Main entry point for the PPL Meta Node - User Management Service."""

import asyncio
import os
import socket
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Add the parent directory to Python path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Temporarily disable shared modules for quick testing
# from shared.logging import setup_logging
# from shared.metrics import PrometheusMiddleware, create_metrics_endpoint, init_metrics
# from shared.validation import handle_validation_error
import logging

# Basic logging setup with file handler
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ppl-meta-node.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ppl-meta-node")

FRESH_ADMIN_EMAIL = "fresh.user@example.com"

try:
    from src.config import settings
    from src.database import SessionLocal, engine
    from src.models.user import Base
    from src.services.user_service import create_user, get_user_by_email
    from src.services.authority_service import authority_service

    # Import licensing service for initialization
    try:
        from src.services.licensing_service import init_licensing_service

        LICENSING_AVAILABLE = True
        logger.info("Licensing service available")
    except ImportError:
        LICENSING_AVAILABLE = False
        init_licensing_service = None
        logger.warning("Licensing service not available")

    logger.info("Successfully imported core modules")
except (ImportError, RuntimeError) as e:
    logger.error("Failed to import core modules: %s", e)
    sys.exit(1)

from src.api import app_settings, backup, capabilities, logs, otp, roles
from src.api.routes import legacy_health_router

# Import API routers
from src.api.v1.routes import router as v1_router

# Import models to ensure they're created
from src.models.installation_info import InstallationInfo
from src.schemas.user import UserCreate
from src.services.multicast_discovery import MulticastServiceDiscoveryBroadcaster
from src.services.vpn_service import enroll_once, report_platform_local_ip
from src.services.role_service import ensure_default_capabilities, ensure_exact_system_roles

# Try to import the shared service discovery module
try:
    service_discovery_available = True
    logger.info("Service discovery module available")
except ImportError:
    service_discovery_available = False
    logger.warning("Service discovery module not available, using fallback mode")

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


def ensure_installation_info_schema(db: Session):
    """Upgrade installation_info in place for authority cache fields."""
    inspector = inspect(db.bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("installation_info")
    }
    required_columns = {
        "authority_application_key": "TEXT",
        "authority_installation_uuid": "TEXT",
        "authority_licence_name": "TEXT",
        "authority_tenant_name": "TEXT",
        "authority_approved_owner_email": "TEXT",
        "authority_licence_status": "TEXT",
        "authority_owner_enabled": "BOOLEAN",
        "authority_warning_period_days": "INTEGER",
        "authority_warning_started_at": "TIMESTAMP",
        "authority_offline_grace_days": "INTEGER",
        "authority_last_checked_at": "TIMESTAMP",
        "authority_last_successful_check_at": "TIMESTAMP",
        "authority_last_result_reason": "TEXT",
    }
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            db.execute(text(f"ALTER TABLE installation_info ADD COLUMN {column_name} {column_type}"))
    db.commit()


def get_local_network_ips():
    """Get all local network IP addresses including VPN ranges"""
    ips = []
    try:
        # Use ifconfig to get all IPs - more reliable than netifaces
        import re

        result = subprocess.run(
            ["ifconfig"], capture_output=True, check=False, text=True, timeout=10
        )
        if result.returncode == 0:
            # Look for inet addresses
            inet_pattern = r"inet (\d+\.\d+\.\d+\.\d+)"
            matches = re.findall(inet_pattern, result.stdout)

            for ip in matches:
                # Skip localhost and link-local addresses
                if not ip.startswith(("127.", "169.254.")):
                    ips.append(ip)

                    # Log VPN detection
                    if ip.startswith("100."):
                        print(f"Detected Tailscale VPN IP: {ip}")
                    elif ip.startswith(("10.", "172.")):
                        if ip.startswith("172."):
                            # Check if it's in private range 172.16-31.x
                            parts = ip.split(".")
                            if len(parts) >= 2:
                                second_octet = int(parts[1])
                                if 16 <= second_octet <= 31:
                                    print(f"Detected VPN/Private IP: {ip}")
                        else:
                            print(f"Detected VPN/Private IP: {ip}")
                    elif ip.startswith("192.168."):
                        print(f"Detected local network IP: {ip}")

    except (OSError, subprocess.SubprocessError) as e:
        print(f"ifconfig method failed: {e}")
        # Fallback to socket method
        hostname = socket.gethostname()
        try:
            ips = [socket.gethostbyname(hostname)]
        except socket.error:
            ips = []

    return ips


def get_dynamic_allowed_hosts():
    """Get dynamically detected allowed hosts for TrustedHostMiddleware."""
    base_hosts = ["localhost", "127.0.0.1", "*.localhost", "0.0.0.0"]
    network_ips = get_local_network_ips()

    all_hosts = base_hosts + network_ips
    logger.info("Dynamic allowed hosts: %s", all_hosts)
    return all_hosts


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing headers."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


class AuthoritySafeguardMiddleware(BaseHTTPMiddleware):
    """Block protected routes when the resolved authority runtime state is safeguard."""

    _exempt_exact_paths = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/licensing/bootstrap/status",
        "/api/v1/licensing/bootstrap/activate",
        "/api/v1/licensing/authority/status",
        "/api/v1/licensing/authority/refresh",
        "/api/v1/users/login",
        "/api/v1/users/logout",
        "/api/v1/users/profile",
        "/api/v1/users/forgot-password",
        "/api/v1/users/reset-password",
        "/api/v1/users/verify-email",
    }

    def _is_exempt(self, path: str) -> bool:
        return (
            path in self._exempt_exact_paths
            or path.startswith("/docs/")
            or path.startswith("/redoc/")
            or path.startswith("/openapi")
        )

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or self._is_exempt(request.url.path):
            return await call_next(request)

        db = SessionLocal()
        try:
            runtime_state = authority_service.derive_runtime_state(db)
        finally:
            db.close()

        if runtime_state["state"] == "safeguard":
            return JSONResponse(
                status_code=423,
                content={
                    "detail": "Installation is in safeguard mode",
                    "runtime_state": runtime_state["state"],
                    "reason": runtime_state["reason"],
                    "warning_deadline": runtime_state["warning_deadline"],
                },
            )

        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager for startup and shutdown tasks."""
    multicast_broadcaster = None
    authority_revalidation_task = None
    vpn_local_ip_report_task = None

    logger.info("Starting PPL Meta Node service...")

    # Initialize service discovery if available
    if service_discovery_available:
        try:
            # Detect actual network IP for registration
            from shared.service_discovery import register_service

            try:
                # Connect to a remote address to determine local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                detected_ip = s.getsockname()[0]
                s.close()
            except OSError:
                # Fallback to hostname resolution
                detected_ip = socket.gethostbyname(socket.gethostname())

            # Detect our Headscale/Tailscale mesh IP so devices dialing in over
            # the VPN can resolve this node's API to a reachable address.
            tailscale_ip = None
            try:
                from shared.networking.tailscale_utils import get_tailscale_ip

                tailscale_ip = get_tailscale_ip()
            except Exception as e:
                logger.warning(f"Could not detect local tailscale IP: {e}")

            node_metadata = {
                "version": "1.0.0",
                "environment": "development",
                "features": "user_management,authentication,admin_api",
            }
            if tailscale_ip:
                node_metadata["tailscale_ip"] = tailscale_ip
                node_metadata["tailscale_port"] = settings.PORT

            await register_service(
                name="ppl-meta-node",
                service_type="backend",
                version="1.0.0",
                host=detected_ip,
                port=settings.PORT,
                health_endpoint="/health/",
                capabilities=["user-management", "authentication", "api"],
                metadata=node_metadata,
            )
            logger.info("Successfully registered ppl-meta-node with discovery service")
        except (ImportError, OSError, RuntimeError) as e:
            logger.error("Failed to register with discovery service: %s", e)
            logger.info("Continuing without service discovery")

    try:
        clear_log_file()
        logger.info("Log file cleared")

        def init_guid_and_admin():
            logger.info("Initializing database connection...")
            try:
                # Test database connection
                db = SessionLocal()

                # Test connection with a simple query
                db.execute(text("SELECT 1"))
                logger.info("Database connection successful")

                # Create tables
                Base.metadata.create_all(bind=engine)
                logger.info("Database tables created/verified")

                ensure_installation_info_schema(db)
                logger.info("Installation info schema verified")

                # Ensure installation GUID
                guid = get_or_create_installation_guid(db)
                logger.info("Installation GUID: %s", guid)

                # Security hardening (Proposal §10.2 C1): dev bootstrap users only
                # created in development mode with env-configurable password.
                DEV_BOOTSTRAP_PASSWORD = os.environ.get(
                    "DEV_BOOTSTRAP_PASSWORD",
                    "" if os.environ.get("ENVIRONMENT") != "development" else "change-me-dev-only",
                )
                is_dev = os.environ.get("ENVIRONMENT") == "development"

                if is_dev and DEV_BOOTSTRAP_PASSWORD:
                    simple_user_email = "nick.glezakos@gmail.com"
                    simple_user = get_user_by_email(db, simple_user_email)
                    if not simple_user:
                        create_user(db, UserCreate(
                            username=simple_user_email, email=simple_user_email,
                            password=DEV_BOOTSTRAP_PASSWORD,
                        ))
                        logger.info("Dev bootstrap user created (simple).")

                    fresh_email = FRESH_ADMIN_EMAIL
                    if not get_user_by_email(db, fresh_email):
                        create_user(db, UserCreate(
                            username=fresh_email, email=fresh_email,
                            password=DEV_BOOTSTRAP_PASSWORD,
                        ))
                        logger.info("Dev bootstrap user created (fresh).")

                    outlook_email = "nick.glezakos@outlook.com"
                    if not get_user_by_email(db, outlook_email):
                        create_user(db, UserCreate(
                            username=outlook_email, email=outlook_email,
                            password=DEV_BOOTSTRAP_PASSWORD,
                        ))
                        logger.info("Dev bootstrap user created (outlook).")
                    ensure_exact_system_roles(db, outlook_email, {"user"})
                else:
                    logger.info("Skipping dev bootstrap users (ENVIRONMENT=%s)", os.environ.get("ENVIRONMENT", "not set"))

                # Ensure default capabilities (media:view) assigned to roles
                ensure_default_capabilities(db)
                logger.info("Default capabilities ensured")

                db.close()
                logger.info("Database initialization completed successfully")

            except (OSError, RuntimeError) as e:
                logger.error("Database initialization failed: %s", e)
                if "db" in locals():
                    db.close()
                raise

        await run_in_threadpool(init_guid_and_admin)

        async def converge_bootstrap_roles() -> None:
            fresh_email = FRESH_ADMIN_EMAIL
            simple_user_email = "nick.glezakos@gmail.com"
            outlook_email = "nick.glezakos@outlook.com"

            fresh_roles = {"owner", "admin", "user"}
            approved_owner_email = None
            if authority_service.is_configured():
                db = SessionLocal()
                try:
                    authority_result = await authority_service.verify_owner_candidate(db, fresh_email)
                finally:
                    db.close()
                if authority_result.get("approved"):
                    logger.info("Authority approved %s as startup owner", fresh_email)
                else:
                    fresh_roles = {"admin", "user"}
                    approved_owner_email = (
                        authority_result.get("installation", {}).get("approved_owner_email")
                    )
                    logger.warning(
                        "Authority did not approve %s as startup owner: %s",
                        fresh_email,
                        authority_result.get("reason", "unknown_reason"),
                    )
            else:
                logger.info("Authority integration not configured; using local startup owner fallback")

            # Keep the local fresh user as an admin regardless of authority owner approval.
            # Authority may remove owner, but this account remains the privileged development/admin user.
            fresh_roles.update({"admin", "user"})

            def apply_bootstrap_roles() -> None:
                db = SessionLocal()
                try:
                    simple_user_roles = {"user"}
                    outlook_roles = {"user"}

                    def converge_bootstrap_user_roles(email: str, role_names: set[str]) -> None:
                        try:
                            ensure_exact_system_roles(db, email, role_names)
                        except ValueError as exc:
                            if str(exc) != "Cannot remove the final owner role assignment":
                                raise
                            logger.warning(
                                "Preserving existing owner role for %s during startup bootstrap because authority fallback did not identify a replacement owner yet",
                                email,
                            )

                    if approved_owner_email and approved_owner_email != fresh_email:
                        approved_owner = get_user_by_email(db, approved_owner_email)
                        if approved_owner:
                            converge_bootstrap_user_roles(
                                approved_owner_email,
                                {"owner", "admin", "user"},
                            )
                            logger.info(
                                "Authority-approved owner bootstrap converged for %s",
                                approved_owner_email,
                            )
                        else:
                            logger.warning(
                                "Authority-approved owner %s does not exist locally yet",
                                approved_owner_email,
                            )

                    converge_bootstrap_user_roles(fresh_email, fresh_roles)
                    if approved_owner_email == simple_user_email:
                        simple_user_roles = {"owner", "admin", "user"}
                    converge_bootstrap_user_roles(simple_user_email, simple_user_roles)

                    if approved_owner_email == outlook_email:
                        outlook_roles = {"owner", "admin", "user"}
                    converge_bootstrap_user_roles(outlook_email, outlook_roles)
                    logger.info(
                        "Development role bootstrap converged: fresh=%s, nick=%s, outlook=%s",
                        sorted(fresh_roles),
                        sorted(simple_user_roles),
                        sorted(outlook_roles),
                    )
                finally:
                    db.close()

            await run_in_threadpool(apply_bootstrap_roles)

        await converge_bootstrap_roles()

        async def revalidate_authority_periodically() -> None:
            interval_seconds = max(1, settings.AUTHORITY_REVALIDATION_INTERVAL_SECONDS)
            while True:
                db = SessionLocal()
                try:
                    result = await authority_service.refresh_cached_authority_state(db)
                    if result.get("configured"):
                        logger.info(
                            "Authority cache refresh completed: %s",
                            result.get("reason", "unknown_reason"),
                        )
                except RuntimeError as e:
                    logger.error("Authority cache refresh failed: %s", e)
                finally:
                    db.close()
                await asyncio.sleep(interval_seconds)

        if authority_service.is_configured():
            authority_revalidation_task = asyncio.create_task(revalidate_authority_periodically())
            logger.info(
                "Authority revalidation worker started with %s second interval",
                max(1, settings.AUTHORITY_REVALIDATION_INTERVAL_SECONDS),
            )

        # Initialize licensing service if available
        if LICENSING_AVAILABLE and init_licensing_service:
            try:
                await init_licensing_service()
                logger.info("✅ Licensing service initialized")
            except RuntimeError as e:
                logger.error("⚠️ Licensing service initialization failed: %s", e)

        # Start multicast discovery broadcaster
        def start_multicast_broadcaster():
            nonlocal multicast_broadcaster
            try:
                multicast_broadcaster = MulticastServiceDiscoveryBroadcaster(
                    service_port=settings.PORT, service_name="ppl-meta-node"
                )
                if multicast_broadcaster.start():
                    logger.info("✅ Multicast discovery broadcaster started")
                else:
                    logger.warning("⚠️ Failed to start multicast broadcaster")
                    multicast_broadcaster = None
            except RuntimeError as e:
                logger.error("❌ Error starting multicast broadcaster: %s", e)
                multicast_broadcaster = None

        await run_in_threadpool(start_multicast_broadcaster)

        # VPN mesh enrollment (one-time bootstrap, non-blocking)
        try:
            vpn_ok = await asyncio.to_thread(enroll_once)
            if vpn_ok:
                logger.info("✅ VPN mesh enrollment complete")
        except Exception:
            pass  # Non-fatal — VPN is optional

        # Periodically re-report the platform's local LAN IP so the Authority can
        # hand leaf devices an up-to-date address if the router/DHCP changes it.
        if vpn_ok:
            async def report_platform_local_ip_periodically() -> None:
                interval_seconds = max(
                    60,
                    int(getattr(settings, "AUTHORITY_REVALIDATION_INTERVAL_SECONDS", 300) or 300),
                )
                while True:
                    try:
                        await asyncio.to_thread(report_platform_local_ip)
                    except Exception:
                        pass  # Non-fatal — VPN is optional
                    await asyncio.sleep(interval_seconds)

            vpn_local_ip_report_task = asyncio.create_task(
                report_platform_local_ip_periodically()
            )
            logger.info("Platform local-IP reporter started")

        logger.info("Service startup completed successfully")

    except (OSError, RuntimeError) as e:
        logger.error("Service startup failed: %s", e)
        raise

    yield

    logger.info("Service shutting down...")

    if authority_revalidation_task:
        authority_revalidation_task.cancel()
        try:
            await authority_revalidation_task
        except asyncio.CancelledError:
            logger.info("Authority revalidation worker stopped")

    if vpn_local_ip_report_task:
        vpn_local_ip_report_task.cancel()
        try:
            await vpn_local_ip_report_task
        except asyncio.CancelledError:
            logger.info("Platform local-IP reporter stopped")

    # Stop multicast broadcaster
    if multicast_broadcaster:
        try:
            multicast_broadcaster.stop()
            logger.info("✅ Multicast discovery broadcaster stopped")
        except RuntimeError as e:
            logger.error("❌ Error stopping multicast broadcaster: %s", e)

    # Deregister from service discovery
    if service_discovery_available:
        try:
            from shared.service_discovery import deregister_service

            await deregister_service("ppl-meta-node")
            logger.info("Service deregistered from discovery service")
        except (ImportError, RuntimeError) as e:
            logger.error("Failed to deregister service: %s", e)


# FastAPI application with metadata
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="User Management Microservice for PPL Meta Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add global exception handlers for validation errors
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc):
    """Handle Pydantic validation errors."""
    logger.error("Validation error: %s", exc)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc):
    """Handle value errors from custom validation."""
    logger.error("Value error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


# Initialize metrics - disabled for testing
# metrics_collector = init_metrics(
#     service_name=settings.APP_NAME, service_version=settings.APP_VERSION
# )

# Middleware
app.add_middleware(TimingMiddleware)
app.add_middleware(AuthoritySafeguardMiddleware)

# Add metrics middleware - disabled for testing
# app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware - Dynamic IP detection for external access
dynamic_hosts = get_dynamic_allowed_hosts()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=dynamic_hosts)

# Include API routers
app.include_router(v1_router)  # API v1 routes
app.include_router(legacy_health_router)  # Legacy health endpoint

# Add metrics endpoint - disabled for testing
# metrics_router = create_metrics_endpoint()
# app.include_router(metrics_router, tags=["Metrics"])

# Legacy routes for backward compatibility
app.include_router(roles.router)
app.include_router(otp.router)
app.include_router(logs.router)
app.include_router(backup.router)
app.include_router(app_settings.router)
app.include_router(app_settings.router, prefix="/api/v1")
app.include_router(capabilities.router)

# Initialize metrics - disabled for testing
# init_metrics()

# Add Prometheus middleware for metrics endpoint - disabled for testing
# app.add_middleware(PrometheusMiddleware)
# create_metrics_endpoint(app)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# Mobile pairing endpoints
@app.get("/api/v1/mobile/discover")
async def mobile_discover():
    """Mobile discovery endpoint for automatic pairing."""
    network_ips = get_local_network_ips()

    # Categorize network types
    network_types = {}
    for ip in network_ips:
        if ip.startswith(("192.168.", "10.", "172.")):
            network_types[ip] = "local_network"
        elif ip.startswith("100."):
            network_types[ip] = "vpn_tailscale"
        elif ip.startswith("169.254."):
            network_types[ip] = "link_local"
        else:
            network_types[ip] = "other"

    return {
        "service": "PPL Meta Platform",
        "version": settings.APP_VERSION,
        "node_service": {
            "port": settings.PORT,
            "endpoints": {
                "health": "/api/v1/health",
                "login": "/api/v1/users/login",
                "discover": "/api/v1/mobile/discover",
            },
        },
        "camera_service": {
            "port": 8005,
            "endpoints": {
                "health": "/health",
                "mobile_cameras": "/api/v1/cameras/mobile",
            },
        },
        "network": {
            "detected_ips": network_ips,
            "network_types": network_types,
            "supported_hosts": get_dynamic_allowed_hosts(),
            "vpn_support": "tailscale_wireguard_compatible",
        },
        "pairing": {
            "status": "ready",
            "instructions": ("Use any detected IP with the specified ports to connect"),
            "vpn_info": "Supports Tailscale and other mesh VPN networks",
        },
    }


@app.get("/api/v1/mobile/pairing-info")
async def get_pairing_info():
    """Get pairing information for mobile app setup."""
    network_ips = get_local_network_ips()

    # Prefer the first private network IP if available
    preferred_ip = network_ips[0] if network_ips else "localhost"

    return {
        "platform": "PPL Meta",
        "connection": {
            "preferred_ip": preferred_ip,
            "available_ips": network_ips,
            "node_service_url": f"http://{preferred_ip}:8001",
            "camera_service_url": f"http://{preferred_ip}:8005",
        },
        "services": {
            "node": {"port": 8001, "status": "running"},
            "cameras": {"port": 8005, "status": "running"},
            "media": {"port": 8000, "status": "running"},
            "gateway": {"port": 8080, "status": "running"},
        },
        "authentication": {
            "login_endpoint": f"http://{preferred_ip}:8001/api/v1/users/login",
            "method": "POST",
            "content_type": "application/x-www-form-urlencoded",
            "fields": ["username", "password"],
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )

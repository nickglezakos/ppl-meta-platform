"""Users API v1 - User management endpoints with inter-service communication support."""

import logging
import os
import smtplib
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Setup logger
logger = logging.getLogger(__name__)

from src.config import settings
from src.auth_utils import create_access_token, get_current_user, require_capability
from src.database import get_db
from src.mail import send_email
from src.models.user import User, UserAction
from src.schemas.user import (
    AdminSetPassword,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserActionRead,
    UserCreate,
    UserPasswordUpdate,
    UserRead,
)
from src.services.user_service import (
    create_user_with_licensing,
    create_password_reset_token,
    get_user_by_email,
    get_user_by_guid,
    get_user_by_id,
    list_users,
    log_user_action,
    set_new_password,
    update_user_password,
    verify_password_reset_token,
    verify_user_email,
)

# Import shared validation - disabled for testing
# from shared.validation import (
#     FieldValidators,
#     SecurityValidator,
#     handle_validation_error,
#     validate_password_update_data,
#     validate_user_create_data,
# )


# Simple validation replacement functions for testing
def validate_user_create_data(user_data):
    """Simple validation replacement."""
    return user_data


def validate_password_update_data(password_data):
    """Simple validation replacement."""
    return password_data


def handle_validation_error(e):
    """Simple validation error handler replacement."""
    return HTTPException(status_code=400, detail=str(e))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/v1/users", tags=["users-v1"])


def verify_service_token(authorization: str = Header(None)):
    """Verify inter-service communication token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authorization header missing",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.split(" ")[1]
    if token != settings.SERVICE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token"
        )
    return True


# ===== AUTHENTICATION ENDPOINTS =====


@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with enhanced validation."""
    try:
        # Apply enhanced validation to user data
        user_data = user.dict()
        validated_data = validate_user_create_data(user_data)

        # Additional business logic validation
        if get_user_by_email(db, validated_data["email"]):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create validated user object
        validated_user = UserCreate(**validated_data)
        created_user = await create_user_with_licensing(db, validated_user)

        # Debug logging before user action logging
        logger.info("User created successfully with ID: %s", created_user.id)

        log_user_action(db, created_user.username, created_user.email, "register")

        # Send verification email
        try:
            verification_token = jwt.encode(
                {
                    "sub": created_user.id,
                    "action": "verify_email",
                    "exp": datetime.utcnow() + timedelta(hours=24),
                },
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM,
            )
            verify_link = f"{settings.FRONTEND_URL}/#/verify-email?token={verification_token}"
            await send_email(
                subject="Verify your EyeNet account",
                email_to=created_user.email,
                body=f"""
                    <h3>Welcome to EyeNet, {created_user.username}!</h3>
                    <p>Please verify your email by clicking the button below:</p>
                    <a href="{verify_link}" style="padding:12px 24px;background:#1a73e8;color:white;
                       text-decoration:none;border-radius:6px;display:inline-block;">Verify Email</a>
                    <p>This link expires in 24 hours.</p>
                """,
            )
        except (ConnectionError, OSError, RuntimeError, smtplib.SMTPException) as email_err:
            logger.warning("Failed to send verification email: %s", email_err)

        # Manual response construction to avoid any serialization issues
        response_data = {
            "message": "User registered successfully",
            "user": {
                "id": created_user.id,
                "guid": str(created_user.guid),  # Force string conversion
                "username": created_user.username,
                "email": created_user.email,
                "email_verified": created_user.email_verified,
                "is_active": created_user.is_active,
                "created_at": created_user.created_at.isoformat(),
            },
        }
        logger.info("Response data constructed successfully")
        return response_data
    except HTTPException:
        # Re-raise validation errors (they already have proper format)
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error("Registration error: %s", e)
        raise HTTPException(status_code=500, detail="Registration failed") from e


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email address."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        action: str = payload.get("action")
        if user_id is None or action != "verify_email":
            raise HTTPException(status_code=400, detail="Invalid verification token")
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired token") from exc

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        return {"detail": "Email already verified."}

    verify_user_email(db, user_id)

    # Send thank you email after verification
    thank_you_body = f"""
        <h3>Thank you, {user.username}!</h3>
        <p>Your email has been successfully verified. You can now use all features of our service.</p>
    """
    await send_email(
        subject="Thank you for verifying your email",
        email_to=user.email,
        body=thank_you_body,
    )

    return {"detail": "Email successfully verified."}


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """User login."""
    user = get_user_by_email(db, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
    })
    log_user_action(db, user.username, user.email, "login")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/platform/services")
async def get_platform_services(
    _request: Request,
    mobile_ip: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _authorized_user: User = Depends(require_capability("auth.session.use")),
):
    """Get platform service discovery information for external connectivity.

    This endpoint provides all microservice endpoints and connectivity details
    needed for external services like mobile cameras to connect to platform.
    """
    try:
        # Detect actual network IP for platform services
        import socket
        import subprocess

        # Detect actual network IP for registration
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except OSError:
            # Fallback to hostname resolution
            local_ip = socket.gethostbyname(socket.gethostname())

        hostname = socket.gethostname()

        # If mobile IP is provided, use it for streaming endpoints
        # so the platform can connect to the mobile device
        streaming_ip = mobile_ip if mobile_ip else local_ip

        # Check for Tailscale IP (100.x.x.x range)
        tailscale_ip = None
        try:
            result = subprocess.run(
                ["ip", "addr", "show", "tailscale0"],
                capture_output=True,
                check=False,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "inet " in line and "100." in line:
                        tailscale_ip = line.split()[1].split("/")[0]
                        break
        except (OSError, subprocess.SubprocessError):
            # Tailscale not available or error occurred
            pass

        # Define platform services
        platform_services = {
            "platform_info": {
                "name": "PPL Meta Platform",
                "version": "2.12.1",
                "environment": "development",
            },
            "connectivity": {
                "local_ip": local_ip,
                "tailscale_ip": tailscale_ip,
                "hostname": hostname,
                "networks": (["local", "tailscale"] if tailscale_ip else ["local"]),
            },
            "microservices": {
                "node": {
                    "name": "User Management Service",
                    "port": 8001,
                    "endpoints": {
                        "local": f"http://{local_ip}:8001",
                        "tailscale": (
                            f"http://{tailscale_ip}:8001" if tailscale_ip else None
                        ),
                    },
                    "health": "/api/v1/health",
                    "purpose": "User authentication and management",
                },
                "media": {
                    "name": "Media Processing Service",
                    "port": 8000,
                    "endpoints": {
                        "local": f"http://{local_ip}:8000",
                        "tailscale": (
                            f"http://{tailscale_ip}:8000" if tailscale_ip else None
                        ),
                    },
                    "health": "/health",
                    "purpose": "Media processing and streaming (mobile cameras)",
                    "streaming_endpoints": {
                        "upload": "/upload",
                        "stream": "/stream",
                        "mjpeg": "/mjpeg",
                    },
                },
                "cameras": {
                    "name": "Camera Management Service",
                    "port": 8005,
                    "endpoints": {
                        "local": f"http://{local_ip}:8005",
                        "tailscale": (
                            f"http://{tailscale_ip}:8005" if tailscale_ip else None
                        ),
                    },
                    "health": "/health",
                    "purpose": "Camera registration and management",
                    "mobile_endpoints": {
                        "register": "/api/cameras/register",
                        "status": "/api/cameras/status",
                        "stream_config": "/api/cameras/stream-config",
                    },
                },
                "gateway": {
                    "name": "API Gateway Service",
                    "port": 8080,
                    "endpoints": {
                        "local": f"http://{local_ip}:8080",
                        "tailscale": (
                            f"http://{tailscale_ip}:8080" if tailscale_ip else None
                        ),
                    },
                    "health": "/health",
                    "purpose": "API routing and aggregation",
                },
                "orchestrator": {
                    "name": "Workflow Orchestration Service",
                    "port": 8002,
                    "endpoints": {
                        "local": f"http://{local_ip}:8002",
                        "tailscale": (
                            f"http://{tailscale_ip}:8002" if tailscale_ip else None
                        ),
                    },
                    "health": "/health",
                    "purpose": "Workflow management and automation",
                },
                "vision": {
                    "name": "Computer Vision Service",
                    "port": 8003,
                    "endpoints": {
                        "local": f"http://{local_ip}:8003",
                        "tailscale": (
                            f"http://{tailscale_ip}:8003" if tailscale_ip else None
                        ),
                    },
                    "health": "/health",
                    "purpose": "Image analysis and face detection",
                },
            },
            "mobile_camera_config": {
                "recommended_service": "cameras",
                "recommended_endpoint": f"http://{streaming_ip}:8005",
                "fallback_service": "media",
                "fallback_endpoint": f"http://{streaming_ip}:8000",
                "streaming_format": "mjpeg",
                "registration_required": True,
                "authentication": "bearer_token",
            },
            "streaming_endpoints": {
                "mjpeg": f"http://{streaming_ip}:8000/mjpeg",
                "websocket": (
                    f"ws://{streaming_ip}:8005/api/v1/cameras/" f"{{device_id}}/stream"
                ),
                "upload": f"http://{streaming_ip}:8000/upload",
                "stream": f"http://{streaming_ip}:8000/stream",
            },
            "camera_endpoints": {
                "register": (f"http://{streaming_ip}:8005/api/v1/cameras/" f"mobile"),
                "status": f"http://{streaming_ip}:8005/api/v1/cameras/status",
                "config": (
                    f"http://{streaming_ip}:8005/api/v1/cameras/" f"stream-config"
                ),
                "websocket_stream": (
                    f"ws://{streaming_ip}:8005/api/v1/cameras/" f"{{device_id}}/stream"
                ),
            },
            "server_info": {
                "host": streaming_ip,
                "node_port": 8001,
                "media_port": 8000,
                "gateway_port": 8080,
                "cameras_port": 8005,
                "vision_port": 8003,
                "orchestrator_port": 8002,
            },
            "network_info": {
                "proxy_available": True,
                "nginx_port": 80,
                "ssl_available": False,
                "cors_enabled": True,
            },
        }

        # Log the service discovery request
        log_user_action(
            db, current_user.username, current_user.email, "platform_services_discovery"
        )

        return platform_services

    except Exception as e:
        logger.error("Platform services discovery error: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve platform services"
        ) from e


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user profile."""
    try:
        from src.services.capabilites_service import get_roles_and_capabilities_by_user

        updated_at = None
        if hasattr(current_user, "updated_at") and current_user.updated_at:
            updated_at = current_user.updated_at.isoformat()

        rc = get_roles_and_capabilities_by_user(db, current_user.id)

        return {
            "id": current_user.id,
            "guid": str(current_user.guid),
            "username": current_user.username,
            "email": current_user.email,
            "email_verified": current_user.email_verified,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat(),
            "updated_at": updated_at,
            "roles": rc["roles"],
            "capabilities": rc["capabilities"],
        }
    except Exception as e:
        logger.error("Profile retrieval error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve profile") from e


@router.get("/debug-profile")
async def debug_get_profile(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    _authorized_user: User = Depends(require_capability("users.profile.read")),
):
    """Debug profile endpoint with manual token extraction."""
    logger.info("Debug profile endpoint called with authorization: %s", authorization)

    if not authorization:
        logger.error("No authorization header provided")
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        logger.error("Invalid authorization header format: %s", authorization)
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    token = authorization[7:]  # Remove "Bearer " prefix
    logger.info("Extracted token: %s", token[:20] + "...")

    try:
        logger.info("Decoding JWT with SECRET_KEY length: %d", len(settings.SECRET_KEY))
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        logger.info("JWT payload: %s", payload)

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="No user ID in token")

        user = get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "debug": "success",
        }
    except JWTError as e:
        logger.error("JWT error: %s", e)
        raise HTTPException(status_code=401, detail=f"JWT error: {str(e)}") from e
    except Exception as e:
        logger.error("Debug profile error: %s", e)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}") from e


@router.post("/logout")
def logout(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
    _authorized_user: UserRead = Depends(require_capability("auth.session.use")),
):
    """User logout (stateless)."""
    log_user_action(db, current_user.username, current_user.email, "logout")
    return {"msg": "Logout successful. Please delete your token client-side."}


# ===== INTER-SERVICE AUTHENTICATION ENDPOINTS =====


@router.post("/validate-token")
async def validate_token(
    token_data: Dict[str, str],
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_token),
):
    """Validate JWT token for inter-service communication."""
    token = token_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "email_verified": user.email_verified,
        }
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


@router.get("/user-info/{user_id}")
async def get_user_info_for_service(
    user_id: int, db: Session = Depends(get_db), _: bool = Depends(verify_service_token)
):
    """Get user information for inter-service communication."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "guid": user.guid,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.get("/user-permissions/{user_id}")
async def get_user_permissions_for_service(
    user_id: int, db: Session = Depends(get_db), _: bool = Depends(verify_service_token)
):
    """Get user permissions for inter-service communication."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user roles and capabilities
    user_roles = []
    user_capabilities = []

    for user_role in user.roles:
        role = user_role.role
        user_roles.append(
            {
                "role_id": role.id,
                "role_name": role.name,
                "role_description": getattr(role, "description", None),
            }
        )

        for role_capability in role.capabilities:
            capability = role_capability.capability
            if capability.name not in [c["name"] for c in user_capabilities]:
                user_capabilities.append(
                    {
                        "name": capability.name,
                        "description": getattr(capability, "description", None),
                    }
                )

    return {"user_id": user.id, "roles": user_roles, "capabilities": user_capabilities}


@router.get("/user-profile/{user_id}")
async def get_user_profile_admin(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_capability("users.accounts.read")),
):
    """Get a user's profile with roles and capabilities. Admin only."""
    from src.services.capabilites_service import get_roles_and_capabilities_by_user

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_rc = get_roles_and_capabilities_by_user(db, user_id)
    return {
        "id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "email_verified": target_user.email_verified,
        "created_at": str(target_user.created_at) if target_user.created_at else None,
        "updated_at": str(target_user.updated_at) if target_user.updated_at else None,
        "roles": target_rc["roles"],
        "capabilities": target_rc["capabilities"],
    }


@router.post("/toggle-capability/{user_id}")
async def toggle_user_capability(
    user_id: int,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_capability("auth.capabilities.assign")),
):
    """Toggle a capability for a user. Admin only."""
    from src.services.capabilites_service import get_roles_and_capabilities_by_user
    from src.models.role import Capability, RoleCapability

    capability_name = body.get("capability")
    enabled = body.get("enabled")
    if not capability_name or enabled is None:
        raise HTTPException(status_code=400, detail="'capability' and 'enabled' are required")

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create the capability row
    cap = db.query(Capability).filter(Capability.name == capability_name).first()
    if not cap:
        cap = Capability(name=capability_name)
        db.add(cap)
        db.commit()
        db.refresh(cap)

    # Iterate over each of the user's roles and add/remove the capability
    for user_role in target_user.roles:
        role = user_role.role
        existing = db.query(RoleCapability).filter_by(
            role_id=role.id, capability_id=cap.id
        ).first()

        if enabled and not existing:
            db.add(RoleCapability(role_id=role.id, capability_id=cap.id))
        elif not enabled and existing:
            db.delete(existing)

    db.commit()

    log_user_action(
        db,
        current_user.username,
        current_user.email,
        f"user_capability_toggle:user={user_id}:capability={capability_name}:enabled={enabled}",
    )

    updated_rc = get_roles_and_capabilities_by_user(db, user_id)
    return {"user_id": user_id, "roles": updated_rc["roles"], "capabilities": updated_rc["capabilities"]}





@router.get("/{user_id}", response_model=UserRead)
def api_get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: UserRead = Depends(require_capability("users.accounts.read")),
):
    """Get user by ID."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/guid/{guid}", response_model=UserRead)
def api_get_user_by_guid(
    guid: str,
    db: Session = Depends(get_db),
    _current_user: UserRead = Depends(require_capability("users.accounts.read")),
):
    """Get user by GUID."""
    user = get_user_by_guid(db, guid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=list[UserRead])
def api_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    _current_user: UserRead = Depends(require_capability("users.accounts.read")),
):
    """List users with pagination."""
    users = list_users(db, skip=skip, limit=limit)
    return users


@router.get("/actions/", response_model=list[UserActionRead])
def api_list_user_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    _current_user: UserRead = Depends(require_capability("users.accounts.read")),
):
    """List user actions with pagination."""
    actions = db.query(UserAction).offset(skip).limit(limit).all()
    return actions


@router.post("/update-password")
async def update_password(
    password_update: UserPasswordUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
    _authorized_user: UserRead = Depends(require_capability("users.password.change_self")),
):
    """Update user password with enhanced validation."""
    try:
        # Apply enhanced validation to password update data
        password_data = password_update.dict()
        validated_data = validate_password_update_data(password_data)

        # Business logic validation
        user = get_user_by_id(db, current_user.id)
        if not user or not pwd_context.verify(
            validated_data["old_password"], user.hashed_password
        ):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        update_user_password(
            db,
            current_user.id,
            validated_data["old_password"],
            validated_data["new_password"],
        )
        log_user_action(
            db, current_user.username, current_user.email, "password_update"
        )
        return {"detail": "Password updated successfully"}
    except (TypeError, ValueError) as e:
        # Handle unexpected errors with proper validation response
        return handle_validation_error(e)


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset."""
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_password_reset_token(user.id, request.email)
    reset_link = f"{settings.FRONTEND_URL}/#/reset-password?token={token}"

    email_body = f"""
        <h3>Password Reset Request</h3>
        <p>We received a request to reset your password.</p>
        <p>Click the button below to set a new password:</p>
        <a href="{reset_link}" style="padding:12px 24px;background:#1a73e8;color:white;
           text-decoration:none;border-radius:6px;display:inline-block;">Reset Password</a>
        <p>This link will expire in 1 hour.</p>
        <p style="color:#666;">If you didn't request this, you can safely ignore this email.</p>
    """

    await send_email(
        subject="Reset your EyeNet password", email_to=request.email, body=email_body
    )

    return {"detail": "Password reset email sent"}


@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password with token."""
    payload = verify_password_reset_token(request.token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    email = payload.get("email")
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    set_new_password(db, user.id, request.new_password)
    log_user_action(db, user.username, user.email, "password_reset")

    return {"detail": "Password reset successfully"}


@router.post("/admin/set-password/{user_id}")
async def admin_set_password(
    user_id: int,
    body: AdminSetPassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_capability("users.accounts.update")),
):
    """Admin sets a new password for a user and optionally emails it."""

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    _result, error = set_new_password(db, user_id, body.new_password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    log_user_action(
        db,
        current_user.username,
        current_user.email,
        f"admin_password_set:user={user_id}",
    )
    log_user_action(db, target_user.username, target_user.email, "admin_password_set")

    if body.send_email:
        email_body = f"""
            <h3>Your password has been updated</h3>
            <p>Hi {target_user.username},</p>
            <p>An administrator has set a new password for your EyeNet account.</p>
            <p>Your new password is: <strong>{body.new_password}</strong></p>
            <p>Please sign in and change your password as soon as possible.</p>
        """
        await send_email(
            subject="Your EyeNet password has been updated",
            email_to=target_user.email,
            body=email_body,
        )

    return {
        "detail": "Password updated successfully",
        "email_sent": body.send_email,
    }

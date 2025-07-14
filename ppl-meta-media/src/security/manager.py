"""
Security middleware integration for PPL Meta Media Service.
Integrates all security services with FastAPI application.
"""

import logging
import os
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.security import HTTPBearer

from .auth import (
    AuthenticationService,
    AuthorizationMiddleware,
    RoleBasedAccessControl,
    SecurityConfig,
)
from .file_security import FileSecurityService
from .rate_limiting import RateLimitingService
from .validation import InputValidationService

logger = logging.getLogger(__name__)


class SecurityManager:
    """Centralized security manager for all security services."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        redis_url: Optional[str] = None,
        enable_malware_scanning: bool = True,
        strict_validation: bool = True,
    ):
        """
        Initialize security manager with all security services.

        Args:
            secret_key: JWT secret key (from environment if None)
            redis_url: Redis URL for rate limiting
            enable_malware_scanning: Enable ClamAV malware scanning
            strict_validation: Enable strict input validation
        """
        # Use environment variables for sensitive configuration
        self.secret_key = secret_key or os.getenv(
            "JWT_SECRET_KEY", "default-secret-change-in-production"
        )
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")

        # Initialize security services
        self.auth_service = AuthenticationService(self.secret_key)
        self.auth_middleware = AuthorizationMiddleware(self.auth_service)
        self.file_security = FileSecurityService(enable_malware_scanning)
        self.rate_limiter = RateLimitingService(
            self.redis_url,
            default_limits={
                "upload": int(os.getenv("RATE_LIMIT_UPLOAD", "10")),
                "api": int(os.getenv("RATE_LIMIT_API", "100")),
                "download": int(os.getenv("RATE_LIMIT_DOWNLOAD", "50")),
                "search": int(os.getenv("RATE_LIMIT_SEARCH", "30")),
                "auth": int(os.getenv("RATE_LIMIT_AUTH", "5")),
            },
        )
        self.input_validator = InputValidationService(strict_validation)

        logger.info("Security manager initialized with all services")

    def setup_security_middleware(self, app: FastAPI) -> None:
        """
        Setup security middleware for FastAPI application.

        Args:
            app: FastAPI application instance
        """

        @app.middleware("http")
        async def security_middleware(request: Request, call_next):
            """Security middleware for all HTTP requests."""
            try:
                # Add security headers to all responses
                response = await call_next(request)

                # Add security headers
                security_headers = SecurityConfig.get_security_headers()
                for header, value in security_headers.items():
                    response.headers[header] = value

                # Add rate limiting headers if available
                rate_info = getattr(request.state, "rate_limit_info", None)
                if rate_info:
                    rate_headers = self.rate_limiter.get_rate_limit_headers(rate_info)
                    for header, value in rate_headers.items():
                        response.headers[header] = value

                return response

            except Exception as e:
                logger.error("Security middleware error: %s", e)
                # Return error response
                return Response(
                    content="Security validation failed",
                    status_code=500,
                    headers=SecurityConfig.get_security_headers(),
                )

        @app.middleware("http")
        async def rate_limiting_middleware(request: Request, call_next):
            """Rate limiting middleware."""
            try:
                # Determine endpoint type for rate limiting
                endpoint_type = "api"  # Default

                if "upload" in request.url.path:
                    endpoint_type = "upload"
                elif "download" in request.url.path or "thumbnail" in request.url.path:
                    endpoint_type = "download"
                elif "search" in request.url.path:
                    endpoint_type = "search"
                elif "auth" in request.url.path:
                    endpoint_type = "auth"

                # Check rate limit
                allowed, rate_info = self.rate_limiter.check_rate_limit(
                    request, endpoint_type
                )

                if not allowed:
                    # Return rate limit exceeded response
                    headers = self.rate_limiter.get_rate_limit_headers(rate_info)
                    headers.update(SecurityConfig.get_security_headers())

                    return Response(
                        content=f"Rate limit exceeded: {rate_info['message']}",
                        status_code=429,
                        headers=headers,
                    )

                # Store rate info for use in response headers
                request.state.rate_limit_info = rate_info

                return await call_next(request)

            except Exception as e:
                logger.error("Rate limiting middleware error: %s", e)
                return await call_next(request)

        logger.info("Security middleware configured")

    def get_security_dependencies(self):
        """Get security dependencies for FastAPI dependency injection."""
        return {
            "file_security": self.file_security,
            "auth_service": self.auth_service,
            "auth_middleware": self.auth_middleware,
            "rate_limiter": self.rate_limiter,
            "input_validator": self.input_validator,
        }

    def validate_environment(self) -> dict:
        """Validate security environment configuration."""
        validation_result = {
            "jwt_secret_configured": self.secret_key
            != "default-secret-change-in-production",
            "redis_available": False,
            "malware_scanner_available": False,
            "security_services_active": True,
            "recommendations": [],
        }

        # Test Redis connection
        try:
            test_allowed, _ = self.rate_limiter.check_rate_limit(
                type(
                    "Request",
                    (),
                    {
                        "client": type("Client", (), {"host": "test"})(),
                        "headers": {},
                        "url": type("URL", (), {"path": "/test"})(),
                    },
                )(),
                "api",
            )
            validation_result["redis_available"] = True
        except Exception:
            validation_result["recommendations"].append(
                "Redis not available - rate limiting will be disabled"
            )

        # Check malware scanner
        validation_result["malware_scanner_available"] = (
            self.file_security.enable_malware_scanning
        )

        if not validation_result["malware_scanner_available"]:
            validation_result["recommendations"].append(
                "ClamAV not available - malware scanning will be disabled"
            )

        # Check JWT secret
        if not validation_result["jwt_secret_configured"]:
            validation_result["recommendations"].append(
                "Using default JWT secret - change JWT_SECRET_KEY environment variable"
            )

        return validation_result

    def get_security_status(self) -> dict:
        """Get current security status and configuration."""
        return {
            "authentication": {
                "jwt_enabled": True,
                "algorithm": self.auth_service.algorithm,
                "secret_configured": self.secret_key
                != "default-secret-change-in-production",
            },
            "authorization": {
                "rbac_enabled": True,
                "roles_configured": len(
                    RoleBasedAccessControl.get_user_permissions("admin")
                ),
            },
            "rate_limiting": {
                "redis_enabled": self.rate_limiter.redis_client is not None,
                "limits_configured": self.rate_limiter.default_limits,
            },
            "file_security": {
                "signature_validation": True,
                "malware_scanning": self.file_security.enable_malware_scanning,
                "size_limits": self.file_security.MAX_FILE_SIZES,
            },
            "input_validation": {
                "sql_injection_protection": True,
                "xss_protection": True,
                "path_traversal_protection": True,
                "strict_mode": self.input_validator.strict_mode,
            },
        }

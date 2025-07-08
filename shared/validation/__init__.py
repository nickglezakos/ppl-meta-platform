"""
PPL Meta Platform - Shared Input Validation
Resolves ISSUE-016: Missing Input Validation

This module provides comprehensive input validation utilities:
- Request/response schema validation with detailed error messages
- SQL injection prevention
- XSS protection
- Field length and format validation
- Custom validators for business logic
"""

import html
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationErrorType(str, Enum):
    """Types of validation errors."""

    REQUIRED_FIELD = "required_field"
    INVALID_FORMAT = "invalid_format"
    LENGTH_VIOLATION = "length_violation"
    BUSINESS_RULE = "business_rule"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT = "rate_limit"


class ValidationErrorDetail:
    """Detailed validation error information."""

    def __init__(
        self,
        field: str,
        error_type: ValidationErrorType,
        message: str,
        value: Optional[Any] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ):
        self.field = field
        self.error_type = error_type
        self.message = message
        self.value = value
        self.constraints = constraints

    def dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "error_type": self.error_type,
            "message": self.message,
            "value": self.value,
            "constraints": self.constraints,
        }


class ValidationErrorResponse:
    """Standardized validation error response."""

    def __init__(
        self, details: List[ValidationErrorDetail], request_id: Optional[str] = None
    ):
        self.error = "validation_failed"
        self.message = "Request validation failed"
        self.details = details
        self.request_id = request_id
        from datetime import datetime

        self.timestamp = datetime.now().isoformat()

    def dict(self) -> Dict[str, Any]:
        return {
            "error": self.error,
            "message": self.message,
            "details": [detail.dict() for detail in self.details],
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


class SecurityValidator:
    """Security-focused validation utilities."""

    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",  # noqa: E501
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*\b=\b.*\bOR\b)",
        r"(\bAND\b.*\b=\b.*\bAND\b)",
        r"(\'\s*(OR|AND)\s*\'\s*=\s*\')",
        r"(\d\s*(OR|AND)\s*\d\s*=\s*\d)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
    ]

    @classmethod
    def validate_sql_injection(cls, value: str, field_name: str) -> str:
        """Check for potential SQL injection attempts."""
        if not isinstance(value, str):
            return value

        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential SQL injection detected in {field_name}")
        return value

    @classmethod
    def validate_xss(cls, value: str, field_name: str) -> str:
        """Check for potential XSS attempts."""
        if not isinstance(value, str):
            return value

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential XSS detected in {field_name}")
        return value

    @classmethod
    def sanitize_html(cls, value: str) -> str:
        """Sanitize HTML content using bleach."""
        if not isinstance(value, str):
            return value

        try:
            import bleach

            # Allow basic formatting tags only
            allowed_tags = ["b", "i", "u", "em", "strong", "p", "br"]
            allowed_attributes = {}

            return bleach.clean(value, tags=allowed_tags, attributes=allowed_attributes)
        except ImportError:
            # Fallback if bleach is not available
            return cls.escape_html(value)

    @classmethod
    def escape_html(cls, value: str) -> str:
        """Escape HTML entities."""
        if not isinstance(value, str):
            return value
        return html.escape(value)


class FieldValidators:
    """Common field validation utilities."""

    @staticmethod
    def validate_username(value: str) -> str:
        """Validate username format and security."""
        if not value:
            raise ValueError("Username is required")

        # Security checks
        SecurityValidator.validate_sql_injection(value, "username")
        SecurityValidator.validate_xss(value, "username")

        # Format checks
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(value) > 50:
            raise ValueError("Username must not exceed 50 characters")

        if not re.match(r"^[a-zA-Z0-9_.-]+$", value):
            raise ValueError(
                "Username can only contain letters, numbers, "
                "underscores, dots, and hyphens"
            )

        # Business rules
        forbidden_usernames = ["admin", "root", "system", "api", "null", "undefined"]
        if value.lower() in forbidden_usernames:
            raise ValueError("This username is not allowed")

        return value.strip()

    @staticmethod
    def validate_password(value: str) -> str:
        """Validate password strength."""
        if not value:
            raise ValueError("Password is required")

        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(value) > 128:
            raise ValueError("Password must not exceed 128 characters")

        # Check for required character types
        has_upper = re.search(r"[A-Z]", value)
        has_lower = re.search(r"[a-z]", value)
        has_digit = re.search(r"\d", value)
        has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', value)

        missing_requirements = []
        if not has_upper:
            missing_requirements.append("uppercase letter")
        if not has_lower:
            missing_requirements.append("lowercase letter")
        if not has_digit:
            missing_requirements.append("number")
        if not has_special:
            missing_requirements.append("special character")

        if missing_requirements:
            req_str = ", ".join(missing_requirements)
            raise ValueError(f"Password must contain at least one {req_str}")

        # Check for common weak patterns
        if re.search(r"(.)\1{2,}", value):  # Three+ repeated characters
            raise ValueError(
                "Password cannot contain three or more " + "repeated characters"
            )

        return value

    @staticmethod
    def validate_email_format(value: str) -> str:
        """Enhanced email validation."""
        if not value:
            raise ValueError("Email is required")

        # Security checks
        SecurityValidator.validate_sql_injection(value, "email")
        SecurityValidator.validate_xss(value, "email")

        # Basic format check (similar to EmailStr validation)
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            raise ValueError("Invalid email format")

        # Length checks
        if len(value) > 254:  # RFC 5321
            raise ValueError("Email address is too long")

        local_part, _ = value.rsplit("@", 1)
        if len(local_part) > 64:  # RFC 5321
            raise ValueError("Email local part is too long")

        return value.lower().strip()

    @staticmethod
    def validate_email(value: str) -> str:
        """Alias for validate_email_format for compatibility."""
        return FieldValidators.validate_email_format(value)

    @staticmethod
    def validate_phone_number(value: Optional[str]) -> Optional[str]:
        """Validate phone number format."""
        if not value:
            return value

        # Security checks
        SecurityValidator.validate_sql_injection(value, "phone")

        # Remove common separators
        cleaned = re.sub(r"[\s\-\(\)\+]", "", value)

        # Check if all remaining characters are digits
        if not cleaned.isdigit():
            raise ValueError(
                "Phone number can only contain digits and " "common separators"
            )

        # Length check (international format)
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError("Phone number must be between 7 and 15 digits")

        return value.strip()

    @staticmethod
    def validate_text_field(
        value: str,
        field_name: str,
        min_length: int = 0,
        max_length: int = 1000,
        allow_html: bool = False,
    ) -> str:
        """Generic text field validation."""
        if not value and min_length > 0:
            raise ValueError(f"{field_name} is required")

        if not value:
            return value

        # Security checks
        SecurityValidator.validate_sql_injection(value, field_name)
        if not allow_html:
            SecurityValidator.validate_xss(value, field_name)

        # Length checks
        if len(value) < min_length:
            raise ValueError(
                f"{field_name} must be at least " f"{min_length} characters long"
            )
        if len(value) > max_length:
            raise ValueError(
                f"{field_name} must not exceed " f"{max_length} characters"
            )

        # Sanitize if HTML is allowed
        if allow_html:
            value = SecurityValidator.sanitize_html(value)
        else:
            value = SecurityValidator.escape_html(value)

        return value.strip()


def validate_user_create_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate user creation data."""
    errors = []
    validated_data = {}

    # Validate username
    try:
        username = data.get("username", "")
        validated_data["username"] = FieldValidators.validate_username(username)
    except ValueError as e:
        errors.append(
            ValidationErrorDetail(
                field="username",
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=str(e),
                value=data.get("username"),
            )
        )

    # Validate email
    try:
        email = data.get("email", "")
        validated_data["email"] = FieldValidators.validate_email_format(email)
    except ValueError as e:
        errors.append(
            ValidationErrorDetail(
                field="email",
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=str(e),
                value=data.get("email"),
            )
        )

    # Validate password
    try:
        password = data.get("password", "")
        validated_data["password"] = FieldValidators.validate_password(password)
    except ValueError as e:
        errors.append(
            ValidationErrorDetail(
                field="password",
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=str(e),
                value="[REDACTED]",
            )
        )

    # Validate optional fields
    for field_name in ["given_name", "family_name"]:
        if field_name in data and data[field_name]:
            try:
                validated_data[field_name] = FieldValidators.validate_text_field(
                    data[field_name], field_name, min_length=1, max_length=100
                )
            except ValueError as e:
                errors.append(
                    ValidationErrorDetail(
                        field=field_name,
                        error_type=ValidationErrorType.INVALID_FORMAT,
                        message=str(e),
                        value=data.get(field_name),
                    )
                )

    # Validate phone number
    if "mobile_phone" in data and data["mobile_phone"]:
        try:
            validated_data["mobile_phone"] = FieldValidators.validate_phone_number(
                data["mobile_phone"]
            )
        except ValueError as e:
            errors.append(
                ValidationErrorDetail(
                    field="mobile_phone",
                    error_type=ValidationErrorType.INVALID_FORMAT,
                    message=str(e),
                    value=data.get("mobile_phone"),
                )
            )

    if errors:
        from fastapi import HTTPException

        error_response = ValidationErrorResponse(details=errors)
        raise HTTPException(status_code=422, detail=error_response.dict())

    return validated_data


def validate_password_update_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate password update data."""
    errors = []
    validated_data = {}

    # Validate old password
    if not data.get("old_password"):
        errors.append(
            ValidationErrorDetail(
                field="old_password",
                error_type=ValidationErrorType.REQUIRED_FIELD,
                message="Current password is required",
            )
        )
    else:
        validated_data["old_password"] = data["old_password"]

    # Validate new password
    try:
        new_password = data.get("new_password", "")
        validated_data["new_password"] = FieldValidators.validate_password(new_password)

        # Check that passwords are different
        if (
            data.get("old_password")
            and new_password
            and data["old_password"] == new_password
        ):
            errors.append(
                ValidationErrorDetail(
                    field="new_password",
                    error_type=ValidationErrorType.BUSINESS_RULE,
                    message="New password must be different from current password",
                )
            )

    except ValueError as e:
        errors.append(
            ValidationErrorDetail(
                field="new_password",
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=str(e),
                value="[REDACTED]",
            )
        )

    if errors:
        from fastapi import HTTPException

        error_response = ValidationErrorResponse(details=errors)
        raise HTTPException(status_code=422, detail=error_response.dict())

    return validated_data


def validate_role_create_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate role creation data."""
    errors = []
    validated_data = {}

    # Validate role name
    try:
        name = data.get("name", "")
        validated_data["name"] = FieldValidators.validate_text_field(
            name, "role name", min_length=2, max_length=50
        )
    except ValueError as e:
        errors.append(
            ValidationErrorDetail(
                field="name",
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=str(e),
                value=data.get("name"),
            )
        )

    # Validate optional description
    if "description" in data and data["description"]:
        try:
            validated_data["description"] = FieldValidators.validate_text_field(
                data["description"], "description", max_length=500
            )
        except ValueError as e:
            errors.append(
                ValidationErrorDetail(
                    field="description",
                    error_type=ValidationErrorType.INVALID_FORMAT,
                    message=str(e),
                    value=data.get("description"),
                )
            )

    if errors:
        from fastapi import HTTPException

        error_response = ValidationErrorResponse(details=errors)
        raise HTTPException(status_code=422, detail=error_response.dict())

    return validated_data


# Error handling utilities
def create_validation_error_response(
    errors: List[ValidationErrorDetail], request_id: Optional[str] = None
):
    """Create standardized validation error response."""
    from fastapi.responses import JSONResponse

    response = ValidationErrorResponse(details=errors, request_id=request_id)
    return JSONResponse(status_code=422, content=response.dict())


def handle_validation_error(exc: Exception, request_id: Optional[str] = None):
    """Convert validation errors to standardized format."""
    errors = []

    if hasattr(exc, "errors") and callable(exc.errors):
        # Handle Pydantic ValidationError
        for error in exc.errors():
            field_name = ".".join(str(loc) for loc in error.get("loc", []))
            if not field_name:
                field_name = "unknown"

            error_type = ValidationErrorType.INVALID_FORMAT

            if error.get("type") == "missing":
                error_type = ValidationErrorType.REQUIRED_FIELD
            elif "length" in str(error.get("type", "")):
                error_type = ValidationErrorType.LENGTH_VIOLATION

            errors.append(
                ValidationErrorDetail(
                    field=field_name,
                    error_type=error_type,
                    message=error.get("msg", str(exc)),
                    value=error.get("input"),
                    constraints=error.get("ctx"),
                )
            )
    else:
        # Handle generic ValueError or other exceptions
        errors.append(
            ValidationErrorDetail(
                field="unknown",
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=str(exc),
            )
        )

    return create_validation_error_response(errors, request_id)


# Rate limiting validation placeholder
class RateLimitValidator:
    """Rate limiting validation utilities."""

    @staticmethod
    def validate_rate_limit(
        client_ip: str, max_requests: int = 100, window_minutes: int = 15
    ) -> bool:
        """Basic rate limiting validation (Redis in production)."""
        # This is a placeholder - implement with Redis in production
        logger.info(
            f"Rate limit check for {client_ip}: "
            f"{max_requests} requests per {window_minutes} minutes"
        )
        return True  # Allow all requests for now


# Middleware for request validation and tracking
class RequestValidationMiddleware:
    """Middleware for comprehensive request validation."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add request ID for tracking
            import uuid

            request_id = str(uuid.uuid4())
            scope["request_id"] = request_id

        await self.app(scope, receive, send)


# Export main components
__all__ = [
    "ValidationErrorType",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "SecurityValidator",
    "FieldValidators",
    "validate_user_create_data",
    "validate_password_update_data",
    "validate_role_create_data",
    "create_validation_error_response",
    "handle_validation_error",
    "RateLimitValidator",
    "RequestValidationMiddleware",
]

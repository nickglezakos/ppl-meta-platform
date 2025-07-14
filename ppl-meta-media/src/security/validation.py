"""
Input Validation Service for PPL Meta Media Service.
Provides comprehensive input sanitization and SQL injection prevention.
"""

import html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class InputValidationService:
    """Comprehensive input validation and sanitization service."""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(--|\#|\/\*|\*\/)",
        r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT|ONLOAD|ONERROR)\b)",
        r"(\<\s*script|\<\s*\/\s*script\>)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"(\<\s*script.*?\>)",
        r"(\<\s*\/\s*script\s*\>)",
        r"(javascript\s*:)",
        r"(on\w+\s*=)",
        r"(\<\s*iframe|\<\s*object|\<\s*embed)",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.\/|\.\.\\)",
        r"(%2e%2e%2f|%2e%2e%5c)",
        r"(%252e%252e%252f|%252e%252e%255c)",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"(\||&|;|\$\(|\`)",
        r"(\b(rm|del|format|mkdir|rmdir|copy|move|cat|type)\b)",
        r"(\b(wget|curl|nc|netcat|telnet|ssh)\b)",
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize input validation service.

        Args:
            strict_mode: Enable strict validation mode
        """
        self.strict_mode = strict_mode

    def sanitize_string(self, input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize string input by removing/escaping dangerous characters.

        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            HTTPException: If input fails validation
        """
        if not isinstance(input_str, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Input must be a string"
            )

        # Length check
        if len(input_str) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input too long (max {max_length} characters)",
            )

        # HTML escape to prevent XSS
        sanitized = html.escape(input_str, quote=True)

        # Additional XSS protection
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                if self.strict_mode:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Input contains potentially dangerous content",
                    )
                else:
                    # Remove dangerous content
                    sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        return sanitized.strip()

    def validate_sql_injection(self, input_str: str) -> bool:
        """
        Check for SQL injection patterns.

        Args:
            input_str: String to check

        Returns:
            True if string is safe from SQL injection

        Raises:
            HTTPException: If SQL injection detected
        """
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Input contains SQL injection patterns",
                )
        return True

    def validate_path_traversal(self, path_str: str) -> bool:
        """
        Check for path traversal attacks.

        Args:
            path_str: Path string to check

        Returns:
            True if path is safe

        Raises:
            HTTPException: If path traversal detected
        """
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path_str, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Input contains path traversal patterns",
                )
        return True

    def validate_command_injection(self, input_str: str) -> bool:
        """
        Check for command injection patterns.

        Args:
            input_str: String to check

        Returns:
            True if string is safe from command injection

        Raises:
            HTTPException: If command injection detected
        """
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Input contains command injection patterns",
                )
        return True

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = filename.split("/")[-1].split("\\")[-1]

        # Remove or replace dangerous characters
        filename = re.sub(r"[<>:\"/\\|?*]", "_", filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip(". ")

        # Ensure it's not empty
        if not filename:
            filename = "unnamed_file"

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            max_name_length = 250 - len(ext)
            filename = name[:max_name_length] + ("." + ext if ext else "")

        return filename

    def validate_user_id(self, user_id: str) -> str:
        """
        Validate and sanitize user ID.

        Args:
            user_id: User ID to validate

        Returns:
            Validated user ID

        Raises:
            HTTPException: If user ID is invalid
        """
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required"
            )

        # Check format (alphanumeric, hyphens, underscores only)
        if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID contains invalid characters",
            )

        # Length check
        if len(user_id) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID too long (max 50 characters)",
            )

        return user_id

    def validate_media_id(self, media_id: str) -> str:
        """
        Validate media ID format.

        Args:
            media_id: Media ID to validate

        Returns:
            Validated media ID

        Raises:
            HTTPException: If media ID is invalid
        """
        if not media_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Media ID is required"
            )

        # Check format (alphanumeric, hyphens only)
        if not re.match(r"^[a-zA-Z0-9-]+$", media_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Media ID contains invalid characters",
            )

        return media_id

    def validate_collection_name(self, name: str) -> str:
        """
        Validate and sanitize collection name.

        Args:
            name: Collection name to validate

        Returns:
            Sanitized collection name

        Raises:
            HTTPException: If name is invalid
        """
        if not name or not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Collection name is required",
            )

        # Sanitize and validate
        sanitized_name = self.sanitize_string(name, max_length=100)

        # Additional validation for collection names
        if len(sanitized_name.strip()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Collection name too short",
            )

        return sanitized_name

    def validate_search_query(self, query: str) -> str:
        """
        Validate and sanitize search query.

        Args:
            query: Search query to validate

        Returns:
            Sanitized search query

        Raises:
            HTTPException: If query is invalid
        """
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query is required",
            )

        # Check SQL injection patterns
        self.validate_sql_injection(query)

        # Sanitize
        sanitized_query = self.sanitize_string(query, max_length=500)

        # Remove excessive whitespace
        sanitized_query = " ".join(sanitized_query.split())

        return sanitized_query

    def validate_request_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize request body.

        Args:
            body: Request body dictionary

        Returns:
            Sanitized request body
        """
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a JSON object",
            )

        sanitized_body = {}

        for key, value in body.items():
            # Validate key
            sanitized_key = self.sanitize_string(str(key), max_length=100)

            # Sanitize value based on type
            if isinstance(value, str):
                sanitized_value = self.sanitize_string(value)
            elif isinstance(value, (int, float, bool)):
                sanitized_value = value
            elif isinstance(value, list):
                sanitized_value = [
                    self.sanitize_string(str(item)) if isinstance(item, str) else item
                    for item in value[:100]  # Limit list size
                ]
            elif isinstance(value, dict):
                # Recursive validation for nested objects
                sanitized_value = self.validate_request_body(value)
            else:
                # Skip unknown types
                continue

            sanitized_body[sanitized_key] = sanitized_value

        return sanitized_body

    def validate_url_parameter(self, param: str, param_name: str) -> str:
        """
        Validate URL parameter.

        Args:
            param: Parameter value
            param_name: Parameter name for error messages

        Returns:
            Validated parameter

        Raises:
            HTTPException: If parameter is invalid
        """
        if not param:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parameter '{param_name}' is required",
            )

        # URL decode
        try:
            decoded_param = quote(param, safe="")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL encoding in parameter '{param_name}'",
            )

        # Check for path traversal
        self.validate_path_traversal(param)

        # Check for command injection
        self.validate_command_injection(param)

        return param

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of validation capabilities.

        Returns:
            Dictionary with validation features summary
        """
        return {
            "features": {
                "sql_injection_protection": True,
                "xss_protection": True,
                "path_traversal_protection": True,
                "command_injection_protection": True,
                "input_sanitization": True,
                "filename_sanitization": True,
            },
            "patterns_detected": {
                "sql_injection": len(self.SQL_INJECTION_PATTERNS),
                "xss": len(self.XSS_PATTERNS),
                "path_traversal": len(self.PATH_TRAVERSAL_PATTERNS),
                "command_injection": len(self.COMMAND_INJECTION_PATTERNS),
            },
            "strict_mode": self.strict_mode,
        }

"""
Standardized structured logging configuration for PPL Meta Platform.

This module provides a consistent logging interface across all microservices
with support for JSON structured logging, configurable log levels, and
uniform format for log aggregation.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.getenv("APP_NAME", "unknown-service"),
            "version": os.getenv("APP_VERSION", "unknown-version"),
            "environment": os.getenv("ENVIRONMENT", "development"),
        }

        # Add extra fields if present
        if hasattr(record, "extra") and record.extra:
            log_entry.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""

    # Color codes for different log levels
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        formatted = (
            f"{color}[{record.levelname:8}]{reset} "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} "
            f"{record.name}: {record.getMessage()}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: str = "console",
    log_file: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> structlog.BoundLogger:
    """
    Set up standardized logging configuration.

    Args:
        service_name: Name of the service (e.g., "ppl-meta-gateway")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" or "console")
        log_file: Optional file path for logging to file
        extra_context: Additional context to include in all log messages

    Returns:
        Configured structlog logger instance
    """

    # Normalize log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    handlers.append(console_handler)

    # File handler (if specified)
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for files
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        format="%(message)s",  # Formatter handles the actual format
        force=True,  # Override any existing configuration
    )

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add service context processor
    def add_service_context(_logger, _method_name, event_dict):
        """Add service-specific context to all log messages."""
        event_dict.update(
            {
                "service": service_name,
                "version": os.getenv("APP_VERSION", "unknown"),
                "environment": os.getenv("ENVIRONMENT", "development"),
            }
        )
        if extra_context:
            event_dict.update(extra_context)
        return event_dict

    processors.insert(0, add_service_context)

    # Configure final renderer based on format
    if log_format.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create and return logger for the service
    logger = structlog.get_logger(service_name)

    # Log setup completion
    logger.info(
        "Logging configured",
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
        handlers_count=len(handlers),
    )

    return logger


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Common log level constants
class LogLevel:
    """Standard log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Common log format constants
class LogFormat:
    """Standard log formats."""

    JSON = "json"
    CONSOLE = "console"


def log_request(
    logger: structlog.BoundLogger,
    request_id: str,
    method: str,
    path: str,
    user_id: Optional[str] = None,
    **kwargs,
) -> None:
    """
    Log HTTP request in standard format.

    Args:
        logger: Logger instance
        request_id: Unique request identifier
        method: HTTP method
        path: Request path
        user_id: Optional user identifier
        **kwargs: Additional context
    """
    logger.info(
        "HTTP request",
        request_id=request_id,
        method=method,
        path=path,
        user_id=user_id,
        **kwargs,
    )


def log_response(
    logger: structlog.BoundLogger,
    request_id: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
) -> None:
    """
    Log HTTP response in standard format.

    Args:
        logger: Logger instance
        request_id: Unique request identifier
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    logger.info(
        "HTTP response",
        request_id=request_id,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> None:
    """
    Log error in standard format.

    Args:
        logger: Logger instance
        error: Exception instance
        context: Additional error context
        **kwargs: Additional fields
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs,
    }

    if context:
        error_context.update(context)

    logger.error("Error occurred", **error_context, exc_info=error)


def log_database_operation(
    logger: structlog.BoundLogger,
    operation: str,
    table: str,
    duration_ms: Optional[float] = None,
    affected_rows: Optional[int] = None,
    **kwargs,
) -> None:
    """
    Log database operation in standard format.

    Args:
        logger: Logger instance
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration_ms: Operation duration in milliseconds
        affected_rows: Number of affected rows
        **kwargs: Additional context
    """
    log_data = {"operation": operation, "table": table, **kwargs}

    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    if affected_rows is not None:
        log_data["affected_rows"] = affected_rows

    logger.info("Database operation", **log_data)


def log_external_api_call(
    logger: structlog.BoundLogger,
    service: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
) -> None:
    """
    Log external API call in standard format.

    Args:
        logger: Logger instance
        service: External service name
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    logger.info(
        "External API call",
        service=service,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )

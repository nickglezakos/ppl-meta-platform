"""
Local logging stub for the gateway service.
"""

import logging
from typing import Optional

import structlog


def setup_logging(
    service_name: str = "gateway",
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """Setup structured logging."""
    # Configure basic logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None):
    """Get a configured logger instance."""
    return structlog.get_logger(name)

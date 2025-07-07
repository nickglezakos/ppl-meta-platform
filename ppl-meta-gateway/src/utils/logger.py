"""
Logging utilities for the gateway service.
"""

import os
import sys

# Add the parent directory to Python path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from config import settings

from shared.logging import get_logger as shared_get_logger
from shared.logging import setup_logging as shared_setup_logging


def setup_logging() -> None:
    """Configure structured logging using shared logging system."""
    shared_setup_logging(
        service_name="ppl-meta-gateway",
        log_level=settings.LOG_LEVEL.upper(),
        log_format=settings.LOG_FORMAT.lower(),
        log_file="/app/logs/gateway-service.log" if os.path.exists("/app") else None,
    )


def get_logger(name: str = None):
    """Get a configured logger instance."""
    return shared_get_logger(name)

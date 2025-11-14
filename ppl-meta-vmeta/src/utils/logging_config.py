"""
Structured Logging Configuration

Centralized logging setup for batch processing with correlation IDs,
context tracking, and log aggregation support.

Author: PPL Meta Platform
Date: November 13, 2025
Version: 1.0.0
"""

import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager
from contextvars import ContextVar
import traceback

# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    'correlation_id', default=None
)
batch_uuid_var: ContextVar[Optional[str]] = ContextVar(
    'batch_uuid', default=None
)
collection_id_var: ContextVar[Optional[str]] = ContextVar(
    'collection_id', default=None
)
session_uuid_var: ContextVar[Optional[str]] = ContextVar(
    'session_uuid', default=None
)


# ============================================================================
# JSON Formatter for Structured Logging
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Outputs logs in JSON format for easy parsing by ELK, Loki, etc.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "vmeta",
            "component": "batch_processing"
        }
        
        # Add correlation IDs if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        batch_uuid = batch_uuid_var.get()
        if batch_uuid:
            log_data["batch_uuid"] = batch_uuid
        
        collection_id = collection_id_var.get()
        if collection_id:
            log_data["collection_id"] = collection_id
        
        session_uuid = session_uuid_var.get()
        if session_uuid:
            log_data["session_uuid"] = session_uuid
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add standard fields
        log_data.update({
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
            "process": record.process,
            "thread": record.thread
        })
        
        return json.dumps(log_data)


# ============================================================================
# Human-Readable Formatter
# ============================================================================

class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter with colors for console output.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Build context string
        context_parts = []
        
        correlation_id = correlation_id_var.get()
        if correlation_id:
            context_parts.append(f"corr_id={correlation_id[:8]}")
        
        batch_uuid = batch_uuid_var.get()
        if batch_uuid:
            context_parts.append(f"batch={batch_uuid[:8]}")
        
        collection_id = collection_id_var.get()
        if collection_id:
            context_parts.append(f"coll={collection_id}")
        
        session_uuid = session_uuid_var.get()
        if session_uuid:
            context_parts.append(f"sess={session_uuid[:8]}")
        
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        # Colorize level
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        
        # Build log line
        log_line = (
            f"{level_color}{timestamp}{reset_color} "
            f"{level_color}[{record.levelname}]{reset_color} "
            f"{record.name}{context_str} - "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_line += f"\n{exc_text}"
        
        return log_line


# ============================================================================
# Logging Configuration
# ============================================================================

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_output: bool = False,
    include_correlation_ids: bool = True
):
    """
    Configure structured logging for batch processing.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
        json_output: Use JSON formatter (for log aggregation)
        include_correlation_ids: Include correlation IDs in logs
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    if json_output:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        
        # Always use JSON for file output
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Batch processing loggers
    logging.getLogger('batch_monitor').setLevel(level.upper())
    logging.getLogger('hybrid_trigger').setLevel(level.upper())
    logging.getLogger('pipeline_executor').setLevel(level.upper())
    logging.getLogger('camera_event_integration').setLevel(level.upper())
    
    logging.info(
        f"Logging configured: level={level}, "
        f"json={json_output}, file={log_file}"
    )


# ============================================================================
# Context Managers
# ============================================================================

@contextmanager
def batch_context(
    batch_uuid: str,
    collection_id: str,
    correlation_id: Optional[str] = None
):
    """
    Context manager for batch processing logging.
    
    Usage:
        with batch_context(batch_uuid, collection_id):
            logger.info("Processing batch")
            # All logs will include batch_uuid and collection_id
    """
    # Generate correlation ID if not provided
    if correlation_id is None:
        import uuid
        correlation_id = str(uuid.uuid4())
    
    # Set context variables
    correlation_token = correlation_id_var.set(correlation_id)
    batch_token = batch_uuid_var.set(batch_uuid)
    collection_token = collection_id_var.set(collection_id)
    
    try:
        yield
    finally:
        # Reset context variables
        correlation_id_var.reset(correlation_token)
        batch_uuid_var.reset(batch_token)
        collection_id_var.reset(collection_token)


@contextmanager
def session_context(session_uuid: str):
    """
    Context manager for tracking session logging.
    
    Usage:
        with session_context(session_uuid):
            logger.info("Processing session")
    """
    session_token = session_uuid_var.set(session_uuid)
    
    try:
        yield
    finally:
        session_uuid_var.reset(session_token)


@contextmanager
def correlation_context(correlation_id: str):
    """
    Context manager for correlation ID tracking.
    
    Usage:
        with correlation_context(correlation_id):
            logger.info("Processing request")
    """
    token = correlation_id_var.set(correlation_id)
    
    try:
        yield
    finally:
        correlation_id_var.reset(token)


# ============================================================================
# Structured Logger Wrapper
# ============================================================================

class StructuredLogger:
    """
    Wrapper around logging.Logger with structured logging support.
    
    Automatically includes correlation IDs and context information.
    """
    
    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
    
    def _add_extra_fields(self, extra: Optional[Dict] = None) -> Dict:
        """Add correlation IDs to extra fields."""
        fields = extra or {}
        
        correlation_id = correlation_id_var.get()
        if correlation_id:
            fields['correlation_id'] = correlation_id
        
        batch_uuid = batch_uuid_var.get()
        if batch_uuid:
            fields['batch_uuid'] = batch_uuid
        
        collection_id = collection_id_var.get()
        if collection_id:
            fields['collection_id'] = collection_id
        
        session_uuid = session_uuid_var.get()
        if session_uuid:
            fields['session_uuid'] = session_uuid
        
        return {'extra_fields': fields}
    
    def debug(self, msg: str, **extra):
        """Log debug message."""
        self.logger.debug(msg, extra=self._add_extra_fields(extra))
    
    def info(self, msg: str, **extra):
        """Log info message."""
        self.logger.info(msg, extra=self._add_extra_fields(extra))
    
    def warning(self, msg: str, **extra):
        """Log warning message."""
        self.logger.warning(msg, extra=self._add_extra_fields(extra))
    
    def error(self, msg: str, **extra):
        """Log error message."""
        self.logger.error(msg, extra=self._add_extra_fields(extra))
    
    def critical(self, msg: str, **extra):
        """Log critical message."""
        self.logger.critical(msg, extra=self._add_extra_fields(extra))
    
    def exception(self, msg: str, **extra):
        """Log exception with traceback."""
        self.logger.exception(msg, extra=self._add_extra_fields(extra))


def get_logger(name: str) -> StructuredLogger:
    """
    Get structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


# ============================================================================
# Log Aggregation Configuration
# ============================================================================

# Elasticsearch/Logstash configuration
LOGSTASH_CONFIG = {
    "host": "localhost",
    "port": 5000,
    "version": 1
}

# Loki configuration
LOKI_CONFIG = {
    "url": "http://localhost:3100",
    "labels": {
        "service": "vmeta",
        "component": "batch_processing"
    }
}


def configure_logstash_handler(host: str, port: int):
    """
    Configure Logstash handler for log aggregation.
    
    Note: Requires python-logstash package
    """
    try:
        import logstash
        
        logger = logging.getLogger()
        logstash_handler = logstash.TCPLogstashHandler(
            host=host,
            port=port,
            version=1
        )
        logger.addHandler(logstash_handler)
        
        logging.info(f"Logstash handler configured: {host}:{port}")
    except ImportError:
        logging.warning(
            "python-logstash not installed, skipping Logstash handler"
        )


def configure_loki_handler(url: str, labels: Dict[str, str]):
    """
    Configure Loki handler for log aggregation.
    
    Note: Requires python-logging-loki package
    """
    try:
        from logging_loki import LokiHandler
        
        logger = logging.getLogger()
        loki_handler = LokiHandler(
            url=url,
            tags=labels,
            version="1"
        )
        logger.addHandler(loki_handler)
        
        logging.info(f"Loki handler configured: {url}")
    except ImportError:
        logging.warning(
            "python-logging-loki not installed, skipping Loki handler"
        )


# ============================================================================
# Performance Logging
# ============================================================================

class PerformanceTimer:
    """Context manager for logging operation duration."""
    
    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        level: str = "INFO"
    ):
        """
        Initialize performance timer.
        
        Args:
            logger: Structured logger instance
            operation: Operation description
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        """Start timer."""
        import time
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and log duration."""
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            # Success
            log_func = getattr(self.logger, self.level.lower())
            log_func(
                f"{self.operation} completed in {duration:.2f}s",
                duration_seconds=duration
            )
        else:
            # Failure
            self.logger.error(
                f"{self.operation} failed after {duration:.2f}s: {exc_val}",
                duration_seconds=duration,
                error_type=exc_type.__name__
            )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Setup logging
    setup_logging(
        level="DEBUG",
        log_file="batch_processing.log",
        json_output=False
    )
    
    # Get logger
    logger = get_logger(__name__)
    
    # Example 1: Basic logging
    logger.info("Starting batch processing")
    
    # Example 2: With batch context
    with batch_context(
        batch_uuid="f7a9e3b2-1234-5678-90ab-cdef12345678",
        collection_id="usb_camera_0"
    ):
        logger.info("Processing batch")
        logger.debug("Video count: 5")
        
        # Nested session context
        with session_context("a1b2c3d4-5678-90ab-cdef-123456789abc"):
            logger.info("Creating tracking session")
    
    # Example 3: Performance timing
    with PerformanceTimer(logger, "Database query"):
        import time
        time.sleep(0.1)
    
    # Example 4: Error logging
    try:
        raise ValueError("Test error")
    except Exception:
        logger.exception("Failed to process batch")

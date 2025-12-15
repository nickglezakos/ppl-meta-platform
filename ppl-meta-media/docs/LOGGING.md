# PPL Meta Media Service - Logging System

## Overview

The PPL Meta Media Service uses a robust, structured logging system built on `structlog` that provides:

- **Structured JSON logging** for production environments
- **Human-readable console output** for development
- **Automatic request/response tracking** with correlation IDs
- **Performance monitoring** with timing metrics
- **Context-aware logging** with automatic metadata injection
- **Specialized loggers** for media-specific operations

## Architecture

### Components

1. **Shared Logging Module** (`/shared/logging/structured_logger.py`)
   - Base structured logging configuration
   - Standard log formatters (JSON and console)
   - Common logging utilities

2. **Media Service Logger** (`src/logger.py`)
   - Media-specific logging utilities
   - Specialized operation loggers
   - Context managers and decorators

3. **Logging Middleware** (`src/middleware/logging.py`)
   - Automatic request/response logging
   - Performance tracking
   - Error capture

## Usage

### Basic Logging

```python
from src.logger import logger

# Simple logging
logger.info("Operation completed")
logger.warning("Slow operation detected", duration_ms=1500)
logger.error("Operation failed", error="Connection timeout")

# With structured context
logger.info(
    "Media uploaded",
    media_id="123",
    filename="video.mp4",
    size_mb=150.5,
    user_id="user_456"
)
```

### Media-Specific Logging

```python
from src.logger import media_logger

# Log media upload
media_logger.log_media_upload(
    filename="vacation_video.mp4",
    file_size=157286400,  # bytes
    content_type="video/mp4",
    user_id="user_123",
    collection_id="col_456",
    duration_ms=3420.5,
    success=True
)

# Log media processing
media_logger.log_media_processing(
    media_id="media_789",
    processing_type="thumbnail_generation",
    duration_ms=245.3,
    input_format="mp4",
    output_format="jpg",
    success=True,
    thumbnail_count=5
)

# Log storage operations
media_logger.log_storage_operation(
    operation="write",
    storage_type="s3",
    path="s3://bucket/media/video.mp4",
    size_bytes=157286400,
    duration_ms=2341.2,
    success=True
)

# Log face detection
media_logger.log_face_detection(
    media_id="media_123",
    faces_detected=3,
    duration_ms=1234.5,
    model="dlib_cnn",
    success=True,
    confidence_scores=[0.98, 0.95, 0.89]
)

# Log trigger evaluation
media_logger.log_trigger_evaluation(
    trigger_id="trigger_456",
    trigger_type="demographic",
    result=True,
    conditions_met=3,
    total_conditions=4,
    duration_ms=15.2
)

# Log ETL operations
media_logger.log_etl_operation(
    job_id="job_789",
    operation="sync_playlist",
    device_id="device_123",
    video_list_id="vlist_456",
    status="success",
    duration_ms=5421.8,
    items_processed=25
)
```

### Using Context Managers

```python
from src.logger import media_logger

# Automatic timing and error handling
with media_logger.operation_context("video_transcoding", media_id="123"):
    # Perform transcoding operation
    transcode_video(media_id="123")
    # Automatically logs start, completion, duration, and any errors
```

### Using Decorators

```python
from src.logger import log_function_call

@log_function_call("thumbnail_generation")
async def generate_thumbnail(media_id: str):
    # Function logic
    pass
    # Automatically logs function entry, exit, duration, and errors
```

### FastAPI Request Logging

The logging middleware automatically captures all requests:

```python
# In main.py
from src.middleware.logging import LoggingMiddleware, PerformanceLoggingMiddleware

app.add_middleware(LoggingMiddleware, exclude_paths=["/health", "/metrics"])
app.add_middleware(PerformanceLoggingMiddleware, slow_threshold_ms=1000.0)
```

All requests will include:
- Request ID (correlation ID)
- Method, path, query parameters
- Client IP and user agent
- Request/response size
- Duration in milliseconds
- Status code

### Request Context

```python
from fastapi import Request
from src.logger import get_request_context, logger

async def my_endpoint(request: Request):
    # Get request context
    context = get_request_context(request)
    
    # Use in logging
    logger.info("Processing request", **context)
```

## Configuration

### Environment Variables

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format (json, console)
LOG_FORMAT=json

# Log file path (optional)
LOG_FILE=/app/logs/media-service.log
```

### In Code

```python
from shared.logging import setup_logging

logger = setup_logging(
    service_name="ppl-meta-media",
    log_level="INFO",
    log_format="json",
    log_file="/app/logs/media-service.log",
    extra_context={"environment": "production"}
)
```

## Log Output Examples

### Console Format (Development)

```
[INFO    ] 2024-12-15 10:30:45 ppl-meta-media: Media upload completed
    filename='video.mp4' 
    file_size_mb=150.5 
    content_type='video/mp4' 
    duration_ms=3420.5 
    success=True
```

### JSON Format (Production)

```json
{
  "timestamp": "2024-12-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "ppl-meta-media",
  "message": "Media upload completed",
  "service": "ppl-meta-media",
  "version": "1.0.0",
  "environment": "production",
  "operation": "media_upload",
  "filename": "video.mp4",
  "file_size_bytes": 157286400,
  "file_size_mb": 150.5,
  "content_type": "video/mp4",
  "user_id": "user_123",
  "collection_id": "col_456",
  "duration_ms": 3420.5,
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Best Practices

### 1. Use Structured Context

**Good:**
```python
logger.info("User uploaded media", user_id="123", media_id="456", size_mb=150.5)
```

**Avoid:**
```python
logger.info(f"User 123 uploaded media 456 with size 150.5 MB")
```

### 2. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: Normal operation events (uploads, processing complete)
- **WARNING**: Unexpected but handled situations (slow requests, retries)
- **ERROR**: Failures that require attention
- **CRITICAL**: System-level failures

### 3. Include Context

Always include relevant identifiers:
```python
logger.error(
    "Failed to process media",
    media_id="123",
    user_id="456",
    error="Transcoding timeout",
    duration_ms=30000
)
```

### 4. Log Performance Metrics

```python
start_time = time.time()
result = perform_operation()
duration_ms = (time.time() - start_time) * 1000

logger.info("Operation completed", operation="transcode", duration_ms=duration_ms)
```

### 5. Use Media Logger for Domain Operations

```python
# Instead of generic logging
logger.info("Upload complete")

# Use specialized logger
media_logger.log_media_upload(filename="...", file_size=..., success=True)
```

## Log Aggregation

### Viewing Logs

**Local Development:**
```bash
# Tail log file
tail -f logs/ppl-meta-media.log

# Search logs
grep "ERROR" logs/ppl-meta-media.log

# Parse JSON logs with jq
tail -f logs/ppl-meta-media.log | jq '.'
```

**Production:**

Logs are structured JSON and can be ingested by:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- CloudWatch Logs
- Datadog
- Grafana Loki

### Log Rotation

Logs automatically rotate with the `RotatingFileHandler`:
- Max file size: 10 MB
- Backup count: 5 files
- Old logs are automatically compressed

## Troubleshooting

### Logs Not Appearing

1. Check log level configuration
2. Verify log file path is writable
3. Check for middleware registration in main.py

### Missing Request Context

Ensure the logging middleware is registered:
```python
app.add_middleware(LoggingMiddleware)
```

### Performance Impact

- JSON logging has minimal overhead (~1-2ms per log)
- Use DEBUG level sparingly in production
- Exclude health check endpoints from logging
- Consider async log handlers for high-throughput scenarios

## Migration Guide

### From Basic Logging

**Before:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Upload complete")
```

**After:**
```python
from src.logger import logger
logger.info("Upload complete", media_id="123", success=True)
```

### From Print Statements

**Before:**
```python
print(f"Processing media {media_id}")
```

**After:**
```python
logger.info("Processing media", media_id=media_id, operation="process")
```

## Additional Resources

- [structlog Documentation](https://www.structlog.org/)
- [Shared Logging Module](/shared/logging/)
- [FastAPI Middleware Guide](https://fastapi.tiangolo.com/tutorial/middleware/)

## Support

For issues or questions:
1. Check this documentation
2. Review `/shared/logging/structured_logger.py`
3. Examine example usage in service code
4. Contact the platform team

# Logging Quick Reference Card

## Import

```python
from src.logger import logger, media_logger, log_function_call
```

## Basic Logging

```python
logger.debug("Debug info", var=value)
logger.info("Operation completed", user_id="123", duration_ms=234)
logger.warning("Slow operation", duration_ms=5000, threshold_ms=1000)
logger.error("Operation failed", error="Connection timeout", retry=3)
logger.critical("System failure", component="database")
```

## Media Operations

### Upload
```python
media_logger.log_media_upload(
    filename="video.mp4",
    file_size=157286400,
    content_type="video/mp4",
    user_id="user_123",
    duration_ms=3420.5,
    success=True
)
```

### Processing
```python
media_logger.log_media_processing(
    media_id="media_123",
    processing_type="thumbnail",
    input_format="mp4",
    output_format="jpg",
    duration_ms=234.5,
    success=True
)
```

### Storage
```python
media_logger.log_storage_operation(
    operation="write",
    storage_type="s3",
    path="s3://bucket/file.mp4",
    size_bytes=1024000,
    duration_ms=2341.2,
    success=True
)
```

### Face Detection
```python
media_logger.log_face_detection(
    media_id="media_123",
    faces_detected=3,
    duration_ms=1234.5,
    model="dlib",
    success=True
)
```

### Triggers
```python
media_logger.log_trigger_evaluation(
    trigger_id="trigger_123",
    trigger_type="demographic",
    result=True,
    conditions_met=3,
    total_conditions=4
)
```

### ETL
```python
media_logger.log_etl_operation(
    job_id="job_123",
    operation="sync",
    device_id="device_456",
    status="success",
    items_processed=25,
    duration_ms=5421.8
)
```

## Context Manager

```python
with media_logger.operation_context("operation_name", media_id="123"):
    # Your code here
    # Automatically logs: start, end, duration, errors
    do_work()
```

## Decorators

```python
@log_function_call("my_operation")
async def my_function(arg1, arg2):
    # Automatically logs: entry, exit, duration, errors
    return result
```

## Middleware Setup

```python
from src.middleware.logging import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    ErrorLoggingMiddleware
)

app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(PerformanceLoggingMiddleware, slow_threshold_ms=1000.0)
app.add_middleware(LoggingMiddleware, exclude_paths=["/health"])
```

## Request Context

```python
from src.logger import get_request_context

context = get_request_context(request)
logger.info("Custom log", **context)
```

## View Logs

```bash
# Tail logs
tail -f logs/ppl-meta-media.log

# Pretty JSON
tail -f logs/ppl-meta-media.log | jq '.'

# Filter errors
tail -f logs/ppl-meta-media.log | jq 'select(.level == "ERROR")'

# Filter operations
tail -f logs/ppl-meta-media.log | jq 'select(.operation == "media_upload")'

# Follow request
tail -f logs/ppl-meta-media.log | jq 'select(.request_id == "uuid")'
```

## Environment Config

```bash
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json             # json or console
LOG_FILE=/app/logs/media-service.log
```

## Common Patterns

### API Endpoint
```python
@router.post("/upload")
async def upload(request: Request, file: UploadFile):
    start_time = time.time()
    try:
        result = await process_upload(file)
        duration_ms = (time.time() - start_time) * 1000
        media_logger.log_media_upload(
            filename=file.filename,
            file_size=result.size,
            content_type=file.content_type,
            duration_ms=duration_ms,
            success=True
        )
        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        media_logger.log_media_upload(
            filename=file.filename,
            file_size=0,
            content_type=file.content_type,
            duration_ms=duration_ms,
            success=False,
            error=str(e)
        )
        raise
```

### Database Query
```python
async def get_media(media_id: str):
    start_time = time.time()
    try:
        result = await db.query(Media).filter_by(id=media_id).first()
        logger.info(
            "Database query",
            operation="select",
            table="media",
            media_id=media_id,
            duration_ms=(time.time() - start_time) * 1000,
            found=result is not None
        )
        return result
    except Exception as e:
        logger.error("Database error", operation="select", error=str(e))
        raise
```

### External API
```python
async def call_api(endpoint: str):
    start_time = time.time()
    try:
        response = await http.post(endpoint, json=payload)
        logger.info(
            "External API call",
            service="vision",
            endpoint=endpoint,
            status_code=response.status_code,
            duration_ms=(time.time() - start_time) * 1000
        )
        return response.json()
    except Exception as e:
        logger.error("API call failed", service="vision", error=str(e))
        raise
```

## Log Levels

| Level | When to Use |
|-------|-------------|
| **DEBUG** | Detailed diagnostic info (development only) |
| **INFO** | Normal operations, successful completions |
| **WARNING** | Unexpected but handled situations, slow operations |
| **ERROR** | Failures requiring attention, retryable errors |
| **CRITICAL** | System-level failures, data loss |

## Performance Tips

- Use INFO level in production, DEBUG only in development
- Exclude high-frequency endpoints: `exclude_paths=["/health", "/metrics"]`
- Avoid logging in tight loops
- Use sampling for high-volume operations: `if random.random() < 0.1`
- Include duration_ms for performance tracking

## Need More Help?

- Full docs: [LOGGING.md](./docs/LOGGING.md)
- Integration: [LOGGING_INTEGRATION.md](./docs/LOGGING_INTEGRATION.md)
- Examples: [logging_examples.py](./examples/logging_examples.py)
- Tests: [test_logging.py](./tests/test_logging.py)

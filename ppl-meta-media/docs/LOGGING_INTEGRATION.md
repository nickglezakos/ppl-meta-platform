# Logging System Integration Guide

## Quick Start

To integrate the enhanced logging system into the PPL Meta Media service, follow these steps:

## 1. Enable Logging Middleware

Add the logging middleware to your FastAPI application in [main.py](../src/main.py):

```python
# Add after other imports
from src.middleware.logging import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    ErrorLoggingMiddleware
)

# Add middleware to app (order matters - add these BEFORE CORS and other middleware)
app = FastAPI(
    title="PPL Meta Media Service",
    # ... other config ...
)

# Add logging middleware FIRST (so it wraps all other middleware)
app.add_middleware(
    ErrorLoggingMiddleware  # Catch all unhandled exceptions
)

app.add_middleware(
    PerformanceLoggingMiddleware,
    slow_threshold_ms=1000.0,  # Warn if requests take > 1 second
    very_slow_threshold_ms=5000.0  # High priority warning if > 5 seconds
)

app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health", "/metrics", "/favicon.ico"],  # Don't log these
    log_request_body=False,  # Set to True if needed (careful with large uploads)
    log_response_body=False  # Set to True if needed
)

# Then add other middleware (CORS, Security, etc.)
app.add_middleware(TrustedHostMiddleware, ...)
app.add_middleware(CORSMiddleware, ...)
```

## 2. Update Existing Logging Calls

### Before: Basic logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing media")
logger.error(f"Failed to process media {media_id}")
```

### After: Structured logging
```python
from src.logger import logger, media_logger

logger.info("Processing media", media_id=media_id, operation="process")

media_logger.log_media_processing(
    media_id=media_id,
    processing_type="transcode",
    success=False,
    error="Codec not supported"
)
```

## 3. Update Service Files

### Example: Update a service file

**File:** `src/services/media_service.py`

```python
from src.logger import logger, media_logger

class MediaService:
    async def upload_media(self, file: UploadFile, user_id: str):
        start_time = time.time()
        
        try:
            # Process upload
            file_size = len(await file.read())
            await file.seek(0)
            
            # ... upload logic ...
            
            # Log successful upload
            duration_ms = (time.time() - start_time) * 1000
            media_logger.log_media_upload(
                filename=file.filename,
                file_size=file_size,
                content_type=file.content_type,
                user_id=user_id,
                duration_ms=duration_ms,
                success=True
            )
            
            return {"success": True, "media_id": media_id}
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            media_logger.log_media_upload(
                filename=file.filename,
                file_size=file_size,
                content_type=file.content_type,
                user_id=user_id,
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            raise
```

## 4. Update API Routes

**File:** `src/api/v1/media.py`

```python
from fastapi import APIRouter, Request
from src.logger import logger, get_request_context

router = APIRouter()

@router.post("/upload")
async def upload_media(request: Request, file: UploadFile):
    # Request context is automatically available from middleware
    context = get_request_context(request)
    
    logger.info("Media upload initiated", **context, filename=file.filename)
    
    # Process upload...
    
    return {"success": True}
```

## 5. Add Context Managers for Long Operations

```python
from src.logger import media_logger

async def transcode_video(media_id: str, target_format: str):
    with media_logger.operation_context(
        "video_transcoding",
        media_id=media_id,
        target_format=target_format
    ):
        # All transcoding logic here
        # Automatically logs start, end, duration, and errors
        result = await perform_transcoding(media_id, target_format)
        return result
```

## 6. Add Function Decorators for Auto-Logging

```python
from src.logger import log_function_call

@log_function_call("thumbnail_generation")
async def generate_thumbnail(media_id: str, timestamp: float):
    # Function automatically logs entry, exit, duration, errors
    thumbnail = await create_thumbnail(media_id, timestamp)
    return thumbnail
```

## 7. Update Worker and Background Tasks

**File:** `src/services/signage_etl_worker.py`

```python
from src.logger import logger, media_logger

class ETLWorker:
    async def process_job(self, job: ETLJob):
        media_logger.log_etl_operation(
            job_id=job.job_id,
            operation="sync_start",
            device_id=job.device_id,
            video_list_id=job.video_list_id,
            status="started"
        )
        
        try:
            # Process job
            result = await self._sync_device(job)
            
            media_logger.log_etl_operation(
                job_id=job.job_id,
                operation="sync_complete",
                device_id=job.device_id,
                video_list_id=job.video_list_id,
                status="success",
                items_processed=result.items_count,
                duration_ms=result.duration_ms
            )
            
        except Exception as e:
            media_logger.log_etl_operation(
                job_id=job.job_id,
                operation="sync_failed",
                device_id=job.device_id,
                video_list_id=job.video_list_id,
                status="failed",
                error=str(e)
            )
            raise
```

## 8. Configuration in Environment

Create or update `.env`:

```bash
# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                   # json or console
LOG_FILE=/app/logs/media-service.log

# Service Configuration
APP_NAME=ppl-meta-media
APP_VERSION=1.0.0
ENVIRONMENT=production            # development, staging, production
```

## 9. Test the Integration

Run the logging examples to verify everything works:

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media
python examples/logging_examples.py
```

Check the logs:

```bash
# View logs
tail -f logs/ppl-meta-media.log

# View JSON logs with pretty formatting
tail -f logs/ppl-meta-media.log | jq '.'

# Filter for errors
tail -f logs/ppl-meta-media.log | jq 'select(.level == "ERROR")'

# Filter by operation
tail -f logs/ppl-meta-media.log | jq 'select(.operation == "media_upload")'
```

## 10. Migration Checklist

- [ ] Add logging middleware to `main.py`
- [ ] Update service files to use structured logging
- [ ] Replace all `logging.getLogger(__name__)` with `from src.logger import logger`
- [ ] Add media-specific logging using `media_logger`
- [ ] Add context managers for long operations
- [ ] Add decorators for frequently called functions
- [ ] Update error handling to log with context
- [ ] Configure environment variables
- [ ] Test logging in development
- [ ] Verify log rotation works
- [ ] Set up log aggregation (production)

## Common Patterns

### Pattern 1: API Endpoint with Upload

```python
@router.post("/media/upload")
async def upload_endpoint(
    request: Request,
    file: UploadFile,
    collection_id: str = None
):
    start_time = time.time()
    
    try:
        result = await media_service.upload(file, collection_id)
        
        duration_ms = (time.time() - start_time) * 1000
        media_logger.log_media_upload(
            filename=file.filename,
            file_size=result.size,
            content_type=file.content_type,
            collection_id=collection_id,
            duration_ms=duration_ms,
            success=True,
            media_id=result.media_id
        )
        
        return result
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        media_logger.log_media_upload(
            filename=file.filename,
            file_size=0,
            content_type=file.content_type,
            collection_id=collection_id,
            duration_ms=duration_ms,
            success=False,
            error=str(e)
        )
        raise
```

### Pattern 2: Database Operations

```python
from src.logger import logger

async def get_media(media_id: str):
    start_time = time.time()
    
    try:
        result = await db.query(Media).filter_by(id=media_id).first()
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Database query completed",
            operation="select",
            table="media",
            media_id=media_id,
            duration_ms=duration_ms,
            found=result is not None
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Database query failed",
            operation="select",
            table="media",
            media_id=media_id,
            error=str(e)
        )
        raise
```

### Pattern 3: External API Calls

```python
from src.logger import logger

async def call_external_service(endpoint: str, payload: dict):
    start_time = time.time()
    
    try:
        response = await http_client.post(endpoint, json=payload)
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "External API call",
            service="face_recognition",
            endpoint=endpoint,
            method="POST",
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response.json()
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        logger.error(
            "External API call failed",
            service="face_recognition",
            endpoint=endpoint,
            method="POST",
            duration_ms=duration_ms,
            error=str(e)
        )
        raise
```

## Performance Tips

1. **Use appropriate log levels**
   - DEBUG: Only in development
   - INFO: Normal operations
   - WARNING: Recoverable issues
   - ERROR: Failures requiring attention

2. **Avoid logging in tight loops**
   ```python
   # Bad
   for item in large_list:
       logger.debug(f"Processing item {item}")
   
   # Good
   logger.info("Processing batch", batch_size=len(large_list))
   for item in large_list:
       process(item)
   logger.info("Batch completed", items_processed=len(large_list))
   ```

3. **Exclude high-frequency endpoints**
   ```python
   app.add_middleware(
       LoggingMiddleware,
       exclude_paths=["/health", "/metrics", "/ping"]
   )
   ```

4. **Use sampling for high-volume operations**
   ```python
   if random.random() < 0.1:  # Log 10% of requests
       logger.debug("High volume operation", ...)
   ```

## Troubleshooting

### Issue: Duplicate logs

**Solution:** Remove custom logging handlers from `main.py`. The middleware handles all request logging.

### Issue: Missing request_id

**Solution:** Ensure `LoggingMiddleware` is added to the application.

### Issue: Logs too verbose

**Solution:** Adjust LOG_LEVEL in environment or exclude more paths.

### Issue: Performance degradation

**Solution:** Check if DEBUG level is enabled in production. Switch to INFO or WARNING.

## Next Steps

1. Review the [LOGGING.md](./LOGGING.md) documentation
2. Run the examples: `python examples/logging_examples.py`
3. Start integrating middleware into main.py
4. Update service files one by one
5. Test thoroughly in development
6. Deploy to staging for validation
7. Monitor production logs

## Support

For questions or issues:
- Review [LOGGING.md](./LOGGING.md)
- Check `/shared/logging/` for base implementation
- Examine example code in `/examples/`

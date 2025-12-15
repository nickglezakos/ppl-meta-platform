"""
Enhanced logging utilities specifically for the PPL Meta Media Service.

This module extends the shared logging infrastructure with media-specific
logging capabilities including:
- Media processing operation logging
- File upload/download tracking
- Storage operation logging
- ETL worker logging
- Performance monitoring
- Request correlation
"""

import functools
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

import structlog
from fastapi import Request

# Get the logger instance
logger = structlog.get_logger("ppl-meta-media")


class MediaServiceLogger:
    """
    Specialized logger for media service operations with context management
    and performance tracking.
    """

    def __init__(self, base_logger: Optional[structlog.BoundLogger] = None):
        """Initialize the media service logger."""
        self.logger = base_logger or structlog.get_logger("ppl-meta-media")

    def log_media_upload(
        self,
        filename: str,
        file_size: int,
        content_type: str,
        user_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log media upload operation.

        Args:
            filename: Name of the uploaded file
            file_size: Size in bytes
            content_type: MIME type
            user_id: User identifier
            collection_id: Collection identifier
            duration_ms: Upload duration in milliseconds
            success: Whether upload succeeded
            error: Error message if failed
            **kwargs: Additional context
        """
        log_data = {
            "operation": "media_upload",
            "filename": filename,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "content_type": content_type,
            "success": success,
        }

        if user_id:
            log_data["user_id"] = user_id
        if collection_id:
            log_data["collection_id"] = collection_id
        if duration_ms:
            log_data["duration_ms"] = round(duration_ms, 2)
        if error:
            log_data["error"] = error

        log_data.update(kwargs)

        if success:
            self.logger.info("Media upload completed", **log_data)
        else:
            self.logger.error("Media upload failed", **log_data)

    def log_media_processing(
        self,
        media_id: str,
        processing_type: str,
        duration_ms: Optional[float] = None,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log media processing operation.

        Args:
            media_id: Media identifier
            processing_type: Type of processing (transcode, thumbnail, analysis, etc.)
            duration_ms: Processing duration in milliseconds
            input_format: Input file format
            output_format: Output file format
            success: Whether processing succeeded
            error: Error message if failed
            **kwargs: Additional context
        """
        log_data = {
            "operation": "media_processing",
            "media_id": media_id,
            "processing_type": processing_type,
            "success": success,
        }

        if duration_ms:
            log_data["duration_ms"] = round(duration_ms, 2)
        if input_format:
            log_data["input_format"] = input_format
        if output_format:
            log_data["output_format"] = output_format
        if error:
            log_data["error"] = error

        log_data.update(kwargs)

        if success:
            self.logger.info("Media processing completed", **log_data)
        else:
            self.logger.error("Media processing failed", **log_data)

    def log_storage_operation(
        self,
        operation: str,
        storage_type: str,
        path: str,
        size_bytes: Optional[int] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log storage operation (local, cloud, database).

        Args:
            operation: Operation type (read, write, delete, move)
            storage_type: Type of storage (local, s3, gcs, database)
            path: File or object path
            size_bytes: Size in bytes
            duration_ms: Operation duration in milliseconds
            success: Whether operation succeeded
            error: Error message if failed
            **kwargs: Additional context
        """
        log_data = {
            "operation": "storage_operation",
            "storage_operation": operation,
            "storage_type": storage_type,
            "path": path,
            "success": success,
        }

        if size_bytes:
            log_data["size_bytes"] = size_bytes
            log_data["size_mb"] = round(size_bytes / (1024 * 1024), 2)
        if duration_ms:
            log_data["duration_ms"] = round(duration_ms, 2)
        if error:
            log_data["error"] = error

        log_data.update(kwargs)

        if success:
            self.logger.info("Storage operation completed", **log_data)
        else:
            self.logger.error("Storage operation failed", **log_data)

    def log_etl_operation(
        self,
        job_id: str,
        operation: str,
        device_id: Optional[str] = None,
        video_list_id: Optional[str] = None,
        status: str = "success",
        duration_ms: Optional[float] = None,
        items_processed: Optional[int] = None,
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log ETL worker operation.

        Args:
            job_id: Job identifier
            operation: ETL operation type
            device_id: Target device identifier
            video_list_id: Video list identifier
            status: Operation status
            duration_ms: Operation duration in milliseconds
            items_processed: Number of items processed
            error: Error message if failed
            **kwargs: Additional context
        """
        log_data = {
            "operation": "etl_operation",
            "job_id": job_id,
            "etl_operation": operation,
            "status": status,
        }

        if device_id:
            log_data["device_id"] = device_id
        if video_list_id:
            log_data["video_list_id"] = video_list_id
        if duration_ms:
            log_data["duration_ms"] = round(duration_ms, 2)
        if items_processed is not None:
            log_data["items_processed"] = items_processed
        if error:
            log_data["error"] = error

        log_data.update(kwargs)

        if status == "success":
            self.logger.info("ETL operation completed", **log_data)
        elif status == "failed":
            self.logger.error("ETL operation failed", **log_data)
        else:
            self.logger.warning("ETL operation status change", **log_data)

    def log_face_detection(
        self,
        media_id: str,
        faces_detected: int,
        duration_ms: Optional[float] = None,
        model: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log face detection operation.

        Args:
            media_id: Media identifier
            faces_detected: Number of faces detected
            duration_ms: Detection duration in milliseconds
            model: Detection model used
            success: Whether detection succeeded
            error: Error message if failed
            **kwargs: Additional context
        """
        log_data = {
            "operation": "face_detection",
            "media_id": media_id,
            "faces_detected": faces_detected,
            "success": success,
        }

        if duration_ms:
            log_data["duration_ms"] = round(duration_ms, 2)
        if model:
            log_data["model"] = model
        if error:
            log_data["error"] = error

        log_data.update(kwargs)

        if success:
            self.logger.info("Face detection completed", **log_data)
        else:
            self.logger.error("Face detection failed", **log_data)

    def log_trigger_evaluation(
        self,
        trigger_id: str,
        trigger_type: str,
        result: bool,
        conditions_met: Optional[int] = None,
        total_conditions: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ) -> None:
        """
        Log trigger evaluation.

        Args:
            trigger_id: Trigger identifier
            trigger_type: Type of trigger
            result: Evaluation result
            conditions_met: Number of conditions met
            total_conditions: Total number of conditions
            duration_ms: Evaluation duration in milliseconds
            **kwargs: Additional context
        """
        log_data = {
            "operation": "trigger_evaluation",
            "trigger_id": trigger_id,
            "trigger_type": trigger_type,
            "result": result,
        }

        if conditions_met is not None and total_conditions is not None:
            log_data["conditions_met"] = conditions_met
            log_data["total_conditions"] = total_conditions
        if duration_ms:
            log_data["duration_ms"] = round(duration_ms, 2)

        log_data.update(kwargs)

        self.logger.info("Trigger evaluation completed", **log_data)

    @contextmanager
    def operation_context(self, operation: str, **context):
        """
        Context manager for tracking operation duration and logging.

        Usage:
            with media_logger.operation_context("video_transcoding", media_id="123"):
                # perform operation
                pass

        Args:
            operation: Operation name
            **context: Additional context to log
        """
        start_time = time.time()
        log_data = {"operation": operation, **context}

        self.logger.info(f"{operation} started", **log_data)

        try:
            yield log_data
            duration_ms = (time.time() - start_time) * 1000
            log_data["duration_ms"] = round(duration_ms, 2)
            log_data["success"] = True
            self.logger.info(f"{operation} completed", **log_data)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_data["duration_ms"] = round(duration_ms, 2)
            log_data["success"] = False
            log_data["error"] = str(e)
            log_data["error_type"] = type(e).__name__
            self.logger.error(f"{operation} failed", **log_data, exc_info=e)
            raise


# Global instance
media_logger = MediaServiceLogger()


def log_function_call(operation_name: Optional[str] = None):
    """
    Decorator to automatically log function calls with timing.

    Usage:
        @log_function_call("my_operation")
        async def my_function(arg1, arg2):
            pass

    Args:
        operation_name: Optional operation name (defaults to function name)
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            log_data = {
                "operation": op_name,
                "function": func.__name__,
                "module": func.__module__,
            }

            logger.debug(f"Function call started: {op_name}", **log_data)

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                log_data["duration_ms"] = round(duration_ms, 2)
                log_data["success"] = True

                logger.debug(f"Function call completed: {op_name}", **log_data)
                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                log_data["duration_ms"] = round(duration_ms, 2)
                log_data["success"] = False
                log_data["error"] = str(e)
                log_data["error_type"] = type(e).__name__

                logger.error(f"Function call failed: {op_name}", **log_data, exc_info=e)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            log_data = {
                "operation": op_name,
                "function": func.__name__,
                "module": func.__module__,
            }

            logger.debug(f"Function call started: {op_name}", **log_data)

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                log_data["duration_ms"] = round(duration_ms, 2)
                log_data["success"] = True

                logger.debug(f"Function call completed: {op_name}", **log_data)
                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                log_data["duration_ms"] = round(duration_ms, 2)
                log_data["success"] = False
                log_data["error"] = str(e)
                log_data["error_type"] = type(e).__name__

                logger.error(f"Function call failed: {op_name}", **log_data, exc_info=e)
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_request_context(request: Request) -> Dict[str, Any]:
    """
    Extract logging context from FastAPI request.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with request context
    """
    return {
        "request_id": getattr(request.state, "request_id", None),
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "user_id": getattr(request.state, "user_id", None),
    }


def log_api_request(request: Request, **kwargs) -> None:
    """
    Log incoming API request.

    Args:
        request: FastAPI request object
        **kwargs: Additional context
    """
    context = get_request_context(request)
    context.update(kwargs)
    logger.info("API request received", **context)


def log_api_response(
    request: Request,
    status_code: int,
    duration_ms: float,
    **kwargs,
) -> None:
    """
    Log API response.

    Args:
        request: FastAPI request object
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    context = get_request_context(request)
    context.update(
        {
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
    )
    context.update(kwargs)

    if status_code >= 500:
        logger.error("API request failed", **context)
    elif status_code >= 400:
        logger.warning("API request error", **context)
    else:
        logger.info("API request completed", **context)


# Import asyncio for decorator
import asyncio


__all__ = [
    "logger",
    "media_logger",
    "MediaServiceLogger",
    "log_function_call",
    "get_request_context",
    "log_api_request",
    "log_api_response",
]

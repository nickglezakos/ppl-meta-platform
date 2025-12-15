"""
Example usage of the PPL Meta Media logging system.

This script demonstrates various logging features and best practices.
"""

import asyncio
import os
import sys
import time

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logger import (
    logger,
    media_logger,
    log_function_call,
)


def example_basic_logging():
    """Demonstrate basic structured logging."""
    print("\n=== Basic Logging Examples ===\n")

    # Simple logging
    logger.info("Service started")
    logger.debug("Debug information", module="example")
    logger.warning("This is a warning", threshold=100, actual=150)
    logger.error("An error occurred", error_code="E001", component="storage")

    # Structured logging with context
    logger.info(
        "User action logged",
        user_id="user_123",
        action="upload",
        resource="video.mp4",
        timestamp=time.time(),
    )


def example_media_operations():
    """Demonstrate media-specific logging."""
    print("\n=== Media Operation Logging ===\n")

    # Log a media upload
    media_logger.log_media_upload(
        filename="vacation_video.mp4",
        file_size=157286400,  # ~150 MB
        content_type="video/mp4",
        user_id="user_456",
        collection_id="col_789",
        duration_ms=3421.5,
        success=True,
        upload_method="multipart",
    )

    # Log media processing
    media_logger.log_media_processing(
        media_id="media_123",
        processing_type="thumbnail_generation",
        duration_ms=245.3,
        input_format="mp4",
        output_format="jpg",
        success=True,
        thumbnails_created=5,
        resolution="1920x1080",
    )

    # Log face detection
    media_logger.log_face_detection(
        media_id="media_123",
        faces_detected=3,
        duration_ms=1234.5,
        model="dlib_cnn",
        success=True,
        confidence_scores=[0.98, 0.95, 0.89],
    )

    # Log storage operation
    media_logger.log_storage_operation(
        operation="write",
        storage_type="s3",
        path="s3://ppl-media/videos/vacation_video.mp4",
        size_bytes=157286400,
        duration_ms=2341.2,
        success=True,
        bucket="ppl-media",
        region="us-east-1",
    )

    # Log ETL operation
    media_logger.log_etl_operation(
        job_id="job_abc123",
        operation="sync_playlist",
        device_id="device_456",
        video_list_id="vlist_789",
        status="success",
        duration_ms=5421.8,
        items_processed=25,
        errors_encountered=0,
    )

    # Log trigger evaluation
    media_logger.log_trigger_evaluation(
        trigger_id="trigger_demo_01",
        trigger_type="demographic",
        result=True,
        conditions_met=3,
        total_conditions=4,
        duration_ms=15.2,
        matched_demographics=["age_25_34", "gender_male"],
    )


def example_context_manager():
    """Demonstrate context manager for operation tracking."""
    print("\n=== Context Manager Example ===\n")

    # Successful operation
    with media_logger.operation_context(
        "video_transcoding",
        media_id="media_456",
        target_format="h264",
    ):
        # Simulate transcoding work
        time.sleep(0.1)
        logger.info("Transcoding in progress", progress=50)
        time.sleep(0.1)

    # Failed operation
    try:
        with media_logger.operation_context(
            "thumbnail_extraction",
            media_id="media_789",
            timestamp="00:05:30",
        ):
            # Simulate failure
            time.sleep(0.05)
            raise ValueError("Invalid timestamp format")
    except ValueError:
        pass  # Exception is already logged


@log_function_call("async_media_upload")
async def example_async_function(filename: str, size_mb: float):
    """Demonstrate decorator with async function."""
    logger.info("Starting async upload", filename=filename, size_mb=size_mb)
    await asyncio.sleep(0.1)  # Simulate async work
    logger.info("Upload chunk processed", chunk=1)
    await asyncio.sleep(0.1)
    return {"success": True, "media_id": "media_new_123"}


@log_function_call("sync_processing")
def example_sync_function(media_id: str):
    """Demonstrate decorator with sync function."""
    logger.info("Processing media", media_id=media_id)
    time.sleep(0.1)  # Simulate work
    return {"processed": True}


async def example_decorated_functions():
    """Demonstrate function decorators."""
    print("\n=== Function Decorator Examples ===\n")

    # Async function with decorator
    result1 = await example_async_function("test_video.mp4", 125.5)
    logger.info("Async result", result=result1)

    # Sync function with decorator
    result2 = example_sync_function("media_test_456")
    logger.info("Sync result", result=result2)


def example_error_logging():
    """Demonstrate error logging patterns."""
    print("\n=== Error Logging Examples ===\n")

    # Log a simple error
    try:
        raise FileNotFoundError("Media file not found")
    except FileNotFoundError as e:
        logger.error(
            "File operation failed",
            operation="read",
            path="/media/missing_file.mp4",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Log an error with full context
    try:
        # Simulate processing failure
        raise RuntimeError("Transcoding failed: codec not supported")
    except RuntimeError as e:
        media_logger.log_media_processing(
            media_id="media_error_123",
            processing_type="transcode",
            input_format="wmv",
            output_format="mp4",
            success=False,
            error=str(e),
            duration_ms=2345.6,
        )


def example_performance_logging():
    """Demonstrate performance logging."""
    print("\n=== Performance Logging Examples ===\n")

    operations = [
        ("fast_operation", 0.05),
        ("normal_operation", 0.15),
        ("slow_operation", 1.2),
    ]

    for operation_name, duration in operations:
        start_time = time.time()
        time.sleep(duration)
        duration_ms = (time.time() - start_time) * 1000

        log_level = "info"
        if duration_ms > 1000:
            log_level = "warning"

        getattr(logger, log_level)(
            f"Operation completed: {operation_name}",
            operation=operation_name,
            duration_ms=round(duration_ms, 2),
            threshold_ms=1000,
            is_slow=duration_ms > 1000,
        )


async def main():
    """Run all examples."""
    print("=" * 60)
    print("PPL Meta Media Service - Logging Examples")
    print("=" * 60)

    # Run examples
    example_basic_logging()
    example_media_operations()
    example_context_manager()
    await example_decorated_functions()
    example_error_logging()
    example_performance_logging()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Setup logging first
    import os
    import sys
    
    # Add workspace root to path for shared modules
    # From ppl-meta-media/examples -> ppl-meta-media -> ppl-meta-code (workspace root)
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if workspace_root not in sys.path:
        sys.path.insert(0, workspace_root)
    
    from shared.logging import setup_logging

    log_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "logs",
        "media-logging-example.log"
    )

    setup_logging(
        service_name="ppl-meta-media",
        log_level="INFO",
        log_format="console",  # Use console format for examples
        log_file=log_file,
    )

    logger.info("Starting logging examples")
    asyncio.run(main())
    logger.info("Logging examples completed", log_file=log_file)

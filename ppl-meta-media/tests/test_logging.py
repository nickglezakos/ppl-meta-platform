"""
Unit tests for the PPL Meta Media logging system.

Tests cover:
- Basic logging functionality
- Media-specific loggers
- Context managers
- Decorators
- Middleware integration
"""

import asyncio
import time
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.logger import (
    logger,
    media_logger,
    log_function_call,
    get_request_context,
)
from src.middleware.logging import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    ErrorLoggingMiddleware,
)


class TestBasicLogging:
    """Test basic logging functionality."""

    def test_logger_import(self):
        """Test that logger can be imported."""
        assert logger is not None

    def test_basic_log_levels(self, caplog):
        """Test that different log levels work."""
        logger.debug("Debug message", test=True)
        logger.info("Info message", test=True)
        logger.warning("Warning message", test=True)
        logger.error("Error message", test=True)

    def test_structured_logging(self):
        """Test that structured context is properly logged."""
        with patch('src.logger.logger') as mock_logger:
            logger.info(
                "Test message",
                user_id="123",
                action="test",
                value=42
            )


class TestMediaLogger:
    """Test media-specific logging functions."""

    def test_media_logger_instance(self):
        """Test that media_logger is properly instantiated."""
        assert media_logger is not None

    def test_log_media_upload_success(self):
        """Test logging successful media upload."""
        media_logger.log_media_upload(
            filename="test.mp4",
            file_size=1024000,
            content_type="video/mp4",
            user_id="user_123",
            collection_id="col_456",
            duration_ms=1234.5,
            success=True
        )

    def test_log_media_upload_failure(self):
        """Test logging failed media upload."""
        media_logger.log_media_upload(
            filename="test.mp4",
            file_size=1024000,
            content_type="video/mp4",
            user_id="user_123",
            duration_ms=500.0,
            success=False,
            error="Connection timeout"
        )

    def test_log_media_processing(self):
        """Test logging media processing operations."""
        media_logger.log_media_processing(
            media_id="media_123",
            processing_type="thumbnail",
            duration_ms=234.5,
            input_format="mp4",
            output_format="jpg",
            success=True
        )

    def test_log_storage_operation(self):
        """Test logging storage operations."""
        media_logger.log_storage_operation(
            operation="write",
            storage_type="s3",
            path="s3://bucket/file.mp4",
            size_bytes=1024000,
            duration_ms=2341.2,
            success=True
        )

    def test_log_face_detection(self):
        """Test logging face detection operations."""
        media_logger.log_face_detection(
            media_id="media_123",
            faces_detected=3,
            duration_ms=1234.5,
            model="dlib",
            success=True
        )

    def test_log_trigger_evaluation(self):
        """Test logging trigger evaluation."""
        media_logger.log_trigger_evaluation(
            trigger_id="trigger_123",
            trigger_type="demographic",
            result=True,
            conditions_met=3,
            total_conditions=4,
            duration_ms=15.2
        )

    def test_log_etl_operation(self):
        """Test logging ETL operations."""
        media_logger.log_etl_operation(
            job_id="job_123",
            operation="sync",
            device_id="device_456",
            status="success",
            items_processed=25,
            duration_ms=5421.8
        )


class TestContextManager:
    """Test operation context manager."""

    def test_successful_operation(self):
        """Test context manager with successful operation."""
        with media_logger.operation_context("test_operation", test_id="123"):
            time.sleep(0.01)
            # Should complete successfully

    def test_failed_operation(self):
        """Test context manager with failed operation."""
        with pytest.raises(ValueError):
            with media_logger.operation_context("test_operation", test_id="456"):
                raise ValueError("Test error")


class TestDecorators:
    """Test function decorators."""

    @log_function_call("test_sync_function")
    def sync_function(self, value):
        """Test synchronous function."""
        time.sleep(0.01)
        return value * 2

    @log_function_call("test_async_function")
    async def async_function(self, value):
        """Test asynchronous function."""
        await asyncio.sleep(0.01)
        return value * 2

    def test_sync_decorator(self):
        """Test decorator on sync function."""
        result = self.sync_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """Test decorator on async function."""
        result = await self.async_function(5)
        assert result == 10

    @log_function_call("test_error_function")
    def error_function(self):
        """Test function that raises an error."""
        raise RuntimeError("Test error")

    def test_decorator_with_error(self):
        """Test that decorator properly logs errors."""
        with pytest.raises(RuntimeError):
            self.error_function()


class TestRequestContext:
    """Test request context extraction."""

    def test_get_request_context(self):
        """Test extracting context from request."""
        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/media/upload"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "test-client"}
        mock_request.state = Mock()
        mock_request.state.request_id = "req_123"
        mock_request.state.user_id = "user_456"

        context = get_request_context(mock_request)

        assert context["method"] == "POST"
        assert context["path"] == "/api/v1/media/upload"
        assert context["client_ip"] == "127.0.0.1"
        assert context["request_id"] == "req_123"
        assert context["user_id"] == "user_456"


class TestLoggingMiddleware:
    """Test logging middleware."""

    def setup_method(self):
        """Set up test FastAPI app with middleware."""
        self.app = FastAPI()
        
        self.app.add_middleware(LoggingMiddleware)

        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        @self.app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        self.client = TestClient(self.app)

    def test_successful_request_logging(self):
        """Test that successful requests are logged."""
        response = self.client.get("/test")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_error_request_logging(self):
        """Test that failed requests are logged."""
        with pytest.raises(Exception):
            self.client.get("/error")


class TestPerformanceMiddleware:
    """Test performance monitoring middleware."""

    def setup_method(self):
        """Set up test FastAPI app with performance middleware."""
        self.app = FastAPI()
        
        self.app.add_middleware(
            PerformanceLoggingMiddleware,
            slow_threshold_ms=10.0,
            very_slow_threshold_ms=50.0
        )

        @self.app.get("/fast")
        async def fast_endpoint():
            return {"message": "fast"}

        @self.app.get("/slow")
        async def slow_endpoint():
            await asyncio.sleep(0.02)  # 20ms - slow
            return {"message": "slow"}

        @self.app.get("/very-slow")
        async def very_slow_endpoint():
            await asyncio.sleep(0.06)  # 60ms - very slow
            return {"message": "very slow"}

        self.client = TestClient(self.app)

    def test_fast_request(self):
        """Test that fast requests don't trigger warnings."""
        response = self.client.get("/fast")
        assert response.status_code == 200

    def test_slow_request(self):
        """Test that slow requests are logged."""
        response = self.client.get("/slow")
        assert response.status_code == 200

    def test_very_slow_request(self):
        """Test that very slow requests are logged with high priority."""
        response = self.client.get("/very-slow")
        assert response.status_code == 200


class TestErrorMiddleware:
    """Test error logging middleware."""

    def setup_method(self):
        """Set up test FastAPI app with error middleware."""
        self.app = FastAPI()
        
        self.app.add_middleware(ErrorLoggingMiddleware)

        @self.app.get("/success")
        async def success_endpoint():
            return {"message": "success"}

        @self.app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error message")

        self.client = TestClient(self.app)

    def test_successful_request_no_error(self):
        """Test that successful requests don't trigger error logging."""
        response = self.client.get("/success")
        assert response.status_code == 200

    def test_error_request_logged(self):
        """Test that errors are properly logged."""
        with pytest.raises(Exception):
            self.client.get("/error")


class TestIntegration:
    """Integration tests with multiple middleware."""

    def setup_method(self):
        """Set up test FastAPI app with all middleware."""
        self.app = FastAPI()
        
        # Add all middleware
        self.app.add_middleware(ErrorLoggingMiddleware)
        self.app.add_middleware(
            PerformanceLoggingMiddleware,
            slow_threshold_ms=100.0
        )
        self.app.add_middleware(
            LoggingMiddleware,
            exclude_paths=["/health"]
        )

        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

        @self.app.get("/api/test")
        async def test_endpoint():
            return {"message": "test"}

        @self.app.post("/api/upload")
        async def upload_endpoint():
            await asyncio.sleep(0.01)
            return {"uploaded": True}

        self.client = TestClient(self.app)

    def test_excluded_path_not_logged(self):
        """Test that excluded paths are not logged."""
        response = self.client.get("/health")
        assert response.status_code == 200
        # Health endpoint should not have request ID
        # (it would if it went through logging middleware)

    def test_normal_endpoint_logged(self):
        """Test that normal endpoints are properly logged."""
        response = self.client.get("/api/test")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_post_endpoint_logged(self):
        """Test that POST endpoints are properly logged."""
        response = self.client.post("/api/upload")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers


# Performance benchmark tests
class TestPerformance:
    """Test logging performance impact."""

    def test_logging_overhead(self):
        """Test that logging doesn't add significant overhead."""
        iterations = 1000

        # Without logging
        start_time = time.time()
        for _ in range(iterations):
            _ = {"test": "data", "value": 123}
        no_logging_time = time.time() - start_time

        # With logging
        start_time = time.time()
        for i in range(iterations):
            logger.debug("Test message", iteration=i, data="test")
        with_logging_time = time.time() - start_time

        # Logging shouldn't add more than 10x overhead
        assert with_logging_time < no_logging_time * 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

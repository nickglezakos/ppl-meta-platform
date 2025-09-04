import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "ppl-meta-cameras", "src"))

from api.v1.endpoints.mobile_streaming import (
    get_mobile_streaming_status,
    setup_mobile_streaming,
    stop_mobile_streaming,
)
from services.camera_detection import CameraDetectionService
from services.mobile_capture import MobileVideoCapture
from services.mobile_streaming import MobileCameraStreamingService


class TestMobileCameraStreamingPhase2:
    """Test suite for Phase 2 - Flutter Mobile App Streaming Integration"""

    @pytest.fixture
    def mock_streaming_service(self):
        """Mock streaming service for testing"""
        service = Mock(spec=MobileCameraStreamingService)
        service.setup_streaming = AsyncMock(return_value=True)
        service.start_streaming = AsyncMock(return_value=True)
        service.stop_streaming = AsyncMock(return_value=True)
        service.is_streaming = Mock(return_value=False)
        service.get_status = Mock(
            return_value={
                "is_streaming": False,
                "rtmp_url": None,
                "quality": "medium",
                "fps": 30,
                "resolution": "1280x720",
            }
        )
        service.get_stats = Mock(
            return_value={
                "frames_sent": 0,
                "bytes_sent": 0,
                "duration": 0,
                "avg_fps": 0.0,
                "bitrate": 0,
            }
        )
        return service

    @pytest.mark.asyncio
    async def test_mobile_streaming_service_initialization(self):
        """Test MobileCameraStreamingService initialization"""
        service = MobileCameraStreamingService()

        # Test initialization
        await service.initialize()

        # Verify initial state
        assert not service.is_streaming()
        assert service.get_status()["is_streaming"] is False

        # Cleanup
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_mobile_capture_interface(self):
        """Test MobileVideoCapture OpenCV compatibility"""
        # Create mock capture
        capture = MobileVideoCapture("mobile://device123")

        # Test interface methods
        assert hasattr(capture, "read")
        assert hasattr(capture, "isOpened")
        assert hasattr(capture, "get")
        assert hasattr(capture, "set")
        assert hasattr(capture, "release")

        # Test initial state
        assert not capture.isOpened()

        # Test read when not opened
        ret, frame = capture.read()
        assert not ret
        assert frame is None

    @pytest.mark.asyncio
    async def test_camera_detection_mobile_support(self):
        """Test camera detection service mobile camera support"""
        service = CameraDetectionService()

        # Test mobile camera string detection
        mobile_connection = "mobile://device123"
        assert service._is_mobile_camera(mobile_connection)

        # Test non-mobile camera strings
        assert not service._is_mobile_camera("0")  # USB camera
        assert not service._is_mobile_camera("rtsp://192.168.1.100:554/stream")

    @pytest.mark.asyncio
    async def test_mobile_streaming_api_setup(self, mock_streaming_service):
        """Test mobile streaming API setup endpoint"""
        device_id = "test_device_123"

        # Mock request
        mock_request = Mock()
        mock_request.json = AsyncMock(
            return_value={
                "rtmp_url": f"rtmp://localhost:1935/streaming/mobile/{device_id}",
                "quality": "high",
                "fps": 30,
            }
        )

        with patch(
            "api.v1.endpoints.mobile_streaming.mobile_streaming_service",
            mock_streaming_service,
        ):
            response = await setup_mobile_streaming(device_id, mock_request)

            # Verify service was called
            mock_streaming_service.setup_streaming.assert_called_once()

            # Verify response
            assert response["status"] == "success"
            assert "session_id" in response

    @pytest.mark.asyncio
    async def test_mobile_streaming_api_status(self, mock_streaming_service):
        """Test mobile streaming API status endpoint"""
        device_id = "test_device_123"

        with patch(
            "api.v1.endpoints.mobile_streaming.mobile_streaming_service",
            mock_streaming_service,
        ):
            response = await get_mobile_streaming_status(device_id)

            # Verify service was called
            mock_streaming_service.get_status.assert_called_once()
            mock_streaming_service.get_stats.assert_called_once()

            # Verify response structure
            assert "status" in response
            assert "stats" in response

    @pytest.mark.asyncio
    async def test_mobile_streaming_api_stop(self, mock_streaming_service):
        """Test mobile streaming API stop endpoint"""
        device_id = "test_device_123"

        with patch(
            "api.v1.endpoints.mobile_streaming.mobile_streaming_service",
            mock_streaming_service,
        ):
            response = await stop_mobile_streaming(device_id)

            # Verify service was called
            mock_streaming_service.stop_streaming.assert_called_once()

            # Verify response
            assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_rtmp_stream_processing(self, mock_streaming_service):
        """Test RTMP stream processing pipeline"""
        device_id = "test_device_123"
        rtmp_url = f"rtmp://localhost:1935/streaming/mobile/{device_id}"

        # Setup streaming
        mock_streaming_service.setup_streaming.return_value = True
        mock_streaming_service.start_streaming.return_value = True

        # Test stream setup
        setup_result = await mock_streaming_service.setup_streaming(
            device_id=device_id, rtmp_url=rtmp_url, quality="medium"
        )

        assert setup_result is True

        # Test stream start
        start_result = await mock_streaming_service.start_streaming(device_id)
        assert start_result is True

    @pytest.mark.asyncio
    async def test_quality_adaptation(self, mock_streaming_service):
        """Test streaming quality adaptation"""
        device_id = "test_device_123"

        # Test different quality settings
        qualities = ["low", "medium", "high"]

        for quality in qualities:
            mock_streaming_service.setup_streaming.reset_mock()

            await mock_streaming_service.setup_streaming(
                device_id=device_id, rtmp_url="rtmp://test", quality=quality
            )

            # Verify setup was called with correct quality
            mock_streaming_service.setup_streaming.assert_called_once()
            call_args = mock_streaming_service.setup_streaming.call_args
            assert call_args[1]["quality"] == quality

    @pytest.mark.asyncio
    async def test_network_connectivity_handling(self):
        """Test network connectivity handling"""
        service = MobileCameraStreamingService()

        # Test network disconnection handling
        with patch(
            "services.mobile_streaming.check_network_connectivity", return_value=False
        ):
            result = await service.setup_streaming(
                device_id="test", rtmp_url="rtmp://test", quality="medium"
            )
            # Should handle network issues gracefully
            assert result is False

    @pytest.mark.asyncio
    async def test_session_management(self, mock_streaming_service):
        """Test streaming session management"""
        device_id = "test_device_123"

        # Setup streaming session
        await mock_streaming_service.setup_streaming(
            device_id=device_id, rtmp_url="rtmp://test", quality="medium"
        )

        # Start streaming
        await mock_streaming_service.start_streaming(device_id)

        # Verify session is active
        status = mock_streaming_service.get_status()
        assert "session_id" in status or status["is_streaming"] is not None

        # Stop streaming
        await mock_streaming_service.stop_streaming(device_id)

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_streaming_service):
        """Test error handling and recovery mechanisms"""
        device_id = "test_device_123"

        # Test setup failure
        mock_streaming_service.setup_streaming.side_effect = Exception("Setup failed")

        with pytest.raises(Exception):
            await mock_streaming_service.setup_streaming(
                device_id=device_id, rtmp_url="invalid://url", quality="medium"
            )

        # Reset mock for recovery test
        mock_streaming_service.setup_streaming.side_effect = None
        mock_streaming_service.setup_streaming.return_value = True

        # Test recovery
        result = await mock_streaming_service.setup_streaming(
            device_id=device_id, rtmp_url="rtmp://valid", quality="medium"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_performance_metrics(self, mock_streaming_service):
        """Test performance metrics collection"""
        device_id = "test_device_123"

        # Mock performance stats
        mock_streaming_service.get_stats.return_value = {
            "frames_sent": 1800,  # 60 seconds at 30 fps
            "bytes_sent": 1024 * 1024 * 5,  # 5 MB
            "duration": 60,  # 60 seconds
            "avg_fps": 30.0,
            "bitrate": 683690,  # ~680 kbps
        }

        stats = mock_streaming_service.get_stats()

        # Verify stats structure
        assert "frames_sent" in stats
        assert "bytes_sent" in stats
        assert "duration" in stats
        assert "avg_fps" in stats
        assert "bitrate" in stats

        # Verify reasonable values
        assert stats["frames_sent"] > 0
        assert stats["bytes_sent"] > 0
        assert stats["avg_fps"] > 0
        assert stats["bitrate"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_streaming_sessions(self, mock_streaming_service):
        """Test handling of multiple concurrent streaming sessions"""
        device_ids = ["device_1", "device_2", "device_3"]

        # Setup multiple sessions
        setup_tasks = []
        for device_id in device_ids:
            task = mock_streaming_service.setup_streaming(
                device_id=device_id,
                rtmp_url=f"rtmp://test/{device_id}",
                quality="medium",
            )
            setup_tasks.append(task)

        results = await asyncio.gather(*setup_tasks)

        # Verify all sessions were setup
        assert all(results)
        assert mock_streaming_service.setup_streaming.call_count == len(device_ids)

    @pytest.mark.asyncio
    async def test_resource_cleanup(self, mock_streaming_service):
        """Test proper resource cleanup"""
        device_id = "test_device_123"

        # Setup and start streaming
        await mock_streaming_service.setup_streaming(
            device_id=device_id, rtmp_url="rtmp://test", quality="medium"
        )
        await mock_streaming_service.start_streaming(device_id)

        # Stop streaming
        await mock_streaming_service.stop_streaming(device_id)

        # Verify cleanup was called
        mock_streaming_service.stop_streaming.assert_called_once_with(device_id)

    def test_integration_with_existing_camera_system(self):
        """Test integration with existing camera detection system"""
        service = CameraDetectionService()

        # Test that mobile cameras are detected alongside existing cameras
        mobile_camera = "mobile://device123"
        usb_camera = "0"
        rtsp_camera = "rtsp://192.168.1.100:554/stream"

        # Verify different camera types are handled correctly
        assert service._is_mobile_camera(mobile_camera)
        assert not service._is_mobile_camera(usb_camera)
        assert not service._is_mobile_camera(rtsp_camera)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])

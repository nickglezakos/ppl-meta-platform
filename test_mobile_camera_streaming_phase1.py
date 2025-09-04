"""
Test mobile camera streaming integration - Phase 1 Backend Infrastructure.
Tests the core mobile camera streaming functionality.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add the src directory to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "ppl-meta-cameras", "src")
)

from models.camera import Camera, CameraStatus, CameraType
from services.camera_detection import CameraDetectionService
from services.mobile_capture import MobileVideoCapture
from services.mobile_streaming import MobileCameraStreamingService


class TestMobileCameraStreaming:
    """Test mobile camera streaming functionality."""

    @pytest.fixture
    def mobile_streaming_service(self):
        """Create mobile streaming service instance."""
        return MobileCameraStreamingService()

    @pytest.fixture
    def sample_mobile_camera(self):
        """Create sample mobile camera for testing."""
        return {
            "device_id": "mobile_test_001",
            "name": "Test Mobile Camera",
            "ip_address": "192.168.1.100",
            "port": 8554,
            "connection_string": "mobile://192.168.1.100:8554",
            "camera_type": CameraType.MOBILE,
            "resolution_width": 1280,
            "resolution_height": 720,
            "max_fps": 30,
        }

    @pytest.mark.asyncio
    async def test_mobile_streaming_service_setup(
        self, mobile_streaming_service, sample_mobile_camera
    ):
        """Test mobile streaming service setup."""

        stream_config = {
            "ip_address": sample_mobile_camera["ip_address"],
            "port": sample_mobile_camera["port"],
            "protocol": "rtmp",
            "width": sample_mobile_camera["resolution_width"],
            "height": sample_mobile_camera["resolution_height"],
            "fps": sample_mobile_camera["max_fps"],
        }

        # Mock FFmpeg and file operations
        with patch("subprocess.Popen") as mock_popen, patch(
            "os.mkfifo"
        ) as mock_mkfifo, patch("tempfile.mkdtemp") as mock_mkdtemp:

            mock_mkdtemp.return_value = "/tmp/test_dir"
            mock_process = Mock()
            mock_popen.return_value = mock_process

            # Test stream setup
            result = await mobile_streaming_service.setup_mobile_camera_stream(
                sample_mobile_camera["device_id"], stream_config
            )

            assert result is True
            assert (
                sample_mobile_camera["device_id"]
                in mobile_streaming_service.active_mobile_streams
            )

            # Verify stream configuration
            stream_info = mobile_streaming_service.active_mobile_streams[
                sample_mobile_camera["device_id"]
            ]
            assert stream_info["ip_address"] == sample_mobile_camera["ip_address"]
            assert stream_info["port"] == sample_mobile_camera["port"]
            assert stream_info["protocol"] == "rtmp"

    @pytest.mark.asyncio
    async def test_mobile_video_capture_interface(
        self, mobile_streaming_service, sample_mobile_camera
    ):
        """Test mobile video capture OpenCV-like interface."""

        # Create mobile video capture instance
        mobile_cap = MobileVideoCapture(
            sample_mobile_camera["device_id"], mobile_streaming_service
        )

        # Mock the streaming service methods
        mobile_streaming_service.setup_mobile_camera_stream = AsyncMock(
            return_value=True
        )
        mobile_streaming_service.get_mobile_camera_frame = Mock(return_value=None)
        mobile_streaming_service.get_mobile_stream_status = Mock(
            return_value={"status": "active"}
        )
        mobile_streaming_service.stop_mobile_camera_stream = Mock(return_value=True)

        # Test opening mobile camera
        stream_config = {
            "ip_address": sample_mobile_camera["ip_address"],
            "port": sample_mobile_camera["port"],
            "protocol": "rtmp",
            "width": 640,
            "height": 480,
            "fps": 30,
        }

        result = await mobile_cap.open(stream_config)
        assert result is True
        assert mobile_cap.isOpened() is True

        # Test getting camera properties
        assert mobile_cap.get(999) == 640.0  # CAP_PROP_FRAME_WIDTH
        assert mobile_cap.get(1000) == 480.0  # CAP_PROP_FRAME_HEIGHT
        assert mobile_cap.get(1001) == 30.0  # CAP_PROP_FPS

        # Test setting camera properties
        assert mobile_cap.set(999, 1280) is True
        assert mobile_cap.set(1000, 720) is True

        # Test frame reading (with no frame available)
        ret, frame = mobile_cap.read()
        assert ret is False
        assert frame is None

        # Test releasing mobile camera
        mobile_cap.release()
        assert mobile_cap._is_opened is False

    @pytest.mark.asyncio
    async def test_camera_detection_service_mobile_integration(
        self, sample_mobile_camera
    ):
        """Test camera detection service integration with mobile cameras."""

        camera_service = CameraDetectionService()

        # Mock database and mobile streaming service
        with patch("src.services.camera_detection.get_db") as mock_get_db, patch(
            "src.services.mobile_streaming.mobile_streaming_service"
        ) as mock_mobile_service, patch(
            "src.services.mobile_capture.MobileVideoCapture"
        ) as mock_mobile_cap:

            # Setup database mock
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db

            # Create mock camera object
            mock_camera = Mock()
            mock_camera.device_id = sample_mobile_camera["device_id"]
            mock_camera.camera_type = CameraType.MOBILE
            mock_camera.connection_string = sample_mobile_camera["connection_string"]
            mock_camera.resolution_width = sample_mobile_camera["resolution_width"]
            mock_camera.resolution_height = sample_mobile_camera["resolution_height"]
            mock_camera.max_fps = sample_mobile_camera["max_fps"]

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_camera
            )

            # Setup mobile capture mock
            mock_mobile_cap_instance = Mock()
            mock_mobile_cap_instance.open = AsyncMock(return_value=True)
            mock_mobile_cap_instance.isOpened.return_value = True
            mock_mobile_cap.return_value = mock_mobile_cap_instance

            # Test connecting to mobile camera
            connection = await camera_service.connect_camera(
                sample_mobile_camera["device_id"]
            )

            # Verify connection was established
            assert connection is not None
            assert (
                sample_mobile_camera["device_id"] in camera_service.active_connections
            )

            # Verify mobile video capture was created with correct parameters
            mock_mobile_cap.assert_called_once()
            mock_mobile_cap_instance.open.assert_called_once()

    def test_mobile_camera_type_enum(self):
        """Test that CameraType.MOBILE enum exists."""
        assert CameraType.MOBILE == "MOBILE"
        assert hasattr(CameraType, "MOBILE")

    @pytest.mark.asyncio
    async def test_mobile_streaming_status_monitoring(
        self, mobile_streaming_service, sample_mobile_camera
    ):
        """Test mobile streaming status monitoring."""

        device_id = sample_mobile_camera["device_id"]

        # Test status when no stream exists
        status = await mobile_streaming_service.get_mobile_stream_status(device_id)
        assert status is None

        # Setup a mock stream
        stream_info = {
            "device_id": device_id,
            "ip_address": sample_mobile_camera["ip_address"],
            "port": sample_mobile_camera["port"],
            "protocol": "rtmp",
            "status": "streaming",
            "last_frame_time": 1234567890,
            "stream_url": f"rtmp://{sample_mobile_camera['ip_address']}:{sample_mobile_camera['port']}/live/{device_id}",
        }

        mobile_streaming_service.active_mobile_streams[device_id] = stream_info
        mobile_streaming_service.stream_queues[device_id] = Mock()
        mobile_streaming_service.stream_queues[device_id].qsize.return_value = 5

        # Test status when stream exists
        status = await mobile_streaming_service.get_mobile_stream_status(device_id)
        assert status is not None
        assert status["device_id"] == device_id
        assert status["protocol"] == "rtmp"
        assert status["queue_size"] == 5

    @pytest.mark.asyncio
    async def test_mobile_streaming_cleanup(
        self, mobile_streaming_service, sample_mobile_camera
    ):
        """Test mobile streaming cleanup and shutdown."""

        device_id = sample_mobile_camera["device_id"]

        # Setup mock stream with cleanup requirements
        with patch("subprocess.Popen") as mock_popen, patch(
            "os.path.exists"
        ) as mock_exists, patch("os.unlink") as mock_unlink, patch(
            "os.rmdir"
        ) as mock_rmdir:

            mock_process = Mock()
            mock_popen.return_value = mock_process
            mock_exists.return_value = True

            # Setup stream
            stream_config = {
                "ip_address": sample_mobile_camera["ip_address"],
                "port": sample_mobile_camera["port"],
                "protocol": "rtmp",
            }

            # Add mock stream info
            mobile_streaming_service.active_mobile_streams[device_id] = {
                "fifo_path": "/tmp/test/stream.mkv",
                "temp_dir": "/tmp/test",
                "ffmpeg_process": mock_process,
            }
            mobile_streaming_service.rtmp_servers[device_id] = mock_process
            mobile_streaming_service.stream_queues[device_id] = Mock()

            # Test cleanup
            result = await mobile_streaming_service.stop_mobile_camera_stream(device_id)

            assert result is True
            assert device_id not in mobile_streaming_service.active_mobile_streams
            assert device_id not in mobile_streaming_service.rtmp_servers
            assert device_id not in mobile_streaming_service.stream_queues

            # Verify cleanup operations
            mock_process.terminate.assert_called_once()
            mock_unlink.assert_called_once()
            mock_rmdir.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

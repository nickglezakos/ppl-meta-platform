"""
Virtual camera capture implementation for mobile cameras.
Provides OpenCV VideoCapture-like interface for mobile camera streams.
"""

import logging
import time
from typing import Any, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class MobileVideoCapture:
    """
    OpenCV VideoCapture-like interface for mobile camera streams.
    Allows mobile cameras to work with existing streaming infrastructure.
    """

    def __init__(self, device_id: str, mobile_streaming_service):
        self.device_id = device_id
        self.mobile_streaming_service = mobile_streaming_service
        self._is_opened = False
        self._last_frame = None
        self._frame_width = 640
        self._frame_height = 480
        self._fps = 30
        self._cv_capture = None  # Initialize OpenCV capture for MJPEG streams
        self._connection_time = 0

    def isOpened(self) -> bool:
        """Check if mobile camera stream is open and active."""
        if not self._is_opened:
            return False

        # Check if mobile stream is still active
        try:
            status = self.mobile_streaming_service.get_mobile_stream_status(
                self.device_id
            )
            if status and status.get("status") == "active":
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking mobile camera status {self.device_id}: {e}")
            return False

    async def open(self) -> bool:
        """Open mobile camera stream connection."""
        try:
            # Try to setup direct MJPEG connection first
            self._reconnect_mjpeg_stream()

            # Also setup mobile streaming service as fallback
            success = await self.mobile_streaming_service.setup_mobile_camera_stream(
                self.device_id, {}
            )

            if success or (
                hasattr(self, "_cv_capture") and self._cv_capture is not None
            ):
                self._is_opened = True
                logger.info("Opened mobile camera stream for %s", self.device_id)
                return True
            else:
                logger.error(
                    "Failed to open mobile camera stream for %s", self.device_id
                )
                return False

        except Exception as e:
            logger.error("Error opening mobile camera %s: %s", self.device_id, str(e))
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from mobile camera stream."""
        if not self._is_opened:
            return False, None

        try:
            # Get the latest frame from the mobile streaming service
            # Import here to avoid circular imports
            # Try to get latest frame from the frame queue
            import asyncio

            from src.services.mobile_streaming import mobile_streaming_service

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we need to handle this differently
                # For now, return the last cached frame
                if hasattr(self, "_last_frame") and self._last_frame is not None:
                    return True, self._last_frame
                else:
                    return False, None
            else:
                # Not in async context, can await
                frame = loop.run_until_complete(
                    mobile_streaming_service.get_latest_mobile_frame(self.device_id)
                )

                if frame is not None:
                    self._last_frame = frame
                    return True, frame
                else:
                    # No frame available, return test frame
                    height, width = self._frame_height, self._frame_width
                    test_frame = np.zeros((height, width, 3), dtype=np.uint8)

                    # Add some visual indication this is a test frame
                    cv2.putText(
                        test_frame,
                        f"Mobile Camera: {self.device_id}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                    )
                    cv2.putText(
                        test_frame,
                        "Waiting for frames...",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (128, 128, 128),
                        1,
                    )

                    return True, test_frame

        except Exception as e:
            logger.error(f"Error reading mobile camera frame {self.device_id}: {e}")
            return False, None

            # Add test pattern indicating waiting for mobile stream
            cv2.putText(
                test_frame,
                "Waiting for Mobile Stream",
                (50, height // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),  # Orange color
                2,
            )
            cv2.putText(
                test_frame,
                f"{self.device_id}",
                (50, height // 2 + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                test_frame,
                f"Time: {int(time.time())}",
                (50, height // 2 + 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
            )

            self._last_frame = test_frame
            return True, test_frame

        except Exception as e:
            logger.error(
                "Error reading frame from mobile camera %s: %s", self.device_id, str(e)
            )
            return False, None

    def _reconnect_mjpeg_stream(self):
        """Try to reconnect to the mobile MJPEG stream."""
        try:
            # Close existing capture if any
            if hasattr(self, "_cv_capture") and self._cv_capture is not None:
                self._cv_capture.release()
                self._cv_capture = None

            # Get mobile camera connection details from database
            from src.database import get_db
            from src.models.camera import Camera, CameraType

            db = next(get_db())
            try:
                camera = (
                    db.query(Camera)
                    .filter(
                        Camera.device_id == self.device_id,
                        Camera.camera_type == CameraType.MOBILE,
                    )
                    .first()
                )

                if camera and camera.connection_string:
                    # Parse mobile://ip:port connection string
                    connection_string = camera.connection_string
                    if connection_string.startswith("mobile://"):
                        _, address_part = connection_string.split("mobile://", 1)
                        if ":" in address_part:
                            ip_address, port_str = address_part.split(":", 1)
                            # Try to connect to MJPEG stream
                            mjpeg_url = f"http://{ip_address}:{port_str}/stream"
                            logger.info(
                                "Attempting to connect to mobile MJPEG stream: %s",
                                mjpeg_url,
                            )

                            # Create OpenCV VideoCapture for MJPEG stream
                            self._cv_capture = cv2.VideoCapture(mjpeg_url)
                            if self._cv_capture.isOpened():
                                logger.info(
                                    "Successfully connected to mobile MJPEG stream for %s",
                                    self.device_id,
                                )
                            else:
                                logger.warning(
                                    "Failed to connect to mobile MJPEG stream for %s",
                                    self.device_id,
                                )
                                self._cv_capture = None
            finally:
                db.close()

        except Exception as e:
            logger.error(
                "Error reconnecting to mobile MJPEG stream for %s: %s",
                self.device_id,
                str(e),
            )

    def release(self):
        """Release mobile camera stream connection."""
        if self._is_opened:
            try:
                # Stop mobile streaming service
                self.mobile_streaming_service.stop_mobile_camera_stream(self.device_id)
                self._is_opened = False
                self._last_frame = None
                logger.info(f"Released mobile camera stream for {self.device_id}")
            except Exception as e:
                logger.error(f"Error releasing mobile camera {self.device_id}: {e}")

    def get(self, prop_id: int) -> float:
        """Get camera property (mimics OpenCV VideoCapture.get())."""
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self._frame_width)
        elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self._frame_height)
        elif prop_id == cv2.CAP_PROP_FPS:
            return float(self._fps)
        elif prop_id == cv2.CAP_PROP_FRAME_COUNT:
            # For live streams, frame count is not applicable
            return -1.0
        else:
            return 0.0

    def set(self, prop_id: int, value: float) -> bool:
        """Set camera property (mimics OpenCV VideoCapture.set())."""
        try:
            if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
                self._frame_width = int(value)
                return True
            elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
                self._frame_height = int(value)
                return True
            elif prop_id == cv2.CAP_PROP_FPS:
                self._fps = int(value)
                return True
            else:
                # Other properties not supported for mobile cameras
                return False
        except Exception as e:
            logger.error(
                f"Error setting property {prop_id} to {value} for mobile camera {self.device_id}: {e}"
            )
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

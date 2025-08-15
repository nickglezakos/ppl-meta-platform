"""
Camera detection and management service for PPL Meta Cameras.
"""

import asyncio
import logging
import platform
import subprocess
import uuid
from typing import Dict, List, Optional, Tuple

import cv2
from sqlalchemy.orm import Session
from src.config import get_config
from src.database import get_db
from src.models.camera import Camera, CameraStatus, CameraType

logger = logging.getLogger(__name__)
config = get_config()


class CameraDetectionService:
    """Service for detecting and managing cameras."""

    def __init__(self):
        self.detected_cameras: Dict[str, Dict] = {}
        self.active_connections: Dict[str, cv2.VideoCapture] = {}

    async def detect_available_cameras(self) -> List[Dict]:
        """Detect all available cameras on the system."""

        logger.info("Starting camera detection...")
        cameras = []

        # Detect USB/Webcam cameras
        usb_cameras = await self._detect_usb_cameras()
        cameras.extend(usb_cameras)

        # Detect IP cameras (if enabled)
        # ip_cameras = await self._detect_ip_cameras()
        # cameras.extend(ip_cameras)

        # Update detected cameras cache
        self.detected_cameras = {cam["device_id"]: cam for cam in cameras}

        logger.info(f"Detected {len(cameras)} cameras")
        return cameras

    async def _detect_usb_cameras(self) -> List[Dict]:
        """Detect USB/Webcam cameras using OpenCV."""

        cameras = []
        max_camera_index = 10  # Check first 10 camera indices

        for index in range(max_camera_index):
            try:
                # Try to open camera
                cap = cv2.VideoCapture(index)

                if cap.isOpened():
                    # Get camera properties
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)

                    # Try to read a frame to verify camera works
                    ret, frame = cap.read()

                    if ret and frame is not None:
                        device_id = f"usb_camera_{index}"
                        camera_info = {
                            "device_id": device_id,
                            "name": f"USB Camera {index}",
                            "camera_type": CameraType.USB,
                            "status": CameraStatus.AVAILABLE,
                            "resolution_width": width,
                            "resolution_height": height,
                            "max_fps": int(fps) if fps > 0 else 30,
                            "connection_string": str(index),
                            "supports_streaming": True,
                            "supports_recording": True,
                            "index": index,
                        }

                        cameras.append(camera_info)
                        logger.info(f"Detected USB camera {index}: {width}x{height}")

                cap.release()

            except Exception as e:
                logger.debug(f"Failed to check camera index {index}: {e}")
                continue

        return cameras

    async def _detect_ip_cameras(self) -> List[Dict]:
        """Detect IP cameras on the network (placeholder for future implementation)."""

        # This would involve network scanning for ONVIF devices, RTSP streams, etc.
        # For now, return empty list
        logger.info("IP camera detection not implemented yet")
        return []

    async def connect_camera(self, device_id: str) -> Optional[cv2.VideoCapture]:
        """Connect to a specific camera."""

        if device_id in self.active_connections:
            logger.warning(f"Camera {device_id} already connected")
            return self.active_connections[device_id]

        # First check detected cameras (USB cameras)
        camera_info = self.detected_cameras.get(device_id)

        try:
            if camera_info:
                # Handle USB cameras from detected cameras
                if camera_info["camera_type"] == CameraType.USB:
                    index = int(camera_info["connection_string"])
                    cap = cv2.VideoCapture(index)

                    if cap.isOpened():
                        self.active_connections[device_id] = cap
                        logger.info(f"Connected to USB camera {device_id}")
                        return cap
                    else:
                        logger.error(f"Failed to open USB camera {device_id}")
                        return None
            else:
                # Camera not in detected cameras, check if it's RTSP camera in database
                db_gen = get_db()
                db = next(db_gen)
                try:
                    camera = (
                        db.query(Camera).filter(Camera.device_id == device_id).first()
                    )
                    if camera and camera.camera_type == CameraType.RTSP:
                        # Handle RTSP camera connection
                        # For RTSP cameras, we need to construct RTSP URL from stored data
                        # The connection_string should contain the RTSP URL
                        rtsp_url = camera.connection_string
                        if not rtsp_url:
                            logger.error(
                                f"RTSP camera {device_id} has no connection string"
                            )
                            return None

                        # URL decode the RTSP URL (e.g., %40 -> @)
                        from urllib.parse import unquote

                        decoded_rtsp_url = unquote(rtsp_url)

                        logger.info(
                            f"Connecting to RTSP camera {device_id} at {decoded_rtsp_url}"
                        )
                        # Try with explicit FFMPEG backend for better RTSP support
                        cap = cv2.VideoCapture(decoded_rtsp_url, cv2.CAP_FFMPEG)

                        if cap.isOpened():
                            self.active_connections[device_id] = cap
                            logger.info(f"Connected to RTSP camera {device_id}")
                            return cap
                        else:
                            logger.error(
                                f"Failed to open RTSP camera {device_id} at {decoded_rtsp_url}"
                            )
                            return None
                    else:
                        logger.error(
                            f"Camera {device_id} not found in detected cameras or database"
                        )
                        return None
                finally:
                    db.close()

        except Exception as e:
            logger.error(f"Error connecting to camera {device_id}: {e}")
            return None

    async def disconnect_camera(self, device_id: str) -> bool:
        """Disconnect from a specific camera."""

        if device_id not in self.active_connections:
            logger.warning(f"Camera {device_id} not connected")
            return False

        try:
            cap = self.active_connections[device_id]
            cap.release()
            del self.active_connections[device_id]
            logger.info(f"Disconnected from camera {device_id}")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting camera {device_id}: {e}")
            return False

    async def get_camera_stream(self, device_id: str) -> Optional[cv2.VideoCapture]:
        """Get active camera stream for reading frames."""

        return self.active_connections.get(device_id)

    async def capture_frame(self, device_id: str) -> Optional[Tuple[bool, any]]:
        """Capture a single frame from camera."""

        cap = await self.get_camera_stream(device_id)
        if not cap:
            logger.error(f"Camera {device_id} not connected")
            return None

        try:
            ret, frame = cap.read()
            return (ret, frame)

        except Exception as e:
            logger.error(f"Error capturing frame from camera {device_id}: {e}")
            return None

    async def get_camera_info(self, device_id: str) -> Optional[Dict]:
        """Get detailed information about a camera."""

        return self.detected_cameras.get(device_id)

    async def list_active_connections(self) -> List[str]:
        """List all active camera connections."""

        return list(self.active_connections.keys())

    async def disconnect_all(self) -> None:
        """Disconnect all active camera connections."""

        logger.info("Disconnecting all cameras...")

        for device_id in list(self.active_connections.keys()):
            await self.disconnect_camera(device_id)

        logger.info("All cameras disconnected")

    async def save_cameras_to_db(self, db: Session) -> int:
        """Save detected cameras to database."""

        saved_count = 0

        for device_id, camera_info in self.detected_cameras.items():
            try:
                # Check if camera already exists
                existing_camera = (
                    db.query(Camera).filter(Camera.device_id == device_id).first()
                )

                if existing_camera:
                    # Update existing camera
                    existing_camera.status = CameraStatus.AVAILABLE
                    existing_camera.last_seen = camera_info.get("last_seen")
                    # Update other properties as needed
                else:
                    # Create new camera
                    new_camera = Camera(
                        name=camera_info["name"],
                        device_id=device_id,
                        camera_type=camera_info["camera_type"],
                        status=camera_info["status"],
                        resolution_width=camera_info.get("resolution_width"),
                        resolution_height=camera_info.get("resolution_height"),
                        max_fps=camera_info.get("max_fps"),
                        connection_string=camera_info.get("connection_string"),
                        supports_streaming=camera_info.get("supports_streaming", True),
                        supports_recording=camera_info.get("supports_recording", True),
                    )

                    db.add(new_camera)

                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving camera {device_id} to database: {e}")
                continue

        try:
            db.commit()
            logger.info(f"Saved {saved_count} cameras to database")
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing cameras to database: {e}")
            saved_count = 0

        return saved_count

    async def get_camera_capabilities(self, device_id: str) -> Optional[Dict]:
        """Get camera's native capabilities including maximum resolution."""

        camera_info = self.detected_cameras.get(device_id)
        if not camera_info:
            logger.warning(
                f"Camera {device_id} not found in detected cameras, attempting to detect..."
            )
            # Try to detect cameras first
            await self.detect_available_cameras()
            camera_info = self.detected_cameras.get(device_id)

            if not camera_info:
                logger.error(f"Camera {device_id} still not found after detection")
                return None

        try:
            import cv2

            index = camera_info.get("index", 0)

            # Test different resolutions to find maximum supported
            test_resolutions = [
                (3840, 2160),  # 4K UHD
                (2560, 1440),  # 2K QHD
                (1920, 1080),  # Full HD
                (1280, 720),  # HD
                (1024, 768),  # XGA
                (800, 600),  # SVGA
                (640, 480),  # VGA
            ]

            supported_resolutions = []
            max_resolution = None

            # Create temporary connection for testing
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                logger.error(
                    f"Failed to open camera {device_id} for capability detection"
                )
                return None

            for width, height in test_resolutions:
                # Set resolution
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

                # Read actual resolution
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Test if we can actually capture at this resolution
                ret, frame = cap.read()
                if ret and frame is not None:
                    if actual_width == width and actual_height == height:
                        resolution_info = {
                            "width": actual_width,
                            "height": actual_height,
                        }
                        supported_resolutions.append(resolution_info)

                        # Set max resolution to the first (highest) working resolution
                        if max_resolution is None:
                            max_resolution = resolution_info

                        logger.info(f"Camera {device_id} supports {width}x{height}")
                    else:
                        logger.debug(
                            f"Camera {device_id} requested {width}x{height}, got {actual_width}x{actual_height}"
                        )
                else:
                    logger.debug(
                        f"Camera {device_id} failed to capture at {width}x{height}"
                    )

            cap.release()

            # Get current stream resolution if active
            current_stream_resolution = None
            active_cap = self.active_connections.get(device_id)
            if active_cap:
                current_width = int(active_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                current_height = int(active_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                current_stream_resolution = {
                    "width": current_width,
                    "height": current_height,
                }

            capabilities = {
                "device_id": device_id,
                "max_resolution": max_resolution or {"width": 640, "height": 480},
                "supported_resolutions": supported_resolutions
                or [{"width": 640, "height": 480}],
                "supports_formats": ["JPEG", "PNG", "BMP"],
                "current_stream_resolution": current_stream_resolution,
            }

            logger.info(
                f"Camera {device_id} capabilities: max {max_resolution}, {len(supported_resolutions)} supported"
            )
            return capabilities

        except Exception as e:
            logger.error(f"Error detecting capabilities for camera {device_id}: {e}")
            return None

    async def capture_high_res_snapshot(
        self, device_id: str, settings: Dict
    ) -> Optional[Tuple[bool, any, Dict]]:
        """Capture snapshot at specified resolution, independent of streaming resolution."""

        try:
            import time

            import cv2

            camera_info = self.detected_cameras.get(device_id)
            if not camera_info:
                logger.error(f"Camera {device_id} not found")
                return None

            index = camera_info.get("index", 0)

            # Determine target resolution
            resolution = settings.get("resolution", "max")
            target_width, target_height = await self._resolve_target_resolution(
                device_id, resolution
            )

            if not target_width or not target_height:
                logger.error(f"Could not resolve target resolution for {device_id}")
                return None

            # Create temporary high-resolution connection
            logger.info(
                f"Creating high-res connection for {device_id} at {target_width}x{target_height}"
            )
            temp_cap = cv2.VideoCapture(index)

            if not temp_cap.isOpened():
                logger.error(f"Failed to create high-res connection for {device_id}")
                return None

            try:
                # Set target resolution
                temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
                temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)

                # Allow camera to adjust
                time.sleep(0.1)

                # Capture frame
                ret, frame = temp_cap.read()

                if ret and frame is not None:
                    actual_width = int(temp_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(temp_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                    metadata = {
                        "requested_resolution": f"{target_width}x{target_height}",
                        "actual_resolution": f"{actual_width}x{actual_height}",
                        "capture_time": time.time(),
                        "settings": settings,
                    }

                    logger.info(
                        f"High-res snapshot captured: {actual_width}x{actual_height}"
                    )
                    return (True, frame, metadata)
                else:
                    logger.error(f"Failed to capture high-res frame from {device_id}")
                    return None

            finally:
                temp_cap.release()

        except Exception as e:
            logger.error(f"Error in high-res snapshot capture for {device_id}: {e}")
            return None

    async def _resolve_target_resolution(
        self, device_id: str, resolution: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """Resolve target resolution from settings."""

        if resolution == "max":
            # Get maximum supported resolution
            capabilities = await self.get_camera_capabilities(device_id)
            if capabilities and capabilities.get("max_resolution"):
                max_res = capabilities["max_resolution"]
                return max_res.get("width"), max_res.get("height")

        elif resolution == "stream":
            # Use current streaming resolution
            active_cap = self.active_connections.get(device_id)
            if active_cap:
                width = int(active_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(active_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                return width, height

        elif "x" in resolution:
            # Parse WIDTHxHEIGHT format
            try:
                width, height = resolution.split("x")
                return int(width), int(height)
            except (ValueError, IndexError):
                logger.error(f"Invalid resolution format: {resolution}")
                return None, None

        # Fallback to default
        logger.warning(f"Could not resolve resolution '{resolution}', using default")
        return 1280, 720


# Global camera detection service instance
camera_service = CameraDetectionService()

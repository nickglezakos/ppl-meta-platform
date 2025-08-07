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

        camera_info = self.detected_cameras.get(device_id)
        if not camera_info:
            logger.error(f"Camera {device_id} not found in detected cameras")
            return None

        try:
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

            # TODO: Handle IP cameras, RTSP streams, etc.

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


# Global camera detection service instance
camera_service = CameraDetectionService()

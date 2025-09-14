"""
Camera detection and management service for PPL Meta Cameras.
"""

import asyncio
import datetime
import logging
import os
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
        self.active_recordings: Dict[str, Dict] = {}  # Track active recordings
        # Store latest frames for each camera (device_id -> (ret, frame))
        self.latest_frames: Dict[str, Tuple] = {}

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

        # Check if this is a mobile camera - mobile cameras should not be
        # connected via backend
        db_gen = get_db()
        db = next(db_gen)
        try:
            camera = db.query(Camera).filter(Camera.device_id == device_id).first()
            if camera and camera.camera_type == CameraType.MOBILE:
                logger.info(
                    f"Skipping backend connection for mobile camera {device_id} "
                    "- mobile cameras use direct frontend access"
                )
                return None
        finally:
            db.close()

        # First check detected cameras (USB cameras)
        camera_info = self.detected_cameras.get(device_id)

        try:
            if camera_info:
                # Handle USB cameras from detected cameras
                if camera_info["camera_type"] == CameraType.USB:
                    index = int(camera_info["connection_string"])

                    # For USB cameras, ensure proper initialization
                    # to avoid black screen
                    cap = cv2.VideoCapture(index)

                    # Wait a moment for camera to initialize
                    await asyncio.sleep(0.1)

                    if cap.isOpened():
                        # Set properties to ensure proper frame capture
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer
                        cap.set(cv2.CAP_PROP_FPS, 30)  # Set frame rate

                        # Read and discard first few frames to ensure
                        # fresh frames
                        for _ in range(3):
                            ret, _ = cap.read()
                            if not ret:
                                break

                        self.active_connections[device_id] = cap
                        logger.info(
                            "Connected to USB camera %s with fresh init", device_id
                        )
                        return cap
                    else:
                        logger.error("Failed to open USB camera %s", device_id)
                        cap.release()
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
                    elif camera and camera.camera_type == CameraType.MOBILE:
                        # Handle mobile camera connection
                        from src.services.mobile_capture import MobileVideoCapture
                        from src.services.mobile_streaming import (
                            mobile_streaming_service,
                        )

                        # Extract mobile camera connection details
                        connection_string = camera.connection_string  # mobile://ip:port
                        if not connection_string or not connection_string.startswith(
                            "mobile://"
                        ):
                            logger.error(
                                f"Invalid mobile camera connection string for {device_id}"
                            )
                            return None

                        # Parse connection string: mobile://ip:port
                        try:
                            _, address_part = connection_string.split("mobile://", 1)
                            ip_address, port_str = address_part.split(":")
                            port = int(port_str)
                        except ValueError:
                            logger.error(
                                f"Failed to parse mobile camera connection string: {connection_string}"
                            )
                            return None

                        # Create mobile stream configuration
                        stream_config = {
                            "ip_address": ip_address,
                            "port": port,
                            "protocol": "rtmp",  # Default to RTMP for mobile cameras
                            "width": camera.resolution_width or 640,
                            "height": camera.resolution_height or 480,
                            "fps": camera.max_fps or 30,
                        }

                        # Create mobile video capture instance
                        mobile_cap = MobileVideoCapture(
                            device_id, mobile_streaming_service
                        )

                        # Open mobile camera stream
                        success = await mobile_cap.open()
                        if success:
                            self.active_connections[device_id] = mobile_cap
                            logger.info(f"Connected to mobile camera {device_id}")
                            return mobile_cap
                        else:
                            logger.error(
                                f"Failed to connect to mobile camera {device_id}"
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
            # Store the latest frame for recording use
            if ret and frame is not None:
                self.latest_frames[device_id] = (ret, frame.copy())
            return (ret, frame)

        except Exception as e:
            logger.error(f"Error capturing frame from camera {device_id}: {e}")
            return None

    async def get_latest_frame(self, device_id: str) -> Optional[Tuple[bool, any]]:
        """Get the latest cached frame for a camera."""
        return self.latest_frames.get(device_id)

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

    # ==========================================
    # VIDEO RECORDING METHODS
    # ==========================================

    async def start_recording(
        self,
        device_id: str,
        user_id: str,
        quality: str = "high",
        auth_token: Optional[str] = None,
    ) -> Optional[Dict]:
        """Start recording video from camera using existing stream frames."""

        try:
            # Check if already recording
            if device_id in self.active_recordings:
                logger.warning(f"Camera {device_id} is already recording")
                return None

            # Check if this is a mobile camera - handle differently
            db_gen = get_db()
            db = next(db_gen)
            try:
                camera = db.query(Camera).filter(Camera.device_id == device_id).first()
                is_mobile = camera and camera.camera_type == CameraType.MOBILE
            finally:
                db.close()

            if is_mobile:
                # For mobile cameras, check if we're receiving frames instead of active connections
                from src.services.mobile_streaming import mobile_streaming_service

                if not mobile_streaming_service.has_active_mobile_camera(device_id):
                    logger.error(
                        f"Mobile camera {device_id} not streaming for recording"
                    )
                    return None

                return await self._start_mobile_recording(
                    device_id, user_id, quality, auth_token
                )
            else:
                # For USB/RTSP cameras, check active connections
                if device_id not in self.active_connections:
                    logger.error(f"Camera {device_id} not connected for recording")
                    return None

                return await self._start_regular_recording(
                    device_id, user_id, quality, auth_token
                )

        except Exception as e:
            logger.error("Error starting recording for camera %s: %s", device_id, e)
            return None

    async def _start_regular_recording(
        self,
        device_id: str,
        user_id: str,
        quality: str,
        auth_token: Optional[str] = None,
    ) -> Optional[Dict]:
        """Start recording for USB/RTSP cameras using stream frames."""
        logger.info(f"🎬 [DEBUG] Starting USB/RTSP recording for {device_id}")
        logger.info(f"🎬 [DEBUG] User ID: {user_id}, Quality: {quality}")

        cap = self.active_connections[device_id]
        logger.info(f"🎬 [DEBUG] Retrieved camera connection for {device_id}")

        # Get recording parameters based on current stream settings
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        logger.info(
            f"🎬 [DEBUG] Camera properties - Width: {width}, Height: {height}, FPS: {fps}"
        )

        # Generate recording file path
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{device_id}_{timestamp}.mp4"
        recordings_dir = os.path.join("recordings", device_id)
        os.makedirs(recordings_dir, exist_ok=True)
        file_path = os.path.join(recordings_dir, filename)
        logger.info(f"🎬 [DEBUG] Recording file path: {file_path}")

        # Initialize video writer with H.264 codec for web compatibility
        # Use H.264 codec for better web player support (Flutter video_player)
        fourcc = cv2.VideoWriter_fourcc(*"H264")
        logger.info(f"🎬 [DEBUG] Using fourcc codec: H264")
        video_writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

        if not video_writer.isOpened():
            logger.error(
                f"🎬 [DEBUG] ❌ CRITICAL: Failed to initialize video writer for {device_id}"
            )
            return None

        logger.info(
            f"🎬 [DEBUG] ✅ Video writer initialized successfully for {device_id}: {width}x{height} at {fps} fps"
        )

        # Store recording info
        recording_id = str(uuid.uuid4())
        logger.info(f"🎬 [DEBUG] Generated recording ID: {recording_id}")

        recording_info = {
            "recording_id": recording_id,
            "device_id": device_id,
            "user_id": user_id,
            "file_path": file_path,
            "video_writer": video_writer,
            "started_at": datetime.datetime.now(),
            "frame_count": 0,
            "quality": quality,
            "resolution": f"{width}x{height}",
            "fps": fps,
            "is_mobile": False,
            "auth_token": auth_token,
        }
        logger.info(f"🎬 [DEBUG] Recording info created for {device_id}")

        self.active_recordings[device_id] = recording_info
        logger.info(f"🎬 [DEBUG] Added recording to active_recordings for {device_id}")

        # Start frame recording task
        asyncio.create_task(self._frame_recording_loop(device_id))
        logger.info(f"🎬 [DEBUG] Frame recording loop task created for {device_id}")

        logger.info(
            f"🎬 [DEBUG] Recording started for camera {device_id} to {file_path}"
        )

        return {
            "recording_id": recording_id,
            "started_at": recording_info["started_at"].isoformat(),
            "file_path": file_path,
        }

    async def _start_mobile_recording(
        self,
        device_id: str,
        user_id: str,
        quality: str,
        auth_token: Optional[str] = None,
    ) -> Optional[Dict]:
        """Start recording for mobile cameras using frame data from mobile service."""

        # Get quality settings for mobile recording
        quality_settings = {
            "low": (320, 240, 15),
            "medium": (640, 480, 30),
            "high": (1280, 720, 30),
            "ultra": (1920, 1080, 30),
        }

        width, height, fps = quality_settings.get(quality, quality_settings["medium"])

        # Generate recording file path
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mobile_recording_{device_id}_{timestamp}.mp4"
        recordings_dir = os.path.join("recordings", device_id)
        os.makedirs(recordings_dir, exist_ok=True)
        file_path = os.path.join(recordings_dir, filename)

        # Initialize video writer with H.264 codec for web compatibility
        fourcc = cv2.VideoWriter_fourcc(*"H264")
        video_writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

        if not video_writer.isOpened():
            logger.error(f"Failed to initialize video writer for mobile {device_id}")
            return None

        # Store recording info
        recording_id = str(uuid.uuid4())
        recording_info = {
            "recording_id": recording_id,
            "device_id": device_id,
            "user_id": user_id,
            "file_path": file_path,
            "video_writer": video_writer,
            "started_at": datetime.datetime.now(),
            "frame_count": 0,
            "quality": quality,
            "resolution": f"{width}x{height}",
            "fps": fps,
            "is_mobile": True,
            "target_size": (width, height),
            "auth_token": auth_token,
        }

        self.active_recordings[device_id] = recording_info

        # Start mobile frame recording task
        asyncio.create_task(self._mobile_recording_loop(device_id))

        logger.info(
            "Started mobile recording for camera %s to %s", device_id, file_path
        )

        return {
            "recording_id": recording_id,
            "started_at": recording_info["started_at"].isoformat(),
            "file_path": file_path,
        }

    async def stop_recording(self, device_id: str, user_id: str) -> Optional[Dict]:
        """Stop recording video from camera and finalize file."""
        logger.info(f"🎬 [DEBUG] Stop recording requested for {device_id}")

        try:
            if device_id not in self.active_recordings:
                logger.warning(f"🎬 [DEBUG] ⚠️ Camera {device_id} is not recording")
                return None

            recording_info = self.active_recordings[device_id]
            logger.info(f"🎬 [DEBUG] Found active recording for {device_id}")

            # Finalize recording
            video_writer = recording_info["video_writer"]
            logger.info(f"🎬 [DEBUG] Releasing video writer for {device_id}")
            video_writer.release()

            # Calculate final stats
            stopped_at = datetime.datetime.now()
            duration = stopped_at - recording_info["started_at"]
            logger.info(
                f"🎬 [DEBUG] Recording duration: {duration.total_seconds():.1f}s"
            )

            # Get file size
            file_size = os.path.getsize(recording_info["file_path"])
            logger.info(f"🎬 [DEBUG] Recording file size: {file_size} bytes")

            # Clean up recording info
            del self.active_recordings[device_id]
            logger.info(f"🎬 [DEBUG] Removed {device_id} from active recordings")

            # TODO: Upload to media service and assign to camera collection
            logger.info(f"🎬 [DEBUG] Starting upload to collection for {device_id}")
            collection_id = await self._upload_recording_to_collection(
                recording_info, user_id
            )
            logger.info(f"🎬 [DEBUG] Upload completed, collection_id: {collection_id}")

            logger.info(
                "Stopped recording for camera %s - "
                "Duration: %.1fs, Frames: %s, Size: %s bytes",
                device_id,
                duration.total_seconds(),
                recording_info["frame_count"],
                file_size,
            )

            result = {
                "recording_id": recording_info["recording_id"],
                "duration_seconds": int(duration.total_seconds()),
                "frame_count": recording_info["frame_count"],
                "file_path": recording_info["file_path"],
                "file_size_bytes": file_size,
                "collection_id": collection_id,
                "stopped_at": stopped_at.isoformat(),
            }
            logger.info(
                f"🎬 [DEBUG] ✅ Stop recording complete for {device_id}: {result}"
            )
            return result

        except Exception as e:
            logger.error(f"🎬 [DEBUG] ❌ Error stopping recording for {device_id}: {e}")
            return None

    def get_active_recording(self, device_id: str) -> Optional[Dict]:
        """Get active recording info for a camera."""
        return self.active_recordings.get(device_id)

    def get_recording_status(self, device_id: str) -> Dict:
        """Get recording status for a camera."""

        recording_info = self.active_recordings.get(device_id)

        if not recording_info:
            return {
                "is_recording": False,
                "recording_id": None,
                "started_at": None,
                "duration_seconds": 0,
                "file_size_bytes": 0,
            }

        # Calculate current duration
        current_time = datetime.datetime.now()
        duration = current_time - recording_info["started_at"]

        # Estimate file size (rough approximation)
        # ~50KB per frame estimate
        estimated_size = recording_info["frame_count"] * 50000

        return {
            "is_recording": True,
            "recording_id": recording_info["recording_id"],
            "started_at": recording_info["started_at"].isoformat(),
            "duration_seconds": int(duration.total_seconds()),
            "file_size_bytes": estimated_size,
            "frame_count": recording_info["frame_count"],
        }

    async def _frame_recording_loop(self, device_id: str):
        """Record frames as continuous video stream for USB/RTSP cameras."""
        logger.info(f"🎬 [DEBUG] Starting frame recording loop for {device_id}")

        try:
            recording_info = self.active_recordings.get(device_id)
            if not recording_info:
                logger.error(f"🎬 [DEBUG] ❌ No recording info found for {device_id}")
                return

            video_writer = recording_info["video_writer"]
            target_fps = recording_info["fps"]
            cap = self.active_connections[device_id]
            frame_interval = 1.0 / target_fps  # Target time between frames
            max_consecutive_failures = 10
            failure_count = 0

            logger.info(f"🎬 [DEBUG] Recording loop initialized for {device_id}")
            logger.info(
                f"🎬 [DEBUG] Target FPS: {target_fps}, Frame interval: {frame_interval:.3f}s"
            )

            logger.info(
                "Starting continuous video recording for camera %s at %d fps",
                device_id,
                target_fps,
            )

            frame_write_count = 0
            while device_id in self.active_recordings:
                try:
                    # Read frame directly from camera with timeout protection
                    ret, frame = cap.read()

                    if not ret or frame is None:
                        failure_count += 1
                        logger.warning(
                            f"🎬 [DEBUG] ⚠️ Failed to read frame {failure_count} for {device_id}"
                        )

                        # Break if too many consecutive failures
                        if failure_count >= max_consecutive_failures:
                            logger.error(
                                f"🎬 [DEBUG] ❌ Too many frame read failures ({failure_count}), stopping recording for {device_id}"
                            )
                            break

                        # Don't sleep too long on frame read failures
                        await asyncio.sleep(0.1)
                        continue

                    # Reset failure count on successful read
                    failure_count = 0
                    frame_write_count += 1

                    # Write frame immediately for continuous stream
                    video_writer.write(frame)
                    recording_info["frame_count"] += 1

                    # Log progress every 30 frames (about 1 second at 30fps)
                    if frame_write_count % 30 == 0:
                        logger.info(
                            f"🎬 [DEBUG] ✅ Wrote {frame_write_count} frames for {device_id}"
                        )

                    # Use async sleep for proper event loop handling
                    await asyncio.sleep(frame_interval)

                except Exception as frame_error:
                    logger.warning(
                        f"🎬 [DEBUG] ⚠️ Frame processing error for {device_id}: {frame_error}"
                    )
                    await asyncio.sleep(0.1)

            logger.info(
                f"🎬 [DEBUG] ✅ Recording loop ended for {device_id}, total frames: {recording_info['frame_count']}"
            )
            logger.info(
                "Continuous video recording ended for camera %s, wrote %d frames",
                device_id,
                recording_info["frame_count"],
            )

        except Exception as e:
            logger.error(
                f"🎬 [DEBUG] ❌ CRITICAL: Error in video recording loop for {device_id}: {e}"
            )
        finally:
            # Always clean up on exit
            if device_id in self.active_recordings:
                recording_info = self.active_recordings[device_id]
                try:
                    recording_info["video_writer"].release()
                except Exception:
                    pass
                del self.active_recordings[device_id]

    async def _mobile_recording_loop(self, device_id: str):
        """Record frames from mobile camera stream data."""

        try:
            recording_info = self.active_recordings.get(device_id)
            if not recording_info:
                logger.error(
                    f"🎬 [MOBILE_RECORDING] No recording info found for {device_id}"
                )
                return

            video_writer = recording_info["video_writer"]
            target_fps = recording_info["fps"]
            target_size = recording_info["target_size"]

            logger.info(
                f"🎬 [MOBILE_RECORDING] Starting mobile recording loop for camera {device_id}"
            )
            logger.info(
                f"🎬 [MOBILE_RECORDING] Target FPS: {target_fps}, Target size: {target_size}"
            )

            # Import mobile streaming service
            from src.services.mobile_streaming import mobile_streaming_service

            frame_count = 0
            while device_id in self.active_recordings:
                # Get frame data from mobile streaming service
                frame_data = (
                    await mobile_streaming_service.get_latest_mobile_frame_data(
                        device_id
                    )
                )

                if frame_data is None:
                    logger.debug(
                        f"🎬 [MOBILE_RECORDING] No mobile frame available for recording {device_id}"
                    )
                    await asyncio.sleep(0.1)
                    continue

                logger.debug(
                    f"🎬 [MOBILE_RECORDING] Got frame data for {device_id}: {type(frame_data)}"
                )

                frame = frame_data["frame"]
                rotation_angle = frame_data.get("rotation_angle", 0)

                logger.debug(
                    f"🎬 [MOBILE_RECORDING] Frame shape: {frame.shape}, rotation: {rotation_angle}"
                )

                # Apply rotation if needed
                if rotation_angle != 0:
                    if rotation_angle == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif rotation_angle == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif rotation_angle == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

                # Resize frame to target recording size
                if frame.shape[1] != target_size[0] or frame.shape[0] != target_size[1]:
                    frame = cv2.resize(frame, target_size)

                # Write frame to video file
                video_writer.write(frame)
                recording_info["frame_count"] += 1
                frame_count += 1

                if frame_count % 30 == 0:  # Log every 30 frames
                    logger.info(
                        f"🎬 [MOBILE_RECORDING] Recorded {frame_count} frames for {device_id}"
                    )

                # Control frame rate
                await asyncio.sleep(1.0 / target_fps)

            logger.info(
                f"🎬 [MOBILE_RECORDING] Mobile recording loop ended for camera {device_id} with {frame_count} frames"
            )

        except Exception as e:
            logger.error(
                "Error in mobile recording loop for camera %s: %s", device_id, e
            )
            # Clean up on error
            if device_id in self.active_recordings:
                recording_info = self.active_recordings[device_id]
                recording_info["video_writer"].release()
                del self.active_recordings[device_id]

    async def _upload_recording_to_collection(
        self, recording_info: Dict, user_id: str
    ) -> Optional[str]:
        """Upload recorded video to media service and assign to collection."""
        logger.info(f"🎬 [DEBUG] Starting upload process for recording")
        from pathlib import Path

        import aiofiles
        import aiohttp

        try:
            file_path = recording_info["file_path"]
            device_id = recording_info["device_id"]
            logger.info(f"🎬 [DEBUG] Upload file: {file_path}, device: {device_id}")

            logger.info(
                "Uploading recording %s to collection for camera %s " "(user: %s)",
                file_path,
                device_id,
                user_id,
            )

            # Get media service URL
            MEDIA_SERVICE_URL = "http://localhost:8000"
            logger.info(f"🎬 [DEBUG] Media service URL: {MEDIA_SERVICE_URL}")

            # Get file info
            path_obj = Path(file_path)
            if not path_obj.exists():
                logger.error(f"🎬 [DEBUG] ❌ Recording file not found: {file_path}")
                return None

            file_size = path_obj.stat().st_size
            logger.info(f"🎬 [DEBUG] File exists, size: {file_size} bytes")

            duration = recording_info.get("duration", 0)
            frame_count = recording_info.get("frame_count", 0)
            fps = recording_info.get("fps", 30)
            logger.info(
                f"🎬 [DEBUG] Video metadata - Duration: {duration}s, Frames: {frame_count}, FPS: {fps}"
            )

            # Read file content
            logger.info(f"🎬 [DEBUG] Reading file content...")
            async with aiofiles.open(file_path, "rb") as file:
                file_content = await file.read()
            logger.info(f"🎬 [DEBUG] ✅ File content read: {len(file_content)} bytes")

            # Upload to media service
            async with aiohttp.ClientSession() as session:
                # Set JWT token for authentication
                headers = {}
                auth_token = recording_info.get("auth_token")
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}"
                    logger.info(f"🎬 [DEBUG] ✅ Using auth token for media upload")
                else:
                    logger.warning(
                        f"🎬 [DEBUG] ⚠️ No auth token available for media upload"
                    )

                # Get user GUID from user profile since media service needs UUID format
                user_guid = None
                if auth_token:
                    logger.info(f"🎬 [DEBUG] Getting user profile for GUID...")
                    try:
                        async with session.get(
                            "http://localhost:8001/api/v1/users/profile",
                            headers={"Authorization": f"Bearer {auth_token}"},
                        ) as profile_response:
                            if profile_response.status == 200:
                                profile_data = await profile_response.json()
                                user_guid = profile_data.get("guid")
                                logger.info(
                                    f"🎬 [DEBUG] ✅ Retrieved user GUID: {user_guid}"
                                )
                            else:
                                logger.warning(
                                    f"🎬 [DEBUG] ⚠️ Failed to get user profile for GUID: {profile_response.status}"
                                )
                    except Exception as profile_error:
                        logger.warning(
                            f"🎬 [DEBUG] ⚠️ Error getting user profile: {profile_error}"
                        )

                # Use GUID if available, otherwise fall back to original user_id
                final_user_id = user_guid if user_guid else user_id
                logger.info(f"🎬 [DEBUG] Final user ID for upload: {final_user_id}")

                logger.info(f"🎬 [DEBUG] Preparing upload form data...")
                data = aiohttp.FormData()
                data.add_field(
                    "file",
                    file_content,
                    filename=f"camera_{device_id}_{path_obj.name}",
                    content_type="video/mp4",
                )
                # Required fields
                data.add_field("media_type", "video")
                data.add_field("user_id", final_user_id)

                # Optional fields
                title = f"Camera Recording - {device_id}"
                description = f"Camera recording from {device_id} ({duration:.1f}s, {frame_count} frames, {fps} fps)"
                data.add_field("title", title)
                data.add_field("description", description)
                data.add_field("tags", f'["camera","recording","{device_id}"]')
                data.add_field("is_public", "false")

                logger.info(f"🎬 [DEBUG] Upload form prepared - Title: {title}")
                logger.info(f"🎬 [DEBUG] Description: {description}")

                try:
                    logger.info(f"🎬 [DEBUG] 🚀 Starting HTTP POST to media service...")
                    async with session.post(
                        f"{MEDIA_SERVICE_URL}/api/v1/media/upload",
                        data=data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        logger.info(
                            f"🎬 [DEBUG] Upload response status: {response.status}"
                        )

                        if response.status == 200:
                            result = await response.json()
                            media_id = result.get("id")
                            media_uuid = result.get("uuid")
                            logger.info(
                                f"🎬 [DEBUG] ✅ Successfully uploaded! "
                                f"Media ID: {media_id}, UUID: {media_uuid}"
                            )
                            logger.info(
                                "Successfully uploaded recording %s " "as media %s",
                                file_path,
                                media_id,
                            )

                            # Find or create camera collection and assign video
                            logger.info(
                                f"🎬 [DEBUG] Finding/creating camera collection..."
                            )
                            collection_id = (
                                await self._find_or_create_camera_collection(
                                    device_id, final_user_id, session, headers
                                )
                            )
                            logger.info(
                                f"🎬 [DEBUG] Collection found/created: {collection_id}"
                            )

                            if collection_id:
                                # Assign uploaded video to camera collection
                                logger.info(
                                    f"🎬 [DEBUG] Assigning media to collection..."
                                )
                                await self._assign_media_to_collection(
                                    media_uuid,  # Use UUID instead of integer ID
                                    collection_id,
                                    final_user_id,
                                    session,
                                    headers,
                                )
                                logger.info(
                                    f"🎬 [DEBUG] ✅ Media assigned to collection"
                                )
                                logger.info(
                                    "Assigned media %s to camera collection %s",
                                    media_id,
                                    collection_id,
                                )
                            else:
                                logger.warning(
                                    f"🎬 [DEBUG] ⚠️ Could not find or create collection for camera {device_id}"
                                )

                            # Clean up local file after successful upload
                            try:
                                logger.info(f"🎬 [DEBUG] Cleaning up local file...")
                                path_obj.unlink()
                                logger.info(
                                    f"🎬 [DEBUG] ✅ Local file cleaned up: {file_path}"
                                )
                            except Exception as cleanup_error:
                                logger.warning(
                                    f"🎬 [DEBUG] ⚠️ Failed to clean up file {file_path}: {cleanup_error}"
                                )

                            return collection_id
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"🎬 [DEBUG] ❌ Upload failed: {response.status} - {error_text}"
                            )
                            logger.error(
                                "Failed to upload recording %s: %s %s",
                                file_path,
                                response.status,
                                error_text,
                            )
                            return None

                except aiohttp.ClientError as http_error:
                    logger.error(
                        "HTTP error uploading recording %s: %s", file_path, http_error
                    )
                    return None

        except Exception as e:
            logger.error(
                "Error uploading recording %s to collection: %s",
                recording_info.get("file_path", "unknown"),
                e,
            )
            return None

    async def _find_or_create_camera_collection(
        self, device_id: str, user_id: str, session, headers: Dict
    ) -> Optional[str]:
        """Find existing or create camera collection using database lookup."""
        import aiohttp

        try:
            logger.info(
                f"🔍 [COLLECTION] Looking for existing collection for camera {device_id}"
            )

            # First, try to find existing collection by camera device ID
            async with session.get(
                f"http://localhost:8000/api/v1/media/collections/by-camera/{device_id}",
                headers=headers,
            ) as response:
                if response.status == 200:
                    collection_data = await response.json()
                    if collection_data:  # Collection found
                        collection_uuid = collection_data.get("uuid")
                        collection_name = collection_data.get("name")
                        logger.info(
                            f"🔍 [COLLECTION] ✅ Found existing collection "
                            f"'{collection_name}' (UUID: {collection_uuid}) "
                            f"for camera {device_id}"
                        )
                        return collection_uuid

            # No existing collection found, create new one
            collection_name = f"{device_id} Collection"

            logger.info(
                f"🔍 [COLLECTION] Creating new collection '{collection_name}' "
                f"for camera {device_id}"
            )

            data = aiohttp.FormData()
            data.add_field("name", collection_name)
            data.add_field("description", f"Media collection for camera {device_id}")
            data.add_field("user_id", user_id)
            data.add_field("is_public", "false")
            data.add_field("camera_device_id", device_id)  # Link to camera
            data.add_field("description", f"Collection for camera: {device_id}")
            data.add_field("user_id", user_id)
            data.add_field("is_public", "false")

            async with session.post(
                "http://localhost:8000/api/v1/media/collections/",
                data=data,
                headers=headers,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    collection_id = result.get("id")
                    collection_uuid = result.get("uuid")
                    logger.info(
                        "Created new collection %s (UUID: %s) for camera %s",
                        collection_id,
                        collection_uuid,
                        device_id,
                    )
                    return collection_uuid
                else:
                    error_text = await response.text()
                    logger.error(
                        "Failed to create collection for camera %s: %s %s",
                        device_id,
                        response.status,
                        error_text,
                    )
                    return None

        except Exception as e:
            logger.error(
                "Error finding/creating collection for camera %s: %s",
                device_id,
                e,
            )
            return None

    async def _assign_media_to_collection(
        self, media_id: str, collection_id: str, user_id: str, session, headers: Dict
    ) -> bool:
        """Assign media item to a collection."""
        try:
            endpoint = f"http://localhost:8000/api/v1/media/collections/{collection_id}/add/{media_id}"
            async with session.post(
                endpoint, headers=headers, params={"user_id": user_id}
            ) as response:
                if response.status == 200:
                    logger.info(
                        "Successfully assigned media %s to collection %s",
                        media_id,
                        collection_id,
                    )
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        "Failed to assign media %s to collection %s: %s %s",
                        media_id,
                        collection_id,
                        response.status,
                        error_text,
                    )
                    return False

        except Exception as e:
            logger.error(
                "Error assigning media %s to collection %s: %s",
                media_id,
                collection_id,
                e,
            )
            return False


# Global camera detection service instance
camera_service = CameraDetectionService()

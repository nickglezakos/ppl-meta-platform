"""
Camera detection and management service for PPL Meta Cameras.
"""

import asyncio
import datetime
import logging
import os
import platform
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import cv2
from sqlalchemy.orm import Session
from src.config import get_config
from src.database import get_db
from src.models.camera import Camera, CameraStatus, CameraType
from src.services.orchestrator_client import OrchestratorClient

# Import streaming session manager for session completion
from src.services.streaming_session_manager import streaming_session_manager

logger = logging.getLogger(__name__)
config = get_config()


class CameraDetectionService:
    """Service for detecting and managing cameras."""

    def __init__(self):
        self.detected_cameras: Dict[str, Dict] = {}
        self.active_connections: Dict[str, cv2.VideoCapture] = {}
        self.camera_sources: Dict[str, str | int] = {}  # Track original camera sources (device index or RTSP URL)
        self.active_recordings: Dict[str, Dict] = {}  # Track active recordings
        self.orchestrator_client = OrchestratorClient()  # Phase 5: Event publishing
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
                        self.camera_sources[device_id] = index  # Store the device index
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
                            self.camera_sources[device_id] = decoded_rtsp_url  # Store the RTSP URL
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

    async def start_recording_with_session(
        self,
        device_id: str,
        user_id: str,
        quality: str = "high",
        auth_token: Optional[str] = None,
        session_uuid: str = "",
        segment_duration: int = 5,
        enable_instant_detection: bool = True,
    ) -> Optional[Dict]:
        """Start recording with session tracking and segment support.
        
        Args:
            enable_instant_detection: If True, automatically start instant detection
        """

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
                # For mobile cameras, check if we're receiving frames
                from src.services.mobile_streaming import mobile_streaming_service

                if not mobile_streaming_service.has_active_mobile_camera(device_id):
                    logger.error(
                        f"Mobile camera {device_id} not streaming for recording"
                    )
                    return None

                result = await self._start_mobile_recording_with_session(
                    device_id,
                    user_id,
                    quality,
                    auth_token,
                    session_uuid,
                    segment_duration,
                )
            else:
                # For USB/RTSP cameras, check active connections
                if device_id not in self.active_connections:
                    logger.error(f"Camera {device_id} not connected for recording")
                    return None

                result = await self._start_regular_recording_with_session(
                    device_id,
                    user_id,
                    quality,
                    auth_token,
                    session_uuid,
                    segment_duration,
                )
            
            # Auto-start instant detection if enabled and recording started successfully
            logger.info(f"🔍 [INSTANT-DETECT] Checking auto-start: result={result is not None}, enable_instant_detection={enable_instant_detection}")
            if result and enable_instant_detection:
                try:
                    logger.info(f"🔍 [INSTANT-DETECT] Attempting to auto-start instant detection for {device_id}")
                    from src.api.v1.endpoints.instant_detection import get_instant_detection_manager
                    manager = get_instant_detection_manager()
                    
                    # Use the SHARED VideoCapture object to avoid resource contention
                    cap = self.active_connections.get(device_id)
                    if cap is None:
                        logger.error(f"🔍 [INSTANT-DETECT] No active connection found for {device_id}")
                        return result
                    
                    logger.info(f"🔍 [INSTANT-DETECT] Using shared VideoCapture for {device_id}")
                    manager.start_sampling(device_id, cap)
                    logger.info(f"✅ Auto-started instant detection for camera {device_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to auto-start instant detection for {device_id}: {e}")
                    logger.exception("Full exception:")
            else:
                logger.info(f"🔍 [INSTANT-DETECT] NOT starting instant detection: result={result is not None}, enable_instant_detection={enable_instant_detection}")
            
            return result

        except Exception as e:
            logger.error("Error starting recording for camera %s: %s", device_id, e)
            return None

    async def _start_regular_recording_with_session(
        self,
        device_id: str,
        user_id: str,
        quality: str,
        auth_token: Optional[str] = None,
        session_uuid: str = "",
        segment_duration: int = 5,
    ) -> Optional[Dict]:
        """Start recording for USB/RTSP cameras with session and segment support."""
        logger.info(
            f"🎬 [SESSION] Starting USB/RTSP recording for {device_id}, session: {session_uuid}"
        )

        cap = self.active_connections[device_id]

        # Get recording parameters
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        raw_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        fps = min(raw_fps, 30) if raw_fps > 0 else 30

        # Create session directory
        session_dir = os.path.join("recordings", device_id, session_uuid)
        os.makedirs(session_dir, exist_ok=True)

        # Generate first segment file
        segment_index = 1
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"segment_{segment_index:03d}_{timestamp}.mp4"
        file_path = os.path.join(session_dir, filename)

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*"H264")
        video_writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

        if not video_writer.isOpened():
            logger.error(f"Failed to initialize video writer for {device_id}")
            return None

        # Store recording info with session tracking
        recording_id = str(uuid.uuid4())
        recording_info = {
            "recording_id": recording_id,
            "device_id": device_id,
            "user_id": user_id,
            "session_uuid": session_uuid,
            "session_dir": session_dir,
            "current_segment_path": file_path,
            "current_segment_index": segment_index,
            "video_writer": video_writer,
            "started_at": datetime.datetime.now(),
            "segment_started_at": datetime.datetime.now(),
            "frame_count": 0,
            "total_frame_count": 0,
            "quality": quality,
            "resolution": f"{width}x{height}",
            "fps": fps,
            "is_mobile": False,
            "auth_token": auth_token,
            "segment_duration": segment_duration,
            "segment_files": [filename],  # Track all segment files
        }

        self.active_recordings[device_id] = recording_info

        # Start frame recording loop with segment support
        logger.info(
            f"🎬 [DEBUG] About to start _frame_recording_loop_with_segments for {device_id}"
        )
        asyncio.create_task(self._frame_recording_loop_with_segments(device_id))
        logger.info(
            f"🎬 [DEBUG] Task created for _frame_recording_loop_with_segments for {device_id}"
        )

        logger.info(
            f"Recording with session started for camera {device_id}, "
            f"session: {session_uuid}, segment: {filename}"
        )

        return {
            "recording_id": recording_id,
            "started_at": recording_info["started_at"].isoformat(),
            "file_path": file_path,
            "session_uuid": session_uuid,
            "segment_duration": segment_duration,
        }

    async def _start_mobile_recording_with_session(
        self,
        device_id: str,
        user_id: str,
        quality: str,
        auth_token: Optional[str] = None,
        session_uuid: str = "",
        segment_duration: int = 5,
    ) -> Optional[Dict]:
        """Start recording for mobile cameras with session and segment support."""
        logger.info(
            f"🎬 [SESSION] Starting mobile recording for {device_id}, session: {session_uuid}"
        )

        # Get target size for mobile recording
        width, height = 1920, 1080  # Default HD for mobile
        target_fps = 30

        # Create session directory
        session_dir = os.path.join("recordings", device_id, session_uuid)
        os.makedirs(session_dir, exist_ok=True)

        # Generate first segment file
        segment_index = 1
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"segment_{segment_index:03d}_{timestamp}.mp4"
        file_path = os.path.join(session_dir, filename)

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*"H264")
        video_writer = cv2.VideoWriter(file_path, fourcc, target_fps, (width, height))

        if not video_writer.isOpened():
            logger.error(f"Failed to initialize mobile video writer for {device_id}")
            return None

        # Store recording info with session tracking
        recording_id = str(uuid.uuid4())
        recording_info = {
            "recording_id": recording_id,
            "device_id": device_id,
            "user_id": user_id,
            "session_uuid": session_uuid,
            "session_dir": session_dir,
            "current_segment_path": file_path,
            "current_segment_index": segment_index,
            "video_writer": video_writer,
            "started_at": datetime.datetime.now(),
            "segment_started_at": datetime.datetime.now(),
            "frame_count": 0,
            "total_frame_count": 0,
            "quality": quality,
            "resolution": f"{width}x{height}",
            "fps": target_fps,
            "is_mobile": True,
            "target_size": (width, height),
            "auth_token": auth_token,
            "segment_duration": segment_duration,
            "segment_files": [filename],  # Track all segment files
        }

        self.active_recordings[device_id] = recording_info

        # Start mobile frame recording task with segment support
        asyncio.create_task(self._mobile_recording_loop_with_segments(device_id))

        logger.info(
            f"Mobile recording with session started for camera {device_id}, "
            f"session: {session_uuid}, segment: {filename}"
        )

        return {
            "recording_id": recording_id,
            "started_at": recording_info["started_at"].isoformat(),
            "file_path": file_path,
            "session_uuid": session_uuid,
            "segment_duration": segment_duration,
        }

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
        raw_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

        # Cap FPS for USB/RTSP cameras to prevent fast playback
        # USB cameras often report 60-90+ FPS which causes fast playback
        # Cap to 30 FPS for consistent playback speed
        fps = min(raw_fps, 30) if raw_fps > 0 else 30

        logger.info(
            f"🎬 [DEBUG] Camera properties - Width: {width}, Height: {height}, "
            f"Raw FPS: {raw_fps}, Capped FPS: {fps}"
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
        # Note: FPS is now used as a fallback/target rate - actual recording
        # uses dynamic frame rate based on mobile frame timestamps
        quality_settings = {
            "low": (320, 240, 15),
            "medium": (640, 480, 30),
            "high": (1280, 720, 30),
            "ultra": (1920, 1080, 30),
        }

        width, height, target_fps = quality_settings.get(
            quality, quality_settings["medium"]
        )

        # Generate recording file path
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mobile_recording_{device_id}_{timestamp}.mp4"
        recordings_dir = os.path.join("recordings", device_id)
        os.makedirs(recordings_dir, exist_ok=True)
        file_path = os.path.join(recordings_dir, filename)

        # Initialize video writer with H.264 codec for web compatibility
        fourcc = cv2.VideoWriter_fourcc(*"H264")
        video_writer = cv2.VideoWriter(file_path, fourcc, target_fps, (width, height))

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
            "fps": target_fps,
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

    async def stop_recording(self, device_id: str, user_id: str, auto_stop_instant_detection: bool = True) -> Optional[Dict]:
        """Stop recording video from camera and finalize files.
        
        Args:
            auto_stop_instant_detection: If True, automatically stop instant detection
        """
        import traceback

        logger.info(
            f"🎬 [STOP_REQUEST] Stop recording requested for {device_id} by user {user_id}"
        )
        logger.info(
            f"🎬 [STOP_CALLER] Call stack: {[frame.name for frame in traceback.extract_stack()[-3:-1]]}"
        )

        try:
            if device_id not in self.active_recordings:
                logger.warning(f"🎬 [DEBUG] ⚠️ Camera {device_id} is not recording")
                return None

            recording_info = self.active_recordings[device_id]
            logger.info(f"🎬 [DEBUG] Found active recording for {device_id}")

            # Check if this is a session-based recording with segments
            is_session_recording = "session_uuid" in recording_info

            if is_session_recording:
                result = await self._stop_session_recording(
                    device_id, user_id, recording_info
                )
            else:
                result = await self._stop_regular_recording(
                    device_id, user_id, recording_info
                )
            
            # Auto-stop instant detection if enabled and recording stopped successfully
            if result and auto_stop_instant_detection:
                try:
                    from src.api.v1.endpoints.instant_detection import get_instant_detection_manager
                    manager = get_instant_detection_manager()
                    manager.stop_sampling()
                    logger.info(f"✅ Auto-stopped instant detection for camera {device_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to auto-stop instant detection for {device_id}: {e}")
            
            return result

        except Exception as e:
            logger.error(f"🎬 [DEBUG] ❌ Error stopping recording for {device_id}: {e}")
            return None

    async def _stop_session_recording(
        self, device_id: str, user_id: str, recording_info: Dict
    ) -> Optional[Dict]:
        """Stop session-based recording with segment finalization."""
        session_uuid = recording_info["session_uuid"]
        logger.info(
            f"🎬 [SESSION] Stopping session recording {session_uuid} for {device_id}"
        )

        # Finalize current segment
        video_writer = recording_info["video_writer"]
        video_writer.release()

        # Get final segment info
        current_segment_path = recording_info["current_segment_path"]
        file_size = os.path.getsize(current_segment_path)
        stopped_at = datetime.datetime.now()
        total_duration = stopped_at - recording_info["started_at"]

        # Add final segment to recording session
        try:
            from src.services.recording_session_service import RecordingSessionService

            db_gen = get_db()
            db = next(db_gen)
            try:
                session_service = RecordingSessionService(db)
                session_service.add_file_to_session(
                    session_uuid=session_uuid,
                    file_path=current_segment_path,
                    file_size_bytes=file_size,
                    duration_seconds=recording_info["segment_duration"],
                    frame_count=recording_info["frame_count"],
                )

                # Complete the recording session
                session_service.stop_session(session_uuid=session_uuid)

                logger.info(f"🎬 [SESSION] Completed recording session {session_uuid}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error finalizing recording session {session_uuid}: {e}")

        # Upload ONLY the final segment (other segments already uploaded during rotation)
        logger.info(f"🎬 [SESSION] Uploading final segment for session {session_uuid}")
        
        # Create modified recording_info for final segment only
        final_segment_recording_info = recording_info.copy()
        final_segment_recording_info["current_segment_path"] = current_segment_path
        
        upload_result = await self._upload_recording_to_collection(
            final_segment_recording_info, user_id
        )
        
        # Wrap single result in list for compatibility with existing code
        upload_results = [upload_result] if upload_result else []

        # Extract collection info from first successful upload
        collection_id = None
        media_ids = []
        media_uuids = []

        if upload_results:
            for result in upload_results:
                if result:
                    if not collection_id:
                        collection_id = result.get("collection_id")
                    media_ids.append(result.get("media_id"))
                    media_uuids.append(result.get("media_uuid"))

            logger.info(
                f"🎬 [SESSION] Media upload completed: {len(media_uuids)} segments uploaded, "
                f"collection_id: {collection_id}"
            )
        else:
            logger.error(f"🎬 [SESSION] Media upload failed for session {session_uuid}")

        # Use first media UUID for session tracking (or could be a list)
        media_uuid = media_uuids[0] if media_uuids else None

        if upload_results and any(upload_results):

            # Update session with media upload status
            try:
                db_gen = get_db()
                db = next(db_gen)
                try:
                    session_service = RecordingSessionService(db)
                    session_service.update_media_upload_status(
                        session_uuid=session_uuid,
                        started=True,
                        completed=True,
                        media_collection_id=collection_id,
                        media_uuid=media_uuid,
                    )
                    logger.info(
                        f"🎬 [SESSION] Updated session {session_uuid} with media info"
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error updating session {session_uuid} media status: {e}")
        else:
            logger.error(f"🎬 [SESSION] Media upload failed for session {session_uuid}")
            # Update session to indicate upload failure
            try:
                db_gen = get_db()
                db = next(db_gen)
                try:
                    session_service = RecordingSessionService(db)
                    session_service.update_media_upload_status(
                        session_uuid=session_uuid,
                        started=True,
                        completed=False,
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(
                    f"Error updating session {session_uuid} upload failure: {e}"
                )

        # Clean up recording info
        elapsed_time = (
            datetime.datetime.now()
            - recording_info.get("started_at", datetime.datetime.now())
        ).total_seconds()
        logger.info(
            f"🎬 [CLEANUP] Removing {device_id} from active_recordings after {elapsed_time:.1f}s"
        )
        del self.active_recordings[device_id]

        # Complete face detection session
        await self._complete_face_detection_session(device_id)

        # Publish recording completion event
        segment_files = recording_info.get("segment_files", [])
        result = {
            "recording_id": recording_info["recording_id"],
            "session_uuid": session_uuid,
            "duration_seconds": int(total_duration.total_seconds()),
            "total_frame_count": recording_info["total_frame_count"],
            "segment_count": len(segment_files),
            "segment_files": segment_files,
            "session_dir": recording_info["session_dir"],
            "collection_id": collection_id,
            "media_uuid": media_uuid,
            "stopped_at": stopped_at.isoformat(),
        }

        await self._publish_recording_completion_event(device_id, result, user_id)

        logger.info(
            f"🎬 [SESSION] ✅ Session recording completed for {device_id}: {len(segment_files)} segments"
        )
        return result

    async def _upload_session_segments_to_collection(
        self, session_uuid: str, recording_info: Dict, user_id: str
    ) -> List[Optional[Dict]]:
        """Upload all session segments separately to media service."""
        try:
            from src.services.recording_session_service import RecordingSessionService

            db_gen = get_db()
            db = next(db_gen)
            try:
                session_service = RecordingSessionService(db)
                session_files = session_service.get_session_files(session_uuid)

                if not session_files:
                    logger.warning(
                        f"🎬 [SEGMENTS] No files found for session {session_uuid}"
                    )
                    return []

                logger.info(
                    f"🎬 [SEGMENTS] Uploading {len(session_files)} segments for session {session_uuid}"
                )

                upload_results = []
                for i, session_file in enumerate(session_files):
                    logger.info(
                        f"🎬 [SEGMENTS] Uploading segment {i+1}/{len(session_files)}: {session_file.file_path}"
                    )

                    # Create modified recording_info for each segment
                    segment_recording_info = recording_info.copy()
                    segment_recording_info["current_segment_path"] = (
                        session_file.file_path
                    )

                    # Upload this segment
                    upload_result = await self._upload_recording_to_collection(
                        segment_recording_info, user_id
                    )
                    upload_results.append(upload_result)

                    if upload_result:
                        logger.info(
                            f"🎬 [SEGMENTS] ✅ Segment {i+1} uploaded: {upload_result.get('media_uuid')}"
                        )
                    else:
                        logger.error(f"🎬 [SEGMENTS] ❌ Failed to upload segment {i+1}")

                successful_uploads = [r for r in upload_results if r]
                logger.info(
                    f"🎬 [SEGMENTS] Upload complete: {len(successful_uploads)}/{len(session_files)} segments uploaded"
                )

                return upload_results

            finally:
                db.close()

        except Exception as e:
            logger.error(
                f"🎬 [SEGMENTS] ❌ Error uploading session {session_uuid} segments: {e}"
            )
            return []

    async def _stop_regular_recording(
        self, device_id: str, user_id: str, recording_info: Dict
    ) -> Optional[Dict]:
        """Stop regular (non-session) recording."""
        # Finalize recording
        video_writer = recording_info["video_writer"]
        logger.info(f"🎬 [DEBUG] Releasing video writer for {device_id}")
        video_writer.release()

        # Calculate final stats
        stopped_at = datetime.datetime.now()
        duration = stopped_at - recording_info["started_at"]
        logger.info(f"🎬 [DEBUG] Recording duration: {duration.total_seconds():.1f}s")

        # Get file size
        file_path = recording_info.get("file_path") or recording_info.get(
            "current_segment_path"
        )
        file_size = os.path.getsize(file_path)
        logger.info(f"🎬 [DEBUG] Recording file size: {file_size} bytes")

        # Clean up recording info
        del self.active_recordings[device_id]
        logger.info(f"🎬 [DEBUG] Removed {device_id} from active recordings")

        # Upload to media service and assign to camera collection
        logger.info(f"🎬 [DEBUG] Starting upload to collection for {device_id}")
        upload_result = await self._upload_recording_to_collection(
            recording_info, user_id
        )

        collection_id = None
        if upload_result:
            collection_id = upload_result.get("collection_id")

        logger.info(f"🎬 [DEBUG] Upload completed, collection_id: {collection_id}")

        result = {
            "recording_id": recording_info["recording_id"],
            "duration_seconds": int(duration.total_seconds()),
            "frame_count": recording_info["frame_count"],
            "file_path": file_path,
            "file_size_bytes": file_size,
            "collection_id": collection_id,
            "stopped_at": stopped_at.isoformat(),
        }

        # Complete face detection session and publish event
        await self._complete_face_detection_session(device_id)
        await self._publish_recording_completion_event(device_id, result, user_id)

        logger.info(f"🎬 [DEBUG] ✅ Stop recording complete for {device_id}: {result}")
        return result

    async def _complete_face_detection_session(self, device_id: str):
        """Complete face detection session."""
        try:
            session_completed = (
                await streaming_session_manager.complete_streaming_session(
                    device_id=device_id, completion_reason="recording_completed"
                )
            )
            if session_completed:
                logger.info(
                    f"✅ [SESSION] Completed face detection session for {device_id}"
                )
            else:
                logger.warning(
                    f"⚠️ [SESSION] No active face detection session for {device_id}"
                )
        except Exception as e:
            logger.error(
                f"❌ [SESSION] Error completing face detection session for {device_id}: {e}"
            )

    async def _publish_recording_completion_event(
        self, device_id: str, result: Dict, user_id: str
    ):
        """Publish recording completion event to orchestrator."""
        try:
            event_published = (
                await self.orchestrator_client.publish_recording_completed_event(
                    camera_device_id=device_id,
                    recording_result=result,
                    user_id=user_id,
                )
            )
            if event_published:
                logger.info(
                    f"📡 [DEBUG] ✅ Published recording completion event for {device_id}"
                )
            else:
                logger.warning(f"📡 [DEBUG] ⚠️ Failed to publish event for {device_id}")
        except Exception as e:
            logger.error(f"📡 [DEBUG] ❌ Error publishing event for {device_id}: {e}")

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

    def get_debug_recording_state(self, device_id: str) -> Dict:
        """Debug method to inspect recording state inconsistencies."""
        # Check in-memory state
        active_recording = self.active_recordings.get(device_id)

        # Check database state
        db_gen = get_db()
        db = next(db_gen)
        try:
            camera = db.query(Camera).filter(Camera.device_id == device_id).first()
            active_session = camera.get_active_recording_session() if camera else None
        finally:
            db.close()

        return {
            "device_id": device_id,
            "has_active_recording_memory": active_recording is not None,
            "has_active_session_db": active_session is not None,
            "active_recording_keys": list(self.active_recordings.keys()),
            "memory_recording_id": (
                active_recording.get("recording_id") if active_recording else None
            ),
            "db_session_uuid": active_session.session_uuid if active_session else None,
            "db_session_status": active_session.status if active_session else None,
        }

    def clear_stale_recording_state(self, device_id: str) -> Dict:
        """Clear stale recording state for debugging purposes."""
        result = {"cleared": []}

        # Clear memory state
        if device_id in self.active_recordings:
            del self.active_recordings[device_id]
            result["cleared"].append("memory_state")

        # Clear database state
        db_gen = get_db()
        db = next(db_gen)
        try:
            camera = db.query(Camera).filter(Camera.device_id == device_id).first()
            if camera:
                active_session = camera.get_active_recording_session()
                if active_session:
                    active_session.status = "completed"
                    active_session.stopped_at = datetime.datetime.utcnow()
                    db.commit()
                    result["cleared"].append("database_session")
        finally:
            db.close()

        return result

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

            # Get camera's actual FPS for frame skipping calculation
            camera_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

            # Calculate frame skipping ratio
            # If camera is 90fps and target is 30fps, skip every 3rd frame (90/30=3)
            skip_ratio = max(1, camera_fps // target_fps)
            frame_counter = 0

            # Frame timing control for consistent FPS
            target_frame_interval = 1.0 / target_fps  # Seconds between frames
            start_time = time.time()
            next_frame_time = start_time

            max_consecutive_failures = 10
            failure_count = 0

            logger.info(f"🎬 [DEBUG] Recording loop initialized for {device_id}")
            logger.info(
                f"🎬 [DEBUG] Camera FPS: {camera_fps}, Target FPS: {target_fps}, "
                f"Skip ratio: {skip_ratio} (write every {skip_ratio} frames)"
            )
            logger.info(
                f"🎬 [DEBUG] Target frame interval: {target_frame_interval:.3f}s"
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
                    frame_counter += 1

                    # Only write frames based on skip ratio to achieve target FPS
                    if frame_counter % skip_ratio == 0:
                        # Check if it's time to write the next frame
                        current_time = time.time()
                        if current_time >= next_frame_time:
                            video_writer.write(frame)
                            recording_info["frame_count"] += 1
                            frame_write_count += 1

                            # Schedule next frame time
                            next_frame_time = current_time + target_frame_interval

                            # Log progress every 30 written frames
                            if frame_write_count % 30 == 0:
                                elapsed = current_time - start_time
                                expected_frames = elapsed * target_fps
                                timing_accuracy = (
                                    (frame_write_count / expected_frames) * 100
                                    if expected_frames > 0
                                    else 100
                                )
                                logger.info(
                                    f"🎬 [DEBUG] ✅ Wrote {frame_write_count} frames for {device_id} "
                                    f"(read {frame_counter} total, timing: {timing_accuracy:.1f}%)"
                                )

                    # Calculate sleep time to maintain proper frame timing
                    current_time = time.time()
                    sleep_time = max(
                        0.001, min(0.033, next_frame_time - current_time)
                    )  # Cap between 1ms and 33ms
                    await asyncio.sleep(sleep_time)

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

                # Dynamic frame rate: Only process when new frame is available
                # Remove sleep to eliminate artificial timing constraints
                # This allows video to be recorded at natural mobile frame rate
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU spinning

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

    async def _frame_recording_loop_with_segments(self, device_id: str):
        """Record frames with automatic segment creation for USB/RTSP cameras."""
        logger.info(
            f"🎬 [SEGMENT] *** METHOD ENTRY *** Starting segment recording loop for {device_id}"
        )
        logger.info(f"🎬 [SEGMENT] Starting segment recording loop for {device_id}")

        try:
            recording_info = self.active_recordings.get(device_id)
            if not recording_info:
                logger.error(f"No segment recording info found for {device_id}")
                return

            # Initialize recording session service for tracking segments
            from src.services.recording_session_service import RecordingSessionService

            db_gen = get_db()
            db = next(db_gen)
            try:
                session_service = RecordingSessionService(db)
            finally:
                db.close()

            cap = self.active_connections[device_id]
            target_fps = recording_info["fps"]
            segment_duration = recording_info["segment_duration"]

            # Frame timing and skipping logic
            camera_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            skip_ratio = max(1, camera_fps // target_fps)
            frame_counter = 0

            logger.info(f"🎬 [SEGMENT] Recording with {segment_duration}s segments")

            # Initialize timing trackers
            loop_start_time = datetime.datetime.now()
            last_debug_log = datetime.datetime.now()
            total_frames_written = 0
            loop_iterations = 0

            while device_id in self.active_recordings:
                try:
                    loop_iterations += 1
                    current_datetime = datetime.datetime.now()

                    # Check if current segment should be rotated - FIXED TIMING
                    segment_elapsed = (
                        current_datetime - recording_info["segment_started_at"]
                    ).total_seconds()

                    # Calculate total recording elapsed time
                    total_elapsed = (current_datetime - loop_start_time).total_seconds()

                    # Enhanced debug logging every 5 seconds
                    if (current_datetime - last_debug_log).total_seconds() >= 5:
                        logger.info(
                            f"🎬 [DEBUG] {device_id}: Total={total_elapsed:.1f}s, "
                            f"Segment={segment_elapsed:.1f}s/{segment_duration}s, "
                            f"Frames={total_frames_written}, Loops={loop_iterations}"
                        )
                        last_debug_log = current_datetime

                    if segment_elapsed >= segment_duration:
                        logger.info(
                            f"🎬 [SEGMENT] Rotating segment for {device_id} after {segment_elapsed:.1f}s"
                        )
                        await self._rotate_to_next_segment(device_id, session_service)
                        continue

                    # Read and process frame
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        await asyncio.sleep(0.1)
                        continue

                    frame_counter += 1

                    # Write frame based on skip ratio (simplified timing)
                    if frame_counter % skip_ratio == 0:
                        recording_info["video_writer"].write(frame)
                        recording_info["frame_count"] += 1
                        recording_info["total_frame_count"] += 1
                        total_frames_written += 1  # Track frames for debug

                    # Small sleep to prevent CPU spinning (camera handles timing)
                    await asyncio.sleep(0.001)

                except Exception as e:
                    logger.error(f"Error in segment frame processing: {e}")
                    await asyncio.sleep(0.1)

            # Log final statistics when recording ends
            final_elapsed = (datetime.datetime.now() - loop_start_time).total_seconds()
            logger.info(
                f"🎬 [FINAL] {device_id} recording ended: "
                f"Total={final_elapsed:.1f}s, Frames={total_frames_written}, "
                f"Loops={loop_iterations}"
            )

        except Exception as e:
            final_elapsed = (datetime.datetime.now() - loop_start_time).total_seconds()
            logger.error(
                f"🎬 [ERROR] {device_id} recording error after {final_elapsed:.1f}s: {e}"
            )
            # Clean up on error
            if device_id in self.active_recordings:
                recording_info = self.active_recordings[device_id]
                recording_info["video_writer"].release()
                del self.active_recordings[device_id]

    async def _mobile_recording_loop_with_segments(self, device_id: str):
        """Record mobile frames with automatic segment creation."""
        logger.info(
            f"🎬 [SEGMENT] Starting mobile segment recording loop for {device_id}"
        )

        try:
            recording_info = self.active_recordings.get(device_id)
            if not recording_info:
                logger.error(f"No mobile segment recording info found for {device_id}")
                return

            # Initialize recording session service for tracking segments
            from src.services.recording_session_service import RecordingSessionService

            db_gen = get_db()
            db = next(db_gen)
            try:
                session_service = RecordingSessionService(db)
            finally:
                db.close()

            from src.services.mobile_streaming import mobile_streaming_service

            target_size = recording_info["target_size"]
            segment_duration = recording_info["segment_duration"]
            frame_count = 0

            logger.info(
                f"🎬 [SEGMENT] Mobile recording with {segment_duration}s segments"
            )

            while device_id in self.active_recordings:
                try:
                    # Check if current segment should be rotated - FIXED TIMING
                    current_datetime = datetime.datetime.now()
                    segment_elapsed = (
                        current_datetime - recording_info["segment_started_at"]
                    ).total_seconds()

                    if segment_elapsed >= segment_duration:
                        await self._rotate_to_next_segment(device_id, session_service)
                        continue

                    # Get mobile frame
                    frame_data = mobile_streaming_service.get_mobile_frame(device_id)
                    if frame_data is None:
                        await asyncio.sleep(0.1)
                        continue

                    # Decode and process frame
                    frame = mobile_streaming_service.decode_mobile_frame(frame_data)
                    if frame is None:
                        continue

                    # Resize frame to target size
                    if (
                        frame.shape[1] != target_size[0]
                        or frame.shape[0] != target_size[1]
                    ):
                        frame = cv2.resize(frame, target_size)

                    # Write frame
                    recording_info["video_writer"].write(frame)
                    recording_info["frame_count"] += 1
                    recording_info["total_frame_count"] += 1
                    frame_count += 1

                    if frame_count % 30 == 0:
                        logger.info(
                            f"🎬 [SEGMENT] Recorded {frame_count} mobile frames for {device_id}"
                        )

                    await asyncio.sleep(0.01)

                except Exception as e:
                    logger.error(f"Error in mobile segment frame processing: {e}")
                    await asyncio.sleep(0.1)

            logger.info(
                f"🎬 [SEGMENT] Mobile segment recording loop ended for {device_id}"
            )

        except Exception as e:
            logger.error(f"Error in mobile segment recording loop for {device_id}: {e}")
            # Clean up on error
            if device_id in self.active_recordings:
                recording_info = self.active_recordings[device_id]
                recording_info["video_writer"].release()
                del self.active_recordings[device_id]

    async def _rotate_to_next_segment(self, device_id: str, session_service):
        """
        Rotate to next segment file and update recording session.
        
        This function is called every segment_duration seconds during
        recording. It closes the current segment, saves it to the session
        database, uploads it immediately to the media service, and creates
        the next segment file.
        
        The immediate upload enables the continuous pipeline to trigger
        face detection and batch processing as segments are recorded,
        rather than waiting until the entire recording session is complete.
        """
        try:
            recording_info = self.active_recordings.get(device_id)
            if not recording_info:
                return

            # Close current segment
            recording_info["video_writer"].release()
            current_segment_path = recording_info["current_segment_path"]
            current_segment_index = recording_info["current_segment_index"]

            # Get file size of completed segment
            file_size = os.path.getsize(current_segment_path)

            # Add completed segment to recording session
            session_uuid = recording_info["session_uuid"]

            # Use the passed session_service parameter instead of creating a new one
            segment_filename = os.path.basename(current_segment_path)
            session_service.add_file_to_session(
                session_uuid=session_uuid,
                file_path=current_segment_path,
                file_size_bytes=file_size,
                duration_seconds=recording_info["segment_duration"],
                frame_count=recording_info["frame_count"],
            )
            logger.info(
                f"🎬 [SEGMENT] Added segment {segment_filename} to session {session_uuid}"
            )

            # Upload completed segment immediately to media service
            logger.info(
                f"🎬 [SEGMENT] Uploading completed segment {segment_filename} "
                f"to media service..."
            )
            logger.info(
                f"🔥 [SEGMENT] Upload segment: {segment_filename}"
            )
            logger.info(
                f"🔥 [SEGMENT] recording_info keys: "
                f"{list(recording_info.keys())}"
            )
            has_token = 'auth_token' in recording_info
            logger.info(f"🔥 [SEGMENT] auth_token present: {has_token}")
            logger.info(
                f"🔥 [SEGMENT] user_id: {recording_info.get('user_id')}"
            )
            
            segment_recording_info = recording_info.copy()
            segment_recording_info["current_segment_path"] = (
                current_segment_path
            )
            
            user_id = recording_info.get("user_id") or "7"
            logger.info(f"🔥 [SEGMENT] Final user_id: {user_id}")
            
            if user_id:
                logger.info("🔥 [SEGMENT] Calling upload function")
                upload_result = await self._upload_recording_to_collection(
                    segment_recording_info, user_id
                )
                logger.info(f"🔥 [SEGMENT] Upload result: {upload_result}")
                
                if upload_result:
                    media_uuid = upload_result.get('media_uuid')
                    logger.info(
                        f"🎬 [SEGMENT] ✅ Segment {segment_filename} uploaded "
                        f"to media service: {media_uuid}"
                    )
                    logger.info(
                        f"🔥 [SEGMENT] ✅ Upload OK: {media_uuid}"
                    )
                else:
                    logger.error(
                        f"🎬 [SEGMENT] ❌ Failed to upload segment "
                        f"{segment_filename} to media service"
                    )
                    logger.error("🔥 [SEGMENT] ❌ Upload failed")
            else:
                logger.warning(
                    f"🎬 [SEGMENT] ⚠️ No user_id found in recording_info, "
                    f"skipping upload for {segment_filename}"
                )
                logger.warning("🔥 [SEGMENT] ⚠️ No user_id")

            # Create next segment
            next_index = current_segment_index + 1
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"segment_{next_index:03d}_{timestamp}.mp4"
            next_segment_path = os.path.join(recording_info["session_dir"], filename)

            # Initialize new video writer
            fourcc = cv2.VideoWriter_fourcc(*"H264")
            width, height = (
                recording_info["target_size"]
                if recording_info["is_mobile"]
                else (
                    int(
                        self.active_connections[device_id].get(cv2.CAP_PROP_FRAME_WIDTH)
                    ),
                    int(
                        self.active_connections[device_id].get(
                            cv2.CAP_PROP_FRAME_HEIGHT
                        )
                    ),
                )
            )
            fps = recording_info["fps"]

            video_writer = cv2.VideoWriter(
                next_segment_path, fourcc, fps, (width, height)
            )

            if not video_writer.isOpened():
                logger.error(f"Failed to create next segment writer for {device_id}")
                return

            # Update recording info for next segment
            recording_info["video_writer"] = video_writer
            recording_info["current_segment_path"] = next_segment_path
            recording_info["current_segment_index"] = next_index
            recording_info["segment_started_at"] = datetime.datetime.now()
            recording_info["frame_count"] = 0  # Reset for new segment
            recording_info["segment_files"].append(filename)

            logger.info(
                f"🎬 [SEGMENT] Rotated to segment {next_index} for {device_id}: {filename}"
            )

        except Exception as e:
            logger.error(f"Error rotating to next segment for {device_id}: {e}")

    async def _upload_recording_to_collection(
        self, recording_info: Dict, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Upload recorded video to media service and assign to collection."""
        print(f"🔥🔥🔥 [UPLOAD] FUNCTION CALLED! user_id={user_id}")
        logger.info(f"🎬 [DEBUG] Starting upload process for recording")
        from pathlib import Path

        import aiofiles
        import aiohttp

        try:
            print(f"🔥🔥🔥 [UPLOAD] Inside try block, about to check file paths")
            # Handle both regular recordings (file_path) and session recordings (current_segment_path)
            file_path = recording_info.get("file_path") or recording_info.get(
                "current_segment_path"
            )
            device_id = recording_info["device_id"]
            logger.info(f"🎬 [DEBUG] Upload file: {file_path}, device: {device_id}")

            if not file_path:
                logger.error(
                    f"🎬 [DEBUG] ❌ No file path found in recording_info: {recording_info.keys()}"
                )
                return None

            # Fetch camera name from database
            camera_name = None
            logger.info(f"🎬 [DEBUG] === STARTING CAMERA NAME QUERY ===")
            logger.info(f"🎬 [DEBUG] Looking for device_id: '{device_id}'")

            try:
                from src.database import get_db
                from src.models.camera import Camera

                logger.info(f"🎬 [DEBUG] Camera model imported successfully")

                # Create fresh database session for camera lookup
                db_gen = get_db()
                db = next(db_gen)
                try:
                    logger.info(f"🎬 [DEBUG] Created fresh DB session: {db}")

                    # Try to query the camera
                    camera_query = db.query(Camera).filter(
                        Camera.device_id == device_id
                    )
                    logger.info(f"🎬 [DEBUG] Query created: {camera_query}")

                    camera = camera_query.first()
                    logger.info(f"🎬 [DEBUG] Query result: {camera}")

                    if camera:
                        camera_name = camera.name
                        logger.info(
                            f"🎬 [DEBUG] ✅ Camera found! Name: '{camera_name}'"
                        )
                    else:
                        logger.warning(
                            f"🎬 [DEBUG] ❌ Camera not found in database for "
                            f"device_id: '{device_id}'"
                        )
                        camera_name = f"Camera {device_id}"  # Fallback name
                        logger.info(f"🎬 [DEBUG] Using fallback name: '{camera_name}'")
                finally:
                    db.close()
                    logger.info("🎬 [DEBUG] Database session closed")

            except Exception as db_error:
                logger.error(
                    f"🎬 [DEBUG] ❌ Exception fetching camera name: {db_error}"
                )
                logger.error(f"🎬 [DEBUG] Exception type: {type(db_error)}")
                import traceback

                logger.error(f"🎬 [DEBUG] Traceback: {traceback.format_exc()}")
                camera_name = f"Camera {device_id}"  # Fallback name
                logger.info(
                    f"🎬 [DEBUG] Using fallback name after error: '{camera_name}'"
                )

            logger.info(f"🎬 [DEBUG] === FINAL CAMERA NAME: '{camera_name}' ===")

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
            timeout = aiohttp.ClientTimeout(total=30, connect=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Set JWT token for authentication
                headers = {}
                auth_token = recording_info.get("auth_token")
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}"
                    logger.info(f"🎬 [DEBUG] ✅ Using auth token")
                else:
                    logger.warning(
                        f"🎬 [DEBUG] ⚠️ No auth token available"
                    )

                # Get user GUID from user profile since media service needs UUID format
                user_guid = None
                if auth_token:
                    logger.info("🎬 [DEBUG] Getting user profile for GUID...")
                    try:
                        async with session.get(
                            "http://localhost:8001/api/v1/users/profile",
                            headers={"Authorization": f"Bearer {auth_token}"},
                        ) as profile_response:
                            if profile_response.status == 200:
                                profile_data = await profile_response.json()
                                user_guid = profile_data.get("guid")
                                logger.info(
                                    "🎬 [DEBUG] ✅ Retrieved user GUID: %s",
                                    user_guid
                                )
                            else:
                                logger.warning(
                                    "🎬 [DEBUG] ⚠️ Failed to get user "
                                    "profile for GUID: %d",
                                    profile_response.status
                                )
                    except Exception as profile_error:
                        logger.warning(
                            "🎬 [DEBUG] ⚠️ Error getting user profile: %s",
                            profile_error
                        )

                # ALWAYS fetch GUID from Node service if we don't have it
                # The Media service requires UUID (GUID), not integer ID
                if not user_guid and user_id:
                    # Fetch GUID from Node service using integer ID
                    try:
                        logger.info(
                            f"🎬 [DEBUG] Fetching GUID for user_id: {user_id}"
                        )
                        logger.info(
                            f"🎬 [DEBUG] Auth token present: "
                            f"{bool(auth_token)}"
                        )
                        node_url = (
                            f"http://localhost:8001/api/v1/users/{user_id}"
                        )
                        
                        # Use auth headers if available
                        fetch_headers = headers.copy() if headers else {}
                        logger.info(
                            f"🎬 [DEBUG] Calling Node: {node_url}"
                        )
                        
                        async with session.get(
                            node_url, headers=fetch_headers
                        ) as node_response:
                            response_text = await node_response.text()
                            logger.info(
                                f"🎬 [DEBUG] Node response status: "
                                f"{node_response.status}"
                            )
                            
                            if node_response.status == 200:
                                user_data = await node_response.json()
                                user_guid = user_data.get("guid")
                                logger.info(
                                    f"🎬 [DEBUG] ✅ Got GUID: {user_guid}"
                                )
                            else:
                                logger.error(
                                    f"🎬 [DEBUG] Node error: "
                                    f"{node_response.status} - "
                                    f"{response_text[:200]}"
                                )
                    except Exception as e:
                        logger.error(
                            f"🎬 [DEBUG] Exception fetching GUID: {e}",
                            exc_info=True
                        )
                
                # Must have a valid GUID to proceed
                if not user_guid:
                    logger.error(
                        f"🎬 [DEBUG] ❌ Failed to get user GUID for "
                        f"user_id={user_id}. Uploads will fail!"
                    )
                    logger.error(
                        f"🎬 [DEBUG] auth_token was: "
                        f"{'present' if auth_token else 'missing'}"
                    )
                    # Continue anyway to see full error from Media service
                    final_user_id = user_id
                else:
                    final_user_id = user_guid
                
                logger.info(
                    f"🎬 [DEBUG] Using ID for upload: {final_user_id}"
                )
                    
                logger.info(
                    "🎬 [DEBUG] Final user GUID for upload: %s",
                    final_user_id
                )

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

                # Add device name for proper collection categorization
                logger.info(f"🎬 [DEBUG] === ADDING DEVICE NAME TO FORM ===")
                logger.info(f"🎬 [DEBUG] camera_name value: '{camera_name}'")
                data.add_field("device_name", camera_name)
                logger.info(f"🎬 [DEBUG] ✅ Device name added to form data")
                logger.info(f"🎬 [DEBUG] camera_name type: {type(camera_name)}")
                logger.info(f"🎬 [DEBUG] camera_name bool check: {bool(camera_name)}")

                if camera_name:
                    data.add_field("device_name", camera_name)
                    logger.info(
                        f"🎬 [DEBUG] ✅ Added device_name to upload: '{camera_name}'"
                    )
                else:
                    logger.warning(
                        f"🎬 [DEBUG] ❌ camera_name is empty/None, not adding to form"
                    )

                logger.info(f"🎬 [DEBUG] === FORM DATA READY FOR UPLOAD ===")

                # Debug: List all form fields
                logger.info(f"🎬 [DEBUG] Form fields being sent:")
                # Note: Can't iterate FormData easily, but let's log what we know we're sending

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

                            # Check if automatic face detection on save is enabled
                            # ✅ RE-ENABLED - November 20, 2025
                            # Service-to-service authentication is working properly.
                            # In-memory person-objects workflow now creates person_objects automatically.
                            await self._check_and_trigger_face_detection(
                                media_uuid, session, headers
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

                            # TODO: Clean up local file after successful upload
                            # DISABLED: Gateway embedded streaming needs local
                            # files for face detection overlay
                            # try:
                            #     logger.info("🎬 Cleaning up local file")
                            #     path_obj.unlink()
                            #     logger.info(
                            #         f"🎬 [DEBUG] ✅ Local file cleaned up: "
                            #         f"{file_path}"
                            #     )
                            # except Exception as cleanup_error:
                            #     logger.warning(
                            #         f"🎬 [DEBUG] ⚠️ Failed to clean up file "
                            #         f"{file_path}: {cleanup_error}"
                            #     )
                            logger.info(
                                f"🎬 [DEBUG] ✅ Local file preserved for Gateway "
                                f"streaming: {file_path}"
                            )

                            return {
                                "collection_id": collection_id,
                                "media_id": media_id,
                                "media_uuid": media_uuid,
                            }
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

    async def _check_and_trigger_face_detection(
        self, media_uuid: str, session, headers: Dict
    ):
        """Check global setting and trigger face detection if enabled."""
        logger.info(
            f"🎯 [FACE-DETECTION] Starting face detection check for media {media_uuid}"
        )
        try:
            # Service URLs
            NODE_SERVICE_URL = "http://localhost:8001"

            # Check the global face detection on save setting
            setting_url = f"{NODE_SERVICE_URL}/api/v1/settings/face_detection_on_save"
            
            logger.info(
                f"🎯 [FACE-DETECTION] Checking setting at: {setting_url}"
            )

            async with session.get(setting_url, headers=headers) as response:
                logger.info(
                    f"🎯 [FACE-DETECTION] Setting response status: {response.status}"
                )
                
                if response.status == 200:
                    setting_data = await response.json()
                    is_enabled = setting_data.get("value") == "true"
                    
                    logger.info(
                        f"🎯 [FACE-DETECTION] Setting value: {setting_data.get('value')}, "
                        f"is_enabled: {is_enabled}"
                    )

                    if is_enabled:
                        logger.info(
                            f"🎯 [FACE-DETECTION] Face detection on save is ENABLED, "
                            f"triggering workflow for media {media_uuid}"
                        )
                        await self._trigger_face_detection_workflow(
                            media_uuid, session, headers
                        )
                    else:
                        logger.info(
                            f"🎯 [FACE-DETECTION] Face detection on save is DISABLED, "
                            f"skipping workflow for media {media_uuid}"
                        )
                elif response.status == 404:
                    # Setting doesn't exist, default to ENABLED for continuous pipeline
                    logger.warning(
                        f"🎯 [FACE-DETECTION] Setting not found (404), "
                        f"DEFAULTING TO ENABLED for continuous pipeline"
                    )
                    # Trigger anyway since we want continuous pipeline
                    await self._trigger_face_detection_workflow(
                        media_uuid, session, headers
                    )
                else:
                    logger.warning(
                        f"🎯 [FACE-DETECTION] Failed to check setting: "
                        f"{response.status}, defaulting to ENABLED"
                    )
                    # Trigger anyway
                    await self._trigger_face_detection_workflow(
                        media_uuid, session, headers
                    )

        except Exception as e:
            logger.error(
                f"🎯 [FACE-DETECTION] ❌ Exception checking setting: {e}",
                exc_info=True
            )
            # Still try to trigger face detection even if setting check fails
            try:
                logger.info(
                    f"🎯 [FACE-DETECTION] Attempting face detection anyway after error..."
                )
                await self._trigger_face_detection_workflow(
                    media_uuid, session, headers
                )
            except Exception as fallback_error:
                logger.error(
                    f"🎯 [FACE-DETECTION] ❌ Fallback trigger also failed: {fallback_error}",
                    exc_info=True
                )

    async def _trigger_face_detection_workflow(
        self, media_uuid: str, session, headers: Dict
    ):
        """Trigger Enhanced Logic V2 face detection for uploaded media."""
        separator = "=" * 20
        logger.info(
            "🎯 [FACE-DETECTION] %s START TRIGGER %s", separator, separator
        )
        logger.info(
            "🎯 [FACE-DETECTION] Triggering workflow for media %s", media_uuid
        )
        logger.info(
            "🎯 [FACE-DETECTION] Headers present: %s", list(headers.keys())
        )
        
        try:
            # Import service auth utilities
            import sys
            from pathlib import Path
            # Add shared module to path
            shared_path = Path(__file__).parent.parent.parent.parent / "shared"
            if str(shared_path) not in sys.path:
                sys.path.insert(0, str(shared_path))
            
            from auth.service_auth import get_service_auth_headers
            
            # Service URLs
            ORCHESTRATOR_SERVICE_URL = "http://localhost:8002"

            # Trigger Enhanced Logic V2 face detection via orchestrator
            # Use frame_interval=10 to process every 10th frame (10x speedup)
            orchestrator_url = (
                f"{ORCHESTRATOR_SERVICE_URL}/api/v1/media/"
                f"{media_uuid}/faces/enhanced-v2?frame_interval=10"
            )
            
            # Use service-to-service authentication headers
            service_headers = get_service_auth_headers("ppl-meta-cameras")
            
            logger.info(
                "🎯 [FACE-DETECTION] Calling orchestrator URL: %s",
                orchestrator_url
            )
            logger.info("🎯 [FACE-DETECTION] Request method: GET")
            logger.info("🎯 [FACE-DETECTION] Using service auth token (frame_interval=10)")

            async with session.get(
                orchestrator_url, headers=service_headers
            ) as response:
                response_status = response.status
                logger.info(
                    "🎯 [FACE-DETECTION] Orchestrator response status: %d",
                    response_status
                )
                
                # Read response body for logging
                result = None
                error_text = None
                try:
                    if response.content_type == 'application/json':
                        result = await response.json()
                        logger.info(
                            "🎯 [FACE-DETECTION] Response body (JSON): %s",
                            result
                        )
                    else:
                        error_text = await response.text()
                        logger.info(
                            "🎯 [FACE-DETECTION] Response body (text): %s",
                            error_text[:500]
                        )
                except Exception as read_error:
                    logger.error(
                        "🎯 [FACE-DETECTION] Failed to read response: %s",
                        read_error
                    )
                
                if response_status == 200:
                    session_uuid = (
                        result.get("session_uuid", "unknown")
                        if result else "unknown"
                    )
                    total_faces = (
                        result.get("total_faces", 0)
                        if result else 0
                    )
                    source = (
                        result.get("source", "unknown")
                        if result else "unknown"
                    )
                    processing_time = (
                        result.get("processing_time", 0)
                        if result else 0
                    )

                    logger.info(
                        "🎯 [FACE-DETECTION] ✅ Enhanced Logic V2 completed "
                        "for media %s: %d faces found "
                        "(%s, %.3fs, session: %s)",
                        media_uuid, total_faces, source,
                        processing_time, session_uuid
                    )
                else:
                    error_msg = (
                        error_text if error_text else "unknown error"
                    )
                    logger.error(
                        "🎯 [FACE-DETECTION] ❌ Failed to trigger for "
                        "media %s: %d - %s",
                        media_uuid, response_status, error_msg
                    )
                    
        except asyncio.TimeoutError:
            logger.error(
                "🎯 [FACE-DETECTION] ❌ TIMEOUT calling orchestrator for "
                "media %s - request took too long",
                media_uuid,
                exc_info=True
            )
        except aiohttp.ClientError as ce:
            logger.error(
                "🎯 [FACE-DETECTION] ❌ CLIENT ERROR calling orchestrator "
                "for media %s: %s - %s",
                media_uuid, type(ce).__name__, ce,
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "🎯 [FACE-DETECTION] ❌ UNEXPECTED EXCEPTION triggering for "
                "media %s: %s - %s",
                media_uuid, type(e).__name__, e,
                exc_info=True
            )
        finally:
            logger.info(
                "🎯 [FACE-DETECTION] %s END TRIGGER %s", separator, separator
            )


# Global camera detection service instance
camera_service = CameraDetectionService()

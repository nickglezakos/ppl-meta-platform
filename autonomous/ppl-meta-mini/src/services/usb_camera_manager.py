"""
Enhanced USB Camera Manager for PPL Meta Mini - Upgrade 2 Implementation
Provides USB camera and embedded camera detection, connection, and recording.
Supports both external USB cameras and built-in embedded cameras.
"""

import asyncio
import logging
import platform
import subprocess
import time
import cv2
import os
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor


class USBCameraManager:
    """
    Enhanced camera manager supporting both USB and embedded cameras.
    Detects and manages external USB cameras and built-in webcams/embedded cameras.
    """

    def __init__(self):
        """Initialize the camera manager."""
        self.logger = logging.getLogger(__name__)
        self.connected_camera = None
        self.camera_index = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.platform_os = platform.system()
        
        self.logger.info("USBCameraManager initialized")

    def __del__(self):
        """Cleanup when manager is destroyed."""
        if self.executor:
            self.executor.shutdown(wait=False)

    async def detect_usb_cameras(self) -> List[Dict[str, Any]]:
        """
        Detect all available cameras including USB and embedded cameras.
        
        Returns:
            List[Dict]: List of detected camera information
        """
        self.logger.info("🔍 Detecting USB and embedded cameras...")
        
        cameras = []
        # Check more indices to catch both USB and embedded cameras
        max_camera_index = 10
        
        for index in range(max_camera_index):
            try:
                camera_info = await self._test_camera_index(index)
                if camera_info:
                    # Determine camera type based on index and platform
                    camera_type = self._determine_camera_type(index, camera_info)
                    camera_info.update({
                        "camera_type": camera_type,
                        "platform": self.platform_os
                    })
                    cameras.append(camera_info)
                    self.logger.info("✅ Found camera at index %d: %s", index, camera_info['name'])
            except Exception as e:
                self.logger.debug("No camera at index %d: %s", index, e)
                continue
        
        self.logger.info("🎥 Camera detection complete. Found %d camera(s)", len(cameras))
        return cameras

    def _determine_camera_type(self, index: int, camera_info: Dict[str, Any]) -> str:
        """
        Determine if a camera is USB, embedded, or webcam based on index and properties.
        
        Args:
            index: Camera index
            camera_info: Camera information dict
            
        Returns:
            str: Camera type ("USB", "WEBCAM", "EMBEDDED")
        """
        # Get camera name/description for analysis
        name = camera_info.get("name", "").lower()
        
        # Platform-specific detection logic
        if self.platform_os == "Darwin":  # macOS
            if index == 0:
                # Index 0 is typically the built-in FaceTime camera on Mac
                if "facetime" in name or "built-in" in name or "isight" in name:
                    return "EMBEDDED"
                else:
                    # Could be USB camera that got index 0
                    return "USB"
            else:
                # Higher indices are typically USB cameras
                return "USB"
                
        elif self.platform_os == "Linux":  # Linux (including Raspberry Pi)
            if index == 0:
                # Check if it's a built-in camera using system tools
                if self._is_embedded_camera_linux(index):
                    return "EMBEDDED"
                else:
                    return "USB"
            else:
                return "USB"
                
        elif self.platform_os == "Windows":  # Windows
            if index == 0:
                # Windows integrated cameras usually at index 0
                if "integrated" in name or "webcam" in name:
                    return "EMBEDDED"
                else:
                    return "USB"
            else:
                return "USB"
        
        # Default fallback
        if index == 0:
            return "WEBCAM"  # Generic webcam for unknown platforms
        else:
            return "USB"

    def _is_embedded_camera_linux(self, index: int) -> bool:
        """
        Check if a camera is embedded on Linux systems.
        
        Args:
            index: Camera index
            
        Returns:
            bool: True if camera appears to be embedded
        """
        try:
            # Check for USB device information
            result = subprocess.run(
                ["lsusb"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                usb_devices = result.stdout.lower()
                # Look for common embedded camera identifiers
                embedded_indicators = [
                    "integrated camera", 
                    "built-in", 
                    "webcam",
                    "uvcvideo"  # Common driver for embedded cameras
                ]
                
                # If we find USB camera devices, index 0 might still be USB
                if any(indicator in usb_devices for indicator in ["camera", "webcam", "video"]):
                    return False  # Likely USB if USB video devices present
                else:
                    return True  # No USB video devices, likely embedded
            
            # Check /sys/class/video4linux for device information
            video_device_path = f"/sys/class/video4linux/video{index}"
            if os.path.exists(video_device_path):
                # Read device name if available
                name_file = os.path.join(video_device_path, "name")
                if os.path.exists(name_file):
                    with open(name_file, 'r') as f:
                        device_name = f.read().strip().lower()
                        embedded_names = ["integrated", "built-in", "bcm", "csi"]
                        return any(name in device_name for name in embedded_names)
                        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, PermissionError):
            # If we can't determine, assume it's USB for safety
            pass
            
        return False

    async def _test_camera_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Test if a camera exists at the given index and return its info.
        
        Args:
            index: Camera index to test
            
        Returns:
            Optional[Dict]: Camera information if found, None otherwise
        """
        def test_camera():
            """Synchronous camera test to run in thread pool."""
        """
        Detect all available USB cameras on the system.
        
        Returns:
            List[Dict]: List of detected camera information
        """
        self.logger.info("🔍 Detecting USB cameras...")
        cameras = []
        
        # Test camera indices 0-4 (covers most common setups)
        for index in range(5):
            try:
                # Run camera detection in thread pool to avoid blocking
                camera_info = await asyncio.get_event_loop().run_in_executor(
                    None, self._test_camera_index, index
                )
                
                if camera_info:
                    cameras.append(camera_info)
                    self.logger.info(f"✅ Found camera at index {index}: {camera_info['name']}")
                
            except Exception as e:
                self.logger.debug(f"No camera at index {index}: {e}")
                continue
        
        self.logger.info(f"🎥 Camera detection complete. Found {len(cameras)} camera(s)")
        return cameras

    def _test_camera_index(self, index: int) -> Optional[Dict]:
        """
        Test if a camera exists at the given index.
        
        Args:
            index: Camera index to test
            
        Returns:
            Camera info dict if camera exists, None otherwise
        """
        cap = None
        try:
            cap = cv2.VideoCapture(index)
            
            # Set a timeout for camera initialization
            cap.set(cv2.CAP_PROP_TIMEOUT, 3000)  # 3 seconds
            
            if not cap.isOpened():
                return None
            
            # Try to read a frame to verify camera is working
            ret, frame = cap.read()
            if not ret or frame is None:
                return None
            
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            backend = cap.getBackendName()
            
            # Generate camera info
            camera_info = {
                "device_id": f"usb_camera_{index}",
                "index": index,
                "name": f"USB Camera {index}",
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "fps": fps if fps > 0 else self.default_fps,
                "backend": backend,
                "status": "available"
            }
            
            return camera_info
            
        except Exception as e:
            self.logger.debug(f"Error testing camera index {index}: {e}")
            return None
        finally:
            if cap is not None:
                cap.release()

    async def connect_camera(self, camera_index: int = 0) -> bool:
        """
        Connect to a specific USB camera.
        
        Args:
            camera_index: Index of the camera to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        self.logger.info(f"🔌 Connecting to camera at index {camera_index}...")
        
        try:
            # Disconnect existing camera if connected
            if self.is_connected:
                await self.disconnect_camera()
            
            # Run connection in thread pool to avoid blocking
            success = await asyncio.get_event_loop().run_in_executor(
                None, self._connect_camera_sync, camera_index
            )
            
            if success:
                self.logger.info(f"✅ Successfully connected to camera {camera_index}")
                return True
            else:
                self.logger.error(f"❌ Failed to connect to camera {camera_index}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error connecting to camera {camera_index}: {e}")
            return False

    def _connect_camera_sync(self, camera_index: int) -> bool:
        """
        Synchronous camera connection logic.
        
        Args:
            camera_index: Camera index to connect to
            
        Returns:
            bool: True if successful
        """
        try:
            self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                return False
            
            # Set camera properties for optimal performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.default_resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.default_resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.default_fps)
            
            # Verify camera is working
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.camera.release()
                return False
            
            # Store camera information
            self.camera_index = camera_index
            self.is_connected = True
            self.camera_info = {
                "device_id": f"usb_camera_{camera_index}",
                "index": camera_index,
                "name": f"USB Camera {camera_index}",
                "resolution": f"{int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
                "fps": self.camera.get(cv2.CAP_PROP_FPS),
                "backend": self.camera.getBackendName(),
                "status": "connected"
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Sync camera connection error: {e}")
            if self.camera:
                self.camera.release()
            return False

    async def disconnect_camera(self) -> bool:
        """
        Disconnect the current camera.
        
        Returns:
            bool: True if disconnection successful
        """
        self.logger.info("🔌 Disconnecting camera...")
        
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            
            self.camera_index = None
            self.camera_info = {}
            self.is_connected = False
            
            self.logger.info("✅ Camera disconnected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error disconnecting camera: {e}")
            return False

    async def get_camera_info(self) -> Dict:
        """
        Get information about the currently connected camera.
        
        Returns:
            Dict: Camera information
        """
        if not self.is_connected:
            return {
                "status": "not_connected",
                "message": "No camera currently connected"
            }
        
        return {
            "status": "connected",
            **self.camera_info
        }

    async def record_video(self, duration: float, output_path: str, quality: str = "medium") -> str:
        """
        Record video from the connected USB camera.
        
        Args:
            duration: Recording duration in seconds
            output_path: Path where to save the recorded video
            quality: Recording quality ["high", "medium", "low"]
            
        Returns:
            str: Path to the recorded video file
            
        Raises:
            RuntimeError: If no camera is connected or recording fails
        """
        if not self.is_connected or self.camera is None:
            raise RuntimeError("No camera connected. Call connect_camera() first.")
        
        self.logger.info(f"🎥 Starting video recording for {duration} seconds...")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Set quality parameters
        resolution, fps = self._get_quality_settings(quality)
        
        try:
            # Run recording in thread pool to avoid blocking
            result_path = await asyncio.get_event_loop().run_in_executor(
                None, self._record_video_sync, duration, output_path, resolution, fps
            )
            
            self.logger.info(f"✅ Video recording completed: {result_path}")
            return result_path
            
        except Exception as e:
            self.logger.error(f"❌ Video recording failed: {e}")
            raise RuntimeError(f"Video recording failed: {e}")

    def _get_quality_settings(self, quality: str) -> Tuple[Tuple[int, int], int]:
        """
        Get resolution and FPS settings based on quality level.
        
        Args:
            quality: Quality level ["high", "medium", "low"]
            
        Returns:
            Tuple of (resolution, fps)
        """
        quality_settings = {
            "high": ((1920, 1080), 30),    # 1080p 30fps
            "medium": ((1280, 720), 30),   # 720p 30fps  
            "low": ((640, 480), 15)        # 480p 15fps
        }
        
        return quality_settings.get(quality, quality_settings["medium"])

    def _record_video_sync(self, duration: float, output_path: str, 
                          resolution: Tuple[int, int], fps: int) -> str:
        """
        Synchronous video recording logic.
        
        Args:
            duration: Recording duration in seconds
            output_path: Output file path
            resolution: Video resolution (width, height)
            fps: Frames per second
            
        Returns:
            str: Path to recorded video
        """
        # Set camera resolution
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.camera.set(cv2.CAP_PROP_FPS, fps)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, resolution)
        
        if not out.isOpened():
            raise RuntimeError(f"Failed to open video writer for {output_path}")
        
        start_time = time.time()
        frame_count = 0
        
        try:
            while time.time() - start_time < duration:
                ret, frame = self.camera.read()
                
                if not ret:
                    self.logger.warning("Failed to read frame from camera")
                    continue
                
                # Resize frame if needed
                if frame.shape[1] != resolution[0] or frame.shape[0] != resolution[1]:
                    frame = cv2.resize(frame, resolution)
                
                out.write(frame)
                frame_count += 1
                
                # Small delay to maintain target FPS
                time.sleep(1.0 / fps)
        
        finally:
            out.release()
        
        actual_duration = time.time() - start_time
        self.logger.info(
            f"📹 Recording completed: {frame_count} frames in {actual_duration:.2f}s "
            f"(target: {duration}s)"
        )
        
        return output_path

    async def capture_frame(self) -> Optional[bytes]:
        """
        Capture a single frame from the connected camera.
        
        Returns:
            Optional[bytes]: JPEG encoded frame data, None if capture fails
        """
        if not self.is_connected or self.camera is None:
            return None
        
        try:
            ret, frame = self.camera.read()
            if not ret or frame is None:
                return None
            
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer.tobytes()
            
        except Exception as e:
            self.logger.error(f"❌ Frame capture failed: {e}")
            return None

    def is_camera_connected(self) -> bool:
        """
        Check if a camera is currently connected.
        
        Returns:
            bool: True if camera is connected
        """
        return self.is_connected and self.camera is not None

    def __del__(self):
        """Cleanup on object destruction."""
        if self.camera is not None:
            self.camera.release()
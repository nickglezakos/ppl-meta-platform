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


class EnhancedCameraManager:
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
        
        # Default quality settings for different recording modes
        self.quality_settings = {
            "high": {"resolution": (1920, 1080), "fps": 30},
            "medium": {"resolution": (1280, 720), "fps": 30},
            "low": {"resolution": (640, 480), "fps": 15}
        }
        
        # Raspberry Pi optimized defaults
        self.default_resolution = (1280, 720)
        self.default_fps = 30
        
        self.logger.info("EnhancedCameraManager initialized for platform: %s", self.platform_os)

    def __del__(self):
        """Cleanup when manager is destroyed."""
        if self.executor:
            self.executor.shutdown(wait=False)

    async def detect_cameras(self) -> List[Dict[str, Any]]:
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
                    self.logger.info("✅ Found %s camera at index %d: %s", 
                                   camera_type, index, camera_info['name'])
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
                if any(keyword in name for keyword in ["facetime", "built-in", "isight"]):
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
                if any(keyword in name for keyword in ["integrated", "webcam"]):
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
                timeout=5,
                check=False
            )
            
            if result.returncode == 0:
                usb_devices = result.stdout.lower()
                
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
                    with open(name_file, 'r', encoding='utf-8') as f:
                        device_name = f.read().strip().lower()
                        embedded_names = ["integrated", "built-in", "bcm", "csi"]
                        return any(name in device_name for name in embedded_names)
                        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, 
                FileNotFoundError, PermissionError):
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
            try:
                cap = cv2.VideoCapture(index)
                
                if not cap.isOpened():
                    return None
                
                # Try to read a frame to verify the camera works
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    cap.release()
                    return None
                
                # Get camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                cap.release()
                
                return {
                    "index": index,
                    "name": f"Camera {index}",
                    "resolution_width": width,
                    "resolution_height": height,
                    "fps": fps if fps > 0 else self.default_fps,
                    "supports_streaming": True,
                    "supports_recording": True,
                    "connection_string": str(index)
                }
                
            except Exception as e:
                self.logger.debug("Error testing camera index %d: %s", index, e)
                return None
        
        # Run camera test in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(self.executor, test_camera)

    async def connect_camera(self, camera_index: int) -> bool:
        """
        Connect to a camera at the specified index.
        
        Args:
            camera_index: Index of the camera to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.connected_camera is not None:
            self.logger.warning("Camera already connected at index %d", self.camera_index)
            return True
        
        self.logger.info("🔌 Connecting to camera at index %d...", camera_index)
        
        try:
            # Run connection in thread pool to avoid blocking
            success = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._sync_connect_camera, camera_index
            )
            
            if success:
                self.camera_index = camera_index
                self.logger.info("✅ Successfully connected to camera %d", camera_index)
                return True
            else:
                self.logger.error("❌ Failed to connect to camera %d", camera_index)
                return False
        
        except Exception as e:
            self.logger.error("❌ Error connecting to camera %d: %s", camera_index, e)
            return False

    def _sync_connect_camera(self, camera_index: int) -> bool:
        """
        Synchronous camera connection for thread pool execution.
        
        Args:
            camera_index: Camera index to connect to
            
        Returns:
            bool: True if connection successful
        """
        try:
            camera = cv2.VideoCapture(camera_index)
            
            if camera.isOpened():
                # Set optimal properties for better performance
                camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer lag
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.default_resolution[0])
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.default_resolution[1])
                camera.set(cv2.CAP_PROP_FPS, self.default_fps)
                
                # Test read to ensure camera is working
                ret, _ = camera.read()
                if ret:
                    self.connected_camera = camera
                    return True
                else:
                    camera.release()
                    return False
            else:
                return False
                
        except Exception as e:
            self.logger.error("Sync camera connection error: %s", e)
            return False

    async def disconnect_camera(self) -> bool:
        """
        Disconnect the currently connected camera.
        
        Returns:
            bool: True if disconnection successful
        """
        if self.connected_camera is None:
            self.logger.warning("No camera connected to disconnect")
            return True
        
        try:
            # Run disconnection in thread pool
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self._sync_disconnect_camera
            )
            
            self.connected_camera = None
            self.camera_index = None
            self.logger.info("✅ Camera disconnected successfully")
            return True
            
        except Exception as e:
            self.logger.error("❌ Error disconnecting camera: %s", e)
            return False

    def _sync_disconnect_camera(self):
        """Synchronous camera disconnection."""
        if self.connected_camera:
            self.connected_camera.release()

    def is_camera_connected(self) -> bool:
        """
        Check if a camera is currently connected.
        
        Returns:
            bool: True if camera is connected
        """
        return self.connected_camera is not None

    async def get_camera_info(self) -> Dict[str, Any]:
        """
        Get information about the current camera connection status.
        
        Returns:
            Dict: Camera information
        """
        if self.connected_camera is None:
            return {
                "status": "not_connected",
                "message": "No camera currently connected"
            }
        
        try:
            # Get current camera properties
            width = int(self.connected_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.connected_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.connected_camera.get(cv2.CAP_PROP_FPS)
            
            return {
                "status": "connected",
                "camera_index": self.camera_index,
                "resolution": f"{width}x{height}",
                "fps": fps,
                "platform": self.platform_os
            }
        
        except Exception as e:
            self.logger.error("Error getting camera info: %s", e)
            return {
                "status": "error",
                "message": f"Error getting camera info: {e}"
            }

    async def record_video(self, duration: float, output_path: str, quality: str = "medium") -> str:
        """
        Record video from the connected camera.
        
        Args:
            duration: Recording duration in seconds
            output_path: Path to save the recorded video
            quality: Recording quality ("high", "medium", "low")
            
        Returns:
            str: Path to the recorded video file
            
        Raises:
            RuntimeError: If no camera is connected or recording fails
        """
        if self.connected_camera is None:
            raise RuntimeError("No camera connected")
        
        self.logger.info("🎥 Starting video recording for %s seconds...", duration)
        
        try:
            # Run recording in thread pool to avoid blocking
            result_path = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._sync_record_video, duration, output_path, quality
            )
            
            if result_path:
                self.logger.info("✅ Video recording completed: %s", result_path)
                return result_path
            else:
                raise RuntimeError("Video recording failed")
        
        except Exception as e:
            self.logger.error("❌ Video recording failed: %s", e)
            raise RuntimeError(f"Video recording failed: {e}") from e

    def _sync_record_video(self, duration: float, output_path: str, quality: str) -> str:
        """
        Synchronous video recording for thread pool execution.
        
        Args:
            duration: Recording duration in seconds
            output_path: Output file path
            quality: Recording quality
            
        Returns:
            str: Path to recorded file
        """
        if not self.connected_camera:
            raise RuntimeError("Camera not connected")
        
        # Get quality settings
        settings = self._get_quality_settings(quality)
        resolution = settings["resolution"]
        fps = settings["fps"]
        
        # Configure camera for recording
        self.connected_camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.connected_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.connected_camera.set(cv2.CAP_PROP_FPS, fps)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, resolution)
        
        start_time = time.time()
        frame_count = 0
        
        try:
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                if elapsed_time >= duration:
                    break
                
                ret, frame = self.connected_camera.read()
                if ret and frame is not None:
                    # Resize frame if necessary
                    if frame.shape[:2][::-1] != resolution:
                        frame = cv2.resize(frame, resolution)
                    
                    out.write(frame)
                    frame_count += 1
                else:
                    self.logger.warning("Failed to read frame during recording")
                    break
            
            actual_duration = time.time() - start_time
            
        finally:
            out.release()
        
        # Log recording statistics
        self.logger.info(
            "📹 Recording completed: %d frames in %.2fs (target: %.2fs)",
            frame_count, actual_duration, duration
        )
        
        return output_path

    def _get_quality_settings(self, quality: str) -> Dict[str, Any]:
        """
        Get recording settings for the specified quality level.
        
        Args:
            quality: Quality level ("high", "medium", "low")
            
        Returns:
            Dict: Recording settings (resolution, fps)
        """
        settings = self.quality_settings.get(quality, self.quality_settings["medium"])
        
        # For Raspberry Pi, limit high quality to avoid performance issues
        if self.platform_os == "Linux" and quality == "high":
            # Use medium settings for Pi high quality
            settings = self.quality_settings["medium"]
        
        return settings
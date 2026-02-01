"""Camera capture module using OpenCV."""
import cv2
import logging
import threading
import time
from typing import Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class CameraCapture:
    """Handle camera capture operations."""
    
    def __init__(self, device_id: int = 0, width: int = 1280, height: int = 720, fps: int = 15):
        """
        Initialize camera capture.
        
        Args:
            device_id: Camera device index
            width: Frame width
            height: Frame height
            fps: Frames per second
        """
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        self.last_frame_time = 0
        
    def start(self) -> bool:
        """
        Start camera capture.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting camera capture on device {self.device_id}")
            
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                logger.error("Failed to open camera")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera configured: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            self.is_running = True
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a single frame from camera.
        
        Returns:
            Tuple of (success, frame)
        """
        if not self.is_running or self.cap is None:
            return False, None
        
        try:
            with self.lock:
                ret, frame = self.cap.read()
                
                if ret:
                    self.latest_frame = frame
                    self.frame_count += 1
                    self.last_frame_time = time.time()
                    return True, frame
                else:
                    logger.warning("Failed to read frame from camera")
                    return False, None
                    
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return False, None
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame."""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def stop(self):
        """Stop camera capture."""
        logger.info("Stopping camera capture")
        self.is_running = False
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.latest_frame = None
    
    def is_healthy(self) -> bool:
        """Check if camera is healthy."""
        if not self.is_running or self.cap is None:
            return False
        
        # Check if we've received frames recently (within last 5 seconds)
        if self.last_frame_time > 0:
            time_since_last_frame = time.time() - self.last_frame_time
            return time_since_last_frame < 5.0
        
        return False
    
    def get_stats(self) -> dict:
        """Get camera statistics."""
        return {
            "device_id": self.device_id,
            "resolution": {"width": self.width, "height": self.height},
            "fps": self.fps,
            "is_running": self.is_running,
            "frame_count": self.frame_count,
            "last_frame_time": self.last_frame_time,
            "is_healthy": self.is_healthy()
        }

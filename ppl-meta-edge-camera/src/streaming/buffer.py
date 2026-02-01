"""Frame buffer for streaming."""
import logging
import threading
from collections import deque
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class FrameBuffer:
    """Thread-safe frame buffer for streaming."""
    
    def __init__(self, max_size: int = 10):
        """
        Initialize frame buffer.
        
        Args:
            max_size: Maximum number of frames to buffer
        """
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.dropped_frames = 0
        
    def put(self, frame_data: Dict[str, Any]) -> bool:
        """
        Add frame to buffer.
        
        Args:
            frame_data: Frame data dict with encoded frame and metadata
            
        Returns:
            True if added, False if buffer full and frame dropped
        """
        with self.lock:
            # Check if buffer is full
            if len(self.buffer) >= self.max_size:
                self.dropped_frames += 1
                logger.warning(f"Buffer full, dropping frame. Total dropped: {self.dropped_frames}")
                return False
            
            self.buffer.append(frame_data)
            return True
    
    def get(self) -> Optional[Dict[str, Any]]:
        """
        Get next frame from buffer.
        
        Returns:
            Frame data dict or None if buffer empty
        """
        with self.lock:
            if len(self.buffer) > 0:
                return self.buffer.popleft()
            return None
    
    def clear(self):
        """Clear all frames from buffer."""
        with self.lock:
            self.buffer.clear()
            logger.debug("Frame buffer cleared")
    
    def size(self) -> int:
        """Get current buffer size."""
        with self.lock:
            return len(self.buffer)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        with self.lock:
            return {
                "current_size": len(self.buffer),
                "max_size": self.max_size,
                "dropped_frames": self.dropped_frames,
                "utilization": len(self.buffer) / self.max_size if self.max_size > 0 else 0
            }

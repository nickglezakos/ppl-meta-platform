"""Frame encoding module."""
import cv2
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class FrameEncoder:
    """Encode frames for streaming."""
    
    def __init__(self, encoding: str = "mjpeg", quality: int = 80):
        """
        Initialize frame encoder.
        
        Args:
            encoding: Encoding format (mjpeg, h264)
            quality: Encoding quality (0-100 for JPEG)
        """
        self.encoding = encoding.lower()
        self.quality = quality
        
        # JPEG encoding parameters
        self.jpeg_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        
        logger.info(f"Frame encoder initialized: {encoding} quality={quality}")
    
    def encode_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Encode a frame to bytes.
        
        Args:
            frame: Input frame (numpy array)
            
        Returns:
            Encoded frame as bytes, or None if encoding fails
        """
        if frame is None:
            return None
        
        try:
            if self.encoding == "mjpeg":
                return self._encode_jpeg(frame)
            else:
                logger.warning(f"Unsupported encoding: {self.encoding}, falling back to JPEG")
                return self._encode_jpeg(frame)
                
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def _encode_jpeg(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode frame as JPEG."""
        ret, buffer = cv2.imencode('.jpg', frame, self.jpeg_params)
        
        if ret:
            return buffer.tobytes()
        else:
            logger.error("Failed to encode frame as JPEG")
            return None
    
    def encode_frame_with_metadata(self, frame: np.ndarray, timestamp: float, frame_number: int) -> Optional[dict]:
        """
        Encode frame with metadata.
        
        Args:
            frame: Input frame
            timestamp: Frame timestamp
            frame_number: Frame sequence number
            
        Returns:
            Dict with encoded frame and metadata
        """
        encoded = self.encode_frame(frame)
        
        if encoded is None:
            return None
        
        return {
            "data": encoded,
            "timestamp": timestamp,
            "frame_number": frame_number,
            "encoding": self.encoding,
            "size": len(encoded)
        }

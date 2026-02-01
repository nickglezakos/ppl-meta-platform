"""Streaming client for sending frames to platform."""
import logging
import requests
import threading
import time
from typing import Optional, Dict, Any
import io

logger = logging.getLogger(__name__)


class StreamingClient:
    """Handle streaming frames to cameras service."""
    
    def __init__(self, cameras_url: str, device_id: str, buffer, api_key: Optional[str] = None):
        """
        Initialize streaming client.
        
        Args:
            cameras_url: Cameras service URL
            device_id: Device identifier
            buffer: FrameBuffer instance
            api_key: JWT token for authentication
        """
        self.cameras_url = cameras_url.rstrip('/')
        self.device_id = device_id
        self.buffer = buffer
        self.api_key = api_key
        
        self.is_streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        self.frames_sent = 0
        self.errors_count = 0
        self.last_error: Optional[str] = None
        
    def start(self) -> bool:
        """
        Start streaming thread.
        
        Returns:
            True if started successfully
        """
        if self.is_streaming:
            logger.warning("Streaming already active")
            return True
        
        logger.info("Starting streaming client")
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        return True
    
    def stop(self):
        """Stop streaming thread."""
        if not self.is_streaming:
            return
        
        logger.info("Stopping streaming client")
        self.is_streaming = False
        
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
            self.stream_thread = None
    
    def _stream_loop(self):
        """Main streaming loop."""
        logger.info("Streaming loop started")
        
        while self.is_streaming:
            try:
                # Get frame from buffer
                frame_data = self.buffer.get()
                
                if frame_data is None:
                    # No frames available, wait a bit
                    time.sleep(0.01)
                    continue
                
                # Send frame to platform
                success = self._send_frame(frame_data)
                
                if success:
                    self.frames_sent += 1
                else:
                    self.errors_count += 1
                    
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                self.errors_count += 1
                self.last_error = str(e)
                time.sleep(1)  # Back off on error
        
        logger.info("Streaming loop stopped")
    
    def _send_frame(self, frame_data: Dict[str, Any]) -> bool:
        """
        Send a single frame to cameras service.
        
        Args:
            frame_data: Frame data dict
            
        Returns:
            True if sent successfully
        """
        try:
            # Prepare multipart form data
            files = {
                'frame': ('frame.jpg', io.BytesIO(frame_data['data']), 'image/jpeg')
            }
            
            data = {
                'device_id': self.device_id,
                'timestamp': frame_data['timestamp'],
                'frame_number': frame_data['frame_number'],
                'encoding': frame_data['encoding']
            }
            
            # Prepare authentication headers
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # Send to cameras service edge endpoint
            response = requests.post(
                f"{self.cameras_url}/api/v1/cameras/edge/{self.device_id}/frame",
                files=files,
                data=data,
                headers=headers,
                timeout=5
            )
            
            if response.status_code in [200, 201, 202]:
                logger.debug(f"Frame {frame_data['frame_number']} sent successfully")
                return True
            else:
                logger.warning(f"Frame upload failed: {response.status_code}")
                self.last_error = f"HTTP {response.status_code}"
                return False
                
        except requests.exceptions.Timeout:
            logger.warning("Frame upload timeout")
            self.last_error = "Timeout"
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Frame upload error: {e}")
            self.last_error = str(e)
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending frame: {e}")
            self.last_error = str(e)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        return {
            "is_streaming": self.is_streaming,
            "frames_sent": self.frames_sent,
            "errors_count": self.errors_count,
            "last_error": self.last_error,
            "buffer_stats": self.buffer.get_stats()
        }

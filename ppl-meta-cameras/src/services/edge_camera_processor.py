"""
Edge Camera Frame Processor - Integrates edge camera frames into existing pipeline.

Processes frames received from edge cameras and integrates them with the unified
camera worker architecture, enabling instant detection, recording, and continuous
pipeline processing.
"""

import logging
import cv2
import numpy as np
from typing import Dict, Optional
import collections
from src.models.camera import CameraType
from src.services.camera_worker import CameraWorker, CameraStatus

logger = logging.getLogger(__name__)


class EdgeCameraFrameProcessor:
    """
    Processes edge camera frames using existing camera worker infrastructure.
    
    Architecture:
        Edge Camera → WebSocket → receive_edge_camera_frame()
            → EdgeCameraFrameProcessor.process_frame()
            → CameraWorker.frame_buffer
            → [StreamingEndpoint, RecordingService, InstantDetectionService]
    
    This enables edge cameras to work exactly like USB/RTSP cameras with:
    - Instant detection
    - Video recording
    - Vision service integration
    - Demographic triggers
    """
    
    def __init__(self):
        """Initialize edge camera frame processor."""
        # device_id -> CameraWorker mapping
        self.workers: Dict[str, CameraWorker] = {}
        # device_id -> frame_number mapping (for deduplication)
        self.frame_numbers: Dict[str, int] = {}
        logger.info("✅ Edge camera frame processor initialized")
    
    def get_or_create_worker(
        self,
        device_id: str,
        camera_info: Dict,
        enable_instant_detection: bool = False
    ) -> CameraWorker:
        """
        Get existing camera worker or create new one for edge camera.
        
        Args:
            device_id: Edge camera device ID
            camera_info: Camera configuration dict
            enable_instant_detection: If True, enable instant detection
            
        Returns:
            CameraWorker instance
        """
        if device_id not in self.workers:
            logger.info(f"Creating new camera worker for edge camera: {device_id}")
            
            worker = CameraWorker(
                device_id=device_id,
                camera_type=CameraType.EDGE,
                camera_info=camera_info,
                enable_instant_detection=enable_instant_detection
            )
            
            # Set back-reference so worker can access frame_numbers
            worker.edge_processor = self
            
            # Start worker thread
            worker.start()
            
            # Set to connected status (edge cameras are "always connected" via WebSocket)
            worker.status = CameraStatus.CONNECTED
            
            # Initialize instant detection if enabled
            if enable_instant_detection:
                detection_config = camera_info.get("detection_config", {
                    "interval_seconds": camera_info.get("instant_detection_interval_seconds", 5)
                })
                worker.start_detection(detection_config)
                logger.info(f"✅ Instant detection enabled for edge camera {device_id}")
            
            self.workers[device_id] = worker
            logger.info(f"✅ Camera worker created and started for edge camera: {device_id}")
        
        return self.workers[device_id]
    
    def process_frame(
        self,
        device_id: str,
        frame_bytes: bytes,
        frame_number: int,
        camera_info: Dict,
        enable_instant_detection: bool = True
    ) -> bool:
        """
        Process edge camera frame and push to camera worker pipeline.
        
        Args:
            device_id: Edge camera device ID
            frame_bytes: JPEG/MJPEG frame data
            frame_number: Frame sequence number from edge device
            camera_info: Camera configuration
            enable_instant_detection: Enable instant detection
            
        Returns:
            True if frame processed successfully, False otherwise
        """
        try:
            # Decode frame from JPEG bytes
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.error(f"Failed to decode frame from edge camera {device_id}")
                return False
            
            # Get or create worker for this edge camera
            worker = self.get_or_create_worker(
                device_id=device_id,
                camera_info=camera_info,
                enable_instant_detection=enable_instant_detection
            )
            
            # Store frame_number for this device (for worker to check)
            self.frame_numbers[device_id] = frame_number
            
            # Push frame to worker's frame buffer (same as USB/RTSP cameras)
            # This makes the frame available to:
            # - Instant detection sampler (pulls from frame_buffer)
            # - Recording service (if recording active)
            # - Streaming endpoints (for frontend display)
            if len(worker.frame_buffer) > 0:
                worker.frame_buffer.pop()  # Remove old frame
            worker.frame_buffer.append(frame)
            
            # Update stats (these are incremented here, not in worker loop)
            worker.frames_read += 1
            worker.last_frame_time = cv2.getTickCount() / cv2.getTickFrequency()
            
            logger.debug(f"✅ Frame #{frame_number} pushed to pipeline for edge camera {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing edge camera frame: {e}")
            return False
    
    def stop_worker(self, device_id: str):
        """Stop and remove camera worker for edge camera."""
        if device_id in self.workers:
            worker = self.workers.pop(device_id)
            worker.stop(timeout=5.0)
            logger.info(f"✅ Camera worker stopped for edge camera: {device_id}")
    
    def get_worker(self, device_id: str) -> Optional[CameraWorker]:
        """Get camera worker for edge camera if exists."""
        return self.workers.get(device_id)
    
    def is_worker_active(self, device_id: str) -> bool:
        """Check if camera worker exists and is active for edge camera."""
        return device_id in self.workers and self.workers[device_id].status == CameraStatus.CONNECTED


# Global singleton instance
_edge_processor: Optional[EdgeCameraFrameProcessor] = None


def get_edge_processor() -> EdgeCameraFrameProcessor:
    """Get the global edge camera frame processor instance."""
    global _edge_processor
    if _edge_processor is None:
        _edge_processor = EdgeCameraFrameProcessor()
    return _edge_processor

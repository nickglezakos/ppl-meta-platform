"""
Mobile Camera Worker - Background task for processing mobile camera frames.

This module implements a background worker that bridges mobile camera frames
into the unified queue-based architecture, enabling instant detection, recording,
and continuous pipeline processing for mobile cameras.

Architecture:
- Async background task per mobile camera
- Pulls frames from mobile streaming service
- Applies rotation transformations
- Pushes frames to camera worker frame buffer
- Enables seamless integration with existing services
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any

import cv2
import numpy as np

from src.services.camera_worker import CameraWorker
from src.models.camera import CameraType

logger = logging.getLogger(__name__)


class MobileCameraWorker:
    """
    Background worker for mobile camera frame processing.
    
    This worker acts as a bridge between the mobile streaming service
    (which receives frames via HTTP POST) and the unified camera worker
    architecture (which provides frames to streaming, recording, and detection).
    
    Flow:
        Mobile App → HTTP POST → MobileStreamingService.store_frame()
            → MobileCameraWorker (this class) → CameraWorker.frame_buffer
            → [StreamingEndpoint, RecordingService, InstantDetectionService]
    
    Usage:
        worker = MobileCameraWorker(device_id="mobile_123", camera_info={...})
        await worker.start()
        
        # Worker runs in background, continuously processing frames
        # ... (frames flow automatically) ...
        
        await worker.stop()
    """
    
    def __init__(self, device_id: str, camera_info: Dict[str, Any], enable_instant_detection: bool = False):
        """
        Initialize mobile camera worker.
        
        Args:
            device_id: Mobile device identifier (e.g., "mobile_TKQ1.221114.001")
            camera_info: Camera configuration dictionary
            enable_instant_detection: If True, enable instant detection for this camera
        """
        self.device_id = device_id
        self.camera_info = camera_info
        self.enable_instant_detection = enable_instant_detection
        
        # Create underlying camera worker for frame buffer and integration
        self.camera_worker = CameraWorker(
            device_id=device_id,
            camera_type=CameraType.MOBILE,
            camera_info=camera_info,
            enable_instant_detection=enable_instant_detection
        )
        
        # Start the camera worker thread
        self.camera_worker.start()
        
        # Set camera worker to connected state (mobile cameras are "always connected" when streaming)
        from src.services.camera_worker import CameraStatus
        self.camera_worker.status = CameraStatus.CONNECTED
        
        # 🔧 Initialize instant detection if enabled
        if enable_instant_detection:
            detection_config = camera_info.get("detection_config", {
                "interval_seconds": camera_info.get("instant_detection_interval_seconds", 5)
            })
            self.camera_worker.start_detection(detection_config)
            logger.info(f"✅ Instant detection enabled for mobile worker {device_id}")
        
        # Task control
        self.is_active = False
        self.task: Optional[asyncio.Task] = None
        
        # Frame processing stats
        self.frames_processed = 0
        self.frames_dropped = 0
        self.last_frame_time = 0.0
        
        # Frame rate management
        self.target_fps = 30
        self.frame_interval = 1.0 / self.target_fps
        
        logger.info(f"✅ MobileCameraWorker initialized for {device_id}")
    
    async def start(self):
        """Start processing mobile camera frames."""
        if self.is_active:
            logger.warning(f"⚠️ Mobile worker already active for {device_id}")
            return
        
        self.is_active = True
        self.task = asyncio.create_task(self._process_frames())
        logger.info(f"🚀 Mobile worker started for {self.device_id}")
    
    async def stop(self):
        """Stop processing frames."""
        if not self.is_active:
            return
        
        logger.info(f"🛑 Stopping mobile worker for {self.device_id}")
        self.is_active = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Stop underlying camera worker
        self.camera_worker.stop(timeout=5.0)
        
        logger.info(f"✅ Mobile worker stopped for {self.device_id}")
    
    async def _process_frames(self):
        """
        Continuously pull frames from mobile storage and push to camera worker.
        
        This is the core processing loop that runs in the background.
        """
        from src.services.mobile_streaming import mobile_streaming_service
        
        logger.info(f"📱 Frame processing loop started for {self.device_id}")
        
        consecutive_empty_frames = 0
        max_empty_frames = 150  # 5 seconds at 30fps
        
        while self.is_active:
            try:
                # Get latest frame data from mobile streaming service
                frame_data = await mobile_streaming_service.get_latest_mobile_frame_data(self.device_id)
                
                if frame_data:
                    frame = frame_data.get("frame")
                    rotation_angle = frame_data.get("rotation_angle", 0)
                    orientation = frame_data.get("orientation", "portraitUp")
                    timestamp = frame_data.get("timestamp", time.time())
                    
                    if frame is not None:
                        # Apply rotation
                        if rotation_angle != 0:
                            frame = self._rotate_frame(frame, rotation_angle)
                            logger.debug(f"📱 Rotated frame by {rotation_angle}° for {self.device_id}")
                        
                        # Push to camera worker frame buffer
                        # The camera worker's frame_buffer is a deque with maxlen=1,
                        # so this automatically replaces the old frame
                        self.camera_worker.frame_buffer.append(frame)
                        
                        # Update stats
                        self.frames_processed += 1
                        self.last_frame_time = time.time()
                        consecutive_empty_frames = 0
                        
                        # Update camera worker stats
                        self.camera_worker.frames_read = self.frames_processed
                        self.camera_worker.last_frame_time = self.last_frame_time
                        
                        logger.debug(f"📱 Frame processed and added to buffer for {self.device_id} (total: {self.frames_processed})")
                    else:
                        consecutive_empty_frames += 1
                else:
                    consecutive_empty_frames += 1
                
                # Check for stream timeout
                if consecutive_empty_frames >= max_empty_frames:
                    logger.warning(f"⏱️ No frames received for {self.device_id} in 5 seconds, continuing to poll...")
                    consecutive_empty_frames = 0  # Reset and continue
                
                # Frame rate control
                await asyncio.sleep(self.frame_interval)
                
            except asyncio.CancelledError:
                logger.info(f"📱 Frame processing loop cancelled for {self.device_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error processing frame for {self.device_id}: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
        
        logger.info(f"📱 Frame processing loop ended for {self.device_id}")
    
    def _rotate_frame(self, frame: np.ndarray, rotation_angle: int) -> np.ndarray:
        """
        Apply rotation to frame based on mobile device orientation.
        
        Args:
            frame: Input frame from mobile camera
            rotation_angle: Rotation angle (90, 180, 270)
        
        Returns:
            Rotated frame
        """
        if rotation_angle == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation_angle == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation_angle == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return frame
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get the latest frame from the camera worker buffer.
        
        Returns:
            Latest frame or None if no frame available
        """
        return self.camera_worker.get_latest_frame()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get worker status information.
        
        Returns:
            Status dictionary with stats
        """
        return {
            "device_id": self.device_id,
            "is_active": self.is_active,
            "camera_type": "mobile",
            "frames_processed": self.frames_processed,
            "frames_dropped": self.frames_dropped,
            "last_frame_time": self.last_frame_time,
            "target_fps": self.target_fps,
            "camera_worker_status": self.camera_worker.status.value,
            "instant_detection_enabled": self.enable_instant_detection,
        }
    
    def get_camera_worker(self) -> CameraWorker:
        """
        Get the underlying camera worker.
        
        This allows other services to access the camera worker directly
        for streaming, recording, and detection integration.
        
        Returns:
            CameraWorker instance
        """
        return self.camera_worker


# Worker management
_active_mobile_workers: Dict[str, MobileCameraWorker] = {}


async def start_mobile_worker(device_id: str, camera_info: Dict[str, Any], enable_instant_detection: bool = False) -> MobileCameraWorker:
    """
    Start a mobile camera worker for a device.
    
    Args:
        device_id: Mobile device identifier
        camera_info: Camera configuration
        enable_instant_detection: Enable instant detection
    
    Returns:
        MobileCameraWorker instance
    """
    global _active_mobile_workers
    
    # Check if worker already exists
    if device_id in _active_mobile_workers:
        logger.info(f"✅ Mobile worker already running for {device_id}")
        return _active_mobile_workers[device_id]
    
    # Create and start new worker
    worker = MobileCameraWorker(
        device_id=device_id,
        camera_info=camera_info,
        enable_instant_detection=enable_instant_detection
    )
    
    await worker.start()
    _active_mobile_workers[device_id] = worker
    
    logger.info(f"✅ Started mobile worker for {device_id}")
    return worker


async def stop_mobile_worker(device_id: str):
    """
    Stop a mobile camera worker.
    
    Args:
        device_id: Mobile device identifier
    """
    global _active_mobile_workers
    
    if device_id not in _active_mobile_workers:
        logger.warning(f"⚠️ No active mobile worker for {device_id}")
        return
    
    worker = _active_mobile_workers[device_id]
    await worker.stop()
    
    del _active_mobile_workers[device_id]
    logger.info(f"✅ Stopped mobile worker for {device_id}")


def get_mobile_worker(device_id: str) -> Optional[MobileCameraWorker]:
    """
    Get an active mobile camera worker.
    
    Args:
        device_id: Mobile device identifier
    
    Returns:
        MobileCameraWorker instance or None
    """
    return _active_mobile_workers.get(device_id)


def get_all_mobile_workers() -> Dict[str, MobileCameraWorker]:
    """
    Get all active mobile camera workers.
    
    Returns:
        Dictionary of device_id -> MobileCameraWorker
    """
    return _active_mobile_workers.copy()


async def cleanup_all_mobile_workers():
    """Stop all active mobile camera workers."""
    global _active_mobile_workers
    
    logger.info(f"🧹 Cleaning up {len(_active_mobile_workers)} mobile workers")
    
    workers = list(_active_mobile_workers.keys())
    for device_id in workers:
        await stop_mobile_worker(device_id)
    
    logger.info("✅ All mobile workers cleaned up")

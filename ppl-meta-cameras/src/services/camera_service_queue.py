"""
Camera Detection Service - Queue Architecture Integration.

This module provides the main camera service interface that uses the
worker-based queue architecture for camera operations.

MIGRATION STATUS: This is the new queue-based implementation.
The old camera_detection.py will be gradually migrated to use this.
"""

import asyncio
import logging
from typing import Dict, List, Optional
import cv2

from src.config import get_config
from src.models.camera import CameraType
from src.services.worker_manager import get_worker_manager
from src.services.camera_worker import CameraWorker, CameraStatus, CameraCommand

logger = logging.getLogger(__name__)
config = get_config()


class CameraService:
    """
    Camera service using queue-based worker architecture.
    
    This is the new implementation that uses dedicated worker threads
    with command queues for each camera instance.
    
    Usage:
        service = CameraService()
        
        # Connect camera
        success = await service.connect_camera(device_id, camera_info)
        
        # Get latest frame (for instant detection)
        frame = await service.get_latest_frame(device_id)
        
        # Get video stream
        stream = await service.get_camera_stream(device_id)
        
        # Disconnect camera
        await service.disconnect_camera(device_id)
    """
    
    def __init__(self):
        self.worker_manager = get_worker_manager()
        # Cache for camera info from detection
        self.detected_cameras: Dict[str, Dict] = {}
        logger.info("✅ CameraService initialized with queue architecture")
    
    async def detect_available_cameras(self) -> List[Dict]:
        """
        Detect all available cameras on the system.
        
        Returns:
            List of camera info dicts
        """
        logger.info("🔍 Starting camera detection...")
        cameras = []
        
        # Detect USB cameras
        usb_cameras = await self._detect_usb_cameras()
        cameras.extend(usb_cameras)
        
        # Update cache
        self.detected_cameras = {cam["device_id"]: cam for cam in cameras}
        
        logger.info(f"✅ Detected {len(cameras)} cameras")
        return cameras
    
    async def _detect_usb_cameras(self) -> List[Dict]:
        """Detect USB cameras available on system."""
        cameras = []
        
        # Get list of already connected cameras to skip
        from src.services.worker_manager import get_worker_manager
        manager = get_worker_manager()
        connected_workers = manager.get_all_workers()
        
        logger.info(f"🔍 [DETECT] Currently connected workers: {list(connected_workers.keys())}")
        
        # Try indices 0-9
        for index in range(10):
            device_id = f"usb_camera_{index}"
            
            # ⚠️ CRITICAL: Skip if camera worker exists (ANY status)
            # Opening cv2.VideoCapture() for a camera that has an active worker
            # will force the existing worker's VideoCapture to fail on macOS
            if device_id in connected_workers:
                worker = connected_workers[device_id]
                logger.warning(f"⏭️ SKIPPING {device_id} - WORKER EXISTS (status: {worker.status.value}) - will NOT open VideoCapture")
                # Return cached info from worker's camera_info
                width = int(worker.camera_info.get('resolution_width', 0))
                height = int(worker.camera_info.get('resolution_height', 0))
                fps = worker.camera_info.get('max_fps', 30)
                camera_info = {
                    "device_id": device_id,
                    "name": f"USB Camera {index}",
                    "camera_type": CameraType.USB,
                    "connection_string": f"/dev/video{index}",
                    "index": index,
                    "resolution_width": width,
                    "resolution_height": height,
                    "max_fps": fps,
                    "status": worker.status.value  # Use actual worker status
                }
                cameras.append(camera_info)
                continue
            
            try:
                # Quick test if camera exists
                loop = asyncio.get_event_loop()
                cap = await loop.run_in_executor(
                    None,
                    lambda: cv2.VideoCapture(index)
                )
                
                is_opened = await loop.run_in_executor(None, cap.isOpened)
                
                if is_opened:
                    # Get camera properties
                    def get_properties():
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        return width, height, fps
                    
                    width, height, fps = await loop.run_in_executor(None, get_properties)
                    
                    camera_info = {
                        "device_id": device_id,
                        "name": f"USB Camera {index}",
                        "camera_type": CameraType.USB,
                        "connection_string": f"/dev/video{index}",
                        "index": index,
                        "resolution_width": width,
                        "resolution_height": height,
                        "max_fps": fps if fps > 0 else 30,
                        "status": "available"
                    }
                    
                    cameras.append(camera_info)
                    logger.info(f"✅ Found {device_id} at index {index} ({width}x{height})")
                
                # Release test capture
                await loop.run_in_executor(None, cap.release)
                
            except Exception as e:
                logger.debug(f"No camera at index {index}: {e}")
                continue
        
        return cameras
    
    async def connect_camera(self, device_id: str, camera_info: Optional[Dict] = None) -> bool:
        """
        Connect to a camera using worker queue architecture.
        
        Args:
            device_id: Camera identifier
            camera_info: Camera configuration (optional, uses cached if not provided)
            
        Returns:
            True if connection successful
        """
        # Get camera info from cache if not provided
        if not camera_info:
            camera_info = self.detected_cameras.get(device_id)
            
            # If not in cache and USB camera, try on-demand detection
            if not camera_info and device_id.startswith("usb_camera_"):
                index = int(device_id.split("_")[-1])
                camera_info = {
                    "device_id": device_id,
                    "name": f"USB Camera {index}",
                    "camera_type": CameraType.USB,
                    "connection_string": f"/dev/video{index}",
                    "index": index
                }
                self.detected_cameras[device_id] = camera_info
            
            # If not in cache and RTSP camera, load from database
            elif not camera_info and device_id.startswith("rtsp_"):
                camera_info = await self._load_rtsp_from_database(device_id)
                if camera_info:
                    self.detected_cameras[device_id] = camera_info
            
            if not camera_info:
                logger.error(f"❌ Camera info not found for {device_id}")
                return False
        
        # Get or create worker
        try:
            worker = await self.worker_manager.get_or_create_worker(
                device_id=device_id,
                camera_type=camera_info["camera_type"],
                camera_info=camera_info
            )
        except RuntimeError as e:
            logger.error(f"❌ Failed to create worker: {e}")
            return False
        
        # Send connect command
        try:
            cmd_id = worker.send_command({
                'action': CameraCommand.CONNECT,
                'connection_string': camera_info.get('connection_string')
            })
            
            # Poll for result with async delays (no executor blocking)
            timeout = 15.0
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check if result ready (non-blocking)
                result = worker.get_result(cmd_id)
                if result is not None:
                    break
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.error(f"❌ Connection timeout for {device_id}")
                    return False
                
                # Async sleep (doesn't block executor)
                await asyncio.sleep(0.1)
            
            if result.get('success'):
                logger.info(f"✅ Camera connected: {device_id}")
                return True
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ Connection failed: {error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting camera: {e}")
            return False
    
    async def disconnect_camera(self, device_id: str) -> bool:
        """
        Disconnect camera.
        
        Args:
            device_id: Camera identifier
            
        Returns:
            True if disconnection successful
        """
        worker = self.worker_manager.get_worker(device_id)
        if not worker:
            logger.warning(f"⚠️ Worker not found for {device_id}")
            return False
        
        try:
            cmd_id = worker.send_command({'action': CameraCommand.DISCONNECT})
            
            # Poll for result with async delays (no executor blocking)
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check if result ready (non-blocking)
                result = worker.get_result(cmd_id)
                if result is not None:
                    break
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.error(f"❌ Disconnection timeout for {device_id}")
                    return False
                
                # Async sleep (doesn't block executor)
                await asyncio.sleep(0.05)
            
            if result.get('success'):
                logger.info(f"✅ Camera disconnected: {device_id}")
                # Don't remove worker yet, keep it for reconnection
                return True
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ Disconnection failed: {error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error disconnecting camera: {e}")
            return False
    
    async def get_latest_frame(self, device_id: str):
        """
        Get latest frame from camera buffer (instant, non-blocking).
        
        Used by instant detection sampler.
        
        Args:
            device_id: Camera identifier
            
        Returns:
            Frame as numpy array, or None if not available
        """
        worker = self.worker_manager.get_worker(device_id)
        if not worker:
            return None
        
        return worker.get_latest_frame()
    
    async def get_camera_stream(self, device_id: str) -> Optional[CameraWorker]:
        """
        Get camera worker for streaming.
        
        The worker continuously buffers frames that can be read by streaming endpoints.
        
        Args:
            device_id: Camera identifier
            
        Returns:
            CameraWorker instance or None
        """
        worker = self.worker_manager.get_worker(device_id)
        if not worker or worker.status != CameraStatus.CONNECTED:
            logger.warning(f"⚠️ Camera not connected: {device_id}")
            return None
        
        return worker
    
    def get_connected_cameras(self) -> List[str]:
        """
        Get list of connected camera device IDs.
        
        Returns:
            List of device IDs
        """
        workers = self.worker_manager.get_connected_workers()
        return [w.device_id for w in workers]
    
    def get_camera_status(self, device_id: str) -> Optional[str]:
        """
        Get camera connection status.
        
        Args:
            device_id: Camera identifier
            
        Returns:
            Status string or None if worker not found
        """
        worker = self.worker_manager.get_worker(device_id)
        if not worker:
            return None
        
        return worker.status.value
    
    def get_camera_stats(self, device_id: str) -> Optional[Dict]:
        """
        Get camera worker statistics.
        
        Args:
            device_id: Camera identifier
            
        Returns:
            Stats dict or None if worker not found
        """
        worker = self.worker_manager.get_worker(device_id)
        if not worker:
            return None
        
        return worker.get_stats()
    
    async def _load_rtsp_from_database(self, device_id: str) -> Optional[Dict]:
        """Load RTSP camera info from database."""
        try:
            def load_from_db():
                from src.database import get_db
                from src.models.camera import Camera
                
                db = next(get_db())
                try:
                    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
                    if camera and camera.camera_type == CameraType.RTSP:
                        return {
                            "device_id": camera.device_id,
                            "name": camera.name,
                            "camera_type": CameraType.RTSP,
                            "connection_string": camera.connection_string,
                            "resolution_width": camera.resolution_width,
                            "resolution_height": camera.resolution_height,
                            "max_fps": camera.max_fps,
                        }
                    return None
                finally:
                    db.close()
            
            loop = asyncio.get_event_loop()
            camera_info = await loop.run_in_executor(None, load_from_db)
            
            if camera_info:
                logger.info(f"✅ RTSP camera {device_id} loaded from database")
            else:
                logger.warning(f"⚠️ RTSP camera {device_id} not found in database")
            
            return camera_info
            
        except Exception as e:
            logger.error(f"❌ Error loading RTSP camera from database: {e}")
            return None


# Global camera service instance
_camera_service: Optional[CameraService] = None


def get_camera_service() -> CameraService:
    """
    Get global camera service instance (singleton).
    
    Returns:
        CameraService instance
    """
    global _camera_service
    
    if _camera_service is None:
        _camera_service = CameraService()
    
    return _camera_service

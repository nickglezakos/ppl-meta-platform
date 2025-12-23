"""
CameraPoolManager - Centralized manager for multiple cameras.

Instead of one thread per camera, this uses a SINGLE thread that reads
from all cameras sequentially. This prevents resource contention and
system overload on limited hardware.

BENEFITS:
- Single thread for ALL cameras (no thread explosion)
- Rate limiting per camera (configurable FPS)
- Fair resource distribution (round-robin)
- Easy to enforce camera limits (max 5 cameras)

REVERSIBLE:
- Can be disabled via config flag
- Falls back to original per-camera threads
"""

import logging
import threading
import time
from typing import Dict, Any, Tuple
import cv2
import json

# Optional Redis support for distributed state
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CameraInfo:
    """Information about a managed camera."""
    
    def __init__(self, device_id: str, cap: cv2.VideoCapture, target_fps: int = 10):
        self.device_id = device_id
        self.cap = cap
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps  # Time between frames
        self.last_read_time = 0.0
        self.error_count = 0
        self.max_errors = 50
        self.frame_count = 0  # Track total frames read
        self.connected_at = time.time()  # When camera was added
        
    def should_read_frame(self) -> bool:
        """Check if enough time has passed to read next frame."""
        current_time = time.time()
        if current_time - self.last_read_time >= self.frame_interval:
            self.last_read_time = current_time
            return True
        return False


class CameraPoolManager:
    """
    Centralized manager for multiple cameras.
    
    Uses a single thread to read from all cameras sequentially,
    preventing resource contention and system overload.
    """
    
    def __init__(self, max_cameras: int = 5, target_fps: int = 10):
        """
        Initialize the camera pool manager.
        
        Args:
            max_cameras: Maximum number of simultaneous cameras
            target_fps: Target frames per second per camera
        """
        self.max_cameras = max_cameras
        self.target_fps = target_fps
        
        self.cameras: Dict[str, CameraInfo] = {}
        self.frame_buffers: Dict[str, Tuple[bool, Any]] = {}
        self.local_state_cache: Dict[str, dict] = {}  # Fast in-memory state
        
        self.running = False
        self.distributor_thread: threading.Thread = None
        self.lock = threading.Lock()
        
        # Redis connection (optional)
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost', port=6379, db=0, 
                    decode_responses=True, socket_timeout=1
                )
                self.redis_client.ping()
                logger.info("🎯 [CAMERA-POOL] Redis connected for distributed state")
            except Exception as e:
                logger.warning(f"🎯 [CAMERA-POOL] Redis unavailable: {e} - using memory only")
                self.redis_client = None
        
        logger.info(
            f"🎯 [CAMERA-POOL] Initialized (max_cameras={max_cameras}, "
            f"target_fps={target_fps})"
        )
    
    def start(self):
        """Start the camera pool manager."""
        if self.running:
            logger.warning("🎯 [CAMERA-POOL] Already running")
            return
        
        self.running = True
        self.distributor_thread = threading.Thread(
            target=self._distribute_loop,
            daemon=True,
            name="CameraPoolDistributor"
        )
        self.distributor_thread.start()
        logger.info("🎯 [CAMERA-POOL] Started distributor thread")
    
    def stop(self):
        """Stop the camera pool manager."""
        if not self.running:
            return
        
        self.running = False
        if self.distributor_thread:
            self.distributor_thread.join(timeout=2.0)
        logger.info("🎯 [CAMERA-POOL] Stopped")
    
    def add_camera(self, device_id: str, cap: cv2.VideoCapture) -> bool:
        """
        Add a camera to the pool.
        
        Args:
            device_id: Unique camera identifier
            cap: OpenCV VideoCapture object
        
        Returns:
            True if added successfully, False if pool is full
        """
        with self.lock:
            if len(self.cameras) >= self.max_cameras:
                logger.error(
                    f"🎯 [CAMERA-POOL] Cannot add {device_id}: "
                    f"pool full ({len(self.cameras)}/{self.max_cameras})"
                )
                return False
            
            if device_id in self.cameras:
                logger.warning(f"🎯 [CAMERA-POOL] Camera {device_id} already in pool")
                return True
            
            camera_info = CameraInfo(device_id, cap, self.target_fps)
            self.cameras[device_id] = camera_info
            logger.info(
                f"🎯 [CAMERA-POOL] Added camera {device_id} "
                f"({len(self.cameras)}/{self.max_cameras})"
            )
            return True
    
    def remove_camera(self, device_id: str):
        """Remove a camera from the pool."""
        with self.lock:
            if device_id in self.cameras:
                del self.cameras[device_id]
                if device_id in self.frame_buffers:
                    del self.frame_buffers[device_id]
                logger.info(f"🎯 [CAMERA-POOL] Removed camera {device_id}")
    
    def get_frame(self, device_id: str) -> Tuple[bool, Any]:
        """
        Get the latest frame for a camera.
        
        Args:
            device_id: Camera identifier
        
        Returns:
            Tuple of (success, frame)
        """
        with self.lock:
            if device_id in self.frame_buffers:
                return self.frame_buffers[device_id]
            return (False, None)
    
    def get_camera_state(self, device_id: str) -> dict:
        """
        Get real-time camera state (HYBRID: memory + Redis).
        NO DATABASE QUERIES - instant response.
        
        Args:
            device_id: Camera identifier
        
        Returns:
            Dict with real-time state info
        """
        # Try local cache first (fastest)
        if device_id in self.local_state_cache:
            cached_state = self.local_state_cache[device_id]
            age = time.time() - cached_state.get("cached_at", 0)
            if age < 2.0:  # Cache valid for 2 seconds
                return cached_state
        
        # Build fresh state
        with self.lock:
            if device_id not in self.cameras:
                state = {
                    "status": "disconnected",
                    "has_frames": False,
                    "is_reading": False
                }
            else:
                camera = self.cameras[device_id]
                has_frames = device_id in self.frame_buffers
                latest_frame_time = camera.last_read_time if has_frames else None
                
                state = {
                    "status": "connected",
                    "has_frames": has_frames,
                    "is_reading": camera.error_count < camera.max_errors,
                    "frame_count": camera.frame_count,
                    "error_count": camera.error_count,
                    "latest_frame_age": time.time() - latest_frame_time if latest_frame_time else None,
                    "uptime_seconds": time.time() - camera.connected_at,
                    "target_fps": camera.target_fps
                }
        
        # Update caches
        state["cached_at"] = time.time()
        self.local_state_cache[device_id] = state
        
        # Update Redis (non-blocking, best-effort)
        if self.redis_client:
            try:
                key = f"camera:state:{device_id}"
                self.redis_client.setex(key, 10, json.dumps(state))  # 10s TTL
            except Exception as e:
                logger.debug(f"🎯 [CAMERA-POOL] Redis update failed: {e}")
        
        return state
    
    def get_all_states(self) -> Dict[str, dict]:
        """Get states for all cameras."""
        with self.lock:
            camera_ids = list(self.cameras.keys())
        
        return {
            camera_id: self.get_camera_state(camera_id)
            for camera_id in camera_ids
        }
    
    def _distribute_loop(self):
        """
        Main distribution loop - reads from all cameras sequentially.
        
        This runs in a single thread and services all cameras in round-robin
        fashion, respecting rate limits for each camera.
        """
        logger.info("🎯 [CAMERA-POOL] Distributor loop started")
        iteration_count = 0
        
        try:
            while self.running:
                iteration_count += 1
                
                # Make a copy of camera IDs to iterate safely
                with self.lock:
                    camera_ids = list(self.cameras.keys())
                
                if not camera_ids:
                    # No cameras, sleep longer
                    time.sleep(0.1)
                    continue
                
                # Read from each camera if its time interval has passed
                for camera_id in camera_ids:
                    if not self.running:
                        break
                    
                    with self.lock:
                        if camera_id not in self.cameras:
                            continue
                        camera_info = self.cameras[camera_id]
                    
                    # Check if we should read a frame (rate limiting)
                    if camera_info.should_read_frame():
                        try:
                            # Use grab() + retrieve() for better control
                            # grab() is faster and less blocking than read()
                            ret = camera_info.cap.grab()  # Non-blocking frame grab
                            if ret:
                                ret, frame = camera_info.cap.retrieve()  # Decode grabbed frame
                                
                                if ret and frame is not None:
                                    # Store in buffer
                                    with self.lock:
                                        self.frame_buffers[camera_id] = (ret, frame.copy())
                                    camera_info.error_count = 0
                                    camera_info.frame_count += 1
                                    camera_info.last_read_time = time.time()
                                    
                                    # Log every 100 frames per camera
                                    if camera_info.frame_count % 100 == 0:
                                        logger.debug(
                                            f"🎯 [CAMERA-POOL] {camera_id}: "
                                            f"{camera_info.frame_count} frames captured"
                                        )
                                else:
                                    camera_info.error_count += 1
                            else:
                                # Grab failed (camera not ready or network issue)
                                camera_info.error_count += 1
                            
                            # Check if too many errors
                            if camera_info.error_count > camera_info.max_errors:
                                logger.error(
                                    f"🎯 [CAMERA-POOL] Too many errors for {camera_id}, "
                                    f"removing from pool"
                                )
                                self.remove_camera(camera_id)
                        
                        except Exception as e:
                            camera_info.error_count += 1
                            logger.error(f"🎯 [CAMERA-POOL] Error reading {camera_id}: {e}")
                            if camera_info.error_count > camera_info.max_errors:
                                self.remove_camera(camera_id)
                
                # Small sleep to prevent CPU spinning
                # With 5 cameras at 10 FPS, we need to check ~50 times/sec
                time.sleep(0.01)  # 100 Hz loop
        
        except Exception as e:
            logger.error(f"🎯 [CAMERA-POOL] Fatal error in distributor: {e}")
        finally:
            logger.info("🎯 [CAMERA-POOL] Distributor loop exited")


# Global instance (can be disabled via config)
camera_pool_manager = CameraPoolManager(max_cameras=5, target_fps=10)

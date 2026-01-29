"""
Camera Worker - Dedicated thread with command queue for each camera instance.

This module implements the queue-based camera architecture where each camera
gets its own dedicated worker thread with a command queue. This completely
decouples camera operations from the FastAPI async event loop.

Key Features:
- Dedicated thread per camera instance
- Command queue for async operations (connect, disconnect, etc.)
- Frame buffer for instant detection and streaming
- Thread-safe status management
- Autonomous frame reading loop
"""

import cv2
import queue
import threading
import time
import uuid
import collections
import logging
import asyncio
import os
import datetime
from typing import Optional, Dict, Any, Deque, List
from enum import Enum
import numpy as np

from src.models.camera import CameraType

logger = logging.getLogger(__name__)


class CameraCommand(str, Enum):
    """Command types for camera worker queue."""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    GET_FRAME = "get_frame"
    UPDATE_SETTINGS = "update_settings"
    STOP = "stop"


class CameraStatus(str, Enum):
    """Camera worker status states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    STOPPING = "stopping"


class CameraWorker:
    """
    Dedicated worker thread with command queue for a single camera.
    
    Architecture:
    - Runs in dedicated thread (all blocking operations safe)
    - Commands sent via queue (non-blocking from async event loop)
    - Frame buffer shared with main thread (thread-safe deque)
    - Status updates via atomic operations
    
    Usage:
        worker = CameraWorker(device_id="usb_camera_0", camera_type=CameraType.USB)
        worker.start()
        
        # Send connect command (non-blocking)
        cmd_id = worker.send_command({
            'action': CameraCommand.CONNECT,
            'connection_string': '/dev/video0',
            'settings': {...}
        })
        
        # Wait for result
        result = worker.wait_for_result(cmd_id, timeout=15.0)
        
        # Get latest frame (instant, non-blocking)
        frame = worker.get_latest_frame()
        
        # Cleanup
        worker.stop()
    """
    
    def __init__(self, device_id: str, camera_type: CameraType, camera_info: Dict[str, Any], enable_instant_detection: bool = False):
        """
        Initialize camera worker.
        
        Args:
            device_id: Unique camera identifier
            camera_type: Type of camera (USB, RTSP, MOBILE)
            camera_info: Camera configuration dict
            enable_instant_detection: If True, enable instant detection for this worker
        """
        self.device_id = device_id
        self.camera_type = camera_type
        self.camera_info = camera_info
        
        # Command queue - async event loop sends commands here
        self.command_queue: queue.Queue = queue.Queue(maxsize=100)
        
        # Frame buffer - shared with main thread (thread-safe)
        # maxlen=1 ensures we always have latest frame only (no memory buildup)
        self.frame_buffer: Deque[np.ndarray] = collections.deque(maxlen=1)
        
        # Mobile camera support - fetch frames from MobileStreamingService
        self.mobile_streaming_service = None
        if camera_type == CameraType.MOBILE:
            from src.services.mobile_streaming import mobile_streaming_service
            self.mobile_streaming_service = mobile_streaming_service
        
        # Instant detection integration
        self.enable_instant_detection = enable_instant_detection
        self.detection_sampler = None
        self.detection_config = None
        
        # Command results - used to return results to caller
        self.command_results: Dict[str, Dict[str, Any]] = {}
        self.results_lock = threading.Lock()
        
        # Status - shared atomic state
        self._status = CameraStatus.DISCONNECTED
        self.status_lock = threading.Lock()
        
        # Error tracking
        self.last_error: Optional[str] = None
        self.error_count = 0
        
        # OpenCV capture - ONLY accessed by worker thread
        self.cap: Optional[cv2.VideoCapture] = None
        
        # Frame reading stats
        self.frames_read = 0
        self.frames_dropped = 0
        self.last_frame_time = 0.0
        
        # Recording state - ALL recording happens in worker thread
        self.is_recording = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording_start_time: Optional[float] = None
        self.recording_frames_written = 0
        self.recording_session_info: Optional[Dict[str, Any]] = None
        # Segment management (for continuous recording)
        self.segment_duration: Optional[float] = None  # Duration in seconds
        self.current_segment_start_time: Optional[float] = None
        self.current_segment_index: int = 0
        self.current_segment_path: Optional[str] = None
        self.session_dir: Optional[str] = None
        self.completed_segments: List[str] = []  # Track all completed segments
        self.batch_upload_size: int = 5  # Upload segments in batches of 5 (aligned with MVR batch size)
        self.segments_since_last_upload: int = 0  # Counter for incremental uploads
        
        # Collection assignment cache
        self.collection_cache: Dict[str, str] = {}  # device_id -> collection_uuid mapping
        
        # Thread control
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        
        logger.info(f"✅ CameraWorker initialized for {device_id} ({camera_type})")
    
    @property
    def status(self) -> CameraStatus:
        """Get current status (thread-safe)."""
        with self.status_lock:
            return self._status
    
    @status.setter
    def status(self, value: CameraStatus):
        """Set status (thread-safe) and publish to Redis."""
        with self.status_lock:
            old_status = self._status
            self._status = value
            if old_status != value:
                logger.info(f"📊 Camera {self.device_id} status: {old_status} → {value}")
                
                # Publish status change to Redis (async, non-blocking)
                self._publish_status_change(old_status, value)
    
    def _publish_status_change(self, old_status: CameraStatus, new_status: CameraStatus):
        """
        Publish status change to Redis (non-blocking).
        
        Runs in a thread to avoid blocking the worker thread.
        """
        def publish_async():
            try:
                # Import here to avoid circular imports
                from src.services.status_notification_service import get_status_service, CameraStatusEvent
                
                # Map status to event
                event_map = {
                    CameraStatus.CONNECTED: CameraStatusEvent.CONNECTED,
                    CameraStatus.DISCONNECTED: CameraStatusEvent.DISCONNECTED,
                    CameraStatus.CONNECTING: CameraStatusEvent.CONNECTING,
                    CameraStatus.ERROR: CameraStatusEvent.ERROR,
                }
                
                event = event_map.get(new_status)
                if not event:
                    return
                
                # Get service and publish
                status_service = get_status_service()
                
                # Run async function in new event loop (we're in a thread)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        status_service.publish_status_change(
                            self.device_id,
                            event,
                            {
                                "old_status": old_status.value,
                                "camera_type": self.camera_type.value,
                                "frames_read": self.frames_read,
                            }
                        )
                    )
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.debug(f"Could not publish status change: {e}")
        
        # Run in separate thread to not block worker
        threading.Thread(target=publish_async, daemon=True).start()
    
    def start(self):
        """Start the worker thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning(f"⚠️ Worker thread already running for {self.device_id}")
            return
        
        self.stop_event.clear()
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name=f"CameraWorker-{self.device_id}",
            daemon=True
        )
        self.worker_thread.start()
        logger.info(f"🚀 Worker thread started for {self.device_id}")
    
    def stop(self, timeout: float = 5.0):
        """
        Stop the worker thread gracefully.
        
        Args:
            timeout: Max seconds to wait for thread to stop
        """
        logger.info(f"🛑 Stopping worker for {self.device_id}")
        self.status = CameraStatus.STOPPING
        
        # Stop detection first
        if self.detection_sampler:
            self.stop_detection()
        
        # Send stop command
        try:
            self.command_queue.put({
                'action': CameraCommand.STOP,
                'cmd_id': str(uuid.uuid4())
            }, timeout=1.0)
        except queue.Full:
            logger.warning(f"⚠️ Command queue full, setting stop event directly")
        
        # Set stop event
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=timeout)
            if self.worker_thread.is_alive():
                logger.error(f"❌ Worker thread did not stop cleanly for {self.device_id}")
            else:
                logger.info(f"✅ Worker thread stopped for {self.device_id}")
    
    def send_command(self, command: Dict[str, Any], timeout: float = 1.0) -> str:
        """
        Send command to worker queue (non-blocking).
        
        Args:
            command: Command dict with 'action' and other params
            timeout: Max seconds to wait if queue is full
            
        Returns:
            command_id for tracking results
            
        Raises:
            queue.Full: If command queue is full
        """
        cmd_id = command.get('cmd_id', str(uuid.uuid4()))
        command['cmd_id'] = cmd_id
        command['timestamp'] = time.time()
        
        try:
            self.command_queue.put(command, timeout=timeout)
            logger.debug(f"📤 Command sent to {self.device_id}: {command['action']}")
            return cmd_id
        except queue.Full:
            logger.error(f"❌ Command queue full for {self.device_id}")
            raise
    
    def get_result(self, cmd_id: str) -> Optional[Dict[str, Any]]:
        """
        Get command result if available (non-blocking).
        
        Args:
            cmd_id: Command ID to check
            
        Returns:
            Result dict if ready, None if still processing
        """
        with self.results_lock:
            if cmd_id in self.command_results:
                result = self.command_results.pop(cmd_id)
                return result
        return None
    
    def wait_for_result(self, cmd_id: str, timeout: float = 15.0) -> Dict[str, Any]:
        """
        Wait for command result (blocking - use get_result for async).
        
        Args:
            cmd_id: Command ID to wait for
            timeout: Max seconds to wait
            
        Returns:
            Result dict with 'success', 'error', etc.
            
        Raises:
            TimeoutError: If result not available within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.get_result(cmd_id)
            if result is not None:
                return result
            time.sleep(0.05)  # Reduced from 0.1 for faster response
        
        raise TimeoutError(f"Command {cmd_id} did not complete within {timeout}s")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get latest frame from buffer - INSTANT, non-blocking.
        
        Used by instant detection sampler.
        Returns None if no frame available.
        
        Returns:
            Latest frame as numpy array, or None
        """
        try:
            if self.frame_buffer:
                return self.frame_buffer[-1].copy()  # Return copy to avoid race conditions
            return None
        except (IndexError, RuntimeError):
            # Handle race condition if buffer is modified during access
            return None
    
    def request_fresh_frame(self) -> str:
        """
        Request a fresh frame capture - async command.
        
        Instant detection can wait for this if buffer is stale.
        
        Returns:
            command_id for tracking
        """
        cmd_id = str(uuid.uuid4())
        self.command_queue.put({
            'action': CameraCommand.GET_FRAME,
            'cmd_id': cmd_id,
            'timestamp': time.time()
        })
        return cmd_id
    
    def _worker_loop(self):
        """
        Main worker loop - processes commands from queue.
        
        Runs in dedicated thread, so ALL blocking operations are safe.
        """
        logger.info(f"🔄 Worker loop started for {self.device_id}")
        
        while not self.stop_event.is_set():
            try:
                # Get command with timeout (non-blocking wait)
                try:
                    cmd = self.command_queue.get(timeout=0.01)  # Shorter timeout for more responsive frame reading
                    
                    # Process command
                    action = cmd.get('action')
                    cmd_id = cmd.get('cmd_id')
                    
                    if action == CameraCommand.CONNECT:
                        self._handle_connect(cmd)
                    elif action == CameraCommand.DISCONNECT:
                        self._handle_disconnect(cmd)
                    elif action == CameraCommand.GET_FRAME:
                        self._handle_get_frame(cmd)
                    elif action == CameraCommand.UPDATE_SETTINGS:
                        self._handle_update_settings(cmd)
                    elif action == CameraCommand.STOP:
                        logger.info(f"🛑 Stop command received for {self.device_id}")
                        break
                    elif action == 'start_detection':
                        self.start_detection(cmd.get('config'))
                        self._set_result(cmd['cmd_id'], {'success': True})
                    elif action == 'stop_detection':
                        self.stop_detection()
                        self._set_result(cmd['cmd_id'], {'success': True})
                    elif action == 'start_recording':
                        self._handle_start_recording(cmd)
                    elif action == 'stop_recording':
                        self._handle_stop_recording(cmd)
                    else:
                        logger.warning(f"⚠️ Unknown command: {action}")
                        self._set_result(cmd_id, {'success': False, 'error': f'Unknown command: {action}'})
                    
                except queue.Empty:
                    pass  # No commands, that's fine
                
                # ✅ CRITICAL FIX: Always read frames when connected, regardless of command processing
                # This ensures continuous frame reading even during recording/detection operations
                # Mobile cameras don't have self.cap, but still need frame reading!
                if self.status == CameraStatus.CONNECTED and (self.cap or self.camera_type == CameraType.MOBILE):
                    self._read_and_buffer_frame()
                
            except Exception as e:
                logger.error(f"❌ Worker error for {self.device_id}: {e}", exc_info=True)
                self.error_count += 1
                self.last_error = str(e)
                
                # If too many errors, disconnect
                if self.error_count > 10:
                    logger.error(f"❌ Too many errors for {self.device_id}, disconnecting")
                    self.status = CameraStatus.ERROR
                    if self.cap:
                        try:
                            self.cap.release()
                        except:
                            pass
                        self.cap = None
        
        # Cleanup on exit
        logger.info(f"🧹 Cleaning up worker for {self.device_id}")
        if self.cap:
            try:
                self.cap.release()
                logger.info(f"✅ VideoCapture released for {self.device_id}")
            except Exception as e:
                logger.error(f"❌ Error releasing VideoCapture: {e}")
            self.cap = None
        
        self.status = CameraStatus.DISCONNECTED
        logger.info(f"✅ Worker loop finished for {self.device_id}")
    
    def _handle_connect(self, cmd: Dict[str, Any]):
        """Handle connect command."""
        cmd_id = cmd['cmd_id']
        connection_string = cmd.get('connection_string') or self.camera_info.get('connection_string')
        
        logger.info(f"🔌 [WORKER-{self.device_id}] STARTING connect to {connection_string}")
        logger.info(f"🔌 [WORKER-{self.device_id}] Thread: {threading.current_thread().name}, Thread ID: {threading.current_thread().ident}")
        self.status = CameraStatus.CONNECTING
        
        try:
            # Stop detection before reconnecting
            if self.detection_sampler:
                self.stop_detection()
            
            # Release existing connection if any
            if self.cap:
                self.cap.release()
                self.cap = None
            
            logger.info(f"📷 [WORKER-{self.device_id}] About to call cv2.VideoCapture...")
            create_start = time.time()
            
            # Handle mobile cameras differently - no VideoCapture needed
            if self.camera_type == CameraType.MOBILE:
                logger.info(f"📱 [WORKER-{self.device_id}] Mobile camera - using MobileStreamingService")
                
                # Verify mobile streaming service is receiving frames
                if not self.mobile_streaming_service.is_receiving_frames(self.device_id):
                    raise Exception(f"Mobile camera {self.device_id} not sending frames")
                
                # Get initial frame from mobile service
                frame_data = self.mobile_streaming_service.get_latest_mobile_frame_data(self.device_id)
                if not frame_data:
                    raise Exception("No frames available from mobile camera")
                
                frame = frame_data["frame"]
                rotation_angle = frame_data.get("rotation_angle", 0)
                
                # Apply rotation if needed
                if rotation_angle != 0:
                    frame = self._rotate_frame(frame, rotation_angle)
                    logger.info(f"📱 Rotated initial frame by {rotation_angle}° for {self.device_id}")
                
                width, height = frame.shape[1], frame.shape[0]
                fps = self.camera_info.get("max_fps", 30)
                
                # Add first frame to buffer
                self.frame_buffer.append(frame)
                self.last_frame_time = time.time()
                self.frames_read = 1
                
                self.status = CameraStatus.CONNECTED
                self.error_count = 0
                
                result = {
                    'success': True,
                    'device_id': self.device_id,
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'connection_string': 'mobile_streaming'
                }
                
                logger.info(f"✅ Mobile camera connected: {self.device_id} ({width}x{height} @ {fps}fps)")
                self._set_result(cmd_id, result)
                return
            
            # Create VideoCapture with timeout (BLOCKING - but in worker thread)
            if self.camera_type == CameraType.USB:
                # Extract USB device index
                device_index = int(connection_string.split('/')[-1].replace('video', ''))
                logger.info(f"📷 [WORKER-{self.device_id}] Opening USB camera at index {device_index}")
                self.cap = cv2.VideoCapture(device_index)
            else:
                # RTSP or other - set connection timeout and LOW-LATENCY mode
                logger.info(f"📷 [WORKER-{self.device_id}] Opening RTSP camera at {connection_string}")
                self.cap = cv2.VideoCapture()
                
                # ⚡ CRITICAL: Set buffer size to 1 BEFORE opening to eliminate lag
                # OpenCV defaults to buffering 5+ frames which causes delay
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Set timeout properties BEFORE opening
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 second timeout
                
                # Open with connection string
                self.cap.open(connection_string)
                
                # ⚡ VERIFY: Double-check buffer size after opening (some backends reset it)
                actual_buffer = self.cap.get(cv2.CAP_PROP_BUFFERSIZE)
                logger.info(f"📷 [WORKER-{self.device_id}] Buffer size set to: {actual_buffer} (requested 1)")
            
            create_elapsed = time.time() - create_start
            logger.info(f"📷 [WORKER-{self.device_id}] cv2.VideoCapture completed in {create_elapsed:.2f}s")
            
            # Verify opened
            if not self.cap.isOpened():
                raise Exception(f"Failed to open camera: {connection_string}")
            
            # Get camera properties
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            # Read first frame to verify
            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise Exception("Failed to read first frame")
            
            # Add first frame to buffer
            self.frame_buffer.append(frame)
            self.last_frame_time = time.time()
            self.frames_read = 1
            
            self.status = CameraStatus.CONNECTED
            self.error_count = 0
            
            result = {
                'success': True,
                'device_id': self.device_id,
                'width': width,
                'height': height,
                'fps': fps,
                'connection_string': connection_string
            }
            
            logger.info(f"✅ Camera connected: {self.device_id} ({width}x{height} @ {fps}fps)")
            self._set_result(cmd_id, result)
            
        except Exception as e:
            logger.error(f"❌ Connection failed for {self.device_id}: {e}")
            self.status = CameraStatus.ERROR
            self.last_error = str(e)
            
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            
            self._set_result(cmd_id, {
                'success': False,
                'error': str(e),
                'device_id': self.device_id
            })
    
    def _handle_disconnect(self, cmd: Dict[str, Any]):
        """Handle disconnect command."""
        cmd_id = cmd['cmd_id']
        
        logger.info(f"🔌 Disconnecting {self.device_id}")
        
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
            
            self.frame_buffer.clear()
            self.status = CameraStatus.DISCONNECTED
            
            logger.info(f"✅ Camera disconnected: {self.device_id}")
            self._set_result(cmd_id, {'success': True, 'device_id': self.device_id})
            
        except Exception as e:
            logger.error(f"❌ Disconnect failed for {self.device_id}: {e}")
            self._set_result(cmd_id, {'success': False, 'error': str(e)})
    
    def _handle_get_frame(self, cmd: Dict[str, Any]):
        """Handle get frame command (forces fresh frame read)."""
        cmd_id = cmd['cmd_id']
        
        try:
            if self.status != CameraStatus.CONNECTED:
                self._set_result(cmd_id, {'success': False, 'error': 'Camera not connected'})
                return
            
            # Handle mobile cameras
            if self.camera_type == CameraType.MOBILE:
                frame_data = self.mobile_streaming_service.get_latest_mobile_frame_data(self.device_id)
                if frame_data and frame_data.get("frame") is not None:
                    frame = frame_data["frame"]
                    self.frame_buffer.append(frame)
                    self.frames_read += 1
                    self.last_frame_time = time.time()
                    self._set_result(cmd_id, {'success': True, 'frame_available': True})
                else:
                    self.frames_dropped += 1
                    self._set_result(cmd_id, {'success': False, 'error': 'No frame from mobile camera'})
                return
            
            # Handle USB/RTSP cameras
            if not self.cap:
                self._set_result(cmd_id, {'success': False, 'error': 'Camera not connected'})
                return
            
            # Force read a fresh frame
            ret, frame = self.cap.read()
            
            if ret and frame is not None:
                self.frame_buffer.append(frame)
                self.frames_read += 1
                self.last_frame_time = time.time()
                self._set_result(cmd_id, {'success': True, 'frame_available': True})
            else:
                self.frames_dropped += 1
                self._set_result(cmd_id, {'success': False, 'error': 'Failed to read frame'})
                
        except Exception as e:
            logger.error(f"❌ Get frame failed for {self.device_id}: {e}")
            self._set_result(cmd_id, {'success': False, 'error': str(e)})
    
    def _handle_update_settings(self, cmd: Dict[str, Any]):
        """Handle update settings command."""
        cmd_id = cmd['cmd_id']
        settings = cmd.get('settings', {})
        
        try:
            if not self.cap or self.status != CameraStatus.CONNECTED:
                self._set_result(cmd_id, {'success': False, 'error': 'Camera not connected'})
                return
            
            # Apply settings
            for key, value in settings.items():
                if key == 'fps':
                    self.cap.set(cv2.CAP_PROP_FPS, value)
                elif key == 'width':
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, value)
                elif key == 'height':
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, value)
            
            logger.info(f"✅ Settings updated for {self.device_id}: {settings}")
            self._set_result(cmd_id, {'success': True})
            
        except Exception as e:
            logger.error(f"❌ Update settings failed for {self.device_id}: {e}")
            self._set_result(cmd_id, {'success': False, 'error': str(e)})
    
    def _read_and_buffer_frame(self):
        """
        Read frame and add to buffer.
        
        Called continuously when camera is connected.
        This keeps buffer fresh for instant detection and streaming.
        
        For RTSP cameras, uses frame grabbing to minimize latency.
        For MOBILE cameras, fetches from MobileStreamingService and applies rotation.
        ⚠️ CRITICAL: For recording, we need to read ALL frames, not skip them!
        """
        try:
            # Handle mobile cameras - fetch from mobile streaming service with rotation
            if self.camera_type == CameraType.MOBILE:
                frame_data = self.mobile_streaming_service.get_latest_mobile_frame_data(self.device_id)
                if frame_data and frame_data.get("frame") is not None:
                    frame = frame_data["frame"]
                    rotation_angle = frame_data.get("rotation_angle", 0)
                    
                    # Apply rotation based on device orientation
                    if rotation_angle != 0:
                        frame = self._rotate_frame(frame, rotation_angle)
                        logger.debug(f"📱 Rotated frame by {rotation_angle}° for {self.device_id}")
                    
                    ret = True
                else:
                    ret, frame = False, None
            elif not self.cap:
                return
            # For RTSP cameras, flush buffer only when NOT recording
            # When recording, we need every frame for proper playback speed
            elif self.camera_type == CameraType.RTSP:
                if self.is_recording:
                    # When recording: Read every frame for accurate video timing
                    ret, frame = self.cap.read()
                else:
                    # When NOT recording (streaming/detection only): Flush buffer for low latency
                    # Grab (decode but don't retrieve) up to 2 frames to flush buffer
                    for _ in range(2):
                        if not self.cap.grab():
                            break
                    
                    # Retrieve the latest frame
                    ret, frame = self.cap.retrieve()
            else:
                # USB cameras: Normal read (no lag issues)
                ret, frame = self.cap.read()
            
            if ret and frame is not None:
                self.frame_buffer.append(frame)
                self.frames_read += 1
                self.last_frame_time = time.time()
                
                # 🎥 INTEGRATED RECORDING: Write frame if recording (all in worker thread)
                if self.is_recording and self.video_writer:
                    try:
                        # Check if segment rotation is needed
                        if self.segment_duration and self.current_segment_start_time:
                            elapsed = time.time() - self.current_segment_start_time
                            if elapsed >= self.segment_duration:
                                logger.info(f"🎬 Rotating segment after {elapsed:.1f}s")
                                self._rotate_to_next_segment()
                        
                        # Write frame to current segment
                        self.video_writer.write(frame)
                        self.recording_frames_written += 1
                    except Exception as e:
                        logger.error(f"Recording write error: {e}")
                
                # 🔍 INSTANT DETECTION: Process frame if enabled
                # Sampler collects frames and submits to Celery (non-blocking)
                if self.enable_instant_detection and self.detection_sampler:
                    try:
                        self.detection_sampler.process_frame(frame, self.frames_read)
                    except Exception as e:
                        logger.debug(f"Detection processing error: {e}")
            else:
                self.frames_dropped += 1
                
                # Check if we should try to reconnect (for RTSP)
                if self.camera_type == CameraType.RTSP:
                    time_since_last_frame = time.time() - self.last_frame_time
                    if time_since_last_frame > 10.0:  # 10 seconds without frame
                        logger.warning(f"⚠️ No frames for 10s from {self.device_id}, may need reconnect")
                        self.error_count += 1
                
        except Exception as e:
            logger.error(f"❌ Frame read error for {self.device_id}: {e}")
            self.frames_dropped += 1
            self.error_count += 1
    
    def _set_result(self, cmd_id: str, result: Dict[str, Any]):
        """Store command result (thread-safe)."""
        with self.results_lock:
            self.command_results[cmd_id] = result
    
    def _rotate_frame(self, frame: np.ndarray, rotation_angle: int) -> np.ndarray:
        """
        Apply rotation to frame based on mobile device orientation.
        
        Args:
            frame: Input frame from mobile camera
            rotation_angle: Rotation angle (90, 180, 270)
        
        Returns:
            Rotated frame
        """
        import cv2
        if rotation_angle == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation_angle == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation_angle == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return frame
    
    def start_detection(self, detection_config: Optional[Dict[str, Any]] = None):
        """
        Start instant detection for this worker.
        
        Args:
            detection_config: Optional detection configuration
        """
        if self.detection_sampler:
            logger.warning(f"Detection already running for {self.device_id}")
            return
        
        try:
            from src.services.instant_detection_sampler import InstantDetectionSampler
            
            self.detection_config = detection_config or {}
            self.detection_sampler = InstantDetectionSampler(
                device_id=self.device_id,
                config=self.detection_config
            )
            self.enable_instant_detection = True
            logger.info(f"✅ Instant detection started for worker {self.device_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start detection for {self.device_id}: {e}")
            self.detection_sampler = None
            self.enable_instant_detection = False
    
    def stop_detection(self):
        """Stop instant detection for this worker."""
        if self.detection_sampler:
            try:
                self.detection_sampler.stop()
                logger.info(f"✅ Instant detection stopped for worker {self.device_id}")
            except Exception as e:
                logger.warning(f"Error stopping detection: {e}")
            finally:
                self.detection_sampler = None
                self.enable_instant_detection = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        stats = {
            'device_id': self.device_id,
            'status': self.status.value,
            'frames_read': self.frames_read,
            'frames_dropped': self.frames_dropped,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'last_frame_time': self.last_frame_time,
            'buffer_size': len(self.frame_buffer),
            'queue_size': self.command_queue.qsize(),
            'detection_enabled': self.enable_instant_detection,
            'is_recording': self.is_recording,
            'recording_frames': self.recording_frames_written,
            'pending_segments_for_upload': len(self.completed_segments),
            'segments_since_last_upload': self.segments_since_last_upload
        }
        
        # Add detection stats if available
        if self.detection_sampler:
            try:
                detection_stats = self.detection_sampler.get_stats()
                stats['detection_stats'] = detection_stats
            except:
                pass
        
        return stats
    
    def get_segments_for_upload(self) -> List[str]:
        """
        Get and clear segments that are ready for upload.
        Called when batch upload threshold is reached.
        Thread-safe.
        """
        segments = self.completed_segments.copy()
        self.completed_segments = []
        self.segments_since_last_upload = 0
        
        if segments:
            logger.info(f"📤 Returning {len(segments)} segments for batch upload")
        
        return segments
    
    def _publish_batch_ready_event(self, session_uuid: str, segments: List[str]):
        """
        Publish segment batch ready event to Redis (runs in separate thread).
        
        Args:
            session_uuid: Recording session UUID
            segments: List of segment paths ready for upload
        """
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                from src.services.status_notification_service import get_status_service
                
                status_service = get_status_service()
                
                # Publish segment batch ready event
                loop.run_until_complete(
                    status_service.publish_segment_batch_ready(
                        device_id=self.device_id,
                        session_uuid=session_uuid,
                        segment_count=len(segments),
                        segments=segments
                    )
                )
                
                logger.info(
                    f"📤 Published batch ready event to Redis: {self.device_id} "
                    f"({len(segments)} segments)"
                )
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to publish batch ready event: {e}")
    
    def _rotate_to_next_segment(self):
        """
        Rotate to next segment file - runs in worker thread.
        This handles segment rotation WITHOUT blocking frame reading.
        """
        try:
            if not self.is_recording or not self.video_writer:
                return
            
            # Close current segment
            logger.info(f"📦 Closing segment {self.current_segment_index}: {self.current_segment_path}")
            self.video_writer.release()
            
            # Get file size of completed segment
            completed_segment_path = self.current_segment_path
            file_size = os.path.getsize(completed_segment_path) if os.path.exists(completed_segment_path) else 0
            
            # Create next segment
            self.current_segment_index += 1
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"segment_{self.current_segment_index:03d}_{timestamp}.mp4"
            next_segment_path = os.path.join(self.session_dir, filename)
            
            # Get recording parameters from session info
            session_info = self.recording_session_info or {}
            width = session_info.get('width', 1280)
            height = session_info.get('height', 720)
            fps = session_info.get('fps', 30)
            
            # Create new VideoWriter (blocking but in worker thread = OK)
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            self.video_writer = cv2.VideoWriter(next_segment_path, fourcc, fps, (width, height))
            
            if not self.video_writer.isOpened():
                logger.error(f"❌ Failed to create next segment writer: {next_segment_path}")
                self.is_recording = False
                self.video_writer = None
                return
            
            # Update segment tracking
            self.current_segment_path = next_segment_path
            self.current_segment_start_time = time.time()
            
            logger.info(
                f"✅ Rotated to segment {self.current_segment_index}: {filename} "
                f"(previous: {file_size} bytes)"
            )
            
            # ✅ Track completed segment
            self.completed_segments.append(completed_segment_path)
            self.segments_since_last_upload += 1
            logger.info(
                f"📋 Segment {len(self.completed_segments)} completed: {completed_segment_path} "
                f"({self.segments_since_last_upload}/{self.batch_upload_size} since last upload)"
            )
            
            # 🚀 Upload completed segment to media service immediately
            # This is the EXACT same mechanism used by USB/RTSP cameras
            session_uuid = self.recording_session_info.get('session_uuid') if self.recording_session_info else None
            user_id = self.recording_session_info.get('user_id') if self.recording_session_info else None
            
            if session_uuid and user_id:
                logger.info(f"📤 Uploading segment {len(self.completed_segments)} to media service...")
                
                # Upload in separate thread to avoid blocking worker
                threading.Thread(
                    target=self._upload_segment_to_media,
                    args=(completed_segment_path, session_uuid, user_id),
                    daemon=True
                ).start()
            else:
                logger.warning(f"⚠️ Cannot upload segment - missing session_uuid or user_id")
            
        except Exception as e:
            logger.error(f"❌ Segment rotation failed: {e}")
            self.is_recording = False
    
    def _upload_segment_to_media(self, segment_path: str, session_uuid: str, user_id: str):
        """
        Upload a segment to the media service - EXACT same method used by USB/RTSP cameras.
        This runs in a separate thread to avoid blocking the worker's frame reading loop.
        """
        try:
            import requests
            from pathlib import Path
            
            logger.info(f"📤 [UPLOAD] Starting upload: {segment_path}")
            
            # Verify file exists
            path_obj = Path(segment_path)
            if not path_obj.exists():
                logger.error(f"❌ [UPLOAD] File not found: {segment_path}")
                return
            
            file_size = path_obj.stat().st_size
            logger.info(f"📤 [UPLOAD] File size: {file_size} bytes")
            
            # Get auth token from session info
            auth_token = self.recording_session_info.get('auth_token') if self.recording_session_info else None
            
            # Fetch user GUID from node service (media service requires UUID, not integer ID)
            user_guid = None
            if user_id:
                try:
                    headers = {}
                    if auth_token:
                        headers['Authorization'] = f'Bearer {auth_token}'
                    
                    node_url = f"http://localhost:8001/api/v1/users/{user_id}"
                    logger.info(f"📤 [UPLOAD] Fetching user GUID from: {node_url}")
                    
                    response = requests.get(node_url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        user_data = response.json()
                        user_guid = user_data.get('guid')
                        logger.info(f"📤 [UPLOAD] ✅ Got user GUID: {user_guid}")
                    else:
                        logger.error(f"❌ [UPLOAD] Failed to fetch GUID: HTTP {response.status_code}")
                        return
                except Exception as e:
                    logger.error(f"❌ [UPLOAD] Exception fetching GUID: {e}")
                    return
            
            if not user_guid:
                logger.error(f"❌ [UPLOAD] No user GUID available, cannot upload")
                return
            
            # Prepare multipart form data
            with open(segment_path, 'rb') as f:
                files = {
                    'file': (f'segment_{self.device_id}_{path_obj.name}', f, 'video/mp4')
                }
                
                data = {
                    'media_type': 'video',
                    'user_id': user_guid,  # Use GUID instead of integer ID
                    'title': f'Camera Recording - {self.device_id}',
                    'description': f'Segment from camera {self.device_id}',
                    'tags': f'["camera","recording","{self.device_id}"]',
                    'is_public': 'false',
                    'device_name': self.device_id
                }
                
                headers = {}
                if auth_token:
                    headers['Authorization'] = f'Bearer {auth_token}'
                
                # Upload to media service
                MEDIA_SERVICE_URL = "http://localhost:8000"
                response = requests.post(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/upload",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    media_uuid = result.get('uuid')
                    logger.info(f"✅ [UPLOAD] Segment uploaded successfully: {media_uuid}")
                    
                    # Remove from completed_segments list (so it's not uploaded again on stop)
                    try:
                        if segment_path in self.completed_segments:
                            self.completed_segments.remove(segment_path)
                            logger.info(f"📋 [UPLOAD] Removed {segment_path} from completed_segments list")
                    except Exception as e:
                        logger.warning(f"⚠️ [UPLOAD] Could not remove from completed_segments: {e}")
                    
                    # Assign to camera collection (so vmeta can find it via database polling)
                    self._assign_to_collection_sync(media_uuid, user_guid, headers)
                    
                else:
                    logger.error(f"❌ [UPLOAD] Failed: HTTP {response.status_code} - {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"❌ [UPLOAD] Exception during upload: {e}")
    
    def _assign_to_collection_sync(self, media_uuid: str, user_guid: str, headers: Dict):
        """
        Assign media to camera collection using IN-MEMORY collection UUID.
        Uses collection_uuid from recording_session_info (set at recording start).
        """
        import requests
        
        try:
            # 🎯 IN-MEMORY: Use collection UUID from session info (no database lookup!)
            collection_uuid = self.recording_session_info.get('collection_uuid') if self.recording_session_info else None
            
            if not collection_uuid:
                logger.warning(f"⚠️ [COLLECTION] No collection_uuid in session_info for {self.device_id}")
                # Fallback to database lookup (should rarely happen)
                collection_uuid = self._find_or_create_collection_sync(user_guid, headers)
            else:
                logger.info(f"🎯 [IN-MEMORY] Using collection UUID from session: {collection_uuid}")
            
            if not collection_uuid:
                logger.error(f"❌ [COLLECTION] Could not find/create collection for {self.device_id}")
                return
            
            # Assign media to collection
            endpoint = f"http://localhost:8000/api/v1/media/collections/{collection_uuid}/add/{media_uuid}"
            response = requests.post(
                endpoint,
                headers=headers,
                params={"user_id": user_guid},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ [COLLECTION] Assigned media {media_uuid} to collection {collection_uuid}")
            else:
                logger.error(f"❌ [COLLECTION] Failed to assign: HTTP {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"❌ [COLLECTION] Exception: {e}")
    
    def _find_or_create_collection_sync(self, user_guid: str, headers: Dict) -> Optional[str]:
        """
        Find existing camera collection or create new one.
        Synchronous version for use in upload thread.
        """
        import requests
        
        try:
            # Check in-memory cache first
            if self.device_id in self.collection_cache:
                cached_uuid = self.collection_cache[self.device_id]
                logger.info(f"📦 [COLLECTION] Using cached: {cached_uuid}")
                return cached_uuid
            
            # Try to find existing collection by camera device ID
            lookup_url = f"http://localhost:8000/api/v1/media/collections/by-camera/{self.device_id}"
            logger.info(f"📦 [COLLECTION] Looking for existing: {self.device_id}")
            
            response = requests.get(lookup_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                collection_data = response.json()
                if collection_data:
                    collection_uuid = collection_data.get("uuid")
                    logger.info(f"📦 [COLLECTION] Found existing: {collection_uuid}")
                    self.collection_cache[self.device_id] = collection_uuid
                    return collection_uuid
            
            # Collection not found, create new one
            logger.info(f"📦 [COLLECTION] Creating new collection for {self.device_id}")
            
            create_data = {
                "name": f"Camera {self.device_id}",
                "description": f"Recordings from camera {self.device_id}",
                "is_public": False,
                "user_id": user_guid,
                "camera_device_id": self.device_id
            }
            
            response = requests.post(
                "http://localhost:8000/api/v1/media/collections",
                json=create_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                collection_data = response.json()
                collection_uuid = collection_data.get("uuid")
                logger.info(f"✅ [COLLECTION] Created new: {collection_uuid}")
                self.collection_cache[self.device_id] = collection_uuid
                return collection_uuid
            else:
                logger.error(f"❌ [COLLECTION] Failed to create: HTTP {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ [COLLECTION] Exception: {e}")
            return None
    
    def _handle_start_recording(self, cmd: Dict[str, Any]):
        """
        Handle start recording command - runs in worker thread.
        ALL recording operations happen here to avoid blocking async event loop.
        """
        cmd_id = cmd['cmd_id']
        
        try:
            if self.is_recording:
                self._set_result(cmd_id, {'success': False, 'error': 'Already recording'})
                return
            
            # Mobile cameras don't have self.cap, check type or connection status
            if self.status != CameraStatus.CONNECTED:
                self._set_result(cmd_id, {'success': False, 'error': 'Camera not connected'})
                return
            
            # For USB/RTSP cameras, verify VideoCapture exists
            if self.camera_type in [CameraType.USB, CameraType.RTSP] and not self.cap:
                self._set_result(cmd_id, {'success': False, 'error': 'Camera not connected'})
                return
            
            # Get recording parameters
            output_path = cmd.get('output_path')
            width = cmd.get('width', 1280)
            height = cmd.get('height', 720)
            fps = cmd.get('fps', 30)
            segment_duration = cmd.get('segment_duration')  # None = no segmentation
            session_info = cmd.get('session_info', {})
            
            if not output_path:
                self._set_result(cmd_id, {'success': False, 'error': 'No output path provided'})
                return
            
            # Create VideoWriter (blocking operation but in worker thread = OK)
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            self.video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not self.video_writer.isOpened():
                self._set_result(cmd_id, {'success': False, 'error': 'Failed to create video writer'})
                self.video_writer = None
                return
            
            # Initialize segment tracking if segmentation enabled
            if segment_duration:
                self.segment_duration = segment_duration
                self.current_segment_start_time = time.time()
                self.current_segment_path = output_path
                self.session_dir = os.path.dirname(output_path)
                self.current_segment_index = 1
                self.completed_segments = []  # Reset completed segments list
                self.segments_since_last_upload = 0  # Reset batch upload counter
                logger.info(f"🎬 Segment rotation enabled: {segment_duration}s per segment")
                logger.info(f"📦 Batch upload enabled: uploading every {self.batch_upload_size} segments")
            
            # Store recording parameters in session_info for segment rotation
            session_info['width'] = width
            session_info['height'] = height
            session_info['fps'] = fps
            
            # Start recording
            self.is_recording = True
            self.recording_start_time = time.time()
            self.recording_frames_written = 0
            self.recording_session_info = session_info
            
            logger.info(f"🎥 Recording started in worker thread: {output_path}")
            
            self._set_result(cmd_id, {
                'success': True,
                'output_path': output_path,
                'timestamp': self.recording_start_time
            })
            
        except Exception as e:
            logger.error(f"❌ Start recording failed for {self.device_id}: {e}")
            self.video_writer = None
            self.is_recording = False
            self._set_result(cmd_id, {'success': False, 'error': str(e)})
    
    def _handle_stop_recording(self, cmd: Dict[str, Any]):
        """
        Handle stop recording command - runs in worker thread.
        Releases VideoWriter safely without blocking async event loop.
        """
        cmd_id = cmd['cmd_id']
        
        try:
            if not self.is_recording:
                self._set_result(cmd_id, {'success': False, 'error': 'Not recording'})
                return
            
            # Stop recording
            self.is_recording = False
            
            # Release video writer (blocking operation but in worker thread = OK)
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            duration = time.time() - self.recording_start_time if self.recording_start_time else 0
            
            logger.info(
                f"🎥 Recording stopped in worker thread: "
                f"duration={duration:.1f}s, frames={self.recording_frames_written}"
            )
            
            # Collect any remaining segments not yet uploaded
            segments_to_upload = self.completed_segments.copy()
            if self.current_segment_path:
                segments_to_upload.append(self.current_segment_path)
            
            result = {
                'success': True,
                'frames_written': self.recording_frames_written,
                'duration': duration,
                'session_info': self.recording_session_info,
                'remaining_segments': segments_to_upload,  # Only segments not yet uploaded
                'total_segments': self.current_segment_index
            }
            
            # Reset recording state
            self.recording_start_time = None
            self.recording_frames_written = 0
            self.recording_session_info = None
            self.completed_segments = []  # Clear completed segments list
            self.current_segment_path = None
            self.segments_since_last_upload = 0
            
            self._set_result(cmd_id, result)
            
        except Exception as e:
            logger.error(f"❌ Stop recording failed for {self.device_id}: {e}")
            self._set_result(cmd_id, {'success': False, 'error': str(e)})

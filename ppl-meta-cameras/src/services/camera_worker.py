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
from typing import Optional, Dict, Any, Deque
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
                if self.status == CameraStatus.CONNECTED and self.cap:
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
            if not self.cap or self.status != CameraStatus.CONNECTED:
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
        
        For RTSP cameras, uses aggressive frame grabbing to minimize latency.
        """
        try:
            if not self.cap:
                return
            
            # ⚡ RTSP LAG FIX: For RTSP cameras, grab multiple times to flush buffer
            # This ensures we always get the LATEST frame, not a buffered old one
            if self.camera_type == CameraType.RTSP:
                # Grab (decode but don't retrieve) up to 3 frames to flush buffer
                for _ in range(3):
                    if not self.cap.grab():
                        break
                
                # Now retrieve the latest frame
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
                
                # 🔍 INSTANT DETECTION: DISABLED in worker thread to prevent blocking
                # TODO: Re-enable when Celery is available or detection is truly async
                # if self.enable_instant_detection and self.detection_sampler:
                #     try:
                #         self.detection_sampler.process_frame(frame, self.frames_read)
                #     except Exception as e:
                #         logger.debug(f"Detection processing error: {e}")
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
            'recording_frames': self.recording_frames_written
        }
        
        # Add detection stats if available
        if self.detection_sampler:
            try:
                detection_stats = self.detection_sampler.get_stats()
                stats['detection_stats'] = detection_stats
            except:
                pass
        
        return stats
    
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
            
            # ✅ Segment is ready - upload will be handled by camera_detection.py later
            logger.info(f"📋 Segment ready for upload: {completed_segment_path}")
            
        except Exception as e:
            logger.error(f"❌ Segment rotation failed: {e}")
            self.is_recording = False
    
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
            
            if not self.cap or self.status != CameraStatus.CONNECTED:
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
                logger.info(f"🎬 Segment rotation enabled: {segment_duration}s per segment")
            
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
            
            result = {
                'success': True,
                'frames_written': self.recording_frames_written,
                'duration': duration,
                'session_info': self.recording_session_info
            }
            
            # Reset recording state
            self.recording_start_time = None
            self.recording_frames_written = 0
            self.recording_session_info = None
            
            self._set_result(cmd_id, result)
            
        except Exception as e:
            logger.error(f"❌ Stop recording failed for {self.device_id}: {e}")
            self._set_result(cmd_id, {'success': False, 'error': str(e)})

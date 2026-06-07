"""
Mobile camera streaming service for PPL Meta Cameras.
Handles incoming video streams from mobile devices via RTMP/WebRTC protocols.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class MobileCameraStreamingService:
    """Service for handling mobile camera video streams."""

    def __init__(self):
        self.active_mobile_streams: Dict[str, Dict[str, Any]] = {}
        self.stream_queues: Dict[str, Queue] = {}
        self.rtmp_servers: Dict[str, subprocess.Popen] = {}
        
        # Mobile camera workers for pipeline integration
        self.mobile_workers: Dict[str, Any] = {}  # device_id -> MobileCameraWorker
        self.worker_auto_start = True  # Auto-start workers when frames arrive
        
        # Track stopped cameras to reject incoming frames
        self.stopped_cameras: Dict[str, float] = {}  # device_id -> stop_timestamp

    async def setup_mobile_camera_stream(
        self, device_id: str, stream_config: Dict[str, Any]
    ) -> bool:
        """Setup streaming infrastructure for a mobile camera."""

        try:
            logger.info(f"Setting up mobile camera stream for {device_id}")

            # Extract mobile camera connection details
            ip_address = stream_config.get("ip_address")
            port = stream_config.get("port", 8554)  # Default RTMP port
            protocol = stream_config.get("protocol", "rtmp")  # Default to RTMP

            if not ip_address:
                logger.error(f"No IP address provided for mobile camera {device_id}")
                return False

            # Create stream configuration
            stream_info = {
                "device_id": device_id,
                "ip_address": ip_address,
                "port": port,
                "protocol": protocol,
                "status": "initializing",
                "frame_queue": Queue(maxsize=30),  # Buffer 30 frames
                "last_frame_time": 0,
                "stream_url": f"{protocol}://{ip_address}:{port}/live/{device_id}",
                "frame_timestamps": [],  # Short calibration window only
                "actual_fps": 30,  # App-reported fallback FPS
                "fps_locked": False,  # Lock once after initial calibration
                "calibrated_fps": None,  # Final FPS used for worker/recording timing
                "fps_calibration_start": None,
            }

            self.active_mobile_streams[device_id] = stream_info
            self.stream_queues[device_id] = stream_info["frame_queue"]

            # Start RTMP server for this mobile camera if needed
            if protocol.lower() == "rtmp":
                await self._start_rtmp_server(device_id, stream_info)

            logger.info(f"Mobile camera stream setup completed for {device_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting up mobile camera stream for {device_id}: {e}")
            return False

    async def _start_rtmp_server(
        self, device_id: str, stream_info: Dict[str, Any]
    ) -> bool:
        """Start an RTMP server instance for receiving mobile camera streams."""

        try:
            port = stream_info["port"]

            # Use FFmpeg to create an RTMP server that converts to a local stream
            # This creates a bridge between mobile RTMP input and our OpenCV processing
            temp_dir = tempfile.mkdtemp()
            fifo_path = os.path.join(temp_dir, f"mobile_stream_{device_id}.mkv")

            # Create named pipe for stream data
            os.mkfifo(fifo_path)

            # FFmpeg command to receive RTMP and output to named pipe
            ffmpeg_cmd = [
                "ffmpeg",
                "-f",
                "flv",
                "-listen",
                "1",
                "-i",
                f"rtmp://0.0.0.0:{port}/live/{device_id}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "zerolatency",
                "-f",
                "matroska",
                "-y",
                fifo_path,
            ]

            # Start FFmpeg process
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )

            self.rtmp_servers[device_id] = process
            stream_info["ffmpeg_process"] = process
            stream_info["fifo_path"] = fifo_path
            stream_info["temp_dir"] = temp_dir

            # Start frame reading thread
            threading.Thread(
                target=self._read_mobile_stream_frames,
                args=(device_id, fifo_path),
                daemon=True,
            ).start()

            logger.info(
                f"RTMP server started for mobile camera {device_id} on port {port}"
            )
            return True

        except Exception as e:
            logger.error(f"Error starting RTMP server for {device_id}: {e}")
            return False

    def _read_mobile_stream_frames(self, device_id: str, fifo_path: str):
        """Read frames from mobile camera stream and queue them."""

        try:
            # Wait for RTMP stream to start
            time.sleep(2)

            # Open video capture from the named pipe
            cap = cv2.VideoCapture(fifo_path)

            if not cap.isOpened():
                logger.error(f"Failed to open mobile stream for {device_id}")
                return

            stream_info = self.active_mobile_streams[device_id]
            frame_queue = stream_info["frame_queue"]

            logger.info(f"Started reading frames from mobile camera {device_id}")

            while device_id in self.active_mobile_streams:
                ret, frame = cap.read()

                if not ret:
                    logger.warning(
                        f"Failed to read frame from mobile camera {device_id}"
                    )
                    time.sleep(0.1)
                    continue

                # Update stream status
                stream_info["status"] = "streaming"
                stream_info["last_frame_time"] = time.time()

                # Add frame to queue (non-blocking)
                try:
                    if frame_queue.full():
                        # Remove oldest frame if queue is full
                        frame_queue.get_nowait()
                    frame_queue.put_nowait(frame)
                except:
                    # Queue operations can fail if service is shutting down
                    break

                # Small delay to prevent overwhelming the queue
                time.sleep(0.033)  # ~30 FPS

        except Exception as e:
            logger.error(f"Error reading mobile stream frames for {device_id}: {e}")
        finally:
            if "cap" in locals():
                cap.release()
            logger.info(f"Stopped reading frames from mobile camera {device_id}")

    async def get_mobile_camera_frame(self, device_id: str) -> Optional[np.ndarray]:
        """Get the latest frame from a mobile camera stream."""

        if device_id not in self.active_mobile_streams:
            return None

        frame_queue = self.stream_queues.get(device_id)
        if not frame_queue:
            return None

        try:
            # Get the most recent frame (non-blocking)
            frame = frame_queue.get_nowait()

            # Clear any additional frames to get the latest
            while not frame_queue.empty():
                try:
                    frame = frame_queue.get_nowait()
                except Empty:
                    break

            return frame

        except Empty:
            return None

    async def stop_mobile_camera_stream(self, device_id: str) -> bool:
        """Stop streaming for a mobile camera."""

        try:
            if device_id not in self.active_mobile_streams:
                logger.warning(f"Mobile camera stream {device_id} not active")
                return False

            stream_info = self.active_mobile_streams[device_id]

            # Stop FFmpeg process if running
            if device_id in self.rtmp_servers:
                process = self.rtmp_servers[device_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                del self.rtmp_servers[device_id]

            # Clean up temporary files
            if "fifo_path" in stream_info and os.path.exists(stream_info["fifo_path"]):
                os.unlink(stream_info["fifo_path"])
            if "temp_dir" in stream_info and os.path.exists(stream_info["temp_dir"]):
                os.rmdir(stream_info["temp_dir"])

            # Remove from active streams
            del self.active_mobile_streams[device_id]
            if device_id in self.stream_queues:
                del self.stream_queues[device_id]
            
            # Mark camera as stopped to reject incoming frames
            self.stopped_cameras[device_id] = time.time()
            logger.info(f"🛑 Marked {device_id} as stopped - will reject incoming frames")

            logger.info(f"Stopped mobile camera stream for {device_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping mobile camera stream for {device_id}: {e}")
            return False

    async def get_mobile_stream_status(
        self, device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get status information for a mobile camera stream."""

        if device_id not in self.active_mobile_streams:
            return None

        stream_info = self.active_mobile_streams[device_id]

        # Check if stream is actively receiving frames
        last_frame_time = stream_info.get("last_frame_time", 0)
        current_time = time.time()
        is_active = (
            current_time - last_frame_time
        ) < 5.0  # Consider active if frame within 5 seconds

        return {
            "device_id": device_id,
            "status": "active" if is_active else "inactive",
            "protocol": stream_info.get("protocol"),
            "stream_url": stream_info.get("stream_url"),
            "last_frame_time": last_frame_time,
            "queue_size": (
                self.stream_queues[device_id].qsize()
                if device_id in self.stream_queues
                else 0
            ),
        }

    def get_mobile_stream_fps(self, device_id: str) -> int:
        """
        Get FPS for mobile camera timing with one-time startup calibration.

        Design goal: keep live pipeline stable by calibrating FPS only during the
        first few seconds, then lock the result and stop recalculation.
        
        Args:
            device_id: Mobile device identifier
            
        Returns:
            Locked calibrated FPS if available, otherwise app-reported fallback FPS
        """
        if device_id not in self.active_mobile_streams:
            logger.debug(f"No active stream for {device_id}, returning default FPS 30")
            return 30
        
        stream_info = self.active_mobile_streams[device_id]

        if stream_info.get("fps_locked") and stream_info.get("calibrated_fps"):
            return int(stream_info["calibrated_fps"])

        # During startup calibration, use app-reported FPS as temporary fallback.
        return int(stream_info.get("actual_fps", 30))

    async def receive_mobile_frame(
        self,
        device_id: str,
        frame: np.ndarray,
        timestamp: float,
        orientation: str = "portraitUp",
        rotation_angle: int = 0,
        fps: int = 30,
    ) -> bool:
        """Receive and store a frame from a mobile camera.
        
        Args:
            device_id: Mobile device identifier
            frame: The image frame
            timestamp: Frame timestamp
            orientation: Device orientation string
            rotation_angle: Rotation angle in degrees
            fps: FPS the mobile app REPORTS (may be incorrect on old Android devices!)
        """

        try:
            # Treat any incoming frame as an implicit resume signal.
            # This prevents frame starvation when stop/start control messages flap.
            if device_id in self.stopped_cameras:
                stop_time = self.stopped_cameras.pop(device_id)
                elapsed = time.time() - stop_time
                logger.info(
                    f"✅ Auto-resuming stopped camera {device_id} on incoming frame after {elapsed:.1f}s"
                )

            # Check if we have an active stream for this device, if not create it
            if device_id not in self.active_mobile_streams:
                logger.info(f"Auto-setting up mobile camera stream for {device_id}")

                # Auto-setup mobile camera stream with default configuration
                stream_config = {
                    "ip_address": "mobile",  # Placeholder for mobile cameras
                    "port": 0,  # Not used for direct frame upload
                    "protocol": "direct",  # Direct frame upload
                }

                success = await self.setup_mobile_camera_stream(
                    device_id, stream_config
                )
                if not success:
                    logger.error(
                        f"Failed to auto-setup mobile camera stream for {device_id}"
                    )
                    return False
            
            logger.debug(
                f"📱 [MOBILE_SERVICE_DEBUG] Storing frame with orientation: {orientation}, rotation: {rotation_angle}, fps: {fps}"
            )
            logger.debug(
                f"📱 [MOBILE_SERVICE_DEBUG] Frame shape: {frame.shape}, timestamp: {timestamp}"
            )

            stream_info = self.active_mobile_streams[device_id]
            frame_queue = self.stream_queues[device_id]

            # Use server-side timing for stream activity and FPS calibration.
            receive_time = time.time()
            stream_info["last_frame_time"] = receive_time
            
            # Store app-reported FPS as fallback while calibration is in progress.
            stream_info["actual_fps"] = fps

            # One-time FPS calibration window (first few seconds only) to avoid
            # continuous runtime recalculation that can destabilize parallel services.
            if not stream_info.get("fps_locked"):
                if stream_info.get("fps_calibration_start") is None:
                    stream_info["fps_calibration_start"] = receive_time

                frame_timestamps = stream_info.setdefault("frame_timestamps", [])
                frame_timestamps.append(receive_time)

                # Keep a bounded list for low overhead.
                if len(frame_timestamps) > 45:
                    frame_timestamps.pop(0)

                calibration_elapsed = receive_time - stream_info["fps_calibration_start"]
                min_frames_for_lock = 10
                calibration_window_seconds = 3.0

                if (
                    calibration_elapsed >= calibration_window_seconds
                    and len(frame_timestamps) >= min_frames_for_lock
                ):
                    time_span = frame_timestamps[-1] - frame_timestamps[0]
                    intervals = len(frame_timestamps) - 1

                    if time_span > 0 and intervals > 0:
                        calculated_fps = intervals / time_span
                        if 5 <= calculated_fps <= 60:
                            locked_fps = int(round(calculated_fps))
                            stream_info["calibrated_fps"] = locked_fps
                            stream_info["fps_locked"] = True

                            if abs(locked_fps - int(fps)) > 2:
                                logger.warning(
                                    f"📱 FPS CALIBRATED for {device_id}: app reported {fps}, locked actual {locked_fps}"
                                )
                            else:
                                logger.info(
                                    f"📱 FPS CALIBRATED for {device_id}: locked at {locked_fps}"
                                )
                        else:
                            # Invalid estimate: lock to fallback to avoid repeated work.
                            stream_info["calibrated_fps"] = int(fps)
                            stream_info["fps_locked"] = True
                            logger.warning(
                                f"📱 FPS calibration out of range for {device_id} ({calculated_fps:.2f}), locking to fallback {fps}"
                            )
                    else:
                        stream_info["calibrated_fps"] = int(fps)
                        stream_info["fps_locked"] = True

                # Once locked, drop calibration timestamps to keep runtime lightweight.
                if stream_info.get("fps_locked"):
                    stream_info["frame_timestamps"] = []

            # Create frame data with metadata
            frame_data = {
                "frame": frame,
                "timestamp": timestamp,
                "orientation": orientation,
                "rotation_angle": rotation_angle,
                "fps": fps,  # Include reported FPS in frame data (worker uses calculated FPS instead)
            }

            # Add frame data to queue (drop oldest if queue is full)
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()  # Remove oldest frame
                except:
                    pass

            frame_queue.put_nowait(frame_data)
            logger.debug(f"Received frame from mobile camera {device_id}")
            
            # 🎯 QUEUE ARCHITECTURE: Mobile workers are now managed by CameraService queue system
            # Auto-start is disabled - workers are started via queue when recording/streaming begins
            # This prevents conflict with the unified queue-based CameraWorker implementation
            
            return True

        except Exception as e:
            logger.error(f"Error receiving frame from mobile camera {device_id}: {e}")
            return False

    async def get_latest_mobile_frame(self, device_id: str) -> Optional[np.ndarray]:
        """Get the latest frame from a mobile camera (backward compatibility)."""
        frame_data = self.get_latest_mobile_frame_data(device_id)
        return frame_data["frame"] if frame_data else None

    def get_latest_mobile_frame_data(self, device_id: str) -> Optional[Dict]:
        """
        Get the latest frame data with metadata from a mobile camera (SYNC version for worker threads).
        
        This is a synchronous method safe to call from worker threads.
        """
        if device_id not in self.stream_queues:
            return None

        frame_queue = self.stream_queues[device_id]

        try:
            # Get the most recent frame data
            latest_frame_data = None
            while not frame_queue.empty():
                latest_frame_data = frame_queue.get_nowait()

            return latest_frame_data

        except Exception as e:
            logger.error(
                f"Error getting latest frame from mobile camera {device_id}: {e}"
            )
            return None
    
    async def get_latest_mobile_frame_data_async(self, device_id: str) -> Optional[Dict]:
        """Get the latest frame data with metadata from a mobile camera (ASYNC version)."""
        # Just call the sync version - queue operations are thread-safe
        return self.get_latest_mobile_frame_data(device_id)

    async def shutdown(self):
        """Shutdown all mobile camera streams."""

        logger.info("Shutting down mobile camera streaming service")

        # Stop all active streams
        for device_id in list(self.active_mobile_streams.keys()):
            await self.stop_mobile_camera_stream(device_id)

        logger.info("Mobile camera streaming service shutdown complete")

    def has_active_mobile_camera(self, device_id: str) -> bool:
        """Check if a mobile camera is actively streaming."""
        if device_id not in self.active_mobile_streams:
            return False
        
        # Check if we've received frames recently (within last 10 seconds)
        stream_info = self.active_mobile_streams[device_id]
        last_frame_time = stream_info.get("last_frame_time", 0)
        time_since_last_frame = time.time() - last_frame_time
        
        if time_since_last_frame > 10.0:
            logger.warning(f"📱 Mobile camera {device_id} inactive for {time_since_last_frame:.1f}s, marking as disconnected")
            return False
        
        return True
    
    def is_receiving_frames(self, device_id: str) -> bool:
        """Check if mobile camera is currently receiving frames (alias for has_active_mobile_camera)."""
        return self.has_active_mobile_camera(device_id)
    
    async def cleanup_stale_cameras(self):
        """Remove mobile cameras that haven't sent frames in a while."""
        stale_cameras = []
        current_time = time.time()
        
        for device_id, stream_info in self.active_mobile_streams.items():
            last_frame_time = stream_info.get("last_frame_time", 0)
            time_since_last_frame = current_time - last_frame_time
            
            # Consider stale if no frames for 30 seconds
            if time_since_last_frame > 30.0:
                logger.warning(f"🧹 Cleaning up stale mobile camera {device_id} (no frames for {time_since_last_frame:.1f}s)")
                stale_cameras.append(device_id)
        
        # Remove stale cameras
        for device_id in stale_cameras:
            await self.stop_mobile_camera_stream(device_id)

            try:
                from src.services.stream_operations_state import get_stream_operations_state_service

                state_service = get_stream_operations_state_service()
                await state_service.mark_stream_stopped(
                    camera_id=device_id,
                    reason="mobile_cleanup_stale_timeout",
                )
            except Exception as exc:
                logger.debug(
                    "Failed to synchronize stream operations state during stale cleanup for %s: %s",
                    device_id,
                    exc,
                )
            
            # Stop worker if exists
            if device_id in self.mobile_workers:
                await self.stop_mobile_worker(device_id)
            
            # Update camera status in database
            try:
                from src.database import SessionLocal
                from src.models.camera import Camera, CameraStatus
                
                db = SessionLocal()
                try:
                    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
                    if camera:
                        camera.status = CameraStatus.DISCONNECTED
                        db.commit()
                        logger.info(f"✅ Updated status to disconnected for {device_id}")
                except Exception as e:
                    logger.error(f"❌ Error updating camera status: {e}")
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"❌ Error accessing database: {e}")
    
    async def start_mobile_worker(self, device_id: str, camera_info: Optional[Dict[str, Any]] = None, enable_instant_detection: bool = False):
        """
        Start background worker for mobile camera frame processing.
        
        This enables instant detection, recording, and pipeline integration.
        
        Args:
            device_id: Mobile device identifier
            camera_info: Camera configuration (optional, will fetch from DB if not provided)
            enable_instant_detection: Enable instant detection for this camera
        """
        if device_id in self.mobile_workers:
            logger.info(f"✅ Mobile worker already running for {device_id}")
            return
        
        # Get camera info if not provided
        if camera_info is None:
            try:
                from src.database import SessionLocal
                from src.models.camera import Camera
                
                db = SessionLocal()
                try:
                    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
                    if camera:
                        camera_info = {
                            "device_id": device_id,
                            "name": camera.name,
                            "camera_type": "mobile",
                            "resolution": camera.resolution,
                        }
                    else:
                        logger.warning(f"⚠️ Camera {device_id} not found in database, using defaults")
                        camera_info = {
                            "device_id": device_id,
                            "name": device_id,
                            "camera_type": "mobile",
                        }
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"❌ Error fetching camera info: {e}")
                camera_info = {
                    "device_id": device_id,
                    "name": device_id,
                    "camera_type": "mobile",
                }
        
        # Import and start worker
        try:
            from src.services.mobile_camera_worker import start_mobile_worker
            
            worker = await start_mobile_worker(
                device_id=device_id,
                camera_info=camera_info,
                enable_instant_detection=enable_instant_detection
            )
            
            self.mobile_workers[device_id] = worker
            logger.info(f"✅ Started mobile worker for {device_id} (instant_detection={enable_instant_detection})")
            
        except Exception as e:
            logger.error(f"❌ Error starting mobile worker for {device_id}: {e}")
    
    async def stop_mobile_worker(self, device_id: str):
        """
        Stop background worker for mobile camera.
        
        Args:
            device_id: Mobile device identifier
        """
        if device_id not in self.mobile_workers:
            logger.warning(f"⚠️ No active mobile worker for {device_id}")
            return
        
        try:
            from src.services.mobile_camera_worker import stop_mobile_worker
            
            await stop_mobile_worker(device_id)
            del self.mobile_workers[device_id]
            logger.info(f"✅ Stopped mobile worker for {device_id}")
            
        except Exception as e:
            logger.error(f"❌ Error stopping mobile worker for {device_id}: {e}")
    
    def get_mobile_worker(self, device_id: str) -> Optional[Any]:
        """
        Get the mobile camera worker for a device.
        
        Args:
            device_id: Mobile device identifier
        
        Returns:
            MobileCameraWorker instance or None
        """
        return self.mobile_workers.get(device_id)
    
    def has_mobile_worker(self, device_id: str) -> bool:
        """
        Check if a mobile camera worker is active.
        
        Args:
            device_id: Mobile device identifier
        
        Returns:
            True if worker is active
        """
        return device_id in self.mobile_workers


# Global instance
mobile_streaming_service = MobileCameraStreamingService()

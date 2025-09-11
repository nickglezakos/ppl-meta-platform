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

    async def receive_mobile_frame(
        self,
        device_id: str,
        frame: np.ndarray,
        timestamp: float,
        orientation: str = "portraitUp",
        rotation_angle: int = 0,
    ) -> bool:
        """Receive and store a frame from a mobile camera."""

        try:
            logger.info(
                f"📱 [MOBILE_SERVICE_DEBUG] Storing frame with orientation: {orientation}, rotation: {rotation_angle}"
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

            stream_info = self.active_mobile_streams[device_id]
            frame_queue = self.stream_queues[device_id]

            # Update last frame time
            stream_info["last_frame_time"] = timestamp

            # Create frame data with metadata
            frame_data = {
                "frame": frame,
                "timestamp": timestamp,
                "orientation": orientation,
                "rotation_angle": rotation_angle,
            }

            # Add frame data to queue (drop oldest if queue is full)
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()  # Remove oldest frame
                except:
                    pass

            frame_queue.put_nowait(frame_data)
            logger.debug(f"Received frame from mobile camera {device_id}")
            return True

        except Exception as e:
            logger.error(f"Error receiving frame from mobile camera {device_id}: {e}")
            return False

    async def get_latest_mobile_frame(self, device_id: str) -> Optional[np.ndarray]:
        """Get the latest frame from a mobile camera (backward compatibility)."""
        frame_data = await self.get_latest_mobile_frame_data(device_id)
        return frame_data["frame"] if frame_data else None

    async def get_latest_mobile_frame_data(self, device_id: str) -> Optional[Dict]:
        """Get the latest frame data with metadata from a mobile camera."""

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

    async def shutdown(self):
        """Shutdown all mobile camera streams."""

        logger.info("Shutting down mobile camera streaming service")

        # Stop all active streams
        for device_id in list(self.active_mobile_streams.keys()):
            await self.stop_mobile_camera_stream(device_id)

        logger.info("Mobile camera streaming service shutdown complete")


# Global instance
mobile_streaming_service = MobileCameraStreamingService()

"""
Recording Service - Manages video recording from camera workers.

This service handles:
- Creating recording sessions
- Background recording tasks (read frames from worker buffers)
- Stopping recordings
- Managing active recordings state
"""

import asyncio
import cv2
import httpx
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from src.services.camera_worker import CameraWorker

logger = logging.getLogger(__name__)


class RecordingService:
    """
    Manages video recording from camera workers.
    
    Records frames continuously from camera worker buffers (non-blocking)
    and writes them to video files.
    
    Usage:
        service = RecordingService(output_dir="recordings")
        
        # Create session and start recording
        session_id = await service.create_session(device_id="usb_camera_0", user_id="user123")
        await service.record_from_worker(worker=worker, session_id=session_id)
        
        # Stop recording
        await service.stop_session(session_id)
    """
    
    def __init__(self, output_dir: str = "recordings"):
        """
        Initialize recording service.
        
        Args:
            output_dir: Directory where recordings will be saved
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Active recordings: session_id -> stop_flag
        self.active_recordings: Dict[str, bool] = {}
        
        # Session metadata: session_id -> session_info
        self.sessions: Dict[str, Dict] = {}
        
        logger.info(f"✅ RecordingService initialized (output_dir={self.output_dir})")
    
    async def create_session(self, device_id: str, user_id: str) -> str:
        """
        Create a new recording session.
        
        Args:
            device_id: Camera device identifier
            user_id: User who initiated the recording
            
        Returns:
            Session ID
        """
        session_id = f"rec_{device_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        session_info = {
            'id': session_id,
            'device_id': device_id,
            'user_id': user_id,
            'started_at': datetime.utcnow(),
            'status': 'recording',
            'frame_count': 0,
            'file_path': None
        }
        
        self.sessions[session_id] = session_info
        
        # TODO: Store in database for persistence
        # await db.recording_sessions.insert(session_info)
        
        logger.info(f"📝 Recording session created: {session_id}")
        return session_id
    
    async def record_from_worker(self, worker: CameraWorker, session_id: str):
        """
        Background task: continuously read frames from worker and write to video.
        
        This runs as a background task, reading from worker's frame buffer.
        NON-BLOCKING because worker.get_latest_frame() is instant.
        
        Args:
            worker: CameraWorker to read frames from
            session_id: Recording session identifier
        """
        session_info = self.sessions.get(session_id)
        if not session_info:
            logger.error(f"❌ Session not found: {session_id}")
            return
        
        device_id = session_info['device_id']
        output_path = self.output_dir / f"{session_id}.mp4"
        session_info['file_path'] = str(output_path)
        
        video_writer = None
        
        try:
            # Get resolution from worker camera_info
            width = int(worker.camera_info.get('resolution_width', 1920))
            height = int(worker.camera_info.get('resolution_height', 1080))
            fps = worker.camera_info.get('max_fps', 30)
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                str(output_path),
                fourcc,
                fps,
                (width, height)
            )
            
            if not video_writer.isOpened():
                raise RuntimeError(f"Failed to open video writer for {output_path}")
            
            # Mark recording as active
            self.active_recordings[session_id] = True
            frame_count = 0
            
            logger.info(f"🎥 [RECORDING] Started {session_id} ({width}x{height} @ {fps}fps)")
            
            # Publish recording started event
            await self._publish_recording_event(device_id, "recording_started", {
                "session_id": session_id,
                "resolution": f"{width}x{height}",
                "fps": fps,
                "output_path": str(output_path)
            })
            
            # Recording loop
            while self.active_recordings.get(session_id, False):
                # Get latest frame from worker buffer (INSTANT, non-blocking)
                frame = worker.get_latest_frame()
                
                if frame is not None:
                    # Ensure frame has correct dimensions
                    if frame.shape[1] != width or frame.shape[0] != height:
                        # Resize if dimensions don't match
                        frame = cv2.resize(frame, (width, height))
                    
                    video_writer.write(frame)
                    frame_count += 1
                    session_info['frame_count'] = frame_count
                    
                    # Log progress every 100 frames
                    if frame_count % 100 == 0:
                        duration = (datetime.now() - session_info['started_at']).total_seconds()
                        logger.debug(f"📹 [RECORDING] {session_id} - {frame_count} frames ({duration:.1f}s)")
                else:
                    # No frame available, wait briefly
                    await asyncio.sleep(0.01)
                
                # Target FPS delay
                await asyncio.sleep(1.0 / fps)
            
            # Recording stopped
            duration = (datetime.now() - session_info['started_at']).total_seconds()
            session_info['stopped_at'] = datetime.now()
            session_info['status'] = 'completed'
            session_info['duration'] = duration
            
            # Publish recording stopped event
            await self._publish_recording_event(device_id, "recording_stopped", {
                "session_id": session_id,
                "frame_count": frame_count,
                "duration": duration
            })
            
            logger.info(f"✅ [RECORDING] Stopped {session_id} - {frame_count} frames in {duration:.1f}s")
            logger.info(f"💾 [RECORDING] Saved to {output_path} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")
            
            # TODO: Update database
            # await db.recording_sessions.update(session_id, {
            #     'stopped_at': session_info['stopped_at'],
            #     'status': 'completed',
            #     'frame_count': frame_count,
            #     'duration': duration,
            #     'file_path': str(output_path)
            # })
            
        except Exception as e:
            logger.error(f"❌ [RECORDING] Error in {session_id}: {e}")
            session_info['status'] = 'error'
            session_info['error'] = str(e)
            self.active_recordings[session_id] = False
            
            # TODO: Update database with error
            
        finally:
            # Cleanup
            if video_writer:
                video_writer.release()
            
            # Remove from active recordings
            if session_id in self.active_recordings:
                del self.active_recordings[session_id]
    
    async def stop_session(self, session_id: str) -> Dict:
        """
        Stop an active recording session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session info dict with final stats
            
        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session_info = self.sessions[session_id]
        
        if session_id in self.active_recordings:
            # Signal recording loop to stop
            self.active_recordings[session_id] = False
            logger.info(f"🛑 [RECORDING] Stop requested for {session_id}")
            
            # Wait briefly for recording to finish
            for _ in range(50):  # Max 5 seconds
                if session_id not in self.active_recordings:
                    break
                await asyncio.sleep(0.1)
        
        # Add stopped_at timestamp
        session_info['stopped_at'] = datetime.utcnow()
        session_info['status'] = 'stopped'
        
        return session_info
    
    async def get_active_session(self, device_id: str) -> Optional[Dict]:
        """
        Get active recording session for a device.
        
        Args:
            device_id: Camera device identifier
            
        Returns:
            Session info dict if active recording exists, None otherwise
        """
        # Find active session for this device
        for session_id, session_info in self.sessions.items():
            if (session_info['device_id'] == device_id and 
                session_info['status'] == 'recording' and
                session_id in self.active_recordings):
                return session_info
        
        return None
    
    async def get_session_status(self, session_id: str) -> Optional[Dict]:
        """
        Get status of a recording session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session info dict or None if not found
        """
        return self.sessions.get(session_id)
    
    def get_active_sessions(self) -> List[Dict]:
        """
        Get all active recording sessions.
        
        Returns:
            List of active session info dicts
        """
        return [
            session_info
            for session_id, session_info in self.sessions.items()
            if session_info['status'] == 'recording' and session_id in self.active_recordings
        ]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up old session metadata.
        
        Args:
            max_age_hours: Maximum age of sessions to keep in memory
        """
        now = datetime.now()
        to_remove = []
        
        for session_id, session_info in self.sessions.items():
            if session_info['status'] != 'recording':
                age = (now - session_info['started_at']).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
    
    async def _publish_recording_event(self, device_id: str, event: str, details: Dict):
        """
        Publish recording event to status notification service AND vmeta service.
        
        Args:
            device_id: Camera device identifier
            event: Event type (recording_started, recording_stopped)
            details: Event details
        """
        logger.info(f"🔔 Attempting to publish {event} for {device_id}")
        
        # Publish to Redis (status notifications)
        try:
            from src.services.status_notification_service import get_status_service, CameraStatusEvent
            
            # Map string to enum
            event_map = {
                "recording_started": CameraStatusEvent.RECORDING_STARTED,
                "recording_stopped": CameraStatusEvent.RECORDING_STOPPED,
            }
            
            status_event = event_map.get(event)
            if status_event:
                status_service = get_status_service()
                await status_service.publish_status_change(device_id, status_event, details)
                logger.info(f"📡 Published {event} to Redis for {device_id}")
            else:
                logger.warning(f"Unknown event type: {event}")
        except Exception as e:
            logger.warning(f"Could not publish recording event to Redis {event}: {e}")
        
        # Forward to vmeta service (continuous pipeline trigger)
        try:
            import os
            vmeta_url = os.getenv("VMETA_URL", "http://localhost:8008")
            endpoint = f"{vmeta_url}/api/v1/recording-events"
            
            # Build vmeta event payload
            vmeta_payload = {
                "event_type": event,
                "device_id": device_id,
                "session_id": details.get("session_id"),
                "collection": device_id,  # Use device_id as collection identifier
                "timestamp": datetime.now().isoformat(),
                "details": details
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(endpoint, json=vmeta_payload)
                response.raise_for_status()
                logger.info(f"✅ [VMETA] Forwarded {event} to vmeta: {endpoint}")
        except httpx.HTTPError as e:
            logger.warning(f"⚠️ [VMETA] Failed to forward {event} to vmeta: {e}")
        except Exception as e:
            logger.warning(f"⚠️ [VMETA] Unexpected error forwarding {event} to vmeta: {e}")


# Global recording service instance
_recording_service: Optional[RecordingService] = None


def get_recording_service() -> RecordingService:
    """Get the global recording service instance."""
    global _recording_service
    if _recording_service is None:
        _recording_service = RecordingService()
    return _recording_service

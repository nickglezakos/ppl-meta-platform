"""
Recording Session Service for Camera Service
Created: 2025-10-15
Purpose: Business logic for managing recording sessions with UUID tracking
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from src.models.camera import Camera
from src.models.recording_session import (
    RecordingFile,
    RecordingMetadata,
    RecordingSession,
    RecordingStatus,
)

logger = logging.getLogger(__name__)


class RecordingSessionService:
    """Service for managing camera recording sessions with UUID tracking."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        camera_device_id: str,
        user_id: str,
        recording_config: Optional[Dict] = None,
    ) -> RecordingSession:
        """
        Create a new recording session for a camera.

        Args:
            camera_device_id: Camera device identifier
            user_id: User who initiated the recording
            recording_config: Optional configuration parameters

        Returns:
            Created RecordingSession object

        Raises:
            ValueError: If camera not found or already has active recording
        """
        # Get camera by device_id
        camera = (
            self.db.query(Camera).filter(Camera.device_id == camera_device_id).first()
        )
        if not camera:
            raise ValueError(f"Camera with device_id '{camera_device_id}' not found")

        # Check if camera already has active recording
        active_session = self._get_active_session_for_camera(camera.id)
        if active_session:
            raise ValueError(
                f"Camera '{camera_device_id}' already has active recording session: {active_session.session_uuid}"
            )

        # Create recording session
        session_uuid = str(uuid.uuid4())
        session = RecordingSession(
            session_uuid=session_uuid,
            camera_id=camera.id,
            user_id=user_id,
            status="active",
            recording_quality=(
                recording_config.get("quality", "high") if recording_config else "high"
            ),
        )

        self.db.add(session)
        self.db.flush()  # Get the ID

        # Create metadata record if config provided
        if recording_config:
            metadata = RecordingMetadata(
                session_uuid=session_uuid,
                segment_interval_seconds=recording_config.get(
                    "segment_interval_seconds"
                ),
                segment_duration_seconds=recording_config.get(
                    "segment_duration_seconds", 30
                ),
                auto_face_detection_enabled=recording_config.get(
                    "auto_face_detection_enabled", True
                ),
                video_codec=recording_config.get("video_codec", "h264"),
                audio_enabled=recording_config.get("audio_enabled", False),
                resolution_width=recording_config.get("resolution_width"),
                resolution_height=recording_config.get("resolution_height"),
                fps=recording_config.get("fps"),
                bitrate=recording_config.get("bitrate"),
                face_detection_method=recording_config.get(
                    "face_detection_method", "enhanced-v2"
                ),
                quality_preset=recording_config.get("quality_preset", "balanced"),
            )
            self.db.add(metadata)

        self.db.commit()
        logger.info(
            f"Created recording session {session_uuid} for camera {camera_device_id}"
        )
        return session

    def stop_session(self, session_uuid: str) -> RecordingSession:
        """
        Stop an active recording session.

        Args:
            session_uuid: UUID of the session to stop

        Returns:
            Updated RecordingSession object

        Raises:
            ValueError: If session not found or not active
        """
        session = (
            self.db.query(RecordingSession)
            .filter(RecordingSession.session_uuid == session_uuid)
            .first()
        )

        if not session:
            raise ValueError(f"Recording session '{session_uuid}' not found")

        if session.status != "active":
            raise ValueError(
                f"Recording session '{session_uuid}' is not active (status: {session.status})"
            )

        # Update session status
        # IMPORTANT: We do NOT stop instant detection or disconnect the camera here
        # - Instant detection should be independent of recording
        # - Camera connection must remain active for streaming
        # - Only the recording loop should be stopped
        session.status = "completed"
        session.stopped_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Stopped recording session {session_uuid}")
        return session

    def update_session_status(
        self, session_uuid: str, status: str, error_message: Optional[str] = None
    ) -> RecordingSession:
        """
        Update the status of a recording session.

        Args:
            session_uuid: UUID of the session to update
            status: New status (active, paused, completed, failed, error)
            error_message: Optional error message if status is failed/error

        Returns:
            Updated RecordingSession object

        Raises:
            ValueError: If session not found
        """
        session = (
            self.db.query(RecordingSession)
            .filter(RecordingSession.session_uuid == session_uuid)
            .first()
        )

        if not session:
            raise ValueError(f"Recording session '{session_uuid}' not found")

        session.status = status
        if error_message:
            session.error_message = error_message

        if status in ["completed", "failed", "error"] and not session.stopped_at:
            session.stopped_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Updated recording session {session_uuid} status to '{status}'")
        return session

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up stale recording sessions (active sessions older than max_age_hours).
        
        This should be called:
        - On service startup
        - When a camera connects
        - Periodically (optional)
        
        Args:
            max_age_hours: Maximum age in hours for an active session before it's considered stale
        
        Returns:
            Number of sessions cleaned up
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Find all active sessions older than cutoff time
        stale_sessions = (
            self.db.query(RecordingSession)
            .filter(
                RecordingSession.status == "active",
                RecordingSession.created_at < cutoff_time
            )
            .all()
        )
        
        cleaned_count = 0
        for session in stale_sessions:
            try:
                session.status = "failed"
                session.error_message = f"Session timed out (stale after {max_age_hours} hours)"
                if not session.stopped_at:
                    session.stopped_at = datetime.utcnow()
                cleaned_count += 1
                logger.info(
                    f"Cleaned up stale session {session.session_uuid} "
                    f"for camera {session.camera.device_id if session.camera else 'unknown'}"
                )
            except Exception as e:
                logger.error(f"Error cleaning up session {session.session_uuid}: {e}")
        
        if cleaned_count > 0:
            self.db.commit()
        
        return cleaned_count

    def get_session(self, session_uuid: str) -> Optional[RecordingSession]:
        """Get recording session by UUID."""
        return (
            self.db.query(RecordingSession)
            .filter(RecordingSession.session_uuid == session_uuid)
            .first()
        )

    def get_sessions_for_camera(
        self, camera_device_id: str, limit: int = 50
    ) -> List[RecordingSession]:
        """
        Get recording sessions for a specific camera.

        Args:
            camera_device_id: Camera device identifier
            limit: Maximum number of sessions to return

        Returns:
            List of RecordingSession objects ordered by creation date (newest first)
        """
        camera = (
            self.db.query(Camera).filter(Camera.device_id == camera_device_id).first()
        )
        if not camera:
            return []

        return (
            self.db.query(RecordingSession)
            .filter(RecordingSession.camera_id == camera.id)
            .order_by(RecordingSession.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_sessions_for_user(
        self, user_id: str, limit: int = 50
    ) -> List[RecordingSession]:
        """Get recording sessions for a specific user."""
        return (
            self.db.query(RecordingSession)
            .filter(RecordingSession.user_id == user_id)
            .order_by(RecordingSession.created_at.desc())
            .limit(limit)
            .all()
        )

    def add_file_to_session(
        self,
        session_uuid: str,
        file_path: str,
        file_size_bytes: int = 0,
        media_uuid: Optional[str] = None,
        **file_metadata,
    ) -> RecordingFile:
        """
        Add a recorded file to a session.

        Args:
            session_uuid: UUID of the recording session
            file_path: Full path to the recorded file
            file_size_bytes: Size of the file in bytes
            media_uuid: UUID from media service if uploaded
            **file_metadata: Additional file metadata

        Returns:
            Created RecordingFile object
        """
        session = self.get_session(session_uuid)
        if not session:
            raise ValueError(f"Recording session '{session_uuid}' not found")

        file_uuid = str(uuid.uuid4())
        file_name = os.path.basename(file_path)

        # Create relative path (remove base recordings directory)
        recordings_base = "/recordings/"  # Adjust based on your setup
        relative_path = (
            file_path.replace(recordings_base, "")
            if recordings_base in file_path
            else file_path
        )

        recording_file = RecordingFile(
            session_uuid=session_uuid,
            file_uuid=file_uuid,
            file_path=file_path,
            relative_path=relative_path,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            media_uuid=media_uuid,
            duration_seconds=file_metadata.get("duration_seconds", 0.0),
            video_codec=file_metadata.get("video_codec"),
            audio_codec=file_metadata.get("audio_codec"),
            mime_type=file_metadata.get("mime_type", "video/mp4"),
        )

        self.db.add(recording_file)
        self.db.commit()

        logger.info(f"Added file {file_name} to recording session {session_uuid}")
        return recording_file

    def update_file_media_upload_status(
        self,
        file_uuid: str,
        media_uuid: str,
        media_collection_id: str,
        upload_completed: bool = True,
    ) -> Optional[RecordingFile]:
        """Update file's media service upload status."""
        recording_file = (
            self.db.query(RecordingFile)
            .filter(RecordingFile.file_uuid == file_uuid)
            .first()
        )

        if not recording_file:
            return None

        recording_file.media_uuid = media_uuid
        recording_file.media_collection_id = media_collection_id
        recording_file.is_uploaded_to_media = upload_completed

        if upload_completed:
            recording_file.media_upload_completed_at = datetime.utcnow()
        else:
            recording_file.media_upload_attempted_at = datetime.utcnow()

        self.db.commit()
        return recording_file

    def get_session_files(self, session_uuid: str) -> List[RecordingFile]:
        """Get all files for a recording session in chronological order."""
        return (
            self.db.query(RecordingFile)
            .filter(RecordingFile.session_uuid == session_uuid)
            .order_by(RecordingFile.created_at.asc())
            .all()
        )

    def get_session_with_files(self, session_uuid: str) -> Optional[Dict]:
        """
        Get complete session information including all associated files.

        Returns:
            Dictionary with session info and ordered file list, or None if not found
        """
        session = self.get_session(session_uuid)
        if not session:
            return None

        files = self.get_session_files(session_uuid)

        return {
            "session": session.to_dict(),
            "metadata": (
                session.recording_metadata.to_dict()
                if session.recording_metadata
                else None
            ),
            "files": [f.to_dict() for f in files],
            "video_count": len(files),
            "total_duration": sum(
                f.duration_seconds for f in files if f.duration_seconds
            ),
            "total_size_bytes": sum(f.file_size_bytes for f in files),
            "media_uuids": [f.media_uuid for f in files if f.media_uuid],
        }

    def update_session_progress(
        self,
        session_uuid: str,
        duration_seconds: float,
        file_size_bytes: int = 0,
        frames_recorded: int = 0,
    ) -> Optional[RecordingSession]:
        """Update session progress metrics."""
        session = self.get_session(session_uuid)
        if not session:
            return None

        session.current_duration_seconds = duration_seconds
        session.estimated_file_size_bytes = file_size_bytes
        session.frames_recorded = frames_recorded
        session.last_heartbeat = datetime.utcnow()

        self.db.commit()
        return session

    def get_active_sessions(self) -> List[RecordingSession]:
        """Get all currently active recording sessions."""
        return (
            self.db.query(RecordingSession)
            .filter(RecordingSession.status == "active")
            .order_by(RecordingSession.started_at.desc())
            .all()
        )

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """
        Mark stale sessions as failed.

        Args:
            max_age_hours: Maximum age for active sessions before considering them stale

        Returns:
            Number of sessions marked as failed
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        stale_sessions = (
            self.db.query(RecordingSession)
            .filter(
                and_(
                    RecordingSession.status == "active",
                    RecordingSession.last_heartbeat < cutoff_time,
                )
            )
            .all()
        )

        count = 0
        for session in stale_sessions:
            session.status = "failed"
            session.error_message = (
                f"Session became stale (no heartbeat for {max_age_hours} hours)"
            )
            session.stopped_at = datetime.utcnow()
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"Marked {count} stale recording sessions as failed")

        return count

    def _get_active_session_for_camera(
        self, camera_id: int
    ) -> Optional[RecordingSession]:
        """Get active recording session for a camera."""
        return (
            self.db.query(RecordingSession)
            .filter(
                and_(
                    RecordingSession.camera_id == camera_id,
                    RecordingSession.status == "active",
                )
            )
            .first()
        )

    def get_session_statistics(self) -> Dict:
        """Get recording session statistics."""
        total_sessions = self.db.query(RecordingSession).count()
        active_sessions = (
            self.db.query(RecordingSession)
            .filter(RecordingSession.status == "active")
            .count()
        )
        completed_sessions = (
            self.db.query(RecordingSession)
            .filter(RecordingSession.status == "completed")
            .count()
        )
        failed_sessions = (
            self.db.query(RecordingSession)
            .filter(RecordingSession.status == "failed")
            .count()
        )

        total_files = self.db.query(RecordingFile).count()
        uploaded_files = (
            self.db.query(RecordingFile)
            .filter(RecordingFile.is_uploaded_to_media == True)
            .count()
        )

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "total_files": total_files,
            "uploaded_files": uploaded_files,
            "upload_success_rate": (
                (uploaded_files / total_files * 100) if total_files > 0 else 0
            ),
        }

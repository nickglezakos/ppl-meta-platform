# ppl-meta-orchestrator/src/services/recording_session_service.py
"""
Recording Session Service - Phase 4 Implementation
Comprehensive service for managing recording sessions with workflow integration
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import get_db
from models.recording_session import (
    RecordingSession,
    RecordingSessionStatus,
    SessionStatus,
)
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RecordingSessionService:
    """Service for managing recording sessions with comprehensive tracking and workflow integration"""

    def __init__(self, db: Session = None):
        self.db = db or next(get_db())

    # Session Creation and Management

    def create_session(
        self,
        camera_device_id: str,
        user_id: str,
        recording_profile_id: Optional[int] = None,
        recording_config: Optional[Dict[str, Any]] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
    ) -> RecordingSession:
        """Create a new recording session"""
        try:
            session_uuid = str(uuid.uuid4())

            session = RecordingSession(
                session_uuid=session_uuid,
                camera_device_id=camera_device_id,
                user_id=user_id,
                recording_profile_id=recording_profile_id,
                status=SessionStatus.ACTIVE,
                recording_config=recording_config or {},
                workflow_metadata=workflow_metadata or {},
                started_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
            )

            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

            # Create initial status record
            self._record_status_update(
                session_uuid=session_uuid,
                duration_seconds=0.0,
                context_data={"event": "session_created"},
            )

            logger.info(
                f"Created recording session {session_uuid} for camera {camera_device_id}"
            )
            return session

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create recording session: {e}")
            raise

    def get_session(self, session_uuid: str) -> Optional[RecordingSession]:
        """Get recording session by UUID"""
        return (
            self.db.query(RecordingSession)
            .filter(RecordingSession.session_uuid == session_uuid)
            .first()
        )

    def get_active_sessions(
        self, camera_device_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[RecordingSession]:
        """Get all active recording sessions with optional filtering"""
        query = self.db.query(RecordingSession).filter(
            RecordingSession.status == SessionStatus.ACTIVE
        )

        if camera_device_id:
            query = query.filter(RecordingSession.camera_device_id == camera_device_id)

        if user_id:
            query = query.filter(RecordingSession.user_id == user_id)

        return query.order_by(desc(RecordingSession.started_at)).all()

    def get_sessions_by_camera(
        self,
        camera_device_id: str,
        limit: int = 50,
        status: Optional[SessionStatus] = None,
    ) -> List[RecordingSession]:
        """Get recording sessions for a specific camera"""
        query = self.db.query(RecordingSession).filter(
            RecordingSession.camera_device_id == camera_device_id
        )

        if status:
            query = query.filter(RecordingSession.status == status)

        return query.order_by(desc(RecordingSession.started_at)).limit(limit).all()

    def get_sessions_by_user(
        self, user_id: str, limit: int = 50, status: Optional[SessionStatus] = None
    ) -> List[RecordingSession]:
        """Get recording sessions for a specific user"""
        query = self.db.query(RecordingSession).filter(
            RecordingSession.user_id == user_id
        )

        if status:
            query = query.filter(RecordingSession.status == status)

        return query.order_by(desc(RecordingSession.started_at)).limit(limit).all()

    # Session Status Updates

    def update_session_status(
        self,
        session_uuid: str,
        status: SessionStatus,
        error_message: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update session status with optional error message"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                logger.warning(f"Session {session_uuid} not found for status update")
                return False

            old_status = session.status
            session.status = status
            session.last_heartbeat = datetime.utcnow()

            if status in [
                SessionStatus.COMPLETED,
                SessionStatus.FAILED,
                SessionStatus.STOPPED,
                SessionStatus.TIMEOUT,
            ]:
                session.stopped_at = datetime.utcnow()

            if error_message:
                session.error_message = error_message

            if status == SessionStatus.FAILED:
                session.retry_count += 1

            self.db.commit()

            # Record status change
            self._record_status_update(
                session_uuid=session_uuid,
                duration_seconds=session.current_duration_seconds,
                context_data={
                    "event": "status_changed",
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "error_message": error_message,
                    **(context_data or {}),
                },
            )

            logger.info(
                f"Updated session {session_uuid} status: {old_status.value} -> {status.value}"
            )
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update session status: {e}")
            return False

    def update_session_progress(
        self,
        session_uuid: str,
        duration_seconds: float,
        frames_recorded: int,
        estimated_file_size_bytes: Optional[int] = None,
        average_fps: Optional[float] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update session progress metrics"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                logger.warning(f"Session {session_uuid} not found for progress update")
                return False

            session.current_duration_seconds = duration_seconds
            session.frames_recorded = frames_recorded
            session.last_heartbeat = datetime.utcnow()

            if estimated_file_size_bytes is not None:
                session.estimated_file_size_bytes = estimated_file_size_bytes

            if average_fps is not None:
                session.average_fps = average_fps

            self.db.commit()

            # Record detailed status update
            self._record_status_update(
                session_uuid=session_uuid,
                duration_seconds=duration_seconds,
                file_size_bytes=estimated_file_size_bytes,
                frames_recorded=frames_recorded,
                current_fps=average_fps,
                context_data={
                    "event": "progress_update",
                    **(performance_metrics or {}),
                },
            )

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update session progress: {e}")
            return False

    def heartbeat_session(self, session_uuid: str) -> bool:
        """Update session heartbeat to indicate it's still active"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                return False

            session.last_heartbeat = datetime.utcnow()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update session heartbeat: {e}")
            return False

    # Workflow Integration

    def trigger_face_detection(
        self,
        session_uuid: str,
        face_detection_session_uuid: str,
        workflow_execution_id: Optional[str] = None,
    ) -> bool:
        """Mark session as having triggered face detection workflow"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                return False

            session.face_detection_triggered = True
            session.face_detection_session_uuid = face_detection_session_uuid

            if workflow_execution_id:
                session.workflow_execution_id = workflow_execution_id

            session.last_heartbeat = datetime.utcnow()
            self.db.commit()

            self._record_status_update(
                session_uuid=session_uuid,
                duration_seconds=session.current_duration_seconds,
                context_data={
                    "event": "face_detection_triggered",
                    "face_detection_session_uuid": face_detection_session_uuid,
                    "workflow_execution_id": workflow_execution_id,
                },
            )

            logger.info(f"Triggered face detection for session {session_uuid}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to trigger face detection: {e}")
            return False

    def complete_face_detection(
        self, session_uuid: str, face_detection_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark face detection as completed for the session"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                return False

            session.face_detection_completed = True
            session.last_heartbeat = datetime.utcnow()

            # Update workflow metadata with results
            if face_detection_results:
                if not session.workflow_metadata:
                    session.workflow_metadata = {}
                session.workflow_metadata["face_detection_results"] = (
                    face_detection_results
                )

            self.db.commit()

            self._record_status_update(
                session_uuid=session_uuid,
                duration_seconds=session.current_duration_seconds,
                context_data={
                    "event": "face_detection_completed",
                    "results": face_detection_results,
                },
            )

            logger.info(f"Completed face detection for session {session_uuid}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to complete face detection: {e}")
            return False

    def update_media_upload_status(
        self,
        session_uuid: str,
        started: Optional[bool] = None,
        completed: Optional[bool] = None,
        media_collection_id: Optional[str] = None,
        media_uuid: Optional[str] = None,
    ) -> bool:
        """Update media upload status for the session"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                return False

            if started is not None:
                session.media_upload_started = started

            if completed is not None:
                session.media_upload_completed = completed

            if media_collection_id:
                session.media_collection_id = media_collection_id

            if media_uuid:
                session.media_uuid = media_uuid

            session.last_heartbeat = datetime.utcnow()
            self.db.commit()

            self._record_status_update(
                session_uuid=session_uuid,
                duration_seconds=session.current_duration_seconds,
                context_data={
                    "event": "media_upload_status_updated",
                    "upload_started": started,
                    "upload_completed": completed,
                    "media_collection_id": media_collection_id,
                    "media_uuid": media_uuid,
                },
            )

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update media upload status: {e}")
            return False

    # Session Cleanup and Monitoring

    def find_stale_sessions(
        self, heartbeat_timeout_minutes: int = 5
    ) -> List[RecordingSession]:
        """Find sessions that haven't had a heartbeat within the timeout period"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=heartbeat_timeout_minutes)

        return (
            self.db.query(RecordingSession)
            .filter(
                and_(
                    RecordingSession.status == SessionStatus.ACTIVE,
                    RecordingSession.last_heartbeat < cutoff_time,
                )
            )
            .all()
        )

    def cleanup_stale_sessions(self, heartbeat_timeout_minutes: int = 5) -> int:
        """Mark stale sessions as timed out"""
        stale_sessions = self.find_stale_sessions(heartbeat_timeout_minutes)
        cleanup_count = 0

        for session in stale_sessions:
            if self.update_session_status(
                session.session_uuid,
                SessionStatus.TIMEOUT,
                error_message=f"Session timed out after {heartbeat_timeout_minutes} minutes of inactivity",
            ):
                cleanup_count += 1

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} stale recording sessions")

        return cleanup_count

    def get_session_statistics(
        self,
        camera_device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        days_back: int = 7,
    ) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = self.db.query(RecordingSession).filter(
            RecordingSession.started_at >= cutoff_date
        )

        if camera_device_id:
            query = query.filter(RecordingSession.camera_device_id == camera_device_id)

        if user_id:
            query = query.filter(RecordingSession.user_id == user_id)

        sessions = query.all()

        # Calculate statistics
        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.status == SessionStatus.ACTIVE])
        completed_sessions = len(
            [s for s in sessions if s.status == SessionStatus.COMPLETED]
        )
        failed_sessions = len([s for s in sessions if s.status == SessionStatus.FAILED])

        total_duration = sum(s.current_duration_seconds for s in sessions)
        total_file_size = sum(
            s.estimated_file_size_bytes for s in sessions if s.estimated_file_size_bytes
        )

        face_detection_triggered = len(
            [s for s in sessions if s.face_detection_triggered]
        )
        face_detection_completed = len(
            [s for s in sessions if s.face_detection_completed]
        )
        media_uploads_completed = len([s for s in sessions if s.media_upload_completed])

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "success_rate": (
                completed_sessions / total_sessions if total_sessions > 0 else 0
            ),
            "total_duration_seconds": total_duration,
            "average_duration_seconds": (
                total_duration / total_sessions if total_sessions > 0 else 0
            ),
            "total_file_size_bytes": total_file_size,
            "face_detection_trigger_rate": (
                face_detection_triggered / total_sessions if total_sessions > 0 else 0
            ),
            "face_detection_completion_rate": (
                face_detection_completed / face_detection_triggered
                if face_detection_triggered > 0
                else 0
            ),
            "media_upload_completion_rate": (
                media_uploads_completed / total_sessions if total_sessions > 0 else 0
            ),
            "period_days": days_back,
        }

    # Private Helper Methods

    def _record_status_update(
        self,
        session_uuid: str,
        duration_seconds: float,
        file_size_bytes: Optional[int] = None,
        frames_recorded: Optional[int] = None,
        current_fps: Optional[float] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ):
        """Record a status update for time-series monitoring"""
        try:
            status_record = RecordingSessionStatus(
                session_uuid=session_uuid,
                status_timestamp=datetime.utcnow(),
                duration_seconds=duration_seconds,
                file_size_bytes=file_size_bytes or 0,
                frames_recorded=frames_recorded or 0,
                current_fps=current_fps,
                context_data=context_data or {},
            )

            self.db.add(status_record)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to record status update: {e}")
            # Don't re-raise since this is auxiliary functionality

    def delete_session(self, session_uuid: str) -> bool:
        """Delete a recording session and all associated status records"""
        try:
            session = self.get_session(session_uuid)
            if not session:
                return False

            # Delete associated status records first (cascade should handle this but being explicit)
            self.db.query(RecordingSessionStatus).filter(
                RecordingSessionStatus.session_uuid == session_uuid
            ).delete()

            # Delete the session
            self.db.delete(session)
            self.db.commit()

            logger.info(f"Deleted recording session {session_uuid}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete session: {e}")
            return False


# Utility functions for easy session management
def get_recording_session_service() -> RecordingSessionService:
    """Get a RecordingSessionService instance"""
    return RecordingSessionService()


def create_recording_session(
    camera_device_id: str,
    user_id: str,
    recording_profile_id: Optional[int] = None,
    recording_config: Optional[Dict[str, Any]] = None,
    workflow_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[RecordingSession]:
    """Convenience function to create a recording session"""
    service = get_recording_session_service()
    try:
        return service.create_session(
            camera_device_id=camera_device_id,
            user_id=user_id,
            recording_profile_id=recording_profile_id,
            recording_config=recording_config,
            workflow_metadata=workflow_metadata,
        )
    except Exception as e:
        logger.error(f"Failed to create recording session: {e}")
        return None


def get_active_recording_sessions(
    camera_device_id: Optional[str] = None, user_id: Optional[str] = None
) -> List[RecordingSession]:
    """Convenience function to get active recording sessions"""
    service = get_recording_session_service()
    return service.get_active_sessions(camera_device_id, user_id)


def cleanup_stale_recording_sessions(heartbeat_timeout_minutes: int = 5) -> int:
    """Convenience function to cleanup stale sessions"""
    service = get_recording_session_service()
    return service.cleanup_stale_sessions(heartbeat_timeout_minutes)

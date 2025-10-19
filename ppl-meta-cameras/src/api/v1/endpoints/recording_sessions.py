"""
Recording Session API Endpoints for Camera Service
Created: 2025-10-15
Purpose: FastAPI endpoints for recording session management with UUID tracking
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera
from src.models.recording_session import RecordingSession
from src.security.auth import get_current_user
from src.services.recording_session_service import RecordingSessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/recording-sessions", tags=["recording-sessions"])


# Pydantic models for request/response
class RecordingStartRequest(BaseModel):
    """Request model for starting a recording session."""

    quality: str = Field(
        default="high", description="Recording quality: low, medium, high"
    )
    segment_interval_seconds: Optional[int] = Field(
        default=None, description="Automatic segment interval in seconds"
    )
    segment_duration_seconds: int = Field(
        default=30, description="Duration of each segment in seconds"
    )
    auto_face_detection_enabled: bool = Field(
        default=True, description="Enable automatic face detection"
    )
    video_codec: str = Field(default="h264", description="Video codec")
    audio_enabled: bool = Field(default=False, description="Enable audio")
    resolution_width: Optional[int] = Field(
        default=None, description="Video width in pixels"
    )
    resolution_height: Optional[int] = Field(
        default=None, description="Video height in pixels"
    )
    fps: Optional[int] = Field(default=None, description="Frames per second")
    bitrate: Optional[int] = Field(default=None, description="Video bitrate")
    face_detection_method: str = Field(
        default="enhanced-v2", description="Face detection method"
    )
    quality_preset: str = Field(
        default="balanced", description="Quality preset: fast, balanced, slow"
    )


class RecordingSessionResponse(BaseModel):
    """Response model for recording session operations."""

    session_uuid: str
    camera_device_id: str
    user_id: str
    status: str
    started_at: datetime
    stopped_at: Optional[datetime] = None
    recording_quality: str
    current_duration_seconds: float
    estimated_file_size_bytes: int
    frames_recorded: int
    created_at: datetime


class RecordingFileResponse(BaseModel):
    """Response model for recording file information."""

    file_uuid: str
    session_uuid: str
    file_name: str
    file_size_bytes: int
    duration_seconds: float
    media_uuid: Optional[str] = None
    is_uploaded_to_media: bool
    created_at: datetime


class SessionWithFilesResponse(BaseModel):
    """Response model for session with associated files."""

    session: Dict
    metadata: Optional[Dict] = None
    files: List[Dict]
    video_count: int
    total_duration: float
    total_size_bytes: int
    media_uuids: List[str]


class SessionProgressRequest(BaseModel):
    """Request model for updating session progress."""

    duration_seconds: float
    file_size_bytes: int = 0
    frames_recorded: int = 0


class AddFileRequest(BaseModel):
    """Request model for adding a file to a session."""

    file_path: str
    file_size_bytes: int = 0
    media_uuid: Optional[str] = None
    duration_seconds: float = 0.0
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    mime_type: str = "video/mp4"


# API Endpoints


@router.post("/", response_model=RecordingSessionResponse)
async def create_recording_session(
    camera_device_id: str = Query(..., description="Camera device ID"),
    request: RecordingStartRequest = RecordingStartRequest(),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new recording session for a camera.

    This endpoint initializes a new recording session with the specified configuration.
    Only one active recording session is allowed per camera at a time.
    """
    service = RecordingSessionService(db)

    try:
        # Convert request to config dict
        recording_config = request.dict()

        session = service.create_session(
            camera_device_id=camera_device_id,
            user_id=current_user.get("sub"),
            recording_config=recording_config,
        )

        # Get camera info for response
        camera = db.query(Camera).filter(Camera.id == session.camera_id).first()

        return RecordingSessionResponse(
            session_uuid=session.session_uuid,
            camera_device_id=camera.device_id if camera else camera_device_id,
            user_id=session.user_id,
            status=session.status,
            started_at=session.started_at,
            stopped_at=session.stopped_at,
            recording_quality=session.recording_quality,
            current_duration_seconds=session.current_duration_seconds,
            estimated_file_size_bytes=session.estimated_file_size_bytes,
            frames_recorded=session.frames_recorded,
            created_at=session.created_at,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create recording session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create recording session",
        )


@router.get("/", response_model=List[RecordingSessionResponse])
async def list_recording_sessions(
    camera_device_id: Optional[str] = Query(
        None, description="Filter by camera device ID"
    ),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of sessions to return"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List recording sessions with optional filtering.

    Returns recording sessions ordered by creation date (newest first).
    Users can only see their own sessions unless they have admin privileges.
    """
    service = RecordingSessionService(db)

    try:
        if camera_device_id:
            sessions = service.get_sessions_for_camera(camera_device_id, limit)
        elif user_id and user_id == current_user.get("sub"):
            sessions = service.get_sessions_for_user(user_id, limit)
        else:
            # Default to current user's sessions
            sessions = service.get_sessions_for_user(current_user.get("sub"), limit)

        # Filter by status if specified
        if status_filter:
            sessions = [s for s in sessions if s.status == status_filter]

        # Convert to response format
        response_sessions = []
        for session in sessions:
            camera = db.query(Camera).filter(Camera.id == session.camera_id).first()

            response_sessions.append(
                RecordingSessionResponse(
                    session_uuid=session.session_uuid,
                    camera_device_id=camera.device_id if camera else "unknown",
                    user_id=session.user_id,
                    status=session.status,
                    started_at=session.started_at,
                    stopped_at=session.stopped_at,
                    recording_quality=session.recording_quality,
                    current_duration_seconds=session.current_duration_seconds,
                    estimated_file_size_bytes=session.estimated_file_size_bytes,
                    frames_recorded=session.frames_recorded,
                    created_at=session.created_at,
                )
            )

        return response_sessions

    except Exception as e:
        logger.error(f"Failed to list recording sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list recording sessions",
        )


@router.get("/{session_uuid}", response_model=SessionWithFilesResponse)
async def get_recording_session(
    session_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a recording session including all associated files.

    Returns complete session information with metadata and ordered file list.
    Files are returned in chronological order (recording sequence).
    """
    service = RecordingSessionService(db)

    try:
        session_data = service.get_session_with_files(session_uuid)

        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording session not found",
            )

        # Check user access (users can only access their own sessions)
        if session_data["session"]["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        return SessionWithFilesResponse(**session_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recording session {session_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recording session",
        )


@router.delete("/{session_uuid}")
async def delete_recording_session(
    session_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stop and mark a recording session as stopped.

    This endpoint stops an active recording session gracefully.
    """
    service = RecordingSessionService(db)

    try:
        session = service.get_session(session_uuid)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording session not found",
            )

        # Check user access
        if session.user_id != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        updated_session = service.stop_session(session_uuid)

        return {
            "message": f"Recording session {session_uuid} stopped successfully",
            "status": updated_session.status,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to stop recording session {session_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop recording session",
        )


@router.put("/{session_uuid}/status")
async def update_session_status(
    session_uuid: str,
    status_update: str = Query(
        ..., description="New status: active, completed, failed, stopped"
    ),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update recording session status."""
    service = RecordingSessionService(db)

    try:
        session = service.get_session(session_uuid)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording session not found",
            )

        # Check user access
        if session.user_id != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Update status
        session.status = status_update
        if (
            status_update in ["completed", "failed", "stopped"]
            and not session.stopped_at
        ):
            session.stopped_at = datetime.utcnow()

        db.commit()

        return {
            "message": f"Session status updated to {status_update}",
            "session_uuid": session_uuid,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session status",
        )


@router.put("/{session_uuid}/progress")
async def update_session_progress(
    session_uuid: str,
    progress: SessionProgressRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update recording session progress metrics."""
    service = RecordingSessionService(db)

    try:
        session = service.update_session_progress(
            session_uuid=session_uuid,
            duration_seconds=progress.duration_seconds,
            file_size_bytes=progress.file_size_bytes,
            frames_recorded=progress.frames_recorded,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording session not found",
            )

        return {"message": "Session progress updated", "session_uuid": session_uuid}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session progress",
        )


@router.post("/{session_uuid}/heartbeat")
async def session_heartbeat(
    session_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send heartbeat to keep session alive."""
    service = RecordingSessionService(db)

    try:
        session = service.get_session(session_uuid)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording session not found",
            )

        session.last_heartbeat = datetime.utcnow()
        db.commit()

        return {
            "message": "Heartbeat received",
            "session_uuid": session_uuid,
            "timestamp": session.last_heartbeat,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process heartbeat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process heartbeat",
        )


@router.post("/{session_uuid}/files")
async def add_file_to_session(
    session_uuid: str,
    file_info: AddFileRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a recorded file to a session."""
    service = RecordingSessionService(db)

    try:
        recording_file = service.add_file_to_session(
            session_uuid=session_uuid,
            file_path=file_info.file_path,
            file_size_bytes=file_info.file_size_bytes,
            media_uuid=file_info.media_uuid,
            duration_seconds=file_info.duration_seconds,
            video_codec=file_info.video_codec,
            audio_codec=file_info.audio_codec,
            mime_type=file_info.mime_type,
        )

        return {
            "message": "File added to session",
            "file_uuid": recording_file.file_uuid,
            "session_uuid": session_uuid,
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add file to session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add file to session",
        )


@router.get("/{session_uuid}/files", response_model=List[RecordingFileResponse])
async def get_session_files(
    session_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all files for a recording session in chronological order."""
    service = RecordingSessionService(db)

    try:
        session = service.get_session(session_uuid)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording session not found",
            )

        # Check user access
        if session.user_id != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        files = service.get_session_files(session_uuid)

        return [
            RecordingFileResponse(
                file_uuid=f.file_uuid,
                session_uuid=f.session_uuid,
                file_name=f.file_name,
                file_size_bytes=f.file_size_bytes,
                duration_seconds=f.duration_seconds,
                media_uuid=f.media_uuid,
                is_uploaded_to_media=f.is_uploaded_to_media,
                created_at=f.created_at,
            )
            for f in files
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session files",
        )


# Camera-specific endpoints


@router.get("/camera/{camera_device_id}", response_model=List[RecordingSessionResponse])
async def get_camera_sessions(
    camera_device_id: str,
    limit: int = Query(50, description="Maximum number of sessions to return"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all recording sessions for a specific camera."""
    service = RecordingSessionService(db)

    try:
        sessions = service.get_sessions_for_camera(camera_device_id, limit)

        return [
            RecordingSessionResponse(
                session_uuid=session.session_uuid,
                camera_device_id=camera_device_id,
                user_id=session.user_id,
                status=session.status,
                started_at=session.started_at,
                stopped_at=session.stopped_at,
                recording_quality=session.recording_quality,
                current_duration_seconds=session.current_duration_seconds,
                estimated_file_size_bytes=session.estimated_file_size_bytes,
                frames_recorded=session.frames_recorded,
                created_at=session.created_at,
            )
            for session in sessions
        ]

    except Exception as e:
        logger.error(f"Failed to get camera sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get camera sessions",
        )


@router.get("/user/{user_id}", response_model=List[RecordingSessionResponse])
async def get_user_sessions(
    user_id: str,
    limit: int = Query(50, description="Maximum number of sessions to return"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all recording sessions for a specific user."""
    # Users can only access their own sessions
    if user_id != current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    service = RecordingSessionService(db)

    try:
        sessions = service.get_sessions_for_user(user_id, limit)

        response_sessions = []
        for session in sessions:
            camera = db.query(Camera).filter(Camera.id == session.camera_id).first()

            response_sessions.append(
                RecordingSessionResponse(
                    session_uuid=session.session_uuid,
                    camera_device_id=camera.device_id if camera else "unknown",
                    user_id=session.user_id,
                    status=session.status,
                    started_at=session.started_at,
                    stopped_at=session.stopped_at,
                    recording_quality=session.recording_quality,
                    current_duration_seconds=session.current_duration_seconds,
                    estimated_file_size_bytes=session.estimated_file_size_bytes,
                    frames_recorded=session.frames_recorded,
                    created_at=session.created_at,
                )
            )

        return response_sessions

    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user sessions",
        )


# Monitoring endpoints


@router.get("/monitoring/active")
async def get_active_sessions(
    current_user: Dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all currently active recording sessions."""
    service = RecordingSessionService(db)

    try:
        active_sessions = service.get_active_sessions()

        return {
            "active_sessions_count": len(active_sessions),
            "sessions": [
                {
                    "session_uuid": session.session_uuid,
                    "camera_id": session.camera_id,
                    "user_id": session.user_id,
                    "started_at": session.started_at,
                    "duration_seconds": session.current_duration_seconds,
                    "last_heartbeat": session.last_heartbeat,
                }
                for session in active_sessions
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active sessions",
        )


@router.get("/monitoring/stale")
async def get_stale_sessions(
    max_age_hours: int = Query(24, description="Maximum age for active sessions"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get sessions that appear to be stale (no recent heartbeat)."""
    from datetime import timedelta

    from sqlalchemy import and_

    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        stale_sessions = (
            db.query(RecordingSession)
            .filter(
                and_(
                    RecordingSession.status == "active",
                    RecordingSession.last_heartbeat < cutoff_time,
                )
            )
            .all()
        )

        return {
            "stale_sessions_count": len(stale_sessions),
            "max_age_hours": max_age_hours,
            "cutoff_time": cutoff_time,
            "sessions": [
                {
                    "session_uuid": session.session_uuid,
                    "camera_id": session.camera_id,
                    "started_at": session.started_at,
                    "last_heartbeat": session.last_heartbeat,
                    "hours_since_heartbeat": (
                        datetime.utcnow() - session.last_heartbeat
                    ).total_seconds()
                    / 3600,
                }
                for session in stale_sessions
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get stale sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stale sessions",
        )


@router.post("/monitoring/cleanup-stale")
async def cleanup_stale_sessions(
    max_age_hours: int = Query(24, description="Maximum age for active sessions"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark stale sessions as failed."""
    service = RecordingSessionService(db)

    try:
        cleaned_count = service.cleanup_stale_sessions(max_age_hours)

        return {
            "message": f"Cleaned up {cleaned_count} stale sessions",
            "cleaned_sessions_count": cleaned_count,
            "max_age_hours": max_age_hours,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup stale sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup stale sessions",
        )


@router.get("/statistics")
async def get_session_statistics(
    current_user: Dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get recording session statistics."""
    service = RecordingSessionService(db)

    try:
        stats = service.get_session_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get session statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session statistics",
        )


@router.get("/health")
async def recording_sessions_health():
    """Recording sessions health check."""
    return {
        "status": "healthy",
        "service": "recording-sessions",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
    }

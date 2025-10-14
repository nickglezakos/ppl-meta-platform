# ppl-meta-orchestrator/src/api/recording_session_endpoints.py
"""
Recording Session API Endpoints - Phase 4 Implementation
Comprehensive REST API for recording session management and workflow integration
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from models.recording_session import SessionStatus
from pydantic import BaseModel, Field
from services.recording_session_service import RecordingSessionService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/recording-sessions", tags=["Recording Sessions"])

# Pydantic Models for API


class CreateRecordingSessionRequest(BaseModel):
    camera_device_id: str = Field(..., description="Camera device identifier")
    user_id: str = Field(..., description="User identifier")
    recording_profile_id: Optional[int] = Field(
        None, description="Recording profile ID"
    )
    recording_config: Optional[Dict[str, Any]] = Field(
        None, description="Recording configuration"
    )
    workflow_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Workflow metadata"
    )


class UpdateSessionStatusRequest(BaseModel):
    status: SessionStatus = Field(..., description="New session status")
    error_message: Optional[str] = Field(
        None, description="Error message if status is failed"
    )
    context_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional context data"
    )


class UpdateSessionProgressRequest(BaseModel):
    duration_seconds: float = Field(..., description="Current recording duration")
    frames_recorded: int = Field(..., description="Number of frames recorded")
    estimated_file_size_bytes: Optional[int] = Field(
        None, description="Estimated file size"
    )
    average_fps: Optional[float] = Field(None, description="Average FPS")
    performance_metrics: Optional[Dict[str, Any]] = Field(
        None, description="Performance metrics"
    )


class TriggerFaceDetectionRequest(BaseModel):
    face_detection_session_uuid: str = Field(
        ..., description="Face detection session UUID"
    )
    workflow_execution_id: Optional[str] = Field(
        None, description="Workflow execution ID"
    )


class CompleteFaceDetectionRequest(BaseModel):
    face_detection_results: Optional[Dict[str, Any]] = Field(
        None, description="Face detection results"
    )


class UpdateMediaUploadRequest(BaseModel):
    started: Optional[bool] = Field(None, description="Media upload started")
    completed: Optional[bool] = Field(None, description="Media upload completed")
    media_collection_id: Optional[str] = Field(None, description="Media collection ID")
    media_uuid: Optional[str] = Field(None, description="Media UUID")


class RecordingSessionResponse(BaseModel):
    """Response model for recording session data"""

    session_uuid: str
    camera_device_id: str
    user_id: str
    recording_profile_id: Optional[int]
    status: SessionStatus
    started_at: datetime
    stopped_at: Optional[datetime]
    last_heartbeat: datetime
    current_duration_seconds: float
    estimated_file_size_bytes: int
    frames_recorded: int
    average_fps: Optional[float]
    error_message: Optional[str]
    warning_count: int
    retry_count: int
    face_detection_triggered: bool
    face_detection_completed: bool
    face_detection_session_uuid: Optional[str]
    workflow_execution_id: Optional[str]
    media_upload_started: bool
    media_upload_completed: bool
    media_collection_id: Optional[str]
    media_uuid: Optional[str]
    recording_config: Optional[Dict[str, Any]]
    workflow_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionStatisticsResponse(BaseModel):
    """Response model for session statistics"""

    total_sessions: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
    success_rate: float
    total_duration_seconds: float
    average_duration_seconds: float
    total_file_size_bytes: int
    face_detection_trigger_rate: float
    face_detection_completion_rate: float
    media_upload_completion_rate: float
    period_days: int


# Session Management Endpoints


@router.post("/", response_model=RecordingSessionResponse)
async def create_recording_session(
    request: CreateRecordingSessionRequest, db: Session = Depends(get_db)
):
    """Create a new recording session"""
    try:
        service = RecordingSessionService(db)
        session = service.create_session(
            camera_device_id=request.camera_device_id,
            user_id=request.user_id,
            recording_profile_id=request.recording_profile_id,
            recording_config=request.recording_config,
            workflow_metadata=request.workflow_metadata,
        )

        return RecordingSessionResponse.from_orm(session)

    except Exception as e:
        logger.error("Failed to create recording session: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to create recording session: {str(e)}"
        )


@router.get("/{session_uuid}", response_model=RecordingSessionResponse)
async def get_recording_session(session_uuid: str, db: Session = Depends(get_db)):
    """Get a specific recording session by UUID"""
    try:
        service = RecordingSessionService(db)
        session = service.get_session(session_uuid)

        if not session:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return RecordingSessionResponse.from_orm(session)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get recording session: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get recording session: {str(e)}"
        )


@router.get("/", response_model=List[RecordingSessionResponse])
async def list_recording_sessions(
    camera_device_id: Optional[str] = Query(
        None, description="Filter by camera device ID"
    ),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[SessionStatus] = Query(
        None, description="Filter by session status"
    ),
    active_only: bool = Query(False, description="Return only active sessions"),
    limit: int = Query(50, description="Maximum number of sessions to return"),
    db: Session = Depends(get_db),
):
    """List recording sessions with optional filtering"""
    try:
        service = RecordingSessionService(db)

        if active_only:
            sessions = service.get_active_sessions(camera_device_id, user_id)
        elif camera_device_id:
            sessions = service.get_sessions_by_camera(camera_device_id, limit, status)
        elif user_id:
            sessions = service.get_sessions_by_user(user_id, limit, status)
        else:
            # Get all sessions with basic filtering
            sessions = service.get_active_sessions() if not status else []

        return [RecordingSessionResponse.from_orm(session) for session in sessions]

    except Exception as e:
        logger.error("Failed to list recording sessions: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to list recording sessions: {str(e)}"
        )


@router.delete("/{session_uuid}")
async def delete_recording_session(session_uuid: str, db: Session = Depends(get_db)):
    """Delete a recording session"""
    try:
        service = RecordingSessionService(db)
        success = service.delete_session(session_uuid)

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Recording session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete recording session: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to delete recording session: {str(e)}"
        )


# Session Status and Progress Endpoints


@router.put("/{session_uuid}/status")
async def update_session_status(
    session_uuid: str,
    request: UpdateSessionStatusRequest,
    db: Session = Depends(get_db),
):
    """Update session status"""
    try:
        service = RecordingSessionService(db)
        success = service.update_session_status(
            session_uuid=session_uuid,
            status=request.status,
            error_message=request.error_message,
            context_data=request.context_data,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Session status updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update session status: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to update session status: {str(e)}"
        )


@router.put("/{session_uuid}/progress")
async def update_session_progress(
    session_uuid: str,
    request: UpdateSessionProgressRequest,
    db: Session = Depends(get_db),
):
    """Update session progress metrics"""
    try:
        service = RecordingSessionService(db)
        success = service.update_session_progress(
            session_uuid=session_uuid,
            duration_seconds=request.duration_seconds,
            frames_recorded=request.frames_recorded,
            estimated_file_size_bytes=request.estimated_file_size_bytes,
            average_fps=request.average_fps,
            performance_metrics=request.performance_metrics,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Session progress updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update session progress: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to update session progress: {str(e)}"
        )


@router.post("/{session_uuid}/heartbeat")
async def session_heartbeat(session_uuid: str, db: Session = Depends(get_db)):
    """Update session heartbeat to indicate it's still active"""
    try:
        service = RecordingSessionService(db)
        success = service.heartbeat_session(session_uuid)

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Session heartbeat updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update session heartbeat: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to update session heartbeat: {str(e)}"
        )


# Workflow Integration Endpoints


@router.post("/{session_uuid}/face-detection/trigger")
async def trigger_face_detection(
    session_uuid: str,
    request: TriggerFaceDetectionRequest,
    db: Session = Depends(get_db),
):
    """Trigger face detection workflow for the session"""
    try:
        service = RecordingSessionService(db)
        success = service.trigger_face_detection(
            session_uuid=session_uuid,
            face_detection_session_uuid=request.face_detection_session_uuid,
            workflow_execution_id=request.workflow_execution_id,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Face detection triggered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger face detection: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger face detection: {str(e)}"
        )


@router.post("/{session_uuid}/face-detection/complete")
async def complete_face_detection(
    session_uuid: str,
    request: CompleteFaceDetectionRequest,
    db: Session = Depends(get_db),
):
    """Mark face detection as completed for the session"""
    try:
        service = RecordingSessionService(db)
        success = service.complete_face_detection(
            session_uuid=session_uuid,
            face_detection_results=request.face_detection_results,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Face detection completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to complete face detection: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to complete face detection: {str(e)}"
        )


@router.put("/{session_uuid}/media-upload")
async def update_media_upload_status(
    session_uuid: str, request: UpdateMediaUploadRequest, db: Session = Depends(get_db)
):
    """Update media upload status for the session"""
    try:
        service = RecordingSessionService(db)
        success = service.update_media_upload_status(
            session_uuid=session_uuid,
            started=request.started,
            completed=request.completed,
            media_collection_id=request.media_collection_id,
            media_uuid=request.media_uuid,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recording session not found")

        return {"message": "Media upload status updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update media upload status: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to update media upload status: {str(e)}"
        )


# Monitoring and Statistics Endpoints


@router.get("/monitoring/active", response_model=List[RecordingSessionResponse])
async def get_active_sessions(db: Session = Depends(get_db)):
    """Get all currently active recording sessions"""
    try:
        service = RecordingSessionService(db)
        sessions = service.get_active_sessions()

        return [RecordingSessionResponse.from_orm(session) for session in sessions]

    except Exception as e:
        logger.error("Failed to get active sessions: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get active sessions: {str(e)}"
        )


@router.get("/monitoring/stale", response_model=List[RecordingSessionResponse])
async def get_stale_sessions(
    heartbeat_timeout_minutes: int = Query(
        5, description="Heartbeat timeout in minutes"
    ),
    db: Session = Depends(get_db),
):
    """Get sessions that haven't had a heartbeat within the timeout period"""
    try:
        service = RecordingSessionService(db)
        sessions = service.find_stale_sessions(heartbeat_timeout_minutes)

        return [RecordingSessionResponse.from_orm(session) for session in sessions]

    except Exception as e:
        logger.error("Failed to get stale sessions: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get stale sessions: {str(e)}"
        )


@router.post("/monitoring/cleanup-stale")
async def cleanup_stale_sessions(
    heartbeat_timeout_minutes: int = Query(
        5, description="Heartbeat timeout in minutes"
    ),
    db: Session = Depends(get_db),
):
    """Cleanup stale sessions by marking them as timed out"""
    try:
        service = RecordingSessionService(db)
        cleanup_count = service.cleanup_stale_sessions(heartbeat_timeout_minutes)

        return {
            "message": f"Cleaned up {cleanup_count} stale sessions",
            "cleanup_count": cleanup_count,
        }

    except Exception as e:
        logger.error("Failed to cleanup stale sessions: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup stale sessions: {str(e)}"
        )


@router.get("/statistics", response_model=SessionStatisticsResponse)
async def get_session_statistics(
    camera_device_id: Optional[str] = Query(
        None, description="Filter by camera device ID"
    ),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days_back: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db),
):
    """Get comprehensive session statistics"""
    try:
        service = RecordingSessionService(db)
        stats = service.get_session_statistics(
            camera_device_id=camera_device_id, user_id=user_id, days_back=days_back
        )

        return SessionStatisticsResponse(**stats)

    except Exception as e:
        logger.error("Failed to get session statistics: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get session statistics: {str(e)}"
        )


# Camera-specific endpoints


@router.get("/camera/{camera_device_id}", response_model=List[RecordingSessionResponse])
async def get_camera_sessions(
    camera_device_id: str,
    status: Optional[SessionStatus] = Query(
        None, description="Filter by session status"
    ),
    limit: int = Query(50, description="Maximum number of sessions to return"),
    db: Session = Depends(get_db),
):
    """Get recording sessions for a specific camera"""
    try:
        service = RecordingSessionService(db)
        sessions = service.get_sessions_by_camera(camera_device_id, limit, status)

        return [RecordingSessionResponse.from_orm(session) for session in sessions]

    except Exception as e:
        logger.error("Failed to get camera sessions: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get camera sessions: {str(e)}"
        )


# User-specific endpoints


@router.get("/user/{user_id}", response_model=List[RecordingSessionResponse])
async def get_user_sessions(
    user_id: str,
    status: Optional[SessionStatus] = Query(
        None, description="Filter by session status"
    ),
    limit: int = Query(50, description="Maximum number of sessions to return"),
    db: Session = Depends(get_db),
):
    """Get recording sessions for a specific user"""
    try:
        service = RecordingSessionService(db)
        sessions = service.get_sessions_by_user(user_id, limit, status)

        return [RecordingSessionResponse.from_orm(session) for session in sessions]

    except Exception as e:
        logger.error("Failed to get user sessions: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get user sessions: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def recording_sessions_health():
    """Health check endpoint for recording sessions API"""
    return {
        "status": "healthy",
        "service": "recording-sessions",
        "timestamp": datetime.utcnow().isoformat(),
    }

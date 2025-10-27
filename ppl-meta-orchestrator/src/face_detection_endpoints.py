"""
Face Detection Endpoints for PPL Meta Orchestrator
==================================================

Implements the self-referencing face detection architecture where Orchestrator
manages face detection sessions and calls its own endpoints for consistency.

Key Features:
- Session-based face detection with UUID tracking
- Self-referencing architecture (Orchestrator → Orchestrator)
- Stored vs live processing handling
- Integration with Vision Service
- Flutter-compatible response format
"""

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from service_clients import ServiceClientManager

# Configure logging
logger = logging.getLogger(__name__)

# Import distance calculator for Enhanced Logic V2 distance integration
try:
    import os
    import sys

    # Add ppl-meta-vision to path for distance calculator import
    vision_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "ppl-meta-vision",
        "src",
    )
    if vision_path not in sys.path:
        sys.path.insert(0, vision_path)

    from distance_calculator import enhance_face_detections_with_distance

    logger.info("✅ Successfully imported distance calculator")
except ImportError as e:
    logger.warning(f"⚠️ Failed to import distance calculator: {e}")
    # Fallback function if import fails

    def enhance_face_detections_with_distance(face_detections):
        logger.warning("Using fallback - no distance calculations applied")
        return face_detections


# Security setup
security = HTTPBearer()


def get_auth_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract and validate authentication token."""
    return credentials.credentials


# Router for face detection endpoints
face_detection_router = APIRouter(prefix="/api/v1", tags=["face-detection"])

# ============================================================================
# MODELS AND ENUMS
# ============================================================================


class SessionStatus(str, Enum):
    """Face detection session status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FaceDetectionRequest(BaseModel):
    """Request model for face detection."""

    media_id: str = Field(..., description="UUID of the media to process")
    method: str = Field(default="two_stage", description="Detection method")
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    frames_per_second: int = Field(default=1, ge=1, le=30)
    save_results: bool = Field(
        default=True, description="Save to Vision Service database"
    )


class FaceDetectionSession(BaseModel):
    """Face detection session model."""

    session_id: str
    media_id: str
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class MediaFaceDetectionResponse(BaseModel):
    """Response for media face detection with stored/live handling."""

    media_id: str
    has_stored_results: bool
    stored_result: Optional[Dict[str, Any]] = None
    live_session: Optional[FaceDetectionSession] = None


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================


class FaceDetectionSessionManager:
    """Manages face detection sessions with self-referencing capabilities."""

    def __init__(self):
        self.sessions: Dict[str, FaceDetectionSession] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.service_clients = ServiceClientManager()

    def create_session(self, request: FaceDetectionRequest) -> FaceDetectionSession:
        """Create a new face detection session."""
        session_id = str(uuid.uuid4())
        session = FaceDetectionSession(
            session_id=session_id,
            media_id=request.media_id,
            status=SessionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self.sessions[session_id] = session
        logger.info(
            f"Created face detection session {session_id} for media {request.media_id}"
        )
        return session

    def get_session(self, session_id: str) -> Optional[FaceDetectionSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def update_session(
        self, session_id: str, **updates
    ) -> Optional[FaceDetectionSession]:
        """Update session with new data."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            return session
        return None

    def list_sessions(
        self, media_id: Optional[str] = None
    ) -> List[FaceDetectionSession]:
        """List sessions, optionally filtered by media_id."""
        sessions = list(self.sessions.values())
        if media_id:
            sessions = [s for s in sessions if s.media_id == media_id]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    async def check_stored_faces(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Check if faces are already stored in Vision Service database."""
        try:
            vision_url = f"http://localhost:8003/faces/media/{media_id}"
            response = requests.get(vision_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data.get("faces", [])) > 0:
                    logger.info(
                        f"Found stored faces for media {media_id}: {len(data['faces'])} faces"
                    )
                    return data
                else:
                    logger.info(f"No stored faces found for media {media_id}")
                    return None
            else:
                logger.warning(
                    f"Vision Service returned {response.status_code} for media {media_id}"
                )
                return None
        except Exception as e:
            logger.error(f"Error checking stored faces for media {media_id}: {e}")
            return None

    async def enhanced_logic_v2_session_based(
        self, media_id: str, auth_token: str, frame_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Enhanced Logic V2: Session-based face detection with frame sampling.

        Workflow:
        1. Create/start a session UUID for this media processing
        2. Check for stored faces under session or media
        3. If no stored faces → Call Vision Service for real-time detection
           with configurable frame sampling for performance optimization
        4. If stored faces found → Use existing data
        5. Everything happens under the same session UUID

        Args:
            media_id: The media UUID to process

        Returns:
            dict: Session-based response with faces and session information
        """
        import time

        start_time = time.time()
        session_uuid = str(uuid.uuid4())

        logger.info(f"🆔 Starting Enhanced Logic V2 for media {media_id}")
        logger.info(f"   🎯 Session UUID: {session_uuid}")

        try:
            # Step 1: Check for stored faces in Vision Service
            logger.info("🔍 Step 1: Checking for stored faces...")
            vision_url = f"http://localhost:8003/faces/media/{media_id}"
            logger.info(f"🔍 Vision URL: {vision_url}")
            
            # Add cache-busting headers to prevent HTTP caching issues
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            response = requests.get(vision_url, headers=headers, timeout=15)
            
            logger.info(f"🔍 Vision response status: {response.status_code}")
            logger.info(f"🔍 RAW Vision response text (first 200 chars): {response.text[:200]}")
            
            if response.status_code == 200:
                # Parse JSON from text to avoid response.json() caching issues
                import json
                response_text = str(response.text)  # Force copy of string
                faces_data = json.loads(response_text)
                
                # Immediately check what we parsed
                parsed_media_id = str(faces_data.get('media_id', 'NONE'))
                logger.info(f"🔍 IMMEDIATELY after json.loads, media_id: {parsed_media_id}")
                logger.info(f"🔍 faces_data object id: {id(faces_data)}")
                logger.info(f"🔍 Vision response media_id: {faces_data.get('media_id')}")
                logger.info(f"🔍 Expected media_id: {media_id}")
                logger.info(f"🔍 Media IDs match: {faces_data.get('media_id') == media_id}")
                logger.info(f"🔍 Has stored faces: {faces_data.get('has_stored_faces', False)}")
                logger.info(f"🔍 Total faces: {faces_data.get('total_faces', 0)}")

                # Check if we have stored faces
                if faces_data.get("has_stored_faces", False):
                    stored_face_count = faces_data.get("total_faces", 0)
                    faces_by_frame = faces_data.get("faces_by_frame", {})

                    logger.info(
                        f"✅ Found stored faces: {stored_face_count} faces "
                        f"in {len(faces_by_frame)} frames"
                    )
                    logger.info("🔄 Using existing session-linked data")

                    # Convert faces_by_frame to flat faces array
                    faces_array = []
                    for frame_num, frame_faces in faces_by_frame.items():
                        for face in frame_faces:
                            face["frame_number"] = int(frame_num)
                            faces_array.append(face)

                    # ✨ ENHANCED LOGIC V2 DISTANCE INTEGRATION
                    # Add distance calculations, center coordinates, and dimensions
                    logger.info(
                        "🧮 Enhancing stored faces with distance calculations..."
                    )
                    enhanced_faces = enhance_face_detections_with_distance(faces_array)
                    logger.info(
                        f"✅ Enhanced {len(enhanced_faces)} faces with distance data"
                    )

                    processing_time = time.time() - start_time

                    return {
                        "success": True,
                        "session_uuid": session_uuid,
                        "media_id": media_id,
                        "source": "stored_faces",
                        "total_faces": stored_face_count,
                        "faces": enhanced_faces,  # Now includes distance data
                        "faces_by_frame": faces_by_frame,
                        "processing_time": processing_time,
                        "message": (
                            f"Retrieved {stored_face_count} stored faces "
                            f"with distance calculations from existing session data"
                        ),
                    }
                else:
                    total_faces = faces_data.get("total_faces", 0)
                    logger.info(f"⚠️ No stored faces found ({total_faces} faces)")
                    logger.info("🚀 Triggering real-time face detection...")

                    # Step 2: No stored faces - trigger real-time detection
                    return await self._trigger_realtime_detection(
                        media_id, session_uuid, start_time, auth_token, frame_interval
                    )

            else:
                logger.warning(
                    f"❌ Error checking stored faces: {response.status_code}"
                )
                logger.info("🚀 Falling back to real-time detection...")

                # Fallback to real-time detection
                return await self._trigger_realtime_detection(
                    media_id, session_uuid, start_time, auth_token
                )

        except Exception as e:
            logger.error(f"❌ Error in Enhanced Logic V2: {e}")
            processing_time = time.time() - start_time

            return {
                "success": False,
                "session_uuid": session_uuid,
                "media_id": media_id,
                "source": "error",
                "total_faces": 0,
                "faces": [],
                "processing_time": processing_time,
                "error": str(e),
                "message": f"Enhanced Logic V2 failed: {e}",
            }

    async def _trigger_realtime_detection(
        self,
        media_id: str,
        session_uuid: str,
        start_time: float,
        auth_token: str,
        frame_interval: int = 10,
    ) -> Dict[str, Any]:
        """
        Trigger real-time face detection via Vision Service with frame sampling.

        Args:
            media_id: The media UUID to process
            session_uuid: The session UUID for this processing
            start_time: Start timestamp for performance measurement
            auth_token: Authentication token for Vision Service requests
            frame_interval: Process every N frames (default: 10)

        Returns:
            dict: Real-time detection results with session information
        """
        import time

        logger.info("🔄 Step 2: Real-time face detection")
        logger.info(
            f"   📡 Calling Vision Service bulk-process "
            f"with frame_interval={frame_interval}..."
        )

        try:
            # Call Vision Service for real-time detection with frame sampling
            bulk_detect_url = (
                f"http://localhost:8003/faces/media/{media_id}/bulk-process"
                f"?force_process=true&frame_interval={frame_interval}"
            )

            # Create headers with Authorization token
            headers = {"Authorization": f"Bearer {auth_token}"}

            # Call bulk-process with frame sampling
            # URL includes force_process and frame_interval parameters
            detection_response = requests.post(
                bulk_detect_url,
                headers=headers,
                timeout=60,  # Face detection can take time
            )

            logger.info(f"📊 Detection Status: {detection_response.status_code}")

            if detection_response.status_code == 200:
                detection_data = detection_response.json()
                logger.info(f"✅ Real-time detection completed: {detection_data}")

                # Now retrieve the newly detected faces
                faces_url = f"http://localhost:8003/faces/media/{media_id}"
                faces_response = requests.get(faces_url, headers=headers, timeout=15)

                if faces_response.status_code == 200:
                    faces_data = faces_response.json()
                    detected_face_count = faces_data.get("total_faces", 0)
                    faces_by_frame = faces_data.get("faces_by_frame", {})

                    logger.info(
                        f"🎯 Retrieved {detected_face_count} newly detected faces"
                    )

                    # Convert to flat array
                    faces_array = []
                    for frame_num, frame_faces in faces_by_frame.items():
                        for face in frame_faces:
                            face["frame_number"] = int(frame_num)
                            faces_array.append(face)

                    # ✨ ENHANCED LOGIC V2 DISTANCE INTEGRATION
                    # Add distance calculations, center coordinates, and dimensions
                    logger.info(
                        "🧮 Enhancing real-time faces with distance calculations..."
                    )
                    enhanced_faces = enhance_face_detections_with_distance(faces_array)
                    logger.info(
                        f"✅ Enhanced {len(enhanced_faces)} faces with distance data"
                    )

                    processing_time = time.time() - start_time

                    # Create session linkage for future use
                    session_data = {
                        "session_uuid": session_uuid,
                        "media_id": media_id,
                        "face_count": detected_face_count,
                        "detection_method": "real_time_enhanced_logic_v2",
                        "timestamp": datetime.now().isoformat(),
                    }

                    return {
                        "success": True,
                        "session_uuid": session_uuid,
                        "media_id": media_id,
                        "source": "real_time_detection",
                        "total_faces": detected_face_count,
                        "faces": enhanced_faces,  # Now includes distance data
                        "faces_by_frame": faces_by_frame,
                        "processing_time": processing_time,
                        "session_data": session_data,
                        "detection_result": detection_data,
                        "message": (
                            f"Detected {detected_face_count} faces "
                            f"via real-time processing with distance calculations"
                        ),
                    }
                else:
                    error_msg = f"Failed to retrieve detected faces: {faces_response.status_code}"
                    logger.error(f"❌ {error_msg}")

            else:
                error_msg = (
                    f"Real-time detection failed: {detection_response.status_code}"
                )
                logger.error(f"❌ {error_msg}")
                error_detail = detection_response.text
                logger.error(f"   Error: {error_detail}")

            # Return error result
            processing_time = time.time() - start_time
            return {
                "success": False,
                "session_uuid": session_uuid,
                "media_id": media_id,
                "source": "real_time_detection_failed",
                "total_faces": 0,
                "faces": [],
                "processing_time": processing_time,
                "error": (
                    error_detail
                    if "error_detail" in locals()
                    else "Real-time detection failed"
                ),
                "message": "Real-time face detection failed",
            }

        except Exception as e:
            logger.error(f"❌ Real-time detection error: {e}")
            processing_time = time.time() - start_time

            return {
                "success": False,
                "session_uuid": session_uuid,
                "media_id": media_id,
                "source": "real_time_detection_error",
                "total_faces": 0,
                "faces": [],
                "processing_time": processing_time,
                "error": str(e),
                "message": f"Real-time detection error: {e}",
            }

    async def trigger_orchestrator_processing(
        self, request: FaceDetectionRequest
    ) -> FaceDetectionSession:
        """
        Trigger face detection processing through Orchestrator's own endpoint.
        This implements the self-referencing architecture.
        """
        session = self.create_session(request)

        # Start processing in background
        self.executor.submit(self._process_face_detection, session, request)

        return session

    def _process_face_detection(
        self, session: FaceDetectionSession, request: FaceDetectionRequest
    ):
        """Process face detection in background thread."""
        try:
            # Update status to running
            session.status = SessionStatus.RUNNING
            session.started_at = datetime.now(timezone.utc)
            session.progress = 0.1

            logger.info(
                f"Starting face detection processing for session {session.session_id}"
            )

            # Call Vision Service for face detection
            vision_url = f"http://localhost:8003/faces/media/{request.media_id}"
            params = {
                "method": request.method,
                "confidence_threshold": request.confidence_threshold,
                "frames_per_second": request.frames_per_second,
            }

            session.progress = 0.3

            response = requests.get(
                vision_url, params=params, timeout=300
            )  # 5 minutes timeout

            if response.status_code == 200:
                result = response.json()
                session.result = result
                session.status = SessionStatus.COMPLETED
                session.progress = 1.0
                session.completed_at = datetime.now(timezone.utc)

                logger.info(
                    f"Face detection completed for session {session.session_id}"
                )
                logger.info(f"Found {len(result.get('faces', []))} faces")

            else:
                error_msg = (
                    f"Vision Service error: {response.status_code} - {response.text}"
                )
                session.error_message = error_msg
                session.status = SessionStatus.FAILED
                session.completed_at = datetime.now(timezone.utc)
                logger.error(
                    f"Face detection failed for session {session.session_id}: {error_msg}"
                )

        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            session.error_message = error_msg
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.error(
                f"Face detection exception for session {session.session_id}: {error_msg}"
            )


# Global session manager instance
session_manager = FaceDetectionSessionManager()

# ============================================================================
# API ENDPOINTS
# ============================================================================


@face_detection_router.post("/face-detection", response_model=FaceDetectionSession)
async def create_face_detection_session(
    request: FaceDetectionRequest, auth_token: str = Depends(get_auth_token)
):
    """
    Create a new face detection session.

    This endpoint creates a session and starts face detection processing
    in the background using the self-referencing architecture.
    """
    try:
        session = await session_manager.trigger_orchestrator_processing(request)
        return session
    except Exception as e:
        logger.error(f"Error creating face detection session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@face_detection_router.get(
    "/sessions/{session_id}", response_model=FaceDetectionSession
)
async def get_face_detection_session(
    session_id: str, auth_token: str = Depends(get_auth_token)
):
    """Get face detection session status and results."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@face_detection_router.get("/sessions", response_model=List[FaceDetectionSession])
async def list_face_detection_sessions(
    media_id: Optional[str] = None, auth_token: str = Depends(get_auth_token)
):
    """List face detection sessions, optionally filtered by media_id."""
    sessions = session_manager.list_sessions(media_id=media_id)
    return sessions


@face_detection_router.get(
    "/media/{media_id}/faces", response_model=MediaFaceDetectionResponse
)
async def get_media_face_detection(
    media_id: str, auth_token: str = Depends(get_auth_token)
):
    """
    Get face detection for media with stored/live processing handling.

    This is the main endpoint that implements the self-referencing architecture:
    1. Check for stored face detection results
    2. If none found, trigger live processing through Orchestrator's own endpoint
    3. Return unified response with either stored results or live session
    """
    try:
        # Check for stored faces first
        stored_result = await session_manager.check_stored_faces(media_id)

        if stored_result and len(stored_result.get("faces", [])) > 0:
            # Return stored results
            return MediaFaceDetectionResponse(
                media_id=media_id,
                has_stored_results=True,
                stored_result=stored_result,
                live_session=None,
            )
        else:
            # No stored results, trigger live processing
            logger.info(
                f"No stored faces for media {media_id}, triggering live processing"
            )

            # Create face detection request
            request = FaceDetectionRequest(
                media_id=media_id,
                method="two_stage",
                confidence_threshold=0.3,
                frames_per_second=1,
                save_results=True,
            )

            # Trigger processing through self-referencing
            session = await session_manager.trigger_orchestrator_processing(request)

            return MediaFaceDetectionResponse(
                media_id=media_id,
                has_stored_results=False,
                stored_result=None,
                live_session=session,
            )

    except Exception as e:
        logger.error(f"Error processing media face detection for {media_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Face detection error: {str(e)}")


@face_detection_router.get("/media/{media_id}/faces/enhanced-v2")
async def get_media_face_detection_enhanced_v2(
    media_id: str,
    auth_token: str = Depends(get_auth_token),
    frame_interval: int = Query(10, description="Process every N frames (default: 10)"),
):
    """
    Enhanced Logic V2: Session-based face detection with frame sampling.

    This endpoint implements the new session-based workflow:
    1. Create session UUID for this processing
    2. Check for stored faces first (fast path)
    3. If no stored faces → trigger real-time detection with frame sampling
    4. Return unified response with session information

    Args:
        media_id: UUID of the media to process
        frame_interval: Process every N frames (default: 10 = 10x faster)

    This is the recommended endpoint for new Flutter integrations.
    """
    try:
        logger.info(
            f"Enhanced Logic V2 requested for media: {media_id}, "
            f"frame_interval: {frame_interval}"
        )

        # Use Enhanced Logic V2 session-based processing with frame sampling
        result = await session_manager.enhanced_logic_v2_session_based(
            media_id, auth_token, frame_interval
        )

        # Return the Enhanced Logic V2 result directly
        return result

    except Exception as e:
        logger.error(f"Enhanced Logic V2 error for media {media_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Enhanced Logic V2 error: {str(e)}"
        )


@face_detection_router.delete("/sessions/{session_id}")
async def cancel_face_detection_session(
    session_id: str, auth_token: str = Depends(get_auth_token)
):
    """Cancel a face detection session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status in [
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    ]:
        raise HTTPException(status_code=400, detail="Session already finished")

    session.status = SessionStatus.CANCELLED
    session.completed_at = datetime.now(timezone.utc)

    return {"message": "Session cancelled", "session_id": session_id}


# ============================================================================
# HEALTH CHECK
# ============================================================================


@face_detection_router.get("/face-detection/health")
async def face_detection_health():
    """Health check for face detection service."""
    return {
        "status": "healthy",
        "service": "face-detection",
        "active_sessions": len(
            [
                s
                for s in session_manager.sessions.values()
                if s.status == SessionStatus.RUNNING
            ]
        ),
        "total_sessions": len(session_manager.sessions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

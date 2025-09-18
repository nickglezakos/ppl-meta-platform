"""
PPL Meta Vision Service - Session Manager
Handles session lifecycle operations for Workflow 4 session-based face detection

This module provides session management functionality including:
- Session creation and initialization
- Session status tracking and updates
- Session completion and cleanup
- Session querying and retrieval
- Integration with face detection pipeline
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import psycopg2
import psycopg2.extras
from api_models import (
    FaceDetectionSessionModel,
    FaceDetectionSessionRequest,
    MediaProcessingStatusModel,
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionErrorResponse,
    SessionQueryRequest,
    SessionQueryResponse,
    SessionStartResponse,
    SessionStatusResponse,
)
from database import VisionDatabase

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages face detection sessions for the Vision Service."""

    def __init__(self, database: VisionDatabase):
        """Initialize session manager with database connection."""
        self.db = database
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def _generate_session_uuid(self) -> str:
        """Generate a unique session UUID."""
        return str(uuid.uuid4())

    def _get_current_timestamp(self) -> datetime:
        """Get current timestamp in UTC."""
        return datetime.now(timezone.utc)

    def _validate_session_uuid(self, session_uuid: str) -> bool:
        """Validate session UUID format."""
        try:
            uuid.UUID(session_uuid)
            return True
        except ValueError:
            return False

    async def create_session(
        self, request: FaceDetectionSessionRequest
    ) -> Union[SessionStartResponse, SessionErrorResponse]:
        """
        Create a new face detection session.

        Args:
            request: Session creation request parameters

        Returns:
            SessionStartResponse on success, SessionErrorResponse on failure
        """
        try:
            # Generate session UUID
            session_uuid = self._generate_session_uuid()
            current_time = self._get_current_timestamp()

            # Validate request parameters
            if not request.media_uuid:
                return SessionErrorResponse(
                    error="INVALID_REQUEST",
                    message="media_uuid is required",
                    details={"field": "media_uuid"},
                )

            if request.session_type not in ["streaming", "upload", "batch"]:
                return SessionErrorResponse(
                    error="INVALID_SESSION_TYPE",
                    message=f"Invalid session_type: {request.session_type}",
                    details={"valid_types": ["streaming", "upload", "batch"]},
                )

            # Prepare session data
            session_data = {
                "session_uuid": session_uuid,
                "media_uuid": request.media_uuid,
                "camera_device_uuid": request.camera_device_uuid,
                "session_type": request.session_type,
                "started_at": current_time,
                "processing_status": "initializing",
                "total_faces_detected": 0,
                "metadata": request.metadata or {},
            }

            # Store session in database
            if self.db and self.db.connection:
                try:
                    with self.db.connection.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO face_detection_sessions 
                            (session_uuid, media_uuid, camera_device_uuid, session_type, 
                             started_at, processing_status, total_faces_detected, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                            (
                                session_uuid,
                                request.media_uuid,
                                request.camera_device_uuid,
                                request.session_type,
                                current_time,
                                "active",
                                0,
                                json.dumps(request.metadata or {}),
                            ),
                        )

                        # Also create media processing status record
                        cursor.execute(
                            """
                            INSERT INTO media_processing_status 
                            (media_uuid, face_detection_processed, face_detection_session_uuid,
                             total_frames_processed, total_faces_detected, processing_method)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (media_uuid) DO UPDATE SET
                                face_detection_session_uuid = EXCLUDED.face_detection_session_uuid,
                                processing_method = EXCLUDED.processing_method,
                                last_updated = CURRENT_TIMESTAMP
                        """,
                            (
                                request.media_uuid,
                                False,  # Not processed yet
                                session_uuid,
                                0,
                                0,
                                f"session_{request.session_type}",
                            ),
                        )

                    logger.info(
                        f"Created session {session_uuid} for media {request.media_uuid}"
                    )

                except Exception as e:
                    logger.error(f"Database error creating session: {e}")
                    return SessionErrorResponse(
                        error="DATABASE_ERROR",
                        message="Failed to create session in database",
                        details={"error": str(e)},
                    )

            # Store in memory for quick access
            self.active_sessions[session_uuid] = session_data

            # Create response
            session_model = FaceDetectionSessionModel(
                session_uuid=session_uuid,
                media_uuid=request.media_uuid,
                camera_device_uuid=request.camera_device_uuid,
                session_type=request.session_type,
                started_at=current_time,
                processing_status="active",
                total_faces_detected=0,
                metadata=request.metadata or {},
            )

            return SessionStartResponse(
                session=session_model, message="Session created successfully"
            )

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return SessionErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to create session",
                details={"error": str(e)},
            )

    async def get_session_status(
        self, session_uuid: str
    ) -> Union[SessionStatusResponse, SessionErrorResponse]:
        """
        Get the current status of a face detection session.

        Args:
            session_uuid: UUID of the session to query

        Returns:
            SessionStatusResponse on success, SessionErrorResponse on failure
        """
        try:
            # Validate session UUID
            if not self._validate_session_uuid(session_uuid):
                return SessionErrorResponse(
                    error="INVALID_SESSION_UUID",
                    message="Invalid session UUID format",
                    details={"session_uuid": session_uuid},
                )

            # Try to get from memory first
            if session_uuid in self.active_sessions:
                session_data = self.active_sessions[session_uuid]

                # Update with latest database data
                if self.db and self.db.connection:
                    try:
                        with self.db.connection.cursor(
                            cursor_factory=psycopg2.extras.RealDictCursor
                        ) as cursor:
                            cursor.execute(
                                """
                                SELECT 
                                    s.*,
                                    COUNT(f.id) as current_face_count
                                FROM face_detection_sessions s
                                LEFT JOIN face_detections f
                                    ON s.media_uuid = f.media_id
                                WHERE s.session_uuid = %s
                                GROUP BY s.session_uuid
                            """,
                                (session_uuid,),
                            )

                            result = cursor.fetchone()
                            if result:
                                session_data.update(dict(result))
                                session_data["total_faces_detected"] = (
                                    result["current_face_count"] or 0
                                )

                    except Exception as e:
                        logger.warning(f"Could not update session from database: {e}")

                # Create session model
                session_model = FaceDetectionSessionModel(
                    session_uuid=session_data["session_uuid"],
                    media_uuid=session_data["media_uuid"],
                    camera_device_uuid=session_data.get("camera_device_uuid"),
                    session_type=session_data["session_type"],
                    started_at=session_data["started_at"],
                    ended_at=session_data.get("ended_at"),
                    processing_status=session_data.get("processing_status", "unknown"),
                    total_faces_detected=session_data.get("total_faces_detected", 0),
                    metadata=session_data.get("metadata", {}),
                )

                return SessionStatusResponse(
                    session=session_model,
                    processing_stats={
                        "total_faces_detected": session_data.get(
                            "total_faces_detected", 0
                        ),
                        "processing_status": session_data.get(
                            "processing_status", "unknown"
                        ),
                        "session_duration_seconds": (
                            (
                                (
                                    session_data.get("ended_at")
                                    or self._get_current_timestamp()
                                )
                                - session_data["started_at"]
                            ).total_seconds()
                            if session_data.get("started_at")
                            else 0
                        ),
                    },
                )

            # If not in memory, try database
            if self.db and self.db.connection:
                try:
                    with self.db.connection.cursor(
                        cursor_factory=psycopg2.extras.RealDictCursor
                    ) as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                s.*,
                                COUNT(f.id) as current_face_count
                            FROM face_detection_sessions s
                            LEFT JOIN face_detections f
                                ON s.media_uuid = f.media_id
                            WHERE s.session_uuid = %s
                            GROUP BY s.session_uuid
                        """,
                            (session_uuid,),
                        )

                        result = cursor.fetchone()
                        if result:
                            session_data = dict(result)

                            # Parse metadata if it's a string
                            if isinstance(session_data.get("metadata"), str):
                                try:
                                    session_data["metadata"] = json.loads(
                                        session_data["metadata"]
                                    )
                                except json.JSONDecodeError:
                                    session_data["metadata"] = {}

                            session_model = FaceDetectionSessionModel(
                                session_uuid=session_data["session_uuid"],
                                media_uuid=session_data["media_uuid"],
                                camera_device_uuid=session_data.get(
                                    "camera_device_uuid"
                                ),
                                session_type=session_data["session_type"],
                                started_at=session_data["started_at"],
                                ended_at=session_data.get("ended_at"),
                                processing_status=session_data.get(
                                    "processing_status", "unknown"
                                ),
                                total_faces_detected=session_data.get(
                                    "current_face_count", 0
                                ),
                                metadata=session_data.get("metadata", {}),
                            )

                            return SessionStatusResponse(
                                session=session_model,
                                processing_stats={
                                    "total_faces_detected": session_data.get(
                                        "current_face_count", 0
                                    ),
                                    "processing_status": session_data.get(
                                        "processing_status", "unknown"
                                    ),
                                    "session_duration_seconds": (
                                        (
                                            (
                                                session_data.get("ended_at")
                                                or self._get_current_timestamp()
                                            )
                                            - session_data["started_at"]
                                        ).total_seconds()
                                        if session_data.get("started_at")
                                        else 0
                                    ),
                                },
                            )
                        else:
                            return SessionErrorResponse(
                                error="SESSION_NOT_FOUND",
                                message=f"Session {session_uuid} not found",
                                details={"session_uuid": session_uuid},
                            )

                except Exception as e:
                    logger.error(f"Database error querying session: {e}")
                    return SessionErrorResponse(
                        error="DATABASE_ERROR",
                        message="Failed to query session from database",
                        details={"error": str(e)},
                    )

            return SessionErrorResponse(
                error="SESSION_NOT_FOUND",
                message=f"Session {session_uuid} not found",
                details={"session_uuid": session_uuid},
            )

        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return SessionErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to get session status",
                details={"error": str(e)},
            )

    async def complete_session(
        self, session_uuid: str, request: SessionCompleteRequest
    ) -> Union[SessionCompleteResponse, SessionErrorResponse]:
        """
        Complete a face detection session.

        Args:
            session_uuid: UUID of the session to complete
            request: Session completion parameters

        Returns:
            SessionCompleteResponse on success, SessionErrorResponse on failure
        """
        try:
            # Validate session UUID
            if not self._validate_session_uuid(session_uuid):
                return SessionErrorResponse(
                    error="INVALID_SESSION_UUID",
                    message="Invalid session UUID format",
                    details={"session_uuid": session_uuid},
                )

            current_time = self._get_current_timestamp()

            # Get current session status first
            session_status = await self.get_session_status(session_uuid)
            if isinstance(session_status, SessionErrorResponse):
                return session_status

            current_session = session_status.session

            # Update session in database
            if self.db and self.db.connection:
                try:
                    with self.db.connection.cursor() as cursor:
                        # Update session end time and status
                        cursor.execute(
                            """
                            UPDATE face_detection_sessions 
                            SET 
                                ended_at = %s,
                                processing_status = %s,
                                total_faces_detected = (
                                    SELECT COUNT(*)::integer 
                                    FROM face_detections 
                                    WHERE session_uuid = %s
                                ),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE session_uuid = %s
                        """,
                            (current_time, "completed", session_uuid, session_uuid),
                        )

                        # Update media processing status
                        cursor.execute(
                            """
                            UPDATE media_processing_status 
                            SET 
                                face_detection_processed = %s,
                                processing_completed_at = %s,
                                total_faces_detected = (
                                    SELECT COUNT(*)::integer 
                                    FROM face_detections 
                                    WHERE session_uuid = %s
                                ),
                                last_updated = CURRENT_TIMESTAMP
                            WHERE face_detection_session_uuid = %s
                        """,
                            (True, current_time, session_uuid, session_uuid),
                        )

                        # Get final session stats
                        cursor.execute(
                            """
                            SELECT 
                                COUNT(*) as total_faces,
                                COUNT(DISTINCT frame_number) as total_frames
                            FROM face_detections 
                            WHERE session_uuid = %s
                        """,
                            (session_uuid,),
                        )

                        stats_result = cursor.fetchone()
                        total_faces = stats_result[0] if stats_result else 0
                        total_frames = stats_result[1] if stats_result else 0

                    logger.info(
                        f"Completed session {session_uuid} with {total_faces} faces detected"
                    )

                except Exception as e:
                    logger.error(f"Database error completing session: {e}")
                    return SessionErrorResponse(
                        error="DATABASE_ERROR",
                        message="Failed to complete session in database",
                        details={"error": str(e)},
                    )
            else:
                # Fallback if no database
                total_faces = 0
                total_frames = 0

            # Update memory cache
            if session_uuid in self.active_sessions:
                self.active_sessions[session_uuid].update(
                    {
                        "ended_at": current_time,
                        "processing_status": "completed",
                        "total_faces_detected": total_faces,
                    }
                )

            # Create final session summary
            session_duration = (
                current_time - current_session.started_at
            ).total_seconds()

            return SessionCompleteResponse(
                session_uuid=session_uuid,
                status="completed",
                session_summary={
                    "total_faces_detected": total_faces,
                    "total_frames_processed": total_frames,
                    "session_duration_seconds": session_duration,
                    "processing_rate_fps": (
                        total_frames / session_duration if session_duration > 0 else 0
                    ),
                    "faces_per_frame": (
                        total_faces / total_frames if total_frames > 0 else 0
                    ),
                },
                completion_timestamp=current_time,
                message="Session completed successfully",
            )

        except Exception as e:
            logger.error(f"Error completing session: {e}")
            return SessionErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to complete session",
                details={"error": str(e)},
            )

    async def update_session_face_count(
        self, session_uuid: str, face_count_increment: int = 1
    ) -> bool:
        """
        Update the face count for a session.

        Args:
            session_uuid: UUID of the session
            face_count_increment: Number of faces to add to the count

        Returns:
            True on success, False on failure
        """
        try:
            # Update memory cache
            if session_uuid in self.active_sessions:
                current_count = self.active_sessions[session_uuid].get(
                    "total_faces_detected", 0
                )
                self.active_sessions[session_uuid]["total_faces_detected"] = (
                    current_count + face_count_increment
                )

            # Update database
            if self.db and self.db.connection:
                try:
                    with self.db.connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE face_detection_sessions 
                            SET 
                                total_faces_detected = (
                                    SELECT COUNT(*)::integer 
                                    FROM face_detections 
                                    WHERE session_uuid = %s
                                ),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE session_uuid = %s
                        """,
                            (session_uuid, session_uuid),
                        )

                        # Also update media processing status
                        cursor.execute(
                            """
                            UPDATE media_processing_status 
                            SET 
                                total_faces_detected = (
                                    SELECT COUNT(*)::integer 
                                    FROM face_detections 
                                    WHERE session_uuid = %s
                                ),
                                last_updated = CURRENT_TIMESTAMP
                            WHERE face_detection_session_uuid = %s
                        """,
                            (session_uuid, session_uuid),
                        )

                except Exception as e:
                    logger.error(f"Database error updating face count: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error updating session face count: {e}")
            return False

    async def query_sessions(
        self, request: SessionQueryRequest
    ) -> Union[SessionQueryResponse, SessionErrorResponse]:
        """
        Query sessions based on various criteria.

        Args:
            request: Session query parameters

        Returns:
            SessionQueryResponse on success, SessionErrorResponse on failure
        """
        try:
            sessions = []

            if self.db and self.db.connection:
                try:
                    with self.db.connection.cursor(
                        cursor_factory=psycopg2.extras.RealDictCursor
                    ) as cursor:
                        # Build query based on filters
                        where_conditions = []
                        params = []

                        if request.media_uuid:
                            where_conditions.append("s.media_uuid = %s")
                            params.append(request.media_uuid)

                        if request.camera_device_uuid:
                            where_conditions.append("s.camera_device_uuid = %s")
                            params.append(request.camera_device_uuid)

                        if request.session_type:
                            where_conditions.append("s.session_type = %s")
                            params.append(request.session_type)

                        if request.processing_status:
                            where_conditions.append("s.processing_status = %s")
                            params.append(request.processing_status)

                        if hasattr(request, "started_after") and request.started_after:
                            where_conditions.append("s.started_at >= %s")
                            params.append(request.started_after)

                        if (
                            hasattr(request, "started_before")
                            and request.started_before
                        ):
                            where_conditions.append("s.started_at <= %s")
                            params.append(request.started_before)

                        # Build final query
                        where_clause = (
                            "WHERE " + " AND ".join(where_conditions)
                            if where_conditions
                            else ""
                        )

                        query = f"""
                            SELECT 
                                s.*,
                                COUNT(f.id) as total_faces_detected
                            FROM face_detection_sessions s
                            LEFT JOIN face_detections f
                                ON s.media_uuid = f.media_id
                            {where_clause}
                            GROUP BY s.session_uuid
                            ORDER BY s.started_at DESC
                            LIMIT %s OFFSET %s
                        """

                        params.extend([request.limit or 50, request.offset or 0])

                        cursor.execute(query, params)
                        results = cursor.fetchall()

                        for result in results:
                            session_data = dict(result)

                            # Parse metadata if it's a string
                            if isinstance(session_data.get("metadata"), str):
                                try:
                                    session_data["metadata"] = json.loads(
                                        session_data["metadata"]
                                    )
                                except json.JSONDecodeError:
                                    session_data["metadata"] = {}

                            session_model = FaceDetectionSessionModel(
                                session_uuid=session_data["session_uuid"],
                                media_uuid=session_data["media_uuid"],
                                camera_device_uuid=session_data.get(
                                    "camera_device_uuid"
                                ),
                                session_type=session_data["session_type"],
                                started_at=session_data["started_at"],
                                ended_at=session_data.get("ended_at"),
                                processing_status=session_data.get(
                                    "processing_status", "unknown"
                                ),
                                total_faces_detected=session_data.get(
                                    "total_faces_detected", 0
                                ),
                                metadata=session_data.get("metadata", {}),
                            )

                            sessions.append(session_model)

                except Exception as e:
                    logger.error(f"Database error querying sessions: {e}")
                    return SessionErrorResponse(
                        error="DATABASE_ERROR",
                        message="Failed to query sessions from database",
                        details={"error": str(e)},
                    )

            return SessionQueryResponse(
                success=True,
                sessions=sessions,
                total_count=len(sessions),
                limit=request.limit or 50,
                offset=request.offset or 0,
            )

        except Exception as e:
            logger.error(f"Error querying sessions: {e}")
            return SessionErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to query sessions",
                details={"error": str(e)},
            )

    def get_active_session_count(self) -> int:
        """Get the number of currently active sessions."""
        return len(
            [
                s
                for s in self.active_sessions.values()
                if s.get("processing_status") in ["active", "processing"]
            ]
        )

    def cleanup_completed_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed sessions from memory cache.

        Args:
            max_age_hours: Maximum age in hours for completed sessions

        Returns:
            Number of sessions cleaned up
        """
        try:
            current_time = self._get_current_timestamp()
            cleaned_count = 0

            sessions_to_remove = []
            for session_uuid, session_data in self.active_sessions.items():
                if session_data.get(
                    "processing_status"
                ) == "completed" and session_data.get("ended_at"):

                    age_hours = (
                        current_time - session_data["ended_at"]
                    ).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        sessions_to_remove.append(session_uuid)

            for session_uuid in sessions_to_remove:
                del self.active_sessions[session_uuid]
                cleaned_count += 1

            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} old completed sessions from memory cache"
                )

            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0


# Global session manager instance
session_manager: Optional[SessionManager] = None


def initialize_session_manager(database: VisionDatabase) -> SessionManager:
    """Initialize the global session manager instance."""
    global session_manager
    session_manager = SessionManager(database)
    logger.info("Session manager initialized")
    return session_manager


def get_session_manager() -> Optional[SessionManager]:
    """Get the global session manager instance."""
    return session_manager

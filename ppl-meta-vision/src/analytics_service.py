"""
PPL Meta Vision Service - Advanced Analytics Service
Phase 5: Advanced Analytics & Traceability Features

This module provides comprehensive analytics capabilities for face detection
sessions, including cross-session analysis, device traceability, and
advanced querying functionality.
"""

# Import database.py file directly
import importlib.util
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

db_spec = importlib.util.spec_from_file_location(
    "database", os.path.join(os.path.dirname(__file__), "database.py")
)
db_module = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db_module)
VisionDatabase = db_module.VisionDatabase

logger = logging.getLogger(__name__)


class AdvancedAnalyticsService:
    """
    Advanced analytics service for cross-session face detection analysis.

    Provides comprehensive insights including:
    - Cross-session analytics and trends
    - Device-specific traceability
    - Media timeline analysis
    - Performance monitoring
    - Advanced querying capabilities
    """

    def __init__(self, database: VisionDatabase):
        """Initialize analytics service with database connection."""
        self.db = database

    # ========================================================================
    # Cross-Session Analytics
    # ========================================================================

    async def get_cross_session_analytics(
        self,
        time_range_hours: Optional[int] = 24,
        session_type: Optional[str] = None,
        camera_device_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive cross-session analytics.

        Args:
            time_range_hours: Time range for analysis (default: 24 hours)
            session_type: Filter by session type ('streaming', 'bulk_processing')
            camera_device_uuid: Filter by specific camera device

        Returns:
            Comprehensive analytics across multiple sessions
        """
        try:
            if not self.db or not self.db.connection:
                raise Exception("Database connection not available")

            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=time_range_hours)

            with self.db.connection.cursor() as cursor:
                # Build base query with filters
                base_conditions = ["s.started_at >= %s", "s.started_at <= %s"]
                params = [start_time, end_time]

                if session_type:
                    base_conditions.append("s.session_type = %s")
                    params.append(session_type)

                if camera_device_uuid:
                    base_conditions.append("s.camera_device_uuid = %s")
                    params.append(camera_device_uuid)

                where_clause = " AND ".join(base_conditions)

                # 1. Session Overview Statistics
                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(CASE WHEN s.processing_status = 'active' THEN 1 END) as active_sessions,
                        COUNT(CASE WHEN s.processing_status = 'completed' THEN 1 END) as completed_sessions,
                        COUNT(CASE WHEN s.processing_status = 'failed' THEN 1 END) as failed_sessions,
                        SUM(s.total_faces_detected) as total_faces_detected,
                        AVG(s.total_faces_detected) as avg_faces_per_session,
                        COUNT(DISTINCT s.media_uuid) as unique_media_files,
                        COUNT(DISTINCT s.camera_device_uuid) as unique_cameras
                    FROM face_detection_sessions s
                    WHERE {where_clause}
                """,
                    params,
                )

                session_stats = cursor.fetchone()

                # 2. Detection Trends by Hour
                cursor.execute(
                    f"""
                    SELECT 
                        DATE_TRUNC('hour', s.started_at) as hour,
                        COUNT(*) as sessions_count,
                        SUM(s.total_faces_detected) as faces_detected,
                        AVG(s.total_faces_detected) as avg_faces
                    FROM face_detection_sessions s
                    WHERE {where_clause}
                    GROUP BY DATE_TRUNC('hour', s.started_at)
                    ORDER BY hour
                """,
                    params,
                )

                hourly_trends = cursor.fetchall()

                # 3. Camera Performance Analysis
                cursor.execute(
                    f"""
                    SELECT 
                        s.camera_device_uuid,
                        COUNT(*) as session_count,
                        SUM(s.total_faces_detected) as total_faces,
                        AVG(s.total_faces_detected) as avg_faces_per_session,
                        COUNT(CASE WHEN s.processing_status = 'completed' THEN 1 END) as successful_sessions,
                        COUNT(CASE WHEN s.processing_status = 'failed' THEN 1 END) as failed_sessions
                    FROM face_detection_sessions s
                    WHERE {where_clause} AND s.camera_device_uuid IS NOT NULL
                    GROUP BY s.camera_device_uuid
                    ORDER BY total_faces DESC
                """,
                    params,
                )

                camera_performance = cursor.fetchall()

                # 4. Session Type Distribution
                cursor.execute(
                    f"""
                    SELECT 
                        s.session_type,
                        COUNT(*) as count,
                        SUM(s.total_faces_detected) as total_faces,
                        AVG(s.total_faces_detected) as avg_faces
                    FROM face_detection_sessions s
                    WHERE {where_clause}
                    GROUP BY s.session_type
                """,
                    params,
                )

                session_type_dist = cursor.fetchall()

                # 5. Processing Success Rate
                cursor.execute(
                    f"""
                    SELECT 
                        processing_status,
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                    FROM face_detection_sessions s
                    WHERE {where_clause}
                    GROUP BY processing_status
                """,
                    params,
                )

                success_rates = cursor.fetchall()

                # 6. Average Session Duration (for completed sessions)
                cursor.execute(
                    f"""
                    SELECT 
                        AVG(EXTRACT(EPOCH FROM (s.ended_at - s.started_at))) as avg_duration_seconds,
                        MIN(EXTRACT(EPOCH FROM (s.ended_at - s.started_at))) as min_duration_seconds,
                        MAX(EXTRACT(EPOCH FROM (s.ended_at - s.started_at))) as max_duration_seconds
                    FROM face_detection_sessions s
                    WHERE {where_clause} AND s.ended_at IS NOT NULL
                """,
                    params,
                )

                duration_stats = cursor.fetchone()

                # Format results
                analytics = {
                    "time_range": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "hours": time_range_hours,
                    },
                    "session_overview": {
                        "total_sessions": session_stats[0] if session_stats[0] else 0,
                        "active_sessions": session_stats[1] if session_stats[1] else 0,
                        "completed_sessions": (
                            session_stats[2] if session_stats[2] else 0
                        ),
                        "failed_sessions": session_stats[3] if session_stats[3] else 0,
                        "total_faces_detected": (
                            session_stats[4] if session_stats[4] else 0
                        ),
                        "avg_faces_per_session": (
                            float(session_stats[5]) if session_stats[5] else 0.0
                        ),
                        "unique_media_files": (
                            session_stats[6] if session_stats[6] else 0
                        ),
                        "unique_cameras": session_stats[7] if session_stats[7] else 0,
                    },
                    "detection_trends": [
                        {
                            "hour": trend[0].isoformat() if trend[0] else None,
                            "sessions_count": trend[1],
                            "faces_detected": trend[2],
                            "avg_faces": float(trend[3]) if trend[3] else 0.0,
                        }
                        for trend in hourly_trends
                    ],
                    "camera_performance": [
                        {
                            "camera_device_uuid": perf[0],
                            "session_count": perf[1],
                            "total_faces": perf[2],
                            "avg_faces_per_session": float(perf[3]) if perf[3] else 0.0,
                            "successful_sessions": perf[4],
                            "failed_sessions": perf[5],
                            "success_rate": (
                                (perf[4] / perf[1] * 100) if perf[1] > 0 else 0.0
                            ),
                        }
                        for perf in camera_performance
                    ],
                    "session_type_distribution": [
                        {
                            "session_type": dist[0],
                            "count": dist[1],
                            "total_faces": dist[2],
                            "avg_faces": float(dist[3]) if dist[3] else 0.0,
                        }
                        for dist in session_type_dist
                    ],
                    "processing_success_rates": [
                        {
                            "status": rate[0],
                            "count": rate[1],
                            "percentage": float(rate[2]) if rate[2] else 0.0,
                        }
                        for rate in success_rates
                    ],
                    "session_duration_stats": (
                        {
                            "avg_duration_seconds": (
                                float(duration_stats[0])
                                if duration_stats and duration_stats[0]
                                else 0.0
                            ),
                            "min_duration_seconds": (
                                float(duration_stats[1])
                                if duration_stats and duration_stats[1]
                                else 0.0
                            ),
                            "max_duration_seconds": (
                                float(duration_stats[2])
                                if duration_stats and duration_stats[2]
                                else 0.0
                            ),
                        }
                        if duration_stats
                        else None
                    ),
                    "filters_applied": {
                        "session_type": session_type,
                        "camera_device_uuid": camera_device_uuid,
                    },
                }

                logger.info(
                    f"Generated cross-session analytics for {analytics['session_overview']['total_sessions']} sessions"
                )
                return analytics

        except Exception as e:
            logger.error(f"Error generating cross-session analytics: {e}")
            raise

    # ========================================================================
    # Device Traceability
    # ========================================================================

    async def get_device_traceability(
        self, camera_device_uuid: str, time_range_days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive traceability for a specific camera device.

        Args:
            camera_device_uuid: UUID of the camera device
            time_range_days: Time range for analysis (default: 30 days)

        Returns:
            Complete traceability data for the device
        """
        try:
            if not self.db or not self.db.connection:
                raise Exception("Database connection not available")

            # Validate UUID format
            try:
                uuid.UUID(camera_device_uuid)
            except ValueError:
                raise Exception(
                    f"Invalid camera device UUID format: {camera_device_uuid}"
                )

            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=time_range_days)

            with self.db.connection.cursor() as cursor:
                # 1. Device Session Overview
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(total_faces_detected) as total_faces_detected,
                        AVG(total_faces_detected) as avg_faces_per_session,
                        COUNT(DISTINCT media_uuid) as unique_media_files,
                        MIN(started_at) as first_session,
                        MAX(started_at) as latest_session,
                        COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as successful_sessions,
                        COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_sessions
                    FROM face_detection_sessions 
                    WHERE camera_device_uuid = %s 
                    AND started_at >= %s AND started_at <= %s
                """,
                    (camera_device_uuid, start_time, end_time),
                )

                device_overview = cursor.fetchone()

                # 2. Session History with Details
                cursor.execute(
                    """
                    SELECT 
                        session_uuid,
                        media_uuid,
                        session_type,
                        started_at,
                        ended_at,
                        total_faces_detected,
                        processing_status,
                        metadata
                    FROM face_detection_sessions 
                    WHERE camera_device_uuid = %s 
                    AND started_at >= %s AND started_at <= %s
                    ORDER BY started_at DESC
                """,
                    (camera_device_uuid, start_time, end_time),
                )

                session_history = cursor.fetchall()

                # 3. Daily Activity Pattern
                cursor.execute(
                    """
                    SELECT 
                        DATE(started_at) as date,
                        COUNT(*) as sessions_count,
                        SUM(total_faces_detected) as faces_detected,
                        AVG(total_faces_detected) as avg_faces
                    FROM face_detection_sessions 
                    WHERE camera_device_uuid = %s 
                    AND started_at >= %s AND started_at <= %s
                    GROUP BY DATE(started_at)
                    ORDER BY date DESC
                """,
                    (camera_device_uuid, start_time, end_time),
                )

                daily_activity = cursor.fetchall()

                # 4. Hourly Usage Patterns
                cursor.execute(
                    """
                    SELECT 
                        EXTRACT(HOUR FROM started_at) as hour,
                        COUNT(*) as sessions_count,
                        AVG(total_faces_detected) as avg_faces
                    FROM face_detection_sessions 
                    WHERE camera_device_uuid = %s 
                    AND started_at >= %s AND started_at <= %s
                    GROUP BY EXTRACT(HOUR FROM started_at)
                    ORDER BY hour
                """,
                    (camera_device_uuid, start_time, end_time),
                )

                hourly_patterns = cursor.fetchall()

                # 5. Face Detection Quality Metrics
                cursor.execute(
                    """
                    SELECT 
                        AVG(fd.confidence) as avg_confidence,
                        MIN(fd.confidence) as min_confidence,
                        MAX(fd.confidence) as max_confidence,
                        COUNT(*) as total_detections,
                        COUNT(DISTINCT fd.method) as detection_methods_used
                    FROM face_detections fd
                    JOIN face_detection_sessions fds ON fd.session_uuid = fds.session_uuid
                    WHERE fds.camera_device_uuid = %s 
                    AND fds.started_at >= %s AND fds.started_at <= %s
                """,
                    (camera_device_uuid, start_time, end_time),
                )

                quality_metrics = cursor.fetchone()

                # 6. Detection Methods Distribution
                cursor.execute(
                    """
                    SELECT 
                        fd.method,
                        COUNT(*) as count,
                        AVG(fd.confidence) as avg_confidence
                    FROM face_detections fd
                    JOIN face_detection_sessions fds ON fd.session_uuid = fds.session_uuid
                    WHERE fds.camera_device_uuid = %s 
                    AND fds.started_at >= %s AND fds.started_at <= %s
                    GROUP BY fd.method
                    ORDER BY count DESC
                """,
                    (camera_device_uuid, start_time, end_time),
                )

                method_distribution = cursor.fetchall()

                # Format results
                traceability = {
                    "camera_device_uuid": camera_device_uuid,
                    "analysis_period": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "days": time_range_days,
                    },
                    "device_overview": {
                        "total_sessions": (
                            device_overview[0] if device_overview[0] else 0
                        ),
                        "total_faces_detected": (
                            device_overview[1] if device_overview[1] else 0
                        ),
                        "avg_faces_per_session": (
                            float(device_overview[2]) if device_overview[2] else 0.0
                        ),
                        "unique_media_files": (
                            device_overview[3] if device_overview[3] else 0
                        ),
                        "first_session": (
                            device_overview[4].isoformat()
                            if device_overview[4]
                            else None
                        ),
                        "latest_session": (
                            device_overview[5].isoformat()
                            if device_overview[5]
                            else None
                        ),
                        "successful_sessions": (
                            device_overview[6] if device_overview[6] else 0
                        ),
                        "failed_sessions": (
                            device_overview[7] if device_overview[7] else 0
                        ),
                        "success_rate": (
                            (device_overview[6] / device_overview[0] * 100)
                            if device_overview[0] and device_overview[0] > 0
                            else 0.0
                        ),
                    },
                    "session_history": [
                        {
                            "session_uuid": session[0],
                            "media_uuid": session[1],
                            "session_type": session[2],
                            "started_at": (
                                session[3].isoformat() if session[3] else None
                            ),
                            "ended_at": session[4].isoformat() if session[4] else None,
                            "total_faces_detected": session[5],
                            "processing_status": session[6],
                            "metadata": session[7],
                        }
                        for session in session_history
                    ],
                    "daily_activity": [
                        {
                            "date": activity[0].isoformat() if activity[0] else None,
                            "sessions_count": activity[1],
                            "faces_detected": activity[2],
                            "avg_faces": float(activity[3]) if activity[3] else 0.0,
                        }
                        for activity in daily_activity
                    ],
                    "hourly_patterns": [
                        {
                            "hour": int(pattern[0]) if pattern[0] is not None else 0,
                            "sessions_count": pattern[1],
                            "avg_faces": float(pattern[2]) if pattern[2] else 0.0,
                        }
                        for pattern in hourly_patterns
                    ],
                    "quality_metrics": (
                        {
                            "avg_confidence": (
                                float(quality_metrics[0])
                                if quality_metrics and quality_metrics[0]
                                else 0.0
                            ),
                            "min_confidence": (
                                float(quality_metrics[1])
                                if quality_metrics and quality_metrics[1]
                                else 0.0
                            ),
                            "max_confidence": (
                                float(quality_metrics[2])
                                if quality_metrics and quality_metrics[2]
                                else 0.0
                            ),
                            "total_detections": (
                                quality_metrics[3]
                                if quality_metrics and quality_metrics[3]
                                else 0
                            ),
                            "detection_methods_used": (
                                quality_metrics[4]
                                if quality_metrics and quality_metrics[4]
                                else 0
                            ),
                        }
                        if quality_metrics
                        else None
                    ),
                    "detection_methods": [
                        {
                            "method": method[0],
                            "count": method[1],
                            "avg_confidence": float(method[2]) if method[2] else 0.0,
                        }
                        for method in method_distribution
                    ],
                }

                logger.info(
                    f"Generated device traceability for {camera_device_uuid}: {traceability['device_overview']['total_sessions']} sessions"
                )
                return traceability

        except Exception as e:
            logger.error(f"Error generating device traceability: {e}")
            raise

    # ========================================================================
    # Media Timeline Analytics
    # ========================================================================

    async def get_media_timeline_analytics(self, media_uuid: str) -> Dict[str, Any]:
        """
        Get comprehensive timeline analytics for a specific media file.

        Args:
            media_uuid: UUID of the media file

        Returns:
            Complete timeline analysis for the media
        """
        try:
            if not self.db or not self.db.connection:
                raise Exception("Database connection not available")

            # Validate UUID format
            try:
                uuid.UUID(media_uuid)
            except ValueError:
                raise Exception(f"Invalid media UUID format: {media_uuid}")

            with self.db.connection.cursor() as cursor:
                # 1. Media Processing Overview
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(total_faces_detected) as total_faces_detected,
                        COUNT(DISTINCT camera_device_uuid) as unique_cameras,
                        MIN(started_at) as first_processing,
                        MAX(started_at) as latest_processing,
                        COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as successful_sessions
                    FROM face_detection_sessions 
                    WHERE media_uuid = %s
                """,
                    (media_uuid,),
                )

                media_overview = cursor.fetchone()

                # 2. Session Timeline
                cursor.execute(
                    """
                    SELECT 
                        session_uuid,
                        camera_device_uuid,
                        session_type,
                        started_at,
                        ended_at,
                        total_faces_detected,
                        processing_status,
                        metadata
                    FROM face_detection_sessions 
                    WHERE media_uuid = %s
                    ORDER BY started_at
                """,
                    (media_uuid,),
                )

                session_timeline = cursor.fetchall()

                # 3. Processing Status Check
                cursor.execute(
                    """
                    SELECT 
                        face_detection_processed,
                        processing_completed_at,
                        total_frames_processed,
                        total_faces_detected,
                        processing_method
                    FROM media_processing_status 
                    WHERE media_uuid = %s
                """,
                    (media_uuid,),
                )

                processing_status = cursor.fetchone()

                # 4. Face Detection Distribution by Session
                cursor.execute(
                    """
                    SELECT 
                        fds.session_uuid,
                        fds.camera_device_uuid,
                        COUNT(fd.id) as detection_count,
                        AVG(fd.confidence) as avg_confidence,
                        MIN(fd.confidence) as min_confidence,
                        MAX(fd.confidence) as max_confidence
                    FROM face_detection_sessions fds
                    LEFT JOIN face_detections fd ON fds.session_uuid = fd.session_uuid
                    WHERE fds.media_uuid = %s
                    GROUP BY fds.session_uuid, fds.camera_device_uuid
                    ORDER BY fds.started_at
                """,
                    (media_uuid,),
                )

                detection_distribution = cursor.fetchall()

                # 5. Frame-by-Frame Analysis (if frame data available)
                cursor.execute(
                    """
                    SELECT 
                        fd.frame_number,
                        COUNT(*) as faces_in_frame,
                        AVG(fd.confidence) as avg_confidence,
                        fd.timestamp
                    FROM face_detections fd
                    JOIN face_detection_sessions fds ON fd.session_uuid = fds.session_uuid
                    WHERE fds.media_uuid = %s AND fd.frame_number IS NOT NULL
                    GROUP BY fd.frame_number, fd.timestamp
                    ORDER BY fd.frame_number
                """,
                    (media_uuid,),
                )

                frame_analysis = cursor.fetchall()

                # Format results
                timeline = {
                    "media_uuid": media_uuid,
                    "media_overview": {
                        "total_sessions": media_overview[0] if media_overview[0] else 0,
                        "total_faces_detected": (
                            media_overview[1] if media_overview[1] else 0
                        ),
                        "unique_cameras": media_overview[2] if media_overview[2] else 0,
                        "first_processing": (
                            media_overview[3].isoformat() if media_overview[3] else None
                        ),
                        "latest_processing": (
                            media_overview[4].isoformat() if media_overview[4] else None
                        ),
                        "successful_sessions": (
                            media_overview[5] if media_overview[5] else 0
                        ),
                    },
                    "session_timeline": [
                        {
                            "session_uuid": session[0],
                            "camera_device_uuid": session[1],
                            "session_type": session[2],
                            "started_at": (
                                session[3].isoformat() if session[3] else None
                            ),
                            "ended_at": session[4].isoformat() if session[4] else None,
                            "total_faces_detected": session[5],
                            "processing_status": session[6],
                            "metadata": session[7],
                        }
                        for session in session_timeline
                    ],
                    "processing_status": (
                        {
                            "face_detection_processed": (
                                processing_status[0] if processing_status else False
                            ),
                            "processing_completed_at": (
                                processing_status[1].isoformat()
                                if processing_status and processing_status[1]
                                else None
                            ),
                            "total_frames_processed": (
                                processing_status[2] if processing_status else None
                            ),
                            "total_faces_detected": (
                                processing_status[3] if processing_status else None
                            ),
                            "processing_method": (
                                processing_status[4] if processing_status else None
                            ),
                        }
                        if processing_status
                        else None
                    ),
                    "detection_distribution": [
                        {
                            "session_uuid": dist[0],
                            "camera_device_uuid": dist[1],
                            "detection_count": dist[2],
                            "avg_confidence": float(dist[3]) if dist[3] else 0.0,
                            "min_confidence": float(dist[4]) if dist[4] else 0.0,
                            "max_confidence": float(dist[5]) if dist[5] else 0.0,
                        }
                        for dist in detection_distribution
                    ],
                    "frame_analysis": (
                        [
                            {
                                "frame_number": frame[0],
                                "faces_in_frame": frame[1],
                                "avg_confidence": float(frame[2]) if frame[2] else 0.0,
                                "timestamp": float(frame[3]) if frame[3] else None,
                            }
                            for frame in frame_analysis
                        ]
                        if frame_analysis
                        else []
                    ),
                }

                logger.info(
                    f"Generated media timeline for {media_uuid}: {timeline['media_overview']['total_sessions']} sessions"
                )
                return timeline

        except Exception as e:
            logger.error(f"Error generating media timeline analytics: {e}")
            raise

    def query_sessions(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Query sessions with complex filters and pagination."""
        try:
            query = """
                SELECT session_uuid, media_uuid, camera_device_uuid, session_type,
                       processing_status, total_faces_detected, started_at, ended_at,
                       created_at, metadata
                FROM face_detection_sessions
                WHERE 1=1
            """
            params = []

            # Add filters
            if filters.get("start_date"):
                query += " AND started_at >= %s"
                params.append(filters["start_date"])

            if filters.get("end_date"):
                query += " AND started_at <= %s"
                params.append(filters["end_date"])

            if filters.get("camera_device_uuid"):
                query += " AND camera_device_uuid = %s"
                params.append(filters["camera_device_uuid"])

            if filters.get("media_uuid"):
                query += " AND media_uuid = %s"
                params.append(filters["media_uuid"])

            if filters.get("session_type"):
                query += " AND session_type = %s"
                params.append(filters["session_type"])

            if filters.get("processing_status"):
                query += " AND processing_status = %s"
                params.append(filters["processing_status"])

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query}) AS filtered_sessions"
            with self.db.connection.cursor() as cursor:
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

            # Add pagination
            query += " ORDER BY started_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            # Execute main query
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, params)
                sessions = cursor.fetchall()

            formatted_sessions = []
            for session in sessions:
                formatted_sessions.append(
                    {
                        "session_uuid": session[0],
                        "media_uuid": session[1],
                        "camera_device_uuid": session[2],
                        "session_type": session[3],
                        "processing_status": session[4],
                        "total_faces_detected": session[5],
                        "started_at": session[6].isoformat() if session[6] else None,
                        "ended_at": session[7].isoformat() if session[7] else None,
                        "created_at": session[8].isoformat() if session[8] else None,
                        "metadata": session[9],
                    }
                )

            return {
                "sessions": formatted_sessions,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": filters,
            }

        except Exception as e:
            logger.error(f"Error querying sessions: {e}")
            return {
                "error": "Failed to query sessions",
                "sessions": [],
                "total_count": 0,
            }

    def query_devices(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Query device analytics with complex filters."""
        try:
            query = """
                SELECT camera_device_uuid,
                       COUNT(DISTINCT session_uuid) as session_count,
                       COUNT(DISTINCT media_uuid) as media_count,
                       SUM(total_faces_detected) as total_faces,
                       AVG(total_faces_detected) as avg_faces_per_session,
                       MIN(started_at) as first_session,
                       MAX(ended_at) as last_session
                FROM face_detection_sessions
                WHERE camera_device_uuid IS NOT NULL
            """
            params = []

            # Add filters
            if filters.get("start_date"):
                query += " AND started_at >= %s"
                params.append(filters["start_date"])

            if filters.get("end_date"):
                query += " AND started_at <= %s"
                params.append(filters["end_date"])

            if filters.get("camera_device_uuid"):
                query += " AND camera_device_uuid = %s"
                params.append(filters["camera_device_uuid"])

            query += " GROUP BY camera_device_uuid"

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query}) AS grouped_devices"
            with self.db.connection.cursor() as cursor:
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

            # Add pagination
            query += " ORDER BY total_faces DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            # Execute main query
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, params)
                devices = cursor.fetchall()

            formatted_devices = []
            for device in devices:
                formatted_devices.append(
                    {
                        "camera_device_uuid": device[0],
                        "session_count": device[1],
                        "media_count": device[2],
                        "total_faces": device[3] or 0,
                        "avg_faces_per_session": float(device[4]) if device[4] else 0.0,
                        "first_session": device[5].isoformat() if device[5] else None,
                        "last_session": device[6].isoformat() if device[6] else None,
                    }
                )

            return {
                "devices": formatted_devices,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": filters,
            }

        except Exception as e:
            logger.error(f"Error querying devices: {e}")
            return {"error": "Failed to query devices", "devices": [], "total_count": 0}

    def query_media(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Query media analytics with complex filters."""
        try:
            query = """
                SELECT s.media_uuid,
                       COUNT(DISTINCT s.session_uuid) as session_count,
                       COUNT(DISTINCT s.camera_device_uuid) as device_count,
                       SUM(s.total_faces_detected) as total_faces,
                       AVG(s.total_faces_detected) as avg_faces_per_session,
                       MIN(s.started_at) as first_session,
                       MAX(s.ended_at) as last_session
                FROM face_detection_sessions s
                WHERE s.media_uuid IS NOT NULL
            """
            params = []

            # Add filters
            if filters.get("start_date"):
                query += " AND s.started_at >= %s"
                params.append(filters["start_date"])

            if filters.get("end_date"):
                query += " AND s.started_at <= %s"
                params.append(filters["end_date"])

            if filters.get("media_uuid"):
                query += " AND s.media_uuid = %s"
                params.append(filters["media_uuid"])

            if filters.get("camera_device_uuid"):
                query += " AND s.camera_device_uuid = %s"
                params.append(filters["camera_device_uuid"])

            query += " GROUP BY s.media_uuid"

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query}) AS grouped_media"
            with self.db.connection.cursor() as cursor:
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

            # Add pagination
            query += " ORDER BY total_faces DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            # Execute main query
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, params)
                media_items = cursor.fetchall()

            formatted_media = []
            for media in media_items:
                formatted_media.append(
                    {
                        "media_uuid": media[0],
                        "session_count": media[1],
                        "device_count": media[2],
                        "total_faces": media[3] or 0,
                        "avg_faces_per_session": float(media[4]) if media[4] else 0.0,
                        "first_session": media[5].isoformat() if media[5] else None,
                        "last_session": media[6].isoformat() if media[6] else None,
                    }
                )

            return {
                "media": formatted_media,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": filters,
            }

        except Exception as e:
            logger.error(f"Error querying media: {e}")
            return {"error": "Failed to query media", "media": [], "total_count": 0}

    def query_performance(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Query performance metrics with complex filters."""
        try:
            # Performance metrics from sessions
            query = """
                SELECT session_uuid, camera_device_uuid, media_uuid,
                       total_faces_detected,
                       EXTRACT(EPOCH FROM (ended_at - started_at)) as duration_seconds,
                       session_type, processing_status,
                       started_at, ended_at
                FROM face_detection_sessions
                WHERE started_at IS NOT NULL AND ended_at IS NOT NULL
            """
            params = []

            # Add filters
            if filters.get("start_date"):
                query += " AND started_at >= %s"
                params.append(filters["start_date"])

            if filters.get("end_date"):
                query += " AND started_at <= %s"
                params.append(filters["end_date"])

            if filters.get("camera_device_uuid"):
                query += " AND camera_device_uuid = %s"
                params.append(filters["camera_device_uuid"])

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query}) AS filtered_performance"
            with self.db.connection.cursor() as cursor:
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

            # Add pagination
            query += " ORDER BY started_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            # Execute main query
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, params)
                performance_data = cursor.fetchall()

            # Calculate metrics
            total_sessions = len(performance_data)
            total_faces = sum(row[3] or 0 for row in performance_data)
            total_duration = sum(row[4] or 0 for row in performance_data)

            avg_faces_per_session = (
                total_faces / total_sessions if total_sessions > 0 else 0
            )
            avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
            throughput = total_faces / total_duration if total_duration > 0 else 0

            formatted_performance = []
            for perf in performance_data:
                formatted_performance.append(
                    {
                        "session_uuid": perf[0],
                        "camera_device_uuid": perf[1],
                        "media_uuid": perf[2],
                        "faces_detected": perf[3] or 0,
                        "duration_seconds": float(perf[4]) if perf[4] else 0.0,
                        "session_type": perf[5],
                        "processing_status": perf[6],
                        "started_at": perf[7].isoformat() if perf[7] else None,
                        "ended_at": perf[8].isoformat() if perf[8] else None,
                        "faces_per_minute": (
                            (perf[3] or 0) / ((perf[4] or 1) / 60)
                            if perf[4] and perf[4] > 0
                            else 0
                        ),
                    }
                )

            return {
                "performance_data": formatted_performance,
                "total_count": total_count,
                "summary": {
                    "total_sessions": total_sessions,
                    "total_faces_detected": total_faces,
                    "total_duration_seconds": total_duration,
                    "avg_faces_per_session": avg_faces_per_session,
                    "avg_session_duration": avg_duration,
                    "overall_throughput_faces_per_second": throughput,
                },
                "limit": limit,
                "offset": offset,
                "filters_applied": filters,
            }

        except Exception as e:
            logger.error(f"Error querying performance: {e}")
            return {
                "error": "Failed to query performance",
                "performance_data": [],
                "total_count": 0,
            }

    def get_performance_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        metric_type: Optional[str] = None,
        granularity: str = "hour",
    ) -> Dict[str, Any]:
        """Get performance analytics and monitoring data."""
        try:
            analytics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "granularity": granularity,
                }
            }

            # Processing time analytics
            with self.db.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) as avg_processing_time,
                        MIN(EXTRACT(EPOCH FROM (ended_at - started_at))) as min_processing_time,
                        MAX(EXTRACT(EPOCH FROM (ended_at - started_at))) as max_processing_time,
                        COUNT(*) as total_sessions
                    FROM face_detection_sessions
                    WHERE started_at >= %s AND ended_at <= %s
                    AND started_at IS NOT NULL AND ended_at IS NOT NULL
                """,
                    (start_date, end_date),
                )

                processing_stats = cursor.fetchone()
                analytics["processing_time"] = {
                    "avg_seconds": (
                        float(processing_stats[0]) if processing_stats[0] else 0.0
                    ),
                    "min_seconds": (
                        float(processing_stats[1]) if processing_stats[1] else 0.0
                    ),
                    "max_seconds": (
                        float(processing_stats[2]) if processing_stats[2] else 0.0
                    ),
                    "total_sessions": processing_stats[3] or 0,
                }

            # Accuracy metrics (confidence-based)
            with self.db.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        AVG(confidence) as avg_confidence,
                        MIN(confidence) as min_confidence,
                        MAX(confidence) as max_confidence,
                        COUNT(*) as total_detections
                    FROM face_detections fd
                    JOIN face_detection_sessions fds ON fd.session_uuid = fds.session_uuid
                    WHERE fds.started_at >= %s AND fds.started_at <= %s
                """,
                    (start_date, end_date),
                )

                accuracy_stats = cursor.fetchone()
                analytics["accuracy"] = {
                    "avg_confidence": (
                        float(accuracy_stats[0]) if accuracy_stats[0] else 0.0
                    ),
                    "min_confidence": (
                        float(accuracy_stats[1]) if accuracy_stats[1] else 0.0
                    ),
                    "max_confidence": (
                        float(accuracy_stats[2]) if accuracy_stats[2] else 0.0
                    ),
                    "total_detections": accuracy_stats[3] or 0,
                }

            # Throughput analysis
            with self.db.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        SUM(total_faces_detected) as total_faces,
                        SUM(EXTRACT(EPOCH FROM (ended_at - started_at))) as total_time
                    FROM face_detection_sessions
                    WHERE started_at >= %s AND ended_at <= %s
                    AND started_at IS NOT NULL AND ended_at IS NOT NULL
                """,
                    (start_date, end_date),
                )

                throughput_stats = cursor.fetchone()
                total_faces = throughput_stats[0] or 0
                total_time = throughput_stats[1] or 1

                analytics["throughput"] = {
                    "total_faces_processed": total_faces,
                    "total_processing_time": float(total_time),
                    "faces_per_second": (
                        total_faces / total_time if total_time > 0 else 0
                    ),
                    "faces_per_minute": (
                        (total_faces / total_time) * 60 if total_time > 0 else 0
                    ),
                }

            # Time-series data based on granularity
            if granularity == "hour":
                date_trunc = "date_trunc('hour', started_at)"
            else:  # day
                date_trunc = "date_trunc('day', started_at)"

            with self.db.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT 
                        {date_trunc} as time_bucket,
                        COUNT(*) as session_count,
                        SUM(total_faces_detected) as faces_count,
                        AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) as avg_duration
                    FROM face_detection_sessions
                    WHERE started_at >= %s AND started_at <= %s
                    AND started_at IS NOT NULL
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                """,
                    (start_date, end_date),
                )

                time_series = cursor.fetchall()
                analytics["time_series"] = []

                for row in time_series:
                    analytics["time_series"].append(
                        {
                            "timestamp": row[0].isoformat() if row[0] else None,
                            "session_count": row[1] or 0,
                            "faces_detected": row[2] or 0,
                            "avg_duration_seconds": float(row[3]) if row[3] else 0.0,
                        }
                    )

            return analytics

        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            return {"error": "Failed to get performance analytics"}


# ========================================================================
# Analytics Service Instance Management
# ========================================================================

_analytics_service_instance = None


def get_analytics_service() -> Optional[AdvancedAnalyticsService]:
    """Get the global analytics service instance."""
    global _analytics_service_instance

    if _analytics_service_instance is None:
        try:
            # Import database.py file directly
            import importlib.util
            import os

            db_spec = importlib.util.spec_from_file_location(
                "database", os.path.join(os.path.dirname(__file__), "database.py")
            )
            db_module = importlib.util.module_from_spec(db_spec)
            db_spec.loader.exec_module(db_module)
            vision_db = db_module.vision_db

            if vision_db:
                _analytics_service_instance = AdvancedAnalyticsService(vision_db)
                logger.info("Analytics service initialized successfully")
            else:
                logger.warning("Database not available for analytics service")
        except Exception as e:
            logger.error(f"Failed to initialize analytics service: {e}")

    return _analytics_service_instance


def reset_analytics_service():
    """Reset the analytics service instance (for testing)."""
    global _analytics_service_instance
    _analytics_service_instance = None

"""
PPL Meta Vision Service - Database Manager
Handles storage and retrieval of face detection results
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from models import FaceDetectionResult, FaceRecord, MediaRecord, OverlayRectangle

logger = logging.getLogger(__name__)


class VisionDatabase:
    """Database manager for vision service data."""

    def __init__(self, db_path: str = "vision_data.db"):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.connection = None
        self.init_database()

    def init_database(self):
        """Initialize database with required tables."""
        try:
            self.connection = sqlite3.connect(
                self.db_path, check_same_thread=False, timeout=30.0
            )
            self.connection.row_factory = sqlite3.Row

            # Create tables
            self.create_tables()
            logger.info(f"✅ Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    def create_tables(self):
        """Create database tables."""
        cursor = self.connection.cursor()

        # Media records table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS media_records (
                media_id TEXT PRIMARY KEY,
                media_type TEXT NOT NULL,
                media_url TEXT NOT NULL,
                processing_status TEXT DEFAULT 'pending',
                total_faces INTEGER DEFAULT 0,
                total_frames INTEGER,
                video_duration REAL,
                video_fps REAL,
                video_width INTEGER,
                video_height INTEGER,
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Face detections table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS face_detections (
                id TEXT PRIMARY KEY,
                media_id TEXT NOT NULL,
                frame_number INTEGER,
                timestamp REAL,
                bbox_x1 INTEGER NOT NULL,
                bbox_y1 INTEGER NOT NULL,
                bbox_x2 INTEGER NOT NULL,
                bbox_y2 INTEGER NOT NULL,
                confidence REAL NOT NULL,
                method TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_records (media_id)
            )
        """
        )

        # Processing jobs table (for batch processing)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'queued',
                total_media INTEGER DEFAULT 0,
                processed_media INTEGER DEFAULT 0,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes for performance
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_media_id 
            ON face_detections(media_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_timestamp 
            ON face_detections(timestamp)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_frame 
            ON face_detections(frame_number)
        """
        )

        self.connection.commit()
        logger.info("✅ Database tables created/verified")

    def store_media_record(self, media_record: MediaRecord) -> bool:
        """Store or update media record."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO media_records 
                (media_id, media_type, media_url, processing_status, 
                 total_faces, total_frames, video_duration, video_fps,
                 video_width, video_height, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    media_record.media_id,
                    media_record.media_type,
                    media_record.media_url,
                    media_record.processing_status,
                    media_record.total_faces,
                    media_record.total_frames,
                    media_record.video_duration,
                    media_record.video_fps,
                    getattr(media_record, "video_width", None),
                    getattr(media_record, "video_height", None),
                    media_record.processed_at,
                ),
            )
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to store media record: {e}")
            return False

    def store_face_detection(self, detection: FaceDetectionResult) -> bool:
        """Store face detection result."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO face_detections 
                (id, media_id, frame_number, timestamp, 
                 bbox_x1, bbox_y1, bbox_x2, bbox_y2, 
                 confidence, method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    detection.id,
                    detection.media_id,
                    detection.frame_number,
                    detection.timestamp,
                    detection.bbox[0],
                    detection.bbox[1],
                    detection.bbox[2],
                    detection.bbox[3],
                    detection.confidence,
                    detection.method,
                ),
            )
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to store face detection: {e}")
            return False

    def get_media_record(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get media record by ID."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT * FROM media_records WHERE media_id = ?
            """,
                (media_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Failed to get media record: {e}")
            return None

    def get_face_detections(
        self,
        media_id: str,
        frame_number: Optional[int] = None,
        timestamp: Optional[float] = None,
        confidence_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Get face detections for media."""
        try:
            cursor = self.connection.cursor()

            query = """
                SELECT * FROM face_detections 
                WHERE media_id = ? AND confidence >= ?
            """
            params = [media_id, confidence_threshold]

            if frame_number is not None:
                query += " AND frame_number = ?"
                params.append(frame_number)

            if timestamp is not None:
                # Get detections within 0.1 seconds of timestamp
                query += " AND ABS(timestamp - ?) <= 0.1"
                params.append(timestamp)

            query += " ORDER BY timestamp, frame_number"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"❌ Failed to get face detections: {e}")
            return []

    def get_face_timeline(
        self,
        media_id: str,
        time_resolution: float = 1.0,
        confidence_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Get face detection timeline for video scrubbing."""
        try:
            cursor = self.connection.cursor()

            # Get video duration first
            media_record = self.get_media_record(media_id)
            if not media_record or not media_record.get("video_duration"):
                return []

            duration = media_record["video_duration"]
            timeline = []

            # Create timeline segments
            for start_time in range(0, int(duration) + 1, int(time_resolution)):
                end_time = min(start_time + time_resolution, duration)

                cursor.execute(
                    """
                    SELECT COUNT(*) as face_count, 
                           MAX(confidence) as max_confidence,
                           GROUP_CONCAT(id) as detection_ids
                    FROM face_detections 
                    WHERE media_id = ? 
                    AND timestamp >= ? 
                    AND timestamp < ?
                    AND confidence >= ?
                """,
                    (media_id, start_time, end_time, confidence_threshold),
                )

                row = cursor.fetchone()
                if row:
                    timeline.append(
                        {
                            "start_time": start_time,
                            "end_time": end_time,
                            "face_count": row["face_count"] or 0,
                            "max_confidence": row["max_confidence"] or 0.0,
                            "detection_ids": (
                                row["detection_ids"].split(",")
                                if row["detection_ids"]
                                else []
                            ),
                        }
                    )

            return timeline

        except Exception as e:
            logger.error(f"❌ Failed to get face timeline: {e}")
            return []

    def get_media_statistics(self, media_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for media."""
        try:
            cursor = self.connection.cursor()

            # Basic stats
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_detections,
                    AVG(confidence) as avg_confidence,
                    MIN(confidence) as min_confidence,
                    MAX(confidence) as max_confidence,
                    COUNT(DISTINCT method) as methods_used
                FROM face_detections 
                WHERE media_id = ?
            """,
                (media_id,),
            )

            stats = dict(cursor.fetchone())

            # Method breakdown
            cursor.execute(
                """
                SELECT method, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM face_detections 
                WHERE media_id = ?
                GROUP BY method
            """,
                (media_id,),
            )

            methods = [dict(row) for row in cursor.fetchall()]
            stats["method_breakdown"] = methods

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to get media statistics: {e}")
            return {}

    def get_database_statistics(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get table counts
                cursor.execute("SELECT COUNT(*) FROM media_records")
                total_media = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM face_detections")
                total_detections = cursor.fetchone()[0]

                # Get media type breakdown
                cursor.execute(
                    """
                    SELECT media_type, COUNT(*) 
                    FROM media_records 
                    GROUP BY media_type
                """
                )
                media_types = dict(cursor.fetchall())

                # Get processing status breakdown
                cursor.execute(
                    """
                    SELECT processing_status, COUNT(*) 
                    FROM media_records 
                    GROUP BY processing_status
                """
                )
                processing_status = dict(cursor.fetchall())

                # Get method distribution
                cursor.execute(
                    """
                    SELECT method, COUNT(*) 
                    FROM face_detections 
                    GROUP BY method
                """
                )
                method_distribution = dict(cursor.fetchall())

                # Get average faces per media
                cursor.execute(
                    """
                    SELECT AVG(total_faces) 
                    FROM media_records 
                    WHERE total_faces IS NOT NULL
                """
                )
                avg_faces = cursor.fetchone()[0] or 0

                return {
                    "total_media_records": total_media,
                    "total_face_detections": total_detections,
                    "media_type_breakdown": media_types,
                    "processing_status_breakdown": processing_status,
                    "detection_method_distribution": method_distribution,
                    "average_faces_per_media": round(avg_faces, 2),
                    "database_path": self.db_path,
                }

        except Exception as e:
            logger.error(f"❌ Database statistics error: {e}")
            return {}

    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data (for maintenance)."""
        try:
            cursor = self.connection.cursor()

            # Delete old face detections
            cursor.execute(
                """
                DELETE FROM face_detections 
                WHERE created_at < datetime('now', '-{} days')
            """.format(
                    days
                )
            )

            deleted_faces = cursor.rowcount

            # Delete old media records without detections
            cursor.execute(
                """
                DELETE FROM media_records 
                WHERE media_id NOT IN (
                    SELECT DISTINCT media_id FROM face_detections
                )
                AND created_at < datetime('now', '-{} days')
            """.format(
                    days
                )
            )

            deleted_media = cursor.rowcount

            self.connection.commit()

            logger.info(
                f"🧹 Cleaned up {deleted_faces} face detections and {deleted_media} media records"
            )
            return deleted_faces + deleted_media

        except Exception as e:
            logger.error(f"❌ Failed to cleanup old data: {e}")
            return 0

    def get_database_status(self) -> Dict[str, Any]:
        """Get database status and statistics."""
        try:
            cursor = self.connection.cursor()

            # Table counts
            cursor.execute("SELECT COUNT(*) FROM media_records")
            media_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM face_detections")
            detection_count = cursor.fetchone()[0]

            # Recent activity
            cursor.execute(
                """
                SELECT COUNT(*) FROM face_detections 
                WHERE created_at > datetime('now', '-1 hour')
            """
            )
            recent_detections = cursor.fetchone()[0]

            return {
                "status": "connected",
                "media_records": media_count,
                "face_detections": detection_count,
                "recent_detections_1h": recent_detections,
                "database_file": str(self.db_path),
                "connection_active": self.connection is not None,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get database status: {e}")
            return {"status": "error", "error": str(e)}

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("📦 Database connection closed")


# Global database instance
vision_db = VisionDatabase()

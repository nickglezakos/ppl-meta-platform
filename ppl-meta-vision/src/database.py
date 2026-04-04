"""
PPL Meta Vision Service - PostgreSQL Database Manager
Handles storage and retrieval of face detection results using PostgreSQL
"""

import logging
import os
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from models import FaceDetectionResult, MediaRecord

logger = logging.getLogger(__name__)


class VisionDatabase:
    """Database manager for vision service data using PostgreSQL."""

    def __init__(self):
        """Initialize database connection."""
        self.connection = None
        self.init_database()

    def _get_connection_params(self) -> Dict[str, Any]:
        """Get database connection parameters."""
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "ppl_vision_db"),
            "user": os.getenv("DB_USER", "nickgklezakos"),
            "password": os.getenv("DB_PASSWORD", "change-this-password"),
        }

    def init_database(self):
        """Initialize database with required tables."""
        try:
            # Connect to database
            conn_params = self._get_connection_params()
            self.connection = psycopg2.connect(**conn_params)
            self.connection.autocommit = True

            # Create tables
            self.create_tables()
            logger.info("PostgreSQL database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Continue without database for now
            self.connection = None

    def create_tables(self):
        """Create database tables."""
        if not self.connection:
            return

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
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
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
                frame_width INTEGER,
                frame_height INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_media_id
            ON face_detections (media_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_timestamp
            ON face_detections (timestamp)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_frame
            ON face_detections (frame_number)
        """
        )

        # Face detection sessions table (for PPL Thread workflow)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS face_detection_sessions (
                session_uuid TEXT PRIMARY KEY,
                media_uuid TEXT NOT NULL,
                workflow_id TEXT,
                status TEXT DEFAULT 'active',
                face_count INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP
            )
        """
        )

        # Create index for face_detection_sessions
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_media 
            ON face_detection_sessions (media_uuid)
        """
        )

        cursor.close()

    def store_media_record(self, media_record: MediaRecord) -> bool:
        """Store media record."""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO media_records
                (media_id, media_type, media_url, processing_status,
                 total_frames, video_duration, video_fps, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (media_id) DO UPDATE SET
                    processing_status = EXCLUDED.processing_status,
                    total_frames = EXCLUDED.total_frames,
                    video_duration = EXCLUDED.video_duration,
                    video_fps = EXCLUDED.video_fps,
                    processed_at = EXCLUDED.processed_at
            """,
                (
                    media_record.media_id,
                    media_record.media_type,
                    media_record.media_url,
                    media_record.processing_status,
                    media_record.total_frames,
                    media_record.video_duration,
                    media_record.video_fps,
                    media_record.processed_at,
                ),
            )
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to store media record: {e}")
            return False

    def store_face_detection(self, detection: FaceDetectionResult) -> bool:
        """Store face detection."""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            # Check if frame_width/frame_height columns exist (migration guard)
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'face_detections' AND column_name = 'frame_width'
            """
            )
            has_frame_dims = cursor.fetchone() is not None

            if has_frame_dims:
                cursor.execute(
                    """
                    INSERT INTO face_detections
                    (id, media_id, frame_number, timestamp,
                     bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     confidence, method, frame_width, frame_height)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        method = EXCLUDED.method,
                        frame_width = EXCLUDED.frame_width,
                        frame_height = EXCLUDED.frame_height
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
                        detection.frame_width,
                        detection.frame_height,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO face_detections
                    (id, media_id, frame_number, timestamp,
                     bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     confidence, method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        method = EXCLUDED.method
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
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to store face detection: {e}")
            return False

    def store_face_detection_with_session(
        self, detection: FaceDetectionResult, session_uuid: str
    ) -> bool:
        """Store face detection with session tracking for Workflow 4."""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            # Check which optional columns exist (migration guards)
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'face_detections'
                AND column_name IN ('session_uuid', 'frame_width')
            """
            )
            existing_cols = {row[0] for row in cursor.fetchall()}
            has_session_column = "session_uuid" in existing_cols
            has_frame_dims = "frame_width" in existing_cols

            if has_session_column and has_frame_dims:
                cursor.execute(
                    """
                    INSERT INTO face_detections
                    (id, media_id, session_uuid, frame_number, timestamp,
                     bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     confidence, method, frame_width, frame_height)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        method = EXCLUDED.method,
                        session_uuid = EXCLUDED.session_uuid,
                        frame_width = EXCLUDED.frame_width,
                        frame_height = EXCLUDED.frame_height
                """,
                    (
                        detection.id,
                        detection.media_id,
                        session_uuid,
                        detection.frame_number,
                        detection.timestamp,
                        detection.bbox[0],
                        detection.bbox[1],
                        detection.bbox[2],
                        detection.bbox[3],
                        detection.confidence,
                        detection.method,
                        detection.frame_width,
                        detection.frame_height,
                    ),
                )
            elif has_session_column:
                # Use enhanced schema with session tracking (no frame dims)
                cursor.execute(
                    """
                    INSERT INTO face_detections
                    (id, media_id, session_uuid, frame_number, timestamp,
                     bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     confidence, method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        method = EXCLUDED.method,
                        session_uuid = EXCLUDED.session_uuid
                """,
                    (
                        detection.id,
                        detection.media_id,
                        session_uuid,
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
            else:
                # Fallback to regular storage if schema not upgraded
                logger.warning(
                    "Session UUID column not found, falling back to regular storage"
                )
                cursor.execute(
                    """
                    INSERT INTO face_detections
                    (id, media_id, frame_number, timestamp,
                     bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     confidence, method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        method = EXCLUDED.method
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

            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to store face detection with session: {e}")
            return False

    def get_face_detections(
        self,
        media_id: str,
        frame_number: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Get face detections for media, optionally filtered by frame.
        
        Returns ALL face detections for the media without time-window filtering.
        Session tracking is now handled via face_detection_sessions table.
        """
        if not self.connection:
            return []

        try:
            cursor = self.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            # Build query to get ALL faces for this media_id
            query = """
                SELECT * FROM face_detections 
                WHERE media_id = %s
            """
            params: List[Any] = [media_id]

            if frame_number is not None:
                query += " AND frame_number = %s"
                params.append(frame_number)

            if confidence_threshold is not None:
                query += " AND confidence >= %s"
                params.append(confidence_threshold)

            query += " ORDER BY frame_number, timestamp"

            cursor.execute(query, params)

            rows = cursor.fetchall()
            cursor.close()

            detections = []
            for row in rows:
                logger.debug(f"Processing row: {dict(row)}")
                logger.debug(f"Available keys: {list(row.keys())}")
                detections.append(
                    {
                        "id": row["id"],
                        "media_id": row["media_id"],
                        "frame_number": row["frame_number"],
                        "timestamp": row["timestamp"],
                        "bbox": [
                            row["bbox_x1"],
                            row["bbox_y1"],
                            row["bbox_x2"],
                            row["bbox_y2"],
                        ],
                        "confidence": row["confidence"],
                        "method": row["method"],
                        "frame_width": row.get("frame_width"),
                        "frame_height": row.get("frame_height"),
                        "created_at": row["created_at"],
                    }
                )

            logger.info(f"Retrieved {len(detections)} faces for media {media_id}")
            return detections

        except Exception as e:
            logger.error(f"Failed to get face detections: {e}")
            return []

    def get_media_record(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get media record."""
        if not self.connection:
            return None

        try:
            cursor = self.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            cursor.execute(
                """
                SELECT * FROM media_records WHERE media_id = %s
            """,
                (media_id,),
            )

            row = cursor.fetchone()
            cursor.close()

            return dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get media record: {e}")
            return None

    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        if not self.connection:
            return {"total_media": 0, "total_detections": 0}

        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM media_records")
            media_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM face_detections")
            detection_count = cursor.fetchone()[0]

            cursor.close()

            return {
                "total_media": media_count,
                "total_detections": detection_count,
                "database_type": "PostgreSQL",
            }

        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {"total_media": 0, "total_detections": 0}


# Global instance
vision_db = VisionDatabase()


# Dependency function for FastAPI
def get_vision_database():
    """Get the global vision database instance for FastAPI dependency injection."""
    return vision_db


# Alias for compatibility
DatabaseManager = VisionDatabase

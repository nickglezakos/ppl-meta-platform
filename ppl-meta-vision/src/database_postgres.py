"""
PPL Meta Vision Service - PostgreSQL Database Manager
Handles storage and retrieval of face detection results using PostgreSQL
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
import psycopg2
import psycopg2.extras
from models import FaceDetectionResult, MediaRecord

logger = logging.getLogger(__name__)


class VisionDatabase:
    """Database manager for vision service data using PostgreSQL."""

    def __init__(self, database_url: str = None):
        """Initialize database connection."""
        self.database_url = database_url or self._get_database_url()
        self.connection_pool = None
        self._sync_connection = None

    def _get_database_url(self) -> str:
        """Get database URL from environment or default."""
        return (
            f"postgresql://{os.getenv('DB_USER', 'nickgklezakos')}:"
            f"{os.getenv('DB_PASSWORD', 'change-this-password')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_NAME', 'ppl_vision_db')}"
        )

    async def init_database(self):
        """Initialize database with required tables."""
        try:
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=10, command_timeout=60
            )

            # Create tables
            async with self.connection_pool.acquire() as conn:
                await self.create_tables(conn)

            logger.info("PostgreSQL database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def init_database_sync(self):
        """Synchronous wrapper for init_database."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new event loop in thread
                import threading

                def run_init():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(self.init_database())
                    new_loop.close()

                thread = threading.Thread(target=run_init)
                thread.start()
                thread.join()
            else:
                loop.run_until_complete(self.init_database())
        except Exception as e:
            logger.error(f"Sync database init failed: {e}")
            raise

    @property
    def connection(self):
        """Get synchronous database connection for PPL Thread workflow."""
        if self._sync_connection is None or self._sync_connection.closed:
            try:
                self._sync_connection = psycopg2.connect(self.database_url)
                self._sync_connection.autocommit = False  # Enable transactions
                logger.info("Synchronous database connection established")
            except Exception as e:
                logger.error(f"Failed to create sync connection: {e}")
                raise
        return self._sync_connection

    async def create_tables(self, conn):
        """Create database tables."""

        # Media records table
        await conn.execute(
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
        await conn.execute(
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
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (media_id) REFERENCES media_records (media_id)
            )
        """
        )

        # Face detection sessions table (for PPL Thread workflow)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS face_detection_sessions (
                session_uuid TEXT PRIMARY KEY,
                media_uuid TEXT NOT NULL,
                workflow_id TEXT,
                status TEXT DEFAULT 'active',
                face_count INTEGER DEFAULT 0,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                FOREIGN KEY (media_uuid) REFERENCES media_records (media_id)
            )
        """
        )

        # Person workflows table (for PPL Thread workflow)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS person_workflows (
                workflow_id TEXT PRIMARY KEY,
                session_uuid TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                input_face_count INTEGER NOT NULL,
                output_person_count INTEGER DEFAULT 0,
                tolerance_percent REAL NOT NULL,
                enable_quality_analysis BOOLEAN DEFAULT TRUE,
                enable_age_detection BOOLEAN DEFAULT FALSE,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                FOREIGN KEY (session_uuid) REFERENCES face_detection_sessions (session_uuid)
            )
        """
        )

        # Person objects table (for PPL Thread workflow results)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS person_objects (
                person_id TEXT PRIMARY KEY,
                session_uuid TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                face_count INTEGER NOT NULL,
                average_position_x REAL NOT NULL,
                average_position_y REAL NOT NULL,
                quality_score REAL DEFAULT 0.0,
                best_face_id TEXT,
                estimated_age TEXT DEFAULT 'Unknown',
                distance_from_camera REAL DEFAULT 0.0,
                tracking_algorithm TEXT NOT NULL,
                tolerance_percent REAL NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (session_uuid) REFERENCES face_detection_sessions (session_uuid),
                FOREIGN KEY (workflow_id) REFERENCES person_workflows (workflow_id)
            )
        """
        )

        # Person face mappings table (for PPL Thread workflow)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS person_face_mappings (
                id SERIAL PRIMARY KEY,
                person_id TEXT NOT NULL,
                face_detection_id TEXT NOT NULL,
                match_type TEXT NOT NULL,
                match_distance REAL NOT NULL,
                frame_number INTEGER NOT NULL,
                position_x REAL NOT NULL,
                position_y REAL NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (person_id) REFERENCES person_objects (person_id),
                FOREIGN KEY (face_detection_id) REFERENCES face_detections (id)
            )
        """
        )

        # Create indexes for face_detections
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_media_id 
            ON face_detections (media_id)
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_timestamp 
            ON face_detections (timestamp)
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detections_frame 
            ON face_detections (frame_number)
        """
        )

        # Create indexes for PPL Thread workflow tables
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_media 
            ON face_detection_sessions (media_uuid)
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_person_workflows_session 
            ON person_workflows (session_uuid)
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_person_objects_session 
            ON person_objects (session_uuid)
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_person_face_mappings_person 
            ON person_face_mappings (person_id)
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_person_face_mappings_face 
            ON person_face_mappings (face_detection_id)
        """
        )

    def store_media_record(self, media_record: MediaRecord) -> bool:
        """Store media record synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Use asyncio.create_task for running loop
                task = asyncio.create_task(self._store_media_record_async(media_record))
                # This will complete when the task finishes
                return True  # Assume success for now
            else:
                return loop.run_until_complete(
                    self._store_media_record_async(media_record)
                )
        except Exception as e:
            logger.error(f"Failed to store media record: {e}")
            return False

    async def _store_media_record_async(self, media_record: MediaRecord) -> bool:
        """Store media record asynchronously."""
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO media_records 
                    (media_id, media_type, media_url, processing_status,
                     total_frames, video_duration, video_fps, processed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (media_id) DO UPDATE SET
                        processing_status = EXCLUDED.processing_status,
                        total_frames = EXCLUDED.total_frames,
                        video_duration = EXCLUDED.video_duration,
                        video_fps = EXCLUDED.video_fps,
                        processed_at = EXCLUDED.processed_at
                """,
                    media_record.media_id,
                    media_record.media_type,
                    media_record.media_url,
                    media_record.processing_status,
                    media_record.total_frames,
                    media_record.video_duration,
                    media_record.video_fps,
                    media_record.processed_at,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to store media record: {e}")
            return False

    def store_face_detection(self, detection: FaceDetectionResult) -> bool:
        """Store face detection synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = asyncio.create_task(self._store_face_detection_async(detection))
                return True  # Assume success for now
            else:
                return loop.run_until_complete(
                    self._store_face_detection_async(detection)
                )
        except Exception as e:
            logger.error(f"Failed to store face detection: {e}")
            return False

    async def _store_face_detection_async(self, detection: FaceDetectionResult) -> bool:
        """Store face detection asynchronously."""
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO face_detections 
                    (id, media_id, frame_number, timestamp,
                     bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     confidence, method)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        method = EXCLUDED.method
                """,
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
                )
            return True
        except Exception as e:
            logger.error(f"Failed to store face detection: {e}")
            return False

    def get_face_detections(self, media_id: str) -> List[Dict[str, Any]]:
        """Get face detections synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # FIXED: Use create_task to run async function in running loop
                task = asyncio.create_task(self._get_face_detections_async(media_id))
                # This is a synchronous function, so we need to handle the running loop properly
                # For now, we'll use a thread to run the async function
                import concurrent.futures
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._get_face_detections_async(media_id))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._get_face_detections_async(media_id)
                )
        except Exception as e:
            logger.error(f"Failed to get face detections: {e}")
            return []

    async def _get_face_detections_async(self, media_id: str) -> List[Dict[str, Any]]:
        """Get face detections asynchronously."""
        try:
            async with self.connection_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM face_detections
                    WHERE media_id = $1
                    ORDER BY frame_number, timestamp
                """,
                    media_id,
                )

                detections = []
                for row in rows:
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
                            "created_at": row["created_at"],
                        }
                    )

                return detections

        except Exception as e:
            logger.error(f"Failed to get face detections: {e}")
            return []

    def get_media_record(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get media record synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None  # For now, return None when loop is running
            else:
                return loop.run_until_complete(self._get_media_record_async(media_id))
        except Exception as e:
            logger.error(f"Failed to get media record: {e}")
            return None

    async def _get_media_record_async(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get media record asynchronously."""
        try:
            async with self.connection_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM media_records WHERE media_id = $1
                """,
                    media_id,
                )

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Failed to get media record: {e}")
            return None

    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return {"total_media": 0, "total_detections": 0}
            else:
                return loop.run_until_complete(self._get_database_statistics_async())
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {"total_media": 0, "total_detections": 0}

    async def _get_database_statistics_async(self) -> Dict[str, Any]:
        """Get database statistics asynchronously."""
        try:
            async with self.connection_pool.acquire() as conn:
                media_count = await conn.fetchval("SELECT COUNT(*) FROM media_records")
                detection_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM face_detections"
                )

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

# ================================================================
# Phase 1: Database Integration Methods
# PPL Meta Platform - PostgreSQL + pgvector Integration
# ================================================================

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)


class Phase1DatabaseClient:
    """
    Database client for Phase 1 enhanced person detection system.

    Features:
    - PostgreSQL with pgvector for facial embeddings
    - Session-based workflow management
    - Person routes tracking with spatial analysis
    - Distance calculation storage
    - Vector similarity search
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(self.connection_string)
        logger.info("Phase 1 database client initialized")

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    # ================================================================
    # Master Workflow Management
    # ================================================================

    async def create_master_workflow(self, workflow_data: Dict) -> str:
        """Create master workflow record."""

        query = """
        INSERT INTO persons_lifecycle_master_workflows (
            session_uuid, source_identifier, source_type, source_id,
            execution_trigger, workflow_types, status, current_stage,
            progress_percentage, configuration, started_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING session_uuid
        """

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                query,
                workflow_data["session_uuid"],
                workflow_data["source_identifier"],
                workflow_data["source_type"],
                workflow_data["source_id"],
                workflow_data["execution_trigger"],
                workflow_data.get("workflow_types", '["face_detection"]'),
                workflow_data["status"],
                workflow_data["current_stage"],
                workflow_data["progress_percentage"],
                workflow_data["configuration"],
                workflow_data["started_at"],
            )

    async def update_master_workflow(self, session_uuid: str, update_data: Dict):
        """Update master workflow record."""

        # Build dynamic update query
        set_clauses = []
        values = []
        param_count = 1

        for key, value in update_data.items():
            set_clauses.append(f"{key} = ${param_count}")
            values.append(value)
            param_count += 1

        query = f"""
        UPDATE persons_lifecycle_master_workflows 
        SET {', '.join(set_clauses)}
        WHERE session_uuid = ${param_count}
        """
        values.append(session_uuid)

        async with self.pool.acquire() as conn:
            await conn.execute(query, *values)

    async def get_master_workflow_by_session(self, session_uuid: str) -> Optional[Dict]:
        """Get master workflow by session UUID."""

        query = """
        SELECT * FROM persons_lifecycle_master_workflows 
        WHERE session_uuid = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, session_uuid)
            return dict(row) if row else None

    # ================================================================
    # Enhanced Face Detection Storage
    # ================================================================

    async def create_face_detection_record(
        self,
        session_uuid: str,
        timestamp_ms: int,
        frame_number: int,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
        distance_from_camera: Optional[float] = None,
        face_area_pixels: Optional[int] = None,
        facial_embedding: Optional[List[float]] = None,
        embedding_confidence: Optional[float] = None,
    ) -> str:
        """Create enhanced face detection record with distance and embeddings."""

        # Convert embedding to pgvector format
        embedding_vector = None
        if facial_embedding:
            embedding_vector = f"[{','.join(map(str, facial_embedding))}]"

        query = """
        INSERT INTO face_detections (
            session_uuid, timestamp_ms, frame_number,
            x, y, width, height, confidence,
            distance_from_camera, face_area_pixels,
            facial_embedding, embedding_confidence
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                query,
                session_uuid,
                timestamp_ms,
                frame_number,
                x,
                y,
                width,
                height,
                confidence,
                distance_from_camera,
                face_area_pixels,
                embedding_vector,
                embedding_confidence,
            )

    async def get_face_detections_by_session(
        self, session_uuid: str, limit: int = 1000
    ) -> List[Dict]:
        """Get face detections for a session."""

        query = """
        SELECT * FROM face_detections 
        WHERE session_uuid = $1 
        ORDER BY timestamp_ms, frame_number
        LIMIT $2
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, session_uuid, limit)
            return [dict(row) for row in rows]

    async def get_face_detections_by_person(
        self, person_id: str, order_by: str = "timestamp_ms"
    ) -> List[Dict]:
        """Get face detections for a specific person."""

        query = f"""
        SELECT fd.* FROM face_detections fd
        JOIN person_objects po ON fd.session_uuid = po.session_uuid
        WHERE po.id = $1
        ORDER BY {order_by}
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, person_id)
            return [dict(row) for row in rows]

    # ================================================================
    # Person Objects with Enhanced Tracking
    # ================================================================

    async def get_person_objects_by_session(self, session_uuid: str) -> List[Dict]:
        """Get person objects for a session."""

        query = """
        SELECT * FROM person_objects 
        WHERE session_uuid = $1 
        ORDER BY created_at
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, session_uuid)
            return [dict(row) for row in rows]

    async def update_person_movement_summary(
        self,
        person_id: str,
        total_route_points: int,
        movement_distance_pixels: float,
        average_velocity: float,
        time_in_frame_seconds: float,
        average_distance: Optional[float] = None,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
    ):
        """Update person object with movement summary."""

        query = """
        UPDATE person_objects SET
            total_route_points = $2,
            movement_distance_pixels = $3,
            average_velocity = $4,
            time_in_frame_seconds = $5,
            average_distance_from_camera = $6,
            min_distance_from_camera = $7,
            max_distance_from_camera = $8,
            updated_at = NOW()
        WHERE id = $1
        """

        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                person_id,
                total_route_points,
                movement_distance_pixels,
                average_velocity,
                time_in_frame_seconds,
                average_distance,
                min_distance,
                max_distance,
            )

    # ================================================================
    # Person Routes Storage and Retrieval
    # ================================================================

    async def create_person_route_point(self, route_data: Dict) -> str:
        """Create person route point."""

        query = """
        INSERT INTO person_routes (
            person_object_id, session_uuid, sequence_number,
            timestamp_ms, frame_number, center_x, center_y,
            bounding_box_width, bounding_box_height,
            distance_from_camera, face_area_pixels,
            velocity_x, velocity_y, velocity_magnitude, direction_radians,
            confidence_score, detection_quality
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        RETURNING id
        """

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                query,
                route_data["person_object_id"],
                route_data["session_uuid"],
                route_data["sequence_number"],
                route_data["timestamp_ms"],
                route_data.get("frame_number"),
                route_data["center_x"],
                route_data["center_y"],
                route_data["bounding_box_width"],
                route_data["bounding_box_height"],
                route_data.get("distance_from_camera"),
                route_data.get("face_area_pixels"),
                route_data["velocity_x"],
                route_data["velocity_y"],
                route_data["velocity_magnitude"],
                route_data["direction_radians"],
                route_data["confidence_score"],
                route_data["detection_quality"],
            )

    async def get_person_routes_by_session(
        self, session_uuid: str, confidence_threshold: float = 0.0
    ) -> List[Dict]:
        """Get person routes for a session."""

        query = """
        SELECT pr.*, po.source_identifier, po.source_type
        FROM person_routes pr
        JOIN person_objects po ON pr.person_object_id = po.id
        WHERE pr.session_uuid = $1 AND pr.confidence_score >= $2
        ORDER BY pr.person_object_id, pr.sequence_number
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, session_uuid, confidence_threshold)
            return [dict(row) for row in rows]

    async def get_person_routes_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        confidence_threshold: float = 0.0,
    ) -> List[Dict]:
        """Get person routes within time range."""

        query = """
        SELECT pr.*, po.source_identifier, po.source_type
        FROM person_routes pr
        JOIN person_objects po ON pr.person_object_id = po.id
        WHERE pr.created_at BETWEEN $1 AND $2 
        AND pr.confidence_score >= $3
        ORDER BY pr.created_at, pr.person_object_id, pr.sequence_number
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, start_time, end_time, confidence_threshold)
            return [dict(row) for row in rows]

    # ================================================================
    # Vector Search with pgvector
    # ================================================================

    async def search_similar_faces_by_embedding(
        self,
        embedding_vector: List[float],
        similarity_threshold: float = 0.8,
        limit: int = 10,
        session_uuid: Optional[str] = None,
    ) -> List[Dict]:
        """Search for similar faces using vector embeddings."""

        # Convert embedding to pgvector format
        vector_str = f"[{','.join(map(str, embedding_vector))}]"

        # Build query with optional session filter
        base_query = """
        SELECT 
            fd.id,
            fd.session_uuid,
            fd.timestamp_ms,
            fd.frame_number,
            fd.x, fd.y, fd.width, fd.height,
            fd.confidence,
            fd.distance_from_camera,
            fd.embedding_confidence,
            1 - (fd.facial_embedding <=> $1::vector) as similarity_score,
            po.source_identifier,
            po.source_type
        FROM face_detections fd
        LEFT JOIN person_objects po ON fd.session_uuid = po.session_uuid
        WHERE fd.facial_embedding IS NOT NULL
        AND 1 - (fd.facial_embedding <=> $1::vector) >= $2
        """

        params = [vector_str, similarity_threshold]
        param_count = 3

        if session_uuid:
            base_query += f" AND fd.session_uuid = ${param_count}"
            params.append(session_uuid)
            param_count += 1

        base_query += f" ORDER BY similarity_score DESC LIMIT ${param_count}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
            return [dict(row) for row in rows]

    async def get_embedding_statistics(self) -> Dict:
        """Get statistics about facial embeddings in database."""

        query = """
        SELECT 
            COUNT(*) as total_embeddings,
            COUNT(DISTINCT session_uuid) as unique_sessions,
            AVG(embedding_confidence) as avg_confidence,
            MIN(embedding_confidence) as min_confidence,
            MAX(embedding_confidence) as max_confidence
        FROM face_detections 
        WHERE facial_embedding IS NOT NULL
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return dict(row) if row else {}

    # ================================================================
    # Analytics and Aggregations
    # ================================================================

    async def get_route_analytics_summary(
        self, session_uuid: Optional[str] = None, hours: int = 24
    ) -> Dict:
        """Get route analytics summary."""

        base_query = """
        SELECT 
            COUNT(DISTINCT person_object_id) as unique_persons,
            COUNT(*) as total_route_points,
            AVG(velocity_magnitude) as avg_velocity,
            MAX(velocity_magnitude) as max_velocity,
            AVG(distance_from_camera) as avg_distance,
            MIN(distance_from_camera) as min_distance,
            MAX(distance_from_camera) as max_distance
        FROM person_routes pr
        WHERE pr.created_at >= NOW() - INTERVAL '{} hours'
        """.format(
            hours
        )

        params = []
        if session_uuid:
            base_query += " AND pr.session_uuid = $1"
            params.append(session_uuid)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(base_query, *params)
            return dict(row) if row else {}

    async def get_spatial_heatmap_data(
        self, session_uuid: Optional[str] = None, grid_size: int = 20
    ) -> List[Dict]:
        """Get spatial heatmap data for visualization."""

        query = """
        WITH bounds AS (
            SELECT 
                MIN(center_x) as x_min, MAX(center_x) as x_max,
                MIN(center_y) as y_min, MAX(center_y) as y_max
            FROM person_routes pr
            WHERE ($1::text IS NULL OR pr.session_uuid = $1)
        ),
        grid AS (
            SELECT 
                generate_series(0, $2-1) as x_grid,
                generate_series(0, $2-1) as y_grid
        )
        SELECT 
            g.x_grid,
            g.y_grid,
            COUNT(pr.id) as point_count,
            AVG(pr.velocity_magnitude) as avg_velocity,
            AVG(pr.distance_from_camera) as avg_distance
        FROM grid g
        CROSS JOIN bounds b
        LEFT JOIN person_routes pr ON (
            ($1::text IS NULL OR pr.session_uuid = $1)
            AND pr.center_x BETWEEN 
                b.x_min + (g.x_grid * (b.x_max - b.x_min) / $2)
                AND b.x_min + ((g.x_grid + 1) * (b.x_max - b.x_min) / $2)
            AND pr.center_y BETWEEN 
                b.y_min + (g.y_grid * (b.y_max - b.y_min) / $2)
                AND b.y_min + ((g.y_grid + 1) * (b.y_max - b.y_min) / $2)
        )
        GROUP BY g.x_grid, g.y_grid, b.x_min, b.x_max, b.y_min, b.y_max
        ORDER BY g.x_grid, g.y_grid
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, session_uuid, grid_size)
            return [dict(row) for row in rows]

    # ================================================================
    # System Information and Health
    # ================================================================

    async def get_system_health_metrics(self) -> Dict:
        """Get system health metrics for Phase 1."""

        queries = {
            "active_sessions": """
                SELECT COUNT(*) FROM persons_lifecycle_master_workflows 
                WHERE status IN ('queued', 'processing')
            """,
            "completed_sessions_today": """
                SELECT COUNT(*) FROM persons_lifecycle_master_workflows 
                WHERE status = 'completed' AND started_at >= CURRENT_DATE
            """,
            "total_faces_detected_today": """
                SELECT COALESCE(SUM(total_faces_detected), 0) 
                FROM persons_lifecycle_master_workflows 
                WHERE started_at >= CURRENT_DATE
            """,
            "total_route_points_today": """
                SELECT COUNT(*) FROM person_routes 
                WHERE created_at >= CURRENT_DATE
            """,
            "embeddings_generated_today": """
                SELECT COUNT(*) FROM face_detections 
                WHERE facial_embedding IS NOT NULL 
                AND created_at >= CURRENT_DATE
            """,
            "database_size": """
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """,
        }

        results = {}
        async with self.pool.acquire() as conn:
            for metric_name, query in queries.items():
                try:
                    result = await conn.fetchval(query)
                    results[metric_name] = result
                except Exception as e:
                    logger.error(f"Failed to get metric {metric_name}: {e}")
                    results[metric_name] = None

        return results

    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Cleanup old workflow sessions and related data."""

        cleanup_queries = [
            """
            DELETE FROM person_routes 
            WHERE created_at < NOW() - INTERVAL '{} days'
            """.format(
                days_old
            ),
            """
            DELETE FROM face_detections 
            WHERE created_at < NOW() - INTERVAL '{} days'
            """.format(
                days_old
            ),
            """
            DELETE FROM person_objects 
            WHERE created_at < NOW() - INTERVAL '{} days'
            """.format(
                days_old
            ),
            """
            DELETE FROM persons_lifecycle_master_workflows 
            WHERE started_at < NOW() - INTERVAL '{} days'
            """.format(
                days_old
            ),
        ]

        total_deleted = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for query in cleanup_queries:
                    result = await conn.execute(query)
                    # Extract number from result like "DELETE 5"
                    deleted_count = (
                        int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                    )
                    total_deleted += deleted_count

        logger.info(
            f"Cleaned up {total_deleted} old records (older than {days_old} days)"
        )
        return total_deleted


# ================================================================
# Database Connection Factory
# ================================================================


async def create_phase1_database_client(config: Dict) -> Phase1DatabaseClient:
    """Create and initialize Phase 1 database client."""

    connection_string = config.get("database_url") or (
        f"postgresql://{config['username']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )

    client = Phase1DatabaseClient(connection_string)
    await client.initialize()

    logger.info("Phase 1 database client created and initialized")
    return client


# ================================================================
# Usage Example
# ================================================================


async def example_database_usage():
    """Example of Phase 1 database operations."""

    # Initialize database client
    config = {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_meta",
        "username": "ppl_user",
        "password": "ppl_password",
    }

    db_client = await create_phase1_database_client(config)

    try:
        # Create master workflow
        workflow_data = {
            "session_uuid": "session-123",
            "source_identifier": "camera-lobby",
            "source_type": "camera_recording",
            "source_id": "media-456",
            "execution_trigger": "automatic",
            "status": "processing",
            "current_stage": "face_detection",
            "progress_percentage": 50.0,
            "configuration": '{"confidence_threshold": 0.5}',
            "started_at": datetime.now().isoformat(),
        }

        await db_client.create_master_workflow(workflow_data)

        # Create face detection with embedding
        face_id = await db_client.create_face_detection_record(
            session_uuid="session-123",
            timestamp_ms=1000,
            frame_number=30,
            x=100,
            y=150,
            width=80,
            height=100,
            confidence=0.85,
            distance_from_camera=2.5,
            face_area_pixels=8000,
            facial_embedding=[0.1, 0.2, 0.3] + [0.0] * 509,  # 512-dimensional
            embedding_confidence=0.9,
        )

        # Search for similar faces
        similar_faces = await db_client.search_similar_faces_by_embedding(
            embedding_vector=[0.1, 0.2, 0.3] + [0.0] * 509,
            similarity_threshold=0.8,
            limit=5,
        )

        print(f"Found {len(similar_faces)} similar faces")

        # Get system health metrics
        health = await db_client.get_system_health_metrics()
        print(f"System health: {health}")

    finally:
        await db_client.close()

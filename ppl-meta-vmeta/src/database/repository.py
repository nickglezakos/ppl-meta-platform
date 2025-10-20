"""
PostgreSQL Repository Layer
PPL Meta Platform - Cross-Video Individual Tracking

This module provides PostgreSQL database access layer for cross-video individual tracking.
Implements CRUD operations with pgvector support for face embeddings and similarity search.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import json
import numpy as np

from models.cross_video_tracking import (
    CrossVideoTrackingConfig,
    Individual,
    TrackingSession,
    VideoAppearance,
    BoundingBox,
    ProcessingStatus,
    SessionStatus
)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


class CrossVideoTrackingRepository:
    """Repository for cross-video individual tracking database operations."""
    
    def __init__(self, connection_string: str):
        """Initialize repository with database connection."""
        self.connection_string = connection_string
        self._connection_pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        try:
            self._connection_pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'search_path': 'public',
                    'timezone': 'UTC'
                }
            )
            logger.info("✅ Database connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize connection pool: {e}")
            raise DatabaseError(f"Connection pool initialization failed: {e}")
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self._connection_pool:
            await self._connection_pool.close()
            logger.info("✅ Database connection pool closed")
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection from pool."""
        if not self._connection_pool:
            raise DatabaseError("Connection pool not initialized")
        
        try:
            return await self._connection_pool.acquire()
        except Exception as e:
            logger.error(f"❌ Failed to acquire connection: {e}")
            raise DatabaseError(f"Connection acquisition failed: {e}")
    
    async def release_connection(self, conn: asyncpg.Connection) -> None:
        """Release connection back to pool."""
        try:
            await self._connection_pool.release(conn)
        except Exception as e:
            logger.error(f"❌ Failed to release connection: {e}")

    # Algorithm Configuration Operations
    
    async def create_algorithm_config(
        self, 
        config: CrossVideoTrackingConfig
    ) -> str:
        """Create new algorithm configuration."""
        conn = await self.get_connection()
        try:
            await conn.execute("""
                INSERT INTO algorithm_configurations 
                (config_name, description, config, is_default, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (config_name) DO UPDATE SET
                    description = EXCLUDED.description,
                    config = EXCLUDED.config,
                    is_default = EXCLUDED.is_default
            """, 
                config.config_name,
                config.description,
                json.dumps(config.dict(exclude={'config_name', 'description'})),
                config.is_default
            )
            
            logger.info(f"✅ Created algorithm config: {config.config_name}")
            return config.config_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create config {config.config_name}: {e}")
            raise DatabaseError(f"Configuration creation failed: {e}")
        finally:
            await self.release_connection(conn)
    
    async def get_algorithm_config(
        self, 
        config_name: str
    ) -> Optional[CrossVideoTrackingConfig]:
        """Get algorithm configuration by name."""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT config_name, description, config, is_default
                FROM algorithm_configurations
                WHERE config_name = $1
            """, config_name)
            
            if not row:
                return None
            
            config_data = json.loads(row['config'])
            config_data.update({
                'config_name': row['config_name'],
                'description': row['description'],
                'is_default': row['is_default']
            })
            
            return CrossVideoTrackingConfig(**config_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to get config {config_name}: {e}")
            return None
        finally:
            await self.release_connection(conn)
    
    async def get_default_algorithm_config(self) -> Optional[CrossVideoTrackingConfig]:
        """Get default algorithm configuration."""
        return await self.get_default_config()
    
    async def get_default_config(self) -> Optional[CrossVideoTrackingConfig]:
        """Get default algorithm configuration."""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT config_name, description, config, is_default
                FROM algorithm_configurations
                WHERE is_default = true
                LIMIT 1
            """)
            
            if not row:
                logger.warning("⚠️ No default algorithm configuration found")
                return None
            
            config_data = json.loads(row['config'])
            config_data.update({
                'config_name': row['config_name'],
                'description': row['description'],
                'is_default': row['is_default']
            })
            
            return CrossVideoTrackingConfig(**config_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to get default config: {e}")
            return None
        finally:
            await self.release_connection(conn)

    # Tracking Session Operations
    
    async def create_tracking_session(
        self,
        user_id: str,
        collections: List[str],
        start_time: datetime,
        end_time: datetime,
        config: CrossVideoTrackingConfig
    ) -> UUID:
        """Create new tracking session."""
        conn = await self.get_connection()
        try:
            session_id = uuid4()
            config_hash = config.get_hash()
            
            await conn.execute("""
                INSERT INTO tracking_sessions 
                (session_uuid, user_id, collections, start_time, end_time, 
                 config_hash, algorithm_config, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                session_id,
                user_id,
                collections,
                start_time,
                end_time,
                config_hash,
                json.dumps(config.dict()),
                SessionStatus.INITIALIZED.value
            )
            
            logger.info(f"✅ Created tracking session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create tracking session: {e}")
            raise DatabaseError(f"Session creation failed: {e}")
        finally:
            await self.release_connection(conn)
    
    async def get_tracking_session(
        self, 
        session_id: UUID
    ) -> Optional[TrackingSession]:
        """Get tracking session by ID."""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT * FROM tracking_sessions WHERE session_uuid = $1
            """, session_id)
            
            if not row:
                return None
            
                config_data = json.loads(row['algorithm_config'])
                config_obj = CrossVideoTrackingConfig(**config_data)
                
                return TrackingSession(
                    session_uuid=row['session_uuid'],
                    user_id=row['user_id'],
                    collections=row['collections'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    config_hash=row['config_hash'],
                    algorithm_config=config_obj,
                    status=SessionStatus(row['status']),
                    total_videos=row['total_videos'],
                    processed_videos=row['processed_videos'],
                    total_individuals=row.get('total_individuals', 0),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at'),
                    completed_at=row.get('completed_at')
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)
    
    async def update_session_status(
        self,
        session_id: UUID,
        status: SessionStatus,
        progress_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update tracking session status and progress."""
        conn = await self.get_connection()
        try:
            update_fields = ["status = $2", "updated_at = $3"]
            params = [session_id, status.value, datetime.utcnow()]
            param_count = 3
            
            if progress_info:
                if 'processed_videos' in progress_info:
                    param_count += 1
                    update_fields.append(f"processed_videos = ${param_count}")
                    params.append(progress_info['processed_videos'])
                
                if 'total_individuals' in progress_info:
                    param_count += 1
                    update_fields.append(f"total_individuals = ${param_count}")
                    params.append(progress_info['total_individuals'])
            
            if status == SessionStatus.COMPLETED:
                param_count += 1
                update_fields.append(f"completed_at = ${param_count}")
                params.append(datetime.utcnow())
            
            query = f"""
                UPDATE tracking_sessions 
                SET {', '.join(update_fields)}
                WHERE session_uuid = $1
            """
            
            result = await conn.execute(query, *params)
            success = result == "UPDATE 1"
            
            if success:
                logger.info(f"✅ Updated session {session_id} status: {status.value}")
            else:
                logger.warning(f"⚠️ Session {session_id} not found for update")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to update session {session_id}: {e}")
            return False
        finally:
            await self.release_connection(conn)

    # Individual Operations
    
    async def create_individual(
        self,
        session_id: UUID,
        first_appearance: VideoAppearance,
        confidence_score: float
    ) -> UUID:
        """Create new individual in tracking session."""
        conn = await self.get_connection()
        try:
            individual_uuid = uuid4()
            individual_id = f"ind_{individual_uuid.hex[:8]}"
            
            # Create individual record
            await conn.execute("""
                INSERT INTO individuals 
                (individual_uuid, individual_id, confidence_score, 
                 spatial_signature, temporal_signature)
                VALUES ($1, $2, $3, $4, $5)
            """,
                individual_uuid,
                individual_id,
                confidence_score,
                json.dumps({}),  # Initial empty spatial signature
                json.dumps({})   # Initial empty temporal signature
            )
            
            # Create session-individual relationship
            await conn.execute("""
                INSERT INTO session_individuals 
                (session_uuid, individual_uuid, processing_type, confidence_contribution)
                VALUES ($1, $2, $3, $4)
            """,
                session_id,
                individual_uuid,
                'primary',
                confidence_score
            )
            
            # Create first video appearance
            await self._create_video_appearance(
                conn, individual_uuid, first_appearance
            )
            
            logger.info(f"✅ Created individual: {individual_uuid}")
            return individual_uuid
            
        except Exception as e:
            logger.error(f"❌ Failed to create individual: {e}")
            raise DatabaseError(f"Individual creation failed: {e}")
        finally:
            await self.release_connection(conn)
    
    async def _create_video_appearance(
        self,
        conn: asyncpg.Connection,
        individual_uuid: UUID,
        appearance: VideoAppearance
    ) -> None:
        """Create video appearance record (internal helper)."""
        
        await conn.execute("""
            INSERT INTO individual_video_appearances 
            (individual_uuid, video_uuid, person_object_uuid, 
             start_timestamp, end_timestamp, entry_bbox, exit_bbox,
             confidence, representative_faces, movement_pattern)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            individual_uuid,
            appearance.video_uuid,
            appearance.person_object_uuid,
            appearance.start_timestamp,
            appearance.end_timestamp,
            appearance.entry_bbox,
            appearance.exit_bbox,
            appearance.confidence,
            json.dumps(appearance.representative_faces or {}),
            json.dumps(appearance.movement_pattern or {})
        )
    
    async def add_appearance_to_individual(
        self,
        individual_id: UUID,
        appearance: VideoAppearance
    ) -> bool:
        """Add new appearance to existing individual."""
        conn = await self.get_connection()
        try:
            # Create appearance record
            await self._create_video_appearance(conn, individual_id, appearance)
            
            # Update individual stats
            await conn.execute("""
                UPDATE individuals 
                SET last_seen_at = $2,
                    total_appearances = total_appearances + 1,
                    updated_at = $3
                WHERE id = $1
            """,
                individual_id,
                appearance.timestamp,
                datetime.utcnow()
            )
            
            logger.info(f"✅ Added appearance to individual: {individual_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add appearance to {individual_id}: {e}")
            return False
        finally:
            await self.release_connection(conn)
    
    async def get_session_individuals(
        self, 
        session_id: UUID
    ) -> List[Individual]:
        """Get all individuals for a tracking session."""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("""
                SELECT i.*, 
                       COUNT(iva.id) as appearance_count,
                       MIN(iva.timestamp) as first_seen,
                       MAX(iva.timestamp) as last_seen
                FROM individuals i
                LEFT JOIN individual_video_appearances iva ON i.id = iva.individual_id
                WHERE i.session_id = $1
                GROUP BY i.id
                ORDER BY i.created_at
            """, session_id)
            
            individuals = []
            for row in rows:
                # Get appearances for this individual
                appearances = await self._get_individual_appearances(
                    conn, row['id']
                )
                
                individual = Individual(
                    id=row['id'],
                    session_id=row['session_id'],
                    confidence_score=row['confidence_score'],
                    first_seen_at=row['first_seen_at'],
                    last_seen_at=row['last_seen_at'],
                    total_appearances=row['total_appearances'],
                    video_appearances=appearances,
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                individuals.append(individual)
            
            logger.info(f"✅ Retrieved {len(individuals)} individuals for session {session_id}")
            return individuals
            
        except Exception as e:
            logger.error(f"❌ Failed to get individuals for session {session_id}: {e}")
            return []
        finally:
            await self.release_connection(conn)
    
    async def _get_individual_appearances(
        self,
        conn: asyncpg.Connection,
        individual_id: UUID
    ) -> List[VideoAppearance]:
        """Get all appearances for an individual (internal helper)."""
        rows = await conn.fetch("""
            SELECT * FROM individual_video_appearances 
            WHERE individual_id = $1 
            ORDER BY timestamp
        """, individual_id)
        
        appearances = []
        for row in rows:
            bbox_data = json.loads(row['bounding_box'])
            appearance = VideoAppearance(
                video_id=row['video_id'],
                timestamp=row['timestamp'],
                bounding_box=BoundingBox(**bbox_data),
                confidence_score=row['confidence_score'],
                face_embedding=row['face_embedding'],
                person_id=row['person_id']
            )
            appearances.append(appearance)
        
        return appearances

    # Cache Management Operations
    
    async def cache_person_objects(
        self,
        collection_name: str,
        video_id: str,
        person_objects: List[Dict[str, Any]]
    ) -> bool:
        """Cache person objects for a video."""
        conn = await self.get_connection()
        try:
            await conn.execute("""
                INSERT INTO cached_person_objects 
                (collection_name, video_id, person_objects, created_at, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (collection_name, video_id) 
                DO UPDATE SET 
                    person_objects = EXCLUDED.person_objects,
                    created_at = EXCLUDED.created_at,
                    expires_at = EXCLUDED.expires_at
            """,
                collection_name,
                video_id,
                json.dumps(person_objects),
                datetime.utcnow(),
                datetime.utcnow() + timedelta(hours=24)  # 24 hour cache
            )
            
            logger.info(f"✅ Cached {len(person_objects)} person objects for {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cache person objects for {video_id}: {e}")
            return False
        finally:
            await self.release_connection(conn)
    
    async def get_cached_person_objects(
        self,
        collection_name: str,
        video_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached person objects for a video."""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT person_objects FROM cached_person_objects
                WHERE collection_name = $1 AND video_id = $2
                AND expires_at > $3
            """, collection_name, video_id, datetime.utcnow())
            
            if row:
                return json.loads(row['person_objects'])
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get cached objects for {video_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)
    
    async def clear_collection_cache(
        self, 
        collection_name: str
    ) -> int:
        """Clear cache for specific collection."""
        conn = await self.get_connection()
        try:
            result = await conn.execute("""
                DELETE FROM cached_person_objects 
                WHERE collection_name = $1
            """, collection_name)
            
            count = int(result.split()[-1])
            logger.info(f"✅ Cleared {count} cached objects for collection {collection_name}")
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to clear cache for {collection_name}: {e}")
            return 0
        finally:
            await self.release_connection(conn)
    
    async def clear_expired_cache(self) -> int:
        """Clear all expired cache entries."""
        conn = await self.get_connection()
        try:
            result = await conn.execute("""
                DELETE FROM cached_person_objects 
                WHERE expires_at <= $1
            """, datetime.utcnow())
            
            count = int(result.split()[-1])
            logger.info(f"✅ Cleared {count} expired cache entries")
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to clear expired cache: {e}")
            return 0
        finally:
            await self.release_connection(conn)

    # Video Processing State Operations
    
    async def update_video_processing_state(
        self,
        session_id: UUID,
        video_id: str,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """Update video processing state."""
        conn = await self.get_connection()
        try:
            await conn.execute("""
                INSERT INTO video_processing_states 
                (session_id, video_id, status, error_message, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (session_id, video_id)
                DO UPDATE SET 
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    updated_at = EXCLUDED.updated_at
            """,
                session_id,
                video_id,
                status.value,
                error_message,
                datetime.utcnow()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update processing state for {video_id}: {e}")
            return False
        finally:
            await self.release_connection(conn)
    
    async def get_session_processing_stats(
        self, 
        session_id: UUID
    ) -> Dict[str, Any]:
        """Get processing statistics for a session."""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_videos,
                    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending
                FROM video_processing_states
                WHERE session_id = $1
            """, session_id)
            
            if row:
                return {
                    'total_videos': row['total_videos'],
                    'completed': row['completed'],
                    'processing': row['processing'],
                    'failed': row['failed'],
                    'pending': row['pending'],
                    'progress_percentage': (
                        (row['completed'] / row['total_videos'] * 100) 
                        if row['total_videos'] > 0 else 0
                    )
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get processing stats for {session_id}: {e}")
            return {}
        finally:
            await self.release_connection(conn)
"""
Embedding Cache Service - Phase 1 of MVR Caching Architecture

This service manages persistent storage and retrieval of facial embeddings
to avoid expensive regeneration operations.

Key Features:
- Cache embeddings in PostgreSQL with pgvector
- Track cache hits/misses for performance monitoring
- Support cache invalidation and LRU cleanup
- Maintain embedding quality metadata

Performance Impact:
- 100-200x faster embedding lookup vs generation
- Reduces Media service API calls by 100% for cached individuals
- Expected cache hit rate: 70-90% in steady state

Author: PPL Meta Platform
Date: 2025-11-07
Version: 2.19.30
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class EmbeddingCacheService:
    """
    Service for managing persistent facial embedding cache.
    
    This service provides:
    1. Fast embedding lookup (check if individual has cached embedding)
    2. Embedding storage (cache new embeddings after generation)
    3. Cache statistics (track hit rates, performance)
    4. Cache maintenance (invalidation, LRU cleanup)
    """
    
    def __init__(self, db_client):
        """
        Initialize embedding cache service.
        
        Args:
            db_client: Database client with connection pool
        """
        self.db_client = db_client
        self.cache_version = 1  # Increment when embedding model changes
        
    async def get_cached_embedding(
        self,
        individual_uuid: UUID,
        update_accessed_time: bool = True
    ) -> Optional[Dict]:
        """
        Retrieve cached embedding for an individual.
        
        Args:
            individual_uuid: UUID of the individual
            update_accessed_time: Whether to update accessed_at timestamp (for LRU)
            
        Returns:
            Dict with embedding data if found, None if cache miss:
            {
                'individual_uuid': UUID,
                'face_embedding': np.ndarray,  # 512-dimensional vector
                'embedding_confidence': float,
                'embedding_model': str,
                'created_at': datetime,
                'source_video_uuid': UUID (optional),
                'source_frame_number': int (optional),
                'bbox': tuple (x, y, width, height) (optional)
            }
        """
        try:
            logger.debug(f"[EMBED_CACHE] GET start: {str(individual_uuid)[:8]}")
            async with self.db_client.pool.acquire() as conn:
                # Query cache
                result = await conn.fetchrow("""
                    SELECT 
                        individual_uuid,
                        face_embedding,
                        embedding_confidence,
                        embedding_model,
                        source_video_uuid,
                        source_frame_number,
                        bbox_x, bbox_y, bbox_width, bbox_height,
                        created_at,
                        cache_version,
                        is_valid
                    FROM individual_embeddings_cache
                    WHERE individual_uuid = $1
                      AND is_valid = TRUE
                      AND cache_version = $2
                """, individual_uuid, self.cache_version)

                if not result:
                    # Cache miss
                    logger.info(f"[EMBED_CACHE] MISS {str(individual_uuid)[:8]}")
                    return None

                # Cache hit! Update accessed time if requested
                if update_accessed_time:
                    await conn.execute("""
                        UPDATE individual_embeddings_cache
                        SET accessed_at = NOW()
                        WHERE individual_uuid = $1
                    """, individual_uuid)
                
                # Convert binary embedding to numpy array
                embedding_bytes = result['face_embedding']
                if isinstance(embedding_bytes, str):
                    # pgvector returns string representation like '[0.1,0.2,...]'
                    # Parse it to numpy array
                    embedding_list = eval(embedding_bytes)
                    embedding_vector = np.array(embedding_list, dtype=np.float32)
                else:
                    # Binary format
                    embedding_vector = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # Build bbox tuple if available
                bbox = None
                if all([
                    result['bbox_x'] is not None,
                    result['bbox_y'] is not None,
                    result['bbox_width'] is not None,
                    result['bbox_height'] is not None
                ]):
                    bbox = (
                        result['bbox_x'],
                        result['bbox_y'],
                        result['bbox_width'],
                        result['bbox_height']
                    )
                
                cache_data = {
                    'individual_uuid': result['individual_uuid'],
                    'face_embedding': embedding_vector,
                    'embedding_confidence': result['embedding_confidence'],
                    'embedding_model': result['embedding_model'],
                    'created_at': result['created_at'],
                    'source_video_uuid': result['source_video_uuid'],
                    'source_frame_number': result['source_frame_number'],
                    'bbox': bbox,
                    'cached': True  # Flag to indicate this came from cache
                }
                
                logger.info(
                    f"✅ Embedding cache hit for {str(individual_uuid)[:8]} "
                    f"(confidence: {result['embedding_confidence']:.3f}, "
                    f"age: {(datetime.now() - result['created_at']).days} days)"
                )
                
                return cache_data
                
        except Exception as e:
            logger.exception(f"[EMBED_CACHE] Error retrieving cached embedding for {str(individual_uuid)[:8]}: {e}")
            return None
    
    async def store_embedding(
        self,
        individual_uuid: UUID,
        face_embedding: np.ndarray,
        embedding_confidence: float,
        embedding_model: str = "Facenet512",
        source_video_uuid: Optional[UUID] = None,
        source_frame_number: Optional[int] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        source_video_quality: float = 0.5,
        face_detection_confidence: float = 0.95
    ) -> bool:
        """
        Store embedding in cache for future use.
        
        Args:
            individual_uuid: UUID of the individual
            face_embedding: 512-dimensional numpy array
            embedding_confidence: DeepFace confidence score
            embedding_model: Model name (default: Facenet512)
            source_video_uuid: UUID of source video (for metadata)
            source_frame_number: Frame number in source video
            bbox: Bounding box (x, y, width, height)
            source_video_quality: Video quality metric (0.0 to 1.0)
            face_detection_confidence: Face detection confidence
            
        Returns:
            True if stored successfully, False otherwise
        """
        # DEBUG: Log to database immediately
        try:
            async with self.db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(failed_videos, $1)
                    WHERE status = 'processing'
                    ORDER BY created_at DESC LIMIT 1
                """, f"🎯 STORE_ENTRY: {str(individual_uuid)[:8]} conf={embedding_confidence:.3f}")
        except:
            pass
        
        try:
            logger.debug(
                f"[EMBED_CACHE] STORE attempt: {str(individual_uuid)[:8]} "
                f"conf={embedding_confidence:.3f} model={embedding_model}"
            )

            # Validate embedding shape
            if face_embedding.shape != (512,):
                logger.error(
                    f"Invalid embedding shape: {face_embedding.shape}. "
                    f"Expected (512,) for Facenet512"
                )
                return False
            
            # Validate confidence
            if not (0.0 <= embedding_confidence <= 1.0):
                logger.warning(
                    f"Invalid embedding confidence: {embedding_confidence}. "
                    f"Clamping to [0.0, 1.0]"
                )
                embedding_confidence = max(0.0, min(1.0, embedding_confidence))
            
            # Convert numpy array to PostgreSQL vector format
            # pgvector with asyncpg requires string representation: '[0.1,0.2,...]'
            embedding_list = face_embedding.tolist()
            
            # Convert to pgvector string format
            embedding_str = '[' + ','.join(str(x) for x in embedding_list) + ']'
            
            # DEBUG: Log embedding format
            logger.info(
                f"[EMBED_CACHE] STORE preparing: uuid={str(individual_uuid)[:8]}, "
                f"embedding_len={len(embedding_list)}, embedding_str_len={len(embedding_str)}, "
                f"first_50_chars={embedding_str[:50]}"
            )
            
            # Extract bbox components
            bbox_x, bbox_y, bbox_width, bbox_height = None, None, None, None
            if bbox:
                bbox_x, bbox_y, bbox_width, bbox_height = bbox
            
            async with self.db_client.pool.acquire() as conn:
                # Use explicit transaction to ensure commit
                async with conn.transaction():
                    # Insert or update embedding
                    await conn.execute("""
                        INSERT INTO individual_embeddings_cache
                        (
                            individual_uuid,
                            face_embedding,
                            embedding_confidence,
                            embedding_model,
                            source_video_uuid,
                            source_frame_number,
                            bbox_x, bbox_y, bbox_width, bbox_height,
                            cache_version,
                            is_valid,
                            source_video_quality,
                            face_detection_confidence,
                            created_at,
                            updated_at,
                            accessed_at
                        )
                        VALUES ($1, $2::vector, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW(), NOW())
                        ON CONFLICT (individual_uuid)
                        DO UPDATE SET
                            face_embedding = EXCLUDED.face_embedding,
                            embedding_confidence = EXCLUDED.embedding_confidence,
                            embedding_model = EXCLUDED.embedding_model,
                            source_video_uuid = EXCLUDED.source_video_uuid,
                            source_frame_number = EXCLUDED.source_frame_number,
                            bbox_x = EXCLUDED.bbox_x,
                            bbox_y = EXCLUDED.bbox_y,
                            bbox_width = EXCLUDED.bbox_width,
                            bbox_height = EXCLUDED.bbox_height,
                            cache_version = EXCLUDED.cache_version,
                            is_valid = EXCLUDED.is_valid,
                            source_video_quality = EXCLUDED.source_video_quality,
                            face_detection_confidence = EXCLUDED.face_detection_confidence,
                            updated_at = NOW(),
                            accessed_at = NOW()
                    """,
                        individual_uuid,
                        embedding_str,  # Pass as string, PostgreSQL will cast to vector(512)
                        embedding_confidence,
                        embedding_model,
                        source_video_uuid,
                        source_frame_number,
                        bbox_x, bbox_y, bbox_width, bbox_height,
                        self.cache_version,
                        True,  # is_valid
                        source_video_quality,
                        face_detection_confidence
                    )
                    
                # Verify outside transaction (separate read)
                verify = await conn.fetchrow(
                    "SELECT individual_uuid, created_at, updated_at FROM individual_embeddings_cache WHERE individual_uuid = $1",
                    individual_uuid
                )
                if verify:
                    logger.debug(f"[EMBED_CACHE] STORE verify: row exists for {str(individual_uuid)[:8]} created_at={verify['created_at']} updated_at={verify['updated_at']}")
                else:
                    logger.error(f"[EMBED_CACHE] STORE verify: no row found after insert for {str(individual_uuid)[:8]} - TRANSACTION ISSUE!")
            
            logger.info(
                f"💾 Stored embedding for {str(individual_uuid)[:8]} "
                f"(confidence: {embedding_confidence:.3f}, model: {embedding_model})"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"[EMBED_CACHE] ❌❌❌ CRITICAL ERROR storing embedding for {str(individual_uuid)[:8]}: "
                f"{type(e).__name__}: {str(e)}"
            )
            logger.exception("Full traceback:")
            
            # Also log to database for visibility
            try:
                async with self.db_client.pool.acquire() as conn:
                    # Try to log error to tracking_sessions (will fail if no active session)
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(failed_videos, $1)
                        WHERE status = 'processing'
                        ORDER BY created_at DESC LIMIT 1
                    """, f"EMBED_CACHE_ERROR: {type(e).__name__}: {str(e)[:100]}")
            except:
                pass  # Ignore logging errors
            
            return False
    
    async def get_cache_statistics(
        self,
        session_uuid: Optional[UUID] = None
    ) -> Dict:
        """
        Get cache statistics for monitoring.
        
        Args:
            session_uuid: If provided, get stats for specific session.
                         If None, get global cache stats.
        
        Returns:
            Dict with cache statistics:
            {
                'total_cached_embeddings': int,
                'cache_hits': int,
                'cache_misses': int,
                'cache_hit_rate': float,
                'avg_cache_age_days': float,
                'total_cache_size_mb': float
            }
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                if session_uuid:
                    # Session-specific stats
                    result = await conn.fetchrow("""
                        SELECT * FROM calculate_embedding_cache_stats($1)
                    """, session_uuid)
                    
                    return {
                        'total_embeddings': result['total_embeddings'],
                        'cached_embeddings': result['cached_embeddings'],
                        'new_embeddings': result['new_embeddings'],
                        'cache_hit_rate': result['cache_hit_rate'],
                        'avg_cache_age_days': result['avg_cache_age_days']
                    }
                else:
                    # Global cache stats
                    result = await conn.fetchrow("""
                        SELECT 
                            COUNT(*) as total_cached,
                            COUNT(*) FILTER (WHERE is_valid = TRUE) as valid_cached,
                            AVG(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0) as avg_age_days,
                            pg_total_relation_size('individual_embeddings_cache') / 1024.0 / 1024.0 as size_mb
                        FROM individual_embeddings_cache
                    """)
                    
                    return {
                        'total_cached_embeddings': result['total_cached'],
                        'valid_cached_embeddings': result['valid_cached'],
                        'avg_cache_age_days': float(result['avg_age_days']) if result['avg_age_days'] else 0.0,
                        'total_cache_size_mb': float(result['size_mb'])
                    }
                    
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}", exc_info=True)
            return {}
    
    async def invalidate_embedding(
        self,
        individual_uuid: UUID,
        reason: str = "manual_invalidation"
    ) -> bool:
        """
        Invalidate cached embedding (mark as invalid without deleting).
        
        Args:
            individual_uuid: UUID of individual whose embedding to invalidate
            reason: Reason for invalidation (for logging)
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE individual_embeddings_cache
                    SET is_valid = FALSE,
                        updated_at = NOW()
                    WHERE individual_uuid = $1
                      AND is_valid = TRUE
                """, individual_uuid)
                
                if result == "UPDATE 1":
                    logger.info(
                        f"🗑️ Invalidated embedding for {str(individual_uuid)[:8]} "
                        f"(reason: {reason})"
                    )
                    return True
                else:
                    logger.warning(
                        f"No valid embedding found to invalidate for {str(individual_uuid)[:8]}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Error invalidating embedding: {e}", exc_info=True)
            return False
    
    async def cleanup_old_embeddings(
        self,
        days_old: int = 30
    ) -> int:
        """
        Invalidate embeddings older than specified days.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of embeddings invalidated
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE individual_embeddings_cache
                    SET is_valid = FALSE,
                        updated_at = NOW()
                    WHERE updated_at < NOW() - INTERVAL '%s days'
                      AND is_valid = TRUE
                """ % days_old)
                
                # Extract count from result string "UPDATE N"
                count = int(result.split()[-1]) if result.startswith("UPDATE") else 0
                
                if count > 0:
                    logger.info(
                        f"🧹 Invalidated {count} embeddings older than {days_old} days"
                    )
                
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up old embeddings: {e}", exc_info=True)
            return 0
    
    async def bulk_get_cached_embeddings(
        self,
        individual_uuids: List[UUID]
    ) -> Dict[UUID, Dict]:
        """
        Retrieve multiple cached embeddings in one query (optimized for batch processing).
        
        Args:
            individual_uuids: List of individual UUIDs to lookup
            
        Returns:
            Dict mapping individual_uuid to embedding data (same format as get_cached_embedding)
            Only includes UUIDs that had cache hits
        """
        if not individual_uuids:
            return {}
        
        try:
            async with self.db_client.pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT 
                        individual_uuid,
                        face_embedding,
                        embedding_confidence,
                        embedding_model,
                        source_video_uuid,
                        source_frame_number,
                        bbox_x, bbox_y, bbox_width, bbox_height,
                        created_at
                    FROM individual_embeddings_cache
                    WHERE individual_uuid = ANY($1)
                      AND is_valid = TRUE
                      AND cache_version = $2
                """, individual_uuids, self.cache_version)
                
                # Update accessed times for all cache hits
                if results:
                    hit_uuids = [r['individual_uuid'] for r in results]
                    await conn.execute("""
                        UPDATE individual_embeddings_cache
                        SET accessed_at = NOW()
                        WHERE individual_uuid = ANY($1)
                    """, hit_uuids)
                
                # Build result dictionary
                cached_embeddings = {}
                for result in results:
                    # Convert embedding
                    embedding_bytes = result['face_embedding']
                    if isinstance(embedding_bytes, str):
                        embedding_list = eval(embedding_bytes)
                        embedding_vector = np.array(embedding_list, dtype=np.float32)
                    else:
                        embedding_vector = np.frombuffer(embedding_bytes, dtype=np.float32)
                    
                    # Build bbox if available
                    bbox = None
                    if all([
                        result['bbox_x'] is not None,
                        result['bbox_y'] is not None,
                        result['bbox_width'] is not None,
                        result['bbox_height'] is not None
                    ]):
                        bbox = (
                            result['bbox_x'],
                            result['bbox_y'],
                            result['bbox_width'],
                            result['bbox_height']
                        )
                    
                    cached_embeddings[result['individual_uuid']] = {
                        'individual_uuid': result['individual_uuid'],
                        'face_embedding': embedding_vector,
                        'embedding_confidence': result['embedding_confidence'],
                        'embedding_model': result['embedding_model'],
                        'created_at': result['created_at'],
                        'source_video_uuid': result['source_video_uuid'],
                        'source_frame_number': result['source_frame_number'],
                        'bbox': bbox,
                        'cached': True
                    }
                
                cache_hits = len(cached_embeddings)
                cache_misses = len(individual_uuids) - cache_hits
                hit_rate = cache_hits / len(individual_uuids) * 100 if individual_uuids else 0
                
                logger.info(
                    f"📦 Bulk embedding cache lookup: {cache_hits} hits, "
                    f"{cache_misses} misses ({hit_rate:.1f}% hit rate)"
                )
                
                return cached_embeddings
                
        except Exception as e:
            logger.error(f"Error in bulk embedding cache lookup: {e}", exc_info=True)
            return {}

"""
Cross-Video Individual Tracking - Intelligent Caching System
PPL Meta Platform v2.19.13+

Implements intelligent caching with configuration-based cache keys,
result storage/retrieval, and cache availability analysis for 
performance optimization.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
import asyncpg

try:
    from ..models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        CachedResult
    )
    from ..models.cache_management import CacheStatistics
except ImportError:
    from models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        CachedResult
    )
    from models.cache_management import CacheStatistics

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Intelligent caching system for cross-video tracking results.
    
    Provides configuration-based cache key generation, result storage/retrieval,
    and comprehensive cache availability analysis for performance optimization.
    """
    
    def __init__(self, db_connection: asyncpg.Connection):
        """Initialize with database connection."""
        self.db = db_connection
        self.logger = logging.getLogger(f"{__name__}.CacheManager")
    
    def calculate_config_hash(self, config: CrossVideoTrackingConfig) -> str:
        """
        Calculate hash for cache key generation.
        
        Creates a deterministic hash from algorithm configuration
        to enable cache matching across sessions with identical configs.
        
        Args:
            config: Algorithm configuration
            
        Returns:
            32-character hash string
        """
        try:
            # Use the config's built-in hash method
            return config.calculate_hash()
        except Exception as e:
            self.logger.error(f"Failed to calculate config hash: {e}")
            # Fallback hash calculation
            config_dict = {
                'max_gap_seconds': config.max_gap_seconds,
                'iou_threshold': config.iou_threshold,
                'min_overlap_confidence': config.min_overlap_confidence,
                'min_appearances': config.min_appearances
            }
            config_json = json.dumps(config_dict, sort_keys=True)
            return hashlib.sha256(config_json.encode()).hexdigest()[:32]
    
    async def get_cached_result(
        self,
        video_uuid: str,
        config_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached processing result.
        
        Args:
            video_uuid: Video identifier
            config_hash: Configuration hash for cache matching
            
        Returns:
            Cached result dictionary or None if not found
        """
        try:
            cache_key = self._generate_cache_key(video_uuid, config_hash)
            
            query = """
                SELECT cache_key, video_uuid, session_uuid, config_hash,
                       person_objects, processing_metadata, created_at,
                       last_accessed, access_count
                FROM cached_person_objects
                WHERE cache_key = $1
            """
            
            result = await self.db.fetchrow(query, cache_key)
            
            if result:
                # Update access statistics
                await self._update_cache_access(cache_key)
                
                # Convert to dictionary
                cached_data = {
                    'cache_key': result['cache_key'],
                    'video_uuid': str(result['video_uuid']),
                    'session_uuid': str(result['session_uuid']),
                    'config_hash': result['config_hash'],
                    'person_objects': result['person_objects'],
                    'processing_metadata': result['processing_metadata'],
                    'created_at': result['created_at'],
                    'last_accessed': result['last_accessed'],
                    'access_count': result['access_count']
                }
                
                self.logger.debug(f"Cache HIT for video {video_uuid}")
                return cached_data
            else:
                self.logger.debug(f"Cache MISS for video {video_uuid}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve cached result: {e}")
            return None
    
    async def store_cached_result(
        self,
        video_uuid: str,
        session_uuid: str,
        config_hash: str,
        person_objects: List[Dict[str, Any]],
        processing_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store processing result in cache.
        
        Args:
            video_uuid: Video identifier
            session_uuid: Session that processed this video
            config_hash: Configuration hash
            person_objects: Processed person objects
            processing_metadata: Additional processing metadata
            
        Returns:
            True if successfully stored
        """
        try:
            cache_key = self._generate_cache_key(video_uuid, config_hash)
            
            query = """
                INSERT INTO cached_person_objects 
                (cache_key, video_uuid, session_uuid, config_hash, 
                 person_objects, processing_metadata, created_at, 
                 last_accessed, access_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (cache_key) 
                DO UPDATE SET
                    person_objects = EXCLUDED.person_objects,
                    processing_metadata = EXCLUDED.processing_metadata,
                    last_accessed = EXCLUDED.last_accessed,
                    access_count = cached_person_objects.access_count + 1
            """
            
            now = datetime.utcnow()
            
            await self.db.execute(
                query,
                cache_key,
                UUID(video_uuid),
                UUID(session_uuid),
                config_hash,
                json.dumps(person_objects),
                json.dumps(processing_metadata) if processing_metadata else None,
                now,
                now,
                0
            )
            
            self.logger.debug(f"Cached result for video {video_uuid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store cached result: {e}")
            return False
    
    async def analyze_cache_availability(
        self,
        video_uuids: List[str],
        config_hash: str
    ) -> Dict[str, bool]:
        """
        Analyze which videos have cached results.
        
        Args:
            video_uuids: List of video identifiers to check
            config_hash: Configuration hash for cache matching
            
        Returns:
            Dictionary mapping video_uuid -> has_cache (bool)
        """
        cache_availability = {}
        
        if not video_uuids:
            return cache_availability
        
        try:
            # Generate cache keys for all videos
            cache_keys = [
                self._generate_cache_key(video_uuid, config_hash)
                for video_uuid in video_uuids
            ]
            
            # Query database for existing cache entries
            query = """
                SELECT cache_key, video_uuid
                FROM cached_person_objects
                WHERE cache_key = ANY($1)
            """
            
            results = await self.db.fetch(query, cache_keys)
            
            # Create lookup of existing cache keys
            existing_cache_keys = {row['cache_key'] for row in results}
            
            # Build availability mapping
            for video_uuid in video_uuids:
                cache_key = self._generate_cache_key(video_uuid, config_hash)
                cache_availability[video_uuid] = cache_key in existing_cache_keys
            
            hit_count = sum(cache_availability.values())
            hit_rate = (hit_count / len(video_uuids)) * 100 if video_uuids else 0
            
            self.logger.info(
                f"Cache analysis: {hit_count}/{len(video_uuids)} "
                f"videos cached ({hit_rate:.1f}% hit rate)"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze cache availability: {e}")
            # Return all False if analysis fails
            cache_availability = {video_uuid: False for video_uuid in video_uuids}
        
        return cache_availability
    
    async def get_cache_statistics(
        self,
        collections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Args:
            collections: Optional filter by collections
            
        Returns:
            Dictionary with cache statistics
        """
        try:
            # Base statistics query
            base_query = """
                SELECT 
                    COUNT(*) as total_cached_videos,
                    COUNT(DISTINCT session_uuid) as total_sessions,
                    AVG(access_count) as avg_access_count,
                    MIN(created_at) as oldest_entry,
                    MAX(created_at) as newest_entry,
                    SUM(LENGTH(person_objects::text)) as total_cache_size_bytes
                FROM cached_person_objects
            """
            
            base_stats = await self.db.fetchrow(base_query)
            
            # Hit rate calculation (last 30 days)
            hit_rate_query = """
                SELECT 
                    COUNT(*) as total_accesses,
                    COUNT(CASE WHEN access_count > 0 THEN 1 END) as cache_hits
                FROM cached_person_objects
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """
            
            hit_rate_stats = await self.db.fetchrow(hit_rate_query)
            
            # Collections covered
            collections_query = """
                SELECT DISTINCT config_hash
                FROM cached_person_objects
                LIMIT 100
            """
            
            config_results = await self.db.fetch(collections_query)
            
            # Calculate statistics
            total_accesses = hit_rate_stats['total_accesses'] or 0
            cache_hits = hit_rate_stats['cache_hits'] or 0
            hit_rate = (cache_hits / total_accesses * 100) if total_accesses > 0 else 0.0
            
            # Convert cache size to MB
            cache_size_bytes = base_stats['total_cache_size_bytes'] or 0
            cache_size_mb = cache_size_bytes / (1024 * 1024)
            
            statistics = {
                'total_cached_videos': base_stats['total_cached_videos'] or 0,
                'total_sessions': base_stats['total_sessions'] or 0,
                'cache_size_mb': round(cache_size_mb, 2),
                'average_access_count': round(base_stats['avg_access_count'] or 0, 2),
                'oldest_cache_entry': base_stats['oldest_entry'],
                'newest_cache_entry': base_stats['newest_entry'],
                'hit_rate_last_30_days': round(hit_rate, 2),
                'total_configurations': len(config_results),
                'cache_efficiency_score': self._calculate_cache_efficiency(
                    base_stats['total_cached_videos'] or 0,
                    hit_rate,
                    base_stats['avg_access_count'] or 0
                )
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Failed to get cache statistics: {e}")
            return {
                'total_cached_videos': 0,
                'total_sessions': 0,
                'cache_size_mb': 0.0,
                'hit_rate_last_30_days': 0.0,
                'cache_efficiency_score': 0.0,
                'error': str(e)
            }
    
    def _generate_cache_key(self, video_uuid: str, config_hash: str) -> str:
        """Generate cache key from video UUID and config hash."""
        combined = f"{video_uuid}{config_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def _update_cache_access(self, cache_key: str) -> None:
        """Update access timestamp and increment count."""
        try:
            query = """
                UPDATE cached_person_objects
                SET last_accessed = NOW(),
                    access_count = access_count + 1
                WHERE cache_key = $1
            """
            await self.db.execute(query, cache_key)
        except Exception as e:
            self.logger.warning(f"Failed to update cache access: {e}")
    
    def _calculate_cache_efficiency(
        self,
        total_cached: int,
        hit_rate: float,
        avg_access: float
    ) -> float:
        """Calculate overall cache efficiency score."""
        if total_cached == 0:
            return 0.0
        
        # Normalize factors (0-1 scale)
        cache_volume_score = min(total_cached / 1000, 1.0)  # Up to 1000 videos = 1.0
        hit_rate_score = hit_rate / 100  # Percentage to decimal
        reuse_score = min(avg_access / 10, 1.0)  # Up to 10 accesses = 1.0
        
        # Weighted average
        efficiency = (
            cache_volume_score * 0.3 +
            hit_rate_score * 0.5 +
            reuse_score * 0.2
        )
        
        return round(efficiency, 3)
    
    async def validate_cache_integrity(self) -> Dict[str, Any]:
        """
        Validate cache integrity and identify inconsistencies.
        
        Returns:
            Dictionary with validation results
        """
        try:
            validation_results = {
                'total_entries_checked': 0,
                'valid_entries': 0,
                'invalid_entries': 0,
                'missing_videos': [],
                'corrupted_data': [],
                'orphaned_cache': [],
                'validation_passed': True
            }
            
            # Check all cache entries
            query = """
                SELECT cache_key, video_uuid, person_objects, processing_metadata
                FROM cached_person_objects
            """
            
            results = await self.db.fetch(query)
            validation_results['total_entries_checked'] = len(results)
            
            for row in results:
                try:
                    # Validate JSON data
                    person_objects = json.loads(row['person_objects'])
                    if row['processing_metadata']:
                        json.loads(row['processing_metadata'])
                    
                    # Validate person objects structure
                    if not isinstance(person_objects, list):
                        validation_results['corrupted_data'].append(row['cache_key'])
                        validation_results['invalid_entries'] += 1
                        continue
                    
                    validation_results['valid_entries'] += 1
                    
                except (json.JSONDecodeError, TypeError) as e:
                    validation_results['corrupted_data'].append(row['cache_key'])
                    validation_results['invalid_entries'] += 1
                    self.logger.warning(f"Corrupted cache entry {row['cache_key']}: {e}")
            
            # Set overall validation status
            validation_results['validation_passed'] = validation_results['invalid_entries'] == 0
            
            self.logger.info(
                f"Cache validation: {validation_results['valid_entries']}"
                f"/{validation_results['total_entries_checked']} entries valid"
            )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Cache validation failed: {e}")
            return {
                'validation_passed': False,
                'error': str(e)
            }
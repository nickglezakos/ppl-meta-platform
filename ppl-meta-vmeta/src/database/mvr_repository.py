"""
MVR-People Repository Layer
PPL Meta Platform - vmeta service

Database access layer for MVR-People (Machine Vision Representation - People).
Provides CRUD operations, similarity search with pgvector, and merge management.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import asyncpg
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import json
import numpy as np

logger = logging.getLogger(__name__)


class MVRRepositoryError(Exception):
    """Custom exception for MVR repository operations."""
    pass


class MVRRepository:
    """Repository for MVR-People database operations."""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        """
        Initialize MVR repository.
        
        Args:
            connection_pool: asyncpg connection pool
        """
        self.pool = connection_pool
        logger.info("MVRRepository initialized")
    
    # ========================================================================
    # MVR-People CRUD Operations
    # ========================================================================
    
    async def create_mvr_people(
        self,
        face_embedding: np.ndarray,
        featured_individual_uuid: UUID,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        age_confidence: Optional[float] = None,
        gender: Optional[str] = None,
        gender_confidence: Optional[float] = None,
        quality_score: float = 0.5,
        confidence_score: float = 0.5,
        face_quality: float = 0.5,
        featured_person_object_uuid: Optional[UUID] = None,
        featured_video_uuid: Optional[UUID] = None,
        created_by_session: Optional[UUID] = None,
        auto_created: bool = True,
        is_isolated: bool = False,
        source_media_uuid: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Create new MVR-People record.
        
        Args:
            face_embedding: 512-dimensional face embedding (numpy array)
            featured_individual_uuid: UUID of the featured Individual
            age_min: Minimum age estimate
            age_max: Maximum age estimate
            age_confidence: Age estimation confidence
            gender: Gender classification (male/female/unknown)
            gender_confidence: Gender classification confidence
            quality_score: Overall quality score
            confidence_score: Overall confidence score
            face_quality: Face image quality
            featured_person_object_uuid: Best person object UUID
            featured_video_uuid: Video containing best appearance
            created_by_session: Tracking session UUID
            auto_created: True if auto-created on Individual insert
            is_isolated: True if this MVR is isolated (no cross-media merging)
            source_media_uuid: UUID of the single media this MVR was created from
            
        Returns:
            Dict with mvr_people_uuid and created_at
        """
        async with self.pool.acquire() as conn:
            try:
                # Validate and normalize face_quality (must be between 0.0-1.0, NOT NULL)
                if face_quality is None:
                    face_quality = 0.5  # Default if missing
                # Normalize if > 1.0 (percentage to decimal)
                if face_quality > 1.0:
                    face_quality = face_quality / 100.0
                # Clamp to valid range [0.0, 1.0]
                face_quality = max(0.0, min(1.0, float(face_quality)))
                
                # Convert numpy array to pgvector string format
                # pgvector expects format: '[val1,val2,val3,...]'
                embedding_list = face_embedding.tolist()
                embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
                
                result = await conn.fetchrow("""
                    INSERT INTO mvr_people (
                        face_embedding,
                        face_quality,
                        age_min,
                        age_max,
                        age_confidence,
                        gender,
                        gender_confidence,
                        quality_score,
                        confidence_score,
                        featured_individual_uuid,
                        featured_person_object_uuid,
                        featured_video_uuid,
                        created_by_session,
                        auto_created,
                        is_isolated,
                        source_media_uuid,
                        created_at,
                        updated_at
                    ) VALUES (
                        $1::vector, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, NOW(), NOW()
                    )
                    RETURNING mvr_people_uuid, created_at
                """,
                    embedding_str,
                    face_quality,
                    age_min,
                    age_max,
                    age_confidence,
                    gender,
                    gender_confidence,
                    quality_score,
                    confidence_score,
                    featured_individual_uuid,
                    featured_person_object_uuid,
                    featured_video_uuid,
                    created_by_session,
                    auto_created,
                    is_isolated,
                    source_media_uuid
                )
                
                logger.info(
                    f"Created MVR-People {result['mvr_people_uuid']} "
                    f"for Individual {featured_individual_uuid}"
                )
                
                return {
                    'mvr_people_uuid': result['mvr_people_uuid'],
                    'created_at': result['created_at']
                }
                
            except Exception as e:
                logger.error(f"Failed to create MVR-People: {e}")
                raise MVRRepositoryError(
                    f"Failed to create MVR-People: {e}"
                )
    
    async def get_mvr_people_by_uuid(
        self,
        mvr_people_uuid: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get MVR-People by UUID.
        
        Args:
            mvr_people_uuid: MVR-People UUID
            
        Returns:
            MVR-People dict or None if not found
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("""
                    SELECT 
                        mvr_people_uuid,
                        face_embedding,
                        face_quality,
                        age_min,
                        age_max,
                        age_confidence,
                        gender,
                        gender_confidence,
                        quality_score,
                        confidence_score,
                        featured_individual_uuid,
                        featured_person_object_uuid,
                        featured_video_uuid,
                        total_linked_individuals,
                        total_appearances,
                        total_videos,
                        first_seen,
                        last_seen,
                        created_at,
                        updated_at,
                        is_orphaned,
                        orphaned_at,
                        merged_into_mvr_uuid,
                        previous_individual_uuids,
                        auto_created,
                        name,
                        name_updated_at,
                        name_updated_by
                    FROM mvr_people
                    WHERE mvr_people_uuid = $1
                """, mvr_people_uuid)
                
                if not result:
                    return None
                
                return dict(result)
                
            except Exception as e:
                logger.error(
                    f"Failed to get MVR-People {mvr_people_uuid}: {e}"
                )
                raise MVRRepositoryError(
                    f"Failed to get MVR-People: {e}"
                )
    
    async def get_mvr_people_by_individual(
        self,
        individual_uuid: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get MVR-People for an Individual.
        
        Args:
            individual_uuid: Individual UUID
            
        Returns:
            MVR-People dict or None if not found
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("""
                    SELECT m.*
                    FROM mvr_people m
                    INNER JOIN individual_mvr_mapping im
                        ON m.mvr_people_uuid = im.mvr_people_uuid
                    WHERE im.individual_uuid = $1
                    AND m.is_orphaned = FALSE
                    ORDER BY im.linked_at DESC
                    LIMIT 1
                """, individual_uuid)
                
                if not result:
                    return None
                
                return dict(result)
                
            except Exception as e:
                logger.error(
                    f"Failed to get MVR for Individual {individual_uuid}: {e}"
                )
                raise MVRRepositoryError(
                    f"Failed to get MVR for Individual: {e}"
                )
    
    async def update_mvr_people(
        self,
        mvr_people_uuid: UUID,
        **kwargs
    ) -> bool:
        """
        Update MVR-People record.
        
        Args:
            mvr_people_uuid: MVR-People UUID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        async with self.pool.acquire() as conn:
            try:
                # Build dynamic UPDATE query
                allowed_fields = {
                    'face_embedding', 'face_quality', 'age_min', 'age_max',
                    'age_confidence', 'gender', 'gender_confidence',
                    'quality_score', 'confidence_score',
                    'featured_individual_uuid',
                    'featured_person_object_uuid',
                    'featured_video_uuid',
                    'total_linked_individuals', 'total_appearances',
                    'total_videos', 'first_seen', 'last_seen'
                }
                
                update_fields = {
                    k: v for k, v in kwargs.items() 
                    if k in allowed_fields
                }
                
                if not update_fields:
                    logger.warning("No valid fields to update")
                    return False
                
                # Add updated_at
                update_fields['updated_at'] = datetime.utcnow()
                
                # Build SET clause
                set_clauses = [
                    f"{field} = ${i+2}" 
                    for i, field in enumerate(update_fields.keys())
                ]
                set_clause = ", ".join(set_clauses)
                
                # Execute update
                query = f"""
                    UPDATE mvr_people
                    SET {set_clause}
                    WHERE mvr_people_uuid = $1
                    AND is_orphaned = FALSE
                """
                
                result = await conn.execute(
                    query,
                    mvr_people_uuid,
                    *update_fields.values()
                )
                
                updated = result.split()[-1] == '1'
                
                if updated:
                    logger.info(f"Updated MVR-People {mvr_people_uuid}")
                
                return updated
                
            except Exception as e:
                logger.error(
                    f"Failed to update MVR-People {mvr_people_uuid}: {e}"
                )
                raise MVRRepositoryError(
                    f"Failed to update MVR-People: {e}"
                )
    
    # ========================================================================
    # Individual-MVR Mapping Operations
    # ========================================================================
    
    async def create_individual_mvr_mapping(
        self,
        individual_uuid: UUID,
        mvr_people_uuid: UUID,
        confidence_score: float,
        quality_score: float,
        similarity_score: Optional[float] = None,
        is_representative: bool = False,
        link_method: str = 'auto_create',
        linked_by_session: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Create Individual-MVR mapping.
        
        Args:
            individual_uuid: Individual UUID
            mvr_people_uuid: MVR-People UUID
            confidence_score: Confidence score
            quality_score: Quality score
            similarity_score: Face similarity score (for merges)
            is_representative: True if featured Individual
            link_method: auto_create, auto_merge, manual_link, batch_import
            linked_by_session: Tracking session UUID
            
        Returns:
            Dict with mapping_uuid and linked_at
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("""
                    INSERT INTO individual_mvr_mapping (
                        individual_uuid,
                        mvr_people_uuid,
                        confidence_score,
                        quality_score,
                        similarity_score,
                        is_representative,
                        link_method,
                        linked_by_session,
                        linked_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    RETURNING mapping_uuid, linked_at
                """,
                    individual_uuid,
                    mvr_people_uuid,
                    confidence_score,
                    quality_score,
                    similarity_score,
                    is_representative,
                    link_method,
                    linked_by_session
                )
                
                logger.info(
                    f"Created mapping: Individual {individual_uuid} -> "
                    f"MVR {mvr_people_uuid} ({link_method})"
                )
                
                return {
                    'mapping_uuid': result['mapping_uuid'],
                    'linked_at': result['linked_at']
                }
                
            except Exception as e:
                logger.error(f"Failed to create mapping: {e}")
                raise MVRRepositoryError(f"Failed to create mapping: {e}")
    
    async def get_linked_individuals(
        self,
        mvr_people_uuid: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all Individuals linked to MVR-People.
        
        Args:
            mvr_people_uuid: MVR-People UUID
            
        Returns:
            List of Individual dicts with mapping info
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch("""
                    SELECT 
                        im.mapping_uuid,
                        im.individual_uuid,
                        im.confidence_score,
                        im.quality_score,
                        im.similarity_score,
                        im.is_representative,
                        im.link_method,
                        im.linked_at,
                        i.individual_id,
                        i.total_appearances,
                        i.first_seen,
                        i.last_seen
                    FROM individual_mvr_mapping im
                    INNER JOIN individuals i 
                        ON im.individual_uuid = i.individual_uuid
                    WHERE im.mvr_people_uuid = $1
                    ORDER BY im.is_representative DESC, im.linked_at DESC
                """, mvr_people_uuid)
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Failed to get linked individuals: {e}")
                raise MVRRepositoryError(
                    f"Failed to get linked individuals: {e}"
                )
    
    # ========================================================================
    # Similarity Search & Matching
    # ========================================================================
    
    async def find_similar_mvr_people(
        self,
        face_embedding: np.ndarray,
        similarity_threshold: float = 0.85,
        max_results: int = 10,
        exclude_orphaned: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar MVR-People using pgvector similarity search.
        
        Args:
            face_embedding: Query face embedding
            similarity_threshold: Minimum similarity score
            max_results: Maximum number of results
            exclude_orphaned: Exclude orphaned MVR-People
            
        Returns:
            List of similar MVR-People with similarity scores
        """
        async with self.pool.acquire() as conn:
            try:
                # Convert numpy array to pgvector string format
                embedding_list = face_embedding.tolist()
                embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
                
                orphan_filter = (
                    "AND is_orphaned = FALSE" if exclude_orphaned else ""
                )
                
                results = await conn.fetch(f"""
                    SELECT 
                        mvr_people_uuid,
                        face_embedding,
                        quality_score,
                        confidence_score,
                        total_linked_individuals,
                        featured_individual_uuid,
                        1 - (face_embedding <=> $1::vector) AS similarity_score
                    FROM mvr_people
                    WHERE 1 - (face_embedding <=> $1::vector) >= $2
                    {orphan_filter}
                    ORDER BY face_embedding <=> $1::vector
                    LIMIT $3
                """,
                    embedding_str,
                    similarity_threshold,
                    max_results
                )
                
                logger.info(
                    f"Found {len(results)} similar MVR-People "
                    f"(threshold: {similarity_threshold})"
                )
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Similarity search failed: {e}")
                raise MVRRepositoryError(f"Similarity search failed: {e}")
    
    # ========================================================================
    # Merge Operations
    # ========================================================================
    
    async def mark_mvr_as_orphaned(
        self,
        source_mvr_uuid: UUID,
        target_mvr_uuid: UUID
    ) -> bool:
        """
        Mark MVR-People as orphaned after merge.
        
        Args:
            source_mvr_uuid: MVR being orphaned
            target_mvr_uuid: MVR it was merged into
            
        Returns:
            True if marked successfully
        """
        async with self.pool.acquire() as conn:
            try:
                # Get previous individual UUIDs before orphaning
                mvr_data = await conn.fetchrow("""
                    SELECT 
                        previous_individual_uuids,
                        featured_individual_uuid
                    FROM mvr_people
                    WHERE mvr_people_uuid = $1
                """, source_mvr_uuid)
                
                if not mvr_data:
                    return False
                
                # Build updated previous_individual_uuids array
                prev_uuids = mvr_data['previous_individual_uuids'] or []
                featured_uuid = str(mvr_data['featured_individual_uuid'])
                
                if featured_uuid not in prev_uuids:
                    prev_uuids.append(featured_uuid)
                
                # Mark as orphaned
                result = await conn.execute("""
                    UPDATE mvr_people
                    SET 
                        is_orphaned = TRUE,
                        orphaned_at = NOW(),
                        merged_into_mvr_uuid = $2,
                        previous_individual_uuids = $3,
                        updated_at = NOW()
                    WHERE mvr_people_uuid = $1
                    AND is_orphaned = FALSE
                """,
                    source_mvr_uuid,
                    target_mvr_uuid,
                    json.dumps(prev_uuids)
                )
                
                orphaned = result.split()[-1] == '1'
                
                if orphaned:
                    logger.info(
                        f"Marked MVR {source_mvr_uuid} as orphaned "
                        f"(merged into {target_mvr_uuid})"
                    )
                
                return orphaned
                
            except Exception as e:
                logger.error(f"Failed to mark MVR as orphaned: {e}")
                raise MVRRepositoryError(
                    f"Failed to mark MVR as orphaned: {e}"
                )
    
    async def reassign_individuals_to_mvr(
        self,
        source_mvr_uuid: UUID,
        target_mvr_uuid: UUID,
        similarity_score: float
    ) -> int:
        """
        Reassign all Individuals from source MVR to target MVR.
        
        Args:
            source_mvr_uuid: Source MVR (being orphaned)
            target_mvr_uuid: Target MVR (receiving individuals)
            similarity_score: Similarity score for merge
            
        Returns:
            Number of individuals reassigned
        """
        async with self.pool.acquire() as conn:
            try:
                # Update mappings to point to target MVR
                result = await conn.execute("""
                    UPDATE individual_mvr_mapping
                    SET 
                        mvr_people_uuid = $2,
                        similarity_score = $3,
                        link_method = 'auto_merge',
                        linked_at = NOW()
                    WHERE mvr_people_uuid = $1
                """,
                    source_mvr_uuid,
                    target_mvr_uuid,
                    similarity_score
                )
                
                count = int(result.split()[-1])
                
                logger.info(
                    f"Reassigned {count} individuals from "
                    f"MVR {source_mvr_uuid} to {target_mvr_uuid}"
                )
                
                return count
                
            except Exception as e:
                logger.error(f"Failed to reassign individuals: {e}")
                raise MVRRepositoryError(
                    f"Failed to reassign individuals: {e}"
                )
    
    async def create_merge_audit_log(
        self,
        source_mvr_uuid: UUID,
        target_mvr_uuid: UUID,
        source_individual_uuid: UUID,
        merge_action: str,
        merge_reason: str,
        similarity_score: float,
        matching_threshold: float,
        source_quality_score: float,
        target_quality_score: float,
        winner_mvr_uuid: UUID,
        user_id: Optional[str] = None,
        system_mode: str = 'automatic',
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Create merge audit log entry.
        
        Args:
            source_mvr_uuid: Source MVR UUID
            target_mvr_uuid: Target MVR UUID
            source_individual_uuid: Individual that triggered merge
            merge_action: merged, rejected, manual_review
            merge_reason: Reason for merge decision
            similarity_score: Face similarity score
            matching_threshold: Threshold used
            source_quality_score: Source MVR quality
            target_quality_score: Target MVR quality
            winner_mvr_uuid: MVR that was kept
            user_id: User ID if manual
            system_mode: automatic, manual, batch
            metadata: Additional context
            
        Returns:
            Audit log UUID
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("""
                    INSERT INTO mvr_merge_audit_log (
                        source_mvr_uuid,
                        target_mvr_uuid,
                        source_individual_uuid,
                        merge_action,
                        merge_reason,
                        similarity_score,
                        matching_threshold,
                        source_quality_score,
                        target_quality_score,
                        winner_mvr_uuid,
                        user_id,
                        system_mode,
                        metadata,
                        merged_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, NOW()
                    )
                    RETURNING audit_uuid
                """,
                    source_mvr_uuid,
                    target_mvr_uuid,
                    source_individual_uuid,
                    merge_action,
                    merge_reason,
                    similarity_score,
                    matching_threshold,
                    source_quality_score,
                    target_quality_score,
                    winner_mvr_uuid,
                    user_id,
                    system_mode,
                    json.dumps(metadata) if metadata else None
                )
                
                audit_uuid = result['audit_uuid']
                
                logger.info(
                    f"Created merge audit log {audit_uuid}: "
                    f"{merge_action} ({merge_reason})"
                )
                
                return audit_uuid
                
            except Exception as e:
                logger.error(f"Failed to create merge audit log: {e}")
                raise MVRRepositoryError(
                    f"Failed to create merge audit log: {e}"
                )
    
    async def get_merge_history(
        self,
        individual_uuid: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get merge history for an Individual.
        
        Args:
            individual_uuid: Individual UUID
            
        Returns:
            List of merge audit log entries
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch("""
                    SELECT 
                        audit_uuid,
                        source_mvr_uuid,
                        target_mvr_uuid,
                        merge_action,
                        merge_reason,
                        similarity_score,
                        matching_threshold,
                        source_quality_score,
                        target_quality_score,
                        winner_mvr_uuid,
                        merged_at,
                        system_mode,
                        metadata
                    FROM mvr_merge_audit_log
                    WHERE source_individual_uuid = $1
                    ORDER BY merged_at DESC
                """, individual_uuid)
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Failed to get merge history: {e}")
                raise MVRRepositoryError(f"Failed to get merge history: {e}")
    
    # ========================================================================
    # Configuration Operations
    # ========================================================================
    
    async def get_matching_config(self) -> Dict[str, Any]:
        """
        Get current matching configuration.
        
        Returns:
            Matching config dict
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("""
                    SELECT 
                        similarity_threshold,
                        min_quality_threshold,
                        auto_merge_enabled,
                        require_manual_review_above,
                        orphan_retention_days,
                        auto_cleanup_orphans,
                        max_candidates_to_check,
                        batch_processing_size,
                        updated_at,
                        updated_by,
                        notes
                    FROM mvr_matching_config
                    WHERE config_id = 1
                """)
                
                if not result:
                    raise MVRRepositoryError(
                        "Matching config not found (run migration)"
                    )
                
                return dict(result)
                
            except Exception as e:
                logger.error(f"Failed to get matching config: {e}")
                raise MVRRepositoryError(
                    f"Failed to get matching config: {e}"
                )
    
    async def update_matching_config(
        self,
        similarity_threshold: Optional[float] = None,
        auto_merge_enabled: Optional[bool] = None,
        updated_by: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Update matching configuration.
        
        Args:
            similarity_threshold: New similarity threshold
            auto_merge_enabled: Enable/disable auto-merge
            updated_by: User making the update
            **kwargs: Other config fields
            
        Returns:
            True if updated
        """
        async with self.pool.acquire() as conn:
            try:
                update_fields = {}
                
                if similarity_threshold is not None:
                    update_fields['similarity_threshold'] = (
                        similarity_threshold
                    )
                if auto_merge_enabled is not None:
                    update_fields['auto_merge_enabled'] = auto_merge_enabled
                if updated_by:
                    update_fields['updated_by'] = updated_by
                
                # Add any other allowed fields
                allowed_fields = {
                    'min_quality_threshold',
                    'require_manual_review_above',
                    'orphan_retention_days',
                    'auto_cleanup_orphans',
                    'max_candidates_to_check',
                    'batch_processing_size',
                    'notes'
                }
                
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        update_fields[key] = value
                
                if not update_fields:
                    return False
                
                update_fields['updated_at'] = datetime.utcnow()
                
                # Build SET clause
                set_clauses = [
                    f"{field} = ${i+1}"
                    for i, field in enumerate(update_fields.keys())
                ]
                set_clause = ", ".join(set_clauses)
                
                query = f"""
                    UPDATE mvr_matching_config
                    SET {set_clause}
                    WHERE config_id = 1
                """
                
                await conn.execute(query, *update_fields.values())
                
                logger.info("Updated matching configuration")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to update matching config: {e}")
                raise MVRRepositoryError(
                    f"Failed to update matching config: {e}"
                )
    
    # ========================================================================
    # Query Operations
    # ========================================================================
    
    async def get_orphaned_mvr_people(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orphaned MVR-People records.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of orphaned MVR-People
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch("""
                    SELECT 
                        mvr_people_uuid,
                        orphaned_at,
                        merged_into_mvr_uuid,
                        previous_individual_uuids,
                        created_at
                    FROM mvr_people
                    WHERE is_orphaned = TRUE
                    ORDER BY orphaned_at DESC
                    LIMIT $1
                """, limit)
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Failed to get orphaned MVR-People: {e}")
                raise MVRRepositoryError(
                    f"Failed to get orphaned MVR-People: {e}"
                )
    
    async def search_by_demographics(
        self,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        gender: Optional[str] = None,
        min_quality: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search MVR-People by demographic criteria.
        
        Args:
            age_min: Minimum age
            age_max: Maximum age
            gender: Gender filter (male/female/unknown)
            min_quality: Minimum quality score
            limit: Maximum results
            
        Returns:
            List of matching MVR-People
        """
        async with self.pool.acquire() as conn:
            try:
                conditions = ["is_orphaned = FALSE"]
                params = []
                param_count = 1
                
                if age_min is not None:
                    conditions.append(f"age_max >= ${param_count}")
                    params.append(age_min)
                    param_count += 1
                
                if age_max is not None:
                    conditions.append(f"age_min <= ${param_count}")
                    params.append(age_max)
                    param_count += 1
                
                if gender:
                    conditions.append(f"gender = ${param_count}")
                    params.append(gender)
                    param_count += 1
                
                if min_quality:
                    conditions.append(f"quality_score >= ${param_count}")
                    params.append(min_quality)
                    param_count += 1
                
                where_clause = " AND ".join(conditions)
                params.append(limit)
                
                query = f"""
                    SELECT 
                        mvr_people_uuid,
                        age_min,
                        age_max,
                        gender,
                        quality_score,
                        confidence_score,
                        total_linked_individuals,
                        created_at
                    FROM mvr_people
                    WHERE {where_clause}
                    ORDER BY quality_score DESC
                    LIMIT ${param_count}
                """
                
                results = await conn.fetch(query, *params)
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Demographic search failed: {e}")
                raise MVRRepositoryError(f"Demographic search failed: {e}")
    
    # ========================================================================
    # Hierarchical Merge Support Methods
    # ========================================================================
    
    async def bulk_orphan_mvr_people(
        self,
        mvr_uuids: List[UUID],
        merged_into_uuid: UUID
    ) -> int:
        """
        Mark multiple MVR people as orphaned (merged into another).
        
        Args:
            mvr_uuids: List of MVR UUIDs to orphan
            merged_into_uuid: UUID they were merged into
            
        Returns:
            Number of MVR people orphaned
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute("""
                    UPDATE mvr_people
                    SET 
                        is_orphaned = TRUE,
                        orphaned_at = NOW(),
                        merged_into_mvr_uuid = $1,
                        updated_at = NOW()
                    WHERE mvr_people_uuid = ANY($2::uuid[])
                        AND NOT is_orphaned
                """, merged_into_uuid, mvr_uuids)
                
                count = int(result.split()[-1])
                logger.info(
                    f"Bulk orphaned {count} MVR people into {merged_into_uuid}"
                )
                return count
                
            except Exception as e:
                logger.error(f"Bulk orphan failed: {e}")
                raise MVRRepositoryError(f"Bulk orphan failed: {e}")
    
    async def get_merged_mvr_people(
        self,
        super_individual_uuid: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all MVR people merged into a super-individual.
        
        Args:
            super_individual_uuid: The super-individual (winner) UUID
            
        Returns:
            List of merged MVR people dicts
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch("""
                    SELECT 
                        mvr_people_uuid,
                        featured_individual_uuid,
                        quality_score,
                        confidence_score,
                        gender,
                        age_min,
                        age_max,
                        orphaned_at,
                        merged_into_mvr_uuid,
                        created_at
                    FROM mvr_people
                    WHERE merged_into_mvr_uuid = $1
                        AND is_orphaned = TRUE
                    ORDER BY quality_score DESC
                """, super_individual_uuid)
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Get merged MVR failed: {e}")
                raise MVRRepositoryError(f"Get merged MVR failed: {e}")
    
    async def get_individuals_for_mvr(
        self,
        mvr_uuid: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all individuals linked to an MVR person.
        
        Args:
            mvr_uuid: MVR UUID
            
        Returns:
            List of individual dicts with person object counts
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch("""
                    SELECT 
                        i.individual_uuid,
                        imm.mvr_people_uuid,
                        MIN(iva.start_timestamp) as first_seen_timestamp,
                        MAX(iva.end_timestamp) as last_seen_timestamp,
                        COUNT(DISTINCT iva.video_uuid) as video_count,
                        COUNT(iva.person_object_uuid) as person_object_count,
                        i.created_at,
                        i.confidence_score
                    FROM individuals i
                    INNER JOIN individual_mvr_mapping imm ON i.individual_uuid = imm.individual_uuid
                    LEFT JOIN individual_video_appearances iva ON iva.individual_uuid = i.individual_uuid
                    WHERE imm.mvr_people_uuid = $1
                    GROUP BY 
                        i.individual_uuid,
                        imm.mvr_people_uuid,
                        i.created_at,
                        i.confidence_score
                    ORDER BY MIN(iva.start_timestamp)
                """, mvr_uuid)
                
                return [dict(r) for r in results]
                
            except Exception as e:
                logger.error(f"Get individuals for MVR failed: {e}")
                raise MVRRepositoryError(f"Get individuals for MVR failed: {e}")

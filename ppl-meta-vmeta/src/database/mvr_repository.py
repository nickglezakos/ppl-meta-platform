"""
MVR-People Repository Layer
PPL Meta Platform - vmeta service

Database access layer for MVR-People (Machine Vision Representation - People).
Provides CRUD operations, similarity search with pgvector, and merge management.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import asyncpg
import httpx
import logging
import os
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
        featured_individual_uuid: Optional[UUID] = None,
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

    async def unmerge_mvr_people(
        self,
        orphaned_mvr_uuid: UUID,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reverse a previous merge by restoring an orphaned MVR record.

        Clears is_orphaned / merged_into_mvr_uuid on the child, restores
        individual_mvr_mapping rows that were reassigned during that specific
        merge (identified via mvr_merge_audit_log), removes the
        mvr_merge_hierarchy row, and appends an audit entry.

        Args:
            orphaned_mvr_uuid: The child/loser MVR UUID to restore.
            user_id: Optional user performing the undo.

        Returns:
            Dict with restored_mvr_uuid, winner_mvr_uuid,
            individuals_reassigned count.

        Raises:
            MVRRepositoryError on failure.
        """
        async with self.pool.acquire() as conn:
            try:
                async with conn.transaction():
                    # 1. Load current orphan row — verify it is actually orphaned
                    orphan_row = await conn.fetchrow(
                        """
                        SELECT mvr_people_uuid, merged_into_mvr_uuid, quality_score
                        FROM mvr_people
                        WHERE mvr_people_uuid = $1
                          AND is_orphaned = TRUE
                        """,
                        orphaned_mvr_uuid,
                    )
                    if not orphan_row:
                        raise MVRRepositoryError(
                            f"MVR {orphaned_mvr_uuid} is not orphaned or does not exist"
                        )

                    winner_uuid = orphan_row["merged_into_mvr_uuid"]

                    # 2. Clear orphan status
                    await conn.execute(
                        """
                        UPDATE mvr_people
                        SET is_orphaned            = FALSE,
                            orphaned_at            = NULL,
                            merged_into_mvr_uuid   = NULL,
                            updated_at             = NOW()
                        WHERE mvr_people_uuid = $1
                        """,
                        orphaned_mvr_uuid,
                    )

                    # 3. Identify which individuals were reassigned during THIS merge
                    #    using the audit log (most recent 'merged' row for this pair).
                    audit_rows = await conn.fetch(
                        """
                        SELECT source_individual_uuid
                        FROM mvr_merge_audit_log
                        WHERE source_mvr_uuid = $1
                          AND target_mvr_uuid = $2
                          AND merge_action    = 'merged'
                        ORDER BY merged_at DESC
                        """,
                        orphaned_mvr_uuid,
                        winner_uuid,
                    )
                    individual_uuids = [r["source_individual_uuid"] for r in audit_rows]

                    # 4. Restore individual_mvr_mapping rows back to the orphan
                    reassigned_count = 0
                    if individual_uuids:
                        result = await conn.execute(
                            """
                            UPDATE individual_mvr_mapping
                            SET mvr_people_uuid = $1,
                                link_method     = 'unmerge_restored',
                                linked_at       = NOW()
                            WHERE mvr_people_uuid = $2
                              AND individual_uuid = ANY($3::uuid[])
                            """,
                            orphaned_mvr_uuid,
                            winner_uuid,
                            individual_uuids,
                        )
                        reassigned_count = int(result.split()[-1])
                    else:
                        # Fallback: restore all current mappings that point to winner
                        # which match previous_individual_uuids stored on the orphan
                        prev_row = await conn.fetchrow(
                            "SELECT previous_individual_uuids FROM mvr_people WHERE mvr_people_uuid = $1",
                            orphaned_mvr_uuid,
                        )
                        prev_uuids_raw = prev_row["previous_individual_uuids"] if prev_row else None
                        if prev_uuids_raw:
                            prev_uuids = (
                                json.loads(prev_uuids_raw)
                                if isinstance(prev_uuids_raw, str)
                                else list(prev_uuids_raw)
                            )
                            if prev_uuids:
                                result = await conn.execute(
                                    """
                                    UPDATE individual_mvr_mapping
                                    SET mvr_people_uuid = $1,
                                        link_method     = 'unmerge_restored',
                                        linked_at       = NOW()
                                    WHERE mvr_people_uuid = $2
                                      AND individual_uuid = ANY($3::uuid[])
                                    """,
                                    orphaned_mvr_uuid,
                                    winner_uuid,
                                    [UUID(u) for u in prev_uuids],
                                )
                                reassigned_count = int(result.split()[-1])

                    # 5. Remove mvr_merge_hierarchy row
                    await conn.execute(
                        """
                        DELETE FROM mvr_merge_hierarchy
                        WHERE super_individual_uuid = $1
                          AND merged_mvr_uuid       = $2
                        """,
                        winner_uuid,
                        orphaned_mvr_uuid,
                    )

                    # 6. Audit log entry for the undo — one row per reassigned individual.
                    # Query the mapping table which was just updated in step 4 so we
                    # always get a valid, non-null individual UUID even when the
                    # forward merge never wrote per-individual audit rows (e.g. force_merge).
                    audit_individual_rows = await conn.fetch(
                        """
                        SELECT individual_uuid
                        FROM individual_mvr_mapping
                        WHERE mvr_people_uuid = $1
                        """,
                        orphaned_mvr_uuid,
                    )
                    audit_individual_uuids = [r["individual_uuid"] for r in audit_individual_rows]

                    # Fallback: use featured_individual_uuid from mvr_people if mapping is empty
                    if not audit_individual_uuids:
                        feat_row = await conn.fetchrow(
                            "SELECT featured_individual_uuid FROM mvr_people WHERE mvr_people_uuid = $1",
                            orphaned_mvr_uuid,
                        )
                        if feat_row and feat_row["featured_individual_uuid"]:
                            audit_individual_uuids = [feat_row["featured_individual_uuid"]]

                    for ind_uuid in audit_individual_uuids:
                        await conn.execute(
                            """
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
                                merged_at
                            ) VALUES ($1, $2, $3, 'unmerged', 'user_undo',
                                      0.0, 0.0,
                                      $4, 0.0,
                                      $1, $5, 'manual', NOW())
                            """,
                            orphaned_mvr_uuid,
                            winner_uuid,
                            ind_uuid,
                            float(orphan_row["quality_score"] or 0),
                            user_id,
                        )

                    logger.info(
                        f"Unmerged MVR {orphaned_mvr_uuid} from {winner_uuid}; "
                        f"reassigned {reassigned_count} individual(s)"
                    )

                    return {
                        "restored_mvr_uuid": str(orphaned_mvr_uuid),
                        "winner_mvr_uuid": str(winner_uuid),
                        "individuals_reassigned": reassigned_count,
                    }

            except MVRRepositoryError:
                raise
            except Exception as e:
                logger.error(f"Failed to unmerge MVR {orphaned_mvr_uuid}: {e}")
                raise MVRRepositoryError(f"Failed to unmerge MVR: {e}")

    async def get_merged_mvr_people(
        self,
        super_individual_uuid: UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Get paginated MVR people merged into a super-individual.

        Args:
            super_individual_uuid: The super-individual (winner) UUID
            page: 1-based page number
            page_size: Number of results per page

        Returns:
            Dict with keys:
              - ``items``: List of merged MVR people dicts for this page
              - ``total``: Total count of merged children
        """
        offset = (page - 1) * page_size
        async with self.pool.acquire() as conn:
            try:
                total = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM mvr_people
                    WHERE merged_into_mvr_uuid = $1
                        AND is_orphaned = TRUE
                """, super_individual_uuid)

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
                    LIMIT $2 OFFSET $3
                """, super_individual_uuid, page_size, offset)

                return {
                    "items": [dict(r) for r in results],
                    "total": total or 0,
                }

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

    # ========================================================================
    # Individual Route Paging
    # ========================================================================

    async def _resolve_route_target_individual_uuids(
        self,
        conn: asyncpg.Connection,
        requested_uuid: UUID,
    ) -> List[UUID]:
        """
        Resolve a route request UUID to raw individual UUIDs.

        Rules:
        - If the UUID is a raw individual UUID, use it directly.
        - If the UUID is an MVR UUID, normalize merged children to the
          containing super-individual and expand to all linked raw individuals.
        - If nothing matches, return the UUID as-is so callers get an empty
          result set rather than a special-case failure.
        """
        is_mvr = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM mvr_people WHERE mvr_people_uuid = $1)",
            requested_uuid,
        )
        if is_mvr:
            rows = await conn.fetch(
                """
                WITH normalized_root AS (
                    SELECT COALESCE(
                        (
                            SELECT super_individual_uuid
                            FROM mvr_merge_hierarchy
                            WHERE merged_mvr_uuid = $1
                            LIMIT 1
                        ),
                        $1::uuid
                    ) AS root_uuid
                ),
                all_mvr AS (
                    SELECT root_uuid AS mvr_people_uuid
                    FROM normalized_root
                    UNION
                    SELECT mh.merged_mvr_uuid
                    FROM mvr_merge_hierarchy mh
                    JOIN normalized_root nr
                      ON mh.super_individual_uuid = nr.root_uuid
                )
                SELECT DISTINCT imm.individual_uuid
                FROM individual_mvr_mapping imm
                JOIN all_mvr am
                  ON am.mvr_people_uuid = imm.mvr_people_uuid
                ORDER BY imm.individual_uuid
                """,
                requested_uuid,
            )

            resolved = [row["individual_uuid"] for row in rows]
            return resolved or [requested_uuid]

        is_individual = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM individuals WHERE individual_uuid = $1)",
            requested_uuid,
        )
        if not is_individual:
            return [requested_uuid]
        return [requested_uuid]

    async def _fetch_route_source_rows(
        self,
        conn: asyncpg.Connection,
        requested_uuid: UUID,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch raw route source rows for a raw individual or MVR/super UUID."""
        target_individual_uuids = await self._resolve_route_target_individual_uuids(
            conn,
            requested_uuid,
        )

        conditions = ["iva.individual_uuid = ANY($1::uuid[])"]
        params: List[Any] = [target_individual_uuids]
        idx = 2

        if start_time_ms is not None:
            conditions.append(
                f"iva.start_timestamp >= to_timestamp(${idx}::float8 / 1000.0)"
            )
            params.append(start_time_ms)
            idx += 1

        if end_time_ms is not None:
            conditions.append(
                f"iva.start_timestamp <= to_timestamp(${idx}::float8 / 1000.0)"
            )
            params.append(end_time_ms)
            idx += 1

        query = f"""
            SELECT
                (EXTRACT(EPOCH FROM iva.start_timestamp) * 1000)::bigint AS timestamp_ms,
                iva.start_timestamp,
                iva.representative_faces,
                iva.entry_bbox,
                iva.exit_bbox,
                iva.video_uuid::text AS video_uuid,
                iva.person_object_uuid::text AS person_object_uuid,
                iva.individual_uuid::text AS individual_uuid,
                iva.confidence
            FROM individual_video_appearances iva
            WHERE {' AND '.join(conditions)}
            ORDER BY iva.start_timestamp ASC
        """

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def _resolve_route_camera_ids(
        self,
        video_uuids: List[str],
        auth_header: Optional[str],
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
    ) -> Dict[str, Tuple[str, str]]:
        """
        Resolve each video UUID to (collection_uuid, collection_name).

        Preferred: collection UUID + name from media search response.
        Fallback: video UUID as both id and name.
        """
        if not video_uuids:
            return {}

        if not auth_header:
            return {v: (v, v) for v in video_uuids}

        unresolved = set(video_uuids)
        resolved: Dict[str, Tuple[str, str]] = {}
        media_base_url = os.getenv("PPL_MEDIA_URL", "http://localhost:8000").rstrip("/")
        headers = {"Authorization": auth_header}
        page = 1
        page_size = 200
        search_params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }

        if start_time_ms is not None:
            search_params["start_time"] = datetime.utcfromtimestamp(
                start_time_ms / 1000.0
            ).isoformat() + "Z"
        if end_time_ms is not None:
            search_params["end_time"] = datetime.utcfromtimestamp(
                end_time_ms / 1000.0
            ).isoformat() + "Z"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while unresolved:
                    search_params["page"] = page
                    response = await client.get(
                        f"{media_base_url}/api/v1/media/search",
                        headers=headers,
                        params=search_params,
                    )
                    if response.status_code != 200:
                        logger.warning(
                            "Route media search fallback returned status %s on page %s",
                            response.status_code,
                            page,
                        )
                        break

                    items = response.json()
                    if not isinstance(items, list) or not items:
                        break

                    for item in items:
                        video_uuid = str(item.get("uuid") or "")
                        if video_uuid not in unresolved:
                            continue

                        collections = item.get("collections") or []
                        collection_uuid = ""
                        collection_name = ""
                        if collections and isinstance(collections, list):
                            first_collection = collections[0] or {}
                            collection_uuid = str(
                                first_collection.get("uuid")
                                or first_collection.get("id")
                                or ""
                            )
                            collection_name = str(
                                first_collection.get("name") or collection_uuid
                            )

                        cam_id = collection_uuid or video_uuid
                        cam_name = collection_name or cam_id
                        resolved[video_uuid] = (cam_id, cam_name)
                        unresolved.discard(video_uuid)

                    if len(items) < page_size:
                        break
                    page += 1
        except Exception as exc:
            logger.warning("Route media UUID fallback failed: %s", exc)

        for video_uuid in unresolved:
            resolved[video_uuid] = (video_uuid, video_uuid)

        return resolved

    async def _build_route_dataset(
        self,
        requested_uuid: UUID,
        auth_header: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch route rows and annotate each row with a UUID-only camera/group id."""
        async with self.pool.acquire() as conn:
            rows = await self._fetch_route_source_rows(
                conn,
                requested_uuid=requested_uuid,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )

        video_uuids = sorted(
            {
                row["video_uuid"]
                for row in rows
                if row.get("video_uuid")
            }
        )
        video_camera_map = await self._resolve_route_camera_ids(
            video_uuids,
            auth_header=auth_header,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )

        for row in rows:
            video_uuid = row.get("video_uuid") or ""
            cam_id, cam_name = video_camera_map.get(video_uuid, (video_uuid, video_uuid))
            row["camera_id"] = cam_id
            row["camera_name"] = cam_name

        rows = await self._expand_with_orchestrator_route_points(rows, auth_header)
        return rows

    @staticmethod
    def _match_person_group_by_representative_face(
        person_groups: List[Dict[str, Any]],
        representative_faces: Any,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Match an appearance to its person_group using representative face data.

        The Orchestrator regenerates person_uuid on every request so UUID
        matching is unreliable.  Instead we match using the representative
        face's frame_number + center_x coordinates against route_points:

        Primary:   frame_number equality AND center_x within 2 px.
        Secondary: closest route point by Euclidean distance (threshold 15 px).
        """
        if not person_groups:
            return None

        if isinstance(representative_faces, str):
            try:
                representative_faces = json.loads(representative_faces)
            except (ValueError, TypeError):
                representative_faces = {}

        ref_frame: Optional[int] = None
        ref_cx: Optional[float] = None
        ref_cy: Optional[float] = None

        if isinstance(representative_faces, dict):
            faces = representative_faces.get("faces") or []
            if faces and isinstance(faces, list):
                face_data = (faces[0] or {}).get("face_data") or {}
                try:
                    ref_frame = int(face_data["frame_number"])
                except (KeyError, TypeError, ValueError):
                    pass
                try:
                    ref_cx = float(face_data["center_x"])
                    ref_cy = float(face_data.get("center_y") or 0.0)
                except (KeyError, TypeError, ValueError):
                    pass

        if ref_frame is None and ref_cx is None:
            return None

        # Primary: exact frame_number match with tight spatial tolerance.
        if ref_frame is not None and ref_cx is not None:
            for pg in person_groups:
                route_pts = (pg.get("movement_tracking") or {}).get("route_points") or []
                for rp in route_pts:
                    if rp.get("frame_number") == ref_frame:
                        if abs(float(rp.get("center_x", 0)) - ref_cx) <= 2.0:
                            return route_pts

        # Secondary: spatial proximity across all groups.
        if ref_cx is not None and ref_cy is not None:
            best_pts: Optional[List[Dict[str, Any]]] = None
            best_dist = float("inf")
            for pg in person_groups:
                route_pts = (pg.get("movement_tracking") or {}).get("route_points") or []
                for rp in route_pts:
                    dx = float(rp.get("center_x", 0)) - ref_cx
                    dy = float(rp.get("center_y", 0)) - ref_cy
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_pts = route_pts
            if best_dist < 15.0:
                return best_pts

        return None

    async def _expand_with_orchestrator_route_points(
        self,
        rows: List[Dict[str, Any]],
        auth_header: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Expand appearance rows with per-frame route points from the orchestrator.

        For each appearance row fetches movement_tracking.route_points via
        GET /api/v1/orchestrator/person-objects/{video_uuid} and returns one
        row per route point.  Falls back to the original single row per
        appearance when the orchestrator is unreachable or has no matching
        route points for a person.

        Matching uses representative face frame_number + center coordinates
        rather than person_uuid, because the Orchestrator regenerates UUIDs
        on every processing call.
        """
        if not auth_header or not rows:
            return rows

        gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080").rstrip("/")
        headers = {"Authorization": auth_header}

        # Group by video_uuid to limit HTTP requests to one per video.
        video_rows: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            vid = row.get("video_uuid") or ""
            video_rows.setdefault(vid, []).append(row)

        expanded: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for video_uuid, appearance_rows in video_rows.items():
                if not video_uuid:
                    expanded.extend(appearance_rows)
                    continue

                person_groups: List[Dict] = []
                try:
                    response = await client.get(
                        f"{gateway_url}/api/v1/orchestrator/person-objects/{video_uuid}",
                        headers=headers,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        person_groups = (
                            data.get("group_tracking") or data.get("person_groups") or []
                        )
                except Exception as exc:
                    logger.warning(
                        "Orchestrator route fetch failed for video %s: %s",
                        video_uuid,
                        exc,
                    )

                for row in appearance_rows:
                    route_pts = self._match_person_group_by_representative_face(
                        person_groups,
                        row.get("representative_faces"),
                    )
                    if not route_pts:
                        # No per-frame data — keep the original single-point row.
                        expanded.append(row)
                        continue

                    base_ts_ms = int(row.get("timestamp_ms") or 0)
                    for rp in route_pts:
                        new_row = dict(row)
                        new_row["precomputed_center_x"] = float(
                            rp.get("center_x", rp.get("x", 0))
                        )
                        new_row["precomputed_center_y"] = float(
                            rp.get("center_y", rp.get("y", 0))
                        )
                        rp_ts = rp.get("timestamp")
                        if rp_ts is not None:
                            new_row["timestamp_ms"] = base_ts_ms + int(float(rp_ts) * 1000)
                        expanded.append(new_row)

        return expanded

    def _build_individual_routes_where_clause(
        self,
        individual_uuid: UUID,
        camera_id: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
    ) -> Tuple[str, List[Any], int]:
        """
        Build reusable WHERE clause for individual route queries.

        Queries use individual_video_appearances (iva) joined to
        tracking_sessions (ts) for camera identity.
        """
        conditions = [
            "iva.individual_uuid = $1",
            "ts.collections[1] IS NOT NULL",
        ]
        params: List[Any] = [individual_uuid]
        idx = 2

        if camera_id is not None:
            conditions.append(f"ts.collections[1] = ${idx}")
            params.append(camera_id)
            idx += 1

        if start_time_ms is not None:
            conditions.append(f"iva.start_timestamp >= to_timestamp(${idx}::float8 / 1000.0)")
            params.append(start_time_ms)
            idx += 1

        if end_time_ms is not None:
            conditions.append(f"iva.start_timestamp <= to_timestamp(${idx}::float8 / 1000.0)")
            params.append(end_time_ms)
            idx += 1

        return " AND ".join(conditions), params, idx

    @staticmethod
    def _bbox_to_center(bbox) -> tuple:
        """Convert a face bounding box [x1,y1,x2,y2] or [x,y,w,h] to (center_x, center_y)."""
        if not bbox or len(bbox) < 4:
            return 0.0, 0.0
        # Heuristic: if bbox[2] > bbox[0] and both are plausible pixel coordinates treat
        # as [x1,y1,x2,y2]; otherwise treat as [x,y,w,h].
        x0, y0, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        if x2 > x0 and y2 > y0:
            # [x1, y1, x2, y2]
            return (x0 + x2) / 2.0, (y0 + y2) / 2.0
        # [x, y, w, h]
        return x0 + x2 / 2.0, y0 + y2 / 2.0

    @staticmethod
    def _extract_bbox_from_representative_faces(rep_faces: Any) -> Optional[List[float]]:
        """Extract a bbox from representative_faces across known payload shapes."""
        if isinstance(rep_faces, str):
            try:
                rep_faces = json.loads(rep_faces)
            except (ValueError, TypeError):
                return None

        # Legacy/list shape: [{"bbox": [...]}, {"face_data": {"bbox": [...]}}]
        if isinstance(rep_faces, list) and rep_faces:
            first = rep_faces[0]
            if isinstance(first, dict):
                bbox = first.get("bbox")
                if isinstance(bbox, list) and len(bbox) >= 4:
                    return bbox[:4]
                face_data = first.get("face_data")
                if isinstance(face_data, dict):
                    bbox = face_data.get("bbox")
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        return bbox[:4]

        # Current/object shape: {"faces": [{"face_data": {"bbox": [...]}}]}
        if isinstance(rep_faces, dict):
            faces = rep_faces.get("faces")
            if isinstance(faces, list) and faces:
                first_face = faces[0]
                if isinstance(first_face, dict):
                    bbox = first_face.get("bbox")
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        return bbox[:4]
                    face_data = first_face.get("face_data")
                    if isinstance(face_data, dict):
                        bbox = face_data.get("bbox")
                        if isinstance(bbox, list) and len(bbox) >= 4:
                            return bbox[:4]

        return None

    @staticmethod
    def _appearance_to_route_point(row: dict, seq: int, camera_id: str) -> dict:
        """Convert an individual_video_appearances row to a route-point dict."""
        ts_ms = int(row["timestamp_ms"]) if row.get("timestamp_ms") is not None else 0
        if row.get("precomputed_center_x") is not None:
            center_x = float(row["precomputed_center_x"])
            center_y = float(row.get("precomputed_center_y") or 0.0)
        else:
            bbox = MVRRepository._extract_bbox_from_representative_faces(
                row.get("representative_faces")
            )
            if not bbox:
                bbox = row.get("entry_bbox") or row.get("exit_bbox")
            center_x, center_y = MVRRepository._bbox_to_center(bbox)
        return {
            "sequence_number": seq,
            "timestamp_ms": ts_ms,
            "center_x": center_x,
            "center_y": center_y,
            "velocity_x": 0.0,
            "velocity_y": 0.0,
            "velocity_magnitude": 0.0,
            "direction_radians": 0.0,
            "confidence_score": float(row.get("confidence") or 0.0),
            "detection_quality": None,
            "video_uuid": row.get("video_uuid"),
            "person_object_uuid": row.get("person_object_uuid"),
            "individual_uuid": row.get("individual_uuid"),
            "camera_id": camera_id,
            "camera_name": camera_id,
        }

    async def get_individual_routes_by_camera_paged(
        self,
        individual_uuid: UUID,
        page_index: int = 0,
        page_size: int = 500,
        camera_id: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        auth_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return camera-grouped paginated route points for a single individual.

        Route points are derived from individual_video_appearances joined to
        tracking_sessions for camera identity.  Each appearance represents
        one detection event and its best-face bounding-box is used as the
        spatial position of the route point.
        """
        try:
            page_size = min(page_size, 2000)
            rows = await self._build_route_dataset(
                requested_uuid=individual_uuid,
                auth_header=auth_header,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )

            grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows:
                current_camera_id = row.get("camera_id") or row.get("video_uuid") or ""
                if camera_id is not None and current_camera_id != camera_id:
                    continue
                grouped_rows.setdefault(current_camera_id, []).append(row)

            if not grouped_rows:
                return {"cameras": []}

            cameras = []
            for current_camera_id in sorted(grouped_rows):
                camera_rows = grouped_rows[current_camera_id]
                current_camera_name = camera_rows[0].get("camera_name") or current_camera_id
                total_points = len(camera_rows)
                total_appearances = len(
                    {
                        row.get("video_uuid")
                        for row in camera_rows
                        if row.get("video_uuid")
                    }
                )
                page_start = page_index * page_size
                page_end = page_start + page_size
                page_rows = camera_rows[page_start:page_end]
                points = [
                    self._appearance_to_route_point(
                        row,
                        page_start + seq + 1,
                        current_camera_id,
                    )
                    for seq, row in enumerate(page_rows)
                ]
                # Patch camera_name on each point from the row
                for point, row in zip(points, page_rows):
                    point["camera_name"] = row.get("camera_name") or current_camera_id
                has_more = page_end < total_points
                start_ts = int(camera_rows[0]["timestamp_ms"]) if camera_rows else None
                end_ts = int(camera_rows[-1]["timestamp_ms"]) if camera_rows else None

                cameras.append(
                    {
                        "camera_id": current_camera_id,
                        "camera_name": current_camera_name,
                        "total_points_across_individuals": total_points,
                        "total_appearances_across_individuals": total_appearances,
                        "has_more": has_more,
                        "individuals": [
                            {
                                "individual_uuid": str(individual_uuid),
                                "total_points": total_points,
                                "total_appearances": total_appearances,
                                "start_time_ms": start_ts,
                                "end_time_ms": end_ts,
                                "has_more": has_more,
                                "points": points,
                            }
                        ],
                    }
                )

            return {"cameras": cameras}
        except Exception as e:
            logger.error(
                "get_individual_routes_by_camera_paged failed for %s: %s",
                individual_uuid,
                e,
            )
            raise MVRRepositoryError(
                f"get_individual_routes_by_camera_paged failed: {e}"
            ) from e

    async def get_individual_routes_metadata_by_camera(
        self,
        individual_uuid: UUID,
        camera_id: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        auth_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return metadata grouped by camera for a single individual.

        Uses individual_video_appearances + tracking_sessions for camera identity.
        """
        try:
            rows = await self._build_route_dataset(
                requested_uuid=individual_uuid,
                auth_header=auth_header,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )

            grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows:
                current_camera_id = row.get("camera_id") or row.get("video_uuid") or ""
                if camera_id is not None and current_camera_id != camera_id:
                    continue
                grouped_rows.setdefault(current_camera_id, []).append(row)

            return {
                "cameras": [
                    {
                        "camera_id": current_camera_id,
                        "camera_name": (camera_rows[0].get("camera_name") or current_camera_id),
                        "total_points": len(camera_rows),
                        "total_appearances": len(
                            {
                                row.get("video_uuid")
                                for row in camera_rows
                                if row.get("video_uuid")
                            }
                        ),
                        "start_time_ms": int(camera_rows[0]["timestamp_ms"]) if camera_rows else None,
                        "end_time_ms": int(camera_rows[-1]["timestamp_ms"]) if camera_rows else None,
                    }
                    for current_camera_id, camera_rows in sorted(grouped_rows.items())
                ]
            }
        except Exception as e:
            logger.error(
                "get_individual_routes_metadata_by_camera failed for %s: %s",
                individual_uuid,
                e,
            )
            raise MVRRepositoryError(
                f"get_individual_routes_metadata_by_camera failed: {e}"
            ) from e

    async def get_individual_routes_paged(
        self,
        individual_uuid: UUID,
        page_index: int = 0,
        page_size: int = 500,
        camera_id: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        auth_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a page of route points for an individual.

        Route points are derived from individual_video_appearances joined to
        tracking_sessions for camera identity.
        """
        try:
            page_size = min(page_size, 2000)
            rows = await self._build_route_dataset(
                requested_uuid=individual_uuid,
                auth_header=auth_header,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )

            filtered_rows = [
                row
                for row in rows
                if camera_id is None or (row.get("camera_id") or row.get("video_uuid") or "") == camera_id
            ]
            total_points = len(filtered_rows)
            total_appearances = len(
                {row.get("video_uuid") for row in filtered_rows if row.get("video_uuid")}
            )
            offset = page_index * page_size
            page_rows = filtered_rows[offset:offset + page_size]
            points = [
                self._appearance_to_route_point(
                    row,
                    offset + seq + 1,
                    row.get("camera_id") or row.get("video_uuid") or "",
                )
                for seq, row in enumerate(page_rows)
            ]

            return {
                "points": points,
                "total_points": total_points,
                "total_appearances": total_appearances,
                "start_time_ms": int(filtered_rows[0]["timestamp_ms"]) if filtered_rows else None,
                "end_time_ms": int(filtered_rows[-1]["timestamp_ms"]) if filtered_rows else None,
            }
        except Exception as e:
            logger.error(
                f"get_individual_routes_paged failed for {individual_uuid}: {e}"
            )
            raise MVRRepositoryError(
                f"get_individual_routes_paged failed: {e}"
            )

    async def get_individual_routes_metadata(
        self,
        individual_uuid: UUID,
        camera_id: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        auth_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return route metadata for an individual without returning point data.
        """
        try:
            rows = await self._build_route_dataset(
                requested_uuid=individual_uuid,
                auth_header=auth_header,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )
            filtered_rows = [
                row
                for row in rows
                if camera_id is None or (row.get("camera_id") or row.get("video_uuid") or "") == camera_id
            ]

            per_video_counts: Dict[str, int] = {}
            for row in filtered_rows:
                video_uuid = row.get("video_uuid") or ""
                if not video_uuid:
                    continue
                per_video_counts[video_uuid] = per_video_counts.get(video_uuid, 0) + 1

            return {
                "total_points": len(filtered_rows),
                "total_appearances": len(per_video_counts),
                "start_time_ms": int(filtered_rows[0]["timestamp_ms"]) if filtered_rows else None,
                "end_time_ms": int(filtered_rows[-1]["timestamp_ms"]) if filtered_rows else None,
                "per_video_counts": [
                    {"video_uuid": video_uuid, "point_count": point_count}
                    for video_uuid, point_count in sorted(
                        per_video_counts.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                ],
            }
        except Exception as e:
            logger.error(
                f"get_individual_routes_metadata failed for {individual_uuid}: {e}"
            )
            raise MVRRepositoryError(
                f"get_individual_routes_metadata failed: {e}"
            ) from e

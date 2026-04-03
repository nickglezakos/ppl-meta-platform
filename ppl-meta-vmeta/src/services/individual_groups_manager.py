"""
Individual Groups Manager Service
Manages CRUD operations for individual groups and their members.
"""

import json
import logging
import httpx
import os
import numpy as np
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from models.individual_group import (
    AddGroupMembersRequest,
    AddMembersResponse,
    CheckDuplicatesResponse,
    DuplicateMatch,
    GroupMembership,
    GroupCameraSearchRequest,
    GroupCameraSearchResponse,
    MatchedIndividual,
    IndividualGroup,
    IndividualSummary,
    MergeMembersResponse,
    RemoveMembersResponse,
    UpdateIndividualGroupRequest,
)

logger = logging.getLogger(__name__)


class IndividualGroupsManager:
    """
    Manages individual groups, their members, and related operations.
    
    This service handles:
    - CRUD operations for individual groups
    - Member management (add, remove, list)
    - Group queries and filtering
    - Membership tracking
    """
    
    def __init__(self, db_client):
        """
        Initialize the groups manager.
        
        Args:
            db_client: VmetaDatabaseClient instance for database operations
        """
        self.db = db_client
        self.media_service_url = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000")
        logger.info("IndividualGroupsManager initialized")
    
    @staticmethod
    def _parse_pgvector(embedding_str: str) -> np.ndarray:
        """
        Parse pgvector string format to numpy array.
        
        Args:
            embedding_str: String like '[0.1,0.2,0.3,...]'
            
        Returns:
            Numpy array
        """
        # Remove brackets and split
        values_str = embedding_str.strip('[]')
        values = [float(x) for x in values_str.split(',')]
        return np.array(values)
    
    # ================================================================
    # Group CRUD Operations
    # ================================================================
    
    async def create_group(
        self,
        name: str,
        description: Optional[str],
        created_by: str,
        visibility: str = "private",
        tags: Optional[List[str]] = None,
        initial_member_ids: Optional[List[str]] = None,
    ) -> IndividualGroup:
        """
        Create a new individual group.
        
        Args:
            name: Group name
            description: Optional description
            created_by: User ID who creates the group
            visibility: Group visibility (private, shared, public)
            tags: Optional list of tags
            initial_member_ids: Optional list of initial members
            
        Returns:
            Created IndividualGroup
        """
        logger.info(f"Creating group '{name}' for user {created_by}")
        
        group = IndividualGroup(
            name=name,
            description=description,
            created_by=created_by,
            visibility=visibility,
            tags=tags or [],
            member_ids=[],
            member_count=0,
        )
        
        # Insert group into database
        query = """
        INSERT INTO individual_groups (
            id, name, description, created_by, created_at, updated_at,
            member_count, member_ids, visibility, tags, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
        RETURNING id
        """
        
        async with self.db.pool.acquire() as conn:
            group_id = await conn.fetchval(
                query,
                group.id,
                group.name,
                group.description,
                group.created_by,
                group.created_at,
                group.updated_at,
                group.member_count,
                group.member_ids,
                group.visibility,
                group.tags,
                json.dumps(group.metadata),
            )
        
        # Add initial members if provided
        if initial_member_ids:
            await self.add_members(group_id, initial_member_ids, created_by)
            group = await self.get_group(group_id)
        
        logger.info(f"Group created: {group_id}")
        return group
    
    async def get_group(self, group_id: str) -> Optional[IndividualGroup]:
        """
        Get a group by ID.
        
        Args:
            group_id: Group identifier
            
        Returns:
            IndividualGroup if found, None otherwise
        """
        query = """
        SELECT id, name, description, created_by, created_at, updated_at,
               member_count, member_ids, visibility, tags, cover_individual_id, metadata
        FROM individual_groups
        WHERE id = $1
        """
        
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow(query, group_id)
        
        if not row:
            logger.warning(f"Group not found: {group_id}")
            return None
        
        # Parse metadata from JSONB
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        elif metadata is None:
            metadata = {}
        
        return IndividualGroup(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=row["member_count"],
            member_ids=row["member_ids"] or [],
            visibility=row["visibility"],
            tags=row["tags"] or [],
            cover_individual_id=row["cover_individual_id"],
            metadata=metadata,
        )
    
    async def list_groups(
        self,
        user_id: Optional[str] = None,
        visibility: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[IndividualGroup], int]:
        """
        List groups with optional filtering.
        
        Args:
            user_id: Filter by creator user ID
            visibility: Filter by visibility level
            tags: Filter by tags (any match)
            search: Search in name/description
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (groups list, total count)
        """
        conditions = []
        params = []
        param_counter = 1
        
        if user_id:
            conditions.append(f"created_by = ${param_counter}")
            params.append(user_id)
            param_counter += 1
        
        if visibility:
            conditions.append(f"visibility = ${param_counter}")
            params.append(visibility)
            param_counter += 1
        
        if tags:
            conditions.append(f"tags && ${param_counter}")
            params.append(tags)
            param_counter += 1
        
        if search:
            conditions.append(
                f"(name ILIKE ${param_counter} OR description ILIKE ${param_counter})"
            )
            params.append(f"%{search}%")
            param_counter += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # Count query
        count_query = f"SELECT COUNT(*) FROM individual_groups {where_clause}"
        
        # Main query
        query = f"""
        SELECT id, name, description, created_by, created_at, updated_at,
               member_count, member_ids, visibility, tags, cover_individual_id, metadata
        FROM individual_groups
        {where_clause}
        ORDER BY updated_at DESC
        LIMIT ${param_counter} OFFSET ${param_counter + 1}
        """
        params.extend([limit, skip])
        
        async with self.db.pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params[:-2]) if params[:-2] else await conn.fetchval(count_query)
            rows = await conn.fetch(query, *params)
        
        groups = []
        for row in rows:
            # Parse metadata from JSONB
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata) if metadata else {}
            elif metadata is None:
                metadata = {}
            
            groups.append(IndividualGroup(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                member_count=row["member_count"],
                member_ids=row["member_ids"] or [],
                visibility=row["visibility"],
                tags=row["tags"] or [],
                cover_individual_id=row["cover_individual_id"],
                metadata=metadata,
            ))
        
        return groups, total
    
    async def update_group(
        self, group_id: str, updates: UpdateIndividualGroupRequest
    ) -> Optional[IndividualGroup]:
        """
        Update a group's metadata.
        
        Args:
            group_id: Group identifier
            updates: Fields to update
            
        Returns:
            Updated IndividualGroup if found, None otherwise
        """
        # Build dynamic update query
        set_clauses = ["updated_at = $1"]
        params = [datetime.utcnow()]
        param_counter = 2
        
        if updates.name is not None:
            set_clauses.append(f"name = ${param_counter}")
            params.append(updates.name)
            param_counter += 1
        
        if updates.description is not None:
            set_clauses.append(f"description = ${param_counter}")
            params.append(updates.description)
            param_counter += 1
        
        if updates.visibility is not None:
            set_clauses.append(f"visibility = ${param_counter}")
            params.append(updates.visibility)
            param_counter += 1
        
        if updates.tags is not None:
            set_clauses.append(f"tags = ${param_counter}")
            params.append(updates.tags)
            param_counter += 1
        
        if updates.cover_individual_id is not None:
            set_clauses.append(f"cover_individual_id = ${param_counter}")
            params.append(updates.cover_individual_id)
            param_counter += 1
        
        params.append(group_id)
        
        query = f"""
        UPDATE individual_groups
        SET {', '.join(set_clauses)}
        WHERE id = ${param_counter}
        RETURNING id
        """
        
        async with self.db.pool.acquire() as conn:
            result = await conn.fetchval(query, *params)
        
        if not result:
            logger.warning(f"Group not found for update: {group_id}")
            return None
        
        logger.info(f"Group updated: {group_id}")
        return await self.get_group(group_id)
    
    async def delete_group(self, group_id: str, remove_members: bool = False) -> bool:
        """
        Delete a group.
        
        Args:
            group_id: Group identifier
            remove_members: If True, also delete membership records
            
        Returns:
            True if deleted, False if not found
        """
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # Delete memberships if requested
                if remove_members:
                    await conn.execute(
                        "DELETE FROM group_memberships WHERE group_id = $1",
                        group_id
                    )
                
                # Delete group
                result = await conn.execute(
                    "DELETE FROM individual_groups WHERE id = $1",
                    group_id
                )
        
        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info(f"Group deleted: {group_id}")
        else:
            logger.warning(f"Group not found for deletion: {group_id}")
        
        return deleted
    
    # ================================================================
    # Member Management
    # ================================================================
    
    async def add_members(
        self, group_id: str, individual_ids: List[str], added_by: str, notes: Optional[str] = None
    ) -> AddMembersResponse:
        """
        Add members to a group.
        
        This method will persist individual appearance data to the database if needed.
        This ensures individuals from collections (which may be in-memory only) can be
        added to groups and later analyzed via cross-video analysis.
        
        Args:
            group_id: Group identifier
            individual_ids: List of individual IDs to add
            added_by: User ID performing the action
            notes: Optional notes
            
        Returns:
            AddMembersResponse with counts
        """
        logger.info(f"Adding {len(individual_ids)} members to group {group_id}")
        
        added_count = 0
        skipped_count = 0
        
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # Get current members
                current_members = await conn.fetchval(
                    "SELECT member_ids FROM individual_groups WHERE id = $1",
                    group_id
                )
                
                if current_members is None:
                    raise ValueError(f"Group not found: {group_id}")
                
                current_members_set = set(current_members or [])
                
                # Add new memberships
                for individual_id in individual_ids:
                    if individual_id in current_members_set:
                        skipped_count += 1
                        continue
                    
                    # Check if individual exists in the individuals table
                    individual_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM individuals WHERE individual_uuid = $1)",
                        individual_id
                    )
                    
                    if not individual_exists:
                        # Individual doesn't exist - the UUID is actually an MVR People UUID
                        # (MVR People = "Individuals" in business logic)
                        logger.info(
                            f"Individual {individual_id} does not exist in database. "
                            f"Checking if this is an MVR People UUID..."
                        )
                        
                        try:
                            # Check if this UUID exists in mvr_people table
                            mvr_exists = await conn.fetchval(
                                """
                                SELECT EXISTS(
                                    SELECT 1 FROM mvr_people
                                    WHERE mvr_people_uuid = $1
                                )
                                """,
                                individual_id
                            )
                            
                            if mvr_exists:
                                # This is an MVR People UUID - create individuals record
                                # Generate individual_id for this UUID
                                # Use format: ind_<first8chars>
                                individual_id_str = f"ind_{str(individual_id).replace('-', '')[:8]}"
                                
                                # Get MVR People data for confidence score
                                mvr_data = await conn.fetchrow(
                                    """
                                    SELECT confidence_score, quality_score
                                    FROM mvr_people
                                    WHERE mvr_people_uuid = $1
                                    """,
                                    individual_id
                                )
                                
                                confidence = mvr_data['confidence_score'] if mvr_data else 0.85
                                
                                # Create the individual record with required fields
                                await conn.execute(
                                    """
                                    INSERT INTO individuals (
                                        individual_uuid,
                                        individual_id,
                                        confidence_score,
                                        spatial_signature,
                                        temporal_signature,
                                        created_at
                                    ) VALUES ($1, $2, $3, $4, $5, $6)
                                    ON CONFLICT (individual_uuid) DO NOTHING
                                    """,
                                    individual_id,
                                    individual_id_str,
                                    confidence,
                                    json.dumps({}),  # Empty spatial signature
                                    json.dumps({}),  # Empty temporal signature
                                    datetime.utcnow()
                                )
                                logger.info(
                                    f"Successfully created individual record for MVR People {individual_id} "
                                    f"with confidence {confidence}"
                                )
                            else:
                                logger.error(
                                    f"UUID {individual_id} not found in mvr_people or individuals tables. "
                                    f"Cannot create individual record. Skipping."
                                )
                                skipped_count += 1
                                continue
                        except Exception as e:
                            logger.error(
                                f"Failed to create individual record for {individual_id}: {e}",
                                exc_info=True
                            )
                            skipped_count += 1
                            continue
                    
                    # Check if individual has appearances persisted
                    has_appearances = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM individual_video_appearances WHERE individual_uuid = $1)",
                        individual_id
                    )
                    
                    if not has_appearances:
                        # For MVR People (Individuals in business logic), appearances should already exist
                        # If they don't, we can still add to group - appearances may be linked via different UUIDs
                        logger.warning(
                            f"Individual {individual_id} has no persisted appearances in individual_video_appearances. "
                            f"This is normal for MVR People - appearances are linked via individual_mvr_mapping. "
                            f"Proceeding with group membership."
                        )
                    
                    membership = GroupMembership(
                        group_id=group_id,
                        individual_id=individual_id,
                        added_by=added_by,
                        notes=notes,
                    )
                    
                    await conn.execute(
                        """
                        INSERT INTO group_memberships (
                            id, group_id, individual_id, added_by, added_at, notes
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (group_id, individual_id) DO NOTHING
                        """,
                        membership.id,
                        membership.group_id,
                        membership.individual_id,
                        membership.added_by,
                        membership.added_at,
                        membership.notes,
                    )
                    
                    current_members_set.add(individual_id)
                    added_count += 1
                
                # Update group
                await conn.execute(
                    """
                    UPDATE individual_groups
                    SET member_ids = $1, member_count = $2, updated_at = $3
                    WHERE id = $4
                    """,
                    list(current_members_set),
                    len(current_members_set),
                    datetime.utcnow(),
                    group_id,
                )
        
        logger.info(f"Added {added_count} members, skipped {skipped_count}")
        
        group = await self.get_group(group_id)
        return AddMembersResponse(
            group=group,
            added_count=added_count,
            skipped_count=skipped_count,
        )
    
    async def remove_members(
        self, group_id: str, individual_ids: List[str]
    ) -> RemoveMembersResponse:
        """
        Remove members from a group.
        
        Args:
            group_id: Group identifier
            individual_ids: List of individual IDs to remove
            
        Returns:
            RemoveMembersResponse with count
        """
        logger.info(f"Removing {len(individual_ids)} members from group {group_id}")
        
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # Delete memberships
                result = await conn.execute(
                    """
                    DELETE FROM group_memberships
                    WHERE group_id = $1 AND individual_id = ANY($2)
                    """,
                    group_id,
                    individual_ids,
                )
                
                removed_count = int(result.split()[-1])
                
                # Update group member_ids
                await conn.execute(
                    """
                    UPDATE individual_groups
                    SET member_ids = ARRAY(
                        SELECT unnest(member_ids)
                        EXCEPT
                        SELECT unnest($1::text[])
                    ),
                    member_count = member_count - $2,
                    updated_at = $3
                    WHERE id = $4
                    """,
                    individual_ids,
                    removed_count,
                    datetime.utcnow(),
                    group_id,
                )
        
        logger.info(f"Removed {removed_count} members")
        
        group = await self.get_group(group_id)
        return RemoveMembersResponse(
            group=group,
            removed_count=removed_count,
        )
    
    async def get_group_members(
        self, group_id: str, skip: int = 0, limit: int = 50, sort: str = "added_date"
    ) -> tuple[List[IndividualSummary], int]:
        """
        Get members of a group.
        
        This method automatically cleans up orphaned members (those that were merged
        into super-individuals) and replaces them with their active super-individual.
        
        Args:
            group_id: Group identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort: Sort field (added_date, appearances, last_seen)
            
        Returns:
            Tuple of (members list, total count)
        """
        logger.info(
            "[IG-DEBUG] get_group_members start group_id=%s skip=%s limit=%s sort=%s",
            group_id,
            skip,
            limit,
            sort,
        )

        # First, clean up any orphaned members in this group
        await self._cleanup_orphaned_members(group_id)
        
        # Now fetch the cleaned members list
        query = """
        SELECT 
            gm.individual_id,
            gm.added_at,
            COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid)::text AS mvr_person_uuid,
            COALESCE(
                NULLIF(m_direct.name, ''),
                NULLIF(m_mapped.name, ''),
                NULLIF(m_related.name, ''),
                NULLIF(m_history.new_name, '')
            ) AS name,
            COALESCE(
                m_direct.name_updated_at,
                m_mapped.name_updated_at,
                m_related.name_updated_at,
                m_history.changed_at
            ) AS name_updated_at,
            COALESCE(
                m_direct.name_updated_by,
                m_mapped.name_updated_by,
                m_related.name_updated_by,
                m_history.changed_by
            ) AS name_updated_by
        FROM (
            SELECT 
                gm.group_id,
                gm.individual_id,
                gm.added_at,
                CASE 
                    WHEN gm.individual_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                    THEN gm.individual_id::uuid
                    ELSE NULL
                END AS individual_uuid
            FROM group_memberships gm
            WHERE gm.group_id = $1
            ORDER BY gm.added_at DESC
            LIMIT $2 OFFSET $3
        ) gm
        LEFT JOIN LATERAL (
            SELECT
                COALESCE(
                    (
                        WITH RECURSIVE merge_chain AS (
                            SELECT gm.individual_uuid AS current_uuid, 0 AS depth
                            UNION ALL
                            SELECT mh.super_individual_uuid AS current_uuid, mc.depth + 1 AS depth
                            FROM mvr_merge_hierarchy mh
                            JOIN merge_chain mc ON mh.merged_mvr_uuid = mc.current_uuid
                        )
                        SELECT current_uuid
                        FROM merge_chain
                        ORDER BY depth DESC
                        LIMIT 1
                    ),
                    gm.individual_uuid
                ) AS canonical_uuid
        ) canonical ON TRUE
        LEFT JOIN LATERAL (
            SELECT 
                m.mvr_people_uuid,
                m.name,
                m.name_updated_at,
                m.name_updated_by
            FROM mvr_people m
            WHERE m.mvr_people_uuid = canonical.canonical_uuid
            LIMIT 1
        ) m_direct ON TRUE
        LEFT JOIN LATERAL (
            SELECT 
                m.mvr_people_uuid,
                m.name,
                m.name_updated_at,
                m.name_updated_by
            FROM individual_mvr_mapping imm
            JOIN mvr_people m ON imm.mvr_people_uuid = m.mvr_people_uuid
            WHERE imm.individual_uuid = canonical.canonical_uuid
            ORDER BY imm.is_representative DESC, imm.linked_at DESC
            LIMIT 1
        ) m_mapped ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                m.name,
                m.name_updated_at,
                m.name_updated_by
            FROM (
                SELECT mh.super_individual_uuid AS related_uuid
                FROM mvr_merge_hierarchy mh
                WHERE mh.merged_mvr_uuid = COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid, canonical.canonical_uuid)

                UNION

                SELECT mh2.merged_mvr_uuid AS related_uuid
                FROM mvr_merge_hierarchy mh2
                WHERE mh2.super_individual_uuid = COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid, canonical.canonical_uuid)
            ) rel
            JOIN mvr_people m ON m.mvr_people_uuid = rel.related_uuid
            WHERE m.name IS NOT NULL AND btrim(m.name) <> ''
            ORDER BY m.name_updated_at DESC NULLS LAST
            LIMIT 1
        ) m_related ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                nh.new_name,
                nh.changed_at,
                nh.changed_by
            FROM mvr_people_name_history nh
            WHERE nh.new_name IS NOT NULL
              AND btrim(nh.new_name) <> ''
                            AND nh.mvr_people_uuid = COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid, canonical.canonical_uuid)
            ORDER BY nh.changed_at DESC
            LIMIT 1
        ) m_history ON TRUE
        ORDER BY gm.added_at DESC
        """
        
        count_query = """
        SELECT COUNT(*) FROM group_memberships WHERE group_id = $1
        """
        
        async with self.db.pool.acquire() as conn:
            total = await conn.fetchval(count_query, group_id)
            rows = await conn.fetch(query, group_id, limit, skip)

        logger.info(
            "[IG-DEBUG] get_group_members fetched group_id=%s total=%s page_rows=%s",
            group_id,
            total,
            len(rows),
        )

        for index, row in enumerate(rows):
            logger.info(
                "[IG-DEBUG] member_row idx=%s group_id=%s individual_id=%s resolved_mvr=%s name=%s name_updated_at=%s name_updated_by=%s",
                skip + index + 1,
                group_id,
                row.get("individual_id"),
                row.get("mvr_person_uuid"),
                row.get("name"),
                row.get("name_updated_at"),
                row.get("name_updated_by"),
            )
        
        # TODO: Join with actual persons table to get full individual data
        members = [
            IndividualSummary(
                id=row["individual_id"],
                mvr_person_uuid=row.get("mvr_person_uuid"),
                thumbnail_url=None,
                total_appearances=0,
                last_seen=None,
                group_count=1,
                group_member_number=skip + index + 1,
                name=row.get("name"),
                name_updated_at=row.get("name_updated_at"),
                name_updated_by=row.get("name_updated_by"),
            )
            for index, row in enumerate(rows)
        ]
        
        return members, total

    async def _cleanup_orphaned_members(self, group_id: str) -> None:
        """
        Clean up orphaned members in a group.
        
        This method finds members that have been merged into super-individuals
        (marked as orphaned) and replaces them with their active super-individual.
        It ensures each super-individual appears only once in the group.
        
        Args:
            group_id: Group identifier
        """
        async with self.db.pool.acquire() as conn:
            # Find all orphaned members in this group
            orphaned_members = await conn.fetch("""
                SELECT 
                    gm.individual_id,
                    m.merged_into_mvr_uuid as super_individual_uuid
                FROM group_memberships gm
                JOIN mvr_people m ON gm.individual_id::uuid = m.mvr_people_uuid
                WHERE gm.group_id = $1 
                AND m.is_orphaned = true
                AND m.merged_into_mvr_uuid IS NOT NULL
            """, group_id)
            
            if not orphaned_members:
                return
            
            logger.info(
                f"Found {len(orphaned_members)} orphaned members in group {group_id}. "
                f"Cleaning up..."
            )
            
            for member in orphaned_members:
                orphaned_id = str(member['individual_id'])
                super_id = str(member['super_individual_uuid'])

                canonical_super_row = await conn.fetchrow(
                    """
                    WITH RECURSIVE merge_chain AS (
                        SELECT $1::uuid AS current_uuid, 0 AS depth
                        UNION ALL
                        SELECT mh.super_individual_uuid AS current_uuid, mc.depth + 1 AS depth
                        FROM mvr_merge_hierarchy mh
                        JOIN merge_chain mc ON mh.merged_mvr_uuid = mc.current_uuid
                    )
                    SELECT current_uuid
                    FROM merge_chain
                    ORDER BY depth DESC
                    LIMIT 1
                    """,
                    super_id,
                )
                if canonical_super_row and canonical_super_row.get('current_uuid'):
                    super_id = str(canonical_super_row['current_uuid'])
                
                # Check if super-individual is already in the group
                existing = await conn.fetchval("""
                    SELECT 1 FROM group_memberships 
                    WHERE group_id = $1 AND individual_id = $2
                """, group_id, super_id)
                
                if existing:
                    # Super-individual already exists, just remove the orphaned one
                    await conn.execute("""
                        DELETE FROM group_memberships 
                        WHERE group_id = $1 AND individual_id = $2
                    """, group_id, orphaned_id)
                    logger.info(
                        f"Removed orphaned member {orphaned_id[:8]} from group {group_id} "
                        f"(super-individual {super_id[:8]} already exists)"
                    )
                else:
                    # Replace orphaned member with super-individual
                    await conn.execute("""
                        UPDATE group_memberships 
                        SET individual_id = $1
                        WHERE group_id = $2 AND individual_id = $3
                    """, super_id, group_id, orphaned_id)
                    logger.info(
                        f"Replaced orphaned member {orphaned_id[:8]} with "
                        f"super-individual {super_id[:8]} in group {group_id}"
                    )    
    async def _persist_individual_appearances(self, conn, individual_uuid: str):
        """
        Persist individual appearance data from person objects to the database.
        
        This method is called when an individual from a collection (in-memory only)
        is added to a group. It fetches all person objects for the individual and
        creates entries in the individual_video_appearances table.
        
        Args:
            conn: Database connection
            individual_uuid: UUID of the individual to persist
        """
        # Get all person objects for this individual
        person_objects = await conn.fetch(
            """
            SELECT 
                po.person_object_uuid,
                po.video_uuid,
                po.first_frame_timestamp as start_timestamp,
                po.last_frame_timestamp as end_timestamp,
                po.best_confidence_score as confidence
            FROM person_objects po
            WHERE po.individual_uuid = $1
            ORDER BY po.first_frame_timestamp
            """,
            individual_uuid
        )
        
        if not person_objects:
            logger.warning(
                f"No person objects found for individual {individual_uuid}. "
                f"Cannot persist appearances."
            )
            return
        
        logger.info(
            f"Found {len(person_objects)} person objects for individual {individual_uuid}. "
            f"Persisting to individual_video_appearances..."
        )
        
        # Insert into individual_video_appearances
        for po in person_objects:
            await conn.execute(
                """
                INSERT INTO individual_video_appearances (
                    individual_uuid,
                    video_uuid,
                    person_object_uuid,
                    start_timestamp,
                    end_timestamp,
                    confidence
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (individual_uuid, person_object_uuid) DO NOTHING
                """,
                individual_uuid,
                po['video_uuid'],
                po['person_object_uuid'],
                po['start_timestamp'],
                po['end_timestamp'],
                po['confidence']
            )
        
        logger.info(
            f"Successfully persisted {len(person_objects)} appearances for individual {individual_uuid}"
        )    
    async def get_individual_groups(self, individual_id: str) -> List[IndividualGroup]:
        """
        Get all groups an individual belongs to.
        
        Args:
            individual_id: Individual identifier
            
        Returns:
            List of IndividualGroup
        """
        query = """
        SELECT g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at,
               g.member_count, g.member_ids, g.visibility, g.tags, g.cover_individual_id, g.metadata
        FROM individual_groups g
        JOIN group_memberships gm ON g.id = gm.group_id
        WHERE gm.individual_id = $1
        ORDER BY gm.added_at DESC
        """
        
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(query, individual_id)
        
        return [
            IndividualGroup(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                member_count=row["member_count"],
                member_ids=row["member_ids"] or [],
                visibility=row["visibility"],
                tags=row["tags"] or [],
                cover_individual_id=row["cover_individual_id"],
                metadata=row["metadata"] or {},
            )
            for row in rows
        ]

    async def search_members_in_cameras(
        self,
        group_id: str,
        camera_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        confidence_threshold: float = 0.6,
        auth_token: str = None,
    ) -> GroupCameraSearchResponse:
        """
        Search for group members across multiple camera collections during a time range.
        
        This method aggregates results from multiple cameras by calling search_members_in_camera
        for each camera and merging the results.
        
        Args:
            group_id: Group identifier
            camera_ids: List of camera/collection IDs to search
            start_time: Search start time
            end_time: Search end time
            confidence_threshold: Minimum similarity threshold (0.6 default)
            auth_token: Optional authentication token for media service calls
            
        Returns:
            GroupCameraSearchResponse with aggregated matched members
        """
        logger.info(
            f"Searching for group {group_id} members across {len(camera_ids)} cameras: {camera_ids}"
        )
        
        if not camera_ids:
            raise ValueError("At least one camera_id must be provided")
        
        # Get group details for response
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Group not found: {group_id}")
        
        # Aggregate results from all cameras
        all_matched_individuals = {}  # individual_uuid -> MatchedIndividual
        
        for camera_id in camera_ids:
            try:
                logger.info(f"Searching camera: {camera_id}")
                
                # Search in single camera
                camera_result = await self.search_members_in_camera(
                    group_id=group_id,
                    camera_id=camera_id,
                    start_time=start_time,
                    end_time=end_time,
                    confidence_threshold=confidence_threshold,
                    auth_token=auth_token,
                )
                
                # Merge matched individuals by super-individual (mvr_person_uuid) if available
                for matched in camera_result.matched_individuals:
                    common_uuid = matched.mvr_person_uuid or matched.individual_uuid

                    if common_uuid in all_matched_individuals:
                        existing = all_matched_individuals[common_uuid]
                        existing.total_appearances += matched.total_appearances

                        # Update time range
                        if matched.first_seen < existing.first_seen:
                            existing.first_seen = matched.first_seen
                        if matched.last_seen > existing.last_seen:
                            existing.last_seen = matched.last_seen

                        # Merge appearances list if present
                        if matched.appearances and existing.appearances:
                            existing.appearances.extend(matched.appearances)
                        elif matched.appearances:
                            existing.appearances = matched.appearances

                        # Take max confidence score
                        existing.confidence_score = max(
                            existing.confidence_score,
                            matched.confidence_score
                        )
                    else:
                        # New individual, add to results
                        all_matched_individuals[common_uuid] = matched

                logger.info(
                    f"Camera {camera_id}: found {len(camera_result.matched_individuals)} individuals (merged into {len(all_matched_individuals)} super entries)"
                )
                
            except Exception as e:
                logger.error(f"Failed to search camera {camera_id}: {e}", exc_info=True)
                # Continue with other cameras
                continue
        
        # Build final response
        matched_list = list(all_matched_individuals.values())
        search_session_uuid = f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}"
        
        logger.info(
            f"Multi-camera search complete: {len(matched_list)} unique individuals found "
            f"across {len(camera_ids)} cameras"
        )
        
        return GroupCameraSearchResponse(
            group_id=group_id,
            group_name=group.name,
            camera_ids=camera_ids,
            camera_names=camera_ids,  # Use IDs as names unless enriched
            search_window={
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
            },
            total_group_members=len(group.member_ids) if group.member_ids else 0,
            members_found=len(matched_list),
            matched_individuals=matched_list,
            search_session_uuid=search_session_uuid,
        )

    async def search_members_in_camera(
        self,
        group_id: str,
        camera_id: str,
        start_time: datetime,
        end_time: datetime,
        confidence_threshold: float = 0.6,
        auth_token: str = None,
    ) -> GroupCameraSearchResponse:
        """
        Search for group members in camera footage during a time range.
        
        NEW APPROACH (uses existing vmeta endpoints):
        1. Get video UUIDs from media service for collection/time range
        2. Get MVR people that appear in those videos
        3. For each group member, use vmeta's /individuals/{uuid}/match endpoint
        4. Aggregate results with appearance details
        
        Args:
            group_id: Group identifier
            camera_id: Camera/collection ID to search
            start_time: Search start time
            end_time: Search end time
            confidence_threshold: Minimum similarity threshold (0.6 default)
            auth_token: Optional authentication token for media service calls
            
        Returns:
            GroupCameraSearchResponse with matched members
        """
        import uuid
        
        logger.info(
            f"🔍 Camera Search: Searching for group {group_id} members in camera {camera_id} "
            f"from {start_time} to {end_time} with threshold={confidence_threshold}"
        )
        
        # Get group details and members
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Group not found: {group_id}")
        
        if not group.member_ids:
            logger.info(f"Group {group_id} has no members, returning empty result")
            return GroupCameraSearchResponse(
                group_id=group_id,
                group_name=group.name,
                camera_id=camera_id,
                camera_name=camera_id,  # Will be enriched if camera metadata available
                search_window={
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                },
                total_group_members=0,
                members_found=0,
                matched_individuals=[],
                search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
            )
        
        member_uuids = set(group.member_ids)
        logger.info(f"Searching for {len(member_uuids)} group members (MVR people UUIDs)")
        
        # Step 1: Normalize group member MVR UUIDs to super-individuals
        async with self.db.pool.acquire() as conn:
            # Group member_ids are MVR people UUIDs
            # Normalize them: if MVR is a merged child, get its super-individual
            normalize_query = """
                WITH input_mvr AS (
                    SELECT unnest($1::text[]::uuid[]) AS mvr_uuid
                ),
                normalized AS (
                    -- Keep MVR if it's not a merged child (it's either super-individual or standalone)
                    SELECT im.mvr_uuid
                    FROM input_mvr im
                    WHERE NOT EXISTS (
                        SELECT 1 FROM mvr_merge_hierarchy mh
                        WHERE mh.merged_mvr_uuid = im.mvr_uuid
                    )
                    
                    UNION
                    
                    -- If MVR is a merged child, replace with its super-individual
                    SELECT mh.super_individual_uuid AS mvr_uuid
                    FROM input_mvr im
                    INNER JOIN mvr_merge_hierarchy mh ON mh.merged_mvr_uuid = im.mvr_uuid
                )
                SELECT DISTINCT mvr_uuid FROM normalized
            """
            normalized_rows = await conn.fetch(normalize_query, list(member_uuids))
            member_mvr_uuids = set(str(row['mvr_uuid']) for row in normalized_rows)
            logger.info(f"Group members normalize to {len(member_mvr_uuids)} super-individual MVR people: {member_mvr_uuids}")
        
        if not member_mvr_uuids:
            logger.info(f"No MVR people found for group members, returning empty result")
            return GroupCameraSearchResponse(
                group_id=group_id,
                group_name=group.name,
                camera_id=camera_id,
                camera_name=camera_id,
                search_window={
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                },
                total_group_members=len(member_uuids),
                members_found=0,
                matched_individuals=[],
                search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
            )
        
        # Step 2: Get video UUIDs from media service for this collection and time range
        video_uuids = None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Query media service /api/v1/media/search endpoint
                params = {
                    'collection': camera_id,  # Collection name
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'page_size': 500,  # Get all videos in range
                }
                
                # Prepare headers with auth token if provided
                headers = {}
                if auth_token:
                    # Extract token from 'Bearer token' format if needed
                    token_value = auth_token.replace('Bearer ', '').strip() if auth_token.startswith('Bearer ') else auth_token
                    headers['Authorization'] = f'Bearer {token_value}'
                
                logger.info(f"Fetching videos from media service: {self.media_service_url}/api/v1/media/search params={params} auth={bool(headers.get('Authorization'))}")
                
                response = await client.get(
                    f"{self.media_service_url}/api/v1/media/search",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                videos_data = response.json()
                
                # Extract video UUIDs from response
                # Response is List[MediaResponse] with 'uuid' field
                if isinstance(videos_data, list):
                    video_uuids = [str(video['uuid']) for video in videos_data]
                else:
                    logger.warning(f"Unexpected response format from media service: {type(videos_data)}")
                    video_uuids = []
                
                logger.info(f"Found {len(video_uuids)} videos in collection '{camera_id}' via media service")
                
                if not video_uuids:
                    logger.info(f"No videos found in collection, returning empty result")
                    return GroupCameraSearchResponse(
                        group_id=group_id,
                        group_name=group.name,
                        camera_id=camera_id,
                        camera_name=camera_id,
                        search_window={
                            'start_time': start_time.isoformat(),
                            'end_time': end_time.isoformat(),
                        },
                        total_group_members=len(member_uuids),
                        members_found=0,
                        matched_individuals=[],
                        search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
                    )
        except Exception as e:
            logger.error(f"Failed to fetch videos from media service: {e}", exc_info=True)
            # Fallback: search all MVR people in time range without collection filter
            video_uuids = None
        
        # Step 2: Get ALL MVR people detected in these videos
        async with self.db.pool.acquire() as conn:
            if video_uuids:
                # Get MVR people detected in these videos
                # Use overlap logic: appearance overlaps with search window if:
                # - appearance starts before search window ends AND
                # - appearance ends after search window starts
                mvr_query = """
                    SELECT DISTINCT mvr_people_uuid
                    FROM individual_mvr_mapping
                    WHERE individual_uuid IN (
                        SELECT DISTINCT individual_uuid
                        FROM individual_video_appearances
                        WHERE video_uuid = ANY($1::uuid[])
                          AND start_timestamp < $3
                          AND end_timestamp > $2
                    )
                """
                mvr_rows = await conn.fetch(mvr_query, video_uuids, start_time, end_time)
            else:
                # Fallback: Get all MVR people in time range
                # Use overlap logic
                mvr_query = """
                    SELECT DISTINCT imm.mvr_people_uuid
                    FROM individual_mvr_mapping imm
                    JOIN individual_video_appearances iva ON imm.individual_uuid = iva.individual_uuid
                    WHERE iva.start_timestamp < $2
                      AND iva.end_timestamp > $1
                """
                mvr_rows = await conn.fetch(mvr_query, start_time, end_time)
            
            search_mvr_uuids = [str(row['mvr_people_uuid']) for row in mvr_rows]
            logger.info(f"Found {len(search_mvr_uuids)} MVR people in camera footage (before normalization)")
            
            if not search_mvr_uuids:
                logger.info(f"No MVR people found in time range, returning empty result")
                return GroupCameraSearchResponse(
                    group_id=group_id,
                    group_name=group.name,
                    camera_id=camera_id,
                    camera_name=camera_id,
                    search_window={
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                    },
                    total_group_members=len(member_uuids),
                    members_found=0,
                    matched_individuals=[],
                    search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
                )
            
            # CRITICAL FIX: Normalize camera MVR UUIDs to super-individuals (same as group members)
            normalize_camera_query = """
                WITH input_mvr AS (
                    SELECT unnest($1::text[]::uuid[]) AS mvr_uuid
                ),
                normalized AS (
                    -- Keep MVR if it's not a merged child (it's either super-individual or standalone)
                    SELECT im.mvr_uuid
                    FROM input_mvr im
                    WHERE NOT EXISTS (
                        SELECT 1 FROM mvr_merge_hierarchy mh
                        WHERE mh.merged_mvr_uuid = im.mvr_uuid
                    )
                    
                    UNION
                    
                    -- If MVR is a merged child, replace with its super-individual
                    SELECT mh.super_individual_uuid AS mvr_uuid
                    FROM input_mvr im
                    INNER JOIN mvr_merge_hierarchy mh ON mh.merged_mvr_uuid = im.mvr_uuid
                )
                SELECT DISTINCT mvr_uuid FROM normalized
            """
            normalized_camera_rows = await conn.fetch(normalize_camera_query, search_mvr_uuids)
            search_mvr_uuids = set(str(row['mvr_uuid']) for row in normalized_camera_rows)
            logger.info(f"Camera MVR people normalize to {len(search_mvr_uuids)} super-individuals: {list(search_mvr_uuids)[:5]}")
        
        # Step 3: Use vmeta's MVRMatcher service for comparison
        # Get embeddings for group members first, then use similarity search
        from database.mvr_repository import MVRRepository
        
        mvr_repository = MVRRepository(self.db.pool)
        
        all_matched_mvr_uuids = set()
        
        logger.info(f"🔍 Starting comparison - Group members: {len(member_mvr_uuids)}, Camera MVR people: {len(search_mvr_uuids)}")
        logger.info(f"🔍 Group member super-individual UUIDs: {member_mvr_uuids}")
        logger.info(f"🔍 Camera super-individual UUIDs (sample): {list(search_mvr_uuids)[:5]}")
        
        # STEP 1: Direct super-individual UUID matching (after normalization)
        direct_matches = member_mvr_uuids.intersection(search_mvr_uuids)
        if direct_matches:
            logger.info(f"✅ Direct super-individual UUID matches found: {len(direct_matches)} - {direct_matches}")
            all_matched_mvr_uuids.update(direct_matches)
        else:
            logger.info(f"❌ No direct UUID matches - will use embedding similarity")
        
        # NEW LOGIC: Direct embedding comparison between group members and camera MVR people
        # Instead of searching the entire database, compare group member embeddings directly with camera MVR embeddings
        
        import numpy as np
        
        # Step 1: Get top-3 embeddings for ALL group members
        group_member_embeddings = {}  # member_uuid -> [(embedding, quality, source), ...]
        
        async with self.db.pool.acquire() as conn:
            top_embeddings_query = """
                WITH super_individual_hierarchy AS (
                    -- Get the super-individual itself
                    SELECT mvr_people_uuid, face_quality, face_embedding, created_at, 'super_individual' as source
                    FROM mvr_people
                    WHERE mvr_people_uuid = $1

                    UNION

                    -- Get all merged children
                    SELECT mp.mvr_people_uuid, mp.face_quality, mp.face_embedding, mp.created_at, 'merged_child' as source
                    FROM mvr_people mp
                    JOIN mvr_merge_hierarchy mh ON mh.merged_mvr_uuid = mp.mvr_people_uuid
                    WHERE mh.super_individual_uuid = $1
                )
                SELECT mvr_people_uuid, face_embedding, face_quality, source
                FROM super_individual_hierarchy
                WHERE face_embedding IS NOT NULL
                  AND (face_quality IS NULL OR face_quality >= 0.6)  -- Filter out low-quality embeddings
                ORDER BY
                    face_quality DESC NULLS LAST,
                    created_at DESC
                LIMIT 3
            """
            
            for member_uuid in member_mvr_uuids:
                rows = await conn.fetch(top_embeddings_query, uuid.UUID(member_uuid))
                if rows:
                    embeddings = []
                    for row in rows:
                        emb = self._parse_pgvector(row['face_embedding'])
                        embeddings.append((emb, row['face_quality'] or 0.0, row['source']))
                    group_member_embeddings[member_uuid] = embeddings
                    quality_scores = [f"{q:.2f}" for _, q, _ in embeddings]
                    logger.info(f"🔍 Group member {member_uuid[:8]}: Loaded {len(embeddings)} embeddings (qualities: {quality_scores})")
                else:
                    logger.warning(f"⚠️  No high-quality embeddings (>=0.6) found for group member {member_uuid[:8]}. This member will not be searchable. Consider re-capturing with better lighting/angles.")
            
            # Step 2: Get top-3 embeddings for ALL camera MVR super-individuals
            camera_mvr_embeddings = {}  # camera_super_uuid -> [(embedding, quality, source), ...]
            
            for camera_uuid in search_mvr_uuids:
                rows = await conn.fetch(top_embeddings_query, uuid.UUID(camera_uuid))
                if rows:
                    embeddings = []
                    for row in rows:
                        emb = self._parse_pgvector(row['face_embedding'])
                        embeddings.append((emb, row['face_quality'] or 0.0, row['source']))
                    camera_mvr_embeddings[camera_uuid] = embeddings
                    quality_scores = [f"{q:.2f}" for _, q, _ in embeddings]
                    logger.info(f"🔍 Camera MVR {camera_uuid[:8]}: Loaded {len(embeddings)} embeddings (qualities: {quality_scores})")
                else:
                    logger.warning(f"⚠️  No high-quality embeddings (>=0.6) found for camera MVR {camera_uuid[:8]}. This individual will not be matchable.")
            
            # Step 3: Compare ALL group member embeddings against ALL camera MVR embeddings
            logger.info(f"🔍 Starting direct embedding comparison: {len(group_member_embeddings)} group members vs {len(camera_mvr_embeddings)} camera MVR people")
            
            # Track matches per member for later merging
            member_matches = {}  # member_uuid -> {camera_mvr_uuid: similarity_score}
            
            for member_uuid, member_embs in group_member_embeddings.items():
                best_matches = []  # (camera_uuid, similarity_score)
                all_scores = []  # For debugging: track all similarity scores
                member_matches[member_uuid] = {}  # Initialize for this member
                
                for camera_uuid, camera_embs in camera_mvr_embeddings.items():
                    # Compare all combinations of high-quality embeddings and keep the best score
                    # This allows matching across different capture conditions/angles
                    best_score = 0.0
                    for member_emb, member_q, member_src in member_embs:
                        for camera_emb, camera_q, camera_src in camera_embs:
                            # Compute cosine similarity
                            similarity = float(np.dot(member_emb, camera_emb) / (np.linalg.norm(member_emb) * np.linalg.norm(camera_emb)))
                            if similarity > best_score:
                                best_score = similarity
                    
                    all_scores.append((camera_uuid, best_score))
                    
                    if best_score >= confidence_threshold:
                        best_matches.append((camera_uuid, best_score))
                        member_matches[member_uuid][camera_uuid] = best_score  # Store for merging
                        logger.info(f"✅ Member {member_uuid[:8]} matched camera MVR {camera_uuid[:8]} (similarity: {best_score:.3f})")
                
                if best_matches:
                    # Sort by score and add to matched set
                    best_matches.sort(key=lambda x: x[1], reverse=True)
                    for cam_uuid, score in best_matches:
                        all_matched_mvr_uuids.add(cam_uuid)
                    logger.info(f"🔍 Member {member_uuid[:8]}: Found {len(best_matches)} matches above threshold {confidence_threshold}")
                else:
                    # Show top 5 scores even if below threshold
                    all_scores.sort(key=lambda x: x[1], reverse=True)
                    top_scores = [(cam[:8], f"{score:.3f}") for cam, score in all_scores[:5]]
                    logger.warning(f"🔍 Member {member_uuid[:8]}: No matches found above threshold {confidence_threshold}. Top 5 scores: {top_scores}")

        
        logger.info(f"Found {len(all_matched_mvr_uuids)} unique matched MVR people using direct embedding comparison")
        
        if not all_matched_mvr_uuids:
            return GroupCameraSearchResponse(
                group_id=group_id,
                group_name=group.name,
                camera_id=camera_id,
                camera_name=camera_id,
                search_window={
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                },
                total_group_members=len(member_uuids),
                members_found=0,
                matched_individuals=[],
                search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
            )
        
        # Step 3.5: Merge matched camera MVR people into group member's super-individual
        # For each group member that had matches, merge all matched camera MVR people into that member's super-individual
        async with self.db.pool.acquire() as conn:
            for member_uuid, camera_mvr_matches in member_matches.items():
                if not camera_mvr_matches:
                    continue
                
                # member_uuid is the MVR person UUID (from member_uuids which are MVR UUIDs)
                # This member_uuid is already the super-individual UUID for the group member
                member_super_uuid = member_uuid
                logger.info(f"🔗 Merging {len(camera_mvr_matches)} camera MVR people into member super-individual {member_super_uuid[:8]}")
                
                # Merge each matched camera MVR into the member's super-individual
                for camera_mvr_uuid, similarity_score in camera_mvr_matches.items():
                    # Skip if already the same person
                    if camera_mvr_uuid == member_super_uuid:
                        logger.info(f"  ↳ {camera_mvr_uuid[:8]} is already the super-individual, skipping")
                        continue
                    
                    # Check if this camera MVR is already in a hierarchy
                    check_hierarchy_query = """
                        SELECT super_individual_uuid 
                        FROM mvr_merge_hierarchy 
                        WHERE merged_mvr_uuid = $1
                    """
                    existing_super_row = await conn.fetchrow(check_hierarchy_query, uuid.UUID(camera_mvr_uuid))
                    
                    if existing_super_row:
                        existing_super_uuid = str(existing_super_row['super_individual_uuid'])
                        if existing_super_uuid == member_super_uuid:
                            logger.info(f"  ↳ {camera_mvr_uuid[:8]} already merged into {member_super_uuid[:8]}, skipping")
                            continue
                        else:
                            logger.warning(f"  ↳ {camera_mvr_uuid[:8]} already belongs to different super {existing_super_uuid[:8]}, skipping")
                            continue
                    
                    # Insert merge record
                    try:
                        merge_insert_query = """
                            INSERT INTO mvr_merge_hierarchy (
                                super_individual_uuid,
                                merged_mvr_uuid,
                                similarity_score,
                                merge_timestamp,
                                merge_level
                            ) VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (super_individual_uuid, merged_mvr_uuid) DO NOTHING
                        """
                        await conn.execute(
                            merge_insert_query,
                            uuid.UUID(member_super_uuid),
                            uuid.UUID(camera_mvr_uuid),
                            similarity_score,
                            datetime.utcnow(),
                            1  # merge_level: 1 = direct child
                        )
                        logger.info(f"  ✅ Merged {camera_mvr_uuid[:8]} into {member_super_uuid[:8]} (similarity: {similarity_score:.3f})")
                    except Exception as e:
                        logger.error(f"  ❌ Failed to merge {camera_mvr_uuid[:8]} into {member_super_uuid[:8]}: {e}")
        
        # Step 4: Get individual UUIDs for matched MVR people
        # Expand to all MVR members of any matched super-individual, so appearance sets are complete.
        async with self.db.pool.acquire() as conn:
            # Normalize matched MVRs to super-individuals
            super_mvr_uuids = set()
            if all_matched_mvr_uuids:
                hierarchy_rows = await conn.fetch(
                    """
                        SELECT merged_mvr_uuid, super_individual_uuid
                        FROM mvr_merge_hierarchy
                        WHERE merged_mvr_uuid = ANY($1::uuid[])
                    """,
                    list(all_matched_mvr_uuids)
                )

                merged_to_super = {
                    str(row['merged_mvr_uuid']): str(row['super_individual_uuid'])
                    for row in hierarchy_rows
                }

                for mvr_uuid in all_matched_mvr_uuids:
                    if mvr_uuid in merged_to_super:
                        super_mvr_uuids.add(merged_to_super[mvr_uuid])
                    else:
                        super_mvr_uuids.add(mvr_uuid)

            all_mvr_uuids = set(super_mvr_uuids)
            if super_mvr_uuids:
                child_rows = await conn.fetch(
                    """
                        SELECT merged_mvr_uuid
                        FROM mvr_merge_hierarchy
                        WHERE super_individual_uuid = ANY($1::uuid[])
                    """,
                    list(super_mvr_uuids)
                )

                all_mvr_uuids.update(str(row['merged_mvr_uuid']) for row in child_rows)

            matched_individual_uuids = []
            if all_mvr_uuids:
                individual_mapping_query = """
                    SELECT individual_uuid
                    FROM individual_mvr_mapping
                    WHERE mvr_people_uuid = ANY($1::uuid[])
                """
                individual_rows = await conn.fetch(individual_mapping_query, list(all_mvr_uuids))
                matched_individual_uuids = [str(row['individual_uuid']) for row in individual_rows]

            logger.info(
                f"Matched MVR people map to {len(matched_individual_uuids)} individuals "
                f"(super MVR set {len(all_mvr_uuids)})"
            )

            if not matched_individual_uuids:
                return GroupCameraSearchResponse(
                    group_id=group_id,
                    group_name=group.name,
                    camera_id=camera_id,
                    camera_name=camera_id,
                    search_window={
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                    },
                    total_group_members=len(member_uuids),
                    members_found=0,
                    matched_individuals=[],
                    search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
                )
            
            # Step 5: Get appearance details for matched individuals
            if video_uuids:
                # Get individual appearances by video for route drawing
                # Use overlap logic for timestamp filtering
                appearances_query = """
                    SELECT
                        iva.individual_uuid,
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.confidence
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                      AND iva.video_uuid = ANY($2::uuid[])
                      AND iva.start_timestamp < $4
                      AND iva.end_timestamp > $3
                      AND iva.confidence >= $5
                    ORDER BY iva.individual_uuid, iva.start_timestamp ASC
                """
                appearance_rows = await conn.fetch(
                    appearances_query,
                    matched_individual_uuids,
                    video_uuids,
                    start_time,
                    end_time,
                    confidence_threshold
                )
            else:
                # Fallback: no collection filter
                # Use overlap logic for timestamp filtering
                appearances_query = """
                    SELECT
                        iva.individual_uuid,
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.confidence
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                      AND iva.start_timestamp < $3
                      AND iva.end_timestamp > $2
                      AND iva.confidence >= $4
                    ORDER BY iva.individual_uuid, iva.start_timestamp ASC
                """
                appearance_rows = await conn.fetch(
                    appearances_query,
                    matched_individual_uuids,
                    start_time,
                    end_time,
                    confidence_threshold
                )
            
            # Build matched individuals list by grouping appearances
            from collections import defaultdict
            appearances_by_individual = defaultdict(list)
            
            for row in appearance_rows:
                appearances_by_individual[str(row['individual_uuid'])].append({
                    'video_uuid': str(row['video_uuid']),
                    'person_object_uuid': str(row['person_object_uuid']),
                    'timestamp': row['start_timestamp'].isoformat(),
                    'confidence': float(row['confidence']),
                    'camera_id': camera_id,  # Add camera/collection ID
                    'camera_name': camera_id,  # Use ID as name (can be enriched later)
                })
            
            # Step 6: Post-process to merge individuals that belong to the same super-individual
            # Build individual_uuid -> mvr_people_uuid -> super_individual_uuid mapping
            individual_to_mvr = {}
            mvr_to_super = {}
            
            for individual_uuid in matched_individual_uuids:
                individual_uuid_obj = uuid.UUID(individual_uuid)
                
                # Get MVR UUID for this individual
                mvr_query = """
                    SELECT mvr_people_uuid 
                    FROM individual_mvr_mapping 
                    WHERE individual_uuid = $1
                    LIMIT 1
                """
                mvr_row = await conn.fetchrow(mvr_query, individual_uuid_obj)
                if mvr_row:
                    mvr_uuid = str(mvr_row['mvr_people_uuid'])
                    individual_to_mvr[individual_uuid] = mvr_uuid
                    
                    # Check if this MVR is a merged child of a super-individual
                    super_query = """
                        SELECT super_individual_uuid 
                        FROM mvr_merge_hierarchy 
                        WHERE merged_mvr_uuid = $1
                    """
                    super_row = await conn.fetchrow(super_query, mvr_row['mvr_people_uuid'])
                    if super_row:
                        # This MVR has a super-individual
                        super_uuid = str(super_row['super_individual_uuid'])
                        mvr_to_super[mvr_uuid] = super_uuid
                        logger.info(f"Individual {individual_uuid[:8]} -> MVR {mvr_uuid[:8]} -> Super {super_uuid[:8]}")
                    else:
                        # This MVR is itself a super-individual (or standalone)
                        mvr_to_super[mvr_uuid] = mvr_uuid
            
            # Group appearances by super-individual MVR UUID
            appearances_by_super_mvr = defaultdict(lambda: {
                'appearances': [],
                'individual_uuids': set(),
                'mvr_uuids': set()
            })
            
            for individual_uuid, appearances in appearances_by_individual.items():
                mvr_uuid = individual_to_mvr.get(individual_uuid)
                if not mvr_uuid:
                    continue
                    
                super_mvr_uuid = mvr_to_super.get(mvr_uuid, mvr_uuid)
                appearances_by_super_mvr[super_mvr_uuid]['appearances'].extend(appearances)
                appearances_by_super_mvr[super_mvr_uuid]['individual_uuids'].add(individual_uuid)
                appearances_by_super_mvr[super_mvr_uuid]['mvr_uuids'].add(mvr_uuid)
            
            logger.info(
                f"Merged {len(appearances_by_individual)} individuals into "
                f"{len(appearances_by_super_mvr)} super-individual groups"
            )
            
            # Step 7: Check if any remaining separate super-individuals should be merged
            # If multiple super-individuals have high similarity, merge their appearances
            super_mvr_list = list(appearances_by_super_mvr.keys())
            
            if len(super_mvr_list) > 1:
                logger.info(f"Checking if {len(super_mvr_list)} super-individuals should be merged")
                
                # Get embeddings for all super-individuals
                super_mvr_embeddings = {}
                for super_mvr_uuid in super_mvr_list:
                    embedding_query = """
                        SELECT face_embedding 
                        FROM mvr_people 
                        WHERE mvr_people_uuid = $1 
                          AND face_embedding IS NOT NULL
                    """
                    embedding_row = await conn.fetchrow(embedding_query, uuid.UUID(super_mvr_uuid))
                    if embedding_row and embedding_row['face_embedding']:
                        super_mvr_embeddings[super_mvr_uuid] = self._parse_pgvector(
                            embedding_row['face_embedding']
                        )
                
                # Compare super-individuals and merge if similar
                merge_groups = {}  # super_mvr -> canonical_super_mvr
                for super_mvr in super_mvr_list:
                    merge_groups[super_mvr] = super_mvr  # Default: each is its own group
                
                for i, super_mvr_a in enumerate(super_mvr_list):
                    if super_mvr_a not in super_mvr_embeddings:
                        continue
                        
                    for super_mvr_b in super_mvr_list[i+1:]:
                        if super_mvr_b not in super_mvr_embeddings:
                            continue
                        
                        # Use MVRRepository for comparison
                        matches = await mvr_repository.find_similar_mvr_people(
                            face_embedding=super_mvr_embeddings[super_mvr_a],
                            similarity_threshold=confidence_threshold,
                            max_results=1,
                            exclude_orphaned=True
                        )
                        
                        for match in matches:
                            if str(match['mvr_people_uuid']) == super_mvr_b:
                                similarity = match['similarity_score']
                                logger.info(
                                    f"Super-individuals match: {super_mvr_a[:8]} ~ {super_mvr_b[:8]} "
                                    f"(similarity: {similarity:.3f})"
                                )
                                # Merge b into a
                                merge_groups[super_mvr_b] = merge_groups[super_mvr_a]
                                break
                
                # Apply merges
                final_appearances_by_super = defaultdict(lambda: {
                    'appearances': [],
                    'individual_uuids': set(),
                    'mvr_uuids': set()
                })
                
                for super_mvr_uuid, data in appearances_by_super_mvr.items():
                    canonical_super = merge_groups[super_mvr_uuid]
                    final_appearances_by_super[canonical_super]['appearances'].extend(data['appearances'])
                    final_appearances_by_super[canonical_super]['individual_uuids'].update(data['individual_uuids'])
                    final_appearances_by_super[canonical_super]['mvr_uuids'].update(data['mvr_uuids'])
                
                appearances_by_super_mvr = final_appearances_by_super
                logger.info(f"After cross-MVR merging: {len(appearances_by_super_mvr)} final groups")
            
            # Create one MatchedIndividual per super-individual with all appearances
            matched_individuals = []
            
            for super_mvr_uuid, data in appearances_by_super_mvr.items():
                all_appearances = data['appearances']
                if all_appearances:
                    # Calculate summary stats across all merged appearances
                    all_confidences = [app['confidence'] for app in all_appearances]
                    timestamps = [datetime.fromisoformat(app['timestamp']) for app in all_appearances]
                    
                    # Use first individual UUID as representative (for compatibility)
                    representative_individual = list(data['individual_uuids'])[0]
                    
                    matched_individuals.append(
                        MatchedIndividual(
                            individual_uuid=representative_individual,
                            mvr_person_uuid=super_mvr_uuid,  # Use super-individual UUID
                            total_appearances=len(all_appearances),
                            first_seen=min(timestamps),
                            last_seen=max(timestamps),
                            confidence_score=sum(all_confidences) / len(all_confidences),
                            demographics=None,
                            appearances=all_appearances,  # All appearances across all videos/individuals
                        )
                    )
            
            logger.info(
                f"Found {len(matched_individuals)} of {len(member_uuids)} members in camera {camera_id}"
            )
            
            return GroupCameraSearchResponse(
                group_id=group_id,
                group_name=group.name,
                camera_id=camera_id,
                camera_name=camera_id,
                search_window={
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                },
                total_group_members=len(member_uuids),
                members_found=len(matched_individuals),
                matched_individuals=matched_individuals,
                search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
            )    
    # ================================================================
    # Duplicate Detection & Merge
    # ================================================================
    
    async def check_for_duplicates(
        self,
        group_id: str,
        candidate_mvr_uuid: str,
        similarity_threshold: float = 0.70,
    ) -> CheckDuplicatesResponse:
        """
        Check if candidate MVR person matches existing group members.
        
        Args:
            group_id: Group identifier
            candidate_mvr_uuid: MVR person UUID to check
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            CheckDuplicatesResponse with potential matches
        """
        # Get group
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        # Get candidate's face embedding
        async with self.db.pool.acquire() as conn:
            try:
                candidate_uuid_obj = UUID(candidate_mvr_uuid)
            except ValueError:
                raise ValueError(f"Candidate MVR person {candidate_mvr_uuid} not found")

            resolved_candidate_uuid = candidate_mvr_uuid
            resolution_type = "direct_mvr"

            candidate_row = await conn.fetchrow(
                """
                SELECT mvr_people_uuid, face_embedding, name, is_orphaned
                FROM mvr_people
                WHERE mvr_people_uuid = $1
                """,
                candidate_uuid_obj
            )

            if candidate_row and candidate_row['is_orphaned']:
                super_row = await conn.fetchrow(
                    """
                    SELECT super_individual_uuid
                    FROM mvr_merge_hierarchy
                    WHERE merged_mvr_uuid = $1
                    ORDER BY merged_at DESC
                    LIMIT 1
                    """,
                    candidate_uuid_obj
                )
                if super_row and super_row['super_individual_uuid']:
                    candidate_row = await conn.fetchrow(
                        """
                        SELECT mvr_people_uuid, face_embedding, name, is_orphaned
                        FROM mvr_people
                        WHERE mvr_people_uuid = $1 AND is_orphaned = FALSE
                        """,
                        super_row['super_individual_uuid']
                    )
                    if candidate_row:
                        resolved_candidate_uuid = str(candidate_row['mvr_people_uuid'])
                        resolution_type = "orphaned_mvr_to_super"

            if not candidate_row:
                candidate_row = await conn.fetchrow(
                    """
                    SELECT m.mvr_people_uuid, m.face_embedding, m.name, m.is_orphaned
                    FROM individual_mvr_mapping imm
                    JOIN mvr_people m ON imm.mvr_people_uuid = m.mvr_people_uuid
                    WHERE imm.individual_uuid = $1
                      AND m.is_orphaned = FALSE
                    ORDER BY imm.is_representative DESC, imm.linked_at DESC
                    LIMIT 1
                    """,
                    candidate_uuid_obj
                )
                if candidate_row:
                    resolved_candidate_uuid = str(candidate_row['mvr_people_uuid'])
                    resolution_type = "individual_to_mvr"

            if not candidate_row:
                candidate_row = await conn.fetchrow(
                    """
                    SELECT m.mvr_people_uuid, m.face_embedding, m.name, m.is_orphaned
                    FROM individual_video_appearances iva
                    JOIN individual_mvr_mapping imm ON iva.individual_uuid = imm.individual_uuid
                    JOIN mvr_people m ON imm.mvr_people_uuid = m.mvr_people_uuid
                    WHERE iva.person_object_uuid = $1
                      AND m.is_orphaned = FALSE
                    ORDER BY imm.is_representative DESC, iva.start_timestamp DESC, imm.linked_at DESC
                    LIMIT 1
                    """,
                    candidate_uuid_obj
                )
                if candidate_row:
                    resolved_candidate_uuid = str(candidate_row['mvr_people_uuid'])
                    resolution_type = "person_object_to_mvr"

            if not candidate_row:
                raise ValueError(f"Candidate MVR person {candidate_mvr_uuid} not found")

            if not candidate_row['face_embedding']:
                raise ValueError(f"Candidate MVR person {resolved_candidate_uuid} has no face embedding")

            if resolved_candidate_uuid != candidate_mvr_uuid:
                logger.info(
                    f"Resolved candidate {candidate_mvr_uuid} to active MVR {resolved_candidate_uuid} "
                    f"via {resolution_type}"
                )
            
            candidate_embedding = self._parse_pgvector(candidate_row['face_embedding'])
            
            # Get all group members' embeddings
            member_rows = await conn.fetch(
                """
                WITH group_members AS (
                    SELECT
                        gm.individual_id,
                        gm.added_at,
                        CASE
                            WHEN gm.individual_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                            THEN gm.individual_id::uuid
                            ELSE NULL
                        END AS individual_uuid
                    FROM group_memberships gm
                    WHERE gm.group_id = $1
                )
                SELECT
                    COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid)::text AS resolved_mvr_uuid,
                    COALESCE(m_direct.face_embedding, m_mapped.face_embedding) AS face_embedding,
                    COALESCE(
                        NULLIF(BTRIM(m_direct.name), ''),
                        NULLIF(BTRIM(m_mapped.name), ''),
                        NULLIF(BTRIM(m_related.name), ''),
                        NULLIF(BTRIM(m_history.new_name), '')
                    ) AS effective_name,
                    gm.individual_id,
                    ROW_NUMBER() OVER (ORDER BY gm.added_at DESC, gm.individual_id DESC) AS group_member_number
                FROM group_members gm
                LEFT JOIN LATERAL (
                    SELECT
                        m.mvr_people_uuid,
                        m.face_embedding,
                        m.name
                    FROM mvr_people m
                    WHERE m.mvr_people_uuid = gm.individual_uuid
                      AND m.is_orphaned = FALSE
                    LIMIT 1
                ) m_direct ON TRUE
                LEFT JOIN LATERAL (
                    SELECT
                        m.mvr_people_uuid,
                        m.face_embedding,
                        m.name
                    FROM individual_mvr_mapping imm
                    JOIN mvr_people m ON imm.mvr_people_uuid = m.mvr_people_uuid
                    WHERE imm.individual_uuid = gm.individual_uuid
                      AND m.is_orphaned = FALSE
                    ORDER BY imm.is_representative DESC, imm.linked_at DESC
                    LIMIT 1
                ) m_mapped ON TRUE
                LEFT JOIN LATERAL (
                    SELECT rel_m.name
                    FROM (
                        SELECT mh.super_individual_uuid AS related_uuid
                        FROM mvr_merge_hierarchy mh
                        WHERE mh.merged_mvr_uuid = COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid, gm.individual_uuid)

                        UNION

                        SELECT mh2.merged_mvr_uuid AS related_uuid
                        FROM mvr_merge_hierarchy mh2
                        WHERE mh2.super_individual_uuid = COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid, gm.individual_uuid)
                    ) rel
                    JOIN mvr_people rel_m ON rel_m.mvr_people_uuid = rel.related_uuid
                    WHERE rel_m.name IS NOT NULL AND BTRIM(rel_m.name) <> ''
                    ORDER BY rel_m.name_updated_at DESC NULLS LAST
                    LIMIT 1
                ) m_related ON TRUE
                LEFT JOIN LATERAL (
                    SELECT nh.new_name
                    FROM mvr_people_name_history nh
                    WHERE nh.mvr_people_uuid = COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid, gm.individual_uuid)
                      AND nh.new_name IS NOT NULL
                      AND BTRIM(nh.new_name) <> ''
                    ORDER BY nh.changed_at DESC
                    LIMIT 1
                ) m_history ON TRUE
                WHERE COALESCE(m_direct.mvr_people_uuid, m_mapped.mvr_people_uuid) IS NOT NULL
                """,
                group_id
            )
            
            matches = []
            for member in member_rows:
                # Skip self-comparison
                if str(member['resolved_mvr_uuid']) == resolved_candidate_uuid:
                    continue
                
                member_embedding = self._parse_pgvector(member['face_embedding'])
                similarity = self._cosine_similarity(candidate_embedding, member_embedding)
                
                if similarity >= similarity_threshold:
                    # Determine confidence level
                    if similarity >= 0.90:
                        confidence = "high"
                    elif similarity >= 0.80:
                        confidence = "medium"
                    else:
                        confidence = "low"
                    
                    matches.append(DuplicateMatch(
                        existing_member_id=str(member['resolved_mvr_uuid']),
                        existing_member_name=member['effective_name'],
                        group_member_number=int(member['group_member_number']) if member.get('group_member_number') is not None else None,
                        similarity_score=round(similarity, 4),
                        confidence=confidence,
                    ))
            
            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return CheckDuplicatesResponse(
                has_duplicates=len(matches) > 0,
                matches=matches,
                candidate_mvr_uuid=resolved_candidate_uuid,
                group_id=group_id,
                group_name=group.name,
            )
    
    async def merge_group_members(
        self,
        group_id: str,
        source_mvr_uuid: str,
        target_mvr_uuid: str,
    ) -> MergeMembersResponse:
        """
        Merge two group members into a super-individual.
        
        Args:
            group_id: Group identifier
            source_mvr_uuid: MVR to merge (will be removed from group)
            target_mvr_uuid: MVR to keep (will remain in group)
            
        Returns:
            MergeMembersResponse with merge result
        """
        async with self.db.pool.acquire() as conn:
            # Verify both are members of the group
            memberships = await conn.fetch(
                """
                SELECT individual_id FROM group_memberships
                WHERE group_id = $1 AND individual_id = ANY($2::text[])
                """,
                group_id,
                [source_mvr_uuid, target_mvr_uuid]
            )
            
            if len(memberships) != 2:
                raise ValueError("Both MVR people must be members of the group")
            
            # Import MVR matcher for merge
            from services.mvr_matcher import MVRMatcher
            from database.mvr_repository import MVRRepository
            
            mvr_repo = MVRRepository(self.db.pool)
            mvr_matcher = MVRMatcher(mvr_repo)
            
            # Execute merge (target keeps, source merges into target)
            merge_result = await mvr_matcher.merge_mvr_people(
                source_mvr_uuid=source_mvr_uuid,
                target_mvr_uuid=target_mvr_uuid,
                similarity_score=0.95,  # High confidence merge
                user_initiated=True,
            )
            
            super_individual_uuid = merge_result['winner_mvr_uuid']
            
            # Update group membership: remove source, keep target
            # If target was replaced by super-individual, update to super-individual
            await conn.execute(
                """
                DELETE FROM group_memberships
                WHERE group_id = $1 AND individual_id = $2
                """,
                group_id,
                source_mvr_uuid
            )
            
            # Update target membership to super-individual if different
            if str(super_individual_uuid) != target_mvr_uuid:
                await conn.execute(
                    """
                    UPDATE group_memberships
                    SET individual_id = $1
                    WHERE group_id = $2 AND individual_id = $3
                    """,
                    str(super_individual_uuid),
                    group_id,
                    target_mvr_uuid
                )
            
            # Get final merge count
            super_mvr = await conn.fetchrow(
                """
                SELECT merged_count FROM mvr_people
                WHERE mvr_people_uuid = $1
                """,
                super_individual_uuid
            )
            
            merged_count = super_mvr['merged_count'] if super_mvr else 2
            
            return MergeMembersResponse(
                success=True,
                super_individual_uuid=str(super_individual_uuid),
                merged_count=merged_count,
                group_membership_updated=True,
            )
    
    def _cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
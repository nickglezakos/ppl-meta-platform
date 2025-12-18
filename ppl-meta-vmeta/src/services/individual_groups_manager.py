"""
Individual Groups Manager Service
Manages CRUD operations for individual groups and their members.
"""

import json
import logging
import httpx
import os
import numpy as np
from datetime import datetime
from typing import List, Optional

from models.individual_group import (
    AddGroupMembersRequest,
    AddMembersResponse,
    GroupMembership,
    GroupCameraSearchRequest,
    GroupCameraSearchResponse,
    MatchedIndividual,
    IndividualGroup,
    IndividualSummary,
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
        
        Args:
            group_id: Group identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort: Sort field (added_date, appearances, last_seen)
            
        Returns:
            Tuple of (members list, total count)
        """
        # This is a placeholder - actual implementation would join with
        # persons/individuals table to get full data
        query = """
        SELECT individual_id, added_at
        FROM group_memberships
        WHERE group_id = $1
        ORDER BY added_at DESC
        LIMIT $2 OFFSET $3
        """
        
        count_query = """
        SELECT COUNT(*) FROM group_memberships WHERE group_id = $1
        """
        
        async with self.db.pool.acquire() as conn:
            total = await conn.fetchval(count_query, group_id)
            rows = await conn.fetch(query, group_id, limit, skip)
        
        # TODO: Join with actual persons table to get full individual data
        members = [
            IndividualSummary(
                id=row["individual_id"],
                thumbnail_url=None,
                total_appearances=0,
                last_seen=None,
                group_count=1,
            )
            for row in rows
        ]
        
        return members, total    
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
            f"Searching for group {group_id} members in camera {camera_id} "
            f"from {start_time} to {end_time}"
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
                mvr_query = """
                    SELECT DISTINCT mvr_people_uuid
                    FROM individual_mvr_mapping
                    WHERE individual_uuid IN (
                        SELECT DISTINCT individual_uuid
                        FROM individual_video_appearances
                        WHERE video_uuid = ANY($1::uuid[])
                          AND start_timestamp >= $2
                          AND end_timestamp <= $3
                    )
                """
                mvr_rows = await conn.fetch(mvr_query, video_uuids, start_time, end_time)
            else:
                # Fallback: Get all MVR people in time range
                mvr_query = """
                    SELECT DISTINCT imm.mvr_people_uuid
                    FROM individual_mvr_mapping imm
                    JOIN individual_video_appearances iva ON imm.individual_uuid = iva.individual_uuid
                    WHERE iva.start_timestamp >= $1
                      AND iva.end_timestamp <= $2
                """
                mvr_rows = await conn.fetch(mvr_query, start_time, end_time)
            
            search_mvr_uuids = [str(row['mvr_people_uuid']) for row in mvr_rows]
            logger.info(f"Found {len(search_mvr_uuids)} MVR people in camera footage")
            
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
        
        # Step 3: Use vmeta's MVRMatcher service for comparison
        # Get embeddings for group members first, then use similarity search
        from database.mvr_repository import MVRRepository
        
        mvr_repository = MVRRepository(self.db.pool)
        
        all_matched_mvr_uuids = set()
        
        async with self.db.pool.acquire() as conn:
            for member_uuid in member_uuids:
                try:
                    # Get face embedding for this group member
                    embedding_query = """
                        SELECT face_embedding 
                        FROM mvr_people 
                        WHERE mvr_people_uuid = $1 
                          AND face_embedding IS NOT NULL
                    """
                    embedding_row = await conn.fetchrow(embedding_query, uuid.UUID(member_uuid))
                    
                    if not embedding_row or not embedding_row['face_embedding']:
                        logger.warning(f"No embedding found for member {member_uuid[:8]}")
                        continue
                    
                    # Parse embedding (pgvector format)
                    face_embedding = self._parse_pgvector(embedding_row['face_embedding'])
                    
                    # Use existing MVRRepository method for similarity search
                    # This searches only among the MVR people found in camera footage
                    matches = await mvr_repository.find_similar_mvr_people(
                        face_embedding=face_embedding,
                        similarity_threshold=confidence_threshold,
                        max_results=100,  # Get all matches above threshold
                        exclude_orphaned=True
                    )
                    
                    # Filter matches to only include those from camera footage
                    for match in matches:
                        match_uuid = str(match['mvr_people_uuid'])
                        if match_uuid in search_mvr_uuids:
                            all_matched_mvr_uuids.add(match_uuid)
                            logger.info(
                                f"Member {member_uuid[:8]} matched {match_uuid[:8]} "
                                f"(similarity: {match['similarity_score']:.3f})"
                            )
                            
                except Exception as e:
                    logger.error(f"Failed to match member {member_uuid[:8]}: {e}")
                    continue
        
        logger.info(f"Found {len(all_matched_mvr_uuids)} unique matched MVR people using MVRRepository")
        
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
        
        # Step 4: Get individual UUIDs for matched MVR people
        async with self.db.pool.acquire() as conn:
            matched_individual_uuids = []
            
            for mvr_uuid in all_matched_mvr_uuids:
                individual_mapping_query = """
                    SELECT individual_uuid 
                    FROM individual_mvr_mapping 
                    WHERE mvr_people_uuid = $1
                """
                individual_rows = await conn.fetch(individual_mapping_query, uuid.UUID(mvr_uuid))
                for row in individual_rows:
                    matched_individual_uuids.append(str(row['individual_uuid']))
            
            logger.info(f"Matched MVR people map to {len(matched_individual_uuids)} individuals")
            
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
                      AND iva.start_timestamp >= $3
                      AND iva.end_timestamp <= $4
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
                      AND iva.start_timestamp >= $2
                      AND iva.end_timestamp <= $3
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

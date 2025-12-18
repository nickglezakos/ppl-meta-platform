"""
Individual Groups Manager Service
Manages CRUD operations for individual groups and their members.
"""

import json
import logging
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
        logger.info("IndividualGroupsManager initialized")
    
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
        confidence_threshold: float = 0.7
    ) -> GroupCameraSearchResponse:
        """
        Search for group members in camera footage during a time range.
        
        This method:
        1. Fetches all member individual_uuids for the group
        2. Queries individual_video_appearances for matching appearances
        3. Filters by camera_id (via video metadata) and time range
        4. Returns matched individuals with appearance details
        
        Args:
            group_id: Group identifier
            camera_id: Camera/collection ID to search
            start_time: Search start time
            end_time: Search end time
            confidence_threshold: Minimum confidence for matches
            
        Returns:
            GroupCameraSearchResponse with matched members
        """
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
        logger.info(f"Searching for {len(member_uuids)} group members")
        
        # Query appearances for group members in the specified time range
        # Note: We filter by camera through the video's collection_name
        async with self.db.pool.acquire() as conn:
            query = """
                SELECT DISTINCT
                    iva.individual_uuid,
                    COUNT(DISTINCT iva.person_object_uuid) as total_appearances,
                    MIN(iva.start_timestamp) as first_seen,
                    MAX(iva.end_timestamp) as last_seen,
                    AVG(iva.confidence) as avg_confidence,
                    i.demographics
                FROM individual_video_appearances iva
                JOIN videos v ON iva.video_uuid = v.video_uuid
                LEFT JOIN individuals i ON iva.individual_uuid = i.individual_uuid
                WHERE iva.individual_uuid = ANY($1)
                  AND v.collection_name = $2
                  AND iva.start_timestamp >= $3
                  AND iva.end_timestamp <= $4
                  AND iva.confidence >= $5
                GROUP BY iva.individual_uuid, i.demographics
                ORDER BY first_seen ASC
            """
            
            rows = await conn.fetch(
                query,
                list(member_uuids),
                camera_id,
                start_time,
                end_time,
                confidence_threshold
            )
        
        # Build matched individuals list
        matched_individuals = []
        for row in rows:
            matched_individuals.append(
                MatchedIndividual(
                    individual_uuid=str(row['individual_uuid']),
                    mvr_person_uuid=None,  # Could be enriched if needed
                    total_appearances=row['total_appearances'],
                    first_seen=row['first_seen'],
                    last_seen=row['last_seen'],
                    confidence_score=float(row['avg_confidence']),
                    demographics=row['demographics'] if row['demographics'] else None,
                )
            )
        
        logger.info(
            f"Found {len(matched_individuals)} of {len(member_uuids)} members in camera {camera_id}"
        )
        
        return GroupCameraSearchResponse(
            group_id=group_id,
            group_name=group.name,
            camera_id=camera_id,
            camera_name=camera_id,  # TODO: Fetch actual camera name from cameras service
            search_window={
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
            },
            total_group_members=len(member_uuids),
            members_found=len(matched_individuals),
            matched_individuals=matched_individuals,
            search_session_uuid=f"camera_search_{group_id}_{int(datetime.utcnow().timestamp())}",
        )

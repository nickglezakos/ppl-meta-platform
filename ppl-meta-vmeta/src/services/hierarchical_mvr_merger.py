"""
Hierarchical MVR-People Merger Service
PPL Meta Platform - vmeta service

Implements hierarchical merging of MVR People based on face embedding similarity.
Provides automatic post-search consolidation of duplicate MVR People across batches.

Key Features:
- Similarity matrix calculation (O(N²) optimized with early termination)
- Connected components finding (Union-Find algorithm)
- Quality-based winner selection
- Full merge provenance tracking

Created: December 15, 2025
Author: PPL Meta Platform Team
Version: 2.19.84
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
import numpy as np
from collections import defaultdict

from database.mvr_repository import MVRRepository, MVRRepositoryError
from services.mvr_matcher import MVRMatcher

logger = logging.getLogger(__name__)


class HierarchicalMVRMergerError(Exception):
    """Custom exception for hierarchical merging operations."""
    pass


class UnionFind:
    """
    Union-Find data structure for finding connected components.
    
    Used to identify merge groups from similarity pairs.
    Implements path compression for O(α(n)) ≈ O(1) operations.
    """
    
    def __init__(self, elements: List[Any]):
        """
        Initialize Union-Find structure.
        
        Args:
            elements: List of elements to track
        """
        self.parent = {elem: elem for elem in elements}
        self.rank = {elem: 0 for elem in elements}
    
    def find(self, x: Any) -> Any:
        """
        Find root of element's set with path compression.
        
        Args:
            x: Element to find root for
            
        Returns:
            Root element of x's set
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]
    
    def union(self, x: Any, y: Any) -> None:
        """
        Union two sets by rank.
        
        Args:
            x: First element
            y: Second element
        """
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return
        
        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
    
    def get_groups(self) -> List[List[Any]]:
        """
        Get all connected components as groups.
        
        Returns:
            List of groups, where each group is a list of connected elements
        """
        groups = defaultdict(list)
        for elem in self.parent:
            root = self.find(elem)
            groups[root].append(elem)
        return list(groups.values())


class HierarchicalMVRMerger:
    """
    Hierarchical MVR-People merger.
    
    Implements automatic post-search merging of similar MVR People:
    1. Calculate similarity matrix for all MVR people
    2. Find merge groups using Union-Find
    3. Execute merges within each group (best quality wins)
    4. Return super-individual UUIDs and merge metadata
    """
    
    def __init__(
        self,
        repository: MVRRepository,
        mvr_matcher: MVRMatcher
    ):
        """
        Initialize hierarchical merger.
        
        Args:
            repository: MVR database repository
            mvr_matcher: MVR matcher for quality comparison
        """
        self.repository = repository
        self.mvr_matcher = mvr_matcher
        logger.info("HierarchicalMVRMerger initialized")
    
    async def merge_hierarchical(
        self,
        mvr_uuids: List[UUID],
        similarity_threshold: float = 0.70,
        min_similarity_check: float = 0.50
    ) -> Dict[str, Any]:
        """
        Perform hierarchical merging of MVR People.
        
        Args:
            mvr_uuids: List of MVR UUIDs to merge
            similarity_threshold: Minimum similarity to merge (default 0.70)
            min_similarity_check: Skip comparisons below this (optimization)
            
        Returns:
            Dict containing:
            - super_individuals: List of winning MVR UUIDs
            - merge_groups: List of merge groups with metadata
            - statistics: Merge statistics
        """
        try:
            logger.info(
                f"Starting hierarchical merge of {len(mvr_uuids)} MVR people "
                f"(threshold: {similarity_threshold})"
            )
            
            # Step 1: Fetch all MVR people with embeddings
            mvr_people = await self._fetch_mvr_people(mvr_uuids)
            
            if not mvr_people:
                logger.warning("No MVR people found to merge")
                return {
                    "super_individuals": [],
                    "merge_groups": [],
                    "statistics": {
                        "total_mvr": 0,
                        "super_individuals": 0,
                        "merges_performed": 0
                    }
                }
            
            # Step 2: Calculate similarity matrix
            similarity_matrix = await self._calculate_similarity_matrix(
                mvr_people,
                min_similarity=min_similarity_check
            )
            
            # Step 3: Find merge groups using Union-Find
            merge_groups = self._find_merge_groups(
                mvr_people,
                similarity_matrix,
                similarity_threshold
            )
            
            logger.info(
                f"Found {len(merge_groups)} merge groups from "
                f"{len(mvr_people)} MVR people"
            )
            
            # Step 4: Execute merges within each group
            super_individuals = []
            merge_metadata = []
            merges_performed = 0
            
            for group in merge_groups:
                if len(group) < 2:
                    # Standalone individual - no merge needed
                    super_individuals.append(group[0]["mvr_people_uuid"])
                    merge_metadata.append({
                        "super_individual_uuid": str(group[0]["mvr_people_uuid"]),
                        "merged_mvr_uuids": [],
                        "mvr_count": 1,
                        "is_standalone": True,
                        "winner_quality": group[0]["quality_score"],
                        "similarities": {}
                    })
                    continue
                
                # Merge group
                winner_uuid, merge_info = await self._merge_group(
                    group,
                    similarity_matrix
                )
                
                super_individuals.append(winner_uuid)
                merge_metadata.append(merge_info)
                merges_performed += len(group) - 1
            
            statistics = {
                "total_mvr": len(mvr_people),
                "super_individuals": len(super_individuals),
                "merges_performed": merges_performed,
                "standalone_individuals": sum(
                    1 for m in merge_metadata if m["is_standalone"]
                ),
                "merged_groups": sum(
                    1 for m in merge_metadata if not m["is_standalone"]
                )
            }
            
            logger.info(
                f"Hierarchical merge complete: {statistics['total_mvr']} MVR → "
                f"{statistics['super_individuals']} super-individuals "
                f"({statistics['merges_performed']} merges performed)"
            )
            
            return {
                "super_individuals": [str(uuid) for uuid in super_individuals],
                "merge_groups": merge_metadata,
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"Hierarchical merge failed: {e}", exc_info=True)
            raise HierarchicalMVRMergerError(f"Merge failed: {e}")
    
    async def _fetch_mvr_people(
        self,
        mvr_uuids: List[UUID]
    ) -> List[Dict[str, Any]]:
        """
        Fetch MVR people with face embeddings.
        
        Args:
            mvr_uuids: List of MVR UUIDs to fetch
            
        Returns:
            List of MVR people dicts with embeddings
        """
        async with self.repository.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    mvr_people_uuid,
                    face_embedding,
                    quality_score,
                    confidence_score,
                    featured_individual_uuid,
                    gender,
                    age_min,
                    age_max,
                    is_orphaned
                FROM mvr_people
                WHERE mvr_people_uuid = ANY($1::uuid[])
                    AND NOT is_orphaned
                ORDER BY quality_score DESC
            """, mvr_uuids)
            
            mvr_people = []
            for row in results:
                # Parse pgvector embedding
                embedding_str = row["face_embedding"]
                embedding = self._parse_pgvector(embedding_str)
                
                mvr_people.append({
                    "mvr_people_uuid": row["mvr_people_uuid"],
                    "face_embedding": embedding,
                    "quality_score": row["quality_score"],
                    "confidence_score": row["confidence_score"],
                    "featured_individual_uuid": row["featured_individual_uuid"],
                    "gender": row["gender"],
                    "age_min": row["age_min"],
                    "age_max": row["age_max"]
                })
            
            return mvr_people
    
    def _parse_pgvector(self, embedding_str: str) -> np.ndarray:
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
    
    async def _calculate_similarity_matrix(
        self,
        mvr_people: List[Dict[str, Any]],
        min_similarity: float = 0.50
    ) -> Dict[Tuple[UUID, UUID], float]:
        """
        Calculate pairwise similarity matrix.
        
        Uses cosine similarity with early termination optimization.
        Only stores similarities >= min_similarity (sparse matrix).
        
        Args:
            mvr_people: List of MVR people with embeddings
            min_similarity: Skip similarities below this threshold
            
        Returns:
            Dict mapping (uuid1, uuid2) -> similarity
        """
        logger.info(
            f"Calculating similarity matrix for {len(mvr_people)} MVR people..."
        )
        
        similarity_matrix = {}
        comparisons = 0
        early_terminations = 0
        
        for i in range(len(mvr_people)):
            for j in range(i + 1, len(mvr_people)):
                mvr1 = mvr_people[i]
                mvr2 = mvr_people[j]
                
                # Calculate cosine similarity
                embedding1 = mvr1["face_embedding"]
                embedding2 = mvr2["face_embedding"]
                
                similarity = self._cosine_similarity(embedding1, embedding2)
                comparisons += 1
                
                # Early termination: skip low similarities
                if similarity < min_similarity:
                    early_terminations += 1
                    continue
                
                # Store in both directions for easy lookup
                uuid1 = mvr1["mvr_people_uuid"]
                uuid2 = mvr2["mvr_people_uuid"]
                similarity_matrix[(uuid1, uuid2)] = similarity
                similarity_matrix[(uuid2, uuid1)] = similarity
        
        # Handle edge case: single MVR person (no comparisons)
        if comparisons == 0:
            logger.info(
                f"Similarity matrix calculated: Single MVR person, no comparisons needed"
            )
        else:
            skip_percentage = (early_terminations / comparisons * 100) if comparisons > 0 else 0
            logger.info(
                f"Similarity matrix calculated: {comparisons} comparisons, "
                f"{len(similarity_matrix)//2} pairs stored, "
                f"{early_terminations} early terminations "
                f"({skip_percentage:.1f}% skipped)"
            )
        
        return similarity_matrix
    
    def _cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score [0, 1]
        """
        # Cosine similarity: dot product / (norm1 * norm2)
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        # Clamp to [0, 1] range
        return max(0.0, min(1.0, (similarity + 1) / 2))
    
    def _find_merge_groups(
        self,
        mvr_people: List[Dict[str, Any]],
        similarity_matrix: Dict[Tuple[UUID, UUID], float],
        threshold: float
    ) -> List[List[Dict[str, Any]]]:
        """
        Find merge groups using Union-Find algorithm.
        
        Args:
            mvr_people: List of MVR people
            similarity_matrix: Pairwise similarities
            threshold: Similarity threshold for merging
            
        Returns:
            List of merge groups (each group is a list of MVR people)
        """
        # Create Union-Find structure with UUIDs
        uuids = [mvr["mvr_people_uuid"] for mvr in mvr_people]
        uf = UnionFind(uuids)
        
        # Union similar MVR people
        for (uuid1, uuid2), similarity in similarity_matrix.items():
            if similarity >= threshold:
                uf.union(uuid1, uuid2)
        
        # Get connected components
        uuid_groups = uf.get_groups()
        
        # Map UUIDs back to full MVR people dicts
        uuid_to_mvr = {mvr["mvr_people_uuid"]: mvr for mvr in mvr_people}
        
        merge_groups = []
        for uuid_group in uuid_groups:
            group = [uuid_to_mvr[uuid] for uuid in uuid_group]
            # Sort by quality (best first)
            group.sort(key=lambda x: x["quality_score"], reverse=True)
            merge_groups.append(group)
        
        # Sort groups by size (largest first) then quality
        merge_groups.sort(
            key=lambda g: (len(g), g[0]["quality_score"]),
            reverse=True
        )
        
        return merge_groups
    
    async def _merge_group(
        self,
        group: List[Dict[str, Any]],
        similarity_matrix: Dict[Tuple[UUID, UUID], float]
    ) -> Tuple[UUID, Dict[str, Any]]:
        """
        Merge a group of MVR people.
        
        Selects best quality as winner, marks others as orphaned.
        
        Args:
            group: List of MVR people to merge (sorted by quality)
            similarity_matrix: For calculating similarities to winner
            
        Returns:
            Tuple of (winner_uuid, merge_metadata)
        """
        # Winner is first (highest quality)
        winner = group[0]
        losers = group[1:]
        
        winner_uuid = winner["mvr_people_uuid"]
        
        logger.info(
            f"Merging group of {len(group)} MVR people: "
            f"Winner: {winner_uuid} (quality: {winner['quality_score']:.3f})"
        )
        
        # Calculate similarities to winner
        similarities = {}
        for loser in losers:
            loser_uuid = loser["mvr_people_uuid"]
            sim = similarity_matrix.get((winner_uuid, loser_uuid), 0.0)
            similarities[str(loser_uuid)] = sim
        
        # Mark losers as orphaned
        loser_uuids = [loser["mvr_people_uuid"] for loser in losers]
        await self.repository.bulk_orphan_mvr_people(
            mvr_uuids=loser_uuids,
            merged_into_uuid=winner_uuid
        )
        
        # Build merge metadata
        merge_info = {
            "super_individual_uuid": str(winner_uuid),
            "merged_mvr_uuids": [str(uuid) for uuid in loser_uuids],
            "mvr_count": len(group),
            "is_standalone": False,
            "winner_quality": winner["quality_score"],
            "similarities": similarities,
            "demographics": {
                "gender": winner.get("gender"),
                "age_min": winner.get("age_min"),
                "age_max": winner.get("age_max")
            }
        }
        
        logger.info(f"Group merged successfully: {len(losers)} MVR orphaned")
        
        return winner_uuid, merge_info
    
    async def get_super_individual_hierarchy(
        self,
        super_individual_uuid: UUID
    ) -> Dict[str, Any]:
        """
        Get full hierarchy for a super-individual.
        
        Returns:
            Dict containing:
            - super_individual: Featured MVR person
            - merged_mvr_people: List of merged MVR people
            - all_individuals: All individuals across all MVR
            - total_person_objects: Total detection count
        """
        try:
            # Get super-individual (featured MVR)
            super_individual = await self.repository.get_mvr_people_by_uuid(
                super_individual_uuid
            )
            
            if not super_individual:
                raise HierarchicalMVRMergerError(
                    f"Super-individual {super_individual_uuid} not found"
                )
            
            # Get merged MVR people (those orphaned into this one)
            merged_mvr = await self.repository.get_merged_mvr_people(
                super_individual_uuid
            )
            
            # Get all individuals from super-individual and merged MVR
            all_mvr_uuids = [super_individual_uuid] + [
                mvr["mvr_people_uuid"] for mvr in merged_mvr
            ]
            
            # Get all video appearances (not aggregated individuals)
            all_appearances = []
            total_person_objects = 0
            
            async with self.repository.pool.acquire() as conn:
                # Query to get individual video appearances for all MVR in hierarchy
                query = """
                    SELECT 
                        i.individual_uuid,
                        imm.mvr_people_uuid,
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp as first_seen_timestamp,
                        iva.end_timestamp as last_seen_timestamp,
                        iva.confidence,
                        i.confidence_score,
                        i.created_at
                    FROM individuals i
                    INNER JOIN individual_mvr_mapping imm ON i.individual_uuid = imm.individual_uuid
                    INNER JOIN individual_video_appearances iva ON iva.individual_uuid = i.individual_uuid
                    WHERE imm.mvr_people_uuid = ANY($1::uuid[])
                    ORDER BY iva.start_timestamp
                """
                results = await conn.fetch(query, all_mvr_uuids)
                all_appearances = [dict(r) for r in results]
                total_person_objects = len(all_appearances)
            
            # DEBUG: Log super_individual name fields
            logger.info("=" * 60)
            logger.info("HIERARCHY RESPONSE DEBUG")
            logger.info("=" * 60)
            logger.info(f"Super-individual UUID: {super_individual_uuid}")
            logger.info(f"Super-individual keys: {list(super_individual.keys()) if super_individual else 'None'}")
            logger.info(f"Super-individual name: {super_individual.get('name') if super_individual else 'N/A'}")
            logger.info(f"Name updated at: {super_individual.get('name_updated_at') if super_individual else 'N/A'}")
            logger.info(f"Name updated by: {super_individual.get('name_updated_by') if super_individual else 'N/A'}")
            logger.info("=" * 60)
            
            return {
                "super_individual": super_individual,
                "merged_mvr_people": merged_mvr,
                "all_individuals": all_appearances,  # Now contains video_uuid for each appearance
                "total_person_objects": total_person_objects,
                "mvr_count": len(all_mvr_uuids),
                "unique_videos": len(set(
                    app["video_uuid"] for app in all_appearances
                    if app.get("video_uuid")
                ))
            }
            
        except Exception as e:
            logger.error(
                f"Failed to get hierarchy for {super_individual_uuid}: {e}",
                exc_info=True
            )
            raise HierarchicalMVRMergerError(
                f"Failed to get hierarchy: {e}"
            )

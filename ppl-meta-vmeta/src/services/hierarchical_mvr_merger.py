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
        self.gender_conflict_min_confidence = 0.80
        # Similarity threshold above which an unknown-gender + known-gender
        # pair is treated as a contamination suspect and blocked from merging.
        # See: docs/modules/MVR merge/EMBEDDING_CONTAMINATION.md
        self.contamination_similarity_threshold = 0.70
        logger.info("HierarchicalMVRMerger initialized")
    
    async def merge_hierarchical(
        self,
        mvr_uuids: List[UUID],
        similarity_threshold: float = 0.70,
        min_similarity_check: float = 0.50,
        force_merge: bool = False
    ) -> Dict[str, Any]:
        """
        Perform hierarchical merging of MVR People.
        
        Args:
            mvr_uuids: List of MVR UUIDs to merge
            similarity_threshold: Minimum similarity to merge (default 0.70)
            min_similarity_check: Skip comparisons below this (optimization)
            force_merge: When True, bypass similarity checks and merge all
                         provided UUIDs into one group unconditionally.
                         Intended for user-initiated manual merges.
            
        Returns:
            Dict containing:
            - super_individuals: List of winning MVR UUIDs
            - merge_groups: List of merge groups with metadata
            - statistics: Merge statistics
        """
        try:
            logger.info(
                f"Starting hierarchical merge of {len(mvr_uuids)} MVR people "
                f"(threshold: {similarity_threshold}, force_merge: {force_merge})"
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
            
            if force_merge:
                # User-initiated manual merge: skip similarity checks entirely
                # and treat all provided MVRs as one group.
                logger.info(
                    f"force_merge=True — bypassing similarity matrix; "
                    f"treating all {len(mvr_people)} MVR people as one group"
                )
                mvr_people_sorted = sorted(
                    mvr_people, key=lambda x: x["quality_score"], reverse=True
                )
                merge_groups = [mvr_people_sorted] if len(mvr_people_sorted) > 1 else [[mvr_people_sorted[0]]]
                # Provide a dummy similarity matrix so _merge_group can still
                # attach similarities to the metadata (use 0.0 for all pairs).
                similarity_matrix: Dict = {}
            else:
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

    async def preview_hierarchical_merge(
        self,
        mvr_uuids: List[UUID],
        similarity_threshold: float = 0.70,
        min_similarity_check: float = 0.50,
        force_merge: bool = False,
    ) -> Dict[str, Any]:
        """Build hierarchical merge groups without writing any persisted state."""
        try:
            logger.info(
                f"Previewing hierarchical merge of {len(mvr_uuids)} MVR people "
                f"(threshold: {similarity_threshold}, force_merge: {force_merge})"
            )

            mvr_people = await self._fetch_mvr_people(mvr_uuids)

            if not mvr_people:
                return {
                    "super_individuals": [],
                    "merge_groups": [],
                    "statistics": {
                        "total_mvr": 0,
                        "super_individuals": 0,
                        "merges_performed": 0,
                        "standalone_individuals": 0,
                        "merged_groups": 0,
                    },
                }

            if force_merge:
                mvr_people_sorted = sorted(
                    mvr_people, key=lambda x: x["quality_score"], reverse=True
                )
                merge_groups = (
                    [mvr_people_sorted]
                    if len(mvr_people_sorted) > 1
                    else [[mvr_people_sorted[0]]]
                )
                similarity_matrix: Dict = {}
            else:
                similarity_matrix = await self._calculate_similarity_matrix(
                    mvr_people,
                    min_similarity=min_similarity_check,
                )
                merge_groups = self._find_merge_groups(
                    mvr_people,
                    similarity_matrix,
                    similarity_threshold,
                )

            merge_metadata = []
            super_individuals = []

            for group in merge_groups:
                winner = group[0]
                winner_uuid = winner["mvr_people_uuid"]
                super_individuals.append(str(winner_uuid))

                merged_mvr_uuids = [
                    str(member["mvr_people_uuid"]) for member in group[1:]
                ]
                similarities = {
                    str(member["mvr_people_uuid"]): similarity_matrix.get(
                        (winner_uuid, member["mvr_people_uuid"]),
                        0.0,
                    )
                    for member in group[1:]
                }

                merge_metadata.append(
                    {
                        "super_individual_uuid": str(winner_uuid),
                        "merged_mvr_uuids": merged_mvr_uuids,
                        "mvr_count": len(group),
                        "is_standalone": len(group) == 1,
                        "winner_quality": winner["quality_score"],
                        "similarities": similarities,
                        "demographics": self._select_best_demographics(group),
                    }
                )

            statistics = {
                "total_mvr": len(mvr_people),
                "super_individuals": len(super_individuals),
                "merges_performed": sum(max(len(group) - 1, 0) for group in merge_groups),
                "standalone_individuals": sum(1 for group in merge_groups if len(group) == 1),
                "merged_groups": sum(1 for group in merge_groups if len(group) > 1),
            }

            return {
                "super_individuals": super_individuals,
                "merge_groups": merge_metadata,
                "statistics": statistics,
            }
        except Exception as e:
            logger.error(f"Hierarchical merge preview failed: {e}", exc_info=True)
            raise HierarchicalMVRMergerError(f"Merge preview failed: {e}")
    
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
                    gender_confidence,
                    age_min,
                    age_max,
                    is_orphaned
                FROM mvr_people
                WHERE mvr_people_uuid = ANY($1::uuid[])
                    AND NOT is_orphaned
                ORDER BY quality_score DESC
            """, mvr_uuids)

            individual_demographics_rows = await conn.fetch("""
                SELECT
                    imm.mvr_people_uuid,
                    i.gender_estimate,
                    i.age_estimate,
                    i.confidence_score
                FROM individual_mvr_mapping imm
                INNER JOIN individuals i ON i.individual_uuid = imm.individual_uuid
                WHERE imm.mvr_people_uuid = ANY($1::uuid[])
            """, mvr_uuids)

            demographics_by_mvr: Dict[UUID, Dict[str, Any]] = defaultdict(
                lambda: {
                    "genders": [],
                    "ages": [],
                }
            )
            for row in individual_demographics_rows:
                bucket = demographics_by_mvr[row["mvr_people_uuid"]]
                gender = self._normalize_gender(row["gender_estimate"])
                if gender is not None:
                    bucket["genders"].append(gender)
                age_estimate = row["age_estimate"]
                if isinstance(age_estimate, int) and age_estimate >= 0:
                    bucket["ages"].append(age_estimate)
            
            mvr_people = []
            for row in results:
                # Parse pgvector embedding
                embedding_str = row["face_embedding"]
                embedding = self._parse_pgvector(embedding_str)

                linked_demo = demographics_by_mvr[row["mvr_people_uuid"]]
                linked_genders = linked_demo["genders"]
                linked_ages = linked_demo["ages"]
                linked_gender_consensus = None
                linked_gender_conflict = False
                if linked_genders:
                    distinct_genders = set(linked_genders)
                    if len(distinct_genders) == 1:
                        linked_gender_consensus = linked_genders[0]
                    else:
                        linked_gender_conflict = True

                effective_gender = (
                    linked_gender_consensus
                    if linked_gender_consensus is not None
                    else row["gender"]
                )
                effective_age_min = (
                    min(linked_ages) if linked_ages else row["age_min"]
                )
                effective_age_max = (
                    max(linked_ages) if linked_ages else row["age_max"]
                )
                
                mvr_people.append({
                    "mvr_people_uuid": row["mvr_people_uuid"],
                    "face_embedding": embedding,
                    "quality_score": row["quality_score"],
                    "confidence_score": row["confidence_score"],
                    "featured_individual_uuid": row["featured_individual_uuid"],
                    "gender": effective_gender,
                    "gender_confidence": row["gender_confidence"],
                    "age_min": effective_age_min,
                    "age_max": effective_age_max,
                    "linked_individual_gender": linked_gender_consensus,
                    "linked_individual_gender_conflict": linked_gender_conflict,
                    "linked_individual_gender_count": len(linked_genders),
                    "linked_individual_age_count": len(linked_ages),
                })
            
            return mvr_people

    def _effective_gender_source(self, mvr: Dict[str, Any]) -> Optional[str]:
        linked_gender = self._normalize_gender(mvr.get("linked_individual_gender"))
        if linked_gender is not None:
            return linked_gender
        return self._normalize_gender(mvr.get("gender"))
    
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
        uuid_to_mvr = {mvr["mvr_people_uuid"]: mvr for mvr in mvr_people}
        blocked_gender_pairs = 0
        contamination_blocked = 0
        
        # Union similar MVR people
        for (uuid1, uuid2), similarity in similarity_matrix.items():
            if similarity >= threshold:
                if not self._can_auto_merge_by_gender(
                    uuid_to_mvr[uuid1],
                    uuid_to_mvr[uuid2]
                ):
                    blocked_gender_pairs += 1
                    continue
                # Fix 4: block merges that show signs of embedding contamination
                # (one unknown gender + one confident known gender at high similarity).
                # See: docs/modules/MVR merge/EMBEDDING_CONTAMINATION.md
                if self._is_contamination_suspect(
                    uuid_to_mvr[uuid1],
                    uuid_to_mvr[uuid2],
                    similarity
                ):
                    contamination_blocked += 1
                    logger.warning(
                        f"Blocked contamination-suspect merge: "
                        f"{str(uuid1)[:8]} "
                        f"(gender={uuid_to_mvr[uuid1].get('gender')}, "
                        f"conf={uuid_to_mvr[uuid1].get('gender_confidence')}) ↔ "
                        f"{str(uuid2)[:8]} "
                        f"(gender={uuid_to_mvr[uuid2].get('gender')}, "
                        f"conf={uuid_to_mvr[uuid2].get('gender_confidence')}) "
                        f"similarity={similarity:.3f}"
                    )
                    continue
                uf.union(uuid1, uuid2)
        
        # Get connected components
        uuid_groups = uf.get_groups()
        
        if blocked_gender_pairs > 0:
            logger.info(
                f"Blocked {blocked_gender_pairs} high-confidence cross-gender pair(s) "
                f"from auto-merge"
            )
        if contamination_blocked > 0:
            logger.info(
                f"Blocked {contamination_blocked} contamination-suspect pair(s) "
                f"(unknown gender + confident known gender at similarity "
                f">= {self.contamination_similarity_threshold})"
            )

        # Map UUIDs back to full MVR people dicts
        merge_groups = []
        for uuid_group in uuid_groups:
            group = [uuid_to_mvr[uuid] for uuid in uuid_group]
            # Sort by quality (best first)
            group.sort(key=lambda x: x["quality_score"], reverse=True)
            refined_groups = self._split_component_by_anchor_similarity(
                group,
                similarity_matrix,
                threshold,
            )
            merge_groups.extend(refined_groups)
        
        # Sort groups by size (largest first) then quality
        merge_groups.sort(
            key=lambda g: (len(g), g[0]["quality_score"]),
            reverse=True
        )
        
        return merge_groups

    def _split_component_by_anchor_similarity(
        self,
        group: List[Dict[str, Any]],
        similarity_matrix: Dict[Tuple[UUID, UUID], float],
        threshold: float,
    ) -> List[List[Dict[str, Any]]]:
        """
        Split a connected component into conservative anchor-based groups.

        Union-Find connected components are too permissive for auto-merge
        because a single bridge pair can chain many weakly related MVRs into one
        winner. Before persisting merges, require every loser in a merged group
        to have a direct similarity edge to the chosen anchor.
        """
        if len(group) < 2:
            return [group]

        remaining = list(group)
        refined_groups: List[List[Dict[str, Any]]] = []

        while remaining:
            anchor = remaining.pop(0)
            anchor_uuid = anchor["mvr_people_uuid"]
            anchor_group = [anchor]
            still_unassigned: List[Dict[str, Any]] = []

            for candidate in remaining:
                candidate_uuid = candidate["mvr_people_uuid"]
                similarity = similarity_matrix.get((anchor_uuid, candidate_uuid))
                if similarity is None or similarity < threshold:
                    still_unassigned.append(candidate)
                    continue
                if not self._can_auto_merge_by_gender(anchor, candidate):
                    still_unassigned.append(candidate)
                    continue
                if self._is_contamination_suspect(anchor, candidate, similarity):
                    still_unassigned.append(candidate)
                    continue
                anchor_group.append(candidate)

            anchor_group.sort(key=lambda x: x["quality_score"], reverse=True)
            refined_groups.append(anchor_group)
            remaining = still_unassigned

        return refined_groups

    def _can_auto_merge_by_gender(
        self,
        mvr1: Dict[str, Any],
        mvr2: Dict[str, Any]
    ) -> bool:
        """Block only high-confidence male/female conflicts during automatic grouping."""
        gender1 = self._effective_gender_source(mvr1)
        gender2 = self._effective_gender_source(mvr2)

        # When both MVRs have consistent linked-individual gender evidence,
        # treat that upstream single-video evidence as authoritative enough to block.
        if (
            mvr1.get("linked_individual_gender") is not None
            and mvr2.get("linked_individual_gender") is not None
            and gender1 is not None
            and gender2 is not None
            and gender1 != gender2
        ):
            return False

        # Unknown or missing gender should not block merges.
        if gender1 is None or gender2 is None:
            return True

        # Same confident gender is merge-eligible.
        if gender1 == gender2:
            return True

        conf1 = self._safe_float(mvr1.get("gender_confidence"))
        conf2 = self._safe_float(mvr2.get("gender_confidence"))
        if conf1 is None or conf2 is None:
            return True

        # Only block if both labels are confident and conflicting.
        return not (
            conf1 >= self.gender_conflict_min_confidence
            and conf2 >= self.gender_conflict_min_confidence
            and gender1 != gender2
        )

    def _is_contamination_suspect(
        self,
        mvr1: Dict[str, Any],
        mvr2: Dict[str, Any],
        similarity: float
    ) -> bool:
        """
        Detect embedding pairs likely contaminated by a multi-face crop.

        Triggers when one MVR has gender=unknown (a known symptom of crop
        contamination — the gender classifier also saw the wrong face and
        returned low confidence) and the other has a high-confidence known
        gender, AND their embedding similarity is >= contamination_similarity_threshold.

        This combination is the fingerprint of the bug described in:
        docs/modules/MVR merge/EMBEDDING_CONTAMINATION.md

        Returns True to block the merge; False to allow it.
        """
        gender1 = self._effective_gender_source(mvr1)
        gender2 = self._effective_gender_source(mvr2)

        # Only suspect when exactly one is unknown and the other is known
        one_unknown_one_known = (gender1 is None) != (gender2 is None)
        if not one_unknown_one_known:
            return False

        known_conf = (
            self._safe_float(mvr2.get("gender_confidence"))
            if gender1 is None
            else self._safe_float(mvr1.get("gender_confidence"))
        )
        if known_conf is None:
            return False

        return (
            known_conf >= self.gender_conflict_min_confidence
            and similarity >= self.contamination_similarity_threshold
        )

    def _normalize_gender(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        gender = str(value).strip().lower()
        if gender in {"male", "female"}:
            return gender
        return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
    
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
        
        # Select best demographics from all MVR people in group
        # Priority: highest quality MVR with non-null demographics
        best_demographics = self._select_best_demographics(group)
        
        # Build merge metadata
        merge_info = {
            "super_individual_uuid": str(winner_uuid),
            "merged_mvr_uuids": [str(uuid) for uuid in loser_uuids],
            "mvr_count": len(group),
            "is_standalone": False,
            "winner_quality": winner["quality_score"],
            "similarities": similarities,
            "demographics": best_demographics
        }
        
        logger.info(f"Group merged successfully: {len(losers)} MVR orphaned")
        
        return winner_uuid, merge_info
    
    def _select_best_demographics(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select best demographics from a group of MVR people.
        
        Strategy:
        1. Find MVR with best quality that has gender (if any)
        2. Find MVR with best quality that has age (if any)
        3. If no valid demographics, return None values
        
        Args:
            group: List of MVR people (already sorted by quality_score DESC)
            
        Returns:
            Dict with gender, age_min, age_max from best quality sources
        """
        best_gender = None
        best_age_min = None
        best_age_max = None
        
        # Group is already sorted by quality_score DESC
        # Find best quality MVR with valid gender
        for mvr in group:
            if best_gender is None and mvr.get("gender") is not None:
                best_gender = mvr["gender"]
            if best_age_min is None and mvr.get("age_min") is not None and mvr.get("age_max") is not None:
                best_age_min = mvr["age_min"]
                best_age_max = mvr["age_max"]
            # Early exit if we found both
            if best_gender is not None and best_age_min is not None:
                break
        
        return {
            "gender": best_gender,
            "age_min": best_age_min,
            "age_max": best_age_max
        }
    
    async def get_super_individual_hierarchy(
        self,
        super_individual_uuid: UUID,
        merged_page: int = 1,
        merged_page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Get full hierarchy for a super-individual.
        
        Returns:
            Dict containing:
            - super_individual: Featured MVR person
            - merged_mvr_people: Paginated list of merged MVR people for this page
            - merged_children_total: Total count of all merged children
            - merged_children_page: Current page number
            - merged_children_page_size: Page size used
            - all_individuals: All individuals across all MVR (not paginated)
            - total_person_objects: Total detection count
        """
        try:
            requested_mvr_uuid = super_individual_uuid

            # Get the requested row first. If it is an orphan, resolve it to the
            # canonical root so callers do not accidentally treat a child UUID as an
            # independent hierarchy head.
            super_individual = await self.repository.get_mvr_people_by_uuid(
                requested_mvr_uuid
            )
            
            if not super_individual:
                raise HierarchicalMVRMergerError(
                    f"Super-individual {requested_mvr_uuid} not found"
                )

            resolved_super_individual_uuid = requested_mvr_uuid
            requested_mvr_was_orphaned = bool(
                super_individual.get("is_orphaned")
            )

            if requested_mvr_was_orphaned and super_individual.get("merged_into_mvr_uuid"):
                async with self.repository.pool.acquire() as conn:
                    root_row = await conn.fetchrow(
                        """
                        WITH RECURSIVE root_chain AS (
                            SELECT mvr_people_uuid, merged_into_mvr_uuid, 0 AS depth
                            FROM mvr_people
                            WHERE mvr_people_uuid = $1

                            UNION ALL

                            SELECT parent.mvr_people_uuid, parent.merged_into_mvr_uuid, rc.depth + 1
                            FROM root_chain rc
                            INNER JOIN mvr_people parent
                                ON parent.mvr_people_uuid = rc.merged_into_mvr_uuid
                            WHERE rc.merged_into_mvr_uuid IS NOT NULL
                                AND rc.depth < 20
                        )
                        SELECT mvr_people_uuid
                        FROM root_chain
                        WHERE merged_into_mvr_uuid IS NULL
                        ORDER BY depth DESC
                        LIMIT 1
                        """,
                        requested_mvr_uuid,
                    )

                if root_row and root_row["mvr_people_uuid"] != requested_mvr_uuid:
                    resolved_super_individual_uuid = root_row["mvr_people_uuid"]
                    super_individual = await self.repository.get_mvr_people_by_uuid(
                        resolved_super_individual_uuid
                    )
                    if not super_individual:
                        raise HierarchicalMVRMergerError(
                            f"Resolved root {resolved_super_individual_uuid} not found"
                        )

            super_individual_uuid = resolved_super_individual_uuid
            
            # Get paginated merged MVR people (those orphaned into this one)
            merged_result = await self.repository.get_merged_mvr_people(
                super_individual_uuid,
                page=merged_page,
                page_size=merged_page_size,
            )
            merged_mvr = merged_result["items"]
            merged_children_total: int = merged_result["total"]
            
            # For appearances/stats, we need ALL children UUIDs (not just this page).
            # Build the full UUID list directly via a lightweight query.
            all_mvr_uuids: List[UUID]
            all_appearances = []
            total_person_objects = 0
            
            async with self.repository.pool.acquire() as conn:
                all_children_rows = await conn.fetch("""
                    SELECT mvr_people_uuid
                    FROM mvr_people
                    WHERE merged_into_mvr_uuid = $1
                        AND is_orphaned = TRUE
                """, super_individual_uuid)
                all_mvr_uuids = [super_individual_uuid] + [
                    row["mvr_people_uuid"] for row in all_children_rows
                ]
            
            # Get all video appearances (not paginated – needed for aggregate stats)
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
                "requested_mvr_uuid": str(requested_mvr_uuid),
                "resolved_super_individual_uuid": str(resolved_super_individual_uuid),
                "requested_mvr_was_orphaned": requested_mvr_was_orphaned,
                "merged_mvr_people": merged_mvr,
                # Pagination metadata for merged children
                "merged_children_total": merged_children_total,
                "merged_children_page": merged_page,
                "merged_children_page_size": merged_page_size,
                "merged_children_has_more": (
                    merged_page * merged_page_size < merged_children_total
                ),
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

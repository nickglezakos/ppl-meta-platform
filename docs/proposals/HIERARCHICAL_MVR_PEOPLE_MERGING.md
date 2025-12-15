# Hierarchical MVR People Merging - Technical Proposal

**Document Version:** 1.0  
**Created:** December 15, 2025  
**Author:** PPL Meta Development Team  
**Status:** Proposal - Awaiting Approval

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Proposed Solution](#proposed-solution)
4. [Database Schema Changes](#database-schema-changes)
5. [Backend Implementation](#backend-implementation)
6. [Frontend Implementation](#frontend-implementation)
7. [API Changes](#api-changes)
8. [Migration Strategy](#migration-strategy)
9. [Testing Strategy](#testing-strategy)
10. [Performance Considerations](#performance-considerations)
11. [Timeline & Milestones](#timeline--milestones)

---

## Executive Summary

### Problem Statement

Currently, the Cross-Video Individual Analysis screen displays MVR People results from batch processing (groups of 3-5 videos). These results are cached and sorted by source videos. However, the system lacks the ability to:

1. **Automatically merge similar MVR People** across different batch results using a similarity threshold
2. **Present a hierarchical view** showing merge relationships
3. **Track merge provenance** to understand which individuals were consolidated at which level

### Current Hierarchy (2 Levels)

```
MVR Person (Individual)
└── Person Objects (detections in frames)
```

### Proposed Hierarchy (3 Levels + Standalone)

```
Merged MVR Person (Super-Individual) [🔵 Blue Badge]
└── MVR Person (Individual) 
    └── Person Objects (detections in frames)

Standalone MVR Person (Individual) [⚫ Grey Badge]
└── Person Objects (detections in frames)
```

**Visual Distinction:**
- **🔵 Blue Badge + "X batches merged" chip**: Merged super-individual (3-tier hierarchy)
- **⚫ Grey Badge + "Standalone individual" chip**: Single MVR person with no similar matches (2-tier hierarchy)
- **Both shown at Level 1** in Individuals tab with equal visual weight (elevation 4)

### Key Benefits

✅ **Reduced Duplicates**: Automatically consolidate the same person appearing in different batch results  
✅ **Better UX**: Users see unique people instead of duplicate entries  
✅ **Complete Coverage**: Both merged AND standalone individuals clearly labeled and distinguished
✅ **Audit Trail**: Full merge provenance with similarity scores  
✅ **Configurable**: User-adjustable similarity threshold per search  
✅ **Backward Compatible**: Existing 2-level hierarchy still works for non-merged data

---

## Current Architecture Analysis

### Batch Processing Flow

**Current Implementation** (from `ppl-meta-face-detection.md`):

```text
┌────────────────────────────────────────────────────────────────┐
│ CURRENT: Batch Processing Every 5 Videos                       │
└────────────────────────────────────────────────────────────────┘

Video 1-5 Recorded → Batch 1 Processing → MVR People (Group A)
Video 6-10 Recorded → Batch 2 Processing → MVR People (Group B)
Video 11-15 Recorded → Batch 3 Processing → MVR People (Group C)

PROBLEM: Same person in Video 2 and Video 7
→ Creates 2 separate MVR People (one in Group A, one in Group B)
→ User sees duplicates in Cross-Video Analysis screen
```

**Key Configuration Values** (from `batch_timeout_manager.py`):

```python
# Default batch size (configurable 2-50)
batch_size: int = 5

# Minimum videos for partial batch
min_videos: int = 2

# Batch timeout before triggering partial batch
timeout_minutes: int = 10
```

### Current MVR People Structure

**Database Schema** (from `mvr_repository.py`):

```sql
-- mvr_people table (existing)
CREATE TABLE mvr_people (
    mvr_people_uuid UUID PRIMARY KEY,
    featured_individual_uuid UUID NOT NULL,
    face_embedding BYTEA,
    quality_score FLOAT,
    
    -- Merge tracking (ALREADY EXISTS!)
    is_orphaned BOOLEAN DEFAULT FALSE,
    orphaned_at TIMESTAMP,
    merged_into_mvr_uuid UUID,  -- ✅ Already tracks merge target!
    previous_individual_uuids JSONB,  -- ✅ Already tracks merged individuals!
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- individuals table
CREATE TABLE individuals (
    individual_uuid UUID PRIMARY KEY,
    mvr_people_uuid UUID REFERENCES mvr_people(mvr_people_uuid),
    tracking_session_uuid UUID,
    -- ... other fields
);
```

**Key Finding**: The database **ALREADY SUPPORTS** merge hierarchies via:
- `merged_into_mvr_uuid`: Points to the parent MVR person
- `is_orphaned`: Marks merged/deprecated MVR people
- `previous_individual_uuids`: Tracks which individuals were merged

### Current Merge Endpoint

**Endpoint** (from `mvr_people.py`):

```
POST /api/v1/mvr-people/merge/individuals
```

**Function**: `merge_individuals()` - Merges 2+ individuals into single MVR person

**Current Usage**: Manual merging from Flutter UI when user selects individuals

---

## Proposed Solution

### Overview

Implement a **three-tier hierarchical system** with automatic post-search merging:

```text
┌────────────────────────────────────────────────────────────────┐
│ PROPOSED: Automatic Hierarchical Merging After Search          │
└────────────────────────────────────────────────────────────────┘

1. User searches collection → Get MVR People from all batches
2. Calculate similarity matrix between all MVR People
3. Auto-merge MVR People with similarity > threshold
4. Create "super-individuals" (merged MVR people)
5. Display hierarchical structure in UI
```

### Three-Tier Hierarchy

#### Tier 1: Person Objects (Unchanged)
- Frame-level detections
- Bounding boxes, timestamps
- Raw face embeddings

#### Tier 2: MVR People / Individuals (Enhanced)
- Consolidated person across video(s) within a batch
- May be merged into Tier 3
- Can be in two states:
  - **Active**: Standalone individual
  - **Merged**: Part of a super-individual (marked as orphaned)

#### Tier 3: Super-Individuals (NEW)
- Consolidated person across **multiple batches**
- Created post-search via automatic merging
- References multiple Tier 2 MVR People
- Highest-quality MVR person becomes the "featured" representative

### Data Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│                     PROPOSED FLOW                                │
└─────────────────────────────────────────────────────────────────┘

1. Collections Screen - User Initiates Search
   └─ POST /api/v1/mvr-people/search/by-collection
      ├─ Returns: All MVR People in date range (50-200 results)
      └─ Cached in sessionData['search_results']

2. Backend - Automatic Post-Search Merging (NEW!)
   └─ POST /api/v1/mvr-people/merge/hierarchical
      ├─ Input: search_results[] from step 1
      ├─ Input: similarity_threshold (default: 0.70)
      ├─ Calculate: Pairwise similarity matrix (N×N comparisons)
      ├─ Group: Connected components with similarity > threshold
      ├─ Merge: Within each group, merge MVR people
      │   ├─ Winner: Highest quality_score
      │   ├─ Update: merged_into_mvr_uuid for losers
      │   ├─ Mark: is_orphaned = TRUE for losers
      │   └─ Return: Super-individual UUIDs (winners)
      └─ Return: {
            "super_individuals": [...],  // Winner MVR UUIDs
            "merge_groups": [...],       // Full hierarchy
            "similarity_matrix": {...}   // For visualization
          }

3. Collections Screen - Display Merged Results
   └─ Shows: "X appearances → Y individuals → Z unique people"
      ├─ X = Total person objects
      ├─ Y = Total MVR people (including merged)
      └─ Z = Super-individuals (after merging)

4. Navigate to PersonObjectsDetailScreen
   └─ Pass: super_individual_uuids (not individual MVR UUIDs)
   └─ Pass: merge_hierarchy data structure

5. Individuals Tab - Hierarchical Display (ENHANCED)
   └─ Level 1: Super-Individual Card (expandable)
      ├─ Shows: Aggregate statistics across all merged MVR people
      ├─ Face: Best quality face from all MVR people
      ├─ Demographics: Averaged across merged MVR people
      ├─ Badge: "3 batches merged" indicator
      └─ Expand to show...
         └─ Level 2: MVR Person Cards (sub-items)
            ├─ Shows: Individual MVR person details
            ├─ Badge: "Batch 2" or "Videos 6-10" indicator
            ├─ Similarity: Score relative to super-individual
            └─ Expand to show...
               └─ Level 3: Person Objects (existing)
                  └─ Frame-level detections
```

---

## Database Schema Changes

### Option A: Reuse Existing Schema (RECOMMENDED)

**No schema changes needed!** Leverage existing merge tracking fields:

```sql
-- mvr_people table (NO CHANGES NEEDED)
-- Already has:
--   merged_into_mvr_uuid: Points to super-individual
--   is_orphaned: Marks merged MVR people
--   previous_individual_uuids: Tracks merge history

-- Simply create a new "merge session" concept in application logic
-- to distinguish batch-level merges from cross-batch merges
```

**Advantages**:
- ✅ No migration required
- ✅ Existing merge endpoints work as-is
- ✅ Backward compatible
- ✅ Less risk

**Application-Level Distinction**:

```python
# Add new field to API responses (not database)
{
    "mvr_people_uuid": "...",
    "merge_level": "super_individual",  # or "individual" or "person_object"
    "merged_from_mvr_uuids": [...],     # Calculated from is_orphaned + merged_into
    "batch_source": "batch_2",          # Tracking session info
    "merge_session_uuid": "...",        # Post-search merge session ID
}
```

### Option B: Explicit Super-Individuals Table (FUTURE)

**Only if needed for complex queries or performance**:

```sql
-- NEW TABLE: super_individuals
CREATE TABLE super_individuals (
    super_individual_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    featured_mvr_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid),
    
    -- Aggregate statistics
    total_merged_mvr_count INTEGER DEFAULT 1,
    total_videos INTEGER,
    total_appearances INTEGER,
    
    -- Quality metrics
    average_quality_score FLOAT,
    best_quality_score FLOAT,
    
    -- Demographics (averaged)
    gender VARCHAR(20),
    age_range VARCHAR(20),
    
    -- Merge provenance
    merge_session_uuid UUID,  -- References the search session that created this
    merge_threshold FLOAT,    -- Similarity threshold used
    created_by_search_at TIMESTAMP DEFAULT NOW(),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Link MVR people to super-individuals
-- (Can reuse merged_into_mvr_uuid or add explicit link)
CREATE TABLE super_individual_members (
    super_individual_uuid UUID REFERENCES super_individuals(super_individual_uuid),
    mvr_people_uuid UUID REFERENCES mvr_people(mvr_people_uuid),
    similarity_score FLOAT,  -- Similarity to featured_mvr_uuid
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (super_individual_uuid, mvr_people_uuid)
);

CREATE INDEX idx_super_individual_members_mvr 
    ON super_individual_members(mvr_people_uuid);
```

**Advantages**:
- ✅ Explicit hierarchy
- ✅ Optimized queries for super-individuals
- ✅ Can store pre-computed aggregates

**Disadvantages**:
- ❌ Requires migration
- ❌ More complex to maintain
- ❌ Risk of data inconsistency

**Recommendation**: Start with **Option A**, migrate to **Option B** only if performance issues arise.

---

## Backend Implementation

### Phase 1: Core Merging Logic

#### New Service: `HierarchicalMVRMerger`

**File**: `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py`

```python
"""
Hierarchical MVR Merger Service
Automatically merges MVR People across batches based on similarity threshold.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Set, Tuple
from uuid import UUID
from collections import defaultdict

from database.mvr_repository import MVRRepository
from services.mvr_matcher import MVRMatcher

logger = logging.getLogger(__name__)


class HierarchicalMVRMerger:
    """
    Service for automatically merging MVR People across batch boundaries.
    
    Creates a hierarchical structure:
    - Super-individuals (merged MVR people from different batches)
    - MVR People (individuals from single batches)
    - Person Objects (frame-level detections)
    """
    
    def __init__(self, repository: MVRRepository, matcher: MVRMatcher):
        self.repository = repository
        self.matcher = matcher
    
    async def merge_search_results(
        self,
        mvr_people: List[Dict[str, Any]],
        similarity_threshold: float = 0.70,
        min_quality_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Automatically merge MVR People from search results.
        
        Args:
            mvr_people: List of MVR People from search
            similarity_threshold: Minimum similarity for merging (0.0-1.0)
            min_quality_threshold: Minimum quality score to consider
            
        Returns:
            Dict with:
                - super_individuals: List of winner MVR UUIDs
                - merge_groups: Hierarchical structure
                - merges_performed: Count of merges
                - similarity_matrix: Pairwise similarities (optional)
        """
        logger.info(
            f"🔄 Starting hierarchical merge for {len(mvr_people)} MVR people "
            f"(threshold: {similarity_threshold:.2f})"
        )
        
        # Step 1: Filter out low-quality MVR people
        eligible_mvr = [
            mvr for mvr in mvr_people
            if mvr.get('quality_score', 0) >= min_quality_threshold
        ]
        
        logger.info(f"Eligible MVR people: {len(eligible_mvr)}/{len(mvr_people)}")
        
        if len(eligible_mvr) < 2:
            logger.info("Not enough MVR people to merge")
            return {
                "super_individuals": [mvr['mvr_people_uuid'] for mvr in mvr_people],
                "merge_groups": [],
                "merges_performed": 0
            }
        
        # Step 2: Extract embeddings and build similarity matrix
        embeddings_map = {}
        for mvr in eligible_mvr:
            uuid = mvr['mvr_people_uuid']
            embedding = mvr.get('face_embedding')
            
            if embedding:
                # Convert to numpy array if needed
                if isinstance(embedding, bytes):
                    embedding = np.frombuffer(embedding, dtype=np.float32)
                embeddings_map[uuid] = embedding
        
        logger.info(f"Extracted {len(embeddings_map)} embeddings")
        
        # Step 3: Calculate pairwise similarities
        similarity_matrix = await self._calculate_similarity_matrix(
            embeddings_map
        )
        
        # Step 4: Find merge groups (connected components)
        merge_groups = await self._find_merge_groups(
            similarity_matrix,
            similarity_threshold
        )
        
        logger.info(f"Found {len(merge_groups)} merge groups")
        
        # Step 5: Execute merges within each group
        super_individuals = []
        merges_performed = 0
        
        for group in merge_groups:
            if len(group) < 2:
                # No merge needed
                super_individuals.extend(group)
                continue
            
            # Merge group into single super-individual
            winner_uuid = await self._merge_group(
                group,
                mvr_people,
                similarity_matrix
            )
            
            super_individuals.append(winner_uuid)
            merges_performed += len(group) - 1
        
        logger.info(
            f"✅ Hierarchical merge complete: "
            f"{len(mvr_people)} → {len(super_individuals)} super-individuals "
            f"({merges_performed} merges)"
        )
        
        return {
            "super_individuals": super_individuals,
            "merge_groups": merge_groups,
            "merges_performed": merges_performed,
            "similarity_matrix": similarity_matrix  # Optional, for debugging
        }
    
    async def _calculate_similarity_matrix(
        self,
        embeddings_map: Dict[UUID, np.ndarray]
    ) -> Dict[Tuple[UUID, UUID], float]:
        """
        Calculate pairwise cosine similarities between all embeddings.
        
        Returns:
            Dict mapping (uuid1, uuid2) -> similarity_score
        """
        similarity_matrix = {}
        uuids = list(embeddings_map.keys())
        
        for i, uuid1 in enumerate(uuids):
            for uuid2 in uuids[i+1:]:
                emb1 = embeddings_map[uuid1]
                emb2 = embeddings_map[uuid2]
                
                # Cosine similarity
                similarity = np.dot(emb1, emb2) / (
                    np.linalg.norm(emb1) * np.linalg.norm(emb2)
                )
                
                similarity_matrix[(uuid1, uuid2)] = float(similarity)
                similarity_matrix[(uuid2, uuid1)] = float(similarity)  # Symmetric
        
        return similarity_matrix
    
    async def _find_merge_groups(
        self,
        similarity_matrix: Dict[Tuple[UUID, UUID], float],
        threshold: float
    ) -> List[List[UUID]]:
        """
        Find connected components in similarity graph.
        
        Uses Union-Find algorithm for efficiency.
        
        Returns:
            List of groups (each group is list of MVR UUIDs to merge)
        """
        # Extract unique UUIDs
        all_uuids = set()
        for (uuid1, uuid2), sim in similarity_matrix.items():
            if sim >= threshold:
                all_uuids.add(uuid1)
                all_uuids.add(uuid2)
        
        # Union-Find data structure
        parent = {uuid: uuid for uuid in all_uuids}
        
        def find(uuid):
            if parent[uuid] != uuid:
                parent[uuid] = find(parent[uuid])  # Path compression
            return parent[uuid]
        
        def union(uuid1, uuid2):
            root1 = find(uuid1)
            root2 = find(uuid2)
            if root1 != root2:
                parent[root2] = root1
        
        # Build union-find structure
        for (uuid1, uuid2), sim in similarity_matrix.items():
            if sim >= threshold:
                union(uuid1, uuid2)
        
        # Group by root
        groups_dict = defaultdict(list)
        for uuid in all_uuids:
            root = find(uuid)
            groups_dict[root].append(uuid)
        
        # Convert to list of groups
        groups = list(groups_dict.values())
        
        return groups
    
    async def _merge_group(
        self,
        group: List[UUID],
        mvr_people: List[Dict[str, Any]],
        similarity_matrix: Dict[Tuple[UUID, UUID], float]
    ) -> UUID:
        """
        Merge a group of MVR People into a single super-individual.
        
        Strategy:
        1. Select winner (highest quality_score)
        2. Merge losers into winner using existing merge endpoint
        3. Return winner UUID
        
        Args:
            group: List of MVR UUIDs to merge
            mvr_people: Full list of MVR people for quality lookup
            similarity_matrix: For calculating merge similarity scores
            
        Returns:
            Winner MVR UUID (the super-individual)
        """
        # Find MVR with highest quality in group
        mvr_map = {mvr['mvr_people_uuid']: mvr for mvr in mvr_people}
        
        best_mvr = max(
            group,
            key=lambda uuid: mvr_map[uuid].get('quality_score', 0)
        )
        
        logger.info(f"Merging group of {len(group)} MVR people into {best_mvr}")
        
        # Merge all others into best
        for loser_uuid in group:
            if loser_uuid == best_mvr:
                continue
            
            # Get similarity score
            similarity = similarity_matrix.get((best_mvr, loser_uuid), 0.0)
            
            # Use existing MVRMatcher.merge_mvr_people()
            await self.matcher.merge_mvr_people(
                new_individual_uuid=None,  # Not from new individual
                new_mvr_uuid=loser_uuid,
                existing_mvr_uuid=best_mvr,
                similarity_score=similarity,
                new_quality_score=mvr_map[loser_uuid].get('quality_score', 0),
                existing_quality_score=mvr_map[best_mvr].get('quality_score', 0)
            )
        
        return best_mvr
    
    async def get_merge_hierarchy(
        self,
        super_individual_uuid: UUID
    ) -> Dict[str, Any]:
        """
        Get the full merge hierarchy for a super-individual.
        
        Returns:
            Dict with:
                - super_individual: Featured MVR person
                - merged_mvr_people: List of merged MVR people
                - total_individuals: Count of individuals across all MVR
                - total_person_objects: Count of detections across all
        """
        # Get the super-individual (winner)
        super_individual = await self.repository.get_mvr_person(
            super_individual_uuid
        )
        
        # Find all MVR people merged into this one
        merged_mvr = await self.repository.get_merged_mvr_people(
            target_mvr_uuid=super_individual_uuid
        )
        
        # Get individuals for each MVR person
        all_individuals = []
        total_person_objects = 0
        
        for mvr in [super_individual] + merged_mvr:
            individuals = await self.repository.get_individuals_by_mvr(
                mvr['mvr_people_uuid']
            )
            all_individuals.extend(individuals)
            
            # Count person objects
            for ind in individuals:
                person_objects = await self.repository.get_person_objects_by_individual(
                    ind['individual_uuid']
                )
                total_person_objects += len(person_objects)
        
        return {
            "super_individual": super_individual,
            "merged_mvr_people": merged_mvr,
            "total_mvr_count": len(merged_mvr) + 1,
            "total_individuals": len(all_individuals),
            "total_person_objects": total_person_objects
        }
```

#### Repository Method: Get Merged MVR People

**File**: `ppl-meta-vmeta/src/database/mvr_repository.py`

**Add new method**:

```python
async def get_merged_mvr_people(
    self,
    target_mvr_uuid: UUID
) -> List[Dict[str, Any]]:
    """
    Get all MVR People that were merged into target.
    
    Args:
        target_mvr_uuid: The winner/super-individual UUID
        
    Returns:
        List of orphaned MVR people merged into target
    """
    async with self.pool.acquire() as conn:
        try:
            rows = await conn.fetch("""
                SELECT 
                    mvr_people_uuid,
                    featured_individual_uuid,
                    quality_score,
                    gender,
                    age_range,
                    face_embedding,
                    is_orphaned,
                    orphaned_at,
                    merged_into_mvr_uuid,
                    previous_individual_uuids,
                    created_at,
                    updated_at
                FROM mvr_people
                WHERE merged_into_mvr_uuid = $1
                    AND is_orphaned = TRUE
                ORDER BY quality_score DESC
            """, target_mvr_uuid)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get merged MVR people: {e}")
            return []
```

### Phase 2: API Endpoint

#### New Endpoint: Hierarchical Merge

**File**: `ppl-meta-vmeta/src/api/routes/mvr_people.py`

```python
@router.post(
    "/merge/hierarchical",
    summary="Automatically merge MVR People across batches",
    description=(
        "Post-search merging: Consolidates MVR People from different batches "
        "that represent the same person. Uses similarity threshold to create "
        "super-individuals."
    ),
    response_model=Dict[str, Any]
)
async def merge_hierarchical(
    request: HierarchicalMergeRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    mvr_repository: MVRRepository = Depends(get_mvr_repository)
):
    """
    Automatically merge MVR People from search results.
    
    Request Body:
        - mvr_people_uuids: List of MVR UUIDs from search
        - similarity_threshold: Minimum similarity for merging (default: 0.70)
        - min_quality_threshold: Minimum quality score (default: 0.5)
        
    Returns:
        - super_individuals: List of winner MVR UUIDs
        - merge_groups: Hierarchical structure
        - merges_performed: Count of merges
        - statistics: Summary statistics
    """
    try:
        logger.info(
            f"Hierarchical merge requested for {len(request.mvr_people_uuids)} MVR people"
        )
        
        # Fetch full MVR person data
        mvr_people = []
        for uuid in request.mvr_people_uuids:
            mvr = await mvr_repository.get_mvr_person(uuid)
            if mvr:
                mvr_people.append(mvr)
        
        # Create merger service
        merger = HierarchicalMVRMerger(mvr_repository, mvr_matcher)
        
        # Execute merge
        result = await merger.merge_search_results(
            mvr_people,
            similarity_threshold=request.similarity_threshold,
            min_quality_threshold=request.min_quality_threshold
        )
        
        # Calculate statistics
        statistics = {
            "input_mvr_count": len(mvr_people),
            "output_super_individual_count": len(result['super_individuals']),
            "reduction_percentage": (
                (len(mvr_people) - len(result['super_individuals'])) / 
                len(mvr_people) * 100
                if len(mvr_people) > 0 else 0
            ),
            "merges_performed": result['merges_performed'],
            "largest_merge_group": (
                max(len(g) for g in result['merge_groups'])
                if result['merge_groups'] else 1
            )
        }
        
        logger.info(
            f"✅ Hierarchical merge complete: "
            f"{statistics['input_mvr_count']} → "
            f"{statistics['output_super_individual_count']} "
            f"({statistics['reduction_percentage']:.1f}% reduction)"
        )
        
        return {
            "success": True,
            "super_individuals": result['super_individuals'],
            "merge_groups": result['merge_groups'],
            "statistics": statistics
        }
        
    except Exception as e:
        logger.error(f"Hierarchical merge failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Hierarchical merge failed: {str(e)}"
        )


# Request model
class HierarchicalMergeRequest(BaseModel):
    mvr_people_uuids: List[UUID]
    similarity_threshold: float = 0.70
    min_quality_threshold: float = 0.5
```

#### Enhanced Endpoint: Get Super-Individual Details

```python
@router.get(
    "/super-individual/{super_individual_uuid}/hierarchy",
    summary="Get merge hierarchy for super-individual",
    description="Returns the full 3-tier hierarchy for a merged super-individual"
)
async def get_super_individual_hierarchy(
    super_individual_uuid: UUID,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher)
):
    """
    Get complete hierarchy for a super-individual.
    
    Returns:
        - super_individual: Featured MVR person (winner)
        - merged_mvr_people: MVR people merged into this super-individual
        - all_individuals: All individuals across all MVR people
        - statistics: Aggregate statistics
    """
    try:
        merger = HierarchicalMVRMerger(mvr_repository, mvr_matcher)
        
        hierarchy = await merger.get_merge_hierarchy(super_individual_uuid)
        
        return {
            "success": True,
            **hierarchy
        }
        
    except Exception as e:
        logger.error(f"Failed to get hierarchy: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get hierarchy: {str(e)}"
        )
```

---

## Frontend Implementation

### Phase 1: Integrate Post-Search Merging

#### Update Collections Screen

**File**: `ppl-meta-frontend/lib/screens/collections_screen.dart`

**Modify** `_fetchIndividualsCount()` method:

```dart
Future<void> _fetchIndividualsCount() async {
  setState(() {
    _isLoadingIndividuals = true;
    _individualsError = null;
  });

  try {
    // Step 1: Get videos from collection (existing)
    final videoResponse = await _mediaApiClient.getMediaByCollection(
      collectionId: selectedCollectionId!,
      startDate: _selectedStartDate,
      endDate: _selectedEndDate,
      mediaType: 'video',
      limit: 1000,
    );

    if (!videoResponse.success || videoResponse.data == null) {
      throw Exception('Failed to fetch videos');
    }

    final videos = videoResponse.data as List<dynamic>;
    final videoUuids = videos
        .map((v) => v['uuid'] as String)
        .toList();

    if (videoUuids.isEmpty) {
      setState(() {
        _trackingSessionData = {'message': 'No videos found'};
        _isLoadingIndividuals = false;
      });
      return;
    }

    // Step 2: Search MVR people in videos (existing)
    final searchResponse = await _mediaApiClient.searchMVRPeopleByVideos(
      videoUuids: videoUuids,
      limit: 500,
    );

    if (!searchResponse.success || searchResponse.data == null) {
      throw Exception('Failed to search MVR people');
    }

    final searchResults = searchResponse.data['search_results'] as List<dynamic>;
    
    // ✨ NEW: Step 3: Automatically merge similar MVR people
    final mergeResponse = await _mediaApiClient.mergeHierarchical(
      mvrPeopleUuids: searchResults
          .map((mvr) => mvr['mvr_people_uuid'] as String)
          .toList(),
      similarityThreshold: 0.70,  // User-configurable in future
      minQualityThreshold: 0.5,
    );

    if (!mergeResponse.success || mergeResponse.data == null) {
      // Fallback: Use unmerged results if merge fails
      logger.warning('Hierarchical merge failed, using unmerged results');
      setState(() {
        _trackingSessionData = {
          'search_results': searchResults,
          'collection_id': selectedCollectionId,
          'merge_failed': true,
        };
      });
    } else {
      // Success: Use merged super-individuals
      final mergeData = mergeResponse.data as Map<String, dynamic>;
      final superIndividuals = mergeData['super_individuals'] as List<dynamic>;
      final statistics = mergeData['statistics'] as Map<String, dynamic>;
      
      setState(() {
        _trackingSessionData = {
          'search_results': searchResults,  // Keep original for reference
          'super_individuals': superIndividuals,  // Merged results
          'merge_groups': mergeData['merge_groups'],
          'merge_statistics': statistics,
          'collection_id': selectedCollectionId,
          'merged': true,
        };
        
        // Update display text
        _individualsCountText = 
            '${searchResults.length} appearances → '
            '${superIndividuals.length} unique people '
            '(${statistics['reduction_percentage'].toStringAsFixed(0)}% reduction)';
      });
      
      logger.info(
        'Hierarchical merge complete: '
        '${searchResults.length} → ${superIndividuals.length}'
      );
    }

    setState(() {
      _isLoadingIndividuals = false;
    });

  } catch (e) {
    setState(() {
      _individualsError = e.toString();
      _isLoadingIndividuals = false;
    });
  }
}
```

### Phase 2: Hierarchical Display in Individuals Tab

#### Update PersonObjectsDetailScreen

**File**: `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

**Modify** `_loadCrossVideoData()` method:

```dart
Future<void> _loadCrossVideoData() async {
  if (widget.crossVideoContext == null) return;

  setState(() {
    _isLoadingCrossVideoData = true;
    _crossVideoError = null;
  });

  try {
    final context = widget.crossVideoContext!;
    final sessionData = context.sessionData;
    
    // Check if we have merged super-individuals
    final bool hasMergedData = sessionData['merged'] == true;
    final List<String> uuidsToLoad = hasMergedData
        ? (sessionData['super_individuals'] as List<dynamic>)
            .map((uuid) => uuid.toString())
            .toList()
        : context.individualUuids;
    
    logger.info(
      'Loading ${uuidsToLoad.length} ${hasMergedData ? "super-individuals" : "individuals"}'
    );

    List<AggregatedIndividualAnalysis> analyses = [];

    for (String uuid in uuidsToLoad) {
      if (hasMergedData) {
        // Load super-individual with full hierarchy
        final response = await _mediaApiClient.getSuperIndividualHierarchy(
          superIndividualUuid: uuid,
        );

        if (response.success && response.data != null) {
          // Convert to hierarchical analysis
          final hierarchyData = response.data as Map<String, dynamic>;
          final analysis = AggregatedIndividualAnalysis.fromSuperIndividual(
            hierarchyData,
          );
          analyses.add(analysis);
        }
      } else {
        // Load regular MVR person (backward compatible)
        final response = await _mediaApiClient.getMVRPersonAnalysis(
          mvrPersonUuid: uuid,
          startTime: context.startTime,
          endTime: context.endTime,
        );

        if (response.success && response.data != null) {
          final analysis = AggregatedIndividualAnalysis.fromJson(
            response.data as Map<String, dynamic>,
          );
          analyses.add(analysis);
        }
      }
    }

    setState(() {
      _aggregatedAnalyses = analyses;
      _isLoadingCrossVideoData = false;
    });

  } catch (e) {
    setState(() {
      _crossVideoError = e.toString();
      _isLoadingCrossVideoData = false;
    });
  }
}
```

**Update** Individuals Tab rendering:

```dart
Widget _buildIndividualsTab() {
  if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
    return Center(child: Text('No individuals found'));
  }

  return ListView.builder(
    padding: EdgeInsets.all(16),
    itemCount: _aggregatedAnalyses!.length,
    itemBuilder: (context, index) {
      final analysis = _aggregatedAnalyses![index];
      final isSuperIndividual = analysis.isSuperIndividual;
      
      return _buildHierarchicalIndividualCard(analysis, isSuperIndividual);
    },
  );
}

Widget _buildHierarchicalIndividualCard(
  AggregatedIndividualAnalysis analysis,
  bool isSuperIndividual,
) {
  final isExpanded = _expandedIndividuals.contains(analysis.individualUuid);
  
  return Card(
    margin: EdgeInsets.only(bottom: 16),
    elevation: 4, // Same elevation for all Level 1 individuals
    child: Column(
      children: [
        // ✨ Level 1: Super-Individual Header (Merged or Standalone)
        ListTile(
          leading: Stack(
            children: [
              // Best quality face thumbnail
              CircleAvatar(
                radius: 30,
                backgroundImage: NetworkImage(analysis.bestFaceThumbnail),
              ),
              // Always show badge: Blue for merged, Grey for standalone
              Positioned(
                bottom: 0,
                right: 0,
                child: Container(
                  padding: EdgeInsets.all(2),
                  decoration: BoxDecoration(
                    color: isSuperIndividual ? Colors.blue : Colors.grey[600],
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    isSuperIndividual ? Icons.merge_type : Icons.person,
                    size: 16,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          title: Row(
            children: [
              Text(
                analysis.demographics?.gender ?? 'Unknown',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                ),
              ),
              SizedBox(width: 8),
              Chip(
                label: Text(
                  isSuperIndividual 
                    ? '${analysis.mergedMVRCount} batches merged'
                    : 'Standalone individual',
                  style: TextStyle(fontSize: 12),
                ),
                backgroundColor: isSuperIndividual 
                  ? Colors.blue.withOpacity(0.2)
                  : Colors.grey.withOpacity(0.2),
                padding: EdgeInsets.symmetric(horizontal: 4),
                ),
            ],
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Age: ${analysis.demographics?.ageRange ?? "Unknown"}'),
              SizedBox(height: 4),
              Text(
                '${analysis.totalAppearances} appearances across '
                '${analysis.uniqueVideos} videos',
                style: TextStyle(fontSize: 12),
              ),
              if (isSuperIndividual)
                Text(
                  '${analysis.totalIndividuals} individuals merged',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.blue,
                  ),
                ),
            ],
          ),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Selection checkbox
              Checkbox(
                value: _selectedIndividuals.contains(analysis.individualUuid),
                onChanged: (_) => _toggleIndividualSelection(
                  analysis.individualUuid
                ),
              ),
              // Expand/collapse button
              IconButton(
                icon: Icon(
                  isExpanded ? Icons.expand_less : Icons.expand_more,
                ),
                onPressed: () {
                  setState(() {
                    if (isExpanded) {
                      _expandedIndividuals.remove(analysis.individualUuid);
                    } else {
                      _expandedIndividuals.add(analysis.individualUuid);
                    }
                  });
                },
              ),
            ],
          ),
        ),
        
        // ✨ Level 2: Merged MVR People (if super-individual and expanded)
        if (isSuperIndividual && isExpanded)
          _buildMergedMVRPeopleList(analysis),
        
        // ✨ Level 3: Person Objects (always available when expanded)
        if (isExpanded)
          _buildPersonObjectsList(analysis),
      ],
    ),
  );
}

Widget _buildMergedMVRPeopleList(AggregatedIndividualAnalysis analysis) {
  return Container(
    margin: EdgeInsets.only(left: 32, right: 16, top: 8),
    padding: EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.blue.withOpacity(0.05),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: Colors.blue.withOpacity(0.2)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.account_tree, size: 20, color: Colors.blue),
            SizedBox(width: 8),
            Text(
              'Merged MVR People',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.blue,
              ),
            ),
          ],
        ),
        SizedBox(height: 12),
        ...analysis.mergedMVRPeople.map((mvrPerson) {
          return _buildMVRPersonCard(mvrPerson, analysis);
        }).toList(),
      ],
    ),
  );
}

Widget _buildMVRPersonCard(
  Map<String, dynamic> mvrPerson,
  AggregatedIndividualAnalysis parentAnalysis,
) {
  final isExpanded = _expandedIndividuals.contains(
    mvrPerson['mvr_people_uuid']
  );
  
  return Card(
    margin: EdgeInsets.only(bottom: 8),
    elevation: 1,
    child: Column(
      children: [
        ListTile(
          dense: true,
          leading: CircleAvatar(
            radius: 20,
            backgroundImage: NetworkImage(mvrPerson['face_thumbnail']),
          ),
          title: Text(
            'Batch ${mvrPerson['batch_number'] ?? "?"}',
            style: TextStyle(fontSize: 14),
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Quality: ${(mvrPerson['quality_score'] * 100).toStringAsFixed(0)}%',
                style: TextStyle(fontSize: 12),
              ),
              Text(
                'Similarity: ${(mvrPerson['similarity_to_featured'] * 100).toStringAsFixed(0)}%',
                style: TextStyle(fontSize: 12, color: Colors.blue),
              ),
              Text(
                '${mvrPerson['individual_count']} individuals',
                style: TextStyle(fontSize: 12),
              ),
            ],
          ),
          trailing: IconButton(
            icon: Icon(
              isExpanded ? Icons.expand_less : Icons.expand_more,
              size: 20,
            ),
            onPressed: () {
              setState(() {
                if (isExpanded) {
                  _expandedIndividuals.remove(mvrPerson['mvr_people_uuid']);
                } else {
                  _expandedIndividuals.add(mvrPerson['mvr_people_uuid']);
                }
              });
            },
          ),
        ),
        
        // Show individuals for this MVR person when expanded
        if (isExpanded)
          Container(
            margin: EdgeInsets.only(left: 48, right: 16, bottom: 8),
            child: _buildIndividualsForMVRPerson(mvrPerson),
          ),
      ],
    ),
  );
}

Widget _buildIndividualsForMVRPerson(Map<String, dynamic> mvrPerson) {
  final individuals = mvrPerson['individuals'] as List<dynamic>? ?? [];
  
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Individuals in this MVR person:',
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Colors.grey[600],
        ),
      ),
      SizedBox(height: 8),
      ...individuals.map((individual) {
        return ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.person_outline, size: 16),
          title: Text(
            'Video: ${individual['video_name']}',
            style: TextStyle(fontSize: 12),
          ),
          subtitle: Text(
            '${individual['person_object_count']} detections',
            style: TextStyle(fontSize: 11),
          ),
        );
      }).toList(),
    ],
  );
}
```

### Phase 3: Update Data Models

**File**: `ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`

**Enhance** `AggregatedIndividualAnalysis`:

```dart
class AggregatedIndividualAnalysis {
  final String individualUuid;
  final String? mvrPeopleUuid;
  final Demographics? demographics;
  final List<IndividualAppearance> appearances;
  final int totalAppearances;
  final int uniqueVideos;
  final double averageConfidence;
  final double? averageVelocity;
  final DateTime? firstSeen;
  final DateTime? lastSeen;
  final String? bestFaceThumbnail;
  final DateTime analysisTimestamp;
  
  // ✨ NEW: Hierarchical merge fields
  final bool isSuperIndividual;  // Is this a merged super-individual?
  final int mergedMVRCount;  // How many MVR people were merged
  final List<Map<String, dynamic>> mergedMVRPeople;  // Details of merged MVR
  final int totalIndividuals;  // Total individuals across all MVR people
  final Map<String, dynamic>? mergeStatistics;  // Merge stats
  
  AggregatedIndividualAnalysis({
    required this.individualUuid,
    this.mvrPeopleUuid,
    this.demographics,
    required this.appearances,
    required this.totalAppearances,
    required this.uniqueVideos,
    required this.averageConfidence,
    this.averageVelocity,
    this.firstSeen,
    this.lastSeen,
    this.bestFaceThumbnail,
    required this.analysisTimestamp,
    // Hierarchical fields
    this.isSuperIndividual = false,
    this.mergedMVRCount = 1,
    this.mergedMVRPeople = const [],
    this.totalIndividuals = 0,
    this.mergeStatistics,
  });
  
  // ✨ NEW: Factory for super-individual hierarchy data
  factory AggregatedIndividualAnalysis.fromSuperIndividual(
    Map<String, dynamic> hierarchyData,
  ) {
    final superIndividual = hierarchyData['super_individual'] as Map<String, dynamic>;
    final mergedMVR = hierarchyData['merged_mvr_people'] as List<dynamic>;
    final statistics = hierarchyData['statistics'] as Map<String, dynamic>? ?? {};
    
    // Convert appearances from all MVR people
    List<IndividualAppearance> allAppearances = [];
    
    // Featured MVR appearances
    if (superIndividual['appearances'] != null) {
      allAppearances.addAll(
        (superIndividual['appearances'] as List<dynamic>)
            .map((a) => IndividualAppearance.fromJson(a))
            .toList()
      );
    }
    
    // Merged MVR appearances
    for (var mvr in mergedMVR) {
      if (mvr['appearances'] != null) {
        allAppearances.addAll(
          (mvr['appearances'] as List<dynamic>)
              .map((a) => IndividualAppearance.fromJson(a))
              .toList()
        );
      }
    }
    
    return AggregatedIndividualAnalysis(
      individualUuid: superIndividual['mvr_people_uuid'] as String,
      mvrPeopleUuid: superIndividual['mvr_people_uuid'] as String,
      demographics: Demographics.fromJson(superIndividual['demographics']),
      appearances: allAppearances,
      totalAppearances: statistics['total_appearances'] ?? allAppearances.length,
      uniqueVideos: statistics['unique_videos'] ?? 0,
      averageConfidence: (superIndividual['quality_score'] ?? 0.0).toDouble(),
      averageVelocity: statistics['average_velocity']?.toDouble(),
      firstSeen: DateTime.tryParse(superIndividual['created_at'] ?? ''),
      lastSeen: DateTime.tryParse(superIndividual['updated_at'] ?? ''),
      bestFaceThumbnail: superIndividual['face_thumbnail'],
      analysisTimestamp: DateTime.now(),
      // Hierarchical fields
      isSuperIndividual: true,
      mergedMVRCount: mergedMVR.length + 1,
      mergedMVRPeople: mergedMVR.cast<Map<String, dynamic>>(),
      totalIndividuals: hierarchyData['total_individuals'] ?? 0,
      mergeStatistics: statistics,
    );
  }
  
  // Existing fromJson for backward compatibility
  factory AggregatedIndividualAnalysis.fromJson(Map<String, dynamic> json) {
    // ... existing implementation
  }
}
```

---

## API Changes

### New Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/mvr-people/merge/hierarchical` | Auto-merge MVR people from search results |
| GET | `/api/v1/mvr-people/super-individual/{uuid}/hierarchy` | Get full 3-tier hierarchy for super-individual |

### Enhanced Endpoints

| Method | Endpoint | Changes |
|--------|----------|---------|
| GET | `/api/v1/mvr-people/mvr-person/{uuid}/analysis` | Add `merge_level` field to response |
| POST | `/api/v1/mvr-people/search/by-collection` | Optionally trigger auto-merge |

---

## Migration Strategy

### Phase 1: Database (No Changes Needed!)

**Action**: None - Reuse existing schema

**Validation**:
```sql
-- Verify merge tracking fields exist
SELECT 
    merged_into_mvr_uuid,
    is_orphaned,
    orphaned_at,
    previous_individual_uuids
FROM mvr_people
WHERE is_orphaned = TRUE
LIMIT 5;
```

### Phase 2: Backend Deployment

1. **Deploy new service** (`HierarchicalMVRMerger`)
2. **Deploy new endpoint** (`/merge/hierarchical`)
3. **Test with existing data** (no breaking changes)

### Phase 3: Frontend Deployment

1. **Deploy enhanced Collections screen** with auto-merge
2. **Deploy hierarchical Individuals tab** with 3-tier display
3. **Add user preference** for similarity threshold

### Rollback Plan

- Frontend gracefully handles missing merge data
- Backend endpoints are additive (no breaking changes)
- Can disable auto-merge via feature flag

---

## Testing Strategy

### Unit Tests

#### Backend: `test_hierarchical_mvr_merger.py`

```python
import pytest
from services.hierarchical_mvr_merger import HierarchicalMVRMerger

@pytest.mark.asyncio
async def test_similarity_matrix_calculation():
    """Test pairwise similarity calculation."""
    # Create mock embeddings
    # Calculate similarities
    # Assert symmetric matrix

@pytest.mark.asyncio
async def test_find_merge_groups_single_group():
    """Test connected components with one merge group."""
    # Mock similarity matrix with clear cluster
    # Assert single group found

@pytest.mark.asyncio
async def test_find_merge_groups_multiple_groups():
    """Test connected components with multiple clusters."""
    # Mock similarity matrix with 3 distinct clusters
    # Assert 3 groups found

@pytest.mark.asyncio
async def test_merge_group_selects_highest_quality():
    """Test that winner has highest quality score."""
    # Mock MVR people with varying quality
    # Execute merge
    # Assert highest quality is winner

@pytest.mark.asyncio
async def test_hierarchical_merge_end_to_end():
    """Test full merge flow."""
    # Create 10 MVR people (3 clusters)
    # Execute hierarchical merge
    # Assert 3 super-individuals created
    # Verify losers marked as orphaned
```

### Integration Tests

#### Frontend: Manual Test Script

```markdown
## Manual Test: Hierarchical MVR People Merging

### Setup
1. Record 15 videos with same person (5 videos per batch)
2. Batches will create 3 MVR people for same person
3. Perform search on collection

### Test Steps

**Test 1: Auto-Merge Triggers**
- [ ] Collections screen search completes
- [ ] Console shows: "Hierarchical merge requested for X MVR people"
- [ ] Console shows: "X → Y super-individuals (Z% reduction)"
- [ ] UI displays: "X appearances → Y unique people"

**Test 2: Hierarchical Display - Collapsed**
- [ ] Navigate to Analysis screen
- [ ] Individuals tab shows super-individual cards
- [ ] Card shows: "3 batches merged" badge
- [ ] Card shows: Aggregate statistics (15 videos total)
- [ ] Card shows: Best quality face thumbnail

**Test 3: Hierarchical Display - Expanded Level 2**
- [ ] Click expand on super-individual
- [ ] Shows 3 MVR person cards
- [ ] Each MVR card shows: "Batch X" label
- [ ] Each MVR card shows: Similarity score to featured
- [ ] Each MVR card shows: Individual count

**Test 4: Hierarchical Display - Expanded Level 3**
- [ ] Click expand on MVR person card
- [ ] Shows individuals for that MVR person
- [ ] Shows: Video names
- [ ] Shows: Person object counts per individual

**Test 5: Statistics Tab**
- [ ] Navigate to Statistics tab
- [ ] Shows: Total appearances across all merged MVR
- [ ] Shows: Unique videos (should be ~15)
- [ ] Shows: Average velocity across all person objects

**Test 6: Routes Tab**
- [ ] Navigate to Routes tab
- [ ] Shows: Combined routes from all videos
- [ ] Color-coded: Different MVR batches
- [ ] Legend: Shows which color = which batch

**Test 7: Selection and Actions**
- [ ] Select super-individual checkbox
- [ ] Actions button appears
- [ ] Can add to group
- [ ] Can merge with another super-individual
```

### Performance Tests

```python
@pytest.mark.asyncio
async def test_large_scale_merge_performance():
    """Test hierarchical merge with 500 MVR people."""
    # Create 500 MVR people (10 clusters, 50 each)
    # Measure merge time
    # Assert < 30 seconds
    # Assert memory usage < 500MB

@pytest.mark.asyncio
async def test_similarity_matrix_memory():
    """Test memory efficiency of similarity matrix."""
    # N×N matrix for N=500 → 250K entries
    # Measure memory footprint
    # Assert sparse matrix optimization works
```

---

## Performance Considerations

### Similarity Matrix Complexity

**Problem**: O(N²) comparisons for N MVR people

**Example**: 500 MVR people = 250,000 comparisons

**Solutions**:

1. **Batch Processing**: Process in chunks of 100
2. **Early Termination**: Stop if similarity < 0.5 (likely different person)
3. **Caching**: Store similarity matrix for reuse
4. **Approximate Nearest Neighbors**: Use Annoy/FAISS for large-scale

### Database Query Optimization

**Problem**: Fetching full hierarchy (3 levels) requires multiple queries

**Solution**: Use recursive CTEs

```sql
-- Single query to get full hierarchy
WITH RECURSIVE hierarchy AS (
    -- Base: Super-individual (winner)
    SELECT 
        mvr_people_uuid,
        merged_into_mvr_uuid,
        0 AS level,
        ARRAY[mvr_people_uuid] AS path
    FROM mvr_people
    WHERE mvr_people_uuid = $1
        AND is_orphaned = FALSE
    
    UNION ALL
    
    -- Recursive: Merged MVR people
    SELECT 
        m.mvr_people_uuid,
        m.merged_into_mvr_uuid,
        h.level + 1,
        h.path || m.mvr_people_uuid
    FROM mvr_people m
    INNER JOIN hierarchy h 
        ON m.merged_into_mvr_uuid = h.mvr_people_uuid
    WHERE m.is_orphaned = TRUE
)
SELECT * FROM hierarchy;
```

### Frontend Rendering

**Problem**: Large merge groups (100+ merged MVR) slow down UI

**Solutions**:

1. **Virtualized Lists**: Use `flutter_list_view` for large lists
2. **Lazy Loading**: Load Level 2/3 on demand
3. **Pagination**: Show first 20 merged MVR, paginate rest

---

## Timeline & Milestones

### Phase 1: Backend Core (Week 1)

- [ ] Day 1-2: Implement `HierarchicalMVRMerger` service
- [ ] Day 3: Add similarity matrix calculation
- [ ] Day 4: Add merge group finding (Union-Find)
- [ ] Day 5: Add merge execution logic
- [ ] Day 6-7: Unit tests and integration tests

### Phase 2: Backend API (Week 2)

- [ ] Day 1-2: Implement `/merge/hierarchical` endpoint
- [ ] Day 3: Implement `/super-individual/{uuid}/hierarchy` endpoint
- [ ] Day 4: Add repository method `get_merged_mvr_people()`
- [ ] Day 5-7: API tests and documentation

### Phase 3: Frontend Integration (Week 3)

- [ ] Day 1-2: Update Collections screen with auto-merge
- [ ] Day 3-4: Enhance data models for hierarchy
- [ ] Day 5-7: Update media API client methods

### Phase 4: Frontend UI (Week 4)

- [ ] Day 1-3: Implement 3-tier hierarchical cards
- [ ] Day 4: Add expand/collapse animations
- [ ] Day 5: Update Statistics and Routes tabs
- [ ] Day 6-7: Manual testing and bug fixes

### Phase 5: Polish & Deploy (Week 5)

- [ ] Day 1-2: Performance optimization
- [ ] Day 3: User preference for similarity threshold
- [ ] Day 4: Documentation and training materials
- [ ] Day 5: Staging deployment
- [ ] Day 6-7: Production deployment and monitoring

---

## Risks & Mitigation

### Risk 1: Performance with Large Result Sets

**Impact**: High (500+ MVR people = 250K comparisons)

**Mitigation**:
- Implement batch processing (100 at a time)
- Add timeout with partial results
- Use approximate methods for very large sets

### Risk 2: Over-Merging (False Positives)

**Impact**: Medium (merges different people)

**Mitigation**:
- Conservative default threshold (0.70)
- User-adjustable threshold
- Ability to un-merge from UI

### Risk 3: Under-Merging (False Negatives)

**Impact**: Low (still shows duplicates)

**Mitigation**:
- Allow manual merge from UI (existing feature)
- Lower threshold option for specific searches

### Risk 4: Complex UI Confuses Users

**Impact**: Medium (users don't understand hierarchy)

**Mitigation**:
- Clear visual indicators (badges, indentation)
- Tooltips explaining each level
- User guide and training video

---

## Future Enhancements

### Phase 6: Advanced Features (Post-Launch)

1. **Persistent Super-Individuals**: Store in dedicated table (Option B schema)
2. **Cross-Collection Merging**: Merge MVR people across different camera collections
3. **Temporal Clustering**: Auto-merge based on time proximity (same person over days)
4. **Visual Merge Preview**: Show side-by-side faces before merging
5. **Merge Confidence Scores**: ML model to predict merge success
6. **Bulk Un-Merge**: Undo entire merge session
7. **Export Hierarchy**: Export merge tree as JSON/CSV for analysis

---

## Conclusion

This proposal provides a comprehensive solution for hierarchical MVR people merging with:

✅ **Minimal database changes** (reuse existing schema)  
✅ **Backward compatibility** (existing 2-level hierarchy still works)  
✅ **Clear implementation path** (5-week timeline)  
✅ **Performance considerations** (optimized for 500+ MVR people)  
✅ **User-friendly UI** (3-tier expandable hierarchy)

The hierarchical approach solves the duplicate problem while maintaining full audit trail and merge provenance.

---

**Approval Required**: Please review and approve to proceed with implementation.

**Questions**: Contact PPL Meta Development Team

**Last Updated**: December 15, 2025

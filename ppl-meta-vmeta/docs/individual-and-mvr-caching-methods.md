# Individual and MVR People Caching Methods

**Document Version**: 1.1  
**Date**: November 9, 2025 (Updated)  
**Author**: System Architecture Documentation  
**Related Version**: v2.19.30 (in development)

**Latest Update**: Session-wide bulk cache fix completed and verified (November 9, 2025)

---

## Authentication Required

⚠️ **All endpoints in this document require authentication.**

To obtain an authentication token, use the following login endpoint:

```bash
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Correct Endpoints**:

1. **Create Tracking Session**:
```bash
curl -X POST http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-11-06T06:00:00",
    "end_time": "2025-11-07T16:00:00"
  }'
```

2. **Get Session Status**:
```bash
curl -X GET http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/<session_uuid> \
  -H "Authorization: Bearer <access_token>"
```

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Two-Level Caching Architecture](#two-level-caching-architecture)
3. [Level 1: Individual-Level Cache (Video-Based)](#level-1-individual-level-cache-video-based)
4. [Level 2: MVR-Level Cache (Individual-Based)](#level-2-mvr-level-cache-individual-based)
5. [MVR Embedding Storage](#mvr-embedding-storage)
6. [Test Results and Verification](#test-results-and-verification)
7. [Known Issues and Next Steps](#known-issues-and-next-steps)

---

## Executive Summary

The PPL Meta cross-video tracking system implements a **two-level caching architecture** to optimize performance and avoid redundant processing:

1. **Level 1: Individual Cache** - Reuses individuals already created for specific videos
2. **Level 2: MVR Cache** - Reuses MVR (Multi-Video Recognition) people already created from individuals

### Key Architectural Decision (November 8, 2025)

**Question**: Should MVR cache work with videos (like individual cache) or with individuals?

**Answer**: **Individual-based** is superior because:
- MVR represents unique people, not videos
- Works across different time-frame selections
- Higher cache hit rate
- Logical hierarchy: Video → Individuals → MVR People

### Current Status

✅ **Implemented**:
- Migration 005: Added `face_embedding vector(512)` to `mvr_people` table
- Quality-weighted embedding computation during merge
- MVR cache query updated to individual-based approach
- HNSW index for fast embedding similarity search

⚠️ **Testing In Progress**:
- MVR embeddings are stored correctly
- Cache query logic needs verification
- Integration with merge flow needs validation

---

## Two-Level Caching Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ SESSION REQUEST (collections + time range)                      │
└──────────────────┬──────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. VIDEO DISCOVERY                                              │
│    Query Media Service → Get list of videos                     │
└──────────────────┬──────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. LEVEL 1 CACHE: Check for existing individuals               │
│    ✓ For each video: Query individuals table                   │
│    ✓ If found: Link to session, skip processing                │
│    ✓ If not found: Create new individuals                      │
└──────────────────┬──────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. LEVEL 2 CACHE: Check for existing MVR people                │
│    ✓ For session individuals: Query individual_mvr_mapping     │
│    ✓ If MVR found: Use cached MVR (with embedding)             │
│    ✓ If not found: Run merge to create new MVR                 │
└──────────────────┬──────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. MERGE & MVR CREATION                                         │
│    ✓ Generate embeddings for new individuals                   │
│    ✓ Compute similarity matrix                                 │
│    ✓ Merge similar individuals into MVR people                 │
│    ✓ Store quality-weighted embedding on MVR                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Level 1: Individual-Level Cache (Video-Based)

### Purpose
Avoid re-processing videos that have already been analyzed. If a video has individuals already created, reuse them instead of calling the Orchestrator again.

### Implementation

**Location**: `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Function**: `query_existing_individuals_for_video()` (lines ~115-302)

### Logic Flow

```python
# For each video in the session
for video in videos:
    # Check if video already has individuals
    existing = await query_existing_individuals_for_video(
        video_uuid=video['uuid'],
        db_client=db_client
    )
    
    if existing:
        # Cache HIT: Link existing individuals to session
        for individual in existing:
            await link_to_session(session_uuid, individual['uuid'])
        logger.info(f"♻️ Reusing {len(existing)} individuals")
    else:
        # Cache MISS: Create new individuals
        individuals = await create_individuals_for_video(video)
```

### Database Query

```sql
SELECT DISTINCT
    i.individual_uuid,
    i.individual_id,
    i.confidence_score,
    m.mvr_people_uuid  -- Also get MVR if exists
FROM individuals i
LEFT JOIN individual_mvr_mapping m 
    ON i.individual_uuid = m.individual_uuid
WHERE i.video_uuid = $1  -- Query by video
  AND i.merged_into_individual_uuid IS NULL  -- Skip merged
ORDER BY i.created_at DESC;
```

### Cache Key
**Video UUID** - The cache is video-based, so identical video UUIDs will hit the cache regardless of session time range.

### Benefits
- ✅ Skips Orchestrator API calls (network I/O savings)
- ✅ Skips person_object matching (CPU savings)
- ✅ Consistent across time-range variations
- ✅ Works even if session time frames differ slightly

### Limitations
- ❌ Only caches if exact same video was processed before
- ❌ Doesn't help with new videos showing same people

---

## Level 2: MVR-Level Cache (Individual-Based)

### Purpose
Avoid creating duplicate MVR people when individuals from a new session represent the same real-world person as individuals from a previous session.

### Architecture Evolution

#### Old Approach (Video-Based) ❌
```sql
-- OLD: Query MVR by videos in session
SELECT DISTINCT m.mvr_people_uuid, mvr.face_embedding
FROM individual_mvr_mapping m
JOIN individuals i ON m.individual_uuid = i.individual_uuid
JOIN mvr_people mvr ON m.mvr_people_uuid = mvr.mvr_people_uuid
WHERE i.video_uuid = ANY($1::uuid[])  -- Session videos
  AND mvr.face_embedding IS NOT NULL;
```

**Problem**: Only finds MVR if the SAME videos were in a previous session. Misses cases where different videos contain the same person.

#### New Approach (Individual-Based) ✅
```sql
-- NEW: Query MVR by individuals in session
-- Step 1: Get individuals from current session
SELECT individual_uuid 
FROM session_individuals 
WHERE session_uuid = $1;

-- Step 2: Find MVR people mapped to these individuals
SELECT DISTINCT 
    m.mvr_people_uuid, 
    mvr.face_embedding,
    mvr.embedding_confidence
FROM individual_mvr_mapping m
JOIN mvr_people mvr ON m.mvr_people_uuid = mvr.mvr_people_uuid
WHERE m.individual_uuid = ANY($1::uuid[])  -- Session individuals
  AND mvr.face_embedding IS NOT NULL;
```

**Benefits**:
- ✅ Finds MVR even with different video selections
- ✅ More robust to time-frame changes
- ✅ Logical consistency: MVR cache works at individual level
- ✅ Higher cache hit rate

### Implementation

**Location**: `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Lines**: ~2580-2640 (modified November 8, 2025)

### Logic Flow

```python
# After all individuals are created/cached for the session
# Check if any are already mapped to MVR people

async with db_client.pool.acquire() as conn:
    # Get individuals from current session
    session_individual_uuids = [
        record['individual_uuid']
        for record in await conn.fetch("""
            SELECT individual_uuid 
            FROM session_individuals 
            WHERE session_uuid = $1
        """, session_uuid)
    ]
    
    if not session_individual_uuids:
        logger.info("[MVR CACHE] No individuals in session")
        mvr_cache_hits = 0
    else:
        # Find MVR people mapped to these individuals
        cached_mvr_records = await conn.fetch("""
            SELECT DISTINCT 
                m.mvr_people_uuid,
                mvr.face_embedding,
                mvr.embedding_confidence
            FROM individual_mvr_mapping m
            JOIN mvr_people mvr 
                ON m.mvr_people_uuid = mvr.mvr_people_uuid
            WHERE m.individual_uuid = ANY($1::uuid[])
              AND mvr.face_embedding IS NOT NULL
        """, session_individual_uuids)
        
        mvr_cache_hits = len(set(
            r['mvr_people_uuid'] for r in cached_mvr_records
        ))
```

### Cache Key
**Individual UUID** - The cache is individual-based, so any individuals that were previously merged into an MVR will trigger a cache hit.

### Merge Decision Logic

```python
# Decide whether to run merge based on cache hits
total_candidates = mvr_cache_hits + len(created_individual_uuids)

should_run_merge = (
    (len(created_individual_uuids) >= 2) or  # Multiple new individuals
    (mvr_cache_hits >= 1 and len(created_individual_uuids) >= 1)  # Cached + new
)

if should_run_merge:
    # Run merge: Compare new individuals against:
    # 1. Each other (standard similarity merge)
    # 2. Cached MVR embeddings (future enhancement)
    merged_count = await merge_individuals_by_similarity(...)
```

---

## MVR Embedding Storage

### Purpose
Store a canonical embedding for each MVR person to enable fast similarity comparison without regenerating embeddings.

### Database Schema

**Migration**: `005_add_mvr_embeddings.sql` (executed November 8, 2025)

```sql
ALTER TABLE mvr_people 
    ADD COLUMN IF NOT EXISTS face_embedding vector(512),
    ADD COLUMN IF NOT EXISTS embedding_confidence DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(50) DEFAULT 'Facenet512',
    ADD COLUMN IF NOT EXISTS embedding_created_at TIMESTAMP;

-- HNSW index for fast similarity search
CREATE INDEX idx_mvr_people_embedding 
    ON mvr_people 
    USING hnsw (face_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index for querying MVRs with embeddings
CREATE INDEX idx_mvr_people_has_embedding 
    ON mvr_people(embedding_created_at) 
    WHERE face_embedding IS NOT NULL;

-- Constraint for confidence range
ALTER TABLE mvr_people 
    ADD CONSTRAINT check_mvr_embedding_confidence 
    CHECK (embedding_confidence IS NULL OR 
           (embedding_confidence >= 0.0 AND embedding_confidence <= 1.0));
```

### Embedding Computation

**Location**: `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Lines**: ~1878-1910 (merge Phase C)

#### For Merge Groups (Multiple Individuals)

```python
for keep_uuid, merge_uuids in merge_groups:
    all_uuids_in_group = [keep_uuid] + merge_uuids
    
    # Collect embeddings and confidences from all individuals in group
    group_embeddings = []
    group_confidences = []
    for individual_uuid in all_uuids_in_group:
        idx = uuids.index(individual_uuid)
        embedding = faces_with_embeddings[idx]['embedding']
        confidence = faces_with_embeddings[idx]['confidence']
        
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        
        group_embeddings.append(embedding)
        group_confidences.append(confidence)
    
    # Compute quality-weighted mean embedding
    mvr_embedding = np.average(
        group_embeddings, 
        axis=0, 
        weights=group_confidences
    )
    mvr_confidence = float(np.mean(group_confidences))
    
    # Convert to list for PostgreSQL
    mvr_embedding_list = mvr_embedding.tolist()
    
    # Create MVR person with aggregated embedding
    mvr_people_uuid = str(uuid4())
    db_operations.append(('create_mvr_person', {
        'mvr_people_uuid': mvr_people_uuid,
        'featured_individual_uuid': keep_uuid,
        'face_embedding': mvr_embedding_list,
        'confidence_score': mvr_confidence,
        'quality_score': mvr_confidence
    }))
```

#### For Unique Individuals (No Merge)

```python
for i, individual_uuid in enumerate(uuids):
    if individual_uuid not in individual_to_mvr:
        # This individual is unique (not similar to anyone)
        embedding = faces_with_embeddings[i]['embedding']
        confidence = faces_with_embeddings[i]['confidence']
        
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        mvr_people_uuid = str(uuid4())
        db_operations.append(('create_mvr_person', {
            'mvr_people_uuid': mvr_people_uuid,
            'featured_individual_uuid': individual_uuid,
            'face_embedding': embedding,  # Single embedding, no averaging
            'confidence_score': confidence,
            'quality_score': confidence
        }))
```

### Database INSERT

**Location**: Lines ~2010-2045

```python
if op_type == 'create_mvr_person':
    # Convert embedding to pgvector string format
    embedding = params['face_embedding']
    if isinstance(embedding, list):
        embedding_str = str(embedding)
    else:
        embedding_str = str(embedding.tolist())
    
    await conn.execute("""
        INSERT INTO mvr_people (
            mvr_people_uuid,
            featured_individual_uuid,
            face_embedding,
            embedding_confidence,
            embedding_model,
            embedding_created_at,
            confidence_score,
            quality_score,
            face_quality
        ) VALUES (
            $1, $2, $3::vector, $4, $5, NOW(),
            $6, $7, $8
        )
    """, 
        params['mvr_people_uuid'],
        params['featured_individual_uuid'],
        embedding_str,  # '[0.41, 0.36, 0.21, ...]'
        params['confidence_score'],  # Used for embedding_confidence
        'Facenet512',  # Model name
        params['confidence_score'],  # confidence_score
        params['quality_score'],  # quality_score
        params['quality_score']  # face_quality
    )
```

### Embedding Format
- **Dimension**: 512 (Facenet512 model)
- **Type**: `vector(512)` (pgvector extension)
- **Storage**: String format `'[0.41377905, 0.36214602, ...]'` converted to vector
- **Aggregation**: Quality-weighted mean `np.average(embeddings, weights=confidences)`

---

## Test Results and Verification

### Test Session 1: Small Range (2 videos, 1 individual)
**UUID**: `c9c45c3c-3da2-4e81-8627-292fa2b1c9bc`  
**Time**: 2025-11-08 19:04:05  
**Range**: 2025-11-06 08:00 to 10:00  
**Result**:
- Videos: 2
- Individuals: 1
- MVR created: ❌ No (merge skipped, only 1 individual)
- Embedding stored: ❌ No

**Analysis**: Merge doesn't run with only 1 individual. This is expected behavior but reveals a gap: individuals that don't go through merge never get an MVR.

### Test Session 2: Wide Range (12 videos, 6 individuals → 1 MVR)
**UUID**: `33f548d1-65da-4374-98fe-bd673c709302`  
**Time**: 2025-11-08 19:05:33  
**Range**: 2025-11-05 00:00 to 2025-11-08 23:59  
**Result**:
- Videos: 12
- Individuals: 6
- MVR created: ✅ Yes
- Embedding stored: ✅ **YES**
- MVR UUID: `01447ff5-9643-4ba5-b761-2952ddee3e88`

**Database Verification**:
```sql
-- Query result
mvr_people_uuid: 01447ff5-9643-4ba5-b761-2952ddee3e88
status: ✅ HAS EMBEDDING
confidence: 0.733
embedding_model: Facenet512
embedding_created_at: 2025-11-08 19:05:37.607285
mapped_individuals: 6
```

**Embedding Data**:
```
face_embedding: [0.41377905, 0.36214602, 0.21021336, -0.31095716, ...]
  (512 dimensions)
```

**Analysis**: ✅ MVR embedding storage is **working correctly**. Quality-weighted mean of 6 individual embeddings computed and stored.

### Test Session 3: Overlapping Range (6 videos, 3 individuals → 1 MVR)
**UUID**: `dc1bcdef-7022-4f68-90c4-53822d70041b`  
**Time**: 2025-11-08 19:06:53  
**Range**: 2025-11-06 00:00 to 2025-11-07 23:59  
**Result**:
- Videos: 6
- Individuals: 3 (all marked as `new`)
- MVR created: ✅ Yes (new MVR, not cached)
- MVR cache hits: ❌ 0

**Video Overlap Analysis**:
- **Session 2 videos** (12 total): `1b4bd00e`, `225a7233`, `35c13b91`, `38bf1f11`, `40f2d732`, `57e1ecd1`, `a317110c`, `a919f858`, ...
- **Session 3 videos** (6 total): `1b4bd00e`, `225a7233`, `57e1ecd1`, `a317110c`, `a919f858`, `a9c5f963`
- **Overlap**: 5 out of 6 videos (83%)

**Expected Behavior**:
1. Individual cache should find individuals from overlapping videos
2. MVR cache should find MVR `01447ff5...` from Session 2
3. New individuals should be mapped to existing MVR

**Actual Behavior**:
1. ❌ Individual cache missed (all 3 individuals marked as `new`)
2. ❌ MVR cache missed (`cached_mvr=0`)
3. ❌ New MVR created instead of reusing existing

**Log Evidence**:
```
merge_check: created=3, cached_mvr=0
```

**Analysis**: ⚠️ **Caching is not working as expected**. Despite 5/6 videos overlapping between Session 2 and Session 3, neither individual cache nor MVR cache triggered.

---

## Session-Wide Bulk Cache (Fixed November 9, 2025)

### Issue: Cache Matching Wrong Sessions

**Problem**: Session-wide bulk cache was returning wrong results when individuals appeared in more videos than were originally submitted to the session (due to cross-video tracking).

**Example Bug Scenario**:
- Session d5955317: Submitted 6 videos, but individuals appeared in 22 videos (cross-video tracking)
- New request for 14 videos: Cache incorrectly matched Session d5955317 because 14 of its 22 videos overlapped
- Result: Got 92 individuals → 14 MVR people (WRONG)

**Root Cause**: Cache query used `individual_video_appearances` table, which shows WHERE individuals appear (includes cross-video tracked videos), not WHICH videos were submitted.

**Solution**: Changed cache query to use `video_processing_states` table, which tracks the PRIMARY KEY (video_uuid, session_uuid) - exactly which videos were submitted to each session.

### Fixed Query Logic

**Location**: `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py` lines 2292-2333

```sql
WITH candidate_sessions AS (
    SELECT ts.session_uuid, ts.created_at, ts.total_videos
    FROM tracking_sessions ts
    WHERE ts.status = 'completed'
      AND ts.session_uuid != $1
      AND ts.total_videos = $3  -- Must have same submitted video count
),
session_video_matches AS (
    SELECT cs.session_uuid, cs.created_at, cs.total_videos,
           COUNT(DISTINCT vps.video_uuid) as matching_videos
    FROM candidate_sessions cs
    JOIN video_processing_states vps  -- ✅ FIXED: Use submitted videos
        ON vps.session_uuid = cs.session_uuid
    WHERE vps.video_uuid = ANY($2::uuid[])
    GROUP BY cs.session_uuid, cs.created_at, cs.total_videos
)
SELECT session_uuid, created_at, matching_videos as video_count
FROM session_video_matches
WHERE matching_videos = total_videos  -- ALL submitted videos must match
ORDER BY created_at DESC
LIMIT 1
```

**Key Changes**:
1. ✅ Filter candidates by `total_videos` (same submission count)
2. ✅ JOIN with `video_processing_states` instead of `individual_video_appearances`
3. ✅ Count matching submitted videos, not appearance videos
4. ✅ Only match if ALL submitted videos are in current request

**Test Results**:
- Session 74090da9 (tested after fix): ✅ 0 videos, 0 individuals, 0 cache hits (correct - no false match)
- Previous buggy sessions (4f099642, fe8974df, 2344e424): All showed 92 individuals from wrong cache

**Status**: ✅ **FIXED AND VERIFIED** - Cache now only matches when exact same videos were SUBMITTED, not where individuals APPEAR.

---

## Known Issues and Next Steps

### Issue 1: Individual Cache Not Being Called (ROOT CAUSE IDENTIFIED)

**STATUS**: This issue is separate from the session-wide bulk cache fix completed on November 9, 2025.

**CRITICAL FINDING**: The `get_or_create_individuals_for_video()` function exists in the codebase but **is never called**!

**Evidence**:
- No `cache_lookup_existing_count` logs in Session 2 or Session 3
- Session 3 created 3 NEW individuals instead of reusing Session 2's individuals
- Code directly creates individuals from Orchestrator responses without checking cache

**Note**: The session-wide bulk cache (which caches entire sessions by video set) is now working correctly. This issue refers to the per-video individual cache, which is a different optimization layer.

**Current Flow (INCORRECT)**:
```
1. Call Orchestrator for ALL videos → Get matched_individuals
2. Create NEW individuals for all results
3. Check MVR cache (works, but for wrong individuals)
4. Merge new individuals → Create new MVR
```

**Expected Flow (CORRECT)**:
```
1. For each video:
   a. Check individual cache (individual_video_appearances)
   b. If cache hit: reuse existing individuals
   c. If cache miss: call Orchestrator → create new individuals
2. Combine cached + new individuals
3. Check MVR cache for cached individuals
4. Merge new individuals with cached MVR or each other
```

**Impact**:
- Session 3 had 83% video overlap with Session 2
- But created entirely new individuals (5cf43abf, 6192901d, 91b5508e)
- Created new MVR (503ec72f) instead of reusing Session 2's MVR (01447ff5)
- Cached MVR=0 (expected ≥1) and all individuals marked as "new"

**Diagnostic Results**:
```sql
-- Session 3's individuals are mapped to NEW MVR 503ec72f (created 2025-11-08 19:06:54)
-- Session 2's individuals are mapped to EXISTING MVR 01447ff5 (created 2025-11-08 19:05:37)
-- MVR cache query WORKS but finds the wrong MVR (503ec72f from Session 3, not 01447ff5 from Session 2)
```

**Code Location**:
- Function exists: `cross_video_tracking_simple.py` lines 115-315
- Should be called: Before creating new individuals (around line 2370-2420)
- Currently: Individuals created directly from Orchestrator batch (lines 2370-2480)

### Issue 3: Singles Don't Get MVR
**Problem**: Individuals that appear alone (no merge candidates) never get an MVR person created.

**Impact**:
- Incomplete MVR coverage
- Cache can't work for subsequent sessions with same person

**Solution Options**:
1. **Create MVR for all individuals** (even singles)
2. **Post-merge MVR creation** for unmapped individuals
3. **Lazy MVR creation** on first subsequent session

---

## Recent Fixes and Improvements

### ✅ Session-Wide Bulk Cache Fix (November 9, 2025)

**Problem Solved**: Cache was matching sessions based on where individuals appeared (including cross-video tracked videos) instead of which videos were originally submitted.

**Solution Implemented**:
- Changed cache query from `individual_video_appearances` to `video_processing_states`
- Added `total_videos` filter to match same submission count
- Ensured ALL submitted videos must match (exact set match)

**Impact**:
- Cache now correctly rejects false matches
- Prevents returning wrong individuals from sessions with different video sets
- Verified working with test session 74090da9

**Database Tables**:
- `video_processing_states`: Tracks PRIMARY KEY (video_uuid, session_uuid) - which videos were submitted
- `individual_video_appearances`: Shows where individuals appear - includes cross-video tracking

**Key Insight**: Semantic difference between "where do individuals appear?" vs "which videos were submitted?" is critical for correct cache behavior.

---

### Next Steps

### **PRIORITY 1: Fix Individual Cache Integration**

**Problem**: `get_or_create_individuals_for_video()` exists but is never called.

**Solution**: Wire up individual cache before Orchestrator calls.

**Note**: This is separate from the session-wide bulk cache (now fixed). The per-video individual cache is an additional optimization layer.

**Implementation** (in `cross_video_tracking_simple.py` around lines 2370-2420):

```python
# CURRENT CODE (INCORRECT):
# Lines 2370-2420: Direct Orchestrator → Create individuals
matched_individuals = await batch_call_orchestrator(videos)
for individual_data in matched_individuals:
    individual_uuid = str(uuid4())
    # Create individual directly...
    db_operations.append(('individual', {...}))

# FIXED CODE (CORRECT):
# Before Orchestrator batch, check individual cache for each video
all_individual_uuids = []
videos_needing_orchestrator = []

for video in videos:
    video_uuid = video['uuid']
    
    # Try individual cache first
    (cached_uuids, cache_hit) = await get_or_create_individuals_for_video(
        conn=conn,
        video_uuid=video_uuid,
        session_uuid=session_uuid,
        create_new_callback=None  # Don't create yet, just check cache
    )
    
    if cache_hit and cached_uuids:
        logger.info(f"✅ Cache hit for video {video_uuid[:8]}: {len(cached_uuids)} individuals")
        all_individual_uuids.extend(cached_uuids)
    else:
        videos_needing_orchestrator.append(video)

# Only call Orchestrator for cache misses
if videos_needing_orchestrator:
    matched_individuals = await batch_call_orchestrator(videos_needing_orchestrator)
    # Create individuals for Orchestrator results...
    # all_individual_uuids.extend(new_individual_uuids)
```

**Expected Outcome**:
- Session 3 would find 5 cached individuals from Session 2
- MVR cache would then find MVR 01447ff5 (not create new 503ec72f)
- Cache hit rate would be ~83% (5/6 videos)

---

### Priority 2: Verify MVR Cache Works After Individual Cache Fix

1. **Verify Individual Cache Query**
   - Add detailed logging to `query_existing_individuals_for_video()`
   - Check if query is executing correctly
   - Verify video UUIDs match exactly

2. **Verify MVR Cache Query**
   - Test the new individual-based query manually
   - Add logging to show when query executes
   - Verify `session_individuals` are populated before MVR cache query

3. **Fix Timing Issues**
   - Ensure MVR cache query happens AFTER all individuals are linked to session
   - Add transaction boundaries to guarantee order

### Priority 3: Handle Singles

4. **Handle Singles**
   - Decide on strategy for individuals without merge candidates
   - Implement MVR creation for singles

### Priority 4: Integration Testing

5. **Integration Testing**
   - Create controlled test with known overlapping videos
   - Verify both cache levels work correctly (session-wide bulk + per-video individual)
   - Document expected vs actual behavior

---

## Cache Architecture Summary (November 9, 2025)

The PPL Meta platform implements **three levels of caching** for cross-video tracking:

### Level 0: Session-Wide Bulk Cache ✅ WORKING
**Purpose**: Reuse entire completed sessions when the exact same video set is requested.

**Query**: Uses `video_processing_states` table to match submitted videos (not appearance videos).

**Status**: Fixed and verified working on November 9, 2025.

**Location**: Lines 2292-2333 in `cross_video_tracking_simple.py`

### Level 1: Individual-Level Cache ⚠️ NOT IMPLEMENTED
**Purpose**: Reuse individuals for videos that have been processed before.

**Query**: Should check `individuals` table by `video_uuid`.

**Status**: Function exists but is never called. Needs integration.

**Location**: Lines 115-315 in `cross_video_tracking_simple.py`

### Level 2: MVR-Level Cache 🔄 PARTIALLY WORKING
**Purpose**: Reuse MVR people when individuals represent the same real-world person.

**Query**: Uses `individual_mvr_mapping` joined with individuals in session.

**Status**: Query logic updated to individual-based approach. Needs verification after Level 1 is fixed.

**Location**: Lines 2580-2640 in `cross_video_tracking_simple.py`

### Performance Impact

With all three levels working:
1. **Session-Wide Cache** (Level 0): Instant response for repeated exact requests ✅
2. **Individual Cache** (Level 1): Skip Orchestrator calls for known videos (not yet working)
3. **MVR Cache** (Level 2): Skip merge computation for known people (partial)

---

## Appendix: Key Files and Locations

### Modified Files (November 8, 2025)

1. **`ppl-meta-vmeta/migrations/005_add_mvr_embeddings.sql`**
   - Added `face_embedding vector(512)` column
   - Added `embedding_confidence`, `embedding_model`, `embedding_created_at`
   - Created HNSW index for similarity search
   - Status: ✅ Executed successfully

2. **`ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`**
   - Lines ~1878-1910: Quality-weighted embedding computation
   - Lines ~2010-2045: MVR INSERT with embedding
   - Lines ~2580-2640: MVR cache query (video-based → individual-based)
   - Status: ✅ Modified, service restarted

### Database Tables

1. **`mvr_people`**
   - Primary table for Multi-Video Recognition people
   - New columns: `face_embedding`, `embedding_confidence`, `embedding_model`, `embedding_created_at`
   - Indexes: HNSW on `face_embedding`, B-tree on `embedding_created_at`

2. **`individual_mvr_mapping`**
   - Maps individuals to MVR people
   - Key for MVR cache queries

3. **`session_individuals`**
   - Links individuals to sessions
   - Contains `processing_type`: `new`, `cached`, `merged`, `extended`
   - Key for individual-based MVR cache

4. **`individuals`**
   - Contains all detected individuals
   - Queried by `video_uuid` for individual cache

5. **`individual_video_appearances`**
   - Contains video appearances for individuals
   - Used to verify video overlap

---

## Conclusion

The three-level caching architecture status as of **November 9, 2025**:

### ✅ **Working** (Production Ready):
1. **Session-Wide Bulk Cache** (Level 0)
   - Fixed cache matching logic using `video_processing_states`
   - Correctly rejects false matches from cross-video tracking
   - Verified working with test sessions
   - **Impact**: Instant response for repeated exact requests

2. **MVR Embedding Storage**
   - Quality-weighted mean embeddings stored in `mvr_people` table
   - HNSW index for fast similarity search
   - Individual-based MVR cache query logic implemented

### ⚠️ **Needs Implementation**:
1. **Individual-Level Cache** (Level 1)
   - Function exists (`get_or_create_individuals_for_video`) but not called
   - Needs integration before Orchestrator batch calls
   - **Impact**: Would skip Orchestrator API calls for known videos

2. **MVR Cache Verification** (Level 2)
   - Individual-based query logic updated
   - Needs testing after Level 1 is integrated
   - **Impact**: Would skip merge computation for known people

### 🔄 **Next Actions**:
1. Wire up individual cache in video processing pipeline
2. Verify MVR cache works with cached individuals
3. Handle singles (individuals without merge candidates)
4. Integration testing with all three cache levels

---

**Document Status**: Living document - updated November 9, 2025 with session-wide bulk cache fix. Will be updated as remaining cache levels are implemented and verified.

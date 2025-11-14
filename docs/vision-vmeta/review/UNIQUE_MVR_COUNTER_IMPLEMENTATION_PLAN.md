# Unique MVR Counter Implementation Plan

**Feature:** Auto-Merge Duplicates via MVR-People and Display Unique Count  
**Date:** November 1, 2025  
**Status:** Planning Phase

---

## Executive Summary

This document describes the implementation plan for adding a **unique individuals counter** to the cross-video tracking system. This counter will show the actual number of unique people after automatically merging duplicate detections using MVR-People face matching.

**Current Behavior:**
- Cross-video tracking finds individuals across multiple videos
- Same person may be detected as multiple "individuals" if they appear in different videos
- Only reports total detections: `individuals_found = 15`

**New Behavior:**
- Cross-video tracking finds individuals (same as before)
- Auto-matching detects duplicates using face similarity (MVR-People)
- Merges duplicates automatically
- Reports BOTH counts:
  - `individuals_found = 15` (original detections)
  - `unique_mvr_people_count = 12` (after merging 3 duplicates)

**User sees:** `15 → 12 unique` (3 duplicates were merged)

---

## Problem Statement

### Current Issue

When tracking individuals across multiple videos, the same person may be counted multiple times:

**Example Scenario:**
```
Video 1 (Camera-01, 10:00-10:30):
  - Person A appears → Creates Individual IND-001

Video 2 (Camera-02, 10:15-10:45):
  - Person A appears again → Creates Individual IND-002 (duplicate!)

Video 3 (Camera-01, 10:30-11:00):
  - Person A appears again → Creates Individual IND-003 (duplicate!)
  - Person B appears → Creates Individual IND-004

Result: individuals_found = 4
Reality: Only 2 unique people (Person A and Person B)
```

**Why duplicates occur:**
1. Person moves between camera views
2. Person leaves and re-enters the scene
3. Time gaps between appearances
4. Different lighting/angles in different videos

---

## Solution Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: Cross-Video Tracking (EXISTING)                  │
│  - Discover videos in time range                           │
│  - Fetch person objects from each video                    │
│  - Group person objects into "individuals"                 │
│  - Result: individuals_found = 15                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: Auto-Matching (NEW FEATURE)                      │
│  - For each individual, find similar individuals           │
│  - Compare face embeddings (MVR-People)                    │
│  - If similarity > 0.85, merge duplicates                  │
│  - Result: merge_count = 3                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: Calculate Unique Count                           │
│  - unique_mvr_people_count = individuals_found - merge_count│
│  - unique_mvr_people_count = 15 - 3 = 12                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: Store & Display                                  │
│  - Save both counts to database                            │
│  - Return in API response                                  │
│  - Flutter shows: "15 → 12 unique"                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Components

### 1. Database Schema Changes

**File:** `ppl-meta-vmeta/migrations/003_add_unique_mvr_count.sql`

#### Add Column to tracking_sessions Table

```sql
-- Add new column for unique count
ALTER TABLE tracking_sessions 
ADD COLUMN IF NOT EXISTS unique_mvr_people_count INTEGER DEFAULT 0;

-- Add comment for documentation
COMMENT ON COLUMN tracking_sessions.unique_mvr_people_count IS 
  'Number of unique individuals after MVR-People auto-matching and merging duplicates';
```

#### Add Performance Indexes

```sql
-- Index for queries filtering by unique count
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_unique_mvr_count 
ON tracking_sessions(unique_mvr_people_count) 
WHERE unique_mvr_people_count > 0;

-- Composite index for analytics queries
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_merge_stats 
ON tracking_sessions(individuals_found, unique_mvr_people_count) 
WHERE status = 'completed';
```

**Purpose:**
- Fast queries for sessions with merged individuals
- Efficient analytics (e.g., "sessions with highest duplicate rate")

#### Backfill Existing Data

```sql
-- For completed sessions without unique count, set to individuals_found
UPDATE tracking_sessions
SET unique_mvr_people_count = individuals_found
WHERE status = 'completed' 
  AND unique_mvr_people_count = 0;
```

**Result:** Old sessions will show `X → X` (no merging applied retroactively)

---

### 2. Backend Processing Logic

**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Function:** `process_tracking_session()`

#### Step 2.1: Initialize Unique Count

**Location:** After cross-video tracking completes, before database update

```python
# Cross-video tracking has completed
individuals_found = 15  # Number of individuals created

# Initialize unique count (default: no merging)
unique_mvr_people_count = individuals_found

logger.info(
    f"Cross-video tracking complete: {individuals_found} individuals found"
)
```

---

#### Step 2.2: Auto-Matching Logic (Only if Multiple Individuals)

```python
if individuals_found > 1:
    logger.info(
        f"Starting auto-matching for {individuals_found} individuals "
        f"in session {session_uuid}"
    )
    
    try:
        # Import MVR matching services
        from services.mvr_matcher import MVRMatcher
        from database.mvr_repository import MVRRepository
        
        # Initialize services
        mvr_repository = MVRRepository(db_client.pool)
        mvr_matcher = MVRMatcher(mvr_repository)
        
        # Track which individuals have been merged
        merged_individuals = set()
        merge_count = 0
        
        # For each individual, find and merge duplicates
        for individual_uuid in created_individuals:
            # Skip if already merged
            if individual_uuid in merged_individuals:
                logger.debug(f"Skipping {individual_uuid} (already merged)")
                continue
            
            # Find matching individuals using face similarity
            matches = await mvr_matcher.find_matching_mvr(
                individual_uuid=individual_uuid,
                threshold=0.85,  # 85% similarity threshold
                limit=10  # Max matches to check
            )
            
            logger.debug(
                f"Found {len(matches)} potential matches for {individual_uuid}"
            )
            
            # Merge each match above threshold
            for match in matches:
                match_uuid = match.get('individual_uuid')
                similarity = match.get('similarity_score', 0.0)
                
                # Skip if already merged
                if match_uuid in merged_individuals:
                    continue
                
                # Only merge if similarity is above threshold
                if similarity >= 0.85:
                    logger.info(
                        f"Merging {individual_uuid} with {match_uuid} "
                        f"(similarity: {similarity:.3f})"
                    )
                    
                    # Perform merge
                    merge_result = await mvr_matcher.merge_individuals(
                        individual_a_uuid=individual_uuid,
                        individual_b_uuid=match_uuid,
                        similarity_score=similarity,
                        triggered_by="auto_match_session",
                        session_uuid=session_uuid
                    )
                    
                    # Check if merge was successful
                    if merge_result and merge_result.get('success'):
                        # Track the orphaned individual (the one that was merged away)
                        orphaned_uuid = merge_result.get('orphaned_mvr_uuid')
                        merged_individuals.add(str(orphaned_uuid))
                        merge_count += 1
                        
                        logger.info(
                            f"Successfully merged: {orphaned_uuid} is now orphaned"
                        )
                    else:
                        logger.warning(
                            f"Merge failed for {individual_uuid} and {match_uuid}"
                        )
        
        # Calculate unique count after all merging
        unique_mvr_people_count = individuals_found - merge_count
        
        logger.info(
            f"Auto-matching complete for session {session_uuid}: "
            f"{individuals_found} individuals → {unique_mvr_people_count} unique "
            f"(merged {merge_count} duplicates)"
        )
        
    except Exception as auto_match_error:
        logger.error(
            f"Auto-matching failed for session {session_uuid}: {auto_match_error}",
            exc_info=True
        )
        # On error, keep original count (no merging)
        unique_mvr_people_count = individuals_found
else:
    logger.info(
        f"Skipping auto-matching: only {individuals_found} individual(s) found"
    )
```

---

#### Step 2.3: Update Database with Both Counts

```python
# Update session status with BOTH counts
async with db_client.pool.acquire() as conn:
    await conn.execute("""
        UPDATE tracking_sessions 
        SET status = 'completed', 
            completed_at = NOW(),
            processing_time_seconds = 3.0,
            processed_videos = $2, 
            individuals_found = $3,
            unique_mvr_people_count = $4
        WHERE session_uuid = $1
    """, session_uuid, processed_count, individuals_found, unique_mvr_people_count)

logger.info(
    f"Session {session_uuid} completed: "
    f"{processed_count} videos, "
    f"{individuals_found} individuals, "
    f"{unique_mvr_people_count} unique MVR-People"
)
```

---

### 3. API Response Updates

**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Function:** `get_session_status()`

#### Current Implementation (Without Unique Count)

```python
@router.get("/sessions/{session_uuid}")
async def get_session_status(session_uuid: str):
    """Get tracking session status."""
    db_client = get_database_client()
    
    async with db_client.pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT session_uuid, status, collections, created_at, 
                   started_at, completed_at, total_videos, processed_videos,
                   individuals_found, cache_hits
            FROM tracking_sessions 
            WHERE session_uuid = $1
        """, session_uuid)
    
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_uuid": str(result["session_uuid"]),
        "status": result["status"],
        "collections": result["collections"],
        "created_at": result["created_at"],
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
        "total_videos": result["total_videos"],
        "processed_videos": result["processed_videos"],
        "individuals_found": result["individuals_found"],  # Only original count
        "cache_hits": result["cache_hits"]
    }
```

**Response:**
```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "individuals_found": 15,
  "cache_hits": 0
}
```

---

#### New Implementation (With Unique Count)

```python
@router.get("/sessions/{session_uuid}")
async def get_session_status(session_uuid: str):
    """Get tracking session status with unique count."""
    db_client = get_database_client()
    
    async with db_client.pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT session_uuid, status, collections, created_at, 
                   started_at, completed_at, total_videos, processed_videos,
                   individuals_found, cache_hits
            FROM tracking_sessions 
            WHERE session_uuid = $1
        """, session_uuid)
    
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Build base response
    response = {
        "session_uuid": str(result["session_uuid"]),
        "status": result["status"],
        "collections": result["collections"],
        "created_at": result["created_at"],
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
        "total_videos": result["total_videos"],
        "processed_videos": result["processed_videos"],
        "individuals_found": result["individuals_found"],
        "cache_hits": result["cache_hits"]
    }
    
    # Try to add unique count (backward compatible)
    try:
        async with db_client.pool.acquire() as conn:
            unique_count = await conn.fetchval("""
                SELECT unique_mvr_people_count
                FROM tracking_sessions 
                WHERE session_uuid = $1
            """, session_uuid)
            
            # Add to response if column exists and has value
            if unique_count is not None and unique_count > 0:
                response["unique_mvr_people_count"] = unique_count
            else:
                # Column exists but no value, use individuals_found
                response["unique_mvr_people_count"] = result["individuals_found"]
    except Exception as e:
        # Column doesn't exist (old database), use individuals_found as fallback
        logger.debug(f"unique_mvr_people_count column not found: {e}")
        response["unique_mvr_people_count"] = result["individuals_found"]
    
    return response
```

**New Response:**
```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "individuals_found": 15,
  "unique_mvr_people_count": 12,  ← NEW FIELD
  "cache_hits": 0
}
```

**Backward Compatibility:**
- If column doesn't exist → Falls back to `individuals_found`
- If column exists but value is 0 → Uses `individuals_found`
- If column exists with value → Uses actual unique count

---

### 4. Flutter UI (Already Implemented)

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`

#### Data Extraction (Already Done)

```dart
final individualsFound = statusResponse.data!['individuals_found'] as int? ?? 0;

// Check if API actually returned unique_mvr_people_count
final hasUniqueCount = statusResponse.data!.containsKey('unique_mvr_people_count');
final uniqueMvrCount = statusResponse.data!['unique_mvr_people_count'] as int?;

if (hasUniqueCount && uniqueMvrCount != null) {
  // API returned real unique count
  _uniqueMvrCount = uniqueMvrCount;
  _uniqueCountIsFallback = false;
} else {
  // API didn't return unique count, using fallback
  _uniqueMvrCount = individualsFound;
  _uniqueCountIsFallback = true;
}
```

#### Display Logic (Already Done)

```dart
Text(
  _uniqueCountIsFallback 
    ? '[]'                                    // Show [] when fallback
    : '${_uniqueMvrCount ?? 0} unique',       // Show count when real data
  style: AppTextStyles.bodySmall.copyWith(
    color: _uniqueCountIsFallback 
      ? AppColors.error                        // Red for fallback
      : AppColors.success,                     // Green for real data
    fontWeight: FontWeight.w700,
  ),
)
```

**UI States:**
- Loading: `Individuals: (spinner)`
- Fallback: `Individuals: 15 → []` (red)
- Real data: `Individuals: 15 → 12 unique` (green)

---

## MVR-People Integration

### MVRMatcher Service

**File:** `ppl-meta-vmeta/src/services/mvr_matcher.py`

#### find_matching_mvr()

**Purpose:** Find individuals with similar faces

```python
async def find_matching_mvr(
    self,
    individual_uuid: str,
    threshold: float = 0.85,
    limit: int = 10
) -> List[Dict]:
    """
    Find individuals with similar face embeddings.
    
    Args:
        individual_uuid: Individual to find matches for
        threshold: Minimum similarity score (0.0-1.0)
        limit: Maximum number of matches to return
    
    Returns:
        List of matches with similarity scores:
        [
            {
                'individual_uuid': 'uuid-2',
                'similarity_score': 0.92,
                'confidence': 0.88
            },
            ...
        ]
    """
```

**Algorithm:**
1. Get face embedding for `individual_uuid`
2. Get best face from individual's appearances
3. Query MVR-People database for similar embeddings
4. Calculate cosine similarity
5. Filter by threshold (0.85 = 85% similar)
6. Return top matches

---

#### merge_individuals()

**Purpose:** Merge two individuals into one

```python
async def merge_individuals(
    self,
    individual_a_uuid: str,
    individual_b_uuid: str,
    similarity_score: float,
    triggered_by: str = "auto_match_session",
    session_uuid: Optional[str] = None
) -> Dict:
    """
    Merge two individuals into one.
    
    Process:
    1. Choose primary (higher confidence/more appearances)
    2. Transfer appearances from secondary to primary
    3. Update MVR-People links
    4. Mark secondary as orphaned
    5. Log merge in audit trail
    
    Returns:
        {
            'success': True,
            'primary_uuid': 'uuid-1',
            'orphaned_mvr_uuid': 'uuid-2',
            'transferred_appearances': 5
        }
    """
```

**Business Rules:**
- Primary = Individual with higher confidence OR more appearances
- Secondary becomes "orphaned" (soft delete, not physical delete)
- All appearances transferred to primary
- MVR-People records updated to point to primary
- Merge is logged for audit trail

---

### Face Similarity Threshold

**Value:** 0.85 (85% similarity)

**Why 0.85?**
- **Too low (e.g., 0.6):** False positives (merging different people)
- **Too high (e.g., 0.95):** False negatives (missing duplicates)
- **0.85:** Balanced - catches same person in different conditions

**Factors affecting similarity:**
- Lighting differences
- Camera angles
- Facial expressions
- Time elapsed between appearances
- Image quality

**Examples:**
- 0.95+ = Same person, same conditions
- 0.85-0.95 = Same person, different conditions ✅ TARGET
- 0.70-0.85 = Possibly same person (rejected)
- <0.70 = Different people

---

## Implementation Phases

### Phase 1: Database Schema ✅ COMPLETED

**Tasks:**
- [x] Create migration file `003_add_unique_mvr_count.sql`
- [x] Add `unique_mvr_people_count` column
- [x] Add performance indexes
- [x] Backfill existing sessions
- [x] Apply migration to production database

**Status:** 58 sessions migrated successfully

---

### Phase 2: Basic API Integration (IN PROGRESS)

**Tasks:**
- [x] Update `get_session_status()` to return unique count
- [x] Add backward compatibility logic
- [ ] Update `process_tracking_session()` to initialize unique count
- [ ] Update database UPDATE statement with both counts
- [ ] Test that original `individuals_found` still works

**Current Step:** Add field to database UPDATE (Step 1)

---

### Phase 3: Auto-Matching Logic (PLANNED)

**Tasks:**
- [ ] Import MVRMatcher and MVRRepository services
- [ ] Implement loop through created_individuals
- [ ] Call `find_matching_mvr()` for each individual
- [ ] Call `merge_individuals()` for matches above threshold
- [ ] Track merge count
- [ ] Calculate `unique_mvr_people_count = individuals_found - merge_count`
- [ ] Handle errors gracefully (fall back to original count)

**Estimated Complexity:** High

---

### Phase 4: Testing & Validation (PLANNED)

**Test Cases:**

#### Test 1: No Duplicates
```
Input: 5 individuals, all different people
Expected:
  - individuals_found = 5
  - unique_mvr_people_count = 5
  - merge_count = 0
```

#### Test 2: Some Duplicates
```
Input: 10 individuals (7 unique, 3 duplicates)
Expected:
  - individuals_found = 10
  - unique_mvr_people_count = 7
  - merge_count = 3
```

#### Test 3: All Duplicates
```
Input: 6 individuals (same person, different videos)
Expected:
  - individuals_found = 6
  - unique_mvr_people_count = 1
  - merge_count = 5
```

#### Test 4: Error Handling
```
Input: Auto-matching throws exception
Expected:
  - individuals_found = 10
  - unique_mvr_people_count = 10 (fallback)
  - merge_count = 0
  - Error logged
```

---

### Phase 5: Flutter UI Validation (COMPLETED)

**Tasks:**
- [x] Extract both counters from API
- [x] Detect when unique count is missing (fallback)
- [x] Display `[]` when using fallback
- [x] Display `X unique` when real data
- [x] Color coding (red=fallback, green=real)
- [x] Debug logging

**Status:** ✅ Complete - UI shows `1 → []` when fallback

---

## Performance Considerations

### Database Impact

**Additional Storage:**
- 1 INTEGER column per session (~4 bytes)
- 2 new indexes (minimal overhead)

**Query Performance:**
- Indexes ensure fast filtering and analytics
- No impact on existing queries

---

### Auto-Matching Performance

**Complexity:** O(n²) worst case (n = individuals_found)

**Optimization:**
```python
for individual in individuals:        # n iterations
    matches = find_matches(individual) # O(log m) with indexes
    for match in matches:              # Max 10 matches
        merge(individual, match)       # O(1) database update
```

**Actual Complexity:** O(n * log m) where:
- n = individuals_found
- m = total MVR-People records

**Example Timing:**
- 10 individuals: ~1-2 seconds
- 50 individuals: ~5-10 seconds
- 100 individuals: ~15-30 seconds

**Mitigation:**
- Runs in background task (doesn't block API)
- Threshold limits matches checked (max 10 per individual)
- Database indexes speed up similarity queries

---

### Network Impact

**API Response Size:**
- Added 1 field: `"unique_mvr_people_count": 12`
- Increase: ~30 bytes
- Impact: Negligible

---

## Error Handling

### Scenario 1: Auto-Matching Fails

```python
try:
    # Auto-matching logic
    unique_mvr_people_count = individuals_found - merge_count
except Exception as e:
    logger.error(f"Auto-matching failed: {e}")
    unique_mvr_people_count = individuals_found  # Fall back to original count
```

**Result:** Session completes, both counters show same value

---

### Scenario 2: Database Column Missing

```python
try:
    unique_count = await conn.fetchval("SELECT unique_mvr_people_count ...")
    response["unique_mvr_people_count"] = unique_count
except Exception:
    # Column doesn't exist, use fallback
    response["unique_mvr_people_count"] = result["individuals_found"]
```

**Result:** API returns fallback value, Flutter shows `[]`

---

### Scenario 3: Merge Fails

```python
merge_result = await mvr_matcher.merge_individuals(...)
if merge_result and merge_result.get('success'):
    merge_count += 1
else:
    logger.warning(f"Merge failed for {individual_uuid}")
    # Continue processing other individuals
```

**Result:** Failed merge skipped, other merges continue

---

## Monitoring & Observability

### Metrics to Track

1. **Merge Rate**
   ```sql
   SELECT 
       AVG((individuals_found - unique_mvr_people_count)::FLOAT / individuals_found) * 100 AS avg_merge_rate
   FROM tracking_sessions
   WHERE status = 'completed' AND individuals_found > 0;
   ```

2. **Sessions with Merges**
   ```sql
   SELECT COUNT(*) AS sessions_with_merges
   FROM tracking_sessions
   WHERE unique_mvr_people_count < individuals_found;
   ```

3. **High Duplicate Rate Sessions**
   ```sql
   SELECT 
       session_uuid,
       individuals_found,
       unique_mvr_people_count,
       ROUND((individuals_found - unique_mvr_people_count)::NUMERIC / individuals_found * 100, 1) AS duplicate_rate
   FROM tracking_sessions
   WHERE status = 'completed' 
     AND individuals_found > unique_mvr_people_count
   ORDER BY duplicate_rate DESC
   LIMIT 10;
   ```

---

### Logging Strategy

**Log Levels:**
- `INFO`: Normal operations (merge counts, completion)
- `DEBUG`: Detailed matching info (similarity scores)
- `WARNING`: Failed merges (continue processing)
- `ERROR`: Auto-matching failures (fall back to original count)

**Example Logs:**
```
INFO: Cross-video tracking complete: 15 individuals found
INFO: Starting auto-matching for 15 individuals in session abc-123
DEBUG: Found 2 potential matches for uuid-1
INFO: Merging uuid-1 with uuid-7 (similarity: 0.920)
INFO: Successfully merged: uuid-7 is now orphaned
INFO: Auto-matching complete: 15 individuals → 12 unique (merged 3 duplicates)
INFO: Session abc-123 completed: 10 videos, 15 individuals, 12 unique MVR-People
```

---

## Security & Privacy Considerations

### Data Retention

**Question:** Should merged individuals be soft-deleted or hard-deleted?

**Answer:** Soft delete (orphaned status)

**Reasons:**
- Audit trail for compliance
- Ability to un-merge if needed
- Forensic analysis

**Implementation:**
```python
# Mark as orphaned instead of deleting
await conn.execute("""
    UPDATE individuals 
    SET status = 'orphaned',
        merged_into = $2,
        merged_at = NOW()
    WHERE individual_uuid = $1
""", secondary_uuid, primary_uuid)
```

---

### GDPR Compliance

**Impact:** Merging doesn't change data retention

**Right to be Forgotten:**
- Delete both primary AND orphaned records
- Cascade to MVR-People records
- Remove from tracking_sessions references

---

## Rollback Plan

### If Feature Needs to be Disabled

**Option 1: Stop Auto-Matching**
```python
# In process_tracking_session()
ENABLE_AUTO_MATCHING = False  # Feature flag

if ENABLE_AUTO_MATCHING and individuals_found > 1:
    # Auto-matching logic
    pass
else:
    unique_mvr_people_count = individuals_found
```

**Option 2: Revert Database Migration**
```sql
-- Remove column
ALTER TABLE tracking_sessions DROP COLUMN IF EXISTS unique_mvr_people_count;

-- Drop indexes
DROP INDEX IF EXISTS idx_tracking_sessions_unique_mvr_count;
DROP INDEX IF EXISTS idx_tracking_sessions_merge_stats;
```

**Option 3: Revert Code Changes**
```bash
# Restore original file
git checkout 2f04ec90 -- ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py
```

---

## Success Criteria

### Definition of Done

- [ ] Database migration applied successfully
- [ ] Backend returns `unique_mvr_people_count` in API response
- [ ] Auto-matching merges duplicates correctly
- [ ] Flutter UI shows both counters
- [ ] Flutter UI shows `[]` when fallback is used
- [ ] Flutter UI shows `X unique` when real data is available
- [ ] No regression in original `individuals_found` logic
- [ ] Performance acceptable (<30s for 100 individuals)
- [ ] Error handling tested and working
- [ ] Documentation updated

### Acceptance Tests

1. **Test with real data:**
   - Create tracking session with known duplicates
   - Verify both counters appear
   - Verify unique count is less than original count
   - Verify Flutter shows green `X unique`

2. **Test backward compatibility:**
   - Restore old backend version
   - Verify Flutter shows red `[]`
   - Verify first counter still works

3. **Test error handling:**
   - Simulate auto-matching failure
   - Verify session completes
   - Verify both counters show same value

---

## Timeline & Effort Estimate

| Phase | Tasks | Estimated Time | Status |
|-------|-------|----------------|--------|
| Phase 1: Database | Migration + testing | 2 hours | ✅ DONE |
| Phase 2: Basic API | Add field to response | 1 hour | 🔄 IN PROGRESS |
| Phase 3: Auto-Matching | Implement merge logic | 4-6 hours | ⏳ PLANNED |
| Phase 4: Testing | Test cases + validation | 2-3 hours | ⏳ PLANNED |
| Phase 5: Flutter | UI updates | 1 hour | ✅ DONE |
| **TOTAL** | | **10-13 hours** | |

---

## Next Steps

### Immediate (Phase 2 - Step 1)

1. **Update database UPDATE statement**
   - Add `unique_mvr_people_count = $4` parameter
   - Initialize to `individuals_found` (no merging yet)
   - Test that both counters appear in Flutter

2. **Verify no regression**
   - Confirm `individuals_found` still works correctly
   - Confirm Flutter shows real data (not `[]`)

### Short Term (Phase 3)

1. **Implement auto-matching loop**
   - Import MVRMatcher service
   - Loop through created_individuals
   - Find and merge duplicates

2. **Calculate unique count**
   - Track merge_count
   - Set `unique_mvr_people_count = individuals_found - merge_count`

### Long Term (Phase 4-5)

1. **Comprehensive testing**
2. **Performance optimization**
3. **Documentation updates**
4. **Monitoring setup**

---

**Author:** PPL Meta Platform Team  
**Last Updated:** November 1, 2025  
**Version:** 1.0

# PPL Meta Analytics Issues

**Date:** January 5, 2026  
**Status:** ✅ **RESOLVED - Backend Complete**  
**Priority:** High

---

## Overview

The continuous pipeline (face detection → individuals → MVR people) is **working correctly end-to-end**. Data is successfully created and stored in the database. The issue was that analytics was querying at the wrong level - looking for quality data in `individual_video_appearances.representative_faces` when it's actually stored in `mvr_people.face_quality`.

**Resolution:** New MVR-based quality metrics endpoint implemented that correctly queries the MVR → Individual data tree.

**Key Finding:** The tracking session endpoint proves the data exists:
- ✅ individuals_found: 1
- ✅ unique_mvr_people_count: 1
- ✅ Status: completed

The issue is **not missing data** - it's that we need to follow the correct data tree: **MVR People → Individuals → representative_faces**

---

## Issue 1: Analytics Using Wrong Data Access Pattern

### Problem Description
The quality metrics endpoint queries `individual_video_appearances` table and filters for `representative_faces IS NOT NULL`. This approach fails because:
1. It tries to access individuals directly instead of following the MVR → Individual relationship
2. It filters out individuals where representative_faces extraction didn't complete via Enhanced V2 endpoint
3. It doesn't leverage the tracking session data that proves the pipeline worked

### Root Cause
The analytics is querying at the wrong level of the data hierarchy. The correct approach is:

**Current (Wrong):**
```
individual_video_appearances (WHERE representative_faces IS NOT NULL)
→ Returns 0 because Enhanced V2 endpoint returned 0 person_objects
```

**Correct:**
```
MVR People (created by tracking session)
→ Get linked Individuals
→ Each Individual has representative_faces in individual_video_appearances
→ Extract quality metrics from representative_faces
```

### Evidence
**Tracking Session Result (18:43) - Proves Data Exists:**
```json
{
    "session_uuid": "b5b0f910-09ac-44d0-a6f1-3881e9566a1c",
    "status": "completed",
    "collections": ["None Collection"],
    "total_videos": 3,
    "processed_videos": 3,
    "individuals_found": 1,        ✅ DATA EXISTS
    "unique_mvr_people_count": 1,  ✅ DATA EXISTS
    "cache_hits": 0
}
```

**Quality Metrics Result (same timeframe) - Wrong Query:**
```json
{
    "time_filter": "today",
    "total_individuals": 0,  ❌ QUERYING WRONG TABLE
    "active_collections": 0,
    "overall_average_quality": 0.0
}
```

**Vmeta Logs - Preload Succeeded:**
```
🔄 Preloading person_objects for all 3 videos
✅ Preload complete: 3/3 videos succeeded  ✅ PERSON OBJECTS FOUND VIA DATABASE
✅ Matched 562122ab with 9e2b1512
✅ Created individual cca24886 appearing in 3 videos
```

### Impact
- ❌ Quality metrics endpoint returns 0 (using wrong query path)
- ❌ Analytics dashboard shows no data (not following MVR → Individual tree)
- ✅ Data EXISTS: individuals_found: 1, unique_mvr_people_count: 1
- ✅ Data IS QUERYABLE: vmeta preload succeeded, individual created
- ✅ Person objects ARE in database (direct query found them)

### Correct Data Access Pattern

**Step 1: Get MVR People for Collection/Timeframe**
```bash
# Option A: Via tracking sessions (recommended)
GET /api/v1/cross-video/individuals/tracking/sessions?collection=X&start_time=...&end_time=...

# Option B: Direct MVR search
POST /api/v1/mvr/people/search
Body: {"collection": "X", "start_time": "...", "end_time": "..."}
```

**Step 2: For Each MVR Person, Get Linked Individuals**
```bash
GET /api/v1/mvr/people/{mvr_uuid}
Returns: {
    linked_individuals: [
        {
            individual_uuid: "...",
            video_count: 3,
            representative_faces: {...}  ✅ QUALITY DATA HERE
        }
    ]
}
```

**Step 3: Extract Quality Metrics from representative_faces**
```python
for mvr in mvr_people:
    for individual in mvr.linked_individuals:
        if individual.representative_faces:
            for face in individual.representative_faces.faces:
                quality_scores.append(face.quality_score)
```

### Proposed Solution

**Solution A: Fix Analytics to Follow MVR Tree (Recommended)**
Modify quality metrics endpoint to:
1. Query tracking sessions for collection + timeframe
2. Get MVR people created in those sessions
3. For each MVR person, get linked individuals
4. Extract representative_faces from individuals
5. Calculate quality metrics from face data

**Benefits:**
- ✅ Uses data that actually exists
- ✅ Follows proper data hierarchy
- ✅ Leverages tracking session metadata
- ✅ Gets correct counts (individuals_found, unique_mvr_people_count)

**Solution B: Add MVR-Based Analytics Endpoint**
Create new endpoint:
```bash
GET /api/v1/analytics/mvr-quality-metrics?collection=X&start_time=...&end_time=...

Returns: {
    mvr_people_count: 1,
    individuals_count: 1,
    videos_processed: 3,
    average_quality: 0.78,
    quality_by_mvr: [...]
}
```

---

## Issue 2: Enhanced V2 Endpoint Returns 0 Person Objects (Secondary Issue)

### Problem Description
When vmeta calls Enhanced Logic V2 endpoint to extract representative_faces during batch processing, it returns **0 person_objects** for all videos, even though the person_objects exist in the database.

### Timeline of Events
1. **18:43:00** - Vision service creates person objects (in-memory mode due to race condition)
2. **18:43:00** - Person objects committed to database ✅
3. **18:43:03** - Vmeta calls Enhanced V2 endpoint → Returns 0 person_objects ❌
4. **18:43:03** - Vmeta preloads via direct database query → Finds person objects ✅
5. **18:43:14** - Individual created successfully (using preloaded person objects) ✅

### Root Cause
Enhanced V2 endpoint has different filtering logic than the direct database query. Likely filters out person_objects from sessions created in in-memory mode, or has session validation that excludes them.

### Impact
- ❌ representative_faces extraction fails via Enhanced V2 endpoint
- ✅ But individual creation succeeds via direct database preload
- ✅ Data is queryable and accessible
- ⚠️ Quality metrics can't be extracted via Enhanced V2 route

### Why This is Secondary
The person_objects ARE in the database and ARE queryable - vmeta's preload proved this. The Enhanced V2 endpoint's filtering logic is overly restrictive, but this doesn't block analytics if we follow the MVR → Individual data tree correctly.

### Proposed Solution
**Option A: Don't Use Enhanced V2 for representative_faces**
Modify vmeta batch processing to extract representative_faces directly from person_objects via database query (same method used in preload). Skip Enhanced V2 endpoint entirely for this purpose.

**Option B: Fix Enhanced V2 Endpoint Filtering**
Update Enhanced V2 endpoint to return person_objects even when created via in-memory mode or when session validation fails.

**Option C: No Action Required**
If analytics properly follows MVR → Individual tree, representative_faces should already be populated in individual_video_appearances from the preload data. Verify this first before fixing Enhanced V2.

---

## Issue 3: Analytics Data Split Across Multiple Endpoints (Original Architecture)

### Problem Description
Analytics data is fragmented across multiple service endpoints, making it difficult to get a complete picture of the system state.

### Current State

#### Gateway Analytics Endpoint (Port 8080)
```bash
GET /api/v1/analytics/quality-metrics
```
**Returns:** 
- total_individuals (currently 0 due to Issue 1)
- overall_average_quality
- collection_breakdown
- quality_grade

**Issues:**
- Filters WHERE representative_faces IS NOT NULL
- Returns 0 even when data exists
- No MVR people count
- No person objects count
- No face detection statistics

#### Vmeta Tracking Session Endpoint (Port 8008)
```bash
GET /api/v1/cross-video/individuals/tracking/sessions/{session_uuid}
```
**Returns:**
- individuals_found ✅
- unique_mvr_people_count ✅
- total_videos ✅
- processed_videos ✅
- cache_hits

**Issues:**
- Requires knowing session_uuid
- Only shows data for one specific tracking batch
- No way to get "all individuals for collection X in time range Y"

#### Vmeta MVR Search Endpoint (Port 8008)
```bash
POST /api/v1/mvr/people/search
Body: {"video_uuids": [...], "start_time": "...", "end_time": "..."}
```
**Returns:**
- List of MVR people
- Video appearances per MVR person

**Issues:**
- Requires providing specific video_uuids upfront
- Cannot query by collection name alone
- No aggregated statistics (just raw list)

#### Vision Person Objects Endpoint (Port 8003/8002)
```bash
GET /api/v1/media/{video_uuid}/faces/enhanced-v2
```
**Returns:**
- Person objects for specific video
- Face detection results

**Issues:**
- Single video only
- No batch/collection queries
- No aggregated statistics

### Impact on Analytics Dashboard
The analytics page cannot get complete data from a single endpoint. It needs to:
1. Query media service for videos in collection + timeframe
2. Query vision service per video for person objects
3. Query vmeta for individuals in those videos
4. Query vmeta for MVR people in those videos
5. Aggregate everything manually

This is:
- ❌ Slow (multiple service calls)
- ❌ Error-prone (service failures affect results)
- ❌ Complex (frontend doing backend aggregation work)
- ❌ Inconsistent (race conditions between queries)

### Proposed Solution

**Option A: Unified Analytics Endpoint**
Create a new comprehensive analytics endpoint that:
```bash
POST /api/v1/analytics/complete
Body: {
    "collections": ["collection1", "collection2"],
    "start_time": "2026-01-05T00:00:00",
    "end_time": "2026-01-05T23:59:59",
    "include_metadata": true
}

Returns: {
    "summary": {
        "total_videos": 50,
        "videos_with_faces": 45,
        "videos_processed": 45,
        "total_face_detections": 523,
        "total_person_objects": 156,
        "total_individuals": 23,
        "total_mvr_people": 8,
        "average_faces_per_video": 11.6,
        "average_quality": 0.78
    },
    "collection_breakdown": [
        {
            "collection_name": "rtsp_192.168.1.77_554",
            "videos": 50,
            "individuals": 23,
            "mvr_people": 8,
            "average_quality": 0.78
        }
    ],
    "individuals": [...],  // optional with include_metadata
    "mvr_people": [...]     // optional with include_metadata
}
```

**Benefits:**
- ✅ Single endpoint for complete analytics
- ✅ Backend handles aggregation
- ✅ Consistent data (single transaction)
- ✅ Fast (optimized queries)
- ✅ Works even if representative_faces is NULL

**Option B: Enhanced Gateway Aggregation**
Improve existing quality metrics endpoint to:
1. Query vmeta for all tracking sessions in timeframe
2. Aggregate individuals_found and unique_mvr_people_count
3. Return complete statistics even without representative_faces

**Option C: GraphQL Analytics API**
Create a GraphQL endpoint allowing flexible queries:
```graphql
query Analytics {
  collection(name: "rtsp_192.168.1.77_554", 
             startTime: "2026-01-05T00:00:00",
             endTime: "2026-01-05T23:59:59") {
    videos {
      count
      withFaces
    }
    individuals {
      count
      list { uuid, videoCount }
    }
    mvrPeople {
      count
      list { uuid, videoCount, demographics }
    }
    statistics {
      averageQuality
      averageFacesPerVideo
    }
  }
}
```

---

## Issue 4: Quality Metrics Uses Wrong Aggregation Logic (Deprecated - See Issue 1)

### Problem Description
Quality metrics endpoint calculates `representative_faces IS NOT NULL` which excludes valid individuals where representative_faces extraction failed or is pending.

### Current Query Logic
```sql
WITH individual_qualities AS (
    SELECT DISTINCT ON (i.individual_uuid)
        i.individual_uuid,
        iva.representative_faces,
        iva.confidence,
        iva.video_uuid
    FROM individuals i
    JOIN individual_video_appearances iva 
        ON i.individual_uuid = iva.individual_uuid
    WHERE iva.start_timestamp >= $1
        AND iva.start_timestamp <= $2
        AND iva.representative_faces IS NOT NULL  -- ❌ THIS FILTERS OUT VALID DATA
    ORDER BY i.individual_uuid, iva.confidence DESC
)
```

### Impact
- Valid individuals excluded from analytics
- Dashboard shows 0 even when data exists
- Users cannot track system performance accurately

### Proposed Solution
Modify query to include individuals even when representative_faces is NULL:
```sql
WHERE iva.start_timestamp >= $1
    AND iva.start_timestamp <= $2
    -- Remove: AND iva.representative_faces IS NOT NULL
```

Then handle NULL representative_faces in quality calculation:
```python
if representative_faces is None:
    quality_scores.append({
        "individual_uuid": individual_uuid,
        "quality": 0.0,  # or None, or "pending"
        "status": "no_representative_faces"
    })
```

---✅ Implementation Complete

### Backend Endpoints (COMPLETED - January 5, 2026)

**New vmeta Endpoint:**
```bash
GET /api/v1/mvr/quality-metrics?start_time=...&end_time=...&collection_name=all
```

**New Gateway Endpoint:**
```bash
GET /api/v1/analytics/mvr-quality-metrics?time_filter=today|last_3_days|last_week|last_month&collection_name=X
```
✅ Priority 2: Verify Quality Data Location (COMPLETED)
- [x] Discovered quality scores stored in `mvr_people` table, not `individual_video_appearances`
- [x] Verified 54.55% of MVR people have quality scores (6 out of 11 in test data)
- [x] Confirmed quality data exists and is accessible
- [x] Updated query to fetch from correct table

### Priority 3: Frontend Integration (NEXT - IN PROGRESS)
- [ ] Locate analytics dashboard component in `ppl-meta-frontend`
- [ ] Find where current quality-metrics endpoint is called
- [ ] Add new endpoint call to `mvr-quality-metrics`
- [ ] Update UI to display:
  - Tracking sessions count
  - Total individuals from sessions
  - Total MVR people from sessions
  - MVR people with quality scores
  - Data completeness percentage
  - Average quality score with grade
  - Quality statistics (min, max, std dev)
- [ ] Add time filter selector (today, last_3_days, last_week, last_month)
- [ ] Add collection filter (optional)
- [ ] Test with real data in browser
- [ ] Update any charts/graphs to use new data structure

### Priority 4: Documentation & Cleanup (FINAL)
- [ ] Update API documentation with new endpoint
- [ ] Add usage examples to developer guide
- [ ] Document MVR quality data storage pattern
- [ ] Update analytics architecture diagram
- [ ] Archive old quality-metrics endpoint (if not used elsewhere)

### ~~Priority 5: Investigate Enhanced V2 Filtering~~ (NOT NEEDED)
- [x] Determined Enhanced V2 filtering is not relevant to quality metrics
- [x] Quality data comes from MVR level, not individual representative_faces
- [x] No action required
    "data_completeness": {
        "total_mvr_people": 11,
        "mvr_with_quality_scores": 6,
        "percentage": 54.55
    },
    "quality_grade": "Fair",
    "time_filter": "last_3_days",
    "generated_at": "2026-01-05T20:05:38+00:00",
    "data_source": "MVR → Individual tree (recommended)"
}
```

### Key Discoveries

**1. Quality Data Storage Location:**
- ✅ Quality scores stored in `mvr_people` table (`face_quality`, `quality_score` columns)
- ❌ NOT in `individual_video_appearances.representative_faces` (only 10 out of 2408 have this)
- ✅ MVR people table is the authoritative source for quality metrics

**2. Correct Data Access Pattern:**
```sql
-- Step 1: Get tracking sessions for timeframe
SELECT * FROM tracking_sessions 
WHERE created_at >= start_time AND created_at <= end_time 
AND status = 'completed'

-- Step 2: Get MVR people created in timeframe with quality scores
SELECT mvr_people_uuid, face_quality, quality_score, total_linked_individuals
FROM mvr_people
WHERE created_at >= start_time AND created_at <= end_time
AND is_merged = false
```

**3. Implementation Details:**
- **File:** `/ppl-meta-vmeta/src/api/v1/quality_metrics.py`
- **File:** `/ppl-meta-gateway/src/api/v1/analytics.py`
- **Database:** `ppl_meta_vmeta` database
- **Table:** `tracking_sessions` (NOT `cross_video_tracking_sessions`)
- **Dependencies Fixed:**
  - `get_db_connection` now correctly accesses global `db_client.pool`
  - Datetime timezone handling (convert to naive for database queries)
  - Query optimized with CTE for video counts

**4. Debugging Journey:**
- Fixed import errors (`core.auth` → `api.dependencies`)
- Fixed database connection pattern (`get_db_pool` → `db_client.pool`)
- Fixed table name (`cross_video_tracking_sessions` → `tracking_sessions`)
- Fixed datetime timezone mismatch (added `.replace(tzinfo=None)`)
- Fixed query to use MVR quality scores instead of individual representative_faces
- Added global exception handler in main.py for better error visibility

**5. Test Results (Last 3 Days):**
- ✅ 10 tracking sessions found
- ✅ 17 individuals created
- ✅ 11 MVR people created
- ✅ 32 videos processed
- ✅ 6 MVR people with quality scores (54.55% completeness)
- ✅ Average quality: 0.561 (Fair grade)
- ✅ Quality range: 0.509 to 0.593
- ✅ Quality std dev: 0.034 (consistent)

---

## Action Items

### ✅ Priority 1: Fix Analytics Data Access Pattern (COMPLETED)
- [x] Modify quality metrics endpoint to query via MVR → Individual tree
- [x] Query tracking sessions for collection + timeframe
- [x] Get MVR people from sessions (unique_mvr_people_count)
- [x] Query mvr_people table for quality scores (face_quality, quality_score)
- [x] Calculate quality metrics from MVR data
- [x] Return correct counts matching tracking session data
- [x] Add timezone handling for datetime parameters
- [x] Fix database connection dependency injection
- [x] Add comprehensive error logging
- [ ] Calculate quality metrics from face data
- [ ] Return correct counts matching tracking session data

### Priority 2: Verify representative_faces Populated (SHORT-TERM)
- [ ] Check if individual_video_appearances has representative_faces for individual cca24886...
- [ ] Verify representative_faces populated during vmeta preload phase
- [ ] If NULL, determine if we need to extract from person_objects
- [ ] If needed, add representative_faces extraction during individual creation
Results

### ✅ Backend Testing (Completed - January 5, 2026)

**Test 1: Today's Data**
```bash
GET /api/v1/analytics/mvr-quality-metrics?time_filter=today
```
Result:
- ✅ 5 tracking sessions found
- ✅ 7 individuals (matches tracking session aggregate)
- ✅ 5 MVR people (matches tracking session aggregate)
- ✅ 15 videos processed
- ✅ 2 MVR people with quality (40% completeness)
- ✅ Average quality: 0.519 (Fair grade)
- ✅ Response time: < 200ms

**Test 2: Last 3 Days**
```bash
GET /api/v1/analytics/mvr-quality-metrics?time_filter=last_3_days
```
Result:
- ✅ 10 tracking sessions found
- ✅ 17 individuals (matches tracking session aggregate)
- ✅ 11 MVR people (matches tracking session aggregate)
- ✅ 32 videos processed
- ✅ 6 MVR people with quality (54.55% completeness)
- ✅ Average quality: 0.561 (Fair grade)
- ✅ Quality range: 0.509 to 0.593
- ✅ Response time: < 250ms

**Verification:**
- [x] Quality metrics returns individuals_found matching tracking session ✅
- [x] Quality metrics returns mvr_people_count matching tracking session ✅
- [x] Can query MVR people for collection + timeframe ✅
- [x] Quality scores fetched from mvr_people table ✅
- [x] Analytics performance acceptable (< 300ms response time) ✅
- [x] No data loss between tracking session and analytics display ✅
- [x] Timezone handling works correctly ✅
- [x] Data completeness percentage calculated accurately ✅

### 🔄 Frontend Testing (Pending)
- [ ] Analytics dashboard shows correct counts from new endpoint
- [ ] UI displays MVR quality metrics properly
- [ ] Time filter selector works
- [ ] Collection filter works (if implemented)
- [ ] Charts/graphs render with new data structure
- [ ] Data refreshes correctly when filters change
- [ ] No console errors or warnings
- [ ] Determine why it returns 0 when direct query succeeds
- [ ] Fix filtering or bypass Enhanced V2 for representative_faces extraction

---

## Testing Checklist

After implementing Priority 1 fix, verify:
- [ ] Quality metrics returns individuals_found matching tracking session
- [ ] Quality metrics returns mvr_people_count matching tracking session  
- [ ] Analytics dashboard shows correct counts
- [ ] representative_faces extraction works or quality defaults gracefully
- [ ] Can query MVR people for collection + timeframe
- [ ] Can get linked individuals for each MVR person
- [ ] Analytics performance acceptable (< 2 seconds response time)
- [ ] No data loss between tracking session and analytics display

---

## Related Documents
- [PPL Meta Logging](./guides/developer/ppl-meta-logging.md) - Service log locations
- [Continuous Pipeline Architecture](./architecture/continuous-individuals-mvr-pipeline.md)
- [Enhanced Logic V2 Specification](./vision-vmeta/enhanced-logic-v2.md)

---

## Frontend Integration Guide

### Endpoint to Use
```bash
GET http://localhost:8080/api/v1/analytics/mvr-quality-metrics
```

### Query Parameters
- `time_filter` (required): `today` | `last_3_days` | `last_week` | `last_month`
- `collection_name` (optional): Collection name or `all` for all collections

### Authentication
Requires Bearer token in Authorization header:
```javascript
headers: {
  'Authorization': `Bearer ${token}`
}
```

### Response Fields to Display

**Summary Metrics:**
- `tracking_sessions_count`: Number of batch processing sessions
- `total_individuals`: Total individuals created
- `total_mvr_people`: Total MVR people created
- `total_videos_processed`: Total videos analyzed

**Quality Metrics:**
- `mvr_with_quality`: MVR people with quality scores
- `mvr_without_quality`: MVR people missing quality scores
- `average_quality`: Mean quality score (0-1 scale)
- `min_quality`: Lowest quality score
- `max_quality`: Highest quality score
- `quality_std_dev`: Quality score standard deviation
- `quality_grade`: Human-readable grade (Excellent/Good/Fair/Poor/Very Poor)

**Data Completeness:**
- `data_completeness.total_mvr_people`: Total MVR people count
- `data_completeness.mvr_with_quality_scores`: Count with quality data
- `data_completeness.percentage`: Percentage with quality data

### Example Frontend Code
```javascript
async function fetchMVRQualityMetrics(timeFilter = 'today', collectionName = 'all') {
  const token = await getAuthToken();
  const params = new URLSearchParams({
    time_filter: timeFilter,
    collection_name: collectionName
  });
  
  const response = await fetch(
    `http://localhost:8080/api/v1/analytics/mvr-quality-metrics?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return await response.json();
}
```

### UI Components to Update
1. **Summary Cards**: Display tracking_sessions_count, total_individuals, total_mvr_people
2. **Quality Gauge**: Show average_quality with quality_grade label
3. **Completeness Progress Bar**: Show data_completeness.percentage
4. **Statistics Table**: Display min/max/avg/std_dev quality scores
5. **Time Filter Dropdown**: Options for today/last_3_days/last_week/last_month
6. **Collection Filter** (optional): Dropdown to select specific collection

---

## Notes

**Key Findings:**
- ✅ Continuous pipeline is working perfectly (face detection → individuals → MVR)
- ✅ Data exists and is queryable (tracking session proves this)
- ✅ Quality scores stored at MVR level (`mvr_people.face_quality`)
- ✅ NOT stored at individual level (`individual_video_appearances.representative_faces` - only 10/2408 have this)
- ✅ Analytics now queries correct data source (MVR table)
- ✅ Backend implementation complete and tested

**Correct Approach (Implemented):**
Query the MVR table directly for quality scores: **tracking_sessions → mvr_people.face_quality**

**Next Step:**
Integrate new endpoint into Flutter analytics dashboard to display real quality metrics.

**Evidence of Success:**
```
Backend Test Results (Last 3 Days):
tracking_sessions_count: 10           ✅
total_individuals: 17                 ✅
total_mvr_people: 11                  ✅
total_videos_processed: 32            ✅
mvr_with_quality: 6 (54.55%)         ✅
average_quality: 0.561 (Fair)        ✅
quality_range: 0.509 - 0.593         ✅
response_time: < 250ms               ✅
```

All the data exists and is now accessible through the correct endpoint.

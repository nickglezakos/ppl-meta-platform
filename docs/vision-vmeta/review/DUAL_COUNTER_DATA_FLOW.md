# Dual Counter Data Flow - Technical Documentation

**Date:** November 1, 2025  
**Feature:** Original vs Unique Individual Counters  
**Status:** In Progress

---

## Overview

This document explains exactly where each counter gets its data from, which API endpoints are involved, and what the data flow looks like.

---

## Current State Analysis

### Flutter UI Display

**Location:** `ppl-meta-frontend/lib/screens/collections_screen.dart`

**Lines 455-475, 535, 647** - Three places showing:
```dart
Text('${_individualsCount ?? 0} → ${_uniqueMvrCount ?? _individualsCount ?? 0} unique')
```

**Format:** `X → Y unique` where:
- `X` = Original detections (before MVR merging)
- `Y` = Unique individuals (after MVR merging)

---

## Data Flow: Counter 1 (Original Count)

### Step 1: Flutter Initiates Tracking Session

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`  
**Function:** `_fetchIndividualsCount()`  
**Line:** ~895

```dart
final createResponse = await mediaApiClient.createCrossVideoTrackingSession(
  collections: [_selectedCollection!.id],
  startTime: _startDate!.toIso8601String(),
  endTime: _endDate!.toIso8601String(),
);
```

**API Call:**
- Method: `POST`
- Endpoint: `http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions`
- Body:
```json
{
  "collections": ["usb_camera_0"],
  "start_time": "2025-11-01T10:00:00Z",
  "end_time": "2025-11-01T12:00:00Z",
  "background_processing": true
}
```

**Response:**
```json
{
  "session_uuid": "abc-123-def-456",
  "status": "running",
  "message": "Tracking session created",
  "cache_hit_rate": 0.0,
  "total_videos": 2
}
```

---

### Step 2: Backend Creates Session

**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Function:** `create_tracking_session()`  
**Line:** ~85

**Database Insert:**
```python
await conn.execute("""
    INSERT INTO tracking_sessions (
        session_uuid, user_id, collections, start_time, end_time,
        status, config_hash, total_videos, processed_videos,
        individuals_found, cache_hits
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
""", session_uuid, "system_user", request.collections,
     start_time_naive, end_time_naive, "running", config_hash,
     total_videos, 0, 0, 0)
```

**Initial Values:**
- `individuals_found` = 0 (not processed yet)
- `unique_mvr_people_count` = **NOT SET** (column doesn't exist in original version)

---

### Step 3: Backend Processes Videos (Background Task)

**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Function:** `process_tracking_session()`  
**Line:** ~450

**Cross-Video Tracking Algorithm:**
1. Discovers videos in time range
2. For each video, fetches person objects
3. Groups person objects into "individuals" using:
   - Temporal proximity (same time window)
   - Spatial proximity (same location)
   - Face embedding similarity

**Creates Individual Records:**
```python
# For each unique individual found
individual_uuid = uuid.uuid4()
await conn.execute("""
    INSERT INTO individuals (
        individual_uuid, individual_id, confidence_score,
        first_seen, last_seen, total_appearances,
        created_by_session
    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
""", individual_uuid, individual_id, confidence,
     first_seen, last_seen, appearance_count, session_uuid)

# Track count
individuals_found += 1
```

**Updates Session:**
```python
await conn.execute("""
    UPDATE tracking_sessions 
    SET status = 'completed', 
        completed_at = NOW(),
        processed_videos = $2, 
        individuals_found = $3
    WHERE session_uuid = $1
""", session_uuid, processed_count, individuals_found)
```

**Result:** `individuals_found` = 1 (in your test case)

---

### Step 4: Flutter Polls for Status

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`  
**Function:** `_pollTrackingSessionStatus()`  
**Line:** ~954

**API Call (every 1 second):**
- Method: `GET`
- Endpoint: `http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions/{uuid}`

**Backend Handler:**

**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
**Function:** `get_session_status()`  
**Line:** ~219

**Database Query:**
```python
result = await conn.fetchrow("""
    SELECT session_uuid, status, collections, created_at, 
           started_at, completed_at, total_videos, processed_videos,
           individuals_found, cache_hits
    FROM tracking_sessions 
    WHERE session_uuid = $1
""", session_uuid)
```

**IMPORTANT:** This query does **NOT** include `unique_mvr_people_count` column!

**Response (Original Backend):**
```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "collections": ["usb_camera_0"],
  "created_at": "2025-11-01T11:00:00Z",
  "started_at": "2025-11-01T11:00:01Z",
  "completed_at": "2025-11-01T11:00:05Z",
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,        ← REAL DATA from database
  "cache_hits": 0
}
```

**Note:** NO `unique_mvr_people_count` field in response!

---

### Step 5: Flutter Extracts Counter 1

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`  
**Line:** ~967

```dart
final individualsFound = statusResponse.data!['individuals_found'] as int? ?? 0;
```

**Result:** `_individualsCount = 1` ✅ **REAL DATA from database**

---

## Data Flow: Counter 2 (Unique Count)

### Current Implementation (Original Backend)

**Flutter Code:**  
**Line:** ~968

```dart
final uniqueMvrCount = statusResponse.data!['unique_mvr_people_count'] as int? ?? individualsFound;
```

**What happens:**
1. Tries to read `unique_mvr_people_count` from API response
2. **Field doesn't exist** in original backend response
3. Falls back to `?? individualsFound`
4. `_uniqueMvrCount = 1` (same as `_individualsCount`)

**Result:** `_uniqueMvrCount = 1` ⚠️ **FALLBACK DATA (copy of individuals_found), NOT real unique count**

---

### Display Result

**Flutter UI shows:** `1 → 1 unique`

**Breakdown:**
- `1` (first counter) = `individuals_found` from database ✅ REAL
- `→` (arrow separator)
- `1` (second counter) = Fallback to `individuals_found` ⚠️ NOT UNIQUE DATA

**This is misleading!** Both counters show the same value because:
- Backend doesn't calculate unique count
- Backend doesn't return `unique_mvr_people_count` field
- Flutter uses fallback logic

---

## Planned Implementation (With Unique Counter)

### Backend Changes Needed

**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`

#### Change 1: Add Auto-Matching Logic

**Location:** `process_tracking_session()` function, after `individuals_found` is calculated

```python
# After cross-video tracking creates individuals
individuals_found = 15  # Example: found 15 individuals

# STEP 1: Initialize unique count (default: no merging)
unique_mvr_people_count = individuals_found

# STEP 2: Auto-match duplicates via MVR-People
if individuals_found > 1:
    from services.mvr_matcher import MVRMatcher
    from database.mvr_repository import MVRRepository
    
    mvr_repository = MVRRepository(db_client.pool)
    mvr_matcher = MVRMatcher(mvr_repository)
    
    merge_count = 0
    merged_individuals = set()
    
    # For each individual
    for individual_uuid in created_individuals:
        if individual_uuid in merged_individuals:
            continue
        
        # Find similar individuals (face similarity > 0.85)
        matches = await mvr_matcher.find_matching_mvr(
            individual_uuid=individual_uuid,
            threshold=0.85
        )
        
        # Merge duplicates
        for match in matches:
            if match['similarity_score'] >= 0.85:
                merge_result = await mvr_matcher.merge_individuals(
                    individual_a_uuid=individual_uuid,
                    individual_b_uuid=match['individual_uuid'],
                    similarity_score=match['similarity_score']
                )
                if merge_result['success']:
                    merged_individuals.add(match['individual_uuid'])
                    merge_count += 1
    
    # STEP 3: Calculate unique count
    unique_mvr_people_count = individuals_found - merge_count
    
    logger.info(
        f"Auto-matching: {individuals_found} individuals → "
        f"{unique_mvr_people_count} unique (merged {merge_count} duplicates)"
    )
```

**Result:**
- `individuals_found = 15` (original detections)
- `merge_count = 3` (duplicates merged)
- `unique_mvr_people_count = 12` (actual unique people)

---

#### Change 2: Update Database

**Location:** `process_tracking_session()` function

```python
await conn.execute("""
    UPDATE tracking_sessions 
    SET status = 'completed', 
        completed_at = NOW(),
        processed_videos = $2, 
        individuals_found = $3,
        unique_mvr_people_count = $4      ← NEW FIELD
    WHERE session_uuid = $1
""", session_uuid, processed_count, individuals_found, unique_mvr_people_count)
```

---

#### Change 3: Return Unique Count in API

**Location:** `get_session_status()` function

**Old Query:**
```python
result = await conn.fetchrow("""
    SELECT session_uuid, status, collections, created_at, 
           started_at, completed_at, total_videos, processed_videos,
           individuals_found, cache_hits
    FROM tracking_sessions 
    WHERE session_uuid = $1
""", session_uuid)

return {
    "session_uuid": str(result["session_uuid"]),
    "status": result["status"],
    # ... other fields
    "individuals_found": result["individuals_found"],
    "cache_hits": result["cache_hits"]
}
```

**New Implementation:**
```python
result = await conn.fetchrow("""
    SELECT session_uuid, status, collections, created_at, 
           started_at, completed_at, total_videos, processed_videos,
           individuals_found, cache_hits
    FROM tracking_sessions 
    WHERE session_uuid = $1
""", session_uuid)

response = {
    "session_uuid": str(result["session_uuid"]),
    "status": result["status"],
    # ... other fields
    "individuals_found": result["individuals_found"],
    "cache_hits": result["cache_hits"]
}

# Try to add unique count (backward compatible)
try:
    unique_count = await conn.fetchval("""
        SELECT unique_mvr_people_count
        FROM tracking_sessions 
        WHERE session_uuid = $1
    """, session_uuid)
    
    if unique_count is not None and unique_count > 0:
        response["unique_mvr_people_count"] = unique_count
    else:
        response["unique_mvr_people_count"] = result["individuals_found"]
except Exception:
    # Column doesn't exist (old database), use individuals_found
    response["unique_mvr_people_count"] = result["individuals_found"]

return response
```

**New Response:**
```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "individuals_found": 15,                ← Original count
  "unique_mvr_people_count": 12,          ← Unique count (NEW!)
  "cache_hits": 0
}
```

---

### Flutter (No Changes Needed)

**Current Code Already Handles This:**

```dart
final individualsFound = statusResponse.data!['individuals_found'] as int? ?? 0;
final uniqueMvrCount = statusResponse.data!['unique_mvr_people_count'] as int? ?? individualsFound;

setState(() {
  _individualsCount = individualsFound;      // 15
  _uniqueMvrCount = uniqueMvrCount;          // 12
});
```

**Display:** `15 → 12 unique`

---

## Data Source Summary

### Current Implementation (Original Backend)

| Counter | Display Name | Data Source | API Field | Real Data? |
|---------|-------------|-------------|-----------|------------|
| Counter 1 | Original detections | Database `individuals_found` column | `individuals_found` | ✅ YES |
| Counter 2 | Unique individuals | **Fallback to Counter 1** | `unique_mvr_people_count` (missing) | ❌ NO - Uses fallback |

**Result:** Both counters show same value (no comparison possible)

---

### Planned Implementation (With Unique Counter)

| Counter | Display Name | Data Source | API Field | Real Data? |
|---------|-------------|-------------|-----------|------------|
| Counter 1 | Original detections | Database `individuals_found` column | `individuals_found` | ✅ YES |
| Counter 2 | Unique individuals | Database `unique_mvr_people_count` column | `unique_mvr_people_count` | ✅ YES |

**Result:** Counters show different values when duplicates are merged

---

## API Endpoints Reference

### 1. Create Tracking Session

**Endpoint:** `POST /api/v1/cross-video/individuals/tracking/sessions`

**Request:**
```json
{
  "collections": ["collection_id"],
  "start_time": "2025-11-01T10:00:00Z",
  "end_time": "2025-11-01T12:00:00Z",
  "background_processing": true
}
```

**Response:**
```json
{
  "session_uuid": "abc-123",
  "status": "running",
  "message": "Tracking session created",
  "cache_hit_rate": 0.0,
  "total_videos": 2
}
```

**Data Source:** Creates new record in `tracking_sessions` table

---

### 2. Get Session Status

**Endpoint:** `GET /api/v1/cross-video/individuals/tracking/sessions/{uuid}`

**Response (Original Backend):**
```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "collections": ["usb_camera_0"],
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,        ← ONLY Counter 1
  "cache_hits": 0
}
```

**Response (With Unique Counter):**
```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "collections": ["usb_camera_0"],
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 15,              ← Counter 1
  "unique_mvr_people_count": 12,        ← Counter 2 (NEW!)
  "cache_hits": 0
}
```

**Data Source:** 
- Direct query from `tracking_sessions` table
- Both `individuals_found` and `unique_mvr_people_count` columns

---

### 3. Get Session Individuals

**Endpoint:** `GET /api/v1/cross-video/individuals/tracking/sessions/{uuid}/individuals`

**Response:**
```json
{
  "session_uuid": "abc-123",
  "total_individuals": 15,              ← Counter 1
  "unique_mvr_people_count": 12,        ← Counter 2
  "individuals": [
    {
      "individual_uuid": "uuid-1",
      "individual_id": "IND-001",
      "total_appearances": 3,
      "total_videos": 2,
      "confidence_score": 0.92
    }
    // ... more individuals
  ]
}
```

**Data Source:**
- `individuals` table join with `individual_video_appearances`
- Session metadata from `tracking_sessions` table

---

## Database Schema

### tracking_sessions Table

**Current Schema (Original):**
```sql
CREATE TABLE tracking_sessions (
    session_uuid UUID PRIMARY KEY,
    user_id VARCHAR(255),
    collections TEXT[],
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),
    config_hash VARCHAR(64),
    total_videos INTEGER DEFAULT 0,
    processed_videos INTEGER DEFAULT 0,
    individuals_found INTEGER DEFAULT 0,    ← Counter 1 ONLY
    cache_hits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_seconds REAL
);
```

**With Unique Counter (Migration 003):**
```sql
-- Add new column
ALTER TABLE tracking_sessions 
ADD COLUMN IF NOT EXISTS unique_mvr_people_count INTEGER DEFAULT 0;

-- Add indexes for performance
CREATE INDEX idx_tracking_sessions_unique_mvr_count 
ON tracking_sessions(unique_mvr_people_count) 
WHERE unique_mvr_people_count > 0;

-- Backfill existing sessions
UPDATE tracking_sessions
SET unique_mvr_people_count = individuals_found
WHERE status = 'completed' AND unique_mvr_people_count = 0;
```

---

## Verification Steps

### How to Verify Real Data vs Mock Data

**Step 1: Check Flutter Debug Logs**

Look for these lines in Flutter console:
```
DEBUG: Tracking session status: completed
  - individuals_found: 1 (original count)
  - unique_mvr_people_count: 1 (after MVR merging)
```

**Step 2: Check API Response**

Run this in terminal:
```bash
curl -s http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions/{uuid} | python3 -m json.tool
```

Look for:
```json
{
  "individuals_found": 1,           ← Should be present
  "unique_mvr_people_count": 1      ← Check if present or missing
}
```

**Step 3: Check Database Directly**

```sql
SELECT 
    session_uuid, 
    status, 
    individuals_found,           -- Counter 1
    unique_mvr_people_count      -- Counter 2 (may not exist in original schema)
FROM tracking_sessions
WHERE session_uuid = 'your-uuid'
ORDER BY created_at DESC
LIMIT 1;
```

**Step 4: Verify Column Exists**

```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'tracking_sessions' 
  AND column_name = 'unique_mvr_people_count';
```

If returns **0 rows** → Column doesn't exist (original backend)  
If returns **1 row** → Column exists (migration applied)

---

## Current Status Summary

**Backend:** Original version (no unique counter calculation)
- ✅ `individuals_found` is REAL data from cross-video tracking
- ❌ `unique_mvr_people_count` field NOT in API response
- ❌ No auto-matching logic implemented

**Flutter:** Updated to display both counters
- ✅ Shows `X → Y unique` format
- ✅ Counter 1 (`X`) = REAL data from `individuals_found`
- ⚠️ Counter 2 (`Y`) = FALLBACK to Counter 1 (not unique data)

**Result:** You see `1 → 1` where both values are the same because Counter 2 is using fallback logic.

---

**Next Steps:**
1. Confirm Counter 1 (`individuals_found`) is working correctly ✅
2. Apply Step 1 backend changes (add `unique_mvr_people_count` to database UPDATE)
3. Test to ensure Counter 1 still works AND Counter 2 appears in API
4. Apply Step 2 backend changes (add auto-matching logic)
5. Test with data that has duplicates to see different counter values

---

**Author:** PPL Meta Platform Team  
**Last Updated:** November 1, 2025

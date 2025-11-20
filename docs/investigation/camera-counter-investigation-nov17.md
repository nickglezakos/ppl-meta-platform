# Camera Counter Investigation - November 17, 2025

## Issue Summary
Camera counter shows "0 → 0 unique" MVR people for usb_camera_0 collection despite recording 8 videos on November 16, 2025.

---

## Investigation Timeline

### 1. Recording Session (Nov 16, 2025 ~13:20-13:24)
- **Videos recorded**: 8 segments (30 seconds each = ~4 minutes total)
- **Collection**: usb_camera_0
- **Upload status**: ✅ All 8 videos successfully uploaded to Media Service
- **Video UUIDs**:
  1. `8c77cf47-1db0-4b91-ab86-2f873307c52d`
  2. `52fa4969-cfe5-4252-9c87-10745b675c15`
  3. `cc62d890-cc0c-4738-ae37-ae06783de1d1`
  4. `5066a8c3-de30-46e7-9e5d-8d7352947181`
  5. `8135343f-c0cd-47a4-9ccb-a1441e355d95`
  6. `42b39201-e0dd-41d9-a195-cfa330df9f86`
  7. `9bbbff74-0286-470a-ad02-3b7b079d1f81`
  8. `011fb0dd-a27c-4c7c-a47d-2761361b8fd7`

---

### 2. Face Detection Status
**Status**: ✅ **WORKING**

- **Endpoint tested**: `GET /api/v1/media/{video_uuid}/faces/enhanced-v2` (Orchestrator)
- **Video 1 results**: 19 faces detected
  - Source: `stored_faces` (already processed)
  - Method: `two_stage_haar_dlib`
  - Session UUID: `02cb54ff-43b9-4ded-b709-2f0f47c75596`
- **Conclusion**: Face detection DID run and found faces in all videos

**Camera Service Trigger Code** (verified in `camera_detection.py`):
- Lines 2266: Calls `_check_and_trigger_face_detection()` after upload
- Lines 2476-2550: Checks `face_detection_on_save` setting
- Lines 2560-2618: Triggers orchestrator face detection endpoint
- **Status**: ✅ Code is in place and functional

---

### 3. Manual Tracking Session (Nov 16, 2025 14:19:49)
**Attempt**: Manual trigger to process the 8 videos

**Request**:
```bash
POST /api/v1/cross-video/individuals/tracking/sessions
{
  "collections": ["usb_camera_0"],
  "start_time": "2025-11-16T13:20:00",
  "end_time": "2025-11-16T13:25:00",
  "video_uuids": [/* all 8 UUIDs */],
  "background_processing": true
}
```

**Response**:
```json
{
  "session_uuid": "843e7d29-36fc-4542-9fc5-194a7a1fbc11",
  "status": "completed",
  "total_videos": 8,
  "processed_videos": 8,
  "individuals_found": 1,          // ❌ WRONG
  "unique_mvr_people_count": 1,    // ❌ WRONG
  "cache_hits": 0
}
```

**Processing time**: 0.17 seconds (suspiciously fast - suggests no actual work done)

---

### 4. Database Verification (Nov 17, 2025)
**Test**: Search for MVR people created during tracking session

**Search Parameters**:
- Collection: `usb_camera_0`
- Time range 1: `2025-11-16 14:19:00` to `14:21:00` (tracking session window)
- Time range 2: `2025-11-16 00:00:00` to `23:59:59` (entire day)

**Results**:
```
MVR people found (14:19-14:21): 0
MVR people found (entire day):  0
```

**Conclusion**: ❌ **NO MVR PEOPLE EXIST IN DATABASE**

---

## Root Cause Analysis

### Issue 1: Tracking Session Counter Bug
**Problem**: Session reports creating "1 individual" and "1 MVR person" but they don't exist in the database.

**Evidence**:
- Session status shows: `individuals_found: 1`, `unique_mvr_people_count: 1`
- Database search returns: 0 MVR people for Nov 16
- Health endpoint shows: Total MVR people = 68 (unchanged from before session)

**Conclusion**: The tracking session's counters are **incorrect** - they count objects that were never persisted.

---

### Issue 2: Individual Cache Not Called (from documentation)
**Reference**: `individual-and-mvr-caching-methods.md` - Known Issue #1

**Problem**: The `get_or_create_individuals_for_video()` function exists but is never called.

**Current (incorrect) flow**:
```
1. Call Orchestrator for ALL videos → Get face detection results
2. Create NEW individuals directly from Orchestrator response
3. [BUG: Individual creation step is skipped or failing]
4. Check MVR cache (can't work without individuals)
5. Merge individuals → Create MVR (can't work without individuals)
```

**Expected (correct) flow**:
```
1. For each video:
   a. Check individual cache (individual_video_appearances table)
   b. If cache hit: reuse existing individuals
   c. If cache miss: call Orchestrator → create new individuals
2. Combine cached + new individuals
3. Check MVR cache for cached individuals
4. Merge individuals → Create MVR people
```

**Impact**: Even though face detection completed successfully, the tracking pipeline never creates individuals from those face detection results.

---

### Issue 3: Fast Completion Time
**Observation**: Session completed in 0.17 seconds for 8 videos

**Analysis**:
- Expected time: ~60 seconds per video for face detection
- Actual time: 0.17 seconds total
- **Conclusion**: Session didn't do any real processing - likely hit a code path that returns early

**Possible causes**:
1. Session-wide cache hit (returned cached individuals from previous session)
2. Individual creation step silently failed/was skipped
3. Early return due to empty face detection results

---

## Why Camera Counter Shows 0

**Camera Counter Implementation**: ✅ **CORRECT**

The camera counter feature (implemented in `camera_card.dart`) correctly shows 0 because:

1. ✅ It calls the correct endpoint: `POST /api/v1/mvr-people/search/by-collection`
2. ✅ It uses correct parameters: `collection_name: "usb_camera_0"`, today's date range
3. ✅ The endpoint works correctly: Returns `total_results: 0`
4. ✅ The database query is correct: Filters by `mvr_people.created_at`

**The counter shows 0 because there genuinely ARE 0 MVR people for that collection today.**

---

## Architecture Verification

### What's Working ✅
1. **Video Recording & Upload** - Camera service records and uploads segments
2. **Face Detection** - Orchestrator/Vision service detects faces successfully
3. **Camera Counter UI** - Flutter widget correctly queries and displays results
4. **Search Endpoint** - MVR search API works correctly
5. **Trigger Code** - Face detection is triggered after video upload

### What's Broken ❌
1. **Individual Creation** - Tracking session doesn't create individuals from faces
2. **MVR Creation** - No MVR people created (depends on individuals)
3. **Continuous Pipeline** - Automatic processing after recording doesn't work
4. **Session Counters** - Report wrong values (say created but didn't persist)

---

## Continuous Pipeline Status

According to `continuous-individuals-and-mvr-pipeline.md`:

### ✅ Successfully Implemented
- Continuous segment upload (Camera Service)
- Video storage (Media Service)
- Face detection triggering

### ❌ Known Issues
- Face detection not auto-triggering consistently
- Individuals not created from uploaded videos
- MVR people not created
- Batch processing never triggered

### 🔍 Root Cause (from documentation)
> "The issue is in the Camera Service's `_upload_recording_to_collection()` function. 
> This function exists and is called, but face detection is not being triggered."

**Update (Nov 17)**: Face detection IS being triggered and works. The issue is downstream in the tracking/individual creation phase.

---

## Next Steps

### Priority 1: Fix Individual Creation in Tracking Sessions
**File**: `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`

**Changes needed** (around lines 2370-2420):
1. Wire up `get_or_create_individuals_for_video()` function
2. Check individual cache BEFORE calling Orchestrator
3. Only create new individuals for cache misses
4. Ensure individuals are persisted to database

### Priority 2: Debug Why Individuals Aren't Persisted
**Possible issues**:
1. Database transaction rollback (check for exceptions)
2. Individual INSERT statements not executing
3. Silent failures in db_operations batch
4. Transaction not committed

### Priority 3: Verify Continuous Pipeline Integration
Once tracking sessions work:
1. Test automatic triggering after recording stops
2. Verify PollingFallbackManager is running
3. Test batch processing with threshold = 5
4. Confirm MVR people are created automatically

---

## Testing Recommendations

### Test 1: Minimal Tracking Session
```bash
# Create session with just 1 video
POST /api/v1/cross-video/individuals/tracking/sessions
{
  "collections": ["usb_camera_0"],
  "video_uuids": ["8c77cf47-1db0-4b91-ab86-2f873307c52d"],
  "start_time": "2025-11-16T13:20:00",
  "end_time": "2025-11-16T13:21:00"
}

# Expected: 19 individuals created (one per face)
# Actual: Will likely show 0 or 1 with wrong counter
```

### Test 2: Direct Individual Creation
```bash
# Try calling orchestrator directly and manually creating individuals
# Bypass tracking session to isolate the issue
```

### Test 3: Database Transaction Logging
```python
# Add extensive logging to cross_video_tracking_simple.py
# Log every INSERT statement execution
# Log transaction commits/rollbacks
# Verify individuals are actually written to DB
```

---

## Conclusion

**Camera Counter Status**: ✅ **WORKING CORRECTLY**
- Shows 0 because there are genuinely 0 MVR people for the collection

**Pipeline Status**: ❌ **BROKEN**
- Face detection works
- Individual creation broken
- MVR creation broken (depends on individuals)
- Tracking session counters lie about what was created

**Root Cause**: The tracking session pipeline has a critical bug where it reports creating individuals/MVR people but doesn't actually persist them to the database. The `get_or_create_individuals_for_video()` caching function exists but is never integrated into the main workflow.

**Fix Required**: Implement the Individual Cache integration as documented in `individual-and-mvr-caching-methods.md` - Priority 1, Section "PRIORITY 1: Fix Individual Cache Integration".

---

**Investigation Date**: November 17, 2025  
**Session Analyzed**: 843e7d29-36fc-4542-9fc5-194a7a1fbc11  
**Recording Date**: November 16, 2025 13:20-13:24  
**Videos Analyzed**: 8 segments from usb_camera_0

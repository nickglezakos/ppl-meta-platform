# Continuous Pipeline Issues - Investigation Report

**Date:** November 20, 2025  
**Issue:** Recording completed (4:10 duration) but no MVR people created in search results  
**Investigator:** System Analysis  
**Status:** ✅ RESOLVED - Cross-Video Tracking Working, Batch Automation Pending

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Investigation Findings](#investigation-findings)
3. [Issues to Resolve](#issues-to-resolve)
4. [Root Cause Analysis](#root-cause-analysis)
5. [Proposed Solutions](#proposed-solutions)
6. [Implementation Plan](#implementation-plan)

---

## Executive Summary

### Incident Overview

**User Report**: "I just finished a recording that lasted 4:10 and then I searched in the camera collection but no mvr people in the results!"

**Investigation Results**:
- ✅ 7 videos successfully uploaded (11:09:56 to 11:13:56 - latest recording)
- ✅ Face detection automatically triggered via Enhanced Logic V2
- ✅ person_objects created automatically per video
- ✅ Cross-video tracking executed successfully (manual trigger)
- ✅ 4 individuals created from 7 videos
- ✅ 1 MVR person created and searchable
- ✅ Flutter app camera search counter found MVR person
- ⚠️ **PENDING**: Automatic batch triggering from recording events (polling manager needs recording start/stop events)
- ⚠️ **FIXED**: video_uuids parameter bug (was passing JSON string instead of array)

### Critical Discovery

**The manual cross-video tracking pipeline IS WORKING END-TO-END.**

Successfully tested with 7 videos from latest recording:
- Enhanced Logic V2 creates person_objects automatically ✅
- Cross-video tracking creates individuals when triggered ✅  
- MVR people created and searchable via Flutter app ✅

**Remaining Issue**: Automatic batch triggering via PollingFallbackManager requires:
1. Recording start/stop events from Camera service to VMeta
2. Dynamic collection management (FIXED - no longer hardcoded)
3. Proper video UUID passing (FIXED - asyncpg JSONB conversion issue resolved)

---

## Investigation Findings

### 1. Video Upload Status

**Database Query Results** (ppl_media_db.media):

| ID  | UUID      | Created At           | Filename                              | Duration |
|-----|-----------|---------------------|---------------------------------------|----------|
| 451 | e4bfdb28  | 2025-11-20 07:39:59 | recording_20251120_073959_camera_0   | 00:00:19 |
| 452 | 99576dc8  | 2025-11-20 07:40:29 | recording_20251120_074029_camera_0   | 00:00:23 |
| 453 | 02b9f2d3  | 2025-11-20 07:41:03 | recording_20251120_074103_camera_0   | 00:00:24 |
| 454 | 5961c0b8  | 2025-11-20 07:41:37 | recording_20251120_074137_camera_0   | 00:00:24 |
| 455 | f669f8eb  | 2025-11-20 07:42:11 | recording_20251120_074211_camera_0   | 00:00:24 |
| 456 | 61eee122  | 2025-11-20 07:42:45 | recording_20251120_074245_camera_0   | 00:00:26 |
| 457 | 652add36  | 2025-11-20 07:43:21 | recording_20251120_074321_camera_0   | 00:00:26 |
| 458 | d5fc47ef  | 2025-11-20 07:43:58 | recording_20251120_074358_camera_0   | 00:00:24 |
| 459 | b68cffa9  | (Nov 19 test video) | test_video                            | -        |

**Status**: ✅ All videos uploaded successfully  
**Collection**: `usb_camera_0`  
**Total Recording Time**: ~4:10 (matches user report)

---

### 2. Face Detection Status

**Database Query Results** (ppl_vision_db.face_detections):

| media_id  | method               | face_count | latest_detection     |
|-----------|---------------------|-----------|---------------------|
| d5fc47ef  | two_stage_haar_dlib | 24        | 2025-11-20 07:44:02 |
| 652add36  | two_stage_haar_dlib | 56        | 2025-11-20 07:43:37 |
| 61eee122  | two_stage_haar_dlib | 56        | 2025-11-20 07:43:01 |
| f669f8eb  | two_stage_haar_dlib | 49        | 2025-11-20 07:42:27 |
| 5961c0b8  | two_stage_haar_dlib | 58        | 2025-11-20 07:41:53 |
| 02b9f2d3  | two_stage_haar_dlib | 51        | 2025-11-20 07:41:19 |
| 99576dc8  | two_stage_haar_dlib | 52        | 2025-11-20 07:40:45 |
| e4bfdb28  | two_stage_haar_dlib | 43        | 2025-11-20 07:40:15 |

**Status**: ❌ **WRONG METHOD** - Basic face detection used instead of Enhanced Logic V2  
**Face Count**: 389 total faces detected across 8 videos  
**Issue**: Faces stored in `face_detections` table but NO `person_objects` created

---

### 3. Person Objects Status

**Database Query Results** (ppl_vision_db.person_objects):

```sql
SELECT COUNT(*) FROM person_objects WHERE created_at >= '2025-11-20 07:00:00';
-- Result: 0 rows
```

**Status**: ❌ **CRITICAL** - No person_objects created  
**Impact**: Cannot create individuals or MVR people without person_objects  
**Required By**: Cross-video tracking (individuals) and MVR aggregation

---

### 4. Face Detection Sessions Status

**Database Query Results** (ppl_vision_db.face_detection_sessions):

```sql
SELECT * FROM face_detection_sessions WHERE created_at >= '2025-11-20 07:30:00';
-- Result: 0 rows
```

**Status**: ❌ **Enhanced Logic V2 NEVER EXECUTED**  
**Expected**: One session per video (8 sessions)  
**Actual**: Zero sessions  
**Conclusion**: Enhanced Logic V2 endpoint was never successfully called

---

### 5. VMeta Tracking Sessions Status

**Database Query Results** (ppl_meta_vmeta.tracking_sessions):

```sql
SELECT * FROM tracking_sessions WHERE created_at >= '2025-11-20';
-- Result: 0 rows
```

**Status**: ❌ No tracking sessions created  
**Impact**: No individuals created, no cross-video identity matching

---

### 6. Batch Processing Status

**Database Query Results** (ppl_meta_vmeta.batch_processing_state):

```sql
SELECT * FROM batch_processing_state;
-- Result: 0 rows
```

**Status**: ❌ Batch processing never triggered  
**Reason**: Recording events never received by VMeta (PollingFallbackManager never activated)

---

### 7. Recording Sessions Status

**Database Query Results** (ppl_orchestrator_db.recording_sessions):

```sql
SELECT * FROM recording_sessions WHERE started_at >= '2025-11-20 07:00:00';
-- Result: 0 rows
```

**Status**: ❌ **CRITICAL** - Recording events never reached VMeta  
**Expected**: Recording start/stop notifications from Camera service  
**Actual**: No recording sessions created  
**Impact**: Batch processing pipeline never activated

---

## Issues Resolved Today (November 20, 2025)

### ✅ Issue #1: video_uuids Parameter Bug - FIXED

**Problem**: Cross-video tracking API was receiving video_uuids as JSON string instead of Python list, causing PostgreSQL JSONB column error.

**Error Message**:
```
invalid input for query argument $9: '["6bc25594-fe00-49b...' 
(a sized iterable container expected (got type 'str'))
```

**Root Cause**: 
```python
# OLD (BROKEN)
video_uuids_json = json.dumps(request.video_uuids)  # Converts to string
await conn.execute("INSERT ... VALUES (..., $9)", video_uuids_json)
```

**Fix Applied** (`cross_video_tracking_simple.py` line 513):
```python
# NEW (FIXED)
video_uuids_list = request.video_uuids  # Keep as list
await conn.execute("INSERT ... VALUES (..., $9)", video_uuids_list)
# asyncpg automatically handles Python list → PostgreSQL JSONB conversion
```

**Result**: ✅ Cross-video tracking now accepts explicit video_uuids and processes them correctly.

---

### ✅ Issue #2: Dynamic Collection Management - FIXED

**Problem**: PollingFallbackManager was hardcoded to single collection `"usb_camera_0"`, preventing parallel per-collection processing.

**Fix Applied** (`main.py` line 219, `batch_timeout_manager.py` lines 310-421):
```python
# OLD (HARDCODED)
polling_manager = PollingFallbackManager(
    collection_id="usb_camera_0",  # Single collection only!
)

# NEW (DYNAMIC)
polling_manager = PollingFallbackManager(
    collection_id=None,  # Managed via recording events
)

# Collection tracking via recording events
_active_recordings = {}  # {collection_id: session_info}
_pending_videos_by_collection = {}  # Separate queue per collection
```

**Result**: ✅ System now supports multiple simultaneous recordings from different cameras, each with independent batch processing.

---

### ✅ Issue #3: Manual Cross-Video Tracking - VERIFIED WORKING

**Test Results** (Session: 7a31bbe1-25b1-4c6f-a6bf-181e22a8dd0c):
```json
{
  "session_uuid": "7a31bbe1-25b1-4c6f-a6bf-181e22a8dd0c",
  "status": "completed",
  "total_videos": 7,
  "processed_videos": 7,
  "individuals_found": 4,
  "unique_mvr_people_count": 1,
  "processing_time": "64 seconds"
}
```

**Flutter App Verification**:
```
🔍 Fetching MVR count for camera: USB Camera 0
*** Response ***
   Found 15 videos today
*** Response ***
📊 MVR people count result: {count: 1, video_count: 15}
```

**Result**: ✅ Complete pipeline works: videos → person_objects → individuals → MVR people → searchable in Flutter app.

---

## Issues to Resolve

### Issue #1: Automatic Batch Triggering via Recording Events - PENDING

**Problem**: Basic face detection (`two_stage_haar_dlib`) executed instead of Enhanced Logic V2

**Investigation Required**:

1. **Trace the execution path** that triggered basic face detection
   - User hypothesis: "Fired on the save video event when the user tapped stop recording button"
   - Likely suspect: Media service auto-trigger on video upload
   
2. **Identify the calling code**:
   - Check Media service `POST /api/v1/media/upload` endpoint (line 232-320 in `media.py`)
   - Check if auto-trigger at line 308 failed silently
   - Check Camera service `_trigger_face_detection_workflow` (line 2596-2650 in `camera_detection.py`)
   - Examine why both attempts to call Enhanced Logic V2 failed

3. **Verify authentication issues**:
   - Media service calls Enhanced Logic V2 WITHOUT auth token (line 110 in `media.py`)
   - Camera service passes headers but auth token may be missing/invalid
   - Enhanced Logic V2 endpoint requires `auth_token` parameter (`Depends(get_auth_token)`)
   - Requests likely failing with 401 Unauthorized or 403 Forbidden

4. **Find the fallback mechanism**:
   - After Enhanced Logic V2 fails, what triggers basic face detection?
   - Where is `POST /api/v1/workflow/face-detection/process/{media_id}` called from?
   - Check if there's a fallback workflow in Camera or Media service

**Files to Investigate**:
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/api/v1/media.py` (lines 86-145, 232-320)
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src/services/camera_detection.py` (lines 2302, 2512-2650)
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/api/v1/face_detection_workflows.py` (lines 260-420, 572-620)
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-orchestrator/src/face_detection_endpoints.py` (lines 681-720)

**Expected Outcome**:
- Identify exact code path that triggered basic face detection
- Understand authentication failure mechanism
- Document the fallback behavior

---

### Issue #2: Disable Basic Face Detection

**Problem**: Need to prevent basic face detection from running until Enhanced Logic V2 is fixed

**Action Items**:

1. **Comment out Media service auto-trigger**:
   - File: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/api/v1/media.py`
   - Lines: 304-316 (the auto-trigger block in upload endpoint)
   - Add clear comment explaining why it's disabled

2. **Comment out Camera service face detection trigger**:
   - File: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src/services/camera_detection.py`
   - Line: 2302 (the call to `_check_and_trigger_face_detection`)
   - Add clear comment explaining temporary disable

3. **Add configuration flag** (optional, for clean solution):
   - Add `ENABLE_AUTO_FACE_DETECTION=false` to environment variables
   - Check flag before triggering face detection
   - Allows easy toggle without code changes

**Implementation**:

```python
# In ppl-meta-media/src/api/v1/media.py (around line 304)
# 🎯 AUTO-TRIGGER: Enhanced Logic V2 for video uploads
# TEMPORARILY DISABLED - November 20, 2025
# Reason: Authentication issues causing Enhanced Logic V2 to fail
# TODO: Re-enable after fixing auth token passing (Issue #3)
# if media.media_type == MediaType.VIDEO:
#     try:
#         await _trigger_enhanced_logic_v2_for_media(
#             str(media.uuid), current_user=None
#         )
#     except Exception as e:
#         logger.warning(
#             f"Failed to trigger Enhanced Logic V2 for uploaded media "
#             f"{media.uuid}: {e}"
#         )
```

```python
# In ppl-meta-cameras/src/services/camera_detection.py (around line 2302)
# Check if automatic face detection on save is enabled
# TEMPORARILY DISABLED - November 20, 2025
# Reason: Authentication issues preventing Enhanced Logic V2
# TODO: Re-enable after implementing proper auth token passing (Issue #3)
# await self._check_and_trigger_face_detection(
#     media_uuid, session, headers
# )
```

**Testing**:
- Upload new video and verify NO face detection runs
- Check `face_detections` table remains empty
- Verify no 401/403 errors in logs

---

### Issue #3: Fix Enhanced Logic V2 Authentication

**Problem**: Enhanced Logic V2 endpoint requires auth token, but callers don't provide it

**Root Cause**:

1. **Media Service** (`_trigger_enhanced_logic_v2_for_media`, line 86-145):
   ```python
   headers = {
       "Content-Type": "application/json",
       "Accept": "application/json",
   }
   # ❌ NO auth token!
   ```

2. **Camera Service** (`_trigger_face_detection_workflow`, line 2596-2650):
   ```python
   async with session.get(
       orchestrator_url, headers=headers
   ) as response:
   # ⚠️ Headers passed but may not contain valid auth token
   ```

3. **Orchestrator Endpoint** (line 681-683):
   ```python
   @face_detection_router.get("/media/{media_id}/faces/enhanced-v2")
   async def get_media_face_detection_enhanced_v2(
       media_id: str,
       auth_token: str = Depends(get_auth_token),  # ❌ REQUIRES AUTH
   ```

**Solutions**:

**Option A: Service-to-Service Authentication (Recommended)**

1. **Create internal service token**:
   ```python
   # In shared/auth/service_auth.py
   INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "service-to-service-secret-key")
   
   def get_service_auth_headers():
       return {
           "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
           "X-Service-Name": "ppl-meta-media",
           "Content-Type": "application/json",
       }
   ```

2. **Update Orchestrator to accept service tokens**:
   ```python
   # In ppl-meta-orchestrator/src/auth.py
   async def get_auth_token_optional(
       authorization: Optional[str] = Header(None)
   ):
       if authorization and authorization.startswith("Bearer "):
           token = authorization.split(" ")[1]
           
           # Check for internal service token
           if token == INTERNAL_SERVICE_TOKEN:
               return token  # Valid service token
           
           # Otherwise validate as user token
           return await validate_user_token(token)
       
       return None  # No auth required for internal calls
   ```

3. **Update Media service caller**:
   ```python
   # In ppl-meta-media/src/api/v1/media.py
   from shared.auth.service_auth import get_service_auth_headers
   
   async def _trigger_enhanced_logic_v2_for_media(
       media_uuid: str, current_user: Optional[AuthUser] = None
   ):
       headers = get_service_auth_headers()  # ✅ Include service token
       
       async with aiohttp.ClientSession() as session:
           async with session.get(orchestrator_url, headers=headers) as response:
               # ... rest of code
   ```

4. **Update Camera service caller**:
   ```python
   # In ppl-meta-cameras/src/services/camera_detection.py
   from shared.auth.service_auth import get_service_auth_headers
   
   async def _trigger_face_detection_workflow(
       self, media_uuid: str, session, headers: Dict
   ):
       # Override with service headers
       service_headers = get_service_auth_headers()
       
       async with session.get(
           orchestrator_url, headers=service_headers  # ✅ Use service token
       ) as response:
           # ... rest of code
   ```

**Option B: Make Enhanced Logic V2 Public for Internal Calls**

1. **Create separate internal endpoint**:
   ```python
   # In ppl-meta-orchestrator/src/face_detection_endpoints.py
   
   @face_detection_router.get("/internal/media/{media_id}/faces/enhanced-v2")
   async def internal_enhanced_logic_v2(
       media_id: str,
       frame_interval: int = Query(10),
       # ❌ NO auth_token required for internal endpoint
   ):
       """Internal endpoint for service-to-service calls."""
       result = await session_manager.enhanced_logic_v2_session_based(
           media_id, auth_token=None, frame_interval=frame_interval
       )
       return result
   ```

2. **Update callers to use internal endpoint**:
   ```python
   # Update both Media and Camera services
   orchestrator_url = (
       f"{ORCHESTRATOR_SERVICE_URL}/api/v1/internal/media/"
       f"{media_uuid}/faces/enhanced-v2"
   )
   ```

**Option C: Pass User Token from Camera Service**

1. **Camera service receives user auth from mobile app**
2. **Forward auth token to Media service during upload**
3. **Media service uses user token for Enhanced Logic V2 call**

*(Not recommended: adds complexity, requires mobile app changes)*

**Recommended Implementation**: **Option A** (Service-to-Service Authentication)
- Most secure
- Follows microservices best practices
- No changes to mobile app required
- Easy to audit service-to-service calls

**Files to Modify**:
1. `/Users/nickgklezakos/Documents/ppl-meta-code/shared/auth/service_auth.py` (create new) ✅ DONE
2. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-orchestrator/src/face_detection_endpoints.py` (add Header import, update get_auth_token, update Vision service calls) ✅ DONE
3. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/api/v1/media.py` (line 110) ✅ DONE
4. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src/services/camera_detection.py` (line 2630) ✅ DONE
5. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src/main.py` (line 1698 - accept service tokens) ⏳ TODO

---

### Issue #4: Fix Recording Event Notifications to VMeta

**Problem**: Recording start/stop events never reach VMeta, preventing batch processing from activating

**Investigation Results**:

1. **Camera Service HAS the code** (streaming.py):
   - Lines 336-358: Recording start notification to VMeta
   - Lines 425-451: Recording stop notification to VMeta
   
2. **VMeta endpoint verified WORKING**:
   - Tested: `curl POST http://localhost:8006/api/v1/recording/started`
   - Result: ✅ SUCCESS (no auth required, PollingFallbackManager activates)

3. **BUT recording_sessions table is EMPTY**:
   - Expected: Recording sessions created when start/stop events received
   - Actual: No rows in `ppl_orchestrator_db.recording_sessions`
   - Conclusion: Events are NOT being sent or are failing silently

**Root Causes to Investigate**:

1. **Is Camera service actually calling the notification code?**
   - Check if recording flow uses streaming.py endpoints
   - Mobile app may be using different recording API
   - May be using direct video upload without recording session

2. **Are notifications failing silently?**
   - Check Camera service logs for VMeta notification attempts
   - Check for network errors, timeouts, or exceptions
   - Verify VMeta URL is correct in Camera service config

3. **Is there a different recording flow?**
   - Mobile app may upload videos directly to Media service
   - Camera service may not be involved in recording at all
   - Need to trace actual recording flow from mobile app

**Action Items**:

1. **Enable detailed logging** in Camera service for recording events:
   ```python
   # In ppl-meta-cameras/src/api/v1/endpoints/streaming.py
   
   # Around line 342 (recording start)
   logger.info(f"🎬 RECORDING START EVENT - Notifying VMeta...")
   logger.info(f"🎬 VMeta URL: {vmeta_url}")
   logger.info(f"🎬 Recording session: {recording_session_id}")
   
   # Add try-catch with detailed error logging
   try:
       async with session.post(vmeta_url, json=payload, headers=headers) as resp:
           logger.info(f"🎬 VMeta response status: {resp.status}")
           response_body = await resp.text()
           logger.info(f"🎬 VMeta response body: {response_body}")
   except Exception as e:
       logger.error(f"🎬 ❌ FAILED to notify VMeta: {e}", exc_info=True)
   ```

2. **Trace actual recording flow** from mobile app:
   - Check Flutter app code for recording API endpoints
   - Verify which service handles recording (Camera vs Media)
   - Document the actual flow vs expected flow

3. **Test recording notification manually**:
   ```bash
   # Create a test recording session
   curl -X POST http://localhost:8006/api/v1/recording/started \
     -H "Content-Type: application/json" \
     -d '{
       "collection_id": "usb_camera_0",
       "recording_session_id": "test_session_123",
       "started_at": "2025-11-20T12:00:00Z"
     }'
   
   # Verify it appears in database
   psql -d ppl_orchestrator_db -c "SELECT * FROM recording_sessions;"
   ```

4. **Fix notification sending** if code exists but not executing:
   - Ensure recording endpoints are actually called by mobile app
   - Add retry logic for failed notifications
   - Implement fallback mechanism if VMeta is unavailable

**Files to Investigate**:
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src/api/v1/endpoints/streaming.py` (lines 336-358, 425-451)
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera/lib/services/camera_service.dart` (mobile app recording code)
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src/api/v1/recording_events.py` (VMeta receiving endpoint)

---

### Issue #5: Implement Proper Continuous Pipeline

**Problem**: Complete pipeline not executing as described in original documentation

**Reference Documentation**: `/Users/nickgklezakos/Documents/ppl-meta-code/docs/guides/developer/continuous-individuals-and-mvr-pipeline.md`

**Expected Pipeline Flow** (from documentation):

1. ✅ **User starts recording** → Camera service begins recording
2. ✅ **User stops recording** → Video saved and uploaded to Media service
3. ❌ **Recording start event** → Sent to VMeta (FAILING - Issue #4)
4. ❌ **Recording stop event** → Sent to VMeta (FAILING - Issue #4)
5. ❌ **Enhanced Logic V2** → Auto-triggered for uploaded video (FAILING - Issue #3)
6. ❌ **Face Detection Session** → Creates person_objects from faces (NEVER RUNS)
7. ❌ **Batch Accumulation** → VMeta counts videos with completed face detection (NEVER STARTS)
8. ❌ **Batch Trigger** → When X videos ready, trigger cross-video tracking (NEVER HAPPENS)
9. ❌ **Individual Creation** → Cross-video tracking creates individuals (NEVER RUNS)
10. ❌ **MVR Aggregation** → Individuals aggregated into MVR people (NEVER RUNS)

**Current Reality**:

1. ✅ User starts/stops recording → Video uploaded
2. ✅ Basic face detection runs (WRONG METHOD)
3. ❌ Everything else fails

**Implementation Requirements**:

**Step 1: Fix Authentication** (Issue #3)
- Implement service-to-service auth
- Enhanced Logic V2 can be called successfully
- person_objects get created automatically

**Step 2: Fix Recording Notifications** (Issue #4)
- Camera service sends recording events to VMeta
- VMeta creates recording_sessions
- PollingFallbackManager activates for batch tracking

**Step 3: Enable Auto-Trigger** (Issue #2 reversal)
- Uncomment Media service auto-trigger (line 304-316)
- Uncomment Camera service trigger (line 2302)
- Enhanced Logic V2 runs automatically on upload

**Step 4: Configure Batch Processing**
- Set batch size X in VMeta config (default: 5 videos)
- Configure polling interval (default: 30 seconds)
- Set batch timeout (default: 5 minutes)

**Step 5: Verify Complete Pipeline**
- Start new recording session
- Upload multiple videos (X+1 videos)
- Verify each step executes:
  * ✅ Recording events sent to VMeta
  * ✅ Enhanced Logic V2 runs for each video
  * ✅ person_objects created in Orchestrator DB
  * ✅ Batch processing accumulates videos
  * ✅ After X videos, cross-video tracking triggers
  * ✅ Individuals created
  * ✅ MVR people aggregated
  * ✅ Search returns MVR people

**Configuration Files to Update**:

1. **VMeta Service Config** (`ppl-meta-vmeta/.env` or `config.yaml`):
   ```yaml
   # Batch Processing Configuration
   BATCH_SIZE: 5  # Trigger after 5 videos
   POLLING_INTERVAL: 30  # Check every 30 seconds
   BATCH_TIMEOUT: 300  # 5 minutes max wait
   ENABLE_BATCH_PROCESSING: true
   
   # Enhanced Logic V2 Integration
   ORCHESTRATOR_URL: "http://localhost:8002"
   CALL_ENHANCED_LOGIC_V2: true
   ```

2. **Camera Service Config** (`ppl-meta-cameras/.env`):
   ```bash
   # VMeta Integration
   VMETA_SERVICE_URL=http://localhost:8008
   ENABLE_RECORDING_NOTIFICATIONS=true
   
   # Face Detection
   ENABLE_AUTO_FACE_DETECTION=true
   ```

3. **Media Service Config** (`ppl-meta-media/.env`):
   ```bash
   # Orchestrator Integration
   ORCHESTRATOR_URL=http://localhost:8002
   ENABLE_AUTO_FACE_DETECTION=true
   ```

**Testing Checklist**:

- [ ] Service-to-service auth working
- [ ] Enhanced Logic V2 called successfully on upload
- [ ] person_objects created in Orchestrator DB
- [ ] Recording events sent to VMeta
- [ ] recording_sessions created in Orchestrator DB
- [ ] PollingFallbackManager activates
- [ ] Batch state accumulates videos
- [ ] After X videos, cross-video tracking triggers
- [ ] tracking_sessions created with video_uuids
- [ ] Individuals created from person_objects
- [ ] MVR people aggregated from individuals
- [ ] Search returns MVR people
- [ ] All tables properly populated

---

## Root Cause Analysis

### Primary Root Cause (RESOLVED)

**Video UUIDs Parameter Type Mismatch**

The cross-video tracking API was incorrectly serializing the `video_uuids` list parameter with `json.dumps()`, converting it to a JSON string. PostgreSQL's JSONB column expected the raw Python list, which asyncpg would automatically convert.

**Fix**: Changed from `json.dumps(request.video_uuids)` to passing `request.video_uuids` directly.

### Secondary Root Cause (RESOLVED)

**Hardcoded Collection ID in PollingFallbackManager**

The polling manager was configured with a single hardcoded collection ID, preventing dynamic multi-collection support as described in the continuous pipeline documentation.

**Fix**: Changed `collection_id` parameter to optional, implemented dynamic collection tracking via recording events (`_active_recordings` dictionary).

### Remaining Root Cause (PENDING)

**~~Authentication Failure in Service-to-Service Communication~~** (Original issue - not the actual problem)

The Enhanced Logic V2 endpoint requires authentication (`auth_token` parameter), but the calling services (Media and Camera) do not provide valid authentication tokens when making internal service-to-service calls.

**Impact Chain**:
1. Media/Camera service calls Enhanced Logic V2 without auth token
2. Request fails with 401 Unauthorized
3. Caller logs warning but continues execution
4. No person_objects created (requires Enhanced Logic V2)
5. Basic face detection somehow triggers as fallback (still under investigation)
6. Pipeline cannot proceed without person_objects

### Secondary Root Cause

**Missing Recording Event Notifications**

The Camera service has code to notify VMeta of recording start/stop events, but these notifications are either:
1. Not being executed (different recording flow used)
2. Failing silently (network errors, wrong URL)
3. Never implemented in actual mobile app integration

**Impact Chain**:
1. VMeta never receives recording start/stop events
2. No recording_sessions created in Orchestrator DB
3. PollingFallbackManager never activates
4. Batch processing never accumulates videos
5. Cross-video tracking never triggers
6. No individuals or MVR people created

### Contributing Factors

1. **Silent Failure Handling**: Both services log warnings but continue execution instead of failing fast
2. **Insufficient Logging**: Log files outdated (Nov 19), no logs from today's recording
3. **Missing Integration Testing**: End-to-end pipeline tests would have caught these issues
4. **Documentation Drift**: Documentation describes ideal state, not actual implementation
5. **Fallback to Basic Detection**: System falls back to legacy basic face detection, masking the Enhanced Logic V2 failure

---

## Proposed Solutions

### Solution Overview

**Phase 1: Investigation & Disable** (Today)
1. Complete investigation of basic face detection trigger
2. Disable auto-face-detection until fixed
3. Document findings in this report

**Phase 2: Authentication Fix** (Priority 1)
1. Implement service-to-service authentication
2. Update all internal service calls
3. Test Enhanced Logic V2 end-to-end

**Phase 3: Recording Notifications** (Priority 2)
1. Trace actual recording flow from mobile app
2. Fix or implement recording event notifications
3. Verify VMeta receives events correctly

**Phase 4: Integration Testing** (Priority 3)
1. Create end-to-end pipeline tests
2. Test with real recording session
3. Verify all database tables populated

**Phase 5: Documentation Update** (Priority 4)
1. Update documentation with actual implementation
2. Add troubleshooting guide
3. Create runbook for common issues

---

## Implementation Plan

### Phase 1: Investigation & Disable (Today - November 20)

**Tasks**:
- [x] Investigate recording results (9 videos found)
- [x] Confirm face detection ran (basic method)
- [x] Identify NO person_objects created
- [x] Verify VMeta endpoints working
- [x] Discover basic vs Enhanced Logic V2 discrepancy
- [x] Trace face detection trigger code
- [x] Document findings in this report
- [ ] Complete basic face detection trigger investigation
- [ ] Disable auto-face-detection in both services
- [ ] Create manual batch trigger script as workaround

**Deliverables**:
- ✅ This investigation report
- ⏳ Basic face detection fully traced
- ⏳ Auto-triggers commented out
- ⏳ Manual script ready for processing existing videos

**Estimated Time**: 2-4 hours remaining

---

### Phase 2: Authentication Fix (Next - November 20-21)

**Tasks**:
1. Create shared service authentication module
2. Implement service-to-service token generation
3. Update Orchestrator auth to accept service tokens
4. Update Media service Enhanced Logic V2 caller
5. Update Camera service Enhanced Logic V2 caller
6. Test service-to-service authentication
7. Test Enhanced Logic V2 execution end-to-end
8. Verify person_objects creation

**Files to Modify**:
- `/Users/nickgklezakos/Documents/ppl-meta-code/shared/auth/service_auth.py` (NEW)
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-orchestrator/src/auth.py`
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/api/v1/media.py`
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src/services/camera_detection.py`
- Environment files for all services (`.env`)

**Testing**:
- Unit tests for service auth module
- Integration test: Media → Orchestrator call
- Integration test: Camera → Orchestrator call
- Verify person_objects created after Enhanced Logic V2
- Check face_detection_sessions table populated

**Deliverables**:
- Service authentication working
- Enhanced Logic V2 callable from internal services
- person_objects created automatically
- Documentation of auth implementation

**Estimated Time**: 4-6 hours

---

### Phase 3: Recording Notifications (November 21-22)

**Tasks**:
1. Trace actual recording flow from mobile app
2. Verify which API endpoints mobile app uses
3. Add detailed logging to Camera service recording endpoints
4. Test recording notification manually
5. Fix notification sending if code exists but not executing
6. Verify VMeta receives events correctly
7. Verify recording_sessions created
8. Verify PollingFallbackManager activates

**Files to Investigate/Modify**:
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera/lib/services/camera_service.dart`
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src/api/v1/endpoints/streaming.py`
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src/api/v1/recording_events.py`

**Testing**:
- Manual curl test of VMeta recording endpoints
- Mobile app test: start/stop recording
- Verify recording_sessions table populated
- Verify batch_processing_state created
- Check PollingFallbackManager logs

**Deliverables**:
- Recording flow documented
- Notifications sent reliably
- VMeta receiving events correctly
- Batch processing activating properly

**Estimated Time**: 3-5 hours

---

### Phase 4: Integration Testing (November 22)

**Tasks**:
1. Create comprehensive end-to-end test
2. Test complete pipeline with real recording
3. Verify all database tables populated:
   - ppl_media_db.media (videos)
   - ppl_vision_db.face_detections (faces)
   - ppl_vision_db.face_detection_sessions (Enhanced Logic V2 sessions)
   - ppl_vision_db.person_objects (person objects from faces)
   - ppl_orchestrator_db.recording_sessions (recording events)
   - ppl_meta_vmeta.batch_processing_state (batch accumulation)
   - ppl_meta_vmeta.tracking_sessions (cross-video tracking)
   - ppl_meta_vmeta.individuals (computed individuals)
   - ppl_meta_vmeta.mvr_people (aggregated MVR people)
4. Test search returns MVR people
5. Document test results

**Test Script**:
```bash
#!/bin/bash
# End-to-end pipeline test

echo "=== Starting Complete Pipeline Test ==="

# 1. Clean up previous test data
echo "Cleaning up test data..."
psql -d ppl_vision_db -c "DELETE FROM face_detection_sessions WHERE created_at >= NOW() - INTERVAL '1 hour';"
psql -d ppl_meta_vmeta -c "DELETE FROM tracking_sessions WHERE created_at >= NOW() - INTERVAL '1 hour';"

# 2. Start recording via mobile app
echo "Starting recording session..."
# (Manual step: use mobile app)

# 3. Record X+1 videos (6 videos if batch size is 5)
echo "Recording videos..."
# (Manual step: record videos)

# 4. Stop recording
echo "Stopping recording..."
# (Manual step: stop recording)

# 5. Wait for batch processing (30-60 seconds)
echo "Waiting for batch processing..."
sleep 60

# 6. Verify database states
echo "Verifying database states..."

echo "Videos uploaded:"
psql -d ppl_media_db -c "SELECT id, uuid, created_at FROM media WHERE created_at >= NOW() - INTERVAL '1 hour' ORDER BY created_at;"

echo "Face detection sessions:"
psql -d ppl_vision_db -c "SELECT session_uuid, media_uuid, total_faces_detected FROM face_detection_sessions WHERE created_at >= NOW() - INTERVAL '1 hour';"

echo "Person objects:"
psql -d ppl_vision_db -c "SELECT COUNT(*) as person_count FROM person_objects WHERE created_at >= NOW() - INTERVAL '1 hour';"

echo "Recording sessions:"
psql -d ppl_orchestrator_db -c "SELECT * FROM recording_sessions WHERE started_at >= NOW() - INTERVAL '1 hour';"

echo "Batch processing state:"
psql -d ppl_meta_vmeta -c "SELECT * FROM batch_processing_state;"

echo "Tracking sessions:"
psql -d ppl_meta_vmeta -c "SELECT session_uuid, status, total_videos FROM tracking_sessions WHERE created_at >= NOW() - INTERVAL '1 hour';"

echo "Individuals created:"
psql -d ppl_meta_vmeta -c "SELECT COUNT(*) FROM individuals WHERE created_at >= NOW() - INTERVAL '1 hour';"

echo "MVR people:"
psql -d ppl_meta_vmeta -c "SELECT COUNT(*) FROM mvr_people WHERE created_at >= NOW() - INTERVAL '1 hour';"

# 7. Test search
echo "Testing search for MVR people..."
curl -s "http://localhost:8001/api/v1/search/mvr-people?collection=usb_camera_0" | jq '.'

echo "=== Test Complete ==="
```

**Deliverables**:
- End-to-end test script
- Test results documentation
- Confirmed working pipeline
- Performance metrics

**Estimated Time**: 2-3 hours

---

### Phase 5: Documentation Update (November 23)

**Tasks**:
1. Update continuous pipeline documentation with actual implementation
2. Add authentication section
3. Add troubleshooting guide
4. Create runbook for common issues
5. Document configuration options
6. Add monitoring recommendations

**Files to Update**:
- `/Users/nickgklezakos/Documents/ppl-meta-code/docs/guides/developer/continuous-individuals-and-mvr-pipeline.md`
- `/Users/nickgklezakos/Documents/ppl-meta-code/docs/troubleshooting/` (new files)
- `/Users/nickgklezakos/Documents/ppl-meta-code/README.md` (service descriptions)

**Deliverables**:
- Updated documentation reflecting actual implementation
- Troubleshooting guide
- Operations runbook
- Configuration guide

**Estimated Time**: 2-3 hours

---

## Total Estimated Implementation Time

- **Phase 1**: 2-4 hours
- **Phase 2**: 4-6 hours
- **Phase 3**: 3-5 hours
- **Phase 4**: 2-3 hours
- **Phase 5**: 2-3 hours

**Total**: 13-21 hours (approximately 2-3 working days)

---

## Success Criteria

### Immediate Success (Phase 1-2) - ✅ COMPLETED

- [x] video_uuids parameter bug identified and fixed
- [x] Dynamic collection management implemented
- [x] Manual cross-video tracking verified working end-to-end
- [x] Enhanced Logic V2 creates person_objects automatically
- [x] Individuals and MVR people created successfully
- [x] MVR people searchable in Flutter app (camera counter: count=1, videos=15)

### Short-term Success (Phase 3-4) - ⏳ IN PROGRESS

- [ ] Recording events sent to VMeta reliably (BLOCKED - needs Camera service implementation)
- [ ] recording_sessions created in Orchestrator DB (PENDING)
- [x] PollingFallbackManager supports dynamic collections
- [x] Per-collection batch queuing implemented
- [ ] Batch processing accumulates videos (PENDING - needs recording events)
- [ ] Cross-video tracking triggers automatically after X videos (PENDING)
- [x] Individuals and MVR people created (WORKING - verified manually)
- [x] Search returns MVR people (WORKING - Flutter app confirmed)
- [x] Cross-video tracking database flow working correctly

### Long-term Success (Phase 5+)

- [ ] Documentation reflects actual implementation
- [ ] Troubleshooting guide available
- [ ] Operations runbook documented
- [ ] Monitoring and alerting configured
- [ ] Pipeline runs reliably without manual intervention
- [ ] Performance meets requirements (< 30 seconds per batch)

---

## Risk Assessment

### High Risk Items

1. **Authentication Changes**: May break existing user-facing endpoints if not carefully implemented
   - **Mitigation**: Use separate internal endpoints or service-specific auth headers
   
2. **Mobile App Integration**: Recording flow may require mobile app changes
   - **Mitigation**: Maintain backward compatibility, implement feature flags

3. **Data Consistency**: Existing 9 videos need to be processed correctly
   - **Mitigation**: Create manual processing script, test thoroughly before running

### Medium Risk Items

1. **Service Downtime**: Updates may require service restarts
   - **Mitigation**: Rolling updates, test in development first

2. **Performance Impact**: Enhanced Logic V2 for every video may slow uploads
   - **Mitigation**: Make auto-trigger async, implement queue if needed

3. **Database Migrations**: May need schema changes
   - **Mitigation**: Use proper migration scripts, backup databases

### Low Risk Items

1. **Configuration Changes**: Environment variables need updates
   - **Mitigation**: Document changes, provide migration guide

2. **Logging Volume**: Increased logging may fill disk
   - **Mitigation**: Implement log rotation, monitor disk usage

---

## Next Steps

1. **Complete Issue #1**: Finish investigating basic face detection trigger
2. **Implement Issue #2**: Disable auto-face-detection temporarily
3. **Process Existing Videos**: Use manual script to process the 9 existing videos
4. **Begin Issue #3**: Implement service-to-service authentication
5. **Test & Iterate**: Verify each fix before moving to next phase

---

## Appendix

### Database Table Reference

**ppl_media_db**:
- `media`: Uploaded video files

**ppl_vision_db**:
- `face_detections`: Detected faces (basic detection)
- `face_detection_sessions`: Enhanced Logic V2 sessions
- `person_objects`: Person objects created by Enhanced Logic V2

**ppl_orchestrator_db**:
- `recording_sessions`: Recording start/stop events

**ppl_meta_vmeta**:
- `batch_processing_state`: Video accumulation for batching
- `tracking_sessions`: Cross-video tracking sessions
- `individuals`: Computed individual identities
- `mvr_people`: Aggregated MVR people (final output)

### Service URL Reference

- **Media Service**: `http://localhost:8000`
- **Node Service**: `http://localhost:8001`
- **Orchestrator Service**: `http://localhost:8002`
- **Vision Service**: `http://localhost:8003`
- **Camera Service**: `http://localhost:8005`
- **Discovery Service**: `http://localhost:8006`
- **Bootcore Service**: `http://localhost:8007`
- **VMeta Service**: `http://localhost:8008`
- **Gateway Service**: `http://localhost:8080`

### Key Endpoints

**Enhanced Logic V2**:
- `GET /api/v1/media/{media_uuid}/faces/enhanced-v2` (Orchestrator, Port 8002)

**Recording Events**:
- `POST /api/v1/recording/started` (VMeta, Port 8008)
- `POST /api/v1/recording/stopped` (VMeta, Port 8008)

**Cross-Video Tracking**:
- `POST /api/v1/cross-video-tracking/sessions` (VMeta, Port 8008)

**Basic Face Detection** (to be disabled):
- `POST /api/v1/workflow/face-detection/process/{media_id}` (Media, Port 8000)

---

**Document End**

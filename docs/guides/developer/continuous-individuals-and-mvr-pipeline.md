# Continuous Individuals and MVR People Data Objects Pipeline

**Document Version:** 1.3  
**Last Updated:** November 20, 2025  
**Service:** ppl-meta-vmeta  
**Port:** 8008  
**Implementation Status:** ⚠️ PARTIAL - Missing Automatic Batch Triggering

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Pipeline Components](#pipeline-components)
4. [Batch Processing Lifecycle](#batch-processing-lifecycle)
5. [Trigger Mechanisms](#trigger-mechanisms)
6. [Resource Management](#resource-management)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Configuration](#configuration)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Error Handling and Recovery](#error-handling-and-recovery)
12. [Performance Optimization](#performance-optimization)

---

## Executive Summary

### Purpose

This document proposes a **continuous, non-blocking pipeline** for automatically creating individuals and MVR people data objects from batches of recorded videos. The pipeline triggers automatically after a configurable number of videos (batch size X) have completed both recording and face detection processing.

### Key Features

✅ **Automatic Batch Triggering**: Processes batches of X videos after face detection completes  
✅ **Two-Level Caching**: Leverages existing individual and MVR cache architecture  
✅ **Non-Blocking Execution**: Runs independently using dedicated resources  
✅ **Time-Range Based**: Creates objects for duration from first to last video in batch  
✅ **Collection-Scoped**: Processes videos within specific camera collections  
✅ **Fault Tolerant**: Handles failures gracefully with retry mechanisms  
✅ **Resource Isolated**: Uses separate compute resources from recording and face detection  

### Architecture Principles

1. **Event-Driven**: Face detection completion events trigger batch processing
2. **Asynchronous**: Pipeline runs in background without blocking other services
3. **Incremental**: Processes batches as they become ready (rolling window)
4. **Cached**: Reuses existing individuals and MVR people via two-level cache
5. **Scalable**: Can process multiple collections concurrently

---

## Implementation Status

### ⚠️ November 20, 2025 - CRITICAL GAP IDENTIFIED

**Cross-Video Tracking NOT Auto-Triggering**

**Issue**: The continuous pipeline is incomplete - while person_objects are created automatically via Enhanced Logic V2, cross-video tracking is NOT triggered automatically. This means:
- ✅ Videos uploaded → person_objects created (working)
- ❌ Cross-video tracking batch triggering → NOT implemented
- ❌ Individuals/MVR people creation → requires manual trigger
- **Impact**: Users see NO search results because MVR people don't exist

**Root Cause**: Missing automatic batch trigger after face detection completes. The pipeline document describes batch triggering (Phase 2) but it's not implemented in code.

**Current Workaround**: Manual API call required:
```bash
POST /api/v1/cross-video/individuals/tracking/sessions
{
  "collections": ["usb_camera_0"],
  "start_time": "2025-11-20T11:09:00",
  "end_time": "2025-11-20T11:14:00"
}
```

**Status**: 
- Camera service: ✅ Auto-uploads videos, assigns to collections
- Enhanced Logic V2: ✅ Auto-creates person_objects
- Cross-video tracking: ❌ NOT auto-triggered (must call manually)
- VMeta service: ✅ Works when tracking is triggered

**Next Steps**: 
1. Implement automatic batch accumulator in vmeta service
2. Subscribe to face_detection_complete events from Orchestrator
3. Trigger cross-video tracking when batch threshold reached
4. Support both threshold-based and time-based triggering

---

### ✅ November 19, 2025 - MAJOR OPTIMIZATION UPDATE

**Enhanced Logic V2 Integration + Video UUID Optimization**

The pipeline has been significantly optimized with two critical improvements:

**1. Enhanced Logic V2 Integration**
- ✅ **person_objects Creation**: System now calls Enhanced Logic V2 endpoint before cross-video tracking
- ✅ **Missing Step Fixed**: Converts stored_faces (Vision DB) → person_objects (Orchestrator DB)
- ✅ **Endpoint**: `POST /api/v1/media/{video_uuid}/faces/enhanced-v2`
- ✅ **Location**: Orchestrator Service (Port 8002)
- ✅ **Impact**: Cross-video tracking can now find person_objects for creating individuals/MVR

**2. Video UUID Direct Lookup Optimization**
- ✅ **Explicit video_uuids**: API now accepts `video_uuids` parameter in request
- ✅ **Skips Time Range Query**: When video_uuids provided, directly fetches metadata by UUID
- ✅ **Performance Gain**: Eliminates unnecessary time range calculations and queries
- ✅ **Precision**: No ambiguity about which videos to process
- ✅ **Backward Compatible**: Falls back to time-based discovery if no video_uuids provided

**Code Changes**:
```python
# API Request Model (cross_video_tracking_simple.py)
class CreateTrackingSessionRequest(BaseModel):
    collections: List[str]
    start_time: datetime
    end_time: datetime
    video_uuids: Optional[List[str]] = None  # NEW: Explicit UUIDs
    algorithm_config: Optional[Dict[str, Any]] = None
    background_processing: bool = True

# Process Flow
async def process_tracking_session(session_uuid: str, auth_token: str = None):
    # 1. Check for explicit video_uuids (OPTIMIZATION)
    if video_uuids_list:
        # Direct UUID lookup - skip time-based query
        videos = await fetch_videos_by_uuids(video_uuids_list)
    else:
        # Legacy: time-based discovery
        videos = await discover_videos_in_collection(collections, start, end)
    
    # 2. Call Enhanced Logic V2 (CRITICAL FIX)
    for video in videos:
        await client.post(
            f"http://localhost:8002/api/v1/media/{video_uuid}/faces/enhanced-v2"
        )
        # Creates person_objects from stored_faces
    
    # 3. Run cross-video tracking (now has person_objects!)
    await process_videos_for_tracking(videos)
```

**Database Migration**:
```sql
-- Added video_uuids JSONB column to tracking_sessions
ALTER TABLE tracking_sessions 
ADD COLUMN IF NOT EXISTS video_uuids JSONB;
```

### ✅ November 14, 2025 - Initial Implementation

**Continuous Segment Upload** (Camera Service - Port 8005)
- ✅ Segment rotation uploads immediately to Media Service
- ✅ Every 30-second segment triggers upload after completion
- ✅ Upload happens in parallel with recording (non-blocking)
- ✅ **Verified Working**: Test recordings upload successfully

**Face Detection Auto-Triggering** (FIXED)
- ✅ Media Service GET endpoint now supports authentication (line 838)
- ✅ Streaming endpoint path fixed (line 1154)
- ✅ File save path corrected (line 1067)
- ✅ `face_detection_on_save` setting enabled in database
- ✅ **Verified Working**: New videos trigger face detection automatically

**Per-Collection Batch Processing** (FIXED)
- ✅ Separate batch queues per collection (`_pending_videos_by_collection`)
- ✅ No cross-camera contamination
- ✅ Each collection processes independently
- ✅ Hardcoded collection_id bug fixed

```python
# This is called after upload succeeds:
await self._check_and_trigger_face_detection(media_uuid, session, headers)
```

This function exists and is called, but face detection is not being triggered. Possible causes:
1. Face detection endpoint not responding
2. Media service not forwarding trigger to Vision service
3. Vision service not accepting face detection requests
4. Workflow creation failing silently

### 🔄 Root Cause Identified (November 19, 2025 - 11:52 AM)

**FOUND THE ISSUE!** 🎯

After manual recording test (2:10 duration, 5 segments):

**What Works**:
- ✅ Videos uploaded to Media service database (2 videos confirmed)
- ✅ Camera service DOES trigger face detection (verified by checking Orchestrator)
- ✅ Orchestrator receives trigger and creates detection session

**The Problem**:
```json
{
    "success": false,
    "error": "Media not found: 408c8d0a-7cfd-42c7-a82d-91195cd8d3c2"
}
```

**Video File Path Mismatch**:
- Media DB stores: `media/4cf362b1-.../video/2025/11/90b341e2....mp4`
- Actual location: `ppl-meta-cameras/recordings/usb_camera_0/768cbbd6-.../segment_005_20251119_114256.mp4`
- **Result**: Vision service cannot find file → Face detection fails → Pipeline never starts

**Root Cause**: 
After Camera service uploads video content to Media service, the physical file is not accessible at the path stored in Media database. Vision service tries to read from Media's path but file doesn't exist there.

**Next Steps**:
1. Fix file storage: Ensure uploaded files are accessible to Vision service
2. Option A: Camera service copies files to Media storage location
3. Option B: Vision service reads from Camera recordings directory
4. Option C: Shared storage volume between services (Docker/K8s)

---

## Latest Updates (November 19, 2025)

### CRITICAL FIX: Per-Collection Batch Processing

**Issue Discovered**: The PollingFallbackManager was mixing videos from multiple camera collections into single batches, causing incorrect cross-camera individual tracking.

**Root Cause**:
- Old architecture used **single queue** for all collections: `self._pending_videos = []`
- Videos from `usb_camera_0` and `usb_camera_1` were batched together
- Result: Individuals incorrectly tracked across different cameras

**Fix Implemented** (Lines 354, 624-740):
```python
# NEW: Separate queue per collection
self._pending_videos_by_collection = {
    'usb_camera_0': [video1, video2, video3],
    'usb_camera_1': [video4, video5]
}

# Polling loop now processes each collection SEPARATELY
for coll_id in active_collection_ids:
    # Query videos for THIS collection only
    # Check faces for THIS collection only
    # Add to THIS collection's queue only
    # Trigger batch when THIS collection reaches batch_size
```

**Impact**:
- ✅ Each camera collection now has independent batch queue
- ✅ Batches contain videos from SINGLE collection only
- ✅ Per-collection individuals and MVR people creation
- ✅ Supports multiple simultaneous recordings
- ✅ No cross-camera contamination

**Testing Required**: Record from 2 cameras simultaneously and verify separate batches are created for each collection.

---

## Latest Test Results (November 18, 2025)

### Test Recording Details
- **Date**: November 18, 2025, 08:21-08:25 AM (4:20 duration)
- **Camera**: USB Camera 0 (usb_camera_0)
- **Videos Uploaded**: 8 segments successfully uploaded to Media service
- **Collection ID**: usb_camera_0

### Database Verification Queries

```sql
-- Face detection sessions (Vision DB - ppl_vision_db)
SELECT COUNT(*) FROM face_detection_sessions WHERE created_at > '2025-11-18';
-- ❌ Result: 0 sessions (NO FACE DETECTION OCCURRED)

-- Individuals (VMeta DB - ppl_meta_vmeta)
SELECT COUNT(*) FROM individual_video_appearances WHERE start_timestamp > '2025-11-18';
-- ❌ Result: 0 individuals

-- MVR People (VMeta DB - ppl_meta_vmeta)  
SELECT COUNT(*) as total_mvr, MAX(created_at) as latest_mvr FROM mvr_people;
-- ⚠️ Result: 69 total, latest from 07:24:35 (BEFORE test recording)
-- ❌ 0 new MVR people created from test recording

-- Batch Processing State (VMeta DB - ppl_meta_vmeta)
SELECT * FROM batch_processing_state ORDER BY updated_at DESC LIMIT 5;
-- ❌ Result: 0 rows (NO BATCHES EVER CREATED)

-- Orchestrator Workflows
curl 'http://localhost:8002/api/v1/workflows?status=completed&limit=20'
-- ❌ Result: 0 workflows from today
```

### Root Cause: Face Detection Not Triggered

**Problem**: The Camera service uploads videos successfully but face detection is never triggered, causing a cascade failure throughout the entire pipeline.

**Evidence**:
1. ✅ 8 videos uploaded to Media service (timestamps: 08:21:28 to 08:25:22)
2. ❌ 0 face detection sessions created in Vision DB
3. ❌ 0 Orchestrator workflows created
4. ❌ 0 individuals created in VMeta
5. ❌ 0 MVR people created
6. ❌ 0 batch processing states created

**Code Investigation** (Camera Service):
```python
# ppl-meta-cameras/src/services/camera_detection.py

# After successful upload:
await self._check_and_trigger_face_detection(media_uuid, session, headers)

async def _check_and_trigger_face_detection(self, media_uuid, session, headers):
    # Step 1: Check Node service for face_detection_on_save setting
    setting_url = f"http://localhost:8001/api/v1/settings/face_detection_on_save"
    
    # Node service has NO settings API endpoint -> returns 404
    # Code defaults to ENABLED on 404 (correct behavior)
    
    # Step 2: Call Orchestrator to trigger face detection
    await self._trigger_face_detection_workflow(media_uuid, session, headers)

async def _trigger_face_detection_workflow(self, media_uuid, session, headers):
    orchestrator_url = f"http://localhost:8002/api/v1/media/{media_uuid}/faces/enhanced-v2"
    
    # THIS IS WHERE THE FAILURE OCCURS
    # Either:
    # a) HTTP request fails silently
    # b) Orchestrator returns error
    # c) Response not logged/visible
```

**Hypothesis**: The `_trigger_face_detection_workflow()` function is either:
- Not being called at all
- HTTP request failing (network/auth issue)
- Orchestrator endpoint returning error
- Exception being caught but not logged

**VMeta Services Status** (Confirmed Working):
- ✅ BatchMonitor initialized in main.py
- ✅ PipelineExecutor created and started  
- ✅ PollingFallbackManager running (30-second interval)
- ✅ Batch processing database tables exist and functional
- ⚠️ **BUT**: All downstream services blocked waiting for face detection prerequisite

### Next Debugging Steps

**Priority 1: Add Detailed Logging to Camera Service**
```python
# Add logging to _trigger_face_detection_workflow():
logger.info(f"🎯 [FACE-DETECTION] Calling: {orchestrator_url}")
logger.info(f"🎯 [FACE-DETECTION] Headers: {headers.keys()}")

async with session.get(orchestrator_url, headers=headers) as response:
    logger.info(f"🎯 [FACE-DETECTION] Status: {response.status}")
    body = await response.text()
    logger.info(f"🎯 [FACE-DETECTION] Body: {body[:500]}")
```

**Priority 2: Test Orchestrator Endpoint Manually**
```bash
# Get auth token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzYzNDUyNDU0fQ.cvaaAgNdoKJLa2IppgZuLSm_t55DKuv4CVlUcW1bKtY"

# Test one of today's videos
VIDEO_UUID="76689b3a-dd5d-4b92-b0e2-fe8f7821dc11"

curl -v "http://localhost:8002/api/v1/media/${VIDEO_UUID}/faces/enhanced-v2" \
  -H "Authorization: Bearer ${TOKEN}"
```

**Priority 3: Check Orchestrator Service Logs**
```bash
# Check if Orchestrator is receiving requests
grep -i "face" logs/ppl-meta-orchestrator.log | tail -50

# Check for errors during 08:21-08:25 timeframe
```

**Priority 4: Verify Vision Service Can Process Videos**
```bash
# Check Vision service health
curl http://localhost:8003/health

# Check available detection methods
curl http://localhost:8003/api/v1/methods
```

### Expected Behavior After Fix

Once face detection triggering is fixed:

1. **Camera Service** uploads video → triggers Orchestrator
2. **Orchestrator** receives request → calls Vision service
3. **Vision Service** detects faces → stores in Vision DB
4. **PollingFallbackManager** polls every 30s → detects new videos with faces
5. **BatchMonitor** counts videos → triggers at batch_size=5
6. **PipelineExecutor** processes batch → creates individuals and MVR people
7. **Flutter UI** displays MVR people count on camera card

---

## Critical Issues Discovered (November 18, 2025 - 12:00 PM)

### Issue Summary

**Two critical bugs preventing pipeline from working:**

1. **Videos uploaded with `user_id: None`** (JWT integer ID vs UUID mismatch)
2. **Batch processing calls non-existent endpoint** (`/api/v1/videos` doesn't exist)

### Issue 1: User ID Attribution (FIXED)

**Root Cause**:
- JWT token contains `"sub": "7"` (integer user ID from Node service)
- Media service expects `user_id: UUID4` format ("4cf362b1-3e05-4e85-81c7-c08a98c7e41b")
- Camera service attempts `UUID("7")` conversion which fails
- Result: Videos uploaded with `user_id: None`

**Why Videos Still Visible**:
- Media `/api/v1/media/search` filters by `MediaCollection.created_by` (collection owner)
- NOT by `Media.uploaded_by` (video user_id)
- Collection owned by user UUID → videos show up despite `user_id: None`

**Fix Implemented** (`ppl-meta-cameras/src/services/camera_detection.py`):
```python
# Lines 2195-2220: Fetch GUID from Node service
if not user_guid and user_id:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8001/api/v1/users/{user_id}"
        )
        if response.status_code == 200:
            user_data = response.json()
            user_guid = user_data.get("guid")

final_user_id = user_guid  # UUID or None
```

### Issue 2: Batch Processing Endpoint (FIXED)

**Root Cause**:
- PipelineExecutor queries: `GET /api/v1/videos`
- This endpoint does not exist in Media service
- Correct endpoint: `GET /api/v1/media/search`

**Fix Implemented** (`ppl-meta-vmeta/src/services/pipeline_executor.py`):
```python
# Lines 477-514: Use correct Media service endpoint
# OLD: url = f"{self.media_service_url}/api/v1/videos"
url = f"{self.media_service_url}/api/v1/media/search"

params = {
    "collection_id": collection_id,
    "date_from": start_time.isoformat(),  # Changed from start_time
    "date_to": end_time.isoformat(),      # Changed from end_time
    "limit": 100
}

# Response is list directly, not wrapped in "videos" key
data = await response.json()
return data if isinstance(data, list) else []
```

### Testing Next Steps

1. **Restart Camera service** to load GUID fetching fix
2. **Restart VMeta service** to load batch processing fix
3. **Record test video** (10-20 seconds)
4. **Verify**:
   - Video has proper UUID user_id (not None)
   - Face detection triggers automatically
   - After 5 videos, batch processing triggers
   - Individuals and MVR people created

---

## Architecture Overview

### High-Level Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│                 CONTINUOUS PIPELINE ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────┘

┌────────────────┐
│ Camera Service │ (Recording Lifecycle - Continuous)
│   Port 8005    │
└────────┬───────┘
         │
         │ Every 30s: Segment recorded & uploaded
         ↓
┌─────────────────────┐
│   Media Service     │ (Video Storage)
│     Port 8000       │
└────────┬────────────┘
         │
         │ Trigger face detection
         ↓
┌─────────────────────┐
│ Vision Service      │ (Face Detection - Parallel, ~60s per segment)
│    Port 8003        │
└────────┬────────────┘
         │
         │ Face detection complete event
         ↓
┌─────────────────────────────────────────────────────────────────┐
│             BATCH MONITORING SERVICE (NEW)                       │
│                  Port 8008 (VMeta)                              │
│                                                                  │
│  Monitors: Face detection completion events per collection      │
│  Tracks:   Video count in current batch                         │
│  Triggers: When batch size X reached → Create tracking session  │
└────────┬────────────────────────────────────────────────────────┘
         │
         │ Batch ready (X videos with face detection complete)
         ↓
┌─────────────────────────────────────────────────────────────────┐
│       INDIVIDUALS & MVR CREATION PIPELINE (NEW)                  │
│                  Port 8008 (VMeta)                              │
│                                                                  │
│  1. Query videos in batch (first X videos in time range)        │
│  2. Check Level 1 Cache: Existing individuals per video         │
│  3. Create new individuals (if cache miss)                      │
│  4. Check Level 2 Cache: Existing MVR people                    │
│  5. Run merge: Create new MVR people                            │
│  6. Store results: Link individuals → MVR people                │
│  7. Update batch status: Mark as processed                      │
└─────────────────────────────────────────────────────────────────┘

✓ Non-blocking: Runs asynchronously in background
✓ Resource isolated: Uses separate worker pool
✓ Cached: Leverages two-level cache architecture
✓ Incremental: Processes batches as they become ready
```

### Service Interaction Diagram

```
Time →
────────────────────────────────────────────────────────────────

Camera Service (Port 8005):
  [Record V1] [Record V2] [Record V3] [Record V4] [Record V5]
      ↓           ↓           ↓           ↓           ↓
      
Vision Service (Port 8003):
  [FD V1─60s] [FD V2─60s] [FD V3─60s] [FD V4─60s] [FD V5─60s]
      ↓           ↓           ↓           ↓           ↓
      
Batch Monitor (Port 8008):
  Count=1     Count=2     Count=3     Count=4     Count=5 → TRIGGER!
                                                      ↓
                                                      
VMeta Pipeline (Port 8008):
                                      [Batch Processing Session]
                                      ├─ Query 5 videos
                                      ├─ Check individual cache
                                      ├─ Create individuals
                                      ├─ Check MVR cache
                                      ├─ Run merge
                                      └─ Create MVR people
                                                      ↓
                                                  [Complete]

─────────────────────────────────────────────────────────────────

Key:
  V1, V2, etc.  = Video segments
  FD            = Face Detection
  Count         = Videos with completed face detection in batch
  TRIGGER       = Batch size X reached, start pipeline
```

---

## Pipeline Components

### 1. Polling Fallback Manager (Recording-Aware)

**Purpose**: Monitors face detection completion during active recordings and triggers batch processing per collection when threshold is reached.

**Location**: `ppl-meta-vmeta/src/services/batch_timeout_manager.py` ✅ **IMPLEMENTED**

**Key Architecture Changes (November 19, 2025)**:

**CRITICAL FIX - Per-Collection Batch Queues**:
```python
# OLD (INCORRECT): Single queue for all collections
self._pending_videos = []  # Mixed videos from all cameras

# NEW (CORRECT): Separate queue per collection
self._pending_videos_by_collection = {
    'usb_camera_0': [video1, video2, video3],
    'usb_camera_1': [video4, video5]
}
```

**Key Responsibilities**:
- ✅ Subscribe to recording start/stop events from Camera Service
- ✅ Poll for new videos ONLY during active recordings
- ✅ Track video count **per collection** in separate queues
- ✅ Trigger pipeline when **each collection** reaches batch_size independently
- ✅ Support multiple simultaneous recordings from different cameras
- ✅ Prevent cross-collection video mixing (CRITICAL)

**Recording-Aware Behavior**:
1. **Recording Start**: Camera sends event → Activates polling for that collection
2. **During Recording**: Polls every 30 seconds → Discovers new videos with faces
3. **Batch Trigger**: Collection reaches batch_size → Triggers processing for THAT collection only
4. **Recording Stop**: Camera sends event → Processes remaining videos for THAT collection
5. **Idle State**: No active recordings → Minimal polling

**Multi-Collection Support**:
```python
# Example: Two cameras recording simultaneously
_active_recordings = {
    'usb_camera_0': {
        'session_uuid': 'abc-123',
        'started_at': datetime(2025, 11, 19, 10, 0, 0),
        'batches_triggered': 2
    },
    'usb_camera_1': {
        'session_uuid': 'def-456',
        'started_at': datetime(2025, 11, 19, 10, 5, 0),
        'batches_triggered': 1
    }
}

_pending_videos_by_collection = {
    'usb_camera_0': [video1, video2, video3],  # 3 pending
    'usb_camera_1': [video4, video5, video6, video7, video8]  # 5 pending → TRIGGER!
}
```

**Database Tables**:
- `batch_processing_state`: Tracks current batch state per collection
- `batch_processing_history`: Audit log of completed batches

**Configuration**:
```python
BATCH_SIZE = 5  # Number of videos per batch (per collection)
POLL_INTERVAL = 30  # Polling interval in seconds
BATCH_TIMEOUT_MINUTES = 10  # Max time to wait for partial batch
MAX_CONCURRENT_BATCHES = 10  # Max batches processing simultaneously
```

**Status Endpoint Response**:
```json
{
  "enabled": true,
  "running": true,
  "batch_size": 5,
  "active_recordings": 2,
  "recordings": {
    "usb_camera_0": {
      "session_uuid": "abc-123",
      "started_at": "2025-11-19T10:00:00Z",
      "batches_triggered": 2,
      "pending_videos": 3
    },
    "usb_camera_1": {
      "session_uuid": "def-456",
      "started_at": "2025-11-19T10:05:00Z",
      "batches_triggered": 1,
      "pending_videos": 5
    }
  },
  "total_pending_videos": 8,
  "pending_by_collection": {
    "usb_camera_0": 3,
    "usb_camera_1": 5
  }
}
```

### 2. Pipeline Executor Service

**Purpose**: Executes the individuals and MVR creation pipeline for ready batches from SINGLE collections.

**Location**: `ppl-meta-vmeta/src/services/pipeline_executor.py` ✅ **IMPLEMENTED**

**Key Responsibilities**:
- ✅ Accept batch processing requests from PollingFallbackManager
- ✅ Query Media Service for videos in batch (from single collection)
- ✅ Execute two-level caching architecture
- ✅ Create individuals and MVR people (collection-scoped)
- ✅ Update batch state and statistics
- ✅ Handle errors and retries

**Per-Collection Processing with Enhanced Logic V2** (November 19, 2025):
```python
async def _trigger_batch_processing(
    self,
    videos_to_process: list,
    is_final: bool = False
):
    """
    Trigger cross-video tracking for videos from SINGLE collection.
    
    CRITICAL: videos_to_process contains videos from ONE collection only.
    The PollingFallbackManager ensures per-collection batching.
    
    NEW (Nov 19): Includes Enhanced Logic V2 integration for person_objects
    """
    # Extract video UUIDs from single collection
    video_uuids = [v['uuid'] for v in videos_to_process]
    
    # All videos are from same collection
    collection = videos_to_process[0]['collection_id']
    
    # OPTIMIZATION: Create tracking session with explicit video_uuids
    # This skips time-range query and directly processes specified videos
    session_data = {
        "collections": [f"{collection} Collection"],
        "start_time": min(v['created_at'] for v in videos_to_process),
        "end_time": max(v['created_at'] for v in videos_to_process),
        "video_uuids": video_uuids,  # NEW: Explicit UUIDs!
        "background_processing": False
    }
    
    # Call cross-video tracking API
    # The API will:
    # 1. Use video_uuids directly (skip time query)
    # 2. Call Enhanced Logic V2 for each video (create person_objects)
    # 3. Run cross-video tracking (create individuals/MVR)
    await client.post(
        f"{self.vmeta_url}/api/v1/cross-video/individuals/tracking/sessions",
        json=session_data
    )
```

**Pipeline Flow (Optimized)**:
```text
┌─────────────────────────────────────────────────────────────┐
│  OPTIMIZED BATCH PROCESSING FLOW (November 19, 2025)        │
└─────────────────────────────────────────────────────────────┘

1. PollingFallbackManager accumulates 5 videos (per collection)
   ↓
2. Sends batch request with explicit video_uuids
   {
     "collections": ["usb_camera_0 Collection"],
     "video_uuids": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"]
   }
   ↓
3. Cross-Video Tracking API receives request
   ↓
4. OPTIMIZATION: Use video_uuids directly (skip time query)
   ↓ Fetch metadata for ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"]
   ↓
5. NEW: Call Enhanced Logic V2 for each video
   ↓ POST /api/v1/media/{uuid1}/faces/enhanced-v2
   ↓ POST /api/v1/media/{uuid2}/faces/enhanced-v2
   ↓ POST /api/v1/media/{uuid3}/faces/enhanced-v2
   ↓ POST /api/v1/media/{uuid4}/faces/enhanced-v2
   ↓ POST /api/v1/media/{uuid5}/faces/enhanced-v2
   ↓ (Creates person_objects from stored_faces)
   ↓
6. Preload person_objects from Orchestrator
   ↓ GET /api/v1/orchestrator/person-objects/{uuid1}
   ↓ GET /api/v1/orchestrator/person-objects/{uuid2}
   ↓ (All videos now have person_objects!)
   ↓
7. Run cross-video tracking
   ↓ Group person_objects by similarity
   ↓ Create individuals
   ↓ Create MVR people
   ↓
8. Complete!
```

**Resource Allocation**:
- ✅ Dedicated asyncio worker pool (separate from API requests)
- ✅ Configurable concurrency limits
- ✅ Memory-bounded processing queues
- ✅ CPU/GPU isolation from other services
- ✅ Parallel processing of multiple collection batches

### 3. Event Subscription Layer (NEW)

**Purpose**: Subscribes to face detection completion events from Orchestrator.

**Location**: `ppl-meta-vmeta/src/services/event_subscriber.py` (to be created)

**Event Sources**:
- Orchestrator Service (Port 8002): Face detection completion events
- Media Service (Port 8000): Video upload completion events (optional)

**Event Format**:
```json
{
  "event_type": "face_detection_complete",
  "media_uuid": "1b4bd00e-...",
  "collection_id": "usb_camera_0",
  "video_start_time": "2025-11-13T10:30:00Z",
  "video_end_time": "2025-11-13T10:30:30Z",
  "face_detection_session_uuid": "a7f3e...",
  "faces_detected": 23,
  "status": "completed",
  "timestamp": "2025-11-13T10:31:45Z"
}
```

---

## Batch Processing Lifecycle

### Phase 1: Accumulation

**Trigger**: Face detection completes for a video in collection

**Process**:
1. Receive face detection completion event
2. Query current batch state for collection
3. Add video to current batch
4. Increment batch counter
5. Check if batch size X reached
   - If YES → Move to Phase 2
   - If NO → Continue accumulating

**Database Operations**:
```sql
-- Update batch state
UPDATE batch_processing_state
SET 
  video_count = video_count + 1,
  last_video_uuid = $1,
  last_video_end_time = $2,
  updated_at = NOW()
WHERE collection_id = $3
  AND status = 'accumulating';

-- Check if batch ready
SELECT video_count >= batch_size_threshold AS ready
FROM batch_processing_state
WHERE collection_id = $1
  AND status = 'accumulating';
```

### Phase 2: Pipeline Execution

**Trigger**: Batch size X reached

**Process**:
```
1. Mark batch as 'processing'
   └─ Prevents duplicate processing

2. Calculate time range
   ├─ start_time = earliest video start time in batch
   └─ end_time = latest video end time in batch

3. Query videos from Media Service
   └─ GET /api/v1/media/search?collection={id}&start={start}&end={end}

4. Create tracking session
   └─ POST /api/v1/cross-video/individuals/tracking/sessions
      Body: {
        "collections": ["usb_camera_0"],
        "start_time": "2025-11-13T10:00:00Z",
        "end_time": "2025-11-13T10:02:30Z",
        "auto_process": true,
        "batch_mode": true,
        "batch_uuid": "batch-uuid-..."
      }

5. Execute two-level caching architecture
   ├─ Level 1: Check existing individuals per video
   ├─ Create new individuals (if needed)
   ├─ Level 2: Check existing MVR people
   └─ Run merge to create new MVR people

6. Store results
   ├─ Link individuals to MVR people
   ├─ Update individual_mvr_mapping table
   └─ Store embeddings in mvr_people table

7. Update batch state
   ├─ Status: 'completed'
   ├─ Statistics: individuals_created, mvr_created, cache_hits
   └─ Processing time
```

**Key Implementation**:
```python
async def execute_batch_pipeline(
    batch_uuid: str,
    collection_id: str,
    video_uuids: List[str],
    start_time: datetime,
    end_time: datetime
) -> Dict:
    """Execute pipeline for batch of videos."""
    
    logger.info(
        f"[BATCH PIPELINE] Starting batch {batch_uuid[:8]} "
        f"with {len(video_uuids)} videos"
    )
    
    try:
        # Create tracking session for batch
        session_data = {
            "collections": [collection_id],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "batch_mode": True,
            "batch_uuid": batch_uuid
        }
        
        # Execute existing cross-video tracking logic
        session_response = await create_tracking_session(
            session_data=session_data,
            db_client=db_client
        )
        
        session_uuid = session_response['session_uuid']
        
        # Wait for session to complete
        result = await wait_for_session_completion(
            session_uuid=session_uuid,
            timeout_seconds=300  # 5 minutes
        )
        
        # Update batch state
        await update_batch_state(
            batch_uuid=batch_uuid,
            status='completed',
            session_uuid=session_uuid,
            individuals_created=result['individuals_created'],
            mvr_created=result['mvr_people_created'],
            cache_hits=result['cache_hits'],
            processing_time_seconds=result['processing_time']
        )
        
        logger.info(
            f"[BATCH PIPELINE] Completed batch {batch_uuid[:8]}: "
            f"{result['individuals_created']} individuals, "
            f"{result['mvr_people_created']} MVR people"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[BATCH PIPELINE] Failed batch {batch_uuid[:8]}: {e}")
        await update_batch_state(
            batch_uuid=batch_uuid,
            status='failed',
            error_message=str(e)
        )
        raise
```

### Phase 3: Cleanup and Next Batch

**Trigger**: Batch processing completes

**Process**:
1. Mark batch as 'completed' or 'failed'
2. Log statistics and metrics
3. Create new batch for collection
4. Reset counter to 0
5. Continue monitoring for next batch

**Database Operations**:
```sql
-- Mark batch complete
UPDATE batch_processing_state
SET 
  status = 'completed',
  session_uuid = $1,
  individuals_created = $2,
  mvr_people_created = $3,
  cache_hits = $4,
  processing_time_seconds = $5,
  completed_at = NOW()
WHERE batch_uuid = $6;

-- Create new batch for collection
INSERT INTO batch_processing_state (
  batch_uuid,
  collection_id,
  status,
  video_count,
  batch_size_threshold,
  created_at
) VALUES (
  gen_random_uuid(),
  $1,
  'accumulating',
  0,
  $2,
  NOW()
);
```

---

## Trigger Mechanisms

### 1. Event-Based Triggering (Primary)

**Mechanism**: Subscribe to face detection completion events from Orchestrator

**Advantages**:
- Real-time responsiveness
- No polling overhead
- Exact batch boundaries
- Minimal latency

**Implementation**:
```python
class FaceDetectionEventSubscriber:
    """Subscribes to face detection completion events."""
    
    def __init__(self, batch_monitor: BatchMonitor):
        self.batch_monitor = batch_monitor
        self.orchestrator_url = "http://localhost:8002"
    
    async def subscribe(self):
        """Subscribe to orchestrator events via WebSocket or SSE."""
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"{self.orchestrator_url}/api/v1/events/face-detection"
            ) as ws:
                async for msg in ws:
                    event = json.loads(msg.data)
                    
                    if event['event_type'] == 'face_detection_complete':
                        await self.handle_completion(event)
    
    async def handle_completion(self, event: Dict):
        """Handle face detection completion event."""
        
        await self.batch_monitor.add_video_to_batch(
            collection_id=event['collection_id'],
            video_uuid=event['media_uuid'],
            start_time=event['video_start_time'],
            end_time=event['video_end_time']
        )
```

### 2. Polling-Based Triggering (Fallback)

**Mechanism**: Periodically poll for videos with completed face detection

**Advantages**:
- Works without event infrastructure
- Resilient to event delivery failures
- Simple implementation

**Implementation**:
```python
async def poll_for_completed_videos(
    collection_id: str,
    last_check: datetime
) -> List[Dict]:
    """Poll for videos with completed face detection."""
    
    # Query Vision Service for completed sessions
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"http://localhost:8003/api/v1/face-detection/sessions",
            params={
                "status": "completed",
                "collection_id": collection_id,
                "completed_after": last_check.isoformat()
            }
        )
        
        sessions = await response.json()
        
        # Extract video UUIDs
        videos = [
            {
                "video_uuid": s['media_uuid'],
                "start_time": s['video_start_time'],
                "end_time": s['video_end_time']
            }
            for s in sessions
        ]
        
        return videos

# Run poller every 30 seconds
async def run_poller():
    last_check = datetime.utcnow() - timedelta(minutes=5)
    
    while True:
        for collection_id in active_collections:
            videos = await poll_for_completed_videos(
                collection_id=collection_id,
                last_check=last_check
            )
            
            for video in videos:
                await batch_monitor.add_video_to_batch(
                    collection_id=collection_id,
                    video_uuid=video['video_uuid'],
                    start_time=video['start_time'],
                    end_time=video['end_time']
                )
        
        last_check = datetime.utcnow()
        await asyncio.sleep(30)
```

### 3. Manual Triggering (Development/Testing)

**Mechanism**: API endpoint to manually trigger batch processing

**Endpoint**: `POST /api/v1/batch-processing/trigger`

**Request**:
```json
{
  "collection_id": "usb_camera_0",
  "force_trigger": true,
  "min_videos": 3
}
```

**Response**:
```json
{
  "batch_uuid": "f7a9e3b2-...",
  "collection_id": "usb_camera_0",
  "video_count": 3,
  "status": "processing",
  "triggered_at": "2025-11-13T10:30:00Z"
}
```

---

## Handling Partial Batches (Remaining Videos)

### Problem Statement

When a recording session ends, there may be videos that haven't reached the batch size threshold. For example:
- Batch size = 5
- Last complete batch processed videos 1-5
- Recording stops after video 8
- **Result**: Videos 6, 7, 8 remain unprocessed (partial batch of 3 videos)

### Solution Strategies

#### Strategy 1: Timeout-Based Auto-Trigger (RECOMMENDED)

**Description**: Automatically trigger batch processing if no new videos arrive within a timeout period.

**Configuration**:
```yaml
batch_processing:
  batch_size_threshold: 5
  partial_batch_timeout_minutes: 5  # Trigger after 5 minutes of inactivity
  min_partial_batch_size: 2  # Minimum videos to process as partial batch
```

**Logic**:
```python
class BatchMonitor:
    async def monitor_batch_timeout(self, collection_id: str):
        """Monitor batch for timeout and trigger if inactive."""
        
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            batch = await get_active_batch(collection_id)
            
            if not batch or batch['status'] != 'accumulating':
                continue
            
            # Check time since last video added
            time_since_last = datetime.utcnow() - batch['last_video_time']
            
            if time_since_last.total_seconds() > TIMEOUT_SECONDS:
                video_count = batch['video_count']
                min_size = batch.get('min_partial_batch_size', 2)
                
                if video_count >= min_size:
                    logger.info(
                        f"[TIMEOUT TRIGGER] Batch {batch['batch_uuid'][:8]} "
                        f"inactive for {time_since_last.total_seconds():.0f}s, "
                        f"triggering with {video_count} videos"
                    )
                    
                    await trigger_batch_processing(
                        batch_uuid=batch['batch_uuid'],
                        reason='timeout'
                    )
                else:
                    logger.warning(
                        f"[TIMEOUT SKIP] Batch {batch['batch_uuid'][:8]} "
                        f"has only {video_count} videos (min: {min_size}), "
                        f"skipping processing"
                    )
```

**Advantages**:
- ✅ Fully automatic - no manual intervention
- ✅ Handles recording stops gracefully
- ✅ Configurable timeout period
- ✅ Prevents indefinite waiting

**Disadvantages**:
- ❌ Adds latency (wait for timeout before processing)
- ❌ May trigger false positives during slow recording periods

**Timing Example**:
```
10:00:00  Recording starts
10:00:30  Video 1 → Batch count = 1
10:01:00  Video 2 → Batch count = 2
...
10:02:30  Video 5 → Batch count = 5 → TRIGGER (normal batch)
10:03:00  Video 6 → New batch, count = 1
10:03:30  Video 7 → Batch count = 2
10:04:00  Video 8 → Batch count = 3
10:04:15  Recording STOPS (user action)
10:09:00  No new videos for 5 minutes → TIMEOUT TRIGGER (partial batch)
          Process videos 6, 7, 8
```

#### Strategy 2: Recording Stop Event Trigger

**Description**: Subscribe to recording session stop events and immediately trigger batch processing for remaining videos.

**Event Source**: Camera Service (Port 8005) publishes recording stop events

**Event Format**:
```json
{
  "event_type": "recording_session_stopped",
  "session_uuid": "abc123...",
  "collection_id": "usb_camera_0",
  "stopped_at": "2025-11-13T10:04:15Z",
  "total_videos": 8,
  "reason": "user_stopped"
}
```

**Implementation**:
```python
class RecordingStopEventHandler:
    async def handle_recording_stop(self, event: Dict):
        """Handle recording stop event - trigger partial batch if needed."""
        
        collection_id = event['collection_id']
        
        # Get current batch state
        batch = await get_active_batch(collection_id)
        
        if not batch or batch['status'] != 'accumulating':
            logger.info(f"[RECORDING STOP] No active batch for {collection_id}")
            return
        
        video_count = batch['video_count']
        min_size = batch.get('min_partial_batch_size', 2)
        
        if video_count >= min_size:
            logger.info(
                f"[RECORDING STOP] Triggering partial batch for {collection_id} "
                f"with {video_count} remaining videos"
            )
            
            await trigger_batch_processing(
                batch_uuid=batch['batch_uuid'],
                reason='recording_stopped',
                is_partial_batch=True
            )
        else:
            logger.warning(
                f"[RECORDING STOP] Skipping partial batch: "
                f"only {video_count} videos (min: {min_size})"
            )
            
            # Mark batch as 'incomplete' for manual review
            await update_batch_state(
                batch_uuid=batch['batch_uuid'],
                status='incomplete',
                note=f'Recording stopped with insufficient videos ({video_count})'
            )
```

**Advantages**:
- ✅ Immediate processing (no timeout wait)
- ✅ Direct correlation with recording lifecycle
- ✅ Clean batch boundaries

**Disadvantages**:
- ❌ Requires integration with Camera Service events
- ❌ May trigger prematurely if recording pauses temporarily

**Timing Example**:
```
10:00:00  Recording starts
10:00:30  Video 1 → Batch count = 1
...
10:02:30  Video 5 → Batch count = 5 → TRIGGER (normal batch)
10:03:00  Video 6 → New batch, count = 1
10:03:30  Video 7 → Batch count = 2
10:04:00  Video 8 → Batch count = 3
10:04:15  Recording STOPS → IMMEDIATE TRIGGER
          Process videos 6, 7, 8 (no timeout wait)
```

#### Strategy 3: Hybrid Approach (BEST PRACTICE)

**Description**: Combine both strategies - use recording stop events as primary trigger, with timeout as fallback.

**Configuration**:
```yaml
batch_processing:
  batch_size_threshold: 5
  
  partial_batch_handling:
    # Primary: Recording stop event
    recording_stop_trigger_enabled: true
    min_partial_batch_size: 2
    
    # Fallback: Timeout
    timeout_trigger_enabled: true
    partial_batch_timeout_minutes: 10
    
    # Safeguard: Maximum wait time
    max_accumulation_hours: 24  # Force trigger after 24 hours regardless
```

**Implementation**:
```python
class HybridBatchTrigger:
    def __init__(self):
        self.timeout_tasks = {}  # collection_id -> asyncio.Task
    
    async def on_video_added(self, collection_id: str):
        """Called when video added to batch."""
        
        batch = await get_active_batch(collection_id)
        
        # Check normal batch size trigger
        if batch['video_count'] >= batch['batch_size_threshold']:
            await trigger_batch_processing(batch['batch_uuid'], reason='threshold')
            return
        
        # Start/reset timeout task
        await self.start_timeout_task(collection_id, batch['batch_uuid'])
    
    async def on_recording_stopped(self, collection_id: str):
        """Called when recording session stops."""
        
        # Cancel timeout task (we'll trigger immediately if needed)
        await self.cancel_timeout_task(collection_id)
        
        batch = await get_active_batch(collection_id)
        
        if batch and batch['video_count'] >= batch['min_partial_batch_size']:
            await trigger_batch_processing(
                batch['batch_uuid'],
                reason='recording_stopped'
            )
    
    async def start_timeout_task(self, collection_id: str, batch_uuid: str):
        """Start timeout monitoring task."""
        
        # Cancel existing task if any
        await self.cancel_timeout_task(collection_id)
        
        # Create new timeout task
        task = asyncio.create_task(
            self.timeout_handler(collection_id, batch_uuid)
        )
        self.timeout_tasks[collection_id] = task
    
    async def timeout_handler(self, collection_id: str, batch_uuid: str):
        """Wait for timeout and trigger if needed."""
        
        try:
            await asyncio.sleep(TIMEOUT_SECONDS)
            
            batch = await get_active_batch(collection_id)
            
            # Verify batch still exists and is accumulating
            if batch and batch['batch_uuid'] == batch_uuid:
                if batch['video_count'] >= batch['min_partial_batch_size']:
                    await trigger_batch_processing(
                        batch_uuid=batch_uuid,
                        reason='timeout'
                    )
        except asyncio.CancelledError:
            # Task cancelled (recording stopped or new video added)
            pass
    
    async def cancel_timeout_task(self, collection_id: str):
        """Cancel timeout task for collection."""
        
        task = self.timeout_tasks.get(collection_id)
        if task and not task.done():
            task.cancel()
```

**Advantages**:
- ✅ Immediate processing when recording stops (recording stop event)
- ✅ Fallback protection if event is missed (timeout)
- ✅ Handles both explicit stops and implicit timeouts
- ✅ Most robust approach

**Disadvantages**:
- ❌ More complex implementation
- ❌ Requires event infrastructure

**Timing Example**:
```
Normal case (recording stop event works):
10:04:00  Video 8 → Batch count = 3
10:04:15  Recording STOPS → Event received → IMMEDIATE TRIGGER
          Process videos 6, 7, 8

Fallback case (event missed or recording crashes):
10:04:00  Video 8 → Batch count = 3
10:04:15  Recording STOPS → Event NOT received
10:14:00  Timeout (10 minutes) → TIMEOUT TRIGGER
          Process videos 6, 7, 8
```

#### Strategy 4: Manual Trigger API

**Description**: Provide API endpoint for operators to manually trigger partial batch processing.

**Endpoint**: `POST /api/v1/batch-processing/trigger`

**Use Case**: Development, testing, or manual recovery scenarios

**Request**:
```json
{
  "collection_id": "usb_camera_0",
  "force_trigger": true,
  "allow_partial": true,
  "min_videos": 1
}
```

**Advantages**:
- ✅ Full operator control
- ✅ Useful for debugging
- ✅ No automatic logic needed

**Disadvantages**:
- ❌ Requires manual intervention
- ❌ Not suitable for production automation

### Recommended Configuration

```yaml
batch_processing:
  # Normal batch size
  batch_size_threshold: 5
  
  # Partial batch handling (HYBRID approach)
  partial_batch:
    # Primary trigger: Recording stop event
    recording_stop_trigger:
      enabled: true
      min_videos: 2  # Process if at least 2 videos remain
      immediate_trigger: true
    
    # Fallback trigger: Timeout
    timeout_trigger:
      enabled: true
      timeout_minutes: 10
      min_videos: 2
    
    # Safeguard: Force trigger
    max_wait:
      enabled: true
      max_hours: 24
      min_videos: 1  # Process even single video after 24 hours
  
  # Collection-specific overrides
  collections:
    usb_camera_0:
      batch_size_threshold: 5
      partial_batch_min_videos: 2
    usb_camera_1:
      batch_size_threshold: 10
      partial_batch_min_videos: 3  # Higher threshold for busy camera
```

### Database Schema Updates

**Add fields to `batch_processing_state` table**:

```sql
ALTER TABLE batch_processing_state
ADD COLUMN is_partial_batch BOOLEAN DEFAULT FALSE,
ADD COLUMN trigger_reason VARCHAR(50),  -- 'threshold', 'timeout', 'recording_stopped', 'manual'
ADD COLUMN last_video_time TIMESTAMP,  -- Time when last video was added
ADD COLUMN timeout_at TIMESTAMP;  -- When timeout trigger should fire

-- Index for timeout monitoring
CREATE INDEX idx_batch_timeout 
ON batch_processing_state(collection_id, timeout_at)
WHERE status = 'accumulating' AND timeout_at IS NOT NULL;
```

### Monitoring Partial Batches

**Metrics**:
```python
# Counter: Partial batches triggered
partial_batches_total = Counter(
    'partial_batches_total',
    'Total partial batches processed',
    ['collection_id', 'trigger_reason']
)

# Histogram: Partial batch sizes
partial_batch_size = Histogram(
    'partial_batch_size',
    'Number of videos in partial batches',
    ['collection_id'],
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
)

# Gauge: Incomplete batches waiting
incomplete_batches_waiting = Gauge(
    'incomplete_batches_waiting',
    'Number of incomplete batches waiting for more videos',
    ['collection_id']
)
```

**API Endpoint for Incomplete Batches**:

`GET /api/v1/batch-processing/incomplete`

**Response**:
```json
{
  "incomplete_batches": [
    {
      "batch_uuid": "f7a9e3b2-...",
      "collection_id": "usb_camera_0",
      "video_count": 3,
      "batch_size_threshold": 5,
      "last_video_time": "2025-11-13T10:04:00Z",
      "waiting_minutes": 15,
      "timeout_at": "2025-11-13T10:14:00Z",
      "can_trigger_now": true
    }
  ]
}
```

### Summary

**Recommended Approach**: **Hybrid Strategy (Strategy 3)**

1. **Primary**: Recording stop event → Immediate trigger
2. **Fallback**: Timeout (10 minutes) → Automatic trigger
3. **Safeguard**: Max wait (24 hours) → Force trigger
4. **Manual**: API endpoint → Operator control

**Configuration**:
- Minimum partial batch size: 2 videos
- Timeout: 10 minutes
- Max wait: 24 hours

**Example Flow**:
```
Recording: 8 videos total
Batch 1: Videos 1-5 → Triggered at video 5 (threshold)
Batch 2: Videos 6-8 → Partial batch (3 videos)
Trigger: Recording stops → Immediate processing (recording_stopped event)
Fallback: If event missed → Timeout after 10 minutes
Result: All 8 videos processed with minimal delay
```

---

## Resource Management

### Dedicated Worker Pool

**Purpose**: Isolate batch processing from API requests and other services

**Configuration**:
```python
class BatchProcessingWorkerPool:
    """Dedicated worker pool for batch processing."""
    
    def __init__(
        self,
        max_workers: int = 3,
        max_queue_size: int = 10
    ):
        self.max_workers = max_workers
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.workers = []
        self.active_batches = {}
    
    async def start(self):
        """Start worker pool."""
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
    
    async def _worker(self, worker_id: int):
        """Worker coroutine."""
        logger.info(f"[WORKER {worker_id}] Started")
        
        while True:
            try:
                batch_task = await self.queue.get()
                
                logger.info(
                    f"[WORKER {worker_id}] Processing batch "
                    f"{batch_task['batch_uuid'][:8]}"
                )
                
                result = await execute_batch_pipeline(**batch_task)
                
                logger.info(
                    f"[WORKER {worker_id}] Completed batch "
                    f"{batch_task['batch_uuid'][:8]}"
                )
                
            except Exception as e:
                logger.error(f"[WORKER {worker_id}] Error: {e}")
            
            finally:
                self.queue.task_done()
    
    async def submit_batch(self, batch_task: Dict):
        """Submit batch for processing."""
        await self.queue.put(batch_task)
```

### Resource Limits

**CPU**:
- Batch processing: 30-40% CPU (separate from API)
- Embedding computation: GPU-accelerated (if available)
- Merge computation: Parallel processing with thread pool

**Memory**:
- Per-batch limit: 2GB
- Total pool limit: 6GB (3 workers × 2GB)
- Video data: Streamed from Media Service (not cached in memory)

**Network**:
- Batch query to Media Service: 1 request per batch
- Orchestrator call: 1 request per video (individual creation)
- Vision Service query: Cached embeddings (no network for cached individuals)

**Concurrency**:
- Max concurrent batches: 3 (configurable)
- Max videos per batch: 10 (configurable)
- Max tracking session time: 5 minutes

---

## Database Schema

### Table: `batch_processing_state`

**Purpose**: Tracks current state of batch accumulation per collection

```sql
CREATE TABLE batch_processing_state (
    -- Primary key
    batch_uuid                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Batch identification
    collection_id               VARCHAR(255) NOT NULL,
    batch_number                INTEGER NOT NULL,  -- Sequential number per collection
    
    -- Status tracking
    status                      VARCHAR(50) NOT NULL,  -- accumulating, processing, completed, failed
    video_count                 INTEGER NOT NULL DEFAULT 0,
    batch_size_threshold        INTEGER NOT NULL DEFAULT 5,
    
    -- Time tracking
    first_video_start_time      TIMESTAMP,
    last_video_end_time         TIMESTAMP,
    triggered_at                TIMESTAMP,
    completed_at                TIMESTAMP,
    
    -- Processing results
    session_uuid                UUID,  -- Tracking session UUID
    individuals_created         INTEGER DEFAULT 0,
    individuals_cached          INTEGER DEFAULT 0,
    mvr_people_created          INTEGER DEFAULT 0,
    mvr_people_cached           INTEGER DEFAULT 0,
    processing_time_seconds     DOUBLE PRECISION,
    
    -- Error handling
    error_message               TEXT,
    retry_count                 INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at                  TIMESTAMP DEFAULT NOW(),
    updated_at                  TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_status CHECK (
        status IN ('accumulating', 'processing', 'completed', 'failed')
    ),
    CONSTRAINT check_video_count CHECK (video_count >= 0)
);

-- Indexes
CREATE INDEX idx_batch_processing_state_collection 
    ON batch_processing_state(collection_id, status);

CREATE INDEX idx_batch_processing_state_status 
    ON batch_processing_state(status)
    WHERE status IN ('accumulating', 'processing');

CREATE UNIQUE INDEX idx_batch_processing_state_active 
    ON batch_processing_state(collection_id)
    WHERE status = 'accumulating';
```

### Table: `batch_video_assignments`

**Purpose**: Tracks which videos belong to which batch

```sql
CREATE TABLE batch_video_assignments (
    -- Primary key
    id                          SERIAL PRIMARY KEY,
    
    -- References
    batch_uuid                  UUID NOT NULL REFERENCES batch_processing_state(batch_uuid),
    video_uuid                  UUID NOT NULL,
    collection_id               VARCHAR(255) NOT NULL,
    
    -- Video metadata
    video_start_time            TIMESTAMP NOT NULL,
    video_end_time              TIMESTAMP NOT NULL,
    face_detection_session_uuid UUID,
    faces_detected              INTEGER,
    
    -- Assignment metadata
    added_at                    TIMESTAMP DEFAULT NOW(),
    sequence_number             INTEGER NOT NULL,  -- Order within batch
    
    -- Constraints
    UNIQUE(batch_uuid, video_uuid)
);

-- Indexes
CREATE INDEX idx_batch_video_assignments_batch 
    ON batch_video_assignments(batch_uuid);

CREATE INDEX idx_batch_video_assignments_video 
    ON batch_video_assignments(video_uuid);

CREATE INDEX idx_batch_video_assignments_collection 
    ON batch_video_assignments(collection_id, video_start_time);
```

### Table: `batch_processing_history`

**Purpose**: Audit log of all completed batches

```sql
CREATE TABLE batch_processing_history (
    -- Primary key
    id                          SERIAL PRIMARY KEY,
    
    -- References
    batch_uuid                  UUID NOT NULL,
    collection_id               VARCHAR(255) NOT NULL,
    
    -- Batch summary
    video_count                 INTEGER NOT NULL,
    individuals_created         INTEGER NOT NULL,
    individuals_cached          INTEGER NOT NULL,
    mvr_people_created          INTEGER NOT NULL,
    mvr_people_cached           INTEGER NOT NULL,
    
    -- Performance metrics
    processing_time_seconds     DOUBLE PRECISION NOT NULL,
    cache_hit_rate              DOUBLE PRECISION,  -- Percentage
    throughput_videos_per_sec   DOUBLE PRECISION,
    
    -- Time range
    batch_start_time            TIMESTAMP NOT NULL,
    batch_end_time              TIMESTAMP NOT NULL,
    
    -- Processing metadata
    session_uuid                UUID,
    status                      VARCHAR(50) NOT NULL,
    error_message               TEXT,
    
    -- Timestamps
    created_at                  TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_batch_processing_history_collection 
    ON batch_processing_history(collection_id, created_at DESC);

CREATE INDEX idx_batch_processing_history_status 
    ON batch_processing_history(status)
    WHERE status = 'failed';
```

---

## API Endpoints

### 1. Get Batch Status

**Endpoint**: `GET /api/v1/batch-processing/status`

**Query Parameters**:
- `collection_id` (optional): Filter by collection

**Response**:
```json
{
  "batches": [
    {
      "batch_uuid": "f7a9e3b2-...",
      "collection_id": "usb_camera_0",
      "status": "accumulating",
      "video_count": 3,
      "batch_size_threshold": 5,
      "progress_percentage": 60.0,
      "first_video_start_time": "2025-11-13T10:00:00Z",
      "last_video_end_time": "2025-11-13T10:01:30Z",
      "created_at": "2025-11-13T10:00:05Z"
    },
    {
      "batch_uuid": "e3c2d8a1-...",
      "collection_id": "usb_camera_1",
      "status": "processing",
      "video_count": 5,
      "batch_size_threshold": 5,
      "progress_percentage": 100.0,
      "session_uuid": "a7f3e9b2-...",
      "triggered_at": "2025-11-13T10:02:00Z"
    }
  ]
}
```

### 2. Get Batch History

**Endpoint**: `GET /api/v1/batch-processing/history`

**Query Parameters**:
- `collection_id` (optional): Filter by collection
- `limit` (default: 50): Number of results
- `offset` (default: 0): Pagination offset

**Response**:
```json
{
  "total": 127,
  "limit": 50,
  "offset": 0,
  "history": [
    {
      "batch_uuid": "d2b1a9e3-...",
      "collection_id": "usb_camera_0",
      "status": "completed",
      "video_count": 5,
      "individuals_created": 12,
      "individuals_cached": 3,
      "mvr_people_created": 2,
      "mvr_people_cached": 1,
      "processing_time_seconds": 45.3,
      "cache_hit_rate": 20.0,
      "batch_start_time": "2025-11-13T09:00:00Z",
      "batch_end_time": "2025-11-13T09:02:30Z",
      "session_uuid": "c8e4f7a2-...",
      "created_at": "2025-11-13T09:03:15Z"
    }
  ]
}
```

### 3. Trigger Batch Processing

**Endpoint**: `POST /api/v1/batch-processing/trigger`

**Request**:
```json
{
  "collection_id": "usb_camera_0",
  "force_trigger": true,
  "min_videos": 3
}
```

**Response**:
```json
{
  "batch_uuid": "f7a9e3b2-...",
  "collection_id": "usb_camera_0",
  "status": "processing",
  "video_count": 3,
  "triggered_at": "2025-11-13T10:30:00Z",
  "message": "Batch processing triggered successfully"
}
```

### 4. Get Batch Configuration

**Endpoint**: `GET /api/v1/batch-processing/config`

**Response**:
```json
{
  "batch_size_threshold": 5,
  "batch_timeout_minutes": 60,
  "max_concurrent_batches": 3,
  "event_triggering_enabled": true,
  "polling_interval_seconds": 30,
  "worker_pool_size": 3
}
```

### 5. Update Batch Configuration

**Endpoint**: `PUT /api/v1/batch-processing/config`

**Description**: Update batch processing configuration including batch size threshold, timeouts, and concurrency limits.

**Request**:
```json
{
  "batch_size_threshold": 10,
  "batch_timeout_minutes": 120,
  "max_concurrent_batches": 5
}
```

**Response**:
```json
{
  "message": "Configuration updated successfully",
  "config": {
    "batch_size_threshold": 10,
    "batch_timeout_minutes": 120,
    "max_concurrent_batches": 5
  },
  "effective_at": "2025-11-13T10:30:00Z"
}
```

### 6. Update Batch Size (Quick Setting)

**Endpoint**: `PUT /api/v1/batch-processing/batch-size`

**Description**: Quick endpoint to update the number of videos per batch without changing other configuration. This is the primary setting for controlling batch processing frequency.

**Request**:
```json
{
  "batch_size": 10,
  "collection_id": "usb_camera_0"  // Optional: set for specific collection
}
```

**Parameters**:
- `batch_size` (required, integer): Number of videos per batch (min: 2, max: 50)
- `collection_id` (optional, string): Apply to specific collection only. If omitted, updates global default.

**Response**:
```json
{
  "message": "Batch size updated successfully",
  "batch_size": 10,
  "collection_id": "usb_camera_0",
  "scope": "collection",  // or "global"
  "previous_batch_size": 5,
  "effective_at": "2025-11-13T10:30:00Z",
  "current_batch_status": {
    "video_count": 3,
    "will_trigger_at": 10,
    "estimated_trigger_time": "2025-11-13T10:45:00Z"
  }
}
```

**Global Update Example**:
```bash
curl -X PUT http://localhost:8008/api/v1/batch-processing/batch-size \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "batch_size": 10
  }'
```

**Collection-Specific Update Example**:
```bash
curl -X PUT http://localhost:8008/api/v1/batch-processing/batch-size \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "batch_size": 7,
    "collection_id": "usb_camera_0"
  }'
```

**Error Responses**:

- **400 Bad Request** (invalid batch size):
```json
{
  "error": "Invalid batch size",
  "message": "Batch size must be between 2 and 50",
  "provided_value": 100
}
```

- **404 Not Found** (collection not found):
```json
{
  "error": "Collection not found",
  "message": "Collection 'usb_camera_unknown' does not exist",
  "collection_id": "usb_camera_unknown"
}
```

**Implementation Notes**:

1. **Immediate Effect**: Changes take effect immediately for new videos added to batch
2. **In-Progress Batches**: Existing batches in 'accumulating' status are updated with new threshold
3. **Processing Batches**: Batches already 'processing' are not affected
4. **Validation**: Batch size must be between 2 and 50 videos
5. **Persistence**: Setting is stored in database and survives service restarts

**Database Update**:
```sql
-- Update global default
UPDATE batch_processing_config
SET batch_size_threshold = $1
WHERE collection_id IS NULL;

-- Update collection-specific
UPDATE batch_processing_config
SET batch_size_threshold = $1
WHERE collection_id = $2;

-- Update active accumulating batches
UPDATE batch_processing_state
SET batch_size_threshold = $1
WHERE collection_id = $2
  AND status = 'accumulating';
```

---

## Configuration

### Environment Variables

```bash
# Batch Processing Configuration
BATCH_SIZE_THRESHOLD=5                    # Videos per batch
BATCH_TIMEOUT_MINUTES=60                  # Max accumulation time
MAX_CONCURRENT_BATCHES=3                  # Parallel processing limit

# Resource Limits
WORKER_POOL_SIZE=3                        # Dedicated workers
MAX_BATCH_MEMORY_GB=2                     # Per-batch memory limit
MAX_BATCH_PROCESSING_TIME_SECONDS=300     # 5 minutes

# Event Configuration
EVENT_TRIGGERING_ENABLED=true             # Use event-based triggering
POLLING_INTERVAL_SECONDS=30               # Fallback polling interval
ORCHESTRATOR_EVENT_URL=http://localhost:8002/api/v1/events/face-detection

# Monitoring
BATCH_METRICS_ENABLED=true                # Enable Prometheus metrics
BATCH_LOGGING_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
```

### Configuration File

**Location**: `ppl-meta-vmeta/config/batch_processing.yml`

```yaml
batch_processing:
  # Batch sizing
  default_batch_size: 5
  min_batch_size: 2
  max_batch_size: 20
  
  # Timeouts
  batch_timeout_minutes: 60
  session_timeout_minutes: 5
  
  # Concurrency
  max_concurrent_batches: 3
  worker_pool_size: 3
  
  # Resource limits
  max_batch_memory_gb: 2
  max_videos_per_session: 10
  
  # Triggering
  event_triggering:
    enabled: true
    orchestrator_url: "http://localhost:8002"
    event_endpoint: "/api/v1/events/face-detection"
    reconnect_interval_seconds: 5
  
  polling_fallback:
    enabled: true
    interval_seconds: 30
    lookback_minutes: 5
  
  # Cache configuration
  caching:
    level_1_enabled: true  # Individual cache
    level_2_enabled: true  # MVR cache
    session_wide_cache_enabled: true
  
  # Collection-specific overrides
  collections:
    usb_camera_0:
      batch_size: 5
      priority: high
    usb_camera_1:
      batch_size: 10
      priority: normal
```

---

## Monitoring and Observability

### Metrics (Prometheus)

```python
# Counter: Total batches processed
batch_processing_total = Counter(
    'batch_processing_total',
    'Total number of batches processed',
    ['collection_id', 'status']
)

# Gauge: Current batch size
batch_current_size = Gauge(
    'batch_current_size',
    'Current number of videos in accumulating batch',
    ['collection_id']
)

# Histogram: Batch processing duration
batch_processing_duration_seconds = Histogram(
    'batch_processing_duration_seconds',
    'Time to process batch',
    ['collection_id'],
    buckets=[10, 30, 60, 120, 300]
)

# Counter: Individuals created
individuals_created_total = Counter(
    'individuals_created_total',
    'Total individuals created',
    ['collection_id', 'source']  # source: new, cached
)

# Counter: MVR people created
mvr_people_created_total = Counter(
    'mvr_people_created_total',
    'Total MVR people created',
    ['collection_id', 'source']  # source: new, cached
)

# Gauge: Cache hit rate
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Percentage of cache hits',
    ['collection_id', 'cache_level']  # level: individual, mvr
)
```

### Logging

```python
import logging

logger = logging.getLogger('batch_processing')

# Log batch trigger
logger.info(
    f"[BATCH TRIGGER] Batch {batch_uuid[:8]} triggered for "
    f"collection {collection_id} with {video_count} videos"
)

# Log cache hit
logger.debug(
    f"[CACHE HIT] Individual cache hit for video {video_uuid[:8]}: "
    f"{cached_count} individuals reused"
)

# Log MVR creation
logger.info(
    f"[MVR CREATED] Created {mvr_count} MVR people from "
    f"{individual_count} individuals"
)

# Log batch completion
logger.info(
    f"[BATCH COMPLETE] Batch {batch_uuid[:8]} completed in "
    f"{duration:.1f}s: {individuals_created} individuals, "
    f"{mvr_created} MVR people, {cache_hit_rate:.1f}% cache hit rate"
)
```

### Health Checks

**Endpoint**: `GET /api/v1/batch-processing/health`

**Response**:
```json
{
  "status": "healthy",
  "worker_pool": {
    "active_workers": 3,
    "idle_workers": 1,
    "queue_size": 2
  },
  "active_batches": [
    {
      "batch_uuid": "f7a9e3b2-...",
      "collection_id": "usb_camera_0",
      "status": "processing",
      "video_count": 5,
      "processing_time_seconds": 23.4
    }
  ],
  "recent_failures": 0,
  "uptime_seconds": 3600
}
```

---

## Error Handling and Recovery

### Retry Logic

```python
async def execute_batch_with_retry(
    batch_uuid: str,
    max_retries: int = 3,
    backoff_seconds: int = 5
) -> Dict:
    """Execute batch with exponential backoff retry."""
    
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            result = await execute_batch_pipeline(batch_uuid)
            return result
            
        except Exception as e:
            retry_count += 1
            last_error = e
            
            if retry_count < max_retries:
                wait_time = backoff_seconds * (2 ** (retry_count - 1))
                
                logger.warning(
                    f"[RETRY] Batch {batch_uuid[:8]} failed (attempt {retry_count}), "
                    f"retrying in {wait_time}s: {e}"
                )
                
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"[RETRY EXHAUSTED] Batch {batch_uuid[:8]} failed after "
                    f"{max_retries} attempts: {e}"
                )
    
    # All retries exhausted
    raise Exception(f"Batch processing failed after {max_retries} retries: {last_error}")
```

### Failure Scenarios

#### 1. Media Service Unavailable

**Detection**: HTTP request to Media Service fails

**Recovery**:
1. Log error
2. Retry with exponential backoff (3 attempts)
3. If all retries fail:
   - Mark batch as 'failed'
   - Keep batch state (don't delete videos from batch)
   - Allow manual retry later

#### 2. Orchestrator Service Unavailable

**Detection**: HTTP request to Orchestrator fails

**Recovery**:
1. Retry with exponential backoff
2. If fails: Mark batch as 'failed'
3. Manual trigger can retry later

#### 3. Database Connection Lost

**Detection**: Database query fails

**Recovery**:
1. Reconnect to database
2. Verify batch state (idempotency)
3. Resume from last checkpoint
4. If batch was 'processing', check if session exists
   - If session exists: Wait for completion
   - If no session: Retry batch execution

#### 4. Worker Crash

**Detection**: Worker process exits unexpectedly

**Recovery**:
1. Restart worker automatically
2. Check for orphaned batches (status='processing' but no active worker)
3. Reset orphaned batches to 'accumulating'
4. Re-trigger processing

### Idempotency

**Key Principle**: Batch processing must be idempotent (safe to retry)

**Implementation**:
```python
async def execute_batch_pipeline_idempotent(batch_uuid: str):
    """Idempotent batch processing."""
    
    # Check if batch already completed
    batch_state = await get_batch_state(batch_uuid)
    
    if batch_state['status'] == 'completed':
        logger.info(f"[IDEMPOTENCY] Batch {batch_uuid[:8]} already completed, skipping")
        return batch_state['result']
    
    # Check if tracking session already exists
    if batch_state['session_uuid']:
        logger.info(f"[IDEMPOTENCY] Resuming existing session {batch_state['session_uuid'][:8]}")
        
        # Wait for existing session to complete
        result = await wait_for_session_completion(
            session_uuid=batch_state['session_uuid']
        )
        
        return result
    
    # No existing session, create new one
    return await execute_batch_pipeline(batch_uuid)
```

---

## Performance Optimization

### 1. Batch Size Optimization

**Objective**: Find optimal batch size for best throughput vs. latency

**Considerations**:
- Smaller batches (2-3 videos): Lower latency, higher cache hit rate
- Larger batches (10-15 videos): Better throughput, more merge opportunities
- Recommended: 5 videos (balance)

**Adaptive Sizing**:
```python
async def calculate_optimal_batch_size(collection_id: str) -> int:
    """Calculate optimal batch size based on historical performance."""
    
    # Query recent batch history
    history = await get_batch_history(
        collection_id=collection_id,
        limit=20
    )
    
    # Calculate average processing time per video
    avg_time_per_video = sum(
        h['processing_time_seconds'] / h['video_count']
        for h in history
    ) / len(history)
    
    # Calculate average cache hit rate
    avg_cache_hit_rate = sum(
        h['cache_hit_rate'] for h in history
    ) / len(history)
    
    # Adjust batch size based on metrics
    if avg_cache_hit_rate > 0.7:
        # High cache hit rate → use larger batches
        return 10
    elif avg_time_per_video > 20:
        # Slow processing → use smaller batches
        return 3
    else:
        # Normal → use default
        return 5
```

### 2. Parallel Batch Processing

**Objective**: Process multiple collections concurrently

**Implementation**:
```python
class MultiCollectionBatchProcessor:
    """Process batches for multiple collections in parallel."""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(self, batch_uuid: str):
        """Process single batch with semaphore."""
        async with self.semaphore:
            return await execute_batch_pipeline(batch_uuid)
    
    async def process_multiple_batches(self, batch_uuids: List[str]):
        """Process multiple batches concurrently."""
        tasks = [
            self.process_batch(batch_uuid)
            for batch_uuid in batch_uuids
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. Cache Warming

**Objective**: Pre-load cache for frequently accessed videos

**Implementation**:
```python
async def warm_cache_for_collection(collection_id: str):
    """Pre-load cache for collection's recent videos."""
    
    # Query recent videos in collection
    videos = await get_recent_videos(
        collection_id=collection_id,
        limit=50
    )
    
    # For each video, trigger individual cache population
    for video in videos:
        await populate_individual_cache(video['uuid'])
```

### 4. Embedding Pre-computation

**Objective**: Pre-compute embeddings during face detection

**Implementation**: Store embeddings in Vision Service during face detection, not during batch processing

**Benefits**:
- Zero embedding computation time during batch processing
- Batch processing only merges existing embeddings
- Significantly faster pipeline execution

---

## Example Scenarios

### Scenario 1: Normal Operation (Batch Size = 5)

```
Timeline:

10:00:00  Camera starts recording
10:00:30  Segment 1 recorded → Face detection starts
10:01:00  Segment 2 recorded → Face detection starts
10:01:30  Segment 1 face detection completes → Batch counter = 1
10:01:30  Segment 3 recorded → Face detection starts
10:02:00  Segment 4 recorded → Face detection starts
10:02:30  Segment 2 face detection completes → Batch counter = 2
10:02:30  Segment 5 recorded → Face detection starts
10:03:00  Segment 6 recorded → Face detection starts
10:03:30  Segment 3 face detection completes → Batch counter = 3
10:04:00  Segment 7 recorded → Face detection starts
10:04:30  Segment 4 face detection completes → Batch counter = 4
10:05:00  Segment 8 recorded → Face detection starts
10:05:30  Segment 5 face detection completes → Batch counter = 5 → TRIGGER!

10:05:30  Batch processing starts (Segments 1-5)
          ├─ Query videos from Media Service
          ├─ Check individual cache (assume 2 cache hits)
          ├─ Create 3 new individuals via Orchestrator
          ├─ Check MVR cache (assume 1 cache hit)
          ├─ Run merge (combine 3 individuals → 1 MVR person)
          └─ Store results

10:06:15  Batch processing completes (45 seconds)
          Result: 5 individuals (2 cached, 3 new) → 2 MVR people (1 cached, 1 new)

10:06:15  New batch starts (Segments 6-10)
          Batch counter resets to 0
          Segment 6 face detection completes → Batch counter = 1
          ...
```

### Scenario 2: High Cache Hit Rate

```
Timeline:

10:00:00  Batch 1: 5 videos processed → 12 individuals, 3 MVR people created
10:05:00  Batch 2: 5 videos (same person appears)
          ├─ Individual cache: 8 hits (reuse from Batch 1)
          ├─ Create: 4 new individuals
          ├─ MVR cache: 2 hits (reuse from Batch 1)
          ├─ Merge: 4 new individuals → 1 new MVR person
          └─ Result: 12 individuals (8 cached, 4 new) → 3 MVR people (2 cached, 1 new)
          
Processing time: 25 seconds (vs. 45 seconds without cache)
Cache hit rate: 66.7% individuals, 66.7% MVR
```

### Scenario 3: Failure and Recovery

```
Timeline:

10:00:00  Batch accumulating (videos 1-5)
10:05:30  Batch triggers
10:05:31  Media Service query fails (network issue)
10:05:36  Retry 1: Success → Query 5 videos
10:05:37  Orchestrator call for individual creation
10:05:45  Orchestrator call succeeds
10:05:46  Database connection lost
10:05:51  Retry: Reconnect to database
10:05:52  Check batch state (status='processing', session exists)
10:05:53  Wait for tracking session to complete
10:06:20  Session completes
10:06:21  Update batch state: status='completed'
10:06:21  Batch processing successful (total time: 51 seconds including retries)
```

---

## Summary

The Continuous Individuals and MVR People Data Objects Pipeline provides:

✅ **Automatic Triggering**: Batches trigger when X videos complete face detection  
✅ **Event-Driven**: Real-time responsiveness via face detection completion events  
✅ **Non-Blocking**: Dedicated worker pool isolates from API and recording services  
✅ **Cached Processing**: Leverages two-level cache (individual + MVR)  
✅ **Fault Tolerant**: Retry logic, idempotency, and graceful error handling  
✅ **Observable**: Comprehensive metrics, logging, and health checks  
✅ **Scalable**: Parallel processing for multiple collections  
✅ **Configurable**: Flexible batch sizing and resource limits  

### Key Metrics

- **Batch Size**: 5 videos (default, configurable)
- **Processing Time**: 30-60 seconds per batch (with cache)
- **Cache Hit Rate**: 40-70% (depending on video overlap)
- **Throughput**: 5-10 batches per minute (3 concurrent workers)
- **Latency**: 30-90 seconds from last video to batch completion

### Next Steps

1. **Implementation Phase 1**: Batch monitoring service
2. **Implementation Phase 2**: Pipeline executor service
3. **Implementation Phase 3**: Event subscription layer
4. **Testing Phase**: Integration testing with camera recording
5. **Optimization Phase**: Performance tuning and cache optimization
6. **Production Phase**: Rollout with monitoring

---

## Implementation Phases

### Overview

The Continuous Individuals and MVR Pipeline will be implemented in **5 phases** over approximately **6-8 weeks**. Each phase builds on the previous one, allowing for incremental testing and validation.

---

### Phase 1: Database Schema and Configuration (Week 1)

**Objective**: Set up database tables and configuration infrastructure

**Tasks**:

1. **Create Migration Scripts**
   - `006_batch_processing_state.sql`: Batch state tracking table
   - `007_batch_video_assignments.sql`: Video-batch mapping table
   - `008_batch_processing_history.sql`: Audit log table
   - `009_batch_processing_config.sql`: Configuration table

2. **Database Tables**:
```sql
-- Migration 006: batch_processing_state
CREATE TABLE batch_processing_state (
    batch_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id VARCHAR(255) NOT NULL,
    batch_number INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    video_count INTEGER NOT NULL DEFAULT 0,
    batch_size_threshold INTEGER NOT NULL DEFAULT 5,
    first_video_start_time TIMESTAMP,
    last_video_end_time TIMESTAMP,
    last_video_time TIMESTAMP,
    timeout_at TIMESTAMP,
    triggered_at TIMESTAMP,
    completed_at TIMESTAMP,
    session_uuid UUID,
    individuals_created INTEGER DEFAULT 0,
    individuals_cached INTEGER DEFAULT 0,
    mvr_people_created INTEGER DEFAULT 0,
    mvr_people_cached INTEGER DEFAULT 0,
    processing_time_seconds DOUBLE PRECISION,
    is_partial_batch BOOLEAN DEFAULT FALSE,
    trigger_reason VARCHAR(50),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_status CHECK (
        status IN ('accumulating', 'processing', 'completed', 'failed', 'incomplete')
    )
);

-- Migration 007: batch_video_assignments
CREATE TABLE batch_video_assignments (
    id SERIAL PRIMARY KEY,
    batch_uuid UUID NOT NULL REFERENCES batch_processing_state(batch_uuid),
    video_uuid UUID NOT NULL,
    collection_id VARCHAR(255) NOT NULL,
    video_start_time TIMESTAMP NOT NULL,
    video_end_time TIMESTAMP NOT NULL,
    face_detection_session_uuid UUID,
    faces_detected INTEGER,
    added_at TIMESTAMP DEFAULT NOW(),
    sequence_number INTEGER NOT NULL,
    UNIQUE(batch_uuid, video_uuid)
);

-- Migration 008: batch_processing_history
CREATE TABLE batch_processing_history (
    id SERIAL PRIMARY KEY,
    batch_uuid UUID NOT NULL,
    collection_id VARCHAR(255) NOT NULL,
    video_count INTEGER NOT NULL,
    individuals_created INTEGER NOT NULL,
    individuals_cached INTEGER NOT NULL,
    mvr_people_created INTEGER NOT NULL,
    mvr_people_cached INTEGER NOT NULL,
    processing_time_seconds DOUBLE PRECISION NOT NULL,
    cache_hit_rate DOUBLE PRECISION,
    throughput_videos_per_sec DOUBLE PRECISION,
    batch_start_time TIMESTAMP NOT NULL,
    batch_end_time TIMESTAMP NOT NULL,
    session_uuid UUID,
    status VARCHAR(50) NOT NULL,
    is_partial_batch BOOLEAN DEFAULT FALSE,
    trigger_reason VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Migration 009: batch_processing_config
CREATE TABLE batch_processing_config (
    id SERIAL PRIMARY KEY,
    collection_id VARCHAR(255) UNIQUE,  -- NULL for global config
    batch_size_threshold INTEGER NOT NULL DEFAULT 5,
    partial_batch_min_videos INTEGER NOT NULL DEFAULT 2,
    partial_batch_timeout_minutes INTEGER NOT NULL DEFAULT 10,
    max_concurrent_batches INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert global default config
INSERT INTO batch_processing_config (
    collection_id, 
    batch_size_threshold,
    partial_batch_min_videos,
    partial_batch_timeout_minutes
) VALUES (NULL, 5, 2, 10);
```

3. **Configuration Files**
   - `ppl-meta-vmeta/config/batch_processing.yml`
   - Environment variables

4. **Testing**:
   - Run migrations on dev database
   - Verify table creation and indexes
   - Test configuration loading

**Deliverables**:
- ✅ 4 migration scripts executed successfully
- ✅ Configuration system functional
- ✅ Unit tests for config loading

**Duration**: 3-4 days

---

### Phase 2: Batch Monitoring Service (Week 2-3)

**Objective**: Implement batch accumulation and threshold detection

**Tasks**:

1. **Create Batch Monitor Module**
   - `ppl-meta-vmeta/src/services/batch_monitor.py`
   - Tracks video count per collection
   - Detects when batch size threshold reached

2. **Implement Core Functions**:
```python
class BatchMonitor:
    """Monitors face detection completion and triggers batch processing."""
    
    async def add_video_to_batch(
        self,
        collection_id: str,
        video_uuid: str,
        start_time: datetime,
        end_time: datetime
    ):
        """Add video to current batch for collection."""
        pass
    
    async def check_and_trigger_batch(self, collection_id: str):
        """Check if batch should be triggered and trigger if ready."""
        pass
    
    async def get_active_batch(self, collection_id: str):
        """Get current accumulating batch for collection."""
        pass
    
    async def create_new_batch(self, collection_id: str):
        """Create new batch for collection."""
        pass
```

3. **Database Operations**:
   - Insert/update batch state
   - Add videos to batch assignments
   - Query batch configuration

4. **Testing**:
   - Unit tests for batch state management
   - Integration tests with database
   - Test batch threshold detection

**Deliverables**:
- ✅ BatchMonitor service implemented
- ✅ Unit tests passing (>80% coverage)
- ✅ Integration tests with database

**Duration**: 5-7 days

---

### Phase 3: Event Subscription and Triggering (Week 3-4)

**Objective**: Subscribe to face detection events and implement batch triggering

**Tasks**:

1. **Create Event Subscriber**
   - `ppl-meta-vmeta/src/services/event_subscriber.py`
   - Subscribe to Orchestrator face detection events
   - Handle event parsing and validation

2. **Implement Event Handlers**:
```python
class FaceDetectionEventSubscriber:
    """Subscribes to face detection completion events."""
    
    async def subscribe(self):
        """Subscribe to orchestrator events."""
        pass
    
    async def handle_completion(self, event: Dict):
        """Handle face detection completion event."""
        pass
    
    async def handle_reconnect(self):
        """Handle WebSocket reconnection."""
        pass
```

3. **Implement Batch Trigger Logic**:
```python
class BatchTrigger:
    """Handles batch processing triggering."""
    
    async def trigger_batch(
        self,
        batch_uuid: str,
        reason: str
    ):
        """Trigger batch processing."""
        pass
    
    async def validate_batch_ready(self, batch_uuid: str) -> bool:
        """Validate batch is ready for processing."""
        pass
```

4. **Polling Fallback**:
   - Implement polling mechanism as backup
   - Query Vision Service for completed sessions

5. **Testing**:
   - Mock face detection events
   - Test event handling
   - Verify batch triggering logic

**Deliverables**:
- ✅ Event subscription working
- ✅ Batch triggering functional
- ✅ Polling fallback implemented
- ✅ Integration tests with mocked events

**Duration**: 5-7 days

---

### Phase 4: Pipeline Executor and Two-Level Caching (Week 4-5)

**Objective**: Implement the core pipeline that creates individuals and MVR people

**Tasks**:

1. **Create Pipeline Executor**
   - `ppl-meta-vmeta/src/services/pipeline_executor.py`
   - Dedicated worker pool for batch processing
   - Queue management for concurrent batches

2. **Implement Pipeline Execution**:
```python
class PipelineExecutor:
    """Executes individuals and MVR creation pipeline."""
    
    async def execute_batch_pipeline(
        self,
        batch_uuid: str,
        collection_id: str,
        video_uuids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Execute pipeline for batch of videos."""
        pass
    
    async def create_tracking_session(
        self,
        session_data: Dict
    ) -> str:
        """Create tracking session for batch."""
        pass
    
    async def wait_for_session_completion(
        self,
        session_uuid: str,
        timeout_seconds: int = 300
    ) -> Dict:
        """Wait for tracking session to complete."""
        pass
```

3. **Integrate Two-Level Caching**:
   - Level 1: Individual cache (existing implementation)
   - Level 2: MVR cache (existing implementation)
   - Ensure batch mode flag is passed through

4. **Worker Pool Management**:
   - Implement dedicated asyncio worker pool
   - Queue management with max capacity
   - Resource isolation from API requests

5. **Testing**:
   - Unit tests for pipeline executor
   - Integration tests with tracking session API
   - Test cache hit scenarios
   - Performance testing with multiple concurrent batches

**Deliverables**:
- ✅ Pipeline executor implemented
- ✅ Worker pool functional
- ✅ Two-level caching integrated
- ✅ Performance benchmarks completed

**Duration**: 7-10 days

---

### Phase 5: Partial Batch Handling - Hybrid Approach (Week 5-6)

**Objective**: Implement Strategy 3 (Hybrid) for handling remaining videos after recording stops

**Tasks**:

1. **Recording Stop Event Integration**
   - Subscribe to Camera Service recording stop events
   - Parse recording session stop event format
   - Immediate batch triggering on recording stop

2. **Implement Hybrid Trigger**:
```python
class HybridBatchTrigger:
    """Hybrid batch triggering: recording stop + timeout fallback."""
    
    def __init__(self):
        self.timeout_tasks = {}  # collection_id -> asyncio.Task
        self.batch_monitor = BatchMonitor()
    
    async def on_video_added(self, collection_id: str):
        """Called when video added to batch."""
        batch = await self.batch_monitor.get_active_batch(collection_id)
        
        # Check normal batch size trigger
        if batch['video_count'] >= batch['batch_size_threshold']:
            await self.trigger_batch(batch['batch_uuid'], reason='threshold')
            return
        
        # Start/reset timeout task
        await self.start_timeout_task(collection_id, batch['batch_uuid'])
    
    async def on_recording_stopped(self, collection_id: str):
        """Called when recording session stops - PRIMARY TRIGGER."""
        # Cancel timeout task
        await self.cancel_timeout_task(collection_id)
        
        batch = await self.batch_monitor.get_active_batch(collection_id)
        
        if batch and batch['video_count'] >= batch['min_partial_batch_size']:
            logger.info(
                f"[RECORDING STOP] Triggering partial batch for {collection_id} "
                f"with {batch['video_count']} remaining videos"
            )
            
            await self.trigger_batch(
                batch['batch_uuid'],
                reason='recording_stopped',
                is_partial=True
            )
    
    async def start_timeout_task(self, collection_id: str, batch_uuid: str):
        """Start timeout monitoring task - FALLBACK TRIGGER."""
        await self.cancel_timeout_task(collection_id)
        
        task = asyncio.create_task(
            self.timeout_handler(collection_id, batch_uuid)
        )
        self.timeout_tasks[collection_id] = task
    
    async def timeout_handler(self, collection_id: str, batch_uuid: str):
        """Wait for timeout and trigger if needed."""
        try:
            config = await get_batch_config(collection_id)
            timeout_seconds = config['partial_batch_timeout_minutes'] * 60
            
            await asyncio.sleep(timeout_seconds)
            
            batch = await self.batch_monitor.get_active_batch(collection_id)
            
            if batch and batch['batch_uuid'] == batch_uuid:
                if batch['video_count'] >= batch['min_partial_batch_size']:
                    logger.info(
                        f"[TIMEOUT] Triggering partial batch after "
                        f"{timeout_seconds}s inactivity"
                    )
                    
                    await self.trigger_batch(
                        batch_uuid=batch_uuid,
                        reason='timeout',
                        is_partial=True
                    )
        except asyncio.CancelledError:
            logger.debug(f"[TIMEOUT] Task cancelled for {collection_id}")
    
    async def cancel_timeout_task(self, collection_id: str):
        """Cancel timeout task."""
        task = self.timeout_tasks.get(collection_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
```

3. **Camera Service Integration**:
   - Subscribe to `recording_session_stopped` events
   - Event format validation
   - Error handling for missing events

4. **Timeout Monitoring**:
   - Background task monitors batch inactivity
   - Configurable timeout per collection
   - Automatic cleanup of stale batches

5. **Testing**:
   - Unit tests for hybrid trigger logic
   - Test recording stop event handling
   - Test timeout fallback mechanism
   - Integration test: recording stop → immediate trigger
   - Integration test: event missed → timeout trigger
   - Edge case: recording pauses then resumes

**Deliverables**:
- ✅ Recording stop event subscription working
- ✅ Immediate trigger on recording stop
- ✅ Timeout fallback functional
- ✅ All edge cases tested
- ✅ Documentation updated

**Duration**: 5-7 days

---

## Search Endpoints Behavior (IMPORTANT)

### Read-Only Search Operations

When you search for individuals or MVR people in the Flutter UI (or via API), the endpoints are **READ-ONLY** and do **NOT** trigger any merge or batch processing operations:

**Search Endpoints**:
- `POST /api/v1/mvr-people/search/by-videos` - **READ-ONLY**
- `POST /api/v1/mvr-people/search/by-collection` - **READ-ONLY** (deprecated)

**Behavior**:
```
User searches timeframe
     ↓
Flutter/API calls search endpoint with video UUIDs or time range
     ↓
VMeta queries ppl_meta_vmeta database
     ↓
Returns existing MVR people + individuals from cache
     ↓
Fast results displayed (< 1 second, database queries only)
```

**Key Points**:
- ✅ **Fast retrieval**: Only database SELECT queries
- ✅ **No processing**: Does NOT trigger face detection or MVR merging
- ✅ **Cached results**: Returns what batch processing already created
- ✅ **Safe to call**: No side effects, idempotent

**What Creates Individuals and MVR People**:
- **Batch Processing Pipeline**: Automatically runs during recordings (every 5 videos)
- **Manual Trigger**: `POST /api/v1/cross-video/individuals/tracking/sessions` (explicit processing)
- **NOT Search Endpoints**: Search only reads existing data

### Phase 6: API Endpoints and Monitoring (Week 6-7)

**Objective**: Expose REST API endpoints and implement monitoring

**Tasks**:

1. **Create API Router**
   - `ppl-meta-vmeta/src/api/v1/batch_processing.py`
   - Implement all documented endpoints

2. **API Endpoints**:
   - `GET /api/v1/batch-processing/status`
   - `GET /api/v1/batch-processing/history`
   - `POST /api/v1/batch-processing/trigger`
   - `GET /api/v1/batch-processing/config`
   - `PUT /api/v1/batch-processing/config`
   - `PUT /api/v1/batch-processing/batch-size`
   - `GET /api/v1/batch-processing/incomplete`
   - `GET /api/v1/batch-processing/health`

3. **Implement Prometheus Metrics**:
```python
from prometheus_client import Counter, Gauge, Histogram

# Batch processing metrics
batch_processing_total = Counter(
    'batch_processing_total',
    'Total batches processed',
    ['collection_id', 'status', 'is_partial']
)

batch_current_size = Gauge(
    'batch_current_size',
    'Current videos in accumulating batch',
    ['collection_id']
)

batch_processing_duration = Histogram(
    'batch_processing_duration_seconds',
    'Batch processing duration',
    ['collection_id', 'is_partial']
)

individuals_created = Counter(
    'individuals_created_total',
    'Individuals created',
    ['collection_id', 'source']
)

mvr_people_created = Counter(
    'mvr_people_created_total',
    'MVR people created',
    ['collection_id', 'source']
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage',
    ['collection_id', 'cache_level']
)
```

4. **Logging Infrastructure**:
   - Structured logging with context
   - Log levels: DEBUG, INFO, WARNING, ERROR
   - Correlation IDs for tracking

5. **Health Checks**:
   - Worker pool health
   - Database connectivity
   - Event subscription status
   - Recent failures tracking

6. **Testing**:
   - API endpoint tests
   - Metrics validation
   - Load testing

**Deliverables**:
- ✅ All API endpoints functional
- ✅ Prometheus metrics exposed
- ✅ Health checks working
- ✅ API documentation generated (Swagger/OpenAPI)

**Duration**: 5-7 days

---

### Phase 7: Integration Testing and Production Deployment (Week 7-8)

**Objective**: End-to-end testing and production rollout

**Tasks**:

1. **Integration Testing Suite**
   - End-to-end workflow tests
   - Multi-collection concurrent processing
   - Failure recovery scenarios
   - Performance benchmarks

2. **Load Testing**:
   - Simulate 10+ concurrent batches
   - Test with various batch sizes (2-20 videos)
   - Measure cache hit rates
   - Identify bottlenecks

3. **Documentation**:
   - Update API documentation
   - Create runbook for operations
   - Write troubleshooting guide

4. **Production Deployment**:
   - Deploy to staging environment
   - Run integration tests in staging
   - Deploy to production with feature flag
   - Enable for single collection (pilot)
   - Monitor for 48 hours
   - Gradual rollout to all collections

5. **Monitoring Setup**:
   - Grafana dashboards
   - Alerting rules (Prometheus/AlertManager)
   - Log aggregation (ELK/Loki)

**Deliverables**:
- ✅ Integration test suite passing
- ✅ Production deployment successful
- ✅ Monitoring dashboards operational
- ✅ Documentation complete

**Duration**: 7-10 days

---

## Full Backend Headless Test Scenario

### Overview

This section provides a complete end-to-end test scenario that validates the entire continuous individuals and MVR pipeline using **real camera recording** via backend APIs (no frontend required). The test uses actual camera hardware or mock camera to record real video segments, which are then processed through the complete pipeline.

### Test Environment Setup

**Prerequisites:**
- All services running (Gateway, Node, Media, Orchestrator, Vision, Cameras, VMeta)
- Valid authentication token
- Real USB camera connected **OR** mock camera configured
- Camera detected and available in system

**Test Parameters:**
```bash
# Environment configuration
export GATEWAY_URL="http://localhost:8080"
export NODE_URL="http://localhost:8001"
export MEDIA_URL="http://localhost:8000"
export ORCHESTRATOR_URL="http://localhost:8002"
export VISION_URL="http://localhost:8003"
export CAMERAS_URL="http://localhost:8005"
export VMETA_URL="http://localhost:8008"

# Authentication (obtain from login endpoint)
export AUTH_TOKEN="your-jwt-token-here"

# Test configuration
export TEST_USER_ID="test-user-123"
export BATCH_SIZE=5  # Process 5 videos per batch
```

---

## Pipeline Verification Testing

### Smoke Test Analysis

The smoke test (`tests/smoke_test_pipeline.sh`) is designed to verify that the continuous pipeline executed correctly after a recording session. It performs post-recording analysis to check if individuals and MVR people were created.

#### How the Smoke Test Works

**Purpose**: Verify pipeline execution **after** a recording session has completed, checking if face detection, individuals, and MVR people were created for videos recorded in a specific time window.

**Test Architecture**:

```bash
┌─────────────────────────────────────────────────────────────────┐
│                    SMOKE TEST FLOW                              │
└─────────────────────────────────────────────────────────────────┘

1. Authenticate
   └─> GET access token from Node Service (Port 8001)

2. Find Recent Recording Session
   └─> Query Media Service (Port 8000) for videos from usb_camera_0
   └─> Identify time range: first_video.created_at → last_video.created_at
   └─> Count videos uploaded in session

3. Check for Individuals
   └─> Query VMeta Service (Port 8008) tracking sessions
   └─> Filter: created_at >= recording_start_time
   └─> Count individuals created after recording began

4. Check for MVR People
   └─> Query VMeta Service (Port 8008) MVR people
   └─> Filter: created_at >= recording_start_time
   └─> Count MVR people created after recording began

5. Check Batch Processing History
   └─> Query VMeta Service (Port 8008) batch history
   └─> Show: batch status, trigger reason, cache rates
   └─> Verify: individuals/MVR created counts match expectations
```

#### Key Test Components

**Step 1: Authentication**

```bash
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

- Gets JWT token from Node service
- Extracts user_id from token payload
- Required for all subsequent API calls

**Step 2: Video Discovery**

```bash
VIDEOS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/media/search?limit=50")
```

The test queries the Media Service to find videos from the recording session:

- Filters videos by camera device ID (usb_camera_0)
- Sorts by created_at timestamp
- Identifies first and last video timestamps
- Calculates session duration and segment count

**Python Analysis Logic**:

```python
# Parse video list
videos = data.get('results', data.get('media', []))

# Filter for camera-specific videos
camera_videos = [v for v in videos 
                 if 'usb_camera_0' in v.get('title', '')]

# Get time range
first_video = camera_videos[-1]  # Oldest
last_video = camera_videos[0]     # Newest
start_time = first_video.get('created_at')
end_time = last_video.get('created_at')

# Export for next steps
print(f"START_TIME='{start_time}'")
print(f"END_TIME='{end_time}'")
print(f"VIDEO_COUNT={len(camera_videos)}")
```

**Step 3: Individual Tracking Sessions**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions"
```

Checks VMeta service for individual tracking sessions:

- Sessions represent cross-video tracking executions
- Each session contains multiple individuals
- Created_at timestamp shows when tracking ran
- Filters sessions created after recording start time

**Expected Result**: 
- If pipeline worked: 1+ sessions with individuals
- If pipeline failed: 0 sessions found

**Step 4: MVR People Objects**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/mvr-people/search/demographics?limit=50"
```

Checks VMeta service for MVR people created:

- MVR people are the final output of the pipeline
- Represent unique persons across multiple videos
- Created_at shows when person was identified/merged
- Filters MVR people created after recording start time

**Expected Result**:
- If pipeline worked: Multiple MVR people with appearance counts
- If pipeline failed: 0 MVR people found

**Step 5: Batch Processing History**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/batch-processing/history?user_id=${USER_ID}&limit=10"
```

Retrieves batch processing execution history:

- Shows batches triggered during/after recording
- Displays batch status (accumulating/processing/completed)
- Shows trigger reason (threshold_reached/recording_stopped)
- Reports individuals/MVR counts and cache hit rates
- Shows processing time per batch

**Expected Result**:
- If pipeline worked: 2-3 completed batches with statistics
- If pipeline failed: 0 batches or batches stuck in "accumulating"

#### Test Output Format

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Continuous Pipeline Smoke Test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ Authenticating...
✅ Authenticated (User ID: 7)

━━━ STEP 1: Check Recent Videos from usb_camera_0 ━━━

✅ Found 9 video segments
   First video: 2025-11-14T18:38:05
   Last video: 2025-11-14T18:42:14
   Segments: 9

Recent video segments:
   1. Camera Recording - usb_camera_0
      UUID: 5f33b26b-1542-4519-9876-d86c917ae819
   ... (truncated for brevity)

━━━ STEP 2: Check for Individuals ━━━

✅ Found 0 individual tracking session(s) after 16:38:
   (No sessions found - pipeline did not execute)

━━━ STEP 3: Check for MVR People ━━━

✅ Found 0 MVR people created after 16:38:
   (No MVR people - pipeline did not execute)

━━━ STEP 4: Check Batch Processing History ━━━

⚠️  No batch processing history found
   This could mean:
   • Batch processing hasn't triggered yet
   • Videos are still being processed
   • Face detection is still running

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Smoke Test Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Test completed!

Check the output above to verify:
  1. Recording session was found (~8 minutes duration)
  2. Video segments were created and uploaded
  3. MVR people objects were created after session start
  4. Batch processing history shows completed batches
```

#### Actual Test Results (November 14, 2025)

**Test Recording**: 4.5 minutes, 18:38-18:42

**✅ Videos Uploaded**: 9 segments successfully uploaded
- segment_001: 18:38:05
- segment_002: 18:38:36
- segment_003: 18:39:07
- segment_004: 18:39:39
- segment_005: 18:40:10
- segment_006: 18:40:41
- segment_007: 18:41:12
- segment_008: 18:41:44
- segment_009: 18:42:14

**❌ Individuals Created**: 0 (Expected: 10-20)

**❌ MVR People Created**: 0 (Expected: 2-5)

**❌ Batch Processing**: No batches triggered

**Root Cause**: Face detection not auto-triggering on uploaded videos

#### Success Criteria

The smoke test validates:

✅ **Upload Success**:
- Videos appear in Media Service
- Timestamps match recording session
- All segments accounted for

❌ **Pipeline Execution** (Currently Failing):
- Individuals created after recording start
- MVR people created from individuals
- Batch processing history exists
- Cache hit rates show optimization

✅ **Data Consistency**:
- Video count matches recording duration
- Timestamps are sequential
- No gaps in segment numbering

#### Using the Smoke Test

**Run after any recording session to verify pipeline execution**:

```bash
# After completing a recording session via Flutter app or API:
cd /Users/nickgklezakos/Documents/ppl-meta-code
bash tests/smoke_test_pipeline.sh
```

**When to use**:
- After manual recording sessions to verify data was processed
- After code changes to continuous pipeline components
- To diagnose why individuals/MVR people aren't being created
- To check batch processing trigger behavior

**What it checks**:
1. Videos were uploaded successfully
2. Individual tracking sessions were created
3. MVR people were generated
4. Batch processing executed with correct triggers
5. Cache hit rates show optimization

**Interpreting results**:
- All green ✅ = Pipeline working correctly
- Videos found but no individuals ❌ = Face detection issue
- No videos found ❌ = Upload issue  
- No batches ⚠️ = Trigger mechanism issue

---

---

## Implementation Summary

The continuous individuals and MVR pipeline implementation is partially complete:

### ✅ Phase 1: Continuous Upload (Completed - November 14, 2025)

**Camera Service Enhancement** (`ppl-meta-cameras/src/services/camera_detection.py`):
- Modified `_rotate_to_next_segment()` to upload immediately after segment completion
- Segments now upload every 30 seconds during recording
- Upload happens in parallel with recording (non-blocking)
- Verified working: 9 segments uploaded successfully in 4.5 minute test

### ❌ Phase 2: Auto Face Detection Trigger (Blocked)

**Current Issue**:
- `_check_and_trigger_face_detection()` is called but not executing
- Videos upload successfully but face detection doesn't trigger
- Blocking all downstream pipeline components

### ⏸️ Phase 3-7: Pipeline Components (Ready but Untested)

**Backend Components** (Code exists but cannot test until Phase 2 fixed):
- Batch monitoring service
- Event subscription and triggering  
- Pipeline executor with two-level caching
- Hybrid partial batch handling
- API endpoints and monitoring

**Next Steps**:
1. Debug and fix automatic face detection trigger
2. Verify face detection runs on uploaded segments
3. Test batch accumulation and threshold triggering
4. Validate two-level caching effectiveness
5. Measure end-to-end pipeline performance

### Timeline Update

**Original Estimate**: 6-8 weeks  
**Current Status**: Week 2 (Phase 1 complete, Phase 2 blocked)  
**Remaining Work**: 4-6 weeks after Phase 2 unblocked
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 5,
    "collection_id": null
  }' | jq '.'

echo "✅ Batch size configured to 5 videos"
```

##### 1.5 Enable Face Detection on Save

```bash
# Enable automatic face detection for recorded segments
echo ""
echo "⚙️ Enabling face detection on save..."

curl -s -X PUT "${NODE_URL}/api/v1/settings/face_detection_on_save" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "true"
  }' | jq '.'

echo "✅ Face detection enabled (Enhanced Logic V2)"
```

---

#### Step 2: Start Real Camera Recording

```bash
# Start recording from real camera
echo ""
echo "🎥 Starting camera recording..."
echo "   Camera: ${CAMERA_NAME}"
echo "   Device: ${CAMERA_DEVICE_ID}"
echo "   Segment Duration: 30 seconds"
echo "   Quality: High (1080p, 30fps)"

START_RESPONSE=$(curl -s -X POST "${CAMERAS_URL}/api/v1/cameras/${CAMERA_DEVICE_ID}/start-recording" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'${TEST_USER_ID}'",
    "recording_quality": "high",
    "segment_duration_seconds": 30,
    "auto_face_detection_enabled": true,
    "face_detection_method": "enhanced-v2",
    "resolution_width": 1920,
    "resolution_height": 1080,
    "fps": 30,
    "video_codec": "h264"
  }')

export SESSION_UUID=$(echo $START_RESPONSE | jq -r '.session_uuid')

if [ -z "$SESSION_UUID" ] || [ "$SESSION_UUID" = "null" ]; then
    echo "❌ Failed to start recording"
    echo $START_RESPONSE | jq '.'
    exit 1
fi

echo ""
echo "✅ Recording started successfully!"
echo "   Session UUID: ${SESSION_UUID}"
echo "   Status: Active"
echo ""
echo "📹 LIVE RECORDING IN PROGRESS..."
echo "   Duration: 6.5 minutes (13 segments × 30 seconds)"
echo "   The camera is now capturing real video."
echo "   Position yourself or subjects in front of the camera for face detection."
echo ""
echo "⏱️  Timeline:"
echo "   • Segments 1-13 will record continuously (30s each)"
echo "   • Each segment uploads to Media Service immediately after recording"
echo "   • Face detection runs on each uploaded segment"
echo "   • Batch processing triggers when conditions are met"
```

---

#### Step 3: Monitor First Batch Accumulation (Videos 1-5)

```bash
# Monitor recording session in real-time
echo ""
echo "📊 BATCH 1: Monitoring accumulation of videos 1-5..."

# Function to check recording status
check_recording_status() {
    STATUS_RESPONSE=$(curl -s "${CAMERAS_URL}/api/v1/recordings/${SESSION_UUID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    CURRENT_DURATION=$(echo $STATUS_RESPONSE | jq -r '.current_duration_seconds')
    SEGMENTS_COUNT=$(echo $STATUS_RESPONSE | jq -r '.segments_count')
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    
    echo "   📹 Status: ${STATUS} | Duration: ${CURRENT_DURATION}s | Segments: ${SEGMENTS_COUNT}"
}

# Function to check batch accumulation
check_batch_status() {
    BATCH_STATUS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/status?user_id=${TEST_USER_ID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    VIDEOS_READY=$(echo $BATCH_STATUS | jq -r '.videos_ready')
    BATCH_NUMBER=$(echo $BATCH_STATUS | jq -r '.current_batch_number')
    
    echo "   📦 Batch ${BATCH_NUMBER} | Videos ready: ${VIDEOS_READY}/5"
}

# Monitor first batch accumulation (Videos 1-5)
for segment in {1..5}; do
    echo ""
    echo "⏱️  Recording segment ${segment}/13..."
    
    # Wait for 30 second segment to record
    for i in {1..30}; do
        sleep 1
        if [ $((i % 10)) -eq 0 ]; then
            check_recording_status
        fi
    done
    
    echo "   ✅ Segment ${segment} recorded and uploaded"
    
    # Wait for face detection to complete (~60 seconds)
    echo "   🔍 Running face detection (Enhanced Logic V2)..."
    
    for i in {1..60}; do
        sleep 1
        if [ $((i % 15)) -eq 0 ]; then
            # Check if face detection completed
            FACE_DETECTION_STATUS=$(curl -s "${MEDIA_URL}/api/v1/media/search?user_id=${TEST_USER_ID}&limit=1" \
              -H "Authorization: Bearer ${AUTH_TOKEN}" | jq -r '.media[0].face_detection_status')
            
            if [ "$FACE_DETECTION_STATUS" = "completed" ]; then
                echo "   ✅ Face detection completed for segment ${segment}"
                break
            fi
        fi
    done
    
    # Check batch accumulation
    check_batch_status
done

echo ""
echo "✅ BATCH 1: All 5 videos recorded and face detection completed"
echo "   Batch threshold reached - pipeline should trigger automatically"
```

---

#### Step 4: Verify First Batch Trigger and Processing
```bash
# Verify batch 1 was triggered
echo ""
echo "🔍 Verifying Batch 1 trigger..."

sleep 3  # Wait for batch trigger

BATCH_HISTORY=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}&limit=1" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

BATCH_1_UUID=$(echo $BATCH_HISTORY | jq -r '.batches[0].batch_uuid')
BATCH_1_STATUS=$(echo $BATCH_HISTORY | jq -r '.batches[0].status')
BATCH_1_TRIGGER=$(echo $BATCH_HISTORY | jq -r '.batches[0].trigger_reason')
BATCH_1_VIDEOS=$(echo $BATCH_HISTORY | jq -r '.batches[0].video_count')

echo ""
echo "📦 BATCH 1 TRIGGERED"
echo "   UUID: ${BATCH_1_UUID}"
echo "   Status: ${BATCH_1_STATUS}"
echo "   Trigger: ${BATCH_1_TRIGGER}"
echo "   Videos: ${BATCH_1_VIDEOS}"

if [ "$BATCH_1_TRIGGER" != "threshold_reached" ]; then
    echo "❌ Expected trigger_reason='threshold_reached', got '${BATCH_1_TRIGGER}'"
    exit 1
fi

# Monitor batch processing
echo ""
echo "⏱️  BATCH 1: Pipeline executing (Two-level caching)..."
echo "   Expected duration: ~45 seconds (no cache warm)"

# Poll for completion
for i in {1..50}; do
    sleep 1
    
    BATCH_1_STATUS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_1_UUID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" | jq -r '.status')
    
    if [ "$BATCH_1_STATUS" = "completed" ]; then
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "   Processing... (${i}s elapsed)"
    fi
done

# Get batch 1 results
BATCH_1_RESULTS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_1_UUID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

INDIVIDUALS_1=$(echo $BATCH_1_RESULTS | jq -r '.individuals_created')
MVR_1=$(echo $BATCH_1_RESULTS | jq -r '.mvr_people_created')
CACHE_1=$(echo $BATCH_1_RESULTS | jq -r '.cache_hit_rate')
TIME_1=$(echo $BATCH_1_RESULTS | jq -r '.processing_time_seconds')

echo ""
echo "✅ BATCH 1 COMPLETED"
echo "   👤 Individuals Created: ${INDIVIDUALS_1}"
echo "   👥 MVR People Created: ${MVR_1}"
echo "   💾 Cache Hit Rate: ${CACHE_1}%"
echo "   ⏱️  Processing Time: ${TIME_1}s"
```

---

#### Step 5: Record and Process Batch 2 (Videos 6-10)

```bash
# Continue recording for batch 2
echo ""
echo "📊 BATCH 2: Recording videos 6-10..."

for segment in {6..10}; do
    echo ""
    echo "⏱️  Recording segment ${segment}/13..."
    
    # Record segment (30s)
    for i in {1..30}; do
        sleep 1
        if [ $((i % 10)) -eq 0 ]; then
            check_recording_status
        fi
    done
    
    echo "   ✅ Segment ${segment} recorded"
    
    # Face detection (~60s)
    echo "   🔍 Running face detection..."
    sleep 60
    
    check_batch_status
done

echo ""
echo "✅ BATCH 2: All 5 videos recorded and face detection completed"

# Verify batch 2 trigger
sleep 3

BATCH_HISTORY=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}&limit=1" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

BATCH_2_UUID=$(echo $BATCH_HISTORY | jq -r '.batches[0].batch_uuid')
BATCH_2_STATUS=$(echo $BATCH_HISTORY | jq -r '.batches[0].status')

echo ""
echo "📦 BATCH 2 TRIGGERED"
echo "   UUID: ${BATCH_2_UUID}"
echo "   Status: ${BATCH_2_STATUS}"

# Wait for processing
echo ""
echo "⏱️  BATCH 2: Pipeline executing (cache warming)..."
echo "   Expected duration: ~35 seconds (30% cache hit)"

for i in {1..40}; do
    sleep 1
    
    BATCH_2_STATUS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_2_UUID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" | jq -r '.status')
    
    if [ "$BATCH_2_STATUS" = "completed" ]; then
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "   Processing... (${i}s elapsed)"
    fi
done

# Get batch 2 results
BATCH_2_RESULTS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_2_UUID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

INDIVIDUALS_2=$(echo $BATCH_2_RESULTS | jq -r '.individuals_created')
MVR_2=$(echo $BATCH_2_RESULTS | jq -r '.mvr_people_created')
CACHE_2=$(echo $BATCH_2_RESULTS | jq -r '.cache_hit_rate')
TIME_2=$(echo $BATCH_2_RESULTS | jq -r '.processing_time_seconds')

echo ""
echo "✅ BATCH 2 COMPLETED"
echo "   👤 Individuals Created: ${INDIVIDUALS_2}"
echo "   👥 MVR People Created: ${MVR_2}"
echo "   💾 Cache Hit Rate: ${CACHE_2}%"
echo "   ⏱️  Processing Time: ${TIME_2}s"
```

---

#### Step 6: Record Final Videos and Test Hybrid Partial Batch

```bash
# Record final 3 videos
echo ""
echo "📊 FINAL SEGMENT: Recording videos 11-13..."

for segment in {11..13}; do
    echo ""
    echo "⏱️  Recording segment ${segment}/13..."
    
    # Record segment (30s)
    for i in {1..30}; do
        sleep 1
        if [ $((i % 10)) -eq 0 ]; then
            check_recording_status
        fi
    done
    
    echo "   ✅ Segment ${segment} recorded"
    
    # Face detection (~60s)
    echo "   🔍 Running face detection..."
    sleep 60
done

echo ""
echo "✅ All 13 segments recorded"
echo "   Remaining: 3 videos in partial batch"
echo ""
echo "🛑 Stopping camera recording..."
echo "   This will trigger Hybrid partial batch processing"

# Stop recording - triggers recording_stopped event
STOP_RESPONSE=$(curl -s -X POST "${CAMERAS_URL}/api/v1/cameras/${CAMERA_DEVICE_ID}/stop-recording" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_uuid": "'${SESSION_UUID}'"
  }')

STOP_STATUS=$(echo $STOP_RESPONSE | jq -r '.status')

if [ "$STOP_STATUS" = "completed" ]; then
    echo "✅ Recording stopped successfully"
else
    echo "❌ Failed to stop recording"
    exit 1
fi

# Verify immediate partial batch trigger
echo ""
echo "🎯 HYBRID TRIGGER: Recording stop event received"
echo "   Expected: Immediate partial batch trigger (0-2 seconds)"

sleep 3

BATCH_HISTORY=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}&limit=1" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

BATCH_3_UUID=$(echo $BATCH_HISTORY | jq -r '.batches[0].batch_uuid')
BATCH_3_STATUS=$(echo $BATCH_HISTORY | jq -r '.batches[0].status')
BATCH_3_TRIGGER=$(echo $BATCH_HISTORY | jq -r '.batches[0].trigger_reason')
BATCH_3_SIZE=$(echo $BATCH_HISTORY | jq -r '.batches[0].video_count')

echo ""
echo "📦 BATCH 3 (PARTIAL) TRIGGERED"
echo "   UUID: ${BATCH_3_UUID}"
echo "   Status: ${BATCH_3_STATUS}"
echo "   Trigger: ${BATCH_3_TRIGGER}"
echo "   Video Count: ${BATCH_3_SIZE}"

if [ "$BATCH_3_TRIGGER" != "recording_stopped" ]; then
    echo "❌ Expected trigger_reason='recording_stopped', got '${BATCH_3_TRIGGER}'"
    echo "⚠️  Hybrid trigger may not be working correctly"
fi

if [ "$BATCH_3_SIZE" != "3" ]; then
    echo "⚠️  Expected 3 videos, got ${BATCH_3_SIZE}"
fi

# Wait for partial batch processing
echo ""
echo "⏱️  BATCH 3: Pipeline executing (cache hot)..."
echo "   Expected duration: ~26 seconds (50% cache hit)"

for i in {1..35}; do
    sleep 1
    
    BATCH_3_STATUS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_3_UUID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" | jq -r '.status')
    
    if [ "$BATCH_3_STATUS" = "completed" ]; then
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "   Processing... (${i}s elapsed)"
    fi
done

# Get batch 3 results
BATCH_3_RESULTS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_3_UUID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

INDIVIDUALS_3=$(echo $BATCH_3_RESULTS | jq -r '.individuals_created')
MVR_3=$(echo $BATCH_3_RESULTS | jq -r '.mvr_people_created')
CACHE_3=$(echo $BATCH_3_RESULTS | jq -r '.cache_hit_rate')
TIME_3=$(echo $BATCH_3_RESULTS | jq -r '.processing_time_seconds')

echo ""
echo "✅ BATCH 3 (PARTIAL) COMPLETED"
echo "   👤 Individuals Created: ${INDIVIDUALS_3}"
echo "   👥 MVR People Created: ${MVR_3}"
echo "   💾 Cache Hit Rate: ${CACHE_3}%"
echo "   ⏱️  Processing Time: ${TIME_3}s"
```

---

#### Step 7: Verify Complete Results

```bash
# Complete session summary
echo ""
echo "═══════════════════════════════════════════════"
echo "📊 COMPLETE TEST SESSION SUMMARY"
echo "═══════════════════════════════════════════════"

# Recording session summary
RECORDING_SUMMARY=$(curl -s "${CAMERAS_URL}/api/v1/recordings/${SESSION_UUID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

TOTAL_SEGMENTS=$(echo $RECORDING_SUMMARY | jq -r '.total_segments')
TOTAL_DURATION=$(echo $RECORDING_SUMMARY | jq -r '.total_duration_seconds')
TOTAL_SIZE=$(echo $RECORDING_SUMMARY | jq -r '.total_size_bytes')

echo ""
echo "🎥 Recording Session:"
echo "   Session UUID: ${SESSION_UUID}"
echo "   Camera: ${CAMERA_NAME}"
echo "   Total Segments: ${TOTAL_SEGMENTS}"
echo "   Total Duration: ${TOTAL_DURATION}s"
echo "   Total Size: $((TOTAL_SIZE / 1024 / 1024))MB"

# Batch processing summary
BATCH_HISTORY_FULL=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

TOTAL_BATCHES=$(echo $BATCH_HISTORY_FULL | jq -r '.total_batches')

echo ""
echo "📦 Batch Processing:"
echo "   Total Batches: ${TOTAL_BATCHES}"

# Calculate totals
TOTAL_INDIVIDUALS=$((INDIVIDUALS_1 + INDIVIDUALS_2 + INDIVIDUALS_3))
TOTAL_MVR=$((MVR_1 + MVR_2 + MVR_3))

echo ""
echo "👤 Data Objects Created:"
echo "   Total Individuals: ${TOTAL_INDIVIDUALS}"
echo "   Total MVR People: ${TOTAL_MVR}"
echo ""
echo "   Batch 1: ${INDIVIDUALS_1} individuals → ${MVR_1} MVR people"
echo "   Batch 2: ${INDIVIDUALS_2} individuals → ${MVR_2} MVR people"
echo "   Batch 3: ${INDIVIDUALS_3} individuals → ${MVR_3} MVR people"

# Cache progression
echo ""
echo "💾 Cache Hit Rate Progression:"
echo "   Batch 1: ${CACHE_1}% (cold cache)"
echo "   Batch 2: ${CACHE_2}% (warming)"
echo "   Batch 3: ${CACHE_3}% (hot cache)"

# Performance progression
echo ""
echo "⏱️  Processing Time Progression:"
echo "   Batch 1: ${TIME_1}s"
echo "   Batch 2: ${TIME_2}s"
echo "   Batch 3: ${TIME_3}s"
echo "   Improvement: $((100 - (TIME_3 * 100 / TIME_1)))% faster (Batch 3 vs Batch 1)"

# Trigger verification
echo ""
echo "🎯 Trigger Mechanisms:"
echo "   Batch 1: ${BATCH_1_TRIGGER}"
echo "   Batch 2: threshold_reached"
echo "   Batch 3: ${BATCH_3_TRIGGER} (Hybrid approach)"

echo ""
echo "═══════════════════════════════════════════════"
```

---

#### Step 8: Success Criteria Verification

```bash
echo ""
echo "✅ TEST SUCCESS CRITERIA VERIFICATION"
echo "═══════════════════════════════════════════════"

# Verify all criteria
SUCCESS_COUNT=0
TOTAL_CRITERIA=8

# 1. Batch count
if [ "$TOTAL_BATCHES" -eq "3" ]; then
    echo "✅ 1. Three batches processed"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ 1. Expected 3 batches, got ${TOTAL_BATCHES}"
fi

# 2. All segments recorded
if [ "$TOTAL_SEGMENTS" -eq "13" ]; then
    echo "✅ 2. All 13 segments recorded"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ 2. Expected 13 segments, got ${TOTAL_SEGMENTS}"
fi

# 3. Batch 1 trigger
if [ "$BATCH_1_TRIGGER" = "threshold_reached" ]; then
    echo "✅ 3. Batch 1 triggered by threshold"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ 3. Batch 1 trigger incorrect: ${BATCH_1_TRIGGER}"
fi

# 4. Batch 3 trigger (Hybrid)
if [ "$BATCH_3_TRIGGER" = "recording_stopped" ]; then
    echo "✅ 4. Batch 3 triggered by recording stop (Hybrid)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ 4. Batch 3 trigger incorrect: ${BATCH_3_TRIGGER}"
fi

# 5. Partial batch size
if [ "$BATCH_3_SIZE" -eq "3" ]; then
    echo "✅ 5. Partial batch has 3 videos"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ 5. Expected 3 videos, got ${BATCH_3_SIZE}"
fi

# 6. Individuals created
if [ "$TOTAL_INDIVIDUALS" -ge "15" ]; then
    echo "✅ 6. Sufficient individuals created (>= 15)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "⚠️  6. Low individual count: ${TOTAL_INDIVIDUALS}"
fi

# 7. Cache improvement
if (( $(echo "$CACHE_3 > $CACHE_1" | bc -l) )); then
    echo "✅ 7. Cache hit rate improved (${CACHE_1}% → ${CACHE_3}%)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "⚠️  7. Cache hit rate did not improve"
fi

# 8. Performance improvement
if (( $(echo "$TIME_3 < $TIME_1" | bc -l) )); then
    echo "✅ 8. Processing time improved (${TIME_1}s → ${TIME_3}s)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "⚠️  8. Processing time did not improve"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "Score: ${SUCCESS_COUNT}/${TOTAL_CRITERIA} criteria passed"

if [ "$SUCCESS_COUNT" -eq "$TOTAL_CRITERIA" ]; then
    echo "🎉 ALL TESTS PASSED!"
elif [ "$SUCCESS_COUNT" -ge "6" ]; then
    echo "✅ Tests mostly successful (minor issues)"
else
    echo "❌ Tests failed (major issues detected)"
fi

echo "═══════════════════════════════════════════════"
```

---

### Cleanup

```bash
echo ""
echo "🧹 Cleaning up test data..."

# Delete recording session and files
curl -s -X DELETE "${CAMERAS_URL}/api/v1/recordings/${SESSION_UUID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" | jq '.'

# Delete batch processing history
curl -s -X DELETE "${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" | jq '.'

echo "✅ Cleanup complete"
echo ""
echo "📝 Test execution finished"
```

---

### Test Success Criteria

✅ **Real Camera Recording**:
- Camera detected and initialized
- 13 video segments recorded (30s each)
- All segments uploaded to Media Service
- Real video files with actual content

✅ **Face Detection**:
- Enhanced Logic V2 runs on each segment
- Face detection completes successfully
- Real faces detected in actual video content
- Results stored in Vision Service database

✅ **Batch Accumulation**:
- Videos added to batch as face detection completes
- Batch counter increments correctly
- Batch status remains `accumulating` until threshold

✅ **Threshold Trigger**:
- Batch processing triggers at exactly 5 videos
- Status changes: `accumulating` → `processing` → `completed`
- Processing completes within 30-60 seconds

✅ **Partial Batch - Hybrid Trigger**:
- Recording stop event triggers immediately (0-2 second delay)
- Partial batch processes with 3 videos
- Trigger reason: `recording_stopped`
- No timeout wait required

✅ **Two-Level Caching**:
- Batch 1: 0% cache hit rate (first batch)
- Batch 2: 20-40% cache hit rate (some overlap)
- Batch 3: 40-60% cache hit rate (partial, high overlap)
- Processing time decreases with cache hits

✅ **Data Correctness**:
- All videos processed (no missing videos)
- Individuals created from actual faces
- MVR people merged based on real face embeddings
- Database consistency maintained

✅ **Performance**:
- Batch processing: 30-60 seconds per batch
- Real-time recording without interruption
- Face detection runs in parallel with recording
- Cache improves performance by 20-40%

✅ **Monitoring**:
- API endpoints return correct data
- Real-time status updates during recording
- Batch progress visible throughout workflow
- Complete session summary at end

---
  DELETE FROM batch_processing_state WHERE collection_id LIKE 'test_camera_%';
  DELETE FROM batch_processing_history WHERE collection_id LIKE 'test_camera_%';
"

# 3. Reset batch configuration
curl -X PUT http://localhost:8008/api/v1/batch-processing/batch-size \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "batch_size": 5
  }'

echo "Test cleanup complete"
```

---

## Document Summary

**Version**: 1.2  
**Date**: November 19, 2025  
**Status**: ✅ OPERATIONAL - Optimized Pipeline Ready for Testing

### November 19, 2025 - Final Implementation Status

**✅ COMPLETE - All Components Operational**:

**Core Pipeline**:
- ✅ Continuous segment upload (camera → media service)
- ✅ Automatic face detection triggering (fixed)
- ✅ Per-collection batch processing (separate queues)
- ✅ Recording-aware polling (event-driven)
- ✅ Enhanced Logic V2 integration (person_objects creation)
- ✅ Video UUID optimization (direct lookup)

**Critical Fixes Applied (November 14-19, 2025)**:
1. ✅ **File Paths**: Media service file storage and streaming paths fixed
2. ✅ **Authentication**: GET /media/{media_id} endpoint supports auth
3. ✅ **Auto-Trigger**: face_detection_on_save setting enabled
4. ✅ **Per-Collection**: Separate batch queues prevent cross-camera mixing
5. ✅ **Person Objects**: Enhanced Logic V2 call creates person_objects from stored_faces
6. ✅ **Performance**: Video UUID direct lookup skips time-based queries

**Pipeline Flow (Optimized)**:
```text
Recording → Upload → Face Detection → stored_faces
                                          ↓
                               Enhanced Logic V2
                                          ↓
                                  person_objects
                                          ↓
Batch (5 videos/collection) → Cross-Video Tracking
                                          ↓
                        Individuals + MVR People
```

**Key Optimizations**:
- **Video UUIDs**: Explicit video list eliminates time range ambiguity
- **Enhanced Logic V2**: Automatic person_objects creation from stored_faces
- **Per-Collection**: Independent processing prevents multi-camera contamination
- **Recording-Aware**: Only polls during active recordings (event-driven)

**Database Migrations Applied**:
- `006_add_video_uuids_optimization.sql` - Adds video_uuids JSONB column

**Ready for Testing**:
- Start recording with Camera service (Port 8005)
- System will automatically process batches of 5 videos per collection
- Each batch triggers Enhanced Logic V2 → Cross-Video Tracking
- Results visible in individuals and mvr_people tables

### Testing Checklist

**Pre-Test Verification**:
- [ ] All services healthy (Cameras, Media, Vision, Orchestrator, VMeta)
- [ ] face_detection_on_save='true' in ppl_db.app_settings
- [ ] VMeta PollingFallbackManager running
- [ ] Database migrations applied

**During Test**:
- [ ] Start recording (Camera service)
- [ ] Verify videos upload automatically
- [ ] Verify face detection triggers automatically
- [ ] Monitor batch accumulation (VMeta logs)
- [ ] Verify batch triggers at 5 videos
- [ ] Check Enhanced Logic V2 calls
- [ ] Verify person_objects created
- [ ] Verify individuals created
- [ ] Verify MVR people created

**Post-Test Validation**:
- [ ] Query individuals table (should have entries)
- [ ] Query mvr_people table (should have entries)
- [ ] Query tracking_sessions (should show completed sessions)
- [ ] Test Flutter app search (should return individuals/MVR)

### Known Limitations

**Current Constraints**:
- Batch size fixed at 5 videos per collection
- Enhanced Logic V2 sequential (not parallel) - could be optimized
- Requires active recording for polling (by design)
- No cross-collection tracking (by design)

**Future Enhancements**:
- Parallel Enhanced Logic V2 calls for better performance
- Configurable batch size per collection
- Support for retroactive processing of existing videos
- Individuals and MVR people creation untested

**⏸️ Ready but Untested**:
- Batch monitoring and accumulation logic
- Two-level caching architecture
- Hybrid partial batch handling
- API endpoints and monitoring

### Key Achievement

The continuous upload mechanism is now production-ready. Videos are uploaded to the media service immediately as 30-second segments are recorded, enabling real-time processing once the face detection trigger issue is resolved.

### Critical Blocker

Face detection must auto-trigger on uploaded videos for the rest of the pipeline to function. The `_check_and_trigger_face_detection()` function in the camera service is called but not executing successfully.

### Next Actions

1. Debug face detection trigger in camera service
2. Verify trigger reaches vision service
3. Test face detection execution on uploaded segments
4. Resume end-to-end pipeline validation

---

**Document Version:** 1.1  
**Last Updated:** November 14, 2025  
**Author:** PPL Meta Development Team  
**Status:** Partial Implementation - Continuous Upload Complete, Face Detection Trigger Blocked

````
- Performance and correctness

**Key Success Metrics**:
- Batch processing latency: 30-60 seconds
- Cache hit rate: 40-60% for overlapping videos
- Partial batch trigger: **0-2 seconds** (recording stop event)
- Fallback trigger: 10 minutes (timeout)
- System stability: No crashes or resource leaks

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  
**Author:** PPL Meta Development Team  
**Status:** Proposal - Ready for Implementation

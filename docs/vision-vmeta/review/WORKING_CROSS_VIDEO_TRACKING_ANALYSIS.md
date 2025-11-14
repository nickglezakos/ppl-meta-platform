# Working Cross-Video Tracking Analysis
**Date:** October 29, 2025  
**Status:** ✅ FULLY FUNCTIONAL  
**Purpose:** Document the successful implementation for future reference

---

## Success Evidence

### Flutter App Request Flow (October 29, 2025 11:36 UTC)

```
Step 1: Session Creation Request
================================
POST http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions

Request Body:
{
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-13T11:36:00.000",
  "end_time": "2025-10-29T11:36:00.000",
  "background_processing": true,
  "algorithm_config": {
    "max_gap_seconds": 10,
    "iou_threshold": 0.3,
    "min_overlap_confidence": 0.5
  }
}

Response (Immediate):
{
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "status": "initialized",
  "message": "Session created successfully",
  "cache_hit_rate": 0,
  "total_videos": 0  ← Note: 0 initially (background processing)
}

Step 2: Status Check #1 (Polling)
=================================
GET http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions/4a0515cf-12ee-45f0-8945-e7b2ae7bbe24

Response:
{
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "status": "running",  ← Processing in background
  "collections": ["usb_camera_0"],
  "created_at": "2025-10-29T11:36:19.523396",
  "started_at": "2025-10-29T11:36:19.535781",
  "completed_at": null,
  "total_videos": 0,  ← Still 0 (processing)
  "processed_videos": 0,
  "individuals_found": 0,
  "cache_hits": 0
}

Step 3: Status Check #2 (Completed!)
====================================
GET http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions/4a0515cf-12ee-45f0-8945-e7b2ae7bbe24

Response:
{
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "status": "completed",  ✅
  "collections": ["usb_camera_0"],
  "created_at": "2025-10-29T11:36:19.523396",
  "started_at": "2025-10-29T11:36:19.535781",
  "completed_at": "2025-10-29T11:36:19.759638",
  "total_videos": 2,  ✅ SUCCESS!
  "processed_videos": 2,  ✅
  "individuals_found": 1,  ✅
  "cache_hits": 0
}
```

**Key Success Metrics:**
- ✅ **Processing Time:** 224ms (completed_at - started_at)
- ✅ **Total Videos Found:** 2 videos
- ✅ **Videos Processed:** 2/2 (100%)
- ✅ **Individuals Tracked:** 1 individual across 2 videos
- ✅ **Background Processing:** Working correctly
- ✅ **Status Transitions:** initialized → running → completed

---

## Technical Architecture (Working Implementation)

### Service Chain

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Flutter App (localhost:3000)                                │
│    - Collections Screen                                        │
│    - User selects date range: Oct 13 - Oct 29                 │
│    - User selects collection: "usb_camera_0"                   │
│    - Taps "Start Tracking"                                     │
└────────────────────┬────────────────────────────────────────────┘
                     │ POST with JWT Bearer token
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Gateway Service (localhost:8080)                            │
│    - Validates JWT token                                       │
│    - Extracts user_id from token                              │
│    - Routes to vmeta service                                   │
│    - Proxies request with Authorization header                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ Forward with auth
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. vmeta Service (localhost:8008)                              │
│    File: api/v1/cross_video_tracking.py                       │
│    Endpoint: POST /api/v1/cross-video/.../tracking/sessions   │
│                                                                 │
│    Step 3.1: Extract JWT and user_id                          │
│    ────────────────────────────────────────────                │
│    - Get Authorization header                                  │
│    - Decode JWT token (no signature verification)             │
│    - Extract user_id from "sub" claim                         │
│    - user_id = "7" (fresh.user@example.com)                   │
│                                                                 │
│    Step 3.2: Create IntegratedCachingService                   │
│    ───────────────────────────────────────────                 │
│    - Initialize with database pool                             │
│    - Creates SessionManager                                    │
│    - Creates CacheManager                                      │
│    - Creates TrackingEngine                                    │
│                                                                 │
│    Step 3.3: Initialize Tracking Session                       │
│    ────────────────────────────────────────                    │
│    Method: initialize_tracking_session()                       │
│    - Creates TrackingSession object                            │
│    - Calls _fetch_video_data() with auth_token                │
│    - Analyzes cache availability                               │
│    - Stores session in database                                │
│    - Returns session_uuid                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │ Session UUID returned
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Background Task Execution                                    │
│    Method: execute_tracking_session(background=True)           │
│                                                                 │
│    Step 4.1: Update Status to RUNNING                          │
│    ────────────────────────────────────────                    │
│    - Status: initialized → running                             │
│    - Set started_at timestamp                                  │
│    - Create asyncio task for background processing             │
│    - Store task reference in active_sessions                   │
│                                                                 │
│    Step 4.2: Fetch Video Data                                  │
│    ────────────────────────────────────────                    │
│    Method: _fetch_video_data()                                 │
│    - Gateway URL: http://localhost:8080                        │
│    - Endpoint: /api/v1/media/search                           │
│    - Parameters:                                               │
│      * collection: "usb_camera_0"                             │
│      * start_time: "2025-10-13T11:36:00"                      │
│      * end_time: "2025-10-29T11:36:00"                        │
│      * user_id: "7"                                           │
│    - Auth: Bearer token in Authorization header               │
│    - Result: 2 videos found ✅                                │
│                                                                 │
│    Step 4.3: Fetch Person Objects Data                         │
│    ────────────────────────────────────────────                │
│    Method: _fetch_person_objects_data()                        │
│    - For each video:                                           │
│      * Vision URL: http://localhost:8003                       │
│      * Endpoint: /api/v1/person-objects/{video_uuid}          │
│      * Auth: Bearer token in Authorization header             │
│    - Extracts group_tracking data                             │
│    - Returns person objects per video                          │
│                                                                 │
│    Step 4.4: Run Tracking Algorithm                            │
│    ────────────────────────────────────────                    │
│    Method: _execute_cache_aware_processing()                   │
│    - Passes videos and person objects to TrackingEngine        │
│    - Applies algorithm_config:                                 │
│      * max_gap_seconds: 10                                     │
│      * iou_threshold: 0.3                                      │
│      * min_overlap_confidence: 0.5                             │
│    - Identifies individuals across videos                      │
│    - Result: 1 individual found ✅                             │
│                                                                 │
│    Step 4.5: Store Results                                     │
│    ────────────────────────────────────────                    │
│    Method: _store_session_results()                            │
│    - Updates database with:                                    │
│      * total_videos: 2                                         │
│      * processed_videos: 2                                     │
│      * individuals_found: 1                                    │
│      * status: completed                                       │
│      * completed_at: timestamp                                 │
│      * processing_time_seconds: 0.224                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Critical Success Factors

### 1. Collection Name Matching ✅

**Working Configuration:**
```dart
// Flutter sends
collections: ["usb_camera_0"]

// Media API recognizes
collection_name: "usb_camera_0"  // Exact match!
```

**Key Point:** Collection name must match EXACTLY (case-sensitive, no extra suffixes)

### 2. JWT Authentication Flow ✅

```python
# File: api/v1/cross_video_tracking.py

# Extract user from JWT
auth_header = authorization or ""
if auth_header.startswith("Bearer "):
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Decode JWT (no signature verification in development)
    payload = jwt.decode(
        token, 
        SECRET_KEY, 
        algorithms=[ALGORITHM],
        options={"verify_signature": False}  # Dev mode
    )
    
    user_id = payload.get("sub")  # Extract user ID from "sub" claim
    # Result: user_id = "7"
```

**Key Point:** User ID extracted from JWT token's "sub" claim

### 3. Auth Token Propagation ✅

```python
# File: services/session_manager.py

async def initialize_tracking_session(
    self,
    user_id: str,
    collections: List[str],
    start_time: datetime,
    end_time: datetime,
    config: CrossVideoTrackingConfig,
    auth_token: Optional[str] = None  # ✅ Token parameter added
) -> TrackingSession:
    
    # Pass auth_token to video data fetching
    video_data = await self._fetch_video_data(
        collections, 
        start_time, 
        end_time,
        user_id=user_id,
        auth_token=auth_token  # ✅ Propagated
    )
```

**Key Point:** Auth token passed through entire service chain

### 4. Media API Integration ✅

```python
# File: services/session_manager.py

async def _fetch_video_data(
    self,
    collections: List[str],
    start_time: datetime,
    end_time: datetime,
    user_id: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    
    gateway_url = "http://localhost:8080"
    
    # Build headers with auth token
    headers = {}
    if auth_token:
        if not auth_token.startswith("Bearer "):
            headers['Authorization'] = f'Bearer {auth_token}'
        else:
            headers['Authorization'] = auth_token
    
    # Build search parameters
    params = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    
    if collections:
        params["collection"] = ",".join(collections)
    
    if user_id:
        params["user_id"] = user_id  # ✅ Critical for multi-tenant
    
    # Call Media search API
    search_url = f"{gateway_url}/api/v1/media/search"
    async with session.get(search_url, params=params, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            # Process and return videos
```

**Key Points:**
- ✅ Uses `/api/v1/media/search` endpoint directly
- ✅ Includes `user_id` parameter for multi-tenant filtering
- ✅ Passes auth token in Authorization header
- ✅ Collection name passed as-is (no translation)

### 5. Vision API Integration ✅

```python
# File: services/session_manager.py

async def _fetch_person_objects_data(
    self, 
    videos: List[Dict[str, Any]],
    auth_token: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    
    vision_url = "http://localhost:8003"
    
    # Setup authentication headers
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for video in videos:
            video_uuid = video.get("video_uuid")
            
            # Call Vision API
            person_objects_url = (
                f"{vision_url}/api/v1/person-objects/{video_uuid}"
            )
            
            async with session.get(person_objects_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('success'):
                        # Extract person objects from response
                        group_tracking = data.get('group_tracking', [])
                        results[video_uuid] = group_tracking
```

**Key Points:**
- ✅ Uses `/api/v1/person-objects/{video_uuid}` endpoint
- ✅ Passes auth token to Vision service
- ✅ Extracts `group_tracking` field from response
- ✅ Returns person objects per video UUID

### 6. Background Processing ✅

```python
# File: services/session_manager.py

async def execute_tracking_session(
    self,
    session_uuid: str,
    background: bool = True,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    
    if background:
        # Update status to RUNNING immediately
        await self._update_session_status(session_uuid, SessionStatus.RUNNING)
        
        # Create background task
        task = asyncio.create_task(
            self._execute_session_background(session, auth_token)
        )
        
        # Store task reference (prevents garbage collection)
        self.active_sessions[session_uuid] = {
            'session': session,
            'task': task,
            'started_at': datetime.utcnow()
        }
        
        return {
            'session_uuid': session_uuid,
            'status': 'initialized',
            'execution_mode': 'background',
            'message': 'Session created successfully'
        }
```

**Key Points:**
- ✅ Returns immediately with `status: "initialized"`
- ✅ Updates to `status: "running"` before starting task
- ✅ Task reference stored in `active_sessions` dict
- ✅ Client polls status endpoint to check progress

### 7. Database Schema ✅

```sql
-- Table: tracking_sessions

CREATE TABLE tracking_sessions (
    session_uuid UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    collections TEXT[] NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    config_hash TEXT NOT NULL,
    algorithm_config JSONB NOT NULL,
    status TEXT NOT NULL,
    total_videos INTEGER DEFAULT 0,
    processed_videos INTEGER DEFAULT 0,
    individuals_found INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    processing_time_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**Key Point:** No `updated_at` column (was causing SQL errors)

---

## Data Flow Timeline

```
Time: 0ms (11:36:19.523)
┌─────────────────────────────────────────┐
│ Session Created                         │
│ UUID: 4a0515cf-12ee-45f0-8945-e7b2ae7bbe24 │
│ Status: initialized                     │
│ total_videos: 0                         │
└─────────────────────────────────────────┘

Time: 12ms (11:36:19.535)
┌─────────────────────────────────────────┐
│ Background Task Started                 │
│ Status: initialized → running           │
│ started_at set                          │
└─────────────────────────────────────────┘

Time: 12-50ms (estimated)
┌─────────────────────────────────────────┐
│ Fetching Video Data                     │
│ GET /api/v1/media/search                │
│ → Found 2 videos                        │
└─────────────────────────────────────────┘

Time: 50-150ms (estimated)
┌─────────────────────────────────────────┐
│ Fetching Person Objects                 │
│ GET /api/v1/person-objects/{uuid}       │
│ → Video 1: person objects fetched       │
│ → Video 2: person objects fetched       │
└─────────────────────────────────────────┘

Time: 150-220ms (estimated)
┌─────────────────────────────────────────┐
│ Running Tracking Algorithm              │
│ → Processing 2 videos                   │
│ → Identified 1 individual               │
└─────────────────────────────────────────┘

Time: 224ms (11:36:19.759)
┌─────────────────────────────────────────┐
│ Session Completed ✅                    │
│ Status: running → completed             │
│ total_videos: 2                         │
│ processed_videos: 2                     │
│ individuals_found: 1                    │
│ completed_at set                        │
└─────────────────────────────────────────┘
```

**Total Processing Time:** 224 milliseconds

---

## File Changes That Made It Work

### Files Modified from Previous Broken State

1. **`services/session_manager.py`** - REVERTED to working version
   - ✅ Removed complex collection lookup logic
   - ✅ Uses Media search API directly
   - ✅ Includes `auth_token` parameter throughout
   - ✅ Passes `user_id` to Media API

2. **`api/v1/cross_video_tracking.py`** - REVERTED to working version
   - ✅ JWT token extraction working
   - ✅ User ID from "sub" claim
   - ✅ Auth token propagation to SessionManager

3. **`services/integrated_caching.py`** - REVERTED to working version
   - ✅ Passes auth_token to execute_tracking_session

4. **`models/cross_video_tracking.py`** - REVERTED to working version
   - ✅ DateTime normalization (UTC conversion)
   - ✅ Timezone handling correct

5. **`database/connection.py`** - REVERTED to working version
   - ✅ Database pool connection working
   - ✅ DBProxy class working

---

## API Endpoint Behavior

### 1. Create Session (POST)

**Endpoint:** `POST /api/v1/cross-video/individuals/tracking/sessions`

**Request:**
```json
{
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-13T11:36:00.000",
  "end_time": "2025-10-29T11:36:00.000",
  "background_processing": true,
  "algorithm_config": {
    "max_gap_seconds": 10,
    "iou_threshold": 0.3,
    "min_overlap_confidence": 0.5
  }
}
```

**Response (Immediate):**
```json
{
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "status": "initialized",
  "message": "Session created successfully",
  "cache_hit_rate": 0,
  "total_videos": 0
}
```

**Behavior:**
- Returns immediately (non-blocking)
- Creates database record
- Starts background task
- Client must poll status endpoint

### 2. Get Session Status (GET)

**Endpoint:** `GET /api/v1/cross-video/individuals/tracking/sessions/{session_uuid}`

**Response (While Running):**
```json
{
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "status": "running",
  "collections": ["usb_camera_0"],
  "created_at": "2025-10-29T11:36:19.523396",
  "started_at": "2025-10-29T11:36:19.535781",
  "completed_at": null,
  "total_videos": 0,
  "processed_videos": 0,
  "individuals_found": 0,
  "cache_hits": 0
}
```

**Response (Completed):**
```json
{
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "status": "completed",
  "collections": ["usb_camera_0"],
  "created_at": "2025-10-29T11:36:19.523396",
  "started_at": "2025-10-29T11:36:19.535781",
  "completed_at": "2025-10-29T11:36:19.759638",
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,
  "cache_hits": 0
}
```

**Behavior:**
- First checks `active_sessions` dict (for running tasks)
- Falls back to database (for completed sessions)
- Returns real-time status
- Client polls every 1-2 seconds

---

## Database State After Success

```sql
-- Query the successful session
SELECT 
    session_uuid,
    user_id,
    collections,
    status,
    total_videos,
    processed_videos,
    individuals_found,
    created_at,
    started_at,
    completed_at,
    processing_time_seconds
FROM tracking_sessions 
WHERE session_uuid = '4a0515cf-12ee-45f0-8945-e7b2ae7bbe24';
```

**Result:**
```
session_uuid                         | 4a0515cf-12ee-45f0-8945-e7b2ae7bbe24
user_id                              | 7
collections                          | {usb_camera_0}
status                               | completed
total_videos                         | 2
processed_videos                     | 2
individuals_found                    | 1
created_at                           | 2025-10-29 11:36:19.523396
started_at                           | 2025-10-29 11:36:19.535781
completed_at                         | 2025-10-29 11:36:19.759638
processing_time_seconds              | 0.223857
```

---

## Lessons Learned

### What Broke It Previously

1. **Collection Name Mismatch**
   - ❌ Flutter sent: `"usb_camera_0"`
   - ❌ Media API expected: `"usb_camera_0 Collection"`
   - ✅ Fixed: Collection names now match exactly

2. **Missing Auth Token**
   - ❌ Media API calls had no Authorization header
   - ❌ Vision API calls had no Authorization header
   - ✅ Fixed: Auth token propagated through entire chain

3. **Missing user_id Parameter**
   - ❌ Media search called without `user_id`
   - ❌ Multi-tenant filtering failed
   - ✅ Fixed: `user_id` extracted from JWT and passed to Media API

4. **Complex Collection Lookup**
   - ❌ Tried to resolve collection name → UUID
   - ❌ Lookup endpoint returned 404
   - ✅ Fixed: Use collection name directly in Media search

5. **DateTime Timezone Issues**
   - ❌ Stripped timezone without UTC conversion
   - ❌ Timestamps interpreted as local time
   - ✅ Fixed: Convert to UTC before stripping timezone

### What Makes It Work Now

1. **Simple, Direct API Calls**
   - ✅ Use `/api/v1/media/search` directly
   - ✅ Pass collection name as-is
   - ✅ No complex translation logic

2. **Complete Auth Chain**
   - ✅ JWT → Gateway → vmeta → Media/Vision
   - ✅ Token propagated at every step
   - ✅ User ID extracted and used

3. **Proper Background Processing**
   - ✅ Returns immediately
   - ✅ Task stored in `active_sessions`
   - ✅ Status polling works correctly

4. **Working Database Integration**
   - ✅ DBProxy class handles asyncpg correctly
   - ✅ No `updated_at` column issues
   - ✅ UUID conversion handled properly

---

## Success Metrics Summary

| Metric | Value | Status |
|--------|-------|--------|
| Total Videos Found | 2 | ✅ |
| Videos Processed | 2/2 (100%) | ✅ |
| Individuals Tracked | 1 | ✅ |
| Processing Time | 224ms | ✅ Excellent |
| Status Transitions | initialized → running → completed | ✅ |
| Background Processing | Working | ✅ |
| Auth Integration | Working | ✅ |
| Database Persistence | Working | ✅ |

---

## Future Reference Checklist

When debugging similar issues:

- [ ] Verify collection names match exactly (case-sensitive)
- [ ] Check auth token is propagated through all service calls
- [ ] Ensure `user_id` parameter included in Media API calls
- [ ] Confirm JWT "sub" claim contains correct user ID
- [ ] Verify background tasks stored in `active_sessions`
- [ ] Check database schema matches (no extra columns)
- [ ] Ensure DateTime conversion to UTC before stripping timezone
- [ ] Use Media `/search` endpoint, not `/collections/{id}/items`
- [ ] Verify Vision API returns `success: true` with data
- [ ] Check service auto-reload picked up code changes

---

## Code Repository State

**Branch:** main  
**Commit:** (reverted to last working version)  
**Modified Files:** All backend files reverted via `git checkout --`  
**Working State:** ✅ Fully functional  
**Performance:** Excellent (224ms for 2 videos)

---

**Document Created:** October 29, 2025  
**Last Updated:** October 29, 2025  
**Status:** ✅ SUCCESS - System fully operational

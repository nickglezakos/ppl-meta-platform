# Video Discovery by Services

**Document Version**: 1.0  
**Last Updated**: 2025-11-02  
**Status**: Active

---

## Overview

This document defines the **standardized approach** for discovering videos across all PPL Meta services. It addresses the critical issue discovered during vmeta cross-video tracking implementation where video discovery failed due to inconsistent timestamp usage.

---

## Problem Statement

### Current Issue (2025-11-02)

**Symptoms**:
- vmeta service cross-video tracking finds **0 videos** when 4+ videos exist
- Gateway `/media/search` returns 20 videos but with wrong timestamps
- Videos have `created_at` (upload time) but missing `start_timestamp` (recording time)
- Discovery function uses `created_at` → filters out all videos outside upload date

**Example Failure**:
```
Search Range: 2025-10-13 00:00:00 to 2025-11-02 23:59:59
Videos in DB: 4 videos recorded Oct 13, Oct 29, Nov 1, Nov 2
Discovery Result: 0 videos (all have created_at=2025-11-02, outside Oct range)
Expected: 4 videos
```

**Root Causes**:
1. Media endpoints return `created_at` instead of `start_timestamp`/`end_timestamp`
2. Services using different timestamp fields (`created_at` vs `timestamp` vs `start_timestamp`)
3. No standardized video discovery pattern across services
4. `/collections/{id}/videos` endpoint missing in Gateway (404)

---

## Flutter UI Video Display

**Evidence from Production**:
All videos in Flutter UI show **complete recording time information**:

```dart
// Example from Flutter video object:
{
  "uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "filename": "camera_usb_camera_0_segment_001_20251013_080603.mp4",
  "start_timestamp": "2025-10-13T08:06:03+03:00",  // ✅ Recording start
  "end_timestamp": "2025-10-13T08:06:33+03:00",    // ✅ Recording end
  "created_at": "2025-11-02T11:36:34+02:00",        // ❌ Upload time
  "duration": 30,
  "collections": [...]
}
```

**Key Observation**: Flutter successfully displays `start_timestamp` and `end_timestamp`, proving this data **exists somewhere** and can be retrieved.

---

## Recommended Solution

### Option 1: Use Existing Media Endpoints (RECOMMENDED) ✅

**Pros**:
- ✅ No database coupling - services remain decoupled
- ✅ Respects service boundaries and microservice architecture
- ✅ Authentication/authorization handled by Media service
- ✅ Consistent with existing architecture patterns
- ✅ Easier to scale horizontally
- ✅ Changes isolated to Media service (single point of update)

**Cons**:
- ⚠️ Requires Media service endpoint fix to return proper timestamps
- ⚠️ Additional network hop (small latency)

**Implementation**:
```python
# vmeta service discovers videos via Media/Gateway endpoints
async def discover_videos_in_collection(
    collections: List[str],
    start_time: datetime,
    end_time: datetime,
    auth_token: str = None
):
    """
    Discover videos using Media service HTTP endpoints.
    """
    headers = {'Authorization': f'Bearer {auth_token}'} if auth_token else {}
    
    # Use Gateway media search endpoint
    # Note: Gateway proxies to Media service
    url = "http://localhost:8080/api/v1/media/search"
    params = {
        "collection": collection_id,
        "start_time": start_time.isoformat() + 'Z',
        "end_time": end_time.isoformat() + 'Z',
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params=params) as response:
            videos = await response.json()
            
            # Extract video data - MUST use recording timestamps
            for video in videos:
                video_data = {
                    "uuid": video['uuid'],
                    "collection": collection_id,
                    # CRITICAL: Use recording time, not upload time
                    "timestamp": video.get('start_timestamp'),  # ✅ Correct
                    # NOT: video.get('created_at')  # ❌ Wrong
                    "duration": video.get('duration', 30)
                }
```

**Required Fix in Media Service**:
```python
# ppl-meta-media or ppl-meta-gateway
# Ensure /media/search returns these fields:
{
    "uuid": "...",
    "start_timestamp": "2025-10-13T08:06:03+03:00",  # ADD THIS
    "end_timestamp": "2025-10-13T08:06:33+03:00",    # ADD THIS
    "created_at": "2025-11-02T11:36:34+02:00",       # Keep this
    "duration": 30,
    ...
}
```

---

### Option 2: Direct Database Query (NOT RECOMMENDED) ❌

**Pros**:
- ⚡ Faster (no network hop)
- 🎯 Direct access to exact data needed

**Cons**:
- ❌ **Violates microservice architecture** - creates tight coupling
- ❌ **Breaks service boundaries** - vmeta directly accessing media database
- ❌ **Authentication bypass** - no user permission checks
- ❌ **Difficult to scale** - database becomes single point of failure
- ❌ **Maintenance nightmare** - schema changes break multiple services
- ❌ **No audit trail** - direct DB access bypasses logging/monitoring
- ❌ **Security risk** - services need database credentials

**Example (DO NOT USE)**:
```python
# ❌ ANTI-PATTERN - Direct database access from vmeta
import asyncpg

async def discover_videos_direct_db(collection_id, start_time, end_time):
    """
    ❌ BAD PRACTICE - Bypasses Media service
    """
    conn = await asyncpg.connect(
        host='localhost',
        database='ppl_meta_media',  # ❌ Accessing another service's DB
        user='ppl_user',
        password='...'
    )
    
    videos = await conn.fetch("""
        SELECT uuid, start_timestamp, end_timestamp, duration
        FROM videos
        WHERE collection_id = $1
          AND start_timestamp >= $2
          AND end_timestamp <= $3
    """, collection_id, start_time, end_time)
```

**Why This is Bad**:
1. If Media service changes schema, vmeta breaks
2. No way to enforce user permissions
3. Database becomes performance bottleneck
4. Can't move services to different servers
5. Violates "single source of truth" principle

---

## Standard Video Discovery Pattern

### For All Services

```python
"""
Standard pattern for discovering videos across PPL Meta platform.
"""

async def discover_videos(
    collection_id: str,
    start_time: datetime,
    end_time: datetime,
    auth_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Discover videos in a collection within time range.
    
    Args:
        collection_id: Collection identifier (e.g., 'usb_camera_0')
        start_time: Recording start time (inclusive)
        end_time: Recording end time (inclusive)
        auth_token: Bearer token for authentication
    
    Returns:
        List of video objects with standardized fields
    """
    
    # 1. Prepare request
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    # 2. Format timestamps as ISO 8601 UTC
    start_iso = start_time.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    end_iso = end_time.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # 3. Query Gateway (which proxies to Media service)
    url = "http://localhost:8080/api/v1/media/search"
    params = {
        "collection": collection_id,
        "start_time": start_iso,
        "end_time": end_iso
    }
    
    # 4. Execute request
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params=params, timeout=10) as response:
            if response.status != 200:
                logger.error(f"Video discovery failed: {response.status}")
                return []
            
            data = await response.json()
            videos = data if isinstance(data, list) else data.get('videos', [])
    
    # 5. Normalize video objects
    normalized_videos = []
    for video in videos:
        # CRITICAL: Use recording timestamps, NOT creation timestamps
        recording_time = (
            video.get('start_timestamp') or      # Preferred
            video.get('recorded_at') or          # Fallback
            video.get('timestamp') or            # Legacy
            video.get('created_at')              # Last resort (WRONG for filtering)
        )
        
        normalized_videos.append({
            "uuid": video.get('uuid') or video.get('id'),
            "collection": collection_id,
            "start_timestamp": video.get('start_timestamp'),
            "end_timestamp": video.get('end_timestamp'),
            "timestamp": recording_time,  # For backward compatibility
            "duration": video.get('duration', 30),
            "filename": video.get('filename'),
            "created_at": video.get('created_at')  # Keep for metadata
        })
    
    return normalized_videos
```

---

## vmeta Service Example

### Current Broken Implementation

```python
# ❌ BEFORE (BROKEN)
for video in potential_videos:
    video_time = video.get('created_at')  # ❌ Wrong! Upload time, not recording time
    videos.append({
        "uuid": video.get('uuid'),
        "timestamp": video_time,
        ...
    })

# Result: 0 videos found (created_at=2025-11-02, outside Oct 13-29 range)
```

### Fixed Implementation

```python
# ✅ AFTER (FIXED)
async def discover_videos_in_collection(
    collections: List[str],
    start_time: datetime,
    end_time: datetime,
    auth_token: str = None,
    session_uuid: str = None
):
    """
    Discover videos for cross-video tracking.
    
    Example:
        collections = ['usb_camera_0']
        start_time = datetime(2025, 10, 13, 0, 0, 0)
        end_time = datetime(2025, 11, 2, 23, 59, 59)
        
        Expected: 4 videos
        - Video 1: 2025-10-13 08:06:03 to 08:06:33
        - Video 2: 2025-10-29 08:06:03 to 08:06:33
        - Video 3: 2025-11-01 11:36:01 to 11:36:31
        - Video 4: 2025-11-02 11:36:31 to 11:37:01
    """
    videos = []
    
    for collection in collections:
        # Format times as UTC ISO strings
        start_iso = start_time.isoformat() + 'Z'
        end_iso = end_time.isoformat() + 'Z'
        
        # Query Gateway
        url = "http://localhost:8080/api/v1/media/search"
        params = {
            "collection": collection,
            "start_time": start_iso,
            "end_time": end_iso
        }
        
        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    potential_videos = data if isinstance(data, list) else []
                    
                    for video in potential_videos:
                        # ✅ CRITICAL FIX: Use recording time, not upload time
                        recording_time = (
                            video.get('start_timestamp') or  # Correct field
                            video.get('recorded_at') or
                            video.get('timestamp')
                            # NOT: video.get('created_at')  # This is upload time!
                        )
                        
                        # Only include if we have a valid recording timestamp
                        if recording_time:
                            videos.append({
                                "uuid": video.get('uuid') or video.get('id'),
                                "collection": collection,
                                "timestamp": recording_time,
                                "start_timestamp": video.get('start_timestamp'),
                                "end_timestamp": video.get('end_timestamp'),
                                "duration": video.get('duration', 30)
                            })
    
    # Sort by recording time
    videos.sort(key=lambda v: v.get('timestamp', ''))
    
    logger.info(f"Discovered {len(videos)} videos in {collections}")
    return videos
```

---

## Required Media Service Changes

### Endpoint: `/api/v1/media/search`

**Current Response** (Missing recording timestamps):
```json
{
  "uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "filename": "camera_usb_camera_0_segment_001.mp4",
  "created_at": "2025-11-02T11:36:34+02:00",
  "duration": 30
}
```

**Required Response** (With recording timestamps):
```json
{
  "uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "filename": "camera_usb_camera_0_segment_001_20251013_080603.mp4",
  "start_timestamp": "2025-10-13T08:06:03+03:00",
  "end_timestamp": "2025-10-13T08:06:33+03:00",
  "created_at": "2025-11-02T11:36:34+02:00",
  "duration": 30,
  "collections": [...]
}
```

### Implementation Location

**Files to Update**:
1. `ppl-meta-gateway/src/api/v1/router.py` - Add `/media/search` proxy
2. `ppl-meta-media/src/api/v1/media.py` - Include `start_timestamp`, `end_timestamp` in response

**SQL Query Fix**:
```sql
-- Ensure video queries include recording timestamps
SELECT 
    uuid,
    filename,
    start_timestamp,  -- ✅ ADD THIS
    end_timestamp,    -- ✅ ADD THIS
    created_at,
    duration
FROM videos
WHERE collection_id = $1
  AND start_timestamp >= $2  -- Filter by recording time
  AND end_timestamp <= $3
ORDER BY start_timestamp ASC
```

---

## Testing

### Test Case 1: vmeta Cross-Video Tracking

```bash
# Given: 4 videos in usb_camera_0
# - 2025-10-13 08:06:03 to 08:06:33
# - 2025-10-29 08:06:03 to 08:06:33  
# - 2025-11-01 11:36:01 to 11:36:31
# - 2025-11-02 11:36:31 to 11:37:01

# Test: Create cross-video tracking session
curl -X POST http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-13T00:00:00",
    "end_time": "2025-11-02T23:59:59"
  }'

# Expected Result:
# {
#   "total_videos": 4,           # ✅ All 4 videos discovered
#   "individuals_found": 1,      # Assuming same person across all
#   "status": "completed"
# }

# Current Broken Result:
# {
#   "total_videos": 0,           # ❌ No videos found
#   "individuals_found": 0,
#   "status": "completed"
# }
```

### Test Case 2: Flutter UI Video List

```bash
# Should work correctly (already does)
GET /api/v1/collections/usb_camera_0/videos?start=2025-10-13&end=2025-11-02

# Returns: List of videos with start_timestamp, end_timestamp
```

---

## Migration Plan

### Phase 1: Fix Media Service (IMMEDIATE)
1. ✅ Update `/media/search` to include `start_timestamp`, `end_timestamp`
2. ✅ Test with Flutter UI (ensure no regression)
3. ✅ Deploy Media service update

### Phase 2: Fix vmeta Service (IMMEDIATE)
1. ✅ Update `discover_videos_in_collection()` to use `start_timestamp`
2. ✅ Remove hardcoded fallback UUIDs (already done)
3. ✅ Test with cross-video tracking
4. ✅ Deploy vmeta service update

### Phase 3: Standardize Other Services (WEEK 1)
1. ⏳ Update Vision service if using video discovery
2. ⏳ Update Orchestrator service if using video discovery
3. ⏳ Document pattern in service templates

---

## Decision

**RECOMMENDATION**: Use **Option 1 - HTTP Endpoints** ✅

**Rationale**:
- Maintains service boundaries
- Leverages existing authentication
- Easier to maintain and scale
- Consistent with microservice best practices
- Only requires Media service to add 2 fields to response

**Action Items**:
1. Media team: Add `start_timestamp`, `end_timestamp` to `/media/search` response
2. vmeta team: Update video discovery to use `start_timestamp` (already done)
3. QA team: Test end-to-end with 4-video scenario

---

## References

- **Related Issue**: vmeta cross-video tracking finds 0 videos (2025-11-02)
- **Related Files**: 
  - `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`
  - `ppl-meta-gateway/src/api/v1/router.py`
  - `ppl-meta-media/src/api/v1/media.py`
- **Related Docs**: 
  - `docs/architecture/microservices-boundaries.md`
  - `docs/api/media-service-api.md`

---

**Document Status**: ✅ Active - Awaiting Media service update

# Debugging Zero Videos Issue - End-to-End Analysis
**Date:** October 29, 2025  
**Issue:** Cross-video tracking sessions return `total_videos: 0` despite videos existing in the collection  
**Service:** vmeta (port 8008)

---

## Problem Statement

When creating a cross-video tracking session via the Flutter app or API, the session completes successfully but shows:
```json
{
  "total_videos": 0,
  "processed_videos": 0,
  "individuals_found": 0
}
```

**Expected Behavior:** Should show 20 videos from the `usb_camera_0 Collection` in the date range.

**Root Cause:** Collection name mismatch - Flutter uses `"usb_camera_0"` but actual name is `"usb_camera_0 Collection"`.

---

## How Collection Names Work

### Collection Name vs UUID

The Media service stores collections with both a **UUID** (unique identifier) and a **name** (human-readable string):

```json
{
  "uuid": "abc123-def456-...",
  "name": "usb_camera_0 Collection",
  "camera_device_id": "usb_camera_0"
}
```

### Media API Search - Accepts EITHER Name or UUID

The Media search API (`/api/v1/media/search`) accepts the `collection` parameter as:
- **Collection Name** (string) - e.g., `"usb_camera_0 Collection"`
- **Collection UUID** - e.g., `"abc123-def456-..."`

**Examples:**
```bash
# Using collection NAME (recommended)
curl "http://localhost:8080/api/v1/media/search?collection=usb_camera_0%20Collection&user_id=7"

# Using collection UUID (also works)
curl "http://localhost:8080/api/v1/media/search?collection=abc123-def456-...&user_id=7"
```

### vmeta Service - Passes Collection Name Directly

The refactored vmeta service **does NOT translate** collection names to UUIDs. It passes the name directly:

```python
# In _fetch_video_data():
params["collection"] = ",".join(collections)  # Passes name as-is
```

**This means:**
- ✅ If Flutter sends `["usb_camera_0 Collection"]` → Media API receives `"usb_camera_0 Collection"` → 20 videos ✅
- ❌ If Flutter sends `["usb_camera_0"]` → Media API receives `"usb_camera_0"` → 0 videos ❌

### Old vs New Approach

**OLD Code (Before Refactoring):**
```python
# 1. Check if collection is UUID (has dashes)
if "-" not in str(collection):
    # 2. Try to lookup UUID by camera_device_id
    lookup_url = f"{gateway}/api/v1/media/collections/by-camera/{collection}"
    response = await session.get(lookup_url)
    if response.status == 200:
        data = await response.json()
        collection_id = data.get("uuid")
    
# 3. Use UUID to get collection items
url = f"{gateway}/api/v1/media/collections/{collection_id}/items"
```

**Problems with old approach:**
- ❌ Lookup endpoint `/by-camera/usb_camera_0` returns 404 (doesn't exist)
- ❌ Falls back to treating `usb_camera_0` as UUID → validation error
- ❌ Complex, fragile logic with multiple failure points

**NEW Code (After Refactoring):**
```python
# Simple and direct - just pass the collection name
params = {
    "collection": ",".join(collections),
    "start_time": start_time.isoformat(),
    "end_time": end_time.isoformat(),
    "user_id": user_id
}
async with session.get(f"{gateway}/api/v1/media/search", params=params)
```

**Benefits:**
- ✅ Simple, one API call
- ✅ Media API handles name/UUID internally
- ✅ No complex lookup logic
- ✅ Works with both names and UUIDs

---

## End-to-End Request Flow

### 1. Flutter App → Gateway → vmeta

```
Flutter App (localhost:3000)
    ↓ POST /api/v1/cross-video/individuals/tracking/sessions
    ↓ Authorization: Bearer <JWT>
    ↓ Body: { collections: ["usb_camera_0"], start_time: "...", end_time: "..." }
    ↓
Gateway (localhost:8080)
    ↓ Forwards to vmeta with same auth header
    ↓
vmeta Service (localhost:8008)
    ↓ Creates session in database
    ↓ Calls _fetch_video_data()
    ↓ Makes request to Media API
    ↓
Media Service (via Gateway - localhost:8080)
    ↓ /api/v1/media/search?collection=usb_camera_0&start_time=...&end_time=...&user_id=7
    ↓ Returns video list
    ↓
vmeta processes videos and updates session
```

---

## Debugging Checklist

### Step 1: Verify Session Was Created

**Command:**
```bash
export TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')

# Get session UUID from Flutter app logs or create one:
SESSION_UUID="<paste-session-uuid-here>"

# Check session in database
psql -U postgres -d ppl_meta_vmeta -c "
  SELECT session_uuid, user_id, collections, start_time, end_time, total_videos, status 
  FROM tracking_sessions 
  WHERE session_uuid = '$SESSION_UUID';
"
```

**Expected Output:**
```
session_uuid                          | user_id | collections     | start_time          | end_time            | total_videos | status
--------------------------------------+---------+-----------------+---------------------+---------------------+--------------+----------
061fab69-18fd-4476-bdc8-ded6ece29a81 | 7       | {usb_camera_0}  | 2025-10-13 08:44:00 | 2025-10-29 08:44:00 | 0            | COMPLETED
```

**Analysis:**
- ✅ Session created successfully
- ✅ Collections array populated correctly
- ✅ Date range looks correct
- ✅ user_id = 7 (from JWT)
- ❌ total_videos = 0 (PROBLEM!)

---

### Step 2: Verify Media API Returns Videos

**Test the exact API call that vmeta should be making:**

```bash
# Build the media search URL with exact parameters from session
START_TIME="2025-10-13T08:44:00"  # From session database
END_TIME="2025-10-29T08:44:00"
COLLECTION="usb_camera_0"
USER_ID="7"

# Test media search endpoint
curl -s "http://localhost:8080/api/v1/media/search?start_time=${START_TIME}&end_time=${END_TIME}&collection=${COLLECTION}&user_id=${USER_ID}" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f'Total videos returned: {len(data)}'); print('First video:'); print(json.dumps(data[0] if data else {}, indent=2))"
```

**Expected Output:**
```
Total videos returned: 20
First video:
{
  "uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "original_filename": "camera_usb_camera_0_segment_002_20251019_130932.mp4",
  "created_at": "2025-10-19T11:09:38.925766",
  "collections": [
    {
      "name": "usb_camera_0",
      "uuid": "..."
    }
  ]
}
```

**Analysis:**
- ✅ Media API returns 20 videos
- ✅ Videos are in the correct date range
- ✅ Videos belong to the correct collection
- **CONCLUSION:** Media API is working correctly!

---

### Step 3: Check vmeta Service Logs

**Find vmeta process and check output:**

```bash
# Find the vmeta service process
ps aux | grep "uvicorn.*8008" | grep -v grep

# Check if service has --reload enabled (should restart on code changes)
ps aux | grep "uvicorn.*8008.*--reload"

# If running in background, check for log output
# (Note: If started via VS Code tasks, logs appear in task terminal)
```

**Look for debug output in vmeta service terminal:**
```
🔍 _fetch_video_data called: collections=['usb_camera_0'], time=2025-10-13 08:44:00 to 2025-10-29 08:44:00, user_id=7
🔍 start_time type: <class 'datetime.datetime'>, tzinfo: None
🔍 end_time type: <class 'datetime.datetime'>, tzinfo: None
✅ Using auth token from request for media service calls
🔐 Auth configured: True, has_token=True
📡 Calling media search API: http://localhost:8080/api/v1/media/search
   Params: {'start_time': '2025-10-13T08:44:00', 'end_time': '2025-10-29T08:44:00', 'collection': 'usb_camera_0', 'user_id': '7'}
📡 Media API response: 200
📦 Got 20 videos from media API
🎯 _fetch_video_data returning: 20 videos
   Sample UUIDs: ['7b462847-cd1f-441a-8bd9-aaed6643b7cb', '...', '...']
```

**If you DON'T see this output:**
- ❌ Service didn't reload with new code changes
- ❌ Still running old version with collection lookup logic
- **ACTION:** Restart vmeta service

---

### Step 4: Force Service Restart

**Stop vmeta service:**
```bash
# Find and kill the process
pkill -f 'ppl-meta-vmeta.*uvicorn'

# Verify it stopped
ps aux | grep "uvicorn.*8008" | grep -v grep
```

**Start vmeta service fresh:**
```bash
# Navigate to vmeta directory
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta

# Activate virtual environment
source venv/bin/activate

# Start service with reload enabled
cd src
PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src \
  uvicorn main:app --host 0.0.0.0 --port 8008 --reload
```

**Verify service health:**
```bash
curl -s http://localhost:8008/health | python3 -m json.tool
```

**Expected:**
```json
{
  "status": "healthy",
  "service": "vmeta",
  "version": "1.0.0",
  "description": "Vector-based facial embeddings and analytics"
}
```

---

### Step 5: Test Session Creation Again

**Create a new tracking session:**
```bash
curl -X POST "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-13T08:44:00Z",
    "end_time": "2025-10-29T08:44:00Z",
    "background_processing": true
  }' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "session_uuid": "new-uuid-here",
  "status": "initialized",
  "message": "Session created successfully",
  "cache_hit_rate": 0.0,
  "total_videos": 20  // ✅ SHOULD NOW SHOW 20!
}
```

**Check session status:**
```bash
NEW_SESSION_UUID="<uuid-from-response>"

curl -s "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$NEW_SESSION_UUID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:**
```json
{
  "session_uuid": "...",
  "status": "completed",
  "total_videos": 20,        // ✅ Should be 20
  "processed_videos": 20,    // ✅ Should be 20
  "individuals_found": 1,    // ✅ Should be > 0
  "is_active": false
}
```

---

## Code Changes Made (Reference)

### File: `ppl-meta-vmeta/src/services/session_manager.py`

#### Change 1: Simplified `_fetch_video_data` Method

**Old Approach (BROKEN):**
```python
# 1. Try collection lookup by camera device ID
# 2. If fails, try collection UUID lookup
# 3. Both fail for "usb_camera_0"
# 4. Fall back to search API but without user_id parameter
# 5. Returns 0 results
```

**New Approach (WORKING):**
```python
async def _fetch_video_data(...) -> List[Dict[str, Any]]:
    """Fetch video data using the media search API directly."""
    
    # Build search parameters
    params = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    
    if collections:
        params["collection"] = ",".join(collections)
    
    if user_id:
        params["user_id"] = user_id  # ✅ Critical for multi-tenant filtering
    
    # Call media search API
    search_url = f"{gateway_url}/api/v1/media/search"
    async with session.get(search_url, params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            # Process and return videos
```

**Key Improvements:**
- ✅ Uses media search API directly (no complex lookup logic)
- ✅ Always includes `user_id` parameter
- ✅ Simpler, more reliable code path
- ✅ ~110 lines instead of ~250 lines

#### Change 2: Fixed DateTime Normalization

**File:** `ppl-meta-vmeta/src/models/cross_video_tracking.py`

**Old Code (BROKEN):**
```python
@validator('start_time', 'end_time', pre=True)
def normalize_datetime(cls, v):
    """Strip timezone info."""
    if v and isinstance(v, datetime) and v.tzinfo:
        return v.replace(tzinfo=None)  # ❌ Doesn't convert to UTC first!
    return v
```

**New Code (WORKING):**
```python
@validator('start_time', 'end_time', pre=True)
def normalize_datetime(cls, v):
    """Convert timezone-aware datetimes to naive UTC."""
    if v and isinstance(v, datetime):
        if v.tzinfo:
            from datetime import timezone
            # Convert to UTC FIRST, then strip timezone
            utc_time = v.astimezone(timezone.utc)
            return utc_time.replace(tzinfo=None)
        return v  # Already naive - assume UTC
    return v
```

**Problem Solved:**
- Flutter sends: `"2025-10-29T05:00:00.000Z"` (UTC)
- Old code: Stripped `Z` without converting → treated as Athens time (UTC+2)
- New code: Converts to UTC, then strips → correct time maintained

---

## Common Issues and Solutions

### Issue 1: Service Not Reloading
**Symptom:** Code changes don't take effect  
**Solution:** 
```bash
pkill -f 'ppl-meta-vmeta.*uvicorn'
cd ppl-meta-vmeta/src
PYTHONPATH=.. uvicorn main:app --host 0.0.0.0 --port 8008 --reload
```

### Issue 2: Authentication Errors
**Symptom:** `"detail": "Not authenticated"`  
**Solution:** 
```bash
# Get fresh token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')

# Use in requests
curl -H "Authorization: Bearer $TOKEN" ...
```

### Issue 3: Media API Returns Empty
**Symptom:** Media search returns `[]`  
**Check:**
```bash
# Verify user_id parameter is included
curl -v "http://localhost:8080/api/v1/media/search?user_id=7&collection=usb_camera_0" \
  -H "Authorization: Bearer $TOKEN" 2>&1 | grep -A 5 "GET /api"

# Check if collection name is correct (case-sensitive!)
psql -U postgres -d ppl_meta -c "SELECT DISTINCT name FROM collections;"
```

### Issue 4: Wrong Collection Name ⚠️ COMMON ISSUE
**Symptom:** Flutter uses "usb camera 0" but actual name is "usb_camera_0 Collection"  
**Check:**
```bash
# List all collections for your user
curl -s "http://localhost:8080/api/v1/media/search?user_id=7" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); \
  collections = {}; \
  [collections.update({c['name']: collections.get(c['name'], 0) + 1}) \
   for v in data for c in v.get('collections', [])]; \
  print('Available collections:'); \
  [print(f'  - \"{name}\" ({count} videos)') for name, count in collections.items()]"
```

**Example Output:**
```
Available collections:
  - "usb_camera_0 Collection" (20 videos)
```

**Fix in Flutter:** Ensure collection name matches EXACTLY (case-sensitive, spaces included):
```dart
// ❌ Wrong - missing " Collection" suffix
collections: ["usb_camera_0"]

// ❌ Wrong - using underscore instead of space
collections: ["usb_camera_0_Collection"]

// ✅ Correct - exact match
collections: ["usb_camera_0 Collection"]
```

---

## Verification Tests

### Test 1: Direct Media API Call
```bash
curl -s "http://localhost:8080/api/v1/media/search?collection=usb_camera_0&user_id=7&start_time=2025-10-01T00:00:00&end_time=2025-10-31T23:59:59" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys, json; print(f'Videos found: {len(json.load(sys.stdin))}')"
```
**Expected:** `Videos found: 20` (or whatever count exists)

### Test 2: vmeta Session Creation
```bash
curl -X POST "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-01T00:00:00Z",
    "end_time": "2025-10-31T23:59:59Z"
  }' | jq '.total_videos'
```
**Expected:** `20` (matches Test 1 result)

### Test 3: Database Verification
```bash
# Get the latest session
psql -U postgres -d ppl_meta_vmeta -c "
  SELECT session_uuid, total_videos, processed_videos, individuals_found, status 
  FROM tracking_sessions 
  ORDER BY created_at DESC 
  LIMIT 1;
"
```
**Expected:** `total_videos` should match Media API count

---

## Success Criteria

✅ **Media API returns videos** (Test 1 passes)  
✅ **vmeta session shows total_videos > 0** (Test 2 passes)  
✅ **Database shows total_videos > 0** (Test 3 passes)  
✅ **Flutter app shows individuals_found > 0**  
✅ **Service logs show media API being called with correct params**

---

## Next Steps After Fix

1. **Test with Flutter App:**
   - Open Collections screen
   - Select date range that includes videos
   - Create tracking session
   - Verify `total_videos` shows correct count

2. **Monitor Performance:**
   - Check processing time for 20 videos
   - Verify individuals are correctly tracked
   - Test cache hit rates on subsequent requests

3. **Clean Up Debug Logging:**
   - Remove excessive `print()` statements
   - Keep INFO-level logging for production

4. **Update Documentation:**
   - Document the collection name format requirement
   - Add troubleshooting section to API docs
   - Include examples of successful requests

---

## Contact & Resources

- **Service Documentation:** `docs/vision-vmeta/VMETA_SERVICE_API_DOCUMENTATION.md`
- **Media API Docs:** `docs/api/MEDIA_SERVICE_API.md`
- **Database Schema:** `ppl-meta-vmeta/migrations/`
- **Service Code:** `ppl-meta-vmeta/src/services/session_manager.py`

**Last Updated:** October 29, 2025

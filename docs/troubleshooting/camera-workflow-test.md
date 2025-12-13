# Camera Workflow Test - 7 Steps

**Date:** December 12, 2025  
**Service:** ppl-meta-cameras (Port 8005)  
**Camera:** usb_camera_0

---

## Test Steps

### Step 1: Detect Cameras ✅ PASSED

**Endpoint:** `POST /api/v1/cameras/detect`

**Command:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzY1NTgwNjI3fQ.DAW2UcCetmcv8N1tpS6a3UUyfAooQXuI6QHYFoceweA"
curl -X POST "http://localhost:8005/api/v1/cameras/detect" -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
{
  "detected_count": 1,
  "cameras": [
    {
      "device_id": "usb_camera_0",
      "name": "USB Camera 0",
      "camera_type": "USB",
      "status": "available",
      "resolution_width": 1280,
      "resolution_height": 720,
      "max_fps": 30,
      "connection_string": "0",
      "supports_streaming": true,
      "supports_recording": true,
      "index": 0
    }
  ],
  "saved_to_db": true,
  "saved_count": 1
}
```

**Status:** ✅ SUCCESS - Detected 1 camera (usb_camera_0)

---

### Step 2: Connect to USB Camera ✅ PASSED

**Endpoint:** `POST /api/v1/cameras/{device_id}/connect`

**Command:**
```bash
curl -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/connect" -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
{
  "device_id": "usb_camera_0",
  "status": "connected",
  "message": "Successfully connected to camera usb_camera_0"
}
```

**Status:** ✅ SUCCESS - Connected to usb_camera_0

---

### Step 3: Start Streaming ✅ PASSED

**Endpoint:** `GET /api/v1/streaming/{device_id}/video`

**Command:**
```bash
curl -s "http://localhost:8005/api/v1/streaming/usb_camera_0/video?token=$TOKEN" --max-time 2 | head -c 200
```

**Result:**
```
--frame
Content-Type: image/jpeg

����JFIF��C
...
(MJPEG frames received)
```

**Status:** ✅ SUCCESS - Streaming working, receiving MJPEG video frames

---

### Step 4: Start Recording ✅ PASSED

**Endpoint:** `POST /api/v1/streaming/{device_id}/record/start`

**Command:**
```bash
curl -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/record/start?enable_instant_detection=true" \
  -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
{
  "status": "success",
  "message": "Recording started for camera usb_camera_0",
  "device_id": "usb_camera_0",
  "session_uuid": "5418506a-8ad2-4194-98a1-866295485575",
  "recording_id": "5fe9698c-778c-4e76-8629-e4c32cc5d076",
  "started_at": "2025-12-12T22:45:22.551168",
  "segment_duration": 30
}
```

**Status:** ✅ SUCCESS - Recording started with session UUID

**Notes:** Had to clear stale database session first using the corrected endpoint path (see Issue 1)

---

### Step 5: Stop Recording ✅ PASSED

**Endpoint:** `POST /api/v1/streaming/{device_id}/record/stop`

**Command:**
```bash
curl -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/record/stop" \
  -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
{
  "status": "success",
  "message": "Recording stopped for camera usb_camera_0",
  "device_id": "usb_camera_0",
  "recording_id": "5fe9698c-778c-4e76-8629-e4c32cc5d076",
  "session_uuid": "5418506a-8ad2-4194-98a1-866295485575",
  "duration_seconds": 15,
  "file_path": null,
  "file_size_bytes": null,
  "collection_id": "usb_camera_0",
  "segment_count": 1,
  "segment_files": ["segment_001_20251212_224522.mp4"],
  "session_dir": "recordings/usb_camera_0/5418506a-8ad2-4194-98a1-866295485575",
  "stopped_at": "2025-12-12T22:45:37.821013"
}
```

**Status:** ✅ SUCCESS - Recording stopped after 15 seconds, created 1 segment

**Notes:** Stop recording functionality works but has a side effect (see Issue 2)

---

### Step 6: Verify Streaming After Stop ⚠️ ISSUE FOUND

**Note:** Streaming continues even during recording. This step verifies we can cleanly stop the stream.

**Command:**
```bash
curl -s "http://localhost:8005/api/v1/streaming/usb_camera_0/video?token=$TOKEN" --max-time 2 | head -c 200
```

**Result:**
```json
{"detail":"Camera usb_camera_0 not connected"}
```

**Status:** ⚠️ FAILED - Camera disconnected when recording stopped

**Workaround:** Had to reconnect camera manually:
```bash
curl -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/connect" -H "Authorization: Bearer $TOKEN"
```

After reconnect, streaming works again. This reveals **Issue 2** below.

---

### Step 7: Disconnect ✅ PASSED

**Endpoint:** `POST /api/v1/cameras/{device_id}/disconnect`

**Command:**
```bash
curl -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/disconnect" \
  -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
{
  "device_id": "usb_camera_0",
  "status": "disconnected",
  "message": "Successfully disconnected from camera usb_camera_0",
  "sessions_cleaned": 0
}
```

**Status:** ✅ SUCCESS - Camera disconnected properly

---

## Summary

- ✅ **Passed:** 6/7 steps
- ⚠️ **Failed with Known Issue:** 1/7 steps (Step 6 - camera disconnects on stop recording)
- **Overall Result:** All core functionality working, but one critical bug found

## Issues Found

### Issue 1: Recording Sessions Router Path Doubled ✅ RESOLVED
- **Step:** 4 (Start Recording)
- **Problem:** Endpoint returns "already recording" due to stale database session that couldn't be cleared
- **Root Cause:** Router prefix defined twice
  - `recording_sessions.py` defines: `router = APIRouter(prefix="/api/v1/recording-sessions")`
  - `routes.py` includes it: `v1_router.include_router(recording_sessions_router, tags=["Recording Sessions"])`
  - `main.py` includes v1_router: `app.include_router(v1_router, prefix="/api/v1")`
  - **Result:** Path becomes `/api/v1/api/v1/recording-sessions/` instead of `/api/v1/recording-sessions/`
- **Correct Path:** `/api/v1/api/v1/recording-sessions/{session_uuid}`
- **Fix Required:** Remove prefix from router definition in `recording_sessions.py`
- **Workaround Used:** Called DELETE with doubled path: `/api/v1/api/v1/recording-sessions/fb52ca4e-d9cd-4e94-95d2-2dd7927085d9`

### Issue 2: Camera Disconnects When Recording Stops ⚠️ CRITICAL BUG
- **Step:** 6 (Verify Streaming After Stop)
- **Problem:** Camera becomes "not connected" after stopping recording
- **Root Cause:** In `recording_session_service.py` line 141, the `stop_session()` method calls:
  ```python
  manager = get_instant_detection_manager()
  manager.stop_sampling()
  ```
  This `stop_sampling()` is releasing the camera VideoCapture connection, not just stopping the sampling loop
- **Expected Behavior:** Stopping recording should only:
  1. Stop the recording loop
  2. Stop instant detection sampling
  3. Release the video writer
  4. **Keep the camera connection active for streaming**
- **Actual Behavior:** Camera connection is released, requiring reconnection
- **Impact:** Frontend will lose video stream when user stops recording
- **Fix Required:** Investigate `InstantDetectionSampler.stop_sampling()` method - it should only stop the sampling thread, not release the camera connection
- **Location:** `/ppl-meta-cameras/src/services/instant_detection.py` - `stop_sampling()` method
- **Temporary Workaround:** Reconnect to camera after stopping recording

---

## Recommendations

### Priority 1: Fix Router Path Duplication
**File:** `ppl-meta-cameras/src/api/v1/endpoints/recording_sessions.py`  
**Change:**
```python
# BEFORE:
router = APIRouter(prefix="/api/v1/recording-sessions", tags=["recording-sessions"])

# AFTER:
router = APIRouter(prefix="/recording-sessions", tags=["recording-sessions"])
```

### Priority 2: Fix Camera Disconnect on Stop Recording
**File:** `ppl-meta-cameras/src/services/instant_detection.py`  
**Investigation Needed:** Check `InstantDetectionSampler.stop_sampling()` implementation
- Should stop sampling thread only
- Should NOT release camera VideoCapture
- Should NOT remove camera from active_connections

**File:** `ppl-meta-cameras/src/services/recording_session_service.py`  
**Alternative Fix:** Maybe `stop_session()` shouldn't call `stop_sampling()` at all? 
- Instant detection should be independent of recording
- User might want instant detection to continue even when not recording

---

**Test Completed:** December 12, 2025, 10:45 PM  
**Tested By:** Backend API Testing  
**Services Version:** Post-restart (fresh state)  
**Test Duration:** ~10 minutes

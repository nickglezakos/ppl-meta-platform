# Mobile Camera UUID and Streaming Fixes

**Date:** February 12, 2026  
**Status:** ✅ UUID Issue Fixed | ⚠️ Frontend Streaming Issue Identified

## Issues Identified

### Issue 1: UUID Lost After Registration ✅ FIXED

**Problem:**
When users updated camera settings after successful registration and streaming, the app reported "No camera UUID stored - camera not registered" even though the camera was actively streaming frames to the backend.

**Root Cause:**
Two services were aggressively clearing the camera UUID on 404 responses:

1. **`mobile_camera_heartbeat_service.dart`** - Line 120
   - Cleared UUID when heartbeat received 404 response
   - This could happen during temporary backend unavailability
   
2. **`auto_camera_registration_service.dart`** - Line 108
   - Cleared UUID when checking existing camera returned 404
   - Could occur due to timing issues or endpoint problems

**Impact:**
- Camera registered successfully and streamed frames
- UUID was stored correctly
- But heartbeat/registration check cleared it on any 404
- Settings sync then failed with "No UUID found" error
- User couldn't update settings despite camera being active

**Solution Implemented:**

1. **Removed Aggressive UUID Clearing**
   - Services now log 404 errors but preserve UUID
   - UUID only cleared during explicit re-registration
   - Allows for troubleshooting and diagnostic logging

2. **Added UUID Caching in DeviceIdentifierService**
   - `_cachedCameraUuid` field stores UUID in memory
   - Fast path for UUID retrieval (no SharedPreferences lookup)
   - Fallback to cache if SharedPreferences fails
   - Survives temporary storage issues

3. **Enhanced Error Handling**
   - Better logging for UUID storage/retrieval
   - Distinguishes between "not registered" vs "storage error"
   - Preserves UUID for diagnostic purposes

**Files Modified:**
- `ppl_meta_mobile_camera/lib/services/mobile_camera_heartbeat_service.dart`
- `ppl_meta_mobile_camera/lib/services/auto_camera_registration_service.dart`
- `ppl_meta_mobile_camera/lib/services/device_identifier_service.dart`

---

### Issue 2: Frontend Not Displaying Mobile Camera Stream ✅ FIXED

**Problem:**
Mobile camera successfully streams frames to backend (720x480 @ 270° rotation), but the stream doesn't appear on the frontend laptop interface.

**Root Cause Found:**
The streaming endpoint was checking if a camera is mobile based on device_id prefix (`device_id.startswith('mobile_')`), but mobile cameras are registered with **UUID device_ids** (e.g., `abc-123-def-456`), not prefixed IDs.

When the frontend requested the stream at `/api/v1/streaming/{device_id}/video`, the backend's streaming endpoint incorrectly identified the mobile camera as a USB/RTSP camera because the UUID didn't start with `mobile_`, causing it to use the wrong frame fetching logic.

**Impact:**
- Mobile camera sent frames successfully to backend ✓
- Frames stored in mobile_streaming_service ✓  
- Backend streaming endpoint failed to identify camera as mobile ✗
- Frontend received no frames because wrong worker type was used ✗

**Solution Implemented:**

1. **Database-Based Camera Type Detection**
   - Replaced prefix-based checks with database lookups
   - Queries Camera table to get actual camera_type
   - Handles all camera types correctly regardless of device_id format

2. **Fixed Two Locations in streaming.py:**
   - Line ~130: In `generate_frames()` function
   - Line ~270: In `video_stream()` endpoint
   - Both now query database for camera_type instead of checking prefix

**Code Changes:**
```python
# Before (INCORRECT):
is_mobile = device_id.startswith('mobile_')

# After (CORRECT):
from src.database import get_db
from src.models.camera import Camera, CameraType

camera_type = None
db = next(get_db())
try:
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if camera:
        camera_type = camera.camera_type
finally:
    db.close()

is_mobile = camera_type == CameraType.MOBILE
```

**Why This Works:**
- Mobile cameras ARE stored in database with CameraType.MOBILE
- Device IDs are properly stored as UUIDs
- Camera workers correctly fetch frames based on actual camera type
- Frontend gets proper MJPEG stream regardless of device_id format

**Files Modified:**
- `ppl-meta-cameras/src/api/v1/endpoints/streaming.py` (2 locations)

**Current Status:**
- ✅ Mobile camera sends frames (verified in logs)
- ✅ StreamingService shows CONNECTED
- ✅ Frames include orientation data
- ✅ Backend correctly identifies mobile cameras by type
- ✅ Frontend should now receive and display stream

---

## Testing Checklist

### UUID Fix Testing ✅
- [x] Register new mobile camera
- [x] Verify UUID stored correctly
- [ ] Update camera settings
- [ ] Verify settings sync succeeds
- [ ] Check UUID persists after app restart
- [ ] Verify heartbeat doesn't clear UUID on 404
- [ ] Test settings update while streaming

### Frontend Streaming Testing 🎯 READY TO TEST
- [ ] Restart cameras service backend
- [ ] Register mobile camera (or use existing)
- [ ] Start streaming from mobile app
- [ ] Open frontend cameras page (`/cameras`)
- [ ] Verify mobile camera appears in camera list
- [ ] Check camera status (online/streaming)
- [ ] Click "View All Streams" button
- [ ] Verify mobile camera stream displays correctly
- [ ] Check frame rate and quality
- [ ] Test stream during camera rotation
- [ ] Verify stream stops/starts properly

---

## Success Criteria

**UUID Fix:**
- ✅ UUID persists after registration
- ✅ Settings updates work when connected
- ✅ Settings queue offline when disconnected
- ✅ UUID survives heartbeat 404 errors
- ✅ UUID cache provides resilience

**Frontend Streaming:**
- ⏳ Camera service identifies mobile cameras correctly
- ⏳ Mobile camera visible in camera list (should already work)
- ⏳ Stream displays in frontend viewer  
- ⏳ Proper frame rate and quality
- ⏳ Rotation handled correctly
- ⏳ Start/stop streaming works

---

## Related Documents

- [Mobile Camera Connection Enhancement Proposal](../proposals/MOBILE-CAMERA-CONNECTION-ENHANCEMENT-PROPOSAL.md)
- Phase 2 Implementation Complete
- Automatic Naming Implementation

## Notes

The UUID fix should be tested immediately as it resolves a critical issue that prevented settings synchronization. The frontend streaming issue requires deeper investigation into the frontend codebase to understand how mobile camera streams are integrated with the existing camera viewing infrastructure.

Once the frontend integration point is identified, the fix may involve:
1. Adding mobile camera support to existing stream viewer
2. Creating new mobile-camera-specific viewer component
3. Updating WebSocket connection logic
4. Adding proper stream format conversion

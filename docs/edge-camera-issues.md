# Edge Camera RPi5 Deployment - Issues & Resolution

**Date**: February 8, 2026  
**Device**: Raspberry Pi 5 @ 192.168.1.77  
**Camera**: Waveshare USB Camera (OV5640)  
**Device ID**: edge-camera-rpi5-001  
**Status**: Container running for 14+ hours, streaming working ✅

---

## Issue #1: Video Corruption - Recorded Video Unplayable

### Symptoms
- Edge camera recorded a 20-second video
- Video appears in collection but won't play in frontend
- Frontend error: `MEDIA_ERR_SRC_NOT_SUPPORTED`
- Error message: "No further diagnostic information can be determined or provided"

### Error Details
```
❌ Video URL: http://localhost:8080/api/v1/media/stream-token/d9021509-3511-4548-9bb4-2fee0a74aa22
❌ Exception: PlatformException(MEDIA_ERR_SRC_NOT_SUPPORTED)
❌ Message: "The video has been found to be unsuitable (missing or in a format not supported by your browser)"
❌ Controller State: isInitialized=false, hasError=true
```

### Video UUID
`d9021509-3511-4548-9bb4-2fee0a74aa22`

### Investigation Steps
1. Check if video file exists on media service storage
2. Verify video file format and codec (should be MP4/H.264)
3. Check file size and integrity
4. Review edge camera recording logs for encoding errors
5. Test direct file download vs stream endpoint
6. Check media service logs for transcoding/processing errors

### Root Cause ✅ IDENTIFIED
**Media Service Deduplication**:
- Media service has SHA256 hash-based deduplication (lines 51-74 in `media_service.py`)
- If same file content uploaded multiple times, returns existing UUID
- Edge camera recorded 4 segments with identical/frozen frames
- All segments hashed to same SHA256, returned same UUID: `d9021509`
- Original file was deleted/cleaned up, but UUID kept being reused
- Frontend tries to play non-existent video

**Evidence**:
- Same UUID appears 4 times (Jan 31: 19:36, 19:58, 20:06; Feb 1: 09:58)
- Different session UUIDs but same media UUID
- Media service logs show NO upload records (dedup returned cached)
- File doesn't exist in storage but UUID in database

### Solution
**Option 1**: Disable deduplication for camera recordings
- Allow multiple segments even if content identical
- Camera might have frozen frame issue

**Option 2**: Fix camera capture
- Edge camera may be sending frozen/black frames
- Check if USB camera driver working properly on RPi5
- Verify frame capture in edge camera logs

---

## Issue #2: Collection Misattribution - USB Camera Videos in Edge Camera Collection ✅ RESOLVED

### Symptoms
- Recorded videos from USB camera appearing in "Edge Camera" collection
- Expected: USB camera videos → USB camera collection
- Actual: USB camera videos → Edge camera collection

### Working Video Example
```
✅ Video UUID: 996cf780-c211-4a82-85f6-46b7cbf54e4b
✅ Duration: 0:00:08.780000
✅ Size: 1280x720
✅ Playback: Working correctly
✅ Device name in media log: 'edge-camera-001' (incorrect)
```

### Root Cause ✅ IDENTIFIED
**Camera Name vs Device ID Mismatch**:
- Upload code used `camera.name` instead of `camera.device_id` when setting `device_name` field
- Collections are linked by `camera_device_id` in MediaCollection table
- Camera registered with `device_id="edge-camera-rpi5-001"` but `name="edge-camera-001"`
- Upload sent `device_name="edge-camera-001"` (from camera.name)
- Collection lookup tried to find collection where `camera_device_id="edge-camera-001"`
- But collections are created using the `device_id` field, causing mismatch

**Code Location**: `ppl-meta-cameras/src/services/camera_detection.py` line 3079

### Solution ✅ IMPLEMENTED
Changed line 3079 from:
```python
camera_name = camera.name  # ❌ Used human-friendly name
```

To:
```python
camera_name = camera.device_id  # ✅ Use unique device_id for collection matching
```

**Result**: Uploads now use `camera.device_id` which correctly matches collection `camera_device_id` field.

### Verification ✅ TESTED
- Recorded test video from edge camera
- Video correctly appeared in edge camera collection (edge-camera-rpi5-001)
- Collection attribution now working as expected

---

## Issue #3: Detection Pipeline Not Running ✅ RESOLVED

### Symptoms
- No instant detection triggered during recording
- No continuous detection pipeline running
- Video recorded but no demographic/tracking data generated

### Expected Behavior
- **Instant Detection**: Real-time alerts during recording
- **Continuous Pipeline**: Post-recording demographic analysis, tracking, MVR creation

### Root Cause ✅ IDENTIFIED
**Missing Face Detection Trigger in Camera Worker**:
- Camera worker (`camera_worker.py`) uploads segments directly to media service
- After upload, it assigns video to collection but does NOT trigger face detection
- The face detection trigger exists in `camera_detection.py`'s `_upload_recording_to_collection` method
- But worker bypasses that method and uploads directly
- Without face detection trigger, continuous pipeline (vision → vmeta → individuals → MVR) never starts

**Code Location**: `ppl-meta-cameras/src/services/camera_worker.py` line 1182 (upload method)

### Solution ✅ IMPLEMENTED
Added face detection trigger to camera worker's upload method:

1. **Added method** `_trigger_face_detection_sync()` to CameraWorker class:
   - Checks face_detection_on_save setting
   - Triggers Enhanced Logic V2 workflow via Vision Service API
   - Uses correct endpoint: `/process/media/enhanced`
   - Sends media processing request with optimal options
   - Enables continuous pipeline: faces → individuals → MVR

2. **Modified** `_upload_segment_to_media()` method:
   - After successful upload and collection assignment
   - Calls `self._trigger_face_detection_sync(media_uuid, headers)`
   - This ensures every uploaded segment triggers the continuous pipeline

**Bug Fix Applied** (Feb 8, 2026):
- Fixed incorrect Vision Service endpoint (was `/api/v1/face-detection/bulk`, now `/process/media/enhanced`)
- Error was: `HTTP 404 - {"detail":"Not Found"}`
- Now uses correct Enhanced Logic V2 endpoint

**Benefits**:
- Works for ALL camera types (USB, RTSP, Mobile, Edge)
- Unified behavior - all cameras trigger continuous pipeline
- No special case handling needed for edge cameras
- Automatic demographic analysis and tracking for all recordings

### Verification ✅ TESTED (Feb 8, 2026)

**Instant Detection**: ✅ WORKING
- Samples 3 frames every 5 seconds as configured
- Calls Vision Service for face detection
- Results: Vision Service returned 0 faces (no people in frame during test)
- Log evidence: `📤 Submitting 3 frames for instant detection: edge-camera-rpi5-001`

**Continuous Pipeline**: ⚠️ PARTIALLY WORKING
- Face detection trigger now executes after segment upload
- Vision Service endpoint corrected (404 error fixed)
- Note: No faces detected in test recording (camera pointed at empty area)
- Recommendation: Test with person in frame (0.5-1.5m from camera for optimal focus)

**What Works**:
- Edge camera WebSocket connection and streaming ✅
- Video recording and segment upload ✅  
- Collection assignment ✅
- Instant detection sampling and Vision Service calls ✅
- Face detection trigger after upload ✅

**What Needs Testing with Person in Frame**:
- Face detection success rate
- Demographics extraction (age/gender)
- Individual creation in vmeta
- MVR (Machine Vision Recognition) person tracking

---

## Deployment Status

### Working ✅
- Container running stable (14+ hours uptime)
- Health checks passing
- Camera capture at 1280x720@10fps
- Discovery service registration
- WebSocket connection to backend
- Streaming endpoint functional
- Some USB camera recordings playable (8.78s video working)

### Not Working ❌
1. Edge camera video encoding/playback
2. Collection attribution for recordings
3. Detection pipeline integration

---

## Environment Details

**Backend Server**: 192.168.1.75
- Gateway: :8080
- Node: :8001
- Cameras: :8005
- Media: :8000

**Edge Camera**: 192.168.1.77:9001
- Container: ppl-meta-edge-camera:latest (v5-deviceid)
- Camera: /dev/video0 (Waveshare USB, OV5640)
- Config: edge-camera-rpi5-001

**Frontend**: localhost:3000
- User: fresh.user@example.com
- Token valid, API calls working

---

## Next Steps

1. **Priority 1**: Fix video corruption (Issue #1)
   - Check edge camera recording/encoding implementation
   - Verify video codec and container format
   - Test direct file access vs streaming

2. **Priority 2**: Fix collection attribution (Issue #2)
   - Trace recording request camera_id flow
   - Verify camera registration and identification

3. **Priority 3**: Enable detection pipeline (Issue #3)
   - Verify vision service connectivity
   - Check detection configuration for edge cameras
   - Test manual detection trigger

---

## Logs to Check

1. Edge camera container: `ssh pi@192.168.1.77 "cd ~/ppl-meta-deploy && docker compose logs edge-camera | tail -100"`
2. Cameras service: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/logs/ppl-meta-cameras.log`
3. Media service: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/logs/ppl-meta-media.log`
4. Vision service: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/logs/ppl-meta-vision.log`
5. Vmeta service: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/logs/ppl-meta-vmeta.log`

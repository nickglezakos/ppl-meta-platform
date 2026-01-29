# Mobile Camera Worker Integration Fix - Phase 1

## Issue Analysis

### Root Cause
The mobile worker framework was implemented but **not being used** by recording and instant detection services:

1. **Recording** - Pulled frames directly from `MobileStreamingService.get_latest_mobile_frame_data()` (raw, unrotated frames)
2. **Instant Detection** - Never initialized for mobile cameras
3. **Streaming** - Correctly used mobile worker (✅ working)

### Test Results (Before Fix)
- ❌ Instant detection did not work
- ❌ Video recorded in landscape (should be portrait) 
- ❌ Continuous pipeline did not process video
- ✅ Video file created and playable
- ✅ MJPEG streaming working correctly

## Changes Implemented

### 1. Recording Service Integration
**File**: `ppl-meta-cameras/src/services/camera_detection.py`

#### Change A: Use Mobile Worker Frames
```python
# OLD: Direct frame access (unrotated)
frame_data = await mobile_streaming_service.get_latest_mobile_frame_data(device_id)
frame = frame_data.get('frame')

# NEW: Mobile worker frames (already rotated)
mobile_worker = mobile_streaming_service.get_mobile_worker(device_id)
if mobile_worker:
    frame = mobile_worker.get_latest_frame()  # Already rotated + resized
else:
    # Fallback to direct access
    frame_data = await mobile_streaming_service.get_latest_mobile_frame_data(device_id)
    frame = frame_data.get('frame')
```

**Impact**: Recording now uses rotated frames from worker's CameraWorker.frame_buffer

#### Change B: Auto-Start Mobile Worker on Recording
```python
# Start mobile worker when recording begins (if not already running)
if not mobile_streaming_service.has_mobile_worker(device_id):
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if camera:
        camera_info = {
            "instant_detection_enabled": camera.instant_detection_enabled,
            "instant_detection_interval_seconds": camera.instant_detection_interval_seconds or 5,
        }
        await mobile_streaming_service.start_mobile_worker(
            device_id=device_id,
            camera_info=camera_info,
            enable_instant_detection=camera.instant_detection_enabled
        )
```

**Impact**: Worker guaranteed to be running during recording

### 2. Instant Detection Integration
**File**: `ppl-meta-cameras/src/services/mobile_camera_worker.py`

```python
# Initialize instant detection if enabled
if enable_instant_detection:
    detection_config = camera_info.get("detection_config", {
        "interval_seconds": camera_info.get("instant_detection_interval_seconds", 5)
    })
    self.camera_worker.start_detection(detection_config)
    logger.info(f"✅ Instant detection enabled for mobile worker {device_id}")
```

**Impact**: CameraWorker's InstantDetectionSampler initialized when worker starts

### 3. Auto-Start Enhancement
**File**: `ppl-meta-cameras/src/services/mobile_streaming.py`

```python
# OLD: Auto-start without camera settings
await self.start_mobile_worker(
    device_id=device_id,
    enable_instant_detection=True  # Always true
)

# NEW: Auto-start with database settings
camera = db.query(CameraModel).filter(CameraModel.device_id == device_id).first()
if camera:
    camera_info = {
        "instant_detection_interval_seconds": camera.instant_detection_interval_seconds or 5
    }
    enable_detection = camera.instant_detection_enabled
    
await self.start_mobile_worker(
    device_id=device_id,
    camera_info=camera_info,
    enable_instant_detection=enable_detection
)
```

**Impact**: Respects per-camera instant detection settings from database

## Architecture Flow (After Fix)

```
Mobile App (Flutter)
    ↓ HTTP POST (JPEG frame + metadata)
MobileStreamingService.receive_mobile_frame()
    ↓ Auto-start worker if needed
MobileCameraWorker._process_frames()
    ↓ Rotation + Resize
CameraWorker.frame_buffer (thread-safe deque)
    ├─→ InstantDetectionSampler (if enabled)
    │       ↓ Every N seconds
    │   Face Detection API
    │       ↓
    │   Person Objects Created
    │
    ├─→ Recording Loop
    │       ↓ cv2.VideoWriter
    │   Video Segments (MP4)
    │       ↓ Upload on completion
    │   Media Service
    │       ↓ Trigger face detection
    │   Continuous Pipeline
    │       ↓
    │   MVR Cross-Video Tracking
    │
    └─→ MJPEG Streaming
            ↓ HTTP Response
        Frontend Player
```

## Testing Checklist

### Before Testing
1. ✅ Restart ppl-meta-cameras service
2. ✅ Mobile camera registered in database
3. ✅ `instant_detection_enabled = true` for mobile camera
4. ✅ Mobile app connected and streaming

### Test 1: Instant Detection
- [ ] Start streaming from mobile app
- [ ] Check logs for: `🚀 Mobile worker started for mobile_TKQ1.221114.001`
- [ ] Check logs for: `✅ Instant detection enabled for mobile worker`
- [ ] Wait 5+ seconds (interval period)
- [ ] Verify face detection attempts in logs
- [ ] Check if person objects created

### Test 2: Video Recording
- [ ] Start recording from mobile app (portrait mode)
- [ ] Record 20+ seconds with face in frame
- [ ] Stop recording
- [ ] Check video orientation: **Should be portrait**
- [ ] Play video via media service URL
- [ ] Verify faces are in correct orientation

### Test 3: Continuous Pipeline
- [ ] Complete recording from Test 2
- [ ] Check ppl-meta-vision logs for face detection
- [ ] Check ppl-meta-vmeta logs for MVR creation
- [ ] Verify person objects have MVR IDs
- [ ] Check MVR quality metrics

### Expected Log Messages

#### Mobile Worker Startup
```
🚀 Auto-starting mobile worker for mobile_TKQ1.221114.001
📸 Camera mobile_TKQ1.221114.001 instant detection: True, interval: 5s
✅ Started mobile worker for mobile_TKQ1.221114.001
✅ Instant detection enabled for mobile worker mobile_TKQ1.221114.001
📱 Frame processing loop started for mobile_TKQ1.221114.001
```

#### Recording with Worker
```
🚀 [RECORDING] Starting mobile worker for mobile_TKQ1.221114.001
✅ [RECORDING] Mobile worker started for mobile_TKQ1.221114.001
🎬 [SEGMENT] Starting mobile segment recording loop for mobile_TKQ1.221114.001
🎬 [SEGMENT] Mobile recording with 30s segments
🎬 [SEGMENT] Recorded 30 mobile frames for mobile_TKQ1.221114.001
```

#### Instant Detection
```
📸 [DETECTION] Processing frame for instant detection: mobile_TKQ1.221114.001
🎯 Face detection triggered for camera mobile_TKQ1.221114.001
✅ Detected N faces via instant detection
```

## Files Modified

1. `ppl-meta-cameras/src/services/camera_detection.py` (2 changes)
   - Lines 1273-1302: Auto-start worker on recording
   - Lines 2489-2520: Use worker frames instead of direct access

2. `ppl-meta-cameras/src/services/mobile_camera_worker.py` (1 change)
   - Lines 73-82: Initialize instant detection sampler

3. `ppl-meta-cameras/src/services/mobile_streaming.py` (1 change)
   - Lines 353-382: Enhanced auto-start with database settings

## Next Steps

1. **Test with real device** (this document serves as test plan)
2. **Monitor performance** - Check CPU/memory impact of worker
3. **Validate continuous pipeline** - Ensure MVRs created correctly
4. **Document any issues** - Create follow-up tasks if needed

## Success Criteria

- ✅ Mobile worker auto-starts when frames arrive
- ✅ Instant detection runs every N seconds
- ✅ Video recorded in correct orientation (portrait)
- ✅ Continuous pipeline processes recordings
- ✅ MVRs created with correct cross-video tracking
- ✅ No crashes or memory leaks during extended use

## Rollback Plan

If issues occur:
1. Revert changes to `camera_detection.py` recording loop
2. Keep streaming endpoint changes (already working)
3. Mobile cameras will record but without rotation (known issue)
4. Document specific failures for targeted fixes

# Mobile Camera Instant Detection & Continuous Pipeline Integration

**Version:** 2.23.15+  
**Date:** January 29, 2026  
**Status:** Planning Phase

## Problem Statement

Mobile cameras successfully stream video from front/rear cameras via WebSocket/HTTP POST, but:

1. **No Instant Detection**: The streaming frames are not being processed for instant detection events
2. **No Recording**: Videos are not being stored for continuous pipeline processing
3. **Architecture Gap**: Mobile cameras use WebSocket frame submission instead of RTSP/MJPEG streaming used by USB/RTSP cameras

## Current Architecture Analysis

### Mobile Camera Streaming Flow

```
Mobile App (Flutter)
    ↓ (HTTP POST with JPEG frames)
MobileStreamingService.store_frame()
    ↓
In-memory frame storage (Dict[device_id, frame_data])
    ↓
StreamingEndpoint.video_stream()
    ↓ (MJPEG stream)
Frontend Browser
```

### Traditional Camera Flow (USB/RTSP)

```
USB/RTSP Camera
    ↓ (cv2.VideoCapture)
CameraWorker (background thread)
    ↓
QueueService (frame queue)
    ↓
├─→ StreamingEndpoint (MJPEG to frontend)
├─→ InstantDetectionService (real-time analysis)
└─→ RecordingService (video storage)
```

### Key Differences

| Feature | Traditional Cameras | Mobile Cameras |
|---------|-------------------|----------------|
| Frame Source | cv2.VideoCapture | HTTP POST |
| Frame Storage | Queue + continuous capture | In-memory Dict |
| Background Worker | Yes (CameraWorker) | No |
| Recording | Automatic via RecordingService | Not implemented |
| Instant Detection | Integrated via queue | Not integrated |
| Continuous Pipeline | Yes | No |

## Root Causes

1. **No Background Worker**: Mobile cameras don't have a CameraWorker equivalent that continuously processes frames
2. **No Queue Integration**: Frames are stored in a separate dictionary, not in the frame queue used by other services
3. **No Recording Trigger**: RecordingService doesn't monitor mobile camera frames
4. **No Detection Hook**: InstantDetectionService doesn't receive mobile camera frames

## Proposed Solution Architecture

### Option A: Unified Queue Architecture (Recommended)

Bridge mobile cameras into the existing queue-based architecture:

```
Mobile App
    ↓ (HTTP POST)
MobileStreamingService.store_frame()
    ↓
[NEW] MobileCameraWorker (async background task)
    ↓
QueueService.add_frame(device_id, frame)
    ↓
├─→ StreamingEndpoint (MJPEG)
├─→ InstantDetectionService (real-time)
└─→ RecordingService (video storage)
```

**Pros:**
- Reuses existing services (instant detection, recording, pipeline)
- Minimal code duplication
- Consistent behavior across all camera types
- Easy to maintain

**Cons:**
- Requires adapting mobile frame format to queue format
- Need to handle WebSocket frame rate vs queue consumption rate

### Option B: Parallel Mobile Pipeline

Create dedicated mobile camera processing pipeline:

```
Mobile App
    ↓
MobileStreamingService
    ↓
├─→ MobileStreamingEndpoint (MJPEG)
├─→ MobileInstantDetectionService (real-time)
└─→ MobileRecordingService (video storage)
```

**Pros:**
- Independent of existing architecture
- Can optimize specifically for mobile patterns
- No risk of breaking existing cameras

**Cons:**
- Code duplication (detection, recording logic)
- Harder to maintain two pipelines
- Different behavior between camera types

### Option C: Hybrid Approach

Extend existing services with mobile camera awareness:

**Pros:**
- Balanced approach
- Selective reuse

**Cons:**
- More complex conditional logic in services
- Harder to reason about

## Recommended Approach: Option A (Unified Queue)

## Implementation Plan

### Phase 1: Mobile Camera Worker Integration

**Goal**: Create background worker to feed mobile frames into the queue system

#### 1.1 Create MobileCameraWorker Class

**File**: `ppl-meta-cameras/src/workers/mobile_camera_worker.py`

```python
class MobileCameraWorker:
    """Background worker for mobile camera frame processing."""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.is_active = False
        self.task = None
        
    async def start(self):
        """Start processing mobile camera frames."""
        self.is_active = True
        self.task = asyncio.create_task(self._process_frames())
        
    async def stop(self):
        """Stop processing frames."""
        self.is_active = False
        if self.task:
            self.task.cancel()
            
    async def _process_frames(self):
        """Continuously pull frames from mobile storage and push to queue."""
        while self.is_active:
            # Get latest frame from mobile storage
            frame_data = await mobile_streaming_service.get_latest_mobile_frame_data(self.device_id)
            
            if frame_data:
                frame = frame_data.get("frame")
                rotation_angle = frame_data.get("rotation_angle", 0)
                
                # Apply rotation
                if rotation_angle != 0:
                    frame = self._rotate_frame(frame, rotation_angle)
                
                # Push to queue
                await queue_service.add_frame(self.device_id, frame)
                
            # Frame rate control (30 fps)
            await asyncio.sleep(1/30)
```

**Dependencies:**
- `mobile_streaming_service` (existing)
- `queue_service` (existing)
- OpenCV for frame rotation

#### 1.2 Worker Lifecycle Management

**File**: `ppl-meta-cameras/src/services/mobile_streaming.py`

Add worker management to MobileStreamingService:

```python
class MobileStreamingService:
    def __init__(self):
        # ... existing code ...
        self.workers: Dict[str, MobileCameraWorker] = {}
    
    async def start_mobile_worker(self, device_id: str):
        """Start background worker for device."""
        if device_id not in self.workers:
            worker = MobileCameraWorker(device_id)
            await worker.start()
            self.workers[device_id] = worker
            logger.info(f"✅ Started mobile worker for {device_id}")
    
    async def stop_mobile_worker(self, device_id: str):
        """Stop background worker for device."""
        if device_id in self.workers:
            await self.workers[device_id].stop()
            del self.workers[device_id]
            logger.info(f"🛑 Stopped mobile worker for {device_id}")
```

#### 1.3 Integration Points

**Trigger Worker Start:**
- When mobile camera starts streaming (first frame received)
- In `store_frame()` method, check if worker exists, if not start it

**Trigger Worker Stop:**
- When streaming stops (timeout, manual stop)
- Camera disconnects

### Phase 2: Recording Integration

**Goal**: Enable automatic video recording for mobile cameras

#### 2.1 Extend RecordingService

**File**: `ppl-meta-cameras/src/services/recording_service.py`

Mobile cameras should be treated like USB/RTSP cameras once in the queue:

```python
async def start_recording(self, device_id: str, workflow_config: dict = None):
    """Start recording for any camera type (USB/RTSP/Mobile)."""
    
    # Check camera type
    is_mobile = device_id.startswith('mobile_')
    
    # Mobile cameras need worker to feed queue
    if is_mobile:
        await mobile_streaming_service.start_mobile_worker(device_id)
    
    # Start recording from queue (unified for all types)
    # ... existing recording logic ...
```

#### 2.2 Video File Metadata

Add mobile-specific metadata to recordings:

```python
metadata = {
    "device_id": device_id,
    "camera_type": "mobile" if is_mobile else "usb",
    "orientation": "portrait" if is_mobile else "landscape",
    "device_info": {
        "model": frame_data.get("device_model"),
        "os": "android"  # or detect from device_id
    }
}
```

### Phase 3: Instant Detection Integration

**Goal**: Enable real-time person detection for mobile cameras

#### 3.1 Queue-Based Detection

Since mobile frames will be in the queue, instant detection should work automatically.

**Verify in**: `ppl-meta-cameras/src/services/instant_detection_service.py`

```python
async def process_camera_stream(self, device_id: str):
    """Process frames from queue for instant detection."""
    
    # This should already work for mobile cameras once they're in the queue
    while self.is_active(device_id):
        frame = await queue_service.get_latest_frame(device_id)
        
        # Detect people
        detections = self._detect_people(frame)
        
        # Trigger events if threshold met
        if len(detections) >= threshold:
            await self._trigger_instant_detection_event(device_id, detections)
```

#### 3.2 Mobile-Specific Optimizations

Consider mobile-specific detection settings:

```python
# Mobile cameras often have different scene characteristics
mobile_detection_config = {
    "confidence_threshold": 0.6,  # Slightly lower for mobile quality
    "frame_skip": 2,  # Process every 2nd frame to save mobile CPU
    "detection_zones": "full_frame"  # Mobile cameras usually have good framing
}
```

### Phase 4: Continuous Pipeline Integration

**Goal**: Enable workflow processing for mobile camera recordings

#### 4.1 Recording Completion Hook

**File**: `ppl-meta-cameras/src/services/recording_service.py`

```python
async def _on_recording_complete(self, device_id: str, video_path: str, metadata: dict):
    """Triggered when recording finishes."""
    
    # Publish to message queue for pipeline processing
    await message_queue.publish(
        exchange="recordings",
        routing_key="recording.completed",
        message={
            "device_id": device_id,
            "video_path": video_path,
            "camera_type": "mobile" if device_id.startswith('mobile_') else "usb",
            "metadata": metadata
        }
    )
```

#### 4.2 Pipeline Service Integration

**File**: `ppl-meta-orchestrator` or relevant pipeline service

Ensure pipeline workers can process mobile camera videos:

```python
async def process_video(self, video_path: str, metadata: dict):
    """Process video through pipeline."""
    
    camera_type = metadata.get("camera_type", "usb")
    
    # Mobile videos may need different handling
    if camera_type == "mobile":
        # Check if video needs re-encoding
        if not self._is_compatible_format(video_path):
            video_path = await self._transcode_video(video_path)
    
    # Run standard pipeline
    await self._run_detection_pipeline(video_path, metadata)
```

### Phase 5: Frame Rate & Quality Management

**Goal**: Optimize mobile frame handling for performance

#### 5.1 Adaptive Frame Rate

```python
class MobileCameraWorker:
    async def _process_frames(self):
        # Detect frame arrival rate
        frame_rate = self._calculate_incoming_rate()
        
        # Adapt processing rate
        if frame_rate < 15:
            sleep_time = 1/15  # Process at 15fps
        elif frame_rate > 30:
            sleep_time = 1/30  # Cap at 30fps
        else:
            sleep_time = 1/frame_rate
```

#### 5.2 Buffer Management

Prevent memory overflow from high frame rates:

```python
# Limit mobile frame buffer size
MAX_MOBILE_FRAMES = 30  # 1 second at 30fps

async def store_frame(self, device_id: str, frame_data: dict):
    # ... existing storage ...
    
    # Limit buffer size
    if len(self.mobile_frames.get(device_id, [])) > MAX_MOBILE_FRAMES:
        self.mobile_frames[device_id].pop(0)  # Remove oldest
```

## Testing Strategy

### Test 1: Queue Integration
- Start mobile camera streaming
- Verify frames appear in queue service
- Check frame rate consistency

### Test 2: Recording
- Start mobile camera stream
- Trigger recording manually
- Verify video file created with correct format
- Check video playback quality

### Test 3: Instant Detection
- Start mobile camera stream
- Walk in front of camera
- Verify instant detection event fires
- Check detection accuracy

### Test 4: Pipeline Processing
- Record video from mobile camera
- Let recording complete
- Verify video enters continuous pipeline
- Check processing results (faces, demographics, etc.)

### Test 5: Resource Usage
- Monitor memory usage with mobile streaming
- Check CPU usage during detection
- Verify no memory leaks over extended sessions

## Configuration Updates

### Camera Registration

Update camera registration to support mobile cameras properly:

```json
{
  "device_id": "mobile_TKQ1.221114.001",
  "camera_type": "mobile",
  "supports_streaming": true,
  "supports_recording": true,
  "supports_instant_detection": true,
  "recording_config": {
    "format": "mp4",
    "codec": "h264",
    "fps": 30,
    "resolution": "480x720"
  }
}
```

### Workflow Configuration

Add mobile camera support flags:

```json
{
  "workflow_id": "mobile_monitoring",
  "enabled_for_mobile": true,
  "recording_settings": {
    "trigger_on_motion": true,
    "segment_duration": 300,
    "storage_path": "/recordings/mobile/"
  }
}
```

## Migration Plan

### Phase 1: Foundation (Week 1)
- [ ] Create MobileCameraWorker class
- [ ] Integrate worker lifecycle management
- [ ] Test frame flow to queue

### Phase 2: Recording (Week 1-2)
- [ ] Extend RecordingService for mobile cameras
- [ ] Test video recording from mobile
- [ ] Verify file format and playback

### Phase 3: Detection (Week 2)
- [ ] Verify instant detection works
- [ ] Tune detection parameters
- [ ] Test event triggering

### Phase 4: Pipeline (Week 2-3)
- [ ] Hook recordings to pipeline
- [ ] Test end-to-end workflow
- [ ] Verify results storage

### Phase 5: Optimization (Week 3)
- [ ] Performance tuning
- [ ] Resource optimization
- [ ] Load testing

## Risks & Mitigations

### Risk 1: Frame Rate Mismatch
**Risk**: Mobile app sends frames at variable rate, queue expects consistent rate  
**Mitigation**: Implement adaptive buffering and frame dropping logic

### Risk 2: Memory Pressure
**Risk**: Storing frames in multiple places (mobile storage + queue)  
**Mitigation**: Use shared memory or pointers, implement buffer limits

### Risk 3: Network Latency
**Risk**: Mobile cameras may have higher latency than local USB cameras  
**Mitigation**: Add latency monitoring, implement timeout handling

### Risk 4: Battery Impact
**Risk**: Continuous streaming drains mobile battery  
**Mitigation**: Add battery level monitoring, implement sleep modes

## Success Metrics

1. **Instant Detection**: Mobile cameras trigger detection events within 1 second of person appearing
2. **Recording Quality**: Videos recorded at 30fps with no dropped frames
3. **Pipeline Integration**: 100% of mobile recordings enter continuous pipeline
4. **Performance**: Mobile streaming uses <10% CPU on backend
5. **Reliability**: Mobile cameras maintain streaming for 8+ hours without issues

## Future Enhancements

1. **Edge Processing**: Run detection on mobile device before sending frames
2. **Adaptive Quality**: Automatically adjust resolution based on network
3. **Multi-Camera**: Support multiple mobile devices simultaneously
4. **Smart Upload**: Only upload frames with detected activity
5. **Offline Mode**: Buffer frames when network unavailable

## References

- Mobile Streaming Service: `ppl-meta-cameras/src/services/mobile_streaming.py`
- Queue Service: `ppl-meta-cameras/src/services/camera_queue.py`
- Recording Service: `ppl-meta-cameras/src/services/recording_service.py`
- Instant Detection: `ppl-meta-cameras/src/services/instant_detection_service.py`
- Camera Workers: `ppl-meta-cameras/src/workers/`

## Appendix A: Code Structure

```
ppl-meta-cameras/
├── src/
│   ├── workers/
│   │   ├── camera_worker.py          (existing - USB/RTSP)
│   │   └── mobile_camera_worker.py   (NEW)
│   ├── services/
│   │   ├── mobile_streaming.py       (existing - extend)
│   │   ├── recording_service.py      (existing - extend)
│   │   ├── instant_detection_service.py (existing - verify)
│   │   └── camera_queue.py           (existing - use)
│   └── api/v1/endpoints/
│       └── streaming.py               (existing - minor updates)
```

## Appendix B: API Endpoints

### Start Mobile Recording
```
POST /api/v1/cameras/mobile/{device_id}/recording/start
```

### Get Instant Detection Status
```
GET /api/v1/cameras/mobile/{device_id}/instant-detection/status
```

### Query Mobile Recordings
```
GET /api/v1/cameras/mobile/{device_id}/recordings?start_date=X&end_date=Y
```

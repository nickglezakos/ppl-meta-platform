# Camera Queue Architecture - Design Document

## Overview

**Problem**: Camera operations (connect, disconnect, frame reading, streaming) are blocking the async event loop despite wrapping in executors. Multiple cameras interfere with each other.

**Solution**: Give each camera instance its own dedicated queue and worker thread. This completely decouples camera operations from the FastAPI async event loop.

## Architecture Design

### Core Concept

```
FastAPI Async Event Loop
    ↓ (non-blocking send to queue)
Camera Queue (per camera instance)
    ↓ (processed by dedicated thread)
Camera Worker Thread (per camera)
    ↓ (blocking OpenCV operations safe here)
Frame Buffer + Status Updates
    ↑ (read by event loop for streaming/instant detection)
```

### Key Components

#### 1. CameraWorker Class (New)
```python
class CameraWorker:
    """Dedicated worker thread with command queue for a single camera."""
    
    def __init__(self, device_id: str, camera_type: CameraType):
        self.device_id = device_id
        self.camera_type = camera_type
        
        # Command queue - async event loop sends commands here
        self.command_queue = queue.Queue()
        
        # Frame buffer - shared with main thread (thread-safe)
        self.frame_buffer = collections.deque(maxlen=1)
        
        # Status - shared atomic state
        self.status = "disconnected"  # disconnected, connecting, connected, error
        self.status_lock = threading.Lock()
        
        # OpenCV capture - ONLY accessed by worker thread
        self.cap = None
        
        # Thread control
        self.stop_event = threading.Event()
        self.worker_thread = None
```

#### 2. Command Types
```python
class CameraCommand:
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    GET_FRAME = "get_frame"  # For instant detection sampling
    UPDATE_SETTINGS = "update_settings"  # FPS, resolution, etc.
```

#### 3. Worker Thread Loop
```python
def _worker_loop(self):
    """Main worker loop - processes commands from queue.
    
    Runs in dedicated thread, so ALL blocking operations are safe.
    """
    while not self.stop_event.is_set():
        try:
            # Get command with timeout (non-blocking wait)
            cmd = self.command_queue.get(timeout=0.1)
            
            if cmd['action'] == CameraCommand.CONNECT:
                self._handle_connect(cmd)
            elif cmd['action'] == CameraCommand.DISCONNECT:
                self._handle_disconnect(cmd)
            elif cmd['action'] == CameraCommand.GET_FRAME:
                self._handle_get_frame(cmd)
                
        except queue.Empty:
            # No commands, continue reading frames if connected
            if self.status == "connected" and self.cap:
                self._read_and_buffer_frame()
        except Exception as e:
            logger.error(f"Worker error for {self.device_id}: {e}")
```

## Integration with Existing Systems

### 1. Instant Detection Integration

**Current Flow**:
```
Timer triggers → sample_detection_from_camera() → 
    camera_service.get_camera_stream() → cap.read() [BLOCKS!] →
    face detection → store results
```

**New Flow**:
```
Timer triggers → sample_detection_from_camera() →
    camera_worker.get_latest_frame() [instant, non-blocking] →
    face detection → store results
```

**Implementation**:
```python
class CameraWorker:
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest frame from buffer - INSTANT, non-blocking.
        
        Used by instant detection sampler.
        Returns None if no frame available.
        """
        if self.frame_buffer:
            return self.frame_buffer[-1]
        return None
    
    def request_fresh_frame(self) -> str:
        """Request a fresh frame capture - async command.
        
        Returns command_id for tracking.
        Instant detection can wait for this if buffer is stale.
        """
        cmd_id = str(uuid.uuid4())
        self.command_queue.put({
            'action': CameraCommand.GET_FRAME,
            'cmd_id': cmd_id,
            'timestamp': time.time()
        })
        return cmd_id
```

**Instant Detection Changes** (minimal):
```python
# In instant_detection.py
async def sample_detection_from_camera(device_id: str):
    worker = camera_service.get_worker(device_id)
    if not worker:
        return None
    
    # Get latest buffered frame (instant)
    frame = worker.get_latest_frame()
    if frame is None:
        logger.warning(f"No frame available for {device_id}")
        return None
    
    # Rest of detection logic unchanged
    detections = await detect_faces_async(frame)
    # ... store results, trigger webhooks, etc.
```

### 2. MVR Continuous Pipeline Integration

**Current Flow**:
```
Recording saves video → 
    Face detection on save → 
    Store individuals/embeddings → 
    Batch processing triggers → 
    Cross-video tracking → 
    MVR people created
```

**Impact**: NONE - Pipeline runs on saved videos, not live streams

**Why No Changes Needed**:
- Pipeline processes **completed video files**, not live camera feeds
- Face detection happens via Vision service API calls (not camera service)
- Camera service only provides: recording capability + instant detection
- Queue architecture doesn't affect saved video processing

**Validation**:
```python
# Recording flow stays the same:
# 1. Camera worker buffers frames
# 2. Recording service reads from buffer (via camera_service.get_camera_stream())
# 3. Frames saved to video file
# 4. Vision service detects faces when file is complete
# 5. Pipeline processes video file
# 6. No direct camera access needed
```

### 3. Counter/People Tracking Integration

**Current**: Counter uses instant detection results (already covered above)

**New**: Same - counter polls instant detection results
```python
# No changes needed in counter logic
# Counter already reads from instant detection results storage
# Camera queue architecture only affects HOW frames are captured
```

## Implementation Plan

### Phase 1: Core Queue Infrastructure (Day 1)

**Files to Create**:
- `ppl-meta-cameras/src/services/camera_worker.py` - CameraWorker class
- `ppl-meta-cameras/src/services/worker_manager.py` - Manages all camera workers

**Changes**:
- `camera_detection.py`: Replace direct cap usage with worker.send_command()
- Add worker lifecycle management (create, start, stop, cleanup)

### Phase 2: Connection Flow (Day 1)

**Connect Camera Flow**:
```python
async def connect_camera(device_id: str):
    # 1. Create or get existing worker
    worker = self._get_or_create_worker(device_id)
    
    # 2. Send connect command (non-blocking)
    cmd_id = worker.send_command({
        'action': CameraCommand.CONNECT,
        'connection_string': camera_info['connection_string'],
        'settings': {...}
    })
    
    # 3. Wait for connection result (with timeout)
    result = await worker.wait_for_result(cmd_id, timeout=15.0)
    
    # 4. Return connection status
    return result['success']
```

### Phase 3: Streaming Integration (Day 2)

**Streaming Endpoint**:
```python
@router.get("/{device_id}/video")
async def video_stream(device_id: str):
    worker = camera_service.get_worker(device_id)
    
    async def generate_frames():
        while True:
            # Non-blocking frame read from buffer
            frame = worker.get_latest_frame()
            if frame is not None:
                # Encode to JPEG (can do in executor if needed)
                jpg = cv2.imencode('.jpg', frame)[1].tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
            await asyncio.sleep(0.03)  # ~30 FPS
    
    return StreamingResponse(generate_frames(), 
                            media_type="multipart/x-mixed-replace; boundary=frame")
```

### Phase 4: Testing & Validation (Day 2-3)

**Test Scenarios**:
1. ✅ Single USB camera connect/stream/disconnect
2. ✅ Single RTSP camera connect/stream/disconnect
3. ✅ Multiple cameras simultaneously (USB + RTSP)
4. ✅ Camera switching (disconnect one, connect another)
5. ✅ Instant detection sampling works during streaming
6. ✅ Recording works (frames saved to file)
7. ✅ MVR pipeline processes recorded videos
8. ✅ Counter updates from instant detection
9. ✅ Service restart with active cameras
10. ✅ Network interruption (RTSP reconnect)

## Benefits of Queue Architecture

### 1. Complete Event Loop Isolation
- **Before**: Blocking OpenCV calls freeze entire async event loop
- **After**: Blocking calls happen in dedicated threads, event loop stays responsive

### 2. True Camera Independence
- **Before**: USB camera operations can affect RTSP camera performance
- **After**: Each camera has own thread, completely isolated

### 3. Simplified Error Handling
- **Before**: Exception in one camera affects others
- **After**: Worker crashes are isolated, can restart individual cameras

### 4. Better Resource Management
- **Before**: Hard to control frame reading rate, buffer sizes
- **After**: Each worker manages its own buffer, frame rate, reconnection logic

### 5. Easier Testing
- **Before**: Hard to test concurrent camera operations
- **After**: Each worker is independent, can test in isolation

## Migration Strategy

### Backwards Compatibility

Keep existing API signatures:
```python
# External API stays the same
async def connect_camera(device_id: str) -> bool
async def disconnect_camera(device_id: str) -> bool
async def get_camera_stream(device_id: str) -> VideoCapture

# Internal implementation changes to use workers
```

### Gradual Rollout

1. **Week 1**: Implement worker infrastructure, test with USB cameras only
2. **Week 2**: Add RTSP support, test with both types
3. **Week 3**: Production testing, monitor instant detection + MVR pipeline
4. **Week 4**: Remove old direct OpenCV code once stable

## Flutter Frontend - Active File Inventoryyes plea

**IMPORTANT**: Before implementing queue architecture, understand which Flutter files are currently in use vs experimental/deprecated versions.

### ✅ PRIMARY FILES (Active - These Will Need Updates)

#### Core Service Layer
1. **`lib/core/services/camera_service.dart`** ⭐ **MAIN SERVICE**
   - Lines: 939 total
   - Purpose: Primary camera API client
   - Methods: `startRecording()`, `stopRecording()`, `connectCamera()`, `disconnectCamera()`, `startStreaming()`, `stopStreaming()`
   - **Status**: ACTIVE - This is what widgets use
   - **Queue Impact**: Will need to work with new backend queue endpoints

#### State Management Layer
2. **`lib/core/providers/camera_providers.dart`** ⭐ **MAIN PROVIDER**
   - Lines: 820 total
   - Purpose: Riverpod state notifiers
   - Key Providers:
     - `cameraRecordingProvider` - Recording state
     - `recordingStateProvider` - Alias for backward compatibility
     - `cameraStreamProvider` - Streaming state
   - Notifiers: `CameraRecordingNotifier` with `startRecording()`, `stopRecording()`
   - **Status**: ACTIVE - Manages UI state
   - **Queue Impact**: State transitions should remain unchanged

#### Widget Layer - Stream Player
3. **`lib/presentation/widgets/camera/camera_stream_player.dart`** ⭐ **PRIMARY PLAYER**
   - Purpose: Main video stream display widget
   - **Status**: ACTIVE
   - **Queue Impact**: None - reads from same stream endpoint

4. **`lib/presentation/widgets/camera/camera_card.dart`** ⭐ **MAIN CARD WIDGET**
   - Purpose: Camera card UI with recording controls
   - **Status**: ACTIVE
   - Displays: Connection status, recording button, stream preview
   - **Queue Impact**: None - UI only

#### Widget Layer - Recording Controls
5. **`lib/widgets/camera/recording_controls.dart`** ⭐ **RECORDING BUTTON**
   - Purpose: Start/Stop recording button widget
   - Uses: `cameraRecordingProvider`
   - **Status**: ACTIVE
   - **Queue Impact**: None - interacts via provider

#### Page Layer
6. **`lib/features/cameras/pages/camera_streaming_page.dart`** ⭐ **CAMERA PAGE**
   - Purpose: Full camera streaming page
   - **Status**: ACTIVE
   - **Queue Impact**: None - orchestrates existing components

### ⚠️ DUPLICATE/ALTERNATIVE FILES (Not Primary - IGNORE These)

#### Service Layer Duplicates
- `lib/services/camera_service.dart` - ⚠️ OLD VERSION, use core/services version
- `lib/services/enhanced_camera_service.dart` - ⚠️ Experimental, not used
- `lib/core/services/multi_camera_service.dart` - ⚠️ For multi-camera view only

#### Widget Duplicates (OLD/EXPERIMENTAL)
- `lib/presentation/widgets/camera/camera_stream_player_debug.dart` - 🧪 DEBUG VERSION
- `lib/presentation/widgets/camera/camera_stream_player_fixed.dart` - 🧪 EXPERIMENTAL
- `lib/presentation/widgets/camera/camera_stream_player_simple.dart` - 🧪 SIMPLIFIED
- `lib/features/cameras/widgets/camera_card.dart` - ⚠️ Alternative version (use presentation/widgets version)
- `lib/widgets/enhanced_camera_card.dart` - ⚠️ Uses old service directly

### 🎯 Queue Architecture Impact on Flutter

**Files That Need Updates**:
```
✅ lib/core/services/camera_service.dart
   - API calls remain same (backend queue is transparent)
   - May need timeout adjustments if queue adds latency
   - No structural changes needed
```

**Files That Need NO Changes**:
```
✅ lib/core/providers/camera_providers.dart (state management unchanged)
✅ lib/presentation/widgets/camera/camera_stream_player.dart (reads same stream)
✅ lib/presentation/widgets/camera/camera_card.dart (UI only)
✅ lib/widgets/camera/recording_controls.dart (interacts via provider)
✅ lib/features/cameras/pages/camera_streaming_page.dart (orchestration unchanged)
```

### 📌 Import Statements to Use

```dart
// ✅ CORRECT - Use these imports
import 'package:ppl_meta_platform/core/services/camera_service.dart';
import 'package:ppl_meta_platform/core/providers/camera_providers.dart';
import 'package:ppl_meta_platform/presentation/widgets/camera/camera_stream_player.dart';
import 'package:ppl_meta_platform/presentation/widgets/camera/camera_card.dart';

// ❌ WRONG - Don't use these
import 'package:ppl_meta_platform/services/camera_service.dart'; // OLD
import 'package:ppl_meta_platform/services/enhanced_camera_service.dart'; // EXPERIMENTAL
```

### ⚡ Service Provider Chain (Unchanged by Queue Architecture)

```
Widget/Page
  ↓ watches
Provider (camera_providers.dart)
  ↓ uses
Service (camera_service.dart)
  ↓ calls
Backend API (/api/v1/cameras, /api/v1/streaming)
  ↓ NEW: Queue-based backend
Camera Queue (per camera instance)
  ↓ processed by
Camera Worker Thread
```

**Key Insight**: Queue architecture is **backend-only**. Frontend continues to use same API endpoints and patterns. The queue makes backend non-blocking, which actually improves frontend reliability (no more timeout errors).

---

## Risk Mitigation

### Risk 1: Frame Latency
**Concern**: Queue adds latency between frame capture and instant detection

**Mitigation**:
- Buffer size = 1 (always latest frame)
- Worker reads frames continuously (no queue delays for frame reading)
- Commands use queue, but frame buffer is direct access

### Risk 2: Memory Usage
**Concern**: Each camera = new thread = memory overhead

**Solution**:
- Thread stack size optimization
- Monitor memory usage
- Limit max concurrent cameras (configurable)

### Risk 3: Thread Safety
**Concern**: Shared state between worker and main thread

**Solution**:
- Frame buffer: thread-safe deque
- Status: protected by lock
- VideoCapture: NEVER accessed from main thread
- Use atomic operations where possible

## Code Structure

```
ppl-meta-cameras/
├── src/
│   ├── services/
│   │   ├── camera_worker.py          # NEW: CameraWorker class
│   │   ├── worker_manager.py         # NEW: Manages all workers
│   │   ├── camera_detection.py       # MODIFIED: Uses workers
│   │   └── instant_detection.py      # MODIFIED: Read from worker buffers
│   └── api/
│       └── v1/
│           └── endpoints/
│               ├── cameras.py         # MODIFIED: Worker lifecycle
│               └── streaming.py       # MODIFIED: Read from worker buffers
```

## Configuration

```python
# config.py
class CameraWorkerConfig:
    # Buffer settings
    FRAME_BUFFER_SIZE = 1  # Keep only latest frame
    
    # Thread settings  
    MAX_WORKER_THREADS = 10  # Max concurrent cameras
    WORKER_THREAD_STACK_SIZE = 1024 * 1024  # 1MB per thread
    
    # Reconnection settings
    RTSP_RECONNECT_ATTEMPTS = 3
    RTSP_RECONNECT_DELAY = 5  # seconds
    USB_RECONNECT_ATTEMPTS = 2
    USB_RECONNECT_DELAY = 2
    
    # Performance
    FRAME_READ_TIMEOUT = 1.0  # seconds
    COMMAND_QUEUE_MAX_SIZE = 100
```

## Success Criteria

✅ All cameras connect without hanging
✅ Multiple cameras stream simultaneously
✅ Instant detection samples frames successfully
✅ MVR pipeline processes recordings
✅ No blocking operations in async event loop
✅ Camera switching is fast (<2 seconds)
✅ Service remains responsive under load
✅ Error in one camera doesn't affect others

## Timeline

- **Day 1 Morning**: Implement CameraWorker class + basic queue infrastructure
- **Day 1 Afternoon**: Migrate connect/disconnect to use workers
- **Day 2 Morning**: Implement streaming via worker buffers
- **Day 2 Afternoon**: Test instant detection integration
- **Day 3**: Full testing (all scenarios), validate MVR pipeline
- **Day 4**: Production deployment, monitoring

## Conclusion

Queue-based architecture completely decouples camera operations from async event loop, solving the root cause of blocking issues. The design preserves all existing functionality (instant detection, MVR pipeline, counter) while providing true camera independence and better error isolation.

**Key Insight**: We're not changing WHAT the system does, just HOW it captures frames. The queue makes frame capture async-safe, while instant detection and MVR pipeline continue to work exactly as before.

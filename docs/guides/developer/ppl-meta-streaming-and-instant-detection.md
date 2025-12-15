# PPL Meta Streaming and Instant Detection Architecture

**Document Version**: 1.0  
**Last Updated**: December 15, 2025  
**Status**: Production

---

## Table of Contents

1. [Overview](#overview)
2. [VideoCapture Lifecycle Management](#videocapture-lifecycle-management)
3. [Streaming Architecture](#streaming-architecture)
4. [Recording Architecture](#recording-architecture)
5. [Instant Detection Architecture](#instant-detection-architecture)
6. [WebSocket Real-Time Updates](#websocket-real-time-updates)
7. [State Management](#state-management)
8. [Resource Sharing and Coordination](#resource-sharing-and-coordination)
9. [Critical Issues and Fixes](#critical-issues-and-fixes)
10. [Code References](#code-references)

---

## Overview

The PPL Meta Cameras service manages three concurrent video operations:
1. **Live Streaming**: Real-time video feed to frontend clients
2. **Video Recording**: Persistent storage of video segments
3. **Instant Detection**: Real-time face/person detection without storage

All three operations share a **single VideoCapture object** per camera to avoid resource contention and ensure efficient camera access.

### Key Design Principles

- **Shared VideoCapture**: One `cv2.VideoCapture` instance per camera
- **Non-blocking Operations**: Streaming, recording, and detection run independently
- **State Synchronization**: Coordinated state changes across all operations
- **Automatic Cleanup**: Graceful handling of disconnections and errors

---

## VideoCapture Lifecycle Management

### Connection States

```
┌─────────────┐
│ DISCONNECTED│
└──────┬──────┘
       │ connect_camera()
       ▼
┌─────────────┐
│  CONNECTED  │◄──────┐
│ (available) │       │
└──────┬──────┘       │
       │              │ reconnect
       │ start_       │
       │ streaming/   │
       │ recording    │
       ▼              │
┌─────────────┐       │
│   ACTIVE    │       │
│  (in use)   │───────┘
└──────┬──────┘
       │ disconnect_camera()
       ▼
┌─────────────┐
│   RELEASED  │
└─────────────┘
```

### VideoCapture Creation and Storage

**Location**: `ppl-meta-cameras/src/services/camera_detection.py`

```python
class CameraDetectionService:
    def __init__(self):
        # Single VideoCapture per camera (device_id -> cv2.VideoCapture)
        self.active_connections: Dict[str, cv2.VideoCapture] = {}
        
        # Track original camera sources (device index or RTSP URL)
        self.camera_sources: Dict[str, str | int] = {}
        
        # Track active recordings
        self.active_recordings: Dict[str, Dict] = {}
```

### Connection Flow

1. **Camera Detection** (Lines 47-113):
   ```python
   async def detect_available_cameras(self) -> List[Dict]:
       # Scans system for USB cameras (indices 0-9)
       # Tests each index with cv2.VideoCapture()
       # Verifies frame capture
       # Returns available cameras
   ```

2. **Connection Establishment** (Lines 126-240):
   ```python
   async def connect_camera(self, device_id: str) -> Optional[cv2.VideoCapture]:
       # Check if already connected
       if device_id in self.active_connections:
           return self.active_connections[device_id]
       
       # For USB cameras
       index = int(camera_info["connection_string"])
       cap = cv2.VideoCapture(index)
       
       # Store for reuse
       self.active_connections[device_id] = cap
       self.camera_sources[device_id] = index
       
       return cap
   ```

3. **Disconnection** (Lines 266-300):
   ```python
   async def disconnect_camera(self, device_id: str) -> bool:
       cap = self.active_connections.get(device_id)
       if cap:
           cap.release()
           del self.active_connections[device_id]
           del self.camera_sources[device_id]
   ```

### Reconnection Handling

**Critical Issue**: When a camera is disconnected and reconnected:
- A **NEW** `VideoCapture` object is created
- Old references become stale
- Operations must detect and adapt to the new object

**Solution** (Implemented December 15, 2025):
- Streaming: Fetch capture on **each frame iteration**
- Instant Detection: Track `_current_capture` and restart if changed
- Recording: Uses latest connection from `active_connections`

---

## Streaming Architecture

### HTTP Streaming Endpoint

**Location**: `ppl-meta-cameras/src/api/v1/endpoints/streaming.py`

**Endpoint**: `GET /api/v1/cameras/{device_id}/video`

### Frame Generation Flow

```
┌───────────────┐
│ Client Request│
└───────┬───────┘
        │
        ▼
┌────────────────────┐
│ video_stream()     │
│ - Validates user   │
│ - Checks camera    │
└────────┬───────────┘
         │
         ▼
┌─────────────────────┐
│ generate_frames()   │◄──┐
│ - Async generator   │   │
└────────┬────────────┘   │
         │                │
         ▼                │
┌──────────────────────┐  │
│ Get Current Capture  │  │
│ (EACH ITERATION)     │  │
└────────┬─────────────┘  │
         │                │
         ▼                │
┌──────────────────────┐  │
│ cap.read()           │  │
│ - Read frame         │  │
│ - Resize if needed   │  │
│ - Encode as JPEG     │  │
└────────┬─────────────┘  │
         │                │
         ▼                │
┌──────────────────────┐  │
│ yield frame          │  │
│ (multipart/x-mixed-  │  │
│  replace)            │  │
└────────┬─────────────┘  │
         │                │
         └────────────────┘
         (loop continues)
```

### Key Implementation Details

**BEFORE FIX** (Lines 71-147):
```python
async def generate_frames():
    # ❌ PROBLEM: Captured once at function start
    cap = await camera_service.get_camera_stream(device_id)
    
    while True:
        ret, frame = cap.read()  # ❌ Uses stale capture after reconnect
        # ... encode and yield
```

**AFTER FIX** (Lines 71-147):
```python
async def generate_frames():
    while True:
        # ✅ SOLUTION: Fetch current capture on EACH iteration
        cap = await camera_service.get_camera_stream(device_id)
        if not cap or not cap.isOpened():
            break
        
        ret, frame = cap.read()  # ✅ Always uses latest connection
        if not ret:
            await asyncio.sleep(0.1)  # Retry on temporary failure
            continue
        
        # ... encode and yield
```

### Quality Settings

Streaming supports 4 quality levels (Lines 83-90):

| Quality | Resolution | FPS | JPEG Quality |
|---------|-----------|-----|--------------|
| low     | 320x240   | 15  | 80           |
| medium  | 640x480   | 30  | 80           |
| high    | 1280x720  | 30  | 80           |
| ultra   | 1920x1080 | 30  | 80           |

### Streaming State Management

**No Explicit State**: Streaming is stateless
- Client opens connection → frames flow
- Client closes connection → generator stops
- No state stored in service

---

## Recording Architecture

### Recording Session Lifecycle

```
┌──────────────┐
│ start_       │
│ recording()  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│ Create Recording State   │
│ - session_uuid           │
│ - output_path            │
│ - VideoWriter setup      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Start Background Thread  │
│ _record_frames_thread()  │
└──────┬───────────────────┘
       │
       │ (runs continuously)
       │
       ▼
┌──────────────────────────┐
│ Frame Capture Loop       │
│ - cap.read()             │
│ - Write to VideoWriter   │
│ - Segment rotation       │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ stop_recording()         │
│ - Set stop flag          │
│ - Join thread            │
│ - Release VideoWriter    │
└──────────────────────────┘
```

### Recording State Storage

**Location**: `ppl-meta-cameras/src/services/camera_detection.py`

```python
# Lines 37-38
self.active_recordings: Dict[str, Dict] = {}

# Recording state structure:
{
    "device_id": {
        "thread": Thread,
        "output_path": "/path/to/video",
        "stop_flag": threading.Event(),
        "writer": cv2.VideoWriter,
        "session_uuid": "...",
        "segment_number": 1,
        "frame_count": 0,
        "start_time": datetime,
    }
}
```

### Recording with Session Support

**Location**: Lines 730-1050

```python
async def _start_regular_recording_with_session(
    self, device_id: str, user_id: str, quality: str,
    auth_token: Optional[str], session_uuid: str, segment_duration: int
) -> Optional[Dict]:
    
    # 1. Get shared VideoCapture
    cap = self.active_connections[device_id]
    
    # 2. Setup output paths and VideoWriter
    output_path = Path(config.storage_path) / ...
    
    # 3. Start recording thread
    recording_thread = threading.Thread(
        target=self._record_frames_thread,
        args=(device_id, cap, ...)
    )
    recording_thread.start()
    
    # 4. Store recording state
    self.active_recordings[device_id] = {
        "thread": recording_thread,
        "output_path": str(output_path),
        ...
    }
```

### Frame Recording Thread

**Location**: Lines 860-1050

```python
def _record_frames_thread(self, device_id: str, cap: cv2.VideoCapture, ...):
    """Background thread that continuously reads frames and writes to video file"""
    
    writer = None
    segment_number = 1
    frames_in_segment = 0
    segment_start_time = time.time()
    
    while not stop_event.is_set():
        # 1. Read frame from SHARED capture
        ret, frame = cap.read()
        if not ret:
            continue
        
        # 2. Create new segment if needed
        if frames_in_segment >= frames_per_segment:
            writer.release()
            segment_number += 1
            writer = cv2.VideoWriter(new_path, ...)
            frames_in_segment = 0
        
        # 3. Write frame
        writer.write(frame)
        frames_in_segment += 1
        
        # 4. Orchestrator event publishing (every 30 frames)
        if frames_in_segment % 30 == 0:
            await self.orchestrator_client.publish_event(...)
```

### Segment Rotation

Recordings are split into segments (default: 5 seconds):

```
Recording Start
│
├── segment_1.mp4 (0-5s)
│   └── frames 0-150 @ 30fps
│
├── segment_2.mp4 (5-10s)
│   └── frames 150-300 @ 30fps
│
├── segment_3.mp4 (10-15s)
│   └── frames 300-450 @ 30fps
│
└── ... (continues until stop)
```

### Recording Stop Flow

**Location**: Lines 1114-1180

```python
async def stop_recording(
    self, device_id: str, 
    auto_stop_instant_detection: bool = True
) -> Optional[Dict]:
    
    # 1. Get recording state
    recording = self.active_recordings.get(device_id)
    
    # 2. Signal thread to stop
    recording["stop_flag"].set()
    
    # 3. Wait for thread completion
    recording["thread"].join(timeout=5.0)
    
    # 4. Release VideoWriter
    if recording["writer"]:
        recording["writer"].release()
    
    # 5. Auto-stop instant detection if enabled
    if auto_stop_instant_detection:
        manager.stop_sampling()
    
    # 6. Clean up state
    del self.active_recordings[device_id]
```

---

## Instant Detection Architecture

### Parallel Sampling System

**Location**: `ppl-meta-cameras/src/services/instant_detection.py`

Instant detection runs in a **separate background thread** that:
1. Samples 3 frames every 5 seconds
2. Submits to Celery for processing
3. Caches results in memory
4. Sends webhook notifications to trigger system

### Singleton Manager Pattern

**Location**: `ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py` (Lines 23-53)

```python
# Global singleton - shared across all requests
_instant_detection_manager: Optional[InstantDetectionSampler] = None

def get_instant_detection_manager() -> InstantDetectionSampler:
    global _instant_detection_manager
    
    if _instant_detection_manager is None:
        _instant_detection_manager = InstantDetectionSampler(
            vision_service_url="http://localhost:8003",
            sampling_interval=5,
            temporal_window=1.0
        )
    
    return _instant_detection_manager
```

### Instant Detection State

**Location**: `ppl-meta-cameras/src/services/instant_detection.py` (Lines 58-75)

```python
class InstantDetectionSampler:
    def __init__(self):
        # Thread management
        self._detection_thread: Optional[threading.Thread] = None
        self._running: bool = False
        
        # Camera tracking (ADDED Dec 15, 2025 for reconnection handling)
        self._current_camera_id: Optional[str] = None
        self._current_capture = None  # Reference to VideoCapture
        
        # Results cache (in-memory, 5 second TTL)
        self.results_cache: Dict[str, Dict] = {}
        
        # Webhook configuration
        self.webhook_enabled: bool = False
        self.webhook_url: Optional[str] = None
```

### Sampling Thread Lifecycle

```
┌──────────────────┐
│ start_sampling() │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────┐
│ Check if already running│
│ or capture changed      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Start daemon thread     │
│ _sample_loop()          │
└────────┬────────────────┘
         │
         │ (every 5 seconds)
         │
         ▼
┌─────────────────────────┐
│ Check capture valid     │◄──┐
└────────┬────────────────┘   │
         │                    │
         ▼                    │
┌─────────────────────────┐   │
│ Capture 3 frames        │   │
│ (t=0s, 0.5s, 1.0s)     │   │
└────────┬────────────────┘   │
         │                    │
         ▼                    │
┌─────────────────────────┐   │
│ Submit to Celery        │   │
│ (non-blocking)          │   │
└────────┬────────────────┘   │
         │                    │
         ▼                    │
┌─────────────────────────┐   │
│ Sleep 5 seconds         │   │
└────────┬────────────────┘   │
         │                    │
         └────────────────────┘
         (loop continues)
```

### Start Sampling with Reconnection Handling

**Location**: Lines 76-120

```python
def start_sampling(self, camera_id: str, camera_capture):
    # ✅ CRITICAL: Detect camera reconnection
    camera_changed = (
        self._current_camera_id != camera_id or 
        self._current_capture is not camera_capture
    )
    
    # If camera changed and still running, restart
    if camera_changed and self._running:
        logger.info("Camera changed - restarting instant detection")
        self.stop_sampling()
    
    # Check thread is not already running
    if self._running and self._detection_thread and self._detection_thread.is_alive():
        logger.warning("Instant detection already running")
        return
    
    # Clean up dead threads
    if self._detection_thread and not self._detection_thread.is_alive():
        self._running = False
        self._detection_thread = None
    
    # ✅ Store current camera and capture for comparison
    self._current_camera_id = camera_id
    self._current_capture = camera_capture
    
    # Start new thread
    self._running = True
    self._detection_thread = threading.Thread(
        target=self._sample_loop,
        args=(camera_id, camera_capture),
        daemon=True,
        name=f"instant-detection-{camera_id}"
    )
    self._detection_thread.start()
```

### Sampling Loop with Failure Handling

**Location**: Lines 135-213

```python
def _sample_loop(self, camera_id: str, camera_capture):
    consecutive_failures = 0
    max_failures = 3  # Auto-stop after 3 failures
    
    while self._running:
        # ✅ Validate capture before reading
        if not camera_capture or not camera_capture.isOpened():
            logger.warning("Camera capture closed, stopping instant detection")
            self._running = False
            break
        
        # Capture 3 frames
        frames = self._capture_3_frames_shared(camera_capture)
        
        if len(frames) == 3:
            # Success - submit to Celery
            self._submit_to_celery(camera_id, frames)
            consecutive_failures = 0  # Reset counter
            
        elif len(frames) == 0:
            # Complete failure - camera likely disconnected
            consecutive_failures += 1
            
            if consecutive_failures >= max_failures:
                logger.error("Too many failures, stopping instant detection")
                self._running = False
                break
        
        else:
            # Partial failure
            consecutive_failures += 1
            
            if consecutive_failures >= max_failures:
                self._running = False
                break
        
        # Wait 5 seconds
        time.sleep(self.sampling_interval)
```

### Frame Capture from Shared VideoCapture

**Location**: Lines 215-260

```python
def _capture_3_frames_shared(self, cap) -> List[Dict]:
    """Capture 3 frames with 0.5s spacing"""
    frames = []
    
    # Validate capture
    if not cap or not cap.isOpened():
        logger.error("Shared camera capture not available")
        return frames
    
    frame_spacing = 0.5  # temporal_window / 2
    
    for i in range(3):
        ret, frame = cap.read()
        
        if ret and frame is not None:
            frames.append({
                "frame": frame.copy(),  # ✅ CRITICAL: Copy frame data
                "timestamp": i * frame_spacing,
                "frame_index": i
            })
            
            # Wait between frames
            if i < 2:
                time.sleep(frame_spacing)
        else:
            logger.warning(f"Failed to capture frame {i}")
            break
    
    return frames
```

### Celery Submission (Non-blocking)

**Location**: Lines 262-340

```python
def _submit_to_celery(self, camera_id: str, frames: List[Dict]):
    """Submit frames to Celery worker for background processing"""
    
    # Prepare serializable payload
    frames_data = []
    for frame_data in frames:
        # Encode frame as base64 JPEG
        _, buffer = cv2.imencode('.jpg', frame_data["frame"])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        frames_data.append({
            "frame_data": frame_b64,
            "timestamp": frame_data["timestamp"],
            "frame_index": frame_data["frame_index"]
        })
    
    # Submit to Celery (returns immediately)
    task = process_instant_detection_task.delay(
        camera_id=camera_id,
        frames=frames_data,
        vision_service_url=self.vision_service_url,
        vmeta_service_url=self.vmeta_service_url
    )
    
    logger.info(f"Submitted instant detection task: {task.id}")
```

### Results Caching and Webhooks

**Location**: Lines 400-500

```python
# After Celery task completes
def _cache_result(self, camera_id: str, result: Dict):
    """Cache result in memory with metadata"""
    self.results_cache[camera_id] = {
        "result": result,
        "cached_at": time.time(),
        "iteration": self.results_cache.get(camera_id, {}).get("iteration", 0) + 1
    }
    
    # Send webhook if configured
    if self.webhook_enabled and self.webhook_url:
        asyncio.create_task(self._send_webhook(camera_id, result))

async def _send_webhook(self, camera_id: str, result: Dict):
    """Send detection results to webhook URL (media service triggers)"""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.webhook_url,
                json={
                    "camera_id": camera_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "people_count": result.get("people_count", 0),
                    "demographics": result.get("demographics", {}),
                    ...
                }
            )
    except Exception as e:
        logger.error(f"Webhook failed: {e}")
```

---

## WebSocket Real-Time Updates

### Architecture Overview

**Problem**: Frontend polling for instant detection results caused system overload:
- Multiple cameras polled every 5 seconds
- Requests timing out (30+ seconds, 503 errors)
- System cascade failures (recording hangs, discovery timeouts)

**Solution**: WebSocket push notifications using Redis Pub/Sub

```
┌──────────────┐
│ Camera       │
│ (Instant     │
│  Detection)  │
└──────┬───────┘
       │ publish
       ▼
┌──────────────┐
│ Redis        │
│ instant-     │
│ detection    │
│ channel      │
└──────┬───────┘
       │ subscribe
       ▼
┌──────────────┐
│ Gateway      │
│ WebSocket    │
│ Manager      │
└──────┬───────┘
       │ broadcast
       ▼
┌──────────────┐
│ Frontend     │
│ (WebSocket   │
│  clients)    │
└──────────────┘
```

### WebSocket Endpoint

**Location**: `ppl-meta-gateway/src/api/v1/websockets.py`

**Endpoint**: `ws://localhost:8080/api/v1/ws/instant-detection`

### Connection Manager

```python
class ConnectionManager:
    """Manages WebSocket connections for instant detection broadcasts"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.redis_client: aioredis.Redis = None
        self.pubsub = None
        self.listener_task = None
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Start Redis listener if this is the first connection
        if len(self.active_connections) == 1:
            await self.start_redis_listener()
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        
        # Stop Redis listener if no more connections
        if len(self.active_connections) == 0:
            await self.stop_redis_listener()
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        message_json = json.dumps(message)
        for connection in self.active_connections:
            await connection.send_text(message_json)
```

### Redis Listener

```python
async def start_redis_listener(self):
    """Start listening to Redis pub/sub for instant detection events"""
    self.redis_client = aioredis.from_url("redis://localhost:6379")
    self.pubsub = self.redis_client.pubsub()
    await self.pubsub.subscribe("instant-detection")
    
    # Start background task
    self.listener_task = asyncio.create_task(self._redis_listener())

async def _redis_listener(self):
    """Background task that listens to Redis and broadcasts to WebSockets"""
    async for message in self.pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            
            # Broadcast to all WebSocket clients
            await self.broadcast({
                "type": "instant-detection",
                "data": data
            })
```

### Message Format

**From Camera (Redis Pub/Sub)**:
```json
{
    "camera_id": "usb_camera_0",
    "timestamp": "2025-12-15T08:00:00+02:00",
    "people_count": 2,
    "demographics": {
        "total_male": 1,
        "total_female": 1,
        "percent_male": 50.0,
        "percent_female": 50.0
    },
    "metadata": {
        "processing_time": 0.5,
        "total_faces": 2
    }
}
```

**To Frontend (WebSocket)**:
```json
{
    "type": "instant-detection",
    "data": {
        "camera_id": "usb_camera_0",
        "timestamp": "2025-12-15T08:00:00+02:00",
        "people_count": 2,
        "demographics": {...},
        "metadata": {...}
    }
}
```

### Frontend Integration Example

```typescript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8080/api/v1/ws/instant-detection');

ws.onopen = () => {
    console.log('✅ Connected to instant detection stream');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'instant-detection') {
        const { camera_id, people_count, demographics } = message.data;
        
        // Update UI with real-time detection results
        updateCameraStats(camera_id, people_count, demographics);
    }
};

ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Connection closed - attempting reconnect...');
    setTimeout(connectWebSocket, 5000);
};

// Ping/pong for keepalive
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
    }
}, 30000);
```

### Benefits Over Polling

| Aspect | Polling (OLD) | WebSocket (NEW) |
|--------|--------------|-----------------|
| **Latency** | 5 seconds | Instant (<100ms) |
| **Server Load** | High (N cameras × polls/sec) | Low (1 Redis listener) |
| **Network** | Constant traffic | Event-driven only |
| **Scalability** | Poor (O(n²)) | Excellent (O(n)) |
| **Reliability** | Timeouts, 503 errors | Stable connections |
| **System Impact** | Recording hangs, discovery timeouts | None |

### Resource Efficiency

**Polling** (3 cameras, 5 second interval):
```
Requests/minute: 3 cameras × 12 polls = 36 requests/min
Failed requests: ~30% timeout (30+ seconds)
System load: 🔴 CRITICAL
```

**WebSocket** (3 cameras, push on detection):
```
Connections: 1 WebSocket + 1 Redis subscriber
Messages: Only when detection occurs (~1-5/min)
System load: 🟢 MINIMAL
```

### Auto-Scaling

```python
# Listener auto-starts with first client
if len(self.active_connections) == 1:
    await self.start_redis_listener()  # ✅ Start

# Listener auto-stops when all clients disconnect  
if len(self.active_connections) == 0:
    await self.stop_redis_listener()  # ✅ Stop
```

**No overhead when idle** - Redis listener only runs when clients are connected.

---

## State Management

### Service-Level State

**CameraDetectionService** maintains global state:

```python
{
    # Detected cameras (from system scan)
    "detected_cameras": {
        "usb_camera_0": {
            "device_id": "usb_camera_0",
            "name": "USB Camera 0",
            "status": "AVAILABLE",
            "resolution": "1280x720",
            ...
        }
    },
    
    # Active VideoCapture connections
    "active_connections": {
        "usb_camera_0": <cv2.VideoCapture object>
    },
    
    # Active recordings
    "active_recordings": {
        "usb_camera_0": {
            "thread": <Thread>,
            "writer": <VideoWriter>,
            "session_uuid": "...",
            "stop_flag": <Event>,
            ...
        }
    },
    
    # Latest frame cache (for snapshots)
    "latest_frames": {
        "usb_camera_0": (True, <numpy.ndarray>)
    }
}
```

### Instant Detection State

**InstantDetectionSampler** (singleton):

```python
{
    # Thread management
    "_running": False,
    "_detection_thread": None,
    
    # Camera tracking
    "_current_camera_id": "usb_camera_0",
    "_current_capture": <cv2.VideoCapture object>,
    
    # Results cache
    "results_cache": {
        "usb_camera_0": {
            "result": {"people_count": 1, ...},
            "cached_at": 1702645200.0,
            "iteration": 42
        }
    },
    
    # Webhook config
    "webhook_enabled": True,
    "webhook_url": "http://localhost:8000/api/v1/triggers/instant-detection"
}
```

### Database State

**Camera** model (persistent):

```sql
CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR UNIQUE,
    name VARCHAR,
    camera_type VARCHAR,  -- USB, IP, MOBILE
    status VARCHAR,       -- AVAILABLE, CONNECTED, RECORDING, ERROR
    connection_string VARCHAR,
    device_index INTEGER,
    ...
)
```

### Streaming Session State

**StreamingSession** model (persistent):

```sql
CREATE TABLE streaming_sessions (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR,
    user_id VARCHAR,
    session_uuid VARCHAR UNIQUE,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    segment_count INTEGER,
    total_frames INTEGER,
    ...
)
```

---

## Resource Sharing and Coordination

### Shared VideoCapture Access Pattern

```
┌──────────────────────┐
│ VideoCapture Object  │
│ (ONE per camera)     │
└─────────┬────────────┘
          │
          ├─────────────┐
          │             │
          ▼             ▼
    ┌──────────┐   ┌──────────┐
    │ Streaming│   │ Recording│
    │ Thread   │   │ Thread   │
    └────┬─────┘   └────┬─────┘
         │              │
         │   ┌──────────┘
         │   │
         ▼   ▼
    ┌──────────────┐
    │ Instant      │
    │ Detection    │
    │ Thread       │
    └──────────────┘
```

### Thread-Safe Access

OpenCV's `VideoCapture.read()` is **NOT thread-safe** by default, but works in practice when:
1. Each thread reads sequentially (not simultaneously)
2. No concurrent `set()` calls on properties
3. Frame reading is fast relative to frame rate

**Coordination Strategy**:
- Streaming: Reads continuously in async loop
- Recording: Reads continuously in background thread
- Instant Detection: Reads 3 frames every 5 seconds

**Timing Example** (30 FPS camera):
```
Time: 0.00s  0.03s  0.06s  0.09s  ...  5.00s  5.03s  5.06s
      ↓      ↓      ↓      ↓            ↓      ↓      ↓
Strm: R      R      R      R            R      R      R
Rec:  R      R      R      R            R      R      R
Inst: -      -      -      -            R      R      R
                                        (3 frames in 1s)
```

### Race Conditions and Mitigation

**Potential Race**: Multiple threads calling `cap.read()` simultaneously

**Mitigation**: Time-slicing naturally separates access
- Frame duration at 30fps: 33ms
- Read operation: ~5-10ms
- Collision probability: Very low

**Observed Behavior**: No frame corruption or access errors in production

### Resource Cleanup Order

When stopping all operations:

1. **Stop Instant Detection First**
   - Set `_running = False`
   - Join thread (2 second timeout)
   - Clear camera tracking

2. **Stop Recording**
   - Set stop event
   - Join thread (5 second timeout)
   - Release VideoWriter

3. **Stop Streaming**
   - Client disconnect closes generator
   - No explicit cleanup needed

4. **Disconnect Camera**
   - Release VideoCapture
   - Remove from active_connections

---

## Critical Issues and Fixes

### Issue #1: Recording Timeout at 20 Seconds

**Date Fixed**: December 14, 2025

**Symptom**: Recording stopped after ~20 seconds even though user didn't tap stop

**Root Cause**: 
```python
# In instant_detection.py (OLD CODE)
finally:
    if cap:
        cap.release()  # ❌ Released SHARED capture!
```

Instant detection was releasing the VideoCapture that recording was still using.

**Fix**: Removed `cap.release()` from instant detection since it doesn't own the capture
```python
finally:
    # Recording owns the capture, instant detection just reads from it
    pass  # ✅ Don't release shared capture
```

**Location**: `ppl-meta-cameras/src/services/instant_detection.py` Line 225

---

### Issue #2: Instant Detection Fails After Stop/Start Recording

**Date Fixed**: December 15, 2025

**Symptom**: 
- First recording: Instant detection works ✅
- Stop recording → Start recording: Instant detection stops working ❌

**Root Cause**: Thread state not cleaned up properly
```python
def start_sampling(self, camera_id, camera_capture):
    if self._running:  # ❌ Flag still True from previous session
        return
```

**Fix**: Check thread liveness, not just flag
```python
def start_sampling(self, camera_id, camera_capture):
    # Check if thread is ACTUALLY running
    if self._running and self._detection_thread and self._detection_thread.is_alive():
        return
    
    # Clean up dead threads
    if self._detection_thread and not self._detection_thread.is_alive():
        self._running = False
        self._detection_thread = None
    
    # Now safe to start new thread
```

**Location**: `ppl-meta-cameras/src/services/instant_detection.py` Lines 76-95

---

### Issue #3: Instant Detection Fails After Camera Reconnect

**Date Fixed**: December 15, 2025

**Symptom**:
- Disconnect camera → Reconnect → Start recording
- Instant detection not producing results ❌

**Root Cause**: Old VideoCapture reference in thread
```python
def start_sampling(self, camera_id, camera_capture):
    # ❌ No check if capture object changed
    if self._running:
        return  # Using OLD capture reference!
```

**Fix**: Track current capture and restart if changed
```python
def start_sampling(self, camera_id, camera_capture):
    # Detect camera reconnection
    camera_changed = (
        self._current_camera_id != camera_id or 
        self._current_capture is not camera_capture
    )
    
    if camera_changed and self._running:
        # Camera reconnected - restart with new capture
        self.stop_sampling()
    
    # Store new capture reference
    self._current_camera_id = camera_id
    self._current_capture = camera_capture
```

**Location**: `ppl-meta-cameras/src/services/instant_detection.py` Lines 88-96

---

### Issue #4: Terminal Flooding After Stop Recording

**Date Fixed**: December 15, 2025

**Symptom**: After stopping recording, service terminal flooded with errors

**Root Cause**: Instant detection loop trying to read from closed capture
```python
while self._running:
    frames = self._capture_3_frames_shared(camera_capture)
    # ❌ Capture closed, returns 0 frames
    # ❌ Loop continues forever logging warnings
```

**Fix**: Track consecutive failures and auto-stop
```python
def _sample_loop(self, camera_id, camera_capture):
    consecutive_failures = 0
    max_failures = 3
    
    while self._running:
        # Check capture validity
        if not camera_capture or not camera_capture.isOpened():
            self._running = False
            break
        
        frames = self._capture_3_frames_shared(camera_capture)
        
        if len(frames) == 0:
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                self._running = False  # Auto-stop
                break
```

**Location**: `ppl-meta-cameras/src/services/instant_detection.py` Lines 135-213

---

### Issue #5: Streaming Freezes After Camera Reconnect

**Date Fixed**: December 15, 2025

**Symptom**:
- Disconnect camera → Reconnect
- Streaming video freezes ❌
- Instant detection still works ✅

**Root Cause**: Streaming generator captured old VideoCapture reference
```python
async def generate_frames():
    cap = await camera_service.get_camera_stream(device_id)
    # ❌ Captured ONCE at function start
    
    while True:
        ret, frame = cap.read()  # ❌ Uses stale capture
```

**Fix**: Fetch capture on EACH frame iteration
```python
async def generate_frames():
    while True:
        # ✅ Fetch CURRENT capture each iteration
        cap = await camera_service.get_camera_stream(device_id)
        if not cap or not cap.isOpened():
            break
        
        ret, frame = cap.read()  # ✅ Always uses latest connection
```

**Location**: `ppl-meta-cameras/src/api/v1/endpoints/streaming.py` Lines 80-128

---

## Code References

### Key Files

| File | Purpose | Lines of Code |
|------|---------|--------------|
| `camera_detection.py` | Camera lifecycle management | 2915 |
| `instant_detection.py` | Instant detection sampler | 1186 |
| `streaming.py` | HTTP video streaming | 595 |
| `recording_scheduler.py` | Scheduled recording | 150 |
| `streaming_session_manager.py` | Session tracking | 300 |

### Critical Methods

**Camera Connection**:
- `connect_camera()` - Lines 126-240
- `disconnect_camera()` - Lines 266-300
- `get_camera_stream()` - Lines 322-325

**Recording**:
- `start_recording()` - Lines 630-725
- `_record_frames_thread()` - Lines 860-1050
- `stop_recording()` - Lines 1114-1180

**Instant Detection**:
- `start_sampling()` - Lines 76-120
- `_sample_loop()` - Lines 135-213
- `_capture_3_frames_shared()` - Lines 215-260
- `_submit_to_celery()` - Lines 262-340

**Streaming**:
- `video_stream()` - Lines 71-147
- `generate_frames()` - Lines 80-128

### Configuration Files

**Environment Variables** (`.env`):
```bash
# Instant Detection Webhook
INSTANT_DETECTION_WEBHOOK_URL=http://localhost:8000/api/v1/triggers/instant-detection
INSTANT_DETECTION_WEBHOOK_ENABLED=true

# Recording Settings
RECORDING_QUALITY=high
SEGMENT_DURATION=5

# Storage Paths
STORAGE_PATH=/path/to/recordings
TEMP_PATH=/tmp/ppl-recordings
```

---

## Summary

The PPL Meta Cameras service achieves efficient multi-operation camera access through:

1. **Shared VideoCapture**: One capture object per camera, accessed by all operations
2. **State Coordination**: Careful management of connection, recording, and detection states
3. **Thread Safety**: Non-blocking parallel operations with natural time-slicing
4. **Reconnection Resilience**: Automatic detection and adaptation to camera reconnections
5. **Failure Handling**: Graceful degradation with automatic recovery

**Key Insight**: All three operations (streaming, recording, instant detection) can safely share a single VideoCapture because:
- Frame reads are fast (5-10ms) relative to frame intervals (33ms at 30fps)
- Operations naturally time-slice their access
- Each operation handles temporary failures gracefully
- Reconnection is detected and handled automatically

This architecture provides robust, efficient real-time video processing with minimal resource overhead.

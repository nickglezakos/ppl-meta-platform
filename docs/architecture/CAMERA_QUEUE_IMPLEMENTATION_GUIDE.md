# Camera Queue Architecture - Complete Implementation Guide

## Document Purpose

This guide provides step-by-step instructions for implementing the complete camera functionality using the queue-based architecture. We're building from a clean slate after the December 2024 cleanup.

**Current State**: 
- ✅ Backend queue architecture implemented
- ✅ Frontend displays 3 cameras (USB, RTSP, Mobile)
- ✅ Camera detection working
- ⏳ Recording controls not wired up
- ⏳ Streaming not wired up

**Goal**: Fully functional camera system with recording, streaming, and real-time status updates.

---

## Phase 1: Backend Queue Infrastructure Validation

### Step 1.1: Verify CameraWorker Implementation

**File**: `ppl-meta-cameras/src/services/camera_service_queue.py`

**Check List**:
- [ ] `CameraWorker` class exists with:
  - `command_queue: queue.Queue()`
  - `frame_buffer: collections.deque(maxlen=1)`
  - `status: str` with thread-safe lock
  - `worker_thread: threading.Thread`
  - `_worker_loop()` method
- [ ] Worker processes commands: CONNECT, DISCONNECT, GET_FRAME
- [ ] Worker continuously buffers frames when connected
- [ ] Thread-safe frame access via `get_latest_frame()`

**Validation**:
```bash
# Check logs for worker creation
cd ppl-meta-cameras
tail -f logs/cameras.log | grep "WORKER"
```

Expected output:
```
🔧 [WORKER-usb_camera_0] Created worker thread
🔧 [WORKER-usb_camera_0] Starting worker loop
✅ [WORKER-usb_camera_0] Connected successfully
🎬 [WORKER-usb_camera_0] Frame buffered (1920x1080)
```

### Step 1.2: Verify Worker Manager

**File**: `ppl-meta-cameras/src/services/camera_service_queue.py`

**Check List**:
- [ ] `CameraServiceQueue` class manages all workers
- [ ] `connected_workers: Dict[str, CameraWorker]`
- [ ] `detect_cameras()` creates workers for detected cameras
- [ ] `connect_camera()` sends CONNECT command to worker
- [ ] `disconnect_camera()` sends DISCONNECT command and cleans up
- [ ] `get_worker()` retrieves worker by device_id

**Test**:
```bash
# Get auth token first
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r .access_token)

# Test detection
curl -X POST http://localhost:8005/api/v1/cameras/detect \
  -H "Authorization: Bearer $TOKEN"

# Check response
# Expected: {"status": "success", "cameras": [...]}
```

### Step 1.3: Verify Non-Blocking Operation

**Test Scenario**: Connect USB camera, then immediately connect RTSP camera

**Script**:
```bash
# Terminal 1: Start services
cd /Users/nickgklezakos/Documents/ppl-meta-code
# (Services should already be running)

# Terminal 2: Connect both cameras rapidly
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r .access_token)

# Connect USB camera (should return immediately)
time curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/connect \
  -H "Authorization: Bearer $TOKEN"

# Connect RTSP camera (should NOT wait for USB)
time curl -X POST http://localhost:8005/api/v1/cameras/rtsp_192.168.1.76_554/connect \
  -H "Authorization: Bearer $TOKEN"
```

**Success Criteria**:
- Each connect request returns in < 3 seconds
- Second request doesn't wait for first to complete
- Both cameras end up in "connected" status
- Logs show parallel worker operations

---

## Phase 2: Backend Recording Implementation

### Step 2.1: Recording Endpoint Implementation

**File**: `ppl-meta-cameras/src/api/v1/endpoints/cameras.py`

**Required Endpoints**:

#### 2.1.1 Start Recording
```python
@router.post("/{device_id}/recording/start")
async def start_recording(
    device_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start recording from camera worker buffer.
    
    Flow:
    1. Get worker for device_id
    2. Create recording session in database
    3. Start background task to read from worker.get_latest_frame()
    4. Write frames to video file
    5. Return session_id
    """
    worker = camera_service.get_worker(device_id)
    if not worker or worker.status != "connected":
        raise HTTPException(status_code=400, detail="Camera not connected")
    
    # Create recording session
    session_id = await recording_service.create_session(
        device_id=device_id,
        user_id=current_user['id']
    )
    
    # Start recording task (reads from worker buffer)
    background_tasks.add_task(
        recording_service.record_from_worker,
        worker=worker,
        session_id=session_id
    )
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Recording started"
    }
```

#### 2.1.2 Stop Recording
```python
@router.post("/{device_id}/recording/stop")
async def stop_recording(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Stop active recording session."""
    session = await recording_service.get_active_session(device_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active recording")
    
    await recording_service.stop_session(session.id)
    
    return {
        "status": "success",
        "session_id": session.id,
        "duration": session.duration,
        "file_path": session.file_path
    }
```

#### 2.1.3 Get Recording Status
```python
@router.get("/{device_id}/recording/status")
async def get_recording_status(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get current recording status."""
    session = await recording_service.get_active_session(device_id)
    
    return {
        "is_recording": session is not None,
        "session_id": session.id if session else None,
        "duration": session.duration if session else 0,
        "frame_count": session.frame_count if session else 0
    }
```

**Implementation Checklist**:
- [ ] Endpoints created in `cameras.py`
- [ ] `RecordingService` class created (see Step 2.2)
- [ ] Database models for recording sessions
- [ ] Error handling for camera not connected
- [ ] Authentication via `get_current_user`

### Step 2.2: Recording Service Implementation

**File**: `ppl-meta-cameras/src/services/recording_service.py` (NEW)

**Create Service**:
```python
import cv2
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RecordingService:
    """Manages video recording from camera workers."""
    
    def __init__(self, output_dir: str = "recordings"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_recordings: Dict[str, bool] = {}  # session_id -> stop_flag
    
    async def create_session(self, device_id: str, user_id: str) -> str:
        """Create recording session in database."""
        session_id = f"rec_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # TODO: Insert to database
        # await db.recording_sessions.insert({
        #     'id': session_id,
        #     'device_id': device_id,
        #     'user_id': user_id,
        #     'started_at': datetime.now(),
        #     'status': 'recording'
        # })
        
        return session_id
    
    async def record_from_worker(self, worker: CameraWorker, session_id: str):
        """Background task: continuously read frames from worker and write to video.
        
        This runs in a background task, reading from worker's frame buffer.
        NON-BLOCKING because worker.get_latest_frame() is instant.
        """
        try:
            # Setup video writer
            output_path = self.output_dir / f"{session_id}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Get resolution from worker camera_info
            width = worker.camera_info.get('resolution_width', 1920)
            height = worker.camera_info.get('resolution_height', 1080)
            fps = worker.camera_info.get('max_fps', 30)
            
            video_writer = cv2.VideoWriter(
                str(output_path), 
                fourcc, 
                fps, 
                (width, height)
            )
            
            self.active_recordings[session_id] = True
            frame_count = 0
            
            logger.info(f"🎥 [RECORDING] Started {session_id}")
            
            while self.active_recordings.get(session_id, False):
                # Get latest frame from worker buffer (INSTANT, non-blocking)
                frame = worker.get_latest_frame()
                
                if frame is not None:
                    video_writer.write(frame)
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        logger.debug(f"📹 [RECORDING] {session_id} - {frame_count} frames")
                
                # Small delay to target FPS
                await asyncio.sleep(1.0 / fps)
            
            # Cleanup
            video_writer.release()
            logger.info(f"✅ [RECORDING] Stopped {session_id} - {frame_count} frames saved to {output_path}")
            
            # Update database
            # await db.recording_sessions.update(session_id, {
            #     'stopped_at': datetime.now(),
            #     'status': 'completed',
            #     'frame_count': frame_count,
            #     'file_path': str(output_path)
            # })
            
        except Exception as e:
            logger.error(f"❌ [RECORDING] Error in {session_id}: {e}")
            self.active_recordings[session_id] = False
    
    async def stop_session(self, session_id: str):
        """Stop recording session."""
        self.active_recordings[session_id] = False
        logger.info(f"🛑 [RECORDING] Stop requested for {session_id}")
    
    async def get_active_session(self, device_id: str) -> Optional[dict]:
        """Get active recording session for device."""
        # TODO: Query database
        # return await db.recording_sessions.find_one({
        #     'device_id': device_id,
        #     'status': 'recording'
        # })
        return None
```

**Implementation Checklist**:
- [ ] `RecordingService` class created
- [ ] `record_from_worker()` background task implemented
- [ ] Video writer configured (codec, resolution, FPS)
- [ ] Stop mechanism via shared flag
- [ ] Database integration (or mock for testing)
- [ ] Logging for debugging

### Step 2.3: Testing Recording

**Test Script**: `test_recording_flow.py`

```python
import asyncio
import httpx
import time

async def test_recording():
    base_url = "http://localhost:8005/api/v1"
    
    # Login
    async with httpx.AsyncClient() as client:
        # Get token
        login_resp = await client.post(
            "http://localhost:8001/api/v1/users/login",
            data={
                "username": "fresh.user@example.com",
                "password": "NewPassword234!"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Start recording
        print("🎬 Starting recording...")
        start_resp = await client.post(
            f"{base_url}/cameras/usb_camera_0/recording/start",
            headers=headers
        )
        print(f"Response: {start_resp.json()}")
        session_id = start_resp.json()["session_id"]
        
        # Wait 10 seconds
        print("⏳ Recording for 10 seconds...")
        await asyncio.sleep(10)
        
        # Check status
        status_resp = await client.get(
            f"{base_url}/cameras/usb_camera_0/recording/status",
            headers=headers
        )
        print(f"Status: {status_resp.json()}")
        
        # Stop recording
        print("🛑 Stopping recording...")
        stop_resp = await client.post(
            f"{base_url}/cameras/usb_camera_0/recording/stop",
            headers=headers
        )
        print(f"Response: {stop_resp.json()}")
        
        print(f"✅ Test complete! Check recordings/{session_id}.mp4")

if __name__ == "__main__":
    asyncio.run(test_recording())
```

**Run Test**:
```bash
cd ppl-meta-cameras
python test_recording_flow.py
```

**Validation**:
- [ ] Recording starts without errors
- [ ] Video file created in `recordings/` directory
- [ ] File size increases during recording
- [ ] Stop request ends recording
- [ ] Video playable with VLC/QuickTime
- [ ] Backend logs show frame counts

---

## Phase 3: Backend Streaming Implementation

### Step 3.1: Streaming Endpoint

**File**: `ppl-meta-cameras/src/api/v1/endpoints/streaming.py`

**Implementation**:
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from ..auth import get_current_user
from ...services.camera_service_queue import camera_service
import cv2
import asyncio

router = APIRouter()

@router.get("/{device_id}/video")
async def video_stream(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """MJPEG video stream from camera worker buffer.
    
    Reads frames from worker.get_latest_frame() (non-blocking).
    """
    worker = camera_service.get_worker(device_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    if worker.status != "connected":
        raise HTTPException(status_code=400, detail=f"Camera not connected (status: {worker.status})")
    
    async def generate_frames():
        """Generator for MJPEG stream."""
        try:
            while True:
                # Get latest frame from worker buffer (INSTANT, non-blocking)
                frame = worker.get_latest_frame()
                
                if frame is not None:
                    # Encode to JPEG
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # Target 30 FPS
                await asyncio.sleep(0.033)
                
        except Exception as e:
            logger.error(f"❌ [STREAMING] Error for {device_id}: {e}")
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
```

**Implementation Checklist**:
- [ ] Endpoint created at `/api/v1/streaming/{device_id}/video`
- [ ] Returns `StreamingResponse` with MJPEG
- [ ] Reads from `worker.get_latest_frame()` (non-blocking)
- [ ] JPEG encoding with quality setting
- [ ] FPS control via sleep
- [ ] Error handling for disconnected camera

### Step 3.2: Test Streaming

**Browser Test**:
```bash
# Get token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r .access_token)

# Open in browser (need to pass token somehow)
open "http://localhost:8005/api/v1/streaming/usb_camera_0/video?token=$TOKEN"
```

**Python Test** (`test_streaming.py`):
```python
import httpx
import time

def test_streaming():
    # Get token
    resp = httpx.post(
        "http://localhost:8001/api/v1/users/login",
        data={
            "username": "fresh.user@example.com",
            "password": "NewPassword234!"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = resp.json()["access_token"]
    
    # Stream for 10 seconds
    print("🎥 Streaming for 10 seconds...")
    headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.stream("GET", 
                      "http://localhost:8005/api/v1/streaming/usb_camera_0/video",
                      headers=headers,
                      timeout=None) as stream:
        
        frame_count = 0
        start_time = time.time()
        
        for chunk in stream.iter_bytes():
            if b'--frame' in chunk:
                frame_count += 1
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"📊 Received {frame_count} frames ({fps:.1f} FPS)")
            
            if time.time() - start_time > 10:
                break
        
        print(f"✅ Test complete! Received {frame_count} frames")

if __name__ == "__main__":
    test_streaming()
```

**Validation**:
- [ ] Stream starts without errors
- [ ] Frames received consistently
- [ ] FPS approximately 30
- [ ] No frame freezing
- [ ] Can stream from multiple cameras simultaneously
- [ ] CPU usage reasonable (<50% per stream)

---

## Phase 4: Frontend Camera Lifecycle & WebSocket Status Integration

> **� EXISTING CODE REVIEW COMPLETED**:
> 
> **✅ ALREADY IMPLEMENTED**:
> - `connectCamera()` method in camera_service.dart (line 315)
> - `disconnectCamera()` method in camera_service.dart (line 387)
> - `stopRecording()` method in camera_service.dart (line 723)
> - `getRecordingStatus()` method in camera_service.dart (line 752)
> - `camera_status_providers.dart` exists (simplified version, no WebSocket)
> - pubspec.yaml dependencies checked
>
> **❌ MISSING / NEEDS IMPLEMENTATION**:
> - `startRecording()` method (not found in camera_service.dart)
> - WebSocket support (no web_socket_channel in pubspec.yaml)
> - Real-time status events (camera_status_providers.dart only has polling stub)
> - CameraStatusService for WebSocket management
> - Complete lifecycle event handling (8 event types)
>
> **🔧 IMPLEMENTATION PLAN**:
> 1. Add `web_socket_channel` to pubspec.yaml
> 2. Create `CameraStatusService` for WebSocket management
> 3. Replace simplified camera_status_providers.dart with full WebSocket implementation
> 4. Add `startRecording()` method to camera_service.dart
> 5. Update camera_card.dart to use real-time status
>
> ---

### Step 4.1: Understand the Camera Lifecycle

**Reference**: `docs/architecture/CAMERA_STATUS_SOLUTION.md`

**Camera States**:
1. **disconnected** - Camera detected but not connected (initial state)
2. **connecting** - Connection attempt in progress
3. **connected** - Camera successfully connected, ready for recording/streaming
4. **error** - Camera error occurred

**WebSocket Event Types** (8 total):
1. `connecting` - Connection initiated
2. `connected` - Successfully connected (OpenCV capture opened)
3. `disconnected` - Camera disconnected
4. `error` - Error occurred (with error message)
5. `recording_started` - Recording began (includes session_id, resolution, fps)
6. `recording_stopped` - Recording ended (includes frames, duration, file_path)
7. `streaming_started` - Stream client connected
8. `streaming_stopped` - Stream client disconnected

**Backend WebSocket Endpoints**:
- Single camera: `ws://localhost:8005/api/v1/cameras/ws/status/{device_id}?token={authToken}`
- All cameras: `ws://localhost:8005/api/v1/cameras/ws/status?token={authToken}`

### Step 4.2: Add WebSocket Package

**File**: `ppl-meta-frontend/pubspec.yaml`

**Check/Add Dependency**:
```yaml
dependencies:
  flutter:
    sdk: flutter
  web_socket_channel: ^2.4.0  # Add if not present
  flutter_riverpod: ^2.4.0
  dio: ^5.3.0
```

**Run**:
```bash
cd ppl-meta-frontend
flutter pub get
```

### Step 4.3: Create Camera Status Service

**File**: `ppl-meta-frontend/lib/core/services/camera_status_service.dart` (NEW)

**Implementation**:
```dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter/foundation.dart';

/// Service for managing WebSocket connections to camera status updates
class CameraStatusService {
  final String baseUrl;
  final String authToken;
  
  WebSocketChannel? _channel;
  StreamController<CameraStatusEvent>? _eventController;
  Timer? _reconnectTimer;
  bool _isDisposed = false;
  int _reconnectAttempts = 0;
  static const int maxReconnectAttempts = 5;
  static const Duration reconnectDelay = Duration(seconds: 2);
  
  CameraStatusService({
    required this.baseUrl,
    required this.authToken,
  });
  
  /// Subscribe to status updates for a specific camera
  Stream<CameraStatusEvent> subscribeToCameraStatus(String deviceId) {
    _eventController = StreamController<CameraStatusEvent>.broadcast();
    _connect(deviceId);
    return _eventController!.stream;
  }
  
  /// Subscribe to status updates for all cameras
  Stream<CameraStatusEvent> subscribeToAllCameras() {
    _eventController = StreamController<CameraStatusEvent>.broadcast();
    _connect(null);
    return _eventController!.stream;
  }
  
  void _connect(String? deviceId) {
    if (_isDisposed) return;
    
    try {
      final wsUrl = _buildWebSocketUrl(deviceId);
      debugPrint('🔌 Connecting to camera status WebSocket: $wsUrl');
      
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _reconnectAttempts = 0;
      
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: () => _handleDisconnect(deviceId),
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('❌ Failed to connect to WebSocket: $e');
      _scheduleReconnect(deviceId);
    }
  }
  
  String _buildWebSocketUrl(String? deviceId) {
    // Convert http://localhost:8005 to ws://localhost:8005
    final wsBase = baseUrl.replaceFirst('http://', 'ws://').replaceFirst('https://', 'wss://');
    
    if (deviceId != null) {
      return '$wsBase/api/v1/cameras/ws/status/$deviceId?token=$authToken';
    } else {
      return '$wsBase/api/v1/cameras/ws/status?token=$authToken';
    }
  }
  
  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message as String);
      final event = CameraStatusEvent.fromJson(data);
      
      debugPrint('📡 Camera status event: ${event.eventType} for ${event.deviceId}');
      
      if (!_isDisposed) {
        _eventController?.add(event);
      }
    } catch (e) {
      debugPrint('❌ Failed to parse camera status event: $e');
    }
  }
  
  void _handleError(dynamic error) {
    debugPrint('❌ WebSocket error: $error');
    if (!_isDisposed) {
      _eventController?.addError(error);
    }
  }
  
  void _handleDisconnect(String? deviceId) {
    debugPrint('🔌 WebSocket disconnected');
    _scheduleReconnect(deviceId);
  }
  
  void _scheduleReconnect(String? deviceId) {
    if (_isDisposed || _reconnectAttempts >= maxReconnectAttempts) {
      debugPrint('⚠️ Max reconnect attempts reached or service disposed');
      return;
    }
    
    _reconnectAttempts++;
    debugPrint('🔄 Scheduling reconnect attempt $_reconnectAttempts in ${reconnectDelay.inSeconds}s');
    
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(reconnectDelay, () {
      _connect(deviceId);
    });
  }
  
  void dispose() {
    _isDisposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _eventController?.close();
  }
}

/// Camera status event from WebSocket
class CameraStatusEvent {
  final String eventType;
  final String deviceId;
  final String? status;
  final DateTime timestamp;
  final Map<String, dynamic>? data;
  
  CameraStatusEvent({
    required this.eventType,
    required this.deviceId,
    this.status,
    required this.timestamp,
    this.data,
  });
  
  factory CameraStatusEvent.fromJson(Map<String, dynamic> json) {
    return CameraStatusEvent(
      eventType: json['event_type'] ?? json['type'],
      deviceId: json['device_id'],
      status: json['status'],
      timestamp: DateTime.parse(json['timestamp']),
      data: json['data'],
    );
  }
  
  bool get isConnecting => eventType == 'connecting';
  bool get isConnected => eventType == 'connected';
  bool get isDisconnected => eventType == 'disconnected';
  bool get isError => eventType == 'error';
  bool get isRecordingStarted => eventType == 'recording_started';
  bool get isRecordingStopped => eventType == 'recording_stopped';
  bool get isStreamingStarted => eventType == 'streaming_started';
  bool get isStreamingStopped => eventType == 'streaming_stopped';
  
  String? get errorMessage => data?['error'];
  String? get sessionId => data?['session_id'];
  int? get frameCount => data?['frames'];
  double? get duration => data?['duration'];
  String? get filePath => data?['file_path'];
}
```

**Implementation Checklist**:
- [ ] File created at `lib/core/services/camera_status_service.dart`
- [ ] WebSocket connection management implemented
- [ ] Auto-reconnection logic with exponential backoff
- [ ] Event parsing for all 8 event types
- [ ] Single camera and all-cameras subscription modes
- [ ] Proper disposal and cleanup

### Step 4.4: Create Camera Status Provider

**File**: `ppl-meta-frontend/lib/core/providers/camera_status_providers.dart` (NEW)

**Implementation**:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../services/camera_status_service.dart';
import '../services/camera_service.dart';
import '../models/camera.dart';

part 'camera_status_providers.g.dart';

/// Provider for camera status service
@riverpod
CameraStatusService cameraStatusService(CameraStatusServiceRef ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  final authToken = ref.watch(authTokenProvider); // Assumes you have auth provider
  
  final service = CameraStatusService(
    baseUrl: cameraService.baseUrl,
    authToken: authToken,
  );
  
  ref.onDispose(() {
    service.dispose();
  });
  
  return service;
}

/// Provider for camera status stream (single camera)
@riverpod
Stream<CameraStatusEvent> cameraStatusStream(
  CameraStatusStreamRef ref,
  String deviceId,
) {
  final service = ref.watch(cameraStatusServiceProvider);
  return service.subscribeToCameraStatus(deviceId);
}

/// Provider for all cameras status stream
@riverpod
Stream<CameraStatusEvent> allCamerasStatusStream(
  AllCamerasStatusStreamRef ref,
) {
  final service = ref.watch(cameraStatusServiceProvider);
  return service.subscribeToAllCameras();
}

/// State notifier for camera status
class CameraStatusNotifier extends StateNotifier<Map<String, CameraStatus>> {
  final CameraStatusService _statusService;
  StreamSubscription? _subscription;
  
  CameraStatusNotifier(this._statusService) : super({}) {
    _subscribeToAllCameras();
  }
  
  void _subscribeToAllCameras() {
    _subscription = _statusService.subscribeToAllCameras().listen(
      _handleStatusEvent,
      onError: (error) {
        debugPrint('❌ Camera status stream error: $error');
      },
    );
  }
  
  void _handleStatusEvent(CameraStatusEvent event) {
    final currentStatus = state[event.deviceId] ?? CameraStatus(
      deviceId: event.deviceId,
      status: 'disconnected',
    );
    
    CameraStatus newStatus;
    
    switch (event.eventType) {
      case 'connecting':
        newStatus = currentStatus.copyWith(status: 'connecting');
        break;
        
      case 'connected':
        newStatus = currentStatus.copyWith(
          status: 'connected',
          error: null,
        );
        break;
        
      case 'disconnected':
        newStatus = currentStatus.copyWith(
          status: 'disconnected',
          isRecording: false,
          isStreaming: false,
        );
        break;
        
      case 'error':
        newStatus = currentStatus.copyWith(
          status: 'error',
          error: event.errorMessage,
        );
        break;
        
      case 'recording_started':
        newStatus = currentStatus.copyWith(
          isRecording: true,
          recordingSessionId: event.sessionId,
          recordingStartTime: event.timestamp,
        );
        break;
        
      case 'recording_stopped':
        newStatus = currentStatus.copyWith(
          isRecording: false,
          recordingSessionId: null,
          recordingStartTime: null,
          lastRecordingPath: event.filePath,
        );
        break;
        
      case 'streaming_started':
        newStatus = currentStatus.copyWith(isStreaming: true);
        break;
        
      case 'streaming_stopped':
        newStatus = currentStatus.copyWith(isStreaming: false);
        break;
        
      default:
        newStatus = currentStatus;
    }
    
    state = {...state, event.deviceId: newStatus};
  }
  
  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}

/// Provider for camera status state
@riverpod
CameraStatusNotifier cameraStatusNotifier(CameraStatusNotifierRef ref) {
  final service = ref.watch(cameraStatusServiceProvider);
  return CameraStatusNotifier(service);
}

/// Provider to get status for a specific camera
@riverpod
CameraStatus? cameraStatus(CameraStatusRef ref, String deviceId) {
  final statusMap = ref.watch(cameraStatusNotifierProvider);
  return statusMap[deviceId];
}

/// Camera status model
class CameraStatus {
  final String deviceId;
  final String status; // disconnected, connecting, connected, error
  final bool isRecording;
  final bool isStreaming;
  final String? recordingSessionId;
  final DateTime? recordingStartTime;
  final String? lastRecordingPath;
  final String? error;
  
  CameraStatus({
    required this.deviceId,
    required this.status,
    this.isRecording = false,
    this.isStreaming = false,
    this.recordingSessionId,
    this.recordingStartTime,
    this.lastRecordingPath,
    this.error,
  });
  
  CameraStatus copyWith({
    String? status,
    bool? isRecording,
    bool? isStreaming,
    String? recordingSessionId,
    DateTime? recordingStartTime,
    String? lastRecordingPath,
    String? error,
  }) {
    return CameraStatus(
      deviceId: deviceId,
      status: status ?? this.status,
      isRecording: isRecording ?? this.isRecording,
      isStreaming: isStreaming ?? this.isStreaming,
      recordingSessionId: recordingSessionId ?? this.recordingSessionId,
      recordingStartTime: recordingStartTime ?? this.recordingStartTime,
      lastRecordingPath: lastRecordingPath ?? this.lastRecordingPath,
      error: error ?? this.error,
    );
  }
  
  bool get isDisconnected => status == 'disconnected';
  bool get isConnecting => status == 'connecting';
  bool get isConnected => status == 'connected';
  bool get hasError => status == 'error';
}
```

**Implementation Checklist**:
- [ ] File created at `lib/core/providers/camera_status_providers.dart`
- [ ] Status service provider created
- [ ] Stream providers for single and all cameras
- [ ] StateNotifier handles all 8 event types
- [ ] CameraStatus model includes all states
- [ ] Proper disposal and cleanup

### Step 4.5: Update Camera Service with Connection Methods

**File**: `ppl-meta-frontend/lib/core/services/camera_service.dart`

**Add Methods**:
```dart
/// Connect to a camera
Future<Map<String, dynamic>> connectCamera(String deviceId) async {
  final response = await _dio.post(
    '/api/v1/cameras/$deviceId/connect',
    options: Options(
      headers: {'Authorization': 'Bearer $_token'},
    ),
  );
  return response.data;
}

/// Disconnect from a camera
Future<Map<String, dynamic>> disconnectCamera(String deviceId) async {
  final response = await _dio.post(
    '/api/v1/cameras/$deviceId/disconnect',
    options: Options(
      headers: {'Authorization': 'Bearer $_token'},
    ),
  );
  return response.data;
}

/// Get camera status
Future<Map<String, dynamic>> getCameraStatus(String deviceId) async {
  final response = await _dio.get(
    '/api/v1/cameras/$deviceId/status',
    options: Options(
      headers: {'Authorization': 'Bearer $_token'},
    ),
  );
  return response.data;
}
```

### Step 4.6: Update Camera Card with Connection Controls

**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**Add Connection Button**:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers/camera_status_providers.dart';
import '../../../core/services/camera_service.dart';

class CameraCard extends ConsumerWidget {
  final Camera camera;
  
  const CameraCard({Key? key, required this.camera}) : super(key: key);
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch real-time status from WebSocket
    final cameraStatus = ref.watch(cameraStatusProvider(camera.deviceId));
    
    return Card(
      child: Column(
        children: [
          // Camera preview/placeholder
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Container(
              color: Colors.black,
              child: _buildStatusOverlay(cameraStatus),
            ),
          ),
          
          // Camera info
          Padding(
            padding: EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  camera.name ?? camera.deviceId,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                SizedBox(height: 4),
                _StatusIndicatorRow(status: cameraStatus),
              ],
            ),
          ),
          
          // Control buttons
          ButtonBar(
            children: [
              _ConnectionButton(camera: camera, status: cameraStatus),
              // Recording and streaming buttons will be added in Phase 5-6
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildStatusOverlay(CameraStatus? status) {
    if (status == null || status.isDisconnected) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.videocam_off, size: 48, color: Colors.grey),
            SizedBox(height: 8),
            Text('Camera Disconnected', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }
    
    if (status.isConnecting) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 8),
            Text('Connecting...', style: TextStyle(color: Colors.white)),
          ],
        ),
      );
    }
    
    if (status.hasError) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error, size: 48, color: Colors.red),
            SizedBox(height: 8),
            Text(
              status.error ?? 'Camera Error',
              style: TextStyle(color: Colors.red),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }
    
    // Connected - show live preview or placeholder
    return Center(
      child: Icon(Icons.videocam, size: 48, color: Colors.green),
    );
  }
}

class _StatusIndicatorRow extends StatelessWidget {
  final CameraStatus? status;
  
  const _StatusIndicatorRow({required this.status});
  
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _StatusDot(status: status),
        SizedBox(width: 8),
        Text(_getStatusText()),
        Spacer(),
        if (status?.isRecording == true) ...[
          Icon(Icons.fiber_manual_record, color: Colors.red, size: 16),
          SizedBox(width: 4),
          Text('Recording', style: TextStyle(color: Colors.red)),
        ],
        if (status?.isStreaming == true) ...[
          SizedBox(width: 8),
          Icon(Icons.cast, color: Colors.blue, size: 16),
          SizedBox(width: 4),
          Text('Streaming', style: TextStyle(color: Colors.blue)),
        ],
      ],
    );
  }
  
  String _getStatusText() {
    if (status == null) return 'Unknown';
    if (status!.hasError) return 'Error';
    if (status!.isConnecting) return 'Connecting...';
    if (status!.isConnected) return 'Connected';
    return 'Disconnected';
  }
}

class _StatusDot extends StatelessWidget {
  final CameraStatus? status;
  
  const _StatusDot({required this.status});
  
  @override
  Widget build(BuildContext context) {
    Color color = Colors.grey;
    
    if (status != null) {
      if (status!.hasError) {
        color = Colors.red;
      } else if (status!.isConnecting) {
        color = Colors.yellow;
      } else if (status!.isConnected) {
        color = Colors.green;
      }
    }
    
    return Container(
      width: 12,
      height: 12,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
      ),
    );
  }
}

class _ConnectionButton extends ConsumerStatefulWidget {
  final Camera camera;
  final CameraStatus? status;
  
  const _ConnectionButton({required this.camera, required this.status});
  
  @override
  ConsumerState<_ConnectionButton> createState() => _ConnectionButtonState();
}

class _ConnectionButtonState extends ConsumerState<_ConnectionButton> {
  bool _isLoading = false;
  
  Future<void> _handleConnection() async {
    if (_isLoading) return;
    
    setState(() => _isLoading = true);
    
    try {
      final cameraService = ref.read(cameraServiceProvider);
      
      if (widget.status?.isConnected == true) {
        // Disconnect
        await cameraService.disconnectCamera(widget.camera.deviceId);
      } else {
        // Connect
        await cameraService.connectCamera(widget.camera.deviceId);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final isConnected = widget.status?.isConnected == true;
    final isConnecting = widget.status?.isConnecting == true;
    
    return ElevatedButton.icon(
      onPressed: (_isLoading || isConnecting) ? null : _handleConnection,
      icon: _isLoading || isConnecting
          ? SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(isConnected ? Icons.power_off : Icons.power),
      label: Text(isConnected ? 'Disconnect' : 'Connect'),
      style: ElevatedButton.styleFrom(
        backgroundColor: isConnected ? Colors.red : Colors.green,
      ),
    );
  }
}
```

**Implementation Checklist**:
- [ ] Camera card watches WebSocket status provider
- [ ] Status indicator shows real-time connection state
- [ ] Connect/disconnect button implemented
- [ ] Loading states handled
- [ ] Error states displayed
- [ ] Status colors: grey (disconnected), yellow (connecting), green (connected), red (error)

### Step 4.7: Testing Camera Lifecycle

**Test Plan**:

1. **Open Flutter App**
   - Navigate to cameras screen
   - Verify all cameras show "Disconnected" with grey dot

2. **Connect Camera**
   - Tap "Connect" button on USB camera
   - Verify status changes: disconnected → connecting (yellow dot) → connected (green dot)
   - Verify button changes to "Disconnect" (red)

3. **WebSocket Events**
   - Open browser console or Flutter logs
   - Verify WebSocket connection established
   - Verify "connecting" event received
   - Verify "connected" event received

4. **Multiple Cameras**
   - Connect USB camera
   - Connect RTSP camera (without waiting for USB to finish)
   - Verify both show independent status updates
   - Verify no blocking between operations

5. **Error Handling**
   - Try connecting to RTSP with wrong URL
   - Verify "error" event received
   - Verify error message displayed
   - Verify status dot turns red

6. **Disconnection**
   - Disconnect connected camera
   - Verify "disconnected" event received
   - Verify UI returns to disconnected state
   - Verify status dot turns grey

7. **Auto-Reconnection**
   - Connect camera
   - Stop backend service
   - Verify WebSocket detects disconnect
   - Restart backend service
   - Verify WebSocket reconnects automatically

**Success Criteria**:
- [ ] All status changes reflected in real-time (no page refresh needed)
- [ ] Status indicators update immediately on events
- [ ] No polling (all updates via WebSocket)
- [ ] Multiple cameras work independently
- [ ] Connection/disconnection smooth
- [ ] Error states handled gracefully

---

## Phase 5: Frontend Recording Integration

> **📋 PREREQUISITE**: Phase 4 (Camera Lifecycle & WebSocket) must be complete. Cameras must be in "connected" state before recording can start.

> **⚠️ CRITICAL UI PERFORMANCE GUIDELINE**:
> 
> All status widgets (recording indicators, timers, counters, buttons) MUST be implemented as **adjacent/sibling widgets** to the camera stream, NOT as overlays or children of the stream widget.
> 
> **Why**: State updates in status widgets (e.g., timer ticking every second) will trigger rebuilds. If these widgets are part of the stream widget tree, they will cause the video stream to rebuild/flicker, resulting in choppy playback.
> 
> **Architecture Pattern**:
> ```dart
> Column(
>   children: [
>     CameraStreamPlayer(...),  // Isolated - no rebuilds from status changes
>     SizedBox(height: 8),
>     RecordingStatusBar(...),  // Adjacent - rebuilds independently
>   ]
> )
> ```
> 
> **Do NOT**:
> ```dart
> Stack(
>   children: [
>     CameraStreamPlayer(...),
>     Positioned(child: RecordingTimer(...)),  // BAD - causes stream rebuilds
>   ]
> )
> ```

### Step 4.1: Update Camera Service

**File**: `ppl-meta-frontend/lib/core/services/camera_service.dart`

**Add Methods**:
```dart
// Recording methods
Future<Map<String, dynamic>> startRecording(String deviceId) async {
  final response = await _dio.post(
    '/api/v1/cameras/$deviceId/recording/start',
    options: Options(
      headers: {'Authorization': 'Bearer $_token'},
    ),
  );
  return response.data;
}

Future<Map<String, dynamic>> stopRecording(String deviceId) async {
  final response = await _dio.post(
    '/api/v1/cameras/$deviceId/recording/stop',
    options: Options(
      headers: {'Authorization': 'Bearer $_token'},
    ),
  );
  return response.data;
}

Future<Map<String, dynamic>> getRecordingStatus(String deviceId) async {
  final response = await _dio.get(
    '/api/v1/cameras/$deviceId/recording/status',
    options: Options(
      headers: {'Authorization': 'Bearer $_token'},
    ),
  );
  return response.data;
}
```

**Implementation Checklist**:
- [ ] Methods added to `CameraService` class
- [ ] Proper error handling with try-catch
- [ ] Token passed in Authorization header
- [ ] Returns typed responses

### Step 5.2: Update Recording Provider

**File**: `ppl-meta-frontend/lib/core/providers/camera_providers.dart`

**Enhance Provider**:
```dart
class CameraRecordingNotifier extends StateNotifier<Map<String, RecordingState>> {
  final CameraService _cameraService;
  
  CameraRecordingNotifier(this._cameraService) : super({});
  
  Future<void> startRecording(String deviceId) async {
    try {
      // Update state to starting
      state = {
        ...state,
        deviceId: RecordingState(
          isRecording: false,
          isLoading: true,
        ),
      };
      
      // Call backend
      final response = await _cameraService.startRecording(deviceId);
      final sessionId = response['session_id'];
      
      // Update state to recording
      state = {
        ...state,
        deviceId: RecordingState(
          isRecording: true,
          isLoading: false,
          sessionId: sessionId,
          startTime: DateTime.now(),
        ),
      };
      
      // Start polling for status updates
      _startStatusPolling(deviceId);
      
    } catch (e) {
      // Update state to error
      state = {
        ...state,
        deviceId: RecordingState(
          isRecording: false,
          isLoading: false,
          error: e.toString(),
        ),
      };
    }
  }
  
  Future<void> stopRecording(String deviceId) async {
    try {
      // Update state to stopping
      final currentState = state[deviceId];
      state = {
        ...state,
        deviceId: currentState!.copyWith(isLoading: true),
      };
      
      // Call backend
      final response = await _cameraService.stopRecording(deviceId);
      
      // Update state to stopped
      state = {
        ...state,
        deviceId: RecordingState(
          isRecording: false,
          isLoading: false,
          duration: response['duration'],
          filePath: response['file_path'],
        ),
      };
      
      // Stop polling
      _stopStatusPolling(deviceId);
      
    } catch (e) {
      // Update state to error
      state = {
        ...state,
        deviceId: state[deviceId]!.copyWith(
          isLoading: false,
          error: e.toString(),
        ),
      };
    }
  }
  
  Timer? _statusTimer;
  
  void _startStatusPolling(String deviceId) {
    _statusTimer?.cancel();
    _statusTimer = Timer.periodic(Duration(seconds: 2), (_) async {
      try {
        final status = await _cameraService.getRecordingStatus(deviceId);
        
        // Update duration
        if (status['is_recording']) {
          final currentState = state[deviceId];
          state = {
            ...state,
            deviceId: currentState!.copyWith(
              frameCount: status['frame_count'],
            ),
          };
        }
      } catch (e) {
        // Ignore polling errors
      }
    });
  }
  
  void _stopStatusPolling(String deviceId) {
    _statusTimer?.cancel();
    _statusTimer = null;
  }
}

// Recording state model
class RecordingState {
  final bool isRecording;
  final bool isLoading;
  final String? sessionId;
  final DateTime? startTime;
  final int? frameCount;
  final int? duration;
  final String? filePath;
  final String? error;
  
  RecordingState({
    required this.isRecording,
    required this.isLoading,
    this.sessionId,
    this.startTime,
    this.frameCount,
    this.duration,
    this.filePath,
    this.error,
  });
  
  RecordingState copyWith({
    bool? isRecording,
    bool? isLoading,
    String? sessionId,
    DateTime? startTime,
    int? frameCount,
    int? duration,
    String? filePath,
    String? error,
  }) {
    return RecordingState(
      isRecording: isRecording ?? this.isRecording,
      isLoading: isLoading ?? this.isLoading,
      sessionId: sessionId ?? this.sessionId,
      startTime: startTime ?? this.startTime,
      frameCount: frameCount ?? this.frameCount,
      duration: duration ?? this.duration,
      filePath: filePath ?? this.filePath,
      error: error ?? this.error,
    );
  }
}
```

**Implementation Checklist**:
- [ ] `startRecording()` calls backend and updates state
- [ ] `stopRecording()` calls backend and updates state
- [ ] Listen to WebSocket events instead of polling
- [ ] `RecordingState` model includes all fields
- [ ] Loading states handled properly
- [ ] Error states handled properly

### Step 5.3: Wire Up Camera Card

**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**⚠️ UI Architecture Requirements**:

1. **Widget Isolation**: Recording controls MUST be adjacent to (not overlaid on) camera preview
2. **State Scoping**: Use `Consumer` or `ref.watch` at the narrowest scope possible
3. **Timer Independence**: Recording timer widget should be completely separate from stream widget

**Recommended Layout Structure**:
```dart
// camera_card.dart structure
Card(
  child: Column(
    children: [
      // 1. Stream preview (isolated, no state dependencies)
      AspectRatio(
        aspectRatio: 16 / 9,
        child: CameraStreamPlayer(deviceId: camera.deviceId),
      ),
      
      Divider(),
      
      // 2. Status row (separate widget tree, rebuilds independently)
      Padding(
        padding: EdgeInsets.all(8),
        child: _CameraStatusRow(camera: camera),
      ),
      
      // 3. Control buttons (separate widget tree)
      _CameraControlButtons(camera: camera),
    ],
  ),
)

// Separate widget for status updates
class _CameraStatusRow extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recordingState = ref.watch(recordingProvider(camera.deviceId));
    
    return Row(
      children: [
        // Recording indicator (rebuilds don't affect stream)
        if (recordingState.isRecording)
          Row(children: [
            Icon(Icons.circle, color: Colors.red, size: 12),
            SizedBox(width: 4),
            _RecordingTimer(startTime: recordingState.startTime!),
          ]),
        
        Spacer(),
        
        // Connection status
        Text(camera.status),
      ],
    );
  }
}

// Timer widget - rebuilds every second but isolated from stream
class _RecordingTimer extends StatefulWidget {
  final DateTime startTime;
  const _RecordingTimer({required this.startTime});
  
  @override
  State<_RecordingTimer> createState() => _RecordingTimerState();
}

class _RecordingTimerState extends State<_RecordingTimer> {
  Timer? _timer;
  Duration _elapsed = Duration.zero;
  
  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(Duration(seconds: 1), (_) {
      setState(() {
        _elapsed = DateTime.now().difference(widget.startTime);
      });
    });
  }
  
  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Text(_formatDuration(_elapsed));
  }
  
  String _formatDuration(Duration d) {
    return '${d.inMinutes.toString().padLeft(2, '0')}:'
           '${(d.inSeconds % 60).toString().padLeft(2, '0')}';
  }
}
```

**Update Recording Controls**:
```dart
class _RecordingControls extends ConsumerWidget {
  final Camera camera;
  
  const _RecordingControls({required this.camera});
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch recording state for this camera
    final recordingState = ref.watch(
      cameraRecordingProvider.select((state) => state[camera.deviceId])
    );
    
    final isRecording = recordingState?.isRecording ?? false;
    final isLoading = recordingState?.isLoading ?? false;
    
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Recording indicator
        if (isRecording)
          Container(
            width: 8,
            height: 8,
            margin: const EdgeInsets.only(right: 8),
            decoration: BoxDecoration(
              color: Colors.red,
              shape: BoxShape.circle,
            ),
          ),
        
        // Recording button
        IconButton(
          onPressed: isLoading ? null : () {
            if (isRecording) {
              ref.read(cameraRecordingProvider.notifier)
                  .stopRecording(camera.deviceId);
            } else {
              ref.read(cameraRecordingProvider.notifier)
                  .startRecording(camera.deviceId);
            }
          },
          icon: isLoading
              ? SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Icon(
                  isRecording ? Icons.stop : Icons.fiber_manual_record,
                  color: isRecording ? Colors.red : null,
                ),
          tooltip: isRecording ? 'Stop Recording' : 'Start Recording',
        ),
        
        // Duration display
        if (isRecording && recordingState?.startTime != null)
          Text(
            _formatDuration(
              DateTime.now().difference(recordingState!.startTime!)
            ),
            style: TextStyle(
              fontSize: 12,
              color: Colors.red,
              fontWeight: FontWeight.bold,
            ),
          ),
      ],
    );
  }
  
  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes.toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }
}
```

**Implementation Checklist**:
- [ ] Recording button wired to provider
- [ ] Loading state shows spinner
- [ ] Recording indicator shows red dot adjacent to stream (NOT overlaid)
- [ ] Duration counter updates every second (in separate widget)
- [ ] Disabled state when loading
- [ ] Stream widget never rebuilds from recording state changes

---

## Phase 6: Frontend Streaming Integration

> **📋 PREREQUISITE**: Phase 4 (Camera Lifecycle) and Phase 5 (Recording) should be complete. Cameras must be connected to stream.

> **⚠️ STREAM WIDGET ISOLATION**:
> 
> The `CameraStreamPlayer` widget MUST be completely isolated from state changes in surrounding widgets.
> 
> **Best Practices**:
> 1. **No Parent Rebuilds**: Wrap stream player in `RepaintBoundary` if needed
> 2. **Const Constructors**: Use `const` for all static parameters
> 3. **Key Stability**: Use stable keys (`ValueKey(deviceId)`) to prevent unnecessary rebuilds
> 4. **Separate Controllers**: Keep play/pause/fullscreen controls in adjacent widgets
> 
> **Example**:
> ```dart
> RepaintBoundary(
>   child: CameraStreamPlayer(
>     key: ValueKey('stream_${camera.deviceId}'),
>     deviceId: camera.deviceId,
>     baseUrl: AppConfig.cameraServiceUrl,
>     token: authToken,
>   ),
> )
> ```

### Step 6.1: Update Stream Player

**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_stream_player.dart`

**Verify Implementation**:
```dart
class CameraStreamPlayer extends StatelessWidget {
  final String deviceId;
  final String baseUrl;
  final String token;
  
  const CameraStreamPlayer({
    Key? key,
    required this.deviceId,
    required this.baseUrl,
    required this.token,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    final streamUrl = '$baseUrl/api/v1/streaming/$deviceId/video';
    
    return Image.network(
      streamUrl,
      headers: {'Authorization': 'Bearer $token'},
      fit: BoxFit.contain,
      errorBuilder: (context, error, stackTrace) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error, color: Colors.red, size: 48),
              SizedBox(height: 8),
              Text('Stream Error', style: TextStyle(color: Colors.red)),
              Text(error.toString(), style: TextStyle(fontSize: 12)),
            ],
          ),
        );
      },
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) return child;
        return Center(
          child: CircularProgressIndicator(
            value: loadingProgress.expectedTotalBytes != null
                ? loadingProgress.cumulativeBytesLoaded / 
                  loadingProgress.expectedTotalBytes!
                : null,
          ),
        );
      },
    );
  }
}
```

**Implementation Checklist**:
- [ ] Uses `Image.network` with MJPEG stream URL
- [ ] Passes Authorization header with token
- [ ] Shows loading indicator while connecting
- [ ] Shows error message if stream fails
- [ ] `fit: BoxFit.contain` to preserve aspect ratio
- [ ] Widget is stateless or uses `const` constructor for stability
- [ ] Wrapped in `RepaintBoundary` for rendering isolation

### Step 6.2: Add Stream View to Camera Card

**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**Add Play Button**:
```dart
// In camera_card.dart, add to bottom actions row:

IconButton(
  onPressed: () {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CameraStreamPage(
          camera: camera,
        ),
      ),
    );
  },
  icon: Icon(Icons.play_circle_outline),
  tooltip: 'View Stream',
),
```

**Create Stream Page** (`camera_stream_page.dart` - NEW):
```dart
import 'package:flutter/material.dart';
import '../../../core/models/camera.dart';
import '../../../core/services/camera_service.dart';
import '../../widgets/camera/camera_stream_player.dart';

class CameraStreamPage extends StatelessWidget {
  final Camera camera;
  
  const CameraStreamPage({Key? key, required this.camera}) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    final cameraService = CameraService();
    
    return Scaffold(
      appBar: AppBar(
        title: Text(camera.name ?? camera.deviceId),
      ),
      body: Column(  // Use Column for vertical layout
        children: [
          // Stream player takes most space (isolated from controls)
          Expanded(
            child: Center(
              child: RepaintBoundary(
                child: CameraStreamPlayer(
                  key: ValueKey('stream_${camera.deviceId}'),
                  deviceId: camera.deviceId,
                  baseUrl: cameraService.baseUrl,
                  token: cameraService.token,
                ),
              ),
            ),
          ),
          
          // Control bar below stream (not overlaid)
          Container(
            color: Colors.black87,
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                // Camera info
                Expanded(
                  child: Text(
                    '${camera.deviceId} - Live',
                    style: TextStyle(color: Colors.white70),
                  ),
                ),
                
                // Fullscreen button
                IconButton(
                  icon: Icon(Icons.fullscreen, color: Colors.white),
                  onPressed: () {
                    // TODO: Toggle fullscreen
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

**Implementation Checklist**:
- [ ] Play button added to camera card
- [ ] Stream displayed in separate widget tree from controls
- [ ] RepaintBoundary wraps stream for rendering isolation
- [ ] `CameraStreamPage` created with Column layout (not Stack)
- [ ] Stream player embedded in page
- [ ] Back button works
- [ ] Control bar positioned below stream, not overlaid
- [ ] Fullscreen toggle optional (can add later)

---

## Phase 7: Testing & Validation

> **⚠️ PERFORMANCE TESTING FOCUS**:
> 
> During testing, specifically verify:
> 1. **Stream Smoothness**: Video should play at consistent FPS without stuttering
> 2. **No Rebuild Interference**: Timer ticking should NOT cause visible frame drops
> 3. **Multiple Streams**: Multiple camera streams should maintain smoothness independently
> 4. **Memory Stability**: Watch for memory leaks during extended streaming/recording
> 
> **Test Methodology**:
> - Open Flutter DevTools Performance tab during testing
> - Monitor frame rendering times (should stay <16ms for 60fps UI)
> - Watch for excessive rebuilds in stream widget using Flutter Inspector
> - Use `debugPrintRebuildDirtyWidgets = true` to track rebuilds
> - Verify RepaintBoundary effectiveness with Performance Overlay
> 
> **Red Flags**:
> - Stream widget showing in rebuild logs when timer updates
> - Frame rendering spikes >33ms (indicating dropped frames)
> - Increasing memory usage over time
> - UI jank when starting/stopping recording

### Step 7.1: Unit Tests

**Backend Tests** (`ppl-meta-cameras/tests/test_camera_worker.py`):
```python
import pytest
import time
from src.services.camera_service_queue import CameraWorker

def test_worker_lifecycle():
    """Test worker creation, start, stop."""
    worker = CameraWorker(device_id="test_camera", camera_type="usb")
    
    # Start worker thread
    worker.start()
    assert worker.worker_thread.is_alive()
    
    # Stop worker
    worker.stop()
    worker.worker_thread.join(timeout=5)
    assert not worker.worker_thread.is_alive()

def test_frame_buffer():
    """Test frame buffering."""
    worker = CameraWorker(device_id="test_camera", camera_type="usb")
    worker.start()
    
    # Mock connection
    worker.status = "connected"
    
    # Wait for frames (mock would need real camera)
    time.sleep(1)
    
    # Get frame
    frame = worker.get_latest_frame()
    assert frame is not None or worker.status != "connected"
    
    worker.stop()
```

**Frontend Tests** (`ppl-meta-frontend/test/widget_test.dart`):
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:ppl_meta_platform/presentation/widgets/camera/camera_card.dart';

void main() {
  testWidgets('Camera card displays camera info', (WidgetTester tester) async {
    final camera = Camera(
      deviceId: 'test_camera',
      name: 'Test Camera',
      status: 'connected',
      resolution: '1920x1080',
    );
    
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CameraCard(camera: camera),
        ),
      ),
    );
    
    expect(find.text('Test Camera'), findsOneWidget);
    expect(find.text('1920x1080'), findsOneWidget);
  });
}
```

### Step 7.2: Integration Tests

**Test Scenarios**:

#### Scenario 1: Single Camera Full Workflow
```bash
# Get auth token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r .access_token)

# 1. Detect cameras
curl -X POST http://localhost:8005/api/v1/cameras/detect -H "Authorization: Bearer $TOKEN"

# 2. Connect camera
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/connect -H "Authorization: Bearer $TOKEN"

# 3. Start streaming (open in browser)
open "http://localhost:8005/api/v1/streaming/usb_camera_0/video?token=$TOKEN"

# 4. Start recording
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/recording/start -H "Authorization: Bearer $TOKEN"

# 5. Wait 10 seconds
sleep 10

# 6. Check recording status
curl http://localhost:8005/api/v1/cameras/usb_camera_0/recording/status -H "Authorization: Bearer $TOKEN"

# 7. Stop recording
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/recording/stop -H "Authorization: Bearer $TOKEN"

# 8. Verify video file exists
ls -lh ppl-meta-cameras/recordings/

# 9. Disconnect camera
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/disconnect -H "Authorization: Bearer $TOKEN"
```

**Success Criteria**:
- [ ] All steps complete without errors
- [ ] Video file created and playable
- [ ] Stream displays in browser
- [ ] Recording duration matches sleep time
- [ ] Camera disconnects cleanly

#### Scenario 2: Multiple Cameras Simultaneously
```bash
# Get auth token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r .access_token)

# Connect both USB and RTSP
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/connect -H "Authorization: Bearer $TOKEN" &
curl -X POST http://localhost:8005/api/v1/cameras/rtsp_192.168.1.76_554/connect -H "Authorization: Bearer $TOKEN" &
wait

# Start recording on both
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/recording/start -H "Authorization: Bearer $TOKEN" &
curl -X POST http://localhost:8005/api/v1/cameras/rtsp_192.168.1.76_554/recording/start -H "Authorization: Bearer $TOKEN" &
wait

# Stream both (open 2 browser tabs)
open "http://localhost:8005/api/v1/streaming/usb_camera_0/video?token=$TOKEN"
open "http://localhost:8005/api/v1/streaming/rtsp_192.168.1.76_554/video?token=$TOKEN"

# Wait
sleep 15

# Stop both
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/recording/stop -H "Authorization: Bearer $TOKEN" &
curl -X POST http://localhost:8005/api/v1/cameras/rtsp_192.168.1.76_554/recording/stop -H "Authorization: Bearer $TOKEN" &
wait

# Check videos
ls -lh ppl-meta-cameras/recordings/
```

**Success Criteria**:
- [ ] Both cameras connect simultaneously
- [ ] Both cameras stream without interference
- [ ] Both recordings complete successfully
- [ ] No blocking between operations
- [ ] CPU usage stays reasonable (<80% total)

#### Scenario 3: Frontend End-to-End
1. Open Flutter app on web/desktop
2. Navigate to Cameras screen
3. Verify 3 cameras displayed
4. Tap "Detect Cameras" - verify refresh
5. Tap play button on USB camera - verify stream displays
6. Tap record button - verify red dot appears
7. Wait 10 seconds - verify timer updates
8. Tap stop button - verify recording stops
9. Check backend recordings folder - verify video exists
10. Play video in VLC - verify playback works

**Success Criteria**:
- [ ] All UI interactions work smoothly
- [ ] No crashes or errors
- [ ] Visual feedback for all actions
- [ ] Recording duration accurate
- [ ] Video quality acceptable

### Step 7.3: Performance Tests

**Load Test** (`test_performance.py`):
```python
import asyncio
import httpx
import time
from concurrent.futures import ThreadPoolExecutor

async def stream_camera(device_id: str, token: str, duration: int):
    """Stream from camera for specified duration."""
    async with httpx.AsyncClient() as client:
        start = time.time()
        frame_count = 0
        
        async with client.stream(
            "GET",
            f"http://localhost:8005/api/v1/streaming/{device_id}/video",
            headers={"Authorization": f"Bearer {token}"},
            timeout=None
        ) as stream:
            async for chunk in stream.aiter_bytes():
                if b'--frame' in chunk:
                    frame_count += 1
                
                if time.time() - start > duration:
                    break
        
        elapsed = time.time() - start
        fps = frame_count / elapsed
        return device_id, frame_count, fps

async def test_multiple_streams():
    """Test streaming from multiple cameras simultaneously."""
    # Get token
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8005/api/v1/users/login", json={
            "username": "admin",
            "password": "admin"
        })
        token = resp.json()["access_token"]
    
    # Stream from 3 cameras for 30 seconds each
    devices = ["usb_camera_0", "rtsp_192.168.1.76_554", "mobile_camera_TKQ1"]
    
    results = await asyncio.gather(*[
        stream_camera(device, token, 30) for device in devices
    ])
    
    print("\n📊 Performance Results:")
    for device_id, frames, fps in results:
        print(f"  {device_id}: {frames} frames @ {fps:.1f} FPS")

if __name__ == "__main__":
    asyncio.run(test_multiple_streams())
```

**Run Test**:
```bash
cd ppl-meta-cameras
python test_performance.py
```

**Success Criteria**:
- [ ] All cameras stream at ~30 FPS
- [ ] Total CPU usage < 80%
- [ ] Memory usage stable (no leaks)
- [ ] No frame drops or freezes
- [ ] Network bandwidth acceptable

---

## Phase 8: Documentation & Cleanup

### Step 8.1: API Documentation

**Create**: `docs/api/CAMERA_API.md`

Document all endpoints:
- `POST /api/v1/cameras/detect`
- `POST /api/v1/cameras/{device_id}/connect`
- `POST /api/v1/cameras/{device_id}/disconnect`
- `POST /api/v1/cameras/{device_id}/recording/start`
- `POST /api/v1/cameras/{device_id}/recording/stop`
- `GET /api/v1/cameras/{device_id}/recording/status`
- `GET /api/v1/streaming/{device_id}/video`

### Step 8.2: User Guide

**Create**: `docs/guides/CAMERA_USER_GUIDE.md`

Include:
- How to detect cameras
- How to start/stop recording
- How to view live streams
- Troubleshooting common issues
- Understanding camera status indicators

### Step 8.3: Code Cleanup

**Checklist**:
- [ ] Remove commented-out code
- [ ] Add docstrings to all public methods
- [ ] Add type hints to Python functions
- [ ] Format code (black, isort for Python; dartfmt for Flutter)
- [ ] Update README files
- [ ] Add inline comments for complex logic

---

## Success Criteria Summary

### Backend
- ✅ CameraWorker threads running for all connected cameras
- ✅ Non-blocking API (connect, disconnect, recording)
- ✅ MJPEG streaming working
- ✅ Recording saves video files
- ✅ Multiple cameras operate independently
- ✅ Proper error handling and logging

### Frontend
- ✅ Cameras display in cards
- ✅ Recording button starts/stops recording
- ✅ Recording indicator shows red dot + timer
- ✅ Play button opens stream viewer
- ✅ Stream displays live video
- ✅ No UI freezes or crashes
- ✅ Proper loading/error states

### Integration
- ✅ End-to-end workflow works (detect → connect → stream → record → stop)
- ✅ Multiple cameras work simultaneously
- ✅ Instant detection still functional (samples from worker buffers)
- ✅ MVR pipeline processes recorded videos
- ✅ Service restarts gracefully

### Performance
- ✅ Streaming at ~30 FPS per camera
- ✅ CPU usage < 80% with 3 cameras
- ✅ Memory usage stable (no leaks)
- ✅ Recording video quality acceptable
- ✅ No blocking between operations

---

## Timeline Estimate

**Week 1: Backend Implementation**
- Day 1-2: Recording service + endpoints (Phase 2)
- Day 3: Streaming endpoint optimization (Phase 3)
- Day 4-5: Testing + bug fixes

**Week 2: Frontend Implementation**
- Day 1-2: WebSocket lifecycle integration (Phase 4)
- Day 3: Recording controls integration (Phase 5)
- Day 4: Streaming player integration (Phase 6)
- Day 5: Testing + polish

**Week 3: Testing & Documentation**
- Day 1-3: Integration testing (all scenarios) (Phase 7)
- Day 4: Performance testing + optimization
- Day 5: Documentation + cleanup (Phase 8)

**Total: ~3 weeks for complete implementation**

**Note**: Phase 4 (Camera Lifecycle) is critical and must be completed before Phases 5-6. All cameras must support connect/disconnect workflow with real-time WebSocket status before recording/streaming features.

---

## Rollback Plan

If issues arise during implementation:

```bash
# Backend rollback
cd ppl-meta-cameras
git checkout HEAD~1 src/services/camera_service_queue.py
git checkout HEAD~1 src/api/v1/endpoints/cameras.py

# Frontend rollback
cd ppl-meta-frontend
git checkout HEAD~1 lib/core/services/camera_service.dart
git checkout HEAD~1 lib/core/providers/camera_providers.dart
git checkout HEAD~1 lib/presentation/widgets/camera/camera_card.dart

# Restart services
pkill -f 'ppl-meta-cameras'
cd ppl-meta-cameras && source venv/bin/activate && python src/main.py
```

---

## Next Steps

1. **Review this document** with team/stakeholders
2. **Validate current state** - run detection and verify 3 cameras display
3. **Begin Phase 2** - Implement recording endpoints
4. **Test incrementally** - Don't wait until end to test
5. **Document as you go** - Update this guide with any changes

**Remember**: Queue architecture is about making camera operations non-blocking. The user-facing functionality (recording, streaming) remains conceptually the same, just implemented to use worker threads instead of direct OpenCV access.

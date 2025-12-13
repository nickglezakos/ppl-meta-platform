# PPL Meta Camera Screen and Cards - Technical Reference

**Document Purpose**: Reference guide for all camera-related functionality, widgets, and code architecture in the PPL Meta frontend.

**Last Updated**: December 13, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Main Camera Page](#main-camera-page)
3. [Camera Cards](#camera-cards)
4. [Key Widgets](#key-widgets)
5. [State Management](#state-management)
6. [Services Layer](#services-layer)
7. [Critical Configuration](#critical-configuration)
8. [File Reference Map](#file-reference-map)

---

## Overview

The PPL Meta camera system consists of multiple layers working together:
- **UI Layer**: Camera page and card widgets
- **Widget Layer**: Specialized widgets for instant detection and MVR counting
- **State Layer**: Riverpod providers for camera recording state
- **Service Layer**: Camera service for API communication
- **Backend**: Camera service (port 8005) handling streams and recording

---

## Main Camera Page

### Enhanced Multi-Camera Page
**File**: `lib/pages/enhanced_multi_camera_page.dart` (875 lines)

**Purpose**: Main page displaying grid of camera cards with streaming and recording controls.

**Key Features**:
- Displays 3 cameras in a responsive grid layout
- Auto-detects and connects cameras on page load
- Handles camera lifecycle (connect, disconnect, stream)
- Integrates with collection management

**Route**: `/cameras`

**Key Code Sections**:
```dart
// Line 254: Camera grid rendering
Widget _buildCameraGrid(BuildContext context) {
  return GridView.builder(
    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
      crossAxisCount: 3,
      childAspectRatio: 16 / 9,
    ),
    itemCount: cameras.length,
    itemBuilder: (context, index) {
      return EnhancedCameraCard(
        camera: cameras[index],
        collection: collections[cameras[index].id],
      );
    },
  );
}
```

**State Management**:
- Uses `camerasProvider` for camera list
- Uses `cameraCollectionsProvider` for collection mappings
- Manages connection state per camera

---

## Camera Cards

### 1. EnhancedCameraCard
**File**: `lib/widgets/enhanced_camera_card.dart` (578 lines)

**Purpose**: Main camera card widget with recording controls and session management.

**Features**:
- Video streaming display
- Recording controls (Start/Stop)
- Session information display
- Error handling and loading states
- Collection integration

**Key Components**:
```dart
// Recording Controls Section (lines 400-500)
- Start Recording Button
- Stop Recording Button  
- Session UUID Display
- Recording Status Indicator
- Error Messages

// Video Stream Section
- SimpleStreamingPlayer widget
- Stream connection management
- Loading states
```

**Does NOT Include**:
- Instant detection widget (handled separately)
- MVR counter (handled separately)

---

### 2. CameraCard
**File**: `lib/widgets/camera/camera_card.dart`

**Purpose**: Alternative camera card that includes instant detection widget.

**Key Feature - Instant Detection Integration**:
```dart
// Instant Detection Widget Instantiation
InstantDetectionWidget(
  cameraId: widget.camera.deviceId,
  refreshInterval: const Duration(seconds: 5),  // FIXED: Was 3 seconds
),
```

**Critical Fix Applied** (Dec 13, 2025):
- Changed hardcoded `refreshInterval` from 3 seconds to 5 seconds
- This was causing instant detection to poll faster than intended
- Now matches the widget's default polling interval

---

## Key Widgets

### 1. Instant Detection Widget
**File**: `lib/widgets/camera/instant_detection_widget.dart` (431 lines)

**Purpose**: Real-time face detection display showing current people count and demographics.

**Polling Configuration**:
```dart
// Line 22: Default refresh interval
final Duration refreshInterval;

// Constructor (line 18-23)
const InstantDetectionWidget({
  Key? key,
  required this.cameraId,
  this.refreshInterval = const Duration(seconds: 5),  // Default: 5 seconds
}) : super(key: key);
```

**Polling Mechanism**:
```dart
// Lines 68-79: Auto-refresh timer
void _startAutoRefresh() {
  print('🔍 [INSTANT_DETECTION_WIDGET] _startAutoRefresh called');
  print('🔍 [INSTANT_DETECTION_WIDGET] Using refresh interval: ${widget.refreshInterval.inSeconds} seconds');
  
  _refreshTimer?.cancel();
  _refreshTimer = Timer.periodic(widget.refreshInterval, (timer) {
    print('🔍 [INSTANT_DETECTION_WIDGET] Periodic fetch tick (${widget.refreshInterval.inSeconds}s interval)');
    _fetchInstantDetection();
  });
}
```

**Display Information**:
- Current people count in view
- Male/Female/Unknown gender breakdown
- Young/Adult/Unknown age breakdown
- Percentage distributions
- Real-time updates every 5 seconds

**API Endpoint Used**:
```
GET /api/v1/detection/instant/{cameraId}
```

**State Management**:
- Local state for detection results
- Auto-refresh timer management
- Error handling for API failures

**Critical Features**:
- Two-tier polling: Fast poll (5s) + Lazy check (10s)
- Automatic cleanup on widget disposal
- Debug logging for troubleshooting

---

### 2. MVR People Counter Widget
**File**: `lib/widgets/camera/mvr_counter_widget.dart` (approximate)

**Purpose**: Displays unique MVR (Machine Vision Recognition) people count for a camera.

**Features**:
- Shows total unique people detected across all videos
- Time filter options (today, week, month, all time)
- Video count display
- Cache status indicator
- Auto-refresh capability

**Display Format**:
```
👥 14 People
📹 10 Videos
(cached: true)
```

**API Endpoint Used**:
```
GET /api/v1/mvr/count/{cameraId}?time_filter=today
```

**Refresh Behavior**:
- Auto-refreshes on page load
- Manual refresh available
- Shows cached vs fresh data status

**Time Filter Options**:
- `today`: Videos from today only
- `week`: Last 7 days
- `month`: Last 30 days
- `all`: All time

---

## State Management

### CameraRecordingNotifier
**File**: `lib/core/providers/camera_providers.dart` (800 lines)

**Purpose**: Riverpod state notifier for managing camera recording lifecycle.

**State Model**:
```dart
class CameraRecordingState {
  final bool isRecording;
  final bool isLoading;
  final String? error;
  final String? sessionUuid;
  final DateTime? startedAt;
}
```

**Key Methods**:

#### Start Recording
```dart
// Lines 650-680: startRecording method
Future<void> startRecording(String deviceId) async {
  print('📹 [CAMERA_RECORDING_NOTIFIER] startRecording called for camera: $deviceId');
  print('📹 [CAMERA_RECORDING_NOTIFIER] Current state - isRecording: ${state.isRecording}, isLoading: ${state.isLoading}');
  
  // Clear stale state
  await _clearStaleRecordingState(deviceId);
  
  // Call camera service
  final result = await _cameraService.startRecording(deviceId, enableInstantDetection: true);
  
  // Update state
  if (result.isSuccess) {
    state = CameraRecordingState(
      isRecording: true,
      isLoading: false,
      sessionUuid: result.recordingId,
      startedAt: result.startedAt,
    );
  }
}
```

#### Stop Recording
```dart
// Lines 698-727: stopRecording method
Future<void> stopRecording(String deviceId) async {
  print('📹 [CAMERA_RECORDING_NOTIFIER] stopRecording called for camera: $deviceId');
  print('📹 [CAMERA_RECORDING_NOTIFIER] Current state - isRecording: ${state.isRecording}, isLoading: ${state.isLoading}');
  
  state = state.copyWith(isLoading: true);
  
  // Call camera service with autoStopInstantDetection=false to keep stream alive
  final result = await _cameraService.stopRecording(deviceId, autoStopInstantDetection: false);
  
  // Update state based on result
  if (result.isSuccess) {
    print('📹 [CAMERA_RECORDING_NOTIFIER] ✅ Success! Updating state to isRecording=false');
    state = CameraRecordingState(
      isRecording: false,
      isLoading: false,
    );
  } else {
    print('📹 [CAMERA_RECORDING_NOTIFIER] ❌ Service returned failure');
    state = state.copyWith(
      isLoading: false,
      error: result.message,
    );
  }
}
```

**Critical Parameter**:
- `autoStopInstantDetection: false` - Keeps camera stream and instant detection active after recording stops

---

## Services Layer

### CameraService
**File**: `lib/core/services/camera_service.dart` (890 lines)

**Purpose**: API service layer for all camera operations.

**Configuration**:
```dart
// Lines 49-52: Timeout configuration (CRITICAL)
_directCameraClient = Dio(BaseOptions(
  baseUrl: AppConfig.instance.cameraServiceUrl,
  connectTimeout: const Duration(seconds: 60),   // For connection establishment
  receiveTimeout: const Duration(seconds: 120),  // For stop recording (video finalization)
  sendTimeout: const Duration(seconds: 30),
));
```

**Why 120 seconds?**
- Backend needs 30-60 seconds to finalize video segments
- Schedule background upload tasks
- Process face detection results
- Original 30s timeout was causing premature failures

---

### Key Methods

#### Start Recording
```dart
// Lines 630-670: startRecording method
Future<RecordingResult> startRecording(
  String deviceId, 
  {bool enableInstantDetection = true}
) async {
  print('🔥 DEBUG CORE: startRecording called for deviceId: $deviceId');
  print('🔥 DEBUG CORE: enableInstantDetection: $enableInstantDetection');
  
  final response = await _cameraApiClient.post(
    '/api/v1/streaming/$deviceId/record/start',
    queryParameters: {
      'enable_instant_detection': enableInstantDetection,
    },
  );
  
  return RecordingResult.fromJson({
    'session_id': response.data['recording_id'] ?? response.data['session_uuid'],
    'device_id': deviceId,
    'status': 'success',
    'message': response.data['message'] ?? 'Recording started successfully',
  });
}
```

**Backend Endpoint**: `POST /api/v1/streaming/{deviceId}/record/start`

---

#### Stop Recording
```dart
// Lines 680-705: stopRecording method
Future<RecordingResult> stopRecording(
  String deviceId, 
  {bool autoStopInstantDetection = false}
) async {
  print('🛑 DEBUG CORE: stopRecording called for deviceId: $deviceId');
  print('🛑 DEBUG CORE: autoStopInstantDetection: $autoStopInstantDetection');
  
  final response = await _cameraApiClient.post(
    '/api/v1/streaming/$deviceId/record/stop',
    queryParameters: {
      'auto_stop_instant_detection': autoStopInstantDetection,
    },
  );
  
  // CRITICAL FIX: status must be 'success' not 'stopped'
  return RecordingResult.fromJson({
    'session_id': response.data['recording_id'] ?? response.data['session_uuid'],
    'device_id': deviceId,
    'status': 'success',  // ✅ FIXED: Was 'stopped', causing isSuccess to return false
    'message': response.data['message'] ?? 'Recording stopped successfully',
  });
}
```

**Backend Endpoint**: `POST /api/v1/streaming/{deviceId}/record/stop`

**Critical Fix** (Dec 13, 2025):
- Changed `status: 'stopped'` to `status: 'success'`
- RecordingResult.isSuccess checks `status == 'success'`
- Previous value caused button to stay in "Stop Recording" state

---

#### RecordingResult Model
```dart
// Lines 810-857: RecordingResult class
class RecordingResult {
  final String status;
  final String message;
  final String deviceId;
  final String? recordingId;
  final DateTime? startedAt;
  final DateTime? stoppedAt;
  
  // CRITICAL: Success check
  bool get isSuccess => status == 'success';  // Line 856
}
```

---

## Critical Configuration

### API Timeouts
**File**: `lib/core/api/api_client.dart`

```dart
// Lines 13-14: Global API timeouts
connectTimeout: const Duration(seconds: 60),   // Connection timeout
receiveTimeout: const Duration(seconds: 120),  // Response timeout
```

**Applied to**:
- Camera service operations
- Recording start/stop operations
- All gateway API calls

---

### Polling Intervals

#### Instant Detection Widget
```dart
refreshInterval: Duration(seconds: 5)  // Default polling frequency
```

**Where Used**:
1. `instant_detection_widget.dart` line 22 - Default parameter
2. `camera_card.dart` - Widget instantiation (FIXED: was 3s, now 5s)

#### MVR Counter
```dart
// Auto-refresh interval (if implemented)
Duration(minutes: 5)  // Typical refresh rate
```

---

### Stream Configuration

**Stream URL Format**:
```dart
http://localhost:8005/api/v1/streaming/{deviceId}/video?token={auth_token}
```

**Authentication**:
- Uses JWT token from AuthService
- Token appended as query parameter
- Auto-refreshes on token expiration

---

## File Reference Map

### Frontend Structure
```
ppl-meta-frontend/
├── lib/
│   ├── pages/
│   │   └── enhanced_multi_camera_page.dart        # Main camera page (875 lines)
│   │
│   ├── widgets/
│   │   ├── enhanced_camera_card.dart              # Camera card with recording (578 lines)
│   │   └── camera/
│   │       ├── camera_card.dart                   # Alternative card with instant detection
│   │       ├── instant_detection_widget.dart      # Real-time face detection (431 lines)
│   │       ├── mvr_counter_widget.dart            # MVR people counter
│   │       └── simple_streaming_player.dart       # Video stream display
│   │
│   ├── core/
│   │   ├── providers/
│   │   │   └── camera_providers.dart              # State management (800 lines)
│   │   │
│   │   ├── services/
│   │   │   └── camera_service.dart                # API service layer (890 lines)
│   │   │
│   │   └── api/
│   │       └── api_client.dart                    # HTTP client config (151 lines)
│   │
│   └── models/
│       └── camera.dart                            # Camera data models
```

### Backend Structure
```
ppl-meta-cameras/
└── src/
    ├── api/v1/endpoints/
    │   ├── streaming.py                           # Recording endpoints (572 lines)
    │   └── detection.py                           # Instant detection endpoints
    │
    └── services/
        └── camera_detection.py                    # Camera detection logic (2905 lines)
```

---

## Camera Function Flow

### Complete Recording Workflow

```
1. User Opens /cameras Page
   ↓
2. enhanced_multi_camera_page.dart loads
   ↓
3. Auto-detects cameras via CameraService.detectCameras()
   ↓
4. Creates EnhancedCameraCard for each camera
   ↓
5. User clicks "Connect" on a camera card
   ↓
6. Camera connects and starts streaming
   ↓
7. SimpleStreamingPlayer displays video feed
   ↓
8. InstantDetectionWidget starts polling (5s intervals)
   ↓
9. MVR counter displays total people count
   ↓
10. User clicks "Start Recording"
    ↓
11. CameraRecordingNotifier.startRecording()
    ↓
12. CameraService.startRecording(enableInstantDetection=true)
    ↓
13. Backend starts 30-second video segments
    ↓
14. Button changes to "Stop Recording"
    ↓
15. Instant detection continues during recording
    ↓
16. User clicks "Stop Recording"
    ↓
17. CameraRecordingNotifier.stopRecording()
    ↓
18. CameraService.stopRecording(autoStopInstantDetection=false)
    ↓
19. Backend finalizes video (30-60 seconds)
    ↓
20. Response received within 120s timeout
    ↓
21. RecordingResult with status='success'
    ↓
22. Button resets to "Start Recording" ✅
    ↓
23. Instant detection continues (stream stays alive) ✅
```

---

## Common Issues & Fixes

### Issue 1: Button Not Resetting After Stop Recording
**Symptom**: Stop recording button stays in "Stop Recording" state, cannot start new recording.

**Root Cause**: RecordingResult status was set to `'stopped'` instead of `'success'`.

**Fix Applied** (Dec 13, 2025):
```dart
// File: lib/core/services/camera_service.dart, line 698
// OLD:
'status': 'stopped',

// NEW:
'status': 'success',
```

**Why**: The `isSuccess` getter checks `status == 'success'`, so any other value returns false.

---

### Issue 2: Instant Detection Polling at 3 Seconds
**Symptom**: Logs showed "Configured refresh interval: 3 seconds" despite widget default being 5 seconds.

**Root Cause**: `camera_card.dart` was explicitly passing `refreshInterval: const Duration(seconds: 3)`.

**Fix Applied** (Dec 13, 2025):
```dart
// File: lib/widgets/camera/camera_card.dart
// OLD:
InstantDetectionWidget(
  cameraId: widget.camera.deviceId,
  refreshInterval: const Duration(seconds: 3),  // ❌ Hardcoded override
),

// NEW:
InstantDetectionWidget(
  cameraId: widget.camera.deviceId,
  refreshInterval: const Duration(seconds: 5),  // ✅ Matches default
),
```

**Why**: Explicit parameter overrides widget default, needed to be consistent.

---

### Issue 3: Stop Recording Timeout
**Symptom**: Stop recording fails with "Connection timeout" after 30 seconds.

**Root Cause**: Backend needs 30-60 seconds to finalize video, but timeout was only 30 seconds.

**Fix Applied** (Earlier):
```dart
// File: lib/core/api/api_client.dart, lines 13-14
// OLD:
connectTimeout: const Duration(seconds: 30),
receiveTimeout: const Duration(seconds: 30),

// NEW:
connectTimeout: const Duration(seconds: 60),
receiveTimeout: const Duration(seconds: 120),
```

**Why**: Backend video finalization requires more time than default timeout allowed.

---

### Issue 4: Stream Freezing After Stop Recording
**Symptom**: Camera stream freezes when recording stops, instant detection stops working.

**Root Cause**: Backend was disconnecting camera from active_connections on recording stop.

**Fix Applied** (Earlier):
- Removed camera disconnect code from `camera_detection.py` lines 1208-1227
- Added `autoStopInstantDetection=false` parameter to keep camera connected
- Stream and instant detection now persist after recording stops

---

## Debug Logging

### Frontend Debug Logs

**Instant Detection Widget**:
```dart
🔍 [INSTANT_DETECTION_WIDGET] initState called for device: usb_camera_0
🔍 [INSTANT_DETECTION_WIDGET] Configured refresh interval: 5 seconds
🔍 [INSTANT_DETECTION_WIDGET] _startAutoRefresh called
🔍 [INSTANT_DETECTION_WIDGET] Using refresh interval: 5 seconds
🔍 [INSTANT_DETECTION_WIDGET] Periodic fetch tick (5s interval)
🔍 Instant detection response: people=1, demographics={...}
```

**Recording State**:
```dart
📹 [CAMERA_RECORDING_NOTIFIER] startRecording called for camera: usb_camera_0
📹 [CAMERA_RECORDING_NOTIFIER] Current state - isRecording: false, isLoading: false
🔥 DEBUG CORE: startRecording called for deviceId: usb_camera_0
🔥 DEBUG CORE: enableInstantDetection: true
✅ DEBUG CORE: startRecording response: 200

📹 [CAMERA_RECORDING_NOTIFIER] stopRecording called for camera: usb_camera_0
🛑 DEBUG CORE: stopRecording called for deviceId: usb_camera_0
🛑 DEBUG CORE: autoStopInstantDetection: false
✅ DEBUG CORE: stopRecording response: 200
📹 [CAMERA_RECORDING_NOTIFIER] ✅ Success! Updating state to isRecording=false
```

**MVR Counter**:
```dart
📡 Fetching MVR count for camera: usb_camera_0 (timeFilter: today, forceRefresh: false)
✅ Got MVR count: 14 people (cached: true)
   ✅ Counter updated: 14 people (10 videos, cached: true)
```

---

## Widget Instantiation Patterns

### Pattern 1: Using Default Polling
```dart
// Widget automatically uses 5-second polling
InstantDetectionWidget(
  cameraId: camera.deviceId,
  // refreshInterval defaults to 5 seconds
)
```

### Pattern 2: Custom Polling Interval
```dart
// Explicitly set polling interval
InstantDetectionWidget(
  cameraId: camera.deviceId,
  refreshInterval: const Duration(seconds: 10),  // Custom interval
)
```

### Pattern 3: MVR Counter with Time Filter
```dart
MvrCounterWidget(
  cameraId: camera.deviceId,
  timeFilter: TimeFilter.today,  // Options: today, week, month, all
  autoRefresh: true,
)
```

---

## API Endpoints Reference

### Camera Detection
- **GET** `/api/v1/cameras/detect` - Detect available cameras
- **POST** `/api/v1/cameras/connect/{deviceId}` - Connect to camera
- **POST** `/api/v1/cameras/disconnect/{deviceId}` - Disconnect camera

### Streaming
- **GET** `/api/v1/streaming/{deviceId}/video?token={jwt}` - Video stream
- **POST** `/api/v1/streaming/{deviceId}/start` - Start streaming
- **POST** `/api/v1/streaming/{deviceId}/stop` - Stop streaming

### Recording
- **POST** `/api/v1/streaming/{deviceId}/record/start?enable_instant_detection=true` - Start recording
- **POST** `/api/v1/streaming/{deviceId}/record/stop?auto_stop_instant_detection=false` - Stop recording
- **GET** `/api/v1/streaming/{deviceId}/record/status` - Recording status

### Detection
- **GET** `/api/v1/detection/instant/{cameraId}` - Instant detection results
- **GET** `/api/v1/mvr/count/{cameraId}?time_filter=today` - MVR people count

---

## Configuration Constants

### Video Recording Settings
```python
# Backend: ppl-meta-cameras/src/config/settings.py
SEGMENT_DURATION = 30  # seconds
VIDEO_RESOLUTION = "1920x1080"
VIDEO_FPS = 30
VIDEO_CODEC = "h264"
VIDEO_FORMAT = "mp4"
```

### Instant Detection Settings
```dart
// Frontend polling intervals
INSTANT_DETECTION_INTERVAL = 5 seconds
LAZY_CHECK_INTERVAL = 10 seconds  // Fallback check

// Backend detection settings
MIN_FACE_SIZE = (30, 30)  // pixels
DETECTION_MODEL = "retinaface"
ATTRIBUTES = ["age", "gender"]
```

### MVR Settings
```python
# Cross-video tracking
SIMILARITY_THRESHOLD = 0.6
MIN_FACES_FOR_MVR = 3
CACHE_DURATION = 3600  # seconds (1 hour)
```

---

## Future Reference Checklist

When modifying camera functionality, check:

- [ ] Timeout values sufficient for backend operations?
- [ ] Polling intervals consistent across all instantiations?
- [ ] Status values match expected checks (e.g., 'success' for isSuccess)?
- [ ] Camera stream persists when needed (autoStopInstantDetection=false)?
- [ ] Debug logging added for troubleshooting?
- [ ] State management updates trigger UI refresh?
- [ ] Error handling covers all failure scenarios?
- [ ] Memory cleanup on widget disposal?

---

## Related Documentation

- [RECORDING_BUTTON_STATE_DEBUG.md](../troubleshooting/RECORDING_BUTTON_STATE_DEBUG.md) - Detailed debugging guide for recording state issues
- [camera-workflow-test.md](../troubleshooting/camera-workflow-test.md) - Camera workflow testing procedures
- Backend API Documentation (if available)
- Flutter Riverpod Documentation: https://riverpod.dev

---

## Maintenance Notes

**Last Major Fixes**:
- **Dec 13, 2025**: Fixed stop recording button reset issue (status 'stopped' → 'success')
- **Dec 13, 2025**: Fixed instant detection hardcoded 3s polling in camera_card.dart
- **Previous**: Increased API timeouts to 60s/120s for recording operations
- **Previous**: Removed backend camera disconnect on recording stop

**Next Steps**:
- Consider removing debug logging after stability confirmation
- Evaluate if instant detection polling should be configurable by user
- Document MVR counter widget in more detail when implementation stabilizes
- Add automated tests for recording state transitions

---

**Document End**

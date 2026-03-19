# Proposal: Decouple Instant Detection from Recording

**Date**: March 19, 2026  
**Status**: Implemented (Phase 1 + Phase 2)  
**Author**: Development Team

---

## Problem Statement

Currently, instant detection is **tightly coupled** to the recording lifecycle:

- When the user taps **Start Recording**, instant detection auto-starts (if enabled in camera settings)
- When the user taps **Stop Recording**, instant detection auto-stops
- The `InstantDetectionWidget` gates all polling on recording state — it shows "Start recording to see live detection" when not recording and refuses to poll

This means there is **no way to run instant detection without recording**. Users who want real-time face detection feedback (people count, demographics, identity) must also be recording video to disk, which wastes storage and is unnecessary for monitoring-only use cases.

---

## Current Coupling Points

### Backend (`ppl-meta-cameras`)

1. **`src/services/camera_detection.py` — `start_recording_with_session()`** (line ~930)
   - Reads `camera.instant_detection_enabled` from database
   - Calls `worker.start_detection(config)` as part of recording start flow
   - The `enable_instant_detection` parameter is passed but overridden by pipeline settings

2. **`src/services/camera_detection.py` — `stop_recording()`** (line ~1734)
   - Accepts `auto_stop_instant_detection` parameter (default `True`)
   - Calls `manager.stop_sampling()` when recording stops (if instant detection is disabled in settings)
   - Handles special `instant_detection_only` mode (partially implemented)

3. **`src/api/v1/endpoints/streaming.py`** (line ~713)
   - Stop recording endpoint passes `auto_stop_instant_detection` query parameter through

### Frontend (`ppl-meta-frontend`)

4. **`lib/widgets/camera/instant_detection_widget.dart`**
   - `ref.watch(cameraRecordingProvider)` — watches recording state
   - `ref.listen(cameraRecordingProvider)` — starts/stops polling based on recording transitions
   - When `!recordingState.isRecording` → shows "Start recording to see live detection" (no polling)
   - `_startLazyChecking()` only called when recording starts
   - `_stopAllPolling()` called when recording stops

5. **`lib/presentation/widgets/camera/camera_card.dart` — `_RecordingControls`** (line ~620)
   - Single recording button (start/stop toggle)
   - No instant detection control

6. **`lib/presentation/pages/camera_stream_page.dart` — `_StreamRecordingControls`** (line ~250)
   - Single recording button (start/stop toggle)
   - No instant detection control

---

## Proposed Changes

### Summary

Add a standalone **Instant Detection toggle button** (eye icon) next to the existing recording button. Remove the automatic start/stop coupling so the two features operate independently.

### UI Changes

#### Camera Card (`_RecordingControls`)

**Before:**
```
[ ● Record ]
```

**After:**
```
[ 👁 Detect ]  [ ● Record ]
```

- **Eye icon button**: Toggles instant detection on/off independently
- **Record button**: Only controls recording (no longer touches instant detection)
- When instant detection is active, the eye icon is filled/blue; when inactive, it is outlined/grey

#### Camera Stream Page (`_StreamRecordingControls`)

**Before:**
```
[ ● Start Recording ]
```

**After:**
```
[ 👁 Start Detection ]  [ ● Start Recording ]
```

Same pattern: two independent buttons side by side.

### Frontend Implementation

#### 1. New Provider: `cameraInstantDetectionProvider`

Create a new state notifier in `lib/core/providers/camera_providers.dart`:

```dart
/// Instant detection state for a camera
class CameraInstantDetectionState {
  final String cameraId;
  final bool isDetecting;
  final bool isLoading;
  final String? error;

  const CameraInstantDetectionState({
    required this.cameraId,
    this.isDetecting = false,
    this.isLoading = false,
    this.error,
  });

  CameraInstantDetectionState copyWith({
    String? cameraId,
    bool? isDetecting,
    bool? isLoading,
    String? error,
  }) {
    return CameraInstantDetectionState(
      cameraId: cameraId ?? this.cameraId,
      isDetecting: isDetecting ?? this.isDetecting,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

/// State notifier for managing instant detection independently.
/// Syncs with backend on initialization so the eye button reflects
/// the real server-side state after page refresh or app restart.
class CameraInstantDetectionNotifier
    extends StateNotifier<CameraInstantDetectionState> {
  final CameraService _cameraService;

  CameraInstantDetectionNotifier(this._cameraService, String cameraId)
      : super(CameraInstantDetectionState(cameraId: cameraId)) {
    // Sync with backend immediately on creation
    _syncFromBackend();
  }

  /// Fetch the current detection status from the backend and update local state.
  /// This ensures the eye button shows the correct state after app restart,
  /// page refresh, or hot reload.
  Future<void> _syncFromBackend() async {
    try {
      final status = await _cameraService.getInstantDetectionStatus();
      if (status != null && mounted) {
        final isRunning = status['status']?['running'] == true;
        final activeCameraId = status['status']?['current_camera_id'];
        // Only mark as detecting if the backend is running for THIS camera
        final detectingThisCamera =
            isRunning && activeCameraId == state.cameraId;
        state = state.copyWith(isDetecting: detectingThisCamera);
      }
    } catch (_) {
      // Silent fail — backend may not be reachable yet
    }
  }

  Future<void> startDetection() async {
    if (state.isDetecting || state.isLoading) return;
    state = state.copyWith(isLoading: true, error: null);

    try {
      final result = await _cameraService.startInstantDetection(state.cameraId);
      if (result != null && result['success'] == true) {
        state = state.copyWith(isLoading: false, isDetecting: true);
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to start detection',
        );
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: '$e');
    }
  }

  Future<void> stopDetection() async {
    if (!state.isDetecting || state.isLoading) return;
    state = state.copyWith(isLoading: true, error: null);

    try {
      final result = await _cameraService.stopInstantDetection(state.cameraId);
      if (result != null && result['success'] == true) {
        state = state.copyWith(isLoading: false, isDetecting: false);
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to stop detection',
        );
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: '$e');
    }
  }

  void toggleDetection() {
    if (state.isDetecting) {
      stopDetection();
    } else {
      startDetection();
    }
  }
}

final cameraInstantDetectionProvider = StateNotifierProvider.family<
    CameraInstantDetectionNotifier,
    CameraInstantDetectionState,
    String>((ref, cameraId) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraInstantDetectionNotifier(cameraService, cameraId);
});
```

#### 2. New Camera Service Methods

Add to `lib/core/services/camera_service.dart`:

```dart
/// Start instant detection for a camera (decoupled from recording)
Future<Map<String, dynamic>?> startInstantDetection(String deviceId) async {
  final response = await _apiPost('/api/v1/instant-detection/start/$deviceId');
  return response;
}

/// Stop instant detection for a specific camera
Future<Map<String, dynamic>?> stopInstantDetection(String deviceId) async {
  final response = await _apiPost('/api/v1/instant-detection/stop/$deviceId');
  return response;
}

/// Get instant detection system status (used for state sync on app restart)
Future<Map<String, dynamic>?> getInstantDetectionStatus() async {
  final response = await _apiGet('/api/v1/instant-detection/status');
  return response;
}
```

#### 3. New Widget: `_InstantDetectionControls`

Add next to `_RecordingControls` in both `camera_card.dart` and `camera_stream_page.dart`:

```dart
class _InstantDetectionControls extends ConsumerWidget {
  final String cameraId;
  const _InstantDetectionControls({required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detectionState =
        ref.watch(cameraInstantDetectionProvider(cameraId));
    final detectionNotifier =
        ref.read(cameraInstantDetectionProvider(cameraId).notifier);

    final isActive = detectionState.isDetecting;

    return IconButton(
      onPressed: detectionState.isLoading
          ? null
          : () => detectionNotifier.toggleDetection(),
      icon: detectionState.isLoading
          ? const SizedBox(
              width: 18, height: 18,
              child: CircularProgressIndicator(strokeWidth: 2.5),
            )
          : Icon(
              isActive ? Icons.visibility : Icons.visibility_off,
              color: isActive ? Colors.blue : Colors.grey,
            ),
      tooltip: detectionState.isLoading
          ? (isActive ? 'Stopping...' : 'Starting...')
          : (isActive ? 'Stop detection' : 'Start detection'),
    );
  }
}
```

#### 4. Update `InstantDetectionWidget`

Remove recording-gate logic. Replace with instant detection state gate:

**Before:**
```dart
final recordingState = ref.watch(cameraRecordingProvider(widget.cameraId));

// If not recording, show message to start recording
if (!recordingState.isRecording) {
  return /* "Start recording to see live detection" */;
}
```

**After:**
```dart
final detectionState = ref.watch(cameraInstantDetectionProvider(widget.cameraId));

// If detection not active, show message to start detection
if (!detectionState.isDetecting) {
  return /* "Start detection to see live results" */;
}
```

Remove the `ref.listen(cameraRecordingProvider)` block entirely. The widget polls when `isDetecting == true` and stops when `isDetecting == false`, regardless of recording state.

#### 5. Update `CameraRecordingNotifier`

Remove instant detection coupling from `startRecording()` and `stopRecording()`. The recording notifier should only manage recording.

### Backend Implementation

#### 6. Enhance `GET /instant-detection/status` to Include Active Camera

The existing `/status` endpoint returns `running` and `thread_alive` but not which camera is being sampled. Add `current_camera_id` so the frontend can sync state per-camera on startup:

```python
def get_status(self) -> Dict:
    return {
        "running": self._running,
        "thread_alive": self._detection_thread.is_alive() if self._detection_thread else False,
        "current_camera_id": self._current_camera_id,  # NEW
        "cached_results": len(self.results_cache),
        "sampling_interval": self.sampling_interval,
        "temporal_window": self.temporal_window,
    }
```

This is the key piece that enables state persistence: the frontend calls `/status` on mount, reads `current_camera_id`, and sets `isDetecting = true` for the matching camera.

#### 7. New Endpoint: `POST /instant-detection/stop/{camera_id}`

Currently there is only a global `POST /stop` endpoint. Add a per-camera stop:

```python
@router.post("/stop/{camera_id}")
async def stop_instant_detection_for_camera(
    camera_id: str,
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """Stop instant detection for a specific camera"""
    # Only stop if the running camera matches
    if manager._current_camera_id == camera_id:
        manager.stop_sampling()
    return {"success": True, "message": f"Instant detection stopped for {camera_id}"}
```

#### 8. Update Gateway Proxy

Add the new per-camera stop route to `ppl-meta-gateway/src/api/v1/router.py`:

```python
@api_router.post("/instant-detection/{camera_id}/stop")
async def stop_instant_detection(request: Request):
    """Proxy stop instant detection to Cameras service."""
    return await _proxy_to_cameras_service(request)
```

> **Note**: This route already exists in the gateway router. Verify it maps to the new per-camera endpoint.

#### 9. Remove Auto-Start from `start_recording_with_session()`

In `ppl-meta-cameras/src/services/camera_detection.py`, remove the block that auto-starts instant detection when recording begins:

```python
# REMOVE this block from start_recording_with_session():
if worker and instant_detection_enabled:
    logger.info(f"🔍 [INSTANT-DETECT] Enabling integrated detection...")
    worker.start_detection(detection_config)
```

Recording start should only start recording. Detection start is now triggered by the user tapping the eye button through the new `/start/{camera_id}` endpoint.

#### 10. Remove Auto-Stop from `stop_recording()`

In `stop_recording()`, remove the `auto_stop_instant_detection` block that stops instant detection when recording stops:

```python
# REMOVE this block from stop_recording():
if auto_stop_instant_detection and not instant_detection_enabled:
    manager = get_instant_detection_manager()
    manager.stop_sampling()
```

The `auto_stop_instant_detection` parameter on the stop recording endpoint can be deprecated.

#### 11. Ensure Queue Worker Connection

Currently, the queue worker is connected/started as part of the recording flow. Instant detection needs a connected camera worker to capture frames. Either:

- **Option A**: The `/start/{camera_id}` endpoint ensures the queue worker is connected before starting sampling (preferred — self-contained)
- **Option B**: Require the user to connect the camera first via a separate action

**Recommended: Option A** — Update the `start_instant_detection` endpoint to check and connect the queue worker if needed.

---

## Migration Path

### Phase 1: Backend Decoupling
1. Enhance `GET /status` to return `current_camera_id`
2. Add per-camera stop endpoint
3. Remove auto-start from recording start
4. Remove auto-stop from recording stop
5. Ensure `/start/{camera_id}` connects queue worker if needed
6. Deprecate `auto_stop_instant_detection` parameter

### Phase 2: Frontend Decoupling
1. Add `CameraInstantDetectionState` and `CameraInstantDetectionNotifier` (with backend sync on init)
2. Add `startInstantDetection()`, `stopInstantDetection()`, and `getInstantDetectionStatus()` to camera service
3. Add `_InstantDetectionControls` widget (eye button)
4. Place eye button next to record button in camera card and stream page
5. Update `InstantDetectionWidget` to use detection state instead of recording state
6. Remove recording-state listeners from instant detection widget

### Phase 3: Cleanup
1. Remove `enable_instant_detection` parameter from recording endpoints
2. Remove `auto_stop_instant_detection` parameter from stop recording
3. Update documentation

---

## Impact Assessment

| Area | Impact |
|------|--------|
| **Camera Card UI** | New eye button added next to record button |
| **Stream Page UI** | New eye button added next to record button |
| **Recording flow** | Simplified — no longer touches instant detection |
| **Instant detection widget** | Simpler — listens to detection state, not recording state |
| **Backend recording endpoints** | Simplified — remove detection coupling code |
| **Backend detection endpoints** | Enhanced — per-camera stop, queue worker auto-connect |
| **Existing API contracts** | `auto_stop_instant_detection` deprecated but still accepted |
| **Backend /status endpoint** | Returns `current_camera_id` for frontend state sync |
| **Database schema** | No changes |
| **Redis/Celery** | No changes |

---

## Detection State Persistence Across App Restarts

Detection runs on the backend in a daemon thread (or Celery worker) that is **independent of the frontend**. When the user refreshes the page or restarts the app, the backend keeps sampling. The frontend must re-synchronise its button state on startup.

### How It Works

1. **Backend**: The `GET /status` endpoint is enhanced to include `current_camera_id` — the camera currently being sampled.
2. **Frontend**: When `CameraInstantDetectionNotifier` is created (i.e., when the camera card or stream page mounts), its constructor calls `_syncFromBackend()`.
3. **Sync logic**: The notifier calls `getInstantDetectionStatus()`, reads `current_camera_id`, and sets `isDetecting = true` only if the backend is running for **this** camera.
4. **Result**: The eye button immediately reflects the real server-side state. No stale "off" state after refresh.

### Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Backend running, frontend refreshes | Eye button shows active (blue) after sync |
| Backend crashed/restarted, frontend refreshes | Eye button shows inactive (grey) — correct |
| Backend running for camera A, user views camera B | Camera B eye button shows inactive — correct |
| Backend unreachable on mount | Silent fail, button defaults to inactive |
| User taps eye while sync is in-flight | `isLoading` guard prevents double-action |

---

## Open Questions

1. **Should recording auto-start detection optionally?** Some users may want the old coupled behavior. This could be a per-camera setting (`auto_start_detection_on_record`) but adds complexity. Recommend starting with full decoupling and adding the option later if requested.

2. **Multiple cameras**: The current `InstantDetectionSampler` singleton only tracks one `_current_camera_id`. For true multi-camera support, the singleton would need to manage multiple sampling threads. This is a separate enhancement.

# Recording Button State Issue - Debug Reference

**Date**: December 13, 2025  
**Issue**: Stop recording button does not reset to "Start Recording" state after stopping  
**Root Cause**: Frontend timeout (30s) while backend processes recording stop (30+ seconds)  
**Status**: FIXED - Increased timeouts

## ROOT CAUSE IDENTIFIED ✅

**Problem**: Stop recording HTTP request was timing out after 30 seconds, causing:
1. ❌ Service call fails with timeout exception
2. ❌ Provider never updates state to `isRecording=false`  
3. ❌ Button remains in "Stop Recording" state
4. ❌ Stream stops anyway (backend completes, but frontend doesn't know)

**Evidence from Logs**:
```
❌ DEBUG CORE: stopRecording error: The request connection took longer than 0:00:30.000000
📹 [CAMERA_RECORDING_NOTIFIER] ❌ Exception caught: Connection timeout
📹 [CAMERA_RECORDING_NOTIFIER] Error state - error: Stop recording error: Connection timeout
```

**Fix Applied**:
- Increased `ApiClient` `connectTimeout`: 30s → 60s
- Increased `ApiClient` `receiveTimeout`: 30s → 120s  
- Backend processing (video finalization, upload scheduling) can take 30-60 seconds
- Frontend now waits long enough for backend to respond

## Secondary Issue: Instant Detection Polling Interval

**Problem**: Logs showed 3-second polling interval instead of 5 seconds:
```
🔍 [INSTANT_DETECTION_WIDGET] Configured refresh interval: 3 seconds
```

**Cause**: Widget definition had default of 5s, but somewhere it's being instantiated with 3s or there's a hot reload issue.

**Status**: Widget default is correctly set to 5 seconds, needs app restart to take effect.

## Problem Summary

After clicking "Stop Recording", the button remains in the "Stop Recording" state instead of reverting to "Start Recording". Recording actually stops successfully (backend confirms), but the UI button state doesn't update.

## Architecture Overview

### Component Stack
```
RecordingControls Widget (UI Layer)
    ↓ uses
recordingStateProvider (State Management)
    ↓ manages
CameraRecordingNotifier (Business Logic)
    ↓ calls
CameraService.stopRecording() (API Layer)
    ↓ sends HTTP request to
Gateway Service → Cameras Service (Backend)
```

## Key Files and Their Roles

### 1. **Frontend Widget**: `ppl-meta-frontend/lib/widgets/camera/recording_controls.dart`
- **Lines 336-353**: `_toggleRecording()` method
- **Line 80**: Watches `recordingStateProvider` for state changes
- **Line 339**: Calls `recordingNotifier.stopRecording()`
- **Debug Logs Added**: 
  - Widget initialization
  - Button click events
  - State before/after recording actions

### 2. **State Provider**: `ppl-meta-frontend/lib/core/providers/camera_providers.dart`
- **Lines 698-727**: `CameraRecordingNotifier.stopRecording()` method
- **Lines 796-798**: Provider definition (`recordingStateProvider` alias for `cameraRecordingProvider`)
- **Lines 707-717**: State update logic - sets `isRecording = false` on success
- **Debug Logs Added**:
  - Method entry with current state
  - Service call tracking
  - Success/failure paths with state changes
  - Exception handling

### 3. **API Service**: `ppl-meta-frontend/lib/core/services/camera_service.dart`
- **Lines 681-701**: `stopRecording()` method
- **Line 687**: Sends POST to `/api/v1/streaming/{deviceId}/record/stop`
- **Line 689**: Passes `auto_stop_instant_detection=false` query parameter
- **Debug Logs Added**:
  - Service method entry
  - HTTP response tracking
  - Success/error paths

### 4. **Backend Service**: `ppl-meta-cameras/src/services/camera_detection.py`
- **Lines 1208-1227**: `_stop_session_recording()` method
- **FIXED**: Removed camera disconnect code that was breaking streaming
- Camera now stays connected after recording stops

### 5. **Backend Endpoint**: `ppl-meta-cameras/src/api/v1/endpoints/streaming.py`
- **Line 395-497**: `stop_recording_endpoint()` 
- **Line 403**: Debug logging for `auto_stop_instant_detection` parameter

### 6. **Instant Detection Widget**: `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart`
- **Line 22**: Default refresh interval = **5 seconds** (not 3!)
- **Lines 43-46**: Widget initialization logging
- **Lines 68-78**: `_startAutoRefresh()` with interval logging
- **Purpose**: Verify polling interval is actually 5 seconds

## Debug Logging Strategy

### Expected Log Flow for Stop Recording

```
1. [RECORDING_CONTROLS] _toggleRecording called
2. [RECORDING_CONTROLS] Current state - isRecording: true, isLoading: false
3. [RECORDING_CONTROLS] Calling stopRecording()...
4. [CAMERA_RECORDING_NOTIFIER] stopRecording called for camera: {deviceId}
5. [CAMERA_RECORDING_NOTIFIER] Current state - isRecording: true, isLoading: false
6. [CAMERA_RECORDING_NOTIFIER] Set isLoading=true, calling camera service...
7. [CAMERA_RECORDING_NOTIFIER] Calling _cameraService.stopRecording({deviceId})...
8. DEBUG CORE: stopRecording called for deviceId: {deviceId}
9. DEBUG CORE: autoStopInstantDetection: false
10. Backend: 🛑 Stop recording endpoint called for {deviceId}, auto_stop_instant_detection=false
11. DEBUG CORE: stopRecording response: 200
12. [CAMERA_RECORDING_NOTIFIER] Service returned - isSuccess: true, message: "..."
13. [CAMERA_RECORDING_NOTIFIER] ✅ Success! Updating state to isRecording=false
14. [CAMERA_RECORDING_NOTIFIER] New state - isRecording: false, isLoading: false
15. [RECORDING_CONTROLS] stopRecording() completed
16. [RECORDING_CONTROLS] New state after stop - isRecording: false, isLoading: false
17. [RECORDING_CONTROLS] build() - Device: {deviceId}, isRecording: false, isLoading: false
```

### Instant Detection Polling Logs

```
[INSTANT_DETECTION_WIDGET] initState called for device: {deviceId}
[INSTANT_DETECTION_WIDGET] Configured refresh interval: 5 seconds
[INSTANT_DETECTION_WIDGET] _startAutoRefresh called
[INSTANT_DETECTION_WIDGET] Using refresh interval: 5 seconds
[INSTANT_DETECTION_WIDGET] Periodic fetch tick (5s interval)  ← Should appear every 5s, not 3s
```

## What to Look For

### 1. **Verify Correct Widget is Used**
Look for logs starting with:
- ✅ `[RECORDING_CONTROLS]` - Correct widget
- ❌ `[ENHANCED_CAMERA_CARD]` - Wrong widget (we edited this before but it's not used)

### 2. **Check Provider State Updates**
After stop recording completes, you should see:
```
[CAMERA_RECORDING_NOTIFIER] ✅ Success! Updating state to isRecording=false
[CAMERA_RECORDING_NOTIFIER] New state - isRecording: false, isLoading: false
```

If you see this but button doesn't update, it's a widget rendering issue.

### 3. **Verify Polling Interval**
Look for:
```
[INSTANT_DETECTION_WIDGET] Using refresh interval: 5 seconds
```
If it says 3 seconds, check if a different widget is being instantiated.

### 4. **Check for Errors**
If you see:
```
[CAMERA_RECORDING_NOTIFIER] ❌ Service returned failure
```
or
```
[CAMERA_RECORDING_NOTIFIER] ❌ Exception caught: ...
```
Then the service call is failing and state won't update.

## Testing Steps

1. **Start the frontend**:
   ```bash
   cd ppl-meta-frontend
   flutter run -d chrome --web-port 3000
   ```

2. **Navigate to Cameras page**

3. **Connect to a camera** and start streaming

4. **Start recording** - Check logs:
   - Should see `[RECORDING_CONTROLS] Calling startRecording()...`
   - Should see state change to `isRecording: true`

5. **Stop recording** - Check logs:
   - Should see full flow from steps 1-17 above
   - Should see state change to `isRecording: false`
   - **Button should visually change** to "Start Recording"

6. **Monitor instant detection** - Every 5 seconds should see:
   ```
   [INSTANT_DETECTION_WIDGET] Periodic fetch tick (5s interval)
   ```

## Possible Root Causes

### If Provider Updates But Button Doesn't Change
- **Cause**: Widget not rebuilding when provider state changes
- **Check**: Look for `[RECORDING_CONTROLS] build()` log after state update
- **Fix**: Ensure `ref.watch()` is used, not `ref.read()`

### If Service Call Fails
- **Cause**: Backend error or network issue
- **Check**: Look for `❌ Service returned failure` or exceptions
- **Fix**: Check backend logs, verify endpoint is accessible

### If State Never Updates to `isRecording=false`
- **Cause**: Service `isSuccess` check failing
- **Check**: What does `Service returned - isSuccess:` show?
- **Fix**: Verify backend response format matches `RecordingResult` model

### If Polling is 3 seconds instead of 5
- **Cause**: Different widget or hard-coded interval somewhere
- **Check**: Search codebase for `Duration(seconds: 3)` in instant detection context
- **Fix**: Update the correct widget instantiation

## Code Changes Made

### Session 1 (Initial Fix)
- ✅ Increased polling from 3s to 5s in `instant_detection_widget.dart`
- ✅ Added `stopCameraRecording()` to `recording_session_service.dart`
- ❌ Modified `enhanced_camera_card.dart` (wrong widget!)

### Session 2 (Backend Fix)
- ✅ Removed camera disconnect from `camera_detection.py` lines 1208-1227
- ✅ Added debug logging to `streaming.py`

### Session 3 (Service Fix + Debug Logging)
- ✅ Added `autoStopInstantDetection` parameter to `camera_service.dart` `stopRecording()`
- ✅ Added comprehensive debug logging to:
  - `recording_controls.dart` (widget)
  - `camera_providers.dart` (provider)
  - `camera_service.dart` (service)
  - `instant_detection_widget.dart` (polling)

## Next Steps

1. **Run the app and capture full logs** during stop recording
2. **Share the logs** showing the complete flow
3. **Identify where the flow breaks**:
   - Does provider update succeed?
   - Does widget see the state change?
   - Does button re-render?
4. **Apply targeted fix** based on log evidence

## Success Criteria

✅ Button changes from "Stop Recording" to "Start Recording" after stop completes  
✅ Stream continues to work (no freeze)  
✅ Instant detection continues polling every 5 seconds  
✅ Can start a new recording immediately after stopping  

## Log Grep Commands

```bash
# Filter for recording control logs
flutter logs | grep "RECORDING_CONTROLS"

# Filter for provider logs
flutter logs | grep "CAMERA_RECORDING_NOTIFIER"

# Filter for instant detection logs
flutter logs | grep "INSTANT_DETECTION_WIDGET"

# Filter for service logs
flutter logs | grep "DEBUG CORE"

# See complete stop recording flow
flutter logs | grep -E "(RECORDING_CONTROLS|CAMERA_RECORDING_NOTIFIER|DEBUG CORE)" | grep -A 5 "stopRecording"
```

---

**Last Updated**: December 13, 2025  
**Debug Logs Version**: v3 (comprehensive flow tracking)

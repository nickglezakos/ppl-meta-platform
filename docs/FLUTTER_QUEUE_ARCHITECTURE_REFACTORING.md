# Flutter State Management Refactoring for Queue Architecture

## Problem Identified

Flutter's camera state management is not synchronized with the backend's new queue-based worker architecture. When cameras connect via workers, Flutter doesn't know about it because it's checking outdated state sources.

## Current Flutter Architecture

### Main Components

1. **UI Layer**: `/lib/widgets/camera/camera_card.dart`
   - Displays camera cards with connect/disconnect/stream buttons
   - Uses `multi_camera_providers` for actions

2. **State Management**: `/lib/core/providers/multi_camera_providers.dart`
   - `CameraActions` class with methods:
     - `connectCamera(cameraId)` - calls `_cameraService.connectCamera()`
     - `disconnectCamera(cameraId)` - calls `_cameraService.disconnectCamera()`
     - `startStreaming(cameraId)` - calls `connectCamera()` then `_cameraService.startStreaming()`

3. **Service Layer**: `/lib/core/services/camera_service.dart`
   - **MISSING**: No `connectCamera()` method
   - **MISSING**: No `disconnectCamera()` method  
   - Has: `startStreaming()`, `stopStreaming()`, `getStreamingStatus()`

4. **Screen**: `/lib/presentation/screens/cameras/cameras_screen.dart`
   - Lists cameras using `cameraListProvider`
   - Shows camera cards

## Issues Causing Erratic Behavior

### Issue 1: Non-existent Methods
```dart
// multi_camera_providers.dart line 168
final success = await _cameraService.connectCamera(camera.deviceId);
```
**Problem**: `camera_service.dart` has NO `connectCamera()` method!

**Result**: 
- Flutter throws error or does nothing
- Backend worker connects (because you tapped button which may call backend directly)
- Flutter never updates UI because it doesn't know about connection

### Issue 2: Status Polling vs Real-time State

Flutter checks status by:
1. Calling `/api/v1/cameras/` endpoint
2. Backend NOW returns real-time worker status (after our fix)
3. But Flutter only calls this on `refreshAllCameras()` - not automatically!

**Result**:
- Camera connects → Flutter doesn't refresh → UI shows "disconnected"
- You manually tap refresh → Flutter sees "connected" → UI updates

### Issue 3: RTSP Delays

RTSP cameras take 2-5 seconds to connect (network stream initialization). During this time:
- Backend worker status: "connecting"
- Flutter expects immediate response
- UI shows loading state forever or times out

### Issue 4: Disconnect Doesn't Work

Same as Issue #1 - calling non-existent `disconnectCamera()` method.

## Required Fixes

### Fix 1: Add Missing Methods to camera_service.dart

**File**: `/lib/core/services/camera_service.dart`

```dart
/// Connect to a camera
Future<bool> connectCamera(String deviceId) async {
  try {
    final response = await _directCameraClient.post<Map<String, dynamic>>(
      '/api/v1/cameras/$deviceId/connect',
    );
    return response.statusCode == 200;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

/// Disconnect from a camera
Future<bool> disconnectCamera(String deviceId) async {
  try {
    final response = await _directCameraClient.post<Map<String, dynamic>>(
      '/api/v1/cameras/$deviceId/disconnect',
    );
    return response.statusCode == 200;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}
```

### Fix 2: Auto-refresh Status After Actions

**File**: `/lib/core/providers/multi_camera_providers.dart`

```dart
/// Connect to a camera
Future<bool> connectCamera(String cameraId) async {
  try {
    final allCameras = await _ref.read(allCamerasProvider.future);
    final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
    if (camera == null) return false;
    
    final success = await _cameraService.connectCamera(camera.deviceId);
    if (success) {
      // Wait a moment for backend to update
      await Future.delayed(Duration(milliseconds: 500));
      await refreshAllCameras();
    }
    return success;
  } catch (e) {
    print('Error connecting to camera $cameraId: $e');
    return false;
  }
}
```

### Fix 3: Add Status Polling for Real-time Updates

**File**: `/lib/core/providers/camera_status_providers.dart` (Create if doesn't exist)

```dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/camera_service.dart';

/// Provider that polls camera status every 2 seconds
final cameraStatusPollingProvider = StreamProvider.family<String, String>((ref, deviceId) async* {
  final cameraService = ref.watch(cameraServiceProvider);
  
  while (true) {
    try {
      final cameras = await cameraService.getCameras();
      final camera = cameras.firstWhere((c) => c.deviceId == deviceId, orElse: () => null);
      yield camera?.status ?? 'disconnected';
    } catch (e) {
      yield 'error';
    }
    await Future.delayed(Duration(seconds: 2));
  }
});
```

### Fix 4: Update CameraCard to Use Real-time Status

**File**: `/lib/widgets/camera/camera_card.dart`

```dart
@override
Widget build(BuildContext context) {
  // Watch real-time status
  final statusAsync = ref.watch(cameraStatusPollingProvider(widget.camera.deviceId));
  
  return statusAsync.when(
    data: (status) {
      // Update local copy of camera with real-time status
      final updatedCamera = widget.camera.copyWith(status: status);
      return _buildCard(context, updatedCamera);
    },
    loading: () => _buildCard(context, widget.camera),
    error: (_, __) => _buildCard(context, widget.camera),
  );
}
```

### Fix 5: Handle RTSP Connection Delays

**File**: `/lib/core/providers/multi_camera_providers.dart`

```dart
/// Connect to a camera with timeout handling
Future<bool> connectCamera(String cameraId) async {
  try {
    final allCameras = await _ref.read(allCamerasProvider.future);
    final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
    if (camera == null) return false;
    
    // Start connection (returns immediately)
    final success = await _cameraService.connectCamera(camera.deviceId);
    
    if (success && camera.cameraType == 'RTSP') {
      // RTSP cameras need time to connect - poll status
      for (int i = 0; i < 10; i++) {  // Wait up to 5 seconds
        await Future.delayed(Duration(milliseconds: 500));
        await refreshAllCameras();
        
        final updatedCameras = await _ref.read(allCamerasProvider.future);
        final updatedCamera = updatedCameras.where((c) => c.id == cameraId).firstOrNull;
        
        if (updatedCamera?.status == 'connected') {
          return true;
        }
      }
    } else {
      // USB cameras connect fast
      await Future.delayed(Duration(milliseconds: 200));
      await refreshAllCameras();
    }
    
    return success;
  } catch (e) {
    print('Error connecting to camera $cameraId: $e');
    return false;
  }
}
```

## Implementation Priority

1. ✅ **CRITICAL**: Add `connectCamera()` and `disconnectCamera()` methods to `camera_service.dart`
2. ✅ **HIGH**: Update `multi_camera_providers.dart` to handle RTSP delays
3. ⏳ **MEDIUM**: Add status polling provider for real-time updates
4. ⏳ **LOW**: Update UI to show connection progress for RTSP

## Testing Plan

After implementing fixes:

1. **USB Camera Test**:
   - Click "Connect" → Should connect in <500ms
   - UI should show "connected" state
   - Click "Disconnect" → Should disconnect
   - UI should show "disconnected" state

2. **RTSP Camera Test**:
   - Click "Connect" → Should show "connecting" state
   - After 2-3 seconds → Should show "connected" state  
   - Stream should start automatically
   - Click "Disconnect" → Should disconnect and stop stream

3. **Concurrent Streams Test**:
   - Connect USB and RTSP simultaneously
   - Both should stream without interfering
   - Each should maintain independent state

4. **Recording Test**:
   - Start recording on USB camera
   - Recording should not block streaming
   - Recording should not affect RTSP camera

## Root Cause Summary

The queue architecture is working perfectly on the backend. The problem is Flutter:

1. **Calls non-existent methods** (`connectCamera`, `disconnectCamera`)
2. **Doesn't poll status** - only checks when manually refreshed
3. **Doesn't handle async connection delays** - expects immediate results
4. **State gets out of sync** - backend workers connected, Flutter thinks disconnected

Once we fix these 4 issues, Flutter will work smoothly with the queue architecture.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/camera.dart';
import '../models/rtsp_camera.dart';
import '../models/snapshot_result.dart';
import '../services/camera_service.dart';
import '../api/api_client.dart';
import 'camera_providers.dart';

/// All cameras provider (USB + RTSP) - uses existing camera service
final allCamerasProvider = FutureProvider<List<Camera>>((ref) async {
  final cameraListState = ref.watch(cameraListProvider);
  
  // If cameras are loading, wait for them
  if (cameraListState.isLoading) {
    // Trigger loading if not already loaded
    await ref.read(cameraListProvider.notifier).loadCameras();
    return ref.read(cameraListProvider).cameras;
  }
  
  // Return current cameras
  return cameraListState.cameras;
});

/// USB cameras provider
final usbCamerasProvider = FutureProvider<List<Camera>>((ref) async {
  final allCameras = await ref.watch(allCamerasProvider.future);
  return allCameras.where((c) => c.type == CameraType.usb).toList();
});

/// RTSP cameras provider - placeholder for now
final rtspCamerasProvider = FutureProvider<List<Camera>>((ref) async {
  final allCameras = await ref.watch(allCamerasProvider.future);
  return allCameras.where((c) => c.type == CameraType.rtsp).toList();
});

/// RTSP configurations provider - placeholder for local RTSP config
final rtspConfigurationsProvider = Provider<List<RTSPCamera>>((ref) {
  // For now, return empty list - will be implemented when RTSP feature is added
  return <RTSPCamera>[];
});

/// Individual camera provider
final cameraProvider = FutureProvider.family<Camera?, String>((ref, cameraId) async {
  final allCameras = await ref.watch(allCamerasProvider.future);
  return allCameras.where((c) => c.id == cameraId).firstOrNull;
});

/// Camera streaming info provider - integrated with existing camera service
final cameraStreamingInfoProvider = 
    FutureProvider.family<StreamingStatus?, String>((ref, cameraId) async {
  final cameraService = ref.watch(cameraServiceProvider);
  try {
    // Get camera to use device_id for API calls
    final allCameras = await ref.read(allCamerasProvider.future);
    final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
    if (camera == null) return null;
    
    return await cameraService.getStreamingStatus(camera.deviceId);
  } catch (e) {
    // Return null if streaming info not available
    return null;
  }
});

/// Camera actions provider using existing camera service
final cameraActionsProvider = Provider<CameraActions>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraActions(cameraService, ref);
});

/// Per-camera streaming state provider to avoid interference between camera types
final perCameraStreamProvider = StateNotifierProvider.family<PerCameraStreamNotifier, PerCameraStreamState, String>((ref, cameraId) {
  return PerCameraStreamNotifier(cameraId);
});

/// Per-camera streaming state
class PerCameraStreamState {
  final String cameraId;
  final bool isStreaming;
  final bool isLoading;
  final String? error;

  const PerCameraStreamState({
    required this.cameraId,
    this.isStreaming = false,
    this.isLoading = false,
    this.error,
  });

  PerCameraStreamState copyWith({
    String? cameraId,
    bool? isStreaming,
    bool? isLoading,
    String? error,
  }) {
    return PerCameraStreamState(
      cameraId: cameraId ?? this.cameraId,
      isStreaming: isStreaming ?? this.isStreaming,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

/// Per-camera stream notifier to manage individual camera streaming states
class PerCameraStreamNotifier extends StateNotifier<PerCameraStreamState> {
  PerCameraStreamNotifier(String cameraId) : super(PerCameraStreamState(cameraId: cameraId));

  Future<void> startStreaming() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      // Streaming logic handled in camera actions, just update state
      state = state.copyWith(isStreaming: true, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> stopStreaming() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      // Streaming logic handled in camera actions, just update state
      state = state.copyWith(isStreaming: false, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void setError(String error) {
    state = state.copyWith(isLoading: false, error: error);
  }
}

/// Camera actions class for state management using existing camera service
class CameraActions {
  final CameraService _cameraService;
  final Ref _ref;

  CameraActions(this._cameraService, this._ref);

  /// Refresh all cameras
  Future<void> refreshAllCameras() async {
    // Use the existing camera list notifier to reload cameras
    await _ref.read(cameraListProvider.notifier).loadCameras();
    
    // Invalidate all derived providers
    _ref.invalidate(allCamerasProvider);
    _ref.invalidate(usbCamerasProvider);
    _ref.invalidate(rtspCamerasProvider);
  }

  /// Detect new cameras
  Future<void> detectCameras() async {
    await _ref.read(cameraListProvider.notifier).detectCameras();
    
    // Invalidate all derived providers
    _ref.invalidate(allCamerasProvider);
    _ref.invalidate(usbCamerasProvider);
    _ref.invalidate(rtspCamerasProvider);
  }

  /// Connect to a camera
  Future<bool> connectCamera(String cameraId) async {
    try {
      // Use device_id for camera service API calls
      final allCameras = await _ref.read(allCamerasProvider.future);
      final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
      if (camera == null) return false;
      
      final success = await _cameraService.connectCamera(camera.deviceId);
      if (success) {
        await refreshAllCameras();
      }
      return success;
    } catch (e) {
      print('Error connecting to camera $cameraId: $e');
      return false;
    }
  }

  /// Disconnect from a camera
  Future<bool> disconnectCamera(String cameraId) async {
    try {
      // Use device_id for camera service API calls
      final allCameras = await _ref.read(allCamerasProvider.future);
      final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
      if (camera == null) return false;
      
      final success = await _cameraService.disconnectCamera(camera.deviceId);
      if (success) {
        await refreshAllCameras();
      }
      return success;
    } catch (e) {
      print('Error disconnecting from camera $cameraId: $e');
      return false;
    }
  }

  /// Start streaming for a camera
  Future<StreamingInfo?> startStreaming(String cameraId) async {
    try {
      // Get camera to use device_id for API calls
      final allCameras = await _ref.read(allCamerasProvider.future);
      final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
      if (camera == null) return null;
      
      // Update per-camera stream state
      _ref.read(perCameraStreamProvider(cameraId).notifier).startStreaming();
      
      // First ensure camera is connected
      await connectCamera(cameraId);
      
      // Start streaming with default settings using device_id
      final streamingInfo = await _cameraService.startStreaming(camera.deviceId);
      
      // Refresh camera status
      _ref.invalidate(cameraStreamingInfoProvider(cameraId));
      
      return streamingInfo;
    } catch (e) {
      print('Error starting streaming for camera $cameraId: $e');
      // Update error state for this specific camera
      _ref.read(perCameraStreamProvider(cameraId).notifier).setError(e.toString());
      return null;
    }
  }

  /// Stop streaming for a camera
  Future<void> stopStreaming(String cameraId) async {
    try {
      // Get camera to use device_id for API calls
      final allCameras = await _ref.read(allCamerasProvider.future);
      final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
      if (camera == null) return;
      
      // Update per-camera stream state
      _ref.read(perCameraStreamProvider(cameraId).notifier).stopStreaming();
      
      await _cameraService.stopStreaming(camera.deviceId);
      
      // Refresh camera status
      _ref.invalidate(cameraStreamingInfoProvider(cameraId));
    } catch (e) {
      print('Error stopping streaming for camera $cameraId: $e');
      // Update error state for this specific camera
      _ref.read(perCameraStreamProvider(cameraId).notifier).setError(e.toString());
    }
  }

  /// Take snapshot from a camera
  Future<SnapshotResult?> takeSnapshot(String cameraId) async {
    try {
      // Get camera to use device_id for API calls
      final allCameras = await _ref.read(allCamerasProvider.future);
      final camera = allCameras.where((c) => c.id == cameraId).firstOrNull;
      if (camera == null) return null;
      
      final snapshot = await _cameraService.captureSnapshot(camera.deviceId);
      return snapshot;
    } catch (e) {
      print('Error taking snapshot from camera $cameraId: $e');
      return null;
    }
  }
  /// Add RTSP camera
  Future<Camera?> addRTSPCamera({
    required String name,
    required String host,
    int port = 554,
    String? username,
    String? password,
    String streamPath = '/stream',
  }) async {
    try {
      final camera = await _cameraService.addRTSPCamera(
        name: name,
        host: host,
        port: port,
        path: streamPath,
        username: username,
        password: password,
      );
      
      // Refresh all camera providers
      await refreshAllCameras();
      
      return camera;
    } catch (e) {
      print('Error adding RTSP camera: $e');
      return null;
    }
  }

  /// Update RTSP camera
  Future<Camera?> updateRTSPCamera(String cameraId, RTSPCamera updatedCamera) async {
    try {
      final camera = await _cameraService.updateRTSPCamera(
        deviceId: cameraId,
        name: updatedCamera.name,
        host: updatedCamera.host,
        port: updatedCamera.port,
        username: updatedCamera.username,
        password: updatedCamera.password,
        path: updatedCamera.streamPath,
      );
      
      // Refresh all camera providers
      await refreshAllCameras();
      
      return camera;
    } catch (e) {
      print('Error updating RTSP camera: $e');
      return null;
    }
  }

  /// Remove RTSP camera
  Future<bool> removeRTSPCamera(String cameraId) async {
    try {
      await _cameraService.deleteRTSPCamera(cameraId);
      
      // Refresh all camera providers
      await refreshAllCameras();
      
      return true;
    } catch (e) {
      print('Error removing RTSP camera: $e');
      return false;
    }
  }
}

/// Active cameras filter provider
final activeCamerasProvider = Provider<List<Camera>>((ref) {
  final allCameras = ref.watch(allCamerasProvider);
  return allCameras.when(
    data: (cameras) => cameras.where((camera) => camera.isActive).toList(),
    loading: () => <Camera>[],
    error: (_, __) => <Camera>[],
  );
});

/// USB cameras filter provider
final activeusbCamerasProvider = Provider<List<Camera>>((ref) {
  final allCameras = ref.watch(allCamerasProvider);
  return allCameras.when(
    data: (cameras) => cameras.where((camera) => 
        camera.type == CameraType.usb && camera.isActive).toList(),
    loading: () => <Camera>[],
    error: (_, __) => <Camera>[],
  );
});

/// RTSP cameras filter provider
final activertspCamerasProvider = Provider<List<Camera>>((ref) {
  final allCameras = ref.watch(allCamerasProvider);
  return allCameras.when(
    data: (cameras) => cameras.where((camera) => 
        camera.type == CameraType.rtsp && camera.isActive).toList(),
    loading: () => <Camera>[],
    error: (_, __) => <Camera>[],
  );
});

/// Camera counts provider
final cameraCountsProvider = Provider<CameraCounts>((ref) {
  final allCameras = ref.watch(allCamerasProvider);
  return allCameras.when(
    data: (cameras) {
      final usbCount = cameras.where((c) => c.type == CameraType.usb).length;
      final rtspCount = cameras.where((c) => c.type == CameraType.rtsp).length;
      final activeCount = cameras.where((c) => c.isActive).length;
      
      return CameraCounts(
        total: cameras.length,
        usb: usbCount,
        rtsp: rtspCount,
        active: activeCount,
      );
    },
    loading: () => const CameraCounts(total: 0, usb: 0, rtsp: 0, active: 0),
    error: (_, __) => const CameraCounts(total: 0, usb: 0, rtsp: 0, active: 0),
  );
});

/// Camera counts data class
class CameraCounts {
  final int total;
  final int usb;
  final int rtsp;
  final int active;
  final int inactive;

  const CameraCounts({
    required this.total,
    required this.usb,
    required this.rtsp,
    required this.active,
    this.inactive = 0,
  });

  const CameraCounts.empty()
      : total = 0,
        usb = 0,
        rtsp = 0,
        active = 0,
        inactive = 0;
}

/// Cameras by type filter provider
final camerasByTypeProvider = Provider.family<List<Camera>, CameraType>((ref, type) {
  final allCameras = ref.watch(allCamerasProvider);
  return allCameras.when(
    data: (cameras) => cameras.where((camera) => camera.type == type).toList(),
    loading: () => [],
    error: (_, __) => [],
  );
});

/// Camera count provider
final cameraCountProvider = Provider<CameraCounts>((ref) {
  final allCameras = ref.watch(allCamerasProvider);
  return allCameras.when(
    data: (cameras) {
      final usbCount = cameras.where((c) => c.type == CameraType.usb).length;
      final rtspCount = cameras.where((c) => c.type == CameraType.rtsp).length;
      final activeCount = cameras.where((c) => c.isActive).length;
      
      return CameraCounts(
        total: cameras.length,
        usb: usbCount,
        rtsp: rtspCount,
        active: activeCount,
        inactive: cameras.length - activeCount,
      );
    },
    loading: () => const CameraCounts.empty(),
    error: (_, __) => const CameraCounts.empty(),
  );
});

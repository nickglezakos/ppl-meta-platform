import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/camera_service.dart';
import '../services/camera_collection_service.dart';
import '../services/background_sync_service.dart';
import '../services/snapshot_collection_service.dart';
import '../services/auth_service.dart';
import '../models/camera.dart';
import '../models/snapshot_result.dart';
import '../models/collection_models.dart';
import '../api/api_client.dart';
import '../../services/media_api_client.dart';

/// Provider for camera service
final cameraServiceProvider = Provider<CameraService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CameraService(apiClient);
});

/// State for camera list
class CameraListState {
  final List<Camera> cameras;
  final bool isLoading;
  final bool isDetecting;
  final String? error;

  const CameraListState({
    this.cameras = const [],
    this.isLoading = false,
    this.isDetecting = false,
    this.error,
  });

  CameraListState copyWith({
    List<Camera>? cameras,
    bool? isLoading,
    bool? isDetecting,
    String? error,
  }) {
    return CameraListState(
      cameras: cameras ?? this.cameras,
      isLoading: isLoading ?? this.isLoading,
      isDetecting: isDetecting ?? this.isDetecting,
      error: error ?? this.error,
    );
  }
}

/// State notifier for managing camera list
class CameraListNotifier extends StateNotifier<CameraListState> {
  final CameraService _cameraService;

  CameraListNotifier(this._cameraService) : super(const CameraListState()) {
    // Don't auto-load cameras in constructor to prevent premature API calls
    // loadCameras() will be called explicitly when needed
  }

  /// Load cameras from the backend
  Future<void> loadCameras() async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final cameras = await _cameraService.getCameras();
      
      // TEMPORARY: Add hardcoded mobile camera for testing
      final testMobileCamera = Camera(
        id: 'mobile_TKQ1.221114.001',
        name: 'Mobile Camera TKQ1',
        deviceId: 'mobile_TKQ1.221114.001', // Use the full device ID that worked in HTML test
        type: CameraType.mobile,
        status: 'connected',
        isActive: true,
        resolution: '720x480',
        lastSeen: DateTime.now(),
      );
      
      final allCameras = [testMobileCamera, ...cameras];
      
      state = state.copyWith(
        cameras: allCameras,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Detect new cameras
  Future<void> detectCameras({bool saveToDb = true}) async {
    state = state.copyWith(isDetecting: true, error: null);
    
    try {
      final detectedCameras = await _cameraService.detectCameras(saveToDb: saveToDb);
      state = state.copyWith(
        cameras: detectedCameras,
        isDetecting: false,
      );
    } catch (e) {
      state = state.copyWith(
        isDetecting: false,
        error: e.toString(),
      );
    }
  }

  /// Update a camera in the list
  void updateCamera(Camera updatedCamera) {
    final updatedCameras = state.cameras.map((camera) {
      return camera.id == updatedCamera.id ? updatedCamera : camera;
    }).toList();
    
    state = state.copyWith(cameras: updatedCameras);
  }

  /// Remove a camera from the list
  void removeCamera(String cameraId) {
    final updatedCameras = state.cameras.where((camera) => camera.id != cameraId).toList();
    state = state.copyWith(cameras: updatedCameras);
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Provider for camera list state notifier
final cameraListProvider = StateNotifierProvider<CameraListNotifier, CameraListState>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraListNotifier(cameraService);
});

/// State for individual camera streaming
class CameraStreamState {
  final String? cameraId;
  final StreamingInfo? streamingInfo;
  final StreamingStatus? status;
  final bool isLoading;
  final bool isStreaming;
  final String? streamUrl;
  final String? error;

  const CameraStreamState({
    this.cameraId,
    this.streamingInfo,
    this.status,
    this.isLoading = false,
    this.isStreaming = false,
    this.streamUrl,
    this.error,
  });

  CameraStreamState copyWith({
    String? cameraId,
    StreamingInfo? streamingInfo,
    StreamingStatus? status,
    bool? isLoading,
    bool? isStreaming,
    String? streamUrl,
    String? error,
  }) {
    return CameraStreamState(
      cameraId: cameraId ?? this.cameraId,
      streamingInfo: streamingInfo ?? this.streamingInfo,
      status: status ?? this.status,
      isLoading: isLoading ?? this.isLoading,
      isStreaming: isStreaming ?? this.isStreaming,
      streamUrl: streamUrl ?? this.streamUrl,
      error: error ?? this.error,
    );
  }
}

/// State notifier for managing camera streaming
class CameraStreamNotifier extends StateNotifier<CameraStreamState> {
  final CameraService _cameraService;

  CameraStreamNotifier(this._cameraService) : super(const CameraStreamState());

  /// Start streaming for a camera with quality controls
  Future<void> startStreaming(
    String cameraId, {
    String quality = 'high',
    int fps = 30,
    String resolution = '1280x720',
    String format = 'MJPEG',
  }) async {
    state = state.copyWith(
      cameraId: cameraId,
      isLoading: true,
      error: null,
    );
    
    try {
      // Start streaming with quality controls
      final streamingInfo = await _cameraService.startStreaming(
        cameraId,
        quality: quality,
        fps: fps,
        resolution: resolution,
        format: format,
      );
      
      // Create enhanced streaming info with the video stream URL
      final enhancedStreamingInfo = streamingInfo.copyWith(
        streamUrl: _cameraService.getVideoStreamUrl(cameraId),
      );
      
      final streamUrl = _cameraService.getVideoStreamUrl(cameraId);
      
      state = state.copyWith(
        streamingInfo: enhancedStreamingInfo,
        streamUrl: streamUrl,
        isLoading: false,
        isStreaming: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Stop streaming for the current camera
  Future<void> stopStreaming([String? cameraId]) async {
    final targetCameraId = cameraId ?? state.cameraId;
    if (targetCameraId == null) return;
    
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      await _cameraService.stopStreaming(targetCameraId);
      state = state.copyWith(
        streamingInfo: null,
        streamUrl: null,
        isLoading: false,
        isStreaming: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Get streaming status for the current camera
  Future<void> getStreamingStatus([String? cameraId]) async {
    final targetCameraId = cameraId ?? state.cameraId;
    if (targetCameraId == null) return;
    
    try {
      final status = await _cameraService.getStreamingStatus(targetCameraId);
      state = state.copyWith(status: status);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Clear the streaming state
  void clearStream() {
    state = const CameraStreamState();
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Provider for camera stream state notifier
final cameraStreamProvider = StateNotifierProvider<CameraStreamNotifier, CameraStreamState>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraStreamNotifier(cameraService);
});

/// State for camera snapshots
class CameraSnapshotState {
  final List<SnapshotResult> snapshots;
  final bool isCapturing;
  final String? error;

  const CameraSnapshotState({
    this.snapshots = const [],
    this.isCapturing = false,
    this.error,
  });

  CameraSnapshotState copyWith({
    List<SnapshotResult>? snapshots,
    bool? isCapturing,
    String? error,
  }) {
    return CameraSnapshotState(
      snapshots: snapshots ?? this.snapshots,
      isCapturing: isCapturing ?? this.isCapturing,
      error: error ?? this.error,
    );
  }
}

/// State notifier for managing camera snapshots
class CameraSnapshotNotifier extends StateNotifier<CameraSnapshotState> {
  final CameraService _cameraService;

  CameraSnapshotNotifier(this._cameraService) : super(const CameraSnapshotState());

  /// Capture a snapshot from a camera
  Future<void> captureSnapshot(String cameraId) async {
    state = state.copyWith(isCapturing: true, error: null);
    
    try {
      final snapshotInfo = await _cameraService.captureSnapshot(cameraId);
      state = state.copyWith(
        snapshots: [snapshotInfo, ...state.snapshots],
        isCapturing: false,
      );
    } catch (e) {
      state = state.copyWith(
        isCapturing: false,
        error: e.toString(),
      );
    }
  }

  /// Clear all snapshots
  void clearSnapshots() {
    state = state.copyWith(snapshots: []);
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Provider for camera snapshot state notifier
final cameraSnapshotProvider = StateNotifierProvider<CameraSnapshotNotifier, CameraSnapshotState>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraSnapshotNotifier(cameraService);
});

/// Provider for getting a specific camera by ID
final cameraByIdProvider = FutureProvider.family<Camera?, String>((ref, cameraId) async {
  final cameraListState = ref.watch(cameraListProvider);
  try {
    return cameraListState.cameras.firstWhere((camera) => camera.deviceId == cameraId);
  } catch (e) {
    return null;
  }
});

/// Provider for active cameras only
final activeCamerasProvider = Provider<List<Camera>>((ref) {
  final cameraListState = ref.watch(cameraListProvider);
  return cameraListState.cameras.where((camera) => camera.isActive).toList();
});

/// Provider for connected cameras only
final connectedCamerasProvider = Provider<List<Camera>>((ref) {
  final cameraListState = ref.watch(cameraListProvider);
  return cameraListState.cameras.where((camera) => camera.isConnected).toList();
});

/// Provider for camera collection service
final cameraCollectionServiceProvider = Provider<CameraCollectionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final authService = ref.watch(authServiceProvider);
  final collectionService = CameraCollectionService(apiClient);
  
  // Register for authentication success events to trigger collection detection
  authService.registerOnAuthenticationSuccess(() {
    collectionService.retryCollectionDetectionAfterAuth();
    
    // Invalidate all camera collection providers to force refresh
    ref.invalidateSelf();
  });
  
  return collectionService;
});

/// Provider for media API client (for snapshot uploads)
final mediaApiClientProvider = Provider<MediaApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return MediaApiClient(apiClient);
});

/// Provider for background sync service
final backgroundSyncServiceProvider = Provider<BackgroundSyncService>((ref) {
  final mediaApiClient = ref.watch(mediaApiClientProvider);
  return BackgroundSyncService(mediaApiClient);
});

/// Enhanced provider for snapshot collection service with auto-upload
final snapshotCollectionServiceProvider = Provider<SnapshotCollectionService>((ref) {
  final mediaApiClient = ref.watch(mediaApiClientProvider);
  final syncService = ref.watch(backgroundSyncServiceProvider);
  final cameraCollectionService = ref.watch(cameraCollectionServiceProvider);
  return SnapshotCollectionService(mediaApiClient, syncService, cameraCollectionService);
});

/// State for camera collections
class CameraCollectionState {
  final List<MediaCollection> collections;
  final List<CameraCollectionMapping> mappings;
  final bool isLoading;
  final String? error;

  const CameraCollectionState({
    this.collections = const [],
    this.mappings = const [],
    this.isLoading = false,
    this.error,
  });

  CameraCollectionState copyWith({
    List<MediaCollection>? collections,
    List<CameraCollectionMapping>? mappings,
    bool? isLoading,
    String? error,
  }) {
    return CameraCollectionState(
      collections: collections ?? this.collections,
      mappings: mappings ?? this.mappings,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

/// State notifier for managing camera collections
class CameraCollectionNotifier extends StateNotifier<CameraCollectionState> {
  final CameraCollectionService _collectionService;

  CameraCollectionNotifier(this._collectionService) : super(const CameraCollectionState());

  /// Setup camera with collection auto-creation
  Future<MediaCollection?> setupCameraWithCollection(Camera camera) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final collection = await _collectionService.setupCameraWithCollection(camera);
      
      // Update state with new collection and mapping
      await loadCollectionsAndMappings();
      
      state = state.copyWith(isLoading: false);
      return collection;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }

  /// Load all collections and mappings
  Future<void> loadCollectionsAndMappings() async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final collections = await _collectionService.getAllCollections();
      final mappings = await _collectionService.getAllCameraMappings();
      
      state = state.copyWith(
        collections: collections,
        mappings: mappings,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Get collection for a specific camera
  Future<MediaCollection?> getCameraCollection(String cameraId) async {
    try {
      final collectionId = await _collectionService.getCameraCollectionId(cameraId);
      if (collectionId != null) {
        return await _collectionService.getCollectionById(collectionId);
      }
      return null;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Create collection for camera
  Future<MediaCollection?> createCameraCollection(String cameraId, String cameraName) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final collection = await _collectionService.createCameraCollection(cameraId, cameraName);
      
      // Reload to get updated state
      await loadCollectionsAndMappings();
      
      state = state.copyWith(isLoading: false);
      return collection;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }

  /// Check if camera has collection
  Future<bool> hasCameraCollection(String cameraId) async {
    try {
      return await _collectionService.hasCameraCollection(cameraId);
    } catch (e) {
      return false;
    }
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Provider for camera collection state notifier
final cameraCollectionProvider = StateNotifierProvider<CameraCollectionNotifier, CameraCollectionState>((ref) {
  final collectionService = ref.watch(cameraCollectionServiceProvider);
  return CameraCollectionNotifier(collectionService);
});

/// Provider for camera collections only
final cameraCollectionsProvider = Provider<List<MediaCollection>>((ref) {
  final collectionState = ref.watch(cameraCollectionProvider);
  return collectionState.collections.where((collection) => 
    collection.metadata?['collection_type'] == 'camera_snapshots' ||
    collection.metadata?['camera_id'] != null
  ).toList();
});

/// Provider for getting collection by camera ID
final collectionByCameraIdProvider = Provider.family<MediaCollection?, String>((ref, cameraId) {
  final collectionState = ref.watch(cameraCollectionProvider);
  
  // Find mapping for this camera
  CameraCollectionMapping? mapping;
  try {
    mapping = collectionState.mappings.firstWhere((m) => m.cameraId == cameraId);
  } catch (e) {
    return null;
  }
  
  if (mapping != null) {
    // Find collection for this mapping
    try {
      return collectionState.collections.firstWhere((c) => c.id == mapping!.collectionId);
    } catch (e) {
      return null;
    }
  }
  return null;
});

/// Provider to check if a camera has a collection
final cameraHasCollectionProvider = FutureProvider.family<bool, String>((ref, cameraId) async {
  final collectionService = ref.watch(cameraCollectionServiceProvider);
  return await collectionService.hasCameraCollection(cameraId);
});

/// Provider to get a camera's collection ID
final cameraCollectionIdProvider = FutureProvider.family<String?, String>((ref, cameraId) async {
  final collectionService = ref.watch(cameraCollectionServiceProvider);
  return await collectionService.getCameraCollectionId(cameraId);
});

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/orchestrator_api_client.dart';
import '../services/media_api_client.dart'; // For FaceDetection and FaceBoundingBox classes
import '../models/api_models.dart'; // For EnhancedLogicV2Face

// =============================================================================
// FACE DATA PROVIDERS
// =============================================================================
//
// This file manages face data loading, caching, and state management for 
// real-time face visualization in media preview screens.
//
// Provider Hierarchy:
// 1. Face Data State Management (MediaFaceDataProvider)
// 2. Face Loading Services (Orchestrator session-based API integration)
// 3. Memory Management (LRU cache for face data)
// 4. Face Count Tracking (Real-time face count updates)
//
// =============================================================================

// -----------------------------------------------------------------------------
// FACE DATA STATE MODELS
// -----------------------------------------------------------------------------

/// State class for managing face data for a specific media item
class MediaFaceDataState {
  final String mediaId;
  final List<FaceDetection> faces;
  final bool isLoading;
  final String? error;
  final DateTime? lastUpdated;
  final int totalCount;

  const MediaFaceDataState({
    required this.mediaId,
    this.faces = const [],
    this.isLoading = false,
    this.error,
    this.lastUpdated,
    int? totalCount,
  }) : totalCount = totalCount ?? faces.length;

  MediaFaceDataState copyWith({
    String? mediaId,
    List<FaceDetection>? faces,
    bool? isLoading,
    String? error,
    DateTime? lastUpdated,
    int? totalCount,
  }) {
    return MediaFaceDataState(
      mediaId: mediaId ?? this.mediaId,
      faces: faces ?? this.faces,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      totalCount: totalCount ?? this.totalCount,
    );
  }

  /// Create loading state
  MediaFaceDataState.loading(String mediaId)
      : this(
          mediaId: mediaId,
          faces: const [],
          isLoading: true,
          error: null,
          lastUpdated: null,
          totalCount: 0,
        );

  /// Create error state
  MediaFaceDataState.error(String mediaId, String errorMessage)
      : this(
          mediaId: mediaId,
          faces: const [],
          isLoading: false,
          error: errorMessage,
          lastUpdated: null,
          totalCount: 0,
        );

  /// Create success state
  MediaFaceDataState.success(String mediaId, List<FaceDetection> faces)
      : this(
          mediaId: mediaId,
          faces: faces,
          isLoading: false,
          error: null,
          lastUpdated: DateTime.now(),
          totalCount: faces.length,
        );

  bool get hasData => faces.isNotEmpty;
  bool get hasError => error != null;
  bool get isEmpty => faces.isEmpty && !isLoading && !hasError;
}

// -----------------------------------------------------------------------------
// FACE DATA CACHE MANAGEMENT
// -----------------------------------------------------------------------------

/// LRU Cache for managing face data in memory
class FaceDataCache {
  final int maxSize;
  final Map<String, MediaFaceDataState> _cache = {};
  final List<String> _accessOrder = [];

  FaceDataCache({this.maxSize = 20}); // Increased from 10 to 20

  /// Get face data from cache
  MediaFaceDataState? get(String mediaId) {
    if (_cache.containsKey(mediaId)) {
      _updateAccessOrder(mediaId);
      return _cache[mediaId];
    }
    return null;
  }

  /// Store face data in cache
  void put(String mediaId, MediaFaceDataState data) {
    if (_cache.containsKey(mediaId)) {
      _cache[mediaId] = data;
      _updateAccessOrder(mediaId);
    } else {
      if (_cache.length >= maxSize) {
        _evictLeastRecentlyUsed();
      }
      _cache[mediaId] = data;
      _accessOrder.add(mediaId);
    }
  }

  /// Remove face data from cache
  void remove(String mediaId) {
    _cache.remove(mediaId);
    _accessOrder.remove(mediaId);
  }

  /// Clear all cached face data
  void clear() {
    _cache.clear();
    _accessOrder.clear();
  }

  /// Check if cache contains data for media
  bool contains(String mediaId) => _cache.containsKey(mediaId);

  /// Get current cache size
  int get size => _cache.length;

  /// Get total face count across all cached media
  int get totalFaceCount => _cache.values
      .map((data) => data.totalCount)
      .fold(0, (sum, count) => sum + count);

  /// Get all cached media IDs
  List<String> get cachedMediaIds => _cache.keys.toList();

  void _updateAccessOrder(String mediaId) {
    _accessOrder.remove(mediaId);
    _accessOrder.add(mediaId);
  }

  void _evictLeastRecentlyUsed() {
    if (_accessOrder.isNotEmpty) {
      final oldestKey = _accessOrder.removeAt(0);
      _cache.remove(oldestKey);
    }
  }
}

// -----------------------------------------------------------------------------
// FACE DATA PROVIDER
// -----------------------------------------------------------------------------

/// StateNotifier for managing face data loading and caching
class MediaFaceDataNotifier extends StateNotifier<MediaFaceDataState> {
  final Ref ref;
  final String mediaId;
  final FaceDataCache _cache;
  Timer? _loadingTimeout;

  MediaFaceDataNotifier(
    this.ref,
    this.mediaId,
    this._cache,
  ) : super(MediaFaceDataState(mediaId: mediaId));

  /// Load face data for the current media item
  Future<void> loadFaces({bool forceRefresh = false}) async {
    print('🔍 PROVIDER: loadFaces called for media $mediaId (forceRefresh: $forceRefresh)');

    // KEEP-ALIVE FIX: This provider is autoDispose; without a listener it would be disposed
    // during the awaited HTTP call, causing "Tried to use MediaFaceDataNotifier after dispose"
    // when state is mutated after the response arrives. Pin it for the duration of the load.
    final keepAliveLink = ref.keepAlive();

    // CACHE CHECK: Check if already loading to prevent duplicate requests
    if (!forceRefresh && _isLoadingInProgress(mediaId)) {
      print('⏳ CACHE: Face loading already in progress for media $mediaId, skipping duplicate request');
      keepAliveLink.close();
      return;
    }

    // Check cache first (unless force refresh is requested)
    if (!forceRefresh && _cache.contains(mediaId)) {
      final cachedData = _cache.get(mediaId);
      if (cachedData != null && cachedData.hasData) {
        state = cachedData;
        print('✅ CACHE: Using cached faces for media $mediaId (${cachedData.totalCount} faces)');
        return;
      }
    }

    print('🔍 PROVIDER: No cache hit for media $mediaId, making API call...');
    
    // Mark as loading to prevent duplicate requests
    _markAsLoading(mediaId);

    // Set loading state
    state = MediaFaceDataState.loading(mediaId);

    // Set timeout for loading operation
    _loadingTimeout?.cancel();
    _loadingTimeout = Timer(const Duration(seconds: 30), () {
      if (state.isLoading) {
        state = MediaFaceDataState.error(
          mediaId,
          'Face loading timeout after 30 seconds',
        );
      }
    });

    try {
      // Get orchestrator API client for Enhanced Logic V2 direct call
      final orchestratorClient = ref.read(orchestratorApiClientProvider);

      // Use Enhanced Logic V2 endpoint which is already working 
      print('🔍 PROVIDER: Starting Enhanced Logic V2 call for media $mediaId...');
      final response = await orchestratorClient.getEnhancedLogicV2Response(mediaId);
      print('🔍 PROVIDER: Enhanced Logic V2 isSuccess=${response.isSuccess}, hasData=${response.data != null}, error=${response.error?.message}');

      _loadingTimeout?.cancel();

      print('🔍 PROVIDER: Enhanced Logic V2 response received - success: ${response.isSuccess}');
      if (response.data != null) {
        print('🔍 PROVIDER: Response data exists - totalFaces: ${response.data!.totalFaces}');
      } else {
        print('🔍 PROVIDER: Response data is null');
      }
      if (response.error != null) {
        print('🔍 PROVIDER: Response error: ${response.error!.message}');
      }

      if (response.isSuccess) {
        final enhancedV2Data = response.data;
        List<FaceDetection> faces = [];
        int totalFaces = 0;
        
        if (enhancedV2Data != null) {
          print('🔍 ENHANCED V2 RAW: totalFaces=${enhancedV2Data.totalFaces}, topLevelFrames=${enhancedV2Data.facesByFrame.keys.length}, source=${enhancedV2Data.source}');
          // Enhanced Logic V2 response structure
          totalFaces = enhancedV2Data.totalFaces;
          
          // 🔥 FIX: Use detection_result.faces_by_frame to get ALL detected faces!
          // The 'faces' array only contains 3-5 representative faces per person
          // The top-level 'faces_by_frame' also only has representative faces (5 frames)
          // The 'detection_result.faces_by_frame' contains ALL detected faces (72 across all frames)
          print('🔍 ENHANCED V2: faces array has ${enhancedV2Data.faces.length} faces (representative)');
          print('🔍 ENHANCED V2: top-level faces_by_frame has ${enhancedV2Data.facesByFrame.keys.length} frames');
          print('🔍 ENHANCED V2: detection_result available: ${enhancedV2Data.detectionResult != null}');
          
          if (enhancedV2Data.detectionResult == null ||
              !enhancedV2Data.detectionResult!.containsKey('faces_by_frame')) {
            throw Exception(
              'Enhanced Logic V2 did not return detection_result.faces_by_frame; refusing to use representative or synthetic fallback data',
            );
          }

          final facesSource =
              enhancedV2Data.detectionResult!['faces_by_frame'] as Map<String, dynamic>;
          print('✅ ENHANCED V2: Using detection_result.faces_by_frame with ${facesSource.keys.length} frames (ALL faces)');
          
          // Flatten faces_by_frame into a single list of ALL faces
          int faceIndex = 0;
          for (final entry in facesSource.entries) {
            final frameNumber = int.parse(entry.key);
            final facesInFrame = entry.value;
            
            // detection_result.faces_by_frame must be raw backend frame data.
            for (final faceData in facesInFrame) {
              if (faceData is! Map<String, dynamic>) {
                throw Exception(
                  'Enhanced Logic V2 detection_result.faces_by_frame returned non-map face data; refusing fallback parsing',
                );
              }

              final bboxRaw = faceData['bbox'] as List;
              final bbox = bboxRaw.map((e) => (e as num).toDouble()).toList();
              final confidence = (faceData['confidence'] as num).toDouble();
              final method = faceData['method'] as String;
              
              faces.add(FaceDetection(
                id: 'enhanced_v2_face_$faceIndex',
                mediaId: mediaId,
                boundingBox: FaceBoundingBox(
                  left: bbox[0],
                  top: bbox[1],
                  width: bbox[2] - bbox[0],
                  height: bbox[3] - bbox[1],
                ),
                confidence: confidence,
                timestamp: DateTime.now(),
                method: method,
                metadata: {
                  'frame_number': frameNumber,
                  'source': 'enhanced_v2_all_faces',
                },
              ));
              faceIndex++;
            }
          }
          
          print('✅ ENHANCED V2: Successfully loaded ${faces.length} faces from faces_by_frame (ALL faces, not just representatives)');
        } else {
          throw Exception('Enhanced Logic V2 response data is null');
        }
        
        // NO DEDUPLICATION: Use raw backend data directly - deduplication should happen in Enhanced Logic V2 backend
        final successState = MediaFaceDataState.success(mediaId, faces);
        
        // Update state
        state = successState;
        
        // Cache the result
        _cache.put(mediaId, successState);
        
        print('✅ ENHANCED V2: Loaded ${faces.length} faces (NO CLIENT-SIDE DEDUPLICATION) for media $mediaId');
      } else {
        final errorState = MediaFaceDataState.error(
          mediaId,
          response.error?.message ?? 'Failed to load face data',
        );
        state = errorState;
        print('❌ Failed to load faces for media $mediaId: ${response.error?.message}');
      }
    } catch (e) {
      _loadingTimeout?.cancel();
      final errorState = MediaFaceDataState.error(
        mediaId,
        'Face loading error: $e',
      );
      state = errorState;
      print('❌ Exception loading faces for media $mediaId: $e');
    } finally {
      // Always mark loading as complete
      _markLoadingComplete(mediaId);
      // Release the keep-alive pin so the provider can be disposed normally
      // once no widget is listening anymore.
      keepAliveLink.close();
    }
  }

  /// Refresh face data (force reload from server)
  Future<void> refresh() async {
    await loadFaces(forceRefresh: true);
  }

  /// Clear face data for this media
  void clearFaces() {
    _cache.remove(mediaId);
    state = MediaFaceDataState(mediaId: mediaId);
  }

  /// Get face count without loading (from cache)
  int getFaceCount() {
    return state.totalCount;
  }

  /// Check if faces are loaded
  bool get hasFaces => state.hasData;

  /// Check if currently loading
  bool get isLoading => state.isLoading;

  /// Check if there's an error
  bool get hasError => state.hasError;

  @override
  void dispose() {
    _loadingTimeout?.cancel();
    super.dispose();
  }
}

// -----------------------------------------------------------------------------
// GLOBAL FACE CACHE PROVIDER  
// -----------------------------------------------------------------------------

/// Global face data cache instance
final _globalFaceCache = FaceDataCache(maxSize: 50); // Increased for better performance

/// Track which media items are currently being loaded to prevent duplicate requests
final _loadingTracker = <String, DateTime>{};

/// Check if media face loading is already in progress
bool _isLoadingInProgress(String mediaId) {
  final loadingTime = _loadingTracker[mediaId];
  if (loadingTime != null) {
    // Consider loading stale after 30 seconds
    if (DateTime.now().difference(loadingTime).inSeconds < 30) {
      return true;
    } else {
      _loadingTracker.remove(mediaId); // Cleanup stale loading state
    }
  }
  return false;
}

/// Mark media as currently loading
void _markAsLoading(String mediaId) {
  _loadingTracker[mediaId] = DateTime.now();
}

/// Mark media loading as complete
void _markLoadingComplete(String mediaId) {
  _loadingTracker.remove(mediaId);
}

/// Global face data cache provider
final faceDataCacheProvider = Provider<FaceDataCache>((ref) => _globalFaceCache);

/// Media face data provider (per media UUID)
final mediaFaceDataProvider = StateNotifierProvider.autoDispose
    .family<MediaFaceDataNotifier, MediaFaceDataState, String>(
  (ref, mediaId) {
    // Return notifier with global cache reference
    return MediaFaceDataNotifier(ref, mediaId, _globalFaceCache);
  },
);

// -----------------------------------------------------------------------------
// FACE COUNT PROVIDER
// -----------------------------------------------------------------------------

/// Provider for getting face count for a specific media item
final mediaFaceCountProvider = Provider.family<int, String>((ref, mediaId) {
  final faceData = ref.watch(mediaFaceDataProvider(mediaId));
  return faceData.totalCount;
});

/// Provider for total face count across all cached media
final totalCachedFaceCountProvider = Provider<int>((ref) {
  final cache = ref.watch(faceDataCacheProvider);
  return cache.totalFaceCount;
});

// -----------------------------------------------------------------------------
// FACE LOADING STATE PROVIDER
// -----------------------------------------------------------------------------

/// Provider for checking if any face data is currently loading
final isFaceDataLoadingProvider = Provider.family<bool, String>((ref, mediaId) {
  final faceData = ref.watch(mediaFaceDataProvider(mediaId));
  return faceData.isLoading;
});

// -----------------------------------------------------------------------------
// AUTOMATIC FACE LOADING HOOK
// -----------------------------------------------------------------------------

/// Hook to automatically load faces when media changes
class AutoFaceLoader {
  static void loadFacesForMedia(WidgetRef ref, String mediaId) {
    // Trigger face loading for the specified media
    Future.microtask(() {
      final notifier = ref.read(mediaFaceDataProvider(mediaId).notifier);
      notifier.loadFaces();
    });
  }

  static void clearFacesForMedia(WidgetRef ref, String mediaId) {
    // Clear faces for the specified media
    final notifier = ref.read(mediaFaceDataProvider(mediaId).notifier);
    notifier.clearFaces();
  }
}
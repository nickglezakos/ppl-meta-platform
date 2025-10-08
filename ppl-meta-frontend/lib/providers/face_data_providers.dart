import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/orchestrator_api_client.dart';
import '../services/media_api_client.dart'; // For FaceDetection and FaceBoundingBox classes

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
    
    // DEDUPLICATION: Check if already loading to prevent duplicate requests
    if (!forceRefresh && _isLoadingInProgress(mediaId)) {
      print('⏳ DEDUPLICATION: Face loading already in progress for media $mediaId, skipping duplicate request');
      return;
    }

    // Check cache first (unless force refresh is requested)
    if (!forceRefresh && _cache.contains(mediaId)) {
      final cachedData = _cache.get(mediaId);
      if (cachedData != null && cachedData.hasData) {
        state = cachedData;
        print('✅ DEDUPLICATION: Using cached faces for media $mediaId (${cachedData.totalCount} faces)');
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
          // Enhanced Logic V2 response structure
          totalFaces = enhancedV2Data.totalFaces;
          
          // Convert Enhanced Logic V2 faces to FaceDetection objects
          faces = enhancedV2Data.faces.map((face) {
            return FaceDetection(
              id: 'enhanced_v2_face_${enhancedV2Data.faces.indexOf(face)}',
              mediaId: mediaId,
              boundingBox: FaceBoundingBox(
                left: face.bbox[0],
                top: face.bbox[1],
                width: face.bbox[2] - face.bbox[0],
                height: face.bbox[3] - face.bbox[1],
              ),
              confidence: face.confidence,
              timestamp: DateTime.now(),
              method: face.method,
              metadata: {
                'frame_number': face.frameNumber,
                'original_timestamp': face.timestamp,
                'source': 'enhanced_v2',
              },
            );
          }).toList();
          
          print('✅ ENHANCED V2: Successfully loaded $totalFaces faces using Enhanced Logic V2 with frame metadata');
        } else {
          throw Exception('Enhanced Logic V2 response data is null');
        }
        
        // DEDUPLICATION: Remove duplicates based on frame and position
        final deduplicatedFaces = _deduplicateFaces(faces);
        
        final successState = MediaFaceDataState.success(mediaId, deduplicatedFaces);
        
        // Update state
        state = successState;
        
        // Cache the result
        _cache.put(mediaId, successState);
        
        print('✅ ENHANCED V2: Loaded ${deduplicatedFaces.length} unique faces (${faces.length} total before deduplication) for media $mediaId');
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
    }
  }

  /// Deduplicate faces based on position similarity
  List<FaceDetection> _deduplicateFaces(List<FaceDetection> faces) {
    final Map<String, FaceDetection> uniqueFaces = {};
    
    for (final face in faces) {
      // Create unique key based on approximate position
      final positionKey = '${(face.boundingBox.left * 100).round()}_${(face.boundingBox.top * 100).round()}';
      
      // Keep the face with highest confidence if duplicate position found
      if (!uniqueFaces.containsKey(positionKey) || 
          face.confidence > uniqueFaces[positionKey]!.confidence) {
        uniqueFaces[positionKey] = face;
      }
    }
    
    final deduplicatedList = uniqueFaces.values.toList();
    
    if (deduplicatedList.length != faces.length) {
      print('🎯 DEDUPLICATION: Removed ${faces.length - deduplicatedList.length} duplicate faces');
    }
    
    return deduplicatedList;
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

/// Global face data cache instance with deduplication tracking
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

/// Media face data provider (per media UUID) with deduplication
final mediaFaceDataProvider = StateNotifierProvider.autoDispose
    .family<MediaFaceDataNotifier, MediaFaceDataState, String>(
  (ref, mediaId) {
    // Return notifier with global cache reference and deduplication tracking
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
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/vision_api_client.dart';
import '../services/media_api_client.dart'; // For FaceDetection class

// =============================================================================
// FACE DATA PROVIDERS
// =============================================================================
//
// This file manages face data loading, caching, and state management for 
// real-time face visualization in media preview screens.
//
// Provider Hierarchy:
// 1. Face Data State Management (MediaFaceDataProvider)
// 2. Face Loading Services (Vision API integration)
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
    // Check cache first (unless force refresh is requested)
    if (!forceRefresh && _cache.contains(mediaId)) {
      final cachedData = _cache.get(mediaId);
      if (cachedData != null && cachedData.hasData) {
        state = cachedData;
        return;
      }
    }

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
      // Get vision API client
      final visionClient = ref.read(visionApiClientProvider);

      // Fetch face data from Vision Service
      final response = await visionClient.getMediaFaces(mediaId);

      _loadingTimeout?.cancel();

      if (response.success) {
        final faces = response.data ?? <FaceDetection>[];
        final successState = MediaFaceDataState.success(mediaId, faces);
        
        // Update state
        state = successState;
        
        // Cache the result
        _cache.put(mediaId, successState);
        
        print('✅ Loaded ${faces.length} faces for media $mediaId');
      } else {
        final errorState = MediaFaceDataState.error(
          mediaId,
          response.error ?? 'Failed to load face data',
        );
        state = errorState;
        print('❌ Failed to load faces for media $mediaId: ${response.error}');
      }
    } catch (e) {
      _loadingTimeout?.cancel();
      final errorState = MediaFaceDataState.error(
        mediaId,
        'Face loading error: $e',
      );
      state = errorState;
      print('❌ Exception loading faces for media $mediaId: $e');
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
// VISION API CLIENT PROVIDER
// -----------------------------------------------------------------------------

/// Vision API client provider
final visionApiClientProvider = Provider<VisionApiClient>((ref) {
  return VisionApiClient(
    baseUrl: 'http://localhost:8003', // Vision service endpoint
  );
});

// -----------------------------------------------------------------------------
// GLOBAL FACE CACHE PROVIDER
// -----------------------------------------------------------------------------

/// Global face data cache provider
final faceDataCacheProvider = Provider<FaceDataCache>((ref) {
  return FaceDataCache(maxSize: 20); // Cache up to 20 media items
});

// -----------------------------------------------------------------------------
// MEDIA FACE DATA PROVIDER
// -----------------------------------------------------------------------------

/// Family provider for face data per media item
final mediaFaceDataProvider = StateNotifierProvider.family<
    MediaFaceDataNotifier, MediaFaceDataState, String>((ref, mediaId) {
  final cache = ref.watch(faceDataCacheProvider);
  return MediaFaceDataNotifier(ref, mediaId, cache);
});

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
import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'face_data_providers.dart';
import '../services/media_api_client.dart'; // Import for FaceDetection class

/// Memory management utility for face data caching
class FaceDataMemoryManager {
  static final FaceDataMemoryManager _instance = FaceDataMemoryManager._internal();
  factory FaceDataMemoryManager() => _instance;
  static FaceDataMemoryManager get instance => _instance;
  FaceDataMemoryManager._internal();

  Timer? _memoryMonitorTimer;
  final Set<String> _activeMediaIds = <String>{};
  final Set<String> _recentlyAccessedIds = <String>{};
  DateTime? _lastCleanup;
  
  // [CACHE] GLOBAL FACE DATA CACHE for overlay persistence
  final Map<String, Map<int, List<FaceDetection>>> _globalFaceCache = {};
  final Map<String, Map<String, List<FaceDetection>>> _globalStoredFaceCache = {};
  
  // Memory thresholds (in MB)
  static const int maxCacheMemoryMB = 50; // Reduced from 100
  static const int cleanupTriggerMemoryMB = 30; // Reduced from 80
  static const Duration cleanupInterval = Duration(minutes: 2); // Reduced from 5
  static const Duration accessTrackingWindow = Duration(minutes: 5); // Reduced from 10

  /// Store face data globally for overlay persistence
  void storeFaceData(String mediaId, Map<int, List<FaceDetection>> memoryCache, Map<String, List<FaceDetection>> storedFaces) {
    _globalFaceCache[mediaId] = Map.from(memoryCache);
    _globalStoredFaceCache[mediaId] = Map.from(storedFaces);
    
    if (kDebugMode) {
      final totalFaces = memoryCache.values.fold(0, (sum, faces) => sum + faces.length);
      print('[CACHE] GLOBAL CACHE STORE: Stored $totalFaces faces for media $mediaId');
      print('[CACHE] GLOBAL CACHE STORE: Cache now contains ${_globalFaceCache.keys.length} media entries: ${_globalFaceCache.keys.toList()}');
    }
  }
  
  /// Retrieve face data from global cache
  Map<int, List<FaceDetection>>? getMemoryCache(String mediaId) {
    final result = _globalFaceCache[mediaId];
    if (kDebugMode) {
      print('[CACHE] GLOBAL CACHE GET: Requested $mediaId, found: ${result != null} (cache has ${_globalFaceCache.keys.length} entries)');
    }
    return result;
  }
  
  /// Retrieve stored face data from global cache
  Map<String, List<FaceDetection>>? getStoredFaces(String mediaId) {
    final result = _globalStoredFaceCache[mediaId];
    if (kDebugMode) {
      print('[CACHE] GLOBAL CACHE GET STORED: Requested $mediaId, found: ${result != null}');
    }
    return result;
  }
  
  /// Check if face data exists in global cache
  bool hasFaceData(String mediaId) {
    final hasData = _globalFaceCache.containsKey(mediaId) && _globalFaceCache[mediaId]!.isNotEmpty;
    if (kDebugMode) {
      print('[CACHE] GLOBAL CACHE CHECK: $mediaId has data: $hasData (cache keys: ${_globalFaceCache.keys.toList()})');
    }
    return hasData;
  }

  /// Clear face data for a specific media ID (when switching videos)
  void clearMediaData(String mediaId) {
    _globalFaceCache.remove(mediaId);
    _globalStoredFaceCache.remove(mediaId);
    _activeMediaIds.remove(mediaId);
    _recentlyAccessedIds.remove(mediaId);
    
    if (kDebugMode) {
      print('[CACHE] GLOBAL CACHE CLEAR: Cleared all data for media $mediaId');
      print('[CACHE] GLOBAL CACHE CLEAR: Cache now contains ${_globalFaceCache.keys.length} media entries: ${_globalFaceCache.keys.toList()}');
    }
  }

  /// Initialize memory monitoring
  void initialize(Ref ref) {
    if (_memoryMonitorTimer != null) return;

    _memoryMonitorTimer = Timer.periodic(cleanupInterval, (_) {
      _performMemoryCleanup(ref);
    });

    if (kDebugMode) {
      print('[MEMORY] FaceDataMemoryManager initialized');
    }
  }

  /// Register a media ID as actively being viewed
  void markMediaActive(String mediaId) {
    _activeMediaIds.add(mediaId);
    _recentlyAccessedIds.add(mediaId);
    
    if (kDebugMode) {
      print('📱 Media $mediaId marked as active (${_activeMediaIds.length} active)');
    }
  }

  /// Unregister a media ID as no longer being viewed
  void markMediaInactive(String mediaId) {
    _activeMediaIds.remove(mediaId);
    
    if (kDebugMode) {
      print('📱 Media $mediaId marked as inactive (${_activeMediaIds.length} active)');
    }
  }

  /// Get estimated memory usage of face cache
  Future<double> getEstimatedMemoryUsageMB() async {
    // Estimate based on typical face data size
    // Average face detection result: ~1KB per face
    // Average video: ~50-100 faces
    // Estimated memory per media item: ~100KB
    
    try {
      if (Platform.isAndroid || Platform.isIOS) {
        // On mobile, we can get more accurate memory info
        return _getEstimatedCacheMemory();
      } else {
        // On desktop/web, use rough estimation
        return _getEstimatedCacheMemory();
      }
    } catch (e) {
      if (kDebugMode) {
        print('⚠️ Memory estimation failed: $e');
      }
      return 0.0;
    }
  }

  double _getEstimatedCacheMemory() {
    // Rough estimation: 100KB per cached media item
    final estimatedMB = (_activeMediaIds.length + _recentlyAccessedIds.length) * 0.1;
    return estimatedMB;
  }

  /// Perform memory cleanup if needed
  Future<void> _performMemoryCleanup(Ref ref) async {
    final currentMemoryMB = await getEstimatedMemoryUsageMB();
    
    if (currentMemoryMB > cleanupTriggerMemoryMB || _shouldPerformRoutineCleanup()) {
      await _cleanupUnusedFaceData(ref);
      _lastCleanup = DateTime.now();
      
      if (kDebugMode) {
        print('🧹 Memory cleanup performed. Estimated usage: ${currentMemoryMB.toStringAsFixed(1)}MB');
      }
    }
  }

  bool _shouldPerformRoutineCleanup() {
    if (_lastCleanup == null) return true;
    return DateTime.now().difference(_lastCleanup!) > cleanupInterval;
  }

  /// Clean up unused face data from cache
  Future<void> _cleanupUnusedFaceData(Ref ref) async {
    final cache = ref.read(faceDataCacheProvider);
    
    // Remove access tracking for old entries
    _recentlyAccessedIds.removeWhere((id) {
      // Keep only recently accessed items (within tracking window)
      return !_activeMediaIds.contains(id);
    });

    // Get list of cached media IDs that are not active or recently accessed
    final cachedIds = cache.cachedMediaIds;
    final unusedIds = cachedIds
        .where((id) => !_activeMediaIds.contains(id) && !_recentlyAccessedIds.contains(id))
        .toList();

    // Clean up unused face data
    for (final mediaId in unusedIds) {
      cache.remove(mediaId);
      if (kDebugMode) {
        print('🧹 Cleaned up cached face data for media: $mediaId');
      }
    }

    if (kDebugMode && unusedIds.isNotEmpty) {
      print('🧹 Memory cleanup: Removed ${unusedIds.length} unused items. Cache size now: ${cache.size}, Total faces: ${cache.totalFaceCount}');
    }
  }

  /// Force immediate cleanup (useful when switching videos)
  Future<void> forceCleanup(Ref ref) async {
    await _cleanupUnusedFaceData(ref);
    _lastCleanup = DateTime.now();
    
    final cache = ref.read(faceDataCacheProvider);
    if (kDebugMode) {
      print('🧹 FORCE CLEANUP: Cache size: ${cache.size}, Total faces: ${cache.totalFaceCount}');
    }
  }

  /// Get memory statistics
  Future<Map<String, dynamic>> getMemoryStats(Ref ref) async {
    final cache = ref.read(faceDataCacheProvider);
    final memoryMB = await getEstimatedMemoryUsageMB();
    
    return {
      'cache_size': cache.size,
      'total_faces_cached': cache.totalFaceCount,
      'active_media_count': _activeMediaIds.length,
      'recently_accessed_count': _recentlyAccessedIds.length,
      'estimated_memory_mb': memoryMB,
      'max_memory_mb': maxCacheMemoryMB,
      'memory_usage_percent': (memoryMB / maxCacheMemoryMB * 100).clamp(0, 100),
      'last_cleanup': _lastCleanup?.toIso8601String(),
    };
  }

  /// Check if memory usage is within acceptable limits
  Future<bool> isMemoryUsageHealthy(Ref ref) async {
    final memoryMB = await getEstimatedMemoryUsageMB();
    return memoryMB <= maxCacheMemoryMB;
  }

  /// Dispose and cleanup resources
  void dispose() {
    _memoryMonitorTimer?.cancel();
    _memoryMonitorTimer = null;
    _activeMediaIds.clear();
    _recentlyAccessedIds.clear();
    
    if (kDebugMode) {
      print('[MEMORY] FaceDataMemoryManager disposed');
    }
  }
}

/// Memory manager provider
final faceDataMemoryManagerProvider = Provider<FaceDataMemoryManager>((ref) {
  final manager = FaceDataMemoryManager();
  manager.initialize(ref);
  
  // Cleanup when provider is disposed
  ref.onDispose(() {
    manager.dispose();
  });
  
  return manager;
});

/// Memory statistics provider
final faceDataMemoryStatsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final manager = ref.watch(faceDataMemoryManagerProvider);
  return await manager.getMemoryStats(ref);
});

/// Memory health check provider
final faceDataMemoryHealthProvider = FutureProvider<bool>((ref) async {
  final manager = ref.watch(faceDataMemoryManagerProvider);
  return await manager.isMemoryUsageHealthy(ref);
});

/// Enhanced AutoFaceLoader with memory management
class EnhancedAutoFaceLoader {
  /// Load faces for media with memory tracking
  static void loadFacesForMedia(WidgetRef ref, String mediaId) {
    // Mark media as active for memory management
    final memoryManager = ref.read(faceDataMemoryManagerProvider);
    memoryManager.markMediaActive(mediaId);
    
    // Load faces using existing mechanism
    final notifier = ref.read(mediaFaceDataProvider(mediaId).notifier);
    notifier.loadFaces();
  }

  /// Clear faces for media with memory tracking
  static void clearFacesForMedia(WidgetRef ref, String mediaId) {
    // Mark media as inactive for memory management
    final memoryManager = ref.read(faceDataMemoryManagerProvider);
    memoryManager.markMediaInactive(mediaId);
    
    // Clear faces using existing mechanism  
    final notifier = ref.read(mediaFaceDataProvider(mediaId).notifier);
    notifier.clearFaces();
  }

  /// Force memory cleanup
  static Future<void> forceMemoryCleanup(WidgetRef ref) async {
    final memoryManager = ref.read(faceDataMemoryManagerProvider);
    // Note: WidgetRef is a subtype of Ref, so this should work
    await memoryManager.forceCleanup(ref as Ref);
  }
}
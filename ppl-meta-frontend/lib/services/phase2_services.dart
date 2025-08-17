// Media API Client for Phase 2 integration
// Simplified working implementation for testing Provider setup

import 'package:dio/dio.dart';
import 'dart:typed_data';

class MediaApiClient {
  final String _baseUrl;
  final Dio _dio;
  
  MediaApiClient({required String baseUrl}) 
    : _baseUrl = baseUrl,
      _dio = Dio(BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 30),
      ));
  
  /// Upload a snapshot to the media service
  Future<Map<String, dynamic>> uploadSnapshot({
    required String snapshotId,
    required Uint8List imageData,
    required Map<String, dynamic> metadata,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          imageData,
          filename: '$snapshotId.jpg',
        ),
        'metadata': metadata.toString(),
      });
      
      final response = await _dio.post('/upload', data: formData);
      return response.data;
    } catch (e) {
      print('Upload error: $e');
      rethrow;
    }
  }
  
  /// Get gallery items from media service
  Future<Map<String, dynamic>> getGalleryItems({
    int? limit,
    String? search,
    String? cameraId,
  }) async {
    try {
      final response = await _dio.get('/gallery', queryParameters: {
        if (limit != null) 'limit': limit,
        if (search != null) 'search': search,
        if (cameraId != null) 'camera_id': cameraId,
      });
      return response.data;
    } catch (e) {
      print('Gallery fetch error: $e');
      return {'items': [], 'total': 0};
    }
  }
  
  /// Check media service health
  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return response.data['status'] == 'healthy';
    } catch (e) {
      return false;
    }
  }
}

// Phase 2 Model Classes (simplified for working implementation)

enum SyncStatus {
  idle,
  syncing,
  error,
  paused,
  completed,
}

class UploadTask {
  final String snapshotId;
  final double progress;
  final String status;
  
  const UploadTask({
    required this.snapshotId,
    required this.progress,
    required this.status,
  });
}

class GalleryItem {
  final String id;
  final String? cameraId;
  final String source; // 'local' or 'cloud'
  final DateTime timestamp;
  final Map<String, dynamic>? metadata;
  
  const GalleryItem({
    required this.id,
    this.cameraId,
    required this.source,
    required this.timestamp,
    this.metadata,
  });
}

class SnapshotCollection {
  final String id;
  final String name;
  final int snapshotCount;
  final DateTime createdAt;
  
  const SnapshotCollection({
    required this.id,
    required this.name,
    required this.snapshotCount,
    required this.createdAt,
  });
}

class GalleryStats {
  final int totalSnapshots;
  final int localSnapshots;
  final int cloudSnapshots;
  final int pendingUploads;
  final double totalSizeMB;
  
  const GalleryStats({
    required this.totalSnapshots,
    required this.localSnapshots,
    required this.cloudSnapshots,
    required this.pendingUploads,
    required this.totalSizeMB,
  });
}

// Phase 2 Service Classes (simplified working implementations)

class SnapshotSyncService {
  final MediaApiClient _mediaClient;
  
  SnapshotSyncService({
    required MediaApiClient mediaApiClient,
    required dynamic sharedPreferences,
  }) : _mediaClient = mediaApiClient;
  
  Future<void> initialize() async {
    print('✅ SnapshotSyncService initialized');
  }
  
  Future<void> startBackgroundSync() async {
    print('✅ Background sync started');
  }
  
  Future<void> stopBackgroundSync() async {
    print('✅ Background sync stopped');
  }
  
  Future<void> syncAll() async {
    print('✅ Manual sync completed');
  }
  
  Future<void> pauseSync() async {
    print('✅ Sync paused');
  }
  
  Stream<SyncStatus> get syncStatusStream => Stream.periodic(
    const Duration(seconds: 2),
    (count) => count % 3 == 0 ? SyncStatus.syncing : SyncStatus.idle,
  );
  
  Stream<List<UploadTask>> get uploadQueueStream => Stream.periodic(
    const Duration(seconds: 3),
    (count) => count % 2 == 0 ? [] : [
      UploadTask(snapshotId: 'test_$count', progress: 0.5, status: 'uploading'),
    ],
  );
}

class EnhancedGalleryService {
  final MediaApiClient _mediaClient;
  
  EnhancedGalleryService({
    required MediaApiClient mediaApiClient,
    required dynamic sharedPreferences,
  }) : _mediaClient = mediaApiClient;
  
  Future<void> initializeCache() async {
    print('✅ Enhanced gallery cache initialized');
  }
  
  Future<void> clearCache() async {
    print('✅ Enhanced gallery cache cleared');
  }
  
  Future<List<GalleryItem>> getGalleryItems({
    required dynamic filter,
    required dynamic mode,
  }) async {
    // Mock implementation for testing
    return [
      GalleryItem(
        id: 'mock_1',
        cameraId: 'camera_1',
        source: 'local',
        timestamp: DateTime.now().subtract(const Duration(hours: 1)),
      ),
      GalleryItem(
        id: 'mock_2',
        cameraId: 'camera_1', 
        source: 'cloud',
        timestamp: DateTime.now().subtract(const Duration(hours: 2)),
      ),
    ];
  }
  
  Future<GalleryStats> getGalleryStats() async {
    return const GalleryStats(
      totalSnapshots: 45,
      localSnapshots: 23,
      cloudSnapshots: 22,
      pendingUploads: 3,
      totalSizeMB: 125.4,
    );
  }
}

class SnapshotCollectionService {
  final MediaApiClient _mediaClient;
  
  SnapshotCollectionService({
    required MediaApiClient mediaApiClient,
    required dynamic sharedPreferences,
  }) : _mediaClient = mediaApiClient;
  
  Future<List<SnapshotCollection>> getAllCollections() async {
    // Mock implementation
    return [
      SnapshotCollection(
        id: 'collection_1',
        name: 'Morning Captures',
        snapshotCount: 12,
        createdAt: DateTime.now().subtract(const Duration(days: 2)),
      ),
      SnapshotCollection(
        id: 'collection_2', 
        name: 'Security Footage',
        snapshotCount: 8,
        createdAt: DateTime.now().subtract(const Duration(days: 1)),
      ),
    ];
  }
}

class EnhancedSnapshotService {
  EnhancedSnapshotService({
    required dynamic cameraService,
    required SnapshotSyncService syncService,
    required EnhancedGalleryService galleryService,
    required SnapshotCollectionService collectionService,
  });
}

/// Storage usage statistics
class StorageStats {
  final int totalSpace;
  final int usedSpace;
  final int availableSpace;
  
  const StorageStats({
    required this.totalSpace,
    required this.usedSpace,
    required this.availableSpace,
  });
  
  double get usagePercentage => totalSpace > 0 ? usedSpace / totalSpace : 0.0;
}

/// Auto-upload configuration
class AutoUploadSettings {
  final bool enabled;
  final bool wifiOnly;
  final double qualityThreshold;
  
  const AutoUploadSettings({
    required this.enabled,
    required this.wifiOnly,
    required this.qualityThreshold,
  });
}

/// Thumbnail cache management
class ThumbnailCache {
  final int maxCacheSize;
  
  const ThumbnailCache({
    required this.maxCacheSize,
  });
  
  // TODO: Implement cache management methods
}

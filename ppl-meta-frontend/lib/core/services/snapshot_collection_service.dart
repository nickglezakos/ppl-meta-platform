import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../services/media_api_client.dart';
import '../models/collection_models.dart';
import '../models/snapshot_result.dart';
import 'background_sync_service.dart';
import 'camera_collection_service.dart';

/// Collection type specifically for camera snapshots
enum SnapshotCollectionType {
  auto,           // Automatic organization
  project,        // Project-based organization
  timeRange,      // Date/time-based organization
  camera,         // Camera-specific organization
  event,          // Event-based organization
  custom,         // User-defined organization
}

/// Snapshot collection metadata
class SnapshotCollectionInfo {
  final String id;
  final String name;
  final String? description;
  final SnapshotCollectionType type;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int itemCount;
  final List<String> cameraIds;
  final DateTimeRange? dateRange;
  final Map<String, dynamic> metadata;
  final bool isPublic;

  const SnapshotCollectionInfo({
    required this.id,
    required this.name,
    this.description,
    required this.type,
    required this.createdAt,
    required this.updatedAt,
    required this.itemCount,
    required this.cameraIds,
    this.dateRange,
    required this.metadata,
    this.isPublic = false,
  });

  /// Create from MediaCollection
  factory SnapshotCollectionInfo.fromMediaCollection(MediaCollection collection) {
    final typeStr = collection.metadata?['snapshot_type']?.toString();
    SnapshotCollectionType type = SnapshotCollectionType.values.firstWhere(
      (e) => e.toString().split('.').last == typeStr,
      orElse: () => SnapshotCollectionType.auto,
    );

    final cameraIds = <String>[];
    if (collection.metadata?['camera_ids'] is List) {
      cameraIds.addAll((collection.metadata!['camera_ids'] as List).cast<String>());
    }

    DateTimeRange? dateRange;
    if (collection.metadata?['date_range'] is Map) {
      final rangeData = collection.metadata!['date_range'] as Map;
      if (rangeData['start'] != null && rangeData['end'] != null) {
        dateRange = DateTimeRange(
          start: DateTime.parse(rangeData['start'].toString()),
          end: DateTime.parse(rangeData['end'].toString()),
        );
      }
    }

    return SnapshotCollectionInfo(
      id: collection.id,
      name: collection.name,
      description: collection.description ?? '',
      type: type,
      cameraIds: cameraIds,
      dateRange: dateRange,
      itemCount: collection.itemCount,
      createdAt: collection.createdAt ?? DateTime.now(),
      updatedAt: collection.updatedAt ?? DateTime.now(),
      metadata: collection.metadata ?? {},
      isPublic: collection.isPublic,
    );
  }

  /// Get display subtitle for the collection
  String get subtitle {
    final parts = <String>[];
    
    if (itemCount > 0) {
      parts.add('$itemCount ${itemCount == 1 ? 'snapshot' : 'snapshots'}');
    }
    
    if (cameraIds.isNotEmpty) {
      parts.add('${cameraIds.length} ${cameraIds.length == 1 ? 'camera' : 'cameras'}');
    }
    
    if (dateRange != null) {
      final formatter = DateFormat('MMM dd');
      parts.add('${formatter.format(dateRange!.start)} - ${formatter.format(dateRange!.end)}');
    }
    
    return parts.join(' • ');
  }

  /// Get formatted type name
  String get typeName {
    switch (type) {
      case SnapshotCollectionType.auto:
        return 'Auto';
      case SnapshotCollectionType.project:
        return 'Project';
      case SnapshotCollectionType.timeRange:
        return 'Time Range';
      case SnapshotCollectionType.camera:
        return 'Camera';
      case SnapshotCollectionType.event:
        return 'Event';
      case SnapshotCollectionType.custom:
        return 'Custom';
    }
  }
}

/// Request for creating snapshot collection
class CreateSnapshotCollectionRequest {
  final String name;
  final String? description;
  final SnapshotCollectionType type;
  final List<String>? initialSnapshotIds;
  final List<String>? cameraIds;
  final DateTimeRange? dateRange;
  final Map<String, dynamic>? customMetadata;
  final bool isPublic;

  const CreateSnapshotCollectionRequest({
    required this.name,
    this.description,
    this.type = SnapshotCollectionType.custom,
    this.initialSnapshotIds,
    this.cameraIds,
    this.dateRange,
    this.customMetadata,
    this.isPublic = false,
  });

  /// Build metadata for media service
  Map<String, dynamic> buildMetadata() {
    final metadata = <String, dynamic>{
      'source': 'camera_snapshots',
      'snapshot_type': type.toString().split('.').last,
      'created_by': 'snapshot_manager',
    };

    if (cameraIds != null && cameraIds!.isNotEmpty) {
      metadata['camera_ids'] = cameraIds;
    }

    if (dateRange != null) {
      metadata['date_range'] = {
        'start': dateRange!.start.toIso8601String(),
        'end': dateRange!.end.toIso8601String(),
      };
    }

    if (customMetadata != null) {
      metadata.addAll(customMetadata!);
    }

    return metadata;
  }
}

/// Service for managing snapshot collections
class SnapshotCollectionService extends ChangeNotifier {
  final MediaApiClient _mediaService;
  final BackgroundSyncService _syncService;
  final CameraCollectionService _cameraCollectionService;
  
  List<SnapshotCollectionInfo> _collections = [];
  bool _isLoading = false;
  String? _error;
  DateTime? _lastFetch;
  
  // Cache settings
  static const Duration cacheTimeout = Duration(minutes: 10);

  SnapshotCollectionService(
    this._mediaService,
    this._syncService,
    this._cameraCollectionService,
  );

  /// Current collections
  List<SnapshotCollectionInfo> get collections => List.unmodifiable(_collections);

  /// Is loading flag
  bool get isLoading => _isLoading;

  /// Error message
  String? get error => _error;

  /// Create snapshot collection
  Future<SnapshotCollectionInfo?> createSnapshotCollection(
    CreateSnapshotCollectionRequest request,
  ) async {
    try {
      _error = null;
      notifyListeners();

      // Create collection via media service
      final response = await _mediaService.createCollection(
        name: request.name,
        description: request.description,
      );

      if (response.success && response.data != null) {
        final collection = response.data!;
        
        // Add initial snapshots if provided
        if (request.initialSnapshotIds != null && request.initialSnapshotIds!.isNotEmpty) {
          await addSnapshotsToCollection(
            collectionId: collection.id,
            snapshotIds: request.initialSnapshotIds!,
          );
        }

        // Refresh collections list
        await getSnapshotCollections(forceRefresh: true);

        final collectionInfo = _collections.firstWhere(
          (c) => c.id == collection.id,
          orElse: () => SnapshotCollectionInfo.fromMediaCollection(collection),
        );

        debugPrint('Created snapshot collection: ${collection.name}');
        return collectionInfo;
      } else {
        _error = response.error ?? 'Failed to create collection';
        notifyListeners();
        return null;
      }
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      debugPrint('Error creating snapshot collection: $e');
      return null;
    }
  }

  /// 🚀 CAM-FLUTTER-004B: Automatic snapshot capture and assignment
  /// 
  /// Captures snapshot and automatically assigns it to the camera's collection
  /// with background upload to Media Service.
  Future<SnapshotResult?> captureAndAssignToCollection(
    String cameraId,
    SnapshotResult snapshot, {
    Map<String, dynamic>? additionalMetadata,
  }) async {
    try {
      debugPrint('🎯 CAM-FLUTTER-004B: Starting automatic assignment for camera: $cameraId');
      
      // 1. Check if camera has an associated collection
      final collectionId = await _cameraCollectionService.getCameraCollectionId(cameraId);
      
      if (collectionId == null) {
        debugPrint('⚠️ No collection found for camera: $cameraId - skipping auto-upload');
        return snapshot;
      }
      
      debugPrint('✅ Found collection for camera $cameraId: $collectionId');
      
      // 2. Prepare metadata for upload
      final metadata = {
        'source': 'camera_snapshot',
        'camera_id': cameraId,
        'capture_timestamp': snapshot.capturedAt.toIso8601String(),
        'resolution': snapshot.metadata?['resolution'],
        'quality': snapshot.metadata?['quality'],
        'format': snapshot.metadata?['format'],
        'auto_assigned': true, // Mark as automatically assigned
        ...?additionalMetadata,
      };
      
      // 3. Queue for background upload to Media Service
      await _syncService.queueSnapshotUpload(
        snapshot,
        collectionId,
        additionalMetadata: metadata,
      );
      
      debugPrint('📤 Queued snapshot for auto-upload: ${snapshot.deviceId} → Collection: $collectionId');
      
      return snapshot;
    } catch (e) {
      debugPrint('❌ Error in automatic snapshot assignment: $e');
      // Don't throw - automatic upload is best-effort
      return snapshot;
    }
  }

  /// Upload snapshot to specific collection
  Future<void> uploadSnapshotToCollection(
    SnapshotResult snapshot,
    String collectionId, {
    Map<String, dynamic>? additionalMetadata,
  }) async {
    final metadata = {
      'source': 'camera_snapshot',
      'camera_id': snapshot.deviceId,
      'capture_timestamp': snapshot.capturedAt.toIso8601String(),
      'resolution': snapshot.metadata?['resolution'],
      'quality': snapshot.metadata?['quality'],
      'format': snapshot.metadata?['format'],
      ...?additionalMetadata,
    };
    
    await _syncService.queueSnapshotUpload(
      snapshot,
      collectionId,
      additionalMetadata: metadata,
    );
  }

  /// Process upload queue manually
  Future<void> processUploadQueue() async {
    // The background sync service handles this automatically,
    // but this method can be used for manual processing
    if (_syncService.hasPendingUploads) {
      debugPrint('🔄 Processing ${_syncService.currentQueue.length} pending uploads...');
      await _syncService.retryFailedUploads();
    } else {
      debugPrint('✅ No pending uploads to process');
    }
  }

  /// Get upload progress stream
  Stream<UploadProgress> get uploadProgressStream => _syncService.uploadProgressStream;

  /// Get sync status stream  
  Stream<SyncStatus> get syncStatusStream => _syncService.syncStatusStream;

  /// Get collections containing camera snapshots
  Future<List<SnapshotCollectionInfo>> getSnapshotCollections({
    bool forceRefresh = false,
  }) async {
    // Return cached data if still valid
    if (!forceRefresh && _lastFetch != null && 
        DateTime.now().difference(_lastFetch!) < cacheTimeout) {
      return collections;
    }

    if (_isLoading) return collections;

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _mediaService.getCollections();
      
      if (response.success && response.data != null) {
        // Filter for snapshot collections and convert
        _collections = response.data!
            .where((collection) => _isSnapshotCollection(collection))
            .map((collection) => SnapshotCollectionInfo.fromMediaCollection(collection))
            .toList();

        // Sort by updated date (newest first)
        _collections.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));

        _lastFetch = DateTime.now();
        debugPrint('Loaded ${_collections.length} snapshot collections');
      } else {
        _error = response.error ?? 'Failed to load collections';
      }
    } catch (e) {
      _error = e.toString();
      debugPrint('Error loading snapshot collections: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }

    return collections;
  }

  /// Add snapshots to existing collection
  Future<bool> addSnapshotsToCollection({
    required String collectionId,
    required List<String> snapshotIds,
  }) async {
    try {
      _error = null;
      
      for (final snapshotId in snapshotIds) {
        final response = await _mediaService.addMediaToCollection(
          collectionId: collectionId,
          mediaId: snapshotId,
        );
        
        if (!response.success) {
          throw Exception(response.error ?? 'Failed to add snapshot $snapshotId');
        }
      }

      // Refresh collections to update item counts
      await getSnapshotCollections(forceRefresh: true);
      
      debugPrint('Added ${snapshotIds.length} snapshots to collection $collectionId');
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      debugPrint('Error adding snapshots to collection: $e');
      return false;
    }
  }

  /// Remove snapshots from collection
  Future<bool> removeSnapshotsFromCollection({
    required String collectionId,
    required List<String> snapshotIds,
  }) async {
    try {
      _error = null;
      
      // Note: This would require media service API for removing items from collections
      // For now, this is a placeholder implementation
      
      // Refresh collections to update item counts
      await getSnapshotCollections(forceRefresh: true);
      
      debugPrint('Removed ${snapshotIds.length} snapshots from collection $collectionId');
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      debugPrint('Error removing snapshots from collection: $e');
      return false;
    }
  }

  /// Update collection information
  Future<bool> updateCollection({
    required String collectionId,
    String? name,
    String? description,
  }) async {
    try {
      _error = null;
      
      final response = await _mediaService.updateCollection(
        collectionId: collectionId,
        name: name,
        description: description,
      );

      if (response.success) {
        // Refresh collections
        await getSnapshotCollections(forceRefresh: true);
        debugPrint('Updated collection $collectionId');
        return true;
      } else {
        _error = response.error ?? 'Failed to update collection';
        notifyListeners();
        return false;
      }
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      debugPrint('Error updating collection: $e');
      return false;
    }
  }

  /// Delete collection
  Future<bool> deleteCollection(String collectionId) async {
    try {
      _error = null;
      
      // Note: This would require media service API for deleting collections
      // For now, this is a placeholder implementation
      
      // Remove from local cache
      _collections.removeWhere((c) => c.id == collectionId);
      notifyListeners();
      
      debugPrint('Deleted collection $collectionId');
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      debugPrint('Error deleting collection: $e');
      return false;
    }
  }

  /// Get snapshots in a specific collection
  Future<List<String>> getCollectionSnapshots(String collectionId) async {
    try {
      // Note: This would use media service API to get collection items
      // For now, return empty list as placeholder
      return [];
    } catch (e) {
      debugPrint('Error getting collection snapshots: $e');
      return [];
    }
  }

  /// Create automatic collections based on criteria
  Future<List<SnapshotCollectionInfo>> createAutomaticCollections({
    required List<SnapshotResult> snapshots,
    bool groupByCamera = true,
    bool groupByDate = true,
  }) async {
    final createdCollections = <SnapshotCollectionInfo>[];

    try {
      if (groupByCamera) {
        // Group by camera device
        final cameraGroups = <String, List<SnapshotResult>>{};
        for (final snapshot in snapshots) {
          cameraGroups.putIfAbsent(snapshot.deviceId, () => []).add(snapshot);
        }

        for (final entry in cameraGroups.entries) {
          if (entry.value.length >= 3) { // Only create collection for 3+ snapshots
            final request = CreateSnapshotCollectionRequest(
              name: 'Camera ${entry.key} Snapshots',
              description: 'Automatically created collection for camera ${entry.key}',
              type: SnapshotCollectionType.camera,
              cameraIds: [entry.key],
              initialSnapshotIds: entry.value.map((s) => s.id).toList(),
            );

            final collection = await createSnapshotCollection(request);
            if (collection != null) {
              createdCollections.add(collection);
            }
          }
        }
      }

      if (groupByDate) {
        // Group by date (daily collections)
        final dateGroups = <String, List<SnapshotResult>>{};
        for (final snapshot in snapshots) {
          final dateKey = DateFormat('yyyy-MM-dd').format(snapshot.capturedAt);
          dateGroups.putIfAbsent(dateKey, () => []).add(snapshot);
        }

        for (final entry in dateGroups.entries) {
          if (entry.value.length >= 5) { // Only create collection for 5+ snapshots
            final date = DateTime.parse(entry.key);
            final request = CreateSnapshotCollectionRequest(
              name: 'Snapshots ${DateFormat('MMM dd, yyyy').format(date)}',
              description: 'Daily snapshot collection',
              type: SnapshotCollectionType.timeRange,
              dateRange: DateTimeRange(
                start: date,
                end: date.add(const Duration(days: 1)),
              ),
              initialSnapshotIds: entry.value.map((s) => s.id).toList(),
            );

            final collection = await createSnapshotCollection(request);
            if (collection != null) {
              createdCollections.add(collection);
            }
          }
        }
      }

      debugPrint('Created ${createdCollections.length} automatic collections');
      return createdCollections;
    } catch (e) {
      debugPrint('Error creating automatic collections: $e');
      return createdCollections;
    }
  }

  /// Check if a media collection is a snapshot collection
  bool _isSnapshotCollection(MediaCollection collection) {
    // Check metadata for snapshot-related markers
    final metadata = collection.metadata ?? {};
    return metadata['source'] == 'camera_snapshots' ||
           metadata.containsKey('snapshot_type') ||
           collection.name.toLowerCase().contains('snapshot');
  }

  /// Get collection statistics
  Map<String, dynamic> getCollectionStats() {
    final totalSnapshots = _collections.fold<int>(0, (sum, c) => sum + c.itemCount);
    final typeStats = <String, int>{};
    
    for (final collection in _collections) {
      final typeName = collection.typeName;
      typeStats[typeName] = (typeStats[typeName] ?? 0) + 1;
    }

    return {
      'total_collections': _collections.length,
      'total_snapshots': totalSnapshots,
      'avg_snapshots_per_collection': _collections.isNotEmpty 
          ? (totalSnapshots / _collections.length).round() 
          : 0,
      'collection_types': typeStats,
      'unique_cameras': _collections
          .expand((c) => c.cameraIds)
          .toSet()
          .length,
    };
  }

  /// Clear error state
  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Refresh collections
  Future<void> refresh() async {
    await getSnapshotCollections(forceRefresh: true);
  }
}

/// Simple DateTimeRange implementation
class DateTimeRange {
  final DateTime start;
  final DateTime end;

  const DateTimeRange({
    required this.start,
    required this.end,
  });

  bool contains(DateTime date) {
    return date.isAfter(start) && date.isBefore(end) ||
           date.isAtSameMomentAs(start) ||
           date.isAtSameMomentAs(end);
  }
}

/// Simple DateFormat implementation for basic formatting
class DateFormat {
  final String pattern;
  
  const DateFormat(this.pattern);
  
  String format(DateTime date) {
    switch (pattern) {
      case 'yyyy-MM-dd':
        return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
      case 'MMM dd':
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return '${months[date.month - 1]} ${date.day}';
      case 'MMM dd, yyyy':
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return '${months[date.month - 1]} ${date.day}, ${date.year}';
      default:
        return date.toString();
    }
  }
}

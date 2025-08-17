import 'dart:async';
import 'dart:collection';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/snapshot_result.dart';
import '../../services/media_api_client.dart';

/// Background synchronization service for automatic snapshot uploads
/// 
/// Provides automatic upload of camera snapshots to their associated collections
/// with background processing, retry logic, and persistent queue management.
class BackgroundSyncService extends ChangeNotifier {
  final MediaApiClient _mediaApiClient;
  final Queue<SnapshotUploadTask> _uploadQueue = Queue();
  Timer? _uploadTimer;
  bool _isProcessing = false;
  
  /// Upload progress stream controller
  final StreamController<UploadProgress> _progressController = 
      StreamController<UploadProgress>.broadcast();
  
  /// Sync status stream controller  
  final StreamController<SyncStatus> _statusController =
      StreamController<SyncStatus>.broadcast();
  
  BackgroundSyncService(this._mediaApiClient) {
    _loadPendingUploads();
    _startPeriodicProcessing();
  }
  
  /// Stream of upload progress events
  Stream<UploadProgress> get uploadProgressStream => _progressController.stream;
  
  /// Stream of sync status changes
  Stream<SyncStatus> get syncStatusStream => _statusController.stream;
  
  /// Queue snapshot for background upload to its collection
  Future<void> queueSnapshotUpload(
    SnapshotResult snapshot, 
    String collectionId, {
    Map<String, dynamic>? additionalMetadata,
  }) async {
    final task = SnapshotUploadTask(
      id: '${snapshot.deviceId}_${snapshot.capturedAt.millisecondsSinceEpoch}',
      snapshot: snapshot,
      collectionId: collectionId,
      timestamp: DateTime.now(),
      retryCount: 0,
      metadata: {
        'source': 'camera_snapshot',
        'camera_id': snapshot.deviceId,
        'capture_timestamp': snapshot.capturedAt.toIso8601String(),
        'collection_id': collectionId,
        ...?additionalMetadata,
      },
    );
    
    _uploadQueue.add(task);
    await _savePendingUploads();
    _processUploadQueue();
    
    debugPrint('📤 Queued snapshot for upload: ${task.id} → Collection: $collectionId');
  }
  
  /// Process upload queue with retry logic
  Future<void> _processUploadQueue() async {
    if (_isProcessing || _uploadQueue.isEmpty) return;
    
    _isProcessing = true;
    _statusController.add(SyncStatus.uploading);
    
    try {
      while (_uploadQueue.isNotEmpty) {
        final task = _uploadQueue.removeFirst();
        
        try {
          await _uploadSnapshot(task);
          _progressController.add(UploadProgress(
            taskId: task.id,
            progress: 1.0,
            status: UploadStatus.completed,
          ));
          debugPrint('✅ Upload completed: ${task.id}');
        } catch (e) {
          await _handleUploadError(task, e);
        }
        
        await _savePendingUploads();
      }
      
      _statusController.add(SyncStatus.synced);
    } finally {
      _isProcessing = false;
    }
  }
  
  /// Upload snapshot to media service with collection assignment
  Future<void> _uploadSnapshot(SnapshotUploadTask task) async {
    _progressController.add(UploadProgress(
      taskId: task.id,
      progress: 0.1,
      status: UploadStatus.uploading,
    ));
    
    // Convert base64 to bytes, handling data URL prefix
    String base64String = task.snapshot.base64Image;
    if (base64String.contains(',')) {
      // Remove data URL prefix (e.g., "data:image/jpeg;base64,")
      base64String = base64String.split(',').last;
      debugPrint('🧹 Cleaned base64 string, length: ${base64String.length}');
    }
    
    try {
      final imageBytes = base64Decode(base64String);
      debugPrint('✅ Successfully decoded base64 to ${imageBytes.length} bytes');
    } catch (e) {
      debugPrint('❌ Base64 decode error: $e');
      debugPrint('❌ Base64 preview: ${base64String.substring(0, math.min(50, base64String.length))}...');
      rethrow;
    }
    
    final imageBytes = base64Decode(base64String);
    final fileName = 'snapshot_${task.snapshot.deviceId}_${task.snapshot.capturedAt.millisecondsSinceEpoch}.jpg';
    
    _progressController.add(UploadProgress(
      taskId: task.id,
      progress: 0.3,
      status: UploadStatus.uploading,
    ));
    
    // Upload to media service (without collection assignment)
    final response = await _mediaApiClient.uploadMedia(
      fileBytes: imageBytes,
      fileName: fileName,
      mimeType: 'image/jpeg',
      metadata: task.metadata,
      // Note: collectionId removed - will be assigned separately
    );
    
    _progressController.add(UploadProgress(
      taskId: task.id,
      progress: 0.6,
      status: UploadStatus.uploading,
    ));
    
    if (!response.success) {
      throw Exception('Media upload failed: ${response.error}');
    }
    
    final mediaId = response.data?.mediaId;
    if (mediaId == null) {
      throw Exception('Media upload succeeded but no media ID returned');
    }
    
    debugPrint('📤 Snapshot uploaded successfully: ${task.id} → $mediaId');
    
    // If collection ID is provided, assign the uploaded media to the collection
    if (task.collectionId != null && task.collectionId!.isNotEmpty) {
      debugPrint('📁 Assigning media $mediaId to collection ${task.collectionId}');
      
      final collectionResponse = await _mediaApiClient.bulkAddToCollection(
        collectionId: task.collectionId!,
        mediaIds: [mediaId],
      );
      
      if (!collectionResponse.success) {
        debugPrint('⚠️ Collection assignment failed: ${collectionResponse.error}');
        // Don't throw here - the upload succeeded even if collection assignment failed
      } else {
        debugPrint('✅ Media $mediaId successfully assigned to collection ${task.collectionId}');
      }
    }
    
    _progressController.add(UploadProgress(
      taskId: task.id,
      progress: 0.8,
      status: UploadStatus.uploading,
    ));
  }
  
  /// Handle upload errors with retry logic
  Future<void> _handleUploadError(SnapshotUploadTask task, dynamic error) async {
    debugPrint('❌ Upload failed for ${task.id}: $error');
    
    if (task.retryCount < 3) {
      // Retry with exponential backoff
      final retryTask = task.copyWith(
        retryCount: task.retryCount + 1,
        timestamp: DateTime.now().add(Duration(seconds: task.retryCount * 5)),
      );
      
      _uploadQueue.add(retryTask);
      
      _progressController.add(UploadProgress(
        taskId: task.id,
        progress: 0.0,
        status: UploadStatus.retrying,
        error: error.toString(),
      ));
      
      debugPrint('🔄 Scheduled retry ${task.retryCount + 1}/3 for ${task.id}');
    } else {
      // Max retries exceeded
      _progressController.add(UploadProgress(
        taskId: task.id,
        progress: 0.0,
        status: UploadStatus.failed,
        error: error.toString(),
      ));
      
      debugPrint('💥 Upload failed permanently: ${task.id}');
    }
  }
  
  /// Retry failed uploads manually
  Future<void> retryFailedUploads() async {
    debugPrint('🔄 Retrying all failed uploads...');
    _processUploadQueue();
  }
  
  /// Get current upload queue status
  List<SnapshotUploadTask> get currentQueue => List.unmodifiable(_uploadQueue);
  
  /// Check if there are pending uploads
  bool get hasPendingUploads => _uploadQueue.isNotEmpty;
  
  /// Save pending uploads to persistent storage
  Future<void> _savePendingUploads() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final taskList = _uploadQueue
          .map((task) => task.toJson())
          .toList();
      await prefs.setString('pending_uploads', jsonEncode(taskList));
    } catch (e) {
      debugPrint('Failed to save pending uploads: $e');
    }
  }
  
  /// Load pending uploads from persistent storage
  Future<void> _loadPendingUploads() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final pendingData = prefs.getString('pending_uploads');
      
      if (pendingData != null) {
        final taskList = jsonDecode(pendingData) as List;
        for (final taskData in taskList) {
          try {
            final task = SnapshotUploadTask.fromJson(taskData);
            _uploadQueue.add(task);
          } catch (e) {
            debugPrint('Failed to load upload task: $e');
          }
        }
        
        debugPrint('📂 Loaded ${_uploadQueue.length} pending uploads');
      }
    } catch (e) {
      debugPrint('Failed to load pending uploads: $e');
    }
  }
  
  /// Start periodic processing of upload queue
  void _startPeriodicProcessing() {
    _uploadTimer = Timer.periodic(const Duration(seconds: 10), (timer) {
      if (!_isProcessing && _uploadQueue.isNotEmpty) {
        _processUploadQueue();
      }
    });
  }
  
  @override
  void dispose() {
    _uploadTimer?.cancel();
    _progressController.close();
    _statusController.close();
    super.dispose();
  }
}

/// Upload task for background processing
class SnapshotUploadTask {
  final String id;
  final SnapshotResult snapshot;
  final String collectionId;
  final DateTime timestamp;
  final int retryCount;
  final Map<String, dynamic> metadata;
  
  const SnapshotUploadTask({
    required this.id,
    required this.snapshot,
    required this.collectionId,
    required this.timestamp,
    required this.retryCount,
    required this.metadata,
  });
  
  SnapshotUploadTask copyWith({
    String? id,
    SnapshotResult? snapshot,
    String? collectionId,
    DateTime? timestamp,
    int? retryCount,
    Map<String, dynamic>? metadata,
  }) {
    return SnapshotUploadTask(
      id: id ?? this.id,
      snapshot: snapshot ?? this.snapshot,
      collectionId: collectionId ?? this.collectionId,
      timestamp: timestamp ?? this.timestamp,
      retryCount: retryCount ?? this.retryCount,
      metadata: metadata ?? this.metadata,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'snapshot': snapshot.toJson(),
      'collectionId': collectionId,
      'timestamp': timestamp.toIso8601String(),
      'retryCount': retryCount,
      'metadata': metadata,
    };
  }
  
  factory SnapshotUploadTask.fromJson(Map<String, dynamic> json) {
    return SnapshotUploadTask(
      id: json['id'],
      snapshot: SnapshotResult.fromJson(json['snapshot']),
      collectionId: json['collectionId'],
      timestamp: DateTime.parse(json['timestamp']),
      retryCount: json['retryCount'] ?? 0,
      metadata: Map<String, dynamic>.from(json['metadata'] ?? {}),
    );
  }
}

/// Upload progress information
class UploadProgress {
  final String taskId;
  final double progress;
  final UploadStatus status;
  final String? error;
  
  const UploadProgress({
    required this.taskId,
    required this.progress,
    required this.status,
    this.error,
  });
}

/// Upload status enumeration
enum UploadStatus {
  queued,
  uploading,
  completed,
  failed,
  retrying,
}

/// Sync status enumeration
enum SyncStatus {
  idle,
  uploading,
  synced,
  error,
  paused,
}

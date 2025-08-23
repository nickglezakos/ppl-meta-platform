import 'dart:io';
import 'dart:convert';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'package:permission_handler/permission_handler.dart';
import '../models/camera_config.dart';
import '../../shared/models/media_item.dart';

/// Gallery service for managing captured media
class GalleryService {
  static GalleryService? _instance;
  static GalleryService get instance => _instance ??= GalleryService._();
  GalleryService._();

  late Directory _capturesDirectory;
  late File _metadataFile;
  Map<String, MediaItem> _mediaCache = {};
  bool _isInitialized = false;

  // Getters
  bool get isInitialized => _isInitialized;
  Directory get capturesDirectory => _capturesDirectory;

  /// Initialize gallery service
  Future<bool> initializeGallery() async {
    try {
      // Request storage permissions
      final storagePermission = await Permission.storage.request();
      if (storagePermission != PermissionStatus.granted) {
        // Try photos permission for newer Android versions
        final photosPermission = await Permission.photos.request();
        if (photosPermission != PermissionStatus.granted) {
          print('Storage permission not granted');
        }
      }

      // Setup captures directory
      final appDocuments = await getApplicationDocumentsDirectory();
      _capturesDirectory = Directory('${appDocuments.path}/captures');
      
      if (!await _capturesDirectory.exists()) {
        await _capturesDirectory.create(recursive: true);
      }

      // Setup metadata file
      _metadataFile = File('${_capturesDirectory.path}/metadata.json');
      
      // Load existing metadata
      await _loadMetadata();
      
      _isInitialized = true;
      return true;
    } catch (e) {
      print('Failed to initialize gallery: $e');
      return false;
    }
  }

  /// Get all media items sorted by date (newest first)
  Future<List<MediaItem>> getAllMedia({
    MediaType? filterType,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      if (!_isInitialized) {
        await initializeGallery();
      }

      // Scan directory for media files
      await _scanDirectory();

      var mediaList = _mediaCache.values.toList();

      // Apply filters
      if (filterType != null) {
        mediaList = mediaList.where((item) => item.type == filterType).toList();
      }

      if (startDate != null) {
        mediaList = mediaList.where((item) => item.timestamp.isAfter(startDate)).toList();
      }

      if (endDate != null) {
        mediaList = mediaList.where((item) => item.timestamp.isBefore(endDate)).toList();
      }

      // Sort by timestamp (newest first)
      mediaList.sort((a, b) => b.timestamp.compareTo(a.timestamp));

      return mediaList;
    } catch (e) {
      print('Failed to get media: $e');
      return [];
    }
  }

  /// Get media items paginated
  Future<List<MediaItem>> getMediaPaginated({
    int page = 0,
    int limit = 20,
    MediaType? filterType,
  }) async {
    try {
      final allMedia = await getAllMedia(filterType: filterType);
      final startIndex = page * limit;
      final endIndex = (startIndex + limit).clamp(0, allMedia.length);

      if (startIndex >= allMedia.length) {
        return [];
      }

      return allMedia.sublist(startIndex, endIndex);
    } catch (e) {
      print('Failed to get paginated media: $e');
      return [];
    }
  }

  /// Add new media item to gallery
  Future<bool> addMediaItem(String filePath, {
    Map<String, dynamic>? metadata,
  }) async {
    try {
      if (!_isInitialized) {
        await initializeGallery();
      }

      final file = File(filePath);
      if (!await file.exists()) {
        return false;
      }

      // Determine media type
      final extension = path.extension(filePath).toLowerCase();
      MediaType type;
      
      if (['.jpg', '.jpeg', '.png', '.gif', '.bmp'].contains(extension)) {
        type = MediaType.photo;
      } else if (['.mp4', '.mov', '.avi', '.mkv'].contains(extension)) {
        type = MediaType.video;
      } else {
        type = MediaType.other;
      }

      // Create media item
      final mediaItem = MediaItem(
        id: path.basenameWithoutExtension(filePath),
        name: path.basename(filePath),
        path: filePath,
        type: type,
        createdAt: await file.lastModified(),
        fileSize: await file.length(),
        metadata: metadata ?? {},
      );

      // Add to cache
      _mediaCache[mediaItem.id] = mediaItem;

      // Save metadata
      await _saveMetadata();

      return true;
    } catch (e) {
      print('Failed to add media item: $e');
      return false;
    }
  }

  /// Delete media item
  Future<bool> deleteMediaItem(String mediaId) async {
    try {
      final mediaItem = _mediaCache[mediaId];
      if (mediaItem == null) {
        return false;
      }

      // Delete file
      final file = File(mediaItem.filePath);
      if (await file.exists()) {
        await file.delete();
      }

      // Remove from cache
      _mediaCache.remove(mediaId);

      // Save metadata
      await _saveMetadata();

      return true;
    } catch (e) {
      print('Failed to delete media item: $e');
      return false;
    }
  }

  /// Delete multiple media items
  Future<Map<String, bool>> deleteMultipleMedia(List<String> mediaIds) async {
    final results = <String, bool>{};
    
    for (final mediaId in mediaIds) {
      results[mediaId] = await deleteMediaItem(mediaId);
    }
    
    return results;
  }

  /// Get media item by ID
  MediaItem? getMediaItem(String mediaId) {
    return _mediaCache[mediaId];
  }

  /// Get gallery statistics
  Future<Map<String, dynamic>> getGalleryStats() async {
    try {
      final allMedia = await getAllMedia();
      
      final photos = allMedia.where((item) => item.type == MediaType.photo).toList();
      final videos = allMedia.where((item) => item.type == MediaType.video).toList();
      
      final totalSize = allMedia.fold<int>(0, (sum, item) => sum + (item.fileSize ?? 0));
      
      return {
        'totalItems': allMedia.length,
        'photos': photos.length,
        'videos': videos.length,
        'other': allMedia.length - photos.length - videos.length,
        'totalSize': totalSize,
        'totalSizeMB': (totalSize / (1024 * 1024)).toStringAsFixed(2),
        'oldestItem': allMedia.isNotEmpty ? allMedia.last.timestamp.toIso8601String() : null,
        'newestItem': allMedia.isNotEmpty ? allMedia.first.timestamp.toIso8601String() : null,
      };
    } catch (e) {
      print('Failed to get gallery stats: $e');
      return {};
    }
  }

  /// Export media item
  Future<bool> exportMediaItem(String mediaId, String destinationPath) async {
    try {
      final mediaItem = _mediaCache[mediaId];
      if (mediaItem == null) {
        return false;
      }

      final sourceFile = File(mediaItem.filePath);
      if (!await sourceFile.exists()) {
        return false;
      }

      final destinationDir = Directory(path.dirname(destinationPath));
      if (!await destinationDir.exists()) {
        await destinationDir.create(recursive: true);
      }

      await sourceFile.copy(destinationPath);
      return true;
    } catch (e) {
      print('Failed to export media item: $e');
      return false;
    }
  }

  /// Clear all media from gallery
  Future<bool> clearGallery() async {
    try {
      // Delete all files
      final entities = await _capturesDirectory.list().toList();
      
      for (final entity in entities) {
        if (entity is File && entity.path != _metadataFile.path) {
          await entity.delete();
        }
      }

      // Clear cache
      _mediaCache.clear();

      // Save empty metadata
      await _saveMetadata();

      return true;
    } catch (e) {
      print('Failed to clear gallery: $e');
      return false;
    }
  }

  /// Scan directory for media files
  Future<void> _scanDirectory() async {
    try {
      final entities = await _capturesDirectory.list().toList();
      
      for (final entity in entities) {
        if (entity is File && entity.path != _metadataFile.path) {
          final filePath = entity.path;
          final filename = path.basename(filePath);
          final id = path.basenameWithoutExtension(filePath);
          
          // Skip if already in cache
          if (_mediaCache.containsKey(id)) {
            continue;
          }

          // Add to gallery
          await addMediaItem(filePath);
        }
      }
    } catch (e) {
      print('Failed to scan directory: $e');
    }
  }

  /// Load metadata from file
  Future<void> _loadMetadata() async {
    try {
      if (!await _metadataFile.exists()) {
        return;
      }

      final content = await _metadataFile.readAsString();
      final data = json.decode(content) as Map<String, dynamic>;
      
      _mediaCache.clear();
      
      for (final entry in data.entries) {
        try {
          _mediaCache[entry.key] = MediaItem.fromJson(entry.value);
        } catch (e) {
          print('Failed to parse media item ${entry.key}: $e');
        }
      }
    } catch (e) {
      print('Failed to load metadata: $e');
    }
  }

  /// Save metadata to file
  Future<void> _saveMetadata() async {
    try {
      final data = <String, dynamic>{};
      
      for (final entry in _mediaCache.entries) {
        data[entry.key] = entry.value.toJson();
      }
      
      await _metadataFile.writeAsString(
        json.encode(data),
        flush: true,
      );
    } catch (e) {
      print('Failed to save metadata: $e');
    }
  }

  /// Clean up orphaned metadata (files that no longer exist)
  Future<void> cleanupOrphanedMetadata() async {
    try {
      final orphanedIds = <String>[];
      
      for (final entry in _mediaCache.entries) {
        final file = File(entry.value.filePath);
        if (!await file.exists()) {
          orphanedIds.add(entry.key);
        }
      }
      
      for (final id in orphanedIds) {
        _mediaCache.remove(id);
      }
      
      if (orphanedIds.isNotEmpty) {
        await _saveMetadata();
      }
    } catch (e) {
      print('Failed to cleanup orphaned metadata: $e');
    }
  }

  /// Get storage usage information
  Future<Map<String, dynamic>> getStorageInfo() async {
    try {
      final appDocuments = await getApplicationDocumentsDirectory();
      final totalSpace = await _getDirectorySize(appDocuments);
      final capturesSpace = await _getDirectorySize(_capturesDirectory);
      
      return {
        'totalAppSize': totalSpace,
        'capturesSize': capturesSpace,
        'capturesSizeMB': (capturesSpace / (1024 * 1024)).toStringAsFixed(2),
        'availableSpace': 'Unknown', // Platform-specific implementation needed
      };
    } catch (e) {
      print('Failed to get storage info: $e');
      return {};
    }
  }

  /// Calculate directory size
  Future<int> _getDirectorySize(Directory directory) async {
    try {
      int size = 0;
      
      await for (final entity in directory.list(recursive: true)) {
        if (entity is File) {
          size += await entity.length();
        }
      }
      
      return size;
    } catch (e) {
      return 0;
    }
  }
}

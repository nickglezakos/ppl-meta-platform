import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import '../core/models/collection_models.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';
import '../core/services/camera_collection_service.dart';
import 'unified_search_service.dart';

/// Service for creating and managing virtual collections
/// Provides aggregated views like "All Camera Media", "Recent Captures", etc.
class VirtualCollectionService extends ChangeNotifier {
  final MediaApiClient _mediaApiClient;
  final CameraCollectionService _cameraCollectionService;
  final UnifiedSearchService _searchService;
  final Logger _logger = Logger();

  // Cache for virtual collections
  final Map<String, List<MediaItem>> _virtualCollectionCache = {};
  DateTime? _lastCacheUpdate;
  static const Duration _cacheTimeout = Duration(minutes: 5);

  VirtualCollectionService({
    required MediaApiClient mediaApiClient,
    required CameraCollectionService cameraCollectionService,
    required UnifiedSearchService searchService,
  }) : _mediaApiClient = mediaApiClient,
       _cameraCollectionService = cameraCollectionService,
       _searchService = searchService;

  /// Get all camera media from all camera collections
  Future<List<MediaItem>> getAllCameraMedia({
    int? limit,
    String? sortBy,
    String? sortOrder,
  }) async {
    const cacheKey = 'all_camera_media';
    
    // Check cache first
    if (_isCacheValid(cacheKey)) {
      _logger.d('Returning cached all camera media');
      return _virtualCollectionCache[cacheKey]!;
    }

    try {
      _logger.i('Fetching all camera media');

      // Get all camera media using search service
      final results = await _searchService.searchCameraMedia('', filters: MediaSearchFilters(
        sortBy: sortBy ?? 'created_at',
        sortOrder: sortOrder ?? 'desc',
      ));

      // Apply limit if specified
      final limitedResults = limit != null && results.length > limit 
          ? results.take(limit).toList() 
          : results;

      // Cache results
      _virtualCollectionCache[cacheKey] = limitedResults;
      _lastCacheUpdate = DateTime.now();

      _logger.i('Retrieved ${limitedResults.length} camera media items');
      return limitedResults;
    } catch (e) {
      _logger.e('Error getting all camera media: $e');
      return [];
    }
  }

  /// Get camera media within a specific time range
  Future<List<MediaItem>> getCameraMediaByTimeRange(
    DateTime start, 
    DateTime end, {
    String? cameraId,
    int? limit,
  }) async {
    try {
      _logger.i('Fetching camera media from ${start.toIso8601String()} to ${end.toIso8601String()}');

      final filters = MediaSearchFilters(
        startDate: start,
        endDate: end,
        sortBy: 'created_at',
        sortOrder: 'desc',
      );

      final results = cameraId != null
          ? await _searchService.searchCameraMedia('', specificCameraId: cameraId, filters: filters)
          : await _searchService.searchCameraMedia('', filters: filters);

      // Apply limit if specified
      final limitedResults = limit != null && results.length > limit 
          ? results.take(limit).toList() 
          : results;

      _logger.i('Retrieved ${limitedResults.length} camera media items for time range');
      return limitedResults;
    } catch (e) {
      _logger.e('Error getting camera media by time range: $e');
      return [];
    }
  }

  /// Group camera media by date
  Future<Map<String, List<MediaItem>>> groupCameraMediaByDate({
    int? daysBack,
    String? cameraId,
  }) async {
    try {
      _logger.i('Grouping camera media by date');

      // Get date range
      final endDate = DateTime.now();
      final startDate = endDate.subtract(Duration(days: daysBack ?? 30));

      // Get camera media for the range
      final allMedia = await getCameraMediaByTimeRange(
        startDate, 
        endDate, 
        cameraId: cameraId,
      );

      // Group by date
      final groupedMedia = <String, List<MediaItem>>{};
      
      for (final item in allMedia) {
        final dateKey = _formatDateKey(item.createdAt);
        groupedMedia.putIfAbsent(dateKey, () => []).add(item);
      }

      // Sort each day's items by time (newest first)
      for (final dayItems in groupedMedia.values) {
        dayItems.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      }

      _logger.i('Grouped camera media into ${groupedMedia.length} days');
      return groupedMedia;
    } catch (e) {
      _logger.e('Error grouping camera media by date: $e');
      return {};
    }
  }

  /// Get recent camera captures (last 24 hours)
  Future<List<MediaItem>> getRecentCameraCaptures({
    int? limit,
  }) async {
    const cacheKey = 'recent_camera_captures';
    
    // Check cache (shorter timeout for recent items)
    if (_isCacheValid(cacheKey, timeout: const Duration(minutes: 2))) {
      _logger.d('Returning cached recent camera captures');
      return _virtualCollectionCache[cacheKey]!;
    }

    try {
      _logger.i('Fetching recent camera captures');

      final endDate = DateTime.now();
      final startDate = endDate.subtract(const Duration(hours: 24));

      final results = await getCameraMediaByTimeRange(
        startDate, 
        endDate, 
        limit: limit ?? 50,
      );

      // Cache results
      _virtualCollectionCache[cacheKey] = results;
      _lastCacheUpdate = DateTime.now();

      _logger.i('Retrieved ${results.length} recent camera captures');
      return results;
    } catch (e) {
      _logger.e('Error getting recent camera captures: $e');
      return [];
    }
  }

  /// Get high resolution camera captures
  Future<List<MediaItem>> getHighResolutionCaptures({
    int? minFileSize,
    int? limit,
    String? cameraId,
  }) async {
    try {
      _logger.i('Fetching high resolution camera captures');

      final filters = MediaSearchFilters(
        minFileSize: minFileSize ?? 1024 * 1024, // 1MB minimum
        sortBy: 'file_size',
        sortOrder: 'desc',
      );

      final results = cameraId != null
          ? await _searchService.searchCameraMedia('', specificCameraId: cameraId, filters: filters)
          : await _searchService.searchCameraMedia('', filters: filters);

      // Apply limit if specified
      final limitedResults = limit != null && results.length > limit 
          ? results.take(limit).toList() 
          : results;

      _logger.i('Retrieved ${limitedResults.length} high resolution captures');
      return limitedResults;
    } catch (e) {
      _logger.e('Error getting high resolution captures: $e');
      return [];
    }
  }

  /// Get security events (media with specific tags or patterns)
  Future<List<MediaItem>> getSecurityEvents({
    List<String>? tags,
    DateTime? startDate,
    DateTime? endDate,
    int? limit,
  }) async {
    try {
      _logger.i('Fetching security events');

      final securityTags = tags ?? ['security', 'surveillance', 'motion', 'event', 'alert'];
      
      final filters = MediaSearchFilters(
        tags: securityTags,
        startDate: startDate,
        endDate: endDate,
        sortBy: 'created_at',
        sortOrder: 'desc',
      );

      // Search for media with security-related tags
      final taggedResults = await _searchService.searchCameraMedia('', filters: filters);

      // Also search for media with security-related keywords in filename/metadata
      final keywordResults = await _searchService.searchCameraMedia(
        'security motion surveillance event alert',
        filters: filters?.copyWith(tags: null),
      );

      // Combine and deduplicate results
      final allResults = <String, MediaItem>{};
      for (final item in [...taggedResults, ...keywordResults]) {
        allResults[item.id] = item;
      }

      final uniqueResults = allResults.values.toList();
      
      // Sort by creation date (newest first)
      uniqueResults.sort((a, b) => b.createdAt.compareTo(a.createdAt));

      // Apply limit if specified
      final limitedResults = limit != null && uniqueResults.length > limit 
          ? uniqueResults.take(limit).toList() 
          : uniqueResults;

      _logger.i('Retrieved ${limitedResults.length} security events');
      return limitedResults;
    } catch (e) {
      _logger.e('Error getting security events: $e');
      return [];
    }
  }

  /// Get media from a specific camera
  Future<List<MediaItem>> getCameraSpecificMedia(
    String cameraId, {
    DateTime? startDate,
    DateTime? endDate,
    int? limit,
    String? sortBy,
    String? sortOrder,
  }) async {
    try {
      _logger.i('Fetching media for camera: $cameraId');

      final filters = MediaSearchFilters(
        startDate: startDate,
        endDate: endDate,
        sortBy: sortBy ?? 'created_at',
        sortOrder: sortOrder ?? 'desc',
      );

      final results = await _searchService.filterByCamera(cameraId);

      // Apply additional filtering if needed
      var filteredResults = results;
      if (startDate != null || endDate != null) {
        filteredResults = results.where((item) {
          if (startDate != null && item.createdAt.isBefore(startDate)) return false;
          if (endDate != null && item.createdAt.isAfter(endDate)) return false;
          return true;
        }).toList();
      }

      // Apply limit if specified
      final limitedResults = limit != null && filteredResults.length > limit 
          ? filteredResults.take(limit).toList() 
          : filteredResults;

      _logger.i('Retrieved ${limitedResults.length} media items for camera $cameraId');
      return limitedResults;
    } catch (e) {
      _logger.e('Error getting camera specific media: $e');
      return [];
    }
  }

  /// Get virtual collection statistics
  Future<VirtualCollectionStats> getVirtualCollectionStats() async {
    try {
      _logger.i('Calculating virtual collection statistics');

      final allCameraMedia = await getAllCameraMedia();
      final recentCaptures = await getRecentCameraCaptures();
      
      // Get camera mappings for camera count
      final cameraMappings = await _cameraCollectionService.getAllCameraMappings();
      
      // Calculate statistics
      final stats = VirtualCollectionStats(
        totalCameraMedia: allCameraMedia.length,
        recentCaptures24h: recentCaptures.length,
        totalCameras: cameraMappings.length,
        totalCollections: cameraMappings.map((m) => m.collectionId).toSet().length,
        oldestCameraCapture: allCameraMedia.isNotEmpty 
            ? allCameraMedia.map((m) => m.createdAt).reduce((a, b) => a.isBefore(b) ? a : b)
            : null,
        newestCameraCapture: allCameraMedia.isNotEmpty 
            ? allCameraMedia.map((m) => m.createdAt).reduce((a, b) => a.isAfter(b) ? a : b)
            : null,
        totalSize: allCameraMedia.fold(0, (sum, item) => sum + item.fileSize),
      );

      _logger.i('Virtual collection stats: ${stats.toString()}');
      return stats;
    } catch (e) {
      _logger.e('Error calculating virtual collection stats: $e');
      return const VirtualCollectionStats(
        totalCameraMedia: 0,
        recentCaptures24h: 0,
        totalCameras: 0,
        totalCollections: 0,
        totalSize: 0,
      );
    }
  }

  /// Clear virtual collection cache
  void clearCache() {
    _virtualCollectionCache.clear();
    _lastCacheUpdate = null;
    _logger.i('Virtual collection cache cleared');
    notifyListeners();
  }

  /// Refresh virtual collections (clear cache and notify listeners)
  Future<void> refresh() async {
    clearCache();
    notifyListeners();
  }

  // Private helper methods

  /// Check if cache is valid for a specific key
  bool _isCacheValid(String key, {Duration? timeout}) {
    if (!_virtualCollectionCache.containsKey(key) || _lastCacheUpdate == null) {
      return false;
    }

    final cacheAge = DateTime.now().difference(_lastCacheUpdate!);
    final maxAge = timeout ?? _cacheTimeout;
    
    return cacheAge < maxAge;
  }

  /// Format date for grouping keys
  String _formatDateKey(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }
}

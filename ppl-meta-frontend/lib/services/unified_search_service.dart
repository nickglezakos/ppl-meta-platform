import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import '../core/models/collection_models.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';
import '../core/services/camera_collection_service.dart';

/// Service for unified search across all collections (camera + user-created)
/// Provides comprehensive search functionality with advanced filtering and virtual collections
class UnifiedSearchService extends ChangeNotifier {
  final MediaApiClient _mediaApiClient;
  final CameraCollectionService _cameraCollectionService;
  final Logger _logger = Logger();
  
  // Search state
  bool _isSearching = false;
  List<MediaItem> _searchResults = [];
  String? _currentQuery;
  MediaSearchFilters? _activeFilters;
  String? _searchError;

  UnifiedSearchService({
    required MediaApiClient mediaApiClient,
    required CameraCollectionService cameraCollectionService,
  }) : _mediaApiClient = mediaApiClient,
       _cameraCollectionService = cameraCollectionService;

  // Getters
  bool get isSearching => _isSearching;
  List<MediaItem> get searchResults => _searchResults;
  String? get currentQuery => _currentQuery;
  MediaSearchFilters? get activeFilters => _activeFilters;
  String? get searchError => _searchError;

  /// Search across all collections (camera + user-created)
  Future<List<MediaItem>> searchAllCollections(String query, {
    MediaSearchFilters? filters,
  }) async {
    try {
      _setSearchState(true, query, filters);
      _logger.i('Searching all collections with query: "$query"');

      // Get all collections first
      final collectionsResponse = await _mediaApiClient.getCollections();
      if (!collectionsResponse.success || collectionsResponse.data == null) {
        throw Exception('Failed to get collections for search');
      }

      final allCollections = collectionsResponse.data!;
      final allResults = <MediaItem>[];

      // Search in each collection
      for (final collection in allCollections) {
        try {
          final collectionResults = await _searchInCollection(
            collection.id, 
            query, 
            filters: filters,
          );
          
          // Add collection metadata to each result
          // TODO: Create new MediaItem instances with collection info
          // for (final result in collectionResults) {
          //   result.collectionInfo = CollectionInfo(
          //     id: collection.id,
          //     name: collection.name,
          //     isCamera: _isCameraCollection(collection.name),
          //   );
          // }
          
          allResults.addAll(collectionResults);
        } catch (e) {
          _logger.w('Failed to search in collection ${collection.name}: $e');
          // Continue searching other collections
        }
      }

      // Apply additional filters and sorting
      final filteredResults = _applyAdvancedFiltering(allResults, filters);
      final sortedResults = _applySorting(filteredResults, filters?.sortBy, filters?.sortOrder);

      _setSearchResults(sortedResults);
      return sortedResults;
    } catch (e) {
      _logger.e('Error searching all collections: $e');
      _setSearchError('Failed to search collections: $e');
      return [];
    } finally {
      _setSearchState(false, query, filters);
    }
  }

  /// Search specifically in camera media across all camera collections
  Future<List<MediaItem>> searchCameraMedia(String query, {
    String? specificCameraId,
    MediaSearchFilters? filters,
  }) async {
    try {
      _setSearchState(true, query, filters);
      _logger.i('Searching camera media with query: "$query"');

      // Get camera collection mappings
      final cameraMappings = await _cameraCollectionService.getAllCameraMappings();
      final cameraResults = <MediaItem>[];

      // Filter by specific camera if provided
      final targetMappings = specificCameraId != null
          ? cameraMappings.where((m) => m.cameraId == specificCameraId).toList()
          : cameraMappings;

      // Search in each camera collection
      for (final mapping in targetMappings) {
        try {
          final collectionResults = await _searchInCollection(
            mapping.collectionId,
            query,
            filters: filters,
          );

          // Add camera metadata to each result
          // TODO: Create new MediaItem instances with collection info
          // for (final result in collectionResults) {
          //   result.collectionInfo = CollectionInfo(
          //     id: mapping.collectionId,
          //     name: mapping.collectionName,
          //     isCamera: true,
          //     cameraId: mapping.cameraId,
          //     cameraName: mapping.cameraName,
          //   );
          // }

          cameraResults.addAll(collectionResults);
        } catch (e) {
          _logger.w('Failed to search in camera collection ${mapping.collectionName}: $e');
          // Continue searching other camera collections
        }
      }

      // Apply camera-specific filtering
      final filteredResults = _applyCameraFiltering(cameraResults, specificCameraId, filters);
      final sortedResults = _applySorting(filteredResults, filters?.sortBy, filters?.sortOrder);

      _setSearchResults(sortedResults);
      return sortedResults;
    } catch (e) {
      _logger.e('Error searching camera media: $e');
      _setSearchError('Failed to search camera media: $e');
      return [];
    } finally {
      _setSearchState(false, query, filters);
    }
  }

  /// Filter media by date range across all collections
  Future<List<MediaItem>> filterByDateRange(DateTime start, DateTime end, {
    bool cameraOnly = false,
  }) async {
    try {
      _setSearchState(true, null, null);
      _logger.i('Filtering by date range: ${start.toIso8601String()} to ${end.toIso8601String()}');

      final dateFilter = MediaSearchFilters(
        startDate: start,
        endDate: end,
        sortBy: 'created_at',
        sortOrder: 'desc',
      );

      if (cameraOnly) {
        return await searchCameraMedia('', filters: dateFilter);
      } else {
        return await searchAllCollections('', filters: dateFilter);
      }
    } catch (e) {
      _logger.e('Error filtering by date range: $e');
      _setSearchError('Failed to filter by date range: $e');
      return [];
    }
  }

  /// Filter media by specific camera across all collections owned by that camera
  Future<List<MediaItem>> filterByCamera(String cameraId) async {
    try {
      _setSearchState(true, null, null);
      _logger.i('Filtering by camera: $cameraId');

      return await searchCameraMedia('', specificCameraId: cameraId);
    } catch (e) {
      _logger.e('Error filtering by camera: $e');
      _setSearchError('Failed to filter by camera: $e');
      return [];
    }
  }

  /// Get search suggestions based on partial query
  Future<SearchSuggestions> getSearchSuggestions(String partialQuery) async {
    try {
      _logger.d('Getting search suggestions for: "$partialQuery"');

      // Get recent search terms (placeholder - could be stored locally)
      final recentSearches = await _getRecentSearches();
      
      // Get available tags from all collections
      final availableTags = await _getAvailableTags();
      
      // Get camera names for camera-specific suggestions
      final cameraNames = await _getCameraNames();
      
      // Generate suggestions
      final suggestions = SearchSuggestions(
        recentSearches: recentSearches
            .where((search) => search.toLowerCase().contains(partialQuery.toLowerCase()))
            .take(5)
            .toList(),
        tagSuggestions: availableTags
            .where((tag) => tag.toLowerCase().contains(partialQuery.toLowerCase()))
            .take(5)
            .toList(),
        cameraSuggestions: cameraNames
            .where((camera) => camera.toLowerCase().contains(partialQuery.toLowerCase()))
            .take(3)
            .toList(),
        quickFilters: _generateQuickFilters(partialQuery),
      );

      return suggestions;
    } catch (e) {
      _logger.e('Error getting search suggestions: $e');
      return const SearchSuggestions(
        recentSearches: [],
        tagSuggestions: [],
        cameraSuggestions: [],
        quickFilters: [],
      );
    }
  }

  /// Save search query to recent searches
  Future<void> saveRecentSearch(String query) async {
    if (query.trim().isEmpty) return;
    
    try {
      final recentSearches = await _getRecentSearches();
      recentSearches.remove(query); // Remove if already exists
      recentSearches.insert(0, query); // Add to beginning
      
      // Keep only last 10 searches
      if (recentSearches.length > 10) {
        recentSearches.removeRange(10, recentSearches.length);
      }

      // Save to local storage (implementation depends on your storage solution)
      await _saveRecentSearches(recentSearches);
    } catch (e) {
      _logger.e('Error saving recent search: $e');
    }
  }

  /// Clear search results and state
  void clearSearch() {
    _searchResults.clear();
    _currentQuery = null;
    _activeFilters = null;
    _searchError = null;
    notifyListeners();
  }

  // Private helper methods

  /// Search within a specific collection
  Future<List<MediaItem>> _searchInCollection(
    String collectionId, 
    String query, {
    MediaSearchFilters? filters,
  }) async {
    final searchFilters = filters?.copyWith(collectionId: collectionId) ?? 
                         MediaSearchFilters(collectionId: collectionId);

    final response = await _mediaApiClient.searchMedia(
      query: query.isEmpty ? null : query,
      filters: searchFilters,
    );

    if (response.success && response.data != null) {
      return response.data!.items;
    }

    return [];
  }

  /// Check if a collection is a camera collection
  bool _isCameraCollection(String collectionName) {
    return collectionName.toLowerCase().contains('camera') ||
           RegExp(r'cam\d+|camera\s*\d+', caseSensitive: false).hasMatch(collectionName);
  }

  /// Apply advanced filtering to search results
  List<MediaItem> _applyAdvancedFiltering(List<MediaItem> results, MediaSearchFilters? filters) {
    if (filters == null) return results;

    var filtered = results;

    // Filter by media type
    if (filters.mediaType != null) {
      filtered = filtered.where((item) => item.mediaType == filters.mediaType).toList();
    }

    // Filter by file size
    if (filters.minFileSize != null) {
      filtered = filtered.where((item) => item.fileSize >= filters.minFileSize!).toList();
    }
    if (filters.maxFileSize != null) {
      filtered = filtered.where((item) => item.fileSize <= filters.maxFileSize!).toList();
    }

    // Filter by thumbnail availability
    if (filters.hasThumbnail != null) {
      filtered = filtered.where((item) => 
        (item.thumbnailUrl != null) == filters.hasThumbnail).toList();
    }

    return filtered;
  }

  /// Apply camera-specific filtering
  List<MediaItem> _applyCameraFiltering(
    List<MediaItem> results, 
    String? specificCameraId, 
    MediaSearchFilters? filters,
  ) {
    var filtered = results;

    // Filter by specific camera if provided
    if (specificCameraId != null) {
      filtered = filtered.where((item) => 
        item.collectionInfo?.cameraId == specificCameraId).toList();
    }

    // Apply additional camera-specific filters
    // (could include resolution, capture settings, etc.)

    return filtered;
  }

  /// Apply sorting to search results
  List<MediaItem> _applySorting(List<MediaItem> results, String? sortBy, String? sortOrder) {
    if (sortBy == null) return results;

    final ascending = sortOrder?.toLowerCase() != 'desc';

    switch (sortBy.toLowerCase()) {
      case 'created_at':
      case 'date':
        results.sort((a, b) => ascending 
            ? a.createdAt.compareTo(b.createdAt)
            : b.createdAt.compareTo(a.createdAt));
        break;
      case 'file_size':
      case 'size':
        results.sort((a, b) => ascending 
            ? a.fileSize.compareTo(b.fileSize)
            : b.fileSize.compareTo(a.fileSize));
        break;
      case 'filename':
      case 'name':
        results.sort((a, b) => ascending 
            ? a.filename.compareTo(b.filename)
            : b.filename.compareTo(a.filename));
        break;
      default:
        // Default to creation date
        results.sort((a, b) => b.createdAt.compareTo(a.createdAt));
        break;
    }

    return results;
  }

  /// Set search state
  void _setSearchState(bool searching, String? query, MediaSearchFilters? filters) {
    _isSearching = searching;
    _currentQuery = query;
    _activeFilters = filters;
    _searchError = null;
    notifyListeners();
  }

  /// Set search results
  void _setSearchResults(List<MediaItem> results) {
    _searchResults = results;
    notifyListeners();
  }

  /// Set search error
  void _setSearchError(String error) {
    _searchError = error;
    _searchResults.clear();
    notifyListeners();
  }

  /// Get recent searches from local storage
  Future<List<String>> _getRecentSearches() async {
    // Placeholder implementation - replace with actual storage
    return [];
  }

  /// Save recent searches to local storage
  Future<void> _saveRecentSearches(List<String> searches) async {
    // Placeholder implementation - replace with actual storage
  }

  /// Get available tags from all collections
  Future<List<String>> _getAvailableTags() async {
    // Placeholder implementation - could be fetched from API
    return [
      'work', 'personal', 'project', 'meeting', 'vacation',
      'family', 'friends', 'travel', 'food', 'nature',
      'security', 'surveillance', 'motion', 'event'
    ];
  }

  /// Get camera names from camera mappings
  Future<List<String>> _getCameraNames() async {
    try {
      final mappings = await _cameraCollectionService.getAllCameraMappings();
      return mappings.map((m) => m.cameraName).toSet().toList();
    } catch (e) {
      _logger.e('Error getting camera names: $e');
      return [];
    }
  }

  /// Generate quick filter suggestions
  List<String> _generateQuickFilters(String partialQuery) {
    final quickFilters = <String>[];

    // Add time-based filters
    quickFilters.addAll([
      'Today',
      'This Week',
      'This Month',
      'Camera Media',
      'User Collections',
    ]);

    // Add format-specific filters
    if (partialQuery.toLowerCase().contains('image') || 
        partialQuery.toLowerCase().contains('photo')) {
      quickFilters.add('Images Only');
    }
    if (partialQuery.toLowerCase().contains('video')) {
      quickFilters.add('Videos Only');
    }

    return quickFilters.take(3).toList();
  }
}

/// Exception for unified search operations
class UnifiedSearchException implements Exception {
  final String message;
  const UnifiedSearchException(this.message);
  
  @override
  String toString() => 'UnifiedSearchException: $message';
}

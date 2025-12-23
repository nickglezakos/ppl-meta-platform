import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/unified_search_service.dart';
import '../../services/virtual_collection_service.dart';
import '../../services/media_api_client.dart';
import '../services/camera_collection_service.dart';
import '../../models/media_models.dart';
import 'camera_providers.dart';

// Unified Search Service Provider
final unifiedSearchServiceProvider = Provider<UnifiedSearchService>((ref) {
  final mediaApiClient = ref.watch(mediaApiClientProvider);
  final cameraCollectionService = ref.watch(cameraCollectionServiceProvider);
  
  return UnifiedSearchService(
    mediaApiClient: mediaApiClient,
    cameraCollectionService: cameraCollectionService,
  );
});

// Virtual Collection Service Provider
final virtualCollectionServiceProvider = Provider<VirtualCollectionService>((ref) {
  final mediaApiClient = ref.watch(mediaApiClientProvider);
  final cameraCollectionService = ref.watch(cameraCollectionServiceProvider);
  final searchService = ref.watch(unifiedSearchServiceProvider);
  
  return VirtualCollectionService(
    mediaApiClient: mediaApiClient,
    cameraCollectionService: cameraCollectionService,
    searchService: searchService,
  );
});

// Search Results Provider
final searchResultsProvider = StateNotifierProvider<SearchResultsNotifier, SearchResultsState>((ref) {
  final searchService = ref.watch(unifiedSearchServiceProvider);
  return SearchResultsNotifier(searchService);
});

// Virtual Collection Stats Provider
final virtualCollectionStatsProvider = FutureProvider<VirtualCollectionStats>((ref) async {
  final virtualCollectionService = ref.watch(virtualCollectionServiceProvider);
  return await virtualCollectionService.getVirtualCollectionStats();
});

// All Camera Media Provider
final allCameraMediaProvider = FutureProvider.family<List<MediaItem>, SearchParams>((ref, params) async {
  final virtualCollectionService = ref.watch(virtualCollectionServiceProvider);
  return await virtualCollectionService.getAllCameraMedia(
    limit: params.limit,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  );
});

// Recent Camera Captures Provider
final recentCameraCapturesProvider = FutureProvider.family<List<MediaItem>, int?>((ref, limit) async {
  final virtualCollectionService = ref.watch(virtualCollectionServiceProvider);
  return await virtualCollectionService.getRecentCameraCaptures(limit: limit);
});

// Security Events Provider
final securityEventsProvider = FutureProvider.family<List<MediaItem>, SecurityEventsParams>((ref, params) async {
  final virtualCollectionService = ref.watch(virtualCollectionServiceProvider);
  return await virtualCollectionService.getSecurityEvents(
    tags: params.tags,
    startDate: params.startDate,
    endDate: params.endDate,
    limit: params.limit,
  );
});

// Camera Specific Media Provider
final cameraSpecificMediaProvider = FutureProvider.family<List<MediaItem>, CameraMediaParams>((ref, params) async {
  final virtualCollectionService = ref.watch(virtualCollectionServiceProvider);
  return await virtualCollectionService.getCameraSpecificMedia(
    params.cameraId,
    startDate: params.startDate,
    endDate: params.endDate,
    limit: params.limit,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  );
});

// Search Suggestions Provider
final searchSuggestionsProvider = FutureProvider.family<SearchSuggestions, String>((ref, query) async {
  if (query.length < 2) return const SearchSuggestions(
    queries: [],
    tags: [],
    cameras: [],
    collections: [],
  );
  
  final searchService = ref.watch(unifiedSearchServiceProvider);
  return await searchService.getSearchSuggestions(query);
});

/// Search Results State Management
class SearchResultsState {
  final List<MediaItem> results;
  final bool isLoading;
  final String? error;
  final String? currentQuery;
  final MediaSearchFilters? activeFilters;

  const SearchResultsState({
    this.results = const [],
    this.isLoading = false,
    this.error,
    this.currentQuery,
    this.activeFilters,
  });

  SearchResultsState copyWith({
    List<MediaItem>? results,
    bool? isLoading,
    String? error,
    String? currentQuery,
    MediaSearchFilters? activeFilters,
  }) {
    return SearchResultsState(
      results: results ?? this.results,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      currentQuery: currentQuery ?? this.currentQuery,
      activeFilters: activeFilters ?? this.activeFilters,
    );
  }
}

class SearchResultsNotifier extends StateNotifier<SearchResultsState> {
  final UnifiedSearchService _searchService;

  SearchResultsNotifier(this._searchService) : super(const SearchResultsState()) {
    // Listen to search service changes
    _searchService.addListener(_onSearchServiceChanged);
  }

  void _onSearchServiceChanged() {
    state = state.copyWith(
      results: _searchService.searchResults,
      isLoading: _searchService.isSearching,
      error: _searchService.searchError,
      currentQuery: _searchService.currentQuery,
      activeFilters: _searchService.activeFilters,
    );
  }

  Future<void> searchAllCollections(String query, {MediaSearchFilters? filters}) async {
    await _searchService.searchAllCollections(query, filters: filters);
  }

  Future<void> searchCameraMedia(String query, {String? cameraId, MediaSearchFilters? filters}) async {
    await _searchService.searchCameraMedia(query, specificCameraId: cameraId, filters: filters);
  }

  Future<void> filterByDateRange(DateTime start, DateTime end, {bool cameraOnly = false}) async {
    await _searchService.filterByDateRange(start, end, cameraOnly: cameraOnly);
  }

  Future<void> filterByCamera(String cameraId) async {
    await _searchService.filterByCamera(cameraId);
  }

  void clearSearch() {
    _searchService.clearSearch();
  }

  @override
  void dispose() {
    _searchService.removeListener(_onSearchServiceChanged);
    super.dispose();
  }
}

/// Parameters for search operations
class SearchParams {
  final int? limit;
  final String? sortBy;
  final String? sortOrder;

  const SearchParams({
    this.limit,
    this.sortBy,
    this.sortOrder,
  });
}

class SecurityEventsParams {
  final List<String>? tags;
  final DateTime? startDate;
  final DateTime? endDate;
  final int? limit;

  const SecurityEventsParams({
    this.tags,
    this.startDate,
    this.endDate,
    this.limit,
  });
}

class CameraMediaParams {
  final String cameraId;
  final DateTime? startDate;
  final DateTime? endDate;
  final int? limit;
  final String? sortBy;
  final String? sortOrder;

  const CameraMediaParams({
    required this.cameraId,
    this.startDate,
    this.endDate,
    this.limit,
    this.sortBy,
    this.sortOrder,
  });
}

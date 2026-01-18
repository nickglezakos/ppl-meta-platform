import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/phase2_services.dart';
import '../core/services/camera_service.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';

// =============================================================================
// PHASE 2 PROVIDERS CONFIGURATION
// =============================================================================
// 
// This file configures all Provider/Riverpod dependencies for Phase 2
// media service integration, connecting backend services to UI components.
//
// Provider Hierarchy:
// 1. Core Dependencies (SharedPreferences, MediaApiClient)
// 2. Enhanced Services (Sync, Gallery, Collections)
// 3. UI State Providers (Gallery state, sync status)
// 4. Composite Providers (Unified API access)
//
// =============================================================================

// -----------------------------------------------------------------------------
// CORE DEPENDENCY PROVIDERS
// -----------------------------------------------------------------------------

/// SharedPreferences provider for local storage operations
final sharedPreferencesProvider = FutureProvider<SharedPreferences>((ref) async {
  return await SharedPreferences.getInstance();
});

/// API client provider for camera operations
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(AppConfig.instance);
});

/// Camera service provider (existing from Phase 1)
final cameraServiceProvider = Provider<CameraService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CameraService(apiClient);
});

/// Media API client provider for cloud operations
final mediaApiClientProvider = Provider<MediaApiClient>((ref) {
  return MediaApiClient(
    baseUrl: 'http://localhost/api/media', // ppl-meta-media service via nginx
  );
});

// -----------------------------------------------------------------------------
// ENHANCED SERVICE PROVIDERS
// -----------------------------------------------------------------------------

/// Snapshot sync service for background cloud upload
final snapshotSyncServiceProvider = FutureProvider<SnapshotSyncService>((ref) async {
  final mediaClient = ref.watch(mediaApiClientProvider);
  final prefs = await ref.watch(sharedPreferencesProvider.future);
  
  return SnapshotSyncService(
    mediaApiClient: mediaClient,
    sharedPreferences: prefs,
  );
});

/// Enhanced gallery service for hybrid local+cloud display
final enhancedGalleryServiceProvider = FutureProvider<EnhancedGalleryService>((ref) async {
  final mediaClient = ref.watch(mediaApiClientProvider);
  final prefs = await ref.watch(sharedPreferencesProvider.future);
  
  return EnhancedGalleryService(
    mediaApiClient: mediaClient,
    sharedPreferences: prefs,
  );
});

/// Snapshot collection service for professional organization
final snapshotCollectionServiceProvider = FutureProvider<SnapshotCollectionService>((ref) async {
  final mediaClient = ref.watch(mediaApiClientProvider);
  final prefs = await ref.watch(sharedPreferencesProvider.future);
  
  return SnapshotCollectionService(
    mediaApiClient: mediaClient,
    sharedPreferences: prefs,
  );
});

/// Enhanced snapshot service for unified Phase 2 API
final enhancedSnapshotServiceProvider = FutureProvider<EnhancedSnapshotService>((ref) async {
  final cameraService = ref.watch(cameraServiceProvider);
  final syncService = await ref.watch(snapshotSyncServiceProvider.future);
  final galleryService = await ref.watch(enhancedGalleryServiceProvider.future);
  final collectionService = await ref.watch(snapshotCollectionServiceProvider.future);
  
  return EnhancedSnapshotService(
    cameraService: cameraService,
    syncService: syncService,
    galleryService: galleryService,
    collectionService: collectionService,
  );
});

// -----------------------------------------------------------------------------
// UI STATE PROVIDERS
// -----------------------------------------------------------------------------

/// Sync status provider for real-time upload status
final syncStatusProvider = StreamProvider<SyncStatus>((ref) async* {
  final syncService = await ref.watch(snapshotSyncServiceProvider.future);
  yield* syncService.syncStatusStream;
});

/// Gallery mode provider (local, cloud, or both)
final galleryModeProvider = StateProvider<GalleryMode>((ref) {
  return GalleryMode.both; // Default to hybrid mode
});

/// Gallery items provider with filtering
final galleryItemsProvider = FutureProvider.family<List<GalleryItem>, GalleryFilter>((ref, filter) async {
  final galleryService = await ref.watch(enhancedGalleryServiceProvider.future);
  final mode = ref.watch(galleryModeProvider);
  
  return await galleryService.getGalleryItems(
    filter: filter,
    mode: mode,
  );
});

/// Collections provider for snapshot organization
final collectionsProvider = FutureProvider<List<SnapshotCollection>>((ref) async {
  final collectionService = await ref.watch(snapshotCollectionServiceProvider.future);
  return await collectionService.getAllCollections();
});

/// Selected collection provider for filtering
final selectedCollectionProvider = StateProvider<SnapshotCollection?>((ref) {
  return null; // No collection selected by default
});

// -----------------------------------------------------------------------------
// SEARCH AND FILTER PROVIDERS
// -----------------------------------------------------------------------------

/// Search query provider for gallery filtering
final searchQueryProvider = StateProvider<String>((ref) {
  return ''; // Empty search by default
});

/// Camera filter provider for gallery
final cameraFilterProvider = StateProvider<String?>((ref) {
  return null; // No camera filter by default
});

/// Date range filter provider
final dateRangeFilterProvider = StateProvider<DateRange?>((ref) {
  return null; // No date filter by default
});

/// Combined gallery filter provider
final galleryFilterProvider = Provider<GalleryFilter>((ref) {
  final searchQuery = ref.watch(searchQueryProvider);
  final cameraId = ref.watch(cameraFilterProvider);
  final dateRange = ref.watch(dateRangeFilterProvider);
  final collection = ref.watch(selectedCollectionProvider);
  
  return GalleryFilter(
    searchQuery: searchQuery.isNotEmpty ? searchQuery : null,
    cameraId: cameraId,
    dateRange: dateRange,
    collectionId: collection?.id,
  );
});

// -----------------------------------------------------------------------------
// COMPOSITE STATE PROVIDERS
// -----------------------------------------------------------------------------

/// Filtered gallery items provider combining all filters
final filteredGalleryItemsProvider = FutureProvider<List<GalleryItem>>((ref) async {
  final filter = ref.watch(galleryFilterProvider);
  return await ref.watch(galleryItemsProvider(filter).future);
});

/// Gallery statistics provider
final galleryStatsProvider = FutureProvider<GalleryStats>((ref) async {
  final galleryService = await ref.watch(enhancedGalleryServiceProvider.future);
  return galleryService.getGalleryStats();
});

/// Upload queue status provider
final uploadQueueProvider = StreamProvider<List<UploadTask>>((ref) async* {
  final syncService = await ref.watch(snapshotSyncServiceProvider.future);
  yield* syncService.uploadQueueStream;
});

// -----------------------------------------------------------------------------
// PERFORMANCE OPTIMIZATION PROVIDERS
// -----------------------------------------------------------------------------

/// Thumbnail cache provider for efficient loading
final thumbnailCacheProvider = Provider<ThumbnailCache>((ref) {
  return ThumbnailCache(maxCacheSize: 50 * 1024 * 1024); // 50MB cache
});

/// Background sync enabled provider
final backgroundSyncEnabledProvider = StateProvider<bool>((ref) {
  return true; // Background sync enabled by default
});

/// Auto-upload settings provider
final autoUploadSettingsProvider = StateProvider<AutoUploadSettings>((ref) {
  return AutoUploadSettings(
    enabled: true,
    wifiOnly: true,
    qualityThreshold: 0.8,
  );
});

// -----------------------------------------------------------------------------
// UTILITY PROVIDERS
// -----------------------------------------------------------------------------

/// Network status provider for connectivity awareness
final networkStatusProvider = StateProvider<NetworkStatus>((ref) {
  return NetworkStatus.connected; // Assume connected initially
});

/// Storage stats provider for local storage monitoring
final storageStatsProvider = FutureProvider<StorageStats>((ref) async {
  // TODO: Implement storage stats calculation using SharedPreferences
  return StorageStats(
    totalSpace: 0,
    usedSpace: 0,
    availableSpace: 0,
  );
});

// =============================================================================
// PROVIDER MODELS & TYPES
// =============================================================================

/// Gallery display mode options
enum GalleryMode {
  local,
  cloud, 
  both,
}

/// Network connectivity status
enum NetworkStatus {
  connected,
  disconnected,
  limited,
}

/// Date range filter model
class DateRange {
  final DateTime start;
  final DateTime end;
  
  const DateRange({
    required this.start,
    required this.end,
  });
}

/// Gallery filter options
class GalleryFilter {
  final String? searchQuery;
  final String? cameraId;
  final DateRange? dateRange;
  final String? collectionId;
  
  const GalleryFilter({
    this.searchQuery,
    this.cameraId,
    this.dateRange,
    this.collectionId,
  });
  
  bool get isEmpty => 
    searchQuery == null && 
    cameraId == null && 
    dateRange == null && 
    collectionId == null;
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_spacing.dart';
import '../widgets/advanced_search_interface.dart';
import '../widgets/responsive_media_gallery.dart';
import '../core/providers/search_providers.dart';
import '../models/media_models.dart';
import '../services/unified_search_service.dart';

/// Unified search screen for searching across all collections (camera + user-created)
/// Provides comprehensive search functionality with virtual collections
class UnifiedSearchScreen extends ConsumerStatefulWidget {
  final String? initialQuery;
  final MediaSearchFilters? initialFilters;

  const UnifiedSearchScreen({
    Key? key,
    this.initialQuery,
    this.initialFilters,
  }) : super(key: key);

  @override
  ConsumerState<UnifiedSearchScreen> createState() => _UnifiedSearchScreenState();
}

class _UnifiedSearchScreenState extends ConsumerState<UnifiedSearchScreen>
    with TickerProviderStateMixin {
  
  late TabController _tabController;
  bool _showVirtualCollections = true;
  String _currentSearchMode = 'all'; // 'all', 'camera', 'user'

  final List<Tab> _tabs = const [
    Tab(icon: Icon(Icons.search), text: 'Search Results'),
    Tab(icon: Icon(Icons.videocam), text: 'All Camera Media'),
    Tab(icon: Icon(Icons.access_time), text: 'Recent Captures'),
    Tab(icon: Icon(Icons.security), text: 'Security Events'),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
    
    // Perform initial search if provided
    if (widget.initialQuery != null || widget.initialFilters != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _performSearch(widget.initialQuery ?? '', widget.initialFilters);
      });
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _performSearch(String query, MediaSearchFilters? filters) {
    final searchNotifier = ref.read(searchResultsProvider.notifier);
    
    switch (_currentSearchMode) {
      case 'camera':
        searchNotifier.searchCameraMedia(query, filters: filters);
        break;
      case 'user':
        // Search only in user collections (implement user-only search)
        searchNotifier.searchAllCollections(query, filters: filters);
        break;
      case 'all':
      default:
        searchNotifier.searchAllCollections(query, filters: filters);
        break;
    }
  }

  void _clearSearch() {
    final searchNotifier = ref.read(searchResultsProvider.notifier);
    searchNotifier.clearSearch();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Unified Search'),
        actions: [
          // Search mode toggle
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_alt),
            onSelected: (value) {
              setState(() {
                _currentSearchMode = value;
              });
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'all',
                child: ListTile(
                  leading: Icon(Icons.all_inclusive),
                  title: Text('All Collections'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              const PopupMenuItem(
                value: 'camera',
                child: ListTile(
                  leading: Icon(Icons.videocam),
                  title: Text('Camera Media Only'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              const PopupMenuItem(
                value: 'user',
                child: ListTile(
                  leading: Icon(Icons.collections),
                  title: Text('User Collections Only'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
          
          // Virtual collections toggle
          IconButton(
            onPressed: () {
              setState(() {
                _showVirtualCollections = !_showVirtualCollections;
              });
            },
            icon: Icon(
              _showVirtualCollections ? Icons.view_module : Icons.view_list,
            ),
            tooltip: _showVirtualCollections 
                ? 'Hide virtual collections' 
                : 'Show virtual collections',
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: _tabs,
          isScrollable: true,
        ),
      ),
      body: Column(
        children: [
          // Search interface
          AdvancedSearchInterface(
            initialFilters: widget.initialFilters,
            onSearch: _performSearch,
            onClear: _clearSearch,
            availableTags: const [
              'work', 'personal', 'project', 'meeting', 'vacation',
              'family', 'friends', 'travel', 'food', 'nature',
              'security', 'surveillance', 'motion', 'event', 'alert'
            ],
            enableCameraFilters: true,
            showVirtualCollections: _showVirtualCollections,
          ),
          
          // Search mode indicator
          if (_currentSearchMode != 'all')
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.md,
                vertical: AppSpacing.sm,
              ),
              color: AppColors.primary.withOpacity(0.1),
              child: Row(
                children: [
                  Icon(
                    _currentSearchMode == 'camera' ? Icons.videocam : Icons.collections,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Text(
                    'Searching in ${_currentSearchMode == 'camera' ? 'Camera Media' : 'User Collections'} only',
                    style: TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: () => setState(() => _currentSearchMode = 'all'),
                    child: const Text('Search All'),
                  ),
                ],
              ),
            ),
          
          // Tab content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildSearchResultsTab(),
                _buildAllCameraMediaTab(),
                _buildRecentCapturesTab(),
                _buildSecurityEventsTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchResultsTab() {
    return Consumer(
      builder: (context, ref, child) {
        final searchState = ref.watch(searchResultsProvider);
        
        return Column(
          children: [
            // Search stats
            if (searchState.currentQuery != null || searchState.results.isNotEmpty)
              _buildSearchStats(searchState),
            
            // Search results
            Expanded(
              child: _buildSearchContent(searchState),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSearchStats(SearchResultsState searchState) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        border: Border(
          bottom: BorderSide(color: AppColors.border.withOpacity(0.5)),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: Text(
              searchState.currentQuery?.isNotEmpty == true
                  ? 'Found ${searchState.results.length} results for "${searchState.currentQuery}"'
                  : '${searchState.results.length} items found',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          if (searchState.isLoading)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
        ],
      ),
    );
  }

  Widget _buildSearchContent(SearchResultsState searchState) {
    if (searchState.isLoading && searchState.results.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: AppSpacing.md),
            Text('Searching...'),
          ],
        ),
      );
    }

    if (searchState.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: AppColors.error),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Search Error',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: AppColors.error,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              searchState.error!,
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.md),
            ElevatedButton(
              onPressed: () => _performSearch(
                searchState.currentQuery ?? '',
                searchState.activeFilters,
              ),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (searchState.results.isEmpty && searchState.currentQuery != null) {
      return _buildEmptySearchResults();
    }

    if (searchState.results.isEmpty) {
      return _buildSearchPrompt();
    }

    return ResponsiveMediaGallery(
      mediaItems: searchState.results,
      enableSelection: true,
      showCollectionBadges: true,
      enableInfiniteScroll: false, // Search results are already loaded
    );
  }

  Widget _buildEmptySearchResults() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off, size: 64, color: AppColors.textSecondary),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No Results Found',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          const Text(
            'Try adjusting your search terms or filters',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.md),
          ElevatedButton(
            onPressed: _clearSearch,
            child: const Text('Clear Search'),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchPrompt() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search, size: 64, color: AppColors.textSecondary),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Search Across All Collections',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          const Text(
            'Find media from camera collections and user collections\nUse filters for more precise results',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildAllCameraMediaTab() {
    return Consumer(
      builder: (context, ref, child) {
        final cameraMediaAsync = ref.watch(allCameraMediaProvider(
          const SearchParams(limit: 100, sortBy: 'created_at', sortOrder: 'desc')
        ));
        
        return cameraMediaAsync.when(
          data: (mediaItems) => ResponsiveMediaGallery(
            mediaItems: mediaItems,
            enableSelection: true,
            showCollectionBadges: true,
            enableInfiniteScroll: false,
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, stack) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: AppSpacing.md),
                Text('Error loading camera media: $error'),
                const SizedBox(height: AppSpacing.md),
                ElevatedButton(
                  onPressed: () => ref.refresh(allCameraMediaProvider(
                    const SearchParams(limit: 100, sortBy: 'created_at', sortOrder: 'desc')
                  )),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildRecentCapturesTab() {
    return Consumer(
      builder: (context, ref, child) {
        final recentCapturesAsync = ref.watch(recentCameraCapturesProvider(50));
        
        return recentCapturesAsync.when(
          data: (mediaItems) => Column(
            children: [
              // Recent captures header
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: Theme.of(context).cardColor,
                  border: Border(
                    bottom: BorderSide(color: AppColors.border.withOpacity(0.5)),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.access_time, color: AppColors.primary),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Recent Camera Captures (Last 24 Hours)',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '${mediaItems.length} items',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              
              // Recent captures gallery
              Expanded(
                child: mediaItems.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.camera_alt, size: 64, color: AppColors.textSecondary),
                            SizedBox(height: AppSpacing.md),
                            Text('No recent captures'),
                            Text('Camera captures from the last 24 hours will appear here'),
                          ],
                        ),
                      )
                    : ResponsiveMediaGallery(
                        mediaItems: mediaItems,
                        enableSelection: true,
                        showCollectionBadges: true,
                        enableInfiniteScroll: false,
                      ),
              ),
            ],
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, stack) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: AppSpacing.md),
                Text('Error loading recent captures: $error'),
                const SizedBox(height: AppSpacing.md),
                ElevatedButton(
                  onPressed: () => ref.refresh(recentCameraCapturesProvider(50)),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildSecurityEventsTab() {
    return Consumer(
      builder: (context, ref, child) {
        final securityEventsAsync = ref.watch(securityEventsProvider(
          const SecurityEventsParams(
            tags: ['security', 'surveillance', 'motion', 'event', 'alert'],
            limit: 100,
          ),
        ));
        
        return securityEventsAsync.when(
          data: (mediaItems) => Column(
            children: [
              // Security events header
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: Theme.of(context).cardColor,
                  border: Border(
                    bottom: BorderSide(color: AppColors.border.withOpacity(0.5)),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.security, color: AppColors.warning),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Security Events',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '${mediaItems.length} events',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              
              // Security events gallery
              Expanded(
                child: mediaItems.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.security, size: 64, color: AppColors.textSecondary),
                            SizedBox(height: AppSpacing.md),
                            Text('No security events'),
                            Text('Media tagged with security, surveillance, motion, or event will appear here'),
                          ],
                        ),
                      )
                    : ResponsiveMediaGallery(
                        mediaItems: mediaItems,
                        enableSelection: true,
                        showCollectionBadges: true,
                        enableInfiniteScroll: false,
                      ),
              ),
            ],
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, stack) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: AppSpacing.md),
                Text('Error loading security events: $error'),
                const SizedBox(height: AppSpacing.md),
                ElevatedButton(
                  onPressed: () => ref.refresh(securityEventsProvider(
                    const SecurityEventsParams(
                      tags: ['security', 'surveillance', 'motion', 'event', 'alert'],
                      limit: 100,
                    ),
                  )),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

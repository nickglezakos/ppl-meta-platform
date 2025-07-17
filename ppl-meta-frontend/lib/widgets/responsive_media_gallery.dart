import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../core/theme/app_theme.dart';
import '../core/models/api_response.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';
import '../core/api/api_client.dart';

/// Responsive media gallery with thumbnail views and infinite scroll
class ResponsiveMediaGallery extends StatefulWidget {
  final String? collectionId;
  final MediaSearchFilters? filters;
  final Function(MediaItem)? onItemTap;
  final Function(MediaItem)? onItemLongPress;
  final Function(List<MediaItem>)? onSelectionChanged;
  final bool enableSelection;
  final bool enableInfiniteScroll;
  final int itemsPerPage;
  final ApiClient? apiClient;

  ResponsiveMediaGallery({
    super.key,
    this.collectionId,
    this.filters,
    this.onItemTap,
    this.onItemLongPress,
    this.onSelectionChanged,
    this.enableSelection = false,
    this.enableInfiniteScroll = true,
    this.itemsPerPage = 20,
    this.apiClient,
  }) {
    print('🔥 GALLERY WIDGET CREATED 🔥');
  }

  @override
  State<ResponsiveMediaGallery> createState() => _ResponsiveMediaGalleryState();
}

class _ResponsiveMediaGalleryState extends State<ResponsiveMediaGallery> {
  final ScrollController _scrollController = ScrollController();
  late final MediaApiClient _apiClient;
  
  List<MediaItem> _items = [];
  Set<String> _selectedItems = {};
  bool _isLoading = false;
  bool _hasMoreItems = true;
  int _currentPage = 1;
  String? _error;
  
  // Layout configuration
  late int _crossAxisCount;
  late double _childAspectRatio;
  late double _itemSpacing;

  @override
  void initState() {
    super.initState();
    print('DEBUG: ResponsiveMediaGallery initState called');
    _apiClient = MediaApiClient(widget.apiClient);
    _scrollController.addListener(_onScroll);
    print('DEBUG: About to call _loadInitialItems');
    _loadInitialItems();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(ResponsiveMediaGallery oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    // Reload if filters changed
    if (widget.filters != oldWidget.filters ||
        widget.collectionId != oldWidget.collectionId) {
      _refreshItems();
    }
  }

  /// Load initial items
  Future<void> _loadInitialItems() async {
    setState(() {
      _error = null;
      _items.clear();
      _selectedItems.clear();
      _currentPage = 1;
      _hasMoreItems = true;
      // Don't set _isLoading = true here, let _loadMoreItems handle it
    });

    await _loadMoreItems();
  }

  /// Load more items for pagination
  Future<void> _loadMoreItems() async {
    if (_isLoading || !_hasMoreItems) {
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final result = await _apiClient.searchMedia(
        query: widget.filters?.query,
        mediaType: widget.filters?.mediaType,
        startDate: widget.filters?.startDate,
        endDate: widget.filters?.endDate,
        tags: widget.filters?.tags,
        collectionId: widget.collectionId,
        sortBy: widget.filters?.sortBy ?? 'created_at',
        sortOrder: widget.filters?.sortOrder ?? 'desc',
        page: _currentPage,
        limit: widget.itemsPerPage,
      );

      if (result.success && result.data != null) {
        setState(() {
          _items.addAll(result.data!.items);
          _currentPage++;
          _hasMoreItems = result.data!.items.length == widget.itemsPerPage;
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = result.error ?? 'Failed to load media';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  /// Refresh items
  Future<void> _refreshItems() async {
    _currentPage = 1;
    _hasMoreItems = true;
    _items.clear();
    _selectedItems.clear();
    await _loadMoreItems();
  }

  /// Handle scroll for infinite loading
  void _onScroll() {
    if (!widget.enableInfiniteScroll) return;
    
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent * 0.8) {
      _loadMoreItems();
    }
  }

  /// Calculate responsive layout parameters
  void _calculateLayout(BoxConstraints constraints) {
    final screenWidth = constraints.maxWidth;
    
    if (screenWidth < 600) {
      // Mobile: 2 columns
      _crossAxisCount = 2;
      _childAspectRatio = 1.0;
      _itemSpacing = AppSpacing.sm;
    } else if (screenWidth < 900) {
      // Tablet: 3 columns
      _crossAxisCount = 3;
      _childAspectRatio = 1.0;
      _itemSpacing = AppSpacing.md;
    } else if (screenWidth < 1200) {
      // Small desktop: 4 columns
      _crossAxisCount = 4;
      _childAspectRatio = 1.0;
      _itemSpacing = AppSpacing.md;
    } else {
      // Large desktop: 5 columns
      _crossAxisCount = 5;
      _childAspectRatio = 1.0;
      _itemSpacing = AppSpacing.lg;
    }
  }

  /// Toggle item selection
  void _toggleSelection(MediaItem item) {
    if (!widget.enableSelection) return;

    setState(() {
      if (_selectedItems.contains(item.id)) {
        _selectedItems.remove(item.id);
      } else {
        _selectedItems.add(item.id);
      }
    });

    // Notify parent of selection changes
    final selectedItems = _items.where((item) => 
        _selectedItems.contains(item.id)).toList();
    widget.onSelectionChanged?.call(selectedItems);
  }

  /// Clear selection
  void _clearSelection() {
    setState(() {
      _selectedItems.clear();
    });
    widget.onSelectionChanged?.call([]);
  }

  /// Select all visible items
  void _selectAll() {
    setState(() {
      _selectedItems.addAll(_items.map((item) => item.id));
    });
    widget.onSelectionChanged?.call(_items);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        _calculateLayout(constraints);
        
        return Column(
          children: [
            // Selection bar
            if (widget.enableSelection && _selectedItems.isNotEmpty)
              _buildSelectionBar(),
            
            // Gallery content
            Expanded(
              child: _buildGalleryContent(),
            ),
          ],
        );
      },
    );
  }

  /// Build selection bar
  Widget _buildSelectionBar() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: const BoxDecoration(
        color: AppColors.primary,
        border: Border(
          bottom: BorderSide(color: AppColors.border),
        ),
      ),
      child: Row(
        children: [
          Text(
            '${_selectedItems.length} selected',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textOnPrimary,
              fontWeight: FontWeight.w500,
            ),
          ),
          const Spacer(),
          TextButton(
            onPressed: _selectAll,
            child: Text(
              'Select All',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textOnPrimary,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          TextButton(
            onPressed: _clearSelection,
            child: Text(
              'Clear',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textOnPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Build main gallery content
  Widget _buildGalleryContent() {
    if (_error != null && _items.isEmpty) {
      return _buildErrorState();
    }

    if (_items.isEmpty && !_isLoading) {
      return _buildEmptyState();
    }

    return RefreshIndicator(
      onRefresh: _refreshItems,
      child: CustomScrollView(
        controller: _scrollController,
        slivers: [
          // Grid
          SliverMasonryGrid.count(
            crossAxisCount: _crossAxisCount,
            mainAxisSpacing: _itemSpacing,
            crossAxisSpacing: _itemSpacing,
            childCount: _items.length + (_isLoading ? 1 : 0),
            itemBuilder: (context, index) {
              if (index >= _items.length) {
                return _buildLoadingItem();
              }
              
              final item = _items[index];
              return _MediaGridItem(
                item: item,
                isSelected: _selectedItems.contains(item.id),
                enableSelection: widget.enableSelection,
                apiClient: widget.apiClient,
                onTap: () => widget.onItemTap?.call(item),
                onLongPress: () {
                  if (widget.enableSelection) {
                    _toggleSelection(item);
                  }
                  widget.onItemLongPress?.call(item);
                },
                onSelectionToggle: () => _toggleSelection(item),
              );
            },
          ),
          
          // Loading indicator
          if (_isLoading && _items.isNotEmpty)
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.lg),
                child: Center(
                  child: CircularProgressIndicator(),
                ),
              ),
            ),
          
          // End message
          if (!_hasMoreItems && _items.isNotEmpty)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Center(
                  child: Text(
                    'No more items to load',
                    style: AppTextStyles.caption,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  /// Build loading item placeholder
  Widget _buildLoadingItem() {
    return Container(
      height: 200,
      decoration: BoxDecoration(
        color: AppColors.gray200,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: const Center(
        child: CircularProgressIndicator(),
      ),
    );
  }

  /// Build error state
  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: AppColors.error,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Failed to load media',
            style: AppTextStyles.h5,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            _error!,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton(
            onPressed: _refreshItems,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  /// Build empty state
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.photo_library_outlined,
            size: 64,
            color: AppColors.textTertiary,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No media found',
            style: AppTextStyles.h5.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Try adjusting your filters or upload some media',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textTertiary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

/// Individual media grid item
class _MediaGridItem extends StatelessWidget {
  final MediaItem item;
  final bool isSelected;
  final bool enableSelection;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final VoidCallback? onSelectionToggle;
  final ApiClient? apiClient;

  const _MediaGridItem({
    required this.item,
    required this.isSelected,
    required this.enableSelection,
    this.onTap,
    this.onLongPress,
    this.onSelectionToggle,
    this.apiClient,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enableSelection && isSelected ? onSelectionToggle : onTap,
      onLongPress: onLongPress,
      child: AnimatedContainer(
        duration: AppDurations.fast,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: isSelected
              ? Border.all(color: AppColors.primary, width: 3)
              : null,
          boxShadow: isSelected
              ? [AppShadows.md]
              : [AppShadows.sm],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.md),
          child: Stack(
            children: [
              // Media content
              _buildMediaContent(),
              
              // Selection overlay
              if (enableSelection)
                _buildSelectionOverlay(),
              
              // Media type indicator
              _buildTypeIndicator(),
              
              // Duration indicator (for videos)
              if (item.mediaType == MediaType.video && item.duration != null)
                _buildDurationIndicator(),
            ],
          ),
        ),
      ),
    );
  }

  /// Build media content (thumbnail/preview)
  Widget _buildMediaContent() {
    // Get authentication headers from ApiClient if available
    Map<String, String> headers = {};
    if (apiClient != null && apiClient!.authToken != null) {
      headers['Authorization'] = 'Bearer ${apiClient!.authToken}';
    }

    // Convert relative URLs to absolute URLs
    String? imageUrl = item.thumbnailUrl ?? item.url;
    if (imageUrl != null && imageUrl.startsWith('/')) {
      // Convert relative URL to absolute URL using the backend base URL
      imageUrl = 'http://localhost:8080$imageUrl';
    }

    // Debug logging (can be removed in production)
    // print('DEBUG: MediaItem ${item.id} - thumbnailUrl: ${item.thumbnailUrl}, url: ${item.url}');
    // print('DEBUG: Final imageUrl: $imageUrl');
    // print('DEBUG: Headers: $headers');

    return AspectRatio(
      aspectRatio: 1.0,
      child: Image.network(
        imageUrl ?? '',
        headers: headers,
        fit: BoxFit.cover,
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) {
            return child;
          }
          return Container(
            color: AppColors.gray200,
            child: const Center(
              child: CircularProgressIndicator(),
            ),
          );
        },
        errorBuilder: (context, error, stackTrace) {
          // Show appropriate error handling for non-image files or access denied
          return Container(
            color: AppColors.gray200,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  _getMediaTypeIcon(),
                  size: 32,
                  color: AppColors.textTertiary,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  item.originalFilename,
                  style: AppTextStyles.caption.copyWith(
                    color: AppColors.textTertiary,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (item.mediaType != MediaType.image)
                  Text(
                    '${item.mediaType.name.toUpperCase()} FILE',
                    style: AppTextStyles.caption.copyWith(
                      color: AppColors.textSecondary,
                      fontSize: 10,
                    ),
                    textAlign: TextAlign.center,
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  /// Build selection overlay
  Widget _buildSelectionOverlay() {
    return Positioned.fill(
      child: AnimatedContainer(
        duration: AppDurations.fast,
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withOpacity(0.3)
              : Colors.transparent,
        ),
        child: isSelected
            ? const Center(
                child: Icon(
                  Icons.check_circle,
                  color: AppColors.white,
                  size: 32,
                ),
              )
            : null,
      ),
    );
  }

  /// Build type indicator
  Widget _buildTypeIndicator() {
    return Positioned(
      top: AppSpacing.sm,
      left: AppSpacing.sm,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xs,
          vertical: 2,
        ),
        decoration: BoxDecoration(
          color: _getMediaTypeColor().withOpacity(0.9),
          borderRadius: BorderRadius.circular(AppRadius.xs),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getMediaTypeIcon(),
              size: 12,
              color: AppColors.white,
            ),
            const SizedBox(width: 2),
            Text(
              item.mediaType.name.toUpperCase(),
              style: AppTextStyles.overline.copyWith(
                color: AppColors.white,
                fontSize: 8,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build duration indicator for videos
  Widget _buildDurationIndicator() {
    final duration = item.duration!;
    final minutes = duration ~/ 60;
    final seconds = duration % 60;
    
    return Positioned(
      bottom: AppSpacing.sm,
      right: AppSpacing.sm,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xs,
          vertical: 2,
        ),
        decoration: BoxDecoration(
          color: AppColors.black.withOpacity(0.7),
          borderRadius: BorderRadius.circular(AppRadius.xs),
        ),
        child: Text(
          '${minutes.toString().padLeft(2, '0')}:'
          '${seconds.toString().padLeft(2, '0')}',
          style: AppTextStyles.caption.copyWith(
            color: AppColors.white,
            fontSize: 10,
          ),
        ),
      ),
    );
  }

  /// Get media type icon
  IconData _getMediaTypeIcon() {
    switch (item.mediaType) {
      case MediaType.image:
        return Icons.image;
      case MediaType.video:
        return Icons.play_arrow;
      case MediaType.audio:
        return Icons.music_note;
      case MediaType.document:
        return Icons.description;
      case MediaType.pdf:
        return Icons.picture_as_pdf;
      case MediaType.text:
        return Icons.text_snippet;
      case MediaType.archive:
        return Icons.archive;
      case MediaType.other:
        return Icons.insert_drive_file;
    }
  }

  /// Get media type color
  Color _getMediaTypeColor() {
    switch (item.mediaType) {
      case MediaType.image:
        return AppColors.imageColor;
      case MediaType.video:
        return AppColors.videoColor;
      case MediaType.audio:
        return AppColors.audioColor;
      case MediaType.document:
        return AppColors.documentColor;
      case MediaType.pdf:
        return AppColors.documentColor; // Use same color as document
      case MediaType.text:
        return AppColors.documentColor; // Use same color as document
      case MediaType.archive:
        return AppColors.documentColor; // Use same color as document
      case MediaType.other:
        return AppColors.documentColor; // Use same color as document
    }
  }
}

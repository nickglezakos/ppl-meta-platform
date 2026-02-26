import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import '../core/config.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';
import '../core/api/api_client.dart';
import '../providers/workflow_providers.dart';

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
  State<ResponsiveMediaGallery> createState() => ResponsiveMediaGalleryState();
}

class ResponsiveMediaGalleryState extends State<ResponsiveMediaGallery> {
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
        collectionId: widget.filters?.collectionId ?? widget.collectionId,
        collectionIds: widget.filters?.collectionIds,
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

  /// Public method to refresh items from parent widgets
  Future<void> refresh() async {
    await _refreshItems();
  }

  /// Get currently selected items
  List<MediaItem> get selectedItems {
    return _items.where((item) => _selectedItems.contains(item.id)).toList();
  }

  /// Clear all selections
  void clearSelections() {
    _clearSelection();
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
class _MediaGridItem extends ConsumerWidget {
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
  Widget build(BuildContext context, WidgetRef ref) {
    // Get workflow status for this media item
    final workflowState = ref.watch(mediaWorkflowProvider(item.id));
    
    return GestureDetector(
      onTap: () {
        if (enableSelection) {
          onSelectionToggle?.call();
        } else {
          onTap?.call();
        }
      },
      onLongPress: () {
        // Call original long press if provided
        onLongPress?.call();
        
        // Show workflow trigger dialog for testing
        _showWorkflowDialog(context, ref);
      },
      child: AnimatedContainer(
        duration: AppDurations.fast,
        decoration: BoxDecoration(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: Colors.transparent, width: 4),
          boxShadow: [AppShadows.sm],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.md),
          child: Stack(
            children: [
              // Media content
              _buildMediaContent(),
              
              // Video play button overlay
              if (item.mediaType == MediaType.video)
                _buildVideoPlayOverlay(),
              
              // Selection overlay
              if (enableSelection)
                _buildSelectionOverlay(),
              
              // Media type indicator
              _buildTypeIndicator(),
              
              // Duration indicator (for videos)
              if (item.mediaType == MediaType.video && item.duration != null)
                _buildDurationIndicator(),
              
              // NEW: Workflow progress overlay
              _buildWorkflowProgressOverlay(workflowState),
              
              // NEW: Processing status badge
              _buildProcessingStatusBadge(workflowState),
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
      imageUrl = '${Config.gatewayServiceUrl}$imageUrl';
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
        fit: BoxFit.contain, // Changed from cover to maintain aspect ratio
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

  /// Build video play button overlay
  Widget _buildVideoPlayOverlay() {
    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.black.withOpacity(0.3),
        ),
        child: Center(
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.black.withOpacity(0.7),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.play_arrow,
              color: AppColors.white,
              size: 32,
            ),
          ),
        ),
      ),
    );
  }

  /// Build selection overlay - just the tick icon
  Widget _buildSelectionOverlay() {
    if (!enableSelection || !isSelected) {
      return const SizedBox.shrink();
    }

    return Positioned(
      top: AppSpacing.sm,
      right: AppSpacing.sm,
      child: AnimatedScale(
        scale: 1.0,
        duration: AppDurations.fast,
        child: Container(
          width: 26,
          height: 26,
          decoration: BoxDecoration(
            color: AppColors.primary,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.5),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: const Icon(
            Icons.check,
            color: AppColors.white,
            size: 18,
          ),
        ),
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

  /// Build workflow progress overlay
  Widget _buildWorkflowProgressOverlay(MediaWorkflowState workflowState) {
    if (!workflowState.isProcessing) return const SizedBox.shrink();
    
    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.black.withOpacity(0.5),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(
                value: workflowState.progress,
                color: AppColors.primary,
                strokeWidth: 3,
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                '${((workflowState.progress ?? 0.0) * 100).toInt()}%',
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build processing status badge
  Widget _buildProcessingStatusBadge(MediaWorkflowState workflowState) {
    if (workflowState.isIdle) return const SizedBox.shrink();
    
    return Positioned(
      bottom: AppSpacing.sm,
      left: AppSpacing.sm,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xs,
          vertical: 2,
        ),
        decoration: BoxDecoration(
          color: _getWorkflowStatusColor(workflowState.status),
          borderRadius: BorderRadius.circular(AppRadius.xs),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getWorkflowStatusIcon(workflowState.status),
              size: 12,
              color: AppColors.white,
            ),
            const SizedBox(width: 4),
            Text(
              workflowState.status.displayName,
              style: AppTextStyles.caption.copyWith(
                color: AppColors.white,
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Get workflow status color
  Color _getWorkflowStatusColor(MediaWorkflowStatus status) {
    switch (status) {
      case MediaWorkflowStatus.idle:
        return AppColors.gray500;
      case MediaWorkflowStatus.queued:
        return AppColors.warning;
      case MediaWorkflowStatus.processing:
        return AppColors.primary;
      case MediaWorkflowStatus.completed:
        return AppColors.success;
      case MediaWorkflowStatus.failed:
        return AppColors.error;
      case MediaWorkflowStatus.stopping:
        return AppColors.warning;
      case MediaWorkflowStatus.cancelled:
        return Colors.grey;
    }
  }

  /// Get workflow status icon
  IconData _getWorkflowStatusIcon(MediaWorkflowStatus status) {
    switch (status) {
      case MediaWorkflowStatus.idle:
        return Icons.hourglass_empty;
      case MediaWorkflowStatus.queued:
        return Icons.queue;
      case MediaWorkflowStatus.processing:
        return Icons.psychology;
      case MediaWorkflowStatus.completed:
        return Icons.check_circle;
      case MediaWorkflowStatus.failed:
        return Icons.error;
      case MediaWorkflowStatus.stopping:
        return Icons.stop_circle;
      case MediaWorkflowStatus.cancelled:
        return Icons.cancel;
    }
  }

  /// Show workflow trigger dialog for testing
  void _showWorkflowDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Start Face Detection'),
        content: Text('Start face detection workflow for:\n${item.originalFilename}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              // Start workflow with default "two_stage" method
              ref.read(mediaWorkflowProvider(item.id).notifier).startWorkflow('two_stage');
              Navigator.of(context).pop();
              
              // Show success snackbar
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Started face detection for ${item.originalFilename}'),
                  backgroundColor: AppColors.success,
                ),
              );
            },
            child: const Text('Start Workflow'),
          ),
        ],
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

import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';
import '../widgets/responsive_media_gallery.dart';
import '../widgets/advanced_search_interface.dart';
import '../widgets/share_dialog.dart';

/// Gallery screen with search and responsive media display
class GalleryScreen extends StatefulWidget {
  const GalleryScreen({super.key});

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen> {
  MediaSearchFilters _currentFilters = MediaSearchFilters();
  List<MediaItem> _selectedItems = [];
  bool _isSelectionMode = false;
  bool _showSearch = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: _isSelectionMode
            ? Text('${_selectedItems.length} selected')
            : const Text('Media Gallery'),
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        leading: _isSelectionMode
            ? IconButton(
                onPressed: _exitSelectionMode,
                icon: const Icon(Icons.close),
              )
            : null,
        actions: [
          if (!_isSelectionMode) ...[
            IconButton(
              onPressed: _toggleSearch,
              icon: Icon(_showSearch ? Icons.search_off : Icons.search),
              tooltip: 'Search',
            ),
            IconButton(
              onPressed: _enterSelectionMode,
              icon: const Icon(Icons.checklist),
              tooltip: 'Select items',
            ),
          ] else ...[
            if (_selectedItems.isNotEmpty) ...[
              IconButton(
                onPressed: _shareSelectedItems,
                icon: const Icon(Icons.share),
                tooltip: 'Share',
              ),
              IconButton(
                onPressed: _deleteSelectedItems,
                icon: const Icon(Icons.delete),
                tooltip: 'Delete',
              ),
            ],
          ],
          IconButton(
            onPressed: () => Navigator.pushNamed(context, '/upload'),
            icon: const Icon(Icons.add_photo_alternate),
            tooltip: 'Upload',
          ),
        ],
      ),
      body: Column(
        children: [
          // Search interface
          if (_showSearch)
            AdvancedSearchInterface(
              initialFilters: _currentFilters,
              onSearch: _applyFilters,
              onClear: _clearFilters,
              availableTags: const [
                'work', 'personal', 'project', 'meeting', 'vacation',
                'family', 'friends', 'travel', 'food', 'nature',
              ],
              availableCollections: const [
                'Work Documents', 'Family Photos', 'Project Assets',
                'Meeting Notes', 'Travel Memories',
              ],
            ),
          
          // Media gallery
          Expanded(
            child: ResponsiveMediaGallery(
              filters: _currentFilters,
              enableSelection: _isSelectionMode,
              enableInfiniteScroll: true,
              onItemTap: _handleItemTap,
              onItemLongPress: _handleItemLongPress,
              onSelectionChanged: _handleSelectionChanged,
            ),
          ),
        ],
      ),
      floatingActionButton: !_isSelectionMode
          ? FloatingActionButton(
              onPressed: () => Navigator.pushNamed(context, '/upload'),
              child: const Icon(Icons.add),
              tooltip: 'Upload media',
            )
          : null,
    );
  }

  /// Toggle search interface visibility
  void _toggleSearch() {
    setState(() {
      _showSearch = !_showSearch;
    });
  }

  /// Apply search filters
  void _applyFilters(MediaSearchFilters filters) {
    setState(() {
      _currentFilters = filters;
    });
  }

  /// Clear search filters
  void _clearFilters() {
    setState(() {
      _currentFilters = MediaSearchFilters();
    });
  }

  /// Enter selection mode
  void _enterSelectionMode() {
    setState(() {
      _isSelectionMode = true;
      _selectedItems.clear();
    });
  }

  /// Exit selection mode
  void _exitSelectionMode() {
    setState(() {
      _isSelectionMode = false;
      _selectedItems.clear();
    });
  }

  /// Handle item tap
  void _handleItemTap(MediaItem item) {
    if (_isSelectionMode) {
      _toggleItemSelection(item);
    } else {
      _openItemDetails(item);
    }
  }

  /// Handle item long press
  void _handleItemLongPress(MediaItem item) {
    if (!_isSelectionMode) {
      _enterSelectionMode();
      _toggleItemSelection(item);
    }
  }

  /// Handle selection changes
  void _handleSelectionChanged(List<MediaItem> selectedItems) {
    setState(() {
      _selectedItems = selectedItems;
    });
  }

  /// Toggle item selection
  void _toggleItemSelection(MediaItem item) {
    setState(() {
      if (_selectedItems.any((i) => i.id == item.id)) {
        _selectedItems.removeWhere((i) => i.id == item.id);
      } else {
        _selectedItems.add(item);
      }
    });
  }

  /// Open item details
  void _openItemDetails(MediaItem item) {
    showDialog(
      context: context,
      builder: (context) => _MediaDetailsDialog(item: item),
    );
  }

  /// Share selected items
  void _shareSelectedItems() {
    if (_selectedItems.isEmpty) return;
    
    showDialog(
      context: context,
      builder: (context) => ShareDialog(items: _selectedItems),
    );
  }

  /// Delete selected items
  void _deleteSelectedItems() async {
    if (_selectedItems.isEmpty) return;
    
    final confirmed = await _showDeleteConfirmation();
    if (!confirmed) return;
    
    // TODO: Implement delete functionality
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('${_selectedItems.length} items deleted'),
        backgroundColor: AppColors.success,
      ),
    );
    
    _exitSelectionMode();
  }

  /// Show delete confirmation dialog
  Future<bool> _showDeleteConfirmation() async {
    return await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Items'),
        content: Text(
          'Are you sure you want to delete ${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'}? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    ) ?? false;
  }
}

/// Media details dialog
class _MediaDetailsDialog extends StatelessWidget {
  final MediaItem item;

  const _MediaDetailsDialog({required this.item});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Container(
        width: 500,
        height: 600,
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  _getMediaTypeIcon(item.mediaType),
                  color: _getMediaTypeColor(item.mediaType),
                  size: 28,
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.filename,
                        style: AppTextStyles.h6,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        item.mediaType.name.toUpperCase(),
                        style: AppTextStyles.overline.copyWith(
                          color: _getMediaTypeColor(item.mediaType),
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            
            const SizedBox(height: AppSpacing.lg),
            
            // Preview (if available)
            if (item.thumbnailUrl != null)
              Container(
                height: 200,
                width: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  border: Border.all(color: AppColors.border),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  child: Image.network(
                    item.thumbnailUrl!,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        color: AppColors.gray200,
                        child: Icon(
                          _getMediaTypeIcon(item.mediaType),
                          size: 64,
                          color: _getMediaTypeColor(item.mediaType),
                        ),
                      );
                    },
                  ),
                ),
              ),
            
            const SizedBox(height: AppSpacing.lg),
            
            // Details
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _DetailItem(
                      label: 'File Size',
                      value: '${(item.fileSize / 1024 / 1024).toStringAsFixed(1)} MB',
                    ),
                    _DetailItem(
                      label: 'Upload Date',
                      value: _formatDate(item.createdAt),
                    ),
                    if (item.duration != null)
                      _DetailItem(
                        label: 'Duration',
                        value: _formatDuration(item.duration!),
                      ),
                    if (item.metadata.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Metadata',
                        style: AppTextStyles.labelLarge,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      ...item.metadata.entries.map((entry) {
                        return _DetailItem(
                          label: entry.key,
                          value: entry.value.toString(),
                        );
                      }),
                    ],
                  ],
                ),
              ),
            ),
            
            // Actions
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      // TODO: Implement download
                    },
                    icon: const Icon(Icons.download),
                    label: const Text('Download'),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      Navigator.pop(context);
                      showDialog(
                        context: context,
                        builder: (context) => ShareDialog(items: [item]),
                      );
                    },
                    icon: const Icon(Icons.share),
                    label: const Text('Share'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Get media type icon
  IconData _getMediaTypeIcon(MediaType type) {
    switch (type) {
      case MediaType.image:
        return Icons.image;
      case MediaType.video:
        return Icons.videocam;
      case MediaType.audio:
        return Icons.audiotrack;
      case MediaType.document:
        return Icons.description;
    }
  }

  /// Get media type color
  Color _getMediaTypeColor(MediaType type) {
    switch (type) {
      case MediaType.image:
        return AppColors.imageColor;
      case MediaType.video:
        return AppColors.videoColor;
      case MediaType.audio:
        return AppColors.audioColor;
      case MediaType.document:
        return AppColors.documentColor;
    }
  }

  /// Format date for display
  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year} at ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }

  /// Format duration for display
  String _formatDuration(int seconds) {
    final hours = seconds ~/ 3600;
    final minutes = (seconds % 3600) ~/ 60;
    final secs = seconds % 60;
    
    if (hours > 0) {
      return '${hours}:${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
    } else {
      return '${minutes}:${secs.toString().padLeft(2, '0')}';
    }
  }
}

/// Detail item widget
class _DetailItem extends StatelessWidget {
  final String label;
  final String value;

  const _DetailItem({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: AppTextStyles.labelMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

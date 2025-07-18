import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../core/api/api_client.dart';
import '../models/media_models.dart';
import '../widgets/collection_management.dart';
import '../widgets/responsive_media_gallery.dart';

/// Collections screen with management and media display
class CollectionsScreen extends ConsumerStatefulWidget {
  const CollectionsScreen({super.key});

  @override
  ConsumerState<CollectionsScreen> createState() => _CollectionsScreenState();
}

class _CollectionsScreenState extends ConsumerState<CollectionsScreen> {
  MediaCollection? _selectedCollection;
  List<MediaItem> _selectedItems = [];
  bool _isSelectionMode = false;

  @override
  Widget build(BuildContext context) {
    final apiClient = ref.watch(apiClientProvider);
    return Scaffold(
      appBar: AppBar(
        title: _selectedCollection != null
            ? Text(_selectedCollection!.name)
            : const Text('Collections'),
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        leading: _selectedCollection != null
            ? IconButton(
                onPressed: () {
                  setState(() {
                    _selectedCollection = null;
                    _isSelectionMode = false;
                    _selectedItems.clear();
                  });
                },
                icon: const Icon(Icons.arrow_back),
              )
            : null,
        actions: [
          if (_selectedCollection != null) ...[
            if (!_isSelectionMode)
              IconButton(
                onPressed: _enterSelectionMode,
                icon: const Icon(Icons.checklist),
                tooltip: 'Select items',
              )
            else
              IconButton(
                onPressed: _exitSelectionMode,
                icon: const Icon(Icons.close),
                tooltip: 'Cancel selection',
              ),
            IconButton(
              onPressed: _showCollectionMenu,
              icon: const Icon(Icons.more_vert),
              tooltip: 'Collection options',
            ),
          ],
        ],
      ),
      body: _selectedCollection == null
          ? _buildCollectionsList()
          : _buildCollectionDetails(apiClient),
    );
  }

  /// Build collections list view
  Widget _buildCollectionsList() {
    final apiClient = ref.watch(apiClientProvider);
    return CollectionManagement(
      apiClient: apiClient,
      onCollectionSelected: (collection) {
        setState(() {
          _selectedCollection = collection;
        });
      },
      onItemsAddedToCollection: (items, collection) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${items.length} items added to "${collection.name}"',
            ),
            backgroundColor: AppColors.success,
          ),
        );
      },
      selectedItems: _selectedItems,
    );
  }

  /// Build collection details view
  Widget _buildCollectionDetails(ApiClient apiClient) {
    return Column(
      children: [
        // Collection header
        _buildCollectionHeader(),
        
        // Collection media
        Expanded(
          child: ResponsiveMediaGallery(
            collectionId: _selectedCollection!.id,
            enableSelection: _isSelectionMode,
            enableInfiniteScroll: true,
            apiClient: apiClient,
            onItemTap: _handleItemTap,
            onItemLongPress: _handleItemLongPress,
            onSelectionChanged: _handleSelectionChanged,
          ),
        ),
      ],
    );
  }

  /// Build collection header
  Widget _buildCollectionHeader() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppColors.border),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: const Icon(
                  Icons.collections,
                  color: AppColors.primary,
                  size: 32,
                ),
              ),
              
              const SizedBox(width: AppSpacing.md),
              
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _selectedCollection!.name,
                      style: AppTextStyles.h4,
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      '${_selectedCollection!.itemCount} items',
                      style: AppTextStyles.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              
              if (_isSelectionMode && _selectedItems.isNotEmpty) ...[
                Text(
                  '${_selectedItems.length} selected',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                IconButton(
                  onPressed: _removeSelectedItems,
                  icon: const Icon(Icons.remove_circle_outline),
                  tooltip: 'Remove from collection',
                  color: AppColors.error,
                ),
              ],
            ],
          ),
          
          if (_selectedCollection!.description?.isNotEmpty ?? false) ...[
            const SizedBox(height: AppSpacing.md),
            Text(
              _selectedCollection!.description!,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          
          const SizedBox(height: AppSpacing.md),
          
          // Collection stats
          Row(
            children: [
              _CollectionStat(
                icon: Icons.schedule,
                label: 'Created',
                value: _formatDate(_selectedCollection!.createdAt),
              ),
              const SizedBox(width: AppSpacing.lg),
              _CollectionStat(
                icon: Icons.update,
                label: 'Updated',
                value: _formatDate(_selectedCollection!.updatedAt ?? _selectedCollection!.createdAt),
              ),
            ],
          ),
        ],
      ),
    );
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
      // Open item details
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
    // TODO: Implement item details dialog
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Opening details for: ${item.filename}'),
      ),
    );
  }

  /// Remove selected items from collection
  void _removeSelectedItems() async {
    if (_selectedItems.isEmpty) return;
    
    final confirmed = await _showRemoveConfirmation();
    if (!confirmed) return;
    
    // TODO: Implement remove functionality
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '${_selectedItems.length} items removed from collection',
        ),
        backgroundColor: AppColors.success,
      ),
    );
    
    _exitSelectionMode();
  }

  /// Show remove confirmation dialog
  Future<bool> _showRemoveConfirmation() async {
    return await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Items'),
        content: Text(
          'Remove ${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'} from "${_selectedCollection!.name}"? Items will not be deleted, only removed from this collection.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warning,
            ),
            child: const Text('Remove'),
          ),
        ],
      ),
    ) ?? false;
  }

  /// Show collection menu
  void _showCollectionMenu() {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.edit),
              title: const Text('Edit Collection'),
              onTap: () {
                Navigator.pop(context);
                _editCollection();
              },
            ),
            ListTile(
              leading: const Icon(Icons.share),
              title: const Text('Share Collection'),
              onTap: () {
                Navigator.pop(context);
                _shareCollection();
              },
            ),
            ListTile(
              leading: const Icon(Icons.download),
              title: const Text('Export Collection'),
              onTap: () {
                Navigator.pop(context);
                _exportCollection();
              },
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.delete, color: AppColors.error),
              title: const Text(
                'Delete Collection',
                style: TextStyle(color: AppColors.error),
              ),
              onTap: () {
                Navigator.pop(context);
                _deleteCollection();
              },
            ),
          ],
        ),
      ),
    );
  }

  /// Edit collection
  void _editCollection() {
    // TODO: Implement edit functionality
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Edit collection functionality coming soon'),
      ),
    );
  }

  /// Share collection
  void _shareCollection() {
    // TODO: Implement share functionality
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Share collection functionality coming soon'),
      ),
    );
  }

  /// Export collection
  void _exportCollection() {
    // TODO: Implement export functionality
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Export collection functionality coming soon'),
      ),
    );
  }

  /// Delete collection
  void _deleteCollection() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Collection'),
        content: Text(
          'Are you sure you want to delete "${_selectedCollection!.name}"? This action cannot be undone.',
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
    
    if (confirmed) {
      // TODO: Implement delete functionality
      setState(() {
        _selectedCollection = null;
      });
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Collection deleted'),
          backgroundColor: AppColors.success,
        ),
      );
    }
  }

  /// Format date for display
  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);
    
    if (difference.inDays == 0) {
      return 'Today';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else {
      return '${date.month}/${date.day}/${date.year}';
    }
  }
}

/// Collection stat widget
class _CollectionStat extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _CollectionStat({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(
          icon,
          size: 16,
          color: AppColors.textSecondary,
        ),
        const SizedBox(width: AppSpacing.xs),
        Text(
          '$label: ',
          style: AppTextStyles.caption.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        Text(
          value,
          style: AppTextStyles.caption.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/app_theme.dart';
import '../core/api/api_client.dart';
import '../models/media_models.dart';
import '../core/models/collection_models.dart';
import '../widgets/collection_management.dart';
import '../widgets/responsive_media_gallery.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/collection_organization_widget.dart';
import '../widgets/collection_picker_dialog.dart';
import '../widgets/media_details_dialog.dart';
import '../services/media_organization_service.dart';
import '../providers/media_organization_providers.dart';

/// Collections screen with management and media display
class CollectionsScreen extends ConsumerStatefulWidget {
  final String? initialCollectionId;
  
  const CollectionsScreen({
    super.key, 
    this.initialCollectionId,
  });

  @override
  ConsumerState<CollectionsScreen> createState() => _CollectionsScreenState();
}

class _CollectionsScreenState extends ConsumerState<CollectionsScreen> {
  MediaCollection? _selectedCollection;
  bool _isLoading = false;
  bool _isSelectionMode = false;
  List<MediaItem> _selectedItems = [];
  bool _showOrganizationWidget = false;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    print('🏗️ CollectionsScreen initState - initialCollectionId: ${widget.initialCollectionId}');
    // Note: Don't set _selectedCollection here directly, let CollectionManagement handle auto-selection
    // This ensures proper coordination between the widgets
  }
  
  // Keep a reference to the gallery widget to prevent recreating it
  ResponsiveMediaGallery? _mediaGallery;

  // Method to build media gallery only when needed
  ResponsiveMediaGallery _buildMediaGallery(ApiClient apiClient) {
    if (_mediaGallery == null || 
        _mediaGallery!.collectionId != _selectedCollection!.id ||
        _mediaGallery!.enableSelection != _isSelectionMode) {
      _mediaGallery = ResponsiveMediaGallery(
        key: ValueKey(_selectedCollection!.id), // Use collection ID as key
        collectionId: _selectedCollection!.id,
        enableSelection: _isSelectionMode,
        enableInfiniteScroll: true,
        apiClient: apiClient,
        onItemTap: _handleItemTap,
        onItemLongPress: _handleItemLongPress,
        onSelectionChanged: _handleSelectionChanged,
      );
    }
    return _mediaGallery!;
  }

  @override
  Widget build(BuildContext context) {
    print('🏗️ CollectionsScreen build() - initialCollectionId: ${widget.initialCollectionId}, _selectedCollection: ${_selectedCollection?.id}');
    
    final apiClient = ref.watch(apiClientProvider);
    return Scaffold(
      appBar: CustomAppBar(
        title: _selectedCollection != null
            ? _selectedCollection!.name
            : 'Collections',
        showBackButton: true, // Always show back button on collections screen
        onBackPressed: _selectedCollection != null 
            ? () {
                print('🔙 Back button pressed - navigating to collections list');
                // Clear selected collection and navigate back
                setState(() {
                  _selectedCollection = null;
                  _isSelectionMode = false;
                  _selectedItems.clear();
                  _showOrganizationWidget = false;
                });
                // Navigate back to collections list using router
                context.go('/collections');
              }
            : null,
        actions: _selectedCollection != null 
            ? [
                if (_isSelectionMode) ...[
                  // Selection count and actions
                  if (_selectedItems.isNotEmpty) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      margin: const EdgeInsets.only(right: 8),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${_selectedItems.length}',
                        style: AppTextStyles.labelMedium.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    
                    // Share button
                    IconButton(
                      onPressed: _shareSelectedItems,
                      icon: const Icon(Icons.share),
                      tooltip: 'Share selected',
                    ),
                    
                    // Add to collection button
                    IconButton(
                      onPressed: _addSelectedToCollection,
                      icon: const Icon(Icons.add_to_photos),
                      tooltip: 'Add to collection',
                    ),
                    
                    // Delete button
                    IconButton(
                      onPressed: _deleteSelectedItems,
                      icon: const Icon(Icons.delete),
                      tooltip: 'Delete selected',
                    ),
                  ],
                  
                  // Exit selection mode
                  IconButton(
                    onPressed: _exitSelectionMode,
                    icon: const Icon(Icons.close),
                    tooltip: 'Exit selection',
                  ),
                ] else ...[
                  // Enter selection mode
                  IconButton(
                    onPressed: _enterSelectionMode,
                    icon: const Icon(Icons.checklist),
                    tooltip: 'Multi-select',
                  ),
                ],
                
                // Organization button (only when in selection mode with items)
                if (_isSelectionMode && _selectedItems.isNotEmpty)
                  IconButton(
                    onPressed: _toggleOrganizationWidget,
                    icon: Icon(
                      _showOrganizationWidget 
                          ? Icons.keyboard_arrow_up 
                          : Icons.drive_file_move,
                    ),
                    tooltip: _showOrganizationWidget 
                        ? 'Hide organization panel' 
                        : 'Organize items',
                  ),
              ]
            : null,
      ),
      body: _selectedCollection == null
          ? _buildCollectionsList()
          : _buildCollectionDetails(apiClient),
      floatingActionButton: _selectedCollection != null && 
                          _isSelectionMode && 
                          _selectedItems.isNotEmpty &&
                          !_showOrganizationWidget
          ? FloatingActionButton.extended(
              onPressed: _toggleOrganizationWidget,
              icon: const Icon(Icons.drive_file_move),
              label: const Text('Organize'),
              backgroundColor: AppColors.primary,
            )
          : null,
    );
  }

  /// Build collections list view
  Widget _buildCollectionsList() {
    final apiClient = ref.watch(apiClientProvider);
    return CollectionManagement(
      apiClient: apiClient,
      initialCollectionId: widget.initialCollectionId,
      onCollectionSelected: (collection) {
        print('🎯 CollectionsScreen: Collection selected - ${collection?.name} (ID: ${collection?.id})');
        print('🎯 Current _selectedCollection before update: ${_selectedCollection?.name} (ID: ${_selectedCollection?.id})');
        setState(() {
          _selectedCollection = collection;
        });
        print('🎯 _selectedCollection after update: ${_selectedCollection?.name} (ID: ${_selectedCollection?.id})');
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
        
        // Organization widget (if shown)
        if (_showOrganizationWidget && _selectedItems.isNotEmpty)
          Container(
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: AppColors.border),
              ),
            ),
            child: CollectionOrganizationWidget(
              selectedMedia: _selectedItems,
              onMoveToCollection: _handleMoveToCollection,
              onCopyToCollection: _handleCopyToCollection,
              onCreateCollection: _handleCreateCollection,
              onCancel: () => setState(() => _showOrganizationWidget = false),
            ),
          ),
        
        // Collection media
        Expanded(
          child: _buildMediaGallery(apiClient),
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
                value: _selectedCollection!.createdAt != null 
                    ? _formatDate(_selectedCollection!.createdAt!) 
                    : 'Unknown',
              ),
              const SizedBox(width: AppSpacing.lg),
              _CollectionStat(
                icon: Icons.update,
                label: 'Updated',
                value: (_selectedCollection!.updatedAt ?? _selectedCollection!.createdAt) != null
                    ? _formatDate(_selectedCollection!.updatedAt ?? _selectedCollection!.createdAt!)
                    : 'Unknown',
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
    showDialog(
      context: context,
      builder: (context) => MediaDetailsDialog(item: item),
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

  /// Toggle organization widget visibility
  void _toggleOrganizationWidget() {
    setState(() {
      _showOrganizationWidget = !_showOrganizationWidget;
    });
  }

  /// Handle organization operation completion
  void _handleOrganizationComplete({
    required String operation,
    required int itemsCount,
    String? targetCollectionName,
  }) {
    // Hide organization widget
    setState(() {
      _showOrganizationWidget = false;
      _isSelectionMode = false;
      _selectedItems.clear();
    });

    // Show success message
    String message;
    switch (operation) {
      case 'move':
        message = '${itemsCount} item${itemsCount == 1 ? '' : 's'} moved to "${targetCollectionName}"';
        break;
      case 'copy':
        message = '${itemsCount} item${itemsCount == 1 ? '' : 's'} copied to "${targetCollectionName}"';
        break;
      case 'create':
        message = 'Created new collection "${targetCollectionName}" with ${itemsCount} item${itemsCount == 1 ? '' : 's'}';
        break;
      default:
        message = 'Organization operation completed';
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.success,
        duration: const Duration(seconds: 3),
      ),
    );

    // Refresh the gallery to reflect changes
    // Force rebuild to reflect changes
    setState(() {
      _mediaGallery = null; // This will force a rebuild of the gallery
    });
  }

  /// Handle move to collection operation
  void _handleMoveToCollection(List<MediaItem> items, String targetCollectionId) async {
    final organizationService = ref.read(mediaOrganizationServiceProvider);
    
    setState(() {
      _isProcessing = true;
    });

    try {
      final mediaIds = items.map((item) => item.mediaId).toList();
      final success = await organizationService.bulkMoveMedia(
        mediaIds,
        targetCollectionId,
      );

      if (success) {
        _handleOrganizationComplete(
          operation: 'move',
          itemsCount: items.length,
          targetCollectionName: 'selected collection',
        );
      } else {
        _showErrorMessage('Failed to move items');
      }
    } catch (e) {
      _showErrorMessage('Error moving items: $e');
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  /// Handle copy to collection operation
  void _handleCopyToCollection(List<MediaItem> items, String targetCollectionId) async {
    final organizationService = ref.read(mediaOrganizationServiceProvider);
    
    setState(() {
      _isProcessing = true;
    });

    try {
      final mediaIds = items.map((item) => item.mediaId).toList();
      // Use move functionality with copy flag (if supported) or implement separate copy logic
      final success = await organizationService.bulkMoveMedia(
        mediaIds,
        targetCollectionId,
      );

      if (success) {
        _handleOrganizationComplete(
          operation: 'copy',
          itemsCount: items.length,
          targetCollectionName: 'selected collection',
        );
      } else {
        _showErrorMessage('Failed to copy items');
      }
    } catch (e) {
      _showErrorMessage('Error copying items: $e');
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  /// Handle create collection operation
  void _handleCreateCollection(String collectionName, List<MediaItem> items) async {
    final organizationService = ref.read(mediaOrganizationServiceProvider);
    
    setState(() {
      _isProcessing = true;
    });

    try {
      final mediaIds = items.map((item) => item.mediaId).toList();
      final success = await organizationService.createCollectionFromMedia(
        collectionName,
        mediaIds,
      );

      if (success) {
        _handleOrganizationComplete(
          operation: 'create',
          itemsCount: items.length,
          targetCollectionName: collectionName,
        );
      } else {
        _showErrorMessage('Failed to create collection');
      }
    } catch (e) {
      _showErrorMessage('Error creating collection: $e');
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  /// Show error message
  void _showErrorMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.error,
        duration: const Duration(seconds: 4),
      ),
    );
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

  /// Share selected items
  void _shareSelectedItems() async {
    if (_selectedItems.isEmpty) return;
    
    try {
      final apiClient = ref.read(apiClientProvider);
      final mediaUrls = _selectedItems
          .map((item) => 'http://localhost:8080${item.url}')
          .toList();
      
      // TODO: Implement actual sharing functionality
      // For now, show a placeholder message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Sharing ${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'}...',
          ),
          backgroundColor: AppColors.info,
        ),
      );
      
      _exitSelectionMode();
    } catch (e) {
      _showErrorMessage('Error sharing items: $e');
    }
  }

  /// Delete selected items
  void _deleteSelectedItems() async {
    if (_selectedItems.isEmpty) return;
    
    final confirmed = await _showDeleteConfirmation();
    if (!confirmed) return;
    
    try {
      final apiClient = ref.read(apiClientProvider);
      
      // TODO: Implement actual deletion functionality
      // For now, show a placeholder message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'} deleted',
          ),
          backgroundColor: AppColors.success,
        ),
      );
      
      _exitSelectionMode();
    } catch (e) {
      _showErrorMessage('Error deleting items: $e');
    }
  }

  /// Add selected items to another collection
  void _addSelectedToCollection() async {
    if (_selectedItems.isEmpty) return;
    
    try {
      final mediaIds = _selectedItems.map((item) => item.id).toList();
      
      // Use the existing collection picker dialog
      await showDialog(
        context: context,
        builder: (context) => CollectionPickerDialog(
          mediaIds: mediaIds,
          title: 'Add ${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'} to Collection',
        ),
      );
      
      // Show success message after dialog closes
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'} added to collection',
          ),
          backgroundColor: AppColors.success,
        ),
      );
      _exitSelectionMode();
    } catch (e) {
      _showErrorMessage('Error adding to collection: $e');
    }
  }

  /// Show delete confirmation dialog
  Future<bool> _showDeleteConfirmation() async {
    return await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Items'),
        content: Text(
          'Permanently delete ${_selectedItems.length} item${_selectedItems.length == 1 ? '' : 's'}? This action cannot be undone.',
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

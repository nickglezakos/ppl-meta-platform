import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import '../core/models/api_response.dart';
import '../core/api/api_client.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';

/// Collection management interface with drag-and-drop organization
class CollectionManagement extends StatefulWidget {
  final Function(MediaCollection)? onCollectionSelected;
  final Function(List<MediaItem>, MediaCollection)? onItemsAddedToCollection;
  final List<MediaItem>? selectedItems;
  final ApiClient? apiClient;

  const CollectionManagement({
    super.key,
    this.onCollectionSelected,
    this.onItemsAddedToCollection,
    this.selectedItems,
    this.apiClient,
  });

  @override
  State<CollectionManagement> createState() => _CollectionManagementState();
}

class _CollectionManagementState extends State<CollectionManagement>
    with TickerProviderStateMixin {
  final TextEditingController _createController = TextEditingController();
  final TextEditingController _searchController = TextEditingController();
  
  late final MediaApiClient _apiClient;
  
  List<MediaCollection> _collections = [];
  MediaCollection? _selectedCollection;
  bool _isLoading = false;
  bool _isCreating = false;
  String? _error;
  
  // Drag and drop state
  MediaCollection? _dragTargetCollection;
  bool _isDragging = false;
  
  // Animation controllers
  late AnimationController _createAnimationController;
  late Animation<double> _createAnimation;

  @override
  void initState() {
    super.initState();
    
    _apiClient = MediaApiClient(widget.apiClient);
    
    _createAnimationController = AnimationController(
      duration: AppDurations.normal,
      vsync: this,
    );
    
    _createAnimation = CurvedAnimation(
      parent: _createAnimationController,
      curve: AppCurves.easeInOut,
    );
    
    _loadCollections();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _createAnimationController.dispose();
    _createController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  /// Load collections from API
  Future<void> _loadCollections() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Use the initialized MediaApiClient instance
      final response = await _apiClient.getCollections();
      
      if (response.success) {
        setState(() {
          _collections = response.data!;
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = response.error;
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

  /// Handle search input changes
  void _onSearchChanged() {
    // Implement real-time search filtering
    setState(() {
      // Filter collections based on search query
    });
  }

  /// Create new collection
  Future<void> _createCollection() async {
    final name = _createController.text.trim();
    if (name.isEmpty) return;

    setState(() {
      _isCreating = true;
    });

    try {
      // Use the initialized MediaApiClient instance
      final response = await _apiClient.createCollection(name: name);
      
      if (response.success) {
        setState(() {
          _collections.insert(0, response.data!);
          _createController.clear();
          _isCreating = false;
        });
      } else {
        setState(() {
          _isCreating = false;
        });
        // Show error message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to create collection: ${response.error}')),
        );
      }
      
      _createAnimationController.reverse();
      
      _showSuccessMessage('Collection "$name" created successfully');
    } catch (e) {
      setState(() {
        _isCreating = false;
      });
      
      _showErrorMessage('Failed to create collection: $e');
    }
  }

  /// Delete collection
  Future<void> _deleteCollection(MediaCollection collection) async {
    final confirmed = await _showDeleteConfirmation(collection.name);
    if (!confirmed) return;

    try {
      // Use the initialized MediaApiClient instance
      await _apiClient.deleteCollection(collection.id);
      
      setState(() {
        _collections.removeWhere((c) => c.id == collection.id);
        if (_selectedCollection?.id == collection.id) {
          _selectedCollection = null;
        }
      });
      
      _showSuccessMessage('Collection "${collection.name}" deleted');
    } catch (e) {
      _showErrorMessage('Failed to delete collection: $e');
    }
  }

  /// Rename collection
  Future<void> _renameCollection(MediaCollection collection) async {
    final newName = await _showRenameDialog(collection.name);
    if (newName == null || newName.trim().isEmpty) return;

    try {
      // Use the initialized MediaApiClient instance
      final response = await _apiClient.updateCollection(
        collectionId: collection.id,
        name: newName.trim(),
      );
      
      if (response.success) {
        setState(() {
          final index = _collections.indexWhere((c) => c.id == collection.id);
          if (index != -1) {
            _collections[index] = response.data!;
          }
          
          if (_selectedCollection?.id == collection.id) {
            _selectedCollection = response.data!;
          }
        });
        
        _showSuccessMessage('Collection renamed to "$newName"');
      } else {
        _showErrorMessage('Failed to rename collection: ${response.error}');
      }
    } catch (e) {
      _showErrorMessage('Failed to rename collection: $e');
    }
  }

  /// Add items to collection via drag and drop
  Future<void> _addItemsToCollection(
    List<MediaItem> items,
    MediaCollection collection,
  ) async {
    try {
      // Use the initialized MediaApiClient instance
      await _apiClient.addItemsToCollection(
        collectionId: collection.id,
        itemIds: items.map((item) => item.id).toList(),
      );
      
      // Update collection item count
      setState(() {
        final index = _collections.indexWhere((c) => c.id == collection.id);
        if (index != -1) {
          _collections[index] = _collections[index].copyWith(
            mediaCount: _collections[index].mediaCount + items.length,
          );
        }
      });
      
      widget.onItemsAddedToCollection?.call(items, collection);
      
      _showSuccessMessage(
        '${items.length} items added to "${collection.name}"',
      );
    } catch (e) {
      _showErrorMessage('Failed to add items to collection: $e');
    }
  }

  /// Show create collection dialog
  void _showCreateDialog() {
    _createAnimationController.forward();
  }

  /// Hide create collection dialog
  void _hideCreateDialog() {
    _createAnimationController.reverse();
    _createController.clear();
  }

  /// Show delete confirmation dialog
  Future<bool> _showDeleteConfirmation(String collectionName) async {
    return await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Collection'),
        content: Text(
          'Are you sure you want to delete "$collectionName"? This action cannot be undone.',
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

  /// Show rename dialog
  Future<String?> _showRenameDialog(String currentName) async {
    final controller = TextEditingController(text: currentName);
    
    return await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Collection'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Collection Name',
            border: OutlineInputBorder(),
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Rename'),
          ),
        ],
      ),
    );
  }

  /// Show success message
  void _showSuccessMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.success,
      ),
    );
  }

  /// Show error message
  void _showErrorMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.error,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with search and create button
        _buildHeader(),
        
        // Create collection form
        AnimatedBuilder(
          animation: _createAnimation,
          builder: (context, child) {
            return SizeTransition(
              sizeFactor: _createAnimation,
              child: _buildCreateForm(),
            );
          },
        ),
        
        // Collections list
        Expanded(
          child: _buildCollectionsList(),
        ),
      ],
    );
  }

  /// Build header section
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        children: [
          // Title
          Text(
            'Collections',
            style: AppTextStyles.h5,
          ),
          
          const Spacer(),
          
          // Search field
          SizedBox(
            width: 200,
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search collections...',
                prefixIcon: const Icon(Icons.search, size: 20),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm,
                  vertical: AppSpacing.sm,
                ),
                isDense: true,
              ),
            ),
          ),
          
          const SizedBox(width: AppSpacing.sm),
          
          // Create button
          ElevatedButton.icon(
            onPressed: _showCreateDialog,
            icon: const Icon(Icons.add),
            label: const Text('Create'),
          ),
        ],
      ),
    );
  }

  /// Build create collection form
  Widget _buildCreateForm() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppColors.border),
        ),
      ),
      child: Row(
        children: [
          // Name field
          Expanded(
            child: TextField(
              controller: _createController,
              decoration: const InputDecoration(
                labelText: 'Collection Name',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _createCollection(),
            ),
          ),
          
          const SizedBox(width: AppSpacing.md),
          
          // Create button
          ElevatedButton(
            onPressed: _isCreating ? null : _createCollection,
            child: _isCreating
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Create'),
          ),
          
          const SizedBox(width: AppSpacing.sm),
          
          // Cancel button
          TextButton(
            onPressed: _hideCreateDialog,
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  /// Build collections list
  Widget _buildCollectionsList() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_error != null) {
      return _buildErrorState();
    }

    if (_collections.isEmpty) {
      return _buildEmptyState();
    }

    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: _collections.length,
      itemBuilder: (context, index) {
        final collection = _collections[index];
        
        return _CollectionListItem(
          collection: collection,
          isSelected: _selectedCollection?.id == collection.id,
          isDragTarget: _dragTargetCollection?.id == collection.id,
          canAcceptDrop: widget.selectedItems?.isNotEmpty ?? false,
          onTap: () {
            setState(() {
              _selectedCollection = collection;
            });
            widget.onCollectionSelected?.call(collection);
          },
          onRename: () => _renameCollection(collection),
          onDelete: () => _deleteCollection(collection),
          onDragEnter: () {
            if (widget.selectedItems?.isNotEmpty ?? false) {
              setState(() {
                _dragTargetCollection = collection;
              });
            }
          },
          onDragLeave: () {
            setState(() {
              _dragTargetCollection = null;
            });
          },
          onDragAccept: (items) {
            _addItemsToCollection(items, collection);
            setState(() {
              _dragTargetCollection = null;
            });
          },
        );
      },
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
            'Failed to load collections',
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
            onPressed: _loadCollections,
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
            Icons.collections_outlined,
            size: 64,
            color: AppColors.textTertiary,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No collections yet',
            style: AppTextStyles.h5.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Create your first collection to organize your media',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textTertiary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton.icon(
            onPressed: _showCreateDialog,
            icon: const Icon(Icons.add),
            label: const Text('Create Collection'),
          ),
        ],
      ),
    );
  }
}

/// Individual collection list item
class _CollectionListItem extends StatelessWidget {
  final MediaCollection collection;
  final bool isSelected;
  final bool isDragTarget;
  final bool canAcceptDrop;
  final VoidCallback onTap;
  final VoidCallback onRename;
  final VoidCallback onDelete;
  final VoidCallback onDragEnter;
  final VoidCallback onDragLeave;
  final Function(List<MediaItem>) onDragAccept;

  const _CollectionListItem({
    required this.collection,
    required this.isSelected,
    required this.isDragTarget,
    required this.canAcceptDrop,
    required this.onTap,
    required this.onRename,
    required this.onDelete,
    required this.onDragEnter,
    required this.onDragLeave,
    required this.onDragAccept,
  });

  @override
  Widget build(BuildContext context) {
    return DragTarget<List<MediaItem>>(
      onWillAccept: (data) => canAcceptDrop,
      onAccept: onDragAccept,
      onMove: (_) => onDragEnter(),
      onLeave: (_) => onDragLeave(),
      builder: (context, candidateData, rejectedData) {
        return AnimatedContainer(
          duration: AppDurations.fast,
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          decoration: BoxDecoration(
            color: isSelected
                ? AppColors.primary.withOpacity(0.1)
                : (isDragTarget 
                    ? AppColors.secondary.withOpacity(0.1)
                    : AppColors.surface),
            border: Border.all(
              color: isSelected
                  ? AppColors.primary
                  : (isDragTarget 
                      ? AppColors.secondary
                      : AppColors.border),
              width: isSelected || isDragTarget ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: ListTile(
            contentPadding: const EdgeInsets.all(AppSpacing.md),
            leading: Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: const Icon(
                Icons.collections,
                color: AppColors.primary,
              ),
            ),
            title: Text(
              collection.name,
              style: AppTextStyles.bodyLarge.copyWith(
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '${collection.itemCount} items',
                  style: AppTextStyles.caption,
                ),
                if (collection.description?.isNotEmpty ?? false) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    collection.description!,
                    style: AppTextStyles.caption.copyWith(
                      color: AppColors.textTertiary,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Created ${_formatDate(collection.createdAt)}',
                  style: AppTextStyles.caption,
                ),
              ],
            ),
            trailing: _buildTrailingActions(),
            onTap: onTap,
          ),
        );
      },
    );
  }



  /// Build trailing actions menu
  Widget _buildTrailingActions() {
    return PopupMenuButton<String>(
      icon: const Icon(Icons.more_vert),
      onSelected: (action) {
        switch (action) {
          case 'rename':
            onRename();
            break;
          case 'delete':
            onDelete();
            break;
        }
      },
      itemBuilder: (context) => [
        const PopupMenuItem(
          value: 'rename',
          child: ListTile(
            leading: Icon(Icons.edit),
            title: Text('Rename'),
            dense: true,
          ),
        ),
        const PopupMenuItem(
          value: 'delete',
          child: ListTile(
            leading: Icon(Icons.delete, color: AppColors.error),
            title: Text(
              'Delete',
              style: TextStyle(color: AppColors.error),
            ),
            dense: true,
          ),
        ),
      ],
    );
  }

  /// Format date for display
  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);
    
    if (difference.inDays == 0) {
      return 'today';
    } else if (difference.inDays == 1) {
      return 'yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else if (difference.inDays < 30) {
      return '${difference.inDays ~/ 7} weeks ago';
    } else if (difference.inDays < 365) {
      return '${difference.inDays ~/ 30} months ago';
    } else {
      return '${difference.inDays ~/ 365} years ago';
    }
  }
}

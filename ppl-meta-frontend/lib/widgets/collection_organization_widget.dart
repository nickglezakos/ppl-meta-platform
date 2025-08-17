import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/models/collection_models.dart';
import '../models/media_models.dart' as media_lib;
import '../providers/media_organization_providers.dart';
import '../core/theme/app_theme.dart';

/// Widget for organizing collections and moving media between them
/// Provides collection selection dialog and organization tools
class CollectionOrganizationWidget extends ConsumerStatefulWidget {
  final List<media_lib.MediaItem> selectedMedia;
  final Function(List<media_lib.MediaItem>, String)? onMoveToCollection;
  final Function(List<media_lib.MediaItem>, String)? onCopyToCollection;
  final Function(String, List<media_lib.MediaItem>)? onCreateCollection;
  final VoidCallback? onCancel;

  const CollectionOrganizationWidget({
    super.key,
    required this.selectedMedia,
    this.onMoveToCollection,
    this.onCopyToCollection,
    this.onCreateCollection,
    this.onCancel,
  });

  @override
  ConsumerState<CollectionOrganizationWidget> createState() => 
      _CollectionOrganizationWidgetState();
}

class _CollectionOrganizationWidgetState 
    extends ConsumerState<CollectionOrganizationWidget> {
  final TextEditingController _newCollectionNameController = TextEditingController();
  final TextEditingController _newCollectionDescriptionController = TextEditingController();
  bool _showCreateNew = false;
  String _selectedAction = 'move'; // 'move', 'copy', 'create'

  @override
  void dispose() {
    _newCollectionNameController.dispose();
    _newCollectionDescriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final collectionsAsync = ref.watch(availableCollectionsProvider);
    final organizationService = ref.watch(mediaOrganizationServiceProvider);
    
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppRadius.lg),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        constraints: const BoxConstraints(maxWidth: 600),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: AppSpacing.lg),
            
            if (organizationService.isOperationInProgress)
              _buildProgressIndicator(organizationService)
            else if (organizationService.operationError != null)
              _buildErrorMessage(organizationService)
            else ...[
              _buildActionSelector(),
              const SizedBox(height: AppSpacing.md),
              
              if (_selectedAction == 'create')
                _buildCreateNewCollection()
              else
                _buildCollectionList(collectionsAsync),
            ],
            
            const SizedBox(height: AppSpacing.lg),
            _buildActionButtons(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Icon(
          Icons.folder_open,
          color: AppColors.primary,
          size: 24,
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Organize Media',
                style: AppTextStyles.h4,
              ),
              Text(
                '${widget.selectedMedia.length} item${widget.selectedMedia.length != 1 ? 's' : ''} selected',
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: widget.onCancel,
          icon: const Icon(Icons.close),
        ),
      ],
    );
  }

  Widget _buildActionSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Choose Action',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.sm),
        
        Row(
          children: [
            Expanded(
              child: _buildActionChip(
                'move',
                'Move to Collection',
                Icons.drive_file_move,
                'Move items to another collection',
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: _buildActionChip(
                'copy',
                'Copy to Collection',
                Icons.content_copy,
                'Copy items to another collection',
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: _buildActionChip(
                'create',
                'Create New',
                Icons.create_new_folder,
                'Create a new collection',
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildActionChip(String value, String label, IconData icon, String tooltip) {
    final isSelected = _selectedAction == value;
    
    return Tooltip(
      message: tooltip,
      child: FilterChip(
        selected: isSelected,
        onSelected: (selected) {
          if (selected) {
            setState(() {
              _selectedAction = value;
            });
          }
        },
        avatar: Icon(
          icon,
          size: 16,
          color: isSelected ? AppColors.primary : AppColors.textSecondary,
        ),
        label: Text(
          label,
          style: AppTextStyles.labelSmall.copyWith(
            color: isSelected ? AppColors.primary : AppColors.textSecondary,
          ),
        ),
        backgroundColor: isSelected ? AppColors.primary.withOpacity(0.1) : AppColors.surface,
        selectedColor: AppColors.primary.withOpacity(0.2),
        checkmarkColor: AppColors.primary,
      ),
    );
  }

  Widget _buildCollectionList(AsyncValue<List<MediaCollection>> collectionsAsync) {
    return collectionsAsync.when(
      data: (collections) {
        if (collections.isEmpty) {
          return _buildEmptyCollections();
        }
        
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Select Target Collection',
              style: AppTextStyles.labelLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            
            Container(
              height: 300,
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: ListView.builder(
                itemCount: collections.length,
                itemBuilder: (context, index) {
                  final collection = collections[index];
                  return _buildCollectionTile(collection);
                },
              ),
            ),
          ],
        );
      },
      loading: () => const Center(
        child: CircularProgressIndicator(),
      ),
      error: (error, stack) => _buildErrorState(error.toString()),
    );
  }

  Widget _buildCollectionTile(MediaCollection collection) {
    return ListTile(
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: AppColors.primary.withOpacity(0.1),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Icon(
          Icons.collections,
          color: AppColors.primary,
          size: 20,
        ),
      ),
      title: Text(
        collection.name,
        style: AppTextStyles.bodyMedium,
      ),
      subtitle: Text(
        '${collection.itemCount} items',
        style: AppTextStyles.caption,
      ),
      onTap: () => _handleCollectionSelection(collection),
      trailing: Icon(
        _selectedAction == 'move' ? Icons.drive_file_move : Icons.content_copy,
        color: AppColors.textSecondary,
      ),
    );
  }

  Widget _buildCreateNewCollection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Create New Collection',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.md),
        
        TextField(
          controller: _newCollectionNameController,
          decoration: InputDecoration(
            labelText: 'Collection Name',
            hintText: 'Enter collection name',
            prefixIcon: const Icon(Icons.collections),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        
        TextField(
          controller: _newCollectionDescriptionController,
          decoration: InputDecoration(
            labelText: 'Description (Optional)',
            hintText: 'Describe this collection',
            prefixIcon: const Icon(Icons.description),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
          ),
          maxLines: 3,
        ),
        const SizedBox(height: AppSpacing.md),
        
        // Quick template buttons
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            _buildTemplateChip('Security Event', 'Security incident collection'),
            _buildTemplateChip('Daily Captures', 'Daily camera captures'),
            _buildTemplateChip('Motion Alerts', 'Motion detection alerts'),
          ],
        ),
      ],
    );
  }

  Widget _buildTemplateChip(String name, String description) {
    return ActionChip(
      label: Text(name),
      onPressed: () {
        setState(() {
          _newCollectionNameController.text = name;
          _newCollectionDescriptionController.text = description;
        });
      },
    );
  }

  Widget _buildProgressIndicator(organizationService) {
    return Column(
      children: [
        LinearProgressIndicator(
          value: organizationService.operationProgress,
          backgroundColor: AppColors.border,
          valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
        ),
        const SizedBox(height: AppSpacing.sm),
        if (organizationService.currentOperationDescription != null)
          Text(
            organizationService.currentOperationDescription!,
            style: AppTextStyles.caption,
            textAlign: TextAlign.center,
          ),
      ],
    );
  }

  Widget _buildErrorMessage(organizationService) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(Icons.error, color: AppColors.error),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              organizationService.operationError!,
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.error),
            ),
          ),
          TextButton(
            onPressed: () => ref.read(mediaOrganizationServiceProvider).clearError(),
            child: const Text('Dismiss'),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyCollections() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.folder_outlined,
            size: 64,
            color: AppColors.textTertiary,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No collections available',
            style: AppTextStyles.bodyLarge.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Create a new collection to organize your media',
            style: AppTextStyles.caption.copyWith(
              color: AppColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(String error) {
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
            style: AppTextStyles.bodyLarge.copyWith(
              color: AppColors.error,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            error,
            style: AppTextStyles.caption.copyWith(
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    final organizationService = ref.watch(mediaOrganizationServiceProvider);
    final isDisabled = organizationService.isOperationInProgress;
    
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: isDisabled ? null : widget.onCancel,
          child: const Text('Cancel'),
        ),
        const SizedBox(width: AppSpacing.sm),
        
        if (_selectedAction == 'create')
          ElevatedButton(
            onPressed: isDisabled || _newCollectionNameController.text.trim().isEmpty
                ? null
                : _handleCreateCollection,
            child: const Text('Create Collection'),
          )
        else
          ElevatedButton(
            onPressed: isDisabled ? null : null, // Will be enabled when collection is selected
            child: Text(_selectedAction == 'move' ? 'Move Items' : 'Copy Items'),
          ),
      ],
    );
  }

  void _handleCollectionSelection(MediaCollection collection) {
    final mediaIds = widget.selectedMedia.map((m) => m.mediaId).toList();
    
    if (_selectedAction == 'move') {
      widget.onMoveToCollection?.call(widget.selectedMedia, collection.id);
    } else if (_selectedAction == 'copy') {
      widget.onCopyToCollection?.call(widget.selectedMedia, collection.id);
    }
  }

  void _handleCreateCollection() {
    final name = _newCollectionNameController.text.trim();
    if (name.isNotEmpty) {
      widget.onCreateCollection?.call(name, widget.selectedMedia);
    }
  }
}

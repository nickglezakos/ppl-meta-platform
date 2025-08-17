import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../core/models/collection_models.dart';
import '../services/media_api_client.dart';
import '../core/api/api_client.dart';

/// Dialog for selecting a collection to add media items to
class CollectionPickerDialog extends ConsumerStatefulWidget {
  final List<String> mediaIds;
  final String title;

  const CollectionPickerDialog({
    super.key,
    required this.mediaIds,
    this.title = 'Add to Collection',
  });

  @override
  ConsumerState<CollectionPickerDialog> createState() => _CollectionPickerDialogState();
}

class _CollectionPickerDialogState extends ConsumerState<CollectionPickerDialog> {
  List<MediaCollection> _collections = [];
  bool _isLoading = true;
  bool _isAdding = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCollections();
  }

  Future<void> _loadCollections() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });

      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);
      final response = await mediaApiClient.getCollections();

      if (response.success && response.data != null) {
        setState(() {
          _collections = response.data!;
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = response.error ?? 'Failed to load collections';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error loading collections: ${e.toString()}';
        _isLoading = false;
      });
    }
  }

  Future<void> _addToCollection(MediaCollection collection) async {
    try {
      setState(() {
        _isAdding = true;
      });

      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);
      
      final response = await mediaApiClient.bulkAddToCollection(
        collectionId: collection.id,
        mediaIds: widget.mediaIds,
      );

      if (response.success) {
        // Show success message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${widget.mediaIds.length} item${widget.mediaIds.length == 1 ? '' : 's'} added to "${collection.name}"',
            ),
            backgroundColor: AppColors.success,
            duration: const Duration(seconds: 3),
          ),
        );
        
        // Close dialog with success result
        Navigator.of(context).pop(true);
      } else {
        // Show error message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to add items to collection'),
            backgroundColor: AppColors.error,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } catch (e) {
      // Show error message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: ${e.toString()}'),
          backgroundColor: AppColors.error,
          duration: const Duration(seconds: 3),
        ),
      );
    } finally {
      setState(() {
        _isAdding = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.background,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Container(
        width: 400,
        constraints: const BoxConstraints(maxHeight: 600),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  Icons.collections,
                  color: AppColors.primary,
                  size: 24,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    widget.title,
                    style: AppTextStyles.h5.copyWith(
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  icon: const Icon(Icons.close),
                  color: AppColors.textSecondary,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // Subtitle
            Text(
              'Select a collection to add ${widget.mediaIds.length} item${widget.mediaIds.length == 1 ? '' : 's'} to:',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // Content
            Flexible(
              child: _buildContent(),
            ),

            // Actions
            const SizedBox(height: AppSpacing.lg),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _isAdding ? null : () => Navigator.of(context).pop(false),
                  child: Text(
                    'Cancel',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.xl),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: AppColors.error,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              _error!,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.error,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            ElevatedButton(
              onPressed: _loadCollections,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_collections.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.collections_outlined,
              size: 48,
              color: AppColors.textTertiary,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'No Collections Available',
              style: AppTextStyles.h6.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Create a collection first to organize your media',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textTertiary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      itemCount: _collections.length,
      itemBuilder: (context, index) {
        final collection = _collections[index];
        return _buildCollectionItem(collection);
      },
    );
  }

  Widget _buildCollectionItem(MediaCollection collection) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      color: AppColors.surface,
      child: ListTile(
        enabled: !_isAdding,
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(
            Icons.collections,
            color: AppColors.primary,
            size: 20,
          ),
        ),
        title: Text(
          collection.name,
          style: AppTextStyles.bodyLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Text(
          collection.description?.isNotEmpty == true
              ? collection.description!
              : '${collection.itemCount} items',
          style: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        trailing: _isAdding
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Icon(
                Icons.add_circle_outline,
                color: AppColors.primary,
              ),
        onTap: _isAdding ? null : () => _addToCollection(collection),
      ),
    );
  }
}

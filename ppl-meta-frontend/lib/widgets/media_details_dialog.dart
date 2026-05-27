import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/config.dart';
import '../core/theme/app_theme.dart';
import '../core/api/api_client.dart';
import '../core/models/collection_models.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';
import '../services/orchestrator_api_client.dart';
import '../services/person_objects_api_client.dart';
import '../providers/person_objects_provider.dart';
import 'video_player_widget.dart';

/// Media details dialog with comprehensive information and actions
class MediaDetailsDialog extends ConsumerStatefulWidget {
  final MediaItem item;
  final String? collectionId;

  const MediaDetailsDialog({
    super.key,
    required this.item,
    this.collectionId,
  });

  @override
  ConsumerState<MediaDetailsDialog> createState() => _MediaDetailsDialogState();
}

class _MediaDetailsDialogState extends ConsumerState<MediaDetailsDialog> {
  late MediaApiClient _mediaApiClient;
  List<MediaCollection> _collections = [];
  bool _isLoadingCollections = false;
  bool _isAddingToCollection = false;
  bool _isComputing = false;

  @override
  void initState() {
    super.initState();
    _initializeApiClient();
    _loadCollections();
  }

  void _initializeApiClient() {
    final apiClient = ref.read(apiClientProvider);
    _mediaApiClient = MediaApiClient(apiClient);
  }

  Future<void> _loadCollections() async {
    setState(() => _isLoadingCollections = true);
    
    try {
      final response = await _mediaApiClient.getCollections();
      if (response.success) {
        setState(() {
          _collections = response.data ?? [];
          _isLoadingCollections = false;
        });
      } else {
        setState(() => _isLoadingCollections = false);
        _showErrorSnackBar('Failed to load collections: ${response.error}');
      }
    } catch (e) {
      setState(() => _isLoadingCollections = false);
      _showErrorSnackBar('Error loading collections: $e');
    }
  }

  Future<void> _addToCollection(MediaCollection collection) async {
    setState(() => _isAddingToCollection = true);
    
    try {
      final response = await _mediaApiClient.addMediaToCollection(
        collectionId: collection.id,
        mediaId: widget.item.mediaId,
      );
      
      if (response.success) {
        _showSuccessSnackBar('Added to "${collection.name}" successfully!');
      } else {
        _showErrorSnackBar('Failed to add to collection: ${response.error}');
      }
    } catch (e) {
      _showErrorSnackBar('Error adding to collection: $e');
    } finally {
      setState(() => _isAddingToCollection = false);
    }
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('✅ $message'),
        backgroundColor: AppColors.success,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('❌ $message'),
        backgroundColor: AppColors.error,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.background,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        height: MediaQuery.of(context).size.height * 0.8,
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: AppColors.border,
            width: 1,
          ),
        ),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with title and close button
            _buildHeader(),
            const SizedBox(height: AppSpacing.lg),
            
            // Content area with tabs
            Expanded(
              child: DefaultTabController(
                length: 3,
                child: Column(
                  children: [
                    // Tab bar
                    TabBar(
                      labelColor: AppColors.primary,
                      unselectedLabelColor: AppColors.textSecondary,
                      indicatorColor: AppColors.primary,
                      dividerColor: AppColors.border,
                      tabs: const [
                        Tab(text: 'Details'),
                        Tab(text: 'Collections'),
                        Tab(text: 'Actions'),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    
                    // Tab content
                    Expanded(
                      child: TabBarView(
                        children: [
                          _buildDetailsTab(),
                          _buildCollectionsTab(),
                          _buildActionsTab(),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.item.originalFilename,
                style: AppTextStyles.h4.copyWith(
                  color: AppColors.textPrimary,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                '${widget.item.mediaType.name.toUpperCase()} • ${_formatFileSize(widget.item.fileSize)}',
                style: AppTextStyles.labelMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.close),
          color: AppColors.textPrimary,
        ),
      ],
    );
  }

  Widget _buildDetailsTab() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Media preview
          _buildMediaPreview(),
          const SizedBox(height: AppSpacing.lg),
          
          // File information
          _buildSection(
            title: 'File Information',
            children: [
              _DetailItem(label: 'Original Name', value: widget.item.originalFilename),
              _DetailItem(label: 'File Size', value: _formatFileSize(widget.item.fileSize)),
              _DetailItem(label: 'Media Type', value: widget.item.mediaType.name.toUpperCase()),
              _DetailItem(label: 'Upload Date', value: _formatDate(widget.item.uploadedAt)),
              if (widget.item.description != null && widget.item.description!.isNotEmpty)
                _DetailItem(label: 'Description', value: widget.item.description!),
            ],
          ),
          
          // Device information
          if (_hasDeviceInfo()) ...[
            const SizedBox(height: AppSpacing.lg),
            _buildSection(
              title: 'Device Information',
              children: _buildDeviceInfo(),
            ),
          ],
          
          // Technical metadata
          if (widget.item.technicalMetadata != null) ...[
            const SizedBox(height: AppSpacing.lg),
            _buildSection(
              title: 'Technical Details',
              children: _formatTechnicalMetadata(widget.item.technicalMetadata!),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCollectionsTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Add to Collection',
          style: AppTextStyles.h5,
        ),
        const SizedBox(height: AppSpacing.md),
        
        if (_isLoadingCollections)
          const Center(child: CircularProgressIndicator())
        else if (_collections.isEmpty)
          _buildEmptyCollectionsState()
        else
          Expanded(
            child: ListView.builder(
              itemCount: _collections.length,
              itemBuilder: (context, index) {
                final collection = _collections[index];
                return _buildCollectionItem(collection);
              },
            ),
          ),
      ],
    );
  }

  Widget _buildActionsTab() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Available Actions',
            style: AppTextStyles.h5,
          ),
          const SizedBox(height: AppSpacing.md),

          // Compute action (video only): runs the continuous pipeline
          // (face detection → person objects → MVRs) for this media.
          if (widget.item.mediaType == MediaType.video)
            ListTile(
              leading: Icon(
                Icons.bolt,
                color: _isComputing ? AppColors.textSecondary : Colors.amber,
              ),
              title: const Text('Compute'),
              subtitle: Text(
                _isComputing
                    ? 'Running pipeline...'
                    : 'Run continuous pipeline (person objects + MVRs)',
              ),
              trailing: _isComputing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : null,
              onTap: _isComputing ? null : _triggerCompute,
            ),

          // Full Screen Preview action
          ListTile(
            leading: const Icon(Icons.fullscreen, color: AppColors.primary),
            title: const Text('Full Screen Preview'),
            subtitle: const Text('View this media in full screen'),
            onTap: _openFullScreenPreview,
          ),

          // Download action
          ListTile(
            leading: const Icon(Icons.download, color: AppColors.primary),
            title: const Text('Download'),
            subtitle: const Text('Download this file to your device'),
            onTap: _downloadMedia,
          ),

          // Share action
          ListTile(
            leading: const Icon(Icons.share, color: AppColors.secondary),
            title: const Text('Share'),
            subtitle: const Text('Share this media item'),
            onTap: _shareMedia,
          ),

          // Delete action
          ListTile(
            leading: const Icon(Icons.delete, color: AppColors.error),
            title: const Text('Delete'),
            subtitle: const Text('Remove this media item'),
            onTap: _deleteMedia,
          ),
        ],
      ),
    );
  }

  Widget _buildMediaPreview() {
    // Check media type and handle accordingly
    switch (widget.item.mediaType) {
      case MediaType.video:
        // Use streaming endpoint for videos with user authentication
        final apiClient = ref.read(apiClientProvider);
        final videoUrl = '/api/v1/media/stream/${widget.item.uuid}';  // Use UUID instead of mediaId

        return Stack(
          children: [
            Container(
              width: double.infinity,
              height: MediaQuery.of(context).size.height * 0.6 * 0.8, // 60% of dialog height (which is 80% of screen)
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(AppRadius.md),
                boxShadow: [AppShadows.sm],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.md),
                child: VideoPlayerWidget(
                  videoUrl: videoUrl,
                  headers: {
                    if (apiClient.authToken != null)
                      'Authorization': 'Bearer ${apiClient.authToken}',
                  },
                  collectionId: widget.collectionId, // Pass collection ID
                  technicalMetadata: widget.item.technicalMetadata, // Pass metadata for speed correction
                  videoDuration: widget.item.duration, // Pass duration for speed correction
                ),
              ),
            ),
            // Full screen button
            Positioned(
              top: 8,
              right: 8,
              child: FloatingActionButton(
                mini: true,
                heroTag: 'preview_video',
                backgroundColor: AppColors.black.withOpacity(0.7),
                foregroundColor: AppColors.white,
                onPressed: _openFullScreenPreview,
                child: const Icon(Icons.fullscreen, size: 20),
              ),
            ),
          ],
        );

      case MediaType.image:
        // Handle image files
        final imageUrl = widget.item.thumbnailUrl ?? widget.item.url;
        if (imageUrl == null) {
          return _buildPlaceholderContainer(Icons.image_not_supported);
        }

        return Stack(
          children: [
            Container(
              width: double.infinity,
              height: MediaQuery.of(context).size.height * 0.6 * 0.8, // 60% of dialog height (which is 80% of screen)
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(AppRadius.md),
                boxShadow: [AppShadows.sm],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.md),
                child: Image.network(
                  imageUrl.startsWith('/')
                      ? '${Config.gatewayServiceUrl}$imageUrl'
                      : imageUrl,
                  fit: BoxFit.contain,
                  width: double.infinity,
                  headers: {
                    if (ref.read(apiClientProvider).authToken != null)
                      'Authorization': 'Bearer ${ref.read(apiClientProvider).authToken}',
                  },
                  errorBuilder: (context, error, stackTrace) {
                    return _buildPlaceholderContainer(Icons.broken_image);
                  },
                ),
              ),
            ),
            // Full screen button
            Positioned(
              top: 8,
              right: 8,
              child: FloatingActionButton(
                mini: true,
                heroTag: 'preview_image',
                backgroundColor: AppColors.black.withOpacity(0.7),
                foregroundColor: AppColors.white,
                onPressed: _openFullScreenPreview,
                child: const Icon(Icons.fullscreen, size: 20),
              ),
            ),
          ],
        );

      case MediaType.audio:
        // Audio files - show audio player interface
        return _buildMediaTypeContainer(
          icon: Icons.audiotrack,
          title: 'Audio File',
          subtitle: 'Click to play audio',
          onTap: () {
            // TODO: Implement audio player
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Audio player not implemented yet')),
            );
          },
        );

      case MediaType.document:
      case MediaType.pdf:
      case MediaType.text:
        // Document types - show document preview
        return _buildMediaTypeContainer(
          icon: widget.item.mediaType == MediaType.pdf 
              ? Icons.picture_as_pdf
              : widget.item.mediaType == MediaType.text
                  ? Icons.description
                  : Icons.insert_drive_file,
          title: '${widget.item.mediaType.displayName} File',
          subtitle: 'Click to view document',
          onTap: () {
            // TODO: Implement document viewer
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Document viewer not implemented yet')),
            );
          },
        );

      case MediaType.archive:
        // Archive files
        return _buildMediaTypeContainer(
          icon: Icons.archive,
          title: 'Archive File',
          subtitle: 'Compressed file archive',
          onTap: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Archive files cannot be previewed')),
            );
          },
        );

      case MediaType.other:
      default:
        // Other or unknown file types
        return _buildMediaTypeContainer(
          icon: Icons.insert_drive_file,
          title: 'Unknown File Type',
          subtitle: 'Preview not available',
          onTap: null,
        );
    }
  }

  Widget _buildPlaceholderContainer(IconData icon) {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(
        minHeight: 200,
      ),
      decoration: BoxDecoration(
        color: AppColors.gray200,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Center(
        child: Icon(icon, size: 48),
      ),
    );
  }

  Widget _buildMediaTypeContainer({
    required IconData icon,
    required String title,
    required String subtitle,
    VoidCallback? onTap,
  }) {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(
        minHeight: 200,
      ),
      decoration: BoxDecoration(
        color: AppColors.gray50,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.gray200),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadius.md),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.xl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: 64,
                  color: AppColors.primary,
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  title,
                  style: AppTextStyles.h5,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  subtitle,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required List<Widget> children,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: AppTextStyles.h6.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        ...children,
      ],
    );
  }

  Widget _buildEmptyCollectionsState() {
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

  Widget _buildCollectionItem(MediaCollection collection) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: ListTile(
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
        title: Text(collection.name),
        subtitle: Text(
          collection.description?.isNotEmpty == true
              ? collection.description!
              : '${collection.itemCount} items',
        ),
        trailing: _isAddingToCollection
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.add),
        onTap: _isAddingToCollection ? null : () => _addToCollection(collection),
      ),
    );
  }

  bool _hasDeviceInfo() {
    return widget.item.deviceName != null ||
           widget.item.deviceManufacturer != null ||
           widget.item.deviceModel != null ||
           widget.item.deviceOs != null;
  }

  List<Widget> _buildDeviceInfo() {
    List<Widget> widgets = [];
    
    if (widget.item.deviceName != null && widget.item.deviceName!.isNotEmpty) {
      widgets.add(_DetailItem(label: 'Device Name', value: widget.item.deviceName!));
    }
    if (widget.item.deviceManufacturer != null && widget.item.deviceManufacturer!.isNotEmpty) {
      widgets.add(_DetailItem(label: 'Manufacturer', value: widget.item.deviceManufacturer!));
    }
    if (widget.item.deviceModel != null && widget.item.deviceModel!.isNotEmpty) {
      widgets.add(_DetailItem(label: 'Model', value: widget.item.deviceModel!));
    }
    if (widget.item.deviceOs != null && widget.item.deviceOs!.isNotEmpty) {
      widgets.add(_DetailItem(label: 'Operating System', value: widget.item.deviceOs!));
    }
    if (widget.item.appName != null && widget.item.appName!.isNotEmpty) {
      widgets.add(_DetailItem(label: 'App Name', value: widget.item.appName!));
    }
    if (widget.item.appVersion != null && widget.item.appVersion!.isNotEmpty) {
      widgets.add(_DetailItem(label: 'App Version', value: widget.item.appVersion!));
    }
    
    return widgets;
  }

  List<Widget> _formatTechnicalMetadata(Map<String, dynamic> metadata) {
    List<Widget> widgets = [];
    
    metadata.forEach((key, value) {
      if (key == 'technical_metadata' && value is Map<String, dynamic>) {
        // Handle technical_metadata object
        final techData = value;
        
        // Handle thumbnails
        if (techData['thumbnails'] is Map<String, dynamic>) {
          final thumbnails = techData['thumbnails'] as Map<String, dynamic>;
          final List<String> thumbStatus = [];
          
          thumbnails.forEach((size, data) {
            if (data is Map<String, dynamic>) {
              final success = data['success'] ?? false;
              final bytes = data['size_bytes'] ?? 0;
              if (success && bytes > 0) {
                thumbStatus.add('$size (${(bytes / 1024).toStringAsFixed(1)} KB)');
              } else {
                thumbStatus.add('$size (failed)');
              }
            }
          });
          
          if (thumbStatus.isNotEmpty) {
            widgets.add(_DetailItem(
              label: 'Thumbnails',
              value: thumbStatus.join(', '),
            ));
          }
        }
        
        // Handle EXIF summary
        if (techData['exif_summary'] is Map<String, dynamic>) {
          final exifSummary = techData['exif_summary'] as Map<String, dynamic>;
          final hasCameraInfo = exifSummary['has_camera_info'] ?? false;
          final hasGpsData = exifSummary['has_gps_data'] ?? false;
          final hasDatetime = exifSummary['has_datetime'] ?? false;
          final totalTags = exifSummary['total_tags'] ?? 0;
          
          if (totalTags > 0) {
            final List<String> exifFeatures = [];
            if (hasCameraInfo) exifFeatures.add('Camera Info');
            if (hasGpsData) exifFeatures.add('GPS Data');
            if (hasDatetime) exifFeatures.add('Date/Time');
            
            widgets.add(_DetailItem(
              label: 'EXIF Data',
              value: exifFeatures.isNotEmpty 
                  ? '${exifFeatures.join(', ')} ($totalTags tags)'
                  : '$totalTags metadata tags',
            ));
          } else {
            widgets.add(_DetailItem(
              label: 'EXIF Data',
              value: 'No EXIF data available',
            ));
          }
        }
        
        // Handle other technical metadata
        techData.forEach((techKey, techValue) {
          if (techKey != 'thumbnails' && techKey != 'exif_summary' && techKey != 'exif') {
            widgets.add(_DetailItem(
              label: _formatMetadataKey(techKey),
              value: _formatMetadataValue(techValue),
            ));
          }
        });
      } else {
        // Handle other metadata entries
        widgets.add(_DetailItem(
          label: _formatMetadataKey(key),
          value: _formatMetadataValue(value),
        ));
      }
    });
    
    return widgets;
  }

  String _formatMetadataKey(String key) {
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
  
  String _formatMetadataValue(dynamic value) {
    if (value == null) return 'Not available';
    if (value is bool) return value ? 'Yes' : 'No';
    if (value is num) return value.toString();
    if (value is String) return value;
    if (value is List) return value.join(', ');
    if (value is Map) return 'Complex data (${value.length} fields)';
    return value.toString();
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '${bytes} B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year} at ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }

  void _openFullScreenPreview() {
    // Close the dialog first
    Navigator.of(context).pop();
    
    // Navigate to the full screen preview with collection context
    if (widget.collectionId != null) {
      context.go('/media-preview?collectionId=${widget.collectionId}', extra: widget.item);
    } else {
      context.go('/media-preview', extra: widget.item);
    }
  }

  Future<void> _downloadMedia() async {
    try {
      final response = await _mediaApiClient.downloadMedia(
        widget.item.mediaId,
        widget.item.originalFilename,
      );
      
      if (response.success) {
        _showSuccessSnackBar('Download started successfully!');
      } else {
        _showErrorSnackBar('Download failed: ${response.error}');
      }
    } catch (e) {
      _showErrorSnackBar('Download error: $e');
    }
  }

  void _shareMedia() {
    // TODO: Implement sharing functionality
    _showErrorSnackBar('Sharing functionality not yet implemented');
  }

  /// Run the continuous pipeline (face detection → person objects → MVRs)
  /// for this media item.
  ///
  /// Behavior:
  /// - No person objects + no MVRs → run the full pipeline silently.
  /// - Person objects exist but no MVRs → run the pipeline (will refresh
  ///   person objects and create MVRs).
  /// - Both exist → ask the user to confirm a recompute, then run the
  ///   pipeline (will update both person objects and MVRs).
  Future<void> _triggerCompute() async {
    if (_isComputing) return;
    setState(() => _isComputing = true);

    try {
      final mediaUuid = widget.item.uuid;
      final orchestratorApiClient = ref.read(orchestratorApiClientProvider);
      final personObjectsApiClient = ref.read(personObjectsApiClientProvider);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Compute: checking pipeline state...'),
          backgroundColor: Colors.amber,
          duration: Duration(seconds: 2),
        ),
      );

      // 1. Check current pipeline state.
      final hasPersonObjects =
          await personObjectsApiClient.hasPersonObjectsForMedia(mediaUuid);
      final mvrResponse = await _mediaApiClient
          .getMVRPeopleCountByVideos(videoUuids: [mediaUuid]);

      int mvrCount = 0;
      if (mvrResponse.success) {
        mvrCount = (mvrResponse.data?['count'] as num?)?.toInt() ?? 0;
      }
      final bool hasMvrs = mvrCount > 0;

      if (!mounted) return;

      String runMessage;
      if (!hasPersonObjects && !hasMvrs) {
        runMessage = 'Compute: nothing computed yet — running full pipeline';
      } else if (hasPersonObjects && !hasMvrs) {
        runMessage =
            'Compute: person objects exist — running pipeline to create MVRs';
      } else if (!hasPersonObjects && hasMvrs) {
        runMessage =
            'Compute: MVRs without person objects — re-running pipeline';
      } else {
        // Both exist → ask the user to confirm a recompute.
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (BuildContext ctx) {
            return AlertDialog(
              title: const Text('Recompute video?'),
              content: Text(
                'This video already has $mvrCount MVR person'
                '${mvrCount == 1 ? '' : 's'} and persisted person objects.\n\n'
                'Recomputing will refresh person objects and update the '
                'existing MVRs. Continue?',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(ctx).pop(true),
                  child: const Text('Recompute'),
                ),
              ],
            );
          },
        );

        if (confirmed != true || !mounted) {
          return;
        }
        runMessage =
            'Compute: recomputing video — updating person objects and MVRs';
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(runMessage),
          backgroundColor: Colors.amber,
          duration: const Duration(seconds: 3),
        ),
      );

      // 2. Run the continuous pipeline.
      // Enhanced Logic V2 always re-runs the person-objects workflow and
      // re-materializes MVRs, regardless of whether stored faces already
      // exist.
      final response =
          await orchestratorApiClient.getEnhancedLogicV2Response(mediaUuid);

      if (!mounted) return;

      if (response.isSuccess) {
        final facesProcessed = response.data?.totalFaces ?? 0;
        int mvrPeopleCreated = 0;

        // Verify MVRs were created. If the orchestrator's STEP 1.7 was
        // skipped (e.g. because the person-objects workflow returned an
        // empty list when objects already exist), explicitly materialize
        // MVRs from the persisted person objects.
        final postMvrResponse = await _mediaApiClient
            .getMVRPeopleCountByVideos(videoUuids: [mediaUuid]);
        int postMvrCount = 0;
        if (postMvrResponse.success) {
          postMvrCount =
              (postMvrResponse.data?['count'] as num?)?.toInt() ?? 0;
        }

        final personObjectsData =
          await personObjectsApiClient.getPersonObjectsForMedia(mediaUuid);
        final persisted =
          personObjectsData?.rawPersonGroups ?? const <Map<String, dynamic>>[];
        final persistedPersonCount = persisted.length;
        final requiresRematerialization =
          persistedPersonCount > 0 && postMvrCount != persistedPersonCount;

        if (requiresRematerialization) {
          if (persisted.isNotEmpty) {
            debugPrint(
              '🔁 Compute: MVRs missing after pipeline — explicitly '
              'materializing ${persisted.length} persisted person objects',
            );
            final materializeResponse =
                await _mediaApiClient.materializePersistedPersonObjects(
              mediaUuid: mediaUuid,
              personObjects: persisted,
              sessionUuid: response.data?.sessionUuid,
              mediaType: 'video',
              awaitAuthoritativeRefresh: true,
            );
            if (!materializeResponse.success) {
              _showErrorSnackBar(
                'Compute: pipeline OK but MVR materialization failed: '
                '${materializeResponse.error ?? 'unknown error'}',
              );
              return;
            }

            mvrPeopleCreated =
                (materializeResponse.data?['mvr_people_count'] as num?)
                        ?.toInt() ??
                    0;
            // If the backend reports it skipped because existing MVRs were
            // already linked to this video, do not advertise those as
            // "created" by this run.
            final materializeStatus =
                materializeResponse.data?['status'] as String?;
            if (materializeStatus == 'skipped_existing') {
              mvrPeopleCreated = 0;
            }
            debugPrint(
              '🧱 Compute: materialize response mvr_people_count='
              '$mvrPeopleCreated status=$materializeStatus',
            );

            // Re-confirm via count endpoint (helps catch race conditions
            // where the response is returned before commit visibility).
            final reCountResponse = await _mediaApiClient
                .getMVRPeopleCountByVideos(videoUuids: [mediaUuid]);
            if (reCountResponse.success) {
              postMvrCount =
                  (reCountResponse.data?['count'] as num?)?.toInt() ?? 0;
              debugPrint(
                '🧱 Compute: post-materialize count=$postMvrCount',
              );
            }
          }
        } else {
          mvrPeopleCreated = postMvrCount;
        }

        if (postMvrCount > 0 || mvrPeopleCreated > 0) {
          _showSuccessSnackBar(
            'Compute complete: $postMvrCount MVR person'
            '${postMvrCount == 1 ? '' : 's'} linked to this video '
            '($facesProcessed face${facesProcessed == 1 ? '' : 's'} processed)',
          );
        } else {
          _showErrorSnackBar(
            'Compute: pipeline ran ($facesProcessed face'
            '${facesProcessed == 1 ? '' : 's'}) but no MVR people were '
            'created. Check vmeta logs for materialization errors.',
          );
        }
      } else {
        _showErrorSnackBar(
          'Compute failed: ${response.error?.message ?? 'unknown error'}',
        );
      }
    } catch (e) {
      if (mounted) {
        _showErrorSnackBar('Compute failed: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isComputing = false);
      }
    }
  }

  Future<void> _deleteMedia() async {
    final confirmed = await _showDeleteConfirmation();
    if (!confirmed) return;
    
    try {
      final response = await _mediaApiClient.deleteMedia(widget.item.mediaId);
      
      if (response.success) {
        _showSuccessSnackBar('Media deleted successfully!');
        Navigator.of(context).pop('deleted'); // Signal deletion to caller
      } else {
        _showErrorSnackBar('Delete failed: ${response.error}');
      }
    } catch (e) {
      _showErrorSnackBar('Delete error: $e');
    }
  }

  Future<bool> _showDeleteConfirmation() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Media'),
        content: Text('Are you sure you want to delete "${widget.item.originalFilename}"? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    
    return result ?? false;
  }
}

/// Detail item widget for displaying metadata
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
            width: 120,
            child: Text(
              label,
              style: AppTextStyles.labelMedium.copyWith(
                color: AppColors.textSecondary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

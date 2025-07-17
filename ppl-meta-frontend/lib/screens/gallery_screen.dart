import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../core/api/api_client.dart';
import '../models/media_models.dart';
import '../widgets/responsive_media_gallery.dart';
import '../widgets/advanced_search_interface.dart';
import '../widgets/share_dialog.dart';

/// Gallery screen with search and responsive media display
class GalleryScreen extends ConsumerStatefulWidget {
  const GalleryScreen({super.key});

  @override
  ConsumerState<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends ConsumerState<GalleryScreen> {
  MediaSearchFilters _currentFilters = MediaSearchFilters();
  List<MediaItem> _selectedItems = [];
  bool _isSelectionMode = false;
  bool _showSearch = false;

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final apiClient = ref.watch(apiClientProvider);
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
              apiClient: apiClient,
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
class _MediaDetailsDialog extends ConsumerWidget {
  final MediaItem item;

  const _MediaDetailsDialog({required this.item});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final apiClient = ref.watch(apiClientProvider);
    
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Container(
        width: 600, // Increased width to give more space
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.9, // Increased to 90% of screen height
          minHeight: 500, // Increased minimum height
        ),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min, // Allow column to size itself
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
                          item.originalFilename,
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
              
              // DEBUG: Quick check - COMMENTED OUT FOR PRODUCTION
              // Container(
              //   color: Colors.blue.withOpacity(0.2),
              //   padding: const EdgeInsets.all(8),
              //   child: Column(
              //     crossAxisAlignment: CrossAxisAlignment.start,
              //     children: [
              //       Text('DEBUG: mediaType=${item.mediaType}'),
              //       Text('DEBUG: mediaType.toString()=${item.mediaType.toString()}'),
              //       Text('DEBUG: url=${item.url}'),
              //       Text('DEBUG: thumbnailUrl=${item.thumbnailUrl}'),
              //       Text('DEBUG: deviceName=${item.deviceName}'),
              //       Text('DEBUG: Should show image: ${item.mediaType == MediaType.image}'),
              //       Text('DEBUG: MediaType.image = ${MediaType.image}'),
              //       Text('DEBUG: Final image URL: ${_getAbsoluteUrl(item.url ?? item.thumbnailUrl ?? '')}'),
              //     ],
              //   ),
              // ),
              
              // Preview (if available) - Responsive layout
              if (item.mediaType == MediaType.image || item.mediaType.toString().contains('image') || item.mediaType.toString().contains('picture'))
                Container(
                  width: double.infinity,
                  // Removed maxHeight constraint to make image fully responsive to container width
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    child: Image.network(
                      // Use original image URL if thumbnail fails, fallback to thumbnail URL
                      _getAbsoluteUrl(item.url ?? item.thumbnailUrl ?? ''),
                      width: double.infinity,
                      fit: BoxFit.contain, // Contain to maintain aspect ratio and responsiveness
                      headers: apiClient.authToken != null 
                          ? {'Authorization': 'Bearer ${apiClient.authToken}'}
                          : null,
                      errorBuilder: (context, error, stackTrace) {
                        // DEBUG: Print statements commented out for production
                        // print('IMAGE LOAD ERROR: $error');
                        // print('IMAGE URL: ${_getAbsoluteUrl(item.url ?? item.thumbnailUrl ?? '')}');
                        // print('AUTH TOKEN: ${apiClient.authToken != null ? 'Present' : 'Missing'}');
                        return Container(
                          height: 200,
                          color: AppColors.gray200,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                _getMediaTypeIcon(item.mediaType),
                                size: 64,
                                color: _getMediaTypeColor(item.mediaType),
                              ),
                              SizedBox(height: 8),
                              Text(
                                'Image unavailable',
                                style: AppTextStyles.bodySmall.copyWith(
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Error: ${error.toString().substring(0, 50)}...',
                                style: AppTextStyles.caption.copyWith(
                                  color: AppColors.textSecondary,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Details Section
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Details',
                      style: AppTextStyles.labelLarge,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _DetailItem(
                      label: 'Original Filename',
                      value: item.originalFilename,
                    ),
                    _DetailItem(
                      label: 'File Size',
                      value: '${(item.fileSize / 1024 / 1024).toStringAsFixed(1)} MB',
                    ),
                    _DetailItem(
                      label: 'Upload Date',
                      value: _formatDate(item.createdAt),
                    ),
                    _DetailItem(
                      label: 'Media Type',
                      value: item.mediaType.displayName,
                    ),
                    if (item.duration != null)
                      _DetailItem(
                        label: 'Duration',
                        value: _formatDuration(item.duration!),
                      ),
                    if (item.deviceName != null && item.deviceName!.isNotEmpty && item.deviceName != 'null')
                      _DetailItem(
                        label: 'Device Name',
                        value: item.deviceName!,
                      ),
                    if (item.deviceManufacturer != null && item.deviceManufacturer!.isNotEmpty && item.deviceManufacturer != 'null')
                      _DetailItem(
                        label: 'Device Manufacturer',
                        value: item.deviceManufacturer!,
                      ),
                    if (item.deviceModel != null && item.deviceModel!.isNotEmpty && item.deviceModel != 'null')
                      _DetailItem(
                        label: 'Device Model',
                        value: item.deviceModel!,
                      ),
                    if (item.deviceOs != null && item.deviceOs!.isNotEmpty && item.deviceOs != 'null')
                      _DetailItem(
                        label: 'Device OS',
                        value: item.deviceOs!,
                      ),
                    if (item.appName != null && item.appName!.isNotEmpty && item.appName != 'null')
                      _DetailItem(
                        label: 'App Name',
                        value: item.appName!,
                      ),
                    if (item.appVersion != null && item.appVersion!.isNotEmpty && item.appVersion != 'null')
                      _DetailItem(
                        label: 'App Version',
                        value: item.appVersion!,
                      ),
                    if (item.description != null && item.description!.isNotEmpty && item.description != 'null')
                      _DetailItem(
                        label: 'Description',
                        value: item.description!,
                      ),
                    if (item.tags.isNotEmpty)
                      _DetailItem(
                        label: 'Tags',
                        value: item.tags.join(', '),
                      ),
                    if (item.metadata?.isNotEmpty == true) ...[
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Technical Metadata',
                        style: AppTextStyles.labelLarge,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      ..._formatTechnicalMetadata(item.metadata!),
                    ],
                    // New: Technical metadata formatting
                    if (item.metadata?.isNotEmpty == true) ..._formatTechnicalMetadata(item.metadata!),
                  ],
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
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
            ], // Fixed: Added missing closing bracket for the main children list
          ),
        ),
      ),
    );
  }

  /// Convert relative URL to absolute URL
  String _getAbsoluteUrl(String relativeUrl) {
    if (relativeUrl.startsWith('http')) {
      return relativeUrl; // Already absolute
    }
    return 'http://localhost:8080$relativeUrl'; // Use Gateway service directly
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

  /// Format technical metadata for user-friendly display
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
  
  /// Format metadata key for display
  String _formatMetadataKey(String key) {
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
  
  /// Format metadata value for display
  String _formatMetadataValue(dynamic value) {
    if (value == null) return 'Not available';
    if (value is bool) return value ? 'Yes' : 'No';
    if (value is num) return value.toString();
    if (value is String) return value;
    if (value is List) return value.join(', ');
    if (value is Map) return 'Complex data (${value.length} fields)';
    return value.toString();
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

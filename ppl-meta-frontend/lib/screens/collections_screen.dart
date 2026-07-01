import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/config.dart';
import '../core/theme/app_theme.dart';
import '../core/api/api_client.dart';
import '../models/media_models.dart';
import '../models/cross_video_analysis_models.dart';
import '../core/models/collection_models.dart';
import '../widgets/collection_management.dart';
import '../widgets/responsive_media_gallery.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/collection_organization_widget.dart';
import '../widgets/collection_picker_dialog.dart';
import '../widgets/media_details_dialog.dart';
import '../widgets/collections_search_dialog.dart';
import '../widgets/vision_processing_dialog.dart';
import '../widgets/vision_results_dialog.dart';
import '../services/media_organization_service.dart';
import '../services/media_api_client.dart';
import '../services/vision_processing_service.dart';
import '../providers/media_organization_providers.dart';
import '../providers/settings_providers.dart';
import '../presentation/widgets/settings/workflow_settings_section.dart'
  as workflow_section;
import 'person_objects_detail_screen.dart';
import '../core/providers/features_providers.dart';
import '../widgets/media_privacy_placeholder.dart';

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
  
  // Date/time filtering state
  DateTime? _startDate;
  DateTime? _endDate;
  
  // Cross-video tracking state
  int? _individualsCount;  // Original count (before MVR merging)
  int? _uniqueMvrCount;    // Unique count (after MVR merging)
  bool _uniqueCountIsFallback = false;  // True if unique count is using fallback
  bool _isLoadingIndividuals = false;
  String? _trackingSessionUuid;
  Map<String, dynamic>? _trackingSessionData;

  List<String> _resolveCollectionCameraUuids(MediaCollection? collection) {
    if (collection == null) {
      return const [];
    }

    final metadataCameraIds = collection.metadata?['camera_ids'];
    if (metadataCameraIds is List) {
      final uuids = metadataCameraIds
          .whereType<Object>()
          .map((value) => value.toString())
          .where((value) => value.isNotEmpty)
          .toSet()
          .toList();
      if (uuids.isNotEmpty) {
        return uuids;
      }
    }

    final collectionUuid = collection.uuid;
    if (collectionUuid != null && collectionUuid.isNotEmpty) {
      return [collectionUuid];
    }

    return const [];
  }

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
    // Create MediaSearchFilters with date/time range if set
    MediaSearchFilters? filters;
    if (_startDate != null || _endDate != null) {
      filters = MediaSearchFilters(
        startDate: _startDate,
        endDate: _endDate,
        sortBy: 'created_at',
        sortOrder: 'desc',
      );
    }
    
    if (_mediaGallery == null || 
        _mediaGallery!.collectionId != _selectedCollection!.id ||
        _mediaGallery!.enableSelection != _isSelectionMode ||
        _mediaGallery!.filters != filters) {
      _mediaGallery = ResponsiveMediaGallery(
        key: ValueKey('${_selectedCollection!.id}_${_startDate}_${_endDate}'), // Include dates in key
        collectionId: _selectedCollection!.id,
        filters: filters,
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
    final canViewMedia = ref.watch(mediaViewingEnabledProvider);
    if (!canViewMedia) {
      return Scaffold(
        appBar: const CustomAppBar(title: 'Collections'),
        body: const MediaPrivacyPlaceholder(),
      );
    }
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
                    
                    // Vision button (NEW)
                    IconButton(
                      onPressed: _processWithVision,
                      icon: Icon(
                        Icons.visibility,
                        color: AppColors.primary,
                      ),
                      tooltip: 'Process with Vision AI',
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
                  // Search button
                  IconButton(
                    onPressed: _showSearchDialog,
                    icon: Icon(
                      _startDate != null || _endDate != null 
                          ? Icons.filter_alt 
                          : Icons.search,
                    ),
                    tooltip: 'Search by date/time',
                  ),
                  
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
        
        // Date/Time filter information bar (if filters are active)
        if (_startDate != null || _endDate != null)
          _buildFilterInfoBar(),
        
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

  /// Build filter information bar
  Widget _buildFilterInfoBar() {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.05),
        border: const Border(
          bottom: BorderSide(color: AppColors.border),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isNarrow = constraints.maxWidth < 600;
          final isMedium = constraints.maxWidth >= 600 && constraints.maxWidth < 900;
          
          if (isNarrow) {
            // Mobile layout: Stack vertically
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.filter_alt,
                      color: AppColors.primary,
                      size: 20,
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Wrap(
                        spacing: AppSpacing.sm,
                        runSpacing: AppSpacing.xs,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          if (_startDate != null) _buildDateTimeChip('From', _startDate!),
                          if (_endDate != null) _buildDateTimeChip('To', _endDate!),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: _clearFilters,
                      icon: const Icon(Icons.clear, size: 20),
                      tooltip: 'Clear filters',
                      color: AppColors.textSecondary,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                Row(
                  children: [
                    Text(
                      'Individuals: ',
                      style: AppTextStyles.bodySmall.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    if (_isLoadingIndividuals)
                      const SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    else
                      Builder(
                        builder: (context) {
                          // DEBUG: Print current counter values when UI renders
                          print('RENDERING COUNTER UI:');
                          print('   _individualsCount = $_individualsCount');
                          print('   _uniqueMvrCount = $_uniqueMvrCount');
                          print('   _uniqueCountIsFallback = $_uniqueCountIsFallback');
                          print('   Display will be: $_individualsCount → ${_uniqueCountIsFallback ? "[]" : "$_uniqueMvrCount unique"}');
                          
                          return Row(
                            children: [
                              Text(
                                '${_individualsCount ?? 0}',
                                style: AppTextStyles.bodySmall.copyWith(
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                ' → ',
                                style: AppTextStyles.bodySmall.copyWith(
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              Text(
                                _uniqueCountIsFallback 
                                  ? '[]' 
                                  : '${_uniqueMvrCount ?? 0} unique',
                                style: AppTextStyles.bodySmall.copyWith(
                                  color: _uniqueCountIsFallback 
                                    ? AppColors.error 
                                    : AppColors.success,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          );
                        },
                      ),
                    const SizedBox(width: AppSpacing.xs),
                    TextButton.icon(
                      onPressed: _showIndividualsDetails,
                      icon: const Icon(Icons.info_outline, size: 14),
                      label: const Text('Details', style: TextStyle(fontSize: 12)),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm,
                          vertical: AppSpacing.xs,
                        ),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ),
                  ],
                ),
              ],
            );
          } else if (isMedium) {
            // Tablet layout: Wrap if needed
            return Row(
              children: [
                const Icon(
                  Icons.filter_alt,
                  color: AppColors.primary,
                  size: 20,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      if (_startDate != null) _buildDateTimeChip('From', _startDate!),
                      if (_endDate != null) _buildDateTimeChip('To', _endDate!),
                      if (_startDate != null || _endDate != null) ...[
                        Text(
                          'Individuals: ',
                          style: AppTextStyles.bodyMedium.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        if (_isLoadingIndividuals)
                          const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        else
                          Text(
                            _uniqueCountIsFallback
                              ? '${_individualsCount ?? 0} → []'
                              : '${_individualsCount ?? 0} → ${_uniqueMvrCount ?? 0} unique',
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: _uniqueCountIsFallback ? AppColors.error : AppColors.primary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        TextButton.icon(
                          onPressed: _showIndividualsDetails,
                          icon: const Icon(Icons.info_outline, size: 16),
                          label: const Text('Details'),
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.sm,
                              vertical: AppSpacing.xs,
                            ),
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                IconButton(
                  onPressed: _clearFilters,
                  icon: const Icon(Icons.clear, size: 20),
                  tooltip: 'Clear filters',
                  color: AppColors.textSecondary,
                ),
              ],
            );
          } else {
            // Desktop layout: Single row
            return Row(
              children: [
                const Icon(
                  Icons.filter_alt,
                  color: AppColors.primary,
                  size: 20,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Row(
                    children: [
                      if (_startDate != null) ...[
                        Text(
                          'From: ',
                          style: AppTextStyles.bodyMedium.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        Text(
                          _formatDateTime(_startDate!),
                          style: AppTextStyles.bodyMedium.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                      if (_startDate != null && _endDate != null)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                          child: Text(
                            '•',
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                      if (_endDate != null) ...[
                        Text(
                          'To: ',
                          style: AppTextStyles.bodyMedium.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        Text(
                          _formatDateTime(_endDate!),
                          style: AppTextStyles.bodyMedium.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                      // Individuals filter section
                      if (_startDate != null || _endDate != null) ...[
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                          child: Text(
                            '•',
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                        Text(
                          'Individuals: ',
                          style: AppTextStyles.bodyMedium.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        if (_isLoadingIndividuals)
                          const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        else
                          Text(
                            _uniqueCountIsFallback
                              ? '${_individualsCount ?? 0} → []'
                              : '${_individualsCount ?? 0} → ${_uniqueMvrCount ?? 0} unique',
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: _uniqueCountIsFallback ? AppColors.error : AppColors.primary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        const SizedBox(width: AppSpacing.sm),
                        TextButton.icon(
                          onPressed: _showIndividualsDetails,
                          icon: const Icon(Icons.info_outline, size: 16),
                          label: const Text('Details'),
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.sm,
                              vertical: AppSpacing.xs,
                            ),
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                // Clear filters button
                IconButton(
                  onPressed: _clearFilters,
                  icon: const Icon(Icons.clear, size: 20),
                  tooltip: 'Clear filters',
                  color: AppColors.textSecondary,
                ),
              ],
            );
          }
        },
      ),
    );
  }

  /// Build date/time chip for compact display
  Widget _buildDateTimeChip(String label, DateTime dateTime) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(
          color: AppColors.primary.withOpacity(0.2),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: AppTextStyles.bodySmall.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
            ),
          ),
          Text(
            _formatDateTime(dateTime),
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// Clear all filters
  void _clearFilters() {
    setState(() {
      _startDate = null;
      _endDate = null;
      _mediaGallery = null; // Force rebuild
    });
  }

  /// Format date/time for display
  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.month}/${dateTime.day}/${dateTime.year} '
           '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  /// Show individuals filter details dialog
  /// 
  /// MODIFIED v2.19.84: Now displays hierarchical merge statistics when available.
  /// Shows original MVR count, post-merge super-individuals, and merge efficiency.
  Future<void> _showIndividualsDetails() async {
    final bool showingExistingMvrSearchResults =
        _trackingSessionData != null &&
        _trackingSessionData!['search_results'] != null &&
        _trackingSessionData!['hierarchical_merge_applied'] != true;

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cross-Video Tracking Details'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Session Information:',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
            const SizedBox(height: 12),
            if (_trackingSessionUuid != null)
              Text('Session: ${_trackingSessionUuid!.substring(0, 8)}...'),
            
            // NEW: Display hierarchical merge statistics if available
            if (_trackingSessionData != null && 
                _trackingSessionData!['hierarchical_merge_applied'] == true) ...[
              const SizedBox(height: 8),
              const Text(
                'Hierarchical Merge Applied:',
                style: TextStyle(fontWeight: FontWeight.w600, color: Colors.green),
              ),
              const SizedBox(height: 4),
              Text('• Original MVR people: ${_trackingSessionData!['pre_merge_count'] ?? 'N/A'}'),
              Text('• Unique individuals: ${_trackingSessionData!['post_merge_count'] ?? 'N/A'}',
                style: const TextStyle(fontWeight: FontWeight.bold)),
              if (_trackingSessionData!['merge_statistics'] != null) ...[
                () {
                  final stats = _trackingSessionData!['merge_statistics'] as Map<String, dynamic>;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('  • Merges performed: ${stats['merges_performed']}'),
                      Text('  • Standalone individuals: ${stats['standalone_individuals']}'),
                      if (stats['merges_performed'] > 0)
                        Text(
                          '  • ${((stats['merges_performed'] / stats['total_mvr']) * 100).toStringAsFixed(1)}% reduction',
                          style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: Colors.green),
                        ),
                    ],
                  );
                }(),
              ],
            ]
            // LEGACY: Display traditional MVR count (fallback)
            else if (_individualsCount != null || _uniqueMvrCount != null) ...[
              Text('• Original detections: ${_individualsCount ?? 0} individual${(_individualsCount ?? 0) == 1 ? '' : 's'}'),
              Text(
                showingExistingMvrSearchResults
                    ? '• Existing MVR identities found: ${_uniqueMvrCount ?? _individualsCount ?? 0}'
                    : '• Unique individuals (after MVR merging): ${_uniqueMvrCount ?? _individualsCount ?? 0}',
                style: const TextStyle(fontWeight: FontWeight.bold)),
              if (!showingExistingMvrSearchResults &&
                  _individualsCount != null &&
                  _uniqueMvrCount != null &&
                  _individualsCount! > _uniqueMvrCount!)
                Text('  (${_individualsCount! - _uniqueMvrCount!} duplicates merged)', 
                  style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
              if (showingExistingMvrSearchResults)
                const Text(
                  '  (These are existing persisted MVR identities, not a new merge from this search.)',
                  style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                ),
            ] else
              const Text('• Loading individual count...'),
            
            const SizedBox(height: 8),
            Text('• Time range: ${_formatDateTime(_startDate!)} to ${_formatDateTime(_endDate!)}'),
            const SizedBox(height: 8),
            Text('• Collection: ${_selectedCollection!.name}'),
            if (_trackingSessionData != null) ...[
              const SizedBox(height: 8),
              Text('• Total videos: ${_trackingSessionData!['total_videos'] ?? 'N/A'}'),
              Text('• Status: ${_trackingSessionData!['status'] ?? 'Unknown'}'),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
          if (_individualsCount != null && _individualsCount! > 0 && _trackingSessionUuid != null)
            ElevatedButton.icon(
              onPressed: () {
                Navigator.of(context).pop(); // Close dialog first
                _navigateToIndividualAnalysis();
              },
              icon: const Icon(Icons.analytics),
              label: const Text('Analysis'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
              ),
            ),
        ],
      ),
    );
  }

  /// Navigate to individual analysis screen
  /// 
  /// MODIFIED v2.19.84: Now performs hierarchical MVR merging before navigation.
  /// Automatically consolidates duplicate MVR people across batches using
  /// similarity-based merging for a cleaner, deduplicated view.
  Future<void> _navigateToIndividualAnalysis() async {
    if (_trackingSessionData == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No MVR search data available')),
      );
      return;
    }

    try {
      final sessionData = _trackingSessionData!;
      final hasRawTrackingSession =
          sessionData['search_results'] == null &&
          _trackingSessionUuid != null &&
          !_trackingSessionUuid!.startsWith('mvr_search_');

      if (hasRawTrackingSession) {
        final rawSessionData = Map<String, dynamic>.from(sessionData);
        rawSessionData['hierarchical_merge_applied'] = false;
        rawSessionData['merge_rule_applied'] = 'backend-owned';
        rawSessionData['backend_owned_session_analysis'] = true;
        _navigateToCrossVideoAnalysis(
          individualUuids: const [],
          sessionUuid: _trackingSessionUuid!,
          sessionData: rawSessionData,
        );
        return;
      }

        if (sessionData['search_results'] != null) {
        final searchParams =
            sessionData['search_parameters'] as Map<String, dynamic>? ?? const {};
        final rawVideoUuids = searchParams['video_uuids'] as List<dynamic>? ?? const [];
        final videoUuids = rawVideoUuids.map((value) => value.toString()).toList();
        final sessionCameraUuids =
            (searchParams['camera_uuids'] as List<dynamic>? ?? const [])
                .map((value) => value.toString())
                .where((value) => value.isNotEmpty)
                .toList();
        final collectionCameraUuids = _resolveCollectionCameraUuids(
          _selectedCollection,
        );
        final cameraUuids = sessionCameraUuids.isNotEmpty
            ? sessionCameraUuids
            : collectionCameraUuids;

        if (cameraUuids.isNotEmpty &&
            videoUuids.isNotEmpty) {
          final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
          final mergeThreshold =
              generalSettings?.mergeIndividualsThreshold ?? 0.70;
          final apiClient = ref.read(apiClientProvider);
          final mediaApiClient = MediaApiClient(apiClient);
          final startTime = searchParams['start_time'] != null
              ? DateTime.tryParse(searchParams['start_time'].toString())
              : _startDate;
          final endTime = searchParams['end_time'] != null
              ? DateTime.tryParse(searchParams['end_time'].toString())
              : _endDate;

          final mergeResponse =
              await mediaApiClient.searchPersistedMergedMVRPeopleByVideos(
            cameraUuids: cameraUuids,
            videoUuids: videoUuids,
            startTime: startTime,
            endTime: endTime,
            limit: 500,
            similarityThreshold: mergeThreshold,
            ignoreExistingSession: false,
          );

          if (mergeResponse.success && mergeResponse.data != null) {
            final mergeSessionUuid =
                mergeResponse.data!['search_session_uuid'] as String?;
            final payload = mergeResponse.data!['result_payload']
                    as Map<String, dynamic>? ??
                const {};
            final mergedResults =
                payload['mvr_people'] as List<dynamic>? ?? const [];
            final mergedUuids = mergedResults
                .map((mvr) => (mvr as Map<String, dynamic>)['mvr_people_uuid'])
                .whereType<Object>()
                .map((uuid) => uuid.toString())
                .toList();

            if (mergeSessionUuid != null && mergedUuids.isNotEmpty) {
              final rawResults =
                  sessionData['search_results'] as List<dynamic>? ?? const [];
              final promotedSessionData = Map<String, dynamic>.from(sessionData);
              promotedSessionData['search_results'] = mergedResults;
              promotedSessionData['persisted_merge_session_uuid'] = mergeSessionUuid;
              promotedSessionData['persisted_merge_session_reused'] =
                  mergeResponse.data!['reused_existing_session'] as bool? ?? false;
              promotedSessionData['hierarchical_merge_applied'] = true;
              promotedSessionData['merge_rule_applied'] = 'backend-owned';
              promotedSessionData['pre_merge_count'] = rawResults.length;
              promotedSessionData['post_merge_count'] = mergedUuids.length;
              promotedSessionData['merge_statistics'] = {
                'total_mvr': rawResults.length,
                'super_individuals': mergedUuids.length,
                'merges_performed': rawResults.length - mergedUuids.length,
                'standalone_individuals': mergedUuids.length,
              };

              _navigateToCrossVideoAnalysis(
                individualUuids: mergedUuids,
                sessionUuid: mergeSessionUuid,
                sessionData: promotedSessionData,
              );
              return;
            }
          }
        }
      }

      // Extract MVR people from search results
      final mvrPeople = _trackingSessionData!['search_results'] as List<dynamic>;

      if (mvrPeople.isEmpty) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No MVR people found in search results')),
          );
        }
        return;
      }

      // Extract MVR person UUIDs
      final List<String> mvrPersonUuids = mvrPeople
          .map((mvr) => mvr['mvr_people_uuid'].toString())
          .toList();
      final updatedSessionData = Map<String, dynamic>.from(_trackingSessionData!);
      updatedSessionData['merge_statistics'] = {
        'total_mvr': mvrPersonUuids.length,
        'super_individuals': mvrPersonUuids.length,
        'merges_performed': 0,
        'standalone_individuals': mvrPersonUuids.length,
      };
      updatedSessionData['pre_merge_count'] = mvrPersonUuids.length;
      updatedSessionData['post_merge_count'] = mvrPersonUuids.length;
      updatedSessionData['hierarchical_merge_applied'] = false;
      updatedSessionData['merge_rule_applied'] = 'backend-owned';

      _navigateToCrossVideoAnalysis(
        individualUuids: mvrPersonUuids,
        sessionUuid: 'mvr_search_${DateTime.now().millisecondsSinceEpoch}',
        sessionData: updatedSessionData,
      );
    } catch (e) {
      print('❌ Error preparing MVR search analysis: $e');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error opening analysis: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Navigate to cross-video analysis with context
  void _navigateToCrossVideoAnalysis({
    required List<String> individualUuids,
    required String sessionUuid,
    required Map<String, dynamic> sessionData,
  }) {
    final context = CrossVideoAnalysisContext(
      individualUuids: individualUuids,
      sessionUuid: sessionUuid,
      sessionData: sessionData,
    );
    
    // Navigate using MaterialPageRoute (direct navigation)
    // TODO: Update to use go_router when PersonObjectsDetailScreen is updated
    Navigator.of(this.context).push(
      MaterialPageRoute(
        builder: (ctx) => PersonObjectsDetailScreen(
          crossVideoContext: context,
        ),
      ),
    );
  }

  /// Fetch individuals count from cross-video tracking
  /// 
  /// MODIFIED: Now searches for existing MVR people instead of creating
  /// a new tracking session. This fetches cached/existing analysis results
  /// without triggering any merge operations.
  Future<void> _fetchIndividualsCount() async {
    if (_startDate == null || _endDate == null || _selectedCollection == null) {
      return;
    }

    setState(() {
      _isLoadingIndividuals = true;
      _individualsCount = null;
      _uniqueMvrCount = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);

      // Use collection UUID as primary identifier for media search filtering.
      // cameraDeviceId is not a collection identifier and may not resolve in
      // backend collection filtering after camera ID format changes.
      // Keep cameraDeviceId as fallback for legacy compatibility only.
      final collectionUuid = _selectedCollection!.uuid;
      final cameraUuids = _resolveCollectionCameraUuids(_selectedCollection);
      if (collectionUuid == null || collectionUuid.isEmpty || cameraUuids.isEmpty) {
        print('ERROR: Collection UUID or camera UUIDs are missing, cannot search or materialize MVR data');
        setState(() {
          _individualsCount = 0;
          _uniqueMvrCount = 0;
          _isLoadingIndividuals = false;
        });
        return;
      }
      
      print('🔍 Searching existing MVR people for collection UUID: $collectionUuid');
      print('   Camera UUIDs: ${cameraUuids.join(", ")}');
      print('   Date range: ${_startDate!.toIso8601String()} to ${_endDate!.toIso8601String()}');
      
      // Step 1: Get all videos from this collection within date range
      final mediaResponse = await mediaApiClient.searchMedia(
        collectionId: collectionUuid,
        mediaType: MediaType.video,
        startDate: _startDate,
        endDate: _endDate,
        limit: 500,
      );

      if (!mediaResponse.success || mediaResponse.data == null || mediaResponse.data!.items.isEmpty) {
        print('   No videos found for collection');
        setState(() {
          _individualsCount = 0;
          _uniqueMvrCount = 0;
          _isLoadingIndividuals = false;
        });
        return;
      }

      final videoUuids = mediaResponse.data!.items.map((media) => media.uuid).toList();
      print('   Found ${videoUuids.length} videos in collection');

      final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
      final mergeRule = generalSettings?.mergeIndividualsRule ?? 'none';

      final mergeThreshold =
          generalSettings?.mergeIndividualsThreshold ?? 0.70;
      final autoMerge = mergeRule == 'auto';
      print(
        '   Backend MVR search settings: mergeRule=$mergeRule, '
        'autoMerge=$autoMerge, threshold=$mergeThreshold',
      );

      final videoDetails = mediaResponse.data!.items
          .map((media) => {
                'video_uuid': media.uuid,
                'media_timestamp': media.createdAt.toUtc().toIso8601String(),
              })
          .toList();
      if (cameraUuids.length == 1) {
        for (final detail in videoDetails) {
          detail['camera_uuid'] = cameraUuids.first;
        }
      }
      
      // Step 2: Search for existing MVR people in these videos
      final searchResponse = autoMerge
          ? await mediaApiClient.searchPersistedMergedMVRPeopleByVideos(
            cameraUuids: cameraUuids,
              videoUuids: videoUuids,
              startTime: _startDate,
              endTime: _endDate,
              limit: 500,
              similarityThreshold: mergeThreshold,
              videoDetails: videoDetails,
            )
          : await mediaApiClient.searchMVRPeopleByVideos(
              videoUuids: videoUuids,
              startTime: _startDate,
              endTime: _endDate,
              limit: 500,
              autoMerge: autoMerge,
              similarityThreshold: mergeThreshold,
            );

      if (searchResponse.success && searchResponse.data != null) {
        final payload = autoMerge
            ? (searchResponse.data!['result_payload'] as Map<String, dynamic>? ?? const {})
            : searchResponse.data!;
        final mvrPeople = payload['mvr_people'] as List<dynamic>? ?? const [];
        final totalResults = payload['total_results'] as int? ?? mvrPeople.length;
        final persistedSessionUuid = autoMerge
            ? searchResponse.data!['search_session_uuid'] as String?
            : null;

        if (totalResults == 0 && videoUuids.isNotEmpty) {
          print('ℹ️ No persisted MVR rows found, triggering backend materialization session...');

          final sessionResponse = await mediaApiClient.createCrossVideoTrackingSession(
            collectionName: collectionUuid,
            videoUuids: videoUuids,
          );

          if (sessionResponse.success && sessionResponse.data != null) {
            final sessionUuid = sessionResponse.data!['session_uuid'] as String?;
            if (sessionUuid != null && sessionUuid.isNotEmpty) {
              setState(() {
                _trackingSessionUuid = sessionUuid;
              });
              await _pollTrackingSessionStatus(mediaApiClient, sessionUuid);
              return;
            }
          }

          print('ERROR: Failed to trigger backend materialization session: ${sessionResponse.error}');
        }
        
        print('✅ Found $totalResults existing MVR people');
        
        // Each MVR person represents a unique individual (already merged)
        // Count total appearances across all MVR people
        int totalAppearances = 0;
        for (var mvr in mvrPeople) {
          totalAppearances += (mvr['total_appearances'] as int? ?? 0);
        }
        
        setState(() {
          _individualsCount = totalAppearances; // Total original detections
          _uniqueMvrCount = totalResults;  // Unique people (already merged)
          _uniqueCountIsFallback = false;
          _isLoadingIndividuals = false;
          
          // Reuse the persisted merge-session UUID when available, otherwise use a local placeholder.
          _trackingSessionUuid = persistedSessionUuid ?? 'mvr_search_${DateTime.now().millisecondsSinceEpoch}';
          
          // Store MVR search results for navigation to analysis screen
          _trackingSessionData = {
            'search_results': mvrPeople,
            'total_mvr_people': totalResults,
            'total_appearances': totalAppearances,
            'search_parameters': payload['search_parameters'],
            'collection_name': _selectedCollection!.name, // Add collection name
            'collection_id': collectionUuid,
            'camera_uuids': cameraUuids,
            'persisted_merge_session_uuid': persistedSessionUuid,
            'persisted_merge_session_reused': autoMerge
                ? (searchResponse.data!['reused_existing_session'] as bool? ?? false)
                : false,
          };
        });
        
        print('📊 MVR Search Results:');
        print('   Total appearances: $totalAppearances');
        print('   Unique MVR people: $totalResults');
        
      } else {
        print('ERROR: Failed to search MVR people: ${searchResponse.error}');
        setState(() {
          _individualsCount = 0;
          _uniqueMvrCount = 0;
          _isLoadingIndividuals = false;
        });
      }
    } catch (e) {
      print('ERROR: Exception searching MVR people: $e');
      setState(() {
        _individualsCount = 0;
        _uniqueMvrCount = 0;
        _isLoadingIndividuals = false;
      });
    }
  }

  /// Poll tracking session status until completed
  Future<void> _pollTrackingSessionStatus(MediaApiClient apiClient, String sessionUuid) async {
    int attempts = 0;
    const maxAttempts = 30; // 30 seconds max
    const pollInterval = Duration(seconds: 1);

    while (attempts < maxAttempts) {
      try {
        final statusResponse = await apiClient.getCrossVideoTrackingSessionStatus(
          sessionUuid: sessionUuid,
        );

        if (statusResponse.success && statusResponse.data != null) {
          final status = statusResponse.data!['status'] as String;
          final individualsFound = statusResponse.data!['individuals_found'] as int? ?? 0;
          
          print('');
          print('### FLUTTER COUNTER DEBUG - DETAILED API RESPONSE ###');
          print('=' * 80);
          print('Session Status Response:');
          print('   Status: $status');
          print('   Session UUID: $sessionUuid');
          print('');
          print('FULL RAW API RESPONSE DATA:');
          print('   ${statusResponse.data}');
          print('');
          print('CHECKING ALL COUNTER FIELDS:');
          print('   individuals_found: ${statusResponse.data!['individuals_found']} (type: ${statusResponse.data!['individuals_found']?.runtimeType})');
          print('   unique_mvr_people_count: ${statusResponse.data!['unique_mvr_people_count']} (type: ${statusResponse.data!['unique_mvr_people_count']?.runtimeType})');
          print('   cache_hits: ${statusResponse.data!['cache_hits']} (type: ${statusResponse.data!['cache_hits']?.runtimeType})');
          print('   total_videos: ${statusResponse.data!['total_videos']}');
          print('   processed_videos: ${statusResponse.data!['processed_videos']}');
          print('');
          
          // Check if API actually returned unique_mvr_people_count
          final hasUniqueCount = statusResponse.data!.containsKey('unique_mvr_people_count');
          final uniqueMvrCount = statusResponse.data!['unique_mvr_people_count'] as int?;
          
          print('UNIQUE COUNT FIELD CHECK:');
          print('   Field exists in response: $hasUniqueCount');
          print('   Field value: $uniqueMvrCount');
          print('   Field is null: ${uniqueMvrCount == null}');
          print('   Field is 0: ${uniqueMvrCount == 0}');
          print('');
          
          // Update counters on every poll (not just when completed)
          setState(() {
            _individualsCount = individualsFound;
            
            if (hasUniqueCount && uniqueMvrCount != null) {
              // API returned real unique count
              _uniqueMvrCount = uniqueMvrCount;
              _uniqueCountIsFallback = false;
              print('SETTING UNIQUE COUNT FROM API: $_uniqueMvrCount');
            } else {
              // API didn't return unique count, using fallback
              _uniqueMvrCount = individualsFound;
              _uniqueCountIsFallback = true;
              print('WARNING - USING FALLBACK COUNT: $_uniqueMvrCount (hasUniqueCount=$hasUniqueCount, uniqueMvrCount=$uniqueMvrCount)');
            }
          });
          
          print('');
          print('FINAL UI COUNTER VALUES (AFTER setState):');
          print('=' * 80);
          print('   _individualsCount: $_individualsCount');
          print('   _uniqueMvrCount: $_uniqueMvrCount');
          print('   _uniqueCountIsFallback: $_uniqueCountIsFallback');
          print('');
          print('FLUTTER WILL DISPLAY:');
          print('   "Individuals: $_individualsCount → ${_uniqueCountIsFallback ? "[]" : "$_uniqueMvrCount unique"}"');
          print('=' * 80);
          print('');
          
          if (status == 'completed') {
            print('');
            print('=' * 80);
            print('SESSION COMPLETED!');
            print('=' * 80);
            print('   Original individuals found: $individualsFound');
            print('   Now triggering auto-merge...');
            print('');
            
            // Trigger automatic duplicate merging via MVR-People
            await _autoMergeDuplicates(
              apiClient,
              sessionUuid,
              individualsFound,
            );
            
            setState(() {
              _isLoadingIndividuals = false;
              _trackingSessionData = statusResponse.data; // Store full session data
            });
            return;
          } else if (status == 'failed') {
            print('ERROR: Tracking session failed');
            setState(() {
              _individualsCount = 0;
              _uniqueMvrCount = 0;
              _isLoadingIndividuals = false;
            });
            return;
          }
        }

        await Future.delayed(pollInterval);
        attempts++;
      } catch (e) {
        print('ERROR: Exception polling tracking session: $e');
        break;
      }
    }

    // Timeout
    print('WARNING: Tracking session polling timed out');
    setState(() {
      _individualsCount = 0;
      _uniqueMvrCount = 0;
      _isLoadingIndividuals = false;
    });
  }

  /// Automatically merge duplicate individuals using MVR-People batch matching
  /// 
  /// This function is called when a cross-video tracking session completes.
  /// It retrieves all individuals from the session and uses the batch merge
  /// Auto-merge duplicates after cross-video tracking session completes.
  /// 
  /// NOTE: Automatic merging now happens during session processing via
  /// merge_individuals_by_similarity(). The session status already contains
  /// the correct unique_mvr_people_count. This function is now a no-op.
  /// 
  /// Updates the UI counters:
  /// - _individualsCount: Original count before merging (already set)
  /// - _uniqueMvrCount: Already set from session status (unique_mvr_people_count)
  /// - _uniqueCountIsFallback: Set to false when real merge data is available
  Future<void> _autoMergeDuplicates(
    MediaApiClient apiClient,
    String sessionUuid,
    int originalCount,
  ) async {
    try {
      print('🔄 Auto-merge: Session processing already merged individuals');
      print('  Original count: $originalCount');
      print('  Unique count already set from session status: $_uniqueMvrCount');
      print('  Skipping redundant batch merge call');
      
      // The merge already happened during session processing!
      // unique_mvr_people_count from session status is the correct value.
      // No need to call batchMatchAndMerge() again.
      // The merge already happened during session processing!
      // unique_mvr_people_count from session status is the correct value.
      // No need to call batchMatchAndMerge() again.
      
      /* DISABLED - Merge already happens during session processing
      // Step 1: Get all individuals from the session
      final individualsResponse = await apiClient.getCrossVideoIndividuals(
        sessionUuid: sessionUuid,
      );

      if (!individualsResponse.success || individualsResponse.data == null) {
        print('ERROR - Failed to get session individuals: ${individualsResponse.error}');
        print('   Response data: ${individualsResponse.data}');
        // Keep fallback values (already set in polling function)
        return;
      }

      print('Got session individuals response: ${individualsResponse.data}');

      // Step 2: Extract individual UUIDs from the response
      final individuals = individualsResponse.data!['individuals'] as List<dynamic>? ?? [];
      
      print('📊 Individuals count in response: ${individuals.length}');
      
      if (individuals.isEmpty) {
        print('WARNING - No individuals found in session, skipping merge');
        print('   Expected $originalCount but got 0 from API');
        print('   This might indicate the session completed but individuals endpoint is empty');
        print('   KEEPING existing counter values from session status');
        // DON'T reset to 0! The session status already has the correct unique_mvr_people_count
        // Just skip the merge operation
        return;
      }

      final individualUuids = individuals
          .map((individual) => individual['individual_uuid'] as String?)
          .where((uuid) => uuid != null)
          .cast<String>()
          .toList();

      print('  Extracted ${individualUuids.length} individual UUIDs');

      if (individualUuids.isEmpty) {
        print('⚠️ No valid individual UUIDs found, skipping merge');
        return;
      }

      // Step 3: Call batch match and merge endpoint
      final mergeResponse = await apiClient.batchMatchAndMerge(
        individualUuids: individualUuids,
        threshold: 0.65, // 65% similarity threshold
        triggeredBy: 'cross_video_tracking_session',
        sessionUuid: sessionUuid,
      );

      if (!mergeResponse.success || mergeResponse.data == null) {
        print('❌ Batch merge failed: ${mergeResponse.error}');
        // Keep fallback values (already set in polling function)
        return;
      }

      // Step 4: Update UI with merge results
      final mergeData = mergeResponse.data!;
      final uniqueCount = mergeData['unique_count'] as int? ?? originalCount;
      final mergeCount = mergeData['merge_count'] as int? ?? 0;
      final processingTime = mergeData['processing_time_seconds'] as double? ?? 0.0;

      print('✅ Auto-merge complete:');
      print('   Original: $originalCount individuals');
      print('   Unique: $uniqueCount individuals');
      print('   Merged: $mergeCount duplicates');
      print('   Time: ${processingTime.toStringAsFixed(2)}s');

      setState(() {
        _uniqueMvrCount = uniqueCount;
        _uniqueCountIsFallback = false; // We have real merge data now
      });
      */

    } catch (e) {
      print('❌ Auto-merge error: $e');
      // Keep fallback values on error
      // Don't update state - keep existing fallback counter
    }
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
  void _openItemDetails(MediaItem item) async {
    final result = await showDialog(
      context: context,
      builder: (context) => MediaDetailsDialog(
        item: item,
        collectionId: _selectedCollection?.uuid, // Pass collection ID
      ),
    );
    if (result == 'deleted' && mounted) {
      setState(() {
        _mediaGallery = null; // Force gallery rebuild to reflect deletion
      });
    }
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

  /// Show search dialog for date/time filtering
  /// Show search dialog for date/time filtering
  Future<void> _showSearchDialog() async {
    await showDialog(
      context: context,
      builder: (context) => CollectionsSearchDialog(
        initialStartDate: _startDate,
        initialEndDate: _endDate,
        onApply: (startDate, endDate) {
          setState(() {
            _startDate = startDate;
            _endDate = endDate;
            // Force rebuild of media gallery with new filters
            _mediaGallery = null;
          });
          
          // Fetch individuals count from vmeta service
          _fetchIndividualsCount();
        },
      ),
    );
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
    final sourceCollectionId = _selectedCollection?.uuid;
    
    setState(() {
      _isProcessing = true;
    });

    try {
      final mediaIds = items.map((item) => item.mediaId).toList();
      final success = await organizationService.bulkMoveMedia(
        mediaIds,
        targetCollectionId,
        sourceCollectionId: sourceCollectionId,
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
      final success = await organizationService.copyMediaToCollection(
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

  /// Process selected items with Vision AI
  void _processWithVision() async {
    if (_selectedItems.isEmpty) return;
    
    try {
      // Show confirmation dialog
      final confirmed = await _showVisionConfirmationDialog();
      if (!confirmed) return;
      
      // Get auth token from ApiClient
      final apiClient = ref.read(apiClientProvider);
      final authToken = apiClient.authToken;
      
      if (authToken == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Authentication required. Please log in again.'),
              backgroundColor: AppColors.error,
            ),
          );
        }
        return;
      }
      
      // Create vision processing service with auth token
      final visionService = VisionProcessingService(authToken: authToken);
      
      // Show progress dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => VisionProcessingDialog(
          mediaIds: _selectedItems.map((item) => item.uuid).toList(),
          visionService: visionService,
        ),
      );
      
      // Execute vision processing
      final mediaIds = _selectedItems.map((item) => item.uuid).toList();
      final workflowSettings = ref.read(workflow_section.workflowSettingsProvider);
      final result = await visionService.processSelectedMedia(
        mediaIds: mediaIds,
        minFaceQuality: workflowSettings.mvrQualityThreshold,
      );
      
      // Close progress dialog
      if (mounted) {
        Navigator.pop(context);
        
        // Show results dialog
        await showDialog(
          context: context,
          builder: (context) => VisionResultsDialog(result: result),
        );
        
        // Exit selection mode
        _exitSelectionMode();
        
        // Optionally refresh the view to show updated data
        setState(() {
          // Trigger rebuild
        });
      }
    } catch (e) {
      // Close progress dialog if open
      if (mounted) {
        Navigator.pop(context);
        _showErrorMessage('Vision processing error: $e');
      }
    }
  }
  
  /// Show Vision confirmation dialog
  Future<bool> _showVisionConfirmationDialog() async {
    return await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.visibility, color: AppColors.primary),
            const SizedBox(width: AppSpacing.sm),
            const Text('Vision Processing'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Process ${_selectedItems.length} media item${_selectedItems.length == 1 ? '' : 's'} with AI face recognition?',
              style: AppTextStyles.bodyLarge,
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'This will:',
              style: AppTextStyles.labelLarge.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            _buildInfoItem('Detect faces in selected media'),
            _buildInfoItem('Create MVR people records'),
            _buildInfoItem('Extract demographics (age, gender)'),
            _buildInfoItem('Generate face embeddings'),
            const SizedBox(height: AppSpacing.lg),
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.info.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: AppColors.info.withOpacity(0.3),
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: AppColors.info, size: 20),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      'Processing may take a few seconds per media item',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.info,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton.icon(
            onPressed: () => Navigator.pop(context, true),
            icon: const Icon(Icons.play_arrow),
            label: const Text('Start Processing'),
          ),
        ],
      ),
    ) ?? false;
  }
  
  Widget _buildInfoItem(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Icon(
            Icons.check_circle_outline,
            size: 16,
            color: AppColors.success,
          ),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: Text(
              text,
              style: AppTextStyles.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  /// Share selected items
  void _shareSelectedItems() async {
    if (_selectedItems.isEmpty) return;
    
    try {
      final apiClient = ref.read(apiClientProvider);
      final mediaUrls = _selectedItems
          .map((item) => '${Config.gatewayServiceUrl}${item.url}')
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

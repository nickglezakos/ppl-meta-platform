import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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
import '../services/media_organization_service.dart';
import '../services/media_api_client.dart';
import '../providers/media_organization_providers.dart';
import 'person_objects_detail_screen.dart';

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
  int? _individualsCount;
  bool _isLoadingIndividuals = false;
  String? _trackingSessionUuid;
  Map<String, dynamic>? _trackingSessionData;

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
                      Text(
                        _individualsCount?.toString() ?? 'Loading...',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
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
                            _individualsCount?.toString() ?? 'Loading...',
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: AppColors.primary,
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
                            _individualsCount?.toString() ?? 'Loading...',
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: AppColors.primary,
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
  Future<void> _showIndividualsDetails() async {
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
            if (_individualsCount != null)
              Text('• $_individualsCount unique individual${_individualsCount == 1 ? '' : 's'} detected'),
            if (_individualsCount == null)
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
  Future<void> _navigateToIndividualAnalysis() async {
    if (_trackingSessionUuid == null || _trackingSessionData == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No tracking session data available')),
      );
      return;
    }

    try {
      // Show loading indicator
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(
          child: CircularProgressIndicator(),
        ),
      );

      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);

      // Fetch individuals data from vmeta endpoint
      final individualsResponse = await mediaApiClient.getCrossVideoIndividuals(
        sessionUuid: _trackingSessionUuid!,
      );

      // Dismiss loading
      if (mounted) Navigator.pop(context);

      if (individualsResponse.success && individualsResponse.data != null) {
        final individuals = individualsResponse.data!['individuals'] as List<dynamic>;

        if (individuals.isEmpty) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('No individuals found in tracking session')),
            );
          }
          return;
        }

        // Extract individual UUIDs
        final individualUuids = individuals
            .map((ind) => ind['individual_uuid'] as String)
            .toList();

        // Navigate to person details screen with cross-video context
        _navigateToCrossVideoAnalysis(
          individualUuids: individualUuids,
          sessionUuid: _trackingSessionUuid!,
          sessionData: _trackingSessionData!,
        );
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to fetch individuals data: ${individualsResponse.error}'),
            ),
          );
        }
      }
    } catch (e) {
      // Dismiss loading if still showing
      if (mounted && Navigator.canPop(context)) {
        Navigator.pop(context);
      }
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
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
  Future<void> _fetchIndividualsCount() async {
    if (_startDate == null || _endDate == null || _selectedCollection == null) {
      return;
    }

    setState(() {
      _isLoadingIndividuals = true;
      _individualsCount = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);

      // Create cross-video tracking session
      // Use cameraDeviceId if available (for camera-linked collections),
      // otherwise use UUID, then fallback to id
      final collectionIdentifier = _selectedCollection!.cameraDeviceId ?? 
                                   _selectedCollection!.uuid ?? 
                                   _selectedCollection!.id;
      
      final createResponse = await mediaApiClient.createCrossVideoTrackingSession(
        collectionName: collectionIdentifier,
        startTime: _startDate!,
        endTime: _endDate!,
      );

      if (createResponse.success && createResponse.data != null) {
        final sessionUuid = createResponse.data!['session_uuid'] as String;
        _trackingSessionUuid = sessionUuid;

        // Poll for session completion
        await _pollTrackingSessionStatus(mediaApiClient, sessionUuid);
      } else {
        print('ERROR: Failed to create tracking session: ${createResponse.error}');
        setState(() {
          _individualsCount = 0;
          _isLoadingIndividuals = false;
        });
      }
    } catch (e) {
      print('ERROR: Exception fetching individuals count: $e');
      setState(() {
        _individualsCount = 0;
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
          
          if (status == 'completed') {
            final individualsFound = statusResponse.data!['individuals_found'] as int? ?? 0;
            setState(() {
              _individualsCount = individualsFound;
              _isLoadingIndividuals = false;
              _trackingSessionData = statusResponse.data; // Store full session data
            });
            return;
          } else if (status == 'failed') {
            print('ERROR: Tracking session failed');
            setState(() {
              _individualsCount = 0;
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
      _isLoadingIndividuals = false;
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
      builder: (context) => MediaDetailsDialog(
        item: item,
        collectionId: _selectedCollection?.uuid, // Pass collection ID
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

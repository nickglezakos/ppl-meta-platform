import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart' as dio;
import 'dart:ui' as ui;
import 'dart:io';
import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';
import 'package:excel/excel.dart' as excel;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import '../core/config.dart';
import '../models/person_objects_models.dart';
import '../models/cross_video_analysis_models.dart';
import '../providers/person_objects_provider.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/triggers_tab.dart';
import '../widgets/editable_mvr_name.dart';
import '../widgets/editable_mvr_gender.dart';
import '../widgets/individual_groups/add_to_group_dialog.dart';
import '../models/media_models.dart';
import '../core/api/api_client.dart';
import '../core/providers/camera_providers.dart';
import '../services/media_api_client.dart';
import '../services/individual_groups_api_client.dart';
import '../services/mvr_image_service.dart';
import '../providers/mvr_image_service_provider.dart';
import '../providers/settings_providers.dart';
import '../models/mvr_best_image.dart';
import '../utils/platform_file_download.dart';
import 'media_preview_screen.dart';
import '../core/providers/provider_bridge.dart';

/// Detailed screen for viewing person objects results and analysis
/// 
/// Supports two modes:
/// 1. Single-video mode: Displays analysis for one video (mediaItem)
/// 2. Cross-video mode: Displays aggregated analysis across multiple videos (crossVideoContext)
class PersonObjectsDetailScreen extends ConsumerStatefulWidget {
  // Single-video mode
  final MediaItem? mediaItem;
  
  // Cross-video mode
  final CrossVideoAnalysisContext? crossVideoContext;

  const PersonObjectsDetailScreen({
    super.key,
    this.mediaItem,
    this.crossVideoContext,
  }) : assert(
    (mediaItem != null && crossVideoContext == null) ||
    (mediaItem == null && crossVideoContext != null),
    'Either mediaItem or crossVideoContext must be provided, but not both',
  );

  @override
  ConsumerState<PersonObjectsDetailScreen> createState() => 
      _PersonObjectsDetailScreenState();
}

class _PersonObjectsDetailScreenState 
    extends ConsumerState<PersonObjectsDetailScreen> 
    with TickerProviderStateMixin {

  void print(Object? message) {}

  void debugPrint(String? message, {int? wrapWidth}) {}
  
  late TabController _tabController;
  // late TabController _visionTabController; // Nested tab controller for Vision tab - COMMENTED OUT
  final Set<String> _debuggedFaces = {}; // Cache for debug output
  String _routesDisplayMode = 'scatter'; // 'path' or 'scatter' - default to scatter
  
  // Cache for routes data to prevent excessive API calls
  Map<String, dynamic>? _cachedRoutesData;
  bool _isLoadingRoutes = false;
  
  // Cross-video analysis state
  bool _isCrossVideoMode = false;
  List<AggregatedIndividualAnalysis>? _aggregatedAnalyses;
  bool _isLoadingCrossVideoData = false;
  String? _crossVideoError;
  
  // Track expanded individuals in cross-video mode
  final Set<String> _expandedIndividuals = {};
  
  // Track selected individuals for merging
  final Set<String> _selectedIndividuals = {};
  
  // Similarity threshold for merging (adjustable by user)
  double _similarityThreshold = 0.7;
  
  // Best images for individuals in cross-video mode
  Map<String, BestImageResponse?> _bestImages = {};

  // Best images for child (merged-in) MVR cards
  Map<String, BestImageResponse?> _childMvrImages = {};

  // ── Merged-children pagination state ─────────────────────────────────────
  // Keyed by super-individual UUID. Populated by _loadMoreMergedChildren().
  static const int _mergedChildrenPageSize = 10;
  final Map<String, List<MergedMVRPerson>> _pagedMergedChildren = {};
  final Map<String, bool> _loadingMoreChildren = {};
  final Map<String, bool> _hasMoreChildren = {};
  final Map<String, int> _mergedChildrenNextPage = {};
  // ─────────────────────────────────────────────────────────────────────────

  // Whether a hierarchical merge was applied during the last search
  bool _hierarchicalMergeWasApplied = false;

  // Merge groups captured from the last cross-video load (for undo banner)
  List<MergeGroupSummary> _mergeGroups = [];

  // After a manual merge the winner UUID(s) replace the original list so
  // the immediate reload shows the merged state instead of stale pre-merge UUIDs.
  List<String>? _overrideIndividualUuids;

  // Cross-video paged route state (new route paging endpoints)
  // Keep initial payload small so route loading is visibly paged in the UI.
  final int _routePageSize = 100;
    final Map<String, Map<String, List<Map<String, dynamic>>>>
      _routePointsByCamera = {};
    final Map<String, Map<String, int>> _routePageIndexByCameraSource = {};
    final Map<String, Map<String, bool>> _routeHasMoreByCameraSource = {};
    final Map<String, Map<String, int>> _routeTotalPointsByCameraSource = {};
    final Map<String, Map<String, String>> _routeDisplayIndividualByCameraSource =
      {};
    final Map<String, String> _routeCameraNamesById = {};
    final Map<String, String> _routeDisplayPersonIdByUuid = {};
    final Set<String> _loadedRouteSourceIndividuals = {};
    String? _selectedRouteCameraId;
    Future<List<Map<String, dynamic>>>? _crossVideoRoutesFetchInFlight;
  bool _isLoadingMoreCrossVideoRoutes = false;

  @override
  void initState() {
    super.initState();
    
    // Determine mode
    _isCrossVideoMode = widget.crossVideoContext != null;

    final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
    _similarityThreshold = generalSettings?.mergeIndividualsThreshold ?? 0.70;
    
    _tabController = TabController(length: 4, vsync: this);
    // _visionTabController = TabController(length: 3, vsync: this); // Vision tab has 3 sub-tabs - COMMENTED OUT
    
    // Load cross-video data if in that mode
    if (_isCrossVideoMode) {
      _loadCrossVideoData();
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    // _visionTabController.dispose(); // COMMENTED OUT
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: _isCrossVideoMode 
            ? 'Cross-Video Individual Analysis' 
            : 'Person Objects Analysis',
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Analysis',
            onPressed: () => _isCrossVideoMode 
                ? _loadCrossVideoData() 
                : _refreshAnalysis(),
          ),
          if (!_isCrossVideoMode)
            IconButton(
              icon: const Icon(Icons.play_arrow),
              tooltip: 'Trigger New Analysis',
              onPressed: () => _triggerNewAnalysis(),
            ),
        ],
      ),
      body: _isCrossVideoMode 
          ? _buildCrossVideoView() 
          : _buildSingleVideoView(),
      floatingActionButton: _isCrossVideoMode && _selectedIndividuals.isNotEmpty
          ? FloatingActionButton.extended(
              onPressed: _showActionsDialog,
              icon: const Icon(Icons.admin_panel_settings),
              label: Text('Actions (${_selectedIndividuals.length})'),
              backgroundColor: Colors.blue,
            )
          : null,
    );
  }

  /// Build single-video analysis view (existing functionality)
  Widget _buildSingleVideoView() {
    return Column(
      children: [
        TabBar(
          controller: _tabController,
          tabs: const [
            Tab(
              icon: Icon(Icons.groups),
              text: 'Persons',
            ),
            Tab(
              icon: Icon(Icons.route),
              text: 'Routes',
            ),
            Tab(
              icon: Icon(Icons.analytics),
              text: 'Overview',
            ),
            Tab(
              icon: Icon(Icons.face),
              text: 'Face Details',
            ),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildPersonGroupsTab(),
              _buildRoutesTab(),
              _buildOverviewTab(),
              _buildFaceDetailsTab(),
            ],
          ),
        ),
      ],
    );
  }

  /// Build cross-video analysis view
  Widget _buildCrossVideoView() {
    if (_isLoadingCrossVideoData) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading cross-video analysis data...'),
            SizedBox(height: 8),
            Text(
              'Fetching person objects from multiple videos',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      );
    }
    
    if (_crossVideoError != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text(_crossVideoError!),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadCrossVideoData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }
    
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(
        child: Text('No individual data available'),
      );
    }
    
    // Use EXACT SAME TABS as single-video mode
    return Column(
      children: [
        // Cross-Video Analysis information bar
        _buildCrossVideoInfoBar(),
        TabBar(
          controller: _tabController,
          tabs: const [
            Tab(
              icon: Icon(Icons.analytics),
              text: 'Statistics',
            ),
            Tab(
              icon: Icon(Icons.route),
              text: 'Routes',
            ),
            Tab(
              icon: Icon(Icons.groups),
              text: 'Individuals',
            ),
            Tab(
              icon: Icon(Icons.event_available),
              text: 'Attendance',
            ),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildStatisticsTabCrossVideo(),
              _buildRoutesTabCrossVideo(),
              _buildIndividualsTabCrossVideo(),
              _buildAttendanceTab(), // Direct attendance tab instead of nested Vision tab
            ],
          ),
        ),
      ],
    );
  }

  /// Build responsive information bar for cross-video analysis
  /// Shows timeframe (from/to dates) and collection name in a single row
  Widget _buildCrossVideoInfoBar() {
    final context = widget.crossVideoContext!;
    
    // Check if this is a camera search
    final isCameraSearch = context.sessionData['source'] == 'individual_group_camera_search';
    
    // Extract dates and collection name from sessionData
    DateTime? startTime;
    DateTime? endTime;
    String collectionName = '';
    
    // DEBUG: Print detailed sessionData structure
    print('');
    print('═══════════════════════════════════════════════════════');
    print('🔍 DEBUG INFO BAR: Analyzing sessionData structure');
    print('═══════════════════════════════════════════════════════');
    print('📦 FULL sessionData:');
    print(context.sessionData);
    print('');
    print('🔑 sessionData keys: ${context.sessionData.keys.toList()}');
    print('');
    
    // Check each top-level key
    context.sessionData.forEach((key, value) {
      print('   $key: ${value.runtimeType} = ${value is Map || value is List ? value : value.toString()}');
    });
    print('');
    
    // Try to get search parameters (from MVR search)
    if (context.sessionData['search_parameters'] != null) {
      final searchParams = context.sessionData['search_parameters'] as Map<String, dynamic>;
      print('📋 search_parameters found!');
      print('   Keys: ${searchParams.keys.toList()}');
      searchParams.forEach((key, value) {
        print('   $key: ${value.runtimeType} = $value');
      });
      print('');
      
      // Parse start and end times
      if (searchParams['start_time'] != null) {
        startTime = DateTime.tryParse(searchParams['start_time'].toString());
        print('✅ Parsed start_time: $startTime');
      }
      if (searchParams['end_time'] != null) {
        endTime = DateTime.tryParse(searchParams['end_time'].toString());
        print('✅ Parsed end_time: $endTime');
      }
      
      // Get collection name from search parameters - try multiple possible keys
      print('');
      print('🔍 Searching for collection name in search_parameters...');
      if (searchParams['collection_id'] != null) {
        collectionName = searchParams['collection_id'].toString();
        print('✅ Found collection_id = "$collectionName"');
      } else if (searchParams['collection'] != null) {
        collectionName = searchParams['collection'].toString();
        print('✅ Found collection = "$collectionName"');
      } else if (searchParams['collections'] is List && (searchParams['collections'] as List).isNotEmpty) {
        collectionName = searchParams['collections'][0].toString();
        print('✅ Found collections[0] = "$collectionName"');
      } else {
        print('❌ No collection found in search_parameters');
      }
    } else {
      print('❌ No search_parameters found in sessionData');
    }
    
    print('');
    print('🔍 Checking context.collections (CrossVideoAnalysisContext)...');
    print('   collections count: ${context.collections.length}');
    print('   collections: ${context.collections}');
    
    // Fallback to context collections if not found in search parameters
    if (collectionName.isEmpty && context.collections.isNotEmpty) {
      collectionName = context.collections.first;
      print('✅ Using context.collections fallback = "$collectionName"');
    }
    
    // Final fallback - check sessionData directly
    if (collectionName.isEmpty) {
      print('');
      print('🔍 Trying direct sessionData keys...');
      print('   isCameraSearch = $isCameraSearch');
      print('   camera_name exists = ${context.sessionData.containsKey("camera_name")}');
      print('   camera_name value = ${context.sessionData["camera_name"]}');
      
      // For camera searches, camera_name is the collection
      if (isCameraSearch && context.sessionData['camera_name'] != null) {
        collectionName = context.sessionData['camera_name'].toString();
        print('✅ Found sessionData.camera_name = "$collectionName"');
      }
      // Check for collection_name (primary key added in v2.19.40)
      else if (context.sessionData['collection_name'] != null) {
        collectionName = context.sessionData['collection_name'].toString();
        print('✅ Found sessionData.collection_name = "$collectionName"');
      } 
      // Fallback to collection_id
      else if (context.sessionData['collection_id'] != null) {
        collectionName = context.sessionData['collection_id'].toString();
        print('✅ Found sessionData.collection_id = "$collectionName"');
      } 
      // Fallback to generic collection key
      else if (context.sessionData['collection'] != null) {
        collectionName = context.sessionData['collection'].toString();
        print('✅ Found sessionData.collection = "$collectionName"');
      } else {
        print('❌ No collection found in direct sessionData keys');
      }
    }
    
    print('');
    print('🎯 FINAL RESULT:');
    print('   collectionName = "$collectionName"');
    print('   startTime = $startTime');
    print('   endTime = $endTime');
    print('═══════════════════════════════════════════════════════');
    print('');
    
    // Format dates in a user-friendly way
    String formatDate(DateTime? date) {
      if (date == null) return 'N/A';
      final monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      final month = monthNames[date.month - 1];
      final day = date.day;
      final year = date.year;
      final hour = date.hour.toString().padLeft(2, '0');
      final minute = date.minute.toString().padLeft(2, '0');
      return '$month $day, $year $hour:$minute';
    }
    
    // Get theme colors for dark mode compatibility
    final theme = Theme.of(this.context);
    final backgroundColor = const Color(0xFF0F0F14); // Match app dark surface
    final borderColor = theme.colorScheme.outline.withOpacity(0.3);
    final iconColor = theme.colorScheme.primary;
    final textColor = theme.colorScheme.onSurface;
    final dividerColor = theme.colorScheme.outline.withOpacity(0.2);
    
    return Column(
      children: [
        // Camera search results banner (if applicable)
        if (isCameraSearch && _aggregatedAnalyses != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer.withOpacity(0.3),
              border: Border(
                bottom: BorderSide(
                  color: borderColor,
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.video_camera_front,
                  size: 20,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Camera Search Results',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${_aggregatedAnalyses!.length} of ${context.sessionData['total_group_members'] ?? '?'} members found in $collectionName',
                        style: TextStyle(
                          fontSize: 12,
                          color: textColor.withOpacity(0.8),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        
        // Standard info bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: backgroundColor,
            border: Border(
              bottom: BorderSide(
                color: borderColor,
                width: 1,
              ),
            ),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              // Determine if we should wrap to multiple lines on very small screens
              final isVerySmall = constraints.maxWidth < 500;
              
              if (isVerySmall) {
                // Stack vertically on very small screens
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.calendar_today, size: 16, color: iconColor),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'From: ${formatDate(startTime)}',
                            style: TextStyle(
                              fontSize: 13,
                              color: textColor,
                              fontWeight: FontWeight.w500,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.event, size: 16, color: iconColor),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'To: ${formatDate(endTime)}',
                            style: TextStyle(
                              fontSize: 13,
                              color: textColor,
                              fontWeight: FontWeight.w500,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.video_collection, size: 16, color: iconColor),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'Collection: $collectionName',
                            style: TextStyle(
                              fontSize: 13,
                              color: textColor,
                              fontWeight: FontWeight.w600,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ],
                );
              } else {
                // Single row on larger screens
                return Wrap(
                  spacing: 20,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.calendar_today, size: 16, color: iconColor),
                        const SizedBox(width: 6),
                        Text(
                          'From: ${formatDate(startTime)}',
                          style: TextStyle(
                            fontSize: 13,
                            color: textColor,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    Container(
                      width: 1,
                      height: 16,
                      color: dividerColor,
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.event, size: 16, color: iconColor),
                        const SizedBox(width: 6),
                        Text(
                          'To: ${formatDate(endTime)}',
                          style: TextStyle(
                            fontSize: 13,
                            color: textColor,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    Container(
                      width: 1,
                      height: 16,
                      color: dividerColor,
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.video_collection, size: 16, color: iconColor),
                        const SizedBox(width: 6),
                        Text(
                          'Collection: $collectionName',
                          style: TextStyle(
                            fontSize: 13,
                            color: textColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                );
              }
            },
          ),
        ),
      ],
    );
  }

  Widget _buildOverviewTab() {
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem!.uuid));
    final workflowState = ref.watch(personObjectsWorkflowControllerProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status Section
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.info_outline, color: Colors.blue),
                      const SizedBox(width: 8),
                      Text(
                        'Analysis Status',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Spacer(),
                      Chip(
                        label: Text('Status: ${workflowState.name}'),
                        backgroundColor: workflowState == PersonObjectsWorkflowState.completed 
                            ? Colors.green.shade100 
                            : Colors.orange.shade100,
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                                            _buildStatusDetails(AsyncValue.data(workflowState)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Statistics Section
          dataAsync.when(
            data: (data) => data != null ? _buildStatisticsSection(data) : const SizedBox.shrink(),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Icon(Icons.error, color: Colors.red, size: 48),
                    const SizedBox(height: 8),
                    Text('Failed to load data: $error'),
                  ],
                ),
              ),
            ),
          ),

          // Quick Actions
          const SizedBox(height: 16),
          _buildQuickActionsSection(),
        ],
      ),
    );
  }

  Widget _buildPersonGroupsTab() {
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem!.uuid));

    return dataAsync.when(
      data: (data) {
        if (data == null) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.groups_outlined, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No person groups available'),
                Text('Run person objects analysis first'),
              ],
            ),
          );
        }

        // Extract person groups from API response
        final personGroups = _extractPersonGroupsFromApiData(data);

        if (personGroups.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.person_off, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No person groups found'),
                Text('The analysis did not identify any person groups'),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: const EdgeInsets.all(16.0),
          itemCount: personGroups.length,
          itemBuilder: (context, index) {
            final group = personGroups[index];
            return _buildPersonGroupCard(group, index);
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, color: Colors.red, size: 48),
            const SizedBox(height: 16),
            Text('Failed to load person groups: $error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _refreshAnalysis(),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  /// Extract person groups from API response data
  List<Map<String, dynamic>> _extractPersonGroupsFromApiData(PersonObjectsData data) {
    // Mock data structure based on what the API should return
    // In the future, this will come directly from data.personGroups when the API is enhanced
    
    if (data.totalPersons == 0) return [];
    
    // Create mock person groups based on the classified faces
    final groups = <Map<String, dynamic>>[];
    
    if (data.classifiedFaces.isNotEmpty) {
      // Group faces by person ID
      final Map<String, List<ClassifiedFace>> facesByPerson = {};
      for (final face in data.classifiedFaces) {
        facesByPerson.putIfAbsent(face.personId, () => []).add(face);
      }
      
      // Create person group data for each person
      facesByPerson.forEach((personId, faces) {
        // Find the face with the largest bounding box area for this person
        BestQualityFace? largestFaceData;
        double maxArea = 0;
        
        if (data.bestQualityFaces.isNotEmpty) {
          for (final faceData in data.bestQualityFaces.values) {
            final bbox = faceData.bbox;
            if (bbox.length >= 4) {
              final width = (bbox[2] - bbox[0]).toDouble();
              final height = (bbox[3] - bbox[1]).toDouble();
              final area = width * height;
              
              if (area > maxArea) {
                maxArea = area;
                largestFaceData = faceData;
              }
            }
          }
        }
        
        print('DEBUG: Selected largest face with area: $maxArea from ${data.bestQualityFaces.length} faces');
        
        final group = {
          'person_uuid': 'uuid_$personId',
          'person_id': personId,
          'face_count': faces.length,
          'representative_faces': faces.map((face) {
            // Use the largest face data for consistent cropping
            final bboxData = largestFaceData?.bbox ?? [
              face.positionX.toInt() - 50, 
              face.positionY.toInt() - 50, 
              face.positionX.toInt() + 50, 
              face.positionY.toInt() + 50
            ];
            print('DEBUG: Using largest bbox for face: $bboxData');
            
            return {
              'face_data': {
                'bbox': bboxData,
                'confidence': largestFaceData?.qualityScore ?? 0.5,
                'frame_number': face.frameNumber,
                'timestamp': face.frameNumber * 0.033, // Approximate timestamp
                'distance_from_camera': (face.matchDistance * 10).clamp(15.0, 50.0), // Convert quality to distance
                'center_x': face.positionX,
                'center_y': face.positionY,
                'face_width': largestFaceData?.bbox != null ? (largestFaceData!.bbox[2] - largestFaceData.bbox[0]).abs() : 100,
                'face_height': largestFaceData?.bbox != null ? (largestFaceData!.bbox[3] - largestFaceData.bbox[1]).abs() : 100,
                'face_area': largestFaceData?.bbox != null ? 
                  ((largestFaceData!.bbox[2] - largestFaceData.bbox[0]) * (largestFaceData.bbox[3] - largestFaceData.bbox[1])).abs() : 10000,
              },
              'quality_score': face.matchDistance,
              'selection_rank': faces.indexOf(face) + 1,
            };
          }).toList(),
          'spatial_bounds': {
            'min_x': faces.map((f) => f.positionX).reduce((a, b) => a < b ? a : b) - 50,
            'max_x': faces.map((f) => f.positionX).reduce((a, b) => a > b ? a : b) + 50,
            'min_y': faces.map((f) => f.positionY).reduce((a, b) => a < b ? a : b) - 50,
            'max_y': faces.map((f) => f.positionY).reduce((a, b) => a > b ? a : b) + 50,
            'width': 100.0,
            'height': 100.0,
          },
          'temporal_span': {
            'start_frame': faces.map((f) => f.frameNumber).reduce((a, b) => a < b ? a : b),
            'end_frame': faces.map((f) => f.frameNumber).reduce((a, b) => a > b ? a : b),
            'duration_seconds': (faces.map((f) => f.frameNumber).reduce((a, b) => a > b ? a : b) - 
                                faces.map((f) => f.frameNumber).reduce((a, b) => a < b ? a : b)) * 0.033,
            'frame_count': faces.length,
          },
          'movement_tracking': {
            'route_points': faces.map((face) => {
              'sequence_number': faces.indexOf(face) + 1,
              'frame_number': face.frameNumber,
              'timestamp': face.frameNumber * 0.033,
              'center_x': face.positionX,
              'center_y': face.positionY,
              'distance_from_camera': face.matchDistance * 10,
              'velocity_x': 0.0,
              'velocity_y': 0.0,
              'velocity_magnitude': 0.0,
            }).toList(),
            'movement_statistics': {
              'total_route_points': faces.length,
              'total_distance_pixels': 100.0,
              'average_velocity': 25.0,
              'max_velocity': 50.0,
              'time_in_frame_seconds': faces.length * 0.033,
            },
          },
          'quality_metrics': {
            'average_quality': faces.map((f) => f.matchDistance).reduce((a, b) => a + b) / faces.length,
            'max_quality': faces.map((f) => f.matchDistance).reduce((a, b) => a > b ? a : b),
            'min_quality': faces.map((f) => f.matchDistance).reduce((a, b) => a < b ? a : b),
            'quality_variance': 2.0,
          },
        };
        groups.add(group);
      });
    } else {
      // Fallback: Create a single person group based on total persons/faces
      groups.add({
        'person_uuid': 'uuid_person_1',
        'person_id': 'person_1',
        'face_count': data.originalGroups,
        'representative_faces': [],
        'spatial_bounds': {
          'min_x': 100.0,
          'max_x': 500.0,
          'min_y': 100.0,
          'max_y': 400.0,
          'width': 400.0,
          'height': 300.0,
        },
        'temporal_span': {
          'start_frame': 0,
          'end_frame': 100,
          'duration_seconds': 3.33,
          'frame_count': data.originalGroups,
        },
        'movement_tracking': {
          'route_points': [],
          'movement_statistics': {
            'total_route_points': 0,
            'total_distance_pixels': 0.0,
            'average_velocity': 0.0,
            'max_velocity': 0.0,
            'time_in_frame_seconds': 0.0,
          },
        },
        'quality_metrics': {
          'average_quality': 25.0,
          'max_quality': 30.0,
          'min_quality': 20.0,
          'quality_variance': 2.0,
        },
      });
    }
    
    return groups;
  }

  /// Build a detailed person group card
  Widget _buildPersonGroupCard(Map<String, dynamic> group, int index) {
    final personId = group['person_id'] as String;
    final faceCount = group['face_count'] as int;
    final representativeFaces = group['representative_faces'] as List<dynamic>;
    final spatialBounds = group['spatial_bounds'] as Map<String, dynamic>;
    final temporalSpan = group['temporal_span'] as Map<String, dynamic>;
    final movementStats = group['movement_tracking']['movement_statistics'] as Map<String, dynamic>;
    final qualityMetrics = group['quality_metrics'] as Map<String, dynamic>;

    // Get the best representative face for the cropped bounding box
    final bestFace = representativeFaces.isNotEmpty ? representativeFaces[0] : null;

    return Card(
      margin: const EdgeInsets.only(bottom: 16.0),
      elevation: 4,
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 24.0),  // Increased vertical padding for larger thumbnail
        leading: CircleAvatar(
          backgroundColor: _getPersonGroupColor(qualityMetrics['average_quality'] as double),
          child: Text(
            '${index + 1}',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        title: Text(
          personId,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text('UUID: ${group['person_uuid']}'),
            const SizedBox(height: 2),
            Row(
              children: [
                Icon(Icons.face, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text('$faceCount faces'),
                const SizedBox(width: 16),
                Icon(Icons.timer, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text('${(temporalSpan['duration_seconds'] as double).toStringAsFixed(1)}s'),
              ],
            ),
          ],
        ),
        // Add cropped bounding box on the right side
        trailing: bestFace != null 
            ? _buildCroppedFaceImage(bestFace)
            : const Icon(Icons.face),
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Representative Faces Section
                _buildRepresentativeFacesSection(representativeFaces),
                
                const SizedBox(height: 16),
                
                // Frame Image Section (moved up after representative faces)
                if (bestFace != null) _buildFrameImageSection(bestFace),
                
                const SizedBox(height: 16),
                
                // Action Buttons
                _buildPersonGroupActions(group),
                
                const SizedBox(height: 16),
                
                // Statistics Grid (moved to bottom)
                _buildPersonGroupStatistics(spatialBounds, temporalSpan, movementStats, qualityMetrics),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build representative faces section
  Widget _buildRepresentativeFacesSection(List<dynamic> representativeFaces) {
    if (representativeFaces.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '🏆 Representative Faces',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline, color: Colors.grey),
                SizedBox(width: 8),
                Text(
                  'No representative faces available',
                  style: TextStyle(color: Colors.grey),
                ),
              ],
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '🏆 Representative Faces (${representativeFaces.length})',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 80,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: representativeFaces.length,
            itemBuilder: (context, index) {
              final face = representativeFaces[index];
              final qualityScore = face['quality_score'] as double;
              final rank = face['selection_rank'] as int;
              
              return Container(
                width: 80,
                margin: const EdgeInsets.only(right: 8),
                child: Column(
                  children: [
                    Container(
                      width: 60,
                      height: 60,
                      decoration: BoxDecoration(
                        color: _getQualityColor(qualityScore),
                        borderRadius: BorderRadius.circular(30),
                        border: Border.all(
                          color: rank == 1 ? Colors.amber : Colors.grey,
                          width: rank == 1 ? 3 : 1,
                        ),
                      ),
                      child: Stack(
                        children: [
                          const Center(
                            child: Icon(
                              Icons.face,
                              color: Colors.white,
                              size: 24,
                            ),
                          ),
                          if (rank == 1)
                            const Positioned(
                              top: 2,
                              right: 2,
                              child: Icon(
                                Icons.star,
                                color: Colors.amber,
                                size: 16,
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Rank #$rank',
                      style: const TextStyle(fontSize: 10),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  /// Build person group statistics grid
  Widget _buildPersonGroupStatistics(
    Map<String, dynamic> spatialBounds,
    Map<String, dynamic> temporalSpan,
    Map<String, dynamic> movementStats,
    Map<String, dynamic> qualityMetrics,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '📊 Group Statistics',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 2.5,
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          children: [
            _buildStatCard(
              'Movement Area',
              '${(spatialBounds['width'] as double).toStringAsFixed(0)} × ${(spatialBounds['height'] as double).toStringAsFixed(0)} px',
              Icons.crop_free,
              Colors.blue,
            ),
            _buildStatCard(
              'Duration',
              '${(temporalSpan['duration_seconds'] as double).toStringAsFixed(1)}s',
              Icons.timer,
              Colors.green,
            ),
            _buildStatCard(
              'Route Points',
              '${movementStats['total_route_points']}',
              Icons.timeline,
              Colors.orange,
            ),
            _buildStatCard(
              'Avg Quality',
              (qualityMetrics['average_quality'] as double).toStringAsFixed(1),
              Icons.star,
              Colors.purple,
            ),
          ],
        ),
      ],
    );
  }

  /// Build action buttons for person group
  Widget _buildPersonGroupActions(Map<String, dynamic> group) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '⚡ Actions',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            ElevatedButton.icon(
              onPressed: () => _showPersonGroupDetails(group),
              icon: const Icon(Icons.visibility, size: 16),
              label: const Text('View Details'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
            OutlinedButton.icon(
              onPressed: () => _exportPersonGroupData(group),
              icon: const Icon(Icons.download, size: 16),
              label: const Text('Export'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Build individual stat card
  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 12,
              color: color,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  /// Get color for person group based on quality
  Color _getPersonGroupColor(double avgQuality) {
    if (avgQuality >= 28) return Colors.green;
    if (avgQuality >= 25) return Colors.orange;
    return Colors.red;
  }

  /// Get color for quality score
  Color _getQualityColor(double qualityScore) {
    if (qualityScore >= 28) return Colors.green;
    if (qualityScore >= 25) return Colors.orange;
    return Colors.red;
  }

  /// Show detailed person group information
  void _showPersonGroupDetails(Map<String, dynamic> group) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${group['person_id']} Details'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('UUID: ${group['person_uuid']}'),
              const SizedBox(height: 8),
              Text('Face Count: ${group['face_count']}'),
              const SizedBox(height: 8),
              Text('Representative Faces: ${(group['representative_faces'] as List).length}'),
              const SizedBox(height: 8),
              const Text('Spatial Bounds:'),
              Text('  Width: ${group['spatial_bounds']['width']} px'),
              Text('  Height: ${group['spatial_bounds']['height']} px'),
              const SizedBox(height: 8),
              const Text('Quality Metrics:'),
              Text('  Average: ${(group['quality_metrics']['average_quality'] as double).toStringAsFixed(2)}'),
              Text('  Max: ${(group['quality_metrics']['max_quality'] as double).toStringAsFixed(2)}'),
              Text('  Min: ${(group['quality_metrics']['min_quality'] as double).toStringAsFixed(2)}'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  /// Export person group data
  void _exportPersonGroupData(Map<String, dynamic> group) {
    // TODO: Implement export functionality
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Export functionality for ${group['person_id']} coming soon!'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Widget _buildFaceDetailsTab() {
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem!.uuid));

    return dataAsync.when(
      data: (data) {
        if (data == null) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.face, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No face details available'),
                Text('Run person objects analysis first'),
              ],
            ),
          );
        }

        final allFaces = data.classifiedFaces.toList()
          ..sort((a, b) => a.matchDistance.compareTo(b.matchDistance)); // Sort by match distance (lower is better)

        if (allFaces.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.face_retouching_off, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No faces found'),
                Text('The analysis did not detect any faces'),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: const EdgeInsets.all(16.0),
          itemCount: allFaces.length,
          itemBuilder: (context, index) {
            final face = allFaces[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 12.0),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: _getDistanceColor(face.matchDistance),
                  child: Icon(
                    Icons.face,
                    color: Colors.white,
                  ),
                ),
                title: Text('Face ${index + 1}'),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Face ID: ${face.faceDetectionId}'),
                    Text('Distance: ${face.matchDistance.toStringAsFixed(3)}'),
                    Text('Position: (${face.positionX.toStringAsFixed(1)}, ${face.positionY.toStringAsFixed(1)})'),
                  ],
                ),
                trailing: Icon(
                  face.matchDistance > 25.0 ? Icons.check_circle : Icons.warning, // Use quality score threshold
                  color: face.matchDistance > 25.0 ? Colors.green : Colors.orange,
                ),
                onTap: () => _showFaceDetailDialog(face),
              ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, color: Colors.red, size: 48),
            const SizedBox(height: 16),
            Text('Failed to load face details: $error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _refreshAnalysis(),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusDetails(AsyncValue<PersonObjectsWorkflowState> workflowState) {
    return workflowState.when(
      data: (state) {
        switch (state) {
          case PersonObjectsWorkflowState.idle:
            return const Text('Ready to start person objects analysis');
          case PersonObjectsWorkflowState.checking:
            return const Text('Checking for existing analysis...');
          case PersonObjectsWorkflowState.triggering:
            return const Text('Starting analysis...');
          case PersonObjectsWorkflowState.processing:
            return const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Analysis is currently running...'),
                SizedBox(height: 8),
                LinearProgressIndicator(),
              ],
            );
          case PersonObjectsWorkflowState.completed:
            return const Text('Analysis completed successfully');
          case PersonObjectsWorkflowState.failed:
            return const Text('Analysis failed - check logs for details');
        }
      },
      loading: () => const Text('Loading status...'),
      error: (_, __) => const Text('Failed to load status'),
    );
  }

  Widget _buildStatisticsSection(PersonObjectsData data) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics, color: Colors.green),
                const SizedBox(width: 8),
                Text(
                  'Analysis Statistics',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Person Objects Summary', 
                         style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text('Total Persons: ${data.totalPersons}'),
                    Text('Classified Faces: ${data.classifiedFaces.length}'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActionsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.flash_on, color: Colors.orange),
                const SizedBox(width: 8),
                Text(
                  'Quick Actions',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton.icon(
                  onPressed: () => _refreshAnalysis(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Refresh'),
                ),
                ElevatedButton.icon(
                  onPressed: () => _triggerNewAnalysis(),
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Re-run Analysis'),
                ),
                OutlinedButton.icon(
                  onPressed: () => _exportResults(),
                  icon: const Icon(Icons.download),
                  label: const Text('Export'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getDistanceColor(double distance) {
    if (distance < 0.3) return Colors.green;
    if (distance < 0.6) return Colors.orange;
    return Colors.red;
  }

  void _showFaceDetailDialog(ClassifiedFace face) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Face Details'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Face Detection ID: ${face.faceDetectionId}'),
            const SizedBox(height: 8),
            Text('Person ID: ${face.personId}'),
            const SizedBox(height: 8),
            Text('Match Distance: ${face.matchDistance.toStringAsFixed(3)}'),
            const SizedBox(height: 8),
            Text('Match Type: ${face.matchType}'),
            const SizedBox(height: 8),
            Text('Frame: ${face.frameNumber}'),
            const SizedBox(height: 8),
            Text('Position: (${face.positionX.toStringAsFixed(1)}, ${face.positionY.toStringAsFixed(1)})'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showEditNameDialog(AggregatedIndividualAnalysis analysis) {
    debugPrint('═══ EDIT DIALOG DEBUG ═══');
    debugPrint('Opening for ID: ${analysis.individualId}');
    debugPrint('Initial name: ${analysis.name}');
    debugPrint('Name is null: ${analysis.name == null}');
    debugPrint('═══════════════════════════');
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Individual'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Assign a name to this individual:',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            EditableMVRName(
              initialName: analysis.name,
              mvrPersonUuid: analysis.individualId,
              propagate: true,
              onNameUpdated: (newName) {
                debugPrint('═══ NAME UPDATE CALLBACK ═══');
                debugPrint('New name saved: $newName');
                debugPrint('Reloading cross-video data...');
                debugPrint('═══════════════════════════');
                // Reload cross-video data to refresh with new name
                _loadCrossVideoData();
              },
            ),
            const SizedBox(height: 24),
            const Text(
              'Set gender:',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            EditableMVRGender(
              initialGender: analysis.demographics?.gender,
              mvrPersonUuid: analysis.individualId,
              propagate: true,
              showIcon: true,
              onGenderUpdated: (newGender) {
                debugPrint('═══ GENDER UPDATE CALLBACK ═══');
                debugPrint('New gender saved: $newGender');
                debugPrint('Reloading cross-video data...');
                debugPrint('═══════════════════════════');
                // Reload cross-video data to refresh with new gender
                _loadCrossVideoData();
              },
            ),
            const SizedBox(height: 16),
            Text(
              'MVR ID: ${analysis.individualId}',
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _refreshAnalysis() {
    ref.invalidate(personObjectsDataProvider(widget.mediaItem!.uuid));
    ref.invalidate(personObjectsWorkflowControllerProvider);
  }

  void _triggerNewAnalysis() async {
    try {
      final controller = ref.read(personObjectsWorkflowControllerProvider.notifier);
      await controller.autoTriggerWorkflow(widget.mediaItem!.uuid);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Person objects analysis started'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start analysis: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Load cross-video analysis data from backend
  /// Uses the new session-less endpoint for MVR search results
  Future<void> _loadCrossVideoData() async {
    if (!_isCrossVideoMode || widget.crossVideoContext == null) return;
    
    setState(() {
      _isLoadingCrossVideoData = true;
      _crossVideoError = null;
      _routePointsByCamera.clear();
      _routePageIndexByCameraSource.clear();
      _routeHasMoreByCameraSource.clear();
      _routeTotalPointsByCameraSource.clear();
      _routeDisplayIndividualByCameraSource.clear();
      _routeCameraNamesById.clear();
      _routeDisplayPersonIdByUuid.clear();
      _loadedRouteSourceIndividuals.clear();
      _selectedRouteCameraId = null;
      _isLoadingMoreCrossVideoRoutes = false;
    });
    
    try {
      final context = widget.crossVideoContext!;
      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);
      
      final aggregatedAnalyses = <AggregatedIndividualAnalysis>[];
      
      final List<String> activeUuids = _overrideIndividualUuids ?? context.individualUuids;
      print('📊 Loading analysis for ${activeUuids.length} individuals');
      print('📊 Source: ${context.sessionData['source']}');

      // Check if this is a camera search from individual groups
      if (context.sessionData['source'] == 'individual_group_camera_search') {
        print('📹 Loading camera search results...');
        print('📹 DEBUG: Inside camera search branch, about to call _loadGroupCameraSearchData');
        final groupId = context.sessionData['group_id'] as String;
        final searchParams = context.sessionData['search_parameters'] as Map<String, dynamic>;
        await _loadGroupCameraSearchData(groupId, searchParams, aggregatedAnalyses);
        
        print('📹 DEBUG: _loadGroupCameraSearchData completed, aggregatedAnalyses.length = ${aggregatedAnalyses.length}');
        
        setState(() {
          _aggregatedAnalyses = aggregatedAnalyses;
          _isLoadingCrossVideoData = false;
        });
        
        print('📹 DEBUG: setState completed');
        
        // Load best images for camera search results
        print('🖼️ Camera search: aggregatedAnalyses.length = ${aggregatedAnalyses.length}');
        if (aggregatedAnalyses.isNotEmpty) {
          print('🖼️ Camera search: Calling _loadBestImagesForIndividuals()...');
          _loadBestImagesForIndividuals();
        } else {
          print('⚠️ Camera search: aggregatedAnalyses is EMPTY, not loading images');
        }
        
        print('📹 DEBUG: About to return from camera search branch');
        return;
      }

      // Extract date range from search parameters if available
      DateTime? startTime;
      DateTime? endTime;
      if (context.sessionData['search_parameters'] != null) {
        final searchParams = context.sessionData['search_parameters'] as Map<String, dynamic>;
        if (searchParams['start_time'] != null) {
          startTime = DateTime.parse(searchParams['start_time'] as String);
          print('📅 Filtering by start_time: $startTime');
        }
        if (searchParams['end_time'] != null) {
          endTime = DateTime.parse(searchParams['end_time'] as String);
          print('📅 Filtering by end_time: $endTime');
        }
      }

      // Check if hierarchical merge was applied
      final bool hierarchicalMergeApplied = 
          context.sessionData['hierarchical_merge_applied'] == true;

      // Check if we're loading MVR people or individuals
      // If search_results exists, we're loading MVR people (consolidated)
      final bool loadingMVRPeople = context.sessionData['search_results'] != null;

      if (loadingMVRPeople) {
        // Always fetch the full hierarchy for every MVR UUID from search results.
        // The hierarchy endpoint returns empty merged_mvr_people for truly standalone MVRs,
        // so this handles both auto-merged super-individuals AND winners of prior manual merges
        // without needing to track the hierarchicalMergeApplied flag per-search.
        print('📊 Loading MVR people via hierarchy endpoint');
        print('📊 Context has ${activeUuids.length} MVR UUIDs to load '
            '(hierarchicalMergeApplied=$hierarchicalMergeApplied)');
        
        // For each MVR UUID, fetch full hierarchy
        for (final superIndividualUuid in activeUuids) {
          try {
            // First, get the hierarchy to determine if this is a merged super-individual
            print('🔍 Fetching hierarchy for: $superIndividualUuid');
            final hierarchyResponse = await apiClient.get(
              '/api/v1/mvr-people/super-individual/$superIndividualUuid/hierarchy',
            );
            
            print('📡 Hierarchy response status: ${hierarchyResponse.statusCode}');
            
            if (hierarchyResponse.statusCode == 200) {
              final hierarchyData = hierarchyResponse.data as Map<String, dynamic>;
              final mergedMVRList = hierarchyData['merged_mvr_people'] as List;
              final allIndividualsList = hierarchyData['all_individuals'] as List;
              final isSuperIndividual = mergedMVRList.isNotEmpty;
              
              print('🔍 Super-individual $superIndividualUuid: '
                  '${isSuperIndividual ? "MERGED" : "STANDALONE"}');
              print('   MVR count: ${hierarchyData['mvr_count']}');
              print('   Total person objects: ${hierarchyData['total_person_objects']}');
              print('   All individuals count: ${allIndividualsList.length}');
              print('   Merged MVR people: ${mergedMVRList.length}');
              print('   Unique videos: ${hierarchyData['unique_videos']}');
              
              if (isSuperIndividual && mergedMVRList.isNotEmpty) {
                // For merged super-individuals, use the hierarchy data directly
                // DO NOT fetch each MVR separately - that would create 60 separate cards!
                print('✅ Creating aggregated analysis from hierarchy data...');
                
                final analysis = AggregatedIndividualAnalysis.fromSuperIndividual(
                  superIndividualUuid: superIndividualUuid,
                  hierarchyData: hierarchyData,
                  sessionUuid: context.sessionUuid,
                  startTime: startTime,
                  endTime: endTime,
                );
                
                aggregatedAnalyses.add(analysis);

                // Seed pagination state from page-1 response
                _pagedMergedChildren[superIndividualUuid] =
                    List.of(analysis.mergedMVRPeople);
                _hasMoreChildren[superIndividualUuid] =
                    analysis.mergedChildrenHasMore;
                _mergedChildrenNextPage[superIndividualUuid] =
                    analysis.mergedChildrenPage + 1;
                
                print('✅ Loaded super-individual with hierarchy:');
                print('   - ${analysis.totalAppearances} total appearances');
                print('   - ${analysis.uniqueVideos} unique videos');
                print('   - ${mergedMVRList.length} merged MVR people '
                    '(total=${analysis.mergedChildrenTotal}, '
                    'has_more=${analysis.mergedChildrenHasMore})');
              } else {
                // For standalone (not merged), use simple factory
                final analysis = AggregatedIndividualAnalysis.fromSuperIndividual(
                  superIndividualUuid: superIndividualUuid,
                  hierarchyData: hierarchyData,
                  sessionUuid: context.sessionUuid,
                  startTime: startTime,
                  endTime: endTime,
                );
                
                aggregatedAnalyses.add(analysis);
                print('✅ Loaded standalone super-individual: '
                    '${analysis.totalAppearances} appearances');
              }
            } else {
              print('⚠️ Hierarchy not found, falling back to direct MVR load');
              // Fallback to direct MVR loading
              await _loadSingleMVRPerson(
                superIndividualUuid,
                mediaApiClient,
                startTime,
                endTime,
                context.sessionUuid,
                aggregatedAnalyses,
              );
            }
          } catch (e) {
            print('❌ Error loading super-individual $superIndividualUuid: $e');
            // Fallback to direct MVR loading
            await _loadSingleMVRPerson(
              superIndividualUuid,
              mediaApiClient,
              startTime,
              endTime,
              context.sessionUuid,
              aggregatedAnalyses,
            );
          }
        }
      } else {
        print('📊 Loading individual data');
        // For each individual UUID, call the session-less endpoint
        for (final individualUuid in activeUuids) {
          try {
            final response = await mediaApiClient.getIndividualAnalysisNoSession(
              individualUuid: individualUuid,
              startTime: startTime,
              endTime: endTime,
            );
          
          if (response.success && response.data != null) {
            // Convert the response to AggregatedIndividualAnalysis
            final data = response.data!;
            
            print('📊 Individual analysis data for $individualUuid:');
            print('   Total appearances: ${data['total_appearances']}');
            print('   Unique videos: ${data['unique_videos']}');
            print('   Appearances count: ${(data['appearances'] as List).length}');
            
            // Log first appearance to check data structure
            if ((data['appearances'] as List).isNotEmpty) {
              final firstApp = (data['appearances'] as List).first;
              print('   First appearance structure: ${firstApp.keys.toList()}');
              print('   Has video_uuid: ${firstApp.containsKey('video_uuid')}');
              print('   Has media_uuid: ${firstApp.containsKey('media_uuid')}');
              print('   video_uuid value: ${firstApp['video_uuid']}');
              print('   media_uuid value: ${firstApp['media_uuid']}');
            }
            
            // Parse demographics if available
            Demographics? demographics;
            if (data['demographics'] != null) {
              final demoData = data['demographics'] as Map<String, dynamic>;
              demographics = Demographics(
                gender: demoData['gender'] as String?,
                genderConfidence: demoData['gender_confidence'] != null 
                    ? (demoData['gender_confidence'] as num).toDouble() 
                    : null,
                ageMin: demoData['age_min'] as int?,
                ageMax: demoData['age_max'] as int?,
                ageMean: demoData['age_mean'] != null 
                    ? (demoData['age_mean'] as num).toDouble() 
                    : null,
                ageConfidence: demoData['age_confidence'] != null 
                    ? (demoData['age_confidence'] as num).toDouble() 
                    : null,
              );
            }
            
            // Skip individuals with no appearances
            final totalAppearances = data['total_appearances'] as int;
            if (totalAppearances == 0) {
              print('⚠️ Skipping individual $individualUuid: 0 appearances (no data)');
              continue;
            }
            
            final analysis = AggregatedIndividualAnalysis(
              individualUuid: data['individual_uuid'] as String,
              individualId: data['mvr_people_uuid'] as String? ?? data['individual_uuid'] as String,  // Use MVR UUID if merged, fallback to individual UUID
              sessionUuid: context.sessionUuid, // Use context session for display
              totalAppearances: totalAppearances,
              uniqueVideos: data['unique_videos'] as int,
              firstSeen: data['first_seen'] != null 
                  ? DateTime.parse(data['first_seen'] as String)
                  : DateTime.now(),
              lastSeen: data['last_seen'] != null 
                  ? DateTime.parse(data['last_seen'] as String)
                  : DateTime.now(),
              totalDurationSeconds: 0.0, // Not provided by session-less endpoint
              averageConfidence: 0.0, // Calculate from appearances if needed
              appearances: (data['appearances'] as List)
                  .where((app) {
                    // Filter out appearances with missing or invalid video UUIDs
                    final videoUuid = app['video_uuid'] ?? app['media_uuid'];
                    if (videoUuid == null || videoUuid.toString().isEmpty) {
                      print('⚠️ Skipping appearance with missing video_uuid for ${data['individual_uuid']}');
                      return false;
                    }
                    return true;
                  })
                  .map((app) => IndividualAppearance(
                        individualUuid: data['individual_uuid'] as String,
                        videoUuid: (app['video_uuid'] ?? app['media_uuid']) as String,
                        personObjectUuid: app['person_object_uuid'] as String,
                        startTimestamp: DateTime.parse(app['start_timestamp'] as String),
                        endTimestamp: DateTime.parse(app['end_timestamp'] as String),
                        confidenceScore: (app['confidence'] as num).toDouble(),
                        entryBbox: null,
                        exitBbox: null,
                      ))
                  .toList(),
              personObjectUuids: (data['appearances'] as List)
                  .map((app) => app['person_object_uuid'] as String)
                  .toList(),
              analysisTimestamp: DateTime.now(),
              demographics: demographics,
            );

            aggregatedAnalyses.add(analysis);
            print('✅ Loaded analysis for individual $individualUuid: ${analysis.totalAppearances} appearances');
          } else {
            print('⚠️ Failed to load analysis for individual $individualUuid: ${response.error}');
          }
        } catch (e) {
          print('❌ Error loading analysis for individual $individualUuid: $e');
        }
        }
      }
      
      if (aggregatedAnalyses.isEmpty) {
        final errorMessage = loadingMVRPeople
            ? 'No MVR people with valid appearance data could be loaded.\n\n'
              'This may occur when:\n'
              '• MVR people were just created and appearance data is still processing\n'
              '• Media processing completed but no faces were detected\n'
              '• Face detection completed but no person objects were created'
            : 'No appearance data found for the selected individual(s).\n\n'
              'This occurs when:\n'
              '• The individual has not appeared in any processed videos yet\n'
              '• The individual was manually created without video associations\n'
              '• Face detection hasn\'t been run on videos containing this person\n\n'
              'To analyze an individual, they must first appear in processed video content.';
        
        setState(() {
          _crossVideoError = errorMessage;
          _isLoadingCrossVideoData = false;
        });
        return;
      }
      
      // Parse merge groups if the search applied a hierarchical merge
      final rawMergeGroups = context.sessionData['merge_groups'];
      final mergeGroups = <MergeGroupSummary>[];
      if (rawMergeGroups is List) {
        for (final g in rawMergeGroups) {
          if (g is Map<String, dynamic>) {
            mergeGroups.add(MergeGroupSummary.fromJson(g));
          }
        }
      }

      setState(() {
        _aggregatedAnalyses = aggregatedAnalyses;
        _hierarchicalMergeWasApplied = hierarchicalMergeApplied && mergeGroups.isNotEmpty;
        _mergeGroups = mergeGroups;
        _isLoadingCrossVideoData = false;
      });
      
      print('✅ Loaded cross-video data for ${aggregatedAnalyses.length} individuals');
      
      // Load best images for all individuals
      if (aggregatedAnalyses.isNotEmpty) {
        _loadBestImagesForIndividuals();
      }
      
    } catch (e) {
      setState(() {
        _crossVideoError = 'Failed to load cross-video data: $e';
        _isLoadingCrossVideoData = false;
      });
      print('❌ Error loading cross-video data: $e');
    }
  }

  /// Load the next page of merged children for a super-individual.
  ///
  /// Calls `GET /api/v1/mvr-people/super-individual/{uuid}/hierarchy` with
  /// `merged_page` incremented, then appends the new children to
  /// [_pagedMergedChildren] and updates the has-more / next-page flags.
  Future<void> _loadMoreMergedChildren(String superIndividualUuid) async {
    if (_loadingMoreChildren[superIndividualUuid] == true) return;
    if (_hasMoreChildren[superIndividualUuid] != true) return;

    final nextPage = _mergedChildrenNextPage[superIndividualUuid] ?? 2;

    setState(() {
      _loadingMoreChildren[superIndividualUuid] = true;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.get(
        '/api/v1/mvr-people/super-individual/$superIndividualUuid/hierarchy',
        queryParameters: {
          'merged_page': nextPage,
          'merged_page_size': _mergedChildrenPageSize,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final newItems = (data['merged_mvr_people'] as List?)
                ?.map((m) =>
                    MergedMVRPerson.fromJson(m as Map<String, dynamic>))
                .toList() ??
            [];
        final hasMore = (data['merged_children_has_more'] as bool?) ?? false;

        setState(() {
          _pagedMergedChildren[superIndividualUuid] = [
            ...(_pagedMergedChildren[superIndividualUuid] ?? []),
            ...newItems,
          ];
          _hasMoreChildren[superIndividualUuid] = hasMore;
          _mergedChildrenNextPage[superIndividualUuid] = nextPage + 1;
          _loadingMoreChildren[superIndividualUuid] = false;
        });

        // Fetch thumbnails for the newly loaded children
        if (newItems.isNotEmpty) {
          final mvrImageService = ref.read(mvrImageServiceProvider);
          final newUuids =
              newItems.map((m) => m.mvrPeopleUuid).toList();
          final childImages =
              await mvrImageService.getBestImagesForMergedChildren(newUuids);
          setState(() {
            _childMvrImages.addAll(childImages);
          });
        }
      } else {
        setState(() {
          _loadingMoreChildren[superIndividualUuid] = false;
        });
      }
    } catch (e) {
      print('❌ Error loading more merged children for $superIndividualUuid: $e');
      setState(() {
        _loadingMoreChildren[superIndividualUuid] = false;
      });
    }
  }

  /// Load best images for all individuals in cross-video analysis
  Future<void> _loadBestImagesForIndividuals() async {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) return;
    
    try {
      print('🖼️ Loading best images for ${_aggregatedAnalyses!.length} individuals in cross-video mode');
      final imageService = ref.read(mvrImageServiceProvider);
      final individualIds = _aggregatedAnalyses!.map((a) => a.individualId).toList();  // Use individualId (MVR UUID)
      print('🖼️ Individual IDs (MVR UUIDs): $individualIds');
      
      final images = await imageService.getBestImagesForMultiple(
        individualIds,
        includeMerged: false,
      );
      
      print('🖼️ Received ${images.length} image responses');
      for (var entry in images.entries) {
        print('🖼️   ${entry.key}: ${entry.value != null ? "✅ Has image" : "❌ No image"}');
        if (entry.value?.bestFace != null) {
          print('🖼️     imageUrl: ${entry.value!.bestFace!.imageUrl}');
          print('🖼️     has faceData: ${entry.value!.bestFace!.faceData != null}');
        }
      }
      
      if (mounted) {
        setState(() {
          _bestImages = images;
          print('🖼️ State updated with ${_bestImages.length} images');
        });
      }

      // Load thumbnails for child (merged-in) MVR cards
      final childUuids = _aggregatedAnalyses!
          .expand((a) => a.mergedMVRPeople.map((m) => m.mvrPeopleUuid))
          .toSet()
          .toList();
      if (childUuids.isNotEmpty) {
        print('🖼️ Loading best images for ${childUuids.length} child MVR cards');
        final childImages = await imageService.getBestImagesForMergedChildren(childUuids);
        if (mounted) {
          setState(() {
            _childMvrImages = childImages;
            print('🖼️ Loaded ${_childMvrImages.length} child MVR images');
          });
        }
      }
    } catch (e, stack) {
      print('❌ Error loading best images for cross-video analysis: $e');
      print('Stack: $stack');
    }
  }

  /// Helper method to load a single MVR person's data (v2.19.85)
  /// 
  /// This is used as a fallback when hierarchy loading fails or for
  /// non-merged MVR people.
  Future<void> _loadGroupCameraSearchData(
    String groupId,
    Map<String, dynamic> searchParameters,
    List<AggregatedIndividualAnalysis> aggregatedAnalyses,
  ) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final individualGroupsApiClient = IndividualGroupsApiClient(apiClient);
      
      // Support both single camera (camera_id) and multiple cameras (camera_ids)
      final cameraId = searchParameters['camera_id'] as String?;
      final cameraIds = searchParameters['camera_ids'] as List<dynamic>?;
      
      final cameras = cameraIds?.cast<String>() ?? 
                     (cameraId != null ? [cameraId] : null);
      
      if (cameras == null || cameras.isEmpty) {
        print('❌ No camera_id or camera_ids in search parameters');
        return;
      }
      
      final startTimeStr = searchParameters['start_time'] as String;
      final endTimeStr = searchParameters['end_time'] as String;
      final startTime = DateTime.parse(startTimeStr);
      final endTime = DateTime.parse(endTimeStr);
      final confidenceThreshold = searchParameters['confidence_threshold'] as double? ?? 0.5;

      print('📹 Loading camera search results: cameras=${cameras.join(", ")}, time=$startTime to $endTime, threshold=$confidenceThreshold');
      
      final response = await individualGroupsApiClient.searchGroupInCamera(
        groupId: groupId,
        cameraIds: cameras,
        startTime: startTime.toIso8601String(),
        endTime: endTime.toIso8601String(),
        confidenceThreshold: confidenceThreshold,
      );
      
      if (response.success && response.data != null) {
        final data = response.data!;
        final matchedIndividuals = data['matched_individuals'] as List<dynamic>;
        
        print('✅ Found ${matchedIndividuals.length} of ${data['total_group_members']} members across ${cameras.length} camera(s)');
        
        // Convert matched individuals to AggregatedIndividualAnalysis
        // For each matched individual, fetch hierarchy to get super-individual data if it exists
        for (var matched in matchedIndividuals) {
          final mvrPersonUuid = matched['mvr_person_uuid'] as String;
          
          try {
            // Fetch hierarchy to get super-individual data (name, gender, age)
            final apiClient = ref.read(apiClientProvider);
            final hierarchyResponse = await apiClient.get(
              '/api/v1/mvr-people/super-individual/$mvrPersonUuid/hierarchy',
            );
            
            if (hierarchyResponse.statusCode == 200 && hierarchyResponse.data != null) {
              final hierarchyData = hierarchyResponse.data as Map<String, dynamic>;
              final superIndividual = hierarchyData['super_individual'] as Map<String, dynamic>;
              
              // Extract demographics from super-individual
              Demographics? demographics;
              final hasAnyDemographics = superIndividual['gender'] != null || 
                                         superIndividual['age_min'] != null ||
                                         superIndividual['age_max'] != null;
              
              if (hasAnyDemographics) {
                demographics = Demographics(
                  gender: superIndividual['gender'] as String?,
                  genderConfidence: (superIndividual['gender_confidence'] as num?)?.toDouble(),
                  ageMin: superIndividual['age_min'] as int?,
                  ageMax: superIndividual['age_max'] as int?,
                  ageMean: superIndividual['age_mean'] != null 
                      ? (superIndividual['age_mean'] as num?)?.toDouble()
                      : (superIndividual['age_min'] != null && superIndividual['age_max'] != null)
                          ? ((superIndividual['age_min']! + superIndividual['age_max']!) / 2.0)
                          : null,
                  ageConfidence: (superIndividual['age_confidence'] as num?)?.toDouble(),
                );
              }
              
              // Get appearances array from backend (includes video_uuid for navigation)
              final appearancesData = matched['appearances'] as List<dynamic>?;
              
              List<IndividualAppearance> appearances;
              if (appearancesData != null && appearancesData.isNotEmpty) {
                // Use detailed appearances from backend
                appearances = appearancesData.map((app) => IndividualAppearance(
                  individualUuid: matched['individual_uuid'] as String,
                  videoUuid: app['video_uuid'] as String,
                  personObjectUuid: app['person_object_uuid'] as String,
                  startTimestamp: DateTime.parse(app['timestamp'] as String),
                  endTimestamp: DateTime.parse(app['timestamp'] as String),
                  confidenceScore: (app['confidence'] as num).toDouble(),
                )).toList();
              } else {
                // Fallback: create single synthetic appearance from summary
                appearances = [
                  IndividualAppearance(
                    individualUuid: matched['individual_uuid'] as String,
                    videoUuid: '', // Not available
                    personObjectUuid: mvrPersonUuid,
                    startTimestamp: DateTime.parse(matched['first_seen'] as String),
                    endTimestamp: DateTime.parse(matched['last_seen'] as String),
                    confidenceScore: (matched['confidence_score'] as num).toDouble(),
                  )
                ];
              }
              
              // Check if merged to determine super-individual status
              final mergedMVRList = hierarchyData['merged_mvr_people'] as List?;
              final isSuperIndividual = mergedMVRList != null && mergedMVRList.isNotEmpty;
              
              final analysis = AggregatedIndividualAnalysis(
                individualUuid: matched['individual_uuid'] as String,
                individualId: mvrPersonUuid, // Use MVR UUID as ID
                sessionUuid: groupId, // Use group ID as session
                totalAppearances: matched['total_appearances'] as int,
                uniqueVideos: appearancesData?.length ?? 1, // Count unique videos from appearances
                firstSeen: appearances.first.startTimestamp,
                lastSeen: appearances.last.endTimestamp,
                totalDurationSeconds: 0.0,
                averageConfidence: appearances.map((a) => a.confidenceScore).reduce((a, b) => a + b) / appearances.length,
                demographics: demographics, // Use super-individual demographics
                appearances: appearances,
                personObjectUuids: [matched['individual_uuid'] as String],
                analysisTimestamp: DateTime.now(),
                name: superIndividual['name'] as String?, // Use super-individual name
                nameUpdatedAt: superIndividual['name_updated_at'] != null
                    ? DateTime.parse(superIndividual['name_updated_at'] as String)
                    : null,
                nameUpdatedBy: superIndividual['name_updated_by'] as String?,
                isSuperIndividual: isSuperIndividual,
                mergedMVRCount: (hierarchyData['mvr_count'] as int?) ?? 1,
              );
              
              aggregatedAnalyses.add(analysis);
              print('✅ Added individual with hierarchy data: name=${analysis.name}, gender=${demographics?.gender}');
            } else {
              print('⚠️ No hierarchy data for $mvrPersonUuid, using basic data');
              // Fallback to basic data without demographics
              final appearancesData = matched['appearances'] as List<dynamic>?;
              
              List<IndividualAppearance> appearances;
              if (appearancesData != null && appearancesData.isNotEmpty) {
                appearances = appearancesData.map((app) => IndividualAppearance(
                  individualUuid: matched['individual_uuid'] as String,
                  videoUuid: app['video_uuid'] as String,
                  personObjectUuid: app['person_object_uuid'] as String,
                  startTimestamp: DateTime.parse(app['timestamp'] as String),
                  endTimestamp: DateTime.parse(app['timestamp'] as String),
                  confidenceScore: (app['confidence'] as num).toDouble(),
                )).toList();
              } else {
                appearances = [
                  IndividualAppearance(
                    individualUuid: matched['individual_uuid'] as String,
                    videoUuid: '',
                    personObjectUuid: mvrPersonUuid,
                    startTimestamp: DateTime.parse(matched['first_seen'] as String),
                    endTimestamp: DateTime.parse(matched['last_seen'] as String),
                    confidenceScore: (matched['confidence_score'] as num).toDouble(),
                  )
                ];
              }
              
              final analysis = AggregatedIndividualAnalysis(
                individualUuid: matched['individual_uuid'] as String,
                individualId: mvrPersonUuid,
                sessionUuid: groupId,
                totalAppearances: matched['total_appearances'] as int,
                uniqueVideos: appearancesData?.length ?? 1,
                firstSeen: appearances.first.startTimestamp,
                lastSeen: appearances.last.endTimestamp,
                totalDurationSeconds: 0.0,
                averageConfidence: appearances.map((a) => a.confidenceScore).reduce((a, b) => a + b) / appearances.length,
                appearances: appearances,
                personObjectUuids: [matched['individual_uuid'] as String],
                analysisTimestamp: DateTime.now(),
              );
              
              aggregatedAnalyses.add(analysis);
            }
          } catch (e, stackTrace) {
            print('❌ Error fetching hierarchy for $mvrPersonUuid: $e');
            print('Stack trace: $stackTrace');
            // Continue with next individual
          }
        }
        
        print('📊 Added ${aggregatedAnalyses.length} individuals to cross-video analysis');
      } else {
        print('❌ Camera search failed: ${response.error}');
      }
    } catch (e, stackTrace) {
      print('❌ Error loading camera search data: $e');
      print('Stack trace: $stackTrace');
    }
  }

  Future<void> _loadSingleMVRPerson(
    String mvrPersonUuid,
    MediaApiClient mediaApiClient,
    DateTime? startTime,
    DateTime? endTime,
    String sessionUuid,
    List<AggregatedIndividualAnalysis> aggregatedAnalyses,
  ) async {
    try {
      final response = await mediaApiClient.getMVRPersonAnalysis(
        mvrPersonUuid: mvrPersonUuid,
        startTime: startTime,
        endTime: endTime,
      );
      
      if (response.success && response.data != null) {
        // Convert the response to AggregatedIndividualAnalysis
        final data = response.data!;
        
        // Parse demographics if available
        Demographics? demographics;
        if (data['demographics'] != null) {
          final demoData = data['demographics'] as Map<String, dynamic>;
          demographics = Demographics(
            gender: demoData['gender'] as String?,
            genderConfidence: demoData['gender_confidence'] != null 
                ? (demoData['gender_confidence'] as num).toDouble() 
                : null,
            ageMin: demoData['age_min'] as int?,
            ageMax: demoData['age_max'] as int?,
            ageMean: demoData['age_mean'] != null 
                ? (demoData['age_mean'] as num).toDouble() 
                : null,
            ageConfidence: demoData['age_confidence'] != null 
                ? (demoData['age_confidence'] as num).toDouble() 
                : null,
          );
        }
        
        // Skip MVR people with no appearances
        final totalAppearances = data['total_appearances'] as int;
        if (totalAppearances == 0) {
          print('⚠️ Skipping MVR person $mvrPersonUuid: 0 appearances (no data)');
          return;
        }
        
        final analysis = AggregatedIndividualAnalysis(
          individualUuid: data['mvr_person_uuid'] as String,
          individualId: data['mvr_person_uuid'] as String,
          sessionUuid: sessionUuid,
          totalAppearances: totalAppearances,
          uniqueVideos: data['unique_videos'] as int,
          firstSeen: data['first_seen'] != null 
              ? DateTime.parse(data['first_seen'] as String)
              : DateTime.now(),
          lastSeen: data['last_seen'] != null 
              ? DateTime.parse(data['last_seen'] as String)
              : DateTime.now(),
          totalDurationSeconds: 0.0,
          averageConfidence: 0.0,
          averageRouteVelocity: (data['average_route_velocity'] as num?)?.toDouble(),
          appearances: (data['appearances'] as List)
              .map((app) => IndividualAppearance(
                    individualUuid: app['individual_uuid'] as String,
                    videoUuid: app['video_uuid'] as String,
                    personObjectUuid: app['person_object_uuid'] as String,
                    startTimestamp: DateTime.parse(app['start_timestamp'] as String),
                    endTimestamp: DateTime.parse(app['end_timestamp'] as String),
                    confidenceScore: (app['confidence'] as num).toDouble(),
                    entryBbox: null,
                    exitBbox: null,
                  ))
              .toList(),
          personObjectUuids: (data['appearances'] as List)
              .map((app) => app['person_object_uuid'] as String)
              .toList(),
          analysisTimestamp: DateTime.now(),
          demographics: demographics,
        );

        aggregatedAnalyses.add(analysis);
        print('✅ Loaded MVR person $mvrPersonUuid: ${analysis.totalAppearances} appearances');
      } else {
        print('⚠️ Failed to load MVR person $mvrPersonUuid: ${response.error}');
      }
    } catch (e) {
      print('❌ Error loading MVR person $mvrPersonUuid: $e');
    }
  }

  /// Show actions dialog with available operations for selected individuals
  Future<void> _showActionsDialog() async {
    final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
    final mergeRule = generalSettings?.mergeIndividualsRule ?? 'semi';
    final bool canMerge = _selectedIndividuals.length >= 2;
    final bool mergeDisabledByRule = mergeRule == 'none';
    
    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Actions (${_selectedIndividuals.length} selected)'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Add to Group button
            ElevatedButton.icon(
              onPressed: () {
                Navigator.of(context).pop();
                _showAddToGroupDialog();
              },
              icon: const Icon(Icons.group_add),
              label: const Text('Add to Group'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
            
            const SizedBox(height: 12),
            
            // Merge Individuals button (only if 2+ selected)
            if (canMerge && !mergeDisabledByRule)
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.of(context).pop();
                  _showMergeConfirmationDialog();
                },
                icon: const Icon(Icons.merge),
                label: Text('Merge ${_selectedIndividuals.length} Individuals'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            
            if (canMerge && mergeDisabledByRule)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  'Merge is disabled by settings (Merge Individuals Rules = No automatic merging).',
                  style: TextStyle(
                    color: Colors.grey,
                    fontSize: 12,
                    fontStyle: FontStyle.italic,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),

            if (!canMerge)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  'Select 2 or more individuals to merge',
                  style: TextStyle(
                    color: Colors.grey,
                    fontSize: 12,
                    fontStyle: FontStyle.italic,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  /// Show dialog for adding selected individuals to a group
  Future<void> _showAddToGroupDialog() async {
    // If only one individual selected, show the AddToGroupDialog directly
    if (_selectedIndividuals.length == 1) {
      final result = await showDialog<bool>(
        context: context,
        builder: (context) => AddToGroupDialog(
          individualId: _selectedIndividuals.first,
          individualName: 'Individual',
        ),
      );
      
      if (result == true && mounted) {
        // Clear selection after successful add
        setState(() {
          _selectedIndividuals.clear();
        });
      }
    } else {
      // Multiple individuals selected - show dialog to handle bulk add
      await showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('Add ${_selectedIndividuals.length} Individuals to Group'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Note: Bulk adding multiple individuals to groups is not yet supported.',
                style: TextStyle(
                  color: Colors.orange,
                  fontStyle: FontStyle.italic,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Please select one individual at a time to add to a group.',
              ),
              const SizedBox(height: 16),
              Text(
                'Currently selected: ${_selectedIndividuals.length} individuals',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
    
    // Clear selection after action
    setState(() {
      _selectedIndividuals.clear();
    });
  }

  /// Show confirmation dialog for merging individuals
  Future<void> _showMergeConfirmationDialog() async {
    final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
    final mergeRule = generalSettings?.mergeIndividualsRule ?? 'semi';
    if (mergeRule == 'none') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Merge is disabled in Settings. Change Merge Individuals Rules to continue.'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    if (_selectedIndividuals.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select at least 2 individuals to merge'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }
    
    // Local state for the slider in the dialog
    double dialogThreshold = _similarityThreshold;
    
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Merge Individuals'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Are you sure you want to merge ${_selectedIndividuals.length} individuals?'),
                const SizedBox(height: 16),
                const Text(
                  'The system will validate face similarity before merging. '
                  'Individuals with similar facial embeddings will be combined into one.',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Similarity Threshold:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: Slider(
                        value: dialogThreshold,
                        min: 0.3,
                        max: 0.95,
                        divisions: 13,
                        label: '${(dialogThreshold * 100).toStringAsFixed(0)}%',
                        onChanged: (value) {
                          setState(() {
                            dialogThreshold = value;
                          });
                        },
                      ),
                    ),
                    SizedBox(
                      width: 60,
                      child: Text(
                        '${(dialogThreshold * 100).toStringAsFixed(0)}%',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  dialogThreshold < 0.5
                      ? 'Very permissive - may merge different people'
                      : dialogThreshold < 0.7
                          ? 'Moderate - good for varied angles/lighting'
                          : 'Strict - only very similar faces',
                  style: TextStyle(
                    fontSize: 11,
                    color: dialogThreshold < 0.5 ? Colors.orange : Colors.grey,
                    fontStyle: FontStyle.italic,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Selected individuals:\n${_selectedIndividuals.map((uuid) => '• ${uuid.substring(0, 8)}...').join('\n')}',
                  style: const TextStyle(fontSize: 12),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                // Update the threshold before closing
                this.setState(() {
                  _similarityThreshold = dialogThreshold;
                });
                Navigator.of(context).pop(true);
              },
              child: const Text('Merge'),
            ),
          ],
        ),
      ),
    );
    
    if (confirmed == true) {
      await _executeMerge();
    }
  }

  /// Execute the merge operation
  Future<void> _executeMerge() async {
    if (_selectedIndividuals.isEmpty || widget.crossVideoContext == null) return;
    
    // Use MVR-People merge whenever the search returned MVR UUIDs (search_results present)
    // — this covers both hierarchical merges and plain MVR searches.
    // Only fall back to the legacy individuals/tracking/merge endpoint when the screen
    // was loaded with raw individual UUIDs (no search_results key in sessionData).
    final bool useMvrMerge =
        widget.crossVideoContext!.sessionData['search_results'] != null ||
        widget.crossVideoContext!.sessionData['hierarchical_merge_applied'] == true;
    
    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              'Merging individuals...',
              style: TextStyle(color: Colors.white),
            ),
          ],
        ),
      ),
    );
    
    try {
      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);
      
      // Use appropriate merge endpoint based on context
      final response = useMvrMerge
          ? await mediaApiClient.mergeMVRPeople(
              mvrUuids: _selectedIndividuals.toList(),
              similarityThreshold: _similarityThreshold,
            )
          : await mediaApiClient.mergeIndividuals(
              individualUuids: _selectedIndividuals.toList(),
              sessionUuid: widget.crossVideoContext!.sessionUuid,
              similarityThreshold: _similarityThreshold,
            );
      
      // Dismiss loading indicator
      if (mounted) Navigator.of(context).pop();
      
      if (response.success && response.data != null) {
        final data = response.data!;
        final predominantUuid = data['predominant_individual_uuid'] as String;
        final mergedCount = (data['merged_individual_uuids'] as List).length;
        final similarityScore = data['similarity_score'] as double?;
        
        // Show success message
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Successfully merged $mergedCount individuals\n'
                'Similarity: ${similarityScore != null ? (similarityScore * 100).toStringAsFixed(1) : "N/A"}%',
              ),
              backgroundColor: Colors.green,
              duration: const Duration(seconds: 4),
            ),
          );
        }
        
        // Update the active UUID list to the winner so the immediate
        // reload shows the merged state rather than stale pre-merge UUIDs.
        setState(() {
          _selectedIndividuals.clear();
          if (useMvrMerge) {
            _overrideIndividualUuids = [predominantUuid];
          }
        });
        await _loadCrossVideoData();
        
      } else {
        // Show error message
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Merge failed: ${response.error ?? "Unknown error"}'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      // Dismiss loading indicator
      if (mounted) Navigator.of(context).pop();
      
      // Show error message
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Merge error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
      print('❌ Error merging individuals: $e');
    }
  }

  void _exportResults() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Export functionality coming soon'),
        backgroundColor: Colors.blue,
      ),
    );
  }

  /// Build cropped face image for the trailing widget
  Widget _buildCroppedFaceImage(Map<String, dynamic> faceData) {
    return SizedBox(
      width: 90,   // Fixed width to ensure it renders
      height: 120, // Fixed height to match the increased row height
      child: Container(
        decoration: BoxDecoration(
          // Removed red debug border
        ),
        child: FutureBuilder<Widget>(
          future: _buildCroppedFaceImageAsync(faceData['face_data']),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Container(
                color: Colors.grey[300],
                child: Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              );
            } else if (snapshot.hasError) {
              return Container(
                color: Colors.grey[300],
                child: Icon(Icons.error, size: 24, color: Colors.red),
              );
            } else {
              return snapshot.data ?? Container(
                color: Colors.grey[300],
                child: Icon(Icons.face, size: 24, color: Colors.grey[600]),
              );
            }
          },
        ),
      ),
    );
  }

  /// Build cropped face image asynchronously
  Future<Widget> _buildCroppedFaceImageAsync(Map<String, dynamic> faceData) async {
    try {
      final frameNumber = faceData['frame_number'] ?? 0;
      final bbox = faceData['bbox'] as List<dynamic>?;
      
      // Create unique cache key to avoid repeated calculations
      final cacheKey = 'frame_${frameNumber}_bbox_${bbox?.join('_')}';
      
      // Only print debug info once per unique face
      final shouldDebug = !_debuggedFaces.contains(cacheKey);
      if (shouldDebug) {
        print('DEBUG CROPPING: frameNumber: $frameNumber, bbox: $bbox');
        _debuggedFaces.add(cacheKey);
      }
      
      // Check if bbox is available and valid
      if (bbox == null || bbox.length < 4) {
        if (shouldDebug) print('Warning: bbox is null or invalid, falling back to full frame image');
        // Fallback to showing the full frame image
        final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
        return _buildAuthenticatedFrameImageWidget(
          frameUrl,
          fit: BoxFit.cover,
        );
      }
      
      // Extract bounding box coordinates
      final x = bbox[0].toDouble();
      final y = bbox[1].toDouble();
      final x2 = bbox[2].toDouble();
      final y2 = bbox[3].toDouble();
      final width = x2 - x;
      final height = y2 - y;
      
      // Expand the crop area to get 250x250 from original 100x100
      final areaMultiplier = 6.25; // 250x250 = 62,500 px² vs 100x100 = 10,000 px²
      final scaleFactor = math.sqrt(areaMultiplier); // Scale factor for dimensions
      final expandedWidth = width * scaleFactor;
      final expandedHeight = height * scaleFactor;
      
      final widthExpansion = expandedWidth - width;
      final heightExpansion = expandedHeight - height;
      
      final expandedX = x - (widthExpansion / 2);
      final expandedY = y - (heightExpansion / 2);
      
      if (shouldDebug) {
        final originalArea = width * height;
        final expandedArea = expandedWidth * expandedHeight;
        final areaIncrease = ((expandedArea - originalArea) / originalArea * 100).toInt();
        final expandedX2 = expandedX + expandedWidth;
        final expandedY2 = expandedY + expandedHeight;
        print('DEBUG BBOX: Original=${width.toInt()}x${height.toInt()} (${originalArea.toInt()}px²) → Expanded=${expandedWidth.toInt()}x${expandedHeight.toInt()} (${expandedArea.toInt()}px², +${areaIncrease}% area)');
        print('DEBUG COORDS: Original=[${x.toInt()}, ${y.toInt()}, ${x2.toInt()}, ${y2.toInt()}] → Expanded=[${expandedX.toInt()}, ${expandedY.toInt()}, ${expandedX2.toInt()}, ${expandedY2.toInt()}]');
      }
      
      // Validate expanded bounding box dimensions
      if (expandedWidth <= 0 || expandedHeight <= 0) {
        print('Warning: Invalid expanded bbox dimensions (width: $expandedWidth, height: $expandedHeight), using fallback');
        final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
        return _buildAuthenticatedFrameImageWidget(
          frameUrl,
          fit: BoxFit.cover,
        );
      }
      
      // Get the full frame image first
      final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
      
      // For now, return the full frame and crop it in Flutter since backend doesn't support cropping
      // TODO: When backend supports crop parameters, use: frameUrl + '&crop=$x,$y,$width,$height'
      return FutureBuilder<ui.Image>(
        future: _loadNetworkImage(frameUrl),
        builder: (context, snapshot) {
          if (snapshot.hasData && snapshot.data != null) {
            return SizedBox(
              width: expandedWidth,
              height: expandedHeight,
              child: CustomPaint(
                painter: CroppedImagePainter(
                  image: snapshot.data!,
                  cropRect: Rect.fromLTWH(expandedX, expandedY, expandedWidth, expandedHeight),
                ),
                size: Size(expandedWidth, expandedHeight), // Use actual bbox dimensions
              ),
            );
          } else {
            return _buildAuthenticatedFrameImageWidget(
              frameUrl,
              fit: BoxFit.cover,
            );
          }
        },
      );
    } catch (e) {
      print('Exception in _buildCroppedFaceImageAsync: $e');
      return Container(
        color: Colors.grey[300],
        child: Icon(Icons.error, size: 24, color: Colors.red), // Larger icon for responsive container
      );
    }
  }

  /// Load network image and return ui.Image for cropping
  Future<ui.Image> _loadNetworkImage(String url) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      // Use Image.network to load the image with proper headers for web compatibility
      final ImageProvider imageProvider = NetworkImage(
        url,
        headers: apiClient.authToken != null ? {
          'Authorization': 'Bearer ${apiClient.authToken}',
        } : {},
      );
      
      final ImageStream stream = imageProvider.resolve(const ImageConfiguration());
      final Completer<ui.Image> completer = Completer<ui.Image>();
      
      late ImageStreamListener listener;
      listener = ImageStreamListener(
        (ImageInfo info, bool synchronousCall) {
          stream.removeListener(listener);
          completer.complete(info.image);
        },
        onError: (exception, stackTrace) {
          stream.removeListener(listener);
          completer.completeError(exception);
        },
      );
      
      stream.addListener(listener);
      return completer.future;
    } catch (e) {
      throw Exception('Failed to load image: $e');
    }
  }

  /// Build frame image widget using the frame extraction API
  Future<Widget> _buildFrameImage(int frameNumber) async {
    try {
      final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
      return _buildAuthenticatedFrameImageWidget(
        frameUrl,
        fit: BoxFit.contain,
      );
    } catch (e) {
      print('Exception in _buildFrameImage: $e');
      return const Center(
        child: Icon(Icons.error, color: Colors.grey),
      );
    }
  }

  /// Build frame image section to show the full frame
  Widget _buildFrameImageSection(Map<String, dynamic> face) {
    final faceData = face['face_data'] as Map<String, dynamic>;
    final frameNumber = faceData['frame_number'] as int;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '🖼️ Frame Image',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          constraints: const BoxConstraints(
            maxHeight: 400, // Half of standard smartphone height (~800px)
          ),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(8),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: FutureBuilder<Widget>(
              future: _buildFrameImage(frameNumber),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Container(
                    height: 200,
                    child: const Center(
                      child: CircularProgressIndicator(),
                    ),
                  );
                } else if (snapshot.hasError || !snapshot.hasData) {
                  return Container(
                    height: 200,
                    child: const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.error, color: Colors.grey, size: 32),
                          SizedBox(height: 8),
                          Text('Failed to load frame', style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    ),
                  );
                } else {
                  return snapshot.data!;
                }
              },
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Frame: $frameNumber',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
        
        // Add cropped face image section
        const SizedBox(height: 16),
        const Text(
          'Selected face',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        Container(
          width: 120,
          height: 160,
          decoration: BoxDecoration(
            // Removed red debug border
          ),
          child: FutureBuilder<Widget>(
            future: _buildCroppedFaceImageAsync(faceData),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return Container(
                  color: Colors.grey[200],
                  child: const Center(
                    child: CircularProgressIndicator(),
                  ),
                );
              } else if (snapshot.hasError || !snapshot.hasData) {
                return Container(
                  color: Colors.grey[200],
                  child: const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.face, color: Colors.grey, size: 32),
                        SizedBox(height: 4),
                        Text('Crop failed', style: TextStyle(color: Colors.grey, fontSize: 10)),
                      ],
                    ),
                  ),
                );
              } else {
                return snapshot.data!;
              }
            },
          ),
        ),
      ],
    );
  }

  /// Build cropped image from frame using the frame extraction API
  Future<Widget> _buildCroppedImageFromFrame(int frameNumber, double x, double y, double width, double height) async {
    try {
      // For now, return the full frame - cropping would require additional backend support
      // TODO: Implement actual cropping when backend supports crop parameters
      return await _buildFrameImage(frameNumber);
    } catch (e) {
      return const Icon(Icons.face, color: Colors.grey);
    }
  }

  Widget _buildRoutesTab() {
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem!.uuid));

    return dataAsync.when(
      data: (data) {
        if (data == null) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.route, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No route data available'),
                Text('Run person objects analysis first'),
              ],
            ),
          );
        }

        // Get person groups and routes data from the provider
        return FutureBuilder<Map<String, dynamic>?>(
          future: _fetchRoutesData(),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Loading routes data...'),
                  ],
                ),
              );
            }

            if (snapshot.hasError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error, size: 64, color: Colors.red),
                    const SizedBox(height: 16),
                    Text('Error loading routes: ${snapshot.error}'),
                  ],
                ),
              );
            }

            final routesData = snapshot.data;
            // Check for both 'group_tracking' (new API) and 'person_groups' (legacy)
            final personGroupsData = routesData?['group_tracking'] ?? routesData?['person_groups'];
            
            if (routesData == null || personGroupsData == null || (personGroupsData as List).isEmpty) {
              return const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.route_outlined, size: 64, color: Colors.grey),
                    SizedBox(height: 16),
                    Text('No movement routes found'),
                  ],
                ),
              );
            }

            final personGroups = personGroupsData as List<dynamic>;
            
            return SingleChildScrollView(
              child: Column(
                children: [
                  // Routes visualization header - make it more compact
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                      const Icon(Icons.route, color: Colors.blue),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Movement Routes Visualization',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            Text(
                              'Shows movement paths for ${personGroups.length} person(s)',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.grey[600],
                              ),
                            ),
                          ],
                        ),
                      ),
                      // Display mode toggle
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.grey.shade300),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.visibility, size: 16, color: Colors.grey),
                            const SizedBox(width: 4),
                            DropdownButton<String>(
                              value: _routesDisplayMode,
                              isDense: true,
                              underline: Container(),
                              items: const [
                                DropdownMenuItem(
                                  value: 'path',
                                  child: Row(
                                    children: [
                                      Icon(Icons.timeline, size: 16),
                                      SizedBox(width: 4),
                                      Text('Path'),
                                    ],
                                  ),
                                ),
                                DropdownMenuItem(
                                  value: 'scatter',
                                  child: Row(
                                    children: [
                                      Icon(Icons.scatter_plot, size: 16),
                                      SizedBox(width: 4),
                                      Text('Scatter'),
                                    ],
                                  ),
                                ),
                              ],
                              onChanged: (String? newValue) {
                                if (newValue != null) {
                                  setState(() {
                                    _routesDisplayMode = newValue;
                                  });
                                }
                              },
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                
                // Routes canvas with actual frame dimensions - NATURAL SIZING
                FutureBuilder<Size?>(
                  future: _getFrameDimensions(),
                  builder: (context, dimensionsSnapshot) {
                    if (dimensionsSnapshot.connectionState == ConnectionState.waiting) {
                      return const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            CircularProgressIndicator(),
                            SizedBox(height: 8),
                            Text('Loading frame dimensions...'),
                          ],
                        ),
                      );
                    }

                    if (dimensionsSnapshot.hasError) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error, size: 48, color: Colors.red),
                            const SizedBox(height: 16),
                            Text('Error loading frame dimensions: ${dimensionsSnapshot.error}'),
                          ],
                        ),
                      );
                    }

                    final frameDimensions = dimensionsSnapshot.data;
                    if (frameDimensions == null) {
                      return const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.warning, size: 48, color: Colors.orange),
                            SizedBox(height: 16),
                            Text('Could not determine frame dimensions'),
                          ],
                        ),
                      );
                    }

                    return Column(
                      children: [
                        // ROW 1: Camera View - HEIGHT = FRAME HEIGHT + HEADER
                        Container(
                          height: frameDimensions.height + 56, // Frame height + header space
                          child: Column(
                            children: [
                              // Camera view header
                              Container(
                                height: 40,
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.videocam, size: 16, color: Colors.blue),
                                    const SizedBox(width: 4),
                                    Text(
                                      'Camera View (${frameDimensions.width.toInt()}×${frameDimensions.height.toInt()}px)',
                                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              
                              // Camera view container - EXACT FRAME DIMENSIONS
                              Center(
                                child: Container(
                                  width: frameDimensions.width,
                                  height: frameDimensions.height,
                                  decoration: BoxDecoration(
                                    color: Colors.black12,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: Colors.grey.shade300),
                                  ),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: CustomPaint(
                                      painter: RoutesPainter(
                                        personGroups,
                                        frameDimensions: frameDimensions,
                                        displayMode: _routesDisplayMode,
                                      ),
                                      size: Size(frameDimensions.width, frameDimensions.height),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        
                        const SizedBox(height: 16), // Spacing between rows
                        
                        // ROW 2: Top View - HEIGHT = FRAME HEIGHT + HEADER  
                        Container(
                          height: frameDimensions.height + 56, // Frame height + header space
                          child: Column(
                            children: [
                              // Top view header
                              Container(
                                height: 40,
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.map, size: 16, color: Colors.green),
                                    const SizedBox(width: 4),
                                    Text(
                                      'Top View (${frameDimensions.width.toInt()}×${frameDimensions.height.toInt()}px)',
                                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              
                              // Top view container - SQUARE BASED ON FRAME HEIGHT
                              Center(
                                child: Container(
                                  width: frameDimensions.height, // Square based on frame height
                                  height: frameDimensions.height,
                                  decoration: BoxDecoration(
                                    color: Colors.black12,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: Colors.grey.shade300),
                                  ),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: CustomPaint(
                                      painter: TopViewRoutesPainter(
                                        personGroups,
                                        displayMode: _routesDisplayMode,
                                      ),
                                      size: Size(frameDimensions.height, frameDimensions.height),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    );
                  },
                ),
                
                // Legend - make it compact
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: _buildRoutesLegend(personGroups),
                ),
              ],
            ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error: $error'),
          ],
        ),
      ),
    );
  }

  Future<Map<String, dynamic>?> _fetchRoutesData() async {
    // Return cached data if available
    if (_cachedRoutesData != null) {
      return _cachedRoutesData;
    }
    
    // Prevent multiple concurrent requests
    if (_isLoadingRoutes) {
      // Wait a bit and return cached data if it becomes available
      await Future.delayed(const Duration(milliseconds: 100));
      return _cachedRoutesData;
    }
    
    _isLoadingRoutes = true;
    
    try {
      // Get authenticated API client
      final apiClient = ref.read(apiClientProvider);
      
      // Use the Orchestrator endpoint via Gateway (add /api/v1 prefix manually)
      final personObjectsResponse = await apiClient.get(
        '/api/v1/orchestrator/person-objects/${widget.mediaItem!.uuid}',
      );
      
      if (personObjectsResponse.statusCode == 200 && personObjectsResponse.data != null) {
        final data = personObjectsResponse.data as Map<String, dynamic>;
        
        // Check if person objects exist
        final success = data['success'] as bool? ?? false;
        final status = data['status'] as String? ?? '';
        
        if (success && status == 'completed') {
          // The Orchestrator response already contains all the data we need
          // including person_groups with movement_tracking and route_points
          // Cache the response
          _cachedRoutesData = data;
          
          return data;
        }
      }

      return null;
    } catch (e) {
      return null; // Return null instead of throwing to prevent UI crashes
    } finally {
      _isLoadingRoutes = false;
    }
  }

  Future<Size?> _getFrameDimensions() async {
    try {
      // Try method 1: Load frame using HTTP image provider
      final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/${widget.mediaItem!.uuid}/frame/0?format=jpeg';
      final apiClient = ref.read(apiClientProvider);
      
      // Create headers for authenticated request
      final headers = <String, String>{};
      if (apiClient.authToken != null) {
        headers['Authorization'] = 'Bearer ${apiClient.authToken}';
      }
      
      try {
        final image = NetworkImage(frameUrl, headers: headers);
        final ImageStream stream = image.resolve(const ImageConfiguration());
        final Completer<ImageInfo> completer = Completer();
        
        stream.addListener(ImageStreamListener((ImageInfo info, bool _) {
          completer.complete(info);
        }));
        
        final imageInfo = await completer.future.timeout(const Duration(seconds: 10));
        final size = Size(
          imageInfo.image.width.toDouble(), 
          imageInfo.image.height.toDouble()
        );

        return size;
      } catch (e) {}
      
      // Method 2: Fallback to media metadata if available
      if (widget.mediaItem!.metadata != null) {
        final metadata = widget.mediaItem!.metadata!;
        if (metadata['width'] != null && metadata['height'] != null) {
          final size = Size(
            (metadata['width'] as num).toDouble(),
            (metadata['height'] as num).toDouble(),
          );
          return size;
        }
      }
      
      // Method 3: Final fallback to common video resolution
      return const Size(1280, 720);
      
    } catch (e) {
      return const Size(1280, 720); // Fallback
    }
  }

  Widget _buildRoutesLegend(List<dynamic> personGroups) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Route Legend',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            
            // Horizontal layout for person legends
            Wrap(
              spacing: 16,
              runSpacing: 4,
              children: personGroups.asMap().entries.map((entry) {
                final index = entry.key;
                final group = entry.value;
                final color = _getPersonColor(index);
                final personId = group['person_id'] ?? 'person_${index + 1}';
                final routePoints = group['movement_tracking']?['route_points'] ?? [];
                
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Color indicator
                    Container(
                      width: 16,
                      height: 16,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 1),
                      ),
                    ),
                    const SizedBox(width: 6),
                    
                    // Person info
                    Text(
                      '$personId (${routePoints.length} pts)',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                );
              }).toList(),
            ),
            
            const SizedBox(height: 8),
            const Divider(height: 1),
            const SizedBox(height: 6),
            
            // Route symbols legend - more compact
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildLegendSymbol(
                  Icons.play_circle_filled,
                  Colors.green,
                  'Start',
                ),
                _buildLegendSymbol(
                  Icons.stop_circle,
                  Colors.red,
                  'End',
                ),
                _buildLegendSymbol(
                  Icons.circle,
                  Colors.blue,
                  'Path',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLegendSymbol(IconData icon, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 11),
        ),
      ],
    );
  }

  Color _getPersonColor(int index) {
    // Generate distinct colors for different persons
    final colors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
      Colors.pink,
      Colors.indigo,
      Colors.brown,
      Colors.cyan,
    ];
    return colors[index % colors.length];
  }

  /// Build thumbnail for individual in cross-video analysis with cropped face
  Widget _buildIndividualThumbnail(String individualUuid, bool isSuperIndividual) {
    final bestImage = _bestImages[individualUuid];

    final fallbackIcon = Icon(
      Icons.person,
      size: 40,
      color: isSuperIndividual ? Colors.blue : Colors.grey[600],
    );

    if (bestImage == null || bestImage.bestFace == null) {
      return fallbackIcon;
    }

    final rawImageUrl = bestImage.bestFace!.imageUrl;
    if (rawImageUrl.isEmpty) {
      return fallbackIcon;
    }

    // Resolve relative URLs (same logic as individual_group_detail_screen)
    final uri = Uri.tryParse(rawImageUrl);
    final resolvedUrl = (uri != null && uri.hasScheme)
        ? rawImageUrl
        : '${Config.gatewayServiceUrl}${rawImageUrl.startsWith('/') ? rawImageUrl : '/$rawImageUrl'}';

    final apiClient = ref.read(apiClientProvider);

    return Image.network(
      resolvedUrl,
      fit: BoxFit.cover,
      headers: apiClient.authToken != null
          ? {'Authorization': 'Bearer ${apiClient.authToken}'}
          : const {},
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) return child;
        return Container(
          color: Colors.grey[300],
          child: const Center(
            child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
          ),
        );
      },
      errorBuilder: (context, error, stackTrace) => fallbackIcon,
    );
  }

  /// Build cropped face for individual - simplified version for smaller thumbnails
  Future<Widget> _buildCroppedFaceForIndividual(
    Map<String, dynamic> faceData,
    String videoUuid,
  ) async {
    try {
      final frameNumber = faceData['frame_number'] ?? 0;
      final bbox = faceData['bbox'] as List<dynamic>?;
      
      if (bbox == null || bbox.length < 4) {
        final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/$videoUuid/frame/$frameNumber?format=jpeg';
        return _buildAuthenticatedFrameImageWidget(
          frameUrl,
          fit: BoxFit.cover,
        );
      }
      
      // Extract bounding box coordinates
      final x = bbox[0].toDouble();
      final y = bbox[1].toDouble();
      final x2 = bbox[2].toDouble();
      final y2 = bbox[3].toDouble();
      final width = x2 - x;
      final height = y2 - y;
      
      // Expand the crop area
      final areaMultiplier = 6.25;
      final scaleFactor = math.sqrt(areaMultiplier);
      final expandedWidth = width * scaleFactor;
      final expandedHeight = height * scaleFactor;
      
      final widthExpansion = expandedWidth - width;
      final heightExpansion = expandedHeight - height;
      
      final expandedX = x - (widthExpansion / 2);
      final expandedY = y - (heightExpansion / 2);
      
      if (expandedWidth <= 0 || expandedHeight <= 0) {
        final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/$videoUuid/frame/$frameNumber?format=jpeg';
        return _buildAuthenticatedFrameImageWidget(
          frameUrl,
          fit: BoxFit.cover,
        );
      }
      
      final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/$videoUuid/frame/$frameNumber?format=jpeg';
      
      return FutureBuilder<ui.Image>(
        future: _loadNetworkImage(frameUrl),
        builder: (context, snapshot) {
          if (snapshot.hasData && snapshot.data != null) {
            return SizedBox(
              width: 60,
              height: 60,
              child: CustomPaint(
                painter: CroppedImagePainter(
                  image: snapshot.data!,
                  cropRect: Rect.fromLTWH(expandedX, expandedY, expandedWidth, expandedHeight),
                ),
                size: Size(60, 60),
              ),
            );
          } else if (snapshot.hasError) {
            return _buildAuthenticatedFrameImageWidget(
              frameUrl,
              fit: BoxFit.cover,
            );
          } else {
            return Container(
              color: Colors.grey[300],
              child: Center(
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            );
          }
        },
      );
    } catch (e) {
      return Container(
        color: Colors.grey[300],
        child: Icon(Icons.error, size: 24, color: Colors.red),
      );
    }
  }

  Future<Uint8List?> _fetchAuthenticatedFrameBytes(String url) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final headers = <String, String>{};
      if (apiClient.authToken != null && apiClient.authToken!.isNotEmpty) {
        headers['Authorization'] = 'Bearer ${apiClient.authToken}';
      }

      final response = await apiClient.dio.get<List<int>>(
        url,
        options: dio.Options(
          responseType: dio.ResponseType.bytes,
          headers: headers,
        ),
      );

      final bytes = response.data;
      if (bytes == null || bytes.isEmpty) {
        return null;
      }
      return Uint8List.fromList(bytes);
    } catch (e) {
      print('Error loading authenticated frame bytes: $e');
      return null;
    }
  }

  Widget _buildAuthenticatedFrameImageWidget(
    String frameUrl, {
    BoxFit fit = BoxFit.cover,
  }) {
    return FutureBuilder<Uint8List?>(
      future: _fetchAuthenticatedFrameBytes(frameUrl),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(
            child: CircularProgressIndicator(strokeWidth: 2),
          );
        }

        final bytes = snapshot.data;
        if (bytes == null || bytes.isEmpty) {
          return Container(
            color: Colors.grey[300],
            child: Icon(Icons.broken_image, size: 24, color: Colors.grey[600]),
          );
        }

        return Image.memory(
          bytes,
          fit: fit,
          gaplessPlayback: true,
        );
      },
    );
  }
}

/// Custom painter to draw cropped image
class CroppedImagePainter extends CustomPainter {
  final ui.Image image;
  final Rect cropRect;

  CroppedImagePainter({required this.image, required this.cropRect});

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint();
    
    // MAINTAIN ASPECT RATIO: Don't stretch the square crop into different canvas proportions
    final cropAspectRatio = cropRect.width / cropRect.height;
    final canvasAspectRatio = size.width / size.height;
    
    late Rect destRect;
    
    if (cropAspectRatio > canvasAspectRatio) {
      // Crop is wider than canvas - fit width, center vertically
      final destHeight = size.width / cropAspectRatio;
      final offsetY = (size.height - destHeight) / 2;
      destRect = Rect.fromLTWH(0, offsetY, size.width, destHeight);
    } else {
      // Crop is taller than canvas - fit height, center horizontally  
      final destWidth = size.height * cropAspectRatio;
      final offsetX = (size.width - destWidth) / 2;
      destRect = Rect.fromLTWH(offsetX, 0, destWidth, size.height);
    }
    
    // Draw with proper aspect ratio (no stretching)
    canvas.drawImageRect(
      image,
      cropRect, // Source: 130x130 expanded face area
      destRect,  // Destination: properly scaled to fit canvas without stretching
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Custom painter for drawing movement routes
class RoutesPainter extends CustomPainter {
  final List<dynamic> personGroups;
  final Size? frameDimensions;
  final String displayMode; // 'path' or 'scatter'

  RoutesPainter(this.personGroups, {this.frameDimensions, this.displayMode = 'path'});

  @override
  void paint(Canvas canvas, Size size) {
    if (personGroups.isEmpty) {
      // Draw "No routes" message
      final textPainter = TextPainter(
        text: const TextSpan(
          text: 'No movement routes to display',
          style: TextStyle(color: Colors.grey, fontSize: 16),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(
          (size.width - textPainter.width) / 2,
          (size.height - textPainter.height) / 2,
        ),
      );
      return;
    }

    // Use frame dimensions for 1:1 coordinate mapping if available
    if (frameDimensions != null) {
      _paintWithFrameDimensions(canvas, size);
    } else {
      _paintWithScaling(canvas, size);
    }
  }

  void _paintWithFrameDimensions(Canvas canvas, Size size) {

    // Check if we have true 1:1 mapping (canvas matches frame exactly)
    final isOneToOneMapping = (size.width == frameDimensions!.width && size.height == frameDimensions!.height);

    // Helper function for coordinate conversion
    Offset convertPoint(double x, double y) {
      if (isOneToOneMapping) {
        // True 1:1 mapping - use coordinates directly
        return Offset(x, y);
      } else {
        // Scale to fit canvas
        final scaleX = size.width / frameDimensions!.width;
        final scaleY = size.height / frameDimensions!.height;
        return Offset(x * scaleX, y * scaleY);
      }
    }

    // Draw routes for each person
    for (int personIndex = 0; personIndex < personGroups.length; personIndex++) {
      final group = personGroups[personIndex];
      final routePoints = group['movement_tracking']?['route_points'] ?? [];
      
      if (routePoints.isEmpty) continue;

      final color = _getPersonColor(personIndex);
      
      // Draw based on display mode
      if (displayMode == 'scatter') {
        // Scatter plot mode - draw all points as circles with sequence numbers
        for (int i = 0; i < routePoints.length; i++) {
          final point = routePoints[i];
          final x = (point['center_x'] ?? 0).toDouble();
          final y = (point['center_y'] ?? 0).toDouble();
          final pos = convertPoint(x, y);
          
          // Varying point sizes: start=large, end=medium, middle=small
          double pointSize;
          Color pointColor;
          if (i == 0) {
            pointSize = 10.0; // Start point
            pointColor = Colors.green;
          } else if (i == routePoints.length - 1) {
            pointSize = 8.0;  // End point
            pointColor = Colors.red;
          } else {
            pointSize = 5.0;  // Middle points
            pointColor = color;
          }
          
          // Draw main point
          final pointPaint = Paint()..color = pointColor.withOpacity(0.8);
          canvas.drawCircle(pos, pointSize, pointPaint);
          
          // Add white border for better visibility
          final borderPaint = Paint()
            ..color = Colors.white
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5;
          canvas.drawCircle(pos, pointSize, borderPaint);
          
          // Draw sequence number on larger points
          if (pointSize >= 8.0) {
            final textPainter = TextPainter(
              text: TextSpan(
                text: '${i + 1}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                ),
              ),
              textDirection: TextDirection.ltr,
            );
            textPainter.layout();
            textPainter.paint(
              canvas,
              Offset(pos.dx - textPainter.width / 2, pos.dy - textPainter.height / 2),
            );
          }
        }
      } else {
        // Path mode - draw connected route path
        if (routePoints.length > 1) {
        final path = Path();
        bool isFirst = true;
        
        for (final point in routePoints) {
          final x = (point['center_x'] ?? 0).toDouble();
          final y = (point['center_y'] ?? 0).toDouble();
          final pos = convertPoint(x, y);
          
          if (isFirst) {
            path.moveTo(pos.dx, pos.dy);
            isFirst = false;
          } else {
            path.lineTo(pos.dx, pos.dy);
          }
        }
        
        // Draw the path
        final pathPaint = Paint()
          ..color = color.withOpacity(0.7)
          ..strokeWidth = 3.0
          ..style = PaintingStyle.stroke;
        
        canvas.drawPath(path, pathPaint);
      }
      
      // Draw route points and markers (only in path mode)
      for (int i = 0; i < routePoints.length; i++) {
        final point = routePoints[i];
        final x = (point['center_x'] ?? 0).toDouble();
        final y = (point['center_y'] ?? 0).toDouble();
        final pos = convertPoint(x, y);
        
        // Draw point
        final pointPaint = Paint()..color = color;
        canvas.drawCircle(pos, 4.0, pointPaint);
        
        // Draw start marker (green arrow)
        if (i == 0) {
          final startPaint = Paint()..color = Colors.green;
          canvas.drawCircle(pos, 8.0, startPaint);
          
          // Draw arrow
          final arrowPaint = Paint()
            ..color = Colors.white
            ..strokeWidth = 2.0
            ..style = PaintingStyle.stroke;
          
          canvas.drawLine(
            Offset(pos.dx - 4, pos.dy),
            Offset(pos.dx + 4, pos.dy),
            arrowPaint,
          );
          canvas.drawLine(
            Offset(pos.dx + 4, pos.dy),
            Offset(pos.dx + 1, pos.dy - 3),
            arrowPaint,
          );
          canvas.drawLine(
            Offset(pos.dx + 4, pos.dy),
            Offset(pos.dx + 1, pos.dy + 3),
            arrowPaint,
          );
        }
        
        // Draw end marker (red square)
        if (i == routePoints.length - 1) {
          final endPaint = Paint()..color = Colors.red;
          canvas.drawRect(
            Rect.fromCenter(center: pos, width: 12, height: 12),
            endPaint,
          );
        }
      }
      } // End of path mode else block
      
      // Draw person label near start point
      if (routePoints.isNotEmpty) {
        final firstPoint = routePoints.first;
        final x = (firstPoint['center_x'] ?? 0).toDouble();
        final y = (firstPoint['center_y'] ?? 0).toDouble();
        final pos = convertPoint(x, y);
        
        final personId = group['person_id'] ?? 'person_${personIndex + 1}';
        final textPainter = TextPainter(
          text: TextSpan(
            text: personId,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
          textDirection: TextDirection.ltr,
        );
        textPainter.layout();
        
        // Position label above and to the right of start point
        textPainter.paint(
          canvas,
          Offset(pos.dx + 12, pos.dy - 20),
        );
      }
    }

    // Draw frame information in corner
    final frameInfo = 'Frame: ${frameDimensions!.width.toInt()}×${frameDimensions!.height.toInt()}px';
    final infoTextPainter = TextPainter(
      text: TextSpan(
        text: frameInfo,
        style: const TextStyle(
          color: Colors.grey,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    infoTextPainter.layout();
    infoTextPainter.paint(
      canvas,
      Offset(size.width - infoTextPainter.width - 8, 8),
    );
  }

  void _paintWithScaling(Canvas canvas, Size size) {
    // Fallback method with scaling (original implementation)
    // Find bounds of all routes to scale properly
    double minX = double.infinity, minY = double.infinity;
    double maxX = double.negativeInfinity, maxY = double.negativeInfinity;

    for (final group in personGroups) {
      final routePoints = group['movement_tracking']?['route_points'] ?? [];
      for (final point in routePoints) {
        final x = (point['center_x'] ?? 0).toDouble();
        final y = (point['center_y'] ?? 0).toDouble();
        minX = math.min(minX, x);
        minY = math.min(minY, y);
        maxX = math.max(maxX, x);
        maxY = math.max(maxY, y);
      }
    }

    // Add padding
    const padding = 40.0;
    final dataWidth = maxX - minX;
    final dataHeight = maxY - minY;
    
    if (dataWidth <= 0 || dataHeight <= 0) return;

    // Calculate scale to fit canvas
    final scaleX = (size.width - 2 * padding) / dataWidth;
    final scaleY = (size.height - 2 * padding) / dataHeight;
    final scale = math.min(scaleX, scaleY);

    // Helper function to convert coordinates
    Offset convertPoint(double x, double y) {
      final scaledX = padding + (x - minX) * scale;
      final scaledY = padding + (y - minY) * scale;
      return Offset(scaledX, scaledY);
    }

    // Draw routes for each person (same as before)
    for (int personIndex = 0; personIndex < personGroups.length; personIndex++) {
      final group = personGroups[personIndex];
      final routePoints = group['movement_tracking']?['route_points'] ?? [];
      
      if (routePoints.isEmpty) continue;

      final color = _getPersonColor(personIndex);
      
      // Draw route path
      if (routePoints.length > 1) {
        final path = Path();
        bool isFirst = true;
        
        for (final point in routePoints) {
          final x = (point['center_x'] ?? 0).toDouble();
          final y = (point['center_y'] ?? 0).toDouble();
          final pos = convertPoint(x, y);
          
          if (isFirst) {
            path.moveTo(pos.dx, pos.dy);
            isFirst = false;
          } else {
            path.lineTo(pos.dx, pos.dy);
          }
        }
        
        // Draw the path
        final pathPaint = Paint()
          ..color = color.withOpacity(0.7)
          ..strokeWidth = 3.0
          ..style = PaintingStyle.stroke;
        
        canvas.drawPath(path, pathPaint);
      }
      
      // Draw route points and markers (same implementation as above)
      for (int i = 0; i < routePoints.length; i++) {
        final point = routePoints[i];
        final x = (point['center_x'] ?? 0).toDouble();
        final y = (point['center_y'] ?? 0).toDouble();
        final pos = convertPoint(x, y);
        
        // Draw point
        final pointPaint = Paint()..color = color;
        canvas.drawCircle(pos, 4.0, pointPaint);
        
        // Draw start marker (green arrow)
        if (i == 0) {
          final startPaint = Paint()..color = Colors.green;
          canvas.drawCircle(pos, 8.0, startPaint);
          
          // Draw arrow (same as above)
          final arrowPaint = Paint()
            ..color = Colors.white
            ..strokeWidth = 2.0
            ..style = PaintingStyle.stroke;
          
          canvas.drawLine(
            Offset(pos.dx - 4, pos.dy),
            Offset(pos.dx + 4, pos.dy),
            arrowPaint,
          );
          canvas.drawLine(
            Offset(pos.dx + 4, pos.dy),
            Offset(pos.dx + 1, pos.dy - 3),
            arrowPaint,
          );
          canvas.drawLine(
            Offset(pos.dx + 4, pos.dy),
            Offset(pos.dx + 1, pos.dy + 3),
            arrowPaint,
          );
        }
        
        // Draw end marker (red square)
        if (i == routePoints.length - 1) {
          final endPaint = Paint()..color = Colors.red;
          canvas.drawRect(
            Rect.fromCenter(center: pos, width: 12, height: 12),
            endPaint,
          );
        }
      }
      
      // Draw person label near start point
      if (routePoints.isNotEmpty) {
        final firstPoint = routePoints.first;
        final x = (firstPoint['center_x'] ?? 0).toDouble();
        final y = (firstPoint['center_y'] ?? 0).toDouble();
        final pos = convertPoint(x, y);
        
        final personId = group['person_id'] ?? 'person_${personIndex + 1}';
        final textPainter = TextPainter(
          text: TextSpan(
            text: personId,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
          textDirection: TextDirection.ltr,
        );
        textPainter.layout();
        
        // Position label above and to the right of start point
        textPainter.paint(
          canvas,
          Offset(pos.dx + 12, pos.dy - 20),
        );
      }
    }
  }

  Color _getPersonColor(int index) {
    final colors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
      Colors.pink,
      Colors.indigo,
      Colors.brown,
      Colors.cyan,
    ];
    return colors[index % colors.length];
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// Custom painter for drawing movement routes from top-down view
class TopViewRoutesPainter extends CustomPainter {
  final List<dynamic> personGroups;
  final String displayMode; // 'path' or 'scatter'

  TopViewRoutesPainter(this.personGroups, {this.displayMode = 'path'});

  @override
  void paint(Canvas canvas, Size size) {
    if (personGroups.isEmpty) {
      // Draw "No routes" message
      final textPainter = TextPainter(
        text: const TextSpan(
          text: 'No movement routes to display',
          style: TextStyle(color: Colors.grey, fontSize: 16),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(
          (size.width - textPainter.width) / 2,
          (size.height - textPainter.height) / 2,
        ),
      );
      return;
    }

    // Find bounds of all routes to create a top-down view
    double minX = double.infinity, minY = double.infinity;
    double maxX = double.negativeInfinity, maxY = double.negativeInfinity;

    for (final group in personGroups) {
      final routePoints = group['movement_tracking']?['route_points'] ?? [];
      for (final point in routePoints) {
        final x = (point['center_x'] ?? 0).toDouble();
        final y = (point['center_y'] ?? 0).toDouble();
        minX = math.min(minX, x);
        minY = math.min(minY, y);
        maxX = math.max(maxX, x);
        maxY = math.max(maxY, y);
      }
    }

    // Add padding around the movement area
    const padding = 40.0;
    final dataWidth = maxX - minX;
    final dataHeight = maxY - minY;
    
    if (dataWidth <= 0 || dataHeight <= 0) return;

    // Calculate scale to fit canvas with equal scaling (preserving aspect ratio)
    final availableWidth = size.width - 2 * padding;
    final availableHeight = size.height - 2 * padding;
    final scale = math.min(availableWidth / dataWidth, availableHeight / dataHeight);

    // Calculate offset to center the movement area
    final scaledWidth = dataWidth * scale;
    final scaledHeight = dataHeight * scale;
    final offsetX = (size.width - scaledWidth) / 2 - minX * scale;
    final offsetY = (size.height - scaledHeight) / 2 - minY * scale;

    // Helper function to convert coordinates
    Offset convertPoint(double x, double y) {
      final convertedX = x * scale + offsetX;
      final convertedY = y * scale + offsetY;
      return Offset(convertedX, convertedY);
    }

    // Draw grid background
    _drawGrid(canvas, size, scale, offsetX, offsetY);

    // Draw routes for each person
    for (int personIndex = 0; personIndex < personGroups.length; personIndex++) {
      final group = personGroups[personIndex];
      final routePoints = group['movement_tracking']?['route_points'] ?? [];
      
      if (routePoints.isEmpty) continue;

      final color = _getPersonColor(personIndex);
      
      // Draw based on display mode
      if (displayMode == 'scatter') {
        // Scatter plot mode - draw only points without lines
        for (int i = 0; i < routePoints.length; i++) {
          final point = routePoints[i];
          final x = (point['center_x'] ?? 0).toDouble();
          final y = (point['center_y'] ?? 0).toDouble();
          final pos = convertPoint(x, y);
          
          // Varying point sizes: start=large, end=medium, middle=small
          double pointSize;
          Color pointColor;
          if (i == 0) {
            pointSize = 12.0; // Start point (slightly larger for top view)
            pointColor = Colors.green;
          } else if (i == routePoints.length - 1) {
            pointSize = 10.0;  // End point
            pointColor = Colors.red;
          } else {
            pointSize = 6.0;  // Middle points (slightly larger for top view)
            pointColor = color;
          }
          
          // Draw main point
          final pointPaint = Paint()..color = pointColor.withOpacity(0.9);
          canvas.drawCircle(pos, pointSize, pointPaint);
          
          // Add white border for better visibility
          final borderPaint = Paint()
            ..color = Colors.white
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2.0;
          canvas.drawCircle(pos, pointSize, borderPaint);
          
          // Draw sequence number on larger points
          if (pointSize >= 10.0) {
            final textPainter = TextPainter(
              text: TextSpan(
                text: '${i + 1}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
              textDirection: TextDirection.ltr,
            );
            textPainter.layout();
            textPainter.paint(
              canvas,
              Offset(pos.dx - textPainter.width / 2, pos.dy - textPainter.height / 2),
            );
          }
        }
      } else {
        // Path mode - draw connected route path
        if (routePoints.length > 1) {
        final path = Path();
        bool isFirst = true;
        
        for (final point in routePoints) {
          final x = (point['center_x'] ?? 0).toDouble();
          final y = (point['center_y'] ?? 0).toDouble();
          final pos = convertPoint(x, y);
          
          if (isFirst) {
            path.moveTo(pos.dx, pos.dy);
            isFirst = false;
          } else {
            path.lineTo(pos.dx, pos.dy);
          }
        }
        
        // Draw the path with thicker lines for top view
        final pathPaint = Paint()
          ..color = color.withOpacity(0.8)
          ..strokeWidth = 4.0
          ..style = PaintingStyle.stroke;
        
        canvas.drawPath(path, pathPaint);
      }
      
      // Draw route points (only in path mode)
      for (int i = 0; i < routePoints.length; i++) {
        final point = routePoints[i];
        final x = (point['center_x'] ?? 0).toDouble();
        final y = (point['center_y'] ?? 0).toDouble();
        final pos = convertPoint(x, y);
        
        // Draw point
        final pointPaint = Paint()..color = color;
        canvas.drawCircle(pos, 6.0, pointPaint);
        
        // Draw start marker (green circle with arrow)
        if (i == 0) {
          final startPaint = Paint()..color = Colors.green;
          canvas.drawCircle(pos, 12.0, startPaint);
          
          // Draw directional arrow towards next point
          if (routePoints.length > 1) {
            final nextPoint = routePoints[1];
            final nextX = (nextPoint['center_x'] ?? 0).toDouble();
            final nextY = (nextPoint['center_y'] ?? 0).toDouble();
            final nextPos = convertPoint(nextX, nextY);
            
            final dx = nextPos.dx - pos.dx;
            final dy = nextPos.dy - pos.dy;
            final length = math.sqrt(dx * dx + dy * dy);
            
            if (length > 0) {
              final unitX = dx / length;
              final unitY = dy / length;
              
              // Draw arrow
              final arrowPaint = Paint()
                ..color = Colors.white
                ..strokeWidth = 2.0
                ..style = PaintingStyle.stroke;
              
              final arrowLength = 8.0;
              final arrowEnd = Offset(
                pos.dx + unitX * arrowLength,
                pos.dy + unitY * arrowLength,
              );
              
              canvas.drawLine(pos, arrowEnd, arrowPaint);
              
              // Arrow head
              final arrowHeadLength = 4.0;
              final leftArrow = Offset(
                arrowEnd.dx - unitX * arrowHeadLength + unitY * arrowHeadLength * 0.5,
                arrowEnd.dy - unitY * arrowHeadLength - unitX * arrowHeadLength * 0.5,
              );
              final rightArrow = Offset(
                arrowEnd.dx - unitX * arrowHeadLength - unitY * arrowHeadLength * 0.5,
                arrowEnd.dy - unitY * arrowHeadLength + unitX * arrowHeadLength * 0.5,
              );
              
              canvas.drawLine(arrowEnd, leftArrow, arrowPaint);
              canvas.drawLine(arrowEnd, rightArrow, arrowPaint);
            }
          }
        }
        
        // Draw end marker (red square)
        if (i == routePoints.length - 1) {
          final endPaint = Paint()..color = Colors.red;
          canvas.drawRect(
            Rect.fromCenter(center: pos, width: 16, height: 16),
            endPaint,
          );
        }
      }
      } // End of path mode else block
      
      // Draw person label near start point
      if (routePoints.isNotEmpty) {
        final firstPoint = routePoints.first;
        final x = (firstPoint['center_x'] ?? 0).toDouble();
        final y = (firstPoint['center_y'] ?? 0).toDouble();
        final pos = convertPoint(x, y);
        
        final personId = group['person_id'] ?? 'person_${personIndex + 1}';
        final textPainter = TextPainter(
          text: TextSpan(
            text: personId,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 14,
              shadows: [
                Shadow(
                  color: Colors.white,
                  offset: Offset(1, 1),
                  blurRadius: 2,
                ),
              ],
            ),
          ),
          textDirection: TextDirection.ltr,
        );
        textPainter.layout();
        
        // Position label above start point
        textPainter.paint(
          canvas,
          Offset(pos.dx - textPainter.width / 2, pos.dy - 30),
        );
      }
    }

    // Draw compass and scale info
    _drawCompassAndScale(canvas, size, scale);
  }

  void _drawGrid(Canvas canvas, Size size, double scale, double offsetX, double offsetY) {
    final gridPaint = Paint()
      ..color = Colors.grey.withOpacity(0.2)
      ..strokeWidth = 1.0;

    // Draw subtle grid lines
    final gridSpacing = 50.0 * scale; // Grid every 50 pixels in original coordinates
    
    for (double x = 0; x < size.width; x += gridSpacing) {
      canvas.drawLine(
        Offset(x, 0),
        Offset(x, size.height),
        gridPaint,
      );
    }
    
    for (double y = 0; y < size.height; y += gridSpacing) {
      canvas.drawLine(
        Offset(0, y),
        Offset(size.width, y),
        gridPaint,
      );
    }
  }

  void _drawCompassAndScale(Canvas canvas, Size size, double scale) {
    // Draw compass rose in top-right corner
    final compassCenter = Offset(size.width - 40, 40);
    
    // Draw compass background
    final compassBgPaint = Paint()
      ..color = Colors.white.withOpacity(0.9)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(compassCenter, 25, compassBgPaint);
    
    final compassBorderPaint = Paint()
      ..color = Colors.grey.shade400
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;
    canvas.drawCircle(compassCenter, 25, compassBorderPaint);
    
    // Draw N arrow
    final arrowPaint = Paint()
      ..color = Colors.red
      ..strokeWidth = 2.0;
      
    canvas.drawLine(
      compassCenter,
      Offset(compassCenter.dx, compassCenter.dy - 15),
      arrowPaint,
    );
    
    // Draw N label
    final compassTextPainter = TextPainter(
      text: const TextSpan(
        text: 'N',
        style: TextStyle(
          color: Colors.red,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    compassTextPainter.layout();
    compassTextPainter.paint(
      canvas,
      Offset(compassCenter.dx - 4, compassCenter.dy - 35),
    );

    // Draw scale info in bottom-right corner
    final scaleText = 'Scale: ${scale.toStringAsFixed(2)}x';
    final scaleTextPainter = TextPainter(
      text: TextSpan(
        text: scaleText,
        style: const TextStyle(
          color: Colors.grey,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    scaleTextPainter.layout();
    scaleTextPainter.paint(
      canvas,
      Offset(size.width - scaleTextPainter.width - 8, size.height - 20),
    );
  }

  Color _getPersonColor(int index) {
    // Same color scheme as camera view for consistency
    final colors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
      Colors.pink,
      Colors.indigo,
      Colors.brown,
      Colors.cyan,
    ];
    return colors[index % colors.length];
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

// ============================================================
// CROSS-VIDEO TAB METHODS
// ============================================================

/// Extension on PersonObjectsDetailScreenState for cross-video tabs
extension CrossVideoTabs on _PersonObjectsDetailScreenState {
  /// Build Individuals tab for cross-video mode
  Widget _buildIndividualsTabCrossVideo() {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(
        child: Text('No individuals available'),
      );
    }

    return Column(
      children: [
        if (_hierarchicalMergeWasApplied) _buildMergeBanner(),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _aggregatedAnalyses!.length,
            itemBuilder: (context, index) {
              final analysis = _aggregatedAnalyses![index];
              return _buildIndividualCard(analysis, index);
            },
          ),
        ),
      ],
    );
  }

  /// Yellow banner shown when the last search applied automatic hierarchical merges
  Widget _buildMergeBanner() {
    final totalMerged = _mergeGroups.fold<int>(0, (sum, g) => sum + g.mergedCount);
    return Container(
      width: double.infinity,
      color: Colors.amber.shade100,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Icon(Icons.merge_type, color: Colors.amber[800]),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '$totalMerged individual${totalMerged == 1 ? '' : 's'} were automatically merged',
              style: TextStyle(color: Colors.amber[900], fontWeight: FontWeight.w500),
            ),
          ),
          TextButton(
            onPressed: _showMergeReviewSheet,
            child: Text('Review', style: TextStyle(color: Colors.amber[900])),
          ),
          TextButton(
            onPressed: () async {
              for (final group in _mergeGroups) {
                for (final childUuid in group.mergedMvrUuids) {
                  await _performUnmerge(childUuid);
                }
              }
            },
            child: Text('Undo All', style: TextStyle(color: Colors.red[700])),
          ),
        ],
      ),
    );
  }

  /// Bottom sheet listing each merge group with face thumbnails and per-child undo buttons
  void _showMergeReviewSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.6,
          maxChildSize: 0.9,
          minChildSize: 0.3,
          builder: (_, scrollCtrl) {
            return Column(
              children: [
                const SizedBox(height: 8),
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 12),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Text(
                    'Automatic Merges',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: ListView.builder(
                    controller: scrollCtrl,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _mergeGroups.length,
                    itemBuilder: (_, i) {
                      final group = _mergeGroups[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Super-individual header row
                              Row(
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(4),
                                    child: SizedBox(
                                      width: 36,
                                      height: 36,
                                      child: _bestImages[group.superIndividualUuid]?.bestFace != null
                                          ? _buildChildMvrThumbnail(group.superIndividualUuid)
                                          : Icon(Icons.person, color: Colors.grey[600]),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'Super: ${group.superIndividualUuid.length >= 8 ? group.superIndividualUuid.substring(0, 8) : group.superIndividualUuid}...',
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              // Child rows
                              ...group.mergedMvrUuids.map((childUuid) {
                                final sim = group.similarities[childUuid];
                                final shortId = childUuid.length >= 8
                                    ? childUuid.substring(0, 8)
                                    : childUuid;
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 6),
                                  child: Row(
                                    children: [
                                      const SizedBox(width: 8),
                                      Icon(Icons.subdirectory_arrow_right,
                                          size: 16, color: Colors.grey[500]),
                                      const SizedBox(width: 4),
                                      ClipRRect(
                                        borderRadius: BorderRadius.circular(4),
                                        child: SizedBox(
                                          width: 30,
                                          height: 30,
                                          child: _buildChildMvrThumbnail(childUuid),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text('$shortId...',
                                                style: const TextStyle(fontSize: 13)),
                                            if (sim != null)
                                              Text(
                                                'Similarity: ${(sim * 100).toStringAsFixed(1)}%',
                                                style: TextStyle(
                                                    fontSize: 11, color: Colors.grey[600]),
                                              ),
                                          ],
                                        ),
                                      ),
                                      TextButton(
                                        onPressed: () {
                                          Navigator.of(ctx).pop();
                                          _performUnmerge(childUuid);
                                        },
                                        child: const Text('Undo',
                                            style: TextStyle(color: Colors.orange)),
                                      ),
                                    ],
                                  ),
                                );
                              }),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  /// Calculate aggregate statistics across all individuals
  /// Build individual card showing aggregated data with hierarchical merge support (v2.19.84)
  Widget _buildIndividualCard(AggregatedIndividualAnalysis analysis, int index) {
    final isExpanded = _expandedIndividuals.contains(analysis.individualUuid);
    final isSelected = _selectedIndividuals.contains(analysis.individualUuid);
    final isSuperIndividual = analysis.isSuperIndividual;
    final isStandalone = analysis.isStandalone;
    
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 4, // Same elevation for all Level 1 individuals
      child: Column(
        children: [
          // Level 1: Super-Individual / Standalone Header
          InkWell(
            onTap: () {
              setState(() {
                if (isExpanded) {
                  _expandedIndividuals.remove(analysis.individualUuid);
                } else {
                  _expandedIndividuals.add(analysis.individualUuid);
                }
              });
            },
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      // Checkbox for selection
                      Checkbox(
                        value: isSelected,
                        onChanged: (bool? value) {
                          setState(() {
                            if (value == true) {
                              _selectedIndividuals.add(analysis.individualUuid);
                            } else {
                              _selectedIndividuals.remove(analysis.individualUuid);
                            }
                          });
                        },
                      ),
                      const SizedBox(width: 8),
                      // Individual icon with badge - now with cropped face
                      Stack(
                        children: [
                          Container(
                            width: 60,
                            height: 60,
                            decoration: BoxDecoration(
                              color: isSuperIndividual 
                                  ? Colors.blue.shade100 
                                  : Colors.grey.shade200,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: _buildIndividualThumbnail(analysis.individualId, isSuperIndividual),  // Use individualId (MVR UUID) not individualUuid
                            ),
                          ),
                          // Badge: Blue for merged, Grey for standalone
                          Positioned(
                            bottom: 0,
                            right: 0,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: isSuperIndividual ? Colors.blue : Colors.grey[600],
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                isSuperIndividual ? Icons.merge_type : Icons.person,
                                size: 16,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(width: 16),
                      // Individual info
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Name (if available)
                            Builder(
                              builder: (context) {
                                debugPrint('═══ UI CARD RENDER DEBUG ═══');
                                debugPrint('Individual ID: ${analysis.individualId}');
                                debugPrint('Name value: ${analysis.name}');
                                debugPrint('Name is null: ${analysis.name == null}');
                                debugPrint('═══════════════════════════');
                                return const SizedBox.shrink();
                              },
                            ),
                            if (analysis.name != null) ...[
                              Text(
                                analysis.name!,
                                style: const TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.blue,
                                ),
                              ),
                              const SizedBox(height: 4),
                            ],
                            Row(
                              children: [
                                Text(
                                  analysis.demographics?.gender ?? 'Unknown',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: analysis.name != null 
                                        ? FontWeight.normal 
                                        : FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                // Chip: Blue for merged, Grey for standalone
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: isSuperIndividual
                                        ? Colors.blue.withOpacity(0.2)
                                        : Colors.grey.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(
                                    isSuperIndividual
                                        ? '${analysis.mergedMVRCount} batches merged'
                                        : 'Standalone individual',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: isSuperIndividual
                                          ? Colors.blue[900]
                                          : Colors.grey[800],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            if (analysis.demographics != null &&
                                (analysis.demographics!.ageMin != null ||
                                    analysis.demographics!.ageMax != null))
                              Text(
                                'Age: ${analysis.demographics!.ageMin ?? "?"}-${analysis.demographics!.ageMax ?? "?"}',
                                style: TextStyle(color: Colors.grey[700]),
                              ),
                            const SizedBox(height: 8),
                            Text(
                              '${analysis.totalAppearances} appearances across ${analysis.uniqueVideos} videos',
                              style: const TextStyle(fontSize: 12),
                            ),
                            const SizedBox(height: 4),
                            _buildStatChip('Confidence', '${(analysis.averageConfidence * 100).toStringAsFixed(0)}%'),
                          ],
                        ),
                      ),
                      // Edit name button
                      IconButton(
                        icon: const Icon(Icons.edit, size: 20),
                        onPressed: () => _showEditNameDialog(analysis),
                        tooltip: 'Edit name',
                        color: Colors.blue[700],
                      ),
                      // Expand/collapse icon
                      Icon(
                        isExpanded ? Icons.expand_less : Icons.expand_more,
                        color: Colors.grey[600],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          
          // Level 2: Merged MVR People (only if super-individual and expanded)
          if (isExpanded && isSuperIndividual && analysis.mergedMVRPeople.isNotEmpty) ...[
            const Divider(height: 1),
            Builder(builder: (context) {
              final superUuid = analysis.individualUuid;
              final displayList =
                  _pagedMergedChildren[superUuid] ?? analysis.mergedMVRPeople;
              final hasMore = _hasMoreChildren[superUuid] ?? false;
              final isLoadingMore =
                  _loadingMoreChildren[superUuid] ?? false;
              final total = analysis.mergedChildrenTotal > 0
                  ? analysis.mergedChildrenTotal
                  : analysis.mergedMVRPeople.length;

              return Container(
                color: Colors.blue.withOpacity(0.05),
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      child: Text(
                        'Merged MVR People (${displayList.length}${hasMore ? ' of $total' : ''})',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.blue[900],
                        ),
                      ),
                    ),
                    ...displayList.map((mvr) => _buildMergedMVRCard(mvr)),
                    if (isLoadingMore)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 8),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (hasMore)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Center(
                          child: TextButton.icon(
                            onPressed: () =>
                                _loadMoreMergedChildren(superUuid),
                            icon: const Icon(Icons.keyboard_arrow_down),
                            label: Text(
                              'Load more (${total - displayList.length} remaining)',
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              );
            }),
          ],
          
          // Level 2/3: Person Objects / Appearances
          if (isExpanded) ...[
            const Divider(height: 1),
            _buildExpandedAppearances(analysis),
          ],
        ],
      ),
    );
  }
  
  /// Build child MVR thumbnail (falls back to badge icon if no image available).
  /// Checks _childMvrImages first, then _bestImages (so super-individual UUIDs also work).
  Widget _buildChildMvrThumbnail(String childMvrUuid) {
    final bestImage = _childMvrImages[childMvrUuid] ?? _bestImages[childMvrUuid];
    if (bestImage?.bestFace == null || bestImage!.bestFace!.imageUrl.isEmpty) {
      return Icon(Icons.badge, size: 24, color: Colors.blue[700]);
    }
    final rawUrl = bestImage.bestFace!.imageUrl;
    final uri = Uri.tryParse(rawUrl);
    final resolvedUrl = (uri != null && uri.hasScheme)
        ? rawUrl
        : '${Config.gatewayServiceUrl}${rawUrl.startsWith('/') ? rawUrl : '/$rawUrl'}';
    final apiClient = ref.read(apiClientProvider);
    return Image.network(
      resolvedUrl,
      fit: BoxFit.cover,
      headers: apiClient.authToken != null
          ? {'Authorization': 'Bearer ${apiClient.authToken}'}
          : const {},
      errorBuilder: (_, __, ___) => Icon(Icons.badge, size: 24, color: Colors.blue[700]),
    );
  }

  /// Build merged MVR person card (Level 2 in hierarchy)
  Widget _buildMergedMVRCard(MergedMVRPerson mvr) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // Child MVR thumbnail
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: Container(
                width: 40,
                height: 40,
                color: Colors.blue.shade50,
                child: _buildChildMvrThumbnail(mvr.mvrPeopleUuid),
              ),
            ),
            const SizedBox(width: 12),
            // MVR info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'MVR ${mvr.mvrPeopleUuid.length >= 8 ? mvr.mvrPeopleUuid.substring(0, 8) : mvr.mvrPeopleUuid}...',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      if (mvr.gender != null)
                        _buildSmallChip(mvr.gender!, Icons.person),
                      if (mvr.ageMin != null && mvr.ageMax != null) ...[
                        const SizedBox(width: 4),
                        _buildSmallChip(mvr.ageRange, Icons.cake),
                      ],
                      const SizedBox(width: 4),
                      _buildSmallChip('Quality: ${(mvr.qualityScore * 100).toStringAsFixed(0)}%', Icons.star),
                    ],
                  ),
                  if (mvr.similarityToFeatured > 0) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.compare_arrows, size: 12, color: Colors.blue[700]),
                        const SizedBox(width: 4),
                        Text(
                          'Similarity: ${mvr.formattedSimilarity}',
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.blue[700],
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            // Split (undo merge) button
            IconButton(
              icon: Icon(Icons.call_split, size: 20, color: Colors.orange[700]),
              tooltip: 'Split — undo this merge',
              onPressed: () => _confirmSplitMvr(mvr),
            ),
          ],
        ),
      ),
    );
  }

  /// Confirm and perform unmerge for a single child MVR card
  void _confirmSplitMvr(MergedMVRPerson mvr) {
    final shortId = mvr.mvrPeopleUuid.length >= 8
        ? mvr.mvrPeopleUuid.substring(0, 8)
        : mvr.mvrPeopleUuid;
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Split merged individual?'),
        content: Text(
          'This will restore MVR $shortId... as a separate individual '
          'and reassign its person objects back to it.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _performUnmerge(mvr.mvrPeopleUuid);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.orange[700]),
            child: const Text('Split'),
          ),
        ],
      ),
    );
  }

  /// Call the unmerge API endpoint, then reload cross-video data
  Future<void> _performUnmerge(String orphanedMvrUuid) async {
    final mediaApiClient = MediaApiClient(ref.read(apiClientProvider));
    try {
      final response = await mediaApiClient.unmergeMvr(orphanedMvrUuid: orphanedMvrUuid);
      if (response.success) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Individual split successfully'),
              backgroundColor: Colors.green,
            ),
          );
          // After a split, reload with both the winner and the now-restored orphan
          // so the detail screen shows them as two separate standalone MVRs.
          final winnerUuid = response.data?['winner_mvr_uuid'] as String?;
          setState(() {
            if (winnerUuid != null && winnerUuid.isNotEmpty) {
              _overrideIndividualUuids = [winnerUuid, orphanedMvrUuid];
            } else {
              _overrideIndividualUuids = null;
            }
          });
          _loadCrossVideoData();
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Split failed: ${response.error ?? 'Unknown error'}'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Split failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Build small chip widget for compact info display
  Widget _buildSmallChip(String label, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.grey[200],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: Colors.grey[700]),
          const SizedBox(width: 2),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey[700],
            ),
          ),
        ],
      ),
    );
  }

  /// Build expanded section showing all person object appearances
  /// Appearances are grouped by camera/collection for better organization
  Widget _buildExpandedAppearances(AggregatedIndividualAnalysis analysis) {
    // Group appearances by camera/collection
    final Map<String, List<IndividualAppearance>> appearancesByCamera = {};
    for (final appearance in analysis.appearances) {
      final cameraKey = appearance.cameraName ?? appearance.cameraId ?? 'Unknown Camera';
      appearancesByCamera.putIfAbsent(cameraKey, () => []).add(appearance);
    }

    // Build sections for each camera/collection
    return Container(
      color: Theme.of(context).colorScheme.surface.withOpacity(0.3),
      child: ListView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        itemCount: appearancesByCamera.length,
        itemBuilder: (context, camIndex) {
          final cameraName = appearancesByCamera.keys.elementAt(camIndex);
          final appearances = appearancesByCamera[cameraName]!;
          
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Camera/Collection header
              if (appearancesByCamera.length > 1) // Only show header if multiple cameras
                Padding(
                  padding: EdgeInsets.only(left: 4, bottom: 8, top: camIndex > 0 ? 12 : 0),
                  child: Row(
                    children: [
                      Icon(Icons.videocam, size: 16, color: Colors.blue[700]),
                      const SizedBox(width: 6),
                      Text(
                        cameraName,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Colors.blue[700],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${appearances.length} appearance${appearances.length != 1 ? 's' : ''}',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
              // Appearance cards for this camera
              ...List.generate(
                appearances.length,
                (index) {
                  final appearance = appearances[index];
                  // Look up child MVR for this appearance
                  MergedMVRPerson? childMvr;
                  if (analysis.isSuperIndividual && appearance.mvrPeopleUuid != null) {
                    try {
                      childMvr = analysis.mergedMVRPeople.firstWhere(
                        (m) => m.mvrPeopleUuid == appearance.mvrPeopleUuid,
                      );
                    } catch (_) {}
                  }
                  final isLast = index == appearances.length - 1;
                  return Padding(
                    padding: EdgeInsets.only(bottom: isLast ? 0 : 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildAppearanceCard(appearance, index),
                        if (childMvr != null)
                          _buildAppearanceMvrRow(childMvr),
                      ],
                    ),
                  );
                },
              ),
            ],
          );
        },
      ),
    );
  }

  /// Compact MVR attribution row shown directly below an appearance card
  Widget _buildAppearanceMvrRow(MergedMVRPerson mvr) {
    return Container(
      margin: const EdgeInsets.only(left: 16, top: 2),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(8),
          bottomRight: Radius.circular(8),
        ),
        border: Border.all(color: Colors.blue.shade100),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      child: Row(
        children: [
          // Thumbnail
          ClipRRect(
            borderRadius: BorderRadius.circular(5),
            child: SizedBox(
              width: 34,
              height: 34,
              child: _buildChildMvrThumbnail(mvr.mvrPeopleUuid),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.badge, size: 13, color: Colors.blue[700]),
                    const SizedBox(width: 4),
                    Text(
                      'MVR ${mvr.mvrPeopleUuid.length >= 8 ? mvr.mvrPeopleUuid.substring(0, 8) : mvr.mvrPeopleUuid}...',
                      style: TextStyle(fontSize: 12, color: Colors.blue[800], fontWeight: FontWeight.w600),
                    ),
                    if (mvr.similarityToFeatured > 0) ...[
                      const SizedBox(width: 8),
                      Text(
                        mvr.formattedSimilarity,
                        style: TextStyle(fontSize: 11, color: Colors.blue[600]),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    if (mvr.gender != null) ...[
                      _buildSmallChip(mvr.gender!, Icons.person),
                      const SizedBox(width: 4),
                    ],
                    if (mvr.ageMin != null && mvr.ageMax != null) ...[
                      _buildSmallChip(mvr.ageRange, Icons.cake),
                      const SizedBox(width: 4),
                    ],
                    _buildSmallChip(
                      'Q:${(mvr.qualityScore * 100).toStringAsFixed(0)}%',
                      Icons.star,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build a single appearance card (same UX as individual card)
  Widget _buildAppearanceCard(IndividualAppearance appearance, int index) {
    return GestureDetector(
      onTap: () async {
        if (!mounted) {
          return;
        }
        final mediaItem = MediaItem(
          mediaId: '0',
          uuid: appearance.videoUuid,
          originalFilename: 'Loading...',
          mediaType: MediaType.video,
          fileSize: 0,
          filePath: '',
          uploadedAt: DateTime.now(),
          isPublic: false,
        );
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => ProviderScreenWrapper(
              child: EnhancedMediaPreviewScreen(mediaItem: mediaItem),
            ),
          ),
        );
      },
      child: Card(
        margin: EdgeInsets.zero,
        elevation: 1,
        color: Theme.of(context).cardColor,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              // Person object icon with play indicator
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: Colors.green.shade100,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    const Icon(
                      Icons.face,
                      size: 32,
                      color: Colors.green,
                    ),
                    Positioned(
                      bottom: 2,
                      right: 2,
                      child: Container(
                        padding: const EdgeInsets.all(2),
                        decoration: const BoxDecoration(
                          color: Colors.blue,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.play_arrow,
                          size: 12,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              // Appearance info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Appearance ${index + 1}',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Video: ${appearance.videoUuid.length >= 8 ? appearance.videoUuid.substring(0, 8) : appearance.videoUuid}...',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Object: ${appearance.personObjectUuid.length >= 8 ? appearance.personObjectUuid.substring(0, 8) : appearance.personObjectUuid}...',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11),
                    ),
                    const SizedBox(height: 6),
                    _buildStatChip('Start', _formatTimestamp(appearance.startTimestamp)),
                    const SizedBox(height: 2),
                    _buildStatChip('End', _formatTimestamp(appearance.endTimestamp)),
                    const SizedBox(height: 2),
                    _buildStatChip('Duration', appearance.formattedDuration),
                    const SizedBox(height: 2),
                    _buildStatChip('Confidence', '${(appearance.confidenceScore * 100).toStringAsFixed(0)}%'),
                  ],
                ),
              ),
              // Tap indicator icon
              Icon(
                Icons.chevron_right,
                color: Colors.grey[600],
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatChip(String label, String value) {
    return Row(
      children: [
        Text(
          '$label: ',
          style: TextStyle(color: Colors.grey[600], fontSize: 12),
        ),
        Text(
          value,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildQualityMetric(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 20, color: Colors.blue),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        Text(
          label,
          style: TextStyle(color: Colors.grey[600], fontSize: 10),
        ),
      ],
    );
  }

  String _formatDuration(int seconds) {
    if (seconds < 60) return '${seconds}s';
    if (seconds < 3600) return '${(seconds / 60).toStringAsFixed(1)}m';
    return '${(seconds / 3600).toStringAsFixed(1)}h';
  }

  /// Build Routes tab for cross-video mode
  Widget _buildRoutesTabCrossVideo() {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(child: Text('No appearance data available'));
    }

    // Use FutureBuilder to fetch route data from all videos
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _fetchCrossVideoRoutesData(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 16),
                Text('Loading route data from videos...'),
              ],
            ),
          );
        }

        if (snapshot.hasError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error, size: 64, color: Colors.red),
                const SizedBox(height: 16),
                Text('Error loading routes: ${snapshot.error}'),
              ],
            ),
          );
        }

        final personGroups = snapshot.data ?? const <Map<String, dynamic>>[];
        final cameraIds = _getRouteCameraIds();
        final hasAnyRouteData = _hasAnyRouteDataInSelection();

        if (!hasAnyRouteData) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.route_outlined, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No route data available'),
                SizedBox(height: 8),
                Text(
                  'Route data could not be loaded from videos',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ),
          );
        }
        final selectedCameraId = _selectedRouteCameraId;
        final selectedCameraName = selectedCameraId == null
            ? null
            : _routeCameraNamesById[selectedCameraId] ?? selectedCameraId;
        final selectedCameraLoaded = selectedCameraId == null
            ? 0
            : _getLoadedPointsForCamera(selectedCameraId);
        final selectedCameraTotal = selectedCameraId == null
            ? 0
            : _getTotalPointsForCamera(selectedCameraId);

        return SingleChildScrollView(
          child: Column(
            children: [
              // Routes visualization header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    const Icon(Icons.route, color: Colors.blue),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Cross-Video Movement Routes',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text(
                            'Routes across ${cameraIds.length} camera(s)',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey[600],
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            selectedCameraId == null
                                ? 'No camera selected'
                                : 'Selected: $selectedCameraName • Loaded $selectedCameraLoaded / $selectedCameraTotal points',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey[700],
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (selectedCameraId != null &&
                        _cameraHasMoreRoutes(selectedCameraId))
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ElevatedButton.icon(
                          onPressed: _isLoadingMoreCrossVideoRoutes
                              ? null
                              : () => _loadMoreCrossVideoRoutes(selectedCameraId),
                          icon: _isLoadingMoreCrossVideoRoutes
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.expand_more, size: 16),
                          label: Text(
                            _isLoadingMoreCrossVideoRoutes
                                ? 'Loading...'
                                : 'Load more routes',
                          ),
                        ),
                      ),
                    // Display mode toggle
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey.shade300),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.visibility, size: 16, color: Colors.grey),
                          const SizedBox(width: 4),
                          DropdownButton<String>(
                            value: _routesDisplayMode,
                            isDense: true,
                            underline: Container(),
                            items: const [
                              DropdownMenuItem(
                                value: 'path',
                                child: Row(
                                  children: [
                                    Icon(Icons.timeline, size: 16),
                                    SizedBox(width: 4),
                                    Text('Path'),
                                  ],
                                ),
                              ),
                              DropdownMenuItem(
                                value: 'scatter',
                                child: Row(
                                  children: [
                                    Icon(Icons.scatter_plot, size: 16),
                                    SizedBox(width: 4),
                                    Text('Scatter'),
                                  ],
                                ),
                              ),
                            ],
                            onChanged: (String? newValue) {
                              if (newValue != null) {
                                setState(() {
                                  _routesDisplayMode = newValue;
                                });
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              if (cameraIds.isNotEmpty)
                Container(
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: _buildRouteCameraSelector(cameraIds),
                ),

              if (selectedCameraId != null)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  margin: const EdgeInsets.only(top: 8),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    border: Border(
                      left: BorderSide(color: Colors.blue.shade700, width: 4),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.videocam, size: 18, color: Colors.blue[700]),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          selectedCameraName ?? selectedCameraId,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: Colors.blue[700],
                          ),
                        ),
                      ),
                      Text(
                        '${personGroups.length} individual${personGroups.length == 1 ? '' : 's'}',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),

              if (selectedCameraId != null) ...[
                const SizedBox(height: 8),
                if (personGroups.isEmpty)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey.shade300),
                    ),
                    child: Text(
                      'No route points have been loaded for this camera yet. If route metadata exists, the loader will keep scanning later pages automatically.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  )
                else ...[
                  _buildCrossVideoRoutesCanvas(personGroups),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: _buildRoutesLegend(personGroups),
                  ),
                ],
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildCrossVideoRoutesCanvas(List<Map<String, dynamic>> personGroups) {
    // Use standard video dimensions for cross-video routes
    const frameDimensions = Size(1920, 1080);
    
    return Column(
      children: [
        // ROW 1: Camera View
        Container(
          height: frameDimensions.height + 56,
          child: Column(
            children: [
              // Camera view header
              Container(
                height: 40,
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.videocam, size: 16, color: Colors.blue),
                    const SizedBox(width: 4),
                    Text(
                      'Unified Camera View (${frameDimensions.width.toInt()}×${frameDimensions.height.toInt()}px)',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
              
              // Camera view container
              Center(
                child: Container(
                  width: frameDimensions.width,
                  height: frameDimensions.height,
                  decoration: BoxDecoration(
                    color: Colors.black12,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: CustomPaint(
                      painter: RoutesPainter(
                        personGroups,
                        frameDimensions: frameDimensions,
                        displayMode: _routesDisplayMode,
                      ),
                      size: Size(frameDimensions.width, frameDimensions.height),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        
        const SizedBox(height: 16),
        
        // ROW 2: Top View
        Container(
          height: frameDimensions.height + 56,
          child: Column(
            children: [
              // Top view header
              Container(
                height: 40,
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.map, size: 16, color: Colors.green),
                    const SizedBox(width: 4),
                    Text(
                      'Unified Top View (${frameDimensions.height.toInt()}×${frameDimensions.height.toInt()}px)',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
              
              // Top view container
              Center(
                child: Container(
                  width: frameDimensions.height,
                  height: frameDimensions.height,
                  decoration: BoxDecoration(
                    color: Colors.black12,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: CustomPaint(
                      painter: TopViewRoutesPainter(
                        personGroups,
                        displayMode: _routesDisplayMode,
                      ),
                      size: Size(frameDimensions.height, frameDimensions.height),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  /// Fetch route data from all videos in cross-video appearances
  Future<List<Map<String, dynamic>>> _fetchCrossVideoRoutesData() async {
    if (_crossVideoRoutesFetchInFlight != null) {
      return _crossVideoRoutesFetchInFlight!;
    }

    _crossVideoRoutesFetchInFlight = _fetchCrossVideoRoutesDataInternal();
    try {
      return await _crossVideoRoutesFetchInFlight!;
    } finally {
      _crossVideoRoutesFetchInFlight = null;
    }
  }

  Future<List<Map<String, dynamic>>> _fetchCrossVideoRoutesDataInternal() async {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return [];
    }

    final apiClient = ref.read(apiClientProvider);
    final routesClient = IndividualGroupsApiClient(apiClient);

    developer.log('🗺️ ROUTES DEBUG: Starting route fetch for ${_aggregatedAnalyses!.length} analyses');
    developer.log('🗺️ ROUTES DEBUG: hasRouteSearchScopeFilter=${_hasRouteSearchScopeFilter()}');
    developer.log('🗺️ ROUTES DEBUG: sessionData source=${widget.crossVideoContext?.sessionData['source']}');
    final searchParams = _getRouteSearchParams();
    if (searchParams != null) {
      developer.log('🗺️ ROUTES DEBUG: search_parameters keys=${searchParams.keys.toList()}');
      developer.log('🗺️ ROUTES DEBUG: camera_uuids=${searchParams['camera_uuids']}');
      developer.log('🗺️ ROUTES DEBUG: camera_ids=${searchParams['camera_ids']}');
    }

    for (final analysis in _aggregatedAnalyses!) {
      _routeDisplayPersonIdByUuid[analysis.individualUuid] = analysis.individualId;

      final sourceIndividualUuids = _resolveRouteSourceIndividualUuids(analysis);
      developer.log('🗺️ ROUTES DEBUG: analysis.individualUuid=${analysis.individualUuid}');
      developer.log('🗺️ ROUTES DEBUG: analysis.individualId=${analysis.individualId}');
      developer.log('🗺️ ROUTES DEBUG: sourceUuids=$sourceIndividualUuids');

      for (final sourceUuid in sourceIndividualUuids) {
        if (_loadedRouteSourceIndividuals.contains(sourceUuid)) {
          continue;
        }

        developer.log('🗺️ ROUTES DEBUG: Fetching metadata for sourceUuid=$sourceUuid');
        // Do NOT pass time filters here.  The routes tab shows the
        // super-individual's complete movement history.  The search window
        // determined which individuals to analyse, but must not restrict which
        // of their appearances are included in the routes visualisation.  The
        // MVR path works because its search_parameters often has null
        // start/end time (no date filter); the individual-groups path always
        // has a non-null window, which caused the metadata call to return 0
        // points for appearances that straddle the search boundary.
        developer.log('🗺️ ROUTES DEBUG: fetching metadata with no time filter (complete history)');
        final metadataResp = await routesClient.getIndividualRoutesMetadataByCamera(
          individualUuid: sourceUuid,
        );
        developer.log('🗺️ ROUTES DEBUG: metadata success=${metadataResp.success}');
        if (metadataResp.success && metadataResp.data != null) {
          developer.log('🗺️ ROUTES DEBUG: metadata raw=${metadataResp.data}');
          final allMetadataCameras =
              (metadataResp.data!['cameras'] as List<dynamic>? ?? [])
                  .whereType<Map<String, dynamic>>()
                  .toList();
          developer.log('🗺️ ROUTES DEBUG: allMetadataCameras count=${allMetadataCameras.length}');
          for (final c in allMetadataCameras) {
            developer.log('🗺️ ROUTES DEBUG:   camera_id=${c['camera_id']}, camera_name=${c['camera_name']}, total_points=${c['total_points']}');
            developer.log('🗺️ ROUTES DEBUG:   inScope=${_isCameraInSearchScope((c['camera_id'] ?? '').toString(), (c['camera_name'] ?? '').toString())}');
          }
          // Do NOT scope-filter cameras here.  The routes tab is an analysis
          // of the super-individual's complete movement history and must
          // include all appearances, including those from cameras that have
          // since been deleted, renamed, or are otherwise inactive.  A scope
          // filter based on collection UUIDs would silently discard any
          // appearance whose originating collection can no longer be resolved
          // by the media-search API (it falls back to a raw video UUID that
          // never matches a stored collection UUID).
          final metadataCameras = allMetadataCameras;
          _registerCameraMetadata(
            analysis: analysis,
            sourceIndividualUuid: sourceUuid,
            cameraMetadata: metadataCameras,
          );
        }

        await _bootstrapRoutePagesForSource(
          routesClient: routesClient,
          analysis: analysis,
          sourceIndividualUuid: sourceUuid,
        );

        _loadedRouteSourceIndividuals.add(sourceUuid);
      }
    }

    final cameraIds = _getRouteCameraIds();
    developer.log('🗺️ ROUTES DEBUG: Final cameraIds=$cameraIds');
    developer.log('🗺️ ROUTES DEBUG: hasAnyRouteData=${_hasAnyRouteDataInSelection()}');
    developer.log('🗺️ ROUTES DEBUG: _routeHasMoreByCameraSource=$_routeHasMoreByCameraSource');
    developer.log('🗺️ ROUTES DEBUG: _routeTotalPointsByCameraSource=$_routeTotalPointsByCameraSource');
    for (final camId in _routePointsByCamera.keys) {
      for (final indvId in _routePointsByCamera[camId]!.keys) {
        developer.log('🗺️ ROUTES DEBUG: cam=$camId indv=$indvId pointCount=${_routePointsByCamera[camId]![indvId]!.length}');
      }
    }
    if (cameraIds.isNotEmpty &&
        (_selectedRouteCameraId == null ||
            !_getRouteCameraIds().contains(_selectedRouteCameraId))) {
      _selectedRouteCameraId = cameraIds.firstWhere(
        (cameraId) => _getTotalPointsForCamera(cameraId) > 0,
        orElse: () => cameraIds.first,
      );
    }

    return _buildSelectedCameraPersonGroups();
  }

  String _routePointKey(Map<String, dynamic> point) {
    final personObjectUuid = (point['person_object_uuid'] ?? '').toString();
    final sequence = (point['sequence_number'] ?? '').toString();
    final timestamp = (point['timestamp'] ?? point['timestamp_ms'] ?? '').toString();
    return '$personObjectUuid|$sequence|$timestamp';
  }

  /// Returns the search_parameters map from the cross-video session data, or null.
  Map<String, dynamic>? _getRouteSearchParams() {
    if (widget.crossVideoContext == null) return null;
    return widget.crossVideoContext!.sessionData['search_parameters']
        as Map<String, dynamic>?;
  }

  /// Start of the search time range in milliseconds, or null if unset.
  int? _getRouteSearchStartTimeMs() {
    final params = _getRouteSearchParams();
    if (params == null) return null;
    final startTime = params['start_time'] as String?;
    if (startTime == null) return null;
    return DateTime.tryParse(startTime)?.millisecondsSinceEpoch;
  }

  /// End of the search time range in milliseconds, or null if unset.
  int? _getRouteSearchEndTimeMs() {
    final params = _getRouteSearchParams();
    if (params == null) return null;
    final endTime = params['end_time'] as String?;
    if (endTime == null) return null;
    final parsed = DateTime.tryParse(endTime);
    if (parsed == null) return null;
    // If the stored end-time is today (same local date), snap to end-of-day so
    // videos processed after the user clicked the quick-filter are still included.
    final now = DateTime.now();
    if (parsed.year == now.year &&
        parsed.month == now.month &&
        parsed.day == now.day) {
      return DateTime(parsed.year, parsed.month, parsed.day, 23, 59, 59, 999)
          .millisecondsSinceEpoch;
    }
    return parsed.millisecondsSinceEpoch;
  }

  /// Returns the list of camera IDs that were selected for the search, or null
  /// if no camera filter was applied (= all cameras).
  List<String>? _getRouteSearchCameraIds() {
    final params = _getRouteSearchParams();
    if (params == null) return null;
    final cameraIds = params['camera_ids'] as List<dynamic>?;
    if (cameraIds != null && cameraIds.isNotEmpty) {
      return cameraIds.map((e) => e.toString()).toList();
    }
    final cameraId = params['camera_id'] as String?;
    if (cameraId != null && cameraId.isNotEmpty) {
      return [cameraId];
    }
    return null;
  }

  /// Returns true if there is any camera scope restriction for route data.
  bool _hasRouteSearchScopeFilter() {
    final sessionData = widget.crossVideoContext?.sessionData;
    if (sessionData == null) return false;

    // Collection-based search: sessionData['collection_id'] or ['collection_ids']
    final collectionId = sessionData['collection_id']?.toString();
    if (collectionId != null && collectionId.isNotEmpty) return true;
    final collectionIds = sessionData['collection_ids'] as List?;
    if (collectionIds != null && collectionIds.isNotEmpty) return true;

    // Camera-based search via search_parameters
    final params = _getRouteSearchParams();
    if (params == null) return false;
    if ((params['camera_uuids'] as List?)?.isNotEmpty == true) return true;
    if ((params['camera_ids'] as List?)?.isNotEmpty == true) return true;
    if ((params['camera_id'] as String?)?.isNotEmpty == true) return true;
    return false;
  }

  /// Returns true if [cameraId] (UUID) / [cameraName] is within the camera
  /// scope of the original search.  Compares both UUID and display name
  /// against all stored forms of camera identifier so mismatches between
  /// name-based and UUID-based identifiers are handled gracefully.
  bool _isCameraInSearchScope(String cameraId, String cameraName) {
    final sessionData = widget.crossVideoContext?.sessionData;
    if (sessionData == null) return true; // no context → no restriction

    // Helper: compare value against both cameraId and cameraName
    // Use case-insensitive comparison for both to handle UUID case differences
    // between the collections API and media search API (route data resolution).
    final cameraIdLower = cameraId.toLowerCase();
    final cameraNameLower = cameraName.toLowerCase();
    bool matches(String v) {
      final vLower = v.toLowerCase();
      return vLower == cameraIdLower || vLower == cameraNameLower;
    }

    // 1. Single collection (collection-based search, top-level sessionData)
    final collectionId = sessionData['collection_id']?.toString() ?? '';
    if (collectionId.isNotEmpty && matches(collectionId)) return true;

    // 2. Multiple collections (top-level sessionData)
    final collectionIds = sessionData['collection_ids'] as List?;
    if (collectionIds != null) {
      if (collectionIds.any((id) => matches(id.toString()))) return true;
    }

    final params = _getRouteSearchParams();
    if (params == null) return false;

    // 3. camera_uuids (new — UUIDs stored alongside names for route filtering)
    final cameraUuids = params['camera_uuids'] as List?;
    if (cameraUuids != null && cameraUuids.isNotEmpty) {
      if (cameraUuids.any((id) => matches(id.toString()))) return true;
    }

    // 4. camera_ids (may contain names OR UUIDs — match against both fields)
    final cameraIds = params['camera_ids'] as List?;
    if (cameraIds != null && cameraIds.isNotEmpty) {
      if (cameraIds.any((id) => matches(id.toString()))) return true;
    }

    // 5. Single camera_id
    final singleId = params['camera_id']?.toString() ?? '';
    if (singleId.isNotEmpty && matches(singleId)) return true;

    return false;
  }

  void _registerCameraMetadata({
    required AggregatedIndividualAnalysis analysis,
    required String sourceIndividualUuid,
    required List<Map<String, dynamic>> cameraMetadata,
  }) {
    for (final camera in cameraMetadata) {
      final cameraId = (camera['camera_id'] ?? '').toString();
      if (cameraId.isEmpty) {
        continue;
      }

      final cameraName = (camera['camera_name'] ?? cameraId).toString();
      final totalPoints = (camera['total_points'] as num?)?.toInt() ?? 0;

      _routeCameraNamesById[cameraId] = cameraName;
      _routeDisplayIndividualByCameraSource
          .putIfAbsent(cameraId, () => {})[sourceIndividualUuid] =
          analysis.individualUuid;
      _routePageIndexByCameraSource.putIfAbsent(cameraId, () => {});
      _routeHasMoreByCameraSource.putIfAbsent(cameraId, () => {});
      _routeTotalPointsByCameraSource.putIfAbsent(cameraId, () => {});
      _routeTotalPointsByCameraSource[cameraId]![sourceIndividualUuid] =
          totalPoints;
      _routeHasMoreByCameraSource[cameraId]![sourceIndividualUuid] =
          totalPoints > 0;
    }
  }

  Future<void> _bootstrapRoutePagesForSource({
    required IndividualGroupsApiClient routesClient,
    required AggregatedIndividualAnalysis analysis,
    required String sourceIndividualUuid,
  }) async {
    final candidateCameraIds = _routeDisplayIndividualByCameraSource.entries
        .where((entry) => entry.value.containsKey(sourceIndividualUuid))
        .map((entry) => entry.key)
        .toList();

    developer.log('🗺️ BOOTSTRAP DEBUG: sourceUuid=$sourceIndividualUuid, candidateCameraIds=$candidateCameraIds');
    developer.log('🗺️ BOOTSTRAP DEBUG: _routeDisplayIndividualByCameraSource=${_routeDisplayIndividualByCameraSource}');

    if (candidateCameraIds.isEmpty) {
      developer.log('🗺️ BOOTSTRAP DEBUG: No candidates! Falling back to generic fetch');
      final firstPageResp = await routesClient.getIndividualRoutesByCamera(
        individualUuid: sourceIndividualUuid,
        pageIndex: 0,
        pageSize: _routePageSize,
        // No time filter — complete history (see metadata call comment above).
      );
      if (!firstPageResp.success || firstPageResp.data == null) {
        return;
      }

      final cameras = (firstPageResp.data!['cameras'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .toList();
      developer.log('🗺️ BOOTSTRAP DEBUG: Generic fetch returned ${cameras.length} camera groups');
      for (final cameraGroup in cameras) {
        developer.log('🗺️ BOOTSTRAP DEBUG: camera_id=${cameraGroup['camera_id']}, has individuals=${(cameraGroup['individuals'] as List?)?.length}');
        _appendCameraGroupedRoutePage(
          analysis: analysis,
          sourceIndividualUuid: sourceIndividualUuid,
          cameraGroup: cameraGroup,
        );
      }
      developer.log('🗺️ BOOTSTRAP DEBUG: After generic fetch: _routeHasMoreByCameraSource=$_routeHasMoreByCameraSource');
      developer.log('🗺️ BOOTSTRAP DEBUG: After generic fetch: _routeTotalPointsByCameraSource=$_routeTotalPointsByCameraSource');
      developer.log('🗺️ BOOTSTRAP DEBUG: After generic fetch: _routePointsByCamera keys=${_routePointsByCamera.keys.toList()}');
      return;
    }

    for (final cameraId in candidateCameraIds) {
      final totalPoints =
          _routeTotalPointsByCameraSource[cameraId]?[sourceIndividualUuid] ?? 0;
      developer.log('🗺️ BOOTSTRAP DEBUG: Per-camera fetch: cameraId=$cameraId, totalPoints=$totalPoints');
      if (totalPoints <= 0) {
        continue;
      }

      // Only fetch page 0.  Subsequent pages are loaded on demand via the
      // "Load more routes" button.  The old loop over maxPageIndex was causing
      // a request flood: with 4 800 total points and pageSize=100 it fired
      // 47 sequential requests — each of which made the backend re-fetch the
      // entire dataset and re-run per-video orchestrator calls.
      final pageResp = await routesClient.getIndividualRoutesByCamera(
        individualUuid: sourceIndividualUuid,
        cameraId: cameraId,
        pageIndex: 0,
        pageSize: _routePageSize,
        // No time filter — complete history (see metadata call comment above).
      );
      if (!pageResp.success || pageResp.data == null) {
        continue;
      }

      final cameras = (pageResp.data!['cameras'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .toList();
      for (final cameraGroup in cameras) {
        _appendCameraGroupedRoutePage(
          analysis: analysis,
          sourceIndividualUuid: sourceIndividualUuid,
          cameraGroup: cameraGroup,
        );
      }
      developer.log('🗺️ BOOTSTRAP DEBUG: page-0 fetch done for cameraId=$cameraId, cameras=${cameras.length}');
    }
  }

  void _appendCameraGroupedRoutePage({
    required AggregatedIndividualAnalysis analysis,
    required String sourceIndividualUuid,
    required Map<String, dynamic> cameraGroup,
  }) {
    final cameraId = (cameraGroup['camera_id'] ?? '').toString();
    if (cameraId.isEmpty) {
      return;
    }

    // No camera-scope filter applied.  The routes analysis covers the
    // super-individual's full appearance history.  Appearances captured by
    // cameras that no longer exist are still valid route data and must not
    // be discarded (their camera_id falls back to a raw video UUID when the
    // originating collection cannot be resolved, so collection-UUID matching
    // would always reject them).

    final cameraName = (cameraGroup['camera_name'] ?? cameraId).toString();
    _routeCameraNamesById[cameraId] = cameraName;
    _routeDisplayIndividualByCameraSource
        .putIfAbsent(cameraId, () => {})[sourceIndividualUuid] =
        analysis.individualUuid;

    final individuals = (cameraGroup['individuals'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>();
    for (final individualGroup in individuals) {
      final page = individualGroup['page'] as Map<String, dynamic>? ?? {};
      final pageIndex = (page['page_index'] as num?)?.toInt() ?? 0;
      final hasMore = page['has_more'] as bool? ?? false;
      final totalPoints =
          (page['total_points'] as num?)?.toInt() ??
          (individualGroup['total_points'] as num?)?.toInt() ??
          0;

      _routePageIndexByCameraSource
          .putIfAbsent(cameraId, () => {})[sourceIndividualUuid] = pageIndex;
      _routeHasMoreByCameraSource
          .putIfAbsent(cameraId, () => {})[sourceIndividualUuid] = hasMore;
      _routeTotalPointsByCameraSource
          .putIfAbsent(cameraId, () => {})[sourceIndividualUuid] = totalPoints;

      final points = (individualGroup['points'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map((point) => _normalizeRoutePoint(point, cameraId, cameraName))
          .toList();

      _routePointsByCamera.putIfAbsent(cameraId, () => {});
      _routePointsByCamera[cameraId]!
          .putIfAbsent(analysis.individualUuid, () => []);
      final existingPoints = _routePointsByCamera[cameraId]![analysis.individualUuid]!;
      final existingKeys = existingPoints.map(_routePointKey).toSet();
      for (final point in points) {
        final key = _routePointKey(point);
        if (existingKeys.add(key)) {
          existingPoints.add(point);
        }
      }
    }
  }

  Map<String, dynamic> _normalizeRoutePoint(
    Map<String, dynamic> point,
    String cameraId,
    String cameraName,
  ) {
    return <String, dynamic>{
      'sequence_number': (point['sequence_number'] as num?)?.toInt() ?? 0,
      'timestamp': (point['timestamp_ms'] as num?)?.toInt() ?? 0,
      'frame_number': (point['sequence_number'] as num?)?.toInt() ?? 0,
      'center_x': (point['center_x'] as num?)?.toDouble() ?? 0.0,
      'center_y': (point['center_y'] as num?)?.toDouble() ?? 0.0,
      'velocity_x': (point['velocity_x'] as num?)?.toDouble() ?? 0.0,
      'velocity_y': (point['velocity_y'] as num?)?.toDouble() ?? 0.0,
      'velocity_magnitude':
          (point['velocity_magnitude'] as num?)?.toDouble() ?? 0.0,
      'camera_id': cameraId,
      'camera_name': cameraName,
      'video_uuid': point['video_uuid'],
      'person_object_uuid': point['person_object_uuid'],
      'individual_uuid': point['individual_uuid'],
    };
  }

  List<String> _getRouteCameraIds() {
    final ids = {
      ..._routeCameraNamesById.keys,
      ..._routeTotalPointsByCameraSource.keys,
      ..._routePointsByCamera.keys,
    }.toList()
      ..sort();
    return ids;
  }

  bool _hasAnyRouteDataInSelection() {
    return _routeTotalPointsByCameraSource.values.any(
      (sourceTotals) => sourceTotals.values.any((count) => count > 0),
    );
  }

  List<Map<String, dynamic>> _buildSelectedCameraPersonGroups() {
    final selectedCameraId = _selectedRouteCameraId;
    if (selectedCameraId == null) {
      return [];
    }

    final cameraName =
        _routeCameraNamesById[selectedCameraId] ?? selectedCameraId;
    final cameraPoints = _routePointsByCamera[selectedCameraId] ?? {};
    final personGroups = <Map<String, dynamic>>[];

    for (final analysis in _aggregatedAnalyses!) {
      final rawPoints = cameraPoints[analysis.individualUuid] ?? [];
      if (rawPoints.isEmpty) {
        continue;
      }

      rawPoints.sort((a, b) {
        final timestampA = a['timestamp'] as num? ?? 0;
        final timestampB = b['timestamp'] as num? ?? 0;
        return timestampA.compareTo(timestampB);
      });

      personGroups.add({
        'person_id': _routeDisplayPersonIdByUuid[analysis.individualUuid] ??
            analysis.individualId,
        'camera_id': selectedCameraId,
        'camera_name': cameraName,
        'total_detections': rawPoints.length,
        'sampled_points': rawPoints.length,
        'movement_tracking': {
          'route_points': rawPoints,
          'total_distance': 0.0,
          'movement_duration': analysis.totalDurationSeconds,
        },
      });
    }

    return personGroups;
  }

  List<String> _resolveRouteSourceIndividualUuids(
    AggregatedIndividualAnalysis analysis,
  ) {
    // Always use individualId (the MVR/super UUID).
    // - In camera-search results: individualUuid = raw individual, individualId = MVR/super UUID.
    // - In hierarchy results: both are the super UUID.
    // The backend expands the super UUID to all linked raw individuals via mvr_merge_hierarchy.
    final resolvedUuid = analysis.individualId.isNotEmpty
        ? analysis.individualId
        : analysis.individualUuid;
    debugPrint('🗺️ Route UUID for ${analysis.individualUuid}: '
        'isSuperIndividual=${analysis.isSuperIndividual}, '
        'individualId=${analysis.individualId} → using $resolvedUuid');
    return [resolvedUuid];
  }

  Widget _buildRouteCameraSelector(List<String> cameraIds) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: cameraIds.map((cameraId) {
          final isSelected = cameraId == _selectedRouteCameraId;
          final cameraName = _routeCameraNamesById[cameraId] ?? cameraId;
          final totalPoints = _getTotalPointsForCamera(cameraId);
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text('$cameraName ($totalPoints pts)'),
              selected: isSelected,
              onSelected: (_) {
                setState(() {
                  _selectedRouteCameraId = cameraId;
                });
              },
            ),
          );
        }).toList(),
      ),
    );
  }

  int _getLoadedPointsForCamera(String cameraId) {
    final cameraGroups = _routePointsByCamera[cameraId] ?? {};
    return cameraGroups.values.fold<int>(0, (sum, points) => sum + points.length);
  }

  int _getTotalPointsForCamera(String cameraId) {
    final sourceTotals = _routeTotalPointsByCameraSource[cameraId] ?? {};
    return sourceTotals.values.fold<int>(0, (sum, count) => sum + count);
  }

  bool _cameraHasMoreRoutes(String cameraId) {
    final sourceHasMore = _routeHasMoreByCameraSource[cameraId] ?? {};
    return sourceHasMore.values.any((value) => value);
  }

  Future<void> _loadMoreCrossVideoRoutes(String cameraId) async {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return;
    }
    if (_isLoadingMoreCrossVideoRoutes) {
      return;
    }

    setState(() {
      _isLoadingMoreCrossVideoRoutes = true;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final routesClient = IndividualGroupsApiClient(apiClient);

      for (final analysis in _aggregatedAnalyses!) {
        final sourceIndividualUuids = _resolveRouteSourceIndividualUuids(analysis);
        for (final sourceUuid in sourceIndividualUuids) {
          final hasMore =
              _routeHasMoreByCameraSource[cameraId]?[sourceUuid] ?? false;
          if (!hasMore) {
            continue;
          }

          final currentPage =
              _routePageIndexByCameraSource[cameraId]?[sourceUuid] ?? 0;
          final nextPage = currentPage + 1;

          final pageResp = await routesClient.getIndividualRoutesByCamera(
            individualUuid: sourceUuid,
            cameraId: cameraId,
            pageIndex: nextPage,
            pageSize: _routePageSize,
            // No time filter — complete history (see metadata call comment above).
          );

          if (!pageResp.success || pageResp.data == null) {
            continue;
          }

          final cameras = (pageResp.data!['cameras'] as List<dynamic>? ?? [])
              .whereType<Map<String, dynamic>>()
              .toList();
          for (final cameraGroup in cameras) {
            _appendCameraGroupedRoutePage(
              analysis: analysis,
              sourceIndividualUuid: sourceUuid,
              cameraGroup: cameraGroup,
            );
          }
        }
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingMoreCrossVideoRoutes = false;
        });
      }
    }
  }

  String _formatTimestamp(dynamic timestamp) {
    try {
      DateTime dt;
      if (timestamp is String) {
        dt = DateTime.parse(timestamp);
      } else if (timestamp is DateTime) {
        dt = timestamp;
      } else {
        return timestamp.toString();
      }
      
      // Day of week (e.g., "Tue")
      final dayOfWeek = _getDayOfWeek(dt.weekday);
      
      // Day of month (e.g., "21")
      final day = dt.day;
      
      // Month (e.g., "Dec.")
      final month = _getMonthAbbreviation(dt.month);
      
      // Year (e.g., "2025")
      final year = dt.year;
      
      // Hour in 12-hour format
      final hour = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
      
      // Minute with leading zero
      final minute = dt.minute.toString().padLeft(2, '0');
      
      // AM/PM
      final period = dt.hour >= 12 ? 'pm' : 'am';
      
      return '$dayOfWeek $day $month $year, $hour:$minute $period';
    } catch (e) {
      return timestamp.toString();
    }
  }

  /// Get day of week abbreviation
  String _getDayOfWeek(int weekday) {
    switch (weekday) {
      case 1: return 'Mon';
      case 2: return 'Tue';
      case 3: return 'Wed';
      case 4: return 'Thu';
      case 5: return 'Fri';
      case 6: return 'Sat';
      case 7: return 'Sun';
      default: return '';
    }
  }

  /// Get month abbreviation
  String _getMonthAbbreviation(int month) {
    switch (month) {
      case 1: return 'Jan.';
      case 2: return 'Feb.';
      case 3: return 'Mar.';
      case 4: return 'Apr.';
      case 5: return 'May';
      case 6: return 'Jun.';
      case 7: return 'Jul.';
      case 8: return 'Aug.';
      case 9: return 'Sep.';
      case 10: return 'Oct.';
      case 11: return 'Nov.';
      case 12: return 'Dec.';
      default: return '';
    }
  }

  /// Build Statistics tab for cross-video mode
  Widget _buildStatisticsTabCrossVideo() {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(child: Text('No statistics available'));
    }

    // Calculate aggregate statistics across all individuals
    int totalAppearances = 0;
    int totalUniqueVideos = 0;
    double sumConfidence = 0;
    double totalDurationSeconds = 0;
    double totalVelocity = 0;
    int velocityCount = 0;
    DateTime? earliestSeen;
    DateTime? latestSeen;
    
    // Aggregate demographics and video data from search results (MVR people data)
    int totalMale = 0;
    int totalFemale = 0;
    int totalUnknown = 0;
    List<double> ages = [];
    List<double> confidenceScores = [];
    bool hasDemographics = false;
    
    // Extract video time span and duration from search results
    DateTime? searchStartTime;
    DateTime? searchEndTime;
    double totalVideoDurationSeconds = 0;
    
    // Try to get search parameters from sessionData
    final searchParams = widget.crossVideoContext!.sessionData['search_parameters'];
    if (searchParams != null) {
      if (searchParams['start_time'] != null) {
        try {
          searchStartTime = DateTime.parse(searchParams['start_time'] as String);
        } catch (e) {
          print('Error parsing start_time: $e');
        }
      }
      if (searchParams['end_time'] != null) {
        try {
          searchEndTime = DateTime.parse(searchParams['end_time'] as String);
        } catch (e) {
          print('Error parsing end_time: $e');
        }
      }
    }
    
    // Calculate total video duration from MVR people appearances
    // Use a Set to track unique video UUIDs to avoid double-counting
    final Set<String> processedVideos = {};
    
    if (widget.crossVideoContext!.sessionData['search_results'] != null) {
      final searchResults = widget.crossVideoContext!.sessionData['search_results'] as List<dynamic>;
      
      // For each MVR person, check their appearances
      for (final mvrPerson in searchResults) {
        final appearances = mvrPerson['appearances'] as List<dynamic>?;
        if (appearances != null) {
          for (final appearance in appearances) {
            // Calculate duration from timestamps
            final startStr = appearance['start_timestamp'] as String?;
            final endStr = appearance['end_timestamp'] as String?;
            final videoUuid = appearance['video_uuid'] as String?;
            
            if (startStr != null && endStr != null && videoUuid != null) {
              try {
                final start = DateTime.parse(startStr);
                final end = DateTime.parse(endStr);
                final durationSecs = end.difference(start).inSeconds.toDouble();
                
                // For total video duration, we want the sum of all unique video segments
                // Track by video_uuid + start_timestamp to get unique segments
                final segmentKey = '$videoUuid-$startStr';
                if (!processedVideos.contains(segmentKey)) {
                  totalVideoDurationSeconds += durationSecs;
                  processedVideos.add(segmentKey);
                }
              } catch (e) {
                print('Error parsing timestamps: $e');
              }
            }
          }
        }
      }
    }

    // Extract demographics from search results if available
    if (widget.crossVideoContext!.sessionData['search_results'] != null) {
      final searchResults = widget.crossVideoContext!.sessionData['search_results'] as List<dynamic>;
      
      for (final mvrPerson in searchResults) {
        // Parse gender
        final gender = mvrPerson['estimated_gender'] as String?;
        if (gender != null) {
          hasDemographics = true;
          if (gender.toLowerCase() == 'male') {
            totalMale++;
          } else if (gender.toLowerCase() == 'female') {
            totalFemale++;
          } else {
            totalUnknown++;
          }
        } else {
          totalUnknown++;
        }
        
        // Parse age (format: "33-43")
        final ageStr = mvrPerson['estimated_age'] as String?;
        if (ageStr != null && ageStr.contains('-')) {
          final parts = ageStr.split('-');
          if (parts.length == 2) {
            final minAge = int.tryParse(parts[0]);
            final maxAge = int.tryParse(parts[1]);
            if (minAge != null && maxAge != null) {
              ages.add((minAge + maxAge) / 2.0);
            }
          }
        }
        
        // Parse confidence score
        final confidenceScore = mvrPerson['confidence_score'] as num?;
        if (confidenceScore != null) {
          confidenceScores.add(confidenceScore.toDouble());
        }
        
        // Calculate velocity for this MVR person (appearances per minute)
        final totalAppearancesForPerson = mvrPerson['total_appearances'] as int?;
        final appearances = mvrPerson['appearances'] as List<dynamic>?;
        
        if (totalAppearancesForPerson != null && appearances != null && appearances.isNotEmpty) {
          // Calculate total time span for this person's appearances
          DateTime? firstAppearance;
          DateTime? lastAppearance;
          
          for (final appearance in appearances) {
            final startStr = appearance['start_timestamp'] as String?;
            final endStr = appearance['end_timestamp'] as String?;
            
            if (startStr != null && endStr != null) {
              try {
                final start = DateTime.parse(startStr);
                final end = DateTime.parse(endStr);
                
                if (firstAppearance == null || start.isBefore(firstAppearance)) {
                  firstAppearance = start;
                }
                if (lastAppearance == null || end.isAfter(lastAppearance)) {
                  lastAppearance = end;
                }
              } catch (e) {
                // Skip invalid timestamps
              }
            }
          }
          
          // Calculate velocity: appearances per minute over the time span
          if (firstAppearance != null && lastAppearance != null) {
            final timeSpanMinutes = lastAppearance.difference(firstAppearance).inMinutes.toDouble();
            if (timeSpanMinutes > 0 && totalAppearancesForPerson > 0) {
              final velocity = totalAppearancesForPerson / timeSpanMinutes;
              totalVelocity += velocity;
              velocityCount++;
            }
          }
        }
      }
    }

    // Track route velocities for average calculation
    List<double> routeVelocities = [];
    
    for (final analysis in _aggregatedAnalyses!) {
      totalAppearances += analysis.totalAppearances;
      totalUniqueVideos = math.max(totalUniqueVideos, analysis.uniqueVideos);
      sumConfidence += analysis.averageConfidence;
      totalDurationSeconds += analysis.totalDurationSeconds;
      
      // Collect route velocity if available
      if (analysis.averageRouteVelocity != null) {
        routeVelocities.add(analysis.averageRouteVelocity!);
      }
      
      if (earliestSeen == null || analysis.firstSeen.isBefore(earliestSeen)) {
        earliestSeen = analysis.firstSeen;
      }
      if (latestSeen == null || analysis.lastSeen.isAfter(latestSeen)) {
        latestSeen = analysis.lastSeen;
      }
    }

    // Use confidence scores from search results if available, otherwise fall back to aggregated analyses
    final avgConfidence = confidenceScores.isNotEmpty
        ? confidenceScores.reduce((a, b) => a + b) / confidenceScores.length
        : (_aggregatedAnalyses!.isNotEmpty 
            ? sumConfidence / _aggregatedAnalyses!.length 
            : 0.0);
    
    final avgVelocity = velocityCount > 0 ? totalVelocity / velocityCount : 0.0;
    
    // Calculate average route velocity (movement speed)
    final avgRouteVelocity = routeVelocities.isNotEmpty
        ? routeVelocities.reduce((a, b) => a + b) / routeVelocities.length
        : 0.0;
    
    // Use video duration if available, otherwise fall back to aggregated analyses duration
    final actualDurationSeconds = totalVideoDurationSeconds > 0 
        ? totalVideoDurationSeconds 
        : totalDurationSeconds;
    
    final totalDurationDays = (actualDurationSeconds / 86400).floor();
    final totalDurationHours = ((actualDurationSeconds % 86400) / 3600).floor();
    final totalDurationMinutes = ((actualDurationSeconds % 3600) / 60).floor();
    final totalDurationSecs = (actualDurationSeconds % 60).floor();
    
    // Calculate time span from search parameters
    String timeSpanText = 'N/A';
    int timeSpanDays = 0;
    
    if (searchStartTime != null && searchEndTime != null) {
      final duration = searchEndTime.difference(searchStartTime);
      timeSpanDays = duration.inDays;
      final hours = duration.inHours % 24;
      final minutes = duration.inMinutes % 60;
      
      if (timeSpanDays > 0) {
        timeSpanText = '$timeSpanDays days, $hours hours';
      } else if (hours > 0) {
        timeSpanText = '$hours hours, $minutes minutes';
      } else {
        timeSpanText = '$minutes minutes';
      }
    } else if (earliestSeen != null && latestSeen != null) {
      // Fallback to earliest/latest seen from aggregated analyses
      timeSpanDays = latestSeen.difference(earliestSeen).inDays;
      final hours = latestSeen.difference(earliestSeen).inHours % 24;
      
      if (timeSpanDays > 0) {
        timeSpanText = '$timeSpanDays days, $hours hours';
      } else if (hours > 0) {
        timeSpanText = '$hours hours';
      } else {
        timeSpanText = '< 1 hour';
      }
    }
    
    // Format duration string
    String durationText;
    if (totalDurationDays > 0) {
      durationText = '$totalDurationDays days, $totalDurationHours hours';
    } else if (totalDurationHours > 0) {
      durationText = '$totalDurationHours hours, $totalDurationMinutes min';
    } else if (totalDurationMinutes > 0) {
      durationText = '$totalDurationMinutes minutes, $totalDurationSecs sec';
    } else {
      durationText = '$totalDurationSecs seconds';
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildStatCard(
          'Total Individuals',
          '${_aggregatedAnalyses!.length}',
          Icons.people,
          Colors.blue,
        ),
        _buildStatCard(
          'Total Appearances',
          '$totalAppearances',
          Icons.visibility,
          Colors.green,
        ),
        _buildStatCard(
          'Unique Videos',
          '$totalUniqueVideos',
          Icons.video_library,
          Colors.purple,
        ),
        _buildStatCard(
          'Average Confidence',
          '${(avgConfidence * 100).toStringAsFixed(1)}%',
          Icons.verified,
          Colors.amber,
        ),
        _buildStatCard(
          'Average Appearance Frequency',
          '${avgVelocity.toStringAsFixed(2)} app/min',
          Icons.speed,
          Colors.lightGreen,
        ),
        if (avgRouteVelocity > 0)
          _buildStatCard(
            'Average Movement Velocity',
            '${avgRouteVelocity.toStringAsFixed(6)} px/s',
            Icons.trending_up,
            Colors.deepPurple,
            subtitle: 'Normalized movement speed',
          ),
        _buildStatCard(
          'Total Duration',
          durationText,
          Icons.timer,
          Colors.orange,
        ),
        _buildStatCard(
          'Search Time Span',
          timeSpanText,
          Icons.date_range,
          Colors.cyan,
        ),
        if (earliestSeen != null && latestSeen != null) ...[
          _buildStatCard(
            'First Appearance',
            _formatTimestamp(earliestSeen),
            Icons.schedule,
            Colors.teal,
          ),
          _buildStatCard(
            'Last Appearance',
            _formatTimestamp(latestSeen),
            Icons.update,
            Colors.indigo,
          ),
        ],
        // Demographics section
        if (hasDemographics) ...[
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 8),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8.0),
            child: Text(
              'Demographics',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          // Gender breakdown
          _buildStatCard(
            'Men',
            '$totalMale',
            Icons.male,
            Colors.blue,
            subtitle: totalMale + totalFemale > 0
                ? '${((totalMale / (totalMale + totalFemale)) * 100).toStringAsFixed(1)}%'
                : null,
          ),
          _buildStatCard(
            'Women',
            '$totalFemale',
            Icons.female,
            Colors.pink,
            subtitle: totalMale + totalFemale > 0
                ? '${((totalFemale / (totalMale + totalFemale)) * 100).toStringAsFixed(1)}%'
                : null,
          ),
          if (totalUnknown > 0)
            _buildStatCard(
              'Unknown Gender',
              '$totalUnknown',
              Icons.help_outline,
              Colors.grey,
            ),
          // Average age
          if (ages.isNotEmpty)
            _buildStatCard(
              'Average Age',
              '${(ages.reduce((a, b) => a + b) / ages.length).toStringAsFixed(1)} years',
              Icons.cake,
              Colors.orange,
            ),
        ],
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color, {String? subtitle}) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    value,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey[500],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build Best Faces tab for cross-video mode
  /// COMMENTED OUT - Attendance is now a first-tier tab
  /*
  Widget _buildFacesTabCrossVideo() {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(child: Text('No data available'));
    }

    // Vision tab now contains three sub-tabs: Insights, Attendance, Triggers
    return Column(
      children: [
        // Sub-tab bar for Vision tab
        Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            border: Border(
              bottom: BorderSide(
                color: Colors.grey.shade300,
                width: 1,
              ),
            ),
          ),
          child: TabBar(
            controller: _visionTabController,
            tabs: const [
              Tab(
                icon: Icon(Icons.lightbulb_outline),
                text: 'Insights',
              ),
              Tab(
                icon: Icon(Icons.event_available),
                text: 'Attendance',
              ),
              Tab(
                icon: Icon(Icons.precision_manufacturing),
                text: 'Automation',
              ),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _visionTabController,
            children: [
              _buildInsightsTab(),
              _buildAttendanceTab(),
              _buildTriggersTab(),
            ],
          ),
        ),
      ],
    );
  }
  */

  /// Build Insights tab - AI-powered behavioral insights
  /// Build Insights tab - COMMENTED OUT
  /*
  Widget _buildInsightsTab() {
    // Use the same statistics calculations as Statistics tab
    return _buildStatisticsTabCrossVideo();
  }
  */

  /// Build individuals summary list for Attendance tab
  Widget _buildIndividualsSummaryList(List<AggregatedIndividualAnalysis> analyses, String cameraName) {
    final theme = Theme.of(context);
    final borderColor = theme.colorScheme.outline.withOpacity(0.3);
    final iconColor = theme.colorScheme.primary;
    final textColor = theme.colorScheme.onSurface;
    
    return Column(
      children: [
        // Header bar matching Camera Search Results style
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: theme.colorScheme.primaryContainer.withOpacity(0.3),
            border: Border(
              bottom: BorderSide(
                color: borderColor,
                width: 1,
              ),
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.people,
                size: 20,
                color: iconColor,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Individuals Summary',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: iconColor,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${analyses.length} ${analyses.length == 1 ? 'person' : 'people'} tracked in this analysis',
                      style: TextStyle(
                        fontSize: 12,
                        color: textColor.withOpacity(0.8),
                      ),
                    ),
                  ],
                ),
              ),
              // Download button
              IconButton(
                icon: Icon(
                  Icons.download,
                  color: iconColor,
                  size: 20,
                ),
                onPressed: () => _downloadAttendanceExcel(cameraName),
                tooltip: 'Download Excel',
              ),
            ],
          ),
        ),
        
        // Table header
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface.withOpacity(0.5),
            border: Border(
              bottom: BorderSide(color: borderColor, width: 1),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 3,
                child: Text(
                  'Individual',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: textColor,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  'First Seen',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: textColor,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  'Last Seen',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: textColor,
                  ),
                ),
              ),
              Expanded(
                flex: 1,
                child: Text(
                  'Total',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: textColor,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
        
        // Individual rows
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: analyses.length,
          separatorBuilder: (context, index) => Divider(
            height: 1,
            thickness: 1,
            color: borderColor,
          ),
          itemBuilder: (context, index) {
            final analysis = analyses[index];
            return _buildIndividualSummaryRow(analysis);
          },
        ),
      ],
    );
  }

  /// Build a single row in the individuals summary table
  Widget _buildIndividualSummaryRow(AggregatedIndividualAnalysis analysis) {
    final theme = Theme.of(context);
    final textColor = theme.colorScheme.onSurface;
    final iconColor = theme.colorScheme.primary;
    
    // Determine display name - prioritize hierarchy (super-individual first)
    String displayName;
    Demographics? displayDemographics = analysis.demographics;
    
    // For super-individuals, the name and demographics are already at the top level
    // For merged members, check if super-individual data exists
    if (analysis.name != null && analysis.name!.isNotEmpty) {
      displayName = analysis.name!;
    } else {
      // Build placeholder name with gender and age approximation from demographics
      final gender = displayDemographics?.gender ?? 'Unknown';
      final ageApproximation = _getAgeApproximation(displayDemographics);
      displayName = '$ageApproximation $gender';
    }

    // Format timestamps
    final firstSeen = analysis.firstSeen != null
        ? _formatTimestamp(analysis.firstSeen!)
        : 'N/A';
    final lastSeen = analysis.lastSeen != null
        ? _formatTimestamp(analysis.lastSeen!)
        : 'N/A';

    return InkWell(
      onTap: () {
        // Could navigate to individual detail or expand inline
      },
      hoverColor: theme.colorScheme.primary.withOpacity(0.05),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            // Individual name/info
            Expanded(
              flex: 3,
              child: Row(
                children: [
                  // Gender icon
                  Icon(
                    displayDemographics?.gender?.toLowerCase() == 'male'
                        ? Icons.male
                        : displayDemographics?.gender?.toLowerCase() == 'female'
                            ? Icons.female
                            : Icons.person,
                    size: 18,
                    color: displayDemographics?.gender?.toLowerCase() == 'male'
                        ? Colors.blue[400]
                        : displayDemographics?.gender?.toLowerCase() == 'female'
                            ? Colors.pink[400]
                            : Colors.grey[400],
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      displayName,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: analysis.name != null ? FontWeight.w600 : FontWeight.w500,
                        color: analysis.name != null 
                            ? iconColor 
                            : textColor,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
            
            // First seen
            Expanded(
              flex: 2,
              child: Text(
                firstSeen,
                style: TextStyle(
                  fontSize: 12,
                  color: textColor.withOpacity(0.8),
                ),
              ),
            ),
            
            // Last seen
            Expanded(
              flex: 2,
              child: Text(
                lastSeen,
                style: TextStyle(
                  fontSize: 12,
                  color: textColor.withOpacity(0.8),
                ),
              ),
            ),
            
            // Appearances count
            Expanded(
              flex: 1,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: iconColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${analysis.totalAppearances}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: iconColor,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Get age approximation label based on demographics
  String _getAgeApproximation(Demographics? demographics) {
    if (demographics == null || demographics.ageMin == null) {
      return 'Unknown';
    }

    final avgAge = ((demographics.ageMin ?? 0) + (demographics.ageMax ?? demographics.ageMin ?? 0)) / 2;

    if (avgAge < 21) {
      return 'Young';
    } else if (avgAge > 70) {
      return 'Senior';
    } else {
      return 'Adult';
    }
  }

  /// Download attendance summary as Excel file
  Future<void> _downloadAttendanceExcel(String cameraName) async {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No data to export')),
      );
      return;
    }

    // Filter analyses for this specific camera
    final cameraAnalyses = _aggregatedAnalyses!.where((analysis) {
      return analysis.appearances.any((appearance) {
        final appearanceCameraName = appearance.cameraName ?? appearance.cameraId ?? 'Unknown Camera';
        return appearanceCameraName == cameraName;
      });
    }).toList();

    if (cameraAnalyses.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No data for this camera')),
      );
      return;
    }

    try {
      // Create Excel workbook
      final excelFile = excel.Excel.createExcel();
      
      // Delete default sheet and create our custom sheet as the first sheet
      excelFile.delete('Sheet1');
      excelFile.rename('Sheet1', 'Attendance Summary');
      final sheet = excelFile['Attendance Summary'];
      
      // Get collection name and dates from crossVideoContext
      final crossVideoCtx = widget.crossVideoContext!;
      final isCameraSearch = crossVideoCtx.sessionData['source'] == 'individual_group_camera_search';
      String collectionName = cameraName;  // Use the camera parameter as collection name
      DateTime? startTime;
      DateTime? endTime;
      
      // Extract dates from search_parameters
      if (crossVideoCtx.sessionData['search_parameters'] != null) {
        final searchParams = crossVideoCtx.sessionData['search_parameters'] as Map<String, dynamic>;
        
        if (searchParams['start_time'] != null) {
          startTime = DateTime.tryParse(searchParams['start_time'].toString());
        }
        if (searchParams['end_time'] != null) {
          endTime = DateTime.tryParse(searchParams['end_time'].toString());
        }
      }
      
      // Format dates
      final startTimeStr = startTime != null ? _formatTimestamp(startTime) : 'N/A';
      final endTimeStr = endTime != null ? _formatTimestamp(endTime) : 'N/A';
      
      // Title row (Row 0)
      sheet.appendRow([
        excel.TextCellValue('Attendance Summary Report - $collectionName'),
      ]);
      
      // Collection and date info (Rows 1-3)
      sheet.appendRow([
        excel.TextCellValue('Collection: $collectionName'),
      ]);
      sheet.appendRow([
        excel.TextCellValue('From: $startTimeStr'),
      ]);
      sheet.appendRow([
        excel.TextCellValue('To: $endTimeStr'),
      ]);
      
      // Empty row
      sheet.appendRow([]);
      
      // Table header (Row 5)
      sheet.appendRow([
        excel.TextCellValue('Individual'),
        excel.TextCellValue('First Seen'),
        excel.TextCellValue('Last Seen'),
        excel.TextCellValue('Total Appearances'),
      ]);
      
      // Data rows - use filtered analyses for this camera
      for (final analysis in cameraAnalyses) {
        // Determine display name
        String displayName;
        Demographics? displayDemographics = analysis.demographics;
        
        if (analysis.name != null && analysis.name!.isNotEmpty) {
          displayName = analysis.name!;
        } else {
          final gender = displayDemographics?.gender ?? 'Unknown';
          final ageApproximation = _getAgeApproximation(displayDemographics);
          displayName = '$ageApproximation $gender';
        }
        
        final firstSeen = analysis.firstSeen != null
            ? _formatTimestamp(analysis.firstSeen!)
            : 'N/A';
        final lastSeen = analysis.lastSeen != null
            ? _formatTimestamp(analysis.lastSeen!)
            : 'N/A';
        
        sheet.appendRow([
          excel.TextCellValue(displayName),
          excel.TextCellValue(firstSeen),
          excel.TextCellValue(lastSeen),
          excel.IntCellValue(analysis.totalAppearances),
        ]);
      }
      
      // Style the header row (row index 5)
      for (int col = 0; col < 4; col++) {
        final cell = sheet.cell(excel.CellIndex.indexByColumnRow(columnIndex: col, rowIndex: 5));
        cell.cellStyle = excel.CellStyle(
          bold: true,
          backgroundColorHex: excel.ExcelColor.blue,
          fontColorHex: excel.ExcelColor.white,
        );
      }
      
      // Auto-fit column widths
      sheet.setColumnWidth(0, 30); // Individual
      sheet.setColumnWidth(1, 25); // First Seen
      sheet.setColumnWidth(2, 25); // Last Seen
      sheet.setColumnWidth(3, 20); // Total Appearances
      
      // Generate file bytes
      final fileBytes = excelFile.encode();
      if (fileBytes == null) {
        throw Exception('Failed to encode Excel file');
      }
      
      // Save and share file with camera name in filename
      final sanitizedCameraName = cameraName.replaceAll(RegExp(r'[^a-zA-Z0-9_-]'), '_');
      final fileName = 'attendance_${sanitizedCameraName}_${DateTime.now().millisecondsSinceEpoch}.xlsx';
      
      if (kIsWeb) {
        await downloadFileBytes(
          bytes: fileBytes,
          filename: fileName,
          mimeType:
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        );
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Excel file downloaded successfully'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        // For mobile/desktop, save to temp and share
        final directory = await getTemporaryDirectory();
        final filePath = '${directory.path}/$fileName';
        final file = File(filePath);
        await file.writeAsBytes(fileBytes);
        
        // Share the file
        await Share.shareXFiles(
          [XFile(filePath)],
          subject: 'Attendance Summary - $collectionName',
        );
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Excel file ready to share'),
              backgroundColor: Colors.green,
            ),
          );
        }
      }
    } catch (e, stackTrace) {
      debugPrint('Error generating Excel file: $e');
      debugPrint('Stack trace: $stackTrace');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to generate Excel: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Build Attendance tab - Time-based presence tracking
  Widget _buildAttendanceTab() {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(child: Text('No attendance data available'));
    }

    // Group analyses by camera/collection
    final analysesByCamera = <String, List<AggregatedIndividualAnalysis>>{};
    for (final analysis in _aggregatedAnalyses!) {
      // Determine which camera(s) this individual appeared in
      final camerasForIndividual = <String>{};
      for (final appearance in analysis.appearances) {
        final cameraName = appearance.cameraName ?? appearance.cameraId ?? 'Unknown Camera';
        camerasForIndividual.add(cameraName);
      }
      
      // Add this individual to each camera group they appeared in
      for (final camera in camerasForIndividual) {
        analysesByCamera.putIfAbsent(camera, () => []).add(analysis);
      }
    }

    return SingleChildScrollView(
      child: Column(
        children: analysesByCamera.entries.map((entry) {
          final cameraName = entry.key;
          final cameraAnalyses = entry.value;
          
          return Column(
            children: [
              // Camera header (only show if multiple cameras)
              if (analysesByCamera.length > 1)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  margin: const EdgeInsets.only(top: 16),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    border: Border(
                      left: BorderSide(color: Colors.blue.shade700, width: 4),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.videocam, size: 18, color: Colors.blue[700]),
                      const SizedBox(width: 8),
                      Text(
                        cameraName,
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Colors.blue[700],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        '${cameraAnalyses.length} ${cameraAnalyses.length != 1 ? 'people' : 'person'}',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
              
              // Individuals Summary List for this camera
              _buildIndividualsSummaryList(cameraAnalyses, cameraName),
              
              const Divider(height: 32, thickness: 2),
              
              // Timeline Header
              Container(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Icon(Icons.event_available, color: Colors.blue),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            analysesByCamera.length > 1 
                              ? 'Attendance Timeline - $cameraName'
                              : 'Attendance Timeline',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text(
                            'Individual appearances over time',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              
              // Attendance graph for this camera
              Center(
                child: Container(
                  height: math.max(400, cameraAnalyses.length * 60.0),
                  margin: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.black12,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: CustomPaint(
                      painter: AttendanceGraphPainter(cameraAnalyses),
                      size: Size.infinite,
                    ),
                  ),
                ),
              ),
              
              // Add spacing between cameras
              if (analysesByCamera.length > 1)
                const SizedBox(height: 32),
            ],
          );
        }).toList(),
      ),
    );
  }

  /// Build Triggers tab - Event-based notifications and alerts - COMMENTED OUT
  /*
  Widget _buildTriggersTab() {
    // Use the new API-integrated triggers widget
    return const TriggersTab();
  }
  */

  Widget _buildFaceCard(FaceData face, String individualId) {
    final qualityScore = face.qualityScore * 100;
    
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
              child: face.imageUrl != null
                  ? Image.network(
                      face.imageUrl!,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: Colors.grey[300],
                        child: const Icon(Icons.person, size: 48),
                      ),
                    )
                  : Container(
                      color: Colors.grey[300],
                      child: const Icon(Icons.person, size: 48),
                    ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Individual $individualId',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.star, size: 14, color: Colors.amber),
                    const SizedBox(width: 4),
                    Text(
                      '${qualityScore.toStringAsFixed(1)}%',
                      style: const TextStyle(fontSize: 11),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'Conf: ${(face.confidence * 100).toStringAsFixed(0)}%',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
/// Custom painter for attendance timeline graph
/// Shows individuals on Y-axis and time on X-axis with appearance points
class AttendanceGraphPainter extends CustomPainter {
  final List<AggregatedIndividualAnalysis> analyses;

  AttendanceGraphPainter(this.analyses);

  @override
  void paint(Canvas canvas, Size size) {
    if (analyses.isEmpty) return;

    // Sort analyses by number of appearances (descending)
    final sortedAnalyses = List<AggregatedIndividualAnalysis>.from(analyses)
      ..sort((a, b) => b.appearances.length.compareTo(a.appearances.length));

    const leftMargin = 150.0; // Space for individual UUIDs
    const rightMargin = 50.0; // More space for last time label
    const topMargin = 40.0;
    const bottomMargin = 80.0; // More space for rotated time labels
    
    final graphWidth = size.width - leftMargin - rightMargin;
    final graphHeight = size.height - topMargin - bottomMargin;
    final rowHeight = graphHeight / sortedAnalyses.length;

    // Find min/max time across all appearances
    DateTime? minTime;
    DateTime? maxTime;
    
    for (final analysis in sortedAnalyses) {
      for (final appearance in analysis.appearances) {
        final startTime = appearance.startTimestamp is String 
            ? DateTime.parse(appearance.startTimestamp as String)
            : appearance.startTimestamp as DateTime;
        final endTime = appearance.endTimestamp is String
            ? DateTime.parse(appearance.endTimestamp as String)
            : appearance.endTimestamp as DateTime;
        
        if (minTime == null || startTime.isBefore(minTime)) minTime = startTime;
        if (maxTime == null || endTime.isAfter(maxTime)) maxTime = endTime;
      }
    }

    if (minTime == null || maxTime == null) return;

    final timeDuration = maxTime.difference(minTime);
    
    // Helper to convert timestamp to X coordinate
    double timeToX(DateTime time) {
      final elapsed = time.difference(minTime!);
      final ratio = elapsed.inMilliseconds / timeDuration.inMilliseconds;
      return leftMargin + (ratio * graphWidth);
    }

    // No background paint - use container's background
    // Draw grid lines (horizontal) - lighter for dark theme
    final gridPaint = Paint()
      ..color = Colors.grey.shade700
      ..strokeWidth = 1.0;
    
    for (int i = 0; i <= sortedAnalyses.length; i++) {
      final y = topMargin + (i * rowHeight);
      canvas.drawLine(
        Offset(leftMargin, y),
        Offset(leftMargin + graphWidth, y),
        gridPaint,
      );
    }

    // Draw vertical time grid lines
    final timeInterval = _calculateTimeInterval(timeDuration);
    DateTime currentTime = minTime;
    
    while (currentTime.isBefore(maxTime) || currentTime.isAtSameMomentAs(maxTime)) {
      final x = timeToX(currentTime);
      canvas.drawLine(
        Offset(x, topMargin),
        Offset(x, topMargin + graphHeight),
        gridPaint,
      );
      
      // Draw time label with better size and alignment
      final timeLabel = _formatTimeLabel(currentTime);
      final timePainter = TextPainter(
        text: TextSpan(
          text: timeLabel,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      timePainter.layout();
      
      // Rotate and draw time label with better positioning
      canvas.save();
      canvas.translate(x - 5, topMargin + graphHeight + 15);
      canvas.rotate(-3.14159 / 4);
      timePainter.paint(canvas, Offset.zero);
      canvas.restore();
      
      currentTime = currentTime.add(timeInterval);
    }
    
    // Always draw the last time label
    if (!currentTime.subtract(timeInterval).isAtSameMomentAs(maxTime)) {
      final x = timeToX(maxTime);
      canvas.drawLine(
        Offset(x, topMargin),
        Offset(x, topMargin + graphHeight),
        gridPaint,
      );
      
      final timeLabel = _formatTimeLabel(maxTime);
      final timePainter = TextPainter(
        text: TextSpan(
          text: timeLabel,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      timePainter.layout();
      
      canvas.save();
      canvas.translate(x - 5, topMargin + graphHeight + 15);
      canvas.rotate(-3.14159 / 4);
      timePainter.paint(canvas, Offset.zero);
      canvas.restore();
    }

    // Draw axis labels
    final titlePainter = TextPainter(
      text: const TextSpan(
        text: 'Time',
        style: TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    titlePainter.layout();
    titlePainter.paint(
      canvas,
      Offset(
        leftMargin + (graphWidth - titlePainter.width) / 2,
        size.height - 20,
      ),
    );

    final yLabelPainter = TextPainter(
      text: const TextSpan(
        text: 'Individuals',
        style: TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    yLabelPainter.layout();
    
    canvas.save();
    canvas.translate(10, topMargin + graphHeight / 2 + yLabelPainter.width / 2);
    canvas.rotate(-3.14159 / 2);
    yLabelPainter.paint(canvas, Offset.zero);
    canvas.restore();

    // Draw individual rows with appearances
    for (int i = 0; i < sortedAnalyses.length; i++) {
      final analysis = sortedAnalyses[i];
      final y = topMargin + (i * rowHeight) + (rowHeight / 2);
      
      // Get consistent color for this individual
      final individualColor = _getIndividualColor(i);
      
      // Find first and last appearance times for this individual
      DateTime? firstTime;
      DateTime? lastTime;
      for (final appearance in analysis.appearances) {
        final startTime = appearance.startTimestamp is String
            ? DateTime.parse(appearance.startTimestamp as String)
            : appearance.startTimestamp as DateTime;
        final endTime = appearance.endTimestamp is String
            ? DateTime.parse(appearance.endTimestamp as String)
            : appearance.endTimestamp as DateTime;
        
        if (firstTime == null || startTime.isBefore(firstTime)) firstTime = startTime;
        if (lastTime == null || endTime.isAfter(lastTime)) lastTime = endTime;
      }
      
      // Draw individual UUID label
      final uuid = analysis.individualUuid.substring(0, 8) + '...';
      final labelPainter = TextPainter(
        text: TextSpan(
          text: uuid,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontFamily: 'monospace',
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      labelPainter.layout();
      labelPainter.paint(
        canvas,
        Offset(leftMargin - labelPainter.width - 10, y - labelPainter.height - 2),
      );
      
      // Draw first and last time underneath the UUID
      if (firstTime != null && lastTime != null) {
        final timeRange = '${_formatCompactTime(firstTime)} → ${_formatCompactTime(lastTime)}';
        final timePainter = TextPainter(
          text: TextSpan(
            text: timeRange,
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 9,
              fontFamily: 'monospace',
            ),
          ),
          textDirection: TextDirection.ltr,
        );
        timePainter.layout();
        timePainter.paint(
          canvas,
          Offset(leftMargin - timePainter.width - 10, y + 2),
        );
      }

      // Draw appearance points - all with same color per individual
      for (int j = 0; j < analysis.appearances.length; j++) {
        final appearance = analysis.appearances[j];
        final startTime = appearance.startTimestamp is String
            ? DateTime.parse(appearance.startTimestamp as String)
            : appearance.startTimestamp as DateTime;
        final endTime = appearance.endTimestamp is String
            ? DateTime.parse(appearance.endTimestamp as String)
            : appearance.endTimestamp as DateTime;
        
        final startX = timeToX(startTime);
        final endX = timeToX(endTime);
        
        // Use individual's color for all appearances
        // Draw appearance as a line segment
        final linePaint = Paint()
          ..color = individualColor.withOpacity(0.7)
          ..strokeWidth = 4.0
          ..strokeCap = StrokeCap.round;
        
        canvas.drawLine(
          Offset(startX, y),
          Offset(endX, y),
          linePaint,
        );
        
        // Draw start point with brighter version
        final pointPaint = Paint()..color = individualColor;
        canvas.drawCircle(Offset(startX, y), 5.0, pointPaint);
        
        // Draw end point with brighter version
        canvas.drawCircle(Offset(endX, y), 5.0, pointPaint);
        
        // Add white border for visibility
        final borderPaint = Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5;
        canvas.drawCircle(Offset(startX, y), 5.0, borderPaint);
        canvas.drawCircle(Offset(endX, y), 5.0, borderPaint);
      }
    }

    // Draw axes
    final axisPaint = Paint()
      ..color = Colors.white70
      ..strokeWidth = 2.0;
    
    // Y-axis
    canvas.drawLine(
      Offset(leftMargin, topMargin),
      Offset(leftMargin, topMargin + graphHeight),
      axisPaint,
    );
    
    // X-axis
    canvas.drawLine(
      Offset(leftMargin, topMargin + graphHeight),
      Offset(leftMargin + graphWidth, topMargin + graphHeight),
      axisPaint,
    );
  }

  Duration _calculateTimeInterval(Duration totalDuration) {
    final hours = totalDuration.inHours;
    
    if (hours <= 24) {
      return const Duration(hours: 2);
    } else if (hours <= 72) {
      return const Duration(hours: 6);
    } else if (hours <= 168) {
      return const Duration(hours: 12);
    } else {
      return const Duration(days: 1);
    }
  }

  String _formatTimeLabel(DateTime time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    final day = time.day.toString().padLeft(2, '0');
    final month = time.month.toString().padLeft(2, '0');
    
    return '$day/$month $hour:$minute';
  }

  String _formatCompactTime(DateTime time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    final day = time.day.toString().padLeft(2, '0');
    final month = time.month.toString().padLeft(2, '0');
    
    return '$day/$month $hour:$minute';
  }

  Color _getIndividualColor(int index) {
    // Use same color palette as routes for consistency
    final colors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
      Colors.pink,
      Colors.indigo,
      Colors.brown,
      Colors.cyan,
    ];
    return colors[index % colors.length];
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

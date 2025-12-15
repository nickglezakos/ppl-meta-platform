import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:ui' as ui;
import 'dart:io';
import 'dart:async';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import '../models/person_objects_models.dart';
import '../models/cross_video_analysis_models.dart';
import '../providers/person_objects_provider.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/triggers_tab.dart';
import '../models/media_models.dart';
import '../core/api/api_client.dart';
import '../services/media_api_client.dart';

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
  
  late TabController _tabController;
  late TabController _visionTabController; // Nested tab controller for Vision tab
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
  double _similarityThreshold = 0.6;

  @override
  void initState() {
    super.initState();
    
    // Determine mode
    _isCrossVideoMode = widget.crossVideoContext != null;
    
    _tabController = TabController(length: 4, vsync: this);
    _visionTabController = TabController(length: 3, vsync: this); // Vision tab has 3 sub-tabs
    
    // Load cross-video data if in that mode
    if (_isCrossVideoMode) {
      _loadCrossVideoData();
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _visionTabController.dispose();
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
              icon: Icon(Icons.videocam),
              text: 'Vision',
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
              _buildFacesTabCrossVideo(),
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
      // Check for collection_name first (primary key added in v2.19.40)
      if (context.sessionData['collection_name'] != null) {
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
    
    return Container(
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
    });
    
    try {
      final context = widget.crossVideoContext!;
      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);
      
      final aggregatedAnalyses = <AggregatedIndividualAnalysis>[];
      
      print('📊 Loading analysis for ${context.individualUuids.length} individuals');

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

      if (loadingMVRPeople && hierarchicalMergeApplied) {
        print('📊 Loading super-individuals with hierarchical data');
        print('📊 Context has ${context.individualUuids.length} MVR UUIDs to load');
        
        // For each super-individual UUID, fetch full hierarchy
        for (final superIndividualUuid in context.individualUuids) {
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
                
                print('✅ Loaded super-individual with hierarchy:');
                print('   - ${analysis.totalAppearances} total appearances');
                print('   - ${analysis.uniqueVideos} unique videos');
                print('   - ${mergedMVRList.length} merged MVR people');
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
      } else if (loadingMVRPeople) {
        print('📊 Loading MVR person data (consolidated individuals)');
        // For each MVR person UUID, call the MVR person endpoint (existing logic)
        for (final mvrPersonUuid in context.individualUuids) {
          await _loadSingleMVRPerson(
            mvrPersonUuid,
            mediaApiClient,
            startTime,
            endTime,
            context.sessionUuid,
            aggregatedAnalyses,
          );
        }
      } else {
        print('📊 Loading individual data');
        // For each individual UUID, call the session-less endpoint
        for (final individualUuid in context.individualUuids) {
          try {
            final response = await mediaApiClient.getIndividualAnalysisNoSession(
              individualUuid: individualUuid,
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
            
            // Skip individuals with no appearances
            final totalAppearances = data['total_appearances'] as int;
            if (totalAppearances == 0) {
              print('⚠️ Skipping individual $individualUuid: 0 appearances (no data)');
              continue;
            }
            
            final analysis = AggregatedIndividualAnalysis(
              individualUuid: data['individual_uuid'] as String,
              individualId: data['individual_uuid'] as String,
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
                  .map((app) => IndividualAppearance(
                        individualUuid: data['individual_uuid'] as String,
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
            : 'No individual data could be loaded';
        
        setState(() {
          _crossVideoError = errorMessage;
          _isLoadingCrossVideoData = false;
        });
        return;
      }
      
      setState(() {
        _aggregatedAnalyses = aggregatedAnalyses;
        _isLoadingCrossVideoData = false;
      });
      
      print('✅ Loaded cross-video data for ${aggregatedAnalyses.length} individuals');
      
    } catch (e) {
      setState(() {
        _crossVideoError = 'Failed to load cross-video data: $e';
        _isLoadingCrossVideoData = false;
      });
      print('❌ Error loading cross-video data: $e');
    }
  }

  /// Helper method to load a single MVR person's data (v2.19.85)
  /// 
  /// This is used as a fallback when hierarchy loading fails or for
  /// non-merged MVR people.
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
    final bool canMerge = _selectedIndividuals.length >= 2;
    
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
            if (canMerge)
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
    // TODO: Implement group management functionality
    // For now, show a placeholder dialog
    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add to Group'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Add ${_selectedIndividuals.length} individual(s) to a group',
              style: const TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 16),
            const Text(
              'Group management feature coming soon!',
              style: TextStyle(
                color: Colors.orange,
                fontStyle: FontStyle.italic,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'This will allow you to:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text('• Create named groups of individuals'),
            const Text('• Add/remove individuals from groups'),
            const Text('• Search and filter by group'),
            const Text('• Generate group-level analytics'),
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
    
    // Clear selection after action
    setState(() {
      _selectedIndividuals.clear();
    });
  }

  /// Show confirmation dialog for merging individuals
  Future<void> _showMergeConfirmationDialog() async {
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
      
      final response = await mediaApiClient.mergeIndividuals(
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
        
        // Clear selection and reload data
        setState(() {
          _selectedIndividuals.clear();
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
        final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
        final apiClient = ref.read(apiClientProvider);
        return Image.network(
          frameUrl,
          fit: BoxFit.cover,
          headers: apiClient.authToken != null ? {
            'Authorization': 'Bearer ${apiClient.authToken}',
          } : {},
          errorBuilder: (context, error, stackTrace) {
            print('Error loading fallback frame image: $error');
            return Container(
              color: Colors.grey[300],
              child: Icon(Icons.broken_image, size: 24, color: Colors.grey[600]),
            );
          },
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
        final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
        final apiClient = ref.read(apiClientProvider);
        return Image.network(
          frameUrl,
          fit: BoxFit.cover,
          headers: apiClient.authToken != null ? {
            'Authorization': 'Bearer ${apiClient.authToken}',
          } : {},
          errorBuilder: (context, error, stackTrace) {
            print('Error loading fallback frame image: $error');
            return Container(
              color: Colors.grey[300],
              child: Icon(Icons.broken_image, size: 24, color: Colors.grey[600]),
            );
          },
        );
      }
      
      // Get the full frame image first
      final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
      
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
            final apiClient = ref.read(apiClientProvider);
            return Image.network(
              frameUrl,
              fit: BoxFit.cover,
              headers: apiClient.authToken != null ? {
                'Authorization': 'Bearer ${apiClient.authToken}',
              } : {},
              loadingBuilder: (context, child, loadingProgress) {
                if (loadingProgress == null) return child;
                return Center(
                  child: CircularProgressIndicator(
                    value: loadingProgress.expectedTotalBytes != null
                        ? loadingProgress.cumulativeBytesLoaded / loadingProgress.expectedTotalBytes!
                        : null,
                    strokeWidth: 2,
                  ),
                );
              },
              errorBuilder: (context, error, stackTrace) {
                print('Error loading cropped image: $error');
                print('URL: $frameUrl');
                return Container(
                  color: Colors.grey[300],
                  child: Icon(Icons.broken_image, size: 24, color: Colors.grey[600]),
                );
              },
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
      final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem!.uuid}/frame/$frameNumber?format=jpeg';
      final apiClient = ref.read(apiClientProvider);
      
      return Image.network(
        frameUrl,
        fit: BoxFit.contain, // Maintain aspect ratio and fit within container
        headers: apiClient.authToken != null ? {
          'Authorization': 'Bearer ${apiClient.authToken}',
        } : {},
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return Center(
            child: CircularProgressIndicator(
              value: loadingProgress.expectedTotalBytes != null
                  ? loadingProgress.cumulativeBytesLoaded / loadingProgress.expectedTotalBytes!
                  : null,
            ),
          );
        },
        errorBuilder: (context, error, stackTrace) {
          print('Error loading frame image: $error');
          print('URL: $frameUrl');
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error, color: Colors.grey, size: 24),
                SizedBox(height: 4),
                Text('Image failed to load', style: TextStyle(fontSize: 10, color: Colors.grey)),
              ],
            ),
          );
        },
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
                      print('🖼️ Frame Dimensions ERROR: ${dimensionsSnapshot.error}');
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
                      print('🖼️ Frame Dimensions ERROR: Null dimensions returned');
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

                    print('🖼️ Frame Dimensions SUCCESS: ${frameDimensions.width}x${frameDimensions.height}');

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
      print('📦 Routes DEBUG: Returning cached routes data');
      return _cachedRoutesData;
    }
    
    // Prevent multiple concurrent requests
    if (_isLoadingRoutes) {
      print('⏳ Routes DEBUG: Already loading routes data, waiting...');
      // Wait a bit and return cached data if it becomes available
      await Future.delayed(const Duration(milliseconds: 100));
      return _cachedRoutesData;
    }
    
    _isLoadingRoutes = true;
    
    try {
      // Get authenticated API client
      final apiClient = ref.read(apiClientProvider);
      
      print('🔍 Routes DEBUG: Fetching person objects data for media: ${widget.mediaItem!.uuid}');
      
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
          print('✅ Routes DEBUG: Person objects found with route data!');
          
          // The Orchestrator response already contains all the data we need
          // including person_groups with movement_tracking and route_points
          print('✅ Routes DEBUG: Successfully fetched person objects data from Orchestrator');
          
          // Cache the response
          _cachedRoutesData = data;
          
          return data;
        } else {
          print('ℹ️ Routes DEBUG: Person objects not processed yet - status: $status');
        }
      }
      
      print('❌ Routes DEBUG: Could not find person objects data');
      return null;
    } catch (e) {
      print('❌ Routes DEBUG: Error fetching routes data: $e');
      return null; // Return null instead of throwing to prevent UI crashes
    } finally {
      _isLoadingRoutes = false;
    }
  }

  Future<Size?> _getFrameDimensions() async {
    try {
      print('🖼️ Frame Dimensions DEBUG: Getting dimensions for media: ${widget.mediaItem!.uuid}');
      
      // Try method 1: Load frame using HTTP image provider
      final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem!.uuid}/frame/0?format=jpeg';
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
        
        print('🖼️ Frame Dimensions DEBUG: Successfully got dimensions: ${size.width}x${size.height}');
        return size;
      } catch (e) {
        print('🖼️ Frame Dimensions DEBUG: NetworkImage method failed: $e');
      }
      
      // Method 2: Fallback to media metadata if available
      if (widget.mediaItem!.metadata != null) {
        final metadata = widget.mediaItem!.metadata!;
        if (metadata['width'] != null && metadata['height'] != null) {
          final size = Size(
            (metadata['width'] as num).toDouble(),
            (metadata['height'] as num).toDouble(),
          );
          print('🖼️ Frame Dimensions DEBUG: Using metadata dimensions: ${size.width}x${size.height}');
          return size;
        }
      }
      
      // Method 3: Final fallback to common video resolution
      print('🖼️ Frame Dimensions DEBUG: Using fallback dimensions: 1280x720');
      return const Size(1280, 720);
      
    } catch (e) {
      print('❌ Frame Dimensions DEBUG: Error getting frame dimensions: $e');
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
}

/// Custom painter to draw cropped image
class CroppedImagePainter extends CustomPainter {
  final ui.Image image;
  final Rect cropRect;
  static String? _lastDebugInfo; // Static variable to reduce debug spam
  static Size? _lastSignificantSize; // Track significant canvas size changes

  CroppedImagePainter({required this.image, required this.cropRect});

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint();
    
    // Much more aggressive debug reduction - only print for significant canvas size changes
    final isSignificantChange = _lastSignificantSize == null || 
        (size.width - _lastSignificantSize!.width).abs() > 20 ||
        (size.height - _lastSignificantSize!.height).abs() > 20;
        
    if (isSignificantChange) {
      print('DEBUG PAINTER: Canvas ${size.width.toInt()}x${size.height.toInt()} for crop ${cropRect.width.toInt()}x${cropRect.height.toInt()}');
      _lastSignificantSize = size;
    }
    
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
    print('🎨 RoutesPainter DEBUG: _paintWithFrameDimensions called');
    print('🎨 RoutesPainter DEBUG: Canvas size: ${size.width}x${size.height}');
    print('🎨 RoutesPainter DEBUG: Frame dimensions: ${frameDimensions!.width}x${frameDimensions!.height}');
    print('🎨 RoutesPainter DEBUG: Person groups count: ${personGroups.length}');
    
    // Check if we have true 1:1 mapping (canvas matches frame exactly)
    final isOneToOneMapping = (size.width == frameDimensions!.width && size.height == frameDimensions!.height);
    print('🎨 RoutesPainter DEBUG: One-to-one mapping: $isOneToOneMapping');

    // Helper function for coordinate conversion
    Offset convertPoint(double x, double y) {
      if (isOneToOneMapping) {
        // True 1:1 mapping - use coordinates directly
        final converted = Offset(x, y);
        print('🎨 RoutesPainter DEBUG: 1:1 direct mapping ($x, $y) -> (${converted.dx}, ${converted.dy})');
        return converted;
      } else {
        // Scale to fit canvas
        final scaleX = size.width / frameDimensions!.width;
        final scaleY = size.height / frameDimensions!.height;
        final converted = Offset(x * scaleX, y * scaleY);
        print('🎨 RoutesPainter DEBUG: Scaled mapping ($x, $y) -> (${converted.dx}, ${converted.dy}) [scale: ${scaleX}x${scaleY}]');
        return converted;
      }
    }

    // Draw routes for each person
    for (int personIndex = 0; personIndex < personGroups.length; personIndex++) {
      final group = personGroups[personIndex];
      final routePoints = group['movement_tracking']?['route_points'] ?? [];
      
      print('🎨 RoutesPainter DEBUG: Person $personIndex has ${routePoints.length} route points');
      
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
          print('🎨 RoutesPainter DEBUG: Route point: x=$x, y=$y');
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

    print('🗺️ TopView DEBUG: Canvas size: ${size.width}x${size.height}');
    print('🗺️ TopView DEBUG: Person groups count: ${personGroups.length}');

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

    print('🗺️ TopView DEBUG: Route bounds: ($minX, $minY) to ($maxX, $maxY)');

    // Add padding around the movement area
    const padding = 40.0;
    final dataWidth = maxX - minX;
    final dataHeight = maxY - minY;
    
    if (dataWidth <= 0 || dataHeight <= 0) return;

    // Calculate scale to fit canvas with equal scaling (preserving aspect ratio)
    final availableWidth = size.width - 2 * padding;
    final availableHeight = size.height - 2 * padding;
    final scale = math.min(availableWidth / dataWidth, availableHeight / dataHeight);

    print('🗺️ TopView DEBUG: Scale factor: $scale');

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
      
      print('🗺️ TopView DEBUG: Person $personIndex has ${routePoints.length} route points');
      
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

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _aggregatedAnalyses!.length,
      itemBuilder: (context, index) {
        final analysis = _aggregatedAnalyses![index];
        return _buildIndividualCard(analysis, index);
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
                      // Individual icon with badge
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
                            child: analysis.bestFaceThumbnail != null
                                ? ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: Image.network(
                                      analysis.bestFaceThumbnail!,
                                      fit: BoxFit.cover,
                                      errorBuilder: (context, error, stackTrace) =>
                                          Icon(
                                            Icons.person,
                                            size: 40,
                                            color: isSuperIndividual 
                                                ? Colors.blue 
                                                : Colors.grey[600],
                                          ),
                                    ),
                                  )
                                : Icon(
                                    Icons.person,
                                    size: 40,
                                    color: isSuperIndividual 
                                        ? Colors.blue 
                                        : Colors.grey[600],
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
                            Row(
                              children: [
                                Text(
                                  analysis.demographics?.gender ?? 'Unknown',
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
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
            Container(
              color: Colors.blue.withOpacity(0.05),
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    child: Text(
                      'Merged MVR People (${analysis.mergedMVRPeople.length})',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Colors.blue[900],
                      ),
                    ),
                  ),
                  ...analysis.mergedMVRPeople.map((mvr) => _buildMergedMVRCard(mvr)),
                ],
              ),
            ),
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
  
  /// Build merged MVR person card (Level 2 in hierarchy)
  Widget _buildMergedMVRCard(MergedMVRPerson mvr) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // MVR icon
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Icon(
                Icons.badge,
                size: 24,
                color: Colors.blue[700],
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
          ],
        ),
      ),
    );
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
  Widget _buildExpandedAppearances(AggregatedIndividualAnalysis analysis) {
    return Container(
      color: Theme.of(context).colorScheme.surface.withOpacity(0.3),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        itemCount: analysis.appearances.length,
        separatorBuilder: (context, index) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final appearance = analysis.appearances[index];
          return _buildAppearanceCard(appearance, index);
        },
      ),
    );
  }

  /// Build a single appearance card (same UX as individual card)
  Widget _buildAppearanceCard(IndividualAppearance appearance, int index) {
    return GestureDetector(
      onTap: () {
        print('🎬 Navigating to media preview for video: ${appearance.videoUuid}');
        // Navigate to media preview screen with the video UUID using GoRouter
        context.go('/media-preview/${appearance.videoUuid}');
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

        final personGroups = snapshot.data;
        if (personGroups == null || personGroups.isEmpty) {
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

        print('🚦 CROSS-VIDEO ROUTES: Successfully loaded ${personGroups.length} person groups with route data');

        // Now use the SAME visualization as single-video mode
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
                            'Unified routes from ${personGroups.length} individual(s) across multiple videos',
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
              
              // Routes canvas
              const SizedBox(height: 8),
              _buildCrossVideoRoutesCanvas(personGroups),
              
              // Legend
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: _buildRoutesLegend(personGroups),
              ),
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
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return [];
    }

    print('🚦 CROSS-VIDEO ROUTES: Starting fetch for ${_aggregatedAnalyses!.length} individuals');

    final apiClient = ref.read(apiClientProvider);
    final personGroups = <Map<String, dynamic>>[];

    // Get all unique video UUIDs from all appearances
    final allVideoUuids = <String>{};
    for (final analysis in _aggregatedAnalyses!) {
      for (final appearance in analysis.appearances) {
        // Skip empty or invalid video UUIDs
        if (appearance.videoUuid.isNotEmpty && appearance.videoUuid.length >= 8) {
          allVideoUuids.add(appearance.videoUuid);
        } else {
          print('⚠️ Skipping invalid video UUID: "${appearance.videoUuid}"');
        }
      }
    }

    print('🚦 CROSS-VIDEO ROUTES: Found ${allVideoUuids.length} unique videos');

    // Fetch person objects data for each video
    final videoRoutesMap = <String, Map<String, dynamic>>{};
    
    for (final videoUuid in allVideoUuids) {
      try {
        print('🚦 CROSS-VIDEO ROUTES: Fetching routes from video $videoUuid');
        
        final response = await apiClient.get(
          '/api/v1/orchestrator/person-objects/$videoUuid',
        );

        if (response.statusCode == 200 && response.data != null) {
          final data = response.data as Map<String, dynamic>;
          final success = data['success'] as bool? ?? false;
          final status = data['status'] as String? ?? '';

          if (success && status == 'completed') {
            videoRoutesMap[videoUuid] = data;
            print('🚦 CROSS-VIDEO ROUTES: ✅ Got routes for video $videoUuid');
          } else {
            print('🚦 CROSS-VIDEO ROUTES: ⚠️ Video $videoUuid not processed (status: $status)');
          }
        }
      } catch (e) {
        print('🚦 CROSS-VIDEO ROUTES: ❌ Error fetching routes for video $videoUuid: $e');
      }
    }

    print('🚦 CROSS-VIDEO ROUTES: Successfully loaded routes from ${videoRoutesMap.length}/${allVideoUuids.length} videos');

    // Now combine route data for each individual across all videos
    for (int i = 0; i < _aggregatedAnalyses!.length; i++) {
      final analysis = _aggregatedAnalyses![i];
      final individualId = analysis.individualId;
      
      print('🚦 CROSS-VIDEO ROUTES: Processing individual $i ($individualId)');
      print('🚦   Individual has ${analysis.appearances.length} appearances');

      final allRoutePoints = <Map<String, dynamic>>[];

      // For each appearance of this individual
      for (int ai = 0; ai < analysis.appearances.length; ai++) {
        final appearance = analysis.appearances[ai];
        final videoUuid = appearance.videoUuid;
        final personObjectUuid = appearance.personObjectUuid;
        
        // Skip invalid UUIDs
        if (videoUuid.isEmpty || videoUuid.length < 8) {
          print('🚦   ⚠️ Appearance $ai: skipping invalid video UUID: "$videoUuid"');
          continue;
        }
        if (personObjectUuid.isEmpty || personObjectUuid.length < 8) {
          print('🚦   ⚠️ Appearance $ai: skipping invalid person object UUID: "$personObjectUuid"');
          continue;
        }
        
        print('🚦   Appearance $ai: video=${videoUuid.substring(0, 8)}, person_object=${personObjectUuid.substring(0, 8)}');

        // Get the routes data for this video
        final videoData = videoRoutesMap[videoUuid];
        if (videoData == null) {
          print('🚦   ⚠️ No route data for video $videoUuid');
          continue;
        }

        // Find the person group that matches this person_object_uuid
        final personGroupsData = videoData['group_tracking'] ?? videoData['person_groups'];
        if (personGroupsData == null) {
          print('🚦   ⚠️ No person_groups in video data');
          continue;
        }

        final personGroupsList = personGroupsData as List<dynamic>;
        
        print('🚦   Video has ${personGroupsList.length} person group(s)');
        
        // IMPORTANT: Since the person_object_uuid in cross-video tracking is mock/fake,
        // we'll use ALL person groups from this video appearance.
        // For most cases there's only 1 person per video, so this works well.
        // For videos with multiple people, we take all routes (future: need better matching)
        
        for (int gi = 0; gi < personGroupsList.length; gi++) {
          final group = personGroupsList[gi] as Map<String, dynamic>;
          
          print('🚦     Processing group $gi (${group['person_id']})');
          
          // Extract route points from this group
          final movementTracking = group['movement_tracking'] as Map<String, dynamic>?;
          if (movementTracking != null) {
            final routePoints = movementTracking['route_points'] as List<dynamic>? ?? [];
            
            print('🚦       ✅ Found ${routePoints.length} route points from ${group['person_id']}');
            
            // Add all route points from this group
            for (final point in routePoints) {
              allRoutePoints.add(point as Map<String, dynamic>);
            }
          } else {
            print('🚦       ⚠️ No movement_tracking in group');
          }
        }
      }

      if (allRoutePoints.isEmpty) {
        print('🚦 Individual $i: ⚠️ No route points found');
        continue;
      }

      // Sort all route points by timestamp or frame_number
      allRoutePoints.sort((a, b) {
        // Handle different timestamp formats
        try {
          final timestampA = a['timestamp'];
          final timestampB = b['timestamp'];
          
          // If timestamp is a string (ISO format), parse as DateTime
          if (timestampA is String && timestampB is String) {
            final timeA = DateTime.parse(timestampA);
            final timeB = DateTime.parse(timestampB);
            return timeA.compareTo(timeB);
          }
          
          // If timestamp is a number (Unix timestamp or frame number), compare directly
          if (timestampA is num && timestampB is num) {
            return timestampA.compareTo(timestampB);
          }
          
          // Fallback: try to use frame_number if timestamp comparison fails
          final frameA = a['frame_number'] as num? ?? 0;
          final frameB = b['frame_number'] as num? ?? 0;
          return frameA.compareTo(frameB);
        } catch (e) {
          print('🚦 Warning: Could not compare timestamps: $e');
          // Fallback to frame number
          final frameA = a['frame_number'] as num? ?? 0;
          final frameB = b['frame_number'] as num? ?? 0;
          return frameA.compareTo(frameB);
        }
      });

      print('🚦 Individual $i: ✅ Combined ${allRoutePoints.length} route points from ${analysis.appearances.length} appearances');

      // Sample route points if there are too many (threshold: 100 points)
      const maxRoutePoints = 100;
      List<Map<String, dynamic>> sampledRoutePoints = allRoutePoints;
      
      if (allRoutePoints.length > maxRoutePoints) {
        // Calculate sampling interval
        final interval = (allRoutePoints.length / maxRoutePoints).ceil();
        sampledRoutePoints = [];
        
        // Always include first and last points
        sampledRoutePoints.add(allRoutePoints.first);
        
        // Sample intermediate points
        for (int j = interval; j < allRoutePoints.length - 1; j += interval) {
          sampledRoutePoints.add(allRoutePoints[j]);
        }
        
        // Always include last point
        if (allRoutePoints.length > 1) {
          sampledRoutePoints.add(allRoutePoints.last);
        }
        
        print('🚦 Individual $i: 📊 Sampled ${allRoutePoints.length} points down to ${sampledRoutePoints.length} points (threshold: $maxRoutePoints)');
      }

      // Create unified person group
      personGroups.add({
        'person_id': individualId,
        'total_detections': allRoutePoints.length, // Keep original count
        'sampled_points': sampledRoutePoints.length, // Add sampled count
        'movement_tracking': {
          'route_points': sampledRoutePoints, // Use sampled points for rendering
          'total_distance': 0.0,
          'movement_duration': analysis.totalDurationSeconds,
        },
      });
    }

    print('🚦 CROSS-VIDEO ROUTES: ✅ Final result: ${personGroups.length} person groups with route data');
    return personGroups;
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
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
    } catch (e) {
      return timestamp.toString();
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
                icon: Icon(Icons.notifications_active),
                text: 'Triggers',
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

  /// Build Insights tab - AI-powered behavioral insights
  Widget _buildInsightsTab() {
    // Use the same statistics calculations as Statistics tab
    return _buildStatisticsTabCrossVideo();
  }

  /// Build Attendance tab - Time-based presence tracking
  Widget _buildAttendanceTab() {
    if (_aggregatedAnalyses == null || _aggregatedAnalyses!.isEmpty) {
      return const Center(child: Text('No attendance data available'));
    }

    return SingleChildScrollView(
      child: Column(
        children: [
          // Header
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
                        'Attendance Timeline',
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
          
          // Attendance graph
          Center(
            child: Container(
              height: math.max(400, _aggregatedAnalyses!.length * 60.0),
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black12,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: CustomPaint(
                  painter: AttendanceGraphPainter(_aggregatedAnalyses!),
                  size: Size.infinite,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Build Triggers tab - Event-based notifications and alerts
  Widget _buildTriggersTab() {
    // Use the new API-integrated triggers widget
    return const TriggersTab();
  }

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

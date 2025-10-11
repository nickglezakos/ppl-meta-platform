import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:ui' as ui;
import 'dart:io';
import 'dart:async';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import '../models/person_objects_models.dart';
import '../providers/person_objects_provider.dart';
import '../widgets/custom_app_bar.dart';
import '../models/media_models.dart';
import '../core/api/api_client.dart';

/// Detailed screen for viewing person objects results and analysis
class PersonObjectsDetailScreen extends ConsumerStatefulWidget {
  final MediaItem mediaItem;

  const PersonObjectsDetailScreen({
    super.key,
    required this.mediaItem,
  });

  @override
  ConsumerState<PersonObjectsDetailScreen> createState() => 
      _PersonObjectsDetailScreenState();
}

class _PersonObjectsDetailScreenState 
    extends ConsumerState<PersonObjectsDetailScreen> 
    with SingleTickerProviderStateMixin {
  
  late TabController _tabController;
  final Set<String> _debuggedFaces = {}; // Cache for debug output

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Person Objects Analysis',
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Analysis',
            onPressed: () => _refreshAnalysis(),
          ),
          IconButton(
            icon: const Icon(Icons.play_arrow),
            tooltip: 'Trigger New Analysis',
            onPressed: () => _triggerNewAnalysis(),
          ),
        ],
      ),
      body: Column(
        children: [
          TabBar(
            controller: _tabController,
            tabs: const [
              Tab(
                icon: Icon(Icons.analytics),
                text: 'Overview',
              ),
              Tab(
                icon: Icon(Icons.groups),
                text: 'Persons',
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
                _buildOverviewTab(),
                _buildPersonGroupsTab(),
                _buildFaceDetailsTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem.uuid));
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
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem.uuid));

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
    final dataAsync = ref.watch(personObjectsDataProvider(widget.mediaItem.uuid));

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
    ref.invalidate(personObjectsDataProvider(widget.mediaItem.uuid));
    ref.invalidate(personObjectsWorkflowControllerProvider);
  }

  void _triggerNewAnalysis() async {
    try {
      final controller = ref.read(personObjectsWorkflowControllerProvider.notifier);
      await controller.autoTriggerWorkflow(widget.mediaItem.uuid);
      
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
        final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem.uuid}/frame/$frameNumber?format=jpeg';
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
        final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem.uuid}/frame/$frameNumber?format=jpeg';
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
      final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem.uuid}/frame/$frameNumber?format=jpeg';
      
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
      final frameUrl = 'http://localhost:8080/api/v1/media/${widget.mediaItem.uuid}/frame/$frameNumber?format=jpeg';
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
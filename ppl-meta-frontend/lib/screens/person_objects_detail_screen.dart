import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/person_objects_models.dart';
import '../providers/person_objects_provider.dart';
import '../widgets/custom_app_bar.dart';
import '../models/media_models.dart';

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
                text: 'Person Groups',
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
        final group = {
          'person_uuid': 'uuid_$personId',
          'person_id': personId,
          'face_count': faces.length,
          'representative_faces': faces.map((face) => {
            'face_data': {
              'bbox': [face.positionX - 50, face.positionY - 50, face.positionX + 50, face.positionY + 50],
              'confidence': 0.5,
              'frame_number': face.frameNumber,
              'timestamp': face.frameNumber * 0.033, // Approximate timestamp
              'distance_from_camera': (face.matchDistance * 10).clamp(15.0, 50.0), // Convert quality to distance
              'center_x': face.positionX,
              'center_y': face.positionY,
              'face_width': 100,
              'face_height': 100,
              'face_area': 10000,
            },
            'quality_score': face.matchDistance,
            'selection_rank': faces.indexOf(face) + 1,
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

    return Card(
      margin: const EdgeInsets.only(bottom: 16.0),
      elevation: 4,
      child: ExpansionTile(
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
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Representative Faces Section
                _buildRepresentativeFacesSection(representativeFaces),
                
                const SizedBox(height: 16),
                
                // Statistics Grid
                _buildPersonGroupStatistics(spatialBounds, temporalSpan, movementStats, qualityMetrics),
                
                const SizedBox(height: 16),
                
                // Action Buttons
                _buildPersonGroupActions(group),
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
}
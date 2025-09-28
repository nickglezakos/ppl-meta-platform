import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../models/person_objects_models.dart';
import '../providers/person_objects_provider.dart';
import '../widgets/person_objects_components.dart';
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

        if (data.groupTracking.isEmpty) {
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
          itemCount: data.groupTracking.length,
          itemBuilder: (context, index) {
            final group = data.groupTracking[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 12.0),
              child: ExpansionTile(
                leading: CircleAvatar(
                  backgroundColor: Colors.blue.shade100,
                  child: Text(
                    '${index + 1}',
                    style: TextStyle(
                      color: Colors.blue.shade700,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                title: Text('Person Group ${index + 1}'),
                subtitle: Text(
                  'Group ID: ${group.mergedGroupId}\n'
                  'Faces: ${group.faceCount}\n'
                  'Tracking: ${group.trackingBased ? "Yes" : "No"}',
                ),
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Group Information:',
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text('Tolerance: ${group.tolerancePercent}%'),
                        Text('Y-Coordinate Based: ${group.yCoordinateBased}'),
                        Text('Average Position: (${group.averagePosition.x.toStringAsFixed(1)}, ${group.averagePosition.y.toStringAsFixed(1)})'),
                      ],
                    ),
                  ),
                ],
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
                  face.matchDistance < 0.3 ? Icons.check_circle : Icons.warning,
                  color: face.matchDistance < 0.3 ? Colors.green : Colors.orange,
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
                    Text('Total Groups: ${data.groupTracking.length}'),
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

  Widget _buildBestQualityFaceCard(BestQualityFace face) {
    return Card(
      color: Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Face ID: ${face.faceId}'),
            Text('Quality Score: ${(face.qualityScore * 100).toStringAsFixed(1)}%'),
            Text('Frame: ${face.frameNumber}'),
            // Commented out bbox access for now
            // if (face.bbox != null && face.bbox!.length >= 4)
            //   Text('Position: (${face.bbox![0]}, ${face.bbox![1]}) Size: ${face.bbox![2]}x${face.bbox![3]}'),
          ],
        ),
      ),
    );
  }

  Widget _buildFaceListItem(ClassifiedFace face) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8.0),
      child: ListTile(
        dense: true,
        leading: CircleAvatar(
          radius: 16,
          backgroundColor: _getDistanceColor(face.matchDistance),
          child: const Icon(Icons.face, size: 16, color: Colors.white),
        ),
        title: Text('Face ${face.faceDetectionId}'),
        subtitle: Text('Person: ${face.personId} (${face.matchType})'),
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
/// PPL Meta Frontend - Person Objects UI Components
/// 
/// Reusable UI components for displaying PPL Thread (Person Objects) data
/// in the media preview screen and other parts of the application.
/// 
/// Key Features:
/// - Compact person objects status display
/// - Detailed person objects information panels
/// - Person group visualization and interaction
/// - Best quality faces display with age detection
/// - Statistics and efficiency visualization
/// - Seamless integration with existing UI design

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/person_objects_models.dart';
import '../providers/person_objects_provider.dart';

/// Compact person objects status display for media preview cards
class PersonObjectsStatusChip extends ConsumerWidget {
  final String mediaUuid;
  final bool showDetails;

  const PersonObjectsStatusChip({
    Key? key,
    required this.mediaUuid,
    this.showDetails = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaUuid));
    final workflowState = ref.watch(personObjectsWorkflowControllerProvider);

    return personObjectsAsync.when(
      data: (data) {
        if (data != null) {
          return _buildPersonObjectsChip(context, data, showDetails);
        } else if (workflowState == PersonObjectsWorkflowState.processing ||
                   workflowState == PersonObjectsWorkflowState.triggering) {
          return _buildProcessingChip(context);
        } else {
          return _buildNotAvailableChip(context);
        }
      },
      loading: () => _buildLoadingChip(context),
      error: (error, stack) => _buildErrorChip(context),
    );
  }

  Widget _buildPersonObjectsChip(BuildContext context, PersonObjectsData data, bool showDetails) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.blue.shade100,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade300),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.groups,
            size: 16,
            color: Colors.blue.shade700,
          ),
          const SizedBox(width: 4),
          Text(
            showDetails ? data.summary.detailedSummary : data.summary.compactSummary,
            style: theme.textTheme.bodySmall?.copyWith(
              color: Colors.blue.shade700,
              fontWeight: FontWeight.w500,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildProcessingChip(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.orange.shade100,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.orange.shade300),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(Colors.orange.shade700),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            'Processing persons...',
            style: theme.textTheme.bodySmall?.copyWith(
              color: Colors.orange.shade700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingChip(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.grey.shade200,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(Colors.grey.shade600),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            'Loading...',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey.shade600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNotAvailableChip(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.groups_outlined,
            size: 16,
            color: Colors.grey.shade600,
          ),
          const SizedBox(width: 4),
          Text(
            'No person data',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey.shade600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorChip(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.red.shade100,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.shade300),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.error_outline,
            size: 16,
            color: Colors.red.shade700,
          ),
          const SizedBox(width: 4),
          Text(
            'Error loading',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.red.shade700,
            ),
          ),
        ],
      ),
    );
  }
}

/// Detailed person objects information panel
class PersonObjectsInfoPanel extends ConsumerWidget {
  final String mediaUuid;
  final bool showTriggerButton;
  final VoidCallback? onViewDetails;

  const PersonObjectsInfoPanel({
    Key? key,
    required this.mediaUuid,
    this.showTriggerButton = true,
    this.onViewDetails,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaUuid));
    final workflowState = ref.watch(personObjectsWorkflowControllerProvider);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.groups, color: Theme.of(context).primaryColor),
                const SizedBox(width: 8),
                Text(
                  'Person Objects',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                if (onViewDetails != null)
                  TextButton.icon(
                    onPressed: onViewDetails,
                    icon: const Icon(Icons.open_in_new, size: 16),
                    label: const Text('Details'),
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    ),
                  ),
                if (showTriggerButton) ...[
                  if (onViewDetails != null) const SizedBox(width: 8),
                  _buildTriggerButton(context, ref, workflowState),
                ],
              ],
            ),
            const SizedBox(height: 16),
            personObjectsAsync.when(
              data: (data) => data != null
                  ? _buildPersonObjectsDetails(context, data)
                  : _buildNoDataMessage(context),
              loading: () => _buildLoadingState(context),
              error: (error, stack) => _buildErrorState(context, error),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTriggerButton(BuildContext context, WidgetRef ref, PersonObjectsWorkflowState state) {
    final isProcessing = state == PersonObjectsWorkflowState.processing ||
                        state == PersonObjectsWorkflowState.triggering;

    return ElevatedButton.icon(
      onPressed: isProcessing ? null : () => _triggerWorkflow(ref),
      icon: isProcessing
          ? SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(Icons.play_arrow),
      label: Text(isProcessing ? 'Processing...' : 'Generate'),
      style: ElevatedButton.styleFrom(
        backgroundColor: Theme.of(context).primaryColor,
        foregroundColor: Colors.white,
      ),
    );
  }

  Widget _buildPersonObjectsDetails(BuildContext context, PersonObjectsData data) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Summary statistics
        _buildStatisticsGrid(context, data),
        
        const SizedBox(height: 16),
        
        // Person groups list
        if (data.groupTracking.isNotEmpty) ...[
          Text(
            'Person Groups (${data.groupTracking.length})',
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ...data.groupTracking.take(5).map((group) =>
            _buildPersonGroupItem(context, group, data.bestQualityFaces[group.mergedGroupId])),
          
          if (data.groupTracking.length > 5)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                '... and ${data.groupTracking.length - 5} more persons',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: Colors.grey.shade600,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
        ],
      ],
    );
  }

  Widget _buildStatisticsGrid(BuildContext context, PersonObjectsData data) {
    final stats = data.statistics;
    
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      childAspectRatio: 3,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      children: [
        _buildStatItem(context, 'Persons', '${data.totalPersons}', Icons.person),
        _buildStatItem(context, 'Total Faces', '${data.originalGroups}', Icons.face),
        _buildStatItem(context, 'Efficiency', '${stats.groupingEfficiency.toStringAsFixed(1)}%', Icons.trending_up),
        _buildStatItem(context, 'Frames', '${stats.framesProcessed}', Icons.movie),
      ],
    );
  }

  Widget _buildStatItem(BuildContext context, String label, String value, IconData icon) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.primaryColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: theme.primaryColor.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: theme.primaryColor),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.primaryColor,
                  ),
                ),
                Text(
                  label,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Colors.grey.shade600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPersonGroupItem(BuildContext context, PersonGroup group, BestQualityFace? bestFace) {
    final theme = Theme.of(context);
    
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Row(
        children: [
          // Person icon with face count
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: theme.primaryColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Center(
              child: Text(
                '${group.faceCount}',
                style: theme.textTheme.labelMedium?.copyWith(
                  color: theme.primaryColor,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          
          const SizedBox(width: 12),
          
          // Person details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Person ${group.mergedGroupId.substring(0, 8)}',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  '${group.faceCount} faces • Position: (${group.averagePosition.x.toStringAsFixed(0)}, ${group.averagePosition.y.toStringAsFixed(0)})',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Colors.grey.shade600,
                  ),
                ),
                if (bestFace != null) ...[
                  Text(
                    'Quality: ${bestFace.qualityPercentage} • ${bestFace.ageDetection.displayAge}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          // Quality indicator
          if (bestFace != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: _getQualityColor(bestFace.qualityScore).withOpacity(0.2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                bestFace.qualityPercentage,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: _getQualityColor(bestFace.qualityScore),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Color _getQualityColor(double qualityScore) {
    if (qualityScore >= 0.8) return Colors.green;
    if (qualityScore >= 0.6) return Colors.orange;
    return Colors.red;
  }

  Widget _buildNoDataMessage(BuildContext context) {
    return Center(
      child: Column(
        children: [
          Icon(
            Icons.groups_outlined,
            size: 48,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            'No person objects available',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Generate person objects from face detections to see grouped individuals',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey.shade500,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState(BuildContext context) {
    return Center(
      child: Column(
        children: [
          CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            'Loading person objects...',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey.shade600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, Object error) {
    return Center(
      child: Column(
        children: [
          Icon(
            Icons.error_outline,
            size: 48,
            color: Colors.red.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            'Error loading person objects',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.red.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error.toString(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey.shade600,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Future<void> _triggerWorkflow(WidgetRef ref) async {
    try {
      final controller = ref.read(personObjectsWorkflowControllerProvider.notifier);
      await controller.autoTriggerWorkflow(mediaUuid);
      
      // Refresh data after workflow completion
      ref.invalidate(personObjectsDataProvider(mediaUuid));
      
    } catch (e) {
      // Handle error - could show a snackbar or dialog
      debugPrint('Failed to trigger person objects workflow: $e');
    }
  }
}

/// Simple person objects count display for compact spaces
class PersonObjectsCountDisplay extends ConsumerWidget {
  final String mediaUuid;

  const PersonObjectsCountDisplay({
    Key? key,
    required this.mediaUuid,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaUuid));

    return personObjectsAsync.when(
      data: (data) => data != null
          ? Text(
              '${data.totalPersons} persons',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.blue.shade700,
                fontWeight: FontWeight.w500,
              ),
            )
          : const SizedBox.shrink(),
      loading: () => SizedBox(
        width: 12,
        height: 12,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      error: (error, stack) => const SizedBox.shrink(),
    );
  }
}
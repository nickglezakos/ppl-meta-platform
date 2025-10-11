/// PPL Meta Frontend - Enhanced Person Counter with Drill-Down
/// 
/// Enhanced counter widget that displays person groups with distance-based colors
/// and provides drill-down functionality to detailed analytics views.

import 'package:flutter/material.dart';
import '../models/person_group_models.dart';
import 'person_group_detail_view.dart';

class EnhancedPersonCounter extends StatelessWidget {
  final int totalPersons;
  final int totalFaces;
  final List<PersonObjectGroup> personGroups;
  final String groupingMethod;
  final double processingTime;
  final String sessionUuid;
  final bool isLoading;
  final String? error;

  const EnhancedPersonCounter({
    Key? key,
    required this.totalPersons,
    required this.totalFaces,
    required this.personGroups,
    this.groupingMethod = 'rectangle_overlap_detection',
    this.processingTime = 0.0,
    this.sessionUuid = '',
    this.isLoading = false,
    this.error,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      margin: const EdgeInsets.all(8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with title
            Row(
              children: [
                const Icon(Icons.people, size: 24, color: Colors.blue),
                const SizedBox(width: 8),
                const Text(
                  'Person Analytics',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                if (isLoading)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
            const SizedBox(height: 16),

            // Error state
            if (error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red[200]!),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: Colors.red[600], size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        error!,
                        style: TextStyle(color: Colors.red[700]),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Main counters
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildCounterColumn(
                  'Persons',
                  totalPersons,
                  Icons.people,
                  Colors.blue,
                ),
                _buildCounterColumn(
                  'Faces',
                  totalFaces,
                  Icons.face,
                  Colors.green,
                ),
                if (personGroups.isNotEmpty)
                  _buildCounterColumn(
                    'Avg Quality',
                    _calculateAverageQuality().toStringAsFixed(0),
                    Icons.star,
                    Colors.orange,
                  ),
              ],
            ),

            const SizedBox(height: 16),

            // Algorithm and processing info
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Algorithm: ${_formatAlgorithmName(groupingMethod)}',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                      ),
                      Text(
                        'Processing: ${processingTime.toStringAsFixed(1)}ms',
                        style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                      ),
                    ],
                  ),
                  if (sessionUuid.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Session: ${sessionUuid.substring(0, 8)}...',
                      style: TextStyle(fontSize: 10, color: Colors.grey[500]),
                    ),
                  ],
                ],
              ),
            ),

            // Person groups section
            if (personGroups.isNotEmpty) ...[
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Person Groups:',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    'Tap for details',
                    style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              
              // Person groups list
              ...personGroups.map((group) => _buildPersonGroupSummary(context, group)),
            ],
          ],
        ),
      ),
    );
  }

  /// Build counter column with icon, value, and label
  Widget _buildCounterColumn(String label, dynamic value, IconData icon, Color color) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 24, color: color),
        ),
        const SizedBox(height: 8),
        Text(
          value.toString(),
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  /// Build person group summary with distance-based color coding
  Widget _buildPersonGroupSummary(BuildContext context, PersonObjectGroup group) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 2),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _showPersonGroupDrillDown(context, group),
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: group.distanceColor.withOpacity(0.05),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: group.distanceColor.withOpacity(0.2)),
            ),
            child: Row(
              children: [
                // Person icon with distance-based color
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: group.distanceColor,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.person,
                    size: 16,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 12),

                // Person info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            group.personId,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: group.distanceColor.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              getDistanceCategoryName(group.closestDistance),
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: group.distanceColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Text(
                            '${group.faceCount} faces',
                            style: const TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '•',
                            style: TextStyle(fontSize: 12, color: Colors.grey[400]),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Quality: ${group.qualityMetrics.averageQuality.toStringAsFixed(0)}',
                            style: const TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                // Distance and drill-down indicator
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '${group.closestDistance.toStringAsFixed(1)}m',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: group.distanceColor,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${group.temporalSpan.durationSeconds.toStringAsFixed(1)}s',
                          style: const TextStyle(fontSize: 10, color: Colors.grey),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          Icons.chevron_right,
                          size: 16,
                          color: Colors.grey[400],
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Navigate to person group drill-down view
  void _showPersonGroupDrillDown(BuildContext context, PersonObjectGroup group) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => PersonGroupDetailView(group: group),
      ),
    );
  }

  /// Calculate average quality across all person groups
  double _calculateAverageQuality() {
    if (personGroups.isEmpty) return 0.0;
    final totalQuality = personGroups
        .map((group) => group.qualityMetrics.averageQuality)
        .reduce((a, b) => a + b);
    return totalQuality / personGroups.length;
  }

  /// Format algorithm name for display
  String _formatAlgorithmName(String algorithm) {
    switch (algorithm.toLowerCase()) {
      case 'rectangle_overlap_detection':
        return 'Rectangle Overlap';
      case 'face_clustering':
        return 'Face Clustering';
      case 'spatial_grouping':
        return 'Spatial Grouping';
      default:
        return algorithm.replaceAll('_', ' ').split(' ')
            .map((word) => word[0].toUpperCase() + word.substring(1))
            .join(' ');
    }
  }
}

/// Simplified person counter for basic use cases
class SimplePersonCounter extends StatelessWidget {
  final int totalPersons;
  final int totalFaces;
  final bool isLoading;

  const SimplePersonCounter({
    Key? key,
    required this.totalPersons,
    required this.totalFaces,
    this.isLoading = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _buildSimpleCounter('Persons', totalPersons, Icons.people, Colors.blue),
            Container(
              width: 1,
              height: 40,
              color: Colors.grey[300],
            ),
            _buildSimpleCounter('Faces', totalFaces, Icons.face, Colors.green),
            if (isLoading) ...[
              Container(
                width: 1,
                height: 40,
                color: Colors.grey[300],
              ),
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSimpleCounter(String label, int count, IconData icon, Color color) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 24, color: color),
        const SizedBox(height: 4),
        Text(
          count.toString(),
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}

/// Person counter summary card for dashboard views
class PersonCounterSummaryCard extends StatelessWidget {
  final List<PersonObjectGroup> personGroups;
  final String title;
  final VoidCallback? onViewAll;

  const PersonCounterSummaryCard({
    Key? key,
    required this.personGroups,
    this.title = 'Recent Detections',
    this.onViewAll,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final totalPersons = personGroups.length;
    final totalFaces = personGroups.fold(0, (sum, group) => sum + group.faceCount);
    final avgQuality = personGroups.isEmpty 
        ? 0.0 
        : personGroups.map((g) => g.qualityMetrics.averageQuality).reduce((a, b) => a + b) / personGroups.length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (onViewAll != null)
                  TextButton(
                    onPressed: onViewAll,
                    child: const Text('View All'),
                  ),
              ],
            ),
            const SizedBox(height: 12),

            // Summary stats
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildSummaryItem('Persons', totalPersons.toString(), Icons.people, Colors.blue),
                _buildSummaryItem('Faces', totalFaces.toString(), Icons.face, Colors.green),
                _buildSummaryItem('Quality', avgQuality.toStringAsFixed(0), Icons.star, Colors.orange),
              ],
            ),

            if (personGroups.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),

              // Distance distribution
              Text(
                'Distance Distribution:',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: Colors.grey[700],
                ),
              ),
              const SizedBox(height: 8),
              _buildDistanceDistribution(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.grey,
          ),
        ),
      ],
    );
  }

  Widget _buildDistanceDistribution() {
    final distanceCategories = <String, int>{};
    
    for (final group in personGroups) {
      final category = getDistanceCategoryName(group.closestDistance);
      distanceCategories[category] = (distanceCategories[category] ?? 0) + 1;
    }

    return Column(
      children: distanceCategories.entries.map((entry) {
        final percentage = (entry.value / personGroups.length * 100).round();
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: Row(
            children: [
              SizedBox(
                width: 80,
                child: Text(
                  entry.key,
                  style: const TextStyle(fontSize: 12),
                ),
              ),
              Expanded(
                child: LinearProgressIndicator(
                  value: entry.value / personGroups.length,
                  backgroundColor: Colors.grey[200],
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _getCategoryColor(entry.key),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '$percentage%',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Color _getCategoryColor(String category) {
    switch (category) {
      case 'Very Close':
        return Colors.red;
      case 'Close':
        return Colors.orange;
      case 'Medium':
        return Colors.yellow;
      case 'Far':
        return Colors.green;
      case 'Very Far':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }
}
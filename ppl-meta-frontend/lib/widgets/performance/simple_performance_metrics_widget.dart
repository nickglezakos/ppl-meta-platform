import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/face_detection_models.dart';
import '../../providers/workflow_providers.dart';

/// Simplified performance metrics display widget using existing infrastructure
class PerformanceMetricsDisplayWidget extends ConsumerWidget {
  final bool showDetailedView;
  
  const PerformanceMetricsDisplayWidget({
    super.key,
    this.showDetailedView = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final metricsAsync = ref.watch(performanceMetricsProvider);
    
    return Card(
      margin: const EdgeInsets.all(16.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Performance Metrics',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            metricsAsync.when(
              data: (metrics) => _buildMetricsContent(metrics),
              loading: () => const Center(
                child: CircularProgressIndicator(),
              ),
              error: (error, stack) => Center(
                child: Column(
                  children: [
                    const Icon(
                      Icons.error,
                      color: Colors.red,
                      size: 48,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Error loading metrics: $error',
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricsContent(WorkflowPerformanceMetrics metrics) {
    return Column(
      children: [
        // Performance summary cards
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: _buildMetricCard(
                'CPU Reduction',
                '${(metrics.cpuUsageReduction * 100).toStringAsFixed(1)}%',
                Icons.memory,
                Colors.green,
              ),
            ),
            const SizedBox(width: 12),
            Flexible(
              child: _buildMetricCard(
                'Memory Reduction',
                '${(metrics.memoryUsageReduction * 100).toStringAsFixed(1)}%',
                Icons.storage,
                Colors.blue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: _buildMetricCard(
                'Active Sessions',
                '${metrics.activeSessionsCount}',
                Icons.play_circle_filled,
                Colors.orange,
              ),
            ),
            const SizedBox(width: 12),
            Flexible(
              child: _buildMetricCard(
                'Videos Processed',
                '${metrics.processedVideosCount}',
                Icons.video_library,
                Colors.purple,
              ),
            ),
          ],
        ),
        if (showDetailedView) ...[
          const SizedBox(height: 16),
          _buildDetailedMetrics(metrics),
        ],
      ],
    );
  }

  Widget _buildMetricCard(
    String title,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailedMetrics(WorkflowPerformanceMetrics metrics) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Detailed Performance',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          if (metrics.avgProcessingTimeSeconds != null)
            _buildDetailRow(
              'Avg Processing Time',
              '${metrics.avgProcessingTimeSeconds!.toStringAsFixed(2)}s',
              Icons.timer,
            ),
          if (metrics.totalFacesDetected != null)
            _buildDetailRow(
              'Total Faces Detected',
              '${metrics.totalFacesDetected}',
              Icons.face,
            ),
          if (metrics.systemCpuUsage != null)
            _buildDetailRow(
              'System CPU Usage',
              '${(metrics.systemCpuUsage! * 100).toStringAsFixed(1)}%',
              Icons.memory,
            ),
          if (metrics.systemMemoryUsage != null)
            _buildDetailRow(
              'System Memory Usage',
              '${(metrics.systemMemoryUsage! * 100).toStringAsFixed(1)}%',
              Icons.storage,
            ),
          _buildDetailRow(
            'Last Updated',
            _formatDateTime(metrics.lastUpdated),
            Icons.update,
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey.shade600),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: Colors.grey.shade700,
                fontSize: 14,
              ),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
}
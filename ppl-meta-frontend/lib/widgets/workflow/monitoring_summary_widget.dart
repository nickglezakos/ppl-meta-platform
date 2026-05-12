import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/monitoring_providers.dart';
import 'monitoring_charts_widget.dart';

/// Unified monitoring summary widget for the dashboard overview tab.
/// Displays aggregated metrics with manual refresh control.
class MonitoringSummaryWidget extends ConsumerWidget {
  const MonitoringSummaryWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(monitoringSummaryProvider);

    return summary.when(
      data: (data) => _buildSummaryContent(context, data, ref),
      loading: () => _buildLoadingState(),
      error: (error, stack) => _buildErrorState(error),
    );
  }

  Widget _buildSummaryContent(
    BuildContext context,
    MonitoringSummary summary,
    WidgetRef ref,
  ) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with manual refresh
          _buildHeader(context, summary, ref),
          
          const SizedBox(height: 24),
          
          // System Health Card
          _buildHealthCard(context, summary.systemHealth),
          
          const SizedBox(height: 16),
          
          // Metrics Grid
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _buildLowLevelCard(context, summary.lowLevelWorkflows),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildHighLevelCard(context, summary.highLevelWorkflows),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          
          // Charts Section
          Text(
            'Analytics',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          const MonitoringChartsWidget(),
        ],
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    MonitoringSummary summary,
    WidgetRef ref,
  ) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Monitoring Overview',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(
                  summary.fromCache ? Icons.memory : Icons.refresh,
                  size: 14,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 4),
                Text(
                  summary.fromCache 
                      ? 'Cached (${summary.cacheTtl}s TTL)'
                      : 'Fresh data',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  '•',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(width: 8),
                Text(
                  _formatTimestamp(summary.timestamp),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
        ElevatedButton.icon(
          onPressed: () {
            ref.read(monitoringRefreshProvider.notifier).refresh();
            ref.invalidate(monitoringSummaryProvider);
          },
          icon: const Icon(Icons.refresh, size: 18),
          label: const Text('Refresh'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
          ),
        ),
      ],
    );
  }

  Widget _buildHealthCard(BuildContext context, SystemHealth health) {
    final color = _getHealthColor(health.color);
    final icon = _getHealthIcon(health.status);
    
    return Card(
      elevation: 2,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: color.withOpacity(0.3),
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: 32),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'System Health',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    health.message,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  if (health.stuckWorkflows > 0 || health.recentFailures > 0) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 12,
                      children: [
                        if (health.stuckWorkflows > 0)
                          _buildHealthBadge(
                            '${health.stuckWorkflows} stuck',
                            AppColors.warning,
                          ),
                        if (health.recentFailures > 0)
                          _buildHealthBadge(
                            '${health.recentFailures} failures',
                            AppColors.error,
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: color.withOpacity(0.3)),
              ),
              child: Text(
                health.status.toUpperCase(),
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLowLevelCard(BuildContext context, LowLevelWorkflows data) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildCardHeader(
              context,
              icon: Icons.face,
              iconColor: AppColors.primary,
              title: 'Face Detection',
            ),
            const SizedBox(height: 20),
            _buildMetricRow(
              context,
              'Active Sessions',
              data.activeSessions.toString(),
              Icons.play_circle,
              data.activeSessions > 0 ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Completed (Total)',
              data.completedWorkflows.toString(),
              Icons.check_circle,
              AppColors.success,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Completed (24h)',
              data.completedMethods24h.toString(),
              Icons.auto_awesome,
              AppColors.success,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Avg Processing Time',
              '${data.avgProcessingTimeSeconds.toStringAsFixed(1)}s',
              Icons.speed,
              AppColors.textPrimary,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Success Rate (24h)',
              '${data.successRate24h.toStringAsFixed(1)}%',
              Icons.trending_up,
              data.successRate24h >= 95 ? AppColors.success : AppColors.warning,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHighLevelCard(BuildContext context, HighLevelWorkflows data) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildCardHeader(
              context,
              icon: Icons.group,
              iconColor: AppColors.secondary,
              title: 'MVR & Tracking',
            ),
            const SizedBox(height: 20),
            _buildMetricRow(
              context,
              'Active MVR People',
              data.totalIndividuals.toString(),
              Icons.person,
              AppColors.textPrimary,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'MVR Created (Today)',
              data.personObjectsToday.toString(),
              Icons.face_retouching_natural,
              AppColors.success,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Cross-Video Matches (Today)',
              data.crossVideoMatchesToday.toString(),
              Icons.compare_arrows,
              AppColors.primary,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Total Merges (7d)',
              data.totalMerges.toString(),
              Icons.merge_type,
              AppColors.secondary,
            ),
            const SizedBox(height: 12),
            _buildMetricRow(
              context,
              'Total Mappings (7d)',
              data.totalMappings.toString(),
              Icons.link,
              AppColors.info,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricRow(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Row(
      children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildCardHeader(
    BuildContext context, {
    required IconData icon,
    required Color iconColor,
    required String title,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final iconBadge = Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            icon,
            color: iconColor,
            size: 24,
          ),
        );

        final titleText = Text(
          title,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        );

        if (constraints.maxWidth < 180) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              iconBadge,
              const SizedBox(height: 12),
              titleText,
            ],
          );
        }

        return Row(
          children: [
            iconBadge,
            const SizedBox(width: 12),
            Expanded(child: titleText),
          ],
        );
      },
    );
  }

  Widget _buildHealthBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: CircularProgressIndicator(),
      ),
    );
  }

  Widget _buildErrorState(Object error) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              color: AppColors.error,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Failed to load monitoring data',
              style: TextStyle(
                color: AppColors.error,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              error.toString(),
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Color _getHealthColor(String color) {
    switch (color.toLowerCase()) {
      case 'green':
        return AppColors.success;
      case 'orange':
      case 'yellow':
        return AppColors.warning;
      case 'red':
        return AppColors.error;
      default:
        return AppColors.textSecondary;
    }
  }

  IconData _getHealthIcon(String status) {
    switch (status.toLowerCase()) {
      case 'healthy':
        return Icons.check_circle;
      case 'degraded':
        return Icons.warning;
      case 'unhealthy':
      case 'error':
        return Icons.error;
      default:
        return Icons.help;
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    
    if (diff.inSeconds < 60) {
      return '${diff.inSeconds}s ago';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else {
      return '${diff.inHours}h ago';
    }
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../models/workflow_widget_models.dart';
import '../../services/workflow_widget_api_client.dart';
import '../../core/providers/auth_provider.dart';
import 'authenticated_workflow_wrapper.dart';

/// Widget for displaying processing analytics, metrics, and recommendations
class AnalyticsDashboardWidget extends ConsumerStatefulWidget {
  final String mediaUuid;
  final bool showRecommendations;
  final bool autoRefresh;

  const AnalyticsDashboardWidget({
    super.key,
    required this.mediaUuid,
    this.showRecommendations = true,
    this.autoRefresh = true,
  });

  @override
  ConsumerState<AnalyticsDashboardWidget> createState() => _AnalyticsDashboardWidgetState();
}

class _AnalyticsDashboardWidgetState extends ConsumerState<AnalyticsDashboardWidget> {
  WidgetAnalyticsResponse? _analytics;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadAnalytics();
  }

  Future<void> _loadAnalytics() async {
    final apiClient = ref.read(workflowWidgetApiClientProvider);
    if (apiClient == null) {
      setState(() {
        _error = 'Authentication required';
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await apiClient.getWidgetProcessingAnalytics(
        mediaUuid: widget.mediaUuid,
      );

      if (response.success) {
        setState(() {
          _analytics = response.data;
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = response.message;
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Failed to load analytics: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error, color: Colors.red, size: 48),
            const SizedBox(height: 16),
            Text(
              'Error loading analytics',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadAnalytics,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_analytics == null) {
      return const Center(
        child: Text('No analytics data available'),
      );
    }

    return _AnalyticsContentWidget(
      analytics: _analytics!,
      showRecommendations: widget.showRecommendations,
      onRefresh: _loadAnalytics,
    );
  }
}

/// Widget for displaying the main analytics content
class _AnalyticsContentWidget extends StatelessWidget {
  final WidgetAnalyticsResponse analytics;
  final bool showRecommendations;
  final VoidCallback onRefresh;

  const _AnalyticsContentWidget({
    required this.analytics,
    required this.showRecommendations,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildHeader(context),
        const SizedBox(height: 16),
        _buildOverviewCards(context),
        const SizedBox(height: 16),
        _buildQualityMetrics(context),
        if (analytics.sessionHistory.isNotEmpty) ...[
          const SizedBox(height: 16),
          _buildSessionHistory(context),
        ],
        if (showRecommendations && analytics.recommendations.isNotEmpty) ...[
          const SizedBox(height: 16),
          _buildRecommendations(context),
        ],
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(
              Icons.analytics,
              color: Colors.blue,
              size: 24,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Processing Analytics',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: onRefresh,
              tooltip: 'Refresh Analytics',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverviewCards(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _buildMetricCard(
            context,
            'Total Sessions',
            analytics.totalSessions.toString(),
            Icons.timeline,
            Colors.blue,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            context,
            'Faces Detected',
            analytics.totalFacesDetected.toString(),
            Icons.face,
            Colors.green,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            context,
            'Avg. Time',
            analytics.averageProcessingTimeText ?? 'N/A',
            Icons.timer,
            Colors.orange,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            context,
            'Faces/Session',
            analytics.facesPerSession.toStringAsFixed(1),
            Icons.bar_chart,
            Colors.purple,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricCard(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQualityMetrics(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quality Metrics',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildQualityChart(context),
            const SizedBox(height: 16),
            _buildQualityDetails(context),
          ],
        ),
      ),
    );
  }

  Widget _buildQualityChart(BuildContext context) {
    final metrics = [
      ChartData('Confidence', analytics.averageConfidence ?? 0.0, Colors.blue),
      ChartData('Consistency', analytics.detectionConsistency ?? 0.0, Colors.green),
      ChartData('Efficiency', analytics.processingEfficiency ?? 0.0, Colors.orange),
    ];

    return SizedBox(
      height: 200,
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: 1.0,
          barTouchData: BarTouchData(enabled: false),
          titlesData: FlTitlesData(
            show: true,
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  if (value >= 0 && value < metrics.length) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 8.0),
                      child: Text(
                        metrics[value.toInt()].label,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    );
                  }
                  return const Text('');
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 40,
                getTitlesWidget: (value, meta) {
                  return Text(
                    '${(value * 100).toInt()}%',
                    style: Theme.of(context).textTheme.bodySmall,
                  );
                },
              ),
            ),
            topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: FlGridData(show: true),
          borderData: FlBorderData(show: false),
          barGroups: metrics
              .asMap()
              .entries
              .map(
                (entry) => BarChartGroupData(
                  x: entry.key,
                  barRods: [
                    BarChartRodData(
                      toY: entry.value.value,
                      color: entry.value.color,
                      width: 20,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ],
                ),
              )
              .toList(),
        ),
      ),
    );
  }

  Widget _buildQualityDetails(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _buildQualityDetail(
            context,
            'Average Confidence',
            '${((analytics.averageConfidence ?? 0.0) * 100).toStringAsFixed(1)}%',
            Colors.blue,
          ),
        ),
        Expanded(
          child: _buildQualityDetail(
            context,
            'Detection Consistency',
            '${((analytics.detectionConsistency ?? 0.0) * 100).toStringAsFixed(1)}%',
            Colors.green,
          ),
        ),
        Expanded(
          child: _buildQualityDetail(
            context,
            'Processing Efficiency',
            '${((analytics.processingEfficiency ?? 0.0) * 100).toStringAsFixed(1)}%',
            Colors.orange,
          ),
        ),
      ],
    );
  }

  Widget _buildQualityDetail(
    BuildContext context,
    String label,
    String value,
    Color color,
  ) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildSessionHistory(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recent Sessions',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ...analytics.sessionHistory.take(5).map(
              (session) => _buildSessionItem(context, session),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSessionItem(BuildContext context, SessionSummary session) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: session.isActive ? Colors.green : Colors.grey,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  session.displayStatus,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  '${session.totalFacesDetected} faces • ${session.durationText ?? 'Duration unknown'}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
          Text(
            session.startedAt.toString().substring(11, 16),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRecommendations(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.lightbulb_outline, color: Colors.amber, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Recommendations',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...analytics.recommendations.map(
              (recommendation) => _buildRecommendationItem(context, recommendation),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationItem(BuildContext context, String recommendation) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.arrow_right, color: Colors.amber, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              recommendation,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

/// Chart data model for quality metrics
class ChartData {
  final String label;
  final double value;
  final Color color;

  ChartData(this.label, this.value, this.color);
}

/// Loading widget
class _LoadingWidget extends StatelessWidget {
  const _LoadingWidget();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(32.0),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('Loading analytics...'),
            ],
          ),
        ),
      ),
    );
  }
}

/// Error widget
class _ErrorWidget extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorWidget({
    required this.error,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              color: Colors.red,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Error Loading Analytics',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              error,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Empty state widget
class _EmptyWidget extends StatelessWidget {
  const _EmptyWidget();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.info_outline,
                color: Colors.grey,
                size: 48,
              ),
              const SizedBox(height: 16),
              Text(
                'No Analytics Available',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
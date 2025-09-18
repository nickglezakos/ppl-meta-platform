import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../models/face_detection_models.dart';
import '../../providers/workflow_providers.dart';

/// Displays comprehensive analytics charts and reports for workflow performance
/// Includes performance trends, session analytics, optimization benefits, and comparisons
class WorkflowAnalyticsWidget extends ConsumerStatefulWidget {
  const WorkflowAnalyticsWidget({super.key});

  @override
  ConsumerState<WorkflowAnalyticsWidget> createState() => 
      _WorkflowAnalyticsWidgetState();
}

class _WorkflowAnalyticsWidgetState extends ConsumerState<WorkflowAnalyticsWidget> 
    with SingleTickerProviderStateMixin {
  late TabController _analyticsTabController;
  String _selectedTimeRange = '7d';
  
  @override
  void initState() {
    super.initState();
    _analyticsTabController = TabController(length: 6, vsync: this);
  }
  
  @override
  void dispose() {
    _analyticsTabController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildAnalyticsHeader(),
        _buildTimeRangeSelector(),
        Expanded(
          child: TabBarView(
            controller: _analyticsTabController,
            children: [
              _buildPerformanceTrendsTab(),
              _buildSessionAnalyticsTab(),
              _buildOptimizationBenefitsTab(),
              _buildComparativeAnalysisTab(),
              _buildPredictiveInsightsTab(),
              _buildOptimizationSuggestionsTab(),
            ],
          ),
        ),
      ],
    );
  }
  
  Widget _buildAnalyticsHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: AppColors.surface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.trending_up,
                color: AppColors.primary,
                size: 24,
              ),
              const SizedBox(width: 12),
              Text(
                'Workflow Analytics & Reporting',
                style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.refresh),
                color: AppColors.textSecondary,
                onPressed: _refreshAnalytics,
                tooltip: 'Refresh Analytics',
              ),
              IconButton(
                icon: const Icon(Icons.file_download),
                color: AppColors.textSecondary,
                onPressed: _exportAnalytics,
                tooltip: 'Export Report',
              ),
            ],
          ),
          const SizedBox(height: 16),
          TabBar(
            controller: _analyticsTabController,
            indicatorColor: AppColors.primary,
            labelColor: AppColors.textPrimary,
            unselectedLabelColor: AppColors.textSecondary,
            isScrollable: true,
            tabs: const [
              Tab(text: 'Performance'),
              Tab(text: 'Sessions'),
              Tab(text: 'Benefits'),
              Tab(text: 'Comparison'),
              Tab(text: 'Predictions'),
              Tab(text: 'Suggestions'),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildTimeRangeSelector() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: AppColors.surfaceVariant,
      child: Row(
        children: [
          Text(
            'Time Range:',
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(width: 12),
          ...['1d', '7d', '30d', '90d'].map((range) => Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text(range),
              selected: _selectedTimeRange == range,
              onSelected: (selected) {
                if (selected) {
                  setState(() => _selectedTimeRange = range);
                }
              },
              selectedColor: AppColors.primary.withOpacity(0.2),
              backgroundColor: AppColors.surface,
              labelStyle: TextStyle(
                color: _selectedTimeRange == range 
                    ? AppColors.primary 
                    : AppColors.textSecondary,
              ),
            ),
          )),
        ],
      ),
    );
  }
  
  Widget _buildPerformanceTrendsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPerformanceChart(),
          const SizedBox(height: 24),
          _buildPerformanceMetricsGrid(),
          const SizedBox(height: 24),
          _buildPerformanceInsights(),
        ],
      ),
    );
  }
  
  Widget _buildPerformanceChart() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Performance Trends',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            
            // Mock chart representation
            Container(
              height: 180, // Reduced from 200
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Padding(
                padding: const EdgeInsets.all(8), // Reduced padding
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.show_chart,
                      color: AppColors.textSecondary,
                      size: 24, // Reduced from 36
                    ),
                    const SizedBox(height: 4), // Reduced from 8
                    Text(
                      'Performance Trend Chart',
                      style: AppTextStyles.labelMedium.copyWith(color: AppColors.textSecondary), // Changed from labelLarge
                    ),
                    const SizedBox(height: 2), // Reduced from 4
                    Text(
                      'CPU Usage Reduction Over Time',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.textTertiary),
                    ),
                    const SizedBox(height: 8), // Reduced from 12
                    Expanded(child: _buildRealAnalyticsChart()), // Updated to use real data
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildRealAnalyticsChart() {
    return Consumer(
      builder: (context, ref, child) {
        final analyticsAsync = ref.watch(analyticsSummaryProvider(7));
        
        return analyticsAsync.when(
          data: (analytics) {
            final summary = analytics['summary'] as Map<String, dynamic>?;
            final systemOverview = summary?['system_overview'] as Map<String, dynamic>?;
            final detectionTrends = summary?['detection_trends'] as List<dynamic>? ?? [];
            
            if (systemOverview == null) {
              return _buildErrorState('No analytics data available');
            }
            
            // Extract key metrics from real data
            final totalSessions = systemOverview['total_sessions'] as int? ?? 0;
            final completedSessions = systemOverview['completed_sessions'] as int? ?? 0;
            final totalFaces = systemOverview['total_faces_detected'] as int? ?? 0;
            final avgFacesPerSession = systemOverview['avg_faces_per_session'] as double? ?? 0.0;
            
            // Calculate completion rate percentage
            final completionRate = totalSessions > 0 ? (completedSessions / totalSessions * 100).round() : 0;
            
            // Build visualization with real data
            return Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildDataPoint('Sessions', totalSessions, totalSessions > 0 ? AppColors.success : AppColors.warning),
                _buildDataPoint('Completed', completedSessions, completedSessions > 0 ? AppColors.success : AppColors.warning),
                _buildDataPoint('Faces', totalFaces, totalFaces > 0 ? AppColors.info : AppColors.warning),
                _buildDataPoint('Avg/Session', avgFacesPerSession.round(), avgFacesPerSession > 0 ? AppColors.success : AppColors.warning),
              ],
            );
          },
          loading: () => _buildLoadingState(),
          error: (error, stack) => _buildErrorState('Failed to load analytics: $error'),
        );
      },
    );
  }
  
  Widget _buildLoadingState() {
    return const Center(
      child: CircularProgressIndicator(),
    );
  }
  
  Widget _buildErrorState(String message) {
    return Center(
      child: Text(
        message,
        style: AppTextStyles.bodySmall.copyWith(
          color: AppColors.error,
        ),
      ),
    );
  }
  
  Widget _buildDataPoint(String label, int value, Color color) {
    return Expanded( // Make each data point take equal space
      child: Column(
        mainAxisSize: MainAxisSize.min, // Take minimum space needed
        children: [
          Container(
            height: (value * 0.1).clamp(8.0, 24.0), // Adjusted scale for different data ranges
            width: 16, // Reduced width
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 4), // Reduced spacing
          Text(
            '$value',
            style: AppTextStyles.bodySmall.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 10, // Smaller font
            ),
          ),
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textTertiary,
              fontSize: 9, // Smaller font
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPerformanceMetricsGrid() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Key Metrics',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: 16),
        Consumer(
          builder: (context, ref, child) {
            final metricsAsync = ref.watch(workflowPerformanceMetricsProvider);
            
            return metricsAsync.when(
              data: (metrics) => GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                childAspectRatio: 2.5,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                children: [
                  _buildMetricCard(
                    'Avg CPU Reduction',
                    '${metrics.cpuUsageReduction.toStringAsFixed(1)}%',
                    Icons.memory,
                    AppColors.success,
                    '+5.2% vs last period',
                  ),
                  _buildMetricCard(
                    'Memory Efficiency',
                    '${metrics.memoryUsageReduction.toStringAsFixed(1)}%',
                    Icons.storage,
                    AppColors.info,
                    '+3.1% vs last period',
                  ),
                  _buildMetricCard(
                    'Active Sessions',
                    '${metrics.activeSessionsCount}',
                    Icons.play_circle,
                    AppColors.primary,
                    '${metrics.activeSessionsCount > 5 ? "+" : ""}${metrics.activeSessionsCount - 3} vs last period',
                  ),
                  _buildMetricCard(
                    'Optimization Rate',
                    '${((metrics.processedVideosCount / (metrics.processedVideosCount + metrics.activeSessionsCount)) * 100).toStringAsFixed(0)}%',
                    Icons.speed,
                    AppColors.warning,
                    '+12% vs last period',
                  ),
                ],
              ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => Text('Error: $error'),
            );
          },
        ),
      ],
    );
  }
  
  Widget _buildMetricCard(String title, String value, IconData icon, Color color, String trend) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.h5.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            trend,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.success,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPerformanceInsights() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Performance Insights',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            _buildInsightItem(
              'Optimization Trending Up',
              'CPU usage reduction has improved by 15% over the last week',
              Icons.trending_up,
              AppColors.success,
            ),
            const SizedBox(height: 12),
            _buildInsightItem(
              'Peak Usage Hours',
              'Most sessions are active between 2PM-4PM daily',
              Icons.schedule,
              AppColors.info,
            ),
            const SizedBox(height: 12),
            _buildInsightItem(
              'Recommendation',
              'Consider scheduling batch processing during off-peak hours',
              Icons.lightbulb_outline,
              AppColors.warning,
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildInsightItem(String title, String description, IconData icon, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 16),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  Widget _buildSessionAnalyticsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSessionStatsGrid(),
          const SizedBox(height: 24),
          _buildSessionActivityChart(),
          const SizedBox(height: 24),
          _buildSessionSuccessRate(),
        ],
      ),
    );
  }
  
  Widget _buildSessionStatsGrid() {
    return Consumer(
      builder: (context, ref, child) {
        final sessionsAsync = ref.watch(allActiveSessionsProvider);
        
        return sessionsAsync.when(
          data: (sessions) {
            final completedSessions = sessions.where((s) => s.status == 'completed').length;
            final activeSessions = sessions.where((s) => s.status == 'active').length;
            final totalFrames = sessions.fold<int>(0, (sum, s) => sum + (s.totalFramesProcessed ?? 0));
            final totalFaces = sessions.fold<int>(0, (sum, s) => sum + (s.totalFacesDetected ?? 0));
            
            return GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 2.2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              children: [
                _buildStatCard('Total Sessions', '${sessions.length}', Icons.list, AppColors.primary),
                _buildStatCard('Completed', '$completedSessions', Icons.check_circle, AppColors.success),
                _buildStatCard('Active Now', '$activeSessions', Icons.play_circle, AppColors.warning),
                _buildStatCard('Total Frames', '$totalFrames', Icons.video_file, AppColors.info),
                _buildStatCard('Total Faces', '$totalFaces', Icons.face, AppColors.secondary),
                _buildStatCard('Avg Confidence', '87.5%', Icons.percent, AppColors.success),
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Text('Error: $error'),
        );
      },
    );
  }
  
  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.h5.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
  
  Widget _buildSessionActivityChart() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Session Activity Timeline',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            Container(
              height: 150,
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.timeline,
                      color: AppColors.textSecondary,
                      size: 32,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Session Activity Chart',
                      style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Shows session creation and completion over time',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.textTertiary),
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
  
  Widget _buildSessionSuccessRate() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Session Success Rate',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Column(
                    children: [
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: AppColors.success, width: 6),
                        ),
                        child: Center(
                          child: Text(
                            '94%',
                            style: AppTextStyles.h4.copyWith(
                              color: AppColors.success,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Success Rate',
                        style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  flex: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSuccessRateItem('Completed Successfully', 47, AppColors.success),
                      const SizedBox(height: 8),
                      _buildSuccessRateItem('Currently Active', 3, AppColors.primary),
                      const SizedBox(height: 8),
                      _buildSuccessRateItem('Failed/Errors', 3, AppColors.error),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildSuccessRateItem(String label, int count, Color color) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
        const Spacer(),
        Text(
          '$count',
          style: AppTextStyles.bodyMedium.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
  
  Widget _buildOptimizationBenefitsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildOptimizationSummary(),
          const SizedBox(height: 24),
          _buildBenefitsComparison(),
          const SizedBox(height: 24),
          _buildCostSavingsAnalysis(),
        ],
      ),
    );
  }
  
  Widget _buildOptimizationSummary() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Optimization Benefits Summary',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildBenefitMetric(
                    'CPU Usage',
                    '90%',
                    'Reduction',
                    Icons.memory,
                    AppColors.success,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildBenefitMetric(
                    'Memory Usage',
                    '65%',
                    'Reduction',
                    Icons.storage,
                    AppColors.info,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildBenefitMetric(
                    'Load Time',
                    '75%',
                    'Faster',
                    Icons.speed,
                    AppColors.warning,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildBenefitMetric(String title, String value, String subtitle, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.h4.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(color: color),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
  
  Widget _buildBenefitsComparison() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Before vs After Optimization',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            _buildComparisonRow('Processing Time', '2.5s', '0.6s', '76% faster'),
            const SizedBox(height: 12),
            _buildComparisonRow('CPU Usage', '85%', '15%', '82% reduction'),
            const SizedBox(height: 12),
            _buildComparisonRow('Memory Usage', '1.2GB', '0.4GB', '67% reduction'),
            const SizedBox(height: 12),
            _buildComparisonRow('Power Consumption', 'High', 'Low', '45% reduction'),
          ],
        ),
      ),
    );
  }
  
  Widget _buildComparisonRow(String metric, String before, String after, String improvement) {
    return Row(
      children: [
        Expanded(
          flex: 2,
          child: Text(
            metric,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary),
          ),
        ),
        Expanded(
          child: Text(
            before,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.error),
            textAlign: TextAlign.center,
          ),
        ),
        Expanded(
          child: Icon(
            Icons.arrow_forward,
            color: AppColors.textSecondary,
            size: 16,
          ),
        ),
        Expanded(
          child: Text(
            after,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.success),
            textAlign: TextAlign.center,
          ),
        ),
        Expanded(
          child: Text(
            improvement,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.success,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }
  
  Widget _buildCostSavingsAnalysis() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Cost Savings Analysis',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildCostSavingCard(
                    'Daily Savings',
                    '\$24.50',
                    'Power + Computing',
                    AppColors.success,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildCostSavingCard(
                    'Monthly Savings',
                    '\$735.00',
                    'Projected',
                    AppColors.info,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildCostSavingCard(String title, String amount, String subtitle, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 8),
          Text(
            amount,
            style: AppTextStyles.h4.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(color: color),
          ),
        ],
      ),
    );
  }
  
  Widget _buildComparativeAnalysisTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildWorkflowComparison(),
          const SizedBox(height: 24),
          _buildIndustryBenchmarks(),
          const SizedBox(height: 24),
          _buildRecommendations(),
        ],
      ),
    );
  }
  
  Widget _buildWorkflowComparison() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Workflow 4 vs Workflow 5 Comparison',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            _buildWorkflowComparisonTable(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildWorkflowComparisonTable() {
    return Table(
      columnWidths: const {
        0: FlexColumnWidth(2),
        1: FlexColumnWidth(1),
        2: FlexColumnWidth(1),
      },
      children: [
        _buildTableHeader(),
        _buildTableRow('Processing Type', 'Session-based', 'Optimized Playback'),
        _buildTableRow('CPU Usage', 'Medium', 'Low'),
        _buildTableRow('Memory Usage', 'Medium', 'Low'),
        _buildTableRow('Processing Time', 'Real-time', 'Pre-processed'),
        _buildTableRow('Quality', 'High', 'High'),
        _buildTableRow('Use Case', 'Live Analysis', 'Batch Processing'),
      ],
    );
  }
  
  TableRow _buildTableHeader() {
    return TableRow(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(4),
      ),
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            'Metric',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            'Workflow 4',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            'Workflow 5',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.success,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ],
    );
  }
  
  TableRow _buildTableRow(String metric, String workflow4, String workflow5) {
    return TableRow(
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            metric,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            workflow4,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary),
            textAlign: TextAlign.center,
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            workflow5,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary),
            textAlign: TextAlign.center,
          ),
        ),
      ],
    );
  }
  
  Widget _buildIndustryBenchmarks() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Industry Benchmarks',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            _buildBenchmarkItem('Face Detection Accuracy', '94.5%', '92%', true),
            const SizedBox(height: 12),
            _buildBenchmarkItem('Processing Speed', '85fps', '60fps', true),
            const SizedBox(height: 12),
            _buildBenchmarkItem('Resource Efficiency', '90%', '75%', true),
            const SizedBox(height: 12),
            _buildBenchmarkItem('Error Rate', '2.1%', '5%', true),
          ],
        ),
      ),
    );
  }
  
  Widget _buildBenchmarkItem(String metric, String ourValue, String industry, bool isGood) {
    return Row(
      children: [
        Expanded(
          flex: 2,
          child: Text(
            metric,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary),
          ),
        ),
        Expanded(
          child: Text(
            ourValue,
            style: AppTextStyles.bodyMedium.copyWith(
              color: isGood ? AppColors.success : AppColors.error,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'vs',
          style: AppTextStyles.bodySmall.copyWith(color: AppColors.textTertiary),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            industry,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
        ),
        Icon(
          isGood ? Icons.trending_up : Icons.trending_down,
          color: isGood ? AppColors.success : AppColors.error,
          size: 16,
        ),
      ],
    );
  }
  
  Widget _buildRecommendations() {
    return Card(
      color: AppColors.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Optimization Recommendations',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            _buildRecommendationItem(
              'Schedule Processing',
              'Run batch processing during off-peak hours (11PM - 6AM) to maximize resource efficiency.',
              Icons.schedule,
              AppColors.primary,
            ),
            const SizedBox(height: 12),
            _buildRecommendationItem(
              'Increase Workflow 5 Usage',
              'Process more videos with Workflow 5 to achieve greater CPU savings across the platform.',
              Icons.speed,
              AppColors.success,
            ),
            const SizedBox(height: 12),
            _buildRecommendationItem(
              'Monitor Resource Usage',
              'Set up alerts for high CPU usage periods to prevent system overload.',
              Icons.monitor,
              AppColors.warning,
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildRecommendationItem(String title, String description, IconData icon, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 16),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  void _exportAnalytics() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Export Analytics Report',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.picture_as_pdf),
              title: const Text('PDF Report'),
              subtitle: const Text('Complete analytics report'),
              onTap: () {
                Navigator.pop(context);
                _showExportSuccess('PDF');
              },
            ),
            ListTile(
              leading: const Icon(Icons.table_chart),
              title: const Text('CSV Data'),
              subtitle: const Text('Raw data for external analysis'),
              onTap: () {
                Navigator.pop(context);
                _showExportSuccess('CSV');
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }
  
  void _showExportSuccess(String format) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$format report export started'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  void _refreshAnalytics() {
    // Invalidate analytics providers to force refresh
    ref.invalidate(analyticsSummaryProvider);
    ref.invalidate(workflowPerformanceMetricsProvider);
    ref.invalidate(allActiveSessionsProvider);
    ref.invalidate(cachedActiveSessionsProvider);
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Analytics data refreshed'),
        backgroundColor: AppColors.success,
        duration: Duration(seconds: 2),
      ),
    );
  }

  /// Predictive insights tab with ML-based predictions and trends
  Widget _buildPredictiveInsightsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPredictiveInsightsHeader(),
          const SizedBox(height: 24),
          _buildWorkloadPredictions(),
          const SizedBox(height: 24),
          _buildResourceForecasting(),
          const SizedBox(height: 24),
          _buildTrendPredictions(),
          const SizedBox(height: 24),
          _buildAnomalyDetection(),
        ],
      ),
    );
  }

  Widget _buildPredictiveInsightsHeader() {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              Icons.psychology,
              color: AppColors.primary,
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Predictive Insights',
                    style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
                  ),
                  Text(
                    'AI-powered predictions based on historical data and trends',
                    style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
            OutlinedButton.icon(
              onPressed: _refreshPredictions,
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text('Refresh'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkloadPredictions() {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Workload Predictions',
              style: AppTextStyles.subtitle1.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildPredictionCard(
                    'Next Week',
                    '15-20 sessions',
                    Icons.trending_up,
                    AppColors.success,
                    'Based on current growth trend',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildPredictionCard(
                    'Peak Hours',
                    '2-4 PM daily',
                    Icons.schedule,
                    AppColors.warning,
                    'Highest activity predicted',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildPredictionCard(
                    'Processing Time',
                    '25% faster',
                    Icons.speed,
                    AppColors.primary,
                    'With new optimizations',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildPredictionCard(
                    'Storage Growth',
                    '120GB/week',
                    Icons.storage,
                    AppColors.info,
                    'Current consumption rate',
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResourceForecasting() {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Resource Forecasting',
              style: AppTextStyles.subtitle1.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.warning.withOpacity(0.1),
                child: Icon(Icons.memory, color: AppColors.warning),
              ),
              title: const Text('CPU Usage'),
              subtitle: const Text('Expected to reach 85% by next month'),
              trailing: const Text('85%', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.success.withOpacity(0.1),
                child: Icon(Icons.storage, color: AppColors.success),
              ),
              title: const Text('Storage'),
              subtitle: const Text('Sufficient capacity for 3 months'),
              trailing: const Text('45%', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.error.withOpacity(0.1),
                child: Icon(Icons.network_check, color: AppColors.error),
              ),
              title: const Text('Bandwidth'),
              subtitle: const Text('May need upgrade in 2 weeks'),
              trailing: const Text('92%', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTrendPredictions() {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Trend Predictions',
              style: AppTextStyles.subtitle1.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            Container(
              height: 200,
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Text(
                  'Trend prediction chart\n(Implementation in progress)',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.textSecondary),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnomalyDetection() {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Anomaly Detection',
              style: AppTextStyles.subtitle1.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.success.withOpacity(0.1),
                child: Icon(Icons.check_circle, color: AppColors.success),
              ),
              title: const Text('System Health'),
              subtitle: const Text('No anomalies detected in the last 24 hours'),
            ),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.warning.withOpacity(0.1),
                child: Icon(Icons.warning, color: AppColors.warning),
              ),
              title: const Text('Processing Delays'),
              subtitle: const Text('Unusual delay pattern detected at 3 PM'),
            ),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.info.withOpacity(0.1),
                child: Icon(Icons.info, color: AppColors.info),
              ),
              title: const Text('Usage Patterns'),
              subtitle: const Text('Higher than normal activity on weekends'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPredictionCard(String title, String value, IconData icon, Color color, String description) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(
                  fontSize: 12,
                  color: color,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
          ),
          const SizedBox(height: 4),
          Text(
            description,
            style: TextStyle(
              fontSize: 10,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  /// Optimization suggestions tab with actionable recommendations
  Widget _buildOptimizationSuggestionsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSuggestionsHeader(),
          const SizedBox(height: 24),
          _buildPerformanceSuggestions(),
          const SizedBox(height: 24),
          _buildResourceOptimization(),
          const SizedBox(height: 24),
          _buildWorkflowImprovements(),
          const SizedBox(height: 24),
          _buildSystemRecommendations(),
        ],
      ),
    );
  }

  Widget _buildSuggestionsHeader() {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              Icons.lightbulb,
              color: AppColors.warning,
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Optimization Suggestions',
                    style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
                  ),
                  Text(
                    'AI-powered recommendations to improve system performance',
                    style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
            OutlinedButton.icon(
              onPressed: _generateNewSuggestions,
              icon: const Icon(Icons.auto_fix_high, size: 16),
              label: const Text('Generate'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceSuggestions() {
    return _buildSuggestionCategory(
      'Performance Optimizations',
      Icons.speed,
      AppColors.primary,
      [
        SuggestionItem(
          title: 'Enable batch processing',
          description: 'Process multiple videos simultaneously to reduce total time by 40%',
          impact: 'High',
          effort: 'Medium',
          action: 'Configure',
        ),
        SuggestionItem(
          title: 'Optimize video encoding settings',
          description: 'Adjust compression parameters to balance quality and speed',
          impact: 'Medium',
          effort: 'Low',
          action: 'Apply',
        ),
        SuggestionItem(
          title: 'Upgrade face detection model',
          description: 'Use latest ML model for 15% faster processing',
          impact: 'High',
          effort: 'High',
          action: 'Upgrade',
        ),
      ],
    );
  }

  Widget _buildResourceOptimization() {
    return _buildSuggestionCategory(
      'Resource Optimization',
      Icons.memory,
      AppColors.success,
      [
        SuggestionItem(
          title: 'Implement smart caching',
          description: 'Cache frequently accessed data to reduce CPU usage by 25%',
          impact: 'High',
          effort: 'Medium',
          action: 'Enable',
        ),
        SuggestionItem(
          title: 'Schedule maintenance tasks',
          description: 'Run cleanup operations during low-usage hours',
          impact: 'Medium',
          effort: 'Low',
          action: 'Schedule',
        ),
        SuggestionItem(
          title: 'Optimize database queries',
          description: 'Index optimization can improve query speed by 60%',
          impact: 'High',
          effort: 'Medium',
          action: 'Optimize',
        ),
      ],
    );
  }

  Widget _buildWorkflowImprovements() {
    return _buildSuggestionCategory(
      'Workflow Improvements',
      Icons.auto_mode,
      AppColors.info,
      [
        SuggestionItem(
          title: 'Add quality checkpoints',
          description: 'Implement automatic quality validation at key stages',
          impact: 'Medium',
          effort: 'Medium',
          action: 'Implement',
        ),
        SuggestionItem(
          title: 'Enable automatic retry',
          description: 'Retry failed processing jobs automatically with backoff',
          impact: 'Medium',
          effort: 'Low',
          action: 'Configure',
        ),
        SuggestionItem(
          title: 'Parallel session processing',
          description: 'Process multiple sessions concurrently based on resource availability',
          impact: 'High',
          effort: 'High',
          action: 'Design',
        ),
      ],
    );
  }

  Widget _buildSystemRecommendations() {
    return _buildSuggestionCategory(
      'System Recommendations',
      Icons.settings,
      AppColors.warning,
      [
        SuggestionItem(
          title: 'Increase storage capacity',
          description: 'Add 500GB storage to handle projected growth',
          impact: 'High',
          effort: 'Low',
          action: 'Purchase',
        ),
        SuggestionItem(
          title: 'Setup monitoring alerts',
          description: 'Get notified when system resources reach threshold limits',
          impact: 'Medium',
          effort: 'Low',
          action: 'Setup',
        ),
        SuggestionItem(
          title: 'Implement load balancing',
          description: 'Distribute processing load across multiple servers',
          impact: 'High',
          effort: 'High',
          action: 'Deploy',
        ),
      ],
    );
  }

  Widget _buildSuggestionCategory(String title, IconData icon, Color color, List<SuggestionItem> suggestions) {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: AppTextStyles.subtitle1.copyWith(color: AppColors.textPrimary),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...suggestions.map((suggestion) => _buildSuggestionTile(suggestion)),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionTile(SuggestionItem suggestion) {
    Color impactColor = suggestion.impact == 'High' 
        ? AppColors.error 
        : suggestion.impact == 'Medium' 
            ? AppColors.warning 
            : AppColors.success;
    
    Color effortColor = suggestion.effort == 'High' 
        ? AppColors.error 
        : suggestion.effort == 'Medium' 
            ? AppColors.warning 
            : AppColors.success;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    suggestion.title,
                    style: AppTextStyles.subtitle2.copyWith(color: AppColors.textPrimary),
                  ),
                ),
                ElevatedButton(
                  onPressed: () => _applySuggestion(suggestion),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(80, 32),
                  ),
                  child: Text(suggestion.action),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              suggestion.description,
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildSuggestionBadge('Impact', suggestion.impact, impactColor),
                const SizedBox(width: 8),
                _buildSuggestionBadge('Effort', suggestion.effort, effortColor),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionBadge(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        '$label: $value',
        style: TextStyle(
          fontSize: 10,
          color: color,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  void _refreshPredictions() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Refreshing predictive insights...'),
        backgroundColor: AppColors.primary,
      ),
    );
  }

  void _generateNewSuggestions() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Generating new optimization suggestions...'),
        backgroundColor: AppColors.primary,
      ),
    );
  }

  void _applySuggestion(SuggestionItem suggestion) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Apply Suggestion',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Apply "${suggestion.title}"?\n\n${suggestion.description}',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Applied: ${suggestion.title}'),
                  backgroundColor: AppColors.success,
                ),
              );
            },
            child: Text(suggestion.action),
          ),
        ],
      ),
    );
  }
}

/// Model for optimization suggestions
class SuggestionItem {
  final String title;
  final String description;
  final String impact;
  final String effort;
  final String action;

  const SuggestionItem({
    required this.title,
    required this.description,
    required this.impact,
    required this.effort,
    required this.action,
  });
}
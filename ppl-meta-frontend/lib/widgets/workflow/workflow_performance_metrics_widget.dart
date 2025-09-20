import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../models/face_detection_models.dart';
import '../../providers/workflow_providers.dart';

/// Displays comprehensive performance metrics for workflow operations
/// Shows CPU savings, memory usage, processing efficiency, and real-time metrics
class WorkflowPerformanceMetricsWidget extends ConsumerWidget {
  const WorkflowPerformanceMetricsWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final performanceMetrics = ref.watch(workflowPerformanceMetricsProvider);
    
    return performanceMetrics.when(
      data: (metrics) => _buildMetricsContent(metrics),
      loading: () => _buildLoadingState(),
      error: (error, stackTrace) => _buildErrorState(error.toString()),
    );
  }
  
  Widget _buildMetricsContent(WorkflowPerformanceMetrics metrics) {
    return Column(
      children: [
        // Primary metrics row
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: _buildMetricCard(
                title: 'CPU Savings',
                value: '${metrics.cpuUsageReduction.toStringAsFixed(1)}%',
                subtitle: 'vs Real-time Processing',
                icon: Icons.memory,
                color: AppColors.success,
                trend: _calculateTrend(metrics.cpuUsageReduction, 75.0),
              ),
            ),
            const SizedBox(width: 12),
            Flexible(
              child: _buildMetricCard(
                title: 'Memory Efficiency',
                value: '${metrics.memoryUsageReduction.toStringAsFixed(1)}%',
                subtitle: 'Reduced Usage',
                icon: Icons.storage,
                color: AppColors.info,
                trend: _calculateTrend(metrics.memoryUsageReduction, 50.0),
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 12),
        
        // Secondary metrics row
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: _buildMetricCard(
                title: 'Active Sessions',
                value: '${metrics.activeSessionsCount}',
                subtitle: 'Currently Running',
                icon: Icons.play_circle,
                color: AppColors.primary,
                showTrend: false,
              ),
            ),
            const SizedBox(width: 12),
            Flexible(
              child: _buildMetricCard(
                title: 'Processed Videos',
                value: '${metrics.processedVideosCount}',
                subtitle: 'Optimized for Playback',
                icon: Icons.video_library,
                color: AppColors.warning,
                showTrend: false,
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 16),
        
        // Database statistics section
        _buildDatabaseStatistics(),
        
        const SizedBox(height: 16),
        
        // Performance summary
        _buildPerformanceSummary(metrics),
      ],
    );
  }
  
  Widget _buildMetricCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color color,
    MetricTrend? trend,
    bool showTrend = true,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const Spacer(),
              if (showTrend && trend != null) _buildTrendIndicator(trend),
            ],
          ),
          
          const SizedBox(height: 12),
          
          Text(
            value,
            style: AppTextStyles.h4.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          
          const SizedBox(height: 4),
          
          Text(
            title,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w500,
            ),
          ),
          
          const SizedBox(height: 2),
          
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildTrendIndicator(MetricTrend trend) {
    IconData icon;
    Color color;
    
    switch (trend) {
      case MetricTrend.up:
        icon = Icons.trending_up;
        color = AppColors.success;
        break;
      case MetricTrend.down:
        icon = Icons.trending_down;
        color = AppColors.error;
        break;
      case MetricTrend.stable:
        icon = Icons.trending_flat;
        color = AppColors.textSecondary;
        break;
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Icon(icon, color: color, size: 14),
    );
  }
  
  Widget _buildPerformanceSummary(WorkflowPerformanceMetrics metrics) {
    final overallEfficiency = _calculateOverallEfficiency(metrics);
    
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.analytics,
                color: AppColors.primary,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Performance Summary',
                style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
              ),
            ],
          ),
          
          const SizedBox(height: 12),
          
          // Overall efficiency indicator
          Row(
            children: [
              Text(
                'Overall Efficiency: ',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              Text(
                '${overallEfficiency.toStringAsFixed(0)}%',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: _getEfficiencyColor(overallEfficiency),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 8),
          
          // Efficiency bar
          LinearProgressIndicator(
            value: overallEfficiency / 100,
            backgroundColor: AppColors.gray800,
            valueColor: AlwaysStoppedAnimation(_getEfficiencyColor(overallEfficiency)),
          ),
          
          const SizedBox(height: 12),
          
          // Performance insights
          _buildPerformanceInsights(metrics),
          
          const SizedBox(height: 8),
          
          // Last updated
          Text(
            'Last updated: ${_formatDateTime(metrics.lastUpdated)}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPerformanceInsights(WorkflowPerformanceMetrics metrics) {
    final insights = _generateInsights(metrics);
    
    if (insights.isEmpty) {
      return const SizedBox.shrink();
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: insights
          .map((insight) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      insight.icon,
                      color: insight.color,
                      size: 14,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        insight.message,
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ],
                ),
              ))
          .toList(),
    );
  }
  
  Widget _buildLoadingState() {
    return Container(
      height: 200,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation(AppColors.primary),
            ),
            SizedBox(height: 16),
            Text(
              'Loading performance metrics...',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildErrorState(String error) {
    return Container(
      height: 200,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              color: AppColors.error,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Failed to load metrics',
              style: AppTextStyles.h6.copyWith(color: AppColors.error),
            ),
            const SizedBox(height: 8),
            Text(
              error,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildDatabaseStatistics() {
    return Consumer(
      builder: (context, ref, child) {
        final databaseStatusAsync = ref.watch(databaseStatusProvider);
        
        return databaseStatusAsync.when(
          data: (status) {
            final statistics = status['statistics'] as Map<String, dynamic>?;
            if (statistics == null) {
              return _buildDatabaseErrorState('No database statistics available');
            }
            
            final totalMedia = statistics['total_media'] as int? ?? 0;
            final totalDetections = statistics['total_detections'] as int? ?? 0;
            final dbType = statistics['database_type'] as String? ?? 'Unknown';
            final dbStatus = status['database_status'] as String? ?? 'Unknown';
            
            return Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.storage, color: AppColors.primary, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'Database Statistics',
                        style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: dbStatus == 'connected' ? AppColors.success.withOpacity(0.1) : AppColors.error.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          dbStatus.toUpperCase(),
                          style: AppTextStyles.caption.copyWith(
                            color: dbStatus == 'connected' ? AppColors.success : AppColors.error,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _buildDatabaseMetric(
                          label: 'Media Files',
                          value: '$totalMedia',
                          icon: Icons.video_library,
                          color: AppColors.info,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _buildDatabaseMetric(
                          label: 'Face Detections',
                          value: '$totalDetections',
                          icon: Icons.face,
                          color: AppColors.warning,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _buildDatabaseMetric(
                          label: 'Database',
                          value: dbType,
                          icon: Icons.data_object,
                          color: AppColors.primary,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
          loading: () => _buildDatabaseLoadingState(),
          error: (error, stack) => _buildDatabaseErrorState('Database status unavailable'),
        );
      },
    );
  }
  
  Widget _buildDatabaseMetric({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: color, size: 16),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                label,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                  fontSize: 11,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
  
  Widget _buildDatabaseLoadingState() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: const Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
  
  Widget _buildDatabaseErrorState(String message) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: AppColors.error, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
            ),
          ),
        ],
      ),
    );
  }
  
  MetricTrend _calculateTrend(double value, double baseline) {
    if (value > baseline + 5) return MetricTrend.up;
    if (value < baseline - 5) return MetricTrend.down;
    return MetricTrend.stable;
  }
  
  double _calculateOverallEfficiency(WorkflowPerformanceMetrics metrics) {
    // Weighted calculation of overall performance
    final cpuWeight = 0.4;
    final memoryWeight = 0.3;
    final utilizationWeight = 0.3;
    
    final utilizationScore = metrics.activeSessionsCount > 0 ? 
        (metrics.processedVideosCount / (metrics.activeSessionsCount + metrics.processedVideosCount)) * 100 : 
        metrics.processedVideosCount > 0 ? 80.0 : 0.0;
    
    return (metrics.cpuUsageReduction * cpuWeight) +
           (metrics.memoryUsageReduction * memoryWeight) +
           (utilizationScore * utilizationWeight);
  }
  
  Color _getEfficiencyColor(double efficiency) {
    if (efficiency >= 80) return AppColors.success;
    if (efficiency >= 60) return AppColors.warning;
    return AppColors.error;
  }
  
  List<PerformanceInsight> _generateInsights(WorkflowPerformanceMetrics metrics) {
    final insights = <PerformanceInsight>[];
    
    // CPU optimization insight
    if (metrics.cpuUsageReduction > 80) {
      insights.add(PerformanceInsight(
        message: 'Excellent CPU optimization achieved through workflow processing',
        icon: Icons.thumb_up,
        color: AppColors.success,
      ));
    } else if (metrics.cpuUsageReduction < 50) {
      insights.add(PerformanceInsight(
        message: 'Consider processing more videos to improve CPU efficiency',
        icon: Icons.lightbulb_outline,
        color: AppColors.warning,
      ));
    }
    
    // Session utilization insight
    if (metrics.activeSessionsCount > 5) {
      insights.add(PerformanceInsight(
        message: 'High session activity - monitor system resources',
        icon: Icons.monitor,
        color: AppColors.info,
      ));
    }
    
    // Processing ratio insight
    if (metrics.processedVideosCount > metrics.activeSessionsCount * 2) {
      insights.add(PerformanceInsight(
        message: 'Good processing ratio - workflows are being utilized effectively',
        icon: Icons.trending_up,
        color: AppColors.success,
      ));
    }
    
    return insights;
  }
  
  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes} minute(s) ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours} hour(s) ago';
    } else {
      return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
    }
  }
}

enum MetricTrend {
  up,
  down,
  stable,
}

class PerformanceInsight {
  final String message;
  final IconData icon;
  final Color color;

  const PerformanceInsight({
    required this.message,
    required this.icon,
    required this.color,
  });
}
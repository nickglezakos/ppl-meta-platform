import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/camera_status_monitor.dart';
import '../../core/providers/camera_status_providers.dart';
import '../../core/theme/app_theme.dart';
import 'camera_status_card.dart';

/// Monitoring dashboard showing overall system health
class CameraMonitoringDashboard extends ConsumerWidget {
  const CameraMonitoringDashboard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final performanceMetrics = ref.watch(monitoringPerformanceProvider);
    final healthSummary = ref.watch(connectionHealthSummaryProvider);
    final camerasWithIssues = ref.watch(camerasWithIssuesProvider);
    final activeMonitoringCount = ref.watch(activeMonitoringCountProvider);

    return Card(
      color: AppColors.widgetFill,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  Icons.monitor_heart,
                  size: 24,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Camera Monitoring Dashboard',
                  style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const Spacer(),
                _buildActiveIndicator(activeMonitoringCount),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Performance metrics
            _buildPerformanceMetrics(performanceMetrics),
            
            const SizedBox(height: 16),
            
            // Connection health summary
            _buildHealthSummary(healthSummary),
            
            if (camerasWithIssues.isNotEmpty) ...[
              const SizedBox(height: 16),
              _buildIssuesSection(camerasWithIssues),
            ],
            
            const SizedBox(height: 16),
            
            // Quick actions
            _buildQuickActions(ref),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveIndicator(int count) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: count > 0 ? Colors.green.withOpacity(0.1) : Colors.grey.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: count > 0 ? Colors.green.withOpacity(0.3) : Colors.grey.withOpacity(0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: count > 0 ? Colors.green : Colors.grey,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            '$count Active',
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: count > 0 ? Colors.green : Colors.grey,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceMetrics(Map<String, dynamic> metrics) {
    final totalCameras = metrics['total_cameras'] as int? ?? 0;
    final healthyCameras = metrics['healthy_cameras'] as int? ?? 0;
    final healthPercentage = metrics['health_percentage'] as int? ?? 0;
    final averageLatency = metrics['average_latency_ms'] as int? ?? 0;
    final reconnectAttempts = metrics['total_reconnect_attempts'] as int? ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Performance Metrics',
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _buildMetricTile(
                'Health',
                '$healthPercentage%',
                '$healthyCameras/$totalCameras',
                healthPercentage >= 80 ? Colors.green : 
                healthPercentage >= 60 ? Colors.orange : Colors.red,
                Icons.health_and_safety,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricTile(
                'Latency',
                '${averageLatency}ms',
                'Average',
                averageLatency <= 100 ? Colors.green :
                averageLatency <= 300 ? Colors.orange : Colors.red,
                Icons.speed,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricTile(
                'Reconnects',
                '$reconnectAttempts',
                'Total',
                reconnectAttempts == 0 ? Colors.green :
                reconnectAttempts <= 3 ? Colors.orange : Colors.red,
                Icons.refresh,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMetricTile(String label, String value, String subtitle, Color color, IconData icon) {
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
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: GoogleFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          Text(
            subtitle,
            style: GoogleFonts.inter(
              fontSize: 10,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthSummary(Map<ConnectionHealth, int> healthSummary) {
    final total = healthSummary.values.fold(0, (sum, count) => sum + count);
    
    if (total == 0) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, color: Colors.grey),
            const SizedBox(width: 8),
            Text(
              'No cameras currently being monitored',
              style: GoogleFonts.inter(
                fontSize: 14,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Connection Health Distribution',
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: ConnectionHealth.values.map((health) {
            final count = healthSummary[health] ?? 0;
            if (count == 0) return const SizedBox.shrink();
            
            final percentage = (count / total * 100).round();
            
            return Expanded(
              flex: count,
              child: Container(
                height: 8,
                decoration: BoxDecoration(
                  color: _getHealthColor(health),
                  borderRadius: BorderRadius.circular(4),
                ),
                margin: const EdgeInsets.only(right: 2),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: ConnectionHealth.values.map((health) {
            final count = healthSummary[health] ?? 0;
            if (count == 0) return const SizedBox.shrink();
            
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: _getHealthColor(health),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  '${health.name.capitalize()} ($count)',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildIssuesSection(List<String> camerasWithIssues) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.warning_amber,
              size: 16,
              color: Colors.orange,
            ),
            const SizedBox(width: 6),
            Text(
              'Cameras with Issues (${camerasWithIssues.length})',
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Colors.orange,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.orange.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.orange.withOpacity(0.3)),
          ),
          child: Column(
            children: camerasWithIssues.map((deviceId) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    Icon(
                      Icons.camera_alt,
                      size: 14,
                      color: Colors.orange,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Camera $deviceId',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                    TextButton(
                      onPressed: () {
                        // TODO: Navigate to camera details
                      },
                      child: Text(
                        'View',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: AppColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildQuickActions(WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quick Actions',
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () {
                  ref.read(cameraMonitoringProvider.notifier).optimizeForBackground();
                },
                icon: Icon(Icons.battery_saver, size: 16),
                label: Text('Battery Mode'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue.withOpacity(0.1),
                  foregroundColor: Colors.blue,
                  elevation: 0,
                  side: BorderSide(color: Colors.blue.withOpacity(0.3)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () {
                  ref.read(cameraMonitoringProvider.notifier).optimizeForForeground();
                },
                icon: Icon(Icons.flash_on, size: 16),
                label: Text('Active Mode'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green.withOpacity(0.1),
                  foregroundColor: Colors.green,
                  elevation: 0,
                  side: BorderSide(color: Colors.green.withOpacity(0.3)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () {
                  ref.read(cameraMonitoringProvider.notifier).stopAllMonitoring();
                },
                icon: Icon(Icons.stop, size: 16),
                label: Text('Stop All'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red.withOpacity(0.1),
                  foregroundColor: Colors.red,
                  elevation: 0,
                  side: BorderSide(color: Colors.red.withOpacity(0.3)),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Color _getHealthColor(ConnectionHealth health) {
    switch (health) {
      case ConnectionHealth.excellent:
        return Colors.green;
      case ConnectionHealth.good:
        return Colors.lightGreen;
      case ConnectionHealth.poor:
        return Colors.orange;
      case ConnectionHealth.critical:
        return Colors.red;
      case ConnectionHealth.unknown:
        return Colors.grey;
    }
  }
}

/// Extension to capitalize string
extension StringCapitalization on String {
  String capitalize() {
    if (isEmpty) return this;
    return this[0].toUpperCase() + substring(1);
  }
}

/// Compact status overview widget for app bars or headers
class CameraStatusOverview extends ConsumerWidget {
  const CameraStatusOverview({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeCount = ref.watch(activeMonitoringCountProvider);
    final healthSummary = ref.watch(connectionHealthSummaryProvider);
    final camerasWithIssues = ref.watch(camerasWithIssuesProvider);

    final healthyCount = (healthSummary[ConnectionHealth.excellent] ?? 0) + 
                        (healthSummary[ConnectionHealth.good] ?? 0);
    final totalMonitored = healthSummary.values.fold(0, (sum, count) => sum + count);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.widgetFill,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.monitor_heart,
            size: 16,
            color: AppColors.primary,
          ),
          const SizedBox(width: 6),
          Text(
            '$activeCount active',
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppColors.textPrimary,
            ),
          ),
          if (totalMonitored > 0) ...[
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 6),
              width: 1,
              height: 12,
              color: AppColors.textSecondary.withOpacity(0.3),
            ),
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: camerasWithIssues.isEmpty ? Colors.green : Colors.orange,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              '$healthyCount/$totalMonitored',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

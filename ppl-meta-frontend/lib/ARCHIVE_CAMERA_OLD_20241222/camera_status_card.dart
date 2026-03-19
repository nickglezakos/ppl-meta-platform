import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../utils/offline_fonts.dart';
import '../../core/services/camera_status_monitor.dart';
import '../../core/providers/camera_status_providers.dart';
import '../../core/theme/app_theme.dart';

/// Connection health indicator with color-coded status
class ConnectionHealthIndicator extends StatelessWidget {
  final ConnectionHealth health;
  final double size;
  final bool showLabel;

  const ConnectionHealthIndicator({
    super.key,
    required this.health,
    this.size = 12.0,
    this.showLabel = false,
  });

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData icon;
    String label;

    switch (health) {
      case ConnectionHealth.excellent:
        color = Colors.green;
        icon = Icons.signal_wifi_4_bar;
        label = 'Excellent';
        break;
      case ConnectionHealth.good:
        color = Colors.lightGreen;
        icon = Icons.signal_wifi_4_bar;
        label = 'Good';
        break;
      case ConnectionHealth.poor:
        color = Colors.orange;
        icon = Icons.signal_wifi_statusbar_4_bar;
        label = 'Poor';
        break;
      case ConnectionHealth.critical:
        color = Colors.red;
        icon = Icons.signal_wifi_connected_no_internet_4;
        label = 'Critical';
        break;
      case ConnectionHealth.unknown:
        color = Colors.grey;
        icon = Icons.signal_wifi_bad;
        label = 'Unknown';
        break;
    }

    if (showLabel) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            color: color,
            size: size,
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: size * 0.8,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    return Icon(
      icon,
      color: color,
      size: size,
    );
  }
}

/// Live camera status card with real-time updates
class CameraStatusCard extends ConsumerWidget {
  final String deviceId;
  final String? cameraName;
  final bool compact;

  const CameraStatusCard({
    super.key,
    required this.deviceId,
    this.cameraName,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusAsync = ref.watch(cameraStatusStreamProvider(deviceId));
    final isMonitored = ref.watch(isCameraMonitoredProvider(deviceId));
    final monitoringMode = ref.watch(cameraMonitoringModeProvider(deviceId));

    return Padding(
      padding: const EdgeInsets.all(16),
      child: statusAsync.when(
        data: (status) => _buildStatusContent(context, ref, status, isMonitored, monitoringMode),
        loading: () => _buildLoadingContent(),
          error: (error, stack) => _buildErrorContent(error.toString()),
        ),
    );
  }

  Widget _buildStatusContent(BuildContext context, WidgetRef ref, CameraStatus status, bool isMonitored, MonitoringMode? mode) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header with name and status
        Row(
          children: [
            Expanded(
              child: Text(
                cameraName ?? 'Camera ${status.deviceId}',
                style: OfflineFonts.inter(
                  fontSize: compact ? 14 : 16,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            if (status.isReconnecting)
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation(Colors.orange),
                ),
              )
            else
              ConnectionHealthIndicator(
                health: status.connectionHealth,
                size: compact ? 14 : 16,
              ),
          ],
        ),
        
        const SizedBox(height: 8),
        
        // Connection status row
        _buildStatusRow(
          'Connection',
          status.connectionStatus,
          _getConnectionStatusColor(status.connectionStatus),
          compact,
        ),
        
        if (!compact) ...[
          const SizedBox(height: 4),
          _buildStatusRow(
            'Stream',
            status.streamStatus,
            _getStreamStatusColor(status.streamStatus),
            compact,
          ),
        ],
        
        // Latency and session info
        if (status.latencyMs != null || status.sessionDuration != null) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              if (status.latencyMs != null) ...[
                Icon(
                  Icons.speed,
                  size: compact ? 12 : 14,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 4),
                Text(
                  '${status.latencyMs}ms',
                  style: OfflineFonts.inter(
                    fontSize: compact ? 11 : 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
              if (status.latencyMs != null && status.sessionDuration != null)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 8),
                  width: 1,
                  height: 12,
                  color: AppColors.textSecondary.withOpacity(0.3),
                ),
              if (status.sessionDuration != null) ...[
                Icon(
                  Icons.timer,
                  size: compact ? 12 : 14,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 4),
                Text(
                  _formatDuration(status.sessionDuration!),
                  style: OfflineFonts.inter(
                    fontSize: compact ? 11 : 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ],
        
        // Monitoring controls
        if (!compact && isMonitored) ...[
          const SizedBox(height: 12),
          _buildMonitoringControls(ref, status.deviceId, mode),
        ],
        
        // Error message
        if (status.errorMessage != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: Colors.red.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.error_outline,
                  size: 16,
                  color: Colors.red,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    status.errorMessage!,
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: Colors.red,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        
        // Last updated timestamp
        if (!compact) ...[
          const SizedBox(height: 8),
          Text(
            'Updated ${_formatTimestamp(status.lastUpdated)}',
            style: OfflineFonts.inter(
              fontSize: 10,
              color: AppColors.textSecondary.withOpacity(0.7),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStatusRow(String label, String status, Color color, bool compact) {
    return Row(
      children: [
        Container(
          width: compact ? 6 : 8,
          height: compact ? 6 : 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: OfflineFonts.inter(
            fontSize: compact ? 11 : 12,
            color: AppColors.textSecondary,
          ),
        ),
        Text(
          status.toUpperCase(),
          style: OfflineFonts.inter(
            fontSize: compact ? 11 : 12,
            fontWeight: FontWeight.w500,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildMonitoringControls(WidgetRef ref, String deviceId, MonitoringMode? mode) {
    return Row(
      children: [
        // Monitoring mode selector
        PopupMenuButton<MonitoringMode>(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: AppColors.primary.withOpacity(0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  _getModeIcon(mode),
                  size: 14,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 4),
                Text(
                  _getModeLabel(mode),
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: AppColors.primary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 4),
                Icon(
                  Icons.arrow_drop_down,
                  size: 16,
                  color: AppColors.primary,
                ),
              ],
            ),
          ),
          onSelected: (newMode) {
            ref.read(cameraMonitoringProvider.notifier).updateMonitoringMode(deviceId, newMode);
          },
          itemBuilder: (context) => [
            PopupMenuItem(
              value: MonitoringMode.active,
              child: Row(
                children: [
                  Icon(Icons.flash_on, size: 16, color: Colors.green),
                  const SizedBox(width: 8),
                  Text('Active (2s)'),
                ],
              ),
            ),
            PopupMenuItem(
              value: MonitoringMode.idle,
              child: Row(
                children: [
                  Icon(Icons.timer, size: 16, color: Colors.orange),
                  const SizedBox(width: 8),
                  Text('Idle (10s)'),
                ],
              ),
            ),
            PopupMenuItem(
              value: MonitoringMode.background,
              child: Row(
                children: [
                  Icon(Icons.battery_saver, size: 16, color: Colors.blue),
                  const SizedBox(width: 8),
                  Text('Background (30s)'),
                ],
              ),
            ),
          ],
        ),
        
        const SizedBox(width: 8),
        
        // Stop monitoring button
        InkWell(
          onTap: () {
            ref.read(cameraMonitoringProvider.notifier).stopMonitoring(deviceId);
          },
          child: Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: Colors.red.withOpacity(0.3)),
            ),
            child: Icon(
              Icons.stop,
              size: 14,
              color: Colors.red,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLoadingContent() {
    return Row(
      children: [
        const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: 12),
        Text(
          'Loading camera status...',
          style: OfflineFonts.inter(
            fontSize: compact ? 12 : 14,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildErrorContent(String error) {
    return Row(
      children: [
        Icon(
          Icons.error_outline,
          size: 16,
          color: Colors.red,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            'Error: $error',
            style: OfflineFonts.inter(
              fontSize: compact ? 12 : 14,
              color: Colors.red,
            ),
          ),
        ),
      ],
    );
  }

  Color _getConnectionStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'connected':
        return Colors.green;
      case 'connecting':
        return Colors.orange;
      case 'disconnected':
        return Colors.grey;
      case 'error':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Color _getStreamStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'active':
        return Colors.green;
      case 'starting':
        return Colors.orange;
      case 'stopping':
        return Colors.orange;
      case 'inactive':
        return Colors.grey;
      case 'error':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _getModeIcon(MonitoringMode? mode) {
    switch (mode) {
      case MonitoringMode.active:
        return Icons.flash_on;
      case MonitoringMode.idle:
        return Icons.timer;
      case MonitoringMode.background:
        return Icons.battery_saver;
      case MonitoringMode.disabled:
        return Icons.pause;
      default:
        return Icons.help_outline;
    }
  }

  String _getModeLabel(MonitoringMode? mode) {
    switch (mode) {
      case MonitoringMode.active:
        return 'Active';
      case MonitoringMode.idle:
        return 'Idle';
      case MonitoringMode.background:
        return 'Battery';
      case MonitoringMode.disabled:
        return 'Disabled';
      default:
        return 'Unknown';
    }
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes % 60;
    final seconds = duration.inSeconds % 60;
    
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    } else if (minutes > 0) {
      return '${minutes}m ${seconds}s';
    } else {
      return '${seconds}s';
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);
    
    if (difference.inSeconds < 60) {
      return 'just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
}

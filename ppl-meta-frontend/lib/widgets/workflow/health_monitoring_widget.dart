import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/workflow_widget_models.dart';
import '../../services/workflow_widget_api_client.dart';
import 'authenticated_workflow_wrapper.dart';

/// Widget for displaying system health monitoring with status indicators and alerts
class HealthMonitoringWidget extends ConsumerStatefulWidget {
  final bool showAlerts;
  final bool autoRefresh;
  final VoidCallback? onHealthChanged;

  const HealthMonitoringWidget({
    super.key,
    this.showAlerts = true,
    this.autoRefresh = true,
    this.onHealthChanged,
  });

  @override
  ConsumerState<HealthMonitoringWidget> createState() => _HealthMonitoringWidgetState();
}

class _HealthMonitoringWidgetState extends ConsumerState<HealthMonitoringWidget> {
  WorkflowWidgetApiClient? _apiClient;
  SystemHealthResponse? _health;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initializeApiClient();
    _loadHealth();
    
    if (widget.autoRefresh) {
      _startAutoRefresh();
    }
  }

  void _initializeApiClient() {
    _apiClient = ref.read(workflowWidgetApiClientProvider);
  }

  Future<void> _loadHealth() async {
    if (_apiClient == null) return;

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await _apiClient!.getProcessingSystemHealth();

      if (response.success && response.data != null) {
        setState(() {
          _health = response.data;
          _isLoading = false;
        });
        
        widget.onHealthChanged?.call();
      } else {
        setState(() {
          _error = response.message ?? 'Failed to load system health';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error loading health: $e';
        _isLoading = false;
      });
    }
  }

  void _startAutoRefresh() {
    Future.delayed(const Duration(seconds: 10), () {
      if (mounted && widget.autoRefresh) {
        _loadHealth().then((_) => _startAutoRefresh());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const _LoadingWidget();
    }

    if (_error != null) {
      return _ErrorWidget(
        error: _error!,
        onRetry: _loadHealth,
      );
    }

    if (_health == null) {
      return const _EmptyWidget();
    }

    return _HealthContentWidget(
      health: _health!,
      showAlerts: widget.showAlerts,
      onRefresh: _loadHealth,
    );
  }

  @override
  void dispose() {
    _apiClient?.dispose();
    super.dispose();
  }
}

/// Widget for displaying the main health content
class _HealthContentWidget extends StatelessWidget {
  final SystemHealthResponse health;
  final bool showAlerts;
  final VoidCallback onRefresh;

  const _HealthContentWidget({
    required this.health,
    required this.showAlerts,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildOverallHealthCard(context),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: _buildActiveSessionsCard(context)),
            const SizedBox(width: 12),
            Expanded(child: _buildQueueStatusCard(context)),
          ],
        ),
        const SizedBox(height: 16),
        _buildServicesHealthCard(context),
        if (showAlerts && health.alerts.isNotEmpty) ...[
          const SizedBox(height: 16),
          _buildAlertsCard(context),
        ],
      ],
    );
  }

  Widget _buildOverallHealthCard(BuildContext context) {
    return Card(
      color: _getOverallHealthColor().withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: _getOverallHealthColor(),
                shape: BoxShape.circle,
              ),
              child: Icon(
                _getOverallHealthIcon(),
                color: Colors.white,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'System Health',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    health.displayOverallStatus,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: _getOverallHealthColor(),
                    ),
                  ),
                  Text(
                    'Last checked: ${_formatTime(health.lastCheck)}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
            Column(
              children: [
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: onRefresh,
                  tooltip: 'Refresh Health Status',
                ),
                Text(
                  '${health.serviceHealthPercentage.toStringAsFixed(0)}%',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: _getOverallHealthColor(),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveSessionsCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.play_circle, color: Colors.blue, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Active Sessions',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              health.activeSessions.toString(),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: health.activeSessions > 0 ? Colors.blue : Colors.grey,
              ),
            ),
            Text(
              health.activeSessions == 1 ? 'session running' : 'sessions running',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQueueStatusCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.queue, color: Colors.green, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Queue Status',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              health.processingQueueSize.toString(),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: health.processingQueueSize > 0 ? Colors.orange : Colors.green,
              ),
            ),
            Text(
              health.processingQueueSize == 1 ? 'item queued' : 'items queued',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServicesHealthCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.dns, color: Colors.purple, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Services Health',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                Text(
                  '${health.healthyServicesCount}/${health.totalServicesCount}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: health.isHealthy ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...health.serviceHealth.entries.map(
              (entry) => _buildServiceItem(context, entry.key, entry.value),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServiceItem(BuildContext context, String serviceName, bool isHealthy) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: isHealthy ? Colors.green : Colors.red,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _formatServiceName(serviceName),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: isHealthy ? Colors.green.withOpacity(0.1) : Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isHealthy ? Colors.green.withOpacity(0.3) : Colors.red.withOpacity(0.3),
              ),
            ),
            child: Text(
              isHealthy ? 'Healthy' : 'Error',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: isHealthy ? Colors.green[700] : Colors.red[700],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertsCard(BuildContext context) {
    return Card(
      color: Colors.orange.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.warning, color: Colors.orange, size: 20),
                const SizedBox(width: 8),
                Text(
                  'System Alerts',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Colors.orange[700],
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.orange,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    health.alerts.length.toString(),
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...health.alerts.map(
              (alert) => _buildAlertItem(context, alert),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAlertItem(BuildContext context, String alert) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.error_outline, color: Colors.orange, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              alert,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.orange[700],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getOverallHealthColor() {
    switch (health.overallStatus) {
      case WorkflowWidgetStatus.completed:
        return Colors.green;
      case WorkflowWidgetStatus.error:
        return Colors.red;
      case WorkflowWidgetStatus.paused:
        return Colors.orange;
      case WorkflowWidgetStatus.inProgress:
        return Colors.blue;
      case WorkflowWidgetStatus.notStarted:
        return Colors.grey;
    }
  }

  IconData _getOverallHealthIcon() {
    switch (health.overallStatus) {
      case WorkflowWidgetStatus.completed:
        return Icons.check_circle;
      case WorkflowWidgetStatus.error:
        return Icons.error;
      case WorkflowWidgetStatus.paused:
        return Icons.warning;
      case WorkflowWidgetStatus.inProgress:
        return Icons.autorenew;
      case WorkflowWidgetStatus.notStarted:
        return Icons.help_outline;
    }
  }

  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

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

  String _formatServiceName(String serviceName) {
    return serviceName
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
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
              Text('Checking system health...'),
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
              'Health Check Failed',
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
                'No Health Data Available',
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
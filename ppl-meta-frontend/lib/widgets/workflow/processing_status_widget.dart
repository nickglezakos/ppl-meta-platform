import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/workflow_widget_models.dart';
import '../../services/workflow_widget_api_client.dart';
import 'authenticated_workflow_wrapper.dart';

/// Widget for displaying real-time processing status with progress indicators
class ProcessingStatusWidget extends ConsumerStatefulWidget {
  final String mediaUuid;
  final bool showProgress;
  final bool autoRefresh;
  final VoidCallback? onStatusChanged;

  const ProcessingStatusWidget({
    super.key,
    required this.mediaUuid,
    this.showProgress = true,
    this.autoRefresh = true,
    this.onStatusChanged,
  });

  @override
  ConsumerState<ProcessingStatusWidget> createState() => _ProcessingStatusWidgetState();
}

class _ProcessingStatusWidgetState extends ConsumerState<ProcessingStatusWidget> {
  WorkflowWidgetApiClient? _apiClient;
  WidgetStatusResponse? _status;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initializeApiClient();
    _loadStatus();
    
    // Auto-refresh disabled to prevent flickering - using cached providers instead
    // if (widget.autoRefresh) {
    //   _startAutoRefresh();
    // }
  }

  void _initializeApiClient() {
    _apiClient = ref.read(workflowWidgetApiClientProvider);
  }

  Future<void> _loadStatus() async {
    if (_apiClient == null) return;

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await _apiClient!.getWidgetProcessingStatus(
        mediaUuid: widget.mediaUuid,
        includeProgress: widget.showProgress,
      );

      if (response.success && response.data != null) {
        setState(() {
          _status = response.data;
          _isLoading = false;
        });
        
        widget.onStatusChanged?.call();
      } else {
        setState(() {
          _error = response.message ?? 'Failed to load processing status';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error loading status: $e';
        _isLoading = false;
      });
    }
  }

  // Auto-refresh disabled to prevent UI flickering
  // Use cached providers in workflow_providers.dart instead
  void _startAutoRefresh() {
    // Commented out to prevent flickering from frequent API calls
    // Future.delayed(const Duration(seconds: 5), () {
    //   if (mounted && widget.autoRefresh) {
    //     _loadStatus().then((_) => _startAutoRefresh());
    //   }
    // });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const _LoadingWidget();
    }

    if (_error != null) {
      return _ErrorWidget(
        error: _error!,
        onRetry: _loadStatus,
      );
    }

    if (_status == null) {
      return const _EmptyWidget();
    }

    return _StatusContentWidget(
      status: _status!,
      showProgress: widget.showProgress,
      onRefresh: _loadStatus,
    );
  }

  @override
  void dispose() {
    _apiClient?.dispose();
    super.dispose();
  }
}

/// Widget for displaying the main status content
class _StatusContentWidget extends StatelessWidget {
  final WidgetStatusResponse status;
  final bool showProgress;
  final VoidCallback onRefresh;

  const _StatusContentWidget({
    required this.status,
    required this.showProgress,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context),
            const SizedBox(height: 12),
            _buildStatusIndicator(context),
            if (showProgress && status.processingProgress != null) ...[
              const SizedBox(height: 16),
              _buildProgressSection(context),
            ],
            const SizedBox(height: 16),
            _buildStatsSection(context),
            if (status.errorMessage != null) ...[
              const SizedBox(height: 16),
              _buildErrorSection(context),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      children: [
        Icon(
          _getStatusIcon(),
          color: _getStatusColor(),
          size: 24,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            'Processing Status',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        IconButton(
          icon: const Icon(Icons.refresh),
          onPressed: onRefresh,
          tooltip: 'Refresh Status',
        ),
      ],
    );
  }

  Widget _buildStatusIndicator(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: _getStatusColor().withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _getStatusColor().withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: _getStatusColor(),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            status.displayStatus,
            style: TextStyle(
              color: _getStatusColor(),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressSection(BuildContext context) {
    final progress = status.processingProgress!;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Processing Progress',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        
        // Progress bar
        LinearProgressIndicator(
          value: progress.percentage / 100,
          backgroundColor: Colors.grey[300],
          valueColor: AlwaysStoppedAnimation<Color>(_getStatusColor()),
        ),
        const SizedBox(height: 8),
        
        // Progress details
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              progress.progressText,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            Text(
              progress.percentageText,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        
        if (progress.estimatedTimeText != null) ...[
          const SizedBox(height: 4),
          Text(
            'Est. ${progress.estimatedTimeText} remaining',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStatsSection(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            context,
            'Faces Detected',
            status.totalFacesDetected.toString(),
            Icons.face,
            Colors.blue,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            context,
            'Frames Processed',
            status.totalFramesProcessed.toString(),
            Icons.movie,
            Colors.green,
          ),
        ),
        if (status.cacheAvailable) ...[
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              context,
              'Cache',
              'Available',
              Icons.cached,
              Colors.orange,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStatCard(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
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

  Widget _buildErrorSection(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: Colors.red, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              status.errorMessage!,
              style: TextStyle(color: Colors.red[700]),
            ),
          ),
        ],
      ),
    );
  }

  IconData _getStatusIcon() {
    switch (status.status) {
      case WorkflowWidgetStatus.notStarted:
        return Icons.play_circle_outline;
      case WorkflowWidgetStatus.inProgress:
        return Icons.autorenew;
      case WorkflowWidgetStatus.completed:
        return Icons.check_circle;
      case WorkflowWidgetStatus.error:
        return Icons.error;
      case WorkflowWidgetStatus.paused:
        return Icons.pause_circle_outline;
    }
  }

  Color _getStatusColor() {
    switch (status.status) {
      case WorkflowWidgetStatus.notStarted:
        return Colors.grey;
      case WorkflowWidgetStatus.inProgress:
        return Colors.blue;
      case WorkflowWidgetStatus.completed:
        return Colors.green;
      case WorkflowWidgetStatus.error:
        return Colors.red;
      case WorkflowWidgetStatus.paused:
        return Colors.orange;
    }
  }
}

/// Loading widget
class _LoadingWidget extends StatelessWidget {
  const _LoadingWidget();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(16.0),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('Loading processing status...'),
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
        padding: const EdgeInsets.all(16.0),
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
              'Error Loading Status',
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
        padding: const EdgeInsets.all(16.0),
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
                'No Status Available',
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
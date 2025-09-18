import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/performance/simple_performance_metrics_widget.dart';

/// Performance metrics dialog that can be shown from any screen
class PerformanceMetricsDialog extends ConsumerStatefulWidget {
  final String? focusedWorkflow;
  final String? mediaUuid;
  
  const PerformanceMetricsDialog({
    super.key,
    this.focusedWorkflow,
    this.mediaUuid,
  });

  /// Show the performance metrics dialog
  static Future<void> show(
    BuildContext context, {
    String? focusedWorkflow,
    String? mediaUuid,
  }) async {
    return showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (BuildContext context) {
        return PerformanceMetricsDialog(
          focusedWorkflow: focusedWorkflow,
          mediaUuid: mediaUuid,
        );
      },
    );
  }

  @override
  ConsumerState<PerformanceMetricsDialog> createState() => _PerformanceMetricsDialogState();
}

class _PerformanceMetricsDialogState extends ConsumerState<PerformanceMetricsDialog> {
  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        height: MediaQuery.of(context).size.height * 0.8,
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          children: [
            _buildDialogHeader(),
            Expanded(
              child: PerformanceMetricsDisplayWidget(
                showDetailedView: true,
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildDialogHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[850],
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(16),
          topRight: Radius.circular(16),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.analytics, color: Colors.green[400], size: 24),
          const SizedBox(width: 12),
          const Text(
            'Workflow Performance Analytics',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (widget.focusedWorkflow != null) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: _getWorkflowColor(widget.focusedWorkflow!),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                _getWorkflowDisplayName(widget.focusedWorkflow!),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white70),
            onPressed: () => Navigator.of(context).pop(),
            tooltip: 'Close',
          ),
        ],
      ),
    );
  }
  
  Color _getWorkflowColor(String workflowType) {
    switch (workflowType) {
      case 'workflow4':
        return Colors.blue;
      case 'workflow5':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
  
  String _getWorkflowDisplayName(String workflowType) {
    switch (workflowType) {
      case 'workflow4':
        return 'Workflow 4 Focus';
      case 'workflow5':
        return 'Workflow 5 Focus';
      default:
        return 'All Workflows';
    }
  }
  
  /// Static method to show the performance metrics dialog
  static Future<void> show(BuildContext context, {
    String? focusedWorkflow,
    String? mediaUuid,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (context) => PerformanceMetricsDialog(
        focusedWorkflow: focusedWorkflow,
        mediaUuid: mediaUuid,
      ),
    );
  }
}

/// Simple performance metrics bottom sheet for mobile-friendly display
class PerformanceMetricsBottomSheet extends ConsumerWidget {
  final String? focusedWorkflow;
  final String? mediaUuid;
  
  const PerformanceMetricsBottomSheet({
    super.key,
    this.focusedWorkflow,
    this.mediaUuid,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: Colors.grey[900],
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(20),
              topRight: Radius.circular(20),
            ),
          ),
          child: Column(
            children: [
              // Handle bar
              Container(
                margin: const EdgeInsets.only(top: 8),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[600],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              
              // Header
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(Icons.speed, color: Colors.green[400], size: 24),
                    const SizedBox(width: 12),
                    const Text(
                      'Performance Metrics',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white70),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              
              // Content
              Expanded(
                child: SingleChildScrollView(
                  controller: scrollController,
                  child: PerformanceMetricsDisplayWidget(
                    showDetailedView: true,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
  
  /// Static method to show the performance metrics bottom sheet
  static Future<void> show(BuildContext context, {
    String? focusedWorkflow,
    String? mediaUuid,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => PerformanceMetricsBottomSheet(
        focusedWorkflow: focusedWorkflow,
        mediaUuid: mediaUuid,
      ),
    );
  }
}

/// Compact performance metrics widget for embedding in other screens
class CompactPerformanceMetricsWidget extends ConsumerWidget {
  final VoidCallback? onTap;
  
  const CompactPerformanceMetricsWidget({
    super.key,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: onTap,
      child: const PerformanceMetricsDisplayWidget(
        showDetailedView: false,
      ),
    );
  }
}
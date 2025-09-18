import 'package:flutter/material.dart';

enum WorkflowStepStatus {
  pending,
  inProgress,
  completed,
  failed,
  skipped,
}

class WorkflowStepData {
  final String id;
  final String title;
  final String description;
  final WorkflowStepStatus status;
  final IconData? icon;
  final Duration? duration;
  final String? errorMessage;
  final DateTime? startTime;
  final DateTime? endTime;

  const WorkflowStepData({
    required this.id,
    required this.title,
    required this.description,
    required this.status,
    this.icon,
    this.duration,
    this.errorMessage,
    this.startTime,
    this.endTime,
  });
}

class WorkflowStepIndicator extends StatelessWidget {
  final List<WorkflowStepData> steps;
  final bool isVertical;
  final double stepSpacing;
  final double stepSize;
  final bool showProgress;
  final VoidCallback? onRetry;
  final Function(WorkflowStepData)? onStepTapped;

  const WorkflowStepIndicator({
    Key? key,
    required this.steps,
    this.isVertical = true,
    this.stepSpacing = 32.0,
    this.stepSize = 40.0,
    this.showProgress = true,
    this.onRetry,
    this.onStepTapped,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (isVertical) {
      return _buildVerticalIndicator(context);
    } else {
      return _buildHorizontalIndicator(context);
    }
  }

  Widget _buildVerticalIndicator(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: List.generate(steps.length, (index) {
        final step = steps[index];
        final isLast = index == steps.length - 1;
        
        return Column(
          children: [
            _buildStepItem(context, step, index),
            if (!isLast) _buildVerticalConnector(context, step, steps[index + 1]),
          ],
        );
      }),
    );
  }

  Widget _buildHorizontalIndicator(BuildContext context) {
    return Row(
      children: List.generate(steps.length, (index) {
        final step = steps[index];
        final isLast = index == steps.length - 1;
        
        return Expanded(
          child: Row(
            children: [
              Expanded(child: _buildStepItem(context, step, index)),
              if (!isLast) _buildHorizontalConnector(context, step, steps[index + 1]),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildStepItem(BuildContext context, WorkflowStepData step, int index) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    
    Color getStepColor() {
      switch (step.status) {
        case WorkflowStepStatus.completed:
          return colorScheme.primary;
        case WorkflowStepStatus.inProgress:
          return colorScheme.secondary;
        case WorkflowStepStatus.failed:
          return colorScheme.error;
        case WorkflowStepStatus.skipped:
          return colorScheme.outline;
        case WorkflowStepStatus.pending:
          return colorScheme.onSurface.withOpacity(0.3);
      }
    }

    IconData getStepIcon() {
      if (step.icon != null) return step.icon!;
      
      switch (step.status) {
        case WorkflowStepStatus.completed:
          return Icons.check_circle;
        case WorkflowStepStatus.inProgress:
          return Icons.play_circle;
        case WorkflowStepStatus.failed:
          return Icons.error;
        case WorkflowStepStatus.skipped:
          return Icons.skip_next;
        case WorkflowStepStatus.pending:
          return Icons.radio_button_unchecked;
      }
    }

    return GestureDetector(
      onTap: () => onStepTapped?.call(step),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Step indicator circle
          Container(
            width: stepSize,
            height: stepSize,
            decoration: BoxDecoration(
              color: getStepColor(),
              shape: BoxShape.circle,
              boxShadow: step.status == WorkflowStepStatus.inProgress
                  ? [
                      BoxShadow(
                        color: getStepColor().withOpacity(0.3),
                        blurRadius: 8,
                        spreadRadius: 2,
                      ),
                    ]
                  : null,
            ),
            child: step.status == WorkflowStepStatus.inProgress
                ? _buildProgressIndicator(context)
                : Icon(
                    getStepIcon(),
                    color: step.status == WorkflowStepStatus.pending
                        ? colorScheme.onSurface.withOpacity(0.5)
                        : Colors.white,
                    size: stepSize * 0.6,
                  ),
          ),
          const SizedBox(width: 12),
          // Step content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  step.title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: step.status == WorkflowStepStatus.pending
                        ? colorScheme.onSurface.withOpacity(0.5)
                        : null,
                    fontWeight: step.status == WorkflowStepStatus.inProgress
                        ? FontWeight.bold
                        : null,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  step.description,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurface.withOpacity(0.7),
                  ),
                ),
                if (step.duration != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Duration: ${_formatDuration(step.duration!)}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurface.withOpacity(0.5),
                    ),
                  ),
                ],
                if (step.status == WorkflowStepStatus.failed && step.errorMessage != null) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: colorScheme.errorContainer,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.error_outline,
                          size: 16,
                          color: colorScheme.error,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            step.errorMessage!,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.error,
                            ),
                          ),
                        ),
                        if (onRetry != null) ...[
                          const SizedBox(width: 8),
                          TextButton(
                            onPressed: onRetry,
                            style: TextButton.styleFrom(
                              foregroundColor: colorScheme.error,
                              minimumSize: const Size(0, 32),
                            ),
                            child: const Text('Retry'),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressIndicator(BuildContext context) {
    return Padding(
      padding: EdgeInsets.all(stepSize * 0.15),
      child: CircularProgressIndicator(
        strokeWidth: 2,
        valueColor: AlwaysStoppedAnimation<Color>(
          Theme.of(context).colorScheme.onSecondary,
        ),
      ),
    );
  }

  Widget _buildVerticalConnector(BuildContext context, WorkflowStepData currentStep, WorkflowStepData nextStep) {
    final colorScheme = Theme.of(context).colorScheme;
    
    Color getConnectorColor() {
      if (currentStep.status == WorkflowStepStatus.completed) {
        return colorScheme.primary;
      } else if (currentStep.status == WorkflowStepStatus.inProgress) {
        return colorScheme.secondary;
      } else {
        return colorScheme.outline.withOpacity(0.3);
      }
    }

    return Container(
      margin: EdgeInsets.only(left: stepSize / 2 - 1),
      child: Column(
        children: [
          Container(
            width: 2,
            height: stepSpacing,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  getConnectorColor(),
                  nextStep.status == WorkflowStepStatus.pending
                      ? colorScheme.outline.withOpacity(0.3)
                      : getConnectorColor(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHorizontalConnector(BuildContext context, WorkflowStepData currentStep, WorkflowStepData nextStep) {
    final colorScheme = Theme.of(context).colorScheme;
    
    Color getConnectorColor() {
      if (currentStep.status == WorkflowStepStatus.completed) {
        return colorScheme.primary;
      } else if (currentStep.status == WorkflowStepStatus.inProgress) {
        return colorScheme.secondary;
      } else {
        return colorScheme.outline.withOpacity(0.3);
      }
    }

    return Container(
      margin: EdgeInsets.only(top: stepSize / 2 - 1),
      child: Container(
        height: 2,
        width: stepSpacing,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
            colors: [
              getConnectorColor(),
              nextStep.status == WorkflowStepStatus.pending
                  ? colorScheme.outline.withOpacity(0.3)
                  : getConnectorColor(),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDuration(Duration duration) {
    if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes.remainder(60)}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds.remainder(60)}s';
    } else {
      return '${duration.inSeconds}s';
    }
  }
}
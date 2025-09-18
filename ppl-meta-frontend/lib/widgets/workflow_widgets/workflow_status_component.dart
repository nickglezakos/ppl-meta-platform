import 'package:flutter/material.dart';

enum WorkflowStatus {
  idle,
  running,
  paused,
  completed,
  failed,
  warning,
}

class WorkflowStatusComponent extends StatefulWidget {
  final WorkflowStatus status;
  final String title;
  final String? subtitle;
  final String? message;
  final bool showPulse;
  final VoidCallback? onAction;
  final String? actionLabel;
  final Widget? customIcon;
  final Duration animationDuration;

  const WorkflowStatusComponent({
    Key? key,
    required this.status,
    required this.title,
    this.subtitle,
    this.message,
    this.showPulse = true,
    this.onAction,
    this.actionLabel,
    this.customIcon,
    this.animationDuration = const Duration(milliseconds: 1500),
  }) : super(key: key);

  @override
  State<WorkflowStatusComponent> createState() => _WorkflowStatusComponentState();
}

class _WorkflowStatusComponentState extends State<WorkflowStatusComponent>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _entryController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      duration: widget.animationDuration,
      vsync: this,
    );
    
    _entryController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.elasticOut),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.easeIn),
    );

    _entryController.forward();
    
    if (widget.showPulse && _shouldPulse()) {
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(WorkflowStatusComponent oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    if (widget.status != oldWidget.status) {
      _entryController.reset();
      _entryController.forward();
      
      if (widget.showPulse && _shouldPulse()) {
        _pulseController.repeat(reverse: true);
      } else {
        _pulseController.stop();
      }
    }
  }

  bool _shouldPulse() {
    return widget.status == WorkflowStatus.running || 
           widget.status == WorkflowStatus.warning;
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _entryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_entryController, _pulseController]),
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: Opacity(
            opacity: _fadeAnimation.value,
            child: Card(
              elevation: 2,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _buildStatusIcon(context),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                widget.title,
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: _getStatusColor(context),
                                ),
                              ),
                              if (widget.subtitle != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  widget.subtitle!,
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        if (widget.onAction != null) ...[
                          const SizedBox(width: 8),
                          _buildActionButton(context),
                        ],
                      ],
                    ),
                    if (widget.message != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: _getStatusColor(context).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: _getStatusColor(context).withOpacity(0.3),
                            width: 1,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              _getMessageIcon(),
                              size: 16,
                              color: _getStatusColor(context),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                widget.message!,
                                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: _getStatusColor(context),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatusIcon(BuildContext context) {
    final color = _getStatusColor(context);
    final icon = widget.customIcon ?? Icon(_getStatusIcon(), color: Colors.white);
    
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: widget.showPulse && _shouldPulse()
            ? [
                BoxShadow(
                  color: color.withOpacity(0.4),
                  blurRadius: 8 * _pulseAnimation.value,
                  spreadRadius: 2 * _pulseAnimation.value,
                ),
              ]
            : [
                BoxShadow(
                  color: color.withOpacity(0.2),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ],
      ),
      child: widget.status == WorkflowStatus.running
          ? Padding(
              padding: const EdgeInsets.all(12.0),
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            )
          : icon,
    );
  }

  Widget _buildActionButton(BuildContext context) {
    return ElevatedButton(
      onPressed: widget.onAction,
      style: ElevatedButton.styleFrom(
        backgroundColor: _getStatusColor(context),
        foregroundColor: Colors.white,
        minimumSize: const Size(80, 36),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
        ),
      ),
      child: Text(
        widget.actionLabel ?? _getDefaultActionLabel(),
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }

  Color _getStatusColor(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    
    switch (widget.status) {
      case WorkflowStatus.idle:
        return colorScheme.outline;
      case WorkflowStatus.running:
        return colorScheme.primary;
      case WorkflowStatus.paused:
        return colorScheme.secondary;
      case WorkflowStatus.completed:
        return Colors.green;
      case WorkflowStatus.failed:
        return colorScheme.error;
      case WorkflowStatus.warning:
        return Colors.orange;
    }
  }

  IconData _getStatusIcon() {
    switch (widget.status) {
      case WorkflowStatus.idle:
        return Icons.pause_circle;
      case WorkflowStatus.running:
        return Icons.play_circle;
      case WorkflowStatus.paused:
        return Icons.pause;
      case WorkflowStatus.completed:
        return Icons.check_circle;
      case WorkflowStatus.failed:
        return Icons.error;
      case WorkflowStatus.warning:
        return Icons.warning;
    }
  }

  IconData _getMessageIcon() {
    switch (widget.status) {
      case WorkflowStatus.completed:
        return Icons.check;
      case WorkflowStatus.failed:
        return Icons.error_outline;
      case WorkflowStatus.warning:
        return Icons.warning_amber;
      default:
        return Icons.info_outline;
    }
  }

  String _getDefaultActionLabel() {
    switch (widget.status) {
      case WorkflowStatus.idle:
        return 'Start';
      case WorkflowStatus.running:
        return 'Pause';
      case WorkflowStatus.paused:
        return 'Resume';
      case WorkflowStatus.completed:
        return 'Restart';
      case WorkflowStatus.failed:
        return 'Retry';
      case WorkflowStatus.warning:
        return 'Review';
    }
  }
}

class WorkflowStatusGrid extends StatelessWidget {
  final List<WorkflowStatusData> statuses;
  final int crossAxisCount;
  final double childAspectRatio;
  final EdgeInsets padding;

  const WorkflowStatusGrid({
    Key? key,
    required this.statuses,
    this.crossAxisCount = 2,
    this.childAspectRatio = 1.5,
    this.padding = const EdgeInsets.all(16.0),
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: crossAxisCount,
          childAspectRatio: childAspectRatio,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
        ),
        itemCount: statuses.length,
        itemBuilder: (context, index) {
          final statusData = statuses[index];
          return WorkflowStatusComponent(
            status: statusData.status,
            title: statusData.title,
            subtitle: statusData.subtitle,
            message: statusData.message,
            onAction: statusData.onAction,
            actionLabel: statusData.actionLabel,
            customIcon: statusData.customIcon,
          );
        },
      ),
    );
  }
}

class WorkflowStatusData {
  final WorkflowStatus status;
  final String title;
  final String? subtitle;
  final String? message;
  final VoidCallback? onAction;
  final String? actionLabel;
  final Widget? customIcon;

  const WorkflowStatusData({
    required this.status,
    required this.title,
    this.subtitle,
    this.message,
    this.onAction,
    this.actionLabel,
    this.customIcon,
  });
}
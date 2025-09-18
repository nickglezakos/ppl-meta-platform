import 'package:flutter/material.dart';

class WorkflowTimelineData {
  final String id;
  final String title;
  final String description;
  final DateTime timestamp;
  final WorkflowTimelineEventType type;
  final IconData? icon;
  final Color? color;
  final Map<String, dynamic>? metadata;
  final Duration? duration;

  const WorkflowTimelineData({
    required this.id,
    required this.title,
    required this.description,
    required this.timestamp,
    required this.type,
    this.icon,
    this.color,
    this.metadata,
    this.duration,
  });
}

enum WorkflowTimelineEventType {
  started,
  completed,
  failed,
  paused,
  resumed,
  warning,
  milestone,
  user_action,
}

class WorkflowExecutionTimeline extends StatefulWidget {
  final List<WorkflowTimelineData> events;
  final bool isReversed;
  final bool showTime;
  final bool showDuration;
  final bool isCompact;
  final Function(WorkflowTimelineData)? onEventTapped;
  final ScrollController? scrollController;

  const WorkflowExecutionTimeline({
    Key? key,
    required this.events,
    this.isReversed = false,
    this.showTime = true,
    this.showDuration = true,
    this.isCompact = false,
    this.onEventTapped,
    this.scrollController,
  }) : super(key: key);

  @override
  State<WorkflowExecutionTimeline> createState() => _WorkflowExecutionTimelineState();
}

class _WorkflowExecutionTimelineState extends State<WorkflowExecutionTimeline> {
  late ScrollController _scrollController;

  @override
  void initState() {
    super.initState();
    _scrollController = widget.scrollController ?? ScrollController();
  }

  @override
  void dispose() {
    if (widget.scrollController == null) {
      _scrollController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final events = widget.isReversed 
        ? widget.events.reversed.toList() 
        : widget.events;

    if (events.isEmpty) {
      return _buildEmptyState(context);
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16.0),
      itemCount: events.length,
      itemBuilder: (context, index) {
        final event = events[index];
        final isLast = index == events.length - 1;
        return _buildTimelineItem(context, event, isLast);
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.timeline,
            size: 64,
            color: colorScheme.outline.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No workflow events yet',
            style: theme.textTheme.titleMedium?.copyWith(
              color: colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Events will appear here as the workflow executes',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colorScheme.onSurface.withOpacity(0.5),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineItem(BuildContext context, WorkflowTimelineData event, bool isLast) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return GestureDetector(
      onTap: () => widget.onEventTapped?.call(event),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline indicator column
          Column(
            children: [
              _buildEventIndicator(context, event),
              if (!isLast) _buildTimelineConnector(context),
            ],
          ),
          const SizedBox(width: 16),
          // Event content
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                bottom: isLast ? 0 : (widget.isCompact ? 16 : 24),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header row with title and time
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              event.title,
                              style: theme.textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.w600,
                                color: _getEventColor(context, event),
                              ),
                            ),
                            if (!widget.isCompact) ...[
                              const SizedBox(height: 4),
                              Text(
                                event.description,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: colorScheme.onSurface.withOpacity(0.7),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      if (widget.showTime) ...[
                        const SizedBox(width: 8),
                        _buildTimeInfo(context, event),
                      ],
                    ],
                  ),
                  // Duration info
                  if (widget.showDuration && event.duration != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: colorScheme.surfaceVariant,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.timer,
                            size: 14,
                            color: colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            _formatDuration(event.duration!),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  // Metadata
                  if (event.metadata != null && event.metadata!.isNotEmpty && !widget.isCompact) ...[
                    const SizedBox(height: 8),
                    _buildMetadata(context, event.metadata!),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEventIndicator(BuildContext context, WorkflowTimelineData event) {
    final color = event.color ?? _getEventColor(context, event);
    final icon = event.icon ?? _getEventIcon(event.type);

    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.3),
            blurRadius: 4,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Icon(
        icon,
        color: Colors.white,
        size: 20,
      ),
    );
  }

  Widget _buildTimelineConnector(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    
    return Container(
      width: 2,
      height: widget.isCompact ? 24 : 32,
      color: colorScheme.outline.withOpacity(0.3),
      margin: const EdgeInsets.symmetric(vertical: 4),
    );
  }

  Widget _buildTimeInfo(BuildContext context, WorkflowTimelineData event) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(
          _formatTime(event.timestamp),
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurface.withOpacity(0.6),
            fontWeight: FontWeight.w500,
          ),
        ),
        Text(
          _formatDate(event.timestamp),
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurface.withOpacity(0.4),
            fontSize: 10,
          ),
        ),
      ],
    );
  }

  Widget _buildMetadata(BuildContext context, Map<String, dynamic> metadata) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colorScheme.surfaceVariant.withOpacity(0.5),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: metadata.entries.map((entry) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${entry.key}: ',
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                Expanded(
                  child: Text(
                    entry.value.toString(),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Color _getEventColor(BuildContext context, WorkflowTimelineData event) {
    final colorScheme = Theme.of(context).colorScheme;
    
    switch (event.type) {
      case WorkflowTimelineEventType.started:
        return colorScheme.primary;
      case WorkflowTimelineEventType.completed:
        return Colors.green;
      case WorkflowTimelineEventType.failed:
        return colorScheme.error;
      case WorkflowTimelineEventType.paused:
        return Colors.orange;
      case WorkflowTimelineEventType.resumed:
        return colorScheme.secondary;
      case WorkflowTimelineEventType.warning:
        return Colors.amber;
      case WorkflowTimelineEventType.milestone:
        return Colors.purple;
      case WorkflowTimelineEventType.user_action:
        return Colors.blue;
    }
  }

  IconData _getEventIcon(WorkflowTimelineEventType type) {
    switch (type) {
      case WorkflowTimelineEventType.started:
        return Icons.play_arrow;
      case WorkflowTimelineEventType.completed:
        return Icons.check;
      case WorkflowTimelineEventType.failed:
        return Icons.error;
      case WorkflowTimelineEventType.paused:
        return Icons.pause;
      case WorkflowTimelineEventType.resumed:
        return Icons.play_arrow;
      case WorkflowTimelineEventType.warning:
        return Icons.warning;
      case WorkflowTimelineEventType.milestone:
        return Icons.flag;
      case WorkflowTimelineEventType.user_action:
        return Icons.person;
    }
  }

  String _formatTime(DateTime dateTime) {
    return '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  String _formatDate(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inDays == 0) {
      return 'Today';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else {
      return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
    }
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
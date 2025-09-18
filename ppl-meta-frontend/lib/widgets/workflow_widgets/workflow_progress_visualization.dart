import 'package:flutter/material.dart';
import 'dart:math' as math;

class WorkflowProgressVisualization extends StatefulWidget {
  final double progress; // 0.0 to 1.0
  final String? title;
  final String? subtitle;
  final List<String>? phaseLabels;
  final Color? primaryColor;
  final Color? backgroundColor;
  final bool animated;
  final Duration animationDuration;
  final WorkflowProgressType type;
  final double size;

  const WorkflowProgressVisualization({
    Key? key,
    required this.progress,
    this.title,
    this.subtitle,
    this.phaseLabels,
    this.primaryColor,
    this.backgroundColor,
    this.animated = true,
    this.animationDuration = const Duration(milliseconds: 800),
    this.type = WorkflowProgressType.circular,
    this.size = 120.0,
  }) : super(key: key);

  @override
  State<WorkflowProgressVisualization> createState() => _WorkflowProgressVisualizationState();
}

enum WorkflowProgressType {
  circular,
  linear,
  radial,
  segmented,
}

class _WorkflowProgressVisualizationState extends State<WorkflowProgressVisualization>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _progressAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: widget.animationDuration,
      vsync: this,
    );
    
    _progressAnimation = Tween<double>(
      begin: 0.0,
      end: widget.progress,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));

    if (widget.animated) {
      _animationController.forward();
    }
  }

  @override
  void didUpdateWidget(WorkflowProgressVisualization oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.progress != oldWidget.progress) {
      _progressAnimation = Tween<double>(
        begin: oldWidget.progress,
        end: widget.progress,
      ).animate(CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeInOut,
      ));
      
      if (widget.animated) {
        _animationController.reset();
        _animationController.forward();
      }
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _progressAnimation,
      builder: (context, child) {
        final currentProgress = widget.animated 
            ? _progressAnimation.value 
            : widget.progress;
            
        switch (widget.type) {
          case WorkflowProgressType.circular:
            return _buildCircularProgress(context, currentProgress);
          case WorkflowProgressType.linear:
            return _buildLinearProgress(context, currentProgress);
          case WorkflowProgressType.radial:
            return _buildRadialProgress(context, currentProgress);
          case WorkflowProgressType.segmented:
            return _buildSegmentedProgress(context, currentProgress);
        }
      },
    );
  }

  Widget _buildCircularProgress(BuildContext context, double progress) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final primaryColor = widget.primaryColor ?? colorScheme.primary;
    final backgroundColor = widget.backgroundColor ?? colorScheme.surfaceVariant;

    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background circle
          SizedBox(
            width: widget.size,
            height: widget.size,
            child: CircularProgressIndicator(
              value: 1.0,
              strokeWidth: 8,
              valueColor: AlwaysStoppedAnimation<Color>(backgroundColor),
            ),
          ),
          // Progress circle
          SizedBox(
            width: widget.size,
            height: widget.size,
            child: CircularProgressIndicator(
              value: progress,
              strokeWidth: 8,
              valueColor: AlwaysStoppedAnimation<Color>(primaryColor),
              strokeCap: StrokeCap.round,
            ),
          ),
          // Center content
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '${(progress * 100).round()}%',
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: primaryColor,
                ),
              ),
              if (widget.title != null) ...[
                const SizedBox(height: 4),
                Text(
                  widget.title!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurface.withOpacity(0.7),
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLinearProgress(BuildContext context, double progress) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final primaryColor = widget.primaryColor ?? colorScheme.primary;
    final backgroundColor = widget.backgroundColor ?? colorScheme.surfaceVariant;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.title != null) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.title!,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '${(progress * 100).round()}%',
                style: theme.textTheme.titleMedium?.copyWith(
                  color: primaryColor,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
        ],
        Container(
          height: 8,
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: BorderRadius.circular(4),
          ),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: progress,
            child: Container(
              decoration: BoxDecoration(
                color: primaryColor,
                borderRadius: BorderRadius.circular(4),
                gradient: LinearGradient(
                  colors: [
                    primaryColor,
                    primaryColor.withOpacity(0.8),
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: primaryColor.withOpacity(0.3),
                    blurRadius: 4,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
          ),
        ),
        if (widget.subtitle != null) ...[
          const SizedBox(height: 4),
          Text(
            widget.subtitle!,
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildRadialProgress(BuildContext context, double progress) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final primaryColor = widget.primaryColor ?? colorScheme.primary;

    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: CustomPaint(
        painter: RadialProgressPainter(
          progress: progress,
          primaryColor: primaryColor,
          backgroundColor: widget.backgroundColor ?? colorScheme.surfaceVariant,
          strokeWidth: 12,
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '${(progress * 100).round()}%',
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: primaryColor,
                ),
              ),
              if (widget.title != null) ...[
                const SizedBox(height: 4),
                Text(
                  widget.title!,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurface.withOpacity(0.7),
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSegmentedProgress(BuildContext context, double progress) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final primaryColor = widget.primaryColor ?? colorScheme.primary;
    final backgroundColor = widget.backgroundColor ?? colorScheme.surfaceVariant;
    
    final phases = widget.phaseLabels ?? ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4'];
    final segmentProgress = progress * phases.length;
    final currentSegment = segmentProgress.floor();
    final currentSegmentProgress = segmentProgress - currentSegment;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.title != null) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.title!,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '${(progress * 100).round()}%',
                style: theme.textTheme.titleMedium?.copyWith(
                  color: primaryColor,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
        ],
        Row(
          children: List.generate(phases.length, (index) {
            final isCompleted = index < currentSegment;
            final isInProgress = index == currentSegment;
            
            return Expanded(
              child: Container(
                margin: EdgeInsets.only(right: index < phases.length - 1 ? 8 : 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      height: 8,
                      decoration: BoxDecoration(
                        color: backgroundColor,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: isCompleted
                          ? Container(
                              decoration: BoxDecoration(
                                color: primaryColor,
                                borderRadius: BorderRadius.circular(4),
                              ),
                            )
                          : isInProgress
                              ? FractionallySizedBox(
                                  alignment: Alignment.centerLeft,
                                  widthFactor: currentSegmentProgress,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      color: primaryColor,
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                  ),
                                )
                              : null,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      phases[index],
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: isCompleted || isInProgress
                            ? colorScheme.onSurface
                            : colorScheme.onSurface.withOpacity(0.5),
                        fontWeight: isInProgress ? FontWeight.w600 : null,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}

class RadialProgressPainter extends CustomPainter {
  final double progress;
  final Color primaryColor;
  final Color backgroundColor;
  final double strokeWidth;

  RadialProgressPainter({
    required this.progress,
    required this.primaryColor,
    required this.backgroundColor,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;

    // Draw background circle
    final backgroundPaint = Paint()
      ..color = backgroundColor
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, backgroundPaint);

    // Draw progress arc
    final progressPaint = Paint()
      ..color = primaryColor
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final sweepAngle = 2 * math.pi * progress;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2, // Start from top
      sweepAngle,
      false,
      progressPaint,
    );

    // Draw glow effect
    if (progress > 0) {
      final glowPaint = Paint()
        ..color = primaryColor.withOpacity(0.3)
        ..strokeWidth = strokeWidth + 4
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2,
        sweepAngle,
        false,
        glowPaint,
      );
    }
  }

  @override
  bool shouldRepaint(RadialProgressPainter oldDelegate) {
    return progress != oldDelegate.progress ||
        primaryColor != oldDelegate.primaryColor ||
        backgroundColor != oldDelegate.backgroundColor;
  }
}
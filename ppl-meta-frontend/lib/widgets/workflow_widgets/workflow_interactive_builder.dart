import 'package:flutter/material.dart';

enum WorkflowActionType {
  primary,
  secondary,
  destructive,
  warning,
  success,
}

class WorkflowAction {
  final String id;
  final String label;
  final IconData? icon;
  final WorkflowActionType type;
  final VoidCallback? onPressed;
  final bool isEnabled;
  final bool isLoading;
  final String? tooltip;

  const WorkflowAction({
    required this.id,
    required this.label,
    this.icon,
    this.type = WorkflowActionType.primary,
    this.onPressed,
    this.isEnabled = true,
    this.isLoading = false,
    this.tooltip,
  });
}

class WorkflowInteractiveBuilder extends StatefulWidget {
  final String title;
  final String? subtitle;
  final Widget? header;
  final Widget content;
  final List<WorkflowAction> actions;
  final bool isExpanded;
  final bool isCollapsible;
  final VoidCallback? onToggleExpanded;
  final EdgeInsets? padding;
  final Color? backgroundColor;
  final double? elevation;

  const WorkflowInteractiveBuilder({
    Key? key,
    required this.title,
    this.subtitle,
    this.header,
    required this.content,
    this.actions = const [],
    this.isExpanded = true,
    this.isCollapsible = true,
    this.onToggleExpanded,
    this.padding,
    this.backgroundColor,
    this.elevation,
  }) : super(key: key);

  @override
  State<WorkflowInteractiveBuilder> createState() => _WorkflowInteractiveBuilderState();
}

class _WorkflowInteractiveBuilderState extends State<WorkflowInteractiveBuilder>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _expandAnimation;
  bool _isExpanded = true;

  @override
  void initState() {
    super.initState();
    _isExpanded = widget.isExpanded;
    
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    _expandAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    );

    if (_isExpanded) {
      _animationController.value = 1.0;
    }
  }

  @override
  void didUpdateWidget(WorkflowInteractiveBuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isExpanded != oldWidget.isExpanded) {
      _toggleExpanded(widget.isExpanded);
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _toggleExpanded([bool? forceExpanded]) {
    setState(() {
      _isExpanded = forceExpanded ?? !_isExpanded;
    });

    if (_isExpanded) {
      _animationController.forward();
    } else {
      _animationController.reverse();
    }

    widget.onToggleExpanded?.call();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      elevation: widget.elevation ?? 2,
      color: widget.backgroundColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          InkWell(
            onTap: widget.isCollapsible ? () => _toggleExpanded() : null,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
            child: Container(
              width: double.infinity,
              padding: widget.padding ?? const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                widget.title,
                                style: theme.textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            if (widget.isCollapsible) ...[
                              const SizedBox(width: 8),
                              AnimatedRotation(
                                turns: _isExpanded ? 0.5 : 0,
                                duration: const Duration(milliseconds: 300),
                                child: Icon(
                                  Icons.keyboard_arrow_down,
                                  color: colorScheme.onSurface.withOpacity(0.6),
                                ),
                              ),
                            ],
                          ],
                        ),
                        if (widget.subtitle != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            widget.subtitle!,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: colorScheme.onSurface.withOpacity(0.7),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          // Custom header
          if (widget.header != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: widget.header!,
            ),

          // Expandable content
          SizeTransition(
            sizeFactor: _expandAnimation,
            child: Column(
              children: [
                // Content
                Padding(
                  padding: widget.padding ?? const EdgeInsets.all(16),
                  child: widget.content,
                ),
                
                // Actions
                if (widget.actions.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    child: _buildActions(context),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActions(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: widget.actions.map((action) => _buildActionButton(context, action)).toList(),
    );
  }

  Widget _buildActionButton(BuildContext context, WorkflowAction action) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    Color getButtonColor() {
      switch (action.type) {
        case WorkflowActionType.primary:
          return colorScheme.primary;
        case WorkflowActionType.secondary:
          return colorScheme.secondary;
        case WorkflowActionType.destructive:
          return colorScheme.error;
        case WorkflowActionType.warning:
          return Colors.orange;
        case WorkflowActionType.success:
          return Colors.green;
      }
    }

    Widget button;

    if (action.type == WorkflowActionType.secondary) {
      button = OutlinedButton.icon(
        onPressed: action.isEnabled && !action.isLoading ? action.onPressed : null,
        icon: action.isLoading
            ? SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : action.icon != null
                ? Icon(action.icon, size: 18)
                : const SizedBox.shrink(),
        label: Text(action.label),
        style: OutlinedButton.styleFrom(
          foregroundColor: getButtonColor(),
          side: BorderSide(color: getButtonColor()),
        ),
      );
    } else {
      button = ElevatedButton.icon(
        onPressed: action.isEnabled && !action.isLoading ? action.onPressed : null,
        icon: action.isLoading
            ? SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : action.icon != null
                ? Icon(action.icon, size: 18)
                : const SizedBox.shrink(),
        label: Text(action.label),
        style: ElevatedButton.styleFrom(
          backgroundColor: getButtonColor(),
          foregroundColor: Colors.white,
        ),
      );
    }

    if (action.tooltip != null) {
      return Tooltip(
        message: action.tooltip!,
        child: button,
      );
    }

    return button;
  }
}

class WorkflowBuilderStep extends StatelessWidget {
  final String title;
  final String? description;
  final Widget content;
  final List<WorkflowAction> actions;
  final bool isActive;
  final bool isCompleted;
  final bool isEnabled;

  const WorkflowBuilderStep({
    Key? key,
    required this.title,
    this.description,
    required this.content,
    this.actions = const [],
    this.isActive = false,
    this.isCompleted = false,
    this.isEnabled = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        border: Border.all(
          color: isActive
              ? colorScheme.primary
              : isCompleted
                  ? Colors.green
                  : colorScheme.outline.withOpacity(0.3),
          width: isActive ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(12),
        color: isActive
            ? colorScheme.primary.withOpacity(0.05)
            : isCompleted
                ? Colors.green.withOpacity(0.05)
                : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                // Status indicator
                Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    color: isCompleted
                        ? Colors.green
                        : isActive
                            ? colorScheme.primary
                            : colorScheme.outline.withOpacity(0.3),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    isCompleted
                        ? Icons.check
                        : isActive
                            ? Icons.play_arrow
                            : Icons.radio_button_unchecked,
                    color: Colors.white,
                    size: 16,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: isEnabled
                              ? null
                              : colorScheme.onSurface.withOpacity(0.5),
                        ),
                      ),
                      if (description != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          description!,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: isEnabled
                                ? colorScheme.onSurface.withOpacity(0.7)
                                : colorScheme.onSurface.withOpacity(0.4),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          // Content
          if (isEnabled) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: content,
            ),
            
            // Actions
            if (actions.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: actions.map((action) {
                    return ElevatedButton.icon(
                      onPressed: action.isEnabled && !action.isLoading ? action.onPressed : null,
                      icon: action.isLoading
                          ? SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : action.icon != null
                              ? Icon(action.icon, size: 18)
                              : const SizedBox.shrink(),
                      label: Text(action.label),
                    );
                  }).toList(),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}

class WorkflowStepBuilder extends StatefulWidget {
  final List<WorkflowBuilderStep> steps;
  final int currentStep;
  final Function(int)? onStepChanged;
  final bool allowSkipping;
  final ScrollController? scrollController;

  const WorkflowStepBuilder({
    Key? key,
    required this.steps,
    this.currentStep = 0,
    this.onStepChanged,
    this.allowSkipping = false,
    this.scrollController,
  }) : super(key: key);

  @override
  State<WorkflowStepBuilder> createState() => _WorkflowStepBuilderState();
}

class _WorkflowStepBuilderState extends State<WorkflowStepBuilder> {
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
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: widget.steps.length,
      itemBuilder: (context, index) {
        final step = widget.steps[index];
        final isActive = index == widget.currentStep;
        final isCompleted = index < widget.currentStep;
        final isEnabled = isActive || isCompleted || widget.allowSkipping;

        return WorkflowBuilderStep(
          title: step.title,
          description: step.description,
          content: step.content,
          actions: step.actions,
          isActive: isActive,
          isCompleted: isCompleted,
          isEnabled: isEnabled,
        );
      },
    );
  }
}
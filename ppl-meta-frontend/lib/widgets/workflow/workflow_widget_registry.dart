import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'processing_status_widget.dart';
import 'analytics_dashboard_widget.dart';
import 'health_monitoring_widget.dart';
import 'authenticated_workflow_wrapper.dart';

/// Enum for different workflow widget types
enum WorkflowWidgetType {
  processingStatus,
  analyticsDashboard,
  healthMonitoring,
  all, // For displaying all widgets
}

/// Widget configuration for the registry
class WorkflowWidgetConfig {
  final String title;
  final String description;
  final IconData icon;
  final Color? color;
  final bool requiresUserUuid;
  final Widget Function(String? userUuid) builder;

  const WorkflowWidgetConfig({
    required this.title,
    required this.description,
    required this.icon,
    this.color,
    this.requiresUserUuid = true,
    required this.builder,
  });
}

/// Registry for all workflow widgets
class WorkflowWidgetRegistry {
  static final Map<WorkflowWidgetType, WorkflowWidgetConfig> _widgets = {
    WorkflowWidgetType.processingStatus: WorkflowWidgetConfig(
      title: 'Processing Status',
      description: 'Real-time status monitoring for face detection processing',
      icon: Icons.trending_up,
      color: Colors.blue,
      requiresUserUuid: true,
      builder: (userUuid) => ProcessingStatusWidget(
        mediaUuid: userUuid!, // ProcessingStatusWidget expects mediaUuid
        autoRefresh: true,
        showProgress: true,
      ),
    ),
    WorkflowWidgetType.analyticsDashboard: WorkflowWidgetConfig(
      title: 'Analytics Dashboard',
      description: 'Comprehensive analytics and metrics for processing workflows',
      icon: Icons.dashboard,
      color: Colors.green,
      requiresUserUuid: true,
      builder: (userUuid) => AnalyticsDashboardWidget(
        mediaUuid: userUuid!, // AnalyticsDashboardWidget expects mediaUuid
        autoRefresh: true,
        showRecommendations: true,
      ),
    ),
    WorkflowWidgetType.healthMonitoring: WorkflowWidgetConfig(
      title: 'System Health',
      description: 'Monitor system health, services status, and alerts',
      icon: Icons.favorite,
      color: Colors.red,
      requiresUserUuid: false,
      builder: (userUuid) => const HealthMonitoringWidget(
        showAlerts: true,
        autoRefresh: true,
      ),
    ),
  };

  /// Get widget configuration
  static WorkflowWidgetConfig? getConfig(WorkflowWidgetType type) {
    return _widgets[type];
  }

  /// Get all widget configurations
  static Map<WorkflowWidgetType, WorkflowWidgetConfig> getAllConfigs() {
    return Map.unmodifiable(_widgets);
  }

  /// Get widget types that require user UUID
  static List<WorkflowWidgetType> getAuthenticatedWidgets() {
    return _widgets.entries
        .where((entry) => entry.value.requiresUserUuid)
        .map((entry) => entry.key)
        .toList();
  }

  /// Get widget types that don't require user UUID
  static List<WorkflowWidgetType> getPublicWidgets() {
    return _widgets.entries
        .where((entry) => !entry.value.requiresUserUuid)
        .map((entry) => entry.key)
        .toList();
  }

  /// Build a specific widget with authentication wrapper
  static Widget buildWidget(
    WorkflowWidgetType type, {
    String? userUuid,
    bool wrapWithAuth = true,
  }) {
    final config = getConfig(type);
    if (config == null) {
      return const _WidgetNotFoundError();
    }

    final widget = config.builder(userUuid);

    if (wrapWithAuth && config.requiresUserUuid) {
      return AuthenticatedWorkflowWrapper(
        requiresAuth: true,
        child: widget,
      );
    }

    return widget;
  }
}

/// Widget for displaying workflow widget selector
class WorkflowWidgetSelector extends StatelessWidget {
  final Function(WorkflowWidgetType)? onWidgetSelected;
  final List<WorkflowWidgetType>? allowedWidgets;
  final bool showDescriptions;

  const WorkflowWidgetSelector({
    super.key,
    this.onWidgetSelected,
    this.allowedWidgets,
    this.showDescriptions = true,
  });

  @override
  Widget build(BuildContext context) {
    final configs = WorkflowWidgetRegistry.getAllConfigs();
    final widgets = allowedWidgets ?? configs.keys.toList();

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 1.2,
      ),
      itemCount: widgets.length,
      itemBuilder: (context, index) {
        final type = widgets[index];
        final config = configs[type]!;
        return _WidgetSelectorCard(
          config: config,
          onTap: () => onWidgetSelected?.call(type),
        );
      },
    );
  }
}

/// Card widget for widget selection
class _WidgetSelectorCard extends StatelessWidget {
  final WorkflowWidgetConfig config;
  final VoidCallback? onTap;

  const _WidgetSelectorCard({
    required this.config,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: (config.color ?? Colors.blue).withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  config.icon,
                  size: 32,
                  color: config.color ?? Colors.blue,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                config.title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                config.description,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Widget for displaying a workflow widget with navigation
class WorkflowWidgetPage extends ConsumerWidget {
  final WorkflowWidgetType widgetType;
  final bool showAppBar;
  final String? customTitle;

  const WorkflowWidgetPage({
    super.key,
    required this.widgetType,
    this.showAppBar = true,
    this.customTitle,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = WorkflowWidgetRegistry.getConfig(widgetType);
    
    if (config == null) {
      return const Scaffold(
        body: _WidgetNotFoundError(),
      );
    }

    return WorkflowWidgetWrapper(
      title: customTitle ?? config.title,
      showAppBar: showAppBar,
      builder: (apiClient, userUuid) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: config.builder(config.requiresUserUuid ? userUuid : null),
      ),
    );
  }
}

/// Widget for displaying all workflow widgets in a dashboard layout
class WorkflowDashboard extends ConsumerWidget {
  final List<WorkflowWidgetType>? visibleWidgets;
  final bool allowToggle;

  const WorkflowDashboard({
    super.key,
    this.visibleWidgets,
    this.allowToggle = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AuthenticatedWorkflowBuilder(
      builder: (context, apiClient, userUuid) {
        final widgets = visibleWidgets ?? [
          WorkflowWidgetType.processingStatus,
          WorkflowWidgetType.analyticsDashboard,
          WorkflowWidgetType.healthMonitoring,
        ];

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Workflow Dashboard',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Monitor your face detection workflows and system health',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 24),
              ...widgets.map((type) => _buildDashboardWidget(context, type, userUuid)),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDashboardWidget(BuildContext context, WorkflowWidgetType type, String userUuid) {
    final config = WorkflowWidgetRegistry.getConfig(type);
    if (config == null) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(config.icon, color: config.color),
            const SizedBox(width: 8),
            Text(
              config.title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const Spacer(),
            if (allowToggle)
              IconButton(
                icon: const Icon(Icons.open_in_new),
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => WorkflowWidgetPage(widgetType: type),
                    ),
                  );
                },
                tooltip: 'Open in full screen',
              ),
          ],
        ),
        const SizedBox(height: 16),
        config.builder(config.requiresUserUuid ? userUuid : null),
        const SizedBox(height: 32),
      ],
    );
  }
}

/// Error widget for widget not found
class _WidgetNotFoundError extends StatelessWidget {
  const _WidgetNotFoundError();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.widgets,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'Widget Not Found',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'The requested workflow widget is not available',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }
}

/// Navigation helper for workflow widgets
class WorkflowWidgetNavigation {
  /// Navigate to a specific workflow widget
  static void navigateToWidget(
    BuildContext context,
    WorkflowWidgetType type, {
    String? customTitle,
  }) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => WorkflowWidgetPage(
          widgetType: type,
          customTitle: customTitle,
        ),
      ),
    );
  }

  /// Navigate to workflow dashboard
  static void navigateToDashboard(
    BuildContext context, {
    List<WorkflowWidgetType>? visibleWidgets,
  }) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => Scaffold(
          appBar: AppBar(
            title: const Text('Workflow Dashboard'),
            backgroundColor: Theme.of(context).colorScheme.inversePrimary,
          ),
          body: WorkflowDashboard(visibleWidgets: visibleWidgets),
        ),
      ),
    );
  }

  /// Navigate to widget selector
  static void navigateToSelector(
    BuildContext context, {
    List<WorkflowWidgetType>? allowedWidgets,
  }) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => Scaffold(
          appBar: AppBar(
            title: const Text('Select Workflow Widget'),
            backgroundColor: Theme.of(context).colorScheme.inversePrimary,
          ),
          body: WorkflowWidgetSelector(
            allowedWidgets: allowedWidgets,
            onWidgetSelected: (type) {
              Navigator.of(context).pop();
              navigateToWidget(context, type);
            },
          ),
        ),
      ),
    );
  }
}
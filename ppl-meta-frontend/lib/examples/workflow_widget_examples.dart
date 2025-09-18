import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/workflow/workflow_widget_registry.dart';
import '../widgets/workflow/authenticated_workflow_wrapper.dart';

/// Example page demonstrating workflow widget usage
class WorkflowWidgetExamplePage extends ConsumerWidget {
  const WorkflowWidgetExamplePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Workflow Widgets Demo'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader(context, 'Widget Selector'),
            _buildWidgetSelector(context),
            const SizedBox(height: 32),
            
            _buildSectionHeader(context, 'Individual Widgets'),
            _buildIndividualWidgetButtons(context),
            const SizedBox(height: 32),
            
            _buildSectionHeader(context, 'Dashboard'),
            _buildDashboardButton(context),
            const SizedBox(height: 32),
            
            _buildSectionHeader(context, 'Authentication Testing'),
            _buildAuthenticationTesting(context),
            const SizedBox(height: 32),
            
            _buildSectionHeader(context, 'Embedded Widgets Demo'),
            _buildEmbeddedWidgetsDemo(context),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Text(
        title,
        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildWidgetSelector(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Widget Selector',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Choose from available workflow widgets',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                WorkflowWidgetNavigation.navigateToSelector(context);
              },
              icon: const Icon(Icons.widgets),
              label: const Text('Open Widget Selector'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIndividualWidgetButtons(BuildContext context) {
    final widgets = [
      (WorkflowWidgetType.processingStatus, 'Processing Status', Icons.trending_up, Colors.blue),
      (WorkflowWidgetType.analyticsDashboard, 'Analytics Dashboard', Icons.dashboard, Colors.green),
      (WorkflowWidgetType.healthMonitoring, 'System Health', Icons.favorite, Colors.red),
    ];

    return Column(
      children: widgets.map((widget) {
        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: Icon(widget.$3, color: widget.$4),
            title: Text(widget.$2),
            subtitle: Text('Open ${widget.$2.toLowerCase()} widget'),
            trailing: const Icon(Icons.arrow_forward_ios),
            onTap: () {
              WorkflowWidgetNavigation.navigateToWidget(context, widget.$1);
            },
          ),
        );
      }).toList(),
    );
  }

  Widget _buildDashboardButton(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Workflow Dashboard',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'View all workflow widgets in a single dashboard',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: () {
                    WorkflowWidgetNavigation.navigateToDashboard(context);
                  },
                  icon: const Icon(Icons.dashboard),
                  label: const Text('Full Dashboard'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: () {
                    WorkflowWidgetNavigation.navigateToDashboard(
                      context,
                      visibleWidgets: [
                        WorkflowWidgetType.processingStatus,
                        WorkflowWidgetType.healthMonitoring,
                      ],
                    );
                  },
                  icon: const Icon(Icons.view_module),
                  label: const Text('Custom Dashboard'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.grey[100],
                    foregroundColor: Colors.grey[700],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAuthenticationTesting(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Authentication Testing',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Test widget behavior with different authentication states',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            Consumer(
              builder: (context, ref, child) {
                final isAuthenticated = ref.watch(authenticationStatusProvider);
                final userUuid = ref.watch(workflowCurrentUserProvider);
                
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isAuthenticated ? Icons.check_circle : Icons.cancel,
                          color: isAuthenticated ? Colors.green : Colors.red,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          isAuthenticated ? 'Authenticated' : 'Not Authenticated',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: isAuthenticated ? Colors.green : Colors.red,
                          ),
                        ),
                      ],
                    ),
                    if (isAuthenticated && userUuid != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        'User UUID: ${userUuid.substring(0, 8)}...',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmbeddedWidgetsDemo(BuildContext context) {
    return Column(
      children: [
        // Embedded Health Monitoring (doesn't require auth)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.favorite, color: Colors.red),
                    const SizedBox(width: 8),
                    Text(
                      'System Health (Embedded)',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SizedBox(
                  height: 300,
                  child: WorkflowWidgetRegistry.buildWidget(
                    WorkflowWidgetType.healthMonitoring,
                    wrapWithAuth: false, // Health monitoring doesn't require auth
                  ),
                ),
              ],
            ),
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Embedded Processing Status (requires auth)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.trending_up, color: Colors.blue),
                    const SizedBox(width: 8),
                    Text(
                      'Processing Status (Embedded)',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SizedBox(
                  height: 300,
                  child: AuthenticatedWorkflowBuilder(
                    builder: (context, apiClient, userUuid) {
                      return WorkflowWidgetRegistry.buildWidget(
                        WorkflowWidgetType.processingStatus,
                        userUuid: userUuid,
                        wrapWithAuth: false, // Already wrapped in AuthenticatedWorkflowBuilder
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// Simple usage examples for different scenarios
class WorkflowWidgetUsageExamples {
  /// Example 1: Simple navigation to a widget
  static void navigateToProcessingStatus(BuildContext context) {
    WorkflowWidgetNavigation.navigateToWidget(
      context,
      WorkflowWidgetType.processingStatus,
    );
  }

  /// Example 2: Embedding a widget with authentication
  static Widget buildAuthenticatedWidget(WorkflowWidgetType type) {
    return AuthenticatedWorkflowWrapper(
      requiresAuth: true,
      child: WorkflowWidgetRegistry.buildWidget(type),
    );
  }

  /// Example 3: Building a custom dashboard with specific widgets
  static Widget buildCustomDashboard() {
    return WorkflowDashboard(
      visibleWidgets: [
        WorkflowWidgetType.processingStatus,
        WorkflowWidgetType.healthMonitoring,
      ],
      allowToggle: true,
    );
  }

  /// Example 4: Using the workflow builder pattern
  static Widget buildWithWorkflowBuilder() {
    return AuthenticatedWorkflowBuilder(
      builder: (context, apiClient, userUuid) {
        return Column(
          children: [
            WorkflowWidgetRegistry.buildWidget(
              WorkflowWidgetType.processingStatus,
              userUuid: userUuid,
              wrapWithAuth: false,
            ),
            WorkflowWidgetRegistry.buildWidget(
              WorkflowWidgetType.analyticsDashboard,
              userUuid: userUuid,
              wrapWithAuth: false,
            ),
          ],
        );
      },
      loadingBuilder: (context) => const CircularProgressIndicator(),
      unauthenticatedBuilder: (context) => const Text('Please log in'),
    );
  }
}
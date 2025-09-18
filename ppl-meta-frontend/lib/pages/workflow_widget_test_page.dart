import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/workflow/authenticated_workflow_wrapper.dart';
import '../widgets/workflow/processing_status_widget.dart';
import '../widgets/workflow/analytics_dashboard_widget.dart';
import '../widgets/workflow/health_monitoring_widget.dart';

/// Test page for our new workflow widget endpoints
class WorkflowWidgetTestPage extends ConsumerWidget {
  const WorkflowWidgetTestPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Workflow Widget Test'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: const SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'New Workflow Widget Endpoints Test',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 24),
            
            // Health Monitoring Widget
            _HealthMonitoringSection(),
            SizedBox(height: 32),
            
            // Analytics Dashboard Widget
            _AnalyticsDashboardSection(),
            SizedBox(height: 32),
            
            // Processing Status Widget
            _ProcessingStatusSection(),
          ],
        ),
      ),
    );
  }
}

class _HealthMonitoringSection extends StatelessWidget {
  const _HealthMonitoringSection();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.favorite, color: Colors.red),
                const SizedBox(width: 8),
                Text(
                  'System Health Monitoring',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Testing new authenticated health endpoint: /api/v1/processing-status/health',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            const SizedBox(
              height: 300,
              child: HealthMonitoringWidget(
                showAlerts: true,
                autoRefresh: false, // Disable auto-refresh for testing
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AnalyticsDashboardSection extends StatelessWidget {
  const _AnalyticsDashboardSection();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics, color: Colors.blue),
                const SizedBox(width: 8),
                Text(
                  'Analytics Dashboard',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Testing new analytics endpoint: /api/v1/processing-status/test-uuid/analytics',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            const SizedBox(
              height: 400,
              child: AnalyticsDashboardWidget(
                mediaUuid: 'test-uuid',
                showRecommendations: true,
                autoRefresh: false, // Disable auto-refresh for testing
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProcessingStatusSection extends StatelessWidget {
  const _ProcessingStatusSection();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.trending_up, color: Colors.green),
                const SizedBox(width: 8),
                Text(
                  'Processing Status',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Testing new widget endpoint: /api/v1/processing-status/test-uuid/widget',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            const SizedBox(
              height: 300,
              child: ProcessingStatusWidget(
                mediaUuid: 'test-uuid',
                showProgress: true,
                autoRefresh: false, // Disable auto-refresh for testing
              ),
            ),
          ],
        ),
      ),
    );
  }
}
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/workflow_providers.dart';

/// Workflow management dashboard for monitoring and controlling workflow executions
/// Provides real-time status, execution history, and manual workflow triggers
class WorkflowDashboard extends ConsumerStatefulWidget {
  const WorkflowDashboard({Key? key}) : super(key: key);

  @override
  ConsumerState<WorkflowDashboard> createState() => _WorkflowDashboardState();
}

class _WorkflowDashboardState extends ConsumerState<WorkflowDashboard> 
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Workflow Management'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard), text: 'Active'),
            Tab(icon: Icon(Icons.history), text: 'History'),
            Tab(icon: Icon(Icons.library_books), text: 'Templates'),
          ],
        ),
        actions: [
          IconButton(
            onPressed: () => _showCreateWorkflowDialog(),
            icon: const Icon(Icons.add),
            tooltip: 'Create Workflow',
          ),
          IconButton(
            onPressed: () => _refreshData(),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildActiveWorkflowsTab(),
          _buildHistoryTab(),
          _buildTemplatesTab(),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showQuickStartDialog(),
        icon: const Icon(Icons.play_arrow),
        label: const Text('Quick Start'),
      ),
    );
  }

  Widget _buildActiveWorkflowsTab() {
    final activeWorkflows = ref.watch(activeWorkflowsProvider);
    final workflowStats = ref.watch(workflowStatsProvider);

    return Column(
      children: [
        // Stats Overview
        Container(
          padding: const EdgeInsets.all(16),
          child: workflowStats.when(
            data: (stats) => Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    title: 'Running',
                    value: '${stats.runningCount}',
                    icon: Icons.play_circle,
                    color: Colors.blue,
                  ),
                ),
                Expanded(
                  child: _buildStatCard(
                    title: 'Queued',
                    value: '${stats.queuedCount}',
                    icon: Icons.queue,
                    color: Colors.orange,
                  ),
                ),
                Expanded(
                  child: _buildStatCard(
                    title: 'Completed Today',
                    value: '${stats.completedTodayCount}',
                    icon: Icons.check_circle,
                    color: Colors.green,
                  ),
                ),
                Expanded(
                  child: _buildStatCard(
                    title: 'Success Rate',
                    value: '${stats.successRate.toStringAsFixed(1)}%',
                    icon: Icons.trending_up,
                    color: stats.successRate > 90 ? Colors.green : Colors.orange,
                  ),
                ),
              ],
            ),
            loading: () => const SizedBox(
              height: 100,
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (error, stack) => Container(
              height: 100,
              padding: const EdgeInsets.all(16),
              child: Center(child: Text('Error loading stats: $error')),
            ),
          ),
        ),

        // Active Workflows List
        Expanded(
          child: activeWorkflows.when(
            data: (workflows) => workflows.isEmpty
                ? _buildEmptyActiveState()
                : RefreshIndicator(
                    onRefresh: () async {
                      ref.refresh(activeWorkflowsProvider);
                    },
                    child: ListView.separated(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemCount: workflows.length,
                      separatorBuilder: (context, index) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final workflow = workflows[index];
                        return ActiveWorkflowCard(
                          workflow: workflow,
                          onCancel: () => _cancelWorkflow(workflow.id),
                          onPause: () => _pauseWorkflow(workflow.id),
                          onResume: () => _resumeWorkflow(workflow.id),
                          onViewDetails: () => _showWorkflowDetails(workflow),
                        );
                      },
                    ),
                  ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error, size: 64, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error loading workflows: $error'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => ref.refresh(activeWorkflowsProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildHistoryTab() {
    final workflowHistory = ref.watch(workflowHistoryProvider);

    return Column(
      children: [
        // History Filters
        Container(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<WorkflowHistoryTimeRange>(
                  decoration: const InputDecoration(
                    labelText: 'Time Range',
                    border: OutlineInputBorder(),
                  ),
                  value: ref.watch(historyFilterProvider).timeRange,
                  items: WorkflowHistoryTimeRange.values.map((range) {
                    return DropdownMenuItem(
                      value: range,
                      child: Text(range.displayName),
                    );
                  }).toList(),
                  onChanged: (range) {
                    if (range != null) {
                      ref.read(historyFilterProvider.notifier).setTimeRange(range);
                    }
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: DropdownButtonFormField<WorkflowStatus?>(
                  decoration: const InputDecoration(
                    labelText: 'Status',
                    border: OutlineInputBorder(),
                  ),
                  value: ref.watch(historyFilterProvider).status,
                  items: [
                    const DropdownMenuItem(
                      value: null,
                      child: Text('All Statuses'),
                    ),
                    ...WorkflowStatus.values.map((status) {
                      return DropdownMenuItem(
                        value: status,
                        child: Row(
                          children: [
                            Icon(
                              _getWorkflowStatusIcon(status),
                              size: 16,
                              color: _getWorkflowStatusColor(status),
                            ),
                            const SizedBox(width: 8),
                            Text(status.displayName),
                          ],
                        ),
                      );
                    }),
                  ],
                  onChanged: (status) {
                    ref.read(historyFilterProvider.notifier).setStatus(status);
                  },
                ),
              ),
            ],
          ),
        ),

        // History List
        Expanded(
          child: workflowHistory.when(
            data: (history) => history.isEmpty
                ? _buildEmptyHistoryState()
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: history.length,
                    separatorBuilder: (context, index) => const Divider(),
                    itemBuilder: (context, index) {
                      final execution = history[index];
                      return WorkflowHistoryTile(
                        execution: execution,
                        onTap: () => _showExecutionDetails(execution),
                        onRerun: () => _rerunWorkflow(execution),
                      );
                    },
                  ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error, size: 64, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error loading history: $error'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => ref.refresh(workflowHistoryProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTemplatesTab() {
    final workflowTemplates = ref.watch(workflowTemplatesProvider);

    return Column(
      children: [
        // Template Categories
        Container(
          padding: const EdgeInsets.all(16),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: WorkflowCategory.values.map((category) {
                final isSelected = ref.watch(templateFilterProvider).category == category;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(category.displayName),
                    selected: isSelected,
                    onSelected: (selected) {
                      ref.read(templateFilterProvider.notifier).setCategory(
                        selected ? category : null,
                      );
                    },
                  ),
                );
              }).toList(),
            ),
          ),
        ),

        // Templates Grid
        Expanded(
          child: workflowTemplates.when(
            data: (templates) => templates.isEmpty
                ? _buildEmptyTemplatesState()
                : GridView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 16,
                      mainAxisSpacing: 16,
                      childAspectRatio: 1.2,
                    ),
                    itemCount: templates.length,
                    itemBuilder: (context, index) {
                      final template = templates[index];
                      return WorkflowTemplateCard(
                        template: template,
                        onStart: () => _startFromTemplate(template),
                        onEdit: () => _editTemplate(template),
                        onDuplicate: () => _duplicateTemplate(template),
                      );
                    },
                  ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error, size: 64, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error loading templates: $error'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => ref.refresh(workflowTemplatesProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              title,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyActiveState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.play_circle_outline,
            size: 64,
            color: Theme.of(context).colorScheme.outline,
          ),
          const SizedBox(height: 16),
          Text(
            'No active workflows',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Start a workflow to see it here',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.outline,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => _showQuickStartDialog(),
            icon: const Icon(Icons.play_arrow),
            label: const Text('Start Workflow'),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyHistoryState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.history,
            size: 64,
            color: Theme.of(context).colorScheme.outline,
          ),
          const SizedBox(height: 16),
          Text(
            'No workflow history',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Completed workflows will appear here',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.outline,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyTemplatesState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.library_books_outlined,
            size: 64,
            color: Theme.of(context).colorScheme.outline,
          ),
          const SizedBox(height: 16),
          Text(
            'No workflow templates',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Create templates to reuse workflows',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.outline,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => _showCreateTemplateDialog(),
            icon: const Icon(Icons.add),
            label: const Text('Create Template'),
          ),
        ],
      ),
    );
  }

  IconData _getWorkflowStatusIcon(WorkflowStatus status) {
    switch (status) {
      case WorkflowStatus.running:
        return Icons.play_circle;
      case WorkflowStatus.completed:
        return Icons.check_circle;
      case WorkflowStatus.failed:
        return Icons.error;
      case WorkflowStatus.cancelled:
        return Icons.cancel;
      case WorkflowStatus.paused:
        return Icons.pause_circle;
      case WorkflowStatus.queued:
        return Icons.queue;
    }
  }

  Color _getWorkflowStatusColor(WorkflowStatus status) {
    switch (status) {
      case WorkflowStatus.running:
        return Colors.blue;
      case WorkflowStatus.completed:
        return Colors.green;
      case WorkflowStatus.failed:
        return Colors.red;
      case WorkflowStatus.cancelled:
        return Colors.orange;
      case WorkflowStatus.paused:
        return Colors.yellow[700]!;
      case WorkflowStatus.queued:
        return Colors.purple;
    }
  }

  void _showCreateWorkflowDialog() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => WorkflowBuilder(
          onSaved: (workflow) {
            ref.read(workflowTemplatesProvider.notifier).addTemplate(workflow);
          },
        ),
      ),
    );
  }

  void _showQuickStartDialog() {
    showModalBottomSheet(
      context: context,
      builder: (context) => QuickStartWorkflowSheet(
        onWorkflowSelected: (workflowType) {
          _startQuickWorkflow(workflowType);
        },
      ),
    );
  }

  void _showCreateTemplateDialog() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => WorkflowTemplateBuilder(
          onSaved: (template) {
            ref.read(workflowTemplatesProvider.notifier).addTemplate(template);
          },
        ),
      ),
    );
  }

  void _showWorkflowDetails(ActiveWorkflow workflow) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => WorkflowDetailsScreen(workflowId: workflow.id),
      ),
    );
  }

  void _showExecutionDetails(WorkflowExecution execution) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => WorkflowExecutionDetailsScreen(executionId: execution.id),
      ),
    );
  }

  void _cancelWorkflow(String workflowId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Workflow'),
        content: const Text('Are you sure you want to cancel this workflow?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              ref.read(activeWorkflowsProvider.notifier).cancelWorkflow(workflowId);
              _showSnackBar('Workflow cancelled');
            },
            child: const Text('Yes, Cancel'),
          ),
        ],
      ),
    );
  }

  void _pauseWorkflow(String workflowId) {
    ref.read(activeWorkflowsProvider.notifier).pauseWorkflow(workflowId);
    _showSnackBar('Workflow paused');
  }

  void _resumeWorkflow(String workflowId) {
    ref.read(activeWorkflowsProvider.notifier).resumeWorkflow(workflowId);
    _showSnackBar('Workflow resumed');
  }

  void _startFromTemplate(WorkflowTemplate template) {
    ref.read(activeWorkflowsProvider.notifier).startFromTemplate(template.id);
    _showSnackBar('Workflow started from template');
  }

  void _editTemplate(WorkflowTemplate template) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => WorkflowTemplateBuilder(
          existingTemplate: template,
          onSaved: (updatedTemplate) {
            ref.read(workflowTemplatesProvider.notifier).updateTemplate(updatedTemplate);
          },
        ),
      ),
    );
  }

  void _duplicateTemplate(WorkflowTemplate template) {
    ref.read(workflowTemplatesProvider.notifier).duplicateTemplate(template.id);
    _showSnackBar('Template duplicated');
  }

  void _rerunWorkflow(WorkflowExecution execution) {
    ref.read(activeWorkflowsProvider.notifier).rerunWorkflow(execution.id);
    _showSnackBar('Workflow restarted');
  }

  void _startQuickWorkflow(QuickWorkflowType type) {
    ref.read(activeWorkflowsProvider.notifier).startQuickWorkflow(type);
    _showSnackBar('Quick workflow started');
  }

  void _refreshData() {
    ref.refresh(activeWorkflowsProvider);
    ref.refresh(workflowHistoryProvider);
    ref.refresh(workflowTemplatesProvider);
    ref.refresh(workflowStatsProvider);
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}

// Supporting classes and widgets would be implemented in separate files:
// - ActiveWorkflowCard
// - WorkflowHistoryTile
// - WorkflowTemplateCard
// - QuickStartWorkflowSheet
// - WorkflowBuilder
// - WorkflowTemplateBuilder
// - WorkflowDetailsScreen
// - WorkflowExecutionDetailsScreen
// - Related data classes and enums
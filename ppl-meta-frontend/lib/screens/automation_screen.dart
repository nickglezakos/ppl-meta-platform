import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../widgets/custom_app_bar.dart';
import '../providers/automation_providers.dart';
import '../models/automation_models.dart';
import '../widgets/workflow_widgets/workflow_widgets.dart';

/// Enhanced Automation Screen integrating Phase 4 automation functionality
/// with existing app structure and design patterns
class AutomationScreen extends ConsumerStatefulWidget {
  const AutomationScreen({super.key});

  @override
  ConsumerState<AutomationScreen> createState() => _AutomationScreenState();
}

class _AutomationScreenState extends ConsumerState<AutomationScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isRefreshing = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Load initial data after dependencies are available
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadInitialData();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }
  
  Future<void> _loadInitialData() async {
    try {
      // Load automation data from providers
      ref.invalidate(automationRulesProvider);
      ref.invalidate(automationExecutionHistoryProvider);
      ref.invalidate(automationMetricsProvider);
    } catch (e) {
      debugPrint('Error loading automation data: $e');
    }
  }
  
  Future<void> _refreshData() async {
    if (_isRefreshing) return;
    
    setState(() => _isRefreshing = true);
    
    try {
      await Future.wait([
        Future(() {
          ref.invalidate(automationRulesProvider);
          return ref.read(automationRulesProvider.future);
        }).catchError((_) => []),
        Future(() {
          ref.invalidate(automationExecutionHistoryProvider);
          return ref.read(automationExecutionHistoryProvider.future);
        }).catchError((_) => []),
        Future(() {
          ref.invalidate(automationMetricsProvider);
          return ref.read(automationMetricsProvider.future);
        }).catchError((_) => null),
      ]);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Automation data refreshed'),
            backgroundColor: AppColors.success,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to refresh: ${e.toString()}'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isRefreshing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: CustomAppBar(
        title: 'Automation Engine',
        showBackButton: true,
        showHomeButton: true,
        actions: [
          IconButton(
            icon: _isRefreshing
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation(AppColors.textPrimary),
                    ),
                  )
                : const Icon(Icons.refresh),
            onPressed: _isRefreshing ? null : _refreshData,
            tooltip: 'Refresh Data',
          ),
          IconButton(
            onPressed: () => _showCreateRuleDialog(),
            icon: const Icon(Icons.add),
            tooltip: 'Create new rule',
          ),
        ],
      ),
      body: Column(
        children: [
          // Tab bar below the navigation bar
          Container(
            color: AppColors.surface,
            child: TabBar(
              controller: _tabController,
              indicatorColor: AppColors.primary,
              labelColor: AppColors.textPrimary,
              unselectedLabelColor: AppColors.textSecondary,
              tabs: const [
                Tab(icon: Icon(Icons.dashboard), text: 'Dashboard'),
                Tab(icon: Icon(Icons.rule), text: 'Rules'),
                Tab(icon: Icon(Icons.history), text: 'History'),
              ],
            ),
          ),
          // Tab content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildDashboardTab(),
                _buildRulesTab(),
                _buildHistoryTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildDashboardTab() {
    return RefreshIndicator(
      onRefresh: _refreshData,
      color: AppColors.primary,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Automation overview
            _buildAutomationOverview(),
            
            const SizedBox(height: 24),
            
            // Quick stats
            _buildQuickStats(),
            
            const SizedBox(height: 24),
            
            // Active rules summary
            _buildActiveRulesSummary(),
            
            const SizedBox(height: 24),
            
            // Recent executions
            _buildRecentExecutions(),
            
            const SizedBox(height: 80), // Bottom padding
          ],
        ),
      ),
    );
  }
  
  Widget _buildRulesTab() {
    return Consumer(
      builder: (context, ref, child) {
        final rules = ref.watch(automationRulesProvider);
        
        return RefreshIndicator(
          onRefresh: _refreshData,
          color: AppColors.primary,
          child: rules.when(
            data: (rulesList) => _buildRulesList(rulesList),
            loading: () => const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation(AppColors.primary),
              ),
            ),
            error: (error, _) => _buildErrorState('Failed to load rules: $error'),
          ),
        );
      },
    );
  }
  
  Widget _buildHistoryTab() {
    return Consumer(
      builder: (context, ref, child) {
        final history = ref.watch(automationExecutionHistoryProvider);
        
        return RefreshIndicator(
          onRefresh: _refreshData,
          color: AppColors.primary,
          child: history.when(
            data: (executions) => _buildHistoryList(executions),
            loading: () => const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation(AppColors.primary),
              ),
            ),
            error: (error, _) => _buildErrorState('Failed to load history: $error'),
          ),
        );
      },
    );
  }

  void _showCreateRuleDialog() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        child: Container(
          padding: const EdgeInsets.all(24),
          constraints: const BoxConstraints(maxWidth: 400),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Create Automation Rule',
                style: AppTextStyles.h5.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Automation rules allow you to automatically trigger actions based on specific conditions like face detection events, camera activities, or system events.',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(
                      'Cancel',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                      // TODO: Navigate to rule builder
                      _showFeatureComingSoon();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                    ),
                    child: const Text('Create Rule'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  void _showFeatureComingSoon() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Rule builder coming soon! Backend automation APIs in development.'),
        backgroundColor: AppColors.warning,
        duration: Duration(seconds: 3),
      ),
    );
  }
  
  void _refreshMetrics() {
    // Refresh the automation metrics provider
    ref.invalidate(automationMetricsProvider);
  }

  void _refreshAllData() {
    ref.invalidate(automationMetricsProvider);
    ref.invalidate(automationRulesProvider);
    ref.invalidate(automationExecutionHistoryProvider);
  }
  
  Widget _buildAutomationOverview() {
    return Consumer(
      builder: (context, ref, child) {
        final metrics = ref.watch(automationMetricsProvider);
        
        return Column(
          children: [
            // Main automation status card
            Card(
              color: AppColors.surfaceVariant,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: const BorderSide(color: AppColors.border),
              ),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Icon(
                            Icons.smart_toy,
                            color: AppColors.primary,
                            size: 24,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Automation Engine Status',
                                style: AppTextStyles.h6.copyWith(
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              Text(
                                'Smart automation for your PPL Meta platform',
                                style: AppTextStyles.bodyMedium.copyWith(
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppColors.success.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(
                                  color: AppColors.success,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                'Active',
                                style: AppTextStyles.bodySmall.copyWith(
                                  color: AppColors.success,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Automation engine progress visualization
            metrics.when(
              data: (data) {
                if (data == null) {
                  return WorkflowStatusComponent(
                    status: WorkflowStatus.failed,
                    title: 'Automation Metrics Error',
                    subtitle: 'No metrics available',
                    message: 'Unable to load automation metrics',
                    onAction: () => _refreshMetrics(),
                    actionLabel: 'Retry',
                  );
                }
                
                final totalRules = data.totalRules;
                final activeRules = data.activeRules;
                final progress = totalRules > 0 ? activeRules / totalRules : 0.0;
                
                return WorkflowProgressVisualization(
                  progress: progress,
                  title: 'Automation Rules Active',
                  subtitle: '$activeRules of $totalRules rules running',
                  type: WorkflowProgressType.linear,
                  primaryColor: AppColors.primary,
                );
              },
              loading: () => const WorkflowProgressVisualization(
                progress: 0.0,
                title: 'Loading automation status...',
                type: WorkflowProgressType.linear,
              ),
              error: (_, __) => const WorkflowProgressVisualization(
                progress: 0.0,
                title: 'Unable to load automation status',
                type: WorkflowProgressType.linear,
              ),
            ),
          ],
        );
      },
    );
  }
  
  Widget _buildQuickStats() {
    return Consumer(
      builder: (context, ref, child) {
        final metrics = ref.watch(automationMetricsProvider);
        
        return Row(
          children: [
            Expanded(
              child: _buildStatCard(
                title: 'Active Rules',
                value: metrics.when(
                  data: (data) => data.activeRulesCount.toString(),
                  loading: () => '...',
                  error: (_, __) => '0',
                ),
                icon: Icons.rule,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildStatCard(
                title: 'Executions Today',
                value: metrics.when(
                  data: (data) => data.executionsToday.toString(),
                  loading: () => '...',
                  error: (_, __) => '0',
                ),
                icon: Icons.play_arrow,
                color: AppColors.success,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildStatCard(
                title: 'Success Rate',
                value: metrics.when(
                  data: (data) => '${(data.successRate * 100).toStringAsFixed(0)}%',
                  loading: () => '...',
                  error: (_, __) => '0%',
                ),
                icon: Icons.check_circle,
                color: AppColors.warning,
              ),
            ),
          ],
        );
      },
    );
  }
  
  Widget _buildStatCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.h4.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            title,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
  
  Widget _buildActiveRulesSummary() {
    return Consumer(
      builder: (context, ref, child) {
        final rules = ref.watch(automationRulesProvider);
        
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Active Rules Status',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            rules.when(
              data: (rulesList) {
                if (rulesList == null || rulesList.isEmpty) {
                  return _buildEmptyState(
                    icon: Icons.rule,
                    title: 'No Rules Created',
                    subtitle: 'Create your first automation rule to get started',
                    actionLabel: 'Create Rule',
                    onAction: _showCreateRuleDialog,
                  );
                }
                
                // Convert rules to workflow status components
                final statusData = rulesList.take(4).map((rule) {
                  WorkflowStatus status;
                  String subtitle;
                  String? message;
                  
                  if (rule.isEnabled) {
                    status = WorkflowStatus.running;
                    subtitle = 'Active and monitoring';
                    message = 'Rule is actively monitoring for trigger conditions';
                  } else {
                    status = WorkflowStatus.paused;
                    subtitle = 'Disabled';
                    message = 'Rule is currently disabled and not monitoring';
                  }
                  
                  return WorkflowStatusData(
                    status: status,
                    title: rule.name,
                    subtitle: subtitle,
                    message: message,
                    onAction: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('${rule.isEnabled ? 'Paused' : 'Activated'} rule: ${rule.name}')),
                      );
                    },
                    actionLabel: rule.isEnabled ? 'Pause' : 'Activate',
                  );
                }).toList();
                
                return WorkflowStatusGrid(
                  statuses: statusData,
                  crossAxisCount: 2,
                  childAspectRatio: 1.3,
                  padding: EdgeInsets.zero,
                );
              },
              loading: () => const Center(
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation(AppColors.primary),
                ),
              ),
              error: (error, _) => WorkflowStatusComponent(
                status: WorkflowStatus.failed,
                title: 'Rules Load Error',
                subtitle: 'Unable to load automation rules',
                message: 'Failed to load automation rules from the server',
                onAction: () => _refreshAllData(),
                actionLabel: 'Retry',
              ),
            ),
          ],
        );
      },
    );
  }
  
  Widget _buildRecentExecutions() {
    return Consumer(
      builder: (context, ref, child) {
        final executionHistory = ref.watch(automationExecutionHistoryProvider);
        
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recent Executions Timeline',
              style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            executionHistory.when(
              data: (executions) {
                if (executions == null || executions.isEmpty) {
                  return _buildEmptyState(
                    icon: Icons.history,
                    title: 'No Recent Executions',
                    subtitle: 'Automation executions will appear here once rules are active',
                  );
                }
                
                // Convert executions to timeline data
                final timelineData = executions.take(5).map((execution) {
                  WorkflowTimelineEventType eventType;
                  
                  switch (execution.status) {
                    case 'completed':
                      eventType = WorkflowTimelineEventType.completed;
                      break;
                    case 'failed':
                      eventType = WorkflowTimelineEventType.failed;
                      break;
                    case 'running':
                      eventType = WorkflowTimelineEventType.started;
                      break;
                    default:
                      eventType = WorkflowTimelineEventType.started;
                  }
                  
                  return WorkflowTimelineData(
                    id: execution.id,
                    title: execution.ruleName,
                    description: 'Automation rule executed',
                    timestamp: execution.executedAt,
                    type: eventType,
                    metadata: {
                      'Status': execution.status,
                      'Rule': execution.ruleName,
                      'Trigger': execution.trigger,
                      'Result': execution.result ?? 'No result',
                      'Duration': execution.duration?.toString() ?? 'Unknown',
                    },
                  );
                }).toList();
                
                return Container(
                  height: 300,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: WorkflowExecutionTimeline(
                    events: timelineData,
                    isCompact: true,
                    showTime: true,
                    showDuration: true,
                    onEventTapped: (event) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Execution ${event.id} details')),
                      );
                    },
                  ),
                );
              },
              loading: () => Container(
                height: 200,
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: const Center(
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation(AppColors.primary),
                  ),
                ),
              ),
              error: (error, _) => Container(
                height: 200,
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error, color: AppColors.error, size: 48),
                      SizedBox(height: 8),
                      Text('Failed to load executions', style: TextStyle(color: AppColors.error)),
                    ],
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
  
  Widget _buildRulesList(List<dynamic> rules) {
    if (rules.isEmpty) {
      return _buildEmptyState(
        icon: Icons.rule,
        title: 'No Automation Rules',
        subtitle: 'Create your first automation rule to start automating your workflows',
        actionLabel: 'Create First Rule',
        onAction: _showCreateRuleDialog,
      );
    }
    
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: rules.length,
      itemBuilder: (context, index) => _buildRulePreview(rules[index]),
    );
  }
  
  Widget _buildHistoryList(List<dynamic> executions) {
    if (executions.isEmpty) {
      return _buildEmptyState(
        icon: Icons.history,
        title: 'No Execution History',
        subtitle: 'Automation execution history will appear here',
      );
    }
    
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: executions.length,
      itemBuilder: (context, index) => _buildExecutionItem(executions[index]),
    );
  }
  
  Widget _buildRulePreview(dynamic rule) {
    return Card(
      color: AppColors.surfaceVariant,
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.border),
      ),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            Icons.rule,
            color: AppColors.primary,
            size: 20,
          ),
        ),
        title: Text(
          'Sample Automation Rule',
          style: AppTextStyles.bodyLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: Text(
          'Trigger: Face detected | Action: Send notification',
          style: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: AppColors.success.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            'Active',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.success,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildExecutionItem(dynamic execution) {
    return Card(
      color: AppColors.surfaceVariant,
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.border),
      ),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.success.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            Icons.check_circle,
            color: AppColors.success,
            size: 20,
          ),
        ),
        title: Text(
          'Sample Execution',
          style: AppTextStyles.bodyLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: Text(
          'Rule executed successfully',
          style: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        trailing: Text(
          'Just now',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textTertiary,
          ),
        ),
      ),
    );
  }
  
  Widget _buildEmptyState({
    required IconData icon,
    required String title,
    required String subtitle,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.border),
              ),
              child: Icon(
                icon,
                color: AppColors.textSecondary,
                size: 48,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              title,
              style: AppTextStyles.h6.copyWith(
                color: AppColors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.add),
                label: Text(actionLabel),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildErrorState(String message) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              color: AppColors.error,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Error',
              style: AppTextStyles.h6.copyWith(
                color: AppColors.error,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _refreshData,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildErrorCard(String message) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(
            Icons.error_outline,
            color: AppColors.error,
            size: 24,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.error,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Dashboard tab showing automation overview and statistics
class AutomationDashboardTab extends ConsumerWidget {
  const AutomationDashboardTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Automation Dashboard',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 16),
          Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Overview',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Text('Welcome to the PPL Meta Automation Engine!'),
                  SizedBox(height: 8),
                  Text('Here you can create and manage automation rules for:'),
                  SizedBox(height: 8),
                  Text('• Face detection workflows'),
                  Text('• Camera recording automation'),
                  Text('• Scheduled processing tasks'),
                  Text('• Event-driven workflows'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Rules tab showing all automation rules
class AutomationRulesTab extends ConsumerWidget {
  const AutomationRulesTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Automation Rules',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 16),
          Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'No Rules Created Yet',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Text('Create your first automation rule to get started.'),
                  SizedBox(height: 8),
                  Text('Available rule types:'),
                  SizedBox(height: 8),
                  Text('• Time-based triggers'),
                  Text('• Camera event triggers'),
                  Text('• Face detection triggers'),
                  Text('• Custom workflow triggers'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// History tab showing automation execution history
class AutomationHistoryTab extends ConsumerWidget {
  const AutomationHistoryTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Execution History',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 16),
          Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'No Executions Yet',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Text('Automation execution history will appear here.'),
                  SizedBox(height: 8),
                  Text('You will see:'),
                  SizedBox(height: 8),
                  Text('• Rule execution timestamps'),
                  Text('• Success/failure status'),
                  Text('• Execution duration'),
                  Text('• Error messages if any'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
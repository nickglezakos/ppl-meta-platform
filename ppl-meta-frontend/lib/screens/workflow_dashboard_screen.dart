import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../models/face_detection_models.dart';
import '../providers/workflow_providers.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/workflow/workflow_performance_metrics_widget.dart';
import '../widgets/workflow/workflow_sessions_list_widget.dart';
import '../widgets/workflow/workflow_processed_videos_widget.dart';
import '../widgets/workflow/workflow_analytics_widget.dart';
import '../widgets/workflow/processing_status_widget.dart';
import '../widgets/workflow/health_monitoring_widget.dart';
import '../widgets/workflow/monitoring_summary_widget.dart';
import '../widgets/workflow_widgets/workflow_widgets.dart';

/// Monitoring dashboard for system and workflow health
/// Displays real-time metrics and system status
class WorkflowDashboardScreen extends ConsumerStatefulWidget {
  const WorkflowDashboardScreen({super.key});

  @override
  ConsumerState<WorkflowDashboardScreen> createState() => 
      _WorkflowDashboardScreenState();
}

class _WorkflowDashboardScreenState extends ConsumerState<WorkflowDashboardScreen> {
  bool _isRefreshing = false;
  
  @override
  void initState() {
    super.initState();
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
    super.dispose();
  }
  
  Future<void> _loadInitialData() async {
    // Trigger initial data loading for all providers
    try {
      // TODO: Re-enable once backend endpoints are fixed
      // ref.invalidate(workflowPerformanceMetricsProvider);
      // ref.invalidate(allActiveSessionsProvider);
      // ref.invalidate(allProcessedVideosProvider);
      
      // Preload all tabs data
      // await Future.wait([
      //   ref.read(workflowPerformanceMetricsProvider.future).catchError((_) => null),
      //   ref.read(allActiveSessionsProvider.future).catchError((_) => []),
      //   ref.read(allProcessedVideosProvider.future).catchError((_) => []),
      // ]);
      
      debugPrint('Initial data loading skipped - using new widget APIs');
    } catch (e) {
      debugPrint('Initial data loading completed with some errors: $e');
    }
  }
  
  Future<void> _refreshAllData() async {
    if (_isRefreshing) return;
    
    setState(() => _isRefreshing = true);
    
    try {
      // TODO: Re-enable once backend endpoints are fixed
      // Refresh all data sources in parallel
      // await Future.wait([
      //   Future(() {
      //     ref.invalidate(workflowPerformanceMetricsProvider);
      //     return ref.read(workflowPerformanceMetricsProvider.future);
      //   }).catchError((_) => null),
      //   Future(() {
      //     ref.invalidate(allActiveSessionsProvider);
      //     return ref.read(allActiveSessionsProvider.future);
      //   }).catchError((_) => []),
      //   Future(() {
      //     ref.invalidate(allProcessedVideosProvider);
      //     return ref.read(allProcessedVideosProvider.future);
      //   }).catchError((_) => []),
      // ]);
      
      // Simulate refresh delay
      await Future.delayed(const Duration(milliseconds: 500));
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('New workflow widgets refreshed'),
            backgroundColor: AppColors.success,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      debugPrint('Error refreshing dashboard data: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to refresh data: ${e.toString()}'),
            backgroundColor: AppColors.error,
            duration: const Duration(seconds: 3),
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
      appBar: _buildAppBar(),
      body: RefreshIndicator(
        onRefresh: _refreshAllData,
        color: AppColors.primary,
        backgroundColor: AppColors.surface,
        child: const MonitoringSummaryWidget(),
      ),
    );
  }
  
  PreferredSizeWidget _buildAppBar() {
    return CustomAppBar(
      title: 'Monitoring Dashboard',
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
          onPressed: _isRefreshing ? null : _refreshAllData,
          tooltip: 'Refresh Data',
        ),
      ],
    );
  }
}
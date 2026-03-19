import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';

// =============================================================================
// MONITORING DASHBOARD PROVIDERS
// =============================================================================
// 
// Providers for the unified monitoring dashboard (formerly "Workflows").
// Connects to optimized backend summary endpoints with Redis caching.
//
// Performance Benefits:
// - 60-second cache TTL on backend
// - Lightweight summary payloads (~2KB vs 100KB+)
// - Manual refresh only (no auto-polling)
// - 90%+ reduction in API calls
//
// =============================================================================

/// Monitoring summary data model
class MonitoringSummary {
  final DateTime timestamp;
  final bool fromCache;
  final int cacheTtl;
  final LowLevelWorkflows lowLevelWorkflows;
  final HighLevelWorkflows highLevelWorkflows;
  final SystemHealth systemHealth;

  MonitoringSummary({
    required this.timestamp,
    required this.fromCache,
    required this.cacheTtl,
    required this.lowLevelWorkflows,
    required this.highLevelWorkflows,
    required this.systemHealth,
  });

  factory MonitoringSummary.fromJson(Map<String, dynamic> json) {
    return MonitoringSummary(
      timestamp: DateTime.parse(json['timestamp']),
      fromCache: json['from_cache'] ?? false,
      cacheTtl: json['cache_ttl'] ?? 60,
      lowLevelWorkflows: LowLevelWorkflows.fromJson(json['low_level_workflows'] ?? {}),
      highLevelWorkflows: HighLevelWorkflows.fromJson(json['high_level_workflows'] ?? {}),
      systemHealth: SystemHealth.fromJson(json['system_health'] ?? {}),
    );
  }
}

/// Low-level workflow metrics (face detection, method lifecycles)
class LowLevelWorkflows {
  final int activeSessions;
  final int completedWorkflows;
  final int failedWorkflows;
  final int completedMethods24h;
  final int failedMethods24h;
  final double avgProcessingTimeSeconds;
  final double successRate24h;

  LowLevelWorkflows({
    required this.activeSessions,
    required this.completedWorkflows,
    required this.failedWorkflows,
    required this.completedMethods24h,
    required this.failedMethods24h,
    required this.avgProcessingTimeSeconds,
    required this.successRate24h,
  });

  factory LowLevelWorkflows.fromJson(Map<String, dynamic> json) {
    return LowLevelWorkflows(
      activeSessions: json['active_sessions'] ?? 0,
      completedWorkflows: json['completed_workflows'] ?? 0,
      failedWorkflows: json['failed_workflows'] ?? 0,
      completedMethods24h: json['completed_methods_24h'] ?? 0,
      failedMethods24h: json['failed_methods_24h'] ?? 0,
      avgProcessingTimeSeconds: (json['avg_processing_time_seconds'] ?? 0.0).toDouble(),
      successRate24h: (json['success_rate_24h'] ?? 100.0).toDouble(),
    );
  }
}

/// High-level workflow metrics (MVR, individual tracking)
class HighLevelWorkflows {
  final int activeMvrSessions;
  final int totalIndividuals;
  final int personObjectsToday;
  final int crossVideoMatchesToday;
  final String? note;

  HighLevelWorkflows({
    required this.activeMvrSessions,
    required this.totalIndividuals,
    required this.personObjectsToday,
    required this.crossVideoMatchesToday,
    this.note,
  });

  factory HighLevelWorkflows.fromJson(Map<String, dynamic> json) {
    return HighLevelWorkflows(
      activeMvrSessions: json['active_mvr_sessions'] ?? 0,
      totalIndividuals: json['total_individuals'] ?? 0,
      personObjectsToday: json['person_objects_today'] ?? 0,
      crossVideoMatchesToday: json['cross_video_matches_today'] ?? 0,
      note: json['note'],
    );
  }
}

/// System health status
class SystemHealth {
  final String status; // healthy, degraded, unhealthy, error
  final String color; // green, orange, red
  final String message;
  final int stuckWorkflows;
  final int recentFailures;
  final DateTime? checkedAt;

  SystemHealth({
    required this.status,
    required this.color,
    required this.message,
    required this.stuckWorkflows,
    required this.recentFailures,
    this.checkedAt,
  });

  factory SystemHealth.fromJson(Map<String, dynamic> json) {
    return SystemHealth(
      status: json['status'] ?? 'unknown',
      color: json['color'] ?? 'grey',
      message: json['message'] ?? 'Status unavailable',
      stuckWorkflows: json['stuck_workflows'] ?? 0,
      recentFailures: json['recent_failures'] ?? 0,
      checkedAt: json['checked_at'] != null 
          ? DateTime.parse(json['checked_at'])
          : null,
    );
  }
}

/// Workflow item for pagination
class WorkflowItem {
  final int id;
  final String workflowId;
  final String workflowType;
  final String status;
  final String? userId;
  final DateTime? createdAt;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final int totalMediaCount;
  final int processedMediaCount;
  final int failedMediaCount;
  final String? errorMessage;

  WorkflowItem({
    required this.id,
    required this.workflowId,
    required this.workflowType,
    required this.status,
    this.userId,
    this.createdAt,
    this.startedAt,
    this.completedAt,
    required this.totalMediaCount,
    required this.processedMediaCount,
    required this.failedMediaCount,
    this.errorMessage,
  });

  factory WorkflowItem.fromJson(Map<String, dynamic> json) {
    return WorkflowItem(
      id: json['id'],
      workflowId: json['workflow_id'],
      workflowType: json['workflow_type'],
      status: json['status'],
      userId: json['user_id'],
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : null,
      startedAt: json['started_at'] != null ? DateTime.parse(json['started_at']) : null,
      completedAt: json['completed_at'] != null ? DateTime.parse(json['completed_at']) : null,
      totalMediaCount: json['total_media_count'] ?? 0,
      processedMediaCount: json['processed_media_count'] ?? 0,
      failedMediaCount: json['failed_media_count'] ?? 0,
      errorMessage: json['error_message'],
    );
  }
}

/// Pagination metadata
class PaginationInfo {
  final int page;
  final int limit;
  final int total;
  final int pages;

  PaginationInfo({
    required this.page,
    required this.limit,
    required this.total,
    required this.pages,
  });

  factory PaginationInfo.fromJson(Map<String, dynamic> json) {
    return PaginationInfo(
      page: json['page'] ?? 1,
      limit: json['limit'] ?? 20,
      total: json['total'] ?? 0,
      pages: json['pages'] ?? 0,
    );
  }
}

/// Paginated workflows response
class PaginatedWorkflows {
  final List<WorkflowItem> workflows;
  final PaginationInfo pagination;

  PaginatedWorkflows({
    required this.workflows,
    required this.pagination,
  });

  factory PaginatedWorkflows.fromJson(Map<String, dynamic> json) {
    return PaginatedWorkflows(
      workflows: (json['workflows'] as List<dynamic>?)
          ?.map((item) => WorkflowItem.fromJson(item))
          .toList() ?? [],
      pagination: PaginationInfo.fromJson(json['pagination'] ?? {}),
    );
  }
}

// =============================================================================
// PROVIDERS
// =============================================================================

/// Base URL for orchestrator service
final orchestratorBaseUrlProvider = Provider<String>((ref) {
  return 'http://localhost:8002'; // Direct to orchestrator, not gateway
});

/// Dio client for monitoring API
final monitoringDioProvider = Provider<Dio>((ref) {
  final dio = Dio();
  dio.options.baseUrl = ref.watch(orchestratorBaseUrlProvider);
  dio.options.connectTimeout = const Duration(seconds: 10);
  dio.options.receiveTimeout = const Duration(seconds: 10);
  
  // Add logging interceptor
  dio.interceptors.add(LogInterceptor(
    requestBody: false,
    responseBody: false,
  ));
  
  return dio;
});

/// Monitoring summary provider (cached 60s on backend)
final monitoringSummaryProvider = FutureProvider<MonitoringSummary>((ref) async {
  final dio = ref.watch(monitoringDioProvider);
  
  try {
    final response = await dio.get('/api/v1/monitoring/summary');
    return MonitoringSummary.fromJson(response.data);
  } catch (e) {
    throw Exception('Failed to load monitoring summary: $e');
  }
});

/// Paginated low-level workflows provider
final paginatedLowLevelWorkflowsProvider = FutureProvider.family<PaginatedWorkflows, Map<String, dynamic>>(
  (ref, params) async {
    final dio = ref.watch(monitoringDioProvider);
    final page = params['page'] ?? 1;
    final limit = params['limit'] ?? 20;
    final status = params['status'];
    
    try {
      final response = await dio.get(
        '/api/v1/monitoring/workflows/low-level',
        queryParameters: {
          'page': page,
          'limit': limit,
          if (status != null) 'status': status,
        },
      );
      return PaginatedWorkflows.fromJson(response.data);
    } catch (e) {
      throw Exception('Failed to load low-level workflows: $e');
    }
  },
);

/// State notifier for manual refresh control
class MonitoringRefreshNotifier extends StateNotifier<DateTime> {
  MonitoringRefreshNotifier() : super(DateTime.now());

  void refresh() {
    state = DateTime.now();
  }
}

/// Provider for manual refresh trigger
final monitoringRefreshProvider = StateNotifierProvider<MonitoringRefreshNotifier, DateTime>(
  (ref) => MonitoringRefreshNotifier(),
);

/// Auto-refresh monitoring summary when refresh is triggered
final autoRefreshMonitoringSummaryProvider = FutureProvider<MonitoringSummary>((ref) async {
  // Watch the refresh trigger
  ref.watch(monitoringRefreshProvider);
  
  // Invalidate and re-fetch the summary
  return ref.watch(monitoringSummaryProvider.future);
});

/// Clear cache endpoint caller
final clearMonitoringCacheProvider = Provider<Future<void> Function()>((ref) {
  return () async {
    final dio = ref.watch(monitoringDioProvider);
    try {
      await dio.post('/api/v1/monitoring/cache/clear');
      // Trigger refresh after clearing cache
      ref.read(monitoringRefreshProvider.notifier).refresh();
    } catch (e) {
      throw Exception('Failed to clear cache: $e');
    }
  };
});

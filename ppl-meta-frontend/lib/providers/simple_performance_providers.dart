import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/face_detection_models.dart';
import '../services/workflow_api_client.dart';

part 'performance_providers.g.dart';

/// Parameters for performance history requests
class PerformanceHistoryParams {
  final DateTime? startDate;
  final DateTime? endDate;
  final String? interval;

  const PerformanceHistoryParams({
    this.startDate,
    this.endDate,
    this.interval,
  });
}

/// Provider for performance history
@riverpod
Future<List<WorkflowPerformanceMetrics>> performanceHistory(
  PerformanceHistoryRef ref,
  PerformanceHistoryParams params,
) async {
  final response = await ref
      .watch(workflowApiClientProvider)
      .getPerformanceHistory(
        startDate: params.startDate,
        endDate: params.endDate,
        interval: params.interval,
      );

  if (response.isSuccess && response.data != null) {
    return response.data!;
  } else {
    throw Exception(response.error ?? 'Failed to fetch performance history');
  }
}
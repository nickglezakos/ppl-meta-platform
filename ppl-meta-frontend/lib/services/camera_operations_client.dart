import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/api_client.dart';
import '../models/camera_operations_models.dart';

class CameraOperationsClient {
  final ApiClient _apiClient;

  CameraOperationsClient(this._apiClient);

  Future<CameraOperationsStatusResponse> getStatus({
    String? cameraType,
    String? state,
    int limit = 200,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/cameras/operations/status',
        queryParameters: {
          if (cameraType != null && cameraType.isNotEmpty) 'camera_type': cameraType,
          if (state != null && state.isNotEmpty) 'state': state,
          'limit': limit,
        },
      );
      return CameraOperationsStatusResponse.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (error) {
      throw _handleError(error, 'Failed to fetch camera operations status');
    }
  }

  Future<ReconcileHealthResponse> getReconcileHealth() async {
    try {
      final response = await _apiClient.get('/api/v1/cameras/operations/reconcile/health');
      return ReconcileHealthResponse.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (error) {
      throw _handleError(error, 'Failed to fetch reconcile health');
    }
  }

  Future<CameraOperationsAggregatesResponse> getAnalyticsAggregates({
    required DateTime from,
    required DateTime to,
    String groupBy = 'camera_type',
    String? cameraType,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/cameras/operations/analytics/aggregates',
        queryParameters: {
          'from': from.toUtc().toIso8601String(),
          'to': to.toUtc().toIso8601String(),
          'group_by': groupBy,
          if (cameraType != null && cameraType.isNotEmpty) 'camera_type': cameraType,
        },
      );
      return CameraOperationsAggregatesResponse.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (error) {
      throw _handleError(error, 'Failed to fetch camera operations aggregates');
    }
  }

  Future<ReconcileTriggerResponse> triggerReconcile({
    String? cameraId,
    bool syncFallback = true,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/cameras/operations/reconcile',
        data: {
          if (cameraId != null && cameraId.isNotEmpty) 'camera_id': cameraId,
          'sync_fallback': syncFallback,
        },
      );
      return ReconcileTriggerResponse.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (error) {
      throw _handleError(error, 'Failed to trigger reconcile');
    }
  }

  Exception _handleError(DioException error, String message) {
    if (error.response != null) {
      final statusCode = error.response!.statusCode;
      final responseData = error.response!.data;
      String detail = error.message ?? 'Unknown error';
      if (responseData is Map && responseData['detail'] != null) {
        detail = responseData['detail'].toString();
      }
      return Exception('$message: $statusCode - $detail');
    }
    return Exception('$message: ${error.message}');
  }
}

final cameraOperationsClientProvider = Provider<CameraOperationsClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CameraOperationsClient(apiClient);
});

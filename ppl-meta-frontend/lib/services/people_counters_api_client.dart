import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/api_response.dart';

/// API client for People Counters automation
/// (Settings supervisor + tagged-batch precompute pipeline).
///
/// Routes are exposed via the gateway at `/api/v1/people-counters/*`
/// and proxied to the orchestrator service.
/// See: docs/proposals/people-counters.md §5.9
class PeopleCountersApiClient {
  late final ApiClient _apiClient;

  PeopleCountersApiClient([ApiClient? apiClient]) {
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }

  // -------------------------------------------------------------------------
  // Status & control
  // -------------------------------------------------------------------------

  Future<ApiResponse<Map<String, dynamic>>> getStatus() async {
    try {
      final response = await _apiClient.get('/api/v1/people-counters/status');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> pause() async {
    try {
      final response = await _apiClient.post('/api/v1/people-counters/pause');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> resume() async {
    try {
      final response = await _apiClient.post('/api/v1/people-counters/resume');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  // -------------------------------------------------------------------------
  // Settings (12 numeric workflow keys, see proposal §5.9)
  // -------------------------------------------------------------------------

  Future<ApiResponse<Map<String, dynamic>>> getSettings() async {
    try {
      final response = await _apiClient.get('/api/v1/people-counters/settings');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> updateSetting(
    String key,
    double value,
  ) async {
    try {
      final response = await _apiClient.put(
        '/api/v1/people-counters/settings/$key',
        data: {'value': value},
      );
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  // -------------------------------------------------------------------------
  // Manual run / backfill
  // -------------------------------------------------------------------------

  /// Force a daily-batch run for one or more cameras (admin / backfill).
  /// If [cameraIds] is empty, the supervisor handles enqueuing.
  Future<ApiResponse<Map<String, dynamic>>> runDailyBatch({
    DateTime? date,
    List<String>? cameraIds,
    bool force = false,
  }) async {
    try {
      final body = <String, dynamic>{
        if (date != null) 'date': date.toUtc().toIso8601String(),
        if (cameraIds != null) 'camera_ids': cameraIds,
        'force': force,
      };
      final response = await _apiClient.post(
        '/api/v1/people-counters/run-daily-batch',
        data: body,
      );
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  // -------------------------------------------------------------------------
  // Jobs
  // -------------------------------------------------------------------------

  Future<ApiResponse<Map<String, dynamic>>> listJobs({
    String? cameraId,
    String? status,
    DateTime? dateFrom,
    DateTime? dateTo,
    int limit = 100,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        if (cameraId != null) 'camera_id': cameraId,
        if (status != null) 'job_status': status,
        if (dateFrom != null) 'date_from': dateFrom.toUtc().toIso8601String(),
        if (dateTo != null) 'date_to': dateTo.toUtc().toIso8601String(),
      };
      final response = await _apiClient.get(
        '/api/v1/people-counters/jobs',
        queryParameters: queryParams,
      );
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> getJob(String batchKey) async {
    try {
      final encoded = Uri.encodeComponent(batchKey);
      final response =
          await _apiClient.get('/api/v1/people-counters/jobs/$encoded');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> retryJob(String batchKey) async {
    try {
      final encoded = Uri.encodeComponent(batchKey);
      final response =
          await _apiClient.post('/api/v1/people-counters/jobs/$encoded/retry');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> invalidateBatch(
    String batchKey,
  ) async {
    try {
      final encoded = Uri.encodeComponent(batchKey);
      final response = await _apiClient
          .post('/api/v1/people-counters/jobs/$encoded/invalidate');
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> deadLetter({int limit = 100}) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/people-counters/dead-letter',
        queryParameters: {'limit': limit},
      );
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  // -------------------------------------------------------------------------
  String _handleDioError(DioException e) {
    if (e.response != null) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        return data['detail'].toString();
      }
      return 'HTTP ${e.response?.statusCode}: ${e.response?.statusMessage}';
    }
    return e.message ?? 'Network error';
  }
}

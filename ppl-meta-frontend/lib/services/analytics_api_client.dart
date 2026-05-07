import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/api_response.dart';

/// API client for analytics operations via Gateway service
class AnalyticsApiClient {
  late final ApiClient _apiClient;
  
  AnalyticsApiClient([ApiClient? apiClient]) {
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }

  /// Get MVR quality metrics (RECOMMENDED)
  /// 
  /// This endpoint follows the correct data tree: MVR → Individual → quality scores
  /// Returns accurate counts from tracking sessions
  Future<ApiResponse<Map<String, dynamic>>> getMvrQualityMetrics({
    String timeFilter = 'today', // today, last_3_days, last_week, last_month, custom
    String? collectionName,
    List<String>? cameraIds,
    List<String>? videoUuids,
    DateTime? startDate,
    DateTime? endDate,
    List<String>? genders,
    List<String>? ageGroups,
    String? dataSource,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'time_filter': timeFilter,
        if (collectionName != null && collectionName.isNotEmpty) 
          'collection_name': collectionName,
        if (cameraIds != null && cameraIds.isNotEmpty)
          'camera_ids': cameraIds.join(','),
        if (videoUuids != null && videoUuids.isNotEmpty)
          'video_uuids': videoUuids.join(','),
        if (timeFilter == 'custom' && startDate != null && endDate != null) ...{
          'start_date': startDate.toUtc().toIso8601String(),
          'end_date': endDate.toUtc().toIso8601String(),
        },
        if (genders != null && genders.isNotEmpty)
          'genders': genders.join(','),
        if (ageGroups != null && ageGroups.isNotEmpty)
          'age_groups': ageGroups.join(','),
        if (dataSource != null && dataSource != 'recording')
          'source_type': dataSource,
      };

      final response = await _apiClient.get(
        '/api/v1/analytics/mvr-quality-metrics',
        queryParameters: queryParams,
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get quality metrics by collection (OLD)
  /// 
  /// This endpoint uses individual_video_appearances (less accurate)
  /// Consider using getMvrQualityMetrics instead
  @Deprecated('Use getMvrQualityMetrics instead for accurate results')
  Future<ApiResponse<Map<String, dynamic>>> getQualityMetrics({
    String timeFilter = 'today',
    List<String>? collectionIds,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'time_filter': timeFilter,
        if (collectionIds != null && collectionIds.isNotEmpty)
          'camera_ids': collectionIds.join(','),
      };

      final response = await _apiClient.get(
        '/api/v1/analytics/quality-metrics',
        queryParameters: queryParams,
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  String _handleDioError(DioException error) {
    if (error.response != null) {
      final data = error.response?.data;
      if (data is Map && data.containsKey('detail')) {
        return data['detail'].toString();
      }
      return 'Server error: ${error.response?.statusCode}';
    } else if (error.type == DioExceptionType.connectionTimeout ||
               error.type == DioExceptionType.sendTimeout ||
               error.type == DioExceptionType.receiveTimeout) {
      return 'Connection timeout - please check your network';
    } else if (error.type == DioExceptionType.unknown) {
      return 'Network error - please check your connection';
    }
    return error.message ?? 'Unknown error occurred';
  }
}

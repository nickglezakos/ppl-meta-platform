import 'package:dio/dio.dart';

import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/api_response.dart';
import '../models/presence_models.dart';

class PresenceApiClient {
  late final ApiClient _apiClient;

  PresenceApiClient([ApiClient? apiClient]) {
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }

  Future<ApiResponse<PresenceAnalyticsSummary>> getAnalyticsSummary() async {
    try {
      final response = await _apiClient.get('/api/v1/presence/analytics/summary');
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceAnalyticsSummary.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<List<PresenceAnalyticsBucket>>> getBySessionMode() async {
    return _getBuckets('/api/v1/presence/analytics/by-session-mode');
  }

  Future<ApiResponse<List<PresenceAnalyticsBucket>>> getByGrantType() async {
    return _getBuckets('/api/v1/presence/analytics/by-grant-type');
  }

  Future<ApiResponse<List<PresenceSessionTraceSummary>>> getSessionTraces({
    int limit = 10,
  }) async {
    final pageResponse = await getSessionTracePage(limit: limit);
    if (!pageResponse.success) {
      return ApiResponse.error(pageResponse.error ?? 'Failed to load session traces');
    }
    return ApiResponse.success(pageResponse.data?.items ?? const []);
  }

  Future<ApiResponse<PresenceSessionTracePage>> getSessionTracePage({
    int limit = 20,
    int offset = 0,
    String? userQuery,
    String? cameraUuid,
    String? grantType,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/presence/mobile/session-traces',
        queryParameters: {
          'limit': limit,
          'offset': offset,
          if (userQuery != null && userQuery.isNotEmpty) 'user_query': userQuery,
          if (cameraUuid != null && cameraUuid.isNotEmpty) 'camera_uuid': cameraUuid,
          if (grantType != null && grantType.isNotEmpty) 'grant_type': grantType,
          if (startDate != null) 'start_date': startDate.toUtc().toIso8601String(),
          if (endDate != null) 'end_date': endDate.toUtc().toIso8601String(),
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceSessionTracePage.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceUserDayAwardPage>> getUserDayAwardSummaryPage({
    int limit = 20,
    int offset = 0,
    String? userQuery,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/presence/mobile/session-awards/by-user-day',
        queryParameters: {
          'limit': limit,
          'offset': offset,
          if (userQuery != null && userQuery.isNotEmpty) 'user_query': userQuery,
          if (startDate != null) 'start_date': startDate.toUtc().toIso8601String(),
          if (endDate != null) 'end_date': endDate.toUtc().toIso8601String(),
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceUserDayAwardPage.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceActionPlanDetails>> getActionPlan(String sessionUuid) async {
    try {
      final response = await _apiClient.get('/api/v1/presence/mobile/sessions/$sessionUuid/action-plan');
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceActionPlanDetails.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<List<PresenceDecisionRecordDetails>>> getDecisionHistory(String sessionUuid) async {
    try {
      final response = await _apiClient.get('/api/v1/presence/mobile/sessions/$sessionUuid/decision-history');
      final data = _unwrapData(response.data);
      final items = (data['items'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(PresenceDecisionRecordDetails.fromJson)
          .toList();
      return ApiResponse.success(items);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceSessionTraceDetails>> getSessionTrace(String sessionUuid) async {
    try {
      final response = await _apiClient.get('/api/v1/presence/mobile/sessions/$sessionUuid/trace');
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceSessionTraceDetails.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceLiveSession>> createSession({
    required String sessionMode,
    required String deviceUuid,
    required String deviceName,
    required String devicePlatform,
    required String appVersion,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/mobile/sessions',
        data: {
          'session_mode': sessionMode,
          'device_uuid': deviceUuid,
          'device_name': deviceName,
          'device_platform': devicePlatform,
          'app_version': appVersion,
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceLiveSession.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceLiveSession>> getSession(String sessionUuid) async {
    try {
      final response = await _apiClient.get('/api/v1/presence/mobile/sessions/$sessionUuid');
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceLiveSession.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceResultDetails>> getResult(String sessionUuid) async {
    try {
      final response = await _apiClient.get('/api/v1/presence/mobile/sessions/$sessionUuid/result');
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceResultDetails.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceQrPayload>> getCurrentQr({
    required String installationUuid,
    String? deviceReference,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/presence/qr/current',
        queryParameters: {
          'installation_uuid': installationUuid,
          if (deviceReference != null && deviceReference.isNotEmpty) 'device_reference': deviceReference,
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceQrPayload.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceQrPayload>> renderQr({
    required String installationUuid,
    String? deviceReference,
    String? deviceDisplayName,
    Map<String, dynamic>? location,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/qr/render',
        data: {
          'installation_uuid': installationUuid,
          if (deviceReference != null && deviceReference.isNotEmpty) 'device_reference': deviceReference,
          if (deviceDisplayName != null && deviceDisplayName.isNotEmpty) 'device_display_name': deviceDisplayName,
          if (location != null) 'location': location,
        },
      );
      final data = _unwrapData(response.data);
      final payload = data['payload'] is Map<String, dynamic> ? data['payload'] as Map<String, dynamic> : null;
      return ApiResponse.success(
        PresenceQrPayload(
          found: true,
          installationUuid: installationUuid,
          deviceReference: deviceReference,
          qrToken: data['qr_token']?.toString(),
          expiresAt: data['expires_at']?.toString(),
          sessionUuid: payload?['session_uuid']?.toString(),
          sessionStatus: null,
          qrStatus: null,
          qrType: payload?['qr_type']?.toString(),
          payload: payload,
        ),
      );
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceQrPayload>> renderOwnerQr({
    required String installationUuid,
    String? ownerUserUuid,
    String? ownerDisplayName,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/qr/render-owner',
        data: {
          'installation_uuid': installationUuid,
          if (ownerUserUuid != null && ownerUserUuid.isNotEmpty) 'owner_user_uuid': ownerUserUuid,
          if (ownerDisplayName != null && ownerDisplayName.isNotEmpty) 'owner_display_name': ownerDisplayName,
        },
      );
      final data = _unwrapData(response.data);
      final payload = data['payload'] is Map<String, dynamic> ? data['payload'] as Map<String, dynamic> : null;
      return ApiResponse.success(
        PresenceQrPayload(
          found: payload != null,
          installationUuid: installationUuid,
          deviceReference: null,
          qrToken: payload?['qr_token']?.toString(),
          expiresAt: payload?['expires_at']?.toString(),
          sessionUuid: payload?['session_uuid']?.toString(),
          sessionStatus: null,
          qrStatus: null,
          qrType: payload?['qr_type']?.toString(),
          payload: payload,
        ),
      );
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceQrValidation>> validateQr(String qrToken) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/qr/validate',
        data: {'qr_token': qrToken},
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceQrValidation.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceLiveSession>> submitQrHit({
    required String sessionUuid,
    required String qrToken,
    required String installationUuid,
    Map<String, dynamic>? qrPayload,
    DateTime? scannedAt,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/mobile/sessions/$sessionUuid/qr-hit',
        data: {
          'qr_token': qrToken,
          'installation_uuid': installationUuid,
          'scanned_at': (scannedAt ?? DateTime.now().toUtc()).toIso8601String(),
          if (qrPayload != null) 'qr_payload': qrPayload,
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceLiveSession.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceLiveSession>> submitOwnerQrHit({
    required String sessionUuid,
    required Map<String, dynamic> qrPayload,
    required String installationUuid,
    DateTime? scannedAt,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/mobile/sessions/$sessionUuid/owner-qr-hit',
        data: {
          'qr_payload': qrPayload,
          'installation_uuid': installationUuid,
          'scanned_at': (scannedAt ?? DateTime.now().toUtc()).toIso8601String(),
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceLiveSession.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceInstallationContext>> getInstallationContext() async {
    try {
      final response = await _apiClient.get('/api/v1/presence/installations/current');
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceInstallationContext.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<List<PresenceCameraOption>>> getCameras() async {
    try {
      final response = await _apiClient.get('/api/v1/presence/cameras');
      final data = _unwrapData(response.data);
      final items = (data['items'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(PresenceCameraOption.fromJson)
          .toList();
      return ApiResponse.success(items);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<List<PresenceIndividualGroupOption>>> getAvailableIndividualGroups() async {
    try {
      final response = await _apiClient.get('/api/v1/presence/installations/current/available-groups');
      final data = _unwrapData(response.data);
      final items = (data['items'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(PresenceIndividualGroupOption.fromJson)
          .toList();
      return ApiResponse.success(items);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceResourceReservation>> reserveCamera({
    required String installationUuid,
    required String resourceUuid,
    String mode = 'bind',
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/cameras/reserve',
        data: {
          'installation_uuid': installationUuid,
          'resource_uuid': resourceUuid,
          'mode': mode,
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceResourceReservation.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> unreserveCamera({
    required String installationUuid,
    required String resourceUuid,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/cameras/unreserve',
        data: {
          'installation_uuid': installationUuid,
          'resource_uuid': resourceUuid,
        },
      );
      return ApiResponse.success(_unwrapData(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceInstallationContext>> updateInstallationPolicy({
    required String installationUuid,
    required PresenceGroupPolicy groupPolicy,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/installations/current/policy',
        data: {
          'installation_uuid': installationUuid,
          'group_policy': groupPolicy.toJson(),
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceInstallationContext.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceInstallationContext>> updateInstallationSettings({
    required String installationUuid,
    required PresenceSessionSettings sessionSettings,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/installations/current/settings',
        data: {
          'installation_uuid': installationUuid,
          'session_settings': sessionSettings.toJson(),
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceInstallationContext.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<PresenceInstallationContext>> updateActivePresenceGroup({
    required String installationUuid,
    String? individualGroupId,
    String? groupName,
    bool clearActiveGroup = false,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/installations/current/active-group',
        data: {
          'installation_uuid': installationUuid,
          if (individualGroupId != null && individualGroupId.isNotEmpty) 'individual_group_id': individualGroupId,
          if (groupName != null && groupName.isNotEmpty) 'group_name': groupName,
          if (clearActiveGroup) 'clear_active_group': true,
        },
      );
      final data = _unwrapData(response.data);
      return ApiResponse.success(PresenceInstallationContext.fromJson(data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<Map<String, dynamic>>> resetReservations({
    required String installationUuid,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/presence/installations/current/reset-reservations',
        data: {'installation_uuid': installationUuid},
      );
      return ApiResponse.success(_unwrapData(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Future<ApiResponse<List<PresenceAnalyticsBucket>>> _getBuckets(String path) async {
    try {
      final response = await _apiClient.get(path);
      final data = _unwrapData(response.data);
      final items = (data['items'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(PresenceAnalyticsBucket.fromJson)
          .toList();
      return ApiResponse.success(items);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  Map<String, dynamic> _unwrapData(dynamic payload) {
    if (payload is Map<String, dynamic>) {
      final data = payload['data'];
      if (data is Map<String, dynamic>) {
        return data;
      }
      return payload;
    }
    return <String, dynamic>{};
  }

  String _handleDioError(DioException error) {
    if (error.response != null) {
      final data = error.response?.data;
      if (data is Map && data.containsKey('detail')) {
        return data['detail'].toString();
      }
      return 'Server error: ${error.response?.statusCode}';
    }
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return 'Connection timeout - please check your network';
    }
    if (error.type == DioExceptionType.unknown) {
      return 'Network error - please check your connection';
    }
    return error.message ?? 'Unknown error occurred';
  }
}
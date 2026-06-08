import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/api_client.dart';

class AuthorityStatus {
  final bool success;
  final bool enabled;
  final bool configured;
  final String serviceUrl;
  final String installationUuid;
  final String? resolvedInstallationUuid;
  final bool applicationKeyConfigured;
  final String? cachedLicenceName;
  final String? cachedTenantName;
  final String? cachedOwnerEmail;
  final bool currentUserIsApprovedOwner;
  final String? cachedLicenceStatus;
  final bool? cachedOwnerEnabled;
  final int? warningPeriodDays;
  final DateTime? warningStartedAt;
  final int? offlineGraceDays;
  final DateTime? lastCheckedAt;
  final DateTime? lastSuccessfulCheckAt;
  final String? lastResultReason;
  final DateTime? cacheExpiresAt;
  final bool cacheWithinGrace;
  final String runtimeState;
  final String? runtimeReason;
  final bool canOperate;
  final DateTime? warningDeadline;
  final int? warningDaysRemaining;

  const AuthorityStatus({
    required this.success,
    required this.enabled,
    required this.configured,
    required this.serviceUrl,
    required this.installationUuid,
    required this.resolvedInstallationUuid,
    required this.applicationKeyConfigured,
    required this.cachedLicenceName,
    required this.cachedTenantName,
    required this.cachedOwnerEmail,
    required this.currentUserIsApprovedOwner,
    required this.cachedLicenceStatus,
    required this.cachedOwnerEnabled,
    required this.warningPeriodDays,
    required this.warningStartedAt,
    required this.offlineGraceDays,
    required this.lastCheckedAt,
    required this.lastSuccessfulCheckAt,
    required this.lastResultReason,
    required this.cacheExpiresAt,
    required this.cacheWithinGrace,
    required this.runtimeState,
    required this.runtimeReason,
    required this.canOperate,
    required this.warningDeadline,
    required this.warningDaysRemaining,
  });

  factory AuthorityStatus.fromJson(Map<String, dynamic> json) {
    final authority = Map<String, dynamic>.from(json['authority'] as Map? ?? const {});
    return AuthorityStatus(
      success: json['success'] == true,
      enabled: authority['enabled'] == true,
      configured: authority['configured'] == true,
      serviceUrl: authority['service_url']?.toString() ?? '',
      installationUuid: authority['installation_uuid']?.toString() ?? '',
      resolvedInstallationUuid: authority['resolved_installation_uuid']?.toString(),
      applicationKeyConfigured: authority['application_key_configured'] == true,
      cachedLicenceName: authority['cached_licence_name']?.toString(),
      cachedTenantName: authority['cached_tenant_name']?.toString(),
      cachedOwnerEmail: authority['cached_owner_email']?.toString(),
      currentUserIsApprovedOwner: authority['current_user_is_approved_owner'] == true,
      cachedLicenceStatus: authority['cached_licence_status']?.toString(),
      cachedOwnerEnabled: authority['cached_owner_enabled'] as bool?,
      warningPeriodDays: authority['warning_period_days'] as int?,
      warningStartedAt: DateTime.tryParse(authority['warning_started_at']?.toString() ?? ''),
      offlineGraceDays: authority['offline_grace_days'] as int?,
      lastCheckedAt: DateTime.tryParse(authority['last_checked_at']?.toString() ?? ''),
      lastSuccessfulCheckAt: DateTime.tryParse(
        authority['last_successful_check_at']?.toString() ?? '',
      ),
      lastResultReason: authority['last_result_reason']?.toString(),
      cacheExpiresAt: DateTime.tryParse(authority['cache_expires_at']?.toString() ?? ''),
      cacheWithinGrace: authority['cache_within_grace'] == true,
      runtimeState: authority['runtime_state']?.toString() ?? 'not_configured',
      runtimeReason: authority['runtime_reason']?.toString(),
      canOperate: authority['can_operate'] == true,
      warningDeadline: DateTime.tryParse(authority['warning_deadline']?.toString() ?? ''),
      warningDaysRemaining: authority['warning_days_remaining'] as int?,
    );
  }

  bool get isOfflineCached => lastResultReason == 'offline_grace_cache';
  bool get isWarningActive => runtimeState == 'warning';
  bool get isSafeguardActive => runtimeState == 'safeguard';
  bool get isHealthy => enabled && configured && cachedOwnerEnabled == true;
}

class AuthorityStatusClient {
  final ApiClient _apiClient;

  AuthorityStatusClient(this._apiClient);

  Future<AuthorityStatus> getAuthorityStatus() async {
    try {
      final response = await _apiClient.get('/api/v1/licensing/authority/status');
      return AuthorityStatus.fromJson(Map<String, dynamic>.from(response.data as Map));
    } on DioException catch (error) {
      throw _handleError(error, 'Failed to fetch authority status');
    }
  }

  Future<AuthorityStatus> refreshAuthorityStatus() async {
    try {
      final response = await _apiClient.post('/api/v1/licensing/authority/refresh');
      return AuthorityStatus.fromJson(Map<String, dynamic>.from(response.data as Map));
    } on DioException catch (error) {
      throw _handleError(error, 'Failed to refresh authority status');
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

final authorityStatusClientProvider = Provider<AuthorityStatusClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthorityStatusClient(apiClient);
});
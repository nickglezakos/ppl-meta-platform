import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/config.dart';
import '../core/api/api_client.dart';
import '../models/email_settings.dart';

/// Email Settings API Client
class EmailSettingsClient {
  final ApiClient _apiClient;
  final String _baseUrl;

  EmailSettingsClient(this._apiClient)
      : _baseUrl = '${Config.gatewayServiceUrl}/api/v1';

  /// Get current email settings
  Future<EmailSettings> getEmailSettings() async {
    try {
      final response = await _apiClient.get('/api/v1/settings/email');
      return EmailSettings.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e, 'Failed to fetch email settings');
    }
  }

  /// Update email settings
  Future<EmailSettings> updateEmailSettings(EmailSettingsUpdate update) async {
    try {
      final response = await _apiClient.put(
        '/api/v1/settings/email',
        data: update.toJson(),
      );
      return EmailSettings.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e, 'Failed to update email settings');
    }
  }

  /// Test email settings by sending a test email
  Future<Map<String, dynamic>> testEmailSettings(String testEmail) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/settings/email/test',
        queryParameters: {'test_email': testEmail},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e, 'Failed to send test email');
    }
  }

  Exception _handleError(DioException error, String message) {
    if (error.response != null) {
      final statusCode = error.response!.statusCode;
      final detail = error.response!.data?['detail'] ?? error.message;
      return Exception('$message: $statusCode - $detail');
    } else {
      return Exception('$message: ${error.message}');
    }
  }
}

/// Provider for EmailSettingsClient
final emailSettingsClientProvider = Provider<EmailSettingsClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return EmailSettingsClient(apiClient);
});

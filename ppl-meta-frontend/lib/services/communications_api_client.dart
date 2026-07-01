import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/communication_log_model.dart';
import '../core/config/app_config.dart';

/// Service for interacting with Communications Service API
class CommunicationsApiClient {
  final String baseUrl;
  String? _authToken;

  CommunicationsApiClient({String? baseUrl})
      : baseUrl = baseUrl ?? AppConfig.instance.apiBaseUrl;

  /// Set authentication token
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Get headers with auth token if available
  Map<String, String> get _headers {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    return headers;
  }

  /// Fetch communication logs with filtering
  Future<CommunicationLogListResponse> fetchLogs({
    int page = 1,
    int pageSize = 50,
    String? type,
    String? status,
    String? triggerId,
    String? installationId,
    String? tenantName,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };

    if (type != null) queryParams['type'] = type;
    if (status != null) queryParams['status'] = status;
    if (triggerId != null) queryParams['trigger_id'] = triggerId;
    if (installationId != null) queryParams['installation_id'] = installationId;
    if (tenantName != null) queryParams['tenant_name'] = tenantName;
    if (startDate != null) queryParams['start_date'] = startDate.toIso8601String();
    if (endDate != null) queryParams['end_date'] = endDate.toIso8601String();

    final uri = Uri.parse('$baseUrl/api/v1/audit/logs')
        .replace(queryParameters: queryParams);

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return CommunicationLogListResponse.fromJson(jsonData);
      } else {
        throw Exception('Failed to load logs: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching communication logs: $e');
    }
  }

  /// Fetch a single communication log by UUID
  Future<CommunicationLog> fetchLog(String uuid) async {
    final uri = Uri.parse('$baseUrl/api/v1/audit/logs/$uuid');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return CommunicationLog.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('Communication log not found');
      } else {
        throw Exception('Failed to load log: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching communication log: $e');
    }
  }

  /// Get log statistics summary
  Future<Map<String, dynamic>> fetchStats() async {
    final uri = Uri.parse('$baseUrl/api/v1/audit/stats');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load stats: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching stats: $e');
    }
  }

  /// Health check
  Future<Map<String, dynamic>> healthCheck() async {
    final uri = Uri.parse('$baseUrl/health');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Health check failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Communications service unavailable: $e');
    }
  }
}

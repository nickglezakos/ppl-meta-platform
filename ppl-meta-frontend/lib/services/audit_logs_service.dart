// Audit Logs Service for PPL Meta Platform
// Handles API communication with Communications service for audit/communication logs

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/config.dart';

class AuditLogsService {
  final String baseUrl;
  String? _authToken;

  AuditLogsService({String? baseUrl})
      : baseUrl = baseUrl ?? Config.gatewayServiceUrl;

  /// Set authentication token for API requests
  void setAuthToken(String token) {
    _authToken = token;
  }

  /// Get authorization headers
  Map<String, String> get _headers {
    final headers = {
      'Content-Type': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    return headers;
  }

  /// Get audit/communication logs with filters
  Future<Map<String, dynamic>> getLogs({
    String? type,
    String? status,
    String? recipient,
    String? triggeredBy,
    String? triggerId,
    String? startDate,
    String? endDate,
    int page = 1,
    int pageSize = 50,
  }) async {
    try {
      final queryParams = <String, String>{
        'page': page.toString(),
        'page_size': pageSize.toString(),
      };
      
      if (type != null) queryParams['type'] = type;
      if (status != null) queryParams['status'] = status;
      if (recipient != null) queryParams['recipient'] = recipient;
      if (triggeredBy != null) queryParams['triggered_by'] = triggeredBy;
      if (triggerId != null) queryParams['trigger_id'] = triggerId;
      if (startDate != null) queryParams['start_date'] = startDate;
      if (endDate != null) queryParams['end_date'] = endDate;

      final uri = Uri.parse('$baseUrl/api/v1/audit/logs')
          .replace(queryParameters: queryParams);

      print('📋 Fetching audit logs from: $uri');

      final response = await http.get(uri, headers: _headers);

      print('📋 Response status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        print('📋 Loaded ${data['total']} audit logs');
        return data;
      } else {
        throw Exception(
            'Failed to load audit logs: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('❌ Error fetching audit logs: $e');
      rethrow;
    }
  }

  /// Get specific audit log by UUID
  Future<Map<String, dynamic>> getLogDetail(String logUuid) async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/audit/logs/$logUuid');

      print('📋 Fetching audit log detail: $uri');

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw Exception(
            'Failed to load audit log: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('❌ Error fetching audit log detail: $e');
      rethrow;
    }
  }
}

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/models/api_response.dart';
import 'auth_manager.dart';

/// API client for edge camera management
/// Communicates with platform backend proxy endpoints
class EdgeCameraApiClient {
  final String baseUrl;
  final AuthManager authManager;

  EdgeCameraApiClient({
    required this.baseUrl,
    required this.authManager,
  });

  /// Get authentication headers
  Future<Map<String, String>> _getHeaders() async {
    final token = authManager.token;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Get edge camera configuration
  Future<ApiResponse<Map<String, dynamic>>> getConfiguration(
    String deviceId,
  ) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/config'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to get configuration: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error getting configuration: $e');
    }
  }

  /// Update edge camera configuration
  Future<ApiResponse<Map<String, dynamic>>> updateConfiguration(
    String deviceId,
    Map<String, dynamic> updates,
  ) async {
    try {
      final headers = await _getHeaders();
      final response = await http.put(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/config'),
        headers: headers,
        body: json.encode({'updates': updates}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to update configuration: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error updating configuration: $e');
    }
  }

  /// Configure platform connection (similar to mobile camera)
  Future<ApiResponse<Map<String, dynamic>>> configurePlatform(
    String deviceId, {
    required String discoveryIp,
    int discoveryPort = 8006,
    int camerasPort = 8005,
    bool useNginx = false,
    String? apiKey,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/config/platform'),
        headers: headers,
        body: json.encode({
          'discovery_ip': discoveryIp,
          'discovery_port': discoveryPort,
          'cameras_port': camerasPort,
          'use_nginx': useNginx,
          if (apiKey != null) 'api_key': apiKey,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to configure platform: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error configuring platform: $e');
    }
  }

  /// Start streaming
  Future<ApiResponse<Map<String, dynamic>>> startStreaming(
    String deviceId,
  ) async {
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/control/start'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to start streaming: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error starting streaming: $e');
    }
  }

  /// Stop streaming
  Future<ApiResponse<Map<String, dynamic>>> stopStreaming(
    String deviceId,
  ) async {
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/control/stop'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to stop streaming: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error stopping streaming: $e');
    }
  }

  /// Restart edge camera
  Future<ApiResponse<Map<String, dynamic>>> restart(
    String deviceId, {
    String scope = 'application',
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/control/restart'),
        headers: headers,
        body: json.encode({'scope': scope}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to restart: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error restarting: $e');
    }
  }

  /// Reconnect to platform services
  Future<ApiResponse<Map<String, dynamic>>> reconnect(
    String deviceId, {
    required String service,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/control/reconnect'),
        headers: headers,
        body: json.encode({'service': service}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to reconnect: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error reconnecting: $e');
    }
  }

  /// Get logs
  Future<ApiResponse<Map<String, dynamic>>> getLogs(
    String deviceId, {
    int lines = 100,
    bool follow = false,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse(
          '$baseUrl/api/v1/edge-cameras/$deviceId/logs?lines=$lines&follow=$follow',
        ),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to get logs: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error getting logs: $e');
    }
  }

  /// Get status
  Future<ApiResponse<Map<String, dynamic>>> getStatus(
    String deviceId,
  ) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/status'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to get status: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error getting status: $e');
    }
  }

  /// Run network diagnostics
  Future<ApiResponse<Map<String, dynamic>>> getNetworkDiagnostics(
    String deviceId,
  ) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/edge-cameras/$deviceId/diagnostics/network'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ApiResponse.success(data);
      } else {
        return ApiResponse.error(
          'Failed to run diagnostics: ${response.statusCode}',
        );
      }
    } catch (e) {
      return ApiResponse.error('Error running diagnostics: $e');
    }
  }
}

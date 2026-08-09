import 'package:dio/dio.dart';
import '../models/capability.dart';
import '../api/api_client.dart';

/// Service for capability-related API calls to the EyeNet Node backend.
class CapabilitiesService {
  final ApiClient _apiClient;

  CapabilitiesService(this._apiClient);

  /// Get capabilities for a specific role
  Future<List<Capability>> getCapabilitiesByRole(int roleId) async {
    try {
      final response = await _apiClient.get<List<dynamic>>(
        '/capabilities/by-role/$roleId',
      );

      if (response.data == null) {
        throw Exception('No data received from server');
      }

      return response.data!
          .map((json) => Capability.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Get roles and capabilities for a specific user
  Future<Map<String, dynamic>> getRolesAndCapabilitiesForUser(int userId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/capabilities/by-user/$userId',
      );

      if (response.data == null) {
        throw Exception('No data received from server');
      }

      return response.data!;
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Get current user's own capabilities
  Future<Map<String, dynamic>> getMyCapabilities() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/capabilities/my-capabilities',
      );

      if (response.data == null) {
        throw Exception('No data received from server');
      }

      return response.data!;
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  Exception _handleError(DioException e) {
    if (e.response?.statusCode == 401) {
      return Exception('Authentication required. Please log in again.');
    } else if (e.response?.statusCode == 403) {
      return Exception('Access denied. Insufficient permissions.');
    } else if (e.response?.statusCode == 404) {
      return Exception('Capabilities not found.');
    } else if (e.type == DioExceptionType.connectionTimeout) {
      return Exception('Connection timeout. Please check your connection.');
    } else {
      return Exception('Failed to load capabilities: ${e.message}');
    }
  }
}

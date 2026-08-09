import 'package:dio/dio.dart';
import '../models/user.dart';
import '../api/api_client.dart';

class UsersService {
  final ApiClient _apiClient;

  UsersService(this._apiClient);

  /// Get list of users with pagination
  Future<List<User>> getUsers({int skip = 0, int limit = 100}) async {
    try {
      final response = await _apiClient.get<List<dynamic>>(
        '/api/v1/users/',
        queryParameters: {
          'skip': skip,
          'limit': limit,
        },
      );

      if (response.data == null) {
        throw Exception('No data received from server');
      }

      return response.data!
          .map((userJson) => User.fromJson(userJson as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('Authentication required. Please log in again.');
      } else if (e.response?.statusCode == 403) {
        throw Exception('Access denied. You do not have permission to view users.');
      } else if (e.response?.statusCode == 404) {
        throw Exception('Users endpoint not found.');
      } else if (e.response?.statusCode == 500) {
        throw Exception('Server error. Please try again later.');
      } else if (e.type == DioExceptionType.connectionTimeout) {
        throw Exception('Connection timeout. Please check your internet connection.');
      } else if (e.type == DioExceptionType.receiveTimeout) {
        throw Exception('Request timeout. Please try again.');
      } else {
        throw Exception('Failed to load users: ${e.message}');
      }
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }
  /// Get detailed user profile with roles and capabilities
  Future<Map<String, dynamic>> getUserProfile(int userId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/api/v1/users/user-profile/$userId',
      );

      if (response.data == null) {
        throw Exception('User profile not found');
      }

      return response.data!;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('Authentication required. Please log in again.');
      } else if (e.response?.statusCode == 403) {
        throw Exception('Access denied. Insufficient permissions.');
      } else if (e.response?.statusCode == 404) {
        throw Exception('User not found.');
      } else {
        throw Exception('Failed to load user profile: ${e.message}');
      }
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Toggle a capability on/off for a user
  Future<Map<String, dynamic>> toggleUserCapability(
    int userId,
    String capability,
    bool enabled,
  ) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/toggle-capability/$userId',
        data: {'capability': capability, 'enabled': enabled},
      );

      if (response.data == null) {
        throw Exception('Failed to toggle capability');
      }

      return response.data!;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('Authentication required. Please log in again.');
      } else if (e.response?.statusCode == 403) {
        throw Exception('Access denied. Insufficient permissions.');
      } else {
        throw Exception('Failed to toggle capability: ${e.message}');
      }
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }
}

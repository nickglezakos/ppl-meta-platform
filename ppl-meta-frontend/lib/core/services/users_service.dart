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

  /// Re-send verification email to the authenticated user
  Future<String> sendVerificationEmail() async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/send-verification-email',
      );

      if (response.data == null) {
        throw Exception('Failed to send verification email');
      }

      return response.data!['detail'] as String? ?? 'Verification email sent.';
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('Authentication required. Please log in again.');
      } else if (e.response?.statusCode == 500) {
        throw Exception('Failed to send email. Please try again later.');
      } else {
        final detail = (e.response?.data as Map?)?['detail']?.toString();
        throw Exception(detail ?? 'Failed to send verification email.');
      }
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Create a new user
  Future<Map<String, dynamic>> createUser(String username, String email, String password) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/register',
        data: {'username': username, 'email': email, 'password': password},
      );
      if (response.data == null) throw Exception('Failed to create user');
      return response.data!;
    } on DioException catch (e) {
      throw Exception(_errorMsg(e));
    }
  }

  /// Update user fields (username/email)
  Future<Map<String, dynamic>> updateUser(int userId, {String? username, String? email}) async {
    try {
      final body = <String, String>{};
      if (username != null) body['username'] = username;
      if (email != null) body['email'] = email;
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/api/v1/users/$userId',
        data: body,
      );
      if (response.data == null) throw Exception('Failed to update user');
      return response.data!;
    } on DioException catch (e) {
      throw Exception(_errorMsg(e));
    }
  }

  /// Delete a user
  Future<void> deleteUser(int userId) async {
    try {
      await _apiClient.delete('/api/v1/users/$userId');
    } on DioException catch (e) {
      throw Exception(_errorMsg(e));
    }
  }

  /// Toggle user active/disabled status
  Future<bool> disableUser(int userId) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/$userId/disable',
      );
      return response.data?['is_active'] == true;
    } on DioException catch (e) {
      throw Exception(_errorMsg(e));
    }
  }

  String _errorMsg(DioException e) {
    if (e.response?.statusCode == 409) return 'Already exists.';
    if (e.response?.statusCode == 404) return 'Not found.';
    if (e.response?.statusCode == 400) {
      return (e.response?.data as Map?)?['detail']?.toString() ?? 'Bad request';
    }
    return e.message ?? 'Request failed';
  }

}

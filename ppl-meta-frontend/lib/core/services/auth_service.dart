import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_client.dart';
import '../models/user.dart';
import '../config/app_config.dart';

/// Exception thrown when authentication fails
class AuthenticationException implements Exception {
  final String message;
  final String? code;

  const AuthenticationException(this.message, {this.code});

  @override
  String toString() => message;
}

/// Authentication service for handling user authentication
class AuthService {
  final ApiClient _apiClient;
  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'user_data';

  AuthService(this._apiClient);

  /// Login with email and password
  Future<AuthResponse> login(String email, String password) async {
    try {
      // Format as form data for OAuth2PasswordRequestForm
      final formData = FormData.fromMap({
        'username': email, // Backend expects email as username
        'password': password,
      });

      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/login',
        data: formData,
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      );

      if (response.data == null) {
        throw const AuthenticationException('Invalid response from server');
      }

      final authResponse = AuthResponse.fromJson(response.data!);
      
      // Store token and set it in API client
      await _storeToken(authResponse.accessToken);
      _apiClient.setAuthToken(authResponse.accessToken);

      // Fetch user info after successful login
      final user = await _fetchUserProfile();
      
      return authResponse.copyWith(user: user);
    } on DioException catch (e) {
      throw _handleApiError(e);
    }
  }

  /// Register a new user
  Future<User> register(String username, String email, String password) async {
    try {
      final registerRequest = RegisterRequest(
        username: username,
        email: email,
        password: password,
      );

      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/register',
        data: registerRequest.toJson(),
      );

      if (response.data == null) {
        throw const AuthenticationException('Invalid response from server');
      }

      return User.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleApiError(e);
    }
  }

  /// Logout user
  Future<void> logout() async {
    try {
      // Call backend logout endpoint if token exists
      final token = await _getStoredToken();
      if (token != null) {
        await _apiClient.post('/api/v1/users/logout');
      }
    } catch (e) {
      // Continue with logout even if backend call fails
    } finally {
      // Always clear local data
      await _clearStoredData();
      _apiClient.clearAuthToken();
    }
  }

  /// Get current user profile
  Future<User?> getCurrentUser() async {
    try {
      final token = await _getStoredToken();
      if (token == null || JwtDecoder.isExpired(token)) {
        await _clearStoredData();
        return null;
      }

      _apiClient.setAuthToken(token);
      return await _fetchUserProfile();
    } catch (e) {
      await _clearStoredData();
      return null;
    }
  }

  /// Check if user is authenticated
  Future<bool> isAuthenticated() async {
    final token = await _getStoredToken();
    return token != null && !JwtDecoder.isExpired(token);
  }

  /// Change user password
  Future<void> changePassword(String currentPassword, String newPassword) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/api/v1/users/update-password',
        data: {
          'old_password': currentPassword,
          'new_password': newPassword,
        },
      );

      if (response.statusCode != 200) {
        throw const AuthenticationException('Failed to change password');
      }
    } on DioException catch (e) {
      throw _handleApiError(e);
    }
  }

  /// Fetch user profile from backend
  Future<User> _fetchUserProfile() async {
    try {
      // Use media service user profile endpoint (integrated backend)
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/api/v1/user/profile',
      );

      if (response.data == null) {
        throw const AuthenticationException('Failed to fetch user profile');
      }

      // Extract user data from response
      final userData = response.data!['user'] ?? response.data!;
      return User.fromJson(userData);
    } on DioException catch (e) {
      throw _handleApiError(e);
    }
  }

  /// Store authentication token
  Future<void> _storeToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  /// Get stored authentication token
  Future<String?> _getStoredToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  /// Clear stored authentication data
  Future<void> _clearStoredData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
  }

  /// Handle API errors and convert to AuthenticationException
  AuthenticationException _handleApiError(DioException error) {
    if (error.response?.data != null) {
      try {
        final apiError = ApiError.fromJson(error.response!.data);
        return AuthenticationException(
          apiError.detail,
          code: error.response?.statusCode.toString(),
        );
      } catch (e) {
        // If parsing fails, use status message
      }
    }

    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        return const AuthenticationException('Connection timeout. Please check your internet connection.');
      case DioExceptionType.connectionError:
        return const AuthenticationException('Unable to connect to server. Please try again later.');
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        if (statusCode == 400) {
          return const AuthenticationException('Invalid email or password.');
        } else if (statusCode == 401) {
          return const AuthenticationException('Invalid credentials.');
        } else if (statusCode == 409) {
          return const AuthenticationException('Email already registered.');
        }
        return AuthenticationException(
          'Server error (${statusCode ?? 'unknown'}). Please try again later.',
        );
      default:
        return const AuthenticationException('An unexpected error occurred. Please try again.');
    }
  }
}

/// Provider for authentication service
final authServiceProvider = Provider<AuthService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthService(apiClient);
});

/// Extension for AuthResponse to add copyWith method
extension AuthResponseExtension on AuthResponse {
  AuthResponse copyWith({
    String? accessToken,
    String? tokenType,
    User? user,
  }) {
    return AuthResponse(
      accessToken: accessToken ?? this.accessToken,
      tokenType: tokenType ?? this.tokenType,
      user: user ?? this.user,
    );
  }
}

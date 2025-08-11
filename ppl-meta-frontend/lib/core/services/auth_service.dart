import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../models/user.dart';
import '../config/app_config.dart';

class AuthenticationException implements Exception {
  final String message;
  final String? code;

  const AuthenticationException(this.message, {this.code});

  @override
  String toString() => message;
}

class AuthService {
  final ApiClient _apiClient;
  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'user_data';

  AuthService(this._apiClient);

  // Initialize the service with stored token
  Future<void> initialize() async {
    final token = await _getStoredToken();
    if (token != null && !JwtDecoder.isExpired(token)) {
      _apiClient.setAuthToken(token);
    } else if (token != null) {
      // Token exists but is expired, clear it
      await _clearStoredData();
    }
  }

  // Login method
  Future<AuthResponse> login(String email, String password) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/users/login',
        data: {
          'username': email,  // Backend expects 'username' field
          'password': password,
        },
        options: Options(
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        ),
      );

      if (response.data == null) {
        throw const AuthenticationException('Invalid response from server');
      }

      final authResponse = AuthResponse.fromJson(response.data!);
      
      // Store the token and set it in the API client
      await _storeToken(authResponse.accessToken);
      _apiClient.setAuthToken(authResponse.accessToken);
      
      return authResponse;
    } on DioException catch (e) {
      throw _handleApiError(e);
    }
  }

  // Register method
  Future<User> register(String username, String email, String password) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/users/register',
        data: {
          'username': username,
          'email': email,
          'password': password,
        },
        options: Options(
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        ),
      );

      if (response.data == null) {
        throw const AuthenticationException('Invalid response from server');
      }

      return User.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleApiError(e);
    }
  }

  // Logout method
  Future<void> logout() async {
    try {
      await _apiClient.post('/api/v1/users/logout');
    } catch (e) {
      // Even if logout fails on server, clear local data
    } finally {
      await _clearStoredData();
      _apiClient.clearAuthToken();
    }
  }

  // Get current user
  Future<User?> getCurrentUser() async {
    try {
      final token = await _getStoredToken();
      if (token == null || JwtDecoder.isExpired(token)) {
        await _clearStoredData();
        _apiClient.clearAuthToken();
        return null;
      }

      // Set the token in the API client if it's not already set
      if (_apiClient.authToken != token) {
        _apiClient.setAuthToken(token);
      }

      final response = await _apiClient.get('/api/v1/users/profile');
      if (response.data != null) {
        return User.fromJson(response.data!);
      }
      return null;
    } catch (e) {
      await _clearStoredData();
      _apiClient.clearAuthToken();
      return null;
    }
  }

  // Check if user is authenticated
  Future<bool> isAuthenticated() async {
    final token = await _getStoredToken();
    if (token != null && !JwtDecoder.isExpired(token)) {
      // Set the token in the API client if it's not already set
      if (_apiClient.authToken != token) {
        _apiClient.setAuthToken(token);
      }
      return true;
    }
    return false;
  }

  // Change password
  Future<void> changePassword(String currentPassword, String newPassword) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/users/change-password',
        data: {
          'current_password': currentPassword,
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

  // Private helper methods
  Future<void> _storeToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<String?> _getStoredToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  Future<void> _clearStoredData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
  }

  AuthenticationException _handleApiError(DioException error) {
    if (error.response?.data != null) {
      try {
        final apiError = ApiError.fromJson(error.response!.data);
        return AuthenticationException(
          apiError.detail,
          code: apiError.type,
        );
      } catch (_) {
        // Fall through to status code handling
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
        switch (statusCode) {
          case 401:
            return const AuthenticationException('Invalid email or password.');
          case 403:
            return const AuthenticationException('Invalid credentials.');
          case 409:
            return const AuthenticationException('Email already registered.');
          default:
            return AuthenticationException(
              error.response?.data?['message'] ?? 'Server error occurred.',
              code: statusCode?.toString(),
            );
        }
      default:
        return const AuthenticationException('An unexpected error occurred. Please try again.');
    }
  }
}

// Provider for AuthService
final authServiceProvider = Provider<AuthService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthService(apiClient);
});

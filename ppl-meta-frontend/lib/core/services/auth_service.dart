import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../models/user.dart';
import '../config/app_config.dart';
import 'secure_storage_service.dart';

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
  static const String _lastLoginEmailKey = 'last_login_email';
  static const String _lastLoginPasswordKey = 'last_login_password';
  
  // Callbacks for authentication events
  final List<Function()> _onAuthenticationSuccessCallbacks = [];

  AuthService(this._apiClient);

  // Register callback for successful authentication
  void registerOnAuthenticationSuccess(Function() callback) {
    _onAuthenticationSuccessCallbacks.add(callback);
  }

  // Remove callback
  void unregisterOnAuthenticationSuccess(Function() callback) {
    _onAuthenticationSuccessCallbacks.remove(callback);
  }

  // Notify all callbacks
  void _notifyAuthenticationSuccess() {
    for (final callback in _onAuthenticationSuccessCallbacks) {
      try {
        callback();
      } catch (e) {
        print('Error in authentication success callback: $e');
      }
    }
  }

  // Initialize the service with stored token
  Future<void> initialize() async {
    print('AuthService: initialize() started');
    final token = await _getStoredToken();
    print('AuthService: Retrieved stored token: ${token != null ? 'EXISTS (${token.length} chars)' : 'NULL'}');
    
    if (token != null) {
      print('AuthService: Stored token found, setting in ApiClient');
      _apiClient.setAuthToken(token);
      
      // Notify success callbacks
      print('AuthService: Authentication success callbacks notified');
      _notifyAuthenticationSuccess();
    } else {
      print('AuthService: No stored token found');
    }
    print('AuthService: initialize() completed');
  }

  // Login method
  Future<AuthResponse> login(String email, String password) async {
    // Clear any existing tokens before attempting new login
    print('AuthService: Clearing any existing tokens before login attempt');
    await _clearStoredData();
    _apiClient.clearAuthToken();
    
    try {
      // Use URL-encoded format (not FormData which is for multipart/form-data)
      final response = await _apiClient.post(
        '/api/v1/users/login',
        data: 'username=${Uri.encodeComponent(email)}&password=${Uri.encodeComponent(password)}',
        options: Options(
          contentType: 'application/x-www-form-urlencoded',
        ),
      );

      if (response.data == null) {
        throw const AuthenticationException('Invalid response from server');
      }

      final authResponse = AuthResponse.fromJson(response.data!);
      
      // Store the token and set it in the API client
      await _storeToken(authResponse.accessToken);
      await _storeLastLoginCredentials(email, password);
      _apiClient.setAuthToken(authResponse.accessToken);
      
      return authResponse;
    } on DioException catch (e) {
      // Login failed - ensure tokens remain cleared
      print('AuthService: Login failed, ensuring tokens are cleared');
      await _clearStoredData();
      _apiClient.clearAuthToken();
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
      if (token == null) {
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
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        print('AuthService: 401 error - clearing stored auth data');
        await _clearStoredData();
        _apiClient.clearAuthToken();
      } else {
        print('AuthService: Non-401 error getting user profile: ${e.response?.statusCode}');
      }
      return null;
    } catch (e) {
      print('AuthService: Network error getting user profile: $e');
      return null;
    }
  }

  // Check if user is authenticated
  Future<bool> isAuthenticated() async {
    final token = await _getStoredToken();
    if (token != null) {
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
    print('AuthService: Storing token (${token.length} chars)');
    try {
      // Store in both secure storage and SharedPreferences for redundancy
      await SecureStorageService.setString(_tokenKey, token);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, token);
      print('AuthService: Token stored successfully in both secure storage and SharedPreferences');
    } catch (e) {
      print('AuthService: Error storing token: $e');
    }
  }

  Future<String?> _getStoredToken() async {
    print('AuthService: _getStoredToken() called');
    try {
      // Try secure storage first
      String? token = await SecureStorageService.getString(_tokenKey);
      print('AuthService: Secure storage result: ${token != null ? 'EXISTS (${token.length} chars)' : 'NULL'}');
      
      if (token != null) {
        return token;
      }
      
      // Fall back to SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      final keys = prefs.getKeys();
      print('AuthService: SharedPreferences keys: $keys');
      token = prefs.getString(_tokenKey);
      print('AuthService: SharedPreferences result: ${token != null ? 'EXISTS (${token.length} chars)' : 'NULL'}');
      return token;
    } catch (e) {
      print('AuthService: Error in _getStoredToken(): $e');
      return null;
    }
  }

  Future<void> _clearStoredData() async {
    print('AuthService: Clearing stored authentication data');
    try {
      // Clear from both storage systems
      await SecureStorageService.remove(_tokenKey);
      await SecureStorageService.remove(_userKey);
      await SecureStorageService.remove(_lastLoginEmailKey);
      await SecureStorageService.remove(_lastLoginPasswordKey);
      
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_tokenKey);
      await prefs.remove(_userKey);
      await prefs.remove(_lastLoginEmailKey);
      await prefs.remove(_lastLoginPasswordKey);
      
      print('AuthService: Stored data cleared from both secure storage and SharedPreferences');
    } catch (e) {
      print('AuthService: Error clearing stored data: $e');
    }
  }

  Future<void> _storeLastLoginCredentials(String email, String password) async {
    try {
      await SecureStorageService.setString(_lastLoginEmailKey, email);
      await SecureStorageService.setString(_lastLoginPasswordKey, password);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_lastLoginEmailKey, email);
      await prefs.remove(_lastLoginPasswordKey);
    } catch (e) {
      print('AuthService: Error storing last login credentials: $e');
    }
  }

  /// Get the current stored token for auth provider
  Future<String?> getToken() async {
    return await _getStoredToken();
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

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import '../services/secure_storage_service.dart';

/// HTTP client for API communication with the PPL Meta Platform backend
class ApiClient {
  late final Dio _dio;
  String? _authToken;
  final AppConfig _config;
  static const String _tokenKey = 'auth_token';
  static const String _lastLoginEmailKey = 'last_login_email';
  static const String _lastLoginPasswordKey = 'last_login_password';
  bool _tokenJustCleared = false; // Prevent immediate restore after clearing
  Future<bool>? _silentReauthFuture;

  ApiClient(this._config) {
    _dio = Dio(BaseOptions(
      baseUrl: _config.apiBaseUrl,
      connectTimeout: const Duration(seconds: 60),  // Increased for recording operations
      receiveTimeout: const Duration(seconds: 120),  // Increased for stop recording (video processing)
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Add request interceptor for authentication
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final skipAuthHeader = options.extra['skipAuthHeader'] == true;

          // If no token, try to restore from storage
          if (_authToken == null && !skipAuthHeader) {
            try {
              // Try secure storage first
              String? storedToken = await SecureStorageService.getString(_tokenKey);
              
              // Fall back to SharedPreferences
              if (storedToken == null) {
                final prefs = await SharedPreferences.getInstance();
                storedToken = prefs.getString(_tokenKey);
              }
              
              if (storedToken != null) {
                _authToken = storedToken;
                print('🔄 ApiClient: Restored token from storage');
              }
            } catch (e) {
              print('⚠️ ApiClient: Failed to restore token from storage: $e');
            }
          }
          
          if (!skipAuthHeader && _authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
            print('🔑 ApiClient: Adding auth header to ${options.method} ${options.path}');
          } else {
            print('⚠️ ApiClient: NO AUTH TOKEN for ${options.method} ${options.path}');
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle authentication failures for 401 and 403 errors
          final statusCode = error.response?.statusCode;
          if (statusCode == 401 || statusCode == 403) {
            final path = error.requestOptions.path;
            final alreadyRetried = error.requestOptions.extra['authRetried'] == true;
            final skipAuthRecovery = error.requestOptions.extra['skipAuthRecovery'] == true;
            final isLoginEndpoint = path.contains('/users/login');
            
            // Server response is the source of truth for token validity.
            bool shouldClearToken = false;

            if (_authToken != null) {
              print('⚠️ ApiClient: Server rejected token ($statusCode) on $path');
            }
            
            // Also clear token for auth endpoints
            final isAuthEndpoint = path.contains('/users/me') || 
                                   path.contains('/users/login') || 
                                   path.contains('/users/current') ||
                                   path.contains('/users/profile');

            if (!isLoginEndpoint && !alreadyRetried && !skipAuthRecovery) {
              final recovered = await _trySilentReauthentication();
              if (recovered && _authToken != null) {
                try {
                  final retryRequest = error.requestOptions;
                  retryRequest.headers['Authorization'] = 'Bearer $_authToken';
                  retryRequest.extra['authRetried'] = true;
                  retryRequest.extra['skipAuthRecovery'] = true;

                  final retryResponse = await _dio.fetch(retryRequest);
                  return handler.resolve(retryResponse);
                } catch (_) {
                }
              }
            }
            
            if (isAuthEndpoint) {
              shouldClearToken = true;
              print('🔓 ApiClient: $statusCode on auth endpoint: $path, clearing token');
            }
            
            // Check if server explicitly said authentication failed
            if (error.response?.data is Map) {
              final detail = error.response?.data['detail']?.toString().toLowerCase() ?? '';
              if (detail.contains('validate token') || 
                  detail.contains('not authenticated') ||
                  detail.contains('authentication required') ||
                  detail.contains('invalid token')) {
                shouldClearToken = true;
                print('🔓 ApiClient: Server reported authentication failure ($statusCode): $detail, clearing token');
              }
            }
            
            if (shouldClearToken) {
              _authToken = null;
              _tokenJustCleared = true; // Mark that we just cleared - don't restore immediately
              // Also clear from storage to prevent restore loop
              try {
                await SecureStorageService.remove(_tokenKey);
                final prefs = await SharedPreferences.getInstance();
                await prefs.remove(_tokenKey);
                print('🗑️ ApiClient: Cleared invalid token from storage');
              } catch (e) {
                print('⚠️ ApiClient: Failed to clear token from storage: $e');
              }
            } else {
              // Don't clear token for resource-specific errors (e.g., forbidden access to specific resource)
              print('⚠️ ApiClient: $statusCode error on $path, but keeping auth token (may be resource-specific issue)');
            }
          }
          handler.next(error);
        },
      ),
    );

    // Add logging interceptor for development (minimal logging)
    if (_config.isDevelopment) {
      _dio.interceptors.add(LogInterceptor(
        requestBody: false,  // Disable request body logging
        responseBody: false,  // Disable response body logging to prevent flooding
        requestHeader: false,
        responseHeader: false,
        logPrint: (object) {
          final str = object.toString();
          // Only log request/response lines, not bodies
          if (str.contains('*** Request ***') || str.contains('*** Response ***')) {
            if (str.length > 300) {
              print(str.substring(0, 300) + '... [truncated]');
            } else {
              print(str);
            }
          }
        },
      ));
    }
  }

  /// Set authentication token for subsequent requests
  void setAuthToken(String token) {
    _tokenJustCleared = false; // Reset flag when new token is set
    _authToken = token;
    _persistToken(token);
  }

  /// Get current authentication token
  String? get authToken => _authToken;

  /// Get base URL
  String get baseUrl => _dio.options.baseUrl;

  /// Get underlying Dio instance for advanced operations
  Dio get dio => _dio;

  /// Clear authentication token
  void clearAuthToken() {
    _authToken = null;
  }

  Future<bool> _trySilentReauthentication() async {
    if (_silentReauthFuture != null) {
      return _silentReauthFuture!;
    }

    _silentReauthFuture = _performSilentReauthentication();
    try {
      return await _silentReauthFuture!;
    } finally {
      _silentReauthFuture = null;
    }
  }

  Future<bool> _performSilentReauthentication() async {
    try {
      final credentials = await _getStoredLoginCredentials();
      if (credentials == null) {
        return false;
      }

      final email = credentials['email'];
      final password = credentials['password'];
      if (email == null || password == null || email.isEmpty || password.isEmpty) {
        return false;
      }

      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/users/login',
        data: 'username=${Uri.encodeComponent(email)}&password=${Uri.encodeComponent(password)}',
        options: Options(
          contentType: 'application/x-www-form-urlencoded',
          extra: {
            'skipAuthHeader': true,
            'skipAuthRecovery': true,
          },
        ),
      );

      final accessToken = response.data?['access_token']?.toString();
      if (accessToken == null || accessToken.isEmpty) {
        return false;
      }

      setAuthToken(accessToken);
      await _persistToken(accessToken);
      return true;
    } catch (e) {
      print('⚠️ ApiClient: Silent re-authentication failed: $e');
      return false;
    }
  }

  Future<Map<String, String>?> _getStoredLoginCredentials() async {
    try {
      String? email = await SecureStorageService.getString(_lastLoginEmailKey);
      String? password = await SecureStorageService.getString(_lastLoginPasswordKey);

      final prefs = await SharedPreferences.getInstance();
      email ??= prefs.getString(_lastLoginEmailKey);
      password ??= prefs.getString(_lastLoginPasswordKey);

      if (email == null || password == null || email.isEmpty || password.isEmpty) {
        return null;
      }

      return {
        'email': email,
        'password': password,
      };
    } catch (_) {
      return null;
    }
  }

  Future<void> _persistToken(String token) async {
    try {
      await SecureStorageService.setString(_tokenKey, token);
    } catch (_) {
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, token);
    } catch (_) {
    }
  }

  /// GET request
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return await _dio.get<T>(
      path,
      queryParameters: queryParameters,
      options: options,
    );
  }

  /// POST request
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return await _dio.post<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  /// PUT request
  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return await _dio.put<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  /// DELETE request
  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return await _dio.delete<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  /// PATCH request
  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return await _dio.patch<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }
}

/// Provider for API client
final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  ref.keepAlive(); // Prevent this provider from being disposed
  return ApiClient(config);
});

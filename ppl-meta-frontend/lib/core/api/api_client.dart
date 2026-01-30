import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import '../services/secure_storage_service.dart';

/// HTTP client for API communication with the PPL Meta Platform backend
class ApiClient {
  late final Dio _dio;
  String? _authToken;
  final AppConfig _config;
  static const String _tokenKey = 'auth_token';
  bool _tokenJustCleared = false; // Prevent immediate restore after clearing

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
          // If no token, try to restore from storage
          if (_authToken == null) {
            try {
              // Try secure storage first
              String? storedToken = await SecureStorageService.getString(_tokenKey);
              
              // Fall back to SharedPreferences
              if (storedToken == null) {
                final prefs = await SharedPreferences.getInstance();
                storedToken = prefs.getString(_tokenKey);
              }
              
              if (storedToken != null && !JwtDecoder.isExpired(storedToken)) {
                _authToken = storedToken;
                // Debug: Check token expiration
                try {
                  final decoded = JwtDecoder.decode(storedToken);
                  final exp = decoded['exp'];
                  final expiryDate = DateTime.fromMillisecondsSinceEpoch(exp * 1000);
                  final now = DateTime.now();
                  final timeUntilExpiry = expiryDate.difference(now);
                  print('🔄 ApiClient: Restored token from storage');
                  print('⏰ Token expires: $expiryDate (in ${timeUntilExpiry.inMinutes} minutes)');
                } catch (e) {
                  print('🔄 ApiClient: Restored token from storage (could not decode expiry)');
                }
              }
            } catch (e) {
              print('⚠️ ApiClient: Failed to restore token from storage: $e');
            }
          }
          
          if (_authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
            print('🔑 ApiClient: Adding auth header to ${options.method} ${options.path}');
          } else {
            print('⚠️ ApiClient: NO AUTH TOKEN for ${options.method} ${options.path}');
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle token expiration and retry logic for 401 and 403 errors
          final statusCode = error.response?.statusCode;
          if (statusCode == 401 || statusCode == 403) {
            final path = error.requestOptions.path;
            
            // Check if token is expired or invalid
            bool shouldClearToken = false;
            
            if (_authToken != null) {
              try {
                // Check if JWT is expired
                if (JwtDecoder.isExpired(_authToken!)) {
                  shouldClearToken = true;
                  print('🔓 ApiClient: Token is expired, clearing it');
                } else {
                  // Debug: Show time until expiry
                  try {
                    final decoded = JwtDecoder.decode(_authToken!);
                    final exp = decoded['exp'];
                    final expiryDate = DateTime.fromMillisecondsSinceEpoch(exp * 1000);
                    final now = DateTime.now();
                    final timeUntilExpiry = expiryDate.difference(now);
                    print('⚠️ ApiClient: Token NOT expired but server rejected it. Time until expiry: ${timeUntilExpiry.inMinutes} minutes');
                    print('🔧 This likely indicates a server-side issue:');
                    print('   - JWT secret mismatch between when token was issued and now');
                    print('   - Server restarted with different configuration');
                    print('   - Multiple servers with different secrets');
                  } catch (e) {
                    print('⚠️ ApiClient: Token NOT expired but server rejected it');
                  }
                  shouldClearToken = true; // Clear it anyway since server rejected it
                }
              } catch (e) {
                // Token is malformed or invalid
                shouldClearToken = true;
                print('🔓 ApiClient: Token is malformed/invalid, clearing it');
              }
            }
            
            // Also clear token for auth endpoints regardless of expiration check
            final isAuthEndpoint = path.contains('/users/me') || 
                                   path.contains('/users/login') || 
                                   path.contains('/users/current') ||
                                   path.contains('/users/profile');
            
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

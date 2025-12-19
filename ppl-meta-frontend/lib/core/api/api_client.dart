import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/app_config.dart';

/// HTTP client for API communication with the PPL Meta Platform backend
class ApiClient {
  late final Dio _dio;
  String? _authToken;
  final AppConfig _config;

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
        onRequest: (options, handler) {
          if (_authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
            print('🔑 ApiClient: Adding auth header to ${options.method} ${options.path}');
          } else {
            print('⚠️ ApiClient: NO AUTH TOKEN for ${options.method} ${options.path}');
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle token expiration and retry logic
          if (error.response?.statusCode == 401) {
            // Token expired, clear it but don't auto-logout here
            // Let the AuthService handle the 401 response properly
            _authToken = null;
            print('🔓 ApiClient: Token cleared due to 401 response');
            // Could implement refresh token logic here
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

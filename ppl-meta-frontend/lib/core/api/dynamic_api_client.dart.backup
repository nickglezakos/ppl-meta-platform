import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/app_config.dart';
import '../config/dynamic_app_config.dart';

/// Enhanced HTTP client for API communication with dynamic service discovery
class DynamicApiClient {
  late final Dio _dio;
  late final Ref _ref;
  String? _authToken;
  final AppConfig _config;
  final Map<String, String> _serviceBaseUrls = {};

  DynamicApiClient(this._config, this._ref) {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Add request interceptor for authentication and dynamic URL resolution
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Add authentication token if available
          if (_authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
          }

          // Resolve dynamic base URL if needed
          if (!options.path.startsWith('http')) {
            // Extract service name from path and get dynamic URL
            final serviceName = _extractServiceNameFromPath(options.path);
            final baseUrl = await _getServiceBaseUrl(serviceName);
            
            // Update the request with the dynamic base URL
            if (!options.path.startsWith('/')) {
              options.path = '/$options.path';
            }
            options.baseUrl = baseUrl;
          }

          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle token expiration and retry logic
          if (error.response?.statusCode == 401) {
            _authToken = null;
            print('🔓 DynamicApiClient: Token cleared due to 401 response');
          }
          handler.next(error);
        },
      ),
    );

    // Add logging interceptor for development
    if (_config.isDevelopment) {
      _dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
        requestHeader: true,
        responseHeader: true,
      ));
    }
  }

  /// Extract service name from API path
  String _extractServiceNameFromPath(String path) {
    // Default service mapping based on API paths
    if (path.contains('/auth') || path.contains('/users') || path.contains('/health')) {
      return 'gateway';
    } else if (path.contains('/media')) {
      return 'media';
    } else if (path.contains('/streaming') || path.contains('/cameras')) {
      return 'cameras';
    } else if (path.contains('/orchestrator')) {
      return 'orchestrator';
    } else if (path.contains('/vision')) {
      return 'vision';
    } else if (path.contains('/node')) {
      return 'node';
    }
    return 'gateway'; // Default to gateway service
  }

  /// Get the appropriate base URL for a service using discovery
  Future<String> _getServiceBaseUrl(String serviceName) async {
    // Return cached URL if available and fresh
    if (_serviceBaseUrls.containsKey(serviceName)) {
      return _serviceBaseUrls[serviceName]!;
    }

    if (!_config.serviceDiscoveryEnabled) {
      // Use fallback URLs when discovery is disabled
      String fallbackUrl;
      switch (serviceName) {
        case 'gateway':
          fallbackUrl = _config.fallbackApiBaseUrl;
          break;
        case 'media':
          fallbackUrl = _config.fallbackApiBaseUrl;
          break;
        case 'cameras':
          fallbackUrl = _config.fallbackCameraServiceUrl;
          break;
        case 'orchestrator':
          fallbackUrl = 'http://localhost:8002';
          break;
        case 'vision':
          fallbackUrl = 'http://localhost:8003';
          break;
        case 'node':
          fallbackUrl = 'http://localhost:8001';
          break;
        default:
          fallbackUrl = _config.fallbackApiBaseUrl;
      }
      _serviceBaseUrls[serviceName] = fallbackUrl;
      return fallbackUrl;
    }

    // Use dynamic service discovery
    try {
      final serviceUrl = await _ref.read(serviceUrlProvider(serviceName).future);
      _serviceBaseUrls[serviceName] = serviceUrl;
      return serviceUrl;
    } catch (e) {
      print('⚠️ Failed to discover $serviceName service, using fallback: $e');
      String fallbackUrl;
      switch (serviceName) {
        case 'gateway':
          fallbackUrl = _config.fallbackApiBaseUrl;
          break;
        case 'media':
          fallbackUrl = _config.fallbackApiBaseUrl;
          break;
        case 'cameras':
          fallbackUrl = _config.fallbackCameraServiceUrl;
          break;
        case 'orchestrator':
          fallbackUrl = 'http://localhost:8002';
          break;
        case 'vision':
          fallbackUrl = 'http://localhost:8003';
          break;
        case 'node':
          fallbackUrl = 'http://localhost:8001';
          break;
        default:
          fallbackUrl = _config.fallbackApiBaseUrl;
      }
      _serviceBaseUrls[serviceName] = fallbackUrl;
      return fallbackUrl;
    }
  }

  /// Clear cached service URLs to force re-discovery
  void clearServiceUrlCache() {
    _serviceBaseUrls.clear();
  }

  /// Set authentication token for subsequent requests
  void setAuthToken(String token) {
    _authToken = token;
  }

  /// Get current authentication token
  String? get authToken => _authToken;

  /// Clear authentication token
  void clearAuthToken() {
    _authToken = null;
  }

  /// Get underlying Dio instance for advanced operations
  Dio get dio => _dio;

  /// GET request with dynamic service discovery
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

  /// POST request with dynamic service discovery
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

  /// PUT request with dynamic service discovery
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

  /// DELETE request with dynamic service discovery
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

  /// Make a direct request to a specific service
  Future<Response<T>> requestToService<T>(
    String serviceName,
    String method,
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final baseUrl = await _getServiceBaseUrl(serviceName);
    final fullUrl = '$baseUrl$path';
    
    switch (method.toUpperCase()) {
      case 'GET':
        return await _dio.get<T>(
          fullUrl,
          queryParameters: queryParameters,
          options: options,
        );
      case 'POST':
        return await _dio.post<T>(
          fullUrl,
          data: data,
          queryParameters: queryParameters,
          options: options,
        );
      case 'PUT':
        return await _dio.put<T>(
          fullUrl,
          data: data,
          queryParameters: queryParameters,
          options: options,
        );
      case 'DELETE':
        return await _dio.delete<T>(
          fullUrl,
          data: data,
          queryParameters: queryParameters,
          options: options,
        );
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }
  }
}

/// Provider for enhanced API client with dynamic service discovery
final dynamicApiClientProvider = Provider<DynamicApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  ref.keepAlive(); // Prevent this provider from being disposed
  return DynamicApiClient(config, ref);
});

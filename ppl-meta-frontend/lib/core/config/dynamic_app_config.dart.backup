import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/dynamic_service_provider.dart';

class AppConfig {
  static AppConfig? _instance;
  static AppConfig get instance => _instance!;
  
  final String fallbackApiBaseUrl;
  final String fallbackCameraServiceUrl;
  final String discoveryServiceUrl;
  final String environment;
  final String logLevel;
  final bool cacheEnabled;
  final bool analyticsEnabled;
  final bool serviceDiscoveryEnabled;
  
  AppConfig._({
    required this.fallbackApiBaseUrl,
    required this.fallbackCameraServiceUrl,
    required this.discoveryServiceUrl,
    required this.environment,
    required this.logLevel,
    required this.cacheEnabled,
    required this.analyticsEnabled,
    required this.serviceDiscoveryEnabled,
  });
  
  static Future<void> initialize() async {
    try {
      final configString = await rootBundle.loadString('assets/config/env.development.json');
      final config = json.decode(configString);
      
      _instance = AppConfig._(
        fallbackApiBaseUrl: config['API_BASE_URL'] ?? 'http://localhost',
        fallbackCameraServiceUrl: config['CAMERA_SERVICE_URL'] ?? 'http://localhost:8005',
        discoveryServiceUrl: config['DISCOVERY_SERVICE_URL'] ?? 'http://localhost:8006',
        environment: config['ENVIRONMENT'] ?? 'development',
        logLevel: config['LOG_LEVEL'] ?? 'debug',
        cacheEnabled: config['CACHE_ENABLED'] ?? true,
        analyticsEnabled: config['ANALYTICS_ENABLED'] ?? false,
        serviceDiscoveryEnabled: config['SERVICE_DISCOVERY_ENABLED'] ?? true,
      );
    } catch (e) {
      // Fallback configuration if asset loading fails
      print('Warning: Could not load config file, using defaults: $e');
      _instance = AppConfig._(
        fallbackApiBaseUrl: 'http://localhost',
        fallbackCameraServiceUrl: 'http://localhost:8005',
        discoveryServiceUrl: 'http://localhost:8006',
        environment: 'development',
        logLevel: 'debug',
        cacheEnabled: true,
        analyticsEnabled: false,
        serviceDiscoveryEnabled: true,
      );
    }
  }
  
  // Legacy API Endpoints (fallback only)
  String get apiBaseUrl => fallbackApiBaseUrl;
  String get authEndpoint => '$fallbackApiBaseUrl/api/v1/auth';
  String get usersEndpoint => '$fallbackApiBaseUrl/api/v1/users';
  String get mediaEndpoint => '$fallbackApiBaseUrl/api/v1/media';
  String get healthEndpoint => '$fallbackApiBaseUrl/api/v1/health';
  
  // Camera Service Endpoints (fallback only)
  String get cameraStreamEndpoint => '$fallbackCameraServiceUrl/api/v1/streaming';
  String get cameraSnapshotEndpoint => '$fallbackCameraServiceUrl/api/v1/streaming';
  
  bool get isDevelopment => environment == 'development';
  bool get isStaging => environment == 'staging';
  bool get isProduction => environment == 'production';
}

// Provider for app configuration
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.instance);

/// Dynamic API client that uses service discovery when enabled
class DynamicApiClient {
  late final Ref _ref;
  String? _authToken;

  DynamicApiClient(this._ref);

  /// Get the appropriate base URL for a service using discovery
  Future<String> _getServiceBaseUrl(String serviceName) async {
    final config = _ref.read(appConfigProvider);
    
    if (!config.serviceDiscoveryEnabled) {
      // Use fallback URLs when discovery is disabled
      switch (serviceName) {
        case 'gateway':
          return config.fallbackApiBaseUrl;
        case 'media':
          return config.fallbackApiBaseUrl;
        case 'cameras':
          return config.fallbackCameraServiceUrl;
        default:
          return config.fallbackApiBaseUrl;
      }
    }

    // Use dynamic service discovery
    try {
      final serviceUrl = await _ref.read(serviceUrlProvider(serviceName).future);
      return serviceUrl;
    } catch (e) {
      print('⚠️ Failed to discover $serviceName service, using fallback: $e');
      switch (serviceName) {
        case 'gateway':
          return config.fallbackApiBaseUrl;
        case 'media':
          return config.fallbackApiBaseUrl;
        case 'cameras':
          return config.fallbackCameraServiceUrl;
        default:
          return config.fallbackApiBaseUrl;
      }
    }
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

  /// Get dynamic endpoint for auth service
  Future<String> get authEndpoint async {
    final baseUrl = await _getServiceBaseUrl('gateway');
    return '$baseUrl/api/v1/auth';
  }

  /// Get dynamic endpoint for users service
  Future<String> get usersEndpoint async {
    final baseUrl = await _getServiceBaseUrl('gateway');
    return '$baseUrl/api/v1/users';
  }

  /// Get dynamic endpoint for media service
  Future<String> get mediaEndpoint async {
    final baseUrl = await _getServiceBaseUrl('media');
    return '$baseUrl/api/v1/media';
  }

  /// Get dynamic endpoint for health service
  Future<String> get healthEndpoint async {
    final baseUrl = await _getServiceBaseUrl('gateway');
    return '$baseUrl/api/v1/health';
  }

  /// Get dynamic endpoint for camera streaming
  Future<String> get cameraStreamEndpoint async {
    final baseUrl = await _getServiceBaseUrl('cameras');
    return '$baseUrl/api/v1/streaming';
  }

  /// Get dynamic endpoint for camera snapshots
  Future<String> get cameraSnapshotEndpoint async {
    final baseUrl = await _getServiceBaseUrl('cameras');
    return '$baseUrl/api/v1/streaming';
  }
}

/// Provider for dynamic API client with service discovery
final dynamicApiClientProvider = Provider<DynamicApiClient>((ref) {
  ref.keepAlive(); // Prevent this provider from being disposed
  return DynamicApiClient(ref);
});

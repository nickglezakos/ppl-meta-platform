import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AppConfig {
  static AppConfig? _instance;
  static AppConfig get instance => _instance!;
  
  final String apiBaseUrl;
  final String cameraServiceUrl;
  final String environment;
  final String logLevel;
  final bool cacheEnabled;
  final bool analyticsEnabled;
  
  AppConfig._({
    required this.apiBaseUrl,
    required this.cameraServiceUrl,
    required this.environment,
    required this.logLevel,
    required this.cacheEnabled,
    required this.analyticsEnabled,
  });
  
  static Future<void> initialize({
    String? backendHostOverride,
  }) async {
    try {
      final configString = await rootBundle.loadString('assets/config/env.development.json');
      final config = json.decode(configString);

      final host = backendHostOverride?.trim();
      final apiBaseUrl = host != null && host.isNotEmpty
          ? 'http://$host:8080'
          : (config['API_BASE_URL'] ?? 'http://localhost:8080');
      final cameraServiceUrl = host != null && host.isNotEmpty
          ? 'http://$host:8005'
          : (config['CAMERA_SERVICE_URL'] ?? 'http://localhost:8005');
      
      _instance = AppConfig._(
        apiBaseUrl: apiBaseUrl,
        cameraServiceUrl: cameraServiceUrl,
        environment: config['ENVIRONMENT'] ?? 'development',
        logLevel: config['LOG_LEVEL'] ?? 'debug',
        cacheEnabled: config['CACHE_ENABLED'] ?? true,
        analyticsEnabled: config['ANALYTICS_ENABLED'] ?? false,
      );
    } catch (e) {
      // Fallback configuration if asset loading fails
      print('⚠️ Warning: Could not load config file, using defaults: $e');
      final host = backendHostOverride?.trim();
      _instance = AppConfig._(
        apiBaseUrl: host != null && host.isNotEmpty
            ? 'http://$host:8080'
            : 'http://localhost:8080',  // Gateway service - routes to all backend services
        cameraServiceUrl: host != null && host.isNotEmpty
            ? 'http://$host:8005'
            : 'http://localhost:8005',
        environment: 'development',
        logLevel: 'debug',
        cacheEnabled: true,
        analyticsEnabled: false,
      );
    }
  }
  
  // API Endpoints
  String get authEndpoint => '$apiBaseUrl/api/v1/auth';
  String get usersEndpoint => '$apiBaseUrl/api/v1/users';
  String get mediaEndpoint => '$apiBaseUrl/api/v1/media';
  String get healthEndpoint => '$apiBaseUrl/api/v1/health';
  
  // Camera Service Endpoints  
  String get cameraStreamEndpoint => '$cameraServiceUrl/api/v1/streaming';
  String get cameraSnapshotEndpoint => '$cameraServiceUrl/api/v1/streaming';
  
  bool get isDevelopment => environment == 'development';
  bool get isStaging => environment == 'staging';
  bool get isProduction => environment == 'production';
}

// Provider for app configuration
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.instance);

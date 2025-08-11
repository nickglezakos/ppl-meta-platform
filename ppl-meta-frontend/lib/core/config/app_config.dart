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
  
  static Future<void> initialize() async {
    try {
      final configString = await rootBundle.loadString('assets/config/env.development.json');
      final config = json.decode(configString);
      
      _instance = AppConfig._(
        apiBaseUrl: config['API_BASE_URL'] ?? 'http://localhost',
        cameraServiceUrl: config['CAMERA_SERVICE_URL'] ?? 'http://localhost',
        environment: config['ENVIRONMENT'] ?? 'development',
        logLevel: config['LOG_LEVEL'] ?? 'debug',
        cacheEnabled: config['CACHE_ENABLED'] ?? true,
        analyticsEnabled: config['ANALYTICS_ENABLED'] ?? false,
      );
    } catch (e) {
      // Fallback configuration if asset loading fails
      print('Warning: Could not load config file, using defaults: $e');
      _instance = AppConfig._(
        apiBaseUrl: 'http://localhost',
        cameraServiceUrl: 'http://localhost',
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
  String get cameraStreamEndpoint => '$cameraServiceUrl/cameras/api/v1/streaming';
  String get cameraSnapshotEndpoint => '$cameraServiceUrl/cameras/api/v1/streaming';
  
  bool get isDevelopment => environment == 'development';
  bool get isStaging => environment == 'staging';
  bool get isProduction => environment == 'production';
}

// Provider for app configuration
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.instance);

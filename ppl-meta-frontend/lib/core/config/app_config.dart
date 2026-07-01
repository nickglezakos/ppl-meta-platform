import 'dart:convert';
import 'package:flutter/foundation.dart';
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

  static String _originFromUri(Uri uri) {
    final defaultPort = (uri.scheme == 'https' && uri.port == 443) ||
        (uri.scheme == 'http' && uri.port == 80);
    final includePort = uri.hasPort && !defaultPort;
    return includePort
        ? '${uri.scheme}://${uri.host}:${uri.port}'
        : '${uri.scheme}://${uri.host}';
  }

  static ({String apiBaseUrl, String cameraServiceUrl}) _webRuntimeDefaults() {
    final uri = Uri.base;
    final rawHost = uri.host.isNotEmpty ? uri.host : 'localhost';
    final host = (rawHost == '0.0.0.0' || rawHost == '::1' || rawHost == '[::1]') ? 'localhost' : rawHost;
    final scheme = uri.scheme.isNotEmpty ? uri.scheme : 'http';

    // When served via nginx proxy (80/443), use same-origin API routes.
    final isProxyPort = !uri.hasPort || uri.port == 80 || uri.port == 443;
    if (isProxyPort) {
      final origin = _originFromUri(uri);
      return (apiBaseUrl: origin, cameraServiceUrl: origin);
    }

    // When served directly from Flutter web dev server (typically :3000),
    // route backend calls to the same host with backend service ports.
    return (
      apiBaseUrl: '$scheme://$host:8080',
      cameraServiceUrl: '$scheme://$host:8005',
    );
  }

  static String normalizeBrowserUrl(String url) {
    if (!kIsWeb || url.isEmpty) {
      return url;
    }

    final parsed = Uri.tryParse(url);
    if (parsed == null) {
      return url;
    }

    if (!parsed.hasScheme) {
      final baseUrl = Uri.parse(AppConfig.instance.apiBaseUrl);
      final normalizedPath = url.startsWith('/') ? url : '/$url';
      return baseUrl.resolve(normalizedPath).toString();
    }

    final browserUri = Uri.base;
    if (parsed.host == 'localhost' || parsed.host == '127.0.0.1' || parsed.host == '0.0.0.0') {
      return parsed.replace(host: browserUri.host, scheme: browserUri.scheme).toString();
    }

    return url;
  }
  
  static Future<void> initialize({
    String? backendHostOverride,
  }) async {
    try {
      final configString = await rootBundle.loadString('assets/config/env.development.json');
      final config = json.decode(configString);

      final webDefaults = kIsWeb ? _webRuntimeDefaults() : null;

      final host = backendHostOverride?.trim();
      final apiBaseUrl = host != null && host.isNotEmpty
          ? 'http://$host:8080'
          : (webDefaults?.apiBaseUrl ?? (config['API_BASE_URL'] ?? 'http://localhost:8080'));
      final cameraServiceUrl = host != null && host.isNotEmpty
          ? 'http://$host:8005'
          : (webDefaults?.cameraServiceUrl ?? (config['CAMERA_SERVICE_URL'] ?? 'http://localhost:8005'));
      
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
      final webDefaults = kIsWeb ? _webRuntimeDefaults() : null;
      final host = backendHostOverride?.trim();
      _instance = AppConfig._(
        apiBaseUrl: host != null && host.isNotEmpty
            ? 'http://$host:8080'
            : (webDefaults?.apiBaseUrl ?? 'http://localhost:8080'),  // Gateway service - routes to all backend services
        cameraServiceUrl: host != null && host.isNotEmpty
            ? 'http://$host:8005'
            : (webDefaults?.cameraServiceUrl ?? 'http://localhost:8005'),
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
  
  // Camera Service Endpoints (routed through gateway for NAT/hotspot compatibility)
  String get cameraStreamEndpoint => '$apiBaseUrl/api/v1/streaming';
  String get cameraSnapshotEndpoint => '$apiBaseUrl/api/v1/streaming';
  
  bool get isDevelopment => environment == 'development';
  bool get isStaging => environment == 'staging';
  bool get isProduction => environment == 'production';
}

// Provider for app configuration
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.instance);

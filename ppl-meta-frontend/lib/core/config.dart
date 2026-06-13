import 'package:flutter/foundation.dart';

class Config {
  static String _backendHost = 'localhost';

  static String _resolvedBackendHost() {
    if (!kIsWeb) {
      return _backendHost;
    }

    final host = Uri.base.host.trim();
    if (host.isEmpty || host == '0.0.0.0') {
      return _backendHost;
    }

    return host;
  }

  static String get backendHost => _backendHost;

  static String get baseUrl => 'http://${_resolvedBackendHost()}:8080';

  static String get gatewayServiceUrl => baseUrl;
  static String get mediaServiceUrl => baseUrl;
  static String get nodeServiceUrl => baseUrl;
  static String get orchestratorServiceUrl => baseUrl;
  static String get visionServiceUrl => baseUrl;
  static String get camerasServiceUrl => 'http://${_resolvedBackendHost()}:8005';
  static String get discoveryServiceUrl => 'http://${_resolvedBackendHost()}:8006';
  static String get bootcoreServiceUrl => baseUrl;
  static String get vmetaServiceUrl => baseUrl;
  static String get communicationsServiceUrl => baseUrl;

  static void configureBackendHost(String backendHost) {
    _backendHost = backendHost;
  }
  
  // API version
  static const String apiVersion = 'v1';
}

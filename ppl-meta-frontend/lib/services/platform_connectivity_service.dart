import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import 'discovery_service_client.dart';

class PlatformConnectivityService {
  static PlatformConnectivityService? _instance;
  static SharedPreferences? _prefs;

  static const String _backendHostKey = 'platform_backend_host';
  static const String _discoveryPortKey = 'platform_discovery_port';
  static const String _configuredKey = 'platform_is_configured';

  PlatformConnectivityService._();

  static Future<PlatformConnectivityService> getInstance() async {
    _instance ??= PlatformConnectivityService._();
    _prefs ??= await SharedPreferences.getInstance();
    return _instance!;
  }

  bool get isConfigured => _prefs?.getBool(_configuredKey) ?? false;

  String get backendHost => _prefs?.getString(_backendHostKey) ?? 'localhost';

  int get discoveryPort => _prefs?.getInt(_discoveryPortKey) ?? 8006;

  String get discoveryUrl => 'http://$backendHost:$discoveryPort';

  Future<bool> saveConfiguration({
    required String backendInput,
    required int discoveryPort,
  }) async {
    final normalizedHost = _normalizeBackendHost(backendInput);
    if (normalizedHost == null) {
      return false;
    }

    await _prefs?.setString(_backendHostKey, normalizedHost);
    await _prefs?.setInt(_discoveryPortKey, discoveryPort);
    await _prefs?.setBool(_configuredKey, true);
    return true;
  }

  Future<void> clearConfiguration() async {
    await _prefs?.remove(_backendHostKey);
    await _prefs?.remove(_discoveryPortKey);
    await _prefs?.setBool(_configuredKey, false);
  }

  Future<bool> testDiscoveryConnection({
    required String backendInput,
    required int discoveryPort,
  }) async {
    final normalizedHost = _normalizeBackendHost(backendInput);
    if (normalizedHost == null) {
      return false;
    }

    final dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 7),
      ),
    );

    try {
      final response = await dio.get('http://$normalizedHost:$discoveryPort/health');
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> applyRuntimeConfiguration() async {
    final host = backendHost;
    final port = discoveryPort;

    Config.configureBackendHost(host);

    final discoveryServiceUrl = 'http://$host:$port';
    DiscoveryService.setDefaultDiscoveryServiceUrl(discoveryServiceUrl);
    DiscoveryService.initialize(discoveryServiceUrl: discoveryServiceUrl);
  }

  String? normalizeHostForInput(String input) => _normalizeBackendHost(input);

  String? _normalizeBackendHost(String input) {
    final trimmed = input.trim();
    if (trimmed.isEmpty) return null;

    try {
      final uri = trimmed.startsWith('http://') || trimmed.startsWith('https://')
          ? Uri.parse(trimmed)
          : Uri.parse('http://$trimmed');

      if (uri.host.isEmpty) {
        return null;
      }

      return uri.host;
    } catch (_) {
      return null;
    }
  }
}

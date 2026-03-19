import 'package:shared_preferences/shared_preferences.dart';
import 'package:logger/logger.dart';

/// Service for managing user-configurable backend connection settings
class ConfigService {
  static ConfigService? _instance;
  static SharedPreferences? _prefs;
  final Logger _logger = Logger();

  ConfigService._internal();

  static Future<ConfigService> getInstance() async {
    if (_instance == null) {
      _instance = ConfigService._internal();
      _prefs = await SharedPreferences.getInstance();
    }
    return _instance!;
  }

  // Configuration keys
  static const String _backendIPKey = 'backend_ip';
  static const String _discoveryPortKey = 'discovery_port';
  static const String _configuredKey = 'is_configured';

  /// Check if backend has been configured
  bool get isConfigured {
    return _prefs?.getBool(_configuredKey) ?? false;
  }

  /// Get configured backend IP
  String get backendIP {
    return _prefs?.getString(_backendIPKey) ?? 'localhost';
  }

  /// Get configured discovery port
  int get discoveryPort {
    return _prefs?.getInt(_discoveryPortKey) ?? 8006;
  }

  /// Get full discovery service URL
  String get discoveryServiceUrl {
    return 'http://$backendIP:$discoveryPort';
  }

  /// Get media service URL (default port 8000)
  String get mediaServiceUrl {
    return 'http://$backendIP:8000';
  }

  /// Get gateway URL (default port 8080)
  String get gatewayUrl {
    return 'http://$backendIP:8080';
  }

  /// Save backend configuration
  Future<bool> saveConfiguration({
    required String backendIP,
    required int discoveryPort,
  }) async {
    try {
      await _prefs?.setString(_backendIPKey, backendIP);
      await _prefs?.setInt(_discoveryPortKey, discoveryPort);
      await _prefs?.setBool(_configuredKey, true);
      
      _logger.i('✅ Configuration saved: $backendIP:$discoveryPort');
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to save configuration', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Save backend URL (convenience method for setup screen)
  Future<bool> saveBackendUrl(String backendIP, String portString) async {
    final port = int.tryParse(portString) ?? 8006;
    return await saveConfiguration(
      backendIP: backendIP,
      discoveryPort: port,
    );
  }

  /// Clear configuration (for testing/reset)
  Future<void> clearConfiguration() async {
    await _prefs?.remove(_backendIPKey);
    await _prefs?.remove(_discoveryPortKey);
    await _prefs?.setBool(_configuredKey, false);
    _logger.i('Configuration cleared');
  }

  /// Get configuration summary for logging
  String get configSummary {
    return 'Backend: $backendIP, Discovery Port: $discoveryPort, Configured: $isConfigured';
  }
}

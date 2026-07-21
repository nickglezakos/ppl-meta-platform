import 'package:shared_preferences/shared_preferences.dart';
import 'simplified_discovery_client.dart';

/// Service to manage discovery service configuration
/// Stores user's network configuration and provides discovery client methods
class DiscoveryConfigService {
  static const String _keyDiscoveryHost = 'discovery_host';
  static const String _keyDiscoveryPort = 'discovery_port';
  static const String _keyDeviceIPPrefix = 'device_ip_prefix';
  
  // Default configuration removed - user must provide explicit network configuration
  static const String _defaultDiscoveryPort = '8006';
  
  static DiscoveryConfigService? _instance;
  static DiscoveryConfigService get instance => _instance ??= DiscoveryConfigService._();
  
  DiscoveryConfigService._();
  
  String? _cachedDiscoveryUrl;
  SimplifiedDiscoveryClient? _discoveryClient;
  
  /// Initialize discovery service — preserve stored configuration.
  Future<void> initialize() async {
    // No longer clearing stored config — preserve user's previous setup
    print('🔧 Discovery service initialized (preserving stored configuration)');
  }

  /// Clear all stored discovery configuration
  Future<void> clearConfiguration() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyDiscoveryHost);
    await prefs.remove(_keyDiscoveryPort);
    await prefs.remove(_keyDeviceIPPrefix);
    
    // Also clear cached URL
    _cachedDiscoveryUrl = null;
    
    // Clear SimplifiedDiscoveryClient cache as well
    if (_discoveryClient != null) {
      _discoveryClient!.clearCache();
    }
    
    print('🗑️ Cleared all stored discovery configuration and cache');
  }

  /// Initialize discovery configuration from user input
  Future<void> configureFromUserInput({
    required String ipLastPart,
    required String port,
    String? deviceIPPrefix,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    
    // Build discovery service URL - require explicit network prefix
    if (deviceIPPrefix == null) {
      throw Exception(
        'Network prefix is required. Please specify the network where your backend services are running '
        '(e.g., "192.168.1" for services on 192.168.1.x network)'
      );
    }
    
    final discoveryHost = '$deviceIPPrefix.$ipLastPart';
    
    // Store configuration
    await prefs.setString(_keyDiscoveryHost, discoveryHost);
    await prefs.setString(_keyDiscoveryPort, port);
    await prefs.setString(_keyDeviceIPPrefix, deviceIPPrefix);
    
    // Cache the discovery URL
    _cachedDiscoveryUrl = 'http://$discoveryHost:$port';
    
    print('✅ Discovery configured: $_cachedDiscoveryUrl');
  }
  
  /// Get the configured discovery service URL
  Future<String?> getDiscoveryUrl() async {
    if (_cachedDiscoveryUrl != null) {
      return _cachedDiscoveryUrl;
    }

    final prefs = await SharedPreferences.getInstance();
    final host = prefs.getString(_keyDiscoveryHost);
    final port = prefs.getString(_keyDiscoveryPort);

    if (host != null && port != null) {
      _cachedDiscoveryUrl = 'http://$host:$port';
      return _cachedDiscoveryUrl;
    }

    // No fallback - user must configure discovery service explicitly
    print('❌ No discovery service configuration found - user input required');
    return null;
  }
  
  /// Get discovery client configured with user settings
  Future<SimplifiedDiscoveryClient?> getConfiguredDiscoveryClient() async {
    if (_discoveryClient != null) {
      return _discoveryClient;
    }

    final discoveryUrl = await getDiscoveryUrl();
    if (discoveryUrl == null) {
      print('❌ No discovery configuration found');
      return null;
    }

    _discoveryClient = SimplifiedDiscoveryClient();

    // Test if the configured discovery service is accessible
    try {
      final uri = Uri.parse(discoveryUrl);
      final host = uri.host;
      final port = uri.port;

      await _discoveryClient!.discoverServicesAtAddress('$host:$port');
      print('✅ Discovery client configured for: $discoveryUrl');
      return _discoveryClient;
    } catch (e) {
      print('❌ Failed to configure discovery client for $discoveryUrl: $e');
      // Don't set _discoveryClient to null here - keep it for retry
      return null;
    }
  }
  
  /// Find a specific service using configured discovery
  Future<ServiceInfo?> findService(String serviceName) async {
    final client = await getConfiguredDiscoveryClient();
    if (client == null) {
      return null;
    }
    
    return await client.findService(serviceName);
  }
  
  /// Get all services using configured discovery
  Future<List<ServiceInfo>> getAllServices() async {
    final client = await getConfiguredDiscoveryClient();
    if (client == null) {
      return [];
    }
    
    return await client.getAllServices();
  }
  
  /// Check if discovery is configured
  Future<bool> isConfigured() async {
    final prefs = await SharedPreferences.getInstance();
    final host = prefs.getString(_keyDiscoveryHost);
    return host != null;
  }
}

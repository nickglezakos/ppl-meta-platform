import 'package:shared_preferences/shared_preferences.dart';
import 'simplified_discovery_client.dart';

/// Service to manage discovery service configuration
/// Stores user's network configuration and provides discovery client methods
class DiscoveryConfigService {
  static const String _keyDiscoveryHost = 'discovery_host';
  static const String _keyDiscoveryPort = 'discovery_port';
  static const String _keyDeviceIPPrefix = 'device_ip_prefix';
  
  // Default configuration for PPL Meta platform
  static const String _defaultDiscoveryHost = '192.168.69.107';
  static const String _defaultDiscoveryPort = '8006';
  
  static DiscoveryConfigService? _instance;
  static DiscoveryConfigService get instance => _instance ??= DiscoveryConfigService._();
  
  DiscoveryConfigService._();
  
  String? _cachedDiscoveryUrl;
  SimplifiedDiscoveryClient? _discoveryClient;
  
  /// Initialize with default PPL Meta platform configuration
  Future<void> initializeWithDefaults() async {
    final prefs = await SharedPreferences.getInstance();
    
    // Only set defaults if no configuration exists
    final existingHost = prefs.getString(_keyDiscoveryHost);
    if (existingHost == null) {
      await prefs.setString(_keyDiscoveryHost, _defaultDiscoveryHost);
      await prefs.setString(_keyDiscoveryPort, _defaultDiscoveryPort);
      
      _cachedDiscoveryUrl = 'http://$_defaultDiscoveryHost:$_defaultDiscoveryPort';
      print('🔧 Initialized default discovery configuration: $_cachedDiscoveryUrl');
    }
  }

  /// Initialize discovery configuration from user input
  Future<void> configureFromUserInput({
    required String ipLastPart,
    required String port,
    String? deviceIPPrefix,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    
    // Build discovery service URL
    String discoveryHost;
    if (deviceIPPrefix != null) {
      discoveryHost = '$deviceIPPrefix.$ipLastPart';
    } else {
      // Auto-detect device IP and build target IP
      final discoveryClient = SimplifiedDiscoveryClient();
      final myIP = await discoveryClient.getMyIPAddress();
      
      if (myIP != null) {
        final parts = myIP.split('.');
        if (parts.length == 4) {
          discoveryHost = '${parts[0]}.${parts[1]}.${parts[2]}.$ipLastPart';
        } else {
          throw Exception('Invalid device IP format: $myIP');
        }
      } else {
        throw Exception('Could not detect device network IP address');
      }
    }
    
    // Store configuration
    await prefs.setString(_keyDiscoveryHost, discoveryHost);
    await prefs.setString(_keyDiscoveryPort, port);
    if (deviceIPPrefix != null) {
      await prefs.setString(_keyDeviceIPPrefix, deviceIPPrefix);
    }
    
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

    // Fall back to default configuration if no user config found
    _cachedDiscoveryUrl = 'http://$_defaultDiscoveryHost:$_defaultDiscoveryPort';
    print('🔧 Using default discovery configuration: $_cachedDiscoveryUrl');
    return _cachedDiscoveryUrl;
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
  
  /// Clear discovery configuration
  Future<void> clearConfiguration() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyDiscoveryHost);
    await prefs.remove(_keyDiscoveryPort);
    await prefs.remove(_keyDeviceIPPrefix);
    
    _cachedDiscoveryUrl = null;
    _discoveryClient = null;
    
    print('🗑️ Discovery configuration cleared');
  }
  
  /// Check if discovery is configured (always true with defaults)
  Future<bool> isConfigured() async {
    // Always return true since we have default configuration
    return true;
  }
}

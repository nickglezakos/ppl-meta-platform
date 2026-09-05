import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert' show jsonDecode, jsonEncode;
import 'package:http/http.dart' as http;
import 'simplified_discovery_client.dart';
import 'platform_config_service.dart';

/// Shared installation auth secret (Option 1) used to ask the local discovery
/// service to issue the HMAC token. Defaults to the dev secret so IDE/CLI
/// builds work out of the box; override per-environment via:
///   `--dart-define=INSTALL_AUTH_SECRET=<your_secret>`
const String _installAuthSecret = String.fromEnvironment(
  'INSTALL_AUTH_SECRET',
  defaultValue: 'ppl-meta-installation-auth-secret-dev',
);

/// Service to manage discovery service configuration
/// Stores user's network configuration and provides discovery client methods
class DiscoveryConfigService {
  static const String _keyDiscoveryHost = 'discovery_host';
  static const String _keyDiscoveryPort = 'discovery_port';
  static const String _keyDeviceIPPrefix = 'device_ip_prefix';
  static const String _keyApiToken = 'installation_api_token';
  static const String _keyInstallationUuid = 'installation_uuid';
  
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
    // VPN-mesh aware: once enrolled, the discovery service lives on the local
    // platform host resolved by PlatformConfigService (LAN by default, mesh when
    // remote). This lets the camera discover the platform from the enrollment
    // token instead of requiring a manually typed LAN IP.
    try {
      final platform = await PlatformConfigService.getInstance();
      final mesh = platform.vpnPlatformTailscaleIp;
      final platformLocal = platform.platformLocalIp;
      if ((mesh != null && mesh.isNotEmpty) ||
          (platformLocal != null && platformLocal.isNotEmpty)) {
        final vpnUrl = platform.discoveryServiceUrl;
        if (vpnUrl.isNotEmpty) {
          _cachedDiscoveryUrl = vpnUrl;
          return vpnUrl;
        }
      }
    } catch (_) {
      // Fall through to legacy stored configuration.
    }

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

  /// Persist the Authority-issued HMAC installation token + installation UUID
  /// (Issue #8). Used to authenticate discovery calls once AUTH_ENFORCE is on.
  Future<void> saveInstallationAuth({
    required String apiToken,
    required String installationUuid,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyApiToken, apiToken);
    await prefs.setString(_keyInstallationUuid, installationUuid);
    print('🔐 Saved installation token for discovery auth');
  }

  /// Build the installation-token auth headers for discovery requests.
  /// Returns an empty map when no token is configured (legacy open behavior).
  Future<Map<String, String>> authHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_keyApiToken) ?? '';
    final uuid = prefs.getString(_keyInstallationUuid) ?? '';
    if (token.isEmpty || uuid.isEmpty) {
      return {};
    }
    return {
      'Authorization': 'Bearer $token',
      'X-Installation-Uuid': uuid,
    };
  }

  /// Option 1 — local onboarding. Ask the local discovery service
  /// (`/api/v1/device-enroll`) to issue an HMAC installation token using the
  /// build-time secret, then persist it so discovery calls carry auth headers.
  /// Best-effort: returns false (and logs) on failure, never throws.
  Future<bool> enrollLocallyIfNeeded() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final existingToken = prefs.getString(_keyApiToken) ?? '';
      final existingUuid = prefs.getString(_keyInstallationUuid) ?? '';
      if (existingToken.isNotEmpty && existingUuid.isNotEmpty) {
        print('🔐 Already enrolled locally (token present)');
        return true;
      }

      final discoveryUrl = await getDiscoveryUrl();
      if (discoveryUrl == null) {
        print('❌ No discovery URL configured; skipping local enrollment');
        return false;
      }

      final resp = await http
          .post(
            Uri.parse('$discoveryUrl/api/v1/device-enroll'),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'X-Enroll-Key': _installAuthSecret,
            },
            body: jsonEncode({}), // blank uuid -> server generates signage-<uuid>
          )
          .timeout(const Duration(seconds: 8));

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final token = data['api_token'] as String? ?? '';
        final uuid = data['installation_uuid'] as String? ?? '';
        if (token.isNotEmpty && uuid.isNotEmpty) {
          await saveInstallationAuth(apiToken: token, installationUuid: uuid);
          print('🔐 Local token issued by discovery (Option 1)');
          return true;
        }
      }
      print('⚠️ Local enrollment failed (HTTP ${resp.statusCode}): ${resp.body}');
      return false;
    } catch (e) {
      print('⚠️ Local enrollment error: $e');
      return false;
    }
  }
}

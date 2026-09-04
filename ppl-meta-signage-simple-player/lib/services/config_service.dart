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

  // Authority (licensing/VPN) metadata keys
  static const String _authorityBaseUrlKey = 'authority_base_url';
  static const String _applicationKeyKey = 'authority_application_key';
  static const String _installationUuidKey = 'authority_installation_uuid';
  static const String _vpnPrimaryNodeIpKey = 'vpn_primary_node_ip';
  static const String _vpnMatrixGroupIdKey = 'vpn_matrix_group_id';
  static const String _vpnHeadscaleServerKey = 'vpn_headscale_server';
  static const String _vpnAuthKeyKey = 'vpn_auth_key';
  static const String _vpnEnrolledKey = 'vpn_enrolled';
  static const String _apiTokenKey = 'installation_api_token';
  static const String _installAuthSecretKey = 'installation_auth_secret';
  static const String _tailscaleIpKey = 'tailscale_ip';
  static const String _vpnPlatformTailscaleIpKey = 'vpn_platform_tailscale_ip';
  static const String _vpnPlatformHostnameKey = 'vpn_platform_hostname';

  /// Check if backend has been configured
  bool get isConfigured {
    return _prefs?.getBool(_configuredKey) ?? false;
  }

  /// Whether the app should skip onboarding and proceed to initialization.
  ///
  /// The app should only skip setup when it has a *usable identity* to act on:
  /// either a concrete backend host to reach, or an existing VPN enrollment /
  /// installation token. A stale `isConfigured=true` with no backend IP and no
  /// enrollment (e.g. a half-wiped install) must NOT skip — otherwise we'd boot
  /// into initialization building `http://:8080` and fail back to the token
  /// screen anyway.
  bool get skipOnboarding {
    // A valid enrollment (or issued install token) is always sufficient.
    if (vpnEnrolled) {
      return true;
    }
    final key = vpnAuthKey;
    if (key != null && key.isNotEmpty) {
      return true;
    }
    if (installationApiToken.isNotEmpty) {
      return true;
    }

    // Otherwise require a concretely configured backend host.
    if (isConfigured && _hasUsableBackendHost) {
      return true;
    }

    return false;
  }

  /// True when we have a non-empty backend IP OR a resolved platform mesh IP.
  bool get _hasUsableBackendHost {
    if (vpnPlatformTailscaleIp != null && vpnPlatformTailscaleIp!.isNotEmpty) {
      return true;
    }
    final ip = backendIP;
    if (ip.isEmpty || ip == 'localhost' || ip == ':') {
      return false;
    }
    return true;
  }

  /// Get configured backend IP
  String get backendIP {
    return _prefs?.getString(_backendIPKey) ?? 'localhost';
  }

  /// Get configured discovery port
  int get discoveryPort {
    return _prefs?.getInt(_discoveryPortKey) ?? 8006;
  }

  /// Get full discovery service URL. The discovery service lives on the LOCAL
  /// platform (on-prem), reachable over the LAN — NOT on the Hetzner authority.
  /// The authority/Hetzner is only used for onboarding and for remote devices
  /// reaching back over the VPN. So use the configured backend (LAN) IP.
  String get discoveryServiceUrl {
    return 'http://$backendIP:$discoveryPort';
  }

  /// Get media service URL (default port 8000). Local platform (LAN) host.
  String get mediaServiceUrl {
    return 'http://$backendIP:8000';
  }

  /// Get gateway URL (default port 8080). Local platform (LAN) host.
  String get gatewayUrl {
    return 'http://$backendIP:8080';
  }

  /// Get authority (licensing/VPN) service URL. The authority is the ONLINE
  /// Hetzner deployment (reachable during onboarding); it does NOT share the
  /// local platform host with discovery/media/gateway.
  String get authorityServiceUrl {
    final stored = _prefs?.getString(_authorityBaseUrlKey);
    if (stored != null && stored.isNotEmpty) {
      return stored;
    }
    // Default to the public authority endpoint.
    return 'https://authority.eyenet-vision.com';
  }

  /// Application key (licence) used for authority activation/enrollment.
  String get authorityApplicationKey {
    return _prefs?.getString(_applicationKeyKey) ?? '';
  }

  /// Installation UUID used for authority activation/enrollment.
  String get authorityInstallationUuid {
    return _prefs?.getString(_installationUuidKey) ?? '';
  }

  /// Primary node Tailscale IP supplied by the Authority (VPN-direct discovery).
  String? get vpnPrimaryNodeIp => _prefs?.getString(_vpnPrimaryNodeIpKey);

  /// Matrix group (mesh) id the installation belongs to.
  String? get vpnMatrixGroupId => _prefs?.getString(_vpnMatrixGroupIdKey);

  /// Headscale server the device is (or should be) enrolled with.
  String? get vpnHeadscaleServer => _prefs?.getString(_vpnHeadscaleServerKey);

  /// Pre-auth key issued for this installation.
  String? get vpnAuthKey => _prefs?.getString(_vpnAuthKeyKey);

  /// Assigned platform's mesh IP (the platform the client should dial over VPN).
  String? get vpnPlatformTailscaleIp => _prefs?.getString(_vpnPlatformTailscaleIpKey);

  /// Assigned platform's hostname (from the Authority).
  String? get vpnPlatformHostname => _prefs?.getString(_vpnPlatformHostnameKey);

  /// Whether the Authority has supplied VPN metadata for this device.
  bool get vpnEnrolled => _prefs?.getBool(_vpnEnrolledKey) ?? false;

  /// HMAC installation token used to authenticate to ppl-meta-discovery (Issue #8).
  String get installationApiToken => _prefs?.getString(_apiTokenKey) ?? '';

  /// Shared installation auth secret used for local (Option A) HMAC derivation.
  String get installationAuthSecret => _prefs?.getString(_installAuthSecretKey) ?? '';

  /// This player's own mesh (``100.64.x.x``) IP, persisted once the embedded
  /// tailscale node is up (Phase 4). Used to register the node's real VPN IP in
  /// discovery without relying on NetworkInterface.list() (which never sees the
  /// VPN tun on Android).
  String? get tailscaleIp => _prefs?.getString(_tailscaleIpKey);

  /// Persist this player's own mesh IP (Phase 4). Pass null/empty to clear it.
  Future<bool> saveTailscaleIp(String? ip) async {
    try {
      if (ip == null || ip.trim().isEmpty) {
        await _prefs?.remove(_tailscaleIpKey);
      } else {
        await _prefs?.setString(_tailscaleIpKey, ip.trim());
      }
      _logger.i('Tailscale IP saved: ${ip ?? 'cleared'}');
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to save tailscale IP', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Explicitly mark the player's VPN enrollment state (Phase 4). Used when the
  /// embedded tailscale node brings itself up, complementing the Authority path.
  Future<void> saveVpnEnrolled(bool value) async {
    await _prefs?.setBool(_vpnEnrolledKey, value);
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

  /// Save authority (licence) credentials used for activation/enrollment.
  Future<bool> saveAuthorityCredentials({
    required String applicationKey,
    required String installationUuid,
  }) async {
    try {
      await _prefs?.setString(_applicationKeyKey, applicationKey);
      await _prefs?.setString(_installationUuidKey, installationUuid);
      _logger.i('Authority credentials saved');
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to save authority credentials', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Save the Authority base URL used for VPN/licence enrollment. Overrides the
  /// default (`http://<backendIP>:8000`) which may not host the Authority.
  Future<bool> saveAuthorityBaseUrl(String url) async {
    try {
      final trimmed = url.trim();
      await _prefs?.setString(
        _authorityBaseUrlKey,
        trimmed.isEmpty ? 'http://$backendIP:8000' : trimmed,
      );
      _logger.i('Authority base URL saved: ${trimmed.isEmpty ? 'default' : trimmed}');
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to save authority base URL', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Save the shared installation auth secret used for local (Option A) HMAC
  /// token derivation. Persisted so the device knows how it issued its token.
  Future<bool> saveInstallationAuthSecret(String secret) async {
    try {
      await _prefs?.setString(_installAuthSecretKey, secret.trim());
      _logger.i('Installation auth secret saved (${secret.isEmpty ? 'empty' : 'present'})');
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to save installation auth secret', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Save VPN metadata returned by the Authority during enrollment.
  Future<bool> saveVpnMetadata({
    String? primaryNodeIp,
    String? matrixGroupId,
    String? headscaleServer,
    String? authKey,
    String? apiToken,
    String? platformTailscaleIp,
    String? platformHostname,
  }) async {
    try {
      if (primaryNodeIp != null) {
        await _prefs?.setString(_vpnPrimaryNodeIpKey, primaryNodeIp);
      }
      if (matrixGroupId != null) {
        await _prefs?.setString(_vpnMatrixGroupIdKey, matrixGroupId);
      }
      if (headscaleServer != null) {
        await _prefs?.setString(_vpnHeadscaleServerKey, headscaleServer);
      }
      if (authKey != null) {
        await _prefs?.setString(_vpnAuthKeyKey, authKey);
      }
      if (apiToken != null) {
        await _prefs?.setString(_apiTokenKey, apiToken);
      }
      if (platformTailscaleIp != null) {
        await _prefs?.setString(_vpnPlatformTailscaleIpKey, platformTailscaleIp);
      }
      if (platformHostname != null) {
        await _prefs?.setString(_vpnPlatformHostnameKey, platformHostname);
      }
      await _prefs?.setBool(_vpnEnrolledKey, authKey != null && authKey.isNotEmpty);
      _logger.i(
        'VPN metadata saved (primary_node_ip=$primaryNodeIp, matrix_group=$matrixGroupId, '
        'platform=$platformHostname@$platformTailscaleIp, enrolled=${authKey != null && authKey.isNotEmpty})',
      );
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to save VPN metadata', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Clear authority/VPN metadata (for re-provisioning / reset).
  Future<void> clearVpnMetadata() async {
    await _prefs?.remove(_vpnPrimaryNodeIpKey);
    await _prefs?.remove(_vpnMatrixGroupIdKey);
    await _prefs?.remove(_vpnHeadscaleServerKey);
    await _prefs?.remove(_vpnAuthKeyKey);
    await _prefs?.remove(_apiTokenKey);
    await _prefs?.remove(_vpnPlatformTailscaleIpKey);
    await _prefs?.remove(_vpnPlatformHostnameKey);
    await _prefs?.setBool(_vpnEnrolledKey, false);
    _logger.i('VPN metadata cleared');
  }

  /// Clear configuration (for testing/reset)
  Future<void> clearConfiguration() async {
    await _prefs?.remove(_backendIPKey);
    await _prefs?.remove(_discoveryPortKey);
    await _prefs?.setBool(_configuredKey, false);
    _logger.i('Configuration cleared');
  }

  /// Full factory reset: clears backend config, authority licence credentials,
  /// VPN metadata, and the installation API token. Used by the
  /// "Reset & Reconfigure" affordance to return the player to the initial
  /// Backend Setup screen.
  Future<void> resetAllConfiguration() async {
    try {
      await clearConfiguration();
      await clearVpnMetadata();
      await _prefs?.remove(_applicationKeyKey);
      await _prefs?.remove(_installationUuidKey);
      await _prefs?.remove(_installAuthSecretKey);
      // is_configured was already set to false by clearConfiguration().
      _logger.i('Configuration fully reset (backend + authority + VPN)');
    } catch (e, stackTrace) {
      _logger.e('Failed to fully reset configuration',
          error: e, stackTrace: stackTrace);
    }
  }

  /// Get configuration summary for logging
  String get configSummary {
    return 'Backend: $backendIP, Discovery Port: $discoveryPort, Configured: $isConfigured';
  }
}

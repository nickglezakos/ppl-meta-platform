import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'app_logger.dart';

/// Central service that resolves the platform endpoints the mobile camera
/// should talk to, using the VPN mesh discovery principles from
/// `docs/modules/VPN/vpn-mesh-discovery-and-remote-access.md`.
///
/// At enrollment the Authority returns, in one payload:
///   - [vpnPlatformTailscaleIp] — the platform's stable mesh IP (100.64.x.x),
///   - [platformLocalIp] — the platform's current LAN IP (fast on-LAN path),
///   - [vpnPlatformHostname] — the platform's human name.
///
/// The camera is a *leaf* on the mesh: it runs locally by default and remotely
/// on demand. [platformHost] prefers the LAN host unless [preferVpnHost] is set
/// (when the LAN path recently failed), then falls back to the mesh IP over the
/// internet. [ensurePlatformReachable] re-resolves stale LAN IPs from the
/// Authority (single internet round-trip) and, via Variant A, pulls the
/// platform's current local IP directly over the mesh.
class PlatformConfigService {
  static PlatformConfigService? _instance;
  static SharedPreferences? _prefs;

  PlatformConfigService._internal();

  /// Initialize with the shared prefs instance. Safe to call every boot.
  static Future<PlatformConfigService> getInstance() async {
    if (_instance == null) {
      _instance = PlatformConfigService._internal();
      _prefs = await SharedPreferences.getInstance();
    }
    return _instance!;
  }

  /// Reset the singleton so it re-reads a fresh prefs store. Test-only.
  @visibleForTesting
  static void resetForTest() {
    _instance = null;
    _prefs = null;
  }

  // ---------------------------------------------------------------------------
  // Storage keys
  // ---------------------------------------------------------------------------

  // Legacy manual backend config (LAN path, kept for backward compatibility).
  static const String _discoveryHostKey = 'discovery_host';
  static const String _savedBackendIpKey = 'saved_backend_ip';

  // Authority (online licensing / VPN) metadata.
  static const String _authorityBaseUrlKey = 'authority_base_url';
  static const String _applicationKeyKey = 'authority_application_key';
  static const String _installationUuidKey = 'authority_installation_uuid';
  static const String _apiTokenKey = 'installation_api_token';
  static const String _installAuthSecretKey = 'installation_auth_secret';
  static const String _vpnEnrolledKey = 'vpn_enrolled';
  static const String _vpnAuthKeyKey = 'vpn_auth_key';
  static const String _vpnHeadscaleServerKey = 'vpn_headscale_server';
  static const String _vpnPrimaryNodeIpKey = 'vpn_primary_node_ip';
  static const String _vpnMatrixGroupIdKey = 'vpn_matrix_group_id';
  static const String _vpnPlatformTailscaleIpKey = 'vpn_platform_tailscale_ip';
  static const String _vpnPlatformHostnameKey = 'vpn_platform_hostname';
  static const String _platformLocalIpKey = 'platform_local_ip';
  static const String _tailscaleIpKey = 'tailscale_ip';
  static const String _preferVpnKey = 'prefer_vpn_host';

  // Service ports (same conventions as the signage player).
  static const int discoveryPort = 8006;
  static const int gatewayPort = 8080;
  static const int platformNodePort = 8001;

  // Default public Authority endpoint (overridable via setup / app-key flow).
  String get defaultAuthorityUrl => 'https://authority.eyenet-vision.com';

  /// When true, [platformHost] prefers the mesh IP over LAN (remote device /
  /// LAN path recently failed). Cleared when LAN becomes reachable again.
/// The platform host to dial for discovery / gateway / node traffic.
  ///
  /// Precedence (LAN-first unless [preferVpnHost] is set):
  ///   1. [platformLocalIp] — auto-discovered from the enrollment token (LAN),
  ///   2. manual backend IP — configured during onboarding,
  ///   3. [vpnPlatformTailscaleIp] — the platform's mesh IP (remote/off-LAN).
  String get platformHost {
    if (preferVpnHost) {
      final vpn = vpnPlatformTailscaleIp;
      if (vpn != null && vpn.isNotEmpty) return vpn;
    }

    final local = platformLocalIp;
    if (local != null && local.isNotEmpty) return local;

    final manual = manualBackendIp;
    if (manual.isNotEmpty && manual != 'localhost' && manual != ':') {
      return manual;
    }

    final vpn = vpnPlatformTailscaleIp;
    if (vpn != null && vpn.isNotEmpty) return vpn;

    return 'localhost';
  }

  /// Whether the camera is currently preferring the mesh IP (remote mode).
  bool get preferVpnHost => _preferVpn || (_prefs?.getBool(_preferVpnKey) ?? false);

  /// Mark LAN as unreachable → subsequent [platformHost] uses the mesh IP.
  Future<void> markLanUnreachable() async {
    _preferVpn = true;
    await _prefs?.setBool(_preferVpnKey, true);
    AppLogger.instance.warning('Platform reachability: preferring VPN mesh host');
  }

  /// Mark LAN as reachable again → resume LAN-first host selection.
  Future<void> markLanReachable() async {
    _preferVpn = false;
    await _prefs?.setBool(_preferVpnKey, false);
    AppLogger.instance.info('Platform reachability: resuming LAN host');
  }

  // ---------------------------------------------------------------------------
  // Getters
  // ---------------------------------------------------------------------------

  String get authorityServiceUrl {
    final stored = _prefs?.getString(_authorityBaseUrlKey);
    if (stored != null && stored.isNotEmpty) return stored;
    return defaultAuthorityUrl;
  }

  String get authorityApplicationKey => _prefs?.getString(_applicationKeyKey) ?? '';
  String get authorityInstallationUuid =>
      _prefs?.getString(_installationUuidKey) ?? '';
  String get installationApiToken => _prefs?.getString(_apiTokenKey) ?? '';
  String get installationAuthSecret =>
      _prefs?.getString(_installAuthSecretKey) ?? '';

  bool get vpnEnrolled => _prefs?.getBool(_vpnEnrolledKey) ?? false;
  String? get vpnAuthKey => _prefs?.getString(_vpnAuthKeyKey);
  String? get vpnHeadscaleServer => _prefs?.getString(_vpnHeadscaleServerKey);
  String? get vpnPrimaryNodeIp => _prefs?.getString(_vpnPrimaryNodeIpKey);
  String? get vpnMatrixGroupId => _prefs?.getString(_vpnMatrixGroupIdKey);
  String? get vpnPlatformTailscaleIp =>
      _prefs?.getString(_vpnPlatformTailscaleIpKey);
  String? get vpnPlatformHostname => _prefs?.getString(_vpnPlatformHostnameKey);
  String? get platformLocalIp => _prefs?.getString(_platformLocalIpKey);
/// This camera's own mesh (100.64.x.x) IP, persisted once the embedded
  /// tailscale node is up. Used to register its real VPN IP so the platform can
  /// reach it remotely over the internet.
  String? get tailscaleIp => _prefs?.getString(_tailscaleIpKey);

  /// Legacy manual backend IP configured during onboarding (LAN path).
  String get manualBackendIp {
    final host = _prefs?.getString(_discoveryHostKey);
    if (host != null && host.isNotEmpty) return host;
    return _prefs?.getString(_savedBackendIpKey) ?? '';
  }

  /// Mesh IP of the platform to use for VPN-direct discovery / Variant A.
  /// Prefers the assigned platform mesh IP over the legacy primary-node IP.
  String? get vpnDiscoveryNodeIp {
    final platform = vpnPlatformTailscaleIp;
    if (platform != null && platform.isNotEmpty) return platform;
    final legacy = vpnPrimaryNodeIp;
    if (legacy != null && legacy.isNotEmpty) return legacy;
    // Last resort: the manual backend host, if it looks like a mesh IP.
    final manual = manualBackendIp;
    return (manual.startsWith('100.64.')) ? manual : null;
  }

  /// Full discovery service URL. The discovery service lives on the local
  /// platform (on-prem), reachable over the LAN — NOT on the Authority. The
  /// Authority is only used for onboarding and remote reach-back over the VPN,
  /// so use the resolved local platform host.
  String get discoveryServiceUrl => 'http://$platformHost:$discoveryPort';

  /// Gateway URL (default port 8080). Local platform (LAN) host.
  String get gatewayUrl => 'http://$platformHost:$gatewayPort';

  /// URL used to pull the platform's current local IP over the mesh (Variant A).
  String? get platformLocalIpPullUrl {
    final mesh = vpnPlatformTailscaleIp;
    if (mesh == null || mesh.isEmpty) return null;
    return 'http://$mesh:$platformNodePort/api/v1/vpn/local-ip';
  }

  bool get _hasUsableBackendHost {
    if (vpnPlatformTailscaleIp != null && vpnPlatformTailscaleIp!.isNotEmpty) {
      return true;
    }
    final ip = manualBackendIp;
    return ip.isNotEmpty && ip != 'localhost' && ip != ':';
  }

  /// Whether the app should skip onboarding. The camera can proceed when it has
  /// a usable identity: a VPN enrollment, an install token, or a concrete host.
  bool get skipOnboarding {
    if (vpnEnrolled) return true;
    final key = vpnAuthKey;
    if (key != null && key.isNotEmpty) return true;
    if (installationApiToken.isNotEmpty) return true;
    return _hasUsableBackendHost;
  }
// ---------------------------------------------------------------------------
  // Writers
  // ---------------------------------------------------------------------------

  /// Persist this camera's own mesh IP. Pass null/empty to clear it.
  Future<bool> saveTailscaleIp(String? ip) async {
    try {
      if (ip == null || ip.trim().isEmpty) {
        await _prefs?.remove(_tailscaleIpKey);
      } else {
        await _prefs?.setString(_tailscaleIpKey, ip.trim());
      }
      AppLogger.instance.info('Tailscale IP saved: ${ip ?? 'cleared'}');
      return true;
    } catch (e) {
      AppLogger.instance.warning('Failed to save tailscale IP: $e');
      return false;
    }
  }

  Future<void> saveVpnEnrolled(bool value) async {
    await _prefs?.setBool(_vpnEnrolledKey, value);
  }

  Future<bool> saveAuthorityBaseUrl(String url) async {
    try {
      final trimmed = url.trim();
      await _prefs?.setString(
        _authorityBaseUrlKey,
        trimmed.isEmpty ? defaultAuthorityUrl : trimmed,
      );
      AppLogger.instance.info('Authority base URL saved: ${trimmed.isEmpty ? 'default' : trimmed}');
      return true;
    } catch (e) {
      AppLogger.instance.warning('Failed to save authority base URL: $e');
      return false;
    }
  }

  Future<bool> saveAuthorityCredentials({
    required String applicationKey,
    required String installationUuid,
  }) async {
    try {
      await _prefs?.setString(_applicationKeyKey, applicationKey);
      await _prefs?.setString(_installationUuidKey, installationUuid);
      AppLogger.instance.info('Authority credentials saved');
      return true;
    } catch (e) {
      AppLogger.instance.warning('Failed to save authority credentials: $e');
      return false;
    }
  }

  /// Save the full VPN metadata returned by the Authority during enrollment.
  Future<bool> saveVpnMetadata({
    String? primaryNodeIp,
    String? matrixGroupId,
    String? headscaleServer,
    String? authKey,
    String? apiToken,
    String? installationUuid,
    String? applicationKey,
    String? platformTailscaleIp,
    String? platformHostname,
    String? platformLocalIp,
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
      if (installationUuid != null) {
        await _prefs?.setString(_installationUuidKey, installationUuid);
      }
      if (applicationKey != null) {
        await _prefs?.setString(_applicationKeyKey, applicationKey);
      }
      if (platformTailscaleIp != null) {
        await _prefs?.setString(_vpnPlatformTailscaleIpKey, platformTailscaleIp);
      }
      if (platformHostname != null) {
        await _prefs?.setString(_vpnPlatformHostnameKey, platformHostname);
      }
      if (platformLocalIp != null) {
        await _prefs?.setString(_platformLocalIpKey, platformLocalIp);
      }
      if (authKey != null && authKey.isNotEmpty) {
        await _prefs?.setBool(_vpnEnrolledKey, true);
      }
      AppLogger.instance.info(
        'VPN metadata saved (platform=$platformHostname@$platformTailscaleIp '
        'local=$platformLocalIp enrolled=$vpnEnrolled)',
      );
      return true;
    } catch (e) {
      AppLogger.instance.warning('Failed to save VPN metadata: $e');
      return false;
    }
  }
// ---------------------------------------------------------------------------
  // Reachability
  // ---------------------------------------------------------------------------

  /// Re-resolve this camera's assigned platform (local + mesh IP) from the
  /// online Authority using the stored HMAC installation token. One internet
  /// round-trip; use it when the platform's LAN IP may have changed.
  Future<bool> refreshPlatformEndpoints() async {
    final uuid = authorityInstallationUuid;
    final token = installationApiToken;
    if (uuid.isEmpty || token.isEmpty) {
      AppLogger.instance.warning(
        'Cannot refresh platform endpoints: missing installation uuid / token',
      );
      return false;
    }
    try {
      final resp = await http
          .post(
            Uri.parse('$authorityServiceUrl/api/v1/vpn/resolve-platform'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'installation_uuid': uuid, 'api_token': token}),
          )
          .timeout(const Duration(seconds: 10));
      if (resp.statusCode != 200) {
        AppLogger.instance.warning(
          'Platform resolve failed (HTTP ${resp.statusCode}): ${resp.body}',
        );
        return false;
      }
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      await saveVpnMetadata(
        platformTailscaleIp: data['platform_tailscale_ip'] as String?,
        platformHostname: data['platform_hostname'] as String?,
        platformLocalIp: data['platform_local_ip'] as String?,
      );
      AppLogger.instance.info(
        'Platform endpoints refreshed from authority: '
        'local=${data['platform_local_ip']} mesh=${data['platform_tailscale_ip']}',
      );
      return true;
    } catch (e) {
      AppLogger.instance.warning('Platform endpoint refresh failed: $e');
      return false;
    }
  }

  /// Variant A: pull the platform's *current* local LAN IP over the VPN mesh.
  /// `GET http://<platform_mesh_ip>:8001/api/v1/vpn/local-ip`
  /// Returns true when a fresh local IP was received and persisted.
  Future<bool> pullPlatformLocalIpFromMesh() async {
    final url = platformLocalIpPullUrl;
    if (url == null) {
      AppLogger.instance.warning('Cannot pull platform local-ip: no platform mesh IP');
      return false;
    }
    try {
      final resp = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 8));
      if (resp.statusCode != 200) {
        AppLogger.instance.warning(
          'Platform local-ip pull failed (HTTP ${resp.statusCode}): ${resp.body}',
        );
        return false;
      }
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      final freshLocal = data['platform_local_ip'] as String?;
      final freshMesh = data['platform_tailscale_ip'] as String?;
      final previous = platformLocalIp;
      await saveVpnMetadata(
        platformLocalIp: freshLocal,
        platformTailscaleIp: freshMesh,
      );
      AppLogger.instance.info(
        'Platform local-ip pulled over mesh: local=$freshLocal mesh=$freshMesh '
        '(was $previous)',
      );
      // If the LAN IP changed, try LAN again next time.
      if (freshLocal != null && freshLocal.isNotEmpty && freshLocal != previous) {
        await markLanReachable();
      }
      return freshLocal != null && freshLocal.isNotEmpty;
    } catch (e) {
      AppLogger.instance.warning('Platform local-ip pull over mesh failed: $e');
      return false;
    }
  }

  /// Probe whether the LAN path to the platform gateway is reachable.
  /// On failure: pull Variant A local-IP, then fall back to VPN preference.
  Future<bool> ensurePlatformReachable() async {
    // Always refresh the Authority cache once at boot / pre-operation (issue #9).
    await refreshPlatformEndpoints();

    final lanHost = platformLocalIp;
    final candidates = <String>[];
    if (lanHost != null && lanHost.isNotEmpty) candidates.add(lanHost);
    final manual = manualBackendIp;
    if (manual.isNotEmpty && manual != 'localhost' && manual != ':' &&
        !candidates.contains(manual)) {
      candidates.add(manual);
    }

    for (final host in candidates) {
      if (await _probeHost(host, gatewayPort)) {
        await markLanReachable();
        return true;
      }
    }

    // LAN failed (or unknown) → Variant A pull, then retry once.
    final pulled = await pullPlatformLocalIpFromMesh();
    if (pulled) {
      final fresh = platformLocalIp;
      if (fresh != null && fresh.isNotEmpty && await _probeHost(fresh, gatewayPort)) {
        await markLanReachable();
        return true;
      }
    }

    // Stay on mesh.
    if (vpnPlatformTailscaleIp != null && vpnPlatformTailscaleIp!.isNotEmpty) {
      await markLanUnreachable();
      return true;
    }
    return candidates.isNotEmpty || platformHost != 'localhost';
  }
Future<bool> _probeHost(String host, int port) async {
    try {
      final uri = Uri.parse('http://$host:$port/health');
      final resp = await http.get(uri).timeout(const Duration(seconds: 2));
      // Any HTTP response means the host is reachable (even 404).
      return resp.statusCode > 0;
    } catch (_) {
      try {
        final uri = Uri.parse('http://$host:$port/');
        final resp = await http.get(uri).timeout(const Duration(seconds: 2));
        return resp.statusCode > 0;
      } catch (e) {
        AppLogger.instance.debug('LAN probe failed for $host:$port — $e');
        return false;
      }
    }
  }

  /// Rewrite a media/stream/service URL so a remote camera replaces a LAN host
  /// with the platform mesh IP when [preferVpnHost] is set (issue #8).
  String rewriteUrlForReachability(String url) {
    if (url.isEmpty) return url;
    if (!preferVpnHost) return url;
    final mesh = vpnPlatformTailscaleIp;
    if (mesh == null || mesh.isEmpty) return url;

    final lan = platformLocalIp;
    try {
      final uri = Uri.parse(url);
      final host = uri.host;
      if (host.isEmpty) return url;

      final shouldRewrite = (lan != null && host == lan) ||
          (manualBackendIp.isNotEmpty && host == manualBackendIp) ||
          // Private RFC1918 hosts when we're in remote mode.
          host.startsWith('192.168.') ||
          host.startsWith('10.') ||
          RegExp(r'^172\.(1[6-9]|2\d|3[0-1])\.').hasMatch(host);

      if (!shouldRewrite) return url;
      return uri.replace(host: mesh).toString();
    } catch (_) {
      return url;
    }
  }

  /// Clear authority / VPN metadata (for re-provisioning / reset).
  Future<void> clearVpnMetadata() async {
    await _prefs?.remove(_vpnPrimaryNodeIpKey);
    await _prefs?.remove(_vpnMatrixGroupIdKey);
    await _prefs?.remove(_vpnHeadscaleServerKey);
    await _prefs?.remove(_vpnAuthKeyKey);
    await _prefs?.remove(_apiTokenKey);
    await _prefs?.remove(_vpnPlatformTailscaleIpKey);
    await _prefs?.remove(_vpnPlatformHostnameKey);
    await _prefs?.remove(_platformLocalIpKey);
    await _prefs?.remove(_tailscaleIpKey);
    await _prefs?.remove(_preferVpnKey);
    _preferVpn = false;
    await _prefs?.setBool(_vpnEnrolledKey, false);
    AppLogger.instance.info('VPN metadata cleared');
  }
}
  bool _preferVpn = false;
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'package:tailscale/tailscale.dart';
import 'package:path_provider/path_provider.dart';

/// Manages the embedded Tailscale VPN connection to EyeNet headscale.
///
/// Uses the `tailscale` package which embeds the Tailscale Go client
/// directly in the Flutter app. No separate Tailscale app needed.
class VpnService extends ChangeNotifier {
  static const String _keyAuthKey = 'vpn_auth_key';
  static const String _keyHostname = 'vpn_hostname';
  static const String _keyServerUrl = 'vpn_server_url';
  static const String _keyInstallationUuid = 'vpn_installation_uuid';

  // Configurable defaults — user can change these
  String _authorityUrl = 'https://authority.eyenet-vision.com';
  String _headscaleUrl = 'https://vpn.eyenet-vision.com';
  String _applicationKey = '';
  String _installationUuid = '';
  String _hostname = '';

  // Connection state
  bool _isConnected = false;
  bool _isConnecting = false;
  String? _vpnIp;
  String? _error;
  String? _matrixGroupId;
  bool _initialized = false;

  // Getters
  bool get isConnected => _isConnected;
  bool get isConnecting => _isConnecting;
  String? get vpnIp => _vpnIp;
  String? get error => _error;
  String get authorityUrl => _authorityUrl;
  set authorityUrl(String v) { _authorityUrl = v; notifyListeners(); }
  String get applicationKey => _applicationKey;
  set applicationKey(String v) { _applicationKey = v; notifyListeners(); }
  String get installationUuid => _installationUuid;
  set installationUuid(String v) { _installationUuid = v; notifyListeners(); }
  String get hostname => _hostname;
  set hostname(String v) { _hostname = v; notifyListeners(); }

  /// Initialize the Tailscale client (call once at app startup).
  Future<void> init() async {
    if (_initialized) return;
    try {
      final dir = await getApplicationSupportDirectory();
      final tsDir = '${dir.path}/eyenet-vpn';
      Tailscale.init(stateDir: tsDir);
      _initialized = true;

      // Try to reconnect with stored credentials
      await _loadCredentials();
      if (_applicationKey.isNotEmpty && _installationUuid.isNotEmpty) {
        _connect();
      }
    } catch (e) {
      _error = 'Init failed: $e';
    }
  }

  /// Connect to the EyeNet VPN mesh.
  Future<void> connect() => _connect();

  Future<void> _connect() async {
    if (_isConnecting || _isConnected) return;
    if (!_initialized) {
      _error = 'VPN not initialized. Please restart the app.';
      notifyListeners();
      return;
    }

    _isConnecting = true;
    _error = null;
    notifyListeners();

    try {
      if (_installationUuid.isEmpty || _applicationKey.isEmpty) {
        _error = 'Installation UUID and Application Key are required.\n'
                 'Tap the settings icon to configure them.';
        _isConnecting = false;
        notifyListeners();
        return;
      }

      final controlUrl = Uri.parse(_headscaleUrl);

      // 1. Try reconnecting with the existing WireGuard identity first.
      //    If the state directory already has a valid node keypair, this
      //    preserves the same VPN IP. Only enroll (fetch auth key) when
      //    there is no existing identity or the current one is invalid.
      try {
        await Tailscale.instance.up(
          hostname: _hostname,
          controlUrl: controlUrl,
          timeout: const Duration(seconds: 30),
        );
      } catch (_) {
        // 2. No existing identity — enroll with a fresh pre-auth key.
        final authKey = await _fetchAuthKey();
        if (authKey == null) {
          _error = 'Failed to get enrollment key from authority.\n'
                   'Check your Installation UUID and Application Key.';
          _isConnecting = false;
          notifyListeners();
          return;
        }

        await Tailscale.instance.up(
          hostname: _hostname,
          authKey: authKey,
          controlUrl: controlUrl,
          timeout: const Duration(seconds: 30),
        );
      }

      // 3. Wait for the node to reach 'running' state.
      //    Check current status first — if already running, the stream
      //    subscription below would miss the event (race condition).
      var currentStatus = await Tailscale.instance.status();
      if (currentStatus.state != NodeState.running) {
        debugPrint('[EyeNetVPN] Waiting for running state (current: ${currentStatus.state})');
        await Tailscale.instance.onStateChange
            .firstWhere((s) => s == NodeState.running)
            .timeout(const Duration(seconds: 25));
        currentStatus = await Tailscale.instance.status();
      }
      final status = currentStatus;

      _vpnIp = status.ipv4;

      if (_vpnIp != null && _vpnIp!.isNotEmpty) {
        _isConnected = true;

        // Save credentials for auto-reconnect
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_keyAuthKey, _applicationKey);
        await prefs.setString(_keyHostname, _hostname);
        await prefs.setString(_keyServerUrl, _authorityUrl);
        await prefs.setString(_keyInstallationUuid, _installationUuid);

        // Auto-fetch mesh peers on successful connection
        fetchPeers();
      } else {
        _error = 'Connected but no IP assigned.';
        _isConnected = false;
      }
    } catch (e) {
      debugPrint('[EyeNetVPN] Connection error: $e');
      _error = 'Connection failed: $e';
      _isConnected = false;
      _vpnIp = null;
    } finally {
      _isConnecting = false;
      notifyListeners();
    }
  }

  /// Disconnect from the VPN mesh.
  Future<void> disconnect() async {
    try {
      await Tailscale.instance.down();
    } catch (e) {
      // Ignore
    }
    _isConnected = false;
    _vpnIp = null;
    notifyListeners();
  }

  /// Logout completely (clears stored credentials).
  Future<void> logout() async {
    try {
      await Tailscale.instance.logout();
    } catch (e) {
      // Ignore
    }
    _isConnected = false;
    _vpnIp = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyAuthKey);
    await prefs.remove(_keyInstallationUuid);
    notifyListeners();
  }

  /// Fetch a pre-auth key from the authority VPS.
  Future<String?> _fetchAuthKey() async {
    try {
      final url = Uri.parse(
        '${_authorityUrl}/api/v1/vpn/enroll-installation',
      );
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'installation_uuid': _installationUuid,
          'application_key': _applicationKey,
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return data['auth_key'] as String?;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Peer info for the mesh dashboard.
  List<Map<String, dynamic>> _peers = [];

  List<Map<String, dynamic>> get peers => _peers;

  /// Refresh the list of peers visible to this device.
  /// Calls the authority API which queries all headscale users.
  Future<void> fetchPeers() async {
    if (!_isConnected) return;
    try {
      final url = Uri.parse('${_authorityUrl}/api/v1/vpn/nodes');
      final response = await http.get(url).timeout(
        const Duration(seconds: 10),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final rawNodes = List<Map<String, dynamic>>.from(data['nodes'] ?? []);
        _peers = rawNodes.map((node) => ({
          'hostname': node['hostname'] ?? '',
          'tailscale_ip': node['tailscale_ip'] ?? '',
          'online': node['online'] ?? false,
          'node_id': node['node_id'] ?? '',
        }).toList();
        debugPrint('[EyeNetVPN] Fetched ${_peers.length} peers');
      }
    } catch (e) {
      debugPrint('[EyeNetVPN] Failed to fetch peers: $e');
    }
    notifyListeners();
  }

  /// Delete a node from the VPN mesh via the authority API.
  Future<bool> deleteNode(String nodeId) async {
    try {
      final url = Uri.parse(
        '${_authorityUrl}/api/v1/vpn/nodes/$nodeId',
      );
      final response = await http.delete(url).timeout(
        const Duration(seconds: 15),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[EyeNetVPN] Failed to delete node: $e');
      return false;
    }
  }

  /// Rename a peer node via the authority API.
  Future<bool> renamePeer(String nodeId, String newHostname) async {
    try {
      final url = Uri.parse(
        '${_authorityUrl}/api/v1/vpn/rename-node',
      );
      final response = await http.patch(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'node_id': nodeId,
          'new_hostname': newHostname,
        }),
      ).timeout(const Duration(seconds: 15));
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[EyeNetVPN] Failed to rename peer: $e');
      return false;
    }
  }

  /// Derive a unique hostname from the installation UUID.
  /// Extracts the last meaningful segment and prefixes with 'eyenet-'.
  /// Example: 'nick.glezakos@gmail.com-0' → 'eyenet-nick.glezakos-0'
  static String _deriveHostname(String installationUuid) {
    // Sanitize: replace '@' with '.', strip non-alphanumeric except '.' and '-'
    var sanitized = installationUuid.replaceAll('@', '.');
    sanitized = sanitized.replaceAll(RegExp(r'[^a-zA-Z0-9.\-]'), '');
    // Truncate to reasonable length for DNS compatibility
    if (sanitized.length > 40) {
      sanitized = sanitized.substring(0, 40);
    }
    return 'eyenet-$sanitized';
  }

  /// Load saved credentials from SharedPreferences.
  Future<void> _loadCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    if (_applicationKey.isEmpty) {
      _applicationKey = prefs.getString(_keyAuthKey) ?? '';
    }
    if (_installationUuid.isEmpty) {
      _installationUuid = prefs.getString(_keyInstallationUuid) ?? '';
    }
    // Load saved hostname, or derive one from the installation_uuid
    final savedHostname = prefs.getString(_keyHostname);
    if (savedHostname != null && savedHostname.isNotEmpty) {
      _hostname = savedHostname;
    } else if (_installationUuid.isNotEmpty) {
      _hostname = _deriveHostname(_installationUuid);
    } else {
      _hostname = 'eyenet-android';
    }
  }
}
/// Client for the Node's VPN status endpoint and Authority VPN API.
///
/// Fetches Tailscale enrollment state, VPN IPs, connectivity
/// information from the local node service, and manages mesh peers
/// via the authority VPN API.
library;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/api_client.dart';

class VpnStatus {
  final bool enrolled;
  final bool available;
  final bool hasTailscaleInstalled;
  final bool connectedToOtherServer;
  final String? currentServer;
  final String? expectedServer;
  final String? tailscaleIp;
  final List<String> vpnIps;
  final String? headscaleServer;
  final String? matrixGroupId;
  final int peerCount; // Real peers (excluding self)
  final int onlineCount;
  final String? hostname;

  const VpnStatus({
    required this.enrolled,
    required this.available,
    this.hasTailscaleInstalled = false,
    this.connectedToOtherServer = false,
    this.currentServer,
    this.expectedServer,
    this.tailscaleIp,
    this.vpnIps = const [],
    this.headscaleServer,
    this.matrixGroupId,
    this.peerCount = 0,
    this.onlineCount = 0,
    this.hostname,
  });

  factory VpnStatus.fromJson(Map<String, dynamic> json) {
    final currentServer = json['current_server']?.toString();
    final expectedServer = json['expected_server']?.toString();
    final hasTailscale = json['has_tailscale_installed'] == true;
    final enrolled = json['enrolled'] == true;
    final backendFlag = json['connected_to_other_server'] == true;
    final inferredForeign = hasTailscale &&
        !enrolled &&
        currentServer != null &&
        currentServer.isNotEmpty &&
        !_isEyenetServer(currentServer);

    return VpnStatus(
      enrolled: enrolled,
      available: json['available'] == true,
      hasTailscaleInstalled: hasTailscale,
      connectedToOtherServer: backendFlag || inferredForeign,
      currentServer: currentServer,
      expectedServer: expectedServer,
      tailscaleIp: json['tailscale_ip']?.toString(),
      vpnIps: List<String>.from(json['vpn_ips'] ?? []),
      headscaleServer: json['headscale_server']?.toString(),
      matrixGroupId: json['matrix_group_id']?.toString(),
      peerCount: json['peer_count'] as int? ?? 0,
      onlineCount: json['online_count'] as int? ?? 0,
      hostname: json['hostname']?.toString(),
    );
  }
}

bool _isEyenetServer(String server) {
  return server.toLowerCase().contains('vpn.eyenet-vision.com');
}

class EnrollmentKey {
  final String authKey;
  final String headscaleServer;
  final String? matrixGroupId;
  final String tailscaleUpCommand;
  final bool enrolled;
  final String? tailscaleIp;
  final bool autoEnrollSkipped;
  final String? message;

  const EnrollmentKey({
    required this.authKey,
    required this.headscaleServer,
    this.matrixGroupId,
    required this.tailscaleUpCommand,
    this.enrolled = false,
    this.tailscaleIp,
    this.autoEnrollSkipped = false,
    this.message,
  });

  factory EnrollmentKey.fromJson(Map<String, dynamic> json) {
    return EnrollmentKey(
      authKey: json['auth_key'] as String,
      headscaleServer: json['headscale_server'] as String? ?? 'https://vpn.eyenet-vision.com',
      matrixGroupId: json['matrix_group_id']?.toString(),
      tailscaleUpCommand: json['tailscale_up_command'] as String? ?? '',
      enrolled: json['enrolled'] == true,
      tailscaleIp: json['tailscale_ip']?.toString(),
      autoEnrollSkipped: json['auto_enroll_skipped'] == true,
      message: json['message']?.toString(),
    );
  }
}

/// VPN peer info from the authority API.
class VpnPeerInfo {
  final String nodeId;
  final String hostname;
  final String tailscaleIp;
  final bool online;
  final String? lastSeen;

  const VpnPeerInfo({
    required this.nodeId,
    required this.hostname,
    required this.tailscaleIp,
    required this.online,
    this.lastSeen,
  });

  factory VpnPeerInfo.fromJson(Map<String, dynamic> json) {
    return VpnPeerInfo(
      nodeId: json['node_id']?.toString() ?? '',
      hostname: json['hostname']?.toString() ?? 'Unknown',
      tailscaleIp: json['tailscale_ip']?.toString() ?? '',
      online: json['online'] == true,
      lastSeen: json['last_seen']?.toString(),
    );
  }
}

class VpnStatusClient {
  final ApiClient _apiClient;
  final Dio _nodeClient;
  final Dio _authorityClient;

  static const _authorityBaseUrl = 'https://authority.eyenet-vision.com';

  VpnStatusClient(this._apiClient)
      : _nodeClient = Dio(BaseOptions(
          baseUrl: 'http://localhost:8001',
          connectTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
          headers: {'Content-Type': 'application/json'},
        )),
        _authorityClient = Dio(BaseOptions(
          baseUrl: _authorityBaseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
          headers: {'Content-Type': 'application/json'},
        ));

  Future<VpnStatus> getStatus() async {
    try {
      final response = await _nodeClient.get('/node/vpn/status');
      return VpnStatus.fromJson(
          Map<String, dynamic>.from(response.data as Map));
    } on DioException catch (error) {
      if (error.response?.statusCode == 503 || error.response?.statusCode == 404) {
        return const VpnStatus(enrolled: false, available: false);
      }
      rethrow;
    }
  }

  /// Request a fresh enrollment key from the authority via the node.
  Future<EnrollmentKey> enroll() async {
    final response = await _nodeClient.post('/node/vpn/enroll',
        data: {'node_type': 'platform'});
    return EnrollmentKey.fromJson(Map<String, dynamic>.from(response.data as Map));
  }

  /// Update the node's Tailscale hostname (MagicDNS name).
  /// Uses the node API to update both daemon and headscale atomically.
  Future<Map<String, dynamic>> updateHostname(String newHostname) async {
    final response = await _nodeClient.patch(
      '/node/vpn/hostname',
      data: {'hostname': newHostname},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  /// Disconnect Tailscale (keep identity for reconnect).
  Future<Map<String, dynamic>> disconnect() async {
    final response = await _nodeClient.post('/node/vpn/disconnect');
    return Map<String, dynamic>.from(response.data as Map);
  }

  /// Reconnect Tailscale with existing identity.
  Future<Map<String, dynamic>> connect() async {
    final response = await _nodeClient.post('/node/vpn/connect');
    return Map<String, dynamic>.from(response.data as Map);
  }

  // -----------------------------------------------------------------------
  // Authority VPN API — Peer Management
  // -----------------------------------------------------------------------

  /// Fetch all VPN peers from the node API (same origin, no CORS).
  Future<List<VpnPeerInfo>> fetchPeers() async {
    final response = await _nodeClient.get('/node/vpn/peers');
    final data = Map<String, dynamic>.from(response.data as Map);
    final rawPeers = List<Map<String, dynamic>>.from(data['peers'] ?? []);
    return rawPeers.map((p) => VpnPeerInfo(
      nodeId: (p['ip']?.toString() ?? '').replaceAll('.', ''),
      hostname: p['hostname']?.toString() ?? 'Unknown',
      tailscaleIp: p['ip']?.toString() ?? '',
      online: p['online'] == true,
    )).toList();
  }

  /// Rename a peer node via the authority API.
  Future<Map<String, dynamic>> renamePeer(String nodeId, String newHostname) async {
    final response = await _authorityClient.patch(
      '/api/v1/vpn/rename-node',
      data: {'node_id': nodeId, 'new_hostname': newHostname},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  /// Delete a peer node via the authority API.
  Future<Map<String, dynamic>> deletePeer(String nodeId) async {
    final response = await _authorityClient.delete('/api/v1/vpn/nodes/$nodeId');
    return Map<String, dynamic>.from(response.data as Map);
  }
}

final vpnStatusClientProvider = Provider<VpnStatusClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return VpnStatusClient(apiClient);
});

final vpnStatusProvider = FutureProvider<VpnStatus>((ref) async {
  final client = ref.watch(vpnStatusClientProvider);
  return await client.getStatus();
});

/// Per-OS installation instructions for Tailscale (only when CLI is missing).
String tailscaleInstallGuide(String os) {
  switch (os.toLowerCase()) {
    case 'macos':
    case 'darwin':
      return 'If Tailscale.app is already running, do not brew-install another copy.\n'
          'Use Enroll Now to mint an EyeNet key, then run the userspace daemon command it prints.\n'
          'Only if there is no Tailscale at all:\n'
          'brew install tailscale';
    case 'windows':
    case 'win32':
      return 'winget install tailscale.tailscale\n'
          'Then use Enroll Now. Do not log out of an existing Tailscale mesh.';
    case 'linux':
      return 'curl -fsSL https://tailscale.com/install.sh | sh\n'
          'Then use Enroll Now. Do not log out of an existing Tailscale mesh.';
    default:
      return 'Install Tailscale from https://tailscale.com/download\n'
          'Then use Enroll Now. Do not run tailscale logout if another mesh is in use.';
  }
}

String eyenetUserspaceEnrollGuide({String expectedServer = 'https://vpn.eyenet-vision.com'}) {
  return '# Keep Tailscale.app on its current mesh (lab / Windows access).\n'
      '# Do not run tailscale logout.\n'
      '# Join EyeNet with a second userspace daemon:\n\n'
      'mkdir -p "\$HOME/.eyenet-tailscale"\n'
      'tailscaled --tun=userspace-networking \\\n'
      '  --socket="\$HOME/.eyenet-tailscale/tailscaled.sock" \\\n'
      '  --statedir="\$HOME/.eyenet-tailscale" &\n\n'
      'TS_SOCKET="\$HOME/.eyenet-tailscale/tailscaled.sock" tailscale up \\\n'
      '  --login-server $expectedServer \\\n'
      '  --auth-key <enrollment-key> \\\n'
      '  --accept-routes=false --accept-dns=false\n\n'
      'export EYENET_TS_SOCKET="\$HOME/.eyenet-tailscale/tailscaled.sock"';
}
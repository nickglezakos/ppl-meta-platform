/// Client for the Node's VPN status endpoint.
///
/// Fetches Tailscale enrollment state, VPN IPs, and connectivity
/// information from the local node service.
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
    final connectedToOther =
        hasTailscale && !(json['enrolled'] == true) && currentServer != null && currentServer.isNotEmpty;

    return VpnStatus(
      enrolled: json['enrolled'] == true,
      available: json['available'] == true,
      hasTailscaleInstalled: hasTailscale,
      connectedToOtherServer: connectedToOther,
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

class EnrollmentKey {
  final String authKey;
  final String headscaleServer;
  final String? matrixGroupId;
  final String tailscaleUpCommand;
  final bool enrolled;
  final String? tailscaleIp;

  const EnrollmentKey({
    required this.authKey,
    required this.headscaleServer,
    this.matrixGroupId,
    required this.tailscaleUpCommand,
    this.enrolled = false,
    this.tailscaleIp,
  });

  factory EnrollmentKey.fromJson(Map<String, dynamic> json) {
    return EnrollmentKey(
      authKey: json['auth_key'] as String,
      headscaleServer: json['headscale_server'] as String? ?? 'https://vpn.eyenet-vision.com',
      matrixGroupId: json['matrix_group_id']?.toString(),
      tailscaleUpCommand: json['tailscale_up_command'] as String? ?? '',
      enrolled: json['enrolled'] == true,
      tailscaleIp: json['tailscale_ip']?.toString(),
    );
  }
}

class VpnStatusClient {
  final ApiClient _apiClient;
  final Dio _nodeClient;

  VpnStatusClient(this._apiClient)
      : _nodeClient = Dio(BaseOptions(
          baseUrl: 'http://localhost:8001',
          connectTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
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
    final response = await _nodeClient.post('/node/vpn/enroll');
    return EnrollmentKey.fromJson(Map<String, dynamic>.from(response.data as Map));
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

/// Per-OS installation instructions for Tailscale.
String tailscaleInstallGuide(String os) {
  switch (os.toLowerCase()) {
    case 'macos':
    case 'darwin':
      return 'brew install tailscale && '
          'tailscale up --login-server https://vpn.eyenet-vision.com '
          '--auth-key <your-enrollment-key>';
    case 'windows':
    case 'win32':
      return 'winget install tailscale.tailscale; '
          'tailscale up --login-server https://vpn.eyenet-vision.com '
          '--auth-key <your-enrollment-key>';
    case 'linux':
      return 'curl -fsSL https://tailscale.com/install.sh | sh; '
          'tailscale up --login-server https://vpn.eyenet-vision.com '
          '--auth-key <your-enrollment-key>';
    case 'ios':
      return '1. Install "Tailscale" from the App Store\n'
          '2. Open the app → Settings → Add Account\n'
          '3. Choose "Custom coordination server"\n'
          '4. Enter: https://vpn.eyenet-vision.com\n'
          '5. Paste your enrollment key when prompted';
    case 'android':
      return '1. Install "Tailscale" from Google Play\n'
          '2. Open the app → Settings → Login\n'
          '3. Tap "Use custom coordination server"\n'
          '4. Enter: https://vpn.eyenet-vision.com\n'
          '5. Paste your enrollment key when prompted';
    default:
      return 'Install Tailscale from https://tailscale.com/download\n'
          'Then run: tailscale up --login-server https://vpn.eyenet-vision.com '
          '--auth-key <your-enrollment-key>';
  }
}
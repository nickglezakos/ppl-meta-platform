import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

/// Subset of the Authority VPN enrollment response used by the player.
///
/// Mirrors `EnrollInstallationResponse` in
/// `autonomous/ppl-meta-authority/src/api/vpn.py`.
class AuthorityVpnEnrollment {
  final String authKey;
  final String tailscaleIpRange;
  final String headscaleServer;
  final String matrixGroupId;

  /// Primary platform node Tailscale IP, resolved by the Authority so the player
  /// can do VPN-direct discovery against ppl-meta-discovery.
  final String? primaryNodeIp;
  final List<String> tags;
  final int expiresInSeconds;

  /// HMAC installation token used to authenticate to ppl-meta-discovery (Issue #8).
  final String apiToken;

  /// The client's *assigned* platform (mesh IP, hostname, local LAN IP) so it
  /// knows where to dial after enrollment — over the LAN (local) or the VPN
  /// (mesh) for remote/off-LAN operation.
  final String? platformTailscaleIp;
  final String? platformHostname;
  final String? platformLocalIp;

  AuthorityVpnEnrollment({
    required this.authKey,
    required this.tailscaleIpRange,
    required this.headscaleServer,
    required this.matrixGroupId,
    this.primaryNodeIp,
    required this.tags,
    required this.expiresInSeconds,
    required this.apiToken,
    this.platformTailscaleIp,
    this.platformHostname,
    this.platformLocalIp,
  });

  factory AuthorityVpnEnrollment.fromJson(Map<String, dynamic> json) {
    return AuthorityVpnEnrollment(
      authKey: (json['auth_key'] as String?) ?? '',
      tailscaleIpRange: (json['tailscale_ip_range'] as String?) ?? '',
      headscaleServer: (json['headscale_server'] as String?) ?? '',
      matrixGroupId: (json['matrix_group_id'] as String?) ?? '',
      primaryNodeIp: json['primary_node_ip'] as String?,
      tags: List<String>.from(json['tags'] ?? const []),
      expiresInSeconds: (json['expires_in_seconds'] as int?) ?? 0,
      apiToken: (json['api_token'] as String?) ?? '',
      platformTailscaleIp: json['platform_tailscale_ip'] as String?,
      platformHostname: json['platform_hostname'] as String?,
      platformLocalIp: json['platform_local_ip'] as String?,
    );
  }
}

/// A node in an Authority VPN matrix group (primary node vs. this client).
class AuthorityVpnNode {
  final String nodeId;
  final String hostname;
  final String installationUuid;
  final String? tailscaleIp;
  final bool online;
  final List<String> tags;

  AuthorityVpnNode({
    required this.nodeId,
    required this.hostname,
    required this.installationUuid,
    required this.tailscaleIp,
    required this.online,
    required this.tags,
  });

  bool get isNode => tags.any((t) => t.contains('tag:node'));

  factory AuthorityVpnNode.fromJson(Map<String, dynamic> json) {
    return AuthorityVpnNode(
      nodeId: (json['node_id'] as String?) ?? '',
      hostname: (json['hostname'] as String?) ?? '',
      installationUuid: (json['installation_uuid'] as String?) ?? '',
      tailscaleIp: (json['tailscale_ip'] as String?) ??
          ((json['tailscale_ip'] as num?)?.toString()),
      online: json['online'] as bool? ?? false,
      tags: List<String>.from(json['tags'] ?? const []),
    );
  }

  @override
  String toString() =>
      'AuthorityVpnNode(node_id: $nodeId, hostname: $hostname, '
      'tailscale_ip: $tailscaleIp, online: $online, tags: $tags)';
}

/// Client for the PPL Meta Authority service (`autonomous/ppl-meta-authority`).
///
/// Supplies the VPN metadata (primary node Tailscale IP, matrix group, headscale
/// server, pre-auth key) that the player uses for VPN-direct discovery against
/// `ppl-meta-discovery`.
class AuthorityApiClient {
  final Dio _dio;
  final Logger _logger;
  final String baseUrl;

  AuthorityApiClient({
    required this.baseUrl,
    Logger? logger,
    Dio? dio,
  })  : _logger = logger ?? Logger(),
        _dio = dio ??
            Dio(BaseOptions(
              baseUrl: baseUrl,
              connectTimeout: const Duration(seconds: 5),
              receiveTimeout: const Duration(seconds: 8),
              sendTimeout: const Duration(seconds: 8),
              headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
              },
            ));

  /// Activate the installation (licensing). Returns the activation record.
  Future<Map<String, dynamic>> activate({
    required String applicationKey,
    required String installationUuid,
    required String ownerEmail,
  }) async {
    final response = await _dio.post(
      '/api/v1/installations/activate',
      data: {
        'application_key': applicationKey,
        'installation_uuid': installationUuid,
        'owner_email': ownerEmail,
      },
    );
    _logger.d('Authority activation response: ${response.data}');
    return response.data as Map<String, dynamic>;
  }

  /// Enroll this installation for VPN access and return the enrollment metadata.
  Future<AuthorityVpnEnrollment> enrollInstallation({
    required String applicationKey,
    required String installationUuid,
    String nodeType = 'client',
  }) async {
    final response = await _dio.post(
      '/api/v1/vpn/enroll-installation',
      data: {
        'installation_uuid': installationUuid,
        'application_key': applicationKey,
        'node_type': nodeType,
      },
    );
    _logger.d('Authority enrollment response: ${response.data}');
    return AuthorityVpnEnrollment.fromJson(response.data as Map<String, dynamic>);
  }

  /// Redeem a one-time enrollment token (scenario b) issued by a platform admin
  /// on the network screen. Returns the full VPN enrollment (auth key, headscale
  /// server, matrix group, assigned platform) so the device can self-register its
  /// own mesh node.
  ///
  /// The token is single-use and short-lived; it binds the device to exactly the
  /// mesh/tenant the operator intended.
  Future<AuthorityVpnEnrollment> redeemEnrollmentToken({
    required String token,
    String nodeType = 'signage',
  }) async {
    final response = await _dio.post(
      '/api/v1/vpn/enroll-token',
      data: {
        'token': token.trim(),
        'node_type': nodeType,
      },
    );
    _logger.d('Authority token redemption response: ${response.data}');
    return AuthorityVpnEnrollment.fromJson(response.data as Map<String, dynamic>);
  }

  /// List all VPN nodes in a matrix group (used to locate the primary node and
  /// the player's own Tailscale IP after enrollment).
  Future<List<AuthorityVpnNode>> listMatrixGroupNodes(String matrixGroupId) async {
    final response = await _dio.get('/api/v1/vpn/matrix-groups/$matrixGroupId/nodes');
    final body = response.data as Map<String, dynamic>;
    final nodes = body['nodes'] as List<dynamic>? ?? const [];
    return nodes
        .map((n) => AuthorityVpnNode.fromJson(n as Map<String, dynamic>))
        .toList();
  }

  /// Resolve the primary (node) Tailscale IP for a matrix group, if any.
  Future<String?> resolvePrimaryNodeIp(String matrixGroupId) async {
    final nodes = await listMatrixGroupNodes(matrixGroupId);
    for (final node in nodes) {
      if (node.isNode && node.tailscaleIp != null && node.tailscaleIp!.isNotEmpty) {
        return node.tailscaleIp;
      }
    }
    return null;
  }

  /// Re-resolve this device's assigned platform (local + mesh IP) from the
  /// Authority using the HMAC installation token. One internet round-trip; use it
  /// to refresh the platform's LAN IP when it may have changed (router/DHCP).
  Future<Map<String, dynamic>> resolvePlatform({
    required String installationUuid,
    required String apiToken,
  }) async {
    final response = await _dio.post(
      '/api/v1/vpn/resolve-platform',
      data: {
        'installation_uuid': installationUuid,
        'api_token': apiToken,
      },
    );
    _logger.d('Authority platform resolve response: ${response.data}');
    return response.data as Map<String, dynamic>;
  }

  void dispose() {
    _dio.close();
  }
}

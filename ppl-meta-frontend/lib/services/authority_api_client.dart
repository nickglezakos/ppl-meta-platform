import 'dart:convert';

import 'package:http/http.dart' as http;

/// The VPN enrollment payload returned by the Authority at enrollment time.
///
/// Mirrors `EnrollInstallationResponse` in
/// `autonomous/ppl-meta-authority/src/api/vpn.py`.
class AuthorityVpnEnrollment {
  final String authKey;
  final String tailscaleIpRange;
  final String headscaleServer;
  final String matrixGroupId;
  final String? primaryNodeIp;
  final List<String> tags;
  final int expiresInSeconds;

  /// HMAC installation token used to authenticate to ppl-meta-discovery.
  final String apiToken;

  /// The client's *assigned* platform: mesh IP, hostname, current local LAN IP.
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

/// Client for the online Authority (licensing / VPN mesh).
class AuthorityApiClient {
  final String baseUrl;

  AuthorityApiClient({this.baseUrl = 'https://authority.eyenet-vision.com'});

  /// Redeem a one-time enrollment token minted by a platform admin.
  Future<AuthorityVpnEnrollment> redeemEnrollmentToken({
    required String token,
    String nodeType = 'frontend',
  }) async {
    final resp = await http
        .post(
          Uri.parse('$baseUrl/api/v1/vpn/enroll-token'),
          headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
          body: jsonEncode({'token': token.trim(), 'node_type': nodeType}),
        )
        .timeout(const Duration(seconds: 12));

    if (resp.statusCode != 200) {
      throw Exception('Enrollment failed (HTTP ${resp.statusCode}): ${resp.body}');
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    return AuthorityVpnEnrollment.fromJson(data);
  }

  /// Enroll this installation for VPN access using an application key (licence).
  Future<AuthorityVpnEnrollment> enrollInstallation({
    required String applicationKey,
    required String installationUuid,
    String nodeType = 'frontend',
  }) async {
    final resp = await http
        .post(
          Uri.parse('$baseUrl/api/v1/vpn/enroll-installation'),
          headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
          body: jsonEncode({
            'installation_uuid': installationUuid,
            'application_key': applicationKey,
            'node_type': nodeType,
          }),
        )
        .timeout(const Duration(seconds: 12));

    if (resp.statusCode != 200) {
      throw Exception('Enrollment failed (HTTP ${resp.statusCode}): ${resp.body}');
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    return AuthorityVpnEnrollment.fromJson(data);
  }
}
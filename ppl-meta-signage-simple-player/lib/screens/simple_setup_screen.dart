import 'package:flutter/material.dart';
import 'dart:convert' show jsonDecode, jsonEncode;
import 'package:http/http.dart' as http;
import '../services/config_service.dart';

/// Shared installation auth secret used to ask the discovery service to issue
/// the local HMAC token. Defaults to the dev secret (matching discovery's
/// default) so IDE/CLI builds work out of the box; override per-environment via:
///   `--dart-define=INSTALL_AUTH_SECRET=<your_secret>`
const String _installAuthSecret = String.fromEnvironment(
  'INSTALL_AUTH_SECRET',
  defaultValue: 'ppl-meta-installation-auth-secret-dev',
);

class SimpleSetupScreen extends StatefulWidget {
  final VoidCallback onSetupComplete;

  const SimpleSetupScreen({
    super.key,
    required this.onSetupComplete,
  });

  @override
  State<SimpleSetupScreen> createState() => _SimpleSetupScreenState();
}

class _SimpleSetupScreenState extends State<SimpleSetupScreen> {
  final _backendIPController = TextEditingController(text: '');
  final _portController = TextEditingController(text: '8006');
  final _enrollmentTokenController = TextEditingController(text: '');
  final _manualAuthorityUrlController = TextEditingController(
    text:
        // Default to the public authority for redemption; overridable so a
        // specific licence/VPN authority can be targeted for manual pasted tokens.
        'https://authority.eyenet-vision.com');
  final _formKey = GlobalKey<FormState>();
  
  bool _isLoading = false;
  bool _useEnrollmentToken = true; // token/self-register is the primary path
  String? _errorMessage;
  String? _successMessage;

  String get _manualAuthorityUrl => _manualAuthorityUrlController.text.trim();

  @override
  void dispose() {
    _backendIPController.dispose();
    _portController.dispose();
    _enrollmentTokenController.dispose();
    _manualAuthorityUrlController.dispose();
    super.dispose();
  }

  Future<void> _connectToBackend() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final backendIP = _backendIPController.text.trim();
      final portString = _portController.text.trim();
      final discoveryPort = int.tryParse(portString) ?? 8006;

      print('🔍 Attempting to connect to Discovery Service at $backendIP:$discoveryPort');

      // Save configuration
      final configService = await ConfigService.getInstance();
      await configService.saveBackendUrl(backendIP, portString);
      print('✅ Configuration saved for backend IP: $backendIP:$discoveryPort');

      if (_useEnrollmentToken) {
        // ---- Scenario (b): one-time enrollment token (Both: LAN first, then paste) ----
        var token = _enrollmentTokenController.text.trim();
        String? authorityUrl = _manualAuthorityUrl.trim();
        if (token.isEmpty) {
          // LAN auto-discovery of a freshly-minted token first.
          if (_installAuthSecret.isNotEmpty) {
            final discovered = await _tryLanAutoDiscoveryToken(
              backendIP: backendIP,
              port: discoveryPort,
            );
            if (discovered != null) {
              token = discovered.token;
              if ((discovered.authorityUrl ?? '').isNotEmpty) {
                authorityUrl = discovered.authorityUrl;
              }
            }
          }
        }
        if (token.isEmpty) {
          throw Exception(
            'No one-time enrollment token provided. Paste the token from the '
            'platform network screen (http://$backendIP/#/network), or let LAN '
            'auto-discovery find it.',
          );
        }
        if (authorityUrl == null || authorityUrl.isEmpty) {
          // Fall back to the configured/default authority URL.
          authorityUrl = configService.authorityServiceUrl;
        }
        await _redeemEnrollmentToken(
          token: token,
          authorityUrl: authorityUrl,
        );
        print('🔐 Enrollment via one-time token complete');
        setState(() {
          _successMessage = 'Enrolled with one-time token. VPN credentials saved.';
        });
      } else {
        // ---- Local onboarding (Option 1): HMAC token from discovery ----
        if (_installAuthSecret.isEmpty) {
          throw Exception(
            'Installation auth secret not configured. Rebuild with '
            '--dart-define=INSTALL_AUTH_SECRET=<secret>.',
          );
        }
        final enrollment = await _fetchLocalToken(
          enrollKey: _installAuthSecret,
          uuid: '', // blank -> server generates a stable signage-<uuid>
          discoveryUrl: configService.discoveryServiceUrl,
        );

        await configService.saveAuthorityCredentials(
          applicationKey: '',
          installationUuid: enrollment.uuid,
        );
        await configService.saveVpnMetadata(apiToken: enrollment.token);
        print('🔐 Token issued by local discovery (Option 1)');
        setState(() {
          _successMessage =
              'Configuration saved. Local token issued by discovery.';
        });
      }

      // Wait a moment to show success message
      await Future.delayed(const Duration(seconds: 1));

      // Call the completion callback to proceed
      widget.onSetupComplete();
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection failed: $e';
      });
      print('❌ Setup failed: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  /// Option 1 flow: ask the local discovery service to issue an HMAC
  /// installation token bound to the given installation UUID (or one the server
  /// generates when blank). Verified server-side against
  /// INSTALLATION_AUTH_SECRET via the `X-Enroll-Key` header.
  Future<({String uuid, String token})> _fetchLocalToken({
    required String enrollKey,
    required String uuid,
    required String discoveryUrl,
  }) async {
    final resp = await http
        .post(
          Uri.parse('$discoveryUrl/api/v1/device-enroll'),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Enroll-Key': enrollKey,
          },
          body: jsonEncode({'installation_uuid': uuid}),
        )
        .timeout(const Duration(seconds: 8));

    if (resp.statusCode != 200) {
      if (resp.statusCode == 401) {
        throw Exception(
          'Invalid install auth secret (401). It must match the discovery '
          'service\'s INSTALLATION_AUTH_SECRET.',
        );
      }
      throw Exception(
        'Device enrollment failed (HTTP ${resp.statusCode}): ${resp.body}',
      );
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    final returnedUuid = (data['installation_uuid'] as String?) ?? uuid;
    final token = data['api_token'] as String? ?? '';
    if (token.isEmpty) {
      throw Exception('Device enrollment returned no token.');
    }
    return (uuid: returnedUuid, token: token);
  }

  /// Scenario (b): redeem a one-time enrollment token minted by a platform admin
  /// on the network screen (`http://<platform>/#/network`). The Authority returns
  /// the full VPN enrollment (auth key, headscale server, matrix group, assigned
  /// platform); we persist it so the app can self-register its own mesh node.
  Future<void> _redeemEnrollmentToken({
    required String token,
    required String authorityUrl,
  }) async {
    final resp = await http
        .post(
          Uri.parse('$authorityUrl/api/v1/vpn/enroll-token'),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: jsonEncode({'token': token.trim(), 'node_type': 'signage'}),
        )
        .timeout(const Duration(seconds: 12));

    if (resp.statusCode != 200) {
      throw Exception(
        'Enrollment token rejected (HTTP ${resp.statusCode}): ${resp.body}',
      );
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;

    final configService = await ConfigService.getInstance();
    await configService.saveAuthorityCredentials(
      applicationKey: '',
      // The HMAC api_token is derived from the installation's REAL UUID, not the
      // matrix group id — persist it so discovery registration authenticates.
      installationUuid: (data['installation_uuid'] as String?) ?? '',
    );
    await configService.saveVpnMetadata(
      primaryNodeIp: data['primary_node_ip'] as String?,
      matrixGroupId: data['matrix_group_id'] as String?,
      headscaleServer: data['headscale_server'] as String?,
      authKey: data['auth_key'] as String?,
      apiToken: data['api_token'] as String?,
      platformTailscaleIp: data['platform_tailscale_ip'] as String?,
      platformHostname: data['platform_hostname'] as String?,
      platformLocalIp: data['platform_local_ip'] as String?,
    );
    print('🔐 Enrollment token redeemed — VPN credentials saved');
  }

  /// LAN auto-discovery: attempt to fetch a freshly-generated one-time enrollment
  /// token from the platform's network screen helper endpoint, along with the
  /// Authority URL to redeem it against. Returns null when the platform does not
  /// expose one yet (the operator then pastes a token manually).
  ///
  /// When no backend IP is typed (empty), it probes localhost and the LAN gateway
  /// so onboarding does not depend on manually entering the platform IP.
  Future<({String token, String? authorityUrl})?> _tryLanAutoDiscoveryToken({
    required String backendIP,
    required int port,
  }) async {
    final hostCandidates = <String>{};
    if (backendIP.isNotEmpty) {
      hostCandidates.add(backendIP);
    } else {
      // No backend IP entered: try the loopback + likely LAN gateway addresses.
      hostCandidates.add('127.0.0.1');
      hostCandidates.add('192.168.1.1');
      hostCandidates.add('192.168.0.1');
      hostCandidates.add('10.0.0.1');
    }
    for (final host in hostCandidates) {
      final candidates = [
        'http://$host:$port/api/v1/network/enroll-token',
        'http://$host:$port/api/v1/enroll-token',
        'http://$host:$port/enroll-token',
      ];
      for (final url in candidates) {
        try {
          final resp = await http
              .get(
                Uri.parse(url),
                headers: {
                  'Accept': 'application/json',
                  'X-Enroll-Key': _installAuthSecret,
                },
              )
              .timeout(const Duration(seconds: 3));
          if (resp.statusCode == 200) {
            final data = jsonDecode(resp.body) as Map<String, dynamic>;
            final token = (data['token'] as String?)?.trim();
            if (token != null && token.isNotEmpty) {
              print('🔍 LAN auto-discovery found enrollment token at $url');
              return (
                token: token,
                authorityUrl: data['authority_base_url'] as String?,
              );
            }
          }
        } catch (_) {
          // Continue probing.
        }
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Backend Setup'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // App Title
                const Icon(
                  Icons.settings_remote,
                  size: 80,
                  color: Colors.blue,
                ),
                const SizedBox(height: 24),
                const Text(
                  'PPL Meta Signage',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Simple Player',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 20,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 48),

                // Primary: self-register via one-time enrollment token (VPN-first).
                // LAN auto-discovery is tried first; a token can be pasted as fallback.
                SwitchListTile(
                  value: _useEnrollmentToken,
                  onChanged: _isLoading
                      ? null
                      : (v) => setState(() => _useEnrollmentToken = v),
                  title: const Text('Join the VPN mesh (enrollment token)'),
                  subtitle: const Text(
                    'Recommended. The device auto-discovers its message token on '
                    'your network and self-registers its own mesh node.',
                  ),
                ),
                if (_useEnrollmentToken) ...[
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _enrollmentTokenController,
                    decoration: const InputDecoration(
                      labelText: 'One-time enrollment token (optional)',
                      hintText: 'hsent-... — leave blank to auto-discover on LAN',
                      prefixIcon: Icon(Icons.vpn_key),
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _manualAuthorityUrlController,
                    decoration: const InputDecoration(
                      labelText: 'Authority URL',
                      hintText: 'https://authority.eyenet-vision.com',
                      prefixIcon: Icon(Icons.dns),
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],

                const SizedBox(height: 16),

                // Advanced / fallback: legacy local-discovery LAN fields.
                // Kept (collapsed) so setups without LAN/VPN auto-discovery can
                // still point at a backend host and use local device-enroll.
                ExpansionTile(
                  title: const Text('Advanced (local discovery)'),
                  subtitle: const Text('Backend IP + discovery port + use local discovery.'),
                  leading: const Icon(Icons.tune),
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: const EdgeInsets.only(top: 8),
                  children: [
                    if (_useEnrollmentToken) ...[
                      const SizedBox(height: 8),
                      Text(
                        'Used only as the network anchor when auto-discovery on '
                        'this network is unavailable. For VPN onboarding, just '
                        'press Connect above.',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                      ),
                      const SizedBox(height: 12),
                    ],
                    TextFormField(
                      controller: _backendIPController,
                      decoration: const InputDecoration(
                        labelText: 'Backend IP Address',
                        hintText: 'e.g., 192.168.1.100',
                        prefixIcon: Icon(Icons.computer),
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Please enter backend IP address';
                        }
                        final parts = value.trim().split('.');
                        if (parts.length != 4) {
                          return 'Invalid IP address format';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _portController,
                      decoration: const InputDecoration(
                        labelText: 'Discovery Service Port',
                        hintText: '8006',
                        prefixIcon: Icon(Icons.settings_ethernet),
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Please enter port number';
                        }
                        final port = int.tryParse(value.trim());
                        if (port == null || port < 1 || port > 65535) {
                          return 'Invalid port number';
                        }
                        return null;
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Connect Button
                ElevatedButton(
                  onPressed: _isLoading ? null : _connectToBackend,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Text(
                          'Connect',
                          style: TextStyle(fontSize: 18),
                        ),
                ),

                // Error Message
                if (_errorMessage != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      border: Border.all(color: Colors.red.shade300),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.error_outline, color: Colors.red.shade700),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: TextStyle(color: Colors.red.shade700),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                // Success Message
                if (_successMessage != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.green.shade50,
                      border: Border.all(color: Colors.green.shade300),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle_outline, color: Colors.green.shade700),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _successMessage!,
                            style: TextStyle(color: Colors.green.shade700),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 24),
                const Text(
                  'Enter the IP address of your backend server and the discovery service port (default: 8006)',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

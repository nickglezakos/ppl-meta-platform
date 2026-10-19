import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/auth/auth_service.dart';
import '../../services/authority_api_client.dart';
import '../../services/platform_config_service.dart';
import '../../services/simplified_discovery_client.dart';
import '../../services/tailscale_service.dart';
import '../enroll/enroll_gate.dart';

/// Plan A setup: LAN Discovery or VPN enrollment token, then local login.
class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _backendIp = TextEditingController();
  final _port = TextEditingController(text: '8006');
  final _username = TextEditingController();
  final _password = TextEditingController();
  final _enrollmentToken = TextEditingController();

  bool _joinVpn = false;
  bool _loading = false;
  bool _obscurePassword = true;
  String? _error;
  String? _enrollmentMessage;
  String? _status;

  @override
  void dispose() {
    _backendIp.dispose();
    _port.dispose();
    _username.dispose();
    _password.dispose();
    _enrollmentToken.dispose();
    super.dispose();
  }

  String _friendlyError(Object e, {required String action, String? target}) {
    if (e is TimeoutException) {
      final where = target == null || target.isEmpty ? '' : ' ($target)';
      return '$action timed out$where. Check Wi‑Fi / VPN mesh, Discovery port 8006, and that the EyeNet PC is online.';
    }
    final raw = e.toString();
    if (raw.contains('Future not completed') || raw.contains('TimeoutException')) {
      final where = target == null || target.isEmpty ? '' : ' ($target)';
      return '$action timed out$where. Check Wi‑Fi / VPN mesh, Discovery port 8006, and that the EyeNet PC is online.';
    }
    return '$action failed: $e';
  }

  Future<void> _redeemVpn() async {
    final token = _enrollmentToken.text.trim();
    if (token.isEmpty) {
      setState(() => _enrollmentMessage = 'Enter the enrollment token from Network.');
      return;
    }
    setState(() {
      _loading = true;
      _enrollmentMessage = null;
      _error = null;
      _status = 'Redeeming enrollment token…';
    });
    try {
      final config = await PlatformConfigService.getInstance();
      final client = AuthorityApiClient(baseUrl: config.authorityServiceUrl);
      final enrollment = await client
          .redeemEnrollmentToken(
            token: token,
            nodeType: 'mobile',
          )
          .timeout(const Duration(seconds: 30));
      await config.saveVpnMetadata(
        authKey: enrollment.authKey,
        headscaleServer: enrollment.headscaleServer,
        matrixGroupId: enrollment.matrixGroupId,
        primaryNodeIp: enrollment.primaryNodeIp,
        apiToken: enrollment.apiToken,
        platformTailscaleIp: enrollment.platformTailscaleIp,
        platformHostname: enrollment.platformHostname,
        platformLocalIp: enrollment.platformLocalIp,
      );
      if (mounted) {
        setState(() => _status = 'Bringing up VPN mesh (can take up to ~90s)…');
      }
      final tailscale = TailscaleService(config: config);
      await tailscale.initialize();
      if (mounted) {
        setState(() => _status = 'Checking platform reachability…');
      }
      await config.ensurePlatformReachable();
      setState(() {
        _backendIp.text = config.platformHost;
        _port.text = '${PlatformConfigService.discoveryPort}';
        _enrollmentMessage =
            'Joined VPN mesh at ${config.platformHost}. Sign in below.';
        _status = null;
      });
    } catch (e) {
      setState(() {
        _enrollmentMessage = _friendlyError(
          e,
          action: 'VPN enrollment',
          target: 'authority / mesh',
        );
        _status = null;
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<List<ServiceInfo>> _discoverWithFallback({
    required PlatformConfigService config,
    required SimplifiedDiscoveryClient discovery,
    required String primaryHost,
    required String portStr,
  }) async {
    final tried = <String>{};
    Future<List<ServiceInfo>> attempt(String host) async {
      tried.add(host);
      if (mounted) {
        setState(() => _status = 'Discovering services at $host:$portStr…');
      }
      return discovery.discoverServicesAtAddress('$host:$portStr');
    }

    try {
      return await attempt(primaryHost);
    } on TimeoutException {
      // LAN IP often fails off-LAN; retry mesh IP when enrolled.
      final mesh = config.vpnPlatformTailscaleIp;
      if (mesh != null &&
          mesh.isNotEmpty &&
          !tried.contains(mesh) &&
          mesh != primaryHost) {
        await config.markLanUnreachable();
        return attempt(mesh);
      }
      rethrow;
    } catch (e) {
      final raw = e.toString();
      final looksTimeout = raw.contains('Future not completed') ||
          raw.contains('TimeoutException') ||
          raw.contains('Failed host lookup') ||
          raw.contains('Connection refused') ||
          raw.contains('Network is unreachable');
      final mesh = config.vpnPlatformTailscaleIp;
      if (looksTimeout &&
          mesh != null &&
          mesh.isNotEmpty &&
          !tried.contains(mesh) &&
          mesh != primaryHost) {
        await config.markLanUnreachable();
        return attempt(mesh);
      }
      rethrow;
    }
  }

  Future<void> _connectAndLogin() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
      _status = 'Preparing…';
    });
    try {
      final config = await PlatformConfigService.getInstance();

      // If already enrolled, resolve LAN vs mesh before Discovery.
      if (config.vpnEnrolled ||
          (config.vpnPlatformTailscaleIp != null &&
              config.vpnPlatformTailscaleIp!.isNotEmpty)) {
        if (mounted) {
          setState(() => _status = 'Resolving platform host (LAN / VPN)…');
        }
        await config.ensurePlatformReachable().timeout(
              const Duration(seconds: 25),
            );
      }

      String host;
      String portStr;
      if (config.vpnEnrolled ||
          (config.vpnPlatformTailscaleIp != null &&
              config.vpnPlatformTailscaleIp!.isNotEmpty)) {
        host = config.platformHost;
        portStr = '${PlatformConfigService.discoveryPort}';
        if (mounted) {
          setState(() {
            _backendIp.text = host;
            _port.text = portStr;
          });
        }
      } else {
        host = _backendIp.text.trim();
        portStr = _port.text.trim();
      }

      final discovery = SimplifiedDiscoveryClient();
      final services = await _discoverWithFallback(
        config: config,
        discovery: discovery,
        primaryHost: host,
        portStr: portStr,
      );
      final gatewayMatches =
          services.where((s) => s.name == 'ppl-meta-gateway');
      final nodeMatches = services.where((s) => s.name == 'ppl-meta-node');
      if (gatewayMatches.isEmpty && nodeMatches.isEmpty) {
        throw Exception('Gateway/node not found via Discovery at $host:$portStr');
      }
      final gateway = gatewayMatches.isEmpty ? null : gatewayMatches.first;
      final node = nodeMatches.isEmpty ? null : nodeMatches.first;
      var loginHost = gateway?.host ?? node!.host;
      final loginPort = gateway?.port ?? 8080;

      // When remote, rewrite private LAN hosts from discovery to mesh IP.
      if (config.preferVpnHost ||
          (config.vpnPlatformTailscaleIp != null &&
              (loginHost.startsWith('192.168.') ||
                  loginHost.startsWith('10.') ||
                  RegExp(r'^172\.(1[6-9]|2\d|3[0-1])\.').hasMatch(loginHost)))) {
        final mesh = config.vpnPlatformTailscaleIp;
        if (mesh != null && mesh.isNotEmpty) {
          loginHost = mesh;
        }
      }

      final loginUrl = 'http://$loginHost:$loginPort';
      if (!mounted) return;
      setState(() => _status = 'Signing in at $loginHost:$loginPort…');

      final auth = context.read<AuthService>();
      await auth.login(
        serverUrl: loginUrl,
        username: _username.text.trim(),
        password: _password.text,
      );

      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const EnrollGate()),
      );
    } catch (e) {
      setState(() {
        _error = _friendlyError(
          e,
          action: 'Connection',
          target: _backendIp.text.trim().isEmpty
              ? null
              : '${_backendIp.text.trim()}:${_port.text.trim()}',
        );
        _status = null;
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('EyeNet Authenticator'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 8),
                Center(
                  child: Image.asset(
                    'assets/images/eyenet-logo.png',
                    height: 120,
                    errorBuilder: (context, error, stackTrace) {
                      return Icon(Icons.visibility, size: 120, color: primary);
                    },
                  ),
                ),
                const SizedBox(height: 12),
                Center(
                  child: Text(
                    'Authenticator',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: primary,
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  'Connect to your local EyeNet platform',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  'LAN: enter Discovery host and port. Remote: join VPN mesh with a Network enrollment token, then sign in with your local account.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 20),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Join VPN mesh (enrollment token)'),
                  value: _joinVpn,
                  onChanged: _loading
                      ? null
                      : (v) => setState(() => _joinVpn = v),
                ),
                if (_joinVpn) ...[
                  TextFormField(
                    controller: _enrollmentToken,
                    decoration: const InputDecoration(
                      labelText: 'Enrollment token',
                      prefixIcon: Icon(Icons.vpn_key),
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: _loading ? null : _redeemVpn,
                    child: const Text('Join VPN Mesh'),
                  ),
                  if (_enrollmentMessage != null) ...[
                    const SizedBox(height: 8),
                    Text(_enrollmentMessage!),
                  ],
                  const SizedBox(height: 16),
                ],
                TextFormField(
                  controller: _backendIp,
                  decoration: const InputDecoration(
                    labelText: 'Backend / Discovery IP',
                    prefixIcon: Icon(Icons.computer),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _port,
                  decoration: const InputDecoration(
                    labelText: 'Discovery port',
                    prefixIcon: Icon(Icons.settings_ethernet),
                  ),
                  keyboardType: TextInputType.number,
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _username,
                  decoration: const InputDecoration(
                    labelText: 'Username / email',
                    prefixIcon: Icon(Icons.person),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _password,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: 'Local password',
                    prefixIcon: const Icon(Icons.lock),
                    suffixIcon: IconButton(
                      tooltip: _obscurePassword ? 'Show password' : 'Hide password',
                      onPressed: () => setState(() {
                        _obscurePassword = !_obscurePassword;
                      }),
                      icon: Icon(
                        _obscurePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                    ),
                  ),
                  validator: (v) =>
                      (v == null || v.isEmpty) ? 'Required' : null,
                ),
                if (_status != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _status!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _error!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _loading ? null : _connectAndLogin,
                  child: _loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Sign in'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

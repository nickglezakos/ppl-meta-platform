import 'package:flutter/material.dart';

import '../../../services/platform_connectivity_service.dart';
import '../../../core/config/platform_config_service.dart';
import '../../../services/authority_api_client.dart';

/// Clean implementation of the platform connection setup screen.
/// Primary path: VPN Mesh Enrollment Token (recommended).
/// Legacy path: Direct LAN connection (collapsed).
class PlatformConnectionSetupScreen extends StatefulWidget {
  final VoidCallback onSetupComplete;

  const PlatformConnectionSetupScreen({
    super.key,
    required this.onSetupComplete,
  });

  @override
  State<PlatformConnectionSetupScreen> createState() =>
      _PlatformConnectionSetupScreenState();
}

class _PlatformConnectionSetupScreenState
    extends State<PlatformConnectionSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _backendController = TextEditingController();
  final _portController = TextEditingController(text: '8006');
  final _enrollmentTokenController = TextEditingController();

  bool _isLoading = false;
  bool _isEnrolling = false;
  String? _errorMessage;
  String? _successMessage;
  String? _enrollmentMessage;

  @override
  void dispose() {
    _backendController.dispose();
    _portController.dispose();
    _enrollmentTokenController.dispose();
    super.dispose();
  }
  // ========================================================================
  // PRIMARY PATH: VPN Mesh Enrollment Token
  // ========================================================================
  Future<void> _redeemEnrollmentToken() async {
    final token = _enrollmentTokenController.text.trim();
    if (token.isEmpty) {
      setState(() => _enrollmentMessage = 'Please enter the enrollment token.');
      return;
    }

    setState(() {
      _isEnrolling = true;
      _enrollmentMessage = null;
      _errorMessage = null;
    });

    try {
      final platformConfig = await PlatformConfigService.getInstance();
      final client = AuthorityApiClient(baseUrl: platformConfig.authorityServiceUrl);

      final enrollment = await client.redeemEnrollmentToken(
        token: token,
        nodeType: 'frontend',
      );

      await platformConfig.saveVpnMetadata(
        authKey: enrollment.authKey,
        headscaleServer: enrollment.headscaleServer,
        matrixGroupId: enrollment.matrixGroupId,
        primaryNodeIp: enrollment.primaryNodeIp,
        apiToken: enrollment.apiToken,
        platformTailscaleIp: enrollment.platformTailscaleIp,
        platformHostname: enrollment.platformHostname,
        platformLocalIp: enrollment.platformLocalIp,
      );

      await platformConfig.ensurePlatformReachable();
      final resolvedHost = platformConfig.platformHost;

      final connectivityService = await PlatformConnectivityService.getInstance();
      await connectivityService.saveConfiguration(
        backendInput: resolvedHost,
        discoveryPort: PlatformConfigService.discoveryPort,
      );
      await connectivityService.applyRuntimeConfiguration();

      setState(() {
        _enrollmentMessage =
            'Joined VPN mesh. Connected to platform at $resolvedHost.';
        _backendController.text = resolvedHost;
        _portController.text = '${PlatformConfigService.discoveryPort}';
      });

      await Future.delayed(const Duration(milliseconds: 800));
      if (mounted) {
        widget.onSetupComplete();
      }
    } catch (e) {
      setState(() => _enrollmentMessage = 'Enrollment failed: $e');
    } finally {
      if (mounted) {
        setState(() => _isEnrolling = false);
      }
    }
  }

  // ========================================================================
  // LEGACY PATH: Direct LAN Connection
  // ========================================================================
  Future<void> _connect() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final service = await PlatformConnectivityService.getInstance();
      final backendInput = _backendController.text.trim();
      final port = int.parse(_portController.text.trim());

      final isReachable = await service.testDiscoveryConnection(
        backendInput: backendInput,
        discoveryPort: port,
      );

      if (!isReachable) {
        setState(() {
          _errorMessage =
              'Could not reach Discovery Service at $backendInput:$port.';
        });
        return;
      }

      final saved = await service.saveConfiguration(
        backendInput: backendInput,
        discoveryPort: port,
      );

      if (!saved) {
        setState(() {
          _errorMessage = 'Failed to save configuration.';
        });
        return;
      }

      await service.applyRuntimeConfiguration();

      setState(() {
        _successMessage = 'Connected successfully. Continuing...';
      });

      await Future.delayed(const Duration(milliseconds: 600));
      if (mounted) {
        widget.onSetupComplete();
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Connect to Platform'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.settings_ethernet, size: 64),
                  const SizedBox(height: 16),
                  const Text(
                    'Connect to Platform',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Choose how you want to connect to your EyeNet platform.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),

                  // ========== PRIMARY: VPN Mesh Token ==========
                  const Divider(),
                  const SizedBox(height: 12),
                  Row(
                    children: const [
                      Icon(Icons.vpn_lock, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Join the VPN mesh (recommended)',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Paste the one-time enrollment token from the platform\'s Network screen.',
                    style: TextStyle(fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _enrollmentTokenController,
                    decoration: const InputDecoration(
                      labelText: 'One-time enrollment token',
                      hintText: 'Paste token from the platform admin screen',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.key),
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_enrollmentMessage != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.green.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.green.shade200),
                      ),
                      child: Text(
                        _enrollmentMessage!,
                        style: TextStyle(color: Colors.green.shade800),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  ElevatedButton.icon(
                    onPressed: _isEnrolling ? null : _redeemEnrollmentToken,
                    icon: _isEnrolling
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.link),
                    label: Text(_isEnrolling ? 'Joining…' : 'Join VPN Mesh'),
                  ),

                  // ========== LEGACY: Direct LAN (collapsed) ==========
                  ExpansionTile(
                    title: const Text('Direct LAN connection (legacy)'),
                    subtitle: const Text(
                        'Only use if you cannot obtain an enrollment token'),
                    leading: const Icon(Icons.settings_ethernet),
                    initiallyExpanded: false,
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16.0),
                        child: Column(
                          children: [
                            TextFormField(
                              controller: _backendController,
                              decoration: const InputDecoration(
                                labelText: 'Platform Host or IP',
                                hintText: 'e.g. 192.168.1.100',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.computer),
                              ),
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return 'Please enter a host or IP';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 16),
                            TextFormField(
                              controller: _portController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Discovery Service Port',
                                hintText: '8006',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.numbers),
                              ),
                              validator: (value) {
                                final port = int.tryParse(value?.trim() ?? '');
                                if (port == null || port < 1 || port > 65535) {
                                  return 'Enter a valid port (1-65535)';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 24),
                            ElevatedButton(
                              onPressed: _isLoading ? null : _connect,
                              style: ElevatedButton.styleFrom(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 14),
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                          strokeWidth: 2),
                                    )
                                  : const Text('Connect via LAN'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 24),

                  if (_errorMessage != null) ...[
                    Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.redAccent),
                      textAlign: TextAlign.center,
                    ),
                  ],
                  if (_successMessage != null) ...[
                    Text(
                      _successMessage!,
                      style: const TextStyle(color: Colors.green),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
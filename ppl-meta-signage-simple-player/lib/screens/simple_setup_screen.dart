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
  final _formKey = GlobalKey<FormState>();
  
  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;

  @override
  void dispose() {
    _backendIPController.dispose();
    _portController.dispose();
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
      final port = _portController.text.trim();

      if (_installAuthSecret.isEmpty) {
        throw Exception(
          'Installation auth secret not configured. Rebuild with '
          '--dart-define=INSTALL_AUTH_SECRET=<secret>.',
        );
      }

      print('🔍 Attempting to connect to Discovery Service at $backendIP:$port');

      // Save configuration
      final configService = await ConfigService.getInstance();
      await configService.saveBackendUrl(backendIP, port);

      print('✅ Configuration saved for backend IP: $backendIP:$port');

      // Local onboarding (Option 1): ask the local discovery service to issue the
      // HMAC token using the build-time secret. No remote Authority round-trip.
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

                // Backend IP Input
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
                    // Basic IP validation
                    final parts = value.trim().split('.');
                    if (parts.length != 4) {
                      return 'Invalid IP address format';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),

                // Port Input
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

                const SizedBox(height: 32),

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

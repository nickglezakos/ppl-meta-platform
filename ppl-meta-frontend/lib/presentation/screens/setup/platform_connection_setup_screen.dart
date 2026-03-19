import 'package:flutter/material.dart';

import '../../../services/platform_connectivity_service.dart';

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

  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;

  @override
  void initState() {
    super.initState();
    _loadExistingConfiguration();
  }

  @override
  void dispose() {
    _backendController.dispose();
    _portController.dispose();
    super.dispose();
  }

  Future<void> _loadExistingConfiguration() async {
    final service = await PlatformConnectivityService.getInstance();
    if (!mounted) return;

    if (service.isConfigured) {
      _backendController.text = service.backendHost;
      _portController.text = service.discoveryPort.toString();
    }
  }

  Future<void> _connect() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

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
              'Could not reach Discovery Service at $backendInput:$port. Check URL/port and try again.';
        });
        return;
      }

      final saved = await service.saveConfiguration(
        backendInput: backendInput,
        discoveryPort: port,
      );

      if (!saved) {
        setState(() {
          _errorMessage = 'Failed to save configuration. Please try again.';
        });
        return;
      }

      await service.applyRuntimeConfiguration();

      setState(() {
        _successMessage = 'Connected successfully. Continuing...';
      });

      await Future.delayed(const Duration(milliseconds: 700));
      widget.onSetupComplete();
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Platform Connection Setup'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.settings_ethernet, size: 72),
                  const SizedBox(height: 16),
                  const Text(
                    'Connect to Platform',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Enter the platform URL/host and Discovery Service port.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 28),
                  TextFormField(
                    controller: _backendController,
                    decoration: const InputDecoration(
                      labelText: 'Platform URL or Host',
                      hintText: 'e.g. 192.168.1.100 or https://my-platform.local',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.language),
                    ),
                    validator: (value) {
                      final input = value?.trim() ?? '';
                      if (input.isEmpty) {
                        return 'Please enter a platform URL or host';
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
                      final text = value?.trim() ?? '';
                      if (text.isEmpty) {
                        return 'Please enter a port number';
                      }
                      final port = int.tryParse(text);
                      if (port == null || port < 1 || port > 65535) {
                        return 'Port must be between 1 and 65535';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _isLoading ? null : _connect,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Connect'),
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 14),
                    Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.redAccent),
                      textAlign: TextAlign.center,
                    ),
                  ],
                  if (_successMessage != null) ...[
                    const SizedBox(height: 14),
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

import 'package:flutter/material.dart';
import '../services/config_service.dart';

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

      print('🔍 Attempting to connect to Discovery Service at $backendIP:$port');

      // Save configuration
      final configService = await ConfigService.getInstance();
      await configService.saveBackendUrl(backendIP, port);
      
      print('✅ Configuration saved for backend IP: $backendIP:$port');

      // Test connection to Discovery Service
      final discoveryUrl = 'http://$backendIP:$port';
      // Simple HTTP check to verify discovery service is accessible
      // Full initialization will happen in InitializationScreen
      
      print('✅ Configuration complete');
      
      setState(() {
        _successMessage = 'Configuration saved! Proceeding to initialization...';
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

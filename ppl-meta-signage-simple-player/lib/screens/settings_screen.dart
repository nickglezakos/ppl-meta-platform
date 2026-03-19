import 'package:flutter/material.dart';
import '../services/config_service.dart';

/// Settings screen for configuring backend connection
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  final _backendIPController = TextEditingController();
  final _discoveryPortController = TextEditingController(text: '8006');
  
  bool _isLoading = false;
  String? _errorMessage;
  ConfigService? _configService;

  @override
  void initState() {
    super.initState();
    _loadCurrentConfig();
  }

  Future<void> _loadCurrentConfig() async {
    _configService = await ConfigService.getInstance();
    setState(() {
      _backendIPController.text = _configService!.backendIP;
      _discoveryPortController.text = _configService!.discoveryPort.toString();
    });
  }

  Future<void> _saveConfiguration() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final backendIP = _backendIPController.text.trim();
      final discoveryPort = int.parse(_discoveryPortController.text.trim());

      final success = await _configService!.saveConfiguration(
        backendIP: backendIP,
        discoveryPort: discoveryPort,
      );

      if (success) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('✅ Configuration saved! Please restart the app.'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 3),
            ),
          );
          Navigator.of(context).pop(true); // Return true to indicate config changed
        }
      } else {
        setState(() {
          _errorMessage = 'Failed to save configuration';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Error: $e';
      });
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
        title: const Text('Settings'),
        backgroundColor: Colors.blue,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Instructions
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.info_outline, color: Colors.blue),
                        SizedBox(width: 8),
                        Text(
                          'Backend Configuration',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 12),
                    Text('1. Find your Mac/Server IP address (e.g., 192.168.1.100)'),
                    SizedBox(height: 4),
                    Text('2. Ensure PPL Meta services are running'),
                    SizedBox(height: 4),
                    Text('3. Both devices must be on the same network'),
                    SizedBox(height: 4),
                    Text('4. Discovery service runs on port 8006 by default'),
                  ],
                ),
              ),
              
              const SizedBox(height: 32),
              
              // Backend IP Input
              TextFormField(
                controller: _backendIPController,
                decoration: const InputDecoration(
                  labelText: 'Backend IP Address *',
                  hintText: 'e.g., 192.168.1.100',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.computer),
                  helperText: 'IP address of the machine running PPL Meta services',
                ),
                keyboardType: TextInputType.text,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the backend IP address';
                  }
                  // Basic IP validation
                  if (value != 'localhost') {
                    final parts = value.split('.');
                    if (parts.length != 4) {
                      return 'Enter a valid IP address (e.g., 192.168.1.100)';
                    }
                    for (final part in parts) {
                      final num = int.tryParse(part);
                      if (num == null || num < 0 || num > 255) {
                        return 'Enter a valid IP address';
                      }
                    }
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 24),
              
              // Discovery Port Input
              TextFormField(
                controller: _discoveryPortController,
                decoration: const InputDecoration(
                  labelText: 'Discovery Service Port *',
                  hintText: '8006',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.settings_ethernet),
                  helperText: 'Port where discovery service is running',
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the discovery port';
                  }
                  final port = int.tryParse(value);
                  if (port == null || port < 1 || port > 65535) {
                    return 'Enter a valid port number (1-65535)';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 32),
              
              // Error message
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: Colors.red),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                ),
              
              // Save Button
              ElevatedButton(
                onPressed: _isLoading ? null : _saveConfiguration,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
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
                        'Save Configuration',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
              
              const SizedBox(height: 16),
              
              // Current config info
              if (_configService != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Current Configuration:',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text('Discovery: ${_configService!.discoveryServiceUrl}'),
                      Text('Media: ${_configService!.mediaServiceUrl}'),
                      Text('Gateway: ${_configService!.gatewayUrl}'),
                      Text('Configured: ${_configService!.isConfigured ? "Yes" : "No"}'),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _backendIPController.dispose();
    _discoveryPortController.dispose();
    super.dispose();
  }
}

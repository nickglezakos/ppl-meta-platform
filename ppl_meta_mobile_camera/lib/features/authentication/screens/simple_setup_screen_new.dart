import 'package:flutter/material.dart';
import '../../../services/simplified_discovery_client.dart';
import '../../../services/discovery_based_authentication_service.dart';
import '../../../home_screen.dart';

class SimpleSetupScreen extends StatefulWidget {
  const SimpleSetupScreen({super.key});

  @override
  State<SimpleSetupScreen> createState() => _SimpleSetupScreenState();
}

class _SimpleSetupScreenState extends State<SimpleSetupScreen> {
  final _ipLastPartController = TextEditingController(text: '68');
  final _portController = TextEditingController(text: '8006');
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  
  bool _isLoading = false;
  String? _errorMessage;
  String? _detectedNetwork;

  @override
  void initState() {
    super.initState();
    _detectNetwork();
  }

  Future<void> _detectNetwork() async {
    try {
      final discoveryClient = SimplifiedDiscoveryClient();
      final myIP = await discoveryClient.getMyIPAddress();
      if (myIP != null) {
        final parts = myIP.split('.');
        if (parts.length == 4) {
          setState(() {
            _detectedNetwork = '${parts[0]}.${parts[1]}.${parts[2]}.X';
          });
        }
      }
    } catch (e) {
      print('Network detection error: $e');
    }
  }

  Future<void> _connectAndAuthenticate() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final ipLastPart = _ipLastPartController.text.trim();
      final port = _portController.text.trim();
      final username = _usernameController.text.trim();
      final password = _passwordController.text.trim();

      // Create discovery client with specific IP and port
      final discoveryClient = SimplifiedDiscoveryClient();
      final targetIP = await _buildTargetIP(ipLastPart);
      
      print('🔍 Attempting to connect to Discovery Service at $targetIP:$port');
      
      // Test connection to Discovery Service
      final services = await discoveryClient.discoverServicesAtAddress('$targetIP:$port');
      
      print('✅ Found ${services.length} services via Discovery Service');
      
      // Find gateway service
      final gatewayService = services.firstWhere(
        (s) => s.name == 'ppl-meta-gateway',
        orElse: () => throw Exception('Gateway service not found in Discovery Service'),
      );
      
      print('🚪 Gateway found at ${gatewayService.host}:${gatewayService.port}');
      
      // Authenticate via gateway
      final authService = DiscoveryBasedAuthenticationService();
      final authResult = await authService.authenticateViaDiscovery(username, password);
      
      if (authResult.success) {
        print('🎉 Authentication successful!');
        
        // Return success to parent screen
        if (mounted) {
          Navigator.of(context).pop({'success': true});
        }
      } else {
        throw Exception('Authentication failed: ${authResult.error}');
      }
      
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

  Future<String> _buildTargetIP(String lastPart) async {
    final discoveryClient = SimplifiedDiscoveryClient();
    final myIP = await discoveryClient.getMyIPAddress();
    
    if (myIP != null) {
      final parts = myIP.split('.');
      if (parts.length == 4) {
        return '${parts[0]}.${parts[1]}.${parts[2]}.$lastPart';
      }
    }
    
    // Fallback
    return '192.168.1.$lastPart';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PPL Meta Setup'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 20),
              
              // Network Info
              if (_detectedNetwork != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.blue.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Network Detected:',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        _detectedNetwork!,
                        style: TextStyle(
                          color: Colors.blue.shade700,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
              
              const SizedBox(height: 24),
              
              // PPL Meta Platform Connection
              const Text(
                'PPL Meta Platform Connection',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              
              // IP Last Part Input
              TextFormField(
                controller: _ipLastPartController,
                decoration: const InputDecoration(
                  labelText: 'Platform IP Last Part',
                  hintText: 'e.g., 68 for 192.168.1.68',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.computer),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the IP last part';
                  }
                  final num = int.tryParse(value);
                  if (num == null || num < 1 || num > 254) {
                    return 'Enter a valid IP part (1-254)';
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
                  hintText: 'e.g., 8006',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.settings_input_antenna),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the port';
                  }
                  final num = int.tryParse(value);
                  if (num == null || num < 1 || num > 65535) {
                    return 'Enter a valid port (1-65535)';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 24),
              
              // User Credentials
              const Text(
                'User Credentials',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              
              // Username Input
              TextFormField(
                controller: _usernameController,
                decoration: const InputDecoration(
                  labelText: 'Username',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your username';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              
              // Password Input
              TextFormField(
                controller: _passwordController,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock),
                ),
                obscureText: true,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your password';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 24),
              
              // Connect Button
              ElevatedButton(
                onPressed: _isLoading ? null : _connectAndAuthenticate,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator()
                    : const Text(
                        'Connect to PPL Meta Platform',
                        style: TextStyle(fontSize: 16),
                      ),
              ),
              
              // Error Message
              if (_errorMessage != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade700),
                  ),
                ),
              ],
              
              const SizedBox(height: 16),
              
              // Help Text
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'How to find your platform connection:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text('1. Check the PPL Meta console for "Discovery Service running on port XXXX"'),
                    Text('2. Find the IP of the machine running PPL Meta'),
                    Text('3. Enter the last part of that IP and the port number'),
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
    _ipLastPartController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}

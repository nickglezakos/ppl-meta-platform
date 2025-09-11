import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../services/simplified_discovery_client.dart';
import '../../../services/discovery_based_authentication_service.dart';
import '../../../services/discovery_config_service.dart';
import '../../../core/providers/authentication_provider.dart';

class SimpleSetupScreen extends StatefulWidget {
  const SimpleSetupScreen({super.key});

  @override
  State<SimpleSetupScreen> createState() => _SimpleSetupScreenState();
}

class _SimpleSetupScreenState extends State<SimpleSetupScreen> {
  final _backendIPController = TextEditingController(text: '');
  final _portController = TextEditingController(text: '8006');
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    // No automatic detection - user must input complete backend IP
  }

  Future<void> _connectAndAuthenticate() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final backendIP = _backendIPController.text.trim();
      final port = _portController.text.trim();
      final username = _usernameController.text.trim();
      final password = _passwordController.text.trim();

      // Save user's backend configuration - no network detection needed
      final configService = DiscoveryConfigService.instance;
      await configService.configureFromUserInput(
        ipLastPart: backendIP.split('.').last, // Just for compatibility 
        port: port,
        deviceIPPrefix: backendIP.split('.').take(3).join('.'), // Backend network prefix
      );
      
      print('✅ Discovery configuration saved for backend IP: $backendIP');

      // Create discovery client with user-specified IP
      final discoveryClient = SimplifiedDiscoveryClient();
      
      print('🔍 Attempting to connect to Discovery Service at $backendIP:$port');
      
      // Test connection to Discovery Service using complete backend IP
      final services = await discoveryClient.discoverServicesAtAddress('$backendIP:$port');
      
      print('✅ Found ${services.length} services via Discovery Service');
      
      // Find node service for authentication (not gateway)
      final nodeService = services.firstWhere(
        (s) => s.name == 'ppl-meta-node',
        orElse: () => throw Exception('Node service not found in Discovery Service'),
      );
      
      print('🚪 Node service found at ${nodeService.host}:${nodeService.port}');
      
      // Construct node service URL for authentication
      final nodeUrl = 'http://${nodeService.host}:${nodeService.port}';
      
      // Authenticate via AuthenticationProvider to properly set app state
      final authProvider = Provider.of<AuthenticationProvider>(context, listen: false);
      final loginSuccess = await authProvider.login(
        serverUrl: nodeUrl,
        username: username,
        password: password,
      );
      
      if (loginSuccess) {
        print('🎉 Authentication successful! App state updated.');
        
        // Navigation will be handled automatically by MainNavigator
        // since AuthenticationProvider.isAuthenticated is now true
        
      } else {
        throw Exception('Authentication failed: ${authProvider.error}');
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
              
              // Instructions
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Setup Instructions:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '1. Open the web frontend at http://localhost:3000/#/settings',
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '2. Check the IP address of the PPL Meta Platform services',
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '3. Enter the complete backend IP address below',
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
              
              // Complete Backend IP Input
              TextFormField(
                controller: _backendIPController,
                decoration: const InputDecoration(
                  labelText: 'Backend IP Address',
                  hintText: 'e.g., 10.109.198.107 (complete IP from frontend settings)',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.computer),
                ),
                keyboardType: TextInputType.text,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the complete backend IP address';
                  }
                  // Basic IP validation
                  final parts = value.split('.');
                  if (parts.length != 4) {
                    return 'Enter a valid IP address (e.g., 10.109.198.107)';
                  }
                  for (final part in parts) {
                    final num = int.tryParse(part);
                    if (num == null || num < 0 || num > 255) {
                      return 'Enter a valid IP address';
                    }
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _errorMessage!,
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                      const SizedBox(height: 8),
                      ElevatedButton.icon(
                        onPressed: () {
                          setState(() {
                            _errorMessage = null;
                          });
                        },
                        icon: const Icon(Icons.refresh),
                        label: const Text('Try Again'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.orange,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ],
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
    _backendIPController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}

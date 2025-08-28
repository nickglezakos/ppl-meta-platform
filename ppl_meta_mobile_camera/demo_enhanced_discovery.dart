import 'package:flutter/material.dart';
import 'services/hybrid_service_discovery.dart';
import 'services/enhanced_authentication_service.dart';

/// Demo app showcasing hybrid service discovery integration with PPL Meta Discovery Service
class ServiceDiscoveryDemoApp extends StatelessWidget {
  const ServiceDiscoveryDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PPL Meta Mobile Camera - Hybrid Service Discovery Demo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const HybridServiceDiscoveryDemoScreen(),
    );
  }
}

class HybridServiceDiscoveryDemoScreen extends StatefulWidget {
  const HybridServiceDiscoveryDemoScreen({super.key});

  @override
  State<HybridServiceDiscoveryDemoScreen> createState() => _HybridServiceDiscoveryDemoScreenState();
}

class _HybridServiceDiscoveryDemoScreenState extends State<HybridServiceDiscoveryDemoScreen> {
  final HybridServiceDiscoveryService _discoveryService = HybridServiceDiscoveryService();
  final EnhancedAuthenticationService _authService = EnhancedAuthenticationService.instance;
  
  bool _isDiscovering = false;
  bool _isAuthenticated = false;
  String? _discoveredNodeUrl;
  List<Map<String, dynamic>> _availableServices = [];
  String _status = 'Ready to discover services';
  Map<String, dynamic>? _authResult;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Hybrid Service Discovery Demo'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _isAuthenticated ? Icons.check_circle : Icons.radio_button_unchecked,
                          color: _isAuthenticated ? Colors.green : Colors.grey,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Service Discovery Status',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(_status),
                    if (_discoveredNodeUrl != null) ...[
                      const SizedBox(height: 8),
                      Text('Node Service: $_discoveredNodeUrl', style: const TextStyle(fontWeight: FontWeight.bold)),
                    ],
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Action Buttons
            ElevatedButton.icon(
              onPressed: _isDiscovering ? null : _discoverServices,
              icon: _isDiscovering 
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.search),
              label: Text(_isDiscovering ? 'Discovering...' : 'Discover Services'),
            ),
            
            const SizedBox(height: 8),
            
            ElevatedButton.icon(
              onPressed: (_discoveredNodeUrl != null && !_isAuthenticated) ? _testAuthentication : null,
              icon: const Icon(Icons.login),
              label: const Text('Test Authentication'),
            ),
            
            const SizedBox(height: 16),
            
            // Services List
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Discovered Services (${_availableServices.length})',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: _availableServices.isEmpty
                          ? const Center(child: Text('No services discovered yet'))
                          : ListView.builder(
                              itemCount: _availableServices.length,
                              itemBuilder: (context, index) {
                                final service = _availableServices[index];
                                final isHealthy = service['status'] == 'healthy';
                                
                                return ListTile(
                                  leading: Icon(
                                    isHealthy ? Icons.check_circle : Icons.error,
                                    color: isHealthy ? Colors.green : Colors.red,
                                  ),
                                  title: Text(service['name'] ?? 'Unknown'),
                                  subtitle: Text(
                                    '${service['host']}:${service['port']} - ${service['status']}\n'
                                    'Version: ${service['version']} | Type: ${service['service_type']}'
                                  ),
                                  isThreeLine: true,
                                );
                              },
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            
            // Authentication Result
            if (_authResult != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Authentication Result',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(_authResult.toString()),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _discoverServices() async {
    setState(() {
      _isDiscovering = true;
      _status = 'Discovering services...';
    });

    try {
      // Step 1: Discover Node service
      setState(() => _status = 'Discovering Node service...');
      final nodeUrl = await _discoveryService.discoverNodeService();
      
      // Step 2: Get all available services
      setState(() => _status = 'Getting available services...'); 
      final services = await _discoveryService.getAvailableServices();
      
      setState(() {
        _discoveredNodeUrl = nodeUrl;
        _availableServices = services;
        _status = nodeUrl != null 
          ? 'Node service discovered: $nodeUrl'
          : 'Failed to discover Node service';
      });

    } catch (e) {
      setState(() {
        _status = 'Discovery failed: $e';
      });
    } finally {
      setState(() {
        _isDiscovering = false;
      });
    }
  }

  Future<void> _testAuthentication() async {
    if (_discoveredNodeUrl == null) return;

    setState(() => _status = 'Testing authentication...');

    try {
      // Use test credentials
      final result = await _authService.autoLogin(
        username: 'fresh.user@example.com',
        password: 'NewPassword234!',
      );

      setState(() {
        _authResult = {
          'success': result.success,
          'message': result.message,
          'nodeUrl': result.serverUrl,
          'hasToken': result.token != null,
          'hasUserData': result.userData != null,
        };
        _isAuthenticated = result.success;
        _status = result.success 
          ? 'Authentication successful!'
          : 'Authentication failed: ${result.message}';
      });

    } catch (e) {
      setState(() {
        _status = 'Authentication error: $e';
      });
    }
  }
}

// Main function to run the demo
void main() {
  runApp(const ServiceDiscoveryDemoApp());
}

class _ServiceDiscoveryDemoScreenState extends State<ServiceDiscoveryDemoScreen> {
  final EnhancedAutoAuthenticationService _authService = EnhancedAutoAuthenticationService();
  final EnhancedAutoCameraRegistrationService _regService = EnhancedAutoCameraRegistrationService();
  
  AuthResult? _authResult;
  bool _isAuthenticating = false;
  bool _isRegistering = false;
  String? _error;

  @override
  void dispose() {
    _authService.dispose();
    _regService.dispose();
    super.dispose();
  }

  Future<void> _performAutoLogin() async {
    setState(() {
      _isAuthenticating = true;
      _error = null;
    });

    try {
      final result = await _authService.autoLogin(
        'fresh.user@example.com', // Demo credentials
        'NewPassword234!',
      );

      setState(() {
        _authResult = result;
        _isAuthenticating = false;
      });

      if (result.success) {
        _showSuccess('Authentication successful via ${result.discoveryMethod}!');
      } else {
        _showError('Authentication failed: ${result.error}');
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isAuthenticating = false;
      });
      _showError('Authentication error: $e');
    }
  }

  Future<void> _performCameraRegistration() async {
    if (_authResult?.token == null) {
      _showError('Please authenticate first');
      return;
    }

    setState(() {
      _isRegistering = true;
      _error = null;
    });

    try {
      final result = await _regService.autoRegisterCamera(_authResult!.token!);

      setState(() => _isRegistering = false);

      if (result.success) {
        _showSuccess('Camera registered successfully! ID: ${result.cameraId}');
      } else {
        _showError('Camera registration failed: ${result.error}');
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isRegistering = false;
      });
      _showError('Registration error: $e');
    }
  }

  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 5),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PPL Meta Mobile Camera'),
        subtitle: const Text('Enhanced Service Discovery Demo'),
        actions: const [
          ServiceDiscoveryIndicator(),
          SizedBox(width: 16),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Service Discovery Status
            const ServiceDiscoveryStatusWidget(),
            
            const SizedBox(height: 24),
            
            // Authentication Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.login, color: Colors.blue),
                        SizedBox(width: 8),
                        Text(
                          'Authentication',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    if (_authResult != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: _authResult!.success 
                            ? Colors.green.shade50 
                            : Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: _authResult!.success 
                              ? Colors.green.shade200 
                              : Colors.red.shade200,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  _authResult!.success ? Icons.check_circle : Icons.error,
                                  color: _authResult!.success ? Colors.green : Colors.red,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  _authResult!.success ? 'Authentication Successful' : 'Authentication Failed',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w500,
                                    color: _authResult!.success ? Colors.green.shade700 : Colors.red.shade700,
                                  ),
                                ),
                              ],
                            ),
                            if (_authResult!.success) ...[
                              const SizedBox(height: 8),
                              Text('Node URL: ${_authResult!.nodeURL}'),
                              Text('Discovery: ${_authResult!.discoveryMethod}'),
                              Text('Token: ${_authResult!.token?.substring(0, 20)}...'),
                              if (_authResult!.discoveredServices != null)
                                Text(_authResult!.discoveryySummary),
                            ] else ...[
                              const SizedBox(height: 8),
                              Text('Error: ${_authResult!.error}'),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    ElevatedButton(
                      onPressed: _isAuthenticating ? null : _performAutoLogin,
                      child: _isAuthenticating
                        ? const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                              SizedBox(width: 8),
                              Text('Authenticating...'),
                            ],
                          )
                        : const Text('Auto-Login with Discovery'),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Camera Registration Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.camera_alt, color: Colors.green),
                        SizedBox(width: 8),
                        Text(
                          'Camera Registration',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: (_isRegistering || _authResult?.token == null) 
                        ? null 
                        : _performCameraRegistration,
                      child: _isRegistering
                        ? const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                              SizedBox(width: 8),
                              Text('Registering...'),
                            ],
                          )
                        : const Text('Register Camera with Discovery'),
                    ),
                    if (_authResult?.token == null) ...[
                      const SizedBox(height: 8),
                      Text(
                        'Please authenticate first',
                        style: TextStyle(
                          color: Colors.grey.shade600,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Error Display
            if (_error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error, color: Colors.red.shade700),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Error: $_error',
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            
            const SizedBox(height: 24),
            
            // Info Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.info, color: Colors.blue),
                        SizedBox(width: 8),
                        Text(
                          'Enhanced Discovery Features',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      '• Central Discovery: Uses PPL Meta Discovery Service for centralized service registry',
                      style: TextStyle(fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '• Multicast Discovery: Local network discovery using multicast announcements',
                      style: TextStyle(fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '• Local Network Scan: Fallback network scanning for service discovery',
                      style: TextStyle(fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '• Smart Fallbacks: Automatic fallback between discovery methods',
                      style: TextStyle(fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '• Health Verification: All discovered services are health-checked',
                      style: TextStyle(fontSize: 14),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Main entry point for the demo
void main() {
  runApp(const ServiceDiscoveryDemoApp());
}

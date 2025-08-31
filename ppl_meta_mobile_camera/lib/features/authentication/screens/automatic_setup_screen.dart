import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';
import '../../../services/discovery_based_authentication_service.dart';
import '../../../services/auto_camera_registration_service.dart';

/// Automatic setup screen for zero-configuration camera setup
class AutomaticSetupScreen extends StatefulWidget {
  const AutomaticSetupScreen({Key? key}) : super(key: key);

  @override
  State<AutomaticSetupScreen> createState() => _AutomaticSetupScreenState();
}

class _AutomaticSetupScreenState extends State<AutomaticSetupScreen> {
  bool _isDiscovering = false;
  String _statusMessage = 'Ready to discover PPL Meta services via Discovery Service';
  String? _discoveredServiceUrl;
  bool _isAuthenticating = false;
  bool _isRegistering = false;
  
  final DiscoveryBasedAuthenticationService _authService = DiscoveryBasedAuthenticationService();
  final AutoCameraRegistrationService _registrationService = AutoCameraRegistrationService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Automatic Setup'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Text(
              'Set up your mobile camera automatically',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            // Description
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                'Automatically discovers services and registers camera',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.8),
                ),
              ),
            ),
            const SizedBox(height: 32),
            
            // Status Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _getStatusIcon(),
                          color: _getStatusColor(),
                          size: 24,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Status',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _statusMessage,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (_discoveredServiceUrl != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        'Service: $_discoveredServiceUrl',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
            
            // Action Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isDiscovering || _isAuthenticating || _isRegistering 
                    ? null 
                    : _startAutomaticSetup,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isDiscovering || _isAuthenticating || _isRegistering
                    ? Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Theme.of(context).colorScheme.onPrimary,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Text('Setting up...'),
                        ],
                      )
                    : const Text('Start Automatic Setup'),
              ),
            ),
            const SizedBox(height: 16),
            
            // Manual Setup Option
            Center(
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Use Manual Setup Instead'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getStatusIcon() {
    if (_isDiscovering) return Icons.search;
    if (_isAuthenticating) return Icons.lock_outline;
    if (_isRegistering) return Icons.camera_alt_outlined;
    if (_discoveredServiceUrl != null) return Icons.check_circle;
    return Icons.radar;
  }

  Color _getStatusColor() {
    if (_isDiscovering || _isAuthenticating || _isRegistering) {
      return Theme.of(context).colorScheme.primary;
    }
    if (_discoveredServiceUrl != null) {
      return Colors.green;
    }
    return Theme.of(context).colorScheme.onSurface.withOpacity(0.6);
  }

  Future<void> _startAutomaticSetup() async {
    try {
      // Step 1: Discovery Service Discovery and Service Registry
      setState(() {
        _isDiscovering = true;
        _statusMessage = '🔍 Discovering PPL Meta Discovery Service...';
      });

      print('🔍 Starting Discovery Service-based automatic setup');
      
      // Get all services from Discovery Service
      final services = await _authService.getAllServices();
      
      if (services.isEmpty) {
        throw Exception('No services found in Discovery Service');
      }

      setState(() {
        _statusMessage = '✅ Found ${services.length} services! Verifying connections...';
      });

      print('✅ Services discovered from Discovery Service:');
      for (final service in services) {
        print('  📱 ${service.name} at ${service.baseUrl}');
      }

      // Step 2: Test connectivity to key services
      setState(() {
        _statusMessage = '🩺 Testing service connectivity...';
      });

      final nodeConnected = await _authService.testServiceConnectivity('ppl-meta-node');
      final gatewayConnected = await _authService.testServiceConnectivity('ppl-meta-gateway');

      if (!nodeConnected) {
        throw Exception('Node service is not reachable for authentication');
      }

      // Get Node service URL
      _discoveredServiceUrl = await _authService.getServiceUrl('ppl-meta-node');

      setState(() {
        _isDiscovering = false;
        _statusMessage = '✅ Services verified! Discovery Service setup complete.';
      });

      print('✅ Service connectivity verified');
      print('🎯 Node service: ${_discoveredServiceUrl}');

      // Step 3: Show success with service details
      await Future.delayed(const Duration(seconds: 2));
      
      if (mounted) {
        final nodeUrl = await _authService.getServiceUrl('ppl-meta-node');
        final mediaUrl = await _authService.getServiceUrl('ppl-meta-media');
        final gatewayUrl = await _authService.getServiceUrl('ppl-meta-gateway');
        
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('🎉 Discovery Service Setup Complete'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('✅ PPL Meta services discovered via Discovery Service!'),
                  const SizedBox(height: 16),
                  
                  const Text('Available Services:', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  
                  if (nodeUrl != null) _buildServiceRow('🔐 Node Service', nodeUrl),
                  if (gatewayUrl != null) _buildServiceRow('🌐 Gateway Service', gatewayUrl),
                  if (mediaUrl != null) _buildServiceRow('📱 Media Service', mediaUrl),
                  
                  const SizedBox(height: 16),
                  const Text('The services have been automatically configured. You can now log in with your credentials.',
                    style: TextStyle(color: Colors.green)),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(context); // Close dialog
                  Navigator.pop(context, nodeUrl); // Go back with Node service URL
                },
                child: const Text('Continue to Login'),
              ),
            ],
          ),
        );
      }

    } catch (e) {
      print('💥 Automatic setup failed: $e');
      setState(() {
        _isDiscovering = false;
        _isAuthenticating = false;
        _statusMessage = '❌ Setup failed: ${e.toString()}';
      });

      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('❌ Setup Failed'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Failed to set up connection to PPL Meta services:'),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    e.toString(),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onErrorContainer,
                      fontSize: 12,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text('Please check your network connection and ensure PPL Meta services are running.'),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Try Again'),
              ),
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pop(context);
                },
                child: const Text('Manual Setup'),
              ),
            ],
          ),
        );
      }
    }
  }
  
  Widget _buildServiceRow(String label, String url) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Text(label, style: const TextStyle(fontSize: 12)),
          ),
          Expanded(
            flex: 3,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                url,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 10),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

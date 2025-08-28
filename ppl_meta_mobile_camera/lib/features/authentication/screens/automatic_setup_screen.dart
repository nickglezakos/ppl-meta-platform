import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';
import '../../../services/auto_authentication_service.dart';
import '../../../services/auto_camera_registration_service.dart';

/// Automatic setup screen for zero-configuration camera setup
class AutomaticSetupScreen extends StatefulWidget {
  const AutomaticSetupScreen({Key? key}) : super(key: key);

  @override
  State<AutomaticSetupScreen> createState() => _AutomaticSetupScreenState();
}

class _AutomaticSetupScreenState extends State<AutomaticSetupScreen> {
  bool _isDiscovering = false;
  String _statusMessage = 'Ready to discover PPL Meta services automatically';
  String? _discoveredServiceUrl;
  bool _isAuthenticating = false;
  bool _isRegistering = false;
  
  final EnhancedNetworkDiscoveryService _discoveryService = EnhancedNetworkDiscoveryService();
  final AutoAuthenticationService _authService = AutoAuthenticationService();
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
      // Step 1: Service Discovery
      setState(() {
        _isDiscovering = true;
        _statusMessage = 'Discovering PPL Meta services...';
      });

      print('🔍 Starting automatic setup process');
      final serviceUrl = await _discoveryService.autoDiscoverNodeService();
      
      if (serviceUrl == null) {
        throw Exception('Failed to discover PPL Meta Node service');
      }

      setState(() {
        _discoveredServiceUrl = serviceUrl;
        _statusMessage = 'Service discovered! Setting up connection...';
        _isDiscovering = false;
        _isAuthenticating = true;
      });

      print('✅ Service discovered: $serviceUrl');

      // Step 2: Test the discovered server URL
      final authProvider = context.read<AuthenticationProvider>();
      
      // Test if the server is reachable
      await authProvider.checkServerConnection(serviceUrl);
      
      setState(() {
        _statusMessage = 'Server discovered and verified! You can now log in.';
        _isAuthenticating = false;
      });

      print('✅ Server verification complete');

      // Step 3: Navigate back with success
      await Future.delayed(const Duration(seconds: 2));
      
      if (mounted) {
        // Show success dialog with server URL to copy
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('🎉 Setup Complete'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('✅ PPL Meta service discovered and verified!'),
                const SizedBox(height: 16),
                const Text('Server URL:', style: TextStyle(fontWeight: FontWeight.bold)),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceVariant,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: SelectableText(
                    serviceUrl,
                    style: const TextStyle(fontFamily: 'monospace'),
                  ),
                ),
                const SizedBox(height: 16),
                const Text('The server URL has been automatically filled in the login form. You can now log in with your credentials or register a new camera.'),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(context); // Close dialog
                  Navigator.pop(context, serviceUrl); // Go back with discovered URL
                },
                child: const Text('Continue to Login'),
              ),
            ],
          ),
        );
      }

    } catch (e) {
      print('❌ Automatic setup failed: $e');
      
      setState(() {
        _statusMessage = 'Setup failed: ${e.toString()}';
        _isDiscovering = false;
        _isAuthenticating = false;
        _isRegistering = false;
      });

      // Show error dialog
      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Setup Failed'),
            content: Text('Automatic setup encountered an error:\n\n${e.toString()}'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    }
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../../core/providers/authentication_provider.dart';
import '../../../services/auto_camera_registration_service.dart';
import '../../../services/app_logger.dart';

/// Manual connection fallback UI for when automatic setup fails
/// 
/// Provides a fully manual flow for:
/// 1. Entering server URL
/// 2. Authenticating with username/password
/// 3. Registering camera manually
class ManualConnectionScreen extends StatefulWidget {
  const ManualConnectionScreen({Key? key}) : super(key: key);

  @override
  State<ManualConnectionScreen> createState() => _ManualConnectionScreenState();
}

class _ManualConnectionScreenState extends State<ManualConnectionScreen> {
  final _formKey = GlobalKey<FormState>();
  final _serverUrlController = TextEditingController(text: 'http://192.168.1.68');
  final _portController = TextEditingController(text: '8005');
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  
  bool _isLoading = false;
  String? _errorMessage;
  String? _statusMessage;
  bool _obscurePassword = true;
  int _currentStep = 0; // 0: Enter details, 1: Authenticating, 2: Registering camera

  @override
  void dispose() {
    _serverUrlController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Manual Connection'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header with icon
              Center(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.phonelink_setup,
                    size: 48,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Title
              Text(
                'Manual Setup',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),

              // Description
              Text(
                'Enter your platform connection details manually',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),

              // Progress indicator
              if (_currentStep > 0) ...[
                LinearProgressIndicator(
                  value: _currentStep / 2,
                  backgroundColor: Theme.of(context).colorScheme.surfaceVariant,
                ),
                const SizedBox(height: 8),
                Text(
                  _getStepText(),
                  style: Theme.of(context).textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
              ],

              // Server URL Input
              TextFormField(
                controller: _serverUrlController,
                decoration: InputDecoration(
                  labelText: 'Server IP Address',
                  hintText: 'e.g., 192.168.1.68',
                  prefixIcon: const Icon(Icons.computer),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  helperText: 'IP address of your PPL Meta platform',
                ),
                keyboardType: TextInputType.url,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the server IP address';
                  }
                  // Basic IP validation
                  final ipPattern = RegExp(r'^(\d{1,3}\.){3}\d{1,3}$');
                  if (!ipPattern.hasMatch(value.replaceAll('http://', '').replaceAll('https://', ''))) {
                    return 'Please enter a valid IP address';
                  }
                  return null;
                },
                enabled: !_isLoading,
              ),
              const SizedBox(height: 16),

              // Port Input
              TextFormField(
                controller: _portController,
                decoration: InputDecoration(
                  labelText: 'Node Service Port',
                  hintText: 'e.g., 8005',
                  prefixIcon: const Icon(Icons.settings_ethernet),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  helperText: 'Port number for authentication service',
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the port number';
                  }
                  final port = int.tryParse(value);
                  if (port == null || port < 1 || port > 65535) {
                    return 'Please enter a valid port (1-65535)';
                  }
                  return null;
                },
                enabled: !_isLoading,
              ),
              const SizedBox(height: 16),

              // Username Input
              TextFormField(
                controller: _usernameController,
                decoration: InputDecoration(
                  labelText: 'Username',
                  hintText: 'Enter your username',
                  prefixIcon: const Icon(Icons.person),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your username';
                  }
                  return null;
                },
                enabled: !_isLoading,
              ),
              const SizedBox(height: 16),

              // Password Input
              TextFormField(
                controller: _passwordController,
                decoration: InputDecoration(
                  labelText: 'Password',
                  hintText: 'Enter your password',
                  prefixIcon: const Icon(Icons.lock),
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscurePassword ? Icons.visibility : Icons.visibility_off,
                    ),
                    onPressed: () {
                      setState(() {
                        _obscurePassword = !_obscurePassword;
                      });
                    },
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                obscureText: _obscurePassword,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your password';
                  }
                  return null;
                },
                enabled: !_isLoading,
              ),
              const SizedBox(height: 24),

              // Status Message
              if (_statusMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.blue.shade200),
                  ),
                  child: Row(
                    children: [
                      const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _statusMessage!,
                          style: TextStyle(
                            color: Colors.blue.shade700,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Error Message
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: Theme.of(context).colorScheme.error.withOpacity(0.3),
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.error_outline,
                        color: Theme.of(context).colorScheme.error,
                        size: 20,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.onErrorContainer,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Connect Button
              ElevatedButton(
                onPressed: _isLoading ? null : _connectAndRegister,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _isLoading
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          ),
                          SizedBox(width: 12),
                          Text('Connecting...'),
                        ],
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Icon(Icons.login),
                          SizedBox(width: 8),
                          Text('Connect & Register Camera'),
                        ],
                      ),
              ),
              const SizedBox(height: 16),

              // Help Text
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.help_outline,
                          size: 16,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Connection Tips',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '• Ensure your device is on the same network as the platform\n'
                      '• Default Node Service port is 8005\n'
                      '• Discovery Service port is usually 8006\n'
                      '• Contact your administrator for credentials',
                      style: TextStyle(
                        fontSize: 12,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getStepText() {
    switch (_currentStep) {
      case 1:
        return 'Step 1/2: Authenticating with platform...';
      case 2:
        return 'Step 2/2: Registering camera...';
      default:
        return '';
    }
  }

  Future<void> _connectAndRegister() async {
    print('🔧 Starting manual connection and registration');
    
    if (!_formKey.currentState!.validate()) {
      print('⚠️  Form validation failed');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _currentStep = 1;
      _statusMessage = 'Connecting to platform...';
    });

    try {
      final serverIp = _serverUrlController.text.trim().replaceAll('http://', '').replaceAll('https://', '');
      final port = _portController.text.trim();
      final username = _usernameController.text.trim();
      final password = _passwordController.text.trim();
      final serverUrl = 'http://$serverIp:$port';

      print('📡 Attempting connection to: $serverUrl');
      print('👤 Username: $username');

      // Step 1: Authenticate with Node Service
      setState(() {
        _statusMessage = 'Authenticating with platform...';
      });

      final loginResponse = await http.post(
        Uri.parse('$serverUrl/api/v1/users/login'),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: 'username=$username&password=$password',
      ).timeout(const Duration(seconds: 15));

      if (loginResponse.statusCode != 200) {
        final errorData = json.decode(loginResponse.body);
        throw Exception(errorData['detail'] ?? 'Authentication failed');
      }

      final authData = json.decode(loginResponse.body);
      final jwtToken = authData['access_token'];
      
      print('✅ Authentication successful');
      print('🔑 JWT token received');

      // Step 2: Update Authentication Provider
      setState(() {
        _currentStep = 2;
        _statusMessage = 'Registering camera with platform...';
      });

      if (!mounted) return;

      final authProvider = context.read<AuthenticationProvider>();
      final loginSuccess = await authProvider.login(
        serverUrl: serverUrl,
        username: username,
        password: password,
      );

      if (!loginSuccess) {
        throw Exception('Failed to update authentication state');
      }

      print('📱 Authentication provider updated');

      // Step 3: Register Camera
      final registrationService = AutoCameraRegistrationService();
      final registrationResult = await registrationService.autoRegisterCamera(jwtToken);

      if (!registrationResult.isSuccess) {
        throw Exception(registrationResult.error ?? 'Camera registration failed');
      }

      print('📷 Camera registered successfully');
      print('   Camera ID: ${registrationResult.cameraId}');
      print('   Camera UUID: ${registrationResult.deviceId}');
      print('   Camera Name: ${registrationResult.cameraName}');

      setState(() {
        _statusMessage = 'Success! Camera registered';
      });

      // Show success dialog
      if (mounted) {
        await showDialog(
          context: context,
          barrierDismissible: false,
          builder: (context) => AlertDialog(
            icon: const Icon(
              Icons.check_circle,
              color: Colors.green,
              size: 64,
            ),
            title: const Text('Setup Complete!'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Your camera has been successfully registered'),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Camera Name: ${registrationResult.cameraName}',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Camera ID: ${registrationResult.cameraId}',
                        style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            actions: [
              ElevatedButton(
                onPressed: () {
                  Navigator.pop(context); // Close dialog
                  Navigator.pop(context); // Return to home/camera screen
                },
                child: const Text('Start Using Camera'),
              ),
            ],
          ),
        );
      }

    } catch (e) {
      print('❌ Manual connection failed: $e');
      
      setState(() {
        _errorMessage = e.toString();
        _statusMessage = null;
        _currentStep = 0;
      });

      // Log detailed error for debugging
      AppLogger.instance.error('Manual connection failed', e);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}

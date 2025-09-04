import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';
import '../../../services/device_identifier_service.dart';

/// Registration form widget for new device registration
class RegistrationForm extends StatefulWidget {
  final VoidCallback onRegistrationSuccess;

  const RegistrationForm({
    Key? key,
    required this.onRegistrationSuccess,
  }) : super(key: key);

  @override
  State<RegistrationForm> createState() => _RegistrationFormState();
}

class _RegistrationFormState extends State<RegistrationForm> {
  final _formKey = GlobalKey<FormState>();
  final _serverUrlController = TextEditingController();
  final _deviceNameController = TextEditingController();

  bool _agreedToTerms = false;

  @override
  void initState() {
    super.initState();
    _loadSavedServerUrl();
    _generateDefaultDeviceName();
  }

  @override
  void dispose() {
    _serverUrlController.dispose();
    _deviceNameController.dispose();
    super.dispose();
  }

  Future<void> _loadSavedServerUrl() async {
    // Load any saved server URL from previous sessions
    final authProvider = context.read<AuthenticationProvider>();
    if (authProvider.serverUrl != null) {
      _serverUrlController.text = authProvider.serverUrl!;
    }
  }

  void _generateDefaultDeviceName() async {
    try {
      // Use DeviceIdentifierService to generate consistent device name
      final deviceService = DeviceIdentifierService();
      final deviceName = await deviceService.generateCameraName();
      _deviceNameController.text = deviceName;
    } catch (e) {
      // Fallback to simple name without timestamp
      _deviceNameController.text = 'Mobile Camera';
    }
  }

  Future<void> _handleRegistration() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (!_agreedToTerms) {
      _showErrorSnackBar('Please agree to the terms and conditions');
      return;
    }

    final authProvider = context.read<AuthenticationProvider>();
    
    // Check server connection first
    await authProvider.checkServerConnection(_serverUrlController.text.trim());
    
    if (!authProvider.isServerOnline) {
      _showErrorSnackBar('Cannot connect to server. Please check the URL and try again.');
      return;
    }

    // Attempt registration
    final success = await authProvider.registerDevice(
      serverUrl: _serverUrlController.text.trim(),
      deviceName: _deviceNameController.text.trim(),
      deviceType: 'mobile', // Default device type for mobile camera app
    );

    if (success) {
      _showSuccessSnackBar('Device registered successfully!');
      widget.onRegistrationSuccess();
    } else {
      _showErrorSnackBar(authProvider.error ?? 'Registration failed');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthenticationProvider>(
      builder: (context, authProvider, child) {
        return Container(
          constraints: BoxConstraints(
            minHeight: MediaQuery.of(context).size.height * 0.6, // Ensure scrollable content
          ),
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min, // Use minimum space needed
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),
                
                // Registration Info Card
                _buildRegistrationInfoCard(),
                
                const SizedBox(height: 24),
                
                // Server URL Field
                _buildServerUrlField(),
                
                const SizedBox(height: 20),
                
                // Device Name Field
                _buildDeviceNameField(),
                
                const SizedBox(height: 16),
                
                // Terms Agreement
                _buildTermsAgreement(),
                
                const SizedBox(height: 32),
                
                // Register Button
                _buildRegisterButton(authProvider),
                
                const SizedBox(height: 16),
                
                // Device Info Button
                _buildDeviceInfoButton(),
                
                const SizedBox(height: 24), // Replace Spacer with fixed spacing
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildRegistrationInfoCard() {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.primaryContainer,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.info_outline,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
                const SizedBox(width: 8),
                Text(
                  'Device Registration',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Register this device as a new camera in your PPL Meta platform. You\'ll need an access code from your system administrator.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onPrimaryContainer,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServerUrlField() {
    return TextFormField(
      controller: _serverUrlController,
      keyboardType: TextInputType.url,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: 'PPL Meta Server URL',
        hintText: 'http://localhost:8001 or https://your-server.com',
        prefixIcon: const Icon(Icons.cloud),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        filled: true,
        fillColor: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
      ),
      validator: (value) {
        if (value == null || value.trim().isEmpty) {
          return 'Server URL is required';
        }
        
        final uri = Uri.tryParse(value.trim());
        if (uri == null || (!uri.hasScheme || !uri.hasAuthority)) {
          return 'Please enter a valid URL';
        }
        
        return null;
      },
      onChanged: (value) {
        // Auto-check server connection when URL changes
        if (value.trim().isNotEmpty) {
          _debounceServerCheck(value.trim());
        }
      },
    );
  }

  Widget _buildDeviceNameField() {
    return TextFormField(
      controller: _deviceNameController,
      textInputAction: TextInputAction.done,
      onFieldSubmitted: (_) => _handleRegistration(), // Submit form when user presses "done"
      decoration: InputDecoration(
        labelText: 'Device Name',
        hintText: 'Enter a name for this camera device',
        prefixIcon: const Icon(Icons.camera_alt),
        suffixIcon: IconButton(
          icon: const Icon(Icons.refresh),
          onPressed: _generateDefaultDeviceName,
          tooltip: 'Generate new name',
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        filled: true,
        fillColor: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
        helperText: 'This name will identify your camera in the platform',
      ),
      validator: (value) {
        if (value == null || value.trim().isEmpty) {
          return 'Device name is required';
        }
        if (value.trim().length < 3) {
          return 'Device name must be at least 3 characters';
        }
        return null;
      },
    );
  }

  Widget _buildTermsAgreement() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Checkbox(
          value: _agreedToTerms,
          onChanged: (value) {
            setState(() {
              _agreedToTerms = value ?? false;
            });
          },
        ),
        Expanded(
          child: GestureDetector(
            onTap: () {
              setState(() {
                _agreedToTerms = !_agreedToTerms;
              });
            },
            child: Text.rich(
              TextSpan(
                children: [
                  const TextSpan(text: 'I agree to the '),
                  TextSpan(
                    text: 'Terms and Conditions',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      decoration: TextDecoration.underline,
                    ),
                  ),
                  const TextSpan(text: ' and '),
                  TextSpan(
                    text: 'Privacy Policy',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      decoration: TextDecoration.underline,
                    ),
                  ),
                ],
              ),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRegisterButton(AuthenticationProvider authProvider) {
    return ElevatedButton(
      onPressed: authProvider.isLoading ? null : _handleRegistration,
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
        elevation: 2,
      ),
      child: authProvider.isLoading
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.app_registration),
                SizedBox(width: 8),
                Text(
                  'Register Device',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildDeviceInfoButton() {
    return OutlinedButton(
      onPressed: _showDeviceInfo,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        side: BorderSide(
          color: Theme.of(context).colorScheme.outline,
        ),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.info),
          SizedBox(width: 8),
          Text('View Device Information'),
        ],
      ),
    );
  }

  Future<void> _showDeviceInfo() async {
    final cameraService = CameraService.instance;
    final deviceInfo = await cameraService.getDeviceInfo();
    
    if (!mounted) return;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Device Information'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildInfoRow('Device ID', deviceInfo['deviceId'] ?? 'Unknown'),
              _buildInfoRow('Model', deviceInfo['model'] ?? 'Unknown'),
              _buildInfoRow('Brand', deviceInfo['brand'] ?? 'Unknown'),
              _buildInfoRow('Platform', deviceInfo['platform'] ?? 'Unknown'),
              _buildInfoRow('Version', deviceInfo['version'] ?? 'Unknown'),
              if (deviceInfo['manufacturer'] != null)
                _buildInfoRow('Manufacturer', deviceInfo['manufacturer']),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  void _debounceServerCheck(String url) {
    // Simple debounce implementation
    Future.delayed(const Duration(milliseconds: 500), () {
      if (_serverUrlController.text.trim() == url) {
        final authProvider = context.read<AuthenticationProvider>();
        authProvider.checkServerConnection(url);
      }
    });
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white),
            const SizedBox(width: 8),
            Text(message),
          ],
        ),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: Theme.of(context).colorScheme.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        duration: const Duration(seconds: 4),
      ),
    );
  }
}

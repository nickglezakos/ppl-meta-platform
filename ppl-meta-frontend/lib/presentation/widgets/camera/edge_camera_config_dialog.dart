import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../services/edge_camera_api_client.dart';
import '../../../services/auth_manager.dart';

/// Dialog for configuring edge camera platform connection
class EdgeCameraConfigDialog extends ConsumerStatefulWidget {
  final String deviceId;
  final String cameraName;
  final Map<String, dynamic>? existingConfig;

  const EdgeCameraConfigDialog({
    super.key,
    required this.deviceId,
    required this.cameraName,
    this.existingConfig,
  });

  @override
  ConsumerState<EdgeCameraConfigDialog> createState() =>
      _EdgeCameraConfigDialogState();
}

class _EdgeCameraConfigDialogState
    extends ConsumerState<EdgeCameraConfigDialog> {
  final _formKey = GlobalKey<FormState>();
  final _discoveryIpController = TextEditingController();
  final _camerasPortController = TextEditingController();
  final _vmetsPortController = TextEditingController();
  final _apiKeyController = TextEditingController();

  bool _useNginx = true;
  bool _isLoading = false;
  bool _showApiKey = false;

  @override
  void initState() {
    super.initState();

    // Load existing configuration if available
    if (widget.existingConfig != null) {
      final config = widget.existingConfig!;
      _discoveryIpController.text =
          config['discovery_service_ip']?.toString() ?? '';
      _camerasPortController.text =
          config['cameras_service_port']?.toString() ?? '8005';
      _vmetsPortController.text =
          config['vmeta_service_port']?.toString() ?? '8008';
      _apiKeyController.text = config['api_key']?.toString() ?? '';
      _useNginx = config['use_nginx_proxy'] as bool? ?? true;
    } else {
      // Defaults
      _camerasPortController.text = '8005';
      _vmetsPortController.text = '8008';
    }
  }

  @override
  void dispose() {
    _discoveryIpController.dispose();
    _camerasPortController.dispose();
    _vmetsPortController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 550,
        constraints: const BoxConstraints(maxHeight: 750),
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(),
              const SizedBox(height: 24),
              _buildForm(),
              const SizedBox(height: 24),
              _buildConfigPreview(),
              const SizedBox(height: 24),
              _buildActions(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Icon(
          Icons.settings_remote,
          color: Theme.of(context).colorScheme.primary,
          size: 28,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Configure Platform Connection',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                widget.cameraName,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey,
                    ),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.close),
        ),
      ],
    );
  }

  Widget _buildForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Discovery Service',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 12),
          _buildTextField(
            controller: _discoveryIpController,
            label: 'Discovery Service IP',
            hint: '192.168.1.100 or discovery.example.com',
            icon: Icons.dns,
            validator: (value) {
              if (value?.isEmpty ?? true) {
                return 'Please enter discovery service IP/hostname';
              }
              return null;
            },
          ),
          const SizedBox(height: 24),
          Text(
            'Service Ports',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildTextField(
                  controller: _camerasPortController,
                  label: 'Cameras Port',
                  hint: '8005',
                  icon: Icons.videocam,
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Required';
                    }
                    final port = int.tryParse(value!);
                    if (port == null || port < 1 || port > 65535) {
                      return 'Invalid port';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildTextField(
                  controller: _vmetsPortController,
                  label: 'VMeta Port',
                  hint: '8008',
                  icon: Icons.analytics,
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Required';
                    }
                    final port = int.tryParse(value!);
                    if (port == null || port < 1 || port > 65535) {
                      return 'Invalid port';
                    }
                    return null;
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            'Authentication',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 12),
          _buildTextField(
            controller: _apiKeyController,
            label: 'API Key',
            hint: 'Optional - Leave empty to use JWT tokens',
            icon: Icons.vpn_key,
            obscureText: !_showApiKey,
            suffixIcon: IconButton(
              icon: Icon(
                _showApiKey ? Icons.visibility : Icons.visibility_off,
              ),
              onPressed: () {
                setState(() {
                  _showApiKey = !_showApiKey;
                });
              },
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Network Options',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            value: _useNginx,
            onChanged: (value) {
              setState(() {
                _useNginx = value;
              });
            },
            title: const Text('Use Nginx Proxy'),
            subtitle: Text(
              _useNginx
                  ? 'Route via Nginx reverse proxy (recommended)'
                  : 'Direct connection to services',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            secondary: Icon(
              _useNginx ? Icons.security : Icons.link_off,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    String? Function(String?)? validator,
    TextInputType? keyboardType,
    bool obscureText = false,
    Widget? suffixIcon,
  }) {
    return TextFormField(
      controller: controller,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(icon),
        suffixIcon: suffixIcon,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      keyboardType: keyboardType,
      obscureText: obscureText,
      validator: validator,
    );
  }

  Widget _buildConfigPreview() {
    final discoveryIp = _discoveryIpController.text;
    final camerasPort = _camerasPortController.text;
    final vmetsPort = _vmetsPortController.text;

    if (discoveryIp.isEmpty) return const SizedBox.shrink();

    final camerasUrl = _useNginx
        ? 'http://$discoveryIp/cameras'
        : 'http://$discoveryIp:$camerasPort';
    final vmetsUrl = _useNginx
        ? 'http://$discoveryIp/vmeta'
        : 'http://$discoveryIp:$vmetsPort';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.info_outline,
                size: 20,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                'Configuration Preview',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildPreviewRow('Discovery IP', discoveryIp),
          _buildPreviewRow('Cameras URL', camerasUrl),
          _buildPreviewRow('VMeta URL', vmetsUrl),
          _buildPreviewRow('Proxy', _useNginx ? 'Enabled' : 'Disabled'),
          if (_apiKeyController.text.isNotEmpty)
            _buildPreviewRow('API Key', '•' * 8 + ' (configured)'),
        ],
      ),
    );
  }

  Widget _buildPreviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontFamily: 'monospace',
                  ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActions() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        const SizedBox(width: 12),
        FilledButton.icon(
          onPressed: _isLoading ? null : _handleSave,
          icon: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.save),
          label: const Text('Save Configuration'),
        ),
      ],
    );
  }

  Future<void> _handleSave() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final baseUrl = 'http://localhost:8005'; // TODO: Get from config
      final prefs = await SharedPreferences.getInstance();
      final authManager = AuthManager(prefs);

      final apiClient = EdgeCameraApiClient(
        baseUrl: baseUrl,
        authManager: authManager,
      );

      final response = await apiClient.configurePlatform(
        widget.deviceId,
        discoveryIp: _discoveryIpController.text.trim(),
        camerasPort: int.parse(_camerasPortController.text.trim()),
        useNginx: _useNginx,
        apiKey: _apiKeyController.text.trim().isEmpty 
            ? null 
            : _apiKeyController.text.trim(),
      );

      if (mounted) {
        if (response.isSuccess) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('✅ Platform configuration saved successfully'),
              backgroundColor: Colors.green,
            ),
          );
          Navigator.of(context).pop(true);
        } else {
          throw Exception(response.error ?? 'Configuration failed');
        }
      }
    } catch (e) {
      if (mounted) {
        String errorMessage = 'Error: $e';

        // Parse specific error messages
        if (e.toString().contains('404')) {
          errorMessage = 'Edge camera not found or offline';
        } else if (e.toString().contains('401') ||
            e.toString().contains('403')) {
          errorMessage = 'Authentication error. Please log in again.';
        } else if (e.toString().contains('400')) {
          errorMessage = 'Invalid configuration. Please check all fields.';
        }

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }
}

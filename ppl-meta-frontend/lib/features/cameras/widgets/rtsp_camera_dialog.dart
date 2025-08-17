import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/rtsp_camera.dart';
import '../../../core/providers/multi_camera_providers.dart';

/// Dialog for adding/editing RTSP camera configuration
class RTSPCameraDialog extends ConsumerStatefulWidget {
  final RTSPCamera? camera;
  final bool isEditing;

  const RTSPCameraDialog({
    super.key,
    this.camera,
    this.isEditing = false,
  });

  @override
  ConsumerState<RTSPCameraDialog> createState() => _RTSPCameraDialogState();
}

class _RTSPCameraDialogState extends ConsumerState<RTSPCameraDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _hostController = TextEditingController();
  final _portController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _streamPathController = TextEditingController();
  
  RTSPTransport _selectedTransport = RTSPTransport.tcp;
  RTSPProfile _selectedProfile = RTSPProfile.main;
  bool _isLoading = false;
  bool _showPassword = false;

  @override
  void initState() {
    super.initState();
    
    if (widget.camera != null) {
      _nameController.text = widget.camera!.name;
      _hostController.text = widget.camera!.host;
      _portController.text = widget.camera!.port.toString();
      _usernameController.text = widget.camera!.username;
      _passwordController.text = widget.camera!.password;
      _streamPathController.text = widget.camera!.streamPath;
      _selectedTransport = widget.camera!.transport;
      _selectedProfile = widget.camera!.profile;
    } else {
      _portController.text = '554';
      _streamPathController.text = '/stream';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _hostController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _streamPathController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 500,
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
          Icons.videocam_outlined,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(width: 12),
        Text(
          widget.isEditing ? 'Edit RTSP Camera' : 'Add RTSP Camera',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const Spacer(),
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
        children: [
          _buildTextField(
            controller: _nameController,
            label: 'Camera Name',
            hint: 'e.g., Front Door Camera',
            icon: Icons.label_outline,
            validator: (value) {
              if (value?.isEmpty ?? true) {
                return 'Please enter a camera name';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                flex: 3,
                child: _buildTextField(
                  controller: _hostController,
                  label: 'Host/IP Address',
                  hint: '192.168.1.100',
                  icon: Icons.computer,
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Please enter host address';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildTextField(
                  controller: _portController,
                  label: 'Port',
                  hint: '554',
                  icon: Icons.settings_ethernet,
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
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildTextField(
                  controller: _usernameController,
                  label: 'Username',
                  hint: 'admin',
                  icon: Icons.person_outline,
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Please enter username';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildTextField(
                  controller: _passwordController,
                  label: 'Password',
                  hint: 'password',
                  icon: Icons.lock_outline,
                  obscureText: !_showPassword,
                  suffixIcon: IconButton(
                    icon: Icon(
                      _showPassword ? Icons.visibility : Icons.visibility_off,
                    ),
                    onPressed: () {
                      setState(() {
                        _showPassword = !_showPassword;
                      });
                    },
                  ),
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Please enter password';
                    }
                    return null;
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildTextField(
            controller: _streamPathController,
            label: 'Stream Path',
            hint: '/stream or /live/main',
            icon: Icons.route,
            validator: (value) {
              if (value?.isEmpty ?? true) {
                return 'Please enter stream path';
              }
              if (!value!.startsWith('/')) {
                return 'Path must start with /';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildDropdown<RTSPTransport>(
                  label: 'Transport',
                  value: _selectedTransport,
                  items: RTSPTransport.values
                      .map((transport) => DropdownMenuItem(
                            value: transport,
                            child: Text(transport.displayName),
                          ))
                      .toList(),
                  onChanged: (transport) {
                    setState(() {
                      _selectedTransport = transport!;
                    });
                  },
                  icon: Icons.swap_horiz,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildDropdown<RTSPProfile>(
                  label: 'Profile',
                  value: _selectedProfile,
                  items: RTSPProfile.values
                      .map((profile) => DropdownMenuItem(
                            value: profile,
                            child: Text(profile.displayName),
                          ))
                      .toList(),
                  onChanged: (profile) {
                    setState(() {
                      _selectedProfile = profile!;
                    });
                  },
                  icon: Icons.tune,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildPreviewUrl(),
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
        border: const OutlineInputBorder(),
        filled: true,
        fillColor: Theme.of(context).colorScheme.surface,
      ),
      validator: validator,
      keyboardType: keyboardType,
      obscureText: obscureText,
    );
  }

  Widget _buildDropdown<T>({
    required String label,
    required T value,
    required List<DropdownMenuItem<T>> items,
    required void Function(T?) onChanged,
    required IconData icon,
  }) {
    return DropdownButtonFormField<T>(
      value: value,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
        filled: true,
        fillColor: Theme.of(context).colorScheme.surface,
      ),
      items: items,
      onChanged: onChanged,
    );
  }

  Widget _buildPreviewUrl() {
    final host = _hostController.text;
    final port = _portController.text;
    final username = _usernameController.text;
    final password = _passwordController.text;
    final streamPath = _streamPathController.text;

    if (host.isEmpty || port.isEmpty || username.isEmpty || password.isEmpty || streamPath.isEmpty) {
      return const SizedBox.shrink();
    }

    final portStr = port != '554' ? ':$port' : '';
    final previewUrl = 'rtsp://$username:***@$host$portStr$streamPath';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.preview,
                size: 16,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 8),
              Text(
                'RTSP URL Preview',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w500,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SelectableText(
            previewUrl,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontFamily: 'monospace',
              color: Theme.of(context).colorScheme.onSurfaceVariant,
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
        ElevatedButton.icon(
          onPressed: _isLoading ? null : _handleSave,
          icon: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Icon(widget.isEditing ? Icons.save : Icons.add),
          label: Text(widget.isEditing ? 'Update Camera' : 'Add Camera'),
        ),
      ],
    );
  }

  Future<void> _handleSave() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final cameraActions = ref.read(cameraActionsProvider);

      if (widget.isEditing && widget.camera != null) {
        // Update existing camera
        final updatedCamera = widget.camera!.copyWith(
          name: _nameController.text.trim(),
          host: _hostController.text.trim(),
          port: int.parse(_portController.text.trim()),
          username: _usernameController.text.trim(),
          password: _passwordController.text.trim(),
          streamPath: _streamPathController.text.trim(),
          transport: _selectedTransport,
          profile: _selectedProfile,
        );

        await cameraActions.updateRTSPCamera(widget.camera!.id, updatedCamera);
      } else {
        // Add new camera
        await cameraActions.addRTSPCamera(
          name: _nameController.text.trim(),
          host: _hostController.text.trim(),
          port: int.parse(_portController.text.trim()),
          username: _usernameController.text.trim(),
          password: _passwordController.text.trim(),
          streamPath: _streamPathController.text.trim(),
        );
      }

      if (mounted) {
        Navigator.of(context).pop(true);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              widget.isEditing
                  ? 'RTSP camera updated successfully'
                  : 'RTSP camera added successfully',
            ),
            backgroundColor: Theme.of(context).colorScheme.primary,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}

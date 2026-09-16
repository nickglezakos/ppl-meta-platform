import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/rtsp_camera.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/multi_camera_providers.dart';
import '../../../core/providers/camera_providers.dart';

/// Dialog for adding/editing RTSP camera configuration
class RTSPCameraDialog extends ConsumerStatefulWidget {
  final Camera? camera; // Changed from RTSPCamera to Camera
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
    
    if (widget.camera != null && widget.isEditing) {
      _nameController.text = widget.camera!.name;

      // Prefer structured fields from API (avoids broken URL parsing / double-encoding).
      final meta = widget.camera!.metadata ?? const <String, dynamic>{};
      final metaUser = meta['username']?.toString();
      final metaPort = meta['port']?.toString();
      final rtspUrl = _rtspUrlFromCamera(widget.camera!);

      if (metaUser != null && metaUser.isNotEmpty) {
        _usernameController.text = metaUser;
      }
      if (metaPort != null && metaPort.isNotEmpty) {
        _portController.text = metaPort;
      }

      if (rtspUrl != null && rtspUrl.startsWith('rtsp://')) {
        _populateFieldsFromRtspUrl(
          rtspUrl,
          fillUsername: _usernameController.text.isEmpty,
          fillPort: _portController.text.isEmpty,
        );
      } else if (_portController.text.isEmpty) {
        _portController.text = '554';
        _streamPathController.text = '/stream1';
      }
      if (_streamPathController.text.isEmpty) {
        _streamPathController.text = '/stream1';
      }
      // Never pre-fill password from URL — user re-enters on change; blank keeps existing.
      _passwordController.clear();
    } else {
      _portController.text = '554';
      _streamPathController.text = '/stream1';
    }
  }

  /// Prefer connection_string from API metadata; never parse deviceId/manufacturer.
  String? _rtspUrlFromCamera(Camera camera) {
    final fromMeta = camera.metadata?['connection_string']?.toString();
    if (fromMeta != null && fromMeta.startsWith('rtsp://')) return fromMeta;
    final stream = camera.streamUrl;
    if (stream != null && stream.startsWith('rtsp://')) return stream;
    return null;
  }

  /// Split credentials on the *last* '@' so email usernames (user@domain) work.
  void _populateFieldsFromRtspUrl(
    String rtspUrl, {
    bool fillUsername = true,
    bool fillPort = true,
  }) {
    try {
      var remaining = rtspUrl.substring('rtsp://'.length);

      final at = remaining.lastIndexOf('@');
      if (at >= 0) {
        final credentials = remaining.substring(0, at);
        remaining = remaining.substring(at + 1);
        if (fillUsername) {
          final colon = credentials.indexOf(':');
          if (colon >= 0) {
            _usernameController.text =
                Uri.decodeComponent(credentials.substring(0, colon));
          } else {
            _usernameController.text = Uri.decodeComponent(credentials);
          }
        }
      }

      final slash = remaining.indexOf('/');
      final hostPort = slash >= 0 ? remaining.substring(0, slash) : remaining;
      _streamPathController.text =
          slash >= 0 ? remaining.substring(slash) : '/stream1';

      final colon = hostPort.lastIndexOf(':');
      if (colon > 0 && !hostPort.contains(']')) {
        _hostController.text = hostPort.substring(0, colon);
        if (fillPort) {
          _portController.text = hostPort.substring(colon + 1);
        }
      } else {
        _hostController.text = hostPort;
        if (fillPort) {
          _portController.text = '554';
        }
      }
    } catch (_) {
      if (fillPort) _portController.text = '554';
      if (_streamPathController.text.isEmpty) {
        _streamPathController.text = '/stream1';
      }
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
        constraints: const BoxConstraints(maxHeight: 700),
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
              _buildUrlPreview(),
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

  Widget _buildUrlPreview() {
    final host = _hostController.text;
    final port = _portController.text;
    final path = _streamPathController.text;
    final username = _usernameController.text;
    
    if (host.isEmpty) return const SizedBox.shrink();
    
    final url = 'rtsp://${username.isNotEmpty ? "$username:****@" : ""}$host${port.isNotEmpty ? ":$port" : ""}$path';
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'RTSP URL Preview:',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            url,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontFamily: 'monospace',
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
        FilledButton(
          onPressed: _isLoading ? null : _handleSave,
          child: _isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(widget.isEditing ? 'Update' : 'Add Camera'),
        ),
      ],
    );
  }

  Future<void> _handleSave() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final cameraActions = ref.read(cameraActionsProvider);
      
      final name = _nameController.text.trim();
      final host = _hostController.text.trim();
      final port = int.parse(_portController.text.trim());
      final username = _usernameController.text.trim();
      final password = _passwordController.text.trim();
      final streamPath = _streamPathController.text.trim();

      if (widget.isEditing && widget.camera != null) {
        // Update existing camera
        print('🔧 Updating RTSP camera: ${widget.camera!.deviceId}');
        print('   New host: $host:$port');
        print('   Username: $username (${username.length} chars)');
        
        final success = await cameraActions.updateRTSPCamera(
          widget.camera!.deviceId,
          RTSPCamera(
            id: widget.camera!.deviceId,
            name: name,
            host: host,
            port: port,
            username: username,
            password: password,
            streamPath: streamPath,
            transport: _selectedTransport,
            profile: _selectedProfile,
          ),
        );
        
        if (success != null) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Camera updated: $host:$port')),
            );
            Navigator.of(context).pop(true);
          }
        } else {
          throw Exception('Failed to update camera - received null response');
        }
      } else {
        // Add new camera
        print('➕ Adding new RTSP camera: $name');
        print('   Host: $host:$port');
        print('   Username: $username');
        
        final camera = await cameraActions.addRTSPCamera(
          name: name,
          host: host,
          port: port,
          username: username,
          password: password,
          streamPath: streamPath,
        );
        
        if (camera != null) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Camera added successfully')),
            );
            Navigator.of(context).pop(true);
          }
        } else {
          throw Exception('Failed to add camera - received null response');
        }
      }
    } catch (e, stackTrace) {
      print('❌ Error saving RTSP camera: $e');
      print('Stack trace: $stackTrace');
      
      if (mounted) {
        String errorMessage = 'Error: $e';
        
        // Parse specific error messages
        if (e.toString().contains('Camera with name') && e.toString().contains('already exists')) {
          errorMessage = '❌ A camera with name "${_nameController.text.trim()}" already exists. Please choose a unique name.';
        } else if (e.toString().contains('UNIQUE constraint') || e.toString().contains('duplicate')) {
          errorMessage = '❌ A camera with this name already exists. Please choose a unique name.';
        } else if (e.toString().contains('404')) {
          errorMessage = 'Camera not found. It may have been deleted. Please refresh the camera list.';
        } else if (e.toString().contains('401') || e.toString().contains('403')) {
          errorMessage = 'Authentication error. Please log in again.';
        } else if (e.toString().contains('400')) {
          errorMessage = 'Invalid camera configuration. Please check all fields.';
        }
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 6),
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

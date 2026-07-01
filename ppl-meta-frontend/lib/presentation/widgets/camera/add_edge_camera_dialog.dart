import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../../core/providers/camera_providers.dart';
import '../../../core/config/app_config.dart';


/// Dialog for adding edge camera manually
class AddEdgeCameraDialog extends ConsumerStatefulWidget {
  const AddEdgeCameraDialog({super.key});

  @override
  ConsumerState<AddEdgeCameraDialog> createState() => _AddEdgeCameraDialogState();
}

class _AddEdgeCameraDialogState extends ConsumerState<AddEdgeCameraDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _ipController = TextEditingController();
  final _portController = TextEditingController(text: '9001');
  
  bool _isLoading = false;
  bool _isTesting = false;
  String? _testResult;
  Map<String, dynamic>? _cameraInfo;

  @override
  void dispose() {
    _nameController.dispose();
    _ipController.dispose();
    _portController.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    if (_ipController.text.isEmpty) {
      setState(() {
        _testResult = 'Please enter an IP address';
        _cameraInfo = null;
      });
      return;
    }

    setState(() {
      _isTesting = true;
      _testResult = null;
      _cameraInfo = null;
    });

    try {
      final ip = _ipController.text.trim();
      final port = _portController.text.trim();
      final url = 'http://$ip:$port/api/identify';
      
      final response = await http.get(Uri.parse(url)).timeout(
        const Duration(seconds: 5),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['service'] == 'ppl-edge-camera') {
          setState(() {
            _testResult = '✅ Connection successful!';
            _cameraInfo = data;
            // Auto-fill name if empty
            if (_nameController.text.isEmpty && data['device_id'] != null) {
              _nameController.text = data['device_id'].toString().replaceAll('edge-camera-', 'Edge Camera ');
            }
          });
        } else {
          setState(() {
            _testResult = '❌ Not an edge camera service';
            _cameraInfo = null;
          });
        }
      } else {
        setState(() {
          _testResult = '❌ Connection failed (HTTP ${response.statusCode})';
          _cameraInfo = null;
        });
      }
    } catch (e) {
      setState(() {
        _testResult = '❌ Cannot reach edge camera: ${e.toString().contains('TimeoutException') ? 'Timeout' : 'Connection error'}';
        _cameraInfo = null;
      });
    } finally {
      setState(() {
        _isTesting = false;
      });
    }
  }

  Future<void> _addCamera() async {
    if (!_formKey.currentState!.validate()) return;
    
    if (_cameraInfo == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please test connection first'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final deviceId = _cameraInfo!['device_id'] as String;
      final ip = _ipController.text.trim();
      final port = _portController.text.trim();
      final name = _nameController.text.trim();
      
      // Register edge camera with platform
      // This creates a camera record in the database
      final baseUrl = AppConfig.instance.apiBaseUrl; // Routed via Gateway for VPN/remote access
      final registerUrl = '$baseUrl/api/v1/edge-cameras/register-edge';
      
      final response = await http.post(
        Uri.parse(registerUrl),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': name,
          'device_id': deviceId,
          'ip_address': ip,
          'management_port': int.parse(port),
          'stream_port': _cameraInfo!['stream_port'] ?? 8554,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        if (mounted) {
          // Refresh camera list
          await ref.read(cameraListProvider.notifier).loadCameras();
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('✅ Edge camera "$name" added successfully'),
              backgroundColor: Colors.green,
            ),
          );
          Navigator.of(context).pop(true);
        }
      } else {
        // Parse error response
        try {
          final errorData = json.decode(response.body);
          final errorDetail = errorData['detail'] ?? response.body;
          if (errorDetail.toString().contains('Camera with name') && errorDetail.toString().contains('exists')) {
            throw Exception('❌ A camera with name "$name" already exists. Please choose a unique name.');
          } else if (errorDetail.toString().contains('UNIQUE constraint') || errorDetail.toString().contains('duplicate')) {
            throw Exception('❌ A camera with this name already exists. Please choose a unique name.');
          } else {
            throw Exception('Registration failed: $errorDetail');
          }
        } catch (parseError) {
          // If error response isn't JSON, use raw body
          if (response.body.contains('Camera with name') || response.body.contains('duplicate')) {
            throw Exception('❌ A camera with name "$name" already exists. Please choose a unique name.');
          }
          throw Exception('Registration failed: ${response.body}');
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error adding camera: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 550,
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
              const SizedBox(height: 16),
              _buildTestSection(),
              if (_cameraInfo != null) ...[
                const SizedBox(height: 16),
                _buildCameraInfo(),
              ],
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
          Icons.camera_outdoor,
          color: Theme.of(context).colorScheme.primary,
          size: 28,
        ),
        const SizedBox(width: 12),
        const Text(
          'Add Edge Camera',
          style: TextStyle(
            fontSize: 20,
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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextFormField(
            controller: _nameController,
            decoration: InputDecoration(
              labelText: 'Camera Name',
              hintText: 'e.g., Living Room Camera',
              prefixIcon: const Icon(Icons.label_outline),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
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
                child: TextFormField(
                  controller: _ipController,
                  decoration: InputDecoration(
                    labelText: 'IP Address',
                    hintText: '192.168.1.150',
                    prefixIcon: const Icon(Icons.router),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  onChanged: (_) {
                    // Clear test result when IP changes
                    setState(() {
                      _testResult = null;
                      _cameraInfo = null;
                    });
                  },
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Required';
                    }
                    // Basic IP validation
                    final ipRegex = RegExp(r'^(\d{1,3}\.){3}\d{1,3}$');
                    if (!ipRegex.hasMatch(value!)) {
                      return 'Invalid IP';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextFormField(
                  controller: _portController,
                  decoration: InputDecoration(
                    labelText: 'Port',
                    hintText: '9001',
                    prefixIcon: const Icon(Icons.settings_ethernet),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value?.isEmpty ?? true) {
                      return 'Required';
                    }
                    final port = int.tryParse(value!);
                    if (port == null || port < 1 || port > 65535) {
                      return 'Invalid';
                    }
                    return null;
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTestSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ElevatedButton.icon(
          onPressed: _isTesting ? null : _testConnection,
          icon: _isTesting
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.wifi_find),
          label: Text(_isTesting ? 'Testing...' : 'Test Connection'),
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 12),
          ),
        ),
        if (_testResult != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: _testResult!.startsWith('✅')
                  ? Colors.green.withOpacity(0.1)
                  : Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _testResult!.startsWith('✅')
                    ? Colors.green
                    : Colors.red,
              ),
            ),
            child: Text(
              _testResult!,
              style: TextStyle(
                color: _testResult!.startsWith('✅')
                    ? Colors.green.shade700
                    : Colors.red.shade700,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildCameraInfo() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.info_outline, size: 20, color: Colors.blue),
              SizedBox(width: 8),
              Text(
                'Edge Camera Information',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildInfoRow('Device ID', _cameraInfo!['device_id']?.toString() ?? 'Unknown'),
          _buildInfoRow('Management Port', _cameraInfo!['management_port']?.toString() ?? '9001'),
          _buildInfoRow('Stream Port', _cameraInfo!['stream_port']?.toString() ?? '8554'),
          if (_cameraInfo!['status'] != null)
            _buildInfoRow('Status', _cameraInfo!['status']?.toString() ?? 'Unknown'),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
                fontWeight: FontWeight.w500,
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
          onPressed: _isLoading || _cameraInfo == null ? null : _addCamera,
          icon: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.add),
          label: const Text('Add Camera'),
        ),
      ],
    );
  }
}

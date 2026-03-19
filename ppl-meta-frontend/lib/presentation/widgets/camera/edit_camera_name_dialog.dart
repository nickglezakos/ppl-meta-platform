import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../../core/models/camera.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/services/auth_service.dart';

/// Dialog for editing camera name
class EditCameraNameDialog extends ConsumerStatefulWidget {
  final Camera camera;

  const EditCameraNameDialog({
    super.key,
    required this.camera,
  });

  @override
  ConsumerState<EditCameraNameDialog> createState() => _EditCameraNameDialogState();
}

class _EditCameraNameDialogState extends ConsumerState<EditCameraNameDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.camera.name);
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _updateName() async {
    if (!_formKey.currentState!.validate()) return;
    
    final newName = _nameController.text.trim();
    
    // If name hasn't changed, just close
    if (newName == widget.camera.name) {
      Navigator.of(context).pop();
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Get auth token
      final authService = ref.read(authServiceProvider);
      final token = await authService.getToken();
      
      if (token == null) {
        throw Exception('Authentication required');
      }

      // Call PATCH endpoint to update camera name
      final baseUrl = 'http://localhost:8005'; // TODO: Get from config
      final url = '$baseUrl/api/v1/cameras/${widget.camera.deviceId}/name';
      
      final response = await http.patch(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: json.encode({
          'name': newName,
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        if (mounted) {
          // Refresh camera list
          await ref.read(cameraListProvider.notifier).loadCameras();
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('✅ Camera renamed to "$newName"'),
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
            setState(() {
              _errorMessage = '❌ A camera with name "$newName" already exists';
            });
          } else if (errorDetail.toString().contains('UNIQUE constraint') || errorDetail.toString().contains('duplicate')) {
            setState(() {
              _errorMessage = '❌ This name is already in use';
            });
          } else {
            setState(() {
              _errorMessage = errorDetail.toString();
            });
          }
        } catch (parseError) {
          // If error response isn't JSON, check raw body
          if (response.body.contains('Camera with name') || response.body.contains('duplicate')) {
            setState(() {
              _errorMessage = '❌ A camera with name "$newName" already exists';
            });
          } else {
            setState(() {
              _errorMessage = 'Update failed (${response.statusCode})';
            });
          }
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          if (e.toString().contains('TimeoutException')) {
            _errorMessage = 'Request timed out. Please try again.';
          } else if (e.toString().contains('Authentication')) {
            _errorMessage = 'Authentication error. Please log in again.';
          } else {
            _errorMessage = 'Error: ${e.toString()}';
          }
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.edit, size: 20),
          SizedBox(width: 8),
          Text('Rename Camera'),
        ],
      ),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Enter a new name for this camera:',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _nameController,
              autofocus: true,
              maxLength: 255,
              decoration: InputDecoration(
                labelText: 'Camera Name',
                hintText: 'e.g., Front Door Camera',
                prefixIcon: const Icon(Icons.label_outline),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                errorText: _errorMessage,
              ),
              validator: (value) {
                if (value?.trim().isEmpty ?? true) {
                  return 'Please enter a camera name';
                }
                if (value!.length > 255) {
                  return 'Name must be 255 characters or less';
                }
                return null;
              },
              onFieldSubmitted: (_) => _updateName(),
            ),
            const SizedBox(height: 8),
            Text(
              'Original name: ${widget.camera.name}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey,
                fontStyle: FontStyle.italic,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, size: 16, color: Colors.blue),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Camera names must be unique',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.blue.shade700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _isLoading ? null : _updateName,
          child: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Rename'),
        ),
      ],
    );
  }
}

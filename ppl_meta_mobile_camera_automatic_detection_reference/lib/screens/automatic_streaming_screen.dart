import 'package:flutter/material.dart';
import '../services/automatic_streaming_workflow.dart';

/// Streamlined UI for automatic streaming workflow
/// 
/// This screen provides the simplest possible interface:
/// - Username and password (PPL Meta credentials)
/// - Camera name (user's choice)
/// - One button to execute complete automatic workflow
class AutomaticStreamingScreen extends StatefulWidget {
  const AutomaticStreamingScreen({Key? key}) : super(key: key);

  @override
  State<AutomaticStreamingScreen> createState() => _AutomaticStreamingScreenState();
}

class _AutomaticStreamingScreenState extends State<AutomaticStreamingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _cameraNameController = TextEditingController();
  
  final AutomaticStreamingWorkflow _workflow = AutomaticStreamingWorkflow();
  
  bool _isExecuting = false;
  WorkflowResult? _result;
  
  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _cameraNameController.dispose();
    super.dispose();
  }
  
  Future<void> _executeAutomaticWorkflow() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    
    setState(() {
      _isExecuting = true;
      _result = null;
    });
    
    try {
      final result = await _workflow.executeCompleteWorkflow(
        username: _usernameController.text.trim(),
        password: _passwordController.text.trim(),
        cameraName: _cameraNameController.text.trim(),
      );
      
      setState(() {
        _result = result;
        _isExecuting = false;
      });
      
      if (result.success) {
        _showSuccessDialog(result);
      } else {
        _showErrorDialog(result.error ?? 'Unknown error occurred');
      }
      
    } catch (e) {
      setState(() {
        _isExecuting = false;
        _result = WorkflowResult.failure(error: e.toString());
      });
      _showErrorDialog(e.toString());
    }
  }
  
  void _showSuccessDialog(WorkflowResult result) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 28),
            SizedBox(width: 12),
            Text('Workflow Complete!'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('🎉 Camera "${result.cameraName}" is ready for streaming!'),
            const SizedBox(height: 16),
            const Text('Automatic Configuration Results:', 
                style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            _buildResultRow('📊 Camera ID', result.cameraId.toString()),
            _buildResultRow('🆔 Device ID', result.deviceId ?? 'Unknown'),
            _buildResultRow('📹 Camera Service', result.cameraServiceURL ?? 'Unknown'),
            _buildResultRow('🎬 Media Service', result.mediaServiceURL ?? 'Unknown'),
            _buildResultRow('🌐 Gateway Service', result.gatewayServiceURL ?? 'Unknown'),
            const SizedBox(height: 12),
            const Text(
              '✅ Everything configured automatically!\nYour camera is now ready to stream.',
              style: TextStyle(color: Colors.green, fontWeight: FontWeight.w500),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Great!'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _navigateToStreaming(result);
            },
            child: const Text('Start Streaming'),
          ),
        ],
      ),
    );
  }
  
  void _showErrorDialog(String error) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.error, color: Colors.red, size: 28),
            SizedBox(width: 12),
            Text('Workflow Failed'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('❌ The automatic workflow encountered an error:'),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Text(
                error,
                style: TextStyle(
                  fontFamily: 'monospace',
                  color: Colors.red.shade800,
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              '💡 Please check:\n'
              '• Network connection\n'
              '• PPL Meta platform services are running\n'
              '• Username and password are correct',
              style: TextStyle(fontSize: 14),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Try Again'),
          ),
        ],
      ),
    );
  }
  
  Widget _buildResultRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: const TextStyle(fontSize: 12)),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }
  
  void _navigateToStreaming(WorkflowResult result) {
    // TODO: Navigate to streaming screen with all configuration
    // This would pass the camera ID, service URLs, and JWT token
    // to the streaming interface
    print('🎥 Navigate to streaming with camera ID: ${result.cameraId}');
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('🚀 Automatic Streaming'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header explanation
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.auto_awesome,
                            color: Theme.of(context).colorScheme.primary,
                            size: 28,
                          ),
                          const SizedBox(width: 12),
                          const Text(
                            'Zero Configuration Setup',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Just enter your credentials and camera name.\n'
                        'Everything else is configured automatically:\n'
                        '• Auto-detect your network IP\n'
                        '• Find PPL Meta services\n'
                        '• Register your camera\n'
                        '• Configure streaming endpoints',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Username field
              TextFormField(
                controller: _usernameController,
                decoration: InputDecoration(
                  labelText: 'PPL Meta Username',
                  prefixIcon: const Icon(Icons.person),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter your username';
                  }
                  return null;
                },
                enabled: !_isExecuting,
              ),
              
              const SizedBox(height: 16),
              
              // Password field
              TextFormField(
                controller: _passwordController,
                decoration: InputDecoration(
                  labelText: 'PPL Meta Password',
                  prefixIcon: const Icon(Icons.lock),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                obscureText: true,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter your password';
                  }
                  return null;
                },
                enabled: !_isExecuting,
              ),
              
              const SizedBox(height: 16),
              
              // Camera name field
              TextFormField(
                controller: _cameraNameController,
                decoration: InputDecoration(
                  labelText: 'Camera Name',
                  prefixIcon: const Icon(Icons.videocam),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  hintText: 'e.g., "Living Room Camera"',
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter a camera name';
                  }
                  return null;
                },
                enabled: !_isExecuting,
              ),
              
              const SizedBox(height: 32),
              
              // Execute workflow button
              ElevatedButton(
                onPressed: _isExecuting ? null : _executeAutomaticWorkflow,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _isExecuting
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                          SizedBox(width: 12),
                          Text('Executing Automatic Workflow...'),
                        ],
                      )
                    : const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.rocket_launch),
                          SizedBox(width: 8),
                          Text('Start Automatic Setup'),
                        ],
                      ),
              ),
              
              const SizedBox(height: 16),
              
              // Status display
              if (_result != null) ...[
                Card(
                  color: _result!.success 
                      ? Colors.green.shade50 
                      : Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              _result!.success 
                                  ? Icons.check_circle 
                                  : Icons.error,
                              color: _result!.success 
                                  ? Colors.green 
                                  : Colors.red,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              _result!.success 
                                  ? 'Workflow Completed Successfully!' 
                                  : 'Workflow Failed',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: _result!.success 
                                    ? Colors.green.shade800 
                                    : Colors.red.shade800,
                              ),
                            ),
                          ],
                        ),
                        if (_result!.success) ...[
                          const SizedBox(height: 8),
                          Text('🎉 Camera "${_result!.cameraName}" is ready!'),
                          Text('📊 Camera ID: ${_result!.cameraId}'),
                          Text('🎬 Ready for streaming'),
                        ] else ...[
                          const SizedBox(height: 8),
                          Text('Error: ${_result!.error}'),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
              
              const Spacer(),
              
              // Footer info
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(12.0),
                  child: Text(
                    '💡 This workflow automatically discovers your network settings and configures everything needed for camera streaming. No manual IP configuration required!',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

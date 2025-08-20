import 'package:flutter/material.dart';
import '../../../core/services/auto_streaming_service.dart';

class AutoStreamingScreen extends StatefulWidget {
  const AutoStreamingScreen({super.key});

  @override
  State<AutoStreamingScreen> createState() => _AutoStreamingScreenState();
}

class _AutoStreamingScreenState extends State<AutoStreamingScreen> {
  final _cameraNameController = TextEditingController();
  final _autoStreamingService = AutoStreamingService();
  
  bool _isLoading = false;
  String? _statusMessage;
  String? _errorMessage;
  AutoStreamingResult? _result;

  @override
  void initState() {
    super.initState();
    _checkExistingCamera();
  }

  @override
  void dispose() {
    _cameraNameController.dispose();
    super.dispose();
  }

  /// Check if there's already a registered camera
  Future<void> _checkExistingCamera() async {
    final lastCamera = await _autoStreamingService.getLastRegisteredCamera();
    if (lastCamera != null) {
      _cameraNameController.text = lastCamera['name'];
      setState(() {
        _statusMessage = 'Camera "${lastCamera['name']}" was previously registered (ID: ${lastCamera['id']})';
      });
    }
  }

  /// Start the automatic streaming workflow
  Future<void> _startAutomaticStreaming() async {
    final cameraName = _cameraNameController.text.trim();
    
    if (cameraName.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter a camera name';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _statusMessage = 'Starting automatic streaming workflow...';
    });

    try {
      // Step-by-step status updates
      setState(() {
        _statusMessage = '🔐 Authenticating with platform...';
      });
      
      await Future.delayed(const Duration(milliseconds: 500));
      
      setState(() {
        _statusMessage = '🔍 Discovering platform services...';
      });
      
      await Future.delayed(const Duration(milliseconds: 500));
      
      setState(() {
        _statusMessage = '📹 Connecting to Camera service...';
      });
      
      await Future.delayed(const Duration(milliseconds: 500));
      
      setState(() {
        _statusMessage = '📱 Registering mobile camera...';
      });

      // Execute the actual workflow
      final result = await _autoStreamingService.startAutomaticStreaming(cameraName);
      
      setState(() {
        _isLoading = false;
        _result = result;
        
        if (result.success) {
          _statusMessage = '✅ Camera "$cameraName" is ready for streaming!\n'
              'Camera ID: ${result.cameraId}\n'
              'Services connected successfully';
          _errorMessage = null;
        } else {
          _errorMessage = result.error;
          _statusMessage = null;
        }
      });

      if (result.success) {
        // Initialize camera for streaming (placeholder for now)
        // final cameraProvider = Provider.of<CameraProvider>(context, listen: false);
        // await cameraProvider.initialize();  
      }

    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Workflow failed: $e';
        _statusMessage = null;
      });
    }
  }

  /// Start streaming (after successful registration)
  Future<void> _startStreaming() async {
    if (_result?.success != true) return;

    // final cameraProvider = Provider.of<CameraProvider>(context, listen: false);
    
    setState(() {
      _isLoading = true;
      _statusMessage = '🎬 Starting video stream...';
    });

    try {
      // Here you would implement the actual streaming logic
      // For now, just simulate the process
      await Future.delayed(const Duration(seconds: 2));
      
      setState(() {
        _isLoading = false;
        _statusMessage = '🔴 LIVE: Streaming to platform';
      });

    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to start streaming: $e';
      });
    }
  }

  /// Clear camera registration
  Future<void> _clearRegistration() async {
    await _autoStreamingService.clearStreamingState();
    _cameraNameController.clear();
    setState(() {
      _result = null;
      _statusMessage = null;
      _errorMessage = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PPL Meta Mobile Camera'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          if (_result?.success == true)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _clearRegistration,
              tooltip: 'Reset camera registration',
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Icon(
                      Icons.videocam,
                      size: 48,
                      color: Theme.of(context).primaryColor,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Automatic Streaming Setup',
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Just enter your camera name - everything else is automatic!',
                      style: Theme.of(context).textTheme.bodyMedium,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Camera name input
            TextField(
              controller: _cameraNameController,
              decoration: const InputDecoration(
                labelText: 'Camera Name',
                hintText: 'e.g., Living Room Camera, Front Door, Kitchen Monitor',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.camera_alt),
              ),
              enabled: !_isLoading,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _startAutomaticStreaming(),
            ),
            
            const SizedBox(height: 24),
            
            // Action buttons
            if (_result?.success != true) ...[
              ElevatedButton(
                onPressed: _isLoading ? null : _startAutomaticStreaming,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isLoading
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                          SizedBox(width: 12),
                          Text('Setting up...'),
                        ],
                      )
                    : const Text(
                        'Start Automatic Setup',
                        style: TextStyle(fontSize: 16),
                      ),
              ),
            ] else ...[
              // Success state - show streaming button
              ElevatedButton.icon(
                onPressed: _isLoading ? null : _startStreaming,
                icon: const Icon(Icons.play_circle_fill),
                label: _isLoading
                    ? const Text('Starting Stream...')
                    : const Text('Start Streaming'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ],
            
            const SizedBox(height: 24),
            
            // Status messages
            if (_statusMessage != null)
              Card(
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.info_outline,
                            color: Colors.blue.shade700,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Status',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.blue.shade700,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _statusMessage!,
                        style: const TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ),
            
            if (_errorMessage != null)
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.error_outline,
                            color: Colors.red.shade700,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Error',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.red.shade700,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _errorMessage!,
                        style: const TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ),
            
            // Success details
            if (_result?.success == true)
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.check_circle_outline,
                            color: Colors.green.shade700,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Setup Complete',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.green.shade700,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('Camera ID: ${_result!.cameraId}'),
                      Text('Camera Service: ${_result!.cameraServiceUrl}'),
                      Text('Media Service: ${_result!.mediaServiceUrl}'),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

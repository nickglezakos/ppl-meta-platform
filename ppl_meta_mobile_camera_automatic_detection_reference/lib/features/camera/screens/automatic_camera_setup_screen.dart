import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../services/automatic_streaming_workflow.dart';
import '../../../core/providers/authentication_provider.dart';
import 'camera_screen.dart';

class AutomaticCameraSetupScreen extends StatefulWidget {
  const AutomaticCameraSetupScreen({super.key});

  @override
  State<AutomaticCameraSetupScreen> createState() => _AutomaticCameraSetupScreenState();
}

class _AutomaticCameraSetupScreenState extends State<AutomaticCameraSetupScreen> {
  final _cameraNameController = TextEditingController();
  final _workflow = AutomaticStreamingWorkflow();
  
  bool _isLoading = false;
  String? _statusMessage;
  String? _errorMessage;

  @override
  void dispose() {
    _cameraNameController.dispose();
    super.dispose();
  }

  /// Setup camera automatically after user provides name
  Future<void> _setupCameraAutomatically() async {
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
      _statusMessage = 'Setting up camera automatically...';
    });

    try {
      // Get stored credentials for the new automatic workflow
      final authProvider = Provider.of<AuthenticationProvider>(context, listen: false);
      final userData = authProvider.userData;
      
      if (userData == null || userData['username'] == null) {
        throw Exception('No stored credentials found');
      }
      
      final username = userData['username'] as String;
      final password = userData['password'] as String? ?? 'NewPassword234!'; // Default password
      
      setState(() {
        _statusMessage = '� Using simplified IP auto-detection...';
      });
      await Future.delayed(const Duration(milliseconds: 500));
      
      setState(() {
        _statusMessage = '🎯 Discovering Node service with device IP...';
      });
      await Future.delayed(const Duration(milliseconds: 500));
      
      setState(() {
        _statusMessage = '📱 Executing complete automatic workflow...';
      });
      await Future.delayed(const Duration(milliseconds: 500));

      // Execute the NEW simplified automatic workflow
      final result = await _workflow.executeCompleteWorkflow(
        username: username,
        password: password,
        cameraName: cameraName,
      );
      
      if (result.success) {
        setState(() {
          _statusMessage = '✅ Camera "$cameraName" registered successfully!';
        });

        // Mark camera as registered in auth provider
        authProvider.setCameraRegistered(true);

        // Navigate to camera screen after short delay
        await Future.delayed(const Duration(milliseconds: 1500));
        
        print('🔄 Attempting navigation to CameraScreen...');
        
        if (mounted) {
          try {
            // Navigate to the main camera screen
            print('🚀 Navigating to CameraScreen');
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (context) => const CameraScreen(),
              ),
            );
            print('✅ Navigation completed successfully');
          } catch (e) {
            print('❌ Navigation failed: $e');
            // If navigation fails, at least update the UI
            setState(() {
              _statusMessage = '✅ Camera setup complete! Please navigate manually.';
              _isLoading = false;
            });
          }
        } else {
          print('❌ Widget not mounted, cannot navigate');
        }

      } else {
        setState(() {
          _isLoading = false;
          _errorMessage = result.error ?? 'Setup failed';
          _statusMessage = null;
        });
      }

    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Setup failed: $e';
        _statusMessage = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthenticationProvider>(context);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Camera Setup'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        automaticallyImplyLeading: false,
        actions: [
          TextButton(
            onPressed: () async {
              await authProvider.logout();
            },
            child: const Text('Logout'),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Welcome message
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  children: [
                    Icon(
                      Icons.camera_alt,
                      size: 48,
                      color: Theme.of(context).primaryColor,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Welcome ${authProvider.userData?['username'] ?? 'User'}!',
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Set up your mobile camera automatically',
                      style: Theme.of(context).textTheme.bodyLarge,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 32),
            
            // Camera name input
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Camera Name',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Enter camera name',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey.shade600,
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _cameraNameController,
                      decoration: InputDecoration(
                        hintText: 'e.g., Living Room, Front Door, Kitchen',
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.videocam),
                        suffixIcon: _cameraNameController.text.isNotEmpty
                            ? IconButton(
                                icon: const Icon(Icons.clear),
                                onPressed: () {
                                  _cameraNameController.clear();
                                  setState(() {});
                                },
                              )
                            : null,
                      ),
                      enabled: !_isLoading,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _setupCameraAutomatically(),
                      onChanged: (_) => setState(() {}),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Setup button
            ElevatedButton(
              onPressed: _isLoading ? null : _setupCameraAutomatically,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Theme.of(context).primaryColor,
                foregroundColor: Colors.white,
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
                        Text('Setting up camera...'),
                      ],
                    )
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.auto_awesome),
                        SizedBox(width: 8),
                        Text(
                          'Setup Camera Automatically',
                          style: TextStyle(fontSize: 16),
                        ),
                      ],
                    ),
            ),
            
            const SizedBox(height: 24),
            
            // Status messages
            if (_statusMessage != null)
              Card(
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      if (_isLoading)
                        const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      else
                        Icon(
                          Icons.check_circle,
                          color: Colors.green.shade700,
                        ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _statusMessage!,
                          style: const TextStyle(fontSize: 14),
                        ),
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
                  child: Row(
                    children: [
                      Icon(
                        Icons.error_outline,
                        color: Colors.red.shade700,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            
            const Spacer(),
            
            // Info card
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
                          Icons.info_outline,
                          color: Colors.green.shade700,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Automatic Setup',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.green.shade700,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Automatically discovers services and registers camera',
                      style: TextStyle(fontSize: 14),
                    ),
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

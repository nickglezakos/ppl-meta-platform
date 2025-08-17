import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/camera_auth_service.dart';
import '../services/camera_service.dart';

/// Camera Authentication Demo Screen
/// 
/// Demonstrates CAM-FLUTTER-001 implementation with login/logout functionality
/// and camera service integration testing
class CameraAuthDemoScreen extends StatefulWidget {
  const CameraAuthDemoScreen({super.key});

  @override
  State<CameraAuthDemoScreen> createState() => _CameraAuthDemoScreenState();
}

class _CameraAuthDemoScreenState extends State<CameraAuthDemoScreen> {
  final _emailController = TextEditingController(text: 'fresh.user@example.com');
  final _passwordController = TextEditingController(text: 'NewPassword234!');
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;
  String? _statusMessage;

  @override
  void initState() {
    super.initState();
    // Initialize authentication service
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<CameraAuthService>(context, listen: false).initialize();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Camera Authentication Demo'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Consumer2<CameraAuthService, CameraService>(
        builder: (context, authService, cameraService, child) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Authentication Status Card
                _buildStatusCard(authService),
                
                const SizedBox(height: 16),
                
                // Authentication Form or User Info
                if (!authService.isAuthenticated) ...[
                  _buildLoginForm(authService),
                ] else ...[
                  _buildUserInfo(authService),
                  const SizedBox(height: 16),
                  _buildCameraControls(cameraService),
                ],
                
                // Status Messages
                if (_statusMessage != null) ...[
                  const SizedBox(height: 16),
                  Card(
                    color: Colors.blue.shade50,
                    child: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Text(
                        _statusMessage!,
                        style: const TextStyle(color: Colors.blue),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatusCard(CameraAuthService authService) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  authService.isAuthenticated ? Icons.check_circle : Icons.error,
                  color: authService.isAuthenticated ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Text(
                  'Authentication Status',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              authService.isAuthenticated ? 'Authenticated' : 'Not Authenticated',
              style: TextStyle(
                color: authService.isAuthenticated ? Colors.green : Colors.red,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (authService.currentUserEmail != null) ...[
              const SizedBox(height: 4),
              Text('User: ${authService.currentUserEmail}'),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLoginForm(CameraAuthService authService) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Login to Node Service',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 16),
              
              TextFormField(
                controller: _emailController,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.email),
                ),
                keyboardType: TextInputType.emailAddress,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your email';
                  }
                  if (!value.contains('@')) {
                    return 'Please enter a valid email';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 16),
              
              TextFormField(
                controller: _passwordController,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock),
                ),
                obscureText: true,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your password';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 24),
              
              ElevatedButton(
                onPressed: _isLoading ? null : () => _handleLogin(authService),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Login'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildUserInfo(CameraAuthService authService) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Welcome, ${authService.currentUserEmail}!',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _testCameraConnection(authService),
                    icon: const Icon(Icons.videocam),
                    label: const Text('Test Camera Service'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _handleLogout(authService),
                    icon: const Icon(Icons.logout),
                    label: const Text('Logout'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraControls(CameraService cameraService) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Camera Management',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            
            // Camera detection and listing
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: cameraService.isLoading 
                        ? null 
                        : () => _detectCameras(cameraService),
                    icon: const Icon(Icons.search),
                    label: const Text('Detect Cameras'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: cameraService.isLoading 
                        ? null 
                        : () => _getCameras(cameraService),
                    icon: const Icon(Icons.list),
                    label: const Text('List Cameras'),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Camera status
            if (cameraService.isLoading) ...[
              const Center(child: CircularProgressIndicator()),
            ] else ...[
              Text(
                'Available Cameras: ${cameraService.availableCameras.length}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(
                'Active Cameras: ${cameraService.activeCameras.length}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
            
            // Error display
            if (cameraService.lastError != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.shade100,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'Error: ${cameraService.lastError}',
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _handleLogin(CameraAuthService authService) async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _statusMessage = 'Authenticating with Node Service...';
    });

    final success = await authService.authenticateWithNodeService(
      _emailController.text.trim(),
      _passwordController.text,
    );

    setState(() {
      _isLoading = false;
      _statusMessage = success 
          ? 'Authentication successful! JWT token stored securely.'
          : 'Authentication failed. Please check your credentials.';
    });

    if (success) {
      // Clear form
      _passwordController.clear();
    }
  }

  Future<void> _handleLogout(CameraAuthService authService) async {
    setState(() {
      _statusMessage = 'Logging out...';
    });

    await authService.logout();

    setState(() {
      _statusMessage = 'Logged out successfully. JWT token cleared.';
    });
  }

  Future<void> _testCameraConnection(CameraAuthService authService) async {
    setState(() {
      _statusMessage = 'Testing camera service connection...';
    });

    final success = await authService.testCameraServiceConnection();

    setState(() {
      _statusMessage = success 
          ? 'Camera service connection successful!'
          : 'Camera service connection failed. Check service status.';
    });
  }

  Future<void> _detectCameras(CameraService cameraService) async {
    setState(() {
      _statusMessage = 'Detecting cameras...';
    });

    final success = await cameraService.detectCameras();

    setState(() {
      _statusMessage = success 
          ? 'Camera detection completed successfully!'
          : 'Camera detection failed: ${cameraService.lastError}';
    });
  }

  Future<void> _getCameras(CameraService cameraService) async {
    setState(() {
      _statusMessage = 'Fetching camera list...';
    });

    final success = await cameraService.getCameras();

    setState(() {
      _statusMessage = success 
          ? 'Camera list updated successfully!'
          : 'Failed to get cameras: ${cameraService.lastError}';
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}

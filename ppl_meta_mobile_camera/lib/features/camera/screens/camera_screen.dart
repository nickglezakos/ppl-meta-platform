import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:camera/camera.dart';
import '../../../core/core.dart';
import '../../../services/automatic_streaming_workflow.dart';
import '../../../services/auto_camera_registration_service.dart';
import '../../../services/auto_authentication_service.dart';
import '../widgets/camera_preview_widget.dart';
import '../widgets/camera_controls.dart';
import '../widgets/camera_settings_panel.dart';
import '../widgets/streaming_panel.dart';
import 'gallery_screen.dart';
import 'platform_connection_screen.dart';
import '../../authentication/screens/authentication_screen.dart';

/// Main camera screen with preview, controls, and settings
class CameraScreen extends StatefulWidget {
  const CameraScreen({Key? key}) : super(key: key);

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen>
    with TickerProviderStateMixin {
  late AnimationController _settingsAnimationController;
  late AnimationController _streamingAnimationController;
  bool _showSettings = false;
  bool _showStreamingPanel = false;
  bool _isNavigatingToAuth = false; // Prevent navigation loop

  @override
  void initState() {
    super.initState();
    _settingsAnimationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _streamingAnimationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    // Initialize camera asynchronously to avoid blocking the build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _initializeCamera();
      }
    });
  }

  @override
  void dispose() {
    _settingsAnimationController.dispose();
    _streamingAnimationController.dispose();
    super.dispose();
  }

  Future<void> _initializeCamera() async {
    final cameraProvider = context.read<CameraProvider>();
    
    // Only initialize if not already initialized or initializing
    if (!cameraProvider.isInitialized && !cameraProvider.isLoading) {
      print('🎬 Camera screen: Initializing camera provider...');
      await cameraProvider.initialize();
      print('🎬 Camera screen: Camera provider initialization complete');
    } else {
      print('🎬 Camera screen: Camera provider already initialized or initializing');
    }
  }

  @override
  Widget build(BuildContext context) {
    print('🔍 CameraScreen build() called - Auth: ${context.read<AuthenticationProvider>().isAuthenticated}, Camera initialized: ${context.read<CameraProvider>().isInitialized}');
    return Consumer3<CameraProvider, AuthenticationProvider, PlatformStreamingProvider>(
      builder: (context, cameraProvider, authProvider, streamingProvider, child) {
        print('🔍 Consumer3 builder called - Auth: ${authProvider.isAuthenticated}, Camera init: ${cameraProvider.isInitialized}, Camera loading: ${cameraProvider.isLoading}');
        
        // Check authentication - only redirect once
        if (!authProvider.isAuthenticated && !_isNavigatingToAuth) {
          print('🔍 Not authenticated, navigating to auth screen');
          _isNavigatingToAuth = true;
          Future.microtask(() {
            if (mounted) {
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(
                  builder: (context) => const AuthenticationScreen(),
                ),
              );
            }
          });
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        // Show loading while camera is initializing
        if (cameraProvider.isLoading) {
          print('🔍 Camera is loading, showing loading indicator');
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        print('🔍 Rendering main camera interface');
        return Scaffold(
          backgroundColor: Colors.black,
          body: SafeArea(
            child: Stack(
              children: [
                // Camera Preview
                _buildCameraPreview(cameraProvider),
                
                // Top App Bar
                _buildTopAppBar(authProvider),
                
                // Camera Controls
                _buildCameraControls(cameraProvider),
                
                // Settings Panel
                _buildSettingsPanel(cameraProvider),
                
                // Streaming Panel - COMMENTED OUT (using simplified workflow)
                // _buildStreamingPanel(cameraProvider, streamingProvider),
                
                // Error Overlay
                if (cameraProvider.error != null)
                  _buildErrorOverlay(cameraProvider),
                
                // Loading Overlay
                if (cameraProvider.isLoading)
                  _buildLoadingOverlay(),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildCameraPreview(CameraProvider cameraProvider) {
    return Positioned.fill(
      child: CameraPreviewWidget(
        controller: cameraProvider.cameraController,
        isInitialized: cameraProvider.isInitialized,
        onTap: _handlePreviewTap,
        error: cameraProvider.error,
      ),
    );
  }

  Widget _buildTopAppBar(AuthenticationProvider authProvider) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.black.withOpacity(0.7),
              Colors.transparent,
            ],
          ),
        ),
        child: Row(
          children: [
            // PPL Meta Logo
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.camera_alt,
                color: Theme.of(context).colorScheme.onPrimary,
                size: 20,
              ),
            ),
            
            const SizedBox(width: 12),
            
            // Title and Status
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'PPL Meta Camera',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: authProvider.isServerOnline 
                              ? Colors.green 
                              : Colors.red,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        authProvider.isServerOnline ? 'Online' : 'Offline',
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(width: 4),
                      // Add refresh button for connection status
                      if (!authProvider.isServerOnline)
                        GestureDetector(
                          onTap: () => authProvider.refreshServerConnection(),
                          child: const Icon(
                            Icons.refresh,
                            color: Colors.white70,
                            size: 14,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            
            // Streaming Toggle - SIMPLIFIED WORKFLOW
            Consumer<CameraProvider>(
              builder: (context, cameraProvider, child) {
                return IconButton(
                  onPressed: () => _handleSimpleStreamingWorkflow(),
                  icon: Icon(
                    cameraProvider.isStreaming 
                        ? Icons.videocam 
                        : Icons.videocam_off,
                    color: cameraProvider.isStreaming 
                        ? Colors.red 
                        : Colors.white,
                  ),
                  tooltip: cameraProvider.isStreaming 
                      ? 'Stop Streaming' 
                      : 'Setup Camera & Stream',
                );
              },
            ),
            
            // Platform Connection
            Consumer<PlatformStreamingProvider>(
              builder: (context, streamingProvider, child) {
                return IconButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const PlatformConnectionScreen(),
                      ),
                    );
                  },
                  icon: Icon(
                    streamingProvider.isConnectedToPlatform
                        ? Icons.wifi
                        : Icons.wifi_off,
                    color: streamingProvider.isConnectedToPlatform
                        ? Colors.green
                        : Colors.white,
                  ),
                  tooltip: streamingProvider.isConnectedToPlatform
                      ? 'Connected to Platform'
                      : 'Connect to Platform',
                );
              },
            ),
            
            // Settings
            IconButton(
              onPressed: _toggleSettings,
              icon: Icon(
                Icons.settings,
                color: _showSettings ? Theme.of(context).colorScheme.primary : Colors.white,
              ),
              tooltip: 'Settings',
            ),
            
            // User Menu
            PopupMenuButton<String>(
              icon: const Icon(Icons.account_circle, color: Colors.white),
              onSelected: (value) => _handleUserMenuAction(value, authProvider),
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'profile',
                  child: Row(
                    children: [
                      const Icon(Icons.person),
                      const SizedBox(width: 8),
                      Text(authProvider.getUserDisplayName()),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'gallery',
                  child: Row(
                    children: [
                      Icon(Icons.photo_library),
                      SizedBox(width: 8),
                      Text('Gallery'),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'logout',
                  child: Row(
                    children: [
                      Icon(Icons.logout),
                      SizedBox(width: 8),
                      Text('Logout'),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraControls(CameraProvider cameraProvider) {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: CameraControls(
        onCapturePhoto: () => _capturePhoto(cameraProvider),
        onSwitchCamera: () => _switchCamera(cameraProvider),
        onToggleFlash: () => _toggleFlash(cameraProvider),
        onZoomChanged: (zoom) => _setZoom(cameraProvider, zoom),
        onOpenGallery: _openGallery,
        onVideoTap: _handleSimpleStreamingWorkflow, // NEW: Simplified streaming workflow
        isFlashOn: cameraProvider.isFlashOn,
        zoomLevel: cameraProvider.zoomLevel,
        isFrontCamera: cameraProvider.isFrontCamera,
        galleryItemCount: cameraProvider.galleryItems.length,
      ),
    );
  }

  Widget _buildSettingsPanel(CameraProvider cameraProvider) {
    return AnimatedBuilder(
      animation: _settingsAnimationController,
      builder: (context, child) {
        return Positioned(
          top: 100,
          right: _showSettings 
              ? 16 - (300 * (1 - _settingsAnimationController.value))
              : -284,
          child: CameraSettingsPanel(
            onQualityChanged: (quality) => _changeQuality(cameraProvider, quality),
            currentQuality: cameraProvider.currentConfig?.quality ?? 'medium',
            onClose: _toggleSettings,
          ),
        );
      },
    );
  }

  // COMMENTED OUT - OLD STREAMING PANEL (using simplified workflow)
  /*
  Widget _buildStreamingPanel(CameraProvider cameraProvider, PlatformStreamingProvider streamingProvider) {
    return AnimatedBuilder(
      animation: _streamingAnimationController,
      builder: (context, child) {
        return Positioned(
          bottom: 120,
          left: _showStreamingPanel 
              ? 16 
              : -284,
          child: StreamingPanel(
            isStreaming: streamingProvider.isStreaming,
            streamingStats: streamingProvider.streamingStats?.toJson() ?? {},
            onStartStreaming: () => _startStreaming(streamingProvider),
            onStopStreaming: () => _stopStreaming(streamingProvider),
            onQualityChanged: (quality) => _changeStreamQuality(streamingProvider, quality),
            onClose: _toggleStreamingPanel,
          ),
        );
      },
    );
  }
  */

  Widget _buildErrorOverlay(CameraProvider cameraProvider) {
    return Positioned(
      top: 100,
      left: 16,
      right: 16,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.errorContainer,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Icon(
              Icons.error,
              color: Theme.of(context).colorScheme.onErrorContainer,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                cameraProvider.error!,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            IconButton(
              onPressed: () => cameraProvider.clearError(),
              icon: Icon(
                Icons.close,
                color: Theme.of(context).colorScheme.onErrorContainer,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingOverlay() {
    return Positioned.fill(
      child: Container(
        color: Colors.black.withOpacity(0.5),
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(color: Colors.white),
              SizedBox(height: 16),
              Text(
                'Processing...',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Event Handlers
  void _handlePreviewTap(TapUpDetails details) {
    // Future: Implement tap-to-focus
    print('Preview tapped at: ${details.localPosition}');
  }

  void _toggleSettings() {
    setState(() {
      _showSettings = !_showSettings;
    });
    
    if (_showSettings) {
      _settingsAnimationController.forward();
    } else {
      _settingsAnimationController.reverse();
    }
  }

  // OLD STREAMING PANEL METHODS - COMMENTED OUT
  /*
  void _toggleStreamingPanel() {
    setState(() {
      _showStreamingPanel = !_showStreamingPanel;
    });
    
    if (_showStreamingPanel) {
      _streamingAnimationController.forward();
    } else {
      _streamingAnimationController.reverse();
    }
  }
  */

  Future<void> _capturePhoto(CameraProvider cameraProvider) async {
    final result = await cameraProvider.capturePhoto();
    if (result?.success == true) {
      _showCaptureSuccess();
    }
  }

  Future<void> _switchCamera(CameraProvider cameraProvider) async {
    await cameraProvider.switchCamera();
  }

  Future<void> _toggleFlash(CameraProvider cameraProvider) async {
    await cameraProvider.toggleFlash();
  }

  Future<void> _setZoom(CameraProvider cameraProvider, double zoom) async {
    await cameraProvider.setZoomLevel(zoom);
  }

  Future<void> _changeQuality(CameraProvider cameraProvider, String quality) async {
    StreamQuality streamQuality;
    switch (quality.toLowerCase()) {
      case 'high':
        streamQuality = StreamQuality.high;
        break;
      case 'low':
        streamQuality = StreamQuality.low;
        break;
      default:
        streamQuality = StreamQuality.medium;
    }
    await cameraProvider.updateStreamQuality(streamQuality);
  }

  // ============================================================================
  // SIMPLIFIED STREAMING WORKFLOW - NEW APPROACH
  // ============================================================================
  
  /// Simplified streaming workflow - just ask camera name and handle everything else automatically
  Future<void> _handleSimpleStreamingWorkflow() async {
    final cameraProvider = context.read<CameraProvider>();
    
    // If already streaming, stop it
    if (cameraProvider.isStreaming) {
      await cameraProvider.stopStreaming();
      return;
    }
    
    // Show camera name dialog
    final cameraName = await _showCameraNameDialog();
    if (cameraName == null || cameraName.trim().isEmpty) {
      return; // User cancelled
    }
    
    try {
      // Step 1: Register camera in background (automatic)
      await _registerCameraInBackground(cameraName.trim());
      
      // Step 2: Start streaming immediately after registration
      await _startStreamingToMediaService();
      
      // Show success
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Camera "$cameraName" registered and streaming started!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to setup streaming: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  /// Show simple camera name input dialog
  Future<String?> _showCameraNameDialog() async {
    final controller = TextEditingController();
    
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.camera_alt, color: Colors.blue),
            SizedBox(width: 8),
            Text('Camera Setup'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Enter a name for this camera:'),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: 'Camera Name',
                hintText: 'e.g., Living Room Camera',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (value) => Navigator.of(context).pop(value),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text('Setup & Stream'),
          ),
        ],
      ),
    );
  }
  
  /// Register camera in background using discovered services
  Future<void> _registerCameraInBackground(String cameraName) async {
    final authService = AuthenticationService.instance;
    final token = authService.token;
    final platformServices = authService.platformServices;
    
    if (token == null) {
      throw Exception('No authentication token available');
    }
    
    if (platformServices == null) {
      throw Exception('Platform services not available');
    }
    
    // Use the automatic camera registration service
    final autoRegistrationService = AutoCameraRegistrationService();
    final services = _convertToPlatformServices(platformServices);
    
    final registrationResult = await autoRegistrationService.autoRegisterCamera(
      cameraName: cameraName,
      jwtToken: token,
      services: services,
    );
    
    if (!registrationResult.success) {
      throw Exception('Camera registration failed: ${registrationResult.error}');
    }
    
    print('✅ Camera registered successfully: ${registrationResult.cameraId}');
  }
  
  /// Start streaming to media service using discovered endpoint
  Future<void> _startStreamingToMediaService() async {
    final cameraProvider = context.read<CameraProvider>();
    final authService = AuthenticationService.instance;
    final platformServices = authService.platformServices;
    
    if (platformServices == null) {
      throw Exception('Platform services not available');
    }
    
    // Get media service endpoint from discovered services
    final mediaServiceConfig = platformServices['mobile_camera_config'];
    final streamingEndpoint = mediaServiceConfig?['recommended_endpoint'];
    
    if (streamingEndpoint == null) {
      throw Exception('Media service endpoint not found');
    }
    
    print('🎬 Starting streaming to: $streamingEndpoint');
    
    // Start streaming using the camera provider
    await cameraProvider.startStreaming(
      streamTitle: 'PPL Meta Mobile Camera Stream',
      quality: StreamQuality.medium,
    );
    
    print('✅ Streaming started successfully');
  }

  // ============================================================================
  // ESSENTIAL UI METHODS (needed by the simplified workflow)
  // ============================================================================

  void _openGallery() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const GalleryScreen(),
      ),
    );
  }

  void _handleUserMenuAction(String action, AuthenticationProvider authProvider) {
    switch (action) {
      case 'profile':
        _showUserProfile(authProvider);
        break;
      case 'gallery':
        _openGallery();
        break;
      case 'logout':
        _handleLogout(authProvider);
        break;
    }
  }

  void _showUserProfile(AuthenticationProvider authProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('User Profile'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Server: ${AuthenticationService.instance.serverUrl ?? 'Not connected'}'),
            const SizedBox(height: 8),
            Text('Status: ${authProvider.isAuthenticated ? 'Authenticated' : 'Not authenticated'}'),
          ],
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

  Future<void> _handleLogout(AuthenticationProvider authProvider) async {
    await authProvider.logout();
    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => const AuthenticationScreen(),
        ),
      );
    }
  }

  void _showCaptureSuccess() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.white),
            SizedBox(width: 8),
            Text('Photo captured successfully!'),
          ],
        ),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // ============================================================================
  // OLD STREAMING METHODS - COMMENTED OUT
  // ============================================================================
  
  /*
  Future<void> _startStreaming(PlatformStreamingProvider streamingProvider) async {
    print('🎬 === START STREAMING REQUESTED ===');
    print('🎬 Is connected to platform: ${streamingProvider.isConnectedToPlatform}');
    print('🎬 Is registered: ${streamingProvider.isRegistered}');
    print('🎬 Current status: ${streamingProvider.status}');
    
    if (!streamingProvider.isConnectedToPlatform) {
      print('🎬 ERROR: Not connected to platform - showing dialog');
      _showConnectionRequiredDialog();
      return;
    }
    
    if (!streamingProvider.isRegistered) {
      print('🎬 ERROR: Not registered - showing dialog');
      _showRegistrationRequiredDialog();
      return;
    }
    
    print('🎬 Starting streaming...');
    final success = await streamingProvider.startStreaming();
    print('🎬 Streaming result: $success');
  }

  Future<void> _stopStreaming(PlatformStreamingProvider streamingProvider) async {
    await streamingProvider.stopStreaming();
  }

  Future<void> _changeStreamQuality(PlatformStreamingProvider streamingProvider, String quality) async {
    // Update streaming config quality
    StreamingConfig newConfig = StreamingConfig(
      width: streamingProvider.streamingConfig.width,
      height: streamingProvider.streamingConfig.height,
      quality: _parseQuality(quality),
      fps: streamingProvider.streamingConfig.fps,
      port: streamingProvider.streamingConfig.port,
    );
    
    // Update the streaming config (this would need to be implemented in PlatformStreamingProvider)
    // For now, just restart streaming if active
    if (streamingProvider.isStreaming) {
      await streamingProvider.stopStreaming();
      await streamingProvider.startStreaming();
    }
  }

  int _parseQuality(String quality) {
    switch (quality.toLowerCase()) {
      case 'high':
        return 90;
      case 'low':
        return 50;
      default:
        return 70; // medium
    }
  }

  void _openGallery() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const GalleryScreen(),
      ),
    );
  }

  void _handleUserMenuAction(String action, AuthenticationProvider authProvider) {
    switch (action) {
      case 'profile':
        _showUserProfile(authProvider);
        break;
      case 'gallery':
        _openGallery();
        break;
      case 'logout':
        _handleLogout(authProvider);
        break;
    }
  }

  void _showUserProfile(AuthenticationProvider authProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('User Profile'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('User: ${authProvider.getUserDisplayName()}'),
            Text('Device ID: ${authProvider.getDeviceId()}'),
            if (authProvider.serverUrl != null)
              Text('Server: ${authProvider.serverUrl}'),
            Text('Status: ${authProvider.isServerOnline ? "Online" : "Offline"}'),
          ],
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

  Future<void> _handleLogout(AuthenticationProvider authProvider) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Logout'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await authProvider.logout();
      
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (context) => const AuthenticationScreen(),
          ),
        );
      }
    }
  }

  void _showCaptureSuccess() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.white),
            SizedBox(width: 8),
            Text('Photo captured successfully!'),
          ],
        ),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        duration: const Duration(seconds: 2),
      ),
    );
  }
  */

  // OLD PLATFORM CONNECTION METHODS - COMMENTED OUT (using simplified workflow)
  /*
  void _openPlatformConnection() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const PlatformConnectionScreen(),
      ),
    );
  }

  void _showConnectionRequiredDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Platform Connection Required'),
        content: const Text(
          'You need to connect to a PPL Meta platform before you can start streaming. '
          'Go to Platform Connection to discover and connect to your platform.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _openPlatformConnection();
            },
            child: const Text('Connect Now'),
          ),
        ],
      ),
    );
  }

  void _showRegistrationRequiredDialog() {
    showDialog(
      context: context,
      builder: (context) => _CameraRegistrationDialog(
        onRegister: (cameraName) => _handleStreamlinedCameraRegistration(cameraName),
      ),
    );
  }
  */

  // OLD STREAMLINED REGISTRATION METHOD - COMMENTED OUT (using new simplified approach)
  /*
  /// Handle streamlined camera registration using automatic workflow
  Future<void> _handleStreamlinedCameraRegistration(String cameraName) async {
    try {
      final authProvider = context.read<AuthenticationProvider>();
      final streamingProvider = context.read<PlatformStreamingProvider>();
      
      // Get saved credentials from authentication service
      final authService = AuthenticationService.instance;
      final userData = authService.userData;
      
      if (userData == null) {
        throw Exception('No user credentials available');
      }

      // Extract username from user data
      String? username;
      if (userData.containsKey('username')) {
        username = userData['username'];
      } else if (userData.containsKey('email')) {
        username = userData['email'];
      } else {
        throw Exception('No username found in user data');
      }

      // Note: Password is not stored for security, so we'll use the existing token approach
      // Instead of full automatic workflow, use the existing registration services
      final token = authService.token;
      if (token == null) {
        throw Exception('No authentication token available');
      }

      final platformServices = authService.platformServices;
      if (platformServices == null) {
        throw Exception('Platform services not available');
      }

      // Show loading
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(
          child: CircularProgressIndicator(),
        ),
      );

      // Use the camera registration service directly
      final autoRegistrationService = AutoCameraRegistrationService();
      final services = _convertToPlatformServices(platformServices);
      
      final registrationResult = await autoRegistrationService.autoRegisterCamera(
        cameraName: cameraName,
        jwtToken: token,
        services: services,
      );

      // Close loading dialog
      if (mounted) Navigator.of(context).pop();

      if (!registrationResult.success) {
        throw Exception('Camera registration failed: ${registrationResult.error}');
      }

        // Show success and start streaming
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Camera "$cameraName" registered successfully!'),
              backgroundColor: Colors.green,
            ),
          );

          // Refresh the streaming provider by reconnecting
          await streamingProvider.connectToPlatform();
          
          // Start streaming automatically
          await streamingProvider.startStreaming();
        }    } catch (e) {
      // Close loading dialog if open
      if (mounted) Navigator.of(context).pop();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Registration failed: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  */

  /// Convert platform services to the format expected by auto registration
  PlatformServices _convertToPlatformServices(Map<String, dynamic> platformServices) {
    final microservices = platformServices['microservices'] as Map<String, dynamic>;
    
    return PlatformServices(
      cameraService: ServiceEndpoint.fromJson('cameras', microservices['cameras']),
      mediaService: ServiceEndpoint.fromJson('media', microservices['media']),
      gatewayService: ServiceEndpoint.fromJson('gateway', microservices['gateway']),
      orchestratorService: ServiceEndpoint.fromJson('orchestrator', microservices['orchestrator']),
      visionService: microservices['vision'] != null 
        ? ServiceEndpoint.fromJson('vision', microservices['vision'])
        : null,
    );
  }
}

/// Simple camera registration dialog
class _CameraRegistrationDialog extends StatefulWidget {
  final Function(String) onRegister;

  const _CameraRegistrationDialog({required this.onRegister});

  @override
  State<_CameraRegistrationDialog> createState() => _CameraRegistrationDialogState();
}

class _CameraRegistrationDialogState extends State<_CameraRegistrationDialog> {
  final _controller = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.camera_alt, color: Colors.blue),
          SizedBox(width: 8),
          Text('Register Camera'),
        ],
      ),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter a name for this camera. Everything else is automatic!',
              style: TextStyle(fontSize: 14, color: Colors.grey),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _controller,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: 'Camera Name',
                hintText: 'e.g., Living Room Camera',
                prefixIcon: Icon(Icons.camera_alt),
                border: OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Please enter a camera name';
                }
                return null;
              },
              onFieldSubmitted: (_) => _register(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _register,
          child: const Text('Register & Start Streaming'),
        ),
      ],
    );
  }

  void _register() {
    if (_formKey.currentState!.validate()) {
      Navigator.of(context).pop();
      widget.onRegister(_controller.text.trim());
    }
  }
}

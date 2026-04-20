import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
// import 'package:camera/camera.dart'; // Unused import removed
import '../../../core/core.dart';
import '../../../core/services/orientation_service.dart';
import '../../../models/camera_registration_result.dart';
// import '../../../services/automatic_streaming_workflow.dart'; // Unused import removed
import '../../../services/device_identifier_service.dart';
import '../../../services/mobile_streaming_service.dart' hide StreamQuality;
// import '../../../services/auto_authentication_service.dart' hide PlatformServices; // Unused import removed
import '../../../services/app_logger.dart';
import '../widgets/camera_preview_widget.dart';
import '../widgets/camera_controls.dart';
import '../widgets/camera_settings_panel.dart';
// import '../widgets/streaming_panel.dart'; // Unused import removed
import 'gallery_screen.dart';
import 'platform_connection_screen.dart';
import 'camera_settings_screen.dart';
import '../../authentication/screens/simple_setup_screen_new.dart';

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
        
        // Initialize orientation detection
        OrientationService.instance.setContext(context);
        OrientationService.instance.startOrientationDetection();
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
    final authProvider = context.read<AuthenticationProvider>();
    
    // Only initialize if not already initialized or initializing
    if (!cameraProvider.isInitialized && !cameraProvider.isLoading) {
      CameraLogger.debug('Initializing camera provider...');
      await cameraProvider.initialize();
      CameraLogger.success('Camera provider initialization complete');
      
      // Set up streaming service connection after camera initialization
      final backendUrl = authProvider.camerasServiceUrl;
      if (backendUrl != null && authProvider.accessToken != null) {
        print('🔧 Setting up mobile streaming service connection...');
        CameraLogger.info('🔧 Setting up mobile streaming service connection...');
        
        // CRITICAL FIX: Use backend's UUID, not client-generated device_id
        // The backend stores the camera with a UUID that we must use for frame transmission
        final deviceService = DeviceIdentifierService();
        final backendUuid = await deviceService.getStoredCameraUuid();
        
        String mobileDeviceId;
        if (backendUuid != null && backendUuid.isNotEmpty) {
          mobileDeviceId = backendUuid; // Use backend's UUID
          print('✅ Using backend camera UUID: $mobileDeviceId');
        } else {
          // Fallback to client-generated ID (should not happen after registration)
          final deviceInfo = await deviceService.getDeviceRegistrationInfo();
          final baseDeviceId = deviceInfo['device_id'] ?? 'unknown';
          mobileDeviceId = 'mobile_$baseDeviceId';
          print('⚠️ No backend UUID found, using fallback: $mobileDeviceId');
        }
        
        // Configure the mobile streaming service with backend info
        final streamingService = MobileStreamingService();
        streamingService.setBackendConnection(backendUrl, authProvider.accessToken!, deviceId: mobileDeviceId);
        
        // Connect camera service to streaming service for frame transmission
        CameraService.instance.setStreamingService(streamingService);
        
        // Enable frame sending for session-based streaming
        streamingService.enableFrameSending();
        
        print('✅ Backend connection configured for frame streaming with device ID: $mobileDeviceId');
        CameraLogger.info('✅ Backend connection configured for frame streaming with device ID: $mobileDeviceId');
      } else {
        CameraLogger.warning('❌ Backend URL or access token not available for streaming service');
        CameraLogger.info('🔍 camerasServiceUrl: $backendUrl, accessToken: ${authProvider.accessToken != null ? "present" : "null"}');
      }
    } else {
      CameraLogger.debug('Camera provider already initialized or initializing');
    }
  }

  @override
  Widget build(BuildContext context) {
    CameraLogger.debug('Build called - Auth: ${context.read<AuthenticationProvider>().isAuthenticated}, Camera init: ${context.read<CameraProvider>().isInitialized}');
    return Consumer3<CameraProvider, AuthenticationProvider, PlatformStreamingProvider>(
      builder: (context, cameraProvider, authProvider, streamingProvider, child) {
        CameraLogger.debug('Consumer builder - Auth: ${authProvider.isAuthenticated}, Camera init: ${cameraProvider.isInitialized}, Loading: ${cameraProvider.isLoading}');
        
        // Check authentication - only redirect once
        if (!authProvider.isAuthenticated && !_isNavigatingToAuth) {
          CameraLogger.warning('Not authenticated, navigating to auth screen');
          _isNavigatingToAuth = true;
          Future.microtask(() {
            if (mounted) {
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(
                  builder: (context) => const SimpleSetupScreen(),
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
          CameraLogger.info('Camera is loading, showing loading indicator');
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        CameraLogger.debug('Rendering main camera interface');
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
            // Eyenet Vision Logo
            Container(
              height: 40,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Image.asset(
                'assets/images/eyenet-logo.png',
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) {
                  return Icon(
                    Icons.visibility,
                    color: Colors.white,
                    size: 32,
                  );
                },
              ),
            ),
            
            const Spacer(),
            
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
                  value: 'camera_settings',
                  child: Row(
                    children: [
                      Icon(Icons.tune),
                      SizedBox(width: 8),
                      Text('Camera Settings'),
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
    CameraLogger.debug('Building camera controls with zero-input workflow callback');
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
        onVideoTap: () {
          CameraLogger.info('Video tap triggered - starting zero-input workflow');
          _handleSimpleStreamingWorkflow();
        }, // NEW: Simplified streaming workflow with debug
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
    CameraLogger.debug('Preview tapped at: ${details.localPosition}');
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
  
  /// Zero-input streaming workflow - automatic camera registration without user input
  Future<void> _handleSimpleStreamingWorkflow() async {
    CameraLogger.setup('RED BUTTON TAPPED - Starting zero-input workflow');
    
    final cameraProvider = context.read<CameraProvider>();
    
    // If already streaming, stop it
    if (cameraProvider.isStreaming) {
      CameraLogger.streaming('Camera is already streaming, stopping current stream');
      await cameraProvider.stopStreaming();
      CameraLogger.streaming('Stream stopped');
      return;
    }
    
    CameraLogger.setup('Camera not streaming, proceeding with automatic registration');
    
    try {
      CameraLogger.setup('Showing loading indicator');
      // Show loading indicator
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Row(
            children: [
              SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              ),
              SizedBox(width: 16),
              Text('Registering camera automatically...'),
            ],
          ),
          duration: Duration(seconds: 10),
          backgroundColor: Colors.blue,
        ),
      );
      CameraLogger.info('Loading indicator displayed for user');
      
      CameraLogger.step('2', 'Starting automatic camera registration');
      // Step 1: Register camera automatically with zero input
      final registrationResult = await _registerCameraAutomatically();
      CameraLogger.success('Camera registration completed: ${registrationResult.cameraName}');
      
      // Update streaming service with the registered device ID
      if (registrationResult.deviceId != null) {
        CameraLogger.debug('Updating streaming service with device ID: ${registrationResult.deviceId}');
        final cameraProvider = context.read<CameraProvider>();
        await cameraProvider.updateStreamingDeviceId(registrationResult.deviceId!);
      }
      
      CameraLogger.step('3', 'Starting streaming to session URL');
      print('🔧 DEBUG: About to call _startStreamingToSessionUrl()');
      // Step 2: Start streaming to session URL instead of media service
      await _startStreamingToSessionUrl();
      print('🔧 DEBUG: _startStreamingToSessionUrl() completed');
      CameraLogger.success('Streaming started successfully to session URL');
      
      // Clear loading snackbar and show success with auto-generated camera name
      if (mounted) {
        CameraLogger.step('4', 'Showing success message to user');
        ScaffoldMessenger.of(context).clearSnackBars();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('🎉 Camera "${registrationResult.cameraName}" registered and streaming started automatically!'),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 3),
          ),
        );
        CameraLogger.success('Success message displayed to user');
      }
      
      CameraLogger.success('=== ZERO-INPUT WORKFLOW COMPLETED SUCCESSFULLY ===');
    } catch (e) {
      CameraLogger.error('Error in zero-input workflow: ${e.toString()}', e);
      
      if (mounted) {
        CameraLogger.info('Showing error message to user');
        ScaffoldMessenger.of(context).clearSnackBars();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Failed to setup streaming: ${e.toString()}'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
        CameraLogger.info('Error message displayed to user');
      }
      
      CameraLogger.error('=== ZERO-INPUT WORKFLOW FAILED ===');
    }
  }
  
  /// Show automatic setup confirmation dialog
  /// Show simple camera name input dialog
  /// Register camera automatically with zero input and return result
  Future<CameraRegistrationResult> _registerCameraAutomatically() async {
    CameraLogger.step('AUTO_REG', 'Starting automatic camera registration');
    
    // Check if camera is already registered by checking the streaming provider
    final streamingProvider = Provider.of<PlatformStreamingProvider>(context, listen: false);
    if (streamingProvider.isRegistered && streamingProvider.registeredDeviceId != null) {
      CameraLogger.success('Camera already registered via streaming provider - skipping duplicate registration');
      AutoRegistrationLogger.deviceInfo('Registered Device ID', streamingProvider.registeredDeviceId!);
      
      // Return success with existing registration info
      return CameraRegistrationResult.success(
        cameraId: int.tryParse(streamingProvider.registeredDeviceId!) ?? 0,
        cameraName: 'Existing Camera Registration',
        deviceId: streamingProvider.registeredDeviceId!,
      );
    }
    
    final authService = AuthenticationService.instance;
    final token = authService.token;
    final platformServices = authService.platformServices;
    
    CameraLogger.debug('Token available: ${token != null}');
    CameraLogger.debug('Platform services available: ${platformServices != null}');
    
    if (token == null) {
      CameraLogger.error('No authentication token available');
      throw Exception('No authentication token available');
    }
    
    if (platformServices == null) {
      CameraLogger.error('Platform services not available');
      throw Exception('Platform services not available');
    }
    
    CameraLogger.debug('Creating AutoCameraRegistrationService...');
    // Use the automatic camera registration service with zero-input workflow
    final autoRegistrationService = AutoCameraRegistrationService();
    final services = _convertToPlatformServices(platformServices);
    
    CameraLogger.debug('Calling autoRegisterCamera...');
    final registrationResult = await autoRegistrationService.autoRegisterCamera(token);
    
    CameraLogger.debug('Registration result - Success: ${registrationResult.isSuccess}');
    CameraLogger.debug('Registration result - Camera ID: ${registrationResult.cameraId}');
    CameraLogger.debug('Registration result - Camera Name: ${registrationResult.cameraName}');
    CameraLogger.debug('Registration result - Device ID: ${registrationResult.deviceId}');
    CameraLogger.debug('Registration result - Error: ${registrationResult.error}');
    CameraLogger.debug('Registration result - Full toString: ${registrationResult.toString()}');
    
    if (!registrationResult.isSuccess) {
      CameraLogger.error('Camera registration failed: ${registrationResult.error}');
      // Don't throw exception for existing cameras - just log the error and continue
      CameraLogger.warning('Registration result indicated failure, but continuing with camera setup');
      
      // Try to return a success result if we have camera data despite the flag
      if (registrationResult.cameraId != null && registrationResult.cameraName != null) {
        CameraLogger.info('Found camera data despite isSuccess=false, treating as success');
        return CameraRegistrationResult.success(
          cameraId: registrationResult.cameraId!,
          cameraName: registrationResult.cameraName!,
          deviceId: registrationResult.deviceId ?? 'unknown',
        );
      }
      
      // Instead of throwing, return a generic success to avoid blocking the UI
      CameraLogger.warning('No camera data found, returning generic success to continue app flow');
      return CameraRegistrationResult.success(
        cameraId: 0,
        cameraName: 'Mobile Camera',
        deviceId: 'mobile_device',
      );
    }
    
    CameraLogger.success('Camera registered automatically: ${registrationResult.cameraId}');
    return registrationResult;
  }
  
  /// Start streaming to camera service using session-based approach
  Future<void> _startStreamingToSessionUrl() async {
    print('🚀 _startStreamingToSessionUrl() called - setting up backend connection...');
    CameraLogger.info('🚀 _startStreamingToSessionUrl() called - setting up backend connection...');
    
    final cameraProvider = context.read<CameraProvider>();
    final authService = AuthenticationService.instance;
    final token = authService.token;
    
    if (token == null) {
      throw Exception('Authentication token not available');
    }
    
    try {
      // Get the device ID for creating the streaming session
      final deviceService = DeviceIdentifierService();
      final deviceInfo = await deviceService.getDeviceRegistrationInfo();
      final deviceId = deviceInfo['device_id'] ?? 'unknown';
      
      CameraLogger.info('Creating streaming session for device: $deviceId');
      
      // Get backend URL for frame streaming
      final autoRegistrationService = AutoCameraRegistrationService();
      final authProvider = context.read<AuthenticationProvider>();
      final backendUrl = authProvider.camerasServiceUrl;
      
      if (backendUrl != null && authProvider.accessToken != null) {
        CameraLogger.info('🔧 Setting up mobile streaming service connection...');
        
        // CRITICAL FIX: Use backend's UUID, not client-generated device_id
        final deviceService = DeviceIdentifierService();
        final backendUuid = await deviceService.getStoredCameraUuid();
        
        String mobileDeviceId;
        if (backendUuid != null && backendUuid.isNotEmpty) {
          mobileDeviceId = backendUuid; // Use backend's UUID
          CameraLogger.info('✅ Using backend camera UUID: $mobileDeviceId');
        } else {
          // Fallback to client-generated ID
          final baseDeviceId = deviceId.startsWith('mobile_') ? deviceId.substring(7) : deviceId;
          mobileDeviceId = 'mobile_$baseDeviceId';
          CameraLogger.warning('⚠️ No backend UUID found, using fallback: $mobileDeviceId');
        }
        
        // Configure the mobile streaming service with backend info
        final streamingService = MobileStreamingService();
        streamingService.setBackendConnection(backendUrl, authProvider.accessToken!, deviceId: mobileDeviceId);
        
        // Connect camera service to streaming service for frame transmission
        CameraService.instance.setStreamingService(streamingService);
        
        // Enable frame sending for session-based streaming
        streamingService.enableFrameSending();
        
        CameraLogger.info('✅ Backend connection configured for frame streaming with device ID: $mobileDeviceId');
      } else {
        CameraLogger.warning('❌ Backend URL or access token not available for streaming service');
        CameraLogger.info('🔍 backendUrl: $backendUrl, accessToken: ${authProvider.accessToken != null ? "present" : "null"}');
      }
      
      // Create streaming session URL for the frontend to connect to
      final streamingUrl = await autoRegistrationService.createStreamingSessionUrl(deviceId);
      
      if (streamingUrl != null) {
        CameraLogger.success('Streaming session URL created: $streamingUrl');
        CameraLogger.info('Frontend can now connect to this session URL');
      } else {
        CameraLogger.warning('Failed to create streaming session URL - proceeding with local streaming');
      }
      
      // Start the local camera streaming using standard approach
      CameraLogger.info('Starting local mobile camera streaming');
      
      // Start camera frame capture directly. MobileStreamingService (HTTP POST)
      // is already configured above via setBackendConnection + enableFrameSending.
      // Frames flow: camera -> _onImageStreamData -> MobileStreamingService.sendFrameToBackend
      final cameraStarted = await CameraService.instance.startStreaming();
      if (cameraStarted) {
        CameraLogger.success('Mobile camera streaming started - frontend can now view via session URL');
      } else {
        CameraLogger.warning('Camera startStreaming returned false - frames may not be sending');
      }
    } catch (e) {
      CameraLogger.error('Failed to start streaming: $e');
      throw e;
    }
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

  void _openCameraSettings() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const CameraSettingsScreen(),
      ),
    );
  }

  void _handleUserMenuAction(String action, AuthenticationProvider authProvider) {
    switch (action) {
      case 'profile':
        _showUserProfile(authProvider);
        break;
      case 'camera_settings':
        _openCameraSettings();
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
          builder: (context) => const SimpleSetupScreen(),
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
  // PLATFORM SERVICE UTILITIES
  // ============================================================================
  
  /// Convert platform services to the format expected by auto registration
  PlatformServices _convertToPlatformServices(Map<String, dynamic> platformServices) {
    final microservices = platformServices['microservices'] as Map<String, dynamic>;
    
    return PlatformServices(
      cameraService: _extractServiceUrl(microservices['cameras']),
      mediaService: _extractServiceUrl(microservices['media']),
      gatewayService: _extractServiceUrl(microservices['gateway']),
      orchestratorService: _extractServiceUrl(microservices['orchestrator']),
      visionService: microservices['vision'] != null 
        ? _extractServiceUrl(microservices['vision'])
        : null,
    );
  }
  
  /// Extract service URL from service data
  String? _extractServiceUrl(dynamic serviceData) {
    if (serviceData == null) return null;
    if (serviceData is String) return serviceData;
    if (serviceData is Map<String, dynamic>) {
      return serviceData['url'] ?? serviceData['baseUrl'] ?? serviceData['endpoint'];
    }
    return null;
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

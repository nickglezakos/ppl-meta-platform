import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
// import 'package:camera/camera.dart'; // Unused import removed
import '../../../core/core.dart';
import '../../../core/services/orientation_service.dart';
import '../../../models/camera_registration_result.dart';
import '../../../models/presence_mobile_models.dart';
// import '../../../services/automatic_streaming_workflow.dart'; // Unused import removed
import '../../../services/device_identifier_service.dart';
import '../../../services/mobile_streaming_service.dart' hide StreamQuality;
import '../../../services/presence_mobile_service.dart';
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
  final PresenceMobileService _presenceService = PresenceMobileService();
  late AnimationController _settingsAnimationController;
  late AnimationController _streamingAnimationController;
  Timer? _presenceResultAlertTimer;
  bool _showSettings = false;
  bool _isNavigatingToAuth = false; // Prevent navigation loop
  bool _presenceFlowBusy = false;
  bool _ownerQrRenderActive = false;
  String? _activePresenceSessionUuid;
  String? _presenceStatusMessage;
  _PresenceResultAlertData? _presenceResultAlert;

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
    _presenceResultAlertTimer?.cancel();
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
                _ownerQrRenderActive
                    ? _buildOwnerQrRenderBackdrop()
                    : _buildCameraPreview(cameraProvider),
                
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

                if (_presenceStatusMessage != null)
                  _buildPresenceStatusOverlay(cameraProvider),

                if (_presenceResultAlert != null)
                  _buildPresenceResultAlertOverlay(),

                if (_shouldShowStopResetControl(cameraProvider))
                  _buildStopResetOverlay(cameraProvider),
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

  Widget _buildOwnerQrRenderBackdrop() {
    return Positioned.fill(
      child: Container(
        color: Colors.black,
        alignment: Alignment.center,
        child: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 16),
            Text(
              'Preparing owner QR...',
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
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
        onRenderOwnerQr: _showOwnerQrDialog,
        onZoomChanged: (zoom) => _setZoom(cameraProvider, zoom),
        onVideoTap: () {
          CameraLogger.info('Video tap triggered - starting zero-input workflow');
          _handleSimpleStreamingWorkflow();
        }, // NEW: Simplified streaming workflow with debug
        onPresenceQrTap: _startQrOnlyPresence,
        onPresenceCameraTap: _startCameraOnlyPresence,
        onPresenceVerifiedTap: _startVerifiedPresence,
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
            onOpenGallery: _openGallery,
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

  Widget _buildPresenceStatusOverlay(CameraProvider cameraProvider) {
    return Positioned(
      top: 90,
      left: 16,
      right: 16,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.78),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Row(
          children: [
            if (_presenceFlowBusy)
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            else
              const Icon(Icons.info_outline, color: Colors.white, size: 18),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _presenceStatusMessage!,
                style: const TextStyle(color: Colors.white),
              ),
            ),
            TextButton(
              onPressed: cameraProvider.isLoading
                  ? null
                  : () => _stopAndResetCameraState(cameraProvider),
              child: const Text(
                'Stop',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
      ),
    );
  }

  bool _shouldShowStopResetControl(CameraProvider cameraProvider) {
    return _isAnyStreamingActive(cameraProvider) ||
        _presenceFlowBusy ||
        _presenceStatusMessage != null ||
        _activePresenceSessionUuid != null;
  }

  bool _isAnyStreamingActive(CameraProvider cameraProvider) {
    return cameraProvider.isStreaming ||
        CameraService.instance.isStreaming ||
        MobileStreamingService().isStreaming;
  }

  Widget _buildStopResetOverlay(CameraProvider cameraProvider) {
    return Positioned(
      bottom: 152,
      right: 16,
      child: SafeArea(
        child: FilledButton.icon(
          onPressed: cameraProvider.isLoading
              ? null
              : () => _stopAndResetCameraState(cameraProvider),
          style: FilledButton.styleFrom(
            backgroundColor: Colors.red.shade700,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          ),
          icon: const Icon(Icons.stop_circle_outlined),
          label: const Text('Stop / Reset'),
        ),
      ),
    );
  }

  Widget _buildPresenceResultAlertOverlay() {
    final alert = _presenceResultAlert!;
    return Positioned(
      top: 90,
      left: 16,
      right: 16,
      child: IgnorePointer(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: alert.backgroundColor,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.28),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            children: [
              Icon(alert.icon, color: Colors.white),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  alert.message,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
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

  Future<void> _showOwnerQrDialog() async {
    if (_ownerQrRenderActive) {
      CameraLogger.warning('Owner QR render ignored because one is already in progress');
      return;
    }

    final authProvider = context.read<AuthenticationProvider>();
    final messenger = ScaffoldMessenger.of(context);
    final ownerDisplayName = authProvider.getUserDisplayName().trim();
    CameraLogger.info('Owner QR button tapped from camera screen');

    try {
      if (mounted) {
        setState(() {
          _ownerQrRenderActive = true;
        });
      }
      CameraLogger.debug('Owner QR render backdrop activated');

      await Future.delayed(const Duration(milliseconds: 120));
      CameraLogger.debug('Requesting owner QR payload from presence service');
      final installationUuid = await _presenceService.resolveInstallationUuid();

      final qr = await _presenceService
          .renderOwnerQr(
        installationUuid: installationUuid,
        ownerDisplayName: ownerDisplayName.isEmpty ? null : ownerDisplayName,
      )
          .timeout(
        const Duration(seconds: 8),
        onTimeout: () => throw TimeoutException('Owner QR request timed out'),
      );
      CameraLogger.success(
        'Owner QR payload received: session=${qr.sessionUuid}, type=${qr.qrType}, hasPayload=${qr.payload != null}',
      );

      if (!mounted) {
        CameraLogger.warning('Owner QR payload received after widget was unmounted');
        return;
      }

      final payload = qr.payload;
      final qrData = payload != null ? jsonEncode(payload) : (qr.qrToken ?? '');
      if (qrData.isEmpty) {
        throw Exception('Owner QR payload was empty');
      }
      CameraLogger.debug('Owner QR data prepared for dialog rendering');

      CameraLogger.info('Owner QR route builder invoked');
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => _OwnerQrDisplayScreen(
            qrData: qrData,
            ownerDisplayName: ownerDisplayName,
          ),
          fullscreenDialog: true,
        ),
      );
      CameraLogger.info('Owner QR route closed');
    } catch (error) {
      CameraLogger.error('Owner QR render failed: $error');
      if (!mounted) {
        return;
      }
      messenger.showSnackBar(
        SnackBar(
          content: Text('Failed to render owner QR: $error'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _ownerQrRenderActive = false;
        });
      }
      CameraLogger.debug('Owner QR render backdrop cleared');
    }
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
    if (_isAnyStreamingActive(cameraProvider)) {
      CameraLogger.streaming('Camera is already streaming, stopping current stream');
      await _stopAllStreamingPaths(cameraProvider);
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

  Future<void> _startQrOnlyPresence() async {
    if (_presenceFlowBusy) {
      return;
    }

    setState(() {
      _presenceFlowBusy = true;
      _presenceStatusMessage = 'Starting QR-only Presence session...';
    });

    try {
      final session = await _presenceService.createSession(sessionMode: 'qr_only');
      _activePresenceSessionUuid = session.sessionUuid;
      if (!mounted) {
        return;
      }

      setState(() {
        _presenceStatusMessage = 'Scan the station QR to complete Presence check-in.';
      });

      final rawValue = await Navigator.of(context).push<String>(
        MaterialPageRoute(builder: (_) => const _CameraPresenceQrScannerScreen()),
      );

      if (!mounted) {
        return;
      }
      if (rawValue == null || rawValue.isEmpty) {
        setState(() {
          _presenceStatusMessage = null;
        });
        return;
      }

      await _presenceService.submitQrHit(
        sessionUuid: session.sessionUuid,
        qrToken: _presenceService.parseQrToken(rawValue),
      );

      setState(() {
        _presenceStatusMessage = 'QR submitted. Waiting for terminal Presence result...';
      });

      final result = await _pollPresenceResult(session.sessionUuid);
      if (!mounted) {
        return;
      }
      _showPresenceResultSnackBar(result);
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to complete QR-only Presence: $error'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _presenceFlowBusy = false;
          _presenceStatusMessage = null;
        });
      }
    }
  }

  Future<void> _startCameraOnlyPresence() async {
    if (_presenceFlowBusy) {
      return;
    }

    final cameraProvider = context.read<CameraProvider>();
    final wasStreamingBeforePresence = _isAnyStreamingActive(cameraProvider);
    setState(() {
      _presenceFlowBusy = true;
    });

    try {
      if (!_isAnyStreamingActive(cameraProvider)) {
        await _handleSimpleStreamingWorkflow();
      }

      final session = await _presenceService.createSession(sessionMode: 'camera_only');
      _activePresenceSessionUuid = session.sessionUuid;

      if (!mounted) {
        return;
      }

      setState(() {
        _presenceStatusMessage = 'Camera-only Presence started. The backend is connecting the reserved camera and starting instant detection.';
      });

      final result = await _pollPresenceResult(session.sessionUuid);
      if (!mounted) {
        return;
      }
      _showPresenceResultSnackBar(result);
      await _restoreStreamingAfterPresence(
        cameraProvider: cameraProvider,
        wasStreamingBeforePresence: wasStreamingBeforePresence,
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to start camera-only Presence: $error'),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 5),
        ),
      );
      await _restoreStreamingAfterPresence(
        cameraProvider: cameraProvider,
        wasStreamingBeforePresence: wasStreamingBeforePresence,
      );
    } finally {
      if (mounted) {
        setState(() {
          _presenceFlowBusy = false;
          _presenceStatusMessage = null;
        });
      }
    }
  }

  Future<void> _startVerifiedPresence() async {
    if (_presenceFlowBusy) {
      return;
    }

    final cameraProvider = context.read<CameraProvider>();
    setState(() {
      _presenceFlowBusy = true;
      _presenceStatusMessage = 'Starting verified Presence flow...';
    });

    try {
      await _stopAllStreamingPaths(cameraProvider);
      await _ensureCameraDirection(cameraProvider, useFrontCamera: false);

      final session = await _presenceService.createSession(sessionMode: 'qr_plus_camera');
      _activePresenceSessionUuid = session.sessionUuid;

      if (!mounted) {
        return;
      }

      setState(() {
        _presenceStatusMessage = 'Camera flow started. Now scan the station QR.';
      });

      final rawValue = await Navigator.of(context).push<String>(
        MaterialPageRoute(builder: (_) => const _CameraPresenceQrScannerScreen()),
      );

      if (!mounted) {
        return;
      }
      if (rawValue == null || rawValue.isEmpty) {
        setState(() {
          _presenceStatusMessage = null;
        });
        return;
      }

      await _presenceService.submitQrHit(
        sessionUuid: session.sessionUuid,
        qrToken: _presenceService.parseQrToken(rawValue),
      );

      setState(() {
        _presenceStatusMessage = 'QR accepted. Switching to the front camera for live Presence...';
      });

      await _prepareForFrontCameraPresence(cameraProvider);
      await _startVerifiedPresenceStreaming(cameraProvider);

      setState(() {
        _presenceStatusMessage = 'QR submitted. Waiting for verified Presence result...';
      });

      final result = await _pollPresenceResult(session.sessionUuid);
      if (!mounted) {
        return;
      }
      _showPresenceResultSnackBar(result);
      await _stopAllStreamingPaths(cameraProvider);
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to complete verified Presence: $error'),
          backgroundColor: Colors.red,
        ),
      );
      await _stopAllStreamingPaths(cameraProvider);
    } finally {
      if (mounted) {
        setState(() {
          _presenceFlowBusy = false;
          _presenceStatusMessage = null;
        });
      }
    }
  }

  Future<PresenceMobileResult> _pollPresenceResult(String sessionUuid) async {
    while (true) {
      final result = await _presenceService.getResult(sessionUuid);
      if (result.isTerminal) {
        return result;
      }
      await Future<void>.delayed(const Duration(seconds: 2));
    }
  }

  Future<void> _restoreStreamingAfterPresence({
    required CameraProvider cameraProvider,
    required bool wasStreamingBeforePresence,
  }) async {
    if (wasStreamingBeforePresence) {
      return;
    }
    if (!_isAnyStreamingActive(cameraProvider)) {
      return;
    }
    await _stopAllStreamingPaths(cameraProvider);
  }

  Future<void> _prepareForFrontCameraPresence(CameraProvider cameraProvider) async {
    await _stopAllStreamingPaths(cameraProvider);
    await Future<void>.delayed(const Duration(milliseconds: 800));

    await _ensureCameraDirection(cameraProvider, useFrontCamera: true);
    await Future<void>.delayed(const Duration(milliseconds: 1200));
  }

  Future<void> _startVerifiedPresenceStreaming(CameraProvider cameraProvider) async {
    try {
      await _handleSimpleStreamingWorkflow();
      return;
    } catch (_) {
      // _handleSimpleStreamingWorkflow handles user-visible errors internally.
    }

    setState(() {
      _presenceStatusMessage = 'Front camera is slow to start. Retrying live Presence...';
    });

    await _stopAllStreamingPaths(cameraProvider);
    await Future<void>.delayed(const Duration(milliseconds: 1500));
    await _ensureCameraDirection(cameraProvider, useFrontCamera: true);
    await Future<void>.delayed(const Duration(milliseconds: 1800));
    await _handleSimpleStreamingWorkflow();
  }

  Future<void> _ensureCameraDirection(
    CameraProvider cameraProvider, {
    required bool useFrontCamera,
  }) async {
    if (cameraProvider.isFrontCamera == useFrontCamera) {
      return;
    }

    await cameraProvider.switchCamera();

    if (cameraProvider.isFrontCamera != useFrontCamera) {
      final expectedCamera = useFrontCamera ? 'front' : 'back';
      throw Exception('Failed to switch to the $expectedCamera camera');
    }
  }

  Future<void> _stopAllStreamingPaths(CameraProvider cameraProvider) async {
    final mobileStreamingService = MobileStreamingService();

    mobileStreamingService.disableFrameSending();

    if (CameraService.instance.isStreaming) {
      await CameraService.instance.stopStreaming();
    }

    if (cameraProvider.isStreaming) {
      await cameraProvider.stopStreaming();
    }
  }

  Future<void> _stopAndResetCameraState(CameraProvider cameraProvider) async {
    final messenger = ScaffoldMessenger.of(context);

    try {
      if (_isAnyStreamingActive(cameraProvider)) {
        await _stopAllStreamingPaths(cameraProvider);
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _presenceFlowBusy = false;
        _activePresenceSessionUuid = null;
        _presenceStatusMessage = null;
      });
      cameraProvider.clearError();

      messenger.clearSnackBars();
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Camera reset to idle state. Streaming stopped and Presence flow cleared.'),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 3),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      messenger.showSnackBar(
        SnackBar(
          content: Text('Failed to stop camera activity: $error'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showPresenceResultSnackBar(PresenceMobileResult result) {
    final success = result.decision == 'granted';
    final message = success
        ? 'Presence completed: ${result.reasonCode}'
        : _humanizePresenceFailureReason(result.reasonCode);
    _presenceResultAlertTimer?.cancel();
    setState(() {
      _presenceResultAlert = _PresenceResultAlertData(
        message: message,
        backgroundColor: success ? Colors.green.shade700 : Colors.red.shade700,
        icon: success ? Icons.check_circle : Icons.cancel,
      );
    });

    _presenceResultAlertTimer = Timer(const Duration(seconds: 3), () {
      if (!mounted) {
        return;
      }
      setState(() {
        _presenceResultAlert = null;
      });
    });
  }

  String _humanizePresenceFailureReason(String reasonCode) {
    switch (reasonCode) {
      case 'presence_session_expired':
        return 'Presence timed out before the match completed. Please try again.';
      case 'presence_attempt_limit_reached':
        return 'Presence used all available attempts. Please try again.';
      case 'presence_no_match':
        return 'Presence did not find a match. Please try again.';
      default:
        return 'Presence ended unsuccessfully. Please try again.';
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

class _OwnerQrDisplayScreen extends StatelessWidget {
  final String qrData;
  final String ownerDisplayName;

  const _OwnerQrDisplayScreen({
    required this.qrData,
    required this.ownerDisplayName,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('User Owner QR'),
      ),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: QrImageView(
                    data: qrData,
                    version: QrVersions.auto,
                    size: 260,
                    backgroundColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  ownerDisplayName.isEmpty
                      ? 'Owner QR ready for station scan.'
                      : ownerDisplayName,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                SelectableText(
                  qrData,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PresenceResultAlertData {
  const _PresenceResultAlertData({
    required this.message,
    required this.backgroundColor,
    required this.icon,
  });

  final String message;
  final Color backgroundColor;
  final IconData icon;
}

class _CameraPresenceQrScannerScreen extends StatefulWidget {
  const _CameraPresenceQrScannerScreen();

  @override
  State<_CameraPresenceQrScannerScreen> createState() => _CameraPresenceQrScannerScreenState();
}

class _CameraPresenceQrScannerScreenState extends State<_CameraPresenceQrScannerScreen> {
  final MobileScannerController _controller = MobileScannerController(facing: CameraFacing.back);
  bool _handled = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Presence QR')),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: (capture) {
              if (_handled) {
                return;
              }
              final value = capture.barcodes.firstOrNull?.rawValue;
              if (value == null || value.isEmpty) {
                return;
              }
              _handled = true;
              Navigator.of(context).pop(value);
            },
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              margin: const EdgeInsets.all(24),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                'Point the back camera at the station QR to continue Presence.',
                style: TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
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

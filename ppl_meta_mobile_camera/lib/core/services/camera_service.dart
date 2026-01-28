import 'dart:io';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:device_info_plus/device_info_plus.dart';
import '../models/camera_config.dart';
import '../../services/mobile_streaming_service.dart' hide StreamQuality;

/// Core camera service for PPL Meta Mobile Camera
class CameraService {
  static CameraService? _instance;
  static CameraService get instance => _instance ??= CameraService._();
  CameraService._();

  CameraController? _controller;
  List<CameraDescription>? _cameras;
  CameraConfig? _currentConfig;
  bool _isInitialized = false;
  bool _isStreaming = false;
  
  // Streaming service integration
  MobileStreamingService? _streamingService;

  // Getters
  CameraController? get controller => _controller;
  List<CameraDescription>? get availableCameras => _cameras;
  CameraConfig? get currentConfig => _currentConfig;
  bool get isInitialized => _isInitialized;
  bool get isStreaming => _isStreaming;

  /// Set the streaming service for frame transmission
  void setStreamingService(MobileStreamingService streamingService) {
    print('🔗 CameraService.setStreamingService() called');
    _streamingService = streamingService;
    print('✅ Streaming service connected to CameraService');
  }

  /// Initialize camera service and request permissions
  Future<bool> initializeCamera() async {
    try {
      print('Initializing camera service...');
      
      // Check current permission status first
      final currentCameraPermission = await Permission.camera.status;
      final currentMicrophonePermission = await Permission.microphone.status;
      
      print('Current camera permission: $currentCameraPermission');
      print('Current microphone permission: $currentMicrophonePermission');
      
      // Request permissions if not already granted
      PermissionStatus cameraPermission = currentCameraPermission;
      if (cameraPermission != PermissionStatus.granted) {
        print('Requesting camera permission...');
        cameraPermission = await Permission.camera.request();
        print('Camera permission result: $cameraPermission');
      }
      
      PermissionStatus microphonePermission = currentMicrophonePermission;
      if (microphonePermission != PermissionStatus.granted) {
        print('Requesting microphone permission...');
        microphonePermission = await Permission.microphone.request();
        print('Microphone permission result: $microphonePermission');
      }
      
      // Check if camera permission was granted
      if (cameraPermission != PermissionStatus.granted) {
        print('Camera permission not granted: $cameraPermission');
        throw Exception('Camera permission is required to use the camera');
      }

      print('Camera permissions granted, proceeding with camera initialization...');

      // Initialize camera service with robust camera detection
      try {
        print('Starting comprehensive camera detection...');
        final List<CameraDescription> workingCameras = [];
        
        // Test multiple camera configurations that are commonly available on Android
        final List<Map<String, dynamic>> cameraConfigs = [
          // Back cameras
          {'id': '0', 'direction': CameraLensDirection.back, 'orientation': 90},
          {'id': '0', 'direction': CameraLensDirection.back, 'orientation': 0},
          {'id': '0', 'direction': CameraLensDirection.back, 'orientation': 180},
          {'id': '0', 'direction': CameraLensDirection.back, 'orientation': 270},
          // Front cameras  
          {'id': '1', 'direction': CameraLensDirection.front, 'orientation': 270},
          {'id': '1', 'direction': CameraLensDirection.front, 'orientation': 90},
          {'id': '1', 'direction': CameraLensDirection.front, 'orientation': 0},
          {'id': '1', 'direction': CameraLensDirection.front, 'orientation': 180},
          // Additional camera IDs
          {'id': '2', 'direction': CameraLensDirection.back, 'orientation': 90},
          {'id': '3', 'direction': CameraLensDirection.front, 'orientation': 270},
        ];
        
        for (final config in cameraConfigs) {
          try {
            final testCamera = CameraDescription(
              name: config['id'] as String,
              lensDirection: config['direction'] as CameraLensDirection,
              sensorOrientation: config['orientation'] as int,
            );
            
            print('Testing camera: ${testCamera.name} (${testCamera.lensDirection})...');
            
            final testController = CameraController(
              testCamera,
              ResolutionPreset.low,
              enableAudio: false,
            );
            
            // Add timeout to prevent hanging
            await testController.initialize().timeout(
              const Duration(seconds: 5),
              onTimeout: () => throw Exception('Camera initialization timeout'),
            );
            
            // If we reach here, the camera works!
            await testController.dispose();
            
            // Add all working cameras (don't filter by direction anymore)
            // We want all orientations available for selection
            workingCameras.add(testCamera);
            print('✅ Camera ${testCamera.name} (${testCamera.lensDirection}, ${testCamera.sensorOrientation}°) works!');
            
          } catch (e) {
            print('❌ Camera ${config['id']} (${config['direction']}) failed: ${e.toString().split('\n').first}');
          }
          
          // Continue testing all camera configurations to get all orientations
          // No early termination - we want all working cameras available
        }
        
        _cameras = workingCameras;
        print('🎯 Camera detection completed: ${_cameras?.length ?? 0} working cameras found');
        
        if (_cameras != null && _cameras!.isNotEmpty) {
          for (int i = 0; i < _cameras!.length; i++) {
            final camera = _cameras![i];
            print('📷 Camera $i: ID=${camera.name} Direction=${camera.lensDirection} Orientation=${camera.sensorOrientation}°');
          }
        } else {
          print('⚠️ No working cameras detected - device may have restricted camera access');
        }
        
      } catch (e) {
        print('❌ Camera detection failed completely: $e');
        _cameras = <CameraDescription>[];
      }
      
      _isInitialized = true;
      final cameraCount = _cameras?.length ?? 0;
      print('✅ Camera service initialization completed with $cameraCount camera(s) available');
      return true;
      
    } catch (e) {
      print('Failed to initialize camera: $e');
      _isInitialized = false;
      return false;
    }
  }

  /// Setup camera controller with configuration
  Future<bool> setupCamera([CameraConfig? config]) async {
    print('🎬 === CAMERA SETUP START ===');
    
    try {
      if (!_isInitialized) {
        print('❌ Camera service not initialized, cannot setup camera');
        throw Exception('Camera service not initialized');
      }

      print('🎬 Setting up camera...');
      print('🎬 Current cameras list: ${_cameras?.length ?? 0} cameras');
      print('🎬 Provided config: ${config != null ? 'Custom config' : 'Default config'}');

      // Try to detect and setup cameras by attempting to create a camera controller
      if (_cameras == null || _cameras!.isEmpty) {
        print('⚠️ No cameras detected yet, skipping setup - cameras should have been detected during initialization');
        return false;
      }

      print('🎬 Found ${_cameras!.length} detected cameras:');
      for (int i = 0; i < _cameras!.length; i++) {
        final cam = _cameras![i];
        print('🎬   Camera $i: ID=${cam.name}, Direction=${cam.lensDirection}, Orientation=${cam.sensorOrientation}°');
      }

      // Dispose existing controller
      print('🎬 Disposing existing camera controller...');
      await _controller?.dispose();
      _controller = null;
      print('🎬 Previous controller disposed');

      // Use provided config or default to back camera
      final CameraConfig cameraConfig;
      if (config != null) {
        print('🎬 Using provided camera config');
        cameraConfig = config;
      } else {
        print('🎬 Creating default camera config...');
        // Try to find back camera with 0° orientation first (for portrait mode)
        final preferredCamera = _cameras!.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.back && camera.sensorOrientation == 0,
          orElse: () => _cameras!.firstWhere(
            (camera) => camera.lensDirection == CameraLensDirection.back,
            orElse: () => _cameras!.first,
          ),
        );
        
        cameraConfig = CameraConfig(
          camera: preferredCamera,
          resolution: ResolutionPreset.medium,
          enableAudio: false,
        );
        print('🎬 Default config created for ${preferredCamera.lensDirection} camera (ID: ${preferredCamera.name}, Orientation: ${preferredCamera.sensorOrientation}°)');
      }

      _currentConfig = cameraConfig;
      print('🎬 Camera config set: ${cameraConfig.camera.name} (${cameraConfig.camera.lensDirection})');

      // Create new controller with fallback resolution handling
      print('🎬 Creating new camera controller...');
      
      // List of resolution presets to try, in order of preference
      final resolutionPresets = [
        ResolutionPreset.medium,   // Try medium first for better compatibility
        ResolutionPreset.low,      // Fallback to low
        cameraConfig.resolution,   // Try the requested resolution
        ResolutionPreset.high,     // Try high last
      ];
      
      // Use YUV420 format for better streaming compatibility
      const imageFormat = ImageFormatGroup.yuv420;
      
      CameraController? tempController;
      bool initSuccess = false;
      
      for (final preset in resolutionPresets) {
        try {
          print('🎬 Trying resolution preset: ${preset.name}');
          
          tempController = CameraController(
            cameraConfig.camera,
            preset,
            enableAudio: cameraConfig.enableAudio,
            imageFormatGroup: imageFormat,
          );
          
          // Initialize controller
          print('🎬 Initializing camera controller with ${preset.name}...');
          await tempController.initialize();
          
          if (tempController.value.isInitialized) {
            _controller = tempController;
            initSuccess = true;
            print('✅ Camera controller initialized successfully with ${preset.name}!');
            print('🎬 Controller state: initialized=${_controller!.value.isInitialized}');
            print('🎬 Preview size: ${_controller!.value.previewSize}');
            print('🎬 Aspect ratio: ${_controller!.value.aspectRatio}');
            break;
          } else {
            await tempController.dispose();
          }
          
        } catch (e) {
          print('❌ Camera initialization failed with ${preset.name}: $e');
          if (tempController != null) {
            try {
              await tempController.dispose();
            } catch (disposeError) {
              print('❌ Error disposing failed controller: $disposeError');
            }
          }
          
          // If this was the last preset, we'll fail
          if (preset == resolutionPresets.last) {
            throw Exception('Camera initialization failed with all resolution presets: $e');
          }
          
          // Wait a bit before trying next preset
          await Future.delayed(const Duration(milliseconds: 500));
        }
      }
      
      if (!initSuccess) {
        throw Exception('Failed to initialize camera with any resolution preset');
      }
      
      print('🎯 === CAMERA SETUP COMPLETE ===');
      return true;
      
    } catch (e) {
      print('❌ === CAMERA SETUP FAILED ===');
      print('❌ Error during camera setup: $e');
      print('❌ Stack trace: ${StackTrace.current}');
      
      // Clean up on failure
      try {
        await _controller?.dispose();
        _controller = null;
      } catch (disposeError) {
        print('❌ Error disposing controller: $disposeError');
      }
      
      return false;
    }
  }

  /// Switch between front and back cameras
  Future<bool> switchCamera() async {
    try {
      if (_cameras == null || _currentConfig == null) {
        return false;
      }

      print('🔄 [CAMERA_SWITCH] Starting camera switch...');
      print('🔄 [CAMERA_SWITCH] Current streaming state: $_isStreaming');
      
      // Save streaming state before switching
      final wasStreaming = _isStreaming;
      
      // Stop streaming if active
      if (wasStreaming) {
        print('🔄 [CAMERA_SWITCH] Stopping streaming before switch...');
        await stopStreaming();
      }

      final currentDirection = _currentConfig!.camera.lensDirection;
      final newDirection = currentDirection == CameraLensDirection.back
          ? CameraLensDirection.front
          : CameraLensDirection.back;

      final newCamera = _cameras!.firstWhere(
        (camera) => camera.lensDirection == newDirection,
        orElse: () => _currentConfig!.camera,
      );

      if (newCamera == _currentConfig!.camera) {
        print('❌ [CAMERA_SWITCH] No alternative camera found');
        return false; // No alternative camera found
      }

      final newConfig = _currentConfig!.copyWith(camera: newCamera);
      print('🔄 [CAMERA_SWITCH] Setting up new camera...');
      final setupSuccess = await setupCamera(newConfig);
      
      // Restart streaming if it was active before
      if (setupSuccess && wasStreaming) {
        print('🔄 [CAMERA_SWITCH] Restarting streaming after camera switch...');
        await Future.delayed(Duration(milliseconds: 300)); // Brief delay for stability
        await startStreaming();
        print('✅ [CAMERA_SWITCH] Streaming restarted successfully');
      }
      
      return setupSuccess;
    } catch (e) {
      print('❌ [CAMERA_SWITCH] Failed to switch camera: $e');
      return false;
    }
  }

  /// Capture high-resolution photo
  Future<CaptureResult> capturePhoto() async {
    print('🎬 === PHOTO CAPTURE START ===');
    try {
      if (_controller == null || !_controller!.value.isInitialized) {
        print('❌ Camera controller not ready for capture');
        return CaptureResult.error('Camera not initialized');
      }

      print('🎬 Camera controller ready, preparing capture...');

      // Get app documents directory
      final directory = await getApplicationDocumentsDirectory();
      final capturesDir = Directory('${directory.path}/captures');
      if (!await capturesDir.exists()) {
        await capturesDir.create(recursive: true);
        print('🎬 Created captures directory: ${capturesDir.path}');
      }

      // Generate filename with timestamp
      final timestamp = DateTime.now();
      final filename = 'photo_${timestamp.millisecondsSinceEpoch}.jpg';
      final filePath = '${capturesDir.path}/$filename';
      print('🎬 Target file path: $filePath');

      // Add a small delay to ensure texture is stable before capture
      print('🎬 Stabilizing texture before capture...');
      await Future.delayed(const Duration(milliseconds: 200));

      // Capture image
      print('🎬 Taking picture...');
      final XFile image = await _controller!.takePicture();
      print('🎬 Picture taken, temporary path: ${image.path}');
      
      // Verify the captured file exists and has content
      final tempFile = File(image.path);
      if (!await tempFile.exists()) {
        throw Exception('Captured image file does not exist');
      }
      
      final tempFileSize = await tempFile.length();
      print('🎬 Captured image size: $tempFileSize bytes');
      
      if (tempFileSize == 0) {
        throw Exception('Captured image is empty');
      }

      // Move to permanent location
      print('🎬 Moving to permanent location...');
      await tempFile.copy(filePath);
      await tempFile.delete(); // Clean up temp file
      print('🎬 File moved and temp cleaned up');

      // Verify the saved file
      final savedFile = File(filePath);
      if (!await savedFile.exists()) {
        throw Exception('Failed to save image to permanent location');
      }
      
      final fileSize = await savedFile.length();
      print('🎬 Saved file size: $fileSize bytes');
      
      if (fileSize == 0) {
        throw Exception('Saved image file is empty');
      }

      // Get resolution info
      final previewSize = _controller!.value.previewSize;
      final resolution = previewSize != null 
          ? '${previewSize.width.toInt()}x${previewSize.height.toInt()}'
          : 'unknown';

      print('🎬 === PHOTO CAPTURE SUCCESS ===');
      print('🎬 File: $filePath');
      print('🎬 Size: $fileSize bytes');
      print('🎬 Resolution: $resolution');

      return CaptureResult(
        filePath: filePath,
        timestamp: timestamp,
        fileSize: fileSize,
        resolution: resolution,
      );
    } catch (e) {
      print('❌ === PHOTO CAPTURE FAILED ===');
      print('❌ Error: $e');
      print('❌ Stack trace: ${StackTrace.current}');
      return CaptureResult.error('Failed to capture photo: $e');
    }
  }

  /// Start video streaming
  Future<bool> startStreaming() async {
    try {
      if (_controller == null || !_controller!.value.isInitialized) {
        print('❌ Cannot start streaming: Camera controller not initialized');
        return false;
      }

      if (_isStreaming) {
        print('✅ Already streaming, returning true');
        return true; // Already streaming
      }

      print('🎬 Starting image stream for mobile camera...');
      await _controller!.startImageStream(_onImageStreamData);
      _isStreaming = true;
      print('✅ Image stream started successfully');
      return true;
    } catch (e) {
      print('❌ Failed to start streaming: $e');
      
      // Try to recover by stopping and restarting with a simpler configuration
      try {
        print('🔄 Attempting to recover from streaming error...');
        if (_controller != null && _controller!.value.isInitialized) {
          await _controller!.stopImageStream();
        }
        _isStreaming = false;
        
        // Wait a moment before retrying
        await Future.delayed(Duration(milliseconds: 500));
        
        print('🔄 Retrying with basic configuration...');
        await _controller!.startImageStream(_onImageStreamData);
        _isStreaming = true;
        print('✅ Streaming recovered successfully');
        return true;
      } catch (recoveryError) {
        print('❌ Failed to recover streaming: $recoveryError');
        _isStreaming = false;
        return false;
      }
    }
  }

  /// Stop video streaming
  Future<bool> stopStreaming() async {
    try {
      if (_controller == null) {
        _isStreaming = false;
        return true;
      }

      if (_isStreaming) {
        print('🛑 [STOP_STREAMING] Stopping image stream...');
        await _controller!.stopImageStream();
        _isStreaming = false;
        print('✅ [STOP_STREAMING] Image stream stopped');
      }
      return true;
    } catch (e) {
      print('❌ [STOP_STREAMING] Failed to stop streaming: $e');
      _isStreaming = false;
      return false;
    }
  }

  /// Handle image stream data for streaming
  void _onImageStreamData(CameraImage image) {
    // Send frame to backend via streaming service
    print('🔍 _onImageStreamData called - _streamingService: ${_streamingService != null ? "CONNECTED" : "NULL"}, _isStreaming: $_isStreaming');
    if (_streamingService != null && _isStreaming) {
      print('✅ Sending frame to backend via streaming service');
      // Pass the current camera lens direction with each frame
      final isFrontCamera = _controller?.description.lensDirection == CameraLensDirection.front;
      _streamingService!.sendFrameToBackend(image, isFrontCamera: isFrontCamera);
    } else {
      print('❌ NOT sending frame - streamingService: ${_streamingService != null ? "OK" : "NULL"}, isStreaming: $_isStreaming');
    }
    
    // Keep the debug message for monitoring
    print('Received frame: ${image.width}x${image.height} | StreamingService: ${_streamingService != null ? "CONNECTED" : "NULL"} | isStreaming: $_isStreaming');
  }

  /// Update stream quality
  Future<bool> updateStreamQuality(StreamQuality quality) async {
    try {
      if (_currentConfig == null) return false;

      final newConfig = _currentConfig!.copyWith(
        resolution: quality.resolution,
        fps: quality.fps,
        quality: quality.label,
      );

      // If streaming, stop first
      final wasStreaming = _isStreaming;
      if (wasStreaming) {
        await stopStreaming();
      }

      // Reconfigure camera
      final success = await setupCamera(newConfig);
      
      // Restart streaming if it was active
      if (success && wasStreaming) {
        await startStreaming();
      }

      return success;
    } catch (e) {
      print('Failed to update stream quality: $e');
      return false;
    }
  }

  /// Get camera capabilities
  Future<Map<String, dynamic>> getCameraCapabilities() async {
    try {
      if (_controller == null || !_controller!.value.isInitialized) {
        return {};
      }

      return {
        'maxZoom': await _controller!.getMaxZoomLevel(),
        'minZoom': await _controller!.getMinZoomLevel(),
        'hasFlash': _currentConfig?.camera.lensDirection == CameraLensDirection.back,
        'supportedResolutions': ResolutionPreset.values.map((r) => r.toString().split('.').last).toList(),
        'cameraDirection': _currentConfig?.camera.lensDirection.toString().split('.').last,
      };
    } catch (e) {
      print('Failed to get camera capabilities: $e');
      return {};
    }
  }

  /// Get device information for registration
  Future<Map<String, dynamic>> getDeviceInfo() async {
    try {
      final deviceInfo = DeviceInfoPlugin();
      
      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        return {
          'deviceId': androidInfo.id,
          'model': androidInfo.model,
          'brand': androidInfo.brand,
          'manufacturer': androidInfo.manufacturer,
          'version': androidInfo.version.release,
          'platform': 'android',
        };
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        return {
          'deviceId': iosInfo.identifierForVendor ?? 'unknown',
          'model': iosInfo.model,
          'brand': 'Apple',
          'manufacturer': 'Apple',
          'version': iosInfo.systemVersion,
          'platform': 'ios',
        };
      }
      
      return {
        'deviceId': 'unknown',
        'model': 'unknown',
        'platform': Platform.operatingSystem,
      };
    } catch (e) {
      print('Failed to get device info: $e');
      return {
        'deviceId': 'error',
        'model': 'error',
        'platform': Platform.operatingSystem,
      };
    }
  }

  /// Check if camera is available on this device
  Future<bool> isCameraAvailable() async {
    try {
      // TODO: Fix availableCameras import issue
      return false; // Temporary stub
    } catch (e) {
      print('Error checking camera availability: $e');
      return false;
    }
  }

  /// Start camera image stream for live processing
  Future<void> startImageStream(Function(CameraImage) onImage) async {
    if (!_isInitialized || _controller == null) {
      throw StateError('Camera not initialized');
    }

    print('Starting camera image stream...');
    await _controller!.startImageStream(onImage);
    print('Camera image stream started');
  }

  /// Stop camera image stream
  Future<void> stopImageStream() async {
    if (_controller != null && _controller!.value.isStreamingImages) {
      print('Stopping camera image stream...');
      await _controller!.stopImageStream();
      print('Camera image stream stopped');
    }
  }

  /// Dispose resources
  Future<void> dispose() async {
    await stopImageStream();
    await stopStreaming();
    await _controller?.dispose();
    _controller = null;
    _currentConfig = null;
    _isInitialized = false;
  }
}

import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
import '../models/camera_config.dart';
import '../services/camera_service.dart';
import '../services/gallery_service.dart';
import '../services/streaming_service.dart';
import '../services/authentication_service.dart';
import '../interfaces/camera_interface.dart';
import '../../shared/models/media_item.dart';
import 'gallery_provider.dart';

/// Camera provider for managing camera state and operations
class CameraProvider extends ChangeNotifier implements ICameraOperations {
  final CameraService _cameraService = CameraService.instance;
  final GalleryService _galleryService = GalleryService.instance;
  final StreamingService _streamingService = StreamingService.instance;

  // Camera state
  bool _isInitialized = false;
  bool _isLoading = false;
  String? _error;
  CameraConfig? _currentConfig;

  // Streaming state
  bool _isStreamingMode = false;
  bool _isStreaming = false;
  Map<String, dynamic> _streamingStats = {};

  // Gallery state
  List<MediaItem> _galleryItems = [];
  bool _isLoadingGallery = false;
  Map<String, dynamic> _galleryStats = {};

  // UI state
  bool _isFlashOn = false;
  double _zoomLevel = 1.0;
  bool _isFrontCamera = false;

  // Getters
  bool get isInitialized => _isInitialized;
  bool get isLoading => _isLoading;
  String? get error => _error;
  CameraConfig? get currentConfig => _currentConfig;
  CameraController? get cameraController => _cameraService.controller;

  bool get isStreamingMode => _isStreamingMode;
  bool get isStreaming => _isStreaming;
  Map<String, dynamic> get streamingStats => _streamingStats;

  List<MediaItem> get galleryItems => _galleryItems;
  bool get isLoadingGallery => _isLoadingGallery;
  Map<String, dynamic> get galleryStats => _galleryStats;

  bool get isFlashOn => _isFlashOn;
  double get zoomLevel => _zoomLevel;
  bool get isFrontCamera => _isFrontCamera;

  /// Initialize the camera provider with all necessary services
  Future<void> initialize() async {
    print('🔍 === CAMERA PROVIDER INITIALIZE CALLED ===');
    print('🔍 Current state: _isInitialized=$_isInitialized, _isLoading=$_isLoading');
    
    if (_isInitialized) {
      print('Camera provider already initialized');
      return;
    }

    _setLoading(true);
    clearError();

    try {
      print('🎯 === STARTING CAMERA PROVIDER INITIALIZATION ===');
      
      // Initialize camera service
      print('🔧 Step 1: Initializing camera service...');
      final cameraInitialized = await _cameraService.initializeCamera();
      print('🔧 Step 1 Result: Camera service initialized = $cameraInitialized');
      
      if (!cameraInitialized) {
        throw Exception('Camera initialization failed - please check camera permissions');
      }

      print('🔧 Step 2: Setting up camera with detected cameras...');
      print('🔧 Available cameras count: ${_cameraService.availableCameras?.length ?? 0}');

      // Setup camera with default configuration
      final cameraSetup = await _cameraService.setupCamera();
      print('🔧 Step 2 Result: Camera setup = $cameraSetup');
      
      if (!cameraSetup) {
        // Camera setup failed but service is initialized
        print('⚠️ Warning: Failed to setup camera - continuing in limited mode');
        _currentConfig = null; // No camera configuration available
      } else {
        _currentConfig = _cameraService.currentConfig;
        _isFrontCamera = _currentConfig?.camera.lensDirection == CameraLensDirection.front;
        print('✅ Camera setup completed successfully');
        print('📷 Available cameras: ${_cameraService.availableCameras?.length ?? 0}');
        print('📷 Current camera: ${_isFrontCamera ? 'front' : 'back'}');
        print('📷 Camera controller ready: ${_cameraService.controller?.value.isInitialized ?? false}');
      }

      // Initialize gallery service
      print('🔧 Step 3: Initializing gallery service...');
      final galleryInitialized = await _galleryService.initializeGallery();
      print('🔧 Step 3 Result: Gallery initialized = $galleryInitialized');
      
      if (!galleryInitialized) {
        print('⚠️ Warning: Failed to initialize gallery service');
      }

      _isInitialized = true;
      print('✅ Camera provider initialization completed successfully');

      // Load initial gallery data
      print('🔧 Step 4: Loading initial gallery data...');
      await refreshGallery();
      print('🔧 Step 4 Result: Gallery refresh completed');

      print('🎯 === CAMERA PROVIDER INITIALIZATION COMPLETE ===');
      print('🎯 Final state: initialized=$_isInitialized, hasCamera=${_currentConfig != null}, cameraCount=${_cameraService.availableCameras?.length ?? 0}');
      
      notifyListeners();
    } catch (e) {
      print('❌ === CAMERA PROVIDER INITIALIZATION FAILED ===');
      print('❌ Error: $e');
      print('❌ Stack trace: ${StackTrace.current}');
      
      if (e.toString().contains('permission')) {
        _setError('Camera permission required. Please grant camera access in device settings and restart the app.');
      } else {
        _setError('Failed to initialize camera: ${e.toString()}');
      }
    } finally {
      _setLoading(false);
    }
  }

  /// Initialize the camera provider with platform connectivity data
  /// This method is called after camera registration to set up streaming capabilities
  Future<void> initializeWithConnectivity({
    required Map<String, dynamic> connectivityData,
    required String registeredCameraName,
  }) async {
    print('🔗 === INITIALIZING CAMERA PROVIDER WITH CONNECTIVITY ===');
    print('🔗 Camera name: $registeredCameraName');
    print('🔗 Connectivity data: $connectivityData');

    try {
      // First initialize the basic camera functionality
      await initialize();

      // Initialize streaming service with server configuration
      String? streamingServerUrl;
      
      // Store connectivity information for streaming
      if (connectivityData['streaming_endpoints'] != null) {
        print('🔗 Configuring streaming endpoints...');
        final streamingEndpoints = connectivityData['streaming_endpoints'] as Map<String, dynamic>;
        
        // Try to use websocket endpoint for streaming
        if (streamingEndpoints['websocket'] != null) {
          streamingServerUrl = streamingEndpoints['websocket'] as String;
          // Convert ws:// back to http:// for the base URL
          streamingServerUrl = streamingServerUrl!.replaceFirst('ws://', 'http://').replaceFirst('/ws/camera_stream', '');
        } else if (streamingEndpoints['stream'] != null) {
          streamingServerUrl = streamingEndpoints['stream'] as String;
        }
        
        print('🔗 Extracted streaming server URL: $streamingServerUrl');
      }

      if (connectivityData['camera_endpoints'] != null) {
        print('🔗 Configuring camera API endpoints...');
        // Store camera endpoints for future use
      }

      if (connectivityData['media_endpoints'] != null) {
        print('🔗 Configuring media endpoints...');
        // Store media endpoints for gallery operations
      }

      // Initialize streaming service if we have streaming endpoints
      if (streamingServerUrl != null) {
        print('🔗 Initializing streaming service with URL: $streamingServerUrl');
        
        // Get auth headers from AuthenticationService
        final authService = AuthenticationService.instance;
        final authHeaders = authService.getAuthHeaders();
        
        final streamingInitialized = await _streamingService.initializeStreaming(
          serverUrl: streamingServerUrl,
          authHeaders: authHeaders,
        );
        
        if (streamingInitialized) {
          print('✅ Streaming service initialized successfully');
          
          // Try to connect to streaming server
          final connected = await _streamingService.connect();
          if (connected) {
            print('✅ Connected to streaming server');
          } else {
            print('⚠️ Could not connect to streaming server initially');
          }
        } else {
          print('❌ Failed to initialize streaming service');
        }
      } else {
        print('⚠️ No streaming server URL found in connectivity data');
      }

      print('✅ Camera provider initialized with connectivity data');
      notifyListeners();
    } catch (e) {
      print('❌ Failed to initialize camera provider with connectivity: $e');
      rethrow;
    }
  }  /// Switch between front and back cameras
  Future<void> switchCamera() async {
    if (_isLoading) {
      print('Camera switch already in progress');
      return;
    }

    _setLoading(true);
    clearError();

    try {
      print('Attempting to switch camera...');
      
      // Check if camera service is properly initialized
      if (!_cameraService.isInitialized) {
        throw Exception('Camera service not initialized');
      }
      
      final success = await _cameraService.switchCamera();
      if (success) {
        _currentConfig = _cameraService.currentConfig;
        _isFrontCamera = _currentConfig?.camera.lensDirection == CameraLensDirection.front;
        print('✅ Camera switched successfully to ${_isFrontCamera ? 'front' : 'back'} camera');
        notifyListeners();
      } else {
        final errorMsg = 'Failed to switch camera - only ${_cameraService.availableCameras?.length ?? 0} camera(s) available';
        print('❌ $errorMsg');
        _setError(errorMsg);
      }
    } catch (e) {
      print('❌ Error switching camera: $e');
      _setError('Error switching camera: ${e.toString()}');
    } finally {
      _setLoading(false);
    }
  }

  /// Capture photo
  Future<CaptureResult?> capturePhoto() async {
    print('📸 === CAMERA PROVIDER CAPTURE START ===');
    _setLoading(true);
    clearError();

    try {
      print('📸 Initiating camera service capture...');
      final result = await _cameraService.capturePhoto();
      
      if (result.success) {
        print('📸 Capture successful, adding to gallery...');
        
        // Add to gallery service
        await _galleryService.addMediaItem(result.filePath!);
        print('📸 Added to gallery service');
        
        // Add delay to allow file system to settle and texture to stabilize
        print('📸 Waiting for file system to settle...');
        await Future.delayed(const Duration(milliseconds: 500));
        
        // Force refresh gallery
        print('📸 Refreshing gallery...');
        await refreshGallery();
        
        print('📸 === CAPTURE COMPLETE SUCCESS ===');
        notifyListeners();
        return result;
      } else {
        print('❌ Capture failed: ${result.error}');
        _setError(result.error ?? 'Failed to capture photo');
        return result;
      }
    } catch (e) {
      print('❌ === CAPTURE ERROR ===');
      print('❌ Error: $e');
      _setError('Error capturing photo: ${e.toString()}');
      return CaptureResult.error(e.toString());
    } finally {
      _setLoading(false);
    }
  }

  /// Toggle streaming mode
  void toggleStreamingMode() {
    _isStreamingMode = !_isStreamingMode;
    
    if (!_isStreamingMode && _isStreaming) {
      stopStreaming();
    }
    
    notifyListeners();
  }

  /// Start streaming
  Future<void> startStreaming({
    String? streamTitle,
    String? streamDescription,
    StreamQuality? quality,
  }) async {
    _setLoading(true);
    clearError();

    try {
      if (!_streamingService.isConnected) {
        _setError('Not connected to streaming server');
        return;
      }

      final success = await _streamingService.startStream(
        streamTitle: streamTitle,
        streamDescription: streamDescription,
        quality: quality,
      );

      if (success) {
        _isStreaming = true;
        _startStreamingStatsUpdate();
        notifyListeners();
      } else {
        _setError('Failed to start streaming');
      }
    } catch (e) {
      _setError('Error starting stream: ${e.toString()}');
    } finally {
      _setLoading(false);
    }
  }

  /// Stop streaming
  Future<void> stopStreaming() async {
    _setLoading(true);

    try {
      await _streamingService.stopStream();
      _isStreaming = false;
      await _updateStreamingStats();
      notifyListeners();
    } catch (e) {
      _setError('Error stopping stream: ${e.toString()}');
    } finally {
      _setLoading(false);
    }
  }

  /// Update stream quality
  Future<void> updateStreamQuality(StreamQuality quality) async {
    try {
      await _cameraService.updateStreamQuality(quality);
      _currentConfig = _cameraService.currentConfig;
      notifyListeners();
    } catch (e) {
      _setError('Error updating stream quality: ${e.toString()}');
    }
  }

  /// Toggle flash
  Future<void> toggleFlash() async {
    try {
      if (_cameraService.controller == null) return;

      final newFlashMode = _isFlashOn ? FlashMode.off : FlashMode.torch;
      await _cameraService.controller!.setFlashMode(newFlashMode);
      
      _isFlashOn = !_isFlashOn;
      notifyListeners();
    } catch (e) {
      _setError('Error toggling flash: ${e.toString()}');
    }
  }

  /// Set zoom level
  Future<void> setZoomLevel(double zoom) async {
    try {
      if (_cameraService.controller == null) return;

      final maxZoom = await _cameraService.controller!.getMaxZoomLevel();
      final minZoom = await _cameraService.controller!.getMinZoomLevel();
      
      _zoomLevel = zoom.clamp(minZoom, maxZoom);
      await _cameraService.controller!.setZoomLevel(_zoomLevel);
      
      notifyListeners();
    } catch (e) {
      _setError('Error setting zoom: ${e.toString()}');
    }
  }

  /// Refresh gallery
  Future<void> refreshGallery() async {
    print('🔄 === GALLERY REFRESH START ===');
    _isLoadingGallery = true;
    notifyListeners();

    try {
      print('🔄 Getting all media from gallery service...');
      _galleryItems = await _galleryService.getAllMedia();
      print('🔄 Found ${_galleryItems.length} media items');
      
      print('🔄 Getting gallery stats...');
      _galleryStats = await _galleryService.getGalleryStats();
      print('🔄 Gallery stats loaded');
      
      print('🔄 === GALLERY REFRESH SUCCESS ===');
    } catch (e) {
      print('❌ === GALLERY REFRESH ERROR ===');
      print('❌ Error: $e');
      _setError('Error loading gallery: ${e.toString()}');
    } finally {
      _isLoadingGallery = false;
      notifyListeners();
    }
  }

  /// Delete media item
  Future<void> deleteMediaItem(String mediaId) async {
    try {
      final success = await _galleryService.deleteMediaItem(mediaId);
      if (success) {
        await refreshGallery();
      } else {
        _setError('Failed to delete media item');
      }
    } catch (e) {
      _setError('Error deleting media: ${e.toString()}');
    }
  }

  /// Delete multiple media items
  Future<void> deleteMultipleMedia(List<String> mediaIds) async {
    _setLoading(true);

    try {
      await _galleryService.deleteMultipleMedia(mediaIds);
      await refreshGallery();
    } catch (e) {
      _setError('Error deleting media: ${e.toString()}');
    } finally {
      _setLoading(false);
    }
  }

  /// Get paginated gallery items
  Future<List<MediaItem>> getGalleryPage(int page, {int limit = 20}) async {
    try {
      return await _galleryService.getMediaPaginated(
        page: page,
        limit: limit,
      );
    } catch (e) {
      _setError('Error loading gallery page: ${e.toString()}');
      return [];
    }
  }

  /// Start streaming stats update
  void _startStreamingStatsUpdate() {
    // Update streaming stats periodically
    Future.doWhile(() async {
      if (!_isStreaming) return false;
      
      await Future.delayed(Duration(seconds: 1));
      await _updateStreamingStats();
      return _isStreaming;
    });
  }

  /// Update streaming stats
  Future<void> _updateStreamingStats() async {
    _streamingStats = await _streamingService.getStreamingStats();
    notifyListeners();
  }

  /// Set loading state
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  /// Set error state
  void _setError(String error) {
    _error = error;
    notifyListeners();
  }

  /// Clear error state
  void clearError() {
    _error = null;
    notifyListeners();
  }

  // ICameraOperations interface implementation
  @override
  Future<void> startImageStream(Function(CameraImage) onImage) async {
    await _cameraService.startImageStream(onImage);
  }

  @override
  Future<void> stopImageStream() async {
    await _cameraService.stopImageStream();
  }

  /// Dispose resources
  @override
  void dispose() {
    _cameraService.dispose();
    _streamingService.dispose();
    super.dispose();
  }
}

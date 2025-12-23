import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'dart:async';
import 'dart:math' as math;
import '../../../core/config/app_config.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/providers/multi_camera_providers.dart';
import '../../../core/models/camera.dart';
import '../../../core/services/auth_service.dart';

/// Simplified camera stream player that focuses on MJPEG rendering
/// without complex provider state management
class CameraStreamPlayerSimple extends ConsumerStatefulWidget {
  final String cameraId;
  final double? width;
  final double? height;
  final VoidCallback? onError;
  final VoidCallback? onStop;

  const CameraStreamPlayerSimple({
    super.key,
    required this.cameraId,
    this.width,
    this.height,
    this.onError,
    this.onStop,
  });

  @override
  ConsumerState<CameraStreamPlayerSimple> createState() => _CameraStreamPlayerSimpleState();
}

class _CameraStreamPlayerSimpleState extends ConsumerState<CameraStreamPlayerSimple> {
  bool _isActive = false;
  bool _isStreaming = false;
  String? _elementId;
  html.ImageElement? _imageElement;
  html.DivElement? _containerElement;
  String? _currentStreamUrl;
  int _retryCount = 0;
  final int _maxRetries = 5;
  final int _retryDelay = 2;

  @override
  void initState() {
    super.initState();
    _elementId = 'camera-stream-${widget.cameraId}-${DateTime.now().millisecondsSinceEpoch}';
    _isActive = true;
    _startStreaming();
  }

  @override
  void dispose() {
    _isActive = false;
    _stopStreaming();
    super.dispose();
  }

  void _startStreaming() {
    if (!_isActive) return;
    
    // Clear any cached URL when starting fresh to ensure new session
    _currentStreamUrl = null;
    _retryCount = 0;
    
    print('🎥 Starting stream for camera: ${widget.cameraId} (before setState)');
    
    // Check if widget is still mounted and not disposed before calling setState
    try {
      if (mounted && context.mounted) {
        setState(() {
          _isStreaming = true;
        });
        print('✅ _isStreaming set to true for camera: ${widget.cameraId}');
      }
    } catch (e) {
      // Widget is already disposed, ignore setState error
      print('🎥 Widget already disposed for camera: ${widget.cameraId}');
    }
  }

  void _stopStreaming() {
    print('🛑 Stopping stream for camera: ${widget.cameraId} (before setState)');
    
    // Check if widget is still mounted and not disposed before calling setState
    try {
      if (mounted && context.mounted) {
        setState(() {
          _isStreaming = false;
        });
        print('❌ _isStreaming set to false for camera: ${widget.cameraId}');
      }
    } catch (e) {
      // Widget is already disposed, ignore setState error
      print('🛑 Widget already disposed for camera: ${widget.cameraId}');
    }
    
    // Clean up HTML elements
    _imageElement?.remove();
    _imageElement = null;
    _containerElement?.remove();
    _containerElement = null;
    _currentStreamUrl = null;
    _retryCount = 0;
    
    widget.onStop?.call();
  }

  Future<String?> _prepareAuthenticatedUrlWithCamera(dynamic camera) async {
    // Check if widget is still active before proceeding
    if (!_isActive || !mounted) {
      print('🚫 Widget not active or mounted, aborting URL preparation');
      return null;
    }
    
    // If we already have a cached URL, return it to avoid recreating
    if (_currentStreamUrl != null) {
      return _currentStreamUrl;
    }
    
    try {

      // ✅✅✅ FIXED VERSION - NO BLOCKING CALL ✅✅✅
      debugPrint('🎥 [SIMPLE_STREAMING_V2_FIXED] Setting up direct stream for camera: ${camera.deviceId}');
      debugPrint('✅ [VERIFY] This is camera_stream_player_SIMPLE.dart - NO startStreaming call!');
      
      // Get authentication token
      final authService = ref.read(authServiceProvider);
      final token = await authService.getToken();
      
      debugPrint('🔑 [SIMPLE_STREAMING] Got auth token: ${token != null ? "${token.substring(0, 20)}..." : "NULL"}');
      
      if (token == null) {
        debugPrint('❌ [SIMPLE_STREAMING] No authentication token available');
        return null;
      }
      
      // Create simple direct streaming URL with token - same for all camera types
      final baseUrl = AppConfig.instance.cameraServiceUrl;
      final authenticatedUrl = '$baseUrl/api/v1/streaming/${camera.deviceId}/video?token=$token';
      
      debugPrint('🎥 [SIMPLE_STREAMING] Direct stream URL: ${authenticatedUrl.replaceAll(token, "***")}');
      
      // Final check before caching the URL
      if (!_isActive || !mounted) {
        print('🚫 Widget disposed before caching URL');
        return null;
      }
      
      // Cache the URL so we don't recreate on every rebuild
      _currentStreamUrl = authenticatedUrl;
      return authenticatedUrl;
    } catch (e) {
      print('Error preparing simple stream URL: $e');
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    // Early return if widget is not active to prevent disposed widget issues
    if (!_isActive || !mounted) {
      print('🚫 Widget not active or not mounted for camera: ${widget.cameraId}');
      return Container(
        width: widget.width ?? 640,
        height: widget.height ?? 480,
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: _buildStoppedView(),
        ),
      );
    }
    
    // NOTE: Debug print removed to prevent console spam during recording
    // print('📺 Building widget for camera: ${widget.cameraId}, _isStreaming: $_isStreaming');
    
    return Container(
      width: widget.width ?? 640,
      height: widget.height ?? 480,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: _isStreaming ? _buildStreamView() : _buildStoppedView(),
      ),
    );
  }

  Widget _buildStoppedView() {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.videocam_off,
              size: 48,
              color: Colors.white54,
            ),
            const SizedBox(height: 16),
            Text(
              'Camera stopped',
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _startStreaming,
              child: const Text('Start Camera'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStreamView() {
    // Watch camera data to handle loading states properly
    final cameraAsyncValue = ref.watch(cameraByIdProvider(widget.cameraId));
    
    // Handle camera data loading state at widget level
    return cameraAsyncValue.when(
      loading: () => const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 16),
            Text(
              'Loading camera data...',
              style: TextStyle(color: Colors.white70),
            ),
          ],
        ),
      ),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: Colors.red.shade300,
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading camera: $error',
              style: TextStyle(color: Colors.red.shade300),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _stopStreaming,
              child: const Text('Stop'),
            ),
          ],
        ),
      ),
      data: (camera) {
        if (camera == null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.camera_alt_outlined,
                  size: 48,
                  color: Colors.white54,
                ),
                const SizedBox(height: 16),
                Text(
                  'Camera not found',
                  style: TextStyle(color: Colors.white70),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _stopStreaming,
                  child: const Text('Stop'),
                ),
              ],
            ),
          );
        }
        
        // Camera data is available, proceed with stream setup
        final urlFuture = _currentStreamUrl != null 
            ? Future.value(_currentStreamUrl)
            : _prepareAuthenticatedUrlWithCamera(camera);
            
        return FutureBuilder<String?>(
          future: urlFuture,
          builder: (context, snapshot) {
            // Only check if widget is disposed, but allow streaming state to be managed normally
            // The _isStreaming check was causing premature termination during async URL preparation
            if (!mounted || !_isActive) {
              return _buildStoppedView();
            }
            
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircularProgressIndicator(color: Colors.white),
                    SizedBox(height: 16),
                    Text(
                      'Preparing camera stream...',
                      style: TextStyle(color: Colors.white70),
                    ),
                  ],
                ),
              );
            }
        
        if (snapshot.hasError || !snapshot.hasData || snapshot.data == null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.camera_alt_outlined,
                  size: 48,
                  color: Colors.white54,
                ),
                const SizedBox(height: 16),
                Text(
                  'Failed to load camera stream',
                  style: TextStyle(color: Colors.white70),
                  textAlign: TextAlign.center,
                ),
                if (snapshot.hasError) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${snapshot.error}',
                    style: TextStyle(
                      color: Colors.red.shade300,
                      fontSize: 12,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _stopStreaming,
                  child: const Text('Stop'),
                ),
              ],
            ),
          );
        }

        // Stream URL is ready, setup HTML elements
        final authenticatedUrl = snapshot.data!;
        
        if (_imageElement == null) {
          _imageElement = html.ImageElement();
          _imageElement!.crossOrigin = 'anonymous';
          
          // Set a unique ID for the image element for orientation detection
          final imageElementId = 'img-${_elementId}';
          _imageElement!.id = imageElementId;
          
          // Check if this is a mobile camera for orientation handling
          final cameraAsyncValue = ref.read(cameraByIdProvider(widget.cameraId));
          final isMobileCamera = cameraAsyncValue.when(
            data: (camera) => camera?.type == CameraType.mobile || camera?.isMobileCamera == true,
            loading: () => false,
            error: (_, __) => false,
          );
          
          if (isMobileCamera) {
            // Mobile cameras: use contain to preserve aspect ratio, may stream in portrait
            _imageElement!.style.width = '100%';
            _imageElement!.style.height = '100%';
            _imageElement!.style.objectFit = 'contain';
            _imageElement!.style.objectPosition = 'center';
            _imageElement!.style.transition = 'transform 0.3s ease';
            
            // Orientation will be handled by frame metadata from backend
            print('📱 [MOBILE_STREAM_DEBUG] Mobile camera setup - orientation will be handled by frame metadata');
          } else {
            // Other cameras: use cover for landscape format
            _imageElement!.style.width = '100%';
            _imageElement!.style.height = '100%';
            _imageElement!.style.objectFit = 'cover';
          }
          _imageElement!.style.display = 'block';
          
          final containerDiv = html.DivElement();
          containerDiv.style.width = '100%';
          containerDiv.style.height = '100%';
          containerDiv.style.overflow = 'hidden';
          containerDiv.style.position = 'relative';
          containerDiv.style.backgroundColor = '#000000'; // Black background for mobile cameras
          containerDiv.append(_imageElement!);
          
          // Set the image source with the authenticated URL
          print('🎥 Setting image src to: $authenticatedUrl');
          
          // Add debugging for image state changes
          _imageElement!.onLoad.listen((event) {
            print('✅ Stream loaded successfully for ${widget.cameraId}');
            print('✅ Loaded URL: $authenticatedUrl');
            print('✅ Image natural dimensions: ${_imageElement!.naturalWidth}x${_imageElement!.naturalHeight}');
          });
          
          _imageElement!.onError.listen((event) {
            print('❌ Stream error for ${widget.cameraId}: $event');
            print('❌ Failed URL: $authenticatedUrl');
            print('❌ Error details: ${event.toString()}');
            print('❌ Stream error for ${widget.cameraId}: $event');
            print('❌ Failed URL: $authenticatedUrl');
            print('❌ Error details: ${event.toString()}');
            
            if (_retryCount < _maxRetries && _isActive && _isStreaming && _currentStreamUrl != null) {
              _retryCount++;
              print('Retrying MJPEG stream connection...');
              
              Timer(Duration(seconds: _retryDelay), () {
                if (_isActive && _isStreaming && _imageElement != null && _currentStreamUrl != null) {
                  final currentUrl = Uri.parse(_currentStreamUrl!);
                  String retryUrl;
                  
                  if (currentUrl.hasQuery) {
                    retryUrl = '$_currentStreamUrl&_retry=${DateTime.now().millisecondsSinceEpoch}';
                  } else {
                    retryUrl = '$_currentStreamUrl?_retry=${DateTime.now().millisecondsSinceEpoch}';
                  }
                  
                  print('🔄 Retry attempt ${_retryCount}/${_maxRetries} with URL: $retryUrl');
                  _imageElement!.src = retryUrl;
                }
              });
              widget.onError?.call();
            } else {
              print('❌ Max retries reached or widget disposed, stopping stream');
              _stopStreaming();
            }
          });
          
          // Set the image source AFTER setting up event listeners
          print('🔗 Actually setting image src now...');
          _imageElement!.src = authenticatedUrl;
          
          // Add a timeout to detect if the image never loads
          Timer(const Duration(seconds: 10), () {
            if (_isActive && _isStreaming && _imageElement != null) {
              // Check if image loaded successfully by checking natural dimensions
              if (_imageElement!.naturalWidth == 0 || _imageElement!.naturalHeight == 0) {
                print('⏱️ Image load timeout - stream may not be responding');
                print('⏱️ Natural dimensions: ${_imageElement!.naturalWidth}x${_imageElement!.naturalHeight}');
                // Don't auto-stop, just log for debugging
              } else {
                print('✅ Image successfully loaded within timeout period');
              }
            }
          });
          
          // Register the HTML container with unique view type
          ui_web.platformViewRegistry.registerViewFactory(_elementId!, (int viewId) {
            return containerDiv;
          });
        }
        
        return Stack(
          fit: StackFit.expand,
          children: [
            HtmlElementView(viewType: _elementId!),
            // Live indicator overlay
            Positioned(
              top: 8,
              left: 8,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: Colors.red,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text(
                      'LIVE',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Camera ID overlay
            Positioned(
              top: 8,
              right: 8,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  widget.cameraId,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                  ),
                ),
              ),
            ),
            // Stop button overlay
            Positioned(
              bottom: 8,
              right: 8,
              child: IconButton(
                onPressed: _stopStreaming,
                style: IconButton.styleFrom(
                  backgroundColor: Colors.black54,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.all(8),
                ),
                icon: const Icon(Icons.stop, size: 16),
                tooltip: 'Stop stream',
              ),
            ),
          ],
        );
          },
        );
      },
    );
  }

  /// Detects if mobile camera stream is showing portrait content in landscape container
  /// and applies CSS transform to rotate it correctly
  void _detectAndFixOrientation(String elementId) {
    print('📱 [ORIENTATION_DEBUG] Starting orientation detection for mobile camera');
    
    // For mobile cameras, we know from the logs that the mobile app
    // always selects Camera 0 with Orientation=90° (landscape)
    // but the phone is locked to portrait, so we need to rotate -90°
    Timer(const Duration(seconds: 1), () {
      try {
        final element = html.document.getElementById(elementId);
        if (element == null) {
          print('📱 [ORIENTATION_DEBUG] Element not found: $elementId');
          return;
        }

        if (element is html.ImageElement) {
          final img = element as html.ImageElement;
          final naturalWidth = img.naturalWidth;
          final naturalHeight = img.naturalHeight;
          
          print('📱 [ORIENTATION_DEBUG] Natural dimensions: ${naturalWidth}x${naturalHeight}');
          
          // Based on mobile app logs, we know:
          // - Camera sends landscape video (720x480) but phone is in portrait
          // - We need to rotate +90° to correct the orientation
          
          if (naturalWidth > 0 && naturalHeight > 0) {
            final aspectRatio = naturalWidth / naturalHeight;
            print('📱 [ORIENTATION_DEBUG] Aspect ratio: $aspectRatio');
            
            // If mobile camera shows landscape (width > height) but phone is locked to portrait,
            // we need to rotate it back to portrait orientation
            bool needsRotation = naturalWidth > naturalHeight; // Landscape content
            
            if (needsRotation) {
              print('📱 [ORIENTATION_DEBUG] Mobile camera needs rotation - applying +90° transform');
              
              // Apply CSS transform to rotate the video to portrait
              img.style.transform = 'rotate(90deg)';
              img.style.transformOrigin = 'center center';
              
              // Adjust container dimensions to accommodate the rotated video
              // When we rotate 90°, width and height are swapped
              final container = img.parent;
              if (container != null) {
                // Calculate the scale to fit the rotated video
                final containerWidth = container.clientWidth;
                final containerHeight = container.clientHeight;
                
                // After rotation, effective dimensions are swapped
                final effectiveWidth = naturalHeight; // height becomes width
                final effectiveHeight = naturalWidth; // width becomes height
                
                final scaleX = containerWidth / effectiveWidth;
                final scaleY = containerHeight / effectiveHeight;
                final scale = math.min(scaleX, scaleY);
                
                print('📱 [ORIENTATION_DEBUG] Applying scale: $scale for rotated video');
                img.style.transform = 'rotate(90deg) scale($scale)';
                
                // Center the rotated and scaled video
                img.style.position = 'absolute';
                img.style.top = '50%';
                img.style.left = '50%';
                img.style.marginLeft = '-${(effectiveWidth * scale) / 2}px';
                img.style.marginTop = '-${(effectiveHeight * scale) / 2}px';
              }
            } else {
              print('📱 [ORIENTATION_DEBUG] Mobile camera orientation appears correct - no rotation needed');
            }
          } else {
            print('📱 [ORIENTATION_DEBUG] Invalid dimensions: ${naturalWidth}x${naturalHeight}');
          }
        }
      } catch (e) {
        print('📱 [ORIENTATION_DEBUG] Error in orientation detection: $e');
      }
    }); // Wait 1 second for the image to fully load
  }
}

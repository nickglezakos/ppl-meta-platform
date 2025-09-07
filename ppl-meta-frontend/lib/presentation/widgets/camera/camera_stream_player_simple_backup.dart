import 'dart:async';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/services/camera_service.dart';

part 'camera_stream_player_simple.g.dart';

@riverpod
class StreamingState extends _$StreamingState {
  @override
  bool build() => false;

  void toggle() => state = !state;
  void stop() => state = false;
  void start() => state = true;
}

class CameraStreamPlayerSimple extends ConsumerStatefulWidget {
  final String cameraId;
  final VoidCallback? onStreamingStopped;

  const CameraStreamPlayerSimple({
    super.key,
    required this.cameraId,
    this.onStreamingStopped,
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
    
    setState(() {
      _isStreaming = true;
    });
    
    print('🎥 Starting stream for camera: ${widget.cameraId}');
  }

  void _stopStreaming() {
    print('🛑 Stopping stream for camera: ${widget.cameraId}');
    
    setState(() {
      _isStreaming = false;
    });
    
    // Clean up HTML elements
    _imageElement?.remove();
    _imageElement = null;
    _containerElement?.remove();
    _containerElement = null;
    _currentStreamUrl = null;
    _retryCount = 0;
    
    widget.onStreamingStopped?.call();
  }

  Future<String?> _prepareAuthenticatedUrl() async {
    try {
      final authService = ref.read(authServiceProvider);
      final cameraService = ref.read(cameraServiceProvider.notifier);
      
      // Get authentication token
      final token = authService.currentToken;
      if (token == null) {
        throw Exception('Authentication required');
      }
      
      // Get camera details
      final camera = await cameraService.getCameraById(widget.cameraId);
      if (camera == null) {
        throw Exception('Camera not found');
      }
      
      // Check if this is a mobile camera
      if (camera.type == CameraType.mobile) {
        print('📱 Setting up mobile camera stream for ${widget.cameraId}');
        print('  - Camera type: ${camera.type}');
        print('  - Using mobile streaming endpoint');
        
        // Use the mobile streaming endpoint via service discovery
        final services = await cameraService.getServices();
        final camerasService = services['ppl-meta-cameras'];
        if (camerasService == null) {
          throw Exception('Cameras service not found');
        }
        
        final baseUrl = 'http://${camerasService['host']}:${camerasService['port']}';
        final streamUrl = '$baseUrl/api/v1/streaming/${widget.cameraId}/video';
        
        print('  - Stream URL: $streamUrl');
        print('  - Using Authorization: Bearer token');
        
        return streamUrl;
      } else {
        // Use direct stream URL for regular cameras
        return camera.directStreamUrl;
      }
    } catch (e) {
      print('❌ Error preparing authenticated URL: $e');
      rethrow;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isActive || !_isStreaming) {
      return _buildStoppedView();
    }
    
    return _buildStreamView();
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
    return FutureBuilder<String?>(
      future: _prepareAuthenticatedUrl(),
      builder: (context, snapshot) {
        if (!_isActive || !_isStreaming) {
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
          _imageElement!.style.width = '100%';
          _imageElement!.style.height = '100%';
          _imageElement!.style.objectFit = 'cover';
          _imageElement!.style.display = 'block';
          
          final containerDiv = html.DivElement();
          containerDiv.style.width = '100%';
          containerDiv.style.height = '100%';
          containerDiv.style.overflow = 'hidden';
          containerDiv.style.position = 'relative';
          containerDiv.append(_imageElement!);
          
          // Set the image source with the authenticated URL
          _imageElement!.src = authenticatedUrl;
          
          // Error handling
          _imageElement!.onError.listen((event) {
            print('Stream error for ${widget.cameraId}: $event');
            
            if (_retryCount < _maxRetries && _isActive && _isStreaming) {
              _retryCount++;
              print('Retrying MJPEG stream connection...');
              
              Timer(Duration(seconds: _retryDelay), () {
                if (_isActive && _isStreaming && _imageElement != null) {
                  final currentUrl = Uri.parse(authenticatedUrl);
                  String retryUrl;
                  
                  if (currentUrl.hasQuery) {
                    retryUrl = '$authenticatedUrl&_retry=${DateTime.now().millisecondsSinceEpoch}';
                  } else {
                    retryUrl = '$authenticatedUrl?_retry=${DateTime.now().millisecondsSinceEpoch}';
                  }
                  
                  _imageElement!.src = retryUrl;
                }
              });
            }
          });
          
          // Load event handler
          _imageElement!.onLoad.listen((event) {
            print('Stream loaded successfully for ${widget.cameraId}');
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
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'dart:async';
import '../../../core/config/app_config.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/services/camera_service.dart' show cameraServiceProvider;

class CameraStreamPlayer extends ConsumerStatefulWidget {
  final String cameraId;
  final double? width;
  final double? height;
  final VoidCallback? onError;
  final VoidCallback? onStop;

  const CameraStreamPlayer({
    super.key,
    required this.cameraId,
    this.width,
    this.height,
    this.onError,
    this.onStop,
  });

  @override
  ConsumerState<CameraStreamPlayer> createState() => _CameraStreamPlayerState();
}

class _CameraStreamPlayerState extends ConsumerState<CameraStreamPlayer> {
  String? _currentStreamUrl;
  String? _elementId;
  bool _isActive = true;
  html.ImageElement? _imageElement;
  html.DivElement? _containerElement;

  @override
  void initState() {
    super.initState();
    _elementId = 'camera-stream-${widget.cameraId}-${DateTime.now().millisecondsSinceEpoch}';
  }

  @override
  void dispose() {
    _isActive = false;
    _clearVideoStream();
    super.dispose();
  }

  void _clearVideoStream() {
    print('Clearing video stream for camera ${widget.cameraId}');
    
    try {
      // Clear the image source immediately to stop MJPEG stream
      if (_imageElement != null) {
        _imageElement!.src = '';
        _imageElement!.remove();
        _imageElement = null;
      }
      
      // Clear the container element
      if (_containerElement != null) {
        _containerElement!.remove();
        _containerElement = null;
      }
      
      // Remove the element from DOM if it exists
      if (_elementId != null) {
        final existingElement = html.document.getElementById(_elementId!);
        existingElement?.remove();
        _elementId = null;
      }
      
      // Reset state for fresh restart
      _currentStreamUrl = null;
      
      // Only call setState if the widget is still active
      if (_isActive && mounted) {
        setState(() {
          // Force rebuild to clear the stream display
        });
      }
    } catch (e) {
      print('Error clearing video stream: $e');
    }
    
    widget.onStop?.call();
  }

  void _stopStream() async {
    if (!_isActive) return; // Don't proceed if widget is being disposed
    
    print('Stop stream button pressed for camera ${widget.cameraId}');
    
    // First clear the video display immediately
    _clearVideoStream();
    
    if (!_isActive) return; // Check again before provider call
    
    // Then stop the streaming via the provider
    try {
      await ref.read(cameraStreamProvider.notifier).stopStreaming();
      print('Streaming stopped successfully');
    } catch (e) {
      print('Error stopping stream: $e');
    }
  }

  Future<String?> _prepareAuthenticatedUrl() async {
    try {
      final cameraService = ref.read(cameraServiceProvider);
      
      // Create a streaming session with the camera service
      print('Creating streaming session for camera ${widget.cameraId}...');
      
      final sessionData = await cameraService.createStreamingSession(widget.cameraId);
      
      if (sessionData != null) {
        final streamingUrl = sessionData['streaming_url'];
        
        print('Streaming session created successfully');
        print('Session URL: $streamingUrl');
        
        // Return the full URL with the camera service base
        final baseUrl = AppConfig.instance.cameraServiceUrl;
        final fullStreamingUrl = '$baseUrl$streamingUrl';
        
        print('Full streaming URL: $fullStreamingUrl');
        return fullStreamingUrl;
      } else {
        print('Failed to create streaming session');
        return null;
      }
    } catch (e) {
      print('Error preparing authenticated URL: $e');
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final streamState = ref.watch(cameraStreamProvider);
    
    // Check if streaming has stopped or this camera is not the active one
    final isStreamingStopped = !streamState.isStreaming || 
                              streamState.cameraId != widget.cameraId;
    
    if (!_isActive || isStreamingStopped) {
      // Clear video if we haven't already
      if (_currentStreamUrl != null) {
        print('Stream state changed - stopping: isStreaming=${streamState.isStreaming}, cameraId=${streamState.cameraId}');
        // Clear immediately instead of using post frame callback
        _clearVideoStream();
      }
      
      return Container(
        width: widget.width ?? 640,
        height: widget.height ?? 480,
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.videocam_off,
                size: 48,
                color: Colors.white54,
              ),
              SizedBox(height: 16),
              Text(
                'Camera stream stopped',
                style: TextStyle(color: Colors.white70),
              ),
            ],
          ),
        ),
      );
    }

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
        child: FutureBuilder<String?>(
          future: _prepareAuthenticatedUrl(),
          builder: (context, snapshot) {
            if (!_isActive) {
              return const Center(
                child: Text(
                  'Stream stopped',
                  style: TextStyle(color: Colors.white70),
                ),
              );
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
                  ],
                ),
              );
            }
            
            final streamUrl = snapshot.data!;
            
            // Check if we need to recreate the element (URL changed OR element was cleared)
            if (_currentStreamUrl != streamUrl || _imageElement == null) {
              _currentStreamUrl = streamUrl;
              print('Setting up camera stream: $streamUrl');
              
              // Generate new element ID to ensure uniqueness for each restart
              final timestamp = DateTime.now().millisecondsSinceEpoch;
              _elementId = 'camera-stream-${widget.cameraId}-$timestamp';
              
              // Create container div for better MJPEG stream handling
              final containerDiv = html.DivElement()
                ..style.width = '100%'
                ..style.height = '100%'
                ..style.overflow = 'hidden'
                ..style.position = 'relative'
                ..style.backgroundColor = '#000'
                ..id = _elementId!;
              
              // Create the HTML img element optimized for MJPEG streams
              final imgElement = html.ImageElement()
                ..style.width = '100%'
                ..style.height = '100%'
                ..style.objectFit = 'contain'
                ..style.border = 'none'
                ..style.display = 'block'
                ..style.imageRendering = 'auto'
                ..style.maxWidth = '100%'
                ..style.maxHeight = '100%'
                ..style.position = 'absolute'
                ..style.top = '0'
                ..style.left = '0'
                ..draggable = false;
              
              // For MJPEG streams, set proper headers and attributes
              imgElement.setAttribute('cache-control', 'no-cache');
              imgElement.setAttribute('pragma', 'no-cache');
              imgElement.setAttribute('expires', '0');
              
              // Since we're using session-based URLs, we can directly set the src
              // The URL already contains the session ID for authentication
              print('Setting stream URL directly (session-based): $streamUrl');
              imgElement.src = streamUrl;
              
              // Append img to container
              containerDiv.append(imgElement);
              
              _imageElement = imgElement;
              _containerElement = containerDiv;
              
              // Add error handling with retry logic
              _imageElement!.onError.listen((event) {
                print('Stream error: $event');
                if (mounted && _isActive) {
                  // For MJPEG streams, errors are common during stream transitions
                  // Try to reconnect after a short delay
                  Timer(const Duration(milliseconds: 1000), () {
                    if (_isActive && _imageElement != null && _currentStreamUrl == streamUrl) {
                      print('Retrying MJPEG stream connection...');
                      _imageElement!.src = '$streamUrl&_retry=$timestamp';
                    }
                  });
                  widget.onError?.call();
                }
              });
              
              // Add load event to confirm stream is working
              _imageElement!.onLoad.listen((event) {
                print('Stream loaded successfully for ${widget.cameraId}');
              });
              
              // Add abort handler
              _imageElement!.onAbort.listen((event) {
                print('Stream aborted for ${widget.cameraId}');
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
                if (_isActive && streamState.isStreaming)
                  Positioned(
                    bottom: 8,
                    right: 8,
                    child: IconButton(
                      onPressed: _stopStream,
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
        ),
      ),
    );
  }
}

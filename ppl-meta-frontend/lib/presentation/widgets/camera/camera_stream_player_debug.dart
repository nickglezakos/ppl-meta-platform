import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'dart:async';
import '../../../core/api/api_client.dart';
import '../../../core/config/app_config.dart';

class CameraStreamPlayerDebug extends ConsumerStatefulWidget {
  final String cameraId;
  final double? width;
  final double? height;
  final VoidCallback? onError;

  const CameraStreamPlayerDebug({
    super.key,
    required this.cameraId,
    this.width,
    this.height,
    this.onError,
  });

  @override
  ConsumerState<CameraStreamPlayerDebug> createState() => _CameraStreamPlayerDebugState();
}

class _CameraStreamPlayerDebugState extends ConsumerState<CameraStreamPlayerDebug> {
  String? _elementId;
  bool _isActive = true;
  html.ImageElement? _imageElement;
  html.DivElement? _containerElement;
  String? _currentStreamUrl;
  String _debugInfo = 'Initializing...';

  @override
  void initState() {
    super.initState();
    _elementId = 'camera-stream-debug-${widget.cameraId}-${DateTime.now().millisecondsSinceEpoch}';
    _setupDebugStream();
  }

  @override
  void dispose() {
    _isActive = false;
    _clearVideoStream();
    super.dispose();
  }

  void _clearVideoStream() {
    try {
      if (_imageElement != null) {
        _imageElement!.src = '';
        _imageElement!.remove();
        _imageElement = null;
      }
      
      if (_containerElement != null) {
        _containerElement!.remove();
        _containerElement = null;
      }
      
      if (_elementId != null) {
        final existingElement = html.document.getElementById(_elementId!);
        existingElement?.remove();
      }
    } catch (e) {
      print('Error clearing video stream: $e');
    }
  }

  Future<void> _setupDebugStream() async {
    try {
      setState(() {
        _debugInfo = 'Getting authentication token...';
      });

      final apiClient = ref.read(apiClientProvider);
      final token = apiClient.authToken;
      
      if (token == null) {
        setState(() {
          _debugInfo = 'ERROR: No auth token available';
        });
        return;
      }

      setState(() {
        _debugInfo = 'Token obtained. Building stream URL...';
      });

      // Build the stream URL
      final baseUrl = AppConfig.instance.cameraStreamEndpoint;
      final streamUrl = '$baseUrl/${widget.cameraId}/video?token=$token';
      
      setState(() {
        _debugInfo = 'Stream URL: $streamUrl\nSetting up video element...';
      });

      _currentStreamUrl = streamUrl;
      
      // Create the video element
      await _createVideoElement(streamUrl);
      
    } catch (e) {
      setState(() {
        _debugInfo = 'ERROR: $e';
      });
    }
  }

  Future<void> _createVideoElement(String streamUrl) async {
    try {
      // Generate new element ID
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      _elementId = 'camera-stream-debug-${widget.cameraId}-$timestamp';
      
      // Create container div
      final containerDiv = html.DivElement()
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.overflow = 'hidden'
        ..style.position = 'relative'
        ..style.backgroundColor = '#000'
        ..id = _elementId!;
      
      // Create the HTML img element for MJPEG stream
      final imgElement = html.ImageElement()
        ..src = streamUrl
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.objectFit = 'contain'
        ..style.border = 'none'
        ..style.display = 'block'
        ..draggable = false;
      
      // Set cache control attributes
      imgElement.setAttribute('cache-control', 'no-cache');
      imgElement.setAttribute('pragma', 'no-cache');
      imgElement.setAttribute('expires', '0');
      
      // Add event listeners
      imgElement.onLoad.listen((event) {
        print('DEBUG: Stream loaded successfully for ${widget.cameraId}');
        if (mounted && _isActive) {
          setState(() {
            _debugInfo = 'SUCCESS: Video stream is active and loading frames';
          });
        }
      });
      
      imgElement.onError.listen((event) {
        print('DEBUG: Stream error for ${widget.cameraId}: $event');
        if (mounted && _isActive) {
          setState(() {
            _debugInfo = 'ERROR: Stream failed to load - $event';
          });
        }
        widget.onError?.call();
      });
      
      imgElement.onAbort.listen((event) {
        print('DEBUG: Stream aborted for ${widget.cameraId}');
        if (mounted && _isActive) {
          setState(() {
            _debugInfo = 'WARNING: Stream was aborted';
          });
        }
      });
      
      // Append img to container
      containerDiv.append(imgElement);
      
      _imageElement = imgElement;
      _containerElement = containerDiv;
      
      // Register the HTML container
      ui_web.platformViewRegistry.registerViewFactory(_elementId!, (int viewId) {
        return containerDiv;
      });
      
      if (mounted && _isActive) {
        setState(() {
          _debugInfo = 'Video element created. Waiting for stream data...';
        });
      }
      
    } catch (e) {
      print('DEBUG: Error creating video element: $e');
      if (mounted && _isActive) {
        setState(() {
          _debugInfo = 'ERROR creating video element: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width ?? 640,
      height: widget.height ?? 480,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Stack(
        children: [
          // Video stream or debug info
          if (_elementId != null && _currentStreamUrl != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: HtmlElementView(viewType: _elementId!),
            )
          else
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const CircularProgressIndicator(color: Colors.white),
                  const SizedBox(height: 16),
                  Text(
                    'Loading camera stream...',
                    style: const TextStyle(color: Colors.white70),
                  ),
                ],
              ),
            ),
          
          // Debug overlay
          Positioned(
            bottom: 8,
            left: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'DEBUG INFO:',
                    style: const TextStyle(
                      color: Colors.yellow,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _debugInfo,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Camera ID: ${widget.cameraId}',
                    style: const TextStyle(
                      color: Colors.grey,
                      fontSize: 9,
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          // Live indicator
          Positioned(
            top: 8,
            left: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 8,
                vertical: 4,
              ),
              decoration: BoxDecoration(
                color: _currentStreamUrl != null ? Colors.red : Colors.grey,
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
                  Text(
                    _currentStreamUrl != null ? 'LIVE' : 'OFFLINE',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

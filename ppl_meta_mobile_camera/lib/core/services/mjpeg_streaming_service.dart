import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;
import '../models/mobile_camera.dart';

/// MJPEG streaming service for mobile camera
class MJPEGStreamingService {
  static MJPEGStreamingService? _instance;
  static MJPEGStreamingService get instance => _instance ??= MJPEGStreamingService._();
  MJPEGStreamingService._();

  HttpServer? _server;
  bool _isStreaming = false;
  StreamingConfig _config = StreamingConfig();
  StreamingStats? _stats;
  
  final List<HttpResponse> _clients = [];
  final StreamController<Uint8List> _frameController = StreamController<Uint8List>.broadcast();
  
  Timer? _statsTimer;
  DateTime? _streamStartTime;
  int _framesSent = 0;
  int _framesDropped = 0;
  int _totalBytesSent = 0;
  final List<double> _fpsHistory = [];
  final List<double> _latencyHistory = [];

  // Getters
  bool get isStreaming => _isStreaming;
  StreamingConfig get config => _config;
  StreamingStats? get stats => _stats;
  int get clientCount => _clients.length;

  /// Start MJPEG streaming server
  Future<bool> startStreaming({
    int port = 8554,
    StreamingConfig? config,
  }) async {
    try {
      if (_isStreaming) {
        print('Streaming already active');
        return true;
      }

      _config = config ?? StreamingConfig();
      print('Starting MJPEG streaming on port $port with config: $_config');

      // Start HTTP server
      _server = await HttpServer.bind(InternetAddress.anyIPv4, port);
      _server!.listen(_handleRequest);

      _isStreaming = true;
      _streamStartTime = DateTime.now();
      _framesSent = 0;
      _framesDropped = 0;
      _totalBytesSent = 0;
      _fpsHistory.clear();
      _latencyHistory.clear();

      // Start statistics tracking
      _startStatsTracking();

      print('MJPEG streaming started on port $port');
      return true;
    } catch (e) {
      print('Error starting MJPEG streaming: $e');
      return false;
    }
  }

  /// Stop MJPEG streaming server
  Future<void> stopStreaming() async {
    try {
      if (!_isStreaming) return;

      print('Stopping MJPEG streaming...');

      // Close all client connections
      for (final client in _clients) {
        try {
          await client.close();
        } catch (e) {
          print('Error closing client connection: $e');
        }
      }
      _clients.clear();

      // Close server
      await _server?.close(force: true);
      _server = null;

      // Stop statistics tracking
      _statsTimer?.cancel();
      _statsTimer = null;

      _isStreaming = false;
      print('MJPEG streaming stopped');
    } catch (e) {
      print('Error stopping MJPEG streaming: $e');
    }
  }

  /// Send a frame to all connected clients
  void sendFrame(CameraImage cameraImage) {
    if (!_isStreaming || _clients.isEmpty) return;

    try {
      final frameStart = DateTime.now();
      
      // Convert CameraImage to JPEG
      final jpegBytes = _convertCameraImageToJpeg(cameraImage);
      if (jpegBytes == null) {
        _framesDropped++;
        return;
      }

      // Create MJPEG frame
      final mjpegFrame = _createMJPEGFrame(jpegBytes);
      
      // Send to all clients
      final disconnectedClients = <HttpResponse>[];
      for (final client in _clients) {
        try {
          client.add(mjpegFrame);
          _framesSent++;
          _totalBytesSent += mjpegFrame.length;
        } catch (e) {
          print('Client disconnected: $e');
          disconnectedClients.add(client);
        }
      }

      // Remove disconnected clients
      for (final client in disconnectedClients) {
        _clients.remove(client);
      }

      // Update performance metrics
      final frameLatency = DateTime.now().difference(frameStart).inMicroseconds / 1000.0;
      _latencyHistory.add(frameLatency);
      if (_latencyHistory.length > 100) {
        _latencyHistory.removeAt(0);
      }

    } catch (e) {
      print('Error sending frame: $e');
      _framesDropped++;
    }
  }

  /// Handle incoming HTTP requests
  void _handleRequest(HttpRequest request) async {
    try {
      final response = request.response;
      final path = request.uri.path;
      
      print('Request from ${request.connectionInfo?.remoteAddress} to path: $path');

      // Only serve MJPEG stream on /stream endpoint
      if (path == '/stream') {
        print('Serving MJPEG stream to client ${request.connectionInfo?.remoteAddress}');

        // Set MJPEG headers
        response.headers.set('Content-Type', 'multipart/x-mixed-replace; boundary=frame');
        response.headers.set('Cache-Control', 'no-cache');
        response.headers.set('Connection', 'close');
        response.headers.set('Access-Control-Allow-Origin', '*');

        // Add client to list
        _clients.add(response);

        // Send initial frame boundary
        response.add('--frame\r\n'.codeUnits);

        // Keep connection alive until client disconnects
        await response.done.catchError((e) {
          print('Client disconnected: $e');
        }).whenComplete(() {
          _clients.remove(response);
        });
      } else {
        // Return 404 for other paths
        print('Path not found: $path');
        response.statusCode = HttpStatus.notFound;
        response.headers.set('Content-Type', 'application/json');
        response.write('{"error": "Path not found. MJPEG stream available at /stream"}');
        await response.close();
      }

    } catch (e) {
      print('Error handling request: $e');
    }
  }

  /// Convert CameraImage to JPEG bytes
  Uint8List? _convertCameraImageToJpeg(CameraImage cameraImage) {
    try {
      // Convert YUV420 to RGB
      final rgb = _convertYUV420ToRGB(cameraImage);
      if (rgb == null) return null;

      // Create image from RGB data
      final image = img.Image.fromBytes(
        width: cameraImage.width,
        height: cameraImage.height,
        bytes: rgb.buffer,
        format: img.Format.uint8,
        numChannels: 3,
      );

      // Resize if needed
      img.Image resizedImage = image;
      if (_config.width != cameraImage.width || _config.height != cameraImage.height) {
        resizedImage = img.copyResize(
          image,
          width: _config.width,
          height: _config.height,
        );
      }

      // Encode as JPEG
      final jpegBytes = img.encodeJpg(resizedImage, quality: _config.quality);
      return Uint8List.fromList(jpegBytes);

    } catch (e) {
      print('Error converting camera image to JPEG: $e');
      return null;
    }
  }

  /// Convert YUV420 camera image to RGB
  Uint8List? _convertYUV420ToRGB(CameraImage image) {
    try {
      const shift = 0xFF;
      final ySize = image.width * image.height;
      final uvSize = image.width * image.height ~/ 4;
      
      final y = image.planes[0].bytes;
      final u = image.planes[1].bytes;
      final v = image.planes[2].bytes;
      
      final rgb = Uint8List(ySize * 3);
      
      for (int i = 0; i < ySize; i++) {
        final yVal = y[i];
        final uVal = u[i ~/ 4] - 128;
        final vVal = v[i ~/ 4] - 128;
        
        // YUV to RGB conversion
        int r = (yVal + 1.402 * vVal).round().clamp(0, 255);
        int g = (yVal - 0.344136 * uVal - 0.714136 * vVal).round().clamp(0, 255);
        int b = (yVal + 1.772 * uVal).round().clamp(0, 255);
        
        rgb[i * 3] = r;
        rgb[i * 3 + 1] = g;
        rgb[i * 3 + 2] = b;
      }
      
      return rgb;
    } catch (e) {
      print('Error converting YUV to RGB: $e');
      return null;
    }
  }

  /// Create MJPEG frame with proper headers
  Uint8List _createMJPEGFrame(Uint8List jpegBytes) {
    final header = 'Content-Type: image/jpeg\r\n'
                  'Content-Length: ${jpegBytes.length}\r\n'
                  '\r\n';
    
    final frameData = <int>[];
    frameData.addAll(header.codeUnits);
    frameData.addAll(jpegBytes);
    frameData.addAll('\r\n--frame\r\n'.codeUnits);
    
    return Uint8List.fromList(frameData);
  }

  /// Start statistics tracking
  void _startStatsTracking() {
    _statsTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      _updateStats();
    });
  }

  /// Update streaming statistics
  void _updateStats() {
    if (_streamStartTime == null) return;

    final now = DateTime.now();
    final uptime = now.difference(_streamStartTime!);
    
    // Calculate FPS
    final currentFps = _framesSent / uptime.inSeconds;
    _fpsHistory.add(currentFps);
    if (_fpsHistory.length > 60) {
      _fpsHistory.removeAt(0);
    }

    final avgFps = _fpsHistory.isNotEmpty 
        ? _fpsHistory.reduce((a, b) => a + b) / _fpsHistory.length 
        : 0.0;

    final avgLatency = _latencyHistory.isNotEmpty
        ? _latencyHistory.reduce((a, b) => a + b) / _latencyHistory.length
        : 0.0;

    _stats = StreamingStats(
      framesSent: _framesSent,
      framesDropped: _framesDropped,
      averageFps: avgFps,
      averageLatency: avgLatency,
      totalBytesSent: _totalBytesSent,
      startTime: _streamStartTime!,
      uptime: uptime,
    );
  }

  /// Update streaming configuration
  void updateConfig(StreamingConfig newConfig) {
    _config = newConfig;
    print('Streaming config updated: $_config');
  }

  /// Get MJPEG stream URL
  String getStreamUrl(String ipAddress, int port) {
    return 'http://$ipAddress:$port/stream';
  }

  /// Reset statistics
  void resetStats() {
    _framesSent = 0;
    _framesDropped = 0;
    _totalBytesSent = 0;
    _fpsHistory.clear();
    _latencyHistory.clear();
    _streamStartTime = DateTime.now();
    _stats = null;
  }
}

import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
// import '../../../services/mobile_streaming_service.dart'; // Unused import removed
import '../../../widgets/streaming_controls_widget.dart';

/// Auto streaming screen for PPL Meta mobile camera streaming
class AutoStreamingScreen extends StatefulWidget {
  final String? rtmpUrl;
  final String? deviceId;
  
  const AutoStreamingScreen({
    Key? key,
    this.rtmpUrl,
    this.deviceId,
  }) : super(key: key);
  
  @override
  State<AutoStreamingScreen> createState() => _AutoStreamingScreenState();
}

class _AutoStreamingScreenState extends State<AutoStreamingScreen>
    with WidgetsBindingObserver {
  
  // Camera and streaming
  CameraController? _cameraController;
  List<CameraDescription> _cameras = [];
  int _selectedCameraIndex = 0;
  bool _isCameraInitialized = false;
  
  // UI state
  bool _isLoading = true;
  String? _errorMessage;
  bool _showControls = true;
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }
  
  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _disposeCamera();
    WakelockPlus.disable();
    super.dispose();
  }
  
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }
    
    if (state == AppLifecycleState.inactive) {
      _disposeCamera();
    } else if (state == AppLifecycleState.resumed) {
      _initializeCamera();
    }
  }
  
  Future<void> _initializeCamera() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
      
      // Get available cameras
      _cameras = await availableCameras();
      
      if (_cameras.isEmpty) {
        setState(() {
          _errorMessage = 'No cameras available';
          _isLoading = false;
        });
        return;
      }
      
      // Initialize with selected camera (default: back camera)
      await _setupCamera(_cameras[_selectedCameraIndex]);
      
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to initialize camera: $e';
        _isLoading = false;
      });
    }
  }
  
  Future<void> _setupCamera(CameraDescription camera) async {
    if (_cameraController != null) {
      await _cameraController!.dispose();
    }
    
    // List of resolution presets to try, in order of preference
    final resolutionPresets = [
      ResolutionPreset.medium,   // Try medium first for better compatibility
      ResolutionPreset.low,      // Fallback to low
      ResolutionPreset.high,     // Try high last
    ];
    
    // Use YUV420 format for better streaming compatibility
    const imageFormat = ImageFormatGroup.yuv420;
    
    for (final preset in resolutionPresets) {
      try {
        _cameraController = CameraController(
          camera,
          preset,
          enableAudio: false,
          imageFormatGroup: imageFormat,
        );
        
        await _cameraController!.initialize();
        
        setState(() {
          _isCameraInitialized = true;
          _isLoading = false;
        });
        
        return; // Success, exit the loop
        
      } catch (e) {
        // Clean up failed attempt
        if (_cameraController != null) {
          try {
            await _cameraController!.dispose();
          } catch (disposeError) {
            // Ignore disposal errors
          }
          _cameraController = null;
        }
        
        // If this was the last preset, show error
        if (preset == resolutionPresets.last) {
          setState(() {
            _errorMessage = 'Camera initialization failed with all resolution settings: $e';
            _isLoading = false;
          });
          return;
        }
        
        // Wait a bit before trying next preset
        await Future.delayed(const Duration(milliseconds: 500));
      }
    }
  }
  
  Future<void> _disposeCamera() async {
    if (_cameraController != null) {
      await _cameraController!.dispose();
      _cameraController = null;
    }
    setState(() {
      _isCameraInitialized = false;
    });
  }
  
  Future<void> _switchCamera() async {
    if (_cameras.length <= 1) return;
    
    setState(() {
      _isLoading = true;
    });
    
    _selectedCameraIndex = (_selectedCameraIndex + 1) % _cameras.length;
    await _setupCamera(_cameras[_selectedCameraIndex]);
  }
  
  void _onStreamingStarted() {
    // Keep screen awake during streaming
    WakelockPlus.enable();
    
    // Show success message
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Live streaming started!'),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
  
  void _onStreamingStopped() {
    // Allow screen to sleep
    WakelockPlus.disable();
    
    // Show info message
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Live streaming stopped'),
        backgroundColor: Colors.blue,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
  
  void _toggleControlsVisibility() {
    setState(() {
      _showControls = !_showControls;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Live Streaming'),
        backgroundColor: Colors.black.withOpacity(0.7),
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(_showControls ? Icons.visibility_off : Icons.visibility),
            onPressed: _toggleControlsVisibility,
            tooltip: _showControls ? 'Hide Controls' : 'Show Controls',
          ),
          if (_cameras.length > 1)
            IconButton(
              icon: const Icon(Icons.flip_camera_ios),
              onPressed: _isLoading ? null : _switchCamera,
              tooltip: 'Switch Camera',
            ),
        ],
      ),
      
      body: Stack(
        children: [
          // Camera Preview
          if (_isLoading)
            const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(color: Colors.white),
                  SizedBox(height: 16),
                  Text(
                    'Initializing camera...',
                    style: TextStyle(color: Colors.white),
                  ),
                ],
              ),
            )
          else if (_errorMessage != null)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.error_outline,
                    color: Colors.red,
                    size: 64,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _errorMessage!,
                    style: const TextStyle(color: Colors.white),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _initializeCamera,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            )
          else if (_isCameraInitialized && _cameraController != null)
            _buildCameraPreview()
          else
            const Center(
              child: Text(
                'Camera not available',
                style: TextStyle(color: Colors.white),
              ),
            ),
          
          // Streaming Controls Overlay
          if (_showControls && _isCameraInitialized && _cameras.isNotEmpty)
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      Colors.black.withOpacity(0.8),
                      Colors.transparent,
                    ],
                  ),
                ),
                child: SafeArea(
                  child: StreamingControlsWidget(
                    camera: _cameras[_selectedCameraIndex],
                    rtmpUrl: widget.rtmpUrl,
                    onStreamingStarted: _onStreamingStarted,
                    onStreamingStopped: _onStreamingStopped,
                  ),
                ),
              ),
            ),
          
          // Camera Info Overlay
          if (_showControls && _isCameraInitialized)
            Positioned(
              top: 16,
              left: 16,
              right: 16,
              child: SafeArea(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.6),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _cameras[_selectedCameraIndex].lensDirection == CameraLensDirection.front
                            ? Icons.camera_front
                            : Icons.camera_rear,
                        color: Colors.white,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _cameras[_selectedCameraIndex].name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Spacer(),
                      if (widget.deviceId != null) ...[
                        const Icon(Icons.devices, color: Colors.white, size: 16),
                        const SizedBox(width: 4),
                        Text(
                          widget.deviceId!,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
  
  Widget _buildCameraPreview() {
    return GestureDetector(
      onTap: _toggleControlsVisibility,
      child: SizedBox.expand(
        child: FittedBox(
          fit: BoxFit.cover,
          child: SizedBox(
            width: _cameraController!.value.previewSize!.height,
            height: _cameraController!.value.previewSize!.width,
            child: CameraPreview(_cameraController!),
          ),
        ),
      ),
    );
  }
}
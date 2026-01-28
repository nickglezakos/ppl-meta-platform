import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

/// Service to detect device orientation changes
/// Orientation data is now sent with each frame instead of separate API calls
class OrientationService {
  static OrientationService? _instance;
  static OrientationService get instance => _instance ??= OrientationService._();
  OrientationService._();

  DeviceOrientation _currentOrientation = DeviceOrientation.portraitUp;
  Timer? _orientationTimer;
  BuildContext? _context;

  DeviceOrientation get currentOrientation => _currentOrientation;

  /// Set the context for orientation detection (call from your main widget)
  void setContext(BuildContext context) {
    _context = context;
    print('📱 [ORIENTATION] Context set for orientation detection');
  }

  /// Start listening for orientation changes
  Future<void> startOrientationDetection() async {
    print('📱 [ORIENTATION] Starting orientation detection...');
    
    // Lock to portrait-only mode for consistent camera streaming
    await SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
    ]);
    print('📱 [ORIENTATION] Locked to portrait-only mode');
    
    // Always use portraitUp since we locked the orientation
    _currentOrientation = DeviceOrientation.portraitUp;
    print('📱 [ORIENTATION] Orientation: $_currentOrientation (locked)');
  }

  /// Get current device orientation from MediaQuery
  Future<DeviceOrientation> _getCurrentOrientation() async {
    try {
      // If we have a context, use MediaQuery to get actual orientation
      if (_context != null && _context!.mounted) {
        final orientation = MediaQuery.of(_context!).orientation;
        final width = MediaQuery.of(_context!).size.width;
        final height = MediaQuery.of(_context!).size.height;
        
        print('📱 [ORIENTATION] MediaQuery: ${orientation.name}, Size: ${width.toInt()}x${height.toInt()}');
        
        // Determine orientation based on screen dimensions
        if (orientation == Orientation.portrait) {
          // For portrait, we could be portraitUp or portraitDown
          // Default to portraitUp as we can't distinguish without sensors
          return DeviceOrientation.portraitUp;
        } else {
          // For landscape, we could be landscapeLeft or landscapeRight
          // Default to landscapeLeft
          return DeviceOrientation.landscapeLeft;
        }
      }
      
      // Fallback
      print('📱 [ORIENTATION] No context available, using fallback');
      return DeviceOrientation.portraitUp;
    } catch (e) {
      print('📱 [ORIENTATION] Error getting orientation: $e');
      return DeviceOrientation.portraitUp;
    }
  }

  /// Stop orientation detection
  void stopOrientationDetection() {
    print('📱 Stopping orientation detection...');
    _orientationTimer?.cancel();
    _orientationTimer = null;
  }

  /// Dispose resources
  void dispose() {
    stopOrientationDetection();
    _currentOrientation = DeviceOrientation.portraitUp;
  }
}

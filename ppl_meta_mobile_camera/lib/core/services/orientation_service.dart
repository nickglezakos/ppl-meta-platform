import 'dart:async';
import 'package:flutter/services.dart';

/// Service to detect device orientation changes
/// Orientation data is now sent with each frame instead of separate API calls
class OrientationService {
  static OrientationService? _instance;
  static OrientationService get instance => _instance ??= OrientationService._();
  OrientationService._();

  DeviceOrientation _currentOrientation = DeviceOrientation.portraitUp;
  Timer? _orientationTimer;

  DeviceOrientation get currentOrientation => _currentOrientation;

  /// Start listening for orientation changes
  Future<void> startOrientationDetection() async {
    print('📱 Starting orientation detection...');
    
    // Get initial orientation
    _currentOrientation = await _getCurrentOrientation();
    print('📱 Initial orientation: $_currentOrientation');
    
    // Poll orientation every 500ms to detect changes
    _orientationTimer = Timer.periodic(const Duration(milliseconds: 500), (timer) async {
      final newOrientation = await _getCurrentOrientation();
      if (newOrientation != _currentOrientation) {
        print('📱 Orientation changed from $_currentOrientation to $newOrientation');
        _currentOrientation = newOrientation;
        // Orientation data will be sent with the next frame automatically
      }
    });
  }

  /// Get current device orientation
  Future<DeviceOrientation> _getCurrentOrientation() async {
    try {
      // For now, we'll use a simple approach. In a real implementation,
      // you might want to use sensors or platform-specific code to detect orientation
      
      // This is a placeholder - in practice, you'd implement proper orientation detection
      // You could use the device's accelerometer or other sensors
      return DeviceOrientation.portraitUp;
    } catch (e) {
      print('📱 Error getting orientation: $e');
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

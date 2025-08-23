import 'package:camera/camera.dart';

/// Interface for camera operations to avoid circular dependencies
abstract class ICameraOperations {
  bool get isInitialized;
  Future<void> startImageStream(Function(CameraImage) onImage);
  Future<void> stopImageStream();
}

/// Singleton interface provider to break circular dependencies
class CameraInterface {
  static ICameraOperations? _instance;
  
  static void setInstance(ICameraOperations instance) {
    _instance = instance;
  }
  
  static ICameraOperations get instance {
    if (_instance == null) {
      throw StateError('CameraInterface not initialized. Call setInstance first.');
    }
    return _instance!;
  }
}

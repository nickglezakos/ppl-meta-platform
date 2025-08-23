/// Result model for camera registration operations
class CameraRegistrationResult {
  final bool isSuccess;
  final String? cameraName;
  final int? cameraId;
  final String? deviceId;
  final String? error;
  final Map<String, dynamic>? data;

  CameraRegistrationResult._({
    required this.isSuccess,
    this.cameraName,
    this.cameraId,
    this.deviceId,
    this.error,
    this.data,
  });

  /// Create a successful registration result
  factory CameraRegistrationResult.success({
    required String cameraName,
    required int cameraId,
    required String deviceId,
    Map<String, dynamic>? data,
  }) {
    return CameraRegistrationResult._(
      isSuccess: true,
      cameraName: cameraName,
      cameraId: cameraId,
      deviceId: deviceId,
      data: data,
    );
  }

  /// Create a failed registration result
  factory CameraRegistrationResult.failure({
    required String error,
    Map<String, dynamic>? data,
  }) {
    return CameraRegistrationResult._(
      isSuccess: false,
      error: error,
      data: data,
    );
  }

  @override
  String toString() {
    if (isSuccess) {
      return 'CameraRegistrationResult.success(cameraName: $cameraName, cameraId: $cameraId, deviceId: $deviceId)';
    } else {
      return 'CameraRegistrationResult.failure(error: $error)';
    }
  }
}

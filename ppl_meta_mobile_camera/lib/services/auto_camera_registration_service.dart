import 'dart:c  /// Auto-register mobile camera with zero user input required
  /// 
  /// Process:
  /// 1. Automatically generate unique camera name from device info
  /// 2. Get device IP for camera registration
  /// 3. Connect to Camera Service using dynamic URL
  /// 4. Register mobile camera with auto-detected specs
  Future<CameraRegistrationResult> autoRegisterCamera({
    required String jwtToken,
    required PlatformServices services,
  }) async {
    try {
      print('📱 Starting automatic camera registration with zero user input...');
      
      // Step 1: Automatically generate unique camera name
      print('🏷️ Step 1: Generating automatic camera name...');
      final cameraName = await _deviceIdentifier.generateCameraName();
      print('✅ Generated camera name: "$cameraName"');
      
      // Step 2: Get device description for logging
      final deviceDescription = await _deviceIdentifier.getDeviceDescription();
      print('📱 Device: $deviceDescription');t 'dart:math';
import 'package:http/http.dart' as http;
import 'package:device_info_plus/device_info_plus.dart';
import 'auto_authentication_service.dart';
import 'multicast_network_discovery.dart';
import 'device_identifier_service.dart';

/// Service for automatic camera registration
class AutoCameraRegistrationService {
  final EnhancedNetworkDiscoveryService _networkService = EnhancedNetworkDiscoveryService();
  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  final DeviceIdentifierService _deviceIdentifier = DeviceIdentifierService();
  
  /// Auto-register mobile camera with minimal user input
  /// 
  /// Process:
  /// 1. Get device IP for camera registration
  /// 2. Connect to Camera Service using dynamic URL
  /// 3. Register mobile camera with auto-detected specs
  Future<CameraRegistrationResult> autoRegisterCamera({
    required String cameraName,
    required String jwtToken,
    required PlatformServices services,
  }) async {
    try {
      print('📱 Starting automatic camera registration...');
      print('🏷️ Camera name: "$cameraName"');
      
      // Step 3: Get device IP for camera registration
      print('🔍 Step 3: Getting device IP for registration...');
      // TODO: Implement device IP detection when needed
      final deviceIP = '192.168.1.100'; // Placeholder for now
      print('📱 Device IP: $deviceIP');
      
      // Step 4: Connect to Camera Service using dynamic URL
      final cameraServiceURL = services.cameraService.endpoint;
      print('📹 Step 4: Connecting to Camera Service...');
      print('🎯 Camera Service URL: $cameraServiceURL');
      
      // Step 5: Get comprehensive device information for registration
      print('📋 Step 5: Gathering comprehensive device information...');
      final deviceRegistrationInfo = await _deviceIdentifier.getDeviceRegistrationInfo();
      final deviceId = _generateDeviceId();
      
      print('📱 Device Registration Info:');
      deviceRegistrationInfo.forEach((key, value) {
        print('   $key: $value');
      });
      print('🆔 Generated Device ID: $deviceId');
      
      // Step 6: Prepare registration data with device info
      final registrationData = {
        'name': cameraName,
        'device_id': deviceId,
        'ip_address': deviceIP,
        'port': 8554, // Standard RTSP port for mobile cameras
        'device_model': deviceRegistrationInfo['device_model'] ?? 'Unknown',
        'device_manufacturer': deviceRegistrationInfo['device_manufacturer'] ?? 'PPL Meta Mobile',
        'device_brand': deviceRegistrationInfo['device_brand'] ?? 'Generic',
        'android_version': deviceRegistrationInfo['android_version'],
        'android_sdk': deviceRegistrationInfo['android_sdk'],
        'app_version': '2.13.1',
        'resolution_width': 1920,
        'resolution_height': 1080,
        'max_fps': 30,
        'supports_audio': false,
        'camera_type': 'MOBILE',
        'is_physical_device': deviceRegistrationInfo['is_physical_device'] ?? true,
        'registration_method': 'automatic_zero_input',
      };
      
      print('📝 Registration data prepared:');
      registrationData.forEach((key, value) {
        print('   $key: $value');
      });
      
      // Step 7: Register with Camera Service
      print('📤 Step 7: Registering with Camera Service...');
      final registrationURL = '$cameraServiceURL/api/v1/cameras/mobile';
      print('🎯 Registration endpoint: $registrationURL');
      
      final response = await http.post(
        Uri.parse(registrationURL),
        headers: {
          'Authorization': 'Bearer $jwtToken',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode(registrationData),
      ).timeout(const Duration(seconds: 15));
      
      print('📥 Registration response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        print('✅ Automatic camera registration successful!');
        print('🎯 Zero user input required - fully automatic workflow completed');
        
        final camera = responseData['camera'];
        final cameraId = camera['id'];
        final registeredDeviceId = camera['device_id'];
        
        print('📄 Automatic registration details:');
        print('   Generated Camera Name: ${camera['name']}');
        print('   Camera ID: $cameraId');
        print('   Device ID: $registeredDeviceId');
        print('   Status: ${camera['status']}');
        print('   Connection String: ${camera['connection_string']}');
        print('   Registration Method: Automatic (Zero Input)');
        
        return CameraRegistrationResult.success(
          cameraId: cameraId,
          deviceId: registeredDeviceId,
          cameraName: camera['name'],
          status: camera['status'],
          connectionString: camera['connection_string'],
          mediaServiceURL: services.mediaService.endpoint,
        );
      } else {
        final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
        throw CameraRegistrationException(
          'Registration failed with status ${response.statusCode}: $errorBody'
        );
      }
      
    } catch (e) {
      print('💥 Automatic camera registration exception: $e');
      if (e is CameraRegistrationException) rethrow;
      throw CameraRegistrationException('Automatic camera registration failed: $e');
    }
  }
  
  /// Generate unique device ID for camera registration
  String _generateDeviceId() {
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final random = Random().nextInt(99999999);
    return 'mobile_${random.toString().padLeft(8, '0')}_$timestamp';
  }
}

/// Camera registration result container
class CameraRegistrationResult {
  final bool success;
  final int? cameraId;
  final String? deviceId;
  final String? cameraName;
  final String? status;
  final String? connectionString;
  final String? mediaServiceURL;
  final String? error;
  
  CameraRegistrationResult._({
    required this.success,
    this.cameraId,
    this.deviceId,
    this.cameraName,
    this.status,
    this.connectionString,
    this.mediaServiceURL,
    this.error,
  });
  
  factory CameraRegistrationResult.success({
    required int cameraId,
    required String deviceId,
    required String cameraName,
    required String status,
    required String connectionString,
    required String mediaServiceURL,
  }) => CameraRegistrationResult._(
    success: true,
    cameraId: cameraId,
    deviceId: deviceId,
    cameraName: cameraName,
    status: status,
    connectionString: connectionString,
    mediaServiceURL: mediaServiceURL,
  );
  
  factory CameraRegistrationResult.failure(String error) => CameraRegistrationResult._(
    success: false,
    error: error,
  );
}

/// Camera registration exception
class CameraRegistrationException implements Exception {
  final String message;
  CameraRegistrationException(this.message);
  
  @override
  String toString() => 'CameraRegistrationException: $message';
}

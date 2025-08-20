import 'dart:convert';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:device_info_plus/device_info_plus.dart';
import 'auto_authentication_service.dart';
import 'multicast_network_discovery.dart';

/// Service for automatic camera registration
class AutoCameraRegistrationService {
  final EnhancedNetworkDiscoveryService _networkService = EnhancedNetworkDiscoveryService();
  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  
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
      
      // Step 1: Get device IP for camera registration
      print('🔍 Step 1: Getting device IP for registration...');
      // TODO: Implement device IP detection when needed
      final deviceIP = '192.168.1.100'; // Placeholder for now
      print('📱 Device IP: $deviceIP');
      
      // Step 2: Connect to Camera Service using dynamic URL
      final cameraServiceURL = services.cameraService.endpoint;
      print('📹 Step 2: Connecting to Camera Service...');
      print('🎯 Camera Service URL: $cameraServiceURL');
      
      // Step 3: Get device information for registration
      print('📋 Step 3: Gathering device information...');
      final deviceModel = await _getDeviceModel();
      final deviceId = _generateDeviceId();
      
      print('📱 Device Model: $deviceModel');
      print('🆔 Device ID: $deviceId');
      
      // Step 4: Prepare registration data
      final registrationData = {
        'name': cameraName,
        'device_id': deviceId,  // Add the missing device_id field
        'ip_address': deviceIP,
        'port': 8554, // Standard RTSP port for mobile cameras
        'device_model': deviceModel,
        'device_manufacturer': 'PPL Meta Mobile',
        'app_version': '2.13.1',
        'resolution_width': 1920,
        'resolution_height': 1080,
        'max_fps': 30,
        'supports_audio': false,
        'camera_type': 'MOBILE',
      };
      
      print('📝 Registration data prepared:');
      registrationData.forEach((key, value) {
        print('   $key: $value');
      });
      
      // Step 5: Register with Camera Service
      print('📤 Step 4: Registering with Camera Service...');
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
        print('✅ Camera registration successful!');
        
        final camera = responseData['camera'];
        final cameraId = camera['id'];
        final registeredDeviceId = camera['device_id'];
        
        print('📄 Registration details:');
        print('   Camera ID: $cameraId');
        print('   Device ID: $registeredDeviceId');
        print('   Camera Name: ${camera['name']}');
        print('   Status: ${camera['status']}');
        print('   Connection String: ${camera['connection_string']}');
        
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
      print('💥 Camera registration exception: $e');
      if (e is CameraRegistrationException) rethrow;
      throw CameraRegistrationException('Camera registration failed: $e');
    }
  }
  
  /// Get device model information
  Future<String> _getDeviceModel() async {
    try {
      final androidInfo = await _deviceInfo.androidInfo;
      return '${androidInfo.manufacturer} ${androidInfo.model}';
    } catch (e) {
      print('⚠️ Could not get device model: $e');
      return 'Unknown Android Device';
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

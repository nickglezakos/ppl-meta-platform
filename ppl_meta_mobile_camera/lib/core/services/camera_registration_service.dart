import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:device_info_plus/device_info_plus.dart';
import 'package:network_info_plus/network_info_plus.dart';
import '../models/mobile_camera.dart';
import 'authentication_service.dart';

/// Service for registering mobile device as camera with PPL Meta Platform
class CameraRegistrationService {
  static CameraRegistrationService? _instance;
  static CameraRegistrationService get instance => _instance ??= CameraRegistrationService._();
  CameraRegistrationService._();

  String? _platformBaseUrl;
  String? _registeredDeviceId;
  bool _isRegistered = false;

  // Getters
  String? get platformBaseUrl => _platformBaseUrl;
  String? get registeredDeviceId => _registeredDeviceId;
  bool get isRegistered => _isRegistered;

  /// Set the platform base URL (e.g., "http://192.168.1.100:8005")
  void setPlatformUrl(String baseUrl) {
    _platformBaseUrl = baseUrl.replaceAll(RegExp(r'/+$'), ''); // Remove trailing slashes
  }

  /// Register this mobile device as a camera with the PPL Meta Platform
  Future<RegistrationResult> registerMobileCamera({
    String? customName,
    int streamingPort = 8554,
    int resolutionWidth = 1920,
    int resolutionHeight = 1080,
    int maxFps = 30,
    bool supportsAudio = false,
  }) async {
    try {
      if (_platformBaseUrl == null) {
        return RegistrationResult.failure('Platform URL not set. Call setPlatformUrl() first.');
      }

      // Get device information
      final deviceInfo = await _getDeviceInfo();
      final ipAddress = await _getLocalIPAddress();
      
      if (ipAddress == null) {
        return RegistrationResult.failure('Could not determine local IP address');
      }

      // Generate device ID
      final deviceId = 'mobile_${deviceInfo['id']}';
      
      // Prepare registration data
      final registrationData = {
        'name': customName ?? '${deviceInfo['manufacturer']} ${deviceInfo['model']} Camera',
        'device_id': deviceId,
        'ip_address': ipAddress,
        'port': streamingPort,
        'device_model': deviceInfo['model'],
        'device_manufacturer': deviceInfo['manufacturer'],
        'app_version': '2.13.0', // Current app version
        'resolution_width': resolutionWidth,
        'resolution_height': resolutionHeight,
        'max_fps': maxFps,
        'supports_audio': supportsAudio,
      };

      print('Registering mobile camera with data: $registrationData');

      // Get authentication token
      final token = await AuthenticationService.instance.getValidToken();
      if (token == null) {
        return RegistrationResult.failure('Authentication token not available');
      }

      // Make registration request
      final response = await http.post(
        Uri.parse('$_platformBaseUrl/api/v1/cameras/mobile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: json.encode(registrationData),
      ).timeout(const Duration(seconds: 30));

      print('Registration response status: ${response.statusCode}');
      print('Registration response body: ${response.body}');

      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = json.decode(response.body);
        
        // Store registration info
        _registeredDeviceId = deviceId;
        _isRegistered = true;

        return RegistrationResult.success(
          deviceId: deviceId,
          cameraId: responseData['camera']['id']?.toString(),
          message: responseData['message'] ?? 'Registration successful',
          cameraInfo: MobileCameraInfo.fromRegistrationResponse(responseData['camera']),
        );
      } else {
        final errorData = json.decode(response.body);
        return RegistrationResult.failure(
          errorData['detail'] ?? 'Registration failed with status ${response.statusCode}',
        );
      }
    } catch (e) {
      print('Error during camera registration: $e');
      return RegistrationResult.failure('Registration error: $e');
    }
  }

  /// Update mobile camera status on the platform
  Future<UpdateResult> updateCameraStatus({
    required String status,
    int? resolutionWidth,
    int? resolutionHeight,
    int? currentFps,
    int? batteryLevel,
  }) async {
    try {
      if (!_isRegistered || _registeredDeviceId == null) {
        return UpdateResult.failure('Camera not registered');
      }

      final token = await AuthenticationService.instance.getValidToken();
      if (token == null) {
        return UpdateResult.failure('Authentication token not available');
      }

      final updateData = <String, dynamic>{
        'status': status,
      };

      if (resolutionWidth != null) updateData['resolution_width'] = resolutionWidth;
      if (resolutionHeight != null) updateData['resolution_height'] = resolutionHeight;
      if (currentFps != null) updateData['current_fps'] = currentFps;
      if (batteryLevel != null) updateData['battery_level'] = batteryLevel;

      final response = await http.put(
        Uri.parse('$_platformBaseUrl/api/v1/cameras/mobile/$_registeredDeviceId'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: json.encode(updateData),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final responseData = json.decode(response.body);
        return UpdateResult.success(responseData['message'] ?? 'Update successful');
      } else {
        final errorData = json.decode(response.body);
        return UpdateResult.failure(
          errorData['detail'] ?? 'Update failed with status ${response.statusCode}',
        );
      }
    } catch (e) {
      print('Error updating camera status: $e');
      return UpdateResult.failure('Update error: $e');
    }
  }

  /// Unregister the mobile camera from the platform
  Future<bool> unregisterCamera() async {
    try {
      if (!_isRegistered || _registeredDeviceId == null) {
        return true; // Already unregistered
      }

      final token = await AuthenticationService.instance.getValidToken();
      if (token == null) {
        print('No auth token available for unregistration');
        return false;
      }

      final response = await http.delete(
        Uri.parse('$_platformBaseUrl/api/v1/cameras/mobile/$_registeredDeviceId'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200 || response.statusCode == 404) {
        // Success or already deleted
        _isRegistered = false;
        _registeredDeviceId = null;
        return true;
      } else {
        print('Failed to unregister camera: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('Error during camera unregistration: $e');
      return false;
    }
  }

  /// Get device information for registration
  Future<Map<String, String>> _getDeviceInfo() async {
    final deviceInfo = DeviceInfoPlugin();
    
    if (Platform.isAndroid) {
      final androidInfo = await deviceInfo.androidInfo;
      return {
        'id': androidInfo.id,
        'manufacturer': androidInfo.manufacturer,
        'model': androidInfo.model,
        'brand': androidInfo.brand,
        'device': androidInfo.device,
        'hardware': androidInfo.hardware,
        'version': androidInfo.version.release,
      };
    } else if (Platform.isIOS) {
      final iosInfo = await deviceInfo.iosInfo;
      return {
        'id': iosInfo.identifierForVendor ?? 'unknown',
        'manufacturer': 'Apple',
        'model': iosInfo.model,
        'brand': 'Apple',
        'device': iosInfo.name,
        'hardware': iosInfo.utsname.machine,
        'version': iosInfo.systemVersion,
      };
    } else {
      return {
        'id': 'unknown',
        'manufacturer': 'Unknown',
        'model': 'Unknown',
        'brand': 'Unknown',
        'device': 'Unknown',
        'hardware': 'Unknown',
        'version': 'Unknown',
      };
    }
  }

  /// Get local IP address
  Future<String?> _getLocalIPAddress() async {
    try {
      final info = NetworkInfo();
      final wifiIP = await info.getWifiIP();
      
      if (wifiIP != null && wifiIP.isNotEmpty) {
        return wifiIP;
      }

      // Fallback: Try to get IP from network interfaces
      for (final interface in await NetworkInterface.list()) {
        for (final addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            return addr.address;
          }
        }
      }

      return null;
    } catch (e) {
      print('Error getting local IP address: $e');
      return null;
    }
  }

  /// Reset registration state (for testing/debugging)
  void resetRegistration() {
    _isRegistered = false;
    _registeredDeviceId = null;
  }
}

/// Result of camera registration attempt
class RegistrationResult {
  final bool success;
  final String message;
  final String? deviceId;
  final String? cameraId;
  final MobileCameraInfo? cameraInfo;

  RegistrationResult._({
    required this.success,
    required this.message,
    this.deviceId,
    this.cameraId,
    this.cameraInfo,
  });

  factory RegistrationResult.success({
    required String deviceId,
    String? cameraId,
    required String message,
    MobileCameraInfo? cameraInfo,
  }) {
    return RegistrationResult._(
      success: true,
      message: message,
      deviceId: deviceId,
      cameraId: cameraId,
      cameraInfo: cameraInfo,
    );
  }

  factory RegistrationResult.failure(String message) {
    return RegistrationResult._(
      success: false,
      message: message,
    );
  }
}

/// Result of camera status update
class UpdateResult {
  final bool success;
  final String message;

  UpdateResult._({required this.success, required this.message});

  factory UpdateResult.success(String message) {
    return UpdateResult._(success: true, message: message);
  }

  factory UpdateResult.failure(String message) {
    return UpdateResult._(success: false, message: message);
  }
}

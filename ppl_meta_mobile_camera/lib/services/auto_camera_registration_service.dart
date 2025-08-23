import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'device_identifier_service.dart';
import 'app_logger.dart';
import '../models/camera_registration_result.dart';
import '../models/platform_services.dart';

/// Service for automatic camera registration without user input
/// Handles device identification, name generation, and registration
class AutoCameraRegistrationService {
  final DeviceIdentifierService _deviceService = DeviceIdentifierService();
  
  /// Register camera automatically using device information
  /// Returns CameraRegistrationResult with camera ID and device ID
  Future<CameraRegistrationResult> autoRegisterCamera(String jwtToken) async {
    AutoRegistrationLogger.step('START', 'Beginning automatic camera registration');
    
    try {
      // Load platform services configuration
      final prefs = await SharedPreferences.getInstance();
      final servicesJson = prefs.getString('ppl_meta_platform_services');
      if (servicesJson == null) {
        AutoRegistrationLogger.error('No platform services data found');
        AutoRegistrationLogger.debug('Checking SharedPreferences keys for debugging...');
        
        // Debug: List all available keys
        final allKeys = prefs.getKeys();
        AutoRegistrationLogger.debug('Available SharedPreferences keys: ${allKeys.toList()}');
        
        throw Exception('Platform services not available - please login first');
      }
      
      final services = PlatformServices.fromJson(json.decode(servicesJson));
      AutoRegistrationLogger.debug('JWT Token length: ${jwtToken.length}');
      AutoRegistrationLogger.debug('Camera service endpoint: ${services.cameraService.endpoint}');
      AutoRegistrationLogger.debug('Media service endpoint: ${services.mediaService.endpoint}');
      AutoRegistrationLogger.debug('Raw services JSON: $servicesJson');
      
      // Step 1: Generate automatic camera name
      AutoRegistrationLogger.step('1', 'Generating camera name');
      final cameraName = await _deviceService.generateCameraName();
      AutoRegistrationLogger.success('Auto-generated camera name: $cameraName');
      
      // Step 2: Get device information
      AutoRegistrationLogger.step('2', 'Collecting device information');
      final deviceInfo = await _deviceService.getDeviceRegistrationInfo();
      AutoRegistrationLogger.success('Device specs collected automatically');
      AutoRegistrationLogger.deviceInfo('Manufacturer', deviceInfo['manufacturer']);
      AutoRegistrationLogger.deviceInfo('Model', deviceInfo['model']);
      AutoRegistrationLogger.deviceInfo('OS Version', deviceInfo['os_version']);
      
      // Step 3: Get device IP
      AutoRegistrationLogger.step('3', 'Getting device IP');
      final deviceIP = await _getDeviceIP();
      AutoRegistrationLogger.success('Device IP: $deviceIP');
      
      // Step 4: Prepare registration data
      AutoRegistrationLogger.step('4', 'Preparing registration payload');
      
      final requestBody = {
        'name': cameraName,
        'device_id': deviceInfo['device_id'] ?? 'unknown',
        'ip_address': deviceIP,
        'port': 8554, // Default RTSP port for mobile cameras
        'device_model': deviceInfo['model'] ?? 'Mobile Camera',
        'device_manufacturer': deviceInfo['manufacturer'] ?? 'PPL Meta Mobile',
        'app_version': '1.0.0',
      };
      AutoRegistrationLogger.success('Mobile camera registration payload prepared');
      AutoRegistrationLogger.debug('Payload keys: ${requestBody.keys.toList()}');
      
      // Step 5: Send registration request
      AutoRegistrationLogger.step('5', 'Sending registration request');
      
      // Use nginx proxy URL for mobile camera registration
      String cameraServiceUrl = 'http://localhost/cameras';
      
      final response = await http.post(
        Uri.parse('$cameraServiceUrl/api/v1/cameras/mobile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $jwtToken',
        },
        body: json.encode(requestBody),
      );
      
      AutoRegistrationLogger.apiCall('POST', '$cameraServiceUrl/api/v1/cameras/mobile', response.statusCode);
      AutoRegistrationLogger.debug('Response body: ${response.body}');
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = json.decode(response.body);
        final cameraData = responseData['camera'];
        final cameraId = cameraData['id']?.toString();
        final deviceId = cameraData['device_id']?.toString();
        
        if (cameraId != null && deviceId != null) {
          AutoRegistrationLogger.success('Mobile camera registered successfully!');
          AutoRegistrationLogger.deviceInfo('Camera ID', cameraId);
          AutoRegistrationLogger.deviceInfo('Device ID', deviceId);
          AutoRegistrationLogger.deviceInfo('Camera Type', cameraData['camera_type']);
          AutoRegistrationLogger.deviceInfo('Status', cameraData['status']);
          AutoRegistrationLogger.deviceInfo('Connection String', cameraData['connection_string']);
          
          return CameraRegistrationResult.success(
            cameraId: int.parse(cameraId),
            cameraName: cameraName,
            deviceId: deviceId,
          );
        } else {
          AutoRegistrationLogger.error('Registration failed: Missing camera ID or device ID in response');
          final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
          AutoRegistrationLogger.debug('Error details: $errorBody');
          
          return CameraRegistrationResult.failure(
            error: 'Registration failed: $errorBody',
          );
        }
      } else {
        AutoRegistrationLogger.error('Registration failed: ${response.statusCode}');
        final errorBody = response.body.isNotEmpty ? response.body : 'Unknown error';
        AutoRegistrationLogger.debug('Error details: $errorBody');
        
        return CameraRegistrationResult.failure(
          error: 'HTTP ${response.statusCode}: $errorBody',
        );
      }
      
    } catch (e, stackTrace) {
      AutoRegistrationLogger.error('Exception during registration: ${e.toString()}', e);
      return CameraRegistrationResult.failure(
        error: 'Registration exception: $e',
      );
    }
  }
  
  /// Get device IP address for registration
  Future<String> _getDeviceIP() async {
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
      
      // Final fallback
      return '192.168.1.100';
    } catch (e) {
      AutoRegistrationLogger.error('Error getting device IP: $e');
      return '192.168.1.100'; // Fallback IP
    }
  }
}

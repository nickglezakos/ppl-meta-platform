import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'device_identifier_service.dart';
import 'app_logger.dart';
import 'discovery_config_service.dart';
import '../models/camera_registration_result.dart';
import '../models/platform_services.dart';

/// Service for automatic camera registration without user input
/// Handles device identification, name generation, and registration
class AutoCameraRegistrationService {
  final DeviceIdentifierService _deviceService = DeviceIdentifierService();
  final DiscoveryConfigService _discoveryConfig = DiscoveryConfigService.instance;

  /// Get cameras service URL from discovery service or fallback to direct URL
  Future<String?> _getCamerasServiceUrl() async {
    try {
      // First try discovery service
      final camerasService = await _discoveryConfig.findService('ppl-meta-cameras');
      if (camerasService != null) {
        AutoRegistrationLogger.debug('Found cameras service at: ${camerasService.baseUrl}');
        return camerasService.baseUrl;
      }
      
      AutoRegistrationLogger.warning('Cameras service not found in discovery service - trying fallback');
      
      // Fallback: try to get direct URL from platform services data
      final prefs = await SharedPreferences.getInstance();
      final servicesJson = prefs.getString('ppl_meta_platform_services');
      if (servicesJson != null) {
        final platformData = json.decode(servicesJson);
        final cameraEndpoints = platformData['camera_endpoints'] as Map<String, dynamic>?;
        if (cameraEndpoints != null && cameraEndpoints['register'] != null) {
          // Extract base URL from register endpoint
          final registerUrl = cameraEndpoints['register'] as String;
          final uri = Uri.parse(registerUrl);
          final baseUrl = '${uri.scheme}://${uri.host}:${uri.port}';
          AutoRegistrationLogger.debug('Using fallback cameras service URL: $baseUrl');
          return baseUrl;
        }
      }
      
      AutoRegistrationLogger.error('No cameras service URL available');
      return null;
    } catch (e) {
      AutoRegistrationLogger.error('Failed to find cameras service: $e');
      
      // Last resort fallback: try to construct from platform IP
      try {
        final prefs = await SharedPreferences.getInstance();
        final servicesJson = prefs.getString('ppl_meta_platform_services');
        if (servicesJson != null) {
          final platformData = json.decode(servicesJson);
          final connectivity = platformData['connectivity'] as Map<String, dynamic>?;
          if (connectivity != null && connectivity['local_ip'] != null) {
            final platformIP = connectivity['local_ip'] as String;
            final fallbackUrl = 'http://$platformIP:8005';
            AutoRegistrationLogger.debug('Using constructed fallback URL: $fallbackUrl');
            return fallbackUrl;
          }
        }
      } catch (fallbackError) {
        AutoRegistrationLogger.error('Fallback URL construction failed: $fallbackError');
      }
      
      return null;
    }
  }
  
  /// Check if camera with device ID already exists
  Future<Map<String, dynamic>?> checkExistingCamera(String jwtToken) async {
    try {
      // Get cameras service URL from discovery service first (no platform dependencies)
      final baseUrl = await _getCamerasServiceUrl();
      if (baseUrl == null) {
        AutoRegistrationLogger.warning('Cameras service URL not available - skipping existing camera check');
        return null; // Don't throw exception, just return null to continue with registration
      }
      
      // Try to get device info, but handle platform binding errors gracefully
      Map<String, dynamic> deviceInfo;
      try {
        deviceInfo = await _deviceService.getDeviceRegistrationInfo();
      } catch (e) {
        if (e.toString().contains('Binding has not yet been initialized') || 
            e.toString().contains('ServicesBinding')) {
          AutoRegistrationLogger.warning('Platform services not yet available for existing camera check');
          return null; // Skip check and proceed with registration
        }
        rethrow; // Re-throw other errors
      }
      
      final baseDeviceId = deviceInfo['device_id'] ?? 'unknown';
      final deviceId = 'mobile_$baseDeviceId'; // Add mobile_ prefix for consistency
      
      AutoRegistrationLogger.step('CHECK', 'Looking for existing camera with device ID: $deviceId');
      
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/cameras/mobile'),
        headers: {
          'Authorization': 'Bearer $jwtToken',
          'Accept': 'application/json',
        },
      );
      
      if (response.statusCode == 200) {
        final responseData = json.decode(response.body);
        final mobileCameras = responseData as List;
        
        // Find camera with matching device ID
        for (final camera in mobileCameras) {
          if (camera['device_id'] == deviceId) {
            AutoRegistrationLogger.success('Found existing camera: ${camera['name']} (ID: ${camera['id']})');
            return camera;
          }
        }
        
        AutoRegistrationLogger.debug('No existing camera found for device ID: $deviceId');
        return null;
      } else {
        AutoRegistrationLogger.warning('Failed to check existing cameras: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      AutoRegistrationLogger.warning('Error checking existing camera - will proceed with registration: $e');
      return null; // Don't fail the whole registration process
    }
  }
  
    /// Create streaming session URL for the registered camera
  Future<String?> createStreamingSessionUrl(String cameraId) async {
    try {
      final camerasUrl = await _getCamerasServiceUrl();
      if (camerasUrl == null) {
        AutoRegistrationLogger.error('Cameras service URL not available');
        return null;
      }

      return '$camerasUrl/api/v1/cameras/mobile/$cameraId/stream';
    } catch (e) {
      AutoRegistrationLogger.error('Failed to create streaming session URL: $e');
      return null;
    }
  }
  
  /// Register camera automatically using device information
  /// Returns CameraRegistrationResult with camera ID and device ID
  Future<CameraRegistrationResult> autoRegisterCamera(String jwtToken) async {
    AutoRegistrationLogger.step('START', 'Beginning automatic camera registration');
    
    try {
      // Step 0: Check for existing camera registration
      AutoRegistrationLogger.step('0', 'Checking for existing camera registration');
      final existingCamera = await checkExistingCamera(jwtToken);
      
      if (existingCamera != null) {
        // Camera already exists, return success with existing camera info
        AutoRegistrationLogger.success('Using existing camera registration');
        AutoRegistrationLogger.deviceInfo('Camera ID', existingCamera['id'].toString());
        AutoRegistrationLogger.deviceInfo('Camera Name', existingCamera['name']);
        AutoRegistrationLogger.deviceInfo('Device ID', existingCamera['device_id']);
        
        return CameraRegistrationResult.success(
          cameraId: existingCamera['id'],
          cameraName: existingCamera['name'],
          deviceId: existingCamera['device_id'],
        );
      }
      
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
      String cameraName;
      try {
        cameraName = await _deviceService.generateCameraName();
        AutoRegistrationLogger.success('Auto-generated camera name: $cameraName');
      } catch (e) {
        if (e.toString().contains('Binding has not yet been initialized') || 
            e.toString().contains('ServicesBinding')) {
          AutoRegistrationLogger.error('Platform services not available for camera name generation');
          return CameraRegistrationResult.failure(
            error: 'Platform services not initialized. Please restart the app.',
          );
        }
        rethrow;
      }
      
      // Step 2: Get device information
      AutoRegistrationLogger.step('2', 'Collecting device information');
      Map<String, dynamic> deviceInfo;
      try {
        deviceInfo = await _deviceService.getDeviceRegistrationInfo();
        AutoRegistrationLogger.success('Device specs collected automatically');
        AutoRegistrationLogger.deviceInfo('Manufacturer', deviceInfo['manufacturer']);
        AutoRegistrationLogger.deviceInfo('Model', deviceInfo['model']);
        AutoRegistrationLogger.deviceInfo('OS Version', deviceInfo['os_version']);
      } catch (e) {
        if (e.toString().contains('Binding has not yet been initialized') || 
            e.toString().contains('ServicesBinding')) {
          AutoRegistrationLogger.error('Platform services not available for device information');
          return CameraRegistrationResult.failure(
            error: 'Platform services not initialized. Please restart the app.',
          );
        }
        rethrow;
      }
      
      // Step 3: Get device IP
      AutoRegistrationLogger.step('3', 'Getting device IP');
      String deviceIP;
      try {
        deviceIP = await _getDeviceIP();
        AutoRegistrationLogger.success('Device IP: $deviceIP');
      } catch (e) {
        if (e.toString().contains('Binding has not yet been initialized') || 
            e.toString().contains('ServicesBinding')) {
          AutoRegistrationLogger.error('Platform services not available for IP detection');
          return CameraRegistrationResult.failure(
            error: 'Platform services not initialized. Please restart the app.',
          );
        }
        rethrow;
      }
      
      // Step 4: Prepare registration data
      AutoRegistrationLogger.step('4', 'Preparing registration payload');
      
      final baseDeviceId = deviceInfo['device_id'] ?? 'unknown';
      final deviceId = 'mobile_$baseDeviceId'; // Add mobile_ prefix for consistency
      
      final requestBody = {
        'name': cameraName,
        'device_id': deviceId,
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
      
      // Get cameras service URL from discovery service
      final baseUrl = await _getCamerasServiceUrl();
      if (baseUrl == null) {
        throw Exception('Cameras service not available');
      }
      AutoRegistrationLogger.debug('Using cameras service base URL: $baseUrl');
      
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/cameras/mobile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $jwtToken',
        },
        body: json.encode(requestBody),
      );
      
      AutoRegistrationLogger.apiCall('POST', '$baseUrl/api/v1/cameras/mobile', response.statusCode);
      AutoRegistrationLogger.debug('Response body: ${response.body}');
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        AutoRegistrationLogger.success('Registration API call successful (${response.statusCode})');
        
        final responseData = json.decode(response.body);
        AutoRegistrationLogger.debug('Full response data: $responseData');
        
        final cameraData = responseData['camera'];
        if (cameraData == null) {
          AutoRegistrationLogger.error('No camera data in response');
          return CameraRegistrationResult.failure(
            error: 'No camera data in response: ${response.body}',
          );
        }
        
        AutoRegistrationLogger.debug('Camera data: $cameraData');
        
        // Extract camera information - these should always be present
        final cameraId = cameraData['id'];
        final deviceId = cameraData['device_id'];
        final cameraNameFromResponse = cameraData['name'];
        
        AutoRegistrationLogger.debug('Raw values - ID: $cameraId, DeviceID: $deviceId, Name: $cameraNameFromResponse');
        
        if (cameraId != null && deviceId != null) {
          AutoRegistrationLogger.success('Mobile camera operation successful!');
          AutoRegistrationLogger.deviceInfo('Camera ID', cameraId.toString());
          AutoRegistrationLogger.deviceInfo('Device ID', deviceId.toString());
          AutoRegistrationLogger.deviceInfo('Camera Name', cameraNameFromResponse?.toString() ?? cameraName);
          AutoRegistrationLogger.deviceInfo('Camera Type', cameraData['camera_type']);
          AutoRegistrationLogger.deviceInfo('Status', cameraData['status']);
          AutoRegistrationLogger.deviceInfo('Connection String', cameraData['connection_string']);
          
          try {
            final successResult = CameraRegistrationResult.success(
              cameraId: cameraId is int ? cameraId : int.tryParse(cameraId.toString()) ?? 0,
              cameraName: cameraNameFromResponse?.toString() ?? cameraName,
              deviceId: deviceId.toString(),
            );
            
            AutoRegistrationLogger.debug('Created success result: ${successResult.toString()}');
            AutoRegistrationLogger.debug('Success result isSuccess: ${successResult.isSuccess}');
            
            return successResult;
          } catch (e) {
            AutoRegistrationLogger.error('Exception creating success result: $e');
            return CameraRegistrationResult.failure(
              error: 'Failed to create success result: $e',
            );
          }
        } else {
          AutoRegistrationLogger.error('Missing required camera data in response');
          AutoRegistrationLogger.error('Camera ID: $cameraId, Device ID: $deviceId');
          AutoRegistrationLogger.error('Full camera data: $cameraData');
          
          return CameraRegistrationResult.failure(
            error: 'Invalid camera data in response - missing ID or device_id',
          );
        }
      } else if (response.statusCode == 400) {
        // Handle "already registered" case
        final errorBody = response.body.isNotEmpty ? response.body : '{}';
        try {
          final errorData = json.decode(errorBody);
          final errorDetail = errorData['detail'] ?? '';
          
          if (errorDetail.contains('already registered')) {
            AutoRegistrationLogger.success('Camera already registered - continuing with existing registration');
            
            // Return success since camera is already registered
            // The device ID from the request is what we'll use
            return CameraRegistrationResult.success(
              cameraId: 0, // We don't have the actual ID, but that's okay for existing cameras
              cameraName: cameraName,
              deviceId: deviceId, // Use the consistent device ID with mobile_ prefix
            );
          }
        } catch (e) {
          AutoRegistrationLogger.debug('Could not parse error response: $e');
        }
        
        AutoRegistrationLogger.error('Registration failed: ${response.statusCode}');
        AutoRegistrationLogger.debug('Error details: $errorBody');
        
        return CameraRegistrationResult.failure(
          error: 'HTTP ${response.statusCode}: $errorBody',
        );
      } else {
        AutoRegistrationLogger.error('Registration failed: ${response.statusCode}');
        final errorBody = response.body.isNotEmpty ? response.body : 'Unknown error';
        AutoRegistrationLogger.debug('Error details: $errorBody');
        
        return CameraRegistrationResult.failure(
          error: 'HTTP ${response.statusCode}: $errorBody',
        );
      }
      
    } catch (e) {
      AutoRegistrationLogger.error('Exception during registration: ${e.toString()}', e);
      AutoRegistrationLogger.error('Exception type: ${e.runtimeType}');
      AutoRegistrationLogger.error('Stack trace: ${StackTrace.current}');
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
      
      // Final fallback - updated for current network
      return '192.168.129.100';
    } catch (e) {
      AutoRegistrationLogger.error('Error getting device IP: $e');
      return '192.168.129.100'; // Fallback IP - updated for current network
    }
  }
}

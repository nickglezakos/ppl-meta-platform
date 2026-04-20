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

  /// Get cameras service URL, preferring the gateway (port 8080) to ensure
  /// connectivity on mobile hotspots where port 8005 may not be reachable.
  Future<String?> _getCamerasServiceUrl() async {
    try {
      // Prefer gateway URL derived from the node server URL the user connected to.
      // The gateway proxies /api/v1/cameras/* routes to the cameras service.
      final prefs = await SharedPreferences.getInstance();
      final serverConfig = prefs.getString('ppl_meta_server_config');
      if (serverConfig != null) {
        final uri = Uri.tryParse(serverConfig);
        if (uri != null) {
          final gatewayUrl = 'http://${uri.host}:8080';
          AutoRegistrationLogger.debug('Using gateway URL for cameras: $gatewayUrl');
          return gatewayUrl;
        }
      }

      // Fallback: try discovery service
      final camerasService = await _discoveryConfig.findService('ppl-meta-cameras');
      if (camerasService != null) {
        AutoRegistrationLogger.debug('Found cameras service at: ${camerasService.baseUrl}');
        return camerasService.baseUrl;
      }
      
      AutoRegistrationLogger.warning('Cameras service not found in discovery service - trying fallback');
      
      // Fallback: try to get direct URL from platform services data
      final servicesJson = prefs.getString('ppl_meta_platform_services');
      if (servicesJson != null) {
        final platformData = json.decode(servicesJson);
        final cameraEndpoints = platformData['camera_endpoints'] as Map<String, dynamic>?;
        if (cameraEndpoints != null && cameraEndpoints['register'] != null) {
          // Extract base URL from register endpoint
          final registerUrl = cameraEndpoints['register'] as String;
          final regUri = Uri.parse(registerUrl);
          final baseUrl = '${regUri.scheme}://${regUri.host}:${regUri.port}';
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
  
  /// Check if camera is already registered (has stored UUID)
  Future<Map<String, dynamic>?> checkExistingCamera(String jwtToken) async {
    try {
      // Check if we have a stored camera UUID from previous registration
      final storedUuid = await _deviceService.getStoredCameraUuid();
      
      if (storedUuid == null) {
        AutoRegistrationLogger.debug('No stored camera UUID - camera not yet registered');
        return null;
      }
      
      AutoRegistrationLogger.step('CHECK', 'Found stored camera UUID: $storedUuid');
      
      // Get cameras service URL
      final baseUrl = await _getCamerasServiceUrl();
      if (baseUrl == null) {
        AutoRegistrationLogger.warning('Cameras service URL not available - skipping existing camera check');
        return null;
      }
      
      // Verify camera still exists on server
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/cameras/$storedUuid'),
        headers: {
          'Authorization': 'Bearer $jwtToken',
        },
      );
      
      if (response.statusCode == 200) {
        final cameraData = json.decode(response.body);
        AutoRegistrationLogger.success('Camera exists on server with UUID: $storedUuid');
        return cameraData;
      } else if (response.statusCode == 404) {
        AutoRegistrationLogger.warning('Camera UUID not found on server - will re-register');
        // DO NOT clear UUID here - it may be needed for troubleshooting
        // The new registration will overwrite it with a new UUID if needed
        AutoRegistrationLogger.debug('UUID preserved for diagnostic purposes');
        return null;
      } else {
        AutoRegistrationLogger.warning('Failed to verify camera: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      AutoRegistrationLogger.error('Error checking existing camera: $e');
      return null;
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
      
      // Step 4: Get device serial for hardware identification
      AutoRegistrationLogger.step('4', 'Getting device serial number');
      String deviceSerial;
      try {
        deviceSerial = await _deviceService.getDeviceSerial();
        AutoRegistrationLogger.success('Device serial obtained');
      } catch (e) {
        AutoRegistrationLogger.error('Failed to get device serial: $e');
        return CameraRegistrationResult.failure(
          error: 'Failed to identify device hardware',
        );
      }
      
      // Step 5: Prepare registration data (NO device_id - server generates UUID)
      AutoRegistrationLogger.step('5', 'Preparing registration payload');
      
      final requestBody = {
        // Name is optional - server will auto-generate if not provided
        if (cameraName.isNotEmpty) 'name': cameraName,
        'ip_address': deviceIP,
        'port': 8554, // Default RTSP port for mobile cameras
        'device_model': deviceInfo['model'] ?? 'Mobile Camera',
        'device_manufacturer': deviceInfo['manufacturer'] ?? 'Unknown',
        'device_serial': deviceSerial, // Hardware identifier component
        'app_version': '1.0.0',
      };
      AutoRegistrationLogger.success('Mobile camera registration payload prepared (UUID v4 system)');
      AutoRegistrationLogger.debug('Payload: manufacturer=${requestBody['device_manufacturer']}, model=${requestBody['device_model']}');
      
      // Step 6: Send registration request
      AutoRegistrationLogger.step('6', 'Sending registration request');
      
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
        
        // Extract camera information
        final cameraId = cameraData['id'];
        final deviceUuid = cameraData['device_id']; // Server-generated UUID
        final cameraNameFromResponse = cameraData['name'];
        
        AutoRegistrationLogger.debug('Raw values - ID: $cameraId, UUID: $deviceUuid, Name: $cameraNameFromResponse');
        
        if (cameraId != null && deviceUuid != null) {
          // Step 7: Store server-generated UUID
          AutoRegistrationLogger.step('7', 'Storing server-generated UUID');
          try {
            await _deviceService.storeCameraUuid(deviceUuid.toString());
            AutoRegistrationLogger.success('UUID stored in SharedPreferences');
          } catch (e) {
            AutoRegistrationLogger.error('Failed to store UUID: $e');
            return CameraRegistrationResult.failure(
              error: 'Registration succeeded but failed to store UUID: $e',
            );
          }
          
          AutoRegistrationLogger.success('Mobile camera registration complete!');
          AutoRegistrationLogger.deviceInfo('Camera ID', cameraId.toString());
          AutoRegistrationLogger.deviceInfo('Device UUID', deviceUuid.toString());
          AutoRegistrationLogger.deviceInfo('Camera Name', cameraNameFromResponse?.toString() ?? cameraName);
          AutoRegistrationLogger.deviceInfo('Camera Type', cameraData['camera_type']);
          AutoRegistrationLogger.deviceInfo('Status', cameraData['status']);
          AutoRegistrationLogger.deviceInfo('Connection String', cameraData['connection_string']);
          
          try {
            final successResult = CameraRegistrationResult.success(
              cameraId: cameraId is int ? cameraId : int.tryParse(cameraId.toString()) ?? 0,
              cameraName: cameraNameFromResponse?.toString() ?? cameraName,
              deviceId: deviceUuid.toString(), // Server UUID, not legacy device_id
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
          AutoRegistrationLogger.error('Camera ID: $cameraId, Device UUID: $deviceUuid');
          AutoRegistrationLogger.error('Full camera data: $cameraData');
          
          return CameraRegistrationResult.failure(
            error: 'Invalid camera data in response - missing ID or device_id (UUID)',
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
            
            // Try to get stored UUID, fall back to device serial if not available
            final storedUuid = await _deviceService.getStoredCameraUuid();
            final fallbackId = storedUuid ?? deviceSerial;
            
            return CameraRegistrationResult.success(
              cameraId: 0, // We don't have the actual ID, but that's okay for existing cameras
              cameraName: cameraName,
              deviceId: fallbackId,
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

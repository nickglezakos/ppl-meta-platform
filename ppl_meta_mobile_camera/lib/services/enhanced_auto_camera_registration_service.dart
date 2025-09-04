import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'device_identifier_service.dart';
import 'app_logger.dart';
import 'unified_discovery_service.dart';
import '../models/camera_registration_result.dart';
import '../models/platform_services.dart';

/// Enhanced camera registration service with unified discovery support
class EnhancedAutoCameraRegistrationService {
  final DeviceIdentifierService _deviceService = DeviceIdentifierService();
  final UnifiedDiscoveryService _discoveryService = UnifiedDiscoveryService();
  
  /// Register camera automatically using discovered services
  /// Returns CameraRegistrationResult with camera ID and device ID
  Future<CameraRegistrationResult> autoRegisterCamera(String jwtToken) async {
    AutoRegistrationLogger.step('START', 'Beginning enhanced automatic camera registration');
    
    try {
      // Step 0: Discover services if needed
      AutoRegistrationLogger.step('0', 'Discovering camera service endpoints');
      final cameraServiceUrl = await _findCameraServiceUrl(jwtToken);
      
      if (cameraServiceUrl == null) {
        AutoRegistrationLogger.error('Failed to discover camera service');
        throw Exception('Camera service not available - discovery failed');
      }
      
      AutoRegistrationLogger.success('Camera service discovered: $cameraServiceUrl');
      
      // Load platform services configuration (fallback)
      final prefs = await SharedPreferences.getInstance();
      final servicesJson = prefs.getString('ppl_meta_platform_services');
      
      PlatformServices? services;
      if (servicesJson != null) {
        try {
          services = PlatformServices.fromJson(json.decode(servicesJson));
          AutoRegistrationLogger.debug('Platform services loaded from storage');
        } catch (e) {
          AutoRegistrationLogger.warning('Failed to parse stored platform services: $e');
        }
      }
      
      AutoRegistrationLogger.debug('JWT Token length: ${jwtToken.length}');
      AutoRegistrationLogger.debug('Camera service endpoint: $cameraServiceUrl');
      if (services != null) {
        AutoRegistrationLogger.debug('Fallback media service: ${services.mediaService.endpoint}');
      }
      
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
        'discovery_method': 'enhanced_unified',
      };
      AutoRegistrationLogger.success('Enhanced mobile camera registration payload prepared');
      AutoRegistrationLogger.debug('Payload keys: ${requestBody.keys.toList()}');
      
      // Step 5: Send registration request
      AutoRegistrationLogger.step('5', 'Sending registration request');
      
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
          AutoRegistrationLogger.success('Enhanced mobile camera registered successfully!');
          AutoRegistrationLogger.deviceInfo('Camera ID', cameraId);
          AutoRegistrationLogger.deviceInfo('Device ID', deviceId);
          AutoRegistrationLogger.deviceInfo('Camera Type', cameraData['camera_type']);
          AutoRegistrationLogger.deviceInfo('Status', cameraData['status']);
          AutoRegistrationLogger.deviceInfo('Connection String', cameraData['connection_string']);
          AutoRegistrationLogger.deviceInfo('Discovery Method', requestBody['discovery_method']);
          
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
      AutoRegistrationLogger.error('Exception during enhanced registration: ${e.toString()}', e);
      return CameraRegistrationResult.failure(
        error: 'Enhanced registration exception: $e',
      );
    } finally {
      // Don't dispose discovery service as it might be used elsewhere
    }
  }
  
  /// Find camera service URL using unified discovery
  Future<String?> _findCameraServiceUrl(String jwtToken) async {
    try {
      AutoRegistrationLogger.debug('Attempting to discover camera service...');
      
      // Method 1: Use unified discovery to find camera service directly
      final discoveredServices = await _discoveryService.discoverAllServices();
      final cameraServices = discoveredServices.where((s) => 
          s.name.contains('camera') || s.capabilities.contains('camera')).toList();
      
      if (cameraServices.isNotEmpty) {
        final bestCameraService = cameraServices.first;
        AutoRegistrationLogger.success('Found camera service via discovery: ${bestCameraService.baseUrl}');
        return bestCameraService.baseUrl;
      }
      
      // Method 2: Try standard camera service URLs
      final standardUrls = [
        'http://localhost:8005',  // Direct camera service
        'http://127.0.0.1:8005',  // Direct camera service
        'http://localhost/cameras', // Via nginx proxy
      ];
      
      for (final url in standardUrls) {
        if (await _testCameraServiceHealth(url, jwtToken)) {
          AutoRegistrationLogger.success('Found camera service via standard URL: $url');
          return url;
        }
      }
      
      // Method 3: Try to derive from discovered services
      final nodeServices = discoveredServices.where((s) => s.isNodeService).toList();
      if (nodeServices.isNotEmpty) {
        final nodeService = nodeServices.first;
        
        // Try to get camera service info from the node service
        final derivedUrls = [
          'http://${nodeService.host}:8005', // Assume camera service on same host, port 8005
        ];
        
        for (final url in derivedUrls) {
          if (await _testCameraServiceHealth(url, jwtToken)) {
            AutoRegistrationLogger.success('Found camera service via derivation: $url');
            return url;
          }
        }
      }
      
      AutoRegistrationLogger.warning('Camera service discovery failed with all methods');
      return null;
      
    } catch (e) {
      AutoRegistrationLogger.error('Error discovering camera service: $e');
      return null;
    }
  }
  
  /// Test if camera service is available and healthy
  Future<bool> _testCameraServiceHealth(String baseUrl, String jwtToken) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health'),
        headers: {
          'Authorization': 'Bearer $jwtToken',
          'Accept': 'application/json',
        },
      ).timeout(const Duration(seconds: 5));
      
      final isHealthy = response.statusCode == 200;
      AutoRegistrationLogger.debug('Camera service health check $baseUrl: ${isHealthy ? 'OK' : 'FAIL'} (${response.statusCode})');
      return isHealthy;
      
    } catch (e) {
      AutoRegistrationLogger.debug('Camera service health check $baseUrl: FAIL ($e)');
      return false;
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

  /// Get current discovered services
  List<DiscoveredServiceInfo> get discoveredServices => _discoveryService.currentServices;

  /// Refresh service discovery
  Future<List<DiscoveredServiceInfo>> refreshDiscovery() async {
    return await _discoveryService.discoverAllServices();
  }

  /// Dispose resources
  void dispose() {
    _discoveryService.dispose();
  }
}

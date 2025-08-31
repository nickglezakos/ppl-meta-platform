import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:io';
import 'package:network_info_plus/network_info_plus.dart';
import '../../../core/core.dart';
import '../../../services/device_identifier_service.dart';

/// Screen for registering the mobile device as a camera with the PPL Meta platform
class CameraRegistrationScreen extends StatefulWidget {
  const CameraRegistrationScreen({super.key});

  @override
  State<CameraRegistrationScreen> createState() => _CameraRegistrationScreenState();
}

class _CameraRegistrationScreenState extends State<CameraRegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _cameraNameController = TextEditingController();
  final _locationController = TextEditingController();
  final _deviceService = DeviceIdentifierService();
  bool _isRegistering = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    // Set default camera name based on device info
    _cameraNameController.text = _generateDefaultCameraName();
  }

  @override
  void dispose() {
    _cameraNameController.dispose();
    _locationController.dispose();
    super.dispose();
  }

  String _generateDefaultCameraName() {
    final now = DateTime.now();
    return 'Mobile Camera ${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }

  Future<void> _registerCamera() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isRegistering = true;
      _errorMessage = null;
    });

    try {
      final authProvider = context.read<AuthenticationProvider>();
      final cameraProvider = context.read<CameraProvider>();
      
      // Get platform connectivity information
      final connectivityInfo = await _fetchPlatformConnectivity();
      
      if (connectivityInfo == null) {
        throw Exception('Failed to get platform connectivity information');
      }

      // Register camera with the platform
      final success = await _registerCameraWithPlatform(
        cameraName: _cameraNameController.text.trim(),
        location: _locationController.text.trim(),
        connectivityInfo: connectivityInfo,
      );

      if (success) {
        // Initialize camera provider with connectivity info
        await cameraProvider.initializeWithConnectivity(
          connectivityData: connectivityInfo,
          registeredCameraName: _cameraNameController.text.trim(),
        );
        
        // Show success message and navigate to camera screen
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Camera "${_cameraNameController.text}" registered successfully!'),
              backgroundColor: Colors.green,
            ),
          );
          
          // Update authentication state to indicate camera is registered
          authProvider.setCameraRegistered(true);
        }
      } else {
        throw Exception('Camera registration failed');
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Registration failed: ${e.toString()}';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isRegistering = false;
        });
      }
    }
  }

  Future<Map<String, dynamic>?> _fetchPlatformConnectivity() async {
    try {
      final authService = AuthenticationService.instance;
      
      // Try to get platform services data from authentication service first
      final platformServices = authService.platformServices;
      
      if (platformServices != null) {
        print('✅ Using cached platform services data');
        
        // Transform platform services data to the expected format
        final connectivityInfo = platformServices['connectivity'] as Map<String, dynamic>?;
        final microservices = platformServices['microservices'] as Map<String, dynamic>?;
        final mobileConfig = platformServices['mobile_camera_config'] as Map<String, dynamic>?;
        
        if (connectivityInfo != null && microservices != null) {
          final localIp = connectivityInfo['local_ip'] as String?;
          final mediaService = microservices['media'] as Map<String, dynamic>?;
          final cameraService = microservices['cameras'] as Map<String, dynamic>?;
          
          return {
            'platform_info': platformServices['platform_info'],
            'connectivity': connectivityInfo,
            'streaming_endpoints': {
              'mjpeg': '${mediaService?['endpoints']?['local']}/mjpeg',
              'websocket': '${mediaService?['endpoints']?['local']?.replaceAll('http', 'ws')}/ws/camera_stream',
              'upload': '${mediaService?['endpoints']?['local']}/upload',
              'stream': '${mediaService?['endpoints']?['local']}/stream',
            },
            'camera_endpoints': {
              'register': '${cameraService?['endpoints']?['local']}/api/v1/cameras/mobile',
              'status': '${cameraService?['endpoints']?['local']}/api/v1/cameras/status',
              'config': '${cameraService?['endpoints']?['local']}/api/v1/cameras/stream-config',
            },
            'server_info': {
              'host': localIp,
              'node_port': microservices['node']?['port'],
              'media_port': microservices['media']?['port'],
              'gateway_port': microservices['gateway']?['port'],
              'cameras_port': microservices['cameras']?['port'],
              'vision_port': microservices['vision']?['port'],
              'orchestrator_port': microservices['orchestrator']?['port'],
            },
            'mobile_camera_config': mobileConfig,
            'raw_platform_services': platformServices, // Keep original data
          };
        }
      }
      
      // Fallback: fetch fresh platform services data
      print('🔄 Fetching fresh platform services data...');
      final serverUrl = authService.serverUrl;
      
      if (serverUrl.isEmpty) {
        throw Exception('No server URL available');
      }

      final response = await authService.makeAuthenticatedRequest(
        'GET',
        '$serverUrl/api/v1/users/platform/services',
      );

      if (response != null) {
        print('✅ Fresh platform services data fetched');
        // Recursively call this method to use the cached data path
        return await _fetchPlatformConnectivity();
      } else {
        throw Exception('Failed to fetch platform services from server');
      }
    } catch (e) {
      print('🔍 Error fetching platform connectivity: $e');
      return null;
    }
  }

  Future<bool> _registerCameraWithPlatform({
    required String cameraName,
    required String location,
    required Map<String, dynamic> connectivityInfo,
  }) async {
    try {
      final authService = AuthenticationService.instance;
      final serverUrl = authService.serverUrl;
      
      // Get device information and IP for the correct payload format
      final deviceInfo = await _deviceService.getDeviceRegistrationInfo();
      final deviceIP = await _getDeviceIP();
      final deviceId = await _generateDeviceId();
      
      // Prepare camera registration data in CORRECT format (MobileCameraCreate schema)
      final registrationData = {
        'name': cameraName,
        'device_id': deviceId,
        'ip_address': deviceIP,
        'port': 8554,
        'device_model': deviceInfo['model'] ?? 'Mobile Camera',
        'device_manufacturer': deviceInfo['manufacturer'] ?? 'PPL Meta Mobile',
        'app_version': '1.0.0',
        'resolution_width': 1920,
        'resolution_height': 1080,
        'max_fps': 30,
        'supports_audio': true,
      };

      print('🎯 Registering camera with CORRECT data: $registrationData');

      // Register with cameras service using CORRECT endpoint
      final cameraEndpoint = connectivityInfo['camera_endpoints']?['register'] ?? 
                            '$serverUrl/api/v1/cameras/mobile';
      
      final response = await authService.makeAuthenticatedRequest(
        'POST',
        cameraEndpoint,
        body: registrationData,
      );

      print('📥 Camera registration response: $response');

      return response != null && 
             (response['message']?.contains('successfully') == true || 
              response['success'] == true || 
              response['status'] == 'success');
    } catch (e) {
      print('❌ Camera registration error: $e');
      return false;
    }
  }

  /// Get device IP address
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
      print('⚠️ Error getting device IP: $e');
      return '192.168.1.100'; // Fallback IP
    }
  }

  /// Generate unique device ID for camera registration
  Future<String> _generateDeviceId() async {
    try {
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final deviceInfo = await _deviceService.getDeviceRegistrationInfo();
      final baseId = deviceInfo['device_id'] ?? 'unknown';
      return 'mobile_${baseId}_$timestamp';
    } catch (e) {
      print('⚠️ Error generating device ID: $e');
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      return 'mobile_fallback_$timestamp';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Register Camera'),
        backgroundColor: Theme.of(context).colorScheme.primaryContainer,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      Icon(
                        Icons.camera_alt,
                        size: 48,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Register Mobile Camera',
                        style: Theme.of(context).textTheme.headlineSmall,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Set up your mobile device as a camera in the PPL Meta platform',
                        style: Theme.of(context).textTheme.bodyMedium,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Camera Name Field
              TextFormField(
                controller: _cameraNameController,
                decoration: const InputDecoration(
                  labelText: 'Camera Name',
                  hintText: 'Enter a name for this camera',
                  prefixIcon: Icon(Icons.label),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter a camera name';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 16),
              
              // Location Field (Optional)
              TextFormField(
                controller: _locationController,
                decoration: const InputDecoration(
                  labelText: 'Location (Optional)',
                  hintText: 'Enter camera location',
                  prefixIcon: Icon(Icons.location_on),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Error Message
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    border: Border.all(color: Colors.red.shade200),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error, color: Colors.red.shade700, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(color: Colors.red.shade700),
                        ),
                      ),
                    ],
                  ),
                ),
              
              // Register Button
              ElevatedButton(
                onPressed: _isRegistering ? null : _registerCamera,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  foregroundColor: Theme.of(context).colorScheme.onPrimary,
                ),
                child: _isRegistering
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          ),
                          SizedBox(width: 12),
                          Text('Registering Camera...'),
                        ],
                      )
                    : const Text(
                        'Register Camera',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
              
              const SizedBox(height: 16),
              
              // Skip Button
              TextButton(
                onPressed: _isRegistering ? null : () {
                  // Skip registration and go to camera screen
                  context.read<AuthenticationProvider>().setCameraRegistered(true);
                },
                child: const Text('Skip Registration'),
              ),
              
              const Spacer(),
              
              // Info Card
              Card(
                color: Theme.of(context).colorScheme.surfaceVariant,
                child: const Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.info_outline, size: 20),
                          SizedBox(width: 8),
                          Text(
                            'What happens next?',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      SizedBox(height: 8),
                      Text(
                        '• Your device will be registered as a camera\n'
                        '• Platform connectivity will be configured\n'
                        '• You can start streaming immediately\n'
                        '• Camera settings can be changed later',
                        style: TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

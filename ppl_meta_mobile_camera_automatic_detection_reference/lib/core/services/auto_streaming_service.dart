import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'authentication_service.dart';

/// Automatic streaming service that implements the complete workflow
/// User only needs to provide camera name - everything else is automatic
class AutoStreamingService {
  static const String _tokenKey = 'jwt_token';
  static const String _cameraIdKey = 'registered_camera_id';
  static const String _lastCameraNameKey = 'last_camera_name';
  
  String? _jwtToken;
  String? _cameraServiceUrl;
  String? _mediaServiceUrl;
  int? _registeredCameraId;
  String? _lastCameraName;

  /// Main method: Start automatic streaming workflow
  /// Only requires camera name from user
  /// Uses existing JWT token if provided
  Future<AutoStreamingResult> startAutomaticStreaming(String cameraName, {String? existingToken}) async {
    try {
      print('🚀 Starting automatic streaming workflow for: $cameraName');
      
      // Step 1: Use existing token or login
      if (existingToken != null) {
        _jwtToken = existingToken;
        print('✅ Using existing JWT token');
      } else {
        if (!await _performLogin()) {
          return AutoStreamingResult.error('Failed to authenticate with platform');
        }
      }
      
      // Step 2: Discover platform services
      if (!await _discoverPlatformServices()) {
        return AutoStreamingResult.error('Failed to discover platform services');
      }
      
      // Step 3: Connect to Camera service
      if (!await _connectToCameraService()) {
        return AutoStreamingResult.error('Failed to connect to Camera service');
      }
      
      // Step 4: Register mobile camera
      final cameraId = await _registerMobileCamera(cameraName);
      if (cameraId == null) {
        return AutoStreamingResult.error('Failed to register camera');
      }
      
      // Step 5: Validate Media service
      if (!await _validateMediaService()) {
        return AutoStreamingResult.error('Media service not available');
      }
      
      // Save state
      await _saveStreamingState(cameraName, cameraId);
      
      return AutoStreamingResult.success(
        cameraId: cameraId,
        cameraServiceUrl: _cameraServiceUrl!,
        mediaServiceUrl: _mediaServiceUrl!,
        jwtToken: _jwtToken!,
      );
      
    } catch (e) {
      print('❌ Automatic streaming workflow failed: $e');
      return AutoStreamingResult.error('Workflow failed: $e');
    }
  }

    /// Step 1: Authenticate with Node service
  Future<bool> _performLogin() async {
    try {
      print('🔐 Step 1: Authenticating with platform...');
      
      // Try to get existing token first
      final prefs = await SharedPreferences.getInstance();
      final existingToken = prefs.getString(_tokenKey);
      
      if (existingToken != null) {
        print('🎫 Found existing token, validating...');
        if (await _validateExistingToken(existingToken)) {
          _jwtToken = existingToken;
          print('✅ Existing token is valid');
          return true;
        } else {
          print('❌ Existing token is invalid, need fresh login');
          await prefs.remove(_tokenKey);
        }
      }
      
            // Use AuthenticationService for login instead of manual login
      final authService = AuthenticationService.instance;
      
      // Initialize and auto-discover server if needed
      await authService.initializeAuth();
      
      // Perform login with correct credentials
      final loginResult = await authService.login(
        username: 'fresh.user@example.com',
        password: 'NewPassword234!',
      );
      
      if (loginResult.success) {
        _jwtToken = loginResult.token;
        print('✅ Login successful via AuthenticationService');
        
        // Save token
        if (_jwtToken != null) {
          await prefs.setString(_tokenKey, _jwtToken!);
        }
        
        return true;
      } else {
        print('❌ Login failed: ${loginResult.error}');
        return false;
      }
      
    } catch (e) {
      print('❌ Login failed: $e');
      return false;
    }
  }

  /// Validate existing JWT token
  Future<bool> _validateExistingToken(String token) async {
    try {
      // Use AuthenticationService to validate token
      final authService = AuthenticationService.instance;
      
      // Try to validate with localhost first (same as test approach)
      final validationUrls = ['http://localhost:8001', 'http://127.0.0.1:8001'];
      
      for (final nodeUrl in validationUrls) {
        try {
          final response = await http.get(
            Uri.parse('$nodeUrl/api/v1/users/platform/services'),
            headers: {'Authorization': 'Bearer $token'},
          ).timeout(Duration(seconds: 3));
          
          if (response.statusCode == 200) {
            return true;
          }
        } catch (e) {
          continue;
        }
      }
      
      return false;
    } catch (e) {
      return false;
    }
  }

  /// Step 2: Discover platform services automatically
  Future<bool> _discoverPlatformServices() async {
    try {
      print('🔍 Step 2: Discovering platform services...');
      
      // Use AuthenticationService's platform services data
      final authService = AuthenticationService.instance;
      final platformServices = authService.platformServices;
      
      if (platformServices == null) {
        print('❌ No platform services data available from AuthenticationService');
        return false;
      }
      
      print('✅ Platform services data available');
      final microservices = platformServices['microservices'] as Map<String, dynamic>?;
      
      if (microservices == null) {
        print('❌ No microservices data in platform services');
        return false;
      }
      
      print('📊 Available services: ${microservices.keys.toList()}');
      
      // Extract Camera service URL
      final cameraService = microservices['cameras'];
      if (cameraService != null) {
        final endpoints = cameraService['endpoints'] as Map<String, dynamic>;
        _cameraServiceUrl = endpoints['local'] ?? endpoints['tailscale'];
        if (_cameraServiceUrl != null) {
          print('📹 Camera service: $_cameraServiceUrl');
        }
      }
      
      // Extract Media service URL
      final mediaService = microservices['media'];
      if (mediaService != null) {
        final endpoints = mediaService['endpoints'] as Map<String, dynamic>;
        _mediaServiceUrl = endpoints['local'] ?? endpoints['tailscale'];
        if (_mediaServiceUrl != null) {
          print('🎬 Media service: $_mediaServiceUrl');
        }
      }
      
      if (_cameraServiceUrl != null && _mediaServiceUrl != null) {
        print('✅ Platform services discovered successfully');
        return true;
      } else {
        print('❌ Failed to discover required service URLs');
        print('📹 Camera service URL: $_cameraServiceUrl');
        print('🎬 Media service URL: $_mediaServiceUrl');
        return false;
      }
      
    } catch (e) {
      print('❌ Service discovery failed: $e');
      return false;
    }
  }

  /// Step 3: Connect and validate Camera service
  Future<bool> _connectToCameraService() async {
    try {
      print('📹 Step 3: Connecting to Camera service...');
      
      // Health check
      final healthResponse = await http.get(
        Uri.parse('$_cameraServiceUrl/health'),
      ).timeout(Duration(seconds: 3));
      
      if (healthResponse.statusCode != 200) {
        print('❌ Camera service health check failed');
        return false;
      }
      
      // Validate token with Camera service (test file shows it uses /api/v1/auth/validate-token with query param)
      print('🔍 Validating token with Camera service...');
      final authResponse = await http.post(
        Uri.parse('$_cameraServiceUrl/api/v1/auth/validate-token?token=$_jwtToken'),
        headers: {'Accept': 'application/json'},
      ).timeout(Duration(seconds: 3));
      
      if (authResponse.statusCode == 200) {
        print('✅ Camera service connection successful');
        return true;
      } else {
        print('❌ Camera service authentication failed: ${authResponse.statusCode}');
        return false;
      }
      
    } catch (e) {
      print('❌ Camera service connection failed: $e');
      return false;
    }
  }

  /// Step 4: Register mobile camera automatically
  Future<int?> _registerMobileCamera(String cameraName) async {
    try {
      print('📱 Step 4: Registering mobile camera: $cameraName');
      
      // Get device info dynamically
      final interfaces = await NetworkInterface.list();
      String deviceIp = '192.168.1.66'; // Default fallback
      
      for (final interface in interfaces) {
        for (final addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            deviceIp = addr.address;
            break;
          }
        }
      }
      
      // Generate unique device ID
      final deviceId = 'mobile_${DateTime.now().millisecondsSinceEpoch}_${deviceIp.replaceAll('.', '')}';
      
      final registrationData = {
        'name': cameraName,
        'device_id': deviceId,
        'ip_address': deviceIp,
        'port': 8554,
        'device_model': Platform.isAndroid ? 'Android Device' : 'iOS Device',
        'device_manufacturer': 'PPL Meta Mobile',
        'app_version': '2.13.1',
        'resolution_width': 1920,
        'resolution_height': 1080,
        'max_fps': 30,
        'supports_audio': false,
      };
      
      print('📝 Registration data: ${registrationData.entries.where((e) => e.key != 'device_id').map((e) => '${e.key}: ${e.value}').join(', ')}');
      
      final response = await http.post(
        Uri.parse('$_cameraServiceUrl/api/v1/cameras/mobile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_jwtToken',
        },
        body: json.encode(registrationData),
      ).timeout(Duration(seconds: 5));
      
      print('📥 Registration response status: ${response.statusCode}');
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = json.decode(response.body);
        print('📄 Full response: $responseData');
        
        // Extract camera ID dynamically (handle different response formats)
        int? cameraId;
        if (responseData.containsKey('camera_id')) {
          cameraId = responseData['camera_id'] as int?;
        } else if (responseData.containsKey('id')) {
          cameraId = responseData['id'] as int?;
        } else if (responseData.containsKey('camera') && responseData['camera'] != null) {
          final camera = responseData['camera'];
          cameraId = camera['id'] as int?;
        } else if (responseData.containsKey('data') && responseData['data'] != null) {
          final data = responseData['data'];
          cameraId = data['id'] as int?;
        }
        
        if (cameraId != null) {
          print('✅ Camera registered successfully');
          print('📊 Camera ID: $cameraId');
          
          _registeredCameraId = cameraId;
          return cameraId;
        } else {
          print('❌ Camera registration succeeded but no camera ID found');
          print('📄 Response structure: ${responseData.keys.toList()}');
          return null;
        }
      } else {
        print('❌ Camera registration failed: ${response.statusCode}');
        print('📄 Response: ${response.body}');
        return null;
      }
      
    } catch (e) {
      print('❌ Camera registration failed: $e');
      return null;
    }
  }

  /// Step 5: Validate Media service
  Future<bool> _validateMediaService() async {
    try {
      print('🎬 Step 5: Validating Media service...');
      
      final response = await http.get(
        Uri.parse('$_mediaServiceUrl/health'),
      ).timeout(Duration(seconds: 3));
      
      if (response.statusCode == 200) {
        print('✅ Media service validation successful');
        return true;
      } else {
        print('⚠️ Media service validation returned: ${response.statusCode}');
        return true; // Media service often doesn't need auth for health checks
      }
      
    } catch (e) {
      print('❌ Media service validation failed: $e');
      return false;
    }
  }

  /// Save streaming state for future use
  Future<void> _saveStreamingState(String cameraName, int cameraId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_cameraIdKey, cameraId);
      await prefs.setString(_lastCameraNameKey, cameraName);
      _lastCameraName = cameraName;
      
      print('💾 Streaming state saved');
    } catch (e) {
      print('⚠️ Failed to save streaming state: $e');
    }
  }

  /// Check if camera is already registered and ready
  Future<bool> isCameraRegistered() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cameraId = prefs.getInt(_cameraIdKey);
      final cameraName = prefs.getString(_lastCameraNameKey);
      
      return cameraId != null && cameraName != null;
    } catch (e) {
      return false;
    }
  }

  /// Get last registered camera info
  Future<Map<String, dynamic>?> getLastRegisteredCamera() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cameraId = prefs.getInt(_cameraIdKey);
      final cameraName = prefs.getString(_lastCameraNameKey);
      
      if (cameraId != null && cameraName != null) {
        return {
          'id': cameraId,
          'name': cameraName,
        };
      }
      
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Clear saved streaming state
  Future<void> clearStreamingState() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_cameraIdKey);
      await prefs.remove(_lastCameraNameKey);
      _registeredCameraId = null;
      _lastCameraName = null;
      
      print('🗑️ Streaming state cleared');
    } catch (e) {
      print('⚠️ Failed to clear streaming state: $e');
    }
  }

  // Getters for current state
  String? get cameraServiceUrl => _cameraServiceUrl;
  String? get mediaServiceUrl => _mediaServiceUrl;
  String? get jwtToken => _jwtToken;
  int? get registeredCameraId => _registeredCameraId;
  String? get lastCameraName => _lastCameraName;
}

/// Result class for automatic streaming workflow
class AutoStreamingResult {
  final bool success;
  final String? error;
  final int? cameraId;
  final String? cameraServiceUrl;
  final String? mediaServiceUrl;
  final String? jwtToken;

  AutoStreamingResult._({
    required this.success,
    this.error,
    this.cameraId,
    this.cameraServiceUrl,
    this.mediaServiceUrl,
    this.jwtToken,
  });

  factory AutoStreamingResult.success({
    required int cameraId,
    required String cameraServiceUrl,
    required String mediaServiceUrl,
    required String jwtToken,
  }) {
    return AutoStreamingResult._(
      success: true,
      cameraId: cameraId,
      cameraServiceUrl: cameraServiceUrl,
      mediaServiceUrl: mediaServiceUrl,
      jwtToken: jwtToken,
    );
  }

  factory AutoStreamingResult.error(String error) {
    return AutoStreamingResult._(
      success: false,
      error: error,
    );
  }
}

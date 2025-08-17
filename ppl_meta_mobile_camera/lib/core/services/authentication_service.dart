import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:crypto/crypto.dart';
import '../models/auth_result.dart';

/// Authentication service for PPL Meta platform integration
class AuthenticationService {
  static AuthenticationService? _instance;
  static AuthenticationService get instance => _instance ??= AuthenticationService._();
  AuthenticationService._();

  static const String _tokenKey = 'ppl_meta_auth_token';
  static const String _userDataKey = 'ppl_meta_user_data';
  static const String _deviceDataKey = 'ppl_meta_device_data';
  static const String _serverConfigKey = 'ppl_meta_server_config';
  static const String _userIdKey = 'ppl_meta_user_id';

  String? _authToken;
  Map<String, dynamic>? _userData;
  Map<String, dynamic>? _deviceData;
  String _serverUrl = '';
  bool _isAuthenticated = false;
  bool _isInitialized = false;

  // Getters
  bool get isAuthenticated => _isAuthenticated;
  String? get authToken => _authToken;
  String? get token => _authToken; // Alias for compatibility
  Map<String, dynamic>? get userData => _userData;
  Map<String, dynamic>? get deviceData => _deviceData;
  String get serverUrl => _serverUrl;
  bool get isInitialized => _isInitialized;

  /// Get platform services connectivity data
  Map<String, dynamic>? get platformServices {
    return _deviceData?['platform_services'];
  }

  /// Get recommended streaming endpoint for mobile cameras
  String? get recommendedStreamingEndpoint {
    return platformServices?['mobile_camera_config']?['recommended_endpoint'];
  }

  /// Get camera service endpoint for registration
  String? get cameraServiceEndpoint {
    final services = platformServices?['microservices']?['cameras'];
    return services?['endpoints']?['local'] ?? services?['endpoints']?['tailscale'];
  }

  /// Initialize authentication service with auto-discovery
  Future<bool> initializeAuth() async {
    try {
      print('Initializing authentication service...');
      
      // Try to auto-discover server first
      await _tryAutoDiscoverServer();
      
      // Load any existing saved configuration
      final prefs = await SharedPreferences.getInstance();
      final savedServerUrl = prefs.getString(_serverConfigKey);
      final savedToken = prefs.getString(_tokenKey);
      final savedUserData = prefs.getString(_userDataKey);
      final savedDeviceData = prefs.getString(_deviceDataKey);
      
      if (savedServerUrl != null && savedServerUrl.isNotEmpty) {
        _serverUrl = savedServerUrl;
        print('Loaded saved server URL: $_serverUrl');
      }
      
      if (savedToken != null && savedToken.isNotEmpty) {
        _authToken = savedToken;
        
        if (savedUserData != null) {
          _userData = json.decode(savedUserData);
        }
        
        if (savedDeviceData != null) {
          _deviceData = json.decode(savedDeviceData);
        }
        
        // Validate saved token
        if (await validateToken()) {
          _isAuthenticated = true;
          print('Valid saved token found, user is authenticated');
        } else {
          print('Saved token is invalid, clearing credentials');
          await clearCredentials();
        }
      }
      
      _isInitialized = true;
      print('Authentication service initialized successfully');
      return _isAuthenticated;
    } catch (e) {
      print('Error initializing authentication service: $e');
      _isInitialized = true; // Still mark as initialized to allow manual config
      return false;
    }
  }

  /// Try to automatically discover the PPL Meta server on network
  Future<void> _tryAutoDiscoverServer() async {
    // Auto-discovery candidates - will try to detect platform services
    const List<String> candidates = [
      'http://localhost:8001',     // Direct Node service (development)
      'http://localhost',          // Via Nginx proxy (development)
      'http://127.0.0.1:8001',     // Alternative localhost
      'http://127.0.0.1',          // Alternative via proxy
    ];
    
    print('Attempting auto-discovery of PPL Meta server...');
    
    for (final candidate in candidates) {
      try {
        print('Trying server: $candidate');
        final response = await http.get(
          Uri.parse('$candidate/api/v1/health'),
          headers: {'Accept': 'application/json'},
        ).timeout(const Duration(seconds: 3));
        
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          if (data['status'] == 'healthy') {
            _serverUrl = candidate;
            final prefs = await SharedPreferences.getInstance();
            await prefs.setString(_serverConfigKey, _serverUrl);
            print('✅ Auto-discovered PPL Meta server at: $_serverUrl');
            return;
          }
        }
      } catch (e) {
        print('Server $candidate not reachable: $e');
        continue;
      }
    }
    
    print('❌ Auto-discovery failed - will require manual server configuration');
  }

  /// Check if server is properly configured and reachable
  Future<bool> isServerReachable() async {
    if (_serverUrl.isEmpty) return false;
    
    try {
      final response = await http.get(
        Uri.parse('$_serverUrl/api/v1/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['status'] == 'healthy';
      }
      return false;
    } catch (e) {
      print('Server reachability check failed: $e');
      return false;
    }
  }

  /// Get server configuration status
  String getServerStatus() {
    if (_serverUrl.isEmpty) {
      return 'No server configured';
    }
    return 'Server: $_serverUrl';
  }

  /// Force manual server configuration
  void requireManualConfiguration() {
    _serverUrl = '';
    print('Manual server configuration required');
  }

  /// Get authentication headers for API requests
  Map<String, String> getAuthHeaders() {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    if (_authToken != null && _authToken!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    
    return headers;
  }

  /// Get current user information
  String getCurrentUsername() {
    return _userData?['username'] ?? 'Unknown User';
  }

  /// Get current user email
  String getCurrentUserEmail() {
    return _userData?['email'] ?? 'unknown@example.com';
  }

  /// Get current user ID
  String getCurrentUserId() {
    return _userData?['id']?.toString() ?? 'unknown';
  }

  /// Login with email and password
  Future<AuthResult> login({
    String? serverUrl,
    required String username,
    required String password,
  }) async {
    try {
      // Use provided server URL or fall back to discovered/stored URL
      final targetServerUrl = serverUrl ?? _serverUrl;
      if (targetServerUrl.isEmpty) {
        final error = 'No server URL available. Please provide a server URL.';
        return AuthResult.failure(error);
      }

      print('🔐 Attempting login to: $targetServerUrl');
      print('👤 Username: $username');

      // Parse the server URL and determine the authentication endpoint
      final baseUri = Uri.parse(targetServerUrl);
      late Uri authUri;
      
      // Determine authentication endpoint based on URL pattern
      if (baseUri.path.contains('/api/v1') || baseUri.port == 8001) {
        // Node service authentication - correct endpoint is /api/v1/users/login
        authUri = Uri.parse('$targetServerUrl/api/v1/users/login');
      } else if (baseUri.port == 8080) {
        // Gateway service authentication
        authUri = Uri.parse('$targetServerUrl/auth/login');
      } else {
        // Default to node service pattern
        final nodeServiceUrl = '${baseUri.scheme}://${baseUri.host}:8001';
        authUri = Uri.parse('$nodeServiceUrl/api/v1/users/login');
      }

      print('🎯 Authentication endpoint: $authUri');

      // Prepare request body for form-urlencoded format (as per PPL Meta node service)
      final requestBody = 'username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}';

      print('📤 Sending authentication request...');

      // Make authentication request with form-urlencoded data
      final response = await http.post(
        authUri,
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: requestBody,
      ).timeout(const Duration(seconds: 10));

      print('📥 Authentication response: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ Login successful');
        print('🎫 Response data keys: ${data.keys.toList()}');

        // Extract authentication token
        String? token;
        if (data.containsKey('token')) {
          token = data['token'];
        } else if (data.containsKey('access_token')) {
          token = data['access_token'];
        } else if (data.containsKey('data') && data['data'].containsKey('token')) {
          token = data['data']['token'];
        }

        if (token == null) {
          final error = 'Authentication successful but no token received';
          print('❌ $error');
          return AuthResult.failure(error);
        }

        // Store authentication data
        _authToken = token;
        _userData = data.containsKey('user') ? data['user'] : data;
        _serverUrl = targetServerUrl;
        _isAuthenticated = true;

        print('🎫 Token received: ${token.substring(0, 20)}...');
        print('👤 User data: $_userData');

        // Fetch platform services connectivity data
        print('🔍 [LOGIN] Fetching platform services connectivity data...');
        await _fetchPlatformServices();

        // Save to persistent storage
        print('💾 [LOGIN] Saving authentication data to storage...');
        await _saveToStorage();

        print('🎉 [LOGIN] Login process completed successfully');
        return AuthResult.success(token);
      } else {
        // Handle authentication errors
        String error = 'Authentication failed';
        try {
          final errorData = json.decode(response.body);
          if (errorData.containsKey('message')) {
            error = errorData['message'];
          } else if (errorData.containsKey('error')) {
            error = errorData['error'];
          }
        } catch (e) {
          error = 'Authentication failed (${response.statusCode})';
        }

        print('❌ Authentication failed: $error');
        return AuthResult.failure(error, statusCode: response.statusCode);
      }
    } catch (e) {
      final error = 'Login error: $e';
      print('💥 Login exception: $e');
      return AuthResult.failure(error);
    }
  }  /// Fetch user profile information after successful authentication
  Future<void> _fetchUserProfile() async {
    try {
      if (_authToken == null || _serverUrl.isEmpty) {
        print('Cannot fetch user profile: missing token or server URL');
        return;
      }

      final response = await http.get(
        Uri.parse('$_serverUrl/api/v1/users/profile'),
        headers: getAuthHeaders(),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        _userData = json.decode(response.body);
        print('✅ User profile fetched: ${_userData?['username']}');
      } else {
        print('⚠️ Failed to fetch user profile: ${response.statusCode}');
        // Don't fail the login if profile fetch fails, just log it
        _userData = {'username': 'User', 'email': 'unknown@example.com'};
      }
    } catch (e) {
      print('⚠️ Error fetching user profile: $e');
      // Provide fallback user data
      _userData = {'username': 'User', 'email': 'unknown@example.com'};
    }
  }

  /// Register a new device with the PPL Meta platform
  Future<AuthResult> registerDevice({
    required String serverUrl,
    required String deviceName,
    required String deviceType,
  }) async {
    try {
      _serverUrl = _normalizeServerUrl(serverUrl);
      
      final registrationData = {
        'deviceName': deviceName,
        'deviceType': deviceType,
        'deviceInfo': await _getDeviceInfo(),
        'timestamp': DateTime.now().toIso8601String(),
      };

      final response = await http.post(
        Uri.parse('$_serverUrl/api/v1/auth/register'),
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'PPL-Meta-Mobile/1.0',
        },
        body: json.encode(registrationData),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = json.decode(response.body);
        
        _authToken = responseData['access_token'] ?? responseData['token'];
        _userData = responseData['user'];
        _deviceData = responseData['device'];
        _isAuthenticated = true;

        // Store authentication data
        await _storeAuthData();
        
        return AuthResult.success(_authToken!);
      } else {
        final errorData = json.decode(response.body);
        return AuthResult.failure(errorData['detail'] ?? errorData['message'] ?? 'Registration failed');
      }
    } catch (e) {
      return AuthResult.failure('Registration failed: $e');
    }
  }

  /// Logout from the PPL Meta platform
  Future<void> logout() async {
    try {
      if (_serverUrl.isNotEmpty && _authToken != null) {
        await http.post(
          Uri.parse('$_serverUrl/api/v1/auth/logout'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $_authToken',
          },
        );
      }
    } catch (e) {
      print('Logout request failed: $e');
    } finally {
      await clearCredentials();
    }
  }

  /// Fetch platform services connectivity data after authentication
  Future<void> _fetchPlatformServices() async {
    try {
      if (_serverUrl.isEmpty || _authToken == null) {
        print('❌ [PLATFORM_SERVICES] Cannot fetch platform services: missing server URL or token');
        print('🔍 [PLATFORM_SERVICES] Server URL: $_serverUrl');
        print('🔍 [PLATFORM_SERVICES] Auth Token: ${_authToken != null ? 'present' : 'null'}');
        return;
      }

      print('🔍 [PLATFORM_SERVICES] Fetching platform services connectivity data...');
      print('🌐 [PLATFORM_SERVICES] Request URL: $_serverUrl/api/v1/users/platform/services');
      
      final response = await http.get(
        Uri.parse('$_serverUrl/api/v1/users/platform/services'),
        headers: {
          'Authorization': 'Bearer $_authToken',
          'Accept': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));

      print('📥 [PLATFORM_SERVICES] Response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final platformData = json.decode(response.body);
        
        print('✅ [PLATFORM_SERVICES] Platform services data fetched successfully');
        print('📊 [PLATFORM_SERVICES] Data keys: ${platformData.keys.toList()}');
        
        // Store platform services data
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('ppl_meta_platform_services', json.encode(platformData));
        print('💾 [PLATFORM_SERVICES] Data saved to SharedPreferences');
        
        print('🌐 [PLATFORM_SERVICES] Local IP: ${platformData['connectivity']['local_ip']}');
        print('📡 [PLATFORM_SERVICES] Available networks: ${platformData['connectivity']['networks']}');
        print('🎯 [PLATFORM_SERVICES] Recommended streaming endpoint: ${platformData['mobile_camera_config']['recommended_endpoint']}');
        
        // Log microservices information
        if (platformData.containsKey('microservices')) {
          final microservices = platformData['microservices'] as Map<String, dynamic>;
          print('🔧 [PLATFORM_SERVICES] Available microservices:');
          microservices.forEach((serviceName, serviceData) {
            print('   - $serviceName: ${serviceData['endpoint']} (${serviceData['purpose']})');
          });
        }
        
        // Update device data with connectivity info
        _deviceData = {
          ...(_deviceData ?? {}),
          'platform_services': platformData,
          'connectivity_fetched_at': DateTime.now().toIso8601String(),
        };
        
        print('🎯 [PLATFORM_SERVICES] Device data updated with platform connectivity info');
        
      } else {
        print('⚠️ [PLATFORM_SERVICES] Failed to fetch platform services: ${response.statusCode}');
        print('📄 [PLATFORM_SERVICES] Response body: ${response.body}');
      }
    } catch (e) {
      print('❌ [PLATFORM_SERVICES] Error fetching platform services: $e');
      print('🔍 [PLATFORM_SERVICES] Error type: ${e.runtimeType}');
    }
  }

  /// Refresh authentication token
  Future<bool> refreshToken() async {
    try {
      if (_serverUrl.isEmpty || _authToken == null) {
        return false;
      }

      final response = await http.post(
        Uri.parse('$_serverUrl/api/v1/auth/refresh'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
      );

      if (response.statusCode == 200) {
        final responseData = json.decode(response.body);
        
        _authToken = responseData['access_token'] ?? responseData['token'];
        
        // Update stored token
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_tokenKey, _authToken!);
        
        return true;
      }
      
      return false;
    } catch (e) {
      return false;
    }
  }

  /// Validate current token
  Future<bool> validateToken() async {
    try {
      if (_serverUrl.isEmpty || _authToken == null) {
        return false;
      }

      final response = await http.get(
        Uri.parse('$_serverUrl/api/v1/auth/validate'),
        headers: getAuthHeaders(),
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Validate token for Camera service (uses different endpoint)
  Future<bool> validateTokenForCameraService(String cameraServiceUrl) async {
    try {
      if (_authToken == null || _authToken!.isEmpty) {
        print('❌ No token available for camera service validation');
        return false;
      }

      print('🔍 Validating token for camera service: $cameraServiceUrl');
      
      // Camera service expects token as query parameter
      final response = await http.post(
        Uri.parse('$cameraServiceUrl/api/v1/auth/validate-token?token=$_authToken'),
        headers: {
          'Accept': 'application/json',
        },
      );

      print('📊 Camera service validation response: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final isValid = data['valid'] ?? false;
        print('✅ Camera service token validation: $isValid');
        return isValid;
      }
      
      return false;
    } catch (e) {
      print('💥 Error validating token for camera service: $e');
      return false;
    }
  }

  /// Get a valid token (refresh if needed)
  Future<String?> getValidToken() async {
    try {
      // Return null if not authenticated
      if (!_isAuthenticated || _authToken == null) {
        return null;
      }

      // Check if current token is valid
      final isValid = await validateToken();
      if (isValid) {
        return _authToken;
      }

      // Try to refresh token if invalid
      final refreshed = await refreshToken();
      if (refreshed) {
        return _authToken;
      }

      return null;
    } catch (e) {
      print('Error getting valid token: $e');
      return null;
    }
  }

  /// Test server connection
  Future<bool> testServerConnection(String serverUrl) async {
    try {
      final normalizedUrl = _normalizeServerUrl(serverUrl);
      final response = await http.get(
        Uri.parse('$normalizedUrl/api/v1/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Store authentication data
  Future<void> _storeAuthData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      if (_authToken != null) {
        await prefs.setString(_tokenKey, _authToken!);
      }
      
      if (_userData != null) {
        await prefs.setString(_userDataKey, json.encode(_userData!));
      }
      
      if (_deviceData != null) {
        await prefs.setString(_deviceDataKey, json.encode(_deviceData!));
      }
      
      if (_serverUrl.isNotEmpty) {
        await prefs.setString(_serverConfigKey, _serverUrl);
      }
    } catch (e) {
      print('Error storing authentication data: $e');
    }
  }

  /// Clear all credentials and authentication data
  Future<void> clearCredentials() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_tokenKey);
      await prefs.remove(_userDataKey);
      await prefs.remove(_deviceDataKey);
      // Don't remove server config to preserve auto-discovered server
      
      _authToken = null;
      _userData = null;
      _deviceData = null;
      _isAuthenticated = false;
    } catch (e) {
      print('Error clearing credentials: $e');
    }
  }

  /// Normalize server URL format
  String _normalizeServerUrl(String url) {
    if (url.isEmpty) return url;
    
    String normalized = url.trim();
    if (!normalized.startsWith('http://') && !normalized.startsWith('https://')) {
      normalized = 'https://$normalized';
    }
    
    if (normalized.endsWith('/')) {
      normalized = normalized.substring(0, normalized.length - 1);
    }
    
    return normalized;
  }

  /// Get stored platform services data
  Map<String, dynamic>? getPlatformServices() {
    final platformServices = _deviceData?['platform_services'] as Map<String, dynamic>?;
    print('🔍 [GET_PLATFORM_SERVICES] Requested platform services');
    print('📊 [GET_PLATFORM_SERVICES] Device data keys: ${_deviceData?.keys.toList()}');
    print('🎯 [GET_PLATFORM_SERVICES] Platform services available: ${platformServices != null}');
    
    if (platformServices != null) {
      print('✅ [GET_PLATFORM_SERVICES] Returning platform services data');
      print('🌐 [GET_PLATFORM_SERVICES] Services keys: ${platformServices.keys.toList()}');
    } else {
      print('❌ [GET_PLATFORM_SERVICES] No platform services data available');
      print('🔍 [GET_PLATFORM_SERVICES] Current device data: $_deviceData');
    }
    
    return platformServices;
  }

  /// Hash password for secure transmission
  String _hashPassword(String password) {
    final bytes = utf8.encode(password);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  /// Get device information
  Future<Map<String, dynamic>> _getDeviceInfo() async {
    return {
      'platform': Platform.operatingSystem,
      'version': Platform.operatingSystemVersion,
      'locale': Platform.localeName,
      'deviceType': 'mobile',
      'appVersion': '1.0.0',
    };
  }

  /// Save authentication data to persistent storage
  Future<void> _saveToStorage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      if (_authToken != null) {
        await prefs.setString(_tokenKey, _authToken!);
      }
      
      if (_userData != null) {
        await prefs.setString(_userDataKey, json.encode(_userData!));
      }
      
      if (_deviceData != null) {
        await prefs.setString(_deviceDataKey, json.encode(_deviceData!));
      }
      
      if (_serverUrl.isNotEmpty) {
        await prefs.setString(_serverConfigKey, _serverUrl);
      }
      
      print('✅ Authentication data saved to storage');
    } catch (e) {
      print('❌ Failed to save authentication data: $e');
    }
  }

  /// Make an authenticated HTTP request
  Future<Map<String, dynamic>?> makeAuthenticatedRequest(
    String method, 
    String url, {
    Map<String, dynamic>? body,
    Map<String, String>? additionalHeaders,
  }) async {
    try {
      if (!_isAuthenticated || _authToken == null) {
        throw Exception('Not authenticated - cannot make authenticated request');
      }

      final headers = getAuthHeaders();
      if (additionalHeaders != null) {
        headers.addAll(additionalHeaders);
      }

      late http.Response response;
      final uri = Uri.parse(url);

      switch (method.toUpperCase()) {
        case 'GET':
          response = await http.get(uri, headers: headers);
          break;
        case 'POST':
          response = await http.post(
            uri,
            headers: headers,
            body: body != null ? json.encode(body) : null,
          );
          break;
        case 'PUT':
          response = await http.put(
            uri,
            headers: headers,
            body: body != null ? json.encode(body) : null,
          );
          break;
        case 'DELETE':
          response = await http.delete(uri, headers: headers);
          break;
        default:
          throw Exception('Unsupported HTTP method: $method');
      }

      if (response.statusCode >= 200 && response.statusCode < 300) {
        if (response.body.isNotEmpty) {
          return json.decode(response.body) as Map<String, dynamic>;
        } else {
          return {'success': true};
        }
      } else {
        print('❌ Authenticated request failed: ${response.statusCode} - ${response.body}');
        return null;
      }
    } catch (e) {
      print('❌ Error making authenticated request: $e');
      return null;
    }
  }
}

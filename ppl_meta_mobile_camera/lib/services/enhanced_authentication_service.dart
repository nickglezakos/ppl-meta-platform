import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/auth_result.dart';
import '../../services/hybrid_service_discovery.dart';

/// Enhanced authentication service with hybrid service discovery integration
class EnhancedAuthenticationService {
  static EnhancedAuthenticationService? _instance;
  static EnhancedAuthenticationService get instance => _instance ??= EnhancedAuthenticationService._();
  EnhancedAuthenticationService._();

  static const String _tokenKey = 'ppl_meta_auth_token';
  static const String _userDataKey = 'ppl_meta_user_data';
  static const String _deviceDataKey = 'ppl_meta_device_data';
  static const String _serverConfigKey = 'ppl_meta_server_config';
  static const String _discoveredServicesKey = 'ppl_meta_discovered_services';

  final HybridServiceDiscoveryService _discoveryService = HybridServiceDiscoveryService();
  
  String? _authToken;
  Map<String, dynamic>? _userData;
  Map<String, dynamic>? _deviceData;
  String _serverUrl = '';
  bool _isAuthenticated = false;
  bool _isInitialized = false;
  List<Map<String, dynamic>> _discoveredServices = [];

  // Getters
  bool get isAuthenticated => _isAuthenticated;
  String? get authToken => _authToken;
  String? get token => _authToken;
  Map<String, dynamic>? get userData => _userData;
  Map<String, dynamic>? get deviceData => _deviceData;
  String get serverUrl => _serverUrl;
  bool get isInitialized => _isInitialized;
  List<Map<String, dynamic>> get discoveredServices => _discoveredServices;

  /// Get platform services connectivity data
  Map<String, dynamic>? get platformServices {
    return _deviceData?['platform_services'];
  }

  /// Get camera service endpoint for registration
  String? get cameraServiceEndpoint {
    // First try from platform services
    final services = platformServices?['microservices']?['cameras'];
    final endpoint = services?['endpoints']?['local'] ?? services?['endpoints']?['tailscale'];
    
    if (endpoint != null) return endpoint;
    
    // Fallback: Look in discovered services
    for (final service in _discoveredServices) {
      if (service['name'] == 'ppl-meta-cameras' && service['status'] == 'healthy') {
        final host = service['host'];
        final port = service['port'];
        final finalHost = (host == '0.0.0.0') ? 'localhost' : host;
        return 'http://$finalHost:$port';
      }
    }
    
    return null;
  }

  /// Initialize authentication service with service discovery
  Future<bool> initializeAuth() async {
    if (_isInitialized) return true;

    try {
      print('🚀 Initializing Enhanced Authentication Service...');

      // Load stored authentication data
      await _loadStoredAuthData();

      // Discover available services
      print('🔍 Discovering available services...');
      _discoveredServices = await _discoveryService.getAvailableServices();
      
      if (_discoveredServices.isNotEmpty) {
        print('📋 Found ${_discoveredServices.length} services:');
        for (final service in _discoveredServices) {
          print('   - ${service['name']}: ${service['host']}:${service['port']} (${service['status']})');
        }
        
        // Cache discovered services
        await _cacheDiscoveredServices();
      } else {
        print('⚠️ No services discovered, loading from cache...');
        await _loadCachedServices();
      }

      _isInitialized = true;
      print('✅ Enhanced Authentication Service initialized');
      return true;

    } catch (e) {
      print('❌ Failed to initialize authentication service: $e');
      _isInitialized = false;
      return false;
    }
  }

  /// Auto-login with service discovery
  Future<AuthResult> autoLogin({
    required String username,
    required String password,
  }) async {
    try {
      print('🔐 Starting auto-login with service discovery...');
      print('👤 Username: $username');

      // Ensure service is initialized
      if (!_isInitialized) {
        await initializeAuth();
      }

      // Step 1: Discover Node service
      print('🔍 Step 1: Discovering Node service...');
      final nodeURL = await _discoveryService.discoverNodeService();
      
      if (nodeURL == null) {
        print('❌ Failed to discover Node service');
        print('📋 Available services:');
        for (final service in _discoveredServices) {
          print('   - ${service['name']}: ${service['host']}:${service['port']} (${service['status']})');
        }
        return AuthResult.failure('Failed to discover Node service');
      }

      print('🎯 Node service discovered: $nodeURL');
      _serverUrl = nodeURL;

      // Step 2: Authenticate
      print('📤 Step 2: Authenticating...');
      final loginURL = '$nodeURL/api/v1/users/login';
      
      final response = await http.post(
        Uri.parse(loginURL),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: 'username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}',
      ).timeout(const Duration(seconds: 10));

      print('📥 Login response: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;

        if (token == null || token.isEmpty) {
          return AuthResult.failure('No access token received');
        }

        print('✅ Authentication successful!');
        
        // Step 3: Get platform services and user data
        print('🔍 Step 3: Getting platform services...');
        final platformData = await _getPlatformServices(nodeURL, token);
        final userData = await _getUserData(nodeURL, token);

        // Store authentication data
        await _storeAuthData(token, userData, platformData, nodeURL);

        // Update internal state
        _authToken = token;
        _userData = userData;
        _deviceData = {'platform_services': platformData};
        _isAuthenticated = true;

        print('🎉 Auto-login completed successfully!');
        
        return AuthResult.success(
          message: 'Auto-login successful',
          token: token,
          userData: userData,
          serverUrl: nodeURL,
          platformServices: platformData,
        );

      } else {
        final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
        print('❌ Authentication failed: HTTP ${response.statusCode} - $errorBody');
        return AuthResult.failure('Authentication failed: HTTP ${response.statusCode} - $errorBody');
      }

    } catch (e) {
      print('💥 Auto-login error: $e');
      return AuthResult.failure('Auto-login failed: $e');
    }
  }

  /// Get platform services configuration
  Future<Map<String, dynamic>> _getPlatformServices(String nodeURL, String token) async {
    try {
      final servicesURL = '$nodeURL/api/v1/users/platform/services';
      
      final response = await http.get(
        Uri.parse(servicesURL),
        headers: {
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        print('📋 Platform services loaded successfully');
        return data;
      } else {
        print('⚠️ Failed to get platform services: ${response.statusCode}');
        return {};
      }
    } catch (e) {
      print('⚠️ Error getting platform services: $e');
      return {};
    }
  }

  /// Get user data
  Future<Map<String, dynamic>> _getUserData(String nodeURL, String token) async {
    try {
      final profileURL = '$nodeURL/api/v1/users/profile';
      
      final response = await http.get(
        Uri.parse(profileURL),
        headers: {
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        print('👤 User data loaded successfully');
        return data;
      } else {
        print('⚠️ Failed to get user data: ${response.statusCode}');
        return {};
      }
    } catch (e) {
      print('⚠️ Error getting user data: $e');
      return {};
    }
  }

  /// Load stored authentication data
  Future<void> _loadStoredAuthData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      _authToken = prefs.getString(_tokenKey);
      
      final userDataJson = prefs.getString(_userDataKey);
      if (userDataJson != null) {
        _userData = jsonDecode(userDataJson);
      }
      
      final deviceDataJson = prefs.getString(_deviceDataKey);
      if (deviceDataJson != null) {
        _deviceData = jsonDecode(deviceDataJson);
      }
      
      _serverUrl = prefs.getString(_serverConfigKey) ?? '';
      _isAuthenticated = _authToken != null && _authToken!.isNotEmpty;

      if (_isAuthenticated) {
        print('📱 Loaded stored authentication data');
        print('🌐 Server URL: $_serverUrl');
        print('👤 User: ${_userData?['username'] ?? 'unknown'}');
      }

    } catch (e) {
      print('⚠️ Error loading stored auth data: $e');
    }
  }

  /// Store authentication data
  Future<void> _storeAuthData(
    String token,
    Map<String, dynamic> userData,
    Map<String, dynamic> platformData,
    String serverUrl,
  ) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      await prefs.setString(_tokenKey, token);
      await prefs.setString(_userDataKey, jsonEncode(userData));
      await prefs.setString(_deviceDataKey, jsonEncode({'platform_services': platformData}));
      await prefs.setString(_serverConfigKey, serverUrl);

      print('💾 Authentication data stored successfully');

    } catch (e) {
      print('⚠️ Error storing auth data: $e');
    }
  }

  /// Cache discovered services
  Future<void> _cacheDiscoveredServices() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_discoveredServicesKey, jsonEncode(_discoveredServices));
      print('💾 Cached ${_discoveredServices.length} discovered services');
    } catch (e) {
      print('⚠️ Error caching services: $e');
    }
  }

  /// Load cached services
  Future<void> _loadCachedServices() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final servicesJson = prefs.getString(_discoveredServicesKey);
      
      if (servicesJson != null) {
        _discoveredServices = List<Map<String, dynamic>>.from(jsonDecode(servicesJson));
        print('📱 Loaded ${_discoveredServices.length} cached services');
      }
    } catch (e) {
      print('⚠️ Error loading cached services: $e');
    }
  }

  /// Logout and clear stored data
  Future<AuthResult> logout() async {
    try {
      print('🚪 Logging out...');

      // Clear stored data
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_tokenKey);
      await prefs.remove(_userDataKey);
      await prefs.remove(_deviceDataKey);

      // Clear internal state
      _authToken = null;
      _userData = null;
      _deviceData = null;
      _isAuthenticated = false;

      print('✅ Logout successful');
      return AuthResult.success(message: 'Logout successful');

    } catch (e) {
      print('❌ Logout error: $e');
      return AuthResult.failure('Logout failed: $e');
    }
  }

  /// Get current user ID
  String getCurrentUserId() {
    return _userData?['id']?.toString() ?? 'unknown';
  }

  /// Check if authentication is still valid
  Future<bool> validateAuth() async {
    if (!_isAuthenticated || _authToken == null || _serverUrl.isEmpty) {
      return false;
    }

    try {
      final response = await http.get(
        Uri.parse('$_serverUrl/api/v1/users/profile'),
        headers: {
          'Authorization': 'Bearer $_authToken',
          'Accept': 'application/json',
        },
      ).timeout(const Duration(seconds: 5));

      final isValid = response.statusCode == 200;
      if (!isValid) {
        print('🔒 Authentication validation failed: ${response.statusCode}');
        _isAuthenticated = false;
      }

      return isValid;

    } catch (e) {
      print('🔒 Authentication validation error: $e');
      _isAuthenticated = false;
      return false;
    }
  }
}

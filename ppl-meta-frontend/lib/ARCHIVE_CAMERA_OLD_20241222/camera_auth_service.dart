import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:logger/logger.dart';

/// Camera Authentication Service for cross-service JWT integration
/// 
/// Handles authentication flow between Flutter app, Node service, and Cameras service
/// Implements secure token storage, automatic refresh, and error handling
class CameraAuthService extends ChangeNotifier {
  static const String _tokenKey = 'ppl_meta_jwt_token';
  static const String _refreshTokenKey = 'ppl_meta_refresh_token';
  static const String _nodeServiceBaseUrl = 'http://localhost:8001/api/v1';
  static const String _cameraServiceBaseUrl = 'http://localhost:8005/api/v1';
  
  // Secure storage for JWT tokens
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      groupId: 'group.com.pplmeta.frontend',
      accountName: 'PPL Meta Camera Auth',
    ),
  );
  
  final Logger _logger = Logger(
    printer: PrettyPrinter(
      methodCount: 2,
      errorMethodCount: 8,
      lineLength: 120,
      colors: true,
      printEmojis: true,
      printTime: true,
    ),
  );

  String? _jwtToken;
  String? _refreshToken;
  Timer? _refreshTimer;
  bool _isAuthenticated = false;
  String? _currentUserEmail;

  // Getters
  bool get isAuthenticated => _isAuthenticated;
  String? get currentUserEmail => _currentUserEmail;
  String? get jwtToken => _jwtToken;

  /// Initialize the authentication service
  /// Loads stored tokens and validates them
  Future<void> initialize() async {
    try {
      _logger.i('🔧 Initializing Camera Authentication Service...');
      
      // Load stored tokens
      _jwtToken = await _secureStorage.read(key: _tokenKey);
      _refreshToken = await _secureStorage.read(key: _refreshTokenKey);
      
      if (_jwtToken != null) {
        // Validate existing token
        if (await validateToken()) {
          _isAuthenticated = true;
          _extractUserFromToken();
          _scheduleTokenRefresh();
          _logger.i('✅ Authentication restored from stored token');
        } else {
          // Token invalid, clear storage
          await _clearStoredTokens();
          _logger.w('⚠️ Stored token invalid, cleared storage');
        }
      }
      
      notifyListeners();
    } catch (e, stackTrace) {
      _logger.e('❌ Failed to initialize auth service', error: e, stackTrace: stackTrace);
    }
  }

  /// Authenticate with Node Service using email and password
  /// Returns true if authentication successful
  Future<bool> authenticateWithNodeService(String email, String password) async {
    try {
      _logger.i('🔐 Authenticating with Node Service for user: $email');
      
      final response = await http.post(
        Uri.parse('$_nodeServiceBaseUrl/users/login'),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: {
          'username': email,
          'password': password,
        },
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Login request timed out', const Duration(seconds: 10)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['access_token'] != null) {
          _jwtToken = data['access_token'];
          _refreshToken = data['refresh_token']; // If available
          _currentUserEmail = email;
          _isAuthenticated = true;
          
          // Store tokens securely
          await _storeTokens();
          
          // Schedule automatic refresh
          _scheduleTokenRefresh();
          
          _logger.i('✅ Authentication successful for user: $email');
          notifyListeners();
          return true;
        } else {
          _logger.e('❌ No access token in response');
          return false;
        }
      } else {
        final errorData = json.decode(response.body);
        _logger.e('❌ Authentication failed: ${response.statusCode} - ${errorData['detail'] ?? 'Unknown error'}');
        return false;
      }
    } catch (e, stackTrace) {
      _logger.e('❌ Authentication error', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Refresh the current JWT token
  /// Uses refresh token if available, otherwise requires re-authentication
  Future<void> refreshToken() async {
    try {
      _logger.i('🔄 Refreshing JWT token...');
      
      if (_refreshToken != null) {
        // Use refresh token if available
        final response = await http.post(
          Uri.parse('$_nodeServiceBaseUrl/users/refresh'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $_refreshToken',
          },
        ).timeout(
          const Duration(seconds: 10),
          onTimeout: () => throw TimeoutException('Token refresh timed out', const Duration(seconds: 10)),
        );

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          _jwtToken = data['access_token'];
          
          if (data['refresh_token'] != null) {
            _refreshToken = data['refresh_token'];
          }
          
          await _storeTokens();
          _scheduleTokenRefresh();
          
          _logger.i('✅ Token refreshed successfully');
          notifyListeners();
          return;
        }
      }
      
      // If refresh failed or no refresh token, require re-authentication
      _logger.w('⚠️ Token refresh failed, user needs to re-authenticate');
      await logout();
      
    } catch (e, stackTrace) {
      _logger.e('❌ Token refresh error', error: e, stackTrace: stackTrace);
      await logout();
    }
  }

  /// Get authentication headers for API requests
  Map<String, String> getAuthHeaders() {
    if (_jwtToken == null) {
      throw Exception('No authentication token available');
    }
    
    return {
      'Authorization': 'Bearer $_jwtToken',
      'Content-Type': 'application/json',
    };
  }

  /// Validate the current JWT token
  /// Verifies token with camera service
  Future<bool> validateToken() async {
    if (_jwtToken == null) {
      return false;
    }

    try {
      // Verify token with camera service
      final response = await http.get(
        Uri.parse('$_cameraServiceBaseUrl/auth/validate'),
        headers: getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 5),
        onTimeout: () => throw TimeoutException('Token validation timed out', const Duration(seconds: 5)),
      );

      if (response.statusCode == 200) {
        _logger.d('✅ Token validation successful');
        return true;
      } else {
        _logger.w('⚠️ Token validation failed: ${response.statusCode}');
        return false;
      }
    } catch (e, stackTrace) {
      _logger.e('❌ Token validation error', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Schedule periodic token refresh without expiration-based calculations
  void _scheduleTokenRefresh() {
    _refreshTimer?.cancel();
    
    if (_jwtToken == null) return;

    _refreshTimer = Timer(const Duration(minutes: 30), () {
      _logger.i('⏰ Auto-refreshing token...');
      refreshToken();
    });

    _logger.d('⏱️ Token refresh scheduled in 30 minutes');
  }

  /// Extract user information from JWT token
  void _extractUserFromToken() {
    if (_jwtToken == null) return;

    try {
      final decodedToken = JwtDecoder.decode(_jwtToken!);
      _currentUserEmail = decodedToken['sub'] ?? decodedToken['email'];
      _logger.d('👤 Extracted user from token: $_currentUserEmail');
    } catch (e, stackTrace) {
      _logger.e('❌ Failed to extract user from token', error: e, stackTrace: stackTrace);
    }
  }

  /// Store JWT tokens securely
  Future<void> _storeTokens() async {
    try {
      if (_jwtToken != null) {
        await _secureStorage.write(key: _tokenKey, value: _jwtToken);
      }
      if (_refreshToken != null) {
        await _secureStorage.write(key: _refreshTokenKey, value: _refreshToken);
      }
      _logger.d('💾 Tokens stored securely');
    } catch (e, stackTrace) {
      _logger.e('❌ Failed to store tokens', error: e, stackTrace: stackTrace);
    }
  }

  /// Clear stored tokens from secure storage
  Future<void> _clearStoredTokens() async {
    try {
      await _secureStorage.delete(key: _tokenKey);
      await _secureStorage.delete(key: _refreshTokenKey);
      _logger.d('🗑️ Stored tokens cleared');
    } catch (e, stackTrace) {
      _logger.e('❌ Failed to clear stored tokens', error: e, stackTrace: stackTrace);
    }
  }

  /// Logout user and clear authentication state
  Future<void> logout() async {
    try {
      _logger.i('👋 Logging out user...');
      
      // Cancel refresh timer
      _refreshTimer?.cancel();
      
      // Clear stored tokens
      await _clearStoredTokens();
      
      // Reset state
      _jwtToken = null;
      _refreshToken = null;
      _isAuthenticated = false;
      _currentUserEmail = null;
      
      _logger.i('✅ Logout completed');
      notifyListeners();
    } catch (e, stackTrace) {
      _logger.e('❌ Logout error', error: e, stackTrace: stackTrace);
    }
  }

  /// Test connection to camera service with current token
  Future<bool> testCameraServiceConnection() async {
    if (!_isAuthenticated || _jwtToken == null) {
      _logger.w('⚠️ Not authenticated, cannot test camera service connection');
      return false;
    }

    try {
      _logger.i('🧪 Testing camera service connection...');
      
      final response = await http.get(
        Uri.parse('$_cameraServiceBaseUrl/cameras/'),
        headers: getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 5),
        onTimeout: () => throw TimeoutException('Camera service test timed out', const Duration(seconds: 5)),
      );

      if (response.statusCode == 200) {
        _logger.i('✅ Camera service connection successful');
        return true;
      } else {
        _logger.w('⚠️ Camera service connection failed: ${response.statusCode}');
        return false;
      }
    } catch (e, stackTrace) {
      _logger.e('❌ Camera service connection test failed', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';

/// Unified Authentication Manager for seamless Phase 2 integration
/// 
/// This class handles:
/// - Single sign-on across all services
/// - Automatic token refresh
/// - Persistent authentication state
/// - Background authentication for sync operations
class AuthManager {
  static const String _tokenKey = 'auth_token';
  static const String _userDataKey = 'user_data';
  static const String _lastLoginKey = 'last_login';
  
  final SharedPreferences _prefs;
  final Dio _dio;
  
  String? _currentToken;
  Map<String, dynamic>? _userData;
  DateTime? _tokenExpiry;
  
  // Listeners for auth state changes
  final List<VoidCallback> _authStateListeners = [];
  
  AuthManager(this._prefs) : _dio = Dio(BaseOptions(
    baseUrl: 'http://localhost:8001',
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
  )) {
    _loadStoredAuth();
  }
  
  // =============================================================================
  // PUBLIC API
  // =============================================================================
  
  /// Current authentication token
  String? get token => _currentToken;
  
  /// Current user data
  Map<String, dynamic>? get userData => _userData;
  
  /// Whether user is currently authenticated
  bool get isAuthenticated => _currentToken != null && !_isTokenExpired;
  
  /// Whether token is expired (with 5 minute buffer)
  bool get _isTokenExpired {
    if (_tokenExpiry == null) return true;
    return DateTime.now().isAfter(_tokenExpiry!.subtract(const Duration(minutes: 5)));
  }
  
  /// Add listener for authentication state changes
  void addAuthStateListener(VoidCallback listener) {
    _authStateListeners.add(listener);
  }
  
  /// Remove listener for authentication state changes
  void removeAuthStateListener(VoidCallback listener) {
    _authStateListeners.remove(listener);
  }
  
  /// Initialize authentication on app startup
  Future<bool> initializeAuth() async {
    try {
      // Load stored authentication
      await _loadStoredAuth();
      
      // Check if we have a valid token
      if (_currentToken != null) {
        // Verify token is still valid with the server
        final isValid = await _verifyToken();
        if (isValid) {
          _notifyAuthStateChange();
          return true;
        } else {
          // Token is invalid, clear it
          await clearAuth();
        }
      }
      
      // Attempt automatic login if we have stored credentials
      return await _attemptAutoLogin();
    } catch (e) {
      debugPrint('Auth initialization failed: $e');
      return false;
    }
  }
  
  /// Login with email and password
  Future<AuthResult> login(String email, String password) async {
    try {
      final response = await _dio.post(
        '/api/v1/users/login',
        data: FormData.fromMap({
          'username': email,
          'password': password,
        }),
        options: Options(
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        ),
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        _currentToken = data['access_token'];
        _userData = data['user'];
        
        // Parse token expiry
        _parseTokenExpiry(_currentToken!);
        
        // Store authentication data
        await _storeAuth(email, password);
        
        _notifyAuthStateChange();
        
        return AuthResult(success: true, token: _currentToken);
      } else {
        return AuthResult(success: false, error: 'Login failed');
      }
    } on DioException catch (e) {
      return AuthResult(success: false, error: e.message ?? 'Network error');
    } catch (e) {
      return AuthResult(success: false, error: e.toString());
    }
  }
  
  /// Logout and clear all authentication data
  Future<void> logout() async {
    await clearAuth();
    _notifyAuthStateChange();
  }
  
  /// Clear all authentication data
  Future<void> clearAuth() async {
    _currentToken = null;
    _userData = null;
    _tokenExpiry = null;
    
    await _prefs.remove(_tokenKey);
    await _prefs.remove(_userDataKey);
    await _prefs.remove(_lastLoginKey);
  }
  
  /// Get current valid token, refreshing if necessary
  Future<String?> getValidToken() async {
    if (_currentToken == null) {
      // Try to initialize auth
      await initializeAuth();
      return _currentToken;
    }
    
    if (_isTokenExpired) {
      // Try to refresh token
      final refreshed = await _attemptAutoLogin();
      if (!refreshed) {
        return null;
      }
    }
    
    return _currentToken;
  }
  
  // =============================================================================
  // PRIVATE METHODS
  // =============================================================================
  
  /// Load stored authentication from SharedPreferences
  Future<void> _loadStoredAuth() async {
    try {
      _currentToken = _prefs.getString(_tokenKey);
      
      final userDataString = _prefs.getString(_userDataKey);
      if (userDataString != null) {
        _userData = json.decode(userDataString);
      }
      
      if (_currentToken != null) {
        _parseTokenExpiry(_currentToken!);
      }
    } catch (e) {
      debugPrint('Error loading stored auth: $e');
    }
  }
  
  /// Store authentication data persistently
  Future<void> _storeAuth(String email, String password) async {
    try {
      await _prefs.setString(_tokenKey, _currentToken!);
      
      if (_userData != null) {
        await _prefs.setString(_userDataKey, json.encode(_userData));
      }
      
      // Store login credentials for auto-login (encrypted in production)
      await _prefs.setString(_lastLoginKey, json.encode({
        'email': email,
        'password': password, // In production, this should be encrypted or use refresh tokens
        'timestamp': DateTime.now().toIso8601String(),
      }));
    } catch (e) {
      debugPrint('Error storing auth: $e');
    }
  }
  
  /// Parse token expiry from JWT token
  void _parseTokenExpiry(String token) {
    try {
      final parts = token.split('.');
      if (parts.length == 3) {
        final payload = parts[1];
        // Add padding if needed
        final normalizedPayload = payload.padRight((payload.length + 3) & ~3, '=');
        final decoded = base64.decode(normalizedPayload);
        final payloadMap = json.decode(utf8.decode(decoded));
        
        if (payloadMap['exp'] != null) {
          _tokenExpiry = DateTime.fromMillisecondsSinceEpoch(payloadMap['exp'] * 1000);
        }
      }
    } catch (e) {
      debugPrint('Error parsing token expiry: $e');
      // Set a default expiry of 1 hour from now
      _tokenExpiry = DateTime.now().add(const Duration(hours: 1));
    }
  }
  
  /// Verify token with server
  Future<bool> _verifyToken() async {
    if (_currentToken == null) return false;
    
    try {
      final response = await _dio.get(
        '/api/v1/health',
        options: Options(
          headers: {'Authorization': 'Bearer $_currentToken'},
        ),
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Attempt automatic login using stored credentials
  Future<bool> _attemptAutoLogin() async {
    try {
      final lastLoginString = _prefs.getString(_lastLoginKey);
      if (lastLoginString == null) return false;
      
      final lastLogin = json.decode(lastLoginString);
      final email = lastLogin['email'];
      final password = lastLogin['password'];
      
      if (email == null || password == null) return false;
      
      final result = await login(email, password);
      return result.success;
    } catch (e) {
      debugPrint('Auto-login failed: $e');
      return false;
    }
  }
  
  /// Notify all listeners of auth state change
  void _notifyAuthStateChange() {
    for (final listener in _authStateListeners) {
      try {
        listener();
      } catch (e) {
        debugPrint('Error in auth state listener: $e');
      }
    }
  }
}

/// Result of authentication operation
class AuthResult {
  final bool success;
  final String? token;
  final String? error;
  
  const AuthResult({
    required this.success,
    this.token,
    this.error,
  });
}

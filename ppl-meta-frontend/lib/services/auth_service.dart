import 'package:shared_preferences/shared_preferences.dart';
import 'auth_manager.dart';

/// Simple AuthService wrapper for backwards compatibility
/// 
/// Provides a simple interface to get the current authentication token
/// Integrates with AuthManager for persistent authentication
class AuthService {
  static AuthManager? _authManager;
  static String? _cachedToken;
  
  /// Initialize the auth service with AuthManager
  static Future<void> initialize() async {
    if (_authManager == null) {
      final prefs = await SharedPreferences.getInstance();
      _authManager = AuthManager(prefs);
      await _authManager!.initializeAuth();
    }
  }
  
  /// Set the authentication token
  void setToken(String token) {
    _cachedToken = token;
  }
  
  /// Get the currently stored authentication token
  /// Returns null if no token is available
  Future<String?> getStoredToken() async {
    // Prefer in-memory AuthManager token when already loaded
    if (_authManager != null) {
      final token = await _authManager!.getValidToken();
      if (token != null) {
        return token;
      }
    }

    // Read the shared prefs key directly. Avoid AuthManager.initializeAuth()
    // here — its old localhost health check cleared auth_token on failure and
    // logged users out after visiting /triggers.
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('auth_token');
      if (token != null && token.isNotEmpty) {
        _cachedToken = token;
        return token;
      }
    } catch (_) {}

    return _cachedToken;
  }
  
  /// Clear the stored token
  Future<void> clearToken() async {
    _cachedToken = null;
    if (_authManager != null) {
      await _authManager!.clearAuth();
    }
  }
  
  /// Check if user is authenticated
  bool get isAuthenticated {
    return _authManager?.isAuthenticated ?? _cachedToken != null;
  }
  
  /// Get the AuthManager instance
  Future<AuthManager?> getAuthManager() async {
    if (_authManager == null) {
      await initialize();
    }
    return _authManager;
  }
}

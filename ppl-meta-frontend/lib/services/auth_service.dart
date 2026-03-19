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
    // Try to get from AuthManager first
    if (_authManager != null) {
      final token = await _authManager!.getValidToken();
      if (token != null) {
        return token;
      }
    }
    
    // Initialize AuthManager if not done yet
    if (_authManager == null) {
      await initialize();
      final token = await _authManager!.getValidToken();
      if (token != null) {
        return token;
      }
    }
    
    // Fallback to cached token
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

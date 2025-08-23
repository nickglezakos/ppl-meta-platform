import 'package:shared_preferences/shared_preferences.dart';

/// Secure token management for PPL Meta authentication
class TokenManager {
  static const String _tokenKey = 'ppl_meta_auth_token';
  static const String _tokenTypeKey = 'ppl_meta_token_type';
  static const String _expiryKey = 'ppl_meta_token_expiry';
  static const String _userIdKey = 'ppl_meta_user_id';

  /// Save authentication token securely
  static Future<void> saveToken({
    required String token,
    String tokenType = 'bearer',
    DateTime? expiryTime,
    int? userId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_tokenTypeKey, tokenType);
    
    if (expiryTime != null) {
      await prefs.setString(_expiryKey, expiryTime.toIso8601String());
    }
    
    if (userId != null) {
      await prefs.setInt(_userIdKey, userId);
    }
  }

  /// Get stored authentication token
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    
    // Check if token is expired
    if (token != null && await isTokenExpired()) {
      await clearToken();
      return null;
    }
    
    return token;
  }

  /// Get token type (usually 'bearer')
  static Future<String?> getTokenType() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenTypeKey);
  }

  /// Get stored user ID
  static Future<int?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_userIdKey);
  }

  /// Check if user is authenticated
  static Future<bool> isAuthenticated() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }

  /// Check if token is expired
  static Future<bool> isTokenExpired() async {
    final prefs = await SharedPreferences.getInstance();
    final expiryString = prefs.getString(_expiryKey);
    
    if (expiryString == null) {
      return false; // No expiry set, assume valid
    }
    
    final expiry = DateTime.parse(expiryString);
    return DateTime.now().isAfter(expiry);
  }

  /// Get authorization header for API requests
  static Future<Map<String, String>?> getAuthHeaders() async {
    final token = await getToken();
    final tokenType = await getTokenType();
    
    if (token == null) return null;
    
    return {
      'Authorization': '${tokenType ?? 'Bearer'} $token',
    };
  }

  /// Clear all stored authentication data
  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    
    await prefs.remove(_tokenKey);
    await prefs.remove(_tokenTypeKey);
    await prefs.remove(_expiryKey);
    await prefs.remove(_userIdKey);
  }

  /// Get token info for debugging
  static Future<Map<String, dynamic>> getTokenInfo() async {
    final prefs = await SharedPreferences.getInstance();
    
    return {
      'has_token': prefs.getString(_tokenKey) != null,
      'token_type': prefs.getString(_tokenTypeKey),
      'expiry': prefs.getString(_expiryKey),
      'user_id': prefs.getInt(_userIdKey),
      'is_expired': await isTokenExpired(),
    };
  }
}

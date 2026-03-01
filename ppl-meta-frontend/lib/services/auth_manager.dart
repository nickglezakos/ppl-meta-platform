import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:dio/dio.dart';

/// Unified Authentication Manager for seamless Phase 2 integration
///
/// This class handles:
/// - Single sign-on across all services
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

  final List<VoidCallback> _authStateListeners = [];

  AuthManager(this._prefs)
      : _dio = Dio(
          BaseOptions(
            baseUrl: 'http://localhost/api/node',
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 30),
          ),
        ) {
    _loadStoredAuth();
  }

  String? get token => _currentToken;

  Map<String, dynamic>? get userData => _userData;

  bool get isAuthenticated => _currentToken != null;

  void addAuthStateListener(VoidCallback listener) {
    _authStateListeners.add(listener);
  }

  void removeAuthStateListener(VoidCallback listener) {
    _authStateListeners.remove(listener);
  }

  Future<bool> initializeAuth() async {
    try {
      await _loadStoredAuth();

      if (_currentToken != null) {
        final isValid = await _verifyToken();
        if (isValid) {
          _notifyAuthStateChange();
          return true;
        }

        await clearAuth();
      }

      return await _attemptAutoLogin();
    } catch (e) {
      debugPrint('Auth initialization failed: $e');
      return false;
    }
  }

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

        await _storeAuth(email, password);
        _notifyAuthStateChange();

        return AuthResult(success: true, token: _currentToken);
      }

      return const AuthResult(success: false, error: 'Login failed');
    } on DioException catch (e) {
      return AuthResult(success: false, error: e.message ?? 'Network error');
    } catch (e) {
      return AuthResult(success: false, error: e.toString());
    }
  }

  Future<void> logout() async {
    await clearAuth();
    _notifyAuthStateChange();
  }

  Future<void> clearAuth() async {
    _currentToken = null;
    _userData = null;

    await _prefs.remove(_tokenKey);
    await _prefs.remove(_userDataKey);
    await _prefs.remove(_lastLoginKey);
  }

  Future<String?> getValidToken() async {
    if (_currentToken == null) {
      await initializeAuth();
    }
    return _currentToken;
  }

  Future<void> _loadStoredAuth() async {
    try {
      _currentToken = _prefs.getString(_tokenKey);

      final userDataString = _prefs.getString(_userDataKey);
      if (userDataString != null && userDataString.isNotEmpty) {
        _userData = json.decode(userDataString) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('Error loading stored auth: $e');
    }
  }

  Future<void> _storeAuth(String email, String password) async {
    try {
      if (_currentToken != null) {
        await _prefs.setString(_tokenKey, _currentToken!);
      }

      if (_userData != null) {
        await _prefs.setString(_userDataKey, json.encode(_userData));
      }

      await _prefs.setString(
        _lastLoginKey,
        json.encode({
          'email': email,
          'password': password,
          'timestamp': DateTime.now().toIso8601String(),
        }),
      );
    } catch (e) {
      debugPrint('Error storing auth: $e');
    }
  }

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
    } catch (_) {
      return false;
    }
  }

  Future<bool> _attemptAutoLogin() async {
    try {
      final lastLoginString = _prefs.getString(_lastLoginKey);
      if (lastLoginString == null || lastLoginString.isEmpty) return false;

      final lastLogin = json.decode(lastLoginString) as Map<String, dynamic>;
      final email = lastLogin['email'] as String?;
      final password = lastLogin['password'] as String?;

      if (email == null || password == null) return false;

      final result = await login(email, password);
      return result.success;
    } catch (e) {
      debugPrint('Auto-login failed: $e');
      return false;
    }
  }

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

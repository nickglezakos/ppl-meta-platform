import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Slim Plan A auth: gateway login + JWT persistence (no camera registration).
class AuthService {
  AuthService._();
  static final AuthService instance = AuthService._();

  static const _tokenKey = 'authenticator_auth_token';
  static const _serverKey = 'authenticator_server_url';
  static const _userKey = 'authenticator_user_data';

  String? _token;
  String _serverUrl = '';
  Map<String, dynamic>? _userData;
  bool _authenticated = false;

  String? get authToken => _token;
  String get serverUrl => _serverUrl;
  Map<String, dynamic>? get userData => _userData;
  bool get isAuthenticated => _authenticated;
  String? get userEmail =>
      _userData?['email']?.toString() ?? _userData?['username']?.toString();

  Future<void> loadPersisted() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    _serverUrl = prefs.getString(_serverKey) ?? '';
    final raw = prefs.getString(_userKey);
    if (raw != null) {
      _userData = jsonDecode(raw) as Map<String, dynamic>;
    }
    if (_token == null || _token!.isEmpty || _serverUrl.isEmpty) {
      return;
    }
    // Optimistic local session so cold start can paint UI even offline.
    _authenticated = true;
    final ok = await validateToken();
    if (ok) return;
    // validateToken returns false for both auth failure and network errors.
    // Only force logout when the install is reachable (token truly dead).
    try {
      final probe = await http
          .get(Uri.parse('$_serverUrl/health'))
          .timeout(const Duration(seconds: 3));
      if (probe.statusCode < 500) {
        await logout();
      }
    } catch (_) {
      _authenticated = true;
    }
  }

  Future<bool> login({
    required String serverUrl,
    required String username,
    required String password,
  }) async {
    final base = serverUrl.replaceAll(RegExp(r'/$'), '');
    final uri = Uri.parse('$base/api/v1/users/login');
    final response = await http
        .post(
          uri,
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
          },
          body:
              'username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}',
        )
        .timeout(const Duration(seconds: 12));

    if (response.statusCode != 200) {
      throw Exception('Login failed (HTTP ${response.statusCode}): ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final token = data['access_token'] as String?;
    if (token == null || token.isEmpty) {
      throw Exception('No access token in login response');
    }

    _token = token;
    _serverUrl = base;
    _userData = {
      'email': username,
      'username': username,
      ...(data['user'] is Map<String, dynamic>
          ? data['user'] as Map<String, dynamic>
          : <String, dynamic>{}),
    };
    _authenticated = true;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_serverKey, base);
    await prefs.setString(_userKey, jsonEncode(_userData));
    return true;
  }

  Future<bool> validateToken() async {
    if (_token == null || _serverUrl.isEmpty) return false;
    try {
      final response = await http
          .get(
            Uri.parse('$_serverUrl/api/v1/users/me'),
            headers: {
              'Accept': 'application/json',
              'Authorization': 'Bearer $_token',
            },
          )
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data is Map<String, dynamic>) {
          _userData = {...?_userData, ...data};
        }
        return true;
      }
      // Some installs expose profile instead of me
      final profile = await http
          .get(
            Uri.parse('$_serverUrl/api/v1/users/profile'),
            headers: {
              'Accept': 'application/json',
              'Authorization': 'Bearer $_token',
            },
          )
          .timeout(const Duration(seconds: 8));
      return profile.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() async {
    _token = null;
    _authenticated = false;
    _userData = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
  }

  Map<String, String> authHeaders() => {
        'Accept': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };
}

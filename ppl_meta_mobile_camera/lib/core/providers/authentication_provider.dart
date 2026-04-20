import 'package:flutter/foundation.dart';
import '../services/authentication_service.dart';
import '../services/streaming_service.dart';
import '../../services/device_identifier_service.dart';

/// Authentication provider for managing authentication state
class AuthenticationProvider extends ChangeNotifier {
  final AuthenticationService _authService = AuthenticationService.instance;
  final StreamingService _streamingService = StreamingService.instance;
  final DeviceIdentifierService _deviceService = DeviceIdentifierService();

  // Authentication state
  bool _isAuthenticated = false;
  bool _isLoading = false;
  String? _error;
  Map<String, dynamic>? _userData;
  Map<String, dynamic>? _deviceData;
  String? _serverUrl;

  // Camera registration state
  bool _isCameraRegistered = false;

  // Server connection state
  bool _isServerOnline = false;
  Map<String, dynamic>? _serverInfo;
  DateTime? _lastConnectionCheck;

  // Getters
  /// Check if user is authenticated
  bool get isAuthenticated {
    // Sync with authentication service to ensure consistency
    final serviceAuth = _authService.isAuthenticated;
    if (_isAuthenticated != serviceAuth) {
      print('🔑 [AUTH_DEBUG] Authentication state mismatch detected - Provider: $_isAuthenticated, Service: $serviceAuth');
      _isAuthenticated = serviceAuth;
    }
    return _isAuthenticated;
  }
  bool get isLoading => _isLoading;
  String? get error => _error;
  Map<String, dynamic>? get userData => _userData;
  Map<String, dynamic>? get deviceData => _deviceData;
  String? get serverUrl => _serverUrl;
  bool get isCameraRegistered => _isCameraRegistered;
  bool get isServerOnline => _isServerOnline;
  Map<String, dynamic>? get serverInfo => _serverInfo;
  
  /// Get access token for API requests
  String? get accessToken => _authService.authToken;
  String? get authToken => _authService.authToken;  // Alias
  String? get token => _authService.authToken;      // Alias for common usage
  
  /// Get camera service endpoint URL
  String? get camerasServiceUrl => _authService.cameraServiceEndpoint;
  String? get baseUrl => _authService.cameraServiceEndpoint ?? _serverUrl;  // Alias for common usage

  /// Initialize authentication provider
  Future<void> initializeAuth() async {
    _setLoading(true);
    _clearError();

    try {
      // Initialize authentication service
      final authInitialized = await _authService.initializeAuth();
      
      if (authInitialized) {
        _isAuthenticated = _authService.isAuthenticated;
        _userData = _authService.userData;
        _deviceData = _authService.deviceData;
        _serverUrl = _authService.serverUrl;

        print('🔑 [AUTH_DEBUG] Init - Auth service isAuthenticated: ${_authService.isAuthenticated}');
        print('🔑 [AUTH_DEBUG] Init - Provider isAuthenticated set to: $_isAuthenticated');

        // Initialize streaming service if authenticated
        if (_isAuthenticated && _serverUrl != null) {
          await _initializeStreamingService();
          
          // Check if camera is already registered (has stored UUID)
          final storedUuid = await _deviceService.getStoredCameraUuid();
          if (storedUuid != null && storedUuid.isNotEmpty) {
            print('✅ [CAMERA_RESTORATION] Found stored camera UUID: $storedUuid');
            _isCameraRegistered = true;
            print('✅ [CAMERA_RESTORATION] Camera registration status set to true - skipping registration');
          } else {
            print('ℹ️  [CAMERA_REGISTRATION] No stored camera UUID - registration required');
            _isCameraRegistered = false;
          }
        }

        // Check server connection with delay to allow services to start
        if (_serverUrl != null) {
          // Add a small delay and retry logic for server connection check
          await Future.delayed(const Duration(milliseconds: 500));
          await _checkServerConnectionWithRetry();
        }
      } else {
        // Authentication service initialized but no stored credentials
        // Still check for server if we have a URL
        if (_authService.serverUrl.isNotEmpty) {
          _serverUrl = _authService.serverUrl;
          await Future.delayed(const Duration(milliseconds: 500));
          await _checkServerConnectionWithRetry();
        }
      }

      notifyListeners();
    } catch (e) {
      print('Authentication initialization error: $e');
      _setError('Failed to initialize authentication: ${e.toString()}');
    } finally {
      _setLoading(false);
    }
  }

  /// Login with credentials
  Future<bool> login({
    String? serverUrl,
    required String username,
    required String password,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      print('Attempting login for user: $username');
      
      final result = await _authService.login(
        serverUrl: serverUrl,
        username: username,
        password: password,
      );

      if (result.success) {
        _isAuthenticated = true;
        _userData = _authService.userData;
        _deviceData = _authService.deviceData;
        _serverUrl = _authService.serverUrl;

        print('🔑 [AUTH_DEBUG] Authentication state set to true');
        print('🔑 [AUTH_DEBUG] Auth service isAuthenticated: ${_authService.isAuthenticated}');
        print('🔑 [AUTH_DEBUG] Provider isAuthenticated: $_isAuthenticated');

        // Initialize streaming service
        await _initializeStreamingService();

        // Check if camera is already registered (has stored UUID)
        final storedUuid = await _deviceService.getStoredCameraUuid();
        if (storedUuid != null && storedUuid.isNotEmpty) {
          print('✅ [CAMERA_RESTORATION] Found stored camera UUID: $storedUuid');
          _isCameraRegistered = true;
          print('✅ [CAMERA_RESTORATION] Camera registration status set to true - skipping registration');
        } else {
          print('ℹ️  [CAMERA_REGISTRATION] No stored camera UUID - registration required');
          _isCameraRegistered = false;
        }

        print('🔑 [AUTH_DEBUG] Before server connection check - isAuthenticated: $_isAuthenticated');
        
        // Re-check server connection after successful login
        if (_serverUrl != null) {
          await _checkServerConnectionWithRetry();
        }

        print('🔑 [AUTH_DEBUG] After server connection check - isAuthenticated: $_isAuthenticated');
        print('🔑 [AUTH_DEBUG] Auth service isAuthenticated: ${_authService.isAuthenticated}');

        print('Login successful for user: $username');
        print('User data: ${_userData?['username'] ?? 'No username'}');
        notifyListeners();
        return true;
      } else {
        _setError(result.error ?? 'Login failed');
        return false;
      }
    } catch (e) {
      print('Login error: $e');
      _setError('Login error: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }

  /// Register device
  Future<bool> registerDevice({
    required String serverUrl,
    required String deviceName,
    required String deviceType,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      final result = await _authService.registerDevice(
        serverUrl: serverUrl,
        deviceName: deviceName,
        deviceType: deviceType,
      );

      if (result.success) {
        _isAuthenticated = true;
        _userData = _authService.userData;
        _deviceData = _authService.deviceData;
        _serverUrl = _authService.serverUrl;

        // Initialize streaming service
        await _initializeStreamingService();

        notifyListeners();
        return true;
      } else {
        _setError(result.error ?? 'Registration failed');
        return false;
      }
    } catch (e) {
      _setError('Registration error: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }

  /// Logout
  Future<void> logout() async {
    _setLoading(true);

    try {
      // Disconnect streaming service
      await _streamingService.disconnect();

      // Logout from authentication service
      await _authService.logout();

      // Clear state
      _isAuthenticated = false;
      _isCameraRegistered = false;
      _userData = null;
      _deviceData = null;
      _serverUrl = null;
      _isServerOnline = false;
      _serverInfo = null;

      notifyListeners();
    } catch (e) {
      _setError('Logout error: ${e.toString()}');
    } finally {
      _setLoading(false);
    }
  }

  /// Refresh authentication token
  Future<bool> refreshToken() async {
    try {
      final success = await _authService.refreshToken();
      
      if (!success) {
        // Token refresh failed, logout user
        await logout();
        _setError('Session expired. Please login again.');
      }

      return success;
    } catch (e) {
      _setError('Token refresh error: ${e.toString()}');
      return false;
    }
  }

  /// Check server connection with retry logic
  Future<void> _checkServerConnectionWithRetry() async {
    const maxRetries = 3;
    const retryDelay = Duration(seconds: 2);
    
    for (int i = 0; i < maxRetries; i++) {
      try {
        final urlToCheck = _serverUrl;
        if (urlToCheck == null) return;

        print('Checking server connection (attempt ${i + 1}/$maxRetries): $urlToCheck');
        final isOnline = await _authService.testServerConnection(urlToCheck);
        
        _isServerOnline = isOnline;
        _serverInfo = isOnline ? {'status': 'online', 'url': urlToCheck} : null;
        _lastConnectionCheck = DateTime.now();

        if (isOnline) {
          print('✅ Server connection successful');
          _clearError();
          notifyListeners();
          return; // Success, no need to retry
        } else {
          print('❌ Server connection failed (attempt ${i + 1}/$maxRetries)');
          if (i < maxRetries - 1) {
            await Future.delayed(retryDelay);
          }
        }
      } catch (e) {
        print('Server connection check error (attempt ${i + 1}/$maxRetries): $e');
        if (i < maxRetries - 1) {
          await Future.delayed(retryDelay);
        }
      }
    }
    
    // All retries failed
    _isServerOnline = false;
    _serverInfo = null;
    print('🔴 Server connection failed after $maxRetries attempts');
    notifyListeners();
  }

  /// Check server connection
  Future<void> checkServerConnection([String? serverUrl]) async {
    try {
      final urlToCheck = serverUrl ?? _serverUrl;
      if (urlToCheck == null) return;

      final isOnline = await _authService.testServerConnection(urlToCheck);
      
      _isServerOnline = isOnline;
      _serverInfo = isOnline ? {'status': 'online', 'url': urlToCheck} : null;
      _lastConnectionCheck = DateTime.now();

      if (!isOnline) {
        _setError('Server connection failed - server not reachable');
      } else {
        _clearError();
      }

      notifyListeners();
    } catch (e) {
      _isServerOnline = false;
      _setError('Connection check failed: ${e.toString()}');
      notifyListeners();
    }
  }

  /// Manually refresh server connection (for UI refresh)
  Future<void> refreshServerConnection() async {
    if (_serverUrl != null) {
      await _checkServerConnectionWithRetry();
    }
  }

  /// Connect to streaming server
  Future<bool> connectToStreamingServer() async {
    if (!_isAuthenticated || _serverUrl == null) {
      _setError('Authentication required');
      return false;
    }

    _setLoading(true);

    try {
      // Initialize streaming service (sets server URL and auth headers)
      await _initializeStreamingService();

      // Mobile cameras use HTTP POST for frames, not WebSocket.
      // Just report success after initialization.
      print('ℹ️ Streaming service initialized (HTTP mode, no WebSocket needed)');

      notifyListeners();
      return true;
    } catch (e) {
      _setError('Streaming connection error: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }

  /// Disconnect from streaming server
  Future<void> disconnectFromStreamingServer() async {
    try {
      await _streamingService.disconnect();
      notifyListeners();
    } catch (e) {
      _setError('Streaming disconnection error: ${e.toString()}');
    }
  }

  /// Get authentication headers for API requests
  Map<String, String> getAuthHeaders() {
    return _authService.getAuthHeaders();
  }

  /// Get device information
  String getDeviceId() {
    return _deviceData?['deviceId'] ?? 'unknown';
  }

  /// Get user display name
  String getUserDisplayName() {
    if (_userData == null) return 'Unknown User';
    
    final username = _userData!['username'] as String?;
    final deviceName = _deviceData?['deviceName'] as String?;
    
    if (username != null && username.isNotEmpty) {
      return username;
    } else if (deviceName != null && deviceName.isNotEmpty) {
      return deviceName;
    } else {
      return 'Camera Device';
    }
  }

  /// Get connection status
  Map<String, dynamic> getConnectionStatus() {
    return {
      'isAuthenticated': _isAuthenticated,
      'isServerOnline': _isServerOnline,
      'isStreamingConnected': _streamingService.isConnected,
      'serverUrl': _serverUrl,
      'lastConnectionCheck': _lastConnectionCheck?.toIso8601String(),
      'deviceId': getDeviceId(),
      'userName': getUserDisplayName(),
    };
  }

  /// Initialize streaming service with authentication
  Future<void> _initializeStreamingService() async {
    if (_serverUrl == null) return;

    // Route streaming through the gateway (port 8080) on the same host.
    // This ensures connectivity on mobile hotspots where the cameras
    // service port (8005) may not be directly reachable.
    final uri = Uri.tryParse(_serverUrl!);
    String streamingServerUrl = _serverUrl!; // fallback
    
    if (uri != null) {
      streamingServerUrl = 'http://${uri.host}:8080';
      print('🎯 [STREAMING_INIT] Using gateway URL for streaming: $streamingServerUrl');
    } else {
      // Legacy fallback: try cameras service from platform services
      final platformServices = _authService.platformServices;
      if (platformServices != null) {
        final microservices = platformServices['microservices'] as Map<String, dynamic>?;
        final camerasService = microservices?['cameras'] as Map<String, dynamic>?;
        final camerasEndpoint = camerasService?['endpoints']?['local'] as String?;
        
        if (camerasEndpoint != null) {
          streamingServerUrl = camerasEndpoint;
          print('⚠️ [STREAMING_INIT] Fallback to cameras service URL: $streamingServerUrl');
        }
      }
    }

    await _streamingService.initializeStreaming(
      serverUrl: streamingServerUrl,
      authHeaders: getAuthHeaders(),
      deviceId: getDeviceId(),  // Pass device ID for mobile camera streaming
    );
  }

  /// Set loading state
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  /// Set error state
  void _setError(String error) {
    _error = error;
    notifyListeners();
  }

  /// Clear error state
  void _clearError() {
    _error = null;
  }

  /// Auto-refresh token periodically
  void startTokenRefreshTimer() {
    if (!_isAuthenticated) return;

    // Refresh token every 30 minutes
    Future.doWhile(() async {
      if (!_isAuthenticated) return false;
      
      await Future.delayed(Duration(minutes: 30));
      
      if (_isAuthenticated) {
        await refreshToken();
      }
      
      return _isAuthenticated;
    });
  }

  /// Auto-check server connection periodically
  void startConnectionCheckTimer() {
    // Check connection every 5 minutes
    Future.doWhile(() async {
      await Future.delayed(Duration(minutes: 5));
      
      if (_serverUrl != null) {
        await checkServerConnection();
      }
      
      return true; // Continue checking
    });
  }

  /// Set camera registration status
  void setCameraRegistered(bool registered) {
    _isCameraRegistered = registered;
    notifyListeners();
  }

  /// Check if camera registration is required
  bool get requiresCameraRegistration => _isAuthenticated && !_isCameraRegistered;
}

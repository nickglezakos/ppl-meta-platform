import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';
import 'camera_auth_service.dart';

/// Camera Service for PPL Meta Cameras microservice integration
/// 
/// Provides high-level camera management, streaming, and snapshot capabilities
/// Relies on CameraAuthService for authentication
class CameraService extends ChangeNotifier {
  static const String _baseUrl = 'http://localhost:8005/api/v1';
  
  final CameraAuthService _authService;
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

  List<Camera> _availableCameras = [];
  List<Camera> _activeCameras = [];
  bool _isLoading = false;
  String? _lastError;

  // Getters
  List<Camera> get availableCameras => _availableCameras;
  List<Camera> get activeCameras => _activeCameras;
  bool get isLoading => _isLoading;
  String? get lastError => _lastError;
  bool get isAuthenticated => _authService.isAuthenticated;

  CameraService(this._authService) {
    _authService.addListener(_onAuthStateChanged);
  }

  /// Handle authentication state changes
  void _onAuthStateChanged() {
    if (!_authService.isAuthenticated) {
      // Clear camera data when user logs out
      _availableCameras.clear();
      _activeCameras.clear();
      notifyListeners();
    }
  }

  /// Detect available cameras and optionally save to database
  Future<bool> detectCameras({bool saveToDb = true}) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _setLoading(true);
      _logger.i('🔍 Detecting cameras...');

      final response = await http.post(
        Uri.parse('$_baseUrl/cameras/detect?save_to_db=$saveToDb'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException('Camera detection timed out', const Duration(seconds: 15)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Camera detection completed: ${data['status']}');
        
        // Refresh camera list after detection
        await getCameras();
        return true;
      } else {
        _lastError = 'Camera detection failed: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Camera detection error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    } finally {
      _setLoading(false);
    }
  }

  /// Get list of all cameras from database
  Future<bool> getCameras() async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _setLoading(true);
      _logger.i('📋 Fetching camera list...');

      final response = await http.get(
        Uri.parse('$_baseUrl/cameras/'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Get cameras timed out', const Duration(seconds: 10)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Parse cameras list (adapt based on actual API response structure)
        if (data['cameras'] != null) {
          _availableCameras = (data['cameras'] as List)
              .map((camera) => Camera.fromJson(camera))
              .toList();
        } else {
          _availableCameras = [];
        }
        
        _logger.i('✅ Found ${_availableCameras.length} cameras');
        notifyListeners();
        return true;
      } else {
        _lastError = 'Failed to get cameras: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get cameras error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    } finally {
      _setLoading(false);
    }
  }

  /// Get list of active camera connections
  Future<bool> getActiveCameras() async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('📋 Fetching active cameras...');

      final response = await http.get(
        Uri.parse('$_baseUrl/cameras/active'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Get active cameras timed out', const Duration(seconds: 10)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Parse active cameras list
        if (data['active_cameras'] != null) {
          _activeCameras = (data['active_cameras'] as List)
              .map((camera) => Camera.fromJson(camera))
              .toList();
        } else {
          _activeCameras = [];
        }
        
        _logger.i('✅ Found ${_activeCameras.length} active cameras');
        notifyListeners();
        return true;
      } else {
        _lastError = 'Failed to get active cameras: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get active cameras error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Connect to a specific camera
  Future<bool> connectCamera(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🔌 Connecting to camera: $deviceId');

      final response = await http.post(
        Uri.parse('$_baseUrl/cameras/$deviceId/connect'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException('Camera connection timed out', const Duration(seconds: 15)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Connected to camera $deviceId: ${data['status']}');
        
        // Refresh active cameras list
        await getActiveCameras();
        return true;
      } else {
        _lastError = 'Failed to connect camera $deviceId: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Camera connection error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Disconnect from a specific camera
  Future<bool> disconnectCamera(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🔌 Disconnecting from camera: $deviceId');

      final response = await http.post(
        Uri.parse('$_baseUrl/cameras/$deviceId/disconnect'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Camera disconnection timed out', const Duration(seconds: 10)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Disconnected from camera $deviceId: ${data['status']}');
        
        // Refresh active cameras list
        await getActiveCameras();
        return true;
      } else {
        _lastError = 'Failed to disconnect camera $deviceId: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Camera disconnection error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Get camera information
  Future<CameraInfo?> getCameraInfo(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.i('ℹ️ Getting camera info for: $deviceId');

      final response = await http.get(
        Uri.parse('$_baseUrl/cameras/$deviceId/info'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Get camera info timed out', const Duration(seconds: 10)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Got camera info for $deviceId');
        return CameraInfo.fromJson(data);
      } else {
        _lastError = 'Failed to get camera info for $deviceId: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get camera info error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Disconnect all cameras
  Future<bool> disconnectAllCameras() async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🔌 Disconnecting all cameras...');

      final response = await http.post(
        Uri.parse('$_baseUrl/cameras/disconnect-all'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException('Disconnect all cameras timed out', const Duration(seconds: 15)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Disconnected all cameras: ${data['status']}');
        
        // Clear active cameras list
        _activeCameras.clear();
        notifyListeners();
        return true;
      } else {
        _lastError = 'Failed to disconnect all cameras: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Disconnect all cameras error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Set loading state and notify listeners
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  /// Clear last error
  void clearError() {
    _lastError = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _authService.removeListener(_onAuthStateChanged);
    super.dispose();
  }
}

/// Camera data model
class Camera {
  final String deviceId;
  final String? name;
  final String? type;
  final bool isActive;
  final DateTime? connectedAt;

  Camera({
    required this.deviceId,
    this.name,
    this.type,
    this.isActive = false,
    this.connectedAt,
  });

  factory Camera.fromJson(Map<String, dynamic> json) {
    return Camera(
      deviceId: json['device_id'] ?? json['id'] ?? '',
      name: json['name'],
      type: json['type'],
      isActive: json['is_active'] ?? false,
      connectedAt: json['connected_at'] != null 
          ? DateTime.parse(json['connected_at']) 
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'name': name,
      'type': type,
      'is_active': isActive,
      'connected_at': connectedAt?.toIso8601String(),
    };
  }
}

/// Camera information model
class CameraInfo {
  final String deviceId;
  final String? name;
  final String? type;
  final Map<String, dynamic>? capabilities;
  final bool isConnected;

  CameraInfo({
    required this.deviceId,
    this.name,
    this.type,
    this.capabilities,
    this.isConnected = false,
  });

  factory CameraInfo.fromJson(Map<String, dynamic> json) {
    return CameraInfo(
      deviceId: json['device_id'] ?? '',
      name: json['name'],
      type: json['type'],
      capabilities: json['capabilities'],
      isConnected: json['is_connected'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'name': name,
      'type': type,
      'capabilities': capabilities,
      'is_connected': isConnected,
    };
  }
}

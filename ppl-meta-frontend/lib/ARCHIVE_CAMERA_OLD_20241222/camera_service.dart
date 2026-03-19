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
/// 
/// Follows the EXACT same workflow as the successful headless camera management test:
/// Steps 1-4: Gateway for detect, connect, stream
/// Steps 5-10: Gateway for recording (now with debug/clear-state endpoints added)
class CameraService extends ChangeNotifier {
  static const String _gatewayUrl = 'http://localhost/api/v1';    // Gateway for ALL operations
  
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
        Uri.parse('$_gatewayUrl/cameras/detect?save_to_db=$saveToDb'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Camera detection completed: ${data['status']}');
        
        // Clear recording state for all detected cameras to prevent conflicts
        if (data['cameras'] != null) {
          for (var camera in data['cameras']) {
            final deviceId = camera['device_id'];
            if (deviceId != null) {
              _logger.i('🧹 Clearing stale state for detected camera: $deviceId');
              await clearRecordingState(deviceId);
            }
          }
        }
        
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
        Uri.parse('$_gatewayUrl/cameras/'),
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
        Uri.parse('$_gatewayUrl/cameras/active'),
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

      // Clear any stale recording state before connecting
      _logger.i('🧹 Clearing recording state before connecting to $deviceId');
      await clearRecordingState(deviceId);

      final response = await http.post(
        Uri.parse('$_gatewayUrl/cameras/$deviceId/connect'),
        headers: _authService.getAuthHeaders(),
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

      // Clear any stale recording state before disconnecting
      _logger.i('🧹 Clearing recording state before disconnecting from $deviceId');
      await clearRecordingState(deviceId);

      final response = await http.post(
        Uri.parse('$_gatewayUrl/cameras/$deviceId/disconnect'),
        headers: _authService.getAuthHeaders(),
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
        Uri.parse('$_gatewayUrl/cameras/$deviceId/info'),
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
        Uri.parse('$_gatewayUrl/cameras/disconnect-all'),
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

  /// Start streaming for a camera
  Future<bool> startStreaming(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('📹 Starting streaming for camera $deviceId...');

      final response = await http.post(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/start'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Streaming started for $deviceId: ${data['status']}');
        return true;
      } else {
        _lastError = 'Failed to start streaming for $deviceId: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Start streaming error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Stop streaming for a camera
  Future<bool> stopStreaming(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('⏹️ Stopping streaming for camera $deviceId...');

      final response = await http.post(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/stop'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Streaming stopped for $deviceId: ${data['status']}');
        return true;
      } else {
        _lastError = 'Failed to stop streaming for $deviceId: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Stop streaming error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Start recording for a camera
  Future<RecordingResult?> startRecording(String deviceId) async {
    print('🔥 DEBUG: startRecording called for deviceId: $deviceId');
    print('🔥 DEBUG: _gatewayUrl is: $_gatewayUrl');
    print('🔥 DEBUG: isAuthenticated: ${_authService.isAuthenticated}');
    
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.i('🎥 Starting recording for camera $deviceId...');

      final response = await http.post(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/record/start'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Recording started successfully');
        
        // Handle both response formats from our working backend test
        String? sessionId;
        String? deviceIdFromResponse;
        String? status = 'active';
        String? startedAt;
        String message = 'Recording started successfully';
        
        if (data is Map<String, dynamic>) {
          // New API response format (if available)
          sessionId = data['session_uuid'] ?? data['recording_id'];
          deviceIdFromResponse = data['camera_device_id'] ?? data['device_id'] ?? deviceId;
          status = data['status'] ?? 'active';
          startedAt = data['started_at'];
          message = data['message'] ?? 'Recording started successfully';
        }
        
        // Transform to RecordingResult format
        final transformedData = {
          'session_id': sessionId ?? 'recording_active',
          'device_id': deviceIdFromResponse ?? deviceId,
          'status': status,
          'started_at': startedAt ?? DateTime.now().toIso8601String(),
          'message': message,
        };
        
        return RecordingResult.fromJson(transformedData);
      } else if (response.statusCode == 409 || (response.statusCode == 200 && response.body.contains('already recording'))) {
        // Handle 409 Conflict OR success response that indicates already recording
        _logger.w('⚠️ Recording conflict detected, attempting to clear stale state...');
        
        final cleared = await clearRecordingState(deviceId);
        if (cleared) {
          _logger.i('🔄 Retrying recording after clearing stale state...');
          
          // Retry the recording start
          final retryResponse = await http.post(
            Uri.parse('$_gatewayUrl/streaming/$deviceId/record/start'),
            headers: _authService.getAuthHeaders(),
          );
          
          if (retryResponse.statusCode == 200) {
            final data = json.decode(retryResponse.body);
            _logger.i('✅ Recording started after retry');
            
            // Handle response format like the main request
            String? sessionId;
            String? deviceIdFromResponse;
            String? status = 'active';
            String? startedAt;
            String message = 'Recording started successfully after retry';
            
            if (data is Map<String, dynamic>) {
              sessionId = data['session_uuid'] ?? data['recording_id'];
              deviceIdFromResponse = data['camera_device_id'] ?? data['device_id'] ?? deviceId;
              status = data['status'] ?? 'active';
              startedAt = data['started_at'];
              message = data['message'] ?? message;
            }
            
            final transformedData = {
              'session_id': sessionId ?? 'recording_active_retry',
              'device_id': deviceIdFromResponse ?? deviceId,
              'status': status,
              'started_at': startedAt ?? DateTime.now().toIso8601String(),
              'message': message,
            };
            
            return RecordingResult.fromJson(transformedData);
          } else {
            _lastError = 'Failed to start recording after retry: ${retryResponse.statusCode}';
            _logger.e('❌ $_lastError');
            return null;
          }
        } else {
          _lastError = 'Failed to clear stale recording state';
          _logger.e('❌ $_lastError');
          return null;
        }
      } else {
        _lastError = 'Failed to start recording: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Start recording error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Clear stale recording state for a camera (debug/fix method)
  Future<bool> clearRecordingState(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🧹 Clearing recording state for camera $deviceId...');

      final response = await http.post(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/record/clear-state'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final cleanedCount = data['cleaned_sessions_count'] ?? 0;
        if (cleanedCount > 0) {
          _logger.i('✅ Cleaned $cleanedCount stale sessions');
        } else {
          _logger.i('ℹ️ No stale sessions found to clean');
        }
        return true;
      } else {
        _lastError = 'Failed to clear recording state: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Clear recording state error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Clear recording state for all available cameras (bulk operation)
  Future<bool> clearAllRecordingStates() async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🧹 Clearing recording state for all cameras...');
      
      // Use the availableCameras getter which returns List<Camera>
      if (availableCameras.isEmpty) {
        _logger.i('No cameras found to clear state for');
        return true;
      }

      int successful = 0;
      int failed = 0;

      // Clear state for each camera
      for (final camera in availableCameras) {
        try {
          final cleared = await clearRecordingState(camera.deviceId);
          if (cleared) {
            successful++;
          } else {
            failed++;
          }
        } catch (e) {
          _logger.w('Failed to clear state for ${camera.deviceId}: $e');
          failed++;
        }
      }

      _logger.i('🧹 Bulk clear complete: $successful successful, $failed failed');
      return failed == 0;
    } catch (e, stackTrace) {
      _lastError = 'Bulk clear recording state error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Stop recording for a camera
  Future<RecordingResult?> stopRecording(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.i('⏹️ Stopping recording for camera $deviceId...');

      // Use actual working stop recording API
      final response = await http.post(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/record/stop'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Stop recording timed out', const Duration(seconds: 10)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Recording stopped: ${data['message']}');
        
        // Transform response to match old RecordingResult format
        final transformedData = {
          'session_id': data['recording_id'] ?? data['session_uuid'],
          'device_id': deviceId,
          'status': 'completed',
          'message': data['message'] ?? 'Recording stopped successfully',
        };
        
        return RecordingResult.fromJson(transformedData);
      } else {
        _lastError = 'Failed to stop recording: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Stop recording error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Get recording status for a camera
  Future<RecordingStatus?> getRecordingStatus(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      // Use actual working status endpoint
      final response = await http.get(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/record/status'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 5),
        onTimeout: () => throw TimeoutException('Get recording status timed out', const Duration(seconds: 5)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        
        // Transform to match old RecordingStatus format
        final transformedData = {
          'is_recording': data['is_recording'] ?? false,
          'session_id': data['recording_id'],
          'device_id': deviceId,
          'started_at': data['started_at'],
          'duration_seconds': data['duration_seconds'] ?? 0,
          'file_size_bytes': data['file_size_bytes'] ?? 0,
        };
        
        return RecordingStatus.fromJson(transformedData);
      } else {
        _lastError = 'Failed to get recording status: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get recording status error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Get instant detection results from camera's memory cache
  Future<Map<String, dynamic>?> getInstantDetectionResults(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.d('🔍 Fetching instant detection results for camera $deviceId...');

      final response = await http.get(
        Uri.parse('$_gatewayUrl/cameras/$deviceId/instant-detection/results'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 3),
        onTimeout: () => throw TimeoutException('Get instant detection timed out', const Duration(seconds: 3)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.d('✅ Got instant detection results: ${data['person_objects']?.length ?? 0} people');
        return data;
      } else if (response.statusCode == 404) {
        // No results cached yet - this is normal
        _logger.d('ℹ️ No instant detection results cached for $deviceId yet');
        return {'success': false, 'person_objects': []};
      } else {
        _lastError = 'Failed to get instant detection: ${response.statusCode}';
        _logger.w('⚠️ $_lastError');
        return null;
      }
    } catch (e) {
      // Don't log errors aggressively - this is called every 5 seconds
      if (e is! TimeoutException) {
        _logger.d('Instant detection fetch: $e');
      }
      return null;
    }
  }

  /// Debug recording state for a camera (to identify state inconsistencies)
  Future<Map<String, dynamic>?> debugRecordingState(String deviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.i('🔍 Debugging recording state for camera $deviceId...');

      final response = await http.get(
        Uri.parse('$_gatewayUrl/streaming/$deviceId/record/debug'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 5),
        onTimeout: () => throw TimeoutException('Debug recording state timed out', const Duration(seconds: 5)),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        _logger.i('🔍 Debug state: memory=${data['has_active_recording_memory']}, db=${data['has_active_session_db']}');
        return data;
      } else {
        _lastError = 'Failed to debug recording state: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Debug recording state error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
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

/// Recording result model for start/stop operations
class RecordingResult {
  final String status;
  final String message;
  final String deviceId;
  final String? recordingId;
  final DateTime? startedAt;
  final DateTime? stoppedAt;
  final int? durationSeconds;
  final String? filePath;
  final int? fileSizeBytes;
  final String? collectionId;

  RecordingResult({
    required this.status,
    required this.message,
    required this.deviceId,
    this.recordingId,
    this.startedAt,
    this.stoppedAt,
    this.durationSeconds,
    this.filePath,
    this.fileSizeBytes,
    this.collectionId,
  });

  factory RecordingResult.fromJson(Map<String, dynamic> json) {
    return RecordingResult(
      status: json['status'] ?? '',
      message: json['message'] ?? '',
      deviceId: json['device_id'] ?? '',
      recordingId: json['recording_id'],
      startedAt: json['started_at'] != null 
          ? DateTime.parse(json['started_at']) 
          : null,
      stoppedAt: json['stopped_at'] != null 
          ? DateTime.parse(json['stopped_at']) 
          : null,
      durationSeconds: json['duration_seconds'],
      filePath: json['file_path'],
      fileSizeBytes: json['file_size_bytes'],
      collectionId: json['collection_id'],
    );
  }

  bool get isSuccess => status == 'success';
}

/// Recording status model for status queries
class RecordingStatus {
  final String deviceId;
  final bool isRecording;
  final String? recordingId;
  final DateTime? startedAt;
  final int durationSeconds;
  final int fileSizeBytes;

  RecordingStatus({
    required this.deviceId,
    required this.isRecording,
    this.recordingId,
    this.startedAt,
    this.durationSeconds = 0,
    this.fileSizeBytes = 0,
  });

  factory RecordingStatus.fromJson(Map<String, dynamic> json) {
    return RecordingStatus(
      deviceId: json['device_id'] ?? '',
      isRecording: json['is_recording'] ?? false,
      recordingId: json['recording_id'],
      startedAt: json['started_at'] != null 
          ? DateTime.parse(json['started_at']) 
          : null,
      durationSeconds: json['duration_seconds'] ?? 0,
      fileSizeBytes: json['file_size_bytes'] ?? 0,
    );
  }
}

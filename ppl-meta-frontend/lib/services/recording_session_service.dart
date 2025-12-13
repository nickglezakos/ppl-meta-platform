import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';
import 'camera_auth_service.dart';

/// Phase 4 Recording Session Service
/// 
/// Provides comprehensive recording session management with database persistence
/// Integrates with PPL Meta Orchestrator for session tracking and workflow management
class RecordingSessionService extends ChangeNotifier {
  static const String _baseUrl = 'http://localhost:8002/api/v1';
  static const String _camerasBaseUrl = 'http://localhost:8005/api/v1';
  
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

  List<RecordingSession> _activeSessions = [];
  List<RecordingSession> _recentSessions = [];
  bool _isLoading = false;
  String? _lastError;

  // Getters
  List<RecordingSession> get activeSessions => _activeSessions;
  List<RecordingSession> get recentSessions => _recentSessions;
  bool get isLoading => _isLoading;
  String? get lastError => _lastError;
  bool get isAuthenticated => _authService.isAuthenticated;

  RecordingSessionService(this._authService) {
    _authService.addListener(_onAuthStateChanged);
  }

  /// Handle authentication state changes
  void _onAuthStateChanged() {
    if (!_authService.isAuthenticated) {
      _activeSessions.clear();
      _recentSessions.clear();
      notifyListeners();
    }
  }

  /// Create a new recording session with Phase 4 database persistence
  Future<RecordingSession?> createRecordingSession({
    required String cameraDeviceId,
    required String workflowId,
    Map<String, dynamic>? metadata,
  }) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _setLoading(true);
      _logger.i('🎥 Creating recording session for camera: $cameraDeviceId');

      final requestBody = {
        'camera_device_id': cameraDeviceId,
        'workflow_id': workflowId,
        if (metadata != null) 'metadata': metadata,
      };

      final response = await http.post(
        Uri.parse('$_baseUrl/recording-sessions/'),
        headers: {
          ..._authService.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: json.encode(requestBody),
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException(
          'Create recording session timed out', 
          const Duration(seconds: 15)
        ),
      );

      if (response.statusCode == 201) {
        final data = json.decode(response.body);
        final session = RecordingSession.fromJson(data);
        
        _activeSessions.add(session);
        _logger.i('✅ Recording session created: ${session.sessionUuid}');
        
        notifyListeners();
        return session;
      } else {
        _lastError = 'Failed to create recording session: ${response.statusCode} - ${response.body}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Create recording session error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    } finally {
      _setLoading(false);
    }
  }

  /// Get all active recording sessions
  Future<bool> getActiveSessions() async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('📋 Fetching active recording sessions...');

      final response = await http.get(
        Uri.parse('$_baseUrl/recording-sessions/monitoring/active'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException(
          'Get active sessions timed out', 
          const Duration(seconds: 10)
        ),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['sessions'] != null) {
          _activeSessions = (data['sessions'] as List)
              .map((session) => RecordingSession.fromJson(session))
              .toList();
        } else {
          _activeSessions = [];
        }
        
        _logger.i('✅ Found ${_activeSessions.length} active sessions');
        notifyListeners();
        return true;
      } else {
        _lastError = 'Failed to get active sessions: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get active sessions error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Get recording session details by UUID
  Future<RecordingSession?> getRecordingSession(String sessionUuid) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.i('📋 Fetching recording session: $sessionUuid');

      final response = await http.get(
        Uri.parse('$_baseUrl/recording-sessions/$sessionUuid'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException(
          'Get recording session timed out', 
          const Duration(seconds: 10)
        ),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final session = RecordingSession.fromJson(data);
        
        _logger.i('✅ Retrieved session: ${session.sessionUuid}');
        return session;
      } else {
        _lastError = 'Failed to get recording session: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get recording session error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Update recording session status
  Future<bool> updateSessionStatus({
    required String sessionUuid,
    required SessionStatus status,
    Map<String, dynamic>? metadata,
  }) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🔄 Updating session $sessionUuid status to: ${status.name}');

      final requestBody = {
        'status': status.name,
        if (metadata != null) 'metadata': metadata,
      };

      final response = await http.put(
        Uri.parse('$_baseUrl/recording-sessions/$sessionUuid/status'),
        headers: {
          ..._authService.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: json.encode(requestBody),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException(
          'Update session status timed out', 
          const Duration(seconds: 10)
        ),
      );

      if (response.statusCode == 200) {
        _logger.i('✅ Session status updated successfully');
        
        // Refresh active sessions
        await getActiveSessions();
        return true;
      } else {
        _lastError = 'Failed to update session status: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Update session status error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Delete/cancel a recording session
  Future<bool> deleteRecordingSession(String sessionUuid) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🗑️ Deleting recording session: $sessionUuid');

      final response = await http.delete(
        Uri.parse('$_baseUrl/recording-sessions/$sessionUuid'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException(
          'Delete recording session timed out', 
          const Duration(seconds: 10)
        ),
      );

      if (response.statusCode == 200) {
        _logger.i('✅ Recording session deleted successfully');
        
        // Remove from active sessions
        _activeSessions.removeWhere((session) => session.sessionUuid == sessionUuid);
        notifyListeners();
        return true;
      } else {
        _lastError = 'Failed to delete recording session: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Delete recording session error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Stop camera recording by calling the cameras service endpoint
  /// This actually stops the recording process, not just updates the database status
  /// 
  /// Note: autoStopInstantDetection should be false to keep streaming and instant detection active
  Future<bool> stopCameraRecording({
    required String cameraDeviceId,
    bool autoStopInstantDetection = false,
  }) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🛑 Stopping camera recording for device: $cameraDeviceId');

      final response = await http.post(
        Uri.parse('$_camerasBaseUrl/streaming/$cameraDeviceId/record/stop?auto_stop_instant_detection=$autoStopInstantDetection'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException(
          'Stop camera recording timed out', 
          const Duration(seconds: 15)
        ),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('✅ Camera recording stopped successfully: ${data['session_uuid']}');
        return true;
      } else {
        _lastError = 'Failed to stop camera recording: ${response.statusCode} - ${response.body}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Stop camera recording error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Send heartbeat for active recording session
  Future<bool> sendSessionHeartbeat(String sessionUuid) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/recording-sessions/$sessionUuid/heartbeat'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 5),
        onTimeout: () => throw TimeoutException(
          'Session heartbeat timed out', 
          const Duration(seconds: 5)
        ),
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        _lastError = 'Failed to send heartbeat: ${response.statusCode}';
        return false;
      }
    } catch (e) {
      _lastError = 'Session heartbeat error: $e';
      return false;
    }
  }

  /// Trigger face detection for recording session
  Future<bool> triggerFaceDetection({
    required String sessionUuid,
    required String mediaUuid,
    Map<String, dynamic>? options,
  }) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return false;
    }

    try {
      _logger.i('🔍 Triggering face detection for session: $sessionUuid');

      final requestBody = {
        'media_uuid': mediaUuid,
        if (options != null) 'options': options,
      };

      final response = await http.post(
        Uri.parse('$_baseUrl/recording-sessions/$sessionUuid/face-detection/trigger'),
        headers: {
          ..._authService.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: json.encode(requestBody),
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException(
          'Face detection trigger timed out', 
          const Duration(seconds: 15)
        ),
      );

      if (response.statusCode == 200) {
        _logger.i('✅ Face detection triggered successfully');
        return true;
      } else {
        _lastError = 'Failed to trigger face detection: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return false;
      }
    } catch (e, stackTrace) {
      _lastError = 'Trigger face detection error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Get recording sessions for specific camera
  Future<List<RecordingSession>?> getCameraSessions(String cameraDeviceId) async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      _logger.i('📋 Fetching sessions for camera: $cameraDeviceId');

      final response = await http.get(
        Uri.parse('$_baseUrl/recording-sessions/camera/$cameraDeviceId'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException(
          'Get camera sessions timed out', 
          const Duration(seconds: 10)
        ),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['sessions'] != null) {
          final sessions = (data['sessions'] as List)
              .map((session) => RecordingSession.fromJson(session))
              .toList();
          
          _logger.i('✅ Found ${sessions.length} sessions for camera $cameraDeviceId');
          return sessions;
        } else {
          return [];
        }
      } else {
        _lastError = 'Failed to get camera sessions: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get camera sessions error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Get session statistics
  Future<SessionStatistics?> getSessionStatistics() async {
    if (!_authService.isAuthenticated) {
      _lastError = 'Authentication required';
      return null;
    }

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/recording-sessions/statistics'),
        headers: _authService.getAuthHeaders(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException(
          'Get session statistics timed out', 
          const Duration(seconds: 10)
        ),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return SessionStatistics.fromJson(data);
      } else {
        _lastError = 'Failed to get session statistics: ${response.statusCode}';
        _logger.e('❌ $_lastError');
        return null;
      }
    } catch (e, stackTrace) {
      _lastError = 'Get session statistics error: $e';
      _logger.e('❌ $_lastError', error: e, stackTrace: stackTrace);
      return null;
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

/// Session Status enum for Phase 4
enum SessionStatus {
  pending,
  active,
  completed,
  failed,
  cancelled
}

/// Recording Session model for Phase 4 database persistence
class RecordingSession {
  final String sessionUuid;
  final String cameraDeviceId;
  final String workflowId;
  final SessionStatus status;
  final DateTime createdAt;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final Map<String, dynamic>? metadata;
  final double? currentDuration;
  final int? framesRecorded;
  final String? errorMessage;

  RecordingSession({
    required this.sessionUuid,
    required this.cameraDeviceId,
    required this.workflowId,
    required this.status,
    required this.createdAt,
    this.startedAt,
    this.completedAt,
    this.metadata,
    this.currentDuration,
    this.framesRecorded,
    this.errorMessage,
  });

  factory RecordingSession.fromJson(Map<String, dynamic> json) {
    return RecordingSession(
      sessionUuid: json['session_uuid'] ?? json['uuid'] ?? '',
      cameraDeviceId: json['camera_device_id'] ?? '',
      workflowId: json['workflow_id'] ?? '',
      status: SessionStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => SessionStatus.pending,
      ),
      createdAt: DateTime.parse(json['created_at']),
      startedAt: json['started_at'] != null ? DateTime.parse(json['started_at']) : null,
      completedAt: json['completed_at'] != null ? DateTime.parse(json['completed_at']) : null,
      metadata: json['metadata'],
      currentDuration: json['current_duration_seconds']?.toDouble(),
      framesRecorded: json['frames_recorded'],
      errorMessage: json['error_message'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'session_uuid': sessionUuid,
      'camera_device_id': cameraDeviceId,
      'workflow_id': workflowId,
      'status': status.name,
      'created_at': createdAt.toIso8601String(),
      'started_at': startedAt?.toIso8601String(),
      'completed_at': completedAt?.toIso8601String(),
      'metadata': metadata,
      'current_duration_seconds': currentDuration,
      'frames_recorded': framesRecorded,
      'error_message': errorMessage,
    };
  }

  /// Get user-friendly status text
  String get statusText {
    switch (status) {
      case SessionStatus.pending:
        return 'Pending';
      case SessionStatus.active:
        return 'Recording';
      case SessionStatus.completed:
        return 'Completed';
      case SessionStatus.failed:
        return 'Failed';
      case SessionStatus.cancelled:
        return 'Cancelled';
    }
  }

  /// Get duration text for display
  String get durationText {
    if (currentDuration == null) return '--:--';
    final minutes = (currentDuration! / 60).floor();
    final seconds = (currentDuration! % 60).floor();
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Check if session is currently active
  bool get isActive => status == SessionStatus.active;

  /// Check if session is completed
  bool get isCompleted => [SessionStatus.completed, SessionStatus.failed, SessionStatus.cancelled].contains(status);
}

/// Session Statistics model
class SessionStatistics {
  final int totalSessions;
  final int activeSessions;
  final int completedSessions;
  final int failedSessions;
  final double averageDuration;
  final Map<String, int> sessionsByCamera;

  SessionStatistics({
    required this.totalSessions,
    required this.activeSessions,
    required this.completedSessions,
    required this.failedSessions,
    required this.averageDuration,
    required this.sessionsByCamera,
  });

  factory SessionStatistics.fromJson(Map<String, dynamic> json) {
    return SessionStatistics(
      totalSessions: json['total_sessions'] ?? 0,
      activeSessions: json['active_sessions'] ?? 0,
      completedSessions: json['completed_sessions'] ?? 0,
      failedSessions: json['failed_sessions'] ?? 0,
      averageDuration: (json['average_duration'] ?? 0.0).toDouble(),
      sessionsByCamera: Map<String, int>.from(json['sessions_by_camera'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_sessions': totalSessions,
      'active_sessions': activeSessions,
      'completed_sessions': completedSessions,
      'failed_sessions': failedSessions,
      'average_duration': averageDuration,
      'sessions_by_camera': sessionsByCamera,
    };
  }
}
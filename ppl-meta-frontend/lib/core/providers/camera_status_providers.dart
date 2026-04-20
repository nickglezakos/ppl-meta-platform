import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import '../services/camera_status_service.dart';
import '../config/app_config.dart';
import '../services/auth_service.dart';

/// Provider for camera status service
final cameraStatusServiceProvider = Provider<CameraStatusService>((ref) {
  // Get auth service to retrieve token
  final authService = ref.watch(authServiceProvider);
  
  final service = CameraStatusService(
    baseUrl: AppConfig.instance.apiBaseUrl,
    authService: authService,
  );
  
  ref.onDispose(() {
    service.dispose();
  });
  
  return service;
});

/// Provider for camera status stream (single camera)
final cameraStatusStreamProvider = StreamProvider.family<CameraStatusEvent, String>((ref, deviceId) {
  final service = ref.watch(cameraStatusServiceProvider);
  return service.subscribeToCameraStatus(deviceId);
});

/// Provider for all cameras status stream
final allCamerasStatusStreamProvider = StreamProvider<CameraStatusEvent>((ref) {
  final service = ref.watch(cameraStatusServiceProvider);
  return service.subscribeToAllCameras();
});

/// State notifier for camera status
class CameraStatusNotifier extends StateNotifier<Map<String, CameraStatus>> {
  final CameraStatusService _statusService;
  StreamSubscription? _subscription;
  
  CameraStatusNotifier(this._statusService) : super({}) {
    _subscribeToAllCameras();
  }
  
  void _subscribeToAllCameras() {
    _subscription = _statusService.subscribeToAllCameras().listen(
      _handleStatusEvent,
      onError: (error) {
        debugPrint('❌ Camera status stream error: $error');
      },
    );
  }
  
  void _handleStatusEvent(CameraStatusEvent event) {
    final currentStatus = state[event.deviceId] ?? CameraStatus(
      deviceId: event.deviceId,
      status: 'disconnected',
    );
    
    CameraStatus newStatus;
    
    switch (event.eventType) {
      case 'connecting':
        newStatus = currentStatus.copyWith(status: 'connecting');
        break;
        
      case 'connected':
        newStatus = currentStatus.copyWith(
          status: 'connected',
          error: null,
        );
        break;
        
      case 'disconnected':
        newStatus = currentStatus.copyWith(
          status: 'disconnected',
          isRecording: false,
          isStreaming: false,
        );
        break;
        
      case 'error':
        newStatus = currentStatus.copyWith(
          status: 'error',
          error: event.errorMessage,
        );
        break;
        
      case 'recording_started':
        newStatus = currentStatus.copyWith(
          isRecording: true,
          recordingSessionId: event.sessionId,
          recordingStartTime: event.timestamp,
        );
        break;
        
      case 'recording_stopped':
        newStatus = currentStatus.copyWith(
          isRecording: false,
          recordingSessionId: null,
          recordingStartTime: null,
          lastRecordingPath: event.filePath,
        );
        break;
        
      case 'streaming_started':
        newStatus = currentStatus.copyWith(isStreaming: true);
        break;
        
      case 'streaming_stopped':
        newStatus = currentStatus.copyWith(isStreaming: false);
        break;
        
      default:
        newStatus = currentStatus;
    }
    
    state = {...state, event.deviceId: newStatus};
  }
  
  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}

/// Provider for camera status state notifier
final cameraStatusNotifierProvider = StateNotifierProvider<CameraStatusNotifier, Map<String, CameraStatus>>((ref) {
  final service = ref.watch(cameraStatusServiceProvider);
  return CameraStatusNotifier(service);
});

/// Provider to get status for a specific camera
final cameraStatusProvider = Provider.family<CameraStatus?, String>((ref, deviceId) {
  final statusMap = ref.watch(cameraStatusNotifierProvider);
  return statusMap[deviceId];
});

/// Camera status model
class CameraStatus {
  final String deviceId;
  final String status; // disconnected, connecting, connected, error
  final bool isRecording;
  final bool isStreaming;
  final String? recordingSessionId;
  final DateTime? recordingStartTime;
  final String? lastRecordingPath;
  final String? error;
  
  CameraStatus({
    required this.deviceId,
    required this.status,
    this.isRecording = false,
    this.isStreaming = false,
    this.recordingSessionId,
    this.recordingStartTime,
    this.lastRecordingPath,
    this.error,
  });
  
  CameraStatus copyWith({
    String? status,
    bool? isRecording,
    bool? isStreaming,
    String? recordingSessionId,
    DateTime? recordingStartTime,
    String? lastRecordingPath,
    String? error,
  }) {
    return CameraStatus(
      deviceId: deviceId,
      status: status ?? this.status,
      isRecording: isRecording ?? this.isRecording,
      isStreaming: isStreaming ?? this.isStreaming,
      recordingSessionId: recordingSessionId ?? this.recordingSessionId,
      recordingStartTime: recordingStartTime ?? this.recordingStartTime,
      lastRecordingPath: lastRecordingPath ?? this.lastRecordingPath,
      error: error ?? this.error,
    );
  }
  
  bool get isDisconnected => status == 'disconnected';
  bool get isConnecting => status == 'connecting';
  bool get isConnected => status == 'connected';
  bool get hasError => status == 'error';
}

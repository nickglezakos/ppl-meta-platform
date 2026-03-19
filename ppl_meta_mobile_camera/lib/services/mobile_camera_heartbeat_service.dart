import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'device_identifier_service.dart';
import 'discovery_config_service.dart';
import 'app_logger.dart';

/// Service for managing camera heartbeat mechanism
/// Sends periodic heartbeats to maintain connection status and receive pending settings
class MobileCameraHeartbeatService {
  static final MobileCameraHeartbeatService _instance = MobileCameraHeartbeatService._internal();
  factory MobileCameraHeartbeatService() => _instance;
  MobileCameraHeartbeatService._internal();

  static const String _heartbeatIntervalKey = 'heartbeat_interval_seconds';
  static const int _defaultHeartbeatInterval = 30; // 30 seconds

  Timer? _heartbeatTimer;
  bool _isRunning = false;
  final DeviceIdentifierService _deviceService = DeviceIdentifierService();
  final DiscoveryConfigService _discoveryConfig = DiscoveryConfigService.instance;

  /// Start heartbeat mechanism
  Future<void> startHeartbeat() async {
    if (_isRunning) {
      print('⚠️  Heartbeat already running');
      return;
    }

    // Get stored camera UUID
    final cameraUuid = await _deviceService.getStoredCameraUuid();
    if (cameraUuid == null) {
      print('❌ Cannot start heartbeat - camera not registered (no UUID stored)');
      return;
    }

    // Get JWT token
    final prefs = await SharedPreferences.getInstance();
    final jwtToken = prefs.getString('jwt_token');
    if (jwtToken == null) {
      print('❌ Cannot start heartbeat - not authenticated');
      return;
    }

    _isRunning = true;
    print('💓 Starting camera heartbeat (UUID: $cameraUuid)');

    // Send initial heartbeat immediately
    await _sendHeartbeat(cameraUuid, jwtToken);

    // Schedule periodic heartbeats
    final interval = prefs.getInt(_heartbeatIntervalKey) ?? _defaultHeartbeatInterval;
    _heartbeatTimer = Timer.periodic(
      Duration(seconds: interval),
      (_) => _sendHeartbeat(cameraUuid, jwtToken),
    );

    print('💓 Heartbeat started with ${interval}s interval');
  }

  /// Stop heartbeat mechanism
  void stopHeartbeat() {
    if (!_isRunning) {
      return;
    }

    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _isRunning = false;
    print('💔 Heartbeat stopped');
  }

  /// Send a single heartbeat to the server
  Future<Map<String, dynamic>?> _sendHeartbeat(String cameraUuid, String jwtToken) async {
    try {
      // Get cameras service URL
      final camerasService = await _discoveryConfig.findService('ppl-meta-cameras');
      if (camerasService == null) {
        print('⚠️  Cameras service not available for heartbeat');
        return null;
      }

      final baseUrl = camerasService.baseUrl;
      final heartbeatUrl = '$baseUrl/api/v1/cameras/mobile/$cameraUuid/heartbeat';

      final response = await http.post(
        Uri.parse(heartbeatUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $jwtToken',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Check for pending settings that were applied
        final pendingApplied = data['pending_settings_applied'] as List?;
        if (pendingApplied != null && pendingApplied.isNotEmpty) {
          print('📝 Applied ${pendingApplied.length} pending settings:');
          for (var setting in pendingApplied) {
            print('  - ${setting['type']}: ${setting['value']}');
            
            // Handle name updates
            if (setting['type'] == 'name_update') {
              final newName = setting['value'];
              print('  ✅ Camera renamed to: $newName');
              // Update local storage or UI if needed
            }
          }
        }

        print('💚 Heartbeat sent successfully (status: ${data['status']})');
        return data;
      } else if (response.statusCode == 404) {
        print('⚠️  Camera not found on server (UUID: $cameraUuid) - heartbeat attempt failed');
        // DO NOT clear UUID immediately - could be temporary backend issue
        // UUID should only be cleared during explicit re-registration
        // or after multiple consecutive 404 failures
        print('💡 UUID preserved - camera may need re-registration but UUID kept for troubleshooting');
        return null;
      } else {
        print('⚠️  Heartbeat failed: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      print('❌ Heartbeat error: $e');
      return null;
    }
  }

  /// Send immediate heartbeat (useful after reconnecting)
  Future<Map<String, dynamic>?> sendImmediateHeartbeat() async {
    final cameraUuid = await _deviceService.getStoredCameraUuid();
    if (cameraUuid == null) {
      print('❌ Cannot send heartbeat - camera not registered');
      return null;
    }

    final prefs = await SharedPreferences.getInstance();
    final jwtToken = prefs.getString('jwt_token');
    if (jwtToken == null) {
      print('❌ Cannot send heartbeat - not authenticated');
      return null;
    }

    return await _sendHeartbeat(cameraUuid, jwtToken);
  }

  /// Check if heartbeat is currently running
  bool get isRunning => _isRunning;

  /// Update heartbeat interval (in seconds)
  Future<void> updateHeartbeatInterval(int seconds) async {
    if (seconds < 5) {
      throw ArgumentError('Heartbeat interval must be at least 5 seconds');
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_heartbeatIntervalKey, seconds);

    // Restart heartbeat with new interval if currently running
    if (_isRunning) {
      stopHeartbeat();
      await startHeartbeat();
    }

    print('💓 Heartbeat interval updated to ${seconds}s');
  }
}

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'communications_api_client.dart';
import 'auth_service.dart';

/// Service for polling and managing alert notifications
class AlertNotificationService {
  final CommunicationsApiClient _client;
  final AuthService _authService;
  Timer? _pollTimer;
  final StreamController<AlertNotification> _alertController = StreamController.broadcast();
  final Set<String> _processedAlertIds = {};
  bool _isInitialized = false;
  
  AlertNotificationService(this._client, this._authService);
  
  /// Stream of incoming alert notifications
  Stream<AlertNotification> get alertStream => _alertController.stream;
  
  /// Initialize with auth token
  Future<void> _initialize() async {
    if (_isInitialized) return;
    
    try {
      final token = await _authService.getStoredToken();
      if (token != null) {
        _client.setAuthToken(token);
        _isInitialized = true;
        print('✅ AlertNotificationService: Auth token set');
      } else {
        print('⚠️ AlertNotificationService: No auth token available');
      }
    } catch (e) {
      print('❌ AlertNotificationService: Failed to get auth token: $e');
    }
  }
  
  /// Start polling for new alerts
  void startPolling({Duration interval = const Duration(seconds: 5)}) {
    stopPolling();
    print('✅ AlertNotificationService: Starting polling every ${interval.inSeconds}s');
    
    // Initialize auth first, then start polling
    _initialize().then((_) {
      _pollTimer = Timer.periodic(interval, (_) => _checkForNewAlerts());
      _checkForNewAlerts(); // Check immediately
    });
  }
  
  /// Stop polling for alerts
  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }
  
  /// Check for new alerts from the Communications Service
  Future<void> _checkForNewAlerts() async {
    try {
      print('🔍 AlertNotificationService: Polling for alerts...');
      // Fetch recent audit logs - use 'audit_log' as the type
      final response = await _client.fetchLogs(
        type: 'audit_log',
        pageSize: 10, // Last 10 events
      );
      
      print('📋 AlertNotificationService: Fetched ${response.logs.length} audit logs');
      
      // Filter for alert events that haven't been processed
      for (final log in response.logs) {
        if (_processedAlertIds.contains(log.uuid)) {
          continue;
        }
        
        try {
          // For audit logs, alert data is in payload field
          if (log.payload != null && log.payload!['message'] != null) {
            final eventData = log.payload!;
            print('📦 AlertNotificationService: Found log with payload: $eventData');
            
            // Verify this is an alert type
            if (eventData['severity'] != null) {
              _processedAlertIds.add(log.uuid);
              
              // Create and emit alert notification
              final alert = AlertNotification(
                id: log.uuid,
                message: eventData['message'] as String,
                severity: eventData['severity'] as String? ?? 'warning',
                durationSeconds: eventData['duration_seconds'] as int? ?? 30,
                triggerName: eventData['trigger_name'] as String?,
                actionName: eventData['action_name'] as String?,
                timestamp: DateTime.tryParse(log.createdAt),
              );
              
              print('🔔 AlertNotificationService: Emitting alert: ${alert.message}');
              _alertController.add(alert);
            }
          }
        } catch (e) {
          print('Error parsing alert log: $e');
        }
      }
      
      // Clean up old processed IDs (keep only last 100)
      if (_processedAlertIds.length > 100) {
        final toRemove = _processedAlertIds.length - 100;
        _processedAlertIds.removeAll(_processedAlertIds.take(toRemove));
      }
      
    } catch (e) {
      print('Error checking for alerts: $e');
    }
  }
  
  void dispose() {
    stopPolling();
    _alertController.close();
  }
}

/// Alert notification model
class AlertNotification {
  final String id;
  final String message;
  final String severity; // info, warning, error, critical
  final int durationSeconds;
  final String? triggerName;
  final String? actionName;
  final DateTime? timestamp;
  
  AlertNotification({
    required this.id,
    required this.message,
    required this.severity,
    required this.durationSeconds,
    this.triggerName,
    this.actionName,
    this.timestamp,
  });
  
  /// Get color based on severity
  Color get color {
    switch (severity) {
      case 'info':
        return const Color(0xFF2196F3); // Blue
      case 'warning':
        return const Color(0xFFFF9800); // Orange
      case 'error':
        return const Color(0xFFF44336); // Red
      case 'critical':
        return const Color(0xFF9C27B0); // Purple
      default:
        return const Color(0xFFFF9800); // Orange (default)
    }
  }
  
  /// Get icon based on severity
  IconData get icon {
    switch (severity) {
      case 'info':
        return Icons.info_outline;
      case 'warning':
        return Icons.warning_amber;
      case 'error':
        return Icons.error_outline;
      case 'critical':
        return Icons.report_problem;
      default:
        return Icons.notifications_active;
    }
  }
}

/// Provider for alert notification service
final alertNotificationServiceProvider = Provider<AlertNotificationService>((ref) {
  // Create client and auth service instances
  final client = CommunicationsApiClient();
  final authService = AuthService();
  final service = AlertNotificationService(client, authService);
  
  // Start polling when service is created
  service.startPolling();
  
  // Clean up when provider is disposed
  ref.onDispose(() {
    service.dispose();
  });
  
  return service;
});

/// Stream provider for alert notifications
final alertStreamProvider = StreamProvider<AlertNotification>((ref) {
  final service = ref.watch(alertNotificationServiceProvider);
  return service.alertStream;
});


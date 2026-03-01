import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/services/secure_storage_service.dart';
import 'communications_api_client.dart';
import 'auth_service.dart';

/// Service for polling and managing alert notifications
class AlertNotificationService {
  final CommunicationsApiClient _client;
  final AuthService _authService;
  Timer? _pollTimer;
  final StreamController<AlertNotification> _alertController = StreamController.broadcast();
  final Set<String> _processedAlertIds = {};
  final Set<String> _shownAlertIds = {}; // Track alerts already shown to user
  final DateTime _serviceStartedAt = DateTime.now().toUtc();
  bool _isInitialized = false;
  bool _isFirstPoll = true; // Flag to skip showing old alerts on first load
  static const String _tokenKey = 'auth_token';

  DateTime? _parseServerTimestampUtc(String? raw) {
    if (raw == null || raw.isEmpty) {
      return null;
    }

    final parsed = DateTime.tryParse(raw);
    if (parsed == null) {
      return null;
    }

    final hasExplicitTimezone =
        raw.toUpperCase().endsWith('Z') || RegExp(r'[+-]\d{2}:\d{2}$').hasMatch(raw);

    if (hasExplicitTimezone) {
      return parsed.toUtc();
    }

    return DateTime.utc(
      parsed.year,
      parsed.month,
      parsed.day,
      parsed.hour,
      parsed.minute,
      parsed.second,
      parsed.millisecond,
      parsed.microsecond,
    );
  }

  
  AlertNotificationService(this._client, this._authService);
  
  /// Stream of incoming alert notifications
  Stream<AlertNotification> get alertStream => _alertController.stream;
  
  /// Initialize with auth token
  Future<bool> _initialize() async {
    if (_isInitialized) return true;
    
    try {
      String? token = await SecureStorageService.getString(_tokenKey);

      if (token == null || token.isEmpty) {
        final prefs = await SharedPreferences.getInstance();
        token = prefs.getString(_tokenKey);
      }

      if (token == null || token.isEmpty) {
        token = await _authService.getStoredToken();
      }

      if (token == null || token.isEmpty) {
        print('⚠️ AlertNotificationService: No auth token available');
        return false;
      }

      _client.setAuthToken(token);
      _isInitialized = true;
      print('✅ AlertNotificationService: Auth token set');
      return true;
    } catch (e) {
      print('❌ AlertNotificationService: Failed to get auth token: $e');
      return false;
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
      if (!_isInitialized) {
        final initialized = await _initialize();
        if (!initialized) {
          print('⚠️ AlertNotificationService: Skipping poll until auth token is available');
          return;
        }
      }

      print('🔍 AlertNotificationService: Polling for alerts...');
      // Fetch recent audit logs - use 'audit_log' as the type
      final response = await _client.fetchLogs(
        type: 'audit_log',
        pageSize: 50, // Fetch enough records to avoid missing new alerts
      );
      
      print('📋 AlertNotificationService: Fetched ${response.logs.length} audit logs');
      
      // On first poll, just mark all as seen without showing them
      if (_isFirstPoll) {
        for (final log in response.logs) {
          if (log.payload != null && log.payload!['message'] != null) {
            final createdAt = _parseServerTimestampUtc(log.createdAt);
            final isHistorical = createdAt == null || createdAt.isBefore(_serviceStartedAt.subtract(const Duration(seconds: 2)));
            if (!isHistorical) {
              continue;
            }
            _shownAlertIds.add(log.uuid);
          }
        }
        print('🔕 AlertNotificationService: First poll - marked only historical alerts as seen (${_shownAlertIds.length})');
        _isFirstPoll = false;
      }
      
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
              
              // Skip if already shown to user
              if (_shownAlertIds.contains(log.uuid)) {
                print('⏭️ AlertNotificationService: Skipping already-shown alert: ${log.uuid}');
                continue;
              }
              
              // Mark as shown
              _shownAlertIds.add(log.uuid);
              
              // Create and emit alert notification
              final alert = AlertNotification(
                id: log.uuid,
                message: eventData['message'] as String,
                severity: eventData['severity'] as String? ?? 'warning',
                durationSeconds: eventData['duration_seconds'] as int? ?? 30,
                triggerName: eventData['trigger_name'] as String?,
                actionName: eventData['action_name'] as String?,
                timestamp: _parseServerTimestampUtc(log.createdAt),
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
      
      // Clean up old shown alert IDs (keep only last 100)
      if (_shownAlertIds.length > 100) {
        final toRemove = _shownAlertIds.length - 100;
        _shownAlertIds.removeAll(_shownAlertIds.take(toRemove));
      }
      
    } catch (e) {
      // Re-attempt auth init on next poll after transient auth/network issues
      _isInitialized = false;
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


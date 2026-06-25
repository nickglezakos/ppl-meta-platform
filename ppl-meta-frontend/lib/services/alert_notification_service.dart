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
  // Content-based deduplication: maps a content key to when it was last shown.
  // Prevents the backend looping the same trigger (new UUID each time) from
  // spamming the overlay.
  final Map<String, DateTime> _recentlyShownByContent = {};
  static const Duration _contentDeduplicationWindow = Duration(seconds: 60);
  final DateTime _serviceStartedAt = DateTime.now().toUtc();
  bool _isInitialized = false;
  bool _isFirstPoll = true; // Flag to skip showing old alerts on first load
  static const String _tokenKey = 'auth_token';

  /// Timestamp of the most recently seen log. Persisted across sessions
  /// so that only logs newer than this are fetched on reload.
  DateTime? _lastSeenTimestamp;
  static const String _lastSeenTimestampKey = 'alert_last_seen_timestamp';

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
  
  /// Initialize with auth token and load persisted state
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

      // Load persisted last-seen timestamp so we only fetch new logs after a reload
      await _loadLastSeenTimestamp();

      print('✅ AlertNotificationService: Auth token set');
      if (_lastSeenTimestamp != null) {
        print('   Resuming from last seen timestamp: $_lastSeenTimestamp');
      }
      return true;
    } catch (e) {
      print('❌ AlertNotificationService: Failed to get auth token: $e');
      return false;
    }
  }

  /// Load the last-seen log timestamp from persistent storage
  Future<void> _loadLastSeenTimestamp() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(_lastSeenTimestampKey);
      if (stored != null && stored.isNotEmpty) {
        _lastSeenTimestamp = DateTime.tryParse(stored)?.toUtc();
      }
    } catch (e) {
      print('⚠️ AlertNotificationService: Failed to load last seen timestamp: $e');
    }
  }

  /// Persist the last-seen log timestamp so it survives page reloads
  Future<void> _persistLastSeenTimestamp(DateTime timestamp) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_lastSeenTimestampKey, timestamp.toUtc().toIso8601String());
    } catch (e) {
      print('⚠️ AlertNotificationService: Failed to persist last seen timestamp: $e');
    }
  }
  
  /// Start polling for new alerts
  void startPolling({Duration interval = const Duration(seconds: 2)}) {
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
  
  /// Fetch all pages of audit logs newer than the cursor, collecting them into
  /// a single list to avoid pagination gaps (where page 2+ logs are skipped).
  Future<List<dynamic>> _fetchAllLogs({int pageSize = 50}) async {
    final allLogs = <dynamic>[];
    int page = 1;

    while (true) {
      final response = await _client.fetchLogs(
        type: 'audit_log',
        pageSize: pageSize,
        page: page,
        startDate: _lastSeenTimestamp,
      );

      allLogs.addAll(response.logs);

      // Stop when we've fetched all pages (fewer than pageSize means last page)
      if (response.logs.length < pageSize) break;
      page++;
    }

    return allLogs;
  }

  /// Process a list of audit logs: deduplicate, emit alerts, and return the
  /// latest timestamp seen in this batch (if any).
  DateTime? _processLogs(List<dynamic> logs) {
    DateTime? latestSeenInBatch;

    for (final log in logs) {
      if (_processedAlertIds.contains(log.uuid)) {
        continue;
      }

      try {
        if (log.payload != null && log.payload!['message'] != null) {
          final eventData = log.payload!;
          _processedAlertIds.add(log.uuid);
          print('📦 AlertNotificationService: Found log with payload: $eventData');

          final logTimestamp = _parseServerTimestampUtc(log.createdAt);
          if (logTimestamp != null &&
              (latestSeenInBatch == null || logTimestamp.isAfter(latestSeenInBatch))) {
            latestSeenInBatch = logTimestamp;
          }

          if (eventData['severity'] != null) {
            if (_shownAlertIds.contains(log.uuid)) {
              print('⏭️ AlertNotificationService: Skipping already-shown alert: ${log.uuid}');
              continue;
            }

            final contentKey = '${eventData['trigger_id'] ?? ''}:${eventData['message'] ?? ''}';
            final lastShown = _recentlyShownByContent[contentKey];
            if (lastShown != null &&
                DateTime.now().difference(lastShown) < _contentDeduplicationWindow) {
              _shownAlertIds.add(log.uuid);
              print('⏭️ AlertNotificationService: Suppressing duplicate content within cooldown: $contentKey');
              continue;
            }

            _shownAlertIds.add(log.uuid);
            _recentlyShownByContent[contentKey] = DateTime.now();

            final alert = AlertNotification(
              id: log.uuid,
              message: eventData['message'] as String,
              severity: eventData['severity'] as String? ?? 'warning',
              durationSeconds: eventData['duration_seconds'] as int? ?? 30,
              triggerName: eventData['trigger_name'] as String?,
              actionName: eventData['action_name'] as String?,
              timestamp: logTimestamp,
            );

            print('🔔 AlertNotificationService: Emitting alert: ${alert.message}');
            _alertController.add(alert);
          }
        }
      } catch (e) {
        print('Error parsing alert log: $e');
      }
    }

    return latestSeenInBatch;
  }

  /// Check for new alerts from the Communications Service.
  /// Fetches all pages to avoid leapfrogging logs that fall on page 2+.
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

      // Fetch ALL pages so no log is skipped due to pagination
      final allLogs = await _fetchAllLogs(pageSize: 50);

      print('📋 AlertNotificationService: Fetched ${allLogs.length} audit logs across all pages (since: ${_lastSeenTimestamp ?? 'beginning'})');

      // On first poll, just mark all fetched logs as seen without showing them
      if (_isFirstPoll) {
        for (final log in allLogs) {
          if (log.payload != null && log.payload!['message'] != null) {
            _shownAlertIds.add(log.uuid);
          }
        }
        print('🔕 AlertNotificationService: First poll - marked ${_shownAlertIds.length} alerts as seen');
        _isFirstPoll = false;
      }

      final latestSeenInBatch = _processLogs(allLogs);

      // Advance cursor only from real server log timestamps.
      // Using DateTime.now() (browser wall clock) would risk leapfrogging
      // server-timestamped logs when there is any clock drift.
      if (latestSeenInBatch != null) {
        _lastSeenTimestamp = latestSeenInBatch;
        await _persistLastSeenTimestamp(_lastSeenTimestamp!);
      }

      // Clean up old processed IDs (keep only last 100)
      if (_processedAlertIds.length > 100) {
        final toRemove = _processedAlertIds.length - 100;
        final idsToRemove = _processedAlertIds.take(toRemove).toList();
        _processedAlertIds.removeAll(idsToRemove);
      }

      // Clean up old shown alert IDs — keep a large window so persistent backend
      // entries are never re-emitted after eviction (the original loop bug).
      if (_shownAlertIds.length > 10000) {
        final toRemove = _shownAlertIds.length - 10000;
        final idsToRemove = _shownAlertIds.take(toRemove).toList();
        _shownAlertIds.removeAll(idsToRemove);
      }

      // Evict expired content-deduplication entries.
      final now = DateTime.now();
      _recentlyShownByContent.removeWhere(
        (_, lastShown) => now.difference(lastShown) >= _contentDeduplicationWindow,
      );

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
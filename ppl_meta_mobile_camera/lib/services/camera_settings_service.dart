import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'device_identifier_service.dart';

/// Service for managing mobile camera settings with local storage and backend sync
class CameraSettingsService {
  static const String _settingsKey = 'camera_settings';
  static const String _lastSyncKey = 'settings_last_sync';
  
  final DeviceIdentifierService _deviceIdService = DeviceIdentifierService();

  /// Camera settings model
  Map<String, dynamic> _defaultSettings = {
    'name': '',
    'collection_id': null,
    'recording_enabled': true,
    'resolution': '1920x1080',
    'frame_rate': 30,
    'orientation': 'portrait',
    'auto_start_recording': false,
    'max_recording_duration': 300, // 5 minutes
    'storage_limit_mb': 1000,
    'last_modified_at': null,
    'last_modified_by': 'mobile',
  };

  /// Get current settings from local storage
  Future<Map<String, dynamic>> getLocalSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final settingsJson = prefs.getString(_settingsKey);
      
      if (settingsJson == null) {
        return Map<String, dynamic>.from(_defaultSettings);
      }
      
      return json.decode(settingsJson) as Map<String, dynamic>;
    } catch (e) {
      print('❌ Error reading local settings: $e');
      return Map<String, dynamic>.from(_defaultSettings);
    }
  }

  /// Save settings locally
  Future<bool> saveLocalSettings(Map<String, dynamic> settings) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Add timestamp and source
      settings['last_modified_at'] = DateTime.now().toIso8601String();
      settings['last_modified_by'] = 'mobile';
      
      final settingsJson = json.encode(settings);
      await prefs.setString(_settingsKey, settingsJson);
      
      print('✅ Settings saved locally');
      return true;
    } catch (e) {
      print('❌ Error saving local settings: $e');
      return false;
    }
  }

  /// Update specific setting locally
  Future<bool> updateSetting(String key, dynamic value) async {
    try {
      final settings = await getLocalSettings();
      settings[key] = value;
      return await saveLocalSettings(settings);
    } catch (e) {
      print('❌ Error updating setting $key: $e');
      return false;
    }
  }

  /// Sync settings to backend
  Future<bool> syncToBackend({
    required String baseUrl,
    required String authToken,
    bool forceSync = false,
  }) async {
    try {
      // Get stored camera UUID
      final uuid = await _deviceIdService.getStoredCameraUuid();
      if (uuid == null) {
        print('❌ No camera UUID found, cannot sync settings');
        return false;
      }

      // Get local settings
      final settings = await getLocalSettings();
      
      // Check if sync is needed
      if (!forceSync && !await _needsSync()) {
        print('ℹ️ Settings already synced, skipping');
        return true;
      }

      // Prepare request
      final url = Uri.parse('$baseUrl/api/v1/cameras/mobile/$uuid/settings');
      final payload = {
        'settings': settings,
        'source': 'mobile',
        'timestamp': DateTime.now().toIso8601String(),
      };

      print('🔄 Syncing settings to backend: $url');
      
      final response = await http.patch(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: json.encode(payload),
      );

      if (response.statusCode == 200) {
        print('✅ Settings synced to backend successfully');
        await _updateLastSyncTime();
        return true;
      } else {
        print('❌ Failed to sync settings: ${response.statusCode} - ${response.body}');
        return false;
      }
    } catch (e) {
      print('❌ Error syncing settings to backend: $e');
      return false;
    }
  }

  /// Fetch settings from backend (for admin-initiated changes)
  Future<Map<String, dynamic>?> fetchFromBackend({
    required String baseUrl,
    required String authToken,
  }) async {
    try {
      // Get stored camera UUID
      final uuid = await _deviceIdService.getStoredCameraUuid();
      if (uuid == null) {
        print('❌ No camera UUID found, cannot fetch settings');
        return null;
      }

      final url = Uri.parse('$baseUrl/api/v1/cameras/mobile/$uuid/settings');
      
      print('🔄 Fetching settings from backend: $url');
      
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ Settings fetched from backend successfully');
        return data['settings'] as Map<String, dynamic>?;
      } else {
        print('❌ Failed to fetch settings: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      print('❌ Error fetching settings from backend: $e');
      return null;
    }
  }

  /// Merge backend settings with local settings
  /// Returns map with: { 'merged': Map, 'conflicts': List }
  Future<Map<String, dynamic>> mergeSettings({
    required Map<String, dynamic> localSettings,
    required Map<String, dynamic> backendSettings,
  }) async {
    final conflicts = <Map<String, dynamic>>[];
    final merged = Map<String, dynamic>.from(localSettings);

    // Check if backend has admin override
    final adminOverride = backendSettings['admin_override'] == true;
    final backendModifiedAt = backendSettings['last_modified_at'];
    final localModifiedAt = localSettings['last_modified_at'];

    for (var key in backendSettings.keys) {
      if (key == 'last_modified_at' || key == 'last_modified_by') {
        continue; // Skip metadata fields
      }

      final backendValue = backendSettings[key];
      final localValue = localSettings[key];

      // If values differ, we have a potential conflict
      if (backendValue != localValue) {
        if (adminOverride) {
          // Admin override: backend always wins
          merged[key] = backendValue;
          conflicts.add({
            'setting': key,
            'local_value': localValue,
            'backend_value': backendValue,
            'resolution': 'backend_wins',
            'reason': 'admin_override',
          });
        } else {
          // No override: compare timestamps (last write wins)
          if (backendModifiedAt != null && localModifiedAt != null) {
            final backendTime = DateTime.parse(backendModifiedAt);
            final localTime = DateTime.parse(localModifiedAt);
            
            if (backendTime.isAfter(localTime)) {
              merged[key] = backendValue;
              conflicts.add({
                'setting': key,
                'local_value': localValue,
                'backend_value': backendValue,
                'resolution': 'backend_wins',
                'reason': 'newer_timestamp',
              });
            } else {
              // Local is newer, keep local value
              conflicts.add({
                'setting': key,
                'local_value': localValue,
                'backend_value': backendValue,
                'resolution': 'local_wins',
                'reason': 'newer_timestamp',
              });
            }
          } else {
            // No timestamps, default to backend (safer for enterprise)
            merged[key] = backendValue;
            conflicts.add({
              'setting': key,
              'local_value': localValue,
              'backend_value': backendValue,
              'resolution': 'backend_wins',
              'reason': 'no_timestamp',
            });
          }
        }
      }
    }

    return {
      'merged': merged,
      'conflicts': conflicts,
    };
  }

  /// Check if settings need sync (based on last sync time)
  Future<bool> _needsSync() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final lastSyncStr = prefs.getString(_lastSyncKey);
      
      if (lastSyncStr == null) {
        return true; // Never synced
      }
      
      final lastSync = DateTime.parse(lastSyncStr);
      final now = DateTime.now();
      
      // Sync if more than 5 minutes since last sync
      return now.difference(lastSync).inMinutes >= 5;
    } catch (e) {
      return true; // If error, assume sync needed
    }
  }

  /// Update last sync timestamp
  Future<void> _updateLastSyncTime() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_lastSyncKey, DateTime.now().toIso8601String());
    } catch (e) {
      print('❌ Error updating last sync time: $e');
    }
  }

  /// Clear all local settings
  Future<bool> clearLocalSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_settingsKey);
      await prefs.remove(_lastSyncKey);
      print('✅ Local settings cleared');
      return true;
    } catch (e) {
      print('❌ Error clearing local settings: $e');
      return false;
    }
  }

  /// Get last sync time
  Future<DateTime?> getLastSyncTime() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final lastSyncStr = prefs.getString(_lastSyncKey);
      if (lastSyncStr != null) {
        return DateTime.parse(lastSyncStr);
      }
    } catch (e) {
      print('❌ Error getting last sync time: $e');
    }
    return null;
  }
}

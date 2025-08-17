import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/snapshot_result.dart';

/// Local storage service for snapshot gallery (Phase 1)
/// Uses SharedPreferences for simplicity - will be replaced with SQLite in Phase 2
class SnapshotStorageService {
  static const String _storageKey = 'ppl_meta_snapshots';
  static const String _settingsKey = 'ppl_meta_snapshot_settings';
  static const int _maxStoredSnapshots = 100; // Limit for performance

  /// Get SharedPreferences instance with web platform support
  static Future<SharedPreferences> _getPrefs() async {
    // Note: SharedPreferences.setMockInitialValues should only be called once during app initialization
    // This is handled in main.dart for web platform
    return await SharedPreferences.getInstance();
  }

  /// Save a snapshot to local storage
  Future<bool> saveSnapshot(SnapshotResult snapshot) async {
    try {
      debugPrint('💾 Saving snapshot for device: ${snapshot.deviceId}');
      final prefs = await _getPrefs();
      final existingSnapshots = await getSnapshots();
      
      debugPrint('📊 Current snapshots in storage: ${existingSnapshots.length}');
      
      // Add new snapshot to the beginning of the list
      existingSnapshots.insert(0, snapshot);
      
      // Limit the number of stored snapshots
      if (existingSnapshots.length > _maxStoredSnapshots) {
        existingSnapshots.removeRange(_maxStoredSnapshots, existingSnapshots.length);
        debugPrint('🗂️ Trimmed snapshots to $_maxStoredSnapshots limit');
      }
      
      // Convert to JSON list
      final jsonList = existingSnapshots.map((s) => s.toJson()).toList();
      final jsonString = jsonEncode(jsonList);
      
      // Save to shared preferences
      final result = await prefs.setString(_storageKey, jsonString);
      debugPrint('✅ Snapshot saved successfully: $result');
      debugPrint('📈 Total snapshots now: ${existingSnapshots.length}');
      return result;
    } catch (e) {
      debugPrint('❌ Error saving snapshot: $e');
      return false;
    }
  }

  /// Get all saved snapshots
  Future<List<SnapshotResult>> getSnapshots() async {
    try {
      final prefs = await _getPrefs();
      final jsonString = prefs.getString(_storageKey) ?? '[]';
      final jsonList = jsonDecode(jsonString) as List;
      
      final snapshots = jsonList
          .map((json) => SnapshotResult.fromJson(json as Map<String, dynamic>))
          .toList();
          
      debugPrint('📚 Loaded ${snapshots.length} snapshots from storage');
      return snapshots;
    } catch (e) {
      debugPrint('❌ Error loading snapshots: $e');
      return [];
    }
  }

  /// Get snapshots for a specific camera
  Future<List<SnapshotResult>> getSnapshotsByCamera(String cameraId) async {
    final allSnapshots = await getSnapshots();
    final filtered = allSnapshots.where((s) => s.deviceId == cameraId).toList();
    debugPrint('🔍 Filtering snapshots for camera $cameraId: found ${filtered.length} out of ${allSnapshots.length} total');
    return filtered;
  }  /// Delete a specific snapshot
  Future<bool> deleteSnapshot(SnapshotResult snapshot) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final existingSnapshots = await getSnapshots();
      
      // Remove the snapshot (compare by deviceId, capturedAt, and base64 hash)
      existingSnapshots.removeWhere((s) => 
          s.deviceId == snapshot.deviceId &&
          s.capturedAt == snapshot.capturedAt &&
          s.base64Image.hashCode == snapshot.base64Image.hashCode);
      
      // Save updated list
      final jsonList = existingSnapshots.map((s) => s.toJson()).toList();
      final jsonString = jsonEncode(jsonList);
      
      return await prefs.setString(_storageKey, jsonString);
    } catch (e) {
      debugPrint('Error deleting snapshot: $e');
      return false;
    }
  }

  /// Delete all snapshots
  Future<bool> clearAllSnapshots() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return await prefs.remove(_storageKey);
    } catch (e) {
      debugPrint('Error clearing snapshots: $e');
      return false;
    }
  }

  /// Delete snapshots for a specific camera
  Future<bool> deleteSnapshotsForCamera(String cameraId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final existingSnapshots = await getSnapshots();
      
      // Remove snapshots for the specified camera
      existingSnapshots.removeWhere((s) => s.deviceId == cameraId);
      
      // Save updated list
      final jsonList = existingSnapshots.map((s) => s.toJson()).toList();
      final jsonString = jsonEncode(jsonList);
      
      return await prefs.setString(_storageKey, jsonString);
    } catch (e) {
      debugPrint('Error deleting camera snapshots: $e');
      return false;
    }
  }

  /// Get storage statistics
  Future<SnapshotStorageStats> getStorageStats() async {
    final snapshots = await getSnapshots();
    
    int totalSize = 0;
    int totalCount = snapshots.length;
    Map<String, int> cameraCount = {};
    
    for (final snapshot in snapshots) {
      totalSize += snapshot.fileSizeBytes ?? 0;
      cameraCount[snapshot.deviceId] = (cameraCount[snapshot.deviceId] ?? 0) + 1;
    }
    
    return SnapshotStorageStats(
      totalSnapshots: totalCount,
      totalSizeBytes: totalSize,
      snapshotsByCamera: cameraCount,
      oldestSnapshot: snapshots.isNotEmpty ? snapshots.last.capturedAt : null,
      newestSnapshot: snapshots.isNotEmpty ? snapshots.first.capturedAt : null,
    );
  }

  /// Get recent snapshots (last N)
  Future<List<SnapshotResult>> getRecentSnapshots({int limit = 10}) async {
    final allSnapshots = await getSnapshots();
    return allSnapshots.take(limit).toList();
  }

  /// Search snapshots by filename or camera name
  Future<List<SnapshotResult>> searchSnapshots(String query) async {
    if (query.isEmpty) return await getSnapshots();
    
    final allSnapshots = await getSnapshots();
    final lowerQuery = query.toLowerCase();
    
    return allSnapshots.where((snapshot) {
      final filename = snapshot.filename?.toLowerCase() ?? '';
      final deviceId = snapshot.deviceId.toLowerCase();
      return filename.contains(lowerQuery) || deviceId.contains(lowerQuery);
    }).toList();
  }

  /// Save snapshot settings
  Future<bool> saveSnapshotSettings(Map<String, dynamic> settings) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return await prefs.setString(_settingsKey, jsonEncode(settings));
    } catch (e) {
      debugPrint('Error saving snapshot settings: $e');
      return false;
    }
  }

  /// Load snapshot settings
  Future<Map<String, dynamic>> loadSnapshotSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString(_settingsKey);
      
      if (jsonString == null) return {};
      
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('Error loading snapshot settings: $e');
      return {};
    }
  }
}

/// Storage statistics model
class SnapshotStorageStats {
  final int totalSnapshots;
  final int totalSizeBytes;
  final Map<String, int> snapshotsByCamera;
  final DateTime? oldestSnapshot;
  final DateTime? newestSnapshot;

  const SnapshotStorageStats({
    required this.totalSnapshots,
    required this.totalSizeBytes,
    required this.snapshotsByCamera,
    this.oldestSnapshot,
    this.newestSnapshot,
  });

  /// Get formatted total size
  String get formattedTotalSize {
    if (totalSizeBytes < 1024) return '$totalSizeBytes B';
    if (totalSizeBytes < 1024 * 1024) return '${(totalSizeBytes / 1024).toStringAsFixed(1)} KB';
    return '${(totalSizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  /// Get storage duration
  String get storageDuration {
    if (oldestSnapshot == null || newestSnapshot == null) return 'No snapshots';
    
    final duration = newestSnapshot!.difference(oldestSnapshot!);
    if (duration.inDays > 0) return '${duration.inDays} days';
    if (duration.inHours > 0) return '${duration.inHours} hours';
    return '${duration.inMinutes} minutes';
  }
}

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

/// Service for queuing settings updates when offline and syncing when online
class OfflineQueueService {
  static const String _queueKey = 'offline_settings_queue';
  static const int _maxQueueSize = 100;

  /// Queue item model
  static const String typeSettingsUpdate = 'settings_update';
  static const String typeCameraRename = 'camera_rename';
  static const String typeCollectionChange = 'collection_change';

  /// Add item to offline queue
  Future<bool> enqueue({
    required String type,
    required Map<String, dynamic> data,
    String? cameraUuid,
  }) async {
    try {
      final queue = await _getQueue();
      
      // Check queue size limit
      if (queue.length >= _maxQueueSize) {
        print('⚠️ Offline queue full, removing oldest item');
        queue.removeAt(0);
      }
      
      final queueItem = {
        'id': DateTime.now().millisecondsSinceEpoch.toString(),
        'type': type,
        'data': data,
        'camera_uuid': cameraUuid,
        'created_at': DateTime.now().toIso8601String(),
        'retry_count': 0,
      };
      
      queue.add(queueItem);
      await _saveQueue(queue);
      
      print('✅ Item added to offline queue: $type');
      return true;
    } catch (e) {
      print('❌ Error adding to offline queue: $e');
      return false;
    }
  }

  /// Get all queued items
  Future<List<Map<String, dynamic>>> getQueuedItems() async {
    return await _getQueue();
  }

  /// Get queue size
  Future<int> getQueueSize() async {
    final queue = await _getQueue();
    return queue.length;
  }

  /// Sync all queued items to backend
  Future<Map<String, dynamic>> syncAll({
    required String baseUrl,
    required String authToken,
    required String cameraUuid,
  }) async {
    int successful = 0;
    int failed = 0;
    final errors = <String>[];
    
    try {
      final queue = await _getQueue();
      
      if (queue.isEmpty) {
        print('ℹ️ Offline queue is empty, nothing to sync');
        return {
          'success': true,
          'synced': 0,
          'failed': 0,
          'errors': [],
        };
      }
      
      print('🔄 Syncing ${queue.length} queued items...');
      
      final itemsToRemove = <Map<String, dynamic>>[];
      
      for (var item in queue) {
        final type = item['type'] as String;
        final data = item['data'] as Map<String, dynamic>;
        final itemUuid = item['camera_uuid'] as String? ?? cameraUuid;
        
        bool syncSuccess = false;
        
        switch (type) {
          case typeSettingsUpdate:
            syncSuccess = await _syncSettingsUpdate(
              baseUrl: baseUrl,
              authToken: authToken,
              cameraUuid: itemUuid,
              settings: data,
            );
            break;
            
          case typeCameraRename:
            syncSuccess = await _syncCameraRename(
              baseUrl: baseUrl,
              authToken: authToken,
              cameraUuid: itemUuid,
              newName: data['name'] as String,
            );
            break;
            
          case typeCollectionChange:
            syncSuccess = await _syncCollectionChange(
              baseUrl: baseUrl,
              authToken: authToken,
              cameraUuid: itemUuid,
              collectionId: data['collection_id'] as String?,
            );
            break;
            
          default:
            print('⚠️ Unknown queue item type: $type');
            syncSuccess = false;
        }
        
        if (syncSuccess) {
          successful++;
          itemsToRemove.add(item);
        } else {
          failed++;
          errors.add('Failed to sync $type');
          
          // Increment retry count
          item['retry_count'] = (item['retry_count'] ?? 0) + 1;
          
          // Remove if too many retries (max 3)
          if (item['retry_count'] >= 3) {
            print('⚠️ Removing item after 3 failed retries: $type');
            itemsToRemove.add(item);
          }
        }
      }
      
      // Remove successfully synced items from queue
      for (var item in itemsToRemove) {
        queue.remove(item);
      }
      
      await _saveQueue(queue);
      
      print('✅ Sync complete: $successful succeeded, $failed failed');
      
      return {
        'success': failed == 0,
        'synced': successful,
        'failed': failed,
        'errors': errors,
      };
    } catch (e) {
      print('❌ Error syncing offline queue: $e');
      return {
        'success': false,
        'synced': successful,
        'failed': failed,
        'errors': [...errors, e.toString()],
      };
    }
  }

  /// Clear all queued items
  Future<bool> clearQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_queueKey);
      print('✅ Offline queue cleared');
      return true;
    } catch (e) {
      print('❌ Error clearing offline queue: $e');
      return false;
    }
  }

  /// Remove specific item from queue
  Future<bool> removeItem(String itemId) async {
    try {
      final queue = await _getQueue();
      queue.removeWhere((item) => item['id'] == itemId);
      await _saveQueue(queue);
      print('✅ Item removed from queue: $itemId');
      return true;
    } catch (e) {
      print('❌ Error removing item from queue: $e');
      return false;
    }
  }

  // Private helper methods

  Future<List<Map<String, dynamic>>> _getQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final queueJson = prefs.getString(_queueKey);
      
      if (queueJson == null) {
        return [];
      }
      
      final queueList = json.decode(queueJson) as List<dynamic>;
      return queueList.map((item) => item as Map<String, dynamic>).toList();
    } catch (e) {
      print('❌ Error reading offline queue: $e');
      return [];
    }
  }

  Future<bool> _saveQueue(List<Map<String, dynamic>> queue) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final queueJson = json.encode(queue);
      await prefs.setString(_queueKey, queueJson);
      return true;
    } catch (e) {
      print('❌ Error saving offline queue: $e');
      return false;
    }
  }

  Future<bool> _syncSettingsUpdate({
    required String baseUrl,
    required String authToken,
    required String cameraUuid,
    required Map<String, dynamic> settings,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/v1/cameras/mobile/$cameraUuid/settings');
      final payload = {
        'settings': settings,
        'source': 'mobile',
        'timestamp': DateTime.now().toIso8601String(),
      };
      
      final response = await http.patch(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: json.encode(payload),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      print('❌ Error syncing settings update: $e');
      return false;
    }
  }

  Future<bool> _syncCameraRename({
    required String baseUrl,
    required String authToken,
    required String cameraUuid,
    required String newName,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/v1/cameras/mobile/$cameraUuid/name');
      final payload = {
        'name': newName,
        'source': 'mobile',
      };
      
      final response = await http.patch(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: json.encode(payload),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      print('❌ Error syncing camera rename: $e');
      return false;
    }
  }

  Future<bool> _syncCollectionChange({
    required String baseUrl,
    required String authToken,
    required String cameraUuid,
    required String? collectionId,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/v1/cameras/mobile/$cameraUuid/collection');
      final payload = {
        'collection_id': collectionId,
        'source': 'mobile',
      };
      
      final response = await http.patch(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: json.encode(payload),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      print('❌ Error syncing collection change: $e');
      return false;
    }
  }
}

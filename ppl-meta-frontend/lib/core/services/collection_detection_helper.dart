import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/collection_models.dart';

/// Helper service to manually establish camera-collection mappings
/// This is a temporary solution until authentication is properly resolved
class CollectionDetectionHelper {
  static const String _mappingsKey = 'camera_collection_mappings';

  /// Manually create a mapping for USB Camera 0 to its existing collection
  static Future<bool> createUsbCameraMapping() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Create the mapping we know exists
      final mapping = CameraCollectionMapping(
        cameraId: 'usb_camera_0',
        collectionId: 'c984dbd1-6598-44db-aa99-87ac955de25a',
        cameraName: 'USB Camera 0',
        collectionName: 'USB Camera 0 Collection',
        createdAt: DateTime.now(),
        lastUsed: DateTime.now(),
        autoCreated: true, // This was auto-created previously
      );
      
      // Get existing mappings
      List<CameraCollectionMapping> mappings = [];
      final mappingsJson = prefs.getString(_mappingsKey);
      if (mappingsJson != null) {
        final mappingsList = json.decode(mappingsJson) as List;
        mappings = mappingsList
            .map((json) => CameraCollectionMapping.fromJson(json as Map<String, dynamic>))
            .toList();
      }
      
      // Remove any existing mapping for this camera
      mappings.removeWhere((m) => m.cameraId == 'usb_camera_0');
      
      // Add the new mapping
      mappings.add(mapping);
      
      // Store updated mappings
      final updatedJson = json.encode(mappings.map((m) => m.toJson()).toList());
      await prefs.setString(_mappingsKey, updatedJson);
      
      print('✅ Successfully created USB Camera 0 collection mapping!');
      print('   Camera: ${mapping.cameraId}');
      print('   Collection: ${mapping.collectionId}');
      print('   Collection Name: ${mapping.collectionName}');
      
      return true;
    } catch (e) {
      print('❌ Failed to create USB Camera mapping: $e');
      return false;
    }
  }

  /// Check if USB Camera 0 mapping exists
  static Future<bool> hasUsbCameraMapping() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final mappingsJson = prefs.getString(_mappingsKey);
      
      if (mappingsJson != null) {
        final mappingsList = json.decode(mappingsJson) as List;
        final mappings = mappingsList
            .map((json) => CameraCollectionMapping.fromJson(json as Map<String, dynamic>))
            .toList();
        
        return mappings.any((m) => m.cameraId == 'usb_camera_0');
      }
      
      return false;
    } catch (e) {
      print('Error checking USB Camera mapping: $e');
      return false;
    }
  }

  /// Get all current mappings for debugging
  static Future<List<CameraCollectionMapping>> getAllMappings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final mappingsJson = prefs.getString(_mappingsKey);
      
      if (mappingsJson != null) {
        final mappingsList = json.decode(mappingsJson) as List;
        return mappingsList
            .map((json) => CameraCollectionMapping.fromJson(json as Map<String, dynamic>))
            .toList();
      }
      
      return [];
    } catch (e) {
      print('Error getting mappings: $e');
      return [];
    }
  }

  /// Clear all mappings (for debugging)
  static Future<void> clearAllMappings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_mappingsKey);
      print('✅ Cleared all camera collection mappings');
    } catch (e) {
      print('❌ Failed to clear mappings: $e');
    }
  }
}

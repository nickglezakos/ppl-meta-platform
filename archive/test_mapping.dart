import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

void main() async {
  final prefs = await SharedPreferences.getInstance();
  
  // Create mapping for USB Camera 0 -> USB Camera 0 Collection
  final mapping = {
    'cameraId': 'usb_camera_0',
    'collectionId': 'c984dbd1-6598-44db-aa99-87ac955de25a',
    'cameraName': 'USB Camera 0',
    'collectionName': 'USB Camera 0 Collection',
    'createdAt': DateTime.now().toIso8601String(),
    'lastUsed': DateTime.now().toIso8601String(),
  };
  
  // Store as list (even if single item)
  final mappingsList = [mapping];
  final mappingsJson = json.encode(mappingsList);
  
  await prefs.setString('camera_collection_mappings', mappingsJson);
  
  print('✅ Stored camera collection mapping successfully!');
  print('Camera: usb_camera_0 -> Collection: c984dbd1-6598-44db-aa99-87ac955de25a');
}

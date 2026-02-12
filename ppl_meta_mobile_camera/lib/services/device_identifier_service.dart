import 'dart:convert';
import 'dart:io';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:crypto/crypto.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

/// Service for generating unique device identifiers and camera names
class DeviceIdentifierService {
  static final DeviceIdentifierService _instance = DeviceIdentifierService._internal();
  factory DeviceIdentifierService() => _instance;
  DeviceIdentifierService._internal();

  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  final Uuid _uuid = const Uuid();
  String? _cachedCameraName;
  String? _cachedDeviceId;
  String? _cachedCameraUuid; // Cache for camera UUID to prevent repeated lookups
  
  /// Key for storing server-generated camera UUID in shared preferences
  static const String _cameraUuidKey = 'ppl_camera_uuid';
  
  /// Key for storing legacy device UUID (deprecated, kept for migration)
  static const String _deviceIdKey = 'ppl_device_uuid';

  /// Generates a unique camera name in the format: mcam-<device-model>-<unique-id>
  /// Example: mcam-xiaomi-redminote11-2d7ee4 (consistent, no timestamps)
  Future<String> generateCameraName() async {
    if (_cachedCameraName != null) {
      return _cachedCameraName!;
    }

    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        final deviceModel = _sanitizeModelName(androidInfo.model);
        final uniqueId = await _generateUniqueId(androidInfo);
        
        // Generate a consistent name without timestamps
        _cachedCameraName = 'mcam-$deviceModel-$uniqueId';
        return _cachedCameraName!;
      } else {
        // Fallback for other platforms
        final uniqueId = _generateFallbackId();
        _cachedCameraName = 'mcam-device-$uniqueId';
        return _cachedCameraName!;
      }
    } catch (e) {
      print('⚠️ Error generating camera name: $e');
      // Generate fallback name without timestamp
      final fallbackId = _generateFallbackId();
      _cachedCameraName = 'mcam-device-$fallbackId';
      return _cachedCameraName!;
    }
  }

  /// Sanitizes device model name to be URL-safe and readable
  String _sanitizeModelName(String model) {
    if (model.isEmpty) return 'device';
    
    final sanitized = model
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]'), '') // Remove non-alphanumeric
        .replaceAll(RegExp(r'^[^a-z]'), ''); // Ensure starts with letter
    
    if (sanitized.isEmpty) return 'device';
    
    // Fix the substring logic to prevent RangeError
    final maxLength = 15;
    final actualLength = sanitized.length;
    final finalLength = actualLength > maxLength ? maxLength : actualLength;
    
    return sanitized.substring(0, finalLength);
  }

  /// Generates a unique 6-character identifier from device info
  Future<String> _generateUniqueId(AndroidDeviceInfo androidInfo) async {
    // Combine multiple device identifiers for uniqueness
    final identifiers = [
      androidInfo.id,
      androidInfo.fingerprint,
      androidInfo.serialNumber,
      androidInfo.product, // Use product instead of androidId
    ].where((id) => id != null && id.isNotEmpty).join('|');

    // Generate hash and take first 6 characters
    final bytes = utf8.encode(identifiers);
    final digest = sha256.convert(bytes);
    return digest.toString().substring(0, 6);
  }

  /// Generates a fallback ID when device info is unavailable
  String _generateFallbackId() {
    // Use a consistent fallback based on platform rather than timestamp
    final platformHash = Platform.operatingSystem.hashCode.abs();
    final idString = platformHash.toString();
    // Take last 6 digits, ensuring we don't exceed the string length
    final endIndex = idString.length;
    final startIndex = endIndex >= 6 ? endIndex - 6 : 0;
    return idString.substring(startIndex);
  }

  /// Gets device UUID - generates and persists if not exists
  /// 
  /// This ensures each device has a stable UUID that persists across app restarts.
  /// Priority:
  /// 1. Cached value (in-memory)
  /// 2. Stored value (SharedPreferences)
  /// 3. Generate new UUID v4 and persist
  Future<String> getDeviceId() async {
    // Return cached value if available
    if (_cachedDeviceId != null) {
      return _cachedDeviceId!;
    }
    
    try {
      final prefs = await SharedPreferences.getInstance();
      String? deviceId = prefs.getString(_deviceIdKey);
      
      if (deviceId == null || deviceId.isEmpty) {
        // Generate proper UUID v4 for new installations
        deviceId = _uuid.v4();
        await prefs.setString(_deviceIdKey, deviceId);
        print('✅ Generated new UUID for mobile camera: $deviceId');
      } else {
        print('📱 Using persisted device UUID: $deviceId');
      }
      
      // Cache for fast access
      _cachedDeviceId = deviceId;
      return deviceId;
    } catch (e) {
      print('⚠️ Error getting/generating device ID: $e');
      // Fallback to generated UUID (won't persist if SharedPreferences failed)
      final fallbackId = _uuid.v4();
      _cachedDeviceId = fallbackId;
      return fallbackId;
    }
  }

  /// Gets detailed device information for registration
  Future<Map<String, dynamic>> getDeviceRegistrationInfo() async {
    // Get proper UUID for device_id
    final deviceId = await getDeviceId();
    
    try {
      if (Platform.isAndroid) {
        final deviceInfo = DeviceInfoPlugin();
        final androidInfo = await deviceInfo.androidInfo;
        return {
          'manufacturer': androidInfo.manufacturer,
          'model': androidInfo.model,
          'brand': androidInfo.brand,
          'os_version': androidInfo.version.release,
          'sdk_version': androidInfo.version.sdkInt,
          'device_id': deviceId, // Use proper UUID
          'fingerprint': androidInfo.fingerprint,
          'platform': Platform.operatingSystem,
        };
      } else {
        // Fallback for other platforms
        return {
          'manufacturer': 'Unknown',
          'model': 'Mobile Device',
          'brand': 'Generic',
          'os_version': Platform.operatingSystemVersion,
          'platform': Platform.operatingSystem,
          'device_id': deviceId, // Use proper UUID
        };
      }
    } catch (e) {
      print('⚠️ Error getting device info: $e');
      return {
        'manufacturer': 'PPL Meta Mobile',
        'model': 'Unknown Device',
        'brand': 'Generic',
        'os_version': 'Unknown',
        'device_id': deviceId, // Use proper UUID
        'error': e.toString(),
      };
    }
  }

  /// Clears cached camera name, device ID, and camera UUID (for testing or reset)
  void clearCache() {
    _cachedCameraName = null;
    _cachedDeviceId = null;
    _cachedCameraUuid = null;
    print('🔄 All device identifier caches cleared');
  }
  
  /// Stores server-generated camera UUID
  /// This UUID is returned by the backend during registration and must be used for all API calls
  Future<void> storeCameraUuid(String uuid) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_cameraUuidKey, uuid);
      
      // Cache the UUID in memory for fast access
      if (uuid.isNotEmpty) {
        _cachedCameraUuid = uuid;
        print('✅ Stored server-generated camera UUID: $uuid (cached in memory)');
      } else {
        // Allow clearing UUID only if explicitly empty
        _cachedCameraUuid = null;
        print('⚠️  Camera UUID cleared from storage and cache');
      }
    } catch (e) {
      print('❌ Error storing camera UUID: $e');
      // Still cache it even if storage fails
      if (uuid.isNotEmpty) {
        _cachedCameraUuid = uuid;
        print('⚠️  UUID cached in memory despite storage error');
      }
      throw Exception('Failed to store camera UUID');
    }
  }
  
  /// Retrieves stored camera UUID from server
  /// Returns null if camera has not been registered yet
  /// Uses in-memory cache for performance and reliability
  Future<String?> getStoredCameraUuid() async {
    // Return cached value if available (fast path)
    if (_cachedCameraUuid != null && _cachedCameraUuid!.isNotEmpty) {
      print('📱 Retrieved camera UUID from cache: $_cachedCameraUuid');
      return _cachedCameraUuid;
    }
    
    try {
      final prefs = await SharedPreferences.getInstance();
      final uuid = prefs.getString(_cameraUuidKey);
      
      if (uuid != null && uuid.isNotEmpty) {
        // Cache for future access
        _cachedCameraUuid = uuid;
        print('📱 Retrieved stored camera UUID: $uuid (now cached)');
        return uuid;
      } else {
        print('⚠️  No camera UUID stored - camera not registered');
        return null;
      }
    } catch (e) {
      print('❌ Error retrieving camera UUID from storage: $e');
      // Return cached value as fallback if storage fails
      if (_cachedCameraUuid != null && _cachedCameraUuid!.isNotEmpty) {
        print('💡 Using cached camera UUID despite storage error: $_cachedCameraUuid');
        return _cachedCameraUuid;
      }
      return null;
    }
  }
  
  /// Gets device serial number for hardware identification
  Future<String> getDeviceSerial() async {
    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        // Use fingerprint as serial since actual serial may not be accessible
        return androidInfo.fingerprint ?? androidInfo.id;
      } else {
        // Fallback for other platforms
        return _uuid.v4();
      }
    } catch (e) {
      print('⚠️ Error getting device serial: $e');
      return _uuid.v4();
    }
  }

  /// Gets a human-readable device description
  Future<String> getDeviceDescription() async {
    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        return '${androidInfo.manufacturer} ${androidInfo.model} (Android ${androidInfo.version.release})';
      } else {
        return 'Mobile Device (${Platform.operatingSystem})';
      }
    } catch (e) {
      return 'Unknown Mobile Device';
    }
  }

  /// Resets device UUID (generates new one) - USE WITH CAUTION
  /// This will cause the device to register as a new camera
  Future<void> resetDeviceId() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_deviceIdKey);
      _cachedDeviceId = null;
      print('⚠️ Device UUID reset - will generate new UUID on next access');
    } catch (e) {
      print('❌ Error resetting device ID: $e');
    }
  }
}

import 'dart:convert';
import 'dart:io';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:crypto/crypto.dart';

/// Service for generating unique device identifiers and camera names
class DeviceIdentifierService {
  static final DeviceIdentifierService _instance = DeviceIdentifierService._internal();
  factory DeviceIdentifierService() => _instance;
  DeviceIdentifierService._internal();

  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  String? _cachedCameraName;

  /// Generates a unique camera name in the format: mcam-<device-model>-<unique-id>
  /// Example: mcam-xiaomi-2201117ty-a1b2c3
  Future<String> generateCameraName() async {
    if (_cachedCameraName != null) {
      return _cachedCameraName!;
    }

    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        final deviceModel = _sanitizeModelName(androidInfo.model);
        final uniqueId = await _generateUniqueId(androidInfo);
        
        _cachedCameraName = 'mcam-$deviceModel-$uniqueId';
        return _cachedCameraName!;
      } else {
        // Fallback for other platforms
        final uniqueId = _generateFallbackId();
        _cachedCameraName = 'mcam-unknown-$uniqueId';
        return _cachedCameraName!;
      }
    } catch (e) {
      print('⚠️ Error generating camera name: $e');
      // Generate fallback name
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
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final randomComponent = timestamp.toString();
    // Take last 6 digits, ensuring we don't exceed the string length
    final endIndex = randomComponent.length;
    final startIndex = endIndex >= 6 ? endIndex - 6 : 0;
    return randomComponent.substring(startIndex);
  }

  /// Gets detailed device information for registration
  Future<Map<String, dynamic>> getDeviceRegistrationInfo() async {
    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        return {
          'manufacturer': androidInfo.manufacturer,
          'model': androidInfo.model,
          'brand': androidInfo.brand,
          'os_version': androidInfo.version.release,
          'sdk_version': androidInfo.version.sdkInt,
          'device_id': androidInfo.id,
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
        };
      }
    } catch (e) {
      print('⚠️ Error getting device info: $e');
      return {
        'manufacturer': 'PPL Meta Mobile',
        'model': 'Unknown Device',
        'brand': 'Generic',
        'os_version': 'Unknown',
        'error': e.toString(),
      };
    }
  }

  /// Clears cached camera name (for testing or reset)
  void clearCache() {
    _cachedCameraName = null;
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
}

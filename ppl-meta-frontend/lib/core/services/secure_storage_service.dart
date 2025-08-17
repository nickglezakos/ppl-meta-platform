import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Platform-aware secure storage service that works across web, Android, and iOS
class SecureStorageService {
  static const _secureStorage = FlutterSecureStorage(
    webOptions: WebOptions(
      dbName: 'ppl_meta_secure_storage',
      publicKey: 'ppl_meta_public_key',
    ),
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  /// Store a value securely
  static Future<void> setString(String key, String value) async {
    try {
      print('SecureStorage: Storing value for key "$key"');
      
      if (kIsWeb) {
        // For web, use both secure storage and SharedPreferences as fallback
        await _secureStorage.write(key: key, value: value);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(key, value);
        print('SecureStorage: Value stored on web (both secure storage and SharedPreferences)');
      } else {
        // For mobile platforms, use secure storage
        await _secureStorage.write(key: key, value: value);
        print('SecureStorage: Value stored on mobile platform');
      }
    } catch (e) {
      print('SecureStorage: Failed to store value for key "$key": $e');
      // Fallback to SharedPreferences if secure storage fails
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(key, value);
        print('SecureStorage: Fallback to SharedPreferences successful');
      } catch (fallbackError) {
        print('SecureStorage: Fallback also failed: $fallbackError');
        rethrow;
      }
    }
  }

  /// Retrieve a value securely
  static Future<String?> getString(String key) async {
    try {
      print('SecureStorage: Retrieving value for key "$key"');
      
      String? value;
      
      if (kIsWeb) {
        // For web, try secure storage first, then SharedPreferences
        try {
          value = await _secureStorage.read(key: key);
          print('SecureStorage: Got value from secure storage: ${value != null ? 'EXISTS' : 'NULL'}');
        } catch (e) {
          print('SecureStorage: Secure storage failed on web, trying SharedPreferences: $e');
        }
        
        if (value == null) {
          final prefs = await SharedPreferences.getInstance();
          value = prefs.getString(key);
          print('SecureStorage: Got value from SharedPreferences: ${value != null ? 'EXISTS' : 'NULL'}');
        }
      } else {
        // For mobile platforms, use secure storage
        value = await _secureStorage.read(key: key);
        print('SecureStorage: Got value from mobile secure storage: ${value != null ? 'EXISTS' : 'NULL'}');
      }
      
      return value;
    } catch (e) {
      print('SecureStorage: Failed to retrieve value for key "$key": $e');
      // Fallback to SharedPreferences
      try {
        final prefs = await SharedPreferences.getInstance();
        final value = prefs.getString(key);
        print('SecureStorage: Fallback to SharedPreferences: ${value != null ? 'EXISTS' : 'NULL'}');
        return value;
      } catch (fallbackError) {
        print('SecureStorage: Fallback also failed: $fallbackError');
        return null;
      }
    }
  }

  /// Remove a value securely
  static Future<void> remove(String key) async {
    try {
      print('SecureStorage: Removing value for key "$key"');
      
      if (kIsWeb) {
        // For web, remove from both storage mechanisms
        await _secureStorage.delete(key: key);
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove(key);
        print('SecureStorage: Value removed from web (both storages)');
      } else {
        // For mobile platforms, use secure storage
        await _secureStorage.delete(key: key);
        print('SecureStorage: Value removed from mobile platform');
      }
    } catch (e) {
      print('SecureStorage: Failed to remove value for key "$key": $e');
      // Fallback to SharedPreferences
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove(key);
        print('SecureStorage: Fallback removal successful');
      } catch (fallbackError) {
        print('SecureStorage: Fallback removal failed: $fallbackError');
      }
    }
  }

  /// Clear all stored values
  static Future<void> clear() async {
    try {
      print('SecureStorage: Clearing all stored values');
      
      if (kIsWeb) {
        // For web, clear both storage mechanisms
        await _secureStorage.deleteAll();
        final prefs = await SharedPreferences.getInstance();
        await prefs.clear();
        print('SecureStorage: All values cleared from web (both storages)');
      } else {
        // For mobile platforms, use secure storage
        await _secureStorage.deleteAll();
        print('SecureStorage: All values cleared from mobile platform');
      }
    } catch (e) {
      print('SecureStorage: Failed to clear all values: $e');
      // Fallback to SharedPreferences
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.clear();
        print('SecureStorage: Fallback clear successful');
      } catch (fallbackError) {
        print('SecureStorage: Fallback clear failed: $fallbackError');
      }
    }
  }

  /// Check if a key exists
  static Future<bool> containsKey(String key) async {
    final value = await getString(key);
    return value != null;
  }

  /// Get all keys (for debugging)
  static Future<Map<String, String>> getAllValues() async {
    try {
      if (kIsWeb) {
        // For web, get from SharedPreferences as it's more reliable for debugging
        final prefs = await SharedPreferences.getInstance();
        final keys = prefs.getKeys();
        final Map<String, String> result = {};
        for (final key in keys) {
          final value = prefs.getString(key);
          if (value != null) {
            result[key] = value;
          }
        }
        return result;
      } else {
        // For mobile, use secure storage
        return await _secureStorage.readAll();
      }
    } catch (e) {
      print('❌ SecureStorage: Failed to get all values: $e');
      return {};
    }
  }
}

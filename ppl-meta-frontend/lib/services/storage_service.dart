import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api/api_client.dart';
import '../models/storage_location.dart';
import '../models/storage_preferences.dart';
import '../services/dynamic_service_provider.dart';

/// Storage service for managing user storage preferences
class StorageService {
  final ApiClient _apiClient;

  StorageService(this._apiClient);

  /// Get user storage preferences
  Future<UserStoragePreferences> getUserPreferences() async {
    try {
      final response = await _apiClient.get('/api/v1/users/storage-preferences');
      return UserStoragePreferences.fromJson(response.data);
    } catch (error) {
      print('🔥 StorageService: Failed to get user preferences: $error');
      rethrow;
    }
  }

  /// Update user storage preferences
  Future<UserStoragePreferences> updateUserPreferences(UserStoragePreferencesUpdate updates) async {
    try {
      final response = await _apiClient.dio.put(
        '/api/v1/users/storage-preferences',
        data: updates.toJson(),
      );
      return UserStoragePreferences.fromJson(response.data);
    } catch (error) {
      print('🔥 StorageService: Failed to update user preferences: $error');
      rethrow;
    }
  }

  /// Reset user storage preferences to defaults
  Future<UserStoragePreferences> resetToDefaults() async {
    try {
      final response = await _apiClient.dio.post('/api/v1/users/storage-preferences/reset');
      return UserStoragePreferences.fromJson(response.data);
    } catch (error) {
      print('🔥 StorageService: Failed to reset preferences: $error');
      rethrow;
    }
  }

  /// Get storage recommendations
  Future<List<StorageRecommendation>> getStorageRecommendations() async {
    try {
      final response = await _apiClient.get('/api/v1/users/storage-recommendations');
      final List<dynamic> data = response.data['recommendations'] ?? [];
      return data.map((item) => StorageRecommendation.fromJson(item)).toList();
    } catch (error) {
      print('🔥 StorageService: Failed to get storage recommendations: $error');
      rethrow;
    }
  }

  // ── Storage Location Methods ───────────────────────────────────────

  /// List all storage locations
  Future<List<StorageLocation>> getStorageLocations() async {
    try {
      final response = await _apiClient.get('/api/v1/users/storage/locations');
      final List<dynamic> data = response.data is List ? response.data : [];
      return data.map((item) => StorageLocation.fromJson(item)).toList();
    } catch (error) {
      print('🔥 StorageService: Failed to get storage locations: $error');
      rethrow;
    }
  }

  /// Get storage dashboard summary
  Future<StorageDashboard> getStorageDashboard() async {
    try {
      final response =
          await _apiClient.get('/api/v1/users/storage/locations/summary');
      return StorageDashboard.fromJson(response.data);
    } catch (error) {
      print('🔥 StorageService: Failed to get storage dashboard: $error');
      rethrow;
    }
  }

  /// Create a new storage location
  Future<StorageLocation> createStorageLocation(
      StorageLocationRequest request) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/users/storage/locations',
        data: request.toJson(),
      );
      return StorageLocation.fromJson(response.data);
    } catch (error) {
      print('🔥 StorageService: Failed to create storage location: $error');
      rethrow;
    }
  }

  /// Update a storage location
  Future<StorageLocation> updateStorageLocation(
      String locationId, Map<String, dynamic> updates) async {
    try {
      final response = await _apiClient.dio.put(
        '/api/v1/users/storage/locations/$locationId',
        data: updates,
      );
      return StorageLocation.fromJson(response.data);
    } catch (error) {
      print('🔥 StorageService: Failed to update storage location: $error');
      rethrow;
    }
  }

  /// Delete a storage location
  Future<void> deleteStorageLocation(String locationId) async {
    try {
      await _apiClient.dio.delete(
        '/api/v1/users/storage/locations/$locationId',
      );
    } catch (error) {
      print('🔥 StorageService: Failed to delete storage location: $error');
      rethrow;
    }
  }

  /// Verify a storage location is accessible
  Future<Map<String, dynamic>> verifyStorageLocation(
      String locationId) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/users/storage/locations/$locationId/verify',
      );
      return response.data;
    } catch (error) {
      print('🔥 StorageService: Failed to verify storage location: $error');
      rethrow;
    }
  }

  /// Set a location as default for its tier
  Future<void> setDefaultLocation(String locationId) async {
    try {
      await _apiClient.dio.post(
        '/api/v1/users/storage/locations/$locationId/set-default',
      );
    } catch (error) {
      print('🔥 StorageService: Failed to set default location: $error');
      rethrow;
    }
  }

  /// Get storage alerts
  Future<List<dynamic>> getStorageAlerts() async {
    try {
      final response = await _apiClient.get('/api/v1/users/storage/alerts');
      return response.data['alerts'] ?? [];
    } catch (error) {
      print('🔥 StorageService: Failed to get storage alerts: $error');
      rethrow;
    }
  }
}

/// Provider for the storage service
final storageServiceProvider = Provider<StorageService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return StorageService(apiClient);
});
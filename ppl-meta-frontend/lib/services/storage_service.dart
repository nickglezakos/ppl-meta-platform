import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api/api_client.dart';
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
}

/// Provider for the storage service
final storageServiceProvider = Provider<StorageService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return StorageService(apiClient);
});
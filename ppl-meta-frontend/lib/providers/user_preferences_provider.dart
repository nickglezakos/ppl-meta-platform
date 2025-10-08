// User Preferences Provider
// State management for user storage preferences and settings

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user_storage_preferences.dart';
import '../core/api/api_client.dart';

class UserPreferencesProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  UserStoragePreferences? _storagePreferences;
  StorageUsageSummary? _usageSummary;
  bool _isLoading = false;
  String? _error;

  UserPreferencesProvider(this._apiClient);

  UserStoragePreferences? get storagePreferences => _storagePreferences;
  StorageUsageSummary? get usageSummary => _usageSummary;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Load user storage preferences from the API
  Future<UserStoragePreferences> getStoragePreferences() async {
    _setLoading(true);
    _clearError();

    try {
      final response = await _apiClient.get('/api/v1/users/storage-preferences');
      _storagePreferences = UserStoragePreferences.fromJson(response.data as Map<String, dynamic>);
      notifyListeners();
      return _storagePreferences!;
    } catch (e) {
      _setError('Failed to load storage preferences: $e');
      // Return default preferences if loading fails
      _storagePreferences = _createDefaultPreferences();
      notifyListeners();
      return _storagePreferences!;
    } finally {
      _setLoading(false);
    }
  }

  /// Update user storage preferences
  Future<void> updateStoragePreferences(UserStoragePreferences preferences) async {
    _setLoading(true);
    _clearError();

    try {
      final response = await _apiClient.put(
        '/api/v1/users/storage-preferences',
        data: preferences.toJson(),
      );
      
      _storagePreferences = UserStoragePreferences.fromJson(response.data as Map<String, dynamic>);
      notifyListeners();
    } catch (e) {
      _setError('Failed to update storage preferences: $e');
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  /// Reset storage preferences to defaults
  Future<void> resetToDefaults() async {
    _setLoading(true);
    _clearError();

    try {
      final response = await _apiClient.post('/api/v1/users/storage-preferences/reset');
      _storagePreferences = UserStoragePreferences.fromJson(response.data as Map<String, dynamic>);
      notifyListeners();
    } catch (e) {
      _setError('Failed to reset preferences: $e');
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  /// Load storage usage summary
  Future<StorageUsageSummary> getStorageUsageSummary() async {
    _setLoading(true);
    _clearError();

    try {
      final response = await _apiClient.get('/api/v1/users/storage-summary');
      _usageSummary = StorageUsageSummary.fromJson(response.data as Map<String, dynamic>);
      notifyListeners();
      return _usageSummary!;
    } catch (e) {
      _setError('Failed to load storage usage summary: $e');
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  /// Get storage recommendations based on current usage
  Future<List<StorageRecommendation>> getStorageRecommendations() async {
    _clearError();

    try {
      final response = await _apiClient.get('/api/v1/users/storage-recommendations');
      final List<dynamic> recommendationsList = response.data['recommendations'] ?? [];
      
      return recommendationsList.map((rec) => StorageRecommendation(
        sizeGb: (rec['size_gb'] as num).toDouble(),
        label: rec['label'] as String,
        description: rec['description'] as String,
        icon: _getIconFromString(rec['icon'] as String),
      )).toList();
    } catch (e) {
      _setError('Failed to load storage recommendations: $e');
      return _getDefaultRecommendations();
    }
  }

  /// Apply recommended collection size
  Future<void> applyRecommendedSize(double sizeGb) async {
    if (_storagePreferences == null) {
      await getStoragePreferences();
    }

    final updatedPreferences = _storagePreferences!.copyWith(
      defaultCollectionSizeGb: sizeGb,
    );

    await updateStoragePreferences(updatedPreferences);
  }

  /// Update specific preference without full update
  Future<void> updatePreference<T>(String key, T value) async {
    if (_storagePreferences == null) {
      await getStoragePreferences();
    }

    UserStoragePreferences updatedPreferences;

    switch (key) {
      case 'defaultCollectionSizeGb':
        updatedPreferences = _storagePreferences!.copyWith(
          defaultCollectionSizeGb: value as double,
        );
        break;
      case 'defaultLivePortionPercentage':
        updatedPreferences = _storagePreferences!.copyWith(
          defaultLivePortionPercentage: value as double,
        );
        break;
      case 'enableStorageNotifications':
        updatedPreferences = _storagePreferences!.copyWith(
          enableStorageNotifications: value as bool,
        );
        break;
      case 'notificationThresholdPercentage':
        updatedPreferences = _storagePreferences!.copyWith(
          notificationThresholdPercentage: value as double,
        );
        break;
      case 'defaultAutoArchiveEnabled':
        updatedPreferences = _storagePreferences!.copyWith(
          defaultAutoArchiveEnabled: value as bool,
        );
        break;
      case 'defaultMinAgeForArchiveDays':
        updatedPreferences = _storagePreferences!.copyWith(
          defaultMinAgeForArchiveDays: value as int,
        );
        break;
      case 'preferredVideoQuality':
        updatedPreferences = _storagePreferences!.copyWith(
          preferredVideoQuality: value as String,
        );
        break;
      case 'preferredCompressionEnabled':
        updatedPreferences = _storagePreferences!.copyWith(
          preferredCompressionEnabled: value as bool,
        );
        break;
      default:
        throw ArgumentError('Unknown preference key: $key');
    }

    await updateStoragePreferences(updatedPreferences);
  }

  /// Check if preferences need optimization
  bool needsOptimization() {
    if (_storagePreferences == null || _usageSummary == null) return false;

    // Check if user is running out of space
    if (_usageSummary!.usagePercentage > 85.0) return true;

    // Check if live storage ratio is inefficient
    if (_storagePreferences!.defaultLivePortionPercentage > 85.0) return true;

    // Check if archival is disabled but storage is getting full
    if (!_storagePreferences!.defaultAutoArchiveEnabled && 
        _usageSummary!.usagePercentage > 70.0) return true;

    return false;
  }

  /// Get optimization suggestions
  List<String> getOptimizationSuggestions() {
    final suggestions = <String>[];

    if (_storagePreferences == null || _usageSummary == null) {
      return suggestions;
    }

    if (_usageSummary!.usagePercentage > 85.0) {
      suggestions.add('Consider increasing default collection size or enabling auto-archival');
    }

    if (_storagePreferences!.defaultLivePortionPercentage > 85.0) {
      suggestions.add('Reduce live storage portion to improve efficiency');
    }

    if (!_storagePreferences!.defaultAutoArchiveEnabled) {
      suggestions.add('Enable auto-archival to automatically manage storage');
    }

    if (!_storagePreferences!.preferredCompressionEnabled && 
        _usageSummary!.usagePercentage > 70.0) {
      suggestions.add('Enable compression to save storage space');
    }

    if (_storagePreferences!.defaultMinAgeForArchiveDays > 30 && 
        _usageSummary!.usagePercentage > 80.0) {
      suggestions.add('Reduce archive delay to free up live storage sooner');
    }

    return suggestions;
  }

  /// Refresh all data
  Future<void> refreshAll() async {
    await Future.wait([
      getStoragePreferences(),
      getStorageUsageSummary(),
    ]);
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void _setError(String error) {
    _error = error;
    notifyListeners();
  }

  void _clearError() {
    _error = null;
  }

  UserStoragePreferences _createDefaultPreferences() {
    return const UserStoragePreferences(
      userUuid: 'default', // This should be replaced with actual user UUID
    );
  }

  IconData _getIconFromString(String iconName) {
    switch (iconName.toLowerCase()) {
      case 'home':
        return Icons.home;
      case 'camera':
      case 'camera_alt':
        return Icons.camera_alt;
      case 'business':
        return Icons.business;
      case 'apartment':
        return Icons.apartment;
      case 'factory':
        return Icons.factory;
      default:
        return Icons.storage;
    }
  }

  List<StorageRecommendation> _getDefaultRecommendations() {
    return [
      const StorageRecommendation(
        sizeGb: 25.0,
        label: 'Basic',
        description: 'Small home setup, 1-2 cameras',
        icon: Icons.home,
      ),
      const StorageRecommendation(
        sizeGb: 50.0,
        label: 'Standard',
        description: 'Most home setups, 3-5 cameras',
        icon: Icons.camera_alt,
      ),
      const StorageRecommendation(
        sizeGb: 100.0,
        label: 'Professional',
        description: 'Small business, 6-10 cameras',
        icon: Icons.business,
      ),
      const StorageRecommendation(
        sizeGb: 250.0,
        label: 'Enterprise',
        description: 'Large installations, 10+ cameras',
        icon: Icons.apartment,
      ),
    ];
  }
}

class StorageRecommendation {
  final double sizeGb;
  final String label;
  final String description;
  final IconData icon;

  const StorageRecommendation({
    required this.sizeGb,
    required this.label,
    required this.description,
    required this.icon,
  });
}

// Riverpod provider for UserPreferencesProvider
final userPreferencesProvider = ChangeNotifierProvider<UserPreferencesProvider>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserPreferencesProvider(apiClient);
});
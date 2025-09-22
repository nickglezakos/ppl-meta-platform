import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';

// Features state model
class FeaturesState {
  final bool hasVisionCapability;
  final bool faceDetectionEnabled;
  final bool faceDetectionOnSaveEnabled; // NEW: Face detection on save
  final String selectedDetectionMethod;
  final double confidenceThreshold;
  final int frameInterval;
  final bool smartOrganizationEnabled;
  final bool autoSyncEnabled;
  final bool isLoading;
  final String? error;

  const FeaturesState({
    this.hasVisionCapability = false,
    this.faceDetectionEnabled = false,
    this.faceDetectionOnSaveEnabled = false, // NEW: Default to false
    this.selectedDetectionMethod = 'two_stage',
    this.confidenceThreshold = 0.5,
    this.frameInterval = 15,
    this.smartOrganizationEnabled = true,
    this.autoSyncEnabled = false,
    this.isLoading = false,
    this.error,
  });

  FeaturesState copyWith({
    bool? hasVisionCapability,
    bool? faceDetectionEnabled,
    bool? faceDetectionOnSaveEnabled, // NEW: Add to copyWith
    String? selectedDetectionMethod,
    double? confidenceThreshold,
    int? frameInterval,
    bool? smartOrganizationEnabled,
    bool? autoSyncEnabled,
    bool? isLoading,
    String? error,
  }) {
    return FeaturesState(
      hasVisionCapability: hasVisionCapability ?? this.hasVisionCapability,
      faceDetectionEnabled: faceDetectionEnabled ?? this.faceDetectionEnabled,
      faceDetectionOnSaveEnabled: faceDetectionOnSaveEnabled ?? this.faceDetectionOnSaveEnabled, // NEW
      selectedDetectionMethod: selectedDetectionMethod ?? this.selectedDetectionMethod,
      confidenceThreshold: confidenceThreshold ?? this.confidenceThreshold,
      frameInterval: frameInterval ?? this.frameInterval,
      smartOrganizationEnabled: smartOrganizationEnabled ?? this.smartOrganizationEnabled,
      autoSyncEnabled: autoSyncEnabled ?? this.autoSyncEnabled,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

// Features notifier
class FeaturesNotifier extends AsyncNotifier<FeaturesState> {
  @override
  Future<FeaturesState> build() async {
    return await _loadFeatures();
  }

  Future<FeaturesState> _loadFeatures() async {
    try {
      // Get user capabilities from the backend
      final capabilities = await _getUserCapabilities();
      final hasVision = capabilities.contains('vision');
      
      // Get saved feature preferences from local storage or defaults
      final savedPreferences = await _loadSavedPreferences();
      
      return FeaturesState(
        hasVisionCapability: hasVision,
        faceDetectionEnabled: hasVision ? savedPreferences['faceDetection'] ?? true : false,
        faceDetectionOnSaveEnabled: hasVision ? savedPreferences['faceDetectionOnSave'] ?? false : false, // NEW: Load setting
        selectedDetectionMethod: savedPreferences['detectionMethod'] ?? 'two_stage',
        confidenceThreshold: savedPreferences['confidenceThreshold'] ?? 0.5,
        frameInterval: savedPreferences['frameInterval'] ?? 15,
        smartOrganizationEnabled: savedPreferences['smartOrganization'] ?? true,
        autoSyncEnabled: savedPreferences['autoSync'] ?? false,
        isLoading: false,
      );
    } catch (e) {
      return FeaturesState(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<List<String>> _getUserCapabilities() async {
    try {
      final apiClient = ref.read(apiClientProvider);
      
      // Call the Node service directly since gateway might not be updated yet
      final response = await apiClient.get('http://localhost:8001/capabilities/my-capabilities');
      
      if (response.data != null && response.data.containsKey('capabilities')) {
        return List<String>.from(response.data['capabilities']);
      }
      
      return [];
    } catch (e) {
      // If the API call fails, we'll assume no special capabilities
      return [];
    }
  }

  Future<Map<String, dynamic>> _loadSavedPreferences() async {
    // Load global settings from backend API
    try {
      final apiClient = ref.read(apiClientProvider);
      
      // Try to get face detection on save setting from backend
      bool faceDetectionOnSave = false;
      try {
        final response = await apiClient.get('/api/v1/settings/face_detection_on_save');
        if (response.data != null) {
          faceDetectionOnSave = response.data['value'] == 'true';
        }
      } catch (e) {
        // Setting doesn't exist yet, use default
        debugPrint('Face detection on save setting not found, using default: $e');
      }
      
      return {
        'faceDetection': true,
        'faceDetectionOnSave': faceDetectionOnSave, // Load from backend
        'detectionMethod': 'two_stage',
        'confidenceThreshold': 0.5,
        'frameInterval': 15,
        'smartOrganization': true,
        'autoSync': false,
      };
    } catch (e) {
      debugPrint('Error loading settings from backend: $e');
      // Fallback to defaults
      return {
        'faceDetection': true,
        'faceDetectionOnSave': false,
        'detectionMethod': 'two_stage',
        'confidenceThreshold': 0.5,
        'frameInterval': 15,
        'smartOrganization': true,
        'autoSync': false,
      };
    }
  }

  Future<void> _savePreferences(Map<String, dynamic> preferences) async {
    // Save face detection on save setting to backend API (global setting)
    try {
      final apiClient = ref.read(apiClientProvider);
      
      // Save the global face detection on save setting
      await apiClient.post('/api/v1/settings/', data: {
        'key': 'face_detection_on_save',
        'value': preferences['faceDetectionOnSave'].toString(),
      });
      
      debugPrint('✅ Global face detection on save setting saved: ${preferences['faceDetectionOnSave']}');
    } catch (e) {
      debugPrint('❌ Error saving face detection on save setting: $e');
    }
  }

  Future<void> toggleFaceDetection(bool enabled) async {
    final currentState = state.value;
    if (currentState == null || !currentState.hasVisionCapability) return;

    state = AsyncValue.data(
      currentState.copyWith(faceDetectionEnabled: enabled),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': enabled,
      'faceDetectionOnSave': currentState.faceDetectionOnSaveEnabled, // NEW: Include in save
      'detectionMethod': currentState.selectedDetectionMethod,
      'confidenceThreshold': currentState.confidenceThreshold,
      'frameInterval': currentState.frameInterval,
      'smartOrganization': currentState.smartOrganizationEnabled,
      'autoSync': currentState.autoSyncEnabled,
    });
  }

  /// NEW: Toggle face detection on save feature
  Future<void> toggleFaceDetectionOnSave(bool enabled) async {
    final currentState = state.value;
    if (currentState == null || !currentState.hasVisionCapability) return;

    state = AsyncValue.data(
      currentState.copyWith(faceDetectionOnSaveEnabled: enabled),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': currentState.faceDetectionEnabled,
      'faceDetectionOnSave': enabled, // NEW: Save the new setting
      'detectionMethod': currentState.selectedDetectionMethod,
      'confidenceThreshold': currentState.confidenceThreshold,
      'frameInterval': currentState.frameInterval,
      'smartOrganization': currentState.smartOrganizationEnabled,
      'autoSync': currentState.autoSyncEnabled,
    });
  }

  Future<void> updateDetectionMethod(String method) async {
    final currentState = state.value;
    if (currentState == null || !currentState.hasVisionCapability) return;

    state = AsyncValue.data(
      currentState.copyWith(selectedDetectionMethod: method),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': currentState.faceDetectionEnabled,
      'faceDetectionOnSave': currentState.faceDetectionOnSaveEnabled, // NEW: Include in save
      'detectionMethod': method,
      'confidenceThreshold': currentState.confidenceThreshold,
      'frameInterval': currentState.frameInterval,
      'smartOrganization': currentState.smartOrganizationEnabled,
      'autoSync': currentState.autoSyncEnabled,
    });
  }

  Future<void> updateConfidenceThreshold(double threshold) async {
    final currentState = state.value;
    if (currentState == null || !currentState.hasVisionCapability) return;

    state = AsyncValue.data(
      currentState.copyWith(confidenceThreshold: threshold),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': currentState.faceDetectionEnabled,
      'faceDetectionOnSave': currentState.faceDetectionOnSaveEnabled, // NEW: Include in save
      'detectionMethod': currentState.selectedDetectionMethod,
      'confidenceThreshold': threshold,
      'frameInterval': currentState.frameInterval,
      'smartOrganization': currentState.smartOrganizationEnabled,
      'autoSync': currentState.autoSyncEnabled,
    });
  }

  Future<void> updateFrameInterval(int interval) async {
    final currentState = state.value;
    if (currentState == null || !currentState.hasVisionCapability) return;

    state = AsyncValue.data(
      currentState.copyWith(frameInterval: interval),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': currentState.faceDetectionEnabled,
      'faceDetectionOnSave': currentState.faceDetectionOnSaveEnabled, // NEW: Include in save
      'detectionMethod': currentState.selectedDetectionMethod,
      'confidenceThreshold': currentState.confidenceThreshold,
      'frameInterval': interval,
      'smartOrganization': currentState.smartOrganizationEnabled,
      'autoSync': currentState.autoSyncEnabled,
    });
  }

  Future<void> toggleSmartOrganization(bool enabled) async {
    final currentState = state.value;
    if (currentState == null) return;

    state = AsyncValue.data(
      currentState.copyWith(smartOrganizationEnabled: enabled),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': currentState.faceDetectionEnabled,
      'detectionMethod': currentState.selectedDetectionMethod,
      'confidenceThreshold': currentState.confidenceThreshold,
      'frameInterval': currentState.frameInterval,
      'smartOrganization': enabled,
      'autoSync': currentState.autoSyncEnabled,
    });
  }

  Future<void> toggleAutoSync(bool enabled) async {
    final currentState = state.value;
    if (currentState == null) return;

    state = AsyncValue.data(
      currentState.copyWith(autoSyncEnabled: enabled),
    );

    // Save preference
    await _savePreferences({
      'faceDetection': currentState.faceDetectionEnabled,
      'detectionMethod': currentState.selectedDetectionMethod,
      'confidenceThreshold': currentState.confidenceThreshold,
      'frameInterval': currentState.frameInterval,
      'smartOrganization': currentState.smartOrganizationEnabled,
      'autoSync': enabled,
    });
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = AsyncValue.data(await _loadFeatures());
  }
}

// Provider
final featuresNotifierProvider = AsyncNotifierProvider<FeaturesNotifier, FeaturesState>(
  () => FeaturesNotifier(),
);

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';
import '../config/app_config.dart';

// Features state model
class FeaturesState {
  final bool hasVisionCapability;
  final bool faceDetectionEnabled;
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
    // In a real app, this would load from SharedPreferences or similar
    // For now, return defaults
    return {
      'faceDetection': true,
      'detectionMethod': 'two_stage',
      'confidenceThreshold': 0.5,
      'frameInterval': 15,
      'smartOrganization': true,
      'autoSync': false,
    };
  }

  Future<void> _savePreferences(Map<String, dynamic> preferences) async {
    // In a real app, this would save to SharedPreferences or similar
    // For now, we'll just log the preferences
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
